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
        "Leads ka run chalao (Leads Sahayak). Paanch actions:\n"
        "- action=her_data: uski apni rows (CSV/Excel/purani campaign list) store mein - har row ke saath source, "
        "dedupe, E.164 phone.\n"
        "- action=indiamart: IndiaMART ke SELLERS (official IndiaMART MCP server, muft) - search_term (jaise "
        "'cement', 'LED bulb'), city ya cities (max 5), biztype (manufacturer/exporter/wholesaler/retailer), "
        "max_rows (default 200). Har row ke saath seller ka IndiaMART page (source), ek business = ek row.\n"
        "- action=places: Google Places EXISTING maps tools se - kinds (Google place types, jaise pharmacy, "
        "hardware_store), near (jaise 'Pune'), sweep_km (default 5, 20-ka-Nearby-ceiling tiles se toota), "
        "details (default false - phone/website mehenge hain, sirf details_max jagahon ke liye kharide jaate "
        "hain, mapsbill cap ke neeche), max_rows. Har row ke saath Google Maps link (source).\n"
        "- action=scrape: Google Maps PUBLIC LISTING grid (P3, SCRAPE lane) - query (jaise 'dentists'), near YA "
        "center {lat,lng}, sweep_km (default 3), zoom (ladder 13-17, default 15 = 1 km cells), max_rows. "
        "Per-tenant opt-in OFF hai - pehli baar pehle REFUSE hoga aur bolega ki aapki haan se on karna hai "
        "(action=scrape_optin on=true). Opt-in ho to: politeness 1 req/s, max 400 cells (plan-time cap), 20 "
        "listings/page, block page par run ruk jaata hai, har row FACTS only (review text/photos kabhi nahi), "
        "source = jis search page se read hua, resume_run_id se grid wahin se continue hota hai.\n"
        "- action=vendor: LICENSED LEAD-DATA VENDOR (P4, VENDOR lane) - query (jaise 'dentists Pune'), city, "
        "max_rows. Config-gated: jab tak aapne vendor ka naam/base/key/price/terms set nahi kiya, lane card par "
        "bhi nahi aur refusal exact config batata hai (plan 12.4 - vendor ka naam aap leti hain). Config ho to: "
        "plan card run ko PEHLE price karta hai (rows x LEADS_VENDOR_PRICE_PER_ROW_INR) - estimate "
        "LEADS_VENDOR_RUN_CAP_INR paar to REFUSE, run shuru nahi hota. Ek hi vendor call per run, dobara nahi "
        "mangi jaati (vendor per call bill kar sakta hai). Har row ke saath vendor ka apna record page hota hi "
        "hai - bina source ki row store nahi hoti. Bill vendor ke apne reported cost par, warna ESTIMATE - aur "
        "karte hain.\n"
        "- action=scrape_optin: SCRAPE lane ka per-tenant switch - on=true par walls quote hoti hain (CLAUDE.md "
        "ka amended rule), off=false par lane phir band. Yeh aapka apna act hai - engine khud kabhi nahi karega.\n"
        "Plan PEHLE banta hai (caps: per-run rows, per-day 20,000) - cap paar hua to refuse, cap ka naam batate "
        "hue. Yeh engine kabhi khud kisi ko message NAHI bhejta - outreach sirf aapke tap par, campaign desk se."),
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
        "Ek leads run ya poore store ka haal (kuch nahi badalta). run_id do to uska card: status, found/kept/"
        "duped/refused, lanes, cap check. run_id na do to store ka summary: kitni rows, kitni phone/email waali, "
        "lane-wise count, aaj ka cap usage."),
     "input_schema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": []}},
    {"name": "leads_list", "description": (
        "Leads store khojo (kuch nahi badalta). q (naam/category/address mein), city, category, lane (HER_DATA ...), "
        "has_phone, has_email, limit -> rows with key_type/key_value aur provenance."),
     "input_schema": {"type": "object", "properties": {
         "q": {"type": "string"}, "city": {"type": "string"}, "category": {"type": "string"},
         "lane": {"type": "string"}, "has_phone": {"type": "boolean"}, "has_email": {"type": "boolean"},
         "limit": {"type": "integer"}, "offset": {"type": "integer"}}, "required": []}},
    {"name": "leads_export", "description": (
        "Leads bahar bhejo. action=csv: filters (q/city/category/lane/has_phone/has_email/run_id) -> CSV file "
        "(har row ke saath source_lane + source_url + parser_version - bina provenance ki row ho to export REFUSE). "
        "opt_out rows default se bahar. action=campaign_list: name + filters -> WhatsApp campaign desk ke liye "
        "LeadList banti hai (sirf phone waali rows, consent har row par False; engine khud kuch NAHI bhejta - bhejna "
        "campaign desk ke consent machinery se, aapke tap par)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["csv", "campaign_list"]},
         "name": {"type": "string"}, "q": {"type": "string"}, "city": {"type": "string"},
         "category": {"type": "string"}, "lane": {"type": "string"}, "has_phone": {"type": "boolean"},
         "has_email": {"type": "boolean"}, "run_id": {"type": "string"}}, "required": ["action"]}},
    {"name": "leads_forget", "description": (
        "Leads mitao (DPO duty: purpose limitation + erasure). run_id ya row_ids [] ya all_rows=true. Jo din ka "
        "cap ledger hai woh rehta hai (din ka hisaab, personal data nahi). Engine ke paas jo row thi woh jaati hai "
        "aur uski campaign-list copy bhi."),
     "input_schema": {"type": "object", "properties": {
         "run_id": {"type": "string"}, "row_ids": {"type": "array", "items": {"type": "string"}},
         "all_rows": {"type": "boolean"}}, "required": []}},
    {"name": "leads_enrich", "description": (
        "Store ki kept rows ENRICH karo (P2, chalu hai). Har row ke apni WEBSITE ka ek chhota crawl-brain pass: "
        "email (mailto + page text), socials (uski site ke links - linkedin/twitter/instagram/facebook/youtube), "
        "email_grade (DNS -> MX -> disposable: pakka / sadak_tak / galat; SMTP probe NAHI hota). Sabse accha "
        "email ek chhota model call chunta hai (bill run card par) - use_model=false par rule rank. Robots.txt "
        "maane jaate hain, site par 1 req/second, max 3 page/site; mari hui site galat dikhata hai, crash nahi. "
        "Cap: LEADS_ENRICH_ROWS_PER_RUN (100/pass) - usse zyada eligible rows par REFUSE (filter ghatao ya "
        "row_ids do). Naya email sirf KHAALI email slot mein jaata hai - kisi aur ka bhara hua email overwrite "
        "nahi hota. fanout=true (P4 scale): wahi per-row kaam HOOLA GRAPH par bikharta hai (dispatch -> chunks "
        "-> join barrier) - sabse zyada leads_enrich_fanout_max site passes ek saath, likhna barrier ke baad ek "
        "writer se. Social PLATFORMS scrape nahi hote, engine khud kisi se baat nahi karta."),
     "input_schema": {"type": "object", "properties": {
         "row_ids": {"type": "array", "items": {"type": "string"}}, "run_id": {"type": "string"},
         "q": {"type": "string"}, "city": {"type": "string"}, "category": {"type": "string"},
         "lane": {"type": "string"}, "use_model": {"type": "boolean"}, "fanout": {"type": "boolean"},
         "ask": {"type": "string"}},
         "required": []}},
]
LEADS_LABELS = {"leads_run": "Leads ka run bana raha hoon", "leads_status": "Leads ka haal dekh raha hoon",
                "leads_list": "Leads store khoj raha hoon", "leads_export": "Leads export taiyaar kar raha hoon",
                "leads_forget": "Leads mita raha hoon (aapke kaha se)",
                "leads_enrich": "Rows ki website padh ke email/socials bhar raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    a = getattr(ctx, "actor", "owner") or "owner"
    if a.startswith("customer:"):
        raise ToolError("Yeh aapke dhandhe ka leads kaam hai; graahak ke liye nahi.")
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
    raise ToolError("action galat (her_data | indiamart | places | scrape | vendor | scrape_optin | plan)")


async def leads_status(ctx: Ctx, **a: Any):
    from ..leads import service as S
    from .. import leadscap
    _actor(ctx)
    t, rid = ctx.tenant_id, _s(a.get("run_id"))

    def go():
        if rid:
            card = S.run_card(rid)
            if card is None or card.get("tenant") != t:
                raise ToolError("run nahi mila")
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
            return await asyncio.to_thread(S.campaign_list, t, _s(a.get("name")) or "Leads list", _s(f.get("q")),
                                           _s(f.get("city")), _s(f.get("category")), _s(f.get("lane")),
                                           _s(f.get("run_id")))
    except (S.LeadsError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat (csv | campaign_list)")


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
