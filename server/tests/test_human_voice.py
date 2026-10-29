"""v0.37: a call that sounds like a person. Turn-taking speed, the persona, the greeting, no dead air while a
tool runs, and the quality numbers that show how human it sounds."""
import asyncio
import json
import time
from array import array

from fastapi.testclient import TestClient
from google.genai import types

from app import voice
from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, read_events, wait_until

LOUD = array("h", [9000, -9000] * 320).tobytes()     # 40 ms of someone talking (16 kHz)


def _audio(n=100):
    return types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x01\x00" * n, mime_type="audio/pcm;rate=24000"))])


def test_persona_talks_like_a_person_not_a_helpdesk(env):
    p = voice.persona_prompt("Santosh", "m").format(lang="hi-IN", now="now", context="ctx")
    assert p.startswith("You are Santosh, on a live phone call")
    # persona and speaking style come before the tool rules
    assert p.index("How you talk") < p.index("Which tool")
    for rule in ("Do not end every turn with a question", "Do not repeat back what the user said",
                 "never textbook Hindi", "One idea per turn", "never repeat them word for word"):
        assert rule in p
    assert "sincerely asks" in p and "you are an AI" in p             # honest when asked
    assert "kar deta hoon" in p and p.rstrip().endswith("ctx")
    f = voice.persona_prompt("Meera", "f").format(lang="hi-IN", now="now", context="ctx")
    assert "You are female" in f and "Indian woman" in f
    assert "kar deti hoon" in f and "Dekhti hoon" in f and "Bhej rahi hoon" in f and "check karti hoon" in f
    assert "kar deta hoon" not in f and "Dekhta hoon" not in f
    assert "kya chal raha hai!" in f                                   # the user's own words are not changed
    assert 'Never "raha" or "gaya" for yourself' in f


def test_turn_taking_is_fast_and_tunable(env, monkeypatch):
    cfg = voice.live_config("Puck", "hi-IN", "", None)
    aad = cfg.realtime_input_config.automatic_activity_detection
    assert aad.silence_duration_ms == 550 and aad.end_of_speech_sensitivity is None and aad.prefix_padding_ms == 300
    # noise and far voices must not count as the user starting to talk
    assert aad.start_of_speech_sensitivity == types.StartSensitivity.START_SENSITIVITY_LOW
    assert cfg.enable_affective_dialog is None and cfg.proactivity is None   # v0.221 3.8-live removed affective dialog (tone comes from the prompt)
    _gemini_env(monkeypatch, VOICE_SILENCE_MS=600, VOICE_END_SENSITIVITY="High", VOICE_PREFIX_PADDING_MS=200,
                VOICE_START_SENSITIVITY="")
    aad = voice.live_config("Puck", "hi-IN", "", None).realtime_input_config.automatic_activity_detection
    assert aad.start_of_speech_sensitivity is None
    assert aad.silence_duration_ms == 600 and aad.prefix_padding_ms == 200
    assert aad.end_of_speech_sensitivity == types.EndSensitivity.END_SENSITIVITY_HIGH
    _gemini_env(monkeypatch, VOICE_SILENCE_MS=20, VOICE_END_SENSITIVITY="low")
    aad = voice.live_config("Puck", "hi-IN", "", None).realtime_input_config.automatic_activity_detection
    assert aad.silence_duration_ms == 300          # never so short that every breath ends the turn
    assert aad.end_of_speech_sensitivity == types.EndSensitivity.END_SENSITIVITY_LOW


def test_greeting_is_short_varied_and_gendered(env):
    g = voice.greeting("default", "m")
    assert "call just connected" in g and "ONE short line" in g and "different every time" in g
    assert any(x in g for x in ("morning", "afternoon", "evening", "late night"))
    assert "sun raha hoon" in g and "helpdesk" in g
    assert "sun rahi hoon" in voice.greeting("default", "f")


def test_trimmed_clip_has_no_silence_or_click():
    silence = b"\x00\x00" * 24000
    talk = array("h", [8000, -8000] * 6000).tobytes()          # 0.5 s
    out = array("h")
    out.frombytes(voice._trim(silence + talk + silence))
    assert 0.5 * 24000 <= len(out) <= 0.6 * 24000               # 30 ms margin each side, no long silence
    assert out[0] == 0 and abs(out[-1]) < 100                    # faded in and out
    assert len(voice._trim(silence)) == 0
    long = array("h", [8000, -8000] * 48000).tobytes()          # 4 s
    assert len(voice._trim(long)) == 24000 * 16 // 10 * 2        # capped at 1.6 s


def _ack_setup(monkeypatch, tool_s=1.5):
    voice._ACKS.clear()
    voice._ACK_BUSY.clear()
    made = []

    def fake_tts(text, v, g, client=None):   # v0.185.1 _build_acks hands the batch's shared client (ignored here)
        made.append((text, v, g))
        return b"\x00\x00" * 100 + array("h", [7000, -7000] * 2400).tobytes() + b"\x00\x00" * 100

    monkeypatch.setattr(voice, "_ack_tts", fake_tts)

    async def slow(name, args, ctx):
        await asyncio.sleep(tool_s)
        return {"temp": "31 C"}

    monkeypatch.setattr(voice, "dispatch", slow)
    return made


def test_silent_tool_gets_a_quick_ek_second_in_his_voice(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_TOOL_ACK="true")
    voice.STATS.clear()
    made = _ack_setup(monkeypatch)
    fake = FakeSession([[
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fcW", name="get_weather", args={"city": "Pune"})])),
    ]])
    fake.send_tool_response = _no_followup(fake)
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            got = []
            end = time.time() + 5
            while time.time() < end and not got:
                m = ws.receive()
                if m.get("bytes"):
                    got.append(m["bytes"])
            assert got and len(got[0]) < 24000 * 2 * 2            # a short clip, not a long sentence
            assert wait_until(lambda: fake.tool_responses)
            ws.send_text(json.dumps({"type": "end"}))
        assert {v for _, v, _ in made} == {"Puck"} and len(made) == len(voice.ACK_LINES)
        assert wait_until(lambda: voice.STATS and voice.STATS[-1]["call_id"])
        s = c.get("/api/voice/stats").json()
    assert s["tool_calls"] >= 1 and s["acks_played"] >= 1 and s["silent_tools_pct"] == 100.0
    # the clips are kept on disk: the next server start does not make them again (v0.201: generation tag in the name)
    assert (voice.ACK_DIR / voice._ack_file("Puck", "m", 0).name).exists()


def _no_followup(fake):
    async def send_tool_response(function_responses):
        fake.tool_responses.extend(function_responses)
    return send_tool_response


def test_no_ack_when_he_already_said_ek_second(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_TOOL_ACK="true")
    _ack_setup(monkeypatch)
    fake = FakeSession([[
        _msg(model_turn=_audio(), output_transcription=types.Transcription(text="Haan, dekhta hoon.")),
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fcW2", name="get_weather", args={"city": "Pune"})])),
    ]])
    fake.send_tool_response = _no_followup(fake)
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: fake.tool_responses, timeout=5)
            ws.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: voice.STATS and voice.STATS[-1]["tools"] == 1)
    assert voice.STATS[-1]["acks"] == 0 and voice.STATS[-1]["silent_tools"] == 0


def test_reply_speed_and_style_are_measured(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch)
    voice.STATS.clear()
    fake = FakeSession([])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            ws.send_bytes(LOUD)                     # the user speaks...
            time.sleep(0.35)                        # ...stops, and he answers a moment later
            fake.turns.append([
                _msg(input_transcription=types.Transcription(text="Kya scene hai")),
                _msg(model_turn=_audio(), output_transcription=types.Transcription(text="Certainly! Main aapki madad karunga. Kya chahiye?")),
                _msg(turn_complete=True),
            ])
            done = read_events(ws, lambda e: e["type"] == "turn_done")[-1]
            assert 300 <= done["latency_ms"] < 3000
            ws.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: voice.STATS and voice.STATS[-1]["turns"] == 1)
        s = c.get("/api/voice/stats").json()
    assert s["calls"] == 1 and s["reply_start_ms_p50"] >= 300
    assert s["question_endings_pct"] == 100.0 and s["assistantisms_per_100"] >= 200
    assert s["words_per_reply_median"] == 7


def test_late_big_job_says_what_it_was_about(env, monkeypatch):
    from app import main
    import app.agent as agent
    _gemini_env(monkeypatch, VOICE_TOOL_WAIT_S=1)

    async def slow_turn(conv, text, tenant_id=None, voice=False):
        await asyncio.sleep(1.4)
        return "list ready"

    monkeypatch.setattr(agent, "run_turn", slow_turn)
    fake = FakeSession([[
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="fcL", name="santosh_kaam", args={"request": "Akola wale customers ki list banao"})])),
    ]])
    fake.send_tool_response = _no_followup(fake)
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: any("list ready" in t for t in fake.texts), timeout=6)
            ws.send_text(json.dumps({"type": "end"}))
    note = next(t for t in fake.texts if "list ready" in t)
    assert "Akola wale customers ki list banao" in note and "woh jo aapne kaha tha" in note


def test_stats_are_per_tenant(env):
    voice.STATS.append({"tenant": "someone-else", "call_id": "x", "ended": 1, "turns": 3, "latency_ms": [5000],
                        "words": [10, 10, 10], "question_endings": 0, "assistantisms": 0, "interruptions": 0,
                        "tools": 0, "silent_tools": 0, "acks": 0})
    s = voice.stats_summary("nobody")
    assert s["calls"] == 0 and s["reply_start_ms_p50"] is None and s["silent_tools_pct"] is None


def _cut_off(*after):
    """He starts a sentence, something cuts him off, then `after` happens."""
    return [[
        _msg(model_turn=_audio(), output_transcription=types.Transcription(text="Kal ki meeting chaar baje hai, aur uske baad")),
        _msg(interrupted=True),
        *after,
    ]]


def test_noise_cut_him_off_so_he_finishes_his_point(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_RESUME_AFTER_NOISE_S=0.5)
    voice.STATS.clear()
    fake = FakeSession(_cut_off())
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            assert wait_until(lambda: any("kat gayi" in t for t in fake.texts), timeout=4)
            ws.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: voice.STATS)
        s = c.get("/api/voice/stats").json()
    note = next(t for t in fake.texts if "kat gayi" in t)
    assert "Kal ki meeting chaar baje hai, aur uske baad" in note and "haan, toh" in note
    assert voice.STATS[-1]["interruptions"] == 1 and voice.STATS[-1]["false_stops"] == 1
    assert s["false_stops_per_call"] == 1.0


def test_real_interruption_is_not_treated_as_noise(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_RESUME_AFTER_NOISE_S=0.5)
    voice.STATS.clear()
    fake = FakeSession(_cut_off(_msg(input_transcription=types.Transcription(text="Nahi ruko, paanch baje karo"))))
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "user_text")
            time.sleep(1.0)
            ws.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: voice.STATS)
    assert not any("kat gayi" in t for t in fake.texts)
    assert voice.STATS[-1]["interruptions"] == 1 and voice.STATS[-1]["false_stops"] == 0
