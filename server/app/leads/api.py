"""HTTP routes of the LEADS engine (/api/leads/*), key-protected. HER taps live here: the run, the export, the
campaign-list hand-off and the forget button. The engine still never contacts anyone - a campaign-list response
creates a COPY for the campaign desk; the sending side is that desk's own consent machinery."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from .. import leadscap
    from . import rules as R
    from . import service as S

    r = APIRouter(prefix="/api/leads", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(lambda: {"store": S.store_summary(tenant), "usage": leadscap.usage(tenant),
                                  "caps": leadscap.caps(), "lanes": list(R.LANES),
                                  "lanes_built": {k: v for k, v in R.LANE_BUILT.items()},
                                  "never": R.NEVER, "one_question": R.ONE_QUESTION,
                                  "store_boundary": R.STORE_BOUNDARY})

    @r.post("/runs/her-data")
    async def post_her_data(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        lanes = [str(b.get("lane") or "HER_DATA")]
        return await run(S.run_her_data, tenant, str(b.get("ask") or ""), b.get("rows") or [],
                         str(b.get("source_name") or "her-data"), str(b.get("place") or ""), lanes)

    @r.post("/runs/indiamart")
    async def post_indiamart(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """P1 REGISTRY lane: IndiaMART sellers (official IndiaMART MCP server via app/indiamart.py), free."""
        b = _b(body)
        cities = b.get("cities") if isinstance(b.get("cities"), list) else None
        try:
            return await S.run_indiamart(tenant, str(b.get("ask") or ""), str(b.get("search_term") or ""),
                                         str(b.get("city") or ""), cities, str(b.get("biztype") or ""),
                                         str(b.get("place") or ""), int(b.get("max_rows") or 200))
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/runs/places")
    async def post_places(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """P1 OFFICIAL_API lane: the EXISTING maps tools (maps.nearby list, maps.place_details bought per place
        under the mapsbill cap) - no second Google client."""
        b = _b(body)
        try:
            return await S.run_places(tenant, str(b.get("ask") or ""), b.get("kinds"), str(b.get("near") or ""),
                                      float(b.get("sweep_km") or 5.0), float(b.get("cell_km") or 2.0),
                                      bool(b.get("details")), str(b.get("place") or ""),
                                      int(b.get("max_rows") or 1000))
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/enrich")
    async def post_enrich(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """P2 ENRICHMENT: the crawl-brain pass over kept rows' OWN websites - emails + socials, DNS->MX grading,
        ONE billed model pick per row. The cap refuses at plan time; a refusal is a 400 with the reason."""
        b = _b(body)
        ids = b.get("row_ids") if isinstance(b.get("row_ids"), list) else None
        try:
            return await S.enrich(tenant, str(b.get("ask") or ""), ids, str(b.get("q") or ""),
                                  str(b.get("city") or ""), str(b.get("category") or ""),
                                  str(b.get("lane") or ""), str(b.get("run_id") or ""),
                                  bool(b.get("use_model", True)))
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/rows")
    async def post_row(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_row, tenant, b.get("row") or {}, str(b.get("source_lane") or ""),
                         str(b.get("source_url") or ""), str(b.get("run_id") or ""))

    @r.get("/runs")
    async def get_runs(limit: int = 20, tenant: str = Depends(current_tenant)):
        return {"runs": await run(S.runs, tenant, limit)}

    @r.get("/runs/{run_id}")
    async def get_run(run_id: str, tenant: str = Depends(current_tenant)):
        card = await run(S.run_card, run_id)
        if card is None or card.get("tenant") != tenant:
            raise HTTPException(404, "run nahi mila")
        return card

    @r.get("/rows")
    async def get_rows(q: str = "", city: str = "", category: str = "", lane: str = "", has_phone: bool = False,
                       has_email: bool = False, limit: int = 50, offset: int = 0,
                       tenant: str = Depends(current_tenant)):
        return await run(S.rows, tenant, q, city, category, lane, has_phone, has_email, None, limit, offset)

    @r.post("/export")
    async def post_export(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.export_csv, tenant, str(b.get("q") or ""), str(b.get("city") or ""),
                         str(b.get("category") or ""), str(b.get("lane") or ""), bool(b.get("has_phone")),
                         bool(b.get("has_email")), str(b.get("run_id") or ""), b.get("opt_out", False))

    @r.post("/campaign-list")
    async def post_campaign_list(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.campaign_list, tenant, str(b.get("name") or "Leads list"), str(b.get("q") or ""),
                         str(b.get("city") or ""), str(b.get("category") or ""), str(b.get("lane") or ""),
                         str(b.get("run_id") or ""))

    @r.post("/opt-out")
    async def post_opt_out(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_opt_out, tenant, str(b.get("contact_id") or ""), bool(b.get("opt_out", True)))

    @r.post("/forget")
    async def post_forget(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ids = b.get("row_ids") if isinstance(b.get("row_ids"), list) else None
        return await run(S.forget, tenant, str(b.get("run_id") or ""), ids, bool(b.get("all_rows")))

    return r
