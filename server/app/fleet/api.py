"""HTTP routes of the Fleet Sahayak (/api/fleet/*). main.py: app.include_router(make_router(require_key, current_tenant)).

ANY spend is approved ONLY here: POST /api/fleet/spends/{id}/decide from her app (her tap, the card's hash, and her phone's
fingerprint once a phone key is set up: 428 -> POST /api/fleet/spends/{id}/challenge, sign, resend with `proof`)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/fleet", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.FleetError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
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
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/steps/{what}")
    async def steps(what: str):
        return S.official_steps(what)

    # ---- vehicles + papers
    @r.get("/vehicles")
    async def list_vehicles(status: str = "", tenant: str = Depends(current_tenant)):
        return {"vehicles": await run(S.vehicles, tenant, status)}

    @r.post("/vehicles")
    async def add_vehicle(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        reg = str(b.pop("reg", "") or "")
        b.pop("vehicle", None)
        return await run(S.save_vehicle, tenant, reg, **b)

    @r.get("/vehicles/{vid}")
    async def get_vehicle(vid: str, tenant: str = Depends(current_tenant)):
        return await run(S.vehicle_view, tenant, vid)

    @r.patch("/vehicles/{vid}")
    async def patch_vehicle(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        b.pop("reg", None)
        b.pop("vehicle", None)
        return await run(S.save_vehicle, tenant, "", vid, **b)

    @r.post("/vehicles/{vid}/docs")
    async def save_doc(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_doc, tenant, vid, str(b.get("kind") or ""), str(b.get("expires") or ""), str(b.get("issued") or ""),
                         str(b.get("number") or ""), str(b.get("issuer") or ""), str(b.get("file_id") or ""), b.get("windows"),
                         b.get("not_needed"), str(b.get("notes") or ""))

    @r.get("/docs")
    async def docs(days: int = 45, tenant: str = Depends(current_tenant)):
        return {"docs": await run(S.docs_due, tenant, days)}

    # ---- fuel
    @r.post("/vehicles/{vid}/fuel")
    async def add_fuel(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_fuel, tenant, vid, b.get("litres"), b.get("amount"), b.get("odo"), str(b.get("day") or ""),
                         bool(b.get("full", True)), str(b.get("station") or ""))

    @r.post("/fuel/import")
    async def fuel_import(file: UploadFile = File(...), vehicle: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, "File 10 MB se badi.")
        return await run(S.import_fuel, tenant, "", data, file.filename or "fuel.csv", vehicle)

    @r.get("/fuel")
    async def fuel(vehicle: str = "", days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.fuel_report, tenant, vehicle, days)

    # ---- service / tyres / breakdowns / expenses / challans
    @r.post("/vehicles/{vid}/service_item")
    async def service_item(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.service_set, tenant, vid, str(b.get("item") or ""), b.get("every_km"), b.get("every_months"), b.get("last_km"),
                         str(b.get("last_on") or ""), bool(b.get("remove")))

    @r.post("/vehicles/{vid}/service_done")
    async def service_done(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.service_done, tenant, vid, b.get("items"), b.get("odo"), str(b.get("day") or ""), b.get("amount"),
                         str(b.get("what") or ""), str(b.get("workshop") or ""), "owner", str(b.get("spend") or ""))

    @r.post("/vehicles/{vid}/tyre")
    async def tyre(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.tyre, tenant, vid, str(b.get("op") or "fit"), str(b.get("position") or ""), str(b.get("brand") or ""),
                         str(b.get("serial") or ""), b.get("odo"), str(b.get("day") or ""), b.get("life_km"), b.get("amount"),
                         str(b.get("tyre_id") or ""), str(b.get("reason") or ""))

    @r.post("/vehicles/{vid}/breakdown")
    async def breakdown(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.breakdown, tenant, vid, str(b.get("what") or ""), str(b.get("place") or ""), str(b.get("day") or ""),
                         b.get("hours"), b.get("amount"), b.get("odo"))

    @r.post("/vehicles/{vid}/expense")
    async def expense(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.expense, tenant, vid, str(b.get("what") or ""), b.get("amount"), str(b.get("day") or ""))

    @r.post("/vehicles/{vid}/challan")
    async def challan(vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.challan, tenant, vid, str(b.get("number") or ""), b.get("amount"), str(b.get("day") or ""),
                         str(b.get("offence") or ""), str(b.get("place") or ""))

    @r.post("/events/{eid}/close")
    async def close_event(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.event_close, tenant, eid, b.get("amount"), str(b.get("note") or ""))

    # ---- trips + loads
    @r.get("/trips")
    async def list_trips(status: str = "", day: str = "", tenant: str = Depends(current_tenant)):
        return {"trips": await run(S.trips, tenant, status, day)}

    @r.post("/trips")
    async def new_trip(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.plan_trip, tenant, str(b.get("origin") or ""), str(b.get("destination") or ""), str(b.get("day") or ""),
                         b.get("stops"), b.get("items"), str(b.get("vehicle") or ""), str(b.get("driver") or ""),
                         str(b.get("driver_phone") or ""), b.get("km"), b.get("toll"), str(b.get("origin_state") or ""),
                         str(b.get("dest_state") or ""), str(b.get("ref") or ""), str(b.get("notes") or ""))

    @r.get("/trips/{tid}")
    async def get_trip(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.trip_view, tenant, tid)

    @r.post("/trips/{tid}/assign")
    async def assign(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.assign_trip, tenant, tid, str(b.get("vehicle") or ""), str(b.get("driver") or ""), str(b.get("driver_phone") or ""),
                         b.get("km"), b.get("toll"), b.get("items"))

    @r.post("/trips/{tid}/status")
    async def trip_status(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.trip_status, tenant, tid, str(b.get("status") or ""), b.get("odo"), str(b.get("note") or ""))

    @r.post("/load_check")
    async def load_check(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.load_check, tenant, b.get("items") or [], str(b.get("vehicle") or ""))

    # ---- spends: HER tap
    @r.get("/spends")
    async def list_spends(status: str = "", tenant: str = Depends(current_tenant)):
        return {"spends": await run(S.spends, tenant, status)}

    @r.post("/spends")
    async def new_spend(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_request, tenant, str(b.get("vehicle") or ""), str(b.get("kind") or "other"), str(b.get("what") or ""),
                         b.get("amount"), str(b.get("vendor") or ""), str(b.get("link_id") or ""))

    @r.post("/spends/{sid}/challenge")
    async def spend_challenge(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.spend_challenge, tenant, sid)

    @r.post("/spends/{sid}/decide")
    async def decide(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide_spend, tenant, sid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), proof,
                         by_tap=True)

    @r.post("/spends/{sid}/done")
    async def spend_done(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_done, tenant, sid, b.get("amount"), str(b.get("ref") or ""), str(b.get("day") or ""))

    # ---- reports
    @r.get("/cost")
    async def cost(vehicle: str = "", days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.cost_report, tenant, vehicle, days)

    @r.get("/idle")
    async def idle(tenant: str = Depends(current_tenant)):
        return {"idle": await run(S.idle, tenant)}

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
