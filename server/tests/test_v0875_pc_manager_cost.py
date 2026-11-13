"""v0.875 PC MANAGER COST (owner: 'FIX IT PERMANENTLY' after OpenRouter showed Sonnet $2.36 beside Qwen 27B $0.13 in a day):
the PC manager turn runs on Qwen 3.8 27B through OpenRouter by default (setting pc_manager_openrouter_model), a Sonnet
turn through OpenRouter caches its system prompt, and the manager rules forbid cutting one ask into tiny tasks."""
from __future__ import annotations

import asyncio

from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401
from tests.test_v0864_pc_manager import live, _capture  # noqa: F401


def _turn(live, monkeypatch, env=None):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    from app.agent import llm
    santosh, seen = _capture(monkeypatch)
    picked = []
    orig = santosh._think

    async def spy(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        picked.append((brain, llm.MODEL_NOW.get()))
        return await orig(brain, system, history, settings, tools, live, max_tokens)
    monkeypatch.setattr(santosh, "_think", spy)
    return santosh, picked, seen


def test_manager_defaults_to_qwen27(live, monkeypatch):  # noqa: F811
    santosh, picked, seen = _turn(live, monkeypatch)
    asyncio.run(santosh.run_turn(live["conv"], "Mere PC pe Chrome mein Swiggy se cheese pizza order karo"))
    assert picked[0] == ("glm", "openrouter:qwen/qwen3.8-27b")
    assert "MANAGER OF THE JOB" in seen[0]["system"] and "pc_do" in seen[0]["tools"]


def test_manager_can_go_back_to_sonnet(live, monkeypatch):  # noqa: F811
    santosh, picked, _ = _turn(live, monkeypatch, {"PC_MANAGER_OPENROUTER_MODEL": "anthropic/claude-sonnet-5.5"})
    asyncio.run(santosh.run_turn(live["conv"], "Mere PC pe Chrome mein Swiggy se cheese pizza order karo"))
    assert picked[0] == ("glm", "openrouter:anthropic/claude-sonnet-5.5")


def test_rules_forbid_tiny_tasks():
    from app.agent import pc_manager
    assert "NEVER cut it into tiny tasks" in pc_manager.RULES and "one ask of hers = one task" in pc_manager.RULES


def test_anthropic_model_via_openrouter_caches_the_system_prompt(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    get_settings.cache_clear()
    try:
        from app.agent import llm
        tok = llm.MODEL_NOW.set("openrouter:anthropic/claude-sonnet-5.5")
        try:
            msgs = [{"role": "system", "content": "RULES"}, {"role": "user", "content": "hi"}]
            llm._cache_system("anthropic/claude-sonnet-5.5", msgs)
            assert msgs[0]["content"][0]["cache_control"] == {"type": "ephemeral"} and msgs[0]["content"][0]["text"] == "RULES"
            other = [{"role": "system", "content": "RULES"}]
            llm._cache_system("qwen/qwen3.8-27b", other)
            assert other[0]["content"] == "RULES"                       # other models are untouched
        finally:
            llm.MODEL_NOW.reset(tok)
    finally:
        get_settings.cache_clear()


def test_setting_default():
    get_settings.cache_clear()
    assert get_settings().pc_manager_openrouter_model == "qwen/qwen3.8-27b"
