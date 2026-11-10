"""v0.636 KAHAN RUKA (her 16:22 call: 18 s before the first Claude call, the calls themselves 5.3 s + 3.3 s at 143k chars).
A call brain turn logs every stage before its first call, skips the whole-chat compaction, and cuts earlier tool results."""
import inspect
import types

from app.agent import santosh


def test_prep_marks_make_one_line():
    tok = santosh._PREP.set({"t0": 0.0, "last": 0.0, "marks": []})
    try:
        import time
        p = santosh._PREP.get()
        p["t0"] = p["last"] = time.monotonic()
        santosh._mark("lock")
        santosh._mark("memory")
        line = santosh._prep_line()
        assert line.startswith("brain prep ") and "lock " in line and "memory " in line
        assert santosh._prep_line() == ""          # once per turn
        santosh._mark("late")                      # after the line: ignored
        assert len(p["marks"]) == 2
    finally:
        santosh._PREP.reset(tok)


def test_no_prep_outside_a_call():
    santosh._mark("x")
    assert santosh._prep_line() == ""


def test_old_results_cut_on_brain_turn_only():
    big = "m" * 9000
    hist = [{"role": "user", "content": "pehle"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "email_check", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": big}]},
            {"role": "assistant", "content": [{"type": "text", "text": "yeh rahe mail"}]},
            {"role": "user", "content": "abhi"}]
    st = types.SimpleNamespace(voice_brain_history=8, voice_brain_result_chars=1500, chat_context="claude")
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        msgs = santosh._request(hist, "sys", [], "claude", "c1", {"turn_start": 4}, st)
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)
    res = [b for m in msgs if isinstance(m["content"], list) for b in m["content"] if b.get("type") == "tool_result"]
    assert res and len(res[0]["content"]) < 1700 and "dobara" in res[0]["content"]
    assert hist[2]["content"][0]["content"] == big          # the saved history is never changed


def test_brain_turn_skips_compaction_and_defaults():
    src = inspect.getsource(santosh._run_turn)
    assert 'STATS_PREP["compact_skipped"] += 1' in src and "_compact.before_turn" in src
    from app.config import Settings
    f = Settings.model_fields
    assert f["voice_brain_history"].default == 8 and f["voice_brain_result_chars"].default == 1500
