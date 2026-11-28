"""v0.999.68 EVERY PROVIDER: the AI Telecaller and the AI phone line work with the voice companies of every country -
Twilio, Plivo, Exotel, Telnyx, Vonage, SignalWire, Bandwidth, Sinch and jambonz (any local SIP carrier anywhere)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import xml.dom.minidom

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.callcentre import models as _models  # noqa: F401  (tables for the env fixture)

T = "default"
BASE = "https://hoola.test"
ALLDAY = {"open": "00:00", "close": "23:59", "days": [0, 1, 2, 3, 4, 5, 6]}
REAL = ["plivo", "exotel", "twilio", "telnyx", "vonage", "signalwire", "bandwidth", "sinch", "jambonz"]


def _rsa_pem() -> str:
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption()).decode()


CREDS = {
    "plivo": {"auth_id": "MA1", "auth_token": "tok"},
    "exotel": {"sid": "ex1", "api_key": "k", "api_token": "t", "flow_id": "99"},
    "twilio": {"account_sid": "AC1", "auth_token": "tok"},
    "telnyx": {"api_key": "KEY1", "public_key": "x", "application_id": "app1", "account_sid": "acc1"},
    "signalwire": {"space": "demo.signalwire.com", "project_id": "p1", "api_token": "tok", "signing_key": "sk"},
    "bandwidth": {"account_id": "9900", "username": "u", "password": "p", "application_id": "bwapp",
                  "callback_user": "cbu", "callback_password": "cbp"},
    "sinch": {"app_key": "ak", "app_secret": base64.b64encode(b"sinch-secret").decode()},
    "jambonz": {"api_key": "jk", "account_sid": "ja1", "webhook_secret": "whs", "base_url": "https://jb.example"},
}


@pytest.fixture
def cc(env, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.callcentre import providers as P
    from app.callcentre import service as S
    monkeypatch.setattr(S, "_llm", lambda system, text: "")
    S.LIVE.clear()
    P.FAKE_ACTIONS.clear()
    yield S
    S.LIVE.clear()
    P.set_transport(None)


def client():
    from app.callcentre.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    return TestClient(a)


# ---------------------------------------------------------------- the list
def test_every_provider_is_offered_with_its_keys(cc):
    from app.callcentre import providers as P
    from app.callcentre import rules as R
    S = cc
    for k in REAL:
        assert k in P.KINDS and k in R.PROVIDERS and P.KEYS[k], k
        assert P.KINDS[k].outbound, f"{k} cannot call out"
    st = S.settings(T)
    assert set(REAL) <= set(st["providers"])
    assert st["providers"]["vonage"]["keys"][1] == {"name": "private_key", "label": "Private key (paste the whole file)",
                                                    "multiline": True}
    assert st["providers"]["jambonz"]["where"] == "every country"
    assert R.providers_for("IN")[0] == "plivo" and "jambonz" in R.providers_for("IN")
    assert R.providers_for("US")[:2] == ["twilio", "telnyx"] and "bandwidth" in R.providers_for("US")
    assert "jambonz" in R.providers_for("NG") and "bandwidth" not in R.providers_for("NG")
    assert "infobip" in R.NOT_PRIMARY and "africastalking" in R.NOT_PRIMARY
    for k in REAL:
        assert S.SETUP.get(k), k
    # keys: what each one needs, a missing one named, the saved key kept when a box is left empty
    with pytest.raises(S.CcError, match="Webhook public key"):
        S.set_creds(T, "telnyx", {"api_key": "KEY1"})
    S.set_creds(T, "telnyx", CREDS["telnyx"])
    S.set_creds(T, "telnyx", {"api_key": "KEY2"})
    assert S.creds(T)["api_key"] == "KEY2" and S.creds(T)["public_key"] == "x"
    # switching company never carries the old keys over
    S.save_settings(T, provider="twilio")
    assert not S.settings(T)["creds_set"]
    # a Vonage key pasted into one line gets its line breaks back
    pem = _rsa_pem()
    S.set_creds(T, "vonage", {"application_id": "va", "signature_secret": "sec", "private_key": " ".join(pem.split("\n"))})
    serialization.load_pem_private_key(S.creds(T)["private_key"].encode(), None)
    with pytest.raises(S.CcError, match="whole Vonage private key"):
        S.set_creds(T, "vonage", {"application_id": "va", "signature_secret": "sec", "private_key": "nope"})


# ---------------------------------------------------------------- answers + audio of each company
def _doc(body: str, ct: str):
    if "xml" in ct:
        return xml.dom.minidom.parseString(body)
    return json.loads(body)


def test_every_provider_answers_and_streams(cc):
    from app.callcentre import providers as P
    creds = CREDS | {"vonage": {"application_id": "va", "private_key": _rsa_pem(), "signature_secret": "s"}}
    for k in REAL:
        p = P.get(k, creds[k])
        for body, ct in (p.stream("wss://h/ws?c=1&t=2", True, {"cc": "c1"}), p.say("Hello", "en-US", dial="+14155550100",
                                                                                     caller_id="+14155550199"),
                         p.say("Bye", "en-GB"), p.hold("Please hold", "en-US", "https://h/answer?try=1")):
            _doc(body, ct)                     # every answer is a valid document for that company
        assert "wss://h/ws?c=1" in p.stream("wss://h/ws?c=1&t=2", False, {"cc": "c1"})[0].replace("&amp;", "&")
    assert json.loads(P.get("jambonz", {}).stream("wss://x", False, {})[0])[0]["verb"] == "listen"
    assert json.loads(P.get("sinch", {}).stream("wss://x", False, {})[0])["action"]["name"] == "connectStream"
    assert json.loads(P.get("vonage", {}).stream("wss://x", False, {})[0])[-1]["endpoint"][0]["type"] == "websocket"
    assert 'mode="bidirectional"' in P.get("bandwidth", {}).stream("wss://x", False, {})[0]
    assert 'bidirectionalMode="rtp"' in P.get("telnyx", {}).stream("wss://x", False, {})[0]


def test_every_line_carries_audio_both_ways(cc):
    from app.callcentre import audio as A
    from app.callcentre import providers as P
    pcm = (b"\x00\x10\xff\x0f" * 400)
    ulaw = base64.b64encode(A.pcm_to_ulaw(pcm[:320])).decode()
    starts = {
        "telnyx": {"event": "start", "stream_id": "st1", "start": {"call_control_id": "cc1", "media_format": {}}},
        "bandwidth": {"eventType": "start", "metadata": {"callId": "c-1", "streamId": "s1", "streamParams": {"cc": "x"}}},
        "vonage": {"event": "websocket:connected", "content-type": "audio/l16;rate=16000", "cc": "x"},
        "sinch": {"event": "start", "callId": "sc1", "callHeaders": [{"key": "cc", "value": "x"}]},
        "jambonz": {"callSid": "jb1", "metadata": {"cc": "x"}},
    }
    for k, st in starts.items():
        line = P.get(k, {}).line()
        ev = line.parse(json.dumps(st))
        assert ev and ev[0]["type"] == "start", k
        out = line.out_audio(pcm) + line.flush()
        assert out, k
        if k in ("vonage", "sinch", "jambonz"):          # raw audio in binary frames
            assert all(isinstance(f, bytes) for f in out)
            assert line.parse(pcm[:640])[0] == {"type": "audio", "pcm": pcm[:640]}
            if k == "vonage":
                assert all(len(f) == 640 for f in out[:-1]) and line.rate == 16000
        else:
            assert all(isinstance(f, str) for f in out)
            media = {"telnyx": {"event": "media", "media": {"track": "inbound", "payload": ulaw}},
                     "bandwidth": {"eventType": "media", "track": "inbound", "payload": ulaw}}[k]
            assert line.parse(json.dumps(media))[0]["type"] == "audio"
    assert P.get("telnyx", {}).line().parse('{"event": "media", "media": {"track": "outbound", "payload": ""}}') == []
    assert P.get("vonage", {}).line().parse('{"event": "websocket:dtmf", "digit": "0"}')[0]["digit"] == "0"
    assert json.loads(P.get("jambonz", {}).line().clear()) == {"type": "killAudio"}
    assert json.loads(P.get("bandwidth", {}).line().clear()) == {"eventType": "clear"}


# ---------------------------------------------------------------- every webhook checked by its own company's rule
def test_signatures_of_every_company():
    from app.callcentre import providers as P
    body = '{"status":"completed","uuid":"u1"}'
    # Telnyx: Ed25519 over "timestamp|body"
    sk = ed25519.Ed25519PrivateKey.generate()
    pk = base64.b64encode(sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    ts = str(int(time.time()))
    sig = base64.b64encode(sk.sign(f"{ts}|{body}".encode())).decode()
    tx = P.get("telnyx", {"public_key": pk})
    h = {"telnyx-timestamp": ts, "telnyx-signature-ed25519": sig, "x-hoola-raw": body}
    assert tx.verify("POST", "u", {}, h)
    assert not tx.verify("POST", "u", {}, h | {"x-hoola-raw": body + " "})
    assert not tx.verify("POST", "u", {}, h | {"telnyx-timestamp": str(int(ts) - 1000)})      # too old
    # Vonage: JWT signed with her signature secret, carrying the body's hash
    tok = jwt.encode({"iat": int(time.time()), "payload_hash": hashlib.sha256(body.encode()).hexdigest()}, "vsec", "HS256")
    vg = P.get("vonage", {"signature_secret": "vsec"})
    assert vg.verify("POST", "u", {}, {"Authorization": f"Bearer {tok}", "x-hoola-raw": body})
    assert not vg.verify("POST", "u", {}, {"Authorization": f"Bearer {tok}", "x-hoola-raw": body.replace("u1", "u2")})
    assert not vg.verify("POST", "u", {}, {"Authorization": "Bearer " + jwt.encode({"a": 1}, "other", "HS256")})
    # Bandwidth: the callback user / password she set on her application
    bw = P.get("bandwidth", CREDS["bandwidth"])
    good = "Basic " + base64.b64encode(b"cbu:cbp").decode()
    assert bw.verify("POST", "u", {}, {"Authorization": good})
    assert not bw.verify("POST", "u", {}, {"Authorization": "Basic " + base64.b64encode(b"cbu:no").decode()})
    # Sinch: HMAC-SHA256 over method, body MD5, content type, timestamp, path
    sec = CREDS["sinch"]["app_secret"]
    s_sig = P.sinch_signature(sec, "POST", "/api/callcentre/hook/sinch/tok/answer", "application/json", "2026-11-21T10:00:00Z", body)
    hs = {"authorization": f"Application ak:{s_sig}", "content-type": "application/json", "x-timestamp": "2026-11-21T10:00:00Z",
          "x-hoola-raw": body}
    sn = P.get("sinch", CREDS["sinch"])
    assert sn.verify("POST", "https://h/api/callcentre/hook/sinch/tok/answer", {}, hs)
    assert not sn.verify("POST", "https://h/api/callcentre/hook/sinch/tok/hangup", {}, hs)
    # jambonz: t=..,v1=HMAC-SHA256(secret, "t.body")
    v1 = hmac.new(b"whs", f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    jb = P.get("jambonz", CREDS["jambonz"])
    assert jb.verify("POST", "u", {}, {"jambonz-signature": f"t={ts},v1={v1}", "x-hoola-raw": body})
    assert not jb.verify("POST", "u", {}, {"jambonz-signature": f"t={ts},v1={v1}", "x-hoola-raw": "{}"})
    # SignalWire: the Twilio algorithm with her signing key
    url, params = "https://h/api/callcentre/hook/signalwire/tok/answer", {"CallSid": "S1", "From": "+14155550100"}
    sw = P.get("signalwire", CREDS["signalwire"])
    assert sw.verify("POST", url, params, {"X-SignalWire-Signature": P.twilio_signature("sk", url, params)})
    assert not sw.verify("POST", url, params, {"X-SignalWire-Signature": P.twilio_signature("tok", url, params)})


# ---------------------------------------------------------------- placing a call with each company
def test_every_company_places_a_call():
    from app.callcentre import providers as P
    sent: list[httpx.Request] = []
    reply = {"telnyx": {"call_sid": "TX9"}, "vonage": {"uuid": "VG9"}, "signalwire": {"sid": "SW9"},
             "bandwidth": {"callId": "BW9"}, "sinch": {"callId": "SN9"}, "jambonz": {"sid": "JB9"}}
    creds = CREDS | {"vonage": {"application_id": "va", "private_key": _rsa_pem(), "signature_secret": "s"}}
    for k, rid in reply.items():
        sent.clear()
        P.set_transport(httpx.MockTransport(lambda r, rid=rid: (sent.append(r), httpx.Response(201, json=rid))[1]))
        try:
            got = P.get(k, creds[k]).dial("+447700900000", "+442079460000", "https://h/answer?out=1", "https://h/hangup?out=1",
                                          "https://h/machine?out=1")
        finally:
            P.set_transport(None)
        assert got["call"] == next(iter(rid.values())), k
        r = sent[0]
        from urllib.parse import unquote
        body = unquote(r.content.decode())
        assert "447700900000" in body and "https://h/answer?out=1" in body.replace("\\/", "/"), k
        if k == "telnyx":
            assert r.url.path == "/v2/texml/calls/app1" and r.headers["authorization"] == "Bearer KEY1"
            assert json.loads(body)["MachineDetection"] == "DetectMessageEnd"
        if k == "vonage":
            claims = jwt.decode(r.headers["authorization"][7:], options={"verify_signature": False})
            assert claims["application_id"] == "va" and json.loads(body)["machine_detection"] == "continue"
        if k == "signalwire":
            assert r.url.host == "demo.signalwire.com" and r.url.path == "/api/laml/2010-04-01/Accounts/p1/Calls.json"
        if k == "bandwidth":
            j = json.loads(body)
            assert r.url.path == "/api/v2/accounts/9900/calls" and j["machineDetection"]["mode"] == "async"
            assert j["username"] == "cbu"
        if k == "sinch":
            j = json.loads(body)
            assert j["customCallout"]["ace"] == "https://h/answer?out=1" and json.loads(j["customCallout"]["ice"])["action"]["amd"]
        if k == "jambonz":
            assert r.url.host == "jb.example" and r.url.path == "/v1/Accounts/ja1/Calls"
            assert json.loads(body)["amd"]["actionHook"]["url"] == "https://h/machine?out=1"


# ---------------------------------------------------------------- one webhook, several events (Vonage end to end)
def _vonage_post(cl, path, body):
    raw = json.dumps(body)
    tok = jwt.encode({"iat": int(time.time()), "payload_hash": hashlib.sha256(raw.encode()).hexdigest()}, "vsec", "HS256")
    return cl.post(path, content=raw, headers={"content-type": "application/json", "Authorization": f"Bearer {tok}"})


def test_vonage_call_list_end_to_end(cc):
    from app.callcentre import outbound as O
    from app.callcentre import providers as P
    S = cc
    S.make_script(T, "Cool Air Services, London. AC sales and service.\nQ: Timings?\nA: 10 am to 7 pm.")
    S.edit_script(T, business="Cool Air Services")
    card = S.submit(T)
    S.decide_script(T, card["script_id"], True, card["hash"])
    S.save_settings(T, provider="vonage", number="+442079460000", hours=ALLDAY, max_concurrent=3, country="GB")
    S.set_creds(T, "vonage", {"application_id": "va", "private_key": _rsa_pem(), "signature_secret": "vsec"})
    S.confirm_country(T, "GB")
    c = O.create(T, "Winter service", goal="the service visit you booked", daily_cap=500, start_hour="00:00",
                 end_hour="23:59", voicemail="This is Hoola for Cool Air Services. We will call again.")
    O.add_people(T, c["id"], rows=[{"Name": "Sam", "Phone": "+447700900000", "Consent": "customer",
                                    "Timezone": "Europe/London"}], basis="customer")
    card = O.start_card(T, c["id"])
    assert card["problems"] == [] and card["callable"] == 1, card
    sent: list[httpx.Request] = []

    def fake(r):
        sent.append(r)
        return httpx.Response(201, json={"uuid": "VG1"}) if r.method == "POST" else httpx.Response(204)
    P.set_transport(httpx.MockTransport(fake))
    O.start(T, c["id"], card["hash"])
    import datetime as _dt
    from unittest import mock
    with mock.patch("app.callcentre.countries.can_call_now", lambda *a, **k: (True, "")):
        assert O.tick() == 1
    dial = json.loads(sent[0].content)
    hang = dial["event_url"][0]
    cl = client()
    p_hang = hang.replace(BASE, "")
    # a status event that needs nothing done
    assert _vonage_post(cl, p_hang, {"status": "ringing", "uuid": "VG1"}).status_code == 200
    # a bad signature is refused
    assert cl.post(p_hang, json={"status": "completed"}, headers={"Authorization": "Bearer x"}).status_code == 403
    # the answer: a WebSocket stream to the AI
    r = _vonage_post(cl, dial["answer_url"][0].replace(BASE, ""), {"uuid": "VG1", "from": "442079460000", "to": "447700900000"})
    ncco = r.json()
    assert ncco[-1]["action"] == "connect" and ncco[-1]["endpoint"][0]["uri"].startswith("wss://hoola.test/api/callcentre/ws/vonage/")
    # the answering-machine event on the SAME event URL -> the call is moved to her voicemail line
    sent.clear()
    assert _vonage_post(cl, p_hang, {"status": "machine", "uuid": "VG1"}).status_code == 200
    put = [x for x in sent if x.method == "PUT"]
    assert put and put[0].url.path == "/v1/calls/VG1"
    vm = json.loads(put[0].content)["destination"]["url"][0]
    assert "/voicemail?out=" in vm
    r = _vonage_post(cl, vm.replace(BASE, ""), {})
    assert r.json()[0]["action"] == "talk" and "Cool Air Services" in r.json()[0]["text"]
    assert O.people(T, c["id"])[0]["outcome"] == "voicemail"
    _ = _dt


def test_sinch_and_jambonz_events_on_one_url(cc):
    from app.callcentre import providers as P
    sn = P.get("sinch", CREDS["sinch"])
    assert sn.event({"event": "ice"}, "answer") == "answer" and sn.event({"event": "dice"}, "answer") == "end"
    assert sn.event({"event": "pie"}, "answer") == "other" and sn.answered_by({"amd": {"status": "machine"}}) == "machine"
    jb = P.get("jambonz", CREDS["jambonz"])
    assert jb.event({"call_status": "ringing"}, "hangup") == "other" and jb.event({"call_status": "completed"}, "hangup") == "end"
    assert jb.event({"type": "amd_machine_detected"}, "machine") == "machine"
    assert jb.event({"type": "amd_human_detected"}, "machine") == "other"
    bw = P.get("bandwidth", CREDS["bandwidth"])
    assert bw.event({"eventType": "initiate"}, "answer") == "answer" and bw.event({"eventType": "disconnect", "cause": "busy"},
                                                                                  "hangup") == "end"
    assert bw.end_status({"cause": "busy"}) == "busy"
    assert bw.event({"eventType": "machineDetectionComplete", "machineDetectionResult": {"value": "answering-machine"}},
                    "machine") == "machine"
    assert P._num("447700900000") == "+447700900000" and P._num("9811112222") == "+919811112222"
    assert P._num({"type": "number", "endpoint": "+14155550100"}) == "+14155550100"
