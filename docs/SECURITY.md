# Security and privacy

## Defaults

| Area | VeyraOS default |
|---|---|
| Firewall | nftables, **inbound denied** except replies, loopback, essential ICMP/ICMPv6 and DHCPv6; outbound allowed. Loaded *before* networking starts (`before net`) and validated (`nft -c`) before loading |
| Packages | signatures **required** (`SigLevel = Required`); official Artix + Arch repositories only; no third-party repos, PPAs or `curl | sh` |
| Flatpak | Flathub only (added on first boot); sandboxed apps; permissions manageable with Flatseal |
| Admin rights | users in `wheel`; root is locked; every admin action asks for your password (sudo/polkit, cached 5–10 min) |
| Telemetry | **none**. KDE feedback off; Firefox telemetry, studies, Pocket and sponsored content off by enterprise policy (`/etc/firefox/policies/policies.json`) |
| Network services | none listening by default (no SSH server, printing service off until enabled) |
| Home folders | `0700` — other local users cannot read your files |
| Kernel | `dmesg`/kernel pointer restriction, unprivileged BPF off, BPF JIT hardening, ICMP redirect protection, reverse-path filtering, protected FIFOs/regular files, SYN cookies; SysRq limited to sync/remount/reboot |
| Updates | update notifications by default; optional automatic download or install (*VeyraOS Control → Updates*); restore point before each update |

## Firewall

```bash
veyra-firewall status
veyra-firewall list                          # optional services and whether they are allowed
sudo veyra-firewall enable-service steam-remoteplay
sudo veyra-firewall disable-service steam-remoteplay
sudo veyra-firewall off|on
```

Optional rules (`/etc/veyra/firewall/services/`): Steam Remote Play (LAN),
KDE Connect (LAN), mDNS (printer discovery), SSH (rate limited), Windows
share browsing. Add your own `.nft` file there with a `# description` first
line. The rule set is verified in the QEMU boot test.

## The privileged helper

GUI apps never run as root. The single entry point,
`/usr/lib/veyra/veyra-helper`, is started through `pkexec`
(`org.veyraos.helper`, `auth_admin_keep`) and:

* accepts only fixed actions (`pkg-install`, `pkg-remove`, `system-update`,
  `firewall`, `firewall-service`, `service`, `nvidia-setup`, `auto-update`,
  `snapshot`, `set-theme-default`);
* validates every argument (package names must match Arch naming rules;
  services come from a whitelist; firewall services must exist);
* passes arguments after `--` so they can never become options;
* refuses to remove core packages (kernel, OpenRC, pacman, glibc, sudo, …);
* runs with a fixed `PATH` and no shell evaluation of input.

Unit tests (`tests/unit/test_helper.py`) cover injection attempts such as
`--root=/tmp`, `-Syu`, `$(id)`, `foo;rm` and path traversal.

Gaming Mode has its own, narrower helper (`gaming-mode-helper on|off|status`)
that the user at the computer may run **without** a password (polkit
`allow_active=yes`); it only changes CPU power preference and pauses services
listed in the root-owned `/etc/veyra/gaming-mode.conf`.

## Automatic updates — honest notes

Artix/Arch are rolling releases: there is no separate "security updates
only" channel; security fixes arrive with regular updates (usually within
days of disclosure). Options:

* **Notify** (default) — a notification when updates exist.
* **Download** — updates are downloaded in the background with
  `checkupdates -d` (temporary database, so a partial upgrade is impossible);
  installing later is fast.
* **Install** — `pacman -Syu` every 6 hours via cron (skipped on battery,
  during Gaming Mode and while pacman is busy). Convenient but occasionally an
  update needs a manual step announced on the Arch/Artix news; the Updates app
  shows recent news. A restore point is taken first if Timeshift is set up.

## Secure Boot

The ISO's GRUB is not signed by Microsoft, so the live USB requires Secure
Boot **off**. After installation you can enable Secure Boot with **your own
keys** using `sbctl` (on the ISO):

```bash
sudo sbctl status                       # Secure Boot must be in "Setup Mode":
                                        # firmware → Secure Boot → Delete/Reset to Setup Mode
sudo sbctl create-keys
sudo sbctl enroll-keys -m               # -m keeps Microsoft's keys (needed for
                                        # Windows dual boot and GPU option ROMs!)
sudo grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=VeyraOS \
     --modules="tpm" --disable-shim-lock
sudo sbctl sign -s /boot/efi/EFI/VeyraOS/grubx64.efi
sudo sbctl sign -s /boot/efi/EFI/BOOT/BOOTX64.EFI
sudo sbctl sign -s /boot/vmlinuz-linux
sudo sbctl sign -s /boot/vmlinuz-linux-lts
sudo sbctl verify
```

Then enable Secure Boot in the firmware. `sbctl` installs a pacman hook that
re-signs kernels on update. **NVIDIA DKMS modules must also be signed**
when Secure Boot enforces module signatures (lockdown); the Arch kernel does
not enforce module signatures by default, so the modules load. Always keep
the `-m` (Microsoft keys) option on PCs with a discrete GPU — removing them
can make the GPU's firmware unusable at boot.

This is the closest practical equivalent to Windows' Secure Boot: shim with a
Microsoft-signed VeyraOS key would require an official signing agreement that
an independent project does not have.

## Known limitations

* No mandatory access control by default. AppArmor is built into the Arch
  kernel but not active; enabling it needs the `lsm=` kernel parameter, the
  `apparmor` package and profiles — planned as an option, not default, to
  avoid breaking games and Proton.
* Steam and NVIDIA's driver are proprietary software (by request).
* Flathub apps are built by their publishers/community, not reviewed by
  VeyraOS; prefer repository packages where available (the Software Center
  labels the source of every app).
