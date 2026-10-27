"""HTTP routes of the Customs Sahayak (/api/customs/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY way filing data goes to the CHA: POST /api/customs/filings/{id}/decide from her app (her tap). Hoola never files a Bill of
Entry on ICEGATE and never pays duty."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/customs", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.CustomsError, ValueError) as e:
            raise HTTPException(400, str(e))

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
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    @r.get("/shipments")
    async def list_shipments(status: str = "", tenant: str = Depends(current_tenant)):
        return {"shipments": await run(S.shipments, tenant, status)}

    @r.post("/shipments")
    async def new_shipment(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kw = {k: b[k] for k in (*S._SHIP_KEYS, "lines") if k in b}
        return await run(S.new_shipment, tenant, **kw)

    @r.get("/shipments/{ref}")
    async def get_shipment(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.shipment_view, tenant, ref)

    @r.patch("/shipments/{ref}")
    async def patch_shipment(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        kw = {k: b[k] for k in (*S._SHIP_KEYS, "lines", "replace") if k in b}
        return await run(S.update_shipment, tenant, ref, **kw)

    @r.post("/shipments/{ref}/cancel")
    async def cancel(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.cancel, tenant, ref, str(_b(body).get("reason") or ""))

    @r.post("/shipments/{ref}/lines")
    async def lines(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ln = b.get("lines") if isinstance(b.get("lines"), list) else [b]
        return await run(S.set_lines, tenant, ref, ln, bool(b.get("replace")))

    @r.delete("/shipments/{ref}/lines/{no}")
    async def remove_line(ref: str, no: int, tenant: str = Depends(current_tenant)):
        return await run(S.remove_line, tenant, ref, no)

    @r.post("/hs/suggest")
    async def hs_suggest(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.hs_suggest, tenant, str(b.get("desc") or ""), bool(b.get("retail")))

    @r.post("/shipments/{ref}/hs")
    async def hs_confirm(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.hs_confirm, tenant, ref, int(b.get("line") or 0), str(b.get("hs") or ""))

    @r.post("/shipments/{ref}/docs")
    async def mark_doc(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.mark_doc, tenant, ref, str(b.get("key") or ""), str(b.get("status") or "have"), str(b.get("note") or ""),
                         str(b.get("file_id") or ""))

    @r.get("/shipments/{ref}/cost")
    async def cost(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.cost, tenant, ref)

    @r.post("/shipments/{ref}/stage")
    async def stage(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        extra = {k: b[k] for k in ("be_no", "be_date", "igm_no", "amount") if k in b}
        return await run(S.update_stage, tenant, ref, str(b.get("stage") or ""), str(b.get("at") or ""), str(b.get("note") or ""),
                         str(b.get("by") or ""), **extra)

    @r.post("/shipments/{ref}/filing")
    async def filing(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.request_filing, tenant, ref)

    @r.post("/shipments/{ref}/datasheet")
    async def datasheet(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.datasheet, tenant, ref)

    @r.get("/filings")
    async def list_filings(status: str = "", tenant: str = Depends(current_tenant)):
        return {"filings": await run(S.filings, tenant, status)}

    @r.post("/filings/{fid}/decide")
    async def decide(fid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Her tap on the filing card (the only place by_tap=True is set)."""
        b = _b(body)
        return await run(S.decide_filing, tenant, fid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("reason") or ""), by_tap=True)

    @r.get("/icegate_steps")
    async def steps():
        return {"steps": S.icegate_steps()}

    return r
