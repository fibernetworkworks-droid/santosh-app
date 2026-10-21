"""v0.91.1 "Hoola clicks randomly on the PC since the realtime update".

Cause: Santosh Desktop turns a click (x, y on the screenshot) into screen pixels with the size of the LAST screenshot it
took. v0.86 started taking live-view frames at 960 px while the model looked at 1280 px screenshots, so on a 1920 px
screen every click after a live frame landed at x*2.0 instead of x*1.5. These tests run the REAL desktop Control code
(screenshot + click arithmetic) under the real server loop."""
import asyncio
import base64
import io
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))


class _Gui:
    def __init__(self):
        self.clicks, self.typed, self.keys = [], [], []
        self.FAILSAFE, self.PAUSE = True, 0

    def click(self, x, y):
        self.clicks.append((x, y))

    def write(self, text, interval=0):
        self.typed.append(text)

    typewrite = write

    def hotkey(self, *k):
        self.keys.append("+".join(k))

    def press(self, k):
        self.keys.append(k)


def _desktop(monkeypatch, width=1920, height=1080):
    from PIL import Image

    from santosh_desktop import control as dc
    gui = _Gui()
    monkeypatch.setattr(dc, "_gui", lambda: gui)
    monkeypatch.setattr(dc, "_dpi_aware", lambda: None)
    import PIL.ImageGrab
    monkeypatch.setattr(PIL.ImageGrab, "grab", lambda all_screens=False: Image.new("RGB", (width, height), (30, 30, 60)))
    ctl = dc.Control()
    monkeypatch.setattr(ctl, "windows", lambda: {"active_window": "Chrome - UIDAI", "windows": ["Chrome - UIDAI"]})
    return ctl, gui


def _wire(monkeypatch, ctl, widths):
    from app.pc import operator

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        args = args or {}
        if action == "screen":
            widths.append(args.get("max_width"))
            return ctl.screen(int(args.get("max_width") or 1280))
        if action == "control":
            a = {k: v for k, v in args.items() if k != "op"}
            if args["op"] == "type":
                return ctl.act("type", text=a.get("text", ""))
            if args["op"] == "key":
                return ctl.act("key", keys=a.get("keys", ""))
            return ctl.act(args["op"], x=a.get("x"), y=a.get("y"))
        return {}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "LIVE_EVERY_S", 0.05)
    monkeypatch.setattr(operator, "SETTLE_S", {})


class _Client:
    """A scripted model that thinks a little (so live frames are taken) and then answers."""

    def __init__(self, turns):
        self.turns, self.n = turns, 0
        self.messages = SimpleNamespace(create=self.create)

    async def create(self, **kw):
        await asyncio.sleep(0.4)
        blocks = self.turns[min(self.n, len(self.turns) - 1)]
        self.n += 1
        return SimpleNamespace(content=blocks)


def _use(i, name, **inp):
    return {"type": "tool_use", "id": f"tu{i}", "name": name, "input": inp}


def test_clicks_land_where_the_model_pointed_even_with_the_live_view_running(env, monkeypatch):
    from app.agent import santosh
    from app.pc import operator
    ctl, gui = _desktop(monkeypatch)
    widths = []
    _wire(monkeypatch, ctl, widths)
    # on the 1280 x 720 screenshot the "Verify & Download" button is at (640, 360) = the middle of the screen
    client = _Client([[_use(1, "click", x=640, y=360)], [_use(2, "click", x=1000, y=600)],
                      [_use(3, "done", answer="ho gaya")]])
    monkeypatch.setattr(santosh, "get_client", lambda: client)
    op = operator.Op(id="pcop_x", tenant="default", conv="c", task="Verify & Download dabao")
    asyncio.run(operator._run(op))
    assert gui.clicks == [(960, 540), (1500, 900)]          # the real middle of a 1920 x 1080 screen, every time
    assert set(widths) == {operator.SHOT_WIDTH}              # one screenshot size for the model AND the live view
    assert op.frame_seq > 3


def test_no_blind_second_click_in_one_turn(env, monkeypatch):
    from app.agent import santosh
    from app.pc import operator
    ctl, gui = _desktop(monkeypatch)
    _wire(monkeypatch, ctl, [])
    # one turn: click the field, type, press enter (fine) ... then click "Next" without having seen the new screen
    client = _Client([[_use(1, "click", x=200, y=100), _use(2, "type", text="Meghana"), _use(3, "key", keys="tab"),
                       _use(4, "click", x=300, y=500), _use(5, "done", answer="ho gaya")],
                      [_use(6, "done", answer="ab sach mein ho gaya")]])
    monkeypatch.setattr(santosh, "get_client", lambda: client)
    op = operator.Op(id="pcop_y", tenant="default", conv="c", task="form bharo")
    asyncio.run(operator._run(op))
    assert gui.clicks == [(300, 150)]                        # the second click was held back
    assert gui.typed == ["Meghana"] and gui.keys == ["tab"]
    assert op.status == "done" and op.summary == "ab sach mein ho gaya"   # "done" only after looking again
    assert operator.STATS["held_blind"] >= 2
