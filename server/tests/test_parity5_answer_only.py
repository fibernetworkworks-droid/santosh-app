"""Parity Phase 5 (docs/CLAUDE_PARITY_PLAN.md, gap 11): the reply is ONLY what the model wrote.

- the "(Kaam: 4/24 steps · 2 calls (2 ok) · done ✓ · tools)" ledger is step data (event `ledger`), never a chat row;
- a done-claim no tool backs is corrected by the model itself (one nudge), and a correction message goes out only
  when a real ACTION claim (sent / paid / booked / deleted / published) is still false after that retry.
The conftest pins CHAT_ANSWER_ONLY=false for the older suites; every test here removes the pin (the new default)."""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


@pytest.fixture()
def ao(gz, monkeypatch):  # noqa: F811
    monkeypatch.delenv("CHAT_ANSWER_ONLY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    assert get_settings().chat_answer_only is True
    from app.agent import research_plan

    async def _off(*a, **k):
        return None
    monkeypatch.setattr(research_plan, "gate", _off)
    return gz


def _rows(conv):
    from app.db import Event, Message, session
    with session() as s:
        evs = [(e.kind, dict(e.payload or {})) for e in s.query(Event).filter(Event.conversation_id == conv)
               .order_by(Event.id).all()]
        msgs = [m.display or "" for m in s.query(Message).filter(Message.conversation_id == conv,
                                                                  Message.role == "assistant").order_by(Message.id).all()]
    return evs, msgs


def _said(evs):
    return [p.get("text", "") for k, p in evs if k == "message" and p.get("role") == "assistant"]


def test_setting_default_on(monkeypatch):
    monkeypatch.delenv("CHAT_ANSWER_ONLY", raising=False)
    from app.config import Settings
    assert Settings().chat_answer_only is True


def test_reply_is_exactly_the_models_text_and_the_ledger_is_step_data(ao, monkeypatch):
    conv = ao["conv"]
    final = "Two jobs are running right now: the report and the site build."
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="jobs")], "tool_use"),
        ([txt(final)], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "what is running?", tenant_id="default"))
    assert brain.script == []
    assert out == final
    evs, msgs = _rows(conv)
    said = _said(evs)
    assert said and said[-1] == final
    for t in said + msgs:
        assert "(Kaam:" not in t and "(To be clear" not in t
    ledgers = [p for k, p in evs if k == "ledger"]
    assert len(ledgers) == 1 and ledgers[0]["line"].startswith("(Kaam:")
    assert "kaam_status" in ledgers[0]["line"] and "1 calls (1 ok)" in ledgers[0]["line"]


def test_old_behaviour_back_with_the_switch_off(ao, monkeypatch):
    conv = ao["conv"]
    monkeypatch.setenv("CHAT_ANSWER_ONLY", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_status", q="jobs")], "tool_use"),
        ([txt("Two jobs are running.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "what is running?", tenant_id="default"))
    evs, _ = _rows(conv)
    assert any(t.startswith("(Kaam:") for t in _said(evs))
    assert not [p for k, p in evs if k == "ledger"]


def test_false_mail_sent_is_nudged_then_said_once(ao, monkeypatch):
    """A real ACTION claim ('sent the mail') with no tool: the model is asked to correct itself; still false after
    the retry -> the one honest message."""
    conv = ao["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("I've sent the mail to Rahul.")], "end_turn"),
        ([txt("I've sent the mail to Rahul.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "Rahul ko mail bhejo", tenant_id="default"))
    assert brain.script == [] and len(brain.seen) == 2       # one nudge, one retry
    nudge = brain.seen[1]["messages"][-1]["content"]
    assert "System check" in str(nudge)
    evs, _ = _rows(conv)
    notes = [t for t in _said(evs) if t.startswith("(To be clear")]
    assert len(notes) == 1


def test_false_mail_sent_corrected_by_the_model_gets_no_note(ao, monkeypatch):
    conv = ao["conv"]
    fixed = "I have not sent it yet - shall I draft the mail to Rahul now?"
    _set_brain(monkeypatch, FakeBrain([
        ([txt("I've sent the mail to Rahul.")], "end_turn"),
        ([txt(fixed)], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "Rahul ko mail bhejo", tenant_id="default"))
    assert out == fixed
    evs, _ = _rows(conv)
    assert not [t for t in _said(evs) if t.startswith("(")]


def test_a_non_action_false_claim_is_nudged_but_never_stapled(ao, monkeypatch):
    """'the reminder is set' is not an action on someone else - nudge once, then the reply stays its own words."""
    conv = ao["conv"]
    again = "Reminder laga diya, kal 9 baje."
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Reminder laga diya.")], "end_turn"),
        ([txt(again)], "end_turn"),
        ([txt(again)], "end_turn"),
        ([txt(again)], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "kal 9 baje yaad dilana", tenant_id="default"))
    assert out == again
    evs, msgs = _rows(conv)
    assert not [t for t in _said(evs) + msgs if t.startswith("(To be clear")]
    assert len(brain.seen) >= 2


def test_action_claim_helper():
    from app.agent import draftcheck as d
    assert d.action_claim("I've sent the mail to Rahul.")
    assert d.action_claim("Payment ho gaya, order placed.") or d.action_claim("I have paid the bill.")
    assert not d.action_claim("The weather is fine today.")


def test_console_shows_the_ledger_in_the_steps_fold():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js = (root / "v2.js").read_text()
    assert "case 'ledger': ledgerLine(p.line)" in js
    assert "ev.kind === 'ledger'" in js and "'maps_places', 'ledger'" in js
    assert ".wledger" in (root / "v2.css").read_text()
    from app.events import LOCAL_KINDS
    assert "ledger" in LOCAL_KINDS
