"""Society Sahayak: Maharashtra caps (non-occupancy 10%, interest 12%, sinking / repair minimums), bill lines by her heads,
interest on overdue principal, GST test (Rs 7,500 AND Rs 20 lakh), quorum / notice days, bills / notices / messages / spends /
penalties that ONLY her tap (card hash; fingerprint for spends) decides, receipts oldest-first + advance, dues and defaulters,
meetings with quorum, resolutions and minutes, vendors / AMC, staff, visitor purge, transfers, parking, tools and API."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.society.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def so(env, monkeypatch):
    from app.society import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_ai", lambda system, text: "")
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _setup(S, n=3):
    S.save_settings(T, name="Shanti CHS Ltd", reg_no="MUM/WR/HSG/1234", state="MH", upi_id="shantichs@okbank", noc_pct=10,
                    interest_pct=12, due_days=15)
    S.set_head(T, "service", 1500)
    S.set_head(T, "water", 100)
    S.set_head(T, "sinking", 0.25)
    S.set_head(T, "repair", 0.75)
    S.set_head(T, "parking", {"car": 500})
    for i in range(1, n + 1):
        S.save_flat(T, f"A-10{i}", owner_name=f"Member {i}", owner_phone=f"98765432{i:02d}", carpet_sqft=600, taps=2,
                    cost=2400000)


def test_rules():
    from app.society import rules as R
    assert R.unit_key("a 101") == "A-101" and R.unit_key("B/202") == "B-202" and R.unit_key("flat 7") == "7"
    assert R.phone10("+91 98765 43210") == "9876543210" and R.phone10("12345") == ""
    heads = [{"key": "service", "basis": "per_flat", "rate": 1000, "service": True},
             {"key": "sinking", "basis": "fund_pct", "rate": 0.2, "fund": "sinking"}]
    block, _ = R.check_heads(heads, "MH", 11, 15)
    assert len(block) == 3                                       # noc > 10, interest > 12, sinking < 0.25
    assert R.check_heads(heads, "KA", 11, 15)[0] == []           # other states: her bye-laws, no MH caps
    flat = {"carpet_sqft": 500, "taps": 3, "lift": True, "parking": [{"kind": "car"}], "cost": 1_200_000_00, "occupancy": "tenant"}
    hs = [{"key": "service", "label": "Service", "basis": "per_flat", "rate": 1000, "service": True},
          {"key": "water", "label": "Water", "basis": "per_tap", "rate": 50},
          {"key": "sinking", "label": "Sinking", "basis": "fund_pct", "rate": 0.25, "fund": "sinking"},
          {"key": "tax", "label": "Property tax", "basis": "area_share", "rate": 10000, "agent": True},
          {"key": "parking", "label": "Parking", "basis": "parking", "rate": {"car": 300}},
          {"key": "insurance", "label": "Insurance", "basis": "area_share", "rate": None}]
    lines, probs = R.bill_lines(flat, hs, {"carpet_total": 2000}, 10)
    amt = {l["head"]: l["amount"] for l in lines}
    assert amt == {"service": 100000, "water": 15000, "sinking": 25000, "tax": 250000, "parking": 30000, "noc": 10000}
    lines2, probs2 = R.bill_lines({**flat, "cost": 0, "taps": None, "occupancy": "self"}, hs, {"carpet_total": 2000}, 10)
    assert "noc" not in {l["head"] for l in lines2} and len(probs2) == 2
    tot, rows = R.interest_on([{"number": "B1", "due_date": date(2026, 1, 1), "unpaid": 365_00}], 12, date(2027, 1, 1))
    assert tot == 4380 and rows[0]["days"] == 365
    assert R.interest_on([{"number": "B1", "due_date": date(2026, 1, 1), "unpaid": 100}], 0, date(2027, 1, 1))[0] == 0
    big = [{"head": "service", "amount": 800_000}, {"head": "tax", "amount": 200_000, "agent": True}]
    assert R.gst_lines(big, 10_000_000, False)[0] == 0 and "dono shart" in R.gst_lines(big, 10_000_000, False)[1]
    assert R.gst_lines(big, 300_000_000, True)[0] == 144_000
    assert R.gst_lines([{"head": "service", "amount": 700_000}], 300_000_000, True) == (0, "")
    assert R.quorum("agm", 250) == 20 and R.quorum("agm", 24) == 16 and R.quorum("committee", 0, 7) == 4
    assert R.clear_days(date(2026, 9, 1), date(2026, 9, 16)) == 14
    assert R.notice_check("agm", date(2026, 9, 10), date(2026, 9, 20), "MH")
    assert not R.notice_check("agm", date(2026, 9, 1), date(2026, 9, 20), "MH")
    assert any("30-09" in p for p in R.notice_check("agm", date(2026, 9, 20), date(2026, 10, 10), "MH"))
    assert R.repair_limit("MH", 24) == 10_000_000 and R.repair_limit("MH", 60) == 30_000_000 and R.repair_limit("KA", 60) is None
    assert R.tds_note(9_000_000, 2_000_000) and not R.tds_note(0, 2_000_000)
    assert R.category_of("lift band hai") == "lift" and R.urgent("lift mein fas gaye bachche")


def test_settings_caps_and_flats(so):
    S = so
    with pytest.raises(S.SocietyError):
        S.save_settings(T, state="MH", noc_pct=15)
    with pytest.raises(S.SocietyError):
        S.save_settings(T, state="MH", interest_pct=21)              # old 21% is no longer allowed (Rules 2026)
    with pytest.raises(S.SocietyError):
        S.save_settings(T, upi_id="not a vpa")
    with pytest.raises(S.SocietyError):
        S.save_settings(T, name="x", actor="staff:1")
    _setup(S, 2)
    with pytest.raises(S.SocietyError):
        S.set_head(T, "sinking", 0.1)
    f = S.flat_view(T, "a101")
    assert f["unit"] == "A-101" and f["owner_phone"] == "9876543201" and "nomination" in f["missing"]
    S.nominate(T, "A-101", "Asha", "beti", 60)
    with pytest.raises(S.SocietyError):
        S.nominate(T, "A-101", "Ravi", "beta", 50)                  # > 100%
    with pytest.raises(S.SocietyError):
        S.parking(T, "A-101", "P1")                                  # MH: GB resolution needed
    S.parking(T, "A-101", "P1", "car", "AGM 2026 res 7")
    with pytest.raises(S.SocietyError):
        S.parking(T, "A-102", "P1", "car", "AGM 2026 res 7")         # slot taken
    with pytest.raises(S.SocietyError):
        S.transfer(T, "A-102", "New Person", premium=30000)          # premium cap Rs 25,000
    tr = S.transfer(T, "A-102", "New Person", phone="9123456780", premium=25000)
    assert tr["flat"]["owner_name"] == "New Person" and "DPDP" in tr["say"]
    assert S.flat_view(T, "A-102")["history"][0]["owner"] == "Member 2"
    imp = S.import_flats(T, b"Flat No,Owner Name,Mobile,Carpet Area,Taps\nB-201,Kiran,9000000001,550,2\nB-202,Bad,123,500,1\n,,,\n")
    assert imp["added"] == 2 and imp["bad"]


def test_bills_cards_receipts_and_dues(so):
    S = so
    _setup(S, 3)
    S.save_flat(T, "", "A-103", occupancy="tenant", tenant_name="Kirayedar", tenant_phone="9111111111")
    S.parking(T, "A-101", "P1", "car", "res 7")
    out = S.make_bills(T, "2026-10")
    c = out["card"]
    assert out["status"] == "needs_tap" and c["kind"] == "bills" and c["data"]["count"] == 3 and "society_card" in kinds(S)
    bl = {b["unit"]: b for b in S.bills(T, "2026-10")}
    # 1500 service + 200 water + 0.25%/12 of 24 lakh (500) + 0.75%/12 (1500) = 3700; A-101 +500 parking; A-103 +150 NOC
    assert bl["A-102"]["total"] == 3700 and bl["A-101"]["total"] == 4200 and bl["A-103"]["total"] == 3850
    assert all(b["status"] == "draft" for b in bl.values())
    with pytest.raises(S.SocietyError):
        S.decide_card(T, c["id"], True, c["hash"])                 # tool path: no by_tap
    with pytest.raises(S.SocietyError):
        S.decide_card(T, c["id"], True, "nope", by_tap=True)
    # making the bills again makes the old card stale (drafts replaced)
    out2 = S.make_bills(T, "2026-10")
    assert S.decide_card(T, c["id"], True, c["hash"], by_tap=True)["card"]["status"] == "stale"
    c2 = out2["card"]
    d = S.decide_card(T, c2["id"], True, c2["hash"], via="self", by_tap=True)
    assert d["card"]["status"] == "approved" and len(d["bills"]) == 3
    wa = [x for x in d["bills"] if x["unit"] == "A-101"][0]
    assert "upi://pay?pa=shantichs%40okbank" in wa["text"] or "upi://pay?pa=shantichs@okbank" in wa["text"]
    assert wa["wa"].startswith("https://wa.me/919876543201")
    assert S.decide_card(T, c2["id"], False, c2["hash"], by_tap=True)["card"]["status"] == "approved"   # decided once
    with pytest.raises(S.SocietyError):
        S.make_bills(T, "2026-10")                                   # already issued this month
    # receipts: owner only, oldest bill first, extra = advance
    with pytest.raises(S.SocietyError):
        S.receive(T, "A-101", 1000, actor="staff:1")
    r = S.receive(T, "A-101", 5000, "upi", "UTR123456789")
    assert r["receipt"]["advance"] == 800 and r["flat"]["due"] == 0 and r["receipt"]["ref_tail"] == "6789"
    S.receive(T, "A-102", 1000, "cash")
    du = S.dues(T)
    assert du["total"] == 2700 + 3850 and {x["unit"] for x in du["flats"]} == {"A-102", "A-103"}
    big = S.receive(T, "A-103", 300000, "cash")
    assert big["warnings"] and "2 lakh" in big["warnings"][0]
    # interest next month on overdue principal; advance fills the new bill
    from app.db import session
    from app.society.models import SocietyBill
    with session() as s:
        for b in s.query(SocietyBill).all():
            b.due_date = (date.today() - timedelta(days=60)).isoformat()
    nxt = S.make_bills(T, "2026-11")
    b2 = {b["unit"]: b for b in S.bills(T, "2026-11")}
    assert b2["A-102"]["interest"] > 0 and b2["A-101"]["interest"] == 0
    S.decide_card(T, nxt["card"]["id"], True, nxt["card"]["hash"], by_tap=True)
    assert {b["unit"]: b for b in S.bills(T, "2026-11")}["A-101"]["paid"] == 800      # advance used
    # reminders = message card; no_messages members skipped
    S.save_flat(T, "", "A-102", no_messages=True)
    with pytest.raises(S.SocietyError):
        S.remind(T, ["A-102"])
    rm = S.remind(T)
    assert rm["status"] == "needs_tap" and rm["card"]["kind"] == "message"
    dm = S.decide_card(T, rm["card"]["id"], True, rm["card"]["hash"], by_tap=True)
    assert dm["messages"] and dm["messages"][0]["wa"].startswith("https://wa.me/91")
    with pytest.raises(S.SocietyError):
        S.message(T, ["A-101"], "Kal pani band [samay]")             # blanks never go
    acc = S.accounts(T)
    assert acc["income_total"] > 0 and acc["funds"]["sinking"]["collected"] > 0


def test_penalty_and_spends(so, monkeypatch):
    S = so
    _setup(S, 2)
    with pytest.raises(S.SocietyError):
        S.penalty_request(T, "A-101", "Gallery mein saaman", 500, "")          # no bye-law reference
    with pytest.raises(S.SocietyError):
        S.penalty_request(T, "A-101", "late payment fine", 500, "bye-law 71")   # delay = interest only
    p = S.penalty_request(T, "A-101", "Common passage mein saaman", 500, "GB res 2026/4")
    S.decide_card(T, p["card"]["id"], True, p["card"]["hash"], by_tap=True)
    out = S.make_bills(T, "2026-10")
    a101 = [b for b in S.bills(T, "2026-10") if b["unit"] == "A-101"][0]
    assert any(l["head"] == "penalty" and l["amount"] == 500 for l in a101["lines"])
    S.decide_card(T, out["card"]["id"], True, out["card"]["hash"], by_tap=True)
    # spends
    with pytest.raises(S.SocietyError):
        S.spend_request(T, "repair", "Terrace waterproofing", None)
    with pytest.raises(S.SocietyError):
        S.spend_request(T, "repair", "Lift motor", 50000, fund="sinking")       # sinking fund needs a GB resolution
    with pytest.raises(S.SocietyError):
        S.spend_request(T, "repair", "Terrace waterproofing", 150000)           # 2 members: limit Rs 1 lakh a year
    ok = S.spend_request(T, "repair", "Terrace waterproofing", 150000, vendor="Sai Builders", resolution_="SGM 12-10-2026 res 2")
    assert ok["status"] == "needs_tap" and any("TDS" in c for c in ok["card"]["data"]["checks"])
    sp = ok["card"]
    assert S.spend_request(T, "repair", "Terrace waterproofing", 150000, vendor="Sai Builders", resolution_="x")["existing"]
    with pytest.raises(S.SocietyError):
        S.spend_done(T, sp["data"]["id"])                                       # not approved yet
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.SocietyError) as e:
        S.decide_card(T, sp["id"], True, sp["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.challenge(T, sp["id"])
    assert ch["message"].startswith("hoola-approve|v1|default|society|")
    monkeypatch.setattr(S, "_verify_fingerprint", lambda *a, **k: None)
    d = S.decide_card(T, sp["id"], True, sp["hash"], by_tap=True)
    assert "Maine de diya" in d["say"]
    done = S.spend_done(T, sp["data"]["id"], 148000, "UTR 999")
    assert done["spend"]["status"] == "done"
    acc = S.accounts(T)
    assert acc["expenditure"]["Repair"] == 148000


def test_meetings_notices_and_minutes(so):
    S = so
    _setup(S, 3)
    on = S.today(T)
    m = S.meeting_plan(T, "agm", (on + timedelta(days=5)).isoformat(), "10:00", "Club house")
    assert m["meeting"]["quorum"] == 2 and m["problems"]                 # 2/3 of 3 members; notice too short
    n = S.notice_draft(T, "agm", meeting=m["meeting"]["id"])
    assert "Club house" in n["notice"]["body"] and n["notice"]["checks"]
    with pytest.raises(S.SocietyError):
        S.notice_send(T, n["notice"]["id"])                              # 14 clear days not met
    m2 = S.meeting_plan(T, "agm", (on + timedelta(days=17)).isoformat(), "10:00", "Club house")
    n2 = S.notice_draft(T, "agm", meeting=m2["meeting"]["id"])
    card = S.notice_send(T, n2["notice"]["id"])["card"]
    S.notice_edit(T, n2["notice"]["id"], body=n2["notice"]["body"] + "\nChai ka intezaam.")
    assert S.decide_card(T, card["id"], True, card["hash"], by_tap=True)["card"]["status"] == "stale"   # changed after the card
    card = S.notice_send(T, n2["notice"]["id"])["card"]
    d = S.decide_card(T, card["id"], True, card["hash"], by_tap=True)
    assert d["notice"]["status"] == "approved" and d["notice"]["issued_on"] and "Chai" in d["group_text"]
    blank = S.notice_draft(T, "circular", title="Pani", body="Kal [samay] se pani band")
    with pytest.raises(S.SocietyError):
        S.notice_send(T, blank["notice"]["id"])
    mid = m2["meeting"]["id"]
    adj = S.meeting_held(T, mid, present_count=1)
    assert adj["meeting"]["status"] == "adjourned"
    m3 = S.meeting_plan(T, "agm", (on + timedelta(days=20)).isoformat(), "10:00", "Club house")["meeting"]["id"]
    S.meeting_held(T, m3, present=["A-101", "A-102", "A-103"], chair="Chairman", notes="Hisaab padhe gaye")
    r = S.resolution(T, m3, "Audited accounts 2025-26 sweekar", "A-101", "A-102", 2, 1)
    assert r["meeting"]["resolutions"][0]["passed"]
    r2 = S.resolution(T, m3, "Naya gate", "A-101", "A-103", 1, 2)
    assert not r2["meeting"]["resolutions"][1]["passed"]
    S.meeting_held(T, m3, present=["A-101", "A-102", "A-103"], chair="Chairman", notes="Hisaab padhe gaye")
    fin = S.minutes_final(T, m3)
    assert fin["meeting"]["status"] == "minuted" and "PAARIT" in fin["meeting"]["minutes"]
    assert S.settings(T)["agm_done"]
    mn = S.notice_draft(T, "minutes", meeting=m3)
    assert "Resolution 1" in mn["notice"]["body"]
    # defaulters list only with real defaulters
    with pytest.raises(S.SocietyError):
        S.notice_draft(T, "defaulters")


def test_complaints_contracts_staff_visitors_tick(so):
    S = so
    _setup(S, 2)
    k = S.contract_save(T, "Otis Lifts", "lift", "9822000000", 60000, "year", "2025-11-01", (S.today(T) + timedelta(days=10)).isoformat())
    assert k["contract"]["days_left"] == 10
    c = S.complaint_new(T, "Lift band hai, bachche andar fas gaye", "A-101", actor="staff:9")
    assert c["complaint"]["category"] == "lift" and c["complaint"]["urgent"] and "ZAROORI" in c["say"]
    assert S.complaint_new(T, "Lift band hai, bachche andar fas gaye", "A-101")["existing"]
    u = S.complaint_update(T, c["complaint"]["number"], contract=k["contract"]["id"])
    assert u["complaint"]["status"] == "assigned" and u["vendor_draft"].startswith("https://wa.me/919822000000")
    with pytest.raises(S.SocietyError):
        S.complaint_update(T, c["complaint"]["id"], "closed", actor="staff:9")
    S.complaint_update(T, c["complaint"]["id"], "resolved", "motor badla")
    st = S.staff_save(T, "Ramesh", "guard", "SecureCo", phone="9000011111")
    assert st["staff"]["recheck_due"] and "Police" in st["say"]
    v = S.visit_in(T, "Courier boy", "A-102", "parcel", "9876501234", "MH12AB1234", "delivery", actor="staff:9")
    assert v["visit"]["phone"] == "XXXXXX1234"
    assert len(S.visits(T, inside_only=True)) == 1
    S.visit_out(T, v["visit"]["id"])
    from app.db import session
    from app.society.models import SocietyVisit
    with session() as s:
        s.add(SocietyVisit(tenant_id=T, name="Old", in_at=datetime.now(timezone.utc) - timedelta(days=120)))
    r = S.tick(datetime.now(timezone.utc))
    assert r["purged"] == 1 and r["alerts"] >= 2 and "society_alert" in kinds(S)
    assert S.tick(datetime.now(timezone.utc) + timedelta(minutes=1))["alerts"] == 0   # once each
    cal = S.calendar(T)
    assert any("AGM" in x["what"] for x in cal) and any("Otis" in x["what"] for x in cal)
    S.forget(T, "A-101", "history")
    reg = S.register_file(T)
    assert reg["file"]["file_id"]


def test_tools_and_api(so, monkeypatch):
    from app.agent import society_tools as ST
    from app.agent.tools import Ctx, ToolError
    S = so
    ctx = conv_ctx()
    asyncio.run(ST.society(ctx, "settings", name="Shanti CHS", state="MH", upi_id="shanti@okbank"))
    asyncio.run(ST.society(ctx, "head", key="service", rate=1200))
    asyncio.run(ST.society(ctx, "flat", unit="A-101", owner_name="Meera", owner_phone="9876500001", carpet_sqft=500))
    staff = Ctx(T, ctx.conversation_id, actor="staff:abc")
    with pytest.raises(ToolError):
        asyncio.run(ST.society(staff, "flat", unit="A-102"))
    with pytest.raises(ToolError):
        asyncio.run(ST.society(staff, "receipt", flat="A-101", amount=100))
    with pytest.raises(ToolError):
        asyncio.run(ST.society_dekho(Ctx(T, ctx.conversation_id, actor="customer:wa:1"), "dues"))
    b = asyncio.run(ST.society(staff, "bills"))
    assert b["status"] == "needs_tap"
    cpl = asyncio.run(ST.society(staff, "complaint", text="Pani nahi aa raha", flat="A-101"))
    assert cpl["complaint"]["category"] == "water"
    rd = asyncio.run(ST.society_dekho(ctx, "rules"))
    assert rd["never"] and rd["sources"] and rd["caps"]["noc_cap_pct"] == 10
    assert asyncio.run(ST.society_dekho(ctx, "cards"))["cards"]
    names = {t["name"] for t in ST.SOCIETY_TOOLS}
    assert names == set(ST.SOCIETY_HANDLERS) == set(ST.SOCIETY_LABELS)
    # API
    from app.society.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/society").status_code == 200
    assert c.put("/api/society/settings", json={"noc_pct": 20}).status_code == 400
    r = c.post("/api/society/flats", json={"unit": "A-102", "owner_name": "Kiran", "owner_phone": "9876500002"})
    assert r.status_code == 200 and r.json()["flat"]["unit"] == "A-102"
    assert c.post("/api/society/flats", json={"unit": "A-103", "owner_phone": "123"}).status_code == 400
    card = c.post("/api/society/bills", json={"period": "2026-10"}).json()["card"]
    assert c.post(f"/api/society/cards/{card['id']}/decide", json={"hash": card["hash"]}).status_code == 400
    assert c.post(f"/api/society/cards/{card['id']}/decide", json={"yes": True, "hash": "x"}).status_code == 400
    ok = c.post(f"/api/society/cards/{card['id']}/decide", json={"yes": True, "hash": card["hash"]})
    assert ok.status_code == 200 and ok.json()["card"]["status"] == "approved"
    fid = r.json()["flat"]["id"]
    rc = c.post(f"/api/society/flats/{fid}/receipt", json={"amount": 1200, "mode": "upi"})
    assert rc.status_code == 200 and rc.json()["flat"]["due"] == 0
    sp = c.post("/api/society/spends", json={"kind": "amc", "what": "Lift AMC", "amount": 30000}).json()["card"]
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    assert c.post(f"/api/society/cards/{sp['id']}/decide", json={"yes": True, "hash": sp["hash"]}).status_code == 428
    assert c.post(f"/api/society/cards/{sp['id']}/challenge").json()["message"].startswith("hoola-approve|v1|default|society|")
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    assert c.post(f"/api/society/cards/{sp['id']}/decide", json={"yes": True, "hash": sp["hash"]}).json()["card"]["status"] == "approved"
    up = c.post("/api/society/flats/import", files={"file": ("m.csv", b"Unit,Owner,Phone\nC-1,Asha,9000000009\n")})
    assert up.status_code == 200 and up.json()["added"] == 1
    for path in ("/api/society/dues", "/api/society/accounts", "/api/society/calendar", "/api/society/day", "/api/society/parking"):
        assert c.get(path).status_code == 200
