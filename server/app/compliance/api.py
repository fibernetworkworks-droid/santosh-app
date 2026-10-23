"""HTTP routes of the Compliance Sahayak (/api/compliance/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /filings/{id}/decide ('portal par file karo'; she still logs in / pays / submits herself)
and POST /certs/{id}/decide (monthly compliance certificate sign-off). The app is the owner, so its done / n/a calls count as hers."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/compliance", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.CompError as e:
            raise HTTPException(400, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        def go():
            return {"settings": S.settings(tenant), "day": S.day(tenant), "calendar": S.calendar(tenant),
                    "filings": S.filings(tenant), "certs": S.certs(tenant), "never": R.NEVER, "check": R.CHECK_LINE}
        return await run(go)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, b.get("facts"), **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/applicability")
    async def applicability(tenant: str = Depends(current_tenant)):
        return await run(S.applicability, tenant)

    @r.post("/build")
    async def build(tenant: str = Depends(current_tenant)):
        return await run(S.build, tenant)

    @r.get("/calendar")
    async def calendar(ahead: int = 60, area: str = "", state: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.calendar, tenant, max(1, min(ahead, 400)), area, state)

    @r.get("/rules")
    async def rules():
        return {"catalogue": [{"key": c["key"], "area": c["area"], "label": c["label"], "freq": c["freq"], "link": c.get("link", ""),
                               "portal": c.get("portal", ""), "evidence": c.get("evidence", ""),
                               "penalty": (c.get("penalty") or {}).get("text", ""), "source": R.source(c),
                               "verify": bool(c.get("verify")) or not c.get("src")} for c in R.CATALOGUE],
                "never": R.NEVER, "check": R.CHECK_LINE}

    @r.post("/items")
    async def add_item(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_custom, tenant, _s(b.get("label")), _s(b.get("due")), _s(b.get("area") or "custom"),
                         _s(b.get("owner")), _s(b.get("note")))

    @r.get("/items/{ref}")
    async def get_item(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.item, tenant, ref)

    @r.patch("/items/{ref}")
    async def patch_item(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.item_update, tenant, ref, _s(b.get("due")), b.get("owner"), _s(b.get("note")))

    @r.post("/items/{ref}/evidence")
    async def evidence(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_evidence, tenant, ref, _s(b.get("file_id")), _s(b.get("note")))

    @r.post("/items/{ref}/done")
    async def done(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark_done, tenant, ref, _s(b.get("file_id")), _s(b.get("note")), bool(b.get("her_word")),
                         _s(b.get("ack")), _s(b.get("on")))

    @r.post("/items/{ref}/na")
    async def na(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.mark_na, tenant, ref, _s(_b(body).get("reason")))

    @r.post("/items/{ref}/reopen")
    async def reopen(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.reopen, tenant, ref)

    @r.post("/items/{ref}/filing")
    async def filing(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.filing_request, tenant, ref)

    @r.get("/items/{ref}/nudge")
    async def nudge(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.nudge, tenant, ref)

    @r.get("/filings")
    async def list_filings(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"filings": await run(S.filings, tenant, status)}

    @r.post("/filings/{fid}/decide")
    async def decide_filing(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_filing, tenant, fid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.get("/certificate")
    async def certificate(month: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.certificate, tenant, month)

    @r.post("/certificate")
    async def cert_request(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.cert_request, tenant, _s(_b(body).get("month")))

    @r.get("/certs")
    async def list_certs(tenant: str = Depends(current_tenant)):
        return {"certs": await run(S.certs, tenant)}

    @r.post("/certs/{cid}/decide")
    async def decide_cert(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide_cert, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    @r.post("/forget")
    async def forget(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.forget_person, tenant, _s(_b(body).get("name")))

    return r
