"""VeyraOS Gaming Mode.

    veyra-gaming-mode on|off|toggle|status

ON:
  * system (via pkexec gaming-mode-helper; no password for the local user):
    CPU performance governor/EPP, pause non-essential services listed in
    /etc/veyra/gaming-mode.conf
  * session (this user): Do Not Disturb (notifications held back), file
    indexer (Baloo) suspended, update notifications paused
OFF restores everything. Network, audio, input, Bluetooth and the desktop
itself are never touched. Per-game tuning (priority, governor) is still done
by Feral GameMode when a game is launched with it.

The session part runs as a small background process holding the
Do Not Disturb inhibition; if it dies, Plasma automatically lifts it.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

HELPER = "/usr/lib/veyra/gaming-mode-helper"


def runtime_dir() -> str:
    return os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/veyra-{os.getuid()}"


def pidfile() -> str:
    return os.path.join(runtime_dir(), "veyra-gaming-mode.pid")


def flagfile() -> str:
    # Read by the update notifier: no update pop-ups while gaming
    return os.path.join(runtime_dir(), "veyra-gaming-mode.active")


def daemon_pid() -> int | None:
    try:
        pid = int(open(pidfile()).read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def is_active() -> bool:
    return daemon_pid() is not None or os.path.exists("/run/veyra/gaming-mode/active")


def _quiet(cmd: list[str]) -> int:
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 127


def _notify(title: str, body: str):
    _quiet(["notify-send", "-a", "Gaming Mode", "-i", "input-gaming", "-h", "boolean:transient:true", title, body])


def _baloo(cmd: str):
    for tool in ("balooctl6", "balooctl"):
        if _quiet([tool, cmd]) != 127:
            return


def run_daemon():
    """Hold the Do Not Disturb inhibition until SIGTERM/SIGINT."""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtDBus import QDBusConnection, QDBusInterface

    app = QCoreApplication(sys.argv)
    os.makedirs(runtime_dir(), exist_ok=True)
    with open(pidfile(), "w") as f:
        f.write(str(os.getpid()))
    open(flagfile(), "w").close()
    bus = QDBusConnection.sessionBus()
    iface = QDBusInterface("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                           "org.freedesktop.Notifications", bus)
    cookie = None
    if iface.isValid():
        reply = iface.call("Inhibit", "veyra-gaming-mode", "Gaming Mode is on", {})
        args = reply.arguments()
        cookie = args[0] if args else None
    _baloo("suspend")

    def stop(*_):
        if cookie is not None and iface.isValid():
            iface.call("UnInhibit", cookie)
        _baloo("resume")
        for p in (pidfile(), flagfile()):
            try:
                os.remove(p)
            except OSError:
                pass
        app.quit()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Let Python handle signals while Qt's loop runs
    from PySide6.QtCore import QTimer
    t = QTimer()
    t.timeout.connect(lambda: None)
    t.start(500)
    app.exec()


def turn_on() -> int:
    if daemon_pid():
        print("Gaming Mode is already on")
        return 0
    rc = _quiet(["pkexec", HELPER, "on"]) if os.path.exists(HELPER) else 0
    if rc not in (0,):
        print("warning: system part of Gaming Mode was not applied (permission denied?)", file=sys.stderr)
    subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0]), "--daemon"],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(30):
        if daemon_pid():
            break
        time.sleep(0.1)
    _notify("Gaming Mode on", "Notifications paused, CPU set to performance, background tasks paused.")
    print("Gaming Mode: on")
    return 0


def turn_off() -> int:
    pid = daemon_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            if not daemon_pid():
                break
            time.sleep(0.1)
    if os.path.exists("/run/veyra/gaming-mode/active") and os.path.exists(HELPER):
        _quiet(["pkexec", HELPER, "off"])
    _notify("Gaming Mode off", "Normal power and notification settings restored.")
    print("Gaming Mode: off")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "toggle"
    if cmd == "--daemon":
        run_daemon()
        return 0
    if cmd == "on":
        return turn_on()
    if cmd == "off":
        return turn_off()
    if cmd == "toggle":
        return turn_off() if is_active() else turn_on()
    if cmd == "status":
        print("on" if is_active() else "off")
        return 0
    print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
    return 2
