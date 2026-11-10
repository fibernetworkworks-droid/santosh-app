"""v0.666 KAAM EK BAAR (owner: "GO WAVE 6" of the second deep audit - work never done twice, never lost).

15 the late-reminder quiet hours really work (her time zone was read wrong, so it never did)
16 a timed-out tool is said to be maybe still running - never "try another way" for a send
17 a send the phone retries after a restart runs once (the inbox remembers it, not memory)
18 a routine rides the turn inbox (a restart re-runs it as a routine)
19 Dobara, an edit and a form answer ride the turn inbox
20 a reply given while another turn holds the chat stays out of the model's history
21 kaam_status action=stop never runs in parallel
22 a channel reply is marked sent only after it really went
23 a reminder is advanced before it is said, and said once
"""
from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import Conversation, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


# ---------------------------------------------------------------- 15 her time zone
def test_quiet_hours_and_the_late_time_really_read_her_zone(env, monkeypatch):
    from app import worker
    from zoneinfo import ZoneInfo
    due = datetime(2026, 11, 7, 16, 0, tzinfo=timezone.utc)                       # 21:30 IST
    assert worker._local_hhmm(T, due) == "9:30 PM"
    h = datetime.now(ZoneInfo("Asia/Kolkata")).hour
    assert worker._quiet_now(T) == (h >= 22 or h < 8)


# ---------------------------------------------------------------- 16 timeout wording
def test_a_timed_out_tool_is_said_to_be_maybe_still_running():
    from app.agent import santosh
    src = santosh.turn_loop_source()
    assert "MAY STILL BE" in src and "NEVER repeat a send" in src
    assert "try a lighter way or another tool, or hand the" not in src


# ---------------------------------------------------------------- 17 send retried across a restart
def test_a_retried_send_is_known_from_the_inbox(env):
    from app import turn_inbox
    _chat("t1")
    assert not turn_inbox.seen(T, "t1", "cid-1")
    turn_inbox.accept(T, "t1", "Sharma ji ko mail bhejo", False, "", "cid-1")
    assert turn_inbox.seen(T, "t1", "cid-1")                 # a new process (empty memory) still knows it
    assert not turn_inbox.seen(T, "t1", "cid-2") and not turn_inbox.seen(T, "t1", "")
    from app import main
    src = inspect.getsource(main.post_message)
    assert "_ti0.seen" in src


# ---------------------------------------------------------------- 18 routines ride the inbox
def test_a_routine_rides_the_inbox_and_reruns_as_a_routine(env, monkeypatch):
    from app import turn_inbox, worker
    from app.agent import santosh
    from app.db import Routine
    from app.turn_inbox import TurnInbox
    _chat("r1")
    with session() as s:
        s.add(Routine(tenant_id=T, conversation_id="r1", title="subah report", instruction="report bhejo",
                      repeat="daily", next_run=datetime.now(timezone.utc) - timedelta(minutes=1), status="active"))
    seen = []

    async def turn(conv, text, tenant_id=None, voice=False, **kw):
        seen.append(kw.get("actor"))
        return "Report bhej di."
    monkeypatch.setattr(santosh, "run_turn", turn)
    import app.agent as ag
    monkeypatch.setattr(ag, "run_turn", turn)

    async def go():
        await worker.run_routines()
        for _ in range(100):
            await asyncio.sleep(0.01)
            if seen:
                break
        await asyncio.sleep(0.05)
    asyncio.run(go())
    assert seen == ["routine"]
    with session() as s:
        rows = s.scalars(select(TurnInbox).where(TurnInbox.conversation_id == "r1")).all()
        assert len(rows) == 1 and rows[0].actor == "routine"
    src = inspect.getsource(turn_inbox.sweep)
    assert 'actor=r["actor"]' in src


# ---------------------------------------------------------------- 19 Dobara / edit / form answer
def test_retry_edit_and_form_answers_ride_the_inbox():
    from app import main
    for fn in (main.chat_retry, main._edited_turn, main._form_reply):
        src = inspect.getsource(fn)
        assert "turn_inbox.accept" in src and "run_owned" in src, fn.__name__
        assert "add_task(run_turn" not in src and "await run_turn(" not in src, fn.__name__


# ---------------------------------------------------------------- 20 rows saved before the lock
def test_a_reply_while_another_turn_holds_the_chat_stays_out_of_history(env):
    from app.agent import santosh
    from app.db import Message
    _chat("h1")

    async def go():
        async with santosh._locks["h1"]:
            santosh._save_pre("h1", "user", "haan", display="haan")
        santosh._save_pre("h1", "user", "theek hai", display="theek hai")
    asyncio.run(go())
    with session() as s:
        rows = {m.display: m.in_history for m in s.scalars(select(Message).where(Message.conversation_id == "h1")).all()}
    assert rows == {"haan": False, "theek hai": True}


# ---------------------------------------------------------------- 21 a stop never runs in parallel
def test_kaam_status_stop_is_never_parallel():
    from app.agent import santosh
    assert santosh._parallel_ok({"name": "kaam_status", "input": {"action": "status"}})
    assert santosh._parallel_ok({"name": "kaam_status", "input": {}})
    assert not santosh._parallel_ok({"name": "kaam_status", "input": {"action": "stop", "q": "x"}})
    assert santosh._parallel_ok({"name": "google_search", "input": {}})
    assert not santosh._parallel_ok({"name": "email_send", "input": {}})


# ---------------------------------------------------------------- 22 channel replies sent once, after they went
def test_a_channel_reply_is_kept_until_it_really_went(env, monkeypatch):
    from app import bahar
    from app.db import Message
    _chat("b1")
    bahar.ensure_table()
    with session() as s:
        l = bahar.BaharLink(tenant_id=T, channel="telegram", hook="h42", external_id="42", status="linked", conversation_id="b1",
                            last_sent_id=0)
        s.add(l)
        s.add(Message(conversation_id="b1", role="assistant", content="Jawab 1", display="Jawab 1", in_history=True))
        s.flush()
        lid = l.id
    ok = {"v": False}
    sent = []

    async def send(link_id, text):
        if ok["v"]:
            sent.append(text)
        return ok["v"]
    monkeypatch.setattr(bahar, "_send", send)
    bahar._FAILS.clear()
    assert asyncio.run(bahar.forward(lid)) == 0                 # the channel was down: nothing marked sent
    ok["v"] = True
    assert asyncio.run(bahar.forward(lid)) == 1 and sent == ["Jawab 1"]
    assert asyncio.run(bahar.forward(lid)) == 0 and sent == ["Jawab 1"]   # once


def test_a_reply_that_keeps_failing_is_skipped_after_three_tries(env, monkeypatch):
    from app import bahar
    from app.db import Message
    _chat("b2")
    bahar.ensure_table()
    with session() as s:
        l = bahar.BaharLink(tenant_id=T, channel="telegram", hook="h43", external_id="43", status="linked", conversation_id="b2",
                            last_sent_id=0)
        s.add(l)
        s.add(Message(conversation_id="b2", role="assistant", content="bad", display="bad", in_history=True))
        s.add(Message(conversation_id="b2", role="assistant", content="good", display="good", in_history=True))
        s.flush()
        lid = l.id
    sent = []

    async def send(link_id, text):
        if text == "bad":
            return False
        sent.append(text)
        return True
    monkeypatch.setattr(bahar, "_send", send)
    bahar._FAILS.clear()
    for _ in range(3):
        asyncio.run(bahar.forward(lid))
    assert sent == ["good"]


# ---------------------------------------------------------------- 23 a reminder said once
def test_a_reminder_is_advanced_before_it_is_said(env, monkeypatch):
    from app import worker
    from app.db import Reminder
    import app.events as ev
    _chat("m1")
    with session() as s:
        s.add(Reminder(tenant_id=T, conversation_id="m1", text="Dawai", repeat="daily",
                       due_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    said = []

    def note(c, t, *a, **k):
        with session() as s:      # at the moment she is told, the reminder is already moved on
            r = s.scalars(select(Reminder).where(Reminder.conversation_id == "m1")).first()
            said.append((t, r.due_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)))
    monkeypatch.setattr(ev, "notify", note)
    monkeypatch.setattr(worker, "_ring_for_reminder", lambda *a: None)
    asyncio.run(worker.fire_reminders())
    asyncio.run(worker.fire_reminders())
    assert said == [("Yaad dila raha hoon: Dawai", True)]
