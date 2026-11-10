"""v0.662 KAAM SAAF (owner: "GO" on Wave 4 of the deep audit - coworker polish: 9, 10, 11, 26, 27, 28, 29, 30).

9  the Kaam list: no "ho gaya" for a turn that only started a job, no questions / routine prompts, waiting cards shown
10 a stuck job's notice promises no check that never happens
11 a Stop tapped while a turn prepares is not erased
26 a dead Google sign-in is not asked again every minute, and she is told (once a day)
27 a reminder missed during downtime is said as LATE and never rings her at night
28 the honesty check knows the common Hinglish "done" forms + an unbacked "yaad dila dungi"
29 one failing worker slot no longer skips the slots after it
30 an outage error is said once (not per background turn); a 3-day-old card is not news on every call ask
"""
from __future__ import annotations

import asyncio
import inspect
import json
import types
from datetime import datetime, timedelta, timezone

import pytest

from app.db import Conversation, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


# ---------------------------------------------------------------- 29 worker slots
def test_a_failing_slot_never_skips_the_ones_after_it(monkeypatch):
    from app import worker
    src = inspect.getsource(worker.tick)
    names = [n.strip() for n in src.split("for fn in (", 1)[1].split("):", 1)[0].replace("\n", " ").split(",") if n.strip()]
    ran = []
    for n in names:
        monkeypatch.setattr(worker, n, (lambda name: (lambda: ran.append(name)))(n))

    def boom():
        raise RuntimeError("campaign table broken")
    monkeypatch.setattr(worker, names[0], boom)
    asyncio.run(worker.tick())
    assert ran == names[1:] and "fire_reminders" in ran


# ---------------------------------------------------------------- 27 late reminders
def _reminder(conv, minutes_ago):
    from app.db import Reminder
    with session() as s:
        s.add(Reminder(tenant_id=T, conversation_id=conv, text="Dawai lena",
                       due_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)))


def _fire(monkeypatch, quiet):
    from app import worker
    import app.events as ev
    said, rang = [], []
    monkeypatch.setattr(ev, "notify", lambda c, t, *a, **k: said.append(t))
    monkeypatch.setattr(worker, "_ring_for_reminder", lambda *a: rang.append(a))
    monkeypatch.setattr(worker, "_quiet_now", lambda tenant: quiet)
    asyncio.run(worker.fire_reminders())
    return said, rang


def test_a_reminder_missed_in_downtime_is_said_late_and_never_rings_at_night(env, monkeypatch):
    _chat("r1")
    _reminder("r1", 330)
    said, rang = _fire(monkeypatch, quiet=True)
    assert said and "der se" in said[0] and "Dawai lena" in said[0]
    assert rang == []


def test_an_on_time_reminder_is_unchanged(env, monkeypatch):
    _chat("r2")
    _reminder("r2", 1)
    said, rang = _fire(monkeypatch, quiet=True)
    assert said == ["Yaad dila raha hoon: Dawai lena"] and len(rang) == 1


# ---------------------------------------------------------------- 11 stop during preparation
def test_a_stop_tapped_while_the_turn_prepares_is_kept(env, monkeypatch):
    from app.agent import santosh
    _chat("s1")
    stepped = []

    async def steps(*a, **k):
        stepped.append(1)
        return "kaam kiya"
    monkeypatch.setattr(santosh, "_steps", steps)
    real = santosh._load_history

    def hist(conv, *a, **k):
        santosh.stop(conv)             # her Stop lands while memory / history is being read
        return real(conv, *a, **k)
    monkeypatch.setattr(santosh, "_load_history", hist)
    out = asyncio.run(santosh.run_turn("s1", "50 logon ko mail bhejo", T))
    assert out == santosh.STOPPED_IN_PREP and stepped == []


# ---------------------------------------------------------------- 26 dead Google sign-in
def test_a_dead_google_sign_in_backs_off_and_tells_her_once(env, monkeypatch):
    from google.auth.exceptions import RefreshError
    from app import google_auth, convs
    import app.events as ev
    _chat("g1")
    monkeypatch.setattr(convs, "current", lambda t: "g1")
    told = []
    monkeypatch.setattr(ev, "notify", lambda c, t, *a, **k: told.append(t))
    google_auth._DEAD.clear()
    calls = []

    class Creds:
        refresh_token = "rt-1"

        def refresh(self, req):
            calls.append(1)
            raise RefreshError("invalid_grant: Token has been expired or revoked.")
    tok = google_auth.BACKGROUND.set(True)              # the background watchers (mail 60 s, calendar 120 s)
    try:
        for _ in range(3):
            with pytest.raises(google_auth.GoogleReconnect):
                google_auth.refresh(Creds(), T, "me@x.in")
    finally:
        google_auth.BACKGROUND.reset(tok)
    assert calls == [1]                                   # asked Google once, not every minute
    with pytest.raises(google_auth.GoogleReconnect):
        google_auth.refresh(Creds(), T, "me@x.in")       # her own chat ask always tries again
    assert calls == [1, 1]
    assert len(told) == 1 and "Google" in told[0] and "naye mail" in told[0]

    class NewCreds(Creds):
        refresh_token = "rt-2"                             # she signed in again: a new token is tried at once

        def refresh(self, req):
            calls.append(2)
    google_auth.refresh(NewCreds(), T, "me@x.in")
    assert calls == [1, 1, 2] and T not in google_auth._DEAD


# ---------------------------------------------------------------- 28 honesty check
@pytest.mark.parametrize("text", ["Order place ho gaya.", "Paisa transfer ho gaya.", "Reminder set ho gaya hai.",
                                  "Meeting fix ho gayi kal 4 baje.", "Mail chala gaya hai.",
                                  "Aapka message Rahul tak pahunch gaya.", "Theek hai, appointment le liya hai."])
def test_common_hinglish_done_claims_are_caught(text):
    from app.agent import draftcheck as d
    assert d.claims_done(text), text
    assert d.fake_done({"calls": []}, text) == d.NUDGE


@pytest.mark.parametrize("text", ["Order place ho jayega.", "Aap haan kahein to reminder set ho jayega."])
def test_future_forms_stay_honest(text):
    from app.agent import draftcheck as d
    assert d.claims_done(text) == ""


def test_a_reminder_promise_needs_a_reminder():
    from app.agent import draftcheck as d
    st = {"calls": []}
    assert d.fake_done(st, "Kal subah 9 baje yaad dila dungi.") == d.NUDGE_PROMISE
    assert d.fake_done(st, "Kal subah 9 baje yaad dila dungi.") == ""          # once
    ok = {"calls": [{"tool": "create_reminder", "ok": True, "result": "{'id': 'r1'}"}]}
    assert d.fake_done(ok, "Kal subah 9 baje yaad dila dungi.") == ""


# ---------------------------------------------------------------- 10 stuck notice
def test_the_stuck_notice_promises_no_check(env, monkeypatch):
    from app import kaamwatch
    from app.kaamwatch import KaamJob
    import app.events as ev
    _chat("k1")
    told = []
    monkeypatch.setattr(ev, "notify", lambda c, t, *a, **k: told.append(t))
    monkeypatch.setenv("KAAM_WATCH", "true")
    at = datetime.now(timezone.utc) - timedelta(minutes=40)
    with session() as s:
        s.add(KaamJob(tenant_id=T, conversation_id="k1", key="site_board:x", kind="site_board", label="Website",
                      title="Bakery", state="working", status="building", updated_at=at, moved_at=at, started_at=at))
    monkeypatch.setattr(kaamwatch, "BOOT_AT", datetime.now(timezone.utc))
    kaamwatch.tick()
    assert told and "dekh kar batata" not in told[0] and "dobara karo" in told[0] and "restart" in told[0]


# ---------------------------------------------------------------- 9 the Kaam list
def test_the_kaam_list_counts_only_real_finished_work(env, monkeypatch):
    from app import kaamlist, events
    from app.agent.pakka import TaskRun
    from app.kaamwatch import KaamJob
    _chat("w1")
    now = datetime.now(timezone.utc)
    with session() as s:
        s.add(TaskRun(tenant_id=T, conversation_id="w1", request="Sharma ji ko quotation bhejo", outcome="done",
                      tools=json.dumps(["email_draft"]), created_at=now - timedelta(hours=3)))
        s.add(TaskRun(tenant_id=T, conversation_id="w1", request="aaj mausam kaisa hai", outcome="done",
                      tools=json.dumps(["weather_check"]), created_at=now - timedelta(hours=2)))
        s.add(TaskRun(tenant_id=T, conversation_id="w1", request="[Automatic job 'subah ki report']", outcome="done",
                      tools=json.dumps(["email_send"]), created_at=now - timedelta(hours=2)))
        s.add(TaskRun(tenant_id=T, conversation_id="w1", request="bakery ki website banao", outcome="done",
                      tools=json.dumps(["website"]), seconds=40, created_at=now - timedelta(minutes=30)))
        s.add(KaamJob(tenant_id=T, conversation_id="w1", key="site_board:b", kind="site_board", label="Website",
                      title="Bakery", state="working", status="building", updated_at=now, moved_at=now,
                      started_at=now - timedelta(minutes=29)))
    monkeypatch.setattr(events, "waiting_cards", lambda t, limit=40, max_age_h=None: [
        {"id": 1, "kind": "bazar_approval", "key": "k", "age_h": 2.0, "title": "Swiggy order", "conversation_id": "w1",
         "at": now.isoformat()}])
    out = kaamlist.listing(T)
    done = [d["title"] for d in out["done"]]
    assert done == ["Sharma ji ko quotation bhejo"]
    assert [r["title"] for r in out["running"]] == ["Bakery"]
    assert any(w["title"] == "Swiggy order" and w["source"] == "card" for w in out["waiting"])


# ---------------------------------------------------------------- 30 errors once + stale cards
def test_an_outage_error_is_said_once_by_background_turns():
    from app.agent import santosh
    santosh._BG_ERR.clear()
    msg = "Anthropic ka credit khatam ho gaya hai (ref ab12cd)."
    assert santosh._say_error(T, "routine", msg) is True
    assert santosh._say_error(T, "wake", "Anthropic ka credit khatam ho gaya hai (ref 99zz11).") is False
    assert santosh._say_error(T, "owner", msg) is True        # her own turn always hears it


def test_a_three_day_old_card_is_not_call_news(monkeypatch):
    from app import events
    rows = [{"id": 1, "kind": "bazar_approval", "key": "k", "age_h": 100.0, "title": "Purana order"}]
    monkeypatch.setattr(events, "waiting_cards",
                        lambda t, limit=40, max_age_h=None: [r for r in rows if max_age_h is None or r["age_h"] <= max_age_h])
    blk = events.cards_block(T)
    assert "Purana order" not in blk and "1 purane card" in blk
