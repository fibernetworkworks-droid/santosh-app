"""v0.999.225 NO FLASH ON LOAD (owner, her screenshot of the console home while it loads: "WHEN HOME PAGE LOADS WHY IT
SHOW LIKE THIS EVERYTIME CHECK AND FIX"): the typing box is written outside #app in v2.html and moved into the page by
v2.js; while the scripts were still loading it stood alone with no styles (huge search / computer icons, a clip and a
grid button). It is not drawn until it is inside the app."""
from __future__ import annotations

import json
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"


def test_shape():
    assert "body>#composer{display:none!important}" in (CON / "v2.css").read_text(encoding="utf-8")


def test_box_hidden_while_scripts_load(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()

    held = {"on": True}
    pg.route("**/static/console/v2.js*", lambda r: r.abort() if held["on"] else r.continue_())   # the moment before v2.js runs

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.goto(base + "/console/", wait_until="domcontentloaded")
    pg.wait_for_timeout(500)                                      # the page is drawn, v2.js still on its way
    assert pg.evaluate("document.querySelector('#composer').parentElement === document.body")
    assert not pg.is_visible("#composer")                          # the bare box never shows
    shots = __import__("os").environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/loading.png")
    held["on"] = False
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn", timeout=30000)
    assert pg.is_visible("#composer")                              # inside the app it shows as before
    ctx.close()
