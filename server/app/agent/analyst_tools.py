"""v0.95 Financial Analyst tools. `paisa_dekho` only reads; `paisa` changes things. Sharing a report outside and
sending payment reminders wait for HER Haan. Hoola never moves money, invests or applies for loans; its numbers are
analysis, not financial advice."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

ANALYST_TOOLS = [
    {"name": "paisa", "description": (
        "Financial analyst for her business. "
        "action=books: file_id (Tally trial balance / P&L / balance sheet export, Excel or CSV), label (e.g. 'Sep 2026', "
        "'FY 2025-26'), start, end -> P&L, balance sheet, ratios vs bank benchmarks, trend vs last period, what stands out. "
        "action=figures: label, start, end, figures {revenue, purchases, direct_exp, indirect_exp, depreciation, interest, "
        "opening_stock, closing_stock, debtors, creditors, cash, bank, bank_od, secured_loans, unsecured_loans, capital, "
        "reserves, fixed_assets, duties, other_ca, other_income}: numbers read from a P&L / balance sheet photo or PDF. "
        "action=map_ledger: ledger, category, snapshot (her correction, remembered). "
        "action=bank: file_id (bank statement Excel / CSV), account -> money in / out, burn, runway, 13-week forecast. "
        "action=category: pattern (narration words) or txn_id, category (remembered). "
        "action=bill: kind receivable|payable, party, amount, bill, bill_date, credit_days, phone, msme (payable to a "
        "micro / small enterprise), agreed_days (written agreement, max 45). action=bills_file: kind, file_id (outstanding "
        "list). action=bill_paid: item_id, amount. action=loan: name, outstanding, rate, emi, months_left. "
        "action=loan_check: amount, rate, years, projected_turnover. action=advance_tax: profit (optional). "
        "action=report: snapshot -> MIS Excel + 1-page PDF. action=share: snapshot, approve, to: ONLY when she herself "
        "says the report may go to the bank / CA / investor. action=reminders (drafts to customers who owe; send only "
        "after her haan). action=settings: business, entity individual|firm|llp|company, budget {category: monthly "
        "amount}, tax_paid (advance tax paid this year), morning_time."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["books", "figures", "map_ledger", "bank", "category", "bill", "bills_file", "bill_paid",
                                               "loan", "loan_check", "advance_tax", "report", "share", "reminders", "settings"]},
         "file_id": {"type": "string"}, "label": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "figures": {"type": "object"}, "ledger": {"type": "string"}, "category": {"type": "string"}, "snapshot": {"type": "string"},
         "account": {"type": "string"}, "pattern": {"type": "string"}, "txn_id": {"type": "string"}, "kind": {"type": "string"},
         "party": {"type": "string"}, "amount": {"type": "number"}, "bill": {"type": "string"}, "bill_date": {"type": "string"},
         "credit_days": {"type": "integer"}, "phone": {"type": "string"}, "msme": {"type": "boolean"}, "agreed_days": {"type": "integer"},
         "item_id": {"type": "string"}, "name": {"type": "string"}, "outstanding": {"type": "number"}, "rate": {"type": "number"},
         "emi": {"type": "number"}, "months_left": {"type": "integer"}, "years": {"type": "number"}, "projected_turnover": {"type": "number"},
         "profit": {"type": "number"}, "approve": {"type": "boolean"}, "to": {"type": "string"}, "business": {"type": "string"},
         "entity": {"type": "string"}, "budget": {"type": "object"}, "tax_paid": {"type": "number"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "paisa_dekho", "description": (
        "Read the business's money picture (nothing changes). what=analysis (snapshot: latest if empty) | periods | cash | "
        "transactions (category) | receivables | payables (MSME 15 / 45-day risk + interest) | alerts | settings | emi "
        "(amount, rate, years)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["analysis", "periods", "cash", "transactions", "receivables", "payables", "alerts", "settings", "emi"]},
         "snapshot": {"type": "string"}, "category": {"type": "string"}, "amount": {"type": "number"}, "rate": {"type": "number"},
         "years": {"type": "number"}},
         "required": ["what"]}},
]
ANALYST_LABELS = {"paisa": "Hisaab-kitaab dekh raha hoon", "paisa_dekho": "Business ka paisa dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..analyst import service as F
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "books":
            return F.import_books(t, _s(a.get("label")), _s(a.get("start")), _s(a.get("end")), _s(a.get("file_id")))
        if action == "figures":
            return F.set_figures(t, _s(a.get("label")), _s(a.get("start")), _s(a.get("end")), a.get("figures") or {})
        if action == "map_ledger":
            return F.map_ledger(t, _s(a.get("ledger")), _s(a.get("category")), _s(a.get("snapshot")))
        if action == "bank":
            return F.import_bank(t, _s(a.get("file_id")), account=_s(a.get("account")))
        if action == "category":
            return F.set_category(t, _s(a.get("pattern")), _s(a.get("category")), _s(a.get("txn_id")))
        if action == "bill":
            return F.add_item(t, _s(a.get("kind")) or "receivable", _s(a.get("party")), a.get("amount"), _s(a.get("bill")),
                              _s(a.get("bill_date")), a.get("credit_days"), _s(a.get("phone")), bool(a.get("msme")), a.get("agreed_days"))
        if action == "bills_file":
            return F.import_items(t, _s(a.get("kind")) or "receivable", _s(a.get("file_id")))
        if action == "bill_paid":
            return F.item_paid(t, _s(a.get("item_id")), a.get("amount"))
        if action == "loan":
            return F.add_loan(t, _s(a.get("name")), a.get("outstanding"), a.get("rate"), a.get("emi"), a.get("months_left"))
        if action == "loan_check":
            return F.loan_check(t, a.get("amount"), a.get("rate") or 10, float(a.get("years") or 5), a.get("projected_turnover"), _s(a.get("snapshot")))
        if action == "advance_tax":
            return F.advance_tax(t, a.get("profit"), _s(a.get("snapshot")))
        if action == "report":
            return F.report(t, _s(a.get("snapshot")), conv)
        if action == "share":
            if not _owner(ctx):
                raise ToolError("Report bahar bhejne ki haan sirf owner.")
            return F.approve_share(t, _s(a.get("snapshot")), bool(a.get("approve")), _s(a.get("to")))
        if action == "reminders":
            return F.reminder_drafts(t)
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Settings sirf owner.")
            keys = ("business", "entity", "budget", "tax_paid", "morning_time")
            return {"settings": F.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
    except (F.FinError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..analyst import rules as R
    from ..analyst import service as F
    t = ctx.tenant_id
    try:
        if what == "analysis":
            return F.analyse(t, _s(a.get("snapshot")))
        if what == "periods":
            return {"periods": F.snapshots(t)}
        if what == "cash":
            return F.cash(t)
        if what == "transactions":
            return {"transactions": F.txns(t, _s(a.get("category")), 100)}
        if what == "receivables":
            return F.aging(t, "receivable")
        if what == "payables":
            return F.aging(t, "payable")
        if what == "alerts":
            return F.alerts(t)
        if what == "settings":
            return F.settings(t)
        if what == "emi":
            return {"emi": R.emi(float(a.get("amount") or 0), float(a.get("rate") or 0), int(float(a.get("years") or 0) * 12))}
    except (F.FinError, ValueError) as e:
        raise ToolError(str(e))
    raise ToolError("what galat")


async def paisa(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def paisa_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


ANALYST_HANDLERS = {"paisa": paisa, "paisa_dekho": paisa_dekho}
