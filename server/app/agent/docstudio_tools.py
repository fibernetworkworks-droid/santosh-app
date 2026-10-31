"""v0.192.0 Document Studio tools: doc_studio (Claude-grade PDF / Word / Excel / PowerPoint with the
cascade-palette design system, cover, TOC, live formulas, QA + deep preview) and doc_preview (look
inside any owner file - pages, outline, sheets - before answering). Delivery rides the v0.51 file-card
path (store_bytes -> public_file -> pc_file event), so file_id works for email / hoola_send exactly as before.
make_document stays for quick plain files; the studio is for anything formal.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..docstudio import docxgen, htmlpdf, pdfgen, pptxgen, preview, xlsxgen
from .make_tools import _deliver, _owner_bytes, _safe  # the v0.51 delivery path, reused
from .tools import Ctx, ToolError

DOCSTUDIO_TOOLS = [
    {"name": "doc_studio",
     "description": (
         "Make a PERFECT PDF / Word / Excel / PowerPoint file. PDFs are designed per topic like Claude's own "
         "(cover, contents with real page numbers, stat rows, callouts, money right-aligned, page review before "
         "delivery). For reports, plans, quotations, invoices, proposals, decks - anything formal. Content format "
         "in your prompt notes."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["pdf", "docx", "xlsx", "pptx"],
                  "description": "file type to build"},
         "title": {"type": "string", "description": "document title (drives the palette)"},
         "text": {"type": "string", "description": "content: '# ' h1, '## ' h2, '- ' bullets, '1. ' steps, "
                  "'| a | b |' table rows (a 'Total' row is bolded), '> ' quote, '> [!KEY|NOTE|TIP|WARNING|"
                  "SUCCESS|HUMAN|GATE] text' box, '[stat: 12% | label]' key number, '[chart: bar|hbar|line|donut | "
                  "title]' above a table, 'Table: caption' / 'Source: ...', footnotes '[^1]' + '[^1]: text', ``` code"},
         "sheets": {"type": "object", "description": "xlsx: {'Sheet': [[header...], [row...]]} - up to "
                   "16,384 cols/sheet (wider auto-splits to -P1/-P2 + Index), 100K rows; a sheet may "
                   "be a dict {rows, conditional_formatting, validation, merges, defined_names}"},
         "slides": {"type": "array", "description": "pptx: [{title, bullets[], notes}]"},
         "charts": {"type": "array", "description": "xlsx charts: [{sheet, type: bar|column|line|pie|scatter|"
                    "area|doughnut|radar|combo, categories: 'B4:B12', values: 'C4:C12', line_values (combo), title}]"},
         "style": {"type": "string", "enum": ["auto", "professional", "boardroom", "warm",
                   "elegant", "forest", "finance", "technology", "education", "health", "legal",
                   "marketing", "people", "agriculture", "government", "travel", "festive"],
                   "description": "design (auto = matched to the topic: cover, fonts, palette; "
                   "or force a look)"},
         "subject": {"type": "string", "description": "one-line subtitle / purpose"},
         "author": {"type": "string", "description": "pdf: who prepared it - her business / name when known "
                    "(default Hoola)"},
         "prepared_for": {"type": "string", "description": "pdf: the client / reader it is for, when known"},
         "filename": {"type": "string", "description": "output file name"},
         "cover": {"type": "boolean", "description": "cover page (auto by size)"},
         "toc": {"type": "boolean", "description": "table of contents (auto when 4+ sections)"},
         "data": {"type": "string", "description": "v0.238 a dataset id from data_fetch: the rows are laid out BY CODE "
                  "(ranking table + one card per row with its data_note text) - no need to write them yourself; "
                  "'[[data]]' in text marks where they go (else at the end)"},
         "data_fields": {"type": "array", "items": {"type": "string"},
                         "description": "columns to show (default: the first 6); the first is each card's title"},
         "data_layout": {"type": "string", "enum": ["both", "table", "cards"], "description": "default both"},
         "data_heading": {"type": "string", "description": "heading above the data part"},
         "part": {"type": "string", "enum": ["build", "add"],
                  "description": "add = keep this text for later (long documents written over several calls, same "
                  "title); build (default) = the saved parts + this text become the file"}},
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


def _draft_path(ctx: Ctx, title: str) -> Path:
    import hashlib
    import re as _re
    from ..datasets import _root
    d = _root(ctx.tenant_id) / "_drafts"
    d.mkdir(parents=True, exist_ok=True)
    slug = _re.sub(r"[^a-z0-9]+", "-", str(title or "doc").lower())[:40].strip("-") or "doc"
    key = hashlib.sha256(f"{ctx.conversation_id}|{slug}".encode()).hexdigest()[:12]
    return d / f"{slug}-{key}.md"


def _cell(v: Any) -> str:
    if isinstance(v, list):
        v = ", ".join(map(str, v[:8]))
    return str("" if v is None else v).replace("|", "/").replace("\n", " ").strip()


def data_markdown(doc: dict, fields: list[str] | None = None, layout: str = "both", heading: str = "") -> str:
    """v0.238 rows of a dataset laid out by code: a ranking table + one card per row (its 'note' column = the text
    Hoola wrote for it with data_note). Any length - the model never has to fit 100 entries in one reply."""
    rows = list(doc.get("rows") or [])
    cols = [c for c in (fields or []) if c in (doc.get("columns") or [])] or \
        [c for c in (doc.get("columns") or []) if c != "note"][:6]
    out: list[str] = []
    if heading:
        out.append(f"# {heading}")
    if layout in ("both", "table") and rows:
        tcols = cols[:5]
        out.append("| # | " + " | ".join(tcols) + " |")
        for i, r in enumerate(rows, 1):
            out.append(f"| {i} | " + " | ".join(_cell(r.get(c))[:80] for c in tcols) + " |")
        out.append("")
    if layout in ("both", "cards"):
        for i, r in enumerate(rows, 1):
            out.append(f"### {i}. {_cell(r.get(cols[0])) if cols else i}")
            for c in cols[1:]:
                val = _cell(r.get(c))
                if val:
                    out.append(f"- **{c}:** {val[:400]}")
            note = _cell(r.get("note"))
            if note:
                out.append(note)
            out.append("")
    src = doc.get("source")
    if src:
        import time as _t
        out.append(f"> Data: {src} - liya gaya {_t.strftime('%d %b %Y', _t.localtime(doc.get('saved_at') or 0))}.")
    return "\n".join(out)


async def doc_studio(ctx: Ctx, kind, title, text="", sheets=None, slides=None, charts=None,
                     filename="", style="auto", cover="auto", toc="auto", subject="", data="",
                     data_fields=None, data_layout="both", data_heading="", part="build", author="",
                     prepared_for="", **_):
    kind = str(kind or "").lower().strip()
    if kind not in ("pdf", "docx", "xlsx", "pptx"):
        raise ToolError("kind: pdf | docx | xlsx | pptx")
    # v0.238 long documents over several calls: 'add' keeps this part on the server, 'build' joins every part
    dp = _draft_path(ctx, str(title))
    if str(part or "build") == "add":
        old = dp.read_text() if dp.exists() else ""
        dp.write_text((old + "\n\n" + str(text or "")).strip())
        return {"part": "saved", "draft_chars": len(dp.read_text()),
                "note": "Part saved. Keep adding with part=add (same title); finish with part=build."}
    if dp.exists() and kind in ("pdf", "docx"):
        text = (dp.read_text() + "\n\n" + str(text or "")).strip()
    if data:
        from .. import datasets as D
        try:
            dsd = await asyncio.to_thread(D.load, ctx.tenant_id, str(data))
        except D.DataError as e:
            raise ToolError(str(e))
        if kind == "xlsx":
            cols = [c for c in (data_fields or []) if c in dsd["columns"]] or dsd["columns"]
            sheets = dict(sheets or {})
            sheets.setdefault((str(data_heading) or "Data")[:31], [cols] + [[_cell(r.get(c)) for c in cols]
                                                                            for r in dsd["rows"]])
        elif kind in ("pdf", "docx"):
            md = data_markdown(dsd, data_fields, str(data_layout or "both"), str(data_heading or ""))
            text = str(text or "")
            text = text.replace("[[data]]", md) if "[[data]]" in text else (text + "\n\n" + md).strip()
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
            res = await asyncio.to_thread(make_pdf, str(title), str(text or ""), kw, str(author or ""),
                                          str(prepared_for or ""))
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
    if dp.exists():
        dp.unlink(missing_ok=True)       # v0.238 the parts are now in the file
    view = await asyncio.to_thread(_deliver, ctx, _safe(str(filename or title), "." + kind), data, "docstudio")
    prev = await asyncio.to_thread(preview.preview, kind, data, res)
    prev.pop("images", None)
    qa = prev.get("qa") or {}
    notes = ["The file card is in chat; file_id email / hoola_send ke liye ready hai."]
    if qa.get("status") == "warn":
        notes.append(f"QA ne kaha: {qa.get('issues')}")
    if kind == "pdf" and res.get("design"):
        d = res["design"]
        notes.append(f"Design matched to the topic: {d['label']} ({d['cover']} cover, "
                     f"{d['fonts']['head']} headings).")
        rv = (qa.get("review") or {}) if isinstance(qa, dict) else {}
        if rv.get("score"):
            notes.append(f"Page review {rv['score']}/10" + (f", changed {list(rv['changed'])}" if rv.get("changed") else "") + ".")
    if kind == "xlsx" and res.get("formulas"):
        notes.append(f"{res['formulas']} live formulas.")
    if kind == "xlsx" and res.get("splits"):
        sp = res["splits"][0]
        notes.append(f"{sp['cols']:,} cols Excel ki ek-sheet limit (16,384) se bade the - "
                     f"{len(sp['parts'])} parts + Index bane.")
    return view | {"made": kind, "style": res.get("style"), "design": res.get("design"),
                   "preview": prev, "note": " ".join(notes)}


def make_pdf(title: str, text: str, kw: dict[str, Any], author: str = "", prepared_for: str = "") -> dict[str, Any]:
    """v0.313 HOOLA PRINT: designed HTML printed by Chromium (docstudio/htmlpdf.py), the Claude way. Chromium missing,
    DOC_ENGINE=reportlab, or any print failure -> the v0.192 ReportLab Document Studio, so a PDF always comes back."""
    from ..config import get_settings
    if (getattr(get_settings(), "doc_engine", "chromium") or "chromium") == "chromium" and htmlpdf.available():
        try:
            return htmlpdf.make_pdf(title, text, author=author or "Hoola", prepared_for=prepared_for, **kw)
        except Exception as e:     # noqa: BLE001 - the file must still reach her
            htmlpdf.STATS["fallback"] += 1
            htmlpdf.log.warning("Hoola Print failed, ReportLab instead: %s", e)
    return pdfgen.make_pdf(title, text, author=author or "Hoola", **kw)


async def doc_preview(ctx: Ctx, file_id, **_):
    name, data = await asyncio.to_thread(_owner_bytes, ctx, str(file_id))
    kind = Path(name).suffix.lower().lstrip(".")
    kind = {"doc": "docx", "ppt": "pptx", "xls": "xlsx", "hwp": ""}.get(kind, kind)
    info = await asyncio.to_thread(preview.preview, kind, data, {})
    return info | {"name": str(name)[:120]}


DOCSTUDIO_HANDLERS = {"doc_studio": doc_studio, "doc_preview": doc_preview}
