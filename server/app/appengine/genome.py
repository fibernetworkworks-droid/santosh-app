"""v0.999.58 D2 THE DESIGN GENOME (docs/WEB_DESIGN_ENGINE_PLAN.md P2 + phase D2): every site and app gets its OWN design,
decided before any page, as data - so the same 39 kit blocks look like a different website every time.

The genome = independent genes, each generated or chosen by RULE and then checked in code:
1. direction - an open, named aesthetic; the 10 Web Studio styles are seeds (starting points), not the limit
2. colour    - an OKLCH palette GENERATED from one brand hue (any colour works): bg / surface / ink / muted / line /
               primary / primary-ink / accent / ok / warn / bad, light AND dark; every text pair checked (WCAG AA 4.5:1,
               UI colours 3:1) and moved in lightness until it passes - a genome that cannot pass is never returned
3. type      - display + text (+ an Indian-script face) chosen by rule from the fonts Hoola bundles (open licences,
               self-hosted - nothing loads from an outside address), with a type scale; the over-used faces an AI reaches
               for by reflex (Inter, Fraunces, Space Grotesk, Plus Jakarta Sans) are never chosen unless she asks
4. shape     - corner radius, shadow set, line strength
5. density   - the spacing scale (Tailwind v4's --spacing)
6. motion    - calm / lively / cinematic: reveal duration, distance and easing (never bounce)
7. imagery   - one photographic / illustrated style for every picture (read by the picture engine)

Out comes tokens.css (Tailwind v4 @theme, the ONLY place colours live) + the font files + DESIGN.md (Google Stitch's
format: YAML tokens + plain rules; Hoola's full genome rides under `hoola:` so it round-trips exactly). Her DESIGN.md
from any tool imports back (`from_design_md`); her words / screenshot pick the direction and hue; nothing here calls a
model. `random_genome(seed)` makes the 100-genome proof of the D2 done-line."""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from pathlib import Path
from typing import Any

from . import tokens as TK

VERSION = 1
FONT_DIR = Path(__file__).resolve().parents[1] / "site" / "assets" / "fonts"
MODES = ("light", "dark")
CHROMA = {"muted": 0.07, "balanced": 0.12, "vivid": 0.17}
SHADOWS = {
    "none": "none",
    "soft": "0 1px 2px rgb(0 0 0 / 0.05), 0 6px 20px rgb(0 0 0 / 0.06)",
    "crisp": "0 1px 0 rgb(0 0 0 / 0.06), 0 2px 6px rgb(0 0 0 / 0.08)",
    "deep": "0 2px 4px rgb(0 0 0 / 0.08), 0 18px 48px rgb(0 0 0 / 0.16)",
}
DENSITY = {"compact": "0.24rem", "regular": "0.25rem", "airy": "0.27rem"}
SCALE = {"tight": 0.92, "standard": 1.0, "dramatic": 1.12}
MOTION = {   # reveal duration, distance, easing - one family per site, never bounce (an AI-look tell)
    "calm": ("0.7s", "10px", "cubic-bezier(0.22, 1, 0.36, 1)"),
    "lively": ("0.45s", "16px", "cubic-bezier(0.16, 1, 0.3, 1)"),
    "cinematic": ("0.95s", "28px", "cubic-bezier(0.19, 1, 0.22, 1)"),
}
TREATMENTS = ("rounded", "framed", "bleed")

# ---------------------------------------------------------------- the fonts Hoola bundles (site/assets/fonts)
# class: serif / sans / display (a face for headings only) / hand; role: what it may be used for
FONTS: dict[str, dict[str, Any]] = {
    "Archivo": {"cls": "sans", "role": ("display", "text")},
    "Baloo 2": {"cls": "rounded", "role": ("display", "text")},
    "Bricolage Grotesque": {"cls": "grotesk", "role": ("display",)},
    "Cormorant Garamond": {"cls": "serif", "role": ("display",)},
    "DM Sans": {"cls": "sans", "role": ("display", "text")},
    "DM Serif Display": {"cls": "serif", "role": ("display",)},
    "Eczar": {"cls": "serif", "role": ("display", "text")},
    "Fraunces": {"cls": "serif", "role": ("display",), "overused": True},
    "Hind": {"cls": "sans", "role": ("text",)},
    "Instrument Serif": {"cls": "serif", "role": ("display",)},
    "Inter": {"cls": "sans", "role": ("text",), "overused": True},
    "Josefin Sans": {"cls": "geometric", "role": ("display",)},
    "Kalam": {"cls": "hand", "role": ("display",)},
    "Khand": {"cls": "condensed", "role": ("display",)},
    "Laila": {"cls": "serif", "role": ("display", "text")},
    "Lato": {"cls": "sans", "role": ("text",)},
    "Lora": {"cls": "serif", "role": ("display", "text")},
    "Manrope": {"cls": "sans", "role": ("display", "text")},
    "Martel": {"cls": "serif", "role": ("text",)},
    "Mukta": {"cls": "sans", "role": ("text",)},
    "Nunito": {"cls": "rounded", "role": ("display", "text")},
    "Outfit": {"cls": "geometric", "role": ("display", "text")},
    "Palanquin": {"cls": "sans", "role": ("text",)},
    "Palanquin Dark": {"cls": "sans", "role": ("display",)},
    "Playfair Display": {"cls": "serif", "role": ("display",)},
    "Plus Jakarta Sans": {"cls": "sans", "role": ("display", "text"), "overused": True},
    "Poppins": {"cls": "geometric", "role": ("display", "text")},
    "Rozha One": {"cls": "serif", "role": ("display",)},
    "Sora": {"cls": "geometric", "role": ("display", "text")},
    "Space Grotesk": {"cls": "grotesk", "role": ("display",), "overused": True},
    "Spectral": {"cls": "serif", "role": ("display", "text")},
    "Syne": {"cls": "grotesk", "role": ("display",)},
    "Teko": {"cls": "condensed", "role": ("display",)},
    "Tiro Devanagari Hindi": {"cls": "serif", "role": ("text",)},
    "Urbanist": {"cls": "geometric", "role": ("display", "text")},
    "Yatra One": {"cls": "festive", "role": ("display",)},
}
FALLBACK = {"serif": 'ui-serif, Georgia, "Noto Serif", serif',
            "sans": 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif'}
SERIFISH = {"serif"}

# ---------------------------------------------------------------- directions = seeds, not the limit
DIRECTIONS: dict[str, dict[str, Any]] = {
    "editorial_calm": {"label": "Editorial calm", "mode": ("light",), "chroma": ("muted", "balanced"), "neutral": ("warm",),
                       "display": ("serif",), "text": ("sans", "geometric"), "radius": (2, 10), "shadow": ("none", "soft"),
                       "density": ("airy",), "motion": ("calm",), "scale": ("dramatic", "standard"), "line": ("subtle",),
                       "imagery": "quiet natural-light photographs, soft shadows, warm paper tones"},
    "bold_modern": {"label": "Bold modern", "mode": ("light",), "chroma": ("vivid",), "neutral": ("pure",),
                    "display": ("grotesk", "sans"), "text": ("sans", "geometric"), "radius": (6, 14), "shadow": ("crisp",),
                    "density": ("regular",), "motion": ("lively",), "scale": ("dramatic",), "line": ("strong",),
                    "imagery": "high-contrast photographs, tight crops, one strong colour per frame"},
    "warm_local": {"label": "Warm local", "mode": ("light",), "chroma": ("balanced",), "neutral": ("warm",),
                   "display": ("rounded", "serif"), "text": ("sans", "rounded"), "radius": (12, 20), "shadow": ("soft",),
                   "density": ("regular",), "motion": ("lively", "calm"), "scale": ("standard",), "line": ("subtle",),
                   "imagery": "warm, lived-in photographs of real people and places, golden-hour light", "hue": (15, 75)},
    "luxury_dark": {"label": "Luxury dark", "mode": ("dark",), "chroma": ("muted",), "neutral": ("warm",),
                    "display": ("serif",), "text": ("sans", "geometric"), "radius": (0, 6), "shadow": ("deep",),
                    "density": ("airy",), "motion": ("cinematic",), "scale": ("dramatic",), "line": ("subtle",),
                    "imagery": "low-key photographs, deep shadows, gold and brass highlights", "hue": (40, 95)},
    "playful_bright": {"label": "Playful bright", "mode": ("light",), "chroma": ("vivid",), "neutral": ("tinted",),
                       "display": ("rounded", "geometric"), "text": ("rounded", "geometric", "sans"), "radius": (18, 28),
                       "shadow": ("soft",), "density": ("regular",), "motion": ("lively",), "scale": ("standard",),
                       "line": ("subtle",), "imagery": "bright flat illustrations and cheerful photographs, plenty of colour"},
    "minimal_swiss": {"label": "Minimal Swiss", "mode": ("light",), "chroma": ("muted", "balanced"), "neutral": ("pure",),
                      "display": ("sans", "grotesk"), "text": ("sans",), "radius": (0, 4), "shadow": ("none",),
                      "density": ("airy",), "motion": ("calm",), "scale": ("dramatic", "standard"), "line": ("strong",),
                      "imagery": "clean product and architecture photographs on plain backgrounds, lots of space"},
    "festive_traditional": {"label": "Festive traditional", "mode": ("light",), "chroma": ("vivid", "balanced"),
                            "neutral": ("warm",), "display": ("festive", "serif"), "text": ("sans",), "radius": (8, 16),
                            "shadow": ("soft",), "density": ("regular",), "motion": ("lively",), "scale": ("standard",),
                            "line": ("subtle",), "imagery": "rich festive photographs, marigold, brass and silk textures",
                            "hue": (0, 50)},
    "tech_gradient": {"label": "Tech", "mode": ("dark", "light"), "chroma": ("vivid",), "neutral": ("cool",),
                      "display": ("geometric", "grotesk"), "text": ("sans", "geometric"), "radius": (10, 16),
                      "shadow": ("crisp",), "density": ("regular",), "motion": ("lively",), "scale": ("standard",),
                      "line": ("strong",), "imagery": "product screenshots and abstract light, crisp and technical",
                      "hue": (200, 290)},
    "organic_natural": {"label": "Organic natural", "mode": ("light",), "chroma": ("balanced", "muted"), "neutral": ("warm",),
                        "display": ("serif",), "text": ("sans", "serif"), "radius": (14, 24), "shadow": ("soft",),
                        "density": ("airy",), "motion": ("calm",), "scale": ("standard",), "line": ("subtle",),
                        "imagery": "soft daylight photographs of plants, hands and natural textures", "hue": (90, 165)},
    "corporate_trust": {"label": "Corporate trust", "mode": ("light",), "chroma": ("balanced",), "neutral": ("cool",),
                        "display": ("sans", "geometric"), "text": ("sans",), "radius": (6, 12), "shadow": ("soft",),
                        "density": ("regular",), "motion": ("calm",), "scale": ("standard", "tight"), "line": ("subtle",),
                        "imagery": "honest documentary photographs of the team and the work, natural colour",
                        "hue": (195, 250)},
}
# her words -> a seed direction (the first match wins); her own named direction is kept as the name
WORDS = [
    ("luxury_dark", r"luxur|premium|gold|jewel|jewell|fine dining|lounge|boutique hotel|bridal couture"),
    ("festive_traditional", r"festiv|diwali|wedding|shaadi|temple|puja|mehendi|navratri|traditional|ethnic"),
    ("tech_gradient", r"\bsaas\b|software|startup|\bapp\b|\bai\b|tech|developer|crypto|cloud|platform"),
    ("playful_bright", r"kid|child|toy|play|game|quiz|fun|party|birthday|school"),
    ("organic_natural", r"organic|yoga|spa|wellness|ayurved|farm|plant|garden|natural|eco"),
    ("corporate_trust", r"law|legal|finance|account|\bca\b|bank|insur|clinic|hospital|doctor|consult|corporate"),
    ("minimal_swiss", r"architect|portfolio|design studio|minimal|photograph|gallery|furniture"),
    ("editorial_calm", r"blog|magazine|writer|author|journal|editorial|course|learn"),
    ("warm_local", r"restaurant|cafe|bakery|sweet|food|kitchen|dhaba|shop|kirana|salon|homestay"),
    ("bold_modern", r"gym|fitness|sport|agency|launch|event|bold"),
]


# ---------------------------------------------------------------- OKLCH colour maths (no model, no library)
def _lin2srgb(x: float) -> float:
    return 1.055 * x ** (1 / 2.4) - 0.055 if x > 0.0031308 else 12.92 * x


def _srgb2lin(x: float) -> float:
    return ((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92


def oklch_rgb(L: float, C: float, h: float) -> tuple[float, float, float]:
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bb = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return r, g, bb


def _in_gamut(rgb: tuple[float, float, float]) -> bool:
    return all(-0.0005 <= c <= 1.0005 for c in rgb)


def oklch_hex(L: float, C: float, h: float) -> str:
    """OKLCH -> #rrggbb, chroma reduced until the colour fits sRGB (the hue and lightness stay)."""
    L = max(0.0, min(1.0, L))
    lo, hi = 0.0, max(0.0, C)
    if not _in_gamut(oklch_rgb(L, hi, h)):
        for _ in range(24):
            mid = (lo + hi) / 2
            if _in_gamut(oklch_rgb(L, mid, h)):
                lo = mid
            else:
                hi = mid
        C = lo
    r, g, b = (max(0.0, min(1.0, _lin2srgb(max(0.0, c)))) for c in oklch_rgb(L, C, h))
    return "#" + "".join(f"{round(c * 255):02x}" for c in (r, g, b))


def hex_oklch(hx: str) -> tuple[float, float, float]:
    r, g, b = (_srgb2lin(int(hx[i:i + 2], 16) / 255) for i in (1, 3, 5))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), (math.degrees(math.atan2(bb, a)) + 360) % 360


def _fit(L: float, C: float, h: float, against: list[str], need: float, darker: bool) -> str:
    """Move a colour's lightness (darker or lighter) until it reads against every colour in `against`."""
    for _ in range(100):
        hx = oklch_hex(L, C, h)
        if all(TK.contrast(hx, x) >= need for x in against):
            return hx
        L += -0.01 if darker else 0.01
        if not 0 <= L <= 1:
            break
    return "#000000" if darker else "#ffffff"


# ---------------------------------------------------------------- the palette (light + dark from one hue)
def palette(colour: dict[str, Any], mode: str) -> dict[str, str]:
    h = float(colour["hue"]) % 360
    cp = CHROMA.get(colour.get("chroma", "balanced"), 0.12)
    shift = float(colour.get("accent_shift", 150))
    nh, nc = {"warm": (70, 0.014), "cool": (250, 0.012), "pure": (h, 0.0), "tinted": (h, 0.016)}.get(
        colour.get("neutral", "tinted"), (h, 0.012))
    strong = colour.get("line") == "strong"
    p: dict[str, str] = {}
    if mode == "light":
        p["bg"] = oklch_hex(0.985, nc * 0.7, nh)
        p["surface"] = oklch_hex(0.998, nc * 0.2, nh)
        p["line"] = oklch_hex(0.86 if strong else 0.91, nc * 1.2, nh)
        p["ink"] = _fit(0.22, nc * 1.6, nh, [p["bg"], p["surface"]], 7.0, True)
        p["muted"] = _fit(0.52, nc * 1.4, nh, [p["bg"], p["surface"]], 4.6, True)
        p["primary"] = _primary(colour, h, cp, [p["bg"], p["surface"]], True)
        p["accent"] = _fit(0.62, cp * 0.95, h + shift, [p["bg"]], 3.0, True)
        for k, hh in (("ok", 150), ("warn", 70), ("bad", 27)):
            p[k] = _fit(0.55, 0.15, hh, [p["bg"], p["surface"]], 4.6, True)
    else:
        p["bg"] = oklch_hex(0.17, nc * 1.4 + 0.004, nh)
        p["surface"] = oklch_hex(0.215, nc * 1.4 + 0.004, nh)
        p["line"] = oklch_hex(0.36 if strong else 0.31, nc * 1.4 + 0.004, nh)
        p["ink"] = _fit(0.95, nc * 0.8, nh, [p["bg"], p["surface"]], 7.0, False)
        p["muted"] = _fit(0.72, nc, nh, [p["bg"], p["surface"]], 4.6, False)
        p["primary"] = _primary(colour, h, cp, [p["bg"], p["surface"]], False)
        p["accent"] = _fit(0.76, cp * 0.95, h + shift, [p["bg"]], 3.0, False)
        for k, hh in (("ok", 150), ("warn", 75), ("bad", 25)):
            p[k] = _fit(0.75, 0.14, hh, [p["bg"], p["surface"]], 4.6, False)
    p["primary_ink"] = _on(p["primary"])
    return p


def _primary(colour: dict[str, Any], h: float, cp: float, against: list[str], light: bool) -> str:
    """The brand colour: her exact pinned colour when it reads on the page (as text: 4.5:1) and carries readable
    button text, else the nearest lightness that does. A light page darkens it, a dark page lightens it."""
    pin = colour.get("pin") or ""
    if TK.HEX.match(pin):
        if all(TK.contrast(pin, x) >= 4.5 for x in against) and _on_ok(pin):
            return pin.lower()
        L, C, hh = hex_oklch(pin)
        return _fit_primary(L, C, hh, against, light)
    return _fit_primary(0.55 if light else 0.72, cp, h, against, light)


def _fit_primary(L: float, C: float, h: float, against: list[str], light: bool) -> str:
    for _ in range(100):
        hx = oklch_hex(L, C, h)
        if all(TK.contrast(hx, x) >= 4.5 for x in against) and _on_ok(hx):
            return hx
        L += -0.01 if light else 0.01
        if not 0 <= L <= 1:
            break
    return oklch_hex(0.4 if light else 0.8, C, h)


def _on(bg: str) -> str:
    w, d = TK.contrast("#ffffff", bg), TK.contrast("#111111", bg)
    return "#ffffff" if w >= 4.5 or w >= d else "#111111"


def _on_ok(bg: str) -> bool:
    return TK.contrast(_on(bg), bg) >= 4.5


# ---------------------------------------------------------------- the checks (every pair a kit part uses)
PAIRS = TK.PAIRS + (("primary", "bg", 4.5), ("primary", "surface", 4.5), ("accent", "bg", 3.0),
                    ("ok", "bg", 4.5), ("warn", "bg", 4.5), ("bad", "bg", 4.5),
                    ("ok", "surface", 4.5), ("warn", "surface", 4.5), ("bad", "surface", 4.5))


def audit_palette(p: dict[str, str]) -> list[str]:
    out = []
    seen = set()
    for a, b, need in PAIRS:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        need = max(need, 4.5) if (a, b) in (("primary", "bg"), ("primary", "surface")) else need
        c = TK.contrast(p[a], p[b])
        if c < need:
            out.append(f"{a.replace('_', '-')} on {b}: {c} (needs {need})")
    return out


def audit(g: dict[str, Any]) -> list[str]:
    """Every problem with a genome in words ([] = it passes): both palettes, fonts on disk, genes in range."""
    out = []
    for m in MODES:
        out += [f"{m}: {x}" for x in audit_palette(palette(g["colour"], m))]
    for k in ("display", "text", "deva"):
        f = g["type"].get(k)
        if f not in FONTS or not font_files(f):
            out.append(f"type.{k}: '{f}' is not a bundled font")
    if g["shape"]["shadow"] not in SHADOWS:
        out.append("shape.shadow unknown")
    if g["density"] not in DENSITY:
        out.append("density unknown")
    if g["motion"] not in MOTION:
        out.append("motion unknown")
    if not 0 <= int(g["shape"]["radius"]) <= 32:
        out.append("shape.radius out of 0-32")
    return out


# ---------------------------------------------------------------- fonts on disk
def _slug(fam: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")


def font_files(fam: str) -> list[tuple[str, int, str]]:
    """[(subset, weight, file name)] bundled for one family."""
    out = []
    for sub in ("latin", "devanagari"):
        for w in (400, 500, 600, 700):
            fn = f"{_slug(fam)}-{sub}-{w}.woff2"
            if (FONT_DIR / fn).exists():
                out.append((sub, w, fn))
    return out


def has_deva(fam: str) -> bool:
    return any(s == "devanagari" for s, _, _ in font_files(fam))


def _choose_font(rnd: random.Random, classes: tuple[str, ...], role: str, avoid: set[str]) -> str:
    pool = [f for f, d in FONTS.items() if role in d["role"] and d["cls"] in classes and not d.get("overused")
            and f not in avoid and font_files(f)]
    if not pool:
        pool = [f for f, d in FONTS.items() if role in d["role"] and not d.get("overused") and f not in avoid and font_files(f)]
    return rnd.choice(sorted(pool))


def _deva_for(text: str, display: str) -> str:
    """The Indian-script face: the text face itself when it has Devanagari, else one that matches its class."""
    if has_deva(text):
        return text
    if FONTS[text]["cls"] == "serif" or FONTS[display]["cls"] == "serif":
        return "Martel"
    return "Mukta"


# ---------------------------------------------------------------- making a genome
def direction_from_words(words: str) -> str:
    w = (words or "").lower()
    for d, rx in WORDS:
        if re.search(rx, w):
            return d
    return ""


def generate(seed: int | str | None = None, hue: float | None = None, direction: str = "", mode: str = "",
             words: str = "", pin: str = "", name: str = "", fonts: dict[str, str] | None = None) -> dict[str, Any]:
    """A genome by rule. `seed` makes it repeatable; `direction` a seed name (or her own words: its seed is guessed and
    her name kept); `hue` / `pin` (her brand colour #rrggbb) pin the colour; `mode` light / dark; `fonts` pins
    display / text when bundled. Always returns a genome that passes `audit` (a gene is re-rolled until it does)."""
    s = int(hashlib.sha256(str(seed if seed is not None else random.random()).encode()).hexdigest()[:12], 16)
    rnd = random.Random(s)
    key = direction if direction in DIRECTIONS else (direction_from_words(f"{direction} {words}") or
                                                      rnd.choice(sorted(DIRECTIONS)))
    d = DIRECTIONS[key]
    if TK.HEX.match(pin or ""):
        hue = hex_oklch(pin)[2]
    if hue is None:
        lo, hi = d.get("hue", (0, 360))
        hue = rnd.uniform(lo, hi) % 360
    m = mode if mode in MODES else rnd.choice(d["mode"])
    for attempt in range(12):
        display = _choose_font(rnd, d["display"], "display", set())
        text = _choose_font(rnd, d["text"], "text", {display})
        if fonts:
            if fonts.get("display") in FONTS and font_files(fonts["display"]):
                display = fonts["display"]
            if fonts.get("text") in FONTS and font_files(fonts["text"]) and "text" in FONTS[fonts["text"]]["role"]:
                text = fonts["text"]
        lo, hi = d["radius"]
        g = {
            "v": VERSION, "seed": str(seed if seed is not None else s),
            "direction": {"name": (direction if direction and direction not in DIRECTIONS else d["label"])[:60],
                          "seed": key, "words": " ".join(str(words or "").split())[:300]},
            "colour": {"hue": round(hue, 1), "chroma": rnd.choice(d["chroma"]), "neutral": rnd.choice(d["neutral"]),
                       "accent_shift": rnd.choice((30, 60, 150, 180, -40, -150)), "line": rnd.choice(d["line"]),
                       "mode": m, "pin": pin.lower() if TK.HEX.match(pin or "") else ""},
            "type": {"display": display, "text": text, "deva": _deva_for(text, display),
                     "scale": rnd.choice(d["scale"]), "display_weight": rnd.choice((500, 600, 700))
                     if FONTS[display]["cls"] not in ("serif", "festive") else rnd.choice((400, 500, 600))},
            "shape": {"radius": rnd.randint(lo, hi), "shadow": rnd.choice(d["shadow"])},
            "density": rnd.choice(d["density"]),
            "motion": rnd.choice(d["motion"]),
            "imagery": {"style": d["imagery"], "treatment": rnd.choice(TREATMENTS)},
            "name": " ".join(str(name or "").split())[:80],
        }
        if not audit(g):
            return g
        rnd.random()                                            # a fresh roll for the next try
    raise ValueError("no readable design for those choices: " + "; ".join(audit(g)))


def random_genome(i: int) -> dict[str, Any]:
    """The i-th genome of the D2 proof: a random direction, hue and mode (repeatable)."""
    rnd = random.Random(10_000 + i)
    return generate(seed=f"proof-{i}", hue=rnd.uniform(0, 360), mode=rnd.choice(MODES),
                    direction=rnd.choice(sorted(DIRECTIONS)))


def clean(g: dict[str, Any]) -> dict[str, Any]:
    """A genome from outside (DESIGN.md, the tool): every gene checked and filled; raises ValueError in words."""
    if not isinstance(g, dict):
        raise ValueError("the design is not a genome")
    c = dict(g.get("colour") or {})
    t = dict(g.get("type") or {})
    d = dict(g.get("direction") or {})
    sh = dict(g.get("shape") or {})
    base = generate(seed=g.get("seed") or "import", hue=c.get("hue"), direction=d.get("seed") or d.get("name") or "",
                    mode=c.get("mode") or "", pin=c.get("pin") or "", words=d.get("words") or "",
                    fonts={"display": t.get("display", ""), "text": t.get("text", "")}, name=g.get("name") or "")
    for k in ("chroma", "neutral", "line"):
        if c.get(k) in ({"chroma": CHROMA, "neutral": ("warm", "cool", "pure", "tinted"), "line": ("subtle", "strong")}[k]):
            base["colour"][k] = c[k]
    if isinstance(c.get("accent_shift"), (int, float)):
        base["colour"]["accent_shift"] = float(c["accent_shift"])
    if t.get("scale") in SCALE:
        base["type"]["scale"] = t["scale"]
    if t.get("display_weight") in (400, 500, 600, 700):
        base["type"]["display_weight"] = int(t["display_weight"])
    if t.get("deva") in FONTS and has_deva(t["deva"]):
        base["type"]["deva"] = t["deva"]
    if d.get("words"):
        base["direction"]["words"] = str(d["words"])[:300]
    if sh.get("shadow") in SHADOWS:
        base["shape"]["shadow"] = sh["shadow"]
    if isinstance(sh.get("radius"), (int, float)):
        base["shape"]["radius"] = max(0, min(32, int(sh["radius"])))
    for k, allowed in (("density", DENSITY), ("motion", MOTION)):
        if g.get(k) in allowed:
            base[k] = g[k]
    im = g.get("imagery") or {}
    if isinstance(im, dict):
        if im.get("style"):
            base["imagery"]["style"] = str(im["style"])[:200]
        if im.get("treatment") in TREATMENTS:
            base["imagery"]["treatment"] = im["treatment"]
    if d.get("name"):
        base["direction"]["name"] = str(d["name"])[:60]
    probs = audit(base)
    if probs:
        raise ValueError("that design does not pass the checks: " + "; ".join(probs))
    return base


# ---------------------------------------------------------------- what the app reads: tokens.css + fonts + theme
def tokens(g: dict[str, Any]) -> dict[str, Any]:
    """The genome as the classic token dict (tokens.theme_json / the style panel read it) - the default mode's colours."""
    p = palette(g["colour"], g["colour"]["mode"])
    return {**p, "radius": int(g["shape"]["radius"]), "head": "serif" if FONTS[g["type"]["display"]]["cls"] in SERIFISH else "sans",
            "body": "serif" if FONTS[g["type"]["text"]]["cls"] in SERIFISH else "sans"}


def fonts_used(g: dict[str, Any]) -> list[tuple[str, str, int, str]]:
    """[(family, subset, weight, file)] the site loads: the display face's heading weights, the text face's 400 / 600,
    the Indian-script face's 400 / 600 (unicode-range: only pages with that script download it)."""
    want = {g["type"]["display"]: {int(g["type"].get("display_weight") or 600), 700},
            g["type"]["text"]: {400, 600}, g["type"]["deva"]: {400, 600}}
    out = []
    for fam, ws in want.items():
        files = font_files(fam)
        have = sorted({w for _, w, _ in files})
        pick = {min(have, key=lambda x: abs(x - w)) for w in ws} if have else set()
        for sub, w, fn in files:
            if w in pick and (sub == "latin" or fam == g["type"]["deva"] or has_deva(fam)):
                out.append((fam, sub, w, fn))
    return out


def _stack(fam: str, deva: str) -> str:
    fb = FALLBACK["serif" if FONTS[fam]["cls"] in SERIFISH else "sans"]
    extra = f', "{deva}"' if deva != fam else ""
    stand = f', "{fam} Fallback"' if _metrics().get(fam) else ""
    return f'"{fam}"{stand}{extra}, {fb}'


def _vars(p: dict[str, str]) -> list[str]:
    return [f"  --color-{k.replace('_', '-')}: {p[k]};" for k in TK.KEYS]


_METRICS: dict[str, Any] = {}


def _metrics() -> dict[str, Any]:
    """v0.999.64 D3: every bundled font measured once (tools/font_metrics.py -> font_metrics.json)"""
    if not _METRICS:
        try:
            _METRICS.update(json.loads((Path(__file__).with_name("font_metrics.json")).read_text()))
        except (OSError, ValueError):
            _METRICS["_none"] = {}
    return _METRICS


def fallback_faces(fam: str, weights: list[int]) -> list[str]:
    """v0.999.64 D3: a stand-in for `fam` made of the visitor's own Arial / Times New Roman, sized to the real font's
    measurements (size-adjust + ascent / descent / line-gap overrides) - text keeps its place when the real font
    arrives, so the page does not jump (layout shift). Same idea as next/font and capsize."""
    m = _metrics()
    own = m.get(fam) or {}
    fb_all = (m.get("_fallback") or {}).get("serif" if FONTS[fam]["cls"] in SERIFISH else "sans") or {}
    out = []
    for w in sorted(set(weights)):
        mine = own.get(str(w)) or own.get("400") or (next(iter(own.values())) if own else None)
        fb = fb_all.get("700" if w >= 600 else "400")
        if not mine or not fb:
            continue
        adj = (mine["xavg"] / mine["upm"]) / (fb["xavg"] / fb["upm"])
        pc = lambda v: f"{abs(v) / (mine['upm'] * adj) * 100:.2f}%"   # noqa: E731
        src = ", ".join(f'local("{n}")' for n in fb["local"])
        out.append(f'@font-face {{ font-family: "{fam} Fallback"; font-weight: {w}; src: {src}; size-adjust: {adj * 100:.2f}%; '
                   f'ascent-override: {pc(mine["ascent"])}; descent-override: {pc(mine["descent"])}; '
                   f'line-gap-override: {pc(mine["line_gap"])}; }}')
    return out


DEFAULT_TEXT = {"3xl": 1.875, "4xl": 2.25, "5xl": 3.0, "6xl": 3.75, "7xl": 4.5}


def css(g: dict[str, Any], font_url: str = "./fonts/") -> str:
    """tokens.css for the genome: the faces, the @theme (colours, corners, shadow, fonts, spacing, heading sizes,
    motion) and the other mode under [data-theme] - so a dark / light switch needs no code."""
    m = g["colour"]["mode"]
    other = "dark" if m == "light" else "light"
    p, q = palette(g["colour"], m), palette(g["colour"], other)
    r = int(g["shape"]["radius"])
    t = g["type"]
    f = SCALE.get(t.get("scale"), 1.0)
    dur, dist, ease = MOTION[g["motion"]]
    faces = []
    for fam, sub, w, fn in fonts_used(g):
        rng = f" unicode-range: {DEVA_RANGE};" if sub == "devanagari" else ""
        faces.append(f'@font-face {{ font-family: "{fam}"; font-weight: {w}; font-style: normal; font-display: swap;{rng} '
                     f'src: url({font_url}{fn}) format("woff2"); }}')
    lines = [f"/* Hoola App Engine - the design system, from this app's design genome (DESIGN.md). Written by Hoola; do not",
             f"   edit by hand. Direction: {g['direction']['name']}; {m} first, the other mode under [data-theme]. */"]
    lines += faces
    shown = int(t.get("display_weight") or 600)
    lines += fallback_faces(t["display"], [shown] if t["display"] != t["text"] else [400, 600, shown])
    if t["text"] != t["display"]:
        lines += fallback_faces(t["text"], [400, 600])
    lines += ["@theme static {", "  --color-*: initial;", "  --color-transparent: transparent;", "  --color-current: currentColor;"]
    lines += _vars(p)
    lines += [f"  --radius-card: {r + 4 if r else 0}px;", f"  --radius-control: {max(2, r - 4) if r else 0}px;",
              f"  --shadow-card: {SHADOWS[g['shape']['shadow']]};",
              f"  --font-head: {_stack(t['display'], t['deva'])};", f"  --font-body: {_stack(t['text'], t['deva'])};",
              f"  --spacing: {DENSITY[g['density']]};"]
    lines += [f"  --text-{k}: {round(v * f, 3)}rem;" for k, v in DEFAULT_TEXT.items()]
    lines += [f"  --motion-reveal: {dur};", f"  --motion-distance: {dist};", f"  --motion-ease: {ease};", "}"]
    lines += ["", f'[data-theme="{other}"] {{'] + _vars(q) + ["}", ""]
    return "\n".join(lines)


DEVA_RANGE = "U+0900-097F, U+1CD0-1CF9, U+200C-200D, U+20A8, U+20B9, U+25CC, U+A830-A839, U+A8E0-A8FF"


def write_fonts(g: dict[str, Any], dest: Path) -> list[str]:
    """Copy the genome's font files into `dest` (an app's src/styles/fonts/); old ones out. Returns the files."""
    dest.mkdir(parents=True, exist_ok=True)
    want = {fn for _, _, _, fn in fonts_used(g)}
    for f in dest.glob("*.woff2"):
        if f.name not in want:
            f.unlink()
    for fn in want:
        if not (dest / fn).exists():
            (dest / fn).write_bytes((FONT_DIR / fn).read_bytes())
    return sorted(want)


# ---------------------------------------------------------------- DESIGN.md (Stitch format: YAML tokens + plain rules)
def design_md(g: dict[str, Any]) -> str:
    import yaml
    m = g["colour"]["mode"]
    p = palette(g["colour"], m)
    q = palette(g["colour"], "dark" if m == "light" else "light")
    r = int(g["shape"]["radius"])
    t = g["type"]
    front = {
        "name": (g.get("name") or g["direction"]["name"]),
        "version": "alpha",
        "generator": f"hoola-genome/{VERSION}",
        "colors": {k.replace("_", "-"): p[k] for k in TK.KEYS},
        "colors-" + ("dark" if m == "light" else "light"): {k.replace("_", "-"): q[k] for k in TK.KEYS},
        "typography": {"display": {"fontFamily": t["display"], "fontWeight": int(t.get("display_weight") or 600)},
                       "body": {"fontFamily": t["text"], "fontWeight": 400},
                       "devanagari": {"fontFamily": t["deva"]}, "scale": t["scale"]},
        "rounded": {"card": f"{r + 4 if r else 0}px", "control": f"{max(2, r - 4) if r else 0}px"},
        "spacing": {"base": DENSITY[g["density"]], "density": g["density"]},
        "shadow": g["shape"]["shadow"],
        "motion": g["motion"],
        "imagery": dict(g["imagery"]),
        "hoola": {"genome": g},
    }
    body = f"""# {front['name']}

## Overview
Direction: **{g['direction']['name']}**{(' - ' + g['direction']['words']) if g['direction'].get('words') else ''}.
{m.capitalize()} first; the {'dark' if m == 'light' else 'light'} version is generated from the same hue.

## Colours
- Brand colour (primary) {p['primary']} on {p['bg']}; text on it {p['primary_ink']}. Accent {p['accent']} for one detail
  per screen, never a second brand colour. Every text colour reads at 4.5:1 or more (checked when this file was made).
- Gradients are an accent, not the page; never on a button.

## Type
- Headings: {t['display']}; text: {t['text']}; Indian scripts: {t['deva']}. Heading scale: {t['scale']}.
- One heading style per level; sentences, not shouting; no tiny labels above headings.

## Shape and space
- Corners {r}px base, shadow {g['shape']['shadow']}, density {g['density']}.

## Motion
- {g['motion'].capitalize()}: things arrive softly once; nothing bounces; reduced motion turns it off.

## Imagery
- {g['imagery']['style']}. Treatment: {g['imagery']['treatment']}. One style for every picture on the site.
"""
    return "---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=120) + "---\n\n" + body


def from_design_md(text: str) -> dict[str, Any]:
    """A DESIGN.md (Hoola's, or one from another tool) -> a checked genome. Hoola's own carries the exact genome;
    another tool's gives its brand colour, fonts (when Hoola bundles them), corners and light / dark - the rest is
    generated, and every colour pair is checked."""
    import yaml
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*(?:\n|$)", text or "", re.S)
    if not m:
        raise ValueError("DESIGN.md needs its tokens between --- lines at the top (YAML)")
    try:
        front = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"the YAML at the top of DESIGN.md does not read: {str(e)[:160]}")
    if not isinstance(front, dict):
        raise ValueError("the YAML at the top of DESIGN.md is not a set of tokens")
    hg = (front.get("hoola") or {}).get("genome") if isinstance(front.get("hoola"), dict) else None
    if isinstance(hg, dict):
        return clean(hg)
    cols = front.get("colors") or {}
    pin = str(cols.get("primary") or "").strip()
    bg = str(cols.get("bg") or cols.get("background") or cols.get("surface") or "").strip()
    mode = ""
    if TK.HEX.match(bg):
        mode = "dark" if hex_oklch(bg)[0] < 0.5 else "light"
    ty = front.get("typography") or {}
    pick = lambda k: str(((ty.get(k) or {}) if isinstance(ty.get(k), dict) else {}).get("fontFamily") or "")  # noqa: E731
    fonts = {"display": pick("display") or pick("headline") or pick("heading"), "text": pick("body") or pick("text")}
    rad = front.get("rounded") or {}
    radius = None
    if isinstance(rad, dict):
        v = str(rad.get("card") or rad.get("md") or rad.get("default") or "")
        mm = re.match(r"(\d+(?:\.\d+)?)\s*(px|rem)?", v)
        if mm:
            radius = float(mm.group(1)) * (16 if mm.group(2) == "rem" else 1)
    g = generate(seed=f"md:{json.dumps(front, sort_keys=True, default=str)[:400]}", pin=pin if TK.HEX.match(pin) else "",
                 mode=mode, name=str(front.get("name") or "")[:80], fonts=fonts,
                 direction=str(front.get("direction") or ""), words=str(front.get("description") or ""))
    if radius is not None:
        g["shape"]["radius"] = max(0, min(32, int(radius - 4 if radius > 4 else radius)))
    return clean(g)


def summary(g: dict[str, Any]) -> dict[str, Any]:
    """For the Studio and the tool answer: the genes in a few words + the colours of both modes."""
    m = g["colour"]["mode"]
    return {"direction": g["direction"]["name"], "seed_direction": g["direction"]["seed"], "mode": m,
            "hue": g["colour"]["hue"], "primary": palette(g["colour"], m)["primary"],
            "fonts": {"display": g["type"]["display"], "text": g["type"]["text"], "indian": g["type"]["deva"]},
            "radius": g["shape"]["radius"], "shadow": g["shape"]["shadow"], "density": g["density"],
            "motion": g["motion"], "imagery": g["imagery"]["style"], "checks": audit(g) or "every colour pair readable"}


def hue_of_words(words: str) -> float | None:
    """A colour she names ("maroon", "teal", "saffron") -> a hue; None when she named none."""
    names = {"red": 27, "maroon": 18, "crimson": 15, "rose": 5, "pink": 350, "magenta": 330, "purple": 305,
             "violet": 290, "indigo": 270, "blue": 255, "navy": 260, "sky": 235, "cyan": 210, "teal": 190,
             "turquoise": 185, "green": 150, "emerald": 160, "mint": 165, "olive": 115, "lime": 125, "yellow": 95,
             "mustard": 85, "gold": 80, "saffron": 60, "orange": 50, "amber": 70, "brown": 55, "terracotta": 38,
             "coral": 30, "peach": 45, "lavender": 300, "beige": 75}
    w = (words or "").lower()
    for k, v in names.items():
        if re.search(rf"\b{k}\b", w):
            return float(v)
    m = re.search(r"#[0-9a-fA-F]{6}\b", w)
    if m:
        return hex_oklch(m.group(0))[2]
    return None


def for_brief(name: str, brief: str) -> dict[str, Any]:
    """A new app's own genome from her name + words: the direction her words point to, a colour she named, the rest
    by rule; repeatable for the same words, different for different words."""
    words = f"{name} {brief}"
    pin = (re.search(r"#[0-9a-fA-F]{6}\b", words or "") or [""])[0]
    return generate(seed=f"brief:{words.strip().lower()}", hue=hue_of_words(words), direction=direction_from_words(words),
                    words=brief, pin=pin, name=name, mode="dark" if re.search(r"\bdark\b|\bblack\b", words.lower()) else "")


__all__ = ["generate", "random_genome", "clean", "audit", "palette", "css", "tokens", "design_md", "from_design_md",
           "write_fonts", "summary", "for_brief", "DIRECTIONS", "FONTS"]
