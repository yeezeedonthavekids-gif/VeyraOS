"""VeyraOS Control — one place for the things that make VeyraOS VeyraOS:
drivers, gaming, updates, security, restore points and services.
Everything else lives in KDE System Settings ("Settings").
"""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QHBoxLayout, QMessageBox, QPushButton,
                               QRadioButton, QVBoxLayout)

from ..common import system
from ..common.ui import Card, CommandRunner, NavWindow, Page, VERSION, init_app, kv_row, label, primary_button
from ..gaming import mode as gaming_mode
from ..gaming import steam

ANTICHEAT_URL = "https://areweanticheatyet.com"


def launch(argv: list[str]):
    try:
        subprocess.Popen(argv, start_new_session=True)
    except OSError as e:
        QMessageBox.warning(None, "Could not start", f"{argv[0]}: {e}")


class RunDialog(QDialog):
    def __init__(self, parent, title: str, argv: list[str], status: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(660, 400)
        v = QVBoxLayout(self)
        self.r = CommandRunner()
        v.addWidget(self.r, 1)
        b = QPushButton("Close")
        b.clicked.connect(self.accept)
        v.addWidget(b, 0, Qt.AlignRight)
        QTimer.singleShot(0, lambda: self.r.start(argv, status))


class ControlWindow(NavWindow):
    def __init__(self):
        super().__init__("VeyraOS Control", (1120, 760))
        self.add_page("overview", "Overview", "computer", self.overview_page())
        self.add_page("graphics", "Graphics & Drivers", "video-display", self.graphics_page())
        self.add_page("gaming", "Gaming", "input-gaming", self.gaming_page())
        self.add_page("updates", "Updates", "system-software-update", self.updates_page())
        self.add_page("security", "Security & Firewall", "security-high", self.security_page())
        self.add_page("restore", "Restore Points", "document-revert", self.restore_page())
        self.add_page("services", "Services", "preferences-system-services", self.services_page())
        self.add_page("appearance", "Appearance", "preferences-desktop-theme-global", self.appearance_page())
        self.add_page("about", "About VeyraOS", "help-about", self.about_page())

    def run(self, title: str, argv: list[str], status: str):
        RunDialog(self, title, argv, status).exec()

    # ---------------------------------------------------------- overview ---
    def overview_page(self) -> Page:
        rel = system.os_release()
        p = Page("Overview", "Your PC at a glance.")
        if system.is_live_session():
            c = Card("You are trying VeyraOS",
                     "Nothing is saved until VeyraOS is installed. Installing never erases a disk "
                     "without asking you first.")
            b = primary_button("Install VeyraOS…")
            b.clicked.connect(lambda: launch(["veyra-install"]))
            c.add(b)
            p.add(c)
        c = Card("This PC")
        gpu = system.gpu_info()
        gpus = ", ".join(g.name for g in gpu.gpus) or "Unknown"
        used, total = system.disk_usage("/")
        c.add(kv_row("Operating system", f"{rel.get('PRETTY_NAME', 'VeyraOS')}"))
        c.add(kv_row("Kernel", system.kernel()))
        c.add(kv_row("Processor", system.cpu_model()))
        c.add(kv_row("Graphics", gpus))
        c.add(kv_row("Memory", f"{system.memory_gib():.1f} GiB"))
        if total:
            c.add(kv_row("System disk", f"{used / 2**30:.0f} GiB used of {total / 2**30:.0f} GiB"))
        c.add(kv_row("Session", os.environ.get("XDG_SESSION_TYPE", "unknown").capitalize()))
        p.add(c)
        quick = Card("Quick actions")
        row = QHBoxLayout()
        for text, argv in (("Settings", ["systemsettings"]), ("Software", ["veyra-software"]),
                           ("Updates", ["veyra-update"]), ("Task Manager", ["plasma-systemmonitor"])):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, a=argv: launch(a))
            row.addWidget(b)
        row.addStretch(1)
        quick.lay.addLayout(row)
        p.add(quick)
        p.finish()
        return p

    # ---------------------------------------------------------- graphics ---
    def graphics_page(self) -> Page:
        p = Page("Graphics & Drivers")
        g = system.gpu_info()
        c = Card("Graphics adapters")
        if not g.gpus:
            c.add(label("No graphics adapter information available.", subtle=True))
        for gp in g.gpus:
            c.add(kv_row(gp.vendor.upper() if gp.vendor != "other" else "GPU", f"{gp.name}  —  driver: {gp.driver}"))
        p.add(c)
        nv = Card("NVIDIA driver")
        if g.nvidia_class == "open":
            state = (f"Proprietary NVIDIA driver {g.nvidia_version} is active (open kernel modules)."
                     if g.nvidia_loaded else
                     "NVIDIA GPU detected but the driver is not loaded. Run driver setup, then restart.")
            nv.add(label(state))
            nv.add(label("Wayland is supported (Plasma Wayland session, default). Vulkan, CUDA, NVENC/NVDEC "
                         "and hardware video decoding (VA-API) are available.", subtle=True))
        elif g.nvidia_class == "legacy":
            nv.add(label("This NVIDIA GPU (Maxwell/Pascal/Volta or older) is not supported by the current "
                         "NVIDIA driver. VeyraOS uses the open-source nouveau driver for it. See the NVIDIA "
                         "guide in the documentation for the legacy driver."))
        else:
            nv.add(label("No NVIDIA GPU detected. The NVIDIA driver is not needed.", subtle=True))
        row = QHBoxLayout()
        b1 = QPushButton("NVIDIA Settings")
        b1.setEnabled(bool(g.nvidia_loaded) and system.which("nvidia-settings"))
        b1.clicked.connect(lambda: launch(["nvidia-settings"]))
        b2 = QPushButton("Re-run driver setup")
        b2.clicked.connect(lambda: self.run("Driver setup", system.helper_argv("nvidia-setup"),
                                            "Detecting hardware and configuring drivers…"))
        b3 = QPushButton("Install CUDA toolkit (~4 GB)")
        b3.setEnabled(g.nvidia_class == "open")
        b3.clicked.connect(lambda: self.run("Install CUDA", system.helper_argv("pkg-install", "cuda"),
                                            "Installing the CUDA toolkit…"))
        for b in (b1, b2, b3):
            row.addWidget(b)
        row.addStretch(1)
        nv.lay.addLayout(row)
        p.add(nv)
        p.finish()
        return p

    # ------------------------------------------------------------ gaming ---
    def gaming_page(self) -> Page:
        p = Page("Gaming", "Steam, Proton, Lutris, Gamescope, MangoHud and GameMode are preinstalled.")
        gm = Card("Gaming Mode",
                  "Pauses notifications, file indexing, update checks and non-essential background "
                  "services, and sets the CPU to performance. Network, audio and controllers are not "
                  "affected. Shortcut: Meta+G.")
        self.gm_state = label("")
        self.gm_btn = primary_button("")
        self.gm_btn.clicked.connect(self.toggle_gaming)
        gm.add_row(self.gm_state, self.gm_btn)
        p.add(gm)
        self.refresh_gaming()

        st = Card("Steam Play (Proton)",
                  "Run Windows games from your Steam library with Proton Experimental. "
                  "Start Steam once and sign in before enabling this.")
        b = QPushButton("Use Proton Experimental for all games")
        b.clicked.connect(self.enable_steam_play)
        st.add(b)
        p.add(st)

        mh = Card("Performance overlay (MangoHud)",
                  "Shows FPS, frame times, CPU/GPU load and temperatures. Toggle in game with Right Shift+F12.")
        self.mh_box = QCheckBox("Show the overlay in all Vulkan/OpenGL games (applies after signing out)")
        self.mh_box.setChecked(os.path.exists(self._mangohud_env()))
        self.mh_box.toggled.connect(self.set_mangohud_global)
        mh.add(self.mh_box)
        p.add(mh)

        tips = Card("Steam launch options",
                    "Right-click a game > Properties > Launch Options:")
        tips.add(label("<code>gamemoderun %command%</code> — per-game CPU tuning<br>"
                       "<code>mangohud %command%</code> — overlay for one game<br>"
                       "<code>gamescope -f -- %command%</code> — run in Gamescope (fullscreen, scaling, frame limiter)",
                       rich=True))
        p.add(tips)

        ac = Card("Anti-cheat compatibility",
                  "Some online games use anti-cheat systems that block Linux, even with Proton. "
                  "For example Fortnite, Valorant, Call of Duty (Warzone/Black Ops), Rainbow Six Siege, "
                  "Battlefield 6, League of Legends and Apex Legends currently do NOT run on Linux. "
                  "Many others work (e.g. Counter-Strike 2, Dota 2, Elden Ring, Helldivers 2). "
                  "Publishers can change this at any time.")
        ac.add(label(f'Check a specific game before buying: <a href="{ANTICHEAT_URL}">{ANTICHEAT_URL}</a> '
                     'and <a href="https://www.protondb.com">protondb.com</a>', rich=True))
        p.add(ac)
        p.finish()
        return p

    def refresh_gaming(self):
        on = gaming_mode.is_active()
        self.gm_state.setText("Gaming Mode is <b>on</b>." if on else "Gaming Mode is off.")
        self.gm_btn.setText("Turn off" if on else "Turn on")

    def toggle_gaming(self):
        try:
            subprocess.run(["veyra-gaming-mode", "toggle"], timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            QMessageBox.warning(self, "Gaming Mode", str(e))
        self.refresh_gaming()

    def enable_steam_play(self):
        try:
            changed = steam.enable_steam_play()
        except RuntimeError as e:
            QMessageBox.information(self, "Steam is running", str(e))
            return
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Steam Play", f"Could not update the Steam configuration: {e}")
            return
        if not steam.steam_roots():
            QMessageBox.information(self, "Steam Play", "Steam has not been started yet. Start Steam once, "
                                    "sign in, exit Steam, then try again.")
        elif changed:
            QMessageBox.information(self, "Steam Play", "Done. All Windows games will use Proton Experimental.")
        else:
            QMessageBox.information(self, "Steam Play", "Proton Experimental is already the default.")

    @staticmethod
    def _mangohud_env() -> str:
        return os.path.expanduser("~/.config/plasma-workspace/env/veyra-mangohud.sh")

    def set_mangohud_global(self, on: bool):
        path = self._mangohud_env()
        if on:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("# Written by VeyraOS Control: MangoHud overlay in all games\nexport MANGOHUD=1\n")
        elif os.path.exists(path):
            os.remove(path)

    # ----------------------------------------------------------- updates ---
    def updates_page(self) -> Page:
        p = Page("Updates")
        c = Card("Automatic updates",
                 "VeyraOS is a rolling release: security fixes arrive together with regular updates. "
                 "A restore point is created before every update when Timeshift is set up.")
        modes = [("notify", "Notify me when updates are available (recommended)"),
                 ("download", "Download updates automatically, install when I choose"),
                 ("install", "Install updates automatically (not on battery or in Gaming Mode)"),
                 ("off", "Off — I will check myself")]
        self.au_group = QButtonGroup(self)
        cur = system.auto_update_mode()
        for key, text in modes:
            rb = QRadioButton(text)
            rb.setProperty("mode", key)
            rb.setChecked(key == cur)
            self.au_group.addButton(rb)
            c.add(rb)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_auto_update)
        c.add(apply_btn)
        p.add(c)
        o = Card("Update now")
        b = primary_button("Open Updates")
        b.clicked.connect(lambda: launch(["veyra-update"]))
        o.add(b)
        p.add(o)
        p.finish()
        return p

    def apply_auto_update(self):
        b = self.au_group.checkedButton()
        if b:
            self.run("Automatic updates", system.helper_argv("auto-update", b.property("mode")), "Saving…")

    # ---------------------------------------------------------- security ---
    def security_page(self) -> Page:
        p = Page("Security & Firewall")
        fw = Card("Firewall", "Blocks all unsolicited incoming connections. Outgoing traffic is allowed.")
        active = system.firewall_active()
        fw.add(label("Status: <b>%s</b>" % ("Active" if active else "Inactive — your PC is not protected"),
                     rich=True))
        b = QPushButton("Turn off" if active else "Turn on")
        b.clicked.connect(lambda: self.run("Firewall", system.helper_argv("firewall", "off" if active else "on"),
                                           "Changing firewall state…"))
        fw.add(b)
        p.add(fw)
        rules = Card("Allowed services", "Allow incoming connections for specific features (local network only where possible).")
        for r in system.firewall_rules():
            cb = QCheckBox(r.description)
            cb.setChecked(r.enabled)
            cb.toggled.connect(lambda on, n=r.name: self.run(
                "Firewall", system.helper_argv("firewall-service", "enable" if on else "disable", n),
                "Updating firewall rules…"))
            rules.add(cb)
        p.add(rules)
        priv = Card("Privacy",
                    "VeyraOS collects no telemetry. KDE's optional feedback is off, Firefox telemetry and "
                    "studies are disabled by policy, and no advertising or third-party repositories are included.")
        p.add(priv)
        sb = Card("Secure Boot")
        sb.add(label(self._secure_boot_state()))
        p.add(sb)
        p.finish()
        return p

    @staticmethod
    def _secure_boot_state() -> str:
        d = "/sys/firmware/efi/efivars"
        if not os.path.isdir(d):
            return "Legacy BIOS boot (Secure Boot not applicable)."
        for f in os.listdir(d):
            if f.startswith("SecureBoot-"):
                try:
                    v = open(os.path.join(d, f), "rb").read()
                    on = bool(v and v[-1] == 1)
                    return ("Secure Boot is ON (custom keys enrolled)." if on else
                            "Secure Boot is off. VeyraOS can use Secure Boot with your own keys (sbctl); "
                            "see the Security guide.")
                except OSError:
                    break
        return "Secure Boot state unknown."

    # ----------------------------------------------------------- restore ---
    def restore_page(self) -> Page:
        p = Page("Restore Points", "Like Windows System Restore: roll the system back if an update causes problems.")
        c = Card("Timeshift")
        if system.timeshift_configured():
            c.add(label("Timeshift is set up. A restore point is created automatically before each update."))
        else:
            c.add(label("Timeshift is not set up yet. Open Timeshift once and choose BTRFS (recommended, "
                        "instant snapshots) or RSYNC."))
        row = QHBoxLayout()
        b1 = primary_button("Open Timeshift")
        b1.clicked.connect(lambda: launch(["timeshift-launcher"]))
        b2 = QPushButton("Create restore point now")
        b2.setEnabled(system.timeshift_configured())
        b2.clicked.connect(lambda: self.run("Restore point", system.helper_argv("snapshot"),
                                            "Creating a restore point…"))
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        c.lay.addLayout(row)
        c.add(label("If the system does not start: choose the restore point in Timeshift from the "
                    "VeyraOS USB stick (live system). See the Recovery guide.", subtle=True))
        p.add(c)
        p.finish()
        return p

    # ---------------------------------------------------------- services ---
    def services_page(self) -> Page:
        p = Page("Services", "Optional background services. Off services use no memory or CPU.")
        for name, title, desc in (
                ("cupsd", "Printing", "Print to local and network printers."),
                ("bluetoothd", "Bluetooth", "Wireless headphones, controllers, mice and keyboards."),
                ("sshd", "Remote login (SSH)", "Log in to this PC from another computer. Leave off unless you need it.")):
            c = Card(title, desc)
            if not system.service_installed(name):
                c.add(label("Not installed.", subtle=True))
            else:
                en = system.service_enabled(name)
                cb = QCheckBox("Enabled")
                cb.setChecked(en)
                cb.toggled.connect(lambda on, n=name: self.run(
                    "Services", system.helper_argv("service", "enable" if on else "disable", n),
                    f"{'Starting' if on else 'Stopping'} {n}…"))
                c.add(cb)
            p.add(c)
        p.finish()
        return p

    # -------------------------------------------------------- appearance ---
    def appearance_page(self) -> Page:
        p = Page("Appearance")
        c = Card("Theme", "Switch between the VeyraOS light and dark themes. Your panel layout is kept.")
        row = QHBoxLayout()
        for text, pkg in (("Light", "org.veyraos.desktop"), ("Dark", "org.veyraos.desktop.dark")):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, k=pkg: self.apply_theme(k))
            row.addWidget(b)
        row.addStretch(1)
        c.lay.addLayout(row)
        p.add(c)
        more = Card("More options")
        b = QPushButton("Open Appearance settings")
        b.clicked.connect(lambda: launch(["systemsettings", "kcm_lookandfeel"]))
        more.add(b)
        p.add(more)
        p.finish()
        return p

    def apply_theme(self, pkg: str):
        try:
            subprocess.run(["plasma-apply-lookandfeel", "-a", pkg], timeout=60)
            subprocess.run(["/usr/lib/veyra/theme-sync"], timeout=30)
        except (OSError, subprocess.TimeoutExpired) as e:
            QMessageBox.warning(self, "Appearance", f"Could not change the theme: {e}")

    # ------------------------------------------------------------- about ---
    def about_page(self) -> Page:
        rel = system.os_release()
        p = Page("About VeyraOS")
        c = Card(rel.get("PRETTY_NAME", f"VeyraOS {VERSION}"))
        c.add(label("A Windows-familiar desktop built on Artix Linux (OpenRC, no systemd) and KDE Plasma."))
        c.add(kv_row("Version", rel.get("VERSION", VERSION)))
        c.add(kv_row("Base", "Artix Linux (OpenRC) + Arch Linux repositories"))
        c.add(kv_row("Desktop", "KDE Plasma 6"))
        c.add(label('Documentation and source: <a href="https://github.com/yeezeedonthavekids-gif/veyraos">'
                    'github.com/yeezeedonthavekids-gif/veyraos</a>', rich=True))
        c.add(label("VeyraOS is free software (GPL-3.0-or-later; artwork CC BY-SA 4.0). It builds on the work of "
                    "the Artix Linux, Arch Linux and KDE communities.", subtle=True))
        p.add(c)
        p.finish()
        return p


def main() -> int:
    app = init_app("veyra-control", "VeyraOS Control", "veyraos")
    w = ControlWindow()
    if len(sys.argv) > 1:
        w.show_page(sys.argv[1])
    w.show()
    return app.exec()
