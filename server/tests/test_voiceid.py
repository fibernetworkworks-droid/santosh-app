"""Awaaz Pehchaan: Hoola knows who is talking (owner, Maa...) and the voice lock keeps the owner's work for the owner.
The real models are swapped for a stand-in that fingerprints a voice by its pitch, so tests run anywhere."""
import io
import json
import math
import time
import wave
from array import array

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app import voice
from app.voiceid import engine, permissions
from tests.test_voice import FakeSession, _connector, _gemini_env, read_events, wait_until

np = pytest.importorskip("numpy")
OWNER_HZ, MAA_HZ, STRANGER_HZ = 140, 260, 420


def fake_embed(pcm: bytes) -> dict:
    """Fingerprint = where the pitch is (a bump on a 64-bin scale), the same shape as a real model's output."""
    x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32)
    f = np.abs(np.fft.rfft(x[:16000 * 2] if len(x) > 32000 else x))
    hz = float(np.argmax(f[1:]) + 1) * 16000 / (2 * (len(f) - 1))
    v = np.exp(-((np.arange(64) - hz / 10) ** 2) / 8)
    return {"campplus": (v / np.linalg.norm(v)).tolist(), "titanet": (v / np.linalg.norm(v)).tolist()}


def speech(hz: float, seconds: float, rate: int = 16000, level: float = 0.3) -> bytes:
    """A voice at this pitch with the rhythm of speech (syllables and short gaps), 16 kHz PCM16."""
    n = int(seconds * rate)
    t = np.arange(n) / rate
    env = np.maximum(0, np.sin(2 * np.pi * 3 * t)) ** 2
    return (level * env * np.sin(2 * np.pi * hz * t) * 32767).astype("<i2").tobytes()


def steady(hz: float, seconds: float) -> bytes:
    t = np.arange(int(seconds * 16000)) / 16000
    return (0.3 * np.sin(2 * np.pi * hz * t) * 32767).astype("<i2").tobytes()


def wav(pcm: bytes, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


@pytest.fixture()
def vid(env, monkeypatch):
    _gemini_env(monkeypatch, SECRET_KEY="s3cret-for-tests")
    from app.voiceid import service
    monkeypatch.setattr(engine, "available", lambda: True)
    monkeypatch.setattr(engine, "embed", fake_embed)
    heard = {"digits": None, "permission": True, "single": True, "live": True}

    def fake_listen(data, script):
        code = heard["digits"]
        if code is None:
            words = script.split("Mera code hai:")[1].split(".")[0]
            back = {v: k for k, v in service.DIGITS.items()}
            code = "".join(back[w.strip()] for w in words.split(","))
        return {"transcript": "Main ... hoon", "code_digits": code, "gave_permission": heard["permission"],
                "single_speaker": heard["single"], "live_voice": heard["live"]}

    monkeypatch.setattr(service, "_listen", fake_listen)
    return service, heard


def enrol(c, name, relation, hz, **kw):
    s = c.post("/api/voiceid/enrol", json={"name": name, "relation": relation, **kw}).json()
    return s, c.post(f"/api/voiceid/enrol/{s['enrol_id']}", files={"file": ("me.wav", wav(speech(hz, 20)), "audio/wav")})


def test_enrol_needs_the_persons_own_consent(vid):
    from app import main
    service, heard = vid
    with TestClient(main.app) as c:
        o = c.get("/api/voiceid").json()
        assert o["available"] and o["mode"] == "on" and not o["owner_enrolled"]
        s = c.post("/api/voiceid/enrol", json={"name": "Asha", "relation": "maa"}).json()
        assert "Main Asha hoon" in s["script"] and "ijaazat deti hoon" in s["script"]    # her own words, her gender
        heard["digits"] = "0000"
        r = c.post(f"/api/voiceid/enrol/{s['enrol_id']}", files={"file": ("a.wav", wav(speech(MAA_HZ, 20)), "audio/wav")})
        assert r.status_code == 400 and "code" in r.json()["detail"]
        heard["digits"] = None
        heard["live"] = False
        assert enrol(c, "Asha", "maa", MAA_HZ)[1].status_code == 400
        heard["live"] = True
        short = c.post("/api/voiceid/enrol", json={"name": "Asha", "relation": "maa"}).json()
        r = c.post(f"/api/voiceid/enrol/{short['enrol_id']}", files={"file": ("a.wav", wav(speech(MAA_HZ, 4)), "audio/wav")})
        assert r.status_code == 400 and "kam aayi" in r.json()["detail"]
        s, r = enrol(c, "Asha", "maa", MAA_HZ)
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["relation"] == "maa" and m["level"] == "family" and m["gender"] == "f" and not m["owner"]
        # each script works once
        again = c.post(f"/api/voiceid/enrol/{s['enrol_id']}", files={"file": ("a.wav", wav(speech(MAA_HZ, 20)), "audio/wav")})
        assert again.status_code == 400
        o, r = enrol(c, "Meghana", "self", OWNER_HZ, gender="f")
        assert r.json()["owner"] and r.json()["level"] == "owner"
        # the same voice cannot be enrolled as somebody else
        dup = enrol(c, "Priya", "behen", MAA_HZ)[1]
        assert dup.status_code == 400 and "Asha" in dup.json()["detail"]
        assert c.get("/api/voiceid").json()["owner_enrolled"]
    # only an encrypted fingerprint is stored, no audio, no plain numbers
    from app.db import session
    from app.voiceid.models import VoiceMember
    with session() as s:
        for row in s.query(VoiceMember):
            assert row.prints.startswith("gAAAA") and "[" not in row.prints
            assert row.consent["code"]


def test_tells_people_apart(vid):
    from app import main
    service, _ = vid
    with TestClient(main.app) as c:
        enrol(c, "Meghana", "self", OWNER_HZ, gender="f")
        enrol(c, "Asha", "maa", MAA_HZ)
    people = service.call_people("default")
    assert service.identify(people, speech(MAA_HZ, 2))["member"]["name"] == "Asha"
    assert service.identify(people, speech(OWNER_HZ, 2))["member"]["owner"] is True
    unknown = service.identify(people, speech(STRANGER_HZ, 2))
    assert unknown["member"] is None and not unknown["sure"]


def test_permissions():
    assert permissions.allowed("owner", "email_delete") and permissions.allowed(None, "pc_do")
    assert permissions.allowed("family", "set_phone_alarm") and permissions.allowed("family", "tv_remote")
    for t in ("email_read", "santosh_kaam", "pc_do", "hoola_send", "remember", "drive_share", "email_draft"):
        assert not permissions.allowed("family", t)
    assert permissions.allowed("trusted", "calendar_agenda") and permissions.allowed("trusted", "email_read")
    for t in ("santosh_kaam", "email_draft", "email_delete", "pc_do", "hoola_send", "forget", "unknown_new_tool"):
        assert not permissions.allowed("trusted", t)


def _chunks(pcm: bytes, n: int = 1280):
    return [pcm[i:i + n] for i in range(0, len(pcm), n)]


def test_call_knows_who_is_talking_and_locks_the_owners_work(vid, monkeypatch):
    # these notes travel as client_content (older Live models); Gemini 3.x queueing: tests/test_v150_voice_heal.py
    monkeypatch.setenv("VOICE_QUIET_NOTES", "client_content")
    from app.config import get_settings as _gs
    _gs.cache_clear()
    from app import main
    ran = []

    async def tool(name, args, ctx):
        ran.append(name)
        return {"ok": True}

    monkeypatch.setattr(voice, "dispatch", tool)
    voice.STATS.clear()
    fake = FakeSession([])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        enrol(c, "Meghana", "self", OWNER_HZ, gender="f")
        enrol(c, "Asha", "maa", MAA_HZ)
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            for ch in _chunks(steady(MAA_HZ, 2.0)):     # Maa talks
                ws.send_bytes(ch)
            ev = read_events(ws, lambda e: e["type"] == "speaker")[-1]
            assert ev == {"type": "speaker", "name": "Asha", "relation": "Maa", "owner": False, "level": "family"}
            # Gemini is told quietly (context, no reply of its own)
            assert wait_until(lambda: fake.client_content)
            note = fake.client_content[-1].parts[0].text
            assert "Asha" in note and "Meghana" in note and "private" in note
            # she asks for the owner's mail: refused by the server, the tool never runs
            fake.turns.append([types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
                types.FunctionCall(id="m1", name="email_check", args={})]))])
            assert wait_until(lambda: any(r.id == "m1" for r in fake.tool_responses))
            r = next(r for r in fake.tool_responses if r.id == "m1")
            assert "Meghana" in r.response["error"] and "email_check" not in ran
            # but she can set an alarm
            fake.turns.append([types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
                types.FunctionCall(id="a1", name="set_phone_alarm", args={"time": "06:00"})]))])
            assert wait_until(lambda: "set_phone_alarm" in ran)
            # the owner takes the phone (after a pause): recognised, and her mail works
            time.sleep(1.3)
            for ch in _chunks(steady(OWNER_HZ, 2.0)):
                ws.send_bytes(ch)
            ev = read_events(ws, lambda e: e["type"] == "speaker")[-1]
            assert ev["owner"] is True and ev["name"] == "Meghana"
            fake.turns.append([types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
                types.FunctionCall(id="m2", name="email_check", args={})]))])
            assert wait_until(lambda: "email_check" in ran)
            ws.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: voice.STATS)
    st = voice.STATS[-1]
    assert st["speaker_changes"] == 2 and st["blocked_tools"] == 1 and st["speaker_sure"] >= 2


def test_strict_mode_unknown_voice_gets_only_everyday_help(vid, monkeypatch):
    from app import main
    ran = []

    async def tool(name, args, ctx):
        ran.append(name)
        return {"ok": True}

    monkeypatch.setattr(voice, "dispatch", tool)
    fake = FakeSession([])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        enrol(c, "Meghana", "self", OWNER_HZ, gender="f")
        assert c.put("/api/voiceid/mode", json={"mode": "strict"}).json()["mode"] == "strict"
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            for ch in _chunks(steady(STRANGER_HZ, 1.0)):   # a short request from a voice nobody knows
                ws.send_bytes(ch)
            time.sleep(0.2)
            fake.turns.append([types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
                types.FunctionCall(id="s1", name="email_read", args={"id": "x"}),
                types.FunctionCall(id="s2", name="get_weather", args={"city": "Akola"})]))])
            assert wait_until(lambda: len(fake.tool_responses) >= 2)
            ws.send_text(json.dumps({"type": "end"}))
    blocked = next(r for r in fake.tool_responses if r.id == "s1")
    assert "pakki nahi hui" in blocked.response["error"] and ran == ["get_weather"]


def test_mode_off_and_delete(vid, monkeypatch):
    from app import main
    service, _ = vid
    with TestClient(main.app) as c:
        m = enrol(c, "Asha", "maa", MAA_HZ)[1].json()
        assert c.patch(f"/api/voiceid/members/{m['id']}", json={"level": "trusted"}).json()["level"] == "trusted"
        assert c.patch(f"/api/voiceid/members/{m['id']}", json={"level": "owner"}).status_code == 400
        c.put("/api/voiceid/mode", json={"mode": "off"})
        assert service.call_people("default") is None
        c.put("/api/voiceid/mode", json={"mode": "on"})
        assert service.call_people("default")
        assert c.delete(f"/api/voiceid/members/{m['id']}").json()["deleted"]
        assert service.call_people("default") is None
        assert c.delete(f"/api/voiceid/members/{m['id']}").status_code == 404
        assert c.put("/api/voiceid/mode", json={"mode": "maybe"}).status_code == 400


def test_engine_scores_and_speech_only():
    a = {"campplus": [1.0, 0.0], "titanet": [0.0, 1.0]}
    assert engine.score(a, a) == pytest.approx(1.0)
    assert engine.score(a, {"campplus": [0.0, 1.0], "titanet": [1.0, 0.0]}) == pytest.approx(0.0, abs=1e-6)
    silence_then_talk = b"\x00\x00" * 16000 + speech(200, 2)
    kept = engine.speech_only(silence_then_talk)
    assert 0 < len(kept) < len(silence_then_talk) - 16000
