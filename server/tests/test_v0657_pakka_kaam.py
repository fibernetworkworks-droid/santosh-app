"""v0.657 PAKKA KAAM (owner: "Wave 1 (lost work, money): 1, 2, 5, 6, 7, 8, 12 --- FIX THIS" after the deep audit).

1  a restart mid-turn (after a tool step) is RESUMED, never marked done unanswered
2  a message queued behind another turn is re-run after a restart, not dropped by the other turn's reply
5  an approval card runs its action exactly once (claimed before it runs); a run cut by a restart is said plainly
6  a wake turn that failed is not "the result delivered" - the honest line with the link goes out
7  a finished job is reported once: no dry line inside its own wake report, no second report later
8  a routine whose turn failed is recorded failed and never spoken on a call as "poora hua"
12 a timed-out turn warns that a step may be half done instead of inviting a blind resend
"""
from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import pytest
from sqlalchemy import select

from app import kaam_followup as kf
from app import kaamwatch as kw
from app import turn_inbox as ti
from app.agent import santosh
from app.db import Conversation, Message, now, session


def _conv(c):
    with session() as s:
        if s.get(Conversation, c) is None:
            s.add(Conversation(id=c, tenant_id="default", title="t"))


def _fake_run(monkeypatch):
    ran = []
    import app.agent as ap

    async def fake(*a, **k):
        ran.append((a, k))
        return "x"
    monkeypatch.setattr(ap, "run_turn", fake)
    return ran


# ---------------------------------------------------------------- 1 + 2 the restart sweep
def test_a_turn_cut_after_a_tool_step_is_resumed_not_marked_done(env, monkeypatch):
    _conv("c1")
    rid = ti.accept("default", "c1", "3 logon ko mail bhejo", False, "", "x")
    with session() as s:
        r = s.get(ti.TurnInbox, rid)
        r.status, r.updated_at = "running", now() - timedelta(minutes=10)
        created = r.created_at
        r.started_at = created + timedelta(seconds=1)
        s.add(Message(conversation_id="c1", role="user", content="3 logon ko mail bhejo",
                      display="3 logon ko mail bhejo", in_history=True, created_at=created + timedelta(seconds=1)))
        s.add(Message(conversation_id="c1", role="assistant", in_history=True, display="Bhej raha hoon",
                      content=[{"type": "text", "text": "Bhej raha hoon"},
                               {"type": "tool_use", "id": "t1", "name": "email_send", "input": {}}],
                      created_at=created + timedelta(seconds=5)))
    ran = _fake_run(monkeypatch)
    asyncio.run(ti.sweep())
    assert len(ran) == 1
    a, k = ran[0]
    assert k.get("save_user") is False                    # her words are already in history
    assert ti.RESUME_NOTE in k.get("context", "") and "DOBARA mat karo" in k["context"]


def test_a_really_answered_turn_is_still_skipped(env, monkeypatch):
    _conv("c1b")
    rid = ti.accept("default", "c1b", "hi", False, "", "x")
    with session() as s:
        r = s.get(ti.TurnInbox, rid)
        r.status, r.updated_at = "running", now() - timedelta(minutes=10)
        r.started_at = r.created_at
        s.add(Message(conversation_id="c1b", role="assistant", in_history=True, display="Namaste",
                      content=[{"type": "text", "text": "Namaste"}], created_at=r.created_at + timedelta(seconds=3)))
    ran = _fake_run(monkeypatch)
    asyncio.run(ti.sweep())
    with session() as s:
        assert s.get(ti.TurnInbox, rid).status == "done"
    assert ran == []


def test_a_queued_message_is_not_dropped_by_the_previous_turns_reply(env, monkeypatch):
    _conv("c2")
    rid_b = ti.accept("default", "c2", "aur Rahul ko bhi", False, "", "b")   # B, queued behind A
    with session() as s:
        r = s.get(ti.TurnInbox, rid_b)
        r.created_at = now() - timedelta(minutes=5)
        s.add(Message(conversation_id="c2", role="assistant", in_history=True, display="A ka jawab",
                      content=[{"type": "text", "text": "A ka jawab"}], created_at=r.created_at + timedelta(seconds=30)))
    ran = _fake_run(monkeypatch)
    asyncio.run(ti.sweep())
    assert len(ran) == 1 and ran[0][0][1] == "aur Rahul ko bhi"
    assert ran[0][1].get("save_user", True) is True       # her words were never saved: save them now


def test_the_turn_stamps_its_own_inbox_row(env):
    _conv("c3")
    rid = ti.accept("default", "c3", "kuch karo", False, "", "s")
    tok = ti.CURRENT.set(rid)
    try:
        ti.started("other-chat")                          # a nested turn in another chat never stamps it
        with session() as s:
            assert s.get(ti.TurnInbox, rid).started_at is None
        ti.CURRENT.set(rid)
        ti.started("c3")
        with session() as s:
            assert s.get(ti.TurnInbox, rid).started_at is not None
    finally:
        ti.CURRENT.reset(tok)


def test_the_real_turn_calls_the_stamp():
    import inspect
    src = inspect.getsource(santosh._run_turn)
    assert "_ti.started" in src and src.index("_ti.started") < src.index("_load_history, conversation_id")   # v0.668 read in a thread


# ---------------------------------------------------------------- 6 + 7 job reports
def test_a_failed_wake_turn_falls_back_to_the_line_with_the_link(env, monkeypatch):
    monkeypatch.setenv("KAAM_FOLLOWUP", "true")
    _conv("c4")
    notices = []
    monkeypatch.setattr(kf, "notify", lambda c, t: notices.append(t))
    monkeypatch.setattr(kw, "_voice", lambda *a: None)
    kf.enqueue("default", "c4", {"key": "video_job:v2", "state": "done", "title": "Reel", "label": "Video edit",
                                 "link": "https://x/y.mp4"})

    async def fake_turn(conv, text, tenant_id=None, actor="owner", **k):
        santosh._mark_failed(conv)
        return "Maaf kijiye, abhi kuch gadbad ho gayi."
    monkeypatch.setattr(santosh, "run_turn", fake_turn)
    monkeypatch.setattr(kf, "_wake_allowed", lambda conv, st: True)
    woke = []
    real_wake = kf._wake_turn

    async def spy(r, st):
        woke.append(1)
        return await real_wake(r, st)
    monkeypatch.setattr(kf, "_wake_turn", spy)

    async def no_model(r, st):
        return ""                       # the model is out too: the canned line with the link
    monkeypatch.setattr(kf, "_model_line", no_model)

    async def go():
        await kf.tick()
        await asyncio.sleep(0.2)
    asyncio.run(go())
    assert woke and any("https://x/y.mp4" in n for n in notices)


def test_no_dry_line_inside_the_jobs_own_wake_report(env, monkeypatch):
    monkeypatch.setenv("KAAM_FOLLOWUP", "true")
    monkeypatch.setenv("KAAM_FOLLOWUP_WAIT_S", "30")
    _conv("c5")
    notices = []
    monkeypatch.setattr(kf, "notify", lambda c, t: notices.append(t))
    monkeypatch.setattr(kw, "_voice", lambda *a: None)
    kf.enqueue("default", "c5", {"key": "video_job:v1", "state": "done", "title": "Reel", "label": "Video edit"})
    with session() as s:
        s.scalars(select(kf.KaamFollowup)).first().created_at = now() - timedelta(seconds=25)
    wake = []

    async def fake_turn(conv, text, tenant_id=None, actor="owner", **k):
        async with santosh._locks[conv]:
            await asyncio.sleep(0.3)
            wake.append("Reel taiyaar")
            return wake[-1]
    monkeypatch.setattr(santosh, "run_turn", fake_turn)

    async def go():
        await kf.tick()
        await asyncio.sleep(0.05)
        with session() as s:
            s.scalars(select(kf.KaamFollowup)).first().created_at = now() - timedelta(seconds=40)
        await kf.tick()
        await asyncio.sleep(0.5)
    asyncio.run(go())
    assert wake and not notices


def test_a_finished_job_is_not_reported_again_later(env, monkeypatch):
    monkeypatch.setenv("KAAM_WATCH", "true")
    monkeypatch.setenv("KAAM_FOLLOWUP", "true")
    _conv("c6")
    monkeypatch.setattr(kw, "_voice", lambda *a: None)
    told = []
    import app.events as ev
    monkeypatch.setattr(ev, "notify", lambda c, t, *a, **k: told.append(t))
    kw.observe("c6", "video_job", {"id": "v9", "status": "done", "name": "Ad reel"})
    with session() as s:
        assert s.scalars(select(kw.KaamJob)).first().told == "done"
        for f in s.scalars(select(kf.KaamFollowup)).all():
            f.status = "sent"
    kw.observe("c6", "video_job", {"id": "v9", "status": "done", "name": "Ad reel"})   # within 10 min
    with session() as s:
        for f in s.scalars(select(kf.KaamFollowup)).all():
            f.created_at = now() - timedelta(minutes=11)
    kw.observe("c6", "video_job", {"id": "v9", "status": "done", "name": "Ad reel"})   # after 10 min
    with session() as s:
        assert len(s.scalars(select(kf.KaamFollowup)).all()) == 1
    assert told == []


# ---------------------------------------------------------------- 8 routines
def test_turn_failed_since():
    t0 = time.time()
    assert not santosh.turn_failed_since("rr", t0)
    santosh._mark_failed("rr")
    assert santosh.turn_failed_since("rr", t0)
    assert not santosh.turn_failed_since("rr", time.time() + 5)


def test_a_failed_routine_is_not_spoken_as_done():
    import inspect
    from app import worker
    src = inspect.getsource(worker)
    i = src.index("turn_failed_since(conv, t0)")
    assert 'out = f"failed: {out}"' in src[i:i + 400]


def test_every_failure_exit_stamps_failed():
    import inspect
    src = inspect.getsource(santosh._run_turn)
    assert src.count("_mark_failed(conversation_id)") >= 3       # budget, timeout, crash
    assert "_mark_failed(conversation_id)" in inspect.getsource(santosh.run_turn)


# ---------------------------------------------------------------- 12 timeout words
def test_the_timeout_line_warns_about_a_half_done_step():
    assert "half done" in santosh.TIMEOUT_TEXT and "twice" in santosh.TIMEOUT_TEXT
    assert "chhota karke phir bolein" not in santosh.TIMEOUT_TEXT
    assert "you do not need to say anything again" in santosh.TIMEOUT_GOAL


# ---------------------------------------------------------------- 5 approval cards
@pytest.fixture
def bz(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security
    bzc.reset_settings()
    security._vault = None
    from app.bazar import service
    service.set_executors(None)
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    yield {"svc": service, "conv": conv}
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


def _bill_card(svc, conv):
    bill = svc.run("default", conv, "msedcl-mahavitaran", "fetch_bill", {"consumer_number": "330012345678", "billing_unit": "4630"})
    return svc.run("default", conv, "msedcl-mahavitaran", "pay_bill", {"bill_ref": bill["bill_ref"], "amount": 1})


def test_a_second_tap_while_the_first_runs_never_runs_it_again(bz, monkeypatch):
    svc, conv = bz["svc"], bz["conv"]
    pay = _bill_card(svc, conv)
    from app.bazar.agent.runner import Runner
    from app.bazar.connectors.base import ToolError
    real = Runner._execute
    runs, second = [], []

    def slow(self, ctx, ap):
        runs.append(ap.id)
        if len(runs) == 1:              # the console tap lands while the phone tap is still running
            try:
                svc.decide("default", pay["approval_id"], "approve")
            except ToolError as e:
                second.append(str(e))
        return real(self, ctx, ap)
    monkeypatch.setattr(Runner, "_execute", slow)
    res = svc.decide("default", pay["approval_id"], "approve")
    assert runs == [pay["approval_id"]]                 # executed exactly once
    assert second and "Already" in second[0]
    assert res["status"] == "approved"


def test_a_run_cut_by_a_restart_is_said_plainly_never_nothing_ordered(bz):
    svc, conv = bz["svc"], bz["conv"]
    pay = _bill_card(svc, conv)
    from app.bazar.db import Approval
    from app.db import session as bsession
    import datetime as dt
    with bsession() as s:
        ap = s.get(Approval, pay["approval_id"])
        ap.decision = "executing"
        ap.decided_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(hours=1)
    svc.expire_approvals(24)
    with bsession() as s:
        assert s.get(Approval, pay["approval_id"]).decision == "interrupted"
    with session() as s:
        said = [m.display or "" for m in s.scalars(select(Message).where(Message.conversation_id == conv)).all()]
    assert any("pakka nahi pata" in m for m in said)
    assert not any("kuch order ya payment nahi hua" in m and "purana" in m for m in said)
