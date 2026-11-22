"""Household Money (F2 of docs/FINANCE_GLOBAL_PLAN.md) tool: `household_money`. A personal finance helper for people and sole traders in
any country: arithmetic on HER statements and numbers, country help at the level its rules have. Nothing is paid, filed or sent; no PIN,
OTP, CVV, card number or password is ever asked for or kept. It explains and calculates; she decides."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["budget", "bills", "forecast", "categorise", "save_rules", "goal", "net_worth", "forgotten", "retirement", "benefits",
            "life_mode", "bereavement", "will_check"]

HOUSEHOLD_TOOLS = [
    {"name": "household_money", "description": (
        "Household money helper for any country (calculations on her own statements and numbers; never pays, files or sends; not "
        "financial / tax / legal advice; never asks for a PIN, OTP, CVV, card number or password). Her transactions come from workspace "
        "(statements she imported into her finance workspace) or rows [{day, amount, narration}] with currency. "
        "budget: workspace or rows, limits {category: amount}, rules {word: category} -> money in / out by month and category, over budget. "
        "bills: workspace or rows -> bills, subscriptions and regular income found from her history with the next due date and price rises "
        "(paying a bill = Hoola Wallet, her tap). forecast: workspace or rows, months_ahead, start_balance -> the next months in / out and a "
        "low-balance warning. categorise: workspace or rows, rules -> each line's category. save_rules: workspace, rules {word: category} -> "
        "kept for next time. goal: target, by (YYYY-MM-DD), saved, return_pct (her assumption) -> how much a month. net_worth: items "
        "[{name, kind asset|liability, amount, currency}], currency, fx [{currency, rate, date, source}] -> net worth (a currency without a "
        "dated rate is left out and named). forgotten: country, workspace -> official places to find lost money + her accounts quiet for a "
        "year. retirement: country, years, pot, monthly, want_monthly, real_return_pct -> pot and income in today's money at her assumption "
        "or 2 / 4 / 6%; the state pension is never added until confirmed. benefits: country -> the official checkers. life_mode: country, mode "
        "student|renter|expat|gig|family -> a checklist. bereavement: country, workspace -> steps, who to tell (from the statements), a "
        "letter she sends. will_check: country, accounts [{name, nominee}] or workspace -> accounts with no nominee recorded. Country "
        "services are shown as 'not confirmed - check this' until Hoola has read the official page."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"},
         "rows": {"type": "array", "items": {"type": "object"}}, "currency": {"type": "string"}, "country": {"type": "string"},
         "limits": {"type": "object"}, "rules": {"type": "object"}, "months_ahead": {"type": "integer"},
         "start_balance": {"type": "number"}, "target": {"type": "number"}, "by": {"type": "string"}, "saved": {"type": "number"},
         "return_pct": {"type": "number"}, "items": {"type": "array", "items": {"type": "object"}},
         "fx": {"type": "array", "items": {"type": "object"}}, "years": {"type": "integer"}, "pot": {"type": "number"},
         "monthly": {"type": "number"}, "want_monthly": {"type": "number"}, "real_return_pct": {"type": "number"},
         "mode": {"type": "string"}, "accounts": {"type": "array", "items": {"type": "object"}}},
         "required": ["action"]}},
]
HOUSEHOLD_LABELS = {"household_money": "Working out household money"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import household as HH
    tenant = getattr(ctx, "tenant_id", "") or "default"
    return core.run_tool(tenant, getattr(ctx, "actor", "owner") or "owner", "household_money", action, a, lambda: HH.run(tenant, action, a))


async def _household_money(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Household money is for the owner only.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


HOUSEHOLD_HANDLERS = {"household_money": _household_money}
