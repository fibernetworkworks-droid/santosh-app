"""v0.719 SAAF COMPOSER (owner, screenshot: "when any artifact, pdf, doc open in right side panel chat typing
section icon gets misplaced ... all content must remain intact not misplaced"): with the side panel open the chat
column is ~250-560 px; the composer row squeezed its buttons to 21 px, broke "Deep research" / "Hoola PC" onto two
lines and pushed Send out of the box. The composer now sizes by its OWN width (container query)."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CSS = Path(__file__).resolve().parents[1] / "app/static/console/v2.css"


def test_composer_sizes_by_its_own_width():
    css = CSS.read_text()
    assert "#app #composer{container-type:inline-size;container-name:composer}" in css
    assert "#app #composer .row{flex-wrap:nowrap;min-width:0}" in css
    assert "#app #composer .row>*{flex:none}" in css                 # buttons never shrink to 21 px
    assert "#app #composer .qc{white-space:nowrap;flex:none}" in css  # chip words never break
    assert "#app #composer .row>#micBtn{margin-left:auto}" in css     # the right group stays flush right
    for q in ("640px", "520px", "360px", "280px"):
        assert f"@container composer (max-width:{q})" in css, q


_MEASURE = """()=>{const row=document.querySelector('#composer .row'), rb=row.getBoundingClientRect(),
  box=document.getElementById('composer').getBoundingClientRect();
  const vis=[...row.children].filter(e=>getComputedStyle(e).display!=='none'&&e.type!=='file');
  const it=vis.map(e=>{const b=e.getBoundingClientRect();return {id:e.id||e.className,l:b.left,r:b.right,t:b.top,w:b.width,h:b.height}});
  const qc=[...document.querySelectorAll('#composer .qc')].map(e=>e.getBoundingClientRect().height);
  return {box:[box.left,box.right], row:[rb.left,rb.right], it, qc,
          ids:vis.map(e=>e.id||e.className)}}"""


def test_composer_intact_with_the_side_panel_open(arena_server):
    base, browser, key = arena_server
    for mode in ("land", "dock"):
        for w in (1180, 1280, 1440, 1700):
            ctx = browser.new_context(viewport={"width": w, "height": 860})
            ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "/console/")
            pg.wait_for_selector("#composer .row")
            pg.fill("#msg", "hello")
            if mode == "dock":
                pg.evaluate("""()=>{document.getElementById('landing').hidden=true;document.getElementById('thread').hidden=false;
                  document.getElementById('dock').hidden=false;document.getElementById('slotDock').appendChild(document.getElementById('composer'))}""")
            pg.evaluate("document.getElementById('app').classList.add('pn'); document.getElementById('stopBtn').hidden=false")
            pg.wait_for_timeout(300)
            m = pg.evaluate(_MEASURE)
            ctx.close()
            where = f"{mode}@{w}"
            assert not errs, (where, errs)
            for need in ("attach", "toolsBtn", "qchips", "micBtn", "stopBtn", "sendBtn"):
                assert need in m["ids"], (where, need)          # nothing dropped
            for i in m["it"]:
                assert i["l"] >= m["row"][0] - 1 and i["r"] <= m["row"][1] + 1, (where, i)   # nothing outside the box
                if i["id"] not in ("qchips", "who"):
                    assert i["w"] >= 30 and i["h"] >= 30, (where, i)                       # never squeezed
            assert all(h <= 34 for h in m["qc"]), (where, m["qc"])  # chip text on ONE line
            right = {i["id"]: i for i in m["it"]}
            assert right["sendBtn"]["r"] >= m["row"][1] - 2, where   # Send sits flush right
            assert abs(right["micBtn"]["t"] - right["sendBtn"]["t"]) <= 3, where
