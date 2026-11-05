# VeyraOS 2026.11 "Aurora" — Release Candidate 1

The first release candidate of VeyraOS: a Windows-familiar desktop on Artix
Linux (OpenRC, no systemd) and KDE Plasma 6, made for gaming on NVIDIA.

## Highlights

* **Windows 11-style desktop** — centered Start button and taskbar, system
  tray with time and date, Windows-style title bars (light/dark), snapping,
  Task View, Alt+Tab grid, Windows keyboard shortcuts, familiar app names.
* **VeyraOS apps** — *Control* (drivers, gaming, updates, firewall, restore
  points, services, theme), *Software* (official repositories + Flathub, with
  a curated catalogue), *Updates* (with Arch/Artix news), *Welcome*,
  *Gaming Mode* (Meta+G).
* **NVIDIA ready** — proprietary driver with open kernel modules (RTX 50
  series supported), DKMS for both kernels, Wayland KMS, OpenRC suspend hooks,
  automatic setup/removal by the installer.
* **Gaming** — Steam with Proton/Proton Experimental, Lutris, Gamescope,
  MangoHud, GameMode, Wine, ntsync, tearing support for low latency.
* **Installer** — Calamares: alongside Windows, replace, erase, manual; btrfs
  with automatic restore points before updates; optional encryption; nothing
  is erased without confirmation.
* **Secure and private** — firewall on by default, signed official packages
  only, no telemetry, admin actions behind polkit, optional automatic updates.
* **Original identity** — logo, "Aurora" wallpapers (light/dark), boot
  animation, GRUB theme, installer slideshow and a synthesized sound theme.

## Before you install

Read [KNOWN-ISSUES.md](KNOWN-ISSUES.md). In particular: some online games
with anti-cheat (e.g. Fortnite) do **not** run on Linux; Secure Boot must be
disabled for the USB stick; this RC has been tested in virtual machines and
containers, not yet on the reference hardware.

## Verify your download

```
sha256sum -c veyraos-2026.11-rc1-x86_64.iso.sha256
```

## Components (resolved at build time; exact versions in `*.packages.txt`)

Artix Linux (OpenRC 0.6x), Linux + Linux LTS, KDE Plasma 6, Mesa, NVIDIA
open modules (DKMS), PipeWire, NetworkManager, Calamares 3.3, Steam, Lutris,
Gamescope, MangoHud, GameMode, Firefox.
