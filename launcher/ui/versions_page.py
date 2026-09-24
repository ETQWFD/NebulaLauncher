# -*- coding: utf-8 -*-
"""版本管理页：已安装版本列表 + 安装新版本（原版 / Fabric / Quilt / Forge）。"""
import os
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from .. import i18n, java as java_mod
from ..minecraft import fabric, forge, installer
from ..minecraft.manifest import fetch_manifest
from .tasks import TaskWorker
from .widgets import Card, PageIndicator


class InstallDialog(QDialog):
    """选择 MC 版本 + 加载器类型并安装。"""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.settings = win.settings
        self.setWindowTitle("Install")
        self.setModal(True)
        self.resize(560, 420)
        self._versions = []
        self.worker = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(12)

        t = QLabel(i18n.tr("dl_title"))
        t.setProperty("title", True)
        lay.addWidget(t)

        self.mc_combo = QComboBox()
        self.mc_combo.setMinimumHeight(38)
        lay.addWidget(self.mc_combo)

        self.loader_combo = QComboBox()
        self.loader_combo.setMinimumHeight(38)
        self.loader_combo.addItem(i18n.tr("loader_vanilla"), "vanilla")
        self.loader_combo.addItem("Fabric", "fabric")
        self.loader_combo.addItem("Quilt", "quilt")
        self.loader_combo.addItem("Forge", "forge")
        lay.addWidget(self.loader_combo)

        self.status = QLabel(i18n.tr("dl_hint"))
        self.status.setProperty("subtitle", True)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        from PySide6.QtWidgets import QProgressBar
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        lay.addWidget(self.progress)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_cancel = QPushButton(i18n.tr("dl_cancel"))
        self.btn_cancel.setProperty("ghost", True)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_install = QPushButton(i18n.tr("dl_install"))
        self.btn_install.setProperty("primary", True)
        self.btn_install.clicked.connect(self._start)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_install)
        lay.addLayout(btns)

    def load(self):
        self.btn_install.setEnabled(False)
        self.status.setText(i18n.tr("dl_loading"))

        def job(progress=None, stage_cb=None, cancel=None):
            return fetch_manifest()

        def ok(versions):
            self._versions = [v for v in versions if v.is_release][:40]
            if not self._versions:
                self._versions = versions[:40]
            self.mc_combo.clear()
            for v in self._versions:
                self.mc_combo.addItem(v.id, v)
            self.btn_install.setEnabled(True)
            self.status.setText(i18n.tr("dl_hint"))
            # 若已有 Fabric 版本则预选对应 MC
            self._preload_loader()

        def fail(e):
            self.status.setText(i18n.tr("dl_failed").format(e=e))

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def _preload_loader(self):
        pass

    def _start(self):
        v = self.mc_combo.currentData()
        loader = self.loader_combo.currentData()
        if not v:
            return
        self.btn_install.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        game_dir = self.settings.game_dir()
        vid = v.id

        def job(progress=None, stage_cb=None, cancel=None):
            if loader == "vanilla":
                vdata = installer.ensure_version_json(game_dir, v)
                installer.install_version(game_dir, v, vdata, progress=progress, stage_cb=stage_cb, cancel=cancel)
                return vid
            if loader == "fabric":
                return fabric.install_fabric(game_dir, vid, progress=progress, stage_cb=stage_cb)
            if loader == "quilt":
                return fabric.install_quilt(game_dir, vid, progress=progress, stage_cb=stage_cb)
            if loader == "forge":
                java_path = self.settings.get("java_path") or java_mod.system_java()
                if not java_path:
                    raise RuntimeError(i18n.tr("forge_no_java"))
                fvers = forge.forge_versions(vid)
                if not fvers:
                    raise RuntimeError(i18n.tr("forge_no_version").format(mc=vid))
                return forge.install_forge(game_dir, vid, fvers[0], java_path,
                                           progress=progress, stage_cb=stage_cb)
            raise RuntimeError("unknown loader")

        def ok(result):
            self.status.setText(i18n.tr("dl_done").format(v=result))
            self.btn_install.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            self.win.home_page.refresh_versions()
            self.win.versions_page.refresh()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, self.accept)

        def fail(e):
            self.status.setText(i18n.tr("dl_failed").format(e=e))
            self.btn_install.setEnabled(True)
            self.btn_cancel.setEnabled(True)

        self.worker = TaskWorker(job)
        self.worker.progress.connect(lambda f, s: (self.progress.setValue(int(f * 1000)), self.status.setText(str(s)[:120])))
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()


class VersionsPage(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.settings = win.settings
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 26, 30, 20)
        outer.setSpacing(16)

        head = QHBoxLayout()
        self.indicator = PageIndicator()
        head.addWidget(self.indicator)
        head.addStretch(1)
        self.btn_install = QPushButton("")
        self.btn_install.setProperty("primary", True)
        self.btn_install.clicked.connect(self._open_install)
        head.addWidget(self.btn_install)
        outer.addLayout(head)

        self.list = QListWidget()
        self.list.setObjectName("modList")
        outer.addWidget(self.list, 1)
        self.install_dialog = None
        self.retranslate()

    def retranslate(self):
        tr = i18n.tr
        self.indicator.set_text(tr("ver_title"), tr("ver_subtitle"))
        self.btn_install.setText(tr("ver_install_new"))
        self.refresh()

    def refresh(self):
        self.list.clear()
        for vid in installer.list_installed(self.settings.game_dir()):
            item = QListWidgetItem()
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(10, 6, 10, 6)
            name = QLabel(vid)
            name.setStyleSheet("font-size:14px; font-weight:600; color:#EAF0FF;")
            kind = QLabel()
            kind.setProperty("subtitle", True)
            if "fabric" in vid.lower():
                kind.setText("Fabric")
            elif "quilt" in vid.lower():
                kind.setText("Quilt")
            elif "forge" in vid.lower():
                kind.setText("Forge")
            else:
                kind.setText(i18n.tr("ver_vanilla"))
            btn_launch = QPushButton(i18n.tr("btn_launch"))
            btn_launch.setProperty("ghost", True)
            btn_launch.setCursor(Qt.PointingHandCursor)
            btn_del = QPushButton(i18n.tr("ver_delete"))
            btn_del.setProperty("danger", True)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_launch.clicked.connect(lambda _, v=vid: self._launch_version(v))
            btn_del.clicked.connect(lambda _, v=vid: self._delete_version(v))
            lay.addWidget(name, 1)
            lay.addWidget(kind)
            lay.addWidget(btn_launch)
            lay.addWidget(btn_del)
            self.list.addItem(item)
            self.list.setItemWidget(item, w)
            item.setSizeHint(w.sizeHint())

    def _launch_version(self, vid):
        self.win.home_page.version_combo.setCurrentIndex(
            max(0, self.win.home_page.version_combo.findData(vid)))
        self.win.switch_page("home")
        self.win.home_page.launch_game()

    def _delete_version(self, vid):
        import shutil
        vdir = os.path.join(self.settings.game_dir(), "versions", vid)
        shutil.rmtree(vdir, ignore_errors=True)
        self.win.home_page.refresh_versions()
        self.refresh()
        self.win.toast(i18n.tr("ver_deleted").format(v=vid))

    def _open_install(self):
        if self.install_dialog is None:
            self.install_dialog = InstallDialog(self.win)
        self.install_dialog.load()
        self.install_dialog.show()
