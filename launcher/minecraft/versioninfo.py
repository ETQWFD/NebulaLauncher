# -*- coding: utf-8 -*-
"""版本信息解析：库(libraries)、参数(arguments)、资产索引、主类等."""
import os
import re
from typing import Dict, List, Optional, Tuple


def os_name() -> str:
    if os.name == "nt":
        return "windows"
    if sys_platform() == "mac":
        return "osx"
    return "linux"


def sys_platform() -> str:
    import platform
    p = platform.system().lower()
    return "mac" if "darwin" in p else p


def arch() -> str:
    import platform
    m = platform.machine().lower()
    return "64" if ("64" in m or "aarch64" in m or "arm64" in m) else "32"


def _feature_matcher(features: Optional[Dict[str, bool]]) -> bool:
    """1.17+ 新参数系统使用 features 决定参数是否启用。"""
    if not features:
        return True
    # 目前仅处理 is_demo_user / has_custom_resolution（均视为 False）
    for k, v in features.items():
        if v is False and k in ("is_demo_user", "has_custom_resolution"):
            continue
        if v is True and k in ("is_demo_user", "has_custom_resolution"):
            return False
    return True


def _rule_ok(rule: Dict) -> bool:
    action = rule.get("action", "allow")
    os_rule = rule.get("os", {})
    if os_rule:
        want = os_rule.get("name")
        if want and want != os_name():
            return action == "disallow"
        want_arch = os_rule.get("arch")
        if want_arch and want_arch != arch():
            return action == "disallow"
        # 部分规则限定版本号，如 os version
        ver = os_rule.get("version")
        if ver:
            return action == "disallow"
    return action == "allow"


def rules_ok(rules: Optional[List[Dict]]) -> bool:
    """按顺序应用 rules；空 rules 视为允许。"""
    if not rules:
        return True
    allowed = False
    for r in rules:
        if _rule_ok(r):
            allowed = r.get("action", "allow") == "allow"
    return allowed


def parse_arguments(vdata: Dict) -> Tuple[List[str], List[str]]:
    """返回 (game_args, jvm_args)。兼容 1.12-（minecraftArguments）与 1.13+（arguments）。"""
    game: List[str] = []
    jvm: List[str] = []
    args = vdata.get("arguments")
    if isinstance(args, dict):
        for chunk in args.get("game", []):
            if isinstance(chunk, str):
                game.append(chunk)
            elif isinstance(chunk, dict) and rules_ok(chunk.get("rules")) and _feature_matcher(chunk.get("features")):
                vals = chunk.get("value")
                if isinstance(vals, str):
                    game.append(vals)
                elif isinstance(vals, list):
                    game.extend(v for v in vals if isinstance(v, str))
        for chunk in args.get("jvm", []):
            if isinstance(chunk, str):
                jvm.append(chunk)
            elif isinstance(chunk, dict) and rules_ok(chunk.get("rules")):
                vals = chunk.get("value")
                if isinstance(vals, str):
                    jvm.append(vals)
                elif isinstance(vals, list):
                    jvm.extend(v for v in vals if isinstance(v, str))
    else:
        legacy = vdata.get("minecraftArguments", "")
        game = legacy.split(" ") if legacy else []
        jvm = ["-Djava.library.path=${natives_directory}",
               "-cp", "${classpath}"]
    return game, jvm


def library_ok(lib: Dict) -> bool:
    return rules_ok(lib.get("rules"))


def library_path(lib: Dict) -> str:
    """根据 library 的 name 计算出 maven 路径."""
    name = lib.get("name", "")
    download = lib.get("downloads", {}).get("artifact", {})
    if download.get("path"):
        return download["path"]
    parts = name.split(":")
    if len(parts) < 3:
        return name
    group, artifact, version = parts[0], parts[1], parts[2]
    # 处理 classifier 版本（version-classifier）
    classifier = None
    if lib.get("natives"):
        native = lib["natives"].get(os_name())
        if native:
            native = re.sub(r"\$<arch>", arch(), native)
            classifier = native
    if classifier:
        return f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}-{classifier}.jar"
    return f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.jar"


def library_sha1(lib: Dict) -> Optional[str]:
    return (lib.get("downloads", {}).get("artifact", {}) or {}).get("sha1")


def library_size(lib: Dict) -> int:
    return (lib.get("downloads", {}).get("artifact", {}) or {}).get("size", 0)


def natives_jar(lib: Dict) -> Optional[str]:
    """返回需要解压 natives 的库路径（如 lwjgl-platform），没有则 None."""
    if lib.get("natives"):
        return library_path(lib)
    return None
