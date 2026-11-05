"""Steam configuration helpers.

Enables "Steam Play for all other titles" with Proton Experimental by writing
the CompatToolMapping entry "0" in Steam's config.vdf — exactly what the
Steam client does when the user ticks that box (Settings > Compatibility).
Steam must not be running (it rewrites config.vdf on exit).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time

DEFAULT_TOOL = "proton_experimental"


# ------------------------------------------------------------- VDF (text) ---
class VdfError(ValueError):
    pass


def _tokens(text: str):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == "/" and text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
        elif c in "{}":
            yield c
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(text[j + 1], text[j + 1]))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            if j >= n:
                raise VdfError("unterminated string")
            yield ("s", "".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '{}"':
                j += 1
            yield ("s", text[i:j])
            i = j


def loads(text: str) -> dict:
    toks = list(_tokens(text))
    pos = 0

    def parse_obj(top: bool) -> dict:
        nonlocal pos
        obj: dict = {}
        while pos < len(toks):
            t = toks[pos]
            if t == "}":
                if top:
                    raise VdfError("unexpected }")
                pos += 1
                return obj
            if not isinstance(t, tuple):
                raise VdfError("expected key")
            key = t[1]
            pos += 1
            if pos >= len(toks):
                raise VdfError("missing value for " + key)
            v = toks[pos]
            if v == "{":
                pos += 1
                obj[key] = parse_obj(False)
            elif isinstance(v, tuple):
                obj[key] = v[1]
                pos += 1
            else:
                raise VdfError("unexpected token after " + key)
        if not top:
            raise VdfError("missing }")
        return obj

    return parse_obj(True)


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def dumps(obj: dict, indent: int = 0) -> str:
    out = []
    tab = "\t" * indent
    for k, v in obj.items():
        if isinstance(v, dict):
            out.append(f"{tab}{_q(k)}\n{tab}{{\n{dumps(v, indent + 1)}{tab}}}\n")
        else:
            out.append(f"{tab}{_q(k)}\t\t{_q(v)}\n")
    return "".join(out)


def _child(d: dict, name: str, create: bool = True) -> dict | None:
    for k, v in d.items():
        if k.lower() == name.lower() and isinstance(v, dict):
            return v
    if not create:
        return None
    d[name] = {}
    return d[name]


# ------------------------------------------------------------------ Steam ---
def steam_roots(home: str | None = None) -> list[str]:
    home = home or os.path.expanduser("~")
    cands = [os.path.join(home, ".local/share/Steam"), os.path.join(home, ".steam/steam"),
             os.path.join(home, ".var/app/com.valvesoftware.Steam/.local/share/Steam")]
    seen, roots = set(), []
    for c in cands:
        r = os.path.realpath(c)
        if os.path.isdir(r) and r not in seen:
            seen.add(r)
            roots.append(r)
    return roots


def steam_running() -> bool:
    if not shutil.which("pgrep"):
        return False
    return subprocess.run(["pgrep", "-x", "steam"], stdout=subprocess.DEVNULL).returncode == 0


def get_default_compat_tool(config_path: str) -> str | None:
    try:
        data = loads(open(config_path, encoding="utf-8").read())
    except (OSError, VdfError):
        return None
    node = data
    for name in ("InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping", "0"):
        node = _child(node, name, create=False)
        if node is None:
            return None
    return node.get("name")


def set_default_compat_tool(config_path: str, tool: str = DEFAULT_TOOL, backup: bool = True) -> None:
    """Set CompatToolMapping "0" (all titles without a native/forced tool)."""
    if os.path.exists(config_path):
        text = open(config_path, encoding="utf-8").read()
        data = loads(text)
        if backup:
            shutil.copy2(config_path, config_path + ".veyra-backup-%d" % int(time.time()))
    else:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        data = {}
    node = data
    for name in ("InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping"):
        node = _child(node, name)
    node["0"] = {"name": tool, "config": "", "priority": "75"}
    tmp = config_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dumps(data))
    os.replace(tmp, config_path)


def enable_steam_play(home: str | None = None, tool: str = DEFAULT_TOOL) -> list[str]:
    """Apply to every Steam installation found. Returns the files changed."""
    if steam_running():
        raise RuntimeError("Steam is running. Close Steam (Steam menu > Exit) and try again.")
    changed = []
    for root in steam_roots(home):
        cfg = os.path.join(root, "config", "config.vdf")
        if get_default_compat_tool(cfg) != tool:
            set_default_compat_tool(cfg, tool)
            changed.append(cfg)
    return changed
