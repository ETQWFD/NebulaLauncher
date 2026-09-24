# -*- coding: utf-8 -*-
"""整合包（Modpack）安装：Modrinth 整合包下载解析 + 本地 zip/mrpack 导入.
整合包解析后：所有模组文件按哈希写入 mods/，overrides 覆盖到游戏目录。
"""
import io
import os
import shutil
import zipfile
from typing import Callable, Dict, List, Optional

from .. import utils
from ..constants import MODRINTH_API


class ModpackInstaller:
    """解析并安装整合包。"""

    def __init__(self, game_dir: str):
        self.game_dir = game_dir

    # ------------------------------------------------------------------
    # 搜索 Modrinth 整合包
    # ------------------------------------------------------------------
    @staticmethod
    def search(query: str, limit: int = 20) -> List[dict]:
        facets = utils.json_dumps([["project_type:modpack"]])
        data = utils.http_get_json(
            f"{MODRINTH_API}/search",
            params={"query": query, "limit": limit,
                    "index": "downloads", "facets": facets})
        return data.get("hits", [])

    @staticmethod
    def versions(project_id: str) -> List[dict]:
        return utils.http_get_json(f"{MODRINTH_API}/project/{project_id}/version")

    @staticmethod
    def version_file(version_info: dict) -> Optional[dict]:
        for f in version_info.get("files", []):
            if f.get("filename", "").endswith(".mrpack"):
                return f
        return None

    # ------------------------------------------------------------------
    # 安装
    # ------------------------------------------------------------------
    def install_mrpack_bytes(self, data: bytes, name: str = "modpack",
                             progress: Optional[Callable[[float, str], None]] = None,
                             stage_cb: Optional[Callable[[str], None]] = None,
                             cancel=None) -> Dict:
        """从 .mrpack 字节流安装整合包。"""
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            idx_name = "modrinth.index.json"
            if idx_name not in names:
                # 兼容老格式 index.json
                idx_name = "index.json"
            index = utils.json_loads(z.read(idx_name).decode("utf-8"))
            overrides = [n for n in names if n.startswith("overrides/")]

            files = index.get("files", [])
            mods_dir = os.path.join(self.game_dir, "mods")
            os.makedirs(mods_dir, exist_ok=True)
            total = len(files)
            for i, f in enumerate(files):
                if cancel and cancel.is_set():
                    raise utils.DownloadError("已取消")
                stage_cb and stage_cb(f"下载模组 {i + 1}/{total}")
                rel = f.get("path", "")
                if not rel:
                    continue
                dest = os.path.join(mods_dir, os.path.basename(rel))
                sha1 = (f.get("hashes") or {}).get("sha1")
                # 已存在且校验一致则跳过
                if os.path.exists(dest) and sha1 and utils.sha1_file(dest) == sha1:
                    progress and progress((i + 1) / max(total, 1), f"skip:{os.path.basename(rel)}")
                    continue
                urls = f.get("downloads") or []
                try:
                    utils.try_download([u for u in urls if u], dest,
                                       expected_sha1=sha1)
                except utils.DownloadError:
                    pass  # 单个失败继续
                progress and progress((i + 1) / max(total, 1), os.path.basename(rel))

            # 应用 overrides
            if overrides:
                stage_cb and stage_cb("应用整合包覆盖文件")
                for n in overrides:
                    if cancel and cancel.is_set():
                        raise utils.DownloadError("已取消")
                    rel = n[len("overrides/"):]
                    if not rel:
                        continue
                    target = os.path.join(self.game_dir, rel)
                    if n.endswith("/"):
                        os.makedirs(target, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(n) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)

            deps = index.get("dependencies", {})
            return {
                "name": index.get("name", name),
                "mc": deps.get("minecraft", ""),
                "loader": deps.get("fabric-loader") or deps.get("quilt-loader") or deps.get("forge", ""),
                "mods": len(files),
                "overrides": len(overrides),
            }

    def install_mrpack_file(self, path: str, **kw) -> Dict:
        with open(path, "rb") as f:
            return self.install_mrpack_bytes(f.read(), name=os.path.basename(path), **kw)

    @staticmethod
    def download_mrpack(version_info: dict, dest_dir: str) -> str:
        f = ModpackInstaller.version_file(version_info)
        if not f:
            raise utils.DownloadError("该版本没有 .mrpack 文件")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, f["filename"])
        utils.try_download([u for u in f.get("urls", []) if u], dest,
                           expected_sha1=(f.get("hashes") or {}).get("sha1"))
        return dest
