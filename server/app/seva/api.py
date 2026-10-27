"""HTTP routes for Seva Sahayak (Profile > Seva sahayak in the app). main.py:
`app.include_router(seva_api.make_router(require_key, current_tenant))`.

The ONLY way a refund / exception is decided is `POST /api/seva/exceptions/{id}/decide` (her tap in the app); a money card
answers 428 `fingerprint_needed` until the phone signs `POST /api/seva/exceptions/{id}/challenge`."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S
    r = APIRouter(prefix="/api/seva", dependencies=[Depends(require_key)])

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except S.SevaError as e:
            msg = str(e)
            if msg in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, msg)
            raise HTTPException(400, msg)

    def _b(body: Any) -> dict:
        return body if isinstance(body, dict) else {}

    @r.get("")
    async def seva_all(tenant: str = Depends(current_tenant)):
        return await run(S.all_in_one, tenant)

    @r.get("/day")
    async def seva_day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def seva_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def seva_save_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        keys = ("kind", "sla", "ecommerce", "officer", "officer_contact", "lang", "csat_on", "auto_ack", "morning_time", "policy") + S.POLICY_KEYS
        return await run(S.save_settings, tenant, **{k: v for k, v in _b(body).items() if k in keys})

    # ---- knowledge base
    @r.get("/kb")
    async def kb(status: str = "", q: str = "", kind: str = "", tenant: str = Depends(current_tenant)):
        return {"entries": await run(S.kb_list, tenant, status, q, kind), "gaps": await run(S.gaps, tenant, 30, 10)}

    @r.post("/kb")
    async def kb_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.kb_add, tenant, b.get("question", ""), b.get("answer", ""), b.get("kind") or "faq", b.get("aliases") or [],
                         b.get("lang", ""))

    @r.post("/kb/import")
    async def kb_import(file: UploadFile | None = File(None), file_id: str = Form(""), url: str = Form(""), text: str = Form(""),
                        tenant: str = Depends(current_tenant)):
        data = await file.read() if file is not None else None
        if data is not None and len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, "File 20 MB se badi hai.")
        return await run(S.kb_import, tenant, file_id, data, (file.filename or "file") if file is not None else "", url, text)

    @r.post("/kb/import_link")
    async def kb_import_link(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.kb_import, tenant, str(b.get("file_id") or ""), None, "", str(b.get("url") or ""), str(b.get("text") or ""))

    @r.post("/kb/ask")
    async def kb_ask(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Test: what would Hoola answer a customer? (logged as channel 'test')"""
        return await run(S.answer, tenant, _b(body).get("question", ""), "test", "", _b(body).get("lang", ""))

    @r.post("/kb/approve")
    async def kb_approve(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.kb_approve, tenant, _b(body).get("ids") or [])

    @r.patch("/kb/{entry_id}")
    async def kb_edit(entry_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = {k: v for k, v in _b(body).items() if k in ("question", "answer", "aliases", "kind")}
        return await run(S.kb_edit, tenant, entry_id, **b)

    @r.delete("/kb/{entry_id}")
    async def kb_remove(entry_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.kb_remove, tenant, entry_id)

    # ---- macros
    @r.get("/macros")
    async def macros(tenant: str = Depends(current_tenant)):
        return {"macros": await run(S.macros, tenant)}

    @r.post("/macros")
    async def macro_add(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.macro_add, tenant, b.get("name", ""), b.get("text", ""), b.get("lang", ""))

    @r.post("/macros/{macro_id}/approve")
    async def macro_approve(macro_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.macro_approve, tenant, macro_id, _b(body).get("texts"))

    @r.delete("/macros/{macro_id}")
    async def macro_remove(macro_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.macro_remove, tenant, macro_id)

    # ---- tickets
    @r.get("/tickets")
    async def tickets(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"tickets": await run(S.tickets, tenant, status, q), "duplicates": await run(S.duplicates, tenant)}

    @r.post("/tickets")
    async def ticket_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.new_ticket, tenant, b.get("text", ""), b.get("channel") or "phone", "", b.get("name", ""), b.get("phone", ""),
                         b.get("category", ""), b.get("priority", ""), "owner")

    @r.get("/tickets/{ref}")
    async def ticket_get(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.ticket, tenant, ref)

    @r.post("/tickets/{ref}/{action}")
    async def ticket_act(ref: str, action: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if action == "update":
            return await run(S.update, tenant, ref, b.get("status", ""), b.get("priority", ""), b.get("public", ""), b.get("note", ""),
                             b.get("assignee"), b.get("category", ""), "owner")
        if action == "reply":
            return await run(S.reply, tenant, ref, b.get("text", ""), b.get("macro", ""))
        if action == "note":
            return await run(S.note, tenant, ref, b.get("text", ""))
        if action == "merge":
            return await run(S.merge, tenant, ref, b.get("into", ""))
        if action == "csat":
            return await run(S.csat, tenant, ref, b.get("score", 0), b.get("comment", ""))
        if action == "exception":
            return await run(S.exception_request, tenant, b.get("kind") or "refund", b.get("reason", ""), b.get("amount", 0), ref,
                             b.get("days_since"), "owner")
        raise HTTPException(404, "action nahi mila")

    # ---- exceptions (her tap only)
    @r.get("/exceptions")
    async def exceptions(status: str = "", tenant: str = Depends(current_tenant)):
        return {"exceptions": await run(S.exceptions, tenant, status)}

    @r.post("/exceptions")
    async def exception_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.exception_request, tenant, b.get("kind") or "other", b.get("reason", ""), b.get("amount", 0), b.get("ticket", ""),
                         b.get("days_since"), "owner", "", "", b.get("customer", ""))

    @r.post("/exceptions/{exc_id}/challenge")
    async def exception_challenge(exc_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.fp_challenge, tenant, exc_id)

    @r.post("/exceptions/{exc_id}/decide")
    async def exception_decide(exc_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, exc_id, bool(b.get("yes")), b.get("hash", ""), b.get("proof"), b.get("note", ""), b.get("amount"),
                         by_tap=True)

    @r.post("/exceptions/{exc_id}/sent")
    async def exception_sent(exc_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.mark_sent, tenant, exc_id, _b(body).get("ref", ""))

    @r.post("/exceptions/{exc_id}/cancel")
    async def exception_cancel(exc_id: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel_exception, tenant, exc_id)

    # ---- numbers
    @r.get("/report")
    async def report(days: int = 30, tenant: str = Depends(current_tenant)):
        return await run(S.report, tenant, days)

    @r.get("/gaps")
    async def gaps(days: int = 30, tenant: str = Depends(current_tenant)):
        return {"gaps": await run(S.gaps, tenant, days, 20)}

    return r
