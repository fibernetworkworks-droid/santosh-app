"""Bima Assist tool: `bima_assist` (health-insurance register Wave 2: assists with a named human decider). Drafts and flags on facts given; decides, sends, files and stores nothing."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['plan_compare', 'material_facts', 'proposal_check', 'coverage_check', 'preauth_checks', 'query_reply', 'medical_timeline', 'rejection_letter', 'grievance_reply', 'ombudsman_packet', 'wording_review', 'missell_review', 'fhir_claim', 'code_map']
_SELF_HELP = {"plan_compare", "material_facts", "wording_review", "ombudsman_packet"}   # a policyholder may use these for herself

BIMAASSIST_TOOLS = [
    {"name": "bima_assist", "description": (
        "Health-insurance assist for the adviser, claims / TPA desk, compliance and integration team (drafts and flags on facts given; a NAMED human decides; sends, files and stores nothing; no medical or legal advice). "
        "action=plan_compare: plans [{name, premium, sum_insured, room_rent_cap, copay_pct, waiting_ped_months, network_count, claim_settlement_pct}] -> side-by-side, no recommendation. "
        "material_facts: answers [{q, answer}], history_notes -> health questions answered 'no' that the history contradicts. "
        "proposal_check: fields {name, dob, age, address, nominee, sum_insured, members, declaration_signed}, required -> missing / contradictions. "
        "coverage_check: policy {start, initial_waiting_days, ped_waiting_months, moratorium_months, specific_waiting{}, sublimits{}, room_rent_cap, copay_pct, clauses{}}, claim {admission, diagnosis, amount, is_ped, accident, room_charged} -> findings, each with the clause text supplied. "
        "preauth_checks: policy, request {procedure, estimate, admission, diagnosis}, package_rates{} -> pass / fail / unknown checks. "
        "query_reply: queries [], chart {} -> draft answers from the chart facts. "
        "medical_timeline: events [{date, type, text}], gap_days, expected{} -> sorted timeline and gaps. "
        "rejection_letter: claim_id, reasons [{reason, clause_ref, clause_text}], documents_considered, appeal_path, ombudsman -> draft (refused without a clause). "
        "grievance_reply: complaint, facts [], clause, remedies [] -> draft. "
        "ombudsman_packet: have [], insurer_reply_on, complaint_on, today -> packet index, missing, dates (rules from memory, verify). "
        "wording_review: text -> jargon, vague terms, long and exclusion sentences. "
        "missell_review: calls [{id, text}], policies [{id, issued, proposal_dob, id_dob}], freelook_days -> phrase hits, free-look days left. "
        "fhir_claim: claim {id, patient_id, insurer_id, provider_id, diagnosis_code, total, service_date, items[]} -> FHIR R4 Claim skeleton (not submitted). "
        "code_map: codes [], mapping {} (her table) -> mapped / ambiguous / unmapped."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "plans": {"type": "array", "items": {"type": "object"}}, "answers": {"type": "array", "items": {"type": "object"}},
         "history_notes": {"type": "string"}, "fields": {"type": "object"}, "required": {"type": "array", "items": {"type": "string"}}, "policy": {"type": "object"}, "claim": {"type": "object"},
         "request": {"type": "object"}, "package_rates": {"type": "object"}, "today": {"type": "string"}, "queries": {"type": "array", "items": {"type": "string"}}, "chart": {"type": "object"},
         "events": {"type": "array", "items": {"type": "object"}}, "gap_days": {"type": "number"}, "expected": {"type": "object"}, "claim_id": {"type": "string"},
         "reasons": {"type": "array", "items": {"type": "object"}}, "documents_considered": {"type": "array", "items": {"type": "string"}}, "appeal_path": {"type": "string"}, "ombudsman": {"type": "string"},
         "complaint": {"type": "string"}, "facts": {"type": "array", "items": {"type": "string"}}, "clause": {"type": "string"}, "remedies": {"type": "array", "items": {"type": "string"}},
         "have": {"type": "array", "items": {"type": "string"}}, "insurer_reply_on": {"type": "string"}, "complaint_on": {"type": "string"}, "text": {"type": "string"},
         "calls": {"type": "array", "items": {"type": "object"}}, "policies": {"type": "array", "items": {"type": "object"}}, "freelook_days": {"type": "number"},
         "codes": {"type": "array", "items": {"type": "string"}}, "mapping": {"type": "object"}},
         "required": ["action"]}},
]
BIMAASSIST_LABELS = {"bima_assist": "Checking with Bima Assist"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..bimaassist import engines as E
    g = a.get
    if action == "plan_compare":
        return E.plan_compare(g("plans") or [])
    if action == "material_facts":
        return E.material_facts(g("answers") or [], g("history_notes", ""))
    if action == "proposal_check":
        return E.proposal_check(g("fields") or {}, g("required"))
    if action == "coverage_check":
        return E.coverage_check(g("policy") or {}, g("claim") or {})
    if action == "preauth_checks":
        return E.preauth_checks(g("policy") or {}, g("request") or {}, g("package_rates"), g("today"))
    if action == "query_reply":
        return E.query_reply(g("queries") or [], g("chart") or {})
    if action == "medical_timeline":
        return E.medical_timeline(g("events") or [], g("gap_days", 3), g("expected"))
    if action == "rejection_letter":
        return E.rejection_letter(g("claim_id", ""), g("reasons") or [], g("documents_considered"), g("appeal_path", ""), g("ombudsman", ""))
    if action == "grievance_reply":
        return E.grievance_reply(g("complaint", ""), g("facts") or [], g("clause", ""), g("remedies"))
    if action == "ombudsman_packet":
        return E.ombudsman_packet(g("have"), g("insurer_reply_on"), g("complaint_on"), g("today"))
    if action == "wording_review":
        return E.wording_review(g("text", ""))
    if action == "missell_review":
        return E.missell_review(g("calls"), g("policies"), g("today"), g("freelook_days", 15))
    if action == "fhir_claim":
        return E.fhir_claim(g("claim") or {})
    if action == "code_map":
        return E.code_map(g("codes") or [], g("mapping") or {})
    raise ToolError(f"Unknown action '{action}'.")


async def _bima_assist(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if actor.startswith("customer:") and action not in _SELF_HELP:
        raise ToolError("This is for the insurance desk team.")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


BIMAASSIST_HANDLERS = {"bima_assist": _bima_assist}
