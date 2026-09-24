# Nebula Launcher · 星云启动器

一个优雅、流畅、真正可用的 Minecraft Java 版启动器，界面仿照 PCL（Plain Craft Launcher），支持 **22 种语言**，内置模组中心与内存优化。

![启动页](website/assets/screenshot_home.png)

## ✨ 特性

- 🎨 **PCL 风格界面**：左侧导航 + 卡片布局，深蓝主题，开箱即用
- 🌐 **22 种界面语言**：中 / 英 / 日 / 韩 / 法 / 德 / 西 / 俄 / 葡 / 意 / 波 / 荷 / 土 / 越 / 泰 / 印尼 / 乌 / 印地 / 阿 / 马来 / 菲律宾 / 繁中
- 🧩 **全加载器支持**：原版（Vanilla）、Fabric、Quilt、Forge 一键安装
- 📦 **模组中心**：连接 GitHub Releases 模组仓库 + Modrinth 官方源，按需下载
- ⚡ **内存优化**：内置 Aikar's Flags（G1GC 调优等），防内存流失、提升帧率
- 🚀 **一键起飞**：启动游戏后自动关闭启动器，只让 Minecraft 单独运行
- 🔄 **多镜像源**：官方 Mojang 源 + BMCLAPI 镜像，国内也能快速下载
- ☕ **Java 自动管理**：自动检测/下载对应版本 Java（Temurin）

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动（单文件入口）
python main.py
```

> 需要 Python 3.10+。Java 可以由启动器自动下载（正版需微软账号，离线可任意昵称）。

## 📦 打包为可执行文件

- **Windows**：双击 `build_windows.bat`（需已安装 Python + PyInstaller）
- **Linux/macOS**：运行 `bash build_linux.sh`

打包产物在 `dist/` 目录。

## 🗂 项目结构

```
NebulaLauncher/
├── main.py                  # 唯一入口
├── launcher/
│   ├── minecraft/           # 版本清单、安装、启动、Fabric/Forge
│   ├── mods/                # 模组源（GitHub Releases / Modrinth）
│   └── ui/                  # PCL 风格界面
├── i18n/                    # 22 种语言文件
├── website/                 # 官网静态资源
├── index.html               # 官网（GitHub Pages 部署）
└── tools/                   # 构建辅助脚本
```

## 🧩 模组仓库

模组分发走 GitHub Releases：[NebulaLauncher-Mods](https://github.com/et2416444244/NebulaLauncher-Mods)

1. 在模组仓库创建 Release，把 `.jar` 模组文件作为附件上传
2. 启动器「模组中心 → GitHub Releases」页签会自动拉取并显示
3. 玩家点击「安装」即可下载到 `.minecraft/mods/`

## 🔒 安全说明

- 启动参数内置 `-Dlog4j2.formatMsgNoLookups=true`（Log4Shell 防护）
- 离线模式不会收集任何个人信息

## 📄 开源协议

MIT License

---

*Minecraft 是 Mojang AB 的商标。本项目与 Mojang / Microsoft 无隶属关系，也不属于官方产品。*
