"""v0.98 Know the cost: every model call counted per owner / feature, a monthly limit that pauses background work,
one bootstrap call at app open, and her 👍 / 👎 after a call."""
import asyncio
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _clean(env):
    from app import usage
    usage._BUF.clear()
    usage._STATE_CACHE.clear()
    yield
    usage._BUF.clear()
    usage._STATE_CACHE.clear()


def _conv(tenant="default"):
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def test_prices_follow_the_official_lists():
    from app import usage
    assert usage.cost("claude-sonnet-5-5", tok_in=1_000_000) == pytest.approx(2.0)
    assert usage.cost("claude-sonnet-5-5-20261001", tok_out=1_000_000) == pytest.approx(10.0)    # dated names too
    assert usage.cost("claude-sonnet-5-5", cache_read=1_000_000) == pytest.approx(0.10)
    assert usage.cost("gemini-2.5-flash", tok_in=1_000_000, audio_in=1_000_000) == pytest.approx(1.30)
    assert usage.cost("gemini-3.8-live", sec_in=60, sec_out=60) == pytest.approx(0.023)        # $0.005 + $0.018 a minute
    assert usage.price_of("some-new-model")[1] is False                                       # counted as an estimate


def test_sdk_calls_are_counted_where_they_happen(env, monkeypatch):
    from anthropic.resources import AsyncMessages
    from google.genai.models import Models

    from app import usage

    async def fake_create(self, **kw):
        return SimpleNamespace(model=kw["model"], usage=SimpleNamespace(input_tokens=1000, output_tokens=500,
                                                                       cache_read_input_tokens=20000,
                                                                       cache_creation_input_tokens=0))

    def fake_gen(self, *, model, contents, config=None):
        return SimpleNamespace(usage_metadata=SimpleNamespace(
            prompt_token_count=3000, candidates_token_count=200, thoughts_token_count=100, cached_content_token_count=0,
            prompt_tokens_details=[SimpleNamespace(modality="AUDIO", token_count=2000)], candidates_tokens_details=[]))
    monkeypatch.setattr(AsyncMessages, "create", fake_create)
    monkeypatch.setattr(Models, "generate_content", fake_gen)
    monkeypatch.setattr(usage, "_INSTALLED", [False])
    usage.install()
    with usage.scope("default", "lekhak"):
        asyncio.run(AsyncMessages.create(None, model="claude-sonnet-5-5", max_tokens=10, messages=[]))
        Models.generate_content(None, model="gemini-2.5-flash", contents="x")
    usage.flush()
    r = usage.report("default", 7)
    lek = next(f for f in r["features"] if f["feature"] == "lekhak")
    assert lek["calls"] == 2
    claude = next(m for m in r["models"] if m["model"] == "claude-sonnet-5-5")
    assert claude["usd"] == pytest.approx((1000 * 2 + 500 * 10 + 20000 * 0.10) / 1e6, abs=1e-4)
    gem = next(m for m in r["models"] if m["model"] == "gemini-2.5-flash")
    assert gem["usd"] == pytest.approx((1000 * 0.30 + 2000 * 1.0 + 300 * 2.5) / 1e6, abs=1e-4)


def test_chat_turn_is_counted_for_her_as_chat(env, monkeypatch):
    from app import usage
    from app.agent import santosh
    conv = _conv()

    async def think(brain, system, history, settings, tools=None):
        usage.record("claude-sonnet-5-5", tok_in=10_000, tok_out=1_000)
        return [{"type": "text", "text": "ho gaya"}], "end_turn", brain
    monkeypatch.setattr(santosh, "_think", think)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    asyncio.run(santosh.run_turn(conv, "namaste"))
    r = usage.report("default", 1)
    assert r["features"][0]["feature"] == "chat" and r["month"]["spent_usd"] == pytest.approx(0.03)


def test_limit_warns_then_pauses_background_work_but_not_her_chat(env, monkeypatch):
    from app import usage
    from app.agent import santosh
    from app.db import Message, session
    from app.net.service import home_conv
    conv = home_conv("default")
    usage.set_limit("default", month_usd=1.0)
    usage.record("claude-sonnet-5-5", tok_in=420_000, tenant="default", feature="chat")       # $0.84 = 84%
    with session() as s:
        texts = [m.display for m in s.query(Message).filter_by(conversation_id=conv).all()]
    assert any("84%" in (t or "") for t in texts)                    # one warning at 80%
    assert usage.allowed("default", "routine")
    usage.record("claude-sonnet-5-5", tok_in=100_000, tenant="default", feature="routine")    # now $1.04
    assert not usage.allowed("default", "routine") and not usage.allowed("default", "website")
    assert usage.allowed("default", "chat") and usage.allowed("default", "call")
    # a routine turn waits; her own chat still runs
    calls = []

    async def think(brain, system, history, settings, tools=None):
        calls.append(1)
        return [{"type": "text", "text": "ok"}], "end_turn", brain
    monkeypatch.setattr(santosh, "_think", think)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    c2 = _conv()
    out = asyncio.run(santosh.run_turn(c2, "subah ki report", actor="routine"))
    assert "seema" in out and not calls
    assert asyncio.run(santosh.run_turn(c2, "kaisi ho")) == "ok" and calls
    # website / video jobs are refused with the same plain words
    from app.operator import service as ops
    monkeypatch.setattr(ops, "available", lambda: True)
    with pytest.raises(ops.OperatorJobError, match="seema"):
        ops.start("default", "MSEDCL ka bill download karo")
    # a higher limit lets them run again
    usage.set_limit("default", month_inr=5000)
    assert usage.allowed("default", "routine")


def test_api_report_limit_and_owner_view(env):
    from fastapi.testclient import TestClient

    from app import main, usage
    usage.record("claude-sonnet-5-5", tok_in=100_000, tenant="default", feature="video")
    usage.record("gemini-3.8-live", sec_in=600, sec_out=300, tenant="default", feature="call")
    with TestClient(main.app) as c:
        r = c.get("/api/usage?days=7").json()
        # >= : a background thread of another test may record its own (fake) model call into the same month
        assert {"video", "call"} <= {f["feature"] for f in r["features"]} and r["month"]["spent_inr"] > 0
        assert r["daily"][-1]["inr"] > 0 and "Sabse zyada" in r["say"]
        lim = c.put("/api/usage/limit", json={"month_inr": 2000}).json()
        assert lim["month"]["limit_inr"] == pytest.approx(2000, rel=1e-3)
        assert c.get("/api/usage/all").json()["tenants"][0]["tenant"] == "default"


def test_tool_reads_and_sets_the_limit(env):
    from app.agent.tools import Ctx, ToolError, dispatch
    r = asyncio.run(dispatch("ai_kharcha", {"action": "limit", "limit_inr": 1500}, Ctx("default", "c")))
    assert r["limit_inr"] == pytest.approx(1500, rel=1e-3)
    with pytest.raises(ToolError, match="sirf owner"):
        asyncio.run(dispatch("ai_kharcha", {"action": "limit", "limit_inr": 99999}, Ctx("default", "c", actor="routine")))


def test_bootstrap_is_one_call(env):
    from fastapi.testclient import TestClient

    from app import main
    with TestClient(main.app) as c:
        first = c.get("/api/bootstrap").json()
        for k in ("health", "conversation_id", "me", "lists", "routines", "avatar", "pending_actions", "usage"):
            assert k in first, k
        assert first["conversation_new"] is True and first["health"]["ok"] is True
        again = c.get(f"/api/bootstrap?conv={first['conversation_id']}").json()
        assert again["conversation_id"] == first["conversation_id"] and again["conversation_new"] is False
        other = c.get("/api/bootstrap?conv=not-hers").json()
        assert other["conversation_new"] is True


def test_call_rating_reaches_the_voice_numbers(env):
    from fastapi.testclient import TestClient

    from app import main
    with TestClient(main.app) as c:
        assert c.post("/api/voice/calls/call1/rating", json={"good": True}).json()["ok"]
        r = c.post("/api/voice/calls/call2/rating", json={"good": False, "reasons": ["cut_off", "slow", "made_up"]}).json()
        assert r["reasons"] == ["Beech mein kaat diya", "Jawab der se aaya"]
        c.post("/api/voice/calls/call2/rating", json={"good": False, "reasons": ["cut_off"]})      # changing her mind
        st = c.get("/api/voice/stats").json()["ratings"]
    assert st["rated_calls"] == 2 and st["good_pct"] == 50.0 and st["top_reasons"][0]["reason"] == "cut_off"
