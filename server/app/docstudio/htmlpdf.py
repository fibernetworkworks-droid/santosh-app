"""v0.305.0 HOOLA PRINT - PDFs made the way Claude makes them: a designed HTML page printed by Chromium.

The owner sent three PDFs Claude made (a business plan, a 46-page delivery plan, a research thesis) and asked for the
same. Their metadata settled the method: all three are HTML + CSS printed by Chrome (Skia/PDF, Liberation / Arial
fonts; the delivery plan's cover joined on with pypdf), never ReportLab drawing. What makes them look "designed per
topic" is that the model picks the look for each document. So:

  1. ART DIRECTION  Opus reads the title + outline and picks the look from FIXED parts (cover, type pair, density,
                    heading / table style, two colours, kicker, tags). It never writes CSS, so a page cannot break.
                    No key / slow / off -> the v0.192 topic router (designs.detect_topic) picks the same fields.
  2. HTML           the make_document mini-language (+ fenced code, callouts, stat rows, links) -> one HTML page from
                    a small set of parts taken from Claude's PDFs: covers, numbered sections, stat row, callouts,
                    dark-header tables with right-aligned money and a bold total, code blocks, contents page.
  3. PRINT          Chromium (Playwright, already on the VPS for Hindi PDFs). Contents page numbers are REAL (pass 1
                    finds every heading's page through an invisible marker, pass 2 prints them). The cover is printed
                    alone, full-bleed, and swapped in for page 1 with pypdf - no header / footer on the cover.
  4. QA + REVIEW    every page is rendered and measured (blank / mostly-empty pages -> one compact re-print); then
                    Opus looks at the cover + inner pages and may ask for ONE change from the same fixed list.

Fonts ship in app/fonts/print (Inter, Source Serif 4, JetBrains Mono, Noto for 10 Indian scripts; Poppins from
app/fonts) so every server prints the same page. Any failure -> the caller falls back to pdfgen (ReportLab).
"""
from __future__ import annotations

import colorsys
import concurrent.futures as _cf
import datetime as _dt
import html as _html
import io
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from . import designs

log = logging.getLogger("santosh.docstudio.print")

ENGINE_VERSION = "v0.305.0"
FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
PRINT_FONTS = FONT_DIR / "print"
STATS = {"printed": 0, "fallback": 0, "art_opus": 0, "art_router": 0, "review": 0, "review_changed": 0,
         "compact_retry": 0}

COVERS = ("gradient", "swiss", "band", "rail", "editorial", "split", "minimal", "none")
TYPES = {   # head font, body font
    "sans": ("Inter", "Inter"),
    "serif": ("Source Serif", "Source Serif"),
    "editorial": ("Source Serif", "Inter"),
    "humanist": ("Inter", "Source Serif"),
    "geometric": ("Poppins", "Inter"),
}
DENSITY = {   # body pt, line height, paragraph gap mm
    "airy": (11.0, 1.65, 3.4),
    "normal": (10.5, 1.58, 2.8),
    "compact": (9.6, 1.48, 2.2),
}
HEADINGS = ("numbered", "plain", "banner")
TABLES = ("dark", "tint", "lines")
CALLOUTS = {"note": "Note", "tip": "Tip", "info": "Note", "important": "Important", "warning": "Warning",
            "caution": "Caution", "success": "Done", "check": "Check", "human": "Your step", "gate": "Gate"}

# family -> the look Claude's PDFs use for that kind of document (router fallback + Opus's starting point)
FAMILY_LOOK: dict[str, dict[str, str]] = {
    "finance": {"cover": "band", "type": "humanist", "headings": "numbered", "table": "dark", "density": "normal"},
    "technology": {"cover": "gradient", "type": "sans", "headings": "banner", "table": "dark", "density": "normal"},
    "education": {"cover": "split", "type": "geometric", "headings": "numbered", "table": "tint", "density": "airy"},
    "health": {"cover": "minimal", "type": "sans", "headings": "plain", "table": "tint", "density": "normal"},
    "legal": {"cover": "editorial", "type": "serif", "headings": "numbered", "table": "lines", "density": "normal"},
    "marketing": {"cover": "gradient", "type": "geometric", "headings": "plain", "table": "tint", "density": "airy"},
    "people": {"cover": "rail", "type": "sans", "headings": "plain", "table": "tint", "density": "normal"},
    "agriculture": {"cover": "split", "type": "humanist", "headings": "numbered", "table": "tint", "density": "normal"},
    "government": {"cover": "band", "type": "serif", "headings": "numbered", "table": "lines", "density": "normal"},
    "travel": {"cover": "gradient", "type": "geometric", "headings": "plain", "table": "tint", "density": "airy"},
    "festive": {"cover": "editorial", "type": "editorial", "headings": "plain", "table": "tint", "density": "airy"},
    "general": {"cover": "swiss", "type": "sans", "headings": "numbered", "table": "lines", "density": "normal"},
}


class PrintError(Exception):
    pass


# ---------------------------------------------------------------- colour
def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def _hsl(h: float, s: float, l: float) -> str:   # noqa: E741
    return _hex(colorsys.hls_to_rgb((h % 360) / 360.0, l, s))


def _rgb(hx: str) -> tuple[float, float, float]:
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def _lum(hx: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(hx)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _valid_hex(v: Any) -> str | None:
    s = str(v or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", s):
        return "#" + s.lstrip("#").lower()
    return None


def _darken_until(hx: str, against: str, ratio: float) -> str:
    """Lower the lightness until text in `hx` reads on `against` (WCAG ratio)."""
    r, g, b = _rgb(hx)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    for _ in range(40):
        cur = _hex(colorsys.hls_to_rgb(h, l, s))
        if contrast(cur, against) >= ratio:
            return cur
        l = max(0.0, l - 0.025)   # noqa: E741
    return _hex(colorsys.hls_to_rgb(h, l, s))


def palette(primary: str, accent: str) -> dict[str, str]:
    """Every colour on the page from two: primary (deep, white text on it) and accent (small, text-safe)."""
    primary = _darken_until(primary, "#ffffff", 7.0)
    accent = _darken_until(accent, "#ffffff", 4.5)
    r, g, b = _rgb(primary)
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    ar, ag, ab = _rgb(accent)
    ah, _al, as_ = colorsys.rgb_to_hls(ar, ag, ab)
    hd = h * 360
    return {
        "primary": primary, "accent": accent,
        "deep2": _hsl(hd + 34, min(0.62, s + 0.05), 0.27),
        "ink": _hsl(hd, min(0.30, s), 0.12), "muted": _hsl(hd, 0.10, 0.40),
        "line": _hsl(hd, 0.14, 0.86), "zebra": _hsl(hd, 0.22, 0.972),
        "soft": _hsl(ah * 360, min(0.55, as_), 0.955), "soft2": _hsl(hd, 0.25, 0.945),
        "paper": "#ffffff",
    }


def router_colours(title: str, family: str, hue: float) -> tuple[str, str]:
    if family == "general":
        return "#16181d", _hsl(hue, 0.62, 0.40)        # the Varasa look: black on white, one quiet accent
    return _hsl(hue, 0.55, 0.25), _hsl(hue + 18, 0.70, 0.38)


# ---------------------------------------------------------------- content -> blocks
_CALLOUT = re.compile(r"^\[!(\w+)\]\s*(.*)$")
_STAT = re.compile(r"^\[stat:\s*(.+?)\s*\|\s*(.+?)\]\s*$", re.I)
_OL = re.compile(r"^(\d+)[.)]\s+")
_UL = re.compile(r"^[-*•]\s+")
_TOTAL = re.compile(r"^\s*(\*\*)?\s*(grand\s+total|total|net\s+total|sub\s*-?total|kul|kul\s+jod|net|कुल|योग)\b", re.I)
_NUMERIC = re.compile(r"^[\s(+\-−~≈<>]*(?:₹|rs\.?|inr|\$|usd|€)?\s*[\d.,]+\s*"
                      r"(?:%|x|cr|crore|l|lakh|lakhs|k|m|bn|mn|days?|hrs?|h|min|pts?|cr\.|lac)?\)?\s*$", re.I)


def _clean(text: str) -> str:
    """Control / bidi / private-use characters out; ZWJ / ZWNJ kept (Indian scripts need them)."""
    out = []
    for ch in str(text or ""):
        o = ord(ch)
        if o in (0x0A, 0x09) or o in (0x200C, 0x200D):
            out.append(ch)
        elif o < 0x20 or o == 0x7F or 0x200B <= o <= 0x200F or 0x2028 <= o <= 0x202F or o in (0x2060, 0xFEFF) \
                or 0xE000 <= o <= 0xF8FF:
            continue
        else:
            out.append(ch)
    return "".join(out)


def parse(text: str) -> list[dict[str, Any]]:
    """The make_document language Hoola already writes ('# ' '## ' '### ', '- ' '1. ', '| a | b |', '> ',
    '[stat: v | label]', '---') plus: ``` fenced code, '> [!NOTE|TIP|WARNING|SUCCESS|HUMAN|GATE] text' callouts,
    '[[pagebreak]]'. Consecutive stats become ONE row; consecutive list items ONE list."""
    out: list[dict[str, Any]] = []
    lines = _clean(text).splitlines()
    i = 0

    def last(k: str) -> dict | None:
        return out[-1] if out and out[-1]["k"] == k else None

    while i < len(lines):
        raw = lines[i].rstrip()
        s = raw.strip()
        i += 1
        if s.startswith("```"):
            lang = s[3:].strip()
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i].rstrip("\n"))
                i += 1
            i += 1
            out.append({"k": "code", "t": "\n".join(buf), "lang": lang})
            continue
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            t = last("table")
            if t is not None and t.get("open"):
                t["rows"].append(cells)
            else:
                out.append({"k": "table", "rows": [cells], "open": True})
            continue
        if out and out[-1]["k"] == "table":
            out[-1]["open"] = False
        if not s:
            if out and out[-1]["k"] in ("ul", "ol", "quote", "callout"):
                out[-1]["closed"] = True
            continue
        if s.lower() in ("[[pagebreak]]", "\\pagebreak", "<pagebreak>"):
            out.append({"k": "pagebreak"})
        elif s in ("---", "***", "___"):
            out.append({"k": "divider"})
        elif s.startswith("#### "):
            out.append({"k": "h3", "t": s[5:].strip()})
        elif s.startswith("### "):
            out.append({"k": "h3", "t": s[4:].strip()})
        elif s.startswith("## "):
            out.append({"k": "h2", "t": s[3:].strip()})
        elif s.startswith("# "):
            out.append({"k": "h1", "t": s[2:].strip()})
        elif s.startswith(">"):
            body = s[1:].strip()
            m = _CALLOUT.match(body)
            if m:
                kind = m.group(1).lower()
                out.append({"k": "callout", "kind": kind if kind in CALLOUTS else "note", "t": m.group(2).strip()})
            else:
                prev = out[-1] if out and out[-1]["k"] in ("quote", "callout") and not out[-1].get("closed") else None
                if prev is not None:
                    prev["t"] = (prev["t"] + "\n" + body).strip()
                else:
                    out.append({"k": "quote", "t": body})
        elif _STAT.match(s):
            m = _STAT.match(s)
            row = last("stats")
            if row is not None and len(row["items"]) < 4:
                row["items"].append((m.group(1), m.group(2)))
            else:
                out.append({"k": "stats", "items": [(m.group(1), m.group(2))]})
        elif _UL.match(s) or _OL.match(s):
            kind = "ul" if _UL.match(s) else "ol"
            item = _UL.sub("", s) if kind == "ul" else _OL.sub("", s)
            level = 1 if (len(raw) - len(raw.lstrip())) >= 2 else 0
            lst = last(kind)
            if lst is not None and not lst.get("closed"):
                lst["items"].append((level, item))
            else:
                start = int(_OL.match(s).group(1)) if kind == "ol" else 1
                out.append({"k": kind, "items": [(level, item)], "start": start})
        else:
            out.append({"k": "p", "t": s})      # one line = one paragraph (the make_document rule)
    return out


def _inline(text: str) -> str:
    """Escape, then **bold**, *italic*, `code`, [text](https://...) - nothing else turns into markup."""
    s = _html.escape(_clean(text), quote=False)
    codes: list[str] = []

    def keep(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"
    s = re.sub(r"`([^`]+)`", keep, s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", s)
    return s


def _numeric(cell: str) -> bool:
    c = re.sub(r"\*\*", "", cell or "").strip()
    return bool(c) and bool(_NUMERIC.match(c))


def numeric_columns(rows: list[list[str]]) -> list[bool]:
    """A column is numeric when 60%+ of its filled body cells are amounts / counts / percentages."""
    if len(rows) < 2:
        return [False] * (len(rows[0]) if rows else 0)
    width = max(len(r) for r in rows)
    flags = []
    for c in range(width):
        cells = [r[c] for r in rows[1:] if c < len(r) and r[c].strip()]
        flags.append(c > 0 and bool(cells) and sum(_numeric(x) for x in cells) / len(cells) >= 0.6)
    return flags


# ---------------------------------------------------------------- art direction
ART_SYSTEM = """You are the art director for Hoola's PDF documents (an Indian AI coworker). You pick the LOOK of one
document from fixed parts, the way a senior designer would for that exact topic and reader. Reference looks:
- business plan / investor memo: cover "swiss" (huge black title on white), type "sans", headings "numbered", table "lines", calm
- delivery / project / technical plan: cover "gradient" (deep two-colour gradient, white title, tags), headings "banner", table "dark"
- annual / financial report: cover "band", type "humanist", table "dark", stat rows
- legal / policy / agreement: cover "editorial" or "minimal", type "serif", table "lines", no tags
- school / training / health leaflet: cover "split" or "minimal", type "geometric" or "sans", table "tint", density "airy"
- marketing / festive / travel: cover "gradient" or "editorial", warm or vivid colours, density "airy"
Colours: primary is DEEP (white text must read on it), accent is the one vivid colour (used small). Pick colours that
suit the topic and the Indian business reader (no neon, no pure #000 primaries except the swiss look).
kicker = 2-5 words, the document type ("ANNUAL REPORT · FY 2025-26"); tags = 0-4 short facts for the cover; subtitle
= one line if the title alone does not say it. Same language as the title."""

ART_FIELDS = """Reply with JSON: {"cover": one of %s, "type": one of %s, "density": one of %s,
"headings": one of %s, "table": one of %s, "primary": "#rrggbb", "accent": "#rrggbb", "kicker": "...",
"subtitle": "...", "tags": ["..."], "why": "one short line"}""" % (
    list(COVERS[:-1]), list(TYPES), list(DENSITY), list(HEADINGS), list(TABLES))


DOC_TYPES = (   # (pattern in the title, kicker) - first match wins; Indian-script titles keep no English kicker
    (r"quotation|quote|estimate|कोटेशन", "Quotation"), (r"invoice|bill\b|बिल", "Invoice"),
    (r"proposal|प्रस्ताव", "Proposal"), (r"business plan", "Business plan"), (r"annual report", "Annual report"),
    (r"delivery plan|project plan|roadmap|rollout", "Delivery plan"), (r"agreement|contract|mou\b|अनुबंध", "Agreement"),
    (r"policy|नीति", "Policy"), (r"notice|नोटिस", "Notice"), (r"letter|पत्र", "Letter"),
    (r"research|thesis|study|analysis|whitepaper|white paper", "Research"), (r"report|रिपोर्ट", "Report"),
    (r"plan\b|योजना", "Plan"), (r"brochure|catalogue|catalog|price list", "Catalogue"), (r"menu", "Menu"),
    (r"resume|cv\b|biodata", "Profile"), (r"certificate|प्रमाण", "Certificate"), (r"guide|manual|handbook", "Guide"),
)


def doc_kicker(title: str, label: str, family: str) -> str:
    t = (title or "").lower()
    indic = any(0x0900 <= ord(c) <= 0x0DFF for c in t)
    for pat, name in DOC_TYPES:
        if re.search(pat, t):
            return "" if indic else name.upper()
    if indic or family == "general":
        return ""
    return label.upper()


def _route(title: str, text: str, style: str | None) -> dict[str, Any]:
    spec = designs.resolve_design(title, text or "", style)
    fam = spec["family"] if spec["family"] in FAMILY_LOOK else "general"
    look = dict(FAMILY_LOOK[fam])
    primary, accent = router_colours(title, fam, float(spec["hue"]))
    look.update({"family": fam, "label": spec["label"], "primary": primary, "accent": accent,
                 "kicker": doc_kicker(title, spec["label"], fam), "subtitle": "", "tags": [],
                 "detected": bool(spec.get("detected")), "source": "router", "why": ""})
    return look


def _sane(spec: dict[str, Any], pick: dict[str, Any]) -> dict[str, Any]:
    """Merge a model's pick into the spec - only the fixed parts, only valid values."""
    out = dict(spec)
    for key, allowed in (("cover", COVERS), ("type", TYPES), ("density", DENSITY), ("headings", HEADINGS),
                         ("table", TABLES)):
        v = str(pick.get(key) or "").strip().lower()
        if v in allowed:
            out[key] = v
    for key in ("primary", "accent"):
        hx = _valid_hex(pick.get(key))
        if hx:
            out[key] = hx
    for key, cap in (("kicker", 48), ("subtitle", 140), ("why", 160)):
        if isinstance(pick.get(key), str) and pick[key].strip():
            out[key] = _clean(pick[key]).strip()[:cap]
    if isinstance(pick.get("tags"), list):
        out["tags"] = [_clean(str(t)).strip()[:40] for t in pick["tags"] if str(t).strip()][:4]
    return out


def _ask_opus(system: str, prompt: str, kind: str, images: list[bytes] | None, timeout: float) -> dict[str, Any]:
    from ..site import ai as AI
    ex = _cf.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(AI.ask_json, system, prompt, 900, kind, images)
    try:
        return fut.result(timeout=timeout) or {}
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


def art_direct(title: str, text: str, style: str | None = None, subject: str = "",
               ask: Any = None) -> dict[str, Any]:
    """The look for this document. An explicit style forces the router's family; 'auto' asks Opus (when on and a
    key is there), and anything Opus says outside the fixed parts is ignored."""
    spec = _route(title, text, style)
    from ..config import get_settings
    st = get_settings()
    want = (style or "auto") == "auto" and (ask is not None or bool(getattr(st, "doc_art", True)))
    if want and (ask is not None or st.anthropic_api_key):
        heads = [b["t"] for b in parse(text) if b["k"] in ("h1", "h2")][:24]
        prompt = (f"TITLE: {title}\nSUBTITLE / PURPOSE: {subject or '-'}\nOUTLINE: {heads}\n"
                  f"TOPIC ROUTER GUESS: {spec['family']} -> {({k: spec[k] for k in ('cover', 'type', 'table')})}\n"
                  f"OPENING TEXT:\n{(text or '')[:1400]}\n\n{ART_FIELDS}")
        try:
            pick = (ask or _ask_opus)(ART_SYSTEM, prompt, "doc_art", None, 50.0)
        except Exception as e:     # slow / busy / no model: the router's look is a good look
            log.info("doc art direction skipped: %s", e)
            pick = {}
        if pick:
            spec = _sane(spec, pick)
            spec["source"] = "opus"
            STATS["art_opus"] += 1
            return spec
    STATS["art_router"] += 1
    return spec


# ---------------------------------------------------------------- HTML
def _font_css() -> str:
    def face(fam: str, file: Path, weight: str = "100 900", style: str = "normal") -> str:
        if not file.exists():
            return ""
        fmt = "woff2" if file.suffix == ".woff2" else "truetype"
        return (f"@font-face{{font-family:'{fam}';src:url('{file.as_uri()}') format('{fmt}');"
                f"font-weight:{weight};font-style:{style};font-display:block}}")
    p = PRINT_FONTS
    css = [face("Inter", p / "Inter.ttf"), face("Source Serif", p / "SourceSerif4.ttf"),
           face("Hoola Mono", p / "JetBrainsMono.ttf"), face("Poppins", FONT_DIR / "Poppins-Bold.ttf", "600 900")]
    for fam, f in (("Noto Sans Devanagari", "NotoSansDevanagari.ttf"), ("Noto Sans Bengali", "NotoSansBengali.ttf"),
                   ("Noto Sans Gurmukhi", "NotoSansGurmukhi.ttf"), ("Noto Sans Gujarati", "NotoSansGujarati.woff2"),
                   ("Noto Sans Oriya", "NotoSansOriya.woff2"), ("Noto Sans Tamil", "NotoSansTamil.woff2"),
                   ("Noto Sans Telugu", "NotoSansTelugu.ttf"), ("Noto Sans Kannada", "NotoSansKannada.ttf"),
                   ("Noto Sans Malayalam", "NotoSansMalayalam.ttf")):
        css.append(face(fam, p / f))
    if not (p / "NotoSansDevanagari.ttf").exists():
        css.append(face("Noto Sans Devanagari", FONT_DIR / "NotoSansDevanagari-Regular.ttf", "400"))
        css.append(face("Noto Sans Devanagari", FONT_DIR / "NotoSansDevanagari-Bold.ttf", "700"))
    return "".join(css)


INDIC = ("'Noto Sans Devanagari','Noto Sans Bengali','Noto Sans Gurmukhi','Noto Sans Gujarati','Noto Sans Oriya',"
         "'Noto Sans Tamil','Noto Sans Telugu','Noto Sans Kannada','Noto Sans Malayalam'")


def _stack(fam: str) -> str:
    tail = "serif" if fam == "Source Serif" else "sans-serif"
    return f"'{fam}','Inter',{INDIC},'DejaVu Sans',{tail}"


GUTTER = 10.0   # mm inside the 8 mm page margin = text 18 mm from the paper; the numbers hang in this strip
GRID = {   # v0.305.0 THE PAGE SYSTEM - every measure below comes from these (measured audit: 8 text edges -> 2)
    "inset": 5.0,       # mm: the ONE indent - text inside any box (note, key number, code, quote, filled table) and lists
    "hang": 3.0,        # mm: gap between a hanging heading number (in the margin) and the heading text
    "scale": (1.125, 1.35, 1.8),   # h3, h2, h1 as multiples of the body size (one ratio ladder, nothing in between)
}


def line_mm(spec: dict[str, Any]) -> float:
    """One body line in mm - the unit every vertical space is a multiple of."""
    size, lh, _gap = DENSITY.get(spec["density"], DENSITY["normal"])
    return round(size * lh * 25.4 / 72, 2)


def _css(spec: dict[str, Any], P: dict[str, str]) -> str:
    """The inside pages as ONE system (v0.305.0, from a measured audit of the printed layout):
    - two left edges only: the text edge (0) and the inset (GRID inset) - paragraphs, headings, plain tables and the
      contents titles start on the text edge; text inside every box and every list starts on the inset; heading and
      contents numbers hang in the margin so they never push the words right;
    - every box spans the full column, text inside it keeps the same inset on the right, so box edges and numbers
      line up down the page;
    - vertical space = multiples of one body line (L): paragraph .5L, around every box .8L (same above and below),
      h3 1L/.3L, h2 1.5L/.4L, h1 2L/.55L (space above a heading always 2.5x+ the space below it);
    - type sizes from one ratio ladder (GRID scale)."""
    head, body = TYPES.get(spec["type"], TYPES["sans"])
    size, lh, _gap = DENSITY.get(spec["density"], DENSITY["normal"])
    L = line_mm(spec)
    IN, HANG = GRID["inset"], GRID["hang"]
    h3, h2, h1 = (round(size * k, 1) for k in GRID["scale"])
    table = spec["table"]
    th = {"dark": f"background:{P['primary']};color:#fff;border-bottom:0",
          "tint": f"background:{P['soft2']};color:{P['ink']};border-bottom:1.2pt solid {P['primary']}",
          "lines": f"background:transparent;color:{P['ink']};border-bottom:1.4pt solid {P['ink']}"}[table]
    zebra = f"tbody tr:nth-child(even) td{{background:{P['zebra']}}}" if table != "lines" else ""
    edge = "0" if table == "lines" else f"{IN}mm"       # a filled table insets like every box; a plain one sits on the edge
    bar = 3.0 * 25.4 / 72                                # the 3pt coloured edge of notes / key numbers, in mm
    return f"""{_font_css()}
:root{{--p:{P['primary']};--a:{P['accent']};--ink:{P['ink']};--mut:{P['muted']};--line:{P['line']};--soft:{P['soft']};
--soft2:{P['soft2']};--deep2:{P['deep2']};--zebra:{P['zebra']};--hf:{_stack(head)};--bf:{_stack(body)};
--L:{L}mm;--in:{IN}mm;--hang:{HANG}mm}}
@page{{size:A4}}
*{{box-sizing:border-box}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{margin:0;padding:0 {GUTTER}mm;font-family:var(--bf);font-size:{size}pt;line-height:{lh};color:var(--ink);font-kerning:normal;
font-variant-numeric:lining-nums;text-rendering:optimizeLegibility;orphans:3;widows:3;hyphens:manual}}
p{{margin:0 0 calc(var(--L)*.5)}} b,strong{{font-weight:650}} a{{color:var(--a);text-decoration:none}}
h1,h2,h3{{font-family:var(--hf);color:var(--ink);break-after:avoid;page-break-after:avoid;line-height:1.22;position:relative}}
h1{{font-size:{h1}pt;font-weight:700;margin:calc(var(--L)*2) 0 calc(var(--L)*.55);letter-spacing:-.01em}}
h2{{font-size:{h2}pt;font-weight:650;margin:calc(var(--L)*1.5) 0 calc(var(--L)*.4)}}
h3{{font-size:{h3}pt;font-weight:650;margin:calc(var(--L)*1) 0 calc(var(--L)*.3)}}
h1 .no{{display:inline-block;width:{GUTTER - .5}mm;margin-left:-{GUTTER - .5}mm;padding-right:var(--hang);
text-align:right;font-size:.6em;color:var(--a);font-variant-numeric:tabular-nums;white-space:nowrap;letter-spacing:0}}
h1.banner{{background:var(--p);color:#fff;padding:calc(var(--L)*.45) var(--in);border-radius:1.2mm;font-size:{h2}pt}}
h1.banner .no{{width:auto;margin:0 .55em 0 0;padding:0;font-size:1em;color:#fff;opacity:.7}}
.body>h1:first-child,.body>.lh+h1{{margin-top:0}}
.body :is(h1,h2,h3)+*{{margin-top:0}}   /* a heading binds to whatever follows: only its own space below counts */
ul,ol{{margin:0 0 calc(var(--L)*.5);padding-left:var(--in)}}
li{{margin:0 0 calc(var(--L)*.2);padding-left:0}} li.l1{{margin-left:var(--in);list-style:circle}}
li::marker{{color:var(--a)}} ol>li::marker{{font-variant-numeric:tabular-nums}}
code{{font-family:'Hoola Mono','DejaVu Sans Mono',monospace;font-size:.86em;background:var(--soft2);border-radius:1mm;
padding:.1em .3em}}
.box,pre,blockquote,.callout,.stats,table{{margin:calc(var(--L)*.8) 0}}
pre{{font-family:'Hoola Mono','DejaVu Sans Mono',monospace;font-size:{max(7.6, size * .82):.1f}pt;line-height:1.5;
background:#141821;color:#e8eaf0;border-radius:1.2mm;padding:calc(var(--L)*.5) var(--in);white-space:pre-wrap;
overflow-wrap:anywhere;break-inside:avoid}}
pre code{{background:none;padding:0;color:inherit;font-size:1em}}
blockquote{{padding:calc(var(--L)*.15) var(--in) calc(var(--L)*.15) calc(var(--in) - {bar:.2f}mm);
border-left:{bar:.2f}mm solid var(--a);color:var(--mut);font-style:italic;break-inside:avoid}}
hr{{border:0;border-top:.8pt solid var(--line);margin:calc(var(--L)*1) 0}}
.callout{{border-left:{bar:.2f}mm solid var(--a);background:var(--soft);
padding:calc(var(--L)*.45) var(--in) calc(var(--L)*.45) calc(var(--in) - {bar:.2f}mm);border-radius:0 1.2mm 1.2mm 0;
break-inside:avoid}}
.callout .ct{{font-family:var(--hf);font-weight:700;font-size:.8em;letter-spacing:.08em;text-transform:uppercase;
color:var(--a);margin-bottom:calc(var(--L)*.15)}}
.callout p{{margin:0 0 calc(var(--L)*.3)}} .callout p:last-child{{margin:0}}
.callout.warning,.callout.caution,.callout.important{{border-color:#b45309;background:#fff7ea}}
.callout.warning .ct,.callout.caution .ct,.callout.important .ct{{color:#9a3f07}}
.callout.success,.callout.check,.callout.gate{{border-color:#15803d;background:#effaf2}}
.callout.success .ct,.callout.check .ct,.callout.gate .ct{{color:#166534}}
.callout.human{{border-color:#c2410c;background:#fff4ec}} .callout.human .ct{{color:#9a3412}}
.stats{{display:grid;grid-template-columns:repeat(var(--n,3),1fr);gap:4mm;break-inside:avoid}}
.stat{{background:var(--soft);border-left:{bar:.2f}mm solid var(--a);border-radius:0 1.2mm 1.2mm 0;
padding:calc(var(--L)*.45) var(--in) calc(var(--L)*.45) calc(var(--in) - {bar:.2f}mm)}}
.stat .v{{display:block;font-family:var(--hf);font-size:{h1}pt;font-weight:700;color:var(--a);line-height:1.1;
font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.stat .l{{display:block;font-size:.84em;color:var(--mut);margin-top:calc(var(--L)*.15);line-height:1.35}}
table{{width:100%;border-collapse:collapse;font-size:{size * .9:.1f}pt;line-height:1.42}}
table.keep{{break-inside:avoid}}
thead{{display:table-header-group}} tr{{break-inside:avoid}}
th{{{th};text-align:left;font-weight:650;padding:2.2mm 3mm;font-family:var(--hf);vertical-align:bottom}}
td{{padding:2mm 3mm;border-bottom:.6pt solid var(--line);vertical-align:top;overflow-wrap:anywhere}}
th:first-child,td:first-child{{padding-left:{edge}}} th:last-child,td:last-child{{padding-right:{edge}}}
{zebra}
td.k,th.k{{white-space:nowrap}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;width:1%}}
tr.tot td{{font-weight:700;border-top:1.4pt solid var(--ink);border-bottom:0;background:transparent}}
.toc{{break-after:page}}
.toc h1{{margin-top:0;margin-bottom:calc(var(--L)*1)}}
.toc .row{{display:flex;align-items:baseline;gap:2mm;color:var(--ink);break-inside:avoid;position:relative;
padding:calc(var(--L)*.18) 0}}
.toc .row .t{{flex:0 1 auto}} .toc .row .d{{flex:1;border-bottom:.8pt dotted var(--line);transform:translateY(-1mm)}}
.toc .row .pg{{flex:0 0 auto;font-variant-numeric:tabular-nums;color:var(--mut);min-width:6mm;text-align:right}}
.toc .r1{{font-weight:650;margin-top:calc(var(--L)*.3)}} .toc .r2{{padding-left:var(--in);font-size:.93em}}
.toc .row .no{{display:inline-block;width:{GUTTER - .5}mm;margin-left:-{GUTTER - .5}mm;padding-right:var(--hang);
text-align:right;color:var(--a);font-variant-numeric:tabular-nums}}
.pb{{break-after:page}}
.coverslot{{height:1mm;break-after:page}}
.mk{{font-size:1px;color:#fff;letter-spacing:0}}
.lh{{border-bottom:2pt solid var(--p);padding-bottom:calc(var(--L)*.6);margin-bottom:calc(var(--L)*1.2);display:flex;
justify-content:space-between;align-items:flex-end;gap:8mm}}
.lh .k{{font-size:8pt;letter-spacing:.16em;text-transform:uppercase;color:var(--a);font-weight:650}}
.lh h1{{margin:calc(var(--L)*.2) 0 0;font-size:{round(h1 * 1.15, 1)}pt}}
.lh .s{{color:var(--mut);margin-top:calc(var(--L)*.2)}}
.lh .m{{text-align:right;font-size:8.5pt;color:var(--mut);white-space:nowrap;line-height:1.5}}
"""


def _cover_css(spec: dict[str, Any], P: dict[str, str]) -> str:
    head, _body = TYPES.get(spec["type"], TYPES["sans"])
    EDGE = GUTTER + 8      # v0.305.0 the cover's text edge = the inside pages' text edge (18 mm from the paper)
    return f"""
@page{{size:A4;margin:0}}
body{{padding:0}}          /* the inside pages' gutter must never reach the full-bleed cover */
.cv{{width:210mm;height:296.6mm;position:relative;overflow:hidden;font-family:var(--bf);color:var(--ink)}}
.cv .k{{font-size:9pt;letter-spacing:.2em;text-transform:uppercase;font-weight:600}}
.cv h1{{font-family:{_stack(head)};font-weight:700;line-height:1.08;letter-spacing:-.015em;margin:0;max-width:160mm}}
.cv .s{{font-size:13pt;line-height:1.45;max-width:150mm}}
.cv .tags span{{display:inline-block;border:.8pt solid currentColor;border-radius:20pt;padding:1.2mm 3.6mm;
margin:0 2mm 2mm 0;font-size:8.6pt;opacity:.92}}
.cv .meta{{position:absolute;left:{EDGE}mm;right:{EDGE}mm;bottom:26mm;font-size:9.4pt;line-height:1.75}}
.cv .meta b{{font-weight:650}}
.cv-gradient{{background:linear-gradient(158deg,var(--p) 0%,var(--deep2) 100%);color:#fff}}
.cv-gradient .in{{position:absolute;left:{EDGE}mm;right:{EDGE}mm;top:40mm}}
.cv-gradient h1{{color:#fff;font-size:34pt;margin:8mm 0 6mm}} .cv-gradient .k{{opacity:.78}}
.cv-gradient .s{{opacity:.9;margin-bottom:9mm}} .cv-gradient .meta{{border-top:.7pt solid rgba(255,255,255,.38);padding-top:6mm}}
.cv-swiss{{background:#fff}} .cv-swiss .in{{position:absolute;left:{EDGE}mm;right:{EDGE}mm;top:62mm}}
.cv-swiss h1{{font-size:44pt;color:#111;letter-spacing:-.025em}} .cv-swiss .k{{color:var(--a);margin-bottom:9mm}}
.cv-swiss .rule{{width:56mm;border-top:1.4pt solid #111;margin:11mm 0 7mm}} .cv-swiss .s{{color:#333}}
.cv-swiss .tags{{color:#333;margin-top:7mm}} .cv-swiss .meta{{left:{EDGE}mm;color:#333}}
.cv-band .top{{background:var(--p);color:#fff;height:128mm;padding:30mm {EDGE}mm 0;position:relative}}
.cv-band h1{{color:#fff;font-size:34pt;margin-top:8mm}} .cv-band .k{{opacity:.75}}
.cv-band .bar{{position:absolute;left:{EDGE}mm;bottom:-2.2mm;width:44mm;height:4.4mm;background:var(--a)}}
.cv-band .low{{padding:16mm {EDGE}mm 0}} .cv-band .s{{color:var(--ink)}} .cv-band .tags{{color:var(--p);margin-top:7mm}}
.cv-band .meta{{color:var(--mut);border-top:.7pt solid var(--line);padding-top:6mm}}
.cv-rail .rail{{position:absolute;left:0;top:0;bottom:0;width:22mm;background:linear-gradient(180deg,var(--p),var(--deep2))}}
.cv-rail .in{{position:absolute;left:42mm;right:{EDGE}mm;top:58mm}}
.cv-rail h1{{font-size:36pt;margin:7mm 0 7mm}} .cv-rail .k{{color:var(--a)}}
.cv-rail .acc{{width:16mm;height:2.6mm;background:var(--a);margin:0 0 8mm}} .cv-rail .s{{color:var(--mut)}}
.cv-rail .tags{{color:var(--p);margin-top:8mm}} .cv-rail .meta{{left:42mm;color:var(--mut)}}
.cv-editorial{{background:#faf7f1}} .cv-editorial .in{{position:absolute;left:{EDGE}mm;right:{EDGE}mm;top:70mm}}
.cv-editorial .k{{color:var(--a);border-top:.8pt solid var(--ink);border-bottom:.8pt solid var(--ink);padding:2.4mm 0;
display:inline-block}}
.cv-editorial h1{{font-family:{_stack('Source Serif')};font-size:40pt;font-weight:600;margin:12mm 0 8mm;color:var(--ink)}}
.cv-editorial .s{{font-family:{_stack('Source Serif')};font-style:italic;font-size:14pt;color:var(--mut)}}
.cv-editorial .tags{{color:var(--ink);margin-top:9mm}} .cv-editorial .meta{{left:{EDGE}mm;color:var(--mut)}}
.cv-split .left{{position:absolute;left:0;top:0;bottom:0;width:78mm;background:var(--p);color:#fff;padding:30mm 12mm 0 14mm}}
.cv-split .left .k{{opacity:.8;line-height:1.7}} .cv-split .left .meta{{left:14mm;right:10mm;color:#fff;opacity:.9}}
.cv-split .in{{position:absolute;left:94mm;right:18mm;top:84mm}}
.cv-split h1{{font-size:32pt;color:var(--ink)}} .cv-split .acc{{width:14mm;height:2.6mm;background:var(--a);margin:9mm 0 7mm}}
.cv-split .s{{color:var(--mut)}} .cv-split .tags{{color:var(--p);margin-top:8mm}}
.cv .inside{{margin-top:12mm;max-width:120mm}}
.cv .inside .il{{font-size:8pt;letter-spacing:.18em;text-transform:uppercase;color:var(--mut);margin-bottom:2.5mm}}
.cv .inside .ir{{font-size:10pt;padding:1.7mm 0;border-top:.6pt solid var(--line);color:var(--ink)}}
.cv .inside .ir span{{display:inline-block;width:9mm;color:var(--a);font-variant-numeric:tabular-nums;font-weight:600}}
.cv-split .inside{{max-width:none}} .cv-minimal .in{{bottom:58mm}}
.cv-minimal{{background:#fff}} .cv-minimal .hair{{position:absolute;left:{EDGE}mm;right:{EDGE}mm;top:30mm;border-top:.7pt solid var(--line)}}
.cv-minimal .k{{position:absolute;left:{EDGE}mm;top:36mm;color:var(--mut)}}
.cv-minimal .in{{position:absolute;left:{EDGE}mm;right:{EDGE}mm;bottom:72mm}}
.cv-minimal .dot{{width:7mm;height:7mm;border-radius:50%;background:var(--a);margin-bottom:9mm}}
.cv-minimal h1{{font-size:36pt;color:var(--ink)}} .cv-minimal .s{{color:var(--mut);margin-top:6mm}}
.cv-minimal .tags{{color:var(--ink);margin-top:7mm}} .cv-minimal .meta{{color:var(--mut);bottom:22mm;border-top:.7pt solid var(--line);padding-top:5mm}}
"""


def _cover_html(spec: dict[str, Any], title: str, meta_html: str, inside: list[str] | None = None) -> str:
    """inside = the document's main sections, printed small on the roomier covers (a reader sees the shape of the
    document before turning the page, and the cover stops being an empty sheet)."""
    e = _html.escape
    ins = ""
    if inside and spec["cover"] in ("band", "rail", "minimal", "split", "swiss"):
        ins = "<div class=inside><div class=il>Inside</div>" + "".join(
            f"<div class=ir><span>{i:02d}</span>{_inline(t)}</div>" for i, t in enumerate(inside[:7], 1)) + "</div>"
    k = e(spec.get("kicker") or "")
    sub = f"<div class=s>{e(spec['subtitle'])}</div>" if spec.get("subtitle") else ""
    tags = "".join(f"<span>{e(t)}</span>" for t in spec.get("tags") or [])
    tags = f"<div class=tags>{tags}</div>" if tags else ""
    t = f"<h1>{e(title)}</h1>"
    meta = f"<div class=meta>{meta_html}</div>"
    v = spec["cover"]
    if v == "gradient":
        inner = f"<div class=in><div class=k>{k}</div>{t}{sub}{tags}</div>{meta}"
    elif v == "swiss":
        inner = f"<div class=in>{'<div class=k>' + k + '</div>' if k else ''}{t}<div class=rule></div>{sub}{tags}{ins}</div>{meta}"
    elif v == "band":
        inner = f"<div class=top><div class=k>{k}</div>{t}<div class=bar></div></div><div class=low>{sub}{tags}{ins}</div>{meta}"
    elif v == "rail":
        inner = f"<div class=rail></div><div class=in><div class=k>{k}</div>{t}<div class=acc></div>{sub}{tags}{ins}</div>{meta}"
    elif v == "editorial":
        inner = f"<div class=in>{'<div class=k>' + k + '</div>' if k else ''}{t}{sub}{tags}</div>{meta}"
    elif v == "split":
        inner = f"<div class=left><div class=k>{k}</div>{meta}</div><div class=in>{t}<div class=acc></div>{sub}{tags}{ins}</div>"
    else:   # minimal
        inner = f"<div class=hair></div><div class=k>{k}</div><div class=in><div class=dot></div>{t}{sub}{tags}{ins}</div>{meta}"
    return f"<div class='cv cv-{v}'>{inner}</div>"


def _table(rows: list[list[str]], keep: bool) -> str:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    nums = numeric_columns(rows)
    # short row labels (WI-0002, Q1, GSTR-3B) stay on one line instead of breaking at the hyphen
    key = len(rows) > 1 and all(len(re.sub(r"\*\*", "", r[0]).strip()) <= 14 for r in rows[1:])

    def cls(i: int) -> str:
        return "n" if nums[i] else ("k" if i == 0 and key else "x")
    head = "".join(f"<th class={cls(i)}>{_inline(c)}</th>" for i, c in enumerate(rows[0]))
    body = []
    for r in rows[1:]:
        tot = bool(_TOTAL.match(r[0] or ""))
        cells = "".join(f"<td class={cls(i)}>{_inline(c.replace('**', '') if tot else c)}</td>"
                        for i, c in enumerate(r))
        body.append(f"<tr{' class=tot' if tot else ''}>{cells}</tr>")
    return (f"<table{' class=keep' if keep else ''}><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table>")


def _list(b: dict[str, Any]) -> str:
    tag = b["k"]
    start = f" start={b.get('start', 1)}" if tag == "ol" and b.get("start", 1) != 1 else ""
    items = "".join(f"<li class=l{lvl}>{_inline(t)}</li>" for lvl, t in b["items"])
    return f"<{tag}{start}>{items}</{tag}>"


_HAS_NO = re.compile(r"^(\d+(\.\d+)*[.)]?|[ivxlc]+\.|part\s+[ivx\d]+)\s", re.I)


def headings(blocks: list[dict[str, Any]], numbered: bool) -> list[dict[str, Any]]:
    """Every h1 / h2 with its anchor id and its section number (only when the text has none of its own)."""
    out, n = [], 0
    own = any(_HAS_NO.match(b["t"]) for b in blocks if b["k"] == "h1")
    for i, b in enumerate(blocks):
        if b["k"] == "h1":
            n += 1
            no = f"{n:02d}" if numbered and not own else ""
            out.append({"i": i, "level": 1, "t": b["t"], "no": no, "id": f"s{i}"})
        elif b["k"] == "h2":
            out.append({"i": i, "level": 2, "t": b["t"], "no": "", "id": f"s{i}"})
    return out


def body_html(blocks: list[dict[str, Any]], spec: dict[str, Any], heads: list[dict[str, Any]], *,
              toc_pages: dict[str, int] | None, markers: bool, letterhead: str = "") -> str:
    """The inside pages. toc_pages=None -> no contents page; {} -> pass 1 (blank numbers, markers on)."""
    by_i = {h["i"]: h for h in heads}
    out: list[str] = []
    if toc_pages is not None:
        rows = []
        show2 = sum(1 for h in heads) <= 26
        for h in heads:
            if h["level"] == 2 and not show2:
                continue
            pg = toc_pages.get(h["id"], "")
            no = f"<span class=no>{h['no']}</span>" if h["no"] else ""
            rows.append(f"<a class='row r{h['level']}' href='#{h['id']}'><span class=t>{no}{_inline(h['t'])}</span>"
                        f"<span class=d></span><span class=pg>{pg}</span></a>")
        out.append(f"<section class=toc><h1>{_html.escape(spec.get('toc_title') or 'Contents')}</h1>{''.join(rows)}</section>")
    out.append(f"<div class=body>{letterhead}")
    for i, b in enumerate(blocks):
        k = b["k"]
        if k in ("h1", "h2", "h3"):
            h = by_i.get(i)
            mk = f"<span class=mk>HQX{h['id']}QXH</span>" if (markers and h) else ""
            if k == "h1":
                cls = " class=banner" if spec["headings"] == "banner" else ""
                no = f"<span class=no>{h['no']}</span>" if h and h["no"] else ""
                out.append(f"<h1 id='{h['id']}'{cls}>{no}{_inline(b['t'])}{mk}</h1>")
            elif k == "h2":
                out.append(f"<h2 id='{h['id']}'>{_inline(b['t'])}{mk}</h2>")
            else:
                out.append(f"<h3>{_inline(b['t'])}</h3>")
        elif k == "p":
            out.append(f"<p>{_inline(b['t'])}</p>")
        elif k in ("ul", "ol"):
            out.append(_list(b))
        elif k == "table":
            out.append(_table(b["rows"], keep=len(b["rows"]) <= 9))
        elif k == "stats":
            out.append(f"<div class=stats style='--n:{len(b['items'])}'>" + "".join(
                f"<div class=stat><span class=v>{_inline(v)}</span><span class=l>{_inline(lbl)}</span></div>"
                for v, lbl in b["items"]) + "</div>")
        elif k == "callout":
            paras = "".join(f"<p>{_inline(x)}</p>" for x in b["t"].split("\n") if x.strip())
            out.append(f"<div class='callout {b['kind']}'><div class=ct>{_html.escape(CALLOUTS[b['kind']])}</div>{paras}</div>")
        elif k == "quote":
            out.append("<blockquote>" + "<br>".join(_inline(x) for x in b["t"].split("\n")) + "</blockquote>")
        elif k == "code":
            out.append(f"<pre><code>{_html.escape(b['t'])}</code></pre>")
        elif k == "divider":
            out.append("<hr>")
        elif k == "pagebreak":
            out.append("<div class=pb></div>")
    out.append("</div>")
    return "".join(out)


def _doc(css: str, inner: str, title: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{_html.escape(title)}</title>"
            f"<style>{css}</style></head><body>{inner}</body></html>")


def _header(title: str, spec: dict[str, Any], P: dict[str, str], right: str) -> str:
    left = title if len(title) <= 70 else title[:67] + "..."
    ok = lambda s: all(ord(c) < 0x2000 or c in "·—–₹" for c in s)  # noqa: E731
    e = _html.escape
    return (f"<div style=\"width:100%;font-size:7.4pt;font-family:'Liberation Sans','DejaVu Sans',sans-serif;"
            f"color:{P['muted']};margin:6mm 18mm 0;padding-bottom:1.6mm;border-bottom:.5pt solid {P['line']};"
            f"display:flex;justify-content:space-between\"><span>{e(left) if ok(left) else ''}</span>"
            f"<span>{e(right) if ok(right) else ''}</span></div>")


def _footer(spec: dict[str, Any], P: dict[str, str], left: str) -> str:
    ok = all(ord(c) < 0x2000 or c in "·—–₹" for c in left)
    return (f"<div style=\"width:100%;font-size:7.4pt;font-family:'Liberation Sans','DejaVu Sans',sans-serif;"
            f"color:{P['muted']};margin:0 18mm 5mm;display:flex;justify-content:space-between\">"
            f"<span>{_html.escape(left) if ok else ''}</span>"
            f"<span>Page <span class=pageNumber></span> of <span class=totalPages></span></span></div>")


# ---------------------------------------------------------------- print (Chromium)
_AVAILABLE: dict[str, Any] = {}


def _launch_kw() -> dict[str, Any]:
    kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                                   "--allow-file-access-from-files"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    return kw


class Printer:
    """One Chromium for every print of one document (pass 1, pass 2, cover, a retry)."""

    def __enter__(self) -> "Printer":
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise PrintError(f"playwright missing: {e}")
        self._tmp = tempfile.TemporaryDirectory(prefix="hoola-print-")
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(**_launch_kw())
        except Exception as e:
            self._pw.stop()
            self._tmp.cleanup()
            raise PrintError(f"chromium did not start: {e}")
        self._page = self._browser.new_page()
        self._n = 0
        self.fonts: set[str] = set()          # the @font-face families the last page really loaded
        return self

    def pdf(self, html_text: str, *, header: str = "", footer: str = "", full_bleed: bool = False) -> bytes:
        self._n += 1
        f = Path(self._tmp.name) / f"p{self._n}.html"
        f.write_text(html_text, encoding="utf-8")
        self._page.goto(f.as_uri(), wait_until="load", timeout=60000)
        try:
            self._page.evaluate("document.fonts.ready")
            self.fonts = set(self._page.evaluate(
                "() => { const o = []; document.fonts.forEach(f => { if (f.status === 'loaded') o.push(f.family) });"
                " return o }") or [])
        except Exception:
            self.fonts = set()
        kw: dict[str, Any] = {"format": "A4", "print_background": True, "prefer_css_page_size": False}
        if full_bleed:
            kw["margin"] = {"top": "0", "bottom": "0", "left": "0", "right": "0"}
        else:
            # v0.305.0 the page margin is 8 mm and the text column is padded 10 mm inside it (GUTTER): the words still
            # start 18 mm from the paper edge, and the hanging section numbers live in that 10 mm strip - Chromium
            # clips anything printed in the true page margin, which is where they vanished.
            kw["margin"] = {"top": "22mm", "bottom": "20mm", "left": "8mm", "right": "8mm"}
            if header or footer:
                kw.update(display_header_footer=True, header_template=header or "<span></span>",
                          footer_template=footer or "<span></span>")
        return self._page.pdf(**kw)

    def __exit__(self, *exc: Any) -> None:
        for step in (lambda: self._browser.close(), lambda: self._pw.stop(), lambda: self._tmp.cleanup()):
            try:
                step()
            except Exception:
                pass


def available() -> bool:
    """Chromium can print here (checked once per process)."""
    if "ok" not in _AVAILABLE:
        try:
            with Printer() as p:
                p.pdf("<!doctype html><p>ok</p>")
            _AVAILABLE["ok"] = True
        except Exception as e:
            log.warning("Hoola Print: Chromium not usable, ReportLab fallback: %s", e)
            _AVAILABLE["ok"] = False
    return bool(_AVAILABLE["ok"])


def heading_pages(data: bytes, ids: list[str]) -> dict[str, int]:
    """Pass-1 PDF -> {heading id: page number}, read from the invisible HQX<id>QXH markers."""
    import pypdfium2 as pdfium
    out: dict[str, int] = {}
    doc = pdfium.PdfDocument(io.BytesIO(data))
    try:
        for n in range(len(doc)):
            tp = doc[n].get_textpage()
            txt = re.sub(r"\s+", "", tp.get_text_range() or "")
            for m in re.finditer(r"HQX(s\d+)QXH", txt):
                out.setdefault(m.group(1), n + 1)
    finally:
        doc.close()
    return {i: out[i] for i in ids if i in out}


def swap_cover(body: bytes, cover: bytes) -> bytes:
    """Page 1 of the body print is an empty slot (so the footer counts it); the full-bleed cover takes its place."""
    from pypdf import PdfReader, PdfWriter
    b, c = PdfReader(io.BytesIO(body)), PdfReader(io.BytesIO(cover))
    w = PdfWriter()
    w.add_page(c.pages[0])
    for p in b.pages[1:]:
        w.add_page(p)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def set_meta(data: bytes, title: str, author: str, subject: str) -> bytes:
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(data)))
    w.add_metadata({"/Title": title[:200] or "Hoola document", "/Author": author[:120] or "Hoola",
                    "/Subject": subject[:200], "/Creator": f"Hoola Print {ENGINE_VERSION}",
                    "/Producer": "Hoola Print (Chromium)"})
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


# ---------------------------------------------------------------- QA
def page_fill(data: bytes, top_mm: float = 22, bottom_mm: float = 20) -> list[float]:
    """How far down each page the ink reaches inside the text area (0 = empty, 1 = full)."""
    import pypdfium2 as pdfium
    fills: list[float] = []
    doc = pdfium.PdfDocument(io.BytesIO(data))
    try:
        for n in range(len(doc)):
            img = doc[n].render(scale=0.35, grayscale=True).to_pil().convert("L")
            w, h = img.size
            px_mm = h / 297.0
            y0, y1 = int(top_mm * px_mm) + 2, int(h - bottom_mm * px_mm) - 2
            last = 0
            px = img.load()
            for y in range(y1 - 1, y0, -1):
                if any(px[x, y] < 200 for x in range(int(w * .08), int(w * .92), 2)):
                    last = y
                    break
            fills.append(round(max(0.0, (last - y0) / max(1, y1 - y0)), 3))
    finally:
        doc.close()
    return fills


def qa(data: bytes, *, cover: bool, toc_pages: int, title: str) -> dict[str, Any]:
    issues: list[str] = []
    fills = page_fill(data)
    pages = len(fills)
    skip = {1} if cover else set()
    first_body = (2 if cover else 1) + toc_pages
    skip |= set(range(2 if cover else 1, first_body))
    empty = [n for n, f in enumerate(fills, 1) if n not in skip and f < 0.04]
    sparse = [n for n, f in enumerate(fills, 1) if n not in skip and n != pages and 0.04 <= f < 0.42]
    if empty:
        issues.append(f"blank pages: {empty}")
    if sparse:
        issues.append(f"mostly empty pages: {sparse}")
    if len(data) > 25 * 1024 * 1024:
        issues.append("file over 25 MB")
    return {"status": "pass" if not issues else "warn", "issues": issues, "pages": pages,
            "fill": fills, "sparse": sparse, "empty": empty, "size_kb": round(len(data) / 1024, 1),
            "checked": ["blank-pages", "mostly-empty-pages", "size", "pages", "contents-page-numbers"]}


REVIEW_SYSTEM = """You review a PDF Hoola just made, from page images, like a senior designer before it goes to a
client. Judge: does the look fit the topic, is the cover strong, is the hierarchy clear, are tables / numbers easy to
read, is any page wasted or crowded, does any text look broken. Score 1-10. You may ask for ONE change, only from:
cover (%s), type (%s), density (%s), headings (%s), table (%s), primary / accent (#rrggbb). Ask for a change only when
it clearly makes the document better; otherwise change = {}.""" % (
    ", ".join(COVERS[:-1]), ", ".join(TYPES), ", ".join(DENSITY), ", ".join(HEADINGS), ", ".join(TABLES))


def review_pages(data: bytes, fills: list[float]) -> list[bytes]:
    """Cover + the first inside page + the emptiest middle page, as PNGs."""
    import pypdfium2 as pdfium
    n = len(fills)
    want = [0] + ([1] if n > 1 else []) + ([2] if n > 2 else [])
    if n > 4:
        mid = min(range(2, n - 1), key=lambda i: fills[i])
        if mid not in want:
            want.append(mid)
    out = []
    doc = pdfium.PdfDocument(io.BytesIO(data))
    try:
        for i in want[:4]:
            pil = doc[i].render(scale=0.9).to_pil()
            b = io.BytesIO()
            pil.convert("RGB").save(b, format="PNG", optimize=True)
            out.append(b.getvalue())
    finally:
        doc.close()
    return out


# ---------------------------------------------------------------- the whole job
def _meta_html(author: str, prepared_for: str, date: str, version: str = "1.0") -> str:
    e = _html.escape
    lines = []
    if prepared_for:
        lines.append(f"<b>Prepared for:</b> {e(prepared_for)}")
    lines.append(f"<b>Prepared by:</b> {e(author)}")
    lines.append(f"<b>Date:</b> {e(date)} &nbsp;·&nbsp; <b>Version:</b> {e(version)}")
    return "<br>".join(lines)


def _letterhead(spec: dict[str, Any], title: str, author: str, prepared_for: str, date: str) -> str:
    e = _html.escape
    k = f"<div class=k>{e(spec['kicker'])}</div>" if spec.get("kicker") else ""
    s = f"<div class=s>{e(spec['subtitle'])}</div>" if spec.get("subtitle") else ""
    who = f"For {e(prepared_for)}<br>" if prepared_for else ""
    return f"<div class=lh><div>{k}<h1>{e(title)}</h1>{s}</div><div class=m>{who}{e(author)}<br>{e(date)}</div></div>"


def render(title: str, text: str, spec: dict[str, Any], *, cover: bool, toc: bool, author: str, prepared_for: str,
           subject: str, printer: Printer) -> tuple[bytes, dict[str, Any]]:
    """One full print of the document with this spec (contents numbers real, cover swapped in)."""
    P = palette(spec["primary"], spec["accent"])
    blocks = parse(text)
    if not any(b["k"] in ("h1", "h2", "p", "ul", "ol", "table", "stats") for b in blocks):
        blocks.append({"k": "p", "t": title})
    heads = headings(blocks, spec["headings"] in ("numbered", "banner"))
    date = _dt.date.today().strftime("%d %b %Y")
    css = _css(spec, P)
    lh = "" if cover else _letterhead(spec, title, author, prepared_for, date)
    slot = "<div class=coverslot></div>" if cover else ""
    use_toc = toc and bool(heads)
    head_tpl = _header(title, spec, P, " · ".join(x for x in (spec.get("kicker", "").title(), date) if x))
    foot_tpl = _footer(spec, P, author if not prepared_for else f"{author} · for {prepared_for}")

    def one(toc_pages: dict | None, markers: bool) -> bytes:
        inner = slot + body_html(blocks, spec, heads, toc_pages=toc_pages, markers=markers, letterhead=lh)
        return printer.pdf(_doc(css, inner, title), header=head_tpl, footer=foot_tpl)

    toc_n = 0
    if use_toc:
        first = one({}, True)
        pages = heading_pages(first, [h["id"] for h in heads])
        data = one(pages, False)
        if heads and heads[0]["id"] in pages:
            toc_n = max(0, pages[heads[0]["id"]] - (2 if cover else 1))
    else:
        data = one(None, False)
    loaded = {f.strip("'\"") for f in printer.fonts}
    if cover:
        inside = [h["t"] for h in heads if h["level"] == 1]
        cv = printer.pdf(_doc(css + _cover_css(spec, P), _cover_html(spec, title, _meta_html(
            author, prepared_for, date), inside if len(inside) >= 2 else None), title), full_bleed=True)
        data = swap_cover(data, cv)
    data = set_meta(data, title, author, subject or spec.get("subtitle") or "")
    report = qa(data, cover=cover, toc_pages=toc_n, title=title)
    head, bodyf = TYPES.get(spec["type"], TYPES["sans"])
    report["fonts"] = sorted(loaded)
    missing = [f for f in dict.fromkeys((head, bodyf)) if f not in loaded and _font_used(blocks, f, head, bodyf)]
    if missing:      # the page fell back to a system font: say so (a deploy without app/fonts/print)
        report["issues"].append(f"fonts not loaded: {missing}")
        report["status"] = "warn"
    report["checked"].append("fonts-loaded")
    return data, report


def _font_used(blocks: list[dict[str, Any]], fam: str, head: str, body: str) -> bool:
    """A family is only loaded when some text uses it (body text always; headings only when there are any)."""
    if fam == body:
        return True
    return any(b["k"] in ("h1", "h2", "h3") for b in blocks)


def make_pdf(title: str, text: str, *, style: str | None = "auto", cover: str | bool = "auto",
             toc: str | bool = "auto", author: str = "Hoola", subject: str = "", prepared_for: str = "",
             art: Any = None, reviewer: Any = None) -> dict[str, Any]:
    """Build a designed PDF the Claude way. Same return shape as pdfgen.make_pdf:
    {data, pages, cover, toc, style, palette, design, qa}. Raises PrintError when Chromium can't print."""
    title = _clean(title).strip() or "Document"
    text = _clean(text or "")
    spec = art_direct(title, text, style, subject, ask=art)
    if subject and not spec.get("subtitle"):
        spec["subtitle"] = subject[:140]
    blocks = parse(text)
    h1s = sum(1 for b in blocks if b["k"] == "h1")
    chars = sum(len(str(b.get("t", ""))) for b in blocks) + sum(
        sum(len(c) for r in b["rows"] for c in r) for b in blocks if b["k"] == "table")
    est = chars / 2600 + 0.25 * sum(1 for b in blocks if b["k"] in ("table", "stats", "code"))
    use_cover = (est >= 1.2 or (h1s >= 5 and est >= 0.8)) if cover == "auto" else bool(cover)
    if spec.get("cover") == "none" and cover == "auto":
        use_cover = False
    if use_cover and spec.get("cover") == "none":
        spec["cover"] = FAMILY_LOOK.get(spec["family"], FAMILY_LOOK["general"])["cover"]
    use_toc = (use_cover and h1s >= 4 and (est >= 1.8 or h1s >= 8)) if toc == "auto" else bool(toc)
    if use_toc and not use_cover and cover == "auto":
        use_cover = True
    from ..config import get_settings
    st = get_settings()
    reviewed: dict[str, Any] = {}
    with Printer() as pr:
        kw = dict(cover=use_cover, toc=use_toc, author=author or "Hoola", prepared_for=prepared_for,
                  subject=subject, printer=pr)
        data, report = render(title, text, spec, **kw)
        if (report["sparse"] or report["empty"]) and spec["density"] != "compact":
            STATS["compact_retry"] += 1          # a wasted page: one tighter print, kept only when it is better
            s2 = dict(spec, density="compact")
            d2, r2 = render(title, text, s2, **kw)
            if len(r2["sparse"]) + len(r2["empty"]) < len(report["sparse"]) + len(report["empty"]):
                data, report, spec = d2, r2, s2
        want_review = reviewer is not None or (bool(getattr(st, "doc_review", True)) and st.anthropic_api_key
                                               and (style or "auto") == "auto")
        if want_review:
            try:
                imgs = review_pages(data, report["fill"])
                prompt = (f"Document: {title}\nTopic: {spec['label']}\nCurrent look: "
                          f"{({k: spec[k] for k in ('cover', 'type', 'density', 'headings', 'table', 'primary', 'accent')})}\n"
                          f"Pages: {report['pages']}, fill per page: {report['fill']}\n"
                          'Reply JSON: {"score": 1-10, "issues": ["..."], "change": {}}')
                STATS["review"] += 1
                got = (reviewer or _ask_opus)(REVIEW_SYSTEM, prompt, "doc_critique", imgs, 70.0) or {}
                reviewed = {"score": got.get("score"), "issues": [str(x)[:200] for x in (got.get("issues") or [])][:6]}
                change = got.get("change") if isinstance(got.get("change"), dict) else {}
                s3 = _sane(spec, change) if change else spec
                score = got.get("score") if isinstance(got.get("score"), (int, float)) else 10
                if s3 != spec and score < 8:
                    d3, r3 = render(title, text, s3, **kw)
                    if not (len(r3["sparse"]) + len(r3["empty"]) > len(report["sparse"]) + len(report["empty"])):
                        data, report, spec = d3, r3, s3
                        reviewed["changed"] = {k: change[k] for k in change if k in s3}
                        STATS["review_changed"] += 1
            except Exception as e:
                log.info("doc review skipped: %s", e)
                reviewed = {"skipped": type(e).__name__}
    STATS["printed"] += 1
    head, body = TYPES.get(spec["type"], TYPES["sans"])
    report["review"] = reviewed
    design = {"topic": spec["family"], "label": spec["label"], "cover": spec["cover"] if use_cover else "letterhead",
              "fonts": {"head": head, "body": body}, "table": spec["table"], "type": spec["type"],
              "density": spec["density"], "headings": spec["headings"], "colours": [spec["primary"], spec["accent"]],
              "detected": bool(spec.get("detected")), "art": spec.get("source", "router"), "engine": "chromium",
              "why": spec.get("why", "")}
    return {"data": data, "pages": report["pages"], "cover": use_cover, "toc": use_toc, "style": style or "auto",
            "palette": {"primary": spec["primary"], "accent": spec["accent"]}, "design": design, "qa": report}
