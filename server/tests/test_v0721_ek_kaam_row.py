"""v0.721 EK HI KAAM-ROW (owner, two screenshots: "IT HAS 2 WORKING... THING IN CHAT SPACE. SHOW ME A PERFECT SINGLE
WORKING.. ALSO DONT SHOW THE BACKEND FEED FREQUENTLY HIDE IT IN DROPDOWN" -> preview -> "DONT SHOW A STEPS JUST A
DROPDOWN ARROW" -> GO): one working row (mark + what is happening now + clock + an arrow), the step list folded under
it, and at the end "Worked for Ns" + the arrow - no second Working block, no step count."""
from __future__ import annotations

import time
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app/static/console"


def test_the_one_row_in_the_code():
    js = (CON / "v2.js").read_text()
    assert "SIMPLE_PROGRESS.append(mark,label,secs,tog,steps);" in js
    assert "tog.className='wtog'" in js and "steps.className='tools hmlive wsteps'" in js
    assert "el.className = 'tools hmfold'; el.open = false; el.hidden = true;" in js     # no second live block
    assert "g.el.querySelector('.sm').textContent = `Worked for ${fmtSecs(secs)}`;" in js   # no step count
    assert "`Worked for ${fmtSecs(secs)} · ${g.n} step" not in js
    assert "textContent = 'Worked';" in js and "Worked · ${n} step" not in js
    css = (CON / "v2.css").read_text()
    assert "#app .simple-progress.wopen .wsteps{display:block}" in css
    assert "#app .simple-progress .wsteps{flex:0 0 100%;display:none;" in css


def test_one_row_in_a_real_browser(arena_server):
    import httpx
    from app.db import Message, session
    from app.events import bus
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    cid = httpx.post(base + "/api/conversations", headers=h, timeout=20).json()["id"]
    with session() as s:
        s.add(Message(conversation_id=cid, role="user", content="Show me images of all Raspberry Pi here",
                      display="Show me images of all Raspberry Pi here", in_history=True))
        s.commit()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/")
    pg.get_by_text("Show me images of all Raspberry Pi here").first.click()
    pg.wait_for_timeout(1500)

    def pub(kind, payload):
        bus.publish(cid, kind, payload)
        pg.wait_for_timeout(350)

    pub("typing", {"on": True})
    pub("step", {"id": "s1", "tool": "web_search", "label": "Google par dhoondh raha hoon", "state": "running"})
    pub("step", {"id": "s1", "tool": "web_search", "label": "Google par dhoondh raha hoon", "state": "done"})
    pub("step", {"id": "s2", "tool": "scrape_page", "label": "Page padh raha hoon", "state": "running"})
    pg.wait_for_timeout(1300)
    live = pg.evaluate("""()=>{const r=document.querySelectorAll('.simple-progress');const p=r[0];
      const vis=e=>!!e&&getComputedStyle(e).display!=='none'&&e.getClientRects().length>0;
      return {rows:r.length, label:p?.querySelector('.progress-label')?.textContent, arrow:vis(p?.querySelector('.wtog')),
        stepsShown:vis(p?.querySelector('.wsteps')), stepRows:p?.querySelectorAll('.wsteps .ts').length,
        otherLive:[...document.querySelectorAll('.tools.hmlive')].filter(e=>!e.closest('.simple-progress')&&vis(e)).length,
        foldsShown:[...document.querySelectorAll('.tools.hmfold')].filter(vis).length,
        text:document.querySelector('#col, .col, main')?.innerText||document.body.innerText}}""")
    assert live["rows"] == 1, live
    assert live["label"] == "Page padh raha hoon", live            # what is happening NOW
    assert live["arrow"] and not live["stepsShown"], live          # folded behind an arrow
    assert live["stepRows"] == 2 and live["otherLive"] == 0 and live["foldsShown"] == 0, live
    assert "Working on it" not in live["text"], live["text"][-300:]   # no second 'Working on it…' line
    pg.click(".simple-progress .wtog")
    pg.wait_for_timeout(300)
    opened = pg.evaluate("()=>getComputedStyle(document.querySelector('.simple-progress .wsteps')).display")
    assert opened == "block"
    pub("step", {"id": "s2", "tool": "scrape_page", "label": "Page padh raha hoon", "state": "done"})
    pub("typing", {"on": False})
    pg.wait_for_timeout(500)
    done = pg.evaluate("""()=>{const f=[...document.querySelectorAll('.tools.hmfold')].filter(e=>!e.hidden);
      return {n:f.length, sm:f[0]?.querySelector('.sm')?.textContent, arrow:!!f[0]?.querySelector('summary .hm-dn'),
        rows:f[0]?.querySelectorAll('.ts').length, open:f[0]?.open, progress:document.querySelectorAll('.simple-progress').length}}""")
    ctx.close()
    assert done["n"] == 1 and done["sm"].startswith("Worked for ") and "step" not in done["sm"], done
    assert done["arrow"] and done["rows"] == 2 and done["open"] is True and done["progress"] == 0, done   # stays open: she opened it
    assert not errs, errs
