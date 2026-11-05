# VeyraOS development log

## 2026-11-05 — overnight build session (RC1)

### Environment discovered at the start

* Sandbox: Ubuntu 24.04 container, 4 CPUs, 15 GB RAM, Docker available, **no
  KVM**, no GPU.
* Network: **Artix and Arch mirrors blocked** (HTTP 403 at the proxy);
  Docker Hub, GitHub, PyPI and the Ubuntu archive reachable.
* GitHub: the repository was empty; **pushing was refused (HTTP 403 — the
  Claude GitHub App has read-only access to the repository)**. Both `git push`
  and the GitHub API returned 403. All work was committed locally on branch
  `claude/veyraos-build-8mr4li`; the push must be retried once write access
  is granted (see "Where I stopped").

Consequence: the full ISO cannot be built here (no Artix packages), and the
original plan B — building it on GitHub Actions — also needs push access.
Strategy chosen: write the complete, reproducible build, and verify every
component with the real tools that *are* reachable:

| Need | Substitute used for testing |
|---|---|
| Artix userland + OpenRC | official `artixlinux/artixlinux:base-openrc` and `base-devel` Docker images |
| Artix kernel | Ubuntu's kernel (only for the boot-mechanism test) |
| Plasma 6 | Ubuntu 26.04's Plasma 6.6 packages in a container |
| Calamares | Ubuntu 26.04's Calamares 3.3.14 (same version as the fallback PKGBUILD) |
| mkinitcpio semantics | read from the real mkinitcpio source on GitHub (`init`, `init_functions`, `install/base`) |
| Calamares module schemas | read from the real Calamares 3.3 sources on GitHub |

### Decisions

* **Own live hook instead of artools/archiso hooks** — ~120 lines, fully
  testable, no dependency on profile formats that could not be inspected.
* **Own ISO builder instead of `buildiso`** — `artools-iso` profile format
  could not be verified offline; `pacman --root` + mkinitcpio + mksquashfs +
  `grub-mkrescue` is transparent and uses only standard tools.
* **Package manifests with alternatives/optional entries** — Artix package
  names could not be checked against live repositories; the resolver turns any
  wrong guess into one precise error list instead of a half-built image.
* **NVIDIA open modules via DKMS** — required for the RTX 5060 (Blackwell);
  DKMS covers both kernels.
* **btrfs + Timeshift** as the "System Restore" equivalent; pacman hook takes
  a restore point before updates (rate-limited, never blocks by default).
* **One privileged helper** with validated actions instead of running GUIs as
  root.
* **Calamares** over a custom installer: kpmcore's partitioning (alongside
  Windows, LUKS) is far more mature than anything writable in one night.
* **No unverifiable third-party code**: KDE-Rounded-Corners was dropped
  because its release could not be pinned and verified from this session.

### Problems found by testing, and fixes

1. **Hybrid ISO on USB would not boot** — QEMU UEFI test from a virtio disk:
   blkid reports the ISO label only on a partition (HFS+/EFI entries of the
   hybrid image); mounting it fails ("Invalid argument"); the iso9660 lives on
   the whole disk. Fix: the hook tries the parent disk of every labelled
   partition first, then the partitions, and accepts only a candidate that
   contains the root image.
2. **zram never started** — `need localmount` + `before swap` formed a cycle
   with OpenRC's own ordering. Removed the localmount dependency.
3. **Legacy-BIOS GRUB menu hung** — `gfxmode=auto` selects the largest VBE
   mode; drawing the themed menu at that size never finished in QEMU. Now
   `auto` on UEFI only; BIOS prefers 1920x1080/1280x720/1024x768.
4. **GRUB config generator bug** — an unquoted heredoc expanded GRUB's
   `$grub_platform` in bash.
5. **Test-harness artefacts (not product bugs), documented for future
   readers:** Ubuntu's static busybox prefers its own applets (so `switch_root`
   did not move `/run`), Ubuntu's kernel/kmod pair needs decompressed modules,
   zram is in `linux-modules-extra`. The harness now mirrors mkinitcpio
   exactly (util-linux `switch_root`, `mount`, `blkid`).
6. **New users got Breeze colours** (Plasma render test) — Plasma does not
   load a colour scheme from its name; `/etc/xdg/kdeglobals` now ships the
   full colour groups (`tools/gen-kdeglobals.py`).
7. **No VeyraOS title bar on Plasma 6.6** — Aurorae was split out of KWin in
   Plasma 6.3; added `aurorae|kwin` to the manifest.
8. **Dark theme kept the light title bar** — Plasma's global-theme switch
   does not apply Aurorae decorations; added `theme-sync` (login + Control).
9. **Calamares**: GeoIP style `none` rejected; `localecfg` lacked a config;
   `GRUB_DEFAULT=saved` dropped (GRUB cannot save its environment on btrfs).
10. **Packaging**: `veyra-apps` `check()` wrote bytecode into the read-only
    source tree (now `PYTHONPYCACHEPREFIX`).
11. **Content error caught in review**: Apex Legends was listed as working
    with anti-cheat; EA blocked Linux in 2024. Corrected.
12. **Plymouth password prompt** showed the spinner inside the passphrase box
    (the per-frame refresh re-showed it) — found by rendering the theme with
    Plymouth's X11 renderer; fixed with a spinner-visibility flag.
13. **Build robustness** (review): the image verification now checks the
    NVIDIA module for *each* kernel, and the live configuration removes any
    pacman keyring created by package scripts (no shared private key on the
    ISO), instead of failing the build late.

### Test status at the end of the session

* `make test`: static checks OK, ShellCheck clean (36 scripts), 41 unit/GUI
  tests pass.
* `make test-packaging`: all 8 packages build (makepkg) and install (pacman)
  in Artix containers; OpenRC scripts accepted by `openrc-run`.
* `make test-boot`: **5/5 boot cases pass** on the final code (BIOS CD,
  UEFI disk, copy-to-RAM, verify, text mode; 10–15 in-system checks each).
* Installer post-install script verified on an Artix root (hostname/keymap
  for OpenRC, Plasma keyboard layout, live settings removed, keyring, driver
  decision, home permissions).
* `make test-desktop`: Plasma 6.6 renders the VeyraOS desktop for a new user,
  light and dark (screenshots in `docs/screenshots/`).
* Calamares 3.3.14 loads the full VeyraOS configuration without errors.
* Plymouth theme runs in real Plymouth (splash, message, LUKS prompt) and the
  KSplash QML renders (screenshots in `docs/screenshots/`).
* `build/build-iso.sh --stage packages` builds all 8 packages and the local
  repository inside the Artix container (stops at the first mirror access, as
  expected offline); `build/chroot-configure.sh` configures an Artix OpenRC
  root correctly (live user, runlevels, text runlevel, autologin, identity).

### Where I stopped / what is unresolved

1. **Push**: everything is committed locally; `git push -u origin
   claude/veyraos-build-8mr4li` fails with 403 until the Claude GitHub App
   gets write access to `yeezeedonthavekids-gif/veyraos`
   (https://claude.ai/connect-github). Nothing else is needed — the branch is
   complete and self-contained. Because the session container is temporary,
   the full history was also delivered as a git bundle
   (`veyraos-2026.11-rc1.bundle`; restore with
   `git clone veyraos-2026.11-rc1.bundle VeyraOS`, then
   `git push -u origin claude/veyraos-build-8mr4li`).
2. **First real ISO build**: run `make iso` (or the *Build ISO* workflow).
   Expect possibly a few package-name corrections in `packages/*.list`
   (the resolver lists them all at once).
3. **Install tests in a VM** and **hardware tests on the reference PC**
   (TESTING.md, "Still to test").
4. **Benchmarks** with `tools/bench-idle.sh` once installed on real hardware.
5. Nice-to-have: a signed VeyraOS package repository so the veyra-* packages
   update with the system; AppArmor as an option.
