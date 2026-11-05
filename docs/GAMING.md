# Gaming on VeyraOS

## Preinstalled

| | |
|---|---|
| **Steam** | with **Proton** and **Proton Experimental** (Steam downloads Proton versions itself) |
| **Lutris** | GOG, Epic, Battle.net, EA app, Ubisoft Connect, emulators — installs games with community scripts |
| **Gamescope** | micro-compositor: fullscreen/scaling (FSR), frame limiting, HDR, fixes many fullscreen/mode-switching issues |
| **MangoHud** | performance overlay (FPS, frame times, CPU/GPU load/temps) — Right Shift+F12 toggles |
| **GameMode** | per-game CPU governor, priority and scheduling while a game runs |
| **Wine** (staging) + winetricks | for non-Steam Windows apps/games |
| **Vulkan** | 64- and 32-bit loaders + NVIDIA/AMD/Intel drivers |

More in *Software → Gaming*: Heroic (Epic/GOG/Amazon), ProtonUp-Qt
(GE-Proton), Bottles, Prism Launcher, RetroArch, GOverlay.

## First steps

1. Start **Steam**, sign in, let it update, then *Steam → Exit*.
2. *VeyraOS Control → Gaming →* **Use Proton Experimental for all games**
   (same as *Steam → Settings → Compatibility → Enable Steam Play for all
   other titles* with Proton Experimental). Also available as
   `veyra-steam-setup` in a terminal.
3. Optional per game (*right-click → Properties → Launch Options*):
   * `gamemoderun %command%` — GameMode CPU tuning
   * `mangohud %command%` — overlay for this game
   * `gamescope -f -W 2560 -H 1440 -- %command%` — run inside Gamescope
   * combine: `gamemoderun mangohud %command%`

## Gaming Mode (Meta+G)

A one-click mode for long sessions. **On:** notifications held back (Do Not
Disturb), file indexing paused, update pop-ups paused, scheduled jobs and
printing service paused, CPU energy preference set to performance.
**Never touched:** network, audio, controllers/Bluetooth, the desktop
itself. **Off** restores everything exactly. Configure the paused services in
`/etc/veyra/gaming-mode.conf`. It does not replace GameMode — they combine.

## Latency and frame pacing

* Plasma (Wayland) on NVIDIA 560+ supports **tearing** for fullscreen games
  (`AllowTearing=true` in VeyraOS' KWin defaults) — lower input latency when
  a game disables V-Sync.
* **VRR / G-Sync:** *Settings → Display → Adaptive sync: Automatic*.
* `ntsync` is loaded at boot and accessible to users: Proton 10+ uses it for
  lower CPU overhead and better frame pacing than esync/fsync.
* High open-file limit (esync), `vm.max_map_count` for games that need it.
* Frame limiter: MangoHud (`fps_limit=` in `~/.config/MangoHud/MangoHud.conf`,
  `fps_limit_method=late` is preset for lowest latency) or Gamescope `-r`.
* No "gaming kernel" or unproven scheduler tweaks — see
  [PERFORMANCE.md](PERFORMANCE.md).

## Controllers

| Controller | Notes |
|---|---|
| Xbox (USB) | kernel `xpad` driver, works out of the box |
| Xbox (Bluetooth) | pair in *Settings → Bluetooth*; recent kernels handle Xbox Series controllers |
| Xbox Wireless Adapter (USB dongle) | needs the `xone` driver (AUR) |
| PlayStation 4/5 | kernel `hid-playstation`/`hid-sony`, USB and Bluetooth |
| Switch Pro | kernel `hid-nintendo` |
| Steam Input | Steam remaps any controller per game (*Steam → Settings → Controller*) |

## Anti-cheat compatibility — please read

Proton runs most Windows games, but **some online games block Linux on
purpose** through their anti-cheat. This is a decision of the game publisher
and **cannot be fixed by VeyraOS**. At the time this guide was written (status as publicly known in mid-2026) these did **not**
work on Linux:

| Game | Why |
|---|---|
| **Fortnite** | Epic has not enabled Easy Anti-Cheat for Linux/Proton |
| Valorant, League of Legends | Riot Vanguard (kernel-level, Windows only) |
| Call of Duty (Warzone, Black Ops 6/7) | Ricochet — Linux blocked |
| Battlefield 6 / 2042 | EA Javelin — Linux blocked, Secure Boot on Windows required |
| Apex Legends | EA disabled Linux/Steam Deck support in 2024 |
| Rainbow Six Siege | BattlEye not enabled for Linux by Ubisoft |
| Destiny 2 | BattlEye not enabled for Linux by Bungie |
| PUBG: Battlegrounds | Linux not supported |
| GTA Online | BattlEye; Rockstar blocked Linux in 2024 |

Many anti-cheat games **do** work because their developers enabled Proton
support, e.g. Elden Ring, Helldivers 2, The Finals, Marvel Rivals,
Counter-Strike 2 and Dota 2 (native), Deep Rock Galactic, Halo Infinite.

Statuses change — publishers add *and remove* Linux support. **Check a game
before buying:** [areweanticheatyet.com](https://areweanticheatyet.com) (anti-cheat
status) and [protondb.com](https://www.protondb.com) (community reports).
For blocked games the realistic options are dual-booting Windows (VeyraOS
installs alongside it) or a cloud-gaming service.

## Troubleshooting

| Problem | Try |
|---|---|
| Game does not start | Steam → Properties → Compatibility → force *Proton Experimental*, or a GE-Proton from ProtonUp-Qt |
| Stutter on first run | Shader compilation; Steam's shader pre-caching (Settings → Downloads) helps |
| Wrong GPU used / low FPS | `nvidia-smi` while playing; check MangoHud shows the RTX 5060 |
| Fullscreen issues | launch through `gamescope -f -- %command%` |
| Controller not detected | Steam → Settings → Controller → enable the right "Support" option; reconnect |
