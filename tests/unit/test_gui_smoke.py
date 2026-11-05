"""Every VeyraOS window can be constructed and painted (offscreen)."""
import os

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from veyra.common.ui import init_app
    return init_app("veyra-test", "VeyraOS test")


def _paint(w, name):
    w.resize(1100, 740)
    w.show()
    QApplication.processEvents()
    img = w.grab()
    assert not img.isNull()
    out = os.environ.get("VEYRA_SCREENSHOT_DIR")
    if out:
        img.save(os.path.join(out, name + ".png"))
    w.close()


def test_control(app):
    from veyra.control.app import ControlWindow
    w = ControlWindow()
    for i in range(w.nav.count()):
        w.nav.setCurrentRow(i)
        QApplication.processEvents()
    w.show_page("gaming")
    _paint(w, "control-gaming")
    w = ControlWindow()
    _paint(w, "control-overview")


def test_software(app):
    from veyra.software.app import SoftwareWindow
    _paint(SoftwareWindow(), "software-home")


def test_welcome(app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    import importlib

    import veyra.welcome.app as wa
    importlib.reload(wa)
    _paint(wa.Welcome(), "welcome")
