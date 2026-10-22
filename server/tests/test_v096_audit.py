"""v0.96 Auditor's Assistant: materiality (SA 320), analytics vs last year (SA 520), journal-entry tests (SA 240), cash
rules (Sec 34(3) / 221 / 219-220), TDS (Sec 393), Benford, MUS / random sampling with a seed (SA 530), confirmations
(SA 505) that wait for her Haan, learned explanations, query list, rep letter, working papers, applicability, tools + API."""
import asyncio
import math
import random

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v095_analyst import TB

T = "default"
TB_PREV = TB.replace("Sales,,1200000", "Sales,,1000000").replace("Salary,150000,", "Salary,60000,").replace(
    "Meghana Capital,,430000", "Meghana Capital,,140000")

DAYBOOK_ROWS = [
    # date, type, no, [(ledger, dr, cr)], narration, user, entered
    ("07-07-2025", "Payment", "P-1", [("Repairs", 15000, 0), ("Cash", 0, 15000)], "machine repair", "ravi", "07-07-2025"),
    ("08-07-2025", "Receipt", "R-1", [("Cash", 250000, 0), ("Walk-in Customer", 0, 250000)], "cash sale receipt", "ravi", "08-07-2025"),
    ("09-07-2025", "Receipt", "R-2", [("Cash", 25000, 0), ("Loan from Ramesh", 0, 25000)], "loan taken", "ravi", "09-07-2025"),
    ("01-06-2025", "Journal", "J-1", [("Sundry Expenses", 300000, 0), ("HDFC Bank", 0, 300000)], "", "ravi", "01-06-2025"),
    ("10-08-2025", "Payment", "P-2", [("Professional Fees", 60000, 0), ("HDFC Bank", 0, 60000)], "CA consultancy", "ravi", "10-08-2025"),
    ("12-08-2025", "Payment", "P-3", [("Office Furniture", 98000, 0), ("HDFC Bank", 0, 98000)], "chairs", "ravi", "12-08-2025"),
    ("20-08-2025", "Journal", "J-2", [("Rathod Steel", 45000, 0), ("Purchase", 0, 45000)], "rate difference", "ravi", "15-10-2025"),
    ("21-08-2025", "Payment", "P-4", [("Rathod Steel", 33333, 0), ("HDFC Bank", 0, 33333)], "part payment", "ravi", "21-08-2025"),
    ("21-08-2025", "Payment", "P-5", [("Rathod Steel", 33333, 0), ("HDFC Bank", 0, 33333)], "part payment", "ravi", "21-08-2025"),
    ("30-03-2026", "Journal", "J-3", [("Sales", 0, 200000), ("Sai Agencies", 200000, 0)], "year end sale", "boss", "30-03-2026"),
]


def daybook_csv(extra: int = 0, seed: int = 3) -> str:
    rows = ["Date,Voucher Type,Voucher No,Particulars,Debit,Credit,Narration,Entered By,Entry Date"]
    for d, t, n, lines, nar, u, eo in DAYBOOK_ROWS:
        for i, (led, dr, cr) in enumerate(lines):
            rows.append(f"{d if i == 0 else ''},{t if i == 0 else ''},{n if i == 0 else ''},{led},{dr or ''},{cr or ''},"
                        f"{nar if i == 0 else ''},{u if i == 0 else ''},{eo if i == 0 else ''}")
    rnd = random.Random(seed)
    for k in range(extra):
        amt = round(math.exp(rnd.uniform(math.log(100), math.log(900000))), 2)
        day = f"{(k % 27) + 1:02d}-{[4, 5, 6, 7, 8, 9, 10, 11, 12][k % 9]:02d}-2025"
        rows.append(f"{day},Sales,S-{k},Sai Agencies,{amt},,sale {k},ravi,{day}")
        rows.append(f",,,Sales,,{amt},,,")
    return "\n".join(rows) + "\n"


def test_rules():
    from app.audit import rules as R
    m = R.materiality(500000, 10000000, 8000000)
    assert m["benchmark"] == "pbt" and m["overall"] == 25000 and m["performance"] == 16250 and m["trivial"] == 1250
    assert R.materiality(-200000, 10000000)["benchmark"] == "revenue" and R.materiality(-200000, 10000000)["overall"] == 100000
    assert R.materiality(500000, 10000000, risk="high")["performance"] == 12500
    assert R.variance(150000, 60000, 16250)["flag"] and not R.variance(61000, 60000, 16250)["flag"]
    assert R.is_round(300000) and not R.is_round(300001) and not R.is_round(50000)
    assert R.just_below(98000, 100000) and not R.just_below(90000, 100000)
    rnd = random.Random(1)
    natural = [math.exp(rnd.uniform(math.log(10), math.log(1e6))) for _ in range(2000)]
    assert R.benford(natural)["ok"] is True
    fake = [rnd.uniform(9000, 9999) for _ in range(500)]
    b = R.benford(fake)
    assert b["ok"] is False and 9 in b["spikes"]
    assert R.benford([1, 2, 3])["ok"] is None
    items = [(f"V{i}", a) for i, a in enumerate([100000, 5000, 7000, 20000, 3000, 9000, 12000, 1500, 40000, 2500])]
    s1, s2 = R.mus_select(items, 30000, 95, 5), R.mus_select(items, 30000, 95, 5)
    assert s1 == s2 and "V0" in s1["key_items"] and s1["interval"] == 10000          # 100000 >= interval: always taken
    assert R.random_select([f"x{i}" for i in range(50)], 5, 9) == R.random_select([f"x{i}" for i in range(50)], 5, 9)
    assert R.tds_nature("Professional Fees")[0] == "professional" and R.tds_nature("Freight inward")[0] == "contractor"
    ta = R.tax_audit("business", 15e7, 3, 4, 2025)
    assert ta["required"] and ta["due"] == "2026-10-21" and "3CD" in ta["form"]
    assert not R.tax_audit("business", 8e7, 3, 4, 2025)["required"] and R.tax_audit("business", 2e7)["required"]
    assert "Form 26" in R.tax_audit("business", 2e7, fy_start=2026)["form"]
    assert R.tax_audit("profession", 6e6)["required"]
    from datetime import date
    assert not R.caro("private", 5e6, 5e6, 5e7, on=date(2026, 3, 31))["applies"]                 # small company
    assert R.caro("private", 15e7, 5e7, 150e7, on=date(2026, 3, 31))["applies"]
    assert R.caro("public", 1e6, 0, 1e6)["applies"] and not R.caro("opc", 0, 0, 0)["applies"]


def test_engagement_end_to_end(env, monkeypatch):
    from app.audit import service as A
    e = A.new_engagement(T, "Sai Fabrication", "tax", "2025-26", "firm", approval_limit=100000)["engagement"]
    out = A.import_tb(T, e["id"], data=TB.encode(), name="tb.csv")
    assert out["difference"] == 0 and out["materiality"]["benchmark"] == "pbt" and out["materiality"]["overall"] == 7500
    A.plan_materiality(T, e["id"], "revenue", 1.0)                                          # her choice: 1% of revenue
    A.import_tb(T, e["id"], data=TB_PREV.encode(), name="tb_prev.csv", previous=True)
    d = A.import_daybook(T, e["id"], data=daybook_csv().encode(), name="db.csv")
    assert d["lines"] == 20
    A.set_facts(T, e["id"], turnover=12e6, cash_receipts_pct=12, cash_payments_pct=3)
    r = A.run_tests(T, e["id"], conv_ctx().conversation_id)
    rules = {f["rule"] for f in r["findings"]}
    refs = {f["rule"]: f["ref"] for f in r["findings"]}
    assert {"variance", "holiday", "round", "below_limit", "backdated", "duplicate", "cash_payment", "cash_receipt",
            "cash_loan_taken", "tds_professional", "year_end", "no_narration"} <= rules, rules
    assert "Salary" in [f["ref"] for f in r["findings"] if f["rule"] == "variance"]
    assert "Repairs" in refs["cash_payment"] and "Walk-in" in refs["cash_receipt"]
    eng = A.get(T, e["id"])
    assert eng["facts"]["tax_audit"]["required"] and eng["status"] == "fieldwork"
    # she explains the Sunday entry and asks Hoola to remember: next run doesn't raise it
    hol = next(f for f in A.findings(T, e["id"]) if f["rule"] == "holiday")
    A.close_finding(T, hol["id"], "explained", "stock count day", remember=True)
    r2 = A.run_tests(T, e["id"])
    assert hol["ref"] not in {f["ref"] for f in r2["findings"] if f["rule"] == "holiday"}
    assert any(f["rule"] == "holiday" and f["status"] == "explained" for f in A.findings(T, e["id"]))
    # sampling is reproducible
    s1 = A.make_sample(T, e["id"], "", "mus")
    s2 = A.make_sample(T, e["id"], "", "mus")
    assert s1["items"] == s2["items"] and s1["count"] >= 1 and s1["seed"] == s2["seed"]
    rs = A.make_sample(T, e["id"], "payment", "random", size=2)
    assert rs["count"] == 2
    sm = A.samples(T, e["id"])
    A.sample_result(T, sm[0]["id"], "exception", "bill missing")
    assert any(f["rule"] == "vouching" for f in A.findings(T, e["id"]))
    # confirmations: drafts until her Haan
    c = A.make_confirmations(T, e["id"], min_amount=10000)
    assert c["count"] == 2
    letters = A.confirmation_letters(T, e["id"])["letters"]
    assert all(x["status"] == "draft" for x in letters) and "31-03-2026" in letters[0]["letter"]
    assert A.approve_confirmations(T, e["id"])["approved"] == 2
    debtor = next(x for x in letters if x["kind"] == "debtor")
    A.confirmation_reply(T, debtor["id"], 240000)
    assert any(f["rule"] == "confirm_diff" for f in A.findings(T, e["id"]))
    q = A.query_list(T, e["id"])
    assert q["count"] > 0 and "Sai Fabrication" in q["draft"]
    A.mark_asked(T, e["id"])
    assert not [f for f in A.findings(T, e["id"], "open") if f["level"] != "info"]
    assert "SA 580" in A.rep_letter(T, e["id"])["say"]
    wp = A.workpapers(T, e["id"])
    assert wp["file"]["name"].endswith(".xlsx")


def test_benford_on_daybook(env):
    from app.audit import service as A
    e = A.new_engagement(T, "Big Co", "statutory", "2025-26", "private")["engagement"]
    A.import_tb(T, e["id"], data=TB.encode(), name="tb.csv")
    A.import_daybook(T, e["id"], data=daybook_csv(400).encode(), name="db.csv")
    r = A.run_tests(T, e["id"])
    assert r["benford"]["n"] >= 300 and r["benford"]["ok"] in (True, False)
    eng = A.get(T, e["id"])
    assert "caro" in eng["facts"] and eng["facts"]["audit_trail"]


def test_tools_api(env):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("audit") == "audit_work" and roles.kind_of("audit_dekho") == "read" and "audit" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["audit_firm"]["role"] == "audit_assistant"
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    e = run("audit", action="start", client="Patil Traders", kind="tax", fy="2025-26")["engagement"]
    assert run("audit_dekho", what="tax_audit", kind="business", turnover=15e6, fy="2025-26")["required"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["audit"](staff, action="approve_confirmations", engagement=e["id"], approve=True))
    with TestClient(main.app) as cl:
        assert "audit" in cl.get("/healthz").json()["features"]
        up = cl.post(f"/api/audit/engagements/{e['id']}/upload/tb", files={"file": ("tb.csv", TB.encode(), "text/csv")})
        assert up.status_code == 200 and up.json()["materiality"]["overall"] > 0, up.text
        up = cl.post(f"/api/audit/engagements/{e['id']}/upload/daybook", files={"file": ("db.csv", daybook_csv().encode(), "text/csv")})
        assert up.json()["lines"] == 20
        r = cl.post(f"/api/audit/engagements/{e['id']}/run", json={}).json()
        assert r["findings"]
        fid = cl.get(f"/api/audit/engagements/{e['id']}/findings").json()["findings"][0]["id"]
        assert cl.post(f"/api/audit/findings/{fid}", json={"status": "explained", "note": "ok"}).status_code == 200
        assert cl.post(f"/api/audit/engagements/{e['id']}/workpapers", json={}).status_code == 200
        assert cl.get("/api/audit/engagements").json()["engagements"]
        assert cl.post(f"/api/audit/engagements/{e['id']}/bogus", json={}).status_code == 404
        assert cl.post(f"/api/audit/engagements/{e['id']}/upload/tb", files={"file": ("x.csv", b"a,b\n", "text/csv")}).status_code == 400
