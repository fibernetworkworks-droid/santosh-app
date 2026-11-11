"""v0.67 Tool `computer_operator`: Hoola as the owner's computer operator on websites (forms, downloads, status checks,
applications), in its own browser, with her on the phone for OTP / CAPTCHA / passwords / approvals / payments."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

OPERATOR_TOOLS = [
    {"name": "computer_operator", "description": (
        "Do a job ON A WEBSITE for the owner like a cyber-cafe / CSC computer operator, in YOUR OWN browser (Hoola's "
        "browser on the server, where her logins stay saved - NOT her PC; where=pc runs it in Chrome on HER PC): fill online forms and applications (government portals, banks, utilities, exams, insurance, "
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
         "where": {"type": "string", "enum": ["auto", "server", "pc"], "description":
                   "auto (default): your own browser on Hoola's server, or HER PC when the site refuses the server "
                   "(say so); server = your own browser even then (only when she asks); pc = Chrome on HER PC (she "
                   "said 'mere PC / laptop pe')"},
         "task_id": {"type": "string"},
         "name": {"type": "string", "description": "recipe name for forget_recipe"}},
         "required": ["action"]}},
]
OPERATOR_LABELS = {"computer_operator": "Working on a website in my browser"}


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
            return {"task_id": v["id"], "status": v["status"], "place": "hoola",
                    "where": "Hoola's own browser (on the server) - not her PC, not her phone",
                    "say": "Started in my own browser (not on your PC): there is a live card in the chat. I will fill the whole form; "
                           "if an OTP comes, tell me here, and I will ask before submit / payment.",
                    "note_for_you": "Do not poll; questions and the result arrive as cards + a message by themselves."}
        if action == "list":
            return {"jobs": [_short(v) for v in ops.listing(ctx.tenant_id, 10)]}
        if action == "recipes":
            return {"recipes": [{k: r.get(k) for k in ("name", "task", "site", "variables", "runs", "updated")}
                                for r in ops.recipes(ctx.tenant_id)]}
        if action == "forget_recipe":
            if not ops.forget_recipe(ctx.tenant_id, a.get("name") or ""):
                raise ToolError("No learned task with this name was found (see action=recipes).")
            return {"ok": True}
        tid = a.get("task_id") or ((ops.active(ctx.tenant_id) or {}).get("id")) or \
            ((ops.listing(ctx.tenant_id, 1) or [{}])[0].get("id"))
        if not tid:
            raise ToolError("There is no website task right now.")
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
        if not got and ops.recently_filled(ctx.tenant_id):
            return {"ok": True, "say": "The OTP has already been entered in the box, I am moving on. Do not repeat the digits."}
        if not got:
            raise ToolError("No OTP / CAPTCHA is being waited for right now, or this did not look like an OTP. Ask her again.")
        return {"ok": got["ok"], "say": got["say"]}
    if str(action) == "start":
        where = str(a.get("where") or "auto")
        from ..config import get_settings
        if where == "hoola":
            # v0.93 she said "apne / Hoola ke browser mein": it stays in Hoola's own browser; a site that refuses the
            # server is told to her with a question - never a quiet move to her PC
            if get_settings().operator_preflight:
                from ..operator import reach
                chk = await asyncio.to_thread(reach.check, str(a.get("task") or ""), str(a.get("start_url") or ""), True)
                if not chk["ok"]:
                    site = chk.get("site") or ""
                    return {"status": "site_blocks_server", "site": site, "why": chk.get("why", ""), "place": "hoola",
                            "say": (f"{site or 'This website'} does not open from my own browser (Hoola's server) - its "
                                    "security blocks data-centre addresses. Shall I do it in Chrome on your PC?"),
                            "next": ("She asked for YOUR browser. Tell her this in one or two lines and ASK. Only when she "
                                     "says yes: computer_operator action=start where=pc. If she says 'try on the server only': where=server.")}
            where = "server"
        if where == "auto" and not get_settings().operator_preflight:
            where = "server"
        if where != "server":
            from ..operator import reach
            chk = {"ok": True, "site": ""} if where == "pc" else \
                await asyncio.to_thread(reach.check, str(a.get("task") or ""), str(a.get("start_url") or ""), True)
            if where != "pc" and not chk["ok"] and not _pc_is_hers(ctx):
                # v0.315 SAB SERVER PAR (v0.271's rule, here too): a site that refuses Hoola's server no longer moves
                # to HER PC on its own - her test run ("Hoola ke browser mein ... Amazon, Flipkart") went to her PC
                # and failed 10 minutes later. She is asked first; her yes = where=pc.
                return _ask_for_pc(chk)
            if where == "pc" or not chk["ok"]:
                return await _to_pc(ctx, a, chk)
    return await asyncio.to_thread(_run, ctx, str(action), a)


def _pc_is_hers(ctx: Ctx) -> bool:
    """She placed this job (or this chat's running website work) on HER PC: then a refused site may go there."""
    from . import where as _where
    conv = getattr(ctx, "conversation_id", "") or ""
    return (getattr(ctx, "place", "") or "") == "pc" or _where._asked(conv, "pc") or _where.working(conv) == "pc"


def _ask_for_pc(chk: dict[str, Any]) -> dict[str, Any]:
    from ..operator import reach
    site = chk.get("site") or ""
    reach.STATS["told"] += 1
    return {"status": "site_blocks_server", "site": site, "why": chk.get("why", ""), "place": "server",
            "say": (f"{site or 'This website'} does not open from Hoola's server - its security blocks data-centre "
                    "addresses. Shall I do it in Chrome on your PC?"),
            "next": ("Do the rest of the job with the sites that DO open (never wait on this one), then tell her in one "
                     "line that this site refuses Hoola's server and ASK. Only when she says yes: computer_operator "
                     "action=start where=pc. Never move it to her PC or the cloud PC by yourself.")}


async def _to_pc(ctx: Ctx, a: dict[str, Any], chk: dict[str, Any]) -> dict[str, Any]:
    """v0.92 The site refuses Hoola's server (UIDAI does): do the same job on her own PC (her home / office internet),
    or tell her at once and plainly - never minutes of retrying the same wall."""
    from ..operator import reach
    from .pc_tools import pc_do
    site = chk.get("site") or ""
    task = str(a.get("task") or "").strip()
    url = str(a.get("start_url") or "").strip()
    pc_task = (task + (f" Website: {url}" if url else "") + " Use Google Chrome on this PC. When the site sends an OTP, "
               "click the OTP box and use ask_otp. Download files to the normal Downloads folder and say the file name.")
    why = chk.get("why") or ""
    asked = chk.get("ok", True)    # v0.93 True = she asked for her PC; False = the site refuses Hoola's server
    try:
        r = await pc_do(ctx, pc_task)
    except ToolError as e:
        if asked:
            return {"status": "pc_not_ready", "place": "pc", "pc": str(e)[:200],
                    "say": ("Your PC is not connected right now, so it could not start there. Open Santosh Desktop on the PC "
                            "and turn on 'Let Santosh control the PC', then tell me."),
                    "next": ("Tell her this in one line. Do NOT start it in your own browser instead unless she says so "
                             "(then computer_operator where=server).")}
        reach.STATS["told"] += 1
        link = url or (f"https://{site}" if site else "")
        return {"status": "site_blocks_server", "site": site, "why": why, "pc": str(e)[:200],
                "say": (f"{site or 'This website'} does not open from Hoola's server (its security blocks "
                        "data-centre addresses), so this task will be done from your PC or phone for now."),
                "next": ("Tell her this plainly in one or two lines and offer: (1) open Santosh Desktop on her PC, then say "
                         "'PC par karo' and it runs there by itself; (2) open_on_phone with " + (link or "the site link") +
                         " so she does it on her phone; (3) the office proxy (one-time setup) so the server can open it. "
                         "Don't start computer_operator again for this site unless she asks to try the server (where=server).")}
    r["place"] = "pc"
    r["where"] = "Her PC (Chrome on HER computer, via Santosh Desktop) - not your own browser"
    if asked:
        r["say"] = ("Started in Chrome on your PC. The live card is in the chat; if an OTP comes just tell me here "
                    "and I will enter it in the PC box.")
        return r
    reach.STATS["routed_pc"] += 1
    r["moved_to"] = "pc"
    r["why"] = f"{site} does not open from Hoola's server ({why})" if site else why
    r["say"] = (f"{site or 'This site'} does not open from my own browser (Hoola's server), so this task was started on YOUR PC "
                "in Chrome. The live card is in the chat; if an OTP comes just tell me here and I will enter it in the PC box.")
    return r


OPERATOR_HANDLERS = {"computer_operator": computer_operator}
