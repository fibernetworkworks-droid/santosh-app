"""HOOLA CHAT KIT in Hoola Code, Hoola Auto and the client intake page (owner: every chat panel has the SAME features,
design, word landing, timing and spacing as the main Hoola chat).

The four panels this file holds to it:
  1. the Hoola Code session thread (/console/code#/s/<id>, code.js)
  2. the Hoola Auto agent chat (#/auto/<pid>/agent/<role>, hoolaauto.js)
  3. the Hoola Auto intake talk (#/auto/<pid>/talk, hoolaauto.js)
  4. the client's intake page (/auto/intake/<token>, auto/intake.js)

Each one: the thread root is the kit's (.hck), her message is a kit bubble shown the moment she sends, a reply is a kit
reply that LANDS (what was already there is drawn whole), there is ONE working row from the kit while Hoola works,
Copy / Read aloud sit under the newest reply, and a refresh never rebuilds the thread. With HOOLA_SHOTS set it saves
pictures."""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "server/app/static"
KIT = ["md.js", "mark.js", "stream.js", "chatkit.js"]


# ---------------------------------------------------------------- 1. the pages load the kit, the panels mount it
def _tags(html: str):
    css = re.findall(r'<link rel="stylesheet" href="([^"]+)"', html)
    js = re.findall(r'<script src="([^"]+)"', html)
    return css, js


def test_the_pages_load_the_kit_in_order_with_their_own_stamp():
    for page, own_css, scripts in (("console/hoolacode.html", "/static/console/hoolacode.css", ["hoolaauto.js", "code.js"]),
                                   ("auto/intake.html", "/static/auto/intake.css", ["intake.js"])):
        html = (STATIC / page).read_text()
        css, js = _tags(html)
        names = [u.split("?")[0].rsplit("/", 1)[-1] for u in js]
        at = [names.index(k) for k in KIT]
        assert at == sorted(at), (page, names)                                     # md, mark, stream, chatkit - in this order
        assert all(names.index("chatkit.js") < names.index(s) for s in scripts), (page, names)   # before the panel's own script
        assert all(u.startswith("/static/console/") for u in js if u.split("?")[0].rsplit("/", 1)[-1] in KIT)
        cnames = [u.split("?")[0] for u in css]
        assert cnames.index("/static/console/chatkit.css") < cnames.index(own_css), page   # the page's token names win
        stamps = {u.split("?", 1)[1] for u in css + js if u.startswith("/static/") and "?" in u}
        assert len(stamps) == 1, (page, stamps)                                    # the kit carries the page's own stamp
        assert "Literata" in html                                                  # the reply serif
    assert 'data-theme="light"' in (STATIC / "auto/intake.html").read_text()        # the client page is always light: the kit never goes dark on it


def test_the_panels_mount_the_kit_and_the_old_waiting_marks_are_gone():
    code = (STATIC / "console/code.js").read_text()
    auto = (STATIC / "console/hoolaauto.js").read_text()
    intake = (STATIC / "auto/intake.js").read_text()
    css = (STATIC / "console/hoolacode.css").read_text()
    icss = (STATIC / "auto/intake.css").read_text()
    assert "HoolaChat.mount(col, o)" in code and "k.t.begin(nowLabel(k.task))" in code            # the session thread + its ONE working row
    assert "k.task.run_at" in code and "t.now || nowDoing(t)" in code                             # the clock and the running step are the server's
    assert auto.count("HoolaChat.mount(") == 2 and "window.HoolaChat.bar(host, o)" in auto          # the agent chat + the intake talk, the kit's box
    assert "window.HoolaChat.mount(TK.root" in intake and "window.HoolaChat.bar(barHost" in intake
    # the old waiting markup: a pulsing dot row, a spinning ring line, italic "thinking" text, a tinted bubble
    assert 'class="hcd-work"' not in code and "feedHTML" not in code and ".hcd-work" not in css
    assert "hca-live" not in auto and "hca-live" not in css and "Intake is thinking" not in auto
    assert "ci-tb" not in intake and "ci-tb" not in icss and "hca-you" not in auto and "hca-composer" not in auto
    # her words show the moment she sends; a reply that arrives in one piece is handed to the kit to land
    assert "herNow(v)" in code and "a.t.her(text, {pending: true})" in auto and "k.final(r.reply || '')" in auto and "k.final(out.reply || '')" in intake
    # the kit's files themselves are not this group's to change: the panels only use its API
    kit = (STATIC / "console/chatkit.js").read_text()
    assert "window.HoolaChat = {mount, bar, fmtSecs, plain}" in kit
    # the page's resets leave the kit's reply text alone (paragraph gaps, italics, code)
    assert "#app .hcd :where(h1,h2,h3,p):not(.hck-txt *){margin:0}" in css and "#app .hcd em:not(.hck-txt *)" in css
    assert "--hck-bubble:var(--you)" in css and "--hck-hair:var(--line)" in icss


# ---------------------------------------------------------------- the browser walks
NOW = datetime.now(timezone.utc)


def _at(sec: float) -> str:
    return (NOW + timedelta(seconds=sec)).isoformat()


SAY0 = "I will look at how the cart computes its total first."
SAY1 = ("The total is divided by the number of items, which is the bug: a total is a **sum**, not an average. "
        "An empty cart then divides by zero. I will write the failing test first, then fix `total()` so an empty cart returns 0 "
        "and every other cart returns the plain sum of its lines.")
SAY2 = "Fixed. `total()` returns the sum, an empty cart returns 0, and the new test passes."
HER = "The cart total crashes when the cart is empty."


def _task(**kw):
    t = {"id": "dt1", "number": "D-0101", "kind": "fix", "repo": "meghana/shop-api", "status": "new", "title": "Empty cart crashes the total",
         "running": True, "stopping": False, "archived": False, "at": _at(-90), "updated": _at(-5), "run_at": _at(-65), "now": "", "live": "",
         "ci": {}, "checks": [], "proof": {}, "self_review": {}, "plan": {}, "pr_number": 0, "pr_url": "", "branch": "", "tier": "",
         "auto_fix": True, "question": "", "base": "main", "mode": "auto", "model": "", "effort": "high", "attach": [], "cost": {}, "text": HER,
         "notes": [], "log": [], "found": {}, "hash": "", "explain": "", "risk": "", "error": "", "rounds": 0, "steps": [], "files": [],
         "file_diffs": [], "diff": "", "can_continue": False, "ws": {"exists": False}, "hint": "", "share": {"on": False}, "sched_id": "",
         "pr_comments": [], "refs": [], "group": []}
    t.update(kw)
    return t


STEPS = [{"k": "say", "text": SAY0, "at": _at(-60), "n": 0},
         {"k": "read", "path": "app/cart.py", "lines": [0, 0], "at": _at(-50), "n": 1},
         {"k": "read", "path": "tests/test_cart.py", "lines": [0, 0], "at": _at(-44), "n": 2},
         {"k": "search", "q": "total(", "num": 3, "at": _at(-40), "n": 3}]
MORE = [{"k": "say", "text": SAY1, "at": _at(-20), "n": 4},
        {"k": "edit", "path": "tests/test_cart.py", "added": 4, "removed": 0, "diff": ["+def test_empty_cart_is_zero():", "+    assert total([]) == 0"], "at": _at(-10), "n": 5}]
LAST = [{"k": "say", "text": SAY2, "final": True, "at": _at(-2), "n": 6}, {"k": "round", "secs": 63, "text": "Worked for 1m 03s", "at": _at(-1), "n": 7}]
OV = {"settings": {"github": True, "login": "meghana", "default_repo": "meghana/shop-api", "permissions": ["Contents"], "never": ["Never push to main"]},
      "repos": [{"repo": "meghana/shop-api", "private": True}], "reviews": [], "actions": [], "kinds": {}, "schedules": []}


def _page(arena_server, width=1360, dark=False):
    base, browser, key = arena_server
    from app.config import get_settings
    get_settings().hoola_code_page = True
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme="dark" if dark else "light")
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}');" + ("localStorage.setItem('hoola.theme','dark');" if dark else ""))
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    return base, ctx, pg, errs


def _shot(pg, name):
    d = os.environ.get("HOOLA_SHOTS")
    if d:
        pg.screenshot(path=os.path.join(d, name + ".png"))


THREAD = """() => { const col = document.querySelector('#hcdCol'); if (!col) return null;
  const kids = [...col.querySelectorAll(':scope > .hck-me, :scope > .hck-ho > *')].filter(e => !e.hidden).map(e =>
    e.classList.contains('hck-me') ? 'her' : e.classList.contains('hck-txt') ? 'say' : e.classList.contains('hcd-wgrp') ? (e.querySelector(':scope > .hck-fold') ? 'fold' : 'rows')
      : e.classList.contains('hck-work') ? 'work' : e.classList.contains('hck-acts') ? 'acts' : e.className);
  return {kit: col.classList.contains('hck'), kids, txt: [...col.querySelectorAll('.hck-txt')].map(e => e.textContent), bub: [...col.querySelectorAll('.hck-bub')].map(e => e.textContent),
    label: (col.querySelector('.hck-work:not([hidden]) .hck-label') || {}).textContent || '', secs: (col.querySelector('.hck-work .hck-secs') || {}).textContent || '',
    folds: [...col.querySelectorAll('.hcd-wgrp > .hck-fold > summary')].map(e => e.textContent.trim()), acts: [...col.querySelectorAll('.hck-acts [data-act]')].map(b => b.dataset.act),
    old: col.querySelectorAll('.hcd-work, .hcd-me, .hcd-say').length, landing: col.querySelectorAll('.hck-txt .w').length,
    same: window.__bub === col.querySelector('.hck-bub')}; }"""


def test_the_session_thread_is_the_kit_and_a_refresh_only_adds(arena_server):  # noqa: F811
    base, ctx, pg, errs = _page(arena_server)
    st = {"steps": list(STEPS), "running": True, "status": "new", "now": "Reading app/cart.py", "live": "", "posts": []}
    st["run_at"] = (datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat()   # 65 s before THIS test starts (the file's NOW is set at import)

    def dt1(r):
        r.fulfill(json=_task(steps=st["steps"], running=st["running"], status=st["status"], now=st["now"], live=st["live"],
                             pr_number=12 if st["status"] == "pr_open" else 0, pr_url="https://github.com/meghana/shop-api/pull/12" if st["status"] == "pr_open" else "",
                             ci={"state": "success"} if st["status"] == "pr_open" else {}, run_at=st["run_at"] if st["running"] else ""))

    def revise(r):
        st["posts"].append(r.request.post_data_json)
        time.sleep(0.9)                                                  # the server takes a moment: her words must already be on the page
        st["steps"] = st["steps"] + [{"k": "note", "text": r.request.post_data_json["text"], "her": True, "at": _at(1), "n": len(st["steps"])}]
        st["running"], st["status"], st["now"] = True, "new", "Reading the code"
        r.fulfill(json={"ok": True})
    pg.route("**/api/devsahayak", lambda r: r.fulfill(json={**OV, "tasks": [_task(steps=[], running=st["running"], status=st["status"])]}))
    pg.route("**/api/devsahayak/tasks/dt1", dt1)
    pg.route("**/api/devsahayak/tasks/dt1/bg/revise", revise)
    pg.goto(base + "/console/code#/s/dt1")
    pg.wait_for_selector("#hcdCol .hck-work")
    # 1. what was already there: drawn whole, the working row is the kit's with the server's step and clock
    t = pg.evaluate(THREAD)
    assert t["kit"] and t["bub"] == [HER] and t["txt"] == [SAY0] and t["landing"] == 0, t
    assert t["kids"] == ["her", "say", "rows", "work"] and t["old"] == 0 and t["acts"] == [], t          # no Copy mid-turn, no old dot row
    assert t["label"] == "Reading app/cart.py", t
    pg.wait_for_function("() => /^1m \\d\\ds$/.test(document.querySelector('#hcdCol .hck-secs').textContent)")   # counts from run_at (65 s ago), not from now
    feed = pg.locator("#hcdCol").text_content()
    assert "Read 2 files, searched 1 time" in feed                                                     # the page's own step rows are still there
    pg.evaluate("() => { window.__bub = document.querySelector('#hcdCol .hck-bub'); }")
    _shot(pg, "ck-1-working")
    # 2. Hoola says something new: it LANDS word by word under the work that came before it, which folds into "Worked for"
    st["steps"] = STEPS + MORE
    st["now"] = "Editing tests/test_cart.py"
    full = pg.evaluate("s => { const d = document.createElement('div'); d.innerHTML = HoolaMD.render(s, false); return d.textContent; }", SAY1)
    pg.wait_for_function("n => { const x = document.querySelectorAll('#hcdCol .hck-txt'); return x.length === 2 && x[1].textContent.length > 0 && x[1].textContent.length < n; }",
                         arg=len(full), timeout=12000)                                                   # part of it is on the page: it is landing
    mid = pg.evaluate(THREAD)
    assert mid["same"] and mid["txt"][0] == SAY0 and mid["landing"] > 0, mid                             # the thread was not rebuilt; the new words fade in
    pg.wait_for_function("s => { const x = document.querySelectorAll('#hcdCol .hck-txt'); return x.length === 2 && x[1].textContent === s; }", arg=full, timeout=20000)
    pg.wait_for_function("() => document.querySelector('#hcdCol .hck-work:not([hidden]) .hck-label')")
    t = pg.evaluate(THREAD)
    assert t["kids"] == ["her", "say", "fold", "say", "rows", "work"], t                                 # in the order it happened, one turn
    assert t["folds"] and t["folds"][0].startswith("Worked for ") and t["label"] == "Editing tests/test_cart.py" and t["same"], t
    assert pg.locator("#hcdCol .hck-txt strong, #hcdCol .hck-txt b").count() >= 1                        # the kit's markdown (was plain text)
    assert pg.locator("#hcdCol .hcd-wgrp .hcd-diff span.add").count() == 2                                # the edit keeps its diff
    _shot(pg, "ck-2-landed")
    # 3. the words being written right now show before their step is saved, and the saved step continues them
    st["live"] = "Fixed. `total()` returns the sum,"
    pg.wait_for_function("() => { const x = document.querySelectorAll('#hcdCol .hck-txt'); return x.length === 3 && x[2].textContent.startsWith('Fixed.'); }", timeout=12000)
    st["steps"], st["live"], st["running"], st["status"], st["now"] = STEPS + MORE + LAST, "", False, "pr_open", ""
    pg.wait_for_selector("#hcdCol .hck-acts", timeout=20000)
    t = pg.evaluate(THREAD)
    assert len(t["txt"]) == 3 and t["txt"][2].startswith("Fixed.") and t["txt"][2].endswith("the new test passes."), t   # one reply, not two
    assert t["kids"] == ["her", "say", "fold", "say", "fold", "say", "acts"] and t["acts"] == ["copy", "aloud"] and t["same"], t
    assert pg.locator("#hcdCol .hck-work").count() == 0 and pg.locator("#hcdCol .hcd-recap").count() == 1   # the cards sit under the thread
    assert "CI passed. Merging is your tap." in pg.locator("#hcdCol .hcd-tail").text_content()
    _shot(pg, "ck-3-done")
    # 4. her follow-up shows the moment she sends, and the step that carries it is that same bubble
    pg.locator("#hcdNote").click()
    pg.keyboard.type("Also treat None like an empty cart")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.querySelectorAll('#hcdCol .hck-bub').length === 2", timeout=700)   # before the server answered
    assert pg.locator("#hcdNote").input_value() == "" and st["posts"] == [] or st["posts"][0]["text"] == "Also treat None like an empty cart"
    pg.wait_for_selector("#hcdCol .hck-work", timeout=12000)
    t = pg.evaluate(THREAD)
    assert t["bub"] == [HER, "Also treat None like an empty cart"] and t["kids"][-3:] == ["say", "her", "work"] and t["acts"] == [], t
    assert t["same"], t
    # 5. another transcript view draws the same thread again, whole
    pg.locator("[data-menu='title']").click()
    pg.get_by_role("menuitemradio", name="Verbose").or_(pg.get_by_text("Verbose", exact=True)).first.click()
    pg.wait_for_function("() => !document.querySelector('#hcdCol .hcd-wgrp > .hck-fold') && document.querySelectorAll('#hcdCol .hck-txt').length === 3")
    t = pg.evaluate(THREAD)
    assert t["landing"] == 0 and t["bub"] == [HER, "Also treat None like an empty cart"] and pg.locator("#hcdCol .hcd-diff span.add").first.is_visible(), t
    pg.locator("[data-menu='title']").click()
    pg.get_by_text("Normal", exact=True).first.click()
    assert not errs, errs
    ctx.close()


def test_a_finished_session_opens_whole_in_light_and_dark(arena_server):  # noqa: F811
    for dark in (False, True):
        base, ctx, pg, errs = _page(arena_server, dark=dark)
        done = _task(steps=STEPS + MORE + LAST, running=False, status="pr_open", pr_number=12, pr_url="https://github.com/meghana/shop-api/pull/12",
                     ci={"state": "success"}, run_at="", explain=SAY2, files=[{"path": "tests/test_cart.py", "added": 4, "removed": 0}])
        pg.route("**/api/devsahayak", lambda r: r.fulfill(json={**OV, "tasks": [done]}))
        pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=done))
        pg.goto(base + "/console/code#/s/dt1")
        pg.wait_for_selector("#hcdCol .hck-acts")
        t = pg.evaluate(THREAD)
        assert t["kids"] == ["her", "say", "fold", "say", "fold", "say", "acts"] and t["landing"] == 0 and len(t["txt"]) == 3, t   # whole, nothing re-lands; the answer is not said twice
        assert t["acts"] == ["copy", "aloud"] and t["old"] == 0, t
        # the reply is the kit's: Literata 16 / 1.5 with its paragraph gap; her bubble 16 / 1.5; 44px between turns, 12px inside one
        got = pg.evaluate("""() => { const cs = (s, p) => getComputedStyle(document.querySelector(s))[p];
          const txt = document.querySelector('#hcdCol .hck-txt'), ho = document.querySelector('#hcdCol .hck-ho'), col = document.querySelector('#hcdCol');
          const p = document.createElement('div'); p.className = 'hck-txt textmd'; p.innerHTML = '<p>a</p><p>b</p><p><em>i</em> <code>c</code></p>'; ho.append(p);
          const out = {font: cs('#hcdCol .hck-txt', 'fontFamily'), size: cs('#hcdCol .hck-txt', 'fontSize'), lh: cs('#hcdCol .hck-txt', 'lineHeight'), bub: cs('#hcdCol .hck-bub', 'fontSize'),
            gap: getComputedStyle(col).rowGap, inner: getComputedStyle(ho).rowGap, para: getComputedStyle(p.firstChild).marginBottom, em: getComputedStyle(p.querySelector('em')).fontStyle,
            code: getComputedStyle(p.querySelector('code')).paddingLeft, ink: cs('#hcdCol .hck-txt', 'color'), bubbg: cs('#hcdCol .hck-bub', 'backgroundColor')};
          p.remove(); return out; }""")
        assert "Literata" in got["font"] and got["size"] == "16px" and got["lh"] == "24px" and got["bub"] == "16px", got
        assert got["gap"] == "44px" and got["inner"] == "12px" and got["para"] == "16px" and got["em"] == "italic" and got["code"] == "4px", got
        lum = lambda c: sum(int(x) for x in re.findall(r"\d+", c)[:3])                                  # noqa: E731
        assert (lum(got["ink"]) > 600) == dark and (lum(got["bubbg"]) < 200) == dark, got               # the page's own tokens, in both themes
        pg.locator("#hcdCol .hcd-wgrp > .hck-fold > summary").first.click()                               # the fold opens onto the page's own rows
        assert pg.locator("#hcdCol .hcd-wgrp > .hck-fold .hcd-step, #hcdCol .hcd-wgrp > .hck-fold .hcd-fold").first.is_visible()
        _shot(pg, "ck-4-done-dark" if dark else "ck-4-done-light")
        assert not errs, errs
        ctx.close()


PROJ = {"id": "p1", "name": "Clinic booking app", "client": "Dr Rao", "phase": "build", "phase_label": "Building", "paused": False, "state": "run", "pct": 40,
        "sub": "Dr Rao", "gate": "", "spent_inr": 120, "cap_inr": 5000, "archived": False}


def _agent_view(chat, running=False, now=""):
    return {"project": PROJ, "role": "backend", "does": "Builds the server side.", "kind": "build", "repo": "meghana/clinic-api", "branch": "hoola/auto-clinic",
            "agent": {"role": "backend", "label": "Backend agent", "state": "working" if running else "done", "since": _at(-125), "tasks": 3, "done": 1, "pct": 33, "share": 20, "cost_inr": 12},
            "tasks": [{"id": "t1", "seq": 1, "title": "Booking model", "state": "done", "role": "backend", "sprint": 1}], "current": None,
            "session": {"id": "dt9", "status": "new", "now": now, "live": "", "files": [], "running": running, "question": "", "model": "Qwen 3.8 27B",
                        "steps": [{"k": "read", "path": "app/models.py", "at": _at(-30)}]} if running else {},
            "chat": chat, "proof": {"done": 1, "prs": 1, "added": 40}}


def test_the_auto_agent_chat_and_the_intake_talk_are_the_kit(arena_server):  # noqa: F811
    base, ctx, pg, errs = _page(arena_server)
    chat = [{"who": "you", "text": "Use UUIDs for booking ids", "tag": "", "at": _at(-300)},
            {"who": "agent", "text": "Noted. I will use **UUIDs** for every booking id.", "tag": "Applied to task 1", "at": _at(-290)}]
    st = {"chat": list(chat), "running": False, "talk": 0}

    def message(r):
        text = r.request.post_data_json["text"]
        time.sleep(1.0)
        st["chat"] = st["chat"] + [{"who": "you", "text": text, "tag": "", "at": _at(2)},
                                   {"who": "agent", "text": "Yes. A cancelled booking keeps its row, with a cancelled_at time, so the clinic can see it later.", "tag": "", "at": _at(3)}]
        r.fulfill(json={"ok": True})

    held = []                                    # the reply is held until the test has looked at the working row (a sleep here would freeze the test too)

    def talk(r):
        st["talk"] += 1
        held.append(r)

    def release():
        for _ in range(100):
            if held:
                break
            pg.wait_for_timeout(50)
        r = held.pop(0)
        said = r.request.post_data_json.get("said", "")
        if not said:
            return r.fulfill(json={"reply": "Hello. I will ask a few questions about the clinic app. What is the main goal of the project?", "speak": "", "got": [],
                                   "next": {"key": "goal", "q": "What is the main goal?", "choices": []}, "answered": 0, "of": 30, "complete": False})
        r.fulfill(json={"reply": "Thank you. Who will use the app day to day?", "speak": "", "got": [{"q": "Main goal", "value": said}],
                        "next": {"key": "users", "q": "Who will use it?", "choices": ["Patients", "Staff"]}, "answered": 1, "of": 30, "complete": False})
    pg.route("**/api/devsahayak", lambda r: r.fulfill(json={**OV, "tasks": []}))
    pg.route("**/api/auto/projects", lambda r: r.fulfill(json={"projects": [PROJ], "live_limit": 2}))
    pg.route("**/api/auto/projects/p1", lambda r: r.fulfill(json=PROJ))
    pg.route("**/api/auto/projects/p1/agents/backend", lambda r: r.fulfill(json=_agent_view(st["chat"], st["running"], "Running the unit tests" if st["running"] else "")))
    pg.route("**/api/auto/projects/p1/agents/backend/message", message)
    pg.route("**/api/auto/projects/p1/talk", talk)
    # ---- the agent chat
    pg.goto(base + "/console/code#/auto/p1/agent/backend")
    pg.wait_for_selector("#hcaChat .hck-acts")
    a = pg.evaluate("""() => { const r = document.querySelector('#hcaChat'); return {kit: r.classList.contains('hck'), bub: [...r.querySelectorAll('.hck-bub')].map(e => e.textContent),
      txt: [...r.querySelectorAll('.hck-txt')].map(e => e.textContent), landing: r.querySelectorAll('.hck-txt .w').length, acts: [...r.querySelectorAll('.hck-acts [data-act]')].map(b => b.dataset.act),
      tag: r.querySelector(".hck-ho .hca-x").textContent.trim(), bar: !!document.querySelector('#hcaBar.hck-bar textarea'), work: r.querySelectorAll('.hck-work').length}; }""")
    assert a["kit"] and a["bub"] == ["Use UUIDs for booking ids"] and a["txt"] == ["Noted. I will use UUIDs for every booking id."] and a["landing"] == 0, a   # history: whole
    assert a["acts"] == ["copy", "aloud"] and a["tag"] == "Applied to task 1" and a["bar"] and a["work"] == 0, a
    pg.evaluate("() => { window.__bub = document.querySelector('#hcaChat .hck-bub'); }")
    pg.locator("#hcaBar textarea").fill("What happens to a cancelled booking?")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.querySelectorAll('#hcaChat .hck-bub').length === 2 && !!document.querySelector('#hcaChat .hck-work .hck-label')", timeout=800)   # at once
    assert pg.locator("#hcaChat .hck-work .hck-label").text_content() == "Thinking…" and pg.locator("#hcaChat .hck-acts").count() == 0
    _shot(pg, "ck-5-agent-thinking")
    pg.wait_for_function("() => { const x = document.querySelectorAll('#hcaChat .hck-txt'); return x.length === 2 && x[1].querySelectorAll('.w').length > 0; }", timeout=12000)   # the reply lands
    pg.wait_for_selector("#hcaChat .hck-acts", timeout=20000)
    a = pg.evaluate("""() => { const r = document.querySelector('#hcaChat'); return {bub: [...r.querySelectorAll('.hck-bub')].map(e => e.textContent), n: r.querySelectorAll('.hck-txt').length,
      last: r.querySelector('.hck-ho:last-of-type .hck-txt').textContent, same: window.__bub === r.querySelector('.hck-bub'), work: r.querySelectorAll('.hck-work').length}; }""")
    assert a["bub"] == ["Use UUIDs for booking ids", "What happens to a cancelled booking?"] and a["n"] == 2 and a["same"] and a["work"] == 0, a   # her bubble once, nothing rebuilt
    assert a["last"].endswith("so the clinic can see it later."), a
    # the agent's own work shows as the kit's working row, with the step it is on
    st["running"] = True
    pg.wait_for_function("() => (document.querySelector('#hcaChat .hck-work .hck-label') || {}).textContent === 'Running the unit tests'", timeout=12000)
    assert pg.locator("#hcaSess .hca-sess").count() == 1 and pg.locator(".hca-live, .hca-you, .hca-composer").count() == 0
    _shot(pg, "ck-6-agent-working")
    # ---- the intake talk: one POST a turn - the working row, then the reply lands
    pg.goto(base + "/console/code#/auto/p1/talk")
    pg.wait_for_selector("#hcaTalkList .hck-work")
    assert pg.locator("#hcaTalkList .hck-work .hck-label").text_content() == "Thinking…" and pg.locator("#hcaTalkBar .go").is_disabled()   # no Stop to offer: Send waits
    release()
    pg.wait_for_selector("#hcaTalkList .hck-acts", timeout=20000)
    assert pg.locator("#hcaTalkList .hck-txt").text_content().startswith("Hello. I will ask a few questions")
    assert pg.locator("#hcaAloud").is_checked() and "0 of 30 answered" in pg.locator("#hcaTalkSide").text_content()   # her read-aloud switch and the side panel are still there
    pg.locator("#hcaTalkBar textarea").fill("Patients book a doctor's slot from their phone")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.querySelectorAll('#hcaTalkList .hck-bub').length === 1 && !!document.querySelector('#hcaTalkList .hck-work')", timeout=800)
    release()
    pg.wait_for_selector("#hcaTalkList .hca-got", timeout=20000)
    pg.wait_for_selector("#hcaTalkList .hck-acts")
    k = pg.evaluate("""() => { const r = document.querySelector('#hcaTalkList'); return {kit: r.classList.contains('hck'), n: r.querySelectorAll('.hck-txt').length,
      got: r.querySelector('.hca-got').textContent, acts: [...r.querySelectorAll('.hck-acts [data-act]')].map(b => b.dataset.act), kids: [...r.lastElementChild.children].map(e => e.className.split(' ')[0])}; }""")
    assert k["kit"] and k["n"] == 2 and "Main goal - Patients book" in k["got"] and k["acts"] == ["copy", "aloud"], k
    assert k["kids"] == ["hck-txt", "hca-gots", "hck-acts"], k                                           # what it recorded sits under its words, the actions last
    assert "1 of 30 answered" in pg.locator("#hcaTalkSide").text_content() and st["talk"] == 2
    _shot(pg, "ck-7-talk")
    assert not errs, errs
    ctx.close()


def _intake(answered=0, found=None):
    f = lambda key, q, value="", state="open": {"key": key, "q": q, "value": value, "state": state, "source_ref": "the talk"}   # noqa: E731
    goal = f("goal", "What is the main goal of the project?", found or "", "found" if found else "open")
    return {"project": "Clinic booking app", "client": "Dr Rao", "pct": round(100 * answered / 3), "answered": answered, "of": 3, "can_answer": True, "signed": "",
            "sections": [{"name": "Basics", "fields": [goal, f("users", "Who will use it?"), f("date", "When should it be ready?")]}],
            "check": [goal] if found else [], "msgs": [], "next": {"key": "users" if found else "goal", "q": "Who will use it?" if found else "What is the main goal of the project?",
                                                                 "choices": [], "section": "Basics", "state": "open"}}


def test_the_client_intake_talk_is_the_kit(arena_server):  # noqa: F811
    base, browser, key = arena_server
    tok = "t" * 32
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")              # a visitor with a dark device: the page stays light, and so does the kit
    pg = ctx.new_page()
    errs, st = [], {"found": None, "gets": 0}
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def data(r):
        st["gets"] += 1
        r.fulfill(json=_intake(1 if st["found"] else 0, st["found"]))

    held = []                                    # the reply is held until the test has looked at the working row (a sleep here would freeze the test too)

    def talk(r):
        held.append(r)

    def release():
        for _ in range(100):
            if held:
                break
            pg.wait_for_timeout(50)
        r = held.pop(0)
        said = r.request.post_data_json.get("said", "")
        if not said:
            return r.fulfill(json={"reply": "Hello Dr Rao. Let us plan the app together. What is the **main goal** of the project?", "speak": "", "got": [], "answered": 0, "of": 3, "complete": False})
        st["found"] = said
        r.fulfill(json={"reply": "Thank you, I have noted that. Who will use the app day to day?", "speak": "", "got": [{"q": "Main goal", "value": said}], "answered": 1, "of": 3, "complete": False})
    pg.route(f"**/api/auto/c/{tok}", data)
    pg.route(f"**/api/auto/c/{tok}/talk", talk)
    r = pg.goto(base + "/auto/intake/" + tok)
    assert "script-src 'self'" in r.headers["content-security-policy"]                                   # the kit's files are this server's own
    pg.get_by_role("button", name="Talk instead of typing").click()
    pg.wait_for_selector("#ci-talk-thread .hck-work")
    assert pg.locator("#ci-talk-thread .hck-label").text_content() == "Thinking…" and pg.locator("#ci-talk-bar .go").is_disabled()
    release()
    pg.wait_for_function("() => document.querySelectorAll('#ci-talk-thread .hck-txt .w').length > 0", timeout=12000)   # the reply lands
    pg.wait_for_selector("#ci-talk-thread .hck-acts", timeout=20000)
    k = pg.evaluate("""() => { const r = document.querySelector('#ci-talk-thread'), cs = (e, p) => getComputedStyle(e)[p]; window.__root = r;
      return {kit: r.classList.contains('hck'), txt: r.querySelector('.hck-txt').textContent, bold: !!r.querySelector('.hck-txt strong, .hck-txt b'),
        acts: [...r.querySelectorAll('.hck-acts [data-act]')].map(b => b.dataset.act), font: cs(r.querySelector('.hck-txt'), 'fontFamily'), size: cs(r.querySelector('.hck-txt'), 'fontSize'),
        ink: cs(r.querySelector('.hck-txt'), 'color'), bar: !!document.querySelector('#ci-talk-bar.hck-bar textarea'), old: document.querySelectorAll('.ci-tb').length}; }""")
    assert k["kit"] and k["txt"].startswith("Hello Dr Rao.") and k["bold"] and k["acts"] == ["copy", "aloud"] and k["bar"] and k["old"] == 0, k
    assert "Literata" in k["font"] and k["size"] == "16px" and sum(int(x) for x in re.findall(r"\d+", k["ink"])[:3]) < 150, k   # 16px serif, dark ink on the light page
    gets = st["gets"]
    pg.locator("#ci-talk-bar textarea").fill("Patients book a slot from their phone")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.querySelectorAll('#ci-talk-thread .hck-bub').length === 1 && !!document.querySelector('#ci-talk-thread .hck-work')", timeout=800)   # her words at once
    release()
    pg.wait_for_selector("#ci-talk-thread .ci-tgot", timeout=20000)
    pg.wait_for_selector("#ci-talk-thread .hck-acts")
    k = pg.evaluate("""() => { const r = document.querySelector('#ci-talk-thread'); return {same: window.__root === r && r.isConnected, n: r.querySelectorAll('.hck-txt').length,
      bub: [...r.querySelectorAll('.hck-bub')].map(e => e.textContent), got: r.querySelector('.ci-tgot').textContent, count: document.querySelector('.ci-talk-tt span').textContent,
      check: document.querySelector('.ci-found') ? document.querySelector('.ci-found').textContent : ''}; }""")
    assert st["gets"] > gets and k["same"], k                 # the answers below refreshed, and the thread was not taken out of the page for it
    assert k["n"] == 2 and k["bub"] == ["Patients book a slot from their phone"] and "Main goal" in k["got"] and k["count"] == "1 of 3 answered", k
    assert "Patients book a slot from their phone" in k["check"], k
    _shot(pg, "ck-8-client-intake")
    # closing and opening the panel keeps the conversation
    pg.get_by_role("button", name="Close").click()
    assert pg.locator("#ci-talk").count() == 0
    pg.get_by_role("button", name="Talk instead of typing").click()
    assert pg.locator("#ci-talk-thread .hck-txt").count() == 2 and pg.locator("#ci-talk-thread .hck-bub").count() == 1
    assert not errs, errs
    ctx.close()


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
