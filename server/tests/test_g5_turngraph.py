"""G5 of docs/LANGGRAPH_TURN_PLAN.md: the turn's outcome lives in the graph state and ONE `deliver` node tells her the
result (`chat_graph` on) - told once, in the right chat, across a restart.

Fake brain / fake tools in the style of test_g0 .. test_g4. Push is counted at the FCM pool (push.on_event and every
gate it has - quiet hours, a live call, the night hold, the ring's own rules - runs for real); the live-call note is
counted at kaamwatch._voice. A restart is simulated as in test_g1: a CancelledError at the chosen point, the in-memory
state wiped, the restart sweep run in a FRESH event loop."""
import asyncio

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, _settings, tu, txt
from tests.test_g1_turngraph import _age, _owned, _restart, _status, _sweep
from tests.test_g4_turngraph import FINAL, SEG1, SEG2, _goal, _job_turn, _shown, gz  # noqa: F401  (fixture)

ANSWER = "Aapke teen reminder hain: kal 10 baje doctor, 2 baje bank, aur shaam 6 baje gym."
REPORT = "Video edit ho gaya - 45 second ka reel taiyaar hai, link chat mein hai."
QUIET = {"VOICE_RING_QUIET": "0-0", "PUSH_QUIET": "0-0"}      # never quiet: the ring / push gates decide by the rules


class Pool:
    """Stands in for push._pool: every push that passed push.on_event's gates lands here (nothing leaves the box)."""

    def __init__(self):
        self.sent: list[dict] = []

    def submit(self, fn, tenant, ev):
        self.sent.append(ev)

    def kinds(self, kind):
        return [e for e in self.sent if e.get("kind") == kind]

    def replies(self, text):
        return [e for e in self.kinds("message") if (e.get("payload") or {}).get("text") == text]


@pytest.fixture
def g5(gz, monkeypatch):  # noqa: F811
    """gz (bz + no titling + rounds at once) + a counted FCM pool + a counted live-call note."""
    from app import kaamwatch, push
    pool = Pool()
    monkeypatch.setattr(push, "_pool", pool)
    monkeypatch.setattr(push, "configured", lambda: True)
    push._AWAKE.clear()
    push._HELD.clear()
    push._RING_DAY.clear()
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(kaamwatch, "_voice", lambda tenant, conv, say: notes.append((conv, say)))
    yield {**gz, "pool": pool, "notes": notes}
    push._HELD.clear()


def _setup(monkeypatch, graph, script, extra=None, **tool_kw):
    from tests.test_g4_turngraph import _setup as g4_setup
    return g4_setup(monkeypatch, graph, script, extra={**QUIET, **(extra or {})}, **tool_kw)


def _watched(monkeypatch):
    """kaamwatch on (it queues the job's report). Found on the way, NOT part of G5 and on both paths: with the watch on,
    a long job's own 'goal:' kaam_jobs row (state working) makes goal._waiting_on_job hold the job for up to an hour
    after its first segment - here the job is let through so its end can be checked."""
    from app.agent import goal
    monkeypatch.setattr(goal, "_waiting_on_job", lambda conv: False)
    return {"KAAM_WATCH": "true"}


def _replies(conv, text):
    return [d for r, d in _rows(conv) if r == "assistant" and d == text]


def _deliveries(conv=""):
    from app.agent import turndeliver as D
    return D.rows(conv)


def _accept(conv, ask, cid):
    from app import turn_inbox as ti
    return ti.accept("default", conv, ask, False, "", cid)


def _followups(conv):
    from app import kaam_followup as K
    from app.db import session
    K.ensure_table()
    with session() as s:
        return [{"id": r.id, "key": r.key, "state": r.state, "status": r.status}
                for r in s.scalars(select(K.KaamFollowup).where(K.KaamFollowup.conversation_id == conv)
                                   .order_by(K.KaamFollowup.created_at)).all()]


def _send(fid):
    from app import kaam_followup as K
    from app.config import get_settings
    asyncio.run(asyncio.wait_for(K._send(fid, get_settings()), 120))


def _queue(conv, key="video_job:v1", state="done"):
    """A finished background job's report, queued the way kaamwatch queues it."""
    from app import kaam_followup as K
    assert K.enqueue("default", conv, {"key": key, "kind": key.split(":")[0], "label": "Video edit",
                                       "title": "Diwali reel", "state": state, "detail": "45 second", "link": ""})
    return [f for f in _followups(conv) if f["key"] == key][-1]["id"]


def _crashy_deliver(monkeypatch, before: bool):
    """The deliver node dies once (a restart): before it does anything, or right after it finished its work."""
    from app.agent import turngraph
    real = turngraph._deliver
    n = {"calls": 0}

    async def node(live, state):
        n["calls"] += 1
        if before and n["calls"] == 1:
            raise asyncio.CancelledError()
        out = await real(live, state)
        if not before and n["calls"] == 1:
            raise asyncio.CancelledError()
        return out
    monkeypatch.setattr(turngraph, "_deliver", node)
    monkeypatch.setattr(turngraph, "_BUILDER", None)    # the graph is compiled again around the patched node
    return n


# (1) a plain turn: the reply is told ONCE - one row, one SSE event, one push - and the state carries the outcome
def test_plain_turn_told_once_and_the_outcome_is_in_state(g5, monkeypatch):
    from app.agent import turngraph
    brain, tools = _setup(monkeypatch, True, [[tu(1, "list_reminders")], txt(ANSWER)],
                          extra={"CHAT_GRAPH_KEEP_FINISHED": "true"})
    conv = _new_conv()
    ask = "Mere reminders batao"
    out = asyncio.run(_owned(conv, _accept(conv, ask, "c-1"), ask))
    assert out == ANSWER
    assert len(_replies(conv, ANSWER)) == 1
    from app.db import Event, session
    with session() as s:
        evs = [e for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "message")).all()
               if (e.payload or {}).get("text") == ANSWER]
    assert len(evs) == 1                                             # one SSE event
    assert len(g5["pool"].replies(ANSWER)) == 1                      # one push
    recs = [r for r in _deliveries(conv) if r["kind"] == "turn"]
    assert len(recs) == 1
    ch = recs[0]["channels"]
    assert ch["chat"]["state"] == "sent" and ch["chat"]["by"] == "step" and ch["push"]["state"] == "sent"
    assert "call" not in ch and "ring" not in ch                     # her own turn: she is reading it, no ring
    assert recs[0]["outcome"] == "done" and recs[0]["conversation_id"] == conv
    from app.config import get_settings
    final = [c for c in asyncio.run(turngraph.checkpoints(get_settings(), conv))
             if c["values"].get("result")][0]["values"]
    assert final["result"] == "done"
    assert final["notified"]["chat"]["row"] == ch["chat"]["row"]
    assert final["delivery"]["target"] == conv and final["delivery"]["key"] == recs[0]["key"]


# (2) a restart AFTER deliver wrote `notified` but before the turn ended: the resumed deliver sends nothing again
def test_restart_after_deliver_sends_nothing_twice(g5, monkeypatch):
    n = _crashy_deliver(monkeypatch, before=False)
    brain, tools = _setup(monkeypatch, True, [[tu(1, "list_reminders")], txt(ANSWER)])
    conv = _new_conv()
    ask = "Mere reminders batao"
    rid = _accept(conv, ask, "c-2")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_owned(conv, rid, ask))
    rec0 = [r for r in _deliveries(conv) if r["kind"] == "turn"]
    assert len(rec0) == 1 and rec0[0]["channels"]["chat"]["state"] == "sent"
    pushes0 = len(g5["pool"].replies(ANSWER))
    _restart()
    _age(rid)
    assert asyncio.run(_sweep()) == 1                                # resumed AT deliver (not marked done by a guess)
    assert n["calls"] == 2
    assert brain.calls == 2 and tools.count == {"list_reminders": 1}  # nothing redone
    assert len(_replies(conv, ANSWER)) == 1
    assert len(g5["pool"].replies(ANSWER)) == pushes0 == 1
    rec1 = [r for r in _deliveries(conv) if r["kind"] == "turn"]
    assert len(rec1) == 1 and rec1[0]["channels"] == rec0[0]["channels"]   # the same stamps, nothing re-sent
    assert _status(rid) == "done"


# (3) a restart BEFORE deliver (the answer streamed, the node never ran): told exactly once after the resume
def test_restart_before_deliver_told_once_after_resume(g5, monkeypatch):
    n = _crashy_deliver(monkeypatch, before=True)
    brain, tools = _setup(monkeypatch, True, [[tu(1, "list_reminders")], txt(ANSWER)])
    conv = _new_conv()
    ask = "Mere reminders batao"
    rid = _accept(conv, ask, "c-3")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_owned(conv, rid, ask))
    assert _deliveries(conv) == []                                   # nothing recorded yet
    _restart()
    _age(rid)
    assert asyncio.run(_sweep()) == 1
    assert n["calls"] == 2 and brain.calls == 2
    assert len(_replies(conv, ANSWER)) == 1                          # the step's row, not a second one
    assert len(g5["pool"].replies(ANSWER)) == 1
    recs = [r for r in _deliveries(conv) if r["kind"] == "turn"]
    assert len(recs) == 1 and recs[0]["channels"]["chat"]["state"] == "sent"
    assert _status(rid) == "done"


# (4) a background job finishes while she has ANOTHER chat open: its report lands in the job's own chat (v0.714), the
# call note and the ring go once (by the deliver node), and a second tick never tells it again
def test_background_job_told_in_its_own_chat_once(g5, monkeypatch):
    from app import convs
    brain, tools = _setup(monkeypatch, True, [txt(REPORT)])
    job_chat, open_chat = _new_conv(), _new_conv()
    convs.mark("default", open_chat)                                 # the chat she is looking at
    fid = _queue(job_chat)
    _send(fid)
    assert brain.calls == 1
    assert len(_replies(job_chat, REPORT)) == 1
    assert [r for r, d in _rows(open_chat) if r == "assistant"] == []   # never in the chat she has open
    news = [r for r in _deliveries() if r["kind"] == "news"]
    assert len(news) == 1 and news[0]["conversation_id"] == job_chat
    ch = news[0]["channels"]
    assert ch["chat"]["state"] == "sent" and ch["call"]["state"] == "sent" and ch["ring"]["state"] == "sent"
    assert [c for c, _ in g5["notes"]] == [job_chat]                 # ONE call note (not the deliver node + the wake)
    assert len(g5["pool"].kinds("voice_ring")) == 1                  # ONE ring (not the deliver node + _send)
    assert len(g5["pool"].replies(REPORT)) == 1
    assert _followups(job_chat)[-1]["status"] == "sent"
    # the row is picked up again (a restart before it was marked sent): the record says told - nothing again
    from app import kaam_followup as K
    from app.db import session
    with session() as s:
        s.get(K.KaamFollowup, fid).status = "pending"
    _send(fid)
    assert brain.calls == 1 and len(_replies(job_chat, REPORT)) == 1
    assert len(g5["notes"]) == 1 and len(g5["pool"].kinds("voice_ring")) == 1
    assert _followups(job_chat)[-1]["status"] == "skipped"


# (4a) the SAME job key finishing again later (a reel made again) is a new occurrence: its report is told, not
# swallowed by the record of the first one
def test_same_job_key_again_later_is_told_again(g5, monkeypatch):
    from datetime import timedelta
    from app import kaam_followup as K
    from app.db import now, session
    again = "Naya reel bhi taiyaar hai - 30 second ka, link chat mein hai."
    brain, tools = _setup(monkeypatch, True, [txt(REPORT), txt(again)])
    conv = _new_conv()
    _send(_queue(conv))
    with session() as s:                       # the next build of the same job, queued after the first was told
        row = K.KaamFollowup(tenant_id="default", conversation_id=conv, key="video_job:v1", kind="video_job",
                             label="Video edit", title="Diwali reel", state="done")
        row.created_at = now() + timedelta(seconds=30)
        s.add(row)
        s.flush()
        fid2 = row.id
    _send(fid2)
    assert brain.calls == 2 and len(_replies(conv, again)) == 1
    assert _followups(conv)[-1]["status"] == "sent"


# (4b) the wake turn's reply landed but the process died before its deliver node ran: after the restart the report is
# known told by its reply row's id (never a time window) - no second wake turn; the missing call note + ring go once
def test_wake_reply_landed_before_a_restart_is_not_told_again(g5, monkeypatch):
    _crashy_deliver(monkeypatch, before=True)
    brain, tools = _setup(monkeypatch, True, [txt(REPORT), txt("(a second report)")])
    conv = _new_conv()
    fid = _queue(conv)
    with pytest.raises(asyncio.CancelledError):
        _send(fid)
    assert len(_replies(conv, REPORT)) == 1 and g5["notes"] == []
    _restart()
    _send(fid)                                                       # the next tick after the restart
    assert brain.calls == 1                                          # no second wake turn
    assert _replies(conv, "(a second report)") == []
    assert len(g5["notes"]) == 1 and len(g5["pool"].kinds("voice_ring")) == 1
    assert _followups(conv)[-1]["status"] == "skipped"


# (5) a G4 long job's final report is told ONCE - by the deliver node at job end, in the job's chat - and the
# kaam_followup row kaamwatch queued for the job's 'done' does not repeat it (no wake turn, no second ring)
def test_long_job_final_report_told_once(g5, monkeypatch):
    brain, tools = _setup(monkeypatch, True, SEG1 + SEG2 + [txt("(a second report)")], extra=_watched(monkeypatch))
    conv = g5["conv"]
    _job_turn(conv)
    g = _goal(conv)
    assert g["status"] == "done" and brain.calls == 5
    assert _shown(conv).count(FINAL) == 1
    rows = [f for f in _followups(conv) if f["key"] == f"goal:{g['id']}"]
    assert len(rows) == 1 and rows[0]["state"] == "done"            # kaamwatch DID queue its report
    for f in _followups(conv):
        if f["status"] == "pending":
            _send(f["id"])
    assert [f["status"] for f in _followups(conv) if f["key"] == f"goal:{g['id']}"] == ["skipped"]
    assert brain.calls == 5                                          # no wake turn
    assert _shown(conv).count(FINAL) == 1 and "(a second report)" not in _shown(conv)
    final = [n for n in g5["notes"] if FINAL in n[1]]
    assert len(final) == 1 and final[0][0] == conv                   # the job's own chat, once
    assert len(g5["pool"].kinds("voice_ring")) == 1                  # a background round ended it: ONE ring
    assert len(g5["pool"].replies(FINAL)) == 1
    from app.agent import turndeliver as D
    assert D.told(f"goal:{g['id']}", "done")
    alias = [r for r in _deliveries(conv) if r["key"] == f"job:goal:{g['id']}:done"]
    run = [r for r in _deliveries(conv) if r["key"].startswith("turn:") and r["job_key"] == f"goal:{g['id']}"]
    assert len(alias) == 1 and alias[0]["told_by"] == run[0]["key"]  # told by the run that ended the job
    assert len(run) == 1 and run[0]["outcome"] == "done" and run[0]["channels"]["ring"]["state"] == "sent"


# (6) a stopped run: outcome = stopped (in the record), the stop line told once, and the goal's 'stopped' report is
# not told a second time by kaam_followup
def test_stopped_run_outcome_stopped_told_once(g5, monkeypatch):
    from app.agent import santosh

    def stop_on_search(name, ctx):
        if name == "google_search":
            santosh.stop(ctx.conversation_id)
    brain, tools = _setup(monkeypatch, True, SEG1 + SEG2, extra=_watched(monkeypatch), on_call=stop_on_search)
    conv = g5["conv"]
    _job_turn(conv)
    g = _goal(conv)
    assert g["status"] == "stopped" and brain.calls == 2
    recs = [r for r in _deliveries(conv) if r["kind"] in ("turn", "job") and r["thread"]]
    assert len(recs) == 1 and recs[0]["outcome"] == "stopped"
    stop_rows = [d for r, d in _rows(conv) if r == "assistant" and d and "stop" in d.lower()]
    assert len(stop_rows) == len(set(stop_rows))                     # no line twice
    n0 = len([d for r, d in _rows(conv) if r == "assistant" and d])
    for f in _followups(conv):
        if f["status"] == "pending":
            _send(f["id"])
    assert brain.calls == 2                                          # no wake turn for the stopped job
    assert len([d for r, d in _rows(conv) if r == "assistant" and d]) == n0
    assert [f["status"] for f in _followups(conv) if f["key"] == f"goal:{g['id']}"] == ["skipped"]
    from app.agent import turndeliver as D
    assert D.told(f"goal:{g['id']}", "stopped")


# (7a) push keeps today's gates: in her quiet hours the news push is HELD for the morning and the ring refused
def test_quiet_hours_hold_the_push_and_refuse_the_ring(g5, monkeypatch):
    from app import push
    brain, tools = _setup(monkeypatch, True, [txt(REPORT)], extra={"VOICE_RING_QUIET": "0-24", "PUSH_QUIET": "0-24"})
    conv = _new_conv()
    _send(_queue(conv))
    assert len(_replies(conv, REPORT)) == 1
    assert g5["pool"].sent == []                                     # nothing woke her phone
    assert any((e.get("payload") or {}).get("text") == REPORT for e in push._HELD.get("default", []))
    news = [r for r in _deliveries() if r["kind"] == "news"][0]
    assert news["channels"]["ring"]["state"] == "sent"               # tried once, the ring's own gate refused it
    assert len(g5["notes"]) == 1


# (7b) ...and on a live call: no push for what she hears, no ring over the call, the call gets the note once
def test_live_call_no_push_no_ring_one_note(g5, monkeypatch):
    from app import voice
    brain, tools = _setup(monkeypatch, True, [txt(REPORT)])
    conv = _new_conv()
    monkeypatch.setattr(voice, "ACTIVE", {conv: [(None, object())]})
    monkeypatch.setattr(voice, "card_news", lambda *a, **k: None)
    _send(_queue(conv))
    assert len(_replies(conv, REPORT)) == 1
    assert g5["pool"].replies(REPORT) == [] and g5["pool"].kinds("voice_ring") == []
    assert [c for c, _ in g5["notes"]] == [conv]


# (8) switch off: the old delivery paths, unchanged - no record, the timing check asked, the wake's own note + ring
def test_switch_off_keeps_the_old_delivery(g5, monkeypatch):
    from app import kaam_followup as K
    from app.agent import turngraph

    async def boom(*a, **k):
        raise AssertionError("graph ran with chat_graph off")
    monkeypatch.setattr(turngraph, "run_steps", boom)
    asked = []
    real = K._answered_since
    monkeypatch.setattr(K, "_answered_since", lambda *a, **k: asked.append(1) or real(*a, **k))
    brain, tools = _setup(monkeypatch, False, [txt(REPORT)])
    conv = _new_conv()
    _send(_queue(conv))
    assert brain.calls == 1 and len(_replies(conv, REPORT)) == 1
    assert asked == [1]                                              # the old 'already told?' guess decided
    assert _deliveries() == []                                       # no delivery record on the old path
    assert [c for c, _ in g5["notes"]] == [conv]                     # the wake's own call note
    assert len(g5["pool"].kinds("voice_ring")) == 1                  # _send's own ring
