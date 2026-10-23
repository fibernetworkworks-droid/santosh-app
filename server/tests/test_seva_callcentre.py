"""Call Centre Sahayak: audio codec / resampling, rules (hand-over words, masking, FAQ match, Plivo V3 signature), the
script flow (draft -> card -> HER tap only, hash-checked), call routing (line off / after hours / busy queue / overflow),
signed webhooks, and a whole phone call over the fake provider WebSocket with a fake Gemini Live session."""
import asyncio
import base64
import contextlib
import json
import math
import time

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.genai import types

from app.callcentre import models as _models  # noqa: F401  (tables for the env fixture)
from tests.test_life import conv_ctx

T = "default"
BASE = "https://hoola.test"
ALLDAY = {"open": "00:00", "close": "23:59", "days": [0, 1, 2, 3, 4, 5, 6]}


@pytest.fixture
def cc(env, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.callcentre import bridge as B
    from app.callcentre import providers as P
    from app.callcentre import service as S
    monkeypatch.setattr(S, "_llm", lambda system, text: "")
    monkeypatch.setattr(B, "HANDOVER_GRACE_S", 0.3)
    monkeypatch.setattr(B, "SAY_THEN_MOVE_S", 0.1)
    S.LIVE.clear()
    P.FAKE_ACTIONS.clear()
    yield S
    S.LIVE.clear()


def app_client():
    from app.callcentre.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: "default"))
    return TestClient(a)


def ready_script(S, can=None):
    S.make_script(T, "Sharma Clinic, Akot. Dant ka ilaaj.\nQ: Clinic ki timing kya hai?\nA: Som se Shani, subah 10 se shaam 7.\n"
                     "Q: Consultation fees kitni hai?\nA: Pehli consultation 300 rupaye.\nappointment bhi de sakte ho")
    S.edit_script(T, business="Sharma Clinic", can=can or {"appointments": True, "complaints": True, "ticket_status": True})
    card = S.submit(T)
    return S.decide_script(T, card["script_id"], True, card["hash"])


def fake_line(S, secret="s3", handover=True):
    S.set_creds(T, "fake", {"secret": secret})
    S.save_settings(T, provider="fake", hours=ALLDAY, max_concurrent=1, queue_max=1,
                    handover=[{"name": "Meghana", "phone": "9876543210"}] if handover else [])


# ---------------------------------------------------------------- audio
def test_audio_codec_and_resampling():
    from app.callcentre import audio as A
    t = np.arange(8000) / 8000
    tone = (np.sin(2 * math.pi * 440 * t) * 12000).astype("<i2").tobytes()
    back = np.frombuffer(A.ulaw_to_pcm(A.pcm_to_ulaw(tone)), dtype="<i2").astype(float)
    err = np.abs(back - np.frombuffer(tone, dtype="<i2")).max()
    assert len(A.pcm_to_ulaw(tone)) == 8000 and err < 500             # G.711 is lossy, within one step
    up, down = A.Resampler(8000, 16000), A.Resampler(24000, 8000)
    y = b"".join(up(tone[i:i + 320]) for i in range(0, len(tone), 320))   # fed in 20 ms chunks
    assert abs(len(y) // 2 - 16000) <= 2
    f = np.abs(np.fft.rfft(np.frombuffer(y, dtype="<i2").astype(float)))
    assert abs(int(np.argmax(f)) * 16000 / (len(y) // 2) - 440) < 3     # same pitch after resampling
    t24 = np.arange(24000) / 24000
    hi = (np.sin(2 * math.pi * 300 * t24) * 9000 + np.sin(2 * math.pi * 9000 * t24) * 9000).astype("<i2").tobytes()
    z = np.frombuffer(b"".join(down(hi[i:i + 4800]) for i in range(0, len(hi), 4800)), dtype="<i2").astype(float)
    spec = np.abs(np.fft.rfft(z))
    assert abs(len(z) - 8000) <= 2 and spec[300] > 20 * spec[1000:].max()   # 9 kHz removed, no aliasing
    ch = A.Chunker(3200)
    assert ch.add(b"\x00" * 5000) == [b"\x00" * 3200] and len(ch.flush(320)) == 1920


# ---------------------------------------------------------------- rules
def test_rules():
    from app.callcentre import providers as P
    from app.callcentre import rules as R
    assert R.handover_reason("mujhe kisi insaan se baat karni hai") == "asked_human"
    assert R.handover_reason("manager se baat karao please") == "asked_human"
    assert R.handover_reason("मुझे मैनेजर से बात करनी है") == "asked_human"
    assert R.handover_reason("mala manager shi bolaycha aahe") == "asked_human"
    assert R.handover_reason("yeh kya bakwas service hai") == "angry"
    assert R.handover_reason("insaan nahi chahiye, aap hi batao timing") == ""
    assert R.handover_reason("clinic kab khulta hai") == ""
    assert R.phone_e164("098765 43210") == "+919876543210" and R.mask_phone("+919876543210") == "98XXXX3210"
    m = R.mask_text("mera OTP 482913 hai aur number 9876543210, aadhaar 2345 6789 0123")
    assert "482913" not in m and "9876543210" not in m and "98XXXX3210" in m and "0123" not in m
    assert R.secret_in("mera OTP 482913 hai") == "otp_pin"
    faqs = [{"q": "Clinic ki timing kya hai?", "a": "10 se 7", "words": ["timing", "khulta", "band"]},
            {"q": "Fees kitni hai?", "a": "300", "words": ["fees", "charge", "paise"]}]
    assert R.best_faq("aapka clinic kab khulta hai", faqs)[0]["a"] == "10 se 7"
    assert R.best_faq("consultation ka charge kya hai", faqs)[0]["a"] == "300"
    assert R.best_faq("parking hai kya", faqs)[0] is None
    assert R.unscripted("Fees 500 rupaye hai", "Fees 300 rupaye") == ["number 500"]
    assert R.unscripted("Fees 300 rupaye", "Fees 300 rupaye") == []
    assert "vaada / guarantee" in R.unscripted("100% guarantee hai", "")
    p = R.parse_faq_text("Parking hai? Haan, bahar\nHome visit - nahi karte")
    assert p[0]["q"] == "Parking hai?" and p[1]["a"] == "nahi karte"
    assert R.blanks({"faqs": [{"q": "Address?", "a": "[blank]"}]}) == ["Address?"]
    # Plivo V3 signature = the official SDK's output (vectors made with plivo-python 4.63.0 utils/signature_v3.py)
    u = "https://h.example/api/callcentre/hook/plivo/tok/answer?b=2&a=1"
    params = {"CallUUID": "x1", "From": "919812345678", "To": "912212345678"}
    assert P.plivo_signature("TOKEN", "POST", u, "n123", params) == "YBkGW2F4dNKkCLxmaojtSIxbVp3nAtLDTKWxj9owa4I="
    assert P.plivo_signature("TOKEN", "GET", "wss://h/x?c=1", "n") == "xGSDjnS75/WfUKE547MmB6kGumn5/eRPuIT/cJIOCrU="
    assert P.plivo_valid("TOKEN", "POST", u, "n123", "junk,YBkGW2F4dNKkCLxmaojtSIxbVp3nAtLDTKWxj9owa4I=", params)
    assert not P.plivo_valid("TOKEN", "POST", u, "n123", "YBkGW2F4dNKkCLxmaojtSIxbVp3nAtLDTKWxj9owa4I=", params | {"From": "1"})
    line = P.PlivoLine()
    ev = line.parse(json.dumps({"event": "start", "start": {"callId": "c1", "streamId": "s1",
                                                            "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000}}}))
    assert ev[0]["call"] == "c1" and line.stream == "s1"
    from app.callcentre import audio as A
    pcm = (np.ones(160) * 3000).astype("<i2").tobytes()
    out = json.loads(line.out_audio(pcm)[0])
    assert out["event"] == "playAudio" and len(base64.b64decode(out["media"]["payload"])) == 160
    assert line.parse(json.dumps({"event": "media", "media": {"payload": out["media"]["payload"]}}))[0]["pcm"] == A.ulaw_to_pcm(A.pcm_to_ulaw(pcm))
    assert json.loads(line.clear()) == {"event": "clearAudio", "streamId": "s1"}
    ex = P.ExotelLine()
    assert ex.out_audio(b"\x00" * 1000) == [] and len(ex.out_audio(b"\x00" * 3000)) == 1      # 100 ms frames, multiples of 320


# ---------------------------------------------------------------- the script: only HER tap makes it run
def test_script_needs_her_tap(cc):
    S = cc
    with pytest.raises(S.CcError):
        S.set_line(T, True)                                          # no approved script yet
    d = S.make_script(T, "Sharma Clinic. Q: Timing kya hai?\nA: 10 se 7\nQ: Address kya hai?\nA: [blank]")
    assert d["status"] == "draft" and d["blanks"] == ["Address kya hai?"]
    with pytest.raises(S.CcError, match="khaali"):
        S.submit(T)
    S.edit_script(T, business="Sharma Clinic", faq_add=[{"q": "Address kya hai?", "a": "Station road, Akot"}])
    card = S.submit(T)
    assert card["status"] == "waiting" and len(card["faqs"]) == 2 and card["changes"]
    assert S.approved(T) is None                                     # a card is not an approval
    with pytest.raises(S.CcError):
        S.decide_script(T, card["script_id"], True, "wrong-hash")
    v = S.decide_script(T, card["script_id"], True, card["hash"])
    assert v["status"] == "approved" and S.approved(T)["version"] == 1
    # a change makes a NEW draft; the running script stays the old one until she taps again
    S.edit_script(T, faq_add=[{"q": "Parking hai?", "a": "Haan, bahar"}])
    assert S.approved(T)["version"] == 1 and S.draft(T)["version"] == 2 and S.draft(T)["faqs"] == 3
    c2 = S.submit(T)
    S.edit_script(T, faq_add=[{"q": "Sunday khula hai?", "a": "Nahi"}])         # changed after the card
    with pytest.raises(S.CcError, match="badal"):
        S.decide_script(T, c2["script_id"], True, c2["hash"])
    rej = S.decide_script(T, c2["script_id"], False)
    assert rej["status"] == "rejected" and S.approved(T)["version"] == 1
    # the tools can only send the card
    from app.agent.callcentre_tools import CALLCENTRE_HANDLERS as H
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    out = asyncio.run(H["call_centre"](ctx, action="faq_add", faqs=[{"q": "Emergency number?", "a": "[blank]"}]))
    assert out["status"] == "draft"
    with pytest.raises(ToolError):
        asyncio.run(H["call_centre"](ctx, action="submit"))            # blank answer blocks the card
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(H["call_centre"](staff, action="line", on=True))
    with pytest.raises(ToolError):
        asyncio.run(H["call_centre"](Ctx(T, ctx.conversation_id, actor="customer:wa:1"), action="script", words="x" * 20))
    assert asyncio.run(H["call_centre_dekho"](ctx, what="script"))["running"]["version"] == 1
    assert "Plivo" in json.dumps(asyncio.run(H["call_centre_dekho"](ctx, what="rules")))
    from app.db import Event, session
    with session() as s:
        assert s.query(Event).filter_by(kind="callcentre_script").count() >= 2


# ---------------------------------------------------------------- call routing
def test_incoming_routing(cc, monkeypatch):
    S = cc
    fake_line(S)
    info = {"call": "p1", "from": "+919811111111", "to": ""}
    d = S.incoming(T, info)
    assert d["action"] == "dial" and d["dial"] == "+919876543210"     # no approved script: straight to her
    ready_script(S)
    S.set_line(T, True)
    d1 = S.incoming(T, {"call": "p2", "from": "+919811111112"})
    assert d1["action"] == "stream" and S.ticket_ok(d1["call_id"], d1["ticket"])
    assert not S.ticket_ok(d1["call_id"], "1.abc") and not S.ticket_ok("other", d1["ticket"])
    h = S.incoming(T, {"call": "p3", "from": "+919811111113"})          # max_concurrent 1: hold once
    assert h["action"] == "hold" and h["tries"] == 1
    b = S.incoming(T, {"call": "p3", "from": "+919811111113"}, tries=1)  # still busy -> call-back message
    assert b["action"] == "say" and "busy" in S.call_row(b["call_id"])["outcome"]
    assert any(m["kind"] == "callback" and m["caller"] == "+919811111113" for m in S.messages(T))
    S.save_settings(T, overflow="transfer")
    t = S.incoming(T, {"call": "p4", "from": "+919811111114"}, tries=1)
    assert t["action"] == "dial" and S.call_row(t["call_id"])["outcome"] == "transferred"
    S.release_slot(T, d1["call_id"])
    monkeypatch.setattr(S, "is_open", lambda tenant, at=None: False)
    S.save_settings(T, after_hours="closed")
    c = S.incoming(T, {"call": "p5", "from": "+919811111115"})
    assert c["action"] == "say" and "band" in c["text"]
    S.hung_up(T, "p3")
    assert S.report(T, 1)["calls"] == 5


def test_line_tools_are_customer_safe(cc):
    S = cc
    from app.employee.models import EmployeeProfile
    from app.db import session
    with session() as s:
        s.add(EmployeeProfile(tenant_id=T, business_name="Sharma Clinic", hours=json.dumps(ALLDAY), slot_minutes=30))
    ready_script(S)
    row = S.incoming(T, {"call": "x", "from": "+919822222222"})
    c = S.CallCtx(T, row["call_id"], "+919822222222", S.approved(T))
    assert S.run_line_tool(c, "faq_answer", {"question": "timing kya hai"})["answer"].startswith("Som se Shani")
    miss = S.run_line_tool(c, "faq_answer", {"question": "parking milegi kya"})
    assert miss["not_in_script"] and c.misses == 1
    assert "error" in S.run_line_tool(c, "email_read", {})            # her personal tools never exist on the line
    assert "error" in S.run_line_tool(c, "create_reminder", {"text": "x"})
    slots = S.run_line_tool(c, "free_slots", {})["slots"]
    b = S.run_line_tool(c, "book_appointment", {"when": slots[0], "name": "Ramesh"})
    assert b["booked"] and b["when"] == slots[0]
    from app.employee import inbox
    assert inbox.appointments(T)[0]["phone"] == "919822222222"         # the number from caller ID, not from the model
    tk = S.run_line_tool(c, "register_complaint", {"text": "Dard ki dawai nahi mili"})["ticket"]
    other = S.CallCtx(T, row["call_id"], "+919833333333", S.approved(T))
    assert S.run_line_tool(other, "ticket_status", {"ticket_no": tk})["found"] is False   # someone else's ticket: nothing
    assert S.run_line_tool(c, "ticket_status", {"ticket_no": tk})["tickets"][0]["status"] == "open"
    msg = S.run_line_tool(c, "take_message", {"message": "Mera OTP 445566 hai, refund chahiye", "name": "Ramesh"})
    assert msg["saved"] and "445566" not in S.messages(T)[0]["text"]
    # a script without appointments: the line can't book
    S.edit_script(T, can={"appointments": False})
    card = S.submit(T)
    S.decide_script(T, card["script_id"], True, card["hash"])
    c3 = S.CallCtx(T, row["call_id"], "+919822222222", S.approved(T))
    assert "error" in S.run_line_tool(c3, "book_appointment", {"when": slots[1], "name": "R"})
    assert {x["name"] for x in S.line_specs(S.approved(T))} == {"faq_answer", "take_message", "transfer_human", "end_call",
                                                               "ticket_status", "register_complaint"}
    p = S.persona(T, S.approved(T), __import__("app.voicelang", fromlist=["LangState"]).LangState("hi-IN"), "+919822222222", True)
    assert "AI sahayak" in p and "record" in p and "RESPOND UNMISTAKABLY IN HINDI" in p and "not_in_script" in p
    assert "Clinic ki timing" in p and "called 0" not in p
    assert S.forget_caller(T, "9822222222")["forgot"]


# ---------------------------------------------------------------- signed webhooks
def test_webhooks_are_verified(cc):
    S = cc
    from app.callcentre import providers as P
    ready_script(S)
    fake_line(S)
    S.set_line(T, True)
    tok = S.settings(T)["urls"]["answer"].split("/")[-2]
    cl = app_client()
    path = f"/api/callcentre/hook/fake/{tok}/answer"
    params = {"call": "f1", "from": "9811112222"}
    assert cl.post(path, data=params, headers={"X-Fake-Signature": "nope"}).status_code == 403
    assert cl.post(f"/api/callcentre/hook/fake/{'x' * 24}/answer", data=params).status_code == 404
    sig = P.Fake.sign("s3", "POST", BASE + path, params)
    r = cl.post(path, data=params, headers={"X-Fake-Signature": sig})
    assert r.status_code == 200 and r.json()["action"] == "stream" and "/api/callcentre/ws/fake/" in r.json()["url"]
    # Plivo: XML answer, signature with HER auth token
    S.set_creds(T, "plivo", {"auth_id": "MAXXXX", "auth_token": "plv-token"})
    S.save_settings(T, provider="plivo", number="02240001000")
    S.release_slot(T, r.json()["url"].split("c=")[1].split("&")[0])
    tok = S.settings(T)["urls"]["answer"].split("/")[-2]
    ppath = f"/api/callcentre/hook/plivo/{tok}/answer"
    form = {"CallUUID": "uuid-1", "From": "919811113333", "To": "912240001000", "Direction": "inbound"}
    hdr = {"X-Plivo-Signature-V3-Nonce": "nonce1",
           "X-Plivo-Signature-V3": P.plivo_signature("plv-token", "POST", BASE + ppath, "nonce1", form)}
    x = cl.post(ppath, data=form, headers=hdr)
    assert x.status_code == 200 and "<Stream bidirectional=\"true\"" in x.text and "wss://hoola.test/api/callcentre/ws/plivo/" in x.text
    assert cl.post(ppath, data=form | {"From": "919999999999"}, headers=hdr).status_code == 403   # tampered
    cid = __import__("re").search(r"\?c=(\w+)", x.text).group(1)
    # transfer XML only for a call that asked for one, with a fresh ticket
    from app.callcentre.models import CcCall
    from app.db import session
    with session() as s:
        s.get(CcCall, cid).transfer_to = "+919876543210"
    tpath = f"/api/callcentre/hook/plivo/{tok}/transfer/{cid}"
    tq = f"?t={S.ticket(cid)}"
    th = {"X-Plivo-Signature-V3-Nonce": "n2", "X-Plivo-Signature-V3": P.plivo_signature("plv-token", "POST", BASE + tpath + tq, "n2", {})}
    tr = cl.post(tpath + tq, headers=th)
    assert tr.status_code == 200 and "<Number>+919876543210</Number>" in tr.text and 'callerId="+912240001000"' in tr.text
    bad = "?t=1.x"
    th2 = {"X-Plivo-Signature-V3-Nonce": "n3", "X-Plivo-Signature-V3": P.plivo_signature("plv-token", "POST", BASE + tpath + bad, "n3", {})}
    assert cl.post(tpath + bad, headers=th2).status_code == 403
    # the stream refuses a missing / wrong ticket
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with cl.websocket_connect(f"/api/callcentre/ws/plivo/{tok}?c={cid}&t=1.bad") as ws:
            ws.receive_text()
    # Exotel flow helpers
    S.save_settings(T, provider="exotel")
    etok = S.settings(T)["urls"]["after"].split("/")[-2]
    with session() as s:
        s.get(CcCall, cid).provider_call = "ex-1"
    assert cl.get(f"/api/callcentre/hook/exotel/{etok}/after?CallSid=ex-1").status_code == 200
    assert cl.get(f"/api/callcentre/hook/exotel/{etok}/after?CallSid=none", follow_redirects=False).status_code == 302
    assert cl.get(f"/api/callcentre/hook/exotel/{etok}/connect?CallSid=ex-1").json()["destination"]["numbers"] == ["+919876543210"]
    # her app routes
    assert cl.get("/api/callcentre").json()["settings"]["provider"] == "exotel"
    assert cl.post("/api/callcentre/try", json={"question": "fees kitni"}).json()["found"]
    assert cl.post(f"/api/callcentre/scripts/{S.approved(T)['id']}/decide", json={"yes": True, "hash": "x"}).status_code == 400


# ---------------------------------------------------------------- a whole call: fake phone line + fake Gemini
def _msg(**kw):
    return types.LiveServerMessage(**kw)


def _say(text):
    return [_msg(server_content=types.LiveServerContent(
        model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x10\x00" * 2400, mime_type="audio/pcm;rate=24000"))]),
        output_transcription=types.Transcription(text=text))),
        _msg(server_content=types.LiveServerContent(turn_complete=True))]


class FakeGemini:
    """Plays a call: disclosure -> caller asks timing (faq_answer) -> answer -> caller wants the manager -> the system's
    hand-over note -> transfer_human."""

    def __init__(self, disclose=True):
        self.turns = [_say("Namaste, Sharma Clinic mein swagat hai. Main Asha, Sharma Clinic ki AI sahayak hoon." if disclose
                           else "Namaste, Sharma Clinic, boliye.")]
        self.audio, self.texts, self.responses = 0, [], []
        self.stage = 0

    async def send_realtime_input(self, audio=None, text=None, **_):
        if audio is not None:
            self.audio += 1
            if self.audio == 3 and self.stage == 0:
                self.stage = 1
                self.turns.append([
                    _msg(server_content=types.LiveServerContent(input_transcription=types.Transcription(text="Clinic ki timing kya hai?"))),
                    _msg(tool_call=types.LiveServerToolCall(function_calls=[
                        types.FunctionCall(id="t1", name="faq_answer", args={"question": "timing kya hai"})]))])
            if self.audio == 12 and self.stage == 2:
                self.stage = 3
                self.turns.append([_msg(server_content=types.LiveServerContent(
                    input_transcription=types.Transcription(text="Mujhe manager se baat karni hai")))] + _say("Ji, ek minute."))
        if text is not None:
            self.texts.append(text)
            if "transfer_human reason=asked_human" in text and self.stage == 3:
                self.stage = 4
                self.turns.append([_msg(tool_call=types.LiveServerToolCall(function_calls=[
                    types.FunctionCall(id="t2", name="transfer_human", args={"reason": "asked_human"})]))] + _say("Aapko team se jod rahi hoon."))

    async def send_tool_response(self, function_responses):
        self.responses.extend(function_responses)
        for r in function_responses:
            if r.name == "faq_answer":
                self.stage = 2
                self.turns.append(_say("Hum Som se Shani, subah das se shaam saat tak khule hain."))

    async def send_client_content(self, **_):
        pass

    async def receive(self):
        while not self.turns:
            await asyncio.sleep(0.01)
        for m in self.turns.pop(0):
            yield m


def _pcm8(n=320):
    t = np.arange(n // 2) / 8000
    return (np.sin(2 * math.pi * 300 * t) * 8000).astype("<i2").tobytes()


def _call(S, fake, cl, tok, frm="9811112222", stop_when=lambda: False, dtmf_at=None, max_s=8):
    from app.callcentre import providers as P
    path = f"/api/callcentre/hook/fake/{tok}/answer"
    params = {"call": f"fc-{frm}", "from": frm}
    url = cl.post(path, data=params, headers={"X-Fake-Signature": P.Fake.sign("s3", "POST", BASE + path, params)}).json()["url"]
    got = []
    with cl.websocket_connect(url.replace(BASE.replace("https", "wss"), "")) as ws:
        ws.send_text(json.dumps({"event": "start", "call": params["call"], "stream": "st1"}))
        t0, i = time.time(), 0
        while time.time() - t0 < max_s and not stop_when():
            ws.send_text(json.dumps({"event": "media", "payload": base64.b64encode(_pcm8()).decode()}))
            i += 1
            if dtmf_at and i == dtmf_at:
                ws.send_text(json.dumps({"event": "dtmf", "digit": "0"}))
            time.sleep(0.03)
        ws.send_text(json.dumps({"event": "stop"}))
        with contextlib.suppress(Exception):
            while True:
                got.append(json.loads(ws.receive_text()))
    return got


def _wait_ended(S, frm, t=6):
    from app.callcentre.models import CcCall
    from app.db import session
    t0 = time.time()
    while time.time() - t0 < t:
        with session() as s:
            c = s.query(CcCall).filter_by(provider_call=f"fc-{frm}").first()
            if c and c.status == "ended" and c.summary:
                return S.call(T, c.id)
        time.sleep(0.05)
    raise AssertionError("call did not end")


def test_whole_call_answers_from_script_then_hands_over(cc, monkeypatch):
    S = cc
    from app.callcentre import bridge as B
    from app.callcentre import providers as P
    ready_script(S)
    fake_line(S)
    S.save_settings(T, record=True)
    S.set_line(T, True)
    fake, cfgs = FakeGemini(), []

    @contextlib.asynccontextmanager
    async def connect(cfg):
        cfgs.append(cfg)
        yield fake
    monkeypatch.setattr(B, "connector", connect)
    cl = app_client()
    tok = S.settings(T)["urls"]["answer"].split("/")[-2]
    frames = _call(S, fake, cl, tok, stop_when=lambda: any(a["do"] == "transfer" for a in P.FAKE_ACTIONS))
    v = _wait_ended(S, "9811112222")
    # config: only the line's own tools, the script + disclosure in the prompt, caller-language transcript hint
    cfg = cfgs[0]
    names = {d.name for d in cfg.tools[0].function_declarations}
    assert names == {"faq_answer", "take_message", "transfer_human", "end_call", "free_slots", "book_appointment",
                     "ticket_status", "register_complaint"}
    sysp = cfg.system_instruction.parts[0].text
    assert "AI sahayak" in sysp and "Yeh call record ho rahi hai" in sysp and "Som se Shani" in sysp
    assert cfg.input_audio_transcription.language_codes == ["hi-IN", "en-IN"] and "Sharma Clinic" in cfg.input_audio_transcription.custom_vocabulary
    assert cfg.realtime_input_config.automatic_activity_detection.silence_duration_ms == 800
    # the call itself
    assert fake.audio >= 12 and fake.responses[0].response["answer"].startswith("Som se Shani")
    assert any("connecting them to the team" in x for x in fake.texts)            # the code noticed "manager"
    t = [a for a in P.FAKE_ACTIONS if a["do"] == "transfer"][0]
    assert t["call"] == "fc-9811112222" and f"/transfer/{v['id']}?t=" in t["url"]
    assert any(f.get("event") == "media" for f in frames)                         # his voice reached the phone (8 kHz)
    pcm = base64.b64decode(next(f for f in frames if f.get("event") == "media")["payload"])
    assert len(pcm) == 2400 * 2 // 3                                               # 24 kHz -> 8 kHz
    assert v["outcome"] == "transferred" and v["handover_reason"] == "asked_human" and v["disclosed"] is True
    assert v["intent"] == "wanted_person" and v["script_version"] == 1 and v["lang"] == "hi-IN"
    assert ["caller", "Clinic ki timing kya hai?"] in v["transcript"] and v["caller_masked"] == "98XXXX2222"
    from app.db import Event, session
    with session() as s:
        ev = s.query(Event).filter_by(kind="callcentre_call").all()
    assert ev and ev[-1].payload["outcome"] == "transferred" and "transcript_tail" in ev[-1].payload
    assert S.caller_info(T, "9811112222")["calls"] == 1
    assert not S.LIVE.get(T)                                                      # the AI slot was given back


def test_call_fixes_missing_disclosure_dtmf_and_ai_down(cc, monkeypatch):
    S = cc
    from app.callcentre import bridge as B
    from app.callcentre import providers as P
    ready_script(S)
    fake_line(S)
    S.set_line(T, True)
    fake = FakeGemini(disclose=False)

    @contextlib.asynccontextmanager
    async def connect(cfg):
        yield fake
    monkeypatch.setattr(B, "connector", connect)
    cl = app_client()
    tok = S.settings(T)["urls"]["answer"].split("/")[-2]
    _call(S, fake, cl, tok, frm="9811114444", dtmf_at=6,
          stop_when=lambda: any(a["do"] == "transfer" and "9811114444" in a["call"] for a in P.FAKE_ACTIONS))
    v = _wait_ended(S, "9811114444")
    assert any("you did not tell the caller you are an AI" in x for x in fake.texts)
    assert any(f["kind"] == "disclosure" for f in v["flags"]) and v["handover_reason"] == "dtmf"
    assert v["outcome"] == "transferred"
    # Gemini down: no dead air - the call goes to her (or a call-back message when nobody can take it)
    fake_line(S, handover=False)

    @contextlib.asynccontextmanager
    async def broken(cfg):
        raise RuntimeError("Gemini 503")
        yield None
    monkeypatch.setattr(B, "connector", broken)
    _call(S, fake, cl, tok, frm="9811115555", max_s=1.0)
    v2 = _wait_ended(S, "9811115555")
    assert v2["outcome"] == "failed"
    assert any(m["caller"] == "+919811115555" and "AI line" in m["text"] for m in S.messages(T))
    assert any(a["do"] == "hangup" and "9811115555" in a["call"] for a in P.FAKE_ACTIONS)


def test_tick_callbacks_and_stale_calls(cc):
    S = cc
    from datetime import timedelta
    from app.db import now, session
    from app.callcentre.models import CcCall
    ready_script(S)
    row = S.incoming(T, {"call": "z", "from": "+919844444444"})
    c = S.CallCtx(T, row["call_id"], "+919844444444", S.approved(T))
    soon = (S.local_now(T) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M")
    S.run_line_tool(c, "take_message", {"message": "Kal ke appointment ke liye call karna", "name": "Sunita", "callback_at": soon})
    assert S.messages(T)[0]["kind"] == "callback" and S.messages(T)[0]["callback_at"]
    with session() as s:
        s.add(CcCall(tenant_id=T, provider="fake", status="live", started_at=now() - timedelta(hours=4)))
    out = S.tick()
    assert out == {"callbacks": 1, "stale": 1} and S.tick()["callbacks"] == 0
    rep = S.report(T, 7)
    assert rep["open_messages"] == 2 and "calls" in rep["say"]           # the call-back + "AI line band thi" (line is off)
    cb = next(m for m in S.messages(T) if m["kind"] == "callback")
    S.message_done(T, cb["id"], "baat ho gayi")
    assert [m["kind"] for m in S.messages(T)] == ["missed"]


def test_exotel_static_stream_with_basic_auth(cc, monkeypatch):
    S = cc
    from app.callcentre import bridge as B
    ready_script(S)
    S.save_settings(T, provider="exotel", number="02240001000", hours=ALLDAY, handover=[{"name": "M", "phone": "9876543210"}])
    S.set_line(T, True)
    fake = FakeGemini()

    @contextlib.asynccontextmanager
    async def connect(cfg):
        yield fake
    monkeypatch.setattr(B, "connector", connect)
    cl = app_client()
    tok = S.settings(T)["urls"]["after"].split("/")[-2]
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):                       # no Basic Auth, no ticket: refused
        with cl.websocket_connect(f"/api/callcentre/ws/exotel/{tok}") as ws:
            ws.receive_text()
    user, pw = S.ws_auth(T)
    auth = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    frames = []
    with cl.websocket_connect(f"/api/callcentre/ws/exotel/{tok}", headers={"Authorization": auth}) as ws:
        ws.send_text(json.dumps({"event": "start", "stream_sid": "es1", "start": {
            "stream_sid": "es1", "call_sid": "ex-77", "from": "09811116666", "to": "02240001000",
            "media_format": {"encoding": "raw/slin", "sample_rate": 8000, "bit_rate": "128kbps"}}}))
        t0 = time.time()
        while time.time() - t0 < 1.5:
            ws.send_text(json.dumps({"event": "media", "stream_sid": "es1", "media": {"payload": base64.b64encode(_pcm8()).decode()}}))
            time.sleep(0.03)
        ws.send_text(json.dumps({"event": "stop", "stream_sid": "es1", "stop": {"reason": "callended"}}))
        with contextlib.suppress(Exception):
            while True:
                frames.append(json.loads(ws.receive_text()))
    v = None
    from app.callcentre.models import CcCall
    from app.db import session
    t0 = time.time()
    while time.time() - t0 < 5:
        with session() as s:
            c = s.query(CcCall).filter_by(provider_call="ex-77").first()
            if c and c.status == "ended" and c.summary:
                v = S.call(T, c.id)
                break
        time.sleep(0.05)
    assert v and v["caller"] == "+919811116666" and v["disclosed"]
    media = [f for f in frames if f.get("event") == "media"]
    assert media and all(len(base64.b64decode(f["media"]["payload"])) % 320 == 0 for f in media)
    assert all(f["stream_sid"] == "es1" for f in media)
