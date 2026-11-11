"""D7 HOOLA DOCUMENTS - the desk behind /console/documents and the phone's Documents screen (docs/DOCUMENT_KIT_PLAN.md D7).

The SAME pdf_kit tool the chat uses, run as the owner: her files are uploaded once (the chat's own file store, the same
checks), every tool is one card in a grid with its few options, and the result comes back with a download link. Nothing
here does PDF work itself - every action goes through `pdf_kit`, so the page and the chat can never disagree.
Results also land in her 'Hoola updates' chat (like every file card), kept for the usual file life."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from . import flows, health

# ---------------------------------------------------------------------------------------------- the grid
# input: pdf (one PDF) | pdfs (2+ in order) | two (old, new) | files (pictures / Office) | any (PDF or pictures) | url
# opts: [key, label, kind, default, choices]   kind = text | number | select | bool | pages
O_PAGES = ["pages", "Pages (e.g. 1-3,5 or odd)", "pages", "", None]
TOOLS: list[dict[str, Any]] = [
    {"group": "Organize", "items": [
        {"id": "merge", "title": "Merge PDF", "line": "Join PDFs and photos in the order you want", "input": "pdfs",
         "opts": [["bookmarks", "A bookmark for each file", "bool", False, None]]},
        {"id": "split", "title": "Split PDF", "line": "Page ranges, every N pages, each page, or by size", "input": "pdf",
         "opts": [["mode", "How", "select", "each", ["each", "ranges", "every", "pages", "size", "bookmarks", "blank"]],
                  ["ranges", "Ranges (1-3, 4-10)", "text", "", None], ["every", "Every N pages", "number", 2, None],
                  ["max_kb", "Each part under (KB)", "number", 2000, None]]},
        {"id": "remove", "title": "Remove pages", "line": "Take pages out", "input": "pdf", "opts": [O_PAGES]},
        {"id": "extract", "title": "Extract pages", "line": "Keep only the pages you pick, in your order",
         "input": "pdf", "opts": [O_PAGES]},
        {"id": "organize", "title": "Organize pages", "line": "Reorder, repeat or add blank pages", "input": "pdf",
         "opts": [["order", "New order (3,1,2,blank,4-)", "text", "", None]]},
        {"id": "rotate", "title": "Rotate", "line": "Turn pages the right way up", "input": "pdf",
         "opts": [["degrees", "Turn by", "select", "90", ["90", "180", "270"]], O_PAGES]},
        {"id": "reverse", "title": "Reverse order", "line": "Last page first", "input": "pdf", "opts": []},
        {"id": "interleave", "title": "Two-sided scan", "line": "Fronts + backs from a one-sided scanner",
         "input": "pdfs", "opts": [["back_reversed", "Backs are in reverse", "bool", True, None]]},
    ]},
    {"group": "Make smaller / fix", "items": [
        {"id": "compress", "title": "Compress PDF", "line": "Smaller file, or under the size a portal asks",
         "input": "pdf", "opts": [["level", "How much", "select", "recommended", ["less", "recommended", "extreme"]],
                                  ["target_kb", "Or under (KB)", "number", "", None]]},
        {"id": "repair", "title": "Repair PDF", "line": "A damaged or half-downloaded PDF", "input": "pdf", "opts": []},
        {"id": "ocr", "title": "Make searchable (OCR)", "line": "Scanned pages get words you can search and copy",
         "input": "pdf", "opts": [["language", "Language (e.g. hindi, english)", "text", "", None]]},
    ]},
    {"group": "To PDF", "items": [
        {"id": "to_pdf", "title": "Photos / Word / Excel to PDF", "line": "Pictures in one PDF; Office files each to PDF",
         "input": "files", "opts": [["page_size", "Page", "select", "fit", ["fit", "a4", "letter", "legal", "a5"]],
                                    ["margin", "Margin", "select", "none", ["none", "small", "big"]]]},
        {"id": "web_to_pdf", "title": "Web page to PDF", "line": "A public web page printed as a PDF", "input": "url",
         "opts": [["url", "Link (https://...)", "text", "", None]]},
    ]},
    {"group": "From PDF", "items": [
        {"id": "to_images", "title": "PDF to JPG", "line": "Each page as a picture", "input": "pdf",
         "opts": [["format", "Format", "select", "jpg", ["jpg", "png"]], ["dpi", "Sharpness (dpi)", "number", 150, None]]},
        {"id": "to_word", "title": "PDF to Word", "line": "An editable Word file", "input": "pdf", "opts": [O_PAGES]},
        {"id": "to_excel", "title": "PDF to Excel", "line": "The tables, with numbers as numbers", "input": "pdf",
         "opts": [O_PAGES]},
        {"id": "to_powerpoint", "title": "PDF to PowerPoint", "line": "One slide per page", "input": "pdf", "opts": []},
        {"id": "to_text", "title": "PDF to text", "line": "The words, as text or markdown", "input": "pdf",
         "opts": [["format", "Format", "select", "txt", ["txt", "md"]]]},
        {"id": "extract_images", "title": "Pictures inside", "line": "Take out the photos inside the PDF",
         "input": "pdf", "opts": []},
        {"id": "pdfa", "title": "PDF/A (archive)", "line": "For long-term keeping and court filings", "input": "pdf",
         "opts": [["level", "Level", "select", "2b", ["1b", "2b", "3b"]]]},
    ]},
    {"group": "Edit", "items": [
        {"id": "page_numbers", "title": "Page numbers", "line": "Numbers, Hindi digits or Bates", "input": "pdf",
         "opts": [["position", "Where", "select", "bottom-center",
                   ["bottom-center", "bottom-right", "bottom-left", "top-center", "top-right", "top-left"]],
                  ["text", "Style", "select", "{n}", ["{n}", "Page {n}", "Page {n} of {p}", "{n} / {p}"]],
                  ["digits", "Digits", "select", "latin", ["latin", "devanagari"]],
                  ["skip_first", "Not on the first page", "bool", False, None]]},
        {"id": "watermark", "title": "Watermark", "line": "A word like CONFIDENTIAL across the pages", "input": "pdf",
         "opts": [["text", "Text", "text", "CONFIDENTIAL", None], ["opacity", "Opacity (0-1)", "number", 0.25, None]]},
        {"id": "header_footer", "title": "Header / footer", "line": "A line at the top or bottom of every page",
         "input": "pdf", "opts": [["header", "Header", "text", "", None], ["footer", "Footer", "text", "", None]]},
        {"id": "crop", "title": "Crop", "line": "Trim the white edges, or by a margin", "input": "pdf",
         "opts": [["auto", "Trim white edges", "bool", True, None], ["top", "Or cut from the top (mm)", "number", "", None],
                  ["bottom", "Bottom (mm)", "number", "", None], ["left", "Left (mm)", "number", "", None],
                  ["right", "Right (mm)", "number", "", None]]},
        {"id": "highlight", "title": "Highlight a word", "line": "Mark a word everywhere it appears", "input": "pdf",
         "opts": [["text", "Word or phrase", "text", "", None]]},
        {"id": "nup", "title": "Pages per sheet", "line": "2 or 4 pages on one sheet", "input": "pdf",
         "opts": [["per_sheet", "Pages per sheet", "select", "2", ["2", "4", "6", "8", "9", "16"]]]},
        {"id": "booklet", "title": "Booklet", "line": "Print, fold and staple", "input": "pdf", "opts": []},
        {"id": "fit", "title": "Fit to A4", "line": "Every page to one paper size", "input": "pdf",
         "opts": [["sheet", "Paper", "select", "a4", ["a4", "letter", "legal", "a5"]]]},
        {"id": "grayscale", "title": "Black & white", "line": "Grey pages for cheaper printing", "input": "pdf",
         "opts": []},
        {"id": "flatten", "title": "Flatten", "line": "Forms and notes become part of the page", "input": "pdf",
         "opts": []},
        {"id": "sanitize", "title": "Remove hidden data", "line": "Scripts, attachments and author details out",
         "input": "pdf", "opts": []},
    ]},
    {"group": "Security", "items": [
        {"id": "protect", "title": "Lock with a password", "line": "Hoola makes a strong password, shown once",
         "input": "pdf", "opts": []},
        {"id": "unlock", "title": "Unlock", "line": "Remove restrictions; an open password is typed on its own page",
         "input": "pdf", "opts": []},
        {"id": "redact", "title": "Redact", "line": "Aadhaar, PAN, card, phone... removed for good (preview first)",
         "input": "pdf", "opts": [["find", "Also these words", "text", "", None]]},
    ]},
    {"group": "Sign & forms", "items": [
        {"id": "form_fields", "title": "See the form boxes", "line": "The fillable boxes in a form", "input": "pdf",
         "opts": []},
        {"id": "sign", "title": "Sign", "line": "Your saved signature, and / or a digital seal", "input": "pdf",
         "opts": [["mode", "How", "select", "place", ["place", "digital", "both"]],
                  ["name", "Name under it", "text", "", None]]},
        {"id": "sign_verify", "title": "Check signatures", "line": "Is a signed PDF unchanged since signing?",
         "input": "pdf", "opts": []},
    ]},
    {"group": "With AI", "items": [
        {"id": "compare", "title": "Compare two versions", "line": "What changed - money and dates first",
         "input": "two", "opts": []},
        {"id": "summarize", "title": "Summarize", "line": "The main points, each with its page", "input": "pdf",
         "opts": [["length", "Length", "select", "medium", ["short", "medium", "long"]],
                  ["language", "In language", "text", "", None]]},
        {"id": "ask", "title": "Ask the PDF", "line": "Answers only from the document, with pages", "input": "pdf",
         "opts": [["question", "Your question", "text", "", None]]},
        {"id": "translate", "title": "Translate", "line": "Keeping the layout", "input": "pdf",
         "opts": [["to", "To language", "text", "hindi", None], ["keep_layout", "Keep the layout", "bool", True, None]]},
        {"id": "smart_split", "title": "Split a bundle", "line": "AI finds where each document starts (a plan first)",
         "input": "pdf", "opts": []},
    ]},
]
TOOL_IDS = {t["id"] for g in TOOLS for t in g["items"]}
RUNNABLE = TOOL_IDS | {"flow", "info", "redact_apply", "signature_save", "flow_save", "flow_delete", "flow_list"}
INTS = {"every", "max_kb", "target_kb", "dpi", "per_sheet", "degrees"}
FLOATS = {"opacity", "top", "bottom", "left", "right"}


class DeskError(Exception):
    pass


def catalogue() -> dict[str, Any]:
    return {"groups": TOOLS, "engines": health.ready(), "steps": list(flows.STEPS), "first": list(flows.FIRST),
            "last": list(flows.LAST), "max_steps": flows.MAX_STEPS}


def clean_args(args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (args or {}).items():
        if v is None or v == "" or v == [] or k == "action":
            continue
        if k in INTS and isinstance(v, str):
            try:
                v = int(float(v))
            except ValueError:
                raise DeskError(f"'{k}' must be a number.")
        if k in FLOATS and isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise DeskError(f"'{k}' must be a number.")
        if k == "ranges" and isinstance(v, str):
            v = [x.strip() for x in v.split(",") if x.strip()]
        if k == "find" and isinstance(v, str):
            v = [x.strip() for x in v.split(",") if x.strip()]
        out[k] = v
    return out


def _links(obj: Any) -> Any:
    """Every made file gets its signed download link (the same link a chat card opens)."""
    from ..pc.service import download_path
    if isinstance(obj, dict):
        out = {k: _links(v) for k, v in obj.items()}
        fid = obj.get("file_id")
        if isinstance(fid, str) and fid.startswith("file_") and not obj.get("url"):
            out["url"] = download_path(fid)
        pv = obj.get("preview_file_id")
        if isinstance(pv, str) and pv.startswith("file_"):
            out["preview_url"] = download_path(pv)
        return out
    if isinstance(obj, list):
        return [_links(x) for x in obj]
    return obj


async def run(tenant: str, action: str, args: dict[str, Any]) -> dict[str, Any]:
    action = str(action or "").strip().lower()
    if action not in RUNNABLE:
        raise DeskError(f"'{action}' is not a Documents tool.")
    clean = clean_args(args)
    clean["action"] = action
    from .. import convs
    from ..agent.tools import Ctx, ToolError, dispatch
    try:
        conv = convs.notice_chat(tenant)
    except Exception:   # noqa: BLE001 - the file still reaches her through the link
        conv = ""
    ctx = Ctx(tenant_id=tenant, conversation_id=conv, actor="owner")
    try:
        out = await asyncio.wait_for(dispatch("pdf_kit", clean, ctx), timeout=600)
    except ToolError as e:
        raise DeskError(str(e))
    except asyncio.TimeoutError:
        raise DeskError("This took too long. Try fewer pages or a smaller file.")
    from ..scrub import scrub
    return {"ok": True, "action": action, "result": _links(scrub(out)), "conversation_id": conv}


def make_router(require_key, current_tenant):
    r = APIRouter()

    def on():
        from ..config import get_settings
        if not getattr(get_settings(), "documents_page", True):
            raise HTTPException(404, "Documents is switched off.")

    @r.get("/api/dockit/tools", dependencies=[Depends(require_key)])
    def tools(tenant: str = Depends(current_tenant)):
        on()
        return catalogue()

    @r.post("/api/dockit/upload", dependencies=[Depends(require_key)])
    async def upload(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        on()
        from .. import chatfiles
        data = await file.read(chatfiles.MAX_BYTES + 1)
        try:
            row = await asyncio.to_thread(chatfiles.store, tenant, file.filename or "file", data, file.content_type or "")
        except chatfiles.FileError as e:
            raise HTTPException(413 if len(data) > chatfiles.MAX_BYTES else 400, str(e))
        return {k: row.get(k) for k in ("file_id", "name", "size", "url", "media", "mime", "real_type", "pages")
                if row.get(k) is not None}

    @r.post("/api/dockit/run", dependencies=[Depends(require_key)])
    async def run_one(body: dict, tenant: str = Depends(current_tenant)):
        on()
        try:
            return await run(tenant, str(body.get("action") or ""), dict(body.get("args") or {}))
        except DeskError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/dockit/flows", dependencies=[Depends(require_key)])
    def flow_list(tenant: str = Depends(current_tenant)):
        on()
        return flows.listing(tenant)

    @r.post("/api/dockit/flows", dependencies=[Depends(require_key)])
    def flow_save(body: dict, tenant: str = Depends(current_tenant)):
        on()
        from .core import DocError
        try:
            return flows.save(tenant, str(body.get("name") or ""), body.get("steps"))
        except DocError as e:
            raise HTTPException(400, str(e))

    @r.delete("/api/dockit/flows/{name}", dependencies=[Depends(require_key)])
    def flow_delete(name: str, tenant: str = Depends(current_tenant)):
        on()
        from .core import DocError
        try:
            return flows.delete(tenant, name)
        except DocError as e:
            raise HTTPException(404, str(e))

    return r
