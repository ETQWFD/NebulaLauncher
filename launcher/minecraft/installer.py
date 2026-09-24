# -*- coding: utf-8 -*-
"""版本安装：下载客户端 jar、库、资产、原生库，并支持进度回调."""
import os
import threading
from typing import Callable, Dict, List, Optional

from .. import utils
from ..constants import (ASSET_INDEX_MIRRORS, ASSET_OBJECT_URLS, LIBRARY_URLS,
                         VERSION_JSON_MIRRORS)
from . import versioninfo
from .manifest import MCVersion, version_json


class InstallProgress:
    def __init__(self):
        self.lock = threading.Lock()
        self.done = 0
        self.total = 0
        self.stage = ""

    def add_total(self, n: int):
        with self.lock:
            self.total += n

    def add_done(self, n: int):
        with self.lock:
            self.done += n

    def ratio(self) -> float:
        with self.lock:
            return (self.done / self.total) if self.total else 0.0


def is_installed(game_dir: str, vid: str) -> bool:
    jar = os.path.join(game_dir, "versions", vid, f"{vid}.jar")
    return os.path.exists(jar)


def list_installed(game_dir: str) -> List[str]:
    vdir = os.path.join(game_dir, "versions")
    if not os.path.isdir(vdir):
        return []
    out = []
    for name in os.listdir(vdir):
        d = os.path.join(vdir, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, f"{name}.jar")):
            out.append(name)
    return sorted(out, reverse=True)


def install_version(game_dir: str, version: MCVersion, vdata: Dict,
                    progress: Optional[Callable[[float, str], None]] = None,
                    stage_cb: Optional[Callable[[str], None]] = None,
                    cancel: Optional[threading.Event] = None) -> bool:
    """完整安装一个版本：客户端 jar + 库 + 资产。返回是否成功。"""
    vid = version.id
    vdir = os.path.join(game_dir, "versions", vid)
    os.makedirs(vdir, exist_ok=True)

    # 1. 客户端 jar
    client = vdata.get("downloads", {}).get("client", {})
    if not client:
        raise utils.DownloadError(f"版本 {vid} 缺少客户端下载信息")
    stage_cb and stage_cb(f"[1/3] 下载客户端 jar")
    jar_urls = [client.get("url", "")]
    jar_urls.append(f"https://bmclapi2.bangbang93.com/version/{vid}/client")
    jar_path = os.path.join(vdir, f"{vid}.jar")
    utils.try_download([u for u in jar_urls if u], jar_path,
                       expected_sha1=client.get("sha1"))
    progress and progress(0.10, "client")

    # 2. 库（含 natives 压缩包）
    libs = [l for l in vdata.get("libraries", []) if versioninfo.library_ok(l)]
    total_steps = 1 + len(libs) + 1
    done_steps = 1
    native_jars: List[tuple] = []   # (jar_path, natives_dest)
    for i, lib in enumerate(libs):
        if cancel and cancel.is_set():
            raise utils.DownloadError("已取消")
        stage_cb and stage_cb(f"[2/3] 下载依赖库 {i+1}/{len(libs)}")
        rel = versioninfo.library_path(lib)
        dest = os.path.join(game_dir, "libraries", rel)
        url = LIBRARY_URLS[0].format(path=rel)
        mirror = LIBRARY_URLS[1].format(path=rel)
        utils.try_download([url, mirror], dest,
                           expected_sha1=versioninfo.library_sha1(lib))
        if versioninfo.natives_jar(lib):
            native_jars.append((dest, os.path.join(vdir, "natives")))
        progress and progress(0.10 + 0.75 * (done_steps / total_steps), f"lib:{rel}")
        done_steps += 1

    # 2.5 解压 natives（LWJGL 等原生库），不处理则游戏无法启动
    if native_jars:
        stage_cb and stage_cb("[2.5/3] 解压原生库 (natives)")
        natives_dir = os.path.join(vdir, "natives")
        os.makedirs(natives_dir, exist_ok=True)
        for jar_path, _ in native_jars:
            if not os.path.exists(jar_path):
                continue
            try:
                utils.extract_zip_file(jar_path, natives_dir)
            except Exception:
                # 某些库并非 zip（如 pom / 无 natives），静默跳过
                pass

    # 3. 资产（asset index + objects）
    stage_cb and stage_cb("[3/3] 下载游戏资产")
    assets = vdata.get("assetIndex", {})
    if assets and assets.get("url"):
        index_dir = os.path.join(game_dir, "assets", "indexes")
        os.makedirs(index_dir, exist_ok=True)
        idx_path = os.path.join(index_dir, f"{assets.get('id','legacy')}.json")
        idx_urls = [assets["url"]]
        idx_urls.append(ASSET_INDEX_MIRRORS[1].format(id=assets.get("id", ""), sha1=assets.get("sha1", "")))
        utils.try_download(idx_urls, idx_path, expected_sha1=assets.get("sha1"))
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                index = utils.json_loads(f.read())
        except Exception:
            index = None
        if index:
            objs = index.get("objects", {})
            obj_dir = os.path.join(game_dir, "assets", "objects")
            keys = list(objs.keys())
            for j, (name, obj) in enumerate(objs.items()):
                if cancel and cancel.is_set():
                    raise utils.DownloadError("已取消")
                h = obj.get("hash", "")
                if not h:
                    continue
                dest = os.path.join(obj_dir, h[:2], h)
                if os.path.exists(dest) and utils.sha1_file(dest) == h:
                    continue
                urls = [ASSET_OBJECT_URLS[0].format(prefix=h[:2], hash=h),
                        ASSET_OBJECT_URLS[1].format(hash=h)]
                try:
                    utils.try_download(urls, dest, expected_sha1=h)
                except utils.DownloadError:
                    pass  # 单个资产失败不阻断
                if progress and (j % 20 == 0 or j == len(keys) - 1):
                    progress(0.85 + 0.15 * ((j + 1) / len(keys)), f"asset:{j+1}/{len(keys)}")
    progress and progress(1.0, "done")
    return True


def ensure_version_json(game_dir: str, version: MCVersion) -> Dict:
    """确保 versions/<id>/<id>.json 存在并返回其内容."""
    vdir = os.path.join(game_dir, "versions", version.id)
    os.makedirs(vdir, exist_ok=True)
    vj = os.path.join(vdir, f"{version.id}.json")
    data = None
    if os.path.exists(vj):
        try:
            with open(vj, "r", encoding="utf-8") as f:
                data = utils.json_loads(f.read())
        except Exception:
            data = None
    if data is None:
        data = version_json(version)
        with open(vj, "w", encoding="utf-8") as f:
            f.write(utils.json_dumps(data))
    return data
