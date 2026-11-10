"""Dukaan Desk tool: `dukaan_desk` (Retail & e-commerce register Wave 1: #1 #2 #7 #10 #32 #36 #38 #78 #79 #81 #86 #90). Calculations, checks and drafts on rows
the owner gives. Nothing is stored, sent, published or paid; no price, discount, refund, order or listing is changed; every answer names who decides."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["day_summary", "forecast", "reorder", "margin", "licences", "oversell", "rto_risk", "reconcile", "claims", "landed", "shop_scam", "gst_split"]
_SHOPPER = {"landed", "shop_scam"}          # the only two a customer actor may run (they work for the buyer)

RETAILDESK_TOOLS = [
    {"name": "dukaan_desk", "description": (
        "Shop and online-seller helper (calculations, checks and drafts on rows given; nothing stored, sent, published or paid; changes no price, order, refund or "
        "listing; every answer names who decides). action=day_summary: sales [{time, amount, mode cash|upi|credit, item}] -> total, mode split, best hour, top "
        "items, credit given. forecast: weekly_sales [..>=4], weeks, festival_boost {week_ahead: multiplier} -> estimates with a range note. reorder: items [{name, "
        "stock, daily_sales, lead_days, cost, last_sold, expiry}], today, cover_days -> reorder quantities (formula shown), fast/slow, expiring, dead stock and cash "
        "stuck. margin: items [{name, cost, selling, mrp}] -> margin %, selling above MRP, below cost. licences: items [{name, expiry}], today -> renewals + GST "
        "dates (verify). oversell: channels [{channel, stock, open_orders}], safety_stock -> sellable now / OVERSELL. rto_risk: orders [{id, address, pincode, "
        "phone, cod, amount, prior_rto}] -> risk level with reasons. reconcile: sales [{ref, amount}], settlements [{ref, amount, fee}] -> matched / to check. "
        "claims: text, spec {brand, mrp, hsn, ...} -> risky claim words + missing listing facts. landed: offers [{seller, price, shipping, cod_fee, coupon_off, "
        "return_days}] -> true total. shop_scam: url, price, market_price, text -> warning signals. gst_split: lines [{name, qty, price, gst_pct, hsn}], "
        "seller_state, buyer_state, price_includes_gst -> CGST/SGST or IGST. Heuristic outputs are labelled; GST dates are from memory (verify)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "sales": {"type": "array", "items": {"type": "object"}},
         "weekly_sales": {"type": "array", "items": {"type": "number"}}, "weeks": {"type": "integer"}, "festival_boost": {"type": "object"},
         "items": {"type": "array", "items": {"type": "object"}}, "today": {"type": "string"}, "cover_days": {"type": "number"},
         "expiry_days": {"type": "number"}, "dead_days": {"type": "number"}, "warn_days": {"type": "number"},
         "channels": {"type": "array", "items": {"type": "object"}}, "safety_stock": {"type": "number"},
         "orders": {"type": "array", "items": {"type": "object"}}, "settlements": {"type": "array", "items": {"type": "object"}},
         "tolerance": {"type": "number"}, "text": {"type": "string"}, "spec": {"type": "object"},
         "offers": {"type": "array", "items": {"type": "object"}}, "url": {"type": "string"}, "price": {"type": "number"},
         "market_price": {"type": "number"}, "lines": {"type": "array", "items": {"type": "object"}},
         "seller_state": {"type": "string"}, "buyer_state": {"type": "string"}, "price_includes_gst": {"type": "boolean"}},
         "required": ["action"]}},
]
RETAILDESK_LABELS = {"dukaan_desk": "Dukaan Desk se hisaab / jaanch kar raha hoon"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..retaildesk import online, shop
    if action == "day_summary":
        return shop.day_summary(a.get("sales") or [])
    if action == "forecast":
        return shop.forecast(a.get("weekly_sales") or [], int(a.get("weeks") or 4), a.get("festival_boost"))
    if action == "reorder":
        return shop.reorder(a.get("items") or [], a.get("today"), a.get("cover_days", 7), a.get("expiry_days", 30), a.get("dead_days", 45))
    if action == "margin":
        return shop.margin(a.get("items") or [])
    if action == "licences":
        return shop.licences(a.get("items") or [], a.get("today"), a.get("warn_days", 45))
    if action == "oversell":
        return shop.oversell(a.get("channels") or [], a.get("safety_stock", 0))
    if action == "rto_risk":
        return online.rto_risk(a.get("orders") or [])
    if action == "reconcile":
        return online.reconcile(a.get("sales") or [], a.get("settlements") or [], a.get("tolerance", 1))
    if action == "claims":
        return online.claims(a.get("text", ""), a.get("spec"))
    if action == "landed":
        return online.landed(a.get("offers") or [])
    if action == "shop_scam":
        return online.shop_scam(a.get("url", ""), a.get("price"), a.get("market_price"), a.get("text", ""))
    if action == "gst_split":
        return online.gst_split(a.get("lines") or [], a.get("seller_state", ""), a.get("buyer_state", ""), a.get("price_includes_gst", True) is not False)
    raise ToolError(f"action '{action}' not recognised.")


async def _dukaan_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if actor.startswith("customer:") and action not in _SHOPPER:
        raise ToolError("This is for the shop owner.")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


RETAILDESK_HANDLERS = {"dukaan_desk": _dukaan_desk}
