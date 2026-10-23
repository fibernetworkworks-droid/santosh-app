"""Banquet Sahayak tools (banquet hall / lawn / hotel-banquet sales). `banquet_dekho` only reads; `banquet` does the work.

The quotation and booking terms going to the client, a hold becoming a confirmed booking, any discount or refund, any payment
request, the post-event bill and any message to a client become CARDS here; only HER tap in the app (API) decides them. A hall +
date + slot already held / confirmed is refused in code. Hoola never invents a price, date or availability, never sends a
message by itself and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "hall", "package", "extra", "enquiry", "lead", "booking", "hold", "release", "close", "open",
            "quote_send", "contract_send", "confirm", "discount", "pay_request", "message", "paid", "count", "lock", "beo",
            "bill", "cancel", "refund_sent", "done", "forget"]
_OWNER_ONLY = {"settings", "hall", "package", "extra", "close", "open", "paid", "cancel", "refund_sent", "done", "forget"}

BANQUET_TOOLS = [
    {"name": "banquet", "description": (
        "Banquet hall / lawn sales coworker. NEVER invent a price, date, capacity or availability; ask her. Cards = only her tap "
        "decides (say 'aapki haan ka card bheja hai', never 'sent / confirmed'). action=settings*: venue, gstin, upi_id, specified "
        "(GST specified premises), gst_food, gst_hall, gst_extra, slots {morning|evening|full: {from,to}}, hold_hours, lock_days, "
        "stages [{label,pct,days_before}], cancel [{days_before,refund_pct}], terms, music_end, morning_time. action=hall*: name, "
        "kind hall|lawn|terrace|poolside|room, seated, floating, rent, rent_full. action=package*: name, diet veg|nonveg|jain, price "
        "(per plate, hers), items, min_plates. action=extra*: name, price, kind, unit event|plate|room_night|hour|nos, gst_pct. "
        "action=enquiry: text (pasted message = data) and/or name, phone, source, event_type, day, slot, guests, diet, budget. "
        "action=lead: lead, status, follow_up, lost_reason, notes. action=booking: booking (to update) or lead, hall, day, slot "
        "morning|evening|full, client, phone, event_type, guests, guarantee, menu [{package, plates}], extras [{name, qty, nights}], "
        "hall_rent, notes, beo_notes, timeline [{at, what}]. action=hold: booking, hours (clash = refused). action=release: booking. "
        "action=close* / open*: hall, day, slot. action=quote_send | contract_send | confirm | bill (actual) | message (text) | "
        "discount (amount or pct, reason) | pay_request (stage or amount): booking -> CARD for her tap. action=paid*: booking, "
        "amount, mode, ref. action=count: booking, final. action=lock: booking. action=beo: booking (function sheet). "
        "action=cancel*: booking, reason, by client|venue -> refund card. action=refund_sent*: booking, ref. action=done* / "
        "forget*: booking. * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "booking": {"type": "string"}, "lead": {"type": "string"}, "hall": {"type": "string"}, "day": {"type": "string"},
         "slot": {"type": "string"}, "client": {"type": "string"}, "name": {"type": "string"}, "phone": {"type": "string"},
         "text": {"type": "string"}, "source": {"type": "string"}, "event_type": {"type": "string"}, "guests": {"type": "integer"},
         "guarantee": {"type": "integer"}, "diet": {"type": "string"}, "budget": {"type": "number"},
         "menu": {"type": "array", "items": {"type": "object"}}, "extras": {"type": "array", "items": {"type": "object"}},
         "hall_rent": {"type": "boolean"}, "notes": {"type": "string"}, "beo_notes": {"type": "string"},
         "timeline": {"type": "array", "items": {"type": "object"}}, "hours": {"type": "integer"}, "status": {"type": "string"},
         "follow_up": {"type": "string"}, "lost_reason": {"type": "string"}, "amount": {"type": "number"}, "pct": {"type": "number"},
         "reason": {"type": "string"}, "stage": {"type": "string"}, "mode": {"type": "string"}, "ref": {"type": "string"},
         "final": {"type": "integer"}, "actual": {"type": "integer"}, "by": {"type": "string"}, "note": {"type": "string"},
         "kind": {"type": "string"}, "seated": {"type": "integer"}, "floating": {"type": "integer"}, "rent": {"type": "number"},
         "rent_full": {"type": "number"}, "price": {"type": "number"}, "items": {"type": "array", "items": {"type": "string"}},
         "min_plates": {"type": "integer"}, "unit": {"type": "string"}, "gst_pct": {"type": "number"},
         "venue": {"type": "string"}, "gstin": {"type": "string"}, "upi_id": {"type": "string"}, "specified": {"type": "boolean"},
         "gst_food": {"type": "number"}, "gst_hall": {"type": "number"}, "gst_extra": {"type": "number"},
         "slots": {"type": "object"}, "hold_hours": {"type": "integer"}, "lock_days": {"type": "integer"},
         "stages": {"type": "array", "items": {"type": "object"}}, "cancel": {"type": "array", "items": {"type": "object"}},
         "terms": {"type": "string"}, "music_end": {"type": "string"}, "morning_time": {"type": "string"},
         "address": {"type": "string"}, "email": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "banquet_dekho", "description": (
        "Read banquet work (nothing changes). what=day (today / tomorrow's functions, holds ending, final-count locks, instalments "
        "due, follow-ups, cards waiting) | free (day, slot, guests, style seated|floating) | calendar (month YYYY-MM) | leads "
        "(status) | bookings (status) | booking (booking: menu, quote, stages, payments, cards) | quote (booking) | halls | "
        "packages | extras | cards | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "free", "calendar", "leads", "bookings", "booking", "quote", "halls", "packages",
                                             "extras", "cards", "settings"]},
         "booking": {"type": "string"}, "day": {"type": "string"}, "slot": {"type": "string"}, "guests": {"type": "integer"},
         "style": {"type": "string"}, "month": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
BANQUET_LABELS = {"banquet": "Banquet ka kaam kar raha hoon", "banquet_dekho": "Banquet booking dekh raha hoon"}

_SET_KEYS = ("venue", "gstin", "address", "phone", "email", "upi_id", "specified", "gst_food", "gst_hall", "gst_extra", "slots",
             "hold_hours", "lock_days", "stages", "cancel", "terms", "music_end", "morning_time", "rules")
_BK_KEYS = ("hall", "day", "slot", "event_type", "client", "phone", "guests", "guarantee", "menu", "extras", "hall_rent", "notes",
            "beo_notes", "timeline")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..banquet import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    bk = _s(a.get("booking"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "hall":
            return S.hall_save(t, _s(a.get("hall") or a.get("name")), _s(a.get("kind")), a.get("seated"), a.get("floating"),
                               a.get("rent"), a.get("rent_full"), _s(a.get("notes")))
        if action == "package":
            return S.package_save(t, _s(a.get("name")), a.get("price"), _s(a.get("diet")), a.get("items"), a.get("min_plates"))
        if action == "extra":
            return S.extra_save(t, _s(a.get("name")), a.get("price"), _s(a.get("kind")), _s(a.get("unit")), a.get("gst_pct"))
        if action == "enquiry":
            return S.enquiry(t, _s(a.get("text")), _s(a.get("name") or a.get("client")), _s(a.get("phone")), _s(a.get("source")),
                             _s(a.get("event_type")), _s(a.get("day")), _s(a.get("slot")), a.get("guests"), _s(a.get("diet")),
                             a.get("budget"), _s(a.get("notes")), actor, conv)
        if action == "lead":
            return S.lead_update(t, _s(a.get("lead")), _s(a.get("status")), _s(a.get("follow_up")), _s(a.get("lost_reason")),
                                 _s(a.get("notes")), actor)
        if action == "booking":
            kw = {k: a[k] for k in _BK_KEYS if k in a}
            return S.booking_save(t, bk, _s(a.get("lead")), actor, conv, **kw)
        if action == "hold":
            return S.hold(t, bk, a.get("hours"), actor, conv)
        if action == "release":
            return S.release(t, bk, actor)
        if action == "close":
            return S.close_slot(t, _s(a.get("hall")), _s(a.get("day")), _s(a.get("slot")), _s(a.get("note")), actor)
        if action == "open":
            return S.open_slot(t, _s(a.get("hall")), _s(a.get("day")), _s(a.get("slot")), actor)
        if action == "quote_send":
            return S.quote_request(t, bk, actor, conv)
        if action == "contract_send":
            return S.contract_request(t, bk, actor, conv)
        if action == "confirm":
            return S.confirm_request(t, bk, actor, conv)
        if action == "discount":
            return S.discount_request(t, bk, a.get("amount"), a.get("pct"), _s(a.get("reason")), actor, conv)
        if action == "pay_request":
            return S.pay_request(t, bk, _s(a.get("stage")), a.get("amount"), actor, conv)
        if action == "message":
            return S.message_request(t, bk, _s(a.get("text")), actor, conv)
        if action == "bill":
            return S.bill_request(t, bk, a.get("actual"), actor, conv)
        if action == "paid":
            return S.paid(t, bk, a.get("amount"), _s(a.get("mode")) or "upi", _s(a.get("ref")), "", actor)
        if action == "count":
            return S.set_count(t, bk, a.get("final"), actor)
        if action == "lock":
            return S.lock_count(t, bk, actor)
        if action == "beo":
            return S.beo(t, bk, conv, actor)
        if action == "cancel":
            return S.cancel(t, bk, _s(a.get("reason")), _s(a.get("by")) or "client", actor, conv)
        if action == "refund_sent":
            return S.refund_sent(t, bk, _s(a.get("ref")), actor)
        if action == "done":
            return S.done(t, bk, actor)
        if action == "forget":
            return S.forget(t, bk, actor)
    except S.BanquetError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..banquet import service as S
    t, bk = ctx.tenant_id, _s(a.get("booking"))
    try:
        if what == "day":
            return S.day(t)
        if what == "free":
            return S.free(t, _s(a.get("day")), _s(a.get("slot")), a.get("guests"), _s(a.get("style")))
        if what == "calendar":
            return S.calendar(t, _s(a.get("month")))
        if what == "leads":
            return {"leads": S.leads(t, _s(a.get("status")))}
        if what == "bookings":
            return {"bookings": S.bookings(t, _s(a.get("status")))}
        if what == "booking":
            return S.booking_view(t, bk)
        if what == "quote":
            return S.quote(t, bk)
        if what == "halls":
            return {"halls": S.halls(t)}
        if what == "packages":
            return {"packages": S.packages(t)}
        if what == "extras":
            return {"extras": S.extras(t)}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "settings":
            return S.settings(t)
    except S.BanquetError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _banquet(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _banquet_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


BANQUET_HANDLERS = {"banquet": _banquet, "banquet_dekho": _banquet_dekho}
