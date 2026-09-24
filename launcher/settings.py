# -*- coding: utf-8 -*-
"""用户设置持久化（config.json）."""
import json
import os
import threading

from .constants import minecraft_dir, GITHUB_MODS_REPO

DEFAULTS = {
    "language": "zh_CN",
    "username": "Steve",
    "ram_mb": 4096,
    "max_ram_mb": 0,               # 0 = 不限制上限
    "java_path": "",               # 空 = 自动检测/下载
    "game_dir": "",                # 空 = 默认 .minecraft
    "auto_close": True,            # 启动游戏后自动关闭启动器
    "close_game_dir": True,        # 游戏进程独立于启动器继续运行
    "theme": "dark",
    "accent": "#3D8BFF",
    "github_mods_repo": GITHUB_MODS_REPO,
    "mod_source": "github",        # github | modrinth
    "last_version": "",
    "jvm_flags_extra": "",
    "mirror": "auto",              # auto | official | bmclapi
    "check_update": True,
    "show_news": True,
}


class Settings:
    def __init__(self, path: str = None):
        self._lock = threading.Lock()
        if path is None:
            base = os.path.join(os.path.expanduser("~"), ".nebulalauncher")
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "config.json")
        self.path = path
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    self.data.update(saved)
            except Exception:
                pass

    def save(self):
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        with self._lock:
            return self.data.get(key, default if default is not None else DEFAULTS.get(key))

    def set(self, key, value):
        with self._lock:
            self.data[key] = value
        self.save()

    def game_dir(self) -> str:
        gd = self.get("game_dir") or ""
        return gd if gd else minecraft_dir()

    def version_dir(self) -> str:
        return os.path.join(self.game_dir(), "versions")
