"""Tax worldwide (F4 of docs/FINANCE_GLOBAL_PLAN.md) tool: `tax_worldwide`. VAT / GST return worksheets from her own books laid out like
her country's form, US sales tax per state, cross-border consumer sales, withholding, e-invoice files (UBL / Peppol), the personal
return organiser, sole-trader quarterly figures, tax letters and her tax calendar. It never files: she or her tax agent files.
In India the portal work (GSTR-1 / 3B, e-invoice numbers) stays with GST & Accounts (bahi)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "return", "sales_tax", "nexus", "oss", "withholding", "einvoice", "organiser", "quarterly", "notice", "calendar",
            "add_date", "codes"]
_CHANGES = {"settings", "add_date", "notice"}

TAXWIDE_TOOLS = [
    {"name": "tax_worldwide", "description": (
        "Tax worksheets for any country from her own books (workspace = her finance workspace); never files, never pays; not tax advice. "
        "settings: country, scheme vat|gst|sales_tax|none, rates {std, reduced, zero ...: her %}, state_rates {CA: 7.25} (US), oss_rates "
        "{FR: 20}, nexus {CA: 500000}, home_state (India GST state), period_kind monthly|quarterly|yearly, quarter_ends [3,6,9,12], "
        "due_offset_days, seller {name, tax_id, street, city, postcode, country}. Her invoice lines carry tax_code std|reduced|zero|exempt|"
        "export|eu_goods|rc_out|rc_in|oss|outside and the invoice supply {country, state, b2b, buyer_tax_id}. return: period YYYY-Qn | "
        "YYYY-MM -> the VAT / GST return in her country's layout (GB 9 boxes, DE UStVA, AU BAS, SG F5, IN GSTR-3B, others general) with "
        "warnings. sales_tax: period -> US per state. nexus: as_of -> 12-month sales per state. oss: period -> consumer sales per "
        "destination country. withholding: payments [{payee, gross, rate_pct, rate_source, certificate}], currency. einvoice: doc -> UBL / "
        "Peppol XML + problems + her country's model. organiser: workspace or rows, year (tax year ending), bands [{upto, pct}], allowance, "
        "extra_income [{kind, amount}] -> income by kind, papers, an estimate only on her bands. quarterly: period -> sole-trader figures "
        "for the quarter and the year so far. notice: text (the tax letter) -> authority, reference, amount, dates, a reply draft; the "
        "reply-by date goes into her calendar. calendar: year. add_date: title, due. codes: what each tax code means."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"}, "country": {"type": "string"},
         "scheme": {"type": "string"}, "rates": {"type": "object"}, "state_rates": {"type": "object"}, "oss_rates": {"type": "object"},
         "nexus": {"type": "object"}, "home_state": {"type": "string"}, "period_kind": {"type": "string"},
         "quarter_ends": {"type": "array", "items": {"type": "integer"}}, "due_offset_days": {"type": "integer"},
         "seller": {"type": "object"}, "period": {"type": "string"}, "since": {"type": "string"}, "upto": {"type": "string"},
         "as_of": {"type": "string"}, "payments": {"type": "array", "items": {"type": "object"}}, "currency": {"type": "string"},
         "doc": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object"}}, "year": {"type": "integer"},
         "bands": {"type": "array", "items": {"type": "object"}}, "allowance": {"type": "number"},
         "extra_income": {"type": "array", "items": {"type": "object"}}, "text": {"type": "string"}, "title": {"type": "string"},
         "due": {"type": "string"}},
         "required": ["action"]}},
]
TAXWIDE_LABELS = {"tax_worldwide": "Working out the tax figures"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import tax as TX
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "tax_worldwide", action, a, lambda: TX.run(tenant, action, a, actor))


async def _tax_worldwide(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action in _CHANGES and actor != "owner" and not actor.startswith("approved:"):
        raise ToolError("Changing her tax settings or calendar is for the owner or someone she approved.")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


TAXWIDE_HANDLERS = {"tax_worldwide": _tax_worldwide}
