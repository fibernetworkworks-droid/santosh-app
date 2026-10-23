"""Shaadi Sahayak tools (wedding planner's coworker). `shaadi_dekho` only reads; `shaadi` does the work.

Vendor booking / advance, vendor payments, any spend, the client quote / payment request and every message or invite to guests
become CARDS here; only HER tap in the app (API) decides them. Hoola never invents a price, date or muhurat (the family pandit
decides it), never sends a message, never pays or collects. The shagun / gift register is owner-only and shown masked here."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "new", "update", "function", "timeline", "checklist", "guest", "guests_import", "rsvp", "room", "room_assign",
            "trip", "vendor", "book", "pay", "paid", "spend", "spend_paid", "budget", "quote", "client_pay", "invite_text", "message",
            "invite_design", "gift", "gift_remove", "gift_list", "forget"]
_OWNER_ONLY = {"settings", "paid", "spend_paid", "gift", "gift_remove", "gift_list", "forget", "trip"}

SHAADI_TOOLS = [
    {"name": "shaadi", "description": (
        "Wedding planner's coworker (Indian weddings, every community). NEVER invent a price, date or MUHURAT (the family's pandit "
        "decides it; store it only as she says, with muhurat_by). Booking / advance / payment / spend / client quote / any message "
        "to guests or vendors = a CARD for her tap; say 'aapki haan ka card bheja hai'. action=new: title, community (hindu_north, "
        "marathi, gujarati, punjabi, sikh, marwari, bengali, tamil, telugu, malayali, kannada, jain, muslim, christian, parsi, "
        "interfaith, other), bride, groom, client, client_phone, city, state, venue, guests_estimate, budget, functions [names], "
        "dates {function: DD-MM-YYYY}. update: wedding + fields. function: wedding, fn, name, date, start, end, venue, side, muhurat, "
        "muhurat_by, notes, add, remove. timeline: wedding, fn, rows [{time, what, who}] or starter. checklist: wedding, item, done | "
        "what+days (new). guest: wedding, name, side bride|groom|common, phone, adults, kids, group, invited [fns], diet, city, "
        "needs_room, arrive, depart, travel_mode, travel_from. guests_import: file_id. rsvp: wedding, guest, answer yes|no|maybe, fn. "
        "room: place, label, capacity, check_in, check_out, rate, count. room_assign: guest, room (overbooking refused). trip*: from "
        "(city -> Travel Sahayak draft). vendor: name, kind, phone, functions, quote (HER word), quote_note, per_plate, plates, "
        "schedule [{label, amount|pct, due}]. book: vendor -> CARD. pay: vendor, item -> CARD. paid*: vendor, item, amount, ref. spend: "
        "what, amount, head, fn, payee -> CARD. budget: amount, head, fn. quote: lines [{name, amount}] -> client CARD (agency). "
        "client_pay: stage. invite_text: kind invite|rsvp, fn, lang hinglish|hindi|marathi|english. message: text, kind, to "
        "guests|vendors, fn, side, pending -> CARD. invite_design (Brand Sahayak). gift*: giver, value, kind cash|upi|cheque|gold|item, "
        "what, relation, side, for_whom, fn. gift_list*: for_whom bride|groom (Dowry Rules 1985 list PDF). forget*: wedding (DPDP, after done). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "wedding": {"type": "string"}, "title": {"type": "string"},
         "community": {"type": "string"}, "bride": {"type": "string"}, "groom": {"type": "string"}, "client": {"type": "string"},
         "client_phone": {"type": "string"}, "city": {"type": "string"}, "state": {"type": "string"}, "venue": {"type": "string"},
         "guests_estimate": {"type": "integer"}, "budget": {"type": "number"}, "age_bride": {"type": "integer"},
         "age_groom": {"type": "integer"}, "functions": {"type": "array", "items": {"type": "string"}}, "dates": {"type": "object"},
         "status": {"type": "string"}, "fn": {"type": "string"}, "name": {"type": "string"}, "date": {"type": "string"},
         "start": {"type": "string"}, "end": {"type": "string"}, "side": {"type": "string"}, "muhurat": {"type": "string"},
         "muhurat_by": {"type": "string"}, "notes": {"type": "string"}, "add": {"type": "boolean"}, "remove": {"type": "boolean"},
         "rows": {"type": "array", "items": {"type": "object"}}, "starter": {"type": "boolean"}, "item": {"type": "string"},
         "done": {"type": "boolean"}, "what": {"type": "string"}, "days": {"type": "integer"}, "phone": {"type": "string"},
         "adults": {"type": "integer"}, "kids": {"type": "integer"}, "group": {"type": "string"},
         "invited": {"type": "array", "items": {"type": "string"}}, "diet": {"type": "string"}, "needs_room": {"type": "boolean"},
         "arrive": {"type": "string"}, "depart": {"type": "string"}, "travel_mode": {"type": "string"}, "travel_from": {"type": "string"},
         "file_id": {"type": "string"}, "guest": {"type": "string"}, "answer": {"type": "string"}, "place": {"type": "string"},
         "label": {"type": "string"}, "capacity": {"type": "integer"}, "check_in": {"type": "string"}, "check_out": {"type": "string"},
         "rate": {"type": "number"}, "count": {"type": "integer"}, "room": {"type": "string"}, "from": {"type": "string"},
         "vendor": {"type": "string"}, "kind": {"type": "string"}, "quote": {"type": "number"}, "quote_note": {"type": "string"},
         "per_plate": {"type": "number"}, "plates": {"type": "integer"}, "schedule": {"type": "array", "items": {"type": "object"}},
         "amount": {"type": "number"}, "ref": {"type": "string"}, "head": {"type": "string"}, "payee": {"type": "string"},
         "card": {"type": "string"}, "lines": {"type": "array", "items": {"type": "object"}}, "stage": {"type": "integer"},
         "lang": {"type": "string"}, "text": {"type": "string"}, "to": {"type": "string"}, "pending": {"type": "boolean"},
         "guests": {"type": "array", "items": {"type": "string"}}, "words": {"type": "string"}, "giver": {"type": "string"},
         "value": {"type": "number"}, "relation": {"type": "string"}, "for_whom": {"type": "string"}, "gift": {"type": "string"},
         "include_gifts": {"type": "boolean"}, "firm": {"type": "string"}, "mode": {"type": "string"}, "gstin": {"type": "string"},
         "upi_id": {"type": "string"}, "fee_mode": {"type": "string"}, "fee_value": {"type": "number"}, "gst_pct": {"type": "number"},
         "stages": {"type": "array", "items": {"type": "object"}}, "terms": {"type": "string"}, "validity_days": {"type": "integer"},
         "morning_time": {"type": "string"}, "rules": {"type": "string"}, "vendor_kind": {"type": "string"}},
         "required": ["action"]}},
    {"name": "shaadi_dekho", "description": (
        "Read wedding work (nothing changes). what=day (this week's functions, checklist due, vendor payments due, cards waiting) | "
        "weddings | wedding (full file) | panchang (tithi / nakshatra / holidays for HER dates; muhurat is the pandit's) | days "
        "(day-wise timeline) | checklist | guests (q, side, fn, answer) | headcount (per function, for the caterer) | rooms | travel | "
        "vendors (with quote comparison) | budget (planned / committed / paid by function and head) | cards | gifts (shagun totals, "
        "names masked) | registration (marriage registration checklist by law) | settings | communities."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "weddings", "wedding", "panchang", "days", "checklist", "guests", "headcount", "rooms",
                                             "travel", "vendors", "budget", "cards", "gifts", "registration", "settings", "communities"]},
         "wedding": {"type": "string"}, "q": {"type": "string"}, "side": {"type": "string"}, "fn": {"type": "string"},
         "answer": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
SHAADI_LABELS = {"shaadi": "Shaadi ka kaam kar raha hoon", "shaadi_dekho": "Shaadi ki file dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..shaadi import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    w = _s(a.get("wedding"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "new":
            keys = ("title", "community", "bride", "groom", "client", "client_phone", "city", "state", "venue", "guests_estimate",
                    "budget", "age_bride", "age_groom", "functions", "dates")
            return S.wedding_new(t, **{k: a[k] for k in keys if k in a}, actor=actor, conv=conv)
        if action == "update":
            return S.wedding_update(t, w, actor, **{k: a[k] for k in S._W_KEYS + ("budget", "age_bride", "age_groom") if k in a})
        if action == "function":
            return S.fn_set(t, w, _s(a.get("fn")), _s(a.get("name")), _s(a.get("date")), _s(a.get("start")), _s(a.get("end")),
                            _s(a.get("venue")), _s(a.get("side")), _s(a.get("muhurat")), _s(a.get("muhurat_by")), _s(a.get("notes")),
                            bool(a.get("remove")), bool(a.get("add")), actor)
        if action == "timeline":
            return S.timeline_set(t, w, _s(a.get("fn")), a.get("rows"), bool(a.get("starter")), actor)
        if action == "checklist":
            return S.checklist_mark(t, w, _s(a.get("item")), a.get("done", True) is not False, _s(a.get("what")), a.get("days"), actor)
        if action == "guest":
            keys = ("side", "phone", "adults", "kids", "group", "invited", "diet", "city", "needs_room", "arrive", "depart", "travel_mode",
                    "travel_from", "notes", "guest")
            return S.guest_add(t, w, _s(a.get("name")), **{k: a[k] for k in keys if k in a}, actor=actor)
        if action == "guests_import":
            return S.guests_import(t, w, _s(a.get("file_id")), side=_s(a.get("side")))
        if action == "rsvp":
            return S.rsvp(t, w, _s(a.get("guest") or a.get("name")), _s(a.get("answer")), _s(a.get("fn")), a.get("adults"), a.get("kids"), actor)
        if action == "room":
            return S.room_add(t, w, _s(a.get("place")), _s(a.get("label")), a.get("capacity"), _s(a.get("check_in")), _s(a.get("check_out")),
                              a.get("rate"), a.get("count"), _s(a.get("notes")))
        if action == "room_assign":
            return S.room_assign(t, w, _s(a.get("guest") or a.get("name")), _s(a.get("room")), bool(a.get("remove")))
        if action == "trip":
            return S.to_trip(t, w, _s(a.get("from")), actor, conv)
        if action == "vendor":
            keys = ("kind", "phone", "functions", "quote", "quote_note", "per_plate", "plates", "schedule", "notes", "vendor")
            return S.vendor_add(t, w, _s(a.get("name")), **{k: a[k] for k in keys if k in a}, actor=actor)
        if action == "book":
            return S.book_request(t, w, _s(a.get("vendor") or a.get("name")), actor, conv)
        if action == "pay":
            return S.pay_request(t, w, _s(a.get("vendor") or a.get("name")), _s(a.get("item")), actor, conv)
        if action == "paid":
            return S.mark_paid(t, w, _s(a.get("vendor") or a.get("name")), _s(a.get("item")), a.get("amount"), _s(a.get("ref")), actor)
        if action == "spend":
            return S.spend_request(t, w, _s(a.get("what")), a.get("amount"), _s(a.get("head")), _s(a.get("fn")), _s(a.get("payee")), actor, conv)
        if action == "spend_paid":
            return S.spend_paid(t, _s(a.get("card")), _s(a.get("ref")), actor)
        if action == "budget":
            return S.budget_set(t, w, a.get("amount"), _s(a.get("head")), _s(a.get("fn")), actor)
        if action == "quote":
            return S.quote_request(t, w, a.get("lines"), actor, conv)
        if action == "client_pay":
            return S.client_pay_request(t, w, int(a.get("stage") or 0), actor, conv)
        if action == "invite_text":
            return S.invite_text(t, w, _s(a.get("kind")) or "invite", _s(a.get("fn")), _s(a.get("lang")) or "hinglish")
        if action == "message":
            return S.message_request(t, w, _s(a.get("text")), _s(a.get("kind")) or "invite", _s(a.get("to")) or "guests", _s(a.get("fn")),
                                     _s(a.get("side")), bool(a.get("pending")), a.get("guests"), _s(a.get("lang")) or "hinglish",
                                     _s(a.get("vendor_kind")), actor, conv)
        if action == "invite_design":
            return S.invite_design(t, w, _s(a.get("fn")), _s(a.get("words")), conv)
        if action == "gift":
            return S.gift_add(t, w, _s(a.get("giver") or a.get("name")), a.get("value") if a.get("value") is not None else a.get("amount"),
                              _s(a.get("kind")) or "cash", _s(a.get("what")), _s(a.get("relation")), _s(a.get("side")),
                              _s(a.get("for_whom")) or "both", _s(a.get("fn")), _s(a.get("date")), _s(a.get("notes")), actor)
        if action == "gift_list":
            return S.gift_list_file(t, w, _s(a.get("for_whom")) or "bride", actor, conv)
        if action == "gift_remove":
            return S.gift_remove(t, _s(a.get("gift")), actor)
        if action == "forget":
            return S.forget(t, w, bool(a.get("include_gifts")), actor)
    except S.ShaadiError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..shaadi import service as S
    t, w = ctx.tenant_id, _s(a.get("wedding"))
    try:
        if what == "day":
            return S.day(t)
        if what == "weddings":
            return {"weddings": S.weddings(t, _s(a.get("status")))}
        if what == "wedding":
            out = S.wedding_view(t, w)
            if not _owner(ctx):
                out.pop("gift_total", None)
            return out
        if what == "panchang":
            return S.panchang(t, w)
        if what == "days":
            return S.day_plan(t, w)
        if what == "checklist":
            return S.checklist(t, w)
        if what == "guests":
            return S.guests(t, w, _s(a.get("q")), _s(a.get("side")), _s(a.get("fn")), _s(a.get("answer")))
        if what == "headcount":
            return S.headcount(t, w)
        if what == "rooms":
            return S.rooms(t, w)
        if what == "travel":
            return S.travel_list(t, w)
        if what == "vendors":
            return S.vendors(t, w)
        if what == "budget":
            return S.budget(t, w)
        if what == "cards":
            return {"cards": S.cards(t, w, _s(a.get("status")))}
        if what == "gifts":
            if not _owner(ctx):
                raise ToolError("Shagun register sirf owner ke liye hai.")
            return S.gifts(t, w, full=False)
        if what == "registration":
            return S.registration(t, w)
        if what == "settings":
            return S.settings(t)
        if what == "communities":
            from ..shaadi import rules as R
            return {"communities": {k: {"label": v["label"], "functions": [R.F[f] for f in v["fns"]]} for k, v in R.COMMUNITIES.items()},
                    "vendor_kinds": R.VENDOR_KINDS}
    except S.ShaadiError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _shaadi(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _shaadi_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


SHAADI_HANDLERS = {"shaadi": _shaadi, "shaadi_dekho": _shaadi_dekho}
