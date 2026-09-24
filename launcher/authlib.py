# -*- coding: utf-8 -*-
"""自定义服务器账号（authlib-injector）：皮肤站/自定义服务器登录.
原理：下载 authlib-injector（Java agent），把 Mojang 认证重定向到自定义服务器，
从而在游戏内获得该服务器的皮肤与披风。
"""
import os
import threading
from typing import Optional

from . import utils
from .constants import ROOT

# authlib-injector 官方发布（GitHub Releases 自动探测最新版）
AUTHLIB_API = "https://api.github.com/repos/yushijinhun/authlib-injector/releases/latest"
AUTHLIB_MIRROR = "https://authlib-injector.yushi.moe/artifact/latest.json"

_download_lock = threading.Lock()
_local_jar = ""


def authlib_jar() -> str:
    """返回本地 authlib-injector jar 路径（不存在则空）。"""
    global _local_jar
    if _local_jar:
        return _local_jar
    p = os.path.join(ROOT, "runtime", "authlib-injector.jar")
    if os.path.exists(p):
        _local_jar = p
        return p
    return ""


def download_authlib(progress=None, stage_cb=None) -> str:
    """下载 authlib-injector 到 runtime/，返回 jar 路径。"""
    global _local_jar
    with _download_lock:
        if _local_jar and os.path.exists(_local_jar):
            return _local_jar
        os.makedirs(os.path.join(ROOT, "runtime"), exist_ok=True)
        dest = os.path.join(ROOT, "runtime", "authlib-injector.jar")
        url = ""
        try:
            meta = utils.http_get_json(AUTHLIB_API, timeout=25)
            for a in meta.get("assets", []):
                if a.get("name", "").endswith(".jar"):
                    url = a.get("browser_download_url", "")
                    break
        except Exception:
            pass
        if not url:
            # 备用官方元数据
            try:
                meta = utils.http_get_json(AUTHLIB_MIRROR, timeout=25)
                url = meta.get("download_url", "") or meta.get("url", "")
            except Exception:
                pass
        if not url:
            raise utils.DownloadError("无法获取 authlib-injector 下载地址")
        stage_cb and stage_cb("下载 authlib-injector")
        utils.try_download([url], dest, progress=progress)
        _local_jar = dest
        return dest


def authlib_flag(jar_path: str, server_url: str) -> str:
    """生成 JVM 参数，把认证重定向到自定义服务器。"""
    return f"-javaagent:{jar_path}={server_url}"
