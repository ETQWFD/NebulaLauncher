# -*- coding: utf-8 -*-
"""Forge 安装（尽力而为）：下载官方 installer jar，以 --installClient 方式静默安装."""
import os
import subprocess
import tempfile
from typing import Optional

from .. import utils
from ..constants import FORGE_INSTALLER, FORGE_PROMOS


def forge_versions(mc: str):
    """查询某 MC 版本可用的 forge 版本号列表。"""
    try:
        data = utils.http_get_json(FORGE_PROMOS.format(mc=mc), timeout=25)
        out = []
        for k, v in data.items():
            if k.startswith(mc) and k != f"{mc}-latest" and k != f"{mc}-recommended":
                vnum = k[len(mc):].lstrip("-")
                out.append(vnum)
        # 推荐版本优先
        rec = data.get(f"{mc}-recommended")
        if rec:
            rec_v = str(rec).replace(f"{mc}-", "")
            if rec_v not in out:
                out.insert(0, rec_v)
        return out
    except Exception:
        return []


def install_forge(game_dir: str, mc: str, forge: str, java_path: str,
                  progress=None, stage_cb=None) -> str:
    """下载并静默运行 Forge 安装器，返回安装后的版本 id."""
    fver = f"{mc}-{forge}"
    vdir = os.path.join(game_dir, "versions", fver)
    if os.path.exists(os.path.join(vdir, f"{fver}.json")):
        return fver

    installer_url = FORGE_INSTALLER.format(forge=fver)
    with tempfile.TemporaryDirectory(prefix="forge_") as tmp:
        installer = os.path.join(tmp, "installer.jar")
        stage_cb and stage_cb("下载 Forge 安装器")
        utils.try_download([installer_url,
                            f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{fver}/forge-{fver}-installer.jar"],
                           installer)
        java = java_path or "java"
        stage_cb and stage_cb("运行 Forge 安装器（静默）")
        progress and progress(0.5, "forge-install")
        cmd = [java, "-jar", installer, "--installClient", game_dir]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            raise utils.DownloadError(f"Forge 安装失败: {proc.stderr[-500:]}")
    progress and progress(1.0, "forge-done")
    return fver
