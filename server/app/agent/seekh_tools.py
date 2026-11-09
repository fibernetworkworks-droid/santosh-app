"""v0.713 SEEKH MANCH: tool `seekh_video` - learn a way of working by WATCHING a video (a YouTube link /
Shorts, a video the owner attached, or a direct video URL). The perception doors, the two memories and the
recipe replay are organs that already ship; this tool is only the bridge (server/app/seekh.py)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SEEKH_TOOLS = [
    {"name": "seekh_video", "description": (
        "Learn a way of doing something by WATCHING a video: a YouTube link / Shorts, a video the owner "
        "attached (file_id), or a direct video URL. action=watch (video = the link / file_id, title "
        "optional): watch it, write the steps as seen with their [m:ss] timestamps, and keep them as a "
        "learned kaam ('Seekhe hue kaam') - for website work it also becomes a draft recipe the computer "
        "operator may use as a guide. It says what it is unsure about, and never keeps a personal value "
        "from the video (values become fill-in variables). Learned is not proven: the first real run "
        "verifies it. action=status = the last watches. When she says 'isse seekh lo' / 'learn this' on a "
        "video, this is the tool."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["watch", "status"]},
         "video": {"type": "string", "description": "A YouTube link / Shorts / video id, a chat file_id, or a direct video URL"},
         "title": {"type": "string", "description": "Optional name for this way of working"}},
         "required": ["action"]}},
]
SEEKH_LABELS = {"seekh_video": "Video dekh kar seekh raha hoon"}


def _run(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .. import seekh
    if action == "status":
        return seekh.listing(ctx.tenant_id)
    if action != "watch":
        raise ToolError("action = watch | status")
    video = str(a.get("video") or "").strip()
    if not video:
        raise ToolError("Kaunsa video? Link ya chat mein attach kiye video ka file_id dijiye.")
    try:
        return seekh.watch(ctx.tenant_id, video, str(a.get("title") or ""),
                           getattr(ctx, "actor", "owner") or "owner")
    except seekh.SeekhError as e:
        raise ToolError(str(e))


async def seekh_video(ctx: Ctx, action="watch", **a):
    return await asyncio.to_thread(_run, ctx, str(action or "watch"), a)


SEEKH_HANDLERS = {"seekh_video": seekh_video}
