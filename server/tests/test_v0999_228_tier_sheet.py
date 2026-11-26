"""v0.999.228 THE QUALITY SHEET (owner, her quality menu: "NOT PROPERLY ALINED AND STALE MAKE IT PREMIUM SHEET LIKE THE
ATTACHMENT SHEET"): the tier sheet is the + card - a header, a tile with its own mark per tier, one line under each,
an ink tick on the chosen one, the note at the foot; it opens below the button and no browser tooltip covers it."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"


def test_shape():
    js = (CON / "v2.js").read_text(encoding="utf-8")
    assert "cls: 'plusm tiers'" in js and "cls: 'plusm tierask'" in js and "TIER_SUB" in js and "TIER_ICON" in js
    assert "b.title = 'Quality: '" not in js and "'⚠ Up to 70× credit'" not in js
    m = (CON / "menu.js").read_text(encoding="utf-8")
    for k in ("qauto:", "qultra:", "qhigh:", "qmed:", "qlow:"):
        assert k in m
    assert "v0.999.228 THE QUALITY SHEET" in (CON / "appdesign.css").read_text(encoding="utf-8")


def test_sheet_in_the_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 960})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.route("**/api/model/tier", lambda r: r.fulfill(status=200, content_type="application/json",
             body=json.dumps({"available": True, "selected": "", "locked": False})))
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn", timeout=30000)
    pg.wait_for_selector("#modelBtn:not([hidden])", timeout=15000)
    assert pg.get_attribute("#modelBtn", "title") is None
    pg.click("#modelBtn")
    pg.wait_for_selector(".hmenu.plusm.tiers .mi"); pg.wait_for_timeout(500)   # after the opening motion
    rows = pg.locator(".hmenu.tiers .mi[role=menuitemradio]")
    assert rows.count() == 5
    box = pg.locator("#modelBtn").bounding_box(); menu = pg.locator(".hmenu.tiers").bounding_box()
    assert menu["y"] >= box["y"] + box["height"] - 1                       # below the button, not over the typing box
    assert abs((menu["x"] + menu["width"]) - (box["x"] + box["width"])) < 2  # right edges line up
    lefts = [rows.nth(i).locator(".ic").first.bounding_box()["x"] for i in range(5)]
    assert max(lefts) - min(lefts) < 1                                                 # every tile on one edge
    assert pg.locator(".hmenu.tiers .mi[aria-checked=true] .mc .ic").count() == 1
    assert pg.locator(".hmenu.tiers .mi small").count() == 5
    assert pg.evaluate("[...document.querySelectorAll('.hmenu.tiers .mi small')].every(e => e.scrollWidth <= e.clientWidth)")  # no line cut off
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/tiers.png")
    rows.nth(1).click()                                                    # Ultra asks first
    pg.wait_for_selector(".hmenu.plusm.tierask")
    if shots:
        pg.screenshot(path=f"{shots}/tierask.png")
    ctx.close()
