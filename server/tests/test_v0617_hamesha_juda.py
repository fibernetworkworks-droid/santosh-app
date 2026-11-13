"""v0.617 HAMESHA JUDA - the voice call stays connected until SHE hangs up, and costs nothing while quiet
(owner: "VOICE CALL IS SOUL OF OUR PRODUCT ... ONCE CALL CONNECTED IT REMAINS CONNECTED TILL USER DONT DISCONNECT
IT. VOICE CALL WILL GIVE REPLY WHEN WORK DONE, GIVE REMINDERS ... 24/7" -> "START").

Gemini Live bills every second of audio sent, silence included (~Rs 26 an hour per open call). So a quiet call
PARKS: Gemini closes, the call to Hoola stays live; her voice, a typed line, news or a reminder brings Gemini back
on the same memory (resumption handle). A long hold and a lost phone park instead of ending the call. Reminders,
the morning briefing and routine results are SPOKEN on a live call. Real voice (OpenAI) moves sessions only at a
pause. The phone re-dials by itself after a server update.
"""
from __future__ import annotations

import asyncio
import json
import struct
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import voice
from tests.test_voice import FakeSession, _connector, _gemini_env, read_events, wait_until

REPO = Path(__file__).resolve().parents[2]
LOUD = struct.pack("<320h", *([9000, -9000] * 160))      # a spoken chunk (peak far above the 1200 gate)


def _counting(monkeypatch):
    sessions = [FakeSession([]) for _ in range(6)]
    _connector(monkeypatch, *sessions)
    return sessions


def _only_call():
    assert wait_until(lambda: len(voice.CALLS) == 1)
    return next(iter(voice.CALLS.values()))


def test_a_quiet_call_parks_and_her_voice_brings_hoola_back(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_PARK="true", VOICE_PARK_AFTER_S=1)
    sessions = _counting(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            call = _only_call()
            evs = read_events(ws, lambda e: e.get("state") == "resting")
            assert evs[-1] == {"type": "status", "state": "resting"}
            assert call.parked and not call.closed.is_set() and call.stats["park_by"] == {"quiet": 1}
            ws.send_bytes(LOUD)                                    # she speaks: Gemini comes back
            read_events(ws, lambda e: e.get("state") == "live")
            assert wait_until(lambda: LOUD in sessions[1].audio_in)
            assert call.stats["wake_by"] == {"voice": 1} and not call.parked
            ws.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: not voice.CALLS)
    assert sessions[0].audio_in == [] or LOUD not in sessions[0].audio_in


def test_news_or_a_typed_line_wakes_a_parked_call(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_PARK="true", VOICE_PARK_AFTER_S=1)
    sessions = _counting(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            call = _only_call()
            read_events(ws, lambda e: e.get("state") == "resting")
            voice.inject(conv, "Report taiyaar hai")                # a finished job's news
            read_events(ws, lambda e: e.get("state") == "live")
            assert wait_until(lambda: any("Report taiyaar" in t for t in sessions[1].texts))
            read_events(ws, lambda e: e.get("state") == "resting")   # quiet again: parks again
            ws.send_text(json.dumps({"type": "text", "text": "kal ka plan batao"}))
            read_events(ws, lambda e: e.get("state") == "live")
            assert wait_until(lambda: any("kal ka plan" in t for t in sessions[2].texts))
            assert call.stats["wake_by"] == {"news": 2} and call.stats["parks"] >= 2
            ws.send_text(json.dumps({"type": "end"}))


def test_a_lost_phone_parks_and_the_call_waits_far_past_the_old_25_s(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_PARK="true", VOICE_PARK_AFTER_S=60, VOICE_RESUME_GRACE_S=1, VOICE_PARK_GRACE_S=30)
    _counting(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            call_id = read_events(ws, lambda e: e["type"] == "ready")[-1]["call_id"]
        call = voice.CALLS[call_id]
        assert wait_until(lambda: call.parked, timeout=8)            # phone away: Gemini closed at once
        time.sleep(1.5)                                             # the old 1 s grace would have ended it
        assert call_id in voice.CALLS and call.stats["park_by"] == {"phone_away": 1}
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&resume={call_id}") as ws2:
            assert read_events(ws2, lambda e: e["type"] == "ready")[-1]["resumed"] is True
            ws2.send_text(json.dumps({"type": "end"}))
        assert wait_until(lambda: call_id not in voice.CALLS)


def test_a_long_hold_parks_instead_of_ending_and_wapas_brings_it_back(env, monkeypatch):
    from app import main
    _gemini_env(monkeypatch, VOICE_PARK="true", VOICE_PARK_AFTER_S=60, VOICE_HOLD_MAX_S=1)
    sessions = _counting(monkeypatch)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            call = _only_call()
            ws.send_text(json.dumps({"type": "hold", "on": True, "reason": "button"}))
            read_events(ws, lambda e: e.get("state") == "resting")
            assert not call.closed.is_set() and call.stats["hold_parked"] is True
            ws.send_bytes(LOUD)                                     # side talk on a held line does NOT wake it
            time.sleep(0.6)
            assert call.parked
            ws.send_text(json.dumps({"type": "hold", "on": False, "reason": "button"}))
            read_events(ws, lambda e: e.get("state") == "live")
            assert call.stats["wake_by"] == {"hold_over": 1}
            ws.send_bytes(LOUD)                                     # back on a fresh Gemini session
            assert wait_until(lambda: LOUD in sessions[1].audio_in)
            ws.send_text(json.dumps({"type": "end"}))


def test_reminder_briefing_and_routine_result_are_spoken_on_a_live_call(env, monkeypatch):
    from datetime import timedelta
    from app import worker
    from app.db import Conversation, Reminder, now, session
    told = []
    monkeypatch.setattr(voice, "inject", lambda conv, note: told.append((conv, note)) or 1)
    monkeypatch.setitem(voice.ACTIVE, "conv_r", [object()])
    voice._CARD_TOLD.clear()
    with session() as s:
        s.add(Conversation(id="conv_r", tenant_id="default"))
        s.add(Reminder(tenant_id="default", conversation_id="conv_r", text="BP ki dawai lo",
                       due_at=now() - timedelta(seconds=5)))
    asyncio.run(worker.fire_reminders())
    assert len(told) == 1 and "Reminder: it is due right now" in told[0][1] and "BP ki dawai" in told[0][1]
    asyncio.run(worker.fire_reminders())                            # fired once, told once
    assert len(told) == 1
    voice.card_news("conv_r", "briefing", {"text": "Aaj 2 meeting, baarish ka chance", "date": "2026-11-06"})
    voice.card_news("conv_r", "routine_done", {"id": "r1", "title": "GST check", "text": "Sab theek, 0 notice"})
    assert "morning briefing" in told[1][1] and "GST check" in told[2][1] and len(told) == 3
    assert "routine_done" in (REPO / "server" / "app" / "worker.py").read_text()


def test_real_voice_moves_its_session_only_at_a_pause():
    from app.voice_openai import OpenAICall
    assert OpenAICall.CAN_PARK is False and voice.Call.CAN_PARK is True
    t = time.monotonic()
    talking = SimpleNamespace(MOVE_WAIT_S=0.6, stats={}, _last_voice_at=t + 5, _last_model_audio=t + 5,
                              user_buf="", reply_buf="aaj ka", _turn_audio=True)
    t0 = time.monotonic()
    asyncio.run(OpenAICall._session_limit(talking, 0))
    assert time.monotonic() - t0 >= 0.5 and talking.stats == {"move_forced": 1}   # waited, then had to move
    quiet = SimpleNamespace(MOVE_WAIT_S=5, stats={}, _last_voice_at=0.0, _last_model_audio=0.0,
                            user_buf="", reply_buf="", _turn_audio=False)
    t0 = time.monotonic()
    asyncio.run(OpenAICall._session_limit(quiet, 0))
    assert time.monotonic() - t0 < 1 and quiet.stats == {}


def test_phone_redials_after_a_server_update_and_keeps_trying():
    lv = (REPO / "lib" / "live_voice.dart").read_text()
    assert "_restartWindow" in lv and "_restarting" in lv and "Duration(minutes: 14)" in lv
    assert "resume: _restarting ? null : _callId" in lv
    cs = (REPO / "lib" / "call_session.dart").read_text()
    assert "'resting' => null" in cs and "'restarting'" in cs
    src = (REPO / "server" / "app" / "voice.py").read_text()
    assert "reconnect by itself in a minute" in src


def test_settings_defaults():
    from app.config import Settings
    s = Settings()
    assert s.voice_park is True and s.voice_park_after_s == 90 and s.voice_park_grace_s == 900


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.879.0"
