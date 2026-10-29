"""v0.150 A call Gemini refuses heals itself (the 'Connection thoda slow hai, sambhal raha hoon' loop).

1. Gemini 3.x closes the session (1007 invalid argument) when client_content arrives mid-call: quiet notes now wait
   for the next tool answer instead, and a model that turns out not to allow it is learned at runtime.
2. A setup refused without a field name: the call retries with one extra less each time and remembers what worked.
3. python -m app.voicecheck finds the refused part (down to the one tool).
"""
import asyncio
import contextlib
import json
import time

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app import voice
from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, read_events

BAD = "1007 None. Request contains an invalid argument."


@pytest.fixture(autouse=True)
def _fresh():
    voice._AFFECTIVE["ok"] = True
    voice.SETUP.update(step=0, key="", at=0.0, refusals=0, healed=0, loaded=False)
    voice.QUIET.update(client_content=None, queued=0, live=0, sent=0, learned_off=0)
    voice.UNSUPPORTED.clear()
    yield
    voice._AFFECTIVE["ok"] = True     # v0.185.2 the call loop's heal flips this process-wide - never leak it
    voice.SETUP.update(step=0, key="", at=0.0, loaded=False)
    voice.QUIET.update(client_content=None)
    # v0.185.2 the voicecheck test here calls remember_setup(5), which persists data/voice_setup.json
    # on disk - without this unlink the file poisoned later suites in the same sweep (seen 26 Oct)
    import contextlib as _cl
    with _cl.suppress(Exception):
        voice._setup_file().unlink(missing_ok=True)


def _audio(text="Haan, boliye."):
    return _msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * 80, mime_type="audio/pcm;rate=24000"))]),
                output_transcription=types.Transcription(text=text))


def test_gemini3_quiet_notes_ride_on_the_tool_answer(env, monkeypatch):
    """Default model gemini-3.8-live: a language drift note is never sent as client_content mid-call."""
    from app import main
    _gemini_env(monkeypatch, VOICE_QUIET_NOTES="queue")
    assert voice.client_content_ok() is False
    ran = []

    async def tool(name, args, ctx):
        ran.append(name)
        return {"ok": True}

    monkeypatch.setattr(voice, "dispatch", tool)
    fake = FakeSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Kal ki meeting chaar baje kar do")),
        _msg(output_transcription=types.Transcription(text="Sure, I have moved the meeting to four o'clock for you.")),
        _msg(turn_complete=True),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&lang=hi-IN") as ws:
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            fake.turns.append([types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
                types.FunctionCall(id="t1", name="get_weather", args={"city": "Akola"})]))])
            for _ in range(100):
                if fake.tool_responses:
                    break
                time.sleep(0.05)
            ws.send_text(json.dumps({"type": "end"}))
        stats = c.get("/api/voice/stats").json()
    assert fake.client_content == []                                   # never mid-call on Gemini 3.x
    r = fake.tool_responses[0]
    assert "Language note" in r.response.get("note_for_you", "")      # delivered with the next tool answer
    assert stats["setup"]["quiet_notes"] == "queued" and stats["setup"]["notes_queued"] >= 1


class _DiesOnClientContent(FakeSession):
    """An older-name model that still refuses client_content mid-call: the session closes with 1007."""

    def __init__(self, turns):
        super().__init__(turns)
        self.dead = False

    async def send_client_content(self, turns=None, turn_complete=True):
        self.client_content.append(turns)
        self.dead = True

    async def receive(self):
        while not self.turns:
            if self.dead:
                raise Exception(BAD)
            await asyncio.sleep(0.02)
        for m in self.turns.pop(0):
            yield m


def test_a_1007_right_after_client_content_is_learned(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, GEMINI_LIVE_MODEL="gemini-2.5-flash-native-audio")
    assert voice.client_content_ok() is True
    first = _DiesOnClientContent([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Kal ki meeting chaar baje kar do")),
        _msg(output_transcription=types.Transcription(text="Sure, I have moved the meeting to four o'clock for you.")),
        _msg(turn_complete=True),
    ]])
    second = FakeSession([[_audio(), _msg(turn_complete=True)]])
    configs = []
    _connector(monkeypatch, first, second, configs=configs)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&lang=hi-IN") as ws:
            evs = read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            evs += read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
    assert len(configs) == 2 and first.client_content                  # the note killed the first session
    assert voice.QUIET["client_content"] is False and voice.QUIET["learned_off"] == 1
    assert not any(e["type"] == "status" and e.get("state") == "reconnecting" for e in evs)   # not a "slow" moment
    assert second.client_content == []


def test_refused_setup_heals_step_by_step_and_is_remembered(env, monkeypatch):
    from app import main, voicestyle
    _gemini_env(monkeypatch)
    monkeypatch.setattr(voicestyle, "for_call", lambda t: {"vocab": ["Rameshwar", "Akot"], "silence_ms": None,
                                                          "block": "", "styled": False, "fixes": 0})
    configs = []

    @contextlib.asynccontextmanager
    async def picky(config):
        configs.append(config)
        tr = config.input_audio_transcription
        if tr is not None and tr.custom_vocabulary:
            raise Exception(BAD)
        yield FakeSession([[_audio(), _msg(turn_complete=True)]])

    monkeypatch.setattr(voice, "connector", picky)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            evs = read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
        # v0.221 3.8-live never gets enable_affective_dialog, so the heal's extra connect is gone: back to the
        # v0.150 shape - the refused extra (vocab) is left out on the second connect, nothing else
        assert len(configs) == 2
        assert all(cfg.enable_affective_dialog is None for cfg in configs)
        assert configs[0].input_audio_transcription.custom_vocabulary == ["Rameshwar", "Akot"]
        assert configs[1].input_audio_transcription.custom_vocabulary is None
        assert configs[1].input_audio_transcription.language_codes      # only the refused extra is left out
        assert configs[1].context_window_compression is not None
        assert evs[0]["type"] == "ready"
        assert voice.SETUP["step"] == 2 and json.loads(open("data/voice_setup.json").read())["step"] == 2
        # the next call starts straight from what worked: one connect, no refusal
        configs.clear()
        voice.SETUP["loaded"] = False
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
        assert len(configs) == 1 and configs[0].input_audio_transcription.custom_vocabulary is None
        stats = c.get("/api/voice/stats").json()
    assert stats["setup"]["without"] == ["mcp", "vocab"]


def test_clean_vocab_and_core_tool_steps(env, monkeypatch):
    _gemini_env(monkeypatch)
    assert voice.clean_vocab(["Rameshwar", "rameshwar", "a", "x@y.com", "😀 Maa", "Sharma ji", "राजू", "<b>"]) == \
        ["Rameshwar", "Sharma ji", "राजू"]
    assert voice.clean_vocab([]) is None
    full = voice.live_config("Puck", "hi-IN", "", None)
    core = voice.live_config("Puck", "hi-IN", "", None, safe=5)
    bare = voice.live_config("Puck", "hi-IN", "", None, safe=6)
    n = lambda c: {d.name for d in c.tools[0].function_declarations}
    assert len(n(full)) > 100 and "santosh_kaam" in n(core) and len(n(core)) <= 20
    assert n(bare) == {"santosh_kaam"}
    assert core.context_window_compression is None and core.input_audio_transcription.language_codes is None


class _CheckLive:
    """Gemini for app.voicecheck: refuses any setup that declares maps_search; answers otherwise."""

    def __init__(self, config):
        names = {d.name for d in (config.tools[0].function_declarations if config.tools else [])}
        if "maps_search" in names:
            raise Exception(BAD)
        self.cc = False

    async def send_realtime_input(self, **_):
        pass

    async def send_client_content(self, **_):
        raise Exception(BAD)      # Gemini 3.x mid-call client_content

    async def receive(self):
        yield _audio()
        yield _msg(turn_complete=True)


def test_voicecheck_finds_the_refused_tool(env, monkeypatch):
    from app import voicecheck
    _gemini_env(monkeypatch)

    @contextlib.asynccontextmanager
    async def connect(config):
        yield _CheckLive(config)

    monkeypatch.setattr(voice, "connector", connect)
    res = asyncio.run(voicecheck.run())
    assert res["steps"][0]["ok"] is False and "invalid argument" in res["steps"][0]["error"]
    assert res["refused_part"] == "core_tools" and res["culprit"] == "tool maps_search"
    assert res["mid_call_client_content"]["ok"] is False
    assert voice.SETUP["step"] == res["works_at"] == 5
    assert "maps_search" in res["say"]


def test_compact_schemas_keep_fields_named_title(env, monkeypatch):
    """v0.150.1 the real cause on her VPS: compaction dropped every field named "title" while "required" kept it,
    so Gemini refused the whole call: 1007 "schema at top-level requires unspecified property 'title'"."""
    _gemini_env(monkeypatch)
    assert voice.client_content_ok() is True                     # gemini-3.8-live takes mid-call notes (voicecheck)
    cfg = voice.live_config("Puck", "hi-IN", "", None, extra_tools=[{
        "name": "mcp_x__make", "description": "d", "input_schema": {
            "type": "object", "title": "Args", "required": ["title", "ghost"],
            "properties": {"title": {"type": "string", "title": "Title"}, "default": {"type": "string"}}}}])
    decls = {d.name: d.parameters_json_schema for d in cfg.tools[0].function_declarations}
    for name, sch in decls.items():
        assert voice.schema_problems(sch) == [], name
    ev = decls["add_calendar_event"]
    assert "title" in ev["properties"] and "title" in ev["required"]
    assert decls["form_create"]["properties"]["questions"]["items"]["properties"].get("title")
    mcp = decls["mcp_x__make"]
    assert mcp["required"] == ["title"] and set(mcp["properties"]) == {"title", "default"} and "title" not in mcp
