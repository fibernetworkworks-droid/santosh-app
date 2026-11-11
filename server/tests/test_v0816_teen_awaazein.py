"""v0.816 TEEN AWAAZEIN: three more call engines she can pick on Call voice - Grok Voice 3.0, GPT-Live-1, Phonic 1.
Gemini stays the default and untouched; each engine runs only with its key, under its budget and her minutes.
Each vendor is played by a scripted fake that speaks its documented wire."""
import asyncio
import base64
import json

import pytest
from fastapi.testclient import TestClient

from app import voice_more, voiceengine
from tests.test_v0264_openai_voice import FakeOA, _drive


def _b64(n=100):
    return base64.b64encode(b"\x01\x00" * n).decode()


@pytest.fixture()
def keys(env, monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("PHONIC_API_KEY", "ph-test")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "voice_engine")
    yield
    get_settings.cache_clear()


# ------------------------------------------------------------------ choosing
def test_pick_each_engine_and_its_plain_fallbacks(env, monkeypatch, tmp_path):
    from app.config import get_settings
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "ve")
    for k in ("XAI_API_KEY", "PHONIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(k, "")
    get_settings.cache_clear()
    assert voiceengine.pick("default") == ("gemini", "")              # nobody picked anything: Gemini
    for eng, env_name in (("grok", "XAI_API_KEY"), ("gptlive", "OPENAI_API_KEY"), ("phonic", "PHONIC_API_KEY")):
        voiceengine.choose("default", eng)
        got, why = voiceengine.pick("default")
        assert got == "gemini" and env_name in why                    # no key = Gemini, and it says which key
        monkeypatch.setenv(env_name, "k")
        get_settings.cache_clear()
        assert voiceengine.pick("default") == (eng, "")
        voiceengine.add_usage("default", usd=1000, engine=eng)        # the month's budget is gone
        got, why = voiceengine.pick("default")
        assert got == "gemini" and "budget" in why
    voiceengine.choose("someone-else", "phonic")                       # "*" = open to every user
    monkeypatch.setenv("VOICE_PHONIC_ENABLED", "false")
    get_settings.cache_clear()
    assert voiceengine.pick("someone-else")[0] == "gemini"
    with pytest.raises(ValueError):
        voiceengine.choose("default", "elevenlabs")
    get_settings.cache_clear()


def test_minutes_cap_and_view(keys):
    from app.config import get_settings
    voiceengine.choose("default", "grok")
    voiceengine.add_usage("default", seconds=(get_settings().voice_grok_user_min + 1) * 60, engine="grok")
    got, why = voiceengine.pick("default")
    assert got == "gemini" and "minutes" in why
    v = voiceengine.view("default")
    eng = {e["engine"]: e for e in v["engines"]}
    assert set(eng) == {"grok", "gptlive", "phonic"}
    assert eng["grok"]["my_minutes"] > get_settings().voice_grok_user_min and eng["phonic"]["ready"] is True
    assert eng["phonic"]["inr_per_min"] > eng["gptlive"]["inr_per_min"] > 0     # $0.07 vs $0.05 a minute
    assert v["month_usd"] == 0                                          # OpenAI realtime's own box untouched


# ------------------------------------------------------------------ Grok
def test_grok_call_end_to_end(keys, monkeypatch):
    """xAI speaks the OpenAI Realtime events: the same fake drives it; only the session body + cost differ."""
    from app import main
    fake = FakeOA()

    async def connect():
        fake.closed = False
        return fake
    monkeypatch.setattr(voice_more, "grok_connect", connect)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        assert c.put("/api/voice/engine", json={"engine": "grok"}).json()["will_use"] == "grok"
        got_audio, events = _drive(c, conv)
    assert events[0]["type"] == "ready" and events[0]["engine"] == "grok"
    assert {"type": "user_text", "text": "Kal subah saat baje ka alarm laga do"} in events
    assert len(got_audio) == 3
    upd = next(e for e in fake.sent if e["type"] == "session.update")["session"]
    assert upd["voice"] == "rex" and upd["turn_detection"] == {"type": "server_vad"}
    assert upd["audio"]["input"]["format"] == {"type": "audio/pcm", "rate": 24000}
    assert upd["reasoning"] == {"effort": "none"} and "model" not in upd and "type" not in upd
    assert any(t["name"] == "santosh_kaam" for t in upd["tools"])
    out = next(e for e in fake.sent if e.get("item", {}).get("type") == "function_call_output")
    assert out["item"]["call_id"] == "call_1"
    import time
    for _ in range(50):                                                 # counted at the call's end, in Grok's own box
        b = voiceengine._bucket(voiceengine._usage(), "grok")
        if (b.get("seconds") or {}).get("default"):
            break
        time.sleep(0.1)
    assert b["seconds"]["default"] > 0 and b["usd"] > 0 and voiceengine._usage().get("usd") is None


# ------------------------------------------------------------------ Phonic
class FakePhonic:
    def __init__(self):
        self.sent, self.q, self.closed, self.n = [], asyncio.Queue(), False, 0

    def _say(self, text):
        for e in ({"type": "audio_chunk", "audio": _b64(), "text": text}, {"type": "assistant_finished_speaking"}):
            self.q.put_nowait(e)

    async def send(self, ev):
        self.sent.append(ev)
        t = ev["type"]
        if t == "config":
            self.q.put_nowait({"type": "ready_to_start_conversation"})
            self.q.put_nowait({"type": "conversation_created", "conversation_id": "conv_ph_1"})
        elif t == "generate_reply":                    # the greeting cue
            self._say("Haan bolo, kya haal hai?")
            for e in ({"type": "user_started_speaking"}, {"type": "user_finished_speaking"},
                      {"type": "input_text", "language": "hi", "text": "Kal subah saat baje ka alarm laga do"},
                      {"type": "tool_call", "tool_call_id": "tc_1", "tool_name": "set_phone_alarm",
                       "parameters": {"time": "07:00", "label": "Uthna hai"}}):
                self.q.put_nowait(e)
        elif t == "tool_call_output":
            self._say("Ho gaya, saat baje ka alarm laga diya.")

    async def events(self):
        while not self.closed:
            try:
                yield await asyncio.wait_for(self.q.get(), 0.05)
            except asyncio.TimeoutError:
                continue

    async def close(self):
        self.closed = True


def test_phonic_call_end_to_end(keys, monkeypatch):
    from app import main
    fake = FakePhonic()

    async def connect():
        fake.closed = False
        return fake
    monkeypatch.setattr(voice_more, "phonic_connect", connect)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        assert c.put("/api/voice/engine", json={"engine": "phonic"}).json()["will_use"] == "phonic"
        got_audio, events = _drive(c, conv, want_done=2)
    assert events[0]["engine"] == "phonic"
    assert {"type": "user_text", "text": "Kal subah saat baje ka alarm laga do"} in events
    assert len(got_audio) == 2
    cfg = next(e for e in fake.sent if e["type"] == "config")
    assert cfg["model"] == "phonic-1" and cfg["voice_id"] == "sandeep"
    assert cfg["input_format"] == "pcm_16000" and cfg["output_format"] == "pcm_24000"
    assert cfg["default_language"] in voice_more.PHONIC_LANGS and cfg["no_input_end_conversation_sec"] == 3600
    tool = cfg["tools"][0]
    assert tool["type"] == "custom_websocket" and tool["tool_schema"]["function"]["name"] == "santosh_kaam"
    assert tool["tool_schema"]["function"]["strict"] is True
    chunks = [e for e in fake.sent if e["type"] == "audio_chunk"]
    assert chunks and all(len(base64.b64decode(e["audio"])) <= voice_more.PHONIC_CHUNK for e in chunks)
    assert base64.b64decode(chunks[0]["audio"]) == (b"\x00\x01" * 320)[:voice_more.PHONIC_CHUNK]   # 16 kHz, as she spoke
    out = next(e for e in fake.sent if e["type"] == "tool_call_output")
    assert out["tool_call_id"] == "tc_1" and json.loads(out["output"])["result"]["sent_to_phone"] is True


# ------------------------------------------------------------------ GPT-Live-1
class FakeLive:
    def __init__(self):
        self.sent, self.q, self.closed = [], asyncio.Queue(), False

    def _say(self, text):
        self.q.put_nowait({"type": "session.output_audio.delta", "delta": _b64()})
        self.q.put_nowait({"type": "session.output_transcript.delta", "delta": text, "start_ms": 0, "end_ms": 400})

    async def send(self, ev):
        self.sent.append(ev)
        t = ev["type"]
        if t == "session.start":
            self.q.put_nowait({"type": "session.started", "session": {"id": "ls_1"}})
        elif t == "session.commentary.append" and ev["delegation_id"] is None:    # the greeting cue
            self._say("Haan bolo, kya haal hai?")
            await asyncio.sleep(1.3)
            self.q.put_nowait({"type": "session.input_transcript.delta", "delta": "Kal ka alarm laga do"})
            self.q.put_nowait({"type": "session.delegation.created",
                               "delegation": {"id": "dl_1", "type": "delegation", "target": "client"}, "offset_ms": 900})
        elif t == "session.commentary.append":
            self._say(ev["content"])
            self.q.put_nowait({"type": "session.usage.updated", "usage": {"seconds": 42.0}})

    async def events(self):
        while not self.closed:
            try:
                yield await asyncio.wait_for(self.q.get(), 0.05)
            except asyncio.TimeoutError:
                continue

    async def close(self):
        self.closed = True


def test_gptlive_call_end_to_end_with_hoola_brain(keys, monkeypatch):
    """GPT-Live delegates; Hoola's brain (santosh_kaam) answers; the answer goes back as that delegation's commentary."""
    from app import main
    fake = FakeLive()
    asks = []

    async def connect():
        fake.closed = False
        return fake

    async def brain(self, name, args):
        asks.append((name, args))
        return {"result": "Alarm saat baje ka laga diya."}
    monkeypatch.setattr(voice_more, "gptlive_connect", connect)
    monkeypatch.setattr(voice_more.GptLiveCall, "_execute", brain)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        assert c.put("/api/voice/engine", json={"engine": "gptlive"}).json()["will_use"] == "gptlive"
        got_audio, events = _drive(c, conv, want_done=2)
    assert events[0]["engine"] == "gptlive"
    start = next(e for e in fake.sent if e["type"] == "session.start")["session"]
    assert start["model"] == "gpt-live-1" and start["delegation"] == {"type": "client"}
    assert start["audio"]["format"] == {"type": "audio/pcm", "rate": 24000} and start["audio"]["output"]["voice"] == "stone"
    assert "<|SpawnThinking|>" in start["instructions"]
    assert asks and asks[0][0] == "santosh_kaam" and "alarm" in asks[0][1]["request"]
    ans = [e for e in fake.sent if e["type"] == "session.commentary.append" and e["delegation_id"] == "dl_1"]
    assert ans and ans[0]["content"] == "Alarm saat baje ka laga diya."
    first_audio = next(i for i, e in enumerate(fake.sent) if e["type"] == "session.input_audio.append")
    assert fake.sent.index(next(e for e in fake.sent if e["type"] == "session.start")) < first_audio
    assert len(got_audio) == 2


def test_gptlive_cost_uses_its_own_seconds():
    c = voice_more.GptLiveCall.__new__(voice_more.GptLiveCall)
    c.stats, c.tenant, c._billed_s = {}, "default", 120.0
    seen = {}
    orig = voiceengine.add_usage
    try:
        voiceengine.add_usage = lambda t, usd=0.0, seconds=0.0, engine="openai": seen.update(usd=usd, s=seconds, e=engine)
        c._record_usage()
    finally:
        voiceengine.add_usage = orig
    assert seen["e"] == "gptlive" and seen["s"] == 120.0 and abs(seen["usd"] - 0.10) < 1e-9   # 2 min x $0.05


def test_main_routes_the_three_and_gemini_stays_default():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
    assert 'if engine in ("grok", "gptlive", "phonic"):' in src and "CLASSES[engine](ws, conv, voice, lang, tenant)" in src
    assert "await v.serve(v.Call(ws, conv, voice, lang, tenant))" in src       # the Gemini call, unchanged
    assert set(voice_more.CLASSES) == set(voiceengine.MORE)
