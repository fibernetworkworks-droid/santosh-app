"""HOOLA CHAT KIT in the small panels (owner: "EVERY CHAT SECTION MUST HAVE SAME FEATURE, DESIGN AND TEXT LANDING, TIMING,
SPACING" -> prototype -> "GO"). Six panels mount the ONE shared thread (static/console/chatkit.js + chatkit.css):

  Hoola Computer chats   console/computer.js        polls -> t.sync, the working row carries the PC task's real step
  AI Apps > Preview      console/aiapps.js          one POST -> t.her / t.begin / t.final / t.end
  the public AI app page aiapps/public.py           her CUSTOMERS' page: the kit from /static, nothing from another site
  Lab "Ask Hoola"        prayog/studio/studio.js    the dock in the lab
  Video Learner run      console/seekh.js           "Hoola says" = the run's replies, the page keeps its own step list
  Hoola Design Ask Hoola console/design/hd-ai.js    her ask, the working row with the clock, what Hoola did lands

Static checks hold the wiring; the walks open each panel in a real browser against the real server.
Set CHATKIT_SHOTS=<folder> to keep a picture of every walk."""
from __future__ import annotations

from tests._hq_wiring import pick_low, quality_under, real_tiers  # v0.999.33 WIRED
import json
import os
import re
import time
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

APP = Path(__file__).resolve().parents[1] / "app"
STATIC = APP / "static"
CON = STATIC / "console"
KIT = ("md.js", "mark.js", "stream.js", "chatkit.js")


def _r(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _shot(pg, name: str) -> None:
    d = os.environ.get("CHATKIT_SHOTS")
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(d) / f"{name}.png"))


def _order(html: str, names, prefix="/static/console/") -> None:
    at = [html.index(prefix + n) for n in names]
    assert at == sorted(at), f"{names} must load in this order"


# ------------------------------------------------------------------------------------------------ the wiring
def test_every_page_loads_the_kit_before_its_panel():
    # Hoola Computer: its own page, its own stamp
    h = _r(CON / "computer.html")
    stamp = re.search(r"computer\.js\?v=([0-9.]+)", h).group(1)
    for f in ("chatkit.css", *KIT, "computer.css", "computer.js"):
        assert f"/static/console/{f}?v={stamp}" in h, f
    _order(h, (*KIT, "computer.js"))
    _order(h, ("chatkit.css", "computer.css"))               # the page's colours for the kit win over the kit's defaults
    assert "family=Literata" in h
    # the console page (AI Apps, Video Learner): the kit after stream.js, before the page scripts
    h = _r(CON / "v2.html")
    stamp = re.search(r"console/v2\.js\?v=([0-9.]+)", h).group(1)
    assert f'href="/static/console/chatkit.css?v={stamp}"' in h and f'src="/static/console/chatkit.js?v={stamp}"' in h
    _order(h, (*KIT, "seekh.js", "aiapps.js", "v2.js"))
    assert h.count("chatkit.js") == 1 and h.count("chatkit.css") == 1 and "Literata" in h
    # the lab
    h = _r(STATIC / "prayog" / "lab.html")
    stamp = re.search(r"studio/studio\.js\?v=([0-9.]+)", h).group(1)
    for f in ("chatkit.css", *KIT):
        assert f"/static/console/{f}?v={stamp}" in h, f
    assert h.index("/static/console/chatkit.css") < h.index("studio/studio.css")
    assert h.index("/static/console/chatkit.js") < h.index("studio/studio.js") and "family=Literata" in h
    # Hoola Design
    h = _r(CON / "design" / "design.html")
    stamp = re.search(r"hd-ai\.js\?v=([0-9.]+)", h).group(1)
    for f in ("chatkit.css", *KIT):
        assert f"/static/console/{f}?v={stamp}" in h, f
    assert h.index("/static/console/chatkit.js") < h.index("design/hd-ai.js")
    assert h.index("/static/console/chatkit.css") < h.index("design/design-ai.css") and "family=Literata" in h


def test_the_panels_mount_the_kit_and_their_old_waiting_marks_are_gone():
    js = _r(CON / "computer.js")
    assert "HoolaChat.mount($('#thread')" in js and "HoolaChat.bar($('#bar')" in js and "ST.thread.sync({key: ST.chat" in js
    assert "ST.thread.her(say, {pending: true" in js, "her message is on screen the moment she sends"
    assert "/stop`" in js and "onStop: stopTurn" in js, "Send turns into Stop only because this chat has a real stop route"
    assert "m-work" not in js and "Hoola is working…" not in js and 'class="m-a"' not in js and 'id="sendBtn"' not in js
    css = _r(CON / "computer.css")
    assert ".m-work" not in css and "@keyframes hcp" not in css and ".hc-box" not in css

    js = _r(CON / "aiapps.js")
    assert "window.HoolaChat.mount(root, {scroller: scroll})" in js and "window.HoolaChat.bar(barHost" in js
    assert "t.her(text); t.begin(" in js and "await t.final((r && r.reply) || ''); t.end();" in js
    prev = js[js.index("function tabPreview(body)"):js.index("function tabChannels(body)")]
    assert "aia-msg" not in js and "text: '…'" not in prev and "textContent" not in prev
    assert "OUT_WORD[r && r.outcome]" in js and "'Source: ' + x.title" in js, "where the answer came from stays with the reply"
    assert "onStop" not in js and ".working = " not in js, "a preview answer cannot be stopped, so no Stop button is shown"

    js = _r(STATIC / "prayog" / "studio" / "studio.js")
    assert "window.HoolaChat.mount(thread, { scroller: msgs })" in js and "window.HoolaChat.bar(barHost" in js
    assert "T.her(text)" in js and "T.final(String(res.d.answer || ''))" in js
    assert "bubble('ai', 'Thinking" not in js and "'msg ' + cls" not in js
    assert "loadKit(function (ok) { if (ok && !S.dead) buildAsk(S, lab, exp); });" in js, "the bench runs without the kit (offline); a cached old lab page fetches it"
    css = _r(STATIC / "prayog" / "studio" / "studio.css")
    assert ".msg.ai" not in css and ".compose textarea" not in css

    js = _r(CON / "seekh.js")
    assert "window.HoolaChat.mount(says, {startedAt: RUN.t0})" in js and "SAYS.sync({key: RUN.cid, messages: replies" in js
    assert "reply.slice(0, 900)" not in js and "skv-replybox" not in js, "the whole reply, in markdown, not the first 900 characters"
    assert 'id="skvActs"' in js, "the steps stay in the page's own list"
    assert "steps:" not in js[js.index("SAYS.sync({key: RUN.cid, messages: replies"):][:260], "and are not repeated as kit steps"

    js = _r(CON / "design" / "hd-ai.js")
    assert "window.HoolaChat.mount(root, {scroller: st.box})" in js and "T.her(prompt); T.begin(" in js and "await T.final(said)" in js
    assert "hdai-spin" not in js and "hdai-busy" not in js and "startClock" not in js and "secsText" not in js
    css = _r(CON / "design" / "design-ai.css")
    assert "hdai-spin" not in css and "hdai-pulse" not in css


def test_each_page_gives_the_kit_its_colours_and_the_soft_landing():
    """A page whose tokens are not the console's sets the kit's --hck-* in ITS OWN css; and outside the console page the
    kit's word animation needs a rule of the page's (in chatkit.css the duration variable shares its name with a colour
    token, which switches the animation off), so each page states the main chat's .46 s itself."""
    word = re.compile(r"\.hck-txt \.w\s*\{\s*animation:\s*hckWord \.46s ease both;?\s*\}")
    for f, tokens in ((CON / "computer.css", ("--hck-bubble:var(--soft)", "--hck-violet:var(--acc)", "--acc-rgb:156 136 255")),
                      (STATIC / "prayog" / "studio" / "studio.css", ("--hck-violet: var(--accent)", "--hck-fb: var(--f-ui)", "--acc-rgb: 157 140 242")),
                      (CON / "design" / "design-ai.css", ("--hck-bubble:var(--sunk)",)),
                      (APP / "aiapps" / "public.py", ("--hck-violet:var(--acc)", "--hck-pill:var(--acc)", "--acc-rgb:91 63 224"))):
        css = _r(f)
        assert word.search(css), f"{f.name}: the words land out of a soft focus over .46 s"
        assert "prefers-reduced-motion" in css
        for t in tokens:
            assert t in css, (f.name, t)
    css = _r(CON / "v2.css")
    tail = css[css.index("HOOLA CHAT KIT in the console's own panels"):]
    assert css.rstrip().endswith(tail.rstrip()), "appended at the very end, nothing before it changed"
    assert ".aia .hck-txt p{margin:0 0 16px}" in tail and "#app .skv-says" in tail


def test_the_public_page_stays_small_and_safe():
    from app.aiapps import public as P
    page = P.PAGE
    # only Hoola's own files, from /static (the page's CSP allows 'self' and nothing else)
    srcs = re.findall(r'<script src="([^"]+)"', page) + re.findall(r'<link rel="stylesheet" href="([^"]+)"', page)
    assert srcs == [f"/static/console/{f}?v=__KIT__" for f in ("md.js", "mark.js", "stream.js", "chatkit.js", "chatkit.css")]
    assert page.index("chatkit.css") < page.index("<style>"), "the page's own colours for the kit come after the kit's"
    assert "https://" not in page and "//fonts" not in page and "innerHTML" not in page and "insertAdjacentHTML" not in page
    assert "Thinking..." not in page and 'class="dots"' not in page and '"msg ai"' not in page
    assert 'window.HoolaChat.mount(thread,{scroller:log,acts:canCopy?["copy","aloud"]:["aloud"]})' in page
    assert "onStop" not in page and ".working=" not in page, "an answer cannot be stopped, so no Stop button"
    assert '"/feedback"' in page and '"Source: "' in page, "sources and Helpful / Not right stay with each reply"
    assert "default-src 'self' 'unsafe-inline'" in P.page_headers(False)["Content-Security-Policy"]
    assert len(P.kit_stamp()) == 10 and P.kit_stamp() == P.kit_stamp()
    assert 'frame.setAttribute("allow","clipboard-write")' in P.EMBED_JS, "Copy in the website bubble; nothing else is granted"


# ------------------------------------------------------------------------------------------------ the walks
SHAPE = """() => { const q = s => document.querySelectorAll(s);
  const root = document.querySelector('.hck');
  return {root: !!root, tight: !!root && root.classList.contains('hck-tight'), bub: q('.hck-bub').length, txt: q('.hck-txt').length,
    acts: [...q('.hck-acts .hck-ra')].map(b => b.dataset.act), work: [...q('.hck-work')].filter(w => !w.hidden).length,
    label: (document.querySelector('.hck-label') || {}).textContent || '', landing: q('.hck-txt .w').length,
    fold: [...q('.hck-fold .sm')].map(n => n.textContent), last: (q('.hck-txt')[q('.hck-txt').length - 1] || {}).textContent || '',
    go: (document.querySelector('.hck-bar .go') || {getAttribute: () => ''}).getAttribute('aria-label'),
    off: !!(document.querySelector('.hck-bar .go') || {}).disabled,
    font: q('.hck-txt').length ? getComputedStyle(q('.hck-txt')[0]).fontSize + ' ' + getComputedStyle(q('.hck-txt')[0]).lineHeight : '',
    anim: q('.hck-txt .w').length ? getComputedStyle(q('.hck-txt .w')[0]).animationName : ''}; }"""


def _page(browser, key, width=1360, height=860, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme, device_scale_factor=1)
    if key:
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs: list[str] = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    return ctx, pg, errs


def _type(pg, text: str) -> None:
    pg.locator(".hck-bar textarea").fill(text)
    pg.locator(".hck-bar textarea").press("Enter")


LONG = ("The return was filed and the receipt is saved in your folder. " * 3).strip()


def test_hoola_computer_chat_in_a_real_browser(arena_server):  # noqa: F811
    import httpx
    base, browser, key = arena_server
    h = {"Authorization": "Bearer " + key}
    chat = httpx.post(base + "/api/computer/hoola/chats", headers=h, timeout=20).json()["id"]
    for scheme in ("light", "dark"):
        st = {"rows": [{"id": 1, "role": "user", "text": "old ask", "at": "2026-11-18T10:00:00"},
                       {"id": 2, "role": "assistant", "text": "old **answer**", "at": "2026-11-18T10:00:05"}],
              "res": {"status": "done", "needs_you": False, "line": "Done", "made": [], "at": ""}, "run": None, "sent": [], "stopped": 0}
        ctx, pg, errs = _page(browser, key, scheme=scheme)

        def messages(r, _req=None, st=st):
            if r.request.method == "POST":
                body = r.request.post_data_json
                st["sent"].append(body)
                st["rows"].append({"id": 3, "role": "user", "text": body["text"], "at": "2026-11-18T10:01:00"})
                st["res"] = {"status": "working", "needs_you": False, "line": "Working on it", "made": [], "at": ""}
                return r.fulfill(status=202, json={"accepted": True})
            return r.fulfill(json={"messages": st["rows"]})

        def status(r, _req=None, st=st):
            d = r.fetch().json()
            d["hoola"]["running"] = st["run"]
            r.fulfill(json=d)

        def stop(r, _req=None, st=st):
            st["stopped"] += 1
            r.fulfill(json={"stopped": True})
        pg.route(f"**/api/conversations/{chat}/messages*", messages)
        pg.route(f"**/api/conversations/{chat}/result", lambda r, _q=None, st=st: r.fulfill(json=st["res"]))
        pg.route(f"**/api/conversations/{chat}/stop", stop)
        pg.route("**/api/computer", status)
        pg.route("**/api/browser/**", lambda r: r.fulfill(status=404, json={"detail": "no screen"}))
        try:
            pg.goto(f"{base}/console/computer#/hoola/{chat}")
            pg.wait_for_selector(".hck-txt")
            o = pg.evaluate(SHAPE)
            assert o["root"] and o["tight"] and o["bub"] == 1 and o["txt"] == 1 and o["landing"] == 0, o   # history: whole, not re-landed
            assert o["acts"] == ["copy", "aloud"] and o["work"] == 0 and o["go"] == "Send" and o["off"], o
            assert o["font"] == "16px 24px", o
            assert pg.locator(".m-work, .m-a, .m-u, #sendBtn").count() == 0
            _type(pg, "File my GST return")
            pg.wait_for_function("() => document.querySelectorAll('.hck-bub').length === 2")           # at once, before any poll
            pg.wait_for_selector(".hck-work")
            st["run"] = {"session_id": "pcop_t1", "task": "File my GST return", "step": 2, "steps_max": 64, "status": "working",
                         "thought": "Opening the GST portal", "pc": "Hoola PC 1", "conv": chat, "from": "", "started": time.time() - 5}
            pg.wait_for_function("() => (document.querySelector('.hck-label') || {}).textContent === 'Opening the GST portal'", timeout=15000)
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 2 and o["work"] == 1 and o["acts"] == [] and o["go"] == "Stop", o   # her message once; no actions under an old reply
            assert pg.locator(".hck-work .hck-mark svg, .hck-work .hck-mark .hm3").count() >= 1
            assert st["sent"][0]["text"] == "File my GST return" and st["sent"][0]["client_id"].startswith("hc")
            if scheme == "light":
                _shot(pg, "computer-working")
            pg.locator(".hck-bar .go").click()                                                   # Stop is real: this chat's stop route
            pg.wait_for_function("() => true", timeout=2000)
            st["run"] = None
            st["rows"].append({"id": 4, "role": "assistant", "text": LONG, "at": "2026-11-18T10:02:00"})
            st["res"] = {"status": "done", "needs_you": False, "line": "Done", "made": [], "at": ""}
            pg.wait_for_selector(".hck-txt .w", timeout=15000)
            mid = pg.evaluate(SHAPE)
            assert mid["txt"] == 2 and mid["landing"] > 0 and mid["anim"] == "hckWord", mid       # landing word by word, soft focus
            pg.wait_for_selector(".hck-acts", timeout=15000)
            o = pg.evaluate(SHAPE)
            assert o["last"].strip() == LONG and o["work"] == 0 and o["acts"] == ["copy", "aloud"] and o["go"] == "Send", o
            assert o["fold"] and o["fold"][0].startswith("Worked for "), o                      # the PC task's steps folded
            assert st["stopped"] == 1
            _shot(pg, f"computer-{scheme}")
            assert not errs, errs
        finally:
            ctx.close()


def _console_view(pg, base, view, arg=""):
    pg.goto(f"{base}/console/?v={view}" + (f"&a={arg}" if arg else ""))
    pg.wait_for_selector(f"#{view}", state="visible")


def test_ai_apps_preview_in_a_real_browser(arena_server):  # noqa: F811
    from app.aiapps import store as ST
    base, browser, key = arena_server
    a = ST.create("default", "Sharma Kirana", soul={"name": "Sharma Kirana", "about": "Grocery shop in Pune", "facts": ["Open 9 am to 9 pm"],
                                                     "opening": "Namaste! Ask me anything.", "suggested": ["Timings?"]})
    asked = []
    for scheme in ("light", "dark"):
        ctx, pg, errs = _page(browser, key, scheme=scheme)

        held = []                                             # the answer is held back until the working row was seen
        pg.route("**/api/aiapps/*/preview", lambda r: (asked.append(r.request.post_data_json), held.append(r))[0])
        try:
            _console_view(pg, base, "aiapps", a["id"])
            pg.wait_for_selector(".aia-tab")
            pg.get_by_role("tab", name="Preview").click()
            pg.wait_for_selector(".aia-thread .hck-txt")
            o = pg.evaluate(SHAPE)
            assert o["root"] and o["bub"] == 0 and o["txt"] == 1 and o["landing"] == 0 and o["acts"] == ["copy", "aloud"], o   # the opening line, whole
            assert pg.locator(".aia-msg").count() == 0
            _type(pg, "When are you open?")
            pg.wait_for_selector(".hck-work")
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 1 and o["work"] == 1 and o["label"] == "Thinking…" and o["go"] == "Send" and o["off"], o   # no fake Stop: Send is off
            held[0].fulfill(json={"reply": "We are open **9 am to 9 pm**, every day.\n\n<img src=x onerror=window.__pwn=1>", "outcome": "model",
                                  "sources": [{"title": "Shop timings"}], "session_id": "s1"})
            pg.wait_for_selector(".hck-acts", timeout=15000)
            o = pg.evaluate(SHAPE)
            assert o["txt"] == 2 and o["work"] == 0 and o["acts"] == ["copy", "aloud"] and "9 am to 9 pm" in o["last"], o
            assert pg.locator(".hck-txt b").count() == 1 and pg.locator(".hck-txt img").count() == 0 and not pg.evaluate("() => !!window.__pwn")
            meta = pg.locator(".hck-ho .aia-meta").text_content()
            assert "Written from your facts" in meta and "Source: Shop timings" in meta                 # where the answer came from
            assert o["font"] == "16px 24px", o
            _shot(pg, f"aiapps-{scheme}")
            assert not errs, errs
        finally:
            ctx.close()
    assert asked[0]["text"] == "When are you open?"


def test_the_public_ai_app_page_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    from app.aiapps import public as P, runtime as RT, store as ST
    base, browser, _key = arena_server
    monkeypatch.setattr(RT, "ASK", [lambda s, p, n: "We are open 9 am to 9 pm."])
    a = ST.create("default", "Sharma Kirana", soul={"name": "Sharma Kirana", "about": "Grocery shop in Pune", "facts": ["Open 9 am to 9 pm"],
                                                     "opening": "Namaste! Ask me anything.", "suggested": ["Timings?"]})
    ST.publish("default", a["id"], a["draft_hash"])
    code = ST.row("default", a["id"]).code
    P.IP_WINDOW.reset(); P.SESSION_WINDOW.reset()
    for scheme, width in (("light", 900), ("dark", 390)):
        ctx, pg, errs = _page(browser, "", width=width, height=760, scheme=scheme)
        try:
            pg.goto(f"{base}/ai/{code}")
            pg.get_by_role("button", name="I agree").click()
            pg.wait_for_selector(".hck-txt")
            o = pg.evaluate(SHAPE)
            assert o["root"] and o["txt"] == 1 and o["landing"] == 0 and o["acts"] == ["copy", "aloud"], o   # the opening line, whole
            assert o["tight"] == (width < 480), o
            pg.locator(".chips button").first.click()                                           # a suggested question
            pg.wait_for_function("() => document.querySelectorAll('.hck-bub').length === 1")
            pg.wait_for_function("() => document.querySelectorAll('.hck-txt').length === 2", timeout=15000)
            pg.wait_for_selector(".hck-acts", timeout=15000)
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 1 and o["work"] == 0 and o["last"].strip() and o["acts"] == ["copy", "aloud"] and o["font"] == "16px 24px", o
            _type(pg, "Do you deliver?")
            pg.wait_for_function("() => document.querySelectorAll('.hck-bub').length === 2")
            pg.wait_for_function("() => document.querySelectorAll('.hck-acts').length === 1 && document.querySelectorAll('.hck-txt').length === 3", timeout=15000)
            assert pg.locator(".msg, .dots").count() == 0
            _shot(pg, f"public-{scheme}")
            # she comes back: the history is drawn whole, nothing lands again
            pg.reload()
            pg.wait_for_function("() => document.querySelectorAll('.hck-txt').length === 3")
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 2 and o["landing"] == 0 and o["acts"] == ["copy", "aloud"], o
            assert not errs, errs
        finally:
            ctx.close()


def test_the_lab_ask_hoola_dock_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    # the lab draws in 3D: its own browser with a software GPU (what tools/prayog_walk.js uses); that is slow, so the
    # lab is opened once and the dark look is checked on the same page
    try:
        gl = browser.browser_type.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
                                         **({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no Chromium with a software GPU here: {str(e)[:80]}")
    try:
        ctx, pg, errs = _page(gl, key, width=1280, height=820)
        pg.set_default_timeout(90000)
        asked, held = [], []                                  # each answer is held back until the working row was seen
        answer = {"answer": "Because **sin θ ≈ θ** only for small angles.\n\n- keep the swing under 10°\n- time 20 swings"}
        pg.route("**/api/prayog/ask", lambda r: (asked.append(r.request.post_data_json), held.append(r))[0])
        try:
            pg.goto(f"{base}/static/prayog/lab.html?id=simple-pendulum")
            pg.wait_for_selector(".askbtn")
            assert not pg.evaluate("() => window.__studioError || ''")
            pg.locator(".askbtn").click()
            pg.wait_for_selector(".dock .hck-txt")
            o = pg.evaluate(SHAPE)
            assert o["root"] and o["tight"] and o["txt"] == 1 and o["landing"] == 0 and o["acts"] == ["copy", "aloud"], o   # the greeting, whole
            assert pg.locator(".dock .msg").count() == 0
            _type(pg, "Why small angles?")
            pg.wait_for_selector(".hck-work")
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 1 and o["work"] == 1 and o["acts"] == [] and o["go"] == "Send" and o["off"], o   # no fake Stop: Send is off
            held[0].fulfill(json=answer)
            pg.wait_for_selector(".hck-acts")
            o = pg.evaluate(SHAPE)
            assert o["txt"] == 2 and o["work"] == 0 and o["acts"] == ["copy", "aloud"] and o["font"] == "16px 24px", o
            assert pg.locator(".hck-txt b").count() == 1 and pg.locator(".hck-txt li").count() == 2       # the kit's markdown
            assert asked[0]["question"] == "Why small angles?" and asked[0]["lab_id"] == "simple-pendulum"
            pg.locator(".dock .chips button").first.click()                                  # a ready question goes the same way
            pg.wait_for_function("() => document.querySelectorAll('.hck-bub').length === 2")
            pg.wait_for_selector(".hck-work")
            held[1].fulfill(json=answer)
            pg.wait_for_function("() => document.querySelectorAll('.hck-txt').length === 3 && document.querySelectorAll('.hck-acts').length === 1")
            assert len(asked) == 2 and len(asked[1]["turns"]) == 2                            # the earlier turn rides along as before
            _shot(pg, "lab-light")
            light = pg.evaluate("() => getComputedStyle(document.querySelector('.hck-txt')).color")
            pg.emulate_media(color_scheme="dark")
            assert pg.evaluate("() => getComputedStyle(document.querySelector('.hck-txt')).color") != light   # the kit follows the lab's dark tokens
            _shot(pg, "lab-dark")
            assert not errs, errs
        finally:
            ctx.close()
    finally:
        gl.close()


def test_video_learner_run_in_a_real_browser(arena_server):  # noqa: F811
    from tests.test_v0785_video_learner_premium import TASK, WATCHES
    base, browser, key = arena_server
    for scheme in ("light", "dark"):
        ctx, pg, errs = _page(browser, key, scheme=scheme)
        rows = json.loads(json.dumps(WATCHES))
        rows["watches"][1]["run"] = {"cid": "c1", "after": 0, "ts": "2026-11-11T10:00:00", "scored": False}
        task = json.loads(json.dumps(TASK))
        task["run"] = {"cid": "c1", "after": 0, "ts": "2026-11-18T10:00:00", "scored": False}
        title = task.get("title") or ""
        ev = [{"id": 5, "kind": "message", "at": "2026-11-18T10:00:00", "payload": {"role": "user", "text": f'Do the learned task "{title}" now, for real.'}},
              {"id": 6, "kind": "step", "at": "2026-11-18T10:00:02", "payload": {"id": "s1", "label": "Opening the scholarship portal", "state": "done"}},
              {"id": 7, "kind": "message", "at": "2026-11-18T10:00:04", "payload": {"role": "assistant", "text": "I have opened the portal. **Next** I will fill your name."}},
              {"id": 8, "kind": "step", "at": "2026-11-18T10:00:06", "payload": {"id": "s2", "label": "Typing the full name", "state": "running"}}]
        st = {"ev": ev, "busy": True}
        pg.route("**/api/seekh/console/watches", lambda r, _q=None, rows=rows: r.fulfill(json=rows))
        pg.route("**/api/seekh/console/task?id=*", lambda r, _q=None, task=task: r.fulfill(json=task))
        pg.route("**/api/seekh/console/run*", lambda r, _q=None, st=st: r.fulfill(json={"run": {"scored": False}, "waiting": [], "busy": st["busy"]}))
        pg.route("**/api/conversations/c1/timeline*", lambda r, _q=None, st=st: r.fulfill(json={"events": st["ev"]}))
        try:
            pg.goto(base + "/console/")
            pg.wait_for_selector("#composer")
            pg.evaluate("() => document.querySelector('.sn[data-v=\"hire\"]')?.click()")
            pg.wait_for_selector(".ae-seekh")
            pg.locator(".ae-seekh").first.click()
            pg.wait_for_selector("[data-run]")
            pg.locator("[data-run]").first.click()
            pg.wait_for_selector("#skvReply .hck-txt")
            o = pg.evaluate(SHAPE)
            # she came back to a running task: what Hoola already said is drawn whole, the ONE working row has the real step
            assert o["root"] and o["txt"] == 1 and o["landing"] == 0 and o["work"] == 1 and o["label"] == "Typing the full name", o
            assert o["acts"] == [] and pg.locator("#skvReply .hck-txt b").count() == 1 and o["font"] == "16px 24px", o
            assert pg.locator("#skvActs li").count() == 2 and pg.locator("#skvReply .hck-ts").count() == 0   # steps: the page's list only
            assert pg.locator(".skv-replybox").count() == 0
            if scheme == "light":
                _shot(pg, "seekh-working")
            long = ("The form is filled and saved as a draft, nothing was submitted. " * 4).strip() + "\n\n- name typed\n- certificate uploaded"
            st["ev"] = [*ev[:3], {**ev[3], "payload": {**ev[3]["payload"], "state": "done"}},
                        {"id": 9, "kind": "message", "at": "2026-11-18T10:00:20", "payload": {"role": "assistant", "text": long}}]
            st["busy"] = False
            pg.wait_for_selector("#skvReply .hck-txt .w", timeout=15000)
            mid = pg.evaluate(SHAPE)
            assert mid["txt"] == 2 and mid["landing"] > 0, mid                                   # the new reply lands
            pg.wait_for_selector("#skvReply .hck-acts", timeout=20000)
            o = pg.evaluate(SHAPE)
            assert o["work"] == 0 and o["acts"] == ["copy", "aloud"] and "nothing was submitted" in o["last"] and len(o["last"]) > 200, o   # all of it, not 900 characters of plain text
            assert pg.locator("#skvReply .hck-txt li").count() == 2
            pg.wait_for_selector(".skv-verdict")                                                 # the page's own ending is unchanged
            _shot(pg, f"seekh-{scheme}")
            assert not errs, errs
        finally:
            ctx.close()


def test_hoola_design_ask_hoola_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    import httpx
    from app.config import get_settings
    base, browser, key = arena_server
    monkeypatch.setenv("DESIGN_AI_ENGINE", "template")       # Hoola's built-in layouts: a real design with no model here
    get_settings.cache_clear()
    real_tiers(monkeypatch)
    h = {"Authorization": "Bearer " + key}
    r = httpx.post(base + "/api/design/files", headers=h, json={"name": "Kit walk"}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Hoola Design is not on here ({r.status_code})")
    fid = r.json()["id"]
    for scheme in ("light", "dark"):
        ctx, pg, errs = _page(browser, key, scheme=scheme)
        try:
            pg.goto(f"{base}/console/design#/f/{fid}")
            pg.wait_for_selector(".hdai-fab:not([hidden])", timeout=60000)
            pg.locator(".hdai-fab").click()
            pg.wait_for_selector(".hdai-panel .hdai-in")
            quality_under(pg, ".hdai-foot")                               # under Ask Hoola's Design row
            assert pg.locator(".hdai-thread").is_hidden()                                        # nothing said yet: no empty box
            pg.locator(".hdai-in").fill("Diwali sale poster for my sweet shop")
            pg.locator(".hdai-go").click()
            pg.wait_for_selector(".hdai-thread .hck-bub")
            o = pg.evaluate(SHAPE)
            assert o["root"] and o["tight"] and o["bub"] == 1, o                                  # her ask is a bubble
            assert pg.locator(".hdai-spin, .hdai-busy, .hdai-quote").count() == 0
            pg.wait_for_selector(".hdai-thread .hck-acts", timeout=90000)
            o = pg.evaluate(SHAPE)
            assert o["txt"] == 1 and o["work"] == 0 and o["acts"] == ["copy", "aloud"] and o["font"] == "16px 24px", o
            assert re.search(r"(Added .+ in \d+ s\.|\d+ frames added in \d+ s\.)", o["last"]), o   # what Hoola did, as a reply
            assert pg.locator(".hdai-acts button", has_text="Remove").count() == 1                # the result's own buttons stay
            assert pg.locator(".hdai-acts button", has_text="Try again").count() == 1
            _shot(pg, f"design-{scheme}")
            # the panel is redrawn when the selection changes; the thread stays in place (nothing lands twice)
            pg.keyboard.press("Escape")
            pg.wait_for_selector(".hdai-fab:not([hidden])")
            pg.locator(".hdai-fab").click()
            pg.wait_for_selector(".hdai-thread .hck-txt")
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 1 and o["txt"] == 1, o
            assert pg.evaluate("() => [...document.querySelectorAll('.hck-bub, .hck-txt .w')].every(n => getComputedStyle(n).animationName === 'none')")
            # an ask the server refuses: her ask stays, the reason is said in the thread, no empty reply is left behind
            pg.route("**/api/design/files/*/ai", lambda r: r.fulfill(status=502, json={"detail": "Hoola could not reach its design model just now."}))
            pg.locator(".hdai-in").fill("A business card for a boutique")
            pg.locator(".hdai-in").press("Enter")
            pg.wait_for_selector(".hdai-thread .hdai-err")
            o = pg.evaluate(SHAPE)
            assert o["bub"] == 2 and o["txt"] == 1 and o["work"] == 0, o
            assert "could not reach its design model" in pg.locator(".hdai-thread .hdai-err").text_content()
            assert pg.evaluate("() => [...document.querySelectorAll('.hdai-thread .hck-ho')].every(n => n.childElementCount > 0)")
            assert pg.locator(".hdai-in").input_value() == "A business card for a boutique"       # her words are kept to try again
            assert not errs, errs
        finally:
            ctx.close()
    get_settings.cache_clear()
