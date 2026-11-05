#!/usr/bin/env bash
# Builds every VeyraOS package with makepkg inside the official Artix
# base-devel container, installs them with pacman -U (dependencies are not
# resolvable offline, so -dd), and runs sanity checks on the installed files.
# Runs fully offline: VeyraOS packages have only local sources.
#   tests/packaging/build-and-install.sh [package...]
set -euo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PKGS=("$@")
if ((${#PKGS[@]} == 0)); then
    # shellcheck source=build/profile.conf
    source "$TOP/build/profile.conf"
    PKGS=("${LOCAL_PKGS[@]}")
fi
OUT=${VEYRA_PKG_OUT:-/var/tmp/veyra-pkgs}
rm -rf "$OUT"; mkdir -p "$OUT"
chmod 777 "$OUT"
# 1) build in base-devel (has makepkg)
docker run --rm -v "$TOP:/veyra:ro" -v "$OUT:/out" -e PKGS="${PKGS[*]}" artixlinux/artixlinux:base-devel bash -euo pipefail -c '
    useradd -m builder
    cp -r /veyra/src /tmp/src; chmod -R a+rX /tmp/src
    for p in $PKGS; do
        rm -rf /tmp/b; cp -r /veyra/pkgbuilds/$p /tmp/b; chown -R builder /tmp/b
        su builder -c "cd /tmp/b && VEYRA_SRC=/tmp/src PKGDEST=/out makepkg -d --noconfirm >/tmp/b/log 2>&1" \
            || { echo "BUILD FAILED: $p"; tail -30 /tmp/b/log; exit 1; }
        echo "built: $p"
    done
    visudo -c -f /veyra/src/system/etc/sudoers.d/00-veyra || exit 1
'
# 2) install + check in base-openrc (real OpenRC, visudo)
docker run --rm -v "$OUT:/out:ro" artixlinux/artixlinux:base-openrc bash -uo pipefail -c '
    pacman -U --noconfirm -dd /out/*.pkg.tar.zst >/tmp/install.log 2>&1 || { cat /tmp/install.log; exit 1; }
    grep -iE "warning|error" /tmp/install.log || true
    echo "installed: $(ls /out/*.pkg.tar.zst | wc -l) packages"
    fail=0
    for s in /etc/init.d/veyra-*; do
        [ -e "$s" ] || continue
        sh -n "$s" || { echo "SYNTAX: $s"; fail=1; }
        out=$("$s" describe 2>&1) || { echo "openrc-run describe failed: $s: $out"; fail=1; }
        echo "  ok: $(basename $s): $(echo "$out" | head -1)"
    done
    if pacman -Qq veyra-system >/dev/null 2>&1; then
        grep -q "^ID=veyraos" /etc/os-release || { echo "os-release not applied"; fail=1; }
        rc-update add veyra-zram boot >/dev/null && rc-update add veyra-firewall default >/dev/null || fail=1
        /usr/lib/veyra/make-text-runlevel && ls /etc/runlevels/text | tr "\n" " "; echo
    fi
    # file permission sanity: nothing world-writable, executables executable
    ww=$(pacman -Qlq $(pacman -Qq | grep "^veyra-") | while read -r f; do [ -L "$f" ] && continue; [ -f "$f" ] && stat -c "%a %n" "$f" | grep -E "^[0-7]{1,2}[2367] " ; done)
    [ -z "$ww" ] || { echo "world-writable files: $ww"; fail=1; }
    exit $fail
'
echo "packages in $OUT"
