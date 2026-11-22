"""F5 of docs/FINANCE_GLOBAL_PLAN.md - Payroll worldwide + Cash & Treasury. The card: payroll for 6 countries matches hand-computed
results to the cent; the forecast is back-tested on held-out months."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _ws(tenant, cc="GB", cur="GBP"):
    from app.fin import profile as PR
    a = {**PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})["answers"], "currency": cur}
    return PR.apply(tenant, a, PR.preview(a)["hash"])["id"]


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f5 as C
    from app.fin.desks import cash as CS
    from app.fin.desks import payroll as PY
    r = C.run(12)
    assert r["ok"] and len(r["countries"]) == 6, [x for x in r["rows"] if not x["ok"]][:3]
    real = PY._contribution
    try:      # a contribution ceiling ignored must fail the card
        PY._contribution = lambda c, g, t, cur: real({k: v for k, v in c.items() if k != "upto"}, g, t, cur)
        assert not C.run(6)["ok"]
    finally:
        PY._contribution = real
    rp = CS.predict_month
    try:      # a backtest that peeks at the month it predicts must fail the card
        CS.predict_month = lambda rows, m, w=3, ex=(): rp(rows, CS._add_months(m, 1), w, ex)
        assert not C.run(4)["ok"]
    finally:
        CS.predict_month = rp


def test_gb_payslip_by_hand_and_rules_never_guessed(env):
    from app.fin.desks import payroll as PY
    ws = _ws("p1")
    PY.run("p1", "employee", {"workspace": ws, "name": "Asha", "annual": 36000, "pre_tax_pct": 5, "tax_id": "QQ123456C"})
    with pytest.raises(PY.PayrollError) as e:
        PY.run("p1", "run", {"workspace": ws, "period": "2026-08"})
    assert "settings" in str(e.value)
    with pytest.raises(PY.PayrollError):          # rates with no source are refused
        PY.run("p1", "settings", {"workspace": ws, "income_tax": {"method": "flat", "flat_pct": 20}})
    PY.run("p1", "settings", {"workspace": ws, "source": "my accountant", "frequency": "monthly",
                              "income_tax": {"method": "annualised", "allowance": 12570, "bands": [{"upto": 37700, "pct": 20},
                                                                                                  {"upto": None, "pct": 40}]},
                              "contributions": [{"name": "NI", "employee_pct": 8, "employer_pct": 15, "from": 1048, "upto": 4189}]})
    r = PY.run("p1", "run", {"workspace": ws, "period": "2026-08", "extras": {"asha": {"bonus": 500}}})
    p = r["people"][0]
    # gross 3000 + 500; pension 5% = 175; taxable 3325 -> (39900 - 12570) x 20% = 5466 / 12 = 455.50
    # NI 8% of (3500 - 1048) = 196.16 ; employer 15% = 367.80
    assert (p["gross"], p["pre_tax"], p["tax"], p["ee"], p["er"]) == (3500.0, 175.0, 455.5, 196.16, 367.8)
    assert p["net"] == 3500 - 175 - 455.5 - 196.16 and p["cost"] == 3867.8
    s = PY.run("p1", "payslip", {"workspace": ws, "period": "2026-08", "employee": "Asha"})
    assert "DRAFT" in s["payslip"] and "my accountant" in s["payslip"]
    assert PY.run("p1", "people", {"workspace": ws})["employees"][0]["tax_id"] == "*****456C"
    pay = PY.run("p1", "payments", {"workspace": ws, "period": "2026-08"})
    assert pay["to_authorities"] == {"income tax": 455.5, "NI": 563.96} and "never pays" in pay["says"]
    PY.run("p1", "close", {"workspace": ws, "period": "2026-08"})
    with pytest.raises(PY.PayrollError):
        PY.run("p1", "run", {"workspace": ws, "period": "2026-08"})
    with pytest.raises(PermissionError):
        PY.run("p1", "file", {"workspace": ws})


def test_slabs_weekly_filings_contractors(env):
    from app.fin.desks import payroll as PY
    ws = _ws("p2", "IN", "INR")
    PY.run("p2", "settings", {"workspace": ws, "source": "test", "income_tax": {"method": "none"},
                              "contributions": [{"name": "PT", "slabs": [{"upto": 10000, "employee": 0}, {"upto": None, "employee": 200}]}],
                              "filings": [{"name": "PT return", "every": "monthly", "due_day": 15}]})
    PY.run("p2", "employee", {"workspace": ws, "name": "Ravi", "per_period": 25000})
    assert PY.run("p2", "run", {"workspace": ws, "period": "2026-08"})["people"][0]["net"] == 24800
    f = PY.run("p2", "filings", {"workspace": ws, "year": 2026, "today": "2026-09-20"})
    aug = next(x for x in f["items"] if x["for"] == "2026-08")
    assert aug["due"] == "2026-09-15" and aug["status"] == "overdue"
    PY.run("p2", "done", {"workspace": ws, "filing": "PT return", "for": "2026-08", "reference": "ACK1"})
    f = PY.run("p2", "filings", {"workspace": ws, "year": 2026, "today": "2026-09-20"})
    assert next(x for x in f["items"] if x["for"] == "2026-08")["status"] == "done"
    c = PY.run("p2", "contractors", {"workspace": ws, "year": 2026, "threshold": 600,
                                     "rows": [{"payee": "A", "amount": 400, "date": "2026-02-01"}, {"payee": "A", "amount": 250, "date": "2026-05-01"},
                                              {"payee": "B", "amount": 100, "date": "2026-05-01"}, {"payee": "A", "amount": 999, "date": "2025-12-01"}]})
    assert [(x["payee"], x["total"], x["report"]) for x in c["payees"]] == [("A", 650.0, True), ("B", 100.0, False)]
    assert c["missing_tax_ids"] == ["A"] and "A," in c["csv"] and "B," not in c["csv"]
    wu = _ws("p3", "US", "USD")
    PY.run("p3", "settings", {"workspace": wu, "source": "t", "frequency": "weekly", "income_tax": {"method": "flat", "flat_pct": 10},
                              "contributions": [{"name": "SS", "employee_pct": 6.2, "employer_pct": 6.2, "upto": 3000}]})
    PY.run("p3", "employee", {"workspace": wu, "name": "Lee", "hourly": 25.5, "hours": 40})
    with pytest.raises(PY.PayrollError):
        PY.run("p3", "run", {"workspace": wu, "period": "2026-08"})          # weekly needs the first day
    r = PY.run("p3", "run", {"workspace": wu, "period": "2026-08-03", "extras": {"lee": {"hours": 44}}})
    assert r["end"] == "2026-08-09" and r["people"][0]["gross"] == 1122.0 and r["people"][0]["ee"] == 69.56


def test_forecast_payroll_idle_fees_fx_covenants(env):
    from app.fin import spine as SP
    from app.fin.desks import books as B
    from app.fin.desks import cash as CS
    from app.fin.desks import payroll as PY
    ws = _ws("c1")
    SP.import_statement("c1", ws, "Date,Narration,Debit,Credit\n2026-07-01,RENT 7,1000.00,\n2026-08-01,RENT 8,1000.00,\n"
                        "2026-09-01,RENT 9,1000.00,\n2026-08-20,MONTHLY FEE,5.00,\n2026-09-20,MONTHLY FEE,5.00,\n2026-09-25,SALES,,20000.00\n",
                        "Current", "GBP")
    PY.run("c1", "settings", {"workspace": ws, "source": "t", "pay_day": 28, "income_tax": {"method": "none"},
                              "contributions": [{"name": "NI", "employer_pct": 10}]})
    PY.run("c1", "employee", {"workspace": ws, "name": "A", "per_period": 2000})
    PY.run("c1", "run", {"workspace": ws, "period": "2026-09"})
    B.run("c1", "bill", {"workspace": ws, "party": "Supplier", "issue": "2026-10-01", "due": "2026-10-14", "issue_now": True,
                         "lines": [{"price": 300}]})
    CS.run("c1", "settings", {"workspace": ws, "min_cash": 15000})
    f = CS.run("c1", "forecast", {"workspace": ws, "start": "2026-10-05", "weeks": 5})
    assert f["opening"] == 16990.0
    lines = [ln for wk in f["weeks"] for ln in wk["lines"]]
    assert any(ln["what"].startswith("rent") and ln["day"] == "2026-11-01" for ln in lines)          # repeats on its day
    assert any("payroll" in ln["what"] and ln["amount"] == -2200 and ln["day"] == "2026-10-28" for ln in lines)
    assert f["weeks"][1]["out"] == 300 and f["lowest"]["closing"] == 16990 - 300 - 2200 - 1000 - 5 == f["weeks"][-1]["closing"]
    assert f["under_minimum_weeks"] == [4, 5]
    i = CS.run("c1", "idle", {"workspace": ws, "start": "2026-10-05", "weeks": 5, "weeks_buffer": 0})
    assert i["idle"] == 0 and "no spare" in i["says"].lower()
    fe = CS.run("c1", "fees", {"workspace": ws})
    assert fe["total"] == 10.0 and fe["by_kind"] == {"account fee": 10.0}
    B.run("c1", "invoice", {"workspace": ws, "party": "Paris", "issue": "2026-10-01", "currency": "EUR", "rate": 0.86, "rate_date": "2026-10-01",
                            "rate_source": "bank", "issue_now": True, "lines": [{"price": 1000}]})
    x = CS.run("c1", "fx", {"workspace": ws, "rates": {"EUR": 0.85}, "move_pct": 10})
    eur = x["positions"][0]
    assert eur["owed_to_you"] == 1000.0 and eur["value_in_GBP"] == 850.0 and x["total_if_all_fall"] == -85.0
    with pytest.raises(CS.CashError):
        CS.run("c1", "covenants", {"workspace": ws})
    CS.run("c1", "settings", {"workspace": ws, "covenants": [{"name": "cash floor", "kind": "min_cash", "limit": 14000},
                                                             {"name": "leverage", "kind": "max_ratio", "numerator": "net_debt",
                                                              "denominator": "ebitda", "limit": 3}]})
    cv = CS.run("c1", "covenants", {"workspace": ws, "start": "2026-10-05", "figures": {"net_debt": 70000, "ebitda": 20000}})
    assert [(c["name"], c["ok"]) for c in cv["covenants"]] == [("cash floor", False), ("leverage", False)]
    assert cv["covenants"][1]["actual"] == 3.5 and set(cv["breached"]) == {"cash floor", "leverage"}


def test_backtest_needs_months(env):
    from app.fin import spine as SP
    from app.fin.desks import cash as CS
    ws = _ws("c2")
    SP.import_statement("c2", ws, "Date,Narration,Debit,Credit\n2026-08-01,RENT,1000.00,\n", "Current", "GBP")
    with pytest.raises(CS.CashError) as e:
        CS.run("c2", "backtest", {"workspace": ws})
    assert "at least 6 months" in str(e.value)


def test_tools_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["payroll_worldwide"] == "payrollwide" and TL.FAMILY_OF["cash_treasury"] == "treasury"
    assert "payroll_worldwide" in HI.CATALOG and "cash_treasury" in HI.CATALOG
    ctx = Ctx(tenant_id="c3", conversation_id="", actor="owner")
    ws = _ws("c3")
    out = asyncio.run(TL.dispatch("payroll_worldwide", {"action": "people", "workspace": ws}, ctx))
    out = out if isinstance(out, dict) else json.loads(out)
    assert out["employees"] == []
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("cash_treasury", {"action": "fees", "workspace": ws}, Ctx(tenant_id="c3", conversation_id="",
                                                                                          actor="customer:x")))
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("payroll_worldwide", {"action": "employee", "workspace": ws, "name": "X", "annual": 1},
                                Ctx(tenant_id="c3", conversation_id="", actor="staff:y")))
    c = TestClient(app)
    assert c.post("/api/fin/payroll/people", json={}).status_code == 400
    assert c.post("/api/fin/payroll/file", json={"workspace": "x"}).status_code == 403
    assert c.post("/api/fin/cash/forecast", json={}).status_code == 400
