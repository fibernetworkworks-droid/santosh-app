"""SUPPORT CHANNELS (G4 of docs/SUPPORT_GLOBAL_PLAN.md): every messaging app into the one support desk on the business's
own accounts - Telegram, Messenger, Instagram, SMS (Twilio, Vonage), LINE, Viber, Slack, X, Zalo, KakaoTalk, WeChat. Keys
sealed and never shown, every incoming call checked against that app's own signature, the answer engine (G2) and the
hand-over rules (G7) decide, the reply goes back on the same app inside its window, STOP ends messages, a person's chat
stays the person's, ticket updates go back on the same app. Each app's API is a recorded fake here. Walked in a browser."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"
BASE = "https://hoola.example"


@pytest.fixture
def ch(env, monkeypatch):
    from app.seva import channels as CH
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(S, "_note_chat", lambda *a, **k: None)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "public_base_url", BASE)
    calls = []

    def fake(method, url, headers=None, json=None, data=None, auth=None):
        calls.append({"method": method, "url": url, "headers": headers or {}, "json": json, "data": data, "auth": auth})
        if "getMe" in url or "setWebhook" in url or "sendMessage" in url:
            return 200, {"ok": True, "result": {}}
        if "viber" in url:
            return 200, {"status": 0}
        if "slack.com" in url:
            return 200, {"ok": True}
        if "zalo" in url:
            return 200, {"error": 0}
        if "weixin" in url and "token?" in url:
            return 200, {"access_token": "wxTOKEN"}
        if "weixin" in url:
            return 200, {"errcode": 0}
        if "graph.facebook.com" in url and "/me?" in url:
            return 200, {"id": "p1", "name": "Shop page"}
        return 200, {}
    CH.set_transport(fake)
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    yield CH, S, calls
    CH.set_transport(None)


def _sent(calls, part):
    return [c for c in calls if part in c["url"]]


def test_join_seals_the_keys(ch):
    CH, S, calls = ch
    with pytest.raises(CH.ChannelError, match="needs: bot_token"):
        CH.connect(T, "telegram", {})
    with pytest.raises(CH.ChannelError, match="closed Business Messages"):
        CH.connect(T, "google_business", {"x": "y"})
    v = CH.connect(T, "telegram", {"bot_token": "123456:SECRET-TOKEN-ABCDEFG"})
    assert v["status"] == "ok" and "webhook is set" in v["note"] and v["address"].startswith(BASE + "/api/support/in/")
    hook = _sent(calls, "setWebhook")[0]["json"]
    assert hook["url"] == v["address"] and hook["secret_token"]
    from app.db import session
    with session() as s:
        row = s.get(CH.SevaChannel, v["id"])
        assert "SECRET-TOKEN" not in row.sealed and "SECRET" not in json.dumps(CH.channels(T))
    assert v["hints"]["bot_token"] == "…DEFG"


def _tg(c, CH, text, uid=555, upd=1, secret=None):
    from app.db import session
    with session() as s:
        row = s.scalars(CH.select(CH.SevaChannel).where(CH.SevaChannel.kind == "telegram")).first()
        tok = row.token
    want = hashlib.sha256((tok + "123456:SECRET-TOKEN-ABCDEFG").encode()).hexdigest()[:48]
    body = {"update_id": upd, "message": {"message_id": upd, "from": {"id": uid, "first_name": "Ana"}, "chat": {"id": uid, "type": "private"},
                                         "text": text}}
    return c.post(f"/api/support/in/{tok}", json=body, headers={"X-Telegram-Bot-Api-Secret-Token": secret or want})


def test_telegram_in_and_out(ch):
    CH, S, calls = ch
    from app.main import app
    CH.connect(T, "telegram", {"bot_token": "123456:SECRET-TOKEN-ABCDEFG"})
    c = TestClient(app)
    assert _tg(c, CH, "what are your timings?", secret="wrong").status_code == 403
    assert CH.conversations(T) == []                                       # nothing read from a wrong signature
    assert _tg(c, CH, "what are your timings?").status_code == 200
    out = _sent(calls, "sendMessage")[-1]["json"]
    assert out["chat_id"] == 555 and "10 am to 7 pm" in out["text"]
    _tg(c, CH, "what are your timings?")                                   # Telegram retries the same update: once only
    assert len(_sent(calls, "sendMessage")) == 1
    th = CH.thread(T, "tg:555")
    assert [m["direction"] for m in th["messages"]] == ["in", "out"] and th["messages"][1]["decision"] == "answer"


def test_hand_over_then_quiet_then_a_person(ch):
    CH, S, calls = ch
    from app.main import app
    CH.connect(T, "telegram", {"bot_token": "123456:SECRET-TOKEN-ABCDEFG"})
    c = TestClient(app)
    _tg(c, CH, "I want to talk to a person", upd=10)
    line = _sent(calls, "sendMessage")[-1]["json"]["text"]
    assert "passed this to" in line and "request number" in line
    from app.seva import handover as H
    hs = H.handovers(T, "open")
    assert hs and hs[0]["customer"] == "tg:555" and hs[0]["channel"] == "telegram"
    n = len(_sent(calls, "sendMessage"))
    _tg(c, CH, "hello? anyone?", upd=11)
    assert len(_sent(calls, "sendMessage")) == n                           # a person has it: Hoola stays quiet
    CH.reply_as_person(T, "tg:555", "Hi Ana, this is Meena. Looking at it now.", "staff:Meena")
    assert _sent(calls, "sendMessage")[-1]["json"]["text"].startswith("Hi Ana") and H.handovers(T, "open")[0]["status"] == "taken"
    num = hs[0]["ticket"]
    S.update(T, num, status="pending", public="We need your router photo.")
    assert "router photo" in _sent(calls, "sendMessage")[-1]["json"]["text"]   # ticket updates go back on Telegram


def test_messenger_window_and_verify(ch):
    CH, S, calls = ch
    from app.main import app
    v = CH.connect(T, "messenger", {"page_token": "PAGETOKEN123456", "app_secret": "appsecret", "verify_token": "my words"})
    tok = v["address"].rsplit("/", 1)[1]
    c = TestClient(app)
    ok = c.get(f"/api/support/in/{tok}", params={"hub.mode": "subscribe", "hub.verify_token": "my words", "hub.challenge": "42"})
    assert ok.status_code == 200 and ok.text == "42"
    assert c.get(f"/api/support/in/{tok}", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "42"}).status_code == 403
    body = json.dumps({"object": "page", "entry": [{"messaging": [{"sender": {"id": "fb77"}, "recipient": {"id": "p1"},
                                                                    "message": {"mid": "m1", "text": "what are your timings"}}]}]}).encode()
    sig = "sha256=" + hmac.new(b"appsecret", body, hashlib.sha256).hexdigest()
    assert c.post(f"/api/support/in/{tok}", content=body, headers={"X-Hub-Signature-256": sig, "content-type": "application/json"}).status_code == 200
    out = _sent(calls, "/me/messages")[-1]["json"]
    assert out["recipient"]["id"] == "fb77" and "10 am" in out["message"]["text"]
    from app.db import session
    with session() as s:
        for m in s.scalars(CH.select(CH.SevaChatMsg).where(CH.SevaChatMsg.customer == "fb:fb77")).all():
            m.at = m.at - timedelta(hours=30)
    with pytest.raises(CH.ChannelError, match="within 24 hours"):
        CH.send_to(T, "fb:fb77", "late update")
    from app.social import inbox as SI
    assert SI._support_owns_dms(T, "facebook") and not SI._support_owns_dms(T, "instagram")


def test_sms_twilio_and_stop(ch):
    CH, S, calls = ch
    from app.main import app
    v = CH.connect(T, "twilio_sms", {"account_sid": "AC1", "auth_token": "twtoken", "from_number": "+15550001111"})
    tok = v["address"].rsplit("/", 1)[1]
    c = TestClient(app)

    def post(text, sid):
        form = {"From": "+15557654321", "To": "+15550001111", "Body": text, "MessageSid": sid}
        url = v["address"]
        base = url + "".join(f"{k}{form[k]}" for k in sorted(form))
        sig = base64.b64encode(hmac.new(b"twtoken", base.encode(), hashlib.sha1).digest()).decode()
        return c.post(f"/api/support/in/{tok}", content=urlencode(form), headers={"X-Twilio-Signature": sig,
                                                                                    "content-type": "application/x-www-form-urlencoded"})
    r = post("what are your timings", "SM1")
    assert r.status_code == 200 and r.text == "<Response></Response>"
    out = _sent(calls, "Messages.json")[-1]
    assert out["data"]["To"] == "15557654321" or out["data"]["To"].endswith("7654321")
    assert "10 am" in out["data"]["Body"] and out["auth"] == ("AC1", "twtoken")
    post("STOP", "SM2")
    assert CH.opted_out(T, "sms:+15557654321")
    with pytest.raises(CH.ChannelError, match="STOP"):
        CH.send_to(T, "sms:+15557654321", "hello")


def test_more_apps_signatures(ch):
    CH, S, calls = ch
    from app.main import app
    c = TestClient(app)
    # LINE
    v = CH.connect(T, "line", {"channel_token": "LINETOKEN1234", "channel_secret": "linesecret"})
    body = json.dumps({"events": [{"type": "message", "replyToken": "r", "source": {"userId": "U1"},
                                   "message": {"type": "text", "id": "l1", "text": "what are your timings"}}]}).encode()
    sig = base64.b64encode(hmac.new(b"linesecret", body, hashlib.sha256).digest()).decode()
    assert c.post(v["address"].replace(BASE, ""), content=body, headers={"X-Line-Signature": sig}).status_code == 200
    assert _sent(calls, "message/push")[-1]["json"]["to"] == "U1"
    assert c.post(v["address"].replace(BASE, ""), content=body, headers={"X-Line-Signature": "bad"}).status_code == 403
    # Viber
    v = CH.connect(T, "viber", {"auth_token": "VIBERTOKEN123", "sender_name": "Shop"})
    body = json.dumps({"event": "message", "message_token": 9, "sender": {"id": "V1", "name": "Bo"},
                       "message": {"type": "text", "text": "what are your timings"}}).encode()
    sig = hmac.new(b"VIBERTOKEN123", body, hashlib.sha256).hexdigest()
    assert c.post(v["address"].replace(BASE, ""), content=body, headers={"X-Viber-Content-Signature": sig}).status_code == 200
    assert _sent(calls, "send_message")[-1]["json"]["receiver"] == "V1"
    # Slack url_verification
    v = CH.connect(T, "slack", {"bot_token": "xoxb-1234567", "signing_secret": "slsecret"})
    body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
    ts = str(int(time.time()))
    sig = "v0=" + hmac.new(b"slsecret", b"v0:" + ts.encode() + b":" + body, hashlib.sha256).hexdigest()
    r = c.post(v["address"].replace(BASE, ""), content=body, headers={"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": sig})
    assert r.json() == {"challenge": "abc"}
    # X CRC
    v = CH.connect(T, "x", {"user_token": "XUSERTOKEN12", "consumer_secret": "xsecret"})
    r = c.get(v["address"].replace(BASE, ""), params={"crc_token": "crc1"})
    assert r.json()["response_token"] == "sha256=" + base64.b64encode(hmac.new(b"xsecret", b"crc1", hashlib.sha256).digest()).decode()
    # Zalo
    v = CH.connect(T, "zalo", {"access_token": "ZALOTOKEN1234", "app_id": "app9", "oa_secret": "zsecret"})
    body = json.dumps({"event_name": "user_send_text", "timestamp": "1700", "sender": {"id": "Z1"},
                       "message": {"text": "what are your timings", "msg_id": "z1"}}).encode()
    mac = "mac=" + hashlib.sha256(("app9" + body.decode() + "1700" + "zsecret").encode()).hexdigest()
    assert c.post(v["address"].replace(BASE, ""), content=body, headers={"X-ZEvent-Signature": mac}).status_code == 200
    assert _sent(calls, "oa/message/cs")[-1]["json"]["recipient"]["user_id"] == "Z1"
    # Vonage signed JWT
    v = CH.connect(T, "vonage_sms", {"api_key": "vk", "api_secret": "vs", "signature_secret": "vsig", "from_number": "Shop"})
    body = json.dumps({"from": "447700900000", "to": "Shop", "text": "what are your timings", "message_uuid": "vu1", "channel": "sms"}).encode()

    def b64(x):
        return base64.urlsafe_b64encode(x).rstrip(b"=").decode()
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64(json.dumps({"payload_hash": hashlib.sha256(body).hexdigest(), "exp": time.time() + 60}).encode())
    jwt = f"{h}.{p}." + b64(hmac.new(b"vsig", f"{h}.{p}".encode(), hashlib.sha256).digest())
    assert c.post(v["address"].replace(BASE, ""), content=body, headers={"Authorization": "Bearer " + jwt}).status_code == 200
    assert _sent(calls, "nexmo.com/v1/messages")[-1]["json"]["to"] == "447700900000"


def test_kakao_and_wechat_answer_in_the_same_call(ch):
    CH, S, calls = ch
    from app.main import app
    c = TestClient(app)
    v = CH.connect(T, "kakao", {})
    r = c.post(v["address"].replace(BASE, ""), json={"userRequest": {"utterance": "what are your timings", "user": {"id": "K1"}}})
    assert "10 am" in r.json()["template"]["outputs"][0]["simpleText"]["text"]
    with pytest.raises(CH.ChannelError, match="only while the customer is writing"):
        CH.send_to(T, "kakao:K1", "later update")
    v = CH.connect(T, "wechat", {"app_id": "wxapp", "app_secret": "wxsecret", "token": "wxtok"})
    q = {"timestamp": "1", "nonce": "2"}
    q["signature"] = hashlib.sha1("".join(sorted(["wxtok", "1", "2"])).encode()).hexdigest()
    path = v["address"].replace(BASE, "")
    assert c.get(path, params=q | {"echostr": "hello"}).text == "hello"
    xml = ("<xml><ToUserName>gh_1</ToUserName><FromUserName>W1</FromUserName><CreateTime>1</CreateTime><MsgType>text</MsgType>"
           "<Content>what are your timings</Content><MsgId>77</MsgId></xml>")
    r = c.post(path, params=q, content=xml.encode())
    assert "<ToUserName><![CDATA[W1]]>" in r.text and "10 am" in r.text
    assert c.post(path, params=q | {"signature": "bad"}, content=xml.encode()).status_code == 403


def test_routes_and_tools(ch):
    CH, S, calls = ch
    from app.agent import seva_tools as ST
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/seva/channels", json={"kind": "telegram", "keys": {"bot_token": "123456:SECRET-TOKEN-ABCDEFG"}})
    assert r.status_code == 200 and "SECRET" not in r.text
    ov = c.get("/api/seva/channels").json()
    assert ov["channels"][0]["kind"] == "telegram" and "google_business" in ov["catalog"]["not_built"]
    assert c.post(f"/api/seva/channels/{ov['channels'][0]['id']}/check").json()["status"] == "ok"
    assert c.post("/api/support/in/not-a-token", json={}).status_code == 404
    assert c.delete(f"/api/seva/channels/{ov['channels'][0]['id']}").json()["removed"]
    names = {t["name"]: t for t in ST.SEVA_TOOLS}
    assert "chats" in names["seva_dekho"]["input_schema"]["properties"]["what"]["enum"]
    assert "bot_token" not in json.dumps(names["seva"]["input_schema"])          # keys are never asked in chat


@pytest.fixture
def c_server(ch, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(get_settings(), "public_base_url", BASE)
    from app.employee import hire
    CH, S, calls = ch
    hire.hire(T, "support", trust="seekh")
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
        yield f"http://127.0.0.1:{port}", browser, KEY, CH, calls
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_channels_in_a_real_browser(c_server):
    base, browser, key, CH, calls = c_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/support#/settings")
    pg.wait_for_selector("#spChKind")
    pg.select_option("#spChKind", "telegram")
    pg.wait_for_selector("#spChKeys [name=k_bot_token]")
    assert pg.get_attribute("#spChKeys [name=k_bot_token]", "type") == "password"
    pg.fill("#spChKeys [name=k_bot_token]", "123456:SECRET-TOKEN-ABCDEFG")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/channels") and r.request.method == "POST") as rr:
        pg.click("#spChAdd button[type=submit]")
    assert rr.value.json()["status"] == "ok"
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Webhook address')", timeout=10000)
    assert "SECRET-TOKEN" not in pg.inner_text("#spPage")
    CH.handle(T, CH.channels(T)[0]["id"], [{"from": "555", "name": "Ana", "text": "what are your timings", "ext_id": "u1",
                                           "meta": {"chat_id": 555}}])
    pg.goto(base + "/console/support#/inbox")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Messages on your apps')", timeout=15000)
    pg.click("a[href='#/chat/tg%3A555']")
    pg.wait_for_selector("#spChat")
    pg.fill("#spChat [name=text]", "Hi Ana, anything else?")
    with pg.expect_response(lambda r: "/send" in r.url):
        pg.click("#spChat button[type=submit]")
    assert calls[-1]["json"]["text"] == "Hi Ana, anything else?"
    ctx.close()
    p2 = browser.new_context(viewport={"width": 390, "height": 900})
    p2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    m = p2.new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    m.goto(base + "/console/support#/settings")
    m.wait_for_selector("#spChKind")
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    p2.close()
    assert not errors, errors
