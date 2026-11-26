"""v0.999.217 CUSTOMIZE IN THE PROFILE MENU (owner, after v0.999.215: "UNDO -- I TELL U TO JUST PALCE / MOVE THE
CONSTERZE SECTION IN PROPFINE"): the sidebar has no Customize row any more (v0.999.215's row that opened the profile
menu is undone); Customize is an item of the profile (account) menu and opens the Customize page."""
from __future__ import annotations

import json
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"
JS = (CON / "v2.js").read_text(encoding="utf-8")
MENU = (CON / "menu.js").read_text(encoding="utf-8")


def test_shape():
    assert "data-acct" not in JS                                         # the v0.999.215 row and its handler are gone
    assert "['more', 'More']];" in JS and "['main', 'Customize']" not in JS
    assert "{label: 'Customize', icon: 'brush', run: () => go('main')}" in JS
    assert "brush:" in MENU


def test_customize_lives_in_the_profile_menu(arena_server):  # noqa: F811
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
    rows = pg.evaluate("[...document.querySelectorAll('#snav .sn .txt')].map(e=>e.textContent.trim())")
    assert "Customize" not in rows and rows[-1] == "More", rows
    pg.click("#model"); pg.wait_for_timeout(400)
    items = pg.evaluate("[...document.querySelectorAll('[role=menuitem],[role=menuitemradio]')].map(e=>e.textContent.trim())")
    assert any(i.startswith("Customize") for i in items), items
    pg.locator("[role=menuitem]", has_text="Customize").first.click(); pg.wait_for_timeout(500)
    assert pg.evaluate("!document.getElementById('v-main').hidden")   # the Customize page is open
    assert not errors, errors
    ctx.close()
