"""v0.136 kaam_status: the REAL live state of every long job Hoola started (chat + calls)."""
from __future__ import annotations

import asyncio

from .tools import Ctx

KAAM_TOOLS = [
    {"name": "kaam_status", "description": (
        "The LIVE state of her long jobs, read from the jobs themselves right now: app design / Android build, website, "
        "video edit, Video Studio, motion reel, website jobs in your own browser (Computer Operator). Each job: working "
        "(with what it is doing now and %), waiting (HER tap / answer needed and for what), done, failed (with the error) "
        "or stopped, and how many minutes since it last moved. Use it whenever she asks 'kya hua / kitna hua / ho gaya? / "
        "kahan tak pahuncha' or before you say anything about a running job. NEVER say 'dekh raha hoon / check kar raha "
        "hoon' without calling this (or the KAAM KI HAALAT list) and telling her the real state. q = optional words to "
        "pick one job (app, website, video, number). action=stop REALLY cancels it (her 'roko / cancel karo / band karo / "
        "rehne do' about running work): q = her words naming the job ('website wala'), empty = the newest, 'sab' = all. "
        "NEVER say a job is cancelled / roka / band without action=stop returning it in `stopped`; if `stopped` is empty, "
        "say plainly that nothing was stopped and why. action=cards lists the cards (approve / send / pay) that really "
        "still wait for her tap, with their own latest state - read it before you tell her a card is waiting."),
     "input_schema": {"type": "object", "properties": {"q": {"type": "string"},
                                                       "action": {"type": "string", "enum": ["status", "stop", "cards"]}}}},
]
KAAM_LABELS = {"kaam_status": "Kaam ki haalat dekh raha hoon"}


async def kaam_status(ctx: Ctx, q: str = "", action: str = "status", **_):
    if action == "stop":   # v0.649 SACH MEIN ROKO: the real cancel (never the turn this tool runs in)
        from .. import kaamstop
        return await asyncio.to_thread(kaamstop.cancel, ctx.tenant_id, str(q or "")[:200], ctx.conversation_id,
                                       ctx.conversation_id)
    if action == "cards":   # parity Phase 2: the waiting cards are fetched, no longer pasted into every prompt
        from .. import events
        txt = await asyncio.to_thread(events.cards_block, ctx.tenant_id)
        return {"cards": txt or "No card is waiting for her tap."}
    from .. import kaamwatch
    # v0.722 a wake turn (a finished job reporting itself) reads only its own chat's jobs - her whole desk once came back
    # as "Open projects on your desk" under a question that had nothing to do with them
    conv = ctx.conversation_id if ctx.actor == "wake" else ""
    return await asyncio.to_thread(kaamwatch.status, ctx.tenant_id, str(q or "")[:80], conv)


KAAM_HANDLERS = {"kaam_status": kaam_status}
