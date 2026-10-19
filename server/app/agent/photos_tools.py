"""Google Photos tools. Google (since 31 Mar 2025) lets apps see ONLY the photos the user picks in the Google Photos
Picker, plus what the app itself uploaded. Santosh cannot browse, search, share or delete the user's library."""
from __future__ import annotations

import asyncio
from typing import Any

from ..bazar.connectors.base import ToolError as BazarError
from ..photos import service as ps
from ..photos.client import NotConnected, PhotosError
from .tools import Ctx, ToolError

SOURCES = {"type": "array", "description": "Each item: {email_id, attachment_id} (photo attached to an email), {file_id} "
                                           "(a PC or phone file) or {drive_file} (a Google Drive file name / link / id)",
           "items": {"type": "object", "properties": {"email_id": {"type": "string"}, "attachment_id": {"type": "string"},
                                                      "file_id": {"type": "string"}, "drive_file": {"type": "string"}}}}

PHOTOS_TOOLS = [
    {"name": "photos_pick", "description": (
        "Let the user choose photos/videos from their Google Photos. Santosh CANNOT browse or search the user's library "
        "(Google policy); instead this puts a 'Photos chuniye' card in the chat, the user picks, and Santosh is told when "
        "they're done. purpose = what to do next (e.g. 'Ramesh ko email karna'). Then use photos_send with the pick_id."),
     "input_schema": {"type": "object", "properties": {
         "purpose": {"type": "string"}, "max_items": {"type": "integer", "description": "Optional limit"}}}},
    {"name": "photos_picked", "description": (
        "Status of a photos_pick (waiting / ready / expired) and the picked items: file name, type, size in pixels, date. "
        "Santosh sees only these details, not what is in the picture."),
     "input_schema": {"type": "object", "properties": {"pick_id": {"type": "string"}}, "required": ["pick_id"]}},
    {"name": "photos_send", "description": (
        "Use the photos the user picked: to='phone' (download cards), 'for_email' (returns file_ids to put in email_draft "
        "attachments), 'pc' (save on the user's PC), or 'drive' (save into Google Drive, optional folder). ids = only "
        "some of the picked items."),
     "input_schema": {"type": "object", "properties": {
         "pick_id": {"type": "string"}, "to": {"type": "string", "enum": ["phone", "for_email", "pc", "drive"]},
         "ids": {"type": "array", "items": {"type": "string"}}, "folder": {"type": "string"}},
         "required": ["pick_id"]}},
    {"name": "photos_upload", "description": (
        "Put photos/videos INTO the user's Google Photos (optionally into an album by name; created if missing), from "
        "email attachments, PC/phone files or Drive files. More than 20 at once needs the user's tap on a card."),
     "input_schema": {"type": "object", "properties": {
         "sources": SOURCES, "album": {"type": "string"}, "description": {"type": "string"}}, "required": ["sources"]}},
    {"name": "photos_albums", "description": (
        "Albums Santosh made in Google Photos: action list | create (title) | items (album). Santosh can't see or "
        "share albums it didn't make, and can't delete anything (Google policy)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "create", "items"]}, "title": {"type": "string"},
         "album": {"type": "string"}}, "required": ["action"]}},
]

PHOTOS_LABELS = {"photos_pick": "Photos chunne ka card bana raha hoon", "photos_picked": "Chuni hui photos dekh raha hoon",
                 "photos_send": "Photos bhej raha hoon", "photos_upload": "Photos Google Photos mein daal raha hoon",
                 "photos_albums": "Albums dekh raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except PhotosError as e:
        raise ToolError(str(e))


def _card(ctx: Ctx, pid: str) -> dict[str, Any]:
    from ..bazar import service
    try:
        out = service.run(ctx.tenant_id, ctx.conversation_id, "santosh-photos", "confirm_change", {"pending_id": pid})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")}


async def photos_pick(ctx: Ctx, purpose="", max_items=0, **_):
    v = await _t(ps.start_pick, ctx.tenant_id, ctx.conversation_id, str(purpose or ""), int(max_items or 0))
    return {"pick_id": v["pick_id"], "status": "waiting",
            "say": ("A 'Photos chuniye' card is in the chat. Tell the user to tap it, pick the photos in Google Photos and "
                    "tap Done; Santosh is told automatically. Then use photos_send with this pick_id."),
            "limits": ps.LIMITS}


async def photos_picked(ctx: Ctx, pick_id, **_):
    return await _t(ps.refresh_pick, ctx.tenant_id, str(pick_id))


async def photos_send(ctx: Ctx, pick_id, to="phone", ids=None, folder=None, **_):
    return await _t(ps.send, ctx.tenant_id, ctx.conversation_id, str(pick_id), str(to or "phone"),
                    [str(i) for i in ids or []] or None, folder)


async def photos_upload(ctx: Ctx, sources, album=None, description="", **_):
    res = await _t(ps.plan_or_upload, ctx.tenant_id, ctx.conversation_id, list(sources or []), album, str(description or ""))
    if "pending_id" in res:
        card = await asyncio.to_thread(_card, ctx, res["pending_id"])
        return {**card, "status": "needs_approval", "note": "Confirm card is in the chat; nothing uploaded yet."}
    return res


async def photos_albums(ctx: Ctx, action="list", title="", album="", **_):
    if action == "create":
        return await _t(ps.create_album, ctx.tenant_id, str(title or ""))
    if action == "items":
        return await _t(ps.album_items, ctx.tenant_id, str(album or title or ""))
    return {"albums": await _t(ps.albums, ctx.tenant_id), "limits": ps.LIMITS}


PHOTOS_HANDLERS = {"photos_pick": photos_pick, "photos_picked": photos_picked, "photos_send": photos_send,
                   "photos_upload": photos_upload, "photos_albums": photos_albums}
