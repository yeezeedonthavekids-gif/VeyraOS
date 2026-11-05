# NVIDIA on VeyraOS

## What is installed

| Package | Purpose |
|---|---|
| `nvidia-open-dkms` (fallback `nvidia-open`) | Kernel modules — **open** modules, built by DKMS for every installed kernel (`linux`, `linux-lts`) |
| `nvidia-utils`, `lib32-nvidia-utils` | OpenGL, **Vulkan**, EGL, NVENC/NVDEC, CUDA runtime libraries (64- and 32-bit for games) |
| `nvidia-settings` | NVIDIA control panel |
| `opencl-nvidia` | OpenCL |
| `libva-nvidia-driver` | VA-API on top of NVDEC (hardware video decoding in browsers/players) |
| `egl-wayland` | Wayland EGL platform |

**Why the open modules:** NVIDIA's RTX 50 series (Blackwell, e.g. the RTX
5060) is supported *only* by the open kernel modules; the legacy closed
modules do not support it. The userspace driver is the same proprietary
driver either way — this is not Nouveau.

CUDA toolkit (~4 GB, compilers and libraries for development) is not on the
ISO: *VeyraOS Control → Graphics & Drivers → Install CUDA toolkit* or
`sudo pacman -S cuda`. The CUDA *runtime* used by apps is already in
`nvidia-utils`.

## Configuration applied by VeyraOS

| Setting | Where | Why |
|---|---|---|
| `nvidia_drm.modeset=1 nvidia_drm.fbdev=1` | kernel command line + `/etc/modprobe.d/veyra-nvidia.conf` | KMS is required for Wayland and gives a flicker-free console |
| `NVreg_PreserveVideoMemoryAllocations=1` | modprobe.d | keeps VRAM across suspend (no garbled desktop after resume) |
| elogind sleep hook `/usr/lib/elogind/system-sleep/veyra-nvidia` | veyra-nvidia | OpenRC replacement for NVIDIA's `nvidia-suspend/resume` systemd units (calls `nvidia-sleep.sh`) |
| `LIBVA_DRIVER_NAME=nvidia`, `NVD_BACKEND=direct` | `/etc/profile.d/veyra-nvidia.sh`, only when the NVIDIA driver is loaded | hardware video decoding |
| nouveau blacklisted | by `nvidia-utils` | no driver conflicts |

## Automatic driver setup

`/usr/lib/veyra/nvidia-setup` runs during installation (and from *VeyraOS
Control → Re-run driver setup*). It uses `veyra-gpu-detect`, which classifies
NVIDIA GPUs by PCI device ID:

| Result | GPUs | Action |
|---|---|---|
| `open` | Turing and newer: GTX 16xx, RTX 20/30/40/**50** | keep the driver, ensure kernel parameters |
| `legacy` | Maxwell, Pascal, Volta (GTX 9xx/10xx, Titan V) | remove `nvidia-open` (it cannot drive them), use nouveau; install the legacy driver manually (below) |
| `none` | no NVIDIA GPU | remove the NVIDIA packages |

`veyra-gpu-detect --json` shows what it found; `veyra-gpu-detect` alone gives
a readable summary.

## Wayland or X11?

The default session is **Plasma (Wayland)** — recommended with driver 560+
(VRR/G-Sync, fractional scaling, HDR in Plasma 6, tearing control for games).
If you hit a Wayland-specific problem, choose **Plasma (X11)** on the login
screen (session menu, bottom left), if your Plasma version still ships it.

*NVIDIA Settings* is limited on Wayland (no PowerMizer/overclock pages) —
that is an NVIDIA limitation; use `nvidia-smi` for monitoring:
`watch -n1 nvidia-smi`.

## Browser hardware video decoding

Firefox: VA-API via NVDEC requires disabling Firefox's RDD sandbox
(`MOZ_DISABLE_RDD_SANDBOX=1`). VeyraOS does **not** do this by default
because it weakens Firefox's security. If you want it:
`about:config` → `media.ffmpeg.vaapi.enabled = true`, and add
`export MOZ_DISABLE_RDD_SANDBOX=1` to `~/.config/plasma-workspace/env/firefox-vaapi.sh`.
Chromium-based browsers: `--enable-features=VaapiVideoDecodeLinuxGL`.

## Legacy GPUs (GTX 10-series and older)

The `nvidia-580xx-dkms` driver series is the last for Maxwell/Pascal and is
maintained in the AUR (not an official repository, so VeyraOS does not
install it automatically). With an AUR helper: `yay -S nvidia-580xx-dkms
nvidia-580xx-utils lib32-nvidia-580xx-utils`. Until then nouveau provides a
working desktop with limited performance.

## Troubleshooting

| Problem | Fix |
|---|---|
| Black screen after GRUB (live USB) | GRUB → *Troubleshooting → Safe graphics*. Then report the GPU (`lspci -nn | grep -i nvidia`) |
| Black screen after GRUB (installed) | At the GRUB menu press **e**, add `nomodeset` to the `linux` line, F10. Log in, run *VeyraOS Control → Re-run driver setup*, update (`sudo pacman -Syu`) |
| `nvidia-smi`: "couldn't communicate with the driver" | The module is not built for the running kernel: `sudo dkms autoinstall` then reboot; or boot the LTS kernel (GRUB → Advanced options) |
| Desktop garbled after resume | Check `cat /proc/driver/nvidia/params | grep Preserve` shows `1`, and that `/usr/lib/elogind/system-sleep/veyra-nvidia` exists |
| Kernel update broke the driver | DKMS rebuilds on every kernel update; if a brand-new kernel is not supported yet, boot `linux-lts` until the driver catches up |
| Want to go back to nouveau (recovery) | `sudo pacman -Rns nvidia-open-dkms nvidia-utils lib32-nvidia-utils nvidia-settings` and reboot |

*Not verified on real hardware during development.* The configuration
follows NVIDIA's documented requirements for the open modules, Wayland and
suspend; the detection logic is unit-tested with real PCI IDs (RTX 5060
`10de:2d05` → `open`, GTX 1080 `10de:1b80` → `legacy`).
