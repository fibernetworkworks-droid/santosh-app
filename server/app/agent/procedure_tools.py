"""Tool `seekhe_kaam`: what Hoola has learned to do (v0.63). The owner can see them, switch one off or make Hoola forget."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

PROCEDURE_TOOLS = [
    {"name": "seekhe_kaam", "description": (
        "Your learned ways of doing multi-step jobs (saved by themselves after a job worked). action=list (what you learned), "
        "off / on (stop or start using one, by id), forget (delete one by id), forget_all (only when the owner clearly says "
        "'sab bhool jao'). The owner can also see and edit them in Profile > Seekhe hue kaam."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "off", "on", "forget", "forget_all"]},
         "id": {"type": "string"}}, "required": ["action"]}},
]
PROCEDURE_LABELS = {"seekhe_kaam": "Seekhe hue kaam dekh raha hoon"}


async def seekhe_kaam(ctx: Ctx, action: str = "list", id: str = "", **_) -> dict[str, Any]:
    from .. import procedures as pr
    if (ctx.actor or "owner") != "owner":
        raise ToolError("Yeh sirf owner dekh / badal sakti / sakta hai.")
    try:
        if action == "list":
            rows = await asyncio.to_thread(pr.listing, ctx.tenant_id)
            return {"learned": [{"id": r["id"], "title": r["title"], "steps": [s["label"] for s in r["steps"]],
                                 "used": r["uses"], "worked": r["wins"], "on": r["active"]} for r in rows[:30]],
                    "total": len(rows)}
        if action in ("off", "on"):
            r = await asyncio.to_thread(pr.update, ctx.tenant_id, id, active=(action == "on"))
            return {"id": r["id"], "title": r["title"], "on": r["active"]}
        if action == "forget":
            await asyncio.to_thread(pr.delete, ctx.tenant_id, id)
            return {"forgotten": id}
        if action == "forget_all":
            return {"forgotten": await asyncio.to_thread(pr.forget_all, ctx.tenant_id)}
    except pr.ProcedureError as e:
        raise ToolError(str(e))
    raise ToolError("action: list, off, on, forget, forget_all")


PROCEDURE_HANDLERS = {"seekhe_kaam": seekhe_kaam}
