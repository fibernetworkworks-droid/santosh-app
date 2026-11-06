"""Health-insurance Wave 3 (bima_risk): rule hits and arithmetic with a named decider; nothing declined, accused, repriced or reserved."""
import asyncio
import inspect

import pytest

from app.bimarisk import engines as E
from tests.test_life import conv_ctx


def test_experience_trend_triangle():
    e = E.experience([{"age_band": "30-40", "premium": 1000, "paid": 1500, "claims": 3, "exposure": 10}, {"age_band": "20-30", "premium": 1000, "paid": 400, "claims": 1, "exposure": 1}], "age_band", 100, 5)
    g = {r["group"]: r for r in e["groups"]}
    assert g["30-40"]["loss_ratio_pct"] == 150.0 and g["30-40"]["frequency_per_year"] == 0.3 and g["30-40"]["severity"] == 500.0 and e["above_alert"] == ["30-40"] and g["20-30"]["thin"]
    with pytest.raises(ValueError):
        E.experience([{"gender": "f"}], "gender")
    t = E.price_trend([{"item": "knee", "year": 2020, "price": 100}, {"item": "knee", "year": 2022, "price": 121}])
    assert t["items"][0]["cagr_pct"] == 10.0
    tr = E.triangle([[100, 150, 165], [110, 165], [120]])
    assert tr["development_factors"][0] == round((150 + 165) / (100 + 110), 4) and tr["total_unpaid"] > 0 and "appointed actuary" in tr["decider"]
    with pytest.raises(ValueError):
        E.triangle([[1]])


def test_pricing_fairness_and_protected_refused():
    f = E.pricing_fairness([{"factor": "age", "level": "30", "premium_relativity": 1.0, "cost_relativity": 1.0}, {"factor": "age", "level": "40", "premium_relativity": 1.6, "cost_relativity": 1.2}])
    assert f["gaps"][0]["level"] == "40" and f["jumps"][0]["jump_pct"] == 60.0
    with pytest.raises(ValueError):
        E.pricing_fairness([{"factor": "gender", "level": "f", "premium_relativity": 1.1, "cost_relativity": 1}])


def test_uw_triage_decline_becomes_referral():
    rules = [{"field": "bmi", "op": ">", "value": 35, "route": "medical", "label": "BMI", "manual_ref": "p12", "loading_pct": 25},
             {"field": "hba1c", "op": ">=", "value": 9, "route": "decline", "label": "HbA1c"}]
    r = {x["id"]: x for x in E.uw_triage([{"id": 1, "bmi": 36, "hba1c": 6}, {"id": 2, "bmi": 20, "hba1c": 10}, {"id": 3, "bmi": 22}], rules)["results"]}
    assert r[1]["route"] == "medical" and r[1]["loading_pct_if_accepted"] == 25.0 and r[2]["route"] == "refer" and r[2]["rules_fired"][0]["was_decline_rule"] and r[3]["route"] == "auto_accept"
    with pytest.raises(ValueError):
        E.uw_triage([{"id": 1}], [{"field": "religion", "op": "==", "value": "x", "route": "refer"}])


def test_fraud_signals_are_questions():
    cl = [{"provider": "H1", "procedure": "knee", "amount": 300}] + [{"provider": "H2", "procedure": "knee", "amount": 100}] * 6
    o = E.provider_outliers(cl)
    assert o["outliers"][0]["provider"] == "H1" and "not an allegation" in o["note"]
    d = E.duplicates([{"claim": 1, "member": "m", "hospital": "A", "admit": "2026-11-01", "discharge": "2026-11-03"}, {"claim": 2, "member": "m", "hospital": "B", "admit": "2026-11-02", "discharge": "2026-11-04"}])
    assert d["overlapping_stays_different_hospitals"][0]["claims"] == [1, 2]
    gp = E.geo_plausibility([{"claim": 1, "member": "m", "home": [19.0, 72.8], "hospital": [28.6, 77.2], "admit": "2026-11-01"}, {"claim": 2, "member": "m", "home": [19.0, 72.8], "hospital": [13.0, 80.2], "admit": "2026-11-01"}])
    assert gp["far_from_home"] and gp["impossible_travel"]
    c = E.cashless_misuse([{"claim": 1, "approved": 100, "final": 160, "los_days": 1, "planned_procedure": "a", "final_procedure": "b"}, {"claim": 2, "approved": 100, "final": 100, "los_days": 4}])
    assert [x["claim"] for x in c["flagged"]] == [1] and len(c["flagged"][0]["reasons"]) == 3
    cb = E.case_builder([{"date": "2026-11-02", "text": "b"}, {"date": "2026-11-01", "text": "a"}])
    assert cb["timeline"][0]["text"] == "a" and "reserved" in cb["allegation"]


def test_fraud_audit_and_scheme_and_wiring(env):
    dec = [{"flagged": i < 10, "confirmed": False if i < 5 else True, "group": "A", "human_override": i < 3} for i in range(100)] + \
          [{"flagged": i < 30, "confirmed": False, "group": "B"} for i in range(100)]
    a = E.fraud_audit(dec)
    g = {r["group"]: r for r in a["groups"]}
    assert g["A"]["flag_rate_pct"] == 10.0 and g["A"]["false_positive_pct_of_reviewed"] == 50.0 and g["A"]["override_pct_of_flagged"] == 30.0 and a["flag_rate_ratio_max_over_min"] == 3.0 and a["disparity_alert"]
    with pytest.raises(ValueError):
        E.fraud_audit([{"flagged": True, "religion": "x"}])
    claims = [{"hospital": f"H{i}", "beneficiary_id": f"b{i}", "amount": 100} for i in range(3) for _ in range(10)] + [{"hospital": "Hx", "beneficiary_id": "b0", "amount": 100000}] * 10
    s = E.scheme_anomalies(claims, z=1.4)
    assert any(o["hospital"] == "Hx" for o in s["hospital_outliers"]) and s["beneficiary_in_multiple_hospitals"][0]["beneficiary_id"] == "b0"
    src = inspect.getsource(E)
    for w in ("session(", "open(", "sqlite", "requests", "httpx"):
        assert w not in src
    from app.agent import tools as T
    assert "bima_risk" in T.HANDLERS
    from app.employee.hire import CATALOG
    assert CATALOG["bima_risk"]["group"] == "Health Insurance"
    from app import voice
    assert "bima_risk" in voice.VOICE_VIA_KAAM
    from app.agent.bimarisk_tools import _bima_risk
    from app.agent.tools import ToolError
    ctx = conv_ctx()
    assert asyncio.run(_bima_risk(ctx, "price_trend", obs=[{"item": "x", "year": 2020, "price": 1}, {"item": "x", "year": 2021, "price": 2}]))["items"][0]["cagr_pct"] == 100.0
    ctx.actor = "customer:1"
    with pytest.raises(ToolError):
        asyncio.run(_bima_risk(ctx, "price_trend", obs=[]))
