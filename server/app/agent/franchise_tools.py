"""v0.115 Franchise Sahayak tools (franchise owner / franchisee). `franchise_dekho` only reads; `franchise` does the work.
Reports and statements reach the franchisor only on HER Haan; Hoola never pays royalty and never files on licence portals."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

FRANCHISE_TOOLS = [
    {"name": "franchise", "description": (
        "Franchise owner's coworker (QSR / cafe / salon / school / pharmacy outlets of a brand), end to end. action=settings: "
        "company, state (GST state code), tds_applies. action=agreement: brand, franchisor, contact, royalty_pct, marketing_pct, "
        "tech_fee (per outlet per month), min_guarantee (min royalty per outlet per month), base net|gross, foreign (franchisor "
        "abroad -> GST reverse charge), franchisor_state, due_day, start, term_years, lock_in_years, notice_months, checklist "
        "[brand SOP items]. action=outlet: name, brand, city, opened_on, rent, lease_end, escalation_pct, escalation_on, "
        "targets {food, staff, rent...: % of sales}, manager_phone. action=sale: outlet, net (or gross + discount), gst, orders, "
        "day, channels {dine, swiggy, zomato...}. action=import: outlet, file_id (POS day-wise export). action=cost: outlet, kind "
        "food|staff|rent|utility|aggregator|marketing|maintenance|other, amount, month. action=statement: brand, month (YYYY-MM, "
        "default last month) -> royalty + marketing + GST / RCM + TDS + payable + Excel. action=approve_statement: statement_id "
        "(ONLY on her haan: report draft for the franchisor). action=paid: statement_id, on (she paid). action=licence: outlet, "
        "kind fssai|shop_act|trade|fire_noc|music|signage|health|pollution|..., valid_to, number. action=audit: outlet, failed "
        "[items missed] or items [{item, ok, note}], kind daily|brand. action=pnl_file: month."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "agreement", "outlet", "sale", "import", "cost", "statement", "approve_statement", "paid",
                                               "licence", "audit", "pnl_file"]},
         "company": {"type": "string"}, "state": {"type": "string"}, "tds_applies": {"type": "boolean"}, "brand": {"type": "string"},
         "franchisor": {"type": "string"}, "contact": {"type": "string"}, "royalty_pct": {"type": "number"}, "marketing_pct": {"type": "number"},
         "tech_fee": {"type": "number"}, "min_guarantee": {"type": "number"}, "base": {"type": "string"}, "foreign": {"type": "boolean"},
         "franchisor_state": {"type": "string"}, "due_day": {"type": "integer"}, "start": {"type": "string"}, "term_years": {"type": "integer"},
         "lock_in_years": {"type": "integer"}, "notice_months": {"type": "integer"}, "checklist": {"type": "array", "items": {"type": "string"}},
         "outlet": {"type": "string"}, "name": {"type": "string"}, "city": {"type": "string"}, "opened_on": {"type": "string"},
         "rent": {"type": "number"}, "lease_end": {"type": "string"}, "escalation_pct": {"type": "number"}, "escalation_on": {"type": "string"},
         "targets": {"type": "object"}, "manager_phone": {"type": "string"}, "net": {"type": "number"}, "gross": {"type": "number"},
         "discount": {"type": "number"}, "gst": {"type": "number"}, "orders": {"type": "integer"}, "day": {"type": "string"},
         "channels": {"type": "object"}, "file_id": {"type": "string"}, "kind": {"type": "string"}, "amount": {"type": "number"},
         "month": {"type": "string"}, "statement_id": {"type": "string"}, "on": {"type": "string"}, "valid_to": {"type": "string"},
         "number": {"type": "string"}, "failed": {"type": "array", "items": {"type": "string"}}, "items": {"type": "array", "items": {"type": "object"}},
         "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "franchise_dekho", "description": (
        "Read franchise work (nothing changes). what=day (yesterday's sales vs last week, licences, royalty due, agreement / lease "
        "dates) | pnl (outlet, month) | compare (month: outlets side by side) | statements (brand) | licences | dates | agreements | "
        "outlets | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "pnl", "compare", "statements", "licences", "dates", "agreements", "outlets", "settings", "rules"]},
         "outlet": {"type": "string"}, "month": {"type": "string"}, "brand": {"type": "string"}},
         "required": ["what"]}},
]
FRANCHISE_LABELS = {"franchise": "Franchise ka kaam kar raha hoon", "franchise_dekho": "Outlets ka hisaab dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..franchise import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.save_settings(t, **{k: a[k] for k in ("company", "state", "tds_applies", "morning_time") if k in a})
        if action == "agreement":
            keys = ("franchisor", "contact", "royalty_pct", "marketing_pct", "tech_fee", "min_guarantee", "base", "foreign", "franchisor_state",
                    "due_day", "start", "term_years", "lock_in_years", "notice_months", "checklist", "notes")
            return S.save_agreement(t, _s(a.get("brand")), **{k: a[k] for k in keys if k in a})
        if action == "outlet":
            return S.save_outlet(t, _s(a.get("name") or a.get("outlet")), _s(a.get("brand")), _s(a.get("city")), _s(a.get("opened_on")), a.get("rent"),
                                 _s(a.get("lease_end")), a.get("escalation_pct"), _s(a.get("escalation_on")), a.get("targets"), _s(a.get("manager_phone")))
        if action == "sale":
            return S.add_sale(t, _s(a.get("outlet")), a.get("net"), _s(a.get("day")), a.get("gross"), a.get("discount"), a.get("gst"), a.get("orders"),
                              a.get("channels"))
        if action == "import":
            return S.import_sales(t, _s(a.get("outlet")), file_id=_s(a.get("file_id")))
        if action == "cost":
            return S.add_cost(t, _s(a.get("outlet")), _s(a.get("kind")) or "other", a.get("amount"), _s(a.get("month")), _s(a.get("note")))
        if action == "statement":
            return S.statement(t, _s(a.get("brand")), _s(a.get("month")), conv)
        if action == "approve_statement":
            if not _owner(ctx):
                raise ToolError("Franchisor ko report bhejne ki haan sirf owner.")
            return S.approve_statement(t, _s(a.get("statement_id")))
        if action == "paid":
            return S.mark_paid(t, _s(a.get("statement_id")), _s(a.get("on")))
        if action == "licence":
            return S.save_licence(t, _s(a.get("outlet")), _s(a.get("kind")) or "other", _s(a.get("valid_to")), _s(a.get("number")), _s(a.get("note")))
        if action == "audit":
            return S.audit(t, _s(a.get("outlet")), a.get("failed"), a.get("items"), _s(a.get("kind")) or "daily", _s(a.get("day")), _s(a.get("note")))
        if action == "pnl_file":
            return S.pnl_file(t, _s(a.get("month")), conv)
    except (S.FrError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..franchise import rules as R
    from ..franchise import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "pnl":
            return S.pnl(t, _s(a.get("outlet")), _s(a.get("month")))
        if what == "compare":
            return S.compare(t, _s(a.get("month")))
        if what == "statements":
            return {"statements": S.statements(t, _s(a.get("brand")))}
        if what == "licences":
            return S.licences(t)
        if what == "dates":
            return {"dates": S.dates_watch(t)}
        if what == "agreements":
            return {"agreements": S.agreements(t)}
        if what == "outlets":
            return {"outlets": S.outlets(t)}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "targets": R.TARGETS, "gst_fee": R.GST_FEE, "tds_royalty": R.TDS_ROYALTY, "tds_rent": R.TDS_RENT,
                    "licences": {k: v[0] for k, v in R.LICENCES.items()}}
    except (S.FrError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def franchise(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def franchise_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


FRANCHISE_HANDLERS = {"franchise": franchise, "franchise_dekho": franchise_dekho}
