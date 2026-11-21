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
        "action=message_done: message_id, note (she called back). action=forget (owner): number (erase one caller). "
        "v0.999.67 BUSINESS KNOWLEDGE (what the line may tell people): action=knowledge_add: kind text|file|url|sheet|"
        "system + text / file_id / url / (system, target, fields) + name -> facts that wait for HER approval in the app; an "
        "API with a key is set up only in the app (keys are never typed in chat). knowledge_sync / knowledge_remove: "
        "source_id. AI CALLS OUT (Hoola makes and speaks every call, only to people in HER data): action=list_new: name, "
        "goal (why Hoola calls, said in the opening), purpose, country, basis asked|customer|cold, start_hour, end_hour, "
        "at_once, max_tries, retry_min, daily_cap (money a day), voicemail, fields [answers to bring back]. list_edit: "
        "list_id + the same. list_people: list_id + file_id (her sheet) | lead_ids (Telecaller leads) | rows. list_card: "
        "list_id -> the start card (who can be called, who is held and why, cost) is sent to HER: ONLY her tap on it "
        "starts calls - never say calls started before she taps. list_pause / list_stop: list_id. test_chat: turns "
        "[{who: customer|hoola, text}] (+ list_id) -> what Hoola would say on a call (nobody is called)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["script", "faq_add", "faq_remove", "edit", "submit", "try", "settings", "line",
                                               "message_done", "forget", "knowledge_add", "knowledge_sync", "knowledge_remove",
                                               "list_new", "list_edit", "list_people", "list_card", "list_pause", "list_stop",
                                               "test_chat"]},
         "kind": {"type": "string"}, "text": {"type": "string"}, "url": {"type": "string"}, "name": {"type": "string"},
         "system": {"type": "string"}, "target": {"type": "string"}, "fields": {"type": "array", "items": {}},
         "source_id": {"type": "string"}, "list_id": {"type": "string"}, "goal": {"type": "string"},
         "purpose": {"type": "string"}, "country": {"type": "string"}, "basis": {"type": "string"},
         "start_hour": {"type": "string"}, "end_hour": {"type": "string"}, "at_once": {"type": "integer"},
         "max_tries": {"type": "integer"}, "retry_min": {"type": "integer"}, "daily_cap": {"type": "number"},
         "voicemail": {"type": "string"}, "lead_ids": {"type": "array", "items": {"type": "string"}},
         "rows": {"type": "array", "items": {"type": "object"}}, "turns": {"type": "array", "items": {"type": "object"}},
         "steps": {"type": "array", "items": {"type": "object"}},
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
        "callers asked that the script could not answer: offer to add them) | setup (provider steps, webhook URLs) | rules | "
        "knowledge (her knowledge sources) | knowledge_source (source_id: its facts) | lists (her AI call lists) | list "
        "(list_id + status: the people and their results) | countries (calling rules per country)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "calls", "call", "messages", "script", "report", "unanswered", "setup", "rules",
                                             "knowledge", "knowledge_source", "lists", "list", "countries"]},
         "source_id": {"type": "string"}, "list_id": {"type": "string"}, "status": {"type": "string"},
         "outcome": {"type": "string"}, "call_id": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
CALLCENTRE_LABELS = {"call_centre": "Doing call centre work", "call_centre_dekho": "Checking the phone line"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_SETTING_KEYS = ("provider", "number", "agent_name", "hours", "after_hours", "max_concurrent", "queue_max", "overflow",
                 "handover", "transfer_on", "record", "max_minutes", "rate_inr_per_min")
_EDIT_KEYS = ("business", "about", "greeting", "closing", "hours_text", "never", "handover_words", "languages", "can", "steps")
_LIST_KEYS = ("name", "goal", "purpose", "country", "basis", "start_hour", "end_hour", "at_once", "max_tries", "retry_min",
              "daily_cap", "voicemail", "fields")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..callcentre import rules as R
    from ..callcentre import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if str(getattr(ctx, "actor", "")).startswith("customer:"):
        raise ToolError("This work is only from inside the business.")
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
                raise ToolError("Only the owner can change the phone line settings.")
            return S.save_settings(t, **{k: a[k] for k in _SETTING_KEYS if k in a})
        if action == "line":
            if not _owner(ctx):
                raise ToolError("Only the owner can turn the line on / off.")
            return S.set_line(t, bool(a.get("on")))
        if action == "message_done":
            return S.message_done(t, _s(a.get("message_id")), _s(a.get("note")))
        if action == "forget":
            if not _owner(ctx):
                raise ToolError("Only the owner can do this.")
            return S.forget_caller(t, _s(a.get("number")))
        return _act2(ctx, action, a)
    except (S.CcError, ValueError) as ex:
        raise ToolError(str(ex))
    _ = R
    raise ToolError("unknown action")


def _act2(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    """v0.999.67 the Business Brain + AI calls out. Approving knowledge and starting a list are HER taps in the app."""
    from ..callcentre import knowledge as K
    from ..callcentre import outbound as O
    from ..callcentre import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "knowledge_add":
            if a.get("api_key") or _s(a.get("kind")) == "api":
                raise ToolError("An API with a key is set up only in the app (Telecaller > Knowledge): keys never go in chat.")
            return K.add_source(t, _s(a.get("kind")) or "text", name=_s(a.get("name")), text=_s(a.get("text")),
                                file_id=_s(a.get("file_id")), url=_s(a.get("url")), system=_s(a.get("system")),
                                target=_s(a.get("target")), fields=list(a.get("fields") or []) or None)
        if action == "knowledge_sync":
            return K.sync(t, _s(a.get("source_id")))
        if action == "knowledge_remove":
            if not _owner(ctx):
                raise ToolError("Only the owner can remove business knowledge.")
            return K.remove(t, _s(a.get("source_id")))
        if action == "list_new":
            return O.create(t, **{k: a[k] for k in _LIST_KEYS if k in a})
        if action == "list_edit":
            return O.update(t, _s(a.get("list_id")), **{k: a[k] for k in _LIST_KEYS if k in a})
        if action == "list_people":
            return O.add_people(t, _s(a.get("list_id")), a.get("rows"), _s(a.get("file_id")), a.get("lead_ids"), _s(a.get("basis")))
        if action == "list_card":
            card = O.start_card(t, _s(a.get("list_id")))
            S.publish(t, "callcentre_campaign_card", card | {"say": f"Start AI calls: {card['name']} - {card['callable']} people"}, conv)
            return card | {"say": "The start card is in the app. Calls begin only when she taps Start on it."}
        if action in ("list_pause", "list_stop"):
            return O.set_status(t, _s(a.get("list_id")), "paused" if action == "list_pause" else "stopped")
        if action == "test_chat":
            return O.test_chat(t, list(a.get("turns") or []), _s(a.get("list_id")))
    except (K.KbError, O.OutError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown action")


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
        from ..callcentre import countries as CO
        from ..callcentre import knowledge as K
        from ..callcentre import outbound as O
        if what == "knowledge":
            return {"sources": K.sources(t)}
        if what == "knowledge_source":
            return K.preview(t, _s(a.get("source_id")))
        if what == "lists":
            return {"lists": O.lists(t)}
        if what == "list":
            return {"people": O.people(t, _s(a.get("list_id")), _s(a.get("status")), 60)}
        if what == "countries":
            return {"countries": CO.summary()}
    except (S.CcError, ValueError) as ex:
        raise ToolError(str(ex))
    except Exception as ex:      # noqa: BLE001 - KbError / OutError said plainly
        if type(ex).__name__ in ("KbError", "OutError"):
            raise ToolError(str(ex))
        raise
    raise ToolError("unknown what")


async def call_centre(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def call_centre_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


CALLCENTRE_HANDLERS = {"call_centre": call_centre, "call_centre_dekho": call_centre_dekho}
