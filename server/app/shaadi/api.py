"""HTTP routes of the Shaadi Sahayak (/api/shaadi/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, proof?, reason?}. Money cards (vendor booking +
advance, vendor payment, spend) need her phone's fingerprint once a phone key is active: 428 -> POST /cards/{id}/challenge ->
sign -> resend with `proof`. The gift register (shagun) is read in full only here (her app); the chat model gets masked names.
All routes are key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

MAX_UPLOAD = 10 * 1024 * 1024


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/shaadi", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.ShaadiError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _s(v: Any) -> str:
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

    # ---- weddings
    @r.get("/weddings")
    async def list_weddings(status: str = "", tenant: str = Depends(current_tenant)):
        return {"weddings": await run(S.weddings, tenant, status)}

    @r.post("/weddings")
    async def new_wedding(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("title", "community", "bride", "groom", "client", "client_phone", "city", "state", "venue", "guests_estimate", "budget",
                "age_bride", "age_groom", "functions", "dates")
        return await run(S.wedding_new, tenant, **{k: b[k] for k in keys if k in b})

    @r.get("/weddings/{wid}")
    async def get_wedding(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.wedding_view, tenant, wid)

    @r.patch("/weddings/{wid}")
    async def patch_wedding(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.wedding_update, tenant, wid, "owner", **{k: b[k] for k in S._W_KEYS + ("budget", "age_bride", "age_groom") if k in b})

    @r.post("/weddings/{wid}/functions")
    async def set_fn(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.fn_set, tenant, wid, _s(b.get("fn")), _s(b.get("name")), _s(b.get("date")), _s(b.get("start")), _s(b.get("end")),
                         _s(b.get("venue")), _s(b.get("side")), _s(b.get("muhurat")), _s(b.get("muhurat_by")), _s(b.get("notes")),
                         bool(b.get("remove")), bool(b.get("add")))

    @r.post("/weddings/{wid}/timeline")
    async def set_timeline(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.timeline_set, tenant, wid, _s(b.get("fn")), b.get("rows"), bool(b.get("starter")))

    @r.get("/weddings/{wid}/panchang")
    async def panchang(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.panchang, tenant, wid)

    @r.get("/weddings/{wid}/days")
    async def days(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.day_plan, tenant, wid)

    @r.get("/weddings/{wid}/checklist")
    async def get_checklist(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.checklist, tenant, wid)

    @r.post("/weddings/{wid}/checklist")
    async def mark_checklist(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.checklist_mark, tenant, wid, _s(b.get("item")), b.get("done", True) is not False, _s(b.get("what")), b.get("days"))

    @r.get("/weddings/{wid}/registration")
    async def registration(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.registration, tenant, wid)

    # ---- guests
    @r.get("/weddings/{wid}/guests")
    async def list_guests(wid: str, q: str = "", side: str = "", fn: str = "", answer: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.guests, tenant, wid, q, side, fn, answer)

    @r.post("/weddings/{wid}/guests")
    async def add_guest(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("side", "phone", "adults", "kids", "group", "invited", "diet", "city", "needs_room", "arrive", "depart", "travel_mode",
                "travel_from", "notes", "guest", "no_messages")
        return await run(S.guest_add, tenant, wid, _s(b.get("name")), **{k: b[k] for k in keys if k in b})

    @r.post("/weddings/{wid}/guests/import")
    async def import_guests(wid: str, file: UploadFile = File(...), side: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "File 10 MB se badi.")
        return await run(S.guests_import, tenant, wid, "", data, file.filename or "guests.csv", side)

    @r.post("/weddings/{wid}/rsvp")
    async def set_rsvp(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rsvp, tenant, wid, _s(b.get("guest")), _s(b.get("answer")), _s(b.get("fn")), b.get("adults"), b.get("kids"))

    @r.get("/weddings/{wid}/headcount")
    async def get_headcount(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.headcount, tenant, wid)

    # ---- rooms + travel
    @r.get("/weddings/{wid}/rooms")
    async def list_rooms(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.rooms, tenant, wid)

    @r.post("/weddings/{wid}/rooms")
    async def add_rooms(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.room_add, tenant, wid, _s(b.get("place")), _s(b.get("label")), b.get("capacity"), _s(b.get("check_in")),
                         _s(b.get("check_out")), b.get("rate"), b.get("count"), _s(b.get("notes")))

    @r.post("/weddings/{wid}/rooms/assign")
    async def assign_room(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.room_assign, tenant, wid, _s(b.get("guest")), _s(b.get("room")), bool(b.get("remove")))

    @r.get("/weddings/{wid}/travel")
    async def travel(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.travel_list, tenant, wid)

    @r.post("/weddings/{wid}/travel/trip")
    async def trip(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.to_trip, tenant, wid, _s(_b(body).get("from")))

    # ---- vendors + budget
    @r.get("/weddings/{wid}/vendors")
    async def list_vendors(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.vendors, tenant, wid)

    @r.post("/weddings/{wid}/vendors")
    async def add_vendor(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("kind", "phone", "functions", "quote", "quote_note", "per_plate", "plates", "schedule", "notes", "vendor")
        return await run(S.vendor_add, tenant, wid, _s(b.get("name")), **{k: b[k] for k in keys if k in b})

    @r.post("/weddings/{wid}/vendors/{vid}/book")
    async def book(wid: str, vid: str, tenant: str = Depends(current_tenant)):
        return await run(S.book_request, tenant, wid, vid)

    @r.post("/weddings/{wid}/vendors/{vid}/pay")
    async def pay(wid: str, vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.pay_request, tenant, wid, vid, _s(_b(body).get("item")))

    @r.post("/weddings/{wid}/vendors/{vid}/paid")
    async def paid(wid: str, vid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark_paid, tenant, wid, vid, _s(b.get("item")), b.get("amount"), _s(b.get("ref")))

    @r.post("/weddings/{wid}/spend")
    async def spend(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_request, tenant, wid, _s(b.get("what")), b.get("amount"), _s(b.get("head")), _s(b.get("fn")), _s(b.get("payee")))

    @r.get("/weddings/{wid}/budget")
    async def get_budget(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.budget, tenant, wid)

    @r.post("/weddings/{wid}/budget")
    async def set_budget(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.budget_set, tenant, wid, b.get("amount"), _s(b.get("head")), _s(b.get("fn")))

    # ---- client (agency) + messages
    @r.post("/weddings/{wid}/quote")
    async def quote(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.quote_request, tenant, wid, _b(body).get("lines"))

    @r.post("/weddings/{wid}/client_pay")
    async def client_pay(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.client_pay_request, tenant, wid, int(_b(body).get("stage") or 0))

    @r.get("/weddings/{wid}/invite_text")
    async def invite_text(wid: str, kind: str = "invite", fn: str = "", lang: str = "hinglish", host: str = "",
                          tenant: str = Depends(current_tenant)):
        return await run(S.invite_text, tenant, wid, kind, fn, lang, host)

    @r.post("/weddings/{wid}/message")
    async def message(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, wid, _s(b.get("text")), _s(b.get("kind")) or "invite", _s(b.get("to")) or "guests",
                         _s(b.get("fn")), _s(b.get("side")), bool(b.get("pending")), b.get("guests"), _s(b.get("lang")) or "hinglish",
                         _s(b.get("vendor_kind")))

    @r.post("/weddings/{wid}/invite_design")
    async def invite_design(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invite_design, tenant, wid, _s(b.get("fn")), _s(b.get("words")))

    # ---- her taps
    @r.get("/cards")
    async def list_cards(wedding: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, wedding, status)}

    @r.post("/cards/{cid}/challenge")
    async def card_challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def card_decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), b.get("proof"), True)

    @r.post("/cards/{cid}/paid")
    async def card_paid(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.spend_paid, tenant, cid, _s(_b(body).get("ref")))

    @r.get("/cards/{cid}/quote.pdf")
    async def quote_pdf(cid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.quote_pdf, tenant, cid)
        return Response(data, media_type="application/pdf")

    # ---- shagun register (owner's app only)
    @r.get("/weddings/{wid}/gifts")
    async def list_gifts(wid: str, tenant: str = Depends(current_tenant)):
        return await run(S.gifts, tenant, wid, True)

    @r.post("/weddings/{wid}/gifts")
    async def add_gift(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.gift_add, tenant, wid, _s(b.get("giver")), b.get("value"), _s(b.get("kind")) or "cash", _s(b.get("what")),
                         _s(b.get("relation")), _s(b.get("side")), _s(b.get("for_whom")) or "both", _s(b.get("fn")), _s(b.get("day")),
                         _s(b.get("note")))

    @r.delete("/gifts/{gid}")
    async def del_gift(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.gift_remove, tenant, gid)

    @r.get("/weddings/{wid}/gifts/list.pdf")
    async def gift_pdf(wid: str, for_whom: str = "bride", tenant: str = Depends(current_tenant)):
        data = await run(S.gift_list_pdf, tenant, wid, for_whom)
        return Response(data, media_type="application/pdf")

    @r.post("/weddings/{wid}/gifts/list")
    async def gift_file(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.gift_list_file, tenant, wid, _s(_b(body).get("for_whom")) or "bride")

    @r.post("/weddings/{wid}/forget")
    async def forget(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, wid, bool(_b(body).get("include_gifts")))

    return r
