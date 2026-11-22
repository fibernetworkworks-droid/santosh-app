"""Investments & Wealth (F10 of docs/FINANCE_GLOBAL_PLAN.md) tool: `investments_desk`. Capital gains by tax lot in her country's method
(GB share identification + Section 104 pool, US FIFO + wash sales, IN, AU and DE FIFO with holding periods, CA average cost + superficial
losses), statements, the cost of fees, loss-harvest lists, a derivatives reality check, investment-scam signs, retirement drawdown, a
fund's NAV check. It never places an order and never says what to buy or sell."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['lots', 'statement', 'fees', 'harvest', 'derivatives', 'scam', 'retirement', 'nav_check', 'methods']

INVESTDESK_TOOLS = [
    {"name": "investments_desk", "description": (
        "Investments for a person up to a fund administrator, any country; never places an order; not advice. lots: country "
        "GB|US|IN|CA|AU|DE (or method fifo|average|uk_share_id, yours), trades [{date, side buy|sell, qty, price, fees, "
        "symbol}], rule_days -> each disposal's cost, gain, holding period, wash / superficial losses disallowed, what is left;"
        " tax not worked out. statement: holdings [{symbol, qty, price, cost, asset_class}], max_pct. fees: amount, years, "
        "return_pct (hers), fee_pct, platform_pct, entry_pct. harvest: country, today, holdings [{symbol, qty, price, cost}], "
        "recent_buys [{symbol, date}]. derivatives: positions [{type call|put|future, side long|short, strike, premium, price, "
        "qty, multiplier, margin}], results [numbers]. scam: text, firm, country, register [{name}] (pasted from the "
        "regulator's register). retirement: pot, withdraw, return_pct, inflation_pct, years. nav_check: assets [{value}], "
        "liabilities [{value}], units, reported_nav, tolerance_bp. methods: the country table."),
     "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": _ACTIONS}, "country": {"type": "string"}, "method": {"type": "string"},
         "trades": {"type": "array", "items": {"type": "object"}}, "rule_days": {"type": "integer"},
         "holdings": {"type": "array", "items": {"type": "object"}}, "max_pct": {"type": "number"}, "amount": {"type": "number"},
         "years": {"type": "integer"}, "return_pct": {"type": "number"}, "fee_pct": {"type": "number"},
         "platform_pct": {"type": "number"}, "entry_pct": {"type": "number"}, "today": {"type": "string"},
         "recent_buys": {"type": "array", "items": {"type": "object"}},
         "positions": {"type": "array", "items": {"type": "object"}}, "results": {"type": "array", "items": {"type": "number"}},
         "text": {"type": "string"}, "firm": {"type": "string"}, "register": {"type": "array", "items": {"type": "object"}},
         "pot": {"type": "number"}, "withdraw": {"type": "number"}, "inflation_pct": {"type": "number"},
         "assets": {"type": "array", "items": {"type": "object"}}, "liabilities": {"type": "array", "items": {"type": "object"}},
         "units": {"type": "number"}, "reported_nav": {"type": "number"}, "tolerance_bp": {"type": "number"}},
         "required": ["action"]}},
]
INVESTDESK_LABELS = {"investments_desk": "Working on the investments"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import investments as IV
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "investments_desk", action, a, lambda: IV.run(tenant, action, a, actor))


async def _investments_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


INVESTDESK_HANDLERS = {"investments_desk": _investments_desk}
