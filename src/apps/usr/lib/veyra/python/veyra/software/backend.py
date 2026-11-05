"""Software Center back ends: official repositories (pacman) and Flathub.

Parsing is separated from command execution so it can be unit-tested.
Installing/removing repository packages goes through veyra-helper (pkexec);
Flatpak installs are system-wide and authorised by Flatpak's own polkit rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..common.system import helper_argv, run, which


@dataclass
class App:
    id: str              # pacman package name or Flatpak application ID
    name: str
    summary: str
    source: str          # "repo" | "flatpak"
    version: str = ""
    icon: str = ""
    category: str = ""
    installed: bool = False
    repo: str = ""

    @property
    def source_label(self) -> str:
        return "VeyraOS repositories" if self.source == "repo" else "Flathub"


# ------------------------------------------------------------------ parsing ---
_PACMAN_HEAD = re.compile(r"^(?P<repo>[\w-]+)/(?P<name>\S+) (?P<ver>\S+)(?P<rest>.*)$")


def parse_pacman_search(out: str) -> list[App]:
    """Parse `pacman -Ss` output (name line + indented description line)."""
    apps: list[App] = []
    cur: App | None = None
    for line in out.splitlines():
        m = _PACMAN_HEAD.match(line)
        if m:
            cur = App(m["name"], m["name"], "", "repo", m["ver"], installed="[installed" in m["rest"],
                      repo=m["repo"])
            apps.append(cur)
        elif cur is not None and line.startswith("    "):
            cur.summary = (cur.summary + " " + line.strip()).strip()
    return apps


def parse_flatpak_search(out: str) -> list[App]:
    """Parse `flatpak search --columns=name,description,application,version,remotes`."""
    apps = []
    for line in out.splitlines():
        cols = line.split("\t")
        if len(cols) < 3 or cols[0] in ("Name", "No matches found"):
            continue
        name, desc, appid = cols[0], cols[1], cols[2]
        ver = cols[3] if len(cols) > 3 else ""
        if "." not in appid:
            continue
        apps.append(App(appid, name, desc, "flatpak", ver))
    return apps


def parse_flatpak_list(out: str) -> list[App]:
    """Parse `flatpak list --app --columns=name,application,version`."""
    apps = []
    for line in out.splitlines():
        cols = line.split("\t")
        if len(cols) >= 2 and "." in cols[1]:
            apps.append(App(cols[1], cols[0], "", "flatpak", cols[2] if len(cols) > 2 else "", installed=True))
    return apps


def parse_pacman_explicit(out: str) -> list[App]:
    """Parse `pacman -Qe` output: 'name version' per line."""
    apps = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            apps.append(App(parts[0], parts[0], "", "repo", parts[1], installed=True))
    return apps


# ----------------------------------------------------------------- queries ---
def installed_repo_names() -> set[str]:
    rc, out = run(["pacman", "-Qq"], timeout=30)
    return set(out.split()) if rc == 0 else set()


def installed_flatpak_ids() -> set[str]:
    if not which("flatpak"):
        return set()
    rc, out = run(["flatpak", "list", "--app", "--columns=application"], timeout=30)
    return set(out.split()) if rc == 0 else set()


def search(query: str) -> list[App]:
    query = query.strip()
    if len(query) < 2:
        return []
    # pacman treats the query as a regex: escape it so input is taken literally
    results = []
    terms = [re.escape(w) for w in query.split()]
    rc, out = run(["pacman", "-Ss", "--", *terms], timeout=30)
    if rc == 0:
        results += parse_pacman_search(out)
    if which("flatpak"):
        rc, out = run(["flatpak", "search", "--columns=name,description,application,version,remotes", query],
                      timeout=60)
        if rc == 0:
            fl = parse_flatpak_search(out)
            ids = installed_flatpak_ids()
            for a in fl:
                a.installed = a.id in ids
            results += fl
    q = query.lower()

    def rank(a: App):
        n = a.name.lower()
        return (0 if n == q else 1 if n.startswith(q) else 2 if q in n else 3,
                0 if a.repo in ("", "extra", "world", "galaxy") else 1, n)
    return sorted(results, key=rank)


def installed_apps() -> list[App]:
    apps = []
    rc, out = run(["pacman", "-Qe"], timeout=30)
    if rc == 0:
        apps += parse_pacman_explicit(out)
    if which("flatpak"):
        rc, out = run(["flatpak", "list", "--app", "--columns=name,application,version"], timeout=30)
        if rc == 0:
            apps += parse_flatpak_list(out)
    return apps


# ---------------------------------------------------------------- actions ---
def install_argv(app: App) -> list[str]:
    if app.source == "repo":
        return helper_argv("pkg-install", app.id)
    return ["flatpak", "install", "--system", "-y", "--noninteractive", "flathub", app.id]


def remove_argv(app: App) -> list[str]:
    if app.source == "repo":
        return helper_argv("pkg-remove", app.id)
    return ["flatpak", "uninstall", "--system", "-y", "--noninteractive", app.id]
