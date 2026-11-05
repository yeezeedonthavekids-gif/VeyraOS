#!/usr/bin/env bash
# Runs the VeyraOS Plymouth theme with Plymouth's X11 renderer under Xvfb and
# takes screenshots: splash, status message, encrypted-disk password prompt.
# Needs (Debian/Ubuntu names): plymouth plymouth-x11 plymouth-label xvfb imagemagick
# Must run as root (plymouthd). Installs the theme to /usr/share/plymouth/themes/veyra.
#   tests/branding/run-plymouth-test.sh [OUTDIR]
set -euo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OUT=${1:-/var/tmp/veyra-plymouth}
mkdir -p "$OUT"
rm -rf /usr/share/plymouth/themes/veyra
cp -r "$TOP/src/branding/plymouth/veyra" /usr/share/plymouth/themes/veyra
mkdir -p /etc/plymouth
printf '[Daemon]\nTheme=veyra\n' > /etc/plymouth/plymouthd.conf
inner=$(mktemp)
cat > "$inner" <<EOI
Xvfb :98 -screen 0 1280x720x24 >/dev/null 2>&1 &
sleep 2; export DISPLAY=:98
plymouthd --no-daemon --debug --debug-file="$OUT/plymouthd.log" --tty="\$(tty)" \
    --kernel-command-line="quiet splash plymouth.ignore-serial-consoles" >/dev/null 2>&1 &
sleep 2
plymouth show-splash; sleep 3; import -window root "$OUT/splash.png"
plymouth display-message --text="Starting VeyraOS…"; sleep 1; import -window root "$OUT/message.png"
plymouth ask-for-password --prompt="Enter the passphrase for the encrypted disk" >/dev/null 2>&1 &
sleep 2; import -window root "$OUT/password.png"
plymouth quit; kill %1 2>/dev/null || true
EOI
timeout 90 script -qc "bash $inner" /dev/null >/dev/null 2>&1 || true
rm -f "$inner"
grep -q "executing script file" "$OUT/plymouthd.log" && echo "theme script executed" || { echo "theme did not run"; exit 1; }
ls -la "$OUT"/*.png
