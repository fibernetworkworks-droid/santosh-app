"""v0.999.213 COLLAPSED SIDEBAR IN ONE LINE (owner, her collapsed-sidebar screenshot: "CHECK THE SIDE PANEL WHEN COLAPSE
THE ICON AND TEXT ARRANGEMENT ARE MESSY AND MISPLACED --- FIX THIS PERFECTLY AND MAKE IT ALINED"): folded, the app-design
sidebar is one column - every button a 40 px square whose middle is the rail's middle, one even step between them, no
words, no Pinned / Recents headers; each icon still names itself on hover; opening it again brings every label back."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")
JS = (CON / "v2.js").read_text(encoding="utf-8")

MEASURE = """()=>{const side=document.querySelector('.side');const sr=side.getBoundingClientRect();
  const vis=e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none';};
  const btns=[...side.querySelectorAll('#collapse, .newc, .srch, #snav .sn')].filter(vis).map(e=>{const r=e.getBoundingClientRect();
    return {c:e.className, mid:r.left+r.width/2-sr.left, top:r.top, w:r.width, h:r.height, title:e.title||e.getAttribute('aria-label')||''}});
  const icons=[...side.querySelectorAll('svg, .uini')].filter(vis).map(e=>{const r=e.getBoundingClientRect();return r.left+r.width/2-sr.left});
  const words=[...side.querySelectorAll('*')].filter(e=>vis(e)&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&!e.classList.contains('uini')).map(e=>e.textContent.trim());
  return {w:sr.width, btns, icons, words}}"""


def test_shape():
    assert "html.appd #app.collapsed .side :is(.slabel,.snl,#pinbox,#recents,.rg,.pjl,.spend){display:none !important}" in CSS
    assert "scrollbar-gutter:auto" in CSS and "width:40px;height:40px;min-width:40px" in CSS
    assert 'title="${esc(n)}" aria-label="${esc(n)}"' in JS


def test_collapsed_rail_is_one_line(arena_server):  # noqa: F811
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
    pg.evaluate(f"""async()=>{{const h={{'Authorization':'Bearer {key}','Content-Type':'application/json'}};
      for (const [t,pin] of [['PINNED ONE',true],['PLAIN ONE',false]]) {{
        const c=await (await fetch('/api/conversations',{{method:'POST',headers:h,body:'{{}}'}})).json();
        await fetch('/api/conversations/'+(c.id||c.conversation_id),{{method:'PATCH',headers:h,body:JSON.stringify({{title:t,pinned:pin}})}});}}}}""")
    pg.reload(); pg.wait_for_selector("html.appd #snav .sn"); pg.wait_for_timeout(900)
    open_words = pg.evaluate(MEASURE)["words"]
    assert "Pinned" in open_words and "Recents" in open_words, open_words        # the open sidebar keeps its labels
    pg.click("#collapse"); pg.wait_for_timeout(500)
    m = pg.evaluate(MEASURE)
    mid = m["w"] / 2
    assert len(m["btns"]) >= 8, m
    for b in m["btns"]:
        assert abs(b["mid"] - mid) <= 1 and b["w"] == 40 and b["h"] == 40, b       # one column on the rail's middle
        assert b["title"], b                                                       # each icon names itself on hover
    assert all(abs(x - mid) <= 1 for x in m["icons"]), m["icons"]
    steps = [round(b["top"] - a["top"]) for a, b in zip(m["btns"][1:], m["btns"][2:])]
    assert len(set(steps)) == 1, steps                                             # one even step
    assert not m["words"], m["words"]                                              # no words, no Pinned / Recents
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/collapsed.png", clip={"x": 0, "y": 0, "width": 240, "height": 900})
        pg.evaluate("document.documentElement.setAttribute('data-theme','dark')"); pg.wait_for_timeout(200)
        pg.screenshot(path=f"{shots}/collapsed-dark.png", clip={"x": 0, "y": 0, "width": 240, "height": 900})
    pg.click("#collapse"); pg.wait_for_timeout(500)
    assert "Recents" in pg.evaluate(MEASURE)["words"]
    assert not errors, errors
    ctx.close()
