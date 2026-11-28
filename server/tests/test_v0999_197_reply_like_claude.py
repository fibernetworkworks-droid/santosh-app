"""v0.999.197 REPLY + MESSAGE LIKE CLAUDE (owner: Claude's reply table "--- DO SAME FOR THIS ALSO TO HOOLA"):
reply body 16 / 1.5 at 400 (dark 360), bold 600 (dark 530), the reply title (#) 28 px / 1.3, reply code in the mono
font, and her own message in the sans at 16 / 430 / 1.4 (dark 400) - measured in a real browser, light and dark."""
from __future__ import annotations

import json

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

JS = r"""()=>{const S=e=>{const c=getComputedStyle(e);return {f:c.fontFamily.split(',')[0].replace(/"/g,''),s:c.fontSize,w:c.fontWeight,lh:c.lineHeight}};
 const col=document.querySelector('#col'),th=document.querySelector('#thread'); if(th) th.hidden=false;
 const u=document.createElement('div');u.className='mu';u.innerHTML='<span class="mut">Make this month GST summary</span>';col.appendChild(u);
 const h=document.createElement('div');h.className='mh';h.innerHTML='<div class="bd"><div class="txt textmd">'+
   HoolaMD.render("# Title here\n\nNormal reply with **bold words** and `code`.\n\n```\nblock\n```",false)+'</div></div>';col.appendChild(h);
 const t=h.querySelector('.txt');
 return {me:S(u.querySelector('.mut')),p:S(t.querySelector('p')),b:S(t.querySelector('strong,b')),
   h:S(t.querySelector('h3.mdh')),code:S(t.querySelector('p code')),pre:S(t.querySelector('pre'))};}"""


def test_reply_and_message(arena_server):  # noqa: F811
    base, browser, key = arena_server
    for scheme, body, bold, mine in (("light", "400", "600", "430"), ("dark", "360", "530", "400")):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()

        def config(route):
            r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.goto(base + "/console/")
        pg.wait_for_selector("html.appd #snav .sn")
        pg.wait_for_timeout(500)
        m = pg.evaluate(JS)
        assert m["p"] == {"f": "Literata", "s": "16px", "w": body, "lh": "24px"}, m
        assert m["b"]["w"] == bold and m["b"]["s"] == "16px", m
        assert m["h"]["s"] == "28px" and m["h"]["lh"] == "36.4px" and m["h"]["w"] == bold, m
        assert m["me"] == {"f": "Schibsted Grotesk", "s": "16px", "w": mine, "lh": "22.4px"}, m
        assert m["code"]["f"] == "JetBrains Mono" and m["pre"]["f"] == "JetBrains Mono", m
        ctx.close()
