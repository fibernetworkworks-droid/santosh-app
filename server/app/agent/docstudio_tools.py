"""v0.189.0 Document Studio tools: doc_studio (Claude-grade PDF / Word / Excel / PowerPoint with the
cascade-palette design system, cover, TOC, live formulas, QA + deep preview) and doc_preview (look
inside any owner file - pages, outline, sheets - before answering). Delivery rides the v0.51 file-card
path (store_bytes -> public_file -> pc_file event), so file_id works for email / hoola_send exactly as before.
make_document stays for quick plain files; the studio is for anything formal.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..docstudio import docxgen, pdfgen, pptxgen, preview, xlsxgen
from .make_tools import _deliver, _owner_bytes, _safe  # the v0.51 delivery path, reused
from .tools import Ctx, ToolError

DOCSTUDIO_TOOLS = [
    {"name": "doc_studio",
     "description": (
         "Make a PERFECT PDF / Word / Excel / PowerPoint file: real design system (palette from the "
         "title, cover, clickable TOC, styled tables, live formulas), QA + deep preview before delivery. "
         "For reports, quotations, invoices, proposals, decks - anything formal. Same content format as "
         "make_document; details in your prompt notes."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["pdf", "docx", "xlsx", "pptx"],
                  "description": "file type to build"},
         "title": {"type": "string", "description": "document title (drives the palette)"},
         "text": {"type": "string", "description": "content: '# ' h1, '## ' h2, '- ' bullets, "
                  "'| a | b |' table rows, '> ' quote, '[stat: 12% | label]' callout"},
         "sheets": {"type": "object", "description": "xlsx: {'Sheet': [[header...], [row...]]}"},
         "slides": {"type": "array", "description": "pptx: [{title, bullets[], notes}]"},
         "charts": {"type": "array", "description": "xlsx charts: [{sheet, type: bar|line|pie, "
                    "categories: 'B4:B12', values: 'C4:C12', title}]"},
         "style": {"type": "string", "enum": ["auto", "professional", "boardroom", "warm",
                   "elegant", "forest"], "description": "palette (auto = from the title)"},
         "subject": {"type": "string", "description": "one-line subtitle / purpose"},
         "filename": {"type": "string", "description": "output file name"},
         "cover": {"type": "boolean", "description": "cover page (auto by size)"},
         "toc": {"type": "boolean", "description": "table of contents (auto when 4+ sections)"}},
         "required": ["kind", "title"]}},
    {"name": "doc_preview",
     "description": (
         "Deep-preview one of the owner's files (file_id): PDF pages, Word outline, Excel sheets, "
         "deck slides - the structure before you answer about it."),
     "input_schema": {"type": "object", "properties": {
         "file_id": {"type": "string", "description": "the owner's file"}},
         "required": ["file_id"]}},
]
DOCSTUDIO_LABELS = {"doc_studio": "Design ke saath file bana raha hoon",
                    "doc_preview": "File andar se dekh raha hoon"}


async def doc_studio(ctx: Ctx, kind, title, text="", sheets=None, slides=None, charts=None,
                     filename="", style="auto", cover="auto", toc="auto", subject="", **_):
    kind = str(kind or "").lower().strip()
    if kind not in ("pdf", "docx", "xlsx", "pptx"):
        raise ToolError("kind: pdf | docx | xlsx | pptx")
    from ..pii import describe, find
    blob = f"{title}\n{text}\n{sheets}\n{slides}\n{charts}"
    bad = [k for k in find(blob) if k in ("otp_pin", "password", "cvv")]
    if bad:
        raise ToolError(f"Isme {describe(bad)} hai; Hoola aisi file nahi banata.")
    if kind in ("xlsx", "pptx") and not (sheets or slides):
        raise ToolError("xlsx ko sheets chahiye ({'Sheet': [[...]]}), pptx ko slides ([{title, bullets}]).")
    kw: dict[str, Any] = {"style": str(style or "auto"), "subject": str(subject or "")}
    if kind != "xlsx":
        kw["cover"] = cover if isinstance(cover, bool) else str(cover or "auto")
    if kind in ("pdf", "docx"):
        kw["toc"] = toc if isinstance(toc, bool) else str(toc or "auto")
    try:
        if kind == "pdf":
            res = await asyncio.to_thread(pdfgen.make_pdf, str(title), str(text or ""), **kw)
        elif kind == "docx":
            res = await asyncio.to_thread(docxgen.make_docx, str(title), str(text or ""), **kw)
        elif kind == "xlsx":
            res = await asyncio.to_thread(xlsxgen.make_xlsx, str(title), sheets or {},
                                          charts=[c for c in (charts or []) if isinstance(c, dict)],
                                          style=str(style or "auto"))
        else:
            res = await asyncio.to_thread(pptxgen.make_pptx, str(title),
                                          [s for s in (slides or []) if isinstance(s, dict)], **kw)
    except (ValueError, TypeError) as e:
        raise ToolError(str(e))
    data = res.pop("data", b"")
    view = await asyncio.to_thread(_deliver, ctx, _safe(str(filename or title), "." + kind), data, "docstudio")
    prev = await asyncio.to_thread(preview.preview, kind, data, res)
    prev.pop("images", None)
    qa = prev.get("qa") or {}
    notes = ["The file card is in chat; file_id email / hoola_send ke liye ready hai."]
    if qa.get("status") == "warn":
        notes.append(f"QA ne kaha: {qa.get('issues')}")
    if kind == "xlsx" and res.get("formulas"):
        notes.append(f"{res['formulas']} live formulas.")
    return view | {"made": kind, "style": res.get("style"), "preview": prev,
                   "note": " ".join(notes)}


async def doc_preview(ctx: Ctx, file_id, **_):
    name, data = await asyncio.to_thread(_owner_bytes, ctx, str(file_id))
    kind = Path(name).suffix.lower().lstrip(".")
    kind = {"doc": "docx", "ppt": "pptx", "xls": "xlsx", "hwp": ""}.get(kind, kind)
    info = await asyncio.to_thread(preview.preview, kind, data, {})
    return info | {"name": str(name)[:120]}


DOCSTUDIO_HANDLERS = {"doc_studio": doc_studio, "doc_preview": doc_preview}
