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
        "video_edit. One short line after: what was made; the card shows it. "
        "action=image (the Create > Image page's own chat only): pictures made on her Create shelf, so they appear in Your "
        "pictures and as a set in this chat - prompt = one rich picture description you write from her words (subject, place, "
        "light, mood, any words to print on it exactly as she gave them), aspect 1:1|4:5|9:16|16:9|3:4|4:3, style, quality "
        "fast|best, count 1-4, file_ids = her reference pictures, title. It starts at once and returns; never say the pictures "
        "are ready, the set in the chat shows them when they are. "
        "In the Create > Music page's own chat only: action=song also takes versions (1-4) and keep_out, and runs on her "
        "Create shelf (each version appears in the chat by itself); action=song_edit changes a song made there - id = its "
        "id (cr_...), steps = audio steps in order (trim{start,end} cut{start,end} fade{in,out} volume{db} "
        "normalize{target} speed{factor} pitch{semitones} eq{bass,treble} denoise{strength} reverse), title - free, at once, "
        "saved as a new version with the old one kept. "
        "In the Hoola Vocal page's own chat only (v0.999.90): action=voice makes speech on her Vocal shelf in ANY language - "
        "text (feelings in square brackets allowed: [warm] [whispers] [laughs] [sighs] [excited] [serious] [slowly] [cheerful] "
        "[pause]), voice = a voice id from the Vocal list below (hv_... / gx_... / ev_... / mv_...) or empty, language = a "
        "language code or name or 'auto', style, speed 0.7-1.3, takes 1-4, engine auto|gemini|eleven; action=dialogue: "
        "lines [{speaker, text}] + cast {speaker: voice id}, language, reactions true = short listener sounds between long lines, "
        "music 'soft' = a quiet music bed under it (free); action=sound: a sound effect from words, prompt, "
        "seconds 0-30, loop, takes 1-4. Each take appears in the chat by itself; never say it is ready."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["song", "voice", "dub", "voices", "image", "song_edit", "dialogue", "sound"]},
         "versions": {"type": "integer"}, "keep_out": {"type": "string"}, "id": {"type": "string"},
         "steps": {"type": "array", "items": {"type": "object"}},
         "brief": {"type": "string"}, "genre": {"type": "string"}, "language": {"type": "string"},
         "vocals": {"type": "string"}, "mood": {"type": "string"}, "bpm": {"type": "integer"}, "seconds": {"type": "integer"},
         "lyrics": {"type": "string"}, "text": {"type": "string"}, "voice": {"type": "string"}, "style": {"type": "string"},
         "speed": {"type": "number"}, "file_id": {"type": "string"},
         "languages": {"type": "array", "items": {"type": "string"}}, "keep_sound": {"type": "boolean"},
         "title": {"type": "string"}, "prompt": {"type": "string"}, "aspect": {"type": "string"},
         "quality": {"type": "string"}, "count": {"type": "integer"},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "takes": {"type": "integer"}, "engine": {"type": "string"}, "loop": {"type": "boolean"},
         "lines": {"type": "array", "items": {"type": "object"}}, "cast": {"type": "object"},
         "reactions": {"type": "boolean"}, "music": {"type": "string", "enum": ["", "soft"]}},
         "required": ["action"]}},
]
CREATE_LABELS = {"create_studio": "Creating in Create Studio"}


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
    if action == "image":
        return await _image(ctx, a)
    if action == "song_edit":
        return await _song_edit(ctx, a)
    if action == "song" and _in_music(ctx):
        return await _song_job(ctx, a)
    if action in ("voice", "dialogue", "sound") and _in_vocal(ctx):
        return await _vocal(ctx, action, a)
    try:
        if action == "song":
            r = await cs.song(a.get("brief") or "", a.get("genre") or "", a.get("language") or "Auto",
                              a.get("vocals") or "duet", a.get("mood") or "", int(a.get("bpm") or 0),
                              int(a.get("seconds") or 0), a.get("lyrics") or "")
            title = a.get("title") or (a.get("brief") or a.get("genre") or "Hoola song")[:40]
            v = _store(ctx, title, r["ext"], r["bytes"], "song", {"genre": a.get("genre") or "", "language": a.get("language") or ""})
            return {"status": "done", "file_id": v["file_id"], "name": v["name"], "about_inr": 7,
                    "note": "The song is ready; she can listen / download it on the card in the chat. Tell her in one line."}
        if action == "voice":
            r = await cs.voice(a.get("text") or "", a.get("voice") or "", a.get("language") or "Hindi",
                               a.get("style") or "friendly", float(a.get("speed") or 1.0), ctx.tenant_id)
            title = a.get("title") or ("Voice-over · " + r["voice"])
            v = _store(ctx, title, r["ext"], r["bytes"], "voice", {"voice": r["voice"], "seconds": r["seconds"]})
            return {"status": "done", "file_id": v["file_id"], "name": v["name"], "voice": r["voice"], "seconds": r["seconds"]}
        if action == "dub":
            fid = str(a.get("file_id") or "").strip()
            if not fid:
                raise ToolError("Which video should be dubbed? Send the video first, then give its file_id.")
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
                    "note": ("The dubs are ready, one card per language in the chat. Tell her: the voice is similar (not a clone), "
                             "lips were not re-synced - lip sync is in Video Studio via a paid card.")}
    except cs.CreateError as e:
        raise ToolError(str(e) + " (Do not try again; tell her this.)")
    raise ToolError("action: song | voice | dub | voices | image")


ASPECTS = ("1:1", "4:5", "9:16", "16:9", "3:4", "4:3")


async def _image(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    """v0.999.51 IMAGE CHAT: the pictures go through the Image page's own engine (create/jobs), so they land on her shelf
    (Your pictures) and the job's set shows in this chat. Starts and returns; the page follows the job."""
    from ..create import jobs, service as cs
    prompt = str(a.get("prompt") or a.get("brief") or "").strip()
    if not prompt:
        raise ToolError("Write the picture description in prompt first.")
    if cs.ready().get("image") is False:
        raise ToolError((cs.NEED.get("image") if isinstance(cs.NEED, dict) else "") or
                        "The picture engine is not set up on the server. (Do not try again; tell her this.)")
    aspect = str(a.get("aspect") or "1:1").strip()
    aspect = aspect if aspect in ASPECTS else "1:1"
    quality = "best" if str(a.get("quality") or "").lower() in ("best", "high") else "fast"
    count = max(1, min(int(a.get("count") or 1), 4))
    fids = [str(f) for f in (a.get("file_ids") or []) if str(f).strip()][:3]
    params = {"prompt": prompt[:4000], "aspect": aspect, "quality": quality, "count": count,
              "style": str(a.get("style") or "")[:60], "file_ids": fids, "title": str(a.get("title") or prompt[:48])[:80]}
    try:
        j = jobs.start(ctx.tenant_id, "image", params, ctx.conversation_id)
    except jobs.JobError as e:
        raise ToolError(str(e))
    each = 12 if quality == "best" else 3
    return {"status": "making", "job": j["id"], "count": count, "aspect": aspect, "about_inr": each * count,
            "note": (f"{count} picture{'s are' if count > 1 else ' is'} being made now (about 15 seconds each). The set "
                     "appears in this chat by itself. Say that in one short line; do not say they are ready.")}


def _in_vocal(ctx: Ctx) -> bool:
    try:
        from .. import vocalchat
        return vocalchat.is_vocal(ctx.conversation_id)
    except Exception:   # noqa: BLE001
        return False


async def _vocal(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    """v0.999.90 HOOLA VOCAL GLOBAL: speech, dialogue and sounds asked in the Vocal page's chat go to her Vocal shelf; each
    take is a row the chat shows by itself (GET /api/vocal/chat/{conv}/items)."""
    import asyncio
    from ..vocal import service as V
    conv = ctx.conversation_id
    try:
        if action == "voice":
            r = await V.tts(ctx.tenant_id, a.get("text") or "", voice=str(a.get("voice") or ""),
                            lang=str(a.get("language") or "auto"), style=str(a.get("style") or "friendly"),
                            speed=a.get("speed") or 1.0, takes=a.get("takes") or 2, engine=str(a.get("engine") or "auto"),
                            chat=conv)
            return {"status": "made", "takes": len(r["items"]), "language": r["lang_name"], "voice": r["voice_name"],
                    "credits": r["credits"], "ids": [x["id"] for x in r["items"]],
                    "note": "The takes are in the chat now. Say in one short line which language and voice; never read the words back."}
        if action == "dialogue":
            r = await V.dialogue(ctx.tenant_id, a.get("lines") or [], a.get("cast") or {}, lang=str(a.get("language") or "auto"),
                                 chat=conv, reactions=bool(a.get("reactions")), music=str(a.get("music") or ""))
            return {"status": "made", "id": r["id"], "seconds": r["seconds"], "voices": r["voice_name"],
                    "note": "The dialogue is in the chat now. One short line."}
        r = await asyncio.to_thread(V.sfx_text, ctx.tenant_id, a.get("prompt") or a.get("text") or "", a.get("seconds") or 0,
                                    bool(a.get("loop")), a.get("takes") or 4, conv)
        return {"status": "made", "takes": len(r["items"]), "credits": r["credits"],
                "note": "The sound takes are in the chat now. One short line."}
    except V.VocalError as e:
        raise ToolError(str(e) + " (Do not try again with the same values; tell her this plainly.)")


def _in_music(ctx: Ctx) -> bool:
    try:
        from .. import musicchat
        return musicchat.is_music(ctx.conversation_id)
    except Exception:   # noqa: BLE001
        return False


async def _song_job(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    """v0.999.79 HOOLA MUSIC: a song asked in the Music page's chat goes through the Create shelf (create/jobs), so its
    versions land in Your songs and as a set in this chat. Starts and returns; the page follows the job."""
    from ..create import jobs, service as cs
    if not (str(a.get("brief") or "").strip() or str(a.get("lyrics") or "").strip() or str(a.get("genre") or "").strip()):
        raise ToolError("Write what the song is about in brief (or give lyrics / a genre) first.")
    if cs.ready().get("song") is False:
        raise ToolError(cs.NEED.get("song", "The music engine is not set up on the server.") + " (Do not try again; tell her this.)")
    n = max(1, min(int(a.get("versions") or 2), 4))
    params = {k: a.get(k) for k in ("brief", "genre", "language", "vocals", "mood", "bpm", "seconds", "lyrics", "keep_out")}
    params.update(versions=n, title=str(a.get("title") or a.get("brief") or a.get("genre") or "Hoola song")[:48],
                  language=str(a.get("language") or "Auto"), vocals=str(a.get("vocals") or "duet"))
    try:
        j = jobs.start(ctx.tenant_id, "song", params, ctx.conversation_id)
    except jobs.JobError as e:
        raise ToolError(str(e))
    return {"status": "making", "job": j["id"], "versions": n, "about_inr": 7 * n, "credits": 80 * n,
            "note": (f"{n} version{'s are' if n > 1 else ' is'} being made now (about a minute each). They appear in this chat "
                     "by themselves. Say that in one short line in her language; do not say they are ready.")}


async def _song_edit(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    """v0.999.79 HOOLA MUSIC: a free change to a song on her shelf (ffmpeg on the server) saved as a NEW version; the song
    it came from stays, so Undo = the earlier version."""
    import asyncio
    import tempfile
    from pathlib import Path
    from ..audedit import ops
    from ..create import jobs
    sid = str(a.get("id") or a.get("file_id") or "").strip()
    if not sid.startswith("cr_"):
        raise ToolError("Give id = the song's id from the songs in this chat (cr_...).")
    try:
        path, it = jobs.item_file(ctx.tenant_id, sid)
    except jobs.JobError as e:
        raise ToolError(str(e))
    if it.get("kind") != "song":
        raise ToolError("That id is not a song.")
    steps = a.get("steps") or []
    if not isinstance(steps, list) or not steps:
        raise ToolError("Give steps, e.g. [{\"op\":\"trim\",\"start\":42,\"end\":72},{\"op\":\"fade\",\"out\":2}].")
    if not ops.ffmpeg_ok():
        raise ToolError("ffmpeg is not on the server, so the song cannot be changed right now. (Do not try again; tell her this.)")
    try:
        ops.chain(steps, 3600.0, 48000)
        r = await asyncio.to_thread(ops.edit, str(path), steps, "mp3", None)
    except ops.AudioError as e:
        raise ToolError(str(e))
    m = dict(it.get("meta") or {})
    what = ", ".join(str(s.get("op")) for s in steps if isinstance(s, dict))[:120]
    secs = round(float(r.get("est_seconds") or 0), 1)
    meta = {k: m.get(k) for k in ("genre", "language", "vocals", "mood", "lyrics", "brief", "bpm") if m.get(k)}
    meta.update(parent=sid, edit=what, steps=steps[:20], seconds=secs, inr=0, credits=0, ai=True, version="",
                job=new_job_id(), **({"chat": ctx.conversation_id} if ctx.conversation_id else {}))
    title = str(a.get("title") or "").strip() or (it.get("title") or "Song")[:60] + " · edited"
    new = await asyncio.to_thread(jobs.keep, ctx.tenant_id, "song", title[:80], "." + r["ext"], r["bytes"], meta)
    return {"status": "done", "id": new["id"], "title": new["title"], "seconds": secs, "from": sid, "steps": r.get("steps") or what,
            "note": "Free. The new version is in the chat and in Your songs; the earlier one is kept. Say what changed in one line."}


def new_job_id() -> str:
    from ..db import new_id
    return new_id("ce")


CREATE_HANDLERS = {"create_studio": create_studio}
