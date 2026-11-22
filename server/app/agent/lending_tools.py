"""Credit & Lending (F6 of docs/FINANCE_GLOBAL_PLAN.md) tool: `credit_lending`. Both sides of a loan, any country. Borrower: the APR by
the country's method, offers compared, invoice finance costed, a business-loan readiness pack. Lender: statement analysis, a credit
memo with every figure traced to its source, her policy's rule hits, a key-facts draft, conditions, servicing, collections contacts
checked against the contact rules before they are made, early warnings, ECL. It never approves, declines or pays out a loan."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["apr", "shop", "invoice_finance", "readiness", "analyse", "memo", "rules", "kfs", "conditions", "servicing",
            "contact_rules", "collect", "ews", "ecl", "methods"]
_CHANGES = {"contact_rules", "collect"}
_LENDER = {"analyse", "memo", "rules", "kfs", "conditions", "servicing", "contact_rules", "collect", "ews", "ecl"}

LENDING_TOOLS = [
    {"name": "credit_lending", "description": (
        "Credit and lending, both sides, any country; never approves, declines or pays out a loan; not advice. "
        "BORROWER: apr: country (GB DE IE US IN AU CA SG AE SA) or method eu_annual|us_actuarial|nominal_irr|effective_irr, amount, "
        "rate (annual %), term (payments), frequency monthly|fortnightly|weekly, payment, fees_upfront, fee_pct, fees_deducted, balloon, "
        "or payments [{period | date, amount}] + start -> APR, money received, total paid. shop: offers [{name, amount, rate, term, "
        "fee_pct ...}], country. invoice_finance: invoice, advance_pct, fee, fee_pct, discount_rate_pct, days. readiness: workspace -> "
        "her statements + books as a lender pack, gaps. LENDER: analyse: rows [{id, date, narration, amount}] (or workspace), opening -> "
        "money in / out by month, regular debts, returned items, each figure traced to rows. memo: borrower, amount, purpose, figures "
        "{name: {value, source}} (a figure needs its source), rows, policy {dscr: 1.25, debt_to_income: 50 ...} -> memo with [S#] "
        "sources and ratios. rules: applicant, rules [{field, op, value, code, severity}]. kfs: lender, borrower, product, amount, "
        "rate, term, fee_pct, country. conditions: items [{name, status received|missing|waived, waived_by, due}]. servicing: amount, "
        "rate, term, start, paid [{date, amount}]. contact_rules: workspace, contact_rules {from_hour, to_hour, per_day, per_week, "
        "no_days, channels, source} (only stricter than Hoola's floor). collect: workspace, borrower, when (their local time), tz, "
        "channel, to (borrower), message, legal_stage -> refused if it breaks a rule, else logged as planned (never sent). ews: "
        "dpd_history, rows, covenants_breached. ecl: exposures [{id, ead, pd, lgd, dpd | stage}]. methods: the APR methods."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"}, "country": {"type": "string"},
         "method": {"type": "string"}, "amount": {"type": "number"}, "rate": {"type": "number"}, "term": {"type": "integer"},
         "frequency": {"type": "string"}, "payment": {"type": "number"}, "fees_upfront": {"type": "number"},
         "fee_pct": {"type": "number"}, "fees_deducted": {"type": "boolean"}, "balloon": {"type": "number"},
         "payments": {"type": "array", "items": {"type": "object"}}, "start": {"type": "string"},
         "offers": {"type": "array", "items": {"type": "object"}}, "invoice": {"type": "number"}, "advance_pct": {"type": "number"},
         "fee": {"type": "number"}, "discount_rate_pct": {"type": "number"}, "days": {"type": "number"},
         "rows": {"type": "array", "items": {"type": "object"}}, "opening": {"type": "number"}, "since": {"type": "string"},
         "upto": {"type": "string"}, "borrower": {"type": "string"}, "purpose": {"type": "string"}, "figures": {"type": "object"},
         "policy": {"type": "object"}, "applicant": {"type": "object"}, "rules": {"type": "array", "items": {"type": "object"}},
         "lender": {"type": "string"}, "product": {"type": "string"}, "items": {"type": "array", "items": {"type": "object"}},
         "paid": {"type": "array", "items": {"type": "object"}}, "today": {"type": "string"}, "contact_rules": {"type": "object"},
         "when": {"type": "string"}, "tz": {"type": "string"}, "channel": {"type": "string"}, "to": {"type": "string"},
         "message": {"type": "string"}, "legal_stage": {"type": "boolean"}, "dpd_history": {"type": "array", "items": {"type": "integer"}},
         "covenants_breached": {"type": "array", "items": {"type": "string"}}, "exposures": {"type": "array", "items": {"type": "object"}}},
         "required": ["action"]}},
]
LENDING_LABELS = {"credit_lending": "Working out the loan figures"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import credit as CR
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "credit_lending", action, a, lambda: CR.run(tenant, action, a, actor))


async def _credit_lending(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if actor.startswith("customer:") and action in _LENDER:
        raise ToolError("The lender's work is not for customers.")
    if action in _CHANGES and actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Collections work is for the owner or someone she approved.")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


LENDING_HANDLERS = {"credit_lending": _credit_lending}
