"""v0.192.0 docstudio.pdfgen - the ReportLab report line, ported from the Claude Code pdf skill
(briefs/report.md): cascade palette, registered font pool with Devanagari shaping, TOC gate,
table iron rules, safe_keep_together, orphan prevention, character safety, header/footer, QA
after build. v0.192.0 adds the DESIGN ROUTER (designs.py): one fitting design per user topic -
6 cover architectures (band / rail / plate / sunrise / minimal / classic), topic font pairings,
grid or clean tables - all colours still minted by tokens.Palette's tier caps, all fonts from a
defensively-registered pool with the FreeSerif/FreeSans floor. Honesty note: the skill renders
covers via HTML+Playwright for interactive use; an always-on server needs a deterministic cover,
so covers are drawn natively in ReportLab following the same design language.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import io
import re
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily, stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, HRFlowable, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from .. import indicpdf
from . import designs, tokens

PAGE_W, PAGE_H = A4
MARGIN = 0.9 * inch
TOP_M, BOT_M = 0.85 * inch, 0.8 * inch
AVAIL_W = PAGE_W - 2 * MARGIN
AVAIL_H = PAGE_H - TOP_M - BOT_M

_FONT_STATE: dict[str, Any] = {"done": False, "serif": False, "pool": set()}
_RUPEE_OK: dict[str, bool] = {}

# The pool: families registered defensively (a missing file drops THAT family, never the build).
# FreeSerif/FreeSans ship in the freefont package the engine already depends on - the guaranteed
# floor. The others (DejaVu / Liberation / Tinos / Carlito) add the topic typographic variety.
_FONT_DIRS: dict[str, tuple[str, dict[str, str]]] = {
    "FreeSerif":       ("freefont", {"regular": "FreeSerif.ttf", "bold": "FreeSerifBold.ttf",
                                     "italic": "FreeSerifItalic.ttf", "bolditalic": "FreeSerifBoldItalic.ttf"}),
    "FreeSans":        ("freefont", {"regular": "FreeSans.ttf", "bold": "FreeSansBold.ttf",
                                     "italic": "FreeSansOblique.ttf", "bolditalic": "FreeSansBoldOblique.ttf"}),
    "DejaVuSans":      ("dejavu", {"regular": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf"}),
    "DejaVuSerif":     ("dejavu", {"regular": "DejaVuSerif.ttf", "bold": "DejaVuSerif-Bold.ttf"}),
    "LiberationSans":  ("liberation", {"regular": "LiberationSans-Regular.ttf", "bold": "LiberationSans-Bold.ttf",
                                       "italic": "LiberationSans-Italic.ttf", "bolditalic": "LiberationSans-BoldItalic.ttf"}),
    "LiberationSerif": ("liberation", {"regular": "LiberationSerif-Regular.ttf", "bold": "LiberationSerif-Bold.ttf",
                                       "italic": "LiberationSerif-Italic.ttf", "bolditalic": "LiberationSerif-BoldItalic.ttf"}),
    "Tinos":           ("english", {"regular": "Tinos-Regular.ttf", "bold": "Tinos-Bold.ttf",
                                     "italic": "Tinos-Italic.ttf", "bolditalic": "Tinos-BoldItalic.ttf"}),
    "Carlito":         ("english", {"regular": "Carlito-Regular.ttf", "bold": "Carlito-Bold.ttf",
                                     "italic": "Carlito-Italic.ttf", "bolditalic": "Carlito-BoldItalic.ttf"}),
}


def _register_family(name: str, dirname: str, files: dict[str, str]) -> bool:
    """Register one family (regular + bold mandatory; italic falls back when the file is absent)."""
    try:
        base = f"/usr/share/fonts/truetype/{dirname}"
        pdfmetrics.registerFont(TTFont(name, f"{base}/{files['regular']}"))
        bold = f"{name}-Bold"
        if files.get("bold"):
            pdfmetrics.registerFont(TTFont(bold, f"{base}/{files['bold']}"))
        else:
            bold = name
        italic = f"{name}-Italic"
        if files.get("italic"):
            pdfmetrics.registerFont(TTFont(italic, f"{base}/{files['italic']}"))
        else:
            italic = name
        bolditalic = f"{name}-BoldItalic"
        if files.get("bolditalic") and files.get("bold") and files.get("italic"):
            pdfmetrics.registerFont(TTFont(bolditalic, f"{base}/{files['bolditalic']}"))
        else:
            bolditalic = bold
        registerFontFamily(name, normal=name, bold=bold, italic=italic, boldItalic=bolditalic)
        _FONT_STATE["pool"].add(name)
        return True
    except Exception:
        return False


def ensure_fonts() -> bool:
    """Register the allowed pool once (FreeSerif family + Devanagari via indicpdf + topic fonts)."""
    if _FONT_STATE["done"]:
        return _FONT_STATE["serif"]
    _FONT_STATE["done"] = True
    for name, (dirname, files) in _FONT_DIRS.items():
        _register_family(name, dirname, files)
    _FONT_STATE["serif"] = "FreeSerif" in _FONT_STATE["pool"]
    indicpdf.dev_font(False)
    indicpdf.dev_font(True)
    return _FONT_STATE["serif"]


def _resolve_pair(chains: dict | None) -> dict[str, str]:
    """Resolve a design's font candidate chains against the registered pool (first wins).
    Every returned name IS registered, so Paragraph <b>/<i> markup resolves through the family."""
    pool = _FONT_STATE["pool"]

    def pick(chain: list[str] | None) -> str:
        for c in (chain or []):
            if c in pool:
                return c
        return "FreeSerif" if "FreeSerif" in pool else "Helvetica"

    head, body = pick((chains or {}).get("head")), pick((chains or {}).get("body"))

    def bold_of(base: str) -> str:
        return f"{base}-Bold"   # pool families register -Bold; Helvetica-Bold is a real builtin

    def italic_of(base: str) -> str:
        if base in pool:
            return f"{base}-Italic"
        return "Helvetica-Oblique" if base == "Helvetica" else base

    return {"head": head, "head_b": bold_of(head),
            "body": body, "body_b": bold_of(body), "body_i": italic_of(body)}


def _glyph_ok(font: str, ch: str) -> bool:
    try:
        f = pdfmetrics.getFont(font)
        return ord(ch) in getattr(f.face, "charToGlyph", {})
    except Exception:
        return False


def _t(text: str) -> str:
    """Escape + character safety for Paragraph text, then Devanagari shaping markup."""
    s = tokens.sanitize_text(str(text or ""))
    if not _RUPEE_OK.get("serif"):
        _RUPEE_OK["serif"] = _FONT_STATE["serif"] and _glyph_ok("FreeSerif", "\u20b9")
    if not _RUPEE_OK["serif"]:
        s = s.replace("\u20b9", "Rs ")
    s = _html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return indicpdf.rl_markup(s)


def _tb(text: str) -> str:  # bold variant for table headers (shaping with bold dev font)
    s = tokens.sanitize_text(str(text or ""))
    s = _html.escape(s, quote=False)
    return indicpdf.rl_markup(s, bold=True)


# ---------------------------------------------------------------- block parser

_STAT = re.compile(r"^\[stat:\s*(.+?)\s*\|\s*(.+?)\]\s*$")
_NUM = re.compile(r"^(\d+)[.)]\s+")


def parse_blocks(text: str) -> list[dict[str, Any]]:
    """The make_document mini-language, extended: '# ' h1, '## ' h2, '### ' h3, '- ' bullet,
    '1. ' numbered, '| a | b |' table rows, '> ' quote, '[stat: 12% | label]' callout, '---' divider."""
    out: list[dict[str, Any]] = []
    tbl: list[list[str]] = []

    def flush_tbl():
        nonlocal tbl
        if tbl:
            out.append({"k": "table", "rows": tbl})
            tbl = []

    for raw in tokens.sanitize_text(text or "").splitlines():
        line = raw.rstrip()
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            tbl.append(cells)
            continue
        flush_tbl()
        if not s:
            continue
        if s in ("---", "***", "___"):
            out.append({"k": "divider"})
        elif s.startswith("### "):
            out.append({"k": "h3", "t": s[4:].strip()})
        elif s.startswith("## "):
            out.append({"k": "h2", "t": s[3:].strip()})
        elif s.startswith("# "):
            out.append({"k": "h1", "t": s[2:].strip()})
        elif s.startswith("> "):
            if out and out[-1]["k"] == "quote":
                out[-1]["t"] += "<br/>" + s[2:].strip()
            else:
                out.append({"k": "quote", "t": s[2:].strip()})
        elif s.startswith("[stat:") and "|" in s:
            m = _STAT.match(s)
            if m:
                out.append({"k": "stat", "v": m.group(1), "label": m.group(2)})
                continue
            out.append({"k": "body", "t": s})
        elif re.match(r"^[-*\u2022]\s+", s):
            out.append({"k": "bullet", "t": re.sub(r"^[-*\u2022]\s+", "", s)})
        elif _NUM.match(s):
            out.append({"k": "num", "t": _NUM.sub("", s)})
        else:
            out.append({"k": "body", "t": s})
    flush_tbl()
    return out


# ---------------------------------------------------------------- styles

def _styles(pal: tokens.Palette, justify: bool, fonts: dict | None = None) -> dict[str, ParagraphStyle]:
    F = fonts or _resolve_pair(None)
    S: dict[str, ParagraphStyle] = {}

    def st(name, *, size, font=None, bold=False, align=None, indent=0, before=0, after=6,
           color=None, italic=False, bullet_indent=None):
        base = font or F["body"]
        if bold:
            fname = F["head_b"] if base == F["head"] else F["body_b"]
        elif italic:
            fname = F["body_i"] if base == F["body"] else base
        else:
            fname = base
        S[name] = ParagraphStyle(
            name=name, fontName=fname,
            fontSize=size, leading=tokens.leading(size),
            alignment=(TA_LEFT if align is None else align),
            leftIndent=indent, firstLineIndent=0, spaceBefore=before, spaceAfter=after,
            textColor=color or colors.HexColor(pal.text_primary),
            bulletIndent=bullet_indent if bullet_indent is not None else max(0, indent - 12),
            wordWrap=None, splitLongWords=0)
        return S[name]

    body_align = TA_JUSTIFY if justify else TA_LEFT
    st("body", size=tokens.SCALE["body"], align=body_align, after=8)
    st("bullet", size=tokens.SCALE["body"], align=TA_LEFT, indent=16, after=4)
    st("quote", size=tokens.SCALE["body"], align=TA_LEFT, indent=10, after=8, italic=True,
       color=colors.HexColor(pal.text_muted))
    st("caption", size=tokens.SCALE["caption"], align=TA_CENTER, after=8,
       color=colors.HexColor(pal.text_muted))
    st("h1", size=tokens.SCALE["h1"], font=F["head"], bold=True, before=16, after=4,
       color=colors.HexColor(pal.header_fill))
    st("h2", size=tokens.SCALE["h2"], font=F["head"], bold=True, before=13, after=6)
    st("h3", size=tokens.SCALE["h3"], font=F["head"], bold=True, before=11, after=5)
    st("cell", size=9.5, align=TA_LEFT, after=0)
    st("cellc", size=9.5, align=TA_CENTER, after=0)
    st("cellh", size=9.5, bold=True, align=TA_CENTER, after=0, color=colors.white)
    st("stat", size=tokens.SCALE["stat_big"], font=F["head"], bold=True, align=TA_CENTER, after=0,
       color=colors.HexColor(pal.accent))
    st("statlabel", size=tokens.SCALE["stat_label"], align=TA_CENTER, after=0,
       color=colors.HexColor(pal.text_muted))
    st("toc", size=11.5, after=3)
    st("toctitle", size=17, font=F["head"], bold=True, after=12, color=colors.HexColor(pal.header_fill))
    return S


# ---------------------------------------------------------------- tables

def _table_flowable(rows: list[list[str]], pal: tokens.Palette, S: dict, avail_w: float,
                    table_style: str = "grid") -> Table:
    ncol = max(len(r) for r in rows)
    norm = [[c for c in r] + [""] * (ncol - len(r)) for r in rows]
    widths = [max(tokens.display_width(r[i]) for r in norm) for i in range(ncol)]
    total = sum(widths) or 1.0
    ratios = [max(0.08, w / total) for w in widths]
    scale = 1.0 / sum(ratios)
    table_w = avail_w * 0.96                       # 85-100% of the content area, never wider
    col_w = [r * scale * table_w for r in ratios]
    numeric = [all(re.fullmatch(r"[-+,\.\s\u20b9Rs$%\d]+", norm[r_i][i] or "x")
                   for r_i in range(1, len(norm))) for i in range(ncol)]
    data = [[Paragraph(_tb(c), S["cellh"]) for c in norm[0]]]
    for r in norm[1:]:
        data.append([Paragraph(_t(c), S["cellc" if (numeric[i] or len(str(c)) <= 12) else "cell"])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=col_w, hAlign="CENTER", repeatRows=1)
    # iron rules kept in BOTH variants: Paragraph cells, widths <= available, centred,
    # repeatRows, M-tier header fill + L-tier zebra. "clean" trades the grid for horizontal
    # rules only (editorial look); "grid" is the v0.189 every-line table.
    cmds: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal.header_fill)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(pal.table_stripe)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if table_style == "clean":
        cmds += [("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor(pal.accent)),
                 ("LINEBELOW", (0, -1), (-1, -1), 0.75, colors.HexColor(pal.border))]
    else:
        cmds += [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(pal.border))]
    t.setStyle(TableStyle(cmds))
    return t


def _stat_flowable(value: str, label: str, pal: tokens.Palette, S: dict) -> Table:
    box = Table([[Paragraph(f"<b>{_t(value)}</b>", S["stat"])],
                 [Paragraph(_t(label), S["statlabel"])]], colWidths=[190])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(pal.card_bg)),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(pal.accent)),
        ("TOPPADDING", (0, 0), (-1, 0), 10), ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("TOPPADDING", (0, 1), (-1, 1), 2), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return box


def _quote_flowable(text: str, pal: tokens.Palette, S: dict) -> Table:
    q = Table([[Paragraph(_t(text), S["quote"])]], colWidths=[AVAIL_W * 0.92])
    q.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, -1), 2, colors.HexColor(pal.accent2)),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return q


# ---------------------------------------------------------------- cover + header/footer

def _runs_width(text: str, font: str, size: float) -> float:
    return sum(stringWidth(p, font if not d else (indicpdf.dev_font(False) or font), size)
               for p, d in indicpdf.runs(text))


def _draw_canvas_runs(c: Any, x: float, y: float, text: str, font: str, size: float) -> None:
    dev = indicpdf.dev_font(False)
    for piece, is_dev in indicpdf.runs(text):
        f = dev if is_dev else font
        c.setFont(f, size)
        c.drawString(x, y, piece)
        x += stringWidth(piece, f, size)


def _cover(c: Any, pal: tokens.Palette, title: str, subtitle: str, author: str,
           kicker: str, variant: str, F: dict) -> None:
    """Six cover architectures, every colour palette-minted (no hardcoded hex), chunked titles,
    Devanagari via canvas runs, each <=5 components. v0.189 geometry preserved exactly for the
    classic variant; band / rail / plate / sunrise / minimal are the v0.192 topic architectures."""
    tb, body = F["head_b"], F["body"]
    meta = f"{author}   \u00b7   {_dt.date.today().strftime('%d %b %Y')}"
    brand = "Hoola \u00b7 Document Studio"

    def _meta_dark() -> None:
        c.setFillColor(colors.HexColor(pal.text_muted))
        c.setFont(body, tokens.SCALE["cover_meta"])
        c.drawString(MARGIN, PAGE_H * 0.12, meta)
        c.setFont(body, tokens.SCALE["footer"] + 1)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H * 0.12, brand)

    def _meta_light(y: float) -> None:
        c.setFillColor(colors.Color(1, 1, 1, 0.85))
        c.setFont(body, tokens.SCALE["cover_meta"])
        c.drawString(MARGIN, y, meta)
        c.setFont(body, tokens.SCALE["footer"] + 1)
        c.drawRightString(PAGE_W - MARGIN, y, brand)

    def _title(x: float, y: float, color: Any) -> float:
        c.setFillColor(color)
        yy = y
        for line in tokens.title_chunk(title):
            _draw_canvas_runs(c, x, yy, line, tb, tokens.SCALE["cover_title"])
            yy -= tokens.SCALE["cover_title"] * 1.22
        return yy

    def _subtitle(x: float, y: float, color: Any) -> None:
        if not subtitle:
            return
        c.setFillColor(color)
        c.setFont(body, tokens.SCALE["cover_sub"])
        yy = y
        for line in tokens.title_chunk(subtitle, words_per_line=5, max_lines=2):
            _draw_canvas_runs(c, x, yy, line, body, tokens.SCALE["cover_sub"])
            yy -= tokens.SCALE["cover_sub"] * 1.3

    def _kicker(x: float, y: float, color: Any) -> None:
        c.setFillColor(color)
        c.setFont(body, tokens.SCALE["kicker"])
        c.drawString(x, y, kicker.upper())

    c.setFillColor(colors.HexColor(pal.page_bg))
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    if variant == "band":
        # full-width deep band at the top, title reversed in white - annual-report posture
        c.setFillColor(colors.HexColor(pal.header_fill))
        c.rect(0, PAGE_H - 210, PAGE_W, 210, stroke=0, fill=1)
        _kicker(MARGIN, PAGE_H - 46, colors.Color(1, 1, 1, 0.72))
        _title(MARGIN, PAGE_H - 96, colors.white)
        _subtitle(MARGIN, PAGE_H - 246, colors.HexColor(pal.text_muted))
        _meta_dark()
    elif variant == "rail":
        # full-height side rail, content beside it - engineering / product posture
        c.setFillColor(colors.HexColor(pal.cover_block))
        c.rect(0, 0, 76, PAGE_H, stroke=0, fill=1)
        x0 = 116
        _kicker(x0, PAGE_H * 0.86, colors.HexColor(pal.text_muted))
        ye = _title(x0, PAGE_H * 0.72, colors.HexColor(pal.text_primary))
        c.setFillColor(colors.HexColor(pal.accent))
        c.rect(x0, ye - 10, 34, 5, stroke=0, fill=1)
        _subtitle(x0, ye - 44, colors.HexColor(pal.text_muted))
        c.setFillColor(colors.HexColor(pal.text_muted))
        c.setFont(body, tokens.SCALE["cover_meta"])
        c.drawString(x0, PAGE_H * 0.12, meta)
        c.setFont(body, tokens.SCALE["footer"] + 1)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H * 0.12, brand)
    elif variant == "plate":
        # solid plate along the bottom carrying meta, title above - school / clinic posture
        c.setFillColor(colors.HexColor(pal.header_fill))
        c.rect(0, 0, PAGE_W, 190, stroke=0, fill=1)
        _kicker(MARGIN, PAGE_H * 0.88, colors.HexColor(pal.text_muted))
        ye = _title(MARGIN, PAGE_H * 0.68, colors.HexColor(pal.text_primary))
        c.setStrokeColor(colors.HexColor(pal.accent))
        c.setLineWidth(2)
        c.line(MARGIN, ye - 8, MARGIN + 64, ye - 8)
        _subtitle(MARGIN, 126, colors.Color(1, 1, 1, 0.9))
        _meta_light(74)
    elif variant == "sunrise":
        # light corner block + deep bottom band - campaign / festive posture
        c.setFillColor(colors.HexColor(pal.card_bg))
        c.rect(PAGE_W * 0.52, PAGE_H - 220, PAGE_W * 0.48, 220, stroke=0, fill=1)
        c.setFillColor(colors.HexColor(pal.cover_block))
        c.rect(0, 0, PAGE_W, 104, stroke=0, fill=1)
        _kicker(MARGIN, PAGE_H * 0.86, colors.HexColor(pal.text_muted))
        ye = _title(MARGIN, PAGE_H * 0.70, colors.HexColor(pal.text_primary))
        c.setStrokeColor(colors.HexColor(pal.accent))
        c.setLineWidth(2.2)
        c.line(MARGIN, ye - 8, MARGIN + 64, ye - 8)
        _subtitle(MARGIN, ye - 40, colors.HexColor(pal.text_muted))
        _meta_light(46)
    elif variant == "minimal":
        # hairlines and a small accent square, zero fills - legal / academic posture
        c.setStrokeColor(colors.HexColor(pal.border))
        c.setLineWidth(0.8)
        c.line(MARGIN, PAGE_H - 88, PAGE_W - MARGIN, PAGE_H - 88)
        _kicker(MARGIN, PAGE_H - 130, colors.HexColor(pal.text_muted))
        ye = _title(MARGIN, PAGE_H * 0.74, colors.HexColor(pal.text_primary))
        c.setFillColor(colors.HexColor(pal.accent))
        c.rect(MARGIN, ye - 12, 12, 12, stroke=0, fill=1)
        _subtitle(MARGIN, ye - 46, colors.HexColor(pal.text_muted))
        _meta_dark()
    else:  # classic - the v0.189 cover, geometry unchanged
        c.setFillColor(colors.HexColor(pal.cover_block))
        c.rect(0, PAGE_H - 150, 7, 150, stroke=0, fill=1)
        _kicker(MARGIN, PAGE_H * 0.88, colors.HexColor(pal.text_muted))
        ye = _title(MARGIN, PAGE_H * 0.74, colors.HexColor(pal.text_primary))
        c.setStrokeColor(colors.HexColor(pal.accent))
        c.setLineWidth(2)
        c.line(MARGIN, ye - 6, MARGIN + 64, ye - 6)
        _subtitle(MARGIN, ye - 32, colors.HexColor(pal.text_muted))
        _meta_dark()


def _header_footer(title: str, author: str, pal: tokens.Palette, F: dict | None = None,
                   variant: str = "classic", kicker: str = "", page_num: str = "plain"):
    F = F or _resolve_pair(None)

    def draw(c: Any, doc: Any) -> None:
        if doc.page == 1 and getattr(doc, "_ds_cover", False):
            _cover(c, pal, doc._ds_title, doc._ds_sub, author, doc._ds_kicker, doc._ds_variant, F)
            return
        c.saveState()
        c.setFont(F["body"], tokens.SCALE["footer"])
        c.setFillColor(colors.HexColor(pal.text_muted))
        c.drawString(MARGIN, PAGE_H - 0.55 * inch, tokens.sanitize_text(title)[:80])
        c.setStrokeColor(colors.HexColor(pal.accent))
        c.setLineWidth(1.2)
        c.line(MARGIN, PAGE_H - 0.62 * inch, PAGE_W - MARGIN, PAGE_H - 0.62 * inch)
        c.setStrokeColor(colors.HexColor(pal.border))
        c.setLineWidth(0.5)
        c.line(MARGIN, 0.58 * inch, PAGE_W - MARGIN, 0.58 * inch)
        c.drawString(MARGIN, 0.42 * inch, tokens.sanitize_text(author)[:60])
        c.drawRightString(PAGE_W - MARGIN, 0.42 * inch,
                          f"Page {doc.page}" if page_num == "Page N" else str(doc.page))
        c.restoreState()
    return draw


# ---------------------------------------------------------------- doc template + TOC gate

class _TocDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable) -> None:
        if hasattr(flowable, "bookmark_key"):
            self.notify("TOCEntry", (getattr(flowable, "bookmark_level", 0),
                                     getattr(flowable, "bookmark_text", ""),
                                     self.page, flowable.bookmark_key))


def _heading(text: str, style: ParagraphStyle, level: int) -> Paragraph:
    import hashlib
    key = "h_" + hashlib.md5(f"{level}:{text}".encode()).hexdigest()[:8]
    p = Paragraph(f'<a name="{key}"/><b>{_t(text)}</b>', style)
    p.bookmark_key = key
    p.bookmark_level = level
    p.bookmark_text = tokens.sanitize_text(text)
    return p


def _safe_keep(flowables: list, cap: float) -> list:
    try:
        total = sum(f.wrap(AVAIL_W, PAGE_H)[1] for f in flowables)
    except Exception:
        return list(flowables)
    if total <= cap:
        return [KeepTogether(flowables)]
    if len(flowables) >= 2:
        return [KeepTogether(flowables[:2])] + list(flowables[2:])
    return list(flowables)


# ---------------------------------------------------------------- build

def make_pdf(title: str, text: str, *, style: str | None = None, cover: str | bool = "auto",
             toc: str | bool = "auto", author: str = "Hoola", subject: str = "") -> dict[str, Any]:
    """Build a designed PDF. The design (palette + cover architecture + fonts + table style)
    comes from the design router: style="auto" (default) matches the user's TOPIC, explicit
    styles force a look. Returns {data, pages, cover, toc, style, palette, design, qa}."""
    ensure_fonts()
    spec = designs.resolve_design(title, text or "", style)
    pal = tokens.Palette(spec["hue"], spec["style_name"])
    F = _resolve_pair(spec["fonts"])
    blocks = parse_blocks(text or "")
    h1s = [b for b in blocks if b["k"] == "h1"]
    chars = sum(len(str(b.get("t", ""))) for b in blocks) + sum(
        sum(len(c) for r in b["rows"] for c in r) for b in blocks if b["k"] == "table")
    est_pages = 1 + chars / 1700 + 0.35 * len([b for b in blocks if b["k"] == "table"])
    use_cover = (est_pages >= 2.2) if cover == "auto" else bool(cover)   # in doubt -> cover (skill rule)
    use_toc = (len(h1s) >= 4 and use_cover) if toc == "auto" else bool(toc)
    if use_toc and not use_cover:
        use_cover = True                     # skill rule: TOC requires a cover
    justify = not tokens.has_devanagari(text) and sum(
        1 for ch in (text or "") if ord(ch) > 0x2E80) < len(text or "") * 0.1
    S = _styles(pal, justify, F)
    buf = io.BytesIO()

    doc = _TocDoc(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                  topMargin=TOP_M, bottomMargin=BOT_M,
                  title=tokens.sanitize_text(title)[:120] or "Hoola document",
                  author=author, creator="Hoola Document Studio v0.192.0",
                  subject=tokens.sanitize_text(subject)[:200])
    doc._ds_cover, doc._ds_title, doc._ds_sub = use_cover, title, subject
    doc._ds_kicker, doc._ds_variant = spec["label"], spec["cover"]
    on_page = _header_footer(title, author, pal, F, spec["cover"], spec["label"], spec["page_num"])
    story: list = []
    if use_toc:
        story.append(Paragraph("<b>Table of Contents</b>", S["toctitle"]))
        story.append(HRFlowable(width="100%", color=colors.HexColor(pal.accent), thickness=1.2, spaceAfter=12))
        toc_obj = TableOfContents()
        toc_obj.levelStyles = [
            ParagraphStyle(name="TOC0", fontName=F["head_b"],
                           fontSize=11.5, leading=17, leftIndent=6, spaceBefore=4),
            ParagraphStyle(name="TOC1", fontName=F["body"],
                           fontSize=10.5, leading=15, leftIndent=24),
        ]
        story.append(toc_obj)
        story.append(PageBreak())
    num = 0
    num_group = 0
    for b in blocks:
        k = b["k"]
        if k == "h1":
            num += 1
            num_group = 0
            story.append(CondPageBreak(AVAIL_H * tokens.H1_ORPHAN_FRACTION))
            head = _heading(f"{num}. {b['t']}", S["h1"], 0)
            rule = HRFlowable(width="100%", color=colors.HexColor(pal.accent),
                              thickness=spec["h1_rule"], spaceBefore=0, spaceAfter=10)
            story.extend(_safe_keep([head, rule], AVAIL_H * tokens.MAX_KEEP_FRACTION))
        elif k == "h2":
            story.append(CondPageBreak(58))
            story.append(_heading(b["t"], S["h2"], 1))
        elif k == "h3":
            story.append(CondPageBreak(46))
            story.append(_heading(b["t"], S["h3"], 1))
        elif k == "body":
            story.append(Paragraph(_t(b["t"]), S["body"]))
        elif k == "bullet":
            num_group = 0
            story.append(Paragraph(_t(b["t"]), S["bullet"], bulletText="\u2022"))
        elif k == "num":
            num_group += 1
            story.append(Paragraph(_t(b["t"]), S["bullet"], bulletText=f"{num_group}."))
        elif k == "table":
            story.append(Spacer(1, 8))
            story.append(_table_flowable(b["rows"], pal, S, AVAIL_W, spec["table"]))
            story.append(Spacer(1, 12))
        elif k == "quote":
            story.append(Spacer(1, 4))
            story.append(_quote_flowable(b["t"], pal, S))
            story.append(Spacer(1, 6))
        elif k == "stat":
            story.append(Spacer(1, 6))
            story.extend(_safe_keep([_stat_flowable(b["v"], b["label"], pal, S)],
                                    AVAIL_H * tokens.MAX_KEEP_FRACTION))
            story.append(Spacer(1, 8))
        elif k == "divider":
            story.append(HRFlowable(width="30%", color=colors.HexColor(pal.border), thickness=0.6,
                                    spaceBefore=8, spaceAfter=10, hAlign="LEFT"))
    if not story:
        story.append(Paragraph(_t(title), S["h1"]))
        story.append(Spacer(1, 10))
    if use_cover:
        story.insert(0, PageBreak())       # page 1 belongs to the canvas-drawn cover alone
    if use_toc:
        doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)   # TOC gate: multiBuild only
    else:
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    data = buf.getvalue()
    qa = _qa(data, use_toc, title, author, subject)
    design = {"topic": spec["family"], "label": spec["label"], "cover": spec["cover"],
              "fonts": {"head": F["head"], "body": F["body"]}, "table": spec["table"],
              "detected": bool(spec.get("detected"))}
    return {"data": data, "pages": qa["pages"], "cover": use_cover, "toc": use_toc,
            "style": pal.style_name, "palette": pal.summary(), "design": design, "qa": qa}


def _qa(data: bytes, had_toc: bool, title: str, author: str, subject: str) -> dict[str, Any]:
    """Post-build QA: blank pages, page count, metadata, size (pypdf, already a dependency)."""
    issues: list[str] = []
    pages = 0
    blank: list[int] = []
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(data))
        pages = len(r.pages)
        for i, p in enumerate(r.pages):
            try:
                if not (p.extract_text() or "").strip():
                    blank.append(i + 1)
            except Exception:
                pass
        meta = r.metadata or {}
        if not (meta.get("/Title") or "").strip():
            issues.append("metadata: title missing")
    except Exception as e:  # pragma: no cover
        issues.append(f"read-back failed: {type(e).__name__}")
    if blank:
        issues.append(f"blank pages: {blank}")
    if had_toc and pages < 3:
        issues.append("toc but fewer than 3 pages")
    if len(data) > 25 * 1024 * 1024:
        issues.append("file over 25 MB")
    return {"status": "pass" if not issues else "warn", "issues": issues, "pages": pages,
            "size_kb": round(len(data) / 1024, 1), "checked": ["blank-pages", "metadata", "size", "pages"]}
