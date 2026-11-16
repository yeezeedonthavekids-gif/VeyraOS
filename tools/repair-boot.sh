#!/bin/bash
# Repair an installed VeyraOS whose GRUB stops with
#   "premature end of file /@/boot/vmlinuz-..."
# Run from the VeyraOS live USB:   sudo bash repair-boot.sh [/dev/BTRFS-PARTITION [/dev/EFI-PARTITION]]
#
# 1. mounts the installed system (btrfs subvolume @) and its EFI partition
# 2. rewrites /boot without btrfs compression
# 3. copies the kernels to the EFI partition (FAT — GRUB always reads it) and
#    adds boot entries that load them from there (kept current by a pacman hook)
# 4. regenerates grub.cfg and shows what GRUB will boot
set -uo pipefail
[[ $EUID -eq 0 ]] || exec sudo bash "$0" "$@"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

PART=${1:-}
if [[ -z $PART ]]; then
    # the btrfs partition that contains a VeyraOS installation
    for p in $(lsblk -rpno NAME,FSTYPE | awk '$2=="btrfs"{print $1}'); do PART=$p; break; done
fi
[[ -b $PART ]] || die "no btrfs partition found (pass it, e.g. /dev/nvme1n1p2)"
DISK=$(lsblk -rpno PKNAME "$PART" | head -1)
M=/mnt/veyra-repair
mkdir -p "$M"
cleanup() {
    for d in sys/firmware/efi/efivars sys proc dev/pts dev run boot/efi ""; do
        mountpoint -q "$M/$d" && umount "$M/$d"
    done
}
trap cleanup EXIT
cleanup
mount -o subvol=@ "$PART" "$M" || die "cannot mount $PART (subvolume @)"
[[ -d $M/boot && -d $M/usr/lib/modules ]] || die "$PART does not look like a VeyraOS installation"
# EFI partition: given on the command line, else the one the installation
# uses (fstab), else the EFI partition on the same disk.
ESP=${2:-}
if [[ -z $ESP ]]; then
    spec=$(awk '$1 !~ /^#/ && $2=="/boot/efi"{print $1; exit}' "$M/etc/fstab" 2>/dev/null)
    [[ -n $spec ]] && ESP=$(blkid -l -o device -t "$spec" 2>/dev/null || findfs "$spec" 2>/dev/null)
fi
[[ -n $ESP ]] || ESP=$(lsblk -rpno NAME,PARTTYPE "$DISK" | awk 'tolower($2)=="c12a7328-f81f-11d2-ba4b-00a0c93ec93b"{print $1; exit}')
[[ -b $ESP ]] || die "no EFI partition found for this installation"
say "installed system: $PART   EFI partition: $ESP"
mkdir -p "$M/boot/efi"
mount "$ESP" "$M/boot/efi" || die "cannot mount $ESP"
for d in proc sys dev; do mount --bind "/$d" "$M/$d" || die "cannot bind /$d"; done
mount --bind /sys/firmware/efi/efivars "$M/sys/firmware/efi/efivars" 2>/dev/null || true

say "1/4  storing /boot without compression"
chattr +m "$M/boot" 2>/dev/null || true
btrfs property set "$M/boot" compression none 2>/dev/null || true
for k in "$M"/usr/lib/modules/*/; do
    [[ -f $k/vmlinuz && -f $k/pkgbase ]] || continue
    cp --reflink=never -f "$k/vmlinuz" "$M/boot/vmlinuz-$(cat "$k/pkgbase")"
done
for f in "$M"/boot/initramfs-*.img "$M"/boot/*-ucode.img; do
    [[ -f $f ]] || continue
    cp --reflink=never "$f" "$f.new" && mv -f "$f.new" "$f"
done
sync
ls -l "$M"/boot/vmlinuz-* "$M"/boot/*.img

say "2/4  copying the kernels to the EFI partition"
install -Dm755 /dev/stdin "$M/usr/lib/veyra/esp-kernels" <<'VEYRA_EOF_1'
#!/bin/bash
# Keeps a copy of the kernels and initramfs images on the EFI partition.
#
# GRUB reads FAT reliably; reading large kernel images from a btrfs root
# failed on real hardware ("premature end of file"). When this mode is on
# (/boot/efi/veyra exists), /etc/grub.d/09_veyra_esp adds boot entries that
# load the kernel from the EFI partition, and a pacman hook re-runs this
# script after every kernel/initramfs change.
#
#   esp-kernels enable   turn the mode on if the EFI partition is big enough
#   esp-kernels          refresh the copies (no-op while the mode is off)
set -uo pipefail
ESP=${VEYRA_ESP:-/boot/efi}
BOOT=${VEYRA_BOOT:-/boot}
D=$ESP/veyra
log() { echo "esp-kernels: $*"; }

size_mb() { local t=0 f; for f in "$@"; do [[ -f $f ]] && t=$(( t + $(stat -c %s "$f") / 1048576 + 1 )); done; echo "$t"; }
free_mb() { df -m --output=avail "$ESP" | tail -1 | tr -d ' '; }

if [[ ${1:-} == enable ]]; then
    if [[ $(stat -f -c %T "$ESP" 2>/dev/null) != msdos ]] || ! mountpoint -q "$ESP"; then
        log "no EFI partition mounted at $ESP; kernels stay in $BOOT"; exit 0
    fi
    rm -rf "$D"
    need=$(size_mb "$BOOT/vmlinuz-linux" "$BOOT/initramfs-linux.img" "$BOOT"/*-ucode.img)
    if (( need + 16 > $(free_mb) )); then
        log "EFI partition too small (${need} MB needed, $(free_mb) MB free); kernels stay in $BOOT"; exit 0
    fi
    mkdir -p "$D"
fi
[[ -d $D ]] || exit 0

rm -f "$D"/*
for f in "$BOOT"/*-ucode.img; do [[ -f $f ]] && cp "$f" "$D/"; done
# Main kernel first; further kernels only while they fit.
for k in "$BOOT/vmlinuz-linux" "$BOOT"/vmlinuz-*; do
    [[ -f $k ]] || continue
    n=${k##*/vmlinuz-}
    [[ -f $D/vmlinuz-$n ]] && continue
    i=$BOOT/initramfs-$n.img
    [[ -f $i ]] || continue
    if (( $(size_mb "$k" "$i") + 8 > $(free_mb) )); then
        log "no room for the '$n' kernel on the EFI partition (skipped)"; continue
    fi
    if cp "$k" "$D/" && cp "$i" "$D/"; then log "copied $n"
    else rm -f "$D/vmlinuz-$n" "$D/initramfs-$n.img"; log "copy of '$n' failed"; fi
done
sync
exit 0
VEYRA_EOF_1
install -Dm755 /dev/stdin "$M/etc/grub.d/09_veyra_esp" <<'VEYRA_EOF_2'
#!/bin/sh
# Boot entries that load the kernel from the EFI partition (FAT) instead of
# the btrfs root. Active only when /usr/lib/veyra/esp-kernels has put kernels
# into /boot/efi/veyra. These entries come first, so they are the default;
# the regular entries (kernel read from /boot) stay below as a fallback.
set -e
ESP=${VEYRA_ESP:-/boot/efi}
ls "$ESP"/veyra/vmlinuz-* >/dev/null 2>&1 || exit 0
esp_uuid=$(grub-probe --target=fs_uuid "$ESP" 2>/dev/null) || exit 0
root_uuid=${GRUB_DEVICE_UUID:-$(grub-probe --target=fs_uuid / 2>/dev/null)} || exit 0
[ -n "$esp_uuid" ] && [ -n "$root_uuid" ] || exit 0
flags=""
if [ "$(grub-probe --target=fs / 2>/dev/null)" = btrfs ]; then
    sub=$(grub-mkrelpath / 2>/dev/null | sed 's|^/||')
    [ -n "$sub" ] && flags="rootflags=subvol=$sub"
fi
ucode=""
for u in "$ESP"/veyra/*-ucode.img; do [ -f "$u" ] && ucode="$ucode /veyra/${u##*/}"; done
entry() { # entry NAME TITLE
    [ -f "$ESP/veyra/vmlinuz-$1" ] && [ -f "$ESP/veyra/initramfs-$1.img" ] || return 0
    echo "Found VeyraOS kernel on the EFI partition: $1" >&2
    cat <<EOF
menuentry '$2' --class veyra --class gnu-linux --class os {
    insmod part_gpt
    insmod fat
    search --no-floppy --fs-uuid --set=root $esp_uuid
    echo 'Loading VeyraOS ...'
    linux /veyra/vmlinuz-$1 root=UUID=$root_uuid rw $flags $GRUB_CMDLINE_LINUX $GRUB_CMDLINE_LINUX_DEFAULT
    initrd$ucode /veyra/initramfs-$1.img
}
EOF
}
entry linux "VeyraOS"
for k in "$ESP"/veyra/vmlinuz-*; do
    n=${k##*/vmlinuz-}
    [ "$n" = linux ] || entry "$n" "VeyraOS ($n kernel)"
done
VEYRA_EOF_2
install -Dm644 /dev/stdin "$M/etc/pacman.d/hooks/95-veyra-esp-kernels.hook" <<'VEYRA_EOF_3'
[Trigger]
Type = Path
Operation = Install
Operation = Upgrade
Operation = Remove
Target = usr/lib/modules/*/vmlinuz
Target = usr/lib/initcpio/*
Target = usr/lib/firmware/*
Target = usr/src/*/dkms.conf
Target = boot/*-ucode.img

[Action]
Description = Updating the kernels on the EFI partition...
When = PostTransaction
Exec = /usr/lib/veyra/esp-kernels
VEYRA_EOF_3
rm -f "$M/etc/pacman.d/hooks/99-veyra-esp-kernels.hook"
echo "EFI partition: $(df -h --output=size,avail "$M/boot/efi" | tail -1)  (size, free)"
chroot "$M" /usr/lib/veyra/esp-kernels enable
ls -l "$M/boot/efi/veyra" 2>/dev/null
[[ -f $M/boot/efi/veyra/vmlinuz-linux || -n $(ls "$M"/boot/efi/veyra/vmlinuz-* 2>/dev/null) ]] \
    || die "the kernels did not fit on the EFI partition — send Claude a photo of this screen"
# every copy must be byte-identical
for f in "$M"/boot/efi/veyra/*; do
    cmp -s "$f" "$M/boot/${f##*/}" || die "copy of ${f##*/} is damaged"
done
echo "copies verified"

say "3/4  regenerating the GRUB menu"
chroot "$M" grub-mkconfig -o /boot/grub/grub.cfg 2>&1 | tail -8
grep -q "/veyra/vmlinuz-" "$M/boot/grub/grub.cfg" || die "grub.cfg has no EFI-partition entry — send Claude a photo of this screen"

say "4/4  what GRUB will start (first entry is the default)"
grep -E "^menuentry|^submenu" "$M/boot/grub/grub.cfg" | cut -d"'" -f2 | sed 's/^/   /'
grep -m1 -E "^\s*linux /veyra/" "$M/boot/grub/grub.cfg" | cut -c1-150
sync
printf '\n\033[1;32m== DONE — shut down, remove the USB stick, start from the second SSD (F11)\033[0m\n'
