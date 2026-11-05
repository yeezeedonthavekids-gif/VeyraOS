# Building VeyraOS

## Requirements

* x86_64 Linux with **Docker** (or Podman: `CONTAINER_ENGINE=podman`), *or* an Artix Linux host
* **Internet access** to the Artix and Arch mirrors (and github.com for the
  Calamares fallback only)
* ~25 GB free disk space, 8 GB RAM recommended
* Time: 30–90 minutes depending on mirror speed and CPU (DKMS builds the NVIDIA
  module for two kernels; squashfs compression is the slowest step)

## Build

```bash
git clone https://github.com/yeezeedonthavekids-gif/veyraos.git
cd veyraos
make iso                    # = build/build-in-docker.sh
```

Output in `out/`:

| File | |
|---|---|
| `veyraos-2026.11-rc1-x86_64.iso` | hybrid ISO (USB/DVD, BIOS/UEFI) |
| `….iso.sha256`, `….iso.sha512` | checksums |
| `….packages.txt` | exact package versions in the image (reproducibility manifest) |
| `….build.log` | full build log |

Native build on Artix: `sudo build/build-iso.sh` (same stages; installs build
tools on the host). Useful options:

```bash
sudo build/build-iso.sh --stage resolve      # re-run from a stage
sudo build/build-iso.sh --keep-work          # keep /var/tmp/veyra-build/{rootfs,iso}
sudo build/build-iso.sh --work /big/disk --out /somewhere
```

The package cache is a Docker volume (`veyra-pkgcache`), so rebuilds only
download what changed.

## On GitHub Actions

`.github/workflows/build-iso.yml` builds the ISO on a hosted runner, boots it
in QEMU with KVM (`tests/boot/check-real-iso.sh`), uploads logs/manifest/
screenshot, and on a `v*` tag publishes a pre-release. GitHub limits release
assets to 2 GiB, so the ISO is published in parts; reassemble with:

```bash
cat veyraos-*.iso.part* > veyraos.iso && sha256sum -c veyraos-*.iso.sha256
```

## Reproducibility

* All inputs are in git: package manifests, PKGBUILDs, configuration, and the
  scripts that generated every piece of artwork (`make assets` regenerates
  them byte-for-byte except for PNG/JPEG encoder differences).
* `SOURCE_DATE_EPOCH` (default: last commit time) fixes ISO timestamps.
* Artix and Arch are rolling releases, so two builds on different days get
  different package versions. Each ISO ships its exact versions in
  `*.packages.txt`. To rebuild an identical package set, point the
  `[extra]`/`[multilib]` servers in `build/pacman.conf.in` to the Arch Linux
  Archive for that date (`https://archive.archlinux.org/repos/YYYY/MM/DD/$repo/os/$arch`);
  Artix does not operate a dated archive, which is the main limit on
  bit-for-bit reproduction.

## Package manifests

`packages/*.list`, one entry per line:

```
plasma-desktop            required
sddm-openrc|displaymanager-openrc   required; first available wins
?plymouth                 optional; skipped with a warning
```

The resolver prints every missing required package before failing, so
repository renames show up as one clear error list.

## Customizing

| Change | Where |
|---|---|
| Name, version, kernels, live user, squashfs compression | `build/profile.conf` |
| Add/remove software | `packages/*.list` |
| Desktop defaults | `src/desktop/etc/xdg/*`, then `tools/gen-kdeglobals.py` if colours changed |
| Panel layout | `src/desktop/usr/share/plasma/look-and-feel/*/contents/layouts/` |
| Artwork | `tools/gen-*.py`, then `make assets` |
| Installer behaviour | `src/installer/etc/calamares/` |
| Services enabled | `build/chroot-configure.sh` (live) and `src/installer/.../services-openrc.conf` (installed) |

Bump the version in `build/profile.conf`, `src/system/usr/share/veyra/release`,
the PKGBUILDs, `branding.desc` and `common/ui.py` together —
`tests/static/check-static.sh` fails if they disagree.

## Troubleshooting the build

| Symptom | Fix |
|---|---|
| `MISSING: foo (desktop.list)` | Package renamed/removed upstream: add an alternative (`foo|newname`) or mark optional (`?foo`) |
| `calamares not found in repositories — building …` | Expected if Artix stops shipping it; needs github.com access |
| `NVIDIA kernel module was not built` | DKMS failed (new kernel not yet supported by the driver). Check the build log for `dkms`; wait for the driver update or pin the kernel |
| `POLICY VIOLATION: package 'systemd' is installed` | Some package pulled systemd in; find it with `pacman --root out/... -Qi systemd` (Required By) and replace it |
| Disk full | Use `--work` on a bigger disk; `docker volume rm veyra-pkgcache` frees the cache |
