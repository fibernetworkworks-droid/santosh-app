"""HTTP routes of the Driver Sahayak (/api/drivers/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way a message reaches a driver through Hoola: POST /api/drivers/messages/{id}/send from her app (her tap, card hash).
No public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/drivers", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.DriversError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("business", "morning_time", "evening_time", "police_months", "fuel_tolerance", "day_h", "week_h", "spread_h", "between_h",
                "days_row", "note")
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    @r.put("/vehicles")
    async def put_vehicle(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_vehicle, tenant, str(b.get("number") or ""), b.get("gvw_kg"), str(b.get("kind") or ""), b.get("kmpl"))

    # ---- drivers
    _DKEYS = ("phone", "licence", "classes", "dl_valid_to", "medical_valid_to", "badge", "badge_valid_to", "police_on", "hazardous_valid_to",
              "payroll_name", "vehicle", "notes", "member", "no_messages", "active")

    @r.get("/drivers")
    async def list_drivers(tenant: str = Depends(current_tenant)):
        return {"drivers": await run(S.drivers, tenant)}

    @r.post("/drivers")
    async def new_driver(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_driver, tenant, str(b.get("name") or ""), "", **{k: b[k] for k in _DKEYS if k in b})

    @r.get("/drivers/{ref}")
    async def get_driver(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_driver, tenant, ref)

    @r.patch("/drivers/{ref}")
    async def patch_driver(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_driver, tenant, str(b.get("name") or ""), ref, **{k: b[k] for k in _DKEYS if k in b})

    @r.post("/drivers/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_driver, tenant, ref)

    # ---- leave
    @r.post("/leaves")
    async def add_leave(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_leave, tenant, str(b.get("driver") or ""), b.get("start"), b.get("end"), str(b.get("kind") or "leave"),
                         str(b.get("note") or ""))

    @r.delete("/leaves/{lid}")
    async def del_leave(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_leave, tenant, lid)

    # ---- duties (the app is the owner)
    @r.get("/duties")
    async def list_duties(day: str = "", driver: str = "", tenant: str = Depends(current_tenant)):
        return {"duties": await run(S.duties, tenant, day or None, driver)}

    @r.post("/duties")
    async def save_duty(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_duty, tenant, str(b.get("driver") or ""), b.get("day"), b.get("start"), b.get("end"), str(b.get("vehicle") or ""),
                         str(b.get("route") or ""), int(b.get("break_min") or 0), str(b.get("kind") or "trip"), bool(b.get("hazardous")),
                         str(b.get("duty") or ""), bool(b.get("force")), str(b.get("reason") or ""), str(b.get("note") or ""),
                         str(b.get("fleet_id") or ""), "owner")

    @r.post("/duties/{did}/status")
    async def duty_status(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_duty_status, tenant, did, str(b.get("status") or ""), str(b.get("note") or ""))

    @r.post("/plan")
    async def plan(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.plan, tenant, b.get("day"), list(b.get("needs") or []))

    @r.post("/day_plan")
    async def day_plan(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.day_plan, tenant, _b(body).get("day"))

    # ---- trip sheets
    _TKEYS = ("start_km", "end_km", "start_time", "end_time", "fuel_l", "fuel_amount", "tolls", "route", "expenses")

    @r.get("/trips")
    async def list_trips(driver: str = "", vehicle: str = "", tenant: str = Depends(current_tenant)):
        return {"trips": await run(S.trips, tenant, driver, None, None, None, 100, vehicle)}

    @r.post("/trips")
    async def add_trip(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_trip, tenant, str(b.get("driver") or ""), b.get("day"), str(b.get("vehicle") or ""), str(b.get("text") or ""),
                         "app", str(b.get("trip") or ""), "", "owner", **{k: b[k] for k in _TKEYS if k in b})

    @r.post("/trips/photo")
    async def trip_photo(file: UploadFile = File(...), driver: str = Form(...), day: str = Form(""), vehicle: str = Form(""),
                         tenant: str = Depends(current_tenant)):
        from .. import chatfiles
        data = await file.read()
        try:
            f = await asyncio.to_thread(chatfiles.store, tenant, file.filename or "trip.jpg", data, file.content_type or "")
        except Exception as e:
            raise HTTPException(400, str(e))
        return await run(S.trip_photo, tenant, f["file_id"], driver, day or None, vehicle)

    @r.post("/trips/{tid}/ok")
    async def trip_ok(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.trip_ok, tenant, tid, bool(_b(body).get("ok", True)))

    @r.get("/missing")
    async def missing(tenant: str = Depends(current_tenant)):
        return {"missing": await run(S.missing_sheets, tenant)}

    @r.post("/sheet_reminders")
    async def sheet_rem(tenant: str = Depends(current_tenant)):
        return await run(S.sheet_reminders, tenant)

    # ---- messages: her tap sends
    @r.get("/messages")
    async def list_msgs(status: str = "draft", tenant: str = Depends(current_tenant)):
        return {"messages": await run(S.messages, tenant, status)}

    @r.post("/messages")
    async def new_msg(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message, tenant, str(b.get("driver") or ""), str(b.get("text") or ""))

    @r.post("/messages/{mid}/send")
    async def send(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        try:
            return await S.send_message(tenant, mid, str(b.get("via") or "self"), str(b.get("hash") or ""), by_tap=True)
        except S.DriversError as e:
            raise HTTPException(400, str(e))

    @r.post("/messages/{mid}/cancel")
    async def cancel(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_message, tenant, mid)

    # ---- documents / attendance
    @r.get("/docs")
    async def docs(within: int = 30, tenant: str = Depends(current_tenant)):
        return {"docs": await run(S.docs_due, tenant, within)}

    @r.get("/attendance")
    async def attendance(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.attendance, tenant, month)

    @r.post("/attendance/file")
    async def attendance_file(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.attendance_file, tenant, str(_b(body).get("month") or ""))

    @r.post("/attendance/payroll")
    async def to_payroll(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.to_payroll, tenant, str(_b(body).get("month") or ""))

    return r
