# -*- coding: utf-8 -*-
"""光影包（Shaderpacks）管理：Modrinth 光影搜索 + 本地 shaderpacks 目录管理."""
import os
import shutil
from dataclasses import dataclass
from typing import List, Optional

from .. import utils
from ..constants import MODRINTH_API
from .github_source import ModFile


@dataclass
class LocalShader:
    name: str
    path: str
    size: int
    enabled: bool = True

    def display(self) -> str:
        return self.name


def shaderpacks_dir(game_dir: str) -> str:
    return os.path.join(game_dir, "shaderpacks")


class ShaderManager:
    def __init__(self, game_dir: str):
        self.dir = shaderpacks_dir(game_dir)

    def scan(self) -> List[LocalShader]:
        if not os.path.isdir(self.dir):
            return []
        out = []
        for name in sorted(os.listdir(self.dir)):
            path = os.path.join(self.dir, name)
            if os.path.isfile(path):
                out.append(LocalShader(name=name, path=path, size=os.path.getsize(path), enabled=True))
            elif os.path.isdir(path) and not name.startswith("."):
                size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(path) for f in fs)
                out.append(LocalShader(name=name, path=path, size=size, enabled=True))
        return out

    def install(self, src: str, filename: str = "") -> str:
        os.makedirs(self.dir, exist_ok=True)
        name = filename or os.path.basename(src)
        dest = os.path.join(self.dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copyfile(src, dest)
        return dest

    def remove(self, shader: LocalShader):
        if os.path.isdir(shader.path) and not os.path.isfile(shader.path):
            shutil.rmtree(shader.path, ignore_errors=True)
        elif os.path.exists(shader.path):
            os.remove(shader.path)


class ModrinthShaders:
    """从 Modrinth 搜索光影包（project_type=shader）。"""

    def search(self, query: str, game_version: str = "", limit: int = 20) -> List[dict]:
        import requests
        facets = [["project_type:shader"]]
        if game_version:
            facets.append([f"versions:{game_version}"])
        r = requests.get(f"{MODRINTH_API}/search",
                         params={"query": query, "limit": limit, "index": "relevance",
                                 "facets": utils.json_dumps(facets)},
                         headers={"User-Agent": "NebulaLauncher/1.0"}, timeout=30)
        r.raise_for_status()
        return r.json().get("hits", [])

    def versions(self, project_id: str, game_version: str = "") -> List[dict]:
        import requests
        params = {"game_versions": "[]"}
        if game_version:
            params["game_versions"] = utils.json_dumps([game_version])
        r = requests.get(f"{MODRINTH_API}/project/{project_id}/version",
                         params=params, headers={"User-Agent": "NebulaLauncher/1.0"}, timeout=30)
        r.raise_for_status()
        return r.json()

    def pick_file(self, version_info: dict) -> Optional[ModFile]:
        for f in version_info.get("files", []):
            if f.get("primary") and f["filename"].endswith((".zip", ".jar")):
                return ModFile(name=f["filename"], size=f.get("size", 0), url=f["url"],
                               version=version_info.get("version_number", ""),
                               source="modrinth", project=version_info.get("project_id", ""))
        for f in version_info.get("files", []):
            if f["filename"].endswith((".zip", ".jar")):
                return ModFile(name=f["filename"], size=f.get("size", 0), url=f["url"],
                               version=version_info.get("version_number", ""),
                               source="modrinth", project=version_info.get("project_id", ""))
        return None

    def download(self, mod: ModFile, dest_dir: str, progress=None) -> str:
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, mod.name)
        utils.try_download([mod.url], dest, progress=progress)
        return dest
