"""v0.67 Tool `computer_operator`: Hoola as the owner's computer operator on websites (forms, downloads, status checks,
applications), in its own browser, with her on the phone for OTP / CAPTCHA / passwords / approvals / payments."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

OPERATOR_TOOLS = [
    {"name": "computer_operator", "description": (
        "Do a job ON A WEBSITE for the owner like a cyber-cafe / CSC computer operator, in your own browser where her "
        "logins stay saved: fill online forms and applications (government portals, banks, utilities, exams, insurance, "
        "her own business panels), download certificates / statements / bills / acknowledgements, check application "
        "or order status, book slots, update details, read results into a table. It researches the official help pages, "
        "works step by step, and LEARNS each finished job as a recipe so the next time is fast. "
        "Aadhaar / PAN / voter ID / DL / passport / ration / ABHA / UAN / GSTIN: it fills them like a Seva Kendra, from "
        "her Pehchaan Locker (numbers she gave are saved there automatically; you pass the {id:...} reference), on any "
        "site with no extra tap; every other number too. "
        "It does the whole job itself like a Setu operator (every field, login / next buttons). It asks her on her "
        "phone only for: the OTP the site sends her, the CAPTCHA (it reads it itself, she just confirms), a login password, the "
        "final submit / send / delete (her tap) and payments (she presses pay herself). When a job waits for an OTP / "
        "CAPTCHA and she tells it to you (e.g. on a call), pass it with action=answer, text=<what she said>; never "
        "repeat it back. "
        "action=start (task = the full job in her words with every detail she gave: names, dates, choices, which "
        "account; start_url if known; file_ids of attached documents / photos to upload) -> runs in the background "
        "with a live card; don't wait or poll. status / list / cancel (task_id defaults to the current job), recipes "
        "(what you learned), forget_recipe (name). Only one job at a time. Put ID numbers in the task as their {id:...} "
        "references (whose and which: 'Papa ka Aadhaar {id:..}'); never passwords, OTP, PIN or card numbers. Use browse_web for quick look-ups and reading; this tool is for real "
        "work on a site."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["start", "status", "list", "cancel", "recipes", "forget_recipe", "answer"]},
         "task": {"type": "string"},
         "text": {"type": "string", "description": "action=answer: the OTP / CAPTCHA she just told you"},
         "start_url": {"type": "string"},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "task_id": {"type": "string"},
         "name": {"type": "string", "description": "recipe name for forget_recipe"}},
         "required": ["action"]}},
]
OPERATOR_LABELS = {"computer_operator": "Website par kaam kar raha hoon"}


def _short(v: dict[str, Any]) -> dict[str, Any]:
    out = {k: v.get(k) for k in ("id", "status", "task", "stage", "steps", "site", "summary", "proof", "recipe", "error")}
    out["files"] = [o.get("name") for o in v.get("outputs") or [] if o.get("file_id")]
    if v.get("pending"):
        out["waiting_for_owner"] = (v["pending"] or {}).get("reason")
    return {k: val for k, val in out.items() if val not in (None, "", [], 0)}


def _run(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..operator import service as ops
    try:
        if action == "start":
            v = ops.start(ctx.tenant_id, a.get("task") or "", a.get("start_url") or "", a.get("file_ids") or [],
                          ctx.conversation_id, created_by=getattr(ctx, "actor", "owner") or "owner")
            return {"task_id": v["id"], "status": v["status"],
                    "say": "Kaam shuru: chat mein live card hai (browser bhi dikhega). Poora form main bharunga; "
                           "OTP aaye to bata dijiye, submit / payment se pehle poochhunga.",
                    "note_for_you": "Do not poll; questions and the result arrive as cards + a message by themselves."}
        if action == "list":
            return {"jobs": [_short(v) for v in ops.listing(ctx.tenant_id, 10)]}
        if action == "recipes":
            return {"recipes": [{k: r.get(k) for k in ("name", "task", "site", "variables", "runs", "updated")}
                                for r in ops.recipes(ctx.tenant_id)]}
        if action == "forget_recipe":
            if not ops.forget_recipe(ctx.tenant_id, a.get("name") or ""):
                raise ToolError("Is naam ka seekha hua kaam nahi mila (action=recipes dekhiye).")
            return {"ok": True}
        tid = a.get("task_id") or ((ops.active(ctx.tenant_id) or {}).get("id")) or \
            ((ops.listing(ctx.tenant_id, 1) or [{}])[0].get("id"))
        if not tid:
            raise ToolError("Abhi koi website ka kaam nahi hai.")
        if action == "status":
            return _short(ops.get(ctx.tenant_id, tid))
        if action == "cancel":
            return _short(ops.cancel(ctx.tenant_id, tid))
    except ops.OperatorJobError as e:
        raise ToolError(str(e))
    raise ToolError("action = start | status | list | cancel | recipes | forget_recipe | answer")


async def computer_operator(ctx: Ctx, action, **a):
    if str(action) == "answer":
        from ..operator import service as ops
        got = await ops.answer_from_chat(ctx.tenant_id, str(a.get("text") or ""))
        if not got:
            raise ToolError("Abhi koi OTP / CAPTCHA ka intezaar nahi hai, ya yeh OTP jaisa nahi laga. Dobara poochhiye.")
        return {"ok": got["ok"], "say": got["say"]}
    return await asyncio.to_thread(_run, ctx, str(action), a)


OPERATOR_HANDLERS = {"computer_operator": computer_operator}
