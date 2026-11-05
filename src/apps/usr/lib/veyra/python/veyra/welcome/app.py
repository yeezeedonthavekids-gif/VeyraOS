"""VeyraOS Welcome — shown at first login (and on the live medium)."""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QVBoxLayout, QWidget)

from ..common import system
from ..common.ui import Card, init_app, label, primary_button

DONE_FLAG = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "veyra", "welcome-done")
LOGO = "/usr/share/pixmaps/veyraos-wordmark.svg"

SHORTCUTS = [
    ("Meta", "Start menu"), ("Meta+E", "File Explorer"), ("Meta+I", "Settings"),
    ("Meta+L", "Lock"), ("Meta+D", "Show desktop"), ("Meta+Tab", "Task View"),
    ("Alt+Tab", "Switch windows"), ("Meta+←/→", "Snap window"), ("Meta+↑/↓", "Maximize / minimize"),
    ("Meta+Shift+S", "Screenshot"), ("Meta+V", "Clipboard history"), ("Ctrl+Shift+Esc", "Task Manager"),
    ("Meta+G", "Gaming Mode"), ("Meta+S", "Search"),
]


def launch(argv):
    try:
        subprocess.Popen(argv, start_new_session=True)
    except OSError:
        pass


class Welcome(QMainWindow):
    def __init__(self):
        super().__init__()
        live = system.is_live_session()
        self.setWindowTitle("Welcome to VeyraOS")
        self.resize(940, 700)
        c = QWidget()
        v = QVBoxLayout(c)
        v.setContentsMargins(32, 26, 32, 22)
        v.setSpacing(14)

        head = QHBoxLayout()
        logo = QLabel()
        pm = QPixmap(LOGO) if os.path.exists(LOGO) else QIcon.fromTheme("veyraos").pixmap(48, 48)
        if not pm.isNull():
            logo.setPixmap(pm.scaledToHeight(52, Qt.SmoothTransformation))
        head.addWidget(logo)
        head.addStretch(1)
        v.addLayout(head)
        title = label("Welcome! Let's get you set up." if not live else
                      "Welcome! Try VeyraOS, then install it when you're ready.")
        title.setObjectName("PageTitle")
        v.addWidget(title)
        v.addWidget(label("Everything works the way you know from Windows — Start menu, taskbar, File Explorer — "
                          "on a fast, private and secure Linux system.", subtle=True))

        grid = QGridLayout()
        grid.setSpacing(12)
        tiles = []
        if live:
            tiles.append(("Install VeyraOS", "Install alongside Windows or on a separate disk. "
                          "Nothing is erased without your confirmation.", "Install…", ["veyra-install"], True))
        tiles += [
            ("Get apps", "Discord, Spotify, Chrome, Office, VS Code and more — one click.",
             "Open Software", ["veyra-software"], not live),
            ("Set up gaming", "Steam, Proton and Lutris are ready. Turn on Steam Play for all games.",
             "Gaming settings", ["veyra-control", "gaming"], False),
            ("Install updates", "Get the latest security fixes and drivers.", "Open Updates", ["veyra-update"], False),
            ("Light or dark", "Pick the look you like. You can change it any time.", "Appearance",
             ["veyra-control", "appearance"], False),
            ("Graphics drivers", "Check your NVIDIA driver, Vulkan and CUDA status.", "Drivers",
             ["veyra-control", "graphics"], False),
            ("Restore points", "Set up Timeshift so updates can always be rolled back.", "Set up",
             ["veyra-control", "restore"], False),
        ]
        for i, (t, d, btn, argv, primary) in enumerate(tiles):
            card = Card(t, d)
            b = primary_button(btn) if primary else QPushButton(btn)
            b.clicked.connect(lambda _=False, a=argv: launch(a))
            card.add(b)
            grid.addWidget(card, i // 3, i % 3)
        v.addLayout(grid)

        sc = Card("Keyboard shortcuts")
        sg = QGridLayout()
        for i, (k, d) in enumerate(SHORTCUTS):
            sg.addWidget(label(f"<b>{k}</b>", rich=True, wrap=False), i // 2, (i % 2) * 2)
            sg.addWidget(label(d, subtle=True, wrap=False), i // 2, (i % 2) * 2 + 1)
        sc.lay.addLayout(sg)
        v.addWidget(sc)
        v.addStretch(1)

        foot = QHBoxLayout()
        self.again = QCheckBox("Show this window at startup")
        self.again.setChecked(not os.path.exists(DONE_FLAG))
        if not live:
            foot.addWidget(self.again)
        foot.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        foot.addWidget(close)
        v.addLayout(foot)
        self.setCentralWidget(c)

    def closeEvent(self, e):
        if not system.is_live_session():
            os.makedirs(os.path.dirname(DONE_FLAG), exist_ok=True)
            if self.again.isChecked():
                if os.path.exists(DONE_FLAG):
                    os.remove(DONE_FLAG)
            else:
                open(DONE_FLAG, "w").close()
        super().closeEvent(e)


def main() -> int:
    if "--autostart" in sys.argv and os.path.exists(DONE_FLAG) and not system.is_live_session():
        return 0
    app = init_app("veyra-welcome", "Welcome to VeyraOS", "veyraos")
    w = Welcome()
    w.show()
    return app.exec()
