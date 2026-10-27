"""v0.65 Tool `video_edit`: Hoola as the owner's video editor (Reels, Shorts, WhatsApp status, YouTube)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

VIDEO_TOOLS = [
    {"name": "video_edit", "description": (
        "Edit the owner's own videos / photos like a professional editor: Instagram Reel, YouTube Short, WhatsApp "
        "status, YouTube video, square / 4:5 post. You watch the footage, pick the best moments, cut pauses and "
        "mistakes, add on-screen text, burned-in captions (Hindi / Hinglish / English), her logo and music, level the "
        "sound, then check the result yourself before she gets it, plus a post caption and hashtags. "
        "action=start (file_ids of attached videos / photos IN ORDER, brief = what she wants in her words, platform "
        "reel|short|status|youtube|square|portrait|same, length_s, captions true/false, logo_file_id, music_file_id, "
        "title) -> runs in the background (1-5 min); a card shows progress and the finished video; don't wait or poll. "
        "action=revise (job_id, instruction: her change in her words, e.g. 'title bada karo', 'pehle 3 sec hatao', "
        "'music dheemi') -> a new version. status / list / cancel. Never posts anything anywhere: she shares it herself. "
        "Only her own files; no downloading other people's videos. Ask for the video if none is attached."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["start", "revise", "status", "list", "cancel"]},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "brief": {"type": "string"},
         "platform": {"type": "string", "enum": ["reel", "short", "status", "youtube", "square", "portrait", "same"]},
         "length_s": {"type": "integer"},
         "captions": {"type": "boolean"},
         "logo_file_id": {"type": "string"},
         "music_file_id": {"type": "string"},
         "title": {"type": "string"},
         "job_id": {"type": "string", "description": "Defaults to the latest job"},
         "instruction": {"type": "string"}},
         "required": ["action"]}},
]
VIDEO_LABELS = {"video_edit": "Video edit kar raha hoon"}


def _short(v: dict[str, Any]) -> dict[str, Any]:
    out = {k: v.get(k) for k in ("id", "status", "stage", "progress", "platform_label", "title", "notes", "post_caption",
                                 "hashtags", "error", "pending")}
    out["versions"] = [{k: x.get(k) for k in ("n", "file_id", "duration", "size", "change")} for x in v.get("versions") or []]
    return {k: val for k, val in out.items() if val not in (None, "", [])}


def _run(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..videoedit import service as vs
    try:
        if action == "start":
            v = vs.start(ctx.tenant_id, a.get("file_ids") or [], a.get("brief") or "", a.get("platform") or "reel",
                         a.get("length_s"), a.get("captions", True) is not False, a.get("logo_file_id") or "",
                         a.get("music_file_id") or "", a.get("title") or "", ctx.conversation_id,
                         created_by=getattr(ctx, "actor", "owner") or "owner")
            return {"job_id": v["id"], "status": v["status"], "platform": v["platform_label"],
                    "say": "Edit shuru ho gaya: card mein progress dikhega aur video taiyaar hote hi yahin aa jayegi "
                           "(1-5 minute). Tab tak kuch aur poochh sakti hain.",
                    "note_for_you": "Do not poll; the finished video arrives as a card + message by itself."}
        job = a.get("job_id") or vs.latest_id(ctx.tenant_id)
        if action == "list":
            return {"jobs": [_short(v) for v in vs.listing(ctx.tenant_id, 10)]}
        if not job:
            raise ToolError("Abhi koi video job nahi hai.")
        if action == "status":
            return _short(vs.get(ctx.tenant_id, job))
        if action == "revise":
            v = vs.revise(ctx.tenant_id, job, a.get("instruction") or "")
            return {"job_id": v["id"], "status": v["status"],
                    "say": "Badlav shuru: naya version card mein aayega (pehle wale clips cache se, isliye jaldi)."}
        if action == "cancel":
            return _short(vs.cancel(ctx.tenant_id, job))
    except vs.VideoError as e:
        raise ToolError(str(e))
    raise ToolError("action = start | revise | status | list | cancel")


async def video_edit(ctx: Ctx, action, **a):
    return await asyncio.to_thread(_run, ctx, str(action), a)


VIDEO_HANDLERS = {"video_edit": video_edit}
