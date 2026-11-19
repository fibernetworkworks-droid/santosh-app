"""Bima Risk tool: `bima_risk` (health-insurance register Wave 3: pricing, underwriting and fraud-signal worksheets). Owner / staff only. Rule hits and arithmetic: declines, accuses, reprices and reserves NOTHING."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['experience', 'price_trend', 'triangle', 'pricing_fairness', 'uw_triage', 'provider_outliers', 'duplicates', 'geo_plausibility', 'cashless_misuse', 'case_builder', 'fraud_audit', 'scheme_anomalies']

BIMARISK_TOOLS = [
    {"name": "bima_risk", "description": (
        "Health-insurance risk worksheets for the actuary, underwriter, SIU and risk officer (rule hits and arithmetic on rows given with HER thresholds; declines, accuses, reprices, reserves and blacklists NO ONE; a named human decides; rules on religion, caste, gender, locality or name are refused). "
        "action=experience: rows [{age_band|city|tier, premium, paid, claims, exposure}], group_by, loss_ratio_alert, min_exposure -> loss ratio, frequency, severity per group. "
        "price_trend: obs [{item, year, price}] -> observed CAGR. "
        "triangle: tri [[cumulative paid by development period per origin]], tail -> chain-ladder working paper (reserve sign-off is the appointed actuary's). "
        "pricing_fairness: factors [{factor, level, premium_relativity, cost_relativity}], max_jump_pct, max_gap_pct -> premium-vs-cost gaps and unexplained jumps. "
        "uw_triage: proposals [{id, ...}], rules [{field, op, value, route medical|refer, label, manual_ref, loading_pct}] -> route and the rule that fired; a decline rule becomes a human referral. "
        "provider_outliers: claims [{provider, procedure, amount}], ratio -> providers above the peer median. "
        "duplicates: claims [{claim, member, hospital, admit, discharge}] -> overlapping stays. "
        "geo_plausibility: stays [{claim, member, home[lat,lon], hospital[lat,lon], admit}] -> far-from-home and impossible travel. "
        "cashless_misuse: cases [{claim, approved, final, los_days, planned_procedure, final_procedure}] -> flagged cases. "
        "case_builder: events [{date, text, source}], evidence[], questions[] -> neutral timeline and evidence table; allegation left blank. "
        "fraud_audit: decisions [{flagged, confirmed, group, human_override}] -> flag rate, false positives and override rate per group, disparity. "
        "scheme_anomalies: claims [{hospital, district, beneficiary_id, amount}] -> hospital outliers and IDs seen at several hospitals."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "rows": {"type": "array", "items": {"type": "object"}}, "group_by": {"type": "string"}, "loss_ratio_alert": {"type": "number"}, "min_exposure": {"type": "number"},
         "obs": {"type": "array", "items": {"type": "object"}}, "tri": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}, "tail": {"type": "number"},
         "factors": {"type": "array", "items": {"type": "object"}}, "max_jump_pct": {"type": "number"}, "max_gap_pct": {"type": "number"},
         "proposals": {"type": "array", "items": {"type": "object"}}, "rules": {"type": "array", "items": {"type": "object"}},
         "claims": {"type": "array", "items": {"type": "object"}}, "ratio": {"type": "number"}, "min_peers": {"type": "number"},
         "stays": {"type": "array", "items": {"type": "object"}}, "max_home_km": {"type": "number"}, "max_kmph": {"type": "number"},
         "cases": {"type": "array", "items": {"type": "object"}}, "upgrade_pct": {"type": "number"}, "short_stay_days": {"type": "number"},
         "events": {"type": "array", "items": {"type": "object"}}, "evidence": {"type": "array", "items": {"type": "object"}}, "questions": {"type": "array", "items": {"type": "string"}},
         "decisions": {"type": "array", "items": {"type": "object"}}, "max_gap": {"type": "number"}, "min_group": {"type": "number"}, "z": {"type": "number"}, "min_n": {"type": "number"}},
         "required": ["action"]}},
]
BIMARISK_LABELS = {"bima_risk": "Running checks with Bima Risk"}


def _sync(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..bimarisk import engines as E
    g = a.get
    if action == "experience":
        return E.experience(g("rows") or [], g("group_by", "age_band"), g("loss_ratio_alert", 100), g("min_exposure", 0))
    if action == "price_trend":
        return E.price_trend(g("obs") or [])
    if action == "triangle":
        return E.triangle(g("tri") or [], g("tail", 1.0))
    if action == "pricing_fairness":
        return E.pricing_fairness(g("factors") or [], g("max_jump_pct", 30), g("max_gap_pct", 15))
    if action == "uw_triage":
        return E.uw_triage(g("proposals") or [], g("rules") or [])
    if action == "provider_outliers":
        return E.provider_outliers(g("claims") or [], g("ratio", 1.5), g("min_peers", 5))
    if action == "duplicates":
        return E.duplicates(g("claims") or [])
    if action == "geo_plausibility":
        return E.geo_plausibility(g("stays") or [], g("max_home_km", 300), g("max_kmph", 90))
    if action == "cashless_misuse":
        return E.cashless_misuse(g("cases") or [], g("upgrade_pct", 25), g("short_stay_days", 1))
    if action == "case_builder":
        return E.case_builder(g("events") or [], g("evidence"), g("questions"))
    if action == "fraud_audit":
        return E.fraud_audit(g("decisions") or [], g("max_gap", 1.25), g("min_group", 30))
    if action == "scheme_anomalies":
        return E.scheme_anomalies(g("claims") or [], g("z", 3), g("min_n", 10))
    raise ToolError(f"Unknown action '{action}'.")


async def _bima_risk(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This is for the insurance risk desk team.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_sync, action, a)
    except ValueError as e:
        raise ToolError(str(e))


BIMARISK_HANDLERS = {"bima_risk": _bima_risk}
