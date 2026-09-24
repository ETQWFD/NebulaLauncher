# -*- coding: utf-8 -*-
"""通用工具：下载、SHA1、线程池、进度回调."""
import hashlib
import io
import json
import os
import shutil
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

import requests

_UA = {"User-Agent": "NebulaLauncher/1.0 (+https://github.com/et2416444244/NebulaLauncher)"}


def json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return json.loads(text.lstrip("\ufeff"))


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


class DownloadError(Exception):
    pass


def http_get_bytes(url: str, timeout: int = 30, session: Optional[requests.Session] = None,
                   max_redirects: int = 3) -> bytes:
    s = session or requests
    for _ in range(max_redirects):
        r = s.get(url, headers=_UA, timeout=timeout)
        if r.status_code == 200:
            return r.content
        if r.status_code in (301, 302, 303, 307, 308):
            url = r.headers.get("Location", "")
            if not url:
                break
            continue
        raise DownloadError(f"HTTP {r.status_code}: {url}")
    raise DownloadError(f"重定向过多: {url}")


def http_get_json(url: str, timeout: int = 30, session: Optional[requests.Session] = None):
    raw = http_get_bytes(url, timeout, session)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return json.loads(raw.decode("utf-8-sig"))


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
    """依次尝试多个镜像 URL 下载到 dest（带 SHA1 校验与进度回调），返回是否成功."""
    if os.path.exists(dest):
        if expected_sha1 is None or sha1_file(dest) == expected_sha1:
            return True
        # 校验失败说明文件损坏，重新下载
        try:
            os.remove(dest)
        except OSError:
            pass
    last_err = None
    for url in urls:
        try:
            s = session or requests
            with s.get(url, headers=_UA, timeout=60, stream=True) as r:
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
