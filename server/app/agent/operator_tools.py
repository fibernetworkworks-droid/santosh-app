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
OPERATOR_LABELS = {"computer_operator": "Apne browser mein website par kaam kar raha hoon"}


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
                    "where": "Hoola ka apna browser (server par) - not her PC, not her phone",
                    "say": "Kaam mere apne browser mein shuru (aapke PC par nahi): chat mein live card hai. Poora form main "
                           "bharunga; OTP aaye to bata dijiye, submit / payment se pehle poochhunga.",
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
        if not got and ops.recently_filled(ctx.tenant_id):
            return {"ok": True, "say": "OTP pehle hi box mein bhar diya hai, aage badh raha hoon. Digits mat dohraiye."}
        if not got:
            raise ToolError("Abhi koi OTP / CAPTCHA ka intezaar nahi hai, ya yeh OTP jaisa nahi laga. Dobara poochhiye.")
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
                            "say": (f"{site or 'Yeh website'} mere apne browser (Hoola ke server) se nahi khulti - unki "
                                    "suraksha data-centre ka address rok deti hai. Aapke PC par Chrome mein kar doon?"),
                            "next": ("She asked for YOUR browser. Tell her this in one or two lines and ASK. Only when she "
                                     "says yes: computer_operator action=start where=pc. If she says 'server pe hi try "
                                     "karo': where=server.")}
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
            "say": (f"{site or 'Yeh website'} Hoola ke server se nahi khulti - unki suraksha data-centre ka address rok "
                    "deti hai. Aapke PC par Chrome mein kar doon?"),
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
                    "say": ("Aapka PC abhi juda nahi hai, isliye wahan shuru nahi ho paya. PC par Santosh Desktop kholiye "
                            "aur 'Santosh ko PC chalane dein' on kijiye, phir bata dijiye."),
                    "next": ("Tell her this in one line. Do NOT start it in your own browser instead unless she says so "
                             "(then computer_operator where=server).")}
        reach.STATS["told"] += 1
        link = url or (f"https://{site}" if site else "")
        return {"status": "site_blocks_server", "site": site, "why": why, "pc": str(e)[:200],
                "say": (f"{site or 'Yeh website'} Hoola ke server se nahi khulti (unki suraksha data-centre ke address "
                        "rok deti hai), isliye yeh kaam abhi aapke PC se ya phone se hoga."),
                "next": ("Tell her this plainly in one or two lines and offer: (1) open Santosh Desktop on her PC, then say "
                         "'PC par karo' and it runs there by itself; (2) open_on_phone with " + (link or "the site link") +
                         " so she does it on her phone; (3) the office proxy (one-time setup) so the server can open it. "
                         "Don't start computer_operator again for this site unless she asks to try the server (where=server).")}
    r["place"] = "pc"
    r["where"] = "Aapka PC (Chrome on HER computer, via Santosh Desktop) - not your own browser"
    if asked:
        r["say"] = ("Aapke PC par Chrome mein shuru kar diya hai. Live card chat mein hai; OTP aaye to bas yahan bata "
                    "dijiye, main PC ke box mein bhar dunga.")
        return r
    reach.STATS["routed_pc"] += 1
    r["moved_to"] = "pc"
    r["why"] = f"{site} Hoola ke server se nahi khulta ({why})" if site else why
    r["say"] = (f"{site or 'Yeh site'} mere apne browser (Hoola ke server) se nahi khulti, isliye yeh kaam AAPKE PC par "
                "Chrome mein shuru kar diya hai. Live card chat mein hai; OTP aaye to bas yahan bata dijiye, main PC ke box "
                "mein bhar dunga.")
    return r


OPERATOR_HANDLERS = {"computer_operator": computer_operator}
