"""Event Sahayak tools (event planner's coworker). `event_plan_dekho` only reads; `event_plan` does the work.

Vendor bookings / advances, the client quotation / invoice, invites / messages and any spend become CARDS here; only HER tap in
the app (API) decides them. Hoola never invents a vendor price, date or licence, never sends a message by itself, never pays or
collects money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "event", "vendor", "vquote", "choose", "budget", "budget_remove", "quote", "doc_send", "doc_mark", "invoice",
            "client_paid", "book", "booking_paid", "spend", "spend_paid", "guests", "rsvp", "optout", "invite", "message",
            "message_sent", "task", "task_update", "permit", "show", "show_file", "report", "forget"]

EVENTPLAN_TOOLS = [
    {"name": "event_plan", "description": (
        "Event planner's coworker (corporate, conference, launch, birthday, college fest, exhibition). NEVER invent a vendor price, "
        "date, venue or licence: missing = blank, ask her. Vendor booking/advance, client quote/invoice, invites/messages, spends = "
        "CARDS for HER tap (say 'aapki haan ka card bheja hai'). action=settings*: firm, gstin, upi_id, margin_pct, head_margins "
        "{head: %}, fee_mode markup|fee|none, fee_pct, gst_pct, validity_days, terms, sound_till, morning_time, team [{name, phone, "
        "role}]. event: name / event (update), kind, client, client_phone, client_gstin, client_state, day, start, end, venue, city, "
        "headcount, budget, brief, facts {venue_kind indoor|open|hotel|public, sound, food, music, alcohol, pandal, stage, fireworks, "
        "drone, road, ticketed}, status. vendor: name, head, phone, upi_id, gstin, fssai. vquote: event, vendor, amount (as quoted), "
        "head, what, gst_included, gst_pct, per plate|person|hour|day, qty, advance_pct, cancel_terms, includes. choose: quote. "
        "budget: event, lines [{id?, head, item, qty, unit, cost, margin_pct, pure_agent}], replace. budget_remove: event, line. "
        "quote: event (draft). doc_send: doc -> CARD. doc_mark: doc, what sent|accepted*|rejected. invoice: event (draft after the "
        "event). client_paid*: event, amount, ref. book: event, vendor or quote, amount, advance, advance_due, arrive (HH:MM) -> CARD. "
        "booking_paid*: booking, amount, ref. spend: event, what, amount, payee, head -> CARD. spend_paid*: spend, ref. guests: event, "
        "text (lines 'Name 98xxxxxxxx group') or rows or file_id. rsvp: event, guest, words or status yes|no|maybe, plus, came. "
        "optout: event, guest. invite: event, text ({name} allowed), group -> CARD. message: event, kind reminder|vendor|client|custom, "
        "to (vendor / 'client'), text -> CARD. message_sent: message. task: event, what, owner, due. task_update: task, status "
        "open|done|skipped, owner, due. permit: event, key, status pending|applied|granted|refused|not_needed, ref, note, label. "
        "show: event, text (lines '18:30 Welcome (10 min) - Riya | stage'), replace. show_file: event (cue sheet PDF). report: event, "
        "attended, notes, issues []. forget*: event (DPDP, after done). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "event": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string"}, "client": {"type": "string"},
         "client_phone": {"type": "string"}, "client_email": {"type": "string"}, "client_gstin": {"type": "string"},
         "client_state": {"type": "string"}, "day": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "venue": {"type": "string"}, "city": {"type": "string"}, "headcount": {"type": "number"}, "budget": {"type": "number"},
         "brief": {"type": "string"}, "facts": {"type": "object"}, "status": {"type": "string"}, "vendor": {"type": "string"},
         "head": {"type": "string"}, "phone": {"type": "string"}, "upi_id": {"type": "string"}, "gstin": {"type": "string"},
         "fssai": {"type": "string"}, "notes": {"type": "string"}, "amount": {"type": "number"}, "what": {"type": "string"},
         "gst_included": {"type": "boolean"}, "gst_pct": {"type": "number"}, "per": {"type": "string"}, "qty": {"type": "number"},
         "advance_pct": {"type": "number"}, "cancel_terms": {"type": "string"}, "includes": {"type": "string"},
         "valid_till": {"type": "string"}, "file_id": {"type": "string"}, "quote": {"type": "string"},
         "lines": {"type": "array", "items": {"type": "object"}}, "replace": {"type": "boolean"}, "line": {"type": "string"},
         "doc": {"type": "string"}, "ref": {"type": "string"}, "advance": {"type": "number"}, "advance_due": {"type": "string"},
         "arrive": {"type": "string"}, "terms": {"type": "string"}, "booking": {"type": "string"}, "payee": {"type": "string"},
         "spend": {"type": "string"}, "text": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object"}},
         "guest": {"type": "string"}, "words": {"type": "string"}, "plus": {"type": "number"}, "came": {"type": "boolean"},
         "group": {"type": "string"}, "to": {"type": "string"}, "message": {"type": "string"}, "task": {"type": "string"},
         "owner": {"type": "string"}, "due": {"type": "string"}, "key": {"type": "string"}, "label": {"type": "string"},
         "note": {"type": "string"}, "attended": {"type": "number"}, "issues": {"type": "array", "items": {"type": "string"}},
         "firm": {"type": "string"}, "address": {"type": "string"}, "email": {"type": "string"}, "margin_pct": {"type": "number"},
         "head_margins": {"type": "object"}, "fee_mode": {"type": "string"}, "fee_pct": {"type": "number"},
         "validity_days": {"type": "integer"}, "sound_till": {"type": "string"}, "morning_time": {"type": "string"},
         "team": {"type": "array", "items": {"type": "object"}}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "event_plan_dekho", "description": (
        "Read event work (nothing changes). what=day (this week's events, today's / late tasks, permissions late, advances due, cards "
        "waiting) | events | event (event: everything) | budget | compare (head) | guests (status) | tasks | permits | show "
        "(run-of-show + day timeline + checks) | doc (doc) | waiting | vendors (head) | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "events", "event", "budget", "compare", "guests", "tasks", "permits", "show", "doc",
                                             "waiting", "vendors", "settings"]},
         "event": {"type": "string"}, "doc": {"type": "string"}, "head": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
EVENTPLAN_LABELS = {"event_plan": "Event ka kaam kar raha hoon", "event_plan_dekho": "Event dekh raha hoon"}

_OWNER_ONLY = {"settings", "client_paid", "booking_paid", "spend_paid", "forget"}
_SET_KEYS = ("firm", "gstin", "address", "phone", "email", "upi_id", "margin_pct", "head_margins", "fee_mode", "fee_pct", "gst_pct",
             "validity_days", "terms", "sound_till", "morning_time", "team", "rules")
_EV_KEYS = ("kind", "client", "client_phone", "client_email", "client_gstin", "client_state", "day", "start", "end", "venue", "city",
            "headcount", "budget", "brief", "facts", "status")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..eventplan import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    ev = _s(a.get("event"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "event":
            return S.event_save(t, _s(a.get("name")), ev, actor, conv, **{k: a[k] for k in _EV_KEYS if k in a})
        if action == "vendor":
            return S.vendor_save(t, _s(a.get("vendor") or a.get("name")), _s(a.get("head")), _s(a.get("phone")), _s(a.get("upi_id")),
                                 _s(a.get("gstin")), _s(a.get("fssai")), _s(a.get("notes")))
        if action == "vquote":
            return S.vquote_add(t, ev, _s(a.get("vendor")), a.get("amount"), _s(a.get("head")), _s(a.get("what")), a.get("gst_included"),
                                a.get("gst_pct"), _s(a.get("per")), a.get("qty"), a.get("advance_pct"), _s(a.get("cancel_terms")),
                                _s(a.get("includes")), _s(a.get("valid_till")), _s(a.get("file_id")))
        if action == "choose":
            return S.choose_quote(t, _s(a.get("quote")), actor)
        if action == "budget":
            return S.budget_set(t, ev, a.get("lines"), bool(a.get("replace")), actor)
        if action == "budget_remove":
            return S.budget_remove(t, ev, _s(a.get("line")))
        if action == "quote":
            return S.quote_make(t, ev, conv, actor)
        if action == "doc_send":
            return S.doc_request(t, _s(a.get("doc")), conv, actor)
        if action == "doc_mark":
            return S.doc_mark(t, _s(a.get("doc")), _s(a.get("what")), actor)
        if action == "invoice":
            return S.invoice_make(t, ev, conv, actor)
        if action == "client_paid":
            return S.client_paid(t, ev, a.get("amount"), _s(a.get("ref")), "", actor)
        if action == "book":
            return S.booking_request(t, ev, _s(a.get("vendor")), _s(a.get("quote")), a.get("amount"), a.get("advance"),
                                     _s(a.get("advance_due")), _s(a.get("arrive")), _s(a.get("terms")), _s(a.get("head")), actor, conv)
        if action == "booking_paid":
            return S.booking_paid(t, _s(a.get("booking")), a.get("amount"), _s(a.get("ref")), actor)
        if action == "spend":
            return S.spend_request(t, ev, _s(a.get("what")), a.get("amount"), _s(a.get("payee")), _s(a.get("head")), actor, conv)
        if action == "spend_paid":
            return S.spend_paid(t, _s(a.get("spend")), _s(a.get("ref")), actor)
        if action == "guests":
            return S.guests_add(t, ev, a.get("rows"), _s(a.get("text")), _s(a.get("file_id")))
        if action == "rsvp":
            return S.rsvp(t, ev, _s(a.get("guest")), _s(a.get("words")), _s(a.get("status")), a.get("plus"), a.get("came"))
        if action == "optout":
            return S.guest_optout(t, ev, _s(a.get("guest")))
        if action == "invite":
            return S.message_request(t, ev, "invite", _s(a.get("text")), _s(a.get("group")), "", actor, conv)
        if action == "message":
            return S.message_request(t, ev, _s(a.get("kind")) or "custom", _s(a.get("text")), _s(a.get("group")), _s(a.get("to")), actor, conv)
        if action == "message_sent":
            return S.message_sent(t, _s(a.get("message")))
        if action == "task":
            return S.task_add(t, ev, _s(a.get("what")), _s(a.get("owner")), _s(a.get("due")))
        if action == "task_update":
            return S.task_update(t, _s(a.get("task")), _s(a.get("status")), _s(a.get("owner")), _s(a.get("due")))
        if action == "permit":
            return S.permit_update(t, ev, _s(a.get("key")), _s(a.get("status")), _s(a.get("ref")), _s(a.get("note")), _s(a.get("label")))
        if action == "show":
            return S.show_set(t, ev, _s(a.get("text")), a.get("lines"), a.get("replace") is not False)
        if action == "show_file":
            return S.show_file(t, ev, conv)
        if action == "report":
            return S.report(t, ev, a.get("attended"), _s(a.get("notes")), a.get("issues"), conv, actor)
        if action == "forget":
            return S.forget(t, ev, actor)
    except S.EventError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..eventplan import service as S
    t, ev = ctx.tenant_id, _s(a.get("event"))
    try:
        if what == "day":
            return S.day(t)
        if what == "events":
            return {"events": S.events(t, _s(a.get("status")))}
        if what == "event":
            return S.event_view(t, ev)
        if what == "budget":
            return S.budget(t, ev)
        if what == "compare":
            return S.compare(t, ev, _s(a.get("head")))
        if what == "guests":
            return S.guests(t, ev, _s(a.get("status")))
        if what == "tasks":
            return S.tasks(t, ev)
        if what == "permits":
            return S.permits(t, ev)
        if what == "show":
            return S.show(t, ev)
        if what == "doc":
            return S.doc_view(t, _s(a.get("doc")))
        if what == "waiting":
            return S.waiting(t)
        if what == "vendors":
            return {"vendors": S.vendors(t, _s(a.get("head")))}
        if what == "settings":
            return S.settings(t)
    except S.EventError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _event_plan(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _event_plan_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


EVENTPLAN_HANDLERS = {"event_plan": _event_plan, "event_plan_dekho": _event_plan_dekho}
