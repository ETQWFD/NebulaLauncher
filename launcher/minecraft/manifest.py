# -*- coding: utf-8 -*-
"""Minecraft 版本清单（官方 + BMCLAPI 镜像）。"""
from typing import List, Optional

from .. import utils
from ..constants import MANIFEST_URLS


class MCVersion:
    def __init__(self, vid: str, vtype: str, release_time: str, url: str, sha1: str = ""):
        self.id = vid
        self.type = vtype            # release / snapshot / old_beta / old_alpha
        self.release_time = release_time
        self.url = url
        self.sha1 = sha1

    @property
    def is_release(self) -> bool:
        return self.type == "release"

    def __repr__(self):
        return f"<MCVersion {self.id} {self.type}>"


def fetch_manifest() -> List[MCVersion]:
    """获取版本清单；优先 release，保留快照与远古版本。"""
    manifest = None
    for url in MANIFEST_URLS:
        try:
            manifest = utils.http_get_json(url, timeout=25)
            break
        except Exception:
            continue
    if not manifest:
        raise utils.DownloadError("无法获取 Minecraft 版本清单（请检查网络）")

    versions = []
    for v in manifest.get("versions", []):
        versions.append(MCVersion(
            vid=v.get("id", ""),
            vtype=v.get("type", "release"),
            release_time=v.get("releaseTime", ""),
            url=v.get("url", ""),
            sha1=v.get("sha1", ""),
        ))
    versions.sort(key=lambda x: x.release_time, reverse=True)
    return versions


def latest_release(versions: List[MCVersion]) -> Optional[MCVersion]:
    for v in versions:
        if v.is_release:
            return v
    return versions[0] if versions else None


def version_json(version: MCVersion):
    """拉取版本 JSON（含库、参数、资产索引等）。"""
    last = None
    urls = [version.url]
    for u in urls:
        try:
            return utils.http_get_json(u, timeout=30)
        except Exception as e:
            last = e
    # 兜底：BMCLAPI 镜像
    for u in ["https://bmclapi2.bangbang93.com/version/{id}/json".format(id=version.id)]:
        try:
            return utils.http_get_json(u, timeout=30)
        except Exception as e:
            last = e
    raise utils.DownloadError(f"无法获取版本信息: {version.id} ({last})")
