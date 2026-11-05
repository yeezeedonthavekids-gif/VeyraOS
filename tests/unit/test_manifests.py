"""Package manifest resolution (build/lib/packages.sh) and the real manifests."""
import os
import subprocess

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve(tmp_path, index, manifest):
    (tmp_path / "index").write_text("\n".join(index) + "\n")
    (tmp_path / "m.list").write_text(manifest)
    script = f"""
source {TOP}/build/lib/common.sh
source {TOP}/build/lib/packages.sh
resolve_manifests {tmp_path}/index {tmp_path}/out {tmp_path}/m.list
"""
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    out = (tmp_path / "out").read_text().split() if (tmp_path / "out").exists() else []
    return p.returncode, out, p.stderr


def test_alternatives_and_optional(tmp_path):
    rc, out, err = resolve(tmp_path, ["a", "c", "opt"],
                           "a\nb|c   # comment\n?missing\n?nope|opt\n\n# only comment\n")
    assert rc == 0, err
    assert out == ["a", "c", "opt"]
    assert "optional package unavailable, skipped: missing" in err


def test_missing_required_fails(tmp_path):
    rc, out, err = resolve(tmp_path, ["a"], "a\nb|c\n")
    assert rc != 0 and "MISSING" in err and "b|c" in err


def test_real_manifests_are_well_formed():
    import re
    pat = re.compile(r"^\??[a-z0-9@._+-]+(\|[a-z0-9@._+-]+)*$")
    for f in os.listdir(os.path.join(TOP, "packages")):
        if not f.endswith(".list"):
            continue
        for line in open(os.path.join(TOP, "packages", f)):
            line = line.split("#", 1)[0].strip()
            if line:
                assert pat.match(line), f"{f}: {line!r}"


def test_no_systemd_packages_requested():
    for f in os.listdir(os.path.join(TOP, "packages")):
        if f.endswith(".list"):
            text = open(os.path.join(TOP, "packages", f)).read()
            for line in text.splitlines():
                name = line.split("#", 1)[0].strip().lstrip("?")
                assert not name.startswith("systemd"), f"{f}: {line}"
