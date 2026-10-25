"""Low-cost GLM brain: format conversion, a full tool-using turn, and Claude fallback when GLM is down."""
import asyncio
import json

import httpx
import pytest

from tests.test_bazar import _events, bz  # noqa: F401  (fixture)


def _glm_env(monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "glm-test")
    from app.config import get_settings
    get_settings.cache_clear()


def test_conversion_roundtrip():
    from app.agent import llm
    msgs = [
        {"role": "user", "content": "bill bhar do"},
        {"role": "assistant", "content": [{"type": "text", "text": "Dekhta hoon"},
                                          {"type": "tool_use", "id": "t1", "name": "bazar_find", "input": {"query": "msedcl"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{\"packs\": []}"},
                                     {"type": "text", "text": "[worker] note"}]},
    ]
    out, fns = llm.to_openai("SYS", [{"name": "bazar_find", "description": "d", "input_schema": {"type": "object"}}], msgs)
    assert [m["role"] for m in out] == ["system", "user", "assistant", "tool", "user"]
    assert out[2]["tool_calls"][0]["function"]["name"] == "bazar_find"
    assert out[3]["tool_call_id"] == "t1"
    assert fns[0]["function"]["parameters"] == {"type": "object"}
    blocks, stop = llm.from_openai({"choices": [{"message": {"content": "", "tool_calls": [
        {"id": "call:9/x", "function": {"name": "bazar_run", "arguments": "{\"pack_id\": \"a\"}"}}]}}]})
    assert stop == "tool_use" and blocks[0]["input"] == {"pack_id": "a"} and blocks[0]["id"] == "call_9_x"


def test_glm_runs_a_tool_turn(bz, monkeypatch):  # noqa: F811
    _glm_env(monkeypatch)
    from app.agent import llm, run_turn
    from app import chats as chats_mod
    async def _no_title(tenant, conv):     # v0.162 auto-title fires in the background and would race the call count
        return ""
    monkeypatch.setattr(chats_mod, "auto_title", _no_title)
    calls = []

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        calls.append(body)
        assert req.headers["authorization"] == "Bearer glm-test"
        assert body["model"] == "glm-4.7" and body["thinking"] == {"type": "disabled"}
        if body.get("stream"):   # v0.170 CONSOLE_V2 streams the turn: the same answers as SSE chunks
            if len(calls) == 1:
                chunks = [{"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1",
                           "function": {"name": "bazar_find", "arguments": "{\"query\": \"msedcl bijli bill\"}"}}]}}]},
                          {"choices": [{"delta": {}, "finish_reason": "tool_calls"}],
                           "usage": {"prompt_tokens": 10, "completion_tokens": 5}}]
            else:
                assert body["messages"][-1]["role"] == "tool"
                assert "msedcl" in body["messages"][-1]["content"]
                chunks = [{"choices": [{"delta": {"content": "MSEDCL mil gaya."}}]}]
            sse = b"".join(b"data: " + json.dumps(c).encode() + b"\n\n" for c in chunks) + b"data: [DONE]\n\n"
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse)
        if len(calls) == 1:
            return httpx.Response(200, json={"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "bazar_find", "arguments": "{\"query\": \"msedcl bijli bill\"}"}}]}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        assert body["messages"][-1]["role"] == "tool"
        assert "msedcl" in body["messages"][-1]["content"]
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "MSEDCL mil gaya."}}]})

    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        out = asyncio.run(run_turn(bz["conv"], "MSEDCL ka bill", tenant_id="default"))
    finally:
        llm.set_http(None)
    assert out == "MSEDCL mil gaya." and len(calls) == 2


def test_glm_down_falls_back_to_claude(bz, monkeypatch):  # noqa: F811
    _glm_env(monkeypatch)
    from app.agent import llm, run_turn, set_client
    from tests.test_campaign_flow import ScriptedClaude, text
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503, text="busy"))))
    set_client(ScriptedClaude([text("Claude se jawab")]))
    try:
        out = asyncio.run(run_turn(bz["conv"], "namaste", tenant_id="default"))
    finally:
        llm.set_http(None)
    assert out == "Claude se jawab"


def test_choose(monkeypatch, env):
    from app.agent import llm
    assert llm.choose([{"role": "user", "content": "hi"}]) == "claude"   # no GLM key
    _glm_env(monkeypatch)
    assert llm.choose([{"role": "user", "content": "hi"}]) == "glm"
    assert llm.choose([{"role": "user", "content": [{"type": "image", "source": {}}]}]) == "claude"
    monkeypatch.setenv("CHAT_LLM", "claude")
    from app.config import get_settings
    get_settings.cache_clear()
    assert llm.choose([{"role": "user", "content": "hi"}]) == "claude"


def test_omniroute_brain(bz, monkeypatch):  # noqa: F811
    """OmniRoute gateway: picked first in auto mode, keeps tool results uncompressed, falls back to Claude."""
    monkeypatch.setenv("GLM_API_KEY", "glm-test")
    monkeypatch.setenv("OMNIROUTE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("OMNIROUTE_KEY", "sk-omni")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import llm, run_turn, set_client
    from tests.test_campaign_flow import ScriptedClaude, text
    assert llm.choose([{"role": "user", "content": "hi"}]) == "omniroute" and llm.describe() == "omniroute:santosh"
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        body = json.loads(req.content)
        assert str(req.url) == "http://127.0.0.1:20128/v1/chat/completions"
        assert req.headers["authorization"] == "Bearer sk-omni" and req.headers["x-omniroute-compression"] == "off"
        assert body["model"] == "santosh" and "thinking" not in body
        if body.get("stream"):   # v0.170 CONSOLE_V2 streams the turn
            sse = b"data: " + json.dumps({"choices": [{"delta": {"content": "Namaste ji"}}]}).encode() + b"\n\n" + b"data: [DONE]\n\n"
            return httpx.Response(200, headers={"x-omniroute-decision": "strategy=priority; provider=deepseek",
                                                "content-type": "text/event-stream"}, content=sse)
        return httpx.Response(200, headers={"x-omniroute-decision": "strategy=priority; provider=deepseek"},
                              json={"choices": [{"message": {"content": "Namaste ji"}}]})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        assert asyncio.run(run_turn(bz["conv"], "namaste", tenant_id="default")) == "Namaste ji"
        llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(502, text="all providers down"))))
        set_client(ScriptedClaude([text("Claude yahan hai")]))
        assert asyncio.run(run_turn(bz["conv"], "phir se", tenant_id="default")) == "Claude yahan hai"
    finally:
        llm.set_http(None)
    monkeypatch.setenv("CHAT_LLM", "glm")
    get_settings.cache_clear()
    assert llm.choose([{"role": "user", "content": "hi"}]) == "glm"
