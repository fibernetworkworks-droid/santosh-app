"""v0.874 voice-call alignment for desktop work (owner: 'check is voice call is perfectly alined for desktop work'):
a call's brain turn about her PC must get the same manager (rules, pc tools, OpenRouter Sonnet) as a chat turn."""
from __future__ import annotations

import asyncio

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0864_pc_manager import live, _capture  # noqa: F401


def _call_turn(santosh, conv, text, monkeypatch):
    from app.agent import llm
    seen_models = []
    orig = santosh._think

    async def spy(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen_models.append((brain, llm.MODEL_NOW.get(), santosh._MODEL_NOW.get()))
        return await orig(brain, system, history, settings, tools, live, max_tokens)
    monkeypatch.setattr(santosh, "_think", spy)

    async def go():
        santosh.VOICE_BRAIN_NOW.set(True)      # exactly what a call's santosh_kaam turn sets
        return await santosh.run_turn(conv, text)
    asyncio.run(go())
    return seen_models


def test_call_brain_turn_about_her_pc_gets_the_manager(live, monkeypatch):  # noqa: F811
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    santosh, seen = _capture(monkeypatch)
    models = _call_turn(santosh, live["conv"], "Mere PC pe Chrome mein Swiggy se cheese pizza order karo", monkeypatch)
    s = seen[0]
    print("CALL TURN:", models[0], "| tools has pc_do:", "pc_do" in s["tools"], "| rules:", "MANAGER OF THE JOB" in s["system"])
    assert "MANAGER OF THE JOB" in s["system"] and "pc_do" in s["tools"]
    assert models[0][0] == "glm" and models[0][1] == "openrouter:qwen/qwen3.8-27b"


def test_call_brain_turn_about_anything_else_stays_haiku(live, monkeypatch):  # noqa: F811
    santosh, seen = _capture(monkeypatch)
    models = _call_turn(santosh, live["conv"], "what is the capital of France?", monkeypatch)
    print("CALL TURN (not PC):", models[0])
    assert "MANAGER OF THE JOB" not in seen[0]["system"]
