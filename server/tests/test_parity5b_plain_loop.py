"""Parity Phase 5b (docs/CLAUDE_PARITY_PLAN.md Part 2 row 5, "The loop"): the model's answer ends the turn.

- an ordinary answer = ONE model call and ONE assistant message (no pakka self-check call, no reviewer call);
- the kept checks (a false ACTION claim, a reminder promised with none set, research figures with no source) run
  BEFORE the answer is shown, and the corrected answer replaces the draft in place: she sees ONE reply;
- CHAT_PLAIN_LOOP=false = the old after-answer checks.
The conftest pins CHAT_PLAIN_LOOP=false for the older suites; every test here removes the pin (the new default)."""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


@pytest.fixture()
def pl(gz, monkeypatch):  # noqa: F811
    monkeypatch.delenv("CHAT_PLAIN_LOOP", raising=False)
    monkeypatch.delenv("CHAT_ANSWER_ONLY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    assert get_settings().chat_plain_loop is True
    from app.agent import research_plan

    async def _off(*a, **k):
        return None
    monkeypatch.setattr(research_plan, "gate", _off)
    return gz


def _check_on(monkeypatch):
    monkeypatch.setenv("HARD_CHECK", "true")     # the conftest turns the held check off for scripted turns
    from app.config import get_settings
    get_settings.cache_clear()


def _off_switch(monkeypatch):
    monkeypatch.setenv("CHAT_PLAIN_LOOP", "false")
    from app.config import get_settings
    get_settings.cache_clear()


def _said(conv):
    from app.db import Event, session
    with session() as s:
        return [dict(e.payload or {}).get("text", "") for e in s.query(Event).filter(Event.conversation_id == conv)
                .order_by(Event.id).all() if e.kind == "message" and (e.payload or {}).get("role") == "assistant"]


def _shown_rows(conv):
    from app.db import Message, session
    with session() as s:
        return [m.display for m in s.query(Message).filter(Message.conversation_id == conv,
                                                            Message.role == "assistant").order_by(Message.id).all()]


def _count_self_check(monkeypatch):
    from app.agent import pakka
    seen = {"n": 0}

    async def _sc(*a, **k):
        seen["n"] += 1
        return {"done": True, "missing": "", "next": "", "claim_ok": True}
    monkeypatch.setattr(pakka, "self_check", _sc)
    return seen


def test_setting_default_on(monkeypatch):
    monkeypatch.delenv("CHAT_PLAIN_LOOP", raising=False)
    from app.config import Settings
    assert Settings().chat_plain_loop is True


def test_ordinary_answer_is_one_call_and_one_message(pl, monkeypatch):
    conv = pl["conv"]
    final = "Paris is the capital of France."
    brain = _set_brain(monkeypatch, FakeBrain([([txt(final)], "end_turn")]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "what is the capital of France?", tenant_id="default"))
    assert out == final
    assert len(brain.seen) == 1 and brain.script == []
    assert _said(conv) == [final]


def test_tool_turn_has_no_after_answer_self_check(pl, monkeypatch):
    """Three real tool calls used to buy one more model call (pakka.self_check) after the answer."""
    conv = pl["conv"]
    sc = _count_self_check(monkeypatch)
    final = "Two jobs are running: the report and the site build."
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="jobs"), tu(2, "kaam_status", q="report"), tu(3, "kaam_status", q="site")], "tool_use"),
        ([txt(final)], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "what is running?", tenant_id="default"))
    assert out == final and len(brain.seen) == 2 and sc["n"] == 0
    assert _said(conv) == [final]


def test_old_loop_with_the_switch_off_still_self_checks(pl, monkeypatch):
    conv = pl["conv"]
    _off_switch(monkeypatch)
    sc = _count_self_check(monkeypatch)
    _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="jobs"), tu(2, "kaam_status", q="report"), tu(3, "kaam_status", q="site")], "tool_use"),
        ([txt("Two jobs are running.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "what is running?", tenant_id="default"))
    assert sc["n"] == 1


def test_false_mail_sent_is_fixed_and_she_sees_one_reply(pl, monkeypatch):
    conv = pl["conv"]
    fixed = "I have not sent it yet - shall I draft the mail to Rahul now?"
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("I've sent the mail to Rahul.")], "end_turn"),
        ([txt(fixed)], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "Rahul ko mail bhejo", tenant_id="default"))
    assert out == fixed and len(brain.seen) == 2
    assert "[" in str(brain.seen[1]["messages"][-1]["content"])          # the one correction ask
    assert _said(conv) == [fixed]                                        # ONE reply: the draft was never published
    rows = _shown_rows(conv)
    assert rows[-1] == fixed and None in rows                            # the draft stays for the model, hidden


def test_false_mail_sent_twice_is_said_inside_the_same_reply(pl, monkeypatch):
    conv = pl["conv"]
    _set_brain(monkeypatch, FakeBrain([
        ([txt("I've sent the mail to Rahul.")], "end_turn"),
        ([txt("I've sent the mail to Rahul.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "Rahul ko mail bhejo", tenant_id="default"))
    said = _said(conv)
    assert len(said) == 1                                               # one reply, the honest line inside it
    assert said[0].startswith("I've sent the mail to Rahul.") and len(said[0]) > len("I've sent the mail to Rahul.")


def test_a_non_action_claim_is_not_rewritten(pl, monkeypatch):
    conv = pl["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Your notes look good, all done.")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "check my notes", tenant_id="default"))
    assert len(brain.seen) == 1 and len(_said(conv)) == 1


def _hard_on(monkeypatch):
    _check_on(monkeypatch)
    from app.agent import hard

    async def _decide(*a, **k):
        return {"hard": True, "why": ["calc"], "score": 3}
    monkeypatch.setattr(hard, "decide", _decide)


def test_ordinary_hard_answer_is_not_held_or_reviewed(pl, monkeypatch):
    conv = pl["conv"]
    _hard_on(monkeypatch)
    import app.agent.santosh as s
    seen = {"n": 0}

    async def _hc(*a, **k):
        seen["n"] += 1
        return ["wrong"]
    monkeypatch.setattr(s, "_hard_check", _hc)
    brain = _set_brain(monkeypatch, FakeBrain([([txt("The answer is 42.")], "end_turn")]))
    out = asyncio.run(s.run_turn(conv, "work out the yearly interest on 5 lakh at 8%", tenant_id="default"))
    assert out == "The answer is 42." and len(brain.seen) == 1 and seen["n"] == 0


def test_research_answer_with_an_unsourced_figure_gets_its_one_fix(pl, monkeypatch):
    conv = pl["conv"]
    _check_on(monkeypatch)
    import app.agent.santosh as s
    monkeypatch.setattr(s, "_research_delivered", lambda c, st: True)
    seen = {"n": 0}

    async def _hc(conversation_id, state, draft, history, settings, free_only=False):
        seen["n"] += 1
        return ["the figure 37% is carried by no source"] if seen["n"] == 1 else []
    monkeypatch.setattr(s, "_hard_check", _hc)
    fixed = "Sales grew [1], the exact share is not confirmed."
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Sales grew 37%.")], "end_turn"),
        ([txt(fixed)], "end_turn"),
    ]))
    out = asyncio.run(s.run_turn(conv, "research our sales growth", tenant_id="default"))
    assert out == fixed and len(brain.seen) == 2 and seen["n"] >= 1
    assert _said(conv) == [fixed]


def test_old_loop_holds_an_ordinary_hard_answer(pl, monkeypatch):
    conv = pl["conv"]
    _off_switch(monkeypatch)
    _hard_on(monkeypatch)
    import app.agent.santosh as s
    seen = {"n": 0}

    async def _hc(*a, **k):
        seen["n"] += 1
        return []
    monkeypatch.setattr(s, "_hard_check", _hc)
    _set_brain(monkeypatch, FakeBrain([([txt("The answer is 42.")], "end_turn")]))
    asyncio.run(s.run_turn(conv, "work out the yearly interest on 5 lakh at 8%", tenant_id="default"))
    assert seen["n"] == 1


def test_live_retract_voids_the_block_and_keeps_the_same_seg(monkeypatch):
    from app import livereply
    out = []
    monkeypatch.setattr(livereply.bus, "publish_live", lambda conv, kind, p: out.append((kind, dict(p))))
    lv = livereply.Live("c1", "default")
    lv.start()
    lv.block(stream=True)
    lv.feed("I have sent the mail to Rahul just now, all done here. ")
    lv.flush(final=True)
    seg = lv.seg
    assert any(k == "delta" for k, _ in out)
    lv.retract()
    assert ("delta_reset", {"turn": lv.turn, "seg": seg}) in out
    lv.block(stream=True)
    assert lv.seg == seg                       # the corrected answer is written into the SAME block
    assert lv.tag()["seg"] == seg


def test_clients_already_clear_a_block_on_delta_reset():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    js = (root / "server" / "app" / "static" / "console" / "v2.js").read_text()
    assert "case 'delta_reset'" in js and "pacer.reset()" in js
    dart = (root / "lib" / "state.dart").read_text()
    assert "case 'delta_reset':" in dart
