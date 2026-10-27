"""Google Slides tools: the user's own Google Slides (official Slides API through Google sign-in).

Santosh writes the content (every slide's title, points and speaker notes) and these tools build the real deck.
Creating, adding, editing, reordering and exporting happen at once; deleting slides and sharing show a confirm card.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..bazar.connectors.base import ToolError as BazarError
from ..events import bus
from ..slides import service as sv
from ..slides.client import NotConnected, SlidesError
from .tools import Ctx, ToolError

DECK = {"type": "string", "description": "The presentation: its name as the user says it, a Google Slides link, or its id"}
SLIDE_SPEC = {"type": "object", "description": (
    "One slide. layout: title (title + subtitle), section (a divider), bullets (title + 3-6 short points), two_columns "
    "(title + left/right points), big_number (number + caption, e.g. '42%' / 'growth this year'), quote (quote + caption), "
    "table (title + rows, first row = header), image (title + public https image_url), closing (thank-you / call to action). "
    "notes = speaker notes, what to say."),
    "properties": {"layout": {"type": "string", "enum": list(sv.LAYOUTS)}, "title": {"type": "string"},
                   "subtitle": {"type": "string"}, "bullets": {"type": "array", "items": {"type": "string"}},
                   "left": {"type": "array", "items": {"type": "string"}}, "right": {"type": "array", "items": {"type": "string"}},
                   "number": {"type": "string"}, "caption": {"type": "string"}, "quote": {"type": "string"},
                   "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                   "image_url": {"type": "string"}, "notes": {"type": "string"}}}

SLIDES_TOOLS = [
    {"name": "slides_find", "description": "Find the user's Google Slides presentations by name (or recent ones).",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "slides_read", "description": (
        "Read a presentation: every slide's number, title, text, tables and speaker notes. Use to summarise a deck, "
        "answer from it, or before editing it."),
     "input_schema": {"type": "object", "properties": {"presentation": DECK}, "required": ["presentation"]}},
    {"name": "slides_create", "description": (
        "Make a new Google Slides presentation in the user's Drive. YOU write the whole deck: a title slide, then the "
        "content slides (short points, not paragraphs; 3-6 points per slide), a closing slide, and speaker notes for "
        "each. Mix layouts (bullets, two_columns, big_number, table, quote) so it doesn't look repetitive. Typical "
        "decks are 6-12 slides. accent = optional brand colour for titles, e.g. '#6D3FE0'. Shows a card with the link."),
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "slides": {"type": "array", "items": SLIDE_SPEC},
         "accent": {"type": "string"}}, "required": ["title", "slides"]}},
    {"name": "slides_add", "description": "Add slides to an existing presentation (at the end, or at position = slide number).",
     "input_schema": {"type": "object", "properties": {
         "presentation": DECK, "slides": {"type": "array", "items": SLIDE_SPEC}, "position": {"type": "integer"},
         "accent": {"type": "string"}}, "required": ["presentation", "slides"]}},
    {"name": "slides_edit", "description": (
        "Change one slide (slide = its number): new title, new body (a list of points, or text), new speaker notes. "
        "Or replace a word / phrase everywhere in the deck with find + replace (e.g. a client name, a year)."),
     "input_schema": {"type": "object", "properties": {
         "presentation": DECK, "slide": {"type": "integer"}, "title": {"type": "string"},
         "body": {"description": "List of points or plain text"}, "notes": {"type": "string"},
         "find": {"type": "string"}, "replace": {"type": "string"}, "match_case": {"type": "boolean"}},
         "required": ["presentation"]}},
    {"name": "slides_arrange", "description": "Move a slide to another position (slide, to), or duplicate it (duplicate=true).",
     "input_schema": {"type": "object", "properties": {
         "presentation": DECK, "slide": {"type": "integer"}, "to": {"type": "integer"}, "duplicate": {"type": "boolean"}},
         "required": ["presentation", "slide"]}},
    {"name": "slides_delete", "description": "Delete slides by number. Always shows the user a confirm card first.",
     "input_schema": {"type": "object", "properties": {
         "presentation": DECK, "slides": {"type": "array", "items": {"type": "integer"}}},
         "required": ["presentation", "slides"]}},
    {"name": "slides_export", "description": (
        "Turn a presentation into a PDF or PowerPoint (.pptx) and send it to the user's phone. The result has a file_id "
        "you can attach to an email (email_draft attachments [{file_id}])."),
     "input_schema": {"type": "object", "properties": {"presentation": DECK, "format": {"type": "string", "enum": ["pdf", "pptx"]}},
                      "required": ["presentation"]}},
    {"name": "slides_share", "description": (
        "Share a presentation with people (emails or names). role: reader (view), commenter or writer (edit). They get a "
        "Google email, so the user confirms on a card first."),
     "input_schema": {"type": "object", "properties": {
         "presentation": DECK, "people": {"type": "array", "items": {"type": "string"}},
         "role": {"type": "string", "enum": ["reader", "commenter", "writer"]}}, "required": ["presentation", "people"]}},
]

SLIDES_LABELS = {"slides_find": "Presentation dhoondh raha hoon", "slides_read": "Slides padh raha hoon",
                 "slides_create": "Presentation bana raha hoon", "slides_add": "Slides jod raha hoon",
                 "slides_edit": "Slide badal raha hoon", "slides_arrange": "Slides jama raha hoon",
                 "slides_delete": "Delete ki manzoori le raha hoon", "slides_export": "PDF / PPT bana raha hoon",
                 "slides_share": "Share ki manzoori le raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except SlidesError as e:
        raise ToolError(str(e))


def _card(ctx: Ctx, pid: str) -> dict[str, Any]:
    from ..bazar import service
    try:
        out = service.run(ctx.tenant_id, ctx.conversation_id, "santosh-slides", "confirm_change", {"pending_id": pid})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")}


def _event(ctx: Ctx, out: dict, status: str) -> None:
    bus.publish(ctx.conversation_id, "slides", {"id": out.get("id", ""), "title": out.get("title", ""),
                                                "link": out.get("link", ""), "status": status,
                                                "slide_count": out.get("slide_count")})


async def slides_find(ctx: Ctx, query="", limit=15, **_):
    return await _t(sv.find, ctx.tenant_id, str(query or ""), int(limit or 15))


async def slides_read(ctx: Ctx, presentation, **_):
    return await _t(sv.read, ctx.tenant_id, str(presentation))


async def slides_create(ctx: Ctx, title, slides, accent=None, **_):
    out = await _t(sv.create, ctx.tenant_id, str(title), list(slides or []), accent)
    _event(ctx, out, "created")
    return {**out, "note": "A card with the link is in the chat."}


async def slides_add(ctx: Ctx, presentation, slides, position=None, accent=None, **_):
    out = await _t(sv.add_slides, ctx.tenant_id, str(presentation), list(slides or []), position, accent)
    return out


async def slides_edit(ctx: Ctx, presentation, slide=None, title=None, body=None, notes=None, find=None, replace=None,
                      match_case=False, **_):
    if find:
        return await _t(sv.replace_text, ctx.tenant_id, str(presentation), str(find), str(replace or ""), bool(match_case))
    if not slide:
        raise ToolError("Kaunsi slide? slide number do (ya find + replace).")
    return await _t(sv.edit_slide, ctx.tenant_id, str(presentation), int(slide), title, body, notes)


async def slides_arrange(ctx: Ctx, presentation, slide, to=None, duplicate=False, **_):
    if duplicate:
        return await _t(sv.duplicate_slide, ctx.tenant_id, str(presentation), int(slide))
    if not to:
        raise ToolError("Kahan le jaana hai? to (slide number) do.")
    return await _t(sv.move_slide, ctx.tenant_id, str(presentation), int(slide), int(to))


async def slides_delete(ctx: Ctx, presentation, slides, **_):
    def work():
        plan = sv.plan_delete(ctx.tenant_id, str(presentation), list(slides or []))
        return sv.pend(ctx.tenant_id, ctx.conversation_id, "delete",
                       {"account": plan["client"].key, "pid": plan["pid"], "ids": plan["ids"]},
                       {"title": plan["title"], "lines": plan["lines"], "note": "Version history se wapas la sakte hain."})
    pid = await _t(work)
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval", "note": "Confirm card is in the chat; nothing deleted yet."}


async def slides_export(ctx: Ctx, presentation, format="pdf", **_):
    def work():
        from ..mailbox import service as ms
        from ..pc import service as pcs
        name, data, p = sv.export(ctx.tenant_id, str(presentation), format or "pdf")
        row = ms.store_bytes(ctx.tenant_id, name, data, "to_phone")
        return name, len(data), pcs.public_file(row), p
    name, size, view, p = await _t(work)
    bus.publish(ctx.conversation_id, "pc_file", {**view, "source": "slides"})
    return {"file": name, "size": size, "file_id": view["file_id"], "title": p.get("title", ""),
            "note": "Download card is in the chat. To email it: email_draft with attachments [{file_id}]."}


async def slides_share(ctx: Ctx, presentation, people, role="reader", **_):
    def work():
        from ..mailbox import contacts
        addrs, problems = contacts.resolve(ctx.tenant_id, ", ".join(str(x) for x in people or []))
        if problems:
            raise SlidesError(" ".join(problems))
        emails = [a.strip() for a in addrs.split(",") if a.strip()]
        if not emails:
            raise SlidesError("Kisko share karna hai?")
        c, p = sv.resolve(ctx.tenant_id, str(presentation))
        r = role if role in ("reader", "commenter", "writer") else "reader"
        label = {"reader": "Sirf dekh", "commenter": "Comment kar", "writer": "Edit kar"}[r]
        return sv.pend(ctx.tenant_id, ctx.conversation_id, "share",
                       {"account": c.key, "pid": p["presentationId"], "emails": emails, "role": r},
                       {"title": p.get("title", ""), "lines": [f"{label} sakenge: " + ", ".join(emails)],
                        "note": "Unhe Google se email jayega."})
    pid = await _t(work)
    card = await asyncio.to_thread(_card, ctx, pid)
    return {**card, "status": "needs_approval"}


SLIDES_HANDLERS = {"slides_find": slides_find, "slides_read": slides_read, "slides_create": slides_create,
                   "slides_add": slides_add, "slides_edit": slides_edit, "slides_arrange": slides_arrange,
                   "slides_delete": slides_delete, "slides_export": slides_export, "slides_share": slides_share}
