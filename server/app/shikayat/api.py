"""HTTP routes for Shikayat Sahayak (Profile > Shikayat sahayak in the app).

main.py: `app.include_router(shikayat_api.make_router(require_key, current_tenant))`.
Compensation is decided ONLY here (`POST /api/shikayat/comp/{id}/decide`): her tap, the card's hash, and her phone's fingerprint
for money once a phone key is set up (428 = ask the phone: `POST /api/shikayat/comp/{id}/challenge`, sign, send `proof`).
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import service as S


def _call(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except S.ShikayatError as e:
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)


class CaseIn(BaseModel):
    text: str
    customer: str = ""
    phone: str = ""
    channel: str = "chat"
    product: str = ""
    order_ref: str = ""
    amount: float | None = None
    sector: str = ""
    severity: str = ""
    owner: str = ""
    received: str = ""
    file_ids: list[str] = Field(default_factory=list)
    conversation_id: str = ""


class Act(BaseModel):
    stage: str = ""
    owner: str | None = None
    note: str = ""
    severity: str = ""
    causes: list[str] | None = None
    due: str = ""
    external_ref: str = ""
    product: str = ""
    resolution: str = ""
    fix_proof: str = ""
    how: str = ""
    kind: str = "close"
    text: str = ""
    polish: bool = True
    fixed: bool = True
    satisfaction: int | None = None
    feedback: str = ""
    force: bool = False
    reason: str = ""
    to: str = ""
    ref: str = ""
    file_id: str = ""
    conversation_id: str = ""


class CompIn(BaseModel):
    kind: str
    amount: float | None = None
    item: str = ""
    reason: str = ""
    conversation_id: str = ""


class Decide(BaseModel):
    yes: bool
    hash: str = ""
    note: str = ""
    proof: dict[str, Any] | None = None


class Given(BaseModel):
    how: str = ""
    ref: str = ""


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()
    dep = [Depends(require_key)]

    @r.get("/api/shikayat", dependencies=dep)
    def sk_home(tenant: str = Depends(current_tenant)):
        return S.home(tenant)

    @r.get("/api/shikayat/settings", dependencies=dep)
    def sk_settings(tenant: str = Depends(current_tenant)):
        return S.settings(tenant)

    @r.put("/api/shikayat/settings", dependencies=dep)
    def sk_settings_put(body: dict, tenant: str = Depends(current_tenant)):
        return _call(S.save_settings, tenant, **{k: v for k, v in (body or {}).items() if isinstance(k, str)})

    @r.get("/api/shikayat/cases", dependencies=dep)
    def sk_cases(stage: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"cases": S.cases(tenant, stage, q)}

    @r.post("/api/shikayat/cases", dependencies=dep)
    def sk_new(body: CaseIn, tenant: str = Depends(current_tenant)):
        return _call(S.log_complaint, tenant, body.text, body.customer, body.phone, body.channel, body.product, body.order_ref,
                     body.amount, body.sector, body.severity, body.owner, body.file_ids, received=body.received or None,
                     conv=body.conversation_id)

    @r.get("/api/shikayat/cases/{case_id}", dependencies=dep)
    def sk_case(case_id: str, tenant: str = Depends(current_tenant)):
        return _call(S.case, tenant, case_id)

    @r.post("/api/shikayat/cases/{case_id}/proof", dependencies=dep)
    async def sk_proof(case_id: str, file: UploadFile = File(...), stage: str = Form("complaint"), note: str = Form(""),
                       tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await asyncio.to_thread(_call, S.add_proof, tenant, case_id, data, file.filename or "proof", stage, note)

    @r.post("/api/shikayat/cases/{case_id}/comp", dependencies=dep)
    def sk_comp(case_id: str, body: CompIn, tenant: str = Depends(current_tenant)):
        return _call(S.comp_request, tenant, case_id, body.kind, body.amount, body.item, body.reason, body.conversation_id)

    @r.post("/api/shikayat/cases/{case_id}/send", dependencies=dep)
    async def sk_send(case_id: str, body: Act, tenant: str = Depends(current_tenant)):
        """Her tap on 'Business WhatsApp se bhejo' (24 h window only)."""
        try:
            return await S.send_business(tenant, case_id, body.text, body.kind)
        except S.ShikayatError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/shikayat/cases/{case_id}/{action}", dependencies=dep)
    def sk_act(case_id: str, action: str, body: Act, tenant: str = Depends(current_tenant)):
        b = body
        acts = {
            "ack": lambda: S.ack(tenant, case_id, b.how),
            "update": lambda: S.update(tenant, case_id, b.stage, b.owner, b.note, b.severity, b.causes, b.due, b.external_ref, b.product),
            "note": lambda: S.note(tenant, case_id, b.note),
            "resolve": lambda: S.resolve(tenant, case_id, b.resolution, b.fix_proof, conv=b.conversation_id),
            "message": lambda: S.message(tenant, case_id, b.kind, b.polish, b.conversation_id),
            "told": lambda: S.mark_told(tenant, case_id, b.how or "whatsapp", b.kind),
            "confirm": lambda: S.confirm(tenant, case_id, b.fixed, b.satisfaction, b.feedback),
            "close": lambda: S.close(tenant, case_id, b.force, b.reason, conv=b.conversation_id),
            "reopen": lambda: S.reopen(tenant, case_id, b.reason or b.note),
            "escalate": lambda: S.escalate(tenant, case_id, b.to, b.ref),
            "attach": lambda: S.attach_file(tenant, case_id, b.file_id, b.stage or "complaint", b.note),
            "ticket_sync": lambda: S.ticket_sync(tenant, case_id),
        }
        if action not in acts:
            raise HTTPException(404, "action")
        return _call(acts[action])

    @r.get("/api/shikayat/proof/{proof_id}", dependencies=dep)
    def sk_proof_get(proof_id: str, tenant: str = Depends(current_tenant)):
        path, mime = _call(S.proof_file, tenant, proof_id)
        return FileResponse(path, media_type=mime)

    @r.post("/api/shikayat/comp/{comp_id}/challenge", dependencies=dep)
    def sk_comp_challenge(comp_id: str, tenant: str = Depends(current_tenant)):
        return _call(S.comp_challenge, tenant, comp_id)

    @r.post("/api/shikayat/comp/{comp_id}/decide", dependencies=dep)
    def sk_comp_decide(comp_id: str, body: Decide, tenant: str = Depends(current_tenant)):
        return _call(S.decide_comp, tenant, comp_id, body.yes, body.hash, body.proof, body.note, by_tap=True)

    @r.post("/api/shikayat/comp/{comp_id}/given", dependencies=dep)
    def sk_comp_given(comp_id: str, body: Given, tenant: str = Depends(current_tenant)):
        return _call(S.comp_given, tenant, comp_id, body.how, body.ref)

    @r.get("/api/shikayat/summary", dependencies=dep)
    def sk_summary(month: str = "", tenant: str = Depends(current_tenant)):
        return S.summary(tenant, month)

    @r.post("/api/shikayat/register", dependencies=dep)
    def sk_register(body: dict | None = None, tenant: str = Depends(current_tenant)):
        b = body or {}
        return _call(S.register_file, tenant, str(b.get("month") or ""), str(b.get("conversation_id") or ""))

    @r.post("/api/shikayat/import_tickets", dependencies=dep)
    def sk_import(tenant: str = Depends(current_tenant)):
        return S.import_tickets(tenant)

    @r.delete("/api/shikayat/customer", dependencies=dep)
    def sk_forget(phone: str, tenant: str = Depends(current_tenant)):
        return _call(S.forget_customer, tenant, phone)

    return r
