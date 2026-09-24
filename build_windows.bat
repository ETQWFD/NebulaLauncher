@echo off
chcp 65001 >nul
title Nebula Launcher Build (Windows)
echo ============================================
echo   Nebula Launcher - Windows 打包脚本
echo ============================================
echo.
echo [1/3] 检查 PyInstaller...
pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo 未安装，正在安装 PyInstaller...
    pip install pyinstaller
)
echo.
echo [2/3] 开始打包（首次约需 2-5 分钟）...
pyinstaller --noconfirm --clean ^
    --name "NebulaLauncher" ^
    --windowed ^
    --icon assets/icon.ico ^
    --add-data "i18n;i18n" ^
    --add-data "assets;assets" ^
    --add-data "website;website" ^
    main.py
echo.
echo [3/3] 复制资源到 dist...
xcopy /E /I /Y i18n dist\NebulaLauncher\_internal\i18n >nul 2>nul
echo.
echo ============================================
echo   打包完成！可执行文件位于: dist\NebulaLauncher\NebulaLauncher.exe
echo ============================================
pause
