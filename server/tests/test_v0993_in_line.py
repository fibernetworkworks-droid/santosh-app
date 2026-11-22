"""v0.993 IN LINE (owner, three screenshots of a long bank-list job: "CHECK THE LOADING. MAKE IT INLINED WITH
CONVERSATION"): once Hoola had written some words, the working row ("Reading the web page 1m 57s") was the next row of
the whole chat, so it took the 44px gap between messages and floated loose above the box. Now it sits inside that
reply, right under its last line, on the same left edge as the words - like the "Worked for" rows."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app/static/console"


def test_the_row_goes_inside_the_reply_in_the_code():
    js = (CON / "v2.js").read_text()
    assert "const host=TURN&&TURN.afterText&&TURN.bd&&TURN.bd.isConnected?TURN.bd:col;" in js
    assert "SIMPLE_PROGRESS.classList.toggle('inturn',host!==col);" in js


def test_the_row_sits_under_the_words_in_a_real_browser(arena_server):
    import httpx
    from app.db import Message, session
    from app.events import bus
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    cid = httpx.post(base + "/api/conversations", headers=h, timeout=20).json()["id"]
    with session() as s:
        s.add(Message(conversation_id=cid, role="user", content="Give me a 50 bank list by profit",
                      display="Give me a 50 bank list by profit", in_history=True))
        s.commit()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/")
    pg.get_by_text("Give me a 50 bank list by profit").first.click()
    pg.wait_for_timeout(1500)

    def pub(kind, payload, wait=350):
        bus.publish(cid, kind, payload)
        pg.wait_for_timeout(wait)

    pub("typing", {"on": True})
    pub("step", {"id": "s1", "tool": "google_search", "label": "Searching Google", "state": "running"})
    before = pg.evaluate("()=>{const p=document.querySelector('.simple-progress');return {inturn:p.classList.contains('inturn'),"
                         "inCol:p.parentElement.classList.contains('col')}}")
    assert before == {"inturn": False, "inCol": True}, before        # no words yet: the reply's first row
    pub("step", {"id": "s1", "tool": "google_search", "label": "Searching Google", "state": "done"})
    pub("reply_start", {"turn": "t1"})
    pub("delta", {"turn": "t1", "seg": 0, "text": "The TABInsights table has all 1,000 banks with net profit. "
                                                 "I am pulling the full table to sort by profit."}, wait=2500)
    pub("step", {"id": "s2", "tool": "web_fetch", "label": "Reading the web page", "state": "running"}, wait=1500)
    m = pg.evaluate("""()=>{const p=document.querySelector('.simple-progress');
      const bd=p.closest('.bd'); const txt=[...(bd?bd.querySelectorAll('.txt'):[])].pop();
      const r=p.getBoundingClientRect(), t=txt?txt.getBoundingClientRect():null;
      const lab=p.querySelector('.progress-label').getBoundingClientRect();
      return {hidden:p.hidden, inturn:p.classList.contains('inturn'), inBd:!!bd, last:p.parentElement.lastElementChild===p,
        gap:t?Math.round(r.top-t.bottom):null, left:t?Math.round(r.left-t.left):null, label:p.querySelector('.progress-label').textContent,
        labelVisible:lab.width>0}}""")
    import os
    if os.environ.get("HOOLA_SHOTS"):
        pg.screenshot(path=os.path.join(os.environ["HOOLA_SHOTS"], "v0993_in_line.png"))
    ctx.close()
    assert not m["hidden"] and m["inturn"] and m["inBd"] and m["last"], m
    assert m["label"] == "Reading the web page" and m["labelVisible"], m
    assert 0 <= m["gap"] <= 20, m           # right under the last line (was the 44px gap between messages + more)
    assert abs(m["left"]) <= 2, m           # on the words' left edge
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.129"
    assert "0.999.129+1124" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
