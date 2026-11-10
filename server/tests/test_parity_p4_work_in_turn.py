"""PARITY Phase 4 (docs/CLAUDE_PARITY_PLAN.md, gaps 7 + 8): LONG WORK STAYS IN THE TURN.

Before: a big ask ("$5M AI SaaS idea") went to a BACKGROUND agent crew (mode=background) or a background research run;
the turn answered "the team is on it" and the real answer came back later through a wake turn (v0.722). Claude runs a
lead + parallel sub-agents INSIDE the turn and answers in the same reply. Now (`chat_work_in_turn`, default True):
her chat turn has a 20-minute budget and ~200 tool calls, deploy_agents / research_run run inside it (the long tool
clock), the crew's combined work is the reply - no AgentTeam row, no follow-up row, no wake turn - and Stop cancels the
turn and every sub-agent. With the switch off the background lane works exactly as before."""
import asyncio
import json
import time
import types

import pytest
from sqlalchemy import func, select

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import gz, tu, txt  # noqa: F401


@pytest.fixture()
def inturn(gz, monkeypatch):  # noqa: F811
    """gz + the conftest pin removed (the new default), and no side model calls that would eat the script."""
    from app.agent import research_plan
    from app.config import get_settings

    async def _off(*a, **k):
        return None
    monkeypatch.setattr(research_plan, "gate", _off)
    monkeypatch.delenv("CHAT_WORK_IN_TURN", raising=False)
    monkeypatch.setenv("HARD_DETECT", "false")
    monkeypatch.setenv("DRAFT_CHECK", "false")
    monkeypatch.setenv("AGENT_AUTO_PLAN", "false")
    get_settings.cache_clear()
    yield gz
    get_settings.cache_clear()


class CrewBrain:
    """Scripted brain for the lead AND its sub-agents: a sub-agent's call is routed by its name in its system prompt
    (they run in parallel, so one shared queue would be popped in a random order); the lead pops `main`."""

    def __init__(self, main, agents):
        self.main = list(main)
        self.agents = {k: list(v) for k, v in agents.items()}
        self.seen = []
        self.main_seen = []
        self.messages = self

    async def create(self, **kw):
        system = json.dumps(kw.get("system"), default=str)
        self.seen.append(kw)
        if "focused sub-agent of Hoola" in system:
            for name, steps in self.agents.items():
                if f'You are \\"{name}\\"' in system or f'You are "{name}"' in system:
                    blocks, stop = steps.pop(0) if steps else ([txt(f"{name}: nothing more")], "end_turn")
                    return types.SimpleNamespace(content=blocks, stop_reason=stop)
            return types.SimpleNamespace(content=[txt("unknown agent")], stop_reason="end_turn")
        self.main_seen.append(kw)
        if not self.main:
            return types.SimpleNamespace(content=[txt("ok")], stop_reason="end_turn")
        blocks, stop = self.main.pop(0)
        return types.SimpleNamespace(content=blocks, stop_reason=stop)


AGENTS = ("market", "rivals", "pricing")


def _crew(monkeypatch, tool_sleep=0.8, mode="background"):
    import app.agent.santosh as s
    agents = {n: [([tu(1, "google_search", q=n)], "tool_use"),
                  ([txt(f"{n} deliverable: {n.upper()}-42")], "end_turn")] for n in AGENTS}
    main = [
        ([txt("Splitting this into three parts."),
          tu(1, "deploy_agents", mission="Check the $5M AI SaaS idea", mode=mode,
             agents=[{"name": n, "task": f"Research the {n} side of the idea"} for n in AGENTS])], "tool_use"),
        ([txt("Here is the full answer: MARKET-42, RIVALS-42 and PRICING-42 together say the idea can work.")],
         "end_turn"),
    ]
    brain = CrewBrain(main, agents)
    monkeypatch.setattr(s, "get_client", lambda: brain)
    real_dispatch = s.dispatch
    starts = []

    async def fake_dispatch(name, args, ctx):
        if name == "google_search":
            starts.append(time.time())
            await asyncio.sleep(tool_sleep)
            return {"results": [{"title": f"page about {args.get('q')}", "url": "https://example.in"}]}
        return await real_dispatch(name, args, ctx)
    monkeypatch.setattr(s, "dispatch", fake_dispatch)
    return brain, starts


def _counts(conv):
    from app.agent.team import AgentTeam, ensure_table
    from app.kaam_followup import KaamFollowup
    from app.db import session
    ensure_table()
    with session() as sdb:
        teams = sdb.scalar(select(func.count(AgentTeam.id)).where(AgentTeam.conversation_id == conv)) or 0
        try:
            fus = sdb.scalar(select(func.count(KaamFollowup.id))) or 0
        except Exception:
            fus = 0
    return teams, fus


def test_settings_defaults_and_conftest_pin(monkeypatch):
    from app.config import get_settings
    assert get_settings().chat_work_in_turn is False          # the old suites' pin is in force
    monkeypatch.delenv("CHAT_WORK_IN_TURN", raising=False)
    get_settings.cache_clear()
    st = get_settings()
    assert st.chat_work_in_turn is True
    assert st.chat_turn_s == 1200 and st.chat_max_calls == 200
    assert st.chat_long_tool_s > st.team_inturn_timeout_s > st.agent_tool_timeout_s
    get_settings.cache_clear()


def test_who_gets_work_in_turn(monkeypatch):
    from app.agent import santosh as s
    from app.agent.tools import Ctx
    from app.config import get_settings
    monkeypatch.delenv("CHAT_WORK_IN_TURN", raising=False)
    get_settings.cache_clear()
    st = get_settings()
    own = Ctx(tenant_id="default", conversation_id="c1", actor="owner")
    assert s.work_in_turn(own, st)
    for actor in ("wake", "goal", "routine", "staff:e1"):
        assert not s.work_in_turn(Ctx(tenant_id="default", conversation_id="c1", actor=actor), st)
    tok = s.VOICE_BRAIN_NOW.set(True)          # a call's brain turn: she is waiting on the line, keep the old lanes
    try:
        assert not s.work_in_turn(own, st)
    finally:
        s.VOICE_BRAIN_NOW.reset(tok)
    assert s._calls_cap(st, own, 48) == 200 and s._calls_cap(st, own, 250) == 250
    assert s._calls_cap(st, Ctx(tenant_id="default", conversation_id="c1", actor="routine"), 48) == 48
    monkeypatch.setenv("CHAT_WORK_IN_TURN", "false")
    get_settings.cache_clear()
    assert not s.work_in_turn(own, get_settings())
    get_settings.cache_clear()


def test_long_tools_get_the_long_clock_in_her_turn(monkeypatch):
    from app.agent import santosh as s
    from app.agent.tools import Ctx
    from app.config import get_settings
    monkeypatch.delenv("CHAT_WORK_IN_TURN", raising=False)
    get_settings.cache_clear()
    seen = {}
    real_wait_for = asyncio.wait_for

    async def spy_wait_for(aw, timeout=None):
        seen["timeout"] = timeout
        return await real_wait_for(aw, timeout)

    async def fake_dispatch(name, args, ctx):
        return {"ok": True}
    monkeypatch.setattr(s, "dispatch", fake_dispatch)
    monkeypatch.setattr(s.asyncio, "wait_for", spy_wait_for)
    own = Ctx(tenant_id="default", conversation_id="c1", actor="owner")
    st = get_settings()
    asyncio.run(s._run_tool("deploy_agents", {}, own, st))
    assert seen["timeout"] == st.chat_long_tool_s
    asyncio.run(s._run_tool("google_search", {}, own, st))
    assert seen["timeout"] == st.agent_tool_timeout_s
    asyncio.run(s._run_tool("research_run", {}, Ctx(tenant_id="default", conversation_id="c1", actor="routine"), st))
    assert seen["timeout"] == st.agent_tool_timeout_s
    get_settings.cache_clear()


def test_a_crew_ask_is_answered_in_the_same_turn(inturn, monkeypatch):
    """The $5M-idea shape: the lead deploys three agents (even asking for background), they run IN PARALLEL inside
    the turn, their work comes back as the tool result, and the lead's combined answer IS the reply. No background
    crew row, no follow-up row, no wake turn."""
    from app.agent import santosh as s
    from app.agent import team
    from app import kaam_followup
    conv = inturn["conv"]
    brain, starts = _crew(monkeypatch, tool_sleep=0.8)
    woke = []
    monkeypatch.setattr(kaam_followup, "_wake", lambda *a, **k: woke.append(a), raising=False)
    bg0, kept0 = team.STATS["background"], s.STATS_INTURN["crews_kept_in_turn"]
    teams0, fus0 = _counts(conv)
    t0 = time.time()
    out = asyncio.run(s.run_turn(conv, "Check whether a $5M AI SaaS idea can work", tenant_id="default"))

    assert "MARKET-42, RIVALS-42 and PRICING-42" in out              # the combined answer is the reply
    assert len(brain.main_seen) == 2                                # one lead call to deploy, one to answer
    last = json.dumps(brain.main_seen[-1]["messages"][-1], default=str)
    for n in AGENTS:                                                # every agent's deliverable reached the lead
        assert f"{n.upper()}-42" in last
    assert '"mode": "inline"' in last or "'mode': 'inline'" in last or "inline" in last
    assert "ran inside this turn" in last
    assert len(starts) == 3 and max(starts) - min(starts) < 0.6       # the agents ran TOGETHER
    assert team.STATS["background"] == bg0                           # nothing went to the background
    assert s.STATS_INTURN["crews_kept_in_turn"] == kept0 + 1
    assert _counts(conv) == (teams0, fus0)                           # no AgentTeam row, no follow-up row
    assert not woke
    assert not team.LIVE                                             # no crew left counted as running


def test_stop_cancels_the_turn_and_every_sub_agent(inturn, monkeypatch):
    from app.agent import santosh as s
    from app.agent import team
    conv = inturn["conv"]
    brain, starts = _crew(monkeypatch, tool_sleep=5.0)
    stopped0 = team.STATS["stopped"]

    async def go():
        task = asyncio.ensure_future(s.run_turn(conv, "Check whether a $5M AI SaaS idea can work", tenant_id="default"))
        for _ in range(60):                        # wait until all three agents are inside their tool call
            await asyncio.sleep(0.1)
            if len(starts) == 3:
                break
        s.stop(conv)                               # her Stop
        t_stop = time.time()
        out = await task
        return out, time.time() - t_stop

    try:
        out, after = asyncio.run(go())
        assert len(starts) == 3
        assert after < 3.5                         # the 5 s tools were cut, not waited for
        assert "MARKET-42" not in out              # no answer was written from half-done work
        assert len(brain.main_seen) == 1           # the lead never got a second call
        assert not team.LIVE                       # every agent was cancelled with the turn
        assert team.STATS["stopped"] >= stopped0   # (cancelled agents never report done)
    finally:
        s._stopped.discard(conv)


def test_switch_off_keeps_the_background_crew(inturn, monkeypatch):
    """CHAT_WORK_IN_TURN=false: mode=background persists a crew and the turn answers at once (the v0.193 / v0.722 lane)."""
    from app.agent import santosh as s
    from app.agent import team
    from app.config import get_settings
    monkeypatch.setenv("CHAT_WORK_IN_TURN", "false")
    get_settings.cache_clear()
    conv = inturn["conv"]
    main = [
        ([tu(1, "deploy_agents", mission="Check the idea", mode="background",
             agents=[{"name": n, "task": f"Research {n}"} for n in AGENTS])], "tool_use"),
        ([txt("A crew of three agents has started; its report will come into this chat.")], "end_turn"),
    ]
    brain = CrewBrain(main, {})
    monkeypatch.setattr(s, "get_client", lambda: brain)
    teams0, _ = _counts(conv)
    bg0 = team.STATS["background"]
    out = asyncio.run(s.run_turn(conv, "Check whether a $5M AI SaaS idea can work", tenant_id="default"))
    assert "crew of three agents has started" in out, (out, len(brain.main_seen))
    assert team.STATS["background"] == bg0 + 1
    assert _counts(conv)[0] == teams0 + 1                           # the crew row the worker slot runs later
    last = json.dumps(brain.main_seen[-1]["messages"][-1], default=str)
    assert "background" in last


def test_research_run_stays_in_her_turn(env, monkeypatch):
    """research_run with no mode: inline (the engine runs now) in her chat turn; the background runner with the
    switch off or on a routine."""
    from app.agent import research_tools as rt
    from app.agent.tools import Ctx
    from app.config import get_settings
    from app.research import bill, engine as E, runner

    class Inline(Exception):
        pass

    class Bg(Exception):
        pass

    async def _run(*a, **k):
        raise Inline()

    def _start(*a, **k):
        raise Bg()
    monkeypatch.setattr(E, "run", _run)
    monkeypatch.setattr(runner, "start", _start)
    monkeypatch.setattr(bill, "preflight", lambda *a, **k: None)
    kw = dict(question="Indian EV two-wheeler market", sub_questions=["size", "players", "prices", "policy"])
    monkeypatch.delenv("CHAT_WORK_IN_TURN", raising=False)
    get_settings.cache_clear()
    with pytest.raises(Inline):
        asyncio.run(rt.research_run(Ctx(tenant_id="default", conversation_id="c_r", actor="owner"), **kw))
    with pytest.raises(Bg):
        asyncio.run(rt.research_run(Ctx(tenant_id="default", conversation_id="c_r", actor="routine"), **kw))
    monkeypatch.setenv("CHAT_WORK_IN_TURN", "false")
    get_settings.cache_clear()
    with pytest.raises(Bg):
        asyncio.run(rt.research_run(Ctx(tenant_id="default", conversation_id="c_r", actor="owner"), **kw))
    get_settings.cache_clear()


def test_the_guide_no_longer_sends_her_crew_to_the_background(monkeypatch):
    from app.agent import prompts
    from app.config import get_settings
    assert prompts.TEAM_BG_TEXT in prompts.SYSTEM                   # the replace really hits the guide
    monkeypatch.delenv("CHAT_WORK_IN_TURN", raising=False)
    get_settings.cache_clear()
    on = prompts.system_prompt(True)
    assert prompts.TEAM_INTURN_TEXT in on and prompts.TEAM_BG_TEXT not in on
    monkeypatch.setenv("CHAT_WORK_IN_TURN", "false")
    get_settings.cache_clear()
    off = prompts.system_prompt(True)
    assert prompts.TEAM_BG_TEXT in off
    get_settings.cache_clear()


def test_her_turn_gets_the_twenty_minute_budget(inturn, monkeypatch):
    from app.agent import santosh as s
    from app.config import get_settings
    seen = {}

    async def spy(coro, conversation_id, first, long):
        seen["first"] = first
        coro.close()
        return "ok"
    monkeypatch.setattr(s, "_with_deadline", spy)
    asyncio.run(s.run_turn(inturn["conv"], "hello", tenant_id="default"))
    assert seen["first"] == get_settings().chat_turn_s == 1200
