"""v0.973 CLAUDE-STYLE CHAT (owner: her Claude screenshot -> "SHOW DESIGN HERE FIRST" -> design canvas
claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL boards 6-9 -> "SHOW SIDE BAR TOP LIKE THIS" -> "GO BUILD"): the web console's
chat shaped like Claude's on Hoola's colours - sidebar top Hoola + Code pill + sidebar button, plain New chat / Search
rows, Work / Made by / AI Employees / Tools / Computer / Customize, the mark beside a serif greeting over a rounded
typing box, Session + model under it, a private-chat button, Claude's + menu."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")
JS = (CON / "v2.js").read_text(encoding="utf-8")
MENU = (CON / "menu.js").read_text(encoding="utf-8")


def test_the_shell_is_claudes_shape():
    assert "return [['hire', 'AI Employees'], ['kaam', 'Tools'], ['computer', 'Computer'], ...more, ['more', 'More'], ['main', 'Customize']];" in JS   # v0.976
    assert "['main', 'Customize']" in JS
    assert "How can ${AV} help you today?" in JS
    assert "function plusMenu(" in JS and "label: 'Deep research'" in JS and "label: 'Use Hoola PC'" in JS
    assert "function sessMenu(" in JS and "id=\"sessBtn\"" not in JS and "incogBtn" not in JS   # v0.974 no ghost; v0.999.23 no Session row
    for k in ("clip:", "search:", "spark:", "grid:"):
        assert k in MENU
    # every new rule stays behind the switch
    block = CSS[CSS.index("v0.973 CLAUDE-STYLE CHAT"):]
    for line in block.splitlines():
        if "{" in line and not line.lstrip().startswith(("/*", "*", "@media")):
            assert line.lstrip().startswith(("html.appd", "html:not(.appd)")), line


def test_claude_chat_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
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
        pg.wait_for_timeout(600)
        m = pg.evaluate("""()=>{const q=s=>document.querySelector(s),g=s=>getComputedStyle(q(s)),r=s=>q(s).getBoundingClientRect();
          return {rows:[...document.querySelectorAll('#snav .sn .txt')].map(e=>e.textContent),
            greet:q('#greet').textContent, gfont:g('#greet').fontFamily, mark:!!q('.landing .hmark svg'),
            row:Math.abs(r('.landing .hmark').top + r('.landing .hmark').height/2 - (r('#greet').top + r('#greet').height/2)) < 8,
            pills:g('.landing .pills').display, ph:q('#msg').placeholder, box:g('#composer').borderRadius,
            under:!!q('#appUnder') && !q('#sessBtn'), incog:!!q('#incogBtn'), clean:getComputedStyle(q('.landing .lhead')).display==='none' && getComputedStyle(q('#liveJobs')).display==='none', sidemark:g('.side .shd .mk').display,
            newc:g('.side .newc').backgroundColor, send:g('#sendBtn').display,
            plusLeft:r('#attach').left < r('#micBtn').left, field:r('#msg').bottom <= r('#attach').top + 2,
            boxIn:r('#composer').right <= r('.landing').right}}""")
        assert m["rows"][:3] == ["AI Employees", "Tools", "Computer"], m   # v0.976
        assert m["rows"][-1] == "Customize", m
        assert re.match(r"Good (morning|afternoon|evening)", m["greet"]), m
        assert "Literata" in m["gfont"] and m["mark"] and m["row"], m
        assert m["pills"] == "none" and m["ph"] == "How can Santosh help you today?", m
        assert m["box"] == "20px" and m["under"] and not m["incog"] and m["clean"], m   # v0.974 clean home
        assert m["newc"] in ("rgba(0, 0, 0, 0)", "transparent"), m
        assert m["send"] == "none" and m["plusLeft"] and m["field"] and m["boxIn"], m
        if shots:
            pg.screenshot(path=f"{shots}/claude-home-{scheme}.png")
        pg.click("#attach")
        pg.wait_for_timeout(300)
        items = pg.evaluate("[...document.querySelectorAll('[role=menu] [role^=menuitem]')].map(e=>e.textContent.trim())")
        assert any("Add photos and files" in t for t in items) and any("Deep research" in t for t in items), items
        pg.keyboard.press("Escape")
        pg.fill("#msg", "hello")
        assert pg.evaluate("getComputedStyle(document.querySelector('#sendBtn')).display") != "none"
        if shots:
            pg.click("#attach"); pg.wait_for_timeout(300)
            pg.screenshot(path=f"{shots}/claude-plus-{scheme}.png"); pg.keyboard.press("Escape")
        # the chat view (the test server streams no reply): the box docks at the bottom, Claude's header above
        pg.fill("#msg", "")
        pg.evaluate("""()=>{const $=s=>document.querySelector(s); $('#landing').hidden=true; $('#thread').hidden=false; $('#dock').hidden=false;
          $('#chead').hidden=false; $('#slotDock').appendChild($('#composer')); const c=document.querySelector('#col');
          c.insertAdjacentHTML('beforeend','<div class="msg mu"><div class="mut">Make this month\\'s GST summary.</div></div>');}""")
        pg.wait_for_selector("#dock:not([hidden]) #composer", timeout=5000)
        pg.wait_for_timeout(400)
        d = pg.evaluate("""()=>{const r=s=>document.querySelector(s).getBoundingClientRect();
          return {ph:document.querySelector('#msg').placeholder, inview:r('#composer').bottom <= innerHeight, chead:getComputedStyle(document.querySelector('#chead')).borderBottomWidth}}""")
        assert d["inview"] and d["chead"] == "0px", d
        if shots:
            pg.screenshot(path=f"{shots}/claude-chat-{scheme}.png")
        assert not errors, errors
        ctx.close()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.102")
