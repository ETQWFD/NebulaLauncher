# -*- coding: utf-8 -*-
"""通用自定义控件：卡片、Toast、导航按钮、开关等."""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, Property
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)


class Card(QFrame):
    """圆角卡片容器。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(22, 18, 22, 18)
        self._layout.setSpacing(10)


class NavButton(QPushButton):
    """侧边栏导航按钮。"""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setProperty("nav", True)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(f"   {icon}    {text}")


class Toast(QFrame):
    """右下角淡入淡出提示。"""

    def __init__(self, parent: QWidget, text: str, ok: bool = True):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        dot = QLabel("●" if ok else "○")
        dot.setStyleSheet(f"color: {'#3ECF8E' if ok else '#FFB84D'}; font-size: 12px;")
        lbl = QLabel(text)
        lbl.setObjectName("toastText")
        lay.addWidget(dot)
        lay.addWidget(lbl)
        self.adjustSize()
        self._op = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._op)
        self._anim = QPropertyAnimation(self._op, b"opacity", self)
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)

    def show_toast(self, duration: int = 2600):
        if self.parent():
            pw, ph = self.parent().width(), self.parent().height()
            self.move(pw - self.width() - 24, ph - self.height() - 70)
        self.show()
        self.raise_()
        self._anim.start()
        self._hide_timer.start(duration)

    def fade_out(self):
        out = QPropertyAnimation(self._op, b"opacity", self)
        out.setDuration(300)
        out.setStartValue(1.0)
        out.setEndValue(0.0)
        out.finished.connect(self.hide)
        out.start()
        self._out = out


class ToggleSwitch(QPushButton):
    """滑动开关。"""

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._t = 0.0
        self._anim = QPropertyAnimation(self, b"t", self)
        self._anim.setDuration(180)
        self.clicked.connect(self._toggle)

    def _toggle(self):
        self._checked = not self._checked
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(1.0 if self._checked else 0.0)
        self._anim.start()

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, v: bool):
        self._checked = v
        self._t = 1.0 if v else 0.0
        self.update()

    def get_t(self):
        return self._t

    def set_t(self, v: float):
        self._t = v
        self.update()

    t = Property(float, get_t, set_t)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        # 轨道
        col = QColor("#3D8BFF") if self._checked else QColor("#2A3247")
        p.setBrush(col)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r, r)
        # 滑块
        x = (w - h + 2) * self._t + 2
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 2, h - 4, h - 4))


class StarIcon(QWidget):
    """自定义星云 Logo（渐变圆 + 星点）。"""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        grad = QColor("#3D8BFF")
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))
        # 星云亮点
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawEllipse(QRectF(s * 0.28, s * 0.24, s * 0.18, s * 0.18))
        p.drawEllipse(QRectF(s * 0.55, s * 0.52, s * 0.11, s * 0.11))
        p.setBrush(QColor(255, 255, 255, 140))
        p.drawEllipse(QRectF(s * 0.62, s * 0.18, s * 0.07, s * 0.07))
        p.drawEllipse(QRectF(s * 0.20, s * 0.60, s * 0.07, s * 0.07))


class PageIndicator(QWidget):
    """页面标题行（标题 + 副标题）。"""

    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.title_lbl = QLabel(title)
        self.title_lbl.setProperty("title", True)
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setProperty("subtitle", True)
        lay.addWidget(self.title_lbl)
        lay.addWidget(self.sub_lbl)

    def set_text(self, title: str, subtitle: str = ""):
        self.title_lbl.setText(title)
        self.sub_lbl.setText(subtitle)
