"""Curated catalogue shown on the Software Center home page.

Prefer the official repositories (signed, updated with the system); use
Flathub for proprietary apps that are not in the repositories or that are
officially distributed there by their vendors. Every entry is verifiable:
repository package names / Flathub IDs, no third-party repositories.
"""
from .backend import App

CATEGORIES = [
    ("internet", "Internet", "applications-internet"),
    ("gaming", "Gaming", "applications-games"),
    ("productivity", "Office & Productivity", "applications-office"),
    ("development", "Development", "applications-development"),
    ("media", "Photo, Video & Audio", "applications-multimedia"),
    ("utilities", "Utilities", "applications-utilities"),
]

_R, _F = "repo", "flatpak"
# (category, id, name, summary, source, icon)
_ENTRIES = [
    ("internet", "firefox", "Firefox", "Fast, private web browser (installed by default)", _R, "firefox"),
    ("internet", "chromium", "Chromium", "Open-source web browser behind Google Chrome", _R, "chromium"),
    ("internet", "com.google.Chrome", "Google Chrome", "Google's web browser (official Flathub build)", _F, "google-chrome"),
    ("internet", "thunderbird", "Thunderbird", "Email, calendar and contacts", _R, "thunderbird"),
    ("internet", "discord", "Discord", "Voice, video and text chat for communities and gamers", _R, "discord"),
    ("internet", "telegram-desktop", "Telegram", "Fast and secure messaging", _R, "telegram"),
    ("internet", "org.signal.Signal", "Signal", "Private messenger", _F, "signal-desktop"),
    ("internet", "us.zoom.Zoom", "Zoom", "Video meetings", _F, "Zoom"),
    ("internet", "com.spotify.Client", "Spotify", "Music streaming", _F, "spotify"),
    ("internet", "qbittorrent", "qBittorrent", "BitTorrent client", _R, "qbittorrent"),

    ("gaming", "steam", "Steam", "Valve's game store and launcher with Proton (installed by default)", _R, "steam"),
    ("gaming", "lutris", "Lutris", "Play games from GOG, Epic, Battle.net, emulators and more (installed by default)", _R, "lutris"),
    ("gaming", "com.heroicgameslauncher.hgl", "Heroic Games Launcher", "Epic Games, GOG and Amazon Prime Gaming", _F, "com.heroicgameslauncher.hgl"),
    ("gaming", "net.davidotek.pupgui2", "ProtonUp-Qt", "Install GE-Proton and other compatibility tools", _F, "net.davidotek.pupgui2"),
    ("gaming", "com.usebottles.bottles", "Bottles", "Run Windows software in managed Wine environments", _F, "com.usebottles.bottles"),
    ("gaming", "prismlauncher", "Prism Launcher", "Minecraft launcher with mod support", _R, "org.prismlauncher.PrismLauncher"),
    ("gaming", "retroarch", "RetroArch", "Emulator front-end", _R, "retroarch"),
    ("gaming", "goverlay", "GOverlay", "Configure MangoHud and vkBasalt with a GUI", _R, "goverlay"),

    ("productivity", "libreoffice-fresh", "LibreOffice", "Office suite compatible with Word, Excel and PowerPoint files", _R, "libreoffice-startcenter"),
    ("productivity", "org.onlyoffice.desktopeditors", "ONLYOFFICE", "Office suite with high Microsoft Office compatibility", _F, "onlyoffice-desktopeditors"),
    ("productivity", "md.obsidian.Obsidian", "Obsidian", "Notes and knowledge base", _F, "md.obsidian.Obsidian"),
    ("productivity", "keepassxc", "KeePassXC", "Offline password manager", _R, "keepassxc"),
    ("productivity", "com.bitwarden.desktop", "Bitwarden", "Password manager with sync", _F, "com.bitwarden.desktop"),

    ("development", "code", "Code - OSS", "Visual Studio Code built from the open-source code", _R, "com.visualstudio.code.oss"),
    ("development", "com.visualstudio.code", "Visual Studio Code", "Microsoft's build of VS Code (Flathub)", _F, "com.visualstudio.code"),
    ("development", "com.vscodium.codium", "VSCodium", "VS Code without Microsoft telemetry", _F, "com.vscodium.codium"),
    ("development", "nodejs", "Node.js", "JavaScript runtime (with npm)", _R, "nodejs"),
    ("development", "python-pip", "Python pip", "Python package installer", _R, "python"),
    ("development", "docker", "Docker", "Containers (enable the 'docker' service afterwards)", _R, "docker"),
    ("development", "jdk-openjdk", "OpenJDK", "Java development kit", _R, "java"),

    ("media", "gimp", "GIMP", "Photo editing", _R, "gimp"),
    ("media", "krita", "Krita", "Digital painting", _R, "krita"),
    ("media", "inkscape", "Inkscape", "Vector graphics", _R, "inkscape"),
    ("media", "blender", "Blender", "3D creation suite", _R, "blender"),
    ("media", "obs-studio", "OBS Studio", "Screen recording and live streaming", _R, "com.obsproject.Studio"),
    ("media", "kdenlive", "Kdenlive", "Video editing", _R, "kdenlive"),
    ("media", "vlc", "VLC", "Plays almost any media file", _R, "vlc"),
    ("media", "audacity", "Audacity", "Audio recording and editing", _R, "audacity"),
    ("media", "handbrake", "HandBrake", "Video converter", _R, "fr.handbrake.ghb"),

    ("utilities", "com.github.tchx84.Flatseal", "Flatseal", "Manage Flatpak app permissions", _F, "com.github.tchx84.Flatseal"),
    ("utilities", "gparted", "GParted", "Partition editor", _R, "gparted"),
    ("utilities", "bleachbit", "BleachBit", "Free disk space and clean caches", _R, "bleachbit"),
    ("utilities", "kdeconnect", "KDE Connect", "Connect your phone to your PC", _R, "kdeconnect"),
    ("utilities", "wine", "Wine", "Run Windows applications", _R, "wine"),
]


def catalog() -> list[App]:
    return [App(i, n, s, src, icon=ic, category=c) for (c, i, n, s, src, ic) in _ENTRIES]
