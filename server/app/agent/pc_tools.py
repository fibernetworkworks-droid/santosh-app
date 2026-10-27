"""Mera PC tools: the user's office/home computer through Santosh Desktop (files, printing, TallyPrime)."""
from __future__ import annotations

import asyncio

from ..bazar import service
from ..bazar.connectors.base import ToolError as BazarError
from ..bazar.connectors.pc import SCHEMAS
from ..config import get_settings
from .tools import Ctx, ToolError

PACK = "pc-bridge"

_NAMES = {"pc_status": "status", "pc_search": "search", "pc_list": "list", "pc_read": "read",
          "pc_send_to_phone": "send_file", "pc_print": "print", "tally_report": "tally_report", "tally_entry": "tally_voucher"}

PC_TOOLS = [{"name": api, "description": "[HER PC - say 'aapka PC'] " + SCHEMAS[tool][0], "input_schema": SCHEMAS[tool][1]}
            for api, tool in _NAMES.items()]

PC_LABELS = {"pc_status": "PC dekh raha hoon", "pc_search": "PC par file dhoondh raha hoon", "pc_list": "PC ka folder dekh raha hoon",
             "pc_read": "File padh raha hoon", "pc_send_to_phone": "File phone par bhej raha hoon",
             "pc_print": "Print taiyar kar raha hoon", "tally_report": "Tally dekh raha hoon", "tally_entry": "Tally entry taiyar kar raha hoon"}


def _handler(api: str):
    tool = _NAMES[api]

    async def h(ctx: Ctx, **args):
        try:
            return await asyncio.to_thread(service.run, ctx.tenant_id, ctx.conversation_id, PACK, tool, args)
        except BazarError as e:
            raise ToolError(str(e))
    return h


PC_HANDLERS = {api: _handler(api) for api in _NAMES}


# ---- Santosh uses the PC like a person (Santosh PC Operator) ----
PC_TOOLS.append({"name": "pc_do", "description": (
    "[HER PC - say 'aapka PC', never 'mera PC'] Santosh uses the user's OWN computer like a person: sees the screen, "
    "opens apps, clicks, types, presses keys, to finish a task end to end in ANY desktop app (Tally, Excel, Word, "
    "Chrome ON HER PC, Busy, Marg, email apps, any software). Use when the user wants something DONE on HER PC that the "
    "file/Tally tools can't do: 'Excel mein sales sheet banao', 'Tally kholo aur ledger dikhao', 'mere PC pe Chrome mein "
    "IRCTC kholo', 'laptop pe yeh site kholo', 'Word mein letter likho'. A website job she did NOT put on her PC goes to "
    "your own browser (browse_web / computer_operator), not here. "
    "Describe the full goal with every detail. The user watches it live; it asks on the phone before sending, "
    "submitting, deleting, paying, installing or changing settings, and never types passwords/OTPs. Needs 'Santosh "
    "ko PC chalane dein' switched on in Santosh Desktop. Slow (a few seconds per step)."),
    "input_schema": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}})
PC_TOOLS.append({"name": "pc_task_result", "description": "[HER PC] Status or result of a pc_do task (session_id).",
                 "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}})
PC_LABELS.update({"pc_do": "Aapke PC par kaam kar raha hoon", "pc_task_result": "Aapke PC ka kaam dekh raha hoon"})


# ---- v0.193 HOOLA KA APNA PC: the Linux cloud computer that belongs to Hoola (the coworker VM) ----
PC_TOOLS.append({"name": "hoola_pc_do", "description": (
    "[HOOLA KA APNA PC - the cloud computer that belongs to YOU, the coworker] Hoola uses its OWN Linux computer "
    "in the cloud like a person: sees the screen, opens apps, clicks, types, INSTALLS SOFTWARE (apt/pip, no "
    "permission needed - it is Hoola's own VM) and runs shell commands. Use when the job needs a computer that "
    "is NOT her PC: software she does not have installed ('ffmpeg se video compress karo', 'LibreOffice mein "
    "sheet banao', 'pandoc se convert karo'), heavy/clean work, a second browser session, downloads that should "
    "not touch her laptop, or anything where the user said 'aapke computer pe / tumhare PC pe / Hoola ke PC pe'. "
    "Her-PC jobs ('mere PC pe') stay with pc_do; quick web look-ups stay with browse_web. Chromium is Chrome here; "
    "files live in /data. Same safety rules as pc_do for anything that leaves the VM (sends, submits, pays). "
    "Describe the full goal with every detail. The user watches it live; it asks on the phone before sending, "
    "submitting, deleting or paying, and never types passwords/OTPs. Slow (a few seconds per step)."),
    "input_schema": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}})
PC_LABELS.update({"hoola_pc_do": "Hoola ke apne PC par kaam kar raha hoon"})


async def hoola_pc_do(ctx: Ctx, task, _wait=None, **_):
    from ..pc import operator
    from ..pc.hub import HOOLA_PC_KIND
    task = str(task or "").strip()
    if len(task) < 3:
        raise ToolError("Batayiye Hoola ke PC par kya karna hai")
    try:
        r = await operator.start(ctx.tenant_id, ctx.conversation_id, task, kind=HOOLA_PC_KIND,
                                 wait=get_settings().pc_wait_seconds if _wait is None else float(_wait))
    except RuntimeError as e:
        if "HOOLA_PC_OFFLINE" in str(e):
            raise ToolError("Hoola ka apna PC abhi online nahi hai. Thodi der baad boliye.")
        if "PC_OFFLINE" in str(e):
            raise ToolError("Hoola ka apna PC abhi online nahi hai. Thodi der baad boliye.")
        raise ToolError(str(e))
    r.pop("timeline", None)
    r.setdefault("where", "Hoola ka apna PC (the cloud computer owned by Hoola, Linux + Chromium)")
    if r["status"] in ("running", "needs_confirm"):
        r["say"] = ("Still working on Hoola ke apne PC (live card in chat; a confirm card appears if a step needs "
                    "approval). The result is posted automatically; if asked before that, call pc_task_result with "
                    f"session_id '{r['session_id']}'.")
    return r


async def pc_do(ctx: Ctx, task, _wait=None, **_):
    from ..pc import operator
    task = str(task or "").strip()
    if len(task) < 3:
        raise ToolError("Batayiye PC par kya karna hai")
    try:
        r = await operator.start(ctx.tenant_id, ctx.conversation_id, task, wait=get_settings().pc_wait_seconds if _wait is None else float(_wait))
    except PermissionError as e:
        raise ToolError(str(e))
    except RuntimeError as e:
        if "PC_OFFLINE" in str(e):
            raise ToolError("Aapka PC offline hai. PC on karke Santosh Desktop kholiye (ya Santosh app > Mera PC se jodiye).")
        raise ToolError(str(e))
    r.pop("timeline", None)
    r.setdefault("where", "Aapka PC (HER computer, Santosh Desktop) - not your own browser")
    if r["status"] in ("running", "needs_confirm"):
        r["say"] = ("Still working on the PC (live card in chat; a confirm card appears if a step needs approval). The "
                    "result is posted automatically; if asked before that, call pc_task_result with session_id "
                    f"'{r['session_id']}'.")
    return r


async def pc_task_result(ctx: Ctx, session_id, **_):
    from ..pc import operator
    op = operator.get(ctx.tenant_id, str(session_id))
    if op is None:
        raise ToolError("That PC task isn't available any more.")
    if not op.done_event.is_set():
        try:
            await asyncio.wait_for(asyncio.shield(op.done_event.wait()), 4)
        except asyncio.TimeoutError:
            pass
    r = op.live()
    r.pop("timeline", None)
    return r


PC_HANDLERS.update({"pc_do": pc_do, "pc_task_result": pc_task_result, "hoola_pc_do": hoola_pc_do})
