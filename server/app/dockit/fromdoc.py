"""D4 PDF -> Word / Excel / PowerPoint, built on the server from the PDF's own words, tables and pictures
(pdfplumber MIT + pypdfium2 + python-docx / openpyxl / python-pptx). No PyMuPDF, no pdf2docx (AGPL / GPL).

Honest about what it is: an EDITABLE copy - headings, paragraphs, tables and pictures in reading order - not a
pixel copy of the layout (no tool does that faithfully for every PDF). Scanned pages are read with the OCR layer
first when the reader is installed; otherwise they go in as pictures and are named."""
from __future__ import annotations

import io
import re
import statistics
from typing import Any

from . import convert, core
from .core import DocError


def _ocr_if_needed(data: bytes, language: str) -> tuple[bytes, list[int], list[int]]:
    """Scanned pages get the invisible text layer first (so their words can be taken out)."""
    texts = convert.page_texts(data)
    scanned = [i + 1 for i, t in enumerate(texts) if not t.strip()]
    if not scanned:
        return data, [], []
    from . import ocrlayer
    if not ocrlayer.ready():
        return data, [], scanned
    r = ocrlayer.searchable(data, language, ",".join(map(str, scanned[:ocrlayer.MAX_OCR_PAGES])))
    return r["bytes"], r["done"], r.get("still_empty", [])


# ---------------------------------------------------------------------------------------------------- numbers
_NUM = re.compile(r"^\(?-?\s*(?:₹|rs\.?|inr)?\s*[-+]?\d[\d,]*(?:\.\d+)?\s*\)?\s*(?:%|cr|dr)?$", re.I)


def number(cell: Any) -> float | int | None:
    """'1,23,456.50' / '₹ 1,200' / '(450)' / '12.5%' / '-75' -> a number; anything else -> None."""
    s = str(cell or "").strip()
    if not s or not _NUM.match(s) or not re.search(r"\d", s):
        return None
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-") or s.lower().endswith("dr")
    t = re.sub(r"(?i)₹|rs\.?|inr|cr|dr|[()%,+\s-]", "", s)
    try:
        v = float(t)
    except ValueError:
        return None
    if s.endswith("%"):
        v = v / 100
    v = -v if neg else v
    return int(v) if v.is_integer() and "." not in t and not s.endswith("%") else v


# ---------------------------------------------------------------------------------------------------- tables
def tables(data: bytes, pages: Any = "all") -> list[dict[str, Any]]:
    """Every table pdfplumber finds (ruled tables first, then text-aligned ones) -> [{page, rows, bbox}]."""
    import pdfplumber
    out = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        idx = core.pages(pages or "all", len(pdf.pages))
        for i in idx:
            page = pdf.pages[i]
            found = page.find_tables()
            if not found:
                found = page.find_tables({"vertical_strategy": "text", "horizontal_strategy": "text",
                                          "min_words_vertical": 2, "min_words_horizontal": 2})
            for t in found:
                rows = [[(c or "").strip() for c in r] for r in t.extract()]
                rows = [r for r in rows if any(r)]
                if len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                    out.append({"page": i + 1, "rows": rows, "bbox": t.bbox})
    return out


def _total_check(rows: list[list[Any]]) -> list[str]:
    """A row that says 'total' is checked against the sum of the numbers above it, column by column."""
    notes = []
    for ri, row in enumerate(rows):
        if not row or not re.search(r"(?i)\b(total|grand total|kul|कुल|sum)\b", " ".join(str(c) for c in row[:2])):
            continue
        for ci, cell in enumerate(row):
            tot = number(cell)
            if tot is None or ci == 0:
                continue
            above = [number(r[ci]) for r in rows[:ri] if ci < len(r)]
            vals = [v for v in above if v is not None]
            if len(vals) < 2:
                continue
            s = round(sum(vals), 2)
            if abs(s - float(tot)) > 0.011:
                notes.append(f"row {ri + 1}, column {ci + 1}: the table says {tot} but the numbers above add up to {s}")
    return notes


def to_xlsx(data: bytes, pages: Any = "all", language: str = "", one_sheet: bool = False) -> dict[str, Any]:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
    data2, ocred, still = _ocr_if_needed(data, language)
    found = tables(data2, pages)
    wb = Workbook()
    wb.remove(wb.active)
    notes: list[str] = []
    numbers = 0
    if not found:
        ws = wb.create_sheet("Text")                    # no table: the lines, one per row, numbers split out
        for line in "\n".join(convert.page_texts(data2, pages)).splitlines():
            parts = [p for p in re.split(r"\s{2,}|\t", line.strip()) if p]
            if parts:
                ws.append([number(p) if number(p) is not None else p for p in parts])
        notes.append("No table was found, so every line of text is a row (columns split where the PDF had wide gaps).")
    for k, t in enumerate(found, 1):
        if one_sheet:
            ws = wb["Tables"] if "Tables" in wb.sheetnames else wb.create_sheet("Tables")
            if ws.max_row > 1:
                ws.append([])
            ws.append([f"Table {k} (page {t['page']})"])
            ws.cell(ws.max_row, 1).font = Font(bold=True)
        else:
            ws = wb.create_sheet(f"P{t['page']} T{k}"[:31])
        for r, row in enumerate(t["rows"]):
            vals = []
            for c in row:
                n = number(c)
                vals.append(n if n is not None else c)
                numbers += n is not None
            ws.append(vals)
            if r == 0:
                for c in range(1, len(vals) + 1):
                    ws.cell(ws.max_row, c).font = Font(bold=True)
        for c in range(1, max(len(r) for r in t["rows"]) + 1):
            width = max(len(str(r[c - 1])) if c - 1 < len(r) else 0 for r in t["rows"])
            ws.column_dimensions[get_column_letter(c)].width = min(60, max(8, width + 2))
        for n in _total_check(t["rows"]):
            notes.append(f"Table {k} (page {t['page']}): {n}.")
    if still:
        notes.append(f"Pages {', '.join(map(str, still[:20]))} are pictures with no readable text; their tables are not in "
                     "the workbook.")
    buf = io.BytesIO()
    wb.save(buf)
    return {"bytes": buf.getvalue(), "tables": len(found), "numbers": numbers, "ocr_pages": ocred, "notes": notes}


# ---------------------------------------------------------------------------------------------------- word
def _lines(page, skip: list[tuple]) -> list[dict[str, Any]]:
    words = page.extract_words(keep_blank_chars=False, use_text_flow=True, extra_attrs=["size", "fontname"])
    inside = lambda w: any(b[0] - 1 <= w["x0"] and w["x1"] <= b[2] + 1 and b[1] - 1 <= w["top"] and w["bottom"] <= b[3] + 1
                           for b in skip)  # noqa: E731
    lines: list[dict[str, Any]] = []
    for w in words:
        if inside(w):
            continue
        if lines and abs(w["top"] - lines[-1]["top"]) < max(2.5, w["size"] * 0.35):
            ln = lines[-1]
            ln["text"] += (" " if w["x0"] - ln["x1"] > w["size"] * 0.15 else "") + w["text"]
            ln["x1"], ln["size"] = w["x1"], max(ln["size"], w["size"])
            ln["bold"] = ln["bold"] and "bold" in w["fontname"].lower()
        else:
            lines.append({"text": w["text"], "top": w["top"], "bottom": w["bottom"], "x0": w["x0"], "x1": w["x1"],
                          "size": w["size"], "bold": "bold" in w["fontname"].lower()})
    return lines


def to_docx(data: bytes, pages: Any = "all", language: str = "", pictures: bool = True) -> dict[str, Any]:
    import pdfplumber
    import pypdfium2 as pdfium
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Inches, Pt
    data2, ocred, still = _ocr_if_needed(data, language)
    doc = Document()
    st = doc.styles["Normal"]
    st.font.size = Pt(11)
    counts = {"paragraphs": 0, "headings": 0, "tables": 0, "pictures": 0}
    pdoc = pdfium.PdfDocument(data2)
    try:
        with pdfplumber.open(io.BytesIO(data2)) as pdf:
            idx = core.pages(pages or "all", len(pdf.pages))
            sizes = [w["size"] for i in idx[:20] for w in pdf.pages[i].extract_words(extra_attrs=["size"])]
            body = statistics.median(sizes) if sizes else 11
            first = pdf.pages[idx[0]]
            if first.width > first.height:
                sec = doc.sections[0]
                sec.orientation = WD_ORIENT.LANDSCAPE
                sec.page_width, sec.page_height = sec.page_height, sec.page_width
            for n_i, i in enumerate(idx):
                page = pdf.pages[i]
                if n_i:
                    doc.add_page_break()
                tbls = page.find_tables()
                boxes = [t.bbox for t in tbls]
                blocks: list[tuple[float, str, Any]] = [(t.bbox[1], "table", t) for t in tbls]
                lines = _lines(page, boxes)
                para: list[dict] = []
                for ln in lines + [None]:                                # paragraphs = lines close together
                    if ln is not None and para and ln["top"] - para[-1]["bottom"] < para[-1]["size"] * 0.9 \
                            and abs(ln["size"] - para[-1]["size"]) < 1:
                        para.append(ln)
                        continue
                    if para:
                        blocks.append((para[0]["top"], "para", para))
                    para = [ln] if ln is not None else []
                if pictures:
                    for im in page.images:
                        if (im["x1"] - im["x0"]) * (im["bottom"] - im["top"]) > 3600:
                            blocks.append((im["top"], "image", im))
                if i + 1 in still:
                    blocks = [(0, "scan", None)]
                for _, kind, obj in sorted(blocks, key=lambda b: b[0]):
                    if kind == "para":
                        text = " ".join(x["text"] for x in obj)
                        size = obj[0]["size"]
                        if size >= body * 1.45 and len(text) < 160:
                            doc.add_heading(text, level=1)
                            counts["headings"] += 1
                        elif (size >= body * 1.15 or all(x["bold"] for x in obj)) and len(text) < 160:
                            doc.add_heading(text, level=2)
                            counts["headings"] += 1
                        else:
                            p = doc.add_paragraph()
                            for k, x in enumerate(obj):
                                p.add_run(("" if k == 0 else " ") + x["text"])
                            counts["paragraphs"] += 1
                    elif kind == "table":
                        rows = [[(c or "").strip() for c in r] for r in obj.extract()]
                        rows = [r for r in rows if any(r)]
                        if not rows:
                            continue
                        cols = max(len(r) for r in rows)
                        t = doc.add_table(rows=len(rows), cols=cols)
                        t.style = "Table Grid"
                        for r, row in enumerate(rows):
                            for c in range(cols):
                                t.cell(r, c).text = row[c] if c < len(row) else ""
                        counts["tables"] += 1
                    elif kind in ("image", "scan"):
                        pg = pdoc[i]
                        try:
                            img = pg.render(scale=150 / 72).to_pil().convert("RGB")
                        finally:
                            pg.close()
                        if kind == "image":
                            s = img.width / float(page.width)
                            img = img.crop((obj["x0"] * s, obj["top"] * s, obj["x1"] * s, obj["bottom"] * s))
                            width = min(6.0, (obj["x1"] - obj["x0"]) / 72)
                        else:
                            width = 6.0
                        b = io.BytesIO()
                        img.save(b, "JPEG", quality=85)
                        b.seek(0)
                        doc.add_picture(b, width=Inches(max(0.5, width)))
                        counts["pictures"] += 1
    finally:
        pdoc.close()
    buf = io.BytesIO()
    doc.save(buf)
    notes = ["An editable copy: headings, paragraphs, tables and pictures in reading order; fonts, columns and exact "
             "positions are approximate."]
    if ocred:
        notes.append(f"Pages {', '.join(map(str, ocred[:20]))} were scans and were read with OCR first: check names and "
                     "numbers.")
    if still:
        notes.append(f"Pages {', '.join(map(str, still[:20]))} could not be read and went in as pictures.")
    return {"bytes": buf.getvalue(), **counts, "ocr_pages": ocred, "notes": notes}


# ---------------------------------------------------------------------------------------------------- powerpoint
def to_pptx(data: bytes, pages: Any = "all", dpi: int = 150) -> dict[str, Any]:
    """One slide per page: the page as a full-slide picture (looks exactly like the PDF), its words in the notes."""
    from pptx import Presentation
    from pptx.util import Emu
    imgs = convert.pdf_to_images(data, pages or "all", dpi=dpi, fmt="jpg")
    texts = convert.page_texts(data, pages or "all")
    if not imgs:
        raise DocError("No pages to turn into slides.")
    prs = Presentation()
    w0, h0 = imgs[0]["width"], imgs[0]["height"]
    prs.slide_width = Emu(12192000)
    prs.slide_height = Emu(int(12192000 * h0 / w0))
    blank = prs.slide_layouts[6]
    for im, t in zip(imgs, texts):
        s = prs.slides.add_slide(blank)
        sw, sh = prs.slide_width, prs.slide_height
        r = min(sw / im["width"], sh / im["height"])
        w, h = int(im["width"] * r), int(im["height"] * r)
        s.shapes.add_picture(io.BytesIO(im["bytes"]), int((sw - w) / 2), int((sh - h) / 2), w, h)
        if t.strip():
            s.notes_slide.notes_text_frame.text = t.strip()[:8000]
    buf = io.BytesIO()
    prs.save(buf)
    return {"bytes": buf.getvalue(), "slides": len(imgs),
            "notes": ["Each slide is the page as a picture (it looks exactly like the PDF); the page's words are in the "
                      "slide notes. To edit the words on the slide itself, use the Word copy."]}
