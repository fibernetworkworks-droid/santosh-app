"""v0.856 PC SPEED (owner: 'TASK DOING PROCESS IS VERY VERY EXTREEM SLOW IT SHOULD BE IN REAL TIME' -> 'GO PC SPEED'):
Qwen thinking off + OpenRouter's fastest host, fewer old screenshots per step, and 'open Notepad + type' in ONE
turn - the typing runs only once the opened app is really the active window."""
import asyncio
import types

from app.config import Settings, get_settings
from app.pc import brain, operator


def test_speed_defaults():
    f = Settings.model_fields
    assert f["pc_qwen_thinking"].default == "off"
    assert f["pc_qwen_provider_sort"].default == "latency"
    assert operator.KEEP_IMAGES == 2


def test_qwen_body_asks_for_the_fastest_host_and_no_thinking(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.delenv("PC_QWEN_THINKING", raising=False)
    get_settings.cache_clear()
    seen = {}

    async def post(url, key, body, timeout):
        seen.update(body)
        return {"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]}
    monkeypatch.setattr(brain, "_post", post)
    asyncio.run(brain.think_qwen("qwen/qwen3.8-max-0902", "S", [{"role": "user", "content": "x"}], [], 100))
    assert seen["reasoning"] == {"enabled": False}
    assert seen["provider"] == {"sort": "latency"}
    get_settings.cache_clear()


def _run(monkeypatch, turns, windows):
    """Drive the real loop with a fake desktop: open_app changes the active window after `windows` screens."""
    calls, state = [], {"win": "Desktop", "pending": None, "left": 0}

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        args = args or {}
        if action == "screen":
            if state["pending"] is not None:
                state["left"] -= 1
                if state["left"] <= 0:
                    state["win"], state["pending"] = state["pending"], None
            return {"image_b64": "QUJD", "width": 1280, "height": 720, "active_window": state["win"], "windows": [state["win"]]}
        calls.append((args.get("op") or action, dict(args), state["win"]))
        if args.get("op") == "open_app":
            state["pending"], state["left"] = f"Untitled - {args.get('name')}", windows
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "SETTLE_S", {})
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(operator.asyncio, "sleep", lambda s: real_sleep(0))
    script = iter(turns)

    async def think(op, client, messages, params, retry):
        return brain.Reply(content=next(script), stop="tool_use")
    monkeypatch.setattr(brain, "think", think)
    monkeypatch.setattr(operator, "_do", _real_do_like(fake_pc))
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    op = operator.Op(id="t", tenant="default", conv="c", task="Notepad kholo aur likho")
    asyncio.run(operator._run(op))
    return op, calls


def _real_do_like(fake_pc):
    async def do(op, name, a):
        await fake_pc(op, "control", {"op": name, **a})
        return "ok"
    return do


def tu(i, tool, **a):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": a}


def test_open_then_type_in_one_turn_waits_for_the_app(monkeypatch):
    op, calls = _run(monkeypatch, [
        [tu(1, "open_app", name="Notepad"), tu(2, "type", text="Hoola test 1")],
        [tu(3, "done", answer="likh diya")],
    ], windows=2)
    typed = [c for c in calls if c[0] == "type"]
    assert typed and typed[0][2] == "Untitled - Notepad"        # typed only once Notepad was in front
    assert op.status == "done"
    assert operator.STATS.get("fast_type", 0) >= 1


def test_type_is_still_held_when_the_app_never_comes_to_front(monkeypatch):
    op, calls = _run(monkeypatch, [
        [tu(1, "open_app", name="Notepad"), tu(2, "type", text="secret")],
        [tu(3, "done", answer="nahi hua")],
    ], windows=99)
    assert not [c for c in calls if c[0] == "type"]              # never typed into the wrong window


def test_click_after_open_app_is_still_held(monkeypatch):
    op, calls = _run(monkeypatch, [
        [tu(1, "open_app", name="Notepad"), tu(2, "click", x=10, y=10)],
        [tu(3, "done", answer="ok")],
    ], windows=1)
    assert not [c for c in calls if c[0] == "click"]


def test_prompt_asks_for_few_turns():
    assert "SPEED:" in operator.SYSTEM and "ONE type action" in operator.SYSTEM


def test_target_words_cover_apps_windows_tabs_sites():
    t = operator._target_of
    assert t("open_app", {"name": "Settings"}) == "Settings"
    assert t("focus_window", {"title": "Tally Prime"}) == "Tally Prime"
    assert t("switch_tab", {"tab": "Gmail"}) == "Gmail"
    assert t("open_url", {"url": "https://www.irctc.co.in/nget"}) == "irctc"
    assert operator.FAST_AFTER >= {"open_app", "ax_launch", "focus_window", "open_url", "switch_tab"}


def test_site_then_keys_in_one_turn(monkeypatch):
    calls, state = [], {"win": "New Tab - Google Chrome"}

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        args = args or {}
        if action == "screen":
            return {"image_b64": "QUJD", "width": 1280, "height": 720, "active_window": state["win"], "windows": [state["win"]]}
        calls.append((args.get("op") or action, state["win"]))
        if args.get("op") == "open_url":
            state["win"] = "Gmail - Inbox - Google Chrome"
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "SETTLE_S", {})
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(operator.asyncio, "sleep", lambda s: real_sleep(0))
    script = iter([[tu(1, "open_url", url="https://mail.google.com"), tu(2, "key", keys="c")],
                   [tu(3, "done", answer="ok")]])

    async def think(op, client, messages, params, retry):
        return brain.Reply(content=next(script), stop="tool_use")
    monkeypatch.setattr(brain, "think", think)
    monkeypatch.setattr(operator, "_do", _real_do_like(fake_pc))
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    # mail.google.com -> word 'mail' (browser names never count); 'Gmail - Inbox' carries it -> same turn
    asyncio.run(operator._run(operator.Op(id="t2", tenant="default", conv="c", task="gmail kholo")))
    assert ("key", "Gmail - Inbox - Google Chrome") in calls


def test_browser_name_alone_never_proves_the_page():
    assert operator._target_of("open_url", {"url": "https://www.google.com"}) == ""   # held, as before
    assert asyncio.run(operator._opened_in_front(operator.Op(id="x", tenant="d", conv="c", task="t"), "")) is False
