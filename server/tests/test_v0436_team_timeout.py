"""v0.436 (long-task report item 0a): a sub-agent crew that runs out of time keeps the work of the agents that
already finished. Before, `asyncio.wait_for(gather(...))` threw away EVERY deliverable on the timeout and replaced
all of them with "time out" - one slow agent cost the whole crew (team.py, inline AND background crews)."""
import asyncio
import time

import app.agent.santosh as santosh
import app.agent.team as team
from app.agent.tools import dispatch
from app.config import get_settings

from tests.test_v0193_harness3 import BrainScript, _ctx, run


def _slow_and_fast(script: BrainScript, slow_s: float):
    async def fake_dispatch(name, args, ctx):
        if (args or {}).get("q") == "slow":
            await asyncio.sleep(slow_s)
        return {"tool": name, "data": "D"}

    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        return await script(brain, system, history, settings, tools, live, max_tokens)

    return fake_brain, fake_dispatch


def _script():
    s = BrainScript()
    s.script["quick"] = [
        ([{"type": "tool_use", "id": "t1", "name": "google_search", "input": {"q": "fast"}}], "tool_use"),
        ([{"type": "text", "text": "quick ka deliverable: 7 dukaanein mili"}], "end_turn"),
    ]
    s.script["slowpoke"] = [
        ([{"type": "tool_use", "id": "t2", "name": "google_search", "input": {"q": "slow"}}], "tool_use"),
        ([{"type": "text", "text": "slowpoke done"}], "end_turn"),
    ]
    return s


def test_inline_timeout_keeps_the_finished_agents_work(env, monkeypatch):
    st = get_settings()
    monkeypatch.setattr(st, "team_agent_timeout_s", 1)
    fake_brain, fake_dispatch = _slow_and_fast(_script(), slow_s=30)
    monkeypatch.setattr(santosh, "_call_brain", fake_brain)
    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    t0 = time.time()
    out = run(dispatch("deploy_agents", {"mission": "do jagah dekho", "mode": "inline",
                                         "agents": [{"name": "quick", "task": "pehli jagah"},
                                                    {"name": "slowpoke", "task": "doosri jagah"}]}, _ctx()))
    assert time.time() - t0 < 10, "the clock did not cut the slow agent"
    by = {a["name"]: a for a in out["agents"]}
    assert by["quick"]["ok"] is True and "7 dukaanein" in by["quick"]["deliverable"]      # kept (was lost)
    assert by["slowpoke"]["ok"] is False and by["slowpoke"].get("timed_out") is True
    assert "time out" in by["slowpoke"]["deliverable"]
    assert "SACH" in out["note"]          # at least one agent delivered -> the merge note, not "koi kuch nahi"


def test_run_crew_timeout_marks_only_the_running_agents(env, monkeypatch):
    fake_brain, fake_dispatch = _slow_and_fast(_script(), slow_s=30)
    monkeypatch.setattr(santosh, "_call_brain", fake_brain)
    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    _ctx()
    before = team.STATS.get("timed_out", 0)
    out = run(team._run_crew([{"name": "quick", "task": "a"}, {"name": "slowpoke", "task": "b"}], "tm_x", "m",
                             None, "default", "c_team", "turn_x", get_settings(), {}, timeout=1))
    assert [o["name"] for o in out] == ["quick", "slowpoke"]        # spec order kept
    assert out[0]["ok"] is True and not out[0].get("timed_out")
    assert out[1].get("timed_out") is True and out[1]["ok"] is False
    assert team.STATS["timed_out"] == before + 1


def test_run_crew_without_timeout_is_unchanged(env, monkeypatch):
    s = BrainScript()
    s.script["a1"] = [([{"type": "text", "text": "a1 done"}], "end_turn")]
    s.script["a2"] = [([{"type": "text", "text": "a2 done"}], "end_turn")]
    fake_brain, fake_dispatch = _slow_and_fast(s, slow_s=0)
    monkeypatch.setattr(santosh, "_call_brain", fake_brain)
    monkeypatch.setattr(santosh, "dispatch", fake_dispatch)
    _ctx()
    out = run(team._run_crew([{"name": "a1", "task": "x"}, {"name": "a2", "task": "y"}], "tm_y", "m",
                             None, "default", "c_team", "turn_y", get_settings(), {}))
    assert [o["ok"] for o in out] == [True, True]
    assert not any(o.get("timed_out") for o in out)
