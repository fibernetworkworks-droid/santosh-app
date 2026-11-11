"""HOOLA DESIGN AI: one line -> a designed frame (phase D5), and "change what I selected".

The model NEVER writes ops, node ids or coordinates of laid-out children. It answers with a small JSON SPEC - a
tree of frames / text / shapes / picture placeholders / icons with auto layout words (row, column, gap, pad, hug,
fill). Everything after that is code:

    clean_spec      strict validation: only known keys, depth <= 8, nodes <= 400, numbers clamped, colours parsed,
                    fonts from the editor's own list, text capped, invented phone numbers / prices / emails turned
                    into marked [blanks], lorem ipsum refused
    build           spec -> contract nodes (docs/HOOLA_DESIGN_PLAN.md section 2) with fresh ids and fractional
                    indexes -> the server's layout pass (ailayout.py) -> a CONTRAST check of every text against what
                    is really behind it, with one automatic fix (darken / lighten) -> ops, parents first
    generate        prompt + context -> spec: the model through the house door (agent/door.py), ONE retry with the
                    validation error fed back, a loud AiError after that; no model configured = a built-in template
    edit            the selection as short handles (n1, n2 ...) -> {handle, set} changes + new children; every
                    property goes through the same validation, and nothing is ever deleted or moved by an edit
    design          the whole job for the route and the agent tool: read the file, make the ops, apply them THROUGH
                    the room (HUB.apply_ops), so every open editor sees the result appear

Text widths on the server are estimates (see ailayout.py); the editor that asked runs the real layout once over
the new nodes (hd-ai.js, the `aiSettle` mark on each new frame).
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
import unicodedata
from typing import Any, Callable

from ..config import get_settings
from . import ailayout, fracidx, icons
from .doc import ROOT, loads

log = logging.getLogger("hoola.design.ai")

MAX_DEPTH = 8
MAX_NODES = 400
MAX_FRAMES = 6
MAX_KIDS = 80
MAX_CHARS = 600
MAX_NAME = 60
PROMPT_MAX = 2000
FRAME_GAP = 80
PAGE_BG = "#F5F5F5"
MIN_CONTRAST = 4.5
STATS = {"model": 0, "template": 0, "retries": 0, "failed": 0, "contrast_fixed": 0, "edits": 0}


class AiError(Exception):
    """The design could not be made. `status` is the HTTP status the route answers with."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class SpecError(ValueError):
    """The model's answer is not a usable spec (the message is fed back to the model once)."""


# name -> (label, width, height, height hugs the content)
PRESETS: dict[str, tuple[str, int, int, bool]] = {
    "phone": ("Phone app screen", 390, 844, False),
    "android": ("Android screen", 360, 800, False),
    "web": ("Desktop web page", 1440, 1024, True),
    "instagram": ("Instagram post", 1080, 1080, False),
    "story": ("Story", 1080, 1920, False),
    "whatsapp": ("WhatsApp status", 1080, 1920, False),
    "poster": ("A4 poster", 1240, 1754, False),
    "card": ("Business card", 1050, 600, False),
    "slide": ("Presentation slide", 1920, 1080, False),
    "logo": ("Logo lockup", 800, 600, False),
}
_PRESET_WORDS: list[tuple[str, str]] = [
    (r"whats\s?app status|व्हाट्सएप स्टेटस", "whatsapp"), (r"\bstory\b|\bstories\b|\bstatus\b|reel cover|स्टोरी", "story"),
    (r"insta(?:gram)?|social (?:media )?post|\bsquare post\b|facebook post|इंस्टाग्राम", "instagram"),
    (r"business card|visiting card|विज़िटिंग कार्ड|विजिटिंग कार्ड", "card"),
    (r"\bslide\b|\bslides\b|presentation|\bppt\b|pitch deck|\bdeck\b", "slide"),
    (r"\blogo\b|wordmark|लोगो", "logo"),
    (r"poster|flyer|pamphlet|leaflet|\ba4\b|पोस्टर|पैम्फलेट", "poster"),
    (r"android", "android"),
    (r"website|web ?page|landing page|home ?page|dashboard|desktop|web app|admin panel|वेबसाइट", "web"),
    (r"\bapp\b|screen|mobile|phone|login|sign ?in|sign ?up|onboarding|checkout|ऐप|स्क्रीन", "phone"),
]

# The editor's own font list (hd-ui.js FONTS): a font outside it is replaced, never loaded.
FONTS = (
    "Inter", "Schibsted Grotesk", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins", "Nunito", "Work Sans", "DM Sans",
    "Manrope", "Plus Jakarta Sans", "Outfit", "Sora", "Space Grotesk", "Figtree", "Urbanist", "Lexend", "Rubik", "Raleway",
    "Source Sans 3", "IBM Plex Sans", "Noto Sans", "Mulish", "Karla", "Barlow", "Oswald", "Archivo", "Quicksand", "Bebas Neue",
    "Literata", "Playfair Display", "Merriweather", "Lora", "Source Serif 4", "DM Serif Display", "Libre Baskerville",
    "Cormorant Garamond", "Fraunces", "EB Garamond", "Crimson Pro",
    "JetBrains Mono", "IBM Plex Mono", "Space Mono", "Fira Code", "Roboto Mono",
    "Pacifico", "Caveat", "Dancing Script", "Lobster", "Permanent Marker", "Abril Fatface", "Righteous", "Comfortaa",
    "Noto Sans Devanagari", "Noto Serif Devanagari", "Hind", "Mukta", "Baloo 2", "Anek Devanagari", "Tiro Devanagari Hindi",
    "Kalam", "Rajdhani", "Yatra One", "Noto Sans Tamil", "Hind Madurai", "Noto Sans Telugu", "Noto Sans Bengali",
    "Hind Siliguri", "Noto Sans Gujarati", "Noto Sans Kannada", "Noto Sans Malayalam", "Noto Sans Gurmukhi", "Noto Nastaliq Urdu",
)
_FONT = {f.lower(): f for f in FONTS}
# script -> (unicode range, fonts that carry it, the font used when the chosen one does not)
SCRIPTS: dict[str, tuple[tuple[int, int], frozenset[str], str]] = {
    "devanagari": ((0x0900, 0x097F), frozenset({"Noto Sans Devanagari", "Noto Serif Devanagari", "Hind", "Mukta", "Baloo 2",
                                                "Anek Devanagari", "Tiro Devanagari Hindi", "Kalam", "Rajdhani", "Yatra One",
                                                "Poppins", "Noto Sans"}), "Noto Sans Devanagari"),
    "bengali": ((0x0980, 0x09FF), frozenset({"Noto Sans Bengali", "Hind Siliguri"}), "Noto Sans Bengali"),
    "gurmukhi": ((0x0A00, 0x0A7F), frozenset({"Noto Sans Gurmukhi"}), "Noto Sans Gurmukhi"),
    "gujarati": ((0x0A80, 0x0AFF), frozenset({"Noto Sans Gujarati"}), "Noto Sans Gujarati"),
    "tamil": ((0x0B80, 0x0BFF), frozenset({"Noto Sans Tamil", "Hind Madurai"}), "Noto Sans Tamil"),
    "telugu": ((0x0C00, 0x0C7F), frozenset({"Noto Sans Telugu"}), "Noto Sans Telugu"),
    "kannada": ((0x0C80, 0x0CFF), frozenset({"Noto Sans Kannada"}), "Noto Sans Kannada"),
    "malayalam": ((0x0D00, 0x0D7F), frozenset({"Noto Sans Malayalam"}), "Noto Sans Malayalam"),
    "arabic": ((0x0600, 0x06FF), frozenset({"Noto Nastaliq Urdu"}), "Noto Nastaliq Urdu"),
}
SHADOWS = {
    "sm": {"type": "drop", "x": 0, "y": 1, "blur": 3, "spread": 0, "color": "#0F172A", "opacity": 0.10, "visible": True},
    "md": {"type": "drop", "x": 0, "y": 6, "blur": 16, "spread": 0, "color": "#0F172A", "opacity": 0.12, "visible": True},
    "lg": {"type": "drop", "x": 0, "y": 18, "blur": 44, "spread": 0, "color": "#0F172A", "opacity": 0.16, "visible": True},
}
TYPES = frozenset({"frame", "text", "rect", "ellipse", "line", "image", "icon"})
_NAMED = {"white": "#FFFFFF", "black": "#000000", "transparent": "", "none": ""}


# =============================================================================================== small helpers
def _num(v: Any, default: float | None = None, lo: float = -1e6, hi: float = 1e6) -> float | None:
    """A finite number inside [lo, hi] from whatever the model wrote ("24px" counts); else `default`."""
    if isinstance(v, bool):
        return default
    if isinstance(v, str):
        m = re.match(r"\s*(-?\d+(?:\.\d+)?)", v)
        if not m:
            return default
        v = float(m.group(1))
    if isinstance(v, int):
        try:
            v = float(v)
        except OverflowError:
            return hi if v > 0 else lo
    if not isinstance(v, float) or v != v or abs(v) == math.inf:
        return default
    return min(hi, max(lo, v))


def _tidy(n: float) -> float | int:
    n = round(float(n), 2)
    return int(n) if n == int(n) else n


def _snap(v: float) -> int:
    """Spacing sits on the 4 / 8 point grid."""
    return int(round(v)) if v < 4 else int(round(v / 4.0) * 4)


def _text(v: Any, cap: int) -> str:
    """Plain text: no control characters (line breaks stay), capped. It is only ever drawn as text."""
    if v is None or isinstance(v, (dict, list, bool)):
        return ""
    s = str(v).replace("\r\n", "\n").replace("\r", "\n")
    s = "".join(ch for ch in s if ch == "\n" or (unicodedata.category(ch) not in ("Cc", "Cs", "Co", "Cn")))
    return s[:cap]


def color(v: Any) -> str | None:
    """'#RRGGBB' from #RGB / #RRGGBB / #RRGGBBAA / rgb(r,g,b) / white / black; '' for none; None when unreadable."""
    if not isinstance(v, str):
        return None
    s = v.strip().lower()
    if s in _NAMED:
        return _NAMED[s]
    m = re.fullmatch(r"#?([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})", s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h[:6].upper()
    m = re.fullmatch(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,[^)]*)?\)", s)
    if m:
        return "#" + "".join(f"{min(255, int(g)):02X}" for g in m.groups())
    return None


def _rgb(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(v)))):02X}" for v in rgb)


def luminance(c: str) -> float:
    out = []
    for v in _rgb(c):
        s = v / 255.0
        out.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def readable(fg: str, backgrounds: list[str], need: float = MIN_CONTRAST) -> tuple[str, bool]:
    """(colour, changed): `fg` kept when it already reads on every background, else the nearest darker / lighter
    shade of it that does; black or white when no shade of it can (a background that runs from light to dark)."""
    bgs = [b for b in backgrounds if b]
    if not bgs or min(contrast(fg, b) for b in bgs) >= need:
        return fg, False
    dark_bg = sum(luminance(b) for b in bgs) / len(bgs) < 0.18
    target = "#FFFFFF" if dark_bg else "#000000"
    for step in range(1, 13):
        c = mix(fg, target, step / 12.0)
        if min(contrast(c, b) for b in bgs) >= need:
            return c, True
    best = max(("#000000", "#FFFFFF"), key=lambda c: min(contrast(c, b) for b in bgs))
    return best, True


def script_of(text: str) -> str:
    """The Indian (or Urdu) script most of the letters are in; '' for Latin / none."""
    counts: dict[str, int] = {}
    for ch in text:
        o = ord(ch)
        if o < 0x0600 or o > 0x0D7F:
            continue
        for name, ((lo, hi), _, _) in SCRIPTS.items():
            if lo <= o <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    return max(counts, key=counts.get) if counts else ""


def font_for(want: Any, chars: str, default: str = "Inter") -> str:
    """A font from the editor's list that can draw these letters."""
    fam = _FONT.get(str(want or "").strip().lower(), default)
    script = script_of(chars)
    if script:
        _, capable, fallback = SCRIPTS[script]
        if fam not in capable:
            return fallback
    return fam


def preset_for(prompt: str, given: str = "") -> str:
    """The size preset: the caller's choice, else the first one her words name; '' = let the model choose."""
    key = str(given or "").strip().lower()
    if key in PRESETS:
        return key
    low = str(prompt or "").lower()
    for pattern, name in _PRESET_WORDS:
        if re.search(pattern, low):
            return name
    return ""


# =============================================================================================== invented facts
_PHONE = re.compile(r"(?<![\w.])\+?\d[\d\s\-()]{8,}\d(?!\w)")
_PRICE = re.compile(r"(?<![A-Za-z])(₹|rs\.?|inr|\$|€|£)\s?(\d[\d,]*(?:\.\d+)?)(\s?(?:k|lakh|lac|crore|cr)\b)?", re.I)
_PRICE_TAIL = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s?(/-|rupees\b|rs\b)", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LOREM = re.compile(r"lorem\s+ipsum|dolor\s+sit\s+amet|consectetur\s+adipisc", re.I)


class Facts:
    """What the request (and her brand kit, and the text already on the canvas) really says. A phone number, a price
    or an email the model wrote that is NOT in there becomes a marked blank - never an invented fact on her design."""

    def __init__(self, *sources: str):
        blob = " ".join(s for s in sources if s)
        self.text = blob.lower()
        self.digits = re.sub(r"\D", "", blob)
        self.numbers = {re.sub(r"[,\s]", "", m).split(".")[0] for m in re.findall(r"\d[\d,]*(?:\.\d+)?", blob)}
        self.blanked = 0

    def _known(self, number: str) -> bool:
        whole = re.sub(r"[,\s]", "", number).split(".")[0]
        return whole in self.numbers

    def guard(self, chars: str) -> str:
        if not chars:
            return chars
        if _LOREM.search(chars):
            self.blanked += 1
            return "[Your text]"

        def phone(m: re.Match) -> str:
            d = re.sub(r"\D", "", m.group(0))
            if len(d) < 10 or d in self.digits or (len(d) > 10 and d[-10:] in self.digits):
                return m.group(0)
            self.blanked += 1
            return "[phone number]"

        def price(m: re.Match) -> str:
            if self._known(m.group(2)):
                return m.group(0)
            self.blanked += 1
            return f"{m.group(1)}[price]"

        def tail(m: re.Match) -> str:
            if self._known(m.group(1)):
                return m.group(0)
            self.blanked += 1
            return "₹[price]"

        def email(m: re.Match) -> str:
            if m.group(0).lower() in self.text:
                return m.group(0)
            self.blanked += 1
            return "[email]"

        out = _EMAIL.sub(email, chars)
        out = _PHONE.sub(phone, out)
        out = _PRICE.sub(price, out)
        return _PRICE_TAIL.sub(tail, out)


# =============================================================================================== cleaning the spec
class _Budget:
    def __init__(self, nodes: int = MAX_NODES):
        self.left = nodes
        self.dropped = 0


def _fill(v: Any) -> Any:
    """'#RRGGBB' | {'from','to','angle'} | '' (no fill) | None (not given / unreadable)."""
    if isinstance(v, dict):
        a, b = color(v.get("from")), color(v.get("to"))
        if a and b:
            return {"from": a, "to": b, "angle": _tidy(_num(v.get("angle"), 180, 0, 360))}
        return a or b or None
    return color(v)


def _stroke(v: Any) -> dict | None:
    if isinstance(v, str):
        c = color(v)
        return {"color": c, "width": 1} if c else None
    if isinstance(v, dict):
        c = color(v.get("color"))
        if c:
            return {"color": c, "width": _tidy(_num(v.get("width"), 1, 0.5, 24))}
    return None


def _pad(v: Any) -> list[int] | None:
    if isinstance(v, list) and v:
        vals = [_num(x, 0, 0, 400) or 0 for x in v[:4]]
        if len(vals) == 1:
            vals *= 4
        elif len(vals) == 2:
            vals = [vals[0], vals[1], vals[0], vals[1]]
        elif len(vals) == 3:
            vals = [vals[0], vals[1], vals[2], vals[1]]
        return [_snap(x) for x in vals]
    n = _num(v, None, 0, 400)
    return None if n is None else [_snap(n)] * 4


def _size(v: Any, lo: float = 1, hi: float = 8000) -> Any:
    if isinstance(v, str) and v.strip().lower() in ("hug", "fill"):
        return v.strip().lower()
    n = _num(v, None, lo, hi)
    return None if n is None else _tidy(n)


def _common(raw: dict, out: dict) -> None:
    name = _text(raw.get("name"), MAX_NAME).replace("\n", " ").strip()
    if name:
        out["name"] = name
    op = _num(raw.get("opacity"), None, 0, 1)
    if op is not None and op < 1:
        out["opacity"] = round(op, 2)
    for k in ("x", "y"):
        n = _num(raw.get(k), None, -8000, 8000)
        if n is not None:
            out[k] = _tidy(n)


def _look(raw: dict, out: dict) -> None:
    """fill / radius / stroke / shadow of a frame or a shape."""
    f = _fill(raw.get("fill"))
    if f is not None:
        out["fill"] = f
    r = _num(raw.get("radius"), None, 0, 2000)
    if r:
        out["radius"] = _tidy(r)
    s = _stroke(raw.get("stroke"))
    if s:
        out["stroke"] = s
    if raw.get("shadow") in SHADOWS:
        out["shadow"] = raw["shadow"]


def _text_props(raw: dict, out: dict, facts: Facts | None) -> None:
    if "chars" in raw or "text" in raw:
        chars = _text(raw.get("chars") if "chars" in raw else raw.get("text"), MAX_CHARS).strip("\n")
        out["chars"] = facts.guard(chars) if facts else chars
    n = _num(raw.get("size"), None, 8, 400)
    if n is not None:
        out["size"] = _tidy(n)
    n = _num(raw.get("weight"), None, 100, 900)
    if n is not None:
        out["weight"] = int(min(700, max(300, round(n / 100.0) * 100)))
    c = color(raw.get("color"))
    if c:
        out["color"] = c
    if raw.get("align") in ("left", "center", "right"):
        out["align"] = raw["align"]
    if isinstance(raw.get("font"), str) and raw["font"].strip().lower() in _FONT:
        out["font"] = _FONT[raw["font"].strip().lower()]
    n = _num(raw.get("lineHeight"), None, 0.8, 3)
    if n is not None:
        out["lineHeight"] = round(n, 2)
    n = _num(raw.get("letterSpacing"), None, -8, 40)
    if n:
        out["letterSpacing"] = _tidy(n)
    if raw.get("upper") is True:
        out["upper"] = True


def clean_node(raw: Any, depth: int, budget: _Budget, facts: Facts | None, assets: dict[str, dict]) -> dict | None:
    """One node of the spec with ONLY the keys this module understands; None = dropped."""
    if not isinstance(raw, dict) or depth > MAX_DEPTH:
        budget.dropped += 1
        return None
    kind = raw.get("type")
    kind = kind.strip().lower() if isinstance(kind, str) else ""
    if kind not in TYPES or budget.left <= 0:
        budget.dropped += 1
        return None
    budget.left -= 1
    out: dict[str, Any] = {"type": kind}
    _common(raw, out)
    if kind == "text":
        _text_props(raw, out, facts)
        if not out.get("chars"):
            budget.left += 1
            return None
        w = _size(raw.get("w"))
        if w is not None:
            out["w"] = w
        return out
    for k in ("w", "h"):
        v = _size(raw.get(k))
        if v is not None:
            out[k] = v
    if kind == "frame":
        lay = raw.get("layout")
        out["layout"] = lay if lay in ("row", "column", "none") else ("column" if raw.get("children") else "none")
        g = _num(raw.get("gap"), None, 0, 400)
        if g:
            out["gap"] = _snap(g)
        p = _pad(raw.get("pad"))
        if p and any(p):
            out["pad"] = p
        if raw.get("align") in ("start", "center", "end", "stretch"):
            out["align"] = raw["align"]
        if raw.get("justify") in ("start", "center", "end", "between"):
            out["justify"] = raw["justify"]
        if isinstance(raw.get("clip"), bool):
            out["clip"] = raw["clip"]
        _look(raw, out)
        kids = raw.get("children")
        out["children"] = []
        if isinstance(kids, list):
            for child in kids[:MAX_KIDS]:
                c = clean_node(child, depth + 1, budget, facts, assets)
                if c is not None:
                    out["children"].append(c)
            budget.dropped += max(0, len(kids) - MAX_KIDS)
    elif kind in ("rect", "ellipse"):
        _look(raw, out)
    elif kind == "line":
        c = color(raw.get("color"))
        if c:
            out["color"] = c
        out["width"] = _tidy(_num(raw.get("width"), 1, 0.5, 24))
    elif kind == "image":
        label = _text(raw.get("label"), 80).replace("\n", " ").strip()
        if label:
            out["label"] = label
        ref = raw.get("hash")
        if isinstance(ref, str) and ref in assets:
            out["hash"] = ref
        r = _num(raw.get("radius"), None, 0, 2000)
        if r:
            out["radius"] = _tidy(r)
        f = color(raw.get("fill"))
        if f:
            out["fill"] = f
    elif kind == "icon":
        name = icons.resolve(raw.get("icon") or raw.get("name"))
        if not name:
            budget.left += 1
            return None
        out["icon"] = name
        out.pop("w", None)
        out.pop("h", None)
        out["size"] = _tidy(_num(raw.get("size"), 24, 8, 512))
        c = color(raw.get("color"))
        if c:
            out["color"] = c
        if raw.get("filled") is True and name in icons.FILLABLE:
            out["filled"] = True
    return out


def _two_fonts(frames: list[dict]) -> None:
    """At most two font families in one design: the two most used stay, the rest become the main one."""
    count: dict[str, int] = {}

    def walk(n: dict) -> None:
        if n["type"] == "text" and n.get("font"):
            count[n["font"]] = count.get(n["font"], 0) + len(n.get("chars", ""))
        for c in n.get("children", ()):
            walk(c)

    for f in frames:
        walk(f)
    if len(count) <= 2:
        return
    keep = sorted(count, key=lambda k: -count[k])[:2]

    def fix(n: dict) -> None:
        if n["type"] == "text" and n.get("font") and n["font"] not in keep:
            n["font"] = keep[0]
        for c in n.get("children", ()):
            fix(c)

    for f in frames:
        fix(f)


def clean_spec(raw: Any, facts: Facts | None = None, assets: dict[str, dict] | None = None, preset: str = "",
               force: bool = False) -> dict:
    """The model's (or a template's) answer as a spec this module trusts. SpecError = there is nothing to draw.
    `preset` sizes a frame that names none; `force` = she chose the size herself, so it wins over the frame's own."""
    if isinstance(raw, list):
        raw = {"frames": raw}
    if not isinstance(raw, dict):
        raise SpecError("The answer must be one JSON object: {\"notes\": \"...\", \"frames\": [ ... ]}.")
    frames = raw.get("frames")
    if isinstance(frames, dict):
        frames = [frames]
    if not isinstance(frames, list) and raw.get("type") == "frame":
        frames = [raw]
    if not isinstance(frames, list) or not frames:
        raise SpecError('The answer has no "frames" list. Give {"frames": [ {"type": "frame", ...} ]}.')
    budget = _Budget()
    out: list[dict] = []
    for f in frames[:MAX_FRAMES]:
        if isinstance(f, dict) and f.get("type") in (None, "") and isinstance(f.get("children"), list):
            f = {**f, "type": "frame"}
        node = clean_node(f, 1, budget, facts, assets or {})
        if node is None or node["type"] != "frame" or not node.get("children"):
            continue
        key = str(f.get("preset") or "").strip().lower()
        node["preset"] = preset if (force and preset in PRESETS) or key not in PRESETS else key
        if node["preset"] not in PRESETS:
            node["preset"] = ""
        out.append(node)
    if not out:
        raise SpecError('No usable frame: every top-level item must be {"type": "frame", "children": [ ... ]} '
                        "with at least one child of a known type (frame, text, rect, ellipse, line, image, icon).")
    _two_fonts(out)
    return {"frames": out, "notes": _text(raw.get("notes"), 240).replace("\n", " ").strip(),
            "dropped": budget.dropped, "blanked": facts.blanked if facts else 0}


def count_nodes(spec: dict) -> int:
    def walk(n: dict) -> int:
        return 1 + sum(walk(c) for c in n.get("children", ()))
    return sum(walk(f) for f in spec.get("frames", ()))


# =============================================================================================== spec -> contract nodes
def _solid(c: str) -> dict:
    return {"type": "solid", "color": c, "opacity": 1, "visible": True}


def paints(fill: Any) -> list[dict]:
    if isinstance(fill, dict):
        a = math.radians(float(fill.get("angle", 180)) - 90)          # 180 = top to bottom, 90 = left to right
        dx, dy = math.cos(a) / 2, math.sin(a) / 2
        return [{"type": "linear", "stops": [{"pos": 0, "color": fill["from"], "opacity": 1},
                                             {"pos": 1, "color": fill["to"], "opacity": 1}],
                 "from": [round(0.5 - dx, 3), round(0.5 - dy, 3)], "to": [round(0.5 + dx, 3), round(0.5 + dy, 3)],
                 "opacity": 1, "visible": True}]
    return [_solid(fill)] if fill else []


def _look_props(n: dict, p: dict) -> None:
    if "fill" in n:
        p["fills"] = paints(n["fill"])
    if n.get("radius"):
        p["radius"] = n["radius"]
    if n.get("stroke"):
        p["strokes"] = [_solid(n["stroke"]["color"])]
        p["strokeWeight"] = n["stroke"]["width"]
        p["strokeAlign"] = "inside"
    if n.get("shadow"):
        p["effects"] = [dict(SHADOWS[n["shadow"]])]


def _line_height(size: float, mult: float | None) -> float | int:
    if mult is None:
        mult = 1.15 if size >= 40 else 1.25 if size >= 22 else 1.45
    return _tidy(max(1.0, round(size * mult)))


def text_props(n: dict, base: dict | None = None) -> dict:
    """Contract text properties from spec words (`base` = the node as it is now, for an edit)."""
    base = base or {}
    p: dict[str, Any] = {}
    chars = n.get("chars", base.get("chars", ""))
    if "chars" in n:
        p["chars"] = n["chars"]
    size = n.get("size", base.get("fontSize", 16))
    if "size" in n:
        p["fontSize"] = n["size"]
    if "weight" in n:
        p["fontWeight"] = n["weight"]
    font = font_for(n.get("font", base.get("font")), str(chars))
    if font != base.get("font", "Inter") or "font" in n:
        p["font"] = font
    if "lineHeight" in n or "size" in n or not base:
        p["lineHeight"] = _line_height(float(size), n.get("lineHeight"))
    if "letterSpacing" in n:
        p["letterSpacing"] = n["letterSpacing"]
    if "align" in n:
        p["align"] = n["align"]
    if n.get("upper"):
        p["textCase"] = "upper"
    if "color" in n:
        p["fills"] = [_solid(n["color"])]
    return p


class _Maker:
    """Turns cleaned spec nodes into contract nodes: `nodes` {id: props} in creation order, `kids` {id: [ids]}."""

    def __init__(self, new_id: Callable[[], str], assets: dict[str, dict] | None = None):
        self.new_id = new_id
        self.assets = assets or {}
        self.nodes: dict[str, dict] = {}
        self.kids: dict[str, list[str]] = {}
        self.unit = 1.0                      # how big this design is against a phone screen (a poster's labels are larger)

    def children(self, nid: str) -> list[str]:
        return self.kids.get(nid, [])

    def _add(self, parent: str, idx: str, props: dict) -> str:
        nid = self.new_id()
        self.nodes[nid] = {**props, "parent": parent, "idx": idx}
        self.kids.setdefault(parent, []).append(nid)
        return nid

    def _sizing(self, n: dict, p: dict, parent: str, parent_mode: str, default_w: Any, default_h: Any,
                fallback: tuple[float, float] = (100, 100)) -> None:
        """w / h of the spec ("fill" | "hug" | a number | nothing) as the contract's size + sizeH / sizeV."""
        pn = self.nodes.get(parent) or {}
        for axis, default, size_key, fb, at in (("w", default_w, "sizeH", fallback[0], "x"), ("h", default_h, "sizeV", fallback[1], "y")):
            v = n.get(axis, default)
            if v == "fill" and parent_mode == "none":           # a free frame's child: "fill" = up to the parent's edge
                room = pn.get(axis) if size_key not in pn else None
                v = max(1, room - (p.get(at) or 0)) if isinstance(room, (int, float)) else None
            if v == "fill":
                p[size_key] = "fill"
                p[axis] = fb
            elif v == "hug" and p.get("layout"):
                p[size_key] = "hug"
                p[axis] = fb
            elif isinstance(v, (int, float)):
                p[axis] = v
            else:
                p[axis] = fb

    def make(self, n: dict, parent: str, idx: str, parent_mode: str, top: bool = False) -> str:
        kind = n["type"]
        p: dict[str, Any] = {}
        if parent_mode == "none" and not top:
            p["x"], p["y"] = n.get("x", 0), n.get("y", 0)
        if "opacity" in n:
            p["opacity"] = n["opacity"]
        if kind == "text":
            return self._text(n, p, parent, idx, parent_mode)
        if kind == "frame":
            return self._frame(n, p, parent, idx, parent_mode, top)
        if kind in ("rect", "ellipse"):
            p.update(type=kind.upper(), name=n.get("name") or ("Rectangle" if kind == "rect" else "Ellipse"))
            _look_props(n, p)
            p.setdefault("fills", [_solid("#E5E7EB")])
            self._sizing(n, p, parent, parent_mode, None, None)
            return self._add(parent, idx, p)
        if kind == "line":
            p.update(type="RECT", name=n.get("name") or "Divider", fills=[_solid(n.get("color") or "#E5E7EB")],
                     h=max(1, n.get("width", 1)))
            w = n.get("w", "fill")
            if w == "fill" and parent_mode != "none":
                p["sizeH"], p["w"] = "fill", 100
            else:
                p["w"] = w if isinstance(w, (int, float)) else 100
            return self._add(parent, idx, p)
        if kind == "icon":
            return self._icon(n, p, parent, idx)
        return self._image(n, p, parent, idx, parent_mode)

    def _text(self, n: dict, p: dict, parent: str, idx: str, parent_mode: str) -> str:
        p.update(type="TEXT", name=n.get("name") or (n["chars"].split("\n")[0][:40] or "Text"))
        p.update(text_props({**n, "color": n.get("color", "#111827")}))
        p.setdefault("fontSize", 16)
        p.setdefault("font", font_for(None, n["chars"]))
        w = n.get("w")
        if w is None:
            w = "fill" if parent_mode == "column" and (len(n["chars"]) > 24 or "\n" in n["chars"]
                                                       or n.get("align") in ("center", "right")) else "hug"
        if w == "fill" and parent_mode != "none":
            p.update(sizeH="fill", autoResize="h", w=100)
        elif isinstance(w, (int, float)):
            p.update(autoResize="h", w=w)
        else:
            p["autoResize"] = "wh"
        return self._add(parent, idx, p)

    def _frame(self, n: dict, p: dict, parent: str, idx: str, parent_mode: str, top: bool) -> str:
        mode = n.get("layout", "none")
        p.update(type="FRAME", name=n.get("name") or ("Frame" if not top else "Screen"))
        if mode in ("row", "column"):
            lay: dict[str, Any] = {"mode": "h" if mode == "row" else "v", "gap": n.get("gap", 0),
                                   "pad": n.get("pad", [0, 0, 0, 0]), "alignMain": n.get("justify", "start"),
                                   "alignCross": n.get("align", "start"), "wrap": False}
            p["layout"] = lay
        _look_props(n, p)
        p.setdefault("fills", [])
        if top:
            p["clip"] = n.get("clip", True)
        else:
            p["clip"] = n.get("clip", bool(n.get("radius")) and mode != "none")
        if top:
            p["w"], p["h"] = n["_w"], n["_h"]
            if n.get("_hug_h") and p.get("layout"):
                p["sizeV"], p["minH"] = "hug", n["_h"]
        else:
            dw = "fill" if parent_mode == "column" else "hug"
            self._sizing(n, p, parent, parent_mode, dw if mode != "none" or parent_mode == "column" else None,
                         "hug" if mode != "none" else None)
        nid = self._add(parent, idx, p)
        kids = n.get("children", [])
        for child, cidx in zip(kids, fracidx.n_between(None, None, len(kids))):
            self.make(child, nid, cidx, mode)
        if mode == "none" and not top:                       # a free frame with no size given wraps its children
            ext_w = max((self.nodes[c].get("x", 0) + self.nodes[c].get("w", 0) for c in self.children(nid)), default=100)
            ext_h = max((self.nodes[c].get("y", 0) + self.nodes[c].get("h", 0) for c in self.children(nid)), default=100)
            if not isinstance(n.get("w"), (int, float)) and "sizeH" not in p:
                self.nodes[nid]["w"] = _tidy(max(1, ext_w))
            if not isinstance(n.get("h"), (int, float)) and "sizeV" not in p:
                self.nodes[nid]["h"] = _tidy(max(1, ext_h))
        return nid

    def _icon(self, n: dict, p: dict, parent: str, idx: str) -> str:
        size = n.get("size", 24)
        art = icons.build(n["icon"], size)
        p.update(type="FRAME", name=n.get("name") or f"Icon / {n['icon']}", w=size, h=size, fills=[], clip=False)
        nid = self._add(parent, idx, p)
        if art:
            paint = [_solid(n.get("color") or "#111827")]
            v: dict[str, Any] = {"type": "VECTOR", "name": n["icon"], "x": art["x"], "y": art["y"], "w": art["w"],
                                 "h": art["h"], "path": art["path"]}
            if n.get("filled"):
                v.update(fills=paint, strokes=[])
            else:
                v.update(fills=[], strokes=paint, strokeWeight=_tidy(max(1.25, size / 12.0)), strokeCap="round",
                         strokeJoin="round", strokeAlign="center")
            self._add(nid, fracidx.between(None, None), v)
        return nid

    def _image(self, n: dict, p: dict, parent: str, idx: str, parent_mode: str) -> str:
        asset = self.assets.get(n.get("hash", ""))
        dw = "fill" if parent_mode == "column" else 160
        if asset:
            p.update(type="RECT", name=n.get("name") or n.get("label") or "Image",
                     fills=[{"type": "image", "hash": asset["hash"], "mode": "fit", "opacity": 1, "visible": True}])
            if n.get("radius"):
                p["radius"] = n["radius"]
            if not isinstance(n.get("w"), (int, float)) and not isinstance(n.get("h"), (int, float)) and asset.get("w"):
                n = {**n, "w": min(480, asset["w"]), "h": _tidy(min(480, asset["w"]) * asset["h"] / max(1, asset["w"]))}
            self._sizing(n, p, parent, parent_mode, dw, 160, (160, 160))
            return self._add(parent, idx, p)
        tint = n.get("fill") or "#E2E8F0"
        ink = readable(mix(tint, "#000000", 0.45), [tint])[0]
        p.update(type="FRAME", name=n.get("name") or f"Image / {n.get('label') or 'placeholder'}", fills=[_solid(tint)],
                 clip=True, layout={"mode": "v", "gap": 8, "pad": [12, 12, 12, 12], "alignMain": "center",
                                    "alignCross": "center", "wrap": False})
        if n.get("radius"):
            p["radius"] = n["radius"]
        self._sizing(n, p, parent, parent_mode, dw, 160, (160, 160))
        nid = self._add(parent, idx, p)
        small = min(p["w"] if "sizeH" not in p else 999, p["h"] if "sizeV" not in p else 999) < 96
        u = self.unit ** 0.85
        a, b = fracidx.n_between(None, None, 2)
        self.make({"type": "icon", "icon": "image", "size": 20 if small else int(min(96, round(30 * u))), "color": ink}, nid, a, "column")
        if n.get("label") and not small:
            self.make({"type": "text", "chars": f"[{n['label']}]", "size": int(min(44, max(13, round(14 * u)))), "weight": 500,
                       "color": ink, "align": "center", "w": "fill"}, nid, b, "column")
        return nid


# =============================================================================================== contrast
def _abs_boxes(nodes: dict[str, dict], kids: Callable[[str], list[str]], root: str) -> dict[str, tuple]:
    box: dict[str, tuple] = {}
    stack = [(root, 0.0, 0.0)]
    while stack:
        nid, ox, oy = stack.pop()
        n = nodes[nid]
        x, y = ox + (n.get("x") or 0), oy + (n.get("y") or 0)
        box[nid] = (x, y, n.get("w") or 0, n.get("h") or 0)
        stack.extend((c, x, y) for c in kids(nid) if c in nodes)
    return box


def _paint_colours(n: dict) -> list[str] | None:
    """The colours of a node's top visible fill: [c] solid, [a, b] gradient ends; [] = an image (unknown); None = no fill."""
    for paint in reversed(n.get("fills") or []):
        if not isinstance(paint, dict) or paint.get("visible") is False or (paint.get("opacity", 1) or 0) < 0.5:
            continue
        if paint.get("type") == "solid" and isinstance(paint.get("color"), str):
            return [paint["color"]]
        if paint.get("type") in ("linear", "radial", "angular"):
            cols = [s.get("color") for s in paint.get("stops") or [] if isinstance(s, dict) and isinstance(s.get("color"), str)]
            return cols[:1] + cols[-1:] if cols else None
        if paint.get("type") == "image":
            return []
    return None


def background_of(nodes: dict[str, dict], kids: Callable[[str], list[str]], box: dict[str, tuple], nid: str,
                  page_bg: str = PAGE_BG) -> list[str]:
    """The colours really behind a node's centre: a shape lying under it in a free frame, else the nearest filled
    frame above it, else the page. [] = a picture is behind it (not judged)."""
    x, y, w, h = box[nid]
    cx, cy = x + w / 2, y + h / 2
    cur, flow = nid, ailayout.Layout(nodes, kids)
    for _ in range(64):
        parent = nodes[cur].get("parent")
        pn = nodes.get(parent) if isinstance(parent, str) else None
        if pn is None or pn.get("type") in ("PAGE", "DOCUMENT"):
            return [color((pn or {}).get("bg")) or page_bg]
        if parent in box and cur in box and not flow.has_layout(pn):
            sibs = kids(parent)
            for sib in reversed(sibs[:sibs.index(cur)] if cur in sibs else []):
                sn = nodes.get(sib)
                if not sn or sn.get("visible") is False or (sn.get("opacity", 1) or 0) < 0.5 or sib not in box:
                    continue
                sx, sy, sw, sh = box[sib]
                if sx <= cx <= sx + sw and sy <= cy <= sy + sh and sn.get("type") in ("RECT", "ELLIPSE", "FRAME"):
                    cols = _paint_colours(sn)
                    if cols is not None:
                        return cols
        if (pn.get("opacity", 1) or 0) >= 0.5:
            cols = _paint_colours(pn)
            if cols is not None:
                return cols
        cur = parent
    return [page_bg]


def fix_contrast(nodes: dict[str, dict], kids: Callable[[str], list[str]], root: str, only: set[str] | None = None,
                 page_bg: str = PAGE_BG) -> int:
    """Every text under `root` must read on what is behind it (4.5:1): a colour that does not is darkened or
    lightened until it does. Returns how many texts were changed."""
    box = _abs_boxes(nodes, kids, root)
    fixed = 0
    for nid in box:
        n = nodes[nid]
        if n.get("type") != "TEXT" or (only is not None and nid not in only):
            continue
        fills = n.get("fills") or []
        fg = fills[-1].get("color") if fills and isinstance(fills[-1], dict) and fills[-1].get("type") == "solid" else None
        if not isinstance(fg, str) or color(fg) is None:
            continue
        bgs = [b for b in (color(c) for c in background_of(nodes, kids, box, nid, page_bg)) if b]
        new, changed = readable(color(fg), bgs)
        if changed:
            n["fills"] = [_solid(new)]
            fixed += 1
    return fixed


def _unsqueeze(nodes: dict[str, dict], kids: Callable[[str], list[str]], root: str) -> bool:
    """A one-line text wider than the room its parent has becomes a wrapping text (fill). True = something changed."""
    lay = ailayout.Layout(nodes, kids)
    hit = False
    stack = [root]
    while stack:
        nid = stack.pop()
        n = nodes[nid]
        stack.extend(kids(nid))
        parent = nodes.get(n.get("parent"))
        if n.get("type") != "TEXT" or n.get("autoResize", "wh") != "wh" or not parent or not lay.has_layout(parent):
            continue
        pad = parent["layout"].get("pad") or [0, 0, 0, 0]
        horiz = parent["layout"].get("mode") == "h"
        if parent.get("sizeH") == "hug":
            continue
        room = (parent.get("w") or 0) - pad[1] - pad[3]
        if horiz:
            others = [nodes[c] for c in kids(n["parent"]) if c != nid and nodes[c].get("sizeH") != "fill"]
            room -= sum(o.get("w") or 0 for o in others) + (parent["layout"].get("gap") or 0) * max(0, len(kids(n["parent"])) - 1)
        if (n.get("w") or 0) > room + 0.5 and room > 24:
            n.update(sizeH="fill", autoResize="h")
            hit = True
    return hit


# =============================================================================================== build
def frame_size(frame: dict) -> tuple[float, float, bool]:
    """(w, h, the height hugs the content) of a top-level frame: its preset, else its own numbers."""
    key = frame.get("preset") or ""
    if key in PRESETS:
        _, w, h, hug = PRESETS[key]
        return w, h, hug
    w = frame.get("w") if isinstance(frame.get("w"), (int, float)) else 390
    h = frame.get("h") if isinstance(frame.get("h"), (int, float)) else 844
    return min(4000, max(120, w)), min(8000, max(120, h)), frame.get("h") == "hug"


def build(spec: dict, new_id: Callable[[], str], parent: str, at: tuple[float, float], after_idx: str | None = None,
          assets: dict[str, dict] | None = None, mark: str = "") -> dict:
    """Cleaned spec -> {ops, roots, nodes, fixed}. Frames stand side by side from `at`, 80 px apart."""
    maker = _Maker(new_id, assets)
    roots: list[str] = []
    x, y = float(at[0]), float(at[1])
    idx = after_idx
    fixed = 0
    for frame in spec["frames"][:MAX_FRAMES]:
        w, h, hug = frame_size(frame)
        idx = fracidx.between(idx, None)
        f = {**frame, "_w": w, "_h": h, "_hug_h": hug}
        maker.unit = max(1.0, min(w, h) / 400.0)
        f.setdefault("fill", "#FFFFFF")
        rid = maker.make(f, parent, idx, "none", top=True)
        root = maker.nodes[rid]
        root.update(x=_tidy(x), y=_tidy(y))
        if mark:
            root["aiSettle"] = mark
        ailayout.run(maker.nodes, maker.children, rid)
        if _unsqueeze(maker.nodes, maker.children, rid):
            ailayout.run(maker.nodes, maker.children, rid)
        fixed += fix_contrast(maker.nodes, maker.children, rid)
        roots.append(rid)
        x += (root.get("w") or w) + FRAME_GAP
    STATS["contrast_fixed"] += fixed
    ops = [{"id": nid, "p": props} for nid, props in maker.nodes.items()]
    return {"ops": ops, "roots": roots, "nodes": maker.nodes, "fixed": fixed}


def spec_to_ops(spec: dict, new_id: Callable[[], str], parent: str, at: tuple[float, float]) -> list[dict]:
    """The ops that create a cleaned spec under `parent` at `at` (ids only from `new_id`, parents before children)."""
    return build(spec, new_id, parent, at)["ops"]


def id_maker(cid: int) -> Callable[[], str]:
    counter = [0]

    def new_id() -> str:
        counter[0] += 1
        return f"{cid}:{counter[0]}"
    return new_id


def place(nodes: dict[str, dict], page: str, size: tuple[float, float], want: tuple[float, float] | None) -> tuple[float, float, str | None]:
    """(x, y, the last child's idx) for new frames on a page: centred on the asked point when that spot is free,
    else to the right of everything already there."""
    kids = [(n.get("idx", ""), nid) for nid, n in nodes.items() if n.get("parent") == page]
    last = max(kids)[0] if kids else None
    boxes = [(n.get("x") or 0, n.get("y") or 0, n.get("w") or 0, n.get("h") or 0)
             for _, nid in kids for n in (nodes[nid],) if n.get("visible") is not False]
    w, h = size
    if want is not None:
        x, y = round(want[0] - w / 2), round(want[1] - min(h, 900) / 2)
        if not any(x < bx + bw + 40 and bx < x + w + 40 and y < by + bh + 40 and by < y + h + 40 for bx, by, bw, bh in boxes):
            return x, y, last
    if not boxes:
        return 0, 0, last
    return round(max(bx + bw for bx, by, bw, bh in boxes) + 100), round(min(by for bx, by, bw, bh in boxes)), last


# =============================================================================================== the model
RULEBOOK = """DESIGN RULES - a senior designer's checklist. Follow every one.
1. SPACING only from the 8-point scale: 4 8 12 16 24 32 40 48 64 80 96 (big posters / slides: also 120, 160). Things
   that belong together sit close; groups are clearly apart. Outer padding: phone 20-24; a 1440 web section 80-120 at
   the sides and 64-96 above / below; a 1080 post or story 72-96; a slide 96-120.
2. ONE TYPE SCALE per design. phone: 12 14 16 20 24 32. web: 14 16 18 24 32 48 64. 1080 post / story: 28 36 48 72 96 128.
   slide: 24 32 40 56 80 112. poster: 28 36 48 72 120 160. Body text never under 14 on a phone, 16 on the web, 28 on a
   1080 post. Headlines weight 600-700 with lineHeight 1.05-1.2; body weight 400 with lineHeight 1.4-1.6.
3. AT MOST 2 FONT FAMILIES: one for headings, one for body (or one for both). Only fonts from FONTS.
4. COLOUR: one neutral family (background, surface, border, text) + ONE accent colour (and its light tint). Roughly 60 %
   background, 30 % surface / text, 10 % accent. Text must read: contrast at least 4.5:1 against what is behind it
   (code checks this and will change a colour that fails). No pure black text on pure white: use a deep neutral.
5. ONE RADIUS FAMILY: choose 8, 12, 16 or 24 and reuse it; pills use 999. Cards inside cards get a smaller radius.
6. HIERARCHY: one focal point per frame, ONE primary button, at most three text sizes visible in one group. Secondary
   text is lighter in colour, not smaller than the scale allows.
7. LAYOUT: everything is rows and columns (auto layout). layout "none" only for decoration that overlaps (big soft
   circles, colour blocks behind content): put the decoration first, then ONE content frame on top of it with x 0, y 0
   and the full size. Never place ordinary content with x / y.
8. SIZES: buttons at least 48 tall on a phone and 44 on the web (pad [14, 24, 14, 24] or more); inputs 48-56 tall; a
   list row at least 56; icons 20-24 in text rows, 28-40 in feature tiles. A bottom navigation bar on a phone screen:
   make the content frame h "fill" and the bar the last child, so the bar sits at the bottom.
9. REAL CONTENT ONLY, from the request's own words. Never lorem ipsum. NEVER invent a price, a phone number, an
   address, an email, a date, a rating, a percentage, a statistic, or the name of a person or a business. A fact you
   were not given is a marked blank in square brackets: "[price]", "[phone number]", "[your address]", "[date]",
   "[your business name]". Ordinary interface words ("Search", "Add to cart", "Continue", "See all") are fine.
10. LANGUAGE: write every text in the language AND script of the request (Hindi in Devanagari with a font from the
   Indian-language part of FONTS; Hinglish in Roman letters; English in English).
11. FILL THE FRAME like a finished design: a phone screen = top area (pad top 56), the content, a clear action; a web
   page = navigation, a hero with headline + one line + button(s) + picture, 2-3 sections, a footer; a post / story /
   poster = ONE message, large, with the supporting facts small and a clear contact / action line.
12. PICTURES are placeholders: {"type":"image","label":"what the photo should show"} - never a drawing made of shapes.
    Use the brand logo only as {"type":"image","hash":"logo"} and only when ASSETS lists "logo".
13. Be compact: at most about 90 nodes per frame. No empty frames, no hidden layers, names in plain words."""

GRAMMAR = """ANSWER FORMAT - ONE JSON object and nothing else (no markdown fence, no comment):
{"notes":"one short sentence about the design","frames":[FRAME, ...]}
One frame unless the request asks for several screens / sizes (then one per screen, at most 6; they are placed side by side).
You never write ids, ops or the positions of laid-out children: code lays everything out and assigns the ids.

A top-level FRAME: {"type":"frame","name":"Home","preset":"phone","layout":"column", ... , "children":[NODE, ...]}
NODE types and their properties (anything else is dropped):
 frame   name, layout "column" | "row" | "none", gap, pad (a number or [top, right, bottom, left]),
         align (across the layout direction: "start" | "center" | "end" | "stretch"),
         justify (along it: "start" | "center" | "end" | "between"), w, h, fill, radius, stroke {"color","width"},
         shadow "sm" | "md" | "lg", opacity, clip, children
 text    chars, size, weight (400 | 500 | 600 | 700), color, align "left" | "center" | "right", font,
         lineHeight (a multiplier such as 1.2), letterSpacing, upper (true = capitals), w, opacity
 rect / ellipse   w, h, fill, radius, stroke, shadow, opacity
 line    a divider across its parent: color, width (its thickness)
 image   a picture placeholder: label, w, h, radius
 icon    icon (a name from ICONS), color, size (default 24), filled (true for a solid star / heart / play / bolt)
 w / h   a number (px), "fill" (take the free room of the parent) or "hug" (fit the content). Defaults: a frame
         inside a column is "fill" wide and "hug" tall; inside a row it hugs; a longer text inside a column wraps at
         the column's width. Give a text "w":"fill" inside a row when it should take the remaining room.
 fill    "#RRGGBB", or a gradient {"from":"#RRGGBB","to":"#RRGGBB","angle":180} (180 = top to bottom, 90 = left to right)
 x, y    ONLY for children of a layout "none" frame. Later children are drawn on top of earlier ones."""

EXAMPLE = """A small example of the style (a card on a phone screen):
{"type":"frame","name":"Offer card","layout":"column","gap":12,"pad":20,"radius":20,"fill":{"from":"#4F46E5","to":"#3730A3","angle":135},"children":[
 {"type":"text","chars":"FESTIVE OFFER","size":12,"weight":600,"color":"#C7D2FE","letterSpacing":1.5},
 {"type":"text","chars":"Sweets for every celebration","size":24,"weight":700,"color":"#FFFFFF","lineHeight":1.15},
 {"type":"frame","name":"Button","layout":"row","gap":8,"pad":[12,18,12,18],"radius":999,"fill":"#FFFFFF","align":"center","w":"hug","children":[
  {"type":"text","chars":"Order now","size":14,"weight":600,"color":"#3730A3"},{"type":"icon","icon":"arrow-right","size":18,"color":"#3730A3"}]}]}"""


def system_prompt() -> str:
    presets = "; ".join(f'"{k}" = {v[0]} {v[1]} x {v[2]}{" (grows with its content)" if v[3] else ""}' for k, v in PRESETS.items())
    return ("You are Hoola's designer: a senior product and graphic designer. You turn ONE request into a finished, "
            "professional design for the Hoola Design editor.\n\n" + GRAMMAR + "\n\nPRESETS (the \"preset\" of a top-level "
            "frame sets its size): " + presets + ". Without a fitting preset give the frame a numeric w and h.\n"
            "ICONS: " + ", ".join(sorted(icons.ICONS)) + ".\nFONTS: " + ", ".join(FONTS) + ".\n\n" + RULEBOOK + "\n\n" + EXAMPLE)


EDIT_GRAMMAR = """You are changing an existing design in the Hoola Design editor. The selected layers are listed below
as short handles (n1, n2 ...), indented like the layer tree.

ANSWER FORMAT - ONE JSON object and nothing else:
{"notes":"one short sentence saying what you changed",
 "changes":[{"handle":"n3","set":{PROPERTIES}}, ...],
 "add":[{"parent":"n1","after":"n4","node":NODE}, ...]}
"changes": only the properties that really change, in the same words as below. A frame takes: name, layout, gap, pad,
align, justify, fill, radius, stroke, shadow, opacity, w, h. A text takes: name, chars, size, weight, color, align,
font, lineHeight, letterSpacing, upper, opacity. A shape takes: name, fill, radius, stroke, shadow, opacity, w, h.
"add": new children for a FRAME handle ("after" = the handle of the sibling it follows; leave it out to add at the
end). NODE is written exactly like in a new design (see NODE types). Use "add" only when the request asks for
something new (a section, a button, a line of text).
You can NOT delete, move, regroup or retype layers, and you can not touch layers outside the selection: if the request
needs that, change what you can and say the rest in "notes".
Keep what the request does not mention exactly as it is. Translate or rewrite text only when asked."""


def edit_system_prompt() -> str:
    node_part = GRAMMAR.split("NODE types and their properties", 1)[1]
    return (EDIT_GRAMMAR + "\n\nNODE types and their properties" + node_part + "\nICONS: " + ", ".join(sorted(icons.ICONS))
            + ".\nFONTS: " + ", ".join(FONTS) + ".\n\n" + RULEBOOK)


_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from anthropic import AsyncAnthropic
        st = get_settings()
        _CLIENT = AsyncAnthropic(api_key=st.anthropic_api_key, timeout=float(getattr(st, "design_ai_timeout_s", 120)),
                                 max_retries=1)
    return _CLIENT


def model_ready() -> str:
    """'claude' / the cheap brain's name when a model can be asked, '' when none is configured (-> templates)."""
    st = get_settings()
    if getattr(st, "design_ai_engine", "auto") == "template":
        return ""
    if st.anthropic_api_key:
        return "claude"
    try:
        from ..agent import llm
        return llm.cheap_brain() or ""
    except Exception:   # noqa: BLE001
        return ""


async def _ask(system: str, user: str, max_tokens: int, tenant: str = "") -> str:
    """One model call through the house door, counted under the feature 'design'."""
    from .. import usage
    from ..agent import door
    st = get_settings()
    with usage.scope(tenant or None, "design"):
        if st.anthropic_api_key:
            model = door.model_for("design_ai_model", st.anthropic_model)
            msg = await door.acreate(_client(), door.shape("design", model, max_tokens, system,
                                                           [{"role": "user", "content": user}], tenant=tenant))
            return "".join(getattr(b, "text", "") or "" for b in msg.content)
        from ..agent import llm
        brain = llm.cheap_brain()
        if not brain:
            raise AiError("No AI model is configured on this server.", 503)
        blocks, _, _ = await llm.openai_create(brain, system, [], [{"role": "user", "content": user}], min(max_tokens, 12000))
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def parse_json(raw: str) -> Any:
    """The first JSON object in the reply (a fence or a sentence around it is ignored). SpecError when there is none."""
    text = str(raw or "")
    start = text.find("{")
    if start < 0:
        raise SpecError("The answer was not JSON. Reply with ONE JSON object and nothing else.")
    try:
        value, _ = json.JSONDecoder(parse_constant=lambda name: None).raw_decode(text[start:])
    except (ValueError, RecursionError) as e:
        raise SpecError(f"The JSON could not be read ({str(e)[:120]}). It may be cut off: answer again, complete and "
                        "more compact (fewer nodes), as ONE JSON object.") from None
    return value


async def _asked(system: str, user: str, max_tokens: int, tenant: str, check: Callable[[Any], Any]) -> Any:
    """Ask, validate, and on a bad answer ask ONCE more with the error fed back. AiError after that."""
    st = get_settings()
    timeout = float(getattr(st, "design_ai_timeout_s", 120))
    said, last = user, ""
    for attempt in (0, 1):
        try:
            raw = await asyncio.wait_for(_ask(system, said, max_tokens, tenant), timeout)
        except asyncio.TimeoutError:
            STATS["failed"] += 1
            raise AiError("Hoola took too long to design this. Please try again, or ask for something smaller.", 504) from None
        except AiError:
            raise
        except Exception as e:   # noqa: BLE001 - the model / the network refused: said plainly, never a silent fallback
            STATS["failed"] += 1
            log.warning("design model call failed: %s", str(e)[:300])
            raise AiError("Hoola could not reach its design model just now. Nothing was added; please try again.") from None
        try:
            return check(parse_json(raw))
        except SpecError as e:
            last = str(e)
            if attempt == 0:
                STATS["retries"] += 1
                said = (user + "\n\nYOUR PREVIOUS ANSWER COULD NOT BE USED: " + last
                        + "\nAnswer again with ONE complete JSON object in the format above.")
    STATS["failed"] += 1
    log.warning("design model answered twice without a usable spec: %s", last[:200])
    raise AiError("Hoola could not turn this into a design (the model's answer was not usable twice). "
                  "Nothing was added; please try again or say it another way.")


def brand_block(brand: dict) -> str:
    lines = [f"name: {brand['name']}"] if brand.get("name") else []
    if brand.get("tagline"):
        lines.append(f"tagline: {brand['tagline']}")
    cols = brand.get("colors") or {}
    if cols:
        lines.append("colours: " + ", ".join(f"{k} {v}" for k, v in cols.items()))
    for k, v in (brand.get("contact") or {}).items():
        lines.append(f"{k}: {v}")
    if not lines:
        return ""
    return ("BRAND (hers - use these colours as the palette and these facts where they fit; they are real):\n  "
            + "\n  ".join(lines))


def user_message(prompt: str, context: dict) -> str:
    parts = ["REQUEST: " + prompt.strip()]
    preset = context.get("preset") or ""
    if preset in PRESETS:
        p = PRESETS[preset]
        parts.append(f'SIZE: use the preset "{preset}" ({p[0]}, {p[1]} x {p[2]}) for every frame.')
    block = brand_block(context.get("brand") or {})
    if block:
        parts.append(block)
    assets = context.get("assets") or {}
    if assets:
        parts.append("ASSETS: " + ", ".join(f'"{k}" ({v.get("w")} x {v.get("h")})' for k, v in assets.items()))
    variant = int(context.get("variant") or 0)
    if variant:
        parts.append(f"VARIATION {variant}: this is one of several options for the same request. Take a clearly "
                     "different direction from the obvious one: " + ("a bold, high-contrast layout with large type.",
                                                                    "a calm, airy layout with a light palette.",
                                                                    "a dark, premium look with one bright accent.")[(variant - 1) % 3])
    return "\n\n".join(parts)


async def generate(prompt: str, context: dict | None = None) -> dict:
    """prompt + context {preset, brand, assets, variant, tenant} -> a cleaned spec (spec["engine"] says who made it:
    "model", or "template" when no model is configured on this server)."""
    context = dict(context or {})
    prompt = _text(prompt, PROMPT_MAX).strip()
    if not prompt:
        raise AiError("Say in a line what Hoola should design.", 400)
    force = str(context.get("preset") or "").strip().lower() in PRESETS           # her own choice of size
    preset = context["preset"] = preset_for(prompt, context.get("preset") or "")
    brand = context.get("brand") or {}
    facts = Facts(prompt, json.dumps(brand, ensure_ascii=False) if brand else "")
    assets = context.get("assets") or {}
    if not model_ready():
        from . import templates
        spec = clean_spec(templates.make(prompt, preset, brand, int(context.get("variant") or 0), assets), None, assets, preset, force)
        spec["engine"] = "template"
        STATS["template"] += 1
        return spec
    spec = await _asked(system_prompt(), user_message(prompt, context), 9000, context.get("tenant") or "",
                        lambda raw: clean_spec(raw, facts, assets, preset, force))
    spec["engine"] = "model"
    STATS["model"] += 1
    return spec


# =============================================================================================== edit
_FRAME_SET = {"name", "layout", "gap", "pad", "align", "justify", "fill", "radius", "stroke", "shadow", "opacity", "w", "h"}
_TEXT_SET = {"name", "chars", "text", "size", "weight", "color", "align", "font", "lineHeight", "letterSpacing", "upper", "opacity"}
_SHAPE_SET = {"name", "fill", "radius", "stroke", "shadow", "opacity", "w", "h"}
_EDITABLE = {"FRAME": _FRAME_SET, "COMPONENT": _FRAME_SET, "SECTION": _FRAME_SET, "TEXT": _TEXT_SET, "RECT": _SHAPE_SET,
             "ELLIPSE": _SHAPE_SET, "POLYGON": _SHAPE_SET, "STAR": _SHAPE_SET, "VECTOR": {"name", "fill", "opacity"}}
EDIT_MAX_NODES = 160


def _first_colour(paint_list: Any) -> str:
    cols = _paint_colours({"fills": paint_list}) if isinstance(paint_list, list) else None
    if not cols:
        return ""
    return cols[0] if len(cols) == 1 else f"{cols[0]}->{cols[1]}"


def describe(nodes: dict[str, dict], kids: Callable[[str], list[str]], selection: list[str]) -> tuple[str, dict[str, str]]:
    """The selected subtrees as indented lines with handles, and handle -> node id. Real ids never reach the model."""
    handles: dict[str, str] = {}
    lines: list[str] = []

    def walk(nid: str, depth: int) -> None:
        if len(handles) >= EDIT_MAX_NODES or depth > MAX_DEPTH + 2:
            return
        n = nodes.get(nid)
        if not n or n.get("type") in ("DOCUMENT", "PAGE"):
            return
        h = f"n{len(handles) + 1}"
        handles[h] = nid
        kind = str(n.get("type", "")).lower()
        bits = [h, kind, json.dumps(str(n.get("name", ""))[:40], ensure_ascii=False)]
        if kind == "text":
            chars = str(n.get("chars", ""))
            bits = [h, "text", json.dumps(chars[:200] + ("…" if len(chars) > 200 else ""), ensure_ascii=False),
                    f"size={n.get('fontSize', 16)}", f"weight={n.get('fontWeight', 400)}", f"font={n.get('font', 'Inter')}"]
            c = _first_colour(n.get("fills"))
            if c:
                bits.append(f"color={c}")
            if n.get("align"):
                bits.append(f"align={n['align']}")
        else:
            bits.append(f"{_tidy(n.get('w') or 0)}x{_tidy(n.get('h') or 0)}")
            lay = n.get("layout") if isinstance(n.get("layout"), dict) else None
            if lay and lay.get("mode") in ("h", "v"):
                bits.append("row" if lay["mode"] == "h" else "column")
                bits.append(f"gap={lay.get('gap', 0)}")
                bits.append(f"pad={json.dumps(lay.get('pad', 0))}")
            c = _first_colour(n.get("fills"))
            if c:
                bits.append(f"fill={c}")
            if n.get("radius"):
                bits.append(f"radius={json.dumps(n['radius'])}")
        lines.append("  " * depth + " ".join(str(b) for b in bits))
        if kind not in ("text", "vector", "instance"):
            for c in kids(nid):
                walk(c, depth + 1)

    for nid in selection:
        walk(nid, 0)
    return "\n".join(lines), handles


def _spec_mode(n: dict) -> str:
    lay = n.get("layout") if isinstance(n.get("layout"), dict) else None
    return {"h": "row", "v": "column"}.get((lay or {}).get("mode"), "none")


def changes_to_props(node: dict, raw: Any, facts: Facts | None, refused: list[str], handle: str = "") -> dict:
    """One {handle, set} of the model as contract properties of an existing node. A property this node type may
    not be given by an edit (type, parent, order, position, prototype links ...) is refused and listed."""
    if not isinstance(raw, dict):
        return {}
    kind = node.get("type")
    allowed = _EDITABLE.get(kind)
    if allowed is None:
        refused.append(f"{handle}: a {str(kind).lower()} can not be changed by an edit")
        return {}
    for key in raw:
        if key not in allowed:
            refused.append(f"{handle}.{str(key)[:24]}")
    take = {k: v for k, v in raw.items() if k in allowed}
    p: dict[str, Any] = {}
    name = _text(take.get("name"), MAX_NAME).replace("\n", " ").strip()
    if name:
        p["name"] = name
    op = _num(take.get("opacity"), None, 0, 1)
    if op is not None:
        p["opacity"] = round(op, 2)
    if kind == "TEXT":
        clean: dict[str, Any] = {}
        _text_props(take, clean, facts)
        if "chars" in clean and not clean["chars"]:
            clean.pop("chars")
        if clean.get("upper"):
            p["textCase"] = "upper"
        p.update(text_props(clean, node))
        return p
    clean = {}
    _look(take, clean)
    look: dict[str, Any] = {}
    _look_props(clean, look)
    if kind == "VECTOR":
        look = {k: v for k, v in look.items() if k == "fills"}
        if look.get("fills") and not node.get("fills") and node.get("strokes"):
            look = {"strokes": look["fills"]}                 # a stroke icon is recoloured through its stroke
    p.update(look)
    if "radius" in take and "radius" not in p and _num(take.get("radius"), None, 0, 2000) == 0:
        p["radius"] = 0
    if kind in ("FRAME", "COMPONENT", "SECTION"):
        lay = dict(node.get("layout")) if isinstance(node.get("layout"), dict) else None
        touched = False
        want = take.get("layout")
        if want in ("row", "column"):
            lay = {"mode": "h" if want == "row" else "v", "gap": (lay or {}).get("gap", 0), "pad": (lay or {}).get("pad", [0, 0, 0, 0]),
                   "alignMain": (lay or {}).get("alignMain", "start"), "alignCross": (lay or {}).get("alignCross", "start"),
                   "wrap": bool((lay or {}).get("wrap", False))}
            touched = True
        if lay and lay.get("mode") in ("h", "v"):
            g = _num(take.get("gap"), None, 0, 400)
            if g is not None:
                lay["gap"], touched = _snap(g), True
            pad = _pad(take.get("pad"))
            if pad is not None:
                lay["pad"], touched = pad, True
            if take.get("align") in ("start", "center", "end", "stretch"):
                lay["alignCross"], touched = take["align"], True
            if take.get("justify") in ("start", "center", "end", "between"):
                lay["alignMain"], touched = take["justify"], True
        if touched:
            p["layout"] = lay
    for axis, key in (("w", "sizeH"), ("h", "sizeV")):
        v = _size(take.get(axis)) if axis in take else None
        if isinstance(v, (int, float)):
            p[axis] = v
            if node.get(key) in ("hug", "fill"):
                p[key] = "fixed"
        elif v in ("hug", "fill") and (v == "fill" or isinstance(node.get("layout"), dict)):
            p[key] = v
    return p


async def edit(prompt: str, nodes: dict[str, dict], selection: list[str], new_id: Callable[[], str],
               context: dict | None = None) -> dict:
    """"Make it more premium" on the selected layers -> {ops, touched, added, refused, notes}. The model sees handles,
    never ids; every property is validated; nothing is deleted or moved."""
    context = dict(context or {})
    prompt = _text(prompt, PROMPT_MAX).strip()
    if not prompt:
        raise AiError("Say in a line what Hoola should change.", 400)
    kid_map: dict[str, list[str]] = {}
    for nid, n in nodes.items():
        if isinstance(n.get("parent"), str):
            kid_map.setdefault(n["parent"], []).append(nid)
    for lst in kid_map.values():
        lst.sort(key=lambda c: (nodes[c].get("idx", ""), c))
    kids = lambda nid: kid_map.get(nid, [])     # noqa: E731
    chosen = [s for s in dict.fromkeys(selection) if s in nodes and nodes[s].get("type") not in ("DOCUMENT", "PAGE")]
    chosen = [s for s in chosen if not any(_above(nodes, s, other) for other in chosen if other != s)]
    if not chosen:
        raise AiError("Select the layers Hoola should change first.", 400)
    if not model_ready():
        raise AiError("Changing a design in words needs an AI model, and none is configured on this server. "
                      "(New designs still work: they come from Hoola's built-in layouts.)", 503)
    listing, handles = describe(nodes, kids, chosen)
    existing = " ".join(str(nodes[i].get("chars", "")) for i in handles.values() if nodes[i].get("type") == "TEXT")
    brand = context.get("brand") or {}
    facts = Facts(prompt, existing, json.dumps(brand, ensure_ascii=False) if brand else "")
    user = "REQUEST: " + prompt + "\n\nSELECTED LAYERS:\n" + listing
    if brand_block(brand):
        user += "\n\n" + brand_block(brand)

    def check(raw: Any) -> dict:
        if not isinstance(raw, dict) or not (isinstance(raw.get("changes"), list) or isinstance(raw.get("add"), list)):
            raise SpecError('The answer must be {"notes": "...", "changes": [{"handle": "n1", "set": {...}}], "add": [...]}.')
        return raw

    raw = await _asked(edit_system_prompt(), user, 7000, context.get("tenant") or "", check)
    work = {nid: dict(n) for nid, n in nodes.items()}
    refused: list[str] = []
    touched: set[str] = set()
    for ch in (raw.get("changes") or [])[:EDIT_MAX_NODES * 2]:
        if not isinstance(ch, dict):
            continue
        nid = handles.get(str(ch.get("handle")))
        if nid is None:
            refused.append(f"{str(ch.get('handle'))[:12]}: no such layer in the selection")
            continue
        if ch.get("delete") or ch.get("remove") or ch.get("del"):
            refused.append(f"{ch.get('handle')}: an edit never deletes a layer")
        props = changes_to_props(work[nid], ch.get("set"), facts, refused, str(ch.get("handle")))
        props = {k: v for k, v in props.items() if work[nid].get(k) != v}
        if props:
            work[nid].update(props)
            touched.add(nid)
    maker = _Maker(new_id, context.get("assets"))
    maker.nodes, maker.kids = work, kid_map
    before = set(work)
    budget = _Budget(120)
    for item in (raw.get("add") or [])[:24]:
        if not isinstance(item, dict):
            continue
        pid = handles.get(str(item.get("parent")))
        parent = work.get(pid) if pid else None
        if parent is None or parent.get("type") not in ("FRAME", "COMPONENT", "SECTION"):
            refused.append(f"add under {str(item.get('parent'))[:12]}: not a frame in the selection")
            continue
        node = clean_node(item.get("node"), 2, budget, facts, context.get("assets") or {})
        if node is None:
            continue
        sibs = kid_map.setdefault(pid, [])
        after = handles.get(str(item.get("after")))
        pos = sibs.index(after) + 1 if after in sibs else len(sibs)
        lo = work[sibs[pos - 1]].get("idx") if pos > 0 else None
        hi = work[sibs[pos]].get("idx") if pos < len(sibs) else None
        nid = maker.make(node, pid, fracidx.between(lo, hi), _spec_mode(parent))
        sibs.remove(nid)
        sibs.insert(pos, nid)
        touched.add(pid)
    added = [nid for nid in work if nid not in before]
    remeasure = {t for t in touched if work[t].get("type") == "TEXT"} | set(added)
    for root in chosen:
        lay = ailayout.Layout(work, kids)
        lay.remeasure = remeasure
        lay.run(root)
        fix_contrast(work, kids, root, only=remeasure | _text_under(work, kids, touched))
    ops: list[dict] = []
    for nid in work:
        if nid in before:
            old = nodes[nid]
            diff = {k: v for k, v in work[nid].items() if old.get(k) != v}
            if diff:
                ops.append({"id": nid, "p": diff})
                touched.add(nid)
    ops += [{"id": nid, "p": work[nid]} for nid in added]
    STATS["edits"] += 1
    return {"ops": ops, "touched": sorted(touched | set(added)), "added": added, "refused": refused[:20],
            "notes": _text(raw.get("notes"), 240).replace("\n", " ").strip(), "blanked": facts.blanked}


def _above(nodes: dict[str, dict], nid: str, ancestor: str) -> bool:
    cur, steps = nodes.get(nid, {}).get("parent"), 0
    while isinstance(cur, str) and steps < 64:
        if cur == ancestor:
            return True
        cur, steps = nodes.get(cur, {}).get("parent"), steps + 1
    return False


def _text_under(nodes: dict[str, dict], kids: Callable[[str], list[str]], ids: set[str]) -> set[str]:
    """The texts inside changed frames (a new background can make an old text unreadable)."""
    out: set[str] = set()
    stack = list(ids)
    while stack:
        nid = stack.pop()
        if nodes.get(nid, {}).get("type") == "TEXT":
            out.add(nid)
        stack.extend(kids(nid))
    return out


# =============================================================================================== the whole job
_CALLS: dict[str, list[float]] = {}


def _recent(tenant: str) -> list[float]:
    now = time.time()
    calls = _CALLS[tenant] = [t for t in _CALLS.get(tenant, []) if now - t < 3600]
    return calls


def rate_left(tenant: str) -> int:
    """Designs this tenant may still ask for in the current hour (counted per server process)."""
    return max(0, max(1, int(getattr(get_settings(), "design_ai_per_hour", 20))) - len(_recent(tenant)))


def rate_take(tenant: str) -> bool:
    """Use one of this hour's designs; False = the hour is full."""
    if rate_left(tenant) <= 0:
        return False
    _recent(tenant).append(time.time())
    return True


def brand_of(tenant: str) -> dict:
    """Her brand kit as facts for the model: name, tagline, colours, contact. {} when she has not set one up."""
    try:
        from ..brand import service as brand
        kit = brand.kit(tenant)
    except Exception:   # noqa: BLE001 - no brand kit is never a reason to fail a design
        return {}
    if not kit.get("ready") and not kit.get("colors_set") and not kit.get("logo"):
        return {}
    hers = bool(kit.get("colors_set") or kit.get("palette"))          # never the kit's built-in default blue
    cols = {k: c for k, v in (kit.get("colors") or {}).items() if hers and k in ("primary", "secondary", "accent", "dark", "light")
            for c in (color(v),) if c}
    contact = {k: _text(v, 120) for k, v in (kit.get("contact") or {}).items() if isinstance(v, str) and v.strip()}
    out = {"name": _text(kit.get("name"), 120), "tagline": _text(kit.get("tagline"), 160), "colors": cols, "contact": contact}
    return {k: v for k, v in out.items() if v}


def brand_logo(tenant: str) -> dict:
    """Her logo as a design asset {"logo": {hash, w, h}}; {} when there is none."""
    try:
        from ..brand import service as brand
        from . import assets
        path, _ = brand.logo_file(tenant)
        info = assets.save_asset(tenant, path.read_bytes())
        return {"logo": {"hash": info["hash"], "w": info["w"], "h": info["h"]}}
    except Exception:   # noqa: BLE001
        return {}


def _settle_mark() -> str:
    return f"{int(time.time() * 1000):x}"


async def design(tenant: str, file_id: str, prompt: str, *, page: str = "", x: float | None = None, y: float | None = None,
                 mode: str = "new", selection: list[str] | None = None, preset: str = "", brand: bool = True,
                 variant: int = 0) -> dict:
    """The whole job: read the file, ask for the design (or the edit), apply the ops THROUGH the room. Raises AiError
    (its `status` is the HTTP answer: 400 bad ask, 404 no such file, 429 too many, 502 the model failed)."""
    from .room import HUB, bg
    st = get_settings()
    if not getattr(st, "design_ai", True):
        raise AiError("Ask Hoola is switched off on this server.", 403)
    prompt = str(prompt or "").strip()
    if not prompt:
        raise AiError("Say in a line what Hoola should design.", 400)
    if len(prompt) > PROMPT_MAX:
        raise AiError(f"That is a long brief: keep it under {PROMPT_MAX} characters.", 400)
    got = await HUB.read(file_id, tenant)
    if got is None:
        raise AiError("File not found", 404)
    if not rate_take(tenant):
        raise AiError("That is a lot of designs in one hour. Please try again a little later.", 429)
    nodes = (await bg(loads, got[1])).get("nodes") or {}
    ctx: dict[str, Any] = {"tenant": tenant, "preset": preset, "variant": variant}
    if brand:
        ctx["brand"] = await bg(brand_of, tenant)
        if ctx["brand"]:
            ctx["assets"] = await bg(brand_logo, tenant)
    cid = await HUB.new_cid(file_id)
    new_id = id_maker(cid)
    if mode == "edit":
        out = await edit(prompt, nodes, list(selection or []), new_id, ctx)
        if not out["ops"]:
            return {"ok": True, "mode": "edit", "engine": "model", "roots": [], "touched": [], "added": [], "seq": got[0],
                    "notes": out["notes"] or "Nothing needed to change.", "refused": out["refused"], "left": rate_left(tenant)}
        res = await HUB.apply_ops(file_id, tenant, out["ops"])
        return {"ok": True, "mode": "edit", "engine": "model", "roots": [], "touched": out["touched"], "added": out["added"],
                "seq": res["seq"], "rejected": len(res["rejected"]), "notes": out["notes"], "refused": out["refused"],
                "blanked": out["blanked"], "left": rate_left(tenant)}
    pages = [nid for nid, n in nodes.items() if n.get("type") == "PAGE" and n.get("parent") == ROOT]
    if page not in pages:
        if not pages:
            raise AiError("This file has no page to draw on.", 409)
        page = sorted(pages, key=lambda p: (nodes[p].get("idx", ""), p))[0]
    spec = await generate(prompt, ctx)
    first = frame_size(spec["frames"][0])
    want = (float(x), float(y)) if isinstance(x, (int, float)) and isinstance(y, (int, float)) \
        and math.isfinite(x) and math.isfinite(y) and abs(x) < 1e7 and abs(y) < 1e7 else None
    px, py, last = place(nodes, page, (first[0], first[1]), want)
    page_bg = color(nodes[page].get("bg")) or PAGE_BG
    built = build(spec, new_id, page, (px, py), last, ctx.get("assets"), _settle_mark())
    res = await HUB.apply_ops(file_id, tenant, built["ops"])
    rejected = {built["ops"][i]["id"] for i in res["rejected"] if 0 <= i < len(built["ops"])}
    roots = [r for r in built["roots"] if r not in rejected]
    if not roots:
        raise AiError("The design could not be added to this file. Nothing was changed.", 500)
    return {"ok": True, "mode": "new", "engine": spec.get("engine", "model"), "roots": roots, "page": page,
            "frames": [{"id": r, "name": built["nodes"][r].get("name", ""), "w": built["nodes"][r].get("w"),
                        "h": built["nodes"][r].get("h")} for r in roots],
            "nodes": len(built["ops"]) - len(rejected), "seq": res["seq"], "rejected": len(rejected), "notes": spec.get("notes", ""),
            "contrast_fixed": built["fixed"], "blanked": spec.get("blanked", 0), "dropped": spec.get("dropped", 0),
            "page_bg": page_bg, "left": rate_left(tenant)}


async def from_request(tenant: str, file_id: str, body: Any) -> dict:
    """The POST /api/design/files/{id}/ai body, read strictly (a wrong type is ignored, never trusted)."""
    if not isinstance(body, dict):
        raise AiError("Send {\"prompt\": \"...\"}.", 400)
    prompt = body.get("prompt") if isinstance(body.get("prompt"), str) else ""
    mode = "edit" if body.get("mode") == "edit" else "new"
    selection = [s for s in body.get("selection") or [] if isinstance(s, str) and 0 < len(s) <= 64][:200] \
        if isinstance(body.get("selection"), list) else []
    num = lambda v: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None      # noqa: E731
    variant = body.get("variant") if isinstance(body.get("variant"), int) and not isinstance(body.get("variant"), bool) else 0
    return await design(tenant, file_id, prompt, page=body.get("page") if isinstance(body.get("page"), str) else "",
                        x=num(body.get("x")), y=num(body.get("y")), mode=mode, selection=selection,
                        preset=body.get("preset") if isinstance(body.get("preset"), str) else "",
                        brand=body.get("brand") is not False, variant=max(0, min(9, variant)))
