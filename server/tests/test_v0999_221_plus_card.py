"""v0.999.221 THE + CARD AND ITS CHIP (owner, her + menu and the chosen Deep research chip: "MAKE THE CARD PREMIUM ...
SELECTED CARD OPTIONS ... PERFECTLY ALLINED AND MUST BE LIKE HUMAN NATIVE MADE NOT A AI BLUE, PINK COMBINATION"):
the + menu is a card with a soft tile per choice and a visible tick on the chosen one; the chosen option sits right
beside the + on the same line, in ink on paper (no violet), with an x - on the home and inside an open chat."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")
JS = (CON / "v2.js").read_text(encoding="utf-8")

ROW = """()=>{const a=document.querySelector('#composer #attach').getBoundingClientRect();
  const c=document.querySelector('#composer .qc[aria-pressed="true"]');const r=c.getBoundingClientRect();const s=getComputedStyle(c);
  return {gap:r.left-a.right, dy:Math.abs((r.top+r.height/2)-(a.top+a.height/2)), h:r.height, bg:s.backgroundColor, fg:s.color,
          ink:getComputedStyle(document.documentElement).getPropertyValue('--ink').trim()}}"""


def test_shape():
    assert "cls: 'plusm'" in JS
    assert ".hmenu.plusm .mi .ic{" in CSS and 'html.appd #app #composer .row:has(.qc[aria-pressed="true"]) #attach{margin-right:0}' in CSS
    assert "--pri-soft" not in CSS.split("v0.999.221 THE + CARD")[1]          # no violet in the new block


def test_plus_card_and_chip(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn"); pg.wait_for_timeout(700)
    plus = pg.locator("#composer [aria-label='Add photos, files and more']")
    plus.click(); pg.wait_for_selector(".hmenu.plusm.on")
    tiles = pg.evaluate("[...document.querySelectorAll('.hmenu.plusm .mi .mt')].length")
    assert tiles >= 4
    pg.locator(".hmenu .mi", has_text="Deep research").click(); pg.wait_for_timeout(250)
    m = pg.evaluate(ROW)
    assert 0 <= m["gap"] <= 10 and m["dy"] <= 1 and m["h"] == 32, m               # beside the +, on its line
    assert "rgb(255, 255, 255)" in m["bg"] and m["fg"] != "rgb(91, 69, 224)", m       # paper and ink, not violet
    plus.click(); pg.wait_for_selector(".hmenu.plusm.on")
    tick = pg.evaluate("""()=>{const t=document.querySelector('.hmenu.plusm .mi[aria-checked="true"] .mc .ic');
      return t && getComputedStyle(t).color}""")
    ink = pg.evaluate("getComputedStyle(document.querySelector('.hmenu.plusm .mi .mt>span')).color")
    assert tick == ink, (tick, ink)                                                   # the tick is visible
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/plus-card.png")
    pg.keyboard.press("Escape")
    pg.evaluate("document.querySelector('#composer').classList.remove('home')"); pg.wait_for_timeout(200)
    m = pg.evaluate(ROW)
    assert 0 <= m["gap"] <= 10 and m["dy"] <= 1, m                                    # the same inside a chat
    pg.locator("#composer .qc[aria-pressed='true']").click(); pg.wait_for_timeout(200)
    assert pg.evaluate("document.querySelectorAll('#composer .qc[aria-pressed=\"true\"]').length") == 0   # tap = off
    assert not errors, errors
    ctx.close()
