"""v0.193.0 "HARNESS-3" - Phase 3 of the dsh / Claude Code harness study, made ADVANCED (owner: "user tell him
deploy several agents then it must do"):

1. the event-sourced session log (agent/eventlog.py): every turn / tool call / result / spawn / wake is one
   best-effort row in harness_events; the brain re-reads it with session_log; the console via GET /harness-events.
2. the AGENT TEAM (agent/team.py): deploy_agents runs SEVERAL sub-agents in PARALLEL, each with its own mini-loop,
   own admitted tool subset and own throwaway history; their deliverables come back in ONE tool result for the
   main brain to merge. Depth 1 (dsh): sub-agents never see deploy_agents / agent_status. Caps everywhere.
3. mode="background": the crew is persisted (agent_teams), the turn answers at once, a worker slot runs it, and
   completion flows through the EXISTING machinery - a bus "agent_team" event shaped by kaamwatch -> the v0.187
   result message -> the v0.192 WAKE turn with the real brain when the chat is idle. End-to-end monitoring of
   crews with zero new reporting code; agent_status action=stop is the crew's Rokiye.
"""
import asyncio
import time

import pytest
from sqlalchemy import select

import app.agent.santosh as santosh
import app.agent.team as team
import app.kaam_followup as kf
import app.kaamwatch as kw

from app.agent.eventlog import HarnessEvent
from app.agent.team import AgentTeam
from app.config import get_settings
from app.db import Conversation, session

from app.agent.tools import Ctx, dispatch
from tests.test_v0187_realtime import fu, tick_drain  # noqa: F401


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _unmute_eventlog():
    """The log self-mutes for 60 s after a write failure - never let one test's broken DB poison the next."""
    from app.agent import eventlog
    eventlog._muted_until = 0.0
    yield
    eventlog._muted_until = 0.0


def _conv(conv):
    with session() as sdb:
        if sdb.get(Conversation, conv) is None:
            sdb.add(Conversation(id=conv, tenant_id="default", title="t"))


def _ctx(conv="c_team", actor="owner"):
    _conv(conv)
    return Ctx(tenant_id="default", conversation_id=conv, actor=actor)


# ---------------- 1. the event-sourced session log ----------------

def test_eventlog_roundtrip_filters_and_brief(env):
    from app.agent import eventlog
    eventlog.log_event("default", "c_log", "tool_call", {"tool": "google_search", "args": {"q": "x"}}, "turn_1", "owner")
    eventlog.log_event("default", "c_log", "tool_result", {"tool": "google_search", "ok": True, "ms": 120}, "turn_1", "owner")
    eventlog.log_event("default", "c_log", "agent_finished", {"agent": "scout", "ok": True}, "turn_1", "team:scout")
    rows = eventlog.recent("c_log")
    assert [r["kind"] for r in rows] == ["tool_call", "tool_result", "agent_finished"]   # oldest last
    only = eventlog.recent("c_log", kinds=["tool_result"])
    assert [r["kind"] for r in only] == ["tool_result"]
    one = eventlog.recent("c_log", turn_id="turn_1")
    assert len(one) == 3
    assert eventlog.recent("c_log", turn_id="turn_x") == []
    b = eventlog.brief("c_log")
    assert "tool_call" in b and "google_search" in b and "[owner]" in b and "[team:scout]" in b
    assert eventlog.recent("c_missing") == []


def test_eventlog_never_raises_and_self_mutes(monkeypatch):
    from app.agent import eventlog
    real_session = eventlog.session

    def broken():
        raise RuntimeError("db gone")

    monkeypatch.setattr(eventlog, "session", broken)
    eventlog.log_event("default", "c_mute", "tool_call", {"tool": "x"})     # must swallow
    assert eventlog.STATS["failed"] >= 1
    assert eventlog.stats()["muted_now"] is True
    n = len(eventlog.recent("c_mute"))                                      # nothing was written
    assert n == 0
    monkeypatch.setattr(eventlog, "session", real_session)
    eventlog._muted_until = 0.0                                             # un-mute for the other tests
    eventlog.log_event("default", "c_mute", "tool_call", {"tool": "x"})
    assert len(eventlog.recent("c_mute")) == 1


def test_eventlog_per_conv_cap_and_retention(env, monkeypatch):
    from app.agent import eventlog
    monkeypatch.setattr(eventlog, "MAX_PER_CONV", 5)
    for i in range(8):
        eventlog.log_event("default", "c_cap", "tool_call", {"tool": f"t{i}"})
    rows = eventlog.recent("c_cap", limit=100)
    assert len(rows) <= 5 and rows[-1]["payload"]["tool"] == "t7"            # newest survive, oldest trimmed
    import datetime as _dt
    from app.db import now as _now
    eventlog.log_event("default", "c_old", "turn_started", {"line": "purana"})
    with session() as sdb:
        r = sdb.scalars(select(HarnessEvent).where(HarnessEvent.conversation_id == "c_old")).first()
        r.created_at = _now() - _dt.timedelta(days=30)
    assert eventlog.forget_old(14) >= 1
    assert eventlog.recent("c_old") == []


def test_run_tool_writes_the_session_log(env, monkeypatch):
    calls = []

    async def fake_dispatch(name, args, ctx):
        calls.append(name)
        return {"tool": name, "found": "X"}

    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    from app.agent import eventlog
    token = eventlog.CURRENT.set({"turn_id": "turn_tool", "actor": "owner"})
    try:
        out = run(santosh._run_tool("google_search", {"q": "jaipur weather"}, _ctx(), get_settings()))
        assert out["found"] == "X"
        async def boom(*a, **k):
            raise ValueError("nope")
        monkeypatch.setattr(santosh, "dispatch", boom)
        with pytest.raises(ValueError):
            run(santosh._run_tool("google_search", {}, _ctx(), get_settings()))
    finally:
        eventlog.CURRENT.reset(token)
    rows = eventlog.recent("c_team")
    kinds = [(r["kind"], r["payload"].get("tool"), r["payload"].get("ok")) for r in rows]
    assert ("tool_call", "google_search", None) in kinds
    assert ("tool_result", "google_search", True) in kinds
    assert ("tool_result", "google_search", False) in kinds                 # the crash was logged too
    assert all(r["turn"] == "turn_tool" and r["actor"] == "owner" for r in rows)


# ---------------- 2. the inline agent team ----------------

class BrainScript:
    """Scripted brains: per agent name, a list of (blocks, stop). Records the tools each agent saw."""
    def __init__(self):
        self.script: dict[str, list] = {}
        self.saw_tools: dict[str, list] = []
        self.calls: list[str] = []

    async def __call__(self, brain, system, history, settings, tools=None, live=None, max_tokens=None):
        name = "unknown"
        for k in self.script:
            if f'You are "{k}"' in system:
                name = k
                break
        self.calls.append(name)
        self.saw_tools.append([t["name"] for t in (tools or [])])
        step = self.script.get(name, [])
        if not step:
            return [{"type": "text", "text": f"(no script for {name})"}], "end_turn"
        blocks, stop = step.pop(0)
        return blocks, stop


def _scripted(script: BrainScript, tool_sleep: float = 0.0):
    async def fake_dispatch(name, args, ctx):
        if tool_sleep:
            await asyncio.sleep(tool_sleep)
        return {"tool": name, "data": "D"}

    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        return await script(brain, system, history, settings, tools, live, max_tokens)

    return fake_brain, fake_dispatch


def test_inline_team_runs_agents_in_parallel_and_merges_deliverables(monkeypatch):
    s = get_settings()
    s.agent_team = True
    script = BrainScript()
    for name in ("scout", "reader", "counter"):
        script.script[name] = [
            ([{"type": "tool_use", "id": "t1", "name": "google_search", "input": {"q": name}}], "tool_use"),
            ([{"type": "text", "text": f"{name} ka deliverable: 42 points"}], "end_turn"),
        ]
    fake_brain, fake_dispatch = _scripted(script, tool_sleep=0.8)
    monkeypatch.setattr(santosh, "_call_brain", fake_brain)
    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    ctx = _ctx()
    t0 = time.time()
    out = run(dispatch("deploy_agents", {"mission": "teen jagah se data lao", "mode": "inline",
                                         "agents": [{"name": "scout", "task": "site 1"},
                                                    {"name": "reader", "task": "site 2"},
                                                    {"name": "counter", "task": "site 3"}]}, ctx))
    took = time.time() - t0
    assert took < 2.0, f"agents did not run together (took {took:.2f}s; serial floor is ~2.4s)"
    assert out["mode"] == "inline" and out["team"]
    dels = {a["name"]: a for a in out["agents"]}
    assert dels["scout"]["ok"] and "42 points" in dels["scout"]["deliverable"]
    assert dels["reader"]["ok"] and dels["counter"]["ok"]
    assert "SACH" in out["note"] or "deliverables" in out["note"]
    assert ctx.team_used == 3
    from app.agent import eventlog
    evs = [e["kind"] for e in eventlog.recent("c_team")]
    assert evs.count("agent_spawned") == 3 and evs.count("agent_finished") == 3 and "team_synthesized" in evs


def test_depth1_subagents_never_see_the_team_tools(monkeypatch):
    s = get_settings()
    script = BrainScript()
    script.script["solo"] = [([{"type": "text", "text": "done"}], "end_turn")]
    fake_brain, fake_dispatch = _scripted(script)
    monkeypatch.setattr(santosh, "_call_brain", fake_brain)
    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    run(dispatch("deploy_agents", {"mission": "ek agent", "mode": "inline",
                                   "agents": [{"name": "solo", "task": "bas dekho",
                                              "tools": ["email", "sheets"]}]}, _ctx()))
    tools_seen = script.saw_tools[0]
    assert "deploy_agents" not in tools_seen and "agent_status" not in tools_seen    # depth 1 (dsh)
    assert "tool_search" in tools_seen                                               # the escape hatch stays
    assert "email_check" in tools_seen and "sheet_update" in tools_seen              # requested families arrived


def test_caps_per_deploy_per_turn_and_actor_refusals(monkeypatch):
    s = get_settings()
    old_cap = s.team_max_agents
    s.team_max_agents = 4
    try:
        script = BrainScript()
        fake_brain, fake_dispatch = _scripted(script)
        monkeypatch.setattr(santosh, "_call_brain", fake_brain)
        monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
        ctx = _ctx()
        six = [{"name": f"a{i}", "task": "t"} for i in range(6)]
        out = run(dispatch("deploy_agents", {"mission": "m", "mode": "inline", "agents": six}, ctx))
        assert len(out["agents"]) == 4 and "4 chal rahe" in out["note"]
        out2 = run(dispatch("deploy_agents", {"mission": "m", "mode": "inline", "agents": six}, ctx))
        assert len(out2["agents"]) == 4                     # room 8 - 4 = 4
        out3 = run(dispatch("deploy_agents", {"mission": "m", "mode": "inline", "agents": six}, ctx))
        assert out3["note"] and "budget" in out3["note"]    # the turn's 8-agent budget is spent
        # actors: staff (via the employee gate) and wake (at the handler) never deploy
        with pytest.raises(Exception) as ei:
            run(dispatch("deploy_agents", {"mission": "m", "agents": [{"name": "x", "task": "t"}]},
                         _ctx(actor="staff:e1")))
        assert "band" in str(ei.value) or "Employee" in str(ei.value)   # the gate refuses staff first
        wake = run(team.deploy_agents(_ctx(actor="wake"), mission="m", agents=[{"name": "x", "task": "t"}]))
        assert "wake" in wake["note"]
        empty = run(dispatch("deploy_agents", {"mission": "", "agents": []}, _ctx()))
        assert "mission" in empty["note"]
        assert team.STATS["refused"] >= 2
    finally:
        s.team_max_agents = old_cap


def test_one_agent_failing_never_kills_the_crew(monkeypatch):
    script = BrainScript()
    for name in ("good1", "bad", "good2"):
        script.script[name] = [
            ([{"type": "tool_use", "id": "t1", "name": "google_search", "input": {}}], "tool_use"),
            ([{"type": "text", "text": f"{name} ho gaya"}], "end_turn"),
        ]
    fake_brain, fake_dispatch = _scripted(script)

    async def brain_with_one_crash(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        if 'You are "bad"' in system:
            raise RuntimeError("brain exploded")
        return await fake_brain(brain, system, history, settings, tools, live, max_tokens)

    monkeypatch.setattr(santosh, "_call_brain", brain_with_one_crash)
    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    out = run(dispatch("deploy_agents", {"mission": "m", "mode": "inline",
                                         "agents": [{"name": "good1", "task": "t"}, {"name": "bad", "task": "t"},
                                                    {"name": "good2", "task": "t"}]}, _ctx()))
    dels = {a["name"]: a for a in out["agents"]}
    assert dels["good1"]["ok"] and dels["good2"]["ok"]
    assert not dels["bad"]["ok"] and "crash" in dels["bad"]["deliverable"].lower() or "exploded" in dels["bad"]["deliverable"]
    assert "fail" in out["note"].lower() or "agent fail" in out["note"]


def test_rokiye_stops_an_inline_crew(monkeypatch):
    script = BrainScript()
    for name in ("slow1", "slow2"):
        script.script[name] = [
            ([{"type": "tool_use", "id": "t1", "name": "google_search", "input": {}}], "tool_use"),
            ([{"type": "text", "text": f"{name} done"}], "end_turn"),
        ]
    fake_brain, _ = _scripted(script)
    monkeypatch.setattr(santosh, "_call_brain", fake_brain)

    async def slow_dispatch(name, args, ctx):
        await asyncio.sleep(3.0)                 # the tool is still running when she taps Rokiye
        return {"tool": name}

    monkeypatch.setattr(santosh, "dispatch", slow_dispatch)
    conv = "c_stop"
    ctx = _ctx(conv)

    async def go():
        task = asyncio.ensure_future(dispatch("deploy_agents", {"mission": "m", "mode": "inline",
                                                                "agents": [{"name": "slow1", "task": "t"},
                                                                           {"name": "slow2", "task": "t"}]}, ctx))
        await asyncio.sleep(0.6)                 # the agents are inside their tool call now
        santosh._stopped.add(conv)               # Rokiye
        return await task

    try:
        out = run(go())
        dels = out["agents"]
        assert all(not a["ok"] for a in dels)    # stopped agents deliver nothing
        assert team.STATS["stopped"] >= 2
    finally:
        santosh._stopped.discard(conv)


# ---------------- 3. background crews + the wake lane ----------------

class BusSpy:
    def __init__(self, real):
        self.real = real
        self.calls = []

    def publish(self, *a, **k):
        self.calls.append((a, k))
        return self.real.publish(*a, **k)


def test_background_deploy_queues_fast_and_the_slot_runs_the_crew(env, monkeypatch):
    conv = "c_bg"
    _conv(conv)
    spy = BusSpy(team.bus)
    monkeypatch.setattr(team, "bus", spy)
    results = [{"name": "a", "ok": True, "stopped": False, "seconds": 1.0, "tools": [],
                "deliverable": "sheet mein 120 rows mile"},
               {"name": "b", "ok": True, "stopped": False, "seconds": 1.2, "tools": [],
                "deliverable": "mail mein 3 unpaid"}]

    async def fake_crew(specs, team_id, mission, fams, tenant, cv, turn_id, settings, shared=None, on_done=None):
        return results

    monkeypatch.setattr(team, "_run_crew", fake_crew)
    ctx = _ctx(conv)
    out = run(dispatch("deploy_agents", {"mission": "sales report nikalo", "mode": "background",
                                         "agents": [{"name": "a", "task": "sheet dekho"},
                                                    {"name": "b", "task": "mail dekho"}]}, ctx))
    assert out["mode"] == "background" and out["team"]
    assert "ABHI" in out["note"] and "agent_status" in out["note"]
    tid = out["team"]
    with session() as sdb:
        row = sdb.get(AgentTeam, tid)
    assert row.status == "queued"
    started = [a for a, k in spy.calls if a[1] == "agent_team" and a[2].get("status") == "started"]
    assert started and started[0][2]["id"] == tid
    # the worker slot runs it
    run(team.tick())
    async def drain():
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    run(drain())
    with session() as sdb:
        row = sdb.get(AgentTeam, tid)
    assert row.status == "done" and "120 rows" in row.result and "3 unpaid" in row.result
    done_ev = [a for a, k in spy.calls if a[1] == "agent_team" and a[2].get("status") == "done"]
    assert done_ev and "120 rows" in done_ev[0][2]["say"]
    # agent_status re-reads the deliverables
    st = run(dispatch("agent_status", {"action": "check"}, _ctx(conv)))
    assert st["teams"][0]["id"] == tid and "120 rows" in st["teams"][0]["deliverables"]


def test_background_crew_reports_through_the_wake_lane(fu, monkeypatch):  # noqa: F811
    conv = fu["conv"]
    wake_texts = []

    async def fake_turn(cv, text, tenant_id=None, actor="owner", **kw2):
        wake_texts.append({"actor": actor, "text": text})
        return "Team ka kaam poora: sheet 120 rows, mail 3 unpaid."

    monkeypatch.setattr(santosh, "run_turn", fake_turn)

    async def fake_crew(specs, team_id, mission, fams, tenant, cv, turn_id, settings, shared=None, on_done=None):
        return [{"name": "sheet-bot", "ok": True, "stopped": False, "seconds": 1.0, "tools": [],
                 "deliverable": "Sheet: 120 naye rows"}]

    monkeypatch.setattr(team, "_run_crew", fake_crew)
    out = run(dispatch("deploy_agents", {"mission": "roz ki report", "mode": "background",
                                         "agents": [{"name": "sheet-bot", "task": "sheet read"}]}, _ctx(conv)))
    tid = out["team"]
    run(team.tick())
    async def drain():
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    run(drain())
    # the crew's own "done" event reached kaamwatch -> the followup queue
    with session() as sdb:
        pend = sdb.scalars(select(kf.KaamFollowup).where(kf.KaamFollowup.conversation_id == conv)).all()
    assert pend and pend[0].state == "done" and "120 naye rows" in pend[0].detail
    # the worker slot reports it: the REAL brain is woken with the result (idle chat, fresh budget)
    kf.wake_reset(conv)
    tick_drain()
    assert wake_texts and wake_texts[0]["actor"] == "wake"
    assert "120 naye rows" in wake_texts[0]["text"] and "Agent team" in wake_texts[0]["text"]
    assert not fu["notices"]                  # the wake turn replaces the one-shot line
    with session() as sdb:
        row = sdb.get(AgentTeam, tid)
    assert row.status == "done"


def test_stale_running_crew_is_recovered_once(env, monkeypatch):
    import datetime as _dt
    from app.db import now as _now
    conv = "c_stale"
    _conv(conv)
    with session() as sdb:
        row = AgentTeam(tenant_id="default", conversation_id=conv, mission="m",
                        spec='{"mission": "m", "agents": [{"name": "a", "task": "t"}]}', status="running", tries=0)
        sdb.add(row)
        sdb.flush()
        old = _now() - _dt.timedelta(minutes=20)
        row.updated_at = old
        tid = row.id
    seen = []

    async def fake_crew(specs, team_id, mission, fams, tenant, cv, turn_id, settings, shared=None, on_done=None):
        seen.append(team_id)
        assert shared["check_stopped"]() is False
        return [{"name": "a", "ok": True, "stopped": False, "seconds": 0.1, "tools": [], "deliverable": "ho gaya"}]

    monkeypatch.setattr(team, "_run_crew", fake_crew)
    assert run(team.tick()) >= 1
    async def drain():
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    run(drain())
    assert seen == [tid]
    with session() as sdb:
        row = sdb.get(AgentTeam, tid)
    assert row.status == "done" and row.tries == 1
    assert run(team.tick()) == 0              # done: never twice


def test_agent_status_stops_a_running_crew_and_the_runner_bails(env, monkeypatch):
    conv = "c_teamstop"
    _conv(conv)
    with session() as sdb:
        row = AgentTeam(tenant_id="default", conversation_id=conv, mission="lamba kaam",
                        spec='{"mission": "lamba kaam", "agents": [{"name": "a", "task": "t"}]}', status="running")
        sdb.add(row)
        sdb.flush()
        tid = row.id
    steps = {"n": 0}

    async def fake_crew(specs, team_id, mission, fams, tenant, cv, turn_id, settings, shared=None, on_done=None):
        for _ in range(20):
            if shared["check_stopped"]():
                return [{"name": "a", "ok": False, "stopped": True, "seconds": 0.1, "tools": [],
                         "deliverable": "roka gaya"}]
            steps["n"] += 1
            await asyncio.sleep(0.02)
        return []

    monkeypatch.setattr(team, "_run_crew", fake_crew)

    async def go():
        t = asyncio.ensure_future(team.run_background(tid))
        await asyncio.sleep(0.1)
        out = await dispatch("agent_status", {"action": "stop", "id": tid}, _ctx(conv))
        await t
        return out

    out = run(go())
    assert "roka gaya" in out["note"] or "rok" in out["note"]
    assert steps["n"] < 20                    # the runner really bailed early
    with session() as sdb:
        row = sdb.get(AgentTeam, tid)
    assert row.status == "stopped"
    again = run(dispatch("agent_status", {"action": "stop", "id": tid}, _ctx(conv)))
    assert "pehle hi" in again["note"]


def test_session_log_tool_reads_the_log(env):
    from app.agent import eventlog
    eventlog.log_event("default", "c_slog", "tool_call", {"tool": "google_search"}, "turn_9", "owner")
    eventlog.log_event("default", "c_slog", "tool_result", {"tool": "google_search", "ok": True}, "turn_9", "owner")
    out = run(dispatch("session_log", {"limit": 10}, _ctx("c_slog")))
    assert out["count"] >= 2 and "tool_call" in out["log"] and "google_search" in out["log"]
    out2 = run(dispatch("session_log", {"kinds": "tool_result"}, _ctx("c_slog")))
    assert "tool_result" in out2["log"] and "tool_call" not in out2["log"]


def test_kaamwatch_shapes_the_agent_team_events():
    w = kw.shape("agent_team", {"id": "tm1", "number": "team 4f2a", "name": "sales report",
                                "status": "started", "stage": "3 agents lage hain"})
    assert w and w["state"] == "working" and w["label"] == "Agent team" and w["key"] == "agent_team:tm1"
    d = kw.shape("agent_team", {"id": "tm1", "number": "team 4f2a", "name": "sales report",
                                "status": "done", "say": "120 rows mile"})
    assert d["state"] == "done" and "120 rows" in d["detail"]
    s = kw.shape("agent_team", {"id": "tm2", "name": "x", "status": "stopped", "say": "owner ne rok diya"})
    assert s["state"] == "stopped"


def test_admission_carries_the_team_family():
    from app.agent import admit
    s = get_settings()
    names = {t["name"] for t in admit.plan_for("3 agents lagao research ke liye", s).specs()}
    assert {"deploy_agents", "agent_status", "session_log"} <= names
    core = {t["name"] for t in admit.plan_for("hello ji", s).specs()}
    assert "deploy_agents" in core and "session_log" in core    # first-class: always visible


# ---------------- version ----------------

def test_version_and_config():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.310.0"
    s = get_settings()
    assert s.agent_team is True
    assert s.team_max_agents == 4
    assert s.team_agent_max_steps == 8
    assert s.team_agent_timeout_s == 240
    assert s.team_background is True
    assert s.team_bg_max_running == 2
    assert s.agent_event_log is True
    assert s.event_log_retain_days == 14
