"""v0.264.0 OPENAI VOICE (Phase 1 of "two engines, she chooses"): the real-voice engine on OpenAI's Realtime API.
Gemini stays the default and untouched; OpenAI runs only when she picked it, a key is set and the budget allows."""
import asyncio
import base64
import json
import math
from array import array
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import voice, voice_openai, voiceengine
from tests.test_voice import FakeSession, _connector, _gemini_env, make_turns, read_events, wait_until

ROOT = Path(__file__).resolve().parents[2]
USAGE = {"total_tokens": 900, "input_tokens": 600, "output_tokens": 300,
         "input_token_details": {"text_tokens": 400, "audio_tokens": 200, "cached_tokens": 300,
                                 "cached_tokens_details": {"text_tokens": 300, "audio_tokens": 0}},
         "output_token_details": {"text_tokens": 60, "audio_tokens": 240}}


def _b64(n=100, x=b"\x01\x00"):
    return base64.b64encode(x * n).decode()


class FakeOA:
    """Plays OpenAI's side: greeting on the first response.create, then her alarm ask with a tool call, then the
    confirmation after the tool result."""

    def __init__(self):
        self.sent = []
        self.q: asyncio.Queue = asyncio.Queue()
        self.n = 0
        self.closed = False

    def _resp(self, rid, say, audio=True, call=None):
        evs = [{"type": "response.created", "response": {"id": rid}}]
        if audio:
            evs.append({"type": "response.output_audio.delta", "item_id": f"it_{rid}", "delta": _b64()})
        if say:
            evs.append({"type": "response.output_audio_transcript.delta", "item_id": f"it_{rid}", "delta": say})
        if call:
            evs.append({"type": "response.function_call_arguments.done", "call_id": call[0], "name": call[1],
                        "arguments": json.dumps(call[2])})
        evs.append({"type": "response.done", "response": {"id": rid, "status": "completed", "usage": USAGE}})
        return evs

    async def send(self, ev):
        self.sent.append(ev)
        if ev["type"] != "response.create":
            return
        self.n += 1
        if self.n == 1:
            evs = self._resp("r1", "Haan bolo, kya haal hai?")
            evs += [{"type": "input_audio_buffer.speech_started", "item_id": "u1"},
                    {"type": "conversation.item.input_audio_transcription.delta", "item_id": "u1", "delta": "Kal subah saat baje "},
                    {"type": "conversation.item.input_audio_transcription.delta", "item_id": "u1", "delta": "ka alarm laga do"},
                    {"type": "conversation.item.input_audio_transcription.completed", "item_id": "u1",
                     "transcript": "Kal subah saat baje ka alarm laga do"}]
            evs += self._resp("r2", "Haan, ek second.",
                              call=("call_1", "set_phone_alarm", {"time": "07:00", "label": "Uthna hai"}))
        else:
            evs = self._resp(f"r{self.n + 1}", "Ho gaya, saat baje ka alarm laga diya.")
        for e in evs:
            self.q.put_nowait(e)

    async def events(self):
        while not self.closed:
            try:
                ev = await asyncio.wait_for(self.q.get(), 0.05)
            except asyncio.TimeoutError:
                continue
            yield ev

    async def close(self):
        self.closed = True


@pytest.fixture()
def oa(env, monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "voice_engine")
    fake = FakeOA()

    async def connect():
        fake.closed = False
        return fake
    monkeypatch.setattr(voice_openai, "connect", connect)
    return fake


def _drive(c, conv, want_done=3):
    got_audio, events = [], []
    with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice=Achird&lang=hi-IN") as ws:
        ws.send_bytes(b"\x00\x01" * 320)
        while True:
            m = ws.receive()
            if m.get("bytes"):
                got_audio.append(m["bytes"])
            elif m.get("text"):
                ev = json.loads(m["text"])
                events.append(ev)
                if ev["type"] == "turn_done" and sum(1 for e in events if e["type"] == "turn_done") == want_done:
                    break
        ws.send_text(json.dumps({"type": "end"}))
    return got_audio, events


def test_openai_call_end_to_end(oa):
    from app import main
    from app.config import get_settings
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        assert c.put("/api/voice/engine", json={"engine": "openai"}).json()["will_use"] == "openai"
        got_audio, events = _drive(c, conv)
    kinds = [e["type"] for e in events]
    assert kinds[0] == "ready" and events[0]["engine"] == "openai"
    assert {"type": "user_text", "text": "Kal subah saat baje ka alarm laga do"} in events
    assert {"type": "tool", "label": "Phone par alarm laga raha hoon", "state": "done"} in events
    assert len(got_audio) == 3                                       # greeting, "ek second", the confirmation
    sent = oa.sent
    upd = next(e for e in sent if e["type"] == "session.update")["session"]
    assert upd["model"] == "gpt-realtime-2.1-mini" and upd["type"] == "realtime"
    assert upd["audio"]["input"]["format"] == {"type": "audio/pcm", "rate": 24000}
    assert upd["audio"]["output"]["voice"] == get_settings().voice_openai_voice_m      # Achird = male avatar
    assert upd["audio"]["input"]["turn_detection"]["type"] == "server_vad"
    assert "AWAAZ MEIN JAAN" in upd["instructions"] and "laughs" in upd["instructions"]
    names = {t["name"] for t in upd["tools"]}
    assert {"set_phone_alarm", "santosh_kaam"} <= names and all(t["type"] == "function" for t in upd["tools"])
    # her 16 kHz mic reached OpenAI as 24 kHz (x1.5)
    app_ = [e for e in sent if e["type"] == "input_audio_buffer.append"]
    assert app_ and len(base64.b64decode(app_[0]["audio"])) == 320 * 2 * 3 // 2
    # greeting went as a system note + response.create; the tool answer as function_call_output
    assert any(e["type"] == "conversation.item.create" and e["item"]["role"] == "system"
               and "call just connected" in e["item"]["content"][0]["text"] for e in sent if e.get("item", {}).get("role"))
    out = next(e for e in sent if e.get("item", {}).get("type") == "function_call_output")
    assert out["item"]["call_id"] == "call_1" and json.loads(out["item"]["output"])["result"]["sent_to_phone"] is True
    # exact cost from response.done usage, counted for the month
    v = voiceengine.view("default")
    assert v["month_usd"] > 0 and v["my_minutes"] >= 0


def test_gemini_untouched_when_she_did_not_pick_openai(env, monkeypatch, tmp_path):
    """Default = Gemini: the exact old call (fake Gemini session) - OpenAI is never contacted."""
    from app import main
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    _gemini_env(monkeypatch)
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "ve")

    async def boom():
        raise AssertionError("OpenAI must not be contacted on a Gemini call")
    monkeypatch.setattr(voice_openai, "connect", boom)
    fake = FakeSession(make_turns())
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        assert c.get("/api/voice/engine").json()["will_use"] == "gemini"
        got_audio, events = _drive(c, conv, want_done=2)
    assert events[0]["type"] == "ready" and "engine" not in events[0]
    assert fake.audio_in and fake.audio_in[0] == b"\x00\x01" * 320     # 16 kHz straight to Gemini, as before


def test_pick_falls_back_to_gemini(env, monkeypatch, tmp_path):
    from app.config import get_settings
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "ve")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    voiceengine.choose("default", "openai")
    eng, why = voiceengine.pick("default")
    assert eng == "gemini" and "key" in why                          # no key -> Gemini, with the reason
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    assert voiceengine.pick("default") == ("openai", "")
    voiceengine.add_usage("default", usd=get_settings().voice_openai_month_usd + 1)
    eng, why = voiceengine.pick("default")
    assert eng == "gemini" and "budget" in why                       # month's budget spent
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "ve2")
    voiceengine.choose("default", "openai")
    voiceengine.add_usage("default", seconds=(get_settings().voice_openai_user_min + 1) * 60)
    assert "minute" in voiceengine.pick("default")[1]                # her minutes spent
    with pytest.raises(PermissionError):
        voiceengine.choose("someone-else", "openai")                 # trial: only the owner
    with pytest.raises(ValueError):
        voiceengine.choose("default", "elevenlabs")


def test_engine_api_refuses_others_and_bad_names(oa):
    from app import main
    with TestClient(main.app) as c:
        assert c.put("/api/voice/engine", json={"engine": "grok"}).status_code == 400
        assert c.put("/api/voice/engine", json={"engine": "gemini"}).json()["will_use"] == "gemini"


def test_resampler_is_even_and_seamless():
    f = lambda t: 10000 * math.sin(2 * math.pi * 440 * t / 16000)
    a = array("h", [int(f(i)) for i in range(1600)])
    o1, st = voice_openai.up16to24(a[:801].tobytes())                 # an odd chunk: the seam must not drift
    o2, st = voice_openai.up16to24(a[801:].tobytes(), st)
    b = array("h")
    b.frombytes(o1 + o2)
    assert len(b) == 2400
    assert max(abs(b[k] - f(k * 2 / 3 - 2 / 3)) for k in range(3, len(b))) < 80


def test_interruption_tells_the_phone_and_truncates_what_she_heard():
    class C(voice_openai.OpenAICall):
        def __init__(self):
            self.stats = {"interruptions": 0, "false_stops": 0}
            self._turn_audio, self._play_until, self.hold = True, 0.0, ""
            self._item, self._item_ms = "it_9", 2000.0
            self.user_buf, self.reply_buf = "", "Kal ka plan yeh hai ki"
            self.sent_phone = []

        async def send_json(self, obj):
            self.sent_phone.append(obj)

        def _watch_false_stop(self, cut):
            pass

        async def finish_turn(self, interrupted=False):
            self.finished = interrupted

    class S:
        def __init__(self):
            self.sent = []

        async def send(self, ev):
            self.sent.append(ev)

    import time
    c, s = C(), S()
    c._play_until = time.monotonic() + 0.5                           # half a second still unplayed on her phone
    asyncio.run(c._she_cut_in(s))
    assert {"type": "interrupted"} in c.sent_phone and c.stats["interruptions"] == 1 and c.finished is True
    tr = s.sent[0]
    assert tr["type"] == "conversation.item.truncate" and tr["item_id"] == "it_9" and 1400 <= tr["audio_end_ms"] <= 1550


def test_no_gemini_voice_clips_on_an_openai_call():
    c = voice_openai.OpenAICall.__new__(voice_openai.OpenAICall)
    assert asyncio.run(c._ack_watch(0.0)) is None and asyncio.run(c._prog_watch(0.0)) is None
    assert c._arm_backchannel() is None
    assert voice_openai.OpenAICall._ack_watch is not voice.Call._ack_watch


def test_prices_and_engine_label():
    from app import usage, callquality
    p, known = usage.price_of("gpt-realtime-2.1-mini")
    assert known and p["audio_in"] == 10.0 and p["audio_out"] == 20.0
    assert callquality.compact({"call_id": "x", "engine": "openai"})["engine"] == "openai"
    assert callquality.compact({"call_id": "y"})["engine"] == "gemini"


def test_gemini_file_has_only_the_routing_seam():
    main_src = (ROOT / "server/app/main.py").read_text()
    assert "engine, why = voiceengine.pick(tenant)" in main_src and "OpenAICall(ws, conv, voice, lang, tenant)" in main_src
    vsrc = (ROOT / "server/app/voice.py").read_text()
    assert "openai" not in vsrc.lower().replace("openai-compatible", "")   # the Gemini engine knows nothing of OpenAI


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.264.0"
    assert "0.264.0+304" in (ROOT / "pubspec.yaml").read_text()
