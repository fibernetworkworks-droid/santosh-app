"""HTTP routes of the Banquet Sahayak (/api/banquet/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for quotation / booking terms / hold ->
confirmed / discount / refund / payment request / post-event bill / message. Money cards (discount, refund) need her fingerprint
once a phone key is active: 428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`. All routes key-protected."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/banquet", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.BanquetError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

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

    # ---- venue: halls, packages, extras
    @r.get("/halls")
    async def list_halls(tenant: str = Depends(current_tenant)):
        return {"halls": await run(S.halls, tenant)}

    @r.post("/halls")
    async def save_hall(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.hall_save, tenant, _s(b.get("name")), _s(b.get("kind")), b.get("seated"), b.get("floating"), b.get("rent"),
                         b.get("rent_full"), _s(b.get("notes")), _s(b.get("id")), b.get("active"))

    @r.get("/packages")
    async def list_packages(tenant: str = Depends(current_tenant)):
        return {"packages": await run(S.packages, tenant)}

    @r.post("/packages")
    async def save_package(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.package_save, tenant, _s(b.get("name")), b.get("price"), _s(b.get("diet")), b.get("items"),
                         b.get("min_plates"), _s(b.get("id")), b.get("active"))

    @r.get("/extras")
    async def list_extras(tenant: str = Depends(current_tenant)):
        return {"extras": await run(S.extras, tenant)}

    @r.post("/extras")
    async def save_extra(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.extra_save, tenant, _s(b.get("name")), b.get("price"), _s(b.get("kind")), _s(b.get("unit")),
                         b.get("gst_pct"), _s(b.get("id")))

    # ---- availability
    @r.get("/free")
    async def free(day: str, slot: str = "", guests: int | None = None, style: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.free, tenant, day, slot, guests, style)

    @r.get("/calendar")
    async def calendar(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, month)

    @r.post("/close")
    async def close_slot(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.close_slot, tenant, _s(b.get("hall")), _s(b.get("day")), _s(b.get("slot")), _s(b.get("note")))

    @r.post("/open")
    async def open_slot(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.open_slot, tenant, _s(b.get("hall")), _s(b.get("day")), _s(b.get("slot")))

    # ---- enquiries
    @r.get("/leads")
    async def list_leads(status: str = "", tenant: str = Depends(current_tenant)):
        return {"leads": await run(S.leads, tenant, status)}

    @r.post("/leads")
    async def new_lead(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.enquiry, tenant, _s(b.get("text")), _s(b.get("name")), _s(b.get("phone")), _s(b.get("source")),
                         _s(b.get("event_type")), _s(b.get("day")), _s(b.get("slot")), b.get("guests"), _s(b.get("diet")),
                         b.get("budget"), _s(b.get("notes")))

    @r.patch("/leads/{lid}")
    async def patch_lead(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.lead_update, tenant, lid, _s(b.get("status")), _s(b.get("follow_up")), _s(b.get("lost_reason")),
                         _s(b.get("notes")))

    # ---- bookings
    @r.get("/bookings")
    async def list_bookings(status: str = "", day_from: str = "", tenant: str = Depends(current_tenant)):
        return {"bookings": await run(S.bookings, tenant, status, day_from)}

    @r.post("/bookings")
    async def new_booking(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.booking_save, tenant, "", _s(b.get("lead")), "owner", "", **{k: b[k] for k in S._BK_KEYS if k in b})

    @r.get("/bookings/{bid}")
    async def get_booking(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.booking_view, tenant, bid)

    @r.patch("/bookings/{bid}")
    async def patch_booking(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.booking_save, tenant, bid, "", "owner", "", **{k: b[k] for k in S._BK_KEYS if k in b})

    @r.post("/bookings/{bid}/hold")
    async def do_hold(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.hold, tenant, bid, _b(body).get("hours"))

    @r.post("/bookings/{bid}/release")
    async def do_release(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.release, tenant, bid)

    @r.get("/bookings/{bid}/quote")
    async def get_quote(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote, tenant, bid)

    @r.get("/bookings/{bid}/quote.pdf")
    async def quote_pdf(bid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.quote_pdf, tenant, bid, False)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{bid}_quote_draft.pdf"'})

    @r.get("/bookings/{bid}/terms.pdf")
    async def terms_pdf(bid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.contract_pdf, tenant, bid, False)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{bid}_terms_draft.pdf"'})

    @r.post("/bookings/{bid}/{what}")
    async def ask_card(bid: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Card requests (never decide): quote | contract | confirm | discount | pay | message | bill; and owner records:
        paid | count | lock | cancel | refund_sent | done | forget | beo."""
        b = _b(body)
        if what == "quote":
            return await run(S.quote_request, tenant, bid)
        if what == "contract":
            return await run(S.contract_request, tenant, bid)
        if what == "confirm":
            return await run(S.confirm_request, tenant, bid)
        if what == "discount":
            return await run(S.discount_request, tenant, bid, b.get("amount"), b.get("pct"), _s(b.get("reason")))
        if what == "pay":
            return await run(S.pay_request, tenant, bid, _s(b.get("stage")), b.get("amount"))
        if what == "message":
            return await run(S.message_request, tenant, bid, _s(b.get("text")))
        if what == "bill":
            return await run(S.bill_request, tenant, bid, b.get("actual"))
        if what == "paid":
            return await run(S.paid, tenant, bid, b.get("amount"), _s(b.get("mode")) or "upi", _s(b.get("ref")), _s(b.get("day")))
        if what == "count":
            return await run(S.set_count, tenant, bid, b.get("final"))
        if what == "lock":
            return await run(S.lock_count, tenant, bid)
        if what == "cancel":
            return await run(S.cancel, tenant, bid, _s(b.get("reason")), _s(b.get("by")) or "client")
        if what == "refund_sent":
            return await run(S.refund_sent, tenant, bid, _s(b.get("ref")))
        if what == "done":
            return await run(S.done, tenant, bid)
        if what == "forget":
            return await run(S.forget, tenant, bid)
        if what == "beo":
            return await run(S.beo, tenant, bid)
        raise HTTPException(404, "Nahi pehchana.")

    @r.get("/bookings/{bid}/receipt/{rc:path}")
    async def receipt(bid: str, rc: str, tenant: str = Depends(current_tenant)):
        data = await run(S.receipt_pdf, tenant, bid, rc)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="receipt.pdf"'})

    # ---- cards (HER tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.get("/cards/{cid}")
    async def get_card(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_view, tenant, cid)

    @r.post("/cards/{cid}/challenge")
    async def card_challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def card_decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), proof, True)

    return r
