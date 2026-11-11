"""v0.472 R1 PLAN PEHLE - a big research ask shows its plan and waits for her Haan.

Pinned here: the recognition fix (the R0 card found 11 of 20 real research asks unseen) without catching plain asks that
merely contain the word, the size tiers read in code (a lookup never waits), the plan card (her language, the estimate
labelled as an estimate), the gate's four outcomes (new plan / Haan / Haan + her change / no / a different thing), that
NOTHING runs before the Haan and the SAME turn gets the approved plan after it, that a stale plan expires, and that a
broken gate never blocks her ask.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from app.agent import research_plan as P
from app.quality.research_asks import ASKS

BIG = "Do deep research on the Indian electric two-wheeler market: size, top players, growth. Sources with dates."
BIG_HI = "Research karo: India ki latest CPI inflation, trend, food vs non-food. Poora research document chahiye, sources ke saath."


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def plan_env(env, monkeypatch):
    """No model call: the sub-questions come from a fixed stub (the template fallback is tested on its own)."""
    async def fake_q(ask, note, a, settings):
        qs = ["What is the size, and as of when?", "Who are the top players?", "How fast is it growing?",
              "What could not be confirmed?"] + ([f"Also: {note}"] if note else [])
        return {"sub_questions": qs, "look_in": ["regulator site", "company filings"], "as_of": "today", "from_model": True}
    monkeypatch.setattr(P, "_questions", fake_q)
    from app.config import get_settings
    return get_settings()


def test_every_research_ask_of_the_r0_card_is_now_recognised_and_plain_asks_are_not(env):
    from app.agent import hard
    assert [a["id"] for a in ASKS if not hard.research_wanted(a["text"])] == []
    for plain in ("research notes ko sheet mein daal do", "Research Gate pe login kar do", "meri research ki file kholo",
                  "open the research folder", "kal research team ki meeting hai, reminder lagao",
                  "Research lab ka bill bhejo", "I did my research yesterday, now book a cab"):
        assert not hard.research_wanted(plain), plain


def test_size_is_read_in_code_a_lookup_never_waits(env):
    assert P.assess("Research karo: India ki latest CPI kitni hai")["tier"] == "small"
    assert P.assess(BIG)["tier"] == "large" and P.assess(BIG_HI)["tier"] == "large"
    assert P.assess("Research the cotton MSP for this year and what changed compared with last year in the Vidarbha region")["tier"] == "standard"
    a = P.assess(BIG_HI)
    assert a["hinglish"] and a["corpus"] == "official" and P.assess(BIG)["hinglish"] is False
    assert P.assess("Compare A, B, C and D fees; compute the monthly cost for each")["tier"] == "large"   # calc + parts


def test_the_card_says_what_it_will_do_in_her_language_and_labels_the_estimate(env, plan_env):
    p = run(P.build(BIG_HI, plan_env))
    txt = P.card_text(p)
    assert "Haan, shuru karo" in txt and "andaza" in txt and "source aur date" in txt
    assert 4 <= len(p["sub_questions"]) <= 6 and p["est"]["assumed"] is True and p["est"]["minutes"] >= 10
    en = P.card_text(run(P.build(BIG, plan_env)))
    assert "I need your approval" in en and "an estimate" in en and "Yes, start" in en


def test_the_plan_still_comes_when_the_model_does_not(env, monkeypatch):
    """No key / a timeout: the card is made from the templates, never an error and never nothing."""
    import app.agent.santosh as S
    monkeypatch.setattr(S, "get_client", lambda: (_ for _ in ()).throw(RuntimeError("no key")))
    from app.config import get_settings
    p = run(P.build(BIG, get_settings()))
    assert p["from_model"] is False and len(p["sub_questions"]) >= 4 and p["look_in"]


def test_a_big_ask_gets_a_plan_and_nothing_runs_until_the_haan(env, plan_env):
    r = run(P.gate("t1", "c1", BIG, plan_env))
    assert r["action"] == "say" and "Research plan" in r["text"]
    assert P._waiting("t1", "c1") is not None
    # a small ask and a non-research ask pass straight through
    assert run(P.gate("t2", "c2", "Research karo: India ki latest CPI kitni hai", plan_env)) is None
    assert run(P.gate("t2", "c2", "Mujhe kal subah 7 baje jagana", plan_env)) is None
    assert P._waiting("t2", "c2") is None


def test_the_haan_starts_the_same_ask_with_the_approved_plan(env, plan_env):
    run(P.gate("t1", "c1", BIG, plan_env))
    r = run(P.gate("t1", "c1", "Haan, shuru karo", plan_env))
    assert r["action"] == "start" and r["words"] == "Haan, shuru karo"
    assert r["text"].startswith(BIG) and "<approved_research_plan>" in r["text"] and "do not ask her again" in r["text"]
    assert P._waiting("t1", "c1") is None                       # closed: a second Haan does nothing
    assert run(P.gate("t1", "c1", "haan", plan_env)) is None


def test_her_change_rides_along_with_the_haan(env, plan_env):
    run(P.gate("t1", "c1", BIG, plan_env))
    r = run(P.gate("t1", "c1", "Haan, par Pakistan se bhi tulna karo", plan_env))
    assert r["action"] == "start" and "HER CHANGE TO THE PLAN" in r["text"] and "Pakistan" in r["text"]


def test_a_no_drops_the_plan_and_runs_nothing(env, plan_env):
    run(P.gate("t1", "c1", BIG, plan_env))
    r = run(P.gate("t1", "c1", "nahi", plan_env))
    assert r["action"] == "say" and P._waiting("t1", "c1") is None


def test_words_that_are_not_a_yes_or_no_revise_the_plan_and_show_it_again(env, plan_env):
    run(P.gate("t1", "c1", BIG, plan_env))
    r = run(P.gate("t1", "c1", "Isme Bangladesh ko bhi jodo", plan_env))
    assert r["action"] == "say" and "Bangladesh" in r["text"]
    w = P._waiting("t1", "c1")
    assert w is not None and "Bangladesh" in json.loads(w.plan)["note"]       # still waiting, on the REVISED plan


def test_a_different_big_ask_replaces_the_waiting_plan(env, plan_env):
    run(P.gate("t1", "c1", BIG, plan_env))
    r = run(P.gate("t1", "c1", BIG_HI, plan_env))
    assert r["action"] == "say" and "CPI" in r["text"]
    assert json.loads(P._waiting("t1", "c1").plan)["ask"].startswith("Research karo")


def test_a_plan_nobody_answered_for_a_day_is_stale(env, plan_env):
    from datetime import timedelta

    from app.db import now, session
    run(P.gate("t1", "c1", BIG, plan_env))
    with session() as s:
        row = s.get(P.ResearchPlan, P._waiting("t1", "c1").id)
        row.created_at = now() - timedelta(hours=P.WAIT_HOURS + 1)
    assert P._waiting("t1", "c1") is None
    assert run(P.gate("t1", "c1", "haan", plan_env)) is None                  # a stale plan is not started by a stray yes


def test_plans_are_per_tenant_and_per_chat(env, plan_env):
    run(P.gate("t1", "c1", BIG, plan_env))
    assert P._waiting("t2", "c1") is None and P._waiting("t1", "c2") is None


def test_the_switch_turns_the_gate_off(env, plan_env):
    plan_env.research_plan_gate = False
    try:
        assert run(P.gate("t1", "c1", BIG, plan_env)) is None
    finally:
        plan_env.research_plan_gate = True


def test_the_turn_shows_the_plan_first_then_runs_the_approved_plan_in_the_same_turn(env, plan_env, monkeypatch):
    """End to end through run_turn: no model/tool step before the Haan; after it the model sees the ask + the plan."""
    import app.agent.santosh as S
    seen = {"steps": 0, "last_user": ""}

    async def fake_steps(conv, ctx, gender, history, settings, tenant, user_text):
        seen["steps"] += 1
        c = history[-1]["content"]
        seen["last_user"] = c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if isinstance(b, dict))
        return "REPORT DONE"
    monkeypatch.setattr(S, "_steps", fake_steps)
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="t9")
        s.add(c)
        s.flush()
        conv = c.id
    first = run(S.run_turn(conv, BIG, tenant_id="t9"))
    assert "Research plan" in first and seen["steps"] == 0                     # nothing ran
    second = run(S.run_turn(conv, "Haan, shuru karo", tenant_id="t9"))
    assert second == "REPORT DONE" and seen["steps"] == 1
    assert BIG in seen["last_user"] and "<approved_research_plan>" in seen["last_user"]
    from app.db import Message
    from sqlalchemy import select
    with session() as s:
        shown = [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv).order_by(Message.id)).all()
                 if m.role == "user" and m.display]
    assert shown == [BIG, "Haan, shuru karo"]                                  # her bubbles are her words, no plan block


def test_a_broken_gate_never_blocks_her_ask(env, plan_env, monkeypatch):
    import app.agent.santosh as S

    async def boom(*a, **k):
        raise RuntimeError("gate down")

    async def fake_steps(conv, ctx, gender, history, settings, tenant, user_text):
        return "ANSWERED"
    monkeypatch.setattr(P, "gate", boom)
    monkeypatch.setattr(S, "_steps", fake_steps)
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="t8")
        s.add(c)
        s.flush()
        conv = c.id
    assert run(S.run_turn(conv, BIG, tenant_id="t8")) == "ANSWERED"
