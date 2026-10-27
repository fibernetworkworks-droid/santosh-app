"""v0.98 Bima Sahayak: grace / lapse / revival rules, client + policy book, renewal reminders (drafts she sends),
premium paid moves the due date, needs analysis, quote comparison that waits for her Haan, renewal-list import,
claims with IRDAI timelines, morning note, Excel book, tools + API."""
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)


@pytest.fixture
def ins(env, monkeypatch):
    from app.insure import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    return S


def test_rules():
    from app.insure import rules as R
    assert R.grace_days("monthly") == 15 and R.grace_days("Yly") == 30 and R.mode_of("HLY") == "half_yearly"
    assert R.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert R.next_due_after(date(2020, 11, 5), "yearly", DAY) == date(2026, 11, 5)
    assert R.premium_state(date(2026, 11, 5), "yearly", "term", DAY)["state"] == "due"
    g = R.premium_state(date(2026, 10, 15), "monthly", "term", DAY)
    assert g["state"] == "grace" and g["days_left"] == 8
    assert R.premium_state(date(2026, 10, 1), "monthly", "term", DAY)["state"] == "lapsed"
    assert R.premium_state(date(2026, 9, 1), "yearly", "ulip", DAY)["revive_by"] == "2029-09-01"
    assert R.premium_state(date(2020, 1, 1), "yearly", "endowment", DAY)["state"] == "lapsed_final"
    life = R.life_cover_need(1000000, 35, 2000000, 1000000, 5000000, 0)
    assert life["need"] == 18000000 and life["gap"] == 13000000
    assert R.life_cover_need(1000000, 45)["multiple"] == 12
    h = R.health_cover_need(4, True, 58, 500000)
    assert h["need"] == 2250000 and h["gap"] == 1750000
    assert R.gst_on("term") == 0 and R.gst_on("health") == 0 and R.gst_on("motor") == 18 and R.gst_on("health", group=True) == 18
    d = R.health_deduction(30000, 60000, False, True)
    assert d["self"] == 25000 and d["parents"] == 50000 and "old regime" in d["note"]


def test_book_renewals_paid_lapse(ins):
    S = ins
    c = S.save_client(T, "Ramesh Patil", phone="98765 43210", dob="12-03-1988", city="Pune", income=1200000,
                      family=[{"name": "Sunita", "relation": "wife", "dob": "1990-05-01"}, {"name": "Aarav", "relation": "son"}])["client"]
    assert c["age"] == 38 and c["metro"]
    p1 = S.save_policy(T, "Ramesh", "LIC", "Jeevan Amar", "", "LIC123", "05-11-2020", "yearly", 15000, 10000000, nominee="Sunita")["policy"]
    assert p1["type"] == "term" and p1["next_due"] == "2026-11-05" and p1["gst_pct"] == 0
    p2 = S.save_policy(T, "9876543210", "Star Health", "Family Optima", "", "STAR9", "2025-10-10", "monthly", 2500, 500000, next_due="2026-10-15")
    assert p2["policy"]["type"] == "health" and p2["policy"]["premium_state"]["state"] == "grace" and "Nominee" in p2["say"]
    S.save_policy(T, "Ramesh", "HDFC Life", "Sanchay Plus", "endowment", "HD1", "2019-08-01", "yearly", 50000, 600000, next_due="2026-08-01",
                  nominee="Sunita")
    r = S.renewals(T, 15)
    assert [p["number"] for p in r["due"]] == ["LIC123"] and [p["number"] for p in r["grace"]] == ["STAR9"]
    assert [p["number"] for p in r["lapsed"]] == ["HD1"] and r["lapsed"][0]["premium_state"]["revive_by"] == "2031-08-01"
    d = S.reminder_drafts(T, 15)["drafts"]
    assert len(d) == 3 and all(x["to"] == "9876543210" for x in d)
    assert "grace period" in next(x for x in d if x["state"] == "grace")["text"]
    assert "revive" in next(x for x in d if x["state"] == "lapsed")["text"]
    S.save_client(T, client="Ramesh", whatsapp_ok=False)
    assert S.reminder_drafts(T, 15)["drafts"] == []
    assert S.mark_lapsed(T) == 1
    hd = S.policies(T, state="lapsed")
    assert hd[0]["status"] == "lapsed"
    paid = S.premium_paid(T, "HD1")["policy"]
    assert paid["next_due"] == "2027-08-01" and paid["status"] == "inforce"
    assert S.premium_paid(T, p2["policy"]["id"])["policy"]["next_due"] == "2026-11-15"
    b = S.book(T)
    assert b["inforce"] == 3 and b["yearly_premium"] == 15000 + 30000 + 50000
    with pytest.raises(S.InsError):
        S.save_policy(T, "Ramesh", pay_link="http://evil.example/pay")
    with pytest.raises(S.InsError):
        S.save_policy(T, "Nobody", "LIC", "x", number="Z1")


def test_needs_recommend_haan(ins):
    S = ins
    S.save_client(T, "Patil Ji", phone="9000000001", dob="1986-01-01", city="Nashik", income=1000000, liabilities=2000000,
                  family=[{"name": "A", "relation": "wife"}, {"name": "B", "relation": "son"}, {"name": "C", "relation": "mother", "dob": "1958-02-01"}])
    S.save_policy(T, "Patil", "LIC", "Tech Term", "term", "T1", "2022-01-01", "yearly", 9000, 5000000)
    n = S.needs(T, "Patil")
    assert n["life"]["multiple"] == 12 and n["life"]["need"] == 14000000 and n["life"]["gap"] == 9000000
    assert n["health"]["need"] == 1500000 and any("Nominee" in g for g in n["gaps"]) and any("accident" in g for g in n["gaps"])
    with pytest.raises(S.InsError):
        S.recommend(T, "Patil", [{"insurer": "X"}])
    r = S.recommend(T, "Patil", [{"insurer": "HDFC Life", "plan": "Click 2 Protect", "premium": 14000, "cover": 10000000, "csr": 99.5},
                                 {"insurer": "ICICI Pru", "plan": "iProtect Smart", "premium": 13000, "cover": 10000000, "csr": 99.2},
                                 {"insurer": "LIC", "plan": "Jeevan Labh", "premium": 60000, "cover": 1000000}])
    assert r["options"][0]["insurer"] == "ICICI Pru" and r["options"][0]["per_lakh"] == 130 and "IRDAI" in r["say"] and "haan" in r["say"]
    a = S.approve_advice(T, r["advice_id"])
    assert a["to"] == "9000000001" and "free-look" in a["draft"] and "GST nahi" in a["draft"]
    ck = S.proposal_checklist("term", 46)
    assert any("Medical" in d for d in ck["documents"]) and any("45+" in t for t in ck["tips"]) and ck["never"]
    assert any("Need analysis" in d for d in S.proposal_checklist("ulip")["documents"])


def test_import_claims_morning(ins):
    S = ins
    csv = ("LIC Premium Due List,,,,,\nPolicy No,Customer Name,Mobile,Plan,Mode,Inst. Premium,FUP,Sum Assured\n"
           "111,Kavita Joshi,9811111111,Jeevan Anand,Hly,6000,01/11/2026,500000\n"
           "222,Kavita Joshi,9811111111,Jeevan Umang,Yly,24000,2026-10-10,1000000\n"
           "333,Mohan Das,,New Endowment,Qly,3000,15/12/2026,200000\n,,,,,,,\n")
    r = S.import_policies(T, data=csv.encode(), name="due.csv", insurer="LIC")
    assert r["added"] == 3 and not r["errors"], r
    assert len(S.clients(T)) == 2
    again = S.import_policies(T, data=csv.encode(), name="due.csv", insurer="LIC")
    assert again["updated"] == 3 and len(S.policies(T)) == 3
    k = S.policies(T, "Kavita")
    assert {p["mode"] for p in k} == {"half_yearly", "yearly"} and all(p["insurer"] == "LIC" for p in k)
    with pytest.raises(S.InsError):
        S.import_policies(T, data=b"a,b\n1,2\n", name="x.csv")
    cl = S.start_claim(T, "111", "health hospital bill", "2026-10-01", 80000)
    assert "Discharge summary" in cl["documents"] and "15 din" in cl["say"]
    u = S.update_claim(T, cl["claim_id"], have=["claim form", "discharge", "asli bill"], filed_on="2026-10-01")
    assert "Claim form" not in u["missing"] and u["status"] == "filed"
    c = S.claims(T)[0]
    assert c["overdue"] and "Ombudsman" in c["escalate"]
    S.update_claim(T, cl["claim_id"], status="settled", settled_amount=72000)
    assert S.claims(T) == [] and S.claims(T, False)[0]["status"] == "settled"
    S.save_client(T, client="Mohan", dob=DAY.replace(year=1970).isoformat())
    assert S.birthdays(T, 0)["birthdays"][0]["client"] == "Mohan Das"
    m = S.send_morning(T)
    assert "Bima" in m["text"] and "Mohan Das" in m["text"]
    f = S.book_file(T)
    assert f["file"]["name"].endswith(".xlsx")


def test_tools_api(ins):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("bima") == "insurance_work" and roles.kind_of("bima_dekho") == "read" and "bima" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["insurance"]["role"] == "insurance_agent"
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    run("bima", action="client", name="Geeta Rao", phone="9822222222", income=800000, dob="1980-06-01")
    p = run("bima", action="policy", client="Geeta", insurer="Niva Bupa", plan="ReAssure", number="NB1", start="2025-11-01", mode="yearly",
            premium=18000, cover=1000000)["policy"]
    assert run("bima_dekho", what="renewals", days=15)["due"][0]["number"] == "NB1"
    assert run("bima_dekho", what="tax", self_premium=18000)["self"] == 18000
    rec = run("bima", action="recommend", client="Geeta", options=[{"insurer": "Tata AIA", "plan": "Sampoorna Raksha", "premium": 12000, "cover": 5000000}])
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["bima"](staff, action="approve", advice_id=rec["advice_id"]))
    with TestClient(main.app) as cl:
        assert "insurance" in cl.get("/healthz").json()["features"]
        s = cl.get("/api/insurance/summary").json()
        assert s["book"]["inforce"] == 1 and s["renewals"]["due"]
        assert cl.post(f"/api/insurance/policies/{p['id']}/paid", json={}).json()["policy"]["next_due"] == "2027-11-01"
        assert cl.post("/api/insurance/clients", json={"name": ""}).status_code == 400
        assert cl.post("/api/insurance/clients", json={"name": "Raju", "phone": "9833333333"}).status_code == 200
        up = cl.post("/api/insurance/import", files={"file": ("d.csv", b"Policy No,Name\n9,Raju\n", "text/csv")})
        assert up.status_code == 200 and up.json()["added"] == 1
        assert cl.post(f"/api/insurance/advice/{rec['advice_id']}", json={"approve": True}).json()["to"] == "9822222222"
        c = cl.post("/api/insurance/claims", json={"policy": "NB1", "kind": "health_cashless"}).json()
        assert "1 ghante" in c["say"]
        assert cl.post(f"/api/insurance/claims/{c['claim_id']}", json={"have": ["health card"]}).status_code == 200
        assert cl.get("/api/insurance/reminders").status_code == 200
        assert cl.get(f"/api/insurance/clients/{p['client_id']}/needs").json()["life"]
        assert cl.post("/api/insurance/book_file", json={}).status_code == 200
        assert cl.post("/api/insurance/settings", json={"agent_name": "Meghana"}).json()["agent_name"] == "Meghana"
