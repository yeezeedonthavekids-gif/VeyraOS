# Installing VeyraOS

## 1. Write the USB stick (8 GB or larger)

Verify the download first: `sha256sum -c veyraos-*.iso.sha256`.

| From | How |
|---|---|
| Windows | **Rufus** → select the ISO → when asked, choose **"Write in DD Image mode"**. (Ventoy also works.) |
| Linux | `sudo dd if=veyraos-….iso of=/dev/sdX bs=4M status=progress oflag=sync` (sdX = the USB stick, **not** a partition) |
| macOS | balenaEtcher |

## 2. Firmware (BIOS) settings

General: boot in **UEFI** mode; **disable Secure Boot** for the live USB and
installation (it can be re-enabled later with your own keys — see
[SECURITY.md](SECURITY.md#secure-boot)).

**MSI PRO B840-VC WIFI** (Click BIOS 5; names can differ slightly between
BIOS versions):

1. Press **Del** at power-on to enter the BIOS, **F7** for Advanced mode.
2. *Settings → Security → Secure Boot →* **Disabled**.
3. *Settings → Advanced → Windows OS Configuration →* leave **BIOS UEFI/CSM
   Mode = UEFI** (CSM off).
4. Optional but recommended for gaming: *OC → Memory →* enable **EXPO** for
   your RAM's rated speed; *Settings → Advanced → PCIe →* **Re-Size BAR
   Support = Enabled** (needs "Above 4G memory" enabled; improves GPU
   performance with the RTX 5060).
5. **F10** to save. At the next power-on press **F11** for the boot menu and
   pick the USB stick ("UEFI: …").

## 3. Try it (live session)

The GRUB menu offers:

* **Start VeyraOS 2026.11** — normal start
* **Start VeyraOS (load into RAM)** — copies the system to memory (needs
  ~6 GB RAM free); the USB stick can be removed and everything runs faster
* **Troubleshooting** → safe graphics (no GPU driver), text-mode rescue
  console, verify medium integrity, verbose boot
* Memory test, UEFI firmware settings, restart, shut down

The live session logs in automatically. Nothing is written to your disks
unless you run the installer. Wi-Fi, sound, Bluetooth and the NVIDIA driver
work in the live session, so you can test your hardware first.

## 4. Before installing next to Windows

1. **Back up** anything important. Resizing partitions is reliable but never
   risk-free.
2. **BitLocker / Device Encryption:** in Windows, open *Manage BitLocker* and
   either *Suspend protection* or at least write down the **recovery key**.
   Changing the boot order can trigger a recovery-key prompt in Windows.
3. **Turn off Fast Startup:** *Control Panel → Power Options → Choose what the
   power buttons do → Change settings that are currently unavailable →*
   untick **Turn on fast startup**. (Otherwise Windows leaves its partition
   in a hibernated state that Linux must not resize or write.)
4. Shut Windows down completely (Shift + Shut down).
5. Optional: shrink the Windows partition yourself in *Disk Management*
   (Windows knows best which blocks are movable). The installer can also do it.

## 5. Install

Double-click **Install VeyraOS** on the live desktop.

1. **Welcome:** language. Requirements: 40 GB disk, 4 GB RAM (internet is not
   required — the installer works offline).
2. **Location:** time zone (pick on the map; no online lookup).
3. **Keyboard:** layout (type in the test box).
4. **Partitions** — nothing is preselected; you must choose:
   * **Install alongside** — shrinks an existing partition (e.g. Windows) with
     a slider and installs into the freed space. Windows stays and appears in
     the boot menu.
   * **Replace a partition** — overwrite one partition you pick.
   * **Erase disk** — the whole selected disk. Check the disk name and size
     twice.
   * **Manual partitioning** — full control (create `/` and use the existing
     EFI partition at `/boot/efi`).
   * File system: **btrfs** (default, enables restore points), ext4 or xfs.
   * **Encrypt system** — LUKS; you'll type the passphrase at every boot.
   * Swap: none needed (compressed zram swap is automatic); choose "swap to
     file/partition" only if you want hibernation.
5. **Users:** name, login, computer name, password. Administrator rights use
   your own password (there is no root password).
6. **Summary:** everything that will happen, including every partition change.
   **Nothing has been written yet.**
7. **Install** → confirm → ~5–15 minutes.
8. Restart, remove the USB stick.

What the installer does automatically: detects your GPU and keeps the NVIDIA
driver only if it is supported (RTX 5060: yes), detects Windows for the boot
menu and sets the hardware clock to local time so Windows' clock stays right,
creates a fresh package-signing keyring, removes the live-only packages.

## 6. After the first login

The **Welcome** window walks you through:

* **Updates** — install them first.
* **Restore points** — open Timeshift once, choose **BTRFS**, done. From then
  on a restore point is made before every update.
* **Gaming** — start Steam once and sign in, exit Steam, then *VeyraOS
  Control → Gaming → Use Proton Experimental for all games*.
* **Software** — install Discord, Spotify, browsers, office suites, etc.

Dual boot: the GRUB menu shows **Windows Boot Manager**. To change which entry
starts by default: `sudo nano /etc/default/grub` (`GRUB_DEFAULT`), then
`sudo grub-mkconfig -o /boot/grub/grub.cfg`.

## Hardware notes for the reference PC

| Part | Status |
|---|---|
| Ryzen 7 8700F (Zen 4, no integrated GPU) | Supported by the stock kernel; `amd-pstate-epp` CPU scaling; microcode via `amd-ucode` |
| RTX 5060 8 GB (Blackwell) | Proprietary driver with **open kernel modules** (`nvidia-open-dkms`, required for RTX 50) — see [NVIDIA.md](NVIDIA.md) |
| MSI PRO B840-VC WIFI | Standard AMD chipset; onboard audio, LAN and USB use in-kernel drivers. The Wi-Fi/Bluetooth card model varies by board revision — check `lspci` in the live session; current MediaTek and Realtek Wi-Fi 6/6E/7 cards are supported by recent kernels |

Because the 8700F has no integrated graphics, the monitor must be connected to
the **RTX 5060**. If the screen stays black after GRUB, use *Troubleshooting →
Safe graphics* and see [NVIDIA.md](NVIDIA.md#troubleshooting).
