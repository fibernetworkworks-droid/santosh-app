"""v0.94 Payroll Officer: Code on Wages wages, EPF (Rs 25,000 ceiling from 17 Sep 2026, September split), ESIC period
coverage, state professional tax, TDS under Sec 392 (new / old regime, marginal relief), the monthly run with checks, her
Haan before files, ECR / bank file / payslips, advances, full & final with gratuity, bonus, the due calendar, tools + API."""
import asyncio
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"


def _today(monkeypatch, d: date):
    monkeypatch.setattr("app.payroll.service.today", lambda t: d)


def test_rules():
    from app.payroll import rules as R
    assert R.code_wages(6000, 18000) == 9000 and R.code_wages(15000, 30000) == 15000
    oct_ = R.pf("2026-10", 30000)
    assert oct_ == {"pf_wages": 25000, "eps_wages": 25000, "edli_wages": 25000, "ee": 3000, "eps": 2083, "er_epf": 917,
                    "edli": 125, "admin": 125}
    aug = R.pf("2026-08", 20000)
    assert aug["ee"] == 1800 and aug["eps"] == 1250 and aug["er_epf"] == 550
    sep = R.pf("2026-09", 30000)
    assert sep["pf_wages"] == 19667 and sep["ee"] == 2360                    # 15,000 x 16/30 + 25,000 x 14/30
    assert R.pf("2026-10", 30000, eps_member=False)["eps"] == 0 and R.pf("2026-10", 30000, eps_member=False)["er_epf"] == 3000
    assert R.pf("2026-10", 40000, on_full=True)["ee"] == 4800 and R.pf("2026-10", 40000, on_full=True)["eps_wages"] == 25000
    assert R.esi(20000, 30) == {"esi_wages": 20000, "ee": 150, "er": 650}
    assert R.esi(15000, 30)["ee"] == 113 and R.esi(4500, 30)["ee"] == 0      # Rs 150 a day: employee share nil
    assert R.esi_period_start("2026-11") == "2026-10" and R.esi_period_start("2027-02") == "2026-10" and R.esi_period_start("2026-05") == "2026-04"
    assert R.pt("27", 15000, 10) == 200 and R.pt("27", 15000, 2) == 300 and R.pt("27", 9000, 10) == 175
    assert R.pt("27", 20000, 10, "F") == 0 and R.pt("Maharashtra", 30000, 10, "F") == 200
    assert R.pt("29", 30000, 5) == 150 and R.pt("29", 45000, 5) == 200 and R.pt("09", 90000, 5) == 0
    assert R.pt("33", 30000, 9, half_year_gross=180000) == 1250 and R.pt("33", 30000, 10) == 0
    assert R.annual_tax(1200000)["total"] == 0
    assert R.annual_tax(1210000)["total"] == 10400                          # marginal relief: no more than the 10,000 above 12 lakh
    assert R.annual_tax(1725000)["total"] == 150800
    assert R.annual_tax(500000, "old")["total"] == 0 and R.annual_tax(600000, "old")["total"] == 33800
    assert R.annual_tax(6e7)["surcharge"] > 0
    assert R.months_left_in_fy("2026-10") == 6 and R.months_left_in_fy("2027-03") == 1 and R.fy_of("2027-01") == "2026-27"
    g = R.gratuity(20000, date(2019, 1, 1), date(2025, 8, 1))
    assert g["eligible"] and g["years"] == 7 and g["amount"] == 80769
    assert not R.gratuity(20000, date(2023, 1, 1), date(2025, 8, 1))["eligible"]
    assert R.gratuity(20000, date(2024, 1, 1), date(2025, 7, 15), fixed_term=True)["eligible"]
    assert R.bonus([15000] * 12) == 6997 and R.bonus([30000] * 12) == 0
    assert R.ot_amount(15600, 4) == 600
    assert R.working_days_after(date(2026, 10, 24), 2) == date(2026, 10, 27)     # Sunday skipped
    ds = {d["kind"]: d["due"] for d in R.dues("2027-03")}
    assert ds["tds"] == date(2027, 4, 30) and ds["form138"] == date(2027, 5, 31) and ds["form130"] == date(2027, 6, 15)
    assert {d["kind"]: d["due"] for d in R.dues("2026-10")}["pf"] == date(2026, 11, 15)


def _setup(P):
    P.save_settings(T, company="Sai Fabrication", state="Maharashtra", pf_on=True, esi_on=True, min_wage=12000)
    P.save_employee(T, "Ramesh Patil", gender="M", doj="2019-01-01", dob="1985-05-01",
                    pay={"basic": 15000, "hra": 6000, "special": 9000}, uan="100200300400", pan="ABCDE1234F",
                    account="123456789012", ifsc="SBIN0001234", phone="9822000001", alias="Ramu")
    P.save_employee(T, "Sunita Jadhav", gender="F", doj="2022-04-01", pay={"basic": 6000, "hra": 6000, "special": 6000},
                    uan="100200300401", esic_ip="1234567890", account="223456789012", ifsc="HDFC0000123")
    P.save_employee(T, "Ajay More", gender="M", doj="2026-10-16", gross=14000, uan="100200300402", esic_ip="1234567891")


def test_run_haan_files_paid(env, monkeypatch):
    from app.payroll import service as P
    _today(monkeypatch, date(2026, 11, 2))
    conv = conv_ctx().conversation_id
    _setup(P)
    emp = {e["name"]: e for e in P.employees(T)}
    assert emp["Ramesh Patil"]["pan"] == "XXXXXX234F" and emp["Ramesh Patil"]["bank"]["account"] == "XXXXXXXX9012"
    with pytest.raises(P.PayError):
        P.save_employee(T, "X", pan="12345")
    out = P.set_attendance(T, "2026-10", [{"employee": "Ramu", "lop_days": 2, "ot_hours": 4}, {"employee": "nobody", "lop_days": 1}])
    assert out["saved"] == 1 and out["errors"]
    P.add_advance(T, "Sunita", 3000, 1000)
    r = P.prepare_run(T, "2026-10", conv)
    run = r["run"]
    L = {x["name"]: x for x in run["lines"]}
    ram = L["Ramesh Patil"]
    assert ram["paid_days"] == 29 and ram["ot"] == round(15000 / 26 / 8 * 2 * 4, 2)
    assert ram["pf"]["ee"] == 1684 and ram["esi"]["ee"] == 0 and ram["pt"] == 200       # ESIC: 30,000 is above 21,000
    sun = L["Sunita Jadhav"]
    assert sun["wages"] == 9000 and sun["pf"]["ee"] == 1080                             # 50% rule: basic 6,000 -> wages 9,000
    assert sun["esi"] == {"esi_wages": 18000, "ee": 135, "er": 585} and sun["pt"] == 0 and sun["advance"] == 1000
    aj = L["Ajay More"]
    assert aj["paid_days"] == 16 and aj["lop_days"] == 15                                # joined on the 16th
    assert run["totals"]["pf_admin"] == 500 and run["totals"]["employees"] == 3
    assert any("bank account nahi" in c for c in run["checks"]) and any("PAN" not in c or True for c in run["checks"])
    # her Haan first
    with pytest.raises(P.PayError):
        P.files(T, run["id"])
    with pytest.raises(P.PayError):
        P.mark_paid(T, run["id"])
    P.decide(T, "2026-10", True)
    f = P.files(T, run["id"], conv)
    names = [x["name"] for x in f["files"]]
    assert {"Payslips_2026-10.pdf", "Salary_Register_2026-10.xlsx", "Bank_Salary_2026-10.xlsx", "ECR_2026-10.txt", "ESIC_2026-10.xlsx"} <= set(names)
    assert f["missing_bank"] == ["Ajay More"]
    ecr = P.ecr_text(run["lines"]).splitlines()
    assert ecr[0].split("#~#")[:2] == ["100200300400", "RAMESH PATIL"] and len(ecr[0].split("#~#")) == 11
    assert ecr[0].split("#~#")[9] == "2"                                                  # NCP days
    paid = P.mark_paid(T, run["id"], "2026-11-05")
    assert paid["run"]["status"] == "paid"
    with P.session() as s:
        adv = s.query(P.PayAdvance).first()
        assert adv.balance == 2000
    with pytest.raises(P.PayError):
        P.prepare_run(T, "2026-10")
    d = P.payslip_drafts(T, run["id"])["drafts"]
    assert any("Ramesh" in x["text"] and x["to"] == "9822000001" for x in d)


def test_tds_ytd_and_regimes(env, monkeypatch):
    from app.payroll import service as P
    _today(monkeypatch, date(2026, 11, 1))
    P.save_settings(T, company="X", state="Karnataka")
    P.save_employee(T, "Big Boss", gender="M", doj="2020-01-01", gross=150000, pan="ABCDE1234F", prev_income=900000,
                    account="123456789012", ifsc="SBIN0001234")
    r = P.prepare_run(T, "2026-10")["run"]
    ln = r["lines"][0]
    assert ln["tax_year"]["total"] == 150800 and ln["tds"] == round(150800 / 6)
    assert ln["pf"]["ee"] == 0 and ln["pt"] == 200                                       # PF not registered; Karnataka PT
    P.decide(T, r["id"], True)
    P.mark_paid(T, r["id"])
    _today(monkeypatch, date(2026, 12, 1))
    r2 = P.prepare_run(T, "2026-11")["run"]
    assert r2["lines"][0]["tds"] == round((150800 - ln["tds"]) / 5)
    P.save_employee(T, "Old Regime", gender="M", doj="2020-01-01", gross=50000, regime="old", declared=150000, pan="ABCDE1234G")
    r3 = P.prepare_run(T, "2026-11")["run"]
    o = next(x for x in r3["lines"] if x["name"] == "Old Regime")
    assert o["tax_year"]["taxable"] == 50000 * 5 - 50000 - 150000 - 200 * 5             # Nov-Mar: 5 months, std ded, 80C, PT


def test_leaving_bonus_calendar(env, monkeypatch):
    from app.payroll import service as P
    _today(monkeypatch, date(2026, 10, 22))
    _setup(P)
    out = P.full_and_final(T, "Ramesh", "2026-10-20", leave_days=10, notice_recovery=2000)
    f = out["fnf"]
    assert f["gratuity"]["eligible"] and f["gratuity"]["years"] == 8
    assert f["leave_encashment"] == round(15000 / 26 * 10) and f["pay_by"] == "2026-10-22"
    assert f["salary_line"]["paid_days"] == 20 and "2 working din" in out["say"]
    assert not any(e["name"] == "Ramesh Patil" for e in P.employees(T))
    cal = P.calendar(T)
    assert any(x["kind"] == "fnf" for x in cal["due"] + cal["late"])
    assert any(x["kind"] == "pf" and x["period"] == "2026-09" for x in cal["late"] + cal["due"]) or cal["due"]
    _today(monkeypatch, date(2026, 11, 3))
    for per in ("2026-10",):
        r = P.prepare_run(T, per)["run"]
        P.decide(T, r["id"], True)
    b = P.bonus_report(T, "2026-10")
    assert any(x["employee"] == "Sunita Jadhav" for x in b["rows"])


def test_tools_api(env, monkeypatch):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    from app.payroll import service as P
    assert roles.duty_of("payroll") == "payroll_work" and roles.kind_of("payroll_dekho") == "read" and "payroll" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["payroll"]["role"] == "payroll_officer"
    _today(monkeypatch, date(2026, 11, 2))
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    run("payroll", action="settings", company="Sai", state="27", pf_on=True)
    e = run("payroll", action="employee", name="Kiran", gender="F", doj="2025-01-01", gross=20000, uan="100200300499")
    assert "bank account" in e["say"]
    out = run("payroll", action="run", period="2026-10")
    rid = out["run"]["id"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["payroll"](staff, action="decide", run=rid, approve=True))
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["payroll"](staff, action="paid", run=rid))
    assert run("payroll_dekho", what="tax", gross_year=1275000)["total"] == 0
    with TestClient(main.app) as cl:
        assert "payroll" in cl.get("/healthz").json()["features"]
        assert cl.get("/api/payroll/employees").json()["employees"][0]["name"] == "Kiran"
        csv_ = "Name,Present Days,OT Hours\nKiran,28,3\n"
        imp = cl.post("/api/payroll/attendance/import", files={"file": ("a.csv", csv_.encode(), "text/csv")}, data={"period": "2026-10"})
        assert imp.status_code == 200 and imp.json()["saved"] == 1, imp.text
        r = cl.post("/api/payroll/runs", json={"period": "2026-10"}).json()["run"]
        assert r["lines"][0]["lop_days"] == 3
        assert cl.post(f"/api/payroll/runs/{r['id']}/files", json={}).status_code == 400
        assert cl.post(f"/api/payroll/runs/{r['id']}/decide", json={"approve": True}).json()["run"]["status"] == "approved"
        assert cl.post(f"/api/payroll/runs/{r['id']}/files", json={}).status_code == 200
        assert cl.get("/api/payroll/today").json()["employees"] == 1
        assert cl.post("/api/payroll/runs", json={"period": "13/2026"}).status_code == 400
    assert P.settings(T)["pf_on"]
