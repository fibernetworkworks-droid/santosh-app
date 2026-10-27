"""HTTP routes for Wapsi Sahayak (Profile > Wapsi sahayak in the app). All under /api/wapsi, all need the key.

The refund approval route is the ONLY way a refund gets approved: her tap sends the card hash she saw (and, once a
phone key is active, the fingerprint proof for approvekey kind "wapsi"); the agent tools can only make the card."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field


class SettingsBody(BaseModel):
    business: str | None = None
    gstin: str | None = None
    address: str | None = None
    state: str | None = None
    warehouse: dict | None = None
    courier: str | None = None
    pg: str | None = None
    auto_approve: bool | None = None
    refund_before_qc: float | None = None
    morning_time: str | None = None


class PolicyBody(BaseModel):
    text: str = ""
    policy: dict | None = None


class KeyBody(BaseModel):
    creds: dict = Field(default_factory=dict)


class ReturnBody(BaseModel):
    order_ref: str = ""
    customer: dict = Field(default_factory=dict)
    items: list | str = Field(default_factory=list)
    reason: str = ""
    reason_text: str = ""
    want: str = "refund"
    delivered_on: str = ""
    order: dict = Field(default_factory=dict)
    channel: str = "manual"
    conversation_id: str = ""


class UpdateBody(BaseModel):
    items: list | str | None = None
    customer: dict | None = None
    order: dict | None = None
    delivered_on: str | None = None
    reason: str | None = None
    want: str | None = None
    order_ref: str | None = None


class DecideBody(BaseModel):
    decision: str
    reason: str = ""
    note: str = ""


class PickupBody(BaseModel):
    parcel: dict = Field(default_factory=dict)
    awb: str = ""
    courier: str = ""


class QcBody(BaseModel):
    checklist: dict = Field(default_factory=dict)
    result: str = ""
    notes: str = ""
    deduction: float | None = None
    deduction_reason: str = ""


class RefundBody(BaseModel):
    mode: str = ""
    upi: str = ""
    deduction: float | None = None
    reason: str = ""


class RefundDecide(BaseModel):
    yes: bool
    hash: str = ""
    reason: str = ""
    proof: dict | None = None


class DoneBody(BaseModel):
    utr: str = ""
    note: str = ""


class ProofBody(BaseModel):
    proof: dict | None = None


def _fingerprint(tenant: str, refund_id: str, proof: dict | None) -> None:
    """Once her phone key is active, a refund approval needs her fingerprint signature over the card as it is now
    (approvekey kind 'wapsi'; 428 = the app asks the phone)."""
    from .. import approvekey as ak
    try:
        if ak.active_on(tenant):
            ak.verify(tenant, "wapsi", refund_id, proof)
    except ak.ApproveError as e:
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S
    r = APIRouter(prefix="/api/wapsi", dependencies=[Depends(require_key)])

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except S.WapsiError as e:
            raise HTTPException(400, str(e))

    @r.get("")
    async def wapsi_home(tenant: str = Depends(current_tenant)):
        return await run(S.home, tenant)

    @r.get("/settings")
    async def wapsi_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def wapsi_settings_put(body: SettingsBody, tenant: str = Depends(current_tenant)):
        return await run(S.save_settings, tenant, **body.model_dump(exclude_none=True))

    @r.post("/policy")
    async def wapsi_policy(body: PolicyBody, tenant: str = Depends(current_tenant)):
        return await run(S.set_policy, tenant, body.text, body.policy)

    @r.put("/keys/{provider}")
    async def wapsi_keys(provider: str, body: KeyBody, tenant: str = Depends(current_tenant)):
        return await run(S.set_keys, tenant, provider, body.creds)

    @r.delete("/keys/{kind}")
    async def wapsi_keys_off(kind: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_keys, tenant, kind)

    @r.get("/returns")
    async def wapsi_returns(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"returns": await run(S.returns, tenant, status, q)}

    @r.post("/returns")
    async def wapsi_new(body: ReturnBody, tenant: str = Depends(current_tenant)):
        d = body.model_dump()
        conv = d.pop("conversation_id", "")
        return await run(S.new_return, tenant, conv=conv, **d)

    @r.get("/returns/{ref}")
    async def wapsi_one(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.return_view, tenant, ref)

    @r.patch("/returns/{ref}")
    async def wapsi_update(ref: str, body: UpdateBody, tenant: str = Depends(current_tenant)):
        return await run(S.update_return, tenant, ref, **body.model_dump(exclude_none=True))

    @r.post("/returns/{ref}/photo")
    async def wapsi_photo(ref: str, file: UploadFile = File(...), stage: str = Form("customer"), note: str = Form(""),
                          tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await run(S.add_photo, tenant, ref, data, file.filename or "photo.jpg", stage, note)

    @r.post("/returns/{ref}/check")
    async def wapsi_check(ref: str, tenant: str = Depends(current_tenant)):
        await run(S.look, tenant, ref)
        return await run(S.recheck, tenant, ref)

    @r.post("/returns/{ref}/decide")
    async def wapsi_decide(ref: str, body: DecideBody, tenant: str = Depends(current_tenant)):
        return await run(S.decide, tenant, ref, body.decision, body.reason, body.note)

    @r.post("/returns/{ref}/pickup")
    async def wapsi_pickup(ref: str, body: PickupBody, tenant: str = Depends(current_tenant)):
        if body.awb:
            return await run(S.set_awb, tenant, ref, body.awb, body.courier)
        return await run(S.book_pickup, tenant, ref, body.parcel)

    @r.post("/returns/{ref}/track")
    async def wapsi_track(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.track, tenant, ref)

    @r.post("/returns/{ref}/received")
    async def wapsi_received(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.received, tenant, ref)

    @r.post("/returns/{ref}/qc")
    async def wapsi_qc(ref: str, body: QcBody, tenant: str = Depends(current_tenant)):
        return await run(S.qc, tenant, ref, body.checklist, body.result, body.notes, body.deduction, body.deduction_reason)

    @r.post("/returns/{ref}/refund")
    async def wapsi_refund(ref: str, body: RefundBody, tenant: str = Depends(current_tenant)):
        return await run(S.prepare_refund, tenant, ref, body.mode, body.upi, body.deduction, body.reason)

    @r.post("/returns/{ref}/exchange_done")
    async def wapsi_exchange(ref: str, body: PickupBody, tenant: str = Depends(current_tenant)):
        return await run(S.exchange_done, tenant, ref, body.awb)

    @r.post("/returns/{ref}/close")
    async def wapsi_close(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.close, tenant, ref)

    @r.post("/returns/{ref}/forget")
    async def wapsi_forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_customer, tenant, ref)

    @r.get("/returns/{ref}/message")
    async def wapsi_message(ref: str, kind: str = "status", tenant: str = Depends(current_tenant)):
        return await run(S.message, tenant, ref, kind)

    @r.get("/photos/{photo_id}")
    async def wapsi_photo_get(photo_id: str, tenant: str = Depends(current_tenant)):
        try:
            path, mime = S.photo_file(tenant, photo_id)
        except S.WapsiError as e:
            raise HTTPException(404, str(e))
        return FileResponse(path, media_type=mime, headers={"Cache-Control": "private, max-age=3600"})

    @r.get("/refunds")
    async def wapsi_refunds(status: str = "", tenant: str = Depends(current_tenant)):
        return {"refunds": await run(S.refunds, tenant, status)}

    @r.post("/refunds/{refund_id}/decide")
    async def wapsi_refund_decide(refund_id: str, body: RefundDecide, tenant: str = Depends(current_tenant)):
        """HER tap. Approving needs the card hash she saw + (with a phone key) her fingerprint. Saying no never does."""
        if body.yes:
            await asyncio.to_thread(_fingerprint, tenant, refund_id, body.proof)
        return await run(S.decide_refund, tenant, refund_id, body.yes, body.hash, body.reason)

    @r.post("/refunds/{refund_id}/done")
    async def wapsi_refund_done(refund_id: str, body: DoneBody, tenant: str = Depends(current_tenant)):
        return await run(S.refund_done, tenant, refund_id, body.utr, body.note)

    @r.post("/refunds/{refund_id}/pg_check")
    async def wapsi_pg_check(refund_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.pg_check, tenant, refund_id)

    @r.post("/refunds/{refund_id}/pg_send")
    async def wapsi_pg_send(refund_id: str, body: ProofBody, tenant: str = Depends(current_tenant)):
        """Her SECOND tap on an approved refund, only when the server allows API refunds. Fingerprint again when
        a phone key is active (approvekey 'wapsi_send' is the approved card)."""
        from .. import approvekey as ak
        if await asyncio.to_thread(ak.active_on, tenant):
            try:
                await asyncio.to_thread(ak.verify, tenant, "wapsi_send", refund_id, body.proof)
            except ak.ApproveError as e:
                raise HTTPException(428 if str(e) in ("fingerprint_needed", "fingerprint_invalid") else 400, str(e))
        return await run(S.pg_send, tenant, refund_id)

    @r.get("/refunds/{refund_id}/credit_note.pdf")
    async def wapsi_cn(refund_id: str, tenant: str = Depends(current_tenant)):
        data = await run(S.credit_note_pdf, tenant, refund_id)
        return Response(data, media_type="application/pdf")

    @r.post("/refunds/{refund_id}/credit_note")
    async def wapsi_cn_file(refund_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.credit_note_file, tenant, refund_id)

    @r.get("/customers/{phone}")
    async def wapsi_customer(phone: str, tenant: str = Depends(current_tenant)):
        return await run(S.customer_view, tenant, phone)

    @r.get("/day")
    async def wapsi_day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.post("/register")
    async def wapsi_register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    return r
