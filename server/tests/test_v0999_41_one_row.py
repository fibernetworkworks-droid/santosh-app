"""v0.999.41 ONE ROW WHILE IT BUILDS (owner, on the build page screenshots: "Too many rows above the page while it builds:
the panel header, the LIVE row, the page tabs, then a browser bar. -- FIX THIS"): while the website is written the panel
has ONE header row - the title, the LIVE tag with what is being written and a clock, a page picker (a menu, not a row of
tabs), the device switch, Follow and Code as icons, close - and the page sits right under it. No LIVE row, no row of page
tabs, no browser bar, no second Pause (the chat's working row has it)."""
from __future__ import annotations

import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v0664_asli_samay import _slow_fake
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ST = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.70"


def test_one_row_in_the_code():
    js, css = (ST / "webstudio.js").read_text(), (ST / "webstudio.css").read_text()
    live = js[js.index("function liveView(pane, v)"):js.index("function drawLiveBits()")]
    assert 'class="lbar"' not in live and 'class="lpages"' not in live and "bwin" not in live and "bchrome" not in live
    assert "viewsBar(tools, true)" in live and 'id="wsLBar"' in live and 'id="wsLPages"' in live and 'role="menu"' in live
    bits = js[js.index("function drawLiveBits()"):js.index("function compareView(")]
    assert 'data-act="stop"' not in bits and "Pause" not in bits                  # Pause lives in the chat's working row
    assert "act === 'lpages'" in js and "opts.live" in js
    block = css.split("v0.999.41 ONE ROW WHILE IT BUILDS", 1)[1].split("HOOLA CHAT KIT in the Web Studio", 1)[0]
    for m in (".lstat{", ".lpmenu{", ".lpmenu[hidden]{display:none}", "@container wpane", "prefers-reduced-motion"):
        assert m in block, m
    assert "font-weight:700" not in block and "font-weight:800" not in block


def _shot(page, name):
    d = os.environ.get("HOOLA_SHOTS")
    if d:
        page.screenshot(path=str(Path(d) / name))


def _rows_above(page):
    """Everything in the panel that sits above the live page: its tops + heights."""
    return page.evaluate("""() => {
      const pane = document.querySelector('#wsPane'), fr = pane.querySelector('iframe[data-live]');
      const top = fr.getBoundingClientRect().top, p = pane.getBoundingClientRect().top;
      const head = pane.querySelector('.ptop').getBoundingClientRect();
      return {gap: top - head.bottom, head: head.height, above: top - p,
              pane_w: pane.clientWidth, pane_sw: pane.scrollWidth, head_sw: pane.querySelector('.ptop').scrollWidth,
              head_cw: pane.querySelector('.ptop').clientWidth};
    }""")


def test_one_row_in_a_browser(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "false")
    monkeypatch.setenv("SITE_PARALLEL", "2")
    monkeypatch.setenv("SITE_WORKER", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots")))
    _slow_fake(monkeypatch, per=0.25, n=14)
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/console/web")
    page.wait_for_selector("#wsAsk", timeout=20000)
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    page.wait_for_selector("#ws .lks button", timeout=120000)
    page.click("#ws [data-act='pick-look']")
    page.wait_for_selector("#ws .phd.lv .lstat .livetag", timeout=30000)
    page.wait_for_selector("#wsPane iframe[data-live][data-look='-1']", timeout=30000)
    # one header row, the page right under it
    pane = page.locator("#wsPane")
    assert pane.locator(".ptop").count() == 1
    assert pane.locator(".lbar, .lpages, .bwin, .bchrome, #wsLUrl").count() == 0
    assert pane.locator("[data-act='stop']").count() == 0                       # no second Pause in the panel
    m = _rows_above(page)
    assert m["head"] <= 52 and m["gap"] <= 24 and m["above"] <= 80, m
    assert m["head_sw"] <= m["head_cw"] + 1, m                                   # the header never spills
    page.wait_for_timeout(600)
    _shot(page, "1-building.png")
    # the page picker is a menu, not a row of tabs
    menu = page.locator("#wsLPages")
    assert menu.is_hidden() and menu.locator("button").count() >= 3
    page.click("#ws [data-act='lpages']")
    assert menu.is_visible()
    _shot(page, "2-pages-menu.png")
    second = menu.locator("button").nth(1)
    slug = second.get_attribute("data-lpage")
    second.click()
    assert menu.is_hidden()
    assert page.get_attribute("#wsPane iframe[data-live]", "data-page") == slug
    assert page.get_attribute("#ws [data-live='follow']", "aria-pressed") == "false"
    page.click("#ws [data-act='lpages']")
    page.keyboard.press("Escape")
    assert menu.is_hidden()
    # a phone: still one row, nothing cut sideways
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(300)
    if page.locator("#wsPane iframe[data-live]").count():
        m = _rows_above(page)
        assert m["head"] <= 52 and m["head_sw"] <= m["head_cw"] + 1 and m["pane_sw"] <= m["pane_w"] + 1, m
        page.locator("#wsPane").scroll_into_view_if_needed()
        _shot(page, "3-phone.png")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.wait_for_selector("#ws #wsPane .url", timeout=180000)                  # built: the normal preview
    _shot(page, "4-ready.png")
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
