import os
import subprocess

from veyra.common import system

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_firewall_rules_from_tree(tmp_path):
    (tmp_path / "services").mkdir()
    (tmp_path / "enabled").mkdir()
    (tmp_path / "services" / "ssh.nft").write_text("# OpenSSH server\nadd rule ...\n")
    (tmp_path / "services" / "kdeconnect.nft").write_text("# KDE Connect\n")
    os.symlink("../services/ssh.nft", tmp_path / "enabled" / "ssh.nft")
    rules = {r.name: r for r in system.firewall_rules(str(tmp_path))}
    assert rules["ssh"].enabled and not rules["kdeconnect"].enabled
    assert rules["ssh"].description == "OpenSSH server"


def test_shipped_firewall_rules_have_descriptions():
    rules = system.firewall_rules(os.path.join(TOP, "src/system/etc/veyra/firewall"))
    assert len(rules) >= 4
    assert all(r.description != r.name for r in rules)


def test_auto_update_mode(tmp_path):
    f = tmp_path / "a.conf"
    f.write_text("# x\nMODE=download\n")
    assert system.auto_update_mode(str(f)) == "download"
    assert system.auto_update_mode(str(tmp_path / "missing")) == "notify"


def _fake_lspci(tmp_path, lines):
    p = tmp_path / "lspci"
    p.write_text("#!/bin/sh\ncat <<'X'\n" + "\n".join(lines) + "\nX\n")
    p.chmod(0o755)
    return str(p)


def _detect(tmp_path, lines, *args):
    env = dict(os.environ, VEYRA_LSPCI=_fake_lspci(tmp_path, lines))
    return subprocess.run(["bash", os.path.join(TOP, "src/nvidia/usr/bin/veyra-gpu-detect"), *args],
                          env=env, capture_output=True, text=True).stdout.strip()


def test_gpu_class_rtx5060(tmp_path):
    assert _detect(tmp_path, ["0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GB206 [GeForce RTX 5060] [10de:2d05] (rev a1)"],
                   "--nvidia-class") == "open"


def test_gpu_class_pascal(tmp_path):
    assert _detect(tmp_path, ["0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GP104 [GeForce GTX 1080] [10de:1b80] (rev a1)"],
                   "--nvidia-class") == "legacy"


def test_gpu_class_none(tmp_path):
    assert _detect(tmp_path, ["0000:00:02.0 VGA compatible controller [0300]: Red Hat, Inc. Virtio GPU [1af4:1050] (rev 01)"],
                   "--nvidia-class") == "none"


def test_gpu_json_parses(tmp_path):
    import json
    out = _detect(tmp_path, ['0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GB206 "quoted" [GeForce RTX 5060] [10de:2d05] (rev a1)'],
                  "--json")
    d = json.loads(out)
    assert d["gpus"][0]["vendor"] == "nvidia" and d["nvidia_class"] == "open"


def test_friendly_names(tmp_path):
    sysdir = tmp_path / "sys" / "applications"
    sysdir.mkdir(parents=True)
    (sysdir / "org.kde.dolphin.desktop").write_text("[Desktop Entry]\nName=Dolphin\nName[de]=Dolphin\nExec=dolphin %u\n")
    home = tmp_path / "home"
    env = dict(os.environ, HOME=str(home), XDG_DATA_DIRS=str(tmp_path / "sys"))
    env.pop("XDG_DATA_HOME", None)
    env.pop("XDG_CONFIG_HOME", None)
    script = os.path.join(TOP, "src/desktop/usr/lib/veyra/friendly-names")
    subprocess.run(["python3", script], env=env, check=True)
    out = (home / ".local/share/applications/org.kde.dolphin.desktop").read_text()
    assert "Name=File Explorer" in out and "Exec=dolphin %u" in out and "Name[de]" not in out
    # user-owned file is never touched
    user = home / ".local/share/applications/org.kde.dolphin.desktop"
    user.write_text("[Desktop Entry]\nName=My Dolphin\n")
    subprocess.run(["python3", script], env=env, check=True)
    assert user.read_text() == "[Desktop Entry]\nName=My Dolphin\n"
    # disabling removes generated overrides only
    user.unlink()
    subprocess.run(["python3", script], env=env, check=True)
    (home / ".config/veyra").mkdir(parents=True)
    (home / ".config/veyra/friendly-names").write_text("off")
    subprocess.run(["python3", script], env=env, check=True)
    assert not user.exists()


def _nvidia_setup(tmp_path, lspci_lines, installed_pkgs):
    """Run nvidia-setup in check (dry-run) mode with fake lspci/pacman."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    lspci = _fake_lspci(tmp_path, lspci_lines)
    (bindir / "veyra-gpu-detect").write_text(
        f"#!/bin/sh\nVEYRA_LSPCI={lspci} exec bash {TOP}/src/nvidia/usr/bin/veyra-gpu-detect \"$@\"\n")
    (bindir / "pacman").write_text(
        "#!/bin/sh\n[ \"$1\" = -Q ] || exit 1\ncase \" " + " ".join(installed_pkgs) + " \" in *\" $2 \"*) exit 0;; esac\nexit 1\n")
    for f in bindir.iterdir():
        f.chmod(0o755)
    script = (open(os.path.join(TOP, "src/nvidia/usr/lib/veyra/nvidia-setup")).read()
              .replace("/usr/bin/veyra-gpu-detect", str(bindir / "veyra-gpu-detect")))
    (tmp_path / "nvidia-setup").write_text(script)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
    return subprocess.run(["bash", str(tmp_path / "nvidia-setup"), "check"], env=env, capture_output=True, text=True)


AMD_GPU = "0000:03:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 33 [1002:7480] (rev c7)"
RTX5060 = "0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GB206 [GeForce RTX 5060] [10de:2d05] (rev a1)"


def test_nvidia_setup_no_gpu_nothing_installed(tmp_path):
    p = _nvidia_setup(tmp_path, [AMD_GPU], [])
    assert p.returncode == 0, p.stdout + p.stderr
    assert "would run" not in p.stdout          # nothing to remove, no empty pacman call


def test_nvidia_setup_no_gpu_removes_driver(tmp_path):
    p = _nvidia_setup(tmp_path, [AMD_GPU], ["nvidia-utils", "nvidia-open-dkms"])
    assert p.returncode == 0, p.stderr
    assert "pacman -Rns --noconfirm nvidia-open-dkms nvidia-utils" in p.stdout


def test_nvidia_setup_rtx5060_keeps_driver(tmp_path):
    p = _nvidia_setup(tmp_path, [RTX5060], ["nvidia-utils", "nvidia-open-dkms"])
    assert p.returncode == 0, p.stderr
    assert "-Rns" not in p.stdout and "class: open" in p.stdout
