"""v0.128 Call Centre Sahayak tools (her side). `call_centre_dekho` only reads; `call_centre` prepares. A script version runs on
the phone line ONLY after her tap in the app (POST /api/callcentre/scripts/{id}/decide): `submit` just sends that card.
The AI line itself has its own customer-safe tools inside the call (callcentre/service.LINE_TOOLS), never these."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

CALLCENTRE_TOOLS = [
    {"name": "call_centre", "description": (
        "Her business phone line answered by Hoola (inbound AI call centre, her approved script only). action=script: words "
        "(her own words: what the business does, timings, prices she wants said, common questions + answers, what the line may "
        "do: appointments / complaint / ticket status) and/or file_id (FAQ file) -> a script DRAFT. action=faq_add: faqs "
        "[{q, a, words}] (her answers only; '[blank]' when she hasn't said). action=faq_remove: questions [..]. action=edit: "
        "business, about, greeting, closing, hours_text, never [..], handover_words [..], languages [hi-IN, mr-IN, en-IN], can "
        "{appointments, ticket_status, complaints}. action=submit: sends HER the approval card (the line runs only after her "
        "tap; never say it is live before). action=try: question -> what the line would answer. action=settings (owner): "
        "provider plivo|exotel|fake, number, agent_name, hours {open, close, days 0=Mon}, after_hours message|closed, "
        "max_concurrent, queue_max, overflow callback|transfer, handover [{name, phone, role}], transfer_on, record, "
        "max_minutes, rate_inr_per_min. Provider keys are typed only in the app. action=line (owner): on true|false. "
        "action=message_done: message_id, note (she called back). action=forget (owner): number (erase one caller)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["script", "faq_add", "faq_remove", "edit", "submit", "try", "settings", "line",
                                               "message_done", "forget"]},
         "words": {"type": "string"}, "file_id": {"type": "string"},
         "faqs": {"type": "array", "items": {"type": "object"}}, "questions": {"type": "array", "items": {"type": "string"}},
         "business": {"type": "string"}, "about": {"type": "string"}, "greeting": {"type": "string"},
         "closing": {"type": "string"}, "hours_text": {"type": "string"}, "never": {"type": "array", "items": {"type": "string"}},
         "handover_words": {"type": "array", "items": {"type": "string"}},
         "languages": {"type": "array", "items": {"type": "string"}}, "can": {"type": "object"},
         "question": {"type": "string"}, "provider": {"type": "string"}, "number": {"type": "string"},
         "agent_name": {"type": "string"}, "hours": {"type": "object"}, "after_hours": {"type": "string"},
         "max_concurrent": {"type": "integer"}, "queue_max": {"type": "integer"}, "overflow": {"type": "string"},
         "handover": {"type": "array", "items": {"type": "object"}}, "transfer_on": {"type": "boolean"},
         "record": {"type": "boolean"}, "max_minutes": {"type": "integer"}, "rate_inr_per_min": {"type": "number"},
         "on": {"type": "boolean"}, "message_id": {"type": "string"}, "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "call_centre_dekho", "description": (
        "Read her phone line (nothing changes). what=day (line on/off, today's calls, open call-backs, problems) | calls "
        "(outcome) | call (call_id: summary, masked transcript, flags) | messages (open call-backs / messages) | script "
        "(running version + draft) | report (days: by outcome, languages, hand-overs, minutes, cost) | unanswered (questions "
        "callers asked that the script could not answer: offer to add them) | setup (provider steps, webhook URLs) | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "calls", "call", "messages", "script", "report", "unanswered", "setup", "rules"]},
         "outcome": {"type": "string"}, "call_id": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
CALLCENTRE_LABELS = {"call_centre": "Call centre ka kaam kar raha hoon", "call_centre_dekho": "Phone line dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_SETTING_KEYS = ("provider", "number", "agent_name", "hours", "after_hours", "max_concurrent", "queue_max", "overflow",
                 "handover", "transfer_on", "record", "max_minutes", "rate_inr_per_min")
_EDIT_KEYS = ("business", "about", "greeting", "closing", "hours_text", "never", "handover_words", "languages", "can")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..callcentre import rules as R
    from ..callcentre import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if str(getattr(ctx, "actor", "")).startswith("customer:"):
        raise ToolError("Yeh kaam sirf business ke andar se.")
    try:
        if action == "script":
            text = ""
            if a.get("file_id"):
                from ..callcentre.api import _file_text
                text = _file_text(t, _s(a["file_id"]))
            return S.make_script(t, _s(a.get("words")), text)
        if action == "faq_add":
            return S.edit_script(t, faq_add=list(a.get("faqs") or []))
        if action == "faq_remove":
            return S.edit_script(t, faq_remove=[_s(x) for x in a.get("questions") or []])
        if action == "edit":
            return S.edit_script(t, **{k: a[k] for k in _EDIT_KEYS if k in a})
        if action == "submit":
            return S.submit(t, conv)
        if action == "try":
            from ..callcentre.api import _try
            return _try(t, _s(a.get("question")), True)
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Phone line ki settings sirf owner badal sakti hain.")
            return S.save_settings(t, **{k: a[k] for k in _SETTING_KEYS if k in a})
        if action == "line":
            if not _owner(ctx):
                raise ToolError("Line chalu / band sirf owner.")
            return S.set_line(t, bool(a.get("on")))
        if action == "message_done":
            return S.message_done(t, _s(a.get("message_id")), _s(a.get("note")))
        if action == "forget":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.forget_caller(t, _s(a.get("number")))
    except (S.CcError, ValueError) as ex:
        raise ToolError(str(ex))
    _ = R
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..callcentre import rules as R
    from ..callcentre import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            d = S.day(t)
            return {k: d[k] for k in ("say", "problems", "live", "messages", "calls")} | {
                "line_on": d["settings"]["line_on"], "script_version": (d["script"] or {}).get("version"),
                "draft_version": (d["draft"] or {}).get("version")}
        if what == "calls":
            return {"calls": S.calls(t, 30, _s(a.get("outcome")))}
        if what == "call":
            v = S.call(t, _s(a.get("call_id")))
            v.pop("caller", None)          # the full number stays in the app
            return v
        if what == "messages":
            return {"messages": [m | {"caller": m["caller_masked"]} for m in S.messages(t)]}
        if what == "script":
            return {"running": S.approved(t), "draft": S.draft(t)}
        if what == "report":
            return S.report(t, int(a.get("days") or 7))
        if what == "unanswered":
            return {"questions": S.unanswered(t, int(a.get("days") or 30)),
                    "next": "Offer to add answers in HER words (faq_add), then submit for her tap."}
        if what == "setup":
            st = S.settings(t)
            return {k: st.get(k) for k in ("provider", "number", "urls", "setup", "providers", "not_used", "problems", "creds_set")}
        if what == "rules":
            return {"never": R.NEVER, "sources": R.SOURCES, "providers": R.PROVIDERS, "not_used": R.NOT_PRIMARY}
    except (S.CcError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def call_centre(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def call_centre_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


CALLCENTRE_HANDLERS = {"call_centre": call_centre, "call_centre_dekho": call_centre_dekho}
