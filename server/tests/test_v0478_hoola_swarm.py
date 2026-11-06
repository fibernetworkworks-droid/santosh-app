"""v0.478.0 HOOLA SWARM - self-spawning subagents (the Hermes delegation ported).

What this suite pins:
(1) REGISTRY: ONE delegate_task tool in the agent's table + handler wired.
(2) KILL SWITCH: coder_delegate (default OFF) refuses honestly; coder_enabled too.
(3) CAPS: too-many-tasks rejected with Hermes's wording (cap = coder_delegate_max_children,
    default 3, both the per-call cap AND the concurrency semaphore); a task without a prompt
    is rejected; prompts are capped at 4000 chars.
(4) DEPTH CAP + MONEY FLOOR: the child's surface excludes delegate_task (no recursion - Hermes
    MAX_DEPTH 1), confirm_send, haan_karo and pc_do; a child that asks anyway is DENIED at
    dispatch with a plain message.
(5) THE CHILD RUNNER: same model path (santosh._call_brain), bounded at 6 tool rounds and 2000
    tokens; every tool call rides santosh._run_tool - so the coder funnel CAPTURES child work
    (tool_uses rows land in the vault); one failed tool never kills the child; the iteration
    budget returns a partial report, never a hang.
(6) TIMEOUT: a stuck child is cancelled at coder_delegate_timeout_s and reported ok=False -
    the batch still returns.
(7) VOICE: delegate_task is NOT in the voice allowlist (a call routes it to a kaam job).
"""
import asyncio
import json

import pytest

from app import coder
from app.coder import delegate, store
from app.agent import tools as agent_tools

T = "default"
CONV = "conv_swarm"


@pytest.fixture()
def swarm(env, monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir; delegation ON (the baked state) unless a test flips it."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_DELEGATE", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    store.ensure()
    yield monkeypatch
    get_settings.cache_clear()


def _ctx():
    return type("C", (), {"tenant_id": T, "conversation_id": CONV,
                          "actor": "owner", "place": ""})()


# ---------------------------------------------------------------- (1) registry

def test_delegate_tool_registered(swarm):
    assert any(t["name"] == "delegate_task" for t in agent_tools.TOOLS)
    assert agent_tools.HANDLERS.get("delegate_task") is not None
    assert agent_tools.TOOL_LABELS.get("delegate_task")


def test_package_exports_the_funnel(swarm):
    """v0.478 REGRESSION (the catch of this suite): the funnel calls coder.tool_observed etc.
    ON THE PACKAGE - v0.473 exported only the modules, so every funnel call raised
    AttributeError and died silently inside its fail-open wrapper: production capture wrote
    NOTHING while every suite stayed green (they call the capture MODULE path directly)."""
    from app import coder as pkg
    for fn in ("tool_observed", "turn_prompt", "session_started", "session_ended", "save_memory"):
        assert callable(getattr(pkg, fn, None)), f"package-level export missing: {fn}"


# ---------------------------------------------------------------- (2) kill switches

def test_kill_switch_default_off(swarm, monkeypatch):
    monkeypatch.setenv("CODER_DELEGATE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    res = asyncio.run(delegate.delegate_task(_ctx(), tasks=[{"prompt": "x"}]))
    assert "error" in res and "coder_delegate" in res["error"]


def test_kill_switch_master(swarm, monkeypatch):
    monkeypatch.setenv("CODER_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    res = asyncio.run(delegate.delegate_task(_ctx(), tasks=[{"prompt": "x"}]))
    assert "error" in res


# ---------------------------------------------------------------- (3) caps

def test_too_many_tasks_rejected_hermes_wording(swarm):
    res = asyncio.run(delegate.delegate_task(
        _ctx(), tasks=[{"prompt": f"t{i}"} for i in range(4)]))
    assert "error" in res
    assert "Too many tasks" in res["error"] and "max_concurrent_children is 3" in res["error"]


def test_bad_tasks_rejected(swarm):
    assert "error" in asyncio.run(delegate.delegate_task(_ctx(), tasks=[]))
    assert "error" in asyncio.run(delegate.delegate_task(_ctx(), tasks="nope"))
    assert "error" in asyncio.run(delegate.delegate_task(_ctx(), tasks=[{"label": "no prompt"}]))
    assert "error" in asyncio.run(delegate.delegate_task(_ctx(), tasks=[{"prompt": "   "}]))


def test_prompts_capped(swarm, monkeypatch):
    seen: dict = {}

    async def fake_child(ctx, settings, task, i):
        seen["len"] = len(task["prompt"])
        return {"label": task["label"], "ok": True, "text": "done", "tool_calls": 0, "seconds": 0}

    monkeypatch.setattr(delegate, "run_child", fake_child)
    res = asyncio.run(delegate.delegate_task(_ctx(), tasks=[{"prompt": "p" * 9000}]))
    assert res["ok"] and seen["len"] == delegate.PROMPT_MAX


# ---------------------------------------------------------------- (4) depth + money floor

def test_child_surface_excludes_denied(swarm):
    names = {t["name"] for t in delegate._child_specs()}
    assert "delegate_task" not in names          # MAX_DEPTH 1: no recursion, hard
    assert "confirm_send" not in names           # campaign sends never move from a worker
    assert "haan_karo" not in names              # approval cards are voice-tapped, never worker-run
    assert "pc_do" not in names                  # a worker must not start a PC job that outlives it
    assert "skill_manage" in names               # the honest surface IS there


def test_child_denied_at_dispatch(swarm):
    """Even if the model asks, the deny set answers at dispatch with a plain message."""
    denied_ask = [{"type": "tool_use", "id": "tu1", "name": "delegate_task",
                   "input": {"tasks": [{"prompt": "nested"}]}}]

    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None,
                         think=False, **_):
        if any(b.get("type") == "tool_result" for m in history if m["role"] == "user"
               for b in (m["content"] if isinstance(m["content"], list) else [])):
            return [{"type": "text", "text": "gave up, reporting"}], "end_turn"
        return denied_ask, "tool_use"

    from app.agent import santosh
    real = santosh._call_brain
    santosh._call_brain = fake_brain
    try:
        out = asyncio.run(delegate.run_child(_ctx(), _settings_like(), {"prompt": "do it"}, 0))
    finally:
        santosh._call_brain = real
    assert out["ok"] and out["tool_calls"] == 0
    assert "cannot delegate" in out["text"] or out["text"] == "gave up, reporting"


def _settings_like():
    from app.config import get_settings
    return get_settings()


# ---------------------------------------------------------------- (5) the child runner

def test_child_runs_tools_through_the_funnel(swarm, monkeypatch):
    """Tool call -> _run_tool -> dispatch -> CAPTURE: the vault sees the child's work."""
    steps = {"n": 0}

    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None,
                         **_):
        steps["n"] += 1
        if steps["n"] == 1:
            return [{"type": "tool_use", "id": "tu9", "name": "list_lead_lists",
                     "input": {}}], "tool_use"
        return [{"type": "text", "text": "found 0 lists, report done"}], "end_turn"

    from app.agent import santosh
    real = santosh._call_brain
    santosh._call_brain = fake_brain
    try:
        out = asyncio.run(delegate.run_child(_ctx(), _settings_like(),
                                             {"prompt": "list her lead lists", "label": "lists"}, 0))
    finally:
        santosh._call_brain = real
    assert out["ok"] and out["label"] == "lists" and out["tool_calls"] == 1
    assert "report done" in out["text"]
    with store.db() as c:
        row = c.execute("SELECT tool, conv FROM tool_uses WHERE conv=? ORDER BY id DESC LIMIT 1",
                        (CONV,)).fetchone()
    assert row is not None and row["tool"] == "list_lead_lists"   # the funnel captured the child


def test_child_tool_error_never_kills_it(swarm, monkeypatch):
    calls = {"n": 0}

    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None,
                         **_):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"type": "tool_use", "id": "tu1", "name": "get_lead_list",
                     "input": {"list_id": "missing"}}], "tool_use"
        return [{"type": "text", "text": "handled the failure"}], "end_turn"

    from app.agent import santosh
    real = santosh._call_brain
    santosh._call_brain = fake_brain
    try:
        out = asyncio.run(delegate.run_child(_ctx(), _settings_like(), {"prompt": "p"}, 0))
    finally:
        santosh._call_brain = real
    assert out["ok"] and "handled the failure" in out["text"]


def test_child_iteration_budget_returns_partial(swarm, monkeypatch):
    """A worker that keeps calling tools is stopped at the budget with a partial report."""
    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None,
                         **_):
        return [{"type": "tool_use", "id": "tux", "name": "list_lead_lists",
                 "input": {}}], "tool_use"

    from app.agent import santosh
    real = santosh._call_brain
    santosh._call_brain = fake_brain
    try:
        out = asyncio.run(delegate.run_child(_ctx(), _settings_like(), {"prompt": "p"}, 0))
    finally:
        santosh._call_brain = real
    assert out["ok"] and "iteration budget" in out["text"]


# ---------------------------------------------------------------- (6) timeout

def test_stuck_child_times_out_batch_survives(swarm, monkeypatch):
    monkeypatch.setenv("CODER_DELEGATE_TIMEOUT_S", "10")
    from app.config import get_settings
    get_settings.cache_clear()

    async def slow_child(ctx, settings, task, i):
        await asyncio.sleep(60)
        return {"label": task["label"], "ok": True, "text": "never", "tool_calls": 0, "seconds": 60}

    monkeypatch.setattr(delegate, "run_child", slow_child)
    res = asyncio.run(delegate.delegate_task(
        _ctx(), tasks=[{"prompt": "hang", "label": "hung"}, {"prompt": "p2", "label": "t2"}]))
    assert len(res["results"]) == 2                # the batch survives
    hung = [r for r in res["results"] if r["label"] == "hung"][0]
    assert hung["ok"] is False and "timed out" in hung["text"]


def test_child_crash_is_one_failed_result(swarm, monkeypatch):
    async def boom(ctx, settings, task, i):
        raise RuntimeError("worker exploded")

    monkeypatch.setattr(delegate, "run_child", boom)
    res = asyncio.run(delegate.delegate_task(_ctx(), tasks=[{"prompt": "p", "label": "x"}]))
    assert res["results"][0]["ok"] is False and "exploded" in res["results"][0]["text"]


# ---------------------------------------------------------------- (7) voice + version

def test_voice_allowlist_never_admits_delegation(swarm):
    from app.voice import VOICE_TOOL_NAMES
    assert "delegate_task" not in VOICE_TOOL_NAMES


def test_delegate_stats_shape(swarm):
    s = delegate.stats()
    assert s["child_max_iters"] == 6 and "delegate_task" in s["children_denied"]


def test_version_stamp(swarm):
    from app.main import APP_VERSION
    assert APP_VERSION == "0.611.0"
