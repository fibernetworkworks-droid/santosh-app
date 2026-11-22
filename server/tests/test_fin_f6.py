"""F6 of docs/FINANCE_GLOBAL_PLAN.md - Credit & Lending, both sides. The card: APR for 10 countries' methods; memo figures traced;
contact-rule violations refused."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _ws(tenant, cc="GB", cur="GBP"):
    from app.fin import profile as PR
    a = {**PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})["answers"], "currency": cur}
    return PR.apply(tenant, a, PR.preview(a)["hash"])["id"]


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f6 as C
    from app.fin.desks import credit as CR
    r = C.run(10)
    assert r["ok"] and len(r["countries"]) == 10 and len(r["methods"]) == 4, [x for x in r["rows"] if not x["ok"]][:3]
    real = CR._flows
    try:      # fees left out of the APR must fail the card
        CR._flows = lambda a: (float(a["amount"]),) + real(a)[1:]
        assert not C.run(4)["ok"]
    finally:
        CR._flows = real
    re_ = CR._effective
    try:      # her looser hours winning over Hoola's floor must fail the card
        CR._effective = lambda mine: {**re_(mine), "to_hour": mine.get("to_hour", 21)}
        assert not C.run(1)["ok"]
    finally:
        CR._effective = re_


def test_apr_methods_and_borrower_tools(env):
    from app.fin.desks import credit as CR
    loan = {"amount": 10000, "rate": 10, "term": 12, "fees_upfront": 200}
    us = CR.run("b1", "apr", {**loan, "country": "US"})
    eu = CR.run("b1", "apr", {**loan, "country": "GB"})
    sg = CR.run("b1", "apr", {**loan, "country": "SG"})
    assert us["method"] == "us_actuarial" and eu["method"] == "eu_annual" and sg["method"] == "effective_irr"
    assert us["apr_pct"] < sg["apr_pct"] and round(eu["apr_pct"]) == round(sg["apr_pct"])        # effective > nominal
    assert us["money_received"] == 9800 and "not confirmed" in us["method_from"]
    with pytest.raises(CR.CreditError):
        CR.run("b1", "apr", {**loan, "country": "ZZ"})
    s = CR.run("b1", "shop", {"country": "IN", "offers": [{"name": "A", "amount": 100000, "rate": 11, "term": 24, "fee_pct": 3},
                                                          {"name": "B", "amount": 100000, "rate": 12, "term": 24}]})
    assert s["cheapest_by_total_cost"] == "B"
    f = CR.run("b1", "invoice_finance", {"invoice": 10000, "advance_pct": 80, "fee_pct": 1, "days": 60})
    assert f["money_now"] == 7900 and f["cost_a_year_pct"] > f["simple_a_year_pct"]
    with pytest.raises(PermissionError):
        CR.run("b1", "approve_loan", {})


def test_readiness_and_memo_traced(env):
    from app.fin import spine as SP
    from app.fin.desks import credit as CR
    ws = _ws("b2")
    SP.import_statement("b2", ws, "Date,Narration,Debit,Credit\n2026-07-01,CLIENT A,,5000.00\n2026-07-05,TERM LOAN EMI,800.00,\n"
                        "2026-08-01,CLIENT A,,5200.00\n2026-08-05,TERM LOAN EMI,800.00,\n2026-08-09,CHQ RTN UNPAID,50.00,\n", "Current", "GBP")
    r = CR.run("b2", "readiness", {"workspace": ws, "since": "2026-01-01"})
    f = r["statements"]["figures"]
    assert f["regular_debt_payments_monthly"]["value"] == 800 and f["bounced_items"]["value"] == 1
    assert any("months of statements" in g for g in r["gaps"]) and any("returned" in g for g in r["gaps"])
    m = CR.run("b2", "memo", {"workspace": ws, "analyse": True, "borrower": "Co",
                              "figures": {"ebitda": {"value": 120000, "source": "accounts 2025 p.3"},
                                          "debt_service": {"value": 100000, "source": "loan schedule"}}, "policy": {"dscr": 1.25}})
    assert m["ratios"]["dscr"]["value"] == 1.2 and m["ratios"]["dscr"]["sources"] == ["S1", "S2"]
    assert m["policy_flags"] and "[S1]" in m["memo_markdown"] and m["sources"]["S3"].startswith("bank statement")
    assert m["ratios"]["debt_to_income"]["value"] == round(800 / 5100 * 100, 1)
    with pytest.raises(CR.CreditError):
        CR.run("b2", "memo", {"figures": {"ebitda": {"value": 1}}})


def test_lender_tools(env):
    from app.fin.desks import credit as CR
    with pytest.raises(CR.CreditError):
        CR.run("l1", "rules", {"applicant": {"gender": "f"}, "rules": [{"field": "gender", "op": "==", "value": "m"}]})
    h = CR.run("l1", "rules", {"applicant": {"income_monthly": 3000, "bureau_score": 640},
                               "rules": [{"field": "bureau_score", "op": ">=", "value": 700, "code": "SCORE"}]})
    assert h["reason_codes"] == ["SCORE"]
    k = CR.run("l1", "kfs", {"amount": 50000, "rate": 12, "term": 24, "fee_pct": 2, "country": "IN"})
    assert "APR by nominal_irr" in k["kfs_markdown"]
    c = CR.run("l1", "conditions", {"today": "2026-09-01", "items": [{"name": "title deed", "status": "received"},
                                                                     {"name": "insurance", "status": "missing", "due": "2026-08-15"}]})
    assert c["missing"] == ["insurance"] and c["items"][1]["late"] and not c["ready_to_draw"]
    with pytest.raises(CR.CreditError):
        CR.run("l1", "conditions", {"items": [{"name": "x", "status": "waived"}]})
    s = CR.run("l1", "servicing", {"amount": 1200, "rate": 0, "term": 12, "start": "2026-01-10", "today": "2026-04-20",
                                   "paid": [{"date": "2026-01-10", "amount": 100}, {"date": "2026-02-10", "amount": 100}]})
    assert (s["arrears"], s["oldest_unpaid_due"], s["days_past_due"], s["next_due"]) == (200.0, "2026-03-10", 41, "2026-05-10")
    e = CR.run("l1", "ews", {"dpd_history": [0, 15, 40]})
    assert e["watch"]
    assert CR.run("l1", "ecl", {"exposures": [{"id": 1, "ead": 1000, "pd": 0.02, "lgd": 0.5, "dpd": 0}]})["total_ecl"] == 10.0


def test_collections_refused_and_logged(env):
    from app.fin.desks import credit as CR
    ws = _ws("l2")
    base = {"workspace": ws, "borrower": "Sam", "tz": "Europe/London", "channel": "sms", "message": "Your payment is due."}
    with pytest.raises(CR.CreditError) as e:
        CR.run("l2", "collect", {**base, "when": "2026-09-07T07:00"})
    assert "08:00-21:00" in str(e.value)
    CR.run("l2", "collect", {**base, "when": "2026-09-07T09:00"})
    with pytest.raises(CR.CreditError):
        CR.run("l2", "collect", {**base, "when": "2026-09-07T12:00"})
    with pytest.raises(CR.CreditError):
        CR.run("l2", "collect", {**base, "when": "2026-09-08T12:00", "message": "We will call the police."})
    assert "does not send" in CR.run("l2", "collect", {**base, "when": "2026-09-08T12:00"})["says"]


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["credit_lending"] == "lending" and "credit_lending" in HI.CATALOG
    out = asyncio.run(TL.dispatch("credit_lending", {"action": "apr", "country": "US", "amount": 1000, "payment": 88.85, "term": 12},
                                  Ctx(tenant_id="l3", conversation_id="", actor="owner")))
    out = out if isinstance(out, dict) else json.loads(out)
    assert out["apr_pct"] == 12.0
    ctx = Ctx(tenant_id="l3", conversation_id="", actor="customer:x")
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("credit_lending", {"action": "memo", "figures": {}}, ctx))
    c = TestClient(app)
    assert c.post("/api/fin/credit/methods", json={}).status_code == 200
    assert c.post("/api/fin/credit/apr", json={}).status_code == 400
    assert c.post("/api/fin/credit/approve_loan", json={}).status_code == 403
