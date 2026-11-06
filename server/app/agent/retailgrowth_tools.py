"""Retail Growth tool: `retail_growth` (Retail & e-commerce register Wave 2: #6 #11 #15 #21 #28 #35 #46 #69 #70 #71 #80). Proposals and checks on rows the owner gives, with HER rules and floors. Nothing is stored, sent or changed; a price, scheme, credit limit or route is the owner's / manager's decision."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["loyalty", "markdown", "unit_economics", "abc", "price_rule", "scheme", "credit_exposure", "beat_route", "working_capital", "delivery_batches"]

RETAILGROWTH_TOOLS = [
    {"name": "retail_growth", "description": (
        "Shop and seller growth helper (proposals and checks on rows given; stores, sends and changes nothing; the owner decides). action=loyalty: customers [{id, last_visit, spend, birthday MM-DD, opted_in}], today, lapsed_days -> lapsed / birthday lists for opted-in customers only. markdown: items [{name, stock, cost, price, mrp, expiry, floor_margin_pct}], today, steps [[days_left, pct]] -> proposed prices inside HER floor and MRP, waste at risk. unit_economics: cac, orders, aov, cogs_pct, ship_cost, return_rate_pct, return_cost, repeat_orders -> contribution, LTV/CAC. abc: items [{sku, sales, margin}] -> A/B/C and range-review candidates. price_rule: items [{name, cost, price, mrp, competitor_prices, floor_margin_pct, target}], max_change_pct -> proposed price within floor and MRP (competitor prices only as given). scheme: scheme_def {min_qty, per_unit, percent, cap}, sales, claims -> accrual and disputes. credit_exposure: retailers [{retailer, outstanding, oldest_days, limit, avg_monthly_purchase}], limit_multiple -> utilisation and flags. beat_route: start {lat, lng}, stops [{name, lat, lng}] -> straight-line visit order. working_capital: inventory, cogs_annual, receivables, sales_annual, payables -> cash cycle. delivery_batches: orders [{id, area, amount}], free_above, flat_fee -> area batches."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "customers": {"type": "array", "items": {"type": "object"}}, "today": {"type": "string"}, "lapsed_days": {"type": "number"}, "items": {"type": "array", "items": {"type": "object"}}, "steps": {"type": "array", "items": {"type": "object"}}, "cac": {"type": "number"}, "orders_n": {"type": "number"}, "aov": {"type": "number"}, "cogs_pct": {"type": "number"}, "ship_cost": {"type": "number"}, "return_rate_pct": {"type": "number"}, "return_cost": {"type": "number"}, "repeat_orders": {"type": "number"}, "max_change_pct": {"type": "number"}, "scheme_def": {"type": "object"}, "sales": {"type": "array", "items": {"type": "object"}}, "claims": {"type": "array", "items": {"type": "object"}}, "retailers": {"type": "array", "items": {"type": "object"}}, "limit_multiple": {"type": "number"}, "start": {"type": "object"}, "stops": {"type": "array", "items": {"type": "object"}}, "inventory": {"type": "number"}, "cogs_annual": {"type": "number"}, "receivables": {"type": "number"}, "sales_annual": {"type": "number"}, "payables": {"type": "number"}, "orders": {"type": "array", "items": {"type": "object"}}, "free_above": {"type": "number"}, "flat_fee": {"type": "number"}, "a_pct": {"type": "number"}, "b_pct": {"type": "number"}},
         "required": ["action"]}},
]
RETAILGROWTH_LABELS = {"retail_growth": "Retail Growth se hisaab / prastaav bana raha hoon"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..retailgrowth import engines as E
    if action == "loyalty":
        return E.loyalty(a.get("customers") or [], a.get("today"), a.get("lapsed_days", 60))
    if action == "markdown":
        return E.markdown(a.get("items") or [], a.get("today"), a.get("steps"))
    if action == "unit_economics":
        return E.unit_economics(a.get("cac"), a.get("orders_n"), a.get("aov"), a.get("cogs_pct"), a.get("ship_cost", 0), a.get("return_rate_pct", 0), a.get("return_cost", 0), a.get("repeat_orders", 1))
    if action == "abc":
        return E.abc(a.get("items") or [], a.get("a_pct", 70), a.get("b_pct", 90))
    if action == "price_rule":
        return E.price_rule(a.get("items") or [], a.get("max_change_pct", 10))
    if action == "scheme":
        return E.scheme(a.get("scheme_def") or {}, a.get("sales") or [], a.get("claims"))
    if action == "credit_exposure":
        return E.credit_exposure(a.get("retailers") or [], a.get("limit_multiple", 1.5))
    if action == "beat_route":
        return E.beat_route(a.get("start") or {}, a.get("stops") or [])
    if action == "working_capital":
        return E.working_capital(a.get("inventory"), a.get("cogs_annual"), a.get("receivables"), a.get("sales_annual"), a.get("payables"))
    if action == "delivery_batches":
        return E.delivery_batches(a.get("orders") or [], a.get("free_above", 0), a.get("flat_fee", 0))
    raise ToolError(f"action '{action}' nahi pehchana.")


async def _retail_growth(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Yeh dukaan ke malik / team ke liye hai.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


RETAILGROWTH_HANDLERS = {"retail_growth": _retail_growth}
