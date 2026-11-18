"""v0.876 PC STEADY (owner: "1) WORK CONSISTANCY 2) THINKING ON SCREEN ... popups get it stuck ... repeatedly does the
same work" -> "GO ALL THREE"): a progress list, no re-opening, repeats counted, popups and stolen focus caught, and the
model's own line shown live."""
import asyncio
import types

from app.pc import brain, operator, steady


def _op(**kw):
    op = operator.Op(id="t", tenant="default", conv="c", task="Swiggy par pizza order karo")
    for k, v in kw.items():
        setattr(op, k, v)
    return op


def tu(i, tool, **a):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": a}


def say(text):
    return {"type": "text", "text": text}


# ---------------------------------------------------------------- thinking line
def test_thought_is_the_first_real_line_cleaned_and_short():
    assert steady.thought_of("**Swiggy khul gaya**, ab pizza search kar raha hoon\nmore") == \
        "Swiggy khul gaya, ab pizza search kar raha hoon"
    assert steady.thought_of("") == "" and steady.thought_of("{\"x\": 1}") == ""
    assert len(steady.thought_of("a" * 400)) <= 160


def test_thought_masks_secret_numbers():
    assert "4111 1111 1111 1111" not in steady.thought_of("Card 4111 1111 1111 1111 dikh raha hai")


def test_prompt_asks_for_the_line_progress_and_popups_first():
    for must in ("ONE short line", "PROGRESS SO FAR", "POPUPS FIRST", "Allow location", "changed nothing"):
        assert must in steady.PROMPT


# ---------------------------------------------------------------- progress + repeats
def test_progress_records_only_what_worked_and_flags_a_repeat():
    op = _op()
    op.step, op.action = 1, "swiggy.com khol raha hoon"
    assert steady.record(op, "open_url", {"url": "https://www.swiggy.com/"}, "opened ...") == ""
    op.step, op.action = 2, "likh raha hoon"
    steady.record(op, "type", {"text": "pizza"}, "typed")
    steady.record(op, "type", {"text": "burger"}, "ERROR: no field")         # failed = not progress
    steady.record(op, "page_text", {}, "text")                              # a read = not progress
    assert [r["step"] for r in op.progress] == [1, 2]
    op.step = 3
    note = steady.record(op, "type", {"text": "Pizza "}, "typed")
    assert "already did this at step 2" in note and op.aim_repeats == 1
    block = steady.progress_block(op)
    assert "PROGRESS SO FAR" in block and "swiggy.com khol raha hoon" in block and "Task:" in block


def test_already_open_needs_the_same_page_and_the_site_in_front():
    op = _op(opened_urls={"swiggy.com/search?q=pizza": 2})
    assert "ALREADY OPEN" in steady.already_open(op, "https://www.swiggy.com/search?q=pizza", "Swiggy - Google Chrome")
    assert steady.already_open(op, "https://www.swiggy.com/search?q=pizza", "New Tab - Google Chrome") == ""
    assert steady.already_open(op, "https://www.swiggy.com/", "Swiggy - Google Chrome") == ""   # another page


def test_carry_from_a_replaced_task():
    old = _op(step=9, task="Swiggy kholo")
    old.progress = [{"step": 1, "text": "swiggy.com khol raha hoon", "n": 1}]
    c = steady.carry_from(old)
    assert "EARLIER TASK" in c and "swiggy.com khol raha hoon" in c and "do not redo" in c
    assert steady.carry_from(_op()) == ""


def test_rescue_counts_repeated_aims_as_stuck(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("PC_VIA_OPENROUTER", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        from app.pc import rescue
        op = _op(brain="qwen27", aim_repeats=2)
        img = [{"type": "image", "source": {"data": "x"}}]
        note = rescue.observe(op, [tu(1, "type", text="a")], [{"tool_use_id": "t1", "content": "ok"}], img)
        assert "redoing work" in note and op.aim_repeats == 0 and op.rescue_left > 0
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- popups / focus
def test_screen_note_only_when_an_action_changed_nothing():
    op = _op()
    shot = [{"type": "image", "source": {"data": "same"}}]
    assert steady.screen_note(op, shot, ["click"]) == ""          # first screen: nothing to compare
    assert "SCREEN UNCHANGED" in steady.screen_note(op, shot, ["click"])
    assert steady.screen_note(op, shot, []) == ""                  # only reading: not stuck


def test_focus_ok_same_app_different_tab_title():
    assert steady.focus_ok("Swiggy - Google Chrome", "Pizza near me - Google Chrome")
    assert not steady.focus_ok("Swiggy - Google Chrome", "Windows Update")
    assert steady.focus_ok("", "x")


def test_sweep_reports_a_window_that_took_the_front_and_new_toasts():
    op = _op(window="Update available", windows=["Update available", "Swiggy - Google Chrome"])
    calls = []

    async def pc(o, action, args=None, timeout=40, log=True):
        calls.append(action)
        return {"notifications": [{"app": "WhatsApp", "title": "Mummy", "body": "khana kha liya?"}]}
    out = asyncio.run(steady.sweep(op, pc, ["Swiggy - Google Chrome"], "Swiggy - Google Chrome", ["click"], False))
    assert "came to the front by itself" in out and "WhatsApp" in out and "DATA" in out and op.popups == 1
    again = asyncio.run(steady.sweep(op, pc, list(op.windows), op.window, ["click"], False))
    assert "WhatsApp" not in again                     # a notification is told once


def test_sweep_silent_when_all_is_well_and_off_when_the_helper_is_missing():
    op = _op(window="Swiggy - Google Chrome", windows=["Swiggy - Google Chrome"], step=1)

    async def broken(o, action, args=None, timeout=40, log=True):
        raise RuntimeError("agent-desktop missing")
    assert asyncio.run(steady.sweep(op, broken, list(op.windows), op.window, ["click"], False)) == ""
    op.unchanged, op.step = 1, 9
    asyncio.run(steady.sweep(op, broken, list(op.windows), op.window, ["click"], False))
    assert op.toasts_off is True


# ---------------------------------------------------------------- the real loop with a fake PC
def _run(monkeypatch, turns, screens=None, task="Swiggy par pizza dhoondho"):
    seen_msgs, calls = [], []
    state = {"win": "Swiggy - Google Chrome", "n": 0}
    screens = list(screens or [])

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        args = args or {}
        if action == "screen":
            state["n"] += 1
            if screens:
                state["win"] = screens.pop(0)
            return {"image_b64": f"IMG{state['n']}", "width": 1280, "height": 720, "active_window": state["win"],
                    "windows": [state["win"]]}
        calls.append((args.get("op") or action, dict(args)))
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "SETTLE_S", {})
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(operator.asyncio, "sleep", lambda s: real_sleep(0))
    script = iter(turns)

    async def think(op, client, messages, params, retry):
        seen_msgs.append([m for m in messages])
        return brain.Reply(content=next(script), stop="tool_use")
    monkeypatch.setattr(brain, "think", think)

    async def do(op, name, a):
        await fake_pc(op, "control", {"op": name, **a})
        if name == "open_url":
            return f"opened {a.get('url')} in Chrome (new tab)"
        return "ok"
    monkeypatch.setattr(operator, "_do", do)
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    op = operator.Op(id="t", tenant="default", conv="c", task=task)
    asyncio.run(operator._run(op))
    return op, calls, seen_msgs


def _last_user_text(msgs):
    out = []
    for b in msgs[-1]["content"]:
        c = b.get("content") if isinstance(b, dict) else None
        for x in (c if isinstance(c, list) else []):
            if isinstance(x, dict) and x.get("type") == "text":
                out.append(x["text"])
    return "\n".join(out)


def test_loop_keeps_the_thought_and_sends_progress_every_turn(monkeypatch):
    op, calls, seen = _run(monkeypatch, [
        [say("Chrome saamne hai, Swiggy khol raha hoon"), tu(1, "open_url", url="https://www.swiggy.com/")],
        [say("Swiggy khul gaya, ab search karta hoon"), tu(2, "page_click", ref=4)],
        [tu(3, "done", answer="mil gaya")],
    ])
    assert op.status == "done"
    assert [t["text"] for t in op.thoughts] == ["Chrome saamne hai, Swiggy khol raha hoon",
                                                "Swiggy khul gaya, ab search karta hoon"]
    assert op.live()["thought"] == "Swiggy khul gaya, ab search karta hoon"
    text = _last_user_text(seen[-1])
    assert "PROGRESS SO FAR" in text and "swiggy.com khol raha hoon" in text


def test_loop_types_only_into_the_window_the_model_saw(monkeypatch):
    # the model saw Chrome; before its typing a Windows Update dialog takes the front
    op, calls, seen = _run(monkeypatch, [
        [say("Search box mein likh raha hoon"), tu(1, "type", text="pizza")],
        [tu(2, "done", answer="ok")],
    ], screens=["Swiggy - Google Chrome", "Windows Update"])
    assert not [c for c in calls if c[0] == "type"]
    held = _last_user_text(seen[-1])
    assert "window in front changed" in held


def test_open_url_already_open_is_not_reopened(monkeypatch):
    op = _op(opened_urls={"swiggy.com": 1})
    op.kind = ""

    async def fake_pc(o, action, args=None, timeout=40, log=True):
        if action == "screen":
            return {"active_window": "Swiggy - Google Chrome", "windows": ["Swiggy - Google Chrome"]}
        raise AssertionError("must not open the site again: " + action)
    monkeypatch.setattr(operator, "_pc", fake_pc)
    out = asyncio.run(operator._do(op, "open_url", {"url": "https://www.swiggy.com/"}))
    assert out.startswith("ALREADY OPEN")


def test_replaced_task_carries_progress(monkeypatch):
    import inspect
    src = inspect.getsource(operator.start)
    assert "carry_from(old)" in src and "op.carry = carry" in src
    assert "op.carry" in inspect.getsource(operator._run)


def test_phone_card_shows_the_thought():
    from pathlib import Path
    dart = (Path(__file__).resolve().parents[2] / "lib/ui/browser_live.dart").read_text(encoding="utf-8")
    assert "l['thought']" in dart and "💭 $thought" in dart
