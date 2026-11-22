"""Community & Inclusive Finance (F11 of docs/FINANCE_GLOBAL_PLAN.md) tool: `community_finance`. A spoken micro-business cash book, savings
group books and share-outs, rotating groups and auction chits, microloan true cost and over-borrowing, MFI collection sheets, crop plans
and crop-insurance claims, remittance comparison, mobile-money fees and scam signs, zakat, Islamic business structures. It never
collects, lends or sends money and never gives a religious ruling."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['cashbook', 'group', 'rosca', 'mfi', 'field', 'farmer', 'remit', 'mobile_money', 'zakat', 'islamic', 'styles']

COMMFIN_TOOLS = [
    {"name": "community_finance", "description": (
        "Community, inclusive and Islamic finance, any country; never collects, lends or sends money; Shariah rulings stay with"
        " her scholar or board; not advice. cashbook: text (spoken / typed lines like 'sold tea 250'; a line may start with a "
        "date) or entries [{date, kind in|out, amount, note}], opening. group: country, members [names], share_value (if "
        "savings are counted in shares), opening_cash, meetings [{date, savings {member: shares or amount}, fines {member: "
        "amount}, social_fund {member: amount}, social_payouts [{member, amount}], repayments [{member, amount}], expenses "
        "[{what, amount}], loans [{member, amount, rate_pct (the group's own, per month), months}], counted (the cash the group"
        " counted)}], share_out true. rosca: members (in payout order), contribution, bids (auction chit: the winning discount "
        "each round), organiser_fee_pct, written_record, organiser_known, registered, promised_return_pct. mfi: amount, "
        "installment, installments, frequency weekly|fortnightly|monthly, upfront_fees; loans [{lender, installment, "
        "frequency}], income_monthly, max_share_pct. field: collections [{member, due, paid}], portfolio [{outstanding, "
        "days_late}]. farmer: area, costs [{what, amount}], yield_per_unit, price; threshold_yield, actual_yield, sum_insured. "
        "remit: send, mid_rate, providers [{name, fee, fee_pct, rate}]. mobile_money: amount, tariff [{min, max, fee}], "
        "message. zakat: nisab_basis gold|silver, gold_price_per_gram, silver_price_per_gram, cash, bank, gold [{grams, karat, "
        "jewellery}], silver_grams, school hanafi|shafii|maliki|hanbali, jewellery_zakatable, business_stock, receivables, "
        "shares_trading, shares_longterm, shares_longterm_pct, debts_due, lunar_year_passed. islamic: structure murabaha (cost,"
        " markup_pct, installments) | ijara (cost, rent, periods) | diminishing_musharaka (price, own_contribution, "
        "rent_pct_per_period, buyback_per_period) | mudaraba (profit, manager_share_pct). styles: group traditions by country."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "text": {"type": "string"},
         "entries": {"type": "array", "items": {"type": "object"}}, "opening": {"type": "number"}, "date": {"type": "string"},
         "country": {"type": "string"}, "members": {"type": "array", "items": {"type": "string"}},
         "share_value": {"type": "number"}, "opening_cash": {"type": "number"}, "opening_social": {"type": "number"},
         "meetings": {"type": "array", "items": {"type": "object"}}, "share_out": {"type": "boolean"},
         "contribution": {"type": "number"}, "bids": {"type": "array", "items": {"type": "number"}},
         "organiser_fee_pct": {"type": "number"}, "written_record": {"type": "boolean"}, "organiser_known": {"type": "boolean"},
         "registered": {"type": "boolean"}, "promised_return_pct": {"type": "number"}, "amount": {"type": "number"},
         "installment": {"type": "number"}, "installments": {"type": "integer"}, "frequency": {"type": "string"},
         "upfront_fees": {"type": "number"}, "loans": {"type": "array", "items": {"type": "object"}},
         "income_monthly": {"type": "number"}, "max_share_pct": {"type": "number"},
         "collections": {"type": "array", "items": {"type": "object"}},
         "portfolio": {"type": "array", "items": {"type": "object"}}, "area": {"type": "number"},
         "costs": {"type": "array", "items": {"type": "object"}}, "yield_per_unit": {"type": "number"},
         "price": {"type": "number"}, "threshold_yield": {"type": "number"}, "actual_yield": {"type": "number"},
         "sum_insured": {"type": "number"}, "send": {"type": "number"}, "mid_rate": {"type": "number"},
         "providers": {"type": "array", "items": {"type": "object"}}, "tariff": {"type": "array", "items": {"type": "object"}},
         "message": {"type": "string"}, "nisab_basis": {"type": "string"}, "gold_price_per_gram": {"type": "number"},
         "silver_price_per_gram": {"type": "number"}, "cash": {"type": "number"}, "bank": {"type": "number"},
         "gold": {"type": "array", "items": {"type": "object"}}, "silver_grams": {"type": "number"},
         "school": {"type": "string"}, "jewellery_zakatable": {"type": "boolean"}, "business_stock": {"type": "number"},
         "receivables": {"type": "number"}, "shares_trading": {"type": "number"}, "shares_longterm": {"type": "number"},
         "shares_longterm_pct": {"type": "number"}, "debts_due": {"type": "number"}, "lunar_year_passed": {"type": "boolean"},
         "structure": {"type": "string"}, "cost": {"type": "number"}, "markup_pct": {"type": "number"},
         "rent": {"type": "number"}, "periods": {"type": "integer"}, "own_contribution": {"type": "number"},
         "rent_pct_per_period": {"type": "number"}, "buyback_per_period": {"type": "number"}, "profit": {"type": "number"},
         "manager_share_pct": {"type": "number"}},
         "required": ["action"]}},
]
COMMFIN_LABELS = {"community_finance": "Working on the group and community money"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import community as CM
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "community_finance", action, a, lambda: CM.run(tenant, action, a, actor))


async def _community_finance(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
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


COMMFIN_HANDLERS = {"community_finance": _community_finance}
