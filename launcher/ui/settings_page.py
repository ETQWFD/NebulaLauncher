# -*- coding: utf-8 -*-
"""设置页：语言、Java、游戏目录、内存、启动行为、模组仓库等。"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from .. import i18n, java as java_mod
from ..minecraft import launch
from .widgets import Card, PageIndicator, ToggleSwitch


class SettingsPage(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.settings = win.settings
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 26, 30, 20)
        outer.setSpacing(16)

        self.indicator = PageIndicator()
        outer.addWidget(self.indicator)

        body = QVBoxLayout()
        body.setSpacing(12)

        # 语言
        c1 = Card()
        g1 = QGridLayout()
        g1.setHorizontalSpacing(18)
        g1.setVerticalSpacing(14)
        self.lbl_lang = QLabel("")
        self.lbl_lang.setProperty("section", True)
        self.lang_combo = QComboBox()
        for code, name in i18n.LANGUAGES:
            self.lang_combo.addItem(name, code)
        self.lang_combo.blockSignals(True)
        idx = self.lang_combo.findData(self.settings.get("language"))
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.blockSignals(False)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)
        g1.addWidget(self.lbl_lang, 0, 0)
        g1.addWidget(self.lang_combo, 0, 1)
        c1.layout().addLayout(g1)
        body.addWidget(c1)

        # 路径
        c2 = Card()
        g2 = QGridLayout()
        g2.setHorizontalSpacing(18)
        g2.setVerticalSpacing(14)
        self.lbl_java = QLabel("")
        self.lbl_java.setProperty("section", True)
        self.java_edit = QLineEdit(self.settings.get("java_path"))
        self.java_edit.textChanged.connect(lambda t: self.settings.set("java_path", t.strip()))
        self.btn_java = QPushButton("...")
        self.btn_java.setProperty("ghost", True)
        self.btn_java.setFixedWidth(44)
        self.btn_java.clicked.connect(self._pick_java)
        self.btn_java_detect = QPushButton("")
        self.btn_java_detect.setProperty("ghost", True)
        self.btn_java_detect.clicked.connect(self._detect_java)
        g2.addWidget(self.lbl_java, 0, 0)
        g2.addWidget(self.java_edit, 0, 1)
        g2.addWidget(self.btn_java, 0, 2)
        g2.addWidget(self.btn_java_detect, 0, 3)

        self.lbl_dir = QLabel("")
        self.lbl_dir.setProperty("section", True)
        self.dir_edit = QLineEdit(self.settings.get("game_dir"))
        self.dir_edit.setPlaceholderText(i18n.tr("set_gamedir_hint"))
        self.dir_edit.textChanged.connect(lambda t: self.settings.set("game_dir", t.strip()))
        self.btn_dir = QPushButton("...")
        self.btn_dir.setProperty("ghost", True)
        self.btn_dir.setFixedWidth(44)
        self.btn_dir.clicked.connect(self._pick_dir)
        self.btn_open = QPushButton("")
        self.btn_open.setProperty("ghost", True)
        self.btn_open.clicked.connect(lambda: self.win.open_game_dir())
        g2.addWidget(self.lbl_dir, 1, 0)
        g2.addWidget(self.dir_edit, 1, 1)
        g2.addWidget(self.btn_dir, 1, 2)
        g2.addWidget(self.btn_open, 1, 3)
        c2.layout().addLayout(g2)
        body.addWidget(c2)

        # 行为
        c3 = Card()
        g3 = QGridLayout()
        g3.setHorizontalSpacing(18)
        g3.setVerticalSpacing(14)
        self.lbl_auto = QLabel("")
        self.lbl_auto.setProperty("section", True)
        self.auto_close = ToggleSwitch(self.settings.get("auto_close", True))
        self.auto_close.clicked.connect(
            lambda: self.settings.set("auto_close", self.auto_close.is_checked()))
        g3.addWidget(self.lbl_auto, 0, 0)
        g3.addWidget(self.auto_close, 0, 1, Qt.AlignLeft)

        self.lbl_jvm = QLabel("")
        self.lbl_jvm.setProperty("section", True)
        self.jvm_edit = QLineEdit(self.settings.get("jvm_flags_extra"))
        self.jvm_edit.setPlaceholderText("-Dminecraft.example=1")
        self.jvm_edit.textChanged.connect(lambda t: self.settings.set("jvm_flags_extra", t.strip()))
        g3.addWidget(self.lbl_jvm, 1, 0)
        g3.addWidget(self.jvm_edit, 1, 1, 1, 3)
        c3.layout().addLayout(g3)
        body.addWidget(c3)

        # 模组仓库
        c4 = Card()
        g4 = QGridLayout()
        g4.setHorizontalSpacing(18)
        g4.setVerticalSpacing(14)
        self.lbl_repo = QLabel("")
        self.lbl_repo.setProperty("section", True)
        self.repo_edit = QLineEdit(self.settings.get("github_mods_repo"))
        self.repo_edit.textChanged.connect(lambda t: self.settings.set("github_mods_repo", t.strip()))
        g4.addWidget(self.lbl_repo, 0, 0)
        g4.addWidget(self.repo_edit, 0, 1)
        c4.layout().addLayout(g4)
        body.addWidget(c4)

        body.addStretch(1)
        outer.addLayout(body, 1)

        # 附加信息
        self.info = QLabel("")
        self.info.setProperty("subtitle", True)
        self.info.setWordWrap(True)
        outer.addWidget(self.info)
        self.retranslate()

    # ------------------------------------------------------------------
    def retranslate(self):
        tr = i18n.tr
        self.indicator.set_text(tr("set_title"), tr("set_subtitle"))
        self.lbl_lang.setText(tr("set_language"))
        self.lbl_java.setText(tr("set_java"))
        self.lbl_dir.setText(tr("set_gamedir"))
        self.lbl_auto.setText(tr("set_autoclose"))
        self.lbl_jvm.setText(tr("set_jvm"))
        self.lbl_repo.setText(tr("set_modrepo"))
        self.btn_open.setText(tr("btn_open_dir"))
        self.btn_java_detect.setText(tr("set_autodetect"))
        self.info.setText(tr("set_about").format(ver="1.2.0"))

    # ------------------------------------------------------------------
    def _pick_java(self):
        exe = "java.exe" if os.name == "nt" else "java"
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("set_java"), os.path.expanduser("~"))
        if path:
            self.java_edit.setText(path)

    def _detect_java(self):
        v = java_mod.system_java()
        if v:
            self.java_edit.setText(v)
            self.win.toast(i18n.tr("java_found"))
        else:
            self.win.toast(i18n.tr("java_notfound"), ok=False)

    def _pick_dir(self):
        path = QFileDialog.getExistingDirectory(self, i18n.tr("set_gamedir"))
        if path:
            self.dir_edit.setText(path)

    def _on_lang(self, idx):
        code = self.lang_combo.itemData(idx)
        self.settings.set("language", code)
        self.win._apply_language()
        for p in (self.win.home_page, self.win.versions_page, self.win.mods_page, self.win.settings_page):
            p.retranslate()
        self.win.toast(i18n.tr("lang_changed"))
