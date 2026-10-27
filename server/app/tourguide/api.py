"""HTTP routes of the Tour Guide Sahayak (/api/tourguide/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Her taps live ONLY here: POST /api/tourguide/cards/{id}/decide (booking confirmation + message, any guest message, refund,
discount, spend; refund / spend need her phone's fingerprint once a phone key is set up: 428 -> POST .../challenge, sign, resend
with `proof`)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/tourguide", dependencies=[Depends(require_key)])

    def _err(e: Exception):
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.TourError, ValueError) as e:
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

    # ---- tours
    @r.get("/tours")
    async def list_tours(tenant: str = Depends(current_tenant)):
        return {"tours": await run(S.tours, tenant)}

    @r.post("/tours")
    async def add_tour(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_tour, tenant, "", **{k: b[k] for k in S._TOUR_KEYS if k in b})

    @r.patch("/tours/{tid}")
    async def patch_tour(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_tour, tenant, tid, **{k: b[k] for k in S._TOUR_KEYS if k in b})

    @r.post("/tours/{tid}/suggest")
    async def suggest(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.suggest_places, tenant, tid, str(_b(body).get("ask") or ""))

    @r.post("/tours/{tid}/script")
    async def tour_script(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.intro_script, tenant, "", tid, str(_b(body).get("language") or ""))

    # ---- bookings
    @r.get("/bookings")
    async def list_bookings(status: str = "", day: str = "", tenant: str = Depends(current_tenant)):
        return {"bookings": await run(S.bookings, tenant, status, day)}

    @r.post("/bookings")
    async def add_booking(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_booking, tenant, "", b.get("guest_list"), str(b.get("emergency_phone") or ""), "owner", "",
                         **{k: b[k] for k in S._BOOK_KEYS if k in b})

    @r.post("/bookings/enquiry")
    async def enquiry(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.enquiry, tenant, str(b.get("text") or ""), str(b.get("tour") or ""), str(b.get("lead_name") or ""),
                         str(b.get("source") or "whatsapp"))

    @r.get("/bookings/{bid}")
    async def get_booking(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.booking_view, tenant, bid)

    @r.patch("/bookings/{bid}")
    async def patch_booking(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_booking, tenant, bid, b.get("guest_list"), str(b.get("emergency_phone") or ""), "owner", "",
                         **{k: b[k] for k in S._BOOK_KEYS if k in b})

    @r.post("/bookings/{bid}/hold")
    async def hold(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.hold, tenant, bid)

    @r.post("/bookings/{bid}/confirm")
    async def confirm(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.confirm_request, tenant, bid, _b(body).get("advance"))

    @r.post("/bookings/{bid}/status")
    async def status(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_status, tenant, bid, str(b.get("status") or ""), "owner", "", str(b.get("note") or ""))

    @r.post("/bookings/{bid}/received")
    async def received(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.received, tenant, bid, b.get("amount"), str(b.get("mode") or "upi"), str(b.get("ref") or ""), str(b.get("on") or ""))

    @r.get("/bookings/{bid}/plan")
    async def plan(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.day_plan, tenant, bid, "", False)

    @r.post("/bookings/{bid}/safety")
    async def safety(bid: str, tenant: str = Depends(current_tenant)):
        try:
            return await S.weather_check(tenant, bid)
        except S.TourError as e:
            _err(e)

    @r.post("/bookings/{bid}/roll")
    async def roll(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.roll_call, tenant, bid, str(b.get("checkpoint") or ""), b.get("present"), b.get("count"))

    @r.post("/bookings/{bid}/roll_sheet")
    async def roll_sheet(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.roll_sheet, tenant, bid)

    @r.post("/bookings/{bid}/script")
    async def script(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.intro_script, tenant, bid, "", str(_b(body).get("language") or ""))

    @r.post("/bookings/{bid}/message")
    async def message(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, bid, str(b.get("kind") or "custom"), str(b.get("text") or ""))

    @r.post("/bookings/{bid}/review")
    async def review(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.review_request, tenant, bid, bool(_b(body).get("survey")))

    @r.post("/bookings/{bid}/refund")
    async def refund(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.refund_request, tenant, bid, b.get("amount"), str(b.get("reason") or ""))

    @r.post("/bookings/{bid}/discount")
    async def discount(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.discount_request, tenant, bid, b.get("amount"), b.get("pct"), str(b.get("reason") or ""))

    @r.post("/bookings/{bid}/travel")
    async def travel(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.travel_link, tenant, bid, str(_b(body).get("origin") or ""))

    @r.post("/bookings/{bid}/forget")
    async def forget(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, bid)

    # ---- cards (HER tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/cards/{cid}/challenge")
    async def challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        try:
            return await S.decide(tenant, cid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("via") or "self"),
                                  str(b.get("reason") or ""), proof, by_tap=True)
        except (S.TourError, ValueError) as e:
            _err(e)

    @r.post("/cards/{cid}/paid")
    async def paid(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.paid_out, tenant, cid, str(b.get("ref") or ""), str(b.get("mode") or "upi"))

    @r.post("/spends")
    async def spend(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_request, tenant, str(b.get("what") or ""), b.get("amount"), str(b.get("party") or ""),
                         str(b.get("booking") or ""))

    # ---- licences / ledger / register
    @r.get("/licences")
    async def list_licences(tenant: str = Depends(current_tenant)):
        return {"licences": await run(S.licences, tenant)}

    @r.post("/licences")
    async def add_licence(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_licence, tenant, str(b.get("licence") or ""), str(b.get("kind") or ""), str(b.get("ref") or ""),
                         str(b.get("holder") or ""), str(b.get("authority") or ""), str(b.get("issued") or ""),
                         str(b.get("valid_to") or ""), str(b.get("note") or ""))

    @r.delete("/licences/{lid}")
    async def del_licence(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.delete_licence, tenant, lid)

    @r.get("/ledger")
    async def get_ledger(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.ledger, tenant, month)

    @r.post("/ledger")
    async def add_ledger(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.ledger_add, tenant, str(b.get("kind") or ""), b.get("amount"), str(b.get("party") or ""),
                         str(b.get("booking") or ""), str(b.get("note") or ""), str(b.get("on") or ""))

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
