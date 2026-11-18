"""v0.864 PC MANAGER - the brain that runs her PC jobs (Hoola in her chat / call) back on Sonnet with its PC rules
(owner: 'put the manager back on Sonnet with its PC rules'). Root cause: SAB HAIKU (v0.631) put every chat turn on
Haiku and parity Phase 2/3 (v0.732) gave it the small prompt with ONE line about PCs and the PC tools out of view."""
from __future__ import annotations

import asyncio
import time
import types

import pytest

from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401

SWITCHES = ("CHAT_ONE_MODEL", "CHAT_SMALL_PROMPT", "CHAT_CORE_TOOLS", "CHAT_WORK_IN_TURN", "CHAT_ANSWER_ONLY",
            "CHAT_ARTIFACT_DIRECT", "CHAT_PLAIN_LOOP", "CHAT_THINKING_ADAPTIVE", "CHAT_ONE_MEMORY", "CLAUDE_ONE_MODEL",
            "PC_MANAGER")


@pytest.fixture()
def live(bz, monkeypatch):
    for k in SWITCHES:
        monkeypatch.delenv(k, raising=False)        # the server's real defaults (Haiku one-model, small prompt)
    monkeypatch.setenv("HOOLA_LANGUAGE", "en")
    get_settings.cache_clear()
    yield bz
    get_settings.cache_clear()


def _capture(monkeypatch):
    from app.agent import santosh
    from app import usage, glmdoor
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen.append({"system": system if isinstance(system, str) else "".join(b.get("text", "") for b in system),
                     "tools": [t.get("name") for t in (tools or []) if not t.get("defer_loading")], "brain": brain,
                     "model": santosh._MODEL_NOW.get(), "bypass": usage.ONE_MODEL_BYPASS.get(),
                     "claude_only": glmdoor.CLAUDE_ONLY.get()})
        return ([{"type": "text", "text": "OK."}], "end_turn", brain)
    monkeypatch.setattr(santosh, "_think", fake_think)
    monkeypatch.setattr(santosh, "_claude_ready", lambda: True)
    return santosh, seen


def test_pc_turn_runs_on_sonnet_with_the_pc_rules(live, monkeypatch):
    santosh, seen = _capture(monkeypatch)
    asyncio.run(santosh.run_turn(live["conv"], "Mere PC pe Chrome mein Swiggy se ek cheese pizza order karo"))
    s = seen[0]
    assert s["model"] == "claude-sonnet-5-5" and s["bypass"] and s["claude_only"] and s["brain"] == "claude"
    assert "YOU ARE THE MANAGER OF THE JOB ON HER COMPUTER" in s["system"]
    assert "ONE job = ONE pc_do task" in s["system"]
    assert "pc_do" in s["tools"]
    from app import usage, glmdoor
    assert not usage.ONE_MODEL_BYPASS.get() and not glmdoor.CLAUDE_ONLY.get()   # never leaks past the turn


def test_follow_up_after_her_pc_task_stays_on_the_manager(live, monkeypatch):
    from app.pc import operator
    santosh, seen = _capture(monkeypatch)
    operator.HER_PC_AT["default"] = time.time()
    try:
        asyncio.run(santosh.run_turn(live["conv"], "pizza cancel karo, KFC se chicken order karo"))
    finally:
        operator.HER_PC_AT.pop("default", None)
    assert seen[0]["model"] == "claude-sonnet-5-5" and "pc_do" in seen[0]["tools"]


def test_ordinary_chat_is_unchanged(live, monkeypatch):
    santosh, seen = _capture(monkeypatch)
    asyncio.run(santosh.run_turn(live["conv"], "what is the capital of France?"))
    s = seen[0]
    assert s["model"] != "claude-sonnet-5-5" or not s["bypass"]
    assert not s["bypass"] and "MANAGER OF THE JOB" not in s["system"]


def test_switch_off(live, monkeypatch):
    monkeypatch.setenv("PC_MANAGER", "false")
    get_settings.cache_clear()
    santosh, seen = _capture(monkeypatch)
    asyncio.run(santosh.run_turn(live["conv"], "Mere PC pe Chrome mein Swiggy kholo"))
    assert not seen[0]["bypass"] and "MANAGER OF THE JOB" not in seen[0]["system"]


def test_hoola_pc_named_is_not_a_manager_turn():
    from app.agent import pc_manager
    st = get_settings()
    ctx = types.SimpleNamespace(place="hoolapc")
    assert not pc_manager.wanted(st, ctx, "c_x", "t_none", "Hoola ke PC par blender install karo")
