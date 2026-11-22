"""G3 SUPPORT CALLS (docs/SUPPORT_GLOBAL_PLAN.md): the phone line feeds the support desk; one customer across channels;
warm transfer (whisper + press 1, call-back window when nobody picks up); the machine / phone-menu check on calls
Hoola makes (incl. Indian operator lines) with menu keys and a loop stop; the learned reply wait; idle / hold; fillers;
WhatsApp voice calls declined honestly with a call-back; the desk's Phone page in a real browser."""
import asyncio
import json
import os

import numpy as np
import pytest

from tests.test_seva_callcentre import ALLDAY, BASE, T, _call, _wait_ended, app_client, cc, fake_line, ready_script  # noqa: F401


# ---------------------------------------------------------------- listening: code only
def test_classify_what_answered():
    from app.callcentre import listen as LI
    assert LI.classify("Hello?")["kind"] == "human" and LI.classify("Haan ji, boliye")["sure"]
    assert LI.classify("Welcome to City Bank. For English press one, for Hindi press two")["kind"] == "ivr"
    assert LI.classify("Hindi ke liye do dabaye")["kind"] == "ivr"
    vm = LI.classify("Hi, you've reached Ravi. Please leave a message after the tone.")
    assert vm["kind"] == "voicemail" and vm["sure"]
    un = LI.classify("Aap jis number par call kar rahe hain vah abhi switch off hai")
    assert un["kind"] == "unreachable" and un["sure"]
    assert LI.classify("जिस नंबर पर आप कॉल कर रहे हैं वह अभी बंद है")["kind"] == "unreachable"
    assert LI.classify("The number you have dialled is not reachable")["kind"] == "unreachable"
    assert LI.classify("The mailbox is full and cannot accept any new messages")["kind"] == "mailbox_full"
    assert LI.classify("")["sure"] is False


def test_menu_keys_and_loop_stop():
    from app.callcentre import listen as LI
    assert LI.keys_ok("2") == (True, "2") and LI.keys_ok("one") == (True, "1") and LI.keys_ok("*0#")[0]
    ok, why = LI.keys_ok("4567 8901")
    assert not ok and "account" in why
    assert not LI.keys_ok("abc")[0]
    w = LI.MenuWatch()
    menu = "For billing press one, for a new connection press two, for anything else press nine"
    assert w.heard(menu) is False
    w.press("9")
    assert w.heard(menu) is False                   # back once after a key: maybe a mistake
    assert w.heard(menu + " please") is True        # twice: a loop
    w2 = LI.MenuWatch(max_presses=2)
    assert w2.press("1")[0] and w2.press("2")[0] and not w2.press("3")[0]


def test_reply_wait_learns_from_the_caller():
    from app.callcentre import listen as LI

    def talk(w, pause_ms, n=8):
        for _ in range(n):
            for _ in range(15):
                w.frame(True, 20)
            for _ in range(int(pause_ms / 20)):
                w.frame(False, 20)
        for _ in range(15):
            w.frame(True, 20)
    slow = LI.ReplyWait(0)
    talk(slow, 1000)
    assert slow.learned() > 1000 and slow.learned() <= LI.ReplyWait.CEIL
    quick = LI.ReplyWait(0)
    talk(quick, 200)
    assert quick.learned() < 800 and quick.learned() >= LI.ReplyWait.FLOOR
    w = LI.ReplyWait(1200)
    assert w.learned() == 1200                       # nothing heard yet: what we knew about them
    talk(w, 600)
    w.turn_ended()
    assert LI.blend(1200, 800) == 960 and LI.blend(0, 700) == 700
    assert LI.wait_words("ek minute ruko") and LI.wait_words("hold on please") and not LI.wait_words("my bill is wrong")


def test_key_tones_are_the_right_frequencies():
    from app.callcentre import audio as A
    pcm = A.dtmf("5", 8000)
    x = np.frombuffer(pcm, "<i2").astype(float)[:960]
    f = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1 / 8000)
    top = sorted(freqs[np.argsort(f)[-2:]])
    assert abs(top[0] - 770) < 15 and abs(top[1] - 1336) < 15
    assert len(A.dtmf("12", 8000)) == 2 * 2 * (960 + 800)


# ---------------------------------------------------------------- providers: the warm transfer
def test_providers_warm_transfer_shapes():
    from app.callcentre import providers as P
    body, ct = P.Plivo({}).warm_dial("Connecting you", "en-IN", "+919876543210", "+912040000000", "https://h/w", "https://h/d")
    assert 'confirmSound="https://h/w"' in body and 'confirmKey="1"' in body and 'action="https://h/d"' in body
    tb, _ = P.Twilio({}).warm_dial("Connecting", "en-IN", "+15550001", "+15550002", "https://h/w", "https://h/d")
    assert '<Number url="https://h/w"' in tb and 'action="https://h/d"' in tb
    wb, _ = P.Twilio({}).whisper("A caller about a bill. Press 1 to take the call.", "en-IN", "https://h/ok")
    assert "<Gather" in wb and 'action="https://h/ok"' in wb
    assert P.Twilio({}).whisper_accept({"Digits": "1"})[0] == "<Response></Response>"
    assert "Hangup" in P.Twilio({}).whisper_accept({"Digits": "2"})[0]
    assert P.KINDS["signalwire"].warm_ok and not P.KINDS["telnyx"].warm_ok
    cold, _ = P.Telnyx({}).warm_dial("Connecting", "en-IN", "+15550001", "+15550002", "https://h/w", "https://h/d")
    assert "https://h/w" not in cold and "+15550001" in cold
    pr = P.Provider()
    assert pr.dial_status({"DialStatus": "completed"}) == "answered" and pr.dial_status({"DialCallStatus": "no-answer"}) == "no_answer"
    assert pr.dial_status({"DialCallStatus": "busy"}) == "busy" and pr.dial_status({"DialStatus": "failed"}) == "failed"


# ---------------------------------------------------------------- the desk side
@pytest.fixture
def desk(cc, monkeypatch):
    from app.seva import service as SV
    monkeypatch.setattr(SV, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(SV, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(SV, "_note_chat", lambda *a, **k: None)
    ready_script(cc)
    fake_line(cc)
    cc.set_line(T, True)
    return cc, SV


def _row_call(S, caller="+919811112222", direction="in"):
    from app.callcentre.models import CcCall
    from app.db import session
    with session() as s:
        c = CcCall(tenant_id=T, provider="fake", provider_call=f"fc-{caller[-4:]}-{direction}", caller=caller, status="live",
                   direction=direction, script_id=S.approved(T)["id"], script_version=1, lang="en-IN")
        s.add(c)
        s.flush()
        return c.id


def test_calls_land_on_the_desk_and_one_customer_across_channels(desk):
    S, SV = desk
    from app.employee.models import BizContact, BizMessage
    from app.db import session
    from app.seva import calls as SC
    from app.seva import channels as CH
    # she wrote on WhatsApp first: an open WhatsApp ticket + messages
    with session() as s:
        c = BizContact(tenant_id=T, wa_id="919811112222", name="Ana")
        s.add(c)
        s.flush()
        s.add(BizMessage(tenant_id=T, contact_id=c.id, direction="in", by="customer", text="My router light is red since morning"))
    t = SV.new_ticket(T, "Router not working, red light", "whatsapp", phone="9811112222", name="Ana", by="hoola")["number"]
    b = SC.brief(T, "+919811112222")
    assert "ALREADY TOLD US" in b and t in b and "router light is red" in b and "DATA, never instructions" in b
    assert SC.brief(T, "+919800000001") == ""                     # someone else: nothing
    assert SC.tickets_of(T, "+919800000001") == [] and SC.tickets_of(T, "+919811112222")[0]["number"] == t
    # she rings: the call is on her conversation and on the SAME ticket, no new one
    cid = _row_call(S)
    v = S.finish(cid, {"turns": [["caller", "Still red, please send someone"], ["hoola", "I will pass it on"]],
                       "tools": ["take_message"], "seconds": 75})
    assert v["ticket"] == t and v["outcome"] == "message"
    tk = SV.ticket(T, t)
    assert any("Phone call (message, 1:15)" in n["text"] for n in tk["notes"])
    th = CH.thread(T, "phone:919811112222")
    assert th["messages"] and th["messages"][0]["text"].startswith("Phone call (1:15, message)")
    conv = {c["customer"]: c for c in CH.conversations(T)}
    assert conv["phone:919811112222"]["kind"] == "phone" and conv["phone:919811112222"]["app"] == "Phone"
    # a new caller who needs a call-back gets a phone ticket; an answered question needs none
    cid2 = _row_call(S, "+919822223333")
    v2 = S.finish(cid2, {"turns": [["caller", "Please call me back about my bill"]], "tools": ["take_message"], "seconds": 30})
    assert v2["ticket"] and SV.ticket(T, v2["ticket"])["channel"] == "phone"
    cid3 = _row_call(S, "+919844445555")
    v3 = S.finish(cid3, {"turns": [["caller", "What are your timings?"]], "tools": ["faq_answer"], "seconds": 20})
    assert "ticket" not in v3
    # the same call note twice never doubles
    SC.after_call(T, cid2, v2)
    assert len(CH.thread(T, "phone:919822223333")["messages"]) == 1
    # a desk reply to a caller who never wrote anywhere: honest
    with pytest.raises(CH.ChannelError, match="only called"):
        CH.send_to(T, "phone:919844445555", "Hello")


def test_complaint_and_status_on_a_call_use_the_desk(desk):
    S, SV = desk
    cid = _row_call(S, "+919811112222")
    c = S.CallCtx(T, cid, "+919811112222", S.approved(T))
    n = S.run_line_tool(c, "register_complaint", {"text": "The bill is double this month"})["ticket"]
    assert SV.ticket(T, n)["channel"] == "phone"
    st = S.run_line_tool(c, "ticket_status", {})["tickets"][0]
    assert st["number"] == n and n in st["status_line"]
    other = S.CallCtx(T, cid, "+919833334444", S.approved(T))
    assert S.run_line_tool(other, "ticket_status", {"ticket_no": n}).get("found") is False


def test_warm_transfer_whisper_and_nobody_picks_up(desk):
    S, SV = desk
    from app.callcentre import providers as P
    from app.callcentre.models import CcMessage
    from app.db import session
    cid = _row_call(S)
    c = S.CallCtx(T, cid, "+919811112222", S.approved(T))
    c.heard = "my internet is down for two days and I am very upset"
    plan = S.plan_handover(c, "angry")
    assert plan["mode"] == "transfer" and plan["warm"] and plan["handover_id"]
    from app.seva import handover as H
    h = H.get(T, plan["handover_id"])
    assert h["channel"] == "phone" and h["rule"] == "angry" and "internet is down" in h["packet"]["problem"]
    cl = app_client()
    tok = S.settings(T)["urls"]["answer"].split("/")[-2]
    t = S.ticket(cid)

    def hook(path, params):
        url = BASE + path
        return cl.post(path, data=params, headers={"X-Fake-Signature": P.Fake.sign("s3", "POST", url, params)})
    r = hook(f"/api/callcentre/hook/fake/{tok}/transfer/{cid}?t={t}", {}).json()
    assert r["action"] == "warm" and r["dial"] == "+919876543210" and "/whisper/" in r["whisper"] and "/dialdone/" in r["done"]
    wpath = r["whisper"].replace(BASE, "")
    w = hook(wpath, {}).json()
    assert w["action"] == "whisper" and "Press 1 to take the call" in w["text"] and h["ticket"] in w["text"] and "upset" in w["text"]
    assert hook(w["accept"].replace(BASE, ""), {"Digits": "1"}).json()["action"] == "connect"
    d = hook(r["done"].replace(BASE, ""), {"dial_status": "no-answer"}).json()
    assert d["action"] == "say" and "call you back between" in d["text"]
    assert S.call_row(cid)["outcome"] == "callback"
    with session() as s:
        assert s.query(CcMessage).filter_by(call_id=cid, kind="callback").count() == 1
    assert any("Warm transfer not answered" in n["text"] for n in SV.ticket(T, h["ticket"])["notes"])
    # warm transfer off: the plain transfer
    S.save_settings(T, warm_transfer=False)
    r2 = hook(f"/api/callcentre/hook/fake/{tok}/transfer/{cid}?t={t}", {}).json()
    assert r2["action"] == "dial"
    # a bad ticket never gets the whisper
    assert hook(f"/api/callcentre/hook/fake/{tok}/whisper/{cid}?t=bad", {}).status_code == 403


# ---------------------------------------------------------------- the bridge: recordings, keys, idle, fillers
class FakeSock:
    def __init__(self):
        self.sent = []

    async def recv(self):
        await asyncio.sleep(10)

    async def send(self, d):
        self.sent.append(d)

    async def close(self):
        pass


def _bridge(S, direction="out", caller="+919811112222"):
    from app.callcentre import bridge as B
    from app.callcentre import providers as P
    cid = _row_call(S, caller, direction)
    b = B.CallBridge(T, P.Fake({"secret": "s3"}), P.FakeLine(), FakeSock(), cid, f"fc-{caller[-4:]}-{direction}")
    b.script = S.approved(T)
    b.out = direction == "out"
    b.cc = S.CallCtx(T, cid, caller, b.script, out=b.out)
    return b, cid


def _notes(b):
    out = []
    while not b.q.empty():
        k, v = b.q.get_nowait()
        if k == "text":
            out.append(v)
    return out


def test_bridge_phone_menu_keys_and_loop(desk):
    S, _ = desk

    async def go():
        b, cid = _bridge(S)
        menu = "Welcome to City Telecom. For billing press one, for a new connection press two, to talk to us press nine"
        assert await b._what_answered(menu) is False
        assert b.cc.menu is not None and any("PHONE MENU" in n for n in _notes(b))
        from app.callcentre.models import CcCall
        from app.db import session
        with session() as s:
            assert s.get(CcCall, cid).answered_by == "menu"
        got = S.run_line_tool(b.cc, "press_keys", {"keys": "9"})
        assert got["press"] == "9"
        await b._press(got["press"])
        assert b.sock.sent and b.stats["keys"] == "9"
        assert "error" in S.run_line_tool(b.cc, "press_keys", {"keys": "123456"})
        assert await b._what_answered(menu) is False
        assert await b._what_answered(menu + " again") is True
        assert any(f["kind"] == "menu_loop" for f in b.flags)
        inb, _ = _bridge(S, "in", "+919800000009")
        assert "error" in S.run_line_tool(inb.cc, "press_keys", {"keys": "1"})      # not on a customer's call
    asyncio.run(go())


def test_bridge_voicemail_and_unreachable(desk):
    S, _ = desk
    from app.callcentre import providers as P
    from app.callcentre.models import CcCall
    from app.db import session

    async def go():
        b, cid = _bridge(S)
        assert await b._what_answered("Hi, you've reached Ravi. Please leave a message after the tone.") is True
        await asyncio.sleep(0.6)
        moved = [a for a in P.FAKE_ACTIONS if a["do"] == "transfer"]
        assert moved and f"/voicemail?out={cid}&ot=" in moved[-1]["url"] and b._outcome == "voicemail"
        with session() as s:
            assert s.get(CcCall, cid).answered_by == "machine"
        b2, cid2 = _bridge(S, caller="+919811110000")
        assert await b2._what_answered("Aap jis number par call kar rahe hain vah abhi switch off hai") is True
        await asyncio.sleep(0.5)
        assert any(a["do"] == "hangup" for a in P.FAKE_ACTIONS) and b2._outcome == "no_answer"
        b3, _ = _bridge(S, caller="+919811110001")
        assert await b3._what_answered("Hello, haan ji boliye") is False and b3._answer_kind == "human" and b3.cc.menu is None
    asyncio.run(go())


def test_bridge_idle_hold_and_filler(desk, monkeypatch):
    S, _ = desk
    import time
    from app.callcentre import listen as LI
    monkeypatch.setattr(LI, "FILLER_S", 0.05)

    async def go():
        b, _ = _bridge(S, "in")
        t = time.monotonic()
        b._last_voice, b._ai_until = t - 11, 0.0
        await b._idle(t)
        assert any("still there" in n for n in _notes(b))
        await b._idle(t + LI.IDLE_END_S + 1)
        assert any(f["kind"] == "silent" for f in b.flags) and any("goodbye" in n for n in _notes(b))
        h, _ = _bridge(S, "in", "+919800000002")
        h._hold_at = t - 1
        h._last_voice, h._ai_until = t - 15, 0.0
        await h._idle(t)
        assert not _notes(h)                                    # she asked to hold on: no nagging at 15 s
        f, _ = _bridge(S, "in", "+919800000003")

        def slow(cc, name, args):
            time.sleep(0.2)
            return {"answer": "10 to 7"}
        monkeypatch.setattr(S, "run_line_tool", slow)

        class FC:
            name, args, id = "faq_answer", {"question": "timings"}, "x1"

        class Sess:
            async def send_tool_response(self, **_):
                pass
        f.session = Sess()
        await f.run_tool(FC())
        assert any("one moment" in n for n in _notes(f)) and f.stats.get("fillers") == 1
    asyncio.run(go())


def test_learned_wait_reaches_the_next_call(desk, monkeypatch):
    S, _ = desk
    import contextlib
    from app.callcentre import bridge as B
    from app.callcentre.models import CcCaller
    from app.db import session
    from app.seva import service as SV
    from tests.test_seva_callcentre import FakeGemini
    SV.new_ticket(T, "My order 55 did not come", "whatsapp", phone="9811112222", by="hoola")
    S._remember_caller(T, "+919811112222", "en-IN", "")
    S.remember_wait(T, "+919811112222", 1100)
    with session() as s:
        assert s.query(CcCaller).filter_by(tenant_id=T).first().reply_wait_ms == 1100
    S.remember_wait(T, "+919811112222", 700)
    assert S.caller_info(T, "+919811112222")["reply_wait_ms"] == 860
    fake, cfgs = FakeGemini(), []

    @contextlib.asynccontextmanager
    async def connect(cfg):
        cfgs.append(cfg)
        yield fake
    monkeypatch.setattr(B, "connector", connect)
    cl = app_client()
    tok = S.settings(T)["urls"]["answer"].split("/")[-2]
    from app.callcentre import providers as P
    _call(S, fake, cl, tok, stop_when=lambda: any(a["do"] == "transfer" for a in P.FAKE_ACTIONS))
    _wait_ended(S, "9811112222")
    cfg = cfgs[0]
    assert cfg.realtime_input_config.automatic_activity_detection.silence_duration_ms == 860
    sysp = cfg.system_instruction.parts[0].text
    assert "WHAT THIS CALLER ALREADY TOLD US" in sysp and "order 55" in sysp


# ---------------------------------------------------------------- WhatsApp voice calls
def test_whatsapp_calls_declined_with_a_callback(desk):
    S, SV = desk
    from app.db import session
    from app.employee.models import BizChannel
    from app.seva import calls as SC
    from app.seva import channels as CH
    from app.employee import inbox
    inbox.set_channel(T, "1000200030004", "912000000000", token="EAAG-test-token")
    with session() as s:
        assert s.get(BizChannel, "1000200030004").tenant_id == T
    seen = []
    CH.set_transport(lambda m, u, headers=None, json=None, data=None, auth=None: (seen.append((m, u, json, headers)) or (200, {"success": True})))
    try:
        value = {"metadata": {"phone_number_id": "1000200030004"}, "contacts": [{"wa_id": "919877776666", "profile": {"name": "Ravi"}}],
                 "calls": [{"id": "wacid.1", "from": "919877776666", "event": "connect", "session": {"sdp_type": "offer", "sdp": "v=0"}}]}
        assert SC.wa_calls(value) == 1
        assert seen and seen[0][1].endswith("/1000200030004/calls") and seen[0][2]["action"] == "reject"
        assert seen[0][3]["Authorization"] == "Bearer EAAG-test-token"
        assert SC.wa_calls(value) == 0                                   # Meta retries: once
        tk = SC.tickets_of(T, "+919877776666")
        assert tk and SV.ticket(T, tk[0]["number"])["channel"] == "whatsapp"
        assert "WhatsApp voice call" in CH.thread(T, "wa:919877776666")["messages"][0]["text"]
        assert any("Rang on WhatsApp" in m["text"] for m in S.messages(T))
        S.save_settings(T, wa_calls="off")
        value["calls"][0]["id"] = "wacid.2"
        assert SC.wa_calls(value) == 0 and len(seen) == 1
    finally:
        CH.set_transport(None)


def test_phone_routes_and_tool(desk):
    S, SV = desk
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.seva.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(a)
    cid = _row_call(S)
    S.finish(cid, {"turns": [["caller", "Call me back please"]], "tools": ["take_message"], "seconds": 12})
    p = cl.get("/api/seva/phone").json()["phone"]
    assert p["line_on"] and p["warm_transfer"] and p["warm_possible"] and p["calls"][0]["ticket"] and p["calls"][0]["caller"].endswith("2222")
    assert "9811112222" not in p["calls"][0]["caller"] + p["calls"][0]["summary"]
    p2 = cl.put("/api/seva/phone", json={"warm_transfer": False, "wa_calls": "off"}).json()["phone"]
    assert p2["warm_transfer"] is False and p2["wa_calls"] == "off"
    assert cl.put("/api/seva/phone", json={"wa_calls": "maybe"}).status_code == 400
    import inspect
    from app.agent import seva_tools as ST
    assert 'what == "calls"' in inspect.getsource(ST)


# ---------------------------------------------------------------- the desk's Phone page in a real browser
@pytest.fixture
def p_server(desk, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "support", trust="seekh")
    S, SV = desk
    cid = _row_call(S)
    S.finish(cid, {"turns": [["caller", "My internet is down, call me back"]], "tools": ["take_message"], "seconds": 64})
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
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, S
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_phone_page_in_a_real_browser(p_server):
    base, browser, key, S = p_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/settings")
    pg.wait_for_selector("#spPhone")
    txt = pg.inner_text("#spPage").lower()
    for w in ("phone calls", "line on", "internet is down", "1:04"):
        assert w in txt, (w, txt[txt.find("your setup"):txt.find("your setup") + 900])
    assert "9811112222" not in txt
    assert pg.is_checked("#spPhone [name=warm_transfer]")
    pg.uncheck("#spPhone [name=warm_transfer]")
    pg.select_option("#spPhone [name=wa_calls]", "off")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/phone") and r.request.method == "PUT") as rr:
        pg.click("#spPhone button[type=submit]")
    assert rr.value.json()["phone"]["warm_transfer"] is False
    assert S.settings(T)["warm_transfer"] is False and S.settings(T)["wa_calls"] == "off"
    pg.wait_for_selector("#spPhone")
    pg.click("#spPage a[href='#/chat/phone%3A919811112222']")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Phone call (1:04')", timeout=15000)
    ctx.close()
    m = browser.new_context(viewport={"width": 390, "height": 900})
    m.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    mp = m.new_page()
    mp.on("pageerror", lambda e: errors.append(str(e)))
    mp.goto(base + "/console/support#/settings")
    mp.wait_for_selector("#spPhone")
    assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    m.close()
    assert not errors, errors
