"""v0.652 SACHCHA NATIJA (owner: "CHECK IS ANY TASK ON ANY SURFACE ... DOES IT MONITOR AND IF COMPLETE, INPROGRESS, STUCK
ETC DOES HOOLA AI HANDLE IT PROPERLY" -> audit -> GO on the four fixes)."""
from __future__ import annotations

import asyncio
import time
import types
from datetime import datetime, timedelta, timezone

from app.db import Conversation, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


# ---------------------------------------------------------------- 1. a cut / crashed turn has an honest outcome
def test_a_crashed_turn_is_recorded_stuck_not_left_to_an_old_done(env, monkeypatch):
    from app.agent import santosh
    from app.agent.pakka import TaskRun
    _chat("c1")
    santosh.LAST_OUTCOME["c1"] = {"outcome": "done", "left": "", "goal": "", "at": time.time() - 600}   # the PREVIOUS ask

    async def boom(*a, **k):
        raise RuntimeError("model gone")
    monkeypatch.setattr(santosh, "_steps", boom)
    asyncio.run(santosh.run_turn("c1", "Sharma ji ko 20 mail bhejo", T))
    oc = santosh.LAST_OUTCOME["c1"]
    assert oc["outcome"] == "stuck" and "galti" in oc["left"] and time.time() - oc["at"] < 30
    with session() as s:
        r = s.query(TaskRun).filter_by(conversation_id="c1").one()
        assert r.outcome == "stuck" and "Sharma ji" in r.request      # it is in the work diary / Kaam list now


def test_the_call_never_reads_an_earlier_asks_done():
    from app import voice
    from app.agent import santosh
    said = []
    fake = types.SimpleNamespace(conv="cc", closed=asyncio.Event(), stats={}, push_news=said.append,
                                 _tone_tag=lambda: "", _orphan_note=lambda t: None)

    async def go(outcome_at):
        santosh.LAST_OUTCOME["cc"] = {"outcome": "done", "left": "", "goal": "", "at": outcome_at}
        f = asyncio.get_running_loop().create_future()
        f.set_result("Yeh kaam bahut der se chal raha tha, isliye maine ise rok diya.")
        voice.Call._late_result(fake, f, "website banao", time.time())
    asyncio.run(go(time.time() - 300))
    assert said and "ho gaya:" not in said[0] and "jawab aaya" in said[0] and "'Ho gaya' sirf tab" in said[0]


def test_a_fresh_stuck_outcome_is_said_as_stuck():
    from app import voice
    from app.agent import santosh
    said = []
    fake = types.SimpleNamespace(conv="cd", closed=asyncio.Event(), stats={}, push_news=said.append,
                                 _tone_tag=lambda: "", _orphan_note=lambda t: None)

    async def go():
        since = time.time() - 5
        santosh.LAST_OUTCOME["cd"] = {"outcome": "stuck", "left": "time limit par roka gaya", "goal": "", "at": time.time()}
        f = asyncio.get_running_loop().create_future()
        f.set_result("rok diya")
        voice.Call._late_result(fake, f, "website banao", since)
    asyncio.run(go())
    assert "atka hai: time limit par roka gaya" in said[0] and "'Ho gaya' bilkul mat kehna" in said[0]


# ---------------------------------------------------------------- 2. every job kind's own words are understood
def test_every_mapped_status_of_every_kind_is_understood():
    from app import kaamwatch as K
    for kind, conf in K.KINDS.items():
        for status, state in conf["map"].items():
            p = {"id": "x1", "status": status, "title": "t"}
            if kind.startswith("devsahayak_"):
                p = {"task": p}
            j = K.shape(kind, p)
            assert j is not None and j["state"] == state, (kind, status)


def test_the_jobs_that_used_to_be_invisible():
    from app import kaamwatch as K
    cases = [("campaign", {"id": "c", "status": "sending", "title": "Diwali offer"}, "working"),
             ("campaign", {"id": "c", "status": "completed"}, "done"),
             ("game_desk", {"id": "g", "status": "design_ready"}, "waiting"),
             ("game_desk", {"id": "g", "status": "testing"}, "working"),
             ("eng_project", {"id": "e", "status": "analysing"}, "working"),
             ("eng_project", {"id": "e", "status": "drawing"}, "working"),
             ("devsahayak_task", {"task": {"id": "d", "status": "pr_open", "title": "fix cart"}}, "waiting"),
             ("devsahayak_task", {"task": {"id": "d", "status": "checks_failed", "title": "fix cart"}}, "failed"),
             ("devsahayak_push", {"task": {"id": "d", "status": "merged", "title": "fix cart"}}, "done")]
    for kind, p, state in cases:
        j = K.shape(kind, p)
        assert j and j["state"] == state, (kind, p)
    assert K.shape("devsahayak_task", cases[6][1])["title"] == "fix cart"


# ---------------------------------------------------------------- 3. stuck says stuck; dead is said once
def _job(conv: str, key: str, minutes_ago: float, state: str = "working"):
    from app.kaamwatch import KaamJob
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    with session() as s:
        s.add(KaamJob(tenant_id=T, conversation_id=conv, key=key, kind="site_board", label="Website", title="Bakery site",
                      state=state, status="building", updated_at=datetime.now(timezone.utc), moved_at=at, started_at=at))


def test_a_stuck_job_never_reads_as_running(env):
    from app import kaamlist, kaamwatch
    _chat("c2")
    _job("c2", "site_board:s1", minutes_ago=40)
    blk = kaamwatch.block(T, "c2")
    assert "ATKA HAI (40 min se aage nahi badha" in blk and "'chal raha hai' mat kehna" in blk
    assert "atka hai" in kaamwatch.status(T)["say"]
    row = kaamlist.listing(T)["running"][0]
    assert row["stuck"] is True and row["say"].startswith("atka hai")


def test_a_dead_job_is_said_once(env, monkeypatch):
    from app import kaamwatch
    import app.events as events
    told = []
    monkeypatch.setattr(events, "notify", lambda conv, text, *a, **k: told.append(text))
    monkeypatch.setenv("KAAM_WATCH", "true")
    _chat("c3")
    _job("c3", "site_board:s2", minutes_ago=3 * 24 * 60)
    kaamwatch.tick()
    kaamwatch.tick()
    assert len(told) == 1 and "2 din se aage nahi badha" in told[0]
    with session() as s:
        r = s.query(kaamwatch.KaamJob).filter_by(key="site_board:s2").one()
        assert (r.state, r.status) == ("stopped", "stale")


# ---------------------------------------------------------------- 4. a long call ask is never silence
def _checkin(monkeypatch, parked=False, cancelled=False):
    from app import kaamstop, voice
    said = []
    fake = types.SimpleNamespace(conv="cx", closed=asyncio.Event(), stats={}, push_news=said.append, parked=parked)
    if cancelled:
        kaamstop._RECENT["cx"] = time.monotonic()
    else:
        kaamstop._RECENT.pop("cx", None)
    real_wait = asyncio.wait

    async def fast_wait(fs, timeout=None, **k):
        return set(), set(fs)          # the job is still running at every check

    async def go():
        job = asyncio.get_running_loop().create_future()
        monkeypatch.setattr(voice.asyncio, "wait", fast_wait)
        try:
            await voice.Call._still_working(fake, job, "website banao")
        finally:
            monkeypatch.setattr(voice.asyncio, "wait", real_wait)
    asyncio.run(go())
    return said, fake


def test_a_long_call_ask_says_it_is_still_working(env, monkeypatch):
    said, fake = _checkin(monkeypatch)
    assert len(said) == 3 and all("abhi bhi chal raha hai" in x and "'Ho gaya' bilkul mat kehna" in x for x in said)
    assert fake.stats["still_working"] == 3


def test_no_checkin_on_a_parked_call_or_a_cancelled_job(env, monkeypatch):
    assert _checkin(monkeypatch, parked=True)[0] == []
    assert _checkin(monkeypatch, cancelled=True)[0] == []
    from app.config import Settings
    assert Settings().voice_checkin_s == 150 and Settings().voice_checkin_max == 3
