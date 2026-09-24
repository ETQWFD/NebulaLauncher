# -*- coding: utf-8 -*-
"""启动页：版本选择、内存滑块、账号、大启动按钮、状态与进度."""
import os
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QProgressBar, QSlider,
                               QVBoxLayout, QWidget)

from .. import i18n, java as java_mod
from ..minecraft import installer, launch
from ..minecraft.manifest import fetch_manifest
from ..settings import Settings
from .tasks import LaunchWorker, TaskWorker
from .widgets import Card, PageIndicator, Toast


class HomePage(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.settings: Settings = win.settings
        self.versions = []          # 在线版本清单（懒加载）
        self.worker = None
        self.game = None
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 26, 30, 20)
        outer.setSpacing(16)

        self.indicator = PageIndicator("", "")
        outer.addWidget(self.indicator)

        body = QHBoxLayout()
        body.setSpacing(16)

        # 左：版本卡片
        left = Card()
        lv = left.layout()
        lv.setSpacing(12)
        t1 = QLabel("")
        t1.setProperty("section", True)
        lv.addWidget(t1)
        self.t1 = t1

        self.version_combo = QComboBox()
        self.version_combo.setMinimumHeight(42)
        lv.addWidget(self.version_combo)

        self.version_info = QLabel("")
        self.version_info.setProperty("subtitle", True)
        self.version_info.setWordWrap(True)
        lv.addWidget(self.version_info)

        lv.addSpacing(8)
        t2 = QLabel("")
        t2.setProperty("section", True)
        lv.addWidget(t2)
        self.t2 = t2
        self.ram_slider = QSlider(Qt.Horizontal)
        self.ram_slider.setRange(1024, 16384)
        self.ram_slider.setSingleStep(512)
        self.ram_slider.setPageStep(1024)
        self.ram_slider.setValue(self.settings.get("ram_mb", 4096))
        self.ram_slider.valueChanged.connect(self._ram_changed)
        lv.addWidget(self.ram_slider)
        self.ram_label = QLabel("")
        self.ram_label.setProperty("subtitle", True)
        lv.addWidget(self.ram_label)

        lv.addSpacing(8)
        t3 = QLabel("")
        t3.setProperty("section", True)
        lv.addWidget(t3)
        self.t3 = t3

        self.account_combo = QComboBox()
        self.account_combo.setMinimumHeight(36)
        lv.addWidget(self.account_combo)
        self.name_edit = QLineEdit(self.settings.get("username", "Steve"))
        self.name_edit.setMinimumHeight(36)
        lv.addWidget(self.name_edit)

        # 自定义服务器账号（authlib-injector）
        self.custom_server_edit = QLineEdit(self.settings.get("custom_server_url"))
        self.custom_server_edit.setPlaceholderText("authlib 服务器地址，如 https://example.com/api/authlib-injector")
        self.custom_server_edit.setMinimumHeight(34)
        self.custom_server_edit.setVisible(False)
        lv.addWidget(self.custom_server_edit)
        self.custom_pwd_edit = QLineEdit(self.settings.get("custom_password"))
        self.custom_pwd_edit.setPlaceholderText("")
        self.custom_pwd_edit.setEchoMode(QLineEdit.Password)
        self.custom_pwd_edit.setMinimumHeight(34)
        self.custom_pwd_edit.setVisible(False)
        lv.addWidget(self.custom_pwd_edit)

        # 正版微软登录按钮
        self.btn_ms_login = QPushButton("")
        self.btn_ms_login.setProperty("ghost", True)
        self.btn_ms_login.setVisible(False)
        self.btn_ms_login.clicked.connect(self._ms_login)
        lv.addWidget(self.btn_ms_login)
        self.ms_status = QLabel("")
        self.ms_status.setProperty("subtitle", True)
        self.ms_status.setVisible(False)
        lv.addWidget(self.ms_status)

        self.account_combo.currentIndexChanged.connect(self._account_changed)
        lv.addSpacing(4)

        # 快捷操作
        row = QHBoxLayout()
        self.btn_refresh = QPushButton("")
        self.btn_refresh.setProperty("ghost", True)
        self.btn_refresh.clicked.connect(self.refresh_versions)
        row.addWidget(self.btn_refresh)
        row.addStretch(1)
        lv.addLayout(row)
        lv.addStretch(1)
        body.addWidget(left, 3)

        # 右：启动区
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(14)

        big = Card()
        bv = big.layout()
        bv.setSpacing(8)
        self.big_version = QLabel("")
        self.big_version.setStyleSheet("font-size: 26px; font-weight: 800; color:#EAF0FF;")
        self.big_type = QLabel("")
        self.big_type.setProperty("subtitle", True)
        bv.addWidget(self.big_version)
        bv.addWidget(self.big_type)
        bv.addSpacing(6)
        self.launch_btn = QPushButton("")
        self.launch_btn.setProperty("primary", True)
        self.launch_btn.setMinimumHeight(56)
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.clicked.connect(self.launch_game)
        bv.addWidget(self.launch_btn)
        rv.addWidget(big, 2)

        # 进度
        prog_card = Card()
        pv = prog_card.layout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        pv.addWidget(self.progress_bar)
        self.stage_label = QLabel("")
        self.stage_label.setProperty("subtitle", True)
        self.stage_label.setWordWrap(True)
        pv.addWidget(self.stage_label)
        rv.addWidget(prog_card, 1)
        body.addWidget(right, 2)

        outer.addLayout(body, 1)
        self._ram_changed(self.ram_slider.value())
        self._setup_accounts()

    # ------------------------------------------------------------------
    def retranslate(self):
        tr = i18n.tr
        self.indicator.set_text(tr("home_title"), tr("home_subtitle"))
        self._update_texts()
        # 下拉框无已安装版本时刷新占位提示
        if self.version_combo.count() == 1 and self.version_combo.itemData(0) is None:
            self.version_combo.setItemText(0, tr("no_version_hint"))

    def _update_texts(self):
        tr = i18n.tr
        self.t1.setText(tr("sec_version"))
        self.t2.setText(tr("sec_memory"))
        self.t3.setText(tr("sec_account"))
        self.version_info.setText(tr("home_version_hint"))
        self.ram_label.setText(tr("ram_fmt").format(mb=self.ram_slider.value(),
                                                    gb=self.ram_slider.value() / 1024))
        self.btn_refresh.setText(tr("btn_refresh"))
        self.launch_btn.setText(tr("btn_launch"))
        self.stage_label.setText(tr("idle"))
        self.big_type.setText(tr("home_ready"))
        self.set_status_text()

    def set_status_text(self):
        vid = self.version_combo.currentData()
        if vid:
            self.big_version.setText(vid)
        else:
            self.big_version.setText(i18n.tr("no_version"))

    def _ram_changed(self, v: int):
        self.settings.set("ram_mb", v)
        self.ram_label.setText(i18n.tr("ram_fmt").format(mb=v, gb=v / 1024))

    # ------------------------------------------------------------------
    def refresh_versions(self):
        """刷新已安装版本列表（本地）。"""
        installed = installer.list_installed(self.settings.game_dir())
        self.version_combo.clear()
        for v in installed:
            self.version_combo.addItem(v, v)
        last = self.settings.get("last_version")
        idx = self.version_combo.findData(last)
        if idx >= 0:
            self.version_combo.setCurrentIndex(idx)
        if not installed:
            self.version_combo.addItem(i18n.tr("no_version_hint"), None)
        self.set_status_text()
        self.win.set_status(i18n.tr("status_versions").format(n=len(installed)))
        self.win.toast(i18n.tr("versions_loaded").format(n=len(installed)))

    # ------------------------------------------------------------------
    # 账号体系
    # ------------------------------------------------------------------
    def _setup_accounts(self):
        self.account_combo.clear()
        self.account_combo.addItem(i18n.tr("acct_offline"), "offline")
        self.account_combo.addItem(i18n.tr("acct_microsoft"), "microsoft")
        self.account_combo.addItem(i18n.tr("acct_custom"), "custom")
        idx = self.account_combo.findData(self.settings.get("account_type"))
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)
        self._account_changed(idx)

    def _account_changed(self, idx):
        kind = self.account_combo.itemData(idx) or "offline"
        self.settings.set("account_type", kind)
        is_off = kind == "offline"
        is_ms = kind == "microsoft"
        is_cu = kind == "custom"
        self.name_edit.setPlaceholderText(i18n.tr("acct_name_hint"))
        self.custom_server_edit.setVisible(is_cu)
        self.custom_pwd_edit.setVisible(is_cu)
        self.custom_pwd_edit.setPlaceholderText(i18n.tr("acct_pwd_hint"))
        self.btn_ms_login.setVisible(is_ms)
        self.ms_status.setVisible(is_ms)
        if is_ms:
            if self.settings.get("microsoft_name"):
                self.ms_status.setText(i18n.tr("acct_ms_logged").format(
                    n=self.settings.get("microsoft_name")))
                self.btn_ms_login.setText(i18n.tr("acct_ms_relogin"))
            else:
                self.ms_status.setText(i18n.tr("acct_ms_notlogin"))
                self.btn_ms_login.setText(i18n.tr("acct_ms_login"))
        if is_cu:
            self.custom_server_edit.setPlaceholderText(i18n.tr("acct_server_hint"))

    def _ms_login(self):
        from .. import auth as auth_mod
        from PySide6.QtWidgets import QInputDialog
        flow = auth_mod.MicrosoftDeviceFlow()
        try:
            dev = flow.request_device_code()
        except Exception as e:
            self.win.toast(i18n.tr("acct_ms_fail").format(e=e), ok=False)
            return
        code, ok = QInputDialog.getText(
            self, i18n.tr("acct_ms_login"),
            i18n.tr("acct_ms_code").format(code=dev["user_code"], uri=flow.verification_uri))
        if not ok:
            self.win.toast(i18n.tr("acct_cancel"), ok=False)
            return
        self.ms_status.setText(i18n.tr("acct_ms_wait"))
        self.win.set_status(i18n.tr("acct_ms_wait"))

        def job(progress=None, stage_cb=None, cancel=None):
            return flow.full_login()

        def ok(info):
            self.settings.set("microsoft_name", info["username"])
            self.settings.set("microsoft_token", info["access_token"])
            self.settings.set("microsoft_uuid", info["uuid"])
            self.settings.set("username", info["username"])
            self.name_edit.setText(info["username"])
            self._account_changed(self.account_combo.currentIndex())
            self.win.toast(i18n.tr("acct_ms_ok").format(n=info["username"]))

        def fail(e):
            self.win.toast(i18n.tr("acct_ms_fail").format(e=e), ok=False)
            self._account_changed(self.account_combo.currentIndex())

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def _resolve_account(self):
        """返回 (username, access_token, uuid, extra_jvm_flags)。"""
        kind = self.settings.get("account_type")
        extra = []
        if kind == "microsoft":
            name = self.settings.get("microsoft_name") or self.name_edit.text().strip() or "Steve"
            return name, self.settings.get("microsoft_token") or "0", \
                   self.settings.get("microsoft_uuid") or "", extra
        if kind == "custom":
            server = self.custom_server_edit.text().strip()
            username = self.name_edit.text().strip()
            password = self.custom_pwd_edit.text()
            if not server or not username or not password:
                raise RuntimeError(i18n.tr("acct_custom_need"))
            self.settings.set("custom_server_url", server)
            self.settings.set("custom_username", username)
            self.settings.set("custom_password", password)
            # authlib-injector：下载并生成 javaagent 参数
            from .. import authlib
            jar = authlib.authlib_jar()
            if not jar:
                jar = authlib.download_authlib()
            extra.append(authlib.authlib_flag(jar, server))
            return username, "0", "", extra
        # 离线
        username = self.name_edit.text().strip() or "Steve"
        return username, "0", "", extra

    # ------------------------------------------------------------------
    def launch_game(self):
        vid = self.version_combo.currentData()
        if not vid:
            self.win.toast(i18n.tr("no_version_hint"), ok=False)
            return
        try:
            username, token, uuid_hex, extra_flags = self._resolve_account()
        except Exception as e:
            self.win.toast(str(e), ok=False)
            return
        self.settings.set("username", username)
        game_dir = self.settings.game_dir()
        vj = os.path.join(game_dir, "versions", vid, f"{vid}.json")
        if not os.path.exists(vj):
            self.win.toast(i18n.tr("version_broken").format(v=vid), ok=False)
            return
        import json as _json
        with open(vj, "r", encoding="utf-8") as f:
            vdata = _json.load(f)

        # Java 准备
        need = launch.java_min_version(vdata)
        java_path = self.settings.get("java_path")
        if not java_path:
            java_path = java_mod.find_java(need)
        if not java_path:
            # 自动下载
            self.win.set_status(i18n.tr("dl_java").format(v=need))
            self.progress_bar.setValue(0)
            self._auto_java(need, vid, vdata, username, game_dir, token, uuid_hex, extra_flags)
            return
        self._do_launch(java_path, vid, vdata, username, game_dir, token, uuid_hex, extra_flags)

    def _auto_java(self, feature, vid, vdata, username, game_dir, token="0", uuid_hex="", extra_flags=None):
        def job(progress=None, stage_cb=None, cancel=None):
            p = java_mod.download_java(feature, progress=progress, stage_cb=stage_cb)
            self.settings.set("java_path", p)
            return p

        def ok(path):
            self.win.toast(i18n.tr("java_ready"))
            self._do_launch(path, vid, vdata, username, game_dir, token, uuid_hex, extra_flags)

        self.worker = TaskWorker(job)
        self.worker.progress.connect(lambda f, s: self._show_progress(f, s))
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(lambda e: (self.win.toast(e, ok=False), self._show_progress(0, e)))
        self.worker.start()

    def _do_launch(self, java_path, vid, vdata, username, game_dir, token="0", uuid_hex="", extra_flags=None):
        ram = self.settings.get("ram_mb", 4096)
        extra = self.settings.get("jvm_flags_extra", "")
        if extra_flags:
            extra = (extra + " " + " ".join(extra_flags)).strip()
        log_path = os.path.join(game_dir, "logs", "nebulalauncher.log")

        def launch_fn():
            return launch.launch(game_dir, vdata, vid, username, ram, java_path,
                                 extra_flags=extra, access_token=token, uuid_hex=uuid_hex or None,
                                 stdout_log=log_path)

        self.launch_btn.setEnabled(False)
        self.launch_btn.setText(i18n.tr("launching"))
        self.win.set_status(i18n.tr("launching"))
        self.worker = LaunchWorker(launch_fn)
        self.worker.launched.connect(self._on_launched)
        self.worker.failed.connect(self._on_launch_failed)
        self.worker.start()

    def _on_launched(self, game):
        self.game = game
        self.settings.set("last_version", self.version_combo.currentData())
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText(i18n.tr("btn_launch"))
        self.win.toast(i18n.tr("game_started"))
        # 自动关闭启动器：只保留游戏进程
        if self.settings.get("auto_close", True):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2500, self.win.close)

    def _on_launch_failed(self, err):
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText(i18n.tr("btn_launch"))
        self.win.toast(i18n.tr("launch_failed").format(e=err), ok=False)
        self.win.set_status(i18n.tr("launch_failed").format(e=err))

    def _show_progress(self, frac, stage):
        self.progress_bar.setValue(int(frac * 1000))
        self.stage_label.setText(str(stage)[:120])
        self.win.set_status(str(stage)[:80])
