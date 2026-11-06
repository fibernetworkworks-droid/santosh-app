"""v0.635 WEB DEVELOPMENT PANEL: the owner-approved prototype ("PERFECT") made real in the web console - a sidebar row,
a home (ask box, four ways to start, her websites, business types) and nine tabs per site. Build / Edit / Code / Data
open the EXISTING Website studio (build.js `openSite`), going live / rollback / take down / old-address redirects are her
taps with the server's hash, new work starts as her words in chat. Then the page in a real browser (Playwright, skipped
without Chromium): every tab draws, the studio opens beside it, light + dark, phone width with no sideways scroll, no
script errors, server text never becomes HTML. Screenshots: CONSOLE_SHOTS=<folder>."""
import os
import re
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.644.0"


def test_console_wiring():
    html = (CONSOLE / "v2.html").read_text()
    js = (CONSOLE / "v2.js").read_text()
    wd = (CONSOLE / "webdev.js").read_text()
    build = (CONSOLE / "build.js").read_text()
    css = (CONSOLE / "v2.css").read_text()
    assert 'id="v-webdev"' in html and re.search(r'/static/console/webdev\.js\?v=[\d.]+"', html)
    assert "['webdev','Web Development']" in js and "HoolaWebDev(" in js and "B?.openSite?.(" in js
    assert "if (v === 'webdev') WD?.open(" in js
    assert "async openSite(p, tab, editMode)" in build and "upsert('site_board', p)" in build
    for tab in ("overview", "build", "edit", "code", "data", "integrations", "publish", "health", "settings"):
        assert f"['{tab}'," in wd
    # her taps: every live / rollback / takedown / redirect write asks first and carries the server's hash
    for act in ("golive", "rollback", "takedown"):
        blk = wd.split(f"act === '{act}'", 1)[1][:400]
        assert "confirm(" in blk
    assert "{hash: d.hash}" in wd and "hash: S(card.hash)" in wd and "{hash: f.dataset.hash, drop}" in wd
    # a payment, a domain purchase, a new site start as her words in chat (the agent's cards and rules apply)
    assert "online payment jodo" in wd and "domain dhoondho" in wd and "say(t)" in wd
    assert "esc(" in wd and wd.count("esc(") > 60                                        # server text drawn through esc()
    blk = css.split("v0.635 WEB DEVELOPMENT PANEL", 1)[1]
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", blk)                                  # theme tokens only, no raw colours


def _ready_site():
    """A built site as the panel sees it (the real build runs Chromium itself, which cannot nest in this browser test)."""
    from app.db import session
    from app.site import service as S
    from app.site.models import Site
    v = S.new(T, "Sharma Sweets mithai dukaan ki website <b>Akola</b>", name="Sharma <i>Sweets</i>",
              answers={"phone": "9876543210", "address": "Main Road, Akola"})
    with session() as s:
        r = s.get(Site, v["id"])
        r.status, r.version, r.stage = "ready", 1, "done"
    return S.get(T, v["id"])


def test_panel_in_a_real_browser(arena_server):
    base, browser, key = arena_server
    g = _ready_site()
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/console/")
        page.wait_for_selector('#snav [data-v="webdev"]', timeout=20000)
        page.click('#snav [data-v="webdev"]')
        page.wait_for_selector("#webdev .wd-site", timeout=20000)
        home = page.inner_text("#webdev")
        assert "What should we build today?" in home and "Move my old site" in home and "Sweet shop" in home
        assert page.locator("#webdev .wd-site").count() == 1
        assert "Sharma <i>Sweets</i>" in page.inner_text("#webdev .wd-site")             # her name is text, never markup
        page.click("#webdev [data-wd-type='Clinic']")
        assert "Clinic" in page.input_value("#wdAsk")
        if shots:
            page.screenshot(path=f"{shots}/webdev-home-{scheme}.png")
        page.click("#webdev .wd-site")
        page.wait_for_selector("#webdev .wd-tabs", timeout=10000)
        assert page.locator("#webdev .wd-tabs button").count() == 9
        assert page.locator("#webdev .wd-tabs [aria-current=page]").inner_text() == "Overview"
        for tab, needle in (("build", "Live preview and build board"), ("edit", "Visual edit"), ("code", "real code"),
                            ("data", "Lists on this site"), ("integrations", "Shop and cart"), ("publish", "Connect your domain"),
                            ("health", "Speed on real phones"), ("settings", "Business details")):
            page.click(f"#webdev .wd-tabs [data-wd-tab='{tab}']")
            page.locator("#wdBody", has_text=needle).wait_for(timeout=15000)
            if shots:
                page.screenshot(path=f"{shots}/webdev-{tab}-{scheme}.png", full_page=True)
        # settings: her phone number is in the form, and a save goes to the answers route
        assert page.input_value("#webdev input[name=phone]") == "9876543210"
        # build tab -> the existing Website studio opens beside the panel
        page.click("#webdev .wd-tabs [data-wd-tab='build']")
        page.wait_for_selector("#webdev [data-wd-studio='preview']")
        page.click("#webdev [data-wd-studio='preview']")
        page.wait_for_selector("#app.st", timeout=10000)
        assert "Website studio" in page.inner_text("#studio")
        if shots:
            page.screenshot(path=f"{shots}/webdev-studio-{scheme}.png")
        page.click("#studio [data-ba=close]")
        # publish: the launch check asks the server and shows its card (nothing goes live here)
        page.click("#webdev .wd-tabs [data-wd-tab='publish']")
        page.wait_for_selector("#webdev [data-wd-act='launch']", timeout=10000)
        page.click("#webdev [data-wd-act='launch']")
        page.wait_for_selector("#wdLaunch .wd-launch, #wdLaunch .wd-li", timeout=15000)
        page.click("#webdev [data-wd-act='home']")
        page.wait_for_selector("#webdev .wd-site")
        ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/console/")
    page.wait_for_selector('#snav [data-v="webdev"]', state="attached", timeout=20000)
    page.evaluate("document.querySelector('#snav [data-v=\"webdev\"]').click()")
    page.wait_for_selector("#webdev .wd-site")
    assert page.evaluate("document.querySelector('#webdev').scrollWidth <= document.querySelector('#webdev').clientWidth + 1")
    page.click("#webdev .wd-site")
    page.wait_for_selector("#webdev .wd-tabs")
    assert page.evaluate("document.querySelector('#webdev').scrollWidth <= document.querySelector('#webdev').clientWidth + 1")
    if shots:
        page.screenshot(path=f"{shots}/webdev-phone.png", full_page=True)
    ctx.close()
    assert not errors, errors
