"""Payments (F8 of docs/FINANCE_GLOBAL_PLAN.md) tool: `payments_desk`. For a shop up to a payment firm, any country. Merchant:
chargeback representment packs by network reason code (Visa compelling evidence worked out), dispute prevention, multi-gateway
reconciliation (orders, settlements, bank deposits), fee audit against her contract, dunning plans, marketplace payouts, export
proceeds. Payment firm: KYB with beneficial owners through the ownership chain, merchant risk, safeguarding, ISO 20022 message
checks, exceptions by age, licensing-return figures. It never submits a response, charges a card or pays anyone."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["dispute", "prevention", "reconcile", "fee_audit", "dunning", "payouts", "export", "kyb", "merchant_risk", "safeguarding",
            "iso20022", "exceptions", "returns", "reasons"]

PAYDESK_TOOLS = [
    {"name": "payments_desk", "description": (
        "Payments for merchants and payment firms, any country; never submits, charges or pays; not advice. "
        "dispute: network visa|mastercard|amex, reason_code (e.g. 10.4, 13.1, 4837, 4855, F29, C08), evidence {proof_of_delivery, "
        "delivery_address_match, signature, avs_cvv_match, three_ds, prior_transactions, customer_communication, description, "
        "terms_accepted, usage_logs, refund_issued, two_separate_sales, authorization, cancellation_policy: true}, amount, currency, "
        "transaction_id, transaction_date, received, window_days (her processor's), and for Visa 10.4 dispute_date, disputed {ip, "
        "device, shipping, account}, prior [{date, ip, device, shipping, account, disputed}] -> evidence split, verdict, deadline, "
        "the letter. prevention: sales [{month, network, count}], disputes [{month, network, count}], thresholds {visa: 0.9}. "
        "reconcile: orders [{id, gateway, amount}], settlements [{gateway, payout_id, payout_date, lines [{order_id, type "
        "sale|refund|chargeback|fee|adjustment, amount}]}], deposits [{id, date, amount, narration}], window_days. fee_audit: contract "
        "{gateway: {pct, fixed}}, transactions [{id, gateway, amount, fee}]. dunning: failed [{customer, amount, plan, date, reason}], "
        "retry_days. payouts: commission_pct, orders [{seller, amount, type sale|refund, fee}]. export: invoices [{id, date, amount, "
        "currency}], receipts [{invoice, amount}], realise_within_days. kyb: business, ownership [{owned, owner, pct, person}], "
        "threshold_pct, documents. merchant_risk: merchants [{name, mcc, monthly_volume, refund_pct, dispute_pct}], high_risk_mcc, "
        "max_refund_pct, max_dispute_pct. safeguarding: days [{date, owed_to_customers, safeguarded}]. iso20022: xml. exceptions: "
        "items [{id, kind, amount, date}]. returns: transactions [{date, type, amount}], period month|quarter. reasons: the codes."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "network": {"type": "string"}, "reason_code": {"type": "string"},
         "evidence": {"type": "object"}, "amount": {"type": "number"}, "currency": {"type": "string"},
         "transaction_id": {"type": "string"}, "transaction_date": {"type": "string"}, "received": {"type": "string"},
         "window_days": {"type": "integer"}, "dispute_date": {"type": "string"}, "disputed": {"type": "object"},
         "prior": {"type": "array", "items": {"type": "object"}}, "sales": {"type": "array", "items": {"type": "object"}},
         "disputes": {"type": "array", "items": {"type": "object"}}, "thresholds": {"type": "object"},
         "orders": {"type": "array", "items": {"type": "object"}}, "settlements": {"type": "array", "items": {"type": "object"}},
         "deposits": {"type": "array", "items": {"type": "object"}}, "contract": {"type": "object"},
         "transactions": {"type": "array", "items": {"type": "object"}}, "failed": {"type": "array", "items": {"type": "object"}},
         "retry_days": {"type": "array", "items": {"type": "integer"}}, "commission_pct": {"type": "number"},
         "invoices": {"type": "array", "items": {"type": "object"}}, "receipts": {"type": "array", "items": {"type": "object"}},
         "realise_within_days": {"type": "integer"}, "today": {"type": "string"}, "business": {"type": "string"},
         "ownership": {"type": "array", "items": {"type": "object"}}, "threshold_pct": {"type": "number"},
         "documents": {"type": "array", "items": {"type": "string"}}, "required_documents": {"type": "array", "items": {"type": "string"}},
         "merchants": {"type": "array", "items": {"type": "object"}}, "high_risk_mcc": {"type": "array", "items": {"type": "string"}},
         "max_refund_pct": {"type": "number"}, "max_dispute_pct": {"type": "number"}, "spike_pct": {"type": "number"},
         "days": {"type": "array", "items": {"type": "object"}}, "xml": {"type": "string"}, "items": {"type": "array", "items": {"type": "object"}},
         "period": {"type": "string"}},
         "required": ["action"]}},
]
PAYDESK_LABELS = {"payments_desk": "Working on the payments"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import payments as PM
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "payments_desk", action, a, lambda: PM.run(tenant, action, a, actor))


async def _payments_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
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


PAYDESK_HANDLERS = {"payments_desk": _payments_desk}
