"""v0.107 Thok Sahayak tools (wholesale trader). `thok_dekho` only reads; `thok` does the work. A bill is made only on HER
Haan (owner); every message to a party is a draft she sends. Hoola never takes or pays money and never makes the
e-way bill / IRN on the portal itself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

THOK_TOOLS = [
    {"name": "thok", "description": (
        "Wholesale trader's coworker (kirana / FMCG / grain / hardware distributor), end to end. Stock + prices live in her "
        "stock list (same as Hoola Deals). action=settings: firm, gstin, address, phone, bank, terms, aato (turnover), "
        "last_fy_turnover, prefix, credit_days, morning_time. action=party: name or party (to update), kind customer|supplier|"
        "both, phone, gstin, address, credit_limit, credit_days, route (beat day / area), msme, pan_ok, opening (old balance). "
        "action=item: name, price, gst_pct (0/5/18/40), unit, qty, hsn, cost, supplier, lead_days, low_at, tiers [{min, price}]. "
        "action=order: party, text (the retailer's order in her words, e.g. 'atta 10 bori, cheeni 5 bag @ 4200') or lines "
        "[{item, qty, rate}] -> priced draft with stock / credit / e-way bill checks. action=bill: order_id, lines (her changes), "
        "bill_date: ONLY when she says haan -> numbered GST tax invoice PDF + a message draft. action=cancel: order_id, reason. "
        "action=receive: party, amount, mode cash|upi|neft|cheque, on, cheque_no, cheque_date, bank (a customer paid HER). "
        "action=cheque: payment_id, status cleared|bounced, memo_date. action=purchase: supplier, text or lines [{item, qty, "
        "rate, gst_pct}], bill_no, bill_date, agreed_days, paid. action=pay_supplier: supplier, amount, mode, on (she paid). "
        "action=reminders: route (vasooli drafts). action=statement: party (ledger Excel). action=invoice: order_id (PDF again)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "party", "item", "order", "bill", "cancel", "receive", "cheque", "purchase",
                                               "pay_supplier", "reminders", "statement", "invoice"]},
         "firm": {"type": "string"}, "gstin": {"type": "string"}, "address": {"type": "string"}, "phone": {"type": "string"},
         "bank": {"type": "string"}, "terms": {"type": "string"}, "aato": {"type": "number"}, "last_fy_turnover": {"type": "number"},
         "prefix": {"type": "string"}, "credit_days": {"type": "integer"}, "morning_time": {"type": "string"},
         "name": {"type": "string"}, "party": {"type": "string"}, "kind": {"type": "string"}, "credit_limit": {"type": "number"},
         "route": {"type": "string"}, "msme": {"type": "boolean"}, "pan_ok": {"type": "boolean"}, "opening": {"type": "number"},
         "price": {"type": "number"}, "gst_pct": {"type": "number"}, "unit": {"type": "string"}, "qty": {"type": "number"},
         "hsn": {"type": "string"}, "cost": {"type": "number"}, "supplier": {"type": "string"}, "lead_days": {"type": "integer"},
         "low_at": {"type": "number"}, "tiers": {"type": "array", "items": {"type": "object"}}, "text": {"type": "string"},
         "lines": {"type": "array", "items": {"type": "object"}}, "order_id": {"type": "string"}, "bill_date": {"type": "string"},
         "reason": {"type": "string"}, "amount": {"type": "number"}, "mode": {"type": "string"}, "on": {"type": "string"},
         "cheque_no": {"type": "string"}, "cheque_date": {"type": "string"}, "payment_id": {"type": "string"},
         "status": {"type": "string"}, "memo_date": {"type": "string"}, "bill_no": {"type": "string"},
         "agreed_days": {"type": "integer"}, "paid": {"type": "number"}, "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "thok_dekho", "description": (
        "Read wholesale work (nothing changes). what=day (today's sales, collection, cheques to deposit, bounced, MSME dues, "
        "low stock) | route (route: today's beat - collect + visit) | outstanding (route) | party (party: ledger, aging, "
        "days-to-pay) | parties (kind, route) | orders (status draft|billed, party) | order (order_id) | items (q) | payments "
        "(party, status pending|bounced) | payables | reorder | margins (days) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "route", "outstanding", "party", "parties", "orders", "order", "items", "payments",
                                             "payables", "reorder", "margins", "settings", "rules"]},
         "route": {"type": "string"}, "party": {"type": "string"}, "kind": {"type": "string"}, "status": {"type": "string"},
         "order_id": {"type": "string"}, "q": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
THOK_LABELS = {"thok": "Thok vyapar ka kaam kar raha hoon", "thok_dekho": "Khaata-bahi dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..thok import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = "owner" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    try:
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            keys = ("firm", "gstin", "address", "phone", "bank", "terms", "aato", "last_fy_turnover", "prefix", "credit_days", "morning_time")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
        if action == "party":
            return S.save_party(t, _s(a.get("name")), _s(a.get("party")), _s(a.get("kind")), _s(a.get("phone")), _s(a.get("gstin")),
                                _s(a.get("address")), a.get("credit_limit"), a.get("credit_days"), _s(a.get("route")), a.get("msme"),
                                a.get("pan_ok"), a.get("opening"), None, _s(a.get("note")))
        if action == "item":
            return S.save_item(t, _s(a.get("name")), a.get("price"), a.get("gst_pct"), _s(a.get("unit")), a.get("qty"), _s(a.get("hsn")),
                               a.get("cost"), _s(a.get("supplier")), a.get("lead_days"), a.get("low_at"), a.get("tiers"))
        if action == "order":
            return S.take_order(t, _s(a.get("party")), _s(a.get("text")), a.get("lines"), _s(a.get("note")), conv)
        if action == "bill":
            if not _owner(ctx):
                raise ToolError("Bill banane ki haan sirf owner.")
            return S.bill(t, _s(a.get("order_id")), _s(a.get("bill_date")), a.get("lines"), conv, by)
        if action == "cancel":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.cancel_order(t, _s(a.get("order_id")), _s(a.get("reason")))
        if action == "receive":
            return S.receive(t, _s(a.get("party")), a.get("amount"), _s(a.get("mode")) or "cash", _s(a.get("on")), _s(a.get("cheque_no")),
                             _s(a.get("cheque_date")), _s(a.get("bank")), _s(a.get("note")))
        if action == "cheque":
            return S.cheque(t, _s(a.get("payment_id")), _s(a.get("status")), _s(a.get("memo_date")), _s(a.get("reason")))
        if action == "purchase":
            return S.purchase(t, _s(a.get("supplier")), _s(a.get("text")), a.get("lines"), _s(a.get("bill_no")), _s(a.get("bill_date")),
                              a.get("agreed_days"), a.get("paid"))
        if action == "pay_supplier":
            return S.pay_supplier(t, _s(a.get("supplier")), a.get("amount"), _s(a.get("mode")) or "neft", _s(a.get("on")), _s(a.get("note")))
        if action == "reminders":
            return S.reminder_drafts(t, _s(a.get("route")))
        if action == "statement":
            return S.statement_file(t, _s(a.get("party")), conv)
        if action == "invoice":
            return S.invoice_file(t, _s(a.get("order_id")), conv)
    except (S.ThokError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..thok import rules as R
    from ..thok import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "route":
            return S.route_plan(t, _s(a.get("route")))
        if what == "outstanding":
            return S.outstanding(t, _s(a.get("route")))
        if what == "party":
            return S.party_view(t, _s(a.get("party")))
        if what == "parties":
            return {"parties": S.parties(t, _s(a.get("kind")), _s(a.get("route")))}
        if what == "orders":
            return {"orders": S.orders(t, _s(a.get("status")), _s(a.get("party")))}
        if what == "order":
            return S.get_order(t, _s(a.get("order_id")))
        if what == "items":
            return {"items": S.items(t, _s(a.get("q")))}
        if what == "payments":
            return {"payments": S.payments(t, _s(a.get("party")), _s(a.get("status")))}
        if what == "payables":
            return S.payables(t)
        if what == "reorder":
            return S.reorder(t)
        if what == "margins":
            return S.margins(t, int(a.get("days") or 30))
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "gst_slabs": R.GST_SLABS, "eway_inter": R.EWB_INTER, "eway_intra": R.EWB_INTRA,
                    "cash_limit": R.CASH_LIMIT, "tds_purchase": R.TDS_PURCHASE, "msme_days": R.MSME_DAYS}
    except (S.ThokError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def thok(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def thok_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


THOK_HANDLERS = {"thok": thok, "thok_dekho": thok_dekho}
