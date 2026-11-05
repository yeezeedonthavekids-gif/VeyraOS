#!/usr/bin/env bash
# VeyraOS ISO builder. Run as root on Artix Linux (or inside the
# artixlinux/artixlinux:base-devel container — see build/build-in-docker.sh).
#
#   build/build-iso.sh [--work DIR] [--out DIR] [--stage STAGE] [--keep-work]
#
# Stages (run in order; --stage runs from that stage onward):
#   host      install build tools on the build host
#   packages  build the VeyraOS packages (pkgbuilds/) into a local repo
#   resolve   resolve package manifests against the repositories
#   rootfs    install the root filesystem
#   configure configure the live system (chroot)
#   verify    policy checks (no systemd, required files, services)
#   image     squashfs + live initramfs + GRUB + ISO
set -Eeuo pipefail

TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=build/lib/common.sh
source "$TOP/build/lib/common.sh"
# shellcheck source=build/lib/packages.sh
source "$TOP/build/lib/packages.sh"
# shellcheck source=build/lib/iso.sh
source "$TOP/build/lib/iso.sh"
# shellcheck source=build/profile.conf
source "$TOP/build/profile.conf"

WORK=/var/tmp/veyra-build
OUT=$TOP/out
START_STAGE=host
KEEP_WORK=0
STAGES=(host packages resolve rootfs configure verify image)

usage() { sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
while (($#)); do
    case $1 in
        --work) WORK=$2; shift 2 ;;
        --out) OUT=$2; shift 2 ;;
        --stage) START_STAGE=$2; shift 2 ;;
        --keep-work) KEEP_WORK=1; shift ;;
        -h|--help) usage 0 ;;
        *) warn "unknown argument: $1"; usage 1 ;;
    esac
done

[[ $EUID -eq 0 ]] || die "must run as root"
[[ " ${STAGES[*]} " == *" $START_STAGE "* ]] || die "unknown stage '$START_STAGE' (valid: ${STAGES[*]})"

ROOT=$WORK/rootfs
ISO=$WORK/iso
REPO=$WORK/repo
CONF=$WORK/pacman.conf
CACHE=$WORK/pkgcache
RESOLVED=$WORK/packages.resolved
ISO_NAME="${VEYRA_ID}-${VEYRA_VERSION}-${VEYRA_CHANNEL}-x86_64"
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -C "$TOP" log -1 --format=%ct 2>/dev/null || date +%s)}

mkdir -p "$WORK" "$OUT" "$REPO" "$CACHE"
exec > >(tee -a "$OUT/$ISO_NAME.build.log") 2>&1
trap 'chroot_teardown' EXIT
trap 'warn "build failed at line $LINENO (stage: ${CUR_STAGE:-?})"' ERR

should_run() {
    local s seen=0
    for s in "${STAGES[@]}"; do
        [[ $s == "$START_STAGE" ]] && seen=1
        [[ $s == "$1" ]] && { ((seen)) && return 0 || return 1; }
    done
    return 1
}

write_pacman_conf() {
    sed "s|@REPO_DIR@|$REPO|" "$TOP/build/pacman.conf.in" > "$CONF"
}

# ---------------------------------------------------------------------------
stage_host() {
    msg "Preparing build host"
    grep -qi artix /etc/os-release || die "the build host must be Artix Linux (use build/build-in-docker.sh elsewhere)"
    # The Arch repos (extra/multilib) are enabled through artix-archlinux-support.
    pacman -Sy --noconfirm --needed artix-archlinux-support archlinux-keyring artix-keyring
    [[ -f /etc/pacman.d/mirrorlist-arch ]] || die "/etc/pacman.d/mirrorlist-arch missing (archlinux-mirrorlist)"
    sh "$TOP/src/system/usr/lib/veyra/ensure-arch-mirror" /etc/pacman.d/mirrorlist-arch
    pacman-key --init
    pacman-key --populate artix archlinux
    write_pacman_conf
    # repo-add needs the [veyra] db to exist before the first -Sy
    [[ -f $REPO/veyra.db.tar.gz ]] || repo-add -q "$REPO/veyra.db.tar.gz"
    pacman --config "$CONF" -Syu --noconfirm --needed \
        base-devel git squashfs-tools libisoburn grub mtools dosfstools freetype2 sudo
    id veyrabuild >/dev/null 2>&1 || useradd -m -r -s /bin/bash veyrabuild
    # makepkg resolves build dependencies through this wrapper so it sees the
    # same repositories (incl. [veyra], extra, multilib) as the image build.
    install -Dm755 /dev/stdin /usr/local/bin/veyra-pacman <<EOF2
#!/bin/sh
exec /usr/bin/pacman --config $CONF "\$@"
EOF2
    install -Dm440 /dev/stdin /etc/sudoers.d/90-veyrabuild \
        <<< 'veyrabuild ALL=(root) NOPASSWD: /usr/local/bin/veyra-pacman, /usr/bin/pacman'
    ok "build host ready"
}

# ---------------------------------------------------------------------------
build_local_pkg() {
    local name=$1 dir="$TOP/pkgbuilds/$1" bdir="$WORK/pkgbuild/$1"
    [[ -f $dir/PKGBUILD ]] || { warn "no PKGBUILD for $name"; return 1; }
    rm -rf "$bdir"; mkdir -p "$bdir"
    cp -a "$dir/." "$bdir/"
    chown -R veyrabuild: "$bdir"
    msg2 "building $name"
    # Architecture-independent (data/script) packages need no build deps: -d.
    # Compiled packages install their makedepends via the veyra-pacman wrapper.
    local depflag=-s
    grep -Eq "^arch=\(['\"]?any['\"]?\)" "$bdir/PKGBUILD" && depflag=-d
    sudo -u veyrabuild env VEYRA_SRC="$WORK/src" PKGDEST="$bdir/out" SRCDEST="$bdir" \
        PACMAN=/usr/local/bin/veyra-pacman \
        makepkg "$depflag" --noconfirm --needed --cleanbuild -D "$bdir" \
        > "$bdir/build.log" 2>&1 || { tail -40 "$bdir/build.log" >&2; return 1; }
    cp "$bdir"/out/*.pkg.tar.zst "$REPO/"
}

stage_packages() {
    msg "Building VeyraOS packages"
    write_pacman_conf
    # Read-only copy of the sources for makepkg (runs as an unprivileged user).
    rm -rf "$WORK/src"; cp -a "$TOP/src" "$WORK/src"; chmod -R a+rX "$WORK/src"
    rm -f "$REPO"/*.pkg.tar.zst "$REPO"/veyra.*
    local p failed=()
    for p in "${LOCAL_PKGS[@]}"; do
        build_local_pkg "$p" || die "failed to build required package $p"
    done
    for p in "${OPTIONAL_LOCAL_PKGS[@]}"; do
        build_local_pkg "$p" || { warn "optional package $p failed to build; skipping"; failed+=("$p"); }
    done
    repo-add -q "$REPO/veyra.db.tar.gz" "$REPO"/*.pkg.tar.zst
    chmod -R a+rX "$REPO"
    pacman --config "$CONF" -Sy
    ok "local repo: $(find "$REPO" -name '*.pkg.tar.zst' | wc -l) packages"
}

# Calamares fallback: if the repos lack calamares, build it from pkgbuilds/.
ensure_calamares() {
    local index=$1
    if ! grep -qx calamares "$index"; then
        warn "calamares not found in repositories — building pkgbuilds/veyra-calamares from source"
        build_local_pkg veyra-calamares || die "calamares fallback build failed"
        repo-add -q "$REPO/veyra.db.tar.gz" "$REPO"/veyra-calamares-*.pkg.tar.zst
        pacman --config "$CONF" -Sy
        build_package_index "$CONF" "$index"
    fi
}

stage_resolve() {
    msg "Resolving package manifests"
    write_pacman_conf
    pacman --config "$CONF" -Sy
    local index=$WORK/package-index
    build_package_index "$CONF" "$index"
    ensure_calamares "$index"
    local -a lists=() l
    for l in "${PACKAGE_LISTS[@]}"; do lists+=("$TOP/packages/$l.list"); done
    resolve_manifests "$index" "$RESOLVED" "${lists[@]}" \
        || die "required packages are missing (see MISSING lines above)"
    # All VeyraOS packages from the local repo:
    pacman --config "$CONF" -Slq veyra | grep -vx veyra-calamares >> "$RESOLVED" || true
    sort -u -o "$RESOLVED" "$RESOLVED"
    ok "$(wc -l < "$RESOLVED") packages selected"
}

# ---------------------------------------------------------------------------
stage_rootfs() {
    msg "Installing root filesystem into $ROOT"
    chroot_teardown
    if [[ -d $ROOT ]]; then rm -rf --one-file-system "$ROOT"; fi
    mkdir -p "$ROOT"/var/lib/pacman "$ROOT"/etc
    chroot_setup "$ROOT"
    local -a pkgs
    mapfile -t pkgs < "$RESOLVED"
    pacman --config "$CONF" --root "$ROOT" --cachedir "$CACHE" --gpgdir /etc/pacman.d/gnupg \
        --hookdir "$ROOT/etc/pacman.d/hooks" \
        -Sy --noconfirm --needed "${pkgs[@]}"
    # Installed-system pacman.conf comes from veyra-system (/etc/pacman.conf).
    chroot_teardown
    ok "root filesystem installed ($(du -sh "$ROOT" | cut -f1))"
}

stage_configure() {
    msg "Configuring the live system"
    chroot_setup "$ROOT"
    install -Dm755 "$TOP/build/chroot-configure.sh" "$ROOT/root/veyra-configure.sh"
    {
        printf 'LIVE_USER=%q\nLIVE_HOSTNAME=%q\nLIVE_LOCALE=%q\nLIVE_TIMEZONE=%q\nLIVE_KEYMAP=%q\n' \
            "$LIVE_USER" "$LIVE_HOSTNAME" "$LIVE_LOCALE" "$LIVE_TIMEZONE" "$LIVE_KEYMAP"
        printf 'VEYRA_VERSION=%q\nVEYRA_CHANNEL=%q\nKERNELS=(%s)\n' "$VEYRA_VERSION" "$VEYRA_CHANNEL" "${KERNELS[*]}"
    } > "$ROOT/root/veyra-configure.env"
    in_chroot "$ROOT" /bin/bash /root/veyra-configure.sh
    rm -f "$ROOT/root/veyra-configure.sh" "$ROOT/root/veyra-configure.env"
    chroot_teardown
    ok "live system configured"
}

# ---------------------------------------------------------------------------
stage_verify() {
    msg "Verifying policy"
    local fail=0 p
    for p in systemd systemd-sysvcompat systemd-libs; do
        if pacman --root "$ROOT" -Q "$p" >/dev/null 2>&1; then
            warn "POLICY VIOLATION: package '$p' is installed"; fail=1
        fi
    done
    if [[ -e $ROOT/usr/lib/systemd/systemd ]]; then warn "POLICY VIOLATION: systemd init binary present"; fail=1; fi
    [[ $(readlink "$ROOT/usr/bin/init") == openrc-init ]] || { warn "init is not openrc-init"; fail=1; }
    for p in "${KERNELS[@]}"; do
        [[ -f $ROOT/boot/vmlinuz-$p ]] || { warn "kernel $p missing"; fail=1; }
        compgen -G "$ROOT/usr/lib/modules/*/updates/dkms/nvidia.ko*" >/dev/null \
          || compgen -G "$ROOT/usr/lib/modules/*/extramodules/nvidia.ko*" >/dev/null \
          || compgen -G "$ROOT/usr/lib/modules/*/*/nvidia.ko*" >/dev/null \
          || { warn "NVIDIA kernel module was not built"; fail=1; }
    done
    for p in NetworkManager dbus elogind veyra-firewall veyra-zram veyra-live; do
        compgen -G "$ROOT/etc/runlevels/*/$p" >/dev/null || { warn "service $p is not enabled"; fail=1; }
    done
    [[ -d $ROOT/etc/runlevels/text ]] || { warn "text runlevel missing"; fail=1; }
    [[ ! -e $ROOT/etc/pacman.d/gnupg/secring.gpg && ! -d $ROOT/etc/pacman.d/gnupg/private-keys-v1.d ]] \
        || { warn "pacman keyring (private key) present in image"; fail=1; }
    ((fail == 0)) || die "verification failed"
    pacman --root "$ROOT" -Q > "$OUT/$ISO_NAME.packages.txt"
    ok "policy checks passed; manifest written to $OUT/$ISO_NAME.packages.txt"
}

# ---------------------------------------------------------------------------
stage_image() {
    msg "Assembling the ISO"
    rm -rf "$ISO"; mkdir -p "$ISO/boot/grub/fonts" "$ISO/veyra/x86_64"
    local k
    # Live initramfs per kernel (separate mkinitcpio config with the veyralive hook)
    chroot_setup "$ROOT"
    for k in "${KERNELS[@]}"; do
        local kver
        kver=$(basename "$(dirname "$(grep -lx "$k" "$ROOT"/usr/lib/modules/*/pkgbase | head -1)")")
        [[ -n $kver ]] || die "cannot determine module version for $k"
        in_chroot "$ROOT" mkinitcpio -c /etc/veyra/mkinitcpio-live.conf -k "$kver" -g "/boot/initramfs-$k-live.img"
        cp "$ROOT/boot/vmlinuz-$k" "$ISO/boot/vmlinuz-$k"
        mv "$ROOT/boot/initramfs-$k-live.img" "$ISO/boot/initramfs-$k.img"
    done
    chroot_teardown
    for k in amd-ucode.img intel-ucode.img; do
        [[ -f $ROOT/boot/$k ]] && cp "$ROOT/boot/$k" "$ISO/boot/"
    done
    if [[ -f $ROOT/boot/memtest86+/memtest.efi ]]; then
        install -Dm644 "$ROOT/boot/memtest86+/memtest.efi" "$ISO/boot/memtest86+/memtest.efi"
    fi

    # GRUB font + theme (from veyra-branding)
    local font
    font=$(find "$ROOT/usr/share/fonts" -iname 'Inter*Regular*.tt*' -o -iname 'DejaVuSans.ttf' 2>/dev/null | head -1)
    if [[ -n $font ]]; then
        grub-mkfont -s 16 -o "$ISO/boot/grub/fonts/unicode.pf2" "$font"
    else
        cp /usr/share/grub/unicode.pf2 "$ISO/boot/grub/fonts/unicode.pf2"
    fi
    if [[ -d $ROOT/usr/share/grub/themes/veyra ]]; then
        cp -a "$ROOT/usr/share/grub/themes/veyra" "$ISO/boot/grub/themes/"
    fi
    write_grub_cfg "$ISO" "$ISO_LABEL" "$LIVE_CMDLINE" "${KERNELS[@]}"

    printf '%s %s (%s)\nbuilt %s\n' "$VEYRA_NAME" "$VEYRA_VERSION" "$VEYRA_CHANNEL" \
        "$(date -u -d "@$SOURCE_DATE_EPOCH" +%FT%TZ)" > "$ISO/veyra/version"

    msg2 "creating squashfs (this takes a while)"
    # Clean volatile state before imaging
    rm -rf "$ROOT"/var/cache/pacman/pkg/* "$ROOT"/var/log/*.log "$ROOT"/tmp/* "$ROOT"/var/tmp/*
    rm -rf "$ROOT"/etc/pacman.d/gnupg
    : > "$ROOT/etc/machine-id"; rm -f "$ROOT/var/lib/dbus/machine-id"
    mksquashfs "$ROOT" "$ISO/veyra/x86_64/rootfs.sfs" "${SQUASHFS_OPTS[@]}" \
        -wildcards -e 'boot/initramfs-*-fallback.img'
    ( cd "$ISO/veyra/x86_64" && sha512sum rootfs.sfs > rootfs.sha512 )

    make_iso "$ISO" "$OUT/$ISO_NAME.iso" "$ISO_LABEL"
    write_checksums "$OUT/$ISO_NAME.iso"
    ok "ISO: $OUT/$ISO_NAME.iso ($(du -h "$OUT/$ISO_NAME.iso" | cut -f1))"
}

# ---------------------------------------------------------------------------
for CUR_STAGE in "${STAGES[@]}"; do
    should_run "$CUR_STAGE" || continue
    "stage_$CUR_STAGE"
done
((KEEP_WORK)) || { msg "Cleaning work directory"; rm -rf --one-file-system "$ROOT" "$ISO"; }
ok "build finished"
