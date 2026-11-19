"""v0.999.42 CREATE ON THE CONSOLE (owner: "NOW CHECK THE CREATE SECTION ON CONSOLE DESIGN PROPERLY" -> "GO FIX ALL").

The design check walked all 17 console Create pages in Chromium and found six problems; these tests hold the fixes:
one tile for every creation (Studio home showed a music note for a script), a drawn stand-in under every picture / clip
(a missing file was a flat grey box), a painted film tile (a big pink letter), no "voice voice" tag, the studio's own
picker in the Video editor, and Cinema's text on the studio's sizes."""
import json
import os
import re
from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (CON / "studio.js").read_text()
CSS = (CON / "studio.css").read_text()


def test_one_tile_everywhere():
    assert "function itemTile(it, tall)" in JS and "function standIn(it)" in JS
    # My creations uses the same tile as Studio home (it had its own copy with a record / waveform / page)
    assert "its.map(it => itemTile(it)).join('')" in JS
    tile = JS[JS.index("function itemTile(it, tall)"):JS.index("async function openScript")]
    assert "it.kind === 'script'" in tile and 'data-scopen=' in tile          # a script is a page, never a music note
    assert "art(it.kind === 'voice' ? 'voice' : 'music', it.id)" in tile       # songs / voice-overs drawn, not a lilac box
    assert "audio-ic" not in tile
    # a script opens in the Script writer from any page (it opened a dead-end box saying "Open from My creations")
    assert "if (b.dataset.scopen) { await openScript(b.dataset.scopen); return true; }" in JS


def test_pictures_sit_on_a_drawn_stand_in():
    assert "${standIn(it)}<img alt=\"\" data-src=" in JS and "${standIn(it)}<video muted" in JS
    assert "${standIn(s)}<img alt=\"Front, three-quarter" in JS                 # the cast sheet (it shrank to a thin strip)
    assert 'data-casel="${it.id}"><span class="thumb">${standIn(it)}' in JS    # the Your cast grid
    hyd = JS[JS.index("function hydrate(root = R)"):JS.index("async function download")]
    assert "paintAll(root)" in hyd and "gone chip" in hyd and "th.querySelector('canvas.art')" in hyd
    assert ".gone.chip{" in CSS and ".ph-mark{" in CSS and ".thumb canvas.art ~ img" in CSS


def test_film_tile_and_voice_tag():
    assert "return filmTile(p.project);" in JS and "art('film', 'f' + name)" in JS
    assert "esc(s.meta?.voice || 'voice')} voice" not in JS                    # "voice voice" when no voice was saved
    assert "${s.meta?.voice ? `<span class=\"tag\">" in JS


def test_editor_picker_and_cinema_sizes():
    assert '<select id="edplat"' not in JS and 'class="prow" id="edplat"' in JS
    assert "menu(b, edPlats().map(" in JS
    assert '<div class="grid-opts four">' in JS and ".grid-opts.four{" in CSS
    cin = (CON / "cinema.js").read_text()
    assert "font-size:13px" not in cin


def test_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    items = [
        {"id": "cr1", "kind": "image", "title": "Diwali offer poster", "mime": "image/png", "size": 1, "created": 1700000000, "meta": {}},
        {"id": "cr2", "kind": "song", "title": "Roshni ka tyohaar", "mime": "audio/wav", "size": 1, "created": 1700000000, "meta": {}},
        {"id": "cr4", "kind": "cast", "title": "Cast · Sharma ji", "mime": "image/png", "size": 1, "created": 1700000000, "meta": {"name": "Sharma ji"}},
        {"id": "cr5", "kind": "script", "title": "Script · Diwali ad", "mime": "text/plain", "size": 1, "created": 1700000000},
    ]
    errs = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/create/items", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"items": items})))
    pg.goto(base + "/console/?v=creative")
    pg.wait_for_selector("#cstudio #snav [data-go]", timeout=20000)
    root = "document.querySelector('#cstudio').shadowRoot"
    pg.wait_for_function(f"() => {root}.querySelectorAll('#recent .res').length === 4", timeout=15000)
    # every picture tile has its drawing under it; the missing files get a chip, not a grey box
    pg.wait_for_function(f"() => {root}.querySelectorAll('#recent .gone.chip').length === 2", timeout=15000)
    assert pg.evaluate(f"() => {root}.querySelectorAll('#recent .thumb canvas.art').length") == 3   # the script is a drawn page
    assert pg.evaluate(f"() => {root}.querySelectorAll('#recent [data-scopen]').length") == 1
    assert pg.evaluate(f"() => {root}.querySelectorAll('#recent .audio-ic').length") == 0
    # the editor's Made for is the studio's own menu
    pg.evaluate(f"() => {root}.querySelector('#snav [data-go=\"editor\"]').click()")
    pg.wait_for_function(f"() => {root}.querySelector('#edplat')?.tagName === 'BUTTON'", timeout=10000)
    pg.evaluate(f"() => {root}.querySelector('#edplat').click()")
    pg.wait_for_function(f"() => !{root}.querySelector('#pop').hidden", timeout=5000)
    assert "Instagram Reel" in pg.evaluate(f"() => {root}.querySelector('#pop').textContent")
    ctx.close()
    assert not errs, errs


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
