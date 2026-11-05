"""VeyraOS Updates — check and install system and app updates.

    veyra-update            open the window
    veyra-update --notify   background notifier (session autostart): checks
                            every few hours and shows a notification
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

from ..common import system

NEWS_FEEDS = [("Arch Linux", "https://archlinux.org/feeds/news/"),
              ("Artix Linux", "https://artixlinux.org/feed.php")]
CHECK_INTERVAL = 6 * 3600


@dataclass
class Update:
    name: str
    old: str
    new: str
    source: str  # "system" | "flatpak"


def parse_checkupdates(out: str) -> list[Update]:
    """`checkupdates` lines: 'name old -> new'"""
    ups = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[2] == "->":
            ups.append(Update(parts[0], parts[1], parts[3], "system"))
    return ups


def parse_flatpak_updates(out: str) -> list[Update]:
    """`flatpak remote-ls --updates --columns=application,version`"""
    ups = []
    for line in out.splitlines():
        cols = line.split("\t")
        if cols and "." in cols[0]:
            ups.append(Update(cols[0], "", cols[1] if len(cols) > 1 else "", "flatpak"))
    return ups


def check() -> tuple[list[Update], str]:
    """Returns (updates, error message or '')."""
    ups: list[Update] = []
    err = ""
    if system.which("checkupdates"):
        rc, out = system.run(["checkupdates"], timeout=180)
        # checkupdates: 0 = updates, 2 = none, 1 = error
        if rc == 0:
            ups += parse_checkupdates(out)
        elif rc != 2:
            err = "Could not check for system updates (no internet connection?)."
    else:
        err = "checkupdates is missing (package pacman-contrib)."
    if system.which("flatpak"):
        rc, out = system.run(["flatpak", "remote-ls", "--system", "--updates",
                              "--columns=application,version"], timeout=120)
        if rc == 0:
            ups += parse_flatpak_updates(out)
    return ups, err


def parse_news(xml_text: str, source: str, max_age_days: int = 45) -> list[tuple[str, str, str, str]]:
    """RSS -> [(source, date, title, link)] for recent items."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    now = time.time()
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or ""
        try:
            dt = parsedate_to_datetime(pub)
            if now - dt.timestamp() > max_age_days * 86400:
                continue
            date = dt.strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date = ""
        if title:
            items.append((source, date, title, link))
    return items[:5]


def fetch_news() -> list[tuple[str, str, str, str]]:
    news = []
    for src, url in NEWS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VeyraOS-Updates/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                news += parse_news(r.read(2_000_000).decode("utf-8", "replace"), src)
        except Exception:  # noqa: BLE001 — news is best-effort
            continue
    return news


# ------------------------------------------------------------------- notifier ---
def gaming_active() -> bool:
    rt = os.environ.get("XDG_RUNTIME_DIR", "")
    return system.gaming_mode_active() or (rt and os.path.exists(os.path.join(rt, "veyra-gaming-mode.active")))


def notify_loop():
    time.sleep(300)  # let the session settle after login
    last_count = -1
    while True:
        if system.auto_update_mode() != "off" and not gaming_active() and not system.is_live_session():
            ups, _err = check()
            if ups and len(ups) != last_count:
                n = len(ups)
                try:
                    res = subprocess.run(
                        ["notify-send", "-a", "Updates", "-i", "system-software-update", "-A", "open=View updates",
                         "-w", f"{n} update{'s' if n != 1 else ''} available",
                         "Keep VeyraOS secure and up to date."],
                        stdout=subprocess.PIPE, text=True, timeout=3600)
                    if res.stdout.strip() == "open":
                        subprocess.Popen(["veyra-update"], start_new_session=True)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            last_count = len(ups)
        time.sleep(CHECK_INTERVAL)


# ------------------------------------------------------------------------- GUI ---
def run_gui() -> int:
    from PySide6.QtCore import QThreadPool, QTimer
    from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

    from ..common.ui import Card, CommandRunner, init_app, label, primary_button
    from ..software.app import Task

    app = init_app("veyra-update", "Updates", "system-software-update")

    class Win(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Updates")
            self.resize(860, 640)
            c = QWidget()
            v = QVBoxLayout(c)
            v.setContentsMargins(24, 20, 24, 20)
            v.setSpacing(12)
            t = label("Updates")
            t.setObjectName("PageTitle")
            v.addWidget(t)
            self.status = label("Checking for updates…", subtle=True)
            v.addWidget(self.status)
            self.news_card = Card("News that may need your attention")
            self.news_card.hide()
            v.addWidget(self.news_card)
            self.tree = QTreeWidget()
            self.tree.setHeaderLabels(["Name", "Installed", "New version", "Type"])
            self.tree.setRootIsDecorated(False)
            self.tree.setAlternatingRowColors(True)
            v.addWidget(self.tree, 2)
            self.runner = CommandRunner()
            self.runner.hide()
            v.addWidget(self.runner, 2)
            row = QHBoxLayout()
            if system.is_live_session():
                row.addWidget(label("Updates are disabled on the live medium.", subtle=True), 1)
            else:
                row.addStretch(1)
            self.check_btn = QPushButton("Check again")
            self.check_btn.clicked.connect(self.check)
            self.install_btn = primary_button("Install all updates")
            self.install_btn.setEnabled(False)
            self.install_btn.clicked.connect(self.install)
            row.addWidget(self.check_btn)
            row.addWidget(self.install_btn)
            v.addLayout(row)
            self.setCentralWidget(c)
            self.pool = QThreadPool.globalInstance()
            self.updates: list[Update] = []
            self.steps: list[tuple[list[str], str]] = []
            self.runner.finished.connect(self.step_done)
            QTimer.singleShot(0, self.check)
            self.pool.start(Task(fetch_news, self.show_news))

        def show_news(self, news):
            if isinstance(news, Exception) or not news:
                return
            for src, date, title, link in news:
                self.news_card.add(label(f'{date} · {src}: <a href="{link}">{title}</a>', rich=True))
            self.news_card.add(label("Rolling-release news occasionally lists a manual step. Read new items "
                                     "before updating.", subtle=True))
            self.news_card.show()

        def check(self):
            self.status.setText("Checking for updates…")
            self.check_btn.setEnabled(False)
            self.install_btn.setEnabled(False)
            self.pool.start(Task(check, self.checked))

        def checked(self, res):
            self.check_btn.setEnabled(True)
            if isinstance(res, Exception):
                self.status.setText(f"Check failed: {res}")
                return
            self.updates, err = res
            self.tree.clear()
            for u in self.updates:
                QTreeWidgetItem(self.tree, [u.name, u.old, u.new, "System" if u.source == "system" else "App (Flatpak)"])
            for i in range(4):
                self.tree.resizeColumnToContents(i)
            n = len(self.updates)
            if err:
                self.status.setText(err)
            elif n:
                self.status.setText(f"{n} update{'s' if n != 1 else ''} available.")
            else:
                self.status.setText("You're up to date.")
            self.install_btn.setEnabled(n > 0 and not system.is_live_session())

        def install(self):
            self.steps = []
            if any(u.source == "system" for u in self.updates):
                self.steps.append((system.helper_argv("system-update"), "Installing system updates…"))
            if any(u.source == "flatpak" for u in self.updates):
                self.steps.append((["flatpak", "update", "--system", "-y", "--noninteractive"], "Updating apps…"))
            self.install_btn.setEnabled(False)
            self.check_btn.setEnabled(False)
            self.runner.show()
            self.next_step()

        def next_step(self):
            if self.steps:
                argv, msg = self.steps.pop(0)
                self.runner.start(argv, msg)
            else:
                self.check_btn.setEnabled(True)
                self.status.setText("Updates installed. Restart the computer if the kernel or graphics driver was updated.")
                self.check()

        def step_done(self, ok: bool):
            if ok:
                self.next_step()
            else:
                self.steps = []
                self.check_btn.setEnabled(True)

    w = Win()
    w.show()
    return app.exec()


def main() -> int:
    if "--notify" in sys.argv:
        notify_loop()
        return 0
    return run_gui()
