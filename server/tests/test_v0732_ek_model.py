"""v0.732 PARITY PHASE 1 EK MODEL (owner: "WE WILL KEEP GLM 5.3 FLASH AS PRIMARY FOR ALL FOR NOW --- PHASE 0 + 1").

A chat runs on ONE model from start to end, like Claude chat: the configured chat brain (GLM-5.3-Flash on her server).
Before: a GLM failure answered the same step on Claude, two failures moved every chat to Claude for 10 minutes, and on
a Claude setup an ask was split across Haiku / Sonnet / Opus by its size. Now the same model is asked again, then the
turn says plainly it is busy. The one exception kept: a PDF / picture the chat brain cannot read goes to Claude."""
from __future__ import annotations

import asyncio

import pytest


@pytest.fixture()
def one(env, monkeypatch):
    from app.agent import llm
    from app.config import get_settings
    monkeypatch.delenv("CHAT_ONE_MODEL", raising=False)       # the real default, not the old suites' pin
    monkeypatch.setenv("GLM_API_KEY", "test-glm")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-claude")
    monkeypatch.setenv("CHAT_LLM", "glm")
    monkeypatch.setenv("CHAT_MODEL_RETRY_S", "0")
    get_settings.cache_clear()
    monkeypatch.setitem(llm.BREAKERS, "glm", {"fails": 0, "until": 0.0, "paused": 0})
    yield get_settings()
    get_settings.cache_clear()


def test_one_model_is_the_default(one):
    assert one.chat_one_model is True and one.chat_model_retries >= 1


def test_a_paused_glm_is_still_the_chats_model(one, monkeypatch):
    import time
    from app.agent import llm
    llm.BREAKERS["glm"]["until"] = time.time() + 600          # the safety switch paused GLM
    assert llm.cheap_brain() is None                         # background calls go to Claude meanwhile ...
    assert llm.choose([{"role": "user", "content": "hello"}]) == "glm"   # ... the chat does not move
    monkeypatch.setenv("CHAT_ONE_MODEL", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert llm.choose([{"role": "user", "content": "hello"}]) == "claude"   # the old behaviour, switch off


def test_a_pdf_still_goes_to_the_model_that_reads_it(one):
    from app.agent import llm
    pdf = [{"role": "user", "content": [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                                       "data": "JVBERi0="}},
                                        {"type": "text", "text": "summarise"}]}]
    assert llm.choose(pdf) == "claude"


def test_no_split_by_ask_size(one):
    from app.agent.santosh import model_for
    assert model_for(one, hard=True, long_job=False) == ""     # was agent_hard_model (Opus)
    assert model_for(one, hard=False, long_job=False) == ""    # was chat_simple_model (Haiku)
    assert model_for(one, hard=False, long_job=True) == ""


def _fake_brain(monkeypatch, errors):
    from app.agent import santosh
    seen = []

    async def call(brain, system, history, settings, tools=None, live=None, max_tokens=None, think=False):
        seen.append(brain)
        if errors:
            raise RuntimeError(errors.pop(0))
        return [{"type": "text", "text": "ok"}], "end_turn"
    monkeypatch.setattr(santosh, "_call_brain", call)
    return seen


def test_a_busy_glm_is_asked_again_never_claude(one, monkeypatch):
    from app.agent import santosh
    seen = _fake_brain(monkeypatch, ["GLM not reachable: timed out (ReadTimeout)", "GLM error 503: busy"])
    blocks, stop, used = asyncio.run(santosh._think("glm", "sys", [{"role": "user", "content": "hi"}], one))
    assert seen == ["glm", "glm", "glm"] and used == "glm" and blocks[0]["text"] == "ok"


def test_a_glm_that_stays_down_says_so_instead_of_switching(one, monkeypatch):
    from app.agent import santosh
    seen = _fake_brain(monkeypatch, ["GLM error 503: busy"] * 5)
    with pytest.raises(RuntimeError, match="503"):
        asyncio.run(santosh._think("glm", "sys", [{"role": "user", "content": "hi"}], one))
    assert "claude" not in seen and len(seen) == 1 + one.chat_model_retries
    line = santosh._friendly_error(RuntimeError("GLM error 503: busy"))
    assert "busy or unreachable" in line                       # the plain line she reads


def test_a_wrong_key_is_not_asked_again(one, monkeypatch):
    from app.agent import santosh
    seen = _fake_brain(monkeypatch, ["GLM error 401: invalid api key"] * 3)
    with pytest.raises(RuntimeError):
        asyncio.run(santosh._think("glm", "sys", [{"role": "user", "content": "hi"}], one))
    assert seen == ["glm"]


def test_the_old_fallback_stays_behind_the_switch(one, monkeypatch):
    from app.agent import santosh
    from app.config import get_settings
    monkeypatch.setenv("CHAT_ONE_MODEL", "false")
    get_settings.cache_clear()
    seen = _fake_brain(monkeypatch, ["GLM error 503: busy"])
    asyncio.run(santosh._think("glm", "sys", [{"role": "user", "content": "hi"}], get_settings()))
    assert seen == ["glm", "claude"]
