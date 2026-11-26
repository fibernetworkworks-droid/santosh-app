"""v0.999.220 NO THEME IN THE PROFILE MENU (owner: "NOW REMOVE THE LIGHT DARK AND SYTEM OPTION IN PROFILE SECTION.
IT IS ALREADY IN CONSTERIZE SECTION"): the profile (account) menu no longer lists Light / Dark / System; the choice stays
on the Customize page's Appearance cards."""
from __future__ import annotations

import json
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

JS = (Path(__file__).resolve().parents[2] / "server/app/static/console/v2.js").read_text(encoding="utf-8")


def test_shape():
    body = JS[JS.index("function acctItems()"):]
    body = body[:body.index("\n}\n")]
    for k in ("'Light'", "'Dark'", "'System'", "setTheme"):
        assert k not in body, k
    assert "data-theme-set=" in JS                        # the Customize page keeps the theme cards


def test_profile_menu_has_no_theme(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn")
    pg.click("#model"); pg.wait_for_timeout(400)
    items = pg.evaluate("[...document.querySelectorAll('[role=menuitem],[role=menuitemradio]')].map(e=>e.textContent.trim())")
    assert any(i.startswith("Customize") for i in items), items
    assert not any(i.split()[0] in ("Light", "Dark", "System") for i in items if i), items
    pg.keyboard.press("Escape")
    assert not errors, errors
    ctx.close()
