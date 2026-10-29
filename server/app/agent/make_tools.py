"""v0.51 Making things for the owner: real Word / Excel / PowerPoint files, clean product photos, passport / form
photos, and meaning-based memory recall. Files land as the owner's files (file_id works for email and Hoola Network)."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from ..events import bus
from .tools import Ctx, ToolError

MAKE_TOOLS = [
    {"name": "make_document", "description": (
        "Make a real Office file the owner can open, print, email or send: kind docx (letter, quotation, report, notice; "
        "text with '# heading', '- bullets', '1. steps', '| a | b |' table rows, **bold**), xlsx (price list, attendance, "
        "budget, bill register; sheets = {\"Sheet name\": [[\"Header\",...],[row...]]}, cells starting with '=' are "
        "formulas like =SUM(B2:B9)), pptx (deck; slides = [{title, bullets[], notes}]). Write the full real content "
        "yourself. Returns file_id (attach to email / hoola_send kind=file)."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["docx", "xlsx", "pptx"]}, "title": {"type": "string"},
         "text": {"type": "string"}, "sheets": {"type": "object"},
         "slides": {"type": "array", "items": {"type": "object"}}, "filename": {"type": "string"}},
         "required": ["kind", "title"]}},
    {"name": "photo_clean", "description": (
        "Cut the subject out of a photo the owner attached (file_id) and put it on a plain background (white by default; "
        "or blue, grey, any hex) - for shop / saree / product photos and catalog pictures. Returns the new photo."),
     "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "color": {"type": "string"}},
                      "required": ["file_id"]}},
    {"name": "id_photo", "description": (
        "Passport / visa / exam-form photo from the owner's selfie (file_id): face-aware crop to the right size, plain "
        "background, plus a 4x6 print sheet. size: india_passport (35x45 mm, default), us_visa (2x2 in), schengen_visa, "
        "pan_card, exam_form, stamp; color: white (default), blue, light_blue, red."),
     "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "size": {"type": "string"},
                                                       "color": {"type": "string"}}, "required": ["file_id"]}},
    {"name": "memory_search", "description": (
        "Search EVERYTHING the owner asked you to remember by meaning (Hinglish ok), not just the recent facts in your "
        "prompt: 'beti ke school wali baat', 'gaadi ka insurance kab'."),
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]
MAKE_LABELS = {"make_document": "File bana raha hoon", "photo_clean": "Photo saaf kar raha hoon",
               "id_photo": "Passport photo bana raha hoon", "memory_search": "Yaad kar raha hoon"}


def _safe(name: str, ext: str) -> str:
    n = re.sub(r"[^\w\- ()]+", "_", name or "Hoola").strip()[:60] or "Hoola"
    return n if n.lower().endswith(ext) else n + ext


def _deliver(ctx: Ctx, name: str, data: bytes, source: str) -> dict[str, Any]:
    from ..mailbox import service as ms
    from ..pc.service import public_file
    row = ms.store_bytes(ctx.tenant_id, name, data, "to_phone")
    view = public_file(row)
    view.pop("pc_path", None)
    bus.publish(ctx.conversation_id, "pc_file", {**view, "source": source})
    return view


def _owner_bytes(ctx: Ctx, file_id: str) -> tuple[str, bytes]:
    from ..mailbox import service as ms
    try:
        f = ms._file_row(ctx.tenant_id, str(file_id))
    except Exception as e:
        raise ToolError(str(e))
    return f.name, Path(f.stored_path).read_bytes()


async def make_document(ctx: Ctx, kind, title, text="", sheets=None, slides=None, filename="", **_):
    from .. import officegen
    from ..pii import describe, find
    blob = f"{title}\n{text}\n{sheets}\n{slides}"
    bad = [k for k in find(blob) if k in ("otp_pin", "password", "cvv")]
    if bad:
        raise ToolError(f"Isme {describe(bad)} hai; Hoola aisi file nahi banata.")
    try:
        if kind == "docx":
            data = await asyncio.to_thread(officegen.make_docx, str(title), str(text or ""))
        elif kind == "xlsx":
            data = await asyncio.to_thread(officegen.make_xlsx, str(title), sheets or {})
        elif kind == "pptx":
            data = await asyncio.to_thread(officegen.make_pptx, str(title), slides or [])
        else:
            raise ToolError("kind: docx | xlsx | pptx")
    except (ValueError, TypeError) as e:
        raise ToolError(str(e))
    view = await asyncio.to_thread(_deliver, ctx, _safe(filename or title, "." + kind), data, "hoola")
    return view | {"made": kind, "note": "The file card is in chat; the file_id works for email / hoola_send."}


async def photo_clean(ctx: Ctx, file_id, color="white", **_):
    from .. import imagekit
    name, data = await asyncio.to_thread(_owner_bytes, ctx, file_id)
    try:
        out = await asyncio.to_thread(imagekit.clean_background, data, str(color or "white"))
    except imagekit.ImageError as e:
        raise ToolError(str(e))
    except Exception as e:
        raise ToolError(f"Photo saaf nahi ho payi ({type(e).__name__}). Doosri photo try kijiye.")
    view = await asyncio.to_thread(_deliver, ctx, _safe(Path(name).stem + " clean", ".jpg"), out, "hoola")
    return view | {"done": True}


async def id_photo(ctx: Ctx, file_id, size="india_passport", color="white", **_):
    from .. import imagekit
    name, data = await asyncio.to_thread(_owner_bytes, ctx, file_id)
    try:
        res = await asyncio.to_thread(imagekit.id_photo, data, str(size or "india_passport"), str(color or "white"))
    except imagekit.ImageError as e:
        raise ToolError(str(e))
    one = await asyncio.to_thread(_deliver, ctx, _safe(f"{size} photo", ".jpg"), res["photo"], "hoola")
    out: dict[str, Any] = {"photo": one}
    if res.get("sheet"):
        out["print_sheet"] = await asyncio.to_thread(_deliver, ctx, _safe(f"{size} 4x6 print sheet", ".jpg"), res["sheet"], "hoola")
    return out | {"note": "Single photo for online forms; the 4x6 sheet prints at any photo shop."}


async def memory_search(ctx: Ctx, query, **_):
    from .. import semantic
    from ..db import MemoryFact, session
    from sqlalchemy import select

    def load():
        from ..fence import chats_in   # v0.246 FENCE: another Session's auto facts stay there
        allowed = chats_in(ctx.tenant_id, getattr(ctx, "conversation_id", "") or "")
        with session() as s:
            q = select(MemoryFact).where(MemoryFact.tenant_id == ctx.tenant_id)
            if allowed is not None:
                q = q.where(MemoryFact.pinned.is_(True) | MemoryFact.conversation_id.is_(None)
                            | MemoryFact.conversation_id.in_(allowed))
            return [(m.id, m.text) for m in s.scalars(q.order_by(MemoryFact.id.desc()).limit(3000)).all()]
    items = await asyncio.to_thread(load)
    hits = await asyncio.to_thread(semantic.rank, str(query), items, 8)
    return {"found": [{"fact_id": i, "text": t, "match": round(sc, 2)} for i, t, sc in hits],
            "searched": len(items), "by_meaning": semantic.available()}


MAKE_HANDLERS = {"make_document": make_document, "photo_clean": photo_clean, "id_photo": id_photo,
                 "memory_search": memory_search}
