"""HTTP routes of the Motion designer desk (/api/motiondesk/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for the storyboard going to the client,
the final delivery / handover, invoices, a paid extra revision round and any client message. Money cards (invoice, extra_round)
need her fingerprint once a phone key is active: 428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`.
All routes key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/motiondesk", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.MotiondeskError as e:
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

    # ---- clients + brand kits
    @r.get("/clients")
    async def list_clients(tenant: str = Depends(current_tenant)):
        return {"clients": await run(S.clients, tenant)}

    @r.post("/clients")
    async def save_client(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kit = b.get("kit") if isinstance(b.get("kit"), dict) else None
        return await run(S.client_save, tenant, _s(b.get("name")), _s(b.get("client") or b.get("id")), _s(b.get("contact")),
                         _s(b.get("phone")), _s(b.get("email")), _s(b.get("gstin")), _s(b.get("state")), kit, _s(b.get("notes")))

    @r.post("/clients/{cid}/logo")
    async def client_logo(cid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 8 * 1024 * 1024:
            raise HTTPException(413, "Logo 8 MB se chhota bhejiye.")
        return await run(S.client_logo, tenant, cid, data)

    @r.post("/clients/{cid}/forget")
    async def forget_client(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_client, tenant, cid)

    # ---- licence register + templates
    @r.get("/assets")
    async def list_assets(tenant: str = Depends(current_tenant)):
        return {"assets": await run(S.assets, tenant)}

    @r.post("/assets")
    async def save_asset(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.asset_save, tenant, _s(b.get("name")), _s(b.get("kind")), _s(b.get("source")), _s(b.get("licence")),
                         _s(b.get("licence_ref")), _s(b.get("credit")), _s(b.get("valid_until")), _s(b.get("note")),
                         _s(b.get("proof_file")), _s(b.get("id")))

    @r.get("/templates")
    async def list_templates(tenant: str = Depends(current_tenant)):
        return {"templates": await run(S.templates, tenant)}

    # ---- jobs
    @r.get("/jobs")
    async def list_jobs(status: str = "", client: str = "", tenant: str = Depends(current_tenant)):
        return {"jobs": await run(S.jobs, tenant, status, client)}

    @r.post("/jobs")
    async def new_job(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.job_new, tenant, _s(b.get("client")), _s(b.get("title")), _s(b.get("brief")), _s(b.get("engine")) or "motion",
                         _s(b.get("kind")), b.get("deliverables"), _s(b.get("deadline")), b.get("quote"), _s(b.get("template")))

    @r.get("/jobs/{jid}")
    async def get_job(jid: str, tenant: str = Depends(current_tenant)):
        return await run(S.job_view, tenant, jid)

    @r.get("/jobs/{jid}/storyboard.pdf")
    async def sb_pdf(jid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.storyboard_pdf, tenant, jid)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="storyboard.pdf"'})

    @r.get("/invoices/{iid}/pdf")
    async def inv_pdf(iid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.invoice_pdf, tenant, iid)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="invoice.pdf"'})

    @r.post("/invoices/{iid}/paid")
    async def inv_paid(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.paid, tenant, iid, b.get("amount"), _s(b.get("ref")))

    @r.post("/jobs/{jid}/{what}")
    async def job_action(jid: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if what == "update":
            return await run(S.job_update, tenant, jid, "owner", **{k: b[k] for k in S._JOB_KEYS if k in b})
        if what == "storyboard":
            return await run(S.storyboard, tenant, jid, b.get("seconds"))
        if what == "frames":
            return await run(S.storyboard_edit, tenant, jid, b.get("frames"))
        if what == "storyboard_send":
            return await run(S.storyboard_request, tenant, jid)
        if what == "client_ok":
            return await run(S.client_ok, tenant, jid, _s(b.get("by")))
        if what == "render":
            return await run(S.render, tenant, jid, _s(b.get("force_reason")))
        if what == "feedback":
            return await run(S.feedback, tenant, jid, _s(b.get("text")), _s(b.get("by")))
        if what == "revise":
            return await run(S.revise, tenant, jid, b.get("data") if isinstance(b.get("data"), dict) else None, _s(b.get("free_reason")))
        if what == "extra_round":
            return await run(S.extra_round_request, tenant, jid)
        if what == "final":
            return await run(S.final_request, tenant, jid)
        if what == "invoice":
            return await run(S.invoice_request, tenant, jid, _s(b.get("bill")) or "final")
        if what == "message":
            return await run(S.message_request, tenant, jid, _s(b.get("text")))
        if what == "asset":
            return await run(S.use_asset, tenant, jid, _s(b.get("asset")))
        if what == "template":
            return await run(S.template_save, tenant, jid, _s(b.get("name")))
        if what == "cancel":
            return await run(S.cancel, tenant, jid, _s(b.get("reason")))
        raise HTTPException(404, "Nahi pehchana.")

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
