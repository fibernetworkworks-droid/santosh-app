"""v0.275.0 OPENAI VOICE Phase 2 + 3: every call feature behaves on the OpenAI engine as on Gemini (news at a pause,
hold for her phone call, a dropped OpenAI connection rebuilt with the talk so far), and the phone gets its own
"Call ki awaaz" picker instead of a curl command."""
import asyncio
import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import voice, voice_openai, voiceengine
from tests.test_v0264_openai_voice import FakeOA, oa, _drive  # noqa: F401  (fixture reused)
from tests.test_voice import wait_until

ROOT = Path(__file__).resolve().parents[2]


class Rec:
    def __init__(self):
        self.sent = []

    async def send(self, ev):
        self.sent.append(ev)


def _call():
    c = voice_openai.OpenAICall.__new__(voice_openai.OpenAICall)
    c.stats, c._quiet_pending, c.hold = {}, [], ""
    c._responding, c._want_response, c._asked = False, False, False
    c.audio = asyncio.Queue()
    return c


def test_job_news_reaches_openai_and_gets_one_reply():
    async def go():
        c, s = _call(), Rec()
        c.push = voice.Call.push.__get__(c)
        c._held_texts = []
        c.push("text", "[Kaam update] video ban gaya")
        up = asyncio.create_task(c.uplink(s))
        await asyncio.sleep(0.05)
        up.cancel()
        return s.sent
    sent = asyncio.run(go())
    assert sent[0]["type"] == "conversation.item.create" and "video ban gaya" in sent[0]["item"]["content"][0]["text"]
    assert [e["type"] for e in sent].count("response.create") == 1


def test_on_hold_his_voice_waits_and_the_hold_note_is_quiet():
    async def go():
        c, s = _call(), Rec()
        c._session = s
        c.hold, c._hold_turn_audio, c._hold_turn_reply = "phone_call", [], False
        played = []

        async def send_audio(b):
            played.append(b)
        c.send_audio = send_audio
        c._item, c._resp_audio, c._breath_next = "", False, False

        class Ev:
            async def events(self):
                yield {"type": "response.output_audio.delta", "item_id": "x", "delta": base64.b64encode(b"\x01\x00" * 50).decode()}
        await voice_openai.OpenAICall.downlink(c, Ev())
        await c._tell_quietly("(Hold: woh phone par hai - chup raho)", live=True)
        return played, c._hold_turn_audio, s.sent
    played, held, sent = asyncio.run(go())
    assert not played and held                                  # never played into her phone call
    assert [e["type"] for e in sent] == ["conversation.item.create"]    # the hold note starts no reply


def test_a_dropped_openai_connection_is_rebuilt_with_the_talk_so_far(oa, monkeypatch):
    """OpenAI's socket dies mid-call: a NEW session gets the same persona + a reseed of the talk so far."""
    from app import main
    sessions = []

    class Dies(FakeOA):
        async def events(self):
            n = 0
            async for ev in super().events():
                yield ev
                n += 1
                if not sessions[1:] and n >= 4:        # the first connection drops after the greeting
                    return

    async def connect():
        s = Dies()
        sessions.append(s)
        return s
    monkeypatch.setattr(voice_openai, "connect", connect)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        c.put("/api/voice/engine", json={"engine": "openai"})
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            ws.send_bytes(b"\x00\x01" * 320)
            assert wait_until(lambda: len(sessions) >= 2, timeout=8)
            ws.send_text(json.dumps({"type": "end"}))
    second = sessions[1].sent
    assert any(e["type"] == "session.update" and "AWAAZ MEIN JAAN" in e["session"]["instructions"] for e in second)


def test_engine_view_has_rupees(env, tmp_path, monkeypatch):
    monkeypatch.setattr(voiceengine, "DIR", tmp_path / "ve")
    voiceengine.add_usage("default", usd=1.0)
    v = voiceengine.view("default")
    assert v["month_inr"] > 50 and v["month_budget_inr"] > 0


def test_phone_picker_and_call_badge_wired():
    scr = (ROOT / "lib/ui/voice_engine_screen.dart").read_text()
    assert "voiceEngineSet(engine)" in scr and "Real voice (OpenAI)" in scr and "month_inr" in scr
    assert "VoiceEngineScreen(app: app)" in (ROOT / "lib/ui/profile_screen.dart").read_text()
    api = (ROOT / "lib/api.dart").read_text()
    assert "'/api/voice/engine'" in api and "'PUT', '/api/voice/engine'" in api
    assert "engine = (e['engine'] as String?) ?? 'gemini'" in (ROOT / "lib/call_session.dart").read_text()
    assert "call.engine == 'openai'" in (ROOT / "lib/ui/live_voice_screen.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.301.0"
    assert "0.301.0+341" in (ROOT / "pubspec.yaml").read_text()
