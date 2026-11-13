"""v0.878 CREDIT ROKE NAHI (owner: "SUDDENLY IN BETWEEN SAYING CREDIT LIMIT IS OVER AND STOP THE WORK --- FIX THIS
FIRST"): OpenRouter's 402 "would exceed your available credits given your current in-flight requests" no longer kills
a PC task - the step waits and asks again with less output room; a truly empty account ends the task as partial with
a plain line, never 'failed'."""
import asyncio

import pytest

from app.agent import llm
from app.pc import brain, operator


@pytest.fixture
def route(monkeypatch):
    monkeypatch.setattr(brain, "qwen_route", lambda: ("https://openrouter.ai/api/v1/chat/completions", "k", "or"))
    real = asyncio.sleep
    monkeypatch.setattr(brain.asyncio, "sleep", lambda s: real(0))


OK = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}


def test_credit_hold_waits_and_asks_for_less_room(monkeypatch, route):
    seen = []

    async def post(url, key, body, timeout):
        seen.append(body["max_tokens"])
        if len(seen) < 3:
            raise brain.QwenError(402, "This request would exceed your available credits given your current in-flight")
        return OK
    monkeypatch.setattr(brain, "_post", post)
    rep = asyncio.run(brain.think_qwen("qwen/qwen3.8-27b", "s", [{"role": "user", "content": "x"}], [], 4000))
    assert seen == [4000, 2000, 1000]


def test_empty_account_raises_credit_low(monkeypatch, route):
    async def post(url, key, body, timeout):
        raise brain.QwenError(402, "add credits")
    monkeypatch.setattr(brain, "_post", post)
    with pytest.raises(brain.CreditLow):
        asyncio.run(brain.think_qwen("qwen/qwen3.8-27b", "s", [{"role": "user", "content": "x"}], [], 4000))


def test_credit_body_floor():
    assert llm.credit_body({"max_tokens": 4000})["max_tokens"] == 2000
    assert llm.credit_body({"max_tokens": 1200}) is None
    assert llm.credit_402(402) and not llm.credit_402(429)


def test_task_ends_partial_with_a_plain_line(monkeypatch):
    async def fake_pc(op, action, args=None, timeout=40, log=True):
        return {"image_b64": "SU1H", "width": 10, "height": 10, "active_window": "Chrome", "windows": ["Chrome"]}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)

    async def think(op, client, messages, params, retry):
        raise brain.CreditLow(402, "add credits")
    monkeypatch.setattr(brain, "think", think)
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    op = operator.Op(id="t", tenant="default", conv="c", task="Swiggy kholo")
    asyncio.run(operator._run(op))
    assert op.status == "partial" and "openrouter.ai" in op.summary and "credit" in op.reason


def test_chat_door_retries_a_credit_hold(monkeypatch):
    import httpx
    sizes = []

    class C:
        async def post(self, url, json=None, headers=None, **kw):
            sizes.append(json["max_tokens"])
            code = 402 if len(sizes) < 2 else 200
            return httpx.Response(code, json={"error": {"message": "in-flight"}} if code == 402 else {"ok": 1},
                                  request=httpx.Request("POST", url))
    monkeypatch.setattr(llm, "_client", lambda: C())
    real = asyncio.sleep
    monkeypatch.setattr(llm.asyncio, "sleep", lambda s: real(0))
    r = asyncio.run(llm._post_with_retry("https://openrouter.ai/x", {"max_tokens": 8000}, {}, "OpenRouter"))
    assert r.status_code == 200 and sizes == [8000, 4000]
