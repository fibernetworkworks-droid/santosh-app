"""HTTP routes of the Yatra Sahayak (/api/travel/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY ways a booking starts or a client quote is released: POST /api/travel/bookings/{id}/decide and
POST /api/travel/quotes/{id}/decide from her app (her tap). Partner keys are typed only here (PUT /api/travel/partner)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/travel", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.TravelError, ValueError) as e:
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
        return await run(S.save_settings, tenant, **{k: b[k] for k in S.SETTING_KEYS if k in b})

    @r.put("/partner")
    async def put_partner(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.partner_set, tenant, str(b.get("provider") or "amadeus"), str(b.get("key") or ""),
                         str(b.get("secret") or ""), str(b.get("env") or "test"))

    @r.delete("/partner/{provider}")
    async def del_partner(provider: str, tenant: str = Depends(current_tenant)):
        return await run(S.partner_forget, tenant, provider)

    @r.get("/train")
    async def train(day: str, cls: str = "SL", depart: str = "", quota: str = "GN"):
        return await run(S.train_info, day, cls, depart, quota)

    # ---- trips
    @r.get("/trips")
    async def list_trips(status: str = "", tenant: str = Depends(current_tenant)):
        return {"trips": await run(S.trips, tenant, status)}

    @r.post("/trips")
    async def new_trip(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("text", "title", "origin", "destination", "start_date", "end_date", "travellers", "budget", "prefs", "kind",
                "for_client", "client_name", "client_phone", "client_email", "country")
        return await run(S.new_trip, tenant, **{k: b[k] for k in keys if k in b})

    @r.get("/trips/{ref}")
    async def get_trip(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_trip, tenant, ref)

    @r.patch("/trips/{ref}")
    async def patch_trip(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("title", "origin", "destination", "kind", "client_name", "client_email", "client_phone", "start_date", "end_date",
                "country", "prefs", "notes", "budget", "status")
        return await run(S.update_trip, tenant, ref, **{k: b[k] for k in keys if k in b})

    @r.post("/trips/{ref}/cancel")
    async def cancel(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_trip, tenant, ref)

    @r.post("/trips/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_trip, tenant, ref)

    @r.post("/trips/{ref}/travellers")
    async def trav(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        op = str(b.pop("op", "add") or "add")
        keys = ("name", "age", "gender", "berth", "id_kind", "id_number", "id_ref", "passport_expiry")
        return await run(S.traveller, tenant, ref, op, **{k: b[k] for k in keys if k in b})

    @r.post("/trips/{ref}/itinerary")
    async def itinerary(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.plan_itinerary, tenant, ref, str(_b(body).get("ask") or ""))

    @r.post("/trips/{ref}/options")
    async def options(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_options, tenant, ref, str(b.get("text") or ""), b.get("options") or None, str(b.get("mode") or ""),
                         str(b.get("leg") or ""), str(b.get("day") or ""))

    @r.post("/trips/{ref}/partner_search")
    async def psearch(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.partner_search, tenant, ref, str(b.get("provider") or "amadeus"), str(b.get("origin_code") or ""),
                         str(b.get("dest_code") or ""), str(b.get("day") or ""), int(b.get("adults") or 0))

    @r.get("/trips/{ref}/compare")
    async def cmp(ref: str, mode: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.compare, tenant, ref, mode)

    @r.post("/trips/{ref}/options/{oid}/choose")
    async def choose(ref: str, oid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.choose, tenant, ref, oid, bool(_b(body).get("on", True)))

    @r.delete("/trips/{ref}/options/{oid}")
    async def del_opt(ref: str, oid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_option, tenant, ref, oid)

    @r.post("/trips/{ref}/docs")
    async def docs(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.doc_mark, tenant, ref, str(b.get("item") or ""), bool(b.get("have", True)), str(b.get("file_id") or ""),
                         str(b.get("note") or ""))

    @r.post("/trips/{ref}/packing")
    async def pack(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.pack_mark, tenant, ref, str(b.get("item") or ""), bool(b.get("done", True)))

    # ---- booking + quote cards (her tap)
    @r.post("/trips/{ref}/book")
    async def book(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.booking_request, tenant, ref, str(_b(body).get("option") or ""))

    @r.post("/bookings/{bid}/decide")
    async def decide_booking(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_booking, tenant, bid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("note") or ""),
                         by_tap=True)

    @r.post("/bookings/{bid}/done")
    async def booking_done(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.booking_done, tenant, bid, str(b.get("pnr") or ""), b.get("paid"), bool(b.get("failed")))

    @r.post("/trips/{ref}/quote")
    async def quote(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_request, tenant, ref)

    @r.post("/quotes/{qid}/decide")
    async def decide_quote(qid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_quote, tenant, qid, bool(b.get("yes")), str(b.get("hash") or ""), by_tap=True)

    @r.get("/quotes/{qid}/pdf")
    async def quote_pdf(qid: str, tenant: str = Depends(current_tenant)):
        from ..db import session
        from .models import TravelQuote

        def _get():
            with session() as s:
                q = s.get(TravelQuote, qid)
                if q is None or q.tenant_id != tenant or q.status != "approved":
                    raise S.TravelError("Yeh quote abhi approve nahi hua.")
                return S.quote_pdf(S._j(q.card, {})), q.number
        data, num = await run(_get)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="Quote-{num}.pdf"'})

    return r
