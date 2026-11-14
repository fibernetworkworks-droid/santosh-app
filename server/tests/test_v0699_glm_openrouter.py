"""v0.699 GLM VIA OPENROUTER (owner: "lets go with glm 5.3 flash - via openrouter").

OpenRouter speaks its OWN reasoning field; Z.ai's "thinking" and NVIDIA's reasoning_effort never ride there.
All offline: a fake OpenRouter endpoint.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

OR = "https://openrouter.ai/api/v1"


@pytest.fixture
def orr(monkeypatch):
    from app.config import get_settings
    from app.agent import llm
    st = get_settings()
    for k, v in {"glm_api_key": "sk-or-test", "glm_base_url": OR, "glm_model": "z-ai/glm-5.3-flash",
                 "glm_thinking": "disabled", "llm_retries": 0}.items():
        monkeypatch.setattr(st, k, v)
    seen = {"bodies": [], "refuse": False}

    def h(req: httpx.Request):
        body = json.loads(req.content)
        seen["bodies"].append(body)
        assert str(req.url) == OR + "/chat/completions"
        if seen["refuse"] and "reasoning" in body:
            return httpx.Response(400, json={"error": "unknown field reasoning"})
        return httpx.Response(200, json={"id": "c1", "model": "z-ai/glm-5.3-flash",
                                         "choices": [{"message": {"role": "assistant", "content": "namaste"},
                                                      "finish_reason": "stop"}],
                                         "usage": {"prompt_tokens": 5, "completion_tokens": 2}})
    llm.set_http(httpx.AsyncClient(transport=httpx.MockTransport(h)))
    yield st, seen
    llm.set_http(None)


def _ask():
    from app.agent import llm
    return asyncio.run(llm._openai_create("glm", "sys", [], [{"role": "user", "content": "hi"}], 500))


def test_openrouter_reasoning_low_never_off(orr):
    from app.agent import llm
    st, seen = orr
    assert llm.is_openrouter() and not llm.is_nvidia()
    url, model, label, headers, extra = llm._target("glm")
    assert label == "GLM (OpenRouter)" and model == "z-ai/glm-5.3-flash"
    assert headers["Authorization"] == "Bearer sk-or-test"
    # v0.700: OpenRouter's GLM refuses {"enabled": false} ("Reasoning is mandatory") - always effort low + room
    assert extra == {"reasoning": {"effort": "low", "exclude": True}}
    assert llm.room(500) > 500
    _ask()
    b = seen["bodies"][0]
    assert b["reasoning"] == {"effort": "low", "exclude": True} and b["max_tokens"] > 500
    for bad in ("thinking", "reasoning_effort", "chat_template_kwargs"):
        assert bad not in b


def test_openrouter_reasoning_on_gets_effort_and_room(orr, monkeypatch):
    from app.agent import llm
    st, _ = orr
    monkeypatch.setattr(st, "glm_thinking", "enabled")
    monkeypatch.setattr(st, "glm_reasoning_effort", "low")
    _, _, _, _, extra = llm._target("glm")
    assert extra == {"reasoning": {"effort": "low", "exclude": True}}
    assert llm.room(500) > 500


def test_openrouter_refusing_reasoning_is_asked_again_plain(orr):
    st, seen = orr
    seen["refuse"] = True
    _ask()
    assert len(seen["bodies"]) == 2 and "reasoning" not in seen["bodies"][1]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.902.0"
