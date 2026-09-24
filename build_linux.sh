#!/usr/bin/env bash
# Nebula Launcher - Linux/macOS 打包脚本
set -e
echo "=== Nebula Launcher Build (Linux/macOS) ==="
pip show pyinstaller >/dev/null 2>&1 || pip install pyinstaller
pyinstaller --noconfirm --clean \
    --name "NebulaLauncher" \
    --windowed \
    --add-data "i18n:i18n" \
    --add-data "assets:assets" \
    --add-data "website:website" \
    main.py
echo "=== 打包完成: dist/NebulaLauncher/ ==="
