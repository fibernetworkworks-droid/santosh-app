"""v0.981 CHAT BAR LIKE CLAUDE (owner: her Claude and Hoola chat bar screenshots - "make perfectly same as Claude", "Stop:
just show an icon", "remove incognito entirely", "change memory to an icon at the chat bar bottom" -> design canvas
claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL boards 13-14 -> "GO BUILD"): in a chat the box is one line with send / stop
inside; +, mic, call under it, a short honest line, the memory gauge and the model; no Incognito anywhere."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
JS = (CON / "v2.js").read_text(encoding="utf-8")
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")


def test_shape():
    assert not re.search(r"incognito", JS, re.I) or "no Incognito chip" in JS
    assert "newIncognito" not in JS and "INCOG" not in JS and "Incognito chat" not in JS
    assert "function barChrome" in JS and "function memGauge" in JS and "barPlace(on)" in JS
    block = CSS[CSS.index("v0.981 CHAT BAR LIKE CLAUDE"):]
    for line in block.splitlines():
        if "{" in line and not line.lstrip().startswith(("/*", "*", "@media")):
            assert line.lstrip().startswith("html.appd"), line


def test_chat_bar_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.route("**/context", lambda route: route.fulfill(status=200, content_type="application/json",
                                                       body=json.dumps({"context": {"mode": "claude", "percent": 64}})))
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn")
    # the home keeps the tall box with its buttons inside
    home = pg.evaluate("""()=>({home:document.querySelector('#composer').classList.contains('home'),
        sendInRow:!!document.querySelector('#composer .row #sendBtn'),
        note:getComputedStyle(document.querySelector('#cnote')).display})""")
    assert home == {"home": True, "sendInRow": True, "note": "none"}, home
    assert "Incognito" not in pg.content()
    # a chat
    pg.evaluate(f"""async()=>{{const h={{'Authorization':'Bearer {key}','Content-Type':'application/json'}};
        const c=await (await fetch('/api/conversations',{{method:'POST',headers:h,body:'{{}}'}})).json();
        await fetch('/api/conversations/'+(c.id||c.conversation_id),{{method:'PATCH',headers:h,body:JSON.stringify({{title:'GST summary'}})}});
        await fetch('/api/conversations/'+(c.id||c.conversation_id)+'/messages',{{method:'POST',headers:h,body:JSON.stringify({{text:'GST summary banao'}})}});}}""")
    pg.reload(); pg.wait_for_selector("#recents .rc")
    pg.click("#recents .rc"); pg.wait_for_timeout(700)
    m = pg.evaluate("""()=>{const q=s=>document.querySelector(s),r=s=>q(s).getBoundingClientRect();
      const line=r('#cline'), row=r('#composer .row');
      const vis=s=>{const e=q(s);return !!e&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0};
      const ord=['#attach','#micBtn','#callBtn','#cnote','#cMeter','#modelBtn'].filter(s=>!q(s).hidden).map(s=>Math.round(r(s).left));
      return {home:q('#composer').classList.contains('home'), lineH:line.height, lineBorder:getComputedStyle(q('#cline')).borderTopWidth,
        formBorder:getComputedStyle(q('#composer')).borderTopWidth, sendIn:!!q('#cline #sendBtn'), stopIn:!!q('#cline #stopBtn'),
        rowBelow:row.top>=line.bottom-1, ord, sendVis:vis('#sendBtn'), note:q('#cnote').textContent.trim(),
        gauge:vis('#cMeter'), gaugeSvg:!!q('#cMeter svg'), gaugeTitle:q('#cMeter').title, gaugeHot:q('#cMeter').classList.contains('hot'),
        disclaim:vis('.dock .disclaim'), headTags:[...document.querySelectorAll('.chead .ctag')].filter(e=>getComputedStyle(e).display!=='none'&&!e.hidden).length}}""")
    assert not m["home"] and m["sendIn"] and m["stopIn"] and m["rowBelow"], m
    assert 40 <= m["lineH"] <= 48 and m["lineBorder"] == "1px" and m["formBorder"] == "0px", m
    assert m["ord"] == sorted(m["ord"]), m           # + / mic / call / note / memory / model, left to right
    assert m["sendVis"] and m["note"] == "Santosh is AI and can make mistakes.", m
    assert m["gauge"] and m["gaugeSvg"] and m["gaugeTitle"].startswith("Memory 64%") and m["gaugeHot"], m
    assert not m["disclaim"] and m["headTags"] == 0, m
    # typing turns the grey return arrow into the black send arrow
    pg.fill("#msg", "Make the GST summary"); pg.wait_for_timeout(100)
    assert pg.evaluate("getComputedStyle(document.querySelector('#sendBtn .sup')).display") != "none"
    pg.fill("#msg", "")
    # working: Stop is an icon only, the empty send hides
    pg.evaluate("document.querySelector('#stopBtn').hidden=false"); pg.wait_for_timeout(100)
    s = pg.evaluate("""()=>{const b=document.querySelector('#stopBtn'),r=b.getBoundingClientRect();
      return {txt:b.textContent.trim(), label:b.getAttribute('aria-label'), w:r.width, h:r.height,
        send:getComputedStyle(document.querySelector('#sendBtn')).display}}""")
    assert s == {"txt": "", "label": "Stop", "w": 32, "h": 32, "send": "none"}, s
    if shots:
        pg.screenshot(path=f"{shots}/chat-bar.png")
    # the slash list no longer offers an incognito chat
    pg.evaluate("document.querySelector('#stopBtn').hidden=true")
    pg.fill("#msg", "/inc"); pg.wait_for_timeout(200)
    assert "Incognito" not in (pg.evaluate("document.querySelector('#slash').textContent") or "")
    assert not errors, errors
    ctx.close()
