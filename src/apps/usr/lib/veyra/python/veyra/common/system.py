"""System queries and privileged operations shared by the VeyraOS apps.

All root operations go through /usr/lib/veyra/veyra-helper via pkexec;
nothing in the GUI runs as root. Every function here degrades gracefully
when a tool is missing (e.g. on a non-VeyraOS development machine), which is
also what the unit tests rely on.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field

HELPER = os.environ.get("VEYRA_HELPER", "/usr/lib/veyra/veyra-helper")
GAMING_HELPER = "/usr/lib/veyra/gaming-mode-helper"


def which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run(cmd: list[str], timeout: float = 30) -> tuple[int, str]:
    """Run a command, return (exit code, combined output). Never raises."""
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def helper_argv(*args: str) -> list[str]:
    """argv for a privileged helper call (pkexec prompts for the password)."""
    if os.environ.get("VEYRA_HELPER_DRYRUN") == "1":
        return [HELPER, *args]
    return ["pkexec", HELPER, *args]


def is_live_session() -> bool:
    return os.path.exists("/run/veyra/sfs")


# ---------------------------------------------------------------- release ---
def os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.rstrip("\n").split("=", 1)
                        data[k] = v.strip().strip('"')
            break
        except OSError:
            continue
    return data


# --------------------------------------------------------------- hardware ---
@dataclass
class Gpu:
    slot: str
    vendor: str
    id: str
    driver: str
    name: str


@dataclass
class GpuInfo:
    gpus: list[Gpu] = field(default_factory=list)
    nvidia_class: str = "none"
    nvidia_loaded: bool = False
    nvidia_version: str = ""
    session: str = ""


def gpu_info() -> GpuInfo:
    rc, out = run(["veyra-gpu-detect", "--json"], timeout=10)
    if rc != 0:
        return GpuInfo()
    try:
        d = json.loads(out)
    except ValueError:
        return GpuInfo()
    return GpuInfo([Gpu(**g) for g in d.get("gpus", [])], d.get("nvidia_class", "none"),
                   bool(d.get("nvidia_loaded")), d.get("nvidia_version", ""), d.get("session", ""))


def cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown CPU"


def memory_gib() -> float:
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0.0


def disk_usage(path: str = "/") -> tuple[int, int]:
    """(used bytes, total bytes)"""
    try:
        u = shutil.disk_usage(path)
        return u.used, u.total
    except OSError:
        return 0, 0


def kernel() -> str:
    return platform.release()


# --------------------------------------------------------------- services ---
def service_running(name: str) -> bool:
    rc, _ = run(["rc-service", "-q", name, "status"], timeout=10)
    return rc == 0


def service_enabled(name: str) -> bool:
    rc, out = run(["rc-update", "show", "default"], timeout=10)
    return rc == 0 and re.search(rf"^\s*{re.escape(name)}\s*\|", out, re.M) is not None


def service_installed(name: str) -> bool:
    return os.path.exists(f"/etc/init.d/{name}")


# --------------------------------------------------------------- firewall ---
FIREWALL_DIR = "/etc/veyra/firewall"


@dataclass
class FirewallRule:
    name: str
    description: str
    enabled: bool


def firewall_rules(base: str = FIREWALL_DIR) -> list[FirewallRule]:
    rules = []
    sdir = os.path.join(base, "services")
    try:
        names = sorted(f[:-4] for f in os.listdir(sdir) if f.endswith(".nft"))
    except OSError:
        return []
    for n in names:
        desc = n
        try:
            with open(os.path.join(sdir, n + ".nft"), encoding="utf-8") as f:
                first = f.readline().strip()
                if first.startswith("#"):
                    desc = first.lstrip("# ").strip()
        except OSError:
            pass
        rules.append(FirewallRule(n, desc, os.path.exists(os.path.join(base, "enabled", n + ".nft"))))
    return rules


def firewall_active() -> bool:
    return service_running("veyra-firewall")


# ------------------------------------------------------------ gaming mode ---
GAMING_STATE = "/run/veyra/gaming-mode/active"


def gaming_mode_active() -> bool:
    return os.path.exists(GAMING_STATE)


# ---------------------------------------------------------------- updates ---
AUTO_UPDATE_CONF = "/etc/veyra/auto-update.conf"


def auto_update_mode(path: str = AUTO_UPDATE_CONF) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*MODE\s*=\s*([a-z]+)", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return "notify"


def timeshift_configured() -> bool:
    return os.path.isfile("/etc/timeshift/timeshift.json") and os.path.getsize("/etc/timeshift/timeshift.json") > 0
