# -*- coding: utf-8 -*-
"""游戏启动核心：拼装 classpath / natives / JVM 参数并拉起 Minecraft 进程."""
import os
import shutil
import subprocess
import sys
import time
import uuid
from typing import Dict, List, Optional

from .. import utils
from ..constants import DEFAULT_JVM_FLAGS
from . import versioninfo


def _natives_jar_rel(lib: Dict) -> Optional[str]:
    if lib.get("natives"):
        return versioninfo.library_path(lib)
    return None


def prepare_classpath(game_dir: str, vdata: Dict, vid: str) -> str:
    """收集 libraries 中所有 .jar 的绝对路径并拼接 classpath."""
    jars = []
    for lib in vdata.get("libraries", []):
        if not versioninfo.library_ok(lib):
            continue
        rel = versioninfo.library_path(lib)
        path = os.path.join(game_dir, "libraries", rel)
        if os.path.exists(path) and path.endswith(".jar"):
            jars.append(path)
    client_jar = os.path.join(game_dir, "versions", vid, f"{vid}.jar")
    jars.append(client_jar)
    return os.pathsep.join(jars)


def extract_natives(game_dir: str, vdata: Dict, vid: str) -> str:
    """解压各平台原生库到 versions/<id>/natives，返回该目录."""
    natives_dir = os.path.join(game_dir, "versions", vid, "natives")
    os.makedirs(natives_dir, exist_ok=True)
    changed = False
    for lib in vdata.get("libraries", []):
        rel = _natives_jar_rel(lib)
        if not rel:
            continue
        jar = os.path.join(game_dir, "libraries", rel)
        if not os.path.exists(jar):
            continue
        # natives 标记是否已处理：若 jar 修改时间新于 natives 目录则重新解压
        stamp = os.path.join(natives_dir, ".done_" + rel.replace("/", "_").replace(":", "_"))
        if os.path.exists(stamp) and os.path.getmtime(stamp) >= os.path.getmtime(jar):
            continue
        try:
            with open(jar, "rb") as f:
                data = f.read()
            utils.extract_zip(data, natives_dir, filter_prefix=None)
            with open(stamp, "w") as f:
                f.write("ok")
            changed = True
        except Exception:
            continue
    return natives_dir


def java_min_version(vdata: Dict) -> int:
    """根据版本 JSON 推断所需 Java 主版本。"""
    # 1.17+: Java 16+；1.20.5+: Java 21；1.12-: Java 8
    jver = (vdata.get("javaVersion", {}) or {}).get("majorVersion", 0)
    if jver:
        return jver
    vdata_id = vdata.get("id", "")
    try:
        major = int(vdata_id.split(".")[1])
        if major >= 20:
            return 21
        if major >= 17:
            return 17
        return 8
    except Exception:
        return 8


def build_command(game_dir: str, vdata: Dict, vid: str, username: str,
                  ram_mb: int, java_path: str, extra_flags: str = "",
                  access_token: str = "0", uuid_hex: Optional[str] = None,
                  server: Optional[str] = None, port: int = 25565,
                  fullscreen: bool = False, resolution: Optional[tuple] = None) -> List[str]:
    """构建完整启动命令。"""
    classpath = prepare_classpath(game_dir, vdata, vid)
    natives_dir = extract_natives(game_dir, vdata, vid)
    assets_root = os.path.join(game_dir, "assets")
    asset_index = (vdata.get("assetIndex", {}) or {}).get("id", "legacy")
    main_class = vdata.get("mainClass", "net.minecraft.client.main.Main")
    uuid_hex = uuid_hex or uuid.uuid4().hex

    game_args, jvm_args_tpl = versioninfo.parse_arguments(vdata)

    tokens = {
        "auth_player_name": username,
        "version_name": vid,
        "game_directory": game_dir,
        "assets_root": assets_root,
        "assets_index_name": asset_index,
        "auth_uuid": uuid_hex,
        "auth_access_token": access_token,
        "clientid": "NebulaLauncher",
        "auth_xuid": "0",
        "user_type": "legacy",
        "version_type": vdata.get("type", "release"),
        "user_properties": "{}",
        "resolution_width": str(resolution[0] if resolution else 854),
        "resolution_height": str(resolution[1] if resolution else 480),
        "natives_directory": natives_dir,
        "launcher_name": "NebulaLauncher",
        "launcher_version": "1.0.0",
        "classpath": classpath,
        "classpath_separator": os.pathsep,
    }

    def fill(args_list: List[str]) -> List[str]:
        out = []
        for a in args_list:
            for k, v in tokens.items():
                a = a.replace("${" + k + "}", v)
            if "${" in a:
                continue  # 无法填充的占位符跳过
            out.append(a)
        return out

    game_final = fill(game_args)
    if server:
        # 官方 server 参数：--server <ip> --port <port>
        if "--server" not in game_final:
            game_final += ["--server", server, "--port", str(port)]
    if fullscreen:
        game_final += ["--fullscreen"]
    if resolution:
        game_final += ["--width", str(resolution[0]), "--height", str(resolution[1])]

    jvm = ["-Xmx{ram}M".format(ram=ram_mb),
           "-Xms{ram}M".format(ram=max(ram_mb // 4, 256))]
    jvm += DEFAULT_JVM_FLAGS
    if extra_flags:
        jvm += [f.strip() for f in extra_flags.replace(";", " ").split() if f.strip()]
    jvm += fill(jvm_args_tpl)

    cmd = [java_path] + jvm + [main_class] + game_final
    return cmd


class GameProcess:
    def __init__(self, proc: subprocess.Popen, pid_file: str = ""):
        self.proc = proc
        self.pid_file = pid_file

    def alive(self) -> bool:
        return self.proc.poll() is None

    def wait(self):
        return self.proc.wait()

    def kill(self):
        if self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass


def launch(game_dir: str, vdata: Dict, vid: str, username: str,
           ram_mb: int, java_path: str, extra_flags: str = "",
           access_token: str = "0", server: Optional[str] = None, port: int = 25565,
           fullscreen: bool = False, resolution: Optional[tuple] = None,
           stdout_log: Optional[str] = None) -> GameProcess:
    """启动游戏，返回 GameProcess。"""
    cmd = build_command(game_dir, vdata, vid, username, ram_mb, java_path,
                        extra_flags, access_token, server=server, port=port,
                        fullscreen=fullscreen, resolution=resolution)
    if stdout_log:
        log_dir = os.path.dirname(stdout_log)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        logf = open(stdout_log, "a", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=game_dir)
    else:
        proc = subprocess.Popen(cmd, cwd=game_dir)
    return GameProcess(proc)


def java_version(java_path: str) -> Optional[int]:
    """检测 Java 主版本号。"""
    try:
        out = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=15)
        text = (out.stderr or out.stdout)
        for line in text.splitlines():
            if "version" in line.lower():
                for part in line.replace('"', "").split():
                    if part.startswith("1."):
                        return int(part.split(".")[1])
                    if part[0].isdigit():
                        return int(part.split(".")[0])
    except Exception:
        pass
    return None
