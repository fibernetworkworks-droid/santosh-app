"""v0.996 BACK TO WORK (owner: "WHEN ONE SESSION IS WORKING AND WE START NEW SESSION AND AGAIN COMEBACK TO WORKING
SESSION ---- WORKING SESSION WORK GET HANGED AND SHOW UNWANTED THING IN CHAT SPACE"). Found by walking it in a browser:
coming back, the console redrew the chat from the server but threw away the running turn's live state - its steps were
skipped, the working row said "Thinking... 1s" (the clock restarted, the step it was on was gone) and stayed so until the
next step, which on a long tool is minutes (it looked hung); a note Hoola had written was wiped by the empty live block;
and the working flag was a remembered one (stale = "Thinking" with Stop for ever on a finished chat). Now the timeline
says whether the chat is working and since when, and the running turn is drawn exactly as it was drawn live."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app/static/console"

ROW = """()=>{const p=document.querySelector('.simple-progress'); if(!p) return null;
  return {label:p.querySelector('.progress-label').textContent, secs:p.querySelector('.progress-secs').textContent,
    hidden:p.hidden, inBd:!!p.closest('.bd'), last:p.parentElement.lastElementChild===p,
    steps:[...p.querySelectorAll('.wsteps .ts')].map(r=>[r.classList.contains('run'), r.querySelector('.tx').textContent]),
    acts:document.querySelectorAll('.racts').length, stop:!document.querySelector('#stopBtn').hidden,
    text:document.querySelector('#app .col').innerText}}"""


def test_the_code():
    js = (CON / "v2.js").read_text()
    assert "const resumed = renderEvents(tl.events, any, busy ? (tl.busy_from || 0) : 0);" in js
    assert "if (typeof tl.busy === 'boolean') CH?.busy(id, tl.busy);" in js
    assert "if (s.text && !(had && had.pacer.finalText !== null))" in js
    assert "if (CH?.isBusy(id)) typing(true);" not in js


def _chats(base, h):
    import httpx
    from app.db import Message, session
    from app.events import bus
    a = httpx.post(base + "/api/conversations", headers=h, timeout=20).json()["id"]
    b = httpx.post(base + "/api/conversations?reuse=false", headers=h, timeout=20).json()["id"]
    with session() as s:
        for c, t in ((a, "Give me 50 banks by profit"), (b, "Something else")):
            s.add(Message(conversation_id=c, role="user", content=t, display=t, in_history=True))
        s.commit()
    bus.publish(a, "message", {"role": "user", "text": "Give me 50 banks by profit"})
    bus.publish(b, "message", {"role": "user", "text": "Something else"})
    return a, b


def test_coming_back_to_a_working_chat_shows_it_as_it_was(arena_server):
    from app import livereply
    from app.agent import santosh as SA
    from app.events import bus
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    a, b = _chats(base, h)
    lk = asyncio.Lock(); lk._locked = True; SA._locks[a] = lk        # chat A is working (its turn holds the chat)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        pg.goto(base + "/console/c/" + a); pg.wait_for_timeout(2000)

        def pub(kind, p, w=300):
            bus.publish(a, kind, p); pg.wait_for_timeout(w)

        def click(c):
            pg.evaluate(f"()=>document.querySelector('#recents .rc[data-conv=\"{c}\"]').click()"); pg.wait_for_timeout(2000)

        pub("typing", {"on": True})
        lv = livereply.Live(a, "default"); lv.start(); lv.block()
        pub("step", {"id": "s1", "tool": "google_search", "label": "Searching Google", "state": "running"})
        pub("step", {"id": "s1", "tool": "google_search", "label": "Searching Google", "state": "done"})
        words = "I found the list of banks and I am now reading the page for profits."
        lv.feed(words + " "); pg.wait_for_timeout(1500)
        bus.publish(a, "message", {"role": "assistant", "text": words, "source": "agent", **lv.tag()})
        lv.block()
        bus.publish(a, "message", {"role": "assistant", "text": "Note: the page is slow today.", "source": "agent",
                                   "note": True, **lv.tag(True)})
        pub("step", {"id": "s2", "tool": "web_fetch", "label": "Reading the web page", "state": "running"}, 1000)
        click(b)                                                            # a new session...
        pub("step", {"id": "s2", "tool": "web_fetch", "label": "Reading the web page", "state": "done"}, 100)
        pub("step", {"id": "s3", "tool": "pylab", "label": "Sorting the table", "state": "running"}, 2500)
        click(a)                                                            # ...and back to the working one
        r = pg.evaluate(ROW)
        assert r and not r["hidden"] and r["inBd"] and r["last"] and r["stop"], r
        assert r["label"] == "Sorting the table", r                         # the step it is on, not "Thinking…"
        assert r["steps"] == [[False, "Reading the web page"], [True, "Sorting the table"]], r
        assert r["secs"] and r["secs"] not in ("1s", "2s"), r             # the clock runs from the turn's start
        assert words in r["text"] and "Note: the page is slow today." in r["text"], r   # nothing wiped
        assert "Worked for" in r["text"] and r["acts"] == 0, r             # no Copy / Retry mid-turn
        pub("step", {"id": "s3", "tool": "pylab", "label": "Sorting the table", "state": "done"})
        lv.block(); end = "Here is the sorted list of 50 banks by profit."
        lv.feed(end); pg.wait_for_timeout(1500)
        bus.publish(a, "message", {"role": "assistant", "text": end, "source": "agent", **lv.tag()})
        lv.end(); lk._locked = False; pub("typing", {"on": False}, 1500)
        done = pg.evaluate("()=>({row:!!document.querySelector('.simple-progress'),acts:document.querySelectorAll('.racts').length,"
                           "stop:!document.querySelector('#stopBtn').hidden,text:document.querySelector('#app .col').innerText})")
        assert not done["row"] and not done["stop"] and done["acts"] == 1 and end in done["text"], done
        assert done["text"].count(words) == 1, done
        assert not errs, errs
    finally:
        lk._locked = False; SA._locks.pop(a, None); ctx.close()


def test_a_finished_chat_never_opens_as_working(arena_server):
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    a, b = _chats(base, h)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    try:
        pg.goto(base + "/console/c/" + b); pg.wait_for_timeout(2000)
        from app.events import bus
        bus.publish(a, "typing", {"on": True}); pg.wait_for_timeout(600)   # the sidebar heard "working"...
        pg.evaluate(f"()=>document.querySelector('#recents .rc[data-conv=\"{a}\"]').click()"); pg.wait_for_timeout(2000)
        r = pg.evaluate(ROW)                                                # ...but the chat is not working any more
        assert r is None and not pg.evaluate("()=>!document.querySelector('#stopBtn').hidden")
    finally:
        ctx.close()


def test_the_timeline_says_working_and_since_when(env):
    from app.agent import santosh as SA
    from app.events import bus, timeline
    bus.publish("c_w", "message", {"role": "user", "text": "hi"})
    assert timeline("c_w", "", own=True)["busy"] is False
    lk = asyncio.Lock(); lk._locked = True; SA._locks["c_w"] = lk
    try:
        bus.publish("c_w", "typing", {"on": True})
        t = timeline("c_w", "", own=True)
        assert t["busy"] is True and t["busy_since"] and t["busy_from"] > 0
        assert "busy" not in timeline("c_w", "", own=True, before=10**9)     # an older page never says
    finally:
        SA._locks.pop("c_w", None)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.151"
    assert "0.999.151+1146" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
