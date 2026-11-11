"""Risk Desk tool: `risk_desk` (Banking & Finance register Wave 3: #32 #36 #39 #51 #65/#75 #66 #76 #92 #112). Prepared papers and checks on rows she gives,
with limits / rules / rates she supplies. Nothing is stored, sent, filed or PLACED: an order is only ever a ticket (it goes through the broker's own
official API on her explicit tap, elsewhere); a loan is never decided; an alert never blocks anyone. Owner only. Never a buy / sell view."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["order_ticket", "portfolio", "underwrite", "kfs", "dpd", "ecl", "dcf", "velocity", "round_trips"]

RISKDESK_TOOLS = [
    {"name": "risk_desk", "description": (
        "Markets and credit desk helper for an owner, investor, credit officer or analyst (prepares papers and checks on rows given; places NO order, "
        "decides NO loan, blocks NOTHING; stores and sends nothing; never says what to buy or sell; every answer names who decides). action=order_ticket: "
        "symbol, side buy|sell, qty, order_type market|limit|stoploss, price, ltp, product, portfolio_value, holding_qty, rates {brokerage_pct, "
        "brokerage_cap, other_pct}, max_pct_of_portfolio, max_price_deviation_pct -> a prepared ticket with flags and the confirm line; it is NOT sent "
        "(only her explicit tap through the broker's official connector can place it). portfolio: holdings [{symbol, qty, price, group}], targets "
        "{name: pct}, tolerance_pct, max_single_pct, max_group_pct, margin {used, available}, margin_alert_pct -> weights, drift, breaches of HER limits, "
        "rebalance PROPOSALS for the manager. underwrite: applicant {income_monthly, obligations_monthly, requested_emi, ...}, rules [{field, op, value, "
        "code, severity}] (HER policy; rules on religion / caste / gender / locality are refused) -> rule hits, reason codes, exceptions; no decision. "
        "kfs: lender, borrower, product, amount, rate, months, fee_pct, fee_fixed, insurance, other_upfront, cooling_off_days, grievance -> a key fact "
        "statement draft with blanks. dpd: accounts [{id, outstanding, oldest_due_date}], as_of, npa_days -> SMA bands and an NPA suggestion (verify). "
        "ecl: exposures [{id, ead, pd, lgd, dpd|stage, pd_lifetime}] -> ECL working paper. dcf: cashflows [..], discount_pct, terminal_growth_pct, "
        "net_debt, shares -> value + sensitivity grid (a model of HER assumptions). velocity: txns [{account, ts, amount, device}], window_minutes, "
        "max_count, max_amount -> rule hits for a fraud analyst. round_trips: trades [{client, symbol, side, qty, price, ts}] -> pattern flags for "
        "compliance (evidence, not accusation)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "symbol": {"type": "string"}, "side": {"type": "string"}, "qty": {"type": "number"},
         "order_type": {"type": "string"}, "price": {"type": "number"}, "ltp": {"type": "number"}, "product": {"type": "string"},
         "portfolio_value": {"type": "number"}, "holding_qty": {"type": "number"}, "rates": {"type": "object"},
         "max_pct_of_portfolio": {"type": "number"}, "max_price_deviation_pct": {"type": "number"},
         "holdings": {"type": "array", "items": {"type": "object"}}, "targets": {"type": "object"}, "tolerance_pct": {"type": "number"},
         "max_single_pct": {"type": "number"}, "max_group_pct": {"type": "number"}, "margin": {"type": "object"}, "margin_alert_pct": {"type": "number"},
         "applicant": {"type": "object"}, "rules": {"type": "array", "items": {"type": "object"}}, "lender": {"type": "string"},
         "borrower": {"type": "string"}, "amount": {"type": "number"}, "rate": {"type": "number"}, "months": {"type": "integer"},
         "fee_pct": {"type": "number"}, "fee_fixed": {"type": "number"}, "insurance": {"type": "number"}, "other_upfront": {"type": "number"},
         "cooling_off_days": {"type": "integer"}, "grievance": {"type": "string"}, "accounts": {"type": "array", "items": {"type": "object"}},
         "as_of": {"type": "string"}, "npa_days": {"type": "integer"}, "exposures": {"type": "array", "items": {"type": "object"}},
         "cashflows": {"type": "array", "items": {"type": "number"}}, "discount_pct": {"type": "number"},
         "terminal_growth_pct": {"type": "number"}, "net_debt": {"type": "number"}, "shares": {"type": "number"},
         "txns": {"type": "array", "items": {"type": "object"}}, "window_minutes": {"type": "number"}, "max_count": {"type": "integer"},
         "max_amount": {"type": "number"}, "trades": {"type": "array", "items": {"type": "object"}}, "product_name": {"type": "string"}},
         "required": ["action"]}},
]
RISKDESK_LABELS = {"risk_desk": "Preparing Risk Desk slips and checks"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..riskdesk import credit, orders, valuation, watch
    if action == "order_ticket":
        return orders.ticket(a.get("symbol"), a.get("side"), a.get("qty"), a.get("order_type", "limit"), a.get("price"), a.get("ltp"), a.get("product", "delivery"),
                             a.get("portfolio_value"), a.get("holding_qty"), a.get("rates"), a.get("max_pct_of_portfolio", 10), a.get("max_price_deviation_pct", 5))
    if action == "portfolio":
        return orders.drift(a.get("holdings") or [], a.get("targets"), a.get("tolerance_pct", 5), a.get("max_single_pct"), a.get("max_group_pct"),
                            a.get("margin"), a.get("margin_alert_pct", 80))
    if action == "underwrite":
        return credit.underwrite(a.get("applicant") or {}, a.get("rules") or [])
    if action == "kfs":
        return credit.kfs(a.get("lender", ""), a.get("borrower", ""), a.get("product_name", ""), a.get("amount"), a.get("rate"), a.get("months"),
                          a.get("fee_pct", 0), a.get("fee_fixed", 0), a.get("insurance", 0), a.get("other_upfront", 0), a.get("cooling_off_days"), a.get("grievance", ""))
    if action == "dpd":
        return credit.dpd(a.get("accounts") or [], a.get("as_of"), a.get("npa_days", 90))
    if action == "ecl":
        return credit.ecl(a.get("exposures") or [])
    if action == "dcf":
        return valuation.dcf(a.get("cashflows") or [], a.get("discount_pct"), a.get("terminal_growth_pct"), a.get("net_debt", 0), a.get("shares"))
    if action == "velocity":
        return watch.velocity(a.get("txns") or [], a.get("window_minutes", 10), a.get("max_count", 5), a.get("max_amount"))
    if action == "round_trips":
        return watch.wash(a.get("trades") or [])
    raise ToolError(f"action '{action}' not recognised.")


async def _risk_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Risk Desk is for the owner only.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


RISKDESK_HANDLERS = {"risk_desk": _risk_desk}
