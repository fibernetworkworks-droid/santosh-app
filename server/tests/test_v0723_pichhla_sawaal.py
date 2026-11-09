"""v0.723 PICHHLA SAWAAL (owner, screenshot: Hoola ended a long answer with "Want me to make a full PDF report on any
one of these?", she wrote "YES", and Hoola answered "Koi pending approval card nahi mila ... Bataiye YES kis cheez ke
liye tha"). ROOT CAUSE: when the chat no longer fits (the GLM door caps it at 40k tokens) the safety net shortens old
exchanges in blocks of 10 - the PREVIOUS exchange included - and a shortened reply kept only its first 1,500
characters. A long answer's closing question / offer sits at its END, so the model never saw what she said yes to,
and the haan_karo tool ("any clear yes") looked like the only meaning of a bare YES."""
from __future__ import annotations

import pytest

from app import yaad
from app.agent import context

ASK = "Want me to make a full PDF report on any one of these (market, competition, build plan, cost)?"


def _settings(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture()
def gauge(env, monkeypatch):
    monkeypatch.setattr(context, "RATIO", {})
    monkeypatch.setattr(context, "LIMIT_SEEN", {})
    monkeypatch.setattr(context, "LAST", {})
    return context


def _long_answer() -> str:
    ideas = "\n\n".join(f"**#{i} Idea {i}** - " + "a detailed paragraph about the market and the build. " * 12
                        for i in range(1, 11))
    return ideas + "\n\nMy honest pick for you: #1.\n\n" + ASK


def _history():
    old = [{"role": "user", "content": "purani baat " + "y" * 300},
           {"role": "assistant", "content": [{"type": "text", "text": "theek hai " + "z" * 300}]}]
    prev = [{"role": "user", "content": "FIND THE 5 MILLION DOLLAR BUSINESS IDEA FOR AI SAAS PRODUCT"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "deploy_agents", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "R" * 60000}]},
            {"role": "assistant", "content": [{"type": "text", "text": _long_answer()}]}]
    return old + prev + [{"role": "user", "content": "YES"}]


def _text(msgs) -> str:
    out = []
    for m in msgs:
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        else:
            out += [str(b.get("text") or b.get("content") or "") for b in c if isinstance(b, dict)]
    return "\n".join(out)


def test_the_net_keeps_the_question_she_said_yes_to(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_CONTEXT_LIMIT_CLAUDE=20000, CHAT_COMPACT="false")
    hist = _history()
    out, form = gauge.fit(hist, "sys", [], "claude", "c-yes", turn_start=len(hist) - 1)
    assert form == "net"
    seen = _text(out)
    assert ASK in seen                                  # the offer she answered survives the shortening
    assert "R" * 5000 not in seen                       # ... while the big tool result is cut
    assert out[-1] == {"role": "user", "content": "YES"}


def test_squeeze_keeps_the_question_too(gauge):
    hist = _history()
    out = gauge.squeeze(hist, "c-yes", turn_start=len(hist) - 1)
    assert ASK in _text(out)


def test_a_shortened_reply_keeps_its_end():
    ex = [{"role": "user", "content": "kuch karo"},
          {"role": "assistant", "content": [{"type": "text", "text": _long_answer()}]}]
    body = yaad.compress(ex)[1]["content"][0]["text"]
    assert len(body) < 2000 and body.rstrip().endswith(ASK)


def test_haan_karo_is_not_the_meaning_of_every_yes():
    from app.agent.tools import TOOLS
    d = next(t for t in TOOLS if t["name"] == "haan_karo")["description"]
    assert "question" in d and "last reply" in d


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.723.0")
