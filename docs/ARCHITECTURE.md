# VeyraOS architecture

VeyraOS is a **distribution layer**, not a fork: it takes Artix Linux (Arch
Linux with OpenRC instead of systemd) and KDE Plasma 6 from their official
repositories and adds a small set of VeyraOS packages that configure and brand
them. Nothing upstream is patched or rebuilt (the only exception is a fallback
Calamares build, used only if the repositories stop carrying it).

```
┌──────────────────────────── VeyraOS ISO ────────────────────────────┐
│ GRUB (BIOS + UEFI, VeyraOS theme)                                   │
│   └─ kernel + mkinitcpio initramfs with the "veyralive" hook        │
│        └─ squashfs root image + tmpfs overlay  (live system)        │
│             ├─ Artix base + OpenRC + elogind + udev                 │
│             ├─ KDE Plasma 6 (Wayland default)                       │
│             ├─ NVIDIA open modules (DKMS), Mesa/Vulkan              │
│             ├─ Steam, Lutris, Gamescope, MangoHud, GameMode, Wine   │
│             └─ VeyraOS packages:                                    │
│                  veyra-system  veyra-desktop  veyra-branding        │
│                  veyra-nvidia  veyra-gaming   veyra-apps            │
│                  veyra-live*   veyra-installer*  (*live only)       │
└─────────────────────────────────────────────────────────────────────┘
```

## Why these foundations

| Choice | Reason |
|---|---|
| **Artix (OpenRC)** | Requirement: no systemd, pacman, Arch compatibility. Artix is the maintained Arch-based distribution with OpenRC and its own `*-openrc` service packages. |
| **Arch [extra]/[multilib] enabled** | Through Artix's official `artix-archlinux-support`. Gives the full Arch package set (Steam, Lutris, NVIDIA, KDE apps). Artix repos are listed first, so OpenRC-native builds always win. No third-party repositories. |
| **KDE Plasma 6** | The most configurable mainstream desktop; its layout scripting, global themes and decoration engines allow a faithful Windows 11 layout without patches. Plasma 6 has solid NVIDIA Wayland support (driver ≥ 560 with KMS). |
| **mkinitcpio + own live hook** | The standard Arch/Artix initramfs. The 120-line `veyralive` hook replaces archiso/artools live hooks, so the live boot path is small, ours, and testable in isolation. |
| **Calamares** | The installer used by Artix, Manjaro, EndeavourOS and KDE neon: mature partitioning (kpmcore), "install alongside", LUKS, btrfs, OpenRC service module. |
| **btrfs default** | Instant Timeshift restore points before updates (Windows "System Restore" equivalent), transparent compression. ext4/xfs remain selectable. |
| **PySide6 apps** | Qt6 like Plasma, so the apps follow the system theme exactly; Python keeps them small and auditable. |

## The VeyraOS packages

All are `arch=any` data/script packages built from `src/` by `pkgbuilds/`.
Installed systems receive them like any package; removing one cleanly
reverts its part.

| Package | Contents |
|---|---|
| `veyra-branding` | Logo, icons, wallpapers (light+dark), sound theme, Plymouth theme, GRUB theme |
| `veyra-system` | OpenRC services `veyra-zram`, `veyra-firewall`, `veyra-firstboot`; nftables rules + `veyra-firewall` CLI; sysctl, sudoers, limits, ntsync; pacman hooks (os-release, restore point before updates); PipeWire launcher; Firefox privacy policy; pacman.conf template; GRUB defaults |
| `veyra-desktop` | Plasma global themes (light/dark) with the panel layout script and splash, colour schemes, Aurorae decorations, `/etc/xdg` defaults (kdeglobals, kwinrc, shortcuts, Dolphin, Konsole, Baloo, SDDM), fontconfig, friendly app names, title-bar theme sync |
| `veyra-nvidia` | Module options (KMS/fbdev/VRAM preservation), elogind suspend hook, VA-API environment, `veyra-gpu-detect`, `nvidia-setup` |
| `veyra-gaming` | GameMode config, MangoHud defaults, Gaming Mode privileged helper + polkit policy |
| `veyra-apps` | VeyraOS Control, Software, Updates, Welcome, Gaming Mode CLI, Steam Play setup, `veyra-helper` (the only privileged entry point), auto-update cron job |
| `veyra-live` | `veyralive` initcpio hook, live mkinitcpio config, `veyra-live` service (removed by the installer) |
| `veyra-installer` | Calamares configuration, branding, slideshow, post-install script (removed by the installer) |

## Configuration layering (desktop)

KDE reads configuration in layers: `~/.config` (user) over `/etc/xdg`
(system defaults) over built-in defaults. VeyraOS only ships `/etc/xdg`
defaults, so:

* every new user starts with the VeyraOS look and behaviour;
* anything a user changes is stored in their home and always wins;
* package upgrades never overwrite user choices.

The global themes (`org.veyraos.desktop`, `org.veyraos.desktop.dark`) carry
the same settings for when the user switches themes in System Settings.
`kdeglobals` ships the full colour groups because Plasma does not derive
colours from the scheme name alone (found in the Plasma render test).

## Boot flow (live medium)

1. Firmware → GRUB (`/boot/grub/grub.cfg` generated by `build/lib/iso.sh`).
2. Kernel + initramfs; `veyra.label=<ISO label>` activates the `veyralive` hook.
3. The hook finds every block device with the label — and, for labelled
   partitions, their **parent disk** (a hybrid ISO written to USB exposes the
   filesystem on the whole disk) — mounts the one containing
   `veyra/x86_64/rootfs.sfs`, optionally verifies its SHA-512 or copies it to
   RAM, mounts the squashfs and a tmpfs overlay as `/`.
4. util-linux `switch_root` moves `/run` (with `/run/veyra/*`) into the new
   root; OpenRC keeps it.
5. OpenRC: sysinit → boot (`veyra-zram`, `elogind`, …) → default
   (`NetworkManager`, `veyra-firewall`, `veyra-live`, `sddm`, …).
6. SDDM autologins the `veyra` live user into Plasma (Wayland); Welcome opens.

`softlevel=text` (GRUB → Troubleshooting) boots the `text` runlevel: the
default runlevel minus the display manager.

## Install flow

Calamares: welcome (requirements) → location → keyboard → partitions →
users → summary → **confirmation** → partition, mount, unpack the squashfs,
machine-id, fstab, locale, keyboard, remove live user, create user, display
manager, network, clock, OpenRC services → `post-install` (live settings
removed, OpenRC hostname/keymap, clock=local if Windows found, fresh pacman
keyring, `nvidia-setup`, home permissions) → remove live packages →
mkinitcpio for all kernels → GRUB config + VeyraOS defaults → GRUB install
(+ EFI fallback path) → finish.

## Privilege model

GUI apps never run as root. Administrative actions go through
`/usr/lib/veyra/veyra-helper`, started by `pkexec` (polkit action
`org.veyraos.helper`, admin password, cached briefly — like a UAC prompt).
The helper accepts a fixed list of actions with validated arguments
(see [SECURITY.md](SECURITY.md)). Gaming Mode uses a separate, narrower helper
that the active local user may run without a password.

## Build flow

`build/build-iso.sh` (as root on Artix, or in the official Artix container via
`build/build-in-docker.sh`), stages:

| Stage | Does |
|---|---|
| `host` | build tools, Arch repo support + keyring, unprivileged `veyrabuild` user |
| `packages` | `makepkg` every VeyraOS package into a local `[veyra]` repo |
| `resolve` | resolve `packages/*.list` against the live repo databases (alternatives, optional entries); fails listing every missing package |
| `rootfs` | `pacman --root` install of the resolved set |
| `configure` | `build/chroot-configure.sh` in the chroot (locale, live user, services, autologin) |
| `verify` | policy: no systemd, `openrc-init` is init, NVIDIA module built for every kernel, services enabled, no private keys; writes the package manifest |
| `image` | live initramfs, GRUB menu + theme, squashfs (zstd), SHA-512, hybrid ISO via `grub-mkrescue`, checksums |
