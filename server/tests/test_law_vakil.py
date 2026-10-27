"""Vakil Sahayak (lawyer's junior): CNR / case numbers, case-status + cause-list text she pastes from the official eCourts app,
limitation arithmetic (ss.4 / 12) from her dates, diary, document checklist, drafts (Word, Lekhak notice reply), cards that ONLY her
tap decides (filing / message / fee + fingerprint), privilege (no other client's data in a message), fee ledger, DPDP forget, tick,
tools, API."""
import asyncio
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.vakil.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 23)          # a Friday

STATUS_TEXT = """Case Details
Case Type : RCS - Regular Civil Suit
Filing Number : 1234/2024
Filing Date : 05-03-2024
Registration Number : 456/2024
CNR Number : MHAK010004562024
Case Status
First Hearing Date : 20th March 2024
Next Hearing Date : 15th November 2026
Case Stage : Evidence
Court Number and Judge : 3-Civil Judge Senior Division
History of Case Hearing
Judge  15-09-2026  20-10-2026  Evidence
Judge  20-10-2026  15-11-2026  Evidence
"""

CAUSE_TEXT = """DISTRICT COURT AKOLA
Cause List for 26-10-2026
Court No. 3 Civil Judge Senior Division
1. RCS/456/2024  Ramesh Patil vs Suresh Deshmukh   Evidence
2. RCS/789/2023  Anil Joshi vs State Bank   Arguments
3. Cri.M.A. 12/2025  Kavita More vs State   Hearing
"""


@pytest.fixture
def vk(env, monkeypatch):
    from app.vakil import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "today", lambda t: DAY)
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=1500: "")
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def base(S):
    S.save_settings(T, advocate="Adv. Meghana Ingle", enrolment_no="MAH/1234/2015", office="Ingle Law Chambers", phone="9876543210",
                    upi_id="ingle@okaxis", place="Akola", closed_dates=["2026-11-16"])
    return S.save_matter(T, "Ramesh Patil vs Suresh Deshmukh", client="Ramesh Patil", client_phone="98765 43211", kind="civil_suit",
                         side="plaintiff", opposite="Suresh Deshmukh", court="Civil Judge Senior Division, Akola", case="RCS 456/2024")


def test_rules_parsing_and_limitation():
    from app.vakil import rules as R
    c = R.cnr("mhak01-000456-2024")
    assert c and c["cnr"] == "MHAK010004562024" and c["state"] == "MH" and c["serial"] == 456 and c["year"] == 2024
    assert R.cnr("MHAK0100045620") is None and R.cnr("1234567890123456") is None
    assert R.parse_case_ref("RCS 123/2024") == {"case_type": "RCS", "case_no": "123", "case_year": "2024"}
    assert R.parse_case_ref("MHAK010004562024") == {"cnr": "MHAK010004562024"}
    assert R.parse_date("15th November 2026") == date(2026, 11, 15) and R.parse_date("15/11/26") == date(2026, 11, 15)
    assert R.parse_date("Nov 15, 2026") == date(2026, 11, 15) and R.parse_date("kabhi") is None
    p = R.parse_status(STATUS_TEXT)
    assert p["cnr"] == "MHAK010004562024" and p["next_date"] == "2026-11-15" and p["stage"] == "Evidence"
    assert p["registration_no"] == "456" and p["registration_year"] == "2024" and len(p["history"]) == 2 and not p["disposed"]
    cl = R.parse_cause_list(CAUSE_TEXT)
    assert cl["date"] == "2026-10-26" and len(cl["items"]) == 3 and cl["items"][0]["item"] == 1
    assert cl["items"][0]["key"] == R.case_key("RCS", 456, 2024) and "Patil" in cl["items"][0]["parties"]
    assert cl["items"][2]["no"] == 12 and cl["items"][2]["year"] == 2025
    # Art 116(b): 30 days from the decree; s.12(1) the first day is not counted
    r = R.limitation("appeal_other_civil", "2026-10-01", today=DAY)
    assert r["ok"] and r["last_date"] == "2026-10-31" and r["source"].startswith("Limitation Act") and R.CHECK in r["say"]
    # s.12(2) certified copy time excluded; s.4 court closed (Sunday) -> next open day
    r2 = R.limitation("appeal_other_civil", "2026-10-01", cc_applied="2026-10-05", cc_ready="2026-10-15", today=DAY)
    assert r2["excluded_days"] == 10 and r2["last_date"] == "2026-11-10"
    r3 = R.limitation("appeal_hc_civil", "2026-08-03", today=DAY)                   # 90 days = 1 Nov 2026, a Sunday
    assert r3["last_date"] == "2026-11-02" and any("s.4" in x for x in r3["steps"])
    r4 = R.limitation("appeal_hc_civil", "2026-08-03", closed={"2026-11-02"}, today=DAY)
    assert r4["last_date"] == "2026-11-03"
    assert R.add_period(date(2024, 2, 29), 3, "y") == date(2027, 2, 28)             # 3 years, leap day clipped
    y = R.limitation("money_loan", "2024-02-29", today=DAY)                         # 28 Feb 2027 is a Sunday -> s.4
    assert y["last_date"] == "2027-03-01" and "Section 5" in y["notes"][0]
    # unknown period is asked, never guessed; her advocate's number is used and labelled
    assert not R.limitation("cheque_138", "2026-10-01")["ok"] and "vakil" in R.limitation("slp", "2026-10-01")["ask"]
    assert not R.limitation("something_else", "2026-10-01")["ok"]
    mine = R.limitation("cheque_138", "2026-10-01", n=1, unit="m", today=DAY)
    assert mine["ok"] and mine["last_date"] == "2026-11-02" and mine["source"] == "aapka bataya"   # 1 Nov is Sunday
    over = R.limitation("review", "2026-10-01", n=45, unit="d", today=DAY)
    assert "aapka maana" in over["steps"][0]
    late = R.limitation("appeal_other_civil", "2026-10-01", cc_applied="2026-11-05", cc_ready="2026-11-10", today=DAY)
    assert late["excluded_days"] == 0 and "baad maangi" in " ".join(late["steps"])
    assert {k for k, _ in R.checklist("cheque_138")} >= {"vakalatnama", "cheque", "return_memo", "notice"}


def test_diary_paste_and_cause_list(vk):
    S = vk
    m = base(S)
    assert m["number"] == "M-0001" and m["case"] == "RCS 456/2024" and m["client"] == "Ramesh Patil"
    assert "Plaint draft" in m["docs_missing"]
    with pytest.raises(S.VakilError):
        S.save_matter(T, ref="M-0001", cnr="ABC123")
    with pytest.raises(S.VakilError):
        S.save_client(T, ref="Ramesh Patil", id_ref="1234 5678 9012")            # ID only by locker reference
    S.save_client(T, ref="Ramesh Patil", id_ref="{id:abc123}")
    out = S.status_paste(T, STATUS_TEXT)
    assert out["matched"] and out["matter"]["cnr"] == "MHAK010004562024" and out["matter"]["next_date"] == "2026-11-15"
    assert out["matter"]["stage"] == "Evidence" and any("Agli tareekh" in c for c in out["changes"])
    assert len(out["matter"]["hearings"]) == 2
    again = S.status_paste(T, STATUS_TEXT)
    assert len(again["matter"]["hearings"]) == 2                                    # nothing doubled
    with pytest.raises(S.VakilError):
        S.status_paste(T, "kuch bhi nahi")
    other = S.status_paste(T, STATUS_TEXT.replace("MHAK010004562024", "MHAK010009992024").replace("456/2024", "999/2024"))
    assert not other["matched"]
    with pytest.raises(S.VakilError):                                              # wrong matter named for that CNR
        S.status_paste(T, STATUS_TEXT.replace("MHAK010004562024", "MHAK010009992024"), "M-0001")
    S.save_matter(T, "Kavita More vs State", client="Kavita More", kind="bail", case="Cri.M.A. 12/2025", next_date="2026-10-26")
    S.save_matter(T, "Old matter", client="Someone Else", case="RCS 10/2020", next_date="2026-10-26")
    cl = S.cause_list(T, CAUSE_TEXT)
    got = {x["matter"]: x for x in cl["found"]}
    assert set(got) == {"M-0001", "M-0002"} and got["M-0001"]["item"] == 1 and got["M-0001"]["date_changed"]
    assert [x["matter"] for x in cl["not_listed"]] == ["M-0003"] and "list mein nahi mile" in cl["say"]
    assert S.matter_view(T, "M-0001")["next_date"] == "2026-10-26"
    h = S.hearing(T, "M-0001", "2026-10-26", "Evidence", "PW1 ki cross poori hui", "2026-11-20", "Evidence (PW2)", "evidence")
    assert h["matter"]["next_date"] == "2026-11-20" and "Agli tareekh 2026-11-20" in h["say"]
    with pytest.raises(S.VakilError):
        S.hearing(T, "M-0001", "2026-10-26", next_date="2026-10-20")
    no_next = S.hearing(T, "M-0002", "2026-10-26", result="Bail par sunwaai adhoori")
    assert "nahi bataayi" in no_next["say"]
    S.event(T, "M-0001", "2024-01-10", "Rs 2,00,000 udhaar diya")
    S.event(T, "M-0001", "2024-02-15", "Legal notice bheja")
    d = S.doc_set(T, "M-0001", "plaint", "have")
    assert next(x for x in d["docs"] if x["key"] == "plaint")["state"] == "have"
    assert any(x["key"].startswith("x_") for x in S.doc_set(T, "M-0001", "", "have", label="Bank statement")["docs"])
    with pytest.raises(S.VakilError):
        S.save_matter(T, ref="M-0002", side="judge")
    lim = S.limitation(T, "appeal_other_civil", "2026-10-01", "M-0001")
    assert lim["deadline"]["last_date"] == "2026-10-31" and lim["matter"] == "M-0001"
    lim2 = S.limitation(T, "appeal_other_civil", "2026-10-01", "M-0001", cc_applied="2026-10-05", cc_ready="2026-10-15")
    assert len(S.deadlines(T)) == 1 and S.deadlines(T)[0]["last_date"] == lim2["last_date"] == "2026-11-10"
    # her court holiday (16 Nov) moves a last date by s.4
    l3 = S.limitation(T, "review", "2026-10-17", save=False)
    assert l3["last_date"] == "2026-11-17"


def test_drafts(vk, monkeypatch):
    S = vk
    base(S)
    S.save_matter(T, ref="M-0001", next_date="2026-11-15", next_purpose="Evidence")
    adj = S.draft(T, "M-0001", "adjournment", reason="client ki tabiyat kharab hai, hospital mein bharti")
    assert "APPLICATION FOR ADJOURNMENT" in adj["draft"]["text"] and "2026-11-15" in adj["draft"]["text"]
    assert "tabiyat kharab" in adj["draft"]["text"] and "DRAFT" in adj["draft"]["text"] and adj["file"]["name"].endswith(".docx")
    assert "MAH/1234/2015" in adj["draft"]["text"] and "vakil_draft" in kinds(S)
    blank = S.draft(T, "M-0001", "adjournment")
    assert blank["draft"]["blanks"] >= 1 and "wajah" in blank["draft"]["text"]
    v = S.draft(T, "M-0001", "vakalatnama")
    assert "Welfare" in v["draft"]["text"] and "enrolment" in v["draft"]["text"]
    with pytest.raises(S.VakilError):
        S.draft(T, "M-0001", "dates_events")                                     # nothing written yet: never invented
    S.event(T, "M-0001", "2024-01-10", "Rs 2,00,000 udhaar diya")
    de = S.draft(T, "M-0001", "dates_events")
    assert "| 10.01.2024 | Rs 2,00,000 udhaar diya |" in de["draft"]["text"]
    # model synopsis: numbers / citations not in the facts are cut out
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=1500:
                        "1. Plaintiff lent Rs 2,00,000 on 2024-01-10 and Rs 9,99,999 later. 2. See AIR 1999 SC 123.")
    syn = S.draft(T, "M-0001", "synopsis")
    t = syn["draft"]["text"]
    assert "2,00,000" in t and "9,99,999" not in t and "[?]" in t and "AIR 1999" not in t and "[citation chahiye]" in t
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    assert "Facts in brief" in S.draft(T, "M-0001", "synopsis")["draft"]["text"]
    seen = {}

    def fake_lekhak(tenant, words, to, conv):
        seen["words"] = words
        return {"doc": {"id": "ld1", "number": "L-0007", "title": "Reply to notice", "text": "Draft reply"}}
    monkeypatch.setattr(S, "_lekhak_reply", fake_lekhak)
    nr = S.draft(T, "M-0001", "notice_reply", words="Notice mein 5 lakh maange, jawab: koi udhaar baaki nahi", to="Adv. Kale")
    assert nr["draft"]["lekhak_doc"] == "ld1" and "5 lakh" in seen["words"] and "aapke tap" in nr["say"]
    with pytest.raises(S.VakilError):
        S.draft(T, "M-0001", "notice_reply", words="hi")
    assert len(S.matter_view(T, "M-0001")["drafts"]) == 7


def test_cards_only_her_tap(vk, monkeypatch):
    S = vk
    base(S)
    S.hearing(T, "M-0001", "2026-10-20", result="Evidence adhoora", next_date="2026-11-15", next_purpose="Evidence")
    msg = S.message_request(T, "M-0001", "client")
    card = msg["card"]
    assert card["status"] == "waiting" and "15" in card["body"]["text"] and "Ramesh Patil" in card["body"]["text"]
    assert "vakil_card" in kinds(S) and "Maine kuch nahi bheja" in msg["say"]
    assert S.message_request(T, "M-0001", "client")["card"]["id"] == card["id"]          # never asked twice
    with pytest.raises(S.VakilError):
        S.decide(T, card["id"], True, card["hash"])                                     # tools can't approve
    with pytest.raises(S.VakilError):
        S.decide(T, card["id"], True, "wrong", by_tap=True)
    out = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert out["card"]["status"] == "approved" and "wa.me/919876543211" in out["links"]["whatsapp"]
    assert S.decide(T, card["id"], True, card["hash"], by_tap=True)["card"]["status"] == "approved"   # decided once
    assert S.card_done(T, card["id"])["card"]["status"] == "done"
    # a changed phone after the card = stale
    S.save_client(T, ref="Ramesh Patil", phone="9876500000")
    c2 = S.message_request(T, "M-0001", "client", text="Kal subah 10 baje court aaiye.")["card"]
    S.save_client(T, ref="Ramesh Patil", phone="9876511111")
    assert S.decide(T, c2["id"], True, c2["hash"], by_tap=True)["card"]["status"] == "stale"
    # privilege: another client's name / matter never goes into a message
    S.save_matter(T, "Anil Joshi vs Bank", client="Anil Joshi", case="RCS 789/2023")
    with pytest.raises(S.VakilError) as e:
        S.message_request(T, "M-0001", "client", text="Anil Joshi ka case bhi isi din hai.")
    assert "doosre matter" in str(e.value)
    with pytest.raises(S.VakilError):
        S.message_request(T, "M-0001", "opposite")                                      # never writes to the other side itself
    with pytest.raises(S.VakilError):
        S.message_request(T, "M-0001", "client", text="Agli tareekh [tareekh chahiye]")
    opp = S.message_request(T, "M-0001", "opposite", text="Notice ka jawab sanlagn hai.", email="kale@law.in")["card"]
    od = S.decide(T, opp["id"], True, opp["hash"], by_tap=True)
    assert od["links"]["email"].startswith("mailto:kale%40law.in")
    S.card_done(T, opp["id"], on="2026-10-23")
    assert any("Doosre paksh" in e["what"] for e in S.matter_view(T, "M-0001")["events"])
    S.save_client(T, ref="Anil Joshi", no_messages=True)
    with pytest.raises(S.VakilError):
        S.message_request(T, "M-0002", "client")
    # filing: card; operator only after her tap, and she does OTP / fee / eSign / submit
    started = {}

    def fake_start(tenant, task, start_url="", file_ids=None, conversation_id="", created_by="owner", guide=""):
        started["task"], started["url"] = task, start_url
        return {"id": "op1"}
    from app.operator import service as ops
    monkeypatch.setattr(ops, "start", fake_start)
    fl = S.filing_request(T, "M-0001", "Plaint with documents", use_operator=True)
    assert fl["card"]["status"] == "waiting" and "missing" in fl["say"] and not started
    with pytest.raises(S.VakilError):
        S.card_done(T, fl["card"]["id"], "EF/1")                                       # nothing before her haan
    fd = S.decide(T, fl["card"]["id"], True, fl["card"]["hash"], by_tap=True)
    assert fd["link"] == "https://efiling.ecourts.gov.in/" and started["url"] == fd["link"] and "do NOT press Submit" in started["task"]
    assert fd["operator"]["status"] == "started"
    S.card_done(T, fl["card"]["id"], "EF/2026/778")
    assert S.matter_view(T, "M-0001")["filing_no"] == "EF/2026/778"
    # fee: her number only; fingerprint once a phone key is active
    with pytest.raises(S.VakilError):
        S.fee_request(T, "M-0001", None)
    S.fee_add(T, "M-0001", "agreed", 50000, "Suit tak")
    fee = S.fee_request(T, "M-0001", "25k", "Pehli kisht")["card"]
    assert fee["body"]["amount"] == 25000
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.VakilError) as e:
        S.decide(T, fee["id"], True, fee["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, fee["id"])
    assert "|vakil|" in ch["message"] and ch["show"]["payee"] == "Ramesh Patil"
    with pytest.raises(S.VakilError):
        S.decide(T, fee["id"], True, fee["hash"], proof={"challenge_id": ch["challenge_id"], "device_id": "x", "signature": "AA=="},
                 by_tap=True)
    monkeypatch.setattr(S, "_verify_fingerprint", lambda *a, **k: None)
    fo = S.decide(T, fee["id"], True, fee["hash"], by_tap=True)
    assert fo["fee_no"] == "FN-0001" and fo["file"]["name"].endswith(".pdf")
    assert fo["links"]["upi"].startswith("upi://pay?pa=ingle%40okaxis&am=25000.00")
    S.fee_add(T, "M-0001", "received", 25000, ref_no="UTR 77")
    led = S.ledger(T, "M-0001")
    assert led["totals"]["requested"] == 25000 and led["totals"]["received"] == 25000 and led["due"] == 25000
    rej = S.fee_request(T, "M-0001", 1000, "Clerkage")["card"]
    assert S.decide(T, rej["id"], False, rej["hash"], by_tap=True)["card"]["status"] == "rejected"   # no fingerprint for Mana


def test_day_tick_forget(vk, monkeypatch):
    S = vk
    base(S)
    S.save_matter(T, ref="M-0001", next_date="2026-10-23", next_purpose="Evidence")
    S.save_matter(T, "Kavita More vs State", client="Kavita More", kind="bail", next_date="2026-10-24")
    S.save_matter(T, "Purani tareekh", client="X Y", next_date="2026-10-01")
    S.limitation(T, "appeal_other_civil", "2026-10-01", "M-0002")                   # 31 Oct: 8 days left
    d = S.day(T)
    assert d["today"][0]["matter"] == "M-0001" and d["tomorrow"][0]["matter"] == "M-0002"
    assert d["stale"][0]["matter"] == "M-0003" and d["limitation"][0]["days_left"] == 8 and "Aaj ki tareekhein" in d["say"]
    when = datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc)                        # 08:30 IST
    out = S.tick(when)
    assert out["morning"] == 1 and out["alerts"] == 2                               # limitation window 15 + stale date
    assert "vakil_day" in kinds(S) and "vakil_alert" in kinds(S)
    assert S.tick(when) == {"alerts": 0, "morning": 0}                              # once each
    # forget only after the client's matters are closed
    with pytest.raises(S.VakilError):
        S.forget(T, "Kavita More")
    S.save_matter(T, ref="M-0002", status="closed")
    f = S.forget(T, "Kavita More")
    assert f["matters"] == ["M-0002"]
    assert all(c["name"] != "Kavita More" for c in S.clients(T))
    reg = S.register_file(T)
    assert reg["file"]["name"] == "Court_diary.xlsx"


def test_tools_and_api(vk, monkeypatch):
    S = vk
    from app.agent import vakil_tools as VT
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    run = lambda c, tool, **a: asyncio.run(VT.VAKIL_HANDLERS[tool](c, **a))   # noqa: E731
    run(ctx, "vakil", action="settings", advocate="Adv. Ingle", place="Akola")
    m = run(ctx, "vakil", action="matter", title="Patil vs Deshmukh", client="Ramesh Patil", case="RCS 456/2024", kind="civil_suit")
    assert m["number"] == "M-0001"
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    run(staff, "vakil", action="hearing", matter="RCS 456/2024", on="2026-10-20", result="Adjourned", next_date="2026-11-15")
    with pytest.raises(ToolError):
        run(staff, "vakil", action="fee", matter="M-0001", kind="received", amount=100)
    with pytest.raises(ToolError):
        run(staff, "vakil", action="matter", matter="M-0001", status="closed")
    with pytest.raises(ToolError):
        run(Ctx(T, ctx.conversation_id, actor="customer:wa:9"), "vakil_dekho", what="matters")
    c = run(staff, "vakil", action="message", matter="M-0001", to="client")
    assert c["card"]["status"] == "waiting"                                           # staff makes the card, can't approve
    lim = run(ctx, "vakil", action="limitation", kind="revision", start="2026-10-01")
    assert lim["last_date"] == "2026-12-30" and "deadline" not in lim
    assert run(ctx, "vakil_dekho", what="matter", matter="Patil")["next_date"] == "2026-11-15"
    assert "limits" in run(ctx, "vakil_dekho", what="rules")
    assert len(VT.VAKIL_TOOLS) == 2 and set(VT.VAKIL_LABELS) == set(VT.VAKIL_HANDLERS)

    from app.vakil.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    cl = TestClient(app)
    ov = cl.get("/api/vakil").json()
    assert ov["matters"][0]["title"] == "Patil vs Deshmukh" and ov["cards"][0]["id"] == c["card"]["id"]
    cid = c["card"]["id"]
    assert cl.post(f"/api/vakil/cards/{cid}/decide", json={}).status_code == 400
    assert cl.post(f"/api/vakil/cards/{cid}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    ok = cl.post(f"/api/vakil/cards/{cid}/decide", json={"yes": True, "hash": c["card"]["hash"]})
    assert ok.status_code == 200 and ok.json()["card"]["status"] == "approved"
    r = cl.post("/api/vakil/paste/status", json={"text": STATUS_TEXT, "matter": "M-0001"})
    assert r.status_code == 200 and r.json()["matter"]["cnr"] == "MHAK010004562024"
    assert cl.post("/api/vakil/paste/cause_list", json={"text": CAUSE_TEXT}).json()["found"][0]["matter"] == "M-0001"
    assert cl.post("/api/vakil/limitation", json={"kind": "cheque_138", "start": "2026-10-01"}).json()["ok"] is False
    assert cl.post("/api/vakil/matters/M-0001/limitation", json={"kind": "review", "start": "2026-10-01"}).json()["last_date"] == "2026-10-31"
    fee = cl.post("/api/vakil/matters/M-0001/fee_request", json={"amount": 5000, "for": "Appearance"}).json()["card"]
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    r = cl.post(f"/api/vakil/cards/{fee['id']}/decide", json={"yes": True, "hash": fee["hash"]})
    assert r.status_code == 428 and r.json()["detail"] == "fingerprint_needed"
    assert cl.post(f"/api/vakil/cards/{fee['id']}/challenge").json()["challenge_id"]
    assert cl.get("/api/vakil/rules").json()["limits"]["appeal_hc_civil"]["n"] == 90
    assert cl.post("/api/vakil/matters/M-0001/draft", json={"kind": "vakalatnama"}).json()["file"]["name"].endswith(".docx")
    assert cl.get("/api/vakil/day").json()["check"]
