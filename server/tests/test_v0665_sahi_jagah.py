"""v0.667 SAHI JAGAH (owner: "GO WAVE 7" of the second deep audit - every thing in its right place, the same everywhere).

24 a WhatsApp / Telegram chat never becomes "the chat she is in"
25 a reminder / routine / briefing set on a voice call belongs to the chat the call came from
26 a reminder / routine in a deleted chat moves to the chat she is in
27 a medicine / bill / birthday reminder is spoken on a call, rings, and keeps its day of the month
28 a monthly reminder keeps its own day (31 Jan -> 28 Feb -> 31 Mar)
29 a background report holding the chat never swallows her new message
30 "server dobara chalu hua" is said only after a real restart
31 a long text inside a tool result is shortened in place - every key after it survives
"""
from __future__ import annotations

import asyncio
import inspect
import json
import types
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import Conversation, session

T = "default"
IST = ZoneInfo("Asia/Kolkata")


def _chat(cid: str, **kw) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, **kw))
    return cid


# ---------------------------------------------------------------- 24 outside channels
def test_a_channel_chat_is_never_the_current_chat(env):
    from app import bahar, convs
    _chat("app1")
    _chat("tg1")
    bahar.ensure_table()
    with session() as s:
        s.add(bahar.BaharLink(tenant_id=T, channel="telegram", hook="hk1", status="linked", conversation_id="tg1"))
    convs._CACHE.clear()
    convs.mark(T, "app1", "message")
    convs._CACHE.clear()
    convs.mark(T, "tg1", "message")             # an old path marking it is refused
    assert convs.current(T) == "app1"
    src = inspect.getsource(bahar)
    assert 'convs.mark(tenant, conv, "message")' not in src


# ---------------------------------------------------------------- 25 set on a call
def test_a_reminder_and_routine_set_on_a_call_belong_to_the_chat(env):
    from app.agent import life_tools
    from app.db import Reminder, Routine
    _chat("home1")
    _chat("call1", kind="call", origin_conv="home1")
    from app import callconv
    callconv._KIND.pop("call1", None) if hasattr(callconv, "_KIND") else None
    ctx = types.SimpleNamespace(tenant_id=T, conversation_id="call1")
    assert life_tools._home(ctx) == "home1"
    src = inspect.getsource(life_tools)
    assert "conversation_id=ctx.conversation_id, text=text[:500]" not in src
    assert "p.briefing_conversation_id = ctx.conversation_id" not in src


# ---------------------------------------------------------------- 26 deleted chat
def test_a_reminder_in_a_deleted_chat_speaks_in_her_current_chat(env, monkeypatch):
    from app import convs, worker
    from app.db import Reminder
    import app.events as ev
    _chat("now1")
    _chat("gone1", deleted=True)
    convs._CACHE.clear()
    convs.mark(T, "now1", "message")
    with session() as s:
        s.add(Reminder(tenant_id=T, conversation_id="gone1", text="Dawai", due_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    said = []
    monkeypatch.setattr(ev, "notify", lambda c, t, *a, **k: said.append(c))
    monkeypatch.setattr(worker, "_ring_for_reminder", lambda *a: None)
    asyncio.run(worker.fire_reminders())
    assert said == ["now1"]


# ---------------------------------------------------------------- 27 bazar reminders
def test_a_bazar_reminder_is_spoken_rings_and_keeps_its_day(env, monkeypatch):
    from app.bazar import service as bz
    from app.bazar.db import Reminder as BzReminder
    from app import worker, convs
    import app.bazar.service as bzs
    _chat("bz1")
    convs._CACHE.clear()
    convs.mark(T, "bz1", "message")
    with session() as s:
        bz.ensure_user(s, T)
        s.add(BzReminder(user_id=T, kind="bill", text="Bijli ka bill", repeat="monthly",
                         due_at=datetime(2026, 10, 31, 4, 30) if datetime.utcnow() > datetime(2026, 10, 31, 4, 31)
                         else datetime.utcnow() - timedelta(minutes=1)))
    rang, events = [], []
    monkeypatch.setattr(bzs, "notify", lambda c, t, *a, **k: None)
    monkeypatch.setattr(worker, "_ring_for_reminder", lambda *a: rang.append(a))
    monkeypatch.setattr(worker, "_quiet_now", lambda t: False)
    real = bzs.__dict__.get("bus")
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda c, k, p: events.append(k))
    assert bz.fire_due_reminders() == 1
    assert "reminder" in events and len(rang) == 1
    with session() as s:
        r = s.scalars(select(BzReminder).where(BzReminder.user_id == T)).first()
        assert r.due_at.day in (30, 31) and (r.meta or {}).get("day") == 31


# ---------------------------------------------------------------- 28 monthly day
def test_a_monthly_repeat_keeps_its_own_day():
    from app import life
    d = datetime(2026, 1, 31, 4, 0, tzinfo=timezone.utc)            # 31 Jan 09:30 IST
    a = life.anchor_of(d, "monthly", IST)
    feb = life.next_due(d, "monthly", IST, a)
    mar = life.next_due(feb, "monthly", IST, a)
    assert (a, feb.astimezone(IST).day, mar.astimezone(IST).day) == (31, 28, 31)
    assert life.next_due(feb, "monthly", IST).astimezone(IST).day == 28     # the old drift without the anchor
    assert life.anchor_of(d, "daily", IST) is None


# ---------------------------------------------------------------- 29 her message vs a background turn
def test_a_wake_turn_holding_the_chat_never_swallows_her_message(env, monkeypatch):
    from app.agent import santosh, quick
    _chat("w1")
    asked = []

    async def fake_quick(*a, **k):
        asked.append(1)
        return {"text": "x", "queued": False}
    monkeypatch.setattr(quick, "answer", fake_quick)

    async def go():
        await santosh._locks["w1"].acquire()
        santosh._HOLDER["w1"] = "wake"
        her = asyncio.create_task(santosh.run_turn("w1", "naya kaam: report bhejo", tenant_id=T))
        await asyncio.sleep(0.3)
        assert not her.done()                    # she waits her turn behind the report, nothing answered early
        her.cancel()
        santosh._HOLDER.pop("w1", None)
        santosh._locks["w1"].release()
    asyncio.run(go())
    assert asked == []


# ---------------------------------------------------------------- 30 restart wording
def test_the_recovery_note_says_restart_only_after_one():
    from app.agent import goal
    src = inspect.getsource(goal.recover_tick)
    assert "upd < _BOOT_AT" in src and "kuch der se ruka tha" in src


# ---------------------------------------------------------------- 31 long strings
def test_a_long_body_keeps_every_key_after_it():
    from app.agent.santosh import _short
    o = {"text": "x" * 20000, "url": "https://a.b/c", "next_page": "p2", "id": "m1", "error": ""}
    out = _short(o, 6000)
    j = json.loads(out)
    assert j["url"] == "https://a.b/c" and j["next_page"] == "p2" and j["id"] == "m1"
    assert "more characters cut" in j["text"] and len(out) <= 6000
