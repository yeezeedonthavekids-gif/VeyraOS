#!/usr/bin/env bash
# VeyraOS live-boot mechanism test (QEMU).
#
# Builds a small test ISO with the SAME code the real build uses
# (build/lib/iso.sh: GRUB menu + hybrid ISO; src/live/initcpio/hooks/veyralive:
# live root discovery + squashfs/overlay), boots it in QEMU (BIOS and UEFI),
# and checks from inside the booted OpenRC system that:
#   - / is the overlay over the squashfs image, /run/veyra/* is visible
#   - OpenRC boots to the default runlevel; veyra-zram swap is active
#   - veyra-firewall loads its nftables rule set; os-release says VeyraOS
#   - boot options work: copy-to-RAM, integrity verification, text runlevel
#
# The userspace is Artix's official artixlinux/artixlinux:base-openrc image
# (real OpenRC init). Because this environment cannot reach the Artix package
# mirrors, the kernel is Ubuntu's generic kernel and the initramfs is a
# minimal mkinitcpio-compatible init that runs the veyralive hook with the
# same interface mkinitcpio uses (run_hook + $mount_handler). The full ISO
# build (build/build-iso.sh) uses the real mkinitcpio.
#
# Usage: tests/boot/run-boot-test.sh [--keep] [--case NAME]...
#   cases: bios uefi copytoram verify textmode   (default: all)
# Requires: docker, qemu-system-x86_64, grub-mkrescue (+pc/efi modules),
#           xorriso, mtools, mksquashfs, busybox-static, OVMF, apt-get download.
# shellcheck disable=SC2054  # qemu option values contain commas
set -euo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
# shellcheck source=build/lib/common.sh
source "$TOP/build/lib/common.sh"
# shellcheck source=build/lib/iso.sh
source "$TOP/build/lib/iso.sh"

W=${VEYRA_TEST_WORK:-/var/tmp/veyra-boot-test}
LABEL=VEYRA_TEST
KEEP=0
CASES=()
while (($#)); do
    case $1 in
        --keep) KEEP=1; shift ;;
        --case) CASES+=("$2"); shift 2 ;;
        *) die "unknown argument $1" ;;
    esac
done
((${#CASES[@]})) || CASES=(bios uefi copytoram verify textmode)
require_cmd docker qemu-system-x86_64 grub-mkrescue xorriso mksquashfs busybox

mkdir -p "$W"
ROOT=$W/rootfs ISO=$W/iso KROOT=$W/kernel INITRD=$W/initrd

# ---------------------------------------------------------------- kernel ----
if [[ ! -d $KROOT/boot || ! -e $W/debs/.complete ]]; then
    msg "Fetching a test kernel (Ubuntu generic)"
    mkdir -p "$W/debs" "$KROOT"
    kpkg=$(apt-cache depends linux-image-generic | awk '/Depends: linux-image-[0-9]/{print $2}' | head -1)
    kver=${kpkg#linux-image-}
    (cd "$W/debs" && apt-get download -qq "linux-image-$kver" "linux-modules-$kver" "linux-modules-extra-$kver")
    for d in "$W"/debs/*.deb; do dpkg-deb -x "$d" "$KROOT"; done
    touch "$W/debs/.complete"
fi
KVER=$(ls "$KROOT/lib/modules")

# ---------------------------------------------------------------- rootfs ----
msg "Preparing root filesystem from artixlinux/artixlinux:base-openrc"
rm -rf "$ROOT"; mkdir -p "$ROOT"
cid=$(docker create artixlinux/artixlinux:base-openrc /bin/true)
docker export "$cid" | tar -x -C "$ROOT"
docker rm "$cid" >/dev/null
rm -f "$ROOT/.dockerenv"
# VeyraOS system + live payload (the files the veyra-system/veyra-live packages install)
cp -a "$TOP/src/system/." "$ROOT/"
cp -a "$TOP/src/live/etc/init.d/." "$ROOT/etc/init.d/"
rm -f "$ROOT/etc/veyra/firewall/enabled/.keep"
# Kernel modules for the test kernel
mkdir -p "$ROOT/usr/lib/modules"
cp -a "$KROOT/lib/modules/$KVER" "$ROOT/usr/lib/modules/"
find "$ROOT/usr/lib/modules/$KVER" -name '*.ko.zst' -exec zstd -q -d --rm {} +
# nft is not in the base image: provide Ubuntu's build, isolated in /opt/nft
mkdir -p "$ROOT/opt/nft/lib"
cp "$(command -v nft)" "$ROOT/opt/nft/nft"
ldd "$(command -v nft)" | awk '/=> \//{print $3}' | while read -r lib; do
    case $(basename "$lib") in libc.so*|libm.so*|ld-linux*) continue ;; esac
    cp -L "$lib" "$ROOT/opt/nft/lib/"
done
printf '#!/bin/sh\nLD_LIBRARY_PATH=/opt/nft/lib exec /opt/nft/nft "$@"\n' > "$ROOT/usr/bin/nft"
chmod 755 "$ROOT/usr/bin/nft"
# Services as the real live system enables them
chroot "$ROOT" /bin/sh -c '
    rc-update add veyra-zram boot >/dev/null
    rc-update add veyra-firewall default >/dev/null
    rc-update add veyra-live default >/dev/null
    /usr/lib/veyra/make-text-runlevel
    /usr/lib/veyra/write-os-release
    depmod '"$KVER"'
'
# In-system test probe: runs at the end of boot (local service), reports on
# the serial port, powers off.
cat > "$ROOT/etc/local.d/zz-veyra-boot-test.start" <<'EOF'
#!/bin/sh
out=/dev/ttyS0
r() { echo "VEYRA-TEST: $*" > $out; }
check() { name=$1; shift; if "$@" >/dev/null 2>&1; then r "PASS $name"; else r "FAIL $name"; fi; }
r "BEGIN runlevel=$(rc-status -r) cmdline=$(cat /proc/cmdline)"
check root-is-overlay       sh -c 'findmnt -n -o FSTYPE / | grep -qx overlay'
check squashfs-mounted      sh -c 'findmnt -n -o FSTYPE /run/veyra/sfs | grep -qx squashfs'
check device-marker         test -s /run/veyra/device
check installer-image-link  sh -c '[ -L /run/veyra/rootfs.sfs ] && [ -f "$(readlink -f /run/veyra/rootfs.sfs)" ]'
if grep -q veyra.copytoram=1 /proc/cmdline; then
    check copytoram-medium-released sh -c '! findmnt /run/veyra/medium'
    check copytoram-ram-image       test -f /run/veyra/ram/rootfs.sfs
else
    check medium-mounted        sh -c 'findmnt -n -o FSTYPE /run/veyra/medium | grep -qx iso9660'
fi
check root-writable         sh -c 'echo ok > /etc/veyra-write-test && rm /etc/veyra-write-test'
check os-release-veyra      grep -q '^ID=veyraos' /etc/os-release
check machine-id            test -s /etc/machine-id
if [ "$(rc-status -r)" = text ]; then
    check text-runlevel-no-dm sh -c '! ls /etc/runlevels/text | grep -Eq "^(sddm|displaymanager)$"'
else
    check zram-swap-active      grep -q '^/dev/zram0 ' /proc/swaps
    check firewall-started      rc-service veyra-firewall status
    check firewall-policy-drop  sh -c 'nft list chain inet veyra input | grep -q "policy drop"'
    check firewall-service-toggle sh -c 'veyra-firewall enable-service ssh && nft list chain inet veyra services | grep -q "dport 22" && veyra-firewall disable-service ssh && ! nft list chain inet veyra services | grep -q "dport 22"'
    check sysctl-applied        sh -c '[ "$(cat /proc/sys/vm/page-cluster)" = 0 ]'
fi
check no-failed-services    sh -c '! rc-status --crashed | grep -q .'
r "SERVICES $(rc-status --all 2>/dev/null | grep -E 'started|stopped|crashed|failed' | tr -s ' ' | tr '\n' ';')"
# Diagnostics (always printed; cheap)
grep -E ' /run| / ' /proc/mounts | sed 's/^/VEYRA-DIAG: mount /' > $out
grep -h -iE 'zram|veyra' /var/log/rc.log 2>/dev/null | tail -20 | sed 's/^/VEYRA-DIAG: rc.log /' > $out
dmesg | grep -iE 'zram|zsmalloc|squashfs|overlay' | tail -10 | sed 's/^/VEYRA-DIAG: dmesg /' > $out
r "END"
sync
poweroff
EOF
chmod 755 "$ROOT/etc/local.d/zz-veyra-boot-test.start"
ok "rootfs ready ($(du -sh "$ROOT" | cut -f1))"

# ------------------------------------------------------------- initramfs ----
msg "Building test initramfs (mkinitcpio-compatible init + veyralive hook)"
rm -rf "$INITRD"; mkdir -p "$INITRD"/{bin,usr/bin,proc,sys,dev,run,new_root,hooks,lib/modules,lib64}
cp "$(command -v busybox)" "$INITRD/bin/busybox"
for b in blkid mount umount switch_root losetup kmod; do
    p=$(command -v "$b"); cp "$p" "$INITRD/usr/bin/$b"
    ldd "$p" | awk '/=> \//{print $3} /ld-linux/{print $1}' | while read -r lib; do
        [[ -f $lib ]] || continue
        mkdir -p "$INITRD$(dirname "$lib")"; cp -Ln "$lib" "$INITRD$lib" 2>/dev/null || true
    done
done
ln -s kmod "$INITRD/usr/bin/modprobe"
# overlay + isofs modules (everything else needed is built in)
# (decompressed: this Ubuntu kernel/kmod pairing passes .ko.zst to the kernel
#  undecompressed — a test-harness quirk, not relevant to the Artix build)
for m in fs/overlayfs/overlay fs/isofs/isofs; do
    mkdir -p "$(dirname "$INITRD/lib/modules/$KVER/kernel/$m")"
    zstd -q -d -f "$KROOT/lib/modules/$KVER/kernel/$m.ko.zst" -o "$INITRD/lib/modules/$KVER/kernel/$m.ko"
done
cp "$KROOT/lib/modules/$KVER"/modules.{order,builtin,builtin.modinfo} "$INITRD/lib/modules/$KVER/" 2>/dev/null || true
depmod -b "$INITRD" "$KVER"
cp "$TOP/src/live/usr/lib/initcpio/hooks/veyralive" "$INITRD/hooks/veyralive"
cat > "$INITRD/init" <<'EOF'
#!/bin/busybox sh
# Minimal stand-in for mkinitcpio's /init: same hook interface.
/bin/busybox --install -s /bin
export PATH=/usr/bin:/bin
# Ubuntu's static busybox prefers its own applets over PATH. mkinitcpio ships
# util-linux mount/umount/blkid/switch_root, so make sure those are used.
mount() { /usr/bin/mount "$@"; }
umount() { /usr/bin/umount "$@"; }
blkid() { /usr/bin/blkid "$@"; }
losetup() { /usr/bin/losetup "$@"; }
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev
mount -t tmpfs run /run -o nosuid,nodev,mode=0755
msg() { echo "$@"; }
err() { echo "ERROR: $*"; }
launch_interactive_shell() { echo "(emergency shell requested — test FAILS)"; echo "VEYRA-TEST: FAIL initramfs-emergency" > /dev/ttyS0; poweroff -f; }
mount_handler=default_mount_handler
default_mount_handler() { err "no live hook handled the root"; launch_interactive_shell; }
. /hooks/veyralive
run_hook
"$mount_handler" /new_root
[ -x /new_root/sbin/init ] || { err "no init in new root"; launch_interactive_shell; }
exec /usr/bin/switch_root /new_root /sbin/init
EOF
chmod 755 "$INITRD/init"

# ----------------------------------------------------------------- image ----
msg "Assembling test ISO with build/lib/iso.sh"
rm -rf "$ISO"; mkdir -p "$ISO/boot/grub/fonts" "$ISO/veyra/x86_64" "$ISO/boot/grub/themes"
cp "$KROOT/boot/vmlinuz-$KVER" "$ISO/boot/vmlinuz-linux"
(cd "$INITRD" && find . | cpio -o -H newc --quiet | zstd -q -19 -T0) > "$ISO/boot/initramfs-linux.img"
cp /usr/share/grub/unicode.pf2 "$ISO/boot/grub/fonts/" 2>/dev/null || true
cp -a "$TOP/src/branding/grub/veyra" "$ISO/boot/grub/themes/"
VEYRA_NAME=VeyraOS VEYRA_VERSION=boot-test \
    write_grub_cfg "$ISO" "$LABEL" "console=ttyS0,115200 loglevel=4" linux
mksquashfs "$ROOT" "$ISO/veyra/x86_64/rootfs.sfs" -comp zstd -Xcompression-level 3 -b 1M -noappend -quiet
(cd "$ISO/veyra/x86_64" && sha512sum rootfs.sfs > rootfs.sha512)
make_iso "$ISO" "$W/test.iso" "$LABEL" >/dev/null 2>&1
ok "test ISO: $(du -h "$W/test.iso" | cut -f1)"

# ------------------------------------------------------------------ boot ----
# boot_case <name> <firmware: bios|uefi> <grub entry> [media: disk|cdrom]
FAILED=0
boot_case() {
    local name=$1 fw=$2 entry=$3 media=${4:-disk} iso="$W/test-$1.iso" log="$W/serial-$1.log"
    msg "Boot case: $name ($fw, entry $entry, $media)"
    # Same image with a different default menu entry (GRUB cfg lives in the ISO)
    cp -a "$ISO" "$W/iso-$name"
    sed -i "s/^set default=0/set default=\"$entry\"/; s/^set timeout=10/set timeout=1/" "$W/iso-$name/boot/grub/grub.cfg"
    make_iso "$W/iso-$name" "$iso" "$LABEL" >/dev/null 2>&1
    rm -rf "$W/iso-$name"
    local -a fwargs=() drive=()
    if [[ $fw == uefi ]]; then
        cp /usr/share/OVMF/OVMF_VARS_4M.fd "$W/vars.fd"
        fwargs=(-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
                -drive if=pflash,format=raw,file="$W/vars.fd")
    fi
    if [[ $media == cdrom ]]; then drive=(-cdrom "$iso"); else drive=(-drive file="$iso",format=raw,if=virtio,readonly=on); fi
    : > "$log"
    timeout 1500 qemu-system-x86_64 -m 3072 -smp 2 -accel tcg "${fwargs[@]}" "${drive[@]}" \
        -display none -vga std -serial file:"$log" -no-reboot \
        -monitor unix:"$W/mon-$name.sock",server,nowait &
    local qpid=$!
    # Screenshot of the boot menu for visual review
    sleep 12; printf 'screendump %s\n' "$W/grub-$name.ppm" | socat - UNIX-CONNECT:"$W/mon-$name.sock" >/dev/null 2>&1 || true
    wait "$qpid" || true
    if grep -q 'VEYRA-TEST: END' "$log" && ! grep -q 'VEYRA-TEST: FAIL' "$log"; then
        ok "$name: $(grep -c 'VEYRA-TEST: PASS' "$log") checks passed"
    else
        warn "$name: FAILED"; grep 'VEYRA-TEST' "$log" >&2 || tail -30 "$log" >&2; FAILED=1
    fi
    grep 'VEYRA-TEST' "$log" | sed "s/^/    [$name] /" >&2 || true
}

for c in "${CASES[@]}"; do
    case $c in
        bios)      boot_case bios bios 0 cdrom ;;
        uefi)      boot_case uefi uefi 0 disk ;;
        copytoram) boot_case copytoram bios 1 disk ;;
        verify)    boot_case verify bios "2>2" disk ;;
        textmode)  boot_case textmode bios "2>1" disk ;;
        *) die "unknown case $c" ;;
    esac
done
((KEEP)) || rm -rf "$ROOT" "$ISO" "$INITRD"
((FAILED == 0)) && ok "all boot cases passed" || die "boot test failed"
