# -*- coding: utf-8 -*-
"""模组管理页：已安装模组 / GitHub Releases 模组仓库 / Modrinth 官方源。"""
import os
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QTabWidget,
                               QVBoxLayout, QWidget)

from .. import i18n
from ..mods.github_source import GithubModSource, ModFile
from ..mods.manager import ModManager
from ..mods.modrinth_source import ModrinthSource
from .tasks import TaskWorker
from .widgets import PageIndicator


class ModsPage(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.settings = win.settings
        self.manager = ModManager(win.settings.game_dir())
        self.github = None
        self.modrinth = ModrinthSource()
        self._github_cache = []
        self.worker = None
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 26, 30, 20)
        outer.setSpacing(14)

        self.indicator = PageIndicator()
        outer.addWidget(self.indicator)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)

        # 标签1：已安装
        self.installed_list = QListWidget()
        self.installed_list.setObjectName("modList")
        self.tabs.addTab(self.installed_list, "installed")

        # 标签2：GitHub 仓库
        gh = QWidget()
        gl = QVBoxLayout(gh)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(8)
        row = QHBoxLayout()
        self.gh_repo_edit = QLineEdit(self.settings.get("github_mods_repo"))
        self.gh_repo_edit.setPlaceholderText("owner/repo")
        btn_gh = QPushButton("refresh")
        btn_gh.setProperty("ghost", True)
        btn_gh.clicked.connect(self.load_github)
        row.addWidget(self.gh_repo_edit, 1)
        row.addWidget(btn_gh)
        gl.addLayout(row)
        self.github_list = QListWidget()
        self.github_list.setObjectName("modList")
        gl.addWidget(self.github_list, 1)
        self.tabs.addTab(gh, "github")

        # 标签3：Modrinth
        mr = QWidget()
        ml = QVBoxLayout(mr)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(8)
        srow = QHBoxLayout()
        self.mr_search = QLineEdit()
        self.mr_search.setPlaceholderText("search mods...")
        self.mr_search.returnPressed.connect(self.search_modrinth)
        btn_mr = QPushButton("search")
        btn_mr.setProperty("ghost", True)
        btn_mr.clicked.connect(self.search_modrinth)
        srow.addWidget(self.mr_search, 1)
        srow.addWidget(btn_mr)
        ml.addLayout(srow)
        self.mr_list = QListWidget()
        self.mr_list.setObjectName("modList")
        ml.addWidget(self.mr_list, 1)
        self.tabs.addTab(mr, "modrinth")

        # 标签4：整合包（Modrinth + 本地导入）
        mp = QWidget()
        mpl = QVBoxLayout(mp)
        mpl.setContentsMargins(0, 0, 0, 0)
        mpl.setSpacing(8)
        prow = QHBoxLayout()
        self.mp_search = QLineEdit()
        self.mp_search.setPlaceholderText("search modpacks...")
        self.mp_search.returnPressed.connect(self.search_modpacks)
        btn_mp = QPushButton("search")
        btn_mp.setProperty("ghost", True)
        btn_mp.clicked.connect(self.search_modpacks)
        btn_imp = QPushButton("import")
        btn_imp.setProperty("ghost", True)
        btn_imp.clicked.connect(self.import_modpack)
        prow.addWidget(self.mp_search, 1)
        prow.addWidget(btn_mp)
        prow.addWidget(btn_imp)
        mpl.addLayout(prow)
        self.mp_list = QListWidget()
        self.mp_list.setObjectName("modList")
        mpl.addWidget(self.mp_list, 1)
        self.tabs.addTab(mp, "modpack")

        # 标签5：光影（Modrinth 搜索 + 已安装管理）
        sh = QWidget()
        shl = QVBoxLayout(sh)
        shl.setContentsMargins(0, 0, 0, 0)
        shl.setSpacing(8)
        srow2 = QHBoxLayout()
        self.sh_search = QLineEdit()
        self.sh_search.setPlaceholderText("search shaders...")
        self.sh_search.returnPressed.connect(self.search_shaders)
        btn_sh = QPushButton("search")
        btn_sh.setProperty("ghost", True)
        btn_sh.clicked.connect(self.search_shaders)
        srow2.addWidget(self.sh_search, 1)
        srow2.addWidget(btn_sh)
        shl.addLayout(srow2)
        self.sh_list = QListWidget()
        self.sh_list.setObjectName("modList")
        shl.addWidget(self.sh_list, 1)
        lbl_sh = QLabel("installed shaders")
        lbl_sh.setProperty("section", True)
        shl.addWidget(lbl_sh)
        self.sh_installed = QListWidget()
        self.sh_installed.setObjectName("modList")
        shl.addWidget(self.sh_installed, 1)
        self.tabs.addTab(sh, "shader")

        self.retranslate()

    # ------------------------------------------------------------------
    def retranslate(self):
        tr = i18n.tr
        self.indicator.set_text(tr("mods_title"), tr("mods_subtitle"))
        self.tabs.setTabText(0, tr("mods_installed"))
        self.tabs.setTabText(1, "GitHub Releases")
        self.tabs.setTabText(2, "Modrinth")
        self.tabs.setTabText(3, tr("modpack_tab"))
        self.tabs.setTabText(4, tr("shader_tab"))
        self.mr_search.setPlaceholderText(tr("mods_search_hint"))
        self.mp_search.setPlaceholderText(tr("modpack_search_hint"))
        self.sh_search.setPlaceholderText(tr("mods_search_hint"))
        self.refresh_installed()
        self.refresh_shaders()
        if self._github_cache:
            self.load_github()

    # ------------------------------------------------------------------
    def refresh_installed(self):
        mods = self.manager.scan()
        self.installed_list.clear()
        for m in mods:
            item = QListWidgetItem()
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(10, 4, 10, 4)
            nm = QLabel(m.name)
            nm.setStyleSheet("font-size:13px; color:#EAF0FF;" + ("" if m.enabled else "color:#5A6275;"))
            sz = QLabel(f"{m.size/1024/1024:.2f} MB")
            sz.setProperty("subtitle", True)
            btn_t = QPushButton(i18n.tr("mods_disable") if m.enabled else i18n.tr("mods_enable"))
            btn_t.setProperty("ghost", True)
            btn_t.setCursor(Qt.PointingHandCursor)
            btn_d = QPushButton(i18n.tr("ver_delete"))
            btn_d.setProperty("danger", True)
            btn_d.setCursor(Qt.PointingHandCursor)
            btn_t.clicked.connect(lambda _, mm=m: self._toggle(mm))
            btn_d.clicked.connect(lambda _, mm=m: self._remove(mm))
            lay.addWidget(nm, 1)
            lay.addWidget(sz)
            lay.addWidget(btn_t)
            lay.addWidget(btn_d)
            self.installed_list.addItem(item)
            self.installed_list.setItemWidget(item, w)
            item.setSizeHint(w.sizeHint())

    def _toggle(self, mod):
        self.manager.toggle(mod)
        self.refresh_installed()

    def _remove(self, mod):
        self.manager.remove(mod)
        self.refresh_installed()
        self.win.toast(i18n.tr("mods_removed").format(m=mod.name))

    # ------------------------------------------------------------------
    def load_github(self):
        repo = self.gh_repo_edit.text().strip()
        if not repo:
            return
        self.settings.set("github_mods_repo", repo)
        self.github = GithubModSource(repo)
        self.win.set_status(i18n.tr("mods_github_loading"))

        def job(progress=None, stage_cb=None, cancel=None):
            return self.github.releases()

        def ok(releases):
            self._github_cache = releases
            self.github_list.clear()
            for rel in releases:
                if not rel.assets:
                    continue
                for a in rel.assets:
                    item = QListWidgetItem()
                    w = QWidget()
                    lay = QHBoxLayout(w)
                    lay.setContentsMargins(10, 4, 10, 4)
                    nm = QLabel(a.name)
                    nm.setStyleSheet("font-size:13px; color:#EAF0FF;")
                    info = QLabel(f"{a.version} · {a.size/1024/1024:.2f} MB")
                    info.setProperty("subtitle", True)
                    btn = QPushButton(i18n.tr("mods_install"))
                    btn.setProperty("primary", True)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.clicked.connect(lambda _, m=a: self._install_mod(m))
                    lay.addWidget(nm, 1)
                    lay.addWidget(info)
                    lay.addWidget(btn)
                    self.github_list.addItem(item)
                    self.github_list.setItemWidget(item, w)
                    item.setSizeHint(w.sizeHint())
            self.win.set_status(i18n.tr("mods_github_ok").format(n=len(self._github_cache)))
            self.win.toast(i18n.tr("mods_github_ok").format(n=len(self._github_cache)))

        def fail(e):
            self.win.set_status(str(e))
            self.win.toast(str(e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def _install_mod(self, mod: ModFile):
        self.win.set_status(i18n.tr("mods_downloading").format(m=mod.name))

        def job(progress=None, stage_cb=None, cancel=None):
            if mod.source == "modrinth":
                return self.modrinth.download(mod, self.manager.dir, progress=progress)
            return self.github.download(mod, self.manager.dir, progress=progress)

        def ok(path):
            self.refresh_installed()
            self.win.toast(i18n.tr("mods_installed_ok").format(m=mod.name))
            self.win.set_status(i18n.tr("mods_installed_ok").format(m=mod.name))

        def fail(e):
            self.win.toast(i18n.tr("mods_install_fail").format(m=mod.name, e=e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    # ------------------------------------------------------------------
    def search_modrinth(self):
        query = self.mr_search.text().strip()
        if not query:
            return
        self.win.set_status(i18n.tr("mods_searching"))

        def job(progress=None, stage_cb=None, cancel=None):
            return self.modrinth.search(query, limit=20)

        def ok(hits):
            self.mr_list.clear()
            for h in hits:
                item = QListWidgetItem()
                w = QWidget()
                lay = QHBoxLayout(w)
                lay.setContentsMargins(10, 4, 10, 4)
                nm = QLabel(h.get("title", h.get("slug", "?")))
                nm.setStyleSheet("font-size:13px; color:#EAF0FF;")
                info = QLabel(f"{h.get('project_type','')} · {h.get('downloads',0)} DL")
                info.setProperty("subtitle", True)
                btn = QPushButton(i18n.tr("mods_install"))
                btn.setProperty("primary", True)
                btn.setCursor(Qt.PointingHandCursor)
                pid = h.get("project_id")
                btn.clicked.connect(lambda _, p=pid, t=h.get("title"): self._install_modrinth(p, t))
                lay.addWidget(nm, 1)
                lay.addWidget(info)
                lay.addWidget(btn)
                self.mr_list.addItem(item)
                self.mr_list.setItemWidget(item, w)
                item.setSizeHint(w.sizeHint())
            self.win.set_status(i18n.tr("mods_search_ok").format(n=len(hits)))

        def fail(e):
            self.win.toast(str(e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def _install_modrinth(self, project_id, title):
        def job(progress=None, stage_cb=None, cancel=None):
            vers = self.modrinth.versions(project_id)
            if not vers:
                raise RuntimeError(i18n.tr("mods_no_version"))
            mod = self.modrinth.pick_file(vers[0])
            if not mod:
                raise RuntimeError(i18n.tr("mods_no_file"))
            return self.modrinth.download(mod, self.manager.dir, progress=progress)

        def ok(path):
            self.refresh_installed()
            self.win.toast(i18n.tr("mods_installed_ok").format(m=title))

        def fail(e):
            self.win.toast(i18n.tr("mods_install_fail").format(m=title, e=e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    # ------------------------------------------------------------------
    # 整合包
    # ------------------------------------------------------------------
    def search_modpacks(self):
        query = self.mp_search.text().strip()
        if not query:
            return
        from ..mods.modpack import ModpackInstaller

        def job(progress=None, stage_cb=None, cancel=None):
            return ModpackInstaller.search(query, limit=15)

        def ok(hits):
            self.mp_list.clear()
            if not hits:
                self.win.toast(i18n.tr("modpack_no_result"), ok=False)
            for h in hits:
                item = QListWidgetItem()
                w = QWidget()
                lay = QHBoxLayout(w)
                lay.setContentsMargins(10, 4, 10, 4)
                nm = QLabel(h.get("title", "?"))
                nm.setStyleSheet("font-size:13px; color:#EAF0FF;")
                info = QLabel(f"整合包 · {h.get('downloads', 0)} DL")
                info.setProperty("subtitle", True)
                btn = QPushButton(i18n.tr("modpack_install"))
                btn.setProperty("primary", True)
                btn.setCursor(Qt.PointingHandCursor)
                pid = h.get("project_id")
                btn.clicked.connect(lambda _, p=pid, t=h.get("title"): self._install_modpack(p, t))
                lay.addWidget(nm, 1)
                lay.addWidget(info)
                lay.addWidget(btn)
                self.mp_list.addItem(item)
                self.mp_list.setItemWidget(item, w)
                item.setSizeHint(w.sizeHint())

        def fail(e):
            self.win.toast(str(e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def _install_modpack(self, project_id, title):
        from ..mods.modpack import ModpackInstaller
        inst = ModpackInstaller(self.settings.game_dir())
        self.win.set_status(i18n.tr("modpack_install") + " " + title)

        def job(progress=None, stage_cb=None, cancel=None):
            vers = ModpackInstaller.versions(project_id)
            if not vers:
                raise RuntimeError(i18n.tr("mods_no_version"))
            vi = vers[0]
            f = ModpackInstaller.version_file(vi)
            if not f:
                raise RuntimeError(i18n.tr("mods_no_file"))
            url = f.get("url") or next((u for u in f.get("urls", []) if u), None)
            if not url:
                raise RuntimeError(i18n.tr("mods_no_file"))
            import io
            data = utils_http_get(url)
            return inst.install_mrpack_bytes(data, name=title, progress=progress, stage_cb=stage_cb, cancel=cancel)

        def ok(info):
            self.refresh_installed()
            self.win.toast(i18n.tr("modpack_installed").format(name=info["name"], mods=info["mods"]))

        def fail(e):
            self.win.toast(i18n.tr("modpack_fail").format(e=e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def import_modpack(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("modpack_import"),
                                              "", "Modpack (*.mrpack *.zip)")
        if not path:
            return
        from ..mods.modpack import ModpackInstaller
        inst = ModpackInstaller(self.settings.game_dir())

        def job(progress=None, stage_cb=None, cancel=None):
            return inst.install_mrpack_file(path, progress=progress, stage_cb=stage_cb, cancel=cancel)

        def ok(info):
            self.refresh_installed()
            self.win.toast(i18n.tr("modpack_installed").format(name=info["name"], mods=info["mods"]))

        def fail(e):
            self.win.toast(i18n.tr("modpack_fail").format(e=e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    # ------------------------------------------------------------------
    # 光影
    # ------------------------------------------------------------------
    def refresh_shaders(self):
        from ..mods.shader import ShaderManager
        mgr = ShaderManager(self.settings.game_dir())
        self.sh_installed.clear()
        for s in mgr.scan():
            item = QListWidgetItem()
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(10, 4, 10, 4)
            nm = QLabel(s.name)
            nm.setStyleSheet("font-size:13px; color:#EAF0FF;")
            sz = QLabel(f"{s.size/1024/1024:.2f} MB")
            sz.setProperty("subtitle", True)
            btn_d = QPushButton(i18n.tr("ver_delete"))
            btn_d.setProperty("danger", True)
            btn_d.setCursor(Qt.PointingHandCursor)
            btn_d.clicked.connect(lambda _, ss=s: self._remove_shader(ss))
            lay.addWidget(nm, 1)
            lay.addWidget(sz)
            lay.addWidget(btn_d)
            self.sh_installed.addItem(item)
            self.sh_installed.setItemWidget(item, w)
            item.setSizeHint(w.sizeHint())

    def _remove_shader(self, shader):
        from ..mods.shader import ShaderManager
        mgr = ShaderManager(self.settings.game_dir())
        mgr.remove(shader)
        self.refresh_shaders()
        self.win.toast(i18n.tr("shader_installed").format(name=shader.name))

    def search_shaders(self):
        query = self.sh_search.text().strip()
        if not query:
            return
        from ..mods.shader import ModrinthShaders
        src = ModrinthShaders()

        def job(progress=None, stage_cb=None, cancel=None):
            return src.search(query, limit=15)

        def ok(hits):
            self.sh_list.clear()
            if not hits:
                self.win.toast(i18n.tr("shader_no_result"), ok=False)
            for h in hits:
                item = QListWidgetItem()
                w = QWidget()
                lay = QHBoxLayout(w)
                lay.setContentsMargins(10, 4, 10, 4)
                nm = QLabel(h.get("title", "?"))
                nm.setStyleSheet("font-size:13px; color:#EAF0FF;")
                info = QLabel(f"光影 · {h.get('downloads', 0)} DL")
                info.setProperty("subtitle", True)
                btn = QPushButton(i18n.tr("shader_download"))
                btn.setProperty("primary", True)
                btn.setCursor(Qt.PointingHandCursor)
                pid = h.get("project_id")
                btn.clicked.connect(lambda _, p=pid, t=h.get("title"): self._install_shader(p, t))
                lay.addWidget(nm, 1)
                lay.addWidget(info)
                lay.addWidget(btn)
                self.sh_list.addItem(item)
                self.sh_list.setItemWidget(item, w)
                item.setSizeHint(w.sizeHint())

        def fail(e):
            self.win.toast(str(e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def _install_shader(self, project_id, title):
        from ..mods.shader import ModrinthShaders, ShaderManager
        src = ModrinthShaders()
        mgr = ShaderManager(self.settings.game_dir())

        def job(progress=None, stage_cb=None, cancel=None):
            vers = src.versions(project_id)
            if not vers:
                raise RuntimeError(i18n.tr("mods_no_version"))
            f = src.pick_file(vers[0])
            if not f:
                raise RuntimeError(i18n.tr("mods_no_file"))
            return src.download(f, mgr.dir, progress=progress)

        def ok(path):
            self.refresh_shaders()
            self.win.toast(i18n.tr("shader_installed").format(name=title))

        def fail(e):
            self.win.toast(i18n.tr("mods_install_fail").format(m=title, e=e), ok=False)

        self.worker = TaskWorker(job)
        self.worker.finished_ok.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()


def utils_http_get(url: str, timeout: int = 120) -> bytes:
    """下载整合包文件到内存（供 mrpack 解析）。"""
    import requests
    r = requests.get(url, timeout=timeout, stream=True)
    r.raise_for_status()
    return r.content
