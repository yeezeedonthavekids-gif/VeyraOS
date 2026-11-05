#!/usr/bin/env python3
"""Render VeyraOS raster branding assets from the SVG sources.

    tools/gen-branding.py            (writes into src/branding/...)

Needs: rsvg-convert, Pillow, the Inter font (for the wordmark), and the
generated wallpapers (tools/gen-wallpapers.py) for the GRUB background.
Outputs are committed so the ISO build does not need these tools.
"""
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

TOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BR = os.path.join(TOP, "src", "branding")
LOGO = os.path.join(BR, "logo")
MARK = os.path.join(LOGO, "veyraos-mark.svg")
MARK_DARK = os.path.join(LOGO, "veyraos-mark-on-dark.svg")
ACCENT = (124, 92, 255)


def svg2png(svg, out, w, h=None):
    cmd = ["rsvg-convert", "-w", str(w)]
    if h:
        cmd += ["-h", str(h)]
    subprocess.run(cmd + [svg, "-o", out], check=True)


def wordmark_svg(fill):
    mark = open(MARK_DARK if fill.upper() == "#FFFFFF" else MARK).read()
    inner = mark.split(">", 1)[1].rsplit("</svg>", 1)[0]
    inner = inner.replace("<title>VeyraOS</title>", "")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 256" width="900" height="256">
  <g transform="translate(0,0)">{inner}</g>
  <text x="290" y="172" font-family="Inter" font-weight="600" font-size="128" letter-spacing="-2" fill="{fill}">Veyra<tspan font-weight="300">OS</tspan></text>
</svg>'''


def rounded(size, radius, fill, outline=None, width=1):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=fill, outline=outline, width=width)
    return im


def nine_slice(im, prefix, r):
    """Split a rounded rect image into GRUB 9-slice pixmaps (nw n ne w c e sw s se)."""
    w, h = im.size
    boxes = {
        "nw": (0, 0, r, r), "n": (r, 0, w - r, r), "ne": (w - r, 0, w, r),
        "w": (0, r, r, h - r), "c": (r, r, w - r, h - r), "e": (w - r, r, w, h - r),
        "sw": (0, h - r, r, h), "s": (r, h - r, w - r, h), "se": (w - r, h - r, w, h),
    }
    for k, b in boxes.items():
        im.crop(b).save(f"{prefix}{k}.png")


def icon_glyph(kind, size=64):
    """Simple line icons for the GRUB menu (white strokes)."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    white = (230, 232, 245, 255)
    lw = max(3, s // 14)
    if kind == "restart":
        d.arc([s * .18, s * .18, s * .82, s * .82], 40, 330, fill=white, width=lw)
        d.polygon([(s * .70, s * .10), (s * .86, s * .30), (s * .62, s * .34)], fill=white)
    elif kind == "shutdown":
        d.arc([s * .18, s * .2, s * .82, s * .84], 300, 240, fill=white, width=lw)
        d.line([s * .5, s * .1, s * .5, s * .5], fill=white, width=lw)
    elif kind == "settings":
        d.ellipse([s * .3, s * .3, s * .7, s * .7], outline=white, width=lw)
        for i in range(8):
            import math
            a = i * math.pi / 4
            x0, y0 = s / 2 + math.cos(a) * s * .26, s / 2 + math.sin(a) * s * .26
            x1, y1 = s / 2 + math.cos(a) * s * .40, s / 2 + math.sin(a) * s * .40
            d.line([x0, y0, x1, y1], fill=white, width=lw)
    elif kind == "recovery":
        d.rounded_rectangle([s * .15, s * .22, s * .85, s * .78], radius=s * .08, outline=white, width=lw)
        d.line([s * .28, s * .40, s * .40, s * .50, s * .28, s * .60], fill=white, width=lw)
        d.line([s * .48, s * .62, s * .68, s * .62], fill=white, width=lw)
    elif kind == "memtest":
        d.rounded_rectangle([s * .2, s * .28, s * .8, s * .72], radius=s * .05, outline=white, width=lw)
        for i in range(4):
            x = s * (.28 + i * .15)
            d.line([x, s * .72, x, s * .86], fill=white, width=lw)
            d.line([x, s * .14, x, s * .28], fill=white, width=lw)
    return im


def main():
    tmp = tempfile.mkdtemp()
    # --- wordmarks ------------------------------------------------------------
    for name, fill in (("veyraos-wordmark.svg", "#1B1D2E"), ("veyraos-wordmark-on-dark.svg", "#FFFFFF")):
        with open(os.path.join(LOGO, name), "w") as f:
            f.write(wordmark_svg(fill))

    # --- Plymouth ---------------------------------------------------------------
    ply = os.path.join(BR, "plymouth", "veyra")
    svg2png(MARK_DARK, os.path.join(ply, "logo.png"), 160)
    dot = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse([13, 13, 27, 27], fill=(255, 255, 255, 255))
    glow = dot.filter(ImageFilter.GaussianBlur(4))
    tint = Image.new("RGBA", dot.size, ACCENT + (0,))
    tint.putalpha(glow.getchannel("A").point(lambda a: int(a * 0.8)))
    Image.alpha_composite(tint, dot).crop((8, 8, 32, 32)).save(os.path.join(ply, "dot.png"))
    rounded((360, 44), 10, (255, 255, 255, 30), (255, 255, 255, 90), 2).save(os.path.join(ply, "entry.png"))
    b = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse([1, 1, 8, 8], fill=(255, 255, 255, 255))
    b.save(os.path.join(ply, "bullet.png"))

    # --- GRUB -----------------------------------------------------------------
    grub = os.path.join(BR, "grub", "veyra")
    wp = os.path.join(BR, "wallpapers", "Veyra", "contents", "images_dark", "1920x1080.jpg")
    bg = Image.open(wp).convert("RGB").filter(ImageFilter.GaussianBlur(6))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    bg.save(os.path.join(grub, "background.png"), optimize=True)
    svg2png(MARK_DARK, os.path.join(grub, "logo.png"), 96)
    sel = rounded((24, 24), 8, ACCENT + (110,), ACCENT + (200,), 1)
    nine_slice(sel, os.path.join(grub, "select_"), 8)
    box = rounded((24, 24), 8, (8, 10, 24, 235))
    nine_slice(box, os.path.join(grub, "terminal_box_"), 8)
    thumb = rounded((6, 24), 3, (200, 200, 230, 160))
    for k, bb in {"n": (0, 0, 6, 3), "c": (0, 3, 6, 21), "s": (0, 21, 6, 24)}.items():
        thumb.crop(bb).save(os.path.join(grub, f"scroll_thumb_{k}.png"))
    icons = os.path.join(grub, "icons")
    svg2png(MARK_DARK, os.path.join(icons, "veyra.png"), 64)
    for k in ("restart", "shutdown", "settings", "recovery", "memtest"):
        icon_glyph(k).save(os.path.join(icons, f"{k}.png"))

    # --- hicolor icons ----------------------------------------------------------
    hic = os.path.join(BR, "icons", "hicolor")
    for size in (16, 22, 24, 32, 48, 64, 128, 256, 512):
        d = os.path.join(hic, f"{size}x{size}", "apps")
        os.makedirs(d, exist_ok=True)
        svg2png(MARK, os.path.join(d, "veyraos.png"), size)
    print("branding assets written")


if __name__ == "__main__":
    main()
