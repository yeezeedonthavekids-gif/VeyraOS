#!/usr/bin/env bash
# Renders the VeyraOS desktop for a brand-new user and takes screenshots.
#
# Uses a Plasma 6 container (Ubuntu 26.04 packages, Plasma 6.6 — the same
# major version Artix ships) because Artix packages cannot be downloaded in
# the development sandbox. The VeyraOS packages built by
# tests/packaging/build-and-install.sh are extracted to their real paths,
# so the look-and-feel package, panel layout script, colour schemes, window
# decoration and /etc/xdg defaults are exercised exactly as on VeyraOS.
#
#   tests/desktop/run-plasma-test.sh [OUTDIR]
# Needs: docker image veyra-plasma-test (see tests/desktop/Dockerfile),
#        packages in /var/tmp/veyra-pkgs
set -euo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OUT=${1:-/var/tmp/veyra-desktop-shots}
PKGS=${VEYRA_PKG_OUT:-/var/tmp/veyra-pkgs}
mkdir -p "$OUT"; rm -f "$OUT"/*.png
docker image inspect veyra-plasma-test >/dev/null 2>&1 \
    || docker build -t veyra-plasma-test "$TOP/tests/desktop"
docker run --rm --cap-add SYS_NICE -v "$PKGS:/pkgs:ro" -v "$OUT:/out" veyra-plasma-test bash -c '
set -u
for p in /pkgs/veyra-branding-*.pkg.tar.zst /pkgs/veyra-desktop-*.pkg.tar.zst /pkgs/veyra-apps-*.pkg.tar.zst /pkgs/veyra-gaming-*.pkg.tar.zst /pkgs/veyra-nvidia-*.pkg.tar.zst; do
    [ -e "$p" ] && tar --zstd -xf "$p" -C / --exclude=".PKGINFO" --exclude=".BUILDINFO" --exclude=".MTREE" --exclude=".INSTALL"
done
fc-cache -f >/dev/null 2>&1
useradd -m -s /bin/bash tester
chmod 777 /out
mkdir -p /run/user/1000 && chown tester /run/user/1000 && chmod 700 /run/user/1000
Xvfb :99 -screen 0 1600x900x24 >/dev/null 2>&1 &
sleep 2
su tester -c "
export DISPLAY=:99 XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland LANG=C.UTF-8
cd ~
dbus-run-session -- bash -c \"
  kwin_wayland --x11-display :99 --width 1600 --height 900 --xwayland --no-lockscreen >/tmp/kwin.log 2>&1 &
  sleep 6
  export WAYLAND_DISPLAY=wayland-0 QT_QPA_PLATFORM=wayland
  # environment that startplasma-wayland sets for a real session
  export QT_QPA_PLATFORMTHEME=kde XDG_CURRENT_DESKTOP=KDE KDE_FULL_SESSION=true KDE_SESSION_VERSION=6 XDG_SESSION_DESKTOP=KDE XDG_MENU_PREFIX=plasma-
  # what a real Plasma login does before the shell starts
  xdg-user-dirs-update
  /usr/lib/veyra/friendly-names
  kbuildsycoca6 --noincremental >/dev/null 2>&1
  kded6 >/dev/null 2>&1 &
  /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd >/dev/null 2>&1 &
  plasmashell >/tmp/plasmashell.log 2>&1 &
  sleep 25
  import -window root /out/desktop.png
  dolphin >/dev/null 2>&1 &
  sleep 8
  import -window root /out/dolphin.png
  qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.activateLauncherMenu >/dev/null 2>&1 || true
  sleep 4
  import -window root /out/startmenu.png
  xdotool key Escape; sleep 1
  plasma-apply-lookandfeel -a org.veyraos.desktop.dark >/tmp/lnf.log 2>&1
  /usr/lib/veyra/theme-sync >>/tmp/lnf.log 2>&1
  sleep 8
  import -window root /out/dark.png
  cp /tmp/lnf.log /out/ 2>/dev/null
  cp ~/.config/kwinrc /out/user-kwinrc.txt 2>/dev/null; cp ~/.config/kdeglobals /out/user-kdeglobals.txt 2>/dev/null
  cp /tmp/plasmashell.log /tmp/kwin.log /out/ 2>/dev/null
  cp ~/.config/plasma-org.kde.plasma.desktop-appletsrc /out/appletsrc.txt 2>/dev/null
\"
"
'
ls -la "$OUT"
