"""v0.189.0 docstudio.pdfgen - the ReportLab report line, ported from the Claude Code pdf skill
(briefs/report.md): cascade palette, registered font pool with Devanagari shaping, TOC gate,
table iron rules, safe_keep_together, orphan prevention, character safety, cover, header/footer,
QA after build. Honesty note: the skill renders covers via HTML+Playwright for interactive use;
an always-on server needs a deterministic cover, so the cover is drawn natively in ReportLab
following the same design language (light bg, one accent bar, chunked title, meta block, <=4 components).
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
from . import tokens

PAGE_W, PAGE_H = A4
MARGIN = 0.9 * inch
TOP_M, BOT_M = 0.85 * inch, 0.8 * inch
AVAIL_W = PAGE_W - 2 * MARGIN
AVAIL_H = PAGE_H - TOP_M - BOT_M

_FONT_STATE: dict[str, bool] = {"done": False, "serif": False}
_RUPEE_OK: dict[str, bool] = {}


def ensure_fonts() -> bool:
    """Register the allowed pool once (FreeSerif family + Devanagari via indicpdf)."""
    if _FONT_STATE["done"]:
        return _FONT_STATE["serif"]
    _FONT_STATE["done"] = True
    try:
        base = "/usr/share/fonts/truetype/freefont"
        pdfmetrics.registerFont(TTFont("FreeSerif", f"{base}/FreeSerif.ttf"))
        pdfmetrics.registerFont(TTFont("FreeSerif-Bold", f"{base}/FreeSerifBold.ttf"))
        pdfmetrics.registerFont(TTFont("FreeSerif-Italic", f"{base}/FreeSerifItalic.ttf"))
        pdfmetrics.registerFont(TTFont("FreeSerif-BoldItalic", f"{base}/FreeSerifBoldItalic.ttf"))
        registerFontFamily("FreeSerif", normal="FreeSerif", bold="FreeSerif-Bold",
                           italic="FreeSerif-Italic", boldItalic="FreeSerif-BoldItalic")
        _FONT_STATE["serif"] = True
    except Exception:  # pragma: no cover - freefont ships with the deploy image
        _FONT_STATE["serif"] = False
    indicpdf.dev_font(False)
    indicpdf.dev_font(True)
    return _FONT_STATE["serif"]


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

def _styles(pal: tokens.Palette, justify: bool) -> dict[str, ParagraphStyle]:
    serif = "FreeSerif" if _FONT_STATE["serif"] else "Helvetica"
    fam_bold = f"{serif}-Bold" if _FONT_STATE["serif"] else "Helvetica-Bold"
    S: dict[str, ParagraphStyle] = {}

    def st(name, *, size, font=None, bold=False, align=None, indent=0, before=0, after=6,
           color=None, italic=False, bullet_indent=None):
        S[name] = ParagraphStyle(
            name=name, fontName=fam_bold if bold else (("FreeSerif-Italic" if italic else font) or serif),
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
    st("h1", size=tokens.SCALE["h1"], bold=True, before=16, after=4,
       color=colors.HexColor(pal.header_fill))
    st("h2", size=tokens.SCALE["h2"], bold=True, before=13, after=6)
    st("h3", size=tokens.SCALE["h3"], bold=True, before=11, after=5)
    st("cell", size=9.5, align=TA_LEFT, after=0)
    st("cellc", size=9.5, align=TA_CENTER, after=0)
    st("cellh", size=9.5, bold=True, align=TA_CENTER, after=0, color=colors.white)
    st("stat", size=tokens.SCALE["stat_big"], bold=True, align=TA_CENTER, after=0,
       color=colors.HexColor(pal.accent))
    st("statlabel", size=tokens.SCALE["stat_label"], align=TA_CENTER, after=0,
       color=colors.HexColor(pal.text_muted))
    st("toc", size=11.5, after=3)
    st("toctitle", size=17, bold=True, after=12, color=colors.HexColor(pal.header_fill))
    return S


# ---------------------------------------------------------------- tables

def _table_flowable(rows: list[list[str]], pal: tokens.Palette, S: dict, avail_w: float) -> Table:
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
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal.header_fill)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(pal.table_stripe)]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(pal.border)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
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


def _cover(c: Any, pal: tokens.Palette, title: str, subtitle: str, author: str, style_name: str) -> None:
    serif = "FreeSerif" if _FONT_STATE["serif"] else "Helvetica"
    serif_b = f"{serif}-Bold" if _FONT_STATE["serif"] else "Helvetica-Bold"
    c.setFillColor(colors.HexColor(pal.page_bg))
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(pal.cover_block))          # one accent bar, top-left to bottom
    c.rect(0, PAGE_H - 150, 7, 150, stroke=0, fill=1)
    # kicker (style name) at 12% from top
    c.setFillColor(colors.HexColor(pal.text_muted))
    c.setFont(serif, tokens.SCALE["kicker"])
    c.drawString(MARGIN, PAGE_H * 0.88, style_name.upper())
    # chunked title, 2-4 words per line, never a single line
    y = PAGE_H * 0.74
    c.setFillColor(colors.HexColor(pal.text_primary))
    for line in tokens.title_chunk(title):
        _draw_canvas_runs(c, MARGIN, y, line, serif_b, tokens.SCALE["cover_title"])
        y -= tokens.SCALE["cover_title"] * 1.22
    y -= 6
    c.setStrokeColor(colors.HexColor(pal.accent))
    c.setLineWidth(2)
    c.line(MARGIN, y, MARGIN + 64, y)
    if subtitle:
        y -= 26
        c.setFillColor(colors.HexColor(pal.text_muted))
        c.setFont(serif, tokens.SCALE["cover_sub"])
        for line in tokens.title_chunk(subtitle, words_per_line=5, max_lines=2):
            _draw_canvas_runs(c, MARGIN, y, line, serif, tokens.SCALE["cover_sub"])
            y -= tokens.SCALE["cover_sub"] * 1.3
    # meta block, bottom-left; brand, bottom-right (two bounding boxes, opposite regions)
    meta = f"{author}   \u00b7   {_dt.date.today().strftime('%d %b %Y')}"
    c.setFillColor(colors.HexColor(pal.text_muted))
    c.setFont(serif, tokens.SCALE["cover_meta"])
    c.drawString(MARGIN, PAGE_H * 0.12, meta)
    c.setFont(serif, tokens.SCALE["footer"] + 1)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H * 0.12, "Hoola \u00b7 Document Studio")


def _header_footer(title: str, author: str, pal: tokens.Palette):
    serif = "FreeSerif" if _FONT_STATE["serif"] else "Helvetica"

    def draw(c: Any, doc: Any) -> None:
        if doc.page == 1 and getattr(doc, "_ds_cover", False):
            _cover(c, pal, doc._ds_title, doc._ds_sub, author, doc._ds_style)
            return
        c.saveState()
        c.setFont(serif, tokens.SCALE["footer"])
        c.setFillColor(colors.HexColor(pal.text_muted))
        c.drawString(MARGIN, PAGE_H - 0.55 * inch, tokens.sanitize_text(title)[:80])
        c.setStrokeColor(colors.HexColor(pal.accent))
        c.setLineWidth(1.2)
        c.line(MARGIN, PAGE_H - 0.62 * inch, PAGE_W - MARGIN, PAGE_H - 0.62 * inch)
        c.setStrokeColor(colors.HexColor(pal.border))
        c.setLineWidth(0.5)
        c.line(MARGIN, 0.58 * inch, PAGE_W - MARGIN, 0.58 * inch)
        c.drawString(MARGIN, 0.42 * inch, tokens.sanitize_text(author)[:60])
        c.drawRightString(PAGE_W - MARGIN, 0.42 * inch, str(doc.page))
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
    """Build a designed PDF. Returns {data, pages, cover, toc, style, palette, qa}."""
    ensure_fonts()
    pal = tokens.palette_for(title, style)
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
    S = _styles(pal, justify)
    buf = io.BytesIO()

    doc = _TocDoc(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                  topMargin=TOP_M, bottomMargin=BOT_M,
                  title=tokens.sanitize_text(title)[:120] or "Hoola document",
                  author=author, creator="Hoola Document Studio v0.189.0",
                  subject=tokens.sanitize_text(subject)[:200])
    doc._ds_cover, doc._ds_title, doc._ds_sub, doc._ds_style = use_cover, title, subject, pal.style_name
    on_page = _header_footer(title, author, pal)
    story: list = []
    if use_toc:
        story.append(Paragraph("<b>Table of Contents</b>", S["toctitle"]))
        story.append(HRFlowable(width="100%", color=colors.HexColor(pal.accent), thickness=1.2, spaceAfter=12))
        toc_obj = TableOfContents()
        toc_obj.levelStyles = [
            ParagraphStyle(name="TOC0", fontName="FreeSerif-Bold" if _FONT_STATE["serif"] else "Helvetica-Bold",
                           fontSize=11.5, leading=17, leftIndent=6, spaceBefore=4),
            ParagraphStyle(name="TOC1", fontName="FreeSerif" if _FONT_STATE["serif"] else "Helvetica",
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
            rule = HRFlowable(width="100%", color=colors.HexColor(pal.accent), thickness=1.2,
                              spaceBefore=0, spaceAfter=10)
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
            story.append(_table_flowable(b["rows"], pal, S, AVAIL_W))
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
    return {"data": data, "pages": qa["pages"], "cover": use_cover, "toc": use_toc,
            "style": pal.style_name, "palette": pal.summary(), "qa": qa}


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
