"""Parity gap 4 THINKING (docs/CLAUDE_PARITY_PLAN.md Part 2 row 4): adaptive thinking on the chat brain, shown folded.

Every chat turn may think; the effort is chosen by the turn (greeting low, ordinary medium, hard ask / long job high).
On OpenRouter GLM the reasoning text comes back (exclude false), streams to the Soch card ('think' events) and never
reaches the saved reply or the next request. Switch chat_thinking_adaptive off = today's request body byte-identical.
All offline: a fake OpenRouter endpoint.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

OR = "https://openrouter.ai/api/v1"


def _adaptive(monkeypatch, on=True):
    from app.config import get_settings
    if on:
        monkeypatch.delenv("CHAT_THINKING_ADAPTIVE", raising=False)   # the conftest pin removed = the default
    else:
        monkeypatch.setenv("CHAT_THINKING_ADAPTIVE", "false")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def orr(monkeypatch):
    from app.config import get_settings
    from app.agent import llm
    get_settings.cache_clear()
    st = get_settings()
    for k, v in {"glm_api_key": "sk-or-test", "glm_base_url": OR, "glm_model": "z-ai/glm-5.3-flash",
                 "glm_thinking": "disabled", "llm_retries": 0}.items():
        monkeypatch.setattr(st, k, v)
    yield st
    llm.REASONING_NOW.set("")


def test_default_on_and_conftest_pins_off(monkeypatch):
    from app.config import Settings
    assert Settings.model_fields["chat_thinking_adaptive"].default is True
    assert _adaptive(monkeypatch, on=False).chat_thinking_adaptive is False


def test_turn_kind_picks_the_effort(monkeypatch):
    from app.agent.santosh import think_level, think_wanted
    st = _adaptive(monkeypatch)
    for g in ("hi", "Hello Hoola!", "namaste", "thanks", "ok", "theek hai", "good morning", "shukriya ji"):
        assert think_level(st, g, False, False) == "low", g
    for t in ("What is the capital of France?", "mera kal ka meeting kab hai", "draft a mail to Ravi about the invoice"):
        assert think_level(st, t, False, False) == "medium", t
    assert think_level(st, "hi", False, True) == "high"            # a hard ask
    assert think_level(st, "build the full report", True, False) == "high"   # a long job / big ask
    # every chat turn may think now, not only while a long job runs
    assert think_wanted(st, False, "medium") and think_wanted(st, False, "low")
    monkeypatch.setattr(st, "chat_thinking", "off")
    assert think_level(st, "What is it?", False, True) == "" and not think_wanted(st, False, "high")


def test_switch_off_is_todays_behaviour(monkeypatch):
    from app.agent.santosh import think_level, think_wanted
    st = _adaptive(monkeypatch, on=False)
    assert think_level(st, "What is it?", True, True) == ""
    assert think_wanted(st, False, "") is False and think_wanted(st, True, "") is True


def test_openrouter_body_per_level_and_room(orr, monkeypatch):
    from app.agent import llm
    # no level = the v0.700 body exactly
    llm.REASONING_NOW.set("")
    assert llm._target("glm")[4] == {"reasoning": {"effort": "low", "exclude": True}}
    base = llm.room(1000)
    assert base == 1000 + 2048
    seen = []
    for lvl in ("low", "medium", "high"):
        llm.REASONING_NOW.set(lvl)
        assert llm._target("glm")[4] == {"reasoning": {"effort": lvl, "exclude": False}}
        seen.append(llm.room(1000))
    assert seen == [1000 + 2048, 1000 + 4096, 1000 + 8192]      # the answer keeps its own 1000 tokens at every level
    llm.REASONING_NOW.set("medium")
    _, _, _, _, body = llm._stream_body("glm", "sys", [], [{"role": "user", "content": "hi"}], 1000)
    assert body["reasoning"] == {"effort": "medium", "exclude": False} and body["max_tokens"] == 5096
    for bad in ("thinking", "reasoning_effort", "chat_template_kwargs"):
        assert bad not in body


def test_switch_off_body_byte_identical(orr, monkeypatch):
    from app.agent import llm
    llm.REASONING_NOW.set("")
    off = llm._stream_body("glm", "sys", [], [{"role": "user", "content": "hi"}], 1000)[4]
    assert off["reasoning"] == {"effort": "low", "exclude": True} and off["max_tokens"] == 3048
    nv = "https://integrate.api.nvidia.com/v1"
    monkeypatch.setattr(orr, "glm_base_url", nv)
    assert llm._target("glm")[4]["reasoning_effort"] == "low"
    llm.REASONING_NOW.set("high")
    assert llm._target("glm")[4]["reasoning_effort"] == "high"
    llm.REASONING_NOW.set("medium")
    assert llm._target("glm")[4]["reasoning_effort"] == "low"     # NVIDIA has no medium


def _sse(*objs):
    return b"".join(b"data: " + json.dumps(o).encode() + b"\n\n" for o in objs) + b"data: [DONE]\n\n"


def test_reasoning_deltas_go_to_on_think_never_into_the_answer(orr):
    from app.agent import llm
    body = _sse({"choices": [{"delta": {"reasoning": "She greets me. "}}]},
                {"choices": [{"delta": {"reasoning": "Reply warmly."}}]},
                {"choices": [{"delta": {"content": "Namaste!"}, "finish_reason": "stop"}],
                 "usage": {"prompt_tokens": 9, "completion_tokens": 4}})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body))))
    words, thought = [], []
    try:
        llm.REASONING_NOW.set("low")
        blocks, stop, _ = asyncio.run(llm.openai_stream("glm", "sys", [], [{"role": "user", "content": "hi"}], 100,
                                                        words.append, on_think=thought.append))
    finally:
        llm.set_http(None)
    assert "".join(thought) == "She greets me. Reply warmly."
    assert words == ["Namaste!"] and blocks == [{"type": "text", "text": "Namaste!"}] and stop == "end_turn"


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def test_a_real_turn_on_glm(env, monkeypatch):
    """Through run_turn: the greeting asks effort low, the ordinary ask medium; the reasoning reaches the 'think' events
    only - never the saved reply and never the next request's messages."""
    monkeypatch.setenv("GLM_API_KEY", "sk-or-test")
    monkeypatch.setenv("GLM_BASE_URL", OR)
    monkeypatch.setenv("GLM_MODEL", "z-ai/glm-5.3-flash")
    monkeypatch.setenv("CONSOLE_STREAM", "true")
    monkeypatch.setenv("HARD_DETECT", "false")
    monkeypatch.setenv("LLM_RETRIES", "0")
    _adaptive(monkeypatch)
    from app.agent import llm, run_turn
    from app.db import Message, session
    from app.events import bus
    from sqlalchemy import select
    bodies = []
    SECRET_THOUGHT = "PRIVATE-REASONING-xyz"

    def handler(req):
        b = json.loads(req.content)
        bodies.append(b)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=_sse(
            {"choices": [{"delta": {"reasoning": SECRET_THOUGHT + " thinking it over."}}]},
            {"choices": [{"delta": {"content": "Here is my answer for you."}, "finish_reason": "stop"}],
             "usage": {"prompt_tokens": 50, "completion_tokens": 9}}))

    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    conv = _conv()
    evs = []

    async def go(text):
        q = bus.subscribe(conv)
        out = await run_turn(conv, text, tenant_id="default")
        while not q.empty():
            evs.append(q.get_nowait())
        bus.unsubscribe(conv, q)
        return out

    try:
        asyncio.run(go("namaste"))
        asyncio.run(go("What should I write in the invoice note for Ravi?"))
    finally:
        llm.set_http(None)
        llm.REASONING_NOW.set("")
    chat = [b for b in bodies if b.get("stream")]
    assert chat, "the chat brain was not GLM"
    assert chat[0]["reasoning"] == {"effort": "low", "exclude": False}
    assert chat[-1]["reasoning"] == {"effort": "medium", "exclude": False}
    assert SECRET_THOUGHT not in json.dumps(chat[-1]["messages"])           # never sent back to the model
    thinks = "".join((e["payload"] or {}).get("text", "") for e in evs if e["kind"] == "think")
    assert SECRET_THOUGHT in thinks                                          # shown on the Soch card
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == conv)).all()
        assert rows and all(SECRET_THOUGHT not in json.dumps([r.content, r.display]) for r in rows)
