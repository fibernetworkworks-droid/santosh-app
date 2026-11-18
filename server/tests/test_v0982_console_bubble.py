"""v0.982 BUBBLE LINES (owner, her screenshot: the first line of her wrapped message was indented and cut by the
line below): since v0.970 the app design gave the inline .mut span its own background + padding; on a wrapped
inline span horizontal padding indents only the first line and each line's background paints over the line above.
The bubble is the .mu box now; .mut is a plain block."""
from __future__ import annotations

import json
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CSS = (Path(__file__).resolve().parents[1] / "app/static/console/appdesign.css").read_text(encoding="utf-8")
MSG = ('Page "Radiant Broadband Panel" (v2) mein error aa raha hai: Uncaught SyntaxError: Unexpected token \'}\' '
       '(line 164). Isse theek karke naya version banao.')


def test_shape():
    assert "html.appd #app .mu .mut{background:var(--you)" not in CSS
    assert "html.appd #app .mu .mut{display:block;background:none" in CSS
    assert "html.appd #app .mu:not(.fonly){background:var(--you)" in CSS


def test_wrapped_message_lines_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1366, "height": 633})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.goto(base + "/console/"); pg.wait_for_selector("#snav .sn")
    pg.evaluate("""async([k,m])=>{const h={'Authorization':'Bearer '+k,'Content-Type':'application/json'};
      const c=await (await fetch('/api/conversations',{method:'POST',headers:h,body:'{}'})).json(), id=c.id||c.conversation_id;
      await fetch('/api/conversations/'+id,{method:'PATCH',headers:h,body:JSON.stringify({title:'Page fix'})});
      await fetch('/api/conversations/'+id+'/messages',{method:'POST',headers:h,body:JSON.stringify({text:m})});}""", [key, MSG])
    pg.reload(); pg.wait_for_selector("#recents .rc"); pg.click("#recents .rc"); pg.wait_for_timeout(1500)
    m = pg.evaluate("""()=>{const mu=document.querySelector('.mu'),t=mu.querySelector('.mut'),r=document.createRange();
      r.selectNodeContents(t);const rows={};for(const q of r.getClientRects()){const y=Math.round(q.top);
      rows[y]=Math.min(rows[y]??1e9,q.left)}const ys=Object.keys(rows).map(Number).sort((a,b)=>a-b),b=mu.getBoundingClientRect();
      return {ys,lefts:ys.map(y=>Math.round(rows[y])),top:b.top,bottom:b.bottom,bg:getComputedStyle(t).backgroundColor,
        pad:getComputedStyle(t).paddingLeft}}""")
    assert len(m["ys"]) >= 2, m                                          # it really wraps
    assert len(set(m["lefts"])) == 1, m                                  # every line starts on the same edge
    assert all(b - a >= 20 for a, b in zip(m["ys"], m["ys"][1:])), m     # no line drawn over another
    assert m["ys"][0] - m["top"] >= 8 and m["bg"] == "rgba(0, 0, 0, 0)" and m["pad"] == "0px", m
    ctx.close()
