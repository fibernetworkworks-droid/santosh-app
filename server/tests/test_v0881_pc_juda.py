"""v0.881 PC JUDA HAI: 'connect to my PC' alone is answered from the hub's state at once - no brain turn, no PC job."""
import asyncio
import types

import pytest

from app import pcconnect


@pytest.mark.parametrize("t", [
    "मेरे पीसी से कनेक्ट करो।", "ओके। अभी मेरे पीसी को कनेक्ट करो।", "Santosh, mera PC ka connection connected hai kya check kijiye ek baar.",
    "connect to my pc", "mera computer connect karo", "laptop se jod do", "PC connected hai kya?",
])
def test_only_connect_yes(t):
    assert pcconnect.only_connect(t), t


@pytest.mark.parametrize("t", [
    "मेरे पीसी से कनेक्ट करो, उसमें Amazon ओपन करो।", "pc connect karo aur chrome kholo", "connect karo",
    "mera pc slow hai", "linkedin kholo pc par", "jodhpur ka mausam", "connect to wifi", "",
])
def test_only_connect_no(t):
    assert not pcconnect.only_connect(t), t


class _Hub:
    def __init__(self, devs):
        self.devs = devs

    def devices(self, tenant):
        return self.devs


def _with(monkeypatch, devs, busy=None):
    from app.pc import hub as H, operator as O
    monkeypatch.setattr(H, "hub", _Hub(devs))
    monkeypatch.setattr(O, "busy", lambda t, d: busy)


def test_status_lines(monkeypatch):
    _with(monkeypatch, [])
    assert "juda nahi" in pcconnect.status_line("t")
    pc = {"device_id": "d1", "name": "FNW-FLOW", "kind": "her_pc", "control": True, "paused": False}
    _with(monkeypatch, [pc])
    assert "FNW-FLOW juda hua hai" in pcconnect.status_line("t")
    _with(monkeypatch, [{**pc, "control": False}])
    assert "control band" in pcconnect.status_line("t")
    _with(monkeypatch, [{**pc, "paused": True}])
    assert "pause" in pcconnect.status_line("t")
    _with(monkeypatch, [pc], busy=types.SimpleNamespace(task="Amazon kholo"))
    assert "Amazon kholo" in pcconnect.status_line("t")
    _with(monkeypatch, [{**pc, "kind": "hoola_pc"}])               # Hoola's own PC never counts as hers
    assert "juda nahi" in pcconnect.status_line("t")


def test_call_answers_without_the_brain(monkeypatch):
    from app import voice
    pc = {"device_id": "d1", "name": "FNW-FLOW", "kind": "her_pc", "control": True, "paused": False}
    _with(monkeypatch, [pc])
    call = types.SimpleNamespace(tenant="t", call_id="c1", stats={})
    line = voice.Call._pc_connect_answer(call, "मेरे पीसी से कनेक्ट करो")
    assert "FNW-FLOW" in line and call.stats["pc_connect_fast"] == 1
    assert voice.Call._pc_connect_answer(call, "pc connect karo aur amazon kholo") == ""
    import inspect
    src = inspect.getsource(voice.Call)
    assert "_pc_connect_answer(self, said or req)" in src and "_pc_connect_answer(self, t)" in src


def test_manager_rule_and_switch():
    from app.agent import pc_manager
    from app.config import Settings
    assert "NOT a job" in pc_manager.RULES and "pc_devices" in pc_manager.RULES
    assert Settings.model_fields["voice_pc_connect_fast"].default is True


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.881.0")
