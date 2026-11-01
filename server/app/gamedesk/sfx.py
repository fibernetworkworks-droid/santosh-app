"""v0.415 game sound effects made in CODE (Hoola Game Engine plan Phase 4): no model, no money, no network.

A small synthesiser in the spirit of the classic retro sound generators: one oscillator (square / saw / triangle /
sine / noise) with a pitch slide, vibrato, an arpeggio jump, an attack / sustain / decay envelope and a low-pass. Each
PRESET is a family of sounds (jump, coin, hit, explosion, powerup, laser, blip, click, hurt, select); the SEED picks
one member of the family, so the same (preset, seed) always gives the same bytes - a sound can be remade exactly, and
"another one like it" is just the next seed. Output: 16-bit mono WAV at 22,050 Hz, peak-normalised to -1 dBFS."""
from __future__ import annotations

import io
import math
import random
import struct
import wave
from typing import Any

RATE = 22050
PRESETS: dict[str, dict[str, Any]] = {
    # wave, base Hz (lo, hi), slide (lo, hi) octaves/sec, length s (lo, hi), attack, decay share, vibrato, arp, lowpass
    "jump": {"wave": "square", "hz": (260, 420), "slide": (1.6, 3.2), "len": (0.16, 0.28), "attack": 0.0, "decay": 0.7},
    "coin": {"wave": "square", "hz": (820, 1100), "slide": (0, 0), "len": (0.18, 0.32), "attack": 0.0, "decay": 0.6,
             "arp": (1.33, 1.6), "arp_at": 0.32},
    "hit": {"wave": "noise", "hz": (500, 900), "slide": (-3.0, -1.5), "len": (0.08, 0.16), "attack": 0.0, "decay": 0.9,
            "lowpass": 0.55},
    "explosion": {"wave": "noise", "hz": (90, 180), "slide": (-1.2, -0.4), "len": (0.5, 0.9), "attack": 0.0, "decay": 0.85,
                  "lowpass": 0.35},
    "powerup": {"wave": "square", "hz": (300, 480), "slide": (1.0, 2.2), "len": (0.35, 0.6), "attack": 0.0, "decay": 0.5,
                "vib": (6, 10, 0.06)},
    "laser": {"wave": "saw", "hz": (900, 1500), "slide": (-4.5, -2.5), "len": (0.12, 0.24), "attack": 0.0, "decay": 0.8},
    "blip": {"wave": "square", "hz": (600, 900), "slide": (0, 0), "len": (0.05, 0.09), "attack": 0.0, "decay": 0.5},
    "click": {"wave": "triangle", "hz": (1200, 1800), "slide": (-1, 0), "len": (0.025, 0.05), "attack": 0.0, "decay": 0.9},
    "hurt": {"wave": "saw", "hz": (180, 300), "slide": (-2.4, -1.2), "len": (0.18, 0.3), "attack": 0.0, "decay": 0.8,
             "lowpass": 0.7},
    "select": {"wave": "sine", "hz": (520, 700), "slide": (0, 0), "len": (0.12, 0.2), "attack": 0.01, "decay": 0.6,
               "arp": (1.25, 1.5), "arp_at": 0.45},
}


class SfxError(Exception):
    pass


def params(preset: str, seed: int) -> dict[str, Any]:
    if preset not in PRESETS:
        raise SfxError(f"sound = {', '.join(PRESETS)}")
    p = PRESETS[preset]
    rnd = random.Random(f"{preset}:{int(seed)}")
    u = lambda lo_hi: rnd.uniform(*lo_hi)        # noqa: E731
    out = {"preset": preset, "seed": int(seed), "wave": p["wave"], "hz": round(u(p["hz"]), 1), "slide": round(u(p["slide"]), 3),
           "len": round(u(p["len"]), 3), "attack": p.get("attack", 0.0), "decay": p.get("decay", 0.7),
           "lowpass": p.get("lowpass", 1.0)}
    if "arp" in p:
        out["arp"], out["arp_at"] = round(u(p["arp"]), 3), p.get("arp_at", 0.4)
    if "vib" in p:
        lo, hi, depth = p["vib"]
        out["vib_hz"], out["vib_depth"] = round(rnd.uniform(lo, hi), 2), depth
    return out


def render(pr: dict[str, Any]) -> bytes:
    """Parameters -> WAV bytes. Deterministic: noise comes from a generator seeded by the same (preset, seed)."""
    n = max(1, int(pr["len"] * RATE))
    rnd = random.Random(f"noise:{pr['preset']}:{pr['seed']}")
    phase = 0.0
    noise_val = 0.0
    lp = 0.0
    alpha = max(0.02, min(1.0, float(pr.get("lowpass", 1.0))))
    att = max(1, int(pr.get("attack", 0.0) * RATE))
    dec_start = int(n * (1 - float(pr.get("decay", 0.7))))
    samples = []
    for i in range(n):
        t = i / RATE
        hz = pr["hz"] * (2 ** (pr["slide"] * t))
        if pr.get("arp") and t >= pr["len"] * pr.get("arp_at", 0.4):
            hz *= pr["arp"]
        if pr.get("vib_hz"):
            hz *= 1 + pr["vib_depth"] * math.sin(2 * math.pi * pr["vib_hz"] * t)
        hz = max(20.0, min(hz, RATE / 2.2))
        prev = phase
        phase = (phase + hz / RATE) % 1.0
        w = pr["wave"]
        if w == "square":
            v = 1.0 if phase < 0.5 else -1.0
        elif w == "saw":
            v = 2 * phase - 1
        elif w == "triangle":
            v = 4 * abs(phase - 0.5) - 1
        elif w == "sine":
            v = math.sin(2 * math.pi * phase)
        else:                                            # noise: a new random value each cycle (pitched noise)
            if phase < prev:
                noise_val = rnd.uniform(-1, 1)
            v = noise_val
        lp += alpha * (v - lp)                           # one-pole low-pass
        env = min(1.0, i / att) if i < att else 1.0
        if i >= dec_start:
            env *= max(0.0, 1 - (i - dec_start) / max(1, n - dec_start))
        samples.append(lp * env)
    peak = max(1e-9, max(abs(x) for x in samples))
    gain = (10 ** (-1 / 20)) / peak                      # -1 dBFS
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x * gain)) * 32767)) for x in samples))
    return buf.getvalue()


def make(preset: str, seed: int = 1) -> tuple[bytes, dict[str, Any]]:
    pr = params(preset, seed)
    return render(pr), pr
