# Known issues and limitations — 2026.11 RC1

## Not yet verified (development environment limits)

| Item | Why | How it will be closed |
|---|---|---|
| Complete ISO not built yet | Development sandbox had no access to the Artix/Arch mirrors | `make iso` on any machine with internet, or the `Build ISO` GitHub workflow |
| Package names in `packages/*.list` | Checked from knowledge, not against live repo databases. The resolver fails with a full list of anything missing and supports alternatives (`a\|b`) | First `make iso` run; fix names reported as MISSING |
| Real disk installation | Calamares config validated by loading it in Calamares 3.3.14, but no install was performed | VM install matrix (TESTING.md) |
| NVIDIA RTX 5060, gaming, Wi-Fi/BT on the reference PC | No GPU/hardware available | Hardware test on the reference PC |
| Performance numbers | Same | `tools/bench-idle.sh` |

## Limitations by design

* **Online games with Linux-blocking anti-cheat do not work** (Fortnite,
  Valorant, Call of Duty, Battlefield 6, Apex Legends, Rainbow Six Siege,
  …). See [GAMING.md](GAMING.md#anti-cheat-compatibility--please-read).
  Windows dual boot is the workaround.
* **Secure Boot** must be off for the USB stick; it can be enabled after
  installation with your own keys (sbctl). No Microsoft-signed shim.
* **Window bottom corners are square** (top corners are rounded by the
  VeyraOS title bar). Fully rounded corners need a third-party KWin effect
  (`kwin-effect-rounded-corners-git` in the AUR), not shipped because it must
  be rebuilt for every KWin update.
* **Software Center** shows Flathub and the curated catalogue nicely, but a
  plain repository search shows package names (no screenshots/ratings).
* Title bars follow Plasma's *automatic* light/dark switching only at the
  next login (or via VeyraOS Control → Appearance) — Plasma's global theme
  switch does not change Aurorae decorations itself.
* VeyraOS packages are installed from the ISO; there is **no VeyraOS package
  repository yet**, so VeyraOS' own packages are not updated by `pacman -Syu`
  (Artix/Arch packages are). Planned: a signed repository published from
  GitHub releases.
* Firefox hardware video decoding is off by default (it requires disabling a
  Firefox sandbox; see NVIDIA.md).
* Hibernation needs a swap partition/file chosen in the installer (zram cannot
  hold a hibernation image).

## Things to watch in the first real build

* `sddm-openrc` vs `displaymanager-openrc` (both handled).
* `chrony-openrc` / `openntpd-openrc` / `ntp-openrc` (first available is used).
* `calamares` availability in Artix repos (fallback PKGBUILD pinned to
  3.3.14 with checksum).
* `aurorae` package name on Artix (manifest entry `aurorae|kwin`).
* NVIDIA DKMS against the newest kernel (the build fails loudly if the module
  is missing for any kernel).
