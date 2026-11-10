"""Bima Desk tool: `bima_desk` (health-insurance register Wave 1: customer side + admin). Worksheets and checklists on rows given; never decides, files, sends or stores a claim."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["claim_checklist", "payable", "settlement_match", "status_message", "ageing", "renewals", "grievance", "appeal", "kyc_check"]
_SHOPPER = {"claim_checklist", "payable", "appeal"}   # a policyholder may use these for her own claim

BIMADESK_TOOLS = [
    {"name": "bima_desk", "description": (
        "Health-insurance helper (worksheets and checklists on rows given; decides NO claim, files, sends and stores nothing; the insurer / TPA / a named officer decides, and it is not medical or legal advice). "
        "action=claim_checklist: claim_type cashless|reimbursement, kind accident|maternity|daycare|pre_post|opd, have [docs], admission, discharge, today -> missing documents and deadlines (periods from memory, verify). "
        "payable: items [{name, billed, payable_cap}], sum_insured, room_rent_cap, room_rent_charged, copay_pct, deductible, non_payable [words], settled -> itemised worksheet, room-rent proportion cut, gap to the settled amount, questions to ask. "
        "settlement_match: payments [{claim, utr, amount}], expected [{claim, payable, tds}] -> matched / short / excess / duplicate UTR. "
        "status_message: status registered|docs_pending|approved|paid|query|rejected, claim_id, extra, language hi|en -> draft message (not sent). "
        "ageing: claims [{id, received, status, last_doc_date}], tat_days, warn_days, today -> past-timeline and due-soon. "
        "renewals: policies [{id, holder, renewal_date, premium, ncb_pct}], window_days, portability_days, today -> reminder list. "
        "grievance: items [{id, received, text, acknowledged}], ack_days, resolve_days -> category guess, due dates, late flags. "
        "appeal: reasons [insurer's words], insurer_replied_on, today -> points to documents, steps, letter outline. "
        "kyc_check: docs {aadhaar, pan, bank_account, ifsc, name, dob} -> format checks with masked values."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "claim_type": {"type": "string"}, "kind": {"type": "string"}, "have": {"type": "array", "items": {"type": "string"}},
         "admission": {"type": "string"}, "discharge": {"type": "string"}, "today": {"type": "string"}, "intimate_hours": {"type": "number"}, "file_days": {"type": "number"},
         "items": {"type": "array", "items": {"type": "object"}}, "sum_insured": {"type": "number"}, "room_rent_cap": {"type": "number"}, "room_rent_charged": {"type": "number"},
         "copay_pct": {"type": "number"}, "deductible": {"type": "number"}, "non_payable": {"type": "array", "items": {"type": "string"}}, "settled": {"type": "number"},
         "payments": {"type": "array", "items": {"type": "object"}}, "expected": {"type": "array", "items": {"type": "object"}}, "tolerance": {"type": "number"},
         "status": {"type": "string"}, "claim_id": {"type": "string"}, "extra": {"type": "string"}, "language": {"type": "string"},
         "claims": {"type": "array", "items": {"type": "object"}}, "tat_days": {"type": "number"}, "warn_days": {"type": "number"},
         "policies": {"type": "array", "items": {"type": "object"}}, "window_days": {"type": "number"}, "portability_days": {"type": "number"},
         "ack_days": {"type": "number"}, "resolve_days": {"type": "number"}, "reasons": {"type": "array", "items": {"type": "string"}},
         "insurer_replied_on": {"type": "string"}, "docs": {"type": "object"}},
         "required": ["action"]}},
]
BIMADESK_LABELS = {"bima_desk": "Bima Desk se dekh raha hoon"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..bimadesk import engines as E
    if action == "claim_checklist":
        return E.claim_checklist(a.get("claim_type", "reimbursement"), a.get("have"), a.get("admission"), a.get("discharge"), a.get("today"), a.get("intimate_hours", 48), a.get("file_days", 30), a.get("kind"))
    if action == "payable":
        return E.payable(a.get("items") or [], a.get("sum_insured", 0), a.get("room_rent_cap", 0), a.get("room_rent_charged", 0), a.get("copay_pct", 0), a.get("deductible", 0), a.get("non_payable"), a.get("settled"))
    if action == "settlement_match":
        return E.settlement_match(a.get("payments") or [], a.get("expected") or [], a.get("tolerance", 1))
    if action == "status_message":
        return E.status_message(a.get("status", ""), a.get("claim_id", ""), a.get("extra", ""), a.get("language", "hi"))
    if action == "ageing":
        return E.ageing(a.get("claims") or [], a.get("today"), a.get("tat_days", 30), a.get("warn_days", 5))
    if action == "renewals":
        return E.renewals(a.get("policies") or [], a.get("today"), a.get("window_days", 60), a.get("portability_days", 45))
    if action == "grievance":
        return E.grievance(a.get("items") or [], a.get("today"), a.get("ack_days", 3), a.get("resolve_days", 14))
    if action == "appeal":
        return E.appeal(a.get("reasons") or [], None, a.get("today"), a.get("insurer_replied_on"))
    if action == "kyc_check":
        return E.kyc_check(a.get("docs") or {})
    raise ToolError(f"Unknown action '{action}'.")


async def _bima_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if actor.startswith("customer:") and action not in _SHOPPER:
        raise ToolError("This is for the insurance desk team.")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


BIMADESK_HANDLERS = {"bima_desk": _bima_desk}
