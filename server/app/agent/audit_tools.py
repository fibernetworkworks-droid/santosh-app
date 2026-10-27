"""v0.96 Auditor's Assistant tools. `audit_dekho` only reads; `audit` changes things. Sending queries / confirmations
waits for HER Haan. Hoola never signs, never gives the final opinion, never generates a UDIN and never files audit forms."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

AUDIT_TOOLS = [
    {"name": "audit", "description": (
        "Auditor's assistant (for a CA / audit firm): does the audit leg-work end to end; the CA judges and signs. "
        "action=start: client, kind statutory|tax|internal|stock|bank|other, fy (e.g. 2025-26), entity private|public|firm|"
        "individual|llp, approval_limit (client's own approval limit). action=tb: engagement, file_id, previous (true for "
        "last year's TB) -> materiality planned. action=daybook: engagement, file_id (Tally day book / ledger export). "
        "action=facts: engagement + turnover, cash_receipts_pct, cash_payments_pct, profession, paid_up, holding_or_sub, "
        "status. action=materiality: engagement, benchmark pbt|revenue|assets|equity|expenses, pct, risk high|normal|low. "
        "action=run: engagement -> analytics vs last year, journal-entry tests, cash rules (Sec 34(3) / 221 / 219-220), TDS "
        "(Sec 393), Benford, going concern, tax audit + CARO applicability. action=close: finding_id, status explained|"
        "adjusted|reported|asked, note, remember (don't raise this pattern again for the client). action=sample: engagement, "
        "population (ledger / sales / purchases / payment / empty), method mus|random, size, confidence. action=sample_result: "
        "sample_id, status ok|exception, note. action=confirmations: engagement, top, min_amount (drafts). action=approve_"
        "confirmations: engagement, approve: ONLY when she says they may go. action=confirmation_reply: confirm_id, amount, "
        "note. action=queries (client query list draft). action=asked: engagement (ONLY after she sent the list). "
        "action=rep_letter. action=workpapers (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["start", "tb", "daybook", "facts", "materiality", "run", "close", "sample", "sample_result",
                                               "confirmations", "approve_confirmations", "confirmation_reply", "queries", "asked",
                                               "rep_letter", "workpapers"]},
         "engagement": {"type": "string"}, "client": {"type": "string"}, "kind": {"type": "string"}, "fy": {"type": "string"},
         "entity": {"type": "string"}, "approval_limit": {"type": "number"}, "file_id": {"type": "string"}, "previous": {"type": "boolean"},
         "turnover": {"type": "number"}, "cash_receipts_pct": {"type": "number"}, "cash_payments_pct": {"type": "number"},
         "profession": {"type": "boolean"}, "paid_up": {"type": "number"}, "holding_or_sub": {"type": "boolean"}, "status": {"type": "string"},
         "benchmark": {"type": "string"}, "pct": {"type": "number"}, "risk": {"type": "string"}, "finding_id": {"type": "string"},
         "note": {"type": "string"}, "remember": {"type": "boolean"}, "population": {"type": "string"}, "method": {"type": "string"},
         "size": {"type": "integer"}, "confidence": {"type": "integer"}, "sample_id": {"type": "string"}, "top": {"type": "integer"},
         "min_amount": {"type": "number"}, "approve": {"type": "boolean"}, "confirm_id": {"type": "string"}, "amount": {"type": "number"}},
         "required": ["action"]}},
    {"name": "audit_dekho", "description": (
        "Read audit work (nothing changes). what=engagements | engagement (engagement) | findings (engagement, status) | "
        "samples (engagement) | confirmations (engagement: letters) | status (all open audits) | tax_audit (kind business|"
        "profession, turnover, cash_receipts_pct, cash_payments_pct, fy) | caro (company private|public, paid_up_reserves, "
        "borrowings, revenue)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["engagements", "engagement", "findings", "samples", "confirmations", "status", "tax_audit", "caro"]},
         "engagement": {"type": "string"}, "status": {"type": "string"}, "kind": {"type": "string"}, "turnover": {"type": "number"},
         "cash_receipts_pct": {"type": "number"}, "cash_payments_pct": {"type": "number"}, "fy": {"type": "string"},
         "company": {"type": "string"}, "paid_up_reserves": {"type": "number"}, "borrowings": {"type": "number"}, "revenue": {"type": "number"}},
         "required": ["what"]}},
]
AUDIT_LABELS = {"audit": "Audit ka kaam kar raha hoon", "audit_dekho": "Audit file dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..audit import service as A
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = "owner" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    e = _s(a.get("engagement") or a.get("client"))
    try:
        if action == "start":
            return A.new_engagement(t, _s(a.get("client")), _s(a.get("kind")) or "statutory", _s(a.get("fy")), _s(a.get("entity")) or "firm",
                                    a.get("approval_limit"), by)
        if action == "tb":
            return A.import_tb(t, e, _s(a.get("file_id")), previous=bool(a.get("previous")))
        if action == "daybook":
            return A.import_daybook(t, e, _s(a.get("file_id")))
        if action == "facts":
            keys = ("turnover", "cash_receipts_pct", "cash_payments_pct", "profession", "paid_up", "holding_or_sub", "status", "approval_limit")
            return A.set_facts(t, e, **{k: a[k] for k in keys if k in a})
        if action == "materiality":
            out = A.plan_materiality(t, e, _s(a.get("benchmark")), a.get("pct"), _s(a.get("risk")) or "normal")
            return out
        if action == "run":
            return A.run_tests(t, e, conv)
        if action == "close":
            return A.close_finding(t, _s(a.get("finding_id")), _s(a.get("status")), _s(a.get("note")), bool(a.get("remember")), by)
        if action == "sample":
            return A.make_sample(t, e, _s(a.get("population")), _s(a.get("method")) or "mus", int(a.get("size") or 25), int(a.get("confidence") or 95))
        if action == "sample_result":
            return A.sample_result(t, _s(a.get("sample_id")), _s(a.get("status")), _s(a.get("note")))
        if action == "confirmations":
            return A.make_confirmations(t, e, int(a.get("top") or 10), a.get("min_amount"))
        if action == "approve_confirmations":
            if not _owner(ctx):
                raise ToolError("Confirmation bhejne ki haan sirf owner.")
            return A.approve_confirmations(t, e, bool(a.get("approve", True)))
        if action == "confirmation_reply":
            return A.confirmation_reply(t, _s(a.get("confirm_id")), a.get("amount"), _s(a.get("note")))
        if action == "queries":
            return A.query_list(t, e)
        if action == "asked":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return A.mark_asked(t, e)
        if action == "rep_letter":
            return A.rep_letter(t, e)
        if action == "workpapers":
            return A.workpapers(t, e, conv)
    except (A.AuditError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..audit import rules as R
    from ..audit import service as A
    t = ctx.tenant_id
    e = _s(a.get("engagement"))
    try:
        if what == "engagements":
            return {"engagements": A.engagements(t)}
        if what == "engagement":
            return A.get(t, e)
        if what == "findings":
            return {"findings": A.findings(t, e, _s(a.get("status")))}
        if what == "samples":
            return {"samples": A.samples(t, e)}
        if what == "confirmations":
            return A.confirmation_letters(t, e)
        if what == "status":
            return A.status_summary(t)
        if what == "tax_audit":
            import re as _re
            m = _re.match(r"(\d{4})", _s(a.get("fy")))
            return R.tax_audit(_s(a.get("kind")) or "business", float(a.get("turnover") or 0), a.get("cash_receipts_pct"),
                               a.get("cash_payments_pct"), int(m.group(1)) if m else 2025)
        if what == "caro":
            return R.caro(_s(a.get("company")) or "private", float(a.get("paid_up_reserves") or 0), float(a.get("borrowings") or 0),
                          float(a.get("revenue") or 0))
    except (A.AuditError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def audit(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def audit_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


AUDIT_HANDLERS = {"audit": audit, "audit_dekho": audit_dekho}
