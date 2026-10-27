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
    assert any("call just connected" in x for x in fake.texts), "greeting sent as live text"
    assert sum("call just connected" in x for x in fake.texts) == 1
    r = fake.tool_responses[0]
    assert r.id == "fc1" and r.response["result"]["sent_to_phone"] is True
    # config: male voice, patient turn-taking, tone-aware
    cfg = seen_cfg[0]
    assert cfg.speech_config.voice_config.prebuilt_voice_config.voice_name == "Achird"
    assert cfg.enable_affective_dialog is True and cfg.proactivity is None   # v0.181 affective dialog back (hears her tone)
    aad = cfg.realtime_input_config.automatic_activity_detection
    # answers at human speed: Gemini's own end-of-speech default and a 500-800 ms pause, not 1100
    assert aad.end_of_speech_sensitivity is None and 500 <= aad.silence_duration_ms <= 800
    assert aad.prefix_padding_ms == 300
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
    """Real error from the phone: 1007 'Unknown name "proactivity" at 'setup''. The call must still connect
    without the optional setting the model does not know."""
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
        if config.context_window_compression is not None:
            raise Exception("1007 None. Invalid JSON payload received. Unknown name \"contextWindowCompression\" at 'setup': Cannot find field.")
        yield fake

    monkeypatch.setattr(voice, "connector", picky_connect)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            first = json.loads(ws.receive_text())
            assert first["type"] == "ready"
            ws.send_text(json.dumps({"type": "end"}))
    assert len(configs) == 2 and configs[1].context_window_compression is None
    assert configs[1].realtime_input_config is not None        # everything else kept
    assert "context_window_compression" in voice.UNSUPPORTED
    # later calls skip it from the start
    assert voice.live_config("Puck", "hi-IN", "", None).context_window_compression is None
    voice.UNSUPPORTED.clear()


def test_voice_starts_fresh_when_resume_expired(env, monkeypatch):
    """Real error from the phone: 1008 'BidiGenerateContent session not found or expired'."""
    from app import main
    from app.config import get_settings
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    fake = FakeSession(make_turns())
    configs = []

    @contextlib.asynccontextmanager
    async def connect(config):
        configs.append(config)
        if config.session_resumption and config.session_resumption.handle:
            raise Exception("1008 None. BidiGenerateContent session not found or expired")
        yield fake

    monkeypatch.setattr(voice, "connector", connect)
    orig_run = voice.Call.run

    async def run_with_stale_handle(self):
        self.handle = "stale-handle"
        await orig_run(self)

    monkeypatch.setattr(voice.Call, "run", run_with_stale_handle)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert json.loads(ws.receive_text())["type"] == "ready"
            ws.send_text(json.dumps({"type": "end"}))
    assert configs[0].session_resumption.handle == "stale-handle"
    assert configs[-1].session_resumption.handle is None


# ---------------------------------------------------------------------------------------------
# v0.36: robustness (phone network drops, interruptions, reconnect loops, slow or repeated tools)
# ---------------------------------------------------------------------------------------------
import time  # noqa: E402


def wait_until(cond, timeout=6.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def read_events(ws, stop, limit=60):
    """Collect JSON events (audio frames skipped) until stop(event) is true."""
    events = []
    for _ in range(limit):
        m = ws.receive()
        if m.get("text"):
            ev = json.loads(m["text"])
            events.append(ev)
            if stop(ev):
                break
    return events


def _gemini_env(monkeypatch, **extra):
    from app.config import get_settings
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    for k, v in extra.items():
        monkeypatch.setenv(k, str(v))
    get_settings.cache_clear()


def _connector(monkeypatch, *sessions, configs=None):
    """The first connect gets sessions[0], the next sessions[1]... (the last one repeats)."""
    it = iter(sessions)
    last = {}

    @contextlib.asynccontextmanager
    async def connect(config):
        if configs is not None:
            configs.append(config)
        try:
            last["s"] = next(it)
        except StopIteration:
            pass
        yield last["s"]

    monkeypatch.setattr(voice, "connector", connect)


def _msg(**kw):
    return types.LiveServerMessage(server_content=types.LiveServerContent(**kw))


def test_voice_call_survives_a_phone_network_drop(env, monkeypatch):
    """Wi-Fi -> mobile data: the phone re-joins the same call; Gemini's session is untouched."""
    from app import main
    _gemini_env(monkeypatch)
    fake = FakeSession([])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            ready = read_events(ws, lambda e: e["type"] == "ready")[-1]
            call_id = ready["call_id"]
            assert call_id and "resumed" not in ready
            ws.send_text(json.dumps({"type": "ping"}))
            assert read_events(ws, lambda e: e["type"] == "pong")[-1] == {"type": "pong"}
            ws.send_bytes(b"\x01\x00" * 200)
            assert wait_until(lambda: b"\x01\x00" * 200 in fake.audio_in)
        # the phone connection is gone but the call is kept for the grace period
        assert wait_until(lambda: call_id in voice.CALLS)
        time.sleep(0.2)
        assert call_id in voice.CALLS
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&resume={call_id}") as ws2:
            again = read_events(ws2, lambda e: e["type"] == "ready")[-1]
            assert again["resumed"] is True and again["call_id"] == call_id
            ws2.send_bytes(b"\x02\x00" * 200)
            assert wait_until(lambda: b"\x02\x00" * 200 in fake.audio_in)
            ws2.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: call_id not in voice.CALLS)


def test_voice_resume_refused_when_call_is_gone_or_not_yours(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&resume=nope") as ws:
            ev = json.loads(ws.receive_text())
            assert ev["type"] == "error" and ev["code"] == "gone"


def test_voice_call_ends_when_phone_never_comes_back(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_RESUME_GRACE_S=1)
    fake = FakeSession([])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            call_id = read_events(ws, lambda e: e["type"] == "ready")[-1]["call_id"]
        assert wait_until(lambda: call_id not in voice.CALLS, timeout=5)   # grace (1 s) ran out: the call ended
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&resume={call_id}") as ws2:
            assert json.loads(ws2.receive_text())["code"] == "gone"


def test_voice_interruption_keeps_each_turn_separate(env, monkeypatch):
    """Cut in on Santosh: the half sentence is saved as its own turn, not glued to your next sentence."""
    from app import main
    _gemini_env(monkeypatch)
    turns = [[
        _msg(input_transcription=types.Transcription(text="Mausam batao")),
        _msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * 40, mime_type="audio/pcm;rate=24000"))]),
             output_transcription=types.Transcription(text="Aaj Akola mein ")),
        _msg(interrupted=True),
        _msg(input_transcription=types.Transcription(text="Nahi, alarm lagao")),
        _msg(output_transcription=types.Transcription(text="Theek hai, kitne baje?")),
        _msg(turn_complete=True),
    ]]
    _connector(monkeypatch, FakeSession(turns))
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            seen = []
            while sum(1 for e in seen if e["type"] == "turn_done") < 2:
                seen.extend(read_events(ws, lambda e: e["type"] == "turn_done", limit=40))
            ws.send_text(json.dumps({"type": "end"}))
    kinds = [e["type"] for e in seen]
    assert "interrupted" in kinds
    done = [e for e in seen if e["type"] == "turn_done"]
    assert done[0].get("interrupted") is True and not done[1].get("interrupted")
    with session() as s:
        shown = [m.display for m in s.query(Message).filter_by(conversation_id=conv).order_by(Message.id) if m.display]
    assert "Mausam batao" in shown and "Aaj Akola mein …" in shown
    assert "Nahi, alarm lagao" in shown and "Theek hai, kitne baje?" in shown
    assert not any("Mausam batao" in x and "alarm" in x for x in shown)


def test_voice_does_not_spin_when_gemini_hangs_up_at_once(env, monkeypatch):
    """A session that ends immediately, over and over, must back off and then tell the user, not hammer Gemini."""
    from app import main
    _gemini_env(monkeypatch)

    class HangsUp(FakeSession):
        async def receive(self):
            if False:
                yield None

    configs = []
    _connector(monkeypatch, HangsUp([]), configs=configs)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            events = read_events(ws, lambda e: e["type"] == "error", limit=20)
    kinds = [e["type"] for e in events]
    assert "status" in kinds and kinds[-1] == "error" and "toot gaya" in events[-1]["message"]
    assert len(configs) == 3


def test_voice_new_session_gets_a_short_briefing_and_no_stale_audio(env, monkeypatch):
    """When Gemini cannot resume, the next session is told what was just said; old mic audio is not replayed."""
    from app import main
    _gemini_env(monkeypatch)
    first = FakeSession([[
        _msg(input_transcription=types.Transcription(text="Kal ka mausam")),
        _msg(output_transcription=types.Transcription(text="Kal barish hogi")),
        _msg(turn_complete=True),
        types.LiveServerMessage(go_away=types.LiveServerGoAway()),
    ]])
    second = FakeSession([])
    _connector(monkeypatch, first, second)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "status" and e["state"] == "live", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
    assert any("Pichli baat" in t and "Kal ka mausam" in t and "Kal barish hogi" in t for t in second.texts)


def test_voice_queue_never_drops_a_note_for_audio(env):
    from app import main  # noqa: F401
    call = voice.Call(object(), "conv", "Puck", "hi-IN")
    call.push("text", "(note)")
    for _ in range(450):
        call.push("audio", b"x")
    assert call.audio.qsize() == 400
    assert ("text", "(note)") in list(call.audio._queue)
    call._drop_stale_audio()
    assert list(call.audio._queue) == [("text", "(note)")]


def test_voice_tool_runs_once_even_if_gemini_resends_it(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch)
    alarm = types.FunctionCall(id="fcA", name="set_phone_alarm", args={"time": "07:00", "label": "Uthna hai"})
    fake = FakeSession([[
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[alarm])),
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[alarm])),   # re-sent
        _msg(turn_complete=True),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: len(fake.tool_responses) >= 1)
            time.sleep(0.3)
            ws.send_text(json.dumps({"type": "end"}))
    assert len(fake.tool_responses) == 1
    with session() as s:
        assert s.query(DeviceAction).filter_by(conversation_id=conv, type="set_alarm").count() == 1


def test_voice_big_job_does_not_freeze_the_call(env, monkeypatch):
    """santosh_kaam that takes long: Gemini hears 'working' at once, the result is spoken in when it is done."""
    from app import main
    import app.agent as agent
    _gemini_env(monkeypatch, VOICE_TOOL_WAIT_S=1)

    async def slow_turn(conv, text, tenant_id=None, voice=False):
        await asyncio.sleep(1.6)
        return "WhatsApp list ready hai"

    monkeypatch.setattr(agent, "run_turn", slow_turn)
    fake = FakeSession([[
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fcK", name="santosh_kaam", args={"request": "list banao"})])),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: len(fake.tool_responses) >= 1, timeout=4)
            assert fake.tool_responses[0].response["status"] == "working"
            assert wait_until(lambda: any("WhatsApp list ready hai" in t for t in fake.texts), timeout=5)
            ws.send_text(json.dumps({"type": "end"}))


def test_voice_slow_tool_is_cut_off_with_a_spoken_reason(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_TOOL_TIMEOUT_S=5)

    async def hangs(name, args, ctx):
        await asyncio.sleep(30)

    monkeypatch.setattr(voice, "dispatch", hangs)
    fake = FakeSession([[
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fcT", name="get_weather", args={"city": "Akola"})])),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: len(fake.tool_responses) >= 1, timeout=9)
            ws.send_text(json.dumps({"type": "end"}))
    assert "der le raha" in fake.tool_responses[0].response["error"]


def test_voice_result_goes_in_as_a_note_when_the_session_moved_on(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch)

    class Moved(FakeSession):
        async def send_tool_response(self, function_responses):
            raise RuntimeError("session closed")

    fake = Moved([[types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
        types.FunctionCall(id="fcM", name="set_phone_alarm", args={"time": "07:00", "label": "Uthna hai"})]))]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: any("Pehle ka kaam 'set_phone_alarm'" in t for t in fake.texts))
            ws.send_text(json.dumps({"type": "end"}))


def test_voice_withdrawn_tool_call_is_not_answered_but_not_lost(env, monkeypatch):
    """The user talked over a request: Gemini withdraws the call. The work still finishes and is mentioned as a note."""
    from app import main
    _gemini_env(monkeypatch)

    async def slowish(name, args, ctx):
        await asyncio.sleep(0.6)
        return {"done": True}

    monkeypatch.setattr(voice, "dispatch", slowish)
    fake = FakeSession([[
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fcC", name="set_phone_alarm", args={})])),
        types.LiveServerMessage(tool_call_cancellation=types.LiveServerToolCallCancellation(ids=["fcC"])),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: any("Pehle ka kaam 'set_phone_alarm'" in t for t in fake.texts), timeout=5)
            ws.send_text(json.dumps({"type": "end"}))
    assert fake.tool_responses == []
