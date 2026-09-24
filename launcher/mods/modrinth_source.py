# -*- coding: utf-8 -*-
"""模组源：Modrinth（官方主流模组平台，开放 API）。"""
from typing import List, Optional

from .. import utils
from ..constants import MODRINTH_API
from .github_source import ModFile


class ModrinthSource:
    """Modrinth 搜索与版本获取。"""

    def __init__(self):
        self._headers = {"User-Agent": "NebulaLauncher/1.0 (contact: github.com/et2416444244)"}

    def search(self, query: str, game_version: str = "", limit: int = 20,
               loader: str = "") -> List[dict]:
        import requests
        facets = []
        if game_version:
            facets.append([f"versions:{game_version}"])
        if loader:
            facets.append([f"categories:{loader}"])
        params = {"query": query, "limit": limit, "index": "relevance"}
        if facets:
            params["facets"] = utils.json_dumps(facets)
        r = requests.get(f"{MODRINTH_API}/search", params=params,
                         headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json().get("hits", [])

    def versions(self, project_id: str, game_version: str = "",
                 loader: str = "") -> List[dict]:
        import requests
        params = {"loaders": "[]", "game_versions": "[]"}
        if game_version:
            params["game_versions"] = utils.json_dumps([game_version])
        if loader:
            params["loaders"] = utils.json_dumps([loader])
        r = requests.get(f"{MODRINTH_API}/project/{project_id}/version",
                         params=params, headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def pick_file(self, version_info: dict) -> Optional[ModFile]:
        """从某版本信息里挑一个主文件（.jar）。"""
        for f in version_info.get("files", []):
            if f.get("primary") and f["filename"].endswith(".jar"):
                return ModFile(name=f["filename"], size=f.get("size", 0),
                               url=f["url"], version=version_info.get("version_number", ""),
                               source="modrinth", project=version_info.get("project_id", ""),
                               downloads=version_info.get("downloads", 0))
        for f in version_info.get("files", []):
            if f["filename"].endswith(".jar"):
                return ModFile(name=f["filename"], size=f.get("size", 0),
                               url=f["url"], version=version_info.get("version_number", ""),
                               source="modrinth", project=version_info.get("project_id", ""))
        return None

    def download(self, mod: ModFile, dest_dir: str, progress=None) -> str:
        import os
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, mod.name)
        utils.try_download([mod.url], dest, progress=progress)
        return dest
