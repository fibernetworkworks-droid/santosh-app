"""v0.95 Financial Analyst: Tally trial balance (detailed + condensed) -> P&L / balance sheet / ratios with benchmarks
and trends, learned ledger mapping, bank statement -> categories, burn, runway, recurring, 13-week forecast, learned
narration rules, receivables aging + reminder drafts, MSME 15 / 45-day risk with Sec 16 interest, loan check (EMI,
DSCR, Nayak), advance tax plan, MIS files, her Haan before sharing, alerts, tools + API."""
import asyncio
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
TB = """Particulars,Debit,Credit
Capital Account,,
Meghana Capital,,430000
Loans (Liability),,
HDFC Term Loan,,300000
Current Liabilities,,
Sundry Creditors,,
Rathod Steel,,150000
Duties & Taxes,,
GST Payable,,20000
Fixed Assets,,
Machinery,400000,
Current Assets,,
Sundry Debtors,,
Sai Agencies,250000,
Cash-in-Hand,,
Cash,20000,
Bank Accounts,,
HDFC Bank,80000,
Closing Stock,150000,
Opening Stock,100000,
Sales Accounts,,
Sales,,1200000
Purchase Accounts,,
Purchase,700000,
Direct Expenses,,
Wages,100000,
Indirect Expenses,,
Salary,150000,
Rent,60000,
Electricity,20000,
Depreciation,40000,
Interest on Loan,30000,
Grand Total,2100000,2100000
"""

CONDENSED = """Particulars,Closing Balance
Capital Account,500000 Cr
Current Liabilities,200000 Cr
Sundry Creditors,150000 Cr
Current Assets,500000 Dr
Sundry Debtors,300000 Dr
Bank Accounts,100000 Dr
Fixed Assets,300000 Dr
Sales Accounts,900000 Cr
Purchase Accounts,600000 Dr
Indirect Expenses,200000 Dr
"""


def _today(monkeypatch, d: date):
    monkeypatch.setattr("app.analyst.service.today", lambda t: d)


def _bank_csv():
    rows = ["Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance"]
    bal = 300000
    for m, sale in ((7, 200000), (8, 180000), (9, 170000)):
        for d, nar, out, inn in ((1, "NEFT CR SAI AGENCIES", 0, sale), (5, f"SALARY {m}", 150000, 0), (7, "RENT OFFICE", 30000, 0),
                                 (10, "NACH HDFC LOAN EMI", 20000, 0), (15, "UPI/RATHOD STEEL/PAY", 40000, 0), (20, "GST CPIN PAYMENT", 15000, 0)):
            bal += inn - out
            rows.append(f"{d:02d}/{m:02d}/2026,{nar},{out or ''},{inn or ''},{bal}")
    return "\n".join(rows) + "\n"


def test_rules():
    from app.analyst import rules as R
    assert R.classify("Sales") == "revenue" and R.classify("Interest on Loan") == "interest" and R.classify("Rent") == "indirect_exp"
    assert R.classify("x", "Sundry Debtors") == "debtors" and R.classify("Depreciation") == "depreciation"
    assert R.bank_category("NACH HDFC LOAN EMI", False) == "loan_emi" and R.bank_category("SALARY OCT", False) == "salary"
    assert R.bank_category("NEFT CR ABC", True) == "sales_receipt" and R.bank_category("GST CPIN 123", False) == "gst"
    assert R.emi(1000000, 12, 60) == 22244.45
    assert R.nayak_limit(10000000) == {"need": 2500000, "owner_margin": 500000, "bank_limit": 2000000, "applies": True}
    assert R.break_even(300000, 30) == 1000000
    assert R.msme_limit(None) == 15 and R.msme_limit(60) == 45 and R.msme_limit(30) == 30
    assert R.MSME_INTEREST == 17.25 and 1400 < R.msme_interest(100000, 30) < 1450
    assert R.tax_estimate(1000000, "firm")["tax"] == 312000 and R.tax_estimate(1000000, "individual")["tax"] == 0
    assert R.tax_estimate(1e7, "company")["tax"] == round(1e7 * 0.22 * 1.10 * 1.04)
    p = R.advance_tax_plan(100000, 2026, 20000, date(2026, 10, 22))
    assert p["next"]["due"] == "2026-12-15" and p["next"]["cumulative"] == 75000 and p["pay_by_next"] == 55000
    assert p["installments"][1]["short"] == 25000                                  # 45,000 due by 15 Sep, 20,000 paid
    assert not R.advance_tax_plan(9000, 2026)["needed"]


def test_books_ratios_trend_learning(env, monkeypatch):
    from app.analyst import service as F
    _today(monkeypatch, date(2026, 10, 22))
    F.save_settings(T, business="Sai Fabrication", entity="firm")
    a = F.import_books(T, "H1 2026-27", "2026-04-01", "2026-09-30", data=TB.encode(), name="tb.csv")
    pl, bs = a["pl"], a["bs"]
    assert pl["revenue"] == 1200000 and pl["cogs"] == 750000 and pl["gross_profit"] == 450000
    assert pl["opex"] == 230000 and pl["depreciation"] == 40000 and pl["interest"] == 30000 and pl["profit_before_tax"] == 150000
    assert bs["debtors"] == 250000 and bs["creditors"] == 150000 and bs["loans"] == 300000 and bs["cash_bank"] == 100000
    r = {x["key"]: x for x in a["ratios"]}
    assert r["gross_margin"]["value"] == 37.5 and r["current_ratio"]["value"] == round(500000 / 170000, 2)
    assert r["current_ratio"]["verdict"] == "good" and r["debtor_days"]["value"] == round(250000 * 183 / 1200000, 2)
    assert "unknown" not in a
    # condensed export: parents minus their sub-groups
    c = F.import_books(T, "FY 2025-26", "2025-04-01", "2026-03-31", data=CONDENSED.encode(), name="tbc.csv")
    assert c["pl"]["revenue"] == 900000 and c["bs"]["debtors"] == 300000 and c["bs"]["current_assets"] == 500000
    assert c["bs"]["creditors"] == 150000 and c["bs"]["current_liabilities"] == 200000
    # trend: H1 vs FY 2025-26 (scaled by days)
    a2 = F.analyse(T, a["snapshot"]["id"])
    assert a2["trend"]["revenue"] is not None
    # her correction is remembered
    bad = TB.replace("Electricity,20000,", "Mystery Ledger,20000,").replace("Indirect Expenses,,\n", "")
    b = F.import_books(T, "Test", "2026-04-01", "2026-09-30", data=bad.encode(), name="tb.csv")
    assert "Mystery Ledger" in b.get("unknown", []) or b["pl"]["opex"] != 230000
    F.map_ledger(T, "Mystery Ledger", "indirect_exp")
    b2 = F.import_books(T, "Test2", "2026-04-01", "2026-09-30", data=bad.encode(), name="tb.csv")
    assert "Mystery Ledger" not in b2.get("unknown", [])
    with pytest.raises(F.FinError):
        F.import_books(T, "x", "2026-04-01", "2026-09-30", data=b"hello,world\n1,2\n", name="x.csv")


def test_bank_cash_forecast_learning(env, monkeypatch):
    from app.analyst import service as F
    _today(monkeypatch, date(2026, 10, 2))
    out = F.import_bank(T, data=_bank_csv().encode(), name="hdfc.csv", account="HDFC")
    assert out["imported"] == 18 and out["balance"] == 300000 + 550000 - 3 * 255000
    cats = {x["category"] for x in out["recurring"]}
    assert {"salary", "rent", "loan_emi", "gst"} <= cats
    assert out["avg_out"] == 255000 and out["runway_months"] is not None and len(out["forecast"]) == 13
    again = F.import_bank(T, data=_bank_csv().encode(), name="hdfc.csv", account="HDFC")
    assert again["imported"] == 0 and again["duplicates"] == 18
    r = F.set_category(T, "rathod steel", "raw_material")
    assert r["updated"] == 3 and all(t["category"] == "raw_material" for t in F.txns(T, "raw_material"))
    F.save_settings(T, budget={"rent": 25000})
    c = F.cash(T)
    assert c["budget_vs_actual"][0]["diff"] == 5000


def test_receivables_msme_loan_tax_report_share(env, monkeypatch):
    from app.analyst import service as F
    on = date(2026, 10, 22)
    _today(monkeypatch, on)
    F.save_settings(T, business="Sai Fabrication", entity="firm", tax_paid=20000)
    F.add_item(T, "receivable", "Sai Agencies", 150000, "S-101", (on - timedelta(days=75)).isoformat(), 30, "9822000001")
    F.add_item(T, "receivable", "Hari Traders", 50000, "S-120", (on - timedelta(days=10)).isoformat(), 30)
    ag = F.aging(T, "receivable")
    assert ag["buckets"]["61-90"] == 150000 and ag["buckets"]["0-30"] == 50000 and ag["items"][0]["overdue_days"] == 45
    d = F.reminder_drafts(T)["drafts"]
    assert len(d) == 1 and d[0]["to"] == "9822000001" and "S-101" in d[0]["text"]
    F.add_item(T, "payable", "Small Castings (MSE)", 100000, "P-9", (on - timedelta(days=40)).isoformat(), msme=True)
    F.add_item(T, "payable", "Agreed MSE", 50000, "P-10", (on - timedelta(days=40)).isoformat(), msme=True, agreed_days=60)
    p = F.aging(T, "payable")
    risk = {x["party"]: x for x in p["items"]}
    assert risk["Small Castings (MSE)"]["msme_days_left"] == -25 and risk["Small Castings (MSE)"]["msme_interest"] > 0
    assert risk["Agreed MSE"]["msme_last_day"] == (on - timedelta(days=40) + timedelta(days=45)).isoformat()
    assert "Sec 37(2)(g)" in risk["Small Castings (MSE)"]["tax_risk"]
    al = F.alerts(T)
    assert any("Agreed MSE" in x for x in al["alerts"]) and any("30+ din" in x for x in al["alerts"])
    F.import_books(T, "H1 2026-27", "2026-04-01", "2026-09-30", data=TB.encode(), name="tb.csv")
    F.add_loan(T, "HDFC Term", 300000, 11, 10000, 36)
    lc = F.loan_check(T, 1000000, 12, 5)
    assert lc["emi"] == 22244.45 and lc["dscr_after"] is not None and lc["nayak"]["bank_limit"] > 0 and "salah nahi" in lc["say"]
    at = F.advance_tax(T)
    assert at["entity"] == "firm" and at["plan"]["needed"] and at["paid"] == 20000
    conv = conv_ctx().conversation_id
    rep = F.report(T, conv=conv)
    assert {f["name"].rsplit(".", 1)[1] for f in rep["files"]} == {"xlsx", "pdf"}
    sh = F.approve_share(T, "H1 2026-27", True, "bank@x.com")
    assert sh["approved"] and "MIS" in sh["draft"]


def test_tools_api(env, monkeypatch):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    _today(monkeypatch, date(2026, 10, 22))
    assert roles.duty_of("paisa") == "finance_analysis" and roles.kind_of("paisa_dekho") == "read" and "paisa" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["finance"]["role"] == "financial_analyst"
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    out = run("paisa", action="figures", label="Q2", start="2026-07-01", end="2026-09-30",
              figures={"revenue": 600000, "purchases": 400000, "indirect_exp": 100000, "debtors": 200000, "creditors": 100000,
                       "bank": 50000, "capital": 300000})
    assert out["pl"]["profit_before_tax"] == 100000
    assert run("paisa_dekho", what="emi", amount=1000000, rate=12, years=5)["emi"] == 22244.45
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["paisa"](staff, action="share", snapshot="Q2", approve=True))
    with TestClient(main.app) as cl:
        assert "finance" in cl.get("/healthz").json()["features"]
        up = cl.post("/api/finance/bank", files={"file": ("s.csv", _bank_csv().encode(), "text/csv")}, data={"account": "HDFC"})
        assert up.status_code == 200, up.text
        assert cl.get("/api/finance/cash").json()["balance"] > 0
        assert cl.get("/api/finance/analysis").json()["pl"]["revenue"] == 600000
        tb = cl.post("/api/finance/books", files={"file": ("tb.csv", TB.encode(), "text/csv")},
                     data={"label": "H1", "start": "2026-04-01", "end": "2026-09-30"})
        assert tb.status_code == 200 and tb.json()["pl"]["revenue"] == 1200000
        assert cl.post("/api/finance/items", json={"kind": "receivable", "party": "A", "amount": 1000}).status_code == 200
        assert cl.get("/api/finance/aging", params={"kind": "receivable"}).json()["total"] == 1000
        assert cl.post("/api/finance/loan_check", json={"amount": 500000, "rate": 11, "years": 3}).json()["emi"] > 0
        assert cl.get("/api/finance/periods").json()["periods"]
        assert cl.post("/api/finance/books", files={"file": ("x.csv", b"a,b\n", "text/csv")},
                       data={"label": "x", "start": "2026-04-01", "end": "2026-09-30"}).status_code == 400
