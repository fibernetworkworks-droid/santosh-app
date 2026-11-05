"""Leads Sahayak tools (v0.540.0 LEADS NEEV). `leads_run` works (P0: her own data only - L0), the other four read,
export or erase. Every tool answers with a CARD that names the caps, the lanes and the provenance; the engine never
contacts anyone - outreach is her tap on the campaign / email desks, and the campaign hand-off pre-fills consent False."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

LEADS_TOOLS = [
    {"name": "leads_run", "description": (
        "Leads ka run chalao (Leads Sahayak). P0 mein lane sirf 'HER_DATA' hai: uski apni rows (CSV/Excel/purani "
        "campaign list se nikale gaye businesses) engine ke store mein jayengi - har row ke saath source, dedupe "
        "same business ko ek row, E.164 phone. action=her_data: ask (kya liya), rows [{name, phone, category, city, "
        "address, email, website, rating, review_count}], source_name (file/list ka naam). Plan PEHLE banta hai "
        "(caps: 5,000 rows/run, 20,000/day) - cap paar hua to refuse hota hai, cap ka naam batate hue. Doosri lanes "
        "(REGISTRY / OFFICIAL_API / SCRAPE / VENDOR) abhi built nahi - naam se refuse, phase batate hue."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["her_data"]},
         "ask": {"type": "string"}, "place": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}},
         "source_name": {"type": "string"}, "lane": {"type": "string"}}, "required": ["action", "ask"]}},
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
]
LEADS_LABELS = {"leads_run": "Leads ka run bana raha hoon", "leads_status": "Leads ka haal dekh raha hoon",
                "leads_list": "Leads store khoj raha hoon", "leads_export": "Leads export taiyaar kar raha hoon",
                "leads_forget": "Leads mita raha hoon (aapke kaha se)"}


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
        if action == "plan":
            return await asyncio.to_thread(S.plan, t, _s(a.get("ask")), [str(a.get("lane") or "HER_DATA")],
                                           _s(a.get("place")), int(a.get("planned_rows") or 0))
    except (S.LeadsError, leadscap.LeadsCapped, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat (P0 mein sirf her_data / plan)")


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
        return {"store": S.store_summary(t), "usage": leadscap.usage(t), "runs": S.runs(t, 5)}

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


LEADS_HANDLERS = {"leads_run": leads_run, "leads_status": leads_status, "leads_list": leads_list,
                  "leads_export": leads_export, "leads_forget": leads_forget}
