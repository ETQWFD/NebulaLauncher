# -*- coding: utf-8 -*-
"""Fabric / Quilt 加载器安装：通过官方 meta 接口拉取 profile 并落地版本文件."""
import os
from typing import Optional

from .. import utils
from ..constants import FABRIC_META, QUILT_META


def _meta_json(base: str, path: str, timeout: int = 25):
    return utils.http_get_json(f"{base}/{path}", timeout=timeout)


def fabric_versions(mc: str):
    """可用的 fabric loader 版本列表（按时间倒序）。"""
    try:
        data = _meta_json(FABRIC_META, f"versions/loader/{mc}")
        return [d.get("loader", {}).get("version", "") for d in data if d.get("loader")]
    except Exception:
        return []


def quilt_versions(mc: str):
    try:
        data = _meta_json(QUILT_META, f"versions/loader/{mc}")
        return [d.get("loader", {}).get("version", "") for d in data if d.get("loader")]
    except Exception:
        return []


def install_fabric(game_dir: str, mc: str, loader: Optional[str] = None,
                   progress=None, stage_cb=None) -> str:
    """安装 Fabric 到指定版本目录，返回安装后的版本 id（fabric-loader-X-Y）。"""
    if not loader:
        vers = fabric_versions(mc)
        if not vers:
            raise utils.DownloadError(f"Fabric 不支持 Minecraft {mc}")
        loader = vers[0]
    profile = _meta_json(FABRIC_META, f"versions/loader/{mc}/{loader}/profile/json")
    vid = profile.get("id", f"fabric-loader-{loader}-{mc}")
    vdir = os.path.join(game_dir, "versions", vid)
    os.makedirs(vdir, exist_ok=True)
    # profile 本身即版本 JSON
    with open(os.path.join(vdir, f"{vid}.json"), "w", encoding="utf-8") as f:
        f.write(utils.json_dumps(profile))
    # 需要下载 loader jar 与 intermediary，安装程序一般会把它们放进 libraries
    libs = profile.get("libraries", [])
    for i, lib in enumerate(libs):
        stage_cb and stage_cb(f"下载 Fabric 依赖 {i+1}/{len(libs)}")
        art = lib.get("downloads", {}).get("artifact", {})
        if not art or not art.get("path"):
            continue
        rel = art["path"]
        dest = os.path.join(game_dir, "libraries", rel)
        if os.path.exists(dest) and utils.sha1_file(dest) == art.get("sha1"):
            continue
        urls = [art.get("url", ""),
                f"https://bmclapi2.bangbang93.com/maven/{rel}"]
        utils.try_download([u for u in urls if u], dest, expected_sha1=art.get("sha1"))
        progress and progress((i + 1) / len(libs), f"fabric-lib:{i}")
    return vid


def install_quilt(game_dir: str, mc: str, loader: Optional[str] = None,
                  progress=None, stage_cb=None) -> str:
    if not loader:
        vers = quilt_versions(mc)
        if not vers:
            raise utils.DownloadError(f"Quilt 不支持 Minecraft {mc}")
        loader = vers[0]
    profile = _meta_json(QUILT_META, f"versions/loader/{mc}/{loader}/profile/json")
    vid = profile.get("id", f"quilt-loader-{loader}-{mc}")
    vdir = os.path.join(game_dir, "versions", vid)
    os.makedirs(vdir, exist_ok=True)
    with open(os.path.join(vdir, f"{vid}.json"), "w", encoding="utf-8") as f:
        f.write(utils.json_dumps(profile))
    libs = profile.get("libraries", [])
    for i, lib in enumerate(libs):
        stage_cb and stage_cb(f"下载 Quilt 依赖 {i+1}/{len(libs)}")
        art = lib.get("downloads", {}).get("artifact", {})
        if not art or not art.get("path"):
            continue
        rel = art["path"]
        dest = os.path.join(game_dir, "libraries", rel)
        if os.path.exists(dest) and utils.sha1_file(dest) == art.get("sha1"):
            continue
        urls = [art.get("url", ""),
                f"https://bmclapi2.bangbang93.com/maven/{rel}"]
        utils.try_download([u for u in urls if u], dest, expected_sha1=art.get("sha1"))
        progress and progress((i + 1) / len(libs), f"quilt-lib:{i}")
    return vid
