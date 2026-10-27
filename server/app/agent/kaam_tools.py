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
        "pick one job (app, website, video, number)."),
     "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}}},
]
KAAM_LABELS = {"kaam_status": "Kaam ki haalat dekh raha hoon"}


async def kaam_status(ctx: Ctx, q: str = "", **_):
    from .. import kaamwatch
    return await asyncio.to_thread(kaamwatch.status, ctx.tenant_id, str(q or "")[:80])


KAAM_HANDLERS = {"kaam_status": kaam_status}
