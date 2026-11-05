#!/usr/bin/env python3
"""Render the KSplash QML of the VeyraOS global theme offscreen (QtQuick only).
   python3 tests/branding/render_splash.py OUT.png"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QML = os.path.join(TOP, "src/desktop/usr/share/plasma/look-and-feel/org.veyraos.desktop/contents/splash/Splash.qml")
app = QGuiApplication(sys.argv)
view = QQuickView()
view.setResizeMode(QQuickView.SizeRootObjectToView)
view.resize(1280, 720)
view.setSource(QUrl.fromLocalFile(QML))
errors = [e.toString() for e in view.errors()]
if errors or view.rootObject() is None:
    print("QML errors:", *errors, sep="\n  ")
    sys.exit(1)
view.show()
QTimer.singleShot(200, lambda: view.rootObject().setProperty("stage", 2))   # what ksplashqml does


def done():
    view.grabWindow().save(sys.argv[1])
    print("rendered", sys.argv[1])
    app.quit()


QTimer.singleShot(1500, done)
sys.exit(app.exec())
