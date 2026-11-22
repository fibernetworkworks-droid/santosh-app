"""Institution mode (F9 of docs/FINANCE_GLOBAL_PLAN.md) tool: `institution_desk` - the five institution employees in one door:
Financial Crime, Compliance, Risk, Audit & Controls, Governance, for a small regulated firm up to a bank. Every draft goes through
maker-checker (a named maker, a different named checker, two over her limit, bound to the text). Hoola prepares, screens and counts;
the named officers decide, sign and file."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["person_add", "limits", "submit", "revise", "check", "drafts", "aml_triage", "sar_draft", "sar_score", "kyc_review", "sanctions",
            "obligations", "policy_check", "promotion_check", "complaints_mi", "incident", "rcsa", "third_party", "models", "ecl", "pbc",
            "sample", "control_test", "je_test", "board_pack", "cap_table", "related_party", "whistle", "api_key", "retention", "export"]

INSTITUTION_TOOLS = [
    {"name": "institution_desk", "description": (
        "Institution mode: financial crime, compliance, risk, audit, governance (workspace = the institution's workspace; person = the "
        "named person acting). Never files, freezes or reports to a regulator; not legal advice. MAKER-CHECKER: person_add (name, roles "
        "admin|maker|checker|mlro|compliance|risk|audit|secretary|viewer; the first is an admin), limits (single_check_limit: above it two "
        "checkers), submit (kind, title, body, amount), revise (draft, body: every check falls away), check (draft, verdict approve|reject, "
        "hash of the text read, reason), drafts. FINANCIAL CRIME: aml_triage (transactions [{id, customer, date, amount, direction "
        "in|out, channel cash|wire|card|transfer, country, counterparty}], rules {cash_threshold, structuring_band_pct, structuring_count, "
        "structuring_days, pass_through_pct, pass_through_days, pass_through_min, high_risk_countries, high_risk_min, spike_multiple, "
        "spike_min, dormant_days, dormant_min, fan_in_senders, fan_in_days}), sar_draft (alert, transactions, customer {name, occupation, "
        "declared_income, expected_activity}, actions_taken, person -> into maker-checker), sar_score (draft, scores {facts_complete, "
        "clear_and_ordered, why_suspicious, no_accusation, ready_to_file: 1-5} by an MLRO), kyc_review (documents [{kind, expires}], "
        "required, factors, weights, bands), sanctions (names, watch). COMPLIANCE: obligations (add [{name, source, owner, control, "
        "every_days, last_done}]), policy_check (text, required_sections), promotion_check (text, banned_words), complaints_mi "
        "(complaints [{category, received, closed, upheld}], deadline_days). RISK: incident (title, detected, severity, clocks [{report, "
        "hours}]), rcsa (risks [{name, likelihood, impact, control_effect}], appetite), third_party (vendors, required_fields), models "
        "(models [{name, owner, ai, validated, validate_every_days}]), ecl (exposures). AUDIT: pbc (items), sample (population, size, "
        "seed), control_test (results, tolerated_failures), je_test (journals [{id, date, amount, user, description}], period_end, "
        "usual_users). GOVERNANCE: board_pack (agenda [{item, paper}], papers, actions), cap_table (holders, pre_money, raise, investor), "
        "related_party (related, transactions), whistle (what, area - no name). PLUMBING: api_key (scopes read|draft|check|admin, "
        "revoke), retention (keep_years), export."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "workspace": {"type": "string"}, "person": {"type": "string"},
         "name": {"type": "string"}, "roles": {"type": "array", "items": {"type": "string"}}, "single_check_limit": {"type": "number"},
         "kind": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "amount": {"type": "number"},
         "draft": {"type": "string"}, "verdict": {"type": "string"}, "hash": {"type": "string"}, "reason": {"type": "string"},
         "transactions": {"type": "array", "items": {}}, "rules": {"type": "object"}, "alert": {"type": "object"},
         "customer": {"type": "object"}, "actions_taken": {"type": "string"}, "scores": {"type": "object"}, "comment": {"type": "string"},
         "documents": {"type": "array", "items": {"type": "object"}}, "required": {"type": "array", "items": {"type": "string"}},
         "factors": {"type": "object"}, "weights": {"type": "object"}, "bands": {"type": "object"}, "names": {"type": "array", "items": {"type": "string"}},
         "watch": {"type": "array", "items": {"type": "object"}}, "add": {"type": "array", "items": {"type": "object"}},
         "text": {"type": "string"}, "required_sections": {"type": "array", "items": {"type": "string"}},
         "banned_words": {"type": "array", "items": {"type": "string"}}, "complaints": {"type": "array", "items": {"type": "object"}},
         "deadline_days": {"type": "integer"}, "detected": {"type": "string"}, "severity": {"type": "string"},
         "clocks": {"type": "array", "items": {"type": "object"}}, "risks": {"type": "array", "items": {"type": "object"}},
         "appetite": {"type": "number"}, "vendors": {"type": "array", "items": {"type": "object"}},
         "required_fields": {"type": "array", "items": {"type": "string"}}, "models": {"type": "array", "items": {"type": "object"}},
         "exposures": {"type": "array", "items": {"type": "object"}}, "items": {"type": "array", "items": {"type": "object"}},
         "population": {"type": "array", "items": {}}, "size": {"type": "integer"}, "seed": {"type": "integer"},
         "results": {"type": "array", "items": {"type": "object"}}, "tolerated_failures": {"type": "integer"},
         "journals": {"type": "array", "items": {"type": "object"}}, "period_end": {"type": "string"},
         "usual_users": {"type": "array", "items": {"type": "string"}}, "agenda": {"type": "array", "items": {"type": "object"}},
         "papers": {"type": "array", "items": {"type": "string"}}, "actions": {"type": "array", "items": {"type": "object"}},
         "holders": {"type": "array", "items": {"type": "object"}}, "pre_money": {"type": "number"}, "raise": {"type": "number"},
         "investor": {"type": "string"}, "related": {"type": "array", "items": {"type": "string"}}, "what": {"type": "string"},
         "area": {"type": "string"}, "scopes": {"type": "array", "items": {"type": "string"}}, "revoke": {"type": "string"},
         "keep_years": {"type": "object"}, "today": {"type": "string"}},
         "required": ["action"]}},
]
INSTITUTION_LABELS = {"institution_desk": "Working on the institution's controls"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import institution as IN
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "institution_desk", action, a, lambda: IN.run(tenant, action, a, actor))


async def _institution_desk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
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


INSTITUTION_HANDLERS = {"institution_desk": _institution_desk}
