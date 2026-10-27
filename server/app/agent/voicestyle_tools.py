"""v0.119 tool: hoola_seekha - what Hoola learned about how she speaks (language, pace, pauses, tone, her words, words it
misheard before), and her changes to it. Numbers and words only; never audio."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SEEKHA_TOOLS = [
    {"name": "hoola_seekha", "description": (
        "What you learned about how SHE speaks on calls, and her changes to it. action=show: her language, pace, how long "
        "you wait before answering (from her own pauses), tone, her yes-words, the names / words you keep for her, and the "
        "words you misheard before ('heard -> meant'). add_word: a name / word you must hear right (term: 'Rameshwar', "
        "'Bisleri', 'Kothrud'). add_fix: she tells you a word you keep mishearing (heard = what you heard / said wrong, "
        "meant = the right word). remove_word / remove_fix (id), confirm_fix (id). learn_off / learn_on: stop / start "
        "learning from her calls. forget (part all | profile | fixes | words | language). Only her; never another person's "
        "voice. You cannot copy her accent or voice and must never claim to."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["show", "add_word", "remove_word", "add_fix", "remove_fix", "confirm_fix",
                                               "learn_on", "learn_off", "forget"]},
         "term": {"type": "string"}, "heard": {"type": "string"}, "meant": {"type": "string"},
         "id": {"type": "integer"}, "part": {"type": "string", "enum": ["all", "profile", "fixes", "words", "language"]}},
         "required": ["action"]}},
]
SEEKHA_LABELS = {"hoola_seekha": "Aapke bolne ka tareeka dekh raha hoon"}


def _owner(ctx: Ctx) -> bool:
    return ctx.actor in ("owner",) or str(ctx.actor).startswith("approved:")


async def hoola_seekha(ctx: Ctx, action: str, term: str = "", heard: str = "", meant: str = "", id: int = 0,
                       part: str = "all", **_) -> dict[str, Any]:
    from .. import voicestyle as vs
    t = ctx.tenant_id
    if action != "show" and not _owner(ctx):
        raise ToolError("Sirf maalkin yeh badal sakti hain")
    try:
        if action == "show":
            v = await asyncio.to_thread(vs.view, t)
            v["say"] = await asyncio.to_thread(vs.say, t)
            v.pop("vocab", None)
            return v
        if action == "add_word":
            return {"ok": True, **await asyncio.to_thread(vs.add_word, t, term, "her")}
        if action == "remove_word":
            return {"ok": await asyncio.to_thread(vs.remove_word, t, int(id))}
        if action == "add_fix":
            return {"ok": True, **await asyncio.to_thread(vs.note_fix, t, heard, meant, True)}
        if action == "remove_fix":
            return {"ok": await asyncio.to_thread(vs.remove_fix, t, int(id))}
        if action == "confirm_fix":
            return {"ok": True, **await asyncio.to_thread(vs.confirm_fix, t, int(id))}
        if action in ("learn_on", "learn_off"):
            return {"ok": True, **await asyncio.to_thread(vs.set_learn, t, action == "learn_on")}
        if action == "forget":
            return {"ok": True, **await asyncio.to_thread(vs.forget, t, part)}
    except vs.StyleError as e:
        raise ToolError(str(e))
    raise ToolError(f"Unknown action {action}")


SEEKHA_HANDLERS = {"hoola_seekha": hoola_seekha}
