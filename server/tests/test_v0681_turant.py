"""Wave 9 TURANT of the third deep audit (owner: "GO WAVE 9" - urgent safety, money, privacy and cost).

1 one user's coder work lists / rows never reach another user
2 a bulk WhatsApp send starts only when HER words in this turn say send; a one-person WhatsApp ask never opens campaigns
3 SAB HAIKU covers streamed calls too (live chat), and the streamed meter counts the model really sent
4 the Web Studio's streamed sections are counted
5 research workers in parallel can no longer overshoot the cost ceiling
6 only the operator is told to recharge Anthropic; a spoken error never carries the code / ref
7 an overloaded one-model call falls back to another model; a failed job report says nothing itself
8 a failed staff task is "failed", never "done" with the error sent to the staff member
9 the minute is out of the cached system prompt (it rides with her newest message)
"""
from __future__ import annotations

import asyncio
import inspect
import re
import types

import pytest

T = "default"


# ---------------------------------------------------------------- 1 privacy
def test_work_lists_belong_to_their_tenant(env):
    from app.coder import store
    store.work_write("default", [{"text": "Sharma ji ka quotation", "status": "todo"}], tenant="t-a")
    store.work_write("default", [{"text": "Riya ki fees", "status": "todo"}], tenant="t-b")
    a = store.work_read(tenant="t-a")
    b = store.work_read(tenant="t-b")
    assert [i["text"] for i in a["default"]] == ["Sharma ji ka quotation"]
    assert [i["text"] for i in b["default"]] == ["Riya ki fees"]
    assert store.work_read(tenant="t-c") == {}
    from app.coder import inject
    assert "Riya" not in " ".join(inject._work_lines("t-a"))


def test_batch_routes_filter_by_tenant():
    from app.coder import service
    src = inspect.getsource(service)
    assert 'if (o.get("tenant") or "") == t' in src and 'if (u.get("tenant") or "") == t' in src
    assert "tenant=current_tenant(request)" in src


# ---------------------------------------------------------------- 2 campaigns
def _ctx(actor="owner"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=T, conversation_id="c1", actor=actor)


@pytest.mark.parametrize("words,actor,ok", [
    ("Haan, sabko bhej do", "owner", True),
    ("haan", "owner", True),
    ("Rahul ko diwali offer ka message banao", "owner", False),
    ("nahi abhi mat bhejo", "owner", False),
    ("Haan bhej do", "routine", False),
    ("Haan bhej do", "wake", False),
])
def test_a_send_needs_her_own_words_now(words, actor, ok):
    from app.agent import santosh, tools
    tok = santosh.ASK_NOW.set(words)
    try:
        assert tools._she_said_send(_ctx(actor)) is ok
    finally:
        santosh.ASK_NOW.reset(tok)


def test_create_campaign_waits_for_her_when_she_did_not_say_send(monkeypatch):
    from app.agent import santosh, tools
    got = {}

    def fake(**kw):
        got.update(kw)
        return {"id": "cmp1", "status": "ready"}
    monkeypatch.setattr(tools.camp, "create_campaign", fake)
    tok = santosh.ASK_NOW.set("customers ko diwali offer ka campaign banao")
    try:
        v = asyncio.run(tools.create_campaign(_ctx(), "Diwali", "ll1", "t1", {}, True, True))
    finally:
        santosh.ASK_NOW.reset(tok)
    assert got["auto_send"] is False and "NOT sent" in v["not_sent"]


def test_confirm_send_refuses_without_her_yes(monkeypatch):
    from app.agent import santosh, tools
    sent = []
    monkeypatch.setattr(tools.camp, "confirm_send", lambda cid: sent.append(cid) or {"status": "sending"})
    monkeypatch.setattr(tools.camp, "campaign_view", lambda cid: {"id": cid, "status": "ready"})
    tok = santosh.ASK_NOW.set("status kya hai?")
    try:
        v = asyncio.run(tools.confirm_send(_ctx(), "cmp1"))
    finally:
        santosh.ASK_NOW.reset(tok)
    assert sent == [] and "NOT sent" in v["not_sent"]
    tok = santosh.ASK_NOW.set("haan bhej do")
    try:
        asyncio.run(tools.confirm_send(_ctx(), "cmp1"))
    finally:
        santosh.ASK_NOW.reset(tok)
    assert sent == ["cmp1"]


def test_a_one_person_whatsapp_ask_does_not_open_campaigns():
    from app.agent import admit
    fam = admit.route("Rahul ko whatsapp pe message bhej do ki meeting cancel hai")
    assert "campaign" not in (fam if isinstance(fam, (dict, set, list)) else {})
    assert "campaign" in admit.route("sabko whatsapp pe diwali offer broadcast karo")


# ---------------------------------------------------------------- 3 + 4 the model really sent, and counted
def test_streams_follow_the_one_model_rule():
    from app import usage
    usage.install()
    from anthropic.resources import AsyncMessages, Messages
    assert AsyncMessages.stream.__name__ == "a_stream" and Messages.stream.__name__ == "s_stream"
    src = inspect.getsource(usage.install)
    assert "one_model(kw)" in src.split("def a_stream", 1)[1][:200]


def test_one_model_bypass_lets_the_fallback_really_change_model(monkeypatch):
    from app import usage
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "claude_one_model", "claude-haiku-5-5")
    assert usage.one_model({"model": "claude-sonnet-5-5"})["model"] == "claude-haiku-5-5"
    tok = usage.ONE_MODEL_BYPASS.set(True)
    try:
        assert usage.one_model({"model": "claude-sonnet-5-5"})["model"] == "claude-sonnet-5-5"
    finally:
        usage.ONE_MODEL_BYPASS.reset(tok)


def test_streamed_calls_are_counted_at_the_real_model():
    from app.agent import santosh
    from app.site import ai
    assert "usage.from_anthropic" in inspect.getsource(ai._streamed)
    assert 'usage.from_anthropic(_sent_model(kw.get("model", "")), msg)' in inspect.getsource(santosh._claude_stream)


# ---------------------------------------------------------------- 5 research ceilings
def test_parallel_research_calls_hold_their_price(monkeypatch):
    from app.research import bill
    monkeypatch.setattr(bill, "caps", lambda: {"run_inr": 10.0, "day_inr": 1000.0, "reserve_inr": 3.0})
    monkeypatch.setattr(bill, "per_call_inr", lambda *a, **k: 3.0)
    monkeypatch.setattr(bill.store, "spent_since", lambda *a, **k: 0.0)
    m = bill.Meter(T, "r1")
    oks = [m.afford()[0] for _ in range(6)]          # six workers ask before any call has returned
    assert oks == [True, True, True, False, False, False]
    m.acc["calls"] += 1                               # one call came back (and cost nothing here)
    assert m.held_inr() == 6.0


# ---------------------------------------------------------------- 6 the outage line
def test_only_the_operator_hears_the_recharge_line(monkeypatch):
    from app.agent import santosh
    e = Exception("Error code: 400 - Your credit balance is too low to access the Anthropic API")
    assert "recharge" in santosh._friendly_error(e, "default", "owner")
    assert santosh._friendly_error(e, "cust-9", "owner").startswith(santosh.OUTAGE_TEXT)
    assert santosh._friendly_error(e, "default", "staff:a1").startswith(santosh.OUTAGE_TEXT)
    spoken = santosh._friendly_error(Exception("Error code: 529 overloaded"), "default", "owner", spoken=True)
    assert "ref" not in spoken and "code" not in spoken


# ---------------------------------------------------------------- 7 fallback + quiet wake failures
def test_a_failed_job_report_says_nothing_itself():
    from app.agent import santosh
    assert santosh._say_error(T, "wake", "Abhi AI service busy ya unreachable hai") is False
    src = inspect.getsource(santosh._call_brain) if hasattr(santosh, "_call_brain") else inspect.getsource(santosh)
    assert "ONE_MODEL_BYPASS.set(True)" in inspect.getsource(santosh)


# ---------------------------------------------------------------- 8 staff tasks
def test_a_failed_staff_task_is_failed():
    from app.employee import network
    src = inspect.getsource(network.run_pending)
    assert "turn_failed_since" in src and 'status, out = "failed"' in src
    assert 'f"Kuch gadbad: {e}"' not in src


# ---------------------------------------------------------------- 9 the cache
def test_no_minute_in_the_cached_system_prompt(env):
    from app.agent import prompts, santosh
    sp = prompts.system_prompt(True, "", T)
    assert not re.search(r"\d{1,2}:\d{2}\s*(AM|PM)", sp)
    assert re.match(r"\[Abhi ka samay: \w+ \d{1,2} \w+ \d{4}, \d{1,2}:\d{2} (AM|PM)", santosh._now_note(T))
    from app import life
    assert not re.search(r"local time now .*\d{2}:\d{2}", life.context_block(T))
