"""Homestay Sahayak tools (homestay / B&B / farm stay / villa host, 1-6 rooms). `homestay_dekho` only reads; `homestay` does the work.
Every message to a guest, every cancel / refund / spend is only a CARD here: her tap in the app decides. A double booking is refused
in code from every source. Hoola never logs in to an OTA and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

HOMESTAY_TOOLS = [
    {"name": "homestay", "description": (
        "Homestay / B&B host's coworker. action=settings (owner): business, host_name, phone, address, city, state (MH/GA/KL/HP...), pin, "
        "map_link, kind homestay|bnb|farmstay|villa, in_flat, serves_food, upi_id, upi_name, gstin, checkin_time, checkout_time, house_rules, "
        "checkin_info, advance_pct, hold_hours, policy (HER words '7 din pehle 100%, 2 din pehle 50%'), menu ('breakfast 250, dinner 400'), "
        "count_children, review_link, police_intimation, staff, morning_time. action=room (owner): room (existing) or name, kind, beds, "
        "base_guests, max_guests, base_rate, weekend_rate, extra_person (HER rates), special {date: rate}, ota_names, active. "
        "action=guest: guest or name + phone, country (IN or other), city, email, aadhaar / passport / visa / id_kind+id_number (straight "
        "into her Pehchaan Locker, only masked kept), form_c {nationality, visa_type, ...}, no_messages. action=book: room(s), check_in, "
        "check_out (or nights), guest or name+phone, adults, children, addons ['breakfast', ...], notes -> HOLD + confirmation CARD (her "
        "tap sends it = pakki). Taken nights are REFUSED. action=block: room(s), start, end, note. action=unblock: booking. action=update: "
        "booking + check_in/check_out/rooms/adults/children/addons/notes (total/advance owner only). action=confirm (owner). action=checkin: "
        "booking, id_seen. action=checkout: booking. action=no_show (owner). action=form_c_done: booking, ref, stage arrival|departure. "
        "action=check: booking, item id_seen|police|house_rules_signed|keys_given. action=received (owner): booking, amount, mode, ref. "
        "action=pay_link: booking, kind advance|balance. action=message: booking, kind confirmation|checkin_info|house_rules|payment|review|"
        "cancellation|custom, text -> CARD. action=edit_message: card, text. action=cancel: booking, by guest|host, reason, refund -> CARD. "
        "action=refund_done (owner): booking, amount, ref. action=spend: what, amount, vendor, booking -> CARD. action=spend_paid (owner): card. "
        "action=ota_email: text (her pasted Airbnb / Booking.com / MMT / Agoda mail) or file_id, room. action=ical: file_id (her .ics export), "
        "room, source. action=task_add: what, room, day, assigned. action=task_done: task, note, skip, assigned. action=registration (owner): "
        "number, valid_to, item tourism|local|fire|police|frro|fssai|gst|society, done, ref. action=register: month (Excel). action=forget "
        "(owner): guest (DPDP)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "room", "guest", "book", "block", "unblock", "update", "confirm", "checkin",
                                               "checkout", "no_show", "form_c_done", "check", "received", "pay_link", "message",
                                               "edit_message", "cancel", "refund_done", "spend", "spend_paid", "ota_email", "ical",
                                               "task_add", "task_done", "registration", "register", "forget"]},
         "business": {"type": "string"}, "host_name": {"type": "string"}, "phone": {"type": "string"}, "address": {"type": "string"},
         "city": {"type": "string"}, "state": {"type": "string"}, "pin": {"type": "string"}, "map_link": {"type": "string"},
         "kind": {"type": "string"}, "in_flat": {"type": "boolean"}, "serves_food": {"type": "boolean"}, "upi_id": {"type": "string"},
         "upi_name": {"type": "string"}, "gstin": {"type": "string"}, "checkin_time": {"type": "string"}, "checkout_time": {"type": "string"},
         "house_rules": {"type": "string"}, "checkin_info": {"type": "string"}, "advance_pct": {"type": "number"},
         "hold_hours": {"type": "integer"}, "policy": {"type": "string"}, "menu": {"type": "string"}, "count_children": {"type": "boolean"},
         "review_link": {"type": "string"}, "police_intimation": {"type": "boolean"}, "staff": {"type": "string"},
         "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "room": {"type": "string"}, "rooms": {"type": "array", "items": {"type": "string"}}, "name": {"type": "string"},
         "beds": {"type": "string"}, "base_guests": {"type": "integer"}, "max_guests": {"type": "integer"}, "base_rate": {"type": "number"},
         "weekend_rate": {"type": "number"}, "extra_person": {"type": "number"}, "special": {"type": "object"},
         "ota_names": {"type": "array", "items": {"type": "string"}}, "active": {"type": "boolean"},
         "guest": {"type": "string"}, "country": {"type": "string"}, "email": {"type": "string"}, "aadhaar": {"type": "string"},
         "passport": {"type": "string"}, "visa": {"type": "string"}, "id_kind": {"type": "string"}, "id_number": {"type": "string"},
         "form_c": {"type": "object"}, "no_messages": {"type": "boolean"},
         "booking": {"type": "string"}, "check_in": {"type": "string"}, "check_out": {"type": "string"}, "nights": {"type": "integer"},
         "adults": {"type": "integer"}, "children": {"type": "integer"}, "addons": {"type": "array", "items": {}},
         "notes": {"type": "string"}, "total": {"type": "number"}, "advance": {"type": "number"}, "start": {"type": "string"},
         "end": {"type": "string"}, "note": {"type": "string"}, "id_seen": {"type": "boolean"}, "ref": {"type": "string"},
         "stage": {"type": "string"}, "item": {"type": "string"}, "done": {"type": "boolean"}, "amount": {"type": "number"},
         "mode": {"type": "string"}, "text": {"type": "string"}, "card": {"type": "string"}, "by": {"type": "string"},
         "reason": {"type": "string"}, "refund": {"type": "number"}, "what": {"type": "string"}, "vendor": {"type": "string"},
         "file_id": {"type": "string"}, "source": {"type": "string"}, "task": {"type": "string"}, "day": {"type": "string"},
         "assigned": {"type": "string"}, "skip": {"type": "boolean"}, "number": {"type": "string"}, "valid_to": {"type": "string"},
         "month": {"type": "string"}},
         "required": ["action"]}},
    {"name": "homestay_dekho", "description": (
        "Read the homestay book (nothing changes). what=day (arrivals, departures, in house, Form C pending, cleaning, dues, holds, cards) | "
        "availability (check_in, check_out) | calendar (start, days) | rooms | guests (q) | bookings (status, when upcoming|past) | booking "
        "(booking) | form_c (booking: data sheet for HER filing on indianfrro.gov.in) | cards | tasks | registration (state checklist) | "
        "report (month YYYY-MM: occupancy, earnings, ADR, RevPAR, by source) | settings | rules (never-list + dated sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "availability", "calendar", "rooms", "guests", "bookings", "booking", "form_c", "cards",
                                             "tasks", "registration", "report", "settings", "rules"]},
         "booking": {"type": "string"}, "check_in": {"type": "string"}, "check_out": {"type": "string"}, "start": {"type": "string"},
         "days": {"type": "integer"}, "q": {"type": "string"}, "status": {"type": "string"}, "when": {"type": "string"},
         "month": {"type": "string"}},
         "required": ["what"]}},
]
HOMESTAY_LABELS = {"homestay": "Homestay ka kaam kar raha hoon", "homestay_dekho": "Homestay ka hisaab dekh raha hoon"}

OWNER_ONLY = ("settings", "room", "confirm", "no_show", "received", "refund_done", "spend_paid", "registration", "forget")
_SET = ("business", "host_name", "phone", "address", "city", "state", "pin", "map_link", "kind", "in_flat", "serves_food", "upi_id",
        "upi_name", "gstin", "checkin_time", "checkout_time", "house_rules", "checkin_info", "advance_pct", "hold_hours", "policy",
        "menu", "count_children", "review_link", "police_intimation", "staff", "morning_time", "rules")
_ROOM = ("name", "kind", "beds", "base_guests", "max_guests", "base_rate", "weekend_rate", "extra_person", "special", "ota_names", "active",
         "notes")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _rooms(a: dict) -> Any:
    return a.get("rooms") or a.get("room") or ""


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..homestay import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Homestay ka kaam graahak ke liye nahi.")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    bk = _s(a.get("booking"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET if k in a})
        if action == "room":
            return S.save_room(t, _s(a.get("room")), **{k: a[k] for k in _ROOM if k in a})
        if action == "guest":
            gkw = {k: a[k] for k in ("email", "country", "city", "no_messages", "notes") if k in a}
            return S.save_guest(t, _s(a.get("guest")), _s(a.get("name")), _s(a.get("phone")), _s(a.get("aadhaar")), _s(a.get("passport")),
                                _s(a.get("visa")), _s(a.get("id_kind")), _s(a.get("id_number")),
                                a.get("form_c") if isinstance(a.get("form_c"), dict) else None, **gkw)
        if action == "book":
            return S.new_booking(t, _rooms(a), _s(a.get("check_in")), _s(a.get("check_out")), _s(a.get("guest")), _s(a.get("name")),
                                 _s(a.get("phone")), int(a.get("adults") or 2), int(a.get("children") or 0), a.get("addons") or [],
                                 "direct", "", a.get("total") if _owner(ctx) else None, a.get("advance") if _owner(ctx) else None,
                                 _s(a.get("notes")), int(a.get("nights") or 0), actor, conv)
        if action == "block":
            return S.block(t, _rooms(a), _s(a.get("start") or a.get("check_in")), _s(a.get("end") or a.get("check_out")), _s(a.get("note")), actor)
        if action == "unblock":
            return S.unblock(t, bk, actor)
        if action == "update":
            return S.update_booking(t, bk, actor, **{k: a[k] for k in S._UPD if a.get(k) is not None})
        if action == "confirm":
            return S.confirm(t, bk, actor)
        if action == "checkin":
            return S.check_in(t, bk, actor, bool(a.get("id_seen")))
        if action == "checkout":
            return S.check_out(t, bk, actor)
        if action == "no_show":
            return S.no_show(t, bk, actor)
        if action == "form_c_done":
            return S.form_c_done(t, bk, _s(a.get("ref")), _s(a.get("stage") or "arrival"), actor)
        if action == "check":
            return S.mark_check(t, bk, _s(a.get("item")), bool(a.get("done", True)), _s(a.get("ref")), actor)
        if action == "received":
            return S.received(t, bk, a.get("amount"), "", _s(a.get("mode") or "upi"), _s(a.get("ref")), "", actor)
        if action == "pay_link":
            return S.pay_link(t, bk, _s(a.get("kind")))
        if action == "message":
            return S.draft_message(t, bk, _s(a.get("kind") or "custom"), _s(a.get("text")), actor, conv)
        if action == "edit_message":
            return S.edit_message(t, _s(a.get("card")), _s(a.get("text")))
        if action == "cancel":
            return S.cancel_request(t, bk, _s(a.get("by") or "guest"), _s(a.get("reason")), a.get("refund"), actor, conv)
        if action == "refund_done":
            return S.refund_done(t, bk, a.get("amount"), _s(a.get("ref")), actor)
        if action == "spend":
            return S.spend_request(t, _s(a.get("what")), a.get("amount"), _s(a.get("vendor")), bk, actor, conv)
        if action == "spend_paid":
            return S.spend_paid(t, _s(a.get("card")), _s(a.get("ref")), actor)
        if action == "ota_email":
            text = _s(a.get("text")) or (S.file_text(t, _s(a.get("file_id")), 200_000) if a.get("file_id") else "")
            if not text.strip():
                raise ToolError("OTA ka mail paste kijiye (text) ya file bhejiye.")
            return S.ota_email(t, text, _s(a.get("room")), actor, conv)
        if action == "ical":
            if not a.get("file_id"):
                raise ToolError("OTA se export ki hui .ics file chat mein bhejiye (file_id).")
            return S.ical_import(t, S.file_text(t, _s(a.get("file_id"))), _s(a.get("room")), _s(a.get("source")), actor, conv)
        if action == "task_add":
            return S.task_add(t, _s(a.get("what")), _s(a.get("room")), _s(a.get("day")), _s(a.get("assigned")))
        if action == "task_done":
            return S.task_done(t, _s(a.get("task")), _s(a.get("note")), actor, bool(a.get("skip")), _s(a.get("assigned")))
        if action == "registration":
            return S.registration_update(t, _s(a.get("number")), _s(a.get("valid_to")), _s(a.get("item")), bool(a.get("done", True)),
                                         _s(a.get("ref")))
        if action == "register":
            return S.register_file(t, _s(a.get("month")), conv)
        if action == "forget":
            return S.forget(t, _s(a.get("guest")), actor)
    except (S.StayError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..homestay import rules as R
    from ..homestay import service as S
    t = ctx.tenant_id
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Homestay ki jaankari graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "availability":
            return S.availability(t, _s(a.get("check_in")), _s(a.get("check_out")))
        if what == "calendar":
            return S.calendar(t, _s(a.get("start")), int(a.get("days") or 31))
        if what == "rooms":
            return {"rooms": S.rooms(t)}
        if what == "guests":
            return {"guests": S.guests(t, _s(a.get("q")))}
        if what == "bookings":
            return {"bookings": S.bookings(t, _s(a.get("status")), _s(a.get("when")))}
        if what == "booking":
            return S.booking_view(t, _s(a.get("booking")))
        if what == "form_c":
            return S.form_c(t, _s(a.get("booking")))
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status") or "waiting"))}
        if what == "tasks":
            return {"tasks": S.tasks(t, _s(a.get("status") if a.get("status") is not None else "open"))}
        if what == "registration":
            return S.registration(t)
        if what == "report":
            return S.report(t, _s(a.get("month")))
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}
    except (S.StayError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def homestay(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def homestay_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


HOMESTAY_HANDLERS = {"homestay": homestay, "homestay_dekho": homestay_dekho}
