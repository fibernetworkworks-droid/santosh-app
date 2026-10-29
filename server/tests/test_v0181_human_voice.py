"""v0.181 HUMAN VOICE: the call answers with feeling (affective dialog back, self-healing if this model generation
refuses it), "ek second" clips in 16 flavours on the new gemini-3.8-flash-tts (legacy fallback), quicker turn-taking
(550 ms default, 420 ms floor for her own pauses), and the tuned fast barge-in finally reaching the phone."""
import contextlib
import json

from fastapi.testclient import TestClient
from google.genai import types

from app import main, voice, voicestyle
from tests.test_voice import FakeSession, _gemini_env, _msg, read_events


import pytest as _pytest


@_pytest.fixture(autouse=True)
def _older_live_model(monkeypatch):
    """v0.221 gemini-3.8-live dropped affective dialog (Hoola never sends it to 3.x); these heal paths are for
    older native-audio models that still take the field, so they pin one."""
    from app.config import get_settings
    monkeypatch.setenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()



def test_affective_dialog_back_on_by_default(env):
    cfg = voice.live_config("Puck", "hi-IN", "", None)
    assert cfg.enable_affective_dialog is True     # he HEARS her laugh / stress / excitement and answers with a matching tone
    assert cfg.proactivity is None                 # 3.8-live always has proactivity on


def test_affective_master_switch_off(env, monkeypatch):
    _gemini_env(monkeypatch, VOICE_AFFECTIVE="0")
    assert voice.live_config("Puck", "hi-IN", "", None).enable_affective_dialog is None


def test_turn_taking_defaults_quicker(env):
    aad = voice.live_config("Puck", "hi-IN", "", None).realtime_input_config.automatic_activity_detection
    assert aad.silence_duration_ms == 550          # was 700: people reply in ~0.2 s, the old wait felt like a bad line
    assert voicestyle.SILENCE_MIN == 420 and voicestyle.SILENCE_MAX == 1000   # her own pauses still raise it


def test_ready_tells_the_phone_about_fast_barge(env):
    v = voice.vad_config()
    assert v["fast"] == 0.85 and v["need"] == 0.5 and v["idle_gate"] is True


def test_ack_lines_varied():
    assert len(voice.ACK_LINES) >= 14 and len(set(voice.ACK_LINES)) == len(voice.ACK_LINES)


def test_ack_tts_uses_new_model_with_legacy_fallback(env, monkeypatch):
    calls = []
    resp = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        parts=[types.Part(inline_data=types.Blob(data=b"\x01\x02", mime_type="audio/pcm;rate=24000"))]))])

    class FakeModels:
        def generate_content(self, *, model, config, contents):
            calls.append(model)
            if model == "gemini-3.8-flash-tts":
                raise RuntimeError("model not found")   # any refusal / outage
            assert "feeling in the voice" in contents   # v0.181 warm, hurried delivery prompt
            return resp

    class FakeClient:
        def __init__(self, **kw):
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)
    pcm = voice._ack_tts("Haan, ek second.", "Puck", "m")
    assert pcm == b"\x01\x02"
    assert calls == ["gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts"]


def test_affective_refusal_never_kills_the_call(env, monkeypatch):
    """This model generation refuses affective dialog: the first connect fails, the call retries at once WITHOUT
    it and remembers for the process. No dead call, no SETUP step burnt."""
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": True})
    fake = FakeSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Kal subah chai ya coffee?")),
        _msg(output_transcription=types.Transcription(text="Chai. Aur aap batao, kaisi ho?")),
        _msg(turn_complete=True),
    ]])
    configs, tries = [], []

    @contextlib.asynccontextmanager
    async def healing_connect(config):
        configs.append(config)
        tries.append(1)
        if len(tries) == 1:
            raise RuntimeError('400 UNKNOWN: Unknown name "enable_affective_dialog" at \'setup\': Cannot find field.')
        yield fake

    monkeypatch.setattr(voice, "connector", healing_connect)
    _gemini_env(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice=Puck&lang=hi-IN") as ws:
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
    assert len(configs) == 2                                    # refused once, retried at once inside the same call
    assert configs[0].enable_affective_dialog is True
    assert configs[1].enable_affective_dialog is None
    assert voice._AFFECTIVE["ok"] is False                      # the rest of this process never sends it again
