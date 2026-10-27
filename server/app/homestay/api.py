"""HTTP routes of the Homestay Sahayak (/api/homestay/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Her taps live ONLY here: POST /api/homestay/cards/{id}/send (any message to a guest; a confirmation sent makes the booking pakki) and
POST /api/homestay/cards/{id}/decide (cancel / refund / spend; money needs her phone's fingerprint once a phone key is set up:
428 -> POST .../challenge, sign, resend with `proof`).
One public route: GET /api/homestay-ical/{tenant}/{token}.ics = her calendar (no guest names) for the OTA's own 'import calendar'
page; the random token is checked."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    root = APIRouter()
    r = APIRouter(prefix="/api/homestay", dependencies=[Depends(require_key)])
    pub = APIRouter(prefix="/api/homestay-ical")

    def _err(e: Exception):
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.StayError, ValueError) as e:
            _err(e)

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

    @r.get("/rules")
    async def rules():
        from . import rules as R
        return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}

    # ---- rooms / guests / calendar
    @r.get("/rooms")
    async def list_rooms(tenant: str = Depends(current_tenant)):
        return {"rooms": await run(S.rooms, tenant)}

    @r.post("/rooms")
    async def add_room(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_room, tenant, "", **{k: b[k] for k in S._ROOM_KEYS if k in b})

    @r.patch("/rooms/{rid}")
    async def patch_room(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_room, tenant, rid, **{k: b[k] for k in S._ROOM_KEYS if k in b})

    @r.get("/guests")
    async def list_guests(q: str = "", tenant: str = Depends(current_tenant)):
        return {"guests": await run(S.guests, tenant, q)}

    @r.post("/guests")
    async def add_guest(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_guest, tenant, str(b.get("guest") or ""), str(b.get("name") or ""), str(b.get("phone") or ""),
                         str(b.get("aadhaar") or ""), str(b.get("passport") or ""), str(b.get("visa") or ""), str(b.get("id_kind") or ""),
                         str(b.get("id_number") or ""), b.get("form_c") if isinstance(b.get("form_c"), dict) else None,
                         **{k: b[k] for k in S._GUEST_KEYS if k in b})

    @r.post("/guests/{gid}/forget")
    async def forget(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, gid)

    @r.get("/availability")
    async def availability(check_in: str, check_out: str, tenant: str = Depends(current_tenant)):
        return await run(S.availability, tenant, check_in, check_out)

    @r.get("/calendar")
    async def calendar(start: str = "", days: int = 31, tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, start, days)

    # ---- bookings
    @r.get("/bookings")
    async def list_bookings(status: str = "", when: str = "", tenant: str = Depends(current_tenant)):
        return {"bookings": await run(S.bookings, tenant, status, when)}

    @r.post("/bookings")
    async def new_booking(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.new_booking, tenant, b.get("rooms") or b.get("room") or "", str(b.get("check_in") or ""),
                         str(b.get("check_out") or ""), str(b.get("guest") or ""), str(b.get("name") or ""), str(b.get("phone") or ""),
                         int(b.get("adults") or 2), int(b.get("children") or 0), b.get("addons") or [], str(b.get("source") or "direct"),
                         str(b.get("ota_ref") or ""), b.get("total"), b.get("advance"), str(b.get("notes") or ""), int(b.get("nights") or 0))

    @r.post("/blocks")
    async def add_block(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.block, tenant, b.get("rooms") or b.get("room") or "", str(b.get("start") or ""), str(b.get("end") or ""),
                         str(b.get("note") or ""))

    @r.get("/bookings/{bid}")
    async def get_booking(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.booking_view, tenant, bid)

    @r.patch("/bookings/{bid}")
    async def patch_booking(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update_booking, tenant, bid, **{k: b[k] for k in S._UPD if k in b})

    @r.post("/bookings/{bid}/{act}")
    async def booking_action(bid: str, act: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if act == "confirm":
            return await run(S.confirm, tenant, bid)
        if act == "unblock":
            return await run(S.unblock, tenant, bid)
        if act == "checkin":
            return await run(S.check_in, tenant, bid, "owner", bool(b.get("id_seen")), b.get("guests"))
        if act == "checkout":
            return await run(S.check_out, tenant, bid)
        if act == "no_show":
            return await run(S.no_show, tenant, bid)
        if act == "form_c_done":
            return await run(S.form_c_done, tenant, bid, str(b.get("ref") or ""), str(b.get("stage") or "arrival"))
        if act == "check":
            return await run(S.mark_check, tenant, bid, str(b.get("item") or ""), bool(b.get("done", True)), str(b.get("ref") or ""))
        if act == "received":
            return await run(S.received, tenant, bid, b.get("amount"), str(b.get("on") or ""), str(b.get("mode") or "upi"),
                             str(b.get("ref") or ""), str(b.get("kind") or ""))
        if act == "message":
            return await run(S.draft_message, tenant, bid, str(b.get("kind") or "custom"), str(b.get("text") or ""))
        if act == "cancel":
            return await run(S.cancel_request, tenant, bid, str(b.get("by") or "guest"), str(b.get("reason") or ""), b.get("refund"))
        if act == "refund_done":
            return await run(S.refund_done, tenant, bid, b.get("amount"), str(b.get("ref") or ""))
        raise HTTPException(404, "action")

    @r.get("/bookings/{bid}/form_c")
    async def form_c(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.form_c, tenant, bid)

    @r.get("/bookings/{bid}/pay_link")
    async def pay_link(bid: str, kind: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.pay_link, tenant, bid, kind)

    @r.post("/payments/{pid}/void")
    async def void(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.void_payment, tenant, pid)

    # ---- OTA mail / iCal file (HER data)
    @r.post("/ota_email")
    async def ota_email(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.ota_email, tenant, str(b.get("text") or ""), str(b.get("room") or ""))

    @r.post("/ical")
    async def ical(file: UploadFile = File(...), room: str = Form(...), source: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 2_000_000:
            raise HTTPException(400, "File 2 MB se badi.")
        return await run(S.ical_import, tenant, data.decode("utf-8", "replace"), room, source)

    @r.get("/ical_export")
    async def ical_export(room: str = "", tenant: str = Depends(current_tenant)):
        text = await run(S.ical_export, tenant, room)
        return Response(text, media_type="text/calendar")

    # ---- cards: HER tap
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.put("/cards/{cid}")
    async def edit_card(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.edit_message, tenant, cid, str(_b(body).get("text") or ""))

    @r.post("/cards/{cid}/send")
    async def send(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        try:
            return await S.send_message(tenant, cid, str(b.get("via") or "self"), str(b.get("hash") or ""), by_tap=True)
        except S.StayError as e:
            _err(e)

    @r.post("/cards/{cid}/challenge")
    async def challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide, tenant, cid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), proof,
                         by_tap=True)

    @r.post("/cards/{cid}/drop")
    async def drop(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.drop_card, tenant, cid)

    @r.post("/cards/{cid}/paid")
    async def spend_paid(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.spend_paid, tenant, cid, str(_b(body).get("ref") or ""))

    @r.post("/spends")
    async def spend(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_request, tenant, str(b.get("what") or ""), b.get("amount"), str(b.get("vendor") or ""),
                         str(b.get("booking") or ""))

    # ---- tasks / registration / reports
    @r.get("/tasks")
    async def list_tasks(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"tasks": await run(S.tasks, tenant, status)}

    @r.post("/tasks")
    async def add_task(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.task_add, tenant, str(b.get("what") or ""), str(b.get("room") or ""), str(b.get("day") or ""),
                         str(b.get("assigned") or ""))

    @r.post("/tasks/{tid}")
    async def task(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.task_done, tenant, tid, str(b.get("note") or ""), "owner", bool(b.get("skip")), str(b.get("assigned") or ""))

    @r.get("/registration")
    async def registration(tenant: str = Depends(current_tenant)):
        return await run(S.registration, tenant)

    @r.put("/registration")
    async def registration_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.registration_update, tenant, str(b.get("number") or ""), str(b.get("valid_to") or ""), str(b.get("item") or ""),
                         bool(b.get("done", True)), str(b.get("ref") or ""), b.get("foreign_guests"))

    @r.get("/report")
    async def report(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, month)

    @r.post("/register")
    async def register(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant, str(_b(body).get("month") or ""))

    # ---- public: her calendar for the OTA's 'import calendar' (random token checked; no guest data inside)
    @pub.get("/{tenant}/{token}.ics")
    async def public_ics(tenant: str, token: str, room: str = ""):
        if len(token) < 16:
            raise HTTPException(404, "not found")
        try:
            text = await asyncio.to_thread(S.ical_export, tenant, room, token)
        except S.StayError:
            raise HTTPException(404, "not found")
        return Response(text, media_type="text/calendar", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})

    root.include_router(r)
    root.include_router(pub)
    return root
