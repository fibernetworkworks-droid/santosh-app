"""Public sector (F12 of docs/FINANCE_GLOBAL_PLAN.md) tool: `public_finance`. Benefit checks against the scheme's own rules,
overpayments, G2P payment runs reconciled, deposit-insurance cover for a failed bank, banks' returns against supervisory
thresholds, inspection findings, development-project tranches and spending. It never pays, awards, refuses or takes a supervisory
action: a named official decides."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['benefits', 'overpayment', 'g2p', 'deposit_cover', 'supervisor', 'inspection', 'dev_finance']

PUBFIN_TOOLS = [
    {"name": "public_finance", "description": (
        "Public-sector finance for benefit offices, payment agencies, deposit insurers, supervisors and development teams, any "
        "country; never pays, awards, refuses or acts; a named official decides; not advice. benefits: household {field: "
        "value}, schemes [{name, source (required), tests [{field, op >=|<=|>|<|==|!=, value}], amount {base, per_field, "
        "per_value, max}, evidence [..]}], evidence_held [..]. overpayment: due [{period, amount}], paid [{period, amount}]. "
        "g2p: beneficiaries [{id, amount, account}], payments [{id, ref, amount, account}], bank_return [{ref, status "
        "success|failed}]. deposit_cover: limit (her scheme's), accounts [{number, holders [ids], balance, interest, type}], "
        "loans [{depositor, due}], set_off_loans, depositors [{id, name, dob}]. supervisor: thresholds {car_min, lcr_min, "
        "npl_max, large_exposure_max}, returns [{bank, capital, rwa, liquid_assets, net_outflows, npl, loans, "
        "largest_exposure}], previous [...], outlier_mad. inspection: findings [{id, area, owner, due, status}], earlier [{id, "
        "area}], today. dev_finance: tranches [{name, amount, conditions, released}], conditions_met, budget [{line, amount}], "
        "spending [{id, line, amount, category}], eligible_categories, indicators [{name, target, actual}]."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "household": {"type": "object"},
         "schemes": {"type": "array", "items": {"type": "object"}},
         "evidence_held": {"type": "array", "items": {"type": "string"}}, "due": {"type": "array", "items": {"type": "object"}},
         "paid": {"type": "array", "items": {"type": "object"}}, "beneficiaries": {"type": "array", "items": {"type": "object"}},
         "payments": {"type": "array", "items": {"type": "object"}},
         "bank_return": {"type": "array", "items": {"type": "object"}}, "limit": {"type": "number"},
         "accounts": {"type": "array", "items": {"type": "object"}}, "loans": {"type": "array", "items": {"type": "object"}},
         "set_off_loans": {"type": "boolean"}, "joint_rule": {"type": "string"},
         "depositors": {"type": "array", "items": {"type": "object"}}, "thresholds": {"type": "object"},
         "returns": {"type": "array", "items": {"type": "object"}}, "previous": {"type": "array", "items": {"type": "object"}},
         "outlier_mad": {"type": "number"}, "findings": {"type": "array", "items": {"type": "object"}},
         "earlier": {"type": "array", "items": {"type": "object"}}, "today": {"type": "string"},
         "tranches": {"type": "array", "items": {"type": "object"}},
         "conditions_met": {"type": "array", "items": {"type": "string"}},
         "budget": {"type": "array", "items": {"type": "object"}}, "spending": {"type": "array", "items": {"type": "object"}},
         "eligible_categories": {"type": "array", "items": {"type": "string"}},
         "indicators": {"type": "array", "items": {"type": "object"}}},
         "required": ["action"]}},
]
PUBFIN_LABELS = {"public_finance": "Working on the public money"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import public as PB
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "public_finance", action, a, lambda: PB.run(tenant, action, a, actor))


async def _public_finance(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
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


PUBFIN_HANDLERS = {"public_finance": _public_finance}
