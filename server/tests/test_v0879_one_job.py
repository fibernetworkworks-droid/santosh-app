"""v0.879 EK KAAM EK BAAR (owner: "FIX ALL" on the log review): (A) on a call, while her PC is in use, a second ask
waits for the first instead of a side record steering the same PC task; (B) a PC step the AI does not answer in time
is said on the call and tried once more, then the task ends partial - never minutes of silence; (C) a PC step holds
1500 output tokens of credit, not 4000."""
import asyncio
import types

import httpx
import pytest

from app.config import get_settings
from app.pc import brain, operator


def test_pc_step_defaults_smaller_and_faster():
    get_settings.cache_clear()
    st = get_settings()
    assert st.pc_max_tokens == 1500 and st.pc_brain_timeout_s <= 40


@pytest.fixture
def route(monkeypatch):
    monkeypatch.setattr(brain, "qwen_route", lambda: ("https://openrouter.ai/api/v1/chat/completions", "k", "or"))


def test_slow_step_is_said_then_retried_once(monkeypatch, route):
    calls, told = [], []

    async def post(url, key, body, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow")
        return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}
    monkeypatch.setattr(brain, "_post", post)
    asyncio.run(brain.think_qwen("qwen/qwen3.8-27b", "s", [{"role": "user", "content": "x"}], [], 1500,
                                 on_slow=lambda: told.append(1)))
    assert len(calls) == 2 and told == [1]


def test_slow_twice_raises_brain_slow(monkeypatch, route):
    async def post(url, key, body, timeout):
        raise httpx.ReadTimeout("slow")
    monkeypatch.setattr(brain, "_post", post)
    with pytest.raises(brain.BrainSlow):
        asyncio.run(brain.think_qwen("qwen/qwen3.8-27b", "s", [{"role": "user", "content": "x"}], [], 1500))


def test_slow_task_ends_partial(monkeypatch):
    async def fake_pc(op, action, args=None, timeout=40, log=True):
        return {"image_b64": "SU1H", "width": 10, "height": 10, "active_window": "Chrome", "windows": ["Chrome"]}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)

    async def think(op, client, messages, params, retry):
        raise brain.BrainSlow(504, "slow")
    monkeypatch.setattr(brain, "think", think)
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    op = operator.Op(id="t", tenant="default", conv="c", task="Aadhaar")
    asyncio.run(operator._run(op))
    assert op.status == "partial" and "did not answer" in op.summary


def test_call_ask_waits_while_her_pc_is_in_use(monkeypatch):
    from app import voice
    from app.agent import santosh as _brain
    call = voice.Call.__new__(voice.Call)
    call.conv, call.call_id, call.stats = "conv_call", "cid", {}
    call.ctx = types.SimpleNamespace(tenant_id="t1")
    call._claimed = {"conv_call": 1}               # the first ask still holds the call record
    opened = []
    from app import callconv
    monkeypatch.setattr(callconv, "open_side", lambda *a: opened.append(1) or "side1")
    monkeypatch.setattr(operator, "her_pc_recent", lambda t, s=0: True)
    assert call._run_conv() == "conv_call" and not opened and call.stats["pc_queued"] == 1
    monkeypatch.setattr(operator, "her_pc_recent", lambda t, s=0: False)
    monkeypatch.setattr(operator, "running_all", lambda t: [])
    assert call._run_conv() == "side1" and opened == [1]   # no PC work: the old side record still runs it now
