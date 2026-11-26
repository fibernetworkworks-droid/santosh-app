"""v0.999.211 NO SESSIONS IN THE SIDEBAR (owner, her sidebar screenshot: "NOW CHECK THE SESSIONS --- REMOVE THAT FROM
SIDE BAR"): the app-design sidebar shows no Sessions label, no + and no session groups; a chat that sits in a session
is still listed in Recents (nothing disappears); the chat menu no longer offers Add to session there."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")
CL = (CON / "chatlist.js").read_text(encoding="utf-8")


def test_shape():
    assert "const SIDE_SECS = () => APPD() ? [] : SECS;" in CL
    assert "for (const p of SIDE_SECS())" in CL and "ctx.pickProject && !APPD()" in CL
    assert "html.appd #app .side #projects{display:none}" in CSS


def test_sidebar_has_no_sessions(arena_server):  # noqa: F811
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
      const p=await (await fetch('/api/projects',{{method:'POST',headers:h,body:JSON.stringify({{name:'GST work'}})}})).json();
      for (const [t,pid] of [['HELO',p.id],['READ','']]) {{
        const c=await (await fetch('/api/conversations',{{method:'POST',headers:h,body:'{{}}'}})).json();
        await fetch('/api/conversations/'+(c.id||c.conversation_id),{{method:'PATCH',headers:h,body:JSON.stringify({{title:t,project_id:pid}})}});}}}}""")
    pg.reload(); pg.wait_for_selector("html.appd #snav .sn"); pg.wait_for_timeout(900)
    m = pg.evaluate("""()=>{const side=document.querySelector('.side');
      const vis=e=>e&&e.getClientRects().length>0;
      return {text:side.innerText, projects:vis(document.querySelector('#projects')), groups:document.querySelectorAll('#recents .sgh').length,
        chats:[...document.querySelectorAll('#recents .rc .rct')].map(e=>e.textContent), other:[...document.querySelectorAll('#recents .rg')].map(e=>e.textContent)}}""")
    assert not m["projects"] and m["groups"] == 0, m
    assert "Sessions" not in m["text"] and "GST work" not in m["text"], m
    assert {"HELO", "READ"} <= set(m["chats"]) and "Other chats" not in m["other"], m
    pg.hover("#recents .rcw"); pg.click("#recents .rcw .rcm")
    pg.wait_for_timeout(300)
    items = pg.evaluate("[...document.querySelectorAll('[role=menu] [role^=menuitem]')].map(e=>e.textContent.trim())")
    assert items and not any("session" in t.lower() for t in items), items
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.keyboard.press("Escape"); pg.screenshot(path=f"{shots}/no-sessions.png")
    assert not errors, errors
    ctx.close()
