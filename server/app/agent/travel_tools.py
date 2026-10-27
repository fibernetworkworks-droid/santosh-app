"""Yatra Sahayak tools (travel agent). `travel_dekho` only reads; `travel` plans trips, compares the options she pasted (or her
partner API found), keeps documents ready and asks for bookings / client quotes ONLY as cards: her tap in the app decides
(there is no approve action here). Hoola never pays: a booking runs up to the payment page and she pays herself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

TRAVEL_TOOLS = [
    {"name": "travel", "description": (
        "Travel agent / trip planner for her family or her travel agency's clients. action=new: text (her words), destination, "
        "origin, start_date, end_date (DD-MM-YYYY), travellers [{name, age, gender, berth, id_kind, id_ref}], budget, prefs, kind "
        "(family|pilgrimage|beach|hill|business|honeymoon|school), for_client, client_name, client_phone, client_email, country -> "
        "trip T-0001 + visa / holiday notes. action=update: trip + fields. action=traveller: trip, name, age, gender, berth, id_kind "
        "(aadhaar|passport|voter|dl|pan), id_ref ({id:...} from the Pehchaan Locker; a plain number she said goes into the locker by "
        "itself), passport_expiry, op add|remove. action=itinerary: trip, ask -> day by day plan (only real places; never invent "
        "times, fares or opening hours). action=options: trip, text (the quotes / search results SHE pasted: one per line) or "
        "options [{mode train|flight|bus|hotel|cab, name, code, day, depart, arrive, duration, price, per_night, rating, cls, "
        "quota}], leg out|back|stay, day -> saved; never make up a fare. action=partner_search: trip, origin_code, dest_code, day "
        "(her partner API key must be joined in the app). action=compare: trip, mode. action=choose: trip, option, on. "
        "action=train: day, cls, depart, quota -> ARP / Tatkal / chart times (no fares). action=docs: trip, item, have, file_id. "
        "action=pack: trip, item, done. action=book: trip, option -> ONLY a booking card for her tap (never say it is booked or "
        "approved; after her tap Hoola's browser fills the site and stops at payment, she pays). action=booked: booking, pnr, paid "
        "(after she says it is booked). action=quote: trip -> client quote card with her markup (her tap before the PDF / "
        "message). action=cancel / forget (owner): trip. action=settings (owner): mode own|agency, agency_name, contact, home_city, "
        "state, markup_pct, markup_flat, gst_pct, gstin, terms, rules, morning_time. Never ask for or repeat full ID numbers, "
        "card numbers, OTPs or passwords."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "update", "traveller", "itinerary", "options", "partner_search", "compare",
                                               "choose", "remove_option", "train", "docs", "pack", "book", "booked", "quote",
                                               "cancel", "forget", "settings"]},
         "trip": {"type": "string"}, "text": {"type": "string"}, "title": {"type": "string"}, "destination": {"type": "string"},
         "origin": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"},
         "travellers": {"type": "array", "items": {"type": "object"}}, "budget": {"type": "string"}, "prefs": {"type": "string"},
         "kind": {"type": "string"}, "for_client": {"type": "boolean"}, "client_name": {"type": "string"},
         "client_phone": {"type": "string"}, "client_email": {"type": "string"}, "country": {"type": "string"},
         "notes": {"type": "string"}, "status": {"type": "string"}, "name": {"type": "string"}, "age": {"type": "integer"},
         "gender": {"type": "string"}, "berth": {"type": "string"}, "id_kind": {"type": "string"}, "id_ref": {"type": "string"},
         "id_number": {"type": "string"}, "passport_expiry": {"type": "string"}, "op": {"type": "string"},
         "ask": {"type": "string"}, "options": {"type": "array", "items": {"type": "object"}}, "mode": {"type": "string"},
         "leg": {"type": "string"}, "day": {"type": "string"}, "option": {"type": "string"}, "on": {"type": "boolean"},
         "origin_code": {"type": "string"}, "dest_code": {"type": "string"}, "provider": {"type": "string"},
         "cls": {"type": "string"}, "depart": {"type": "string"}, "quota": {"type": "string"}, "item": {"type": "string"},
         "have": {"type": "boolean"}, "file_id": {"type": "string"}, "done": {"type": "boolean"}, "booking": {"type": "string"},
         "pnr": {"type": "string"}, "paid": {"type": "string"}, "failed": {"type": "boolean"}, "mode_setting": {"type": "string"},
         "agency_name": {"type": "string"}, "contact": {"type": "string"}, "home_city": {"type": "string"},
         "state": {"type": "string"}, "markup_pct": {"type": "number"}, "markup_flat": {"type": "string"},
         "gst_pct": {"type": "number"}, "gstin": {"type": "string"}, "terms": {"type": "string"}, "rules": {"type": "string"},
         "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "travel_dekho", "description": (
        "Read the travel desk (nothing changes). what=day (trips in the next 7 days, missing documents, cards waiting) | trips "
        "(status open|draft|planned|booked|done) | trip (trip: travellers masked, itinerary, options, bookings, quotes, documents, "
        "packing, booking windows, visa / passport notes) | compare (trip, mode) | docs (trip) | train (day, cls, depart, quota) | "
        "visa (country) | links (mode, origin, destination, day) | settings | sources."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "trips", "trip", "compare", "docs", "train", "visa", "links", "settings", "sources"]},
         "trip": {"type": "string"}, "status": {"type": "string"}, "mode": {"type": "string"}, "day": {"type": "string"},
         "cls": {"type": "string"}, "depart": {"type": "string"}, "quota": {"type": "string"}, "country": {"type": "string"},
         "origin": {"type": "string"}, "destination": {"type": "string"}},
         "required": ["what"]}},
]
TRAVEL_LABELS = {"travel": "Yatra ka plan sambhal raha hoon", "travel_dekho": "Yatra ki details dekh raha hoon"}

_OWNER_ONLY = {"settings", "cancel", "forget", "booked"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..travel import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yatra desk graahakon ke liye seedha nahi hai.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    tr = _s(a.get("trip"))
    try:
        if action == "new":
            keys = ("text", "title", "origin", "destination", "start_date", "end_date", "travellers", "budget", "prefs", "kind",
                    "for_client", "client_name", "client_phone", "client_email", "country")
            return S.new_trip(t, actor=actor, conv=conv, **{k: a[k] for k in keys if k in a})
        if action == "update":
            keys = ("title", "origin", "destination", "kind", "client_name", "client_email", "client_phone", "start_date", "end_date",
                    "country", "prefs", "notes", "budget", "status")
            return S.update_trip(t, tr, actor=actor, **{k: a[k] for k in keys if k in a})
        if action == "traveller":
            keys = ("name", "age", "gender", "berth", "id_kind", "id_ref", "id_number", "passport_expiry")
            return S.traveller(t, tr, _s(a.get("op") or "add"), actor=actor, **{k: a[k] for k in keys if k in a})
        if action == "itinerary":
            return S.plan_itinerary(t, tr, _s(a.get("ask")), actor=actor, conv=conv)
        if action == "options":
            return S.add_options(t, tr, _s(a.get("text")), a.get("options") or None, _s(a.get("mode")), _s(a.get("leg")),
                                 _s(a.get("day")), actor=actor, conv=conv)
        if action == "partner_search":
            return S.partner_search(t, tr, _s(a.get("provider") or "amadeus"), _s(a.get("origin_code")), _s(a.get("dest_code")),
                                    _s(a.get("day")), actor=actor)
        if action == "compare":
            return S.compare(t, tr, _s(a.get("mode")))
        if action == "choose":
            return S.choose(t, tr, _s(a.get("option")), bool(a.get("on", True)), actor=actor)
        if action == "remove_option":
            return S.remove_option(t, tr, _s(a.get("option")))
        if action == "train":
            return S.train_info(_s(a.get("day")), _s(a.get("cls") or "SL"), _s(a.get("depart")), _s(a.get("quota") or "GN"))
        if action == "docs":
            if not a.get("item"):
                return {"docs": S.get_trip(t, tr)["docs"]}
            return S.doc_mark(t, tr, _s(a.get("item")), bool(a.get("have", True)), _s(a.get("file_id")))
        if action == "pack":
            return S.pack_mark(t, tr, _s(a.get("item")), bool(a.get("done", True)))
        if action == "book":
            return S.booking_request(t, tr, _s(a.get("option")), actor=actor, conv=conv)
        if action == "booked":
            return S.booking_done(t, _s(a.get("booking")), _s(a.get("pnr")), a.get("paid"), bool(a.get("failed")), actor=actor)
        if action == "quote":
            return S.quote_request(t, tr, actor=actor, conv=conv)
        if action == "cancel":
            return S.cancel_trip(t, tr)
        if action == "forget":
            return S.forget_trip(t, tr)
        if action == "settings":
            kw = {k: a[k] for k in S.SETTING_KEYS if k in a and k != "mode"}
            if a.get("mode_setting"):
                kw["mode"] = a["mode_setting"]
            return S.save_settings(t, **kw)
    except (S.TravelError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("Unknown action.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..travel import rules as R
    from ..travel import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "trips":
            return {"trips": S.trips(t, _s(a.get("status") or "open"))}
        if what == "trip":
            return S.get_trip(t, _s(a.get("trip")))
        if what == "compare":
            return S.compare(t, _s(a.get("trip")), _s(a.get("mode")))
        if what == "docs":
            v = S.get_trip(t, _s(a.get("trip")))
            return {"docs": v["docs"], "missing": v["docs_missing"], "visa": v["visa"], "passport": v["passport"]}
        if what == "train":
            return S.train_info(_s(a.get("day")), _s(a.get("cls") or "SL"), _s(a.get("depart")), _s(a.get("quota") or "GN"))
        if what == "visa":
            c = _s(a.get("country")).lower()
            return R.visa_info(R.country_of(c) or c.replace(" ", "_"))
        if what == "links":
            return {"links": R.search_links(_s(a.get("mode")), _s(a.get("origin")), _s(a.get("destination")), _s(a.get("day")))}
        if what == "settings":
            return S.settings(t)
        if what == "sources":
            return {"sources": R.SOURCES}
    except (S.TravelError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("Unknown what.")


async def _travel(ctx: Ctx, action: str = "", **a) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _travel_dekho(ctx: Ctx, what: str = "", **a) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


TRAVEL_HANDLERS = {"travel": _travel, "travel_dekho": _travel_dekho}
