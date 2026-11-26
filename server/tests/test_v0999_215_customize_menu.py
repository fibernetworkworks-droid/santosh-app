"""v0.999.215 CUSTOMIZE = PROFILE MENU (owner, her account-menu screenshot: "CHANGE THE CUSTOMERIZE SECTION TO THIS SHOWN
PROFILE OPTIONS"): the app-design sidebar's Customize row opens the same profile menu as the account button (her email,
Settings, Credits, Library, Skills, Light / Dark / System, Keyboard shortcuts, Log out) below it, instead of the Customize
page; Skills gets its own icon."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"
JS = (CON / "v2.js").read_text(encoding="utf-8")
MENU = (CON / "menu.js").read_text(encoding="utf-8")


def test_shape():
    assert "function acctItems()" in JS and "data-acct aria-haspopup=\"menu\"" in JS
    assert "HoolaMenu.open(e.currentTarget, acctItems()" in JS and "HoolaMenu.open(b, acctItems()" in JS
    assert "  skills: '" in MENU


def test_customize_opens_profile_menu(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1366, "height": 760})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav [data-acct]")
    before = pg.evaluate("location.search + location.hash")
    pg.click("#snav [data-acct]"); pg.wait_for_timeout(400)
    items = pg.evaluate("""()=>[...document.querySelectorAll('[role=menu] [role^=menuitem]')].map(e=>({t:e.textContent.trim(),
      ic:!!e.querySelector('svg')}))""")
    words = [i["t"] for i in items]
    for w in ("Settings", "Credits", "Skills", "Light", "Dark", "System", "Keyboard shortcuts", "Log out"):
        assert any(x.startswith(w) for x in words), (w, words)
    assert all(i["ic"] for i in items), items                       # every row has its icon, Skills too
    box = pg.evaluate("""()=>{const m=document.querySelector('[role=menu]').getBoundingClientRect();
      const b=document.querySelector('#snav [data-acct]').getBoundingClientRect();return {mt:m.top,bb:b.bottom,mb:m.bottom,h:innerHeight}}""")
    assert box["mt"] >= box["bb"] - 2 and box["mb"] <= box["h"], box          # below the row, inside the window
    assert pg.evaluate("location.search + location.hash") == before            # the page did not change
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/customize-menu.png", clip={"x": 0, "y": 0, "width": 320, "height": 760})
    pg.keyboard.press("Escape")
    pg.click("#snav [data-acct]"); pg.wait_for_timeout(300)
    pg.click("[role=menu] >> text=Settings"); pg.wait_for_timeout(500)
    assert pg.evaluate("document.querySelector('#snav [data-acct]').getAttribute('aria-current')") == "true"
    assert not errors, errors
    ctx.close()
