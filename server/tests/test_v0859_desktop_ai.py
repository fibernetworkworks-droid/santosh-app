"""v0.859 DESKTOP AI D1 + D2 + D4 (owner: 'GO D0 D1 D2 D4' on docs/DESKTOP_AI_PLAN.md):
D1 Claude's own computer toolset (zoom ...) mapped onto the desktop's actions, with a fallback when the API refuses it;
D2 a job split into checked stages; D4 'done' only after the screen is checked against her ask."""
import asyncio
import base64
import io

import pytest

from app.config import get_settings
from app.pc import brain, operator


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("PC_PLAN", "true")
    monkeypatch.setenv("PC_VERIFY", "true")
    monkeypatch.setenv("PC_NATIVE_TOOLS", "true")
    get_settings.cache_clear()
    operator.NATIVE_STATE["off"] = ""
    yield
    operator.NATIVE_STATE["off"] = ""
    get_settings.cache_clear()


def _jpeg(w, h):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(buf, "JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def test_native_members_map_onto_the_desktop():
    f = operator._from_native
    assert f("left_click", {"coordinate": [10, 20]}) == ("click", {"x": 10, "y": 20})
    assert f("triple_click", {"coordinate": [1, 2]})[1]["triple"] is True
    assert f("right_click", {"coordinate": [1, 2]})[1]["button"] == "right"
    assert f("left_click_drag", {"start_coordinate": [1, 2], "coordinate": [3, 4]}) == \
        ("drag", {"x": 1, "y": 2, "to_x": 3, "to_y": 4})
    assert f("key", {"text": "Return"}) == ("key", {"keys": "enter", "repeat": 1})
    assert f("key", {"text": "ctrl+Page_Down", "repeat": 3}) == ("key", {"keys": "ctrl+pagedown", "repeat": 3})
    assert f("scroll", {"scroll_direction": "down", "scroll_amount": 5})[1]["amount"] == -5
    assert f("scroll", {"scroll_direction": "left", "scroll_amount": 5})[0] is None
    assert f("left_click", {"coordinate": [1, 2], "text": "shift"})[0] is None
    assert f("middle_click", {"coordinate": [1, 2]})[0] is None
    assert f("hold_key", {"text": "a", "duration": 1})[0] is None


def test_native_tool_list_drops_the_clashing_custom_tools():
    op = operator.Op(id="n", tenant="t", conv="c", task="x", brain="sonnet")
    op.native = True
    tools = operator._tools_for(op)
    assert tools[0] == {"type": "computer_toolset_20260801"}
    names = {t.get("name") for t in tools[1:]}
    assert not names & operator.NATIVE_DROP and {"open_url", "ask_user", "stage_done", "done"} <= names
    op.brain = "qwen"
    assert not operator._native_on(op)              # Qwen keeps the custom tools


def _harness(monkeypatch, turns, checks=None, plan=None, refuse_native=False):
    calls, seen = [], []

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        args = args or {}
        if action == "screen":
            w = 2560 if (args.get("max_width") or 0) > 5000 else 1280
            return {"image_b64": _jpeg(w, w * 9 // 16), "width": w, "height": w * 9 // 16,
                    "active_window": "Swiggy - Google Chrome", "windows": ["Swiggy - Google Chrome"]}
        if action == "page_text":
            return {"text": "Swiggy cart: Farmhouse pizza"}
        calls.append((args.get("op") or action, dict(args)))
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "SETTLE_S", {})
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)
    script = iter(turns)
    state = {"refused": False}

    async def think(op, client, messages, params, retry):
        seen.append(params)
        if refuse_native and any(t.get("type") == "computer_toolset_20260801" for t in params["tools"]) and not state["refused"]:
            state["refused"] = True
            e = RuntimeError("computer_toolset_20260801 is not supported")
            e.status_code = 400
            raise e
        return brain.Reply(content=next(script), stop="tool_use")
    monkeypatch.setattr(brain, "think", think)
    cq = iter(checks or [])

    async def claude_json(model, system, content, max_tokens=700, timeout=25):
        if "plan a job" in system:
            return {"stages": plan} if plan else {}
        return next(cq, {"ok": True, "why": "looks right"})
    monkeypatch.setattr(operator, "_claude_json", claude_json)
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    monkeypatch.setattr(operator, "_inject", lambda op, text: 0)
    op = operator.Op(id="pcop_d", tenant="default", conv="c", task="Swiggy pe Farmhouse pizza cart mein daalo aur ruk jao",
                     brain="sonnet", brain_model="claude-sonnet-5-5")
    asyncio.run(operator._run(op))
    return op, calls, seen


def nt(i, name, **inp):
    return {"type": "tool_use", "id": f"n{i}", "name": name, "input": inp, "toolset_name": "computer"}


def tu(i, name, **inp):
    return {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}


def test_native_click_runs_and_its_result_carries_the_toolset_name(monkeypatch):
    op, calls, seen = _harness(monkeypatch, [
        [nt(1, "left_click", coordinate=[100, 200])],
        [tu(2, "done", answer="cart mein hai")],
    ])
    assert ("click", {"op": "click", "x": 100, "y": 200}) in calls
    assert seen[0]["tools"][0]["type"] == "computer_toolset_20260801" and "COMPUTER TOOLS" in seen[0]["system"]
    res = [b for m in seen[1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result"]
    assert res and res[-1]["toolset_name"] == "computer"
    assert op.status == "done"


def test_zoom_returns_a_full_resolution_crop_and_resets_the_click_scale(monkeypatch):
    op, calls, seen = _harness(monkeypatch, [
        [nt(1, "zoom", region=[0, 0, 320, 180])],
        [tu(2, "done", answer="ok")],
    ])
    res = [b for m in seen[1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
           for b in m["content"] if b.get("type") == "tool_result" and b.get("tool_use_id") == "n1"][0]
    imgs = [c for c in res["content"] if isinstance(c, dict) and c.get("type") == "image"]
    assert imgs and operator.STATS.get("zooms", 0) >= 1
    assert op.shot_w == 1280                          # the model's screenshot scale is back after the big capture


def test_refused_toolset_falls_back_to_the_custom_tools(monkeypatch):
    op, calls, seen = _harness(monkeypatch, [
        [tu(1, "click", x=5, y=5)],
        [tu(2, "done", answer="ok")],
    ], refuse_native=True)
    assert operator.NATIVE_STATE["off"] and op.native is False
    assert all(t.get("type") != "computer_toolset_20260801" for t in seen[-1]["tools"])
    assert ("click", {"op": "click", "x": 5, "y": 5}) in calls


def test_plan_stages_are_checked_before_moving_on(monkeypatch):
    plan = [{"goal": "Swiggy kholo", "done_when": "Swiggy home page", "ask": ""},
            {"goal": "Pizza cart mein", "done_when": "cart shows the pizza", "ask": ""}]
    op, calls, seen = _harness(monkeypatch, [
        [tu(1, "stage_done", stage=1, evidence="home page")],
        [tu(2, "stage_done", stage=2, evidence="cart")],
        [tu(3, "stage_done", stage=2, evidence="cart now")],
        [tu(4, "done", answer="Farmhouse cart mein")],
    ], checks=[{"ok": True, "why": "home"}, {"ok": False, "why": "cart is empty"}, {"ok": True, "why": "cart ok"},
               {"ok": True, "why": "done"}], plan=plan)
    first = seen[0]["messages"][0]["content"][0]["text"]
    assert "PLAN" in first and "Swiggy kholo" in first and "stage_done" in first
    texts = [str(b.get("content")) for m in seen[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
             for b in m["content"] if b.get("type") == "tool_result"]
    assert any("NOT YET (checker): cart is empty" in t for t in texts)
    assert op.stage == 2 and op.status == "done"


def test_done_is_sent_back_until_the_screen_shows_it(monkeypatch):
    op, calls, seen = _harness(monkeypatch, [
        [tu(1, "done", answer="ho gaya")],
        [tu(2, "done", answer="ab ho gaya")],
    ], checks=[{"ok": False, "why": "the cart is empty"}, {"ok": True, "why": "pizza in cart"}])
    texts = [str(b.get("content")) for m in seen[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
             for b in m["content"] if b.get("type") == "tool_result"]
    assert any("NOT VERIFIED" in t and "the cart is empty" in t for t in texts)
    assert op.status == "done" and op.verify_rejects == 1 and "pizza in cart" in op.verified


def test_checker_that_cannot_run_never_blocks(monkeypatch):
    op, calls, seen = _harness(monkeypatch, [[tu(1, "done", answer="ok")]], checks=[{}])
    assert op.status == "done"
