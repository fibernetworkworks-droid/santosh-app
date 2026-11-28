"""Markets & Post-Trade (F10 of docs/FINANCE_GLOBAL_PLAN.md) tool: `markets_desk`. Position and cash reconciliation against a custodian's
file, trade confirmations, settlement fails with penalties, corporate-action entitlements, dividend withholding reclaims, margin calls
after haircuts, best-execution slippage, comparables, settlement instructions, the disclosure calendar. It never places, changes,
cancels, allocates or affirms an order or a trade."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['recon', 'confirm', 'fails', 'corp_action', 'reclaim', 'margin', 'best_ex', 'comps', 'ssi', 'calendar']

MKTDESK_TOOLS = [
    {"name": "markets_desk", "description": (
        "Post-trade and markets work for brokers, asset managers, custodians and listed companies, any country; never places, "
        "cancels or affirms anything; not advice. recon: internal [{account, symbol, qty}] (or internal_csv), custodian [...] "
        "(or custodian_csv), internal_cash / custodian_cash [{account, currency, amount}], tolerance. confirm: trades [{id, "
        "side, symbol, account, qty, price, trade_date, settle_date}], confirms [same], price_tolerance. fails: settlements "
        "[{id, symbol, counterparty, value, intended, settled}], today, penalty_bp_per_day (her market's). corp_action: event "
        "{type split|reverse_split|consolidation|cash_dividend|stock_dividend|bonus|rights, symbol, ratio '2:1' (new for old), "
        "rate, withholding_pct, subscription_price, record_date, cash_in_lieu_price}, positions [{account, symbol, qty, date}]."
        " reclaim: dividends [{date, symbol, country, gross, withheld}], treaty {country: pct}, claim_years {country: years}, "
        "today. margin: requirement, collateral [{symbol, class, value}], haircuts {symbol|class: pct}, due. best_ex: "
        "executions [{id, side, qty, price, benchmark}]. comps: peers [{name, ev, ebitda, revenue, price, eps}], target "
        "{ebitda, revenue, eps}. ssi: instructions [{counterparty, currency, bic, account, iban}]. calendar: period_ends "
        "[dates], rules [{name, days_after}]."),
     "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": _ACTIONS}, "internal": {"type": "array", "items": {"type": "object"}},
         "custodian": {"type": "array", "items": {"type": "object"}}, "internal_csv": {"type": "string"},
         "custodian_csv": {"type": "string"}, "internal_cash": {"type": "array", "items": {"type": "object"}},
         "custodian_cash": {"type": "array", "items": {"type": "object"}}, "tolerance": {"type": "number"},
         "trades": {"type": "array", "items": {"type": "object"}}, "confirms": {"type": "array", "items": {"type": "object"}},
         "price_tolerance": {"type": "number"}, "settlements": {"type": "array", "items": {"type": "object"}},
         "today": {"type": "string"}, "penalty_bp_per_day": {"type": "number"}, "event": {"type": "object"},
         "positions": {"type": "array", "items": {"type": "object"}},
         "dividends": {"type": "array", "items": {"type": "object"}}, "treaty": {"type": "object"},
         "claim_years": {"type": "object"}, "requirement": {"type": "number"},
         "collateral": {"type": "array", "items": {"type": "object"}}, "haircuts": {"type": "object"}, "due": {"type": "string"},
         "executions": {"type": "array", "items": {"type": "object"}}, "peers": {"type": "array", "items": {"type": "object"}},
         "target": {"type": "object"}, "instructions": {"type": "array", "items": {"type": "object"}},
         "period_ends": {"type": "array", "items": {"type": "string"}}, "rules": {"type": "array", "items": {"type": "object"}}},
         "required": ["action"]}},
]
MKTDESK_LABELS = {"markets_desk": "Working on the trades and positions"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import markets as MK
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "markets_desk", action, a, lambda: MK.run(tenant, action, a, actor))


async def _markets_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
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


MKTDESK_HANDLERS = {"markets_desk": _markets_desk}
