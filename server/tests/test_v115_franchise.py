"""v0.115 Franchise Sahayak: agreements + outlets, daily sales (typed / POS import) vs last week, costs, royalty statement
(minimum guarantee, marketing, tech fee, GST forward / RCM, TDS once the year crosses Rs 50,000), her Haan for the report,
paid, outlet P&L with ratio flags + break-even, compare, FSSAI / licence windows, agreement / lease dates, SOP audits with
repeat misses, day note, tools + API."""
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)


@pytest.fixture
def fr(env, monkeypatch):
    from app.franchise import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    return S


def setup(S):
    S.save_settings(T, company="Ingle Foods LLP", state="27", tds_applies=True)
    S.save_agreement(T, "Chai Point", franchisor="Chai Point Pvt Ltd", contact="royalty@chaipoint.example", royalty_pct=6, marketing_pct=2,
                     tech_fee=2000, min_guarantee=30000, base="net", franchisor_state="29", due_day=10, start="2022-01-01", term_years=5,
                     lock_in_years=3, notice_months=6, checklist=["Floor clean", "Uniform", "Fridge temp log", "FIFO stock", "Hand wash"])
    S.save_outlet(T, "Koregaon Park", "Chai Point", "Pune", "2022-02-01", rent=85000, lease_end="2026-12-31", escalation_pct=5,
                  escalation_on="2026-11-15", manager_phone="9822222222")
    S.save_outlet(T, "Akola Station", "Chai Point", "Akola", rent=25000, targets={"food": 30})


def test_rules():
    from app.franchise import rules as R
    assert R.royalty(400000, 6, 30000) == {"calc": 24000.0, "min_topup": 6000.0, "royalty": 30000.0}
    assert R.royalty(1000000, 6, 30000)["min_topup"] == 0
    assert R.fee_gst(10000, True, False)["how"] == "rcm" and R.fee_gst(10000, False, True)["how"] == "cgst_sgst"
    assert R.tds_on_fee(0, 40000, True)["tds"] == 0
    assert R.tds_on_fee(40000, 20000, True)["tds"] == 6000.0           # crosses: whole year so far
    assert R.tds_on_fee(60000, 20000, True)["tds"] == 2000.0
    assert R.tds_on_fee(60000, 20000, False)["tds"] == 0
    assert R.flags({"food": 36.0, "staff": 15.0}, R.TARGETS) == ["Raw material / food cost 36.0% (lakshya 32%)"]
    assert R.break_even(100000, 50) == 200000
    assert R.licence_status("fssai", date(2026, 11, 10), DAY)["state"] == "late_window"
    assert R.licence_status("fssai", date(2027, 1, 30), DAY)["state"] == "renew_now"
    assert "3 guna" in R.licence_status("fssai", date(2026, 9, 1), DAY)["text"]
    assert "naya licence" in R.licence_status("fssai", date(2026, 1, 1), DAY)["text"]
    assert R.licence_status("trade", date(2027, 6, 1), DAY)["state"] == "ok"


def test_sales_statement_pnl(fr):
    S = fr
    setup(S)
    for d in range(1, 31):
        S.add_sale(T, "Koregaon", 30000 if d % 7 else 45000, f"2026-09-{d:02d}", orders=200)
        S.add_sale(T, "Akola", 9000, f"2026-09-{d:02d}", orders=90)
    r = S.add_sale(T, "Koregaon", 33000, "2026-10-21", orders=210)
    S.add_sale(T, "Koregaon", 30000, "2026-10-14")
    r = S.add_sale(T, "Koregaon", 33000, "2026-10-21", orders=210)
    assert r["vs_last_week"] == 10
    with pytest.raises(S.FrError):
        S.add_sale(T, "Koregaon", 100, "2026-10-25")
    st = S.statement(T, "Chai Point", "2026-09")
    d = st["statement"]
    kp = next(x for x in d["lines"] if x["outlet"] == "Koregaon Park")
    ak = next(x for x in d["lines"] if x["outlet"] == "Akola Station")
    assert kp["net"] == 26 * 30000 + 4 * 45000 and kp["royalty"] == round(kp["net"] * 0.06, 2) and kp["min_topup"] == 0
    assert ak["net"] == 270000 and ak["royalty"] == 30000 and ak["min_topup"] == 30000 - 16200
    assert d["gst"]["how"] == "igst" and d["gst"]["gst"] == round(d["fees"] * 0.18, 2)
    assert d["tds"]["applies"] and d["payable"] == round(d["fees"] + d["gst"]["gst"] - d["tds"]["tds"], 2)
    assert d["due"] == "2026-10-10" and st["file"]["name"].endswith(".xlsx") and "haan" in st["say"]
    ap = S.approve_statement(T, st["statement_id"])
    assert ap["to"] == "royalty@chaipoint.example" and "2026-09" in ap["text"]
    assert "26Q" in S.mark_paid(T, st["statement_id"])["say"]
    with pytest.raises(S.FrError):
        S.statement(T, "Chai Point", "2026-09")
    # costs + P&L
    S.add_cost(T, "Koregaon", "food", 330000, "2026-09")
    S.add_cost(T, "Koregaon", "staff", 140000, "2026-09")
    S.add_cost(T, "Koregaon", "swiggy commission", 60000, "2026-09")
    p = S.pnl(T, "Koregaon", "2026-09")
    assert p["costs"]["rent"] == 85000 and p["costs"]["aggregator"] == 60000 and p["ratios"]["food"] == round(330000 * 100 / 960000, 1)
    assert any("food" in f.lower() for f in p["flags"]) and p["break_even"] and p["profit"] == round(960000 - sum(p["costs"].values()), 2)
    cmp = S.compare(T, "2026-09")
    assert len(cmp["outlets"]) == 2 and "Sabse" in cmp["say"]
    assert S.pnl_file(T, "2026-09")["file"]["name"].endswith(".xlsx")


def test_import_licence_audit_day(fr):
    S = fr
    setup(S)
    csv = ("Petpooja Day Wise Report,,,,\nDate,Gross Sales,Discount,Total Tax,Net Sales,No of Bills\n"
           "20/10/2026,32000,2000,1500,30000,190\n21/10/2026,35000,1000,1700,34000,205\nTotal,67000,3000,3200,64000,395\n")
    r = S.import_sales(T, "Koregaon", csv.encode(), "pp.csv")
    assert r["days"] == 2, r
    with pytest.raises(S.FrError):
        S.import_sales(T, "Koregaon", b"a,b\n1,2\n", "x.csv")
    assert "Rs 100" in S.save_licence(T, "Koregaon", "fssai", "2026-11-10", "11521999000123")["say"]
    S.save_licence(T, "Akola", "fire noc", "2027-08-01")
    lic = S.licences(T)
    assert lic["due"][0]["kind"] == "fssai" and any(x["kind"] == "fire_noc" and x["state"] == "ok" for x in lic["licences"])
    w = S.dates_watch(T)
    assert {x["what"] for x in w} >= {"Koregaon Park: kiraya 5% badhega", "Koregaon Park: lease khatam"}
    for dd in ("2026-10-18", "2026-10-19", "2026-10-20"):
        S.audit(T, "Koregaon", ["fridge"], day=dd)
    a = S.audit(T, "Koregaon", ["uniform"])
    assert a["score"] == 80.0 and a["failed"] == ["Uniform"] and a["draft"]["to"] == "9822222222"
    assert "Fridge temp log" in S.audit(T, "Koregaon", ["fridge"])["repeat"]
    day = S.day(T)
    assert "Koregaon Park" in day["say"] and "licence" in day["say"]
    assert S.send_morning(T)["text"].startswith("Franchise:")
    with pytest.raises(S.FrError):
        S.save_agreement(T, "Bad", royalty_pct=55)


def test_tools_api(fr):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("franchise") == "franchise_work" and roles.kind_of("franchise_dekho") == "read" and "franchise" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["franchisee"]["role"] == "franchise_manager"
    S = fr
    setup(S)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    run("franchise", action="sale", outlet="Akola", net=12000, day="2026-09-05")
    st = run("franchise", action="statement", brand="Chai Point", month="2026-09")
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["franchise"](staff, action="approve_statement", statement_id=st["statement_id"]))
    assert run("franchise_dekho", what="statements")["statements"][0]["month"] == "2026-09"
    with TestClient(main.app) as cl:
        assert "franchise" in cl.get("/healthz").json()["features"]
        d = cl.get("/api/franchise/day").json()
        assert len(d["outlets"]) == 2 and d["agreements"][0]["brand"] == "Chai Point"
        assert cl.post(f"/api/franchise/statements/{st['statement_id']}/approve", json={}).json()["to"]
        assert cl.post("/api/franchise/sales", json={"outlet": "Koregaon", "net": 40000, "day": "2026-10-21"}).status_code == 200
        up = cl.post("/api/franchise/sales/import", data={"outlet": "Akola"},
                     files={"file": ("s.csv", b"Date,Net Sales\n2026-10-20,8000\n", "text/csv")})
        assert up.json()["days"] == 1, up.text
        assert cl.get("/api/franchise/pnl", params={"outlet": "Akola", "month": "2026-09"}).json()["sales"]["net"] == 12000
        assert cl.get("/api/franchise/bogus").status_code == 404
        assert cl.post("/api/franchise/sales", json={"outlet": "Nowhere", "net": 1}).status_code == 400
        assert cl.post("/api/franchise/licences", json={"outlet": "Akola", "kind": "fssai", "valid_to": "2027-05-01"}).status_code == 200
        assert cl.post("/api/franchise/audits", json={"outlet": "Akola", "failed": []}).json()["score"] == 100
