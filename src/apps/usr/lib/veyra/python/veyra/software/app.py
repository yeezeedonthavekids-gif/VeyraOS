"""VeyraOS Software — install apps from the official repositories and Flathub."""
from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from ..common import system
from ..common.ui import Card, CommandRunner, NavWindow, Page, init_app, label, primary_button
from . import backend
from .backend import App
from .catalog import CATEGORIES, catalog


class _Sig(QObject):
    done = Signal(object)


class Task(QRunnable):
    """Run a blocking function in the thread pool, deliver the result in the GUI thread."""

    def __init__(self, fn, cb):
        super().__init__()
        self.fn, self.sig = fn, _Sig()
        self.sig.done.connect(cb)

    def run(self):
        try:
            res = self.fn()
        except Exception as e:  # noqa: BLE001 — surfaced to the user
            res = e
        self.sig.done.emit(res)


class OperationDialog(QDialog):
    """Shows install/remove progress with the command output."""

    def __init__(self, parent, title: str, argv: list[str], status: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 380)
        v = QVBoxLayout(self)
        self.runner = CommandRunner()
        v.addWidget(self.runner, 1)
        self.close_btn = QPushButton("Close")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.close_btn)
        v.addLayout(row)
        self.ok = False
        self.runner.finished.connect(self._finished)
        QTimer.singleShot(0, lambda: self.runner.start(argv, status))

    def _finished(self, ok: bool):
        self.ok = ok
        self.close_btn.setEnabled(True)


class AppTile(Card):
    def __init__(self, app: App, on_action):
        super().__init__()
        self.app, self.on_action = app, on_action
        self.setMinimumWidth(250)
        top = QHBoxLayout()
        icon = QLabel()
        ic = QIcon.fromTheme(app.icon or app.id, QIcon.fromTheme("application-x-executable"))
        icon.setPixmap(ic.pixmap(40, 40))
        top.addWidget(icon)
        col = QVBoxLayout()
        name = QLabel(app.name)
        name.setObjectName("CardTitle")
        col.addWidget(name)
        src = label(app.source_label, subtle=True)
        col.addWidget(src)
        top.addLayout(col, 1)
        self.lay.addLayout(top)
        summ = label(app.summary or "", subtle=False)
        summ.setMinimumHeight(36)
        self.lay.addWidget(summ)
        self.btn = QPushButton()
        self.btn.clicked.connect(lambda: self.on_action(self.app))
        self.lay.addWidget(self.btn, 0, Qt.AlignRight)
        self.refresh()

    def refresh(self):
        if self.app.installed:
            self.btn.setText("Remove")
            self.btn.setObjectName("")
        else:
            self.btn.setText("Install")
            self.btn.setObjectName("Primary")
        self.btn.style().unpolish(self.btn)
        self.btn.style().polish(self.btn)


class TileGrid(QWidget):
    def __init__(self, cols: int = 3):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.cols = cols
        self.tiles: list[AppTile] = []

    def set_apps(self, apps: list[App], on_action):
        for t in self.tiles:
            t.setParent(None)
        self.tiles = []
        for i, a in enumerate(apps):
            t = AppTile(a, on_action)
            self.grid.addWidget(t, i // self.cols, i % self.cols)
            self.tiles.append(t)


class SoftwareWindow(NavWindow):
    def __init__(self):
        super().__init__("Software", (1180, 780))
        self.pool = QThreadPool.globalInstance()
        self.catalog = catalog()
        self.grids: list[TileGrid] = []

        # Home
        home = Page("Software", "Apps from the official VeyraOS (Artix/Arch) repositories and Flathub. "
                                "Everything is signed and verified; nothing comes from unknown sources.")
        if system.is_live_session():
            warn = Card("You are running the live system",
                        "Apps you install now live only in memory and disappear after a restart. "
                        "Install VeyraOS first to keep them.")
            home.add(warn)
        sb = QLineEdit()
        sb.setPlaceholderText("Search apps (e.g. 'discord', 'office', 'minecraft')…")
        sb.setClearButtonEnabled(True)
        sb.returnPressed.connect(lambda: self.do_search(sb.text()))
        home.add(sb)
        featured = [a for a in self.catalog if a.id in (
            "steam", "discord", "com.heroicgameslauncher.hgl", "libreoffice-fresh", "obs-studio", "com.spotify.Client")]
        home.add(label("<b>Popular</b>", rich=True))
        g = TileGrid()
        g.set_apps(featured, self.act)
        self.grids.append(g)
        home.add(g)
        home.finish()
        self.add_page("home", "Home", "go-home", home)

        # Category pages
        for key, title, icon in CATEGORIES:
            p = Page(title)
            g = TileGrid()
            g.set_apps([a for a in self.catalog if a.category == key], self.act)
            self.grids.append(g)
            p.add(g)
            p.finish()
            self.add_page(key, title, icon, p)

        # Search
        self.search_page = Page("Search")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search the repositories and Flathub…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.returnPressed.connect(lambda: self.do_search(self.search_box.text()))
        self.search_page.add(self.search_box)
        self.search_status = label("", subtle=True)
        self.search_page.add(self.search_status)
        self.search_grid = TileGrid()
        self.search_page.add(self.search_grid)
        self.search_page.finish()
        self.add_page("search", "Search", "search", self.search_page)

        # Installed
        self.inst_page = Page("Installed", "Applications you installed (not counting system components).")
        self.inst_status = label("Loading…", subtle=True)
        self.inst_page.add(self.inst_status)
        self.inst_grid = TileGrid()
        self.inst_page.add(self.inst_grid)
        self.inst_page.finish()
        self.add_page("installed", "Installed", "view-list-details", self.inst_page)

        upd = Page("Updates", "System and app updates are handled by the Updates app.")
        b = primary_button("Open Updates")
        b.clicked.connect(lambda: __import__("subprocess").Popen(["veyra-update"]))
        upd.add(b)
        upd.finish()
        self.add_page("updates", "Updates", "system-software-update", upd)

        self.nav.currentRowChanged.connect(self._page_changed)
        self.refresh_installed_state()

    # -------------------------------------------------------------- state ---
    def refresh_installed_state(self):
        def work():
            return backend.installed_repo_names(), backend.installed_flatpak_ids()

        def done(res):
            if isinstance(res, Exception):
                return
            repo, flat = res
            for g in self.grids + [self.search_grid]:
                for t in g.tiles:
                    t.app.installed = t.app.id in (repo if t.app.source == "repo" else flat)
                    t.refresh()
        self.pool.start(Task(work, done))

    def _page_changed(self, idx):
        if self.stack.widget(idx) is self.inst_page:
            self.load_installed()

    def load_installed(self):
        self.inst_status.setText("Loading…")

        def done(res):
            if isinstance(res, Exception):
                self.inst_status.setText(f"Could not list installed apps: {res}")
                return
            # Only show user-facing apps: repo packages that have a desktop entry are
            # hard to detect cheaply, so show Flatpaks + catalogue apps that are installed.
            cat_ids = {a.id: a for a in self.catalog}
            shown = []
            for a in res:
                if a.source == "flatpak":
                    shown.append(a)
                elif a.id in cat_ids:
                    c = cat_ids[a.id]
                    shown.append(App(a.id, c.name, c.summary, "repo", a.version, c.icon, c.category, True))
            self.inst_grid.set_apps(shown, self.act)
            self.inst_status.setText(f"{len(shown)} apps" if shown else
                                     "No additional apps installed yet. Browse the categories to get started.")
        self.pool.start(Task(backend.installed_apps, done))

    def do_search(self, text: str):
        self.show_page("search")
        self.search_box.setText(text)
        if len(text.strip()) < 2:
            self.search_status.setText("Type at least two characters.")
            return
        self.search_status.setText(f"Searching for “{text}”…")

        def done(res):
            if isinstance(res, Exception):
                self.search_status.setText(f"Search failed: {res}")
                return
            res = res[:60]
            self.search_grid.set_apps(res, self.act)
            self.search_status.setText(f"{len(res)} results" if res else "No results. Check the spelling, or try a more general term.")
        self.pool.start(Task(lambda: backend.search(text), done))

    # ------------------------------------------------------------ actions ---
    def act(self, app: App):
        if app.installed:
            if QMessageBox.question(self, "Remove app", f"Remove {app.name}?") != QMessageBox.Yes:
                return
            argv, title, status = backend.remove_argv(app), f"Removing {app.name}", f"Removing {app.name}…"
        else:
            argv, title, status = backend.install_argv(app), f"Installing {app.name}", \
                f"Installing {app.name} from {app.source_label}…"
        dlg = OperationDialog(self, title, argv, status)
        dlg.exec()
        self.refresh_installed_state()


def main() -> int:
    app = init_app("veyra-software", "Software", "veyra-software")
    w = SoftwareWindow()
    if len(sys.argv) > 2 and sys.argv[1] == "--search":
        w.do_search(" ".join(sys.argv[2:]))
    w.show()
    return app.exec()
