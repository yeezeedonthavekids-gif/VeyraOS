# shellcheck shell=bash
# Common helpers for the VeyraOS build. Sourced, not executed.

if [[ -t 2 ]]; then
    _c_info=$'\e[1;36m' _c_warn=$'\e[1;33m' _c_err=$'\e[1;31m' _c_ok=$'\e[1;32m' _c_off=$'\e[0m'
else
    _c_info='' _c_warn='' _c_err='' _c_ok='' _c_off=''
fi

msg()   { printf '%s==>%s %s\n' "$_c_info" "$_c_off" "$*" >&2; }
msg2()  { printf '  %s->%s %s\n' "$_c_info" "$_c_off" "$*" >&2; }
ok()    { printf '%s==> OK:%s %s\n' "$_c_ok" "$_c_off" "$*" >&2; }
warn()  { printf '%s==> WARNING:%s %s\n' "$_c_warn" "$_c_off" "$*" >&2; }
die()   { printf '%s==> ERROR:%s %s\n' "$_c_err" "$_c_off" "$*" >&2; exit 1; }

require_cmd() {
    local c missing=()
    for c in "$@"; do command -v "$c" >/dev/null 2>&1 || missing+=("$c"); done
    ((${#missing[@]} == 0)) || die "missing required commands: ${missing[*]}"
}

# ---- chroot management (equivalent of artix-chroot / arch-chroot) ----------
# Track mounts so they can be torn down in reverse order on exit.
declare -ga _CHROOT_MOUNTS=()

_chroot_mount() {
    # _chroot_mount <target> <mount args...>
    local target=$1; shift
    mount "$@" "$target" || die "mount failed: $* $target"
    _CHROOT_MOUNTS=("$target" "${_CHROOT_MOUNTS[@]}")
}

chroot_setup() {
    local root=$1
    [[ -d $root ]] || die "chroot_setup: $root does not exist"
    mkdir -p "$root"/{proc,sys,dev,run,tmp,etc}
    mountpoint -q "$root/proc" || _chroot_mount "$root/proc" -t proc proc -o nosuid,noexec,nodev
    mountpoint -q "$root/sys"  || _chroot_mount "$root/sys"  -t sysfs sys -o nosuid,noexec,nodev,ro
    mountpoint -q "$root/dev"  || _chroot_mount "$root/dev"  -t devtmpfs udev -o mode=0755,nosuid
    mkdir -p "$root/dev/pts" "$root/dev/shm"
    mountpoint -q "$root/dev/pts" || _chroot_mount "$root/dev/pts" -t devpts devpts -o mode=0620,gid=5,nosuid,noexec
    mountpoint -q "$root/dev/shm" || _chroot_mount "$root/dev/shm" -t tmpfs shm -o mode=1777,nosuid,nodev
    mountpoint -q "$root/run"  || _chroot_mount "$root/run"  -t tmpfs run -o nosuid,nodev,mode=0755
    mountpoint -q "$root/tmp"  || _chroot_mount "$root/tmp"  -t tmpfs tmp -o mode=1777,strictatime,nodev,nosuid
    # DNS for package hooks that need the network (e.g. flatpak remote-add)
    if [[ -e /etc/resolv.conf ]]; then
        cp -L /etc/resolv.conf "$root/etc/resolv.conf" 2>/dev/null || true
    fi
}

chroot_teardown() {
    local m
    for m in "${_CHROOT_MOUNTS[@]}"; do
        umount -l "$m" 2>/dev/null || true
    done
    _CHROOT_MOUNTS=()
}

in_chroot() {
    # in_chroot <root> <command...>
    local root=$1; shift
    SHELL=/bin/bash LANG=C.UTF-8 chroot "$root" "$@"
}

# Read a manifest file: strip comments/blank lines; print one entry per line.
read_manifest() {
    sed -e 's/#.*$//' -e 's/[[:space:]]*$//' -e 's/^[[:space:]]*//' "$1" | grep -v '^$' || true
}
