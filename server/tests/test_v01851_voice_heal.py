"""v0.185.1 the voice fix for the VPS deploy day: Gemini refuses enable_affective_dialog with a GENERIC
"1007 invalid argument" that never names the field, so v0.181's _affective_refused() heal never fired and
every call burnt the whole SETUP ladder and died with 0 turns. Now a generic setup refusal with affective
on drops affective once, process-wide, and retries inside the same call; ack clips build with ONE shared
TTS client per batch instead of a fresh Client per clip."""
import contextlib
import json

from fastapi.testclient import TestClient
from google.genai import types

from app import main, voice
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


GENERIC_1007 = RuntimeError("APIError('1007 None. Request contains an invalid argument.')")


def test_generic_1007_with_affective_on_heals_at_once(env, monkeypatch):
    """THE regression from the VPS (26 Oct): a generic 1007 on connect must drop affective ONCE and retry
    in the same call - no ladder burnt, no dead call, and the process remembers for every later call."""
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": True})
    fake = FakeSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Kal subah chai ya coffee?")),
        _msg(output_transcription=types.Transcription(text="Chai. Aur aap batao, kaisi ho?")),
        _msg(turn_complete=True),
    ]])
    configs, tries = [], []

    @contextlib.asynccontextmanager
    async def generic_refusing_connect(config):
        configs.append(config)
        tries.append(1)
        if len(tries) == 1:
            raise GENERIC_1007          # the REAL shape of the refusal: generic, no field named
        yield fake

    monkeypatch.setattr(voice, "connector", generic_refusing_connect)
    _gemini_env(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice=Puck&lang=hi-IN") as ws:
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
    assert len(configs) == 2                                    # refused once, healed inside the same call
    assert configs[0].enable_affective_dialog is True
    assert configs[1].enable_affective_dialog is None           # the retry goes out without it
    assert voice._AFFECTIVE["ok"] is False                      # every later call in this process skips it


def test_generic_1007_with_affective_already_off_climbs_ladder(env, monkeypatch):
    """With affective already dropped, a generic 1007 must NOT loop the heal - it climbs the SETUP ladder
    as before and finally tells the phone the truth (error event) instead of hanging."""
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": False})
    monkeypatch.setattr(voice, "SETUP", {"step": 0, "key": "", "at": 0.0, "refusals": 0, "healed": 0, "loaded": True})
    configs = []

    @contextlib.asynccontextmanager
    async def always_refusing(config):
        configs.append(config)
        raise GENERIC_1007
        yield None            # pragma: no cover

    monkeypatch.setattr(voice, "connector", always_refusing)
    _gemini_env(monkeypatch, VOICE_SAFE_SETUP="1")
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice=Puck&lang=hi-IN") as ws:
            events = read_events(ws, lambda e: e["type"] == "error", limit=240)
    assert events and events[-1]["type"] == "error"             # honest failure, no hang
    assert len(configs) >= 4                                    # the ladder really climbed (mcp, vocab, langcodes...)
    assert all(cfg.enable_affective_dialog is None for cfg in configs)   # the heal never re-added it


def test_ack_batch_builds_with_one_shared_client(env, monkeypatch, tmp_path):
    """v0.185.1: the whole ack batch shares ONE genai client (was a fresh Client per clip - on the VPS every
    clip died at once with 'client has been closed'). A batch client that cannot be made falls back softly."""
    made = []
    resp = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        parts=[types.Part(inline_data=types.Blob(data=b"\x10\x27" * 4000, mime_type="audio/pcm;rate=24000"))]))])

    class FakeModels:
        def generate_content(self, *, model, config, contents):
            assert "feeling in the voice" in contents
            return resp

    class FakeClient:
        def __init__(self, **kw):
            made.append(1)
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)
    monkeypatch.setattr(voice, "ACK_DIR", tmp_path)
    _gemini_env(monkeypatch)
    voice._ACKS.pop("TestV:m", None)
    voice._ACK_BUSY.discard("TestV:m")
    voice._build_acks("TestV:m", "TestV", "m")
    assert len(made) == 1                                       # ONE client for all of ACK_LINES
    assert len(voice._ACKS["TestV:m"]) == len(voice.ACK_LINES)  # every clip built and cached


def test_ack_tts_still_works_without_a_shared_client(env, monkeypatch):
    """Back-compat: a caller without the batch client (old signature, tests, tools) still gets its clip."""
    resp = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        parts=[types.Part(inline_data=types.Blob(data=b"\x10\x27" * 4000, mime_type="audio/pcm;rate=24000"))]))])

    class FakeModels:
        def generate_content(self, *, model, config, contents):
            return resp

    class FakeClient:
        def __init__(self, **kw):
            self.models = FakeModels()

    monkeypatch.setattr("google.genai.Client", FakeClient)
    _gemini_env(monkeypatch)
    assert voice._ack_tts("Haan, ek second.", "TestV", "m")     # creates its own client, returns audio
