# -*- coding: utf-8 -*-
"""本地模组管理：扫描/启用/禁用/删除 .minecraft/mods 下的模组。"""
import os
import shutil
from dataclasses import dataclass
from typing import List


@dataclass
class LocalMod:
    name: str
    path: str
    size: int
    enabled: bool = True
    is_loader: bool = False     # 由安装器产生的 loader/核心文件（如 fabric-api 依赖）

    def display(self) -> str:
        return self.name


def mods_dir(game_dir: str) -> str:
    return os.path.join(game_dir, "mods")


class ModManager:
    def __init__(self, game_dir: str):
        self.dir = mods_dir(game_dir)

    def scan(self) -> List[LocalMod]:
        if not os.path.isdir(self.dir):
            return []
        out = []
        for name in sorted(os.listdir(self.dir)):
            path = os.path.join(self.dir, name)
            if not os.path.isfile(path):
                continue
            lower = name.lower()
            if lower.endswith(".jar"):
                out.append(LocalMod(name=name, path=path, size=os.path.getsize(path), enabled=True))
            elif lower.endswith(".jar.disabled"):
                out.append(LocalMod(name=name[:-9], path=path,
                                    size=os.path.getsize(path), enabled=False))
        return out

    def install(self, src: str, filename: str = "") -> str:
        """把已下载的模组文件放入 mods 目录，返回目标路径。"""
        os.makedirs(self.dir, exist_ok=True)
        name = filename or os.path.basename(src)
        dest = os.path.join(self.dir, name)
        shutil.copyfile(src, dest)
        return dest

    def toggle(self, mod: LocalMod) -> bool:
        """启用/禁用（.jar <-> .jar.disabled），返回新状态。"""
        if mod.enabled:
            new = mod.path + ".disabled"
            os.rename(mod.path, new)
            return False
        new = mod.path[:-9] if mod.path.endswith(".disabled") else mod.path
        os.rename(mod.path, new)
        return True

    def remove(self, mod: LocalMod):
        if os.path.exists(mod.path):
            os.remove(mod.path)
