"""v0.893 HOOLA COMPUTER TOOLS - her first live test: in a Hoola PC chat Hoola never called the Hoola PC (it opened
Google Translate in the server's browser instead) because the PC tools were only admitted when her words said 'PC'.
A computer's own chat now always has the PC tools in view."""
from __future__ import annotations

import asyncio

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0864_pc_manager import _capture, live  # noqa: F401


def _new_chat(tenant: str, which: str) -> str:
    from app import computer
    if which == "mine":
        computer.set_mine(tenant, True)
    return computer.new_chat(tenant, which)["id"]


def test_hoola_pc_chat_sees_the_hoola_pc_tool(live, monkeypatch):
    santosh, seen = _capture(monkeypatch)
    conv = _new_chat("default", "hoola")
    asyncio.run(santosh.run_turn(conv, "Google translate kholo aur 'good morning' ka Hindi batao"))
    assert seen and "hoola_pc_do" in seen[0]["tools"]


def test_ordinary_chat_does_not_get_pc_tools_for_the_same_words(live, monkeypatch):
    santosh, seen = _capture(monkeypatch)
    asyncio.run(santosh.run_turn(live["conv"], "Google translate kholo aur 'good morning' ka Hindi batao"))
    assert seen and "hoola_pc_do" not in seen[0]["tools"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.914.0")
