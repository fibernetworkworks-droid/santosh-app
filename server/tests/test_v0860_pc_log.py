"""v0.860 PC KA HISAAB: every PC task explains itself in the server log (start, replace, plan, checks, ask, end),
so a messy run on her PC can be read from `pm2 logs` instead of guessed."""
import logging

from tests.test_v0859_desktop_ai import _harness, _on, tu  # noqa: F401  (fixture reused)


def test_run_logs_plan_check_and_end(monkeypatch, caplog):
    plan = [{"goal": "Swiggy kholo", "done_when": "Swiggy home", "ask": ""},
            {"goal": "Pizza cart mein", "done_when": "cart shows it", "ask": ""}]
    caplog.set_level(logging.INFO, logger="santosh.pcop")
    _harness(monkeypatch, [[tu(1, "stage_done", stage=1, evidence="home")],
                           [tu(2, "stage_done", stage=2, evidence="cart")],
                           [tu(3, "done", answer="cart mein")]],
             checks=[{"ok": True, "why": "home"}, {"ok": True, "why": "cart"}, {"ok": True, "why": "done"}], plan=plan)
    text = caplog.text
    assert "pc plan pcop_d 2 stages: Swiggy kholo > Pizza cart mein" in text
    assert "pc check pcop_d ok=True" in text
    assert "pc task end pcop_d status=done" in text


def test_tell_is_logged(monkeypatch, caplog):
    from app.pc import operator
    op = operator.Op(id="pcop_t", tenant="t1", conv="c1", task="x")
    monkeypatch.setattr(operator, "live_for", lambda tenant, conv="": op)
    caplog.set_level(logging.INFO, logger="santosh.pcop")
    operator.tell("t1", "c1", "Margherita lo")
    assert "pc task pcop_t told (her words, from chat c1): Margherita lo" in caplog.text
