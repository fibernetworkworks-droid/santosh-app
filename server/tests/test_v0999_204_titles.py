"""v0.999.204 TITLES LIKE CLAUDE (owner: "ALSO DO GAME DEV AND HOOLA COMPUTER TITLES"): Game Dev's home greeting and page
titles, Hoola Computer's home and Connect your PC titles in Claude's greeting - Literata 38 / 1.2 at the light weight
(Game Dev is always dark: 290; Hoola Computer follows the theme: 330 light, 290 dark)."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[2] / "server" / "app" / "static" / "console"


def test_the_rules_are_there():
    gd, pc = (CON / "gamedev.css").read_text(), (CON / "computer.css").read_text()
    assert "v0.999.204 TITLES LIKE CLAUDE" in gd and "v0.999.204 TITLES LIKE CLAUDE" in pc
    assert ".gdv-hero h1{font-family:'Literata'" in gd and "font-weight:290}" in gd
    assert ".gdv-pageh h1{font-family:'Literata',Georgia,serif;font-size:28px;line-height:1.25;font-weight:530" in gd
    assert ".hc-main h1,.hc-home h1,.hc-connect h1{font-family:'Literata'" in pc and "font-weight:var(--hck0-gw,330)}" in pc
    for page in ("gamedev.html", "computer.html"):
        assert "Literata:ital,opsz,wght@0,7..72,300..700" in (CON / page).read_text(), page


PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/static/console/chatkit.css">
<link rel="stylesheet" href="/static/console/computer.css"><link rel="stylesheet" href="/static/console/gamedev.css"></head>
<body style="width:1200px"><main class="hc-main hc-home"><h1 id="pc">Hoola Computer</h1></main>
<div class="gdv-hero"><h1 id="gd">What game should we make today?</h1></div><div class="gdv-pageh"><h1 id="gp">All games</h1></div></body></html>"""


def test_the_titles_render_like_claude(arena_server):
    base, browser, _key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    try:
        pg.route(base + "/__t204", lambda r: r.fulfill(status=200, content_type="text/html", body=PAGE))
        pg.goto(base + "/__t204")
        look = """() => Object.fromEntries(['pc','gd','gp'].map(i => { const s = getComputedStyle(document.getElementById(i));
            return [i, [s.fontFamily.split(',')[0].replace(/["']/g, ''), s.fontSize, s.fontWeight]]; }))"""
        light = pg.evaluate(look)
        pg.evaluate("() => { document.documentElement.dataset.theme = 'dark'; }")
        dark = pg.evaluate(look)
    finally:
        ctx.close()
    assert light == {"pc": ["Literata", "38px", "330"], "gd": ["Literata", "38px", "290"], "gp": ["Literata", "28px", "530"]}, light
    assert dark["pc"] == ["Literata", "38px", "290"] and dark["gd"][2] == "290", dark
