"""v0.512.0 const_customer tools (#92 Customer Payment & Demand-letter Manager + #97/#98 Handover / DLP).
`const_customer_dekho` only reads; `const_customer` does the work. Tier A with the card law on top: a
demand letter is DRAFTED as a PDF and marked sent ONLY on the owner's word (actor check, like theka's
bill_status); WhatsApp sending stays with her; the DLP clock is arithmetic, vendor dispatch is recorded
after it happens. Hoola never decides a legal entitlement (interest claims go to the letter, not the ledger)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

CUSTOMER_TOOLS = [
    {"name": "const_customer", "description": (
        "Grahak ke paise + possession desk (builder's customer side). action=demand: project, unit, customer, phone, "
        "milestone (plinth / slab / registration), amount, due, interest_pct (aapke agreement ka clause), note -> DRAFT "
        "demand. action=letter: demand (id) -> the demand-letter PDF (file). action=demand_send: demand (id) - OWNER ONLY, "
        "bhejne ki haan. action=receipt: demand (id) or project+unit, amount, mode neft|rtgs|cheque|upi|loan, day, note. "
        "action=handover: project, unit, customer, items [{item, done, day, note}] (checklist), keys_on, utilities, status "
        "open|ready|handed. action=dlp_open: project, unit, issue, trade, vendor, dlp_months (agreement), possession_on -> "
        "DLP ticket with the window arithmetic. action=dlp_sent: ticket (id) - OWNER ONLY, vendor ko bhejne ka record. "
        "action=dlp_close: ticket (id), day, note. Hoola demand nahi bhejta, vendor ko nahi bhejta, byaaj ka legal faisla "
        "nahi karta - sirf draft + record + hisaab."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["demand", "letter", "demand_send", "receipt", "handover", "dlp_open",
                                               "dlp_sent", "dlp_close"]},
         "project": {"type": "string"}, "unit": {"type": "string"}, "customer": {"type": "string"}, "phone": {"type": "string"},
         "milestone": {"type": "string"}, "amount": {"type": "number"}, "due": {"type": "string"},
         "interest_pct": {"type": "number"}, "note": {"type": "string"}, "demand": {"type": "string"},
         "mode": {"type": "string"}, "day": {"type": "string"}, "items": {"type": "array", "items": {"type": "object"}},
         "keys_on": {"type": "string"}, "utilities": {"type": "string"}, "status": {"type": "string"},
         "issue": {"type": "string"}, "trade": {"type": "string"}, "vendor": {"type": "string"},
         "dlp_months": {"type": "number"}, "possession_on": {"type": "string"}, "ticket": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_customer_dekho", "description": (
        "Read the customer money desk (nothing changes). what=demands (status optional: draft|sent|paid|part) | "
        "handover (project optional) | dlp (open tickets + windows)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["demands", "handover", "dlp"]}, "status": {"type": "string"},
         "project": {"type": "string"}},
         "required": ["what"]}},
]
CUSTOMER_LABELS = {"const_customer": "Grahak ke paise ka kaam kar raha hoon", "const_customer_dekho": "Customer desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import customer as C
    from ..construction.common import guard
    guard(f"{action} customer")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "demand":
            return C.demand(t, _s(a.get("project")), _s(a.get("unit")), _s(a.get("customer")), _s(a.get("phone")),
                            _s(a.get("milestone")), a.get("amount"), _s(a.get("due")), a.get("interest_pct"), _s(a.get("note")))
        if action == "letter":
            from .. import chatfiles
            did = _s(a.get("demand"))
            pdf = C.demand_letter(t, did)
            f = chatfiles.store(t, f"Demand-{did[:8]}.pdf", pdf, "application/pdf")
            return {"file": f, "say": "Demand letter PDF ban gaya. Bhejna aapki haan se (demand_send owner-only)."}
        if action == "demand_send":
            return C.demand_send(t, _s(a.get("demand")), ctx.actor, _s(a.get("day")), conv)
        if action == "receipt":
            return C.receipt(t, _s(a.get("demand")), _s(a.get("project")), _s(a.get("unit")), _s(a.get("customer")),
                             a.get("amount"), _s(a.get("mode")), _s(a.get("day")), _s(a.get("note")))
        if action == "handover":
            return C.handover(t, _s(a.get("project")), _s(a.get("unit")), _s(a.get("customer")), a.get("items"),
                              _s(a.get("status")), _s(a.get("keys_on")), _s(a.get("utilities")), conv)
        if action == "dlp_open":
            return C.dlp_open(t, _s(a.get("project")), _s(a.get("unit")), _s(a.get("issue")), _s(a.get("trade")),
                              _s(a.get("vendor")), a.get("dlp_months"), _s(a.get("possession_on")), _s(a.get("day")),
                              _s(a.get("note")))
        if action == "dlp_sent":
            return C.dlp_sent(t, _s(a.get("ticket")), ctx.actor, _s(a.get("day")))
        if action == "dlp_close":
            return C.dlp_close(t, _s(a.get("ticket")), _s(a.get("day")), _s(a.get("note")))
    except (C.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import customer as C
    t = ctx.tenant_id
    try:
        if what == "demands":
            return {"demands": C.demands(t, _s(a.get("status")))}
        if what == "handover":
            from ..db import session
            from sqlalchemy import select
            from ..construction.models import CHandover
            with session() as s:
                rows = s.scalars(select(CHandover).where(CHandover.tenant_id == t)).all()
            pr = _s(a.get("project"))
            if pr:
                rows = [r for r in rows if pr.lower() in r.project.lower()]
            return {"handover": [{"project": r.project, "unit": r.unit, "customer": r.customer, "status": r.status,
                                  "keys_on": r.keys_on, "utilities": r.utilities} for r in rows]}
        if what == "dlp":
            return {"tickets": C.dlp_list(t, open_only=True)}
    except (C.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def const_customer(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_customer_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


CUSTOMER_HANDLERS = {"const_customer": const_customer, "const_customer_dekho": const_customer_dekho}
