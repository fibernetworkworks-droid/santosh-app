"""Site Sahayak (construction site supervisor): rules (OT rounding, IS 456 sampling / acceptance, curing, Form XI clock,
checklists), site linked to a Theka project (plan from BOQ, delays into the hindrance diary, material mirror), labour attendance +
register numbers, material balance + indent card decided only by her tap (fingerprint path), safety checklist -> stop-work card,
incident register, pour + cubes, snags with EXIF-stripped photos, DPR card -> her tap -> wa.me / business, tick, tools, API."""
import asyncio
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.sitesup.models  # noqa: F401  (tables for the env fixture's init_db)
import app.theka.service  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)
BOQ = "Item No,Description of item,Unit,Qty,Rate\n1,Earthwork in excavation,cum,1000,250\n2,RCC M25 slab,cum,200,8500\n"


@pytest.fixture
def ss(env, monkeypatch, tmp_path):
    from app.sitesup import service as S
    from app.theka import service as TH
    monkeypatch.setattr(S, "today", lambda t: DAY)
    monkeypatch.setattr(TH, "today", lambda t: DAY)
    monkeypatch.setenv("SITESUP_DIR", str(tmp_path / "ss"))
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def make_site(S, theka=False):
    if theka:
        from app.theka import service as TH
        TH.save_project(T, "Akot school building", client="ZP Akola", govt=True, value=5000000, start="2026-09-01", end="2027-03-31")
        TH.boq(T, "school", data=BOQ.encode(), name="boq.csv")
    S.save_settings(T, firm="Ingle Constructions", supervisor="Patil", rates={"mason": 900, "helper": 550})
    r = S.save_site(T, "Akot school", client="ZP Akola", client_phone="9876543210", address="Akot, Akola 444101",
                    **({"theka_project": "school"} if theka else {}))
    return r["site"]


def test_rules():
    from app.sitesup import rules as R
    assert R.round_ot(0.2) == 0 and R.round_ot(0.25) == 0.5 and R.round_ot(0.5) == 0.5 and R.round_ot(0.6) == 1 and R.round_ot(2.4) == 2.5
    assert R.split_hours(10) == {"hours": 10.0, "normal": 8.0, "ot": 2.0} and R.split_hours(8.3)["ot"] == 0.5
    assert [R.samples_for(v) for v in (3, 5, 6, 15, 16, 30, 40, 50, 51, 100, 101)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6]
    assert R.curing_days("OPC 53") == 7 and R.curing_days("PPC") == 10 and R.curing_days("OPC", hot_dry=True) == 10
    assert R.cube_ages("OPC 53") == [7, 28] and 56 in R.cube_ages("PPC")
    assert R.judge_cubes("M25", 7, [17.5, 18.0, 17.0])["verdict"] == "indicative_ok"
    assert R.judge_cubes("M25", 7, [12, 13, 12.5])["verdict"] == "indicative_low"
    assert R.judge_cubes("M25", 28, [30.1, 29.5, 31.0])["verdict"] == "pass"
    assert R.judge_cubes("M25", 28, [30, 29, 20.5])["verdict"] == "fail"                       # one cube below fck - 4
    j = R.judge_cubes("M25", 28, [29.0, 29.5, 29.2], earlier_means=[28.0, 28.2, 28.4])        # mean of 4 < 25 + max(0.825*4, 4)
    assert j["verdict"] == "fail" and j["need_mean"] == 29.0
    assert R.judge_cubes("M25", 28, [30, 30, 30], limits={"individual_minus": 3, "mean_plus": 3})["need_individual"] == 22
    at = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
    assert R.report_due("death", at)[0] == at
    assert R.report_due("dangerous", at)[0] == at + timedelta(hours=12)
    assert R.report_due("injury", at)[0] == at + timedelta(hours=60)
    assert R.report_due("near_miss", at)[0] is None
    assert R.incident_kind("", "scaffold gir gaya, koi chot nahi") == "dangerous"
    assert R.incident_kind("", "beldar ka haath fracture, hospital le gaye") == "injury"
    assert R.trade_of("raj mistri") == "mason" and R.trade_of("beldar") == "helper" and R.trade_of("sariya wala bar bender") == "bar_bender"
    assert R.delay_kind("baarish se kaam ruka") == ("rain", False) and R.delay_kind("drawing nahi aayi")[1] is True
    res = R.checklist_result("scaffold", {"base": True, "bracing": False, "platform": True, "rails": True})
    assert res["unsafe"] == ["bracing"] and "tag" in res["unanswered"]
    st = R.activity_state(date(2026, 10, 1), date(2026, 10, 31), DAY, 30.0)
    assert st["state"] == "behind" and st["planned_pct"] > 60


def test_site_on_theka_plan_progress_labour_material(ss):
    S = ss
    site = make_site(S, theka=True)
    assert site["theka_project_id"] and site["theka"]["name"] == "Akot school building"
    p = S.plan(T, "", from_boq=True)
    assert p["added"] == 2
    S.plan(T, "", [{"code": "2", "name": "RCC M25 slab", "start": "2026-10-01", "finish": "2026-10-31", "qty": 200,
                    "needs": [{"item": "cement", "qty": 800, "unit": "bag"}]}])
    r = S.progress(T, "", "slab", 18, note="ground floor slab panel A")
    assert r["cumulative"] == 18 and "18" in r["say"]
    with pytest.raises(S.SiteError):
        S.progress(T, "", "slab", 5, day="2026-10-30")                          # future
    S.progress(T, "", "earthwork", 0, delay="baarish se kaam band", lost_hours=6)
    from app.theka import service as TH
    with TH.session() as s:
        from sqlalchemy import select
        rows = s.scalars(select(TH.ThekaDiary)).all()
        assert any("baarish" in r.hindrance for r in rows) and not any(r.by_client for r in rows if "baarish" in r.hindrance)
    acts = {a["code"]: a for a in S.activities(T)}
    assert acts["2"]["state"] == "behind" and acts["2"]["done_pct"] == 9.0 and "mb_done" in acts["2"]
    # labour: gang rows + named worker with OT; same row replaced, not doubled
    a = S.attendance(T, "", [{"contractor": "Ramesh", "trade": "beldar", "count": 12, "hours": 8},
                             {"contractor": "Ramesh", "trade": "mistri", "count": 2, "hours": 10},
                             {"worker": "Suresh Pawar", "trade": "bar bender", "contractor": "Ramesh", "hours": 9.4}])
    assert a["total"] == 15 and any("overtime" in w for w in a["warnings"])
    a = S.attendance(T, "", [{"contractor": "Ramesh", "trade": "beldar", "count": 10, "hours": 8}])
    assert a["total"] == 13
    reg = S.register(T, "", "2026-10-01", "2026-10-31")
    m = {(x["contractor"], x["trade"]): x for x in reg["lines"]}
    assert m[("Ramesh", "mason")]["ot_hours"] == 4.0 and m[("Ramesh", "mason")]["estimate"] == round(900 * 2 + 900 / 8 * 2 * 4, 2)
    assert m[("Ramesh", "bar_bender")]["ot_hours"] == 1.5 and m[("Ramesh", "helper")]["man_days"] == 10
    with TH.session() as s:
        from sqlalchemy import select
        d = s.scalars(select(TH.ThekaDiary).where(TH.ThekaDiary.day == DAY.isoformat())).first()
        assert d.labour == 13
    # material: receipt + use + balance, duplicate challan refused, can't use more than at site; mirrored into theka stock
    S.material(T, "", "cement", 200, "in", "bag", "Shree Traders", "554", "MH30AB1234")
    with pytest.raises(S.SiteError):
        S.material(T, "", "cement", 200, "in", "bag", challan="554")
    with pytest.raises(S.SiteError):
        S.material(T, "", "cement", 500, "used")
    r = S.material(T, "", "cement", 150, "used")
    assert r["balance"] == 50
    assert {x["item"]: x["balance"] for x in TH.stock(T, "school")}["cement"] == 50
    la = S.lookahead(T)
    assert any(sh["item"] == "cement" for a in la["coming"] for sh in a["short"]) and "indent" in la["say"]


def test_indent_card_only_her_tap_and_fingerprint(ss, monkeypatch):
    S = ss
    make_site(S)
    c = conv_ctx()
    from app.agent.sitesup_tools import SITESUP_HANDLERS as H
    from app.agent.tools import Ctx, ToolError
    r = asyncio.run(H["sitesup"](c, action="indent", items=[{"item": "cement", "qty": 100, "unit": "bag"}], need_by="2026-10-25",
                                 supplier="Shree Traders", supplier_phone="9822012345", amount=38000))
    ind = r["indent"]
    assert r["status"] == "needs_tap" and ind["status"] == "waiting" and "sitesup_indent" in kinds(S)
    again = S.indent_request(T, "", [{"item": "cement", "qty": 100, "unit": "bag"}])
    assert again["existing"]
    with pytest.raises(S.SiteError):
        S.decide_indent(T, ind["id"], True, ind["hash"])                 # not by tap
    with pytest.raises(S.SiteError):
        S.decide_indent(T, ind["id"], True, "wrong", by_tap=True)
    with pytest.raises(S.SiteError):
        S.indent_ordered(T, ind["id"])                                    # before her tap
    # fingerprint once a phone key is active: refused without proof, accepted with a good signature
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda t: True)
    with pytest.raises(S.SiteError) as e:
        S.decide_indent(T, ind["id"], True, ind["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.indent_challenge(T, ind["id"])
    assert "|sitesup|" in ch["message"]
    monkeypatch.setattr(ak, "_check", lambda s, tenant, kind, target, proof, digest: kind == "sitesup" and target == ind["id"] and digest == ind["hash"])
    d = S.decide_indent(T, ind["id"], True, ind["hash"], proof={"challenge_id": ch["challenge_id"], "device_id": "x", "signature": "y"}, by_tap=True)
    assert d["indent"]["status"] == "approved" and d["indent"]["wa"].startswith("https://wa.me/919822012345")
    S.indent_ordered(T, ind["id"])
    S.material(T, "", "cement", 100, "in", "bag", challan="771", indent=ind["number"])
    assert S.indents(T)[0]["status"] == "received"
    # a staff actor may raise an indent card but never decide; customers get nothing
    staff = Ctx(T, c.conversation_id, "staff:abc")
    asyncio.run(H["sitesup"](staff, action="indent", item="sand", qty=2, unit="brass"))
    with pytest.raises(ToolError):
        asyncio.run(H["sitesup"](staff, action="settings", firm="x"))
    with pytest.raises(ToolError):
        asyncio.run(H["sitesup_dekho"](Ctx(T, c.conversation_id, "customer:91"), what="day"))


def test_safety_stop_incident(ss):
    S = ss
    make_site(S)
    t = S.toolbox(T, "", "Unchai par harness", 20)
    assert "20 log" in t["say"]
    r = S.checklist(T, "", "height", {"edge": False, "openings": True, "harness": True, "ladder": True}, area="2nd floor slab edge")
    assert r["result"]["unsafe"] == ["edge"] and r["stop"]["status"] == "waiting" and "door hataiye" in r["say"]
    stop = r["stop"]
    with pytest.raises(S.SiteError):
        S.decide_stop(T, stop["id"], True, stop["hash"])
    d = S.decide_stop(T, stop["id"], True, stop["hash"], by_tap=True)
    assert d["stop"]["status"] == "active" and "BAND" in d["notice"]
    with pytest.raises(S.SiteError):
        S.lift_stop(T, stop["id"], "rail lag gayi")
    with pytest.raises(S.SiteError):
        S.lift_stop(T, stop["id"], "", by_tap=True)
    assert S.lift_stop(T, stop["id"], "Guard rail lag gayi, checklist 100%", by_tap=True)["stop"]["status"] == "lifted"
    # whole-site stop marks the site stopped
    w = S.stop_request(T, "", "Poori site", "Crane ka hook toota")["stop"]
    S.decide_stop(T, w["id"], True, w["hash"], by_tap=True)
    assert S.site_view(T)["status"] == "stopped"
    S.lift_stop(T, w["id"], "Naya hook, load test ho gaya", by_tap=True)
    assert S.site_view(T)["status"] == "running"
    inc = S.incident(T, "", "Shuttering staging gir gaya, 2 log ko chot", people=2, names="Ravi, Mohan", at="2026-10-22 11:00")
    v = inc["incident"]
    assert v["kind"] == "dangerous" and v["due_at"] and "Form XI" in inc["form_xi"] and inc["stop"]["status"] == "waiting"
    assert "sitesup_alert" in kinds(S)
    nm = S.incident(T, "", "Eent upar se giri, bal bal bache")
    assert nm["incident"]["kind"] == "near_miss" and not nm["incident"]["due_at"]
    with pytest.raises(S.SiteError):
        S.incident_reported(T, v["id"], "")
    assert S.incident_reported(T, v["id"], "Shram Suvidha ack 123")["incident"]["reported"]
    log = S.safety_log(T)
    assert {x["type"] for x in log} == {"talk", "check", "incident"}


def test_quality_pour_cubes_snags_photo(ss):
    S = ss
    make_site(S)
    p = S.pour(T, "", "1st floor slab", "M25", 32, "OPC 53", day="2026-09-24")
    pv = p["pour"]
    assert pv["samples"] == 4 and len(pv["cubes"]) == 8 and pv["curing_until"] == "2026-10-01" and "12 cube" in p["say"]
    c7 = S.cube_result(T, pv["number"], 7, [18.2, 17.9, 18.6])
    assert c7["judge"]["verdict"] == "indicative_ok"
    with pytest.raises(S.SiteError):
        S.cube_result(T, pv["number"], 28, [650, 640, 660])               # kN, not N/mm2
    c28 = S.cube_result(T, pv["number"], 28, [30.5, 31.0, 29.8], sample=1)
    assert c28["judge"]["verdict"] == "pass"
    bad = S.cube_result(T, pv["number"], 28, [24.0, 20.1, 25.0], sample=2)
    assert bad["judge"]["verdict"] == "fail" and "sitesup_alert" in kinds(S)
    due = S.cubes_due(T, 30)
    assert any(c["age"] == 28 and c["sample"] == 3 for c in due)
    sn = S.snag(T, "", "Plaster mein crack", "Flat 203 bedroom", contractor="Ramesh")["snag"]
    from PIL import Image
    im = Image.new("RGB", (40, 30), "red")
    exif = Image.Exif()
    exif[0x010F] = "SecretPhoneMaker"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif.tobytes())
    ph = S.add_photo(T, buf.getvalue(), "", sn["number"], "snag")
    raw = S.photo_bytes(T, ph["photo"])
    assert b"SecretPhoneMaker" not in raw and Image.open(io.BytesIO(raw)).getexif().get(0x010F) is None
    with pytest.raises(S.SiteError):
        S.snag_status(T, sn["id"], "verified")
    S.add_photo(T, buf.getvalue(), "", sn["id"], "fixed")
    assert S.snags(T)[0]["status"] == "fixed"
    assert S.snag_status(T, sn["id"], "verified")["snag"]["status"] == "verified"


def test_dpr_her_tap_then_wa_or_business(ss, monkeypatch):
    S = ss
    make_site(S)
    with pytest.raises(S.SiteError):
        S.dpr_request(T)                                                  # nothing logged today
    S.plan(T, "", [{"name": "Brickwork 230 mm", "unit": "cum", "qty": 100, "start": "2026-10-10", "finish": "2026-11-10"}])
    S.progress(T, "", "brickwork", 6.5, note="2nd floor")
    S.attendance(T, "", [{"contractor": "Ramesh", "trade": "mason", "count": 3}, {"contractor": "Ramesh", "trade": "helper", "count": 6}])
    S.toolbox(T, "", "Helmet", 9)
    r = S.dpr_request(T, "", weather="saaf", tomorrow="Brickwork jaari")
    rep = r["report"]
    assert r["status"] == "needs_tap" and rep["status"] == "waiting" and "Brickwork 230 mm: 6.5 cum" in rep["text"] and r["file"]["name"].endswith(".pdf")
    assert "Manpower: 9" in rep["text"] and "sitesup_report" in kinds(S)
    with pytest.raises(S.SiteError):
        asyncio.run(S.decide_report(T, rep["id"], True, rep["hash"]))     # tool / no tap
    # a newer DPR for the same day makes the old card stale
    r2 = S.dpr_request(T, "", weather="saaf", tomorrow="Brickwork + plaster")
    assert S.reports(T, status="stale")[0]["id"] == rep["id"]
    with pytest.raises(S.SiteError):
        asyncio.run(S.decide_report(T, r2["report"]["id"], True, rep["hash"], by_tap=True))
    ok = asyncio.run(S.decide_report(T, r2["report"]["id"], True, r2["report"]["hash"], by_tap=True))
    assert ok["report"]["status"] == "approved" and ok["report"]["wa"].startswith("https://wa.me/919876543210")
    assert S.report_sent(T, r2["report"]["id"])["report"]["status"] == "sent"
    # business WhatsApp needs a client who wrote to the business number
    m = S.message_request(T, "", "Kal subah 2nd floor ki drawing chahiye, kripya bhejiye.")["report"]
    with pytest.raises(S.SiteError):
        asyncio.run(S.decide_report(T, m["id"], True, m["hash"], "business", by_tap=True))
    from app.employee import inbox
    from app.employee.models import BizContact
    with S.session() as s:
        s.add(BizContact(tenant_id=T, wa_id="919876543210", name="ZP"))
    sent = []

    async def fake_send(tenant, cid, text, by="owner"):
        sent.append(text)
    monkeypatch.setattr(inbox, "send", fake_send)
    done = asyncio.run(S.decide_report(T, m["id"], True, m["hash"], "business", by_tap=True))
    assert done["report"]["status"] == "sent" and sent and "drawing" in sent[0]


def test_tick_day_api_and_forget(ss, monkeypatch):
    S = ss
    make_site(S)
    S.pour(T, "", "Footing F1", "M20", 4, "OPC", day=(DAY - timedelta(days=6)).isoformat())
    S.incident(T, "", "Scaffold ka ek hissa gira", at="2026-10-22 09:00")
    S.attendance(T, "", [{"contractor": "Apne", "trade": "helper", "count": 4}])
    from app.sitesup import service as SV
    monkeypatch.setattr(SV, "_tenants", lambda: [T])
    noon = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)          # 19:30 IST: after morning + dpr time
    out = S.tick(noon)
    assert out["morning"] == 1 and out["dpr"] == 1 and out["alerts"] >= 1
    says = " ".join(p.get("say", "") for k, p in S.EVENTS if k in ("sitesup_alert", "sitesup_day"))
    assert "7 din wale cube" in says and "DPR baaki" in says
    n = len(S.EVENTS)
    S.tick(noon + timedelta(minutes=1))
    assert len(S.EVENTS) == n                                             # once only
    late = S.tick(datetime(2026, 10, 23, 2, 0, tzinfo=timezone.utc))
    assert late["alerts"] >= 1 and any("samay nikal gaya" in p.get("say", "") for k, p in S.EVENTS)
    # API
    from app.sitesup.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(app)
    ov = cl.get("/api/sitesup").json()
    assert ov["sites"] and "height" in ov["checklists"]
    sid = ov["sites"][0]["id"]
    assert cl.get(f"/api/sitesup/sites/{sid}").json()["labour_today"]["total"] == 4
    ind = cl.post(f"/api/sitesup/sites/{sid}/indents", json={"items": [{"item": "steel 12mm", "qty": 2, "unit": "t"}], "amount": 130000}).json()["indent"]
    monkeypatch.setattr("app.approvekey.active_on", lambda t: True)
    assert cl.post(f"/api/sitesup/indents/{ind['id']}/decide", json={"yes": True, "hash": ind["hash"]}).status_code == 428
    assert cl.post(f"/api/sitesup/indents/{ind['id']}/decide", json={"yes": False, "hash": ind["hash"], "reason": "rate zyada"}).json()["indent"]["status"] == "rejected"
    st = cl.post(f"/api/sitesup/sites/{sid}/stops", json={"area": "Lift shaft", "reason": "Opening khula"}).json()["stop"]
    assert cl.post(f"/api/sitesup/stops/{st['id']}/decide", json={"yes": True, "hash": st["hash"]}).json()["stop"]["status"] == "active"
    rep = cl.post(f"/api/sitesup/sites/{sid}/dpr", json={}).json()["report"]
    assert cl.post(f"/api/sitesup/reports/{rep['id']}/decide", json={"yes": True, "hash": rep["hash"]}).json()["report"]["status"] == "approved"
    f = cl.post(f"/api/sitesup/sites/{sid}/register_file", json={}).json()
    assert f["file"]["name"].endswith(".xlsx")
    assert cl.post(f"/api/sitesup/sites/{sid}/forget").status_code == 400           # site still running
    S.save_site(T, site=sid, status="done")
    assert cl.post(f"/api/sitesup/sites/{sid}/forget").json()["say"]
    assert S.site_view(T, sid)["client_phone"] == ""
