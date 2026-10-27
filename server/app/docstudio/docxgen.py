"""v0.189.0 docstudio.docxgen - the Word line, ported from the Claude Code docx skill
(references/design-system.md + common-rules.md + routes/create.md):

  - cover follows recipe R1 (pure paragraph, left-aligned - the validated freehand-free recipe):
    kicker + chunked title with calcTitleLayout-style sizing + accent rule + meta block, own section,
    NEVER a PageBreak at the section end (double break = blank page in MS Office)
  - line spacing 1.3x everywhere (the skill's mandatory default), body left-aligned for
    Devanagari/Hinglish (justified only for clean English), complex-script font set for Hindi
  - real Heading 1/2/3 styles in the palette's colours (never bold-simulated headings) so the
    navigation pane and the TOC field work
  - TOC: real Word field + the italic refresh hint (mandatory) + PageBreak right after
  - tables: PRIMARY header row + white bold text, warm zebra, cell margins, header row repeats
    across pages, rows never split - the three cross-page rules the skill calls mandatory
"""
from __future__ import annotations

import datetime as _dt
import io
import re
from typing import Any

from . import tokens
from .pdfgen import parse_blocks

MAX_ROWS = 500


def _style_font(doc: Any, style: Any, name: str, size: float, bold: bool = False,
                color: str | None = None, italic: bool = False) -> None:
    from docx.shared import Pt, RGBColor
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    if color:
        style.font.color.rgb = RGBColor.from_string(color.lstrip("#").upper())
    rpr = style.element.get_or_add_rPr()
    for tag in ("w:cs", "w:eastAsia"):
        el = rpr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}" + tag.split(":")[1])
        if el is None:
            el = rpr.makeelement("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}" + tag.split(":")[1], {})
            rpr.append(el)
        el.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii", name)
        el.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi", name)


def _cover_size(lines: list[str]) -> float:
    longest = max(len(l) for l in lines)
    if longest <= 14:
        return 34.0
    if longest <= 24:
        return 29.0
    if longest <= 40:
        return 25.0
    return 22.0


def _toc_field(paragraph: Any) -> None:
    xml = ('<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'w:instr=\' TOC \\o "1-3" \\h \\z \\u \'><w:r><w:t></w:t></w:r></w:fldSimple>')
    from docx.oxml import parse_xml
    paragraph._p.append(parse_xml(xml))


def _page_field(paragraph: Any) -> None:
    xml = ('<w:fldSimple xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'w:instr=\' PAGE \\* arabic \\* MERGEFORMAT \'><w:r><w:t>1</w:t></w:r></w:fldSimple>')
    from docx.oxml import parse_xml
    paragraph._p.append(parse_xml(xml))


def _shade(cell: Any, hexs: str) -> None:
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    cell._tc.get_or_add_tcPr().append(parse_xml(r'<w:shd {} w:val="clear" w:fill="{}"/>'.format(nsdecls("w"), hexs.lstrip("#").upper())))


def _table_margins(table: Any, twips: int = 140) -> None:
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    tbl_pr = table._tbl.tblPr
    tbl_pr.append(parse_xml(
        r'<w:tblCellMar {}>'
        r'<w:left w:w="{}" w:type="dxa"/><w:right w:w="{}" w:type="dxa"/>'
        r'<w:top w:w="60" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/></w:tblCellMar>'.format(nsdecls("w"), twips, twips)))


def _cant_split_and_repeat(table: Any) -> None:
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    for i, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(parse_xml(r"<w:cantSplit %s/>" % nsdecls("w")))
        if i == 0:
            tr_pr.append(parse_xml(r"<w:tblHeader %s/>" % nsdecls("w")))


def make_docx(title: str, text: str, *, style: str | None = None, cover: str | bool = "auto",
              toc: str | bool = "auto", author: str = "Hoola", subject: str = "") -> dict[str, Any]:
    """Build a designed Word file. Returns {data, headings, tables, toc, style, palette, qa}."""
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    pal = tokens.palette_for(title, style)
    P = {k: v.lstrip("#").upper() for k, v in pal.pdf_colors().items()}
    blocks = parse_blocks(text or "")
    h1s = [b for b in blocks if b["k"] == "h1"]
    chars = sum(len(str(b.get("t", ""))) for b in blocks) + sum(
        sum(len(c) for r in b["rows"] for c in r) for b in blocks if b["k"] == "table")
    est_pages = 1 + chars / 1500
    use_cover = (est_pages >= 1.7) if cover == "auto" else bool(cover)   # in doubt -> cover (skill rule)
    use_toc = (len(h1s) >= 4) if toc == "auto" else bool(toc)
    justify = not tokens.has_devanagari(text) and sum(1 for ch in (text or "") if ord(ch) > 0x2E80) < len(text or "") * 0.1

    d = Document()
    FONT = "Calibri"
    normal = d.styles["Normal"]
    _style_font(d, normal, FONT, 11)
    normal.paragraph_format.line_spacing = 1.3          # the skill's mandatory default
    normal.paragraph_format.space_after = Pt(6)
    for lvl, (size, col) in {"Heading 1": (17, P["header_fill"]), "Heading 2": (14, P["text_primary"]),
                             "Heading 3": (12, P["text_primary"])}.items():
        st = d.styles[lvl]
        _style_font(d, st, FONT, size, bold=True, color=col)
        st.paragraph_format.line_spacing = 1.3
        st.paragraph_format.space_before = Pt(14 if lvl == "Heading 1" else 10)
        st.paragraph_format.space_after = Pt(6)

    sec = d.sections[0]
    sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.0)
    sec.left_margin, sec.right_margin = Cm(2.4), Cm(2.4)   # symmetric

    if use_cover:
        kicker = d.add_paragraph()
        kr = kicker.add_run(pal.style_name.upper())
        kr.font.size, kr.font.bold = Pt(10), True
        kr.font.color.rgb = RGBColor.from_string(P["accent"].upper())
        kicker.paragraph_format.space_before, kicker.paragraph_format.space_after = Pt(46), Pt(18)
        lines = tokens.title_chunk(title)
        tsize = _cover_size(lines)
        for i, line in enumerate(lines):
            tp = d.add_paragraph()
            tr = tp.add_run(tokens.sanitize_text(line))
            tr.font.size, tr.font.bold = Pt(tsize), True
            tr.font.color.rgb = RGBColor.from_string(P["text_primary"].upper())
            tp.paragraph_format.line_spacing = 1.15
            tp.paragraph_format.space_after = Pt(4)
        rule = d.add_paragraph()
        rule.paragraph_format.space_before, rule.paragraph_format.space_after = Pt(10), Pt(16)
        ppr = rule._p.get_or_add_pPr()
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        ppr.append(parse_xml(r'<w:pBdr %s><w:bottom w:val="single" w:sz="18" w:space="1" w:color="%s"/></w:pBdr>'
                             % (nsdecls("w"), P["accent"].upper())))
        if subject:
            sp = d.add_paragraph()
            sr = sp.add_run(tokens.sanitize_text(subject))
            sr.font.size = Pt(14)
            sr.font.color.rgb = RGBColor.from_string(P["text_muted"].upper())
        meta = d.add_paragraph()
        mr = meta.add_run(f"{author}   \u00b7   {_dt.date.today().strftime('%d %b %Y')}")
        mr.font.size = Pt(11)
        mr.font.color.rgb = RGBColor.from_string(P["text_muted"].upper())
        meta.paragraph_format.space_before = Pt(120)
        # section break to the body - cover section ends WITHOUT a PageBreak (blank-page rule 1)
        d.add_section(WD_SECTION.NEW_PAGE)

    if use_toc:
        t = d.add_paragraph()
        tr = t.add_run("Table of Contents")
        tr.font.size, tr.font.bold = Pt(17), True
        tr.font.color.rgb = RGBColor.from_string(P["header_fill"].upper())
        _toc_field(d.add_paragraph())
        hint = d.add_paragraph()
        hr = hint.add_run("Page numbers gale lagne par is par right-click karke 'Update Field' dabaiye.")
        hr.font.size, hr.font.italic = Pt(8.5), True
        hr.font.color.rgb = RGBColor.from_string(P["text_muted"].upper())
        from docx.enum.text import WD_BREAK
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)   # MANDATORY break after the TOC

    headings: list[str] = []
    tables = 0
    num_group = 0
    h1n = 0
    for b in blocks:
        k = b["k"]
        if k == "h1":
            h1n += 1
            headings.append(b["t"])
            d.add_heading(f"{h1n}. {tokens.sanitize_text(b['t'])}", level=1)
        elif k in ("h2", "h3"):
            headings.append(b["t"])
            d.add_heading(tokens.sanitize_text(b["t"]), level=2 if k == "h2" else 3)
        elif k == "body":
            p = d.add_paragraph()
            _runs_md(p, b["t"], P)
            if justify and not tokens.has_devanagari(b["t"]):
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif k == "bullet":
            num_group = 0
            p = d.add_paragraph(style="List Bullet")
            _runs_md(p, b["t"], P)
        elif k == "num":
            num_group += 1
            p = d.add_paragraph()
            r = p.add_run(f"{num_group}. ")
            r.bold = True
            _runs_md(p, b["t"], P)
        elif k == "quote":
            p = d.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            _runs_md(p, b["t"], P, italic=True)
        elif k == "stat":
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(tokens.sanitize_text(b["v"]))
            r.font.size, r.font.bold = Pt(20), True
            r.font.color.rgb = RGBColor.from_string(P["accent"].upper())
            lp = d.add_paragraph()
            lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            lr = lp.add_run(tokens.sanitize_text(b["label"]))
            lr.font.size = Pt(8.5)
            lr.font.color.rgb = RGBColor.from_string(P["text_muted"].upper())
        elif k == "divider":
            p = d.add_paragraph()
            ppr = p._p.get_or_add_pPr()
            from docx.oxml import parse_xml
            from docx.oxml.ns import nsdecls
            ppr.append(parse_xml(r'<w:pBdr %s><w:bottom w:val="single" w:sz="6" w:space="1" w:color="%s"/></w:pBdr>'
                                 % (nsdecls("w"), P["border"].upper())))
        elif k == "table":
            rows = b["rows"][:MAX_ROWS]
            if not rows:
                continue
            ncol = max(len(r) for r in rows)
            tb = d.add_table(rows=len(rows), cols=ncol)
            tb.style = "Table Grid"
            tb.autofit = True
            _table_margins(tb)
            for i, row in enumerate(rows):
                for j in range(ncol):
                    cell = tb.cell(i, j)
                    cell.text = ""
                    cp = cell.paragraphs[0]
                    cp.paragraph_format.line_spacing = 1.15
                    cp.paragraph_format.space_after = Pt(2)
                    val = row[j] if j < len(row) else ""
                    run = cp.add_run(tokens.sanitize_text(str(val)))
                    run.font.size = Pt(9.5)
                    if i == 0:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor.from_string("FFFFFF")
                        _shade(cell, P["header_fill"])
                    elif (i % 2) == 0:
                        _shade(cell, P["table_stripe"])
            _cant_split_and_repeat(tb)
            tables += 1
            d.add_paragraph()

    # footer: page number field, right-aligned, above a light rule
    footer = sec.footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _page_field(fp)
    for r in fp.runs:
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor.from_string(P["text_muted"].upper())
    if use_cover:  # footers/headers inherit; the cover section keeps no page number
        sec.footer.is_linked_to_previous = True

    buf = io.BytesIO()
    d.core_properties.title = tokens.sanitize_text(title)[:200]
    d.core_properties.author = author
    d.core_properties.comments = tokens.sanitize_text(subject)[:200]
    d.save(buf)
    data = buf.getvalue()
    qa = _qa(data, use_toc)
    return {"data": data, "headings": headings[:20], "tables": tables, "toc": use_toc,
            "cover": use_cover, "style": pal.style_name, "palette": pal.summary(), "qa": qa}


def _runs_md(p: Any, text: str, P: dict, italic: bool = False) -> None:
    """**bold** inline markup -> real bold runs; Devanagari handled by the cs font."""
    s = tokens.sanitize_text(str(text or ""))
    for i, part in enumerate(re.split(r"(\*\*[^*]+\*\*)", s)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            r = p.add_run(part[2:-2])
            r.bold = True
        else:
            r = p.add_run(part)
        r.italic = italic


def _qa(data: bytes, had_toc: bool) -> dict[str, Any]:
    issues: list[str] = []
    paras = tables = 0
    try:
        from docx import Document
        d = Document(io.BytesIO(data))
        paras = len(d.paragraphs)
        tables = len(d.tables)
        if not any(p.text.strip() for p in d.paragraphs) and not tables:
            issues.append("document empty")
        joined = "\n".join(p.text for p in d.paragraphs)
        for bad in ("TODO", "lorem ipsum", "xxx"):
            if bad.lower() in joined.lower():
                issues.append(f"placeholder text in document: {bad}")
    except Exception as e:
        issues.append(f"read-back failed: {type(e).__name__}")
    if len(data) > 25 * 1024 * 1024:
        issues.append("file over 25 MB")
    return {"status": "pass" if not issues else "warn", "issues": issues, "paragraphs": paras,
            "tables": tables, "size_kb": round(len(data) / 1024, 1), "checked": ["re-open", "placeholders", "size"]}
