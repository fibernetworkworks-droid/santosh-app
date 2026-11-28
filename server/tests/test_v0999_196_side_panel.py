"""v0.999.196 SIDE PANEL LIKE CLAUDE (owner: "Side panel - All of it is Anthropic Sans --- MAKE SAME FOR HOOLA"):
the whole side panel in one sans at Claude's own scale - every row, chat, group and name 14 px / 430 / 1.4 (dark 400),
every label 12 px / 430 / 1.4 (dark 400), the open chat not heavier. Anthropic Sans is private, so Hoola's own sans
carries the numbers."""
from __future__ import annotations

import json

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

JS = """()=>{const out=[];const side=document.querySelector('.side');
  for (const el of side.querySelectorAll('.sn,.newc,.srch,.rc,.slabel,.user b,#uhandle,.codepill')) {
    const r=el.getBoundingClientRect(); if(!r.width) continue; const c=getComputedStyle(el);
    out.push({k:el.className||el.id||el.tagName,t:(el.textContent||'').trim().slice(0,20),f:c.fontFamily.split(',')[0].replace(/"/g,''),
      s:c.fontSize,w:c.fontWeight,lh:c.lineHeight}); }
  return out;}"""


def test_side_panel_scale(arena_server):  # noqa: F811
    base, browser, key = arena_server
    for scheme, w in (("light", "430"), ("dark", "400")):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()

        def config(route):
            r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.goto(base + "/console/")
        pg.wait_for_selector("html.appd #snav .sn")
        pg.evaluate(f"""async()=>{{const h={{'Authorization':'Bearer {key}','Content-Type':'application/json'}};
          const c=await (await fetch('/api/conversations',{{method:'POST',headers:h,body:'{{}}'}})).json();
          await fetch('/api/conversations/'+(c.id||c.conversation_id),{{method:'PATCH',headers:h,body:JSON.stringify({{title:'GST summary'}})}});}}""")
        pg.reload(); pg.wait_for_selector("html.appd #recents .rc"); pg.wait_for_timeout(600)
        pg.click("#recents .rc"); pg.wait_for_timeout(600)      # the open chat must not turn heavier
        rows = pg.evaluate(JS)
        assert rows
        for r in rows:
            assert r["f"] == "Schibsted Grotesk", r
            small = "slabel" in r["k"] or r["k"] == "uhandle"
            assert r["s"] == ("12px" if small else "14px"), r
            assert r["w"] == w, r
            assert r["lh"] == ("16.8px" if small else "19.6px"), r
        ctx.close()
