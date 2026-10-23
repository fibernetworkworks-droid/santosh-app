"""HTTP routes of the Event Sahayak (/api/eventplan/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): vendor booking (/bookings/{id}/decide, fingerprint once a phone key is active when an
advance goes: 428 -> /bookings/{id}/challenge -> sign -> resend with `proof`), quotation / invoice to the client
(/docs/{id}/decide), invites / messages (/messages/{id}/decide), other spends (/spends/{id}/decide, fingerprint likewise).
All routes are key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

MAX_UPLOAD = 10 * 1024 * 1024


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/eventplan", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.EventError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _proof(b: dict) -> dict | None:
        return b.get("proof") if isinstance(b.get("proof"), dict) else None

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/waiting")
    async def waiting(tenant: str = Depends(current_tenant)):
        return await run(S.waiting, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- vendors
    @r.get("/vendors")
    async def list_vendors(head: str = "", tenant: str = Depends(current_tenant)):
        return {"vendors": await run(S.vendors, tenant, head)}

    @r.post("/vendors")
    async def save_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.vendor_save, tenant, str(b.get("name") or ""), str(b.get("head") or ""), str(b.get("phone") or ""),
                         str(b.get("upi_id") or ""), str(b.get("gstin") or ""), str(b.get("fssai") or ""), str(b.get("notes") or ""),
                         str(b.get("id") or ""))

    # ---- events
    @r.get("/events")
    async def list_events(status: str = "", tenant: str = Depends(current_tenant)):
        return {"events": await run(S.events, tenant, status)}

    @r.post("/events")
    async def new_event(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.event_save, tenant, str(b.get("name") or ""), "", "owner", "", **{k: b[k] for k in S._EV_KEYS if k in b})

    @r.get("/events/{eid}")
    async def get_event(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.event_view, tenant, eid)

    @r.patch("/events/{eid}")
    async def patch_event(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.event_save, tenant, str(b.get("name") or ""), eid, "owner", "", **{k: b[k] for k in S._EV_KEYS if k in b})

    @r.get("/events/{eid}/budget")
    async def get_budget(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.budget, tenant, eid)

    @r.post("/events/{eid}/budget")
    async def set_budget(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.budget_set, tenant, eid, b.get("lines"), bool(b.get("replace")))

    @r.delete("/events/{eid}/budget/{line}")
    async def del_budget(eid: str, line: str, tenant: str = Depends(current_tenant)):
        return await run(S.budget_remove, tenant, eid, line)

    @r.post("/events/{eid}/vquotes")
    async def add_vquote(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.vquote_add, tenant, eid, str(b.get("vendor") or ""), b.get("amount"), str(b.get("head") or ""),
                         str(b.get("what") or ""), b.get("gst_included"), b.get("gst_pct"), str(b.get("per") or ""), b.get("qty"),
                         b.get("advance_pct"), str(b.get("cancel_terms") or ""), str(b.get("includes") or ""),
                         str(b.get("valid_till") or ""), str(b.get("file_id") or ""))

    @r.get("/events/{eid}/compare")
    async def get_compare(eid: str, head: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.compare, tenant, eid, head)

    @r.post("/vquotes/{qid}/choose")
    async def choose(qid: str, tenant: str = Depends(current_tenant)):
        return await run(S.choose_quote, tenant, qid)

    @r.post("/events/{eid}/quote")
    async def make_quote(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_make, tenant, eid)

    @r.post("/events/{eid}/invoice")
    async def make_invoice(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.invoice_make, tenant, eid)

    @r.post("/events/{eid}/client_paid")
    async def paid(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.client_paid, tenant, eid, b.get("amount"), str(b.get("ref") or ""), str(b.get("day") or ""))

    @r.post("/events/{eid}/bookings")
    async def new_booking(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.booking_request, tenant, eid, str(b.get("vendor") or ""), str(b.get("quote") or ""), b.get("amount"),
                         b.get("advance"), str(b.get("advance_due") or ""), str(b.get("arrive") or ""), str(b.get("terms") or ""),
                         str(b.get("head") or ""))

    @r.post("/events/{eid}/spends")
    async def new_spend(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.spend_request, tenant, eid, str(b.get("what") or ""), b.get("amount"), str(b.get("payee") or ""),
                         str(b.get("head") or ""))

    @r.get("/events/{eid}/guests")
    async def get_guests(eid: str, status: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.guests, tenant, eid, status)

    @r.post("/events/{eid}/guests")
    async def add_guests(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.guests_add, tenant, eid, b.get("rows"), str(b.get("text") or ""))

    @r.post("/events/{eid}/guests/import")
    async def import_guests(eid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "File 10 MB se badi.")
        return await run(S.guests_add, tenant, eid, None, "", "", data, file.filename or "guests.csv")

    @r.post("/events/{eid}/rsvp")
    async def do_rsvp(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rsvp, tenant, eid, str(b.get("guest") or ""), str(b.get("words") or ""), str(b.get("status") or ""),
                         b.get("plus"), b.get("came"))

    @r.post("/events/{eid}/messages")
    async def new_message(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, eid, str(b.get("kind") or "invite"), str(b.get("text") or ""),
                         str(b.get("group") or ""), str(b.get("to") or ""))

    @r.get("/events/{eid}/tasks")
    async def get_tasks(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.tasks, tenant, eid)

    @r.post("/events/{eid}/tasks")
    async def add_task(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.task_add, tenant, eid, str(b.get("what") or ""), str(b.get("owner") or ""), str(b.get("due") or ""))

    @r.patch("/tasks/{tid}")
    async def patch_task(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.task_update, tenant, tid, str(b.get("status") or ""), str(b.get("owner") or ""), str(b.get("due") or ""))

    @r.get("/events/{eid}/permits")
    async def get_permits(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.permits, tenant, eid)

    @r.post("/events/{eid}/permits")
    async def set_permit(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.permit_update, tenant, eid, str(b.get("key") or ""), str(b.get("status") or ""), str(b.get("ref") or ""),
                         str(b.get("note") or ""), str(b.get("label") or ""))

    @r.get("/events/{eid}/show")
    async def get_show(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.show, tenant, eid)

    @r.post("/events/{eid}/show")
    async def set_show(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.show_set, tenant, eid, str(b.get("text") or ""), b.get("cues"), bool(b.get("replace", True)))

    @r.get("/events/{eid}/show.pdf")
    async def show_pdf(eid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.show_pdf, tenant, eid)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="run_of_show.pdf"'})

    @r.post("/events/{eid}/report")
    async def do_report(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.report, tenant, eid, b.get("attended"), str(b.get("notes") or ""), b.get("issues"))

    @r.post("/events/{eid}/forget")
    async def do_forget(eid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, eid)

    # ---- client docs (her tap)
    @r.get("/docs/{did}")
    async def get_doc(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.doc_view, tenant, did)

    @r.get("/docs/{did}/pdf")
    async def doc_pdf(did: str, tenant: str = Depends(current_tenant)):
        d = await run(S.doc_view, tenant, did)
        data = await run(S.doc_pdf, tenant, did, d["status"] in ("approved", "sent", "accepted"))
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="eventplan.pdf"'})

    @r.post("/docs/{did}/request")
    async def doc_request(did: str, tenant: str = Depends(current_tenant)):
        return await run(S.doc_request, tenant, did)

    @r.post("/docs/{did}/decide")
    async def doc_decide(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_doc, tenant, did, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), True)

    @r.post("/docs/{did}/mark")
    async def doc_mark(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.doc_mark, tenant, did, str(_b(body).get("what") or ""), "owner")

    # ---- bookings (her tap + fingerprint)
    @r.get("/bookings")
    async def list_bookings(status: str = "", tenant: str = Depends(current_tenant)):
        return {"bookings": await run(S.bookings, tenant, "", status)}

    @r.post("/bookings/{bid}/challenge")
    async def booking_challenge(bid: str, tenant: str = Depends(current_tenant)):
        return await run(S.booking_challenge, tenant, bid)

    @r.post("/bookings/{bid}/decide")
    async def booking_decide(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_booking, tenant, bid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""),
                         _proof(b), True)

    @r.post("/bookings/{bid}/paid")
    async def booking_paid(bid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.booking_paid, tenant, bid, b.get("amount"), str(b.get("ref") or ""), "owner")

    # ---- spends (her tap + fingerprint)
    @r.post("/spends/{sid}/challenge")
    async def spend_challenge(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.spend_challenge, tenant, sid)

    @r.post("/spends/{sid}/decide")
    async def spend_decide(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_spend, tenant, sid, bool(b.get("yes")), str(b.get("hash") or ""), _proof(b), True)

    @r.post("/spends/{sid}/paid")
    async def spend_paid(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.spend_paid, tenant, sid, str(_b(body).get("ref") or ""), "owner")

    # ---- messages (her tap)
    @r.post("/messages/{mid}/decide")
    async def message_decide(mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_message, tenant, mid, bool(b.get("yes")), str(b.get("hash") or ""), True)

    @r.post("/messages/{mid}/sent")
    async def message_sent(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.message_sent, tenant, mid)

    return r
