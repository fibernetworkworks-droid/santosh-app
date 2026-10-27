"""Driver Sahayak tools (driver coordinator). `drivers_dekho` only reads; `drivers` does the work. Messages to drivers are only
DRAFTS here (her app tap sends them); money / advances to drivers are payroll's / hers, never Hoola's."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

DRIVERS_TOOLS = [
    {"name": "drivers", "description": (
        "Driver coordinator: duties, trip sheets, reminders. action=driver: name (new) or driver (code / name to change), phone, "
        "licence (the number or a {id:...} locker ref: it goes into the Pehchaan Locker, only the last 4 show), classes (LMV / LMV-TR / "
        "MGV / HGV / HTV / HPV / TRANS / hazardous), dl_valid_to, medical_valid_to, badge, badge_valid_to, police_on, hazardous_valid_to, "
        "vehicle (usual), payroll_name, member (Hoola Employee team member name / Hoola ID), active (false = left). action=leave: driver, "
        "start, end, kind leave|sick|off|unpaid. action=duty: driver, day (dd-mm-yyyy / aaj / kal), start, end (HH:MM), vehicle, route, "
        "break_min, kind, hazardous, duty (number to change), force + reason (ONLY when she explicitly accepts a law / rule flag). "
        "Overlaps, leave, expired licence and wrong licence class are never saved. action=duty_status: duty, status done|absent|cancelled. "
        "action=plan: day, needs [{start, end, vehicle, route, hazardous}] -> who can take each (nothing saved). action=day_plan: day "
        "(default tomorrow) -> one DRAFT message per driver + a card she taps to send. action=trip: driver, day, vehicle, text (her / the "
        "driver's words exactly) and / or start_km, end_km, start_time, end_time, fuel_l, fuel_amount, tolls, expenses [{what, amount}], "
        "from_driver (true when the text is the driver's message = draft). action=trip_photo: file_id (photo / PDF of the paper sheet), "
        "driver, day, vehicle -> OCR draft. action=trip_ok: trip, ok. action=message: driver, text (a draft). action=sheet_reminders. "
        "action=attendance_file: month YYYY-MM (Excel for payroll). action=to_payroll: month (owner). action=vehicle: number, gvw_kg, "
        "kind, kmpl. action=settings: business, morning_time, evening_time, day_h, week_h, spread_h, between_h, days_row, police_months, "
        "note. action=forget: driver (after left; DPDP)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["driver", "leave", "duty", "duty_status", "plan", "day_plan", "trip", "trip_photo", "trip_ok",
                                               "message", "sheet_reminders", "attendance_file", "to_payroll", "vehicle", "settings", "forget"]},
         "name": {"type": "string"}, "driver": {"type": "string"}, "phone": {"type": "string"}, "licence": {"type": "string"},
         "classes": {"type": "string"}, "dl_valid_to": {"type": "string"}, "medical_valid_to": {"type": "string"}, "badge": {"type": "string"},
         "badge_valid_to": {"type": "string"}, "police_on": {"type": "string"}, "hazardous_valid_to": {"type": "string"},
         "vehicle": {"type": "string"}, "payroll_name": {"type": "string"}, "member": {"type": "string"}, "active": {"type": "boolean"},
         "start": {"type": "string"}, "end": {"type": "string"}, "kind": {"type": "string"}, "note": {"type": "string"},
         "day": {"type": "string"}, "route": {"type": "string"}, "break_min": {"type": "integer"}, "hazardous": {"type": "boolean"},
         "duty": {"type": "string"}, "force": {"type": "boolean"}, "reason": {"type": "string"}, "status": {"type": "string"},
         "needs": {"type": "array", "items": {"type": "object"}}, "text": {"type": "string"}, "from_driver": {"type": "boolean"},
         "start_km": {"type": "number"}, "end_km": {"type": "number"}, "start_time": {"type": "string"}, "end_time": {"type": "string"},
         "fuel_l": {"type": "number"}, "fuel_amount": {"type": "number"}, "tolls": {"type": "number"},
         "expenses": {"type": "array", "items": {"type": "object"}}, "file_id": {"type": "string"}, "trip": {"type": "string"},
         "ok": {"type": "boolean"}, "month": {"type": "string"}, "number": {"type": "string"}, "gvw_kg": {"type": "number"},
         "kmpl": {"type": "number"}, "business": {"type": "string"}, "morning_time": {"type": "string"}, "evening_time": {"type": "string"},
         "day_h": {"type": "number"}, "week_h": {"type": "number"}, "spread_h": {"type": "number"}, "between_h": {"type": "number"},
         "days_row": {"type": "integer"}, "police_months": {"type": "integer"}},
         "required": ["action"]}},
    {"name": "drivers_dekho", "description": (
        "Read driver coordination (nothing changes). what=day (today's duties, tomorrow, missing trip sheets, documents expiring, "
        "flagged sheets, who is free) | drivers | driver (driver) | duties (day or driver) | trips (driver / vehicle) | missing | docs "
        "(within days) | attendance (month) | messages (drafts) | settings | rules (law limits + sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "drivers", "driver", "duties", "trips", "missing", "docs", "attendance", "messages",
                                             "settings", "rules"]},
         "driver": {"type": "string"}, "day": {"type": "string"}, "vehicle": {"type": "string"}, "month": {"type": "string"},
         "within": {"type": "integer"}},
         "required": ["what"]}},
]
DRIVERS_LABELS = {"drivers": "Driver ki duty / trip sheet sambhal raha hoon", "drivers_dekho": "Driver aur duty dekh raha hoon"}

_OWNER_ONLY = {"driver", "settings", "vehicle", "forget", "to_payroll", "trip_ok", "leave"}
_DKEYS = ("phone", "licence", "classes", "dl_valid_to", "medical_valid_to", "badge", "badge_valid_to", "police_on", "hazardous_valid_to",
          "payroll_name", "vehicle", "member", "active", "notes")
_TKEYS = ("start_km", "end_km", "start_time", "end_time", "fuel_l", "fuel_amount", "tolls", "route", "expenses")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..drivers import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    staff = actor.startswith("staff:")
    if staff and action != "trip":
        raise ToolError("Team member sirf apni trip sheet bhej sakte hain; baaki owner karti hain.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    try:
        if action == "driver":
            return S.save_driver(t, _s(a.get("name")), _s(a.get("driver")), **{k: a[k] for k in _DKEYS if k in a})
        if action == "leave":
            return S.add_leave(t, _s(a.get("driver")), a.get("start") or a.get("day"), a.get("end"), _s(a.get("kind")) or "leave", _s(a.get("note")))
        if action == "duty":
            return S.save_duty(t, _s(a.get("driver")), a.get("day"), a.get("start"), a.get("end"), _s(a.get("vehicle")), _s(a.get("route")),
                               int(a.get("break_min") or 0), _s(a.get("kind")) or "trip", bool(a.get("hazardous")), _s(a.get("duty")),
                               bool(a.get("force")), _s(a.get("reason")), _s(a.get("note")), "", actor)
        if action == "duty_status":
            return S.set_duty_status(t, _s(a.get("duty")), _s(a.get("status")), _s(a.get("note")))
        if action == "plan":
            return S.plan(t, a.get("day"), list(a.get("needs") or []))
        if action == "day_plan":
            return S.day_plan(t, a.get("day"), conv)
        if action == "trip":
            src = "driver" if (staff or a.get("from_driver")) else "words"
            return S.add_trip(t, _s(a.get("driver")), a.get("day"), _s(a.get("vehicle")), _s(a.get("text")), src, _s(a.get("trip")), "", actor,
                              **{k: a[k] for k in _TKEYS if k in a})
        if action == "trip_photo":
            return S.trip_photo(t, _s(a.get("file_id")), _s(a.get("driver")), a.get("day"), _s(a.get("vehicle")))
        if action == "trip_ok":
            return S.trip_ok(t, _s(a.get("trip")), a.get("ok") is not False)
        if action == "message":
            return S.message(t, _s(a.get("driver")), _s(a.get("text")))
        if action == "sheet_reminders":
            return S.sheet_reminders(t, conv)
        if action == "attendance_file":
            return S.attendance_file(t, _s(a.get("month")), conv)
        if action == "to_payroll":
            return S.to_payroll(t, _s(a.get("month")))
        if action == "vehicle":
            return S.set_vehicle(t, _s(a.get("number") or a.get("vehicle")), a.get("gvw_kg"), _s(a.get("kind")), a.get("kmpl"))
        if action == "settings":
            keys = ("business", "morning_time", "evening_time", "day_h", "week_h", "spread_h", "between_h", "days_row", "police_months", "note")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
        if action == "forget":
            return S.forget_driver(t, _s(a.get("driver")))
    except (S.DriversError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..drivers import rules as R
    from ..drivers import service as S
    t, actor = ctx.tenant_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh jaankari graahak ke liye nahi.")
    if actor.startswith("staff:"):            # a driver on the team: only their own duties
        if what != "duties":
            raise ToolError("Team member sirf apni duty dekh sakte hain.")
        mid = actor.split(":", 1)[1]
        mine = [d for d in S.drivers(t) if d["member_id"] == mid]
        if not mine:
            raise ToolError("Aap driver list mein nahi.")
        return {"duties": [{k: x[k] for k in ("number", "day", "start", "end", "vehicle", "route", "status")}
                           for x in S.duties(t, driver=mine[0]["id"], start=S.today(t))]}
    try:
        if what == "day":
            return S.day(t)
        if what == "drivers":
            return {"drivers": S.drivers(t)}
        if what == "driver":
            return S.get_driver(t, _s(a.get("driver")))
        if what == "duties":
            return {"duties": S.duties(t, a.get("day") or None, _s(a.get("driver")))}
        if what == "trips":
            return {"trips": S.trips(t, _s(a.get("driver")), a.get("day") or None, vehicle=_s(a.get("vehicle")), limit=50)}
        if what == "missing":
            return {"missing": S.missing_sheets(t)}
        if what == "docs":
            return {"docs": S.docs_due(t, int(a.get("within") or 30))}
        if what == "attendance":
            return S.attendance(t, _s(a.get("month")))
        if what == "messages":
            return {"messages": [{k: m[k] for k in ("number", "driver", "kind", "text", "status")} for m in S.messages(t)]}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"law": R.LAW, "notes": R.LAW_NOTE, "never": list(R.NEVER), "sources": R.SOURCES, "classes": R.CLASSES}
    except (S.DriversError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def drivers(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def drivers_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


DRIVERS_HANDLERS = {"drivers": drivers, "drivers_dekho": drivers_dekho}
