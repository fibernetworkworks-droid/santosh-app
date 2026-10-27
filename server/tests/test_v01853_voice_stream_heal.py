"""v0.185.3 the affective heal moves to where the refusal REALLY arrives.

The VPS (26 Oct) proved the SDK's connect() returns BEFORE setupComplete: Gemini's generic
"1007 Request contains an invalid argument" lands as a STREAM CLOSE ("voice stream ended:
ConnectionClosedError Close(code=1007...)"), never as a connect error. The v0.185.1 heal sat
only on the connect path, so in production it never fired, the SETUP ladder burnt every rung
with affective still on, and both test calls died "done: 0 turns" while the phone showed a
connected-but-silent call (the exact owner report). The old tests faked the refusal AT connect
(raise before yield) - the tests were green while the real path was broken. These tests use the
REAL shape: connect succeeds, the session's receive() raises the close."""
import contextlib
import json

from fastapi.testclient import TestClient
from google.genai import types
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from app import main, voice
from tests.test_voice import FakeSession, _gemini_env, _msg, read_events

# the EXACT shape from the VPS pm2 log, 26 Oct ~11:49
CLOSE_1007 = ConnectionClosedError(Close(1007, "Request contains an invalid argument."),
                                   Close(1007, "Request contains an invalid argument."), True)


class RefusingSession(FakeSession):
    """A session that connects fine and then dies mid-stream with the generic 1007 close."""

    async def receive(self):
        raise CLOSE_1007
        yield  # pragma: no cover - makes this an async generator like the real receive()


def test_stream_close_1007_with_affective_on_heals_in_place(env, monkeypatch):
    """THE real regression: connect succeeds, the 1007 arrives as a stream close. The heal must fire
    THERE - drop affective process-wide, retry the SAME setup (ladder untouched) - and the call
    must live: today this exact sequence ends 'done: 0 turns' on the VPS."""
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": True})
    good = FakeSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Kal subah chai ya coffee?")),
        _msg(output_transcription=types.Transcription(text="Chai. Aur aap batao, kaisi ho?")),
        _msg(turn_complete=True),
    ]])
    configs, sessions = [], []

    @contextlib.asynccontextmanager
    async def connect_ok_then_stream_refused(config):
        configs.append(config)
        s = RefusingSession([]) if len(configs) == 1 else good
        sessions.append(s)
        yield s

    monkeypatch.setattr(voice, "connector", connect_ok_then_stream_refused)
    _gemini_env(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice=Puck&lang=hi-IN") as ws:
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
    assert len(configs) == 2                                    # one refusal, healed at the same rung
    assert configs[0].enable_affective_dialog is True
    assert configs[1].enable_affective_dialog is None           # the retry goes out without it
    assert voice._AFFECTIVE["ok"] is False                      # every later call in this process skips it
    assert good.turns == []                                     # the healed session really spoke: its turn played out to turn_done


def test_stream_close_1007_with_affective_off_climbs_ladder(env, monkeypatch):
    """With affective already dropped, a stream-close 1007 must NOT loop the heal - it climbs the
    SETUP ladder exactly as before and ends in the honest error event, no hang."""
    monkeypatch.setattr(voice, "_AFFECTIVE", {"ok": False})
    monkeypatch.setattr(voice, "SETUP", {"step": 0, "key": "", "at": 0.0, "refusals": 0, "healed": 0, "loaded": True})
    configs = []

    @contextlib.asynccontextmanager
    async def connect_ok_stream_always_refused(config):
        configs.append(config)
        yield RefusingSession([])

    monkeypatch.setattr(voice, "connector", connect_ok_stream_always_refused)
    _gemini_env(monkeypatch, VOICE_SAFE_SETUP="1")
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&voice=Puck&lang=hi-IN") as ws:
            events = read_events(ws, lambda e: e["type"] == "error", limit=240)
    assert events and events[-1]["type"] == "error"             # honest failure, no hang
    assert len(configs) >= 4                                    # the ladder really climbed (mcp, vocab, langcodes...)
    assert all(cfg.enable_affective_dialog is None for cfg in configs)   # the heal never re-added it
