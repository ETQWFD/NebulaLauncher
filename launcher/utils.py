# -*- coding: utf-8 -*-
"""通用工具：下载、SHA1、线程池、进度回调、网络重试、打开文件夹."""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

import requests

from .constants import GITHUB_API_PROXY, GITHUB_DL_PROXY

_UA = {"User-Agent": "NebulaLauncher/1.2 (+https://github.com/ETQWFD/NebulaLauncher)"}

# 每次请求的最大重试次数（同一 URL）
MAX_ATTEMPTS = 3
# 默认超时（连接, 读取）
DEFAULT_TIMEOUT = (10, 40)


def json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return json.loads(text.lstrip("\ufeff"))


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


class DownloadError(Exception):
    pass


def _request(session, method: str, url: str, timeout=DEFAULT_TIMEOUT, **kw):
    """带重试的请求；网络异常自动重试 MAX_ATTEMPTS 次。"""
    last = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = (session or requests).request(method, url, headers=_UA, timeout=timeout, **kw)
            return r
        except Exception as e:
            last = e
    raise DownloadError(f"网络请求失败（已重试 {MAX_ATTEMPTS} 次）: {url} ({last})")


def http_get_bytes(url: str, timeout=DEFAULT_TIMEOUT, session: Optional[requests.Session] = None,
                   max_redirects: int = 3, **kw) -> bytes:
    s = session or requests
    for _ in range(max_redirects):
        r = _request(s, "GET", url, timeout=timeout, **kw)
        if r.status_code == 200:
            return r.content
        if r.status_code in (301, 302, 303, 307, 308):
            url = r.headers.get("Location", "")
            if not url:
                break
            continue
        raise DownloadError(f"HTTP {r.status_code}: {url}")
    raise DownloadError(f"重定向过多: {url}")


def http_get_json(url: str, timeout=DEFAULT_TIMEOUT, session: Optional[requests.Session] = None,
                  **kw):
    raw = http_get_bytes(url, timeout, session, **kw)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return json.loads(raw.decode("utf-8-sig"))


def github_api_get(url: str, token: str = "") -> dict:
    """访问 GitHub API：带 UA、可配代理前缀、自动重试；403/404 报友好错误。"""
    proxy = (GITHUB_API_PROXY or "").strip()
    target = url
    if proxy:
        target = proxy.rstrip("/") + "/" + url.lstrip("/")
    headers = dict(_UA)
    if token:
        headers["Authorization"] = f"token {token}"
    last = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = requests.get(target, headers=headers, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 403:
                raise DownloadError("GitHub API 访问受限（403，匿名限流）。可稍后重试或在代码中配置令牌。")
            if r.status_code == 404:
                raise DownloadError("GitHub 仓库不存在或名称拼写错误（404）。请在「设置」中检查仓库地址。")
            last = DownloadError(f"HTTP {r.status_code}: {url}")
        except DownloadError:
            raise
        except Exception as e:
            last = e
    raise DownloadError(f"GitHub 访问失败（已重试 {MAX_ATTEMPTS} 次）: {url} ({last})")


def proxied_url(url: str) -> str:
    """若配置了 GitHub 下载代理，则把 github.com 资产链接换成代理前缀。"""
    proxy = (GITHUB_DL_PROXY or "").strip()
    if proxy and url.startswith("https://github.com/"):
        return proxy.rstrip("/") + "/" + url.lstrip("/")
    return url


def sha1_of(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def try_download(urls: List[str], dest: str, expected_sha1: Optional[str] = None,
                 progress: Optional[Callable[[int, int], None]] = None,
                 session: Optional[requests.Session] = None) -> bool:
    """依次尝试多个镜像 URL 下载到 dest（带 SHA1 校验、超时重试与进度回调）。"""
    if os.path.exists(dest):
        if expected_sha1 is None or sha1_file(dest) == expected_sha1:
            return True
        try:
            os.remove(dest)
        except OSError:
            pass
    last_err = None
    for url in urls:
        url = proxied_url(url)
        for attempt in range(MAX_ATTEMPTS):
            try:
                s = session or requests
                with s.get(url, headers=_UA, timeout=DEFAULT_TIMEOUT, stream=True) as r:
                    if r.status_code != 200:
                        raise DownloadError(f"HTTP {r.status_code}")
                    total = int(r.headers.get("Content-Length") or 0)
                    done = 0
                    tmp = dest + ".part"
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1 << 16):
                            if chunk:
                                f.write(chunk)
                                done += len(chunk)
                                if progress and total:
                                    progress(done, total)
                    if expected_sha1 and sha1_file(tmp) != expected_sha1:
                        raise DownloadError("SHA1 校验失败")
                    os.replace(tmp, dest)
                    if progress:
                        progress(total, total)
                    return True
            except Exception as e:
                last_err = e
                continue
    raise DownloadError(f"全部镜像下载失败: {last_err}")


def extract_zip(data: bytes, dest: str, filter_prefix: Optional[str] = None):
    """解压 zip 字节流到 dest（可只解压某个前缀下的文件，用于 natives 处理）。"""
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if filter_prefix and not name.startswith(filter_prefix):
                continue
            target = os.path.join(dest, name)
            if name.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return dest


def extract_zip_file(zip_path: str, dest: str):
    """从本地 zip 文件解压到 dest。"""
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name.endswith("/"):
                continue
            target = os.path.join(dest, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def open_folder(path: str) -> bool:
    """跨平台打开文件管理器显示指定文件夹。"""
    if not path or not os.path.exists(path):
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def parallel_map(fn: Callable, items: List, workers: int = 8):
    """简单的并行执行（返回每个 item 的结果，异常被捕获返回）。"""
    results = {}
    lock = threading.Lock()
    def run(item):
        try:
            r = fn(item)
        except Exception as e:
            r = e
        with lock:
            results[id(item)] = r
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run, it) for it in items]
        for f in futures:
            f.result()
    return [results[id(it)] for it in items]
