"""v0.999.67 AI TELECALLER + BUSINESS BRAIN + GLOBAL: Hoola makes and speaks every call, only to people in her data,
answers from her approved business knowledge, and follows the calling rules of the country it calls."""
from __future__ import annotations

import ipaddress
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.callcentre import models as _models  # noqa: F401  (tables for the env fixture)

T = "default"
BASE = "https://hoola.test"
ALLDAY = {"open": "00:00", "close": "23:59", "days": [0, 1, 2, 3, 4, 5, 6]}


@pytest.fixture
def cc(env, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.callcentre import knowledge as K
    from app.callcentre import providers as P
    from app.callcentre import service as S
    monkeypatch.setattr(S, "_llm", lambda system, text: "")
    monkeypatch.setattr(K, "_RESOLVE", lambda host: [ipaddress.ip_address("10.0.0.1" if host.endswith(".internal")
                                                                            else "93.184.216.34")])
    S.LIVE.clear()
    P.FAKE_ACTIONS.clear()
    yield S
    S.LIVE.clear()
    K.set_transport(None)


def client():
    from app.callcentre.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    return TestClient(a)


def ready(S, cap=500.0):
    S.make_script(T, "Cool Air Services, Pune. AC sales and service.\nQ: What are your timings?\nA: 10 am to 7 pm, Monday to Saturday.")
    S.edit_script(T, business="Cool Air Services", steps=[{"name": "Greet", "say": "say who you are"},
                                                         {"name": "Book", "say": "offer a free site visit"}])
    card = S.submit(T)
    S.decide_script(T, card["script_id"], True, card["hash"])
    S.set_creds(T, "fake", {"secret": "s3"})
    S.save_settings(T, provider="fake", number="+912040004410", hours=ALLDAY, max_concurrent=3)


# ---------------------------------------------------------------- countries (global)
def test_country_rules():
    from app.callcentre import countries as CO
    assert CO.e164("98765 43210", "IN") == "+919876543210"
    assert CO.e164("020 7946 0000", "GB") == "+442079460000"
    assert CO.e164("+1 (415) 555-0100", "IN") == "+14155550100"           # its own country code wins
    assert CO.e164("0044 20 7946 0000", "IN") == "+442079460000"
    assert CO.e164("12", "GB") == ""
    assert CO.country_of("+442079460000") == "GB" and CO.country_of("+971501234567") == "AE" and CO.country_of("+14155550100") == "US"
    assert CO.tz_of("GB") == "Europe/London" and CO.tz_of("US") == ""              # the US needs a time zone column
    assert CO.tz_of("US", "America/New_York") == "America/New_York" and CO.tz_of("US", "Mars/Base") == ""
    # the PERSON's local hours: 10:00 UTC = 15:30 in India (ok), 05:00 in New York (not ok)
    at = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
    assert CO.can_call_now("IN", "Asia/Kolkata", "10:00", "19:00", at)[0]
    ok, why = CO.can_call_now("US", "America/New_York", "10:00", "19:00", at)
    assert not ok and "outside calling hours" in why
    assert not CO.can_call_now("US", "", at=at)[0]
    assert CO.window("IN", "07:00", "23:00") == ("09:00", "21:00")                 # never wider than the law's
    assert not CO.can_call_now("FR", "Europe/Paris", at=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc))[0]  # Saturday
    # who may be called
    assert CO.basis_ok("IN", "asked", False, False)[0]
    assert not CO.basis_ok("IN", "cold", False, False)[0] and CO.basis_ok("IN", "cold", True, False)[0]
    assert not CO.basis_ok("GB", "asked", False, False)[0]                         # not verified: she confirms first
    assert CO.basis_ok("GB", "asked", False, True)[0] and not CO.basis_ok("GB", "cold", True, True)[0]
    assert not CO.basis_ok("XX", "asked", True, True)[0]
    assert any(c["code"] == "IN" and c["checked"] for c in CO.summary())


# ---------------------------------------------------------------- the Business Brain
def test_knowledge_needs_her_approval_then_answers_calls(cc):
    S = cc
    from app.callcentre import knowledge as K
    v = K.add_source(T, "text", name="Price list", text=(
        "Split AC 1.5 ton\nThe 1.5 ton inverter split AC costs Rs 34,990 with free installation in Pune.\n\n"
        "Warranty\nEvery AC has 5 years of compressor warranty and 1 year on parts."))
    assert v["status"] == "waiting" and v["facts"] == 2 and K.search(T, "1.5 ton price") == []   # not live yet
    pv = K.preview(T, v["id"])
    with pytest.raises(K.KbError):
        K.approve(T, v["id"], "wrong")
    K.approve(T, v["id"], pv["pending_hash"])
    got = K.search(T, "how much is the 1.5 ton AC")
    assert got and "34,990" in got[0]["text"] and got[0]["kind"] == "price"
    assert "warranty" in K.search(T, "what warranty do you give")[0]["text"].lower()
    # on a call: a question not in the script FAQ is answered from her approved facts
    cx = S.CallCtx(T, "c1", "+919811112222", {"content": {"faqs": []}})
    out = S.faq_answer(cx, question="1.5 ton price kitna hai")
    assert any("34,990" in f for f in out["facts"]) and "34,990" in cx.seen_text
    assert S.faq_answer(cx, question="do you sell washing machines")["not_in_script"]
    # secrets never become knowledge
    with pytest.raises(K.KbError):
        K.add_source(T, "text", text="Staff login password is hunter2, card 4111 1111 1111 1111")


def test_knowledge_from_her_api_sheet_and_live_lookup(cc):
    from app.callcentre import knowledge as K
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path == "/products":
            return httpx.Response(200, json={"items": [{"name": "Wall fan", "price": "Rs 2,499", "secret_margin": "40%"},
                                                       {"name": "Tower fan", "price": "Rs 5,999", "secret_margin": "35%"}]})
        if req.url.path == "/orders":
            return httpx.Response(200, json={"data": [{"order": "A-77", "status": "Out for delivery", "phone": "x", "cost": "9"}]})
        if req.url.path.endswith("/export"):
            return httpx.Response(200, content=b"Branch,Address,Open\nKothrud,Paud Road,10-8\nBaner,Baner Road,11-9\n")
        return httpx.Response(404)
    K.set_transport(httpx.MockTransport(handler))
    v = K.add_source(T, "api", name="Products", url="https://api.shop.example/products", api_key="sk_live_SECRET",
                     path="items", fields=["name", "price"])
    assert v["facts"] == 2 and v["has_key"] and "sk_live_SECRET" not in json.dumps(v)
    assert seen[0].headers["authorization"] == "Bearer sk_live_SECRET"
    assert all("40%" not in f["text"] for f in K.preview(T, v["id"])["facts_preview"])    # only the fields she picked
    sh = K.add_source(T, "sheet", url="https://docs.google.com/spreadsheets/d/AbC123/edit#gid=0")
    assert sh["facts"] == 2 and "docs.google.com/spreadsheets/d/AbC123/export?format=csv" in str(seen[-1].url)
    with pytest.raises(K.KbError, match="private"):
        K.add_source(T, "url", url="https://intranet.internal/prices")
    with pytest.raises(K.KbError, match="https"):
        K.add_source(T, "url", url="http://shop.example/prices")
    # live: the caller's own number goes into her lookup address, only her fields come back, nothing is stored
    lv = K.add_source(T, "api", name="Orders", mode="live", url="https://api.shop.example/orders?phone={phone}",
                      path="data", fields=["order", "status"], lookup="order status by the caller's number")
    assert lv["status"] == "waiting"
    assert K.lookup(T, lv["id"], "+919811112222")["error"]                            # not approved yet
    K.approve(T, lv["id"], K.preview(T, lv["id"])["pending_hash"])
    got = K.lookup(T, lv["id"], "+919811112222")
    assert got["rows"] == [{"order": "A-77", "status": "Out for delivery"}]
    assert "phone=%2B919811112222" in str(seen[-1].url)
    from app.callcentre import service as S
    specs = {x["name"]: x for x in S.line_specs({"content": {"can": {}}}, tenant=T)}
    assert "lookup" in specs and lv["id"] in specs["lookup"]["input_schema"]["properties"]["source"]["enum"]
    # a re-read that changes approved facts waits for her again (unless she trusts updates)
    K.approve(T, v["id"], K.preview(T, v["id"])["pending_hash"])
    def handler2(req):
        return httpx.Response(200, json={"items": [{"name": "Wall fan", "price": "Rs 2,799"}]})
    K.set_transport(httpx.MockTransport(handler2))
    assert K.sync(T, v["id"])["status"] == "waiting" and K.search(T, "wall fan price") == []


# ---------------------------------------------------------------- AI calls out
def _list(S, **kw):
    from app.callcentre import outbound as O
    c = O.create(T, "Diwali AC offer", goal="the AC enquiry you sent", daily_cap=500, fields=["need", "visit_day"],
                 voicemail="This is Hoola for Cool Air Services about your AC enquiry. We will call again tomorrow.", **kw)
    return O, c


def test_list_people_gates_and_her_tap(cc, monkeypatch):
    S = cc
    O, c = _list(S, start_hour="00:00", end_hour="23:59")
    got = O.add_people(T, c["id"], rows=[
        {"Name": "Ravi", "Mobile": "98111 12222", "Need": "2 ACs", "Consent": "yes"},
        {"Name": "Om Sai Clinic", "Mobile": "9822233333", "Consent": "cold"},
        {"Name": "Sam", "Mobile": "+44 20 7946 0000", "Consent": "yes"},
        {"Name": "Dup", "Mobile": "+91 98111 12222"},
        {"Name": "Bad", "Mobile": "12"}])
    assert got["added"] == 3 and got["duplicates"] == 1 and got["why_skipped"] == {"not a phone number": 1}
    card = O.start_card(T, c["id"])
    assert "no approved call script yet" in " ".join(card["problems"])
    ready(S)
    card = O.start_card(T, c["id"])
    assert card["problems"] == [] and card["callable"] == 1                        # only Ravi
    held = card["held"]
    assert any("140" in k for k in held) and any("United Kingdom" in k for k in held)
    with pytest.raises(O.OutError, match="changed"):
        O.start(T, c["id"], "nope")
    from app.callcentre import providers as P
    assert O.tick() == 0 and not [a for a in P.FAKE_ACTIONS if a["do"] == "dial"]   # nothing before her tap
    O.start(T, c["id"], card["hash"])
    assert O.tick() == 1
    d = [a for a in P.FAKE_ACTIONS if a["do"] == "dial"]
    assert len(d) == 1 and d[0]["to"] == "+919811112222" and d[0]["from"] == "+912040004410"
    assert "?out=ccc" in d[0]["answer"] and "&ot=" in d[0]["answer"] and d[0]["machine"].endswith(d[0]["answer"].split("?")[1])
    assert O.tick() == 0                                                            # Ravi is being called; others held
    # confirming the UK law lets Sam in (asked), and the cold Indian list stays held without a 140 line
    S.confirm_country(T, "GB")
    assert O.start_card(T, c["id"])["callable"] == 2


def _answer(cl, url_q, params):
    from app.callcentre import providers as P
    path = "/api/callcentre/hook/fake/" + url_q
    full = BASE + path
    p_ = path.split("?")[0]
    return cl.post(path, data=params, headers={"X-Fake-Signature": P.Fake.sign("s3", "POST", full, params)})


def test_answer_machine_retry_and_never_again(cc):
    S = cc
    O, c = _list(S, start_hour="00:00", end_hour="23:59", max_tries=2, retry_min=60)
    ready(S)
    O.add_people(T, c["id"], rows=[{"Name": "Ravi", "Phone": "9811112222", "Consent": "yes"},
                                   {"Name": "Priya", "Phone": "9822211111", "Consent": "yes"}])
    O.start(T, c["id"], O.start_card(T, c["id"])["hash"])
    assert O.tick() == 2
    from app.callcentre import providers as P
    d1, d2 = [a for a in P.FAKE_ACTIONS if a["do"] == "dial"]
    cl = client()
    tok = d1["answer"].split("/hook/fake/")[1].split("/")[0]
    # Ravi picks up -> a stream to the AI with a one-time ticket
    q1 = d1["answer"].split("?")[1]
    r = _answer(cl, f"{tok}/answer?{q1}", {"call": "prov-1", "from": "+912040004410", "answered_by": "human"})
    body = r.json()
    assert r.status_code == 200 and body["action"] == "stream" and "/api/callcentre/ws/fake/" in body["url"]
    # Priya's answering machine -> her voicemail, then a later try
    q2 = d2["answer"].split("?")[1]
    r = _answer(cl, f"{tok}/answer?{q2}", {"call": "prov-2", "answered_by": "machine"})
    assert r.json()["action"] == "say" and "Cool Air Services" in r.json()["text"]
    people = {p["name"]: p for p in O.people(T, c["id"])}
    assert people["Priya"]["status"] == "retry" and people["Priya"]["outcome"] == "voicemail"
    # no answer on the 2nd (last) try -> done, no more calls
    from app.callcentre.models import CcTarget
    from app.db import session
    with session() as s:
        s.get(CcTarget, people["Priya"]["id"]).next_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert O.tick() == 1
    d3 = [a for a in P.FAKE_ACTIONS if a["do"] == "dial"][-1]
    q3 = d3["hangup"].split("?")[1]
    r = _answer(cl, f"{tok}/hangup?{q3}", {"status": "no-answer"})
    assert r.status_code == 200
    p = {x["name"]: x for x in O.people(T, c["id"])}["Priya"]
    assert p["status"] == "done" and p["outcome"] == "no_answer" and p["tries"] == 2
    # a tampered ticket is refused
    r = _answer(cl, f"{tok}/answer?out={d1['answer'].split('out=')[1].split('&')[0]}&ot=1.bad", {"answered_by": "human"})
    assert r.json().get("action") != "stream"
    # Ravi said "don't call me" on the call -> never again, on any list
    from app.callcentre.models import CcCall
    with session() as s:
        call = s.query(CcCall).filter_by(provider_call="prov-1").first()
        cid_call = call.id
    cx = S.CallCtx(T, cid_call, "+919811112222", {"content": {}}, out=True)
    S.run_line_tool(cx, "do_not_call", {})
    assert {x["name"]: x for x in O.people(T, c["id"])}["Ravi"]["status"] == "dnd"
    c2 = O.create(T, "Second list", daily_cap=100)
    got = O.add_people(T, c2["id"], rows=[{"Name": "Ravi", "Phone": "+919811112222"}])
    assert got["added"] == 0 and got["why_skipped"] == {"said do not call": 1}


def test_outbound_tools_and_persona(cc):
    S = cc
    O, c = _list(S, start_hour="00:00", end_hour="23:59")
    ready(S)
    O.add_people(T, c["id"], rows=[{"Name": "Ravi", "Phone": "9811112222", "Need": "2 ACs", "Consent": "yes"}])
    O.start(T, c["id"], O.start_card(T, c["id"])["hash"])
    O.tick()
    from app.callcentre.models import CcCall
    from app.db import session
    with session() as s:
        call = s.query(CcCall).filter_by(direction="out").first()
        call_id = call.id
    cx = S.CallCtx(T, call_id, "+919811112222", {"content": {"can": {}}}, out=True)
    cx.fields = c["fields"]
    names = {x["name"] for x in S.line_specs({"content": {"can": {}}}, cx)}
    assert {"save_result", "do_not_call", "call_back", "faq_answer", "end_call"} <= names
    inbound = {x["name"] for x in S.line_specs({"content": {"can": {}}}, S.CallCtx(T, "x", "", {"content": {}}))}
    assert "save_result" not in inbound and "do_not_call" not in inbound          # only on calls Hoola made
    S.run_line_tool(cx, "save_result", {"need": "2 x 1.5 ton", "visit_day": "Saturday", "salary": "secret", "interest": "hot"})
    res = O.people(T, c["id"])[0]["result"]
    assert res == {"need": "2 x 1.5 ton", "visit_day": "Saturday", "interest": "hot"}   # only her fields
    assert S.run_line_tool(cx, "call_back", {"when": "tomorrow 4 pm"})["saved"]
    # the persona: an AI that CALLED them, says so first, why, and what to bring back
    from app import voicelang as VL
    from app.callcentre import bridge as B
    target, camp = B._out_context(T, S.call_row(call_id))
    p = S.persona_out(T, S.approved(T), VL.LangState("en-IN", "caller"), target, camp, False)
    assert "YOU CALLED this person" in p and "an AI assistant calling for Cool Air Services about the AC enquiry you sent" in p
    assert "need (need)" in p and "2 ACs" in p and "CALL STEPS" in p and "Greet" in p
    # a Spanish-speaking person abroad: the line speaks Spanish and is told to say the AI line in Spanish
    st = VL.LangState("es-ES", "caller")
    assert st.base == "es-ES" and VL.transcription_codes(st) == ["es-ES", "en-US"]
    assert "(say this in Spanish)" in S.persona_out(T, S.approved(T), st, target, camp, False)
    assert VL.norm_code("en-US") == "en-US" and VL.norm_code("en") == "en-IN" and VL.norm_code("hi") == "hi-IN"
    # the call ends -> the person's row is settled (she asked for a later time -> one more call then)
    S.finish(call_id, {"turns": [["caller", "call me tomorrow"]], "tools": ["call_back"], "seconds": 40})
    p = O.people(T, c["id"])[0]
    assert p["status"] == "retry" and p["next_at"]


def test_twilio_provider():
    from app.callcentre import providers as P
    url = "https://hoola.test/api/callcentre/hook/twilio/tok/answer?out=c1&ot=1.x"
    params = {"CallSid": "CA1", "From": "+14155550100", "To": "+14155550199", "AnsweredBy": "machine_end_beep"}
    sig = P.twilio_signature("TOKEN", url, params)
    tw = P.get("twilio", {"account_sid": "AC1", "auth_token": "TOKEN"})
    assert tw.verify("POST", url, params, {"X-Twilio-Signature": sig})
    assert not tw.verify("POST", url, params | {"To": "+1"}, {"X-Twilio-Signature": sig})
    assert tw.answered_by(params) == "machine" and tw.answered_by({"AnsweredBy": "human"}) == "human"
    xml, ct = tw.stream("wss://h/ws?c=1", False, {"cc": "c1"})
    assert "<Connect><Stream url=" in xml and 'name="cc"' in xml and ct == "application/xml"
    line = tw.line()
    ev = line.parse(json.dumps({"event": "start", "start": {"streamSid": "MZ1", "callSid": "CA1", "customParameters": {"cc": "c1"}}}))
    assert ev[0]["call"] == "CA1" and ev[0]["params"] == {"cc": "c1"}
    out = json.loads(line.out_audio(b"\x00\x10" * 80)[0])
    assert out["event"] == "media" and out["streamSid"] == "MZ1"
    assert json.loads(line.clear()) == {"event": "clear", "streamSid": "MZ1"}
    sent = []
    P.set_transport(httpx.MockTransport(lambda r: (sent.append(r), httpx.Response(201, json={"sid": "CA9"}))[1]))
    try:
        assert tw.dial("+14155550100", "+14155550199", "https://a", "https://h", "https://m") == {"call": "CA9"}
    finally:
        P.set_transport(None)
    form = dict(x.split("=", 1) for x in sent[0].content.decode().split("&"))
    assert form["MachineDetection"] == "DetectMessageEnd" and sent[0].url.path.endswith("/Accounts/AC1/Calls.json")


def test_test_chat_and_chat_tool_gates(cc, monkeypatch):
    S = cc
    ready(S)
    from app.callcentre import knowledge as K
    from app.callcentre import outbound as O
    v = K.add_source(T, "text", text="Free installation\nInstallation is free in Pune city for every AC bought this month.")
    K.approve(T, v["id"], K.preview(T, v["id"])["pending_hash"])
    seen = {}

    def llm(system, text):
        seen["system"] = system
        return "Installation is free in Pune, and the AC is only Rs 999 today!"
    monkeypatch.setattr(S, "_llm", llm)
    got = O.test_chat(T, [{"who": "customer", "text": "is installation free?"}])
    assert "Installation is free in Pune" in seen["system"] and got["facts_used"]
    assert "number 999" in got["flags"]                                            # an invented price is caught
    # the chat tool: knowledge with a key and starting a list are never chat work
    import asyncio
    from app.agent import callcentre_tools as CT
    from tests.test_life import conv_ctx
    ctx = conv_ctx()
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="only in the app"):
        asyncio.run(CT.call_centre(ctx, "knowledge_add", kind="api", url="https://x.example", api_key="k"))
    spec = next(t for t in CT.CALLCENTRE_TOOLS if t["name"] == "call_centre")
    assert "list_start" not in spec["input_schema"]["properties"]["action"]["enum"]
    lst = asyncio.run(CT.call_centre(ctx, "list_new", name="Renewals", daily_cap=200))
    out = asyncio.run(CT.call_centre(ctx, "list_card", list_id=lst["id"]))
    assert "only when she taps Start" in out["say"]
    from app.db import Event, session
    with session() as s:
        assert s.query(Event).filter_by(kind="callcentre_campaign_card").count() == 1


# ---------------------------------------------------------------- the Telecaller desk (its own section)
def test_desk_chat_hub_and_wiring(cc):
    from pathlib import Path
    from app import telecallerchat as TC
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert TC.summary(T) == {"hired": False}
    cat = {e["key"]: e for e in hire.catalog(T)}
    assert cat["telecaller"]["live"] is True
    hire.hire(T, "telecaller", trust="seekh")
    d = TC.summary(T)
    assert d["hired"] and "no approved call script yet" in " ".join(d["problems"])
    chat = TC.current(T)
    assert TC.is_tele(chat["id"]) and TC.owns(T, chat["id"])
    assert "only to the people you give me" in TC.greeting(T)
    blk = TC.block(T)
    assert "<telecaller_desk>" in blk and "ONLY her tap on Start begins the calls" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_tlc.is_tele(conversation_id)" in src and "adm.admit_families(_tlc.FAMILIES)" in src
    from app.agent import admit
    assert set(TC.FAMILIES) <= set(admit.FAMILY_OF.values())
    for f in ("callconv.py", "convs.py"):
        assert '"telecall")' in (root / "server/app" / f).read_text()
    assert "_cc_out.tick" in (root / "server/app/worker.py").read_text()
    from app.main import APP_VERSION, app
    c = TestClient(app)
    r = c.get("/console/telecaller")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "telecallerdesk.js" in r.text
    html = (root / "server/app/static/console/telecallerdesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "seodesk.css", "telecallerdesk.css", "telecallerdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/telecaller')" in (root / "server/app/static/console/v2.js").read_text()
    assert "'/console/telecaller'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


@pytest.fixture
def tc_server(cc, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    S = cc
    monkeypatch.setattr(S, "_llm", lambda system, text: "Yes, installation is free in Pune.")
    from app.callcentre import knowledge as K
    from app.callcentre import outbound as O
    from app.employee import hire
    hire.hire(T, "telecaller", trust="seekh")
    ready(S)
    K.add_source(T, "text", name="Price list", text="Split AC 1.5 ton\nThe 1.5 ton split AC costs Rs 34,990 with free installation.")
    c = O.create(T, "Diwali AC offer", goal="your AC enquiry", daily_cap=500, start_hour="00:00", end_hour="23:59")
    O.add_people(T, c["id"], rows=[{"Name": "Ravi", "Phone": "9811112222", "Consent": "yes"}])
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, c["id"]
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_telecaller_desk_in_a_real_browser(tc_server):
    base, browser, key, list_id = tc_server
    errors = []
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/telecaller")
        pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=20000)
        pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('only to the people you give me')", timeout=20000)
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, want in (("lists", "New call list"), ("calls", "No calls yet"), ("knowledge", "Price list"),
                          ("script", "Test chat"), ("incoming", "Incoming calls"), ("settings", "Countries Hoola may call"),
                          ("today", "Call lists")):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            try:
                pg.wait_for_function("(w) => document.querySelector('#tcPage').innerText.includes(w)", arg=want, timeout=10000)
            except Exception:
                raise AssertionError(f"{tab}: errors={errors} page={pg.inner_text('#tcPage')[:500]!r}")
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        if width == 1440 and scheme == "light":
            pg.goto(base + f"/console/telecaller#/list/{list_id}")
            pg.wait_for_function("() => document.querySelector('#tcPage').innerText.includes('Start calling')", timeout=10000)
            assert "1 people can be called" in pg.inner_text("#tcPage")
            pg.goto(base + "/console/telecaller#/script")
            pg.wait_for_selector("#tcTest input[name=text]")
            pg.fill("#tcTest input[name=text]", "is installation free?")
            pg.click("#tcTest button[type=submit]")
            pg.wait_for_function("() => document.querySelector('#tcTestLine').innerText.includes('installation is free')", timeout=10000)
            pg.goto(base + "/console/telecaller#/knowledge")
            pg.wait_for_selector("#tcPage a[href^='#/source/']")
            pg.click("#tcPage a[href^='#/source/']")
            pg.wait_for_selector("[data-src='yes']")
            pg.click("[data-src='yes']")
            pg.wait_for_function("() => !document.querySelector(\"[data-src='yes']\")", timeout=10000)
        ctx.close()
    assert not errors, errors
