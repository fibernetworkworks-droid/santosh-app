"""v0.142 Doosre se baat: talk that is not for Hoola (her phone call, people in the room) is never answered."""
import json
import time

from fastapi.testclient import TestClient
from google.genai import types

from app import sidetalk
from app.db import Message, session
from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, read_events

N = ["Santosh", "Hoola"]


class QuietSession(FakeSession):
    """A fake Gemini that only records tool answers (no automatic spoken confirmation)."""

    async def send_tool_response(self, function_responses):
        self.tool_responses.extend(function_responses)


def _audio(n=60, v=b"\x03\x00"):
    return types.Part(inline_data=types.Blob(data=v * n, mime_type="audio/pcm;rate=24000"))


def _notes(fake):
    return [p.text for t in fake.client_content for p in (t.parts or [])] + list(fake.texts)


def _wait(pred, s=5.0):
    end = time.time() + s
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return False


def _read(ws, stop, limit=80):
    """Events + count of audio frames until stop(event)."""
    events, frames = [], 0
    for _ in range(limit):
        m = ws.receive()
        if m.get("bytes"):
            frames += 1
        elif m.get("text"):
            ev = json.loads(m["text"])
            events.append(ev)
            if stop(ev):
                break
    return events, frames


def test_name_calls_and_hold_words():
    assert sidetalk.called("Santosh, kal ka mausam batao", N)
    assert sidetalk.called("अरे संतोष सुनो", N)                # Devanagari, spelt like the transcript does
    assert sidetalk.called("Santhosh ek kaam karo", N)          # close spelling
    assert sidetalk.called("kal mausam kaisa hai Santosh", N)    # the name at the end
    assert sidetalk.called("Hoola wapas aao", N)
    assert not sidetalk.called("Santosh ko bolti hoon kal", N)   # talking ABOUT Hoola to someone else
    assert not sidetalk.called("ye Hoola ne kaha tha", N)
    assert not sidetalk.called("main Santosh se poochti hoon", N)
    assert not sidetalk.called("bhai woh Santosh wala kaam kal karna hai bahut zaroori hai", N)
    assert not sidetalk.called("haan bhai main aa raha hoon", N)
    t = "haan bhai kal milte hain. Santosh, ab reminder lagao"
    assert t[sidetalk.call_start(t, N):].startswith("Santosh")
    for s in ["ek minute main kisi se baat kar rahi hoon", "chup raho", "phone aa gaya", "चुप रहो", "मत बोलो",
              "hold karo", "main dost se baat kar rahi hoon", "tum mat bolo abhi", "one sec I'm talking to my mom"]:
        assert sidetalk.wants_hold(s), s
    for s in ["ruko", "kal ka mausam batao", "bhai ko phone karna hai", "phone ki battery kitni hai"]:
        assert not sidetalk.wants_hold(s), s


def test_persona_and_tool_know_about_side_talk(env, monkeypatch):
    from app import voice
    _gemini_env(monkeypatch)
    p = voice.persona_prompt("Meera", "f")
    assert "Who is she talking to?" in p and "side_talk" in p and p.rstrip().endswith("{context}")
    assert "Meera" in p and "ye Santosh" not in p
    assert any(t["name"] == "side_talk" for t in voice._tool_specs())
    _gemini_env(monkeypatch, VOICE_SIDE_TALK="false")
    assert not any(t["name"] == "side_talk" for t in voice._tool_specs())
    assert "Who is she talking to?" not in voice.persona_prompt("Meera", "f")


def test_she_talks_to_someone_else_then_calls_hoola_back(env, monkeypatch):
    """'Ek minute, main kisi se baat kar rahi hoon' -> hold: the side talk is not shown, not saved, no reply is played,
    no tool runs. 'Santosh, ...' -> back, and that request is answered and saved."""
    from app import main, voice
    _gemini_env(monkeypatch)
    held = [
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Ek minute, main kisi se baat kar rahi hoon")),
        _msg(model_turn=types.Content(parts=[_audio()]), output_transcription=types.Transcription(text="Theek hai")),
        _msg(turn_complete=True),
        _msg(input_transcription=types.Transcription(text="haan bhai kal paise bhej dena pakka")),
        _msg(model_turn=types.Content(parts=[_audio()]), output_transcription=types.Transcription(text="Theek hai, bhej deta hoon")),
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="h1", name="create_reminder", args={"text": "paise bhejne hain", "when": "kal"})])),
        _msg(turn_complete=True),
    ]
    back = [
        _msg(input_transcription=types.Transcription(text="Santosh, kal subah saat baje ka alarm laga do")),
        _msg(model_turn=types.Content(parts=[_audio(80, b"\x05\x00")]),
             output_transcription=types.Transcription(text="Haan, saat baje ka alarm laga deta hoon.")),
        _msg(turn_complete=True),
    ]
    fake = QuietSession([held])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&lang=hi-IN") as ws:
            ev1, frames1 = _read(ws, lambda e: e["type"] == "hold" and e["on"])
            assert ev1[-1]["reason"] == "asked" and ev1[-1]["say"]
            assert _wait(lambda: fake.tool_responses), "the held tool call must be answered (refused)"
            fake.turns.append(back)
            ev2, frames2 = _read(ws, lambda e: e["type"] == "turn_done")
            ws.send_text(json.dumps({"type": "end"}))
        stats = c.get("/api/voice/stats").json()
    shown = json.dumps(ev1 + ev2, ensure_ascii=False)
    assert "paise" not in shown and "bhej deta" not in shown       # side talk never shown, his answer to it never shown
    assert frames1 == 0                                             # nothing he said to the side talk was played
    assert frames2 >= 1                                             # the answer to her named request was
    off = [e for e in ev2 if e["type"] == "hold" and not e["on"]]
    assert off and off[0]["by"] == "name"
    assert any(e["type"] == "user_text" and e["text"].startswith("Santosh") for e in ev2)
    r = fake.tool_responses[0]
    assert r.name == "create_reminder" and "on_hold" in r.response["error"]
    notes = _notes(fake)
    assert any(n.startswith("(HOLD:") for n in notes) and any(n.startswith("(HOLD OVER") for n in notes)
    with session() as s:
        saved = json.dumps([m.content for m in s.query(Message).filter(Message.conversation_id == conv).all()], ensure_ascii=False)
    assert "paise" not in saved and "kisi se baat" not in saved and "saat baje ka alarm" in saved
    call = voice.STATS[-1]
    assert call["holds"] == 1 and call["hold_reasons"] == {"asked": 1} and call["released_by"] == {"name": 1}
    assert call["held_turns"] == 2 and call["dropped_replies"] == 2 and call["hold_refused_tools"] == 1
    assert stats["calls_with_hold"] >= 1 and stats["dropped_replies"] >= 2


def test_her_phone_call_holds_and_sends_no_mic(env, monkeypatch):
    """The phone says she is on another call: not one mic chunk reaches Gemini, notes wait, the call ends -> back."""
    from app import main, voice
    _gemini_env(monkeypatch)
    fake = QuietSession([[types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete())]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            ws.send_bytes(b"\x10\x00" * 640)
            assert _wait(lambda: len(fake.audio_in) == 1)
            ws.send_text(json.dumps({"type": "hold", "on": True, "reason": "phone_call"}))
            on = read_events(ws, lambda e: e["type"] == "hold")[-1]
            assert on["on"] and on["reason"] == "phone_call"
            for _ in range(5):
                ws.send_bytes(b"\x20\x00" * 640)
            voice.inject(conv, "(Woh bada kaam ho gaya: bill bhar diya.)")    # a job finishes during her call
            ws.send_text(json.dumps({"type": "ping"}))
            read_events(ws, lambda e: e["type"] == "pong")
            assert len(fake.audio_in) == 1                                     # her phone call never went to Gemini
            assert not any("bill bhar diya" in t for t in fake.texts)          # the note waits for her
            ws.send_text(json.dumps({"type": "hold", "on": False, "reason": "phone_call"}))
            off = read_events(ws, lambda e: e["type"] == "hold")[-1]
            assert not off["on"] and off["by"] == "phone"
            assert _wait(lambda: any("bill bhar diya" in t for t in fake.texts))
            ws.send_bytes(b"\x30\x00" * 640)
            assert _wait(lambda: len(fake.audio_in) == 2)
            ws.send_text(json.dumps({"type": "end"}))
    call = voice.STATS[-1]
    assert call["hold_reasons"] == {"phone_call": 1} and call["released_by"] == {"phone": 1}
    notes = _notes(fake)
    assert any("another phone call" in n for n in notes) and any("phone call has ended" in n for n in notes)


def test_gemini_notices_side_talk_and_button_brings_it_back(env, monkeypatch):
    """Gemini calls side_talk (two voices talking to each other) -> hold; 'Wapas aao' button -> back."""
    from app import main, voice
    _gemini_env(monkeypatch)
    fake = QuietSession([[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="mummy khana ban gaya kya")),
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
            types.FunctionCall(id="s1", name="side_talk", args={"why": "she is talking to her mother"})])),
    ]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            on = read_events(ws, lambda e: e["type"] == "hold")[-1]
            assert on["on"] and on["reason"] == "model"
            ws.send_text(json.dumps({"type": "hold", "on": False}))
            off = read_events(ws, lambda e: e["type"] == "hold")[-1]
            assert not off["on"] and off["by"] == "button"
            ws.send_text(json.dumps({"type": "end"}))
    assert fake.tool_responses[0].name == "side_talk" and fake.tool_responses[0].response["result"]["status"] == "on_hold"
    assert voice.STATS[-1]["hold_reasons"] == {"model": 1}


def test_a_hold_that_never_ends_closes_the_call(env, monkeypatch):
    from app import main, voice
    _gemini_env(monkeypatch, VOICE_HOLD_MAX_S=1)
    fake = QuietSession([[types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete())]])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            ws.send_text(json.dumps({"type": "hold", "on": True}))
            err = read_events(ws, lambda e: e["type"] == "error")[-1]
    assert err["code"] == "gone"
    assert voice.STATS[-1].get("hold_ended_call") and voice.STATS[-1]["hold_reasons"] == {"button": 1}
