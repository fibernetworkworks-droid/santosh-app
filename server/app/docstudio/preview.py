"""v0.189.0 docstudio.preview - the deep preview pass (the skill's "render, measure, then deliver").

Before a studio file reaches the chat, the engine looks at its OWN output:
  - pdf   : page images (pypdfium2, first 3 pages) + page count + the QA report
  - xlsx  : per-sheet structure (headers, dims, totals row) + formula/chart counts
  - docx  : heading outline + table count
  - pptx  : slide titles + bullet counts
Anything unreadable is said plainly (no silent pass), and the images ride back as small PNGs the
caller can attach to the file card.
"""
from __future__ import annotations

import io
from typing import Any

from . import tokens

MAX_PREVIEW_PAGES = 3
THUMB_SCALE = 1.6   # ~115 dpi on A4 - readable, small enough for chat


def pdf_pages(data: bytes, limit: int = MAX_PREVIEW_PAGES) -> list[bytes]:
    """First N pages of a PDF as PNGs (pypdfium2, the v0.43 dependency)."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(io.BytesIO(data))
        out = []
        for i, page in enumerate(doc):
            if i >= limit:
                break
            bitmap = page.render(scale=THUMB_SCALE)
            pil = bitmap.to_pil()
            pil.thumbnail((900, 1273))
            b = io.BytesIO()
            pil.save(b, format="PNG", optimize=True)
            out.append(b.getvalue())
            page.close()
        doc.close()
        return out
    except Exception:
        return []


def preview(kind: str, data: bytes, build_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Deep preview of a freshly built (or owner-supplied) file. Never raises."""
    kind = (kind or "").lower().lstrip(".")
    out: dict[str, Any] = {"kind": kind, "preview": True}
    build_info = build_info or {}
    try:
        if kind == "pdf":
            out["pages"] = build_info.get("pages") or _pdf_pages(data)
        elif kind == "xlsx":
            out.update(_xlsx_view(data))
        elif kind in ("docx", "doc"):
            out.update(_docx_view(data))
        elif kind in ("pptx", "ppt"):
            out.update(_pptx_view(data))
        else:
            out["note"] = "is file ka deep preview abhi nahi hai"
    except Exception as e:
        out["warning"] = f"preview adhoora raha: {type(e).__name__}"
    qa = build_info.get("qa")
    if qa:
        out["qa"] = qa
    out["size_kb"] = round(len(data) / 1024, 1)
    return out


def _pdf_pages(data: bytes) -> int:
    from pypdf import PdfReader
    return len(PdfReader(io.BytesIO(data)).pages)


def _xlsx_view(data: bytes) -> dict[str, Any]:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), data_only=False)
    sheets = []
    cf_count = dv_count = 0
    for name in wb.sheetnames[:20]:
        ws = wb[name]
        headers = []
        for row in ws.iter_rows(min_row=4, max_row=4, min_col=2, max_col=min(ws.max_column, 14)):
            headers = [str(c.value) if c.value is not None else "" for c in row]
            break
        try:
            cf_count += sum(len(rules) for rules in ws.conditional_formatting._cf_rules.values())
        except Exception:
            pass
        try:
            dv_count += len(ws.data_validations.dataValidation)
        except Exception:
            pass
        sheets.append({"name": name, "rows": max(0, ws.max_row - 4),
                       "cols": max(0, ws.max_column - 1),
                       "headers": headers})
    view: dict[str, Any] = {"sheets": sheets}
    try:
        view["defined_names"] = sorted(list(wb.defined_names))[:20]
    except Exception:
        pass
    if cf_count:
        view["conditional_formats"] = cf_count
    if dv_count:
        view["validations"] = dv_count
    return view


def _docx_view(data: bytes) -> dict[str, Any]:
    from docx import Document
    d = Document(io.BytesIO(data))
    outline = []
    for p in d.paragraphs:
        s = (p.style.name or "")
        if s.startswith("Heading") and p.text.strip():
            outline.append({"level": s.replace("Heading ", "") or "?", "text": p.text.strip()[:90]})
        if len(outline) >= 30:
            break
    return {"outline": outline, "tables": len(d.tables), "paragraphs": len(d.paragraphs)}


def _pptx_view(data: bytes) -> dict[str, Any]:
    from pptx import Presentation
    p = Presentation(io.BytesIO(data))
    slides = []
    for i, s in enumerate(p.slides, start=1):
        title = ""
        for shp in s.shapes:
            if shp.has_text_frame and shp.text_frame.text.strip():
                title = shp.text_frame.text.strip().splitlines()[0][:90]
                break
        slides.append({"n": i, "title": title})
    return {"slide_count": len(slides), "slides": slides[:40]}
