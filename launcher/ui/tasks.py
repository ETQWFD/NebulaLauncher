# -*- coding: utf-8 -*-
"""后台任务线程：安装版本、安装加载器、启动游戏等，通过信号回传 UI."""
import threading

from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    """通用后台任务。fn 为可调用对象，可接收 progress/stage 回调。"""

    progress = Signal(float, str)          # (0~1, stage 描述)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self._stop = threading.Event()

    def cancel(self):
        self._stop.set()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs,
                             progress=self.progress.emit,
                             stage_cb=self.progress.emit,
                             cancel=self._stop)
            self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class LaunchWorker(QThread):
    """启动游戏线程：启动后等待若干秒确认游戏存活，再通知主线程自关闭."""

    launched = Signal(object)          # GameProcess
    log = Signal(str)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            game = self.fn()
            # 等待最多 30s 确认游戏进程存活（未立即崩溃）
            import time
            for _ in range(30):
                if game.alive():
                    break
                time.sleep(1)
            if not game.alive():
                raise RuntimeError("游戏进程启动后立即退出，请查看日志")
            self.launched.emit(game)
        except Exception as e:
            self.failed.emit(str(e))
