"""v0.128.1 Colour for apps: a full palette from ANY one colour (her words "neela", "maroon aur sunehra", a hex, or her logo),
in 6 harmony schemes (complementary, analogous, triadic, split, tetradic, monochrome), in light AND dark mode, with text
contrast fixed by code (ink >= 7:1 on the background, button text picked for the button colour). 200 named palettes =
the website library's 50 hand-made ones + 150 generated (25 hues x 6 schemes)."""
from __future__ import annotations

import colorsys
import re
from functools import lru_cache
from typing import Any

from ..brand import rules as BR
from ..site import taxonomy as ST

SCHEMES = {"complementary": 180, "analogous": 32, "triadic": 120, "split": 150, "tetradic": 90, "monochrome": 0}
HUES = {"crimson": 352, "red": 4, "coral": 12, "tomato": 18, "orange": 28, "saffron": 34, "amber": 42, "gold": 46, "mustard": 50,
        "olive": 66, "lime": 84, "green": 130, "emerald": 152, "mint": 160, "teal": 176, "cyan": 188, "sky": 200, "azure": 210,
        "blue": 220, "royal": 228, "indigo": 240, "violet": 260, "purple": 276, "magenta": 300, "rose": 330}
MORE_NAMES = {"laal": "#D32F2F", "maroon": "#7A1F3D", "mehroon": "#7A1F3D", "narangi": "#F57C00", "kesariya": "#F57C00",
              "haldi": "#E8A317", "mehendi": "#5B7B2A", "mehndi": "#5B7B2A", "tota": "#3FA34D", "dhaani": "#7CB342",
              "firozi": "#14A3A3", "firoza": "#14A3A3", "rani": "#C2185B", "jamuni": "#5E2B7E", "baingani": "#6A1B9A",
              "chocolate": "#5D3A1A", "coffee": "#6F4E37", "bhura": "#6D4C41", "chandi": "#9E9E9E", "silver": "#9E9E9E",
              "sona": "#C9A227", "sunehri": "#C9A227", "gehra neela": "#0B2545", "halka neela": "#64B5F6", "aasmani": "#4FC3F7",
              "lavender": "#8E7CC3", "peach": "#F4A582", "mint": "#3EB489", "olive": "#6B7A2A", "wine": "#722F37",
              "turquoise": "#1AA6A6", "beige": "#D8C3A5", "ivory": "#F6F1E1", "charcoal": "#2B2B2B", "slate": "#465A6B",
              "neon green": "#39FF14", "neon": "#39FF14", "rust": "#B7410E", "terracotta": "#C8643B", "plum": "#6E2A5E",
              "लाल": "#D32F2F", "नीला": "#1565C0", "हरा": "#2E7D32", "पीला": "#F9C80E", "केसरी": "#F57C00", "गुलाबी": "#E91E63",
              "काला": "#111111", "सफेद": "#FFFFFF", "सुनहरा": "#C9A227", "बैंगनी": "#6A1B9A", "मरून": "#7A1F3D", "निळा": "#1565C0",
              "हिरवा": "#2E7D32", "पिवळा": "#F9C80E", "भगवा": "#F57C00"}


def _hex(c: str) -> str:
    return BR.parse_color(c) or MORE_NAMES.get((c or "").strip().lower(), "")


def hsl(h: str) -> tuple[float, float, float]:
    r, g, b = (x / 255 for x in BR.rgb(h))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, ss, ll


def from_hsl(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, max(0, min(1, l)), max(0, min(1, s)))
    return BR.to_hex(r * 255, g * 255, b * 255)


def find_colors(text: str) -> list[str]:
    """Colours named in her words (Hinglish / Hindi / Marathi / English / hex), in order."""
    t = (text or "").lower()
    found: list[tuple[int, str]] = []
    for m in re.finditer(r"#?[0-9a-f]{6}\b", t):
        found.append((m.start(), "#" + m.group(0).lstrip("#").upper()))
    names = {**{k: v for k, v in BR.NAMED.items()}, **MORE_NAMES}
    for name in sorted(names, key=len, reverse=True):
        for m in re.finditer(rf"(?<![\wऀ-ॿ]){re.escape(name)}(?![\wऀ-ॿ])", t):
            if not any(a <= m.start() < a + 12 for a, _ in found):
                found.append((m.start(), names[name]))
    return [c for _, c in sorted(found)]


def _moods(h: float, s: float, l: float, dark: bool) -> list[str]:
    m = ["dark"] if dark else []
    m.append("warm" if (h < 70 or h > 320) else "cool")
    m.append("bright" if s > 0.62 else "calm")
    if 90 <= h <= 170:
        m.append("green")
    if 190 <= h <= 250:
        m += ["blue", "trust"]
    if 260 <= h <= 300:
        m.append("tech")
    if 20 <= h <= 50 and s > 0.6:
        m.append("festive")
    return m


def harmony(seed: str, scheme: str = "complementary", dark: bool = False, second: str = "") -> dict[str, Any]:
    """One colour (+ an optional second she named) -> {bg, surface, ink, primary, accent, moods} for light or dark."""
    seed = _hex(seed) or "#1565C0"
    h, s, l = hsl(seed)
    s = max(0.35, min(0.85, s if s > 0.05 else 0.1))
    gray = hsl(seed)[1] < 0.08
    if second and _hex(second):
        accent = _hex(second)
    elif scheme == "monochrome" or gray:
        accent = from_hsl(h, s * 0.65, 0.62 if not dark else 0.72)
    else:
        accent = from_hsl(h + SCHEMES.get(scheme, 180), min(0.9, s + 0.05), 0.55)
    if dark:
        bg, surface = from_hsl(h, 0.16 if not gray else 0, 0.075), from_hsl(h, 0.14 if not gray else 0, 0.125)
        ink = from_hsl(h, 0.12 if not gray else 0, 0.94)
        primary = seed
        while BR.contrast(bg, primary) < 4.6 and hsl(primary)[2] < 0.9:
            ph, ps, pl = hsl(primary)
            primary = from_hsl(ph, ps, pl + 0.05)
        ah, as_, al = hsl(accent)
        accent = from_hsl(ah, as_, max(al, 0.62))
    else:
        bg, surface = from_hsl(h, 0.32 if not gray else 0, 0.975), "#FFFFFF"
        ink = from_hsl(h, 0.22 if not gray else 0, 0.1)
        primary = seed if l <= 0.62 else from_hsl(h, s, 0.48)
    if BR.contrast(bg, ink) < 7:
        ink = BR.best_text(bg, ["#111111", "#F5F5F5"])
    return {"bg": bg, "surface": surface, "ink": ink, "primary": primary, "accent": accent,
            "moods": _moods(h, s, l, dark), "scheme": scheme if not second else "her two colours", "seed": seed, "dark": dark}


@lru_cache(maxsize=1)
def palettes() -> dict[str, dict[str, Any]]:
    """200 palettes: the 50 hand-made website palettes + 150 generated (25 named hues x 6 schemes)."""
    out = {k: dict(v) for k, v in ST.PALETTES.items()}
    for name, hue in HUES.items():
        for sch in SCHEMES:
            seed = from_hsl(hue, 0.68, 0.46)
            p = harmony(seed, sch)
            out[f"{name}_{sch}"] = {k: p[k] for k in ("bg", "surface", "ink", "primary", "accent", "moods")}
    return out


def dark_of(tk: dict[str, Any]) -> dict[str, str]:
    """The dark-mode colours of an app whose light colours are tk (primary / accent kept recognisable)."""
    d = harmony(tk["primary"], "complementary", True, tk.get("accent", ""))
    return {k: d[k] for k in ("bg", "surface", "ink", "primary", "accent")}
