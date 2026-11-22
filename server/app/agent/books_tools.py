"""Books & Accounts (F3 of docs/FINANCE_GLOBAL_PLAN.md) tool: `books_accounts`. Double-entry books for a sole trader, a business, a firm's
client or an institution in any country, on the finance workspace. It posts, matches, reconciles, depreciates and closes on her confirm;
it never sends an invoice, pays a bill or files anything. In India GST returns stay with GST & Accounts (bahi)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["chart", "add_account", "journal", "invoice", "bill", "issue", "documents", "receipt", "matches", "apply_match", "post_bank",
            "reconcile", "ageing", "asset", "depreciation", "inventory", "revalue", "reports", "close_check", "close_lock", "export"]
_READS = {"chart", "documents", "matches", "reconcile", "ageing", "inventory", "reports", "close_check", "export"}

BOOKS_TOOLS = [
    {"name": "books_accounts", "description": (
        "Double-entry books on her finance workspace (workspace = its id), any country, amounts in that currency; never sends an invoice, "
        "pays, or files; not tax / legal advice. chart: the chart of accounts. add_account: code, name, type asset|liability|equity|income|"
        "expense. journal: day, memo, lines [{code, debit | credit}] (must balance; a locked month refuses it). invoice / bill: party, issue, "
        "due, currency, lines [{description, qty, price, tax_pct (her rate)}], code (income / expense account), a foreign currency needs "
        "rate, rate_date, rate_source; issue_now=true posts it. issue: doc -> numbered once and posted. documents: kind sales|purchase, "
        "status draft|open|paid. receipt: text (the receipt's words) -> a draft bill. matches: bank lines against open invoices and bills "
        "with the reason and confidence; unsure lines list the choices. apply_match: txn, doc (her confirm; exchange difference to the FX "
        "account). post_bank: txn, code (a line with no document). reconcile: period YYYY-MM, statement_balance -> matched, bank only, "
        "books only, difference. ageing: kind receivables|payables, as_of. asset: name, cost, start YYYY-MM, life_months or method reducing "
        "+ rate_pct, salvage. depreciation: period. inventory: movements [{day, qty (+in/-out), unit_cost}], method fifo|average. revalue: "
        "period, rates [{currency, rate, date, source}]. reports: since, upto -> trial balance, profit and loss, balance sheet. close_check: "
        "period -> the month-end checklist and its hash. close_lock: period, hash (her confirm of that checklist), exceptions (why, if items "
        "are not done). export: format csv|xero|quickbooks|tally, since, upto -> an import file."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"}, "code": {"type": "string"},
         "name": {"type": "string"}, "type": {"type": "string"}, "day": {"type": "string"}, "memo": {"type": "string"},
         "lines": {"type": "array", "items": {"type": "object"}}, "party": {"type": "string"}, "issue": {"type": "string"},
         "due": {"type": "string"}, "currency": {"type": "string"}, "rate": {"type": "number"}, "rate_date": {"type": "string"},
         "rate_source": {"type": "string"}, "issue_now": {"type": "boolean"}, "doc": {"type": "string"}, "kind": {"type": "string"},
         "status": {"type": "string"}, "text": {"type": "string"}, "txn": {"type": "string"}, "account": {"type": "string"},
         "period": {"type": "string"}, "statement_balance": {"type": "number"}, "as_of": {"type": "string"}, "cost": {"type": "number"},
         "start": {"type": "string"}, "life_months": {"type": "integer"}, "method": {"type": "string"}, "rate_pct": {"type": "number"},
         "salvage": {"type": "number"}, "movements": {"type": "array", "items": {"type": "object"}},
         "rates": {"type": "array", "items": {"type": "object"}}, "since": {"type": "string"}, "upto": {"type": "string"},
         "hash": {"type": "string"}, "exceptions": {"type": "string"}, "format": {"type": "string"}},
         "required": ["action"]}},
]
BOOKS_LABELS = {"books_accounts": "Working on the books"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import books as BK
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "books_accounts", action, a, lambda: BK.run(tenant, action, a, actor))


async def _books_accounts(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action not in _READS and actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Changing the books is for the owner or someone she approved.")
    if action == "close_lock" and actor != "owner":
        raise ToolError("Only the owner locks a month.")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


BOOKS_HANDLERS = {"books_accounts": _books_accounts}
