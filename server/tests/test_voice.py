"""Realtime voice gateway against a fake Gemini Live session."""
import asyncio
import contextlib
import json

from fastapi.testclient import TestClient
from google.genai import types

from app import voice
from app.db import DeviceAction, Message, session


class FakeSession:
    """Behaves like google.genai AsyncSession: receive() yields one turn, then ends."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.audio_in = []
        self.texts = []
        self.tool_responses = []
        self.client_content = []

    async def send_realtime_input(self, audio=None, text=None, **_):
        if audio is not None:
            self.audio_in.append(audio.data)
        if text is not None:
            self.texts.append(text)

    async def send_client_content(self, turns=None, turn_complete=True):
        self.client_content.append(turns)

    async def send_tool_response(self, function_responses):
        self.tool_responses.extend(function_responses)
        # after the tool result, the model speaks the confirmation
        self.turns.append([
            types.LiveServerMessage(server_content=types.LiveServerContent(
                model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x02\x00" * 50, mime_type="audio/pcm;rate=24000"))]),
                output_transcription=types.Transcription(text="Ho gaya, saat baje ka alarm laga diya."))),
            types.LiveServerMessage(server_content=types.LiveServerContent(turn_complete=True)),
        ])

    async def receive(self):
        while not self.turns:
            await asyncio.sleep(0.02)
        for m in self.turns.pop(0):
            yield m


def make_turns():
    return [[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        types.LiveServerMessage(server_content=types.LiveServerContent(input_transcription=types.Transcription(text="Kal subah saat baje "))),
        types.LiveServerMessage(server_content=types.LiveServerContent(input_transcription=types.Transcription(text="ka alarm laga do"))),
        types.LiveServerMessage(server_content=types.LiveServerContent(
            model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * 100, mime_type="audio/pcm;rate=24000"))]),
            output_transcription=types.Transcription(text="Haan, ek second."))),
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fc1", name="set_phone_alarm", args={"time": "07:00", "label": "Uthna hai"})])),
        types.LiveServerMessage(server_content=types.LiveServerContent(turn_complete=True)),
    ]]


def test_voice_call_end_to_end(env, monkeypatch):
    from app import main
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()
    fake = FakeSession(make_turns())
    seen_cfg = []

    @contextlib.asynccontextmanager
    async def fake_connect(config):
        seen_cfg.append(config)
        yield fake

    monkeypatch.setattr(voice, "connector", fake_connect)
    with TestClient(main.app) as c:
        h = c.get("/healthz").json()
        assert "realtime_voice" in h["features"] and any(v["id"] == "Puck" for v in h["voices"])
        conv = c.post("/api/conversations").json()["id"]
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
                    if ev["type"] == "turn_done" and sum(1 for e in events if e["type"] == "turn_done") == 2:
                        break
            ws.send_text(json.dumps({"type": "end"}))

    kinds = [e["type"] for e in events]
    assert kinds[0] == "ready" and events[0]["voice"] == "Achird"
    assert {"type": "user_text", "text": "Kal subah saat baje ka alarm laga do"} in events
    assert {"type": "tool", "label": "Phone par alarm laga raha hoon", "state": "done"} in events
    assert len(got_audio) == 2 and fake.audio_in and fake.audio_in[0] == b"\x00\x01" * 320
    assert fake.client_content, "greeting prompt sent on connect"
    r = fake.tool_responses[0]
    assert r.id == "fc1" and r.response["result"]["sent_to_phone"] is True
    # config: male voice, patient turn-taking, tone-aware
    cfg = seen_cfg[0]
    assert cfg.speech_config.voice_config.prebuilt_voice_config.voice_name == "Achird"
    assert cfg.enable_affective_dialog is True
    aad = cfg.realtime_input_config.automatic_activity_detection
    assert aad.end_of_speech_sensitivity == types.EndSensitivity.END_SENSITIVITY_LOW and aad.silence_duration_ms >= 900
    names = {d.name for d in cfg.tools[0].function_declarations}
    assert {"set_phone_alarm", "create_reminder", "santosh_kaam"} <= names and "submit_template" not in names
    assert "raha hoon" in cfg.system_instruction.parts[0].text
    with session() as s:
        assert s.query(DeviceAction).filter_by(conversation_id=conv, type="set_alarm").count() == 1
        shown = [m.display for m in s.query(Message).filter_by(conversation_id=conv).order_by(Message.id)]
    assert "Kal subah saat baje ka alarm laga do" in shown
    assert any(x and "Haan, ek second." in x for x in shown) and any(x and "saat baje ka alarm" in x for x in shown)


def test_voice_rejects_bad_key_and_missing_gemini(env, monkeypatch):
    from app import main
    from app.config import get_settings
    monkeypatch.setenv("API_KEY", "secret")
    get_settings.cache_clear()
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations", headers={"Authorization": "Bearer secret"}).json()["id"]
        import pytest
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
                ws.receive_text()
        with c.websocket_connect(f"/api/voice/ws?conv={conv}", headers={"Authorization": "Bearer secret"}) as ws:
            ev = json.loads(ws.receive_text())
            assert ev["type"] == "error" and "GEMINI_API_KEY" in ev["message"]


def test_voice_drops_settings_the_model_refuses(env, monkeypatch):
    """Real error from the phone: 1007 'Unknown name "proactivity" at 'setup''. The call must still connect."""
    from app import main
    from app.config import get_settings
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    voice.UNSUPPORTED.clear()
    fake = FakeSession(make_turns())
    configs = []

    @contextlib.asynccontextmanager
    async def picky_connect(config):
        configs.append(config)
        if config.proactivity is not None:
            raise Exception("1007 None. Invalid JSON payload received. Unknown name \"proactivity\" at 'setup': Cannot find field.")
        yield fake

    monkeypatch.setattr(voice, "connector", picky_connect)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            first = json.loads(ws.receive_text())
            assert first["type"] == "ready"
            ws.send_text(json.dumps({"type": "end"}))
    assert len(configs) == 2 and configs[1].proactivity is None
    assert configs[1].enable_affective_dialog is True          # everything else kept
    assert "proactivity" in voice.UNSUPPORTED
    # later calls skip it from the start
    assert voice.live_config("Puck", "hi-IN", "", None).proactivity is None
    voice.UNSUPPORTED.clear()
