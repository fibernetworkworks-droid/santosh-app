"""HTTP routes of the Rentdesk Sahayak (/api/rentdesk/*). main.py: app.include_router(make_router(require_key, current_tenant)).

Her taps live ONLY here: POST /api/rentdesk/approvals/{id}/decide (deposit deductions, rent changes, notices, repair spends; money
cards need her phone's fingerprint once a phone key is set up: 428 -> POST .../challenge, sign, resend with `proof`) and
POST /api/rentdesk/messages/{id}/send (any message to a tenant)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/rentdesk", dependencies=[Depends(require_key)])

    def _err(e: Exception):
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.RentError, ValueError) as e:
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
        return await run(S.save_settings, tenant, str(b.get("pan") or ""), **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/rules")
    async def rules():
        from . import rules as R
        return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}

    # ---- units / people
    @r.get("/units")
    async def list_units(status: str = "", tenant: str = Depends(current_tenant)):
        return {"units": await run(S.units, tenant, status)}

    @r.post("/units")
    async def add_unit(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        b.pop("unit", None)
        return await run(S.save_unit, tenant, "", **{k: b[k] for k in S._UNIT_KEYS if k in b})

    @r.patch("/units/{uid}")
    async def patch_unit(uid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_unit, tenant, uid, **{k: b[k] for k in S._UNIT_KEYS if k in b})

    @r.get("/people")
    async def list_people(q: str = "", tenant: str = Depends(current_tenant)):
        return {"people": await run(S.people, tenant, q)}

    @r.post("/people")
    async def add_person(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_person, tenant, str(b.pop("person", "") or ""), str(b.pop("name", "") or ""), str(b.pop("phone", "") or ""),
                         str(b.pop("aadhaar", "") or ""), str(b.pop("pan", "") or ""), **b)

    @r.post("/people/{pid}/forget")
    async def forget(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, pid)

    # ---- tenancies
    @r.get("/tenancies")
    async def list_tenancies(status: str = "", tenant: str = Depends(current_tenant)):
        return {"tenancies": await run(S.tenancies, tenant, status)}

    @r.post("/tenancies")
    async def new_tenancy(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        unit, person = str(b.pop("unit", "") or ""), str(b.pop("person", "") or "")
        return await run(S.new_tenancy, tenant, unit, person, **{k: b[k] for k in S._TEN_KEYS if k in b})

    @r.get("/tenancies/{tid}")
    async def get_tenancy(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.tenancy_view, tenant, tid)

    @r.patch("/tenancies/{tid}")
    async def patch_tenancy(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.update_tenancy, tenant, tid, **{k: b[k] for k in S._TEN_KEYS if k in b})

    @r.post("/tenancies/{tid}/activate")
    async def activate(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.activate, tenant, tid)

    @r.post("/tenancies/{tid}/check")
    async def check(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.check_item, tenant, tid, str(b.get("item") or ""), bool(b.get("done", True)), str(b.get("ref") or ""),
                         str(b.get("on") or ""), str(b.get("office") or ""))

    @r.post("/tenancies/{tid}/agreement")
    async def agreement(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.agreement_file, tenant, tid)

    @r.get("/tenancies/{tid}/statement")
    async def statement(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.statement, tenant, tid)

    @r.get("/tenancies/{tid}/pay_link")
    async def pay_link(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.pay_link, tenant, tid)

    @r.post("/tenancies/{tid}/receive")
    async def receive(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.receive, tenant, tid, b.get("amount"), str(b.get("on") or ""), str(b.get("mode") or "upi"),
                         str(b.get("ref") or ""), str(b.get("charge") or ""))

    @r.post("/tenancies/{tid}/charge")
    async def charge(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_charge, tenant, tid, str(b.get("kind") or "other"), b.get("amount"), str(b.get("due_on") or ""),
                         str(b.get("note") or ""))

    @r.post("/tenancies/{tid}/rent_change")
    async def rent_change(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.rent_change, tenant, tid, b.get("new_rent"), str(b.get("from") or ""), str(b.get("why") or ""),
                         str(b.get("clause") or ""))

    @r.post("/tenancies/{tid}/notice")
    async def notice(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.notice_request, tenant, tid, str(b.get("kind") or "vacate"), str(b.get("vacate_on") or ""),
                         str(b.get("reason") or ""), b.get("new_rent"), str(b.get("from") or ""))

    @r.post("/tenancies/{tid}/tenant_notice")
    async def tenant_notice(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.tenant_notice, tenant, tid, str(b.get("vacate_on") or ""), str(b.get("on") or ""))

    @r.post("/tenancies/{tid}/message")
    async def message(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.draft_message, tenant, tid, str(b.get("kind") or "custom"), str(b.get("text") or ""))

    @r.post("/tenancies/{tid}/inspection")
    async def inspection(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.inspection_start, tenant, tid, str(b.get("kind") or "move_in"), str(b.get("on") or ""))

    @r.get("/tenancies/{tid}/compare")
    async def compare(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.inspection_compare, tenant, tid)

    @r.post("/tenancies/{tid}/settlement")
    async def settlement(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.settlement_start, tenant, tid)

    # ---- ledger lines
    @r.post("/charges/{cid}/waive")
    async def waive(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.waive, tenant, cid)

    @r.post("/payments/{pid}/void")
    async def void(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.void_payment, tenant, pid)

    @r.get("/payments/{pid}/receipt.pdf")
    async def receipt_pdf(pid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.receipt_pdf, tenant, pid)
        return Response(data, media_type="application/pdf")

    @r.post("/payments/{pid}/receipt")
    async def receipt_file(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.receipt_file, tenant, pid)

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
        except S.RentError as e:
            _err(e)

    @r.post("/messages/{mid}/drop")
    async def drop_message(mid: str, tenant: str = Depends(current_tenant)):
        return await run(S.drop_message, tenant, mid)

    # ---- approvals: HER tap
    @r.get("/approvals")
    async def list_approvals(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"approvals": await run(S.approvals, tenant, status)}

    @r.post("/approvals/{aid}/challenge")
    async def challenge(aid: str, tenant: str = Depends(current_tenant)):
        return await run(S.challenge, tenant, aid)

    @r.post("/approvals/{aid}/decide")
    async def decide(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        proof = b.get("proof") if isinstance(b.get("proof"), dict) else None
        return await run(S.decide, tenant, aid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), proof,
                         by_tap=True)

    # ---- repairs / vendors
    @r.get("/requests")
    async def list_requests(status: str = "", tenant: str = Depends(current_tenant)):
        return {"requests": await run(S.requests, tenant, status)}

    @r.post("/requests")
    async def new_request(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_new, tenant, str(b.get("unit") or ""), str(b.get("text") or ""))

    @r.post("/requests/{rid}/assign")
    async def assign(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_assign, tenant, rid, str(b.get("vendor") or ""), b.get("quote"), str(b.get("who_pays") or ""))

    @r.post("/requests/{rid}/done")
    async def done(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_done, tenant, rid, b.get("paid"), str(b.get("note") or ""))

    @r.get("/vendors")
    async def list_vendors(tenant: str = Depends(current_tenant)):
        return {"vendors": await run(S.vendors, tenant)}

    @r.post("/vendors")
    async def add_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_vendor, tenant, str(b.get("name") or ""), str(b.get("phone") or ""), str(b.get("trade") or "other"),
                         str(b.get("notes") or ""), str(b.get("vendor") or ""))

    # ---- inspections / photos / settlement
    @r.patch("/inspections/{iid}")
    async def inspection_update(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.inspection_update, tenant, iid, b.get("items"), b.get("meters"), b.get("keys"), str(b.get("signed_by") or ""),
                         bool(b.get("close")))

    @r.post("/photos")
    async def photo(file: UploadFile = File(...), owner_kind: str = Form("inspection"), owner_id: str = Form(...), item: str = Form(""),
                    tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await run(S.add_photo, tenant, owner_kind, owner_id, data, item)

    @r.get("/photos/{pid}")
    async def photo_get(pid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.photo_bytes, tenant, pid)
        return Response(data, media_type="image/jpeg")

    @r.post("/settlements/{sid}/line")
    async def settle_line(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.settlement_line, tenant, sid, str(b.get("what") or ""), b.get("amount"), str(b.get("reason") or ""),
                         b.get("photos"), bool(b.get("remove")))

    @r.post("/settlements/{sid}/request")
    async def settle_request(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.settlement_request, tenant, sid)

    @r.post("/settlements/{sid}/paid")
    async def settle_paid(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.refund_paid, tenant, sid, b.get("amount"), str(b.get("ref") or ""))

    @r.post("/settlements/{sid}/file")
    async def settle_file(sid: str, tenant: str = Depends(current_tenant)):
        return await run(S.settlement_file, tenant, sid)

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
