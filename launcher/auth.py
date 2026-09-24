# -*- coding: utf-8 -*-
"""账号系统：离线模式 + Microsoft 正版登录（设备码流程）。"""
import threading
import time
import uuid
from typing import Optional

from . import utils

# Microsoft OAuth（设备码流程）
# 使用公共客户端 ID（可被 Azure 注册的自己的应用替换）
CLIENT_ID = "1d3b36a3-04e7-4f8e-9b3a-5b7d9f2a6c41"
TOKEN_URL = "https://login.live.com/oauth20_token.srf"
DEVICE_CODE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MINECRAFT_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MINECRAFT_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"


def offline_uuid(username: str) -> str:
    """根据玩家名生成稳定的离线 UUID。"""
    return str(uuid.uuid3(uuid.NAMESPACE_URL, f"OfflinePlayer:{username}"))


def random_token() -> str:
    return uuid.uuid4().hex


class MicrosoftDeviceFlow:
    """Microsoft 设备码登录流程（正版账号）。"""

    def __init__(self):
        self.device_code = ""
        self.user_code = ""
        self.verification_uri = ""
        self.interval = 5
        self.expires_in = 900

    def request_device_code(self) -> dict:
        payload = {
            "client_id": CLIENT_ID,
            "scope": "XboxLive.signin offline_access",
        }
        # 设备码接口需要表单提交
        import requests
        r = requests.post(DEVICE_CODE_URL, data=payload, timeout=30,
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
        r.raise_for_status()
        data = r.json()
        self.device_code = data["device_code"]
        self.user_code = data["user_code"]
        self.verification_uri = data.get("verification_uri", "https://microsoft.com/link")
        self.interval = data.get("interval", 5)
        self.expires_in = data.get("expires_in", 900)
        return data

    def poll_token(self, stop: threading.Event = None) -> Optional[dict]:
        """轮询等待用户完成授权，返回 (access_token, refresh_token)。"""
        import requests
        deadline = time.time() + self.expires_in
        while time.time() < deadline:
            if stop and stop.is_set():
                return None
            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": self.device_code,
            }
            r = requests.post(TOKEN_URL, data=payload, timeout=30)
            data = r.json()
            if "access_token" in data:
                return data
            err = data.get("error")
            if err == "authorization_pending":
                time.sleep(self.interval)
                continue
            if err == "slow_down":
                self.interval += 5
                time.sleep(self.interval)
                continue
            if err == "authorization_declined":
                raise utils.DownloadError("用户拒绝了授权")
            if err == "expired_token":
                raise utils.DownloadError("设备码已过期，请重试")
            time.sleep(self.interval)
        raise utils.DownloadError("授权超时")

    @staticmethod
    def xbl_authenticate(access_token: str) -> str:
        payload = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={access_token}",
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        }
        data = utils.http_get_json(XBL_AUTH_URL, timeout=30)
        return data["Token"]

    def full_login(self, stop: threading.Event = None) -> dict:
        """完整流程：设备码 -> 令牌 -> XBL -> XSTS -> Minecraft -> Profile."""
        self.request_device_code()
        tokens = self.poll_token(stop)
        if not tokens:
            raise utils.DownloadError("登录已取消")
        return self._exchange(tokens["access_token"])

    def _exchange(self, access_token: str) -> dict:
        # 1) Xbox Live 认证
        payload = {
            "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com",
                           "RpsTicket": f"d={access_token}"},
            "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT",
        }
        import requests
        xbl = requests.post(XBL_AUTH_URL, json=payload, timeout=30).json()
        # 2) XSTS
        payload = {"Properties": {"SandboxId": "RETAIL",
                                  "UserTokens": [xbl["Token"]]},
                   "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}
        xsts = requests.post(XSTS_URL, json=payload, timeout=30).json()
        # 3) Minecraft 登录
        payload = {"identityToken": f"XBL3.0 x={xbl['DisplayClaims']['xui'][0]['uhs']};{xsts['Token']}"}
        mc = requests.post(MINECRAFT_LOGIN_URL, json=payload, timeout=30).json()
        # 4) 玩家档案
        headers = {"Authorization": f"Bearer {mc['access_token']}"}
        prof = requests.get(MINECRAFT_PROFILE_URL, headers=headers, timeout=30).json()
        return {
            "username": prof.get("name", "Steve"),
            "uuid": prof.get("id", ""),
            "access_token": mc["access_token"],
            "expires": time.time() + mc.get("expires_in", 86400),
        }
