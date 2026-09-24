# -*- coding: utf-8 -*-
"""主窗口：PCL 风格（左侧导航 + 内容区 + 自定义标题栏 + 底部状态栏）。"""
import sys

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout,
                               QLabel, QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import i18n
from ..settings import Settings
from . import theme
from .home_page import HomePage
from .mods_page import ModsPage
from .settings_page import SettingsPage
from .versions_page import VersionsPage
from .widgets import StarIcon, Toast

NAV_ITEMS = [
    ("启动", "home"),
    ("版本", "version"),
    ("模组", "mods"),
    ("设置", "settings"),
]
NAV_ICONS = {
    "home": "▶",
    "version": "◫",
    "mods": "▤",
    "settings": "⚙",
}


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(46)
        self._drag_pos = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(8)

        logo = StarIcon(26)
        name = QLabel("Nebula Launcher")
        name.setStyleSheet("font-size: 14px; font-weight: 700; color: #EAF0FF;")

        def make_btn(text, close=False):
            b = QPushButton(text)
            b.setProperty("winbtn", True)
            b.setProperty("close", close)
            b.setCursor(Qt.PointingHandCursor)
            return b

        self.btn_min = make_btn("—")
        self.btn_max = make_btn("□")
        self.btn_close = make_btn("✕", close=True)

        lay.addWidget(logo)
        lay.addWidget(name)
        lay.addStretch(1)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)

        self.btn_min.clicked.connect(lambda: self.window().showMinimized())
        self.btn_max.clicked.connect(self._toggle_max)
        self.btn_close.clicked.connect(self.window().close)

    def _toggle_max(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag_pos is not None and ev.buttons() & Qt.LeftButton:
            self.window().move(ev.globalPosition().toPoint() - self._drag_pos)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag_pos = None


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("Nebula Launcher · 星云启动器")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1160, 720)
        self.setMinimumSize(1000, 640)
        self._build()
        self._apply_language()

    # ------------------------------------------------------------------
    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏
        self.title_bar = TitleBar(self)
        outer.addWidget(self.title_bar)

        # 主体：侧边栏 + 内容
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # ---- 侧边栏 ----
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(218)
        sb_lay = QVBoxLayout(self.sidebar)
        sb_lay.setContentsMargins(16, 22, 16, 18)
        sb_lay.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(StarIcon(40))
        names = QVBoxLayout()
        names.setSpacing(0)
        app_name = QLabel("星云启动器")
        app_name.setObjectName("appName")
        app_sub = QLabel("Nebula Launcher")
        app_sub.setObjectName("appSub")
        names.addWidget(app_name)
        names.addWidget(app_sub)
        head.addLayout(names)
        head.addStretch(1)
        sb_lay.addLayout(head)
        sb_lay.addSpacing(22)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for label, key in NAV_ITEMS:
            b = QPushButton(f"  {NAV_ICONS[key]}    {label}")
            b.setProperty("nav", True)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(46)
            self.nav_group.addButton(b)
            sb_lay.addWidget(b)
            self.nav_buttons[key] = b
        sb_lay.addStretch(1)

        # 语言快速切换（底部）
        lang_box = QHBoxLayout()
        lang_lbl = QLabel("🌐" if False else "文")
        lang_lbl.setStyleSheet("color:#8A93A8; font-size:12px;")
        from PySide6.QtWidgets import QComboBox
        self.lang_combo = QComboBox()
        for code, name in i18n.LANGUAGES:
            self.lang_combo.addItem(name, code)
        idx = self.lang_combo.findData(self.settings.get("language"))
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_change)
        lang_box.addWidget(lang_lbl)
        lang_box.addWidget(self.lang_combo, 1)
        sb_lay.addLayout(lang_box)

        # ---- 内容区 ----
        self.stack = QStackedWidget()
        self.home_page = HomePage(self)
        self.versions_page = VersionsPage(self)
        self.mods_page = ModsPage(self)
        self.settings_page = SettingsPage(self)
        for p in (self.home_page, self.versions_page, self.mods_page, self.settings_page):
            self.stack.addWidget(p)

        body_lay.addWidget(self.sidebar)
        body_lay.addWidget(self.stack, 1)
        outer.addWidget(body, 1)

        # ---- 底部状态栏 ----
        self.status_bar = QFrame()
        self.status_bar.setObjectName("statusBar")
        self.status_bar.setFixedHeight(34)
        st_lay = QHBoxLayout(self.status_bar)
        st_lay.setContentsMargins(18, 0, 18, 0)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusText")
        st_lay.addWidget(self.status_label)
        st_lay.addStretch(1)
        self.status_version = QLabel("v1.0.0")
        self.status_version.setObjectName("statusText")
        st_lay.addWidget(self.status_version)
        outer.addWidget(self.status_bar)

        # 导航绑定
        self.nav_group.buttonClicked.connect(self._on_nav)
        self.nav_buttons["home"].setChecked(True)
        self._pages = {"home": 0, "version": 1, "mods": 2, "settings": 3}

        # 启动后刷新本地数据
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self.home_page.refresh_versions)
        QTimer.singleShot(200, self.versions_page.refresh)
        QTimer.singleShot(250, self.mods_page.refresh_installed)

        # 状态栏初始
        self.set_status(i18n.tr("ready"))

    # ------------------------------------------------------------------
    def _on_nav(self, btn):
        for key, b in self.nav_buttons.items():
            if b is btn:
                self.stack.setCurrentIndex(self._pages[key])
                break

    def switch_page(self, key: str):
        self.nav_buttons[key].setChecked(True)
        self.stack.setCurrentIndex(self._pages[key])

    def _apply_language(self):
        i18n.set_language(self.settings.get("language"))
        # 侧边栏文字
        labels = {"home": i18n.tr("nav_launch"), "version": i18n.tr("nav_versions"),
                  "mods": i18n.tr("nav_mods"), "settings": i18n.tr("nav_settings")}
        for key, b in self.nav_buttons.items():
            b.setText(f"  {NAV_ICONS[key]}    {labels.get(key, key)}")
        self.status_version.setText("v1.0.0")
        self.status_bar.setVisible(True)

    def _on_lang_change(self, idx):
        code = self.lang_combo.itemData(idx)
        self.settings.set("language", code)
        self._apply_language()
        for p in (self.home_page, self.versions_page, self.mods_page, self.settings_page):
            p.retranslate()
        self.toast(i18n.tr("lang_changed"))

    # ------------------------------------------------------------------
    def set_status(self, text: str):
        self.status_label.setText(text)

    def toast(self, text: str, ok: bool = True):
        t = Toast(self, text, ok)
        t.show_toast()
        self._toast = t


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    font = QFont(theme.FONT_FAMILY.split(",")[0], 10)
    app.setFont(font)
    app.setStyleSheet(theme.QSS)
    settings = Settings()
    win = MainWindow(settings)
    win.show()
    return app.exec()
