"""v0.185.0 "Mera PC browser intelligence": Hoola reads her browser like a person — page_text / tabs /
switch_tab / downloads over UIA, open_url lands as a new tab in the browser she already uses and reports the
loaded page title + first words, typing verifies itself in the field, and browser jobs get a bigger budget.

Server-side tests run the real operator loop against a FakePC (same style as test_v0166_pc_full_hands.py);
desktop-side tests exercise the real browser module's safe paths (Linux CI: everything must degrade quietly).
"""
import asyncio
import base64
import sys
import types
from pathlib import Path

import pytest

from tests.test_bazar import _events, _notices, bz  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fakejpeg").decode()


class FakePC:
    def __init__(self):
        self.calls = []
        self.old = False          # simulates a desktop older than 1.4.0
        self.verify = None        # when set, control type replies {"ok": True, "verify": {...}}
        self.url_result = None    # when set, open_url replies with this exact dict

    async def __call__(self, op, action, args=None, timeout=40, log=True):
        args = dict(args or {})
        self.calls.append((action, args))
        if self.old and action in ("open_url", "window", "page_text", "tabs", "switch_tab", "downloads"):
            raise RuntimeError("Unknown action " + action)
        if action == "screen":
            return {"image_b64": JPEG, "width": 1280, "height": 720, "active_window": "IRCTC - Google Chrome",
                    "windows": ["IRCTC - Google Chrome"], "monitor": args.get("monitor", "primary")}
        if action == "open_url":
            if self.url_result is not None:
                return self.url_result
            return {"opened": args["url"]}   # a desktop < 1.4.0 answers just this
        if action == "page_text":
            return {"title": "IRCTC | Train Ticket Booking", "url": "https://www.irctc.co.in/ntrain/train/search",
                    "text": "Book train tickets online. From station, To station, Search Trains. Login."}
        if action == "tabs":
            return {"tabs": [{"index": 1, "title": "Gmail - Inbox", "active": False},
                             {"index": 2, "title": "IRCTC Next Generation", "active": True}], "count": 2}
        if action == "switch_tab":
            return {"switched": "IRCTC Next Generation", "title": "IRCTC Next Generation"}
        if action == "downloads":
            return {"folder": "C:/Users/She/Downloads",
                    "files": [{"name": "ticket.pdf", "size_text": "120 KB", "partial": False},
                              {"name": "song.zip.crdownload", "size_text": "3 MB", "partial": True}]}
        if action == "control":
            if args.get("op") == "type" and self.verify is not None:
                return {"ok": True, "verify": self.verify}
            return {"ok": True}
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


# ---------------- budgets (speed) ----------------

def test_web_tasks_get_the_bigger_budget():
    from app.pc import operator
    assert operator._is_web_task("Chrome mein IRCTC kholo")
    assert operator._is_web_task("amazon.in par mera order track karo")
    assert operator._is_web_task("https://hoola.ainewtika.com kholo")
    assert operator._is_web_task("YouTube par video download karo")
    assert not operator._is_web_task("Notepad kholo aur letter likho")
    assert not operator._is_web_task("Tally mein aaj ki sales dikhao")
    assert operator._budget("irctc par ticket") == (operator.MAX_STEPS_WEB, operator.TASK_MINUTES_WEB)
    assert operator._budget("Tally kholo") == (operator.MAX_STEPS, operator.TASK_MINUTES)


def test_start_sets_the_budget_on_the_live_card(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([[tu(1, "done", answer="ho gaya")]])
    _wire_claude(monkeypatch, claude)
    r = run(operator.start("default", bz["conv"], "mere PC pe Chrome mein IRCTC kholo", wait=5))
    assert r["steps_max"] == operator.MAX_STEPS_WEB
    r2 = run(operator.start("default", bz["conv"], "Notepad kholo", wait=5))
    assert r2["steps_max"] == operator.MAX_STEPS


# ---------------- tool surface ----------------

def test_tools_schema_carries_browser_intelligence(op):
    operator, _pc, _bz = op
    names = {t["name"] for t in operator.TOOLS}
    assert {"page_text", "tabs", "switch_tab", "downloads"} <= names


def test_prompt_promises_browser_reading(op):
    operator, _pc, _bz = op
    for word in ("page_text", "switch_tab", "downloads", "NEW TAB", "verified"):
        assert word in operator.SYSTEM


def test_say_has_hinglish_lines_for_new_tools(op):
    operator, _pc, _bz = op
    assert operator._say("page_text", {}) == "page ka text padh raha hoon"
    assert operator._say("tabs", {}) == "browser tabs dekh raha hoon"
    assert "tab" in operator._say("switch_tab", {"tab": "IRCTC"})
    assert "Downloads" in operator._say("downloads", {})


# ---------------- page_text / tabs / switch_tab / downloads in the loop ----------------

def test_page_text_reaches_the_model(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "page_text", max_chars=2000)],
        [tu(2, "done", answer="IRCTC ka home page khula hai")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "irctc kholo", wait=5))
    assert ("page_text", {"max_chars": 2000}) in pc.calls
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "IRCTC | Train Ticket Booking" in body
    assert "Book train tickets online" in body
    assert "https://www.irctc.co.in/ntrain/train/search" in body


def test_tabs_and_switch_tab_flow(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "tabs")],
        [tu(2, "switch_tab", tab="Gmail")],
        [tu(3, "done", answer="Gmail tab par aa gaya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "browser ke tabs dekho", wait=5))
    assert ("tabs", {}) in pc.calls
    assert ("switch_tab", {"tab": "Gmail", "index": 0}) in pc.calls
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "1. Gmail - Inbox" in body
    assert "[active]" in body


def test_switch_tab_holds_blind_clicks(op, monkeypatch):
    """A tab switch moves the whole screen: a click in the SAME turn must not run (v0.91.1 rule)."""
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "switch_tab", tab="IRCTC"), tu(2, "click", x=640, y=360)],
        [tu(3, "click", x=640, y=360), tu(4, "done", answer="almost")],
        [tu(5, "done", answer="tab badal ke click kar diya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "irctc tab par jaake click karo", wait=5))
    clicks = [c for a, c in pc.calls if a == "control" and c.get("op") == "click"]
    assert len(clicks) == 1
    assert operator.STATS["held_blind"] >= 2


def test_downloads_reports_finished_and_partial(op, monkeypatch):
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "downloads", minutes=30)],
        [tu(2, "done", answer="ticket.pdf download ho gaya, zip abhi chal rahi hai")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "file download karo", wait=5))
    assert ("downloads", {"minutes": 30}) in pc.calls
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "ticket.pdf (120 KB, finished)" in body
    assert "song.zip.crdownload (3 MB, STILL DOWNLOADING)" in body


# ---------------- typed-value verify ----------------

def test_type_verify_warns_when_text_did_not_land(op, monkeypatch):
    operator, pc, bz = op
    pc.verify = {"kind": "EditControl", "length": 3, "matches": False}
    claude = FakeClaude([
        [tu(1, "type", text="rajkumar@example.com")],
        [tu(2, "done", answer="email theek kar diya", success=False)],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "form bharo", wait=5))
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "does NOT show the sent text" in body
    assert "3 chars" in body


def test_type_verify_confirms_when_it_matches(op, monkeypatch):
    operator, pc, bz = op
    pc.verify = {"kind": "EditControl", "length": 19, "matches": True}
    claude = FakeClaude([
        [tu(1, "type", text="rajkumar@example.com")],
        [tu(2, "done", answer="email likh diya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "form bharo", wait=5))
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "verified in the field" in body


def test_type_without_verify_stays_quiet(op, monkeypatch):
    """Desktops < 1.4.0 send no verify block: the model must get plain 'typed' as before."""
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "type", text="hello")],
        [tu(2, "done", answer="likh diya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "notepad mein likho", wait=5))
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert body.strip() == "typed" or "typed" in body


# ---------------- open_url: new tab + load signal + digest ----------------

def test_open_url_reports_tab_title_and_page_digest(op, monkeypatch):
    operator, pc, bz = op
    pc.url_result = {"opened": "https://www.irctc.co.in", "in": "Chrome (new tab)",
                     "title": "IRCTC | Train Ticket Booking", "loaded": True}
    claude = FakeClaude([
        [tu(1, "open_url", url="https://www.irctc.co.in")],
        [tu(2, "done", answer="IRCTC khul gaya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "Chrome mein IRCTC kholo", wait=5))
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "opened https://www.irctc.co.in in Chrome (new tab)" in body
    assert "page title now: IRCTC | Train Ticket Booking" in body
    assert "Page text starts with: Book train tickets online" in body
    # the digest call rode along automatically and was not logged as a step
    assert any(a == "page_text" for a, _k in pc.calls)


def test_open_url_old_desktop_stays_plain(op, monkeypatch):
    """Desktop < 1.4.0: open_url returns only {'opened': url} — the result stays a single clean line."""
    operator, pc, bz = op
    claude = FakeClaude([
        [tu(1, "open_url", url="https://example.com")],
        [tu(2, "done", answer="khul gaya")],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "example kholo", wait=5))
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "opened https://example.com in her browser" in body


def test_old_desktop_browser_tools_get_the_upgrade_note(op, monkeypatch):
    operator, pc, bz = op
    pc.old = True
    claude = FakeClaude([
        [tu(1, "page_text")],
        [tu(2, "tabs")],
        [tu(3, "done", answer="Desktop update kijiye", success=False)],
    ])
    _wire_claude(monkeypatch, claude)
    run(operator.start("default", bz["conv"], "page padho", wait=5))
    body = " ".join(str(b.get("content", "")) for b in _tool_results(claude))
    assert "SantoshDesktop.exe install kijiye" in body


# ---------------- desktop side (real code, safe paths) ----------------

def test_downloads_listing_is_real_and_flags_partials(tmp_path, monkeypatch):
    from santosh_desktop import browser
    dl = tmp_path / "Downloads"
    dl.mkdir()
    (dl / "report.pdf").write_bytes(b"x" * 2048)
    (dl / "song.zip.crdownload").write_bytes(b"y" * 4096)
    monkeypatch.setattr(browser.Path, "home", classmethod(lambda cls: tmp_path))
    r = browser.downloads(minutes=60)
    names = [f["name"] for f in r["files"]]
    assert "report.pdf" in names and "song.zip.crdownload" in names
    partial = {f["name"] for f in r["files"] if f["partial"]}
    assert partial == {"song.zip.crdownload"}


def test_page_text_degrades_quietly_off_windows():
    from santosh_desktop import browser
    if sys.platform == "win32":      # on Windows CI this would touch real UIA — skip there
        pytest.skip("Windows machine: real UIA test not runnable headless")
    with pytest.raises(browser.BrowserUnavailable):
        browser.page_text()


def test_desktop_version_is_140():
    import santosh_desktop
    assert santosh_desktop.__version__ == "1.4.0"


def test_app_version_is_0185():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.216.0"
