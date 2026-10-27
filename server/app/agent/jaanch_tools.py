"""v0.92 Tool `hoola_jaanch`: Hoola checks itself (every part, live) and reports the last 14 days of real work."""
from __future__ import annotations

from .tools import Ctx, ToolError

JAANCH_TOOLS = [
    {"name": "hoola_jaanch", "description": (
        "Check yourself: action=check runs a live health check of every part (brain, voice, search, email route, "
        "website operator, browser, her PC, notifications, Google, disk, and which government / daily websites open "
        "from the server) and says what is broken with the fix; action=report = the last 14 days of real work (tasks "
        "done / stuck, website jobs, lessons, crashes). Use it when she asks 'kya kharab hai', 'Hoola theek hai?', "
        "'kaam kyun nahi ho raha', or before telling her a feature is broken. Read out the broken parts and their fixes "
        "in plain short lines."),
     "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["check", "report"]}},
                      "required": ["action"]}},
]
JAANCH_LABELS = {"hoola_jaanch": "Apni jaanch kar raha hoon"}


async def hoola_jaanch(ctx: Ctx, action="check", **_):
    import asyncio

    from .. import jaanch
    if action == "report":
        return await asyncio.to_thread(jaanch.report, ctx.tenant_id)
    if action != "check":
        raise ToolError("action = check | report")
    r = await jaanch.run(ctx.tenant_id)
    r["checks"] = [c for c in r["checks"] if c["ok"] is not True] or [{"name": "sab", "ok": True}]
    r["report"] = {k: r["report"].get(k) for k in ("chat", "website", "crashes")}
    return r


JAANCH_HANDLERS = {"hoola_jaanch": hoola_jaanch}
