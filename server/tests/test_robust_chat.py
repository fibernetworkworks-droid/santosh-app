"""v0.36: the chat brain survives a busy model, a hung tool, an empty answer and a retried send."""
import asyncio

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_campaign_flow import ScriptedClaude, text, tool


def _glm_env(monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "glm-test")
    from app.config import get_settings
    get_settings.cache_clear()


def _ok(content):
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": content}}]})


def test_busy_model_is_retried_before_falling_back(bz, monkeypatch):  # noqa: F811
    _glm_env(monkeypatch)
    from app.agent import llm, run_turn
    monkeypatch.setattr(llm, "RETRY_DELAY", 0.01)
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503, text="busy") if len(calls) < 3 else _ok("Ab chal gaya")

    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        out = asyncio.run(run_turn(bz["conv"], "namaste", tenant_id="default"))
    finally:
        llm.set_http(None)
    assert out == "Ab chal gaya" and len(calls) == 3      # two busy answers, then success: Claude was never needed


def test_wrong_key_is_not_retried(bz, monkeypatch):  # noqa: F811
    _glm_env(monkeypatch)
    from app.agent import llm
    monkeypatch.setattr(llm, "RETRY_DELAY", 0.01)
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(401, text="bad key")

    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        with pytest.raises(llm.LLMError):
            asyncio.run(llm.openai_create("glm", "sys", [], [{"role": "user", "content": "hi"}], 100))
    finally:
        llm.set_http(None)
    assert len(calls) == 1


def test_claude_down_falls_back_to_the_cheap_brain(bz, monkeypatch):  # noqa: F811
    """Plain text: when Claude fails, the low-cost brain still answers."""
    _glm_env(monkeypatch)
    from app.agent import llm, run_turn, set_client

    class DownClaude:
        class messages:
            @staticmethod
            async def create(**_):
                raise RuntimeError("claude is down")

    set_client(DownClaude())
    monkeypatch.setattr(llm, "choose", lambda msgs: "claude")
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: _ok("Cheap brain ne jawab diya"))))
    try:
        out = asyncio.run(run_turn(bz["conv"], "namaste", tenant_id="default"))
    finally:
        llm.set_http(None)
    assert out == "Cheap brain ne jawab diya"


def test_hung_tool_is_stopped_and_the_turn_finishes(bz, monkeypatch):  # noqa: F811
    monkeypatch.setenv("AGENT_TOOL_TIMEOUT_S", "5")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import run_turn, santosh, set_client

    async def hangs(name, args, ctx):
        await asyncio.sleep(60)

    monkeypatch.setattr(santosh, "dispatch", hangs)
    set_client(ScriptedClaude([tool("list_reminders", {}, 1), text("Reminders abhi nahi mil paye, baad mein dekhte hain")]))
    out = asyncio.run(asyncio.wait_for(run_turn(bz["conv"], "reminders batao", tenant_id="default"), 30))
    assert "nahi mil paye" in out


def test_turn_that_runs_forever_releases_the_chat(bz, monkeypatch):  # noqa: F811
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import run_turn, santosh, set_client

    orig = santosh._think
    state = {"n": 0}

    async def stuck_once(*a, **k):
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(120)
        return await orig(*a, **k)

    monkeypatch.setattr(santosh, "_think", stuck_once)
    set_client(ScriptedClaude([text("Haan bataiye")]))

    async def go():
        first = await asyncio.wait_for(run_turn(bz["conv"], "hello", tenant_id="default"), 45)
        second = await asyncio.wait_for(run_turn(bz["conv"], "dobara", tenant_id="default"), 10)   # the chat is free again
        return first, second

    first, second = asyncio.run(go())
    assert "rok diya" in first and second == "Haan bataiye"


def test_silent_model_never_leaves_an_empty_chat(bz, monkeypatch):  # noqa: F811
    from app.agent import run_turn, set_client
    set_client(ScriptedClaude([tool("list_reminders", {}, 1), []]))
    out = asyncio.run(run_turn(bz["conv"], "reminders", tenant_id="default"))
    assert out.strip()


def test_friendly_error_for_a_busy_service():
    from app.agent.llm import LLMError
    from app.agent.santosh import _friendly_error
    assert "busy" in _friendly_error(LLMError("GLM error 503: x"))
    assert "gadbad" in _friendly_error(ValueError("weird"))


def test_retried_send_runs_once(env):
    from fastapi.testclient import TestClient
    from app import main
    from app.agent import set_client
    set_client(ScriptedClaude([text("Ek hi baar"), text("Doosra"), text("Teesra")]))
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        r1 = c.post(f"/api/conversations/{conv}/messages", json={"text": "hello", "client_id": "abc123"})
        r2 = c.post(f"/api/conversations/{conv}/messages", json={"text": "hello", "client_id": "abc123"})
        r3 = c.post(f"/api/conversations/{conv}/messages", json={"text": "hello", "client_id": "other"})
        r4 = c.post(f"/api/conversations/{conv}/messages", json={"text": "hello"})
    assert r1.json() == {"accepted": True} and r2.json() == {"accepted": True, "duplicate": True}
    assert r3.json() == {"accepted": True} and r4.json() == {"accepted": True}
