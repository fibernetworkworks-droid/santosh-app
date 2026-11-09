"""CALL PAR TEAM (owner: "lets work on hoola ai multi agent call during call during a long task" -> GO).

1  the background-crew cap counts crews (it compared an id string with a number - TypeError while one ran)
2  a long job's rounds scheduled from a call run as chat work, never in quick-voice mode
3  a call question that did not touch the open job is answered, not pulled into the job
4  a crew report that waited out a busy call is still SAID on the live call
5  spoken crew results carry whole sentences (700 / 3000 / 1500, the digest 600)
6  "agents band karo" stops a background crew for real
7  on a call, kaam_plan add / show / step reach the job running in the chat the call came from
8  live agent-by-agent progress of every crew in the job block and agent_status
9  a cap on inline agents per HER, not per ask
10 a crew asked for on a call works like a chat crew (no voice mode) and a research ask gets the research rules
11 fixed lines in her avatar's forms
12 two quick asks on a call never pick the same record
"""
from __future__ import annotations

import asyncio
import inspect
import types

from app.db import Conversation, session

T = "default"


def _chat(cid: str, **kw) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, **kw))
    return cid


# ---------------------------------------------------------------- 1
def test_the_background_cap_counts_crews(env):
    from app.agent import team
    from app.config import get_settings
    _chat("bt1")
    team.ensure_table()
    with session() as s:
        s.add(team.AgentTeam(tenant_id=T, conversation_id="bt1", mission="m1", spec="{}", status="running"))
        s.add(team.AgentTeam(tenant_id=T, conversation_id="bt1", mission="m2", spec="{}", status="running"))
    specs = [{"name": "a", "task": "kuch dhoondo"}]
    out = asyncio.run(team._deploy_background(specs, "teesra", T, "bt1", "t1", "", get_settings()))
    assert "pehle ki background team" in out["note"]                     # refused, not a TypeError


# ---------------------------------------------------------------- 2
def test_a_round_scheduled_from_a_call_is_chat_work(env, monkeypatch):
    from app.agent import goal, santosh
    _chat("g2")
    v = goal.set_goal(T, "g2", "kaam", ["a", "b"], origin="owner")
    seen = []

    async def fake_cont(*a, **k):
        seen.append((santosh.VOICE_BRAIN_NOW.get(), santosh._MODEL_NOW.get()))
    monkeypatch.setattr(goal, "_continuation", fake_cont)

    async def go():
        santosh.VOICE_BRAIN_NOW.set(True)
        santosh._MODEL_NOW.set("claude-haiku-5-5")
        goal._schedule("g2", T, goal.active_for("g2"), count_round=False)
        await asyncio.sleep(0.05)
    goal._PENDING.pop(v["id"], None)
    asyncio.run(go())
    goal._PENDING.pop(v["id"], None)
    assert seen == [(False, "")]


# ---------------------------------------------------------------- 3
def test_a_call_question_is_not_pulled_into_the_job():
    from app.agent import santosh
    src = inspect.getsource(santosh._steps_inner)
    assert 'VOICE_BRAIN_NOW.get() and not any(' in src and '.get("tool") == "kaam_plan"' in src


# ---------------------------------------------------------------- 4 + 5
def test_crew_reports_reach_the_call_whole():
    from app import kaam_followup, voice
    from app.agent import team
    src = inspect.getsource(kaam_followup)
    assert "kaamwatch._voice(r.tenant_id, conv, line[:700])" in src and '.split())[:700])' in src
    assert '"say": _clip(digest, 600)' in inspect.getsource(team.run_background)
    vs = inspect.getsource(voice.Call._late_result)
    assert "[:3000]" in vs and "[:1500]" in vs


# ---------------------------------------------------------------- 6
def test_roko_stops_a_background_crew(env):
    from app.agent import team
    from app import kaamstop
    _chat("st6")
    team.ensure_table()
    with session() as s:
        r = team.AgentTeam(tenant_id=T, conversation_id="st6", mission="prices", spec="{}", status="running")
        s.add(r)
        s.flush()
        tid = r.id
    assert kaamstop._native_stop(T, "agent_team", tid, "st6") is True
    with session() as s:
        assert s.get(team.AgentTeam, tid).status == "stopped"
    assert kaamstop._native_stop(T, "agent_team", tid, "st6") is False   # already stopped


# ---------------------------------------------------------------- 7
def test_a_call_reaches_the_chats_running_job(env):
    from app.agent import goal, goal_tools
    from app import callconv
    _chat("home7")
    _chat("call7", kind="call", origin_conv="home7")
    callconv._KIND.pop("call7", None)
    v = goal.set_goal(T, "home7", "Diwali campaign", ["list", "message"], origin="owner")
    ctx = types.SimpleNamespace(tenant_id=T, conversation_id="call7", actor="owner")
    shown = asyncio.run(goal_tools.kaam_plan(ctx, action="show"))
    assert v["id"] in str(shown)
    asyncio.run(goal_tools.kaam_plan(ctx, action="add", text="Rahul ko bhi bhejna"))
    steps = [x["text"] for x in goal.active_for("home7")["steps"]]
    assert "Rahul ko bhi bhejna" in steps
    assert goal.active_for("call7") is None                       # no second job on the call record


# ---------------------------------------------------------------- 8 + 9
def test_live_progress_and_the_per_her_cap(env, monkeypatch):
    from app.agent import team, santosh
    from app import kaamwatch
    team.LIVE.clear()
    team._live_open("tmA", T, "c8", "5 supplier ke daam", [{"name": "price"}, {"name": "gst"}, {"name": "review"}])
    team.LIVE["tmA"]["agents"]["gst"] = "ho gaya"
    lines = team.live_lines(T)
    assert lines and "1/3 agent ho gaye" in lines[0] and "price" in lines[0]
    assert team.inline_running(T) == 2
    assert "1/3 agent ho gaye" in kaamwatch.block(T)
    monkeypatch.setattr(santosh.get_settings(), "team_tenant_inline_max", 2)
    ctx = types.SimpleNamespace(tenant_id=T, conversation_id="c8", actor="owner", team_used=0, admit=None)
    out = asyncio.run(team.deploy_agents(ctx, "naya kaam", [{"name": "x", "task": "kuch karo"}]))
    assert "pehle se kai agents chal rahe" in out["note"]
    team.LIVE.clear()


# ---------------------------------------------------------------- 10
def test_a_call_crew_is_chat_work_and_research_gets_its_rules(env, monkeypatch):
    from app.agent import team, santosh
    seen = {}

    async def fake_agent(spec, team_id, mission, fams, tenant, conv, turn_id, settings, shared):
        seen["voice"] = santosh.VOICE_BRAIN_NOW.get()
        seen["model"] = santosh._MODEL_NOW.get()
        seen["research"] = shared.get("research")
        return {"name": spec["name"], "ok": True, "deliverable": "x", "seconds": 0.1, "tools": []}
    monkeypatch.setattr(team, "_run_agent", fake_agent)
    team.LIVE.clear()

    async def go():
        santosh.VOICE_BRAIN_NOW.set(True)
        santosh._MODEL_NOW.set("claude-haiku-5-5")
        ctx = types.SimpleNamespace(tenant_id=T, conversation_id="c10", actor="owner", team_used=0, admit=None)
        return await team.deploy_agents(ctx, "Research the latest CBSE fee rules from official sources with dates",
                                        [{"name": "a", "task": "official CBSE pages padho"}])
    out = asyncio.run(go())
    assert out["mode"] == "inline" and seen == {"voice": False, "model": "", "research": True}
    assert team.LIVE == {}


# ---------------------------------------------------------------- 11
def test_fixed_lines_in_her_forms(monkeypatch):
    from app import kaam_followup, voice
    import app.avatar.service as av
    r = types.SimpleNamespace(tenant_id="t-f", label="Team", title="prices", state="stopped", detail="", link="")
    monkeypatch.setattr(av, "persona", lambda t: ("Priya", "f"))
    assert "I will start it again" in kaam_followup._canned(r)
    assert "'bataungi' if getattr(self, 'gender', 'm') == 'f'" in inspect.getsource(voice.Call._late_result)


# ---------------------------------------------------------------- 12
def test_two_quick_asks_never_pick_the_same_record(monkeypatch):
    from app import voice, callconv
    made = []
    monkeypatch.setattr(callconv, "open_side", lambda t, c, cid: made.append(1) or f"side{len(made)}")
    call = voice.Call.__new__(voice.Call)
    call.conv, call.ctx, call.call_id, call.stats = "callX", types.SimpleNamespace(tenant_id=T), "cid", {}
    a = call._pick_conv()                   # the first ask's turn has not taken the lock yet
    b = call._pick_conv()
    assert a == "callX" and b == "side1" and a != b
    call._claimed["callX"] = 0              # the first ask ended: the call record is free again
    assert call._run_conv() == "callX"
