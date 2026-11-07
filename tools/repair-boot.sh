#!/bin/bash
# Repair an installed VeyraOS whose GRUB stops with
#   "premature end of file /@/boot/vmlinuz-..."
# Run from the VeyraOS live USB:   sudo bash repair-boot.sh [/dev/BTRFS-PARTITION]
#
# 1. mounts the installed system (btrfs subvolume @) and its EFI partition
# 2. asks GRUB's own file-system driver (grub-fstest) whether it can read
#    every kernel and initramfs exactly
# 3. if not: rewrites /boot without btrfs compression and tests again
# 4. if GRUB still cannot read them: keeps a copy of the kernels on the EFI
#    partition (FAT, always readable by GRUB) and boots from there
# 5. regenerates grub.cfg
set -uo pipefail
[[ $EUID -eq 0 ]] || exec sudo bash "$0" "$@"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

PART=${1:-}
if [[ -z $PART ]]; then
    PART=$(lsblk -rpno NAME,FSTYPE | awk '$2=="btrfs"{print $1; exit}')
fi
[[ -b $PART ]] || die "no btrfs partition found (pass it, e.g. /dev/nvme1n1p2)"
DISK=/dev/$(lsblk -no PKNAME "$PART" | head -1)
ESP=$(lsblk -rpno NAME,PARTTYPE "$DISK" | awk 'tolower($2)=="c12a7328-f81f-11d2-ba4b-00a0c93ec93b"{print $1; exit}')
say "installed system: $PART   EFI partition: ${ESP:-none}"

M=/mnt/veyra-repair
mkdir -p "$M"
cleanup() {
    for d in sys/firmware/efi/efivars sys proc dev/pts dev run boot/efi ""; do
        mountpoint -q "$M/$d" && umount "$M/$d"
    done
}
trap cleanup EXIT
mountpoint -q "$M" || mount -o subvol=@ "$PART" "$M" || die "cannot mount $PART (subvolume @)"
[[ -d $M/boot && -d $M/usr/lib/modules ]] || die "$PART does not look like a VeyraOS installation"
if [[ -n $ESP ]]; then
    mkdir -p "$M/boot/efi"
    mountpoint -q "$M/boot/efi" || mount "$ESP" "$M/boot/efi" || die "cannot mount $ESP"
fi

boot_files() { ls "$M"/boot/vmlinuz-* "$M"/boot/initramfs-*.img "$M"/boot/*-ucode.img 2>/dev/null; }

# Returns 0 when GRUB's btrfs driver reads every boot file byte-exactly.
grub_reads_all() {
    local f ok=0
    if ! command -v grub-fstest >/dev/null; then
        echo "  (grub-fstest not available — cannot test, assuming not readable)"; return 1
    fi
    for f in $(boot_files); do
        if grub-fstest "$PART" cmp "/@/boot/${f##*/}" "$f" >/dev/null 2>&1; then
            echo "  OK      ${f##*/}"
        else
            echo "  FAILED  ${f##*/}"; ok=1
        fi
    done
    return $ok
}

say "files in /boot"
ls -l "$M/boot"
say "can GRUB read them?"
if grub_reads_all; then
    echo "GRUB reads all boot files — they are fine."
else
    say "rewriting /boot without compression"
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
    sync; blockdev --flushbufs "$PART" 2>/dev/null; echo 3 > /proc/sys/vm/drop_caches
    echo "compressed extents left in vmlinuz files: $(for f in "$M"/boot/vmlinuz-*; do filefrag -v "$f"; done | grep -c encoded)"
    say "can GRUB read them now?"
    if grub_reads_all; then
        echo "Fixed: GRUB reads all boot files."
    elif [[ -n $ESP ]]; then
        say "GRUB still cannot read btrfs here — keeping the kernels on the EFI partition"
        # shellcheck disable=SC2046
        need=$(du -cm $(boot_files) | tail -1 | cut -f1)
        free=$(df -m --output=avail "$M/boot/efi" | tail -1 | tr -d ' ')
        echo "  needs ${need} MB, EFI partition has ${free} MB free"
        (( need + 10 < free )) || die "EFI partition too small — tell Claude these numbers"
        install -Dm755 /dev/stdin "$M/usr/lib/veyra/esp-kernels" <<'EOS'
#!/bin/sh
# Copy kernels/initramfs to the EFI partition (GRUB cannot read them on this btrfs).
mkdir -p /boot/efi/veyra || exit 0
rm -f /boot/efi/veyra/*
for f in /boot/vmlinuz-* /boot/initramfs-*.img /boot/*-ucode.img; do
    [ -f "$f" ] && cp "$f" /boot/efi/veyra/
done
sync
EOS
        install -Dm644 /dev/stdin "$M/etc/pacman.d/hooks/99-veyra-esp-kernels.hook" <<'EOS'
[Trigger]
Type = Path
Operation = Install
Operation = Upgrade
Operation = Remove
Target = usr/lib/modules/*/vmlinuz
Target = usr/lib/initcpio/*
Target = usr/lib/firmware/*
Target = usr/src/*/dkms.conf

[Action]
Description = Copying kernels to the EFI partition...
When = PostTransaction
Exec = /usr/lib/veyra/esp-kernels
EOS
        # GRUB_TOP_LEVEL etc. stay; grub.cfg entries get their paths from a
        # menu file that points at the EFI copies.
        install -Dm755 /dev/stdin "$M/etc/grub.d/09_veyra_esp" <<'EOS'
#!/bin/sh
# Boot entries that load the kernel from the EFI partition (see /usr/lib/veyra/esp-kernels).
esp_uuid=$(grub-probe --target=fs_uuid /boot/efi 2>/dev/null) || exit 0
root_uuid=$(grub-probe --target=fs_uuid / 2>/dev/null) || exit 0
opts=$(. /etc/default/grub; echo "$GRUB_CMDLINE_LINUX $GRUB_CMDLINE_LINUX_DEFAULT")
for k in /boot/efi/veyra/vmlinuz-*; do
    [ -f "$k" ] || continue
    n=${k##*/vmlinuz-}
    ucode=""
    for u in /boot/efi/veyra/*-ucode.img; do [ -f "$u" ] && ucode="$ucode /veyra/${u##*/}"; done
    cat <<EOF
menuentry 'VeyraOS ($n)' --class veyra --class gnu-linux {
    insmod part_gpt
    insmod fat
    search --no-floppy --fs-uuid --set=root $esp_uuid
    echo 'Loading VeyraOS ($n) ...'
    linux /veyra/vmlinuz-$n root=UUID=$root_uuid rw rootflags=subvol=@ $opts
    initrd $ucode /veyra/initramfs-$n.img
}
EOF
done
EOS
        mount --bind /proc "$M/proc"; mount --bind /sys "$M/sys"; mount --bind /dev "$M/dev"
        chroot "$M" /usr/lib/veyra/esp-kernels
        echo "Kernels copied to the EFI partition; they are kept up to date on every update."
    else
        die "GRUB cannot read the boot files and there is no EFI partition"
    fi
fi

say "regenerating the GRUB menu"
for d in proc sys dev; do mountpoint -q "$M/$d" || mount --bind "/$d" "$M/$d"; done
mountpoint -q "$M/sys/firmware/efi/efivars" || mount --bind /sys/firmware/efi/efivars "$M/sys/firmware/efi/efivars" 2>/dev/null
chroot "$M" grub-mkconfig -o /boot/grub/grub.cfg 2>&1 | tail -5
grep -E "^menuentry|^submenu" "$M/boot/grub/grub.cfg" | cut -c1-80
sync
say "done — shut down, remove the USB stick, and start from the second SSD (F11)"
