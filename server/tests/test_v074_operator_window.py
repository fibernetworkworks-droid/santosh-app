"""v0.74 The Computer Operator is a real browser window (Google Chrome when installed) on a virtual screen, so sites
don't see "HeadlessChrome" (which many Indian portals refuse). Nothing is faked: navigator.webdriver stays true."""
import asyncio
import shutil

import pytest

from app.operator import display


def test_launch_options_choices(monkeypatch):
    monkeypatch.setattr(display, "chrome_installed", lambda: True)
    monkeypatch.setattr(display, "virtual_display", lambda: ":99")
    o, what = display.launch_options(False, "auto")
    assert o["channel"] == "chrome" and o["headless"] is False and o["env"]["DISPLAY"] == ":99" and "Chrome" in what
    o, _ = display.launch_options(False, "chromium")
    assert "channel" not in o
    monkeypatch.setattr(display, "virtual_display", lambda: "")
    o, what = display.launch_options(False, "auto")
    assert o["headless"] is True and "xvfb" in what.lower()          # no screen possible -> old headless, said plainly
    o, _ = display.launch_options(True, "auto", "/x/chrome")
    assert o["executable_path"] == "/x/chrome" and o["headless"] is True


@pytest.mark.skipif(not shutil.which("Xvfb"), reason="needs Xvfb")
def test_real_window_is_not_headless_and_not_hidden():
    from playwright.async_api import async_playwright

    async def go():
        o, _ = display.launch_options(False, "auto")
        async with async_playwright() as pw:
            b = await pw.chromium.launch(**o)
            p = await b.new_page()
            ua, wd = await p.evaluate("[navigator.userAgent, navigator.webdriver]")
            await b.close()
        return ua, wd
    ua, wd = asyncio.run(go())
    assert "HeadlessChrome" not in ua and wd is True


def test_v0881_stale_virtual_screens_do_not_block(tmp_path):
    """v0.88.1: after many server restarts every :99-:119 lock was taken by dead / orphaned Xvfb and the operator fell
    back to headless (sites block it). A dead lock is cleared, a running Xvfb is shared."""
    import os
    from app.operator import display as D
    lock = tmp_path / "lock"
    lock.write_text("      999999\n")
    assert D._lock_pid(lock) == 999999 and not D._alive(999999)
    assert D._alive(os.getpid()) and not D._is_xvfb(os.getpid())
    (tmp_path / "bad").write_text("x")
    assert D._lock_pid(tmp_path / "bad") == 0
