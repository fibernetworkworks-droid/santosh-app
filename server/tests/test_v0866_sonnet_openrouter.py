"""v0.866 SONNET VIA OPENROUTER (owner: 'I HAVE CREDIT IN OPENROUTER USE SONET VIA THAT'): her PC work - the manager
turn and the PC loop - runs on Sonnet billed to the server's OpenRouter key; no key = the Anthropic path as before."""
from __future__ import annotations

import asyncio

import pytest

from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401
from tests.test_v0864_pc_manager import live, _capture  # noqa: F401


def test_pc_loop_picks_sonnet_on_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    monkeypatch.setenv("PC_MODEL", "sonnet")
    get_settings.cache_clear()
    try:
        from app.pc import brain
        b, m, note = brain.choose("")
        assert (b, m, note) == ("sonnet-or", "anthropic/claude-sonnet-5.5", "")
        monkeypatch.setenv("PC_VIA_OPENROUTER", "false")
        get_settings.cache_clear()
        assert brain.choose("")[0] == "sonnet"
    finally:
        get_settings.cache_clear()


def test_pc_loop_openrouter_request_shape(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    get_settings.cache_clear()
    from app.pc import brain
    sent = {}

    async def fake_post(url, key, body, timeout):
        sent.update(body=body, url=url)
        return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {
            "name": "done", "arguments": "{\"answer\": \"ok\"}"}}]}, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2}}
    monkeypatch.setattr(brain, "_post", fake_post)
    try:
        rep = asyncio.run(brain.think_qwen("anthropic/claude-sonnet-5.5", "RULES", [{"role": "user", "content": "go"}],
                                           [{"name": "done", "description": "d", "input_schema": {"type": "object"}}], 500))
        body = sent["body"]
        assert "openrouter.ai" in sent["url"] and body["model"] == "anthropic/claude-sonnet-5.5"
        assert body["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}
        assert "reasoning" not in body and "provider" not in body
        assert rep.content and rep.content[0]["type"] == "tool_use"
    finally:
        get_settings.cache_clear()


def test_manager_turn_rides_openrouter_when_keyed(live, monkeypatch):  # noqa: F811
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    get_settings.cache_clear()
    from app.agent import llm
    santosh, seen = _capture(monkeypatch)
    picked = []
    orig = santosh._think

    async def spy(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        picked.append((brain, llm.MODEL_NOW.get()))
        return await orig(brain, system, history, settings, tools, live, max_tokens)
    monkeypatch.setattr(santosh, "_think", spy)
    asyncio.run(santosh.run_turn(live["conv"], "Mere PC pe Chrome mein Swiggy se pizza order karo"))
    assert picked[0] == ("glm", "openrouter:anthropic/claude-sonnet-5.5")
    assert "MANAGER OF THE JOB" in seen[0]["system"]
