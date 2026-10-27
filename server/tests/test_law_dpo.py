"""DPO Sahayak: records of processing pre-filled from her modules, Rule 3 notice in hi / mr / en with blanks, consent + parental
verification by reference, rights requests with the 90-day clock and identity by method only, reply / erasure / breach notices that
ONLY her tap (card hash; fingerprint for erasure) decides, erasure through the modules' own forget, breach 72 h clock + CERT-In link,
DPIA, processor DPA gaps, retention review, worker alerts, tools and API."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.dpo.models  # noqa: F401  (tables for the env fixture's init_db)
import app.helpdesk.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def dp(env, monkeypatch):
    from app.dpo import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_notice_file", lambda tenant, nid, lang, ver, txt: {"file_id": "f_test", "name": "n.docx"})
    S.EVENTS = events
    return S


def _lead(phone="9876543210", name="Ramesh"):
    from app.db import session
    from app.telecall.service import TeleLead
    with session() as s:
        l = TeleLead(tenant_id=T, name=name, phone=phone)
        s.add(l)
        s.flush()
        return l.id


def _settings(S):
    S.save_settings(T, org="Sharma Traders", contact_name="Meera", contact_email="privacy@sharma.example", contact_phone="9800000000",
                    link="https://sharma.example/privacy", identifiers="registered mobile par call")


def test_rules():
    from datetime import date
    from app.dpo import rules as R
    assert R.kind_of("please delete my data") == "erasure" and R.kind_of("mera data kya hai") == "access"
    assert R.kind_of("मेरा नाम सुधार दो") == "correction" and R.kind_of("message mat bhejo") == "withdraw"
    assert R.due_rights(date(2026, 1, 1), 0) == date(2026, 4, 1) and R.due_rights(date(2026, 1, 1), 120) == date(2026, 4, 1)
    assert R.due_rights(date(2026, 1, 1), 30) == date(2026, 1, 31)
    act = {"name": "Leads", "items": ["naam", "mobile"], "purpose": "call karna", "basis": "consent", "retention": "1 saal",
           "processors": ["Hoola"]}
    t = R.notice_text("en", "", [act], "", "", 30, 1, date(2026, 10, 23))
    assert "naam, mobile" in t and R.has_blank(t) and "Data Protection Board" in t and "withdraw" in t.lower()
    hi = R.notice_text("hi", "Dukaan", [act], "https://x.in", "Meera", 30, 2, date(2026, 10, 23))
    assert "गोपनीयता" in hi and not R.has_blank(hi)
    mr = R.notice_text("mr", "Dukaan", [{**act, "children": True}], "https://x.in", "Meera", 30, 1, date(2026, 10, 23))
    assert "पालक" in mr
    score, level, notes = R.dpia_score({"purpose": True, "children": True, "health_fin": True, "scale": True, "new_tech": False,
                                        "abroad": True, "sharing": False, "security": False, "consent_ok": True, "erase_ok": True})
    assert score == 10 and level == "high" and any("Kami" in n for n in notes)
    assert len(R.child_flags({"children": True, "purpose": "targeted ads for kids"})) == 2
    assert R.child_flags({"children": False}) == []
    assert R.scrub("OTP 445566 and card 4111 1111 1111 1111") == "OTP [hataya] and card [hataya]"
    assert R.has_blank(R.breach_report_text({}, "X")) and R.BLANK not in R.breach_people_text(
        {k: "x" for k in R.BREACH_FIELDS}, "Org", "Meera")


def test_scan_notice_and_tap(dp):
    S = dp
    _lead()
    out = S.scan(T)
    assert any(f["key"] == "telecall" and f["records"] == 1 for f in out["found"])
    acts = S.activities(T)
    tele = next(a for a in acts if a["source"] == "telecall")
    assert tele["records"] == 1 and not tele["confirmed"] and any("sahi hai" in c for c in tele["checks"])
    S.scan(T)                                                    # no duplicates on a second scan
    assert len([a for a in S.activities(T) if a["source"] == "telecall"]) == 1
    S.activity_save(T, tele["number"], confirmed=True, retention="band lead 1 saal", retention_days=365)
    n = S.notice_draft(T, "en")["notice"]
    assert n["blanks"]                                           # no org / link / contact yet
    with pytest.raises(S.DpoError):
        S.notice_request(T, n["id"])
    _settings(S)
    n = S.notice_draft(T, "hi")["notice"]
    assert not n["blanks"] and n["version"] == 1 and "Sharma Traders" in n["text"]
    c = S.notice_request(T, n["id"])["card"]
    with pytest.raises(S.DpoError):
        S.decide_card(T, c["id"], True, c["hash"])               # the tool path: never by_tap
    with pytest.raises(S.DpoError):
        S.decide_card(T, c["id"], True, "wrong", by_tap=True)
    r = S.decide_card(T, c["id"], True, c["hash"], by_tap=True)
    assert r["card"]["status"] == "approved" and r["file"]["file_id"] == "f_test"
    assert S.notices(T)[0]["status"] == "published"
    n2 = S.notice_draft(T, "hi")["notice"]
    c2 = S.notice_request(T, n2["id"])["card"]
    S.decide_card(T, c2["id"], True, c2["hash"], by_tap=True)
    st = {x["version"]: x["status"] for x in S.notices(T) if x["lang"] == "hi"}
    assert st == {1: "old", 2: "published"}


def test_request_verify_erase_reply(dp):
    from app.db import session
    from app.telecall.service import TeleLead
    S = dp
    _settings(S)
    lid = _lead()
    r = S.request_new(T, "Please delete my data, my OTP is 123456", name="Ramesh", phone="+91 98765 43210", via="whatsapp")["request"]
    assert r["kind"] == "erasure" and "123456" not in r["text"] and r["found"] and r["found"][0]["module"] == "telecall"
    assert r["due_on"] > r["received_on"] and r["phone"].endswith("3210")
    with pytest.raises(S.DpoError):
        S.erase_request(T, r["number"])                          # identity first
    with pytest.raises(S.DpoError):
        S.request_reply(T, r["number"])
    with pytest.raises(S.DpoError):
        S.request_verify(T, r["number"], True, "Aadhaar 2234 5678 9123 dekha")   # never an ID number
    S.request_verify(T, r["number"], True, "registered mobile par call karke pucha")
    c = S.erase_request(T, r["number"])["card"]
    assert c["fingerprint"] and c["data"]["targets"][0]["module"] == "telecall"
    out = S.decide_card(T, c["id"], True, c["hash"], by_tap=True)
    assert out["erased"][0]["ok"]
    with session() as s:
        assert s.get(TeleLead, lid) is None
    rep = S.request_reply(T, r["number"])["card"]
    assert "hata diya" in rep["data"]["text"]
    d = S.decide_card(T, rep["id"], True, rep["hash"], by_tap=True)
    assert d["send"]["wa"].startswith("https://wa.me/919876543210")
    S.request_sent(T, r["number"], "WhatsApp")
    assert S.request_view(T, r["number"])["status"] == "replied"


def test_access_reply_stale_and_fingerprint(dp, monkeypatch):
    S = dp
    _settings(S)
    _lead(phone="9811111111")
    S.scan(T)
    r = S.request_new(T, "mera kya data hai?", phone="9811111111")["request"]
    assert r["kind"] == "access"
    S.request_verify(T, r["id"], True, "registered number se")
    c = S.request_reply(T, r["id"])["card"]
    assert "Telecaller" in c["data"]["text"] and "Hoola" in c["data"]["text"]
    S.request_reply(T, r["id"], body="Aapka naam aur number hamare paas hai.")   # new draft -> old card stale
    old = S.card(T, c["id"])
    assert old["status"] == "stale"
    # erasure needs the phone fingerprint once a key is active
    e = S.request_new(T, "delete karo", phone="9811111111", kind="erasure")["request"]
    S.request_verify(T, e["id"], True, "call")
    ec = S.erase_request(T, e["id"])["card"]
    from app import approvekey
    monkeypatch.setattr(approvekey, "active_on", lambda tenant: True)
    with pytest.raises(S.DpoError, match="fingerprint_needed"):
        S.decide_card(T, ec["id"], True, ec["hash"], by_tap=True)
    ch = S.challenge(T, ec["id"])
    assert "|dpo|" in ch["message"]
    assert S.decide_card(T, ec["id"], False, ec["hash"], by_tap=True)["card"]["status"] == "rejected"   # Mana needs no finger


def test_consent_child_withdraw(dp):
    S = dp
    S.activity_save(T, name="Coaching students", purpose="classes", basis="consent", items=["naam", "umar"], children=True)
    a = S.activities(T)[0]
    assert any("verifiable consent" in c for c in a["checks"])
    with pytest.raises(S.DpoError):
        S.consent_add(T, "Riya", "9822222222", [a["number"]], how="form", child=True)
    with pytest.raises(S.DpoError):
        S.consent_add(T, "Riya", "9822222222", [a["number"]], child=True, parent_name="Asha", parent_check="PAN ABCDE1234F dekha")
    c = S.consent_add(T, "Riya", "9822222222", [a["number"]], how="form", child=True, parent_name="Asha",
                      parent_check="DigiLocker se umar dekhi, ref 23-10")["consent"]
    assert c["child"] and c["phone"].endswith("2222")
    w = S.consent_withdraw(T, phone="9822222222", how="WhatsApp")
    assert w["withdrawn"] == 1 and a["number"] in w["say"]
    assert S.consents(T)[0]["status"] == "withdrawn"


def test_breach_flow_and_tick(dp, monkeypatch):
    S = dp
    _settings(S)
    from app.helpdesk import service as H
    monkeypatch.setattr(H, "_publish", lambda *a, **k: None)
    aware = datetime(2026, 10, 23, 4, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(S, "clock", lambda: aware)
    b = S.breach_new(T, "Laptop chori hua, customer list thi", aware="abhi", nature="laptop chori", extent="400 graahak: naam, mobile",
                     affected=[{"name": "A", "phone": "9833333333"}, "x@y.example", "garbage"])["breach"]
    assert b["affected"] == 2 and b["report_due"] and b["hours_left"] == 72.0
    assert b["cert_in"].get("incident")                          # IT Helpdesk incident with the CERT-In clock
    init = S.breach_send(T, b["number"], "initial")["card"]      # initial may go with what is known
    with pytest.raises(S.DpoError):
        S.breach_send(T, b["number"], "report")                  # 72 h report: every item filled
    with pytest.raises(S.DpoError):
        S.breach_sent(T, b["number"], "initial")                 # not approved yet
    S.decide_card(T, init["id"], True, init["hash"], by_tap=True)
    S.breach_sent(T, b["number"], "initial", "mail 23-10")
    S.breach_update(T, b["number"], when="22-10 raat", location="dukaan", impact="spam calls", consequences="anjaan call aa sakte hain",
                    measures="sab password badle", safety="OTP kisi ko na dein", cause="laptop gaadi mein chhoda", findings="police FIR",
                    remedial="laptop encryption", details="400 record", people_report="sabko WhatsApp")
    p = S.breach_send(T, b["number"], "people")["card"]
    out = S.decide_card(T, p["id"], True, p["hash"], by_tap=True)
    assert len(out["send"]) == 2 and out["send"][0]["wa"].startswith("https://wa.me/91")
    with pytest.raises(S.DpoError):
        S.breach_close(T, b["number"])
    # worker: 6 h left -> alert once
    S.EVENTS.clear()
    S.tick(aware + timedelta(hours=67))
    S.tick(aware + timedelta(hours=67, minutes=5))
    al = [p for k, p in S.EVENTS if k == "dpo_alert" and p["kind"] == "breach"]
    assert len(al) == 1 and "ghante baaki" in al[0]["say"]
    rep = S.breach_send(T, b["number"], "report")["card"]
    S.decide_card(T, rep["id"], True, rep["hash"], by_tap=True)
    monkeypatch.setattr(S, "clock", lambda: aware + timedelta(hours=80))
    assert "72 ghante nikal" in S.breach_sent(T, b["number"], "report", "ref")["say"]
    S.breach_sent(T, b["number"], "people")
    assert S.breach_close(T, b["number"])["breach"]["status"] == "closed"


def test_vendor_dpia_retention_request_alerts(dp, monkeypatch):
    from app.db import session
    from app.telecall.service import TeleLead
    S = dp
    _lead()
    with session() as s:
        s.add(TeleLead(tenant_id=T, name="Old", phone="9844444444", created_at=datetime.now(timezone.utc) - timedelta(days=500)))
    S.scan(T)
    tele = next(a for a in S.activities(T) if a["source"] == "telecall")
    ret = next(r for r in S.retention(T) if r["activity"] == tele["number"])
    assert ret["older"] == 1
    v = S.vendor_save(T, name="Meta WhatsApp", country="USA", clauses={"security": True, "breach": True})["vendor"]
    assert v["abroad"] and len(v["missing"]) == 9 and not v["dpa_signed"]
    d = S.dpia(T, tele["number"], {"purpose": True, "children": False, "health_fin": False, "scale": False, "new_tech": False,
                                   "abroad": True, "sharing": True, "security": True, "consent_ok": True, "erase_ok": False})
    assert d["activity"]["dpia"]["level"] == "medium" and d["activity"]["abroad"]
    S.save_settings(T, reply_days=30)
    with pytest.raises(S.DpoError):
        S.save_settings(T, reply_days=120)
    r = S.request_new(T, "shikayat hai", phone="9855555555", received="2026-09-01")["request"]
    S.EVENTS.clear()
    S.tick(datetime(2026, 10, 2, 6, 0, tzinfo=timezone.utc))
    kinds = [p["kind"] for k, p in S.EVENTS if k == "dpo_alert"]
    assert "request" in kinds and "retention" in kinds
    assert any(k == "dpo_day" for k, _ in S.EVENTS)


def test_tools_and_api(dp):
    from app.agent import tools as AT
    from app.agent.dpo_tools import DPO_HANDLERS, DPO_TOOLS
    from app.dpo.api import make_router
    S = dp
    assert {t["name"] for t in DPO_TOOLS} == {"dpo", "dpo_dekho"}
    ctx = conv_ctx()
    out = asyncio.run(DPO_HANDLERS["dpo"](ctx, action="request", text="delete my data", phone="9866666666"))
    assert out["request"]["kind"] == "erasure"
    law = asyncio.run(DPO_HANDLERS["dpo_dekho"](ctx, what="law"))
    assert law["phases"]["main_duties"] == "2027-05-13" and law["sources"]
    staff = AT.Ctx(ctx.tenant_id, ctx.conversation_id, actor="staff:x")
    with pytest.raises(AT.ToolError):
        asyncio.run(DPO_HANDLERS["dpo"](staff, action="settings", org="X"))
    cust = AT.Ctx(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(AT.ToolError):
        asyncio.run(DPO_HANDLERS["dpo_dekho"](cust, what="requests"))
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(app)
    assert cl.put("/api/dpo/settings", json={"org": "Sharma", "link": "https://s.example/p", "contact_email": "a@b.example"}).status_code == 200
    _lead(phone="9877777777")
    assert cl.post("/api/dpo/scan").json()["found"]
    n = cl.post("/api/dpo/notices", json={"lang": "mr"}).json()["notice"]
    c = cl.post(f"/api/dpo/notices/{n['id']}/publish").json()["card"]
    assert cl.post(f"/api/dpo/cards/{c['id']}/decide", json={"hash": c["hash"]}).status_code == 400
    assert cl.post(f"/api/dpo/cards/{c['id']}/decide", json={"yes": True, "hash": c["hash"]}).json()["card"]["status"] == "approved"
    assert cl.get("/api/dpo/find", params={"phone": "9877777777"}).json()["found"]
    ov = cl.get("/api/dpo").json()
    assert ov["activities"] and "say" in ov["day"]
