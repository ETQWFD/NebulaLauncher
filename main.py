# -*- coding: utf-8 -*-
"""Nebula Launcher 入口：python main.py 一键启动."""
import os
import sys

# 确保能导入 launcher 包（兼容直接运行与打包后运行）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    from launcher.ui.main_window import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
