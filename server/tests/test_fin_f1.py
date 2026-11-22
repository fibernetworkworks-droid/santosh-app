"""F1 of docs/FINANCE_GLOBAL_PLAN.md - Money Safety in every country: the parts, country rules at the D3 level they have, the rule
review (Hoola reads the official page -> source_read; a named person confirms -> checked), saved cases, the tool, the routes, the card."""
import asyncio
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

TEN = ("GB", "US", "IN", "AE", "SG", "AU", "CA", "IE", "DE", "SA")


@pytest.fixture
def review(tmp_path, monkeypatch):
    monkeypatch.setenv("HOOLA_FIN_REVIEW_DIR", str(tmp_path / "review"))
    from app.fin import pack as P
    P.load.cache_clear()
    yield tmp_path / "review"
    P.load.cache_clear()


def test_ten_packs_load_with_the_money_safety_rules(review):
    from app.fin import pack as P
    assert set(TEN) <= set(P.codes())
    r = P.check_all()
    assert r["errors"] == []
    for cc in TEN:
        for path in ("scam_refund.regime", "ombudsman.name", "fraud_report.police", "deposit_insurance.scheme", "credit_bureaus.list",
                     "card_dispute.law", "identity_theft.report_to"):
            assert P.peek(cc, path), (cc, path)
    assert P.currency_of("AE") == "AED" and P.currency_of("DE") == "EUR"


def test_the_card_passes_and_can_fail(review):
    from app.fin import card_f1 as C
    from app.fin.desks import safety as S
    r = C.run()
    assert r["cases"] == 60 and r["passed"] == 60 and r["refusals_held"] == 10, [x for x in r["rows"] if not x["ok"]][:3]
    real = S.add_period
    try:
        S.add_period = lambda st, n, u: real(st, n, u) + __import__("datetime").timedelta(days=1)
        assert C.run()["passed"] < 60
    finally:
        S.add_period = real


def test_unconfirmed_rules_never_become_deadlines(review):
    from app.fin.desks import safety as S
    out = S.refund_claim({"country": "GB", "txn_date": "2026-11-02", "amount": 100, "save": False})
    assert all(t["kind"] != "deadline" and t["date"] is None for t in out["time_limits"])
    assert S.NOT_CONFIRMED in out["regime"] and "check" in out["time_limits"][0]["says"]
    dep = S.deposit_check({"country": "US", "balances": [{"bank": "A", "amount": 300000}]})
    assert "protected" not in dep["banks"][0] and "not confirmed" in dep["says"]


def test_a_country_without_a_pack_gets_safe_steps_only(review):
    from app.fin.desks import safety as S
    out = S.refund_claim({"country": "ZZ", "txn_date": "2026-11-02"})
    assert out["pack"] is False and out["steps"] and "no country rules for ZZ" in out["says"]
    with pytest.raises(S.SafetyError):
        S.check_pay({"country": "United Kingdom"})


def test_reading_and_confirming_a_rule(review):
    from app.fin import pack as P
    from app.fin import review as RV
    from app.fin.desks import safety as S
    page = "<p>You must tell your bank within <b>13 months</b> of the payment to claim a refund.</p>"
    with pytest.raises(RV.ReviewError):      # not an official site
        RV.read("GB", "scam_refund.report_within", "https://example.com/x", "within 13 months of the payment", fetch=lambda u: page)
    with pytest.raises(RV.ReviewError):      # the sentence is not on the page
        RV.read("GB", "scam_refund.report_within", "https://www.psr.org.uk/app", "within 6 months of the payment", fetch=lambda u: page)
    r = RV.read("GB", "scam_refund.report_within", "https://www.psr.org.uk/app", "within 13 months of the payment",
                fetch=lambda u: page, today=date(2026, 11, 1))
    assert r["status"] == "source_read"
    out = S.refund_claim({"country": "GB", "txn_date": "2026-11-02", "save": False})
    t = out["time_limits"][0]
    assert t["kind"] == "reminder" and t["date"] == "2027-12-02" and "not a confirmed legal deadline" in t["says"]
    with pytest.raises(RV.ReviewError):
        RV.confirm("GB", "scam_refund.report_within", "", "https://www.psr.org.uk/app")
    RV.confirm("GB", "scam_refund.report_within", "A. Reviewer, UK payments lawyer", "https://www.psr.org.uk/app", today=date(2026, 11, 1))
    assert P.value_of("GB", "scam_refund.report_within")["status"] == "checked"
    t = S.refund_claim({"country": "GB", "txn_date": "2026-11-02", "save": False})["time_limits"][0]
    assert t["kind"] == "deadline" and t["date"] == "2027-12-02"
    assert json.loads((review / "GB.json").read_text())["rules"]["scam_refund.report_within"]["checked_by"].startswith("A. Reviewer")
    # a checked rule past its review date drops a level again
    assert P.value_of("GB", "scam_refund.report_within", need="source_read", today=date(2028, 1, 1))["status"] == "source_read"


def test_tool_new_parts_save_cases_and_old_actions_are_unchanged(env, review):
    from app.agent import tools as T
    from app.agent.tools import Ctx, ToolError
    from app.finguard import complaint as CP
    ctx = Ctx(tenant_id="t1", conversation_id="", actor="owner")
    old = asyncio.run(T.dispatch("paisa_sahayak", {"action": "complaint", "issue_type": "charges", "bank": "X"}, ctx))
    old = old if isinstance(old, dict) else json.loads(old)
    assert old["letter"] == CP.draft({"issue_type": "charges", "bank": "X"})["letter"]
    out = asyncio.run(T.dispatch("paisa_sahayak", {"action": "card_dispute", "country": "IE", "txn_date": "2026-11-02",
                                                    "amount": 40, "merchant": "Shop"}, ctx))
    out = out if isinstance(out, dict) else json.loads(out)
    assert out["case_id"] and "Payment Services Regulations" in out["law"]
    g = asyncio.run(T.dispatch("paisa_sahayak", {"action": "complaint", "country": "SG", "complained_on": "2026-11-02"}, ctx))
    g = g if isinstance(g, dict) else json.loads(g)
    assert "FIDReC" in g["ombudsman"]
    cases = asyncio.run(T.dispatch("paisa_sahayak", {"action": "cases"}, ctx))
    cases = cases if isinstance(cases, dict) else json.loads(cases)
    assert len(cases["cases"]) == 2 and {c["part"] for c in cases["cases"]} == {"card_dispute", "complaint_global"}
    with pytest.raises(ToolError):
        asyncio.run(T.dispatch("paisa_sahayak", {"action": "refund_claim", "country": "GB", "txn_date": "2026-11-02",
                                                  "otp": "123456"}, ctx))
    with pytest.raises(ToolError):
        asyncio.run(T.dispatch("paisa_sahayak", {"action": "id_theft", "country": "GB"},
                               Ctx(tenant_id="t1", conversation_id="", actor="customer:x")))


def test_institution_case_file_leaves_the_decision_to_a_person(review):
    from app.fin.desks import safety as S
    out = S.case_prep({"country": "AU", "case_kind": "scam", "evidence": ["Customer statement attached"]})
    assert out["decision"]["outcome"] == "" and "does not decide" in out["decision"]["says"]
    assert "Payment details and timestamps" in out["evidence_missing"]
    assert "Customer statement in their words" not in out["evidence_missing"]


def test_routes(env, review, monkeypatch):
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/fin/safety/deposit_check", json={"country": "CA", "balances": [{"bank": "A", "amount": 5}]})
    assert r.status_code == 200 and r.json()["banks"][0]["total"] == 5
    assert c.post("/api/fin/safety/approve_refund", json={"country": "CA"}).status_code == 403
    assert c.post("/api/fin/safety/refund_claim", json={"country": "CA", "txn_date": "bad"}).status_code == 400
    assert c.post("/api/fin/safety/card_dispute", json={"country": "DE", "txn_date": "2026-11-02"}).status_code == 200
    assert len(c.get("/api/fin/safety/cases").json()["cases"]) == 1
    assert any(x["path"] == "ombudsman.name" for x in c.get("/api/fin/packs/SA/todo").json()["rules"])
    assert c.post("/api/fin/packs/GB/confirm", json={"path": "ombudsman.name", "checked_by": "A. Person, lawyer",
                                                     "source": "https://example.com"}).status_code == 400
    import inspect

    from app.fin import api as FA
    assert "only the Hoola owner can change them" in inspect.getsource(FA)   # read / confirm check the owner first
