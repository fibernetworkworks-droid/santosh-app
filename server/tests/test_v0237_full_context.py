"""v0.237 FULL CLAUDE MODE Phase 1: the whole chat word for word while it fits, the gauge with its safety net,
one retry after a "too long" answer, a clean error line, and a gauge that learns from real token counts."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent import run_turn, set_client
from app.db import Conversation, Message, session
from tests.test_v108_memory import add_exchange, conv


@pytest.fixture()
def gauge(env, monkeypatch):
    """A fresh gauge (its learned ratios / windows live in the process)."""
    from app.agent import context
    monkeypatch.setattr(context, "RATIO", {})
    monkeypatch.setattr(context, "LIMIT_SEEN", {})
    monkeypatch.setattr(context, "LAST", {})
    return context


def _settings(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    from app.config import get_settings
    get_settings.cache_clear()


class Model:
    """Scripted Claude: records every request; `fail` = how many first calls answer 'too long'."""

    def __init__(self, fail=0, error="prompt is too long: 250000 tokens > 200000 maximum", usage=None):
        self.sent, self.fail, self.error, self.usage = [], fail, error, usage
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.sent.append(json.loads(json.dumps({"system": kw.get("system"), "messages": kw["messages"]}, default=str)))
        if self.fail:
            self.fail -= 1
            raise RuntimeError(f"Error code: 400 - {{'error': {{'message': '{self.error}'}}}}")
        u = SimpleNamespace(input_tokens=self.usage, cache_read_input_tokens=0, cache_creation_input_tokens=0) \
            if self.usage else None
        return SimpleNamespace(content=[{"type": "text", "text": "Ho gaya."}], stop_reason="end_turn", usage=u)


def _users(messages):
    """Her plain words in a request (a merged first message counts by its text blocks)."""
    out = []
    for m in messages:
        if m["role"] != "user":
            continue
        c = m["content"]
        if isinstance(c, str):
            out.append(c)
        else:
            out += [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
    return out


def _all_text(messages) -> str:
    return json.dumps(messages, ensure_ascii=False)


# ------------------------------------------------------------------ 1. word for word
def test_whole_chat_goes_word_for_word(gauge, monkeypatch):
    c = conv()
    for i in range(63):
        add_exchange(c, i, steps=2 if i % 2 == 0 else 0)
    from app import yaad
    with session() as s:    # a rolling summary exists, but the whole chat rides: it is not repeated in the prompt
        s.add(yaad.YaadSummary(conversation_id=c, tenant_id="default", upto_id=1, exchanges=10, text="- purana saar"))
    m = Model()
    set_client(m)
    asyncio.run(run_turn(c, "wahi file bhejo", tenant_id="default"))
    sent = m.sent[0]["messages"]
    words = _all_text(sent)
    for i in range(63):                                   # every exchange is there, not a 40-49 window
        assert f"kaam number {i} karo" in words
    assert "file_0_1" in words and '"tool_use"' in words and '"tool_result"' in words   # oldest tool steps intact
    assert "⟦kiya:" not in words                          # nothing was shortened
    assert "purana saar" not in json.dumps(m.sent[0]["system"], ensure_ascii=False)
    assert gauge.LAST[c]["form"] == "full"


def test_hoola_mode_is_the_old_window_byte_for_byte(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_CONTEXT="hoola")
    from app import yaad
    from app.agent.santosh import _load_history, _sanitize
    c = conv()
    for i in range(63):
        add_exchange(c, i, steps=3 if i % 2 == 0 else 0)
    assert _load_history(c) == _sanitize(yaad.history(c))
    users = [x for x in _load_history(c) if x["role"] == "user" and isinstance(x["content"], str)]
    assert 40 <= len(users) <= 49
    msgs = [{"role": "user", "content": "x" * 900000}]
    out, form = gauge.fit(msgs, "sys", [], "claude", c)   # hoola mode never reshapes (only the overflow rescue acts)
    assert form == "hoola" and out is msgs


# ------------------------------------------------------------------ 2. the safety net
def test_safety_net_shortens_the_oldest_and_keeps_this_turn_whole(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_CONTEXT_LIMIT_CLAUDE=60000)
    c = conv()
    for i in range(40):
        add_exchange(c, i, steps=2, big=2500)               # big tool results: the chat no longer fits 45k tokens
    m = Model()
    set_client(m)
    asyncio.run(run_turn(c, "ab final report banao", tenant_id="default"))
    r = gauge.LAST[c]
    assert r["form"] == "net" and r["shortened"] >= 10
    sent = m.sent[0]["messages"]
    words = _all_text(sent)
    assert "⟦kiya:" in words                                 # the oldest exchanges went the v0.108 way
    assert "kaam number 0 karo" in words                     # ... but her words are still there
    assert "ab final report banao" in _users(sent)[-1]       # this turn's message is whole and last
    assert sent[0]["role"] == "user"
    total = sum(len(json.dumps(x["content"], ensure_ascii=False)) for x in sent)
    assert gauge.tokens("claude", total) < gauge.budget("claude")


def test_net_drops_oldest_blocks_with_the_summary_in_their_place(gauge, monkeypatch):
    _settings(monkeypatch, CHAT_CONTEXT_LIMIT_CLAUDE=8000)
    from app import yaad
    c = conv()
    for i in range(60):
        add_exchange(c, i, steps=1)
    with session() as s:
        s.add(yaad.YaadSummary(conversation_id=c, tenant_id="default", upto_id=1, exchanges=10,
                               text="- Sharma ji ki file Invoice_March_v3.pdf bani"))
    hist = [{"role": "user", "content": f"purani baat {i} " + "y" * 400} if i % 2 == 0 else
            {"role": "assistant", "content": [{"type": "text", "text": "theek " + "z" * 400}]} for i in range(120)]
    hist.append({"role": "user", "content": "naya sawal"})
    out, form = gauge.fit(hist, "sys", [], "claude", c, turn_start=len(hist) - 1)
    assert form == "net" and gauge.LAST[c]["dropped"] >= 10
    assert out[0]["role"] == "user" and "Invoice_March_v3.pdf" in out[0]["content"]
    assert out[-1] == {"role": "user", "content": "naya sawal"}
    assert hist[0]["content"].startswith("purani baat 0")    # a projection: the caller's list is untouched


# ------------------------------------------------------------------ 3. the overflow rescue
def test_too_long_is_retried_once_and_the_chat_goes_on(gauge, monkeypatch):
    c = conv()
    for i in range(20):
        add_exchange(c, i, steps=1)
    m = Model(fail=1)
    set_client(m)
    out = asyncio.run(run_turn(c, "aage badho", tenant_id="default"))
    assert out == "Ho gaya." and len(m.sent) == 2
    assert len(_all_text(m.sent[1]["messages"])) < len(_all_text(m.sent[0]["messages"]))
    assert gauge.LIMIT_SEEN["claude"] == 200000 and gauge.ratio("claude") < gauge.CHARS_PER_TOKEN
    assert gauge.STATS["squeezed"] >= 1
    m2 = Model()                                            # the next turn: the chat is NOT stuck
    set_client(m2)
    assert asyncio.run(run_turn(c, "ek aur kaam", tenant_id="default")) == "Ho gaya."


def test_still_too_long_gives_a_clean_line(gauge, monkeypatch):
    c = conv()
    add_exchange(c, 0)
    set_client(Model(fail=5))
    out = asyncio.run(run_turn(c, "aage badho", tenant_id="default"))
    assert "bahut lambi" in out and "250000" not in out and "prompt is too long" not in out
    assert "ref " in out


def test_friendly_error_never_shows_raw_text():
    from app.agent.llm import LLMError
    from app.agent.santosh import _friendly_error
    busy = _friendly_error(LLMError("GLM error 503: upstream /srv/internal/x crashed"))
    assert "busy" in busy and "code 503" in busy and "/srv/internal" not in busy
    odd = _friendly_error(ValueError("weird KeyError at app/agent/santosh.py line 9"))
    assert "gadbad" in odd and "santosh.py" not in odd and "ref " in odd


# ------------------------------------------------------------------ 4. the gauge learns
def test_gauge_learns_from_real_token_counts(gauge):
    assert gauge.ratio("glm") == gauge.CHARS_PER_TOKEN
    gauge.learn("glm", 40000, 20000)                       # the first real count replaces the guess: 2 chars / token
    assert gauge.ratio("glm") == pytest.approx(2.0)
    gauge.learn("glm", 60000, 20000)                       # later counts move it 30% of the way
    assert gauge.ratio("glm") == pytest.approx(2.0 + 0.3 * (3.0 - 2.0))
    before = gauge.ratio("glm")
    gauge.after_call("glm", "s" * 30000, [], [], 10, estimated=True)   # a made-up count teaches nothing
    assert gauge.ratio("glm") == before
    gauge.overflowed("glm", "This model's maximum context length is 131072 tokens. You requested 140000 tokens.")
    assert gauge.LIMIT_SEEN["glm"] == 131072 and gauge.limit("glm") == 131072
    assert gauge.is_overflow("prompt is too long: 215000 tokens > 200000 maximum")
    assert gauge.is_overflow("Error code: 400 - This model's maximum context length is 131072 tokens")
    assert not gauge.is_overflow("Rate limit reached: Request too large, tokens per min (TPM): Limit 30000")
    assert not gauge.is_overflow("GLM error 429: too many tokens per minute")


def test_real_count_from_claude_lands_on_the_reading(gauge, monkeypatch):
    c = conv()
    for i in range(10):
        add_exchange(c, i, steps=1)
    set_client(Model(usage=9000))
    asyncio.run(run_turn(c, "kitna bhara hai", tenant_id="default"))
    r = gauge.LAST[c]
    assert r["real"] == 9000 and "claude" in gauge.RATIO


def test_context_endpoint(gauge, monkeypatch):
    c = conv()
    add_exchange(c, 0)
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = client.get(f"/api/conversations/{c}/context").json()
    assert r["context"]["mode"] == "claude" and r["context"]["measured"] is False
    assert r["context"]["limit"] >= 8000 and "stats" in r["gauge"]
    set_client(Model())
    asyncio.run(run_turn(c, "namaste", tenant_id="default"))
    r = client.get(f"/api/conversations/{c}/context").json()["context"]
    assert r["measured"] is True and r["form"] == "full" and r["percent"] > 0
