"""Cash & Treasury (F5 of docs/FINANCE_GLOBAL_PLAN.md) tool: `cash_treasury`. Her 13-week and 30 / 60 / 90-day cash forecast from her
open invoices, bills, payroll and what repeats in her statements; the forecast model checked on months she already lived; spare cash
after her buffer; bank charges; foreign-currency exposure at her rates; her loan covenants. It moves no money and names no product."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "forecast", "backtest", "idle", "fees", "fx", "covenants"]
_CHANGES = {"settings"}

TREASURY_TOOLS = [
    {"name": "cash_treasury", "description": (
        "Cash & treasury from her own records (workspace = her finance workspace); moves no money, names no product; not advice. "
        "settings: min_cash, lag_days (how late customers pay), weeks_buffer, exclude [statement words], covenants [{name, kind "
        "min_cash|max_ratio|min_ratio, numerator, denominator, limit}]. forecast: start, weeks (13), opening (else her statements), "
        "items [{date, amount (- = out), label}] -> weekly in / out / closing, the lowest week, weeks under her minimum, 30/60/90 days, "
        "overdue invoices. backtest: window (3), hold_out (3) -> each held-out month predicted only from earlier months vs what "
        "happened. idle: spare cash after her buffer across the forecast. fees: since, upto -> bank charges by kind and month. "
        "fx: rates {EUR: book per unit}, move_pct -> exposure per currency and the effect of a move. covenants: figures {cash, "
        "net_debt, ebitda ...} -> each covenant ok or breached with headroom."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"}, "min_cash": {"type": "number"},
         "lag_days": {"type": "integer"}, "weeks_buffer": {"type": "integer"}, "exclude": {"type": "array", "items": {"type": "string"}},
         "covenants": {"type": "array", "items": {"type": "object"}}, "start": {"type": "string"}, "weeks": {"type": "integer"},
         "opening": {"type": "number"}, "items": {"type": "array", "items": {"type": "object"}}, "window": {"type": "integer"},
         "hold_out": {"type": "integer"}, "since": {"type": "string"}, "upto": {"type": "string"}, "rates": {"type": "object"},
         "move_pct": {"type": "number"}, "figures": {"type": "object"}},
         "required": ["action"]}},
]
TREASURY_LABELS = {"cash_treasury": "Working out the cash forecast"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import cash as CS
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "cash_treasury", action, a, lambda: CS.run(tenant, action, a, actor))


async def _cash_treasury(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action in _CHANGES and actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Changing the cash settings is for the owner or someone she approved.")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


TREASURY_HANDLERS = {"cash_treasury": _cash_treasury}
