"""HTTP routes of the Notary Sahayak (/api/notary/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER tap lives ONLY here (by_tap=True): POST /docs/{id}/decide {yes, hash} = the final print (files without the DRAFT mark).
All routes are key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/notary", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.NotaryError as e:
            raise HTTPException(400, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/kinds")
    async def kinds():
        return {"kinds": {k: {"label": v["label"], "fields": [{"key": a, "label": b, "required": c} for a, b, c in v["fields"]],
                              "stamp": v["stamp"], "act": v["act"]} for k, v in R.KINDS.items()},
                "party_fields": [{"key": a, "label": b, "required": c} for a, b, c in R.PARTY_FIELDS],
                "langs": R.LANGS, "acts": {k: v["label"] for k, v in R.ACTS.items()}, "doc_types": R.DOC_TYPES, "never": R.NEVER,
                "sources": R.SOURCES}

    # ---- settings + her own tables
    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kw = {k: b[k] for k in S._SET_KEYS if k in b}
        for k in ("charges", "fee_caps"):
            if isinstance(b.get(k), dict):
                kw[k] = b[k]
        return await run(S.save_settings, tenant, **kw)

    @r.post("/stamp_rates")
    async def stamp_rate(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_stamp, tenant, _s(b.get("state")), _s(b.get("key")), b.get("amount"), _s(b.get("mode")))

    @r.post("/fees")
    async def fee(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_fee, tenant, _s(b.get("act")), b.get("amount"))

    # ---- documents
    @r.get("/docs")
    async def list_docs(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        return {"docs": await run(S.docs, tenant, status, q)}

    @r.post("/docs")
    async def new_doc(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.draft, tenant, _s(b.get("kind")), _s(b.get("lang")), b.get("party") or {}, b.get("facts") or {},
                         _s(b.get("words")), _s(b.get("state")), "", "", b.get("others") or [])

    @r.post("/docs/from_rentdesk")
    async def from_rentdesk(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.from_rentdesk, tenant, _s(b.get("tenancy")), _s(b.get("lang")))

    @r.get("/docs/{ref}")
    async def get_doc(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_doc, tenant, ref)

    @r.patch("/docs/{ref}")
    async def patch_doc(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if b.get("text"):
            return await run(S.edit_text, tenant, ref, _s(b["text"]))
        return await run(S.update, tenant, ref, b.get("party") or None, b.get("facts") or None, _s(b.get("lang")), _s(b.get("state")),
                         "", b.get("others"))

    @r.post("/docs/{ref}/copy")
    async def copy(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.copy, tenant, ref, _s(_b(body).get("lang")))

    @r.post("/docs/{ref}/translate")
    async def translate(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.translate, tenant, ref, _s(_b(body).get("to")))

    @r.post("/docs/{ref}/stamp")
    async def stamp(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.stamp_ref, tenant, ref, _s(b.get("ref")), _s(b.get("mode")), _s(b.get("state")))

    @r.post("/docs/{ref}/print")
    async def print_request(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.print_request, tenant, ref)

    @r.post("/docs/{ref}/decide")
    async def decide(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide_print, tenant, ref, bool(b["yes"]), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.post("/docs/{ref}/executed")
    async def executed(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.executed, tenant, ref, _s(b.get("notary")), _s(b.get("on")))

    @r.post("/docs/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    # ---- register + receipts (her act is done; Hoola only writes it down)
    @r.get("/register")
    async def register(year: int = 0, tenant: str = Depends(current_tenant)):
        return await run(S.register, tenant, year or None)

    @r.post("/register")
    async def notarise(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.notarise, tenant, _s(b.get("doc")), _s(b.get("act")), b.get("fee"), b.get("executants") or [],
                         _s(b.get("contents")), _s(b.get("stamp_text")), _s(b.get("payer")), _s(b.get("mode") or "cash"), _s(b.get("ref")),
                         b.get("charges") or {}, _s(b.get("remarks")), int(b.get("pages") or 1))

    @r.post("/register/correct")
    async def correct(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.correct_entry, tenant, _s(b.get("serial")), _s(b.get("remarks")))

    @r.post("/register/file")
    async def register_file(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant, int(_b(body).get("year") or 0) or None)

    @r.post("/receipts")
    async def receipt(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.receipt, tenant, _s(b.get("payer")), b.get("charges") or {}, _s(b.get("mode") or "cash"), _s(b.get("ref")),
                         _s(b.get("doc")))

    @r.post("/receipts/{number:path}/void")
    async def void(number: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.void_receipt, tenant, number, _s(_b(body).get("reason")))

    # ---- apostille / attestation
    @r.get("/apostilles")
    async def list_ap(status: str = "", tenant: str = Depends(current_tenant)):
        return {"apostilles": await run(S.apostilles, tenant, status)}

    @r.post("/apostilles")
    async def new_ap(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.apostille, tenant, _s(b.get("doc_title")), _s(b.get("doc_type") or "personal"), _s(b.get("country")),
                         b.get("hague"), _s(b.get("party")), _s(b.get("phone")), _s(b.get("doc")))

    @r.post("/apostilles/{ref}")
    async def upd_ap(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.apostille_update, tenant, ref, _s(b.get("step")), bool(b.get("done", True)), b.get("hague"), _s(b.get("note")),
                         _s(b.get("status")))

    return r
