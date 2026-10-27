"""HTTP routes of the Edit Desk (/api/editdesk/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason, proof} for the quote, invoices, review link,
messages, extra charges / paid rounds, final delivery and refunds. Refunds need her fingerprint once a phone key is active:
428 -> POST /cards/{id}/challenge -> sign -> resend with `proof`. All routes key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/editdesk", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.EditError as e:
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
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/clients")
    async def list_clients(tenant: str = Depends(current_tenant)):
        return {"clients": await run(S.clients, tenant)}

    @r.post("/clients")
    async def save_client(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.client_save, tenant, _s(b.get("name")), _s(b.get("phone")), _s(b.get("email")), _s(b.get("company")),
                         _s(b.get("gstin")), _s(b.get("country")), b.get("business"), _s(b.get("notes")), _s(b.get("ref")),
                         b.get("no_messages"))

    @r.post("/clients/forget")
    async def forget(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, _s(_b(body).get("client")))

    @r.get("/projects")
    async def list_projects(status: str = "", tenant: str = Depends(current_tenant)):
        return {"projects": await run(S.projects, tenant, status)}

    @r.post("/projects")
    async def new_project(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.project_new, tenant, _s(b.get("client")), _s(b.get("title")), _s(b.get("brief")), _s(b.get("kind")),
                         b.get("platforms"), _s(b.get("due")), b.get("file_ids"), b.get("length_s"))

    @r.get("/projects/{ref}")
    async def get_project(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.project_view, tenant, ref)

    @r.patch("/projects/{ref}")
    async def patch_project(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("brief", "title", "due", "kind", "captions", "music_file_id", "logo_file_id", "client", "platforms", "length_s", "deliverable")
        return await run(S.project_update, tenant, ref, "owner", **{k: b[k] for k in keys if k in b})

    @r.post("/projects/{ref}/sync")
    async def sync(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.sync, tenant, ref)

    @r.post("/projects/{ref}/footage")
    async def footage(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.footage_add, tenant, ref, b.get("file_ids"), _s(b.get("item")), b.get("have"), _s(b.get("note")))

    @r.post("/projects/{ref}/edit")
    async def edit(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.edit_start, tenant, ref, _s(_b(body).get("deliverable")))

    @r.post("/projects/{ref}/comments")
    async def comments(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.comments_add, tenant, ref, _s(b.get("text")), _s(b.get("deliverable")), b.get("version"), _s(b.get("by")) or "client")

    @r.patch("/comments/{cid}")
    async def comment(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.comment_status, tenant, cid, _s(_b(body).get("status")))

    @r.post("/projects/{ref}/revise")
    async def revise(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.revise, tenant, ref, _s(b.get("deliverable")), bool(b.get("free")))

    @r.post("/projects/{ref}/client_ok")
    async def client_ok(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.client_ok, tenant, ref, _s(b.get("deliverable")), b.get("version"))

    @r.post("/projects/{ref}/quote")
    async def quote(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.quote_make, tenant, ref, b.get("lines"), b.get("rounds"), b.get("extra_round_fee"), b.get("advance_pct"),
                         b.get("valid_days"), _s(b.get("terms")))

    @r.post("/projects/{ref}/quote_send")
    async def quote_send(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_request, tenant, ref)

    @r.post("/projects/{ref}/quote_accept")
    async def quote_accept(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.quote_accept, tenant, ref)

    @r.post("/projects/{ref}/invoice")
    async def invoice(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invoice_request, tenant, ref, _s(b.get("kind")) or "final", b.get("amount"), _s(b.get("what")))

    @r.post("/projects/{ref}/paid")
    async def paid(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.paid, tenant, ref, b.get("amount"), b.get("tds"), _s(b.get("mode")) or "upi", _s(b.get("utr")), _s(b.get("invoice")))

    @r.post("/projects/{ref}/charge")
    async def charge(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.charge_request, tenant, ref, _s(b.get("what")), b.get("amount"))

    @r.post("/projects/{ref}/review")
    async def review(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.review_request, tenant, ref, _s(_b(body).get("text")))

    @r.post("/projects/{ref}/message")
    async def message(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.message_request, tenant, ref, _s(_b(body).get("text")))

    @r.post("/projects/{ref}/deliver")
    async def deliver(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.deliver_request, tenant, ref)

    @r.post("/projects/{ref}/cancel")
    async def cancel(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.cancel, tenant, ref, _s(b.get("reason")), b.get("refund"))

    @r.post("/projects/{ref}/refund_sent")
    async def refund_sent(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.refund_sent, tenant, ref, _s(_b(body).get("utr")))

    @r.get("/licences")
    async def list_licences(project: str = "", tenant: str = Depends(current_tenant)):
        return {"licences": await run(S.licences, tenant, project)}

    @r.post("/licences")
    async def save_licence(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.licence_add, tenant, _s(b.get("project")), _s(b.get("kind")) or "music", _s(b.get("title")), _s(b.get("source")),
                         _s(b.get("licence_type")), _s(b.get("licence_ref")), _s(b.get("proof_file_id")), _s(b.get("file_id")),
                         b.get("commercial"), _s(b.get("expires")), _s(b.get("notes")), _s(b.get("ref")))

    @r.get("/quotes/{qid}/pdf")
    async def quote_pdf(qid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.quote_pdf, tenant, qid)
        return Response(content=data, media_type="application/pdf")

    @r.get("/invoices/{iid}/pdf")
    async def invoice_pdf(iid: str, tenant: str = Depends(current_tenant)):
        data = await run(S.invoice_pdf, tenant, iid)
        return Response(content=data, media_type="application/pdf")

    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/cards/{cid}/challenge")
    async def challenge(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_challenge, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), b.get("proof"), True)

    @r.get("/report")
    async def report(days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, days)

    return r
