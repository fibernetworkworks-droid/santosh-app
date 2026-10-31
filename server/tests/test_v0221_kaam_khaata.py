"""v0.221 KAAM KHAATA - long jobs keep their progress and keep going.

Root causes (found on v0.220, reproduced): (1) one message after a long job, yaad squeezed it to its FIRST 13 steps
with values cut at 60 chars - the newest progress was dropped; (2) the GLM / OmniRoute brain's cut answers
(finish_reason 'length') counted as finished and half-written tool calls ran with empty inputs; (3) without a
kaam_plan the turn died at step 24 and that line was never saved; (4) a goal paused on her tap never restarted;
(5) a finished job's result was never saved into history (only Hoola's reply about it).
"""
import asyncio
import json
import types

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


def _job(conv, n, tag="F", reply="Kaam ho gaya"):
    from app.agent import santosh
    santosh._save(conv, "user", f"Bada kaam {tag}", display=f"Bada kaam {tag}")
    for i in range(1, n + 1):
        santosh._save(conv, "assistant", [tu(f"{tag}{i}", "step_tool", n=i)])
        res = {"status": "ok", "step": i, "file_id": f"{tag}_FILE_{i}",
               "url": f"https://example.com/a/really/long/path/to/the/result/number/{i}/of/this/job/final-output.html",
               "data": "x" * 5900}
        santosh._save(conv, "user", [{"type": "tool_result", "tool_use_id": f"t{tag}{i}",
                                       "content": santosh._short(res)}])
    santosh._save(conv, "assistant", [txt(reply)])


def test_previous_long_job_keeps_its_newest_steps_and_whole_values(gz):  # noqa: F811
    from app import yaad
    from app.agent import santosh
    conv = gz["conv"]
    _job(conv, 40)
    santosh._save(conv, "user", "haan aage badho", display="haan aage badho")
    h = json.dumps(yaad.history(conv), ensure_ascii=False)
    for i in (1, 20, 39, 40):                        # every step of the job survives, the newest ones too
        assert f"F_FILE_{i}" in h
    assert "/number/40/of/this/job/final-output.html" in h      # the link is whole, not cut at 60 chars
    assert len(h) < 40000                             # still a compact form, not the 240 KB original


def test_very_long_job_drops_only_the_middle():
    from app import yaad
    steps = [f"s{i}" for i in range(1, 101)]
    kept = yaad.keep_steps(steps, 80)
    assert kept[:2] == ["s1", "s2"] and kept[-1] == "s100" and len(kept) == 80
    assert "beech ke" in kept[2]
    assert yaad.keep_steps(steps, 14)[-1] == "s100"   # even the short form keeps the newest progress


def test_truncated_result_is_salvaged():
    from app import yaad
    from app.agent.santosh import _short
    big = _short({"status": "ok", "file_id": "FX1", "url": "https://example.com/" + "p/" * 60 + "end.pdf",
                  "rows": ["y" * 100] * 100})
    assert "…(truncated)" in big
    g = yaad.gist(big)
    assert "file_id=FX1" in g and "end.pdf" in g


def test_older_work_beyond_the_newest_few_uses_the_short_form(gz):  # noqa: F811
    from app import yaad
    from app.agent import santosh
    conv = gz["conv"]
    for k in range(6):
        _job(conv, 20, tag=f"J{k}")
    santosh._save(conv, "user", "theek hai", display="theek hai")
    h = json.dumps(yaad.history(conv), ensure_ascii=False)
    assert "J5_FILE_20" in h and "J4_FILE_20" in h          # newest work: rich (every step)
    assert "J0_FILE_20" in h and "file_id=J0_FILE_5," not in h and "file_id=J0_FILE_2," in h       # old work: short form, newest steps kept


def test_cheap_brain_cut_is_not_a_finished_answer():
    from app.agent import llm
    data = {"choices": [{"finish_reason": "length", "message": {"content": "Ab main", "tool_calls": [
        {"id": "a", "function": {"name": "make_document", "arguments": '{"title": "Rep'}}]}}]}
    blocks, stop = llm.from_openai(data)
    assert stop == "max_tokens" and all(b["type"] != "tool_use" for b in blocks)
    # a whole call next to a broken one still runs
    data["choices"][0]["message"]["tool_calls"].append({"id": "b", "function": {"name": "kaam_status", "arguments": "{}"}})
    blocks, stop = llm.from_openai(data)
    assert stop == "tool_use" and [b["name"] for b in blocks if b["type"] == "tool_use"] == ["kaam_status"]
    # streamed answers carry finish_reason too
    blocks, stop = llm.from_openai(llm._assemble("cut her", {}, "length"))
    assert stop == "max_tokens"
    assert llm.from_openai(llm._assemble("done", {}, "stop"))[1] == "end_turn"


def test_long_turn_without_a_plan_goes_past_step_24(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    script = [([tu(i, "kaam_status", q=f"step {i}")], "tool_use") for i in range(1, 31)]
    script.append(([txt("Saare 30 kadam ho gaye.")], "end_turn"))
    brain = _set_brain(monkeypatch, FakeBrain(script))
    from app.agent.santosh import STATS_LONG, run_turn
    out = asyncio.run(run_turn(conv, "30 kadam wala kaam karo", tenant_id="default"))
    assert "30 kadam ho gaye" in out
    # v0.311 PLAN HAMESHA: the server writes the plan at step 7 now, long before the step-24 switch (either one = long caps)
    assert len(brain.seen) == 31 and (STATS_LONG["extended"] >= 1 or STATS_LONG["auto_plan"] >= 1)
    assert any("kaam_plan set" in (b.get("text") or "") for m in brain.seen for msg in m["messages"]
               for b in (msg["content"] if isinstance(msg["content"], list) else []) if isinstance(b, dict))


def test_step_cap_line_is_saved_when_long_mode_is_off(gz, monkeypatch):  # noqa: F811
    monkeypatch.setenv("AGENT_GOAL", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        conv = gz["conv"]
        _set_brain(monkeypatch, FakeBrain([([tu(i, "kaam_status", q=f"s{i}")], "tool_use") for i in range(1, 30)]))
        from app.agent.santosh import run_turn
        out = asyncio.run(run_turn(conv, "lamba kaam", tenant_id="default"))
        assert "Yeh kaam lamba" in out
        from app.db import Message, session
        from sqlalchemy import select
        with session() as s:
            last = s.scalars(select(Message).where(Message.conversation_id == conv).order_by(Message.id.desc())).first()
        assert last.role == "assistant" and "Yeh kaam lamba" in (last.display or "")
    finally:
        get_settings.cache_clear()


def test_cut_answer_continues_with_more_room(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Report ka pehla hissa")], "max_tokens"),
                                               ([txt("aur baaki hissa.")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "lambi report likho", tenant_id="default"))
    assert len(brain.seen) == 2 and brain.seen[1]["max_tokens"] > brain.seen[0]["max_tokens"]


def test_job_result_is_saved_into_history_but_never_as_her_words(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    _set_brain(monkeypatch, FakeBrain([([txt("Website taiyaar hai, link chat mein hai.")], "end_turn")]))
    from app.agent.santosh import run_turn
    wake = "[Santosh worker update, not the user] Kaam: Website banao\nNatija: ho gaya\nLink: https://x.test/site-77"
    asyncio.run(run_turn(conv, wake, tenant_id="default", actor="wake", save_user=False))
    from app import yaad
    h = json.dumps(yaad.history(conv), ensure_ascii=False)
    assert "https://x.test/site-77" in h                           # the real result is remembered next turn
    assert all("site-77" not in t for _, t in yaad._recent_user_words(conv, 10, 600))   # never as her words


def test_goal_paused_on_her_restarts_after_she_answers(gz, monkeypatch):  # noqa: F811
    from app.agent import goal
    from app.agent import santosh
    conv = gz["conv"]
    v = goal.set_goal("default", conv, "Website launch", ["build", "launch", "dns"])
    goal._pause(v["id"] if "id" in v else goal.active_for(conv)["id"])
    gid = goal.active_for(conv)["id"]
    started = []
    monkeypatch.setattr(santosh, "_bg", lambda coro: (started.append(coro), coro.close()))
    waiting = {"on": True}
    monkeypatch.setattr(goal, "_waiting_on_her", lambda c: waiting["on"])
    assert goal.resume_tick() == 0 and not started            # her card still waits: nothing restarts
    waiting["on"] = False
    assert goal.resume_tick() == 1 and len(started) == 1       # she answered: the job carries on by itself
    from app.db import session
    with session() as s:
        r = s.get(goal.GoalRun, gid)
        assert r.paused_at is None and r.rounds == 1 and r.paused_s is not None   # no round used up
    assert goal.resume_tick() == 0                              # once


def test_waiting_time_never_counts_against_the_goal(gz):  # noqa: F811
    from datetime import timedelta
    from app.agent import goal
    from app.db import now, session
    conv = gz["conv"]
    goal.set_goal("default", conv, "Kaam", ["a", "b"])
    gid = goal.active_for(conv)["id"]
    with session() as s:
        r = s.get(goal.GoalRun, gid)
        r.started_at = now() - timedelta(minutes=300)
        r.paused_at = now() - timedelta(minutes=290)
    with session() as s:
        assert goal._working_minutes(s.get(goal.GoalRun, gid)) < 15


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.332.0"
