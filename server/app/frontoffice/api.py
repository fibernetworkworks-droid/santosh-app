"""HTTP routes of the Front Office Sahayak (/api/frontoffice/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Her taps live ONLY here: POST /api/frontoffice/cards/{id}/decide (discount / complimentary / cancellation charge / refund / bill
final; refunds need her phone's fingerprint once a phone key is set up: 428 -> POST .../challenge, sign, resend with `proof`) and
POST /api/frontoffice/messages/{id}/send (any message to a guest)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/frontoffice", dependencies=[Depends(require_key)])

    def _err(e: Exception):
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.FoError, ValueError) as e:
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
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/rules")
    async def rules():
        from . import rules as R
        return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}

    # ---- room types / rooms / housekeeping
    @r.get("/types")
    async def list_types(tenant: str = Depends(current_tenant)):
        return {"types": await run(S.types, tenant)}

    @r.post("/types")
    async def add_type(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_type, tenant, str(b.pop("type", "") or ""), "owner", **{k: b[k] for k in S._TYPE_KEYS if k in b})

    @r.post("/rooms")
    async def add_rooms(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_rooms, tenant, str(b.get("type") or ""), b.get("numbers"), str(b.get("floor") or ""))

    @r.get("/board")
    async def board(tenant: str = Depends(current_tenant)):
        return await run(S.board, tenant)

    @r.post("/rooms/{room}/status")
    async def room_status(room: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_room_status, tenant, room, str(b.get("status") or ""), str(b.get("reason") or ""),
                         str(b.get("until") or ""), str(b.get("from") or ""))

    @r.get("/availability")
    async def availability(arrive: str = "", depart: str = "", days: int = 7, tenant: str = Depends(current_tenant)):
        return await run(S.availability, tenant, arrive, depart, days)

    # ---- guests / bookings
    @r.get("/guests")
    async def list_guests(q: str = "", tenant: str = Depends(current_tenant)):
        return {"guests": await run(S.guests, tenant, q)}

    @r.post("/guests")
    async def save_guest(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("email", "address", "company", "notes", "nationality", "gstin", "no_messages", "arrived_india_on", "visa_type",
                "visa_expiry", "visa_issued_at")
        return await run(S.save_guest, tenant, str(b.get("guest") or ""), str(b.get("name") or ""), str(b.get("phone") or ""),
                         str(b.get("id_kind") or ""), str(b.get("id_number") or ""), str(b.get("visa_number") or ""),
                         **{k: b[k] for k in keys if k in b})

    @r.post("/guests/{gid}/forget")
    async def forget(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, gid)

    @r.get("/bookings")
    async def list_bookings(status: str = "", on: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"bookings": await run(S.bookings, tenant, status, on, q)}

    @r.post("/bookings")
    async def new_booking(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("depart", "nights", "name", "phone", "guest", "adults", "children", "child_beds", "rate", "discount", "complimentary",
                "source", "hold", "room", "meal_plan", "notes", "nationality")
        return await run(S.book, tenant, str(b.get("room_type") or ""), str(b.get("arrive") or ""), **{k: b[k] for k in keys if k in b})

    @r.get("/bookings/{bid}")
    async def get_booking(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.booking_view, tenant, bid)

    @r.post("/bookings/{bid}/amend")
    async def amend(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.amend, tenant, bid, str(b.get("arrive") or ""), str(b.get("depart") or ""), str(b.get("room_type") or ""),
                         b.get("adults"), b.get("rate"), str(b.get("notes") or ""))

    @r.post("/bookings/{bid}/confirm")
    async def confirm(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.confirm_hold, tenant, bid)

    @r.post("/bookings/{bid}/checkin")
    async def check_in(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("room", "id_kind", "id_number", "nationality", "passport", "visa_number", "visa_type", "visa_expiry",
                "arrived_india_on", "address", "coming_from", "going_to", "purpose", "companions", "force", "reason")
        return await run(S.check_in, tenant, bid, **{k: b[k] for k in keys if k in b})

    @r.post("/bookings/{bid}/move")
    async def move(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.move_room, tenant, bid, str(_b(body).get("room") or ""))

    @r.post("/bookings/{bid}/checkout")
    async def check_out(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.check_out, tenant, bid)

    @r.post("/bookings/{bid}/charge")
    async def charge(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_charge, tenant, bid, str(b.get("kind") or "other"), b.get("amount"), b.get("qty", 1),
                         str(b.get("text") or ""), str(b.get("on") or ""))

    @r.post("/charges/{cid}/void")
    async def void_charge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.void_charge, tenant, cid)

    @r.post("/bookings/{bid}/received")
    async def received(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.received, tenant, bid, b.get("amount"), str(b.get("mode") or "upi"), str(b.get("ref") or ""),
                         str(b.get("on") or ""))

    @r.get("/bookings/{bid}/pay_link")
    async def pay_link(bid: str, amount: float | None = None, what: str = "balance", tenant: str = Depends(current_tenant)):
        return await run(S.pay_link, tenant, bid, amount, what)

    @r.post("/bookings/{bid}/discount")
    async def discount(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_discount, tenant, bid, b.get("amount"), bool(b.get("complimentary")), str(b.get("reason") or ""),
                         pct=b.get("pct"))

    @r.post("/bookings/{bid}/refund")
    async def refund(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.refund_request, tenant, bid, b.get("amount"), str(b.get("reason") or ""))

    @r.post("/bookings/{bid}/cancel")
    async def cancel(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.cancel, tenant, bid, str(_b(body).get("reason") or ""))

    @r.post("/bookings/{bid}/no_show")
    async def no_show(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel, tenant, bid, "no-show", no_show=True)

    @r.post("/bookings/{bid}/bill")
    async def bill(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.bill_request, tenant, bid)

    @r.post("/bookings/{bid}/message")
    async def message(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.draft_message, tenant, bid, str(b.get("kind") or "custom"), str(b.get("text") or ""))

    @r.get("/bills/{bill_id}.pdf")
    async def bill_pdf(bill_id: str, tenant: str = Depends(current_tenant)):
        data = await run(S.bill_pdf, tenant, bill_id)
        return Response(data, media_type="application/pdf")

    @r.post("/bills/{bill_id}/file")
    async def bill_file(bill_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.bill_file, tenant, bill_id)

    # ---- OTA mails / sheets (her paste)
    @r.post("/import")
    async def import_text(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.import_ota, tenant, str(b.get("text") or ""), str(b.get("room_type") or ""))

    @r.post("/import/sheet")
    async def import_sheet(file: UploadFile = File(...), source: str = Form(""), room_type: str = Form(""),
                           tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "Sheet 5 MB se badi hai.")
        return await run(S.import_sheet, tenant, data, file.filename or "sheet.csv", source, room_type)

    # ---- cards: HER tap
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

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

    @r.post("/cards/{cid}/refund_done")
    async def refund_done(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.refund_done, tenant, cid, str(b.get("ref") or ""), str(b.get("mode") or "upi"))

    # ---- messages: HER tap sends
    @r.get("/messages")
    async def list_messages(status: str = "draft", tenant: str = Depends(current_tenant)):
        return {"messages": await run(S.messages, tenant, status)}

    @r.put("/messages/{mid}")
    async def edit_message(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.edit_message, tenant, mid, str(_b(body).get("text") or ""))

    @r.post("/messages/{mid}/send")
    async def send_message(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        try:
            return await S.send_message(tenant, mid, str(b.get("via") or "self"), str(b.get("hash") or ""), by_tap=True)
        except S.FoError as e:
            _err(e)

    @r.post("/messages/{mid}/drop")
    async def drop_message(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.drop_message, tenant, mid)

    # ---- Form C / reports
    @r.get("/formc")
    async def formc(status: str = "due", tenant: str = Depends(current_tenant)):
        return {"formc": await run(S.formc_list, tenant, status)}

    @r.get("/formc/{fid}")
    async def formc_data(fid: str, tenant: str = Depends(current_tenant)):
        return await run(S.formc_data, tenant, fid)

    @r.post("/formc/{fid}/done")
    async def formc_done(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.formc_done, tenant, fid, str(_b(body).get("ref") or ""))

    @r.get("/report")
    async def report(start: str = "", end: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, start, end)

    @r.post("/register")
    async def register(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.register_file, tenant, str(b.get("start") or ""), str(b.get("end") or ""))

    return r
