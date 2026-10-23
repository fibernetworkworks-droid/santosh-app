"""Compliance Sahayak (compliance officer): applicability from her facts, the statutory calendar (own items + GST / payroll / Daftar rows
READ from those Sahayaks), evidence-or-her-word to mark done, 'portal par file karo' and the monthly certificate that ONLY her tap
decides (hash checked, stale after any change), reminders / overdue penalty andaaza / morning note, tools and API."""
import asyncio
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.compliance.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 23)
GSTIN_MH = "27AAPFU0939F1ZV"
FACTS = {"entity": "pvt_ltd", "state": "Maharashtra", "employees": 25, "tan": True, "gstin": GSTIN_MH, "turnover": 3e7,
         "sectors": ["office"], "msme_dues": True, "fire_noc": False, "pt_yearly": 50000}


@pytest.fixture
def co(env, monkeypatch):
    from app.compliance import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "today", lambda t: DAY)
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def by_key(S, tenant=T):
    out = {}
    for v in S.calendar(tenant, ahead=120, include_linked=False)["items"]:
        out.setdefault(v["key"], []).append(v)
    return out


def setup(S, tenant=T):
    S.save_settings(tenant, None, firm="Newtika Pvt Ltd", signatory="Meghana Ingle", designation="Director",
                    owners={"tds": "Ankita", "labour": "Sandesh"}, team=[{"name": "Ankita", "phone": "98765 43210"}])
    return S.save_settings(tenant, FACTS)


def test_rules_catalogue_and_dates():
    from app.compliance import rules as R
    with pytest.raises(ValueError):
        R.clean_facts({"entity": "alien"})
    with pytest.raises(ValueError):
        R.clean_facts({"gstin": "27AAPFU0939F1ZA"})                       # bad check digit
    with pytest.raises(ValueError):
        R.clean_facts({"employees": -2})
    f = R.clean_facts(FACTS)
    assert f["state"] == "27" and f["entity"] == "pvt_ltd" and f["employees"] == 25
    assert R.clean_facts({"gstin": GSTIN_MH})["state"] == "27"           # state from GSTIN
    ap = {x["key"]: x for x in R.applicability(f)}
    for k in ("gst", "gstr9", "tds_deposit", "tds_140", "pf", "esic", "osh_reg", "posh_ic", "ptrc_year", "ptec", "lwf_mh", "msme1",
              "agm", "aoc4", "mgt7", "dpt3", "dir3"):
        assert ap[k]["applies"], k
    for k in ("fssai", "fssai_d1", "consent", "env_statement", "fire", "llp11", "tcs_deposit", "ptrc_month", "contract_licence"):
        assert not ap[k]["applies"], k
    assert ap["tds_140"]["source"]["url"].startswith("https://studycafe.in") and not ap["tds_140"]["verify"]
    assert ap["aoc4"]["source"]["title"] == "[citation chahiye]" and ap["aoc4"]["verify"]       # never an invented citation
    # TDS: 7th of next month, March deductions -> 30 April
    e = R.BY_KEY["tds_deposit"]
    got = {p: due for p, due, _ in R.instances(e, f, date(2027, 4, 1), date(2027, 5, 5))}
    assert got == {"2027-03": date(2027, 4, 30)}
    q = {p: due for p, due, _ in R.instances(R.BY_KEY["tds_140"], f, date(2026, 10, 1), date(2027, 6, 1))}
    assert q == {"FY2627-Q2": date(2026, 10, 31), "FY2627-Q3": date(2027, 1, 31), "FY2627-Q4": date(2027, 5, 31)}
    ar = {p: due for p, due, _ in R.instances(R.BY_KEY["annual_return"], f, date(2026, 10, 1), date(2027, 3, 31))}
    assert ar == {"CY2026": date(2027, 2, 28)}                            # labour codes Form XVII: last day of February
    g = {p for p, _, _ in R.instances(R.BY_KEY["gst"], f, date(2026, 10, 1), date(2026, 10, 31))}
    assert g == {"2026-09:gstr1", "2026-09:gstr3b"}
    # licence from HER date: 120 days before for FSSAI
    fl = R.clean_facts({**FACTS, "food_kind": "trader", "licences": {"fssai": "2027-03-31"}})
    assert R.instances(R.BY_KEY["fssai"], fl, date(2026, 10, 1), date(2027, 1, 31)) == [
        ("exp:2027-03-31", date(2026, 12, 1), "valid 31 Mar 2027 tak; 120 din pehle apply")]
    assert R.instances(R.BY_KEY["fssai"], f, date(2026, 10, 1), date(2027, 1, 31))[0][1] is None    # no date -> she tells
    assert R.penalty(R.BY_KEY["tds_140"], 10)["amount"] == 2000
    assert R.penalty(R.BY_KEY["fssai_d1"], 5)["amount"] == 500
    assert R.penalty(R.BY_KEY["tds_140"], 0)["amount"] is None
    assert R.penalty(R.BY_KEY["gst"], 3, "2026-09:gstr3b", f)["amount"] is not None
    assert any("TDS" in x for x in R.questions({"entity": "pvt_ltd", "state": "27", "employees": 3}))
    assert "CA / CS / vakil" in R.CHECK_LINE


def test_build_calendar_states_and_penalty(co):
    S = co
    setup(S)
    again = S.build(T)
    assert again["made"] == 0                                               # idempotent
    k = by_key(S)
    sep = next(v for v in k["tds_deposit"] if v["period"] == "2026-09")
    assert sep["due"] == "2026-10-07" and sep["state"] == "late" and sep["owner"] == "Ankita"
    assert "1.5%" in sep["penalty"]["text"]
    q2 = k["tds_140"][0]
    assert q2["due"] == "2026-10-31" and q2["state"] in ("due", "upcoming")
    assert any(v["period"].endswith(":gstr3b") and v["state"] == "late" for v in k["gst"])
    assert k["osh_reg"][0]["state"] == "no_date" and k["shop"][0]["state"] == "no_date"
    assert k["agm"][0]["due"] == "2026-09-30" and k["aoc4"][0]["state"] == "no_date"      # AOC-4 waits for the AGM date
    assert "fssai" not in k and "consent" not in k
    # she gives the AGM date: the placeholder goes, the real dates come
    S.save_settings(T, {"agm_date": "2026-09-28"})
    k = by_key(S)
    assert [v["due"] for v in k["aoc4"]] == ["2026-10-28"] and [v["due"] for v in k["mgt7"]] == ["2026-11-27"]
    ap = S.applicability(T)
    assert ap["facts"]["state"] == "27" and "CA / CS" in ap["say"]
    d = S.day(T)
    assert d["late"] and "Late" in d["say"]
    cal = S.calendar(T, area="tds")
    assert cal["items"] and all(v["area"] == "tds" for v in cal["items"])
    with pytest.raises(S.CompError):
        S.save_settings(T, {"entity": "spaceship"})


def test_done_needs_evidence_or_her_word(co):
    S = co
    setup(S)
    sep = next(v for v in by_key(S)["tds_deposit"] if v["period"] == "2026-09")
    with pytest.raises(S.CompError):
        S.mark_done(T, sep["number"])                                        # no saboot, no word
    with pytest.raises(S.CompError):
        S.mark_done(T, sep["number"], her_word=True, actor="staff:abc")      # staff can't just say so
    with pytest.raises(S.CompError):
        S.add_evidence(T, sep["number"], "nope")
    from app import chatfiles
    fid = chatfiles.store(T, "TDS_challan_Sep.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")["file_id"]
    v = S.mark_done(T, sep["number"], file_id=fid, ack="CIN 0510308 12345", actor="staff:abc")
    assert v["status"] == "done" and v["done_how"] == "evidence" and v["evidence"][0]["name"] == "TDS_challan_Sep.pdf"
    assert v["ack"] == "CIN 0510308 12345"
    oct_ = next(v for v in by_key(S)["tds_deposit"] if v["period"] == "2026-10")
    w = S.mark_done(T, oct_["id"], her_word=True, note="password hai abc123 bhar diya")
    assert w["done_how"] == "word" and "abc123" not in S.item(T, oct_["id"])["note"]
    with pytest.raises(S.CompError):
        S.mark_na(T, "C-0001", "x", actor="owner")                          # needs a real reason
    with pytest.raises(S.CompError):
        S.mark_na(T, "C-0001", "humare yahan lagu nahi", actor="staff:abc")
    n = S.mark_na(T, by_key(S)["dpt3"][0]["number"] if "dpt3" in by_key(S) else by_key(S)["posh_ic"][0]["number"], "pehle se bana hai, order file hai")
    assert n["status"] == "na"
    c = S.add_custom(T, "Lift ka yearly inspection", "2026-11-15", "licence", "Sandesh")
    assert c["custom"] and c["due"] == "2026-11-15"
    with pytest.raises(S.CompError):
        S.add_custom(T, "x", actor="staff:abc")
    nd = S.nudge(T, c["number"])
    assert "wa.me" in nd["whatsapp"] and "aap bhejiye" in nd["say"]


def test_filing_card_only_her_tap(co):
    S = co
    setup(S)
    q2 = by_key(S)["tds_140"][0]
    card = S.filing_request(T, q2["number"])
    assert card["status"] == "waiting" and "compliance_filing" in kinds(S) and "aap khud" in card["say"]
    with pytest.raises(S.CompError):
        S.decide_filing(T, card["id"], True, card["hash"])                   # a tool / the model can't approve
    with pytest.raises(S.CompError):
        S.decide_filing(T, card["id"], True, "wrong", by_tap=True)
    S.item_update(T, q2["number"], due="2026-11-15")                         # her own date -> the card is old
    with pytest.raises(S.CompError):
        S.decide_filing(T, card["id"], True, card["hash"], by_tap=True)
    assert S.filings(T, "stale")[0]["id"] == card["id"]
    card2 = S.filing_request(T, q2["number"])
    out = S.decide_filing(T, card2["id"], True, card2["hash"], by_tap=True)
    assert out["status"] == "approved" and "login" in out["say"]
    assert S.item(T, q2["number"])["status"] == "file_ok"
    assert S.decide_filing(T, card2["id"], False, card2["hash"], by_tap=True)["filing"]["status"] == "approved"   # decided once
    with pytest.raises(S.CompError):
        S.item_update(T, q2["number"], due="2026-12-01", actor="staff:abc")
    S.mark_done(T, q2["number"], her_word=True, ack="Token 123456789012345")
    with pytest.raises(S.CompError):
        S.filing_request(T, q2["number"])


def test_certificate_sign_off(co):
    S = co
    S.save_settings(T, FACTS)
    with pytest.raises(S.CompError):
        S.cert_request(T, "2026-10")                                         # who signs?
    S.save_settings(T, None, signatory="Meghana Ingle", firm="Newtika Pvt Ltd")
    draft = S.certificate(T, "2026-10")
    assert draft["counts"]["total"] > 0 and draft["counts"]["open"] > 0 and "Apvaad" in draft["text"]
    assert any(x["carry"] is False for x in draft["items"])
    card = S.cert_request(T, "2026-10")
    assert card["status"] == "waiting" and "compliance_cert" in kinds(S)
    with pytest.raises(S.CompError):
        S.decide_cert(T, card["id"], True, card["hash"])
    sep = next(v for v in by_key(S)["tds_deposit"] if v["period"] == "2026-09")
    S.mark_done(T, sep["number"], her_word=True)                              # something changed after the card
    with pytest.raises(S.CompError):
        S.decide_cert(T, card["id"], True, card["hash"], by_tap=True)
    card2 = S.cert_request(T, "2026-10")
    out = S.decide_cert(T, card2["id"], True, card2["hash"], by_tap=True)
    assert out["cert"]["status"] == "signed" and out["file"]["name"] == "Compliance_certificate_2026-10.pdf"
    assert "pc_file" in kinds(S) and "CA / CS" in out["say"]
    assert S.decide_cert(T, card2["id"], False, card2["hash"], by_tap=True)["cert"]["status"] == "signed"
    assert S.certs(T)[0]["status"] == "signed"
    reg = S.register_file(T)
    assert reg["file"]["name"].endswith(".xlsx")


def test_linked_neighbours_are_read_not_copied(co):
    S = co
    t2 = "t2"
    from app.gstp import service as G
    from app.office import service as O
    from app.payroll import service as P
    G.add_client(t2, "Apni firm", GSTIN_MH, scheme="monthly", aato=3e7)
    P.save_employee(t2, name="Ramu", gross=15000)
    O.renewal_add(t2, "FSSAI licence", "2027-01-10", kind="licence")
    S.save_settings(t2, {**FACTS, "food_kind": "trader", "licences": {"fssai": "2027-03-31"}})
    k = by_key(S, t2)
    assert "gst" not in k and "pf" not in k and "esic" not in k and "fssai" not in k     # their Sahayaks own these
    assert "tds_140" in k                                                     # non-salary TDS is still hers here
    lk = S.linked(t2)
    assert lk["gstp"] and lk["payroll"] and "fssai" in lk["office_licences"] and not lk["cosec"]
    rows = S.linked_rows(t2, ahead=120)
    src = {r["source"] for r in rows}
    assert {"gstp", "payroll", "office"} <= src
    ap = {x["key"]: x for x in S.applicability(t2)["items"]}
    assert ap["gst"]["covered_by"] == "gstp" and ap["pf"]["covered_by"] == "payroll" and ap["fssai"]["covered_by"] == "office"
    cal = S.calendar(t2, ahead=120)
    assert cal["linked"] and any(r["source"] == "office" and "FSSAI" in r["label"] for r in cal["linked"])


def test_tick_reminders_overdue_morning_and_cert_nudge(co):
    S = co
    setup(S)
    S.EVENTS.clear()
    w = datetime(2026, 10, 23, 4, 30, tzinfo=timezone.utc)                    # 10:00 IST
    out = S.tick(w)
    assert out["alerts"] > 0 and out["morning"] == 1
    late = [p for k, p in S.EVENTS if k == "compliance_alert" and "late" in p["say"]]
    assert late and any("Rs" in p["say"] or "%" in p["say"] or "interest" in p["say"].lower() for p in late)
    n = len(S.EVENTS)
    assert S.tick(w)["alerts"] == 0 and len(S.EVENTS) == n                    # once each
    out2 = S.tick(datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc))
    assert any(p["item"] is None and "Oct 2026" in p["say"] for k, p in S.EVENTS if k == "compliance_alert")
    assert out2["built"] == 1
    S.forget_person(T, "Ankita")
    assert not any(v["owner"] == "Ankita" for v in S.calendar(T, include_linked=False)["items"])


def test_tools(co):
    from app.agent import compliance_tools as CT
    from app.agent.tools import Ctx, ToolError
    S = co
    ctx = conv_ctx()
    r = asyncio.run(CT.compliance(ctx, "facts", entity="proprietor", state="27", employees=4, tan=True, sectors=["shop"]))
    assert "TDS jama (challan)" in r["applies"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(CT.compliance(staff, "facts", employees=40))
    cust = Ctx(T, ctx.conversation_id, actor="customer:wa:9876543210")
    with pytest.raises(ToolError):
        asyncio.run(CT.compliance_dekho(cust, "day"))
    item = S.calendar(T, include_linked=False)["items"][0]
    with pytest.raises(ToolError):
        asyncio.run(CT.compliance(staff, "done", item=item["number"], her_word=True))
    card = asyncio.run(CT.compliance(ctx, "filing", item=item["number"]))
    assert card["status"] == "waiting"                                        # the tool can only send the card
    d = asyncio.run(CT.compliance_dekho(ctx, "applicability"))
    assert d["items"] and d["questions"] is not None
    rules = asyncio.run(CT.compliance_dekho(ctx, "rules"))
    assert rules["never"] and len(rules["catalogue"]) > 30
    assert set(CT.COMPLIANCE_HANDLERS) == {t["name"] for t in CT.COMPLIANCE_TOOLS} == set(CT.COMPLIANCE_LABELS)


def test_api(co):
    from app.compliance.api import make_router
    S = co
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.put("/api/compliance/settings", json={"facts": FACTS, "signatory": "Meghana"}).status_code == 200
    o = c.get("/api/compliance").json()
    assert o["calendar"]["items"] and o["never"]
    assert c.put("/api/compliance/settings", json={"facts": {"entity": "x"}}).status_code == 400
    assert c.get("/api/compliance/applicability").json()["items"]
    it = o["calendar"]["items"][0]["number"]
    assert c.post(f"/api/compliance/items/{it}/done", json={}).status_code == 400
    f = c.post(f"/api/compliance/items/{it}/filing").json()
    assert c.post(f"/api/compliance/filings/{f['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    ok = c.post(f"/api/compliance/filings/{f['id']}/decide", json={"yes": True, "hash": f["hash"]}).json()
    assert ok["status"] == "approved"
    assert c.post(f"/api/compliance/items/{it}/done", json={"her_word": True, "ack": "ARN AA27"}).json()["status"] == "done"
    cert = c.post("/api/compliance/certificate", json={"month": "2026-10"}).json()
    signed = c.post(f"/api/compliance/certs/{cert['id']}/decide", json={"yes": True, "hash": cert["hash"]}).json()
    assert signed["cert"]["status"] == "signed"
    assert len(c.get("/api/compliance/rules").json()["catalogue"]) > 30
    assert c.post("/api/compliance/items", json={"label": "Lift inspection", "due": "2026-12-01"}).json()["due"] == "2026-12-01"
