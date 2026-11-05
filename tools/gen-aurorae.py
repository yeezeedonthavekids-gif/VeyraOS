#!/usr/bin/env python3
"""Generate the VeyraOS Aurorae window decoration themes (light + dark).

    tools/gen-aurorae.py OUTDIR      (OUTDIR/Veyra, OUTDIR/VeyraDark)

Windows 11-like: flat title bar matching the window colour, title on the
left, 46x32 caption buttons on the right (minimize, maximize/restore,
close) with a red close hover, rounded top corners and a soft shadow.
QtSvg (used by Aurorae) has no filter support, so the shadow is built from
linear/radial gradients in a 9-slice frame.
"""
import os
import sys

P = 16      # shadow padding (px)
R = 8       # top corner radius
TITLE_H = 32
BTN_W, BTN_H = 46, 32
SHADOW_ALPHA = 0.20

THEMES = {
    "Veyra": dict(
        name="VeyraOS Light", title="243,243,247", title_inactive="243,243,247",
        border="#D6D6DE", text="26,27,38", text_inactive="128,130,150",
        glyph="#1A1B26", glyph_inactive="#8A8CA0",
        hover="#000000", hover_a=0.06, pressed_a=0.10,
    ),
    "VeyraDark": dict(
        name="VeyraOS Dark", title="32,32,40", title_inactive="32,32,40",
        border="#3A3A48", text="236,237,245", text_inactive="140,143,165",
        glyph="#ECEDF5", glyph_inactive="#7C7F98",
        hover="#FFFFFF", hover_a=0.08, pressed_a=0.05,
    ),
}


def rgb(s):
    return "rgb(%s)" % s


def decoration_svg(t):
    """9-slice frame for active and inactive windows (prefixes decoration/-inactive)."""
    W = 2 * (P + R) + 1  # canvas width per frame
    parts = []
    defs = []
    for prefix, fill in (("decoration", t["title"]), ("decoration-inactive", t["title_inactive"])):
        a = SHADOW_ALPHA if prefix == "decoration" else SHADOW_ALPHA * 0.6
        gid = prefix.replace("-", "_")
        # gradients
        defs.append(f'''
    <linearGradient id="{gid}_sh_top" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="{a*0.6:.3f}"/></linearGradient>
    <linearGradient id="{gid}_sh_bottom" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="{a:.3f}"/></linearGradient>
    <linearGradient id="{gid}_sh_left" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="{a*0.8:.3f}"/></linearGradient>
    <linearGradient id="{gid}_sh_right" x1="1" y1="0" x2="0" y2="0">
      <stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="{a*0.8:.3f}"/></linearGradient>
    <radialGradient id="{gid}_sh_corner" cx="0" cy="0" r="1" gradientUnits="objectBoundingBox">
      <stop offset="0" stop-color="#000" stop-opacity="{a*0.8:.3f}"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>''')
        bc = t["border"]
        C = P + R  # corner size
        # top-left: shadow quarter-disc centred on the window corner + rounded corner fill
        parts.append(f'''
  <g id="{prefix}-topleft">
    <rect x="0" y="0" width="{C}" height="{C}" fill="#000" fill-opacity="0"/>
    <circle cx="{C}" cy="{C}" r="{C}" fill="url(#{gid}_sh_c_tl)"/>
    <path d="M{P} {C} A{R} {R} 0 0 1 {C} {P} L{C} {C} Z" fill="{rgb(fill)}" stroke="{bc}" stroke-width="1"/>
  </g>
  <g id="{prefix}-top">
    <rect x="0" y="0" width="1" height="{P}" fill="url(#{gid}_sh_top)"/>
    <rect x="0" y="{P}" width="1" height="{R}" fill="{rgb(fill)}"/>
    <rect x="0" y="{P}" width="1" height="1" fill="{bc}"/>
  </g>
  <g id="{prefix}-topright">
    <rect x="0" y="0" width="{C}" height="{C}" fill="#000" fill-opacity="0"/>
    <circle cx="0" cy="{C}" r="{C}" fill="url(#{gid}_sh_c_tr)"/>
    <path d="M{R} {C} A{R} {R} 0 0 0 0 {P} L0 {C} Z" fill="{rgb(fill)}" stroke="{bc}" stroke-width="1"/>
  </g>
  <g id="{prefix}-left">
    <rect x="0" y="0" width="{P}" height="1" fill="url(#{gid}_sh_left)"/>
    <rect x="{P}" y="0" width="1" height="1" fill="{bc}"/>
  </g>
  <g id="{prefix}-center">
    <rect x="0" y="0" width="1" height="1" fill="{rgb(fill)}"/>
  </g>
  <g id="{prefix}-right">
    <rect x="1" y="0" width="{P}" height="1" fill="url(#{gid}_sh_right)"/>
    <rect x="0" y="0" width="1" height="1" fill="{bc}"/>
  </g>
  <g id="{prefix}-bottomleft">
    <rect x="0" y="0" width="{P+1}" height="{P+1}" fill="#000" fill-opacity="0"/>
    <circle cx="{P+1}" cy="0" r="{P}" fill="url(#{gid}_sh_c_bl)"/>
    <rect x="{P}" y="0" width="1" height="1" fill="{bc}"/>
  </g>
  <g id="{prefix}-bottom">
    <rect x="0" y="1" width="1" height="{P}" fill="url(#{gid}_sh_bottom)"/>
    <rect x="0" y="0" width="1" height="1" fill="{bc}"/>
  </g>
  <g id="{prefix}-bottomright">
    <rect x="0" y="0" width="{P+1}" height="{P+1}" fill="#000" fill-opacity="0"/>
    <circle cx="0" cy="0" r="{P}" fill="url(#{gid}_sh_c_br)"/>
    <rect x="0" y="0" width="1" height="1" fill="{bc}"/>
  </g>''')
        # per-corner radial gradients (userSpaceOnUse so they are centred correctly)
        for k, (cx, cy, rr) in {"tl": (C, C, C), "tr": (0, C, C), "bl": (P + 1, 0, P), "br": (0, 0, P)}.items():
            defs.append(f'''
    <radialGradient id="{gid}_sh_c_{k}" cx="{cx}" cy="{cy}" r="{rr}" gradientUnits="userSpaceOnUse">
      <stop offset="{(rr - P) / rr if rr > P else 0:.3f}" stop-color="#000" stop-opacity="{a*0.8:.3f}"/>
      <stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}">
  <defs>{"".join(defs)}
  </defs>{"".join(parts)}
</svg>
'''


def glyph(kind, color):
    cx, cy = BTN_W / 2, BTN_H / 2
    s = 'fill="none" stroke="%s" stroke-width="1" shape-rendering="crispEdges"' % color
    if kind == "minimize":
        return f'<line x1="{cx-5}" y1="{cy+0.5}" x2="{cx+5}" y2="{cy+0.5}" {s}/>'
    if kind == "maximize":
        return f'<rect x="{cx-4.5}" y="{cy-4.5}" width="9" height="9" rx="1.5" {s.replace("crispEdges", "geometricPrecision")}/>'
    if kind == "restore":
        g = s.replace("crispEdges", "geometricPrecision")
        return (f'<rect x="{cx-4.5}" y="{cy-2.5}" width="7" height="7" rx="1.2" {g}/>'
                f'<path d="M{cx-2.5} {cy-2.5} V{cy-3.3} Q{cx-2.5} {cy-4.5} {cx-1.3} {cy-4.5} H{cx+3.3} Q{cx+4.5} {cy-4.5} {cx+4.5} {cy-3.3} V{cy+1.3} Q{cx+4.5} {cy+2.5} {cx+3.3} {cy+2.5} H{cx+2.5}" {g}/>')
    if kind == "close":
        g = 'fill="none" stroke="%s" stroke-width="1.1" stroke-linecap="round"' % color
        return f'<path d="M{cx-5} {cy-5} L{cx+5} {cy+5} M{cx+5} {cy-5} L{cx-5} {cy+5}" {g}/>'
    raise ValueError(kind)


def button_svg(kind, t):
    close = kind == "close"
    states = {
        # state: (background colour, opacity, glyph colour)
        "active": (None, 0, t["glyph"]),
        "hover": ("#C42B1C" if close else t["hover"], 1 if close else t["hover_a"], "#FFFFFF" if close else t["glyph"]),
        "pressed": ("#B22A1C" if close else t["hover"], 0.9 if close else t["pressed_a"], "#FFFFFF" if close else t["glyph"]),
        "deactivated": (None, 0, t["glyph_inactive"]),
        "inactive": (None, 0, t["glyph_inactive"]),
        "hover-inactive": ("#C42B1C" if close else t["hover"], 1 if close else t["hover_a"], "#FFFFFF" if close else t["glyph"]),
        "pressed-inactive": ("#B22A1C" if close else t["hover"], 0.9 if close else t["pressed_a"], "#FFFFFF" if close else t["glyph"]),
        "deactivated-inactive": (None, 0, t["glyph_inactive"]),
    }
    groups = []
    for i, (st, (bg, op, gc)) in enumerate(states.items()):
        y = i * (BTN_H + 4)
        bgrect = (f'<rect x="0" y="0" width="{BTN_W}" height="{BTN_H}" fill="{bg}" fill-opacity="{op}"/>' if bg
                  else f'<rect x="0" y="0" width="{BTN_W}" height="{BTN_H}" fill="#000" fill-opacity="0"/>')
        groups.append(f'  <g id="{st}-center" transform="translate(0,{y})">{bgrect}{glyph(kind, gc)}</g>')
    H = len(states) * (BTN_H + 4)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{BTN_W}" height="{H}">
{chr(10).join(groups)}
</svg>
'''


def rc(theme, t):
    return f"""[General]
ActiveTextColor={t['text']}
InactiveTextColor={t['text_inactive']}
TitleAlignment=Left
TitleVerticalAlignment=Center
Animation=120
Shadow=true
UseTextShadow=false
HaloActive=false
HaloInactive=false

[Layout]
BorderLeft=1
BorderRight=1
BorderBottom=1
TitleEdgeTop=0
TitleEdgeBottom=0
TitleEdgeLeft=12
TitleEdgeRight=0
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized=12
TitleEdgeRightMaximized=0
TitleBorderLeft=8
TitleBorderRight=8
TitleHeight={TITLE_H - 1}
ButtonWidth={BTN_W}
ButtonWidthMinimize={BTN_W}
ButtonWidthMaximizeRestore={BTN_W}
ButtonWidthClose={BTN_W}
ButtonHeight={BTN_H - 1}
ButtonSpacing=0
ButtonMarginTop=0
ButtonMarginTopMaximized=0
ExplicitButtonSpacer=8
PaddingTop={P}
PaddingBottom={P}
PaddingLeft={P}
PaddingRight={P}
"""


def main():
    out = sys.argv[1]
    for theme, t in THEMES.items():
        d = os.path.join(out, theme)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "decoration.svg"), "w").write(decoration_svg(t))
        for k in ("minimize", "maximize", "restore", "close"):
            open(os.path.join(d, f"{k}.svg"), "w").write(button_svg(k, t))
        open(os.path.join(d, f"{theme}rc"), "w").write(rc(theme, t))
        open(os.path.join(d, "metadata.desktop"), "w").write(f"""[Desktop Entry]
Name={t['name']}
Comment=Windows-style window decoration for VeyraOS
X-KDE-PluginInfo-Author=VeyraOS Project
X-KDE-PluginInfo-Name={theme}
X-KDE-PluginInfo-Version=1.0
X-KDE-PluginInfo-Category=
X-KDE-PluginInfo-License=GPL-2.0-or-later
X-KDE-PluginInfo-EnabledByDefault=true
""")
        print("wrote", d)


if __name__ == "__main__":
    main()
