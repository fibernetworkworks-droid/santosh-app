"""v0.999.79 HOOLA MUSIC - the Create > Music page is a chat like the Video and Image pages (owner: "WE WILL BUILD OUR OWN
SUNO -- FOR MUSIC" -> "MAKE IT FOR GLOBAL ... ALL LANGUAGES" -> "ADD AI CHAT TO ALL BOARDS" -> "START THE BUILD"; design
canvas claude.ai/artifact/Qq4WmnjktJD7VS9torkejn; plan docs/HOOLA_MUSIC_PLAN.md).

- A Music chat = a Conversation with kind 'music', kept out of every Hoola chat list (callconv.not_call, convs), like the
  Video and Image chats; what she tells it still reaches her one memory.
- Her picks in Song settings (kind, language, singers, length, tempo, versions, what to keep out, her lyrics) ride each
  message as a "[Web console Song settings: ...]" note: her bubble shows only her words.
- A turn here gets the create + file tools in view (`FAMILIES`) and `block`: the rules (a song = create_studio
  action=song with her settings exactly; a change to a made song = create_studio action=song_edit, free, a new version)
  and the songs made in this chat with their ids, lengths and words.
- Money: a song costs about Rs 7 (Lyria, ~80 credits) per version; the page shows the price under the box before she
  sends, and the songs are made when she sends (the Image page's rule). Edits are free (ffmpeg on the server).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.musicchat")

KIND = "music"
_OF: dict[str, bool] = {}
FAMILIES = ["create", "file"]
GREETING = ("Tell me the song you want, in any language. A song, an instrumental, a jingle or a film score; your own lyrics "
            "or mine. You get two versions to pick from, and I can change any of them after: shorter, longer, a fade, louder, "
            "a new style.")


def is_music(conv: str) -> bool:
    """True for a Music chat, and for a voice call started from one (the call record's origin)."""
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
        log.exception("music chat kind read failed")
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
            return {"id": c.id, "title": c.title or "Music chat", "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Music chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "title": c.title or "Music chat", "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Music chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=GREETING, display=GREETING, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "title": "Music chat", "new": True}


def chats(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    """Her earlier Music chats (newest first), each with its first words as the title when it was never named."""
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
            title = c.title if c.title and c.title != "Music chat" else (words[:60] or "Music chat")
            at = c.last_at or c.created_at
            out.append({"id": c.id, "title": title, "at": at.isoformat() if at else ""})
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- what a turn in the Music chat knows
RULES = (
    "You are Hoola's music maker, talking in the Create > Music page's own chat. She makes songs, instrumentals, jingles and "
    "film scores here, in ANY language of the world. Her picks ride her message as a '[Web console Song settings: ...]' note: "
    "use them EXACTLY (kind, language, singers, length, tempo, how many versions, what to keep out, her lyrics) unless her "
    "words in this message ask for something else. Language 'Auto' = the language of her words or lyrics; a song may mix "
    "languages part by part when she asks. To make a song call create_studio action=song ONCE with brief = one rich line "
    "you write from her words (what it is about, the feel, the instruments), genre, language, vocals "
    "(duet|female|male|choir|group|child|none), mood, bpm (0 = let the engine choose), seconds, versions (1-4, her setting), "
    "keep_out, and lyrics: HER lyrics word for word, or lyrics you write first when she asked you to, with part tags on their "
    "own lines ([Intro] [Verse 1] [Chorus] [Verse 2] [Bridge] [Outro]), in the language she asked. A CHANGE to a song already "
    "made here (shorter, a 15 / 30 second cut, fade in / out, louder, quieter, faster, slower, higher / lower key, more bass "
    "or treble, clean noise, join two songs) = create_studio action=song_edit with id = that song's id from the list below "
    "and steps = audio steps in order: trim{start,end} cut{start,end} fade{in,out} volume{db} normalize{target "
    "social|music|podcast} speed{factor} pitch{semitones} eq{bass,treble} denoise{strength} reverse; it is free, made at "
    "once, and saved as a NEW version (the old one stays). For a reel cut, trim to the part she names (a chorus usually "
    "starts near a third of the way in) and fade the end. NOT possible yet, say so plainly and offer the nearest thing: "
    "remaking only one part of a song, changing one sung line, splitting a song into vocals / drums / bass, singing in HER "
    "own voice, a cover of an uploaded song, a song from her humming (these come in later phases). A new style or another "
    "language = a NEW song with the same words (or the words rewritten for the tune), which costs like any song. Never "
    "invent prices: about Rs 7 (80 credits) per version; the songs are made the moment you call the tool. Reply in one or "
    "two short sentences in her language; never claim a song is ready - the set in the chat shows it. Never copy a named "
    "real singer's voice, never claim a song is by a real artist, and say every song is marked as made by AI. ")


def _songs(tenant: str, conv: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        from .create import jobs
        out: list[dict[str, Any]] = []
        for it in jobs.shelf(tenant):
            m = it.get("meta") or {}
            if it.get("kind") != "song" or m.get("chat") != conv:
                continue
            out.append({"id": it["id"], "title": it.get("title") or "", "version": m.get("version") or "",
                        "seconds": m.get("seconds") or 0, "edit": m.get("edit") or "", "parent": m.get("parent") or "",
                        "genre": m.get("genre") or "", "language": m.get("language") or "",
                        "lyrics": (m.get("lyrics") or "")[:400]})
            if len(out) >= limit:
                break
        for j in jobs.recent(tenant):
            if j.get("kind") == "song" and j.get("conv") == conv and j.get("status") != "done":
                out.insert(0, {"id": j["id"], "title": j.get("title") or "", "state": "being made"
                               if j["status"] == "running" else "could not be made: " + (j.get("error") or "")})
        return out[:limit]
    except Exception:   # noqa: BLE001
        log.exception("music chat songs failed")
        return []


def block(tenant: str, conv: str) -> str:
    rows = _songs(tenant, conv)

    def line(s: dict[str, Any]) -> str:
        if s.get("state"):
            return f"- {s['title']}: {s['state']}"
        what = (f"version {s['version']}" if s.get("version") else "") + (f", edited from {s['parent']} ({s['edit']})" if s.get("parent") else "")
        words = f" Words: {s['lyrics'].replace(chr(10), ' / ')}" if s.get("lyrics") else ""
        return f"- id {s['id']}: {s['title']} ({what or 'song'}, {s['seconds']:.0f} s, {s['genre'] or 'auto'}, {s['language'] or 'auto'}).{words}"
    made = ("\nSongs in this chat (newest first):\n" + "\n".join(line(s) for s in rows)) if rows else "\nNo songs made in this chat yet."
    return f"\n\n<music_chat>{RULES}{made}\n</music_chat>"


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/music/chat", dependencies=[Depends(require_key)])
    def music_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/music/chat/new", dependencies=[Depends(require_key)])
    def music_chat_new(tenant: str = Depends(current_tenant)):
        return new_chat(tenant)

    @router.get("/api/music/chats", dependencies=[Depends(require_key)])
    def music_chats(tenant: str = Depends(current_tenant)):
        return {"chats": chats(tenant)}

    @router.get("/api/music/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def music_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Music chat")
        _OF[conv] = True
        return {"ok": True}

    app.include_router(router)
