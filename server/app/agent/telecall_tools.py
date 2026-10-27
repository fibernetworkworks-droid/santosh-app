"""v0.99 Telecaller Sahayak tools. Hoola prepares the call list, scripts and logs; a PERSON always makes the call.
`telecall_dekho` only reads. Nothing here dials a number, calls with an AI voice or sends a message."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

TELECALL_TOOLS = [
    {"name": "telecall", "description": (
        "Telecaller coworker: Hoola PREPARES calls, she / her team MAKE them (never say Hoola called anyone; the phone's "
        "dialer opens only when she taps Call in the app). "
        "action=add: one person (name, phone, source enquiry|website|walk_in|missed_call|whatsapp|referral|customer|"
        "ads_form|bought|cold, purpose sales|followup|renewal|dues|appointment|feedback|service|reactivate, need, city, "
        "language, amount, assigned, next_when). action=import: a lead sheet (file_id of a CSV / Excel she sent, or list_id "
        "from the chat import) + source + purpose. "
        "action=log: AFTER she spoke to someone: lead (name / phone / id) + notes = HER OWN WORDS about the call (or file_id of "
        "her voice note) and/or outcome (interested | callback | converted | not_interested | already_bought | promised_pay | "
        "language | complaint | no_answer | busy | switched_off | not_reachable | wrong_number | dnd), next_when ('kal 4 baje', "
        "'Friday', '2 ghante'), interest, amount. Result has the follow-up time and a WhatsApp draft she sends herself. "
        "action=script: lead -> a short script for this person. action=update: lead + need / notes / purpose / interest / "
        "stage / next_when / assigned / amount. action=dnd: lead (wrong=true for a wrong number). action=forget: lead (delete "
        "everything, DPDP). action=forget_old (delete closed records older than a year). action=settings (owner only): "
        "business, caller_name, pitch, segment, start_hour, end_hour, daily_goal, max_attempts, record_calls, registered "
        "(she calls from a TRAI-registered 140 line), language, rules, dont_say, team, morning_time."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["add", "import", "log", "script", "update", "dnd", "forget", "forget_old",
                                               "settings"]},
         "lead": {"type": "string"}, "name": {"type": "string"}, "phone": {"type": "string"}, "source": {"type": "string"},
         "purpose": {"type": "string"}, "need": {"type": "string"}, "city": {"type": "string"}, "language": {"type": "string"},
         "amount": {"type": "number"}, "assigned": {"type": "string"}, "next_when": {"type": "string"},
         "file_id": {"type": "string"}, "list_id": {"type": "string"}, "notes": {"type": "string"},
         "outcome": {"type": "string"}, "interest": {"type": "string"}, "stage": {"type": "string"},
         "consent": {"type": "boolean"}, "wrong": {"type": "boolean"}, "seconds": {"type": "integer"},
         "business": {"type": "string"}, "caller_name": {"type": "string"}, "pitch": {"type": "string"},
         "segment": {"type": "string"}, "start_hour": {"type": "string"}, "end_hour": {"type": "string"},
         "daily_goal": {"type": "integer"}, "max_attempts": {"type": "integer"}, "record_calls": {"type": "boolean"},
         "registered": {"type": "boolean"}, "rules": {"type": "array", "items": {"type": "string"}},
         "dont_say": {"type": "array", "items": {"type": "string"}}, "team": {"type": "array", "items": {"type": "object"}},
         "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "telecall_dekho", "description": (
        "Read the telecalling work (nothing changes). what=list (who to call now, each with WHY, then later today and "
        "people held back for compliance; assigned to filter one caller) | lead (lead: details + full call history + last "
        "script) | leads (q, stage open|new|interested|callback|converted|lost|dnd) | report (days: calls, connects, talk "
        "time, interested, converted, missed follow-ups, sources, best hours, objections) | objections (purpose) | "
        "best_hours | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["list", "lead", "leads", "report", "objections", "best_hours", "settings"]},
         "lead": {"type": "string"}, "q": {"type": "string"}, "stage": {"type": "string"}, "days": {"type": "integer"},
         "assigned": {"type": "string"}, "purpose": {"type": "string"}},
         "required": ["what"]}},
]
TELECALL_LABELS = {"telecall": "Call list ka kaam kar raha hoon", "telecall_dekho": "Call list dekh raha hoon"}
_OWNER_ONLY = {"settings", "forget_old"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..telecall import service as T
    actor = getattr(ctx, "actor", "owner") or "owner"
    by = "owner" if actor == "owner" else actor
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action in _OWNER_ONLY and actor != "owner" and not actor.startswith("approved:"):
            raise ToolError("Yeh sirf owner kar sakti hain.")
        if action == "add":
            return T.add_lead(t, _s(a.get("name")), _s(a.get("phone") or a.get("lead")), _s(a.get("source")) or "enquiry",
                              _s(a.get("purpose")) or "sales", _s(a.get("need")), _s(a.get("notes")), _s(a.get("city")),
                              _s(a.get("language")), a.get("amount"), a.get("consent"), _s(a.get("assigned")),
                              _s(a.get("next_when")), by=by)
        if action == "import":
            return T.import_list(t, _s(a.get("list_id")), _s(a.get("file_id")), _s(a.get("source")),
                                 _s(a.get("purpose")) or "sales", _s(a.get("assigned")))
        if action == "log":
            return T.log_call(t, _s(a.get("lead") or a.get("phone") or a.get("name")), "", _s(a.get("outcome")),
                              _s(a.get("notes")), _s(a.get("next_when")), a.get("seconds"), _s(a.get("interest")),
                              a.get("amount"), _s(a.get("file_id")), by, "chat", conv)
        if action == "script":
            return T.make_script(t, _s(a.get("lead") or a.get("name") or a.get("phone")), conv)
        if action == "update":
            keys = ("name", "need", "city", "language", "assigned", "notes", "purpose", "interest", "stage", "amount",
                    "consent", "next_when")
            return T.update_lead(t, _s(a.get("lead") or a.get("phone")), **{k: a[k] for k in keys if k in a})
        if action == "dnd":
            return T.mark_dnd(t, _s(a.get("lead") or a.get("phone")), bool(a.get("wrong")))
        if action == "forget":
            return T.forget(t, _s(a.get("lead") or a.get("phone")))
        if action == "forget_old":
            return T.forget_old(t)
        if action == "settings":
            keys = ("business", "caller_name", "pitch", "segment", "start_hour", "end_hour", "daily_goal", "max_attempts",
                    "record_calls", "registered", "language", "rules", "dont_say", "team", "morning_time")
            return {"settings": T.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
    except T.TeleError as e:
        raise ToolError(str(e))
    raise ToolError("action = add | import | log | script | update | dnd | forget | forget_old | settings")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..telecall import service as T
    t = ctx.tenant_id
    try:
        if what == "list":
            r = T.call_list(t, 25, _s(a.get("assigned")))
            return r | {"note": "Read the WHY to her. She calls from the app (Call button); never say you called."}
        if what == "lead":
            return T.get_lead(t, _s(a.get("lead")))
        if what == "leads":
            return {"leads": T.leads(t, _s(a.get("q")), _s(a.get("stage")), 60)}
        if what == "report":
            return T.report(t, int(a.get("days") or 1))
        if what == "objections":
            return {"objections": T.objection_library(t, _s(a.get("purpose")), 10)}
        if what == "best_hours":
            return {"best_hours": T.best_hours(t)}
        if what == "settings":
            return T.settings(t)
    except T.TeleError as e:
        raise ToolError(str(e))
    raise ToolError("what = list | lead | leads | report | objections | best_hours | settings")


async def telecall(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def telecall_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


TELECALL_HANDLERS = {"telecall": telecall, "telecall_dekho": telecall_dekho}
