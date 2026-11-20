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
        from . import scale as _scale
        return await run(lambda: {"store": S.store_summary(tenant), "usage": leadscap.usage(tenant),
                                  "caps": leadscap.caps(), "lanes": list(R.LANES),
                                  "lanes_built": {k: v for k, v in R.LANE_BUILT.items()},
                                  "store_backend": _scale.store_backend(),
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
        ONE billed model pick per row. fanout=true (P4) walks the HOOLA GRAPH: bounded in-flight site passes,
        join barrier, the writes land after it. The cap refuses at plan time; a refusal is a 400."""
        b = _b(body)
        ids = b.get("row_ids") if isinstance(b.get("row_ids"), list) else None
        try:
            return await S.enrich(tenant, str(b.get("ask") or ""), ids, str(b.get("q") or ""),
                                  str(b.get("city") or ""), str(b.get("category") or ""),
                                  str(b.get("lane") or ""), str(b.get("run_id") or ""),
                                  bool(b.get("use_model", True)), bool(b.get("fanout")))
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/runs/vendor")
    async def post_vendor(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """P4 VENDOR lane: the licensed lead-data vendor (config-gated - no vendor named, no lane; the plan
        card prices the run BEFORE it and the estimate over the run cap refuses at plan time)."""
        b = _b(body)
        try:
            return await S.run_vendor(tenant, str(b.get("ask") or ""), str(b.get("query") or ""),
                                      str(b.get("city") or ""), int(b.get("max_rows") or 1000),
                                      str(b.get("place") or ""))
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/runs/scrape")
    async def post_scrape(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """P3 SCRAPE lane: the Google Maps PUBLIC LISTING grid (per-tenant opt-in OFF by default - the flip is
        POST /scrape-optin, her act). Caps refused at plan time; a block wall aborts the run with the reason."""
        b = _b(body)
        center = b.get("center") if isinstance(b.get("center"), dict) else None
        try:
            return await S.run_scrape(tenant, str(b.get("ask") or ""), str(b.get("query") or ""),
                                      str(b.get("near") or ""), center, float(b.get("sweep_km") or 3.0),
                                      int(b.get("zoom") or 15), int(b.get("max_rows") or 1000),
                                      str(b.get("place") or ""), str(b.get("resume_run_id") or ""))
        except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/scrape-optin")
    async def post_scrape_optin(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """HER act: flip the SCRAPE lane's per-tenant opt-in (OFF by default; the walls are quoted back - the
        amended CLAUDE.md rule text, the store boundary, the never-sends wall)."""
        b = _b(body)
        return await run(S.set_scrape_optin, tenant, bool(b.get("on")), str(b.get("actor") or "owner"))

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
            raise HTTPException(404, "run not found")
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
        """P5: two taps - the default (confirm=False) returns the CONFIRM CARD and creates nothing; her second
        tap (confirm=true) builds the list. Refusals stay 400s."""
        b = _b(body)
        ids = None
        if isinstance(b.get("ids"), list) or b.get("stage"):      # v0.999.47: the rows she ticked, or one stage
            from . import pipeline as PL
            ids = await run(PL.ids_for, tenant, b.get("ids") if isinstance(b.get("ids"), list) else None, str(b.get("stage") or ""))
        return await run(S.campaign_list, tenant, str(b.get("name") or "Leads list"), str(b.get("q") or ""),
                         str(b.get("city") or ""), str(b.get("category") or ""), str(b.get("lane") or ""),
                         True, str(b.get("run_id") or ""), bool(b.get("confirm")), ids)

    @r.get("/outreach")
    async def get_outreach(kind: str = "", limit: int = 200, tenant: str = Depends(current_tenant)):
        """P5: the outreach ledger, readable - every event that left the store through the campaign / email desks."""
        return await run(S.outreach_log, tenant, str(kind or ""), int(limit or 200))

    @r.post("/opt-out")
    async def post_opt_out(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_opt_out, tenant, str(b.get("contact_id") or ""), bool(b.get("opt_out", True)))

    @r.post("/forget")
    async def post_forget(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ids = b.get("row_ids") if isinstance(b.get("row_ids"), list) else None
        return await run(S.forget, tenant, str(b.get("run_id") or ""), ids, bool(b.get("all_rows")))

    # ------------------------------------------------ v0.999.47 LEAD DESK: what happens after a lead is found
    from . import pipeline as PL

    async def prun(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (PL.DeskError, S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.get("/desk")
    async def desk_today(tenant: str = Depends(current_tenant)):
        return await prun(PL.today, tenant)

    @r.get("/desk/summary")
    async def desk_summary(tenant: str = Depends(current_tenant)):
        return await prun(PL.summary, tenant)

    @r.get("/desk/leads")
    async def desk_leads(stage: str = "", q: str = "", city: str = "", lane: str = "", has_phone: bool = False,
                         due: bool = False, limit: int = 50, offset: int = 0, tenant: str = Depends(current_tenant)):
        return await prun(PL.leads, tenant, stage, q, city, lane, has_phone, due, limit, offset)

    @r.get("/desk/leads/{cid}")
    async def desk_lead(cid: str, tenant: str = Depends(current_tenant)):
        try:
            return await asyncio.to_thread(PL.lead, tenant, cid)
        except PL.DeskError as e:
            raise HTTPException(404, str(e))

    @r.post("/desk/stage")
    async def desk_stage(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await prun(PL.set_stage, tenant, b.get("ids") or [], str(b.get("stage") or ""))

    @r.post("/desk/follow")
    async def desk_follow(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await prun(PL.set_follow, tenant, b.get("ids") or [], str(b.get("on") or ""), str(b.get("note") or ""))

    @r.post("/desk/note")
    async def desk_note(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await prun(PL.add_note, tenant, str(b.get("id") or ""), str(b.get("text") or ""))

    @r.post("/desk/draft")
    async def desk_draft(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await prun(PL.draft, tenant, str(b.get("id") or ""), str(b.get("text") or ""))

    @r.get("/desk/quality")
    async def desk_quality(tenant: str = Depends(current_tenant)):
        return await prun(PL.quality, tenant)

    @r.get("/desk/lists")
    async def desk_lists(tenant: str = Depends(current_tenant)):
        return await prun(PL.lists, tenant)

    @r.post("/desk/saved")
    async def desk_save(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await prun(PL.save_search, tenant, str(b.get("name") or ""), str(b.get("lane") or ""),
                          b.get("params") if isinstance(b.get("params"), dict) else {}, bool(b.get("weekly")))

    @r.delete("/desk/saved/{sid}")
    async def desk_drop_saved(sid: str, tenant: str = Depends(current_tenant)):
        return await prun(PL.drop_saved, tenant, sid)

    @r.post("/desk/saved/{sid}/run")
    async def desk_run_saved(sid: str, tenant: str = Depends(current_tenant)):
        try:
            return await PL.run_saved(tenant, sid)
        except (PL.DeskError, S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
            raise HTTPException(400, str(e))

    @r.post("/desk/telecaller")
    async def desk_telecaller(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ids = await prun(PL.ids_for, tenant, b.get("ids") if isinstance(b.get("ids"), list) else None, str(b.get("stage") or ""))
        return await prun(PL.to_telecaller, tenant, ids, bool(b.get("confirm")))

    @r.post("/desk/import")
    async def desk_import(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await prun(PL.import_file, tenant, str(b.get("file_id") or ""), str(b.get("ask") or ""))

    return r
