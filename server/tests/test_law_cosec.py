"""Cosec Sahayak (company secretary's desk): due-date maths from her dates, small company, DIR-3 KYC 3-year cycle, additional-fee
starters, SS-1 / s.101 notice periods, quorum, board frequency; company master + DIN-only directors; events -> registers + DIR-12 /
PAS-3 / CHG-1; meeting notice / minutes / filing cards that ONLY her tap decides (fingerprint for filings once a phone key is
active); reminders once per window; tools (owner-only writes, customers refused) and API."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.cosec.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 23)
CIN = "U74999MH2020PTC123456"


@pytest.fixture
def cs(env, monkeypatch):
    from app.cosec import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "today", lambda t: DAY)
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def base(S):
    S.save_settings(T, firm="Ingle & Co", cs_name="CS Meghana Ingle", membership_no="ACS 12345")
    e = S.save_entity(T, "Akot Agro Pvt Ltd", kind="private", cin=CIN, paid_up="25 lakh", turnover="3 crore",
                      registered_office="Khanapur Ves, Akot 444101", incorporated_on="2020-06-10", auditor_name="Joshi & Co",
                      auditor_frn="123456W", auditor_term_to_agm="2029-30")
    S.person(T, "Akot", "Ramesh Patil", "director", din="01234567", kyc_on="2025-09-10", email="r@ex.in", phone="9876543210")
    S.person(T, "Akot", "Sunita Patil", "director", din="07654321", kyc_on="2025-09-12", phone="9876543211")
    return e


def test_rules():
    from app.cosec import rules as R
    # private, AGM held 25 Sep 2026 -> AOC-4 +30, MGT-7 +60, deposits 30 June
    rows = {r["form"]: r for r in R.annual("private", False, 2026, agm_on=date(2026, 9, 25))}
    assert rows["AOC-4"]["due"] == date(2026, 10, 25) and not rows["AOC-4"]["est"]
    assert rows["MGT-7"]["due"] == date(2026, 11, 24) and rows["DPT-3"]["due"] == date(2026, 6, 30)
    assert "ADT-1" not in rows and "MSME-1" not in rows
    est = {r["form"]: r for r in R.annual("private", True, 2026)}
    assert est["AGM"]["due"] == date(2026, 9, 30) and est["AOC-4"]["due"] == date(2026, 10, 30) and est["AOC-4"]["est"]
    assert "MGT-7A" in est and "MGT-7" not in est
    first = {r["form"]: r for r in R.annual("private", False, 2026, first_fy=True)}
    assert first["AGM"]["due"] == date(2026, 12, 31)
    gap = {r["form"]: r for r in R.annual("private", False, 2026, last_agm=date(2025, 6, 15))}
    assert gap["AGM"]["due"] == date(2026, 9, 15)                                    # 15 months from the last AGM
    opc = {r["form"]: r for r in R.annual("opc", False, 2026)}
    assert opc["AOC-4 OPC"]["due"] == date(2026, 9, 27) and "AGM" not in opc and opc["MGT-7A"]["est"]
    llp = {r["form"]: r for r in R.annual("llp", False, 2026)}
    assert llp["LLP-11"]["due"] == date(2026, 5, 30) and llp["LLP-8"]["due"] == date(2026, 10, 30)
    ms = [r for r in R.annual("private", False, 2026, msme_dues=True, auditor_term_ends=True, agm_on=date(2026, 9, 25)) if r["form"] in ("MSME-1", "ADT-1")]
    assert {r["due"] for r in ms} == {date(2026, 4, 30), date(2026, 10, 31), date(2026, 10, 10)}
    # small company (from 1 Dec 2025)
    assert R.small_check("private", 9e7, 9e8)["small"] and not R.small_check("private", 11e7, 9e8)["small"]
    assert R.small_check("private", None, 9e8)["small"] is None and not R.small_check("public", 1e6, 1e7)["small"]
    assert not R.small_check("private", 1e6, 1e7, holding_or_sub=True)["small"]
    # DIR-3 KYC once in 3 FYs
    assert R.kyc_due(date(2025, 9, 1))["due"] == date(2028, 6, 30)
    assert R.kyc_due(date(2026, 7, 1))["due"] == date(2029, 6, 30) and R.kyc_due(date(2026, 7, 1))["est"]
    assert R.kyc_due(None)["due"] is None
    # additional fee starters
    assert R.additional_fee("AOC-4", 10)["amount"] == 1000 and R.additional_fee("MGT-7A", 0)["amount"] == 0
    assert R.additional_fee("DIR-12", 20)["multiple"] == 2 and R.additional_fee("DIR-12", 200, 500)["amount"] == 6000
    assert R.additional_fee("DIR-12", 10)["amount"] is None and R.additional_fee("LLP-11", 3)["amount"] == 300
    # notice periods: board 7 clear days, general meeting 21; post adds 2 days
    assert R.notice_check("board", date(2026, 11, 10), date(2026, 11, 2))["ok"]
    assert not R.notice_check("board", date(2026, 11, 10), date(2026, 11, 3))["ok"]
    assert R.notice_check("board", date(2026, 11, 10), date(2026, 11, 3), shorter_consent=True)["ok"]
    assert not R.notice_check("agm", date(2026, 9, 25), date(2026, 9, 3), "post")["ok"]
    assert R.notice_check("agm", date(2026, 9, 25), date(2026, 9, 3))["latest_send"] == date(2026, 9, 3)
    assert R.quorum("board", strength=7, present=3)["ok"] and not R.quorum("board", strength=7, present=2)["ok"]
    assert R.quorum("board", strength=4, present=2, entity_kind="public", interested=1)["ok"] is False
    assert R.quorum("agm", members=1200, entity_kind="public", present=14)["need"] == 15
    assert R.quorum("agm", entity_kind="private", present=2)["ok"]
    assert R.board_frequency([date(2026, 1, 5), date(2026, 4, 1), date(2026, 9, 1), date(2026, 12, 1)], 2026, False) == [
        "2026-04-01 aur 2026-09-01 ke beech 153 din (120 se zyada nahi)."]
    assert R.board_frequency([date(2026, 3, 1), date(2026, 8, 1)], 2026, True) == []
    assert R.board_frequency([date(2026, 6, 1), date(2026, 7, 15)], 2026, True)
    assert R.guess_event("Ramesh ne istifa de diya") == "director_resign" and R.guess_event("naya director add karo") == "director_appoint"
    assert R.guess_event("registered office shift kar rahe hain") == "ro_change_local" and R.guess_event("shares allot kiye") == "allotment"
    with pytest.raises(ValueError):
        R.check_din("12345")
    with pytest.raises(ValueError):
        R.check_cin("ABC")
    assert R.norm_form("aoc4") == "AOC-4" and R.fy_end_year("2025-26") == 2026 and R.fy_label(2026) == "2025-26"


def test_entity_people_calendar(cs):
    S = cs
    e = base(S)
    assert e["number"] == "E-001" and e["small"] is True                            # Rs 25 lakh / Rs 3 crore -> small
    with pytest.raises(S.CosecError):
        S.save_entity(T, "Bad", cin="XYZ")
    with pytest.raises(S.CosecError):
        S.person(T, "Akot", "X", din="1234")
    with pytest.raises(S.CosecError):
        S.person(T, "Akot", "Ramesh Patil", id_ref="ABCDE1234F")                     # PAN only by locker reference
    assert S.person(T, "Akot", "Ramesh Patil", id_ref="{id:abc123}")["id_ref"] == "{id:abc123}"
    with pytest.raises(S.CosecError):
        S.person(T, "Akot", "Y", role="director", email="nomail")
    cal = S.calendar(T, "Akot", "2025-26")
    by = {f["form"]: f for f in cal["filings"]}
    assert by["AOC-4"]["due"] == "2026-10-30" and by["AOC-4"]["est"] and by["MGT-7A"]["due"] == "2026-11-29"
    assert by["DPT-3"]["due"] == "2026-06-30" and by["DPT-3"]["late"] and by["DPT-3"]["fee"]["multiple"] == 10
    kyc = [f for f in cal["filings"] if f["form"] == "DIR-3 KYC"]
    assert len(kyc) == 2 and kyc[0]["due"] == "2028-06-30"
    assert "CS / vakil" in cal["say"]
    # AGM held -> real dates replace the andaaza
    m = S.meeting_new(T, "Akot", "agm", "2026-09-25", "11:00", "Regd office", fy="2025-26")
    assert m["number"] == "AGM-001" and m["agenda"]
    S.notice_request(T, m["id"], send_on="2026-09-02")
    mm = [p for k, p in S.EVENTS if k == "cosec_notice"][-1]["meeting"]
    assert not mm["card"]["blockers"], mm["card"]["blockers"]
    S.decide_notice(T, m["id"], True, mm["notice_hash"], by_tap=True)
    att = S.attendance(T, m["id"], ["Ramesh Patil", "Sunita Patil"])
    assert att["quorum"]["ok"]
    by = {f["form"]: f for f in S.calendar(T, "Akot", "2025-26")["filings"]}
    assert by["AOC-4"]["due"] == "2026-10-25" and not by["AOC-4"]["est"] and by["AGM"]["status"] == "filed"
    # stop deposits flag -> DPT-3 not needed
    S.save_entity(T, ref="E-001", deposits=False)
    by = {f["form"]: f for f in S.calendar(T, "Akot", "2025-26")["filings"]}
    assert by["DPT-3"]["status"] == "not_needed"
    # OPC: no AGM
    S.save_entity(T, "Solo OPC Pvt Ltd", kind="opc", cin="U74999MH2021OPC123456")
    with pytest.raises(S.CosecError):
        S.meeting_new(T, "Solo", "agm", "2026-09-20", fy="2025-26")
    with pytest.raises(S.CosecError):
        S.save_entity(T, "Bad LLP", kind="llp", cin=CIN)


def test_events_registers(cs):
    S = cs
    base(S)
    out = S.event(T, "Akot", words="naya director add karo", on="2026-10-01", details={"name": "Anil Rao", "din": "11112222"})
    assert out["event"] == "director_appoint" and out["filings"][0]["form"] == "DIR-12" and out["filings"][0]["due"] == "2026-10-31"
    assert "cosec_event" in kinds(S)
    v = S.entity_view(T, "Akot")
    assert any(p["name"] == "Anil Rao" and p["din"] == "11112222" for p in v["directors"])
    late = S.event(T, "Akot", "allotment", "2026-09-01", details={"allottees": [{"name": "Ramesh Patil", "shares": 1000}, {"name": "Sunita Patil", "shares": "500"}]})
    f = late["filings"][0]
    assert f["form"] == "PAS-3" and f["due"] == "2026-10-01" and f["late"] and "nikal chuki" in late["say"]
    S.event(T, "Akot", "transfer", "2026-10-05", details={"from": "Ramesh Patil", "to": "Kavita Joshi", "shares": 200})
    mem = {p["name"]: p for p in S.entity_view(T, "Akot")["members"]}
    assert mem["Ramesh Patil"]["shares"] == 800 and mem["Kavita Joshi"]["shares"] == 200 and mem["Kavita Joshi"]["folio"]
    with pytest.raises(S.CosecError):
        S.event(T, "Akot", "transfer", details={"from": "Kavita Joshi", "to": "X", "shares": 999})
    ch = S.event(T, "Akot", words="bank loan liya, hypothecation", on="2026-10-10", details={"holder": "SBI Akot", "amount": "50 lakh"})
    assert ch["filings"][0]["form"] == "CHG-1"
    S.event(T, "Akot", "charge_satisfy", "2026-10-20", details={"holder": "SBI"})
    assert S.entity_view(T, "Akot")["charges"][0]["satisfied_on"] == "2026-10-20"
    r = S.event(T, "Akot", "director_resign", "2026-10-15", details={"name": "Anil Rao"})
    assert r["filings"][0]["form"] == "DIR-12"
    r2 = S.event(T, "Akot", "director_resign", "2026-10-16", details={"din": "07654321"})
    assert any("kam se kam 2" in n for n in r2["notes"])
    ro = S.event(T, "Akot", "ro_change_city", "2026-10-18", details={"address": "MIDC Akola"})
    assert {x["form"] for x in ro["filings"]} == {"MGT-14", "INC-22"}
    assert S.entity_view(T, "Akot")["registered_office"] == "MIDC Akola"
    with pytest.raises(S.CosecError):
        S.event(T, "Akot", words="kuch hua")
    with pytest.raises(S.CosecError):
        S.event(T, "Akot", "partner_change")
    S.save_entity(T, "Patil Traders LLP", kind="llp", llpin="AAB-1234")
    p = S.event(T, "Patil Traders", "partner_change", "2026-10-01", details={"name": "Mohan Patil", "din": "22223333"})
    assert p["filings"][0]["form"] == "LLP-4"
    assert S.registers_file(T, "Akot")["file"]["name"] == "Registers_E-001.xlsx"


def test_meeting_notice_minutes_by_tap(cs):
    S = cs
    base(S)
    m = S.meeting_new(T, "Akot", "board", "2026-10-27", "", "", agenda=["Bank account kholna", "Auditor ki fees"])
    S.notice_request(T, m["id"])                                                     # 3 clear days, no time / place
    card = [p for k, p in S.EVENTS if k == "cosec_notice"][-1]["meeting"]["card"]
    assert any("7 chahiye" in b for b in card["blockers"]) and any("[samay]" in b for b in card["blockers"])
    S.meeting_update(T, m["id"], on="2026-11-05", time="11:00", place="Regd office")
    v = S.notice_request(T, m["id"])
    assert not v["card"]["blockers"] and len(v["card"]["recipients"]) == 2 and "NOTICE is hereby given" in v["card"]["text"]
    with pytest.raises(S.CosecError):
        S.decide_notice(T, m["id"], True, v["notice_hash"])                            # not from the app
    with pytest.raises(S.CosecError):
        S.decide_notice(T, m["id"], True, "bad", by_tap=True)
    with pytest.raises(S.CosecError):
        S.attendance(T, m["id"], ["Ramesh Patil"])                                    # notice not sent yet
    out = S.decide_notice(T, m["id"], True, v["notice_hash"], by_tap=True)
    assert out["file"]["name"] == "Notice_BM-001.docx" and out["meeting"]["notice_sent_on"] == "2026-10-23"
    assert any(d["whatsapp"].startswith("https://wa.me/919876543210") for d in out["drafts"])
    with pytest.raises(S.CosecError):
        S.meeting_update(T, m["id"], on="2026-11-06")                                 # notice already out
    with pytest.raises(S.CosecError):
        S.resolution(T, m["id"], text="Open account")                                 # before the meeting is held
    a = S.attendance(T, m["id"], ["Ramesh Patil"])
    assert not a["quorum"]["ok"] and "POORA NAHI" in a["say"]
    with pytest.raises(S.CosecError):
        S.resolution(T, m["id"], text="Open account")
    a = S.attendance(T, m["id"], ["Ramesh Patil", "01234567", "Sunita Patil"], chair="Ramesh Patil")
    assert a["quorum"]["ok"]
    with pytest.raises(S.CosecError):
        S.resolution(T, m["id"], kind="special", text="Change name")                  # special only at a general meeting
    r = S.resolution(T, m["id"], kind="board", text="a current account be opened with SBI Akot")
    assert r["number"] == "R-2026/001" and r["result"] == "passed" and r["filing"] is None
    r2 = S.resolution(T, m["id"], kind="board", text="borrow up to Rs 50 lakh", mgt14=True)
    assert r2["filing"]["form"] == "MGT-14"
    d = S.minutes_draft(T, m["id"])
    assert "RESOLVED THAT a current account" in d["minutes"] and d["deadlines"]["sign_by"] == "2026-12-05"
    w = S.minutes_request(T, m["id"])
    assert w["card"]["blockers"]                                                     # [Discussion ...] still blank
    with pytest.raises(S.CosecError):
        S.decide_minutes(T, m["id"], True, w["minutes_hash"], by_tap=True)
    text = d["minutes"].replace("[Discussion: kya baat hui]", "Discussed and approved.")
    S.minutes_edit(T, m["id"], text)
    w = S.minutes_request(T, m["id"])
    assert not w["card"]["blockers"] and "cosec_minutes" in kinds(S)
    with pytest.raises(S.CosecError):
        S.decide_minutes(T, m["id"], True, w["minutes_hash"])
    done = S.decide_minutes(T, m["id"], True, w["minutes_hash"], by_tap=True)
    assert done["meeting"]["status"] == "minuted" and done["file"]["name"] == "Minutes_BM-001.docx"
    with pytest.raises(S.CosecError):
        S.minutes_edit(T, m["id"], "changed")
    # general meeting: special resolution needs 3x for -> MGT-14
    g = S.meeting_new(T, "Akot", "egm", "2026-11-20", "10:00", "Regd office", agenda=["Alteration of Articles"])
    gv = S.notice_request(T, g["id"], send_on="2026-10-28")
    S.decide_notice(T, g["id"], True, gv["notice_hash"], by_tap=True)
    S.attendance(T, g["id"], ["Ramesh Patil", "Sunita Patil"])
    bad = S.resolution(T, g["id"], kind="special", text="alter the Articles", votes_for=70, votes_against=30)
    assert bad["result"] == "failed" and bad["filing"] is None
    ok = S.resolution(T, g["id"], kind="special", text="alter the Articles", votes_for=80, votes_against=20)
    assert ok["filing"]["form"] == "MGT-14" and ok["filing"]["due"] == "2026-12-20"


def test_filing_card_by_tap_and_fingerprint(cs, monkeypatch):
    S = cs
    base(S)
    cal = S.calendar(T, "Akot", "2025-26")
    by = {f["form"]: f for f in cal["filings"]}
    aoc = S.filing_request(T, by["AOC-4"]["id"])
    assert any("AGM abhi hua nahi" in b for b in aoc["card"]["blockers"])
    with pytest.raises(S.CosecError):
        S.decide_filing(T, aoc["id"], True, aoc["hash"], by_tap=True)
    dpt = S.filing_request(T, by["DPT-3"]["id"])
    assert dpt["status"] == "waiting" and not dpt["card"]["blockers"] and "cosec_filing" in kinds(S)
    assert any("din der" in c for c in dpt["card"]["checks"]) and "DSC" in " ".join(dpt["card"]["steps"])
    with pytest.raises(S.CosecError):
        S.decide_filing(T, dpt["id"], True, dpt["hash"])                               # not from the app
    with pytest.raises(S.CosecError):
        S.filing_done(T, dpt["id"], "SRN1")                                           # not approved yet
    with pytest.raises(S.CosecError):
        S.decide_filing(T, dpt["id"], True, "bad", by_tap=True)
    assert S.filings(T, "Akot", "todo") and [f for f in S.filings(T, "Akot") if f["id"] == dpt["id"]][0]["status"] == "todo"
    dpt = S.filing_request(T, dpt["id"])
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.CosecError) as e:
        S.decide_filing(T, dpt["id"], True, dpt["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.filing_challenge(T, dpt["id"])
    assert "|cosec|" in ch["message"] and "DPT-3" in ch["show"]["title"]
    with pytest.raises(S.CosecError):
        S.decide_filing(T, dpt["id"], True, dpt["hash"], proof={"challenge_id": ch["challenge_id"], "device_id": "x", "signature": "AA=="},
                        by_tap=True)
    monkeypatch.setattr(S, "_verify_fingerprint", lambda *a, **k: None)
    ok = S.decide_filing(T, dpt["id"], True, dpt["hash"], by_tap=True)
    assert ok["status"] == "approved" and "MCA V3" in ok["say"]
    done = S.filing_done(T, dpt["id"], "AB1234567", "2026-10-24", 1200)
    assert done["status"] == "filed" and done["fee"]["days"] == 116 and done["fee"]["multiple"] == 10
    with pytest.raises(S.CosecError):
        S.filing_skip(T, dpt["id"], "galat")
    with pytest.raises(S.CosecError):
        S.filing_skip(T, by["MGT-7A"]["id"], "")
    assert S.filing_skip(T, by["MGT-7A"]["id"], "CS ne kaha")["status"] == "not_needed"
    no = S.filing_request(T, by["DIR-3 KYC"]["id"])
    assert S.decide_filing(T, no["id"], False, no["hash"], by_tap=True)["status"] == "todo"


def test_tick_reminders_once(cs):
    S = cs
    base(S)
    S.save_settings(T, morning_time="09:00")
    S.calendar(T, "Akot", "2025-26")
    S.event(T, "Akot", "director_appoint", "2026-09-24", details={"name": "Anil Rao", "din": "11112222"})   # DIR-12 due 24 Oct
    when = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)                         # 10:30 IST
    out = S.tick(when)
    alerts = [p["say"] for k, p in S.EVENTS if k == "cosec_alert"]
    assert any("DIR-12" in a and "1 din" in a for a in alerts) and any("DPT-3" in a and "der" in a for a in alerts)
    assert out["morning"] == 1
    day = [p for k, p in S.EVENTS if k == "cosec_day"][0]
    assert "Der ho gayi" in day["say"] and "30 din mein" in day["say"]
    n = len(S.EVENTS)
    S.tick(when + timedelta(minutes=5))
    assert len(S.EVENTS) == n                                                         # once each
    S.tick(when + timedelta(days=1))
    assert any("DIR-12" in p["say"] and "aaj aakhri din" in p["say"] for k, p in S.EVENTS[n:] if k == "cosec_alert")


def test_tools_and_api(cs, monkeypatch):
    S = cs
    from app.agent import cosec_tools as CT
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    run = lambda c, tool, **a: asyncio.run(CT.COSEC_HANDLERS[tool](c, **a))   # noqa: E731
    run(ctx, "cosec", action="settings", firm="Ingle & Co", membership_no="FCS 1234")
    e = run(ctx, "cosec", action="entity", name="Vidarbha Foods Pvt Ltd", kind="private", cin=CIN, paid_up="1 crore", turnover="20 crore",
              registered_office="Akola")
    assert e["small"] is True
    run(ctx, "cosec", action="person", entity="Vidarbha", name="Asha Rao", din="33334444")
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        run(staff, "cosec", action="settings", firm="X")
    with pytest.raises(ToolError):
        run(Ctx(T, ctx.conversation_id, actor="customer:wa:9"), "cosec_dekho", what="entities")
    cal = run(staff, "cosec", action="calendar", entity="Vidarbha", fy="2025-26")
    dpt = next(f for f in cal["filings"] if f["form"] == "DPT-3")
    card = run(staff, "cosec", action="file", filing_id=dpt["id"])
    assert card["status"] == "waiting"                                               # staff makes the card, can't file
    with pytest.raises(ToolError):
        run(staff, "cosec", action="skip", filing_id=dpt["id"], reason="x")
    assert run(ctx, "cosec_dekho", what="day")["say"]
    assert run(ctx, "cosec_dekho", what="entity", entity="Vidarbha")["directors"][0]["din"] == "33334444"
    assert "never" in run(ctx, "cosec_dekho", what="rules")
    m = run(ctx, "cosec", action="meeting", entity="Vidarbha", kind="board", on="2026-11-10", time="11:00", place="Office")
    assert run(ctx, "cosec_dekho", what="meeting", meeting=m["number"])["id"] == m["id"]
    assert len(CT.COSEC_TOOLS) == 2 and set(CT.COSEC_LABELS) == set(CT.COSEC_HANDLERS)

    from app.cosec.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    ov = c.get("/api/cosec").json()
    assert ov["entities"][0]["name"] == "Vidarbha Foods Pvt Ltd" and ov["never"]
    assert c.post(f"/api/cosec/filings/{dpt['id']}/decide", json={}).status_code == 400
    assert c.post(f"/api/cosec/filings/{dpt['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    card = c.post(f"/api/cosec/filings/{dpt['id']}/request").json()
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    r = c.post(f"/api/cosec/filings/{dpt['id']}/decide", json={"yes": True, "hash": card["hash"]})
    assert r.status_code == 428 and r.json()["detail"] == "fingerprint_needed"
    assert c.post(f"/api/cosec/filings/{dpt['id']}/challenge").json()["challenge_id"]
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    assert c.post(f"/api/cosec/filings/{dpt['id']}/decide", json={"yes": True, "hash": card["hash"]}).json()["status"] == "approved"
    n = c.post(f"/api/cosec/meetings/{m['id']}/notice", json={}).json()
    ok = c.post(f"/api/cosec/meetings/{m['id']}/notice/decide", json={"yes": True, "hash": n["notice_hash"]})
    assert ok.status_code == 200 and ok.json()["file"]["name"].endswith(".docx")
    ev = c.post("/api/cosec/entities/E-001/events", json={"words": "shares allot kiye", "on": "2026-10-20",
                                                         "details": {"allottees": [{"name": "Asha Rao", "shares": 100}]}}).json()
    assert ev["filings"][0]["form"] == "PAS-3"
    assert c.get("/api/cosec/entities/E-001/registers").json()["file"]["name"].endswith(".xlsx")
    assert c.post("/api/cosec/entities/E-001/forget").status_code == 400            # active client: no forget
    c.patch("/api/cosec/entities/E-001", json={"status": "closed"})
    assert c.post("/api/cosec/entities/E-001/forget").json()["forgotten"] >= 1
    assert c.get("/api/cosec/rules").json()["forms"]["AOC-4"]["law"] == "s.137"
