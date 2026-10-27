"""Fleet Sahayak tools (fleet manager). `fleet_dekho` only reads; `fleet` does the work. ANY spend (service, tyres, permit fee,
tax, insurance, challan, repair) is only a card here: her tap in the app decides it. Hoola never pays or buys anything."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

FLEET_TOOLS = [
    {"name": "fleet", "description": (
        "Fleet manager's coworker (trucks / tempos / pickups / buses / taxis / cars), end to end. action=settings (owner): business, "
        "home_state (MH...), diesel_rate / petrol_rate / cng_rate (HER rates per litre), toll_per_km {vehicle type: rupees}, fill_pct, "
        "low_kmpl_pct, idle_days, avg_speed, morning_time, rules. action=vehicle (owner): reg (new, e.g. 'MH 30 AB 1234') or vehicle "
        "(existing), type truck|trailer|tanker|tempo|pickup|van|bus|taxi|car|two_wheeler, make, model, fuel, bs, reg_date, capacity_t "
        "(payload tonnes), capacity_cbm, body {l,w,h metres}, axles, tank_l, owner_name, ownership own|attached|leased, national (runs "
        "on a national permit), driver, odo, status active|workshop|sold. action=doc: vehicle, kind rc|insurance|fitness|puc|"
        "national_permit|state_permit|road_tax|ais140|fastag|speed_governor|other, expires (from HER paper), issued, number, issuer, "
        "file_id, windows [days], not_needed. action=fuel: vehicle, litres, amount, odo, day, full (tank filled), station. "
        "action=fuel_import: file_id (fuel card statement CSV / Excel), vehicle (if the sheet has no vehicle column). "
        "action=service_set (owner): vehicle, item, every_km, every_months, last_km, last_on, remove. action=service_done: vehicle, "
        "items [names | 'all'], odo, day, amount, what, workshop, spend (approved card id). action=tyre: vehicle, op fit|remove, "
        "position, brand, serial, odo, life_km, amount, tyre_id, reason. action=breakdown: vehicle, what, place, hours, amount, odo. "
        "action=close: event (breakdown / entry id), amount, note. action=expense: vehicle, what, amount, day. action=challan: "
        "vehicle, number, amount, day, offence, place (what she found on eChallan). action=spend: vehicle, kind service|tyre|permit|"
        "tax|insurance|fitness|puc|challan|repair|fastag|gps|other, what, amount (from her bill / portal), vendor, link_id -> only "
        "makes a card for HER tap (never say it is approved). action=spend_done (owner): spend, amount, ref (after she paid herself). "
        "action=trip: origin, destination, stops, day, items [{name, weight_kg, cbm, count, dims}], vehicle, driver, driver_phone, km "
        "(her number; else Google Maps when the server has it), toll (her number), origin_state, dest_state, ref (LR / order no), notes. "
        "action=assign: trip, vehicle, driver, driver_phone, km, toll, items. action=trip_status: trip, status started|done|cancelled, odo. "
        "action=load_check: items, vehicle. action=register (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "vehicle", "doc", "fuel", "fuel_import", "service_set", "service_done", "tyre",
                                               "breakdown", "close", "expense", "challan", "spend", "spend_done", "trip", "assign",
                                               "trip_status", "load_check", "register"]},
         "business": {"type": "string"}, "home_state": {"type": "string"}, "diesel_rate": {"type": "number"},
         "petrol_rate": {"type": "number"}, "cng_rate": {"type": "number"}, "toll_per_km": {"type": "object"},
         "fill_pct": {"type": "number"}, "low_kmpl_pct": {"type": "number"}, "idle_days": {"type": "integer"},
         "avg_speed": {"type": "number"}, "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "reg": {"type": "string"}, "vehicle": {"type": "string"}, "type": {"type": "string"}, "make": {"type": "string"},
         "model": {"type": "string"}, "fuel": {"type": "string"}, "bs": {"type": "string"}, "reg_date": {"type": "string"},
         "capacity_t": {"type": "number"}, "capacity_cbm": {"type": "number"}, "body": {"type": "object"}, "axles": {"type": "integer"},
         "tank_l": {"type": "number"}, "owner_name": {"type": "string"}, "ownership": {"type": "string"}, "national": {"type": "boolean"},
         "driver": {"type": "string"}, "odo": {"type": "number"}, "status": {"type": "string"},
         "kind": {"type": "string"}, "expires": {"type": "string"}, "issued": {"type": "string"}, "number": {"type": "string"},
         "issuer": {"type": "string"}, "file_id": {"type": "string"}, "windows": {"type": "array", "items": {"type": "integer"}},
         "not_needed": {"type": "boolean"}, "litres": {"type": "number"}, "amount": {"type": "number"}, "day": {"type": "string"},
         "full": {"type": "boolean"}, "station": {"type": "string"}, "item": {"type": "string"}, "every_km": {"type": "number"},
         "every_months": {"type": "integer"}, "last_km": {"type": "number"}, "last_on": {"type": "string"}, "remove": {"type": "boolean"},
         "items": {"type": "array", "items": {}}, "what": {"type": "string"}, "workshop": {"type": "string"}, "spend": {"type": "string"},
         "op": {"type": "string"}, "position": {"type": "string"}, "brand": {"type": "string"}, "serial": {"type": "string"},
         "life_km": {"type": "number"}, "tyre_id": {"type": "string"}, "reason": {"type": "string"}, "place": {"type": "string"},
         "hours": {"type": "number"}, "event": {"type": "string"}, "note": {"type": "string"}, "offence": {"type": "string"},
         "vendor": {"type": "string"}, "link_id": {"type": "string"}, "ref": {"type": "string"}, "origin": {"type": "string"},
         "destination": {"type": "string"}, "stops": {"type": "array", "items": {"type": "string"}}, "driver_phone": {"type": "string"},
         "km": {"type": "number"}, "toll": {"type": "number"}, "origin_state": {"type": "string"}, "dest_state": {"type": "string"},
         "notes": {"type": "string"}, "trip": {"type": "string"}},
         "required": ["action"]}},
    {"name": "fleet_dekho", "description": (
        "Read the fleet (nothing changes). what=day (today's trips, expired / due papers, service due, tyres, diesel signals, challans, "
        "spends waiting, idle vehicles) | vehicles | vehicle (vehicle: papers, service, tyres, fuel, events) | docs (days) | fuel "
        "(vehicle, days: km/l and signals) | cost (vehicle, days: cost per km + idle days) | idle | trips (status, day) | trip (trip) | "
        "spends (status) | settings | steps (step=echallan|vahan: official steps she follows) | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "vehicles", "vehicle", "docs", "fuel", "cost", "idle", "trips", "trip", "spends",
                                             "settings", "steps", "rules"]},
         "vehicle": {"type": "string"}, "days": {"type": "integer"}, "status": {"type": "string"}, "day": {"type": "string"},
         "trip": {"type": "string"}, "step": {"type": "string"}},
         "required": ["what"]}},
]
FLEET_LABELS = {"fleet": "Fleet ka kaam kar raha hoon", "fleet_dekho": "Gaadiyan aur kaagaz dekh raha hoon"}

OWNER_ONLY = ("settings", "vehicle", "service_set", "spend_done", "register")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_VEH_KEYS = ("type", "make", "model", "fuel", "bs", "reg_date", "capacity_t", "capacity_cbm", "body", "axles", "tank_l", "owner_name",
             "ownership", "national", "driver", "odo", "status", "notes")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..fleet import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Fleet ka kaam graahak ke liye nahi.")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    v = _s(a.get("vehicle"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "vehicle":
            return S.save_vehicle(t, _s(a.get("reg")), v, **{k: a[k] for k in _VEH_KEYS if k in a})
        if action == "doc":
            return S.save_doc(t, v, _s(a.get("kind")), _s(a.get("expires")), _s(a.get("issued")), _s(a.get("number")), _s(a.get("issuer")),
                              _s(a.get("file_id")), a.get("windows"), a.get("not_needed"), _s(a.get("notes") or a.get("note")))
        if action == "fuel":
            return S.add_fuel(t, v, a.get("litres"), a.get("amount"), a.get("odo"), _s(a.get("day")), a.get("full", True) is not False,
                              _s(a.get("station")), actor=actor, conv=conv)
        if action == "fuel_import":
            if not a.get("file_id"):
                raise ToolError("file_id chahiye (fuel card ki statement).")
            return S.import_fuel(t, _s(a.get("file_id")), vehicle=v, actor=actor, conv=conv)
        if action == "service_set":
            return S.service_set(t, v, _s(a.get("item")), a.get("every_km"), a.get("every_months"), a.get("last_km"), _s(a.get("last_on")),
                                 bool(a.get("remove")))
        if action == "service_done":
            return S.service_done(t, v, a.get("items") or a.get("item"), a.get("odo"), _s(a.get("day")), a.get("amount"), _s(a.get("what")),
                                  _s(a.get("workshop")), actor, _s(a.get("spend")))
        if action == "tyre":
            return S.tyre(t, v, _s(a.get("op") or "fit"), _s(a.get("position")), _s(a.get("brand")), _s(a.get("serial")), a.get("odo"),
                          _s(a.get("day")), a.get("life_km"), a.get("amount"), _s(a.get("tyre_id")), _s(a.get("reason")), actor, _s(a.get("spend")))
        if action == "breakdown":
            return S.breakdown(t, v, _s(a.get("what")), _s(a.get("place")), _s(a.get("day")), a.get("hours"), a.get("amount"), a.get("odo"),
                               actor, conv)
        if action == "close":
            return S.event_close(t, _s(a.get("event")), a.get("amount"), _s(a.get("note")))
        if action == "expense":
            return S.expense(t, v, _s(a.get("what")), a.get("amount"), _s(a.get("day")), actor)
        if action == "challan":
            return S.challan(t, v, _s(a.get("number")), a.get("amount"), _s(a.get("day")), _s(a.get("offence")), _s(a.get("place")), actor)
        if action == "spend":
            return S.spend_request(t, v, _s(a.get("kind") or "other"), _s(a.get("what")), a.get("amount"), _s(a.get("vendor")),
                                   _s(a.get("link_id")), actor, conv)
        if action == "spend_done":
            return S.spend_done(t, _s(a.get("spend")), a.get("amount"), _s(a.get("ref")), _s(a.get("day")), actor)
        if action == "trip":
            return S.plan_trip(t, _s(a.get("origin")), _s(a.get("destination")), _s(a.get("day")), a.get("stops"), a.get("items"), v,
                               _s(a.get("driver")), _s(a.get("driver_phone")), a.get("km"), a.get("toll"), _s(a.get("origin_state")),
                               _s(a.get("dest_state")), _s(a.get("ref")), _s(a.get("notes")), actor, conv)
        if action == "assign":
            return S.assign_trip(t, _s(a.get("trip")), v, _s(a.get("driver")), _s(a.get("driver_phone")), a.get("km"), a.get("toll"),
                                 a.get("items"), conv)
        if action == "trip_status":
            return S.trip_status(t, _s(a.get("trip")), _s(a.get("status")), a.get("odo"), _s(a.get("note")), actor)
        if action == "load_check":
            return S.load_check(t, a.get("items") or [], v)
        if action == "register":
            return S.register_file(t, conv)
    except (S.FleetError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..fleet import rules as R
    from ..fleet import service as S
    t, v = ctx.tenant_id, _s(a.get("vehicle"))
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Fleet ki jaankari graahak ke liye nahi.")
    days = int(a.get("days") or 30)
    try:
        if what == "day":
            return S.day(t)
        if what == "vehicles":
            return {"vehicles": S.vehicles(t, _s(a.get("status")))}
        if what == "vehicle":
            return S.vehicle_view(t, v)
        if what == "docs":
            return {"docs": S.docs_due(t, int(a.get("days") or 45))}
        if what == "fuel":
            return S.fuel_report(t, v, days)
        if what == "cost":
            return S.cost_report(t, v, days)
        if what == "idle":
            return {"idle": S.idle(t)}
        if what == "trips":
            return {"trips": S.trips(t, _s(a.get("status")), _s(a.get("day")))}
        if what == "trip":
            return S.trip_view(t, _s(a.get("trip")))
        if what == "spends":
            return {"spends": S.spends(t, _s(a.get("status")))}
        if what == "settings":
            return S.settings(t)
        if what == "steps":
            return S.official_steps(_s(a.get("step") or "echallan"))
        if what == "rules":
            return {"never": list(R.NEVER), "docs": {k: {"label": x["label"], "rule": x["note"], "where": x["where"]} for k, x in R.DOC_KINDS.items()},
                    "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}
    except (S.FleetError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def fleet(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def fleet_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


FLEET_HANDLERS = {"fleet": fleet, "fleet_dekho": fleet_dekho}
