"""v0.999.52 LEAD DESK - the Lead Generation employee's desk tool (its chat, a call started from it, any chat of hers).

The leads engine's own tools (leads_run / leads_list / leads_export / leads_enrich / leads_forget) find and keep leads.
`leads_desk` is what happens next: it reads the desk (today, one lead's timeline, quality checks, lists), puts a file she
attached into the store, sets a lead's stage / follow-up / note, saves a search and drafts a message with a WhatsApp link
she taps to send herself. It NEVER sends anything, hands a list to the campaign desk or the Telecaller, opts a business
out or forgets one: those stay her taps on the desk.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

LEADSDESK_TOOLS = [
    {"name": "leads_desk", "description": (
        "HER Lead Generation desk (the businesses she found, each with a stage, follow-up and notes) - only when she has "
        "hired the Lead Generation employee. action=read: what=today (counts by stage, follow-ups due, searches running, "
        "saved searches) | leads (stage new|contacted|interested|not_interested|won|opted_out, q, city, due=true for "
        "follow-ups due) | lead (lead_id -> its details + timeline) | quality (maybe the same business twice, no phone, "
        "websites that did not open, untouched for 90 days) | lists (lists made for the campaign desk + saved searches). "
        "action=import_file: file_id of a CSV / Excel she attached -> her list goes into the store (one row per "
        "business, the file named as the source). action=stage: lead_ids + stage -> sets the stage. action=follow_up: "
        "lead_ids + on (YYYY-MM-DD, empty = clear) + note. action=note: lead_id + text. action=draft: lead_id + text -> "
        "the message + a WhatsApp link SHE taps to send from her own phone (nothing is sent; never say it was sent). "
        "action=save_search: name, lane REGISTRY (IndiaMART, free) | OFFICIAL_API (Google Maps, paid), params "
        "{search_term, city, kinds, near, max_rows}, weekly (IndiaMART only). It cannot send, hand a list to the campaign "
        "desk or the Telecaller, opt out or forget: tell her to tap it on the desk next to the chat. A business that "
        "opted out is never contacted or drafted for."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["read", "import_file", "stage", "follow_up", "note", "draft", "save_search"]},
         "what": {"type": "string", "enum": ["today", "leads", "lead", "quality", "lists"]},
         "lead_id": {"type": "string"}, "lead_ids": {"type": "array", "items": {"type": "string"}},
         "stage": {"type": "string"}, "q": {"type": "string"}, "city": {"type": "string"}, "due": {"type": "boolean"},
         "on": {"type": "string"}, "note": {"type": "string"}, "text": {"type": "string"}, "file_id": {"type": "string"},
         "name": {"type": "string"}, "lane": {"type": "string", "enum": ["REGISTRY", "OFFICIAL_API"]},
         "params": {"type": "object"}, "weekly": {"type": "boolean"}},
         "required": ["action"]}},
]
LEADSDESK_LABELS = {"leads_desk": "Working on your leads desk"}

KEY = "leads"
CHANGES = ("import_file", "stage", "follow_up", "note", "draft", "save_search")


def _ids(a: dict[str, Any]) -> list[str]:
    v = a.get("lead_ids")
    if isinstance(v, list) and v:
        return [str(x) for x in v]
    return [str(a["lead_id"])] if a.get("lead_id") else []


def _do(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    from ..employee import hire
    from ..leads import pipeline as PL
    from ..leads import service as S
    from .. import leadscap
    t = ctx.tenant_id
    if hire.status(t, KEY) not in ("hired", "paused"):
        raise ToolError("The Lead Generation employee is not hired. She can hire it from AI Employees.")
    act = str(a.get("action") or "")
    if act in CHANGES and ctx.actor not in ("owner",) and not str(ctx.actor).startswith("approved:"):
        raise ToolError("Only the owner can change the Lead Generation desk.")
    try:
        if act == "read":
            what = str(a.get("what") or "today")
            if what == "leads":
                r = PL.leads(t, str(a.get("stage") or ""), str(a.get("q") or ""), str(a.get("city") or ""), "",
                             False, bool(a.get("due")), 40)
                return {"total": r["total"], "counts": r["counts"],
                        "leads": [{k: x[k] for k in ("id", "name", "category", "city", "phone_shown", "stage_name",
                                                     "follow_on", "follow_note", "source_name")} for x in r["rows"]]}
            if what == "lead":
                return PL.lead(t, str(a.get("lead_id") or ""))
            if what == "quality":
                q = PL.quality(t)
                return {k: (v[:15] if isinstance(v, list) else v) for k, v in q.items()}
            if what == "lists":
                return PL.lists(t)
            d = PL.today(t)
            return {**d, "due": d["due"][:15], "recent_runs": d["recent_runs"][:4]}
        if act == "import_file":
            r = PL.import_file(t, str(a.get("file_id") or ""), str(a.get("text") or ""))
            return {**r, "note": "Her list is in the store. Nothing was sent to anyone."}
        if act == "stage":
            return PL.set_stage(t, _ids(a), str(a.get("stage") or ""), by="hoola")
        if act == "follow_up":
            return PL.set_follow(t, _ids(a), str(a.get("on") or ""), str(a.get("note") or ""), by="hoola")
        if act == "note":
            return PL.add_note(t, str(a.get("lead_id") or ""), str(a.get("text") or a.get("note") or ""), by="hoola")
        if act == "draft":
            return PL.draft(t, str(a.get("lead_id") or ""), str(a.get("text") or ""), by="hoola")
        if act == "save_search":
            return PL.save_search(t, str(a.get("name") or ""), str(a.get("lane") or "REGISTRY"),
                                  a.get("params") if isinstance(a.get("params"), dict) else {}, bool(a.get("weekly")))
    except (PL.DeskError, S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
        raise ToolError(str(e)) from e
    raise ToolError("action: read | import_file | stage | follow_up | note | draft | save_search")


async def leads_desk(ctx: Ctx, **args: Any) -> dict[str, Any]:
    out = await asyncio.to_thread(_do, ctx, dict(args))
    try:
        from .. import leadschat
        leadschat.forget(ctx.tenant_id)
    except Exception:   # noqa: BLE001
        pass
    return out


LEADSDESK_HANDLERS = {"leads_desk": leads_desk}
