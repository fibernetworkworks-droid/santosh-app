"""Daily-life pack: reminders, phone actions, memory, lists, profile and the morning briefing."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import life, worker
from app.agent.life_tools import (add_calendar_event, create_reminder, list_add, list_done, remember, set_phone_alarm,
                                  set_phone_timer, set_profile)
from app.agent.tools import Ctx, ToolError
from app.db import Conversation, DeviceAction, Event, Message, Reminder, now, session

IST = ZoneInfo("Asia/Kolkata")


def conv_ctx():
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush()
        return Ctx("default", c.id)


def notes(conv):
    with session() as s:
        return s.scalars(select(Message.display).where(Message.conversation_id == conv, Message.in_history.is_(False))).all()


def test_next_due_keeps_local_time():
    fri = datetime(2026, 10, 16, 9, 0, tzinfo=IST).astimezone(timezone.utc)
    assert life.next_due(fri, "daily", IST).astimezone(IST) == datetime(2026, 10, 17, 9, 0, tzinfo=IST)
    assert life.next_due(fri, "weekdays", IST).astimezone(IST) == datetime(2026, 10, 19, 9, 0, tzinfo=IST)   # Monday
    assert life.next_due(fri, "weekly", IST).astimezone(IST).date().isoformat() == "2026-10-23"
    jan31 = datetime(2027, 1, 31, 20, 30, tzinfo=IST).astimezone(timezone.utc)
    assert life.next_due(jan31, "monthly", IST).astimezone(IST) == datetime(2027, 2, 28, 20, 30, tzinfo=IST)
    dec = datetime(2026, 12, 5, 8, 0, tzinfo=IST).astimezone(timezone.utc)
    assert life.next_due(dec, "monthly", IST).astimezone(IST).date().isoformat() == "2027-01-05"
    assert life.next_due(fri, "none", IST) is None


def test_reminder_create_fire_and_repeat(env):
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        asyncio.run(create_reminder(ctx, "old", "2020-01-01T09:00"))
    soon = (datetime.now(IST) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    one = asyncio.run(create_reminder(ctx, "Dawai lena", soon))
    daily = asyncio.run(create_reminder(ctx, "Paani peena", soon, "daily"))
    assert one["status"] == "active" and "Dawai" in one["text"]
    # make both due now
    with session() as s:
        for rid in (one["id"], daily["id"]):
            s.get(Reminder, rid).due_at = now() - timedelta(seconds=5)
    asyncio.run(worker.fire_reminders())
    with session() as s:
        assert s.get(Reminder, one["id"]).status == "done"
        d = s.get(Reminder, daily["id"])
        assert d.status == "active" and d.fired_count == 1
        from app.db import as_utc
        assert as_utc(d.due_at) > now() + timedelta(hours=23)
    n = notes(ctx.conversation_id)
    assert any("Dawai lena" in x for x in n) and any("Paani peena" in x for x in n)
    asyncio.run(worker.fire_reminders())     # nothing fires twice
    assert len(notes(ctx.conversation_id)) == len(n)


def test_phone_actions_and_results(env, monkeypatch):
    monkeypatch.setattr(env["settings"], "api_key", "")
    ctx = conv_ctx()
    a = asyncio.run(set_phone_alarm(ctx, "06:30", "Uthna hai", ["mon", "tue", "xyz"]))
    t = asyncio.run(set_phone_timer(ctx, 10, "Chai"))
    start = (datetime.now(IST) + timedelta(days=1)).replace(hour=16, minute=0).strftime("%Y-%m-%dT%H:%M")
    c = asyncio.run(add_calendar_event(ctx, "Doctor appointment", start, location="Ruby Hall", remind_minutes_before=30))
    with pytest.raises(ToolError):
        asyncio.run(set_phone_alarm(ctx, "25:99"))
    with session() as s:
        act = s.get(DeviceAction, a["action_id"])
        assert act.payload == {"hour": 6, "minute": 30, "label": "Uthna hai", "days": ["mon", "tue"]}
        assert s.get(DeviceAction, t["action_id"]).payload["seconds"] == 600
        cal = s.get(DeviceAction, c["action_id"]).payload
        assert cal["end_ms"] - cal["start_ms"] == 3600 * 1000
        assert s.scalars(select(Reminder).where(Reminder.conversation_id == ctx.conversation_id)).first() is not None
        kinds = s.scalars(select(Event.kind).where(Event.conversation_id == ctx.conversation_id)).all()
        assert kinds.count("device_action") == 3
    from app.main import app
    with TestClient(app) as cl:
        pend = cl.get("/api/device-actions/pending").json()["actions"]
        assert {p["id"] for p in pend} >= {a["action_id"], t["action_id"], c["action_id"]}
        assert cl.post(f"/api/device-actions/{a['action_id']}/result", json={"ok": True}).json()["status"] == "done"
        assert cl.post(f"/api/device-actions/{t['action_id']}/result", json={"ok": False, "detail": "no clock app"}).json()["status"] == "failed"
    assert any("nahi ho paya" in x for x in notes(ctx.conversation_id))
    # the calendar action was never confirmed: it expires and the user is told
    with session() as s:
        s.get(DeviceAction, c["action_id"]).created_at = now() - timedelta(minutes=20)
    worker.expire_device_actions()
    with session() as s:
        assert s.get(DeviceAction, c["action_id"]).status == "expired"
    assert any("phone par nahi pahuncha" in x for x in notes(ctx.conversation_id))


def test_memory_lists_profile_and_prompt(env):
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        asyncio.run(remember(ctx, "Mera bank OTP 445566 hai"))
    asyncio.run(remember(ctx, "Car insurance 12 March ko khatam hota hai"))
    asyncio.run(set_profile(ctx, name="Meghana", city="Akola", briefing_time="07:30"))
    block = life.context_block("default")
    assert "Meghana" in block and "Akola" in block and "Car insurance" in block and "07:30" in block

    r = asyncio.run(list_add(ctx, "Shopping", ["Doodh", "Bread", "doodh"]))
    assert r["items"] == ["Doodh", "Bread"]
    r = asyncio.run(list_done(ctx, "shopping", ["doodh"]))
    assert r["ticked"] == ["Doodh"] and r["remaining"] == ["Bread"]
    with pytest.raises(ToolError):
        asyncio.run(set_profile(ctx, briefing_time="7 baje"))


def test_morning_briefing_once_a_day(env, monkeypatch):
    ctx = conv_ctx()
    asyncio.run(list_add(ctx, "todo", ["GST file karna"]))
    soon = (datetime.now(IST) + timedelta(minutes=30))
    if soon.date() == datetime.now(IST).date():
        asyncio.run(create_reminder(ctx, "Client call", soon.strftime("%Y-%m-%dT%H:%M")))
    t = (datetime.now(IST) - timedelta(minutes=1)).strftime("%H:%M")
    asyncio.run(set_profile(ctx, name="Meghana Ingle", briefing_time=t))   # no city -> weather skipped, no network

    async def no_weather(*a, **k):
        raise AssertionError("weather should not be called without a city")
    monkeypatch.setattr(life, "weather_for", no_weather)
    asyncio.run(worker.morning_briefings())
    asyncio.run(worker.morning_briefings())
    briefs = [x for x in notes(ctx.conversation_id) if x.startswith("Suprabhat")]
    assert len(briefs) == 1
    assert "Meghana!" in briefs[0] and "todo mein 1" in briefs[0]


def test_weather_tool_uses_profile_city(env, monkeypatch):
    ctx = conv_ctx()
    asyncio.run(set_profile(ctx, city="Pune"))
    calls = []

    async def fake_geo(city):
        calls.append(city); return 18.52, 73.86, "Pune, Maharashtra"

    async def fake_weather(lat, lon, tz="Asia/Kolkata"):
        return {"now_c": 29.4, "now": "halke baadal", "today_min_c": 21, "today_max_c": 31, "rain_chance_pct": 60}
    monkeypatch.setattr(life, "geocode", fake_geo)
    monkeypatch.setattr(life, "weather", fake_weather)
    from app.agent.life_tools import get_weather
    w = asyncio.run(get_weather(ctx))
    assert w["place"] == "Pune, Maharashtra" and calls == ["Pune"]
    asyncio.run(get_weather(ctx))
    assert calls == ["Pune"]          # coordinates cached after the first lookup
    text = asyncio.run(life.compose_briefing("default"))
    assert "Pune" in text and "chhata" in text
