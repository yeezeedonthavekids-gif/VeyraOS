#!/usr/bin/env python3
"""Generate the VeyraOS default wallpapers ("Aurora") procedurally.

Original artwork: soft, flowing light ribbons over a deep gradient — the
VeyraOS visual signature. Deterministic (fixed seeds) so the output is
reproducible. Requires numpy + Pillow.

    tools/gen-wallpapers.py OUTDIR [--sizes 3840x2160,2560x1440,1920x1080] [--preview]

Writes OUTDIR/Veyra/contents/images/WxH.jpg (light) and images_dark/WxH.jpg
(dark), in Plasma wallpaper package layout.
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


THEMES = {
    "dark": {
        "bg_top": "#0B0F2A", "bg_bottom": "#05060F", "bg_glow": "#1E1B4B",
        "ribbons": ["#7C3AED", "#22D3EE", "#6366F1", "#C026D3", "#38BDF8"],
        "ribbon_gain": 1.0, "blend": "screen",
    },
    "light": {
        "bg_top": "#EEF0FB", "bg_bottom": "#F8F7FD", "bg_glow": "#E0E7FF",
        "ribbons": ["#8B5CF6", "#06B6D4", "#6366F1", "#D946EF", "#0EA5E9"],
        "ribbon_gain": 0.75, "blend": "multiply_soft",
    },
}

# Ribbon geometry, in normalized coordinates (x in [0,1], y in [0,1]).
# Each: (base_y, amplitude, frequency, phase, width, tilt, color_index, strength)
RIBBONS = [
    (0.62, 0.10, 1.10, 0.40, 0.050, -0.22, 0, 1.00),
    (0.58, 0.12, 0.95, 1.30, 0.030, -0.18, 1, 0.85),
    (0.66, 0.08, 1.35, 2.20, 0.075, -0.25, 2, 0.70),
    (0.55, 0.14, 0.80, 3.10, 0.018, -0.15, 3, 0.65),
    (0.70, 0.07, 1.60, 4.00, 0.022, -0.28, 4, 0.60),
]


def render(theme_name, width, height, seed=7):
    t = THEMES[theme_name]
    rng = np.random.default_rng(seed)
    # Supersample-free: compute directly at target resolution in float32.
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    aspect = width / height
    x = xs / width
    y = ys / height

    # Background: vertical gradient + soft radial glow behind the ribbons
    top, bottom, glow = hex2rgb(t["bg_top"]), hex2rgb(t["bg_bottom"]), hex2rgb(t["bg_glow"])
    img = top[None, None, :] * (1 - y[..., None]) + bottom[None, None, :] * y[..., None]
    gx, gy = 0.58, 0.60
    r2 = ((x - gx) * aspect) ** 2 + (y - gy) ** 2
    g = np.exp(-r2 / 0.18)[..., None]
    img = img * (1 - 0.65 * g) + glow[None, None, :] * 0.65 * g

    # Ribbons: gaussian bands around sinusoidal centre lines with a sheen
    light = np.zeros_like(img)
    layers = []
    for (by, amp, freq, ph, w, tilt, ci, strength) in RIBBONS:
        col = hex2rgb(t["ribbons"][ci])
        centre = by + tilt * (x - 0.5) + amp * np.sin(2 * np.pi * freq * x + ph) \
            + 0.25 * amp * np.sin(2 * np.pi * 2.7 * freq * x + 1.7 * ph)
        # width breathes along x so ribbons look like folded silk
        ww = w * (0.65 + 0.35 * np.sin(2 * np.pi * 0.6 * x + ph * 1.3) ** 2)
        d = (y - centre) / ww
        band = np.exp(-d ** 2)
        # fine filaments inside the band
        fil = 0.5 + 0.5 * np.cos(d * 6.0 + 3 * np.sin(2 * np.pi * x * 1.5 + ph))
        sheen = band * (0.55 + 0.45 * fil)
        # fade ribbons at the far left so the desktop icons area stays calm
        fade = np.clip((x - 0.02) / 0.35, 0, 1) ** 1.2
        light += (sheen * fade * strength)[..., None] * col[None, None, :]
        layers.append((np.clip(sheen * fade * strength, 0, 1), col))

    light *= t["ribbon_gain"]
    if t["blend"] == "screen":
        out = 1 - (1 - img) * (1 - np.clip(light, 0, 1))
        # bloom: blurred highlights added back
        bloom = Image.fromarray((np.clip(light, 0, 1) * 255).astype(np.uint8))
        bloom = bloom.filter(ImageFilter.GaussianBlur(radius=max(4, width // 90)))
        out = 1 - (1 - out) * (1 - 0.55 * np.asarray(bloom, dtype=np.float32) / 255.0)
    else:
        # light theme: alpha-composite each ribbon as a translucent pastel
        # silk band, with a soft coloured haze around it
        out = img.copy()
        white = np.ones(3, dtype=np.float32)
        for alpha, col in layers:
            haze = Image.fromarray((alpha * 255).astype(np.uint8))
            haze = np.asarray(haze.filter(ImageFilter.GaussianBlur(radius=max(4, width // 60))),
                              dtype=np.float32) / 255.0
            c = 0.80 * col + 0.20 * white
            a = np.clip(0.62 * alpha + 0.30 * haze, 0, 0.85)[..., None]
            out = out * (1 - a) + c[None, None, :] * a

    # Vignette + film grain (prevents banding on 8-bit panels)
    v = 1 - 0.18 * (((x - 0.5) * aspect / aspect) ** 2 + (y - 0.5) ** 2) * 2
    if theme_name == "dark":
        out = out * v[..., None]
    grain = rng.normal(0, 1.2 / 255.0, size=out.shape[:2]).astype(np.float32)
    out = np.clip(out + grain[..., None], 0, 1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--sizes", default="3840x2160,2560x1440,1920x1080,1920x1200")
    ap.add_argument("--preview", action="store_true", help="also write small previews")
    a = ap.parse_args()
    pkg = os.path.join(a.outdir, "Veyra")
    for theme, sub in (("light", "images"), ("dark", "images_dark")):
        d = os.path.join(pkg, "contents", sub)
        os.makedirs(d, exist_ok=True)
        for s in a.sizes.split(","):
            w, h = (int(v) for v in s.split("x"))
            im = render(theme, w, h)
            p = os.path.join(d, f"{w}x{h}.jpg")
            im.save(p, quality=90, optimize=True, progressive=True, subsampling=0)
            print("wrote", p)
        render(theme, 800, 450).save(os.path.join(pkg, "contents", f"screenshot{'_dark' if theme == 'dark' else ''}.jpg"), quality=88)


if __name__ == "__main__":
    main()
