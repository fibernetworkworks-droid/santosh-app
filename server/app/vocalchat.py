"""v0.999.89 HOOLA VOCAL GLOBAL - the Hoola Vocal home is a chat, the twin of the Music chat (owner, on the design canvas
claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue: "GO BUILD ALL"; contract docs/HOOLA_VOCAL_GLOBAL.md).

- A Vocal chat = a Conversation with kind 'vocal', kept out of every Hoola chat list (callconv.not_call, convs) like the
  Music / Video / Image chats; what she tells it still reaches her one memory.
- Her picks (language, voice, style, speed, takes, engine) ride each message as a "[Vocal settings: ...]" note; her bubble
  shows only her words.
- A turn here gets the create + file tools in view and `block`: the rules (speech = create_studio action=voice, a talk
  between people = action=dialogue, a sound = action=sound, all on her Vocal shelf) and the voices + takes of this chat.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.vocalchat")

KIND = "vocal"
_OF: dict[str, bool] = {}
FAMILIES = ["create", "file"]
GREETING = ("Tell me what to say, in any language: a welcome, an ad, a story, a lesson, a podcast between two people, or a "
            "sound. I make two takes to choose from, and I can change them after: slower, warmer, another voice, another "
            "language.")


def is_vocal(conv: str) -> bool:
    """True for a Vocal chat, and for a voice call started from one (the call record's origin)."""
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
        log.exception("vocal chat kind read failed")
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
            return {"id": c.id, "title": c.title or "Vocal chat", "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Vocal chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "title": c.title or "Vocal chat", "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Vocal chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=GREETING, display=GREETING, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "title": "Vocal chat", "new": True}


def chats(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    """Her earlier Vocal chats (newest first), each with its first words as the title when it was never named."""
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
            title = c.title if c.title and c.title != "Vocal chat" else (words[:60] or "Vocal chat")
            at = c.last_at or c.created_at
            out.append({"id": c.id, "title": title, "at": at.isoformat() if at else ""})
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- what a turn in the Vocal chat knows
RULES = (
    "You are Hoola's voice maker, talking in the Hoola Vocal page's own chat. She makes speech, voice-overs, readings, "
    "dialogues and sounds here, in ANY language of the world. Her picks ride her message as a '[Vocal settings: ...]' note: "
    "use them EXACTLY (language, voice, style, speed, takes, engine) unless her words in this message ask for something "
    "else. Language 'auto' = the language of the words to be spoken. To make speech call create_studio action=voice ONCE "
    "with text = EXACTLY the words to be spoken (her words when she gave them, or words you write when she asked you to "
    "write them, in the language she wants), feelings in square brackets where she asked for them ([warm] [whispers] "
    "[laughs] [sighs] [excited] [serious] [slowly] [cheerful] [pause]), voice, language, style, speed, takes. Two or more "
    "people talking = action=dialogue with lines and a cast (a different voice per speaker). A sound effect = action=sound "
    "with prompt. A CHANGE to a take (slower, warmer, another voice, another language) = make it again with the change: "
    "every take stays, nothing is overwritten. Translating is fine when she asks for another language: write the words in "
    "that language yourself. Never read prices from memory: Standard speech costs about 15 credits a minute, Premium about "
    "80; the takes are made the moment you call the tool. Reply in one or two short sentences in her language and never "
    "claim a take is ready - the chat shows it. Never copy a named real person's voice; her own voice only after her "
    "recorded consent (the Your voice page). ")


def _voices_line(tenant: str) -> str:
    try:
        from .vocal import service as V
        d = V._load(tenant)
        mine = [f"{v['id']} ({v['name']}, {v.get('kind')})" for v in V._mine(d)][:8]
        lib = [f"{v['id']} ({v['name']}, {v.get('gender') or 'any'}, {v.get('tier')})" for v in V.library()][:40]
        return ("\nHer own voices: " + (", ".join(mine) or "none") + "\nReady voices: " + ", ".join(lib))
    except Exception:   # noqa: BLE001
        log.exception("vocal chat voices failed")
        return ""


def block(tenant: str, conv: str) -> str:
    try:
        from .vocal import service as V
        rows = V.chat_items(tenant, conv, 12)
    except Exception:   # noqa: BLE001
        rows = []
    made = ("\nMade in this chat (newest first):\n" + "\n".join(
        f"- id {r['id']} take {r.get('take') or 'A'}: {r.get('kind')} '{r.get('title')}' in {r.get('lang') or 'auto'}, "
        f"voice {r.get('voice_name')}, {r.get('seconds') or 0:.0f} s" for r in rows)) if rows else "\nNothing made in this chat yet."
    return f"\n\n<vocal_chat>{RULES}{_voices_line(tenant)}{made}\n</vocal_chat>"


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/vocal/chat", dependencies=[Depends(require_key)])
    def vocal_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/vocal/chat/new", dependencies=[Depends(require_key)])
    def vocal_chat_new(tenant: str = Depends(current_tenant)):
        return new_chat(tenant)

    @router.get("/api/vocal/chats", dependencies=[Depends(require_key)])
    def vocal_chats(tenant: str = Depends(current_tenant)):
        return {"chats": chats(tenant)}

    @router.get("/api/vocal/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def vocal_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Vocal chat")
        _OF[conv] = True
        return {"ok": True}

    @router.get("/api/vocal/chat/{conv}/items", dependencies=[Depends(require_key)])
    def vocal_chat_items(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Vocal chat")
        from .vocal import service as V
        return {"items": V.chat_items(tenant, conv)}

    app.include_router(router)
