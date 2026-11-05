#!/bin/bash
# Runs INSIDE the live root filesystem (chroot) during the ISO build.
# Turns a freshly installed package set into the VeyraOS live system.
# Everything that should also apply to installed systems lives in the
# veyra-* packages instead; this script only does live-medium specifics.
set -Eeuo pipefail
# shellcheck source=/dev/null
source /root/veyra-configure.env

log() { printf '  [configure] %s\n' "$*"; }

# ---- Locale, time, keyboard, hostname ------------------------------------
log "locale / timezone / hostname"
sed -i "s/^#\(${LIVE_LOCALE//./\\.} \)/\1/" /etc/locale.gen
grep -q "^${LIVE_LOCALE} " /etc/locale.gen || echo "${LIVE_LOCALE} UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG=${LIVE_LOCALE}" > /etc/locale.conf
ln -sf "/usr/share/zoneinfo/${LIVE_TIMEZONE}" /etc/localtime
sed -i "s/^keymap=.*/keymap=\"${LIVE_KEYMAP}\"/" /etc/conf.d/keymaps
echo "${LIVE_HOSTNAME}" > /etc/hostname
echo "hostname=\"${LIVE_HOSTNAME}\"" > /etc/conf.d/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   ${LIVE_HOSTNAME}.localdomain ${LIVE_HOSTNAME}
EOF

# ---- Package manager -------------------------------------------------------
log "pacman configuration"
install -m644 /usr/share/veyra/pacman.conf /etc/pacman.conf
/usr/lib/veyra/ensure-arch-mirror
/usr/lib/veyra/write-os-release

# ---- Live user -------------------------------------------------------------
log "live user '${LIVE_USER}'"
if ! id "$LIVE_USER" >/dev/null 2>&1; then
    useradd -m -G wheel -s /bin/bash -c "VeyraOS Live" "$LIVE_USER"
fi
passwd -d "$LIVE_USER" >/dev/null          # empty password on the live medium only
passwd -l root >/dev/null                  # root stays locked
for g in gamemode; do getent group "$g" >/dev/null && gpasswd -a "$LIVE_USER" "$g" >/dev/null; done
install -Dm440 /dev/stdin /etc/sudoers.d/10-veyra-live <<EOF
# Live medium only — removed by the installer.
${LIVE_USER} ALL=(ALL:ALL) NOPASSWD: ALL
EOF
sudo -u "$LIVE_USER" LANG="$LIVE_LOCALE" xdg-user-dirs-update --force || true
# Installer shortcut on the live desktop
DESK=$(sudo -u "$LIVE_USER" xdg-user-dir DESKTOP 2>/dev/null || echo "/home/$LIVE_USER/Desktop")
install -d -o "$LIVE_USER" -g "$LIVE_USER" "$DESK"
if [[ -f /usr/share/applications/veyra-install.desktop ]]; then
    install -m755 -o "$LIVE_USER" -g "$LIVE_USER" /usr/share/applications/veyra-install.desktop "$DESK/"
fi

# Live session: no screen lock / auto-suspend (the live user has no password)
install -d -o "$LIVE_USER" -g "$LIVE_USER" "/home/$LIVE_USER/.config"
for f in kscreenlockerrc powermanagementprofilesrc; do
    install -m644 -o "$LIVE_USER" -g "$LIVE_USER" "/usr/share/veyra/live/$f" "/home/$LIVE_USER/.config/$f"
done

# ---- Display manager: autologin into Plasma on the live medium --------------
log "display manager"
install -Dm644 /dev/stdin /etc/sddm.conf.d/20-veyra-live.conf <<EOF
# Live medium only — removed by the installer.
[Autologin]
User=${LIVE_USER}
Session=plasma
Relogin=false
EOF

# ---- Services (OpenRC) -----------------------------------------------------
log "services"
enable() { # enable <runlevel> <service>
    if [[ -e /etc/init.d/$2 ]]; then rc-update add "$2" "$1" >/dev/null; log "  + $2 ($1)";
    else log "  ! service $2 not present, skipped"; fi
}
enable boot    veyra-zram
enable default dbus
enable boot    elogind
enable default NetworkManager
enable default veyra-firewall
enable default bluetoothd
enable default cronie
for s in chronyd openntpd ntpd; do [[ -e /etc/init.d/$s ]] && { enable default "$s"; break; }; done
enable default veyra-live
enable default veyra-firstboot

# Display manager: Artix ships either a per-DM service or the generic one.
if [[ -e /etc/init.d/sddm ]]; then
    enable default sddm
elif [[ -e /etc/init.d/displaymanager ]]; then
    sed -i 's/^DISPLAYMANAGER=.*/DISPLAYMANAGER="sddm"/' /etc/conf.d/displaymanager 2>/dev/null \
        || echo 'DISPLAYMANAGER="sddm"' > /etc/conf.d/displaymanager
    enable default displaymanager
else
    echo "ERROR: no display manager service found" >&2; exit 1
fi
# Console logins are not needed beyond tty1-2 (fewer idle processes).
for t in 3 4 5 6; do rc-update del "agetty.tty$t" default >/dev/null 2>&1 || true; done

# "text" runlevel: everything in default except the display manager.
# Used by the "Text mode rescue console" boot entry (softlevel=text).
/usr/lib/veyra/make-text-runlevel

# ---- Live initramfs config sanity ------------------------------------------
[[ -f /etc/veyra/mkinitcpio-live.conf ]] || { echo "ERROR: veyra-live not installed" >&2; exit 1; }

# ---- Desktop database / caches ---------------------------------------------
log "caches"
update-desktop-database -q 2>/dev/null || true
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
fc-cache -s >/dev/null 2>&1 || true
# Flathub is configured on first boot by veyra-firstboot (needs network).

log "done"
