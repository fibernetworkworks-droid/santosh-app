"""v0.189.0 Document Studio tokens: the cascade palette engine + typography scale.

Ported from the Claude Code pdf/xlsx/docx skills' design systems. The iron rule they share:
NO hardcoded hex anywhere in the generators - every colour comes from here, derived from the
document title (deterministic: same title = same colours) and capped by area:

  tier  used for                    max saturation
  XL    page / section background   0.08
  L     cards, table zebra stripes  0.15
  M     table header fill, cover    0.30
  S     borders, icons              0.50
  XS    accents, stats              0.75

Text is never pure black (#111827-ish ink), muted text for meta/captions.
Charts get one hue family (accent, accent2, header_fill, icon) - max 5, no rainbow.
"""
from __future__ import annotations

import colorsys
import hashlib
import re

# ---------------------------------------------------------------- HSL helpers

def _hsl(h: float, s: float, l: float) -> str:
    """h in degrees, s/l in 0..1 -> '#rrggbb'."""
    r, g, b = colorsys.hls_to_rgb((h % 360.0) / 360.0, min(max(l, 0.0), 1.0), min(max(s, 0.0), 1.0))
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def _hex_rgb(hexs: str) -> tuple[int, int, int]:
    h = hexs.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_tuple(hexs: str) -> tuple[float, float, float]:
    r, g, b = _hex_rgb(hexs)
    return (r / 255.0, g / 255.0, b / 255.0)


# ---------------------------------------------------------------- styles

STYLES: dict[str, dict] = {
    # name: (hue override or None=derive from title, mode label)
    "auto":        (None, "derived from the title itself"),
    "professional": (215, "deep steel blue - reports, analyses, business letters"),
    "boardroom":   (222, "navy charcoal - board notes, quotations, contracts"),
    "warm":        (26,  "terracotta - shop / family / festival documents"),
    "elegant":     (282, "muted plum - invitations, profiles, Portfolios"),
    "forest":      (150, "calm green - farm, health, education"),
}
DEFAULT_STYLE = "auto"


def resolve_style(style: str | None) -> str:
    s = (style or DEFAULT_STYLE).strip().lower()
    return s if s in STYLES else DEFAULT_STYLE


def _title_hue(title: str) -> float:
    """Deterministic hue from the title: same title -> same palette, always."""
    digest = hashlib.sha256((title or "hoola").encode("utf-8")).digest()
    return digest[0] / 255.0 * 360.0


class Palette:
    """Cascade palette: every role the generators need, tier-capped."""

    def __init__(self, hue: float, style_name: str = "auto"):
        self.hue = hue
        self.style_name = style_name
        # XL tier - backgrounds (largest area, lowest saturation)
        self.page_bg = _hsl(hue, 0.06, 0.97)
        self.section_bg = _hsl(hue, 0.07, 0.955)
        # L tier - surfaces
        self.card_bg = _hsl(hue, 0.13, 0.93)
        self.table_stripe = _hsl(hue, 0.12, 0.94)
        # M tier - structural fills
        self.header_fill = _hsl(hue, 0.30, 0.34)
        self.cover_block = _hsl(hue, 0.28, 0.40)
        # S tier - edges & icons
        self.border = _hsl(hue, 0.22, 0.78)
        self.icon = _hsl(hue, 0.45, 0.42)
        # XS tier - accents (tiny areas only)
        self.accent = _hsl(hue, 0.72, 0.42)
        self.accent2 = _hsl((hue + 26.0) % 360.0, 0.65, 0.44)   # analogous harmony
        # Typography ink - never pure #000000
        self.text_primary = _hsl(hue, 0.14, 0.15)
        self.text_muted = _hsl(hue, 0.08, 0.52)
        # Chart family (max 5, one hue family)
        self.chart_colors = [self.accent, self.accent2, self.header_fill, self.icon, self.text_muted]

    # -- convenience views -------------------------------------------------
    def pdf_colors(self) -> dict[str, str]:
        return {k: getattr(self, k) for k in (
            "page_bg", "section_bg", "card_bg", "table_stripe", "header_fill", "cover_block",
            "border", "icon", "accent", "accent2", "text_primary", "text_muted")}

    def summary(self) -> dict:
        return {"style": self.style_name, "hue": round(self.hue), "accent": self.accent,
                "header_fill": self.header_fill, "zebra": self.table_stripe,
                "chart_colors": self.chart_colors[:3]}


def palette_for(title: str, style: str | None = None) -> Palette:
    """The ONLY way generators get colours. Deterministic per (title, style)."""
    name = resolve_style(style)
    hue = _title_hue(title or "") if STYLES[name][0] is None else float(STYLES[name][0])
    return Palette(hue, name)


# ---------------------------------------------------------------- typography scale

# pt sizes (pdf/docx share the scale; xlsx uses its own 11pt grid)
SCALE = {
    "cover_title": 30,     # chunked <br/> every 2-4 words, max 2 lines on the cover
    "cover_sub": 15,
    "cover_meta": 11,
    "h1": 19,
    "h2": 14,
    "h3": 11.5,
    "body": 10.5,
    "caption": 8.5,
    "kicker": 10,
    "stat_big": 21,
    "stat_label": 8.5,
    "footer": 7.5,
}
LEADING = 1.5          # minimum 1.4x the font size, CJK/Devanagari like 1.5x
MAX_KEEP_FRACTION = 0.4  # safe_keep_together cap: 40% of the page height
H1_ORPHAN_FRACTION = 0.22  # CondPageBreak threshold for H1


def leading(size: float) -> float:
    return round(size * LEADING, 1)


# ---------------------------------------------------------------- xlsx palettes

# Same three-color discipline for Excel: one PRIMARY family, semantic accents, warm neutrals.
XLSX_PALETTES: dict[str, dict[str, object]] = {
    "professional": {"PRIMARY": "1B2A4A", "PRIMARY_LIGHT": "D6E4F0"},
    "boardroom":    {"PRIMARY": "232C3D", "PRIMARY_LIGHT": "D8DCE4"},
    "warm":         {"PRIMARY": "7A3B20", "PRIMARY_LIGHT": "F2DDD2"},
    "elegant":      {"PRIMARY": "4A2E4F", "PRIMARY_LIGHT": "E7DAEA"},
    "forest":       {"PRIMARY": "1E4633", "PRIMARY_LIGHT": "D7E8DE"},
}
XLSX_BASE: dict[str, object] = {
    "ACCENT_POSITIVE": "1B7D46", "ACCENT_NEGATIVE": "C0392B", "ACCENT_WARNING": "D4820A",
    "NEUTRAL_900": "37352F", "NEUTRAL_600": "8C8A84", "NEUTRAL_200": "E9E9E8",
    "NEUTRAL_100": "F7F7F5", "NEUTRAL_50": "FAFAF9", "NEUTRAL_0": "FFFFFF",
    "HEADER_TEXT": "FFFFFF",
}


def xlsx_palette(style: str | None) -> dict[str, object]:
    """Full colour dict for the Excel engine (PRIMARY family + accents + neutrals + chart colors)."""
    name = resolve_style(style)
    fam = XLSX_PALETTES.get(name, XLSX_PALETTES["professional"])
    out: dict[str, object] = dict(XLSX_BASE)
    out.update(fam)
    out["SECONDARY"] = fam["PRIMARY_LIGHT"]
    r, g, b = _hex_rgb(str(fam["PRIMARY"]))
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    out["CHART_COLORS"] = [str(fam["PRIMARY"]), _hsl(h * 360, 0.62, 0.46), "D4820A", "1B7D46", "8C8A84"]
    out["STYLE"] = name
    return out


# ---------------------------------------------------------------- shared text helpers

_DEV = re.compile(r"[\u0900-\u097F\uA8E0-\uA8FF\u1CD0-\u1CFF]")


def has_devanagari(*texts: object) -> bool:
    return bool(_DEV.search(" ".join(str(t or "") for t in texts)))


def display_width(text: object) -> float:
    """Spreadsheet-column width estimate: wide scripts (CJK/Devanagari) count ~1.8."""
    s = str(text if text is not None else "")
    w = 0.0
    for ch in s:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F or 0xA8E0 <= o <= 0xA8FF or o >= 0x2E80:
            w += 1.8
        else:
            w += 1.0
    return w


def sanitize_text(text: str) -> str:
    """Strip control / zero-width / PUA chars from externally-sourced text (skill rule 3c)."""
    out = []
    for ch in (text or ""):
        o = ord(ch)
        if o in (0x0A, 0x09):
            out.append(ch)
            continue
        if o < 0x20 or o == 0x7F:
            continue
        if 0x200B <= o <= 0x200F or 0x2028 <= o <= 0x202F or o in (0x2060, 0xFEFF):
            continue
        if 0xFE00 <= o <= 0xFE0F or 0xE000 <= o <= 0xF8FF:
            continue
        if o == 0xFFFD:
            continue
        out.append(ch)
    return "".join(out)


def title_chunk(title: str, words_per_line: int = 3, max_lines: int = 3) -> list[str]:
    """Cover titles break every 2-4 words (single-line title = FAIL, skill rule)."""
    words = [w for w in re.split(r"\s+", (title or "").strip()) if w]
    if not words:
        return ["Hoola"]
    lines, cur = [], []
    per = max(2, min(4, words_per_line))
    for w in words:
        cur.append(w)
        if len(cur) >= per and len(lines) < max_lines - 1:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        if len(lines) >= max_lines and len(cur) <= 2 and lines:
            lines[-1] = (lines[-1] + " " + " ".join(cur)).strip()
        else:
            lines.append(" ".join(cur))
    return lines[:max_lines] or [title[:60]]
