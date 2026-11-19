"""Leads Sahayak tools (v0.540.0 NEEV, v0.541.0 OFFICIAL LANES, v0.542.0 ENRICHMENT, v0.543.0 SCRAPE LANE,
v0.544.0 VENDOR + SCALE). `leads_run` works her data (P0), the IndiaMART MCP sellers lane (P1 REGISTRY), the
Places lane through the EXISTING maps tools (P1 OFFICIAL_API), - only when SHE has flipped the per-tenant
opt-in that is OFF by default - the Google Maps PUBLIC LISTING scrape grid (P3 SCRAPE; the CLAUDE.md rule text
was amended in the same commit that built it), and the licensed lead-data vendor (P4 VENDOR: config-gated - no
vendor named, no lane; priced on the plan card BEFORE the run). `leads_enrich` is the P2 pass over kept rows'
OWN websites, with the P4 fanout=True walking the HOOLA GRAPH (bounded in-flight, join barrier). Every tool
answers with a CARD that names the caps, the lanes and the provenance; the engine never contacts anyone -
outreach is her tap on the campaign / email desks, and the campaign hand-off pre-fills consent False."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

LEADS_TOOLS = [
    {"name": "leads_run", "description": (
        "Run a leads job (Leads Assistant). Six actions:\n"
        "- action=her_data: her own rows (CSV/Excel/old campaign list) go into the store - each row with its source, "
        "dedupe, E.164 phone.\n"
        "- action=indiamart: IndiaMART SELLERS (official IndiaMART MCP server, free) - search_term (e.g. "
        "'cement', 'LED bulb'), city or cities (max 5), biztype (manufacturer/exporter/wholesaler/retailer), "
        "max_rows (default 200). Each row carries the seller's IndiaMART page (source); one business = one row.\n"
        "- action=places: Google Places through the EXISTING maps tools - kinds (Google place types, e.g. pharmacy, "
        "hardware_store), near (e.g. 'Pune'), sweep_km (default 5, split into tiles under the Nearby ceiling of 20), "
        "details (default false - phone/website are costly, bought only for details_max places, "
        "under the mapsbill cap), max_rows. Each row carries a Google Maps link (source).\n"
        "- action=scrape: Google Maps PUBLIC LISTING grid (P3, SCRAPE lane) - query (e.g. 'dentists'), near OR "
        "center {lat,lng}, sweep_km (default 3), zoom (ladder 13-17, default 15 = 1 km cells), max_rows. "
        "Per-tenant opt-in is OFF - the first time it REFUSES and says it needs her yes to turn on "
        "(action=scrape_optin on=true). Once opted in: politeness 1 req/s, max 400 cells (plan-time cap), 20 "
        "listings/page, the run stops at a block page, every row is FACTS only (never review text/photos), "
        "source = the search page it was read from, resume_run_id continues the grid from where it stopped.\n"
        "- action=vendor: LICENSED LEAD-DATA VENDOR (P4, VENDOR lane) - query (e.g. 'dentists Pune'), city, "
        "max_rows. Config-gated: until she has set the vendor name/base/key/price/terms the lane is not even on the "
        "card and the refusal names the exact config (plan 12.4 - she picks the vendor). Once configured: "
        "the plan card PRICES the run first (rows x LEADS_VENDOR_PRICE_PER_ROW_INR) - an estimate above "
        "LEADS_VENDOR_RUN_CAP_INR is REFUSED and the run does not start. One vendor call per run, never repeated "
        "(the vendor may bill per call). Each row carries the vendor's own record page - "
        "a row without a source is not stored. Billed at the vendor's own reported cost, else an ESTIMATE - and "
        "marked as such.\n"
        "- action=scrape_optin: the per-tenant switch of the SCRAPE lane - on=true quotes the walls (the amended rule "
        "in CLAUDE.md), off=false closes the lane again. This is HER own act - the engine never does it itself.\n"
        "The plan is made FIRST (caps: per-run rows, per-day 20,000) - over the cap it refuses and names the cap. "
        "This engine NEVER messages anyone itself - outreach happens only on her tap, from the campaign desk."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["her_data", "indiamart", "places", "scrape", "vendor", "scrape_optin"]},
         "ask": {"type": "string"}, "place": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}}, "source_name": {"type": "string"},
         "lane": {"type": "string"},
         "search_term": {"type": "string"}, "city": {"type": "string"},
         "cities": {"type": "array", "items": {"type": "string"}}, "biztype": {"type": "string"},
         "kinds": {"type": "array", "items": {"type": "string"}}, "near": {"type": "string"},
         "sweep_km": {"type": "number"}, "cell_km": {"type": "number"}, "details": {"type": "boolean"},
         "query": {"type": "string"}, "center": {"type": "object"}, "zoom": {"type": "integer"},
         "resume_run_id": {"type": "string"}, "on": {"type": "boolean"},
         "max_rows": {"type": "integer"}}, "required": ["action", "ask"]}},
    {"name": "leads_status", "description": (
        "Status of one leads run or of the whole store (changes nothing). With run_id: its card - status, found/kept/"
        "duped/refused, lanes, cap check. Without run_id: the store summary - how many rows, how many with phone/email, "
        "count per lane, today's cap usage."),
     "input_schema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": []}},
    {"name": "leads_list", "description": (
        "Search the leads store (changes nothing). q (in name/category/address), city, category, lane (HER_DATA ...), "
        "has_phone, has_email, limit -> rows with key_type/key_value and provenance."),
     "input_schema": {"type": "object", "properties": {
         "q": {"type": "string"}, "city": {"type": "string"}, "category": {"type": "string"},
         "lane": {"type": "string"}, "has_phone": {"type": "boolean"}, "has_email": {"type": "boolean"},
         "limit": {"type": "integer"}, "offset": {"type": "integer"}}, "required": []}},
    {"name": "leads_export", "description": (
        "Export leads. action=csv: filters (q/city/category/lane/has_phone/has_email/run_id) -> CSV file "
        "(each row with source_lane + source_url + parser_version - the export REFUSES any row without provenance). "
        "opt_out rows are excluded by default. action=campaign_list: a LeadList for the WhatsApp campaign desk - the FIRST TAP "
        "only brings a CONFIRM CARD (rows, rows_without_phone, opt_out_excluded - nothing is made); on her tap, "
        "confirm=true is the second tap that makes the list (only rows with a phone, consent False on every row; the engine "
        "sends NOTHING itself - sending goes through the campaign desk's consent machinery, on her tap). action=outreach_log: "
        "the lead_outreach ledger - which row went out when, through which desk (campaign/email), with which list/campaign/draft."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["csv", "campaign_list", "outreach_log"]},
         "name": {"type": "string"}, "q": {"type": "string"}, "city": {"type": "string"},
         "category": {"type": "string"}, "lane": {"type": "string"}, "has_phone": {"type": "boolean"},
         "has_email": {"type": "boolean"}, "run_id": {"type": "string"}, "confirm": {"type": "boolean"},
         "kind": {"type": "string", "enum": ["campaign_list", "campaign_sent", "email_sent"]},
         "limit": {"type": "integer"}}, "required": ["action"]}},
    {"name": "leads_forget", "description": (
        "Delete leads (DPO duty: purpose limitation + erasure). run_id or row_ids [] or all_rows=true. The daily "
        "cap ledger stays (a day's count, not personal data). Every row the engine held goes, "
        "and its campaign-list copy too."),
     "input_schema": {"type": "object", "properties": {
         "run_id": {"type": "string"}, "row_ids": {"type": "array", "items": {"type": "string"}},
         "all_rows": {"type": "boolean"}}, "required": []}},
    {"name": "leads_enrich", "description": (
        "ENRICH the kept rows in the store (P2, live). A small crawl-brain pass over each row's own WEBSITE: "
        "email (mailto + page text), socials (links on its site - linkedin/twitter/instagram/facebook/youtube), "
        "email_grade (DNS -> MX -> disposable: pakka / sadak_tak / galat; NO SMTP probe). A small model call picks the best "
        "email (billed on the run card) - with use_model=false a rule ranks them. Robots.txt "
        "is obeyed, 1 req/second per site, max 3 pages/site; a dead site shows as bad, no crash. "
        "Cap: LEADS_ENRICH_ROWS_PER_RUN (100/pass) - more eligible rows than that is REFUSED (narrow the filter or give "
        "row_ids). A new email goes only into an EMPTY email slot - nobody else's filled email is overwritten. "
        "fanout=true (P4 scale): the same per-row work is spread on HOOLA GRAPH (dispatch -> chunks "
        "-> join barrier) - at most leads_enrich_fanout_max site passes at once, writing after the barrier by one "
        "writer. Social PLATFORMS are not scraped, and the engine never talks to anyone itself."),
     "input_schema": {"type": "object", "properties": {
         "row_ids": {"type": "array", "items": {"type": "string"}}, "run_id": {"type": "string"},
         "q": {"type": "string"}, "city": {"type": "string"}, "category": {"type": "string"},
         "lane": {"type": "string"}, "use_model": {"type": "boolean"}, "fanout": {"type": "boolean"},
         "ask": {"type": "string"}},
         "required": []}},
]
LEADS_LABELS = {"leads_run": "Creating a leads run", "leads_status": "Checking leads status",
                "leads_list": "Searching the leads store", "leads_export": "Preparing the leads export",
                "leads_forget": "Deleting leads (as you asked)",
                "leads_enrich": "Reading row websites to fill in emails and socials"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    a = getattr(ctx, "actor", "owner") or "owner"
    if a.startswith("customer:"):
        raise ToolError("This is lead work for her own business, not for customers.")
    return a


def _rows(v: Any) -> list[dict]:
    return [r for r in (v or []) if isinstance(r, dict)]


def _filters(a: dict) -> dict:
    keep = ("q", "city", "category", "lane", "has_phone", "has_email", "run_id")
    return {k: a.get(k) for k in keep if a.get(k) not in (None, "", False)}


async def leads_run(ctx: Ctx, action, **a: Any):
    from ..leads import service as S
    from .. import leadscap
    _actor(ctx)
    t, action = ctx.tenant_id, str(action)
    try:
        if action == "her_data":
            return await asyncio.to_thread(S.run_her_data, t, _s(a.get("ask")), _rows(a.get("rows")),
                                           _s(a.get("source_name")) or "her-data", _s(a.get("place")),
                                           [str(a.get("lane") or "HER_DATA")])
        if action == "indiamart":
            cities = a.get("cities") if isinstance(a.get("cities"), list) else None
            return await S.run_indiamart(t, _s(a.get("ask")), _s(a.get("search_term")), _s(a.get("city")),
                                         cities, _s(a.get("biztype")), _s(a.get("place")),
                                         int(a.get("max_rows") or 200))
        if action == "places":
            return await S.run_places(t, _s(a.get("ask")), a.get("kinds"), _s(a.get("near")),
                                      float(a.get("sweep_km") or 5.0), float(a.get("cell_km") or 2.0),
                                      bool(a.get("details")), _s(a.get("place")),
                                      int(a.get("max_rows") or 1000))
        if action == "scrape":
            center = a.get("center") if isinstance(a.get("center"), dict) else None
            return await S.run_scrape(t, _s(a.get("ask")), _s(a.get("query") or _s(a.get("search_term"))),
                                      _s(a.get("near")), center, float(a.get("sweep_km") or 3.0),
                                      int(a.get("zoom") or 15), int(a.get("max_rows") or 1000),
                                      _s(a.get("place")), _s(a.get("resume_run_id")))
        if action == "vendor":
            return await S.run_vendor(t, _s(a.get("ask")), _s(a.get("query") or _s(a.get("search_term"))),
                                      _s(a.get("city")), int(a.get("max_rows") or 1000), _s(a.get("place")))
        if action == "scrape_optin":
            return await asyncio.to_thread(S.set_scrape_optin, t, bool(a.get("on")), _actor(ctx))
        if action == "plan":
            return await asyncio.to_thread(S.plan, t, _s(a.get("ask")), [str(a.get("lane") or "HER_DATA")],
                                           _s(a.get("place")), int(a.get("planned_rows") or 0))
    except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("Unknown action (her_data | indiamart | places | scrape | vendor | scrape_optin | plan)")


async def leads_status(ctx: Ctx, **a: Any):
    from ..leads import service as S
    from .. import leadscap
    _actor(ctx)
    t, rid = ctx.tenant_id, _s(a.get("run_id"))

    def go():
        if rid:
            card = S.run_card(rid)
            if card is None or card.get("tenant") != t:
                raise ToolError("run not found")
            return card
        from ..leads import scale as _scale
        return {"store": S.store_summary(t), "usage": leadscap.usage(t), "runs": S.runs(t, 5),
                "store_backend": _scale.store_backend()}

    try:
        return await asyncio.to_thread(go)
    except (S.LeadsError, ValueError) as e:
        raise ToolError(str(e))


async def leads_list(ctx: Ctx, **a: Any):
    from ..leads import service as S
    _actor(ctx)
    f = _filters(a)
    try:
        return await asyncio.to_thread(S.rows, ctx.tenant_id, _s(f.get("q")), _s(f.get("city")),
                                       _s(f.get("category")), _s(f.get("lane")), bool(f.get("has_phone")),
                                       bool(f.get("has_email")), None, int(a.get("limit") or 50),
                                       int(a.get("offset") or 0))
    except (S.LeadsError, ValueError) as e:
        raise ToolError(str(e))


async def leads_export(ctx: Ctx, action, **a: Any):
    from ..leads import service as S
    _actor(ctx)
    t, action = ctx.tenant_id, str(action)
    f = _filters(a)
    try:
        if action == "csv":
            return await asyncio.to_thread(S.export_csv, t, _s(f.get("q")), _s(f.get("city")), _s(f.get("category")),
                                           _s(f.get("lane")), bool(f.get("has_phone")), bool(f.get("has_email")),
                                           _s(f.get("run_id")), False)
        if action == "campaign_list":
            # kwargs on purpose - the old positional call dropped run_id into the has_phone slot (P5 fix)
            return await asyncio.to_thread(S.campaign_list, t, _s(a.get("name")) or "Leads list",
                                           q=_s(f.get("q")), city=_s(f.get("city")),
                                           category=_s(f.get("category")), lane=_s(f.get("lane")),
                                           run_id=_s(f.get("run_id")), confirm=bool(a.get("confirm")))
        if action == "outreach_log":
            return await asyncio.to_thread(S.outreach_log, t, _s(a.get("kind")), int(a.get("limit") or 200))
    except (S.LeadsError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("Unknown action (csv | campaign_list | outreach_log)")


async def leads_forget(ctx: Ctx, **a: Any):
    from ..leads import service as S
    _actor(ctx)
    ids = a.get("row_ids") if isinstance(a.get("row_ids"), list) else None
    try:
        return await asyncio.to_thread(S.forget, ctx.tenant_id, _s(a.get("run_id")), ids, bool(a.get("all_rows")))
    except (S.LeadsError, ValueError) as e:
        raise ToolError(str(e))


async def leads_enrich(ctx: Ctx, **a: Any):
    """The P2 pass (app/leads/enrich.py), P4 fanout optional: each kept row's OWN website read once through
    the EXISTING scrape stack (SSRF guard, robots gate, 1 req/s), deliverability graded honestly, the best
    email one billed model call. The cap refuses at plan time - a refusal is the answer, never a truncate.
    fanout=true walks the HOOLA GRAPH (leads/scale.py): bounded in-flight, join barrier, writes after it."""
    from ..leads import service as S
    from .. import leadscap
    _actor(ctx)
    ids = a.get("row_ids") if isinstance(a.get("row_ids"), list) else None
    try:
        return await S.enrich(ctx.tenant_id, _s(a.get("ask")), ids, _s(a.get("q")), _s(a.get("city")),
                              _s(a.get("category")), _s(a.get("lane")), _s(a.get("run_id")),
                              bool(a.get("use_model", True)), bool(a.get("fanout")))
    except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
        raise ToolError(str(e))


LEADS_HANDLERS = {"leads_run": leads_run, "leads_status": leads_status, "leads_list": leads_list,
                  "leads_export": leads_export, "leads_forget": leads_forget, "leads_enrich": leads_enrich}
