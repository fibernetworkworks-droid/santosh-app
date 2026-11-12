"""v0.867 PC SASTA (owner: 'GO QWEN 27B'): the cheap PC worker (Qwen 3.8 27B on OpenRouter), the Sonnet rescue when it is
stuck, the desktop playbook, and the step / daily rupee caps."""
from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace as NS

import pytest

from app.config import get_settings


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    monkeypatch.setenv("PC_MODEL", "qwen27")
    get_settings.cache_clear()
    from app.pc import rescue
    rescue.SPEND.clear()
    yield
    get_settings.cache_clear()


def _op(**kw):
    base = dict(id="op1", brain="qwen27", brain_model="qwen/qwen3.8-27b", step=3, tenant="t1", rescue_left=0,
                rescues=0, sigs=[], shots=[], err_run=0)
    base.update(kw)
    return NS(**base)


def _use(name, **inp):
    return {"type": "tool_use", "id": "u" + name, "name": name, "input": inp}


def _res(text="ok"):
    return {"type": "tool_result", "tool_use_id": "x", "content": text}


def _shot(tag):
    return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": tag}}]


def test_default_brain_is_the_cheap_qwen27_when_keyed(keyed):
    from app.pc import brain
    assert brain.choose("") == ("qwen27", "qwen/qwen3.8-27b", "")
    assert brain.choose("qwen")[0] == "qwen" and brain.choose("sonnet")[0] == "sonnet-or"


def test_no_openrouter_key_runs_sonnet_and_says_so(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("PC_MODEL", "qwen27")
    get_settings.cache_clear()
    try:
        from app.pc import brain
        b, m, note = brain.choose("")
        if brain.qwen_route() is None:
            assert b == "sonnet" and "OpenRouter" in note
    finally:
        get_settings.cache_clear()


def test_cheap_worker_request_shape(keyed, monkeypatch):
    from app.pc import brain
    sent = {}

    async def fake_post(url, key, body, timeout):
        sent.update(body=body)
        return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {
            "name": "done", "arguments": "{}"}}]}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 9, "completion_tokens": 1}}
    monkeypatch.setattr(brain, "_post", fake_post)
    op = _op()
    rep = asyncio.run(brain.think(op, None, [{"role": "user", "content": "go"}], {"system": "S", "tools": [
        {"name": "done", "description": "d", "input_schema": {"type": "object"}}], "max_tokens": 300}, None))
    b = sent["body"]
    assert b["model"] == "qwen/qwen3.8-27b" and b["reasoning"] == {"enabled": False}
    assert isinstance(b["messages"][0]["content"], str)      # no Anthropic cache_control on Qwen
    assert rep.content[0]["type"] == "tool_use"


def test_stuck_same_action_three_times_starts_a_rescue(keyed):
    from app.pc import rescue
    op = _op()
    for i in range(2):
        assert rescue.observe(op, [_use("click", x=10, y=20)], [_res()], _shot("a%d" % i)) == ""
    note = rescue.observe(op, [_use("click", x=10, y=20)], [_res()], _shot("a9"))
    assert "same action three times" in note and op.rescue_left == 3 and op.rescues == 1


def test_screen_not_changing_after_two_actions_starts_a_rescue(keyed):
    from app.pc import rescue
    op = _op()
    rescue.observe(op, [_use("click", x=1, y=1)], [_res()], _shot("S"))
    rescue.observe(op, [_use("click", x=2, y=2)], [_res()], _shot("S"))
    note = rescue.observe(op, [_use("click", x=3, y=3)], [_res()], _shot("S"))
    assert "screen did not change" in note and op.rescue_left == 3


def test_two_errors_in_a_row_start_a_rescue(keyed):
    from app.pc import rescue
    op = _op()
    assert rescue.observe(op, [_use("click", x=1, y=1)], [_res("ERROR: nope")], _shot("a")) == ""
    note = rescue.observe(op, [_use("click", x=2, y=2)], [_res("REFUSED: twin")], _shot("b"))
    assert "error" in note and op.rescue_left == 3


def test_scrolling_waiting_and_reading_are_not_stuck(keyed):
    from app.pc import rescue
    op = _op()
    for i in range(5):
        assert rescue.observe(op, [_use("scroll", amount=-5)], [_res()], _shot("S")) == ""
    for i in range(4):
        assert rescue.observe(op, [_use("page_text")], [_res()], _shot("S")) == ""
    assert op.rescue_left == 0


def test_only_the_cheap_worker_gets_a_rescue(keyed):
    from app.pc import rescue
    op = _op(brain="sonnet-or")
    for _ in range(4):
        assert rescue.observe(op, [_use("click", x=1, y=1)], [_res()], _shot("S")) == ""
    assert op.rescue_left == 0


def test_rescue_steps_run_on_sonnet_then_the_cheap_worker_returns(keyed, monkeypatch):
    from app.pc import brain
    used = []

    async def fake_post(url, key, body, timeout):
        used.append(body["model"])
        return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}
    monkeypatch.setattr(brain, "_post", fake_post)
    op = _op(rescue_left=2)
    for _ in range(4):
        asyncio.run(brain.think(op, None, [{"role": "user", "content": "go"}], {"system": "S", "tools": [], "max_tokens": 50}, None))
    assert used == ["anthropic/claude-sonnet-5.5", "anthropic/claude-sonnet-5.5", "qwen/qwen3.8-27b", "qwen/qwen3.8-27b"]
    assert op.rescue_left == 0


def test_rescues_per_task_are_capped(keyed):
    from app.pc import rescue
    op = _op()
    cap = int(get_settings().pc_rescue_max)
    started = 0
    for i in range(cap * 8):
        if rescue.observe(op, [_use("click", x=5, y=5)], [_res()], _shot("q%d" % i)):
            started += 1
            op.rescue_left = 0           # the rescue steps ran
    assert started == cap and op.rescues == cap


def test_rescue_off_switch(keyed, monkeypatch):
    monkeypatch.setenv("PC_RESCUE", "false")
    get_settings.cache_clear()
    from app.pc import rescue
    op = _op()
    for _ in range(4):
        assert rescue.observe(op, [_use("click", x=1, y=1)], [_res()], _shot("S")) == ""
    assert rescue.rescue_active(_op(rescue_left=2)) is None


def test_daily_rupee_cap_stops_a_task(keyed, monkeypatch):
    monkeypatch.setenv("PC_DAILY_INR", "1")
    get_settings.cache_clear()
    from app.pc import rescue
    op = _op()
    assert rescue.over_budget(op) == ""
    for _ in range(6):
        rescue.charge(op, "qwen27")            # 6 x Rs 0.2 = Rs 1.2
    msg = rescue.over_budget(op)
    assert "limit" in msg and "PC_DAILY_INR" in msg
    assert rescue.over_budget(_op(tenant="other")) == ""        # per person
    monkeypatch.setenv("PC_DAILY_INR", "0")
    get_settings.cache_clear()
    assert rescue.over_budget(op) == ""                          # 0 = no cap


def test_step_cap(keyed, monkeypatch):
    from app.pc import rescue
    assert rescue.step_cap(80) == 64 and rescue.step_cap(25) == 25
    monkeypatch.setenv("PC_STEP_CAP", "0")
    get_settings.cache_clear()
    assert rescue.step_cap(80) == 80


def test_playbook_only_for_the_cheap_worker(keyed):
    from app.pc import rescue
    assert rescue.playbook_on(_op()) is True
    assert rescue.playbook_on(_op(brain="sonnet-or")) is False
    for must in ("ONE job", "ACT, then CHECK", "CHOICES are hers", "STOP before money", "DONE means the result is on the screen"):
        assert must in rescue.PLAYBOOK


def test_operator_wiring_pins():
    from app.pc import operator
    src = inspect.getsource(operator)
    assert "_rescue.PLAYBOOK" in src and "_rescue.observe(op, uses, results, shot)" in src
    assert "_rescue.over_budget(op)" in src and "_rs.step_cap(op.steps_max)" in src
    bsrc = inspect.getsource(__import__("app.pc.brain", fromlist=["x"]))
    assert "rescue.rescue_active(op)" in bsrc and "_rs.charge(op, brain)" in bsrc


def test_settings_defaults():
    get_settings.cache_clear()
    st = get_settings()
    assert st.pc_cheap_model == "qwen/qwen3.8-27b" and st.pc_rescue is True and st.pc_rescue_steps == 3
    assert st.pc_daily_inr == 300 and st.pc_step_cap == 64 and st.pc_playbook is True
