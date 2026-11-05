"""The global theme's KSplash QML loads without errors and renders."""
import os
import subprocess
import sys

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_splash_renders(tmp_path):
    out = tmp_path / "splash.png"
    p = subprocess.run([sys.executable, os.path.join(TOP, "tests/branding/render_splash.py"), str(out)],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert out.stat().st_size > 1000
