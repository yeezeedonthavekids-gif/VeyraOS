# Testing

Five layers, from seconds to tens of minutes. Each says exactly what it proves.

| Command | Proves | Does not prove |
|---|---|---|
| `make test-static` | Versions consistent across profile/PKGBUILDs/installer/apps; desktop entries valid (`desktop-file-validate`); JSON valid; Python compiles; global themes complete; every Aurorae button state exists; no systemd units/`systemctl` shipped; every Calamares module in the sequence has a config; **ShellCheck clean** (all bash/sh scripts; OpenRC scripts and the ash hook as POSIX sh) | Runtime behaviour |
| `make test-unit` (pytest) | Steam VDF parser/writer round-trip and edits; Software Center/Updates parsers (pacman, flatpak, checkupdates, RSS); **privileged helper rejects injection** and protects core packages (dry-run); firewall rule discovery; GPU classification with real PCI IDs (RTX 5060 → open, GTX 1080 → legacy); friendly-names generation and user-file protection; manifest resolver (alternatives/optional/missing); all app windows construct and paint | Real pacman/flatpak/polkit interaction |
| `make test-packaging` | All VeyraOS PKGBUILDs build with **makepkg** in the official Artix base-devel container and install with **pacman** in the Artix base-openrc container; every OpenRC script is accepted by `openrc-run describe`; sudoers parses (`visudo -c`); os-release hook works; text runlevel is generated; no world-writable files | Dependency resolution against the repos (packages are installed with `-dd` offline) |
| `make test-boot` | An ISO produced by the **real** `build/lib/iso.sh` (GRUB menu + theme, `grub-mkrescue` hybrid image) with the **real** `veyralive` hook boots in QEMU: **BIOS from CD, UEFI from a USB-style disk, copy-to-RAM, integrity verification, text-mode runlevel**. Inside the booted Artix OpenRC system it checks: overlay root, `/run/veyra` mounts, writable root, VeyraOS os-release, machine-id, **zram swap active**, **firewall active with policy drop and per-service toggling**, sysctl applied, no crashed services | The real kernel/initramfs (uses Ubuntu's kernel and a mkinitcpio-compatible init because Artix kernel packages could not be downloaded); the desktop session |
| `make test-desktop` | The built packages, extracted into a **Plasma 6.6** system, produce the intended desktop for a **brand-new user**: layout script, colours, icons, fonts, title bars, Dolphin places, Start menu favourites with friendly names; switching to the dark global theme (+ title-bar sync) works. Screenshots in `docs/screenshots/` | Artix-specific packaging of Plasma; GPU effects (blur/shadows: software rendering) |
| `tests/boot/check-real-iso.sh` (CI) | The real ISO boots with its own kernel and mkinitcpio initramfs to the display manager; screenshot of the live desktop | Hardware-specific behaviour |
| Calamares (manual, see DEVLOG) | The installer configuration loads in **Calamares 3.3.14** with all modules; branding and welcome page render | An actual disk installation |

## Bugs these tests found (all fixed)

* Live boot from USB would have failed: on a hybrid ISO the label is only
  reported on a partition while the filesystem is on the whole disk
  (boot test, UEFI/disk case).
* `veyra-zram` dependency cycle with OpenRC's `swap`/`localmount`
  (boot test).
* GRUB menu unusable under legacy BIOS with `gfxmode=auto` (boot test).
* GRUB config generator expanded a GRUB variable in bash (boot test).
* New users got Breeze colours instead of VeyraOS colours (desktop test).
* Window decoration missing on Plasma ≥ 6.3 because Aurorae became a
  separate package (desktop test).
* Global theme switch did not change the title bars (desktop test).
* Calamares: GeoIP style rejected; missing `localecfg` config (Calamares/static).
* `veyra-apps` check() wrote into the read-only source tree (packaging test).

## Still to test on real hardware (release blockers for 2026.11 final)

1. Full ISO build from the mirrors (CI workflow ready).
2. Install in a VM: erase disk (btrfs, ext4), encrypted, alongside a
   Windows installation, manual partitioning.
3. Reference PC (Ryzen 7 8700F, RTX 5060, MSI PRO B840-VC WIFI): NVIDIA
   driver, Wayland session, suspend/resume, VRR, Steam + Proton games,
   controllers, Wi-Fi/Bluetooth.
4. Benchmarks with `tools/bench-idle.sh`.
