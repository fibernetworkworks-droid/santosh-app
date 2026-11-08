"""SAB GLM (owner: "NOW LETS USE GLM 5.3 FLASH FOR ALL USE --- AS NVIDIA PROVIDING FREE API ... FIND THE WAY").

Every Claude call passes ONE door (the Anthropic SDK, wrapped in usage.install). With claude_all_glm on, that door
answers from NVIDIA's free z-ai/glm-5.3-flash and hands back a real anthropic Message; Claude only when GLM fails.
All offline: a fake NVIDIA endpoint and a fake Anthropic endpoint.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

NV = "https://integrate.api.nvidia.com/v1"


def _anth_reply(text="from claude"):
    return {"id": "msg_x", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 3, "output_tokens": 2}}


@pytest.fixture
def glm(monkeypatch):
    from app import usage
    from app.config import get_settings
    from app.agent import llm
    usage.install()
    st = get_settings()
    for k, v in {"claude_all_glm": True, "glm_api_key": "nvapi-test", "glm_base_url": NV,
                 "glm_model": "z-ai/glm-5.3-flash", "anthropic_api_key": "sk-test", "llm_retries": 0}.items():
        monkeypatch.setattr(st, k, v)
    seen = {"glm": [], "claude": 0, "glm_status": 200, "reply": None}

    def nv(req: httpx.Request):
        body = json.loads(req.content)
        seen["glm"].append(body)
        if seen["glm_status"] != 200:
            return httpx.Response(seen["glm_status"], json={"error": "busy"})
        msg = seen["reply"] or {"role": "assistant", "content": "GLM se jawab"}
        return httpx.Response(200, json={"id": "c1", "model": "z-ai/glm-5.3-flash",
                                         "choices": [{"message": msg, "finish_reason": "stop"}],
                                         "usage": {"prompt_tokens": 11, "completion_tokens": 4}})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(nv)))
    real_client = httpx.Client

    def fake_client(*a, **k):
        k.pop("transport", None)
        return real_client(transport=httpx.MockTransport(nv))
    monkeypatch.setattr("app.glmdoor.httpx.Client", fake_client)

    def anth(req):
        import httpx2
        seen["claude"] += 1
        return httpx2.Response(200, json=_anth_reply())
    import anthropic
    import httpx2
    seen["aclient"] = anthropic.AsyncAnthropic(api_key="sk-test",
                                               http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(anth)))
    seen["sclient"] = anthropic.Anthropic(api_key="sk-test", http_client=httpx2.Client(transport=httpx2.MockTransport(anth)))
    yield seen
    llm.set_http(None)


def test_off_by_default():
    from app.config import Settings
    assert Settings().claude_all_glm is False


def test_every_claude_call_is_answered_by_glm(glm):
    m = asyncio.run(glm["aclient"].messages.create(model="claude-sonnet-5-5", max_tokens=900, system="sys",
                                                     messages=[{"role": "user", "content": "namaste"}]))
    assert m.content[0].text == "GLM se jawab" and m.model == "z-ai/glm-5.3-flash" and glm["claude"] == 0
    b = glm["glm"][-1]
    assert b["model"] == "z-ai/glm-5.3-flash" and b["reasoning_effort"] == "low"
    assert b["chat_template_kwargs"] == {"clear_thinking": True} and b["max_tokens"] == 900 + 2048
    assert "thinking" not in b                                   # Z.ai's own field is not sent to NVIDIA
    s = glm["sclient"].messages.create(model="claude-haiku-5-5", max_tokens=100,
                                       messages=[{"role": "user", "content": "hi"}])
    assert s.content[0].text == "GLM se jawab" and glm["claude"] == 0


def test_tool_calls_come_back_as_real_blocks(glm):
    glm["reply"] = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": '{"city": "Pune"}'}}]}
    m = asyncio.run(glm["aclient"].messages.create(
        model="claude-haiku-5-5", max_tokens=200, messages=[{"role": "user", "content": "Pune ka mausam"}],
        tools=[{"name": "get_weather", "description": "w", "input_schema": {"type": "object", "properties": {}}}],
        tool_choice={"type": "tool", "name": "get_weather"}))
    tu = [b for b in m.content if b.type == "tool_use"][0]
    assert tu.name == "get_weather" and tu.input == {"city": "Pune"} and m.stop_reason == "tool_use"
    assert glm["glm"][-1]["tool_choice"] == {"type": "function", "function": {"name": "get_weather"}}


def test_glm_down_means_claude_answers(glm):
    glm["glm_status"] = 500
    m = asyncio.run(glm["aclient"].messages.create(model="claude-haiku-5-5", max_tokens=50,
                                                     messages=[{"role": "user", "content": "hi"}]))
    assert m.content[0].text == "from claude" and glm["claude"] == 1


def test_streams_ride_the_same_door(glm):
    async def go():
        async with glm["aclient"].messages.stream(model="claude-haiku-5-5", max_tokens=50,
                                                  messages=[{"role": "user", "content": "hi"}]) as st:
            texts = [ev.delta.text async for ev in st if getattr(ev, "type", "") == "content_block_delta"]
            return texts, await st.get_final_message()
    texts, m = asyncio.run(go())
    assert texts == ["GLM se jawab"] and m.content[0].text == "GLM se jawab" and glm["claude"] == 0
    with glm["sclient"].messages.stream(model="claude-haiku-5-5", max_tokens=50,
                                        messages=[{"role": "user", "content": "hi"}]) as st:
        assert st.get_final_message().content[0].text == "GLM se jawab"


def test_pictures_go_to_nvidia_glm_and_pdfs_to_claude(glm):
    from app import glmdoor
    from app.agent import llm
    img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"}}
    msgs, _ = llm.to_openai("s", [], [{"role": "user", "content": [{"type": "text", "text": "kya hai?"}, img]}])
    parts = msgs[-1]["content"]
    assert parts[1] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}
    assert not glmdoor.has_media([{"role": "user", "content": [img]}])
    assert glmdoor.has_media([{"role": "user", "content": [{"type": "document", "source": {}}]}])


def test_a_glm_answer_is_counted_once_at_glm_price(glm):
    from app import usage
    from types import SimpleNamespace
    seen = []
    orig = usage.record
    try:
        usage.record = lambda *a, **k: seen.append(a)
        usage.from_anthropic("claude-haiku-5-5", SimpleNamespace(model="z-ai/glm-5.3-flash",
                                                                 usage=SimpleNamespace(input_tokens=5, output_tokens=5)))
    finally:
        usage.record = orig
    assert seen == []


def test_an_endpoint_that_refuses_the_reasoning_fields_is_asked_again(glm, monkeypatch):
    from app.agent import llm
    calls = []

    def nv(req):
        b = json.loads(req.content)
        calls.append(b)
        if "reasoning_effort" in b:
            return httpx.Response(400, json={"error": "unknown field reasoning_effort"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(nv)))
    m = asyncio.run(glm["aclient"].messages.create(model="claude-haiku-5-5", max_tokens=50,
                                                     messages=[{"role": "user", "content": "hi"}]))
    assert m.content[0].text == "ok" and len(calls) == 2 and "reasoning_effort" not in calls[1]


def test_a_hung_glm_is_skipped_and_claude_answers_at_once(glm, monkeypatch):
    """Her live NVIDIA test: the model listed, every chat call hung with 0 bytes. Two failures -> GLM skipped."""
    from app.agent import llm
    from app import glmdoor

    def hang(req):
        raise httpx.ReadTimeout("no bytes", request=req)
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(hang)))
    llm.BREAKER.update({"fails": 0, "until": 0.0})
    for _ in range(2):
        m = asyncio.run(glm["aclient"].messages.create(model="claude-haiku-5-5", max_tokens=50,
                                                         messages=[{"role": "user", "content": "hi"}]))
        assert m.content[0].text == "from claude"
    assert llm.glm_paused() and not glmdoor.active() and llm.cheap_brain() in (None, "omniroute")
    n = glm["claude"]
    asyncio.run(glm["aclient"].messages.create(model="claude-haiku-5-5", max_tokens=50,
                                               messages=[{"role": "user", "content": "hi"}]))
    assert glm["claude"] == n + 1                    # straight to Claude, no wait on GLM
    llm.BREAKER.update({"fails": 0, "until": 0.0})


def test_one_glm_request_has_a_short_clock(glm):
    from app.agent import llm
    t = llm._glm_timeout()
    assert t.read == 45.0 and t.connect == 10


def test_a_nemotron_model_gets_a_plain_request(glm, monkeypatch):
    """Her key answered only NVIDIA's Nemotron models: GLM's own reasoning fields are not sent to them."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "glm_model", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    asyncio.run(glm["aclient"].messages.create(model="claude-haiku-5-5", max_tokens=100,
                                               messages=[{"role": "user", "content": "hi"}]))
    b = glm["glm"][-1]
    assert b["model"] == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert "reasoning_effort" not in b and "chat_template_kwargs" not in b and "thinking" not in b
