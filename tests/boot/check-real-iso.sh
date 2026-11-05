#!/usr/bin/env bash
# Boot test for a REAL VeyraOS ISO (built by build/build-iso.sh).
#
# Boots the ISO's own kernel + mkinitcpio initramfs in QEMU (UEFI) with a
# serial console added to the kernel command line, waits for OpenRC to bring
# up the live session, and checks the serial log. Takes screenshots of the
# live desktop so a human can review it.
#
#   tests/boot/check-real-iso.sh out/veyraos-*.iso [OUTDIR]
# Uses KVM when /dev/kvm is available (GitHub Actions Linux runners have it).
set -euo pipefail
ISO=${1:?usage: $0 ISO [OUTDIR]}
OUT=${2:-$(dirname "$ISO")/boot-check}
mkdir -p "$OUT"
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT

echo "[check] reading ISO label"
label=$(timeout 60 xorriso -indev "$ISO" -pvd_info 2>/dev/null | sed -n 's/^Volume Id *: *//p' | tr -d "'" | xargs)
[[ -n $label ]] || { echo "cannot read volume label" >&2; exit 1; }
echo "[check] label=$label; extracting kernel + initramfs"
timeout 120 osirrox -indev "$ISO" -extract /boot/vmlinuz-linux "$W/vmlinuz" -extract /boot/initramfs-linux.img "$W/initrd" >/dev/null 2>&1

accel=(-accel tcg); mem=4096; wait_s=900
if [[ -w /dev/kvm ]]; then accel=(-enable-kvm -cpu host); wait_s=300; fi
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$W/vars.fd"
log=$OUT/serial.log
echo "[check] booting (${accel[*]}), waiting up to ${wait_s}s for the display manager"
qemu-system-x86_64 "${accel[@]}" -m $mem -smp 4 \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
    -drive if=pflash,format=raw,file="$W/vars.fd" \
    -kernel "$W/vmlinuz" -initrd "$W/initrd" \
    -append "veyra.label=$label console=tty0 console=ttyS0,115200 loglevel=5" \
    -drive file="$ISO",format=raw,if=virtio,readonly=on \
    -device virtio-vga -display none -serial file:"$log" \
    -monitor unix:"$W/mon",server,nowait -no-reboot &
qpid=$!
shot() { printf 'screendump %s\n' "$W/s.ppm" | timeout 20 socat - UNIX-CONNECT:"$W/mon" >/dev/null 2>&1 && \
         convert "$W/s.ppm" "$OUT/$1.png" 2>/dev/null || true; }

result=FAIL
for ((t = 0; t < wait_s; t += 10)); do
    sleep 10
    if grep -qE "Starting (sddm|displaymanager)" "$log"; then result=PASS; break; fi
    echo "[check] ${t}s: $(tail -c 300 "$log" | tr -d '\033' | tail -1 | cut -c1-120)"
    kill -0 $qpid 2>/dev/null || break
done
sleep 60   # let Plasma come up for the screenshot
shot live-desktop
kill $qpid 2>/dev/null || true; wait $qpid 2>/dev/null || true

echo "== key boot messages"
grep -aE "VeyraOS medium found|OpenRC|veyra-|NetworkManager|sddm|displaymanager|ERROR|failed" "$log" | head -40
for svc in veyra-zram veyra-firewall veyra-live NetworkManager; do
    grep -aq "$svc\|Starting.*${svc#veyra-}" "$log" || echo "WARNING: no start message for $svc"
done
grep -aq "VeyraOS medium found" "$log" || result=FAIL
echo "RESULT: $result (serial log: $log, screenshot: $OUT/live-desktop.png)"
[[ $result == PASS ]]
