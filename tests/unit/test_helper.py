"""veyra-helper argument validation (dry-run mode: nothing is executed)."""
import os
import subprocess

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = os.path.join(TOP, "src/apps/usr/lib/veyra/veyra-helper")


def h(*args):
    env = dict(os.environ, VEYRA_HELPER_DRYRUN="1")
    p = subprocess.run(["bash", HELPER, *args], env=env, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def test_install_valid():
    rc, out = h("pkg-install", "firefox", "lib32-mesa", "gtk3", "python-pyside6")
    assert rc == 0 and "pacman -S --noconfirm --needed -- firefox lib32-mesa gtk3 python-pyside6" in out


def test_install_rejects_injection():
    for bad in ["--root=/tmp", "-Syu", "foo;rm", "Foo", "a b", "$(id)", "../x", ".hidden", ""]:
        rc, out = h("pkg-install", bad)
        assert rc != 0, bad
        assert "DRYRUN" not in out, bad


def test_remove_protects_core():
    for p in ["linux", "openrc", "pacman", "veyra-system", "glibc", "sudo"]:
        rc, out = h("pkg-remove", p)
        assert rc != 0 and "refusing" in out
    rc, out = h("pkg-remove", "discord")
    assert rc == 0 and "pacman -Rns --noconfirm -- discord" in out


def test_unknown_action_rejected():
    rc, _ = h("rm", "-rf", "/")
    assert rc != 0


def test_services_whitelist():
    assert h("service", "enable", "cupsd")[0] == 0
    assert h("service", "enable", "udev")[0] != 0
    assert h("service", "start", "cupsd")[0] != 0


def test_firewall_service_requires_known_rule():
    assert h("firewall-service", "enable", "../../etc/shadow")[0] != 0
    assert h("firewall", "maybe")[0] != 0


def test_auto_update_modes():
    for m in ("off", "notify", "download", "install"):
        assert h("auto-update", m)[0] == 0
    assert h("auto-update", "always;reboot")[0] != 0


def test_system_update_takes_no_args():
    assert h("system-update", "--overwrite=*")[0] != 0
    rc, out = h("system-update")
    assert rc == 0 and "pacman -Syu --noconfirm" in out
