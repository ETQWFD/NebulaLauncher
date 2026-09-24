# -*- coding: utf-8 -*-
"""Nebula Launcher 全局常量与路径定义."""
import os
import sys

APP_NAME = "Nebula Launcher"
APP_NAME_CN = "星云启动器"
APP_VERSION = "1.2.0"
APP_TAG = "v1.2.0"

def app_dir() -> str:
    """启动器自身所在目录（兼容打包后的 exe）。"""
    if getattr(sys, "frozen", False):          # PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROOT = app_dir()
I18N_DIR = os.path.join(ROOT, "i18n")
ASSETS_DIR = os.path.join(ROOT, "assets")

def minecraft_dir() -> str:
    """默认 .minecraft 目录（可在设置里修改）。"""
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, ".minecraft")
    return os.path.join(os.path.expanduser("~"), ".minecraft")

# ---------------------------------------------------------------------------
# 网络源（BMCLAPI 镜像优先：国内更快更稳；官方源作为兜底，全球可用）
# ---------------------------------------------------------------------------
MANIFEST_URLS = [
    "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json",
    "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
    "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
]
VERSION_JSON_MIRRORS = [
    "https://bmclapi2.bangbang93.com/version/{id}/json",
    "https://piston-meta.mojang.com/v1/packages/{sha1}/{id}.json",
]
ASSET_INDEX_MIRRORS = [
    "https://bmclapi2.bangbang93.com/indexes/{id}/{sha1}.json",
    "https://piston-meta.mojang.com/v1/packages/{sha1}/{id}.json",
]
ASSET_OBJECT_URLS = [
    "https://bmclapi2.bangbang93.com/assets/{hash}",
    "https://resources.download.minecraft.net/{prefix}/{hash}",
]
LIBRARY_URLS = [
    "https://bmclapi2.bangbang93.com/maven/{path}",
    "https://libraries.minecraft.net/{path}",
]

# Fabric / Quilt / Forge 元数据
FABRIC_META = "https://meta.fabricmc.net/v2"
QUILT_META = "https://meta.quiltmc.org/v3"
FORGE_PROMOS = "https://bmclapi2.bangbang93.com/forge/minecraft/{mc}/promos.json"
FORGE_INSTALLER = "https://maven.minecraftforge.net/net/minecraftforge/forge/{forge}/forge-{forge}-installer.jar"

# Java 自动下载（Adoptium Temurin）
JAVA_API = "https://api.adoptium.net/v3/binary/latest/{feature}/ga/{os}/{arch}/jdk/hotspot/normal/eclipse?project=jdk"

# Modrinth 官方模组源
MODRINTH_API = "https://api.modrinth.com/v2"
# GitHub Release 模组源（默认指向用户的模组仓库，可在设置中修改）
GITHUB_MODS_REPO = "ETQWFD/NebulaLauncher-Mods"

# GitHub API / 下载代理前缀（国内网络加速；可留空=直连；示例：https://ghfast.top/、https://ghproxy.net/）
GITHUB_DL_PROXY = os.environ.get("NEBULA_GH_PROXY", "")   # 下载 GitHub 资产时前置代理
GITHUB_API_PROXY = os.environ.get("NEBULA_GH_API", "")    # 访问 GitHub API 时前置代理

# 默认 JVM 内存优化参数（Aikar's Flags 精简版 + 常见优化项）
DEFAULT_JVM_FLAGS = [
    "-XX:+UseG1GC",
    "-XX:+ParallelRefProcEnabled",
    "-XX:MaxGCPauseMillis=200",
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+DisableExplicitGC",
    "-XX:+AlwaysPreTouch",
    "-XX:G1NewSizePercent=30",
    "-XX:G1MaxNewSizePercent=40",
    "-XX:G1HeapRegionSize=8M",
    "-XX:G1ReservePercent=20",
    "-XX:G1HeapWastePercent=5",
    "-XX:G1MixedGCCountTarget=4",
    "-XX:InitiatingHeapOccupancyPercent=15",
    "-XX:G1MixedGCLiveThresholdPercent=90",
    "-XX:G1RSetUpdatingPauseTimePercent=5",
    "-XX:SurvivorRatio=32",
    "-XX:+PerfDisableSharedMem",
    "-XX:MaxTenuringThreshold=1",
    "-XX:CompileThreshold=1500",
    "-Dusing.aikars.flags=https://mcflags.emc.gs",
    "-Daikars.new.flags=true",
    "-Dlog4j2.formatMsgNoLookups=true",   # log4shell 防护
]
