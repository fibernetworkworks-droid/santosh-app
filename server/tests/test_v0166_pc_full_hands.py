"""v0.166 "100% PC tasks": the operator reaches the whole PC — one-step sites in her browser, Store apps / .exe
paths, window management, every monitor stitched, and an old Santosh Desktop gets a clean upgrade note.

Server-side tests run the real operator loop against a FakePC; desktop-side tests run the REAL santosh_desktop
Control code (same style as test_v0911_pc_clicks.py)."""
import asyncio
import base64
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_bazar import _events, _notices, bz  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()


class FakePC:
    def __init__(self, control=True):
        self.calls = []
        self.control = control
        self.old = False            # simulates a desktop older than 1.3.0

    async def __call__(self, op, action, args=None, timeout=40):
        args = dict(args or {})
        self.calls.append((action, args))
        if self.old and action in ("open_url", "window"):
            raise RuntimeError("Unknown action " + action)
        if action == "screen":
            return {"image_b64": JPEG, "width": 1280, "height": 720, "active_window": "Excel - Book1",
                    "windows": ["Excel - Book1"], "monitor": args.get("monitor", "primary")}
        if action == "open_url":
            return {"opened": args["url"]}
        if action == "window":
            return {"window": "TallyPrime 4.1 - Company X", "op": args["op"]}
        return {"ok": True}


def tu(i, tool, **inp):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp})


def txt(t):
    return types.SimpleNamespace(model_dump=lambda exclude_none=True: {"type": "text", "text": t})


class FakeClaude:
    def __init__(self, script):
        self.script = list(script)
        self.seen = []
        self.messages = self

    async def create(self, **kw):
        self.seen.append(kw)
        return types.SimpleNamespace(content=self.script.pop(0))


@pytest.fixture
def op(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    pc = FakePC()
    monkeypatch.setattr(operator, "_pc", pc)

    class Conn:
        info = {"control": True}
    from app.pc.hub import hub
    monkeypatch.setattr(hub, "is_online", lambda t, d=None: True)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    yield operator, pc, bz


def _wire_claude(monkeypatch, claude):
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)


def _tool_results(claude):
    return [b for m in claude.seen[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
            for b in m["content"] if b.get("type") == "tool_result"]


def run(coro):
    return asyncio.run(coro)


# ---------------- server side ----------------

def test_site_opens_in_her_browser_in_one_step(op, monkeypatch):
    """'Chrome mein IRCTC kholo' = open_url, no Chrome-first click dance."""
    operator, pc, bz = op
    claude = FakeClaude([
        [txt("IRCTC khol raha hoon"), tu(1, "open_url", url="https://www.irctc.co.in")],
        [tu(2, "done", answer="IRCTC aapke browser mein khul gaya.", success=True)],
    ])
    _wire_claude(monkeypatch, claude)
    r = run(operator.start("default", bz["conv"], "mere PC pe Chrome mein IRCTC kholo", wait=5))
    assert r["status"] == "done"
    assert ("open_url", {"url": "https://www.irctc.co.in"}) in pc.calls
    assert not any(c[0] == "control" for c in pc.calls)          # no clicks needed


def test_open_url_refuses_non_websites(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "open_url", url="javascript:alert(1)")],
        [tu(2, "open_url", url="file:///C:/Windows/System32/cmd.exe")],
        [tu(3, "done", answer="nahi khol sakta", success=False)],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "yeh kholo", wait=5))
    assert not any(c[0] == "open_url" for c in pc.calls)         # nothing reached the PC
    assert any("REFUSED" in str(b["content"]) for b in _tool_results(claude))


def test_window_management_reaches_the_desktop(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "window", op="minimize", title="TallyPrime")],
        [tu(2, "window", op="close", title="Notepad")],
        [tu(3, "done", answer="ho gaya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "Tally minimize karo", wait=5))
    assert ("window", {"op": "minimize", "title": "TallyPrime"}) in pc.calls
    assert ("window", {"op": "close", "title": "Notepad"}) in pc.calls
    bad = [a for a, k in pc.calls if a == "window" and k.get("op") not in
           ("minimize", "maximize", "restore", "close")]
    assert not bad


def test_monitor_switch_holds_blind_clicks_and_marks_the_screen(op, monkeypatch):
    """screenshot monitor=all: the picture reaches the model as the tool result, and a click in the SAME turn is held."""
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "screenshot", monitor="all"), tu(2, "click", x=640, y=360)],
        [tu(3, "click", x=640, y=360), tu(4, "done", answer="almost")],   # done after a click is held too (v0.91.1)
        [tu(5, "done", answer="dusra screen dekh liya")],
    ])
    _wire_claude(monkeypatch, claude)
    r = run(operator.start("default", bz["conv"], "doosri screen par dekho", wait=5))
    # the screenshot really asked for all monitors, on both the tool shot and the live frames
    assert any(a == "screen" and k.get("monitor") == "all" for a, k in pc.calls)
    # the same-turn click was NOT sent; after looking, the next turn's click ran exactly once
    clicks = [c for a, c in pc.calls if a == "control" and c.get("op") == "click"]
    assert len(clicks) == 1
    assert operator.STATS["held_blind"] >= 2      # the guarded click AND the guarded done
    assert r["status"] == "done"


def test_old_desktop_gets_a_clean_upgrade_note(op, monkeypatch):
    operator, pc, bz = op
    pc.old = True
    claude = FakeClaude([
        [tu(1, "open_url", url="https://example.com")],
        [tu(2, "done", answer="Desktop update kijiye", success=False)],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "site kholo", wait=5))
    assert any("SantoshDesktop.exe install kijiye" in str(b["content"]) for b in _tool_results(claude))


def test_prompt_promises_the_whole_pc(op):
    operator, _pc, _bz = op
    for word in ("open_url", "monitor", "window", "Store apps", ".exe"):
        assert word in operator.SYSTEM


def test_tools_schema_carries_the_new_actions(op):
    operator, _pc, _bz = op
    names = {t["name"] for t in operator.TOOLS}
    assert {"open_url", "screenshot", "window"} <= names


# ---------------- desktop side (real Control code) ----------------

class _Gui:
    def __init__(self):
        self.clicks, self.typed, self.keys, self.started = [], [], [], []

    def click(self, x, y):
        self.clicks.append((x, y))

    def write(self, text, interval=0):
        self.typed.append(text)

    typewrite = write

    def hotkey(self, *k):
        self.keys.append("+".join(k))

    def press(self, k):
        self.keys.append(k)


def test_desktop_clicks_map_across_monitors(monkeypatch):
    """A click on the stitched two-monitor picture lands on the LEFT monitor (negative origin)."""
    from PIL import Image

    from santosh_desktop import control as dc
    gui = _Gui()
    monkeypatch.setattr(dc, "_gui", lambda: gui)
    monkeypatch.setattr(dc, "_dpi_aware", lambda: None)
    monkeypatch.setattr(dc, "_virtual_screen", lambda: (-1920, 0, 3840, 1080))
    import PIL.ImageGrab
    monkeypatch.setattr(PIL.ImageGrab, "grab",
                        lambda all_screens=False, bbox=None: Image.new("RGB", (3840, 1080) if bbox else (1920, 1080),
                                                                       (30, 30, 60)))
    ctl = dc.Control()
    monkeypatch.setattr(ctl, "windows", lambda: {"active_window": "x", "windows": ["x"]})
    s = ctl.screen(1280, monitor="all")
    assert s["monitor"] == "all" and s["origin"] == [-1920, 0]
    ctl.act("click", 320, 180)        # middle of the LEFT monitor on the stitched 1280x360 shot
    assert gui.clicks == [(-1920 + 320 * 3, 180 * 3)]


def test_desktop_types_long_text_via_clipboard_and_restores_it(monkeypatch):
    from santosh_desktop import control as dc
    gui = _Gui()
    monkeypatch.setattr(dc, "_gui", lambda: gui)
    fake_clip = types.SimpleNamespace(_v="user ka purana text",
                                      paste=lambda: fake_clip._v,
                                      copy=lambda v: setattr(fake_clip, "_v", v))
    monkeypatch.setitem(sys.modules, "pyperclip", fake_clip)
    ctl = dc.Control()
    ctl.act("type", text="Is mahine ke GST return ki details poore type karo" * 1)
    assert gui.keys == ["ctrl+v"] and gui.typed == []          # pasted, not key-by-key
    assert fake_clip._v == "user ka purana text"               # her clipboard is back
    # short plain text (OTP-style) still types key by key: no clipboard touch
    fake_clip._v = "user ka purana text"
    ctl.act("type", text="123456")
    assert gui.typed == ["123456"] and fake_clip._v == "user ka purana text"


def test_desktop_open_url_validates_the_scheme(monkeypatch):
    from santosh_desktop import control as dc
    opened = []
    monkeypatch.setattr(sys, "platform", "win32")          # the sandbox is Linux; the launch path is the same shape
    monkeypatch.setattr(dc.os, "startfile", opened.append, raising=False)
    ctl = dc.Control()
    ctl.open_url("irctc.co.in")                     # no scheme -> https
    assert opened == ["https://irctc.co.in"]
    with pytest.raises(dc.ControlError):
        ctl.open_url("javascript:alert(1)")
    with pytest.raises(dc.ControlError):
        ctl.open_url("file:///C:/Windows/System32/cmd.exe")
    with pytest.raises(dc.ControlError):
        ctl.open_url("C:\\Windows\\System32\\cmd.exe")
    assert len(opened) == 1


def test_desktop_window_op_closes_restores_minimizes(monkeypatch):
    from santosh_desktop import control as dc
    wins = [SimpleNamespace(title="TallyPrime 4.1 - X", minimize=lambda: None, maximize=lambda: None,
                            restore=lambda: None, close=lambda: None)]
    calls = []
    for n in ("minimize", "maximize", "restore", "close"):
        setattr(wins[0], n, (lambda n: lambda: calls.append(n))(n))
    fake_gw = types.SimpleNamespace(getAllWindows=lambda: wins)
    monkeypatch.setitem(sys.modules, "pygetwindow", fake_gw)
    ctl = dc.Control()
    assert ctl.window_op("minimize", "tally")["op"] == "minimize"
    assert ctl.window_op("restore", "TallyPrime")["op"] == "restore"
    assert calls == ["minimize", "restore"]
    with pytest.raises(dc.ControlError):
        ctl.window_op("kill", "Tally")
    with pytest.raises(dc.ControlError):
        ctl.window_op("close", "koi nahi hai")


def test_desktop_refuses_blocked_app_names_even_by_path():
    from santosh_desktop import control as dc
    ctl = dc.Control()
    with pytest.raises(dc.ControlError):
        ctl.open_app("powershell")
    with pytest.raises(dc.ControlError):
        ctl.open_app("C:\\Windows\\System32\\regedit.exe")
