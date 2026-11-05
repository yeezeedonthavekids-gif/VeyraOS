# The VeyraOS desktop

## Windows → VeyraOS

| Windows | VeyraOS | App |
|---|---|---|
| Start menu | Start menu (VeyraOS logo, or the **Meta/Windows** key) | Plasma Kickoff: pinned grid, all apps, search, power |
| Taskbar | Centered taskbar with pinned apps, previews on hover/click | Plasma icon task manager |
| System tray / Quick settings | Tray: network, volume, Bluetooth, battery, notifications, clipboard | Plasma system tray |
| Notification center | Bell in the tray; pop-ups bottom-right; Do Not Disturb | Plasma notifications |
| File Explorer | **File Explorer** — Quick-access sidebar (Home, Desktop, Documents, Downloads, Pictures, Music, Videos), drives under *Devices*, breadcrumb path, tabs, previews, search | Dolphin |
| Settings | **Settings** (Meta+I) | KDE System Settings |
| — | **VeyraOS Control**: drivers, gaming, updates, firewall, restore points, services, theme | VeyraOS |
| Microsoft Store | **Software** | VeyraOS Software (repositories + Flathub) |
| Windows Update | **Updates** | VeyraOS Updates |
| Task Manager (Ctrl+Shift+Esc) | **Task Manager** | Plasma System Monitor |
| Snipping Tool (Meta+Shift+S) | **Screenshot** | Spectacle |
| Terminal / PowerShell | **Terminal** | Konsole |
| Notepad | **Text Editor** | Kate |
| Photos | **Photos** | Gwenview |
| Disk Management | **Disk Management** | KDE Partition Manager |
| 7-Zip/WinRAR | **Archive Manager** (zip, 7z, rar, tar…) | Ark |
| System Restore | **Restore Points** | Timeshift (btrfs snapshots) |
| Network settings | tray → Network, *Settings → Network* | plasma-nm (NetworkManager) |
| Bluetooth | tray → Bluetooth | BlueDevil |

App names in the Start menu are "friendly" names (File Explorer, Task
Manager…). They are generated per user at login by
`/usr/lib/veyra/friendly-names` from the real application entries, so they
stay correct after updates. Turn them off with
`echo off > ~/.config/veyra/friendly-names`.

## Keyboard shortcuts

| Keys | Action |
|---|---|
| Meta | Start menu |
| Meta+E | File Explorer |
| Meta+I | Settings |
| Meta+S / Alt+Space | Search (KRunner) |
| Meta+L | Lock |
| Meta+D | Show desktop |
| Meta+Tab | Task View (overview of windows and desktops) |
| Alt+Tab / Alt+Shift+Tab | Switch windows (thumbnail grid) |
| Meta+← / Meta+→ | Snap window left/right |
| Meta+↑ / Meta+↓ | Maximize / minimize |
| Meta+Z | Snap layouts (tile editor) |
| Meta+V | Clipboard history |
| Meta+. | Emoji picker |
| Meta+Shift+S | Screenshot of a region |
| Print | Screenshot |
| Ctrl+Shift+Esc | Task Manager |
| Ctrl+Alt+T | Terminal |
| Meta+Ctrl+← / → | Previous/next virtual desktop |
| Meta+G | Gaming Mode on/off |
| Alt+F4 | Close window |

Change any of them in *Settings → Keyboard → Shortcuts*.

## Window management

* Title bars: Windows-style minimize / maximize / close buttons on the right
  (red close on hover), title on the left, rounded top corners, soft shadow.
  Light and dark variants follow the system theme.
* Drag a window to the left/right screen edge to snap it to half the screen,
  to the top to maximize, to a corner for a quarter.
* Double-click a title bar to maximize. Windows open centered.
* Animations are ~30 % faster than Plasma's defaults (Windows-like
  snappiness); *Settings → Accessibility/Animation speed* to adjust.

## Themes

*VeyraOS Control → Appearance → Light / Dark* switches the colour scheme,
icons (Papirus / Papirus-Dark), panel, title bars and wallpaper (the
"Aurora" wallpaper has light and dark versions). Plasma's automatic
light/dark switching (Settings → Colors & Themes) works with the two VeyraOS
global themes; title bars are re-synced at the next login or by pressing the
theme button in VeyraOS Control.

Typography: **Inter** for the interface, **JetBrains Mono** for terminals and
code. Windows font names are mapped to metric-compatible free fonts
(Segoe UI → Inter, Arial/Times/Courier → Liberation, Consolas → JetBrains
Mono) so documents and websites keep their layout.

## Under the hood

| What | File |
|---|---|
| Panel layout (first login) | `/usr/share/plasma/look-and-feel/org.veyraos.desktop/contents/layouts/org.kde.plasma.desktop-layout.js` |
| System-wide defaults | `/etc/xdg/kdeglobals`, `kwinrc`, `kglobalshortcutsrc`, `dolphinrc`, `konsolerc`, `baloofilerc`, `ksmserverrc`, `kscreenlockerrc` |
| Colour schemes | `/usr/share/color-schemes/Veyra{Light,Dark}.colors` |
| Title bars | `/usr/share/aurorae/themes/Veyra{,Dark}/` |
| Login screen | SDDM Breeze theme with the VeyraOS wallpaper (`/etc/sddm.conf.d/10-veyra.conf`) |
| Boot splash / login splash | Plymouth theme `veyra`, KSplash in the global theme |
| Sounds | `/usr/share/sounds/veyra/` (freedesktop sound theme) |

Reset your desktop to the VeyraOS default: *Settings → Colors & Themes →
Global Theme → VeyraOS Light → tick "Desktop and window layout" → Apply*.

## Search

Dolphin search and the Start menu search use Baloo, configured to index
**file names only** (fast, negligible resources). Turn on full-text content
search in *Settings → Search → File Search* if you want it. Steam libraries,
Wine prefixes and caches are excluded.
