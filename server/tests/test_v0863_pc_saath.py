"""v0.863 PC SAATH - her log: a new pizza task opened a SECOND Swiggy tab, 'cancel pizza, order KFC' after the task
ended went to Hoola's own PC, page_text (~10 s on Swiggy) was read after every open."""
import asyncio
import types

import pytest

from app.agent import pick
from app.agent.tools import ToolError
from app.pc import operator


async def _noop():
    return None


def _fake(monkeypatch, front, tabs=()):
    seen = []

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        seen.append((action, (args or {}).get("keys") or (args or {}).get("op") or (args or {}).get("tab")))
        if action == "screen":
            return {"image_b64": "QUJD", "width": 1, "height": 1, "active_window": front[0],
                    "windows": [front[0]]}
        if action == "tabs":
            return {"tabs": [{"title": t} for t in tabs]}
        if action == "switch_tab":
            front[0] = args["tab"] + " - Google Chrome"
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(asyncio, "sleep", lambda *_a, **_k: _noop())
    op = operator.Op(id="pcop_s", tenant="t", conv="c", task="swiggy")
    op.browser, op.browser_src = "chrome", "said"
    return op, seen


def test_site_word_and_root():
    assert operator._site_word("https://www.swiggy.com/") == "swiggy"
    assert operator._site_word("amazon.in/cart") == "amazon"
    assert operator._is_root("https://www.swiggy.com/") and not operator._is_root("swiggy.com/search?q=kfc")


def test_open_url_reuses_the_swiggy_tab_already_in_front(monkeypatch):
    op, seen = _fake(monkeypatch, ["Swiggy Cart - Google Chrome"])
    out = asyncio.run(operator._do(op, "open_url", {"url": "https://www.swiggy.com"}))
    assert "ALREADY open" in out and ("control", "ctrl+t") not in seen and not any(a == "page_text" for a, _ in seen)


def test_open_url_switches_to_the_swiggy_tab_behind(monkeypatch):
    op, seen = _fake(monkeypatch, ["Google - Google Chrome"], tabs=["Google", "Swiggy | Cart"])
    out = asyncio.run(operator._do(op, "open_url", {"url": "https://www.swiggy.com/"}))
    assert ("switch_tab", "Swiggy | Cart") in seen and "ALREADY open" in out and ("control", "ctrl+t") not in seen


def test_open_url_new_site_still_new_tab_and_no_slow_page_text(monkeypatch):
    op, seen = _fake(monkeypatch, ["Google - Google Chrome"], tabs=["Google"])
    asyncio.run(operator._do(op, "open_url", {"url": "https://www.zomato.com"}))
    assert ("control", "ctrl+t") in seen and not any(a == "page_text" for a, _ in seen)


def test_after_her_pc_task_hoola_pc_and_server_browser_refused(monkeypatch):
    operator.HER_PC_AT["t_saath"] = __import__("time").time()
    ctx = types.SimpleNamespace(tenant_id="t_saath", conversation_id="conv_new", place="", admit=None)
    try:
        with pytest.raises(ToolError, match="pc_do"):
            pick.check("hoola_pc_do", {"task": "KFC se chicken order karo swiggy par"}, ctx)
        monkeypatch.setattr("app.pc.hub.hub.is_online", lambda *_a: True, raising=False)
        with pytest.raises(ToolError, match="pc_do"):
            pick.check("browse_web", {"task": "order KFC chicken on swiggy"}, ctx)
        pick.check("pc_do", {"task": "Cancel pizza, order KFC chicken on Swiggy"}, ctx)   # allowed, no error
    finally:
        operator.HER_PC_AT.pop("t_saath", None)


def test_hoola_pc_named_in_this_message_still_works():
    operator.HER_PC_AT["t_saath2"] = __import__("time").time()
    ctx = types.SimpleNamespace(tenant_id="t_saath2", conversation_id="conv_x", place="hoolapc", admit=None)
    try:
        pick.check("hoola_pc_do", {"task": "install blender"}, ctx)
    finally:
        operator.HER_PC_AT.pop("t_saath2", None)
