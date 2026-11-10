"""Retail Trust tool: `retail_trust` (Retail & e-commerce register Wave 3: #52 #55 #57 #58 #59 #67 #100 #102 and pricing fairness). Rule hits and checklists on rows given, with HER thresholds, for the investigator / trust team / grievance officer / moderator. Nothing here bans, removes, refunds, fines or accuses anyone; owner / staff only."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["fraud_flags", "return_abuse", "dark_patterns", "grievance_clock", "reviews", "seller_kyc", "label_check", "promise_audit", "override_rate", "price_fairness"]

RETAILTRUST_TOOLS = [
    {"name": "retail_trust", "description": (
        "Marketplace / store trust and compliance helper (rule hits and checklists on rows given; bans, removes, refunds, fines and accuses NO ONE; a named person decides). action=fraud_flags: orders [{id, customer, ts, amount, address, device, cod}], max_per_customer, window_hours, shared_address_accounts, high_value -> explainable rule hits. return_abuse: customers [{id, orders, returns, refund_value}], min_orders, max_return_rate_pct -> above-threshold list (pattern flag). dark_patterns: flow_text, checks {price_shown_up_front, addons_off_by_default, cancel_as_easy_as_signup, timer_is_real} -> pattern hits and failed checks. grievance_clock: complaints [{id, received, acknowledged, resolved}], today, ack_hours, resolve_days -> late / open (periods from memory, verify). reviews: items [{id, user, text, rating, date, verified, incentivised, disclosed}] -> authenticity signals. seller_kyc: seller {name, gstin, pan, bank_account_name, bank_ifsc, address, category} -> format and GSTIN check-digit checks, missing documents. label_check: label {name, net_quantity, mrp, manufacturer, month_year, consumer_care, country_of_origin} -> missing declarations (verify). promise_audit: deliveries [{id, promised_days, actual_days}] -> on-time % and an honest promise hint. override_rate: decisions [{model, ai_decision, human_decision}] -> override rate per model. price_fairness: quotes [{product, segment, price}], max_spread_pct -> spread between segments."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "orders": {"type": "array", "items": {"type": "object"}}, "max_per_customer": {"type": "number"}, "window_hours": {"type": "number"}, "shared_address_accounts": {"type": "number"}, "high_value": {"type": "number"}, "customers": {"type": "array", "items": {"type": "object"}}, "min_orders": {"type": "number"}, "max_return_rate_pct": {"type": "number"}, "flow_text": {"type": "string"}, "checks": {"type": "object"}, "complaints": {"type": "array", "items": {"type": "object"}}, "today": {"type": "string"}, "ack_hours": {"type": "number"}, "resolve_days": {"type": "number"}, "items": {"type": "array", "items": {"type": "object"}}, "seller": {"type": "object"}, "label": {"type": "object"}, "deliveries": {"type": "array", "items": {"type": "object"}}, "decisions": {"type": "array", "items": {"type": "object"}}, "alert_pct": {"type": "number"}, "quotes": {"type": "array", "items": {"type": "object"}}, "max_spread_pct": {"type": "number"}},
         "required": ["action"]}},
]
RETAILTRUST_LABELS = {"retail_trust": "Retail Trust se jaanch kar raha hoon"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..retailtrust import engines as E
    if action == "fraud_flags":
        return E.fraud_flags(a.get("orders") or [], a.get("max_per_customer", 5), a.get("window_hours", 24), a.get("shared_address_accounts", 3), a.get("high_value"))
    if action == "return_abuse":
        return E.return_abuse(a.get("customers") or [], a.get("min_orders", 5), a.get("max_return_rate_pct", 40))
    if action == "dark_patterns":
        return E.dark_patterns(a.get("flow_text", ""), a.get("checks"))
    if action == "grievance_clock":
        return E.grievance_clock(a.get("complaints") or [], a.get("today"), a.get("ack_hours", 48), a.get("resolve_days", 30))
    if action == "reviews":
        return E.reviews(a.get("items") or [])
    if action == "seller_kyc":
        return E.seller_kyc(a.get("seller") or {})
    if action == "label_check":
        return E.label_check(a.get("label") or {})
    if action == "promise_audit":
        return E.promise_audit(a.get("deliveries") or [])
    if action == "override_rate":
        return E.override_rate(a.get("decisions") or [], a.get("alert_pct", 30))
    if action == "price_fairness":
        return E.price_fairness(a.get("quotes") or [], a.get("max_spread_pct", 5))
    raise ToolError(f"action '{action}' not recognised.")


async def _retail_trust(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This is for the shop owner / team.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


RETAILTRUST_HANDLERS = {"retail_trust": _retail_trust}
