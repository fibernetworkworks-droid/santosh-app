"""G4 of docs/LANGGRAPH_TURN_PLAN.md: a long job is ONE graph thread continuing (`chat_graph` on).

A kaam_plan job with more steps than one turn's step budget (AGENT_GOAL_MAX_STEPS=3 here) runs in SEGMENTS of the same
thread "<conv>:job-<goal id>": the first turn stops at the `carry` boundary (checkpointed), the job's round resumes the
thread with ainvoke(None) instead of starting a fresh turn that re-reads the chat. Fake brain / fake tools in the style
of test_g0 .. test_g3 (kaam_plan itself is the real tool, so the goal, its steps, its limits and its finish are real).
A restart is simulated as in test_g1: a CancelledError at the chosen point, the in-memory state wiped, the recovery
sweep (goal.recover_tick) run in a FRESH event loop."""
import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, _settings, tu, txt

CRASH = "CRASH"
FINAL = "Yeh raha natija: ek, do aur teen ke jawab neeche hain."
ASK = "Mera lamba kaam karo: pehle ek dhoondo, phir do dekho, phir teen likho"


@pytest.fixture
def gz(bz, monkeypatch):  # noqa: F811
    """bz + no background chat titling (it would borrow the scripted brain) + rounds start at once."""
    from app import chats
    from app.agent import goal
    monkeypatch.setattr(chats, "enabled", lambda: False)
    monkeypatch.setattr(goal, "ROUND_DELAY_S", 0.0)
    goal._PENDING.clear()
    goal._STOPPED.clear()
    yield bz
    goal._PENDING.clear()
    goal._STOPPED.clear()


class Brain:
    """Scripted brain (sequential); a CRASH step raises CancelledError (the process dies during that model call)."""

    def __init__(self, script):
        self.script = list(script)
        self.sent: list[str] = []
        self.messages = SimpleNamespace(create=self._create)

    @property
    def calls(self):
        return len(self.sent)

    async def _create(self, **kw):
        self.sent.append(json.dumps(kw.get("messages"), ensure_ascii=False, default=str))
        step = self.script.pop(0) if self.script else txt("(script ended)")
        if step == CRASH:
            raise asyncio.CancelledError()
        stop = "tool_use" if any(b["type"] == "tool_use" for b in step) else "end_turn"
        return SimpleNamespace(content=json.loads(json.dumps(step)), stop_reason=stop)


class Tools:
    """kaam_plan is the REAL tool; every other tool is fake and counted. `crash` = CancelledError on the first call
    (the process dies mid-tool), `slow` = seconds on the first call, `on_call(name, ctx)` after a fake tool's work."""

    def __init__(self, real, crash=(), slow=None, on_call=None):
        self.real = real
        self.crash = set(crash)
        self.slow = dict(slow or {})
        self.on_call = on_call
        self.count: dict[str, int] = {}

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name == "kaam_plan":
            return await self.real(name, args, ctx)
        if name in self.crash:
            self.crash.discard(name)
            raise asyncio.CancelledError()
        if self.slow.get(name):
            await asyncio.sleep(self.slow.pop(name))
        if self.on_call:
            self.on_call(name, ctx)
        return {"ok": True, "tool": name, "rows": [1, 2, 3]}


def _setup(monkeypatch, graph, script, extra=None, **tool_kw):
    _settings(monkeypatch, graph, {"AGENT_GOAL_MAX_STEPS": "3", "AGENT_STEER": "false", "QUICK_LANE": "false",
                                   **(extra or {})})
    from app.agent import santosh, set_client
    tools = Tools(santosh.dispatch, **tool_kw)
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    brain = Brain(script)
    set_client(brain)
    return brain, tools


async def _quiet(limit_s: float = 60.0):
    """Wait until no round of any job is scheduled or running."""
    from app.agent import goal
    loop = asyncio.get_running_loop()
    end = loop.time() + limit_s
    while loop.time() < end:
        if not goal._PENDING:
            await asyncio.sleep(0.1)
            if not goal._PENDING:
                return
        await asyncio.sleep(0.05)
    raise AssertionError(f"rounds never finished: {goal._PENDING}")


def _owned(conv, rid, ask):
    from app import turn_inbox as ti
    return ti.run_owned(rid, conv, ask, "default", False, client_id="c-" + rid)


def _accept(conv, ask, cid="c-1"):
    from app import turn_inbox as ti
    return ti.accept("default", conv, ask, False, "", cid)


def _job_turn(conv, ask=ASK):
    """Her ask through the inbox, then every round of the job."""
    async def go():
        out = await _owned(conv, _accept(conv, ask), ask)
        await _quiet()
        return out
    return asyncio.run(asyncio.wait_for(go(), 120))


def _goal(conv):
    from app.agent import goal
    from app.db import session
    with session() as s:
        r = s.scalars(select(goal.GoalRun).where(goal.GoalRun.conversation_id == conv)
                      .order_by(goal.GoalRun.updated_at.desc())).first()
        return goal._row_view(r) if r is not None else None


def _job_next(conv):
    from app.agent import turngraph
    from app.config import get_settings
    g = _goal(conv)
    return asyncio.run(turngraph.job_next(get_settings(), conv, g["id"])) if g else None


def _checkpoints(conv):
    from app.agent import turngraph
    from app.config import get_settings
    return asyncio.run(turngraph.checkpoints(get_settings(), conv))


def _restart():
    """What a pm2 restart wipes: the chat locks, stop marks, the graph's live objects, the rounds in flight."""
    from app.agent import goal, santosh, turngraph
    santosh._locks.clear()
    santosh._stopped.clear()
    turngraph._RUNS.clear()
    turngraph._CUT.clear()
    goal._PENDING.clear()


def _age_goal(conv, minutes=30):
    from app.agent import goal
    from app.db import now, session
    with session() as s:
        r = s.scalars(select(goal.GoalRun).where(goal.GoalRun.conversation_id == conv)).first()
        r.updated_at = now() - timedelta(minutes=minutes)


def _shown(conv):
    return [d for r, d in _rows(conv) if r == "assistant" and d and not d.startswith("(Kaam:")]


def _first(sent: str) -> list:
    """The texts of the first message the model got (the prompt-cache marker that rides the newest block left out)."""
    c = json.loads(sent)[0]["content"]
    return [c] if isinstance(c, str) else [b.get("text") for b in c if isinstance(b, dict)]


def _ids_in(sent: str, i: int) -> int:
    return sent.count(f'"id": "tu_{i}"')


SEG1 = [[tu(1, "kaam_plan", action="set", goal="Teen kadam ka kaam", steps=["ek dhoondo", "do dekho", "teen likho"])],
        [tu(2, "kaam_plan", action="step", n=1, state="done"), tu(3, "google_search", query="ek")],
        [tu(4, "maps_search", query="do"), tu(5, "kaam_plan", action="step", n=2, state="done")]]
SEG2 = [[tu(6, "kaam_plan", action="step", n=3, state="done"),
         tu(7, "kaam_plan", action="finish", outcome="done", reason="teeno kadam")],
        txt(FINAL)]


# (1) a 3-step job that needs 2 segments finishes on ONE thread: no tool twice, one final report
def test_two_segments_one_thread_no_repeats_one_report(gz, monkeypatch):  # noqa: F811
    from app.agent import turngraph
    brain, tools = _setup(monkeypatch, True, SEG1 + SEG2)
    s0 = dict(turngraph.STATS)
    conv = gz["conv"]
    _job_turn(conv)
    assert brain.calls == 5                                        # 3 in segment 1, 2 in segment 2
    assert tools.count == {"kaam_plan": 5, "google_search": 1, "maps_search": 1}
    assert turngraph.STATS["copied"] == s0["copied"] + 1           # her inbox turn's state went onto the job thread
    assert turngraph.STATS["job_resumed"] == s0["job_resumed"] + 1  # the round CONTINUED it (no fresh turn)
    assert turngraph.STATS["segments"] == s0["segments"] + 1
    assert turngraph.STATS["job_fresh"] == s0["job_fresh"]
    seg2 = brain.sent[3]
    # the same thread: segment 2 starts from segment 1's own messages - her first message still carries the memory
    # block it had in segment 1 (a fresh round re-reads the chat, where her row has no memory block)
    assert _first(seg2) == _first(brain.sent[0])
    assert all(_ids_in(seg2, i) == 1 for i in range(1, 6))         # every earlier step exactly once
    assert "[Goal jaari" in seg2                                    # the round's own line is the new segment's ask
    g = _goal(conv)
    assert g["status"] == "done"
    shown = _shown(conv)
    assert shown.count(FINAL) == 1 and shown[-1] == FINAL           # ONE final report
    assert [d for r, d in _rows(conv) if r == "user" and d] == [ASK]   # the round's line is never shown as hers
    assert _checkpoints(conv) == []                                # job over: no thread left behind


# (2) a restart BETWEEN segments: the recovery sweep continues the parked job thread (nothing redone, no RESUME_NOTE)
def test_restart_between_segments_continues_the_job_thread(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, turngraph
    brain, tools = _setup(monkeypatch, True, SEG1 + SEG2)
    real_schedule = goal._schedule
    monkeypatch.setattr(goal, "_schedule", lambda *a, **k: True)   # the process dies before the round starts
    conv = gz["conv"]
    _job_turn(conv)
    assert brain.calls == 3 and _job_next(conv) == "carry"
    monkeypatch.setattr(goal, "_schedule", real_schedule)
    _restart()
    _age_goal(conv)
    s0 = dict(turngraph.STATS)

    async def recover():
        n = goal.recover_tick()
        await _quiet()
        return n
    assert asyncio.run(recover()) == 1
    assert turngraph.STATS["job_resumed"] == s0["job_resumed"] + 1
    assert tools.count == {"kaam_plan": 5, "google_search": 1, "maps_search": 1}
    assert not any("Server restart" in m for m in brain.sent)      # no RESUME_NOTE re-run
    assert _goal(conv)["status"] == "done"
    assert any("server restarted" in d.lower() for r, d in _rows(conv) if d)   # the honest recovery note


# (3) a restart MID-TOOL in segment 2: it continues from that step - finished steps not redone, the cut send ambiguous
def test_restart_mid_tool_in_a_later_segment(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, toolledger as L, turngraph
    line = "Ravi wala mail shayad ja chuka hai - pehle sent folder dekhna hoga."
    script = SEG1 + [[tu(6, "email_send", to="ravi@x.in"), tu(7, "list_reminders")],
                     [tu(8, "kaam_plan", action="step", n=3, state="done"),
                      tu(9, "kaam_plan", action="finish", outcome="done", reason="teeno kadam")],
                     txt(line)]
    brain, tools = _setup(monkeypatch, True, script, crash=("email_send",))
    conv = gz["conv"]
    _job_turn(conv)                                                # segment 1 ok, segment 2 dies inside email_send
    assert brain.calls == 4 and tools.count.get("email_send") == 1
    assert _job_next(conv) == "tools"                              # the job thread holds the cut step
    _restart()
    _age_goal(conv)
    a0, j0 = L.STATS["ambiguous"], turngraph.STATS["job_resumed"]

    async def recover():
        n = goal.recover_tick()
        await _quiet()
        return n
    assert asyncio.run(recover()) == 1
    assert turngraph.STATS["job_resumed"] == j0 + 1
    assert tools.count["email_send"] == 1                          # the cut send is NEVER sent again
    assert L.STATS["ambiguous"] == a0 + 1
    assert tools.count["list_reminders"] == 1
    assert tools.count["google_search"] == 1 and tools.count["maps_search"] == 1   # segment 1 not redone
    assert "MAY ALREADY HAVE RUN" in brain.sent[4]                  # the resumed step's model call saw it honestly
    assert not any("Server restart" in m for m in brain.sent)
    assert _goal(conv)["status"] == "done"
    assert _shown(conv)[-1] == line


# (4) Stop mid-job ends the whole job: no continuation runs, no thread kept
def test_stop_mid_job_ends_it(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh

    def stop_on_search(name, ctx):
        if name == "google_search":
            santosh.stop(ctx.conversation_id)
    brain, tools = _setup(monkeypatch, True, SEG1 + SEG2, on_call=stop_on_search)
    conv = gz["conv"]
    _job_turn(conv)
    assert brain.calls == 2                                        # nothing after her Stop, no round
    assert "maps_search" not in tools.count
    assert _goal(conv)["status"] == "stopped"
    assert _job_next(conv) is None and _checkpoints(conv) == []


# (4b) Stop while the job waits between segments: the waiting round does nothing and the parked thread goes
def test_stop_between_segments_drops_the_parked_job(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, santosh
    brain, tools = _setup(monkeypatch, True, SEG1 + SEG2)
    real_schedule = goal._schedule
    monkeypatch.setattr(goal, "_schedule", lambda *a, **k: True)
    conv = gz["conv"]
    _job_turn(conv)
    gid = _goal(conv)["id"]
    assert _job_next(conv) == "carry"
    monkeypatch.setattr(goal, "_schedule", real_schedule)
    santosh.stop(conv)
    asyncio.run(goal._continuation(conv, "default", "[Goal jaari: x]", gid, "goal"))
    assert brain.calls == 3                                        # the round ran nothing
    assert _goal(conv)["status"] == "stopped"
    assert _checkpoints(conv) == []


# (5) her new message while the job waits for its next round: it runs FIRST (arrival order), the job then continues
# from her turn's state (her words in it, nothing doubled)
def test_her_message_between_segments_runs_first_then_the_job_continues(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, turngraph
    her = "Status kya hai? Teesra kadam bhi dekh lo"
    script = SEG1 + [txt("Do kadam ho chuke hain, teesra baaki hai."),          # her turn: answer -> plan nudge
                     [tu(6, "google_search", query="teen")],
                     txt("Teesre kadam par kaam chal raha hai."),               # -> nudge -> step budget spent
                     [tu(7, "kaam_plan", action="step", n=3, state="done"),   # the job's next segment
                      tu(8, "kaam_plan", action="finish", outcome="done", reason="teeno kadam")],
                     txt(FINAL)]
    brain, tools = _setup(monkeypatch, True, script)
    monkeypatch.setattr(goal, "ROUND_DELAY_S", 0.5)
    conv = gz["conv"]
    s0 = dict(turngraph.STATS)

    async def go():
        await _owned(conv, _accept(conv, ASK, "c-1"), ASK)          # segment 1; the round now waits 0.5 s
        assert goal._PENDING
        await _owned(conv, _accept(conv, her, "c-2"), her)          # her message arrives before the round starts
        await _quiet()
    asyncio.run(asyncio.wait_for(go(), 120))
    assert brain.calls == 8
    assert her in brain.sent[3] and "[Goal jaari" not in brain.sent[3]   # her turn ran before the round
    seg = brain.sent[6]
    assert "[Goal jaari" in seg and her in seg                     # the job continued from HER turn's state
    assert all(_ids_in(seg, i) == 1 for i in range(1, 7))          # nothing doubled by the hand-over
    assert turngraph.STATS["copied"] == s0["copied"] + 2           # segment 1, then her turn, went onto the job thread
    assert turngraph.STATS["job_resumed"] == s0["job_resumed"] + 1
    assert tools.count == {"kaam_plan": 5, "google_search": 2, "maps_search": 1}
    assert _goal(conv)["status"] == "done"
    assert _shown(conv).count(FINAL) == 1


# (6) the job's overall limit asks "Shall I carry on?" instead of looping; her yes continues the SAME thread
def test_overall_limit_asks_then_her_yes_continues_the_thread(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, turngraph
    script = [[tu(1, "kaam_plan", action="set", goal="Chaar kadam", steps=["ek", "do", "teen", "char"])],
              [tu(2, "kaam_plan", action="step", n=1, state="done"), tu(3, "google_search", query="ek")],
              # round 1 (segment 2)
              [tu(4, "kaam_plan", action="step", n=2, state="done"), tu(5, "maps_search", query="do")],
              [tu(6, "kaam_plan", action="step", n=3, state="done")],
              # after her yes (segment 3)
              [tu(7, "kaam_plan", action="step", n=4, state="done"),
               tu(8, "kaam_plan", action="finish", outcome="done", reason="chaaron")],
              txt(FINAL)]
    brain, tools = _setup(monkeypatch, True, script, extra={"AGENT_GOAL_MAX_STEPS": "2", "AGENT_GOAL_ROUNDS": "2"})
    conv = gz["conv"]
    s0 = dict(turngraph.STATS)
    _job_turn(conv)
    g = _goal(conv)
    assert brain.calls == 4                                        # segment 1 + ONE round, then it stopped
    assert g["status"] == "blocked" and g["hold"] == "limit" and "Shall I carry on" in g["reason"]
    assert _job_next(conv) == "carry"                              # nothing thrown away: the thread waits

    async def yes():
        assert goal.continue_now("default", conv) is not None
        await _quiet()
    asyncio.run(yes())
    assert brain.calls == 6
    assert turngraph.STATS["job_resumed"] == s0["job_resumed"] + 2
    assert tools.count == {"kaam_plan": 6, "google_search": 1, "maps_search": 1}
    assert all(_ids_in(brain.sent[4], i) == 1 for i in range(1, 7))
    assert _goal(conv)["status"] == "done"
    assert _shown(conv).count(FINAL) == 1


# (7) a segment cut by its deadline is parked, and the next round continues from the cut step (budgets never kill)
def test_deadline_cut_segment_continues_from_the_cut_step(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh, toolledger as L, turngraph
    script = [SEG1[0], SEG1[1],
              [tu(4, "kaam_plan", action="step", n=2, state="done"), tu(5, "kaam_plan", action="step", n=3,
                                                                       state="done"),
               tu(6, "kaam_plan", action="finish", outcome="done", reason="teeno")],
              txt(FINAL)]
    brain, tools = _setup(monkeypatch, True, script, slow={"google_search": 5.0})
    orig = santosh._with_deadline
    monkeypatch.setattr(santosh, "_with_deadline", lambda coro, c, f, l: orig(coro, c, 1.5, 0))
    conv = gz["conv"]
    s0, r0, u0 = dict(turngraph.STATS), L.STATS["rerun_read"], L.STATS["reused"]
    _job_turn(conv)
    assert turngraph.STATS["cut_parked"] == s0["cut_parked"] + 1
    assert turngraph.STATS["job_resumed"] == s0["job_resumed"] + 1
    assert tools.count["google_search"] == 2                       # the cut look-up simply ran again
    assert L.STATS["rerun_read"] == r0 + 1
    assert L.STATS["reused"] >= u0 + 1                             # the finished kaam_plan step was not run again
    assert tools.count["kaam_plan"] == 5
    assert brain.calls == 4
    assert any(d.startswith("This round ran out of time") for d in _shown(conv))
    assert _goal(conv)["status"] == "done"


# (8) switch off: the old goal rounds, unchanged (a fresh round turn that re-reads the chat; no graph at all)
def test_switch_off_keeps_the_old_rounds(gz, monkeypatch):  # noqa: F811
    from app.agent import turngraph

    async def boom(*a, **k):
        raise AssertionError("graph ran with chat_graph off")
    monkeypatch.setattr(turngraph, "run_steps", boom)
    brain, tools = _setup(monkeypatch, False, SEG1 + SEG2)
    conv = gz["conv"]
    _job_turn(conv)
    assert brain.calls == 5
    assert tools.count == {"kaam_plan": 5, "google_search": 1, "maps_search": 1}
    assert _first(brain.sent[3]) != _first(brain.sent[0])   # the round re-read the chat
    assert "[Goal jaari" in brain.sent[3]
    assert _goal(conv)["status"] == "done"
    assert _shown(conv).count(FINAL) == 1
