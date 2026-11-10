"""Vitt Sahayak (finance desk assists, Wave 2) tool: `vitt_sahayak`. Rows she types or pastes in, a calculation / check / draft out.
Nothing is stored, nothing is sent, no money moves, nothing is filed. Every answer names who DECIDES (CA, analyst, MLRO, credit committee).
Register: docs/research/banking_finance_industry/00_INDEX.md  (#11 slice, #34, #60, #87, #88, #103 slice, #110)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["goal", "advance_tax", "tds_reconcile", "ageing", "three_way", "aml_triage", "sanctions", "ratios", "credit_memo"]
_SENSITIVE = {"aml_triage", "sanctions", "credit_memo", "ratios"}  # staff / owner only

FINOPS_TOOLS = [
    {"name": "vitt_sahayak", "description": (
        "Finance desk helper for a business owner, CA, analyst or credit officer (calculations, checks and drafts on rows given; nothing stored, sent, "
        "filed or paid; never decides; every answer names the person who decides). action=goal: target, years, current, inflation, rates {name: pct} -> "
        "monthly SIP per low/mid/high scenario (ASSUMED returns, not promises). advance_tax: liability, fy_start_year, tds -> instalment dates and "
        "amounts (dates from memory, verify). tds_reconcile: books [{party, section, tds}], portal [{party, section, tds}] (26AS / AIS rows), tolerance "
        "-> what matches and what to ask. ageing: invoices [{party, invoice_no, due_date, amount, paid}], as_of -> buckets by party. three_way: pos "
        "[{po, qty, price}], grns [{po, qty}], invoices [{invoice_no, po, qty, price}], qty_tol_pct, price_tol_pct -> match or hold with reasons. "
        "aml_triage: txns [{account, date, amount, type, counterparty}], cash_threshold (HERS) -> alerts with a draft narrative for the analyst "
        "(never files an STR). sanctions: names, watch [{name, list, ref}] (HER list; none built in), threshold -> explainable name-match scores. "
        "ratios: financials {revenue, ebitda, net_profit, interest, debt_service, current_assets, current_liabilities, total_debt, net_worth}. "
        "credit_memo: borrower, financials, purpose, amount, years [{revenue, ebitda, net_profit}], policy {dscr, current_ratio, interest_cover, "
        "debt_to_equity} (HER floors) -> a memo draft with blanks; no score, no approve / decline."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "target": {"type": "number"}, "years": {"type": ["number", "array"]},
         "current": {"type": "number"}, "inflation": {"type": "number"}, "rates": {"type": "object"}, "liability": {"type": "number"},
         "fy_start_year": {"type": "integer"}, "tds": {"type": "number"}, "books": {"type": "array", "items": {"type": "object"}},
         "portal": {"type": "array", "items": {"type": "object"}}, "tolerance": {"type": "number"},
         "invoices": {"type": "array", "items": {"type": "object"}}, "as_of": {"type": "string"},
         "pos": {"type": "array", "items": {"type": "object"}}, "grns": {"type": "array", "items": {"type": "object"}},
         "qty_tol_pct": {"type": "number"}, "price_tol_pct": {"type": "number"}, "txns": {"type": "array", "items": {"type": "object"}},
         "cash_threshold": {"type": "number"}, "names": {"type": "array", "items": {"type": "string"}},
         "watch": {"type": "array", "items": {"type": "object"}}, "threshold": {"type": "number"}, "financials": {"type": "object"},
         "borrower": {"type": "string"}, "purpose": {"type": "string"}, "amount": {"type": "number"}, "policy": {"type": "object"}},
         "required": ["action"]}},
]
FINOPS_LABELS = {"vitt_sahayak": "Vitt Sahayak se hisaab / jaanch kar raha hoon"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..finops import aml, credit, goals, ledger, tax
    if action == "goal":
        return goals.goal(a.get("target"), a.get("years"), a.get("current", 0), a.get("inflation", 6), a.get("rates"))
    if action == "advance_tax":
        return goals.advance_tax(a.get("liability"), a.get("fy_start_year"), a.get("tds", 0))
    if action == "tds_reconcile":
        return tax.tds_reconcile(a.get("books") or [], a.get("portal") or [], a.get("tolerance", 1))
    if action == "ageing":
        return ledger.ageing(a.get("invoices") or [], a.get("as_of"))
    if action == "three_way":
        return ledger.three_way(a.get("pos") or [], a.get("grns") or [], a.get("invoices") or [], a.get("qty_tol_pct", 0), a.get("price_tol_pct", 0))
    if action == "aml_triage":
        return aml.triage(a.get("txns") or [], a.get("cash_threshold", 1000000))
    if action == "sanctions":
        return aml.screen(a.get("names") or [], a.get("watch") or [], a.get("threshold", 0.7))
    if action == "ratios":
        return {"ratios": credit.ratios(a.get("financials") or {})}
    if action == "credit_memo":
        yrs = a.get("years")
        return credit.memo(a.get("borrower", ""), a.get("financials") or {}, a.get("purpose", ""), a.get("amount"),
                           yrs if isinstance(yrs, list) else None, a.get("policy"))
    raise ToolError(f"Unknown action '{action}'.")


async def _vitt_sahayak(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action in _SENSITIVE and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("This is for the owner only.")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


FINOPS_HANDLERS = {"vitt_sahayak": _vitt_sahayak}
