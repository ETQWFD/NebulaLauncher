# -*- coding: utf-8 -*-
"""Java 运行时管理：自动检测、下载 Temurin JDK."""
import os
import platform
import re
import subprocess
import sys
import tarfile
import zipfile

from . import utils
from .constants import JAVA_API, ROOT


def system_java() -> str:
    """检测系统 PATH 中的 java，返回路径或空串。"""
    try:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10)
        return "java" if r.returncode == 0 else ""
    except Exception:
        return ""


def find_java(feature: int) -> str:
    """在常见目录查找可用的 java（可满足 feature 主版本）。"""
    candidates = []
    home = os.environ.get("JAVA_HOME", "")
    if home:
        candidates.append(os.path.join(home, "bin", "java.exe" if os.name == "nt" else "java"))
    candidates.append(system_java())
    # 启动器自带运行时目录
    runtime_dir = os.path.join(ROOT, "runtime")
    if os.path.isdir(runtime_dir):
        for name in sorted(os.listdir(runtime_dir), reverse=True):
            base = os.path.join(runtime_dir, name, "bin",
                                "java.exe" if os.name == "nt" else "java")
            candidates.append(base)
    for c in candidates:
        if c and os.path.exists(c):
            v = _major(c)
            if v and v >= feature:
                return c
    return ""


def _major(java_path: str) -> int:
    try:
        r = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=15)
        text = r.stderr or r.stdout or ""
        m = re.search(r'version "([^"]+)"', text)
        if m:
            ver = m.group(1)
            if ver.startswith("1."):
                return int(ver.split(".")[1])
            return int(ver.split(".")[0])
    except Exception:
        pass
    return 0


def _os_key() -> str:
    if os.name == "nt":
        return "windows"
    return "mac" if sys.platform == "darwin" else "linux"


def _arch_key() -> str:
    m = platform.machine().lower()
    if "aarch64" in m or "arm64" in m:
        return "aarch64"
    return "x64" if "64" in m else "x32"


def download_java(feature: int, progress=None, stage_cb=None) -> str:
    """下载并解压 Temurin JDK 到 runtime/，返回 java 可执行文件路径。"""
    url = JAVA_API.format(feature=feature, os=_os_key(), arch=_arch_key())
    runtime_dir = os.path.join(ROOT, "runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    stage_cb and stage_cb(f"下载 Java {feature}（Temurin）")
    archive = os.path.join(runtime_dir, f"jdk-{feature}.tmp")
    try:
        utils.try_download([url], archive, progress=progress)
        target = os.path.join(runtime_dir, f"jdk-{feature}")
        os.makedirs(target, exist_ok=True)
        if archive.endswith(".zip") or zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as z:
                z.extractall(target)
        else:
            with tarfile.open(archive, "r:*") as t:
                t.extractall(target, filter="data")
        # 找到解压后的 java
        for root, dirs, files in os.walk(target):
            for f in files:
                if f == "java" or f == "java.exe":
                    return os.path.join(root, f)
        raise utils.DownloadError("Java 解压后未找到可执行文件")
    finally:
        if os.path.exists(archive):
            try:
                os.remove(archive)
            except OSError:
                pass
