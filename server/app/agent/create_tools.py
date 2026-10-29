"""v0.259 Tool `create_studio`: the Create Studio engines Video Studio does not already have - a whole SONG (Google
Lyria), a VOICE-OVER in any Gemini voice, and DUBBING of her own video into other languages. Every result lands in
the chat as a card (play / download / open in the workspace) and in her creations."""
from __future__ import annotations

from typing import Any

from ..events import bus
from .tools import Ctx, ToolError

CREATE_TOOLS = [
    {"name": "create_studio", "description": (
        "CREATE STUDIO audio + dubbing. action=song: a complete song / instrumental / jingle / film score by Google Lyria "
        "(brief, genre, language, vocals duet|female|male|choir|none, mood, bpm, seconds, lyrics = hers word for word, or "
        "write them yourself first when she asked you to). action=voice: a voice-over (text, voice = a Gemini voice name "
        "from action=voices or 'mine' = her Hoola's own voice, language, style friendly|calm|excited|news|story|ad, speed "
        "0.6-1.6). action=dub: dub HER OWN video (file_id) into languages [up to 4] with matched voices per speaker, "
        "keep_sound = original music / room kept quietly underneath (default true); up to 3 minutes. action=voices: the "
        "voice list. Tell her honestly: dub voices are matched not cloned, lips are not re-synced (lip sync = Video Studio, "
        "paid card). Videos made from a description -> video_studio; pictures -> photo_banao; her footage edits -> "
        "video_edit. One short line after: what was made; the card shows it."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["song", "voice", "dub", "voices"]},
         "brief": {"type": "string"}, "genre": {"type": "string"}, "language": {"type": "string"},
         "vocals": {"type": "string"}, "mood": {"type": "string"}, "bpm": {"type": "integer"}, "seconds": {"type": "integer"},
         "lyrics": {"type": "string"}, "text": {"type": "string"}, "voice": {"type": "string"}, "style": {"type": "string"},
         "speed": {"type": "number"}, "file_id": {"type": "string"},
         "languages": {"type": "array", "items": {"type": "string"}}, "keep_sound": {"type": "boolean"},
         "title": {"type": "string"}},
         "required": ["action"]}},
]
CREATE_LABELS = {"create_studio": "Create Studio mein bana raha hoon"}


def _store(ctx: Ctx, title: str, ext: str, data: bytes, what: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    from ..mailbox import service as ms
    from ..pc.service import public_file
    from .make_tools import _safe
    row = ms.store_bytes(ctx.tenant_id, _safe(title or "Hoola " + what, ext), data, "to_phone")
    view = public_file(row)
    view.pop("pc_path", None)
    card = {**view, "title": title or view["name"], "studio": what, "ai": True, **(extra or {})}
    bus.publish(ctx.conversation_id, "pc_file", card)
    return view


async def create_studio(ctx: Ctx, action, **a: Any):
    from .. import usage
    from ..create import service as cs
    action = str(action)
    if action == "voices":
        return {"voices": cs.voices(), "ready": cs.ready(), "styles": list(cs.STYLES), "languages": list(cs.LANGS)}
    if not str(getattr(ctx, "actor", "owner") or "owner").startswith(("owner", "approved", "goal")):
        if not usage.allowed(ctx.tenant_id, "routine"):
            raise ToolError(usage.blocked_text(ctx.tenant_id))
    try:
        if action == "song":
            r = await cs.song(a.get("brief") or "", a.get("genre") or "", a.get("language") or "Hindi",
                              a.get("vocals") or "duet", a.get("mood") or "", int(a.get("bpm") or 0),
                              int(a.get("seconds") or 0), a.get("lyrics") or "")
            title = a.get("title") or (a.get("brief") or a.get("genre") or "Hoola song")[:40]
            v = _store(ctx, title, r["ext"], r["bytes"], "song", {"genre": a.get("genre") or "", "language": a.get("language") or ""})
            return {"status": "done", "file_id": v["file_id"], "name": v["name"], "about_inr": 7,
                    "note": "Gaana ban gaya; chat mein card par sun / download sakti hain. Ek line mein batao."}
        if action == "voice":
            r = await cs.voice(a.get("text") or "", a.get("voice") or "", a.get("language") or "Hindi",
                               a.get("style") or "friendly", float(a.get("speed") or 1.0), ctx.tenant_id)
            title = a.get("title") or ("Voice-over · " + r["voice"])
            v = _store(ctx, title, r["ext"], r["bytes"], "voice", {"voice": r["voice"], "seconds": r["seconds"]})
            return {"status": "done", "file_id": v["file_id"], "name": v["name"], "voice": r["voice"], "seconds": r["seconds"]}
        if action == "dub":
            fid = str(a.get("file_id") or "").strip()
            if not fid:
                raise ToolError("Kaunsa video dub karna hai? Pehle video bhejiye, phir uska file_id do.")
            from .make_tools import _owner_bytes
            name, data = _owner_bytes(ctx, fid)
            r = await cs.dub(data, name, a.get("languages") or [], a.get("keep_sound", True) is not False)
            made = []
            for o in r["outputs"]:
                stem = name.rsplit(".", 1)[0][:30]
                v = _store(ctx, f"{stem} · {o['language']} dub", ".mp4", o["bytes"], "dub",
                           {"language": o["language"], "seconds": o["seconds"]})
                made.append({"language": o["language"], "file_id": v["file_id"], "name": v["name"]})
            return {"status": "done", "made": made, "source_language": r["source_language"],
                    "speakers": r["speakers"], "voices": r["voices"], "lines": len(r["lines"]),
                    "note": ("Dub ban gaye, har bhasha ka card chat mein. Bata do: awaaz milti-julti hai (clone nahi), "
                             "honth dobara sync nahi hue - lip sync Video Studio mein paid card se.")}
    except cs.CreateError as e:
        raise ToolError(str(e) + " (Dobara mat try karo; unhe yahi bata do.)")
    raise ToolError("action: song | voice | dub | voices")


CREATE_HANDLERS = {"create_studio": create_studio}
