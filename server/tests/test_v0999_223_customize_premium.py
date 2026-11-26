"""v0.999.223 CUSTOMIZE, PREMIUM (owner: "MAKE IT MORE PREMIUN, ADVANCE" -> design claude.ai/artifact/ENS4Mk3mkFsgEJaA8hxSD2
-> "GO BUILD"): the Customize page = header, account card with Credits / Google apps / Memories, a page list, one card per
part; Appearance with a live chat preview; password with show / strength; memory search, pin and a two-tap forget."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (CON / "v2.js").read_text(encoding="utf-8")
CSS = (CON / "v2.css").read_text(encoding="utf-8")


def test_shape():
    body = JS[JS.index("async function drawMain()"):]
    body = body[:body.index("\n}\n")]
    for k in ('cz-me"', "czCred", "czGapps", "czMemN", 'id="signin"', 'id="connections"', 'id="memory"', 'id="about"',
              'id="pwStr"', "cz-eye", 'id="czMemQ"', 'id="logoutBtn"', 'id="gAppsBtn"', "'/api/credits'", "'/api/google'"):
        assert k in body, k
    app = JS[JS.index("function appearanceHTML()"):]
    app = app[:app.index("\n}\n")]
    for k in ('data-theme-set', 'data-size-set="sm"', 'data-font-set', 'id="calmSw"', 'id="glowSw"', "cz-pv", "czReset"):
        assert k in app, k
    assert "'DELETE', '/api/memory/' + id" in JS and "'PATCH', '/api/memory/' + id, {pinned:" in JS
    assert "Forget this everywhere?" in JS                         # forgetting asks once more on the row
    blk = CSS[CSS.index("v0.999.223 CUSTOMIZE, PREMIUM"):]
    assert "var(--fchat,var(--fr))" in blk and "var(--fs,15px)" in blk   # the preview uses the real chat font + size


def test_walk(arena_server):  # noqa: F811
    base, browser, key = arena_server
    errors = []
    for w in (1440, 390):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))

        def config(route):
            r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.route("**/api/memory", lambda r: r.fulfill(json={"facts": [
            {"id": 1, "text": "Our shop opens at 9 am.", "pinned": True, "auto": False, "created_at": "2026-11-20T10:00:00+00:00"},
            {"id": 2, "text": "Send invoices to accounts first.", "pinned": False, "auto": True, "created_at": "2026-11-01T10:00:00+00:00"}]}))
        pg.goto(base + "/console/")
        pg.wait_for_selector("html.appd #snav .sn")
        pg.click("#model"); pg.wait_for_timeout(300)
        pg.locator("[role=menuitem]", has_text="Customize").first.click()
        pg.wait_for_selector("#mainp .cz-me")
        pg.set_viewport_size({"width": w, "height": 900}); pg.wait_for_timeout(200)
        pg.wait_for_selector("#mfacts .cz-fact")
        assert pg.locator("#mfacts .cz-fact").count() == 2
        assert pg.locator("#czMemN").inner_text() == "2"
        pg.fill("#czMemQ", "invoices"); assert pg.locator("#mfacts .cz-fact").count() == 1
        pg.fill("#czMemQ", "")
        pg.locator("#mfacts [data-fid='2'] [data-czdel]").click()
        assert "Forget this everywhere?" in pg.locator("#mfacts [data-fid='2']").inner_text()
        pg.locator("#mfacts [data-czno]").click()
        assert pg.locator("#mfacts .cz-fact.ask").count() == 0
        pg.locator('#mainp [data-theme-set="dark"]').click()
        for _ in range(40):   # a view transition can lag a frame (no wait_for_function: the console's CSP forbids eval)
            if pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark":
                break
            pg.wait_for_timeout(100)
        assert pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark"
        pg.locator('#mainp [data-font-set="sans"]').click()
        assert "Sans" in pg.locator("#czPvNote").inner_text()
        pg.fill("#pwn", "abc"); assert pg.locator("#pwStr").get_attribute("data-s") == "1"
        pg.fill("#pwn", "LongerPass123!x"); assert pg.locator("#pwStr").get_attribute("data-s") == "4"
        pg.locator("#signin .cz-eye").first.click(); assert pg.locator("#pwn").get_attribute("type") == "text"
        pg.locator("#czReset").click()
        sw = pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1 && document.querySelector('#mainp').scrollWidth <= document.querySelector('#mainp').clientWidth + 1")
        assert sw, "the page scrolls sideways at %d" % w
        if os.environ.get("HOOLA_SHOTS"):
            pg.locator('#mainp [data-theme-set="light"]').click(); pg.wait_for_timeout(4500)
            pg.set_viewport_size({"width": w, "height": 3400 if w > 500 else 5200}); pg.evaluate("document.querySelector('#mainp').scrollTop = 0"); pg.wait_for_timeout(300)
            pg.locator("#mainp").screenshot(path=f"{os.environ['HOOLA_SHOTS']}/cz_{w}.png")
            pg.locator('#mainp [data-theme-set="dark"]').click()
            pg.locator("#mainp .cz-app").screenshot(path=f"{os.environ['HOOLA_SHOTS']}/cz_{w}_dark.png")
        ctx.close()
    assert not errors, errors
