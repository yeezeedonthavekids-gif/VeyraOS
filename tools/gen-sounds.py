#!/usr/bin/env python3
"""Synthesize the VeyraOS sound theme (original sounds; deterministic).

    tools/gen-sounds.py OUTDIR

Writes OUTDIR/veyra/{index.theme, stereo/*.oga} following the freedesktop
sound theme specification. Requires numpy and ffmpeg (for Ogg Vorbis).
"""
import os
import subprocess
import sys
import wave

import numpy as np

SR = 48000


def note(name):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    n = names[name[0]]
    i = 1
    if name[i] in "#b":
        n += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    return 440.0 * 2 ** ((n + (octave - 4) * 12) / 12)


def bell(freq, dur, amp=1.0, decay=3.0, bright=1.0):
    t = np.arange(int(SR * dur)) / SR
    # soft mallet: slightly inharmonic partials like a glass/marimba blend
    partials = [(1.0, 1.0), (2.0, 0.35 * bright), (3.01, 0.12 * bright), (4.2, 0.06 * bright), (5.4, 0.025 * bright)]
    sig = np.zeros_like(t)
    for ratio, a in partials:
        sig += a * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t * decay * (1 + 0.6 * (ratio - 1)))
    attack = np.clip(t / 0.006, 0, 1)
    return amp * sig * attack


def place(buf, sig, at):
    i = int(at * SR)
    end = min(len(buf), i + len(sig))
    buf[i:end] += sig[: end - i]


def reverb(x, mix=0.22):
    # fast feedback comb filters via IIR in numpy chunks
    tail = np.zeros(len(x) + int(SR * 1.2))
    tail[: len(x)] = x
    wet = np.zeros_like(tail)
    for delay_ms, g in ((29.7, 0.70), (37.1, 0.66), (41.1, 0.63), (43.7, 0.60)):
        d = int(SR * delay_ms / 1000)
        y = tail.copy()
        for start in range(d, len(y), d):
            y[start:start + d] += g * y[start - d:start][: len(y[start:start + d])]
        wet += y
    wet /= 4
    # gentle low-pass on the wet signal
    k = np.ones(24) / 24
    wet = np.convolve(wet, k, mode="same")
    res = tail * (1 - mix) + wet * mix
    return res


def finish(x, peak_db=-6.0):
    x = reverb(x)
    # trim trailing silence
    thr = 10 ** (-60 / 20) * np.max(np.abs(x))
    nz = np.nonzero(np.abs(x) > thr)[0]
    x = x[: nz[-1] + int(0.02 * SR)] if len(nz) else x
    fade = min(len(x), int(0.03 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    return np.stack([x, x], axis=1)  # stereo


def seq(notes, step, dur=1.2, amp=None, decay=3.0, bright=1.0, length=None):
    total = length or (step * len(notes) + dur)
    buf = np.zeros(int(SR * total))
    for i, n in enumerate(notes):
        a = amp[i] if amp else 1.0
        place(buf, bell(note(n), dur, a, decay, bright), i * step)
    return buf


def noise_sweep(dur, f0, f1, amp=0.5):
    rng = np.random.default_rng(3)
    n = rng.standard_normal(int(SR * dur))
    # crude moving-average band shaping that sweeps from f0 to f1
    out = np.zeros_like(n)
    t = np.arange(len(n)) / SR
    for i, w in enumerate(np.linspace(SR / f0, SR / f1, 8)):
        w = max(2, int(w))
        seg = slice(i * len(n) // 8, (i + 1) * len(n) // 8)
        out[seg] = np.convolve(n, np.ones(w) / w, mode="same")[seg]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return amp * out * env


def shutter():
    buf = np.zeros(int(SR * 0.4))
    place(buf, noise_sweep(0.12, 6000, 1500, 0.9), 0.0)
    place(buf, bell(note("E6"), 0.25, 0.3, 18.0), 0.02)
    return buf


SOUNDS = {
    # name: generator
    "desktop-login": lambda: seq(["E5", "G5", "B5", "D6", "G6"], 0.11, 1.6, [0.8, 0.8, 0.85, 0.9, 0.6], 2.2),
    "desktop-logout": lambda: seq(["D6", "B5", "G5", "E5"], 0.12, 1.4, [0.7, 0.75, 0.8, 0.9], 2.6),
    "message-new-instant": lambda: seq(["G5", "C6"], 0.09, 0.8, [0.8, 1.0], 4.5),
    "message": lambda: seq(["E5", "A5"], 0.10, 0.8, [0.8, 1.0], 4.5),
    "dialog-information": lambda: seq(["A5"], 0.1, 0.9, None, 4.0),
    "dialog-question": lambda: seq(["E5", "A5"], 0.13, 0.9, [0.9, 0.8], 4.0),
    "dialog-warning": lambda: seq(["D5", "D5"], 0.16, 0.7, [1.0, 0.8], 5.0, 0.7),
    "dialog-error": lambda: seq(["F4", "C4"], 0.14, 0.8, [1.0, 1.0], 5.0, 0.5),
    "bell": lambda: seq(["C6"], 0.1, 0.5, None, 7.0),
    "device-added": lambda: seq(["C5", "G5"], 0.09, 0.7, [0.85, 1.0], 5.0),
    "device-removed": lambda: seq(["G5", "C5"], 0.09, 0.7, [1.0, 0.85], 5.0),
    "power-plug": lambda: seq(["E5", "B5"], 0.08, 0.6, [0.8, 1.0], 6.0),
    "power-unplug": lambda: seq(["B5", "E5"], 0.08, 0.6, [1.0, 0.8], 6.0),
    "battery-low": lambda: seq(["A4", "A4", "A4"], 0.18, 0.5, [1.0, 0.9, 0.8], 6.0, 0.6),
    "complete": lambda: seq(["C5", "E5", "G5", "C6"], 0.07, 0.9, [0.7, 0.75, 0.8, 1.0], 4.0),
    "outcome-success": lambda: seq(["G5", "B5", "D6"], 0.07, 0.9, [0.8, 0.85, 1.0], 4.0),
    "outcome-failure": lambda: seq(["E5", "C5"], 0.12, 0.8, [1.0, 1.0], 5.0, 0.6),
    "audio-volume-change": lambda: seq(["A6"], 0.1, 0.12, None, 30.0, 0.4),
    "trash-empty": lambda: noise_sweep(0.45, 2000, 300, 0.6),
    "screen-capture": lambda: shutter(),
    "service-login": lambda: seq(["G5", "D6"], 0.1, 0.9, [0.8, 1.0], 3.5),
    "service-logout": lambda: seq(["D6", "G5"], 0.1, 0.9, [1.0, 0.8], 3.5),
    "camera-shutter": lambda: noise_sweep(0.12, 6000, 1500, 0.9),
    "window-attention": lambda: seq(["C6", "E6"], 0.08, 0.6, [0.8, 1.0], 5.0),
}


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    out = os.path.join(sys.argv[1], "veyra")
    stereo = os.path.join(out, "stereo")
    os.makedirs(stereo, exist_ok=True)
    with open(os.path.join(out, "index.theme"), "w") as f:
        f.write("[Sound Theme]\nName=VeyraOS\nComment=VeyraOS system sounds\n"
                "Inherits=ocean,freedesktop\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n")
    for name, gen in SOUNDS.items():
        x = gen()
        if name == "screen-capture":
            x = x[: int(0.4 * SR)]
        data = finish(x, -7.0 if name not in ("audio-volume-change",) else -12.0)
        wav = os.path.join(stereo, name + ".wav")
        oga = os.path.join(stereo, name + ".oga")
        write_wav(wav, data)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "5",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", oga], check=True)
        os.remove(wav)
        print("wrote", oga)


if __name__ == "__main__":
    main()
