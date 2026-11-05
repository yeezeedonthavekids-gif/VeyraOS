#!/usr/bin/env bash
# Fast static checks that need no network, root or containers.
set -uo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$TOP" || exit 1
fail=0
pass() { printf '  ok   %s\n' "$*"; }
bad()  { printf '  FAIL %s\n' "$*"; fail=1; }

# shellcheck source=build/profile.conf
source build/profile.conf

# 1. Release identification is consistent everywhere
# shellcheck source=src/system/usr/share/veyra/release
source src/system/usr/share/veyra/release
[[ $VEYRA_VERSION == "$(sed -n 's/^VEYRA_VERSION=//p' build/profile.conf | tr -d '"')" ]] && pass "release file version" || bad "release file version differs from profile.conf"
for p in pkgbuilds/veyra-*/PKGBUILD; do
    [[ $p == *veyra-calamares* || $p == *rounded-corners* ]] && continue
    v=$(sed -n 's/^pkgver=//p' "$p")
    [[ $v == "$VEYRA_VERSION" ]] || bad "$p pkgver $v != $VEYRA_VERSION"
done
pass "PKGBUILD versions"
grep -q "version: *\"$VEYRA_VERSION\"" src/installer/usr/share/calamares/branding/veyra/branding.desc && pass "installer branding version" || bad "branding.desc version"
grep -q "VERSION = \"$VEYRA_VERSION\"" src/apps/usr/lib/veyra/python/veyra/common/ui.py && pass "apps version" || bad "apps VERSION constant"

# 2. Every local package in the profile has a PKGBUILD
for p in "${LOCAL_PKGS[@]}" "${OPTIONAL_LOCAL_PKGS[@]}"; do
    [[ -f pkgbuilds/$p/PKGBUILD ]] || { [[ " ${OPTIONAL_LOCAL_PKGS[*]} " == *" $p "* ]] && continue; bad "missing PKGBUILD for $p"; }
done
pass "PKGBUILDs present"

# 3. Desktop entries are valid
de_fail=0
while IFS= read -r f; do
    out=$(desktop-file-validate "$f" 2>&1 | grep -v "hint:") || true
    [[ -z $out ]] || { echo "$out"; de_fail=1; }
done < <(find src -name '*.desktop' -path '*applications*' -o -name '*.desktop' -path '*autostart*')
((de_fail)) && bad "desktop-file-validate" || pass "desktop entries valid"

# 4. JSON files parse
while IFS= read -r f; do python3 -m json.tool "$f" >/dev/null 2>&1 || bad "invalid JSON: $f"; done < <(find src -name '*.json')
pass "JSON files"

# 5. Python compiles; QML/JS files exist where referenced
python3 -m compileall -q src/apps/usr/lib/veyra/python src/desktop/usr/lib/veyra >/dev/null && pass "python compiles" || bad "python compile"
for lnf in src/desktop/usr/share/plasma/look-and-feel/*/; do
    [[ -f $lnf/contents/layouts/org.kde.plasma.desktop-layout.js && -f $lnf/contents/splash/Splash.qml && -f $lnf/contents/defaults ]] \
        || bad "incomplete look-and-feel package $lnf"
done
pass "look-and-feel packages complete"

# 6. Aurorae themes: every button state element exists
for t in src/desktop/usr/share/aurorae/themes/*/; do
    for b in close minimize maximize restore; do
        for st in active hover pressed inactive; do
            grep -q "id=\"$st-center\"" "$t/$b.svg" || bad "$t$b.svg lacks $st-center"
        done
    done
done
pass "aurorae button states"

# 7. No systemd units or systemctl calls in what we ship (OpenRC only)
if grep -rnE '\bsystemctl\b|\.service\b' src --include='*' -I | grep -vE 'services-(openrc|systemd)|#.*systemd|services-systemd|\.service.*\(no|nvidia-suspend|systemd units' | grep -v "^src/installer/etc/calamares/settings.conf" | grep -q .; then
    grep -rnE '\bsystemctl\b' src -I | head; bad "systemd references found"
else
    pass "no systemctl / systemd units"
fi

# 8. Calamares: every module in the sequence has a config file (or is an instance)
for m in $(sed -n '/^sequence:/,/^branding:/p' src/installer/etc/calamares/settings.conf | sed -n 's/^ *- \([a-z@-]*\)$/\1/p'); do
    case $m in *@*) c=$(grep -A2 "id: ${m#*@}" src/installer/etc/calamares/settings.conf | sed -n 's/.*config: //p');;
                *) c="$m.conf";; esac
    [[ -f src/installer/etc/calamares/modules/$c ]] || bad "calamares module $m has no config ($c)"
done
pass "calamares module configs"

exit $fail
