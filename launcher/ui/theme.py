# -*- coding: utf-8 -*-
"""UI 主题：PCL 风格深蓝配色 + QSS 样式表."""

# 配色（深色主基调 + 亮蓝强调色，类 PCL）
ACCENT = "#3D8BFF"
ACCENT_HOVER = "#5C9DFF"
ACCENT_PRESS = "#2F74E0"
BG_DARK = "#12151D"
BG_SIDEBAR = "#171B26"
BG_CARD = "#1E2432"
BG_CARD_HOVER = "#252C3D"
BG_INPUT = "#141926"
BORDER = "#2A3247"
TEXT_MAIN = "#EAF0FF"
TEXT_DIM = "#8A93A8"
TEXT_FAINT = "#5A6275"
SUCCESS = "#3ECF8E"
WARNING = "#FFB84D"
DANGER = "#FF5B6E"

FONT_FAMILY = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, Segoe UI, sans-serif"

QSS = """
* { font-family: %s; outline: none; }
QMainWindow, QWidget#root { background: %s; color: %s; }

/* ---------- 侧边栏 ---------- */
QWidget#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 %s, stop:1 %s);
    border-right: 1px solid %s;
}
QLabel#appName { color: %s; font-size: 21px; font-weight: 700; letter-spacing: 1px; }
QLabel#appSub  { color: %s; font-size: 11px; }

QPushButton[nav="true"] {
    background: transparent; color: %s; border: none; border-radius: 10px;
    text-align: left; padding: 12px 18px; font-size: 14px; font-weight: 500;
}
QPushButton[nav="true"]:hover { background: rgba(61,139,255,0.14); color: %s; }
QPushButton[nav="true"]:checked { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(61,139,255,0.32), stop:1 rgba(61,139,255,0.12)); color: %s; border-left: 3px solid %s; }

/* ---------- 卡片 ---------- */
QFrame#card {
    background: %s; border: 1px solid %s; border-radius: 16px;
}
QFrame#card:hover { border-color: #3A4560; }
QLabel[title="true"] { font-size: 17px; font-weight: 700; color: %s; }
QLabel[subtitle="true"] { font-size: 12px; color: %s; }
QLabel[section="true"] { font-size: 13px; font-weight: 600; color: %s; }

/* ---------- 按钮 ---------- */
QPushButton[primary="true"] {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 %s, stop:1 %s);
    color: white; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 700; padding: 12px 28px;
}
QPushButton[primary="true"]:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 %s, stop:1 %s); }
QPushButton[primary="true"]:pressed { background: %s; }
QPushButton[primary="true"]:disabled { background: #2A3247; color: #6A738A; }

QPushButton[ghost="true"] {
    background: rgba(61,139,255,0.10); color: %s; border: 1px solid rgba(61,139,255,0.35);
    border-radius: 10px; padding: 8px 16px; font-size: 13px;
}
QPushButton[ghost="true"]:hover { background: rgba(61,139,255,0.22); }
QPushButton[ghost="true"]:disabled { color: #5A6275; border-color: #2A3247; background: transparent; }

QPushButton[danger="true"] {
    background: rgba(255,91,110,0.12); color: %s; border: 1px solid rgba(255,91,110,0.4);
    border-radius: 10px; padding: 8px 16px; font-size: 13px;
}
QPushButton[danger="true"]:hover { background: rgba(255,91,110,0.25); }

/* ---------- 输入框 / 下拉框 ---------- */
QLineEdit, QComboBox, QSpinBox {
    background: %s; color: %s; border: 1px solid %s; border-radius: 10px;
    padding: 9px 12px; font-size: 13px; selection-background-color: %s;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: %s; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid %s; margin-right: 10px; }
QComboBox QAbstractItemView {
    background: %s; color: %s; border: 1px solid %s; border-radius: 8px;
    selection-background-color: rgba(61,139,255,0.35);
    padding: 4px;
}

/* ---------- 列表 ---------- */
QListWidget {
    background: transparent; border: none; color: %s; font-size: 13px;
}
QListWidget::item { border-radius: 10px; padding: 6px; margin: 2px 0; }
QListWidget::item:hover { background: rgba(61,139,255,0.12); }
QListWidget::item:selected { background: rgba(61,139,255,0.28); color: %s; }

QListWidget#modList { background: transparent; }
QListWidget#modList::item { border-bottom: 1px solid %s; border-radius: 0; padding: 10px 4px; margin: 0; }

/* ---------- 滚动条 ---------- */
QScrollBar:vertical { background: transparent; width: 8px; margin: 4px; }
QScrollBar::handle:vertical { background: %s; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3A4560; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal { background: transparent; height: 8px; }
QScrollBar::handle:horizontal { background: #2A3247; border-radius: 4px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---------- 进度条 ---------- */
QProgressBar {
    background: %s; border: none; border-radius: 6px; height: 10px; text-align: center;
    color: %s; font-size: 10px;
}
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 %s, stop:1 %s); border-radius: 6px; }

/* ---------- 开关 ---------- */
QCheckBox { spacing: 8px; color: %s; font-size: 13px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid %s; background: %s; }
QCheckBox::indicator:checked { background: %s; border-color: %s; image: none; }
QCheckBox::indicator:checked { background: %s; }

/* ---------- 标题栏 ---------- */
QWidget#titleBar { background: %s; border-bottom: 1px solid %s; }
QPushButton[winbtn="true"] {
    background: transparent; color: %s; border: none; border-radius: 6px;
    font-size: 14px; padding: 6px 12px; font-weight: 600;
}
QPushButton[winbtn="true"]:hover { background: rgba(255,255,255,0.08); }
QPushButton[winbtn="true"][close="true"]:hover { background: #E81123; color: white; }

/* ---------- 标签页 ---------- */
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab {
    background: transparent; color: %s; padding: 10px 22px; font-size: 14px; font-weight: 600;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: %s; border-bottom: 2px solid %s; }
QTabBar::tab:hover { color: %s; }

/* ---------- 提示气泡 ---------- */
QFrame#toast { background: rgba(20,24,38,0.94); border: 1px solid %s; border-radius: 12px; }
QLabel#toastText { color: %s; font-size: 13px; }

QFrame#statusBar { background: %s; border-top: 1px solid %s; border-radius: 0; }
QLabel#statusText { color: %s; font-size: 12px; }
""" % (
    FONT_FAMILY, BG_DARK, TEXT_MAIN,
    BG_SIDEBAR, "#141722", BORDER,
    TEXT_MAIN, TEXT_DIM,
    TEXT_DIM, TEXT_MAIN, TEXT_MAIN, ACCENT,
    BG_CARD, BORDER, TEXT_MAIN, TEXT_DIM, TEXT_DIM,
    ACCENT, ACCENT_HOVER, ACCENT_HOVER, ACCENT_PRESS, ACCENT_PRESS,
    ACCENT, DANGER,
    BG_INPUT, TEXT_MAIN, BORDER, ACCENT, ACCENT,
    TEXT_DIM, BG_CARD, TEXT_MAIN, BORDER,
    TEXT_MAIN, TEXT_MAIN, BORDER,
    "#2A3247", ACCENT,
    BG_INPUT, TEXT_MAIN, ACCENT, ACCENT_HOVER,
    TEXT_MAIN, BORDER, BG_INPUT, ACCENT, ACCENT,
    BG_SIDEBAR, BORDER, TEXT_DIM,
    TEXT_DIM, TEXT_MAIN, ACCENT, TEXT_MAIN,
    BORDER, TEXT_MAIN,
    BG_SIDEBAR, BORDER, TEXT_DIM,
)
