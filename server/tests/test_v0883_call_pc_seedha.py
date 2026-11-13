"""v0.883 CALL PC SEEDHA: a call turn never goes long-job, stops watching a PC task it handed off, keeps the PC tools
for a follow-up; the PC skips a dead browser lane, says an admin window cannot be driven, never clicks Hoola's banner."""
import inspect
import types

from app import pcconnect
from app.pc import steady


def test_call_turn_not_big_and_no_studio_block():
    from app.agent import santosh
    src = inspect.getsource(santosh._steps_begin)
    assert "not VOICE_BRAIN_NOW.get()\n                        and _goal.looks_big" in src
    assert '"" if VOICE_BRAIN_NOW.get() else _tmode.rules()' in src


def test_call_stops_watching_after_handoff():
    from app.agent import santosh
    src = inspect.getsource(santosh)
    assert 'state.get("pc_handed") and _pc_watch(b["name"])' in src and 'state["pc_handed"] = True' in src
    assert santosh._pc_watch("pc_do") and santosh._pc_watch("pc_task_result") and santosh._pc_watch("kaam_status")
    assert not santosh._pc_watch("pc_search") and not santosh._pc_watch("email_draft")


def test_follow_up_on_a_call_keeps_pc_tools(monkeypatch):
    from app.agent import pc_manager, santosh
    from app.pc import operator as O
    st = types.SimpleNamespace(pc_manager=True)
    ctx = types.SimpleNamespace(place="")
    monkeypatch.setattr(O, "live_for", lambda t, c: None)
    monkeypatch.setattr(O, "her_pc_recent", lambda t, secs=2700: True)
    assert not pc_manager.wanted(st, ctx, "c1", "t1", "isse minimize kar do")          # chat: needs a PC word
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        assert pc_manager.wanted(st, ctx, "c1", "t1", "isse minimize kar do")          # call: right after a PC task
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)


def test_spoken_task_is_short():
    t = "[Team job: Swiggy par Margherita cart mein daalna] Aapke PC ke Chrome mein ek NAYA TAB kholo aur..."
    assert pcconnect._short_task(t) == "Swiggy par Margherita cart mein daalna"


def test_browser_lane_skipped_after_two_failures():
    op = types.SimpleNamespace()
    assert steady.lane_skip(op, "page_elements") == ""
    steady.lane_seen(op, "page_elements", "ERROR: no browser")
    steady.lane_seen(op, "page_text", "ERROR: no browser")
    assert steady.lane_skip(op, "tabs").startswith("SKIPPED") and steady.lane_skip(op, "click") == ""
    steady.lane_seen(op, "page_text", "Page: x")
    assert steady.lane_skip(op, "tabs") == ""
    from app.pc import operator, rescue
    s = inspect.getsource(operator)
    assert "steady.lane_skip(op, name)" in s and "steady.admin_note(op)" in s and '" ERROR | "' in s
    assert not "SKIPPED".startswith(("ERROR", "REFUSED", "NOT RUN"))   # a skip never sets off the rescue


def test_admin_window_said_once():
    op = types.SimpleNamespace(window="Task Manager", unchanged=1)
    assert steady.admin_note(op) == ""
    op.unchanged = 2
    assert "ADMIN WINDOW" in steady.admin_note(op) and steady.admin_note(op) == ""
    assert steady.admin_note(types.SimpleNamespace(window="Swiggy - Google Chrome", unchanged=5)) == ""


def test_prompt_rules():
    assert "HOOLA'S OWN WINDOW" in steady.PROMPT and "open_app 'Task Manager'" in steady.PROMPT


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.884.0")
