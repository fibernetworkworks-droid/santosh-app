"""v0.999.51 IMAGE CHAT - the Create > Image page is a chat like the Video page (owner: "DESIGN SHOULD BE SAME AS HOOLA
VIDEO SECTION -- SHOW DESIGN FIRST" -> design canvas claude.ai/artifact/MADqzZqiUDde71pFpJ95f7 -> "GO BUILD").

- An Image chat = a Conversation with kind 'image', kept out of every Hoola chat list (callconv.not_call, convs), like the
  Video chat; what she tells it still reaches her one memory.
- Her picks in Picture settings (shape, style, quality, how many, brand colours, what to leave out, her reference pictures)
  ride each message as a "[Web console Image settings: ...]" note: her bubble shows only her words.
- A turn here gets the create + file tools in view (`FAMILIES`) and `block`: the rules (pictures = create_studio
  action=image with her settings exactly) and the picture sets made in this chat.
- Money: a picture costs Rs 3 (Standard) or Rs 12 (Best); the page shows the price under the box before she sends, and the
  pictures are made when she sends (the owner's design: no price card for a picture).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.imagechat")

KIND = "image"
_OF: dict[str, bool] = {}
FAMILIES = ["create", "file"]
GREETING = ("Tell me the picture you want, or add your photo with +. I can make posters, product photos, reel covers and "
            "banners, with Hindi or English words on them. You see the price before anything is made.")


def is_image(conv: str) -> bool:
    """True for an Image chat, and for a voice call started from one (the call record's origin)."""
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
        log.exception("image chat kind read failed")
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
            return {"id": c.id, "title": c.title or "Image chat", "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Image chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "title": c.title or "Image chat", "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Image chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=GREETING, display=GREETING, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "title": "Image chat", "new": True}


def chats(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    """Her earlier Image chats (newest first), each with its first words as the title when it was never named."""
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
            title = c.title if c.title and c.title != "Image chat" else (words[:60] or "Image chat")
            at = c.last_at or c.created_at
            out.append({"id": c.id, "title": title, "at": at.isoformat() if at else ""})
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- what a turn in the Image chat knows
RULES = (
    "You are Hoola's picture maker, talking in the Create > Image page's own chat. She makes pictures here: posters, product "
    "photos, reel covers, banners, logos, cards. Her picks ride her message as a '[Web console Image settings: ...]' note: "
    "use them EXACTLY (shape, style, quality, how many, brand colours, what to leave out, her reference pictures) unless her "
    "words in this message ask for something else. To make pictures call create_studio action=image ONCE with prompt = one "
    "rich picture description you write from her words (subject, place, light, mood; any words to print on the picture "
    "exactly as she wrote them, in her script), plus aspect, style, quality, count and file_ids (her reference pictures from "
    "the note and the photos she attached to this message). Brand colours and things to leave out go into the prompt. A "
    "DOCUMENT she attached = read it first (file_read) and follow it; quote nothing from it that is not there. A change to a "
    "picture she already made = a new set with the changed description, and that picture in file_ids when she wants it kept. "
    "Never invent prices: Standard is Rs 3 a picture, Best Rs 12; the pictures are made the moment you call the tool. Reply "
    "in one or two short sentences; never claim pictures are ready - the set in the chat shows them. Not for real people "
    "without their permission, nudity, someone else's brand or logo, or fake documents and ids. ")


def _sets(tenant: str, conv: str, limit: int = 8) -> list[dict[str, Any]]:
    try:
        from .create import jobs
        out: dict[str, dict[str, Any]] = {}
        for it in jobs.shelf(tenant):
            m = it.get("meta") or {}
            if it.get("kind") != "image" or m.get("chat") != conv:
                continue
            s = out.setdefault(m.get("job") or it["id"], {"aspect": m.get("aspect") or "", "style": m.get("style") or "",
                                                          "prompt": (m.get("prompt") or "")[:200], "ids": []})
            s["ids"].append(it["id"])
            if len(out) > limit:
                break
        for j in jobs.recent(tenant):
            if j.get("kind") == "image" and j.get("conv") == conv and j.get("status") != "done":
                out.setdefault(j["id"], {"aspect": j.get("aspect") or "", "style": j.get("style") or "", "prompt": j.get("title") or "",
                                         "ids": [], "state": "being made" if j["status"] == "running" else "could not be made: " + (j.get("error") or "")})
        return list(out.values())[:limit]
    except Exception:   # noqa: BLE001
        log.exception("image chat sets failed")
        return []


def block(tenant: str, conv: str) -> str:
    sets = _sets(tenant, conv)
    made = ("\nPicture sets in this chat (newest first):\n" + "\n".join(
        f"- {s['aspect']} {s['style'] or 'Auto'}: {s.get('state') or 'ready, pictures ' + ', '.join(s['ids'])}. Words: {s['prompt']}"
        for s in sets)) if sets else "\nNo pictures made in this chat yet."
    return f"\n\n<image_chat>{RULES}{made}\n</image_chat>"


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/image/chat", dependencies=[Depends(require_key)])
    def image_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/image/chat/new", dependencies=[Depends(require_key)])
    def image_chat_new(tenant: str = Depends(current_tenant)):
        return new_chat(tenant)

    @router.get("/api/image/chats", dependencies=[Depends(require_key)])
    def image_chats(tenant: str = Depends(current_tenant)):
        return {"chats": chats(tenant)}

    @router.get("/api/image/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def image_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Image chat")
        _OF[conv] = True
        return {"ok": True}

    app.include_router(router)

