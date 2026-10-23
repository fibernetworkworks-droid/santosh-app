"""Tour Guide Sahayak tools (local guide / small tour operator). `tour_guide_dekho` only reads; `tour_guide` does the work. A booking
confirmation, EVERY message to guests, a refund, a discount and any spend are only cards here: her tap in the app decides them.
Hoola never takes or pays money and never invents prices, monument timings or ticket rates."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

TOURGUIDE_TOOLS = [
    {"name": "tour_guide", "description": (
        "Local guide / tour operator coworker. action=settings*: business, guide_name, phone, city, state, upi_id, upi_name, gstin, "
        "gst_mode none|guide|tour5|tour18, languages, cancel_policy (shown upfront to guests), review_link, parallel_tours, "
        "morning_time, rules. action=tour*: tour (existing) or title (new), kind city_walk|heritage|temple|trek|food|nature|boat|"
        "day_trip, city, duration_min, price_pp / price_group (HER price), group_max, min_guests, meeting_point, includes, excludes, "
        "languages, difficulty, places [{name, stop_min, walk_min, open, close, closed_on, ticket_in, ticket_foreign, source, asi}] "
        "(timings / tickets ONLY as she said). action=enquiry: text (her pasted enquiry = data), tour, lead_name, source. "
        "action=booking: booking (existing) or new + tour, day, start_time, lead_name, phone, email, guests, language, pickup, "
        "special_needs, emergency_name, emergency_phone (locker), guest_list [{name, age, nationality in|foreign, id}] (IDs go to the "
        "locker), source, price_total*, notes. action=hold: booking (slot checked, no overbooking). action=confirm: booking, advance "
        "-> CARD (her tap confirms + sends). action=status: booking, status done|no_show|cancelled*. action=received*: booking, "
        "amount, mode, ref. action=plan: booking (day plan). action=suggest: tour, text (AI place names only). action=safety: "
        "booking (+ weather). action=roll: booking, checkpoint, present [names] | count. action=roll_sheet: booking. action=script: "
        "booking or tour, language. action=message: booking, kind reminder|custom, text -> CARD. action=review: booking, survey "
        "-> CARD. action=refund: booking, amount, reason -> CARD. action=discount: booking, amount|pct, reason -> CARD. "
        "action=spend: text (what), amount, party, booking -> CARD. action=paid_out*: card, ref. action=travel: booking, origin "
        "(Yatra Sahayak trip). action=licence*: licence, kind iitf|iitg_heritage|iitg_adventure|rlg|state|asi_site|first_aid|"
        "adventure|other, ref, holder, authority, issued, valid_to, note. action=ledger_add*: kind tip|commission_in|commission_out, "
        "amount, party, booking, note. action=forget*: booking. action=register. (* = owner only)"),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "tour", "enquiry", "booking", "hold", "confirm", "status", "received", "plan",
                                               "suggest", "safety", "roll", "roll_sheet", "script", "message", "review", "refund",
                                               "discount", "spend", "paid_out", "travel", "licence", "ledger_add", "forget", "register"]},
         "business": {"type": "string"}, "guide_name": {"type": "string"}, "phone": {"type": "string"}, "city": {"type": "string"},
         "state": {"type": "string"}, "upi_id": {"type": "string"}, "upi_name": {"type": "string"}, "gstin": {"type": "string"},
         "gst_mode": {"type": "string"}, "languages": {"type": "array", "items": {"type": "string"}}, "cancel_policy": {"type": "string"},
         "review_link": {"type": "string"}, "parallel_tours": {"type": "integer"}, "morning_time": {"type": "string"},
         "rules": {"type": "string"}, "tour": {"type": "string"}, "title": {"type": "string"}, "kind": {"type": "string"},
         "duration_min": {"type": "integer"}, "price_pp": {"type": "number"}, "price_group": {"type": "number"},
         "group_max": {"type": "integer"}, "min_guests": {"type": "integer"}, "meeting_point": {"type": "string"},
         "includes": {"type": "string"}, "excludes": {"type": "string"}, "difficulty": {"type": "string"},
         "places": {"type": "array", "items": {"type": "object"}}, "active": {"type": "boolean"}, "text": {"type": "string"},
         "booking": {"type": "string"}, "day": {"type": "string"}, "start_time": {"type": "string"}, "lead_name": {"type": "string"},
         "email": {"type": "string"}, "guests": {"type": "integer"}, "language": {"type": "string"}, "pickup": {"type": "string"},
         "special_needs": {"type": "string"}, "emergency_name": {"type": "string"}, "emergency_phone": {"type": "string"},
         "guest_list": {"type": "array", "items": {"type": "object"}}, "source": {"type": "string"}, "price_total": {"type": "number"},
         "notes": {"type": "string"}, "advance": {"type": "number"}, "status": {"type": "string"}, "amount": {"type": "number"},
         "pct": {"type": "number"}, "mode": {"type": "string"}, "ref": {"type": "string"}, "checkpoint": {"type": "string"},
         "present": {"type": "array", "items": {"type": "string"}}, "count": {"type": "integer"}, "reason": {"type": "string"},
         "party": {"type": "string"}, "card": {"type": "string"}, "survey": {"type": "boolean"}, "origin": {"type": "string"},
         "licence": {"type": "string"}, "holder": {"type": "string"}, "authority": {"type": "string"}, "issued": {"type": "string"},
         "valid_to": {"type": "string"}, "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "tour_guide_dekho", "description": (
        "Read the tour book (nothing changes). what=day (today / tomorrow tours, enquiries, cards waiting, licences) | tours | "
        "bookings (status, day) | booking (booking: group file, money, cards) | plan (booking) | cards | licences | ledger (month) | "
        "settings | rules (never-list + dated sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "tours", "bookings", "booking", "plan", "cards", "licences", "ledger", "settings", "rules"]},
         "booking": {"type": "string"}, "status": {"type": "string"}, "day": {"type": "string"}, "month": {"type": "string"}},
         "required": ["what"]}},
]
TOURGUIDE_LABELS = {"tour_guide": "Tour ka kaam kar raha hoon", "tour_guide_dekho": "Tour ki diary dekh raha hoon"}

OWNER_ONLY = ("settings", "tour", "received", "paid_out", "licence", "ledger_add", "forget")

_SET = ("business", "guide_name", "phone", "city", "state", "upi_id", "upi_name", "gstin", "gst_mode", "languages", "cancel_policy",
        "review_link", "parallel_tours", "morning_time", "rules")
_TOUR = ("title", "kind", "city", "duration_min", "price_pp", "price_group", "group_max", "min_guests", "meeting_point", "includes",
         "excludes", "languages", "difficulty", "places", "active", "notes")
_BOOK = ("tour", "day", "start_time", "lead_name", "phone", "email", "guests", "language", "pickup", "special_needs",
         "emergency_name", "source", "price_total", "notes")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..tourguide import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Tour ka kaam graahak ke liye nahi.")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    bk = _s(a.get("booking"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET if k in a})
        if action == "tour":
            return S.save_tour(t, _s(a.get("tour")), **{k: a[k] for k in _TOUR if k in a})
        if action == "enquiry":
            return S.enquiry(t, _s(a.get("text")), _s(a.get("tour")), _s(a.get("lead_name")), _s(a.get("source") or "whatsapp"), actor, conv)
        if action == "booking":
            return S.save_booking(t, bk, a.get("guest_list"), _s(a.get("emergency_phone")), actor, conv,
                                  **{k: a[k] for k in _BOOK if k in a})
        if action == "hold":
            return S.hold(t, bk, actor, conv)
        if action == "confirm":
            return S.confirm_request(t, bk, a.get("advance"), actor, conv)
        if action == "status":
            return S.set_status(t, bk, _s(a.get("status")), actor, conv, _s(a.get("note")))
        if action == "received":
            return S.received(t, bk, a.get("amount"), _s(a.get("mode") or "upi"), _s(a.get("ref")), "", actor)
        if action == "plan":
            return S.day_plan(t, bk, conv)
        if action == "suggest":
            return S.suggest_places(t, _s(a.get("tour")), _s(a.get("text")))
        if action == "roll":
            return S.roll_call(t, bk, _s(a.get("checkpoint")), a.get("present"), a.get("count"), actor, conv)
        if action == "roll_sheet":
            return S.roll_sheet(t, bk, conv)
        if action == "script":
            return S.intro_script(t, bk, _s(a.get("tour")), _s(a.get("language")), conv)
        if action == "message":
            return S.message_request(t, bk, _s(a.get("kind") or "custom"), _s(a.get("text")), actor, conv)
        if action == "review":
            return S.review_request(t, bk, bool(a.get("survey")), actor, conv)
        if action == "refund":
            return S.refund_request(t, bk, a.get("amount"), _s(a.get("reason")), actor, conv)
        if action == "discount":
            return S.discount_request(t, bk, a.get("amount"), a.get("pct"), _s(a.get("reason")), actor, conv)
        if action == "spend":
            return S.spend_request(t, _s(a.get("text")), a.get("amount"), _s(a.get("party")), bk, actor, conv)
        if action == "paid_out":
            return S.paid_out(t, _s(a.get("card")), _s(a.get("ref")), _s(a.get("mode") or "upi"), actor)
        if action == "travel":
            return S.travel_link(t, bk, _s(a.get("origin")), actor, conv)
        if action == "licence":
            return S.save_licence(t, _s(a.get("licence")), _s(a.get("kind")), _s(a.get("ref")), _s(a.get("holder")),
                                  _s(a.get("authority")), _s(a.get("issued")), _s(a.get("valid_to")), _s(a.get("note")), actor)
        if action == "ledger_add":
            return S.ledger_add(t, _s(a.get("kind")), a.get("amount"), _s(a.get("party")), bk, _s(a.get("note")), "", actor)
        if action == "forget":
            return S.forget(t, bk, actor)
        if action == "register":
            return S.register_file(t, conv)
    except (S.TourError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError(f"Anjaan action: {action}")


async def tour_guide(ctx: Ctx, action, **a: Any):
    action = str(action)
    if action == "safety":
        from ..tourguide import service as S
        try:
            return await S.weather_check(ctx.tenant_id, _s(a.get("booking")), ctx.conversation_id)
        except S.TourError as e:
            raise ToolError(str(e))
    return await asyncio.to_thread(_act, ctx, action, a)


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..tourguide import rules as R
    from ..tourguide import service as S
    t = ctx.tenant_id
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "tours":
            return {"tours": S.tours(t)}
        if what == "bookings":
            return {"bookings": S.bookings(t, _s(a.get("status")), _s(a.get("day")))}
        if what == "booking":
            return S.booking_view(t, _s(a.get("booking")))
        if what == "plan":
            return S.day_plan(t, _s(a.get("booking")), publish=False)
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "licences":
            return {"licences": S.licences(t)}
        if what == "ledger":
            return S.ledger(t, _s(a.get("month")))
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}
    except (S.TourError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError(f"Anjaan what: {what}")


async def tour_guide_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


TOURGUIDE_HANDLERS = {"tour_guide": tour_guide, "tour_guide_dekho": tour_guide_dekho}
