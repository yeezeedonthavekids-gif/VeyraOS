# Performance

Principle: **only changes with a documented, measurable reason.** No
"gaming kernels", no scheduler or I/O-scheduler swaps, no mitigations
disabled, no CPU governor forced globally.

## What VeyraOS changes, and why

| Change | Effect | Why it is safe |
|---|---|---|
| **zram swap** (zstd, 50 % of RAM, priority 100) | Under memory pressure, cold pages are compressed in RAM instead of the desktop stalling or apps being killed | Used by Fedora, ChromeOS, SteamOS; no disk wear |
| `vm.swappiness=100`, `vm.page-cluster=0` | Prefer compressing idle memory into zram over evicting file cache; no read-ahead for zram | Standard companion settings for zram (Fedora/Pop!_OS use similar or higher) |
| `vm.max_map_count=2147483642` | Some games crash without it | Same value as Arch/SteamOS defaults |
| `ntsync` module loaded, `/dev/ntsync` usable | Wine/Proton 10+ use kernel NT sync: less CPU overhead, better frame pacing | Upstream kernel driver |
| High hard `nofile` limit | esync needs many file descriptors | Soft limit unchanged |
| KWin `AllowTearing=true` | Fullscreen games that disable V-Sync get lower latency | Only applies when the game requests it |
| Lean OpenRC service set | No print spooler, SSH, ModemManager-style daemons running by default; only 2 text consoles | Each can be enabled in VeyraOS Control |
| Baloo indexes **file names only**; game folders excluded | Avoids indexer CPU/disk load (a top cause of "random" desktop slowdowns) | Full-text search can be enabled |
| Empty session at login | Faster login, nothing restored unexpectedly | Windows behaves the same |
| ~30 % shorter animations | Feels snappier | Visual only |
| Gaming Mode / GameMode | Performance CPU preference only while gaming | Restored afterwards |

## What VeyraOS deliberately does not do

* No custom kernel (stock `linux` + `linux-lts`): NVIDIA DKMS, security
  updates and support depend on it.
* No `mitigations=off`: small gains, real security cost.
* No forced `performance` governor: Zen 4's `amd-pstate-epp` with balanced
  preference already boosts instantly; GameMode raises it while gaming.
* No `rc_parallel="YES"` in OpenRC: OpenRC documents parallel start-up as
  less reliable; boot is already short with the reduced service set.
* No I/O scheduler or VM dirty-ratio tweaks without measurements.

## Measuring (before/after)

`tools/bench-idle.sh LABEL` records, on a real installation:

* boot duration to the OpenRC default runlevel,
* idle memory use and swap use,
* idle CPU % over 60 s,
* process and started-service counts,
* the top memory users,

into `bench-LABEL-DATE.json`. Recommended protocol: reboot, log in, wait two
minutes without opening apps, run the script three times, compare the
medians before and after a change. Game performance: MangoHud's logging
(`Shift_L+F2` starts/stops a log; set `output_folder=` in MangoHud.conf)
gives FPS and frame-time percentiles per run.

## Measurements so far

**None on real hardware yet** — VeyraOS was developed in an environment
without a GPU or access to the package mirrors, so the complete image could
not be built or run on the reference PC. The QEMU boot tests run under
software emulation (no KVM), where timings say nothing about real
performance, so they are not reported as benchmarks. First real numbers are
an explicit release-blocking task for 2026.11 final (see
[KNOWN-ISSUES.md](KNOWN-ISSUES.md)).

Expected ballpark from the component choices (to be confirmed): Plasma 6
Wayland sessions typically idle at roughly 1.3–1.8 GB RAM used and well
under 1 % CPU on a modern 8-core desktop.
