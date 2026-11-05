// VeyraOS default desktop layout: a Windows 11-style bottom taskbar with the
// Start button and pinned/running apps centred, system tray and clock on the
// right, and "peek at desktop" in the far corner.

var panel = new Panel;
panel.location = "bottom";
panel.height = 2 * Math.ceil(gridUnit * 2.75 / 2);   // ~48 px at default scale
panel.hiding = "none";
panel.alignment = "center";
panel.lengthMode = "fill";
// Plasma >= 6.0: Windows-style edge-to-edge taskbar instead of a floating one
try { panel.floating = false; } catch (e) {}

// Left flexible spacer: together with the right one it centres Start + tasks
var leftSpacer = panel.addWidget("org.kde.plasma.panelspacer");
leftSpacer.currentConfigGroup = ["General"];
leftSpacer.writeConfig("expanding", true);

// Start menu
var kickoff = panel.addWidget("org.kde.plasma.kickoff");
kickoff.currentConfigGroup = ["Shortcuts"];
kickoff.writeConfig("global", "Alt+F1");
kickoff.currentConfigGroup = ["General"];
kickoff.writeConfig("icon", "veyraos-start");
kickoff.writeConfig("favoritesDisplay", 0);          // pinned apps as a grid
kickoff.writeConfig("applicationsDisplay", 1);       // all apps as a list
kickoff.writeConfig("showActionButtonCaptions", true);
kickoff.writeConfig("primaryActions", 1);            // Sleep/Restart/Shut down buttons
kickoff.writeConfig("favorites", [
    "preferred://browser",
    "applications:org.kde.dolphin.desktop",
    "applications:veyra-software.desktop",
    "applications:systemsettings.desktop",
    "applications:veyra-control.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:steam.desktop",
    "applications:net.lutris.Lutris.desktop",
    "applications:org.kde.kate.desktop",
    "applications:org.kde.spectacle.desktop",
    "applications:org.kde.kcalc.desktop",
    "applications:org.kde.plasma-systemmonitor.desktop"
].join(","));

// Taskbar (icons only, like Windows 11)
var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "preferred://browser",
    "applications:veyra-software.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:steam.desktop"
].join(","));
tasks.writeConfig("showOnlyCurrentDesktop", false);
tasks.writeConfig("groupedTaskVisualization", 1);     // click on a group shows window previews
tasks.writeConfig("indicateAudioStreams", true);
tasks.writeConfig("fill", false);
tasks.writeConfig("iconSpacing", 1);

var rightSpacer = panel.addWidget("org.kde.plasma.panelspacer");
rightSpacer.currentConfigGroup = ["General"];
rightSpacer.writeConfig("expanding", true);

// System tray
panel.addWidget("org.kde.plasma.systemtray");

// Clock: time above the date, like Windows
var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", true);
clock.writeConfig("dateDisplayFormat", "BelowTime");
clock.writeConfig("dateFormat", "shortDate");
clock.writeConfig("showSeconds", 0);

// Thin "peek at desktop" button in the corner
panel.addWidget("org.kde.plasma.showdesktop");

// Desktop: icons on the desktop (folder view) with the VeyraOS wallpaper
var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    var d = desktopsArray[j];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/Veyra/");
    d.writeConfig("FillMode", 2);   // scaled and cropped
}
