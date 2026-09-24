# -*- coding: utf-8 -*-
"""模组源：GitHub Releases（用户自己的模组仓库，经 release 上传分发）。"""
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .. import utils


@dataclass
class ModFile:
    name: str
    size: int
    url: str
    version: str = ""          # 所属 release 标签
    source: str = "github"
    project: str = ""          # 所属项目/仓库
    downloads: int = 0
    description: str = ""


@dataclass
class GithubRelease:
    tag: str
    name: str
    published: str
    body: str = ""
    assets: List[ModFile] = field(default_factory=list)


class GithubModSource:
    """从 GitHub Releases 拉取模组列表与下载。默认仓库可在设置中修改。"""

    def __init__(self, repo: str, token: str = ""):
        self.repo = repo.strip().strip("/")
        self.token = token
        self._headers = {"User-Agent": "NebulaLauncher/1.0"}
        if token:
            self._headers["Authorization"] = f"token {token}"

    def releases(self, per_page: int = 30) -> List[GithubRelease]:
        """获取 releases 及其模组资产（.jar 文件）。"""
        import requests
        url = f"https://api.github.com/repos/{self.repo}/releases?per_page={per_page}"
        r = requests.get(url, headers=self._headers, timeout=30)
        if r.status_code == 403:
            raise utils.DownloadError(
                "GitHub API 访问受限（403，通常是匿名限流）。可在「设置」中为该仓库配置令牌，或稍后重试。")
        if r.status_code != 200:
            raise utils.DownloadError(f"GitHub 仓库访问失败 ({r.status_code}): {self.repo}")
        out = []
        for rel in r.json():
            assets = []
            for a in rel.get("assets", []):
                if a.get("name", "").endswith(".jar"):
                    assets.append(ModFile(
                        name=a["name"], size=a.get("size", 0),
                        url=a.get("browser_download_url", ""),
                        version=rel.get("tag_name", ""),
                        source="github", project=self.repo,
                        downloads=a.get("download_count", 0),
                    ))
            out.append(GithubRelease(
                tag=rel.get("tag_name", ""),
                name=rel.get("name") or rel.get("tag_name", ""),
                published=rel.get("published_at", ""),
                body=rel.get("body", "") or "",
                assets=assets,
            ))
        return out

    def download(self, mod: ModFile, dest_dir: str, progress=None) -> str:
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, mod.name)
        utils.try_download([mod.url], dest, progress=progress)
        return dest
