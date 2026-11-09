"""v0.724 SAARI BAAT (owner: "GLM IS NOT ISSUE... MIGHT BE ISSUE IN OUR CODE --- CHECK IT PROPERLY"). Measured: with the
GLM door on, the chat's token cap (40k, v0.707) counted the system prompt + tool list - ~33k tokens on a test server,
more on hers - so the CONVERSATION had ~7k tokens and every real chat was shortened or dropped on every GLM turn.
The cap is now the conversation's own room, on top of the fixed part."""
from __future__ import annotations

import asyncio

import pytest

from app.agent import context, run_turn, set_client
from tests.test_v0237_full_context import Model, _settings
from tests.test_v108_memory import conv

ASK = "Want me to make a full PDF report on any one of these?"


@pytest.fixture()
def gauge(env, monkeypatch):
    from app import glmdoor
    from app.config import get_settings
    for k in ("CHAT_CONTEXT_LIMIT_CLAUDE", "CHAT_CONTEXT_LIMIT_GLM", "CHAT_CONTEXT_MAX_TOKENS_GLM", "QUICK_LANE",
              "CHAT_APPROVAL_WORDS"):
        monkeypatch.delenv(k, raising=False)       # the real defaults, not the old suites' pins
    get_settings.cache_clear()
    monkeypatch.setattr(context, "RATIO", {})
    monkeypatch.setattr(context, "LIMIT_SEEN", {})
    monkeypatch.setattr(context, "LAST", {})
    monkeypatch.setattr(context, "FIXED_SEEN", {})
    monkeypatch.setattr(glmdoor, "active", lambda: True)
    return context


def _chat(c, n=3, reply_chars=9000):
    from app.db import Message, session
    with session() as s:
        for i in range(n):
            s.add(Message(conversation_id=c, role="user", content=f"sawaal {i}", display=f"sawaal {i}"))
            body = f"jawab {i} " + "lambi baat " * (reply_chars // 11) + (ASK if i == n - 1 else "")
            s.add(Message(conversation_id=c, role="assistant", content=[{"type": "text", "text": body}], display=body))


def test_every_chat_has_a_million_token_window(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_COMPACT="false")
    for b in ("claude", "glm", "omniroute"):
        assert gauge.window(b) == 1_000_000      # owner: "MAKE IT 1 MILLION CONTEXT WINDOW FOR EVERY CHAT"


def test_a_smaller_real_window_is_learned_from_the_models_error(gauge):
    gauge.overflowed("claude", "maximum context length is 262144 tokens, requested 300000")
    assert gauge.window("claude") == 262144


def test_glm_room_if_set_is_on_top_of_the_fixed_part(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_COMPACT="false", CHAT_CONTEXT_MAX_TOKENS_GLM=40000)
    gauge.FIXED_SEEN["claude"] = 33000
    assert abs(gauge.budget("claude") - (40000 + 33000)) <= 1


def test_a_normal_glm_chat_goes_whole(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_COMPACT="false")
    c = conv()
    _chat(c)                                  # three long answers, ~27k characters of conversation
    m = Model()
    set_client(m)
    asyncio.run(run_turn(c, "YES", tenant_id="default"))
    r = gauge.LAST[c]
    assert r["form"] == "full", r             # before v0.724: 'net' - the chat was shortened on a 3-message chat
    sent = str(m.sent[0]["messages"])
    assert ASK in sent and "jawab 0" in sent


def test_a_users_own_cap_still_means_the_whole_request(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_CONTEXT_MAX_TOKENS=50000)
    gauge.FIXED_SEEN["claude"] = 33000
    assert abs(gauge.budget("claude") - 50000) <= 1


def test_glm_clears_old_tool_results_later():
    from app.agent import prune
    assert prune.CLEAR_TRIGGER_GLM >= 30000


def test_every_message_reaches_the_model(gauge):
    from app.config import get_settings
    s = get_settings()
    assert s.quick_lane is False and s.chat_approval_words is False


def test_a_bare_haan_goes_to_the_model_with_the_chat(gauge, monkeypatch):
    """A waiting PC step card + her 'haan': with Claude's handling the model reads it (it may still approve the card
    with haan_karo, seeing its own last reply); nothing answers before the model."""
    from app.bazar import service
    called = []
    monkeypatch.setattr(service, "voice_approve", lambda *a, **k: called.append(a) or {"say": "approved"})
    c = conv()
    m = Model()
    set_client(m)
    asyncio.run(run_turn(c, "haan", tenant_id="default"))
    assert not called and m.sent                    # the model got the turn


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.split(".")[1] >= "724"
