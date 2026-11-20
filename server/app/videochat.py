"""v0.999.43 VIDEO CHAT - the Create > Video page is a chat (owner, on the design: "THIS IS TO BE A FULL CHAT PANEL ... AT
BOTTOM DIFFERENT OPTIONS REGARDING VIDEO ... USER CAN UPLOAD IMAGES, VIDEOS, DOCUMENTS, EVERY FILE" -> "GO BUILD").

- A Video chat = a Conversation with kind 'video', kept out of every Hoola chat list (callconv.not_call, convs), like the
  SEO / Social desk chats; what she tells it still reaches her one memory.
- Her picks under the typing box (shape, length, camera, model, resolution, sound, takes, spoken language) ride each
  message as a "[Web console Video settings: ...]" note: her bubble shows only her words (turnbox.her_words strips it).
- A turn here gets the video tools in view (`FAMILIES`) and `block`: the rules (one clip = video_studio action=clip with
  her settings exactly; her photo = start_image_file_id; a document = read it first) and the clips made in this chat.
- Money: every clip still ends on the studio's price card. Nothing is spent until she taps Yes (here or on the tile).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.videochat")

KIND = "video"
_OF: dict[str, bool] = {}
FAMILIES = ["studio"]
GREETING = ("Tell me the shot you want, or add a photo, a video or a brief with +. I write the shot plan for free and show "
            "you the price before anything is made.")


def is_video(conv: str) -> bool:
    """True for a Video chat, and for a voice call started from one (the call record's origin)."""
    if not conv:
        return False
    if conv in _OF:
        return _OF[conv]
    hit = False
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None:
                if (c.kind or "") == KIND:
                    hit = True
                elif (c.kind or "") == "call" and c.origin_conv:
                    o = s.get(Conversation, c.origin_conv)
                    hit = bool(o is not None and (o.kind or "") == KIND)
    except Exception:   # noqa: BLE001
        log.exception("video chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "title": c.title or "Video chat", "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Video chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "title": c.title or "Video chat", "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Video chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=GREETING, display=GREETING, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "title": "Video chat", "new": True}


def chats(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    """Her earlier Video chats (newest first), each with its first words as the title when it was never named."""
    out = []
    with session() as s:
        rows = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(limit)).all()
        for c in rows:
            first = s.scalars(select(Message.display).where(Message.conversation_id == c.id, Message.role == "user")
                              .order_by(Message.id).limit(1)).first()
            if not first:
                continue
            from .pipeline.turnbox import her_words
            words = her_words(first)[0].strip().replace("\n", " ")
            title = c.title if c.title and c.title != "Video chat" else (words[:60] or "Video chat")
            at = c.last_at or c.created_at
            out.append({"id": c.id, "title": title, "at": at.isoformat() if at else ""})
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- what a turn in the Video chat knows
RULES = (
    "You are Hoola's video maker, talking in the Create > Video page's own chat. She makes short clips here (up to 30 s; a "
    "longer film is the Director, next to this chat). Her picks under the typing box ride her message as a "
    "'[Web console Video settings: ...]' note: use them EXACTLY (aspect, seconds, camera move, model / Hoola Auto mode, "
    "resolution, sound, takes, spoken language) unless her words in this message ask for something else. "
    "To make a clip call video_studio action=clip ONCE with brief = one rich shot description you write from her words "
    "(subject, place, light, mood, the camera move in words), plus her settings: aspect, seconds, language, resolution, "
    "auto, model (only if she picked one), variants = takes, compare (2-3 models only if she asked to compare), audio. "
    "A PHOTO she attached for this clip = start_image_file_id (it becomes the first frame). A DOCUMENT she attached (a "
    "brief, a script, a sheet) = read it first (file_read) and follow it; quote nothing from it that is not there. A VIDEO "
    "she attached = describe its look from what she says about it; the studio cannot copy a video's motion. "
    "Never invent prices: the price card appears on the clip by itself in about a minute, and nothing is spent until she "
    "taps Yes on it - say exactly that, short. A change to a clip she already made = a new clip with the changed brief "
    "(name it after the old one + the change). Reply in two or three short sentences; never claim a clip is made or "
    "ready before the studio says so. Not for videos of real people without their permission, real brands, news, "
    "officials or politicians. ")


def _clips(tenant: str, conv: str, limit: int = 8) -> list[dict[str, Any]]:
    try:
        from .studio import service as ss
        st = ss.studio_sync(tenant)
        out = []
        for row in ss.listing(tenant)[:40]:
            try:
                p = st.load(row["project"])
            except Exception:   # noqa: BLE001
                continue
            if (p.get("conversation") or "") != conv:
                continue
            v = ss.view(tenant, p)
            state = ("writing the shot plan" if v.get("planning") else "waiting for her Yes on the price card" if v.get("approvals")
                     else "being made" if v.get("working") else "could not start: " + v["error"] if v.get("error")
                     else "ready" if any(o.get("url") for o in v.get("outputs") or []) or any(
                         t.get("url") for s in v.get("shots") or [] for t in s.get("take_list") or []) else "planned")
            out.append({"name": v["project"], "aspect": v["aspect"], "seconds": v.get("seconds"), "state": state,
                        "brief": (v.get("brief") or "")[:200]})
            if len(out) >= limit:
                break
        return out
    except Exception:   # noqa: BLE001
        log.exception("video chat clips failed")
        return []


def block(tenant: str, conv: str) -> str:
    clips = _clips(tenant, conv)
    made = ("\nClips in this chat (newest first):\n" + "\n".join(
        f"- {c['name']} ({c['aspect']}, {c['seconds']} s): {c['state']}. Brief: {c['brief']}" for c in clips)) if clips else \
        "\nNo clips made in this chat yet."
    return f"\n\n<video_chat>{RULES}{made}\n</video_chat>"


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/video/chat", dependencies=[Depends(require_key)])
    def video_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/video/chat/new", dependencies=[Depends(require_key)])
    def video_chat_new(tenant: str = Depends(current_tenant)):
        return new_chat(tenant)

    @router.get("/api/video/chats", dependencies=[Depends(require_key)])
    def video_chats(tenant: str = Depends(current_tenant)):
        return {"chats": chats(tenant)}

    @router.get("/api/video/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def video_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Video chat")
        _OF[conv] = True
        return {"ok": True}

    app.include_router(router)

