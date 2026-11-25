"""v0.999.199 SMOOTH LANDING like Claude (owner: "NOW LETS WORK ON SMOOTH LANDING OF PROMPT IN CHAT" -> "GO"):
a message she sends lands at the top of the chat (16px under it), the space below is kept for the reply, the
reply grows into it without moving her message, the page follows only after SHE scrolls to the bottom, and a
chat that opens still opens at its bottom - measured in a real browser."""
from __future__ import annotations

import json

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

POS = r"""()=>{const t=document.querySelector('#thread');const b=[...document.querySelectorAll('#col .mu')].pop();
 const pt=parseFloat(getComputedStyle(t).paddingTop)||0;
 return {y:Math.round(b.getBoundingClientRect().top-t.getBoundingClientRect().top-pt),top:Math.round(t.scrollTop),
  gap:Math.round(t.scrollHeight-t.scrollTop-t.clientHeight),jump:document.querySelector('#jump').hidden}}"""
REPLY = r"""(n)=>{const c=document.querySelector('#col');let r=c.lastElementChild;
 if(!r||!r.classList.contains('fake')){r=document.createElement('div');r.className='mh fake';r.innerHTML='<div class="bd"><div class="txt textmd"></div></div>';c.appendChild(r);}
 const t=r.querySelector('.txt');for(let i=0;i<n;i++){const p=document.createElement('p');p.textContent='A line of the reply that grows down the page.';t.appendChild(p);}}"""


def _send(pg, text):
    pg.fill("#msg", text)
    pg.press("#msg", "Enter")
    pg.wait_for_timeout(700)


def test_message_lands_at_the_top(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 820})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)

    def post(route):
        if route.request.method == "POST":
            route.fulfill(status=200, content_type="application/json", body="{}")
        else:
            route.continue_()
    pg.route("**/api/conversations/*/messages", post)
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn")
    pg.wait_for_timeout(2500)                   # the chat is ready to send

    _send(pg, "First question")
    pg.evaluate(REPLY, 60)                       # a long first answer: the chat now scrolls
    pg.wait_for_timeout(200)
    _send(pg, "Second question")
    a = pg.evaluate(POS)
    assert abs(a["y"] - 16) <= 3, a              # her message sits 16px under the top, not at the bottom
    assert a["jump"] is True, a
    for _ in range(5):                           # the reply grows into the kept space; nothing moves
        pg.evaluate(REPLY, 3); pg.wait_for_timeout(80)
        b = pg.evaluate(POS)
        assert abs(b["y"] - 16) <= 3 and b["top"] == a["top"], (a, b)
    pg.evaluate(REPLY, 40)                       # the reply runs past the screen: still no pull, the arrow shows
    pg.wait_for_timeout(150)
    c = pg.evaluate(POS)
    assert abs(c["y"] - 16) <= 3 and c["top"] == a["top"] and c["jump"] is False, c
    pg.mouse.move(640, 400)                      # she scrolls to the end herself: the page follows from then
    for _ in range(12):
        pg.mouse.wheel(0, 800); pg.wait_for_timeout(60)
    pg.wait_for_timeout(300)
    pg.evaluate(REPLY, 10); pg.wait_for_timeout(200)
    d = pg.evaluate(POS)
    assert d["gap"] <= 4, d
    pg.mouse.wheel(0, -600); pg.wait_for_timeout(250)   # she scrolls up: the follow stops
    pg.evaluate(REPLY, 10); pg.wait_for_timeout(200)
    e = pg.evaluate(POS)
    assert e["gap"] > 200, e
    ctx.close()


def test_bubble_fade_and_open_chat_at_bottom():
    from pathlib import Path
    app = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    css = (app / "v2.css").read_text()
    assert "#app .mu{animation:hmRise .2s ease-out both}" in css
    assert "@keyframes hmRise{from{opacity:0;transform:translateY(6px)}" in css
    js = (app / "v2.js").read_text()
    assert "userBubble(body.text, files, null, body.client_id, null, true)" in js   # a send lands
    assert "if (p.role === 'user') userBubble(p.text, p.files, ev.id, null, ev.at);" in js   # history does not
    assert "const scrollDown = force => { if (force) { STICK = true; dropAnchor(); }" in js   # opening a chat drops it
