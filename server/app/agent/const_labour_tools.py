"""v0.512.0 const_labour tools (#85 Labour Compliance Desk + #87 Wage & Payment Auditor + #90 BOCW Cess
& TDS). `const_labour_dekho` only reads; `const_labour` does the work. Tier A: muster, licence renewals,
her wage rates WITH their source, the wage-audit working paper, and the DETERMINED cess / TDS arithmetic
from the state pack (a stale pack refuses, never a guessed rate). Money never moves: wage_paid records a
payment AFTER she made it; the compliance calendar reminds - Hoola files nothing."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

LABOUR_TOOLS = [
    {"name": "const_labour", "description": (
        "Labour compliance + wages desk (labour law, wages, BOCW cess). action=muster: site, day, contractor, "
        "trade, present, absent, ot_hours, wage_basis day|hour|piece, note - the daily muster roll row. action=licence: "
        "kind contract_labour|bocw|epf|esic|other, number, authority, holder, site, valid_from, valid_to, status, note - "
        "renewal calendar. action=wage_rate: trade, rate, basis, site, wef, source (WHERE the number came from - agreement / "
        "notification / your word), note. action=wage_audit: site, day, trade, workers, ot_hours, advances, deductions "
        "-> the working paper (gross - advance - deductions = to pay; with the source of the rate). action=wage_paid: site, day, "
        "trade, amount, workers, note - record AFTER the payment is made. action=cess_tds: base (construction cost / "
        "contract payment), state (default maharashtra), individual, pan_ok -> BOCW cess + Sec 393(1) TDS, determined "
        "arithmetic only. Hoola does not send money; filing a licence / return is the compliance officer's job."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["muster", "licence", "wage_rate", "wage_audit", "wage_paid", "cess_tds"]},
         "site": {"type": "string"}, "day": {"type": "string"}, "contractor": {"type": "string"}, "trade": {"type": "string"},
         "present": {"type": "integer"}, "absent": {"type": "integer"}, "ot_hours": {"type": "number"},
         "wage_basis": {"type": "string"}, "note": {"type": "string"}, "kind": {"type": "string"}, "number": {"type": "string"},
         "authority": {"type": "string"}, "holder": {"type": "string"}, "valid_from": {"type": "string"},
         "valid_to": {"type": "string"}, "status": {"type": "string"}, "rate": {"type": "number"}, "basis": {"type": "string"},
         "wef": {"type": "string"}, "source": {"type": "string"}, "workers": {"type": "integer"}, "advances": {"type": "number"},
         "deductions": {"type": "number"}, "amount": {"type": "number"}, "base": {"type": "number"},
         "state": {"type": "string"}, "individual": {"type": "boolean"}, "pan_ok": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "const_labour_dekho", "description": (
        "Read the labour desk (nothing changes). what=day (licences expiring in 30 days, unpaid muster rows) | "
        "licences (all) | rates (her wage rates with sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "licences", "rates"]}},
         "required": ["what"]}},
]
LABOUR_LABELS = {"const_labour": "Checking labour accounts and rules", "const_labour_dekho": "Viewing the labour desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import labour as L
    from ..construction.common import guard
    guard(f"{action} labour")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "muster":
            return L.muster(t, _s(a.get("site")), _s(a.get("day")), _s(a.get("contractor")), _s(a.get("trade")),
                            a.get("present"), a.get("absent"), a.get("ot_hours"), _s(a.get("wage_basis")),
                            _s(a.get("note")), conv)
        if action == "licence":
            return L.licence(t, _s(a.get("kind")), _s(a.get("number")), _s(a.get("authority")), _s(a.get("holder")),
                             _s(a.get("site")), _s(a.get("valid_from")), _s(a.get("valid_to")), _s(a.get("status")),
                             _s(a.get("note")))
        if action == "wage_rate":
            return L.wage_rate(t, _s(a.get("trade")), a.get("rate"), _s(a.get("basis")), _s(a.get("site")),
                               _s(a.get("wef")), _s(a.get("source")), _s(a.get("note")))
        if action == "wage_audit":
            return L.wage_audit(t, _s(a.get("site")), _s(a.get("day")), _s(a.get("trade")), a.get("workers"),
                                a.get("ot_hours"), a.get("advances"), a.get("deductions"))
        if action == "wage_paid":
            return L.wage_paid(t, _s(a.get("site")), _s(a.get("day")), _s(a.get("trade")), a.get("amount"),
                               a.get("workers"), _s(a.get("note")))
        if action == "cess_tds":
            return L.cess_tds(t, a.get("base"), _s(a.get("state")) or "maharashtra", bool(a.get("individual")),
                              bool(a.get("pan_ok", True)))
    except (L.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import labour as L
    t = ctx.tenant_id
    try:
        if what == "day":
            return L.day(t)
        if what == "licences":
            return {"licences": L.licences(t)}
        if what == "rates":
            from ..db import session
            from sqlalchemy import select
            from ..construction.models import CLabourWage
            with session() as s:
                rows = s.scalars(select(CLabourWage).where(CLabourWage.tenant_id == t)).all()
            return {"rates": [{"trade": r.trade, "rate": r.rate, "basis": r.basis, "site": r.site, "wef": r.wef,
                               "source": r.source} for r in rows]}
    except (L.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown what")


async def const_labour(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_labour_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


LABOUR_HANDLERS = {"const_labour": const_labour, "const_labour_dekho": const_labour_dekho}
