"""Shared widgets and styling for VeyraOS applications.

Colours are derived from the active Qt/KDE palette, so every app follows the
system light/dark theme automatically (VeyraOS Light/Dark colour schemes).
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import QProcess, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
                               QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

ACCENT_FALLBACK = QColor(107, 78, 255)
VERSION = "2026.11"


def is_dark(palette: QPalette | None = None) -> bool:
    p = palette or QApplication.palette()
    return p.color(QPalette.Window).lightness() < 128


def accent(palette: QPalette | None = None) -> QColor:
    p = palette or QApplication.palette()
    c = p.color(QPalette.Highlight)
    return c if c.isValid() else ACCENT_FALLBACK


def _mix(a: QColor, b: QColor, t: float) -> str:
    return "rgb(%d,%d,%d)" % (a.red() + (b.red() - a.red()) * t,
                              a.green() + (b.green() - a.green()) * t,
                              a.blue() + (b.blue() - a.blue()) * t)


def stylesheet() -> str:
    p = QApplication.palette()
    win, base, text = p.color(QPalette.Window), p.color(QPalette.Base), p.color(QPalette.WindowText)
    acc = accent(p)
    dark = is_dark(p)
    card = _mix(win, base, 0.6 if not dark else 0.35)
    border = _mix(win, text, 0.10)
    hover = _mix(win, text, 0.06)
    sel_bg = _mix(win, acc, 0.18)
    sub = _mix(win, text, 0.62)
    return f"""
    QFrame#Card {{ background: {card}; border: 1px solid {border}; border-radius: 10px; }}
    QLabel#PageTitle {{ font-size: 20pt; font-weight: 600; }}
    QLabel#CardTitle {{ font-size: 11.5pt; font-weight: 600; }}
    QLabel#Subtle {{ color: {sub}; }}
    QLabel#Badge {{ border-radius: 9px; padding: 2px 9px; background: {sel_bg}; color: {acc.name()}; font-weight: 600; }}
    QListWidget#Nav {{ background: transparent; border: none; outline: 0; font-size: 10.5pt; }}
    QListWidget#Nav::item {{ padding: 9px 10px; margin: 2px 6px; border-radius: 7px; }}
    QListWidget#Nav::item:hover {{ background: {hover}; }}
    QListWidget#Nav::item:selected {{ background: {sel_bg}; color: {text.name()}; border-left: 3px solid {acc.name()}; }}
    QPushButton#Primary {{ background: {acc.name()}; color: white; border: none; border-radius: 6px;
                          padding: 7px 16px; font-weight: 600; }}
    QPushButton#Primary:hover {{ background: {acc.lighter(112).name()}; }}
    QPushButton#Primary:disabled {{ background: {_mix(win, acc, 0.4)}; }}
    QPlainTextEdit#Log {{ font-family: "JetBrains Mono", monospace; font-size: 9pt; border-radius: 8px; }}
    """


def init_app(name: str, display: str, icon: str = "veyraos") -> QApplication:
    QApplication.setApplicationName(name)
    QApplication.setApplicationDisplayName(display)
    QApplication.setDesktopFileName(name)
    QApplication.setOrganizationName("VeyraOS")
    app = QApplication.instance() or QApplication(sys.argv)
    # Outside Plasma (no KDE platform theme) fall back to the VeyraOS icon set
    if QIcon.themeName() in ("", "hicolor"):
        for theme in ("Papirus", "breeze"):
            if os.path.isdir(f"/usr/share/icons/{theme}"):
                QIcon.setThemeName(theme)
                break
    app.setWindowIcon(QIcon.fromTheme(icon))
    app.setStyleSheet(stylesheet())
    return app


# ------------------------------------------------------------------ widgets ---
class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(8)
        if title:
            t = QLabel(title)
            t.setObjectName("CardTitle")
            self.lay.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("Subtle")
            s.setWordWrap(True)
            self.lay.addWidget(s)

    def add(self, w: QWidget) -> QWidget:
        self.lay.addWidget(w)
        return w

    def add_row(self, *widgets: QWidget, stretch_first: bool = True) -> QHBoxLayout:
        row = QHBoxLayout()
        for i, w in enumerate(widgets):
            row.addWidget(w, 1 if (i == 0 and stretch_first) else 0)
        self.lay.addLayout(row)
        return row


def label(text: str, subtle: bool = False, wrap: bool = True, rich: bool = False) -> QLabel:
    lb = QLabel(text)
    lb.setWordWrap(wrap)
    if subtle:
        lb.setObjectName("Subtle")
    if rich:
        lb.setTextFormat(Qt.RichText)
        lb.setOpenExternalLinks(True)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
    return lb


def primary_button(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("Primary")
    b.setCursor(Qt.PointingHandCursor)
    return b


def kv_row(key: str, value: str) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 2, 0, 2)
    k = label(key, subtle=True, wrap=False)
    k.setMinimumWidth(170)
    h.addWidget(k)
    h.addWidget(label(value), 1)
    return w


class Page(QScrollArea):
    """A scrollable settings page with a large title."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self.lay = QVBoxLayout(inner)
        self.lay.setContentsMargins(28, 22, 28, 22)
        self.lay.setSpacing(14)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        self.lay.addWidget(t)
        if subtitle:
            self.lay.addWidget(label(subtitle, subtle=True))
        self.setWidget(inner)

    def add(self, w: QWidget) -> QWidget:
        self.lay.addWidget(w)
        return w

    def finish(self):
        self.lay.addStretch(1)


class NavWindow(QMainWindow):
    """Window with a left navigation list and stacked pages (Windows 11 Settings style)."""

    def __init__(self, title: str, size=(1080, 720)):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(*size)
        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        side = QWidget()
        side.setFixedWidth(250)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(8, 16, 8, 12)
        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QIcon.fromTheme("veyraos").pixmap(28, 28))
        head.addWidget(logo)
        name = QLabel(title)
        f = name.font()
        f.setPointSizeF(f.pointSizeF() * 1.15)
        f.setWeight(QFont.DemiBold)
        name.setFont(f)
        head.addWidget(name, 1)
        sv.addLayout(head)
        sv.addSpacing(12)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setIconSize(QSize(20, 20))
        sv.addWidget(self.nav, 1)
        self.stack = QStackedWidget()
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self._pages: dict[str, int] = {}

    def add_page(self, key: str, text: str, icon: str, page: QWidget):
        it = QListWidgetItem(QIcon.fromTheme(icon), text)
        self.nav.addItem(it)
        self._pages[key] = self.stack.addWidget(page)
        if self.nav.count() == 1:
            self.nav.setCurrentRow(0)

    def show_page(self, key: str):
        if key in self._pages:
            self.nav.setCurrentRow(self._pages[key])


class CommandRunner(QWidget):
    """Runs a (usually privileged) command and streams its output."""
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.status = label("", subtle=True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.setMaximumHeight(6)
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(140)
        self.log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v.addWidget(self.status)
        v.addWidget(self.bar)
        v.addWidget(self.log)
        self.bar.hide()
        self.proc: QProcess | None = None

    def busy(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.NotRunning

    def start(self, argv: list[str], status: str = "Working…"):
        if self.busy():
            return
        self.log.clear()
        self.status.setText(status)
        self.bar.show()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        env = self.proc.processEnvironment()
        env.insert("LC_ALL", "C.UTF-8")
        self.proc.setProcessEnvironment(env)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        self.proc.errorOccurred.connect(lambda _e: self._done(127, None))
        self.log.appendPlainText("$ " + " ".join(argv))
        self.proc.start(argv[0], argv[1:])

    def _read(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.moveCursor(self.log.textCursor().MoveOperation.End)
        self.log.insertPlainText(data)
        self.log.ensureCursorVisible()

    def _done(self, code, _status=None):
        if self.bar.isHidden():
            return
        self.bar.hide()
        ok = code == 0
        if code in (126, 127) and not ok:
            self.status.setText("Cancelled — administrator permission was not granted." if code == 126
                                else "Could not start the command.")
        else:
            self.status.setText("Done." if ok else f"Failed (exit code {code}). See the details below.")
        self.finished.emit(ok)


def env_flag(name: str) -> bool:
    return os.environ.get(name, "") not in ("", "0", "false", "no")
