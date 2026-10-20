"""Tool `employee`: Hoola's job in the owner's business (v0.58). Pause / resume, status, today's report, job sheet,
waiting asks, trust per duty; and, for a team member's own Hoola, sending a task to the workplace's Hoola."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

EMPLOYEE_TOOLS = [
    {"name": "employee", "description": (
        "Hoola Employee: your job in the owner's business. action=status (is it on, paused, what waits for her), "
        "pause (the owner says ruk jao / kaam roko / sab band: stops every job action at once), resume (only the owner), "
        "report (today's work report), job_sheet (what you do and never do), asks (actions waiting for her Haan), "
        "trust (change how far you may go alone in one duty: level seekh | saathi | bharosa; only when the owner clearly "
        "says so), send_task (the owner works somewhere: send a task to her workplace's Hoola, to = their Hoola ID)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["status", "pause", "resume", "report", "job_sheet", "asks", "trust", "send_task"]},
         "duty": {"type": "string", "description": "trust: customers, appointments, reminders, email, tickets, collections, records, campaigns, research"},
         "level": {"type": "string", "enum": ["seekh", "saathi", "bharosa"]},
         "to": {"type": "string", "description": "send_task: the workplace Hoola ID (name@server) or a connection's name"},
         "text": {"type": "string", "description": "send_task: the task in plain words"}},
         "required": ["action"]}},
]
EMPLOYEE_LABELS = {"employee": "Naukri ka hisaab dekh raha hoon"}


async def employee(ctx: Ctx, action: str = "status", duty: str = "", level: str = "", to: str = "", text: str = "", **_) -> dict[str, Any]:
    from ..employee import service as emp
    owner = (ctx.actor or "owner") == "owner"
    try:
        if action == "status":
            return emp.status(ctx.tenant_id)
        if action == "pause":
            p = await asyncio.to_thread(emp.set_pause, ctx.tenant_id, True, ctx.actor or "owner")
            return {"paused": p["paused"], "note": "Naukri ke saare kaam ruk gaye. Owner 'kaam shuru' kahe ya app mein dabaye tab chalenge."}
        if not owner and action not in ("report", "job_sheet"):
            raise ToolError("Yeh sirf owner kar sakti / sakta hai.")
        if action == "resume":
            p = await asyncio.to_thread(emp.set_pause, ctx.tenant_id, False, "owner")
            return {"paused": p["paused"]}
        if action == "report":
            r = await asyncio.to_thread(emp.report, ctx.tenant_id)
            return {"text": r["text"], "pending": r["pending"]}
        if action == "job_sheet":
            return {"text": emp.job_sheet(ctx.tenant_id)["text"][:3000]}
        if action == "asks":
            return {"waiting": [{k: a[k] for k in ("what", "who", "why", "detail")} for a in emp.asks(ctx.tenant_id)[:10]],
                    "note": "Haan / Mana owner app ke card se deti hain (Profile > Hoola Employee)."}
        if action == "trust":
            if not duty or not level:
                raise ToolError("duty aur level dono chahiye.")
            t = await asyncio.to_thread(emp.set_trust, ctx.tenant_id, duty, level)
            return {"duty": t["label"], "level": t["level_label"]}
        if action == "send_task":
            from ..employee import network
            from ..net.service import NetError
            try:
                return await asyncio.to_thread(network.send_task, ctx.tenant_id, to, text)
            except NetError as e:
                raise ToolError(str(e))
    except emp.EmployeeError as e:
        raise ToolError(str(e))
    raise ToolError("action: status, pause, resume, report, job_sheet, asks, trust, send_task")


EMPLOYEE_HANDLERS = {"employee": employee}
