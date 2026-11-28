"""v0.999.198 HOME LIKE CLAUDE (owner: Claude's home table "--- ALSO MAKE THIS SAME"): the greeting 38 px / 330
(dark 290) / 1.2 in the serif, the typing box 16 px / 430 (dark 400), the row under the box 14 px / 430 (dark 400) -
measured in a real browser, light and dark."""
from __future__ import annotations

import json

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

JS = r"""()=>{const S=e=>{if(!e)return null;const c=getComputedStyle(e);return {f:c.fontFamily.split(',')[0].replace(/"/g,''),s:c.fontSize,w:c.fontWeight,lh:c.lineHeight}};
 const ph=getComputedStyle(document.querySelector('#msg'),'::placeholder');
 const under=[...document.querySelectorAll('.appunder .uchip,#modelBtn,#modelBtn .mname')].map(S);
 return {g:S(document.querySelector('#greet')),box:S(document.querySelector('#msg')),ph:{s:ph.fontSize,w:ph.fontWeight},under};}"""


def test_home(arena_server):  # noqa: F811
    base, browser, key = arena_server
    for scheme, g, w in (("light", "330", "430"), ("dark", "290", "400")):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()

        def config(route):
            r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.goto(base + "/console/")
        pg.wait_for_selector("html.appd #snav .sn")
        pg.wait_for_timeout(600)
        m = pg.evaluate(JS)
        assert m["g"] == {"f": "Literata", "s": "38px", "w": g, "lh": "45.6px"}, m
        assert m["box"]["s"] == "16px" and m["box"]["w"] == w and m["ph"] == {"s": "16px", "w": w}, m
        assert m["under"], m
        for u in m["under"]:
            assert u["s"] == "14px" and u["w"] == w and u["f"] == "Schibsted Grotesk", m
        ctx.close()
