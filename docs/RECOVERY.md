# Recovery

Keep the VeyraOS USB stick: it is also the rescue system.

## Quick reference

| Situation | Go to |
|---|---|
| Black screen / no desktop after an update | [Graphics problems](#graphics-problems) |
| An update broke something | [Restore point (Timeshift)](#roll-back-with-a-restore-point) |
| System does not boot at all / GRUB missing | [Repair from the USB stick](#repair-from-the-usb-stick) |
| Windows missing from the boot menu | [Windows boot entry](#windows-missing-from-the-boot-menu) |
| Forgot password | [Reset a password](#reset-a-password) |
| Frozen system | [Safe reboot](#frozen-system) |
| Firewall blocks something you need | `sudo veyra-firewall list` / `enable-service NAME` or *VeyraOS Control → Security* |

## Boot options in GRUB (installed system)

Hold **Shift** (BIOS) or press **Esc** (UEFI) during start-up if the menu is
hidden. *Advanced options* lists:

* the **LTS kernel** (`linux-lts`) — use it when a new kernel misbehaves;
* **fallback initramfs** entries (all drivers included);
* press **e** on an entry to edit its kernel line for one boot, e.g. add
  `nomodeset` (no GPU driver) or `softlevel=text` (no graphical login), then
  **F10** / Ctrl+X.

`softlevel=text` boots VeyraOS' **text runlevel**: everything except the
display manager. Log in on the console and repair (e.g. update, remove a
broken package), then `sudo reboot`.

## Graphics problems

1. GRUB → **e** → add `nomodeset` → F10. You get a basic (unaccelerated)
   desktop or console.
2. Update and re-run the driver setup:
   ```bash
   sudo pacman -Syu
   sudo /usr/lib/veyra/nvidia-setup auto
   sudo dkms autoinstall
   sudo reboot
   ```
3. Still broken: boot the LTS kernel; or temporarily remove the NVIDIA driver
   (nouveau takes over): `sudo pacman -Rns nvidia-open-dkms nvidia-utils lib32-nvidia-utils nvidia-settings`.

## Roll back with a restore point

If Timeshift is set up (btrfs), a restore point is created automatically
before each update (`/etc/veyra/snapshots.conf`).

* **System still starts:** open **Timeshift**, pick the point from before the
  problem, *Restore*, reboot.
* **System does not start:** boot the USB stick, open a terminal, run
  `sudo timeshift-launcher` (Timeshift is included on the USB stick), choose
  your disk in *Settings → Location*, then restore.

Restoring affects system files only (`@`); your files in `/home` (`@home`)
are untouched.

## Downgrade a single package

```bash
ls /var/cache/pacman/pkg/ | grep firefox          # previous versions are cached
sudo pacman -U /var/cache/pacman/pkg/firefox-<old-version>-x86_64.pkg.tar.zst
```

## Repair from the USB stick

Boot the USB stick (*Start VeyraOS*), open **Terminal**, then:

```bash
lsblk -f                                   # find your root and EFI partitions
# --- btrfs (default) ---
sudo mount -o subvol=@ /dev/nvme0n1p5 /mnt
sudo mount -o subvol=@home /dev/nvme0n1p5 /mnt/home
# --- ext4/xfs instead ---
# sudo mount /dev/nvme0n1p5 /mnt
sudo mount /dev/nvme0n1p1 /mnt/boot/efi    # the EFI system partition
# encrypted? first: sudo cryptsetup open /dev/nvme0n1p5 cryptroot  (then use /dev/mapper/cryptroot)

for d in proc sys dev run; do sudo mount --rbind /$d /mnt/$d; done
sudo chroot /mnt /bin/bash
```

Inside the chroot (your installed system):

```bash
# Reinstall the boot loader (UEFI)
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=VeyraOS --removable
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=VeyraOS
/usr/lib/veyra/grub-defaults
grub-mkconfig -o /boot/grub/grub.cfg

# Rebuild the initramfs for all kernels
mkinitcpio -P

# Finish an interrupted update
pacman -Syu

exit
sudo umount -R /mnt && sudo reboot
```

## Windows missing from the boot menu

```bash
sudo /usr/lib/veyra/grub-defaults          # sets GRUB_DISABLE_OS_PROBER=false
sudo os-prober                             # should list Windows
sudo grub-mkconfig -o /boot/grub/grub.cfg
```

If Windows does not show up, its partition may be hibernated (Fast Startup):
boot Windows from the firmware boot menu (F11 on MSI), disable Fast Startup,
shut down fully, repeat.

## Windows' clock is wrong after using VeyraOS

The installer sets the hardware clock to local time when it finds Windows.
If you installed Windows later: `sudo sed -i 's/^clock=.*/clock="local"/' /etc/conf.d/hwclock`.

## Reset a password

Boot the USB stick, mount and chroot as above, then `passwd yourname`.

## Frozen system

Before pressing the power button, try **Ctrl+Alt+F2** (text console) and
`sudo rc-service sddm restart` (logs you out). As a last resort use the
safe kernel reboot: hold **Alt + SysRq (Print)** and press **S** (sync),
**U** (remount read-only), **B** (reboot), a second apart each. (VeyraOS
enables only these safe SysRq functions.)

## Package manager errors

| Error | Fix |
|---|---|
| `invalid or corrupted package (PGP signature)` | `sudo pacman -Sy archlinux-keyring artix-keyring && sudo pacman -Su` |
| `unable to lock database` | make sure no update is running, then `sudo rm /var/lib/pacman/db.lck` |
| `conflicting files` | read [the Arch/Artix news](https://archlinux.org/news/) — manual steps are announced there; the Updates app shows recent news |
| Keyring broken after a long time offline | `sudo rm -r /etc/pacman.d/gnupg && sudo pacman-key --init && sudo pacman-key --populate artix archlinux` |
