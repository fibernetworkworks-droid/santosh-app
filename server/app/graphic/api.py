"""HTTP routes of the Graphic Sahayak (/api/graphic/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for the quotation, proofs, an extra
revision round, the handover pack, the print order, invoices, discounts and messages. A discount needs her fingerprint once a
phone key is active: 428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`. All routes are key-protected
(files too: the app sends its auth header)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

MAX_UPLOAD = 80 * 1024 * 1024


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/graphic", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.GraphicError as e:
            code = str(e)
            if code in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, code)
            raise HTTPException(400, code)
        except ValueError as e:
            raise HTTPException(400, str(e))

    async def _read(file: UploadFile) -> bytes:
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "File 80 MB se badi.")
        return data

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
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- clients (their brand kits)
    @r.get("/clients")
    async def list_clients(tenant: str = Depends(current_tenant)):
        return {"clients": await run(S.clients, tenant)}

    @r.post("/clients")
    async def new_client(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.client_save, tenant, "", "owner", **_b(body))

    @r.get("/clients/{ref}")
    async def get_client(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.client_view, tenant, ref)

    @r.patch("/clients/{ref}")
    async def patch_client(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.client_save, tenant, ref, "owner", **_b(body))

    @r.post("/clients/{ref}/logo")
    async def client_logo(ref: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await _read(file)
        return await run(S.client_logo, tenant, ref, data, "", file.filename or "logo.png")

    @r.post("/clients/{ref}/forget")
    async def forget_client(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_client, tenant, ref)

    # ---- printers
    @r.get("/vendors")
    async def list_vendors(tenant: str = Depends(current_tenant)):
        return {"vendors": await run(S.vendors, tenant)}

    @r.post("/vendors")
    async def save_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.vendor_save, tenant, _s(b.get("name")), _s(b.get("phone")), _s(b.get("email")), _s(b.get("does")),
                         b.get("spec") if isinstance(b.get("spec"), dict) else None, _s(b.get("notes")), _s(b.get("id")))

    # ---- jobs
    @r.get("/jobs")
    async def list_jobs(status: str = "", client: str = "", tenant: str = Depends(current_tenant)):
        return {"jobs": await run(S.jobs, tenant, status, client)}

    @r.post("/jobs")
    async def new_job(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.job_save, tenant, "", _s(b.get("client")), "owner", "", **{k: b[k] for k in S._JOB_KEYS if k in b})

    @r.get("/jobs/{ref}")
    async def get_job(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.job_view, tenant, ref)

    @r.patch("/jobs/{ref}")
    async def patch_job(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.job_save, tenant, ref, "", "owner", "", **{k: b[k] for k in S._JOB_KEYS if k in b})

    @r.get("/jobs/{ref}/quote.pdf")
    async def quote_pdf(ref: str, tenant: str = Depends(current_tenant)):
        data = await run(S.quote_pdf, tenant, ref, False)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{ref}_quote_draft.pdf"'})

    @r.get("/jobs/{ref}/tm_help")
    async def tm_help(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.tm_help, tenant, ref)

    @r.post("/jobs/{ref}/upload")
    async def upload(ref: str, file: UploadFile = File(...), note: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await _read(file)
        return await run(S.proof_upload, tenant, ref, data, file.filename or "design", "", note)

    @r.post("/jobs/{ref}/{what}")
    async def job_action(ref: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Work: render | feedback | client_ok | waive | asset | asset_remove | tm | assignment | accepted | paid | cancel | done.
        Card requests (never decide): quote | proof | extra | handover | vendor | invoice | discount | message."""
        b = _b(body)
        v = b.get("version")
        ver = int(v) if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()) else None
        if what == "render":
            return await run(S.proof_render, tenant, ref, b.get("words") if isinstance(b.get("words"), dict) else None,
                             _s(b.get("layout")), b.get("sizes"), _s(b.get("instruction")))
        if what == "feedback":
            return await run(S.feedback, tenant, ref, _s(b.get("text")), ver)
        if what == "client_ok":
            return await run(S.client_approved, tenant, ref, ver, _s(b.get("evidence")))
        if what == "waive":
            return await run(S.waive_round, tenant, ref, _s(b.get("reason")))
        if what == "asset":
            return await run(S.asset_add, tenant, ref, _s(b.get("name")), _s(b.get("kind")) or "font", _s(b.get("source")),
                             _s(b.get("licence")), _s(b.get("licence_ref")))
        if what == "asset_remove":
            return await run(S.asset_remove, tenant, ref, _s(b.get("name")))
        if what == "tm":
            return await run(S.tm_record, tenant, ref, _s(b.get("result")), b.get("classes") or [], _s(b.get("notes")))
        if what == "assignment":
            return await run(S.set_assignment, tenant, ref, _s(b.get("rights")), b.get("years"), _s(b.get("territory")))
        if what == "accepted":
            return await run(S.accepted, tenant, ref, _s(b.get("evidence")))
        if what == "paid":
            return await run(S.paid, tenant, ref, b.get("amount"), _s(b.get("mode")) or "upi", _s(b.get("ref")), _s(b.get("day")))
        if what == "cancel":
            return await run(S.cancel, tenant, ref, _s(b.get("reason")))
        if what == "done":
            return await run(S.done, tenant, ref)
        if what == "quote":
            return await run(S.quote_request, tenant, ref)
        if what == "proof":
            return await run(S.proof_send, tenant, ref, ver)
        if what == "extra":
            return await run(S.extra_request, tenant, ref)
        if what == "handover":
            return await run(S.handover_request, tenant, ref, bool(b.get("force")))
        if what == "vendor":
            return await run(S.vendor_request, tenant, ref, _s(b.get("vendor")))
        if what == "invoice":
            return await run(S.invoice_request, tenant, ref, _s(b.get("what")) or "final")
        if what == "discount":
            return await run(S.discount_request, tenant, ref, b.get("amount"), b.get("pct"), _s(b.get("reason")))
        if what == "message":
            return await run(S.message_request, tenant, ref, _s(b.get("text")))
        raise HTTPException(404, "Nahi pehchana.")

    @r.get("/files/{job}/{name}")
    async def get_file(job: str, name: str, tenant: str = Depends(current_tenant)):
        p, mime = await run(S.file_path, tenant, job, name)
        return FileResponse(str(p), media_type=mime, filename=name)

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
