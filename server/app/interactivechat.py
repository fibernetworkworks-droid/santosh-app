"""v0.999.170 HOOLA INTERACTIVE REBUILD - the Hoola Interactive home is a chat, the twin of the Interactive chat (owner, on the
design canvas claude.ai/artifact/38Ejw9Eekn9y8u8H8nEwGp: "GO BUILD"; contract docs/HOOLA_INTERACTIVE_REBUILD.md).

- An Interactive chat = a Conversation with kind 'interactive', kept out of every Hoola chat list (callconv.not_call,
  convs) like the Vocal / Music chats; what she tells it still reaches her one memory.
- Her picks (language, face, voice, engine, shape) ride each message as an "[Interactive settings: ...]" note; her bubble
  shows only her words.
- A turn here gets the create + file tools in view and `block`: the rules (a video = create_studio action=talking_video,
  a DRAFT with its price card - making it is HER tap on the card, never the model's) and the faces, voices, engines and
  drafts of this chat.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.interactivechat")

KIND = "interactive"
_OF: dict[str, bool] = {}
FAMILIES = ["create", "file", "webfetch"]   # v0.999.172 + webfetch: "start from a web page"
GREETING = ("Tell me what the video should say, in any language: an offer, a welcome, a lesson, a product. I write the "
            "scenes, pick your face and voice, and show you the price before anything is made.")


def is_interactive(conv: str) -> bool:
    """True for an Interactive chat, and for a voice call started from one (the call record's origin)."""
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
        log.exception("interactive chat kind read failed")
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
            return {"id": c.id, "title": c.title or "Interactive chat", "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    try:                          # v0.999.172 a chat that holds a plan is not untouched, even with no words of hers
        from .interactive import studio as S
        planned = {p.get("chat") for p in S._load(tenant).get("projects") or [] if p.get("chat")}
    except Exception:   # noqa: BLE001
        planned = set()
    with session() as s:          # her newest untouched Interactive chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n and c.id not in planned:
                return {"id": c.id, "title": c.title or "Interactive chat", "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Interactive chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=GREETING, display=GREETING, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "title": "Interactive chat", "new": True}


def chats(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    """Her earlier Interactive chats (newest first), each with its first words as the title when it was never named."""
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
            title = c.title if c.title and c.title != "Interactive chat" else (words[:60] or "Interactive chat")
            at = c.last_at or c.created_at
            out.append({"id": c.id, "title": title, "at": at.isoformat() if at else ""})
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- what a turn in the Interactive chat knows
RULES = (
    "You are Hoola's video maker, talking in the Hoola Interactive page's own chat. She makes talking videos here: a "
    "person (her face, a consented face or an AI-made one) speaks her words in any language, with titles, prices and "
    "numbers drawn as scenes. Her picks ride her message as an '[Interactive settings: ...]' note: use them EXACTLY "
    "(language, kind, face, voice, engine, shape, length) unless her words in this message ask for something else. "
    "Language 'auto' = the language her words are written in, or the one she names for the video (she may write in one "
    "language and ask for the video in another); pass it as a language code. Kind presenter|explainer|reel|product|lesson "
    "is passed as kind=; length N s = seconds=N. To plan a video "
    "call create_studio action=talking_video ONCE with brief = what the video is about in her words (keep every price, "
    "date, number and name she gave exactly), language, face = an avatar id below or empty, voice = a voice id below or "
    "empty, engine = an engine id below or empty (her default), shape talking_head|product|reel, kind presenter|explainer|reel|product|lesson, seconds 10-90. It makes "
    "a DRAFT with scenes and a price card in this chat; it never makes the video - making it is HER tap on the card. A "
    "change she asks for (another voice, shorter, another language, another engine) = call it again with id = the draft "
    "id and the change; the earlier draft stays. Never invent a price, discount, date or count she did not write: a scene "
    "that needs a number she did not give is left for her to fill. Reply in one or two short sentences in her language "
    "and never claim a video is ready - the chat shows it. A face is used only with her consent on record (the Avatars "
    "page); never a public figure or anyone under 18. ")


def _context_line(tenant: str) -> str:
    try:
        from .interactive import engines as EN
        from .interactive import studio as S
        from .interactive import voice as VO
        d = S._load(tenant)
        faces = [f"{a['id']} ({a['name']})" for a in d.get("avatars") or []][:8]
        vs = VO.voices(tenant)
        mine = [f"{v['id']} ({v['name']}, her own)" for v in vs["mine"]][:6]
        lib = [f"{v['id']} ({v['name']}, {v.get('gender') or 'any'})" for v in vs["library"] if v.get("ready")][:24]
        engs = [f"{e['id']} ({e['label']}, {e['price']}{'' if e['ready'] else ', NOT connected'})"
                for e in EN.view(tenant)["engines"] if e["job"] == "video"]
        return ("\nHer faces: " + (", ".join(faces) or "none yet (she adds one on the Avatars page)")
                + "\nVoices: " + ", ".join(mine + lib)
                + "\nVideo engines: " + ", ".join(engs)
                + f"\nHer default video engine: {EN.defaults_of(tenant)['video']}")
    except Exception:   # noqa: BLE001
        log.exception("interactive chat context failed")
        return ""


def chat_items(tenant: str, conv: str, limit: int = 20) -> list[dict[str, Any]]:
    from .interactive import studio as S
    d = S._load(tenant)
    rows = [p for p in d.get("projects") or [] if p.get("chat") == conv][:limit]
    out = []
    for p in rows:
        try:
            q = S.quote_for(tenant, p)
        except Exception:   # noqa: BLE001
            q = None
        out.append({**p, "problems": S.problems(p) + S.engine_problems(tenant, p), "quote": q})
    return out


def block(tenant: str, conv: str) -> str:
    rows = chat_items(tenant, conv, 8)
    made = ("\nDrafts in this chat (newest first):\n" + "\n".join(
        f"- id {r['id']}: '{r['title']}' in {r.get('lang')}, {len(r['scenes'])} scenes, engine {r.get('engine')}, "
        f"status {r['status']}" for r in rows)) if rows else "\nNothing planned in this chat yet."
    return f"\n\n<interactive_chat>{RULES}{_context_line(tenant)}{made}\n</interactive_chat>"


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/interactive/chat", dependencies=[Depends(require_key)])
    def interactive_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/interactive/chat/new", dependencies=[Depends(require_key)])
    def interactive_chat_new(tenant: str = Depends(current_tenant)):
        return new_chat(tenant)

    @router.get("/api/interactive/chats", dependencies=[Depends(require_key)])
    def interactive_chats(tenant: str = Depends(current_tenant)):
        return {"chats": chats(tenant)}

    @router.get("/api/interactive/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def interactive_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Interactive chat")
        _OF[conv] = True
        return {"ok": True}

    @router.get("/api/interactive/chat/{conv}/items", dependencies=[Depends(require_key)])
    def interactive_chat_items(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Interactive chat")
        return {"items": chat_items(tenant, conv)}

    app.include_router(router)
