"""v0.621 YAAD KI GHANTI (owner: "CHECK THE ISSUE REMINDER NOT WORKING VIA VOICE").

Found: with no call live, a due reminder was a chat line + a notification only - Hoola never SAID it and never rang.
Now: no live call -> the server rings her phone (the GHANTI voice_ring) and the call it starts OPENS with the reminder;
a live call (any chat of hers) hears it at the next pause. Her own reminder ignores the job-ring quiet hours.
"""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from fastapi.testclient import TestClient

from app import voice
from tests.test_voice import FakeSession, _connector, _gemini_env, read_events, wait_until

T = "default"


def _due(conv: str, text: str):
    from app.db import Reminder, now, session
    with session() as s:
        s.add(Reminder(tenant_id=T, conversation_id=conv, text=text, due_at=now() - timedelta(seconds=2)))


def _conv(cid: str = "conv_g") -> str:
    from app.db import Conversation, session
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


def test_no_live_call_rings_her_and_the_call_opens_with_the_reminder(env, monkeypatch):
    from app import worker, yaad
    from app.events import bus
    seen = []
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload, **k: (seen.append((kind, payload)), real(conv, kind, payload, **k))[1])
    c = _conv()
    _due(c, "BP ki dawai lo")
    asyncio.run(worker.fire_reminders())
    rings = [p for k, p in seen if k == "voice_ring"]
    assert len(rings) == 1 and rings[0]["reminder"] is True and rings[0]["conv"] == c
    note = yaad.take_call_followup(c)
    assert "REMINDER" in note and "BP ki dawai" in note


def test_a_live_call_hears_it_and_no_ring_goes_out(env, monkeypatch):
    from app import main, worker
    from app.events import bus
    _gemini_env(monkeypatch, VOICE_PARK="true", VOICE_PARK_AFTER_S=60)
    sessions = [FakeSession([]) for _ in range(3)]
    _connector(monkeypatch, *sessions)
    kinds = []
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload, **k: (kinds.append(kind), real(conv, kind, payload, **k))[1])
    with TestClient(main.app) as cl:
        conv = cl.post("/api/conversations").json()["id"]
        with cl.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            _due(conv, "paani piyo")
            loop = next(iter(voice.ACTIVE[conv]))[0]
            asyncio.run_coroutine_threadsafe(worker.fire_reminders(), loop).result(5)
            assert wait_until(lambda: any("paani piyo" in t and "Reminder" in t for t in sessions[0].texts), timeout=40)
            assert "voice_ring" not in kinds and voice.tenant_live(T)
            ws.send_text(json.dumps({"type": "end"}))


def test_the_rung_call_says_the_reminder_first(env, monkeypatch):
    from app import main, yaad
    _gemini_env(monkeypatch)
    fake = FakeSession([])
    _connector(monkeypatch, fake)
    with TestClient(main.app) as cl:
        conv = cl.post("/api/conversations").json()["id"]
        yaad.note_call_followup(conv, T, "REMINDER jo usne khud lagaya tha, abhi due hai: bijli ka bill bharo.")
        with cl.websocket_connect(f"/api/voice/ws?conv={conv}") as ws:
            read_events(ws, lambda e: e["type"] == "ready")
            assert wait_until(lambda: any("bijli ka bill" in t for t in fake.texts))
            ws.send_text(json.dumps({"type": "end"}))


def test_her_reminder_rings_inside_quiet_hours_a_job_does_not(env, monkeypatch):
    from app import push
    from app.config import get_settings
    monkeypatch.setenv("VOICE_RING_QUIET", "0-24")        # every hour is quiet
    get_settings.cache_clear()
    push._REM_DAY.clear()
    push._RING_DAY.clear()
    assert push._ring_allowed(T, "c1") is False                       # a job's news waits for morning
    assert push._ring_allowed(T, "c1", reminder=True) is True         # the reminder she set rings
    monkeypatch.setenv("VOICE_RING_REMINDER_MAX_DAY", "1")
    get_settings.cache_clear()
    assert push._ring_allowed(T, "c1", reminder=True) is False        # the sanity cap
    monkeypatch.setenv("VOICE_RING_REMINDERS", "false")
    get_settings.cache_clear()


def test_switch_off_keeps_the_old_quiet_reminder(env, monkeypatch):
    from app import worker, yaad
    from app.config import get_settings
    monkeypatch.setenv("VOICE_RING_REMINDERS", "false")
    get_settings.cache_clear()
    c = _conv("conv_off")
    _due(c, "chai")
    asyncio.run(worker.fire_reminders())
    assert yaad.take_call_followup(c) == ""


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.812.0"
