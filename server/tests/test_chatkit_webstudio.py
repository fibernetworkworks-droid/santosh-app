"""HOOLA CHAT KIT in the Web Studio (owner: "EVERY CHAT SECTION MUST HAVE SAME FEATURE, DESIGN AND TEXT LANDING, TIMING,
SPACING" -> prototype -> "GO"): the site thread, the plan chat and the React app chat are drawn by the one chat kit
(static/console/chatkit.js + chatkit.css) - her bubble, the reply landing at the shared pace, ONE working row with the
real step words and the clock, Copy / Read aloud (and Good answer / Not right on the site thread, whose replies have a
turn the server keeps them for). Everything the Studio hangs on a reply stays: Thought for · steps · credits + Details,
the plan card, Start building, Version N / Undo this change, Edit and resend, the queue, Stop."""
from __future__ import annotations

from tests._hq_wiring import pick_low, quality_under, real_tiers  # v0.999.33 WIRED
import asyncio
import os
import re
import time
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _r(name: str) -> str:
    return (CON / name).read_text(encoding="utf-8")


def test_the_studio_page_loads_the_kit_before_its_panels():
    html = _r("webstudio.html")
    order = [html.index(f"/static/console/{f}") for f in ("md.js", "mark.js", "stream.js", "chatkit.js", "appengine.js", "webstudio.js")]
    assert order == sorted(order), "md, mark, stream, chatkit - then the panels that mount it"
    assert "/static/console/chatkit.css" in html and "Literata" in html
    stamps = set(re.findall(r"/static/console/[\w./-]+\?v=([\d.]+)", html))
    assert len(stamps) == 1, f"one release stamp on every tag: {stamps}"


def test_the_three_panels_mount_the_kit_and_the_old_waiting_markup_is_gone():
    ws, ae = _r("webstudio.js"), _r("appengine.js")
    # the site thread, the plan chat, the React app chat
    assert "window.HoolaChat.mount(root, KOPT)" in ws and "window.HoolaChat.mount(root, {scroller: $('#wsPlanMsgs')})" in ws
    assert "window.HoolaChat.mount(root, AKOPT)" in ae
    assert "window.HoolaChat.bar(host" in ws and "window.HoolaChat.bar(host" in ae, "the plain boxes are the kit's pill"
    # her line at send, the working row, the text so far / the whole reply - through the kit
    for needle in ("K.t.her(", "pending: true", "K.t.sync({key: st.key, messages: st.msgs, working: true, label: workLabel(), steps: newSteps(K)})",
                   "K.t.text(tx)", "K.t.begin('Updating the plan", "await K.t.final(say)"):
        assert needle in ws, needle
    assert "K.t.her(m.text, {pending: true})" in ae and "label: 'Working on the app'" in ae
    # the panels' own waiting markup is gone: no spinner card, no live box, no dots row, no pulse dot
    for gone in ("working wcard", "wsLiveBox", "wsWork", "class=\"thinking\"", "new window.HoolaMD.Live(", "new window.HoolaStream.Pacer(",
                 "class=\"who\"", "Updating the plan · about a minute<span", "data-form=\"revise\""):
        assert gone not in ws, gone
    for gone in ("ae-work", "ae-hoola", "ae-me", "Hoola is working on the app", "md.render("):
        assert gone not in ae, gone
    assert ".ae-work" not in _r("appengine.css") and "ae-pulse" not in _r("appengine.css")


def test_actions_are_only_the_ones_a_route_answers():
    ws, ae = _r("webstudio.js"), _r("appengine.js")
    # the site thread is a real conversation: Good answer / Not right go to the main chat's own route, with the reply's turn
    assert "acts: ['copy', 'aloud', 'up', 'down']" in ws
    assert "/feedback`, {turn, value}" in ws and "b.hidden = !can" in ws, "hidden where the turn is not known"
    assert "'again'" not in ws and "/retry" not in ws, "Ask again would build the change a second time: Edit and resend is the Studio's way"
    # the plan chat and the app chat: Copy + Read aloud (the kit's default), nothing that needs a route they lack
    assert "acts:" not in ae and ws.count("acts:") == 1
    # Stop is real everywhere it shows: the conversation's own stop route
    assert "/stop`, {}" in ws and "/stop`, {}" in ae and "onStop: () => stopTurn()" in ae
    assert "onStop" not in ws[ws.index("function planThread"):ws.index("async function revisePlan")], "a plan rewrite cannot be stopped: no fake Stop"


def test_the_page_sets_the_kits_colours_from_its_own_tokens():
    css = _r("webstudio.css")
    block = css[css.index("HOOLA CHAT KIT in the Web Studio"):]
    block = block.split("/* v0.999.24 PROTOTYPE FIRST")[0]           # the next block is the prototype page, not the kit
    assert ":is(#wsHist,#wsPlanHist,#wsRevBar,#aeHist,#aeBar){--hck-bubble:var(--me);--hck-pill:var(--solid);--hck-onpill:var(--on-solid)}" in block
    assert ':root[data-theme="dark"] :is(#wsHist,#wsPlanHist,#aeHist){--acc-rgb:156 136 255}' in block
    # this file is shared with the App Studio page: every kit rule here names one of this page's own roots
    for rule in re.findall(r"^([^{}/@\n][^{}\n]*)\{", block, flags=re.M):
        assert re.search(r"#ws(Hist|PlanHist|RevBar|Q)|#ae(Hist|Bar)|\.comp |\.pbar", rule), rule
    assert not re.search(r"\.hck-(txt|bub|work|label)\s*\{", block), "the kit's own look is not restyled per panel"


def _open(browser, key, url, errors, width=1366, height=820, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme, device_scale_factor=1)
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(url)
    return ctx, page


def test_the_site_thread_on_the_kit_in_a_browser(arena_server, arch_env, monkeypatch):
    """A real browser on a website's thread: her bubble at send, the kit's ONE working row (Thinking, then the real
    step, with the clock), Stop beside Send, a second message waits greyed, the streamed reply lands as soft words in
    the kit's text block, the steps fold to Worked for, Thought for · 1 step · credits + Details stay, the action row has
    Copy / Read aloud / Good answer / Not right and Good answer reaches the server with the reply's turn."""
    base, browser, key = arena_server
    hq_t = real_tiers(monkeypatch)                                      # v0.999.33 the real tier + credits routes
    from app import turn_inbox, turncost
    from app.db import Message, now, session
    from app.events import bus
    gate = {"go": False}
    words = "The hero now has a deeper colour and a calmer headline for your clinic. " * 3

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        t0 = now()
        if "second" in text:                                # the server runs one turn at a time: this one after the first
            for _ in range(240):
                if gate.get("first"):
                    break
                await asyncio.sleep(0.25)
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        if "second" in text:
            await asyncio.sleep(1.0)
            reply = "Done, the second change is in too."
            with session() as s:
                s.add(Message(conversation_id=conv, role="assistant", content=reply, display=reply, in_history=True))
            bus.publish(conv, "message", {"role": "assistant", "text": reply, "source": "agent", "turn": "tr2"})
            return reply
        await asyncio.sleep(0.5)
        bus.publish_live(conv, "think", {"turn": "tr1", "seg": 0, "seq": 1, "text": "hmm"})
        await asyncio.sleep(1.3)
        bus.publish(conv, "step", {"tool": "website", "label": "Reading the site", "state": "running", "id": "s1"})
        await asyncio.sleep(1.2)
        bus.publish(conv, "step", {"tool": "website", "label": "Reading the site", "state": "done", "id": "s1"})
        for _ in range(60):
            if gate["go"]:
                break
            await asyncio.sleep(0.25)
        bus.publish_live(conv, "reply_start", {"turn": "tr1"})
        for i, w in enumerate(words.strip().split(" ")):
            bus.publish_live(conv, "delta", {"turn": "tr1", "seg": 0, "seq": i + 1, "text": w + " "})
            await asyncio.sleep(0.02)
        bus.publish_live(conv, "reply_end", {"turn": "tr1"})
        await asyncio.sleep(0.2)
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content=words.strip(), display=words.strip(), in_history=True))
        turncost.record(tenant, conv, t0, {"usd": 0.035, "calls": 3})
        bus.publish(conv, "message", {"role": "assistant", "text": words.strip(), "source": "agent", "turn": "tr1"})
        gate["first"] = True
        return words
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    from app.site import service as S
    a = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    shots = os.environ.get("CONSOLE_SHOTS")
    errors: list[str] = []
    ctx, page = _open(browser, key, base + f"/console/web#/site/{a['id']}", errors)
    page.wait_for_selector("#wsTh")
    page.wait_for_selector("#wsHist.hck .hck-txt")                      # the opening line is the kit's too, drawn whole
    quality_under(page, "#wsTh")                                       # her tier + credits under the box, from the server
    pick_low(page, "#wsTh", hq_t)                                      # a pick there is the tier her work runs on
    assert page.locator("#wsHist .hck-txt .w").count() == 0, "what is there when the panel opens is never re-landed"
    assert page.locator("#wsHist .chip[data-ask]").count() == 4 and page.locator("#wsStop").is_hidden()
    page.fill("#wsTh", "Make the hero more premium")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsHist .hck-me .hck-bub:has-text('Make the hero more premium')", timeout=3000)   # at once
    page.wait_for_selector("#wsHist .hck-work .hck-mark svg", timeout=4000)                     # the ONE working row
    page.evaluate("document.querySelector('#wsHist .hck-bub').__first = true")
    assert page.locator("#wsHist .hck-work").count() == 1 and page.locator("#wsMsgs .spin, #wsMsgs .wcard, #wsMsgs .dots").count() == 0
    assert page.locator("#wsStop").is_visible(), "Stop sits beside Send while Hoola works"
    page.wait_for_function("() => (document.querySelector('#wsHist .hck-label') || {}).textContent === 'Thinking…'", timeout=8000)
    page.wait_for_function("() => (document.querySelector('#wsHist .hck-label') || {}).textContent === 'Reading the site'", timeout=8000)
    page.wait_for_function("() => /^\\d+s$/.test((document.querySelector('#wsHist .hck-secs') || {}).textContent || '')", timeout=5000)
    if shots:
        page.wait_for_timeout(450)
        page.screenshot(path=f"{shots}/kit-ws-working.png")
    page.fill("#wsTh", "and a second change")                          # sent while Hoola works: waits greyed, at the bottom
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsQ .me.queued:has-text('and a second change')", timeout=4000)
    assert page.locator("#wsHist .hck-bub").count() == 1, "a queued line is not in the thread yet"
    gate["go"] = True
    page.wait_for_selector("#wsHist .hck-txt .w", timeout=8000)         # the newest words land out of a soft focus
    assert page.locator("#wsHist .hck-fold .sm").first.inner_text().startswith("Worked for "), "words start -> the steps fold"
    n1 = len(page.inner_text("#wsHist .hck-ho:last-of-type .hck-txt"))
    assert n1 < len(words.strip()), "the reply lands at reading pace, not in one piece"
    if shots:
        page.screenshot(path=f"{shots}/kit-ws-landing.png")
    # the first reply lands to its end, THEN the queued line moves into the thread and its own turn runs
    page.wait_for_selector("#wsHist .hck-bub:has-text('and a second change')", timeout=30000)
    first = page.locator("#wsHist .hck-ho[data-id]").first
    assert first.locator(".hck-txt").inner_text().strip() == words.strip()
    page.wait_for_selector("#wsHist .hck-txt:has-text('the second change is in too')", timeout=15000)
    page.wait_for_selector("#wsHist .hck-acts", timeout=15000)
    page.wait_for_function("() => !document.querySelector('#wsHist .hck-work')", timeout=15000)
    assert page.locator("#wsStop").is_hidden() and page.locator("#wsQ .me.queued").count() == 0
    # the Studio's own line under the fold: Thought for · steps · rupees, and Details
    page.wait_for_selector("#wsHist .ws-tmeta:has-text('credit')", timeout=10000)
    meta = first.locator(".ws-tmeta").inner_text()
    assert meta.startswith("Thought for ") and "1 step" in meta and "1 steps" not in meta and meta.endswith(" credits"), meta
    first.locator(".hck-fold summary").click()
    assert "Read the site" in first.locator(".hck-fold").inner_text()   # past tense once done
    # actions under the newest reply only; Good answer goes to the server with that reply's turn
    assert page.locator("#wsHist .hck-acts").count() == 1
    acts = page.locator("#wsHist .hck-acts [data-act]:visible").evaluate_all("els => els.map(e => e.dataset.act)")
    assert acts == ["copy", "aloud", "up", "down"], acts
    with page.expect_request(lambda r: r.url.endswith("/feedback") and r.method == "POST") as fb:
        page.click("#wsHist .hck-acts [data-act='up']")
    assert fb.value.post_data_json == {"turn": "tr2", "value": "up"}
    assert page.get_attribute("#wsHist .hck-acts [data-act='up']", "aria-pressed") == "true"
    assert page.evaluate("document.querySelector('#wsHist .hck-bub').__first === true"), "the thread was never drawn again while she worked"
    order = page.locator("#wsHist > .hck-me, #wsHist > .hck-ho").evaluate_all("els => els.map(e => e.className.split(' ')[0])")
    assert order == ["hck-me", "hck-ho", "hck-me", "hck-ho"], order
    if shots:
        page.screenshot(path=f"{shots}/kit-ws-done.png")
    first.locator("[data-act='details']").click()
    page.wait_for_selector("#wsPane .tline li", timeout=4000)
    assert "Read the site" in page.inner_text("#wsPane .tline")
    page.click("#wsPane [data-view='preview']")
    # a reload: the same thread is history, drawn whole (no landing), with the fold and the numbers back
    page.reload()
    page.wait_for_selector("#wsHist .hck-fold", timeout=15000)
    page.wait_for_selector("#wsHist .ws-tmeta:has-text('credit')", timeout=10000)
    assert page.locator("#wsHist .hck-txt .w").count() == 0 and page.locator("#wsHist .hck-bub").count() == 2
    assert page.locator("#wsHist .hck-ho").count() == 2 and page.locator("#wsHist .hck-acts").count() == 1
    assert page.locator("#wsHist .hck-acts [data-act='up']").is_visible(), "the timeline names the reply's turn: Good answer still works after a reload"
    # the kit's numbers, not the old 15.5 / 25: Literata 16 / 1.5, her bubble 16 / 1.5, 28 px between turns in this narrow column
    got = page.evaluate("""() => { const c = s => getComputedStyle(document.querySelector(s));
        return [c('#wsHist .hck-txt').fontFamily.split(',')[0].replace(/"/g, ''), c('#wsHist .hck-txt').fontSize, c('#wsHist .hck-txt').lineHeight,
                c('#wsHist .hck-bub').fontSize, c('#wsHist').rowGap, c('#wsHist .hck-bub').backgroundColor] }""")
    assert got == ["Literata", "16px", "24px", "16px", "28px", "rgb(242, 240, 235)"], got
    # dark: the page's own tokens reach the kit (ink, bubble), the mark is the dark violet
    page.emulate_media(color_scheme="dark")
    page.reload()
    page.wait_for_selector("#wsHist .hck-acts", timeout=20000)
    dark = page.evaluate("""() => { const c = s => getComputedStyle(document.querySelector(s));
        return [c('#wsHist .hck-txt').color, c('#wsHist .hck-bub').backgroundColor, c('#wsHist').getPropertyValue('--acc-rgb').trim()] }""")
    assert dark == ["rgb(228, 228, 234)", "rgb(42, 37, 67)", "156 136 255"], dark
    if shots:
        page.screenshot(path=f"{shots}/kit-ws-dark.png")
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors


def test_the_plan_chat_on_the_kit_in_a_browser(arena_server, arch_env, monkeypatch):
    """The plan chat: what is there is drawn whole by the kit, her change is a kit bubble at once, the kit's working
    row runs with the clock while the plan is rewritten (no Stop - a rewrite cannot be stopped), Hoola's line lands in
    the kit's text block with Copy / Read aloud under it, and the plan on the right is the new one."""
    base, browser, key = arena_server
    real_tiers(monkeypatch)
    shots = os.environ.get("CONSOLE_SHOTS")
    errors: list[str] = []
    ctx, page = _open(browser, key, base + "/console/web#/", errors)
    page.wait_for_selector("#wsAsk")
    quality_under(page, "#wsAsk")                                      # the home box
    words = "hamare school ka portal - admission, fees, chhutti ki arzi, notices"
    pid = page.evaluate("""async ([key, words]) => {
        const r = await fetch('/api/site-architect', {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + key}, body: JSON.stringify({words})});
        const c = await r.json(); localStorage.setItem('hoola.ws.spec.words.' + c.id, words); return c.id; }""", [key, words])
    page.goto(base + f"/console/web#/plan/{pid}")
    page.wait_for_selector("#wsPlanHist.hck .hck-txt", timeout=20000)
    quality_under(page, "#wsRev")                                      # the plan's box
    assert page.inner_text("#wsPlanHist .hck-bub") == words
    assert page.locator("#wsPlanHist .hck-txt .w").count() == 0, "history is drawn whole"
    assert page.locator("#wsRevBar.hck-bar textarea#wsRev").count() == 1 and page.is_disabled("#wsRevBar .go")
    assert page.locator("#wsPlanMsgs .dots, form[data-form='revise']").count() == 0
    fam = page.evaluate("getComputedStyle(document.querySelector('#wsPlanHist .hck-txt')).fontFamily + '|' + getComputedStyle(document.querySelector('#wsPlanHist .hck-txt')).fontSize")
    assert fam.startswith('Literata') or fam.startswith('"Literata"'), fam
    assert fam.endswith("|16px"), fam

    def slow(route):
        time.sleep(2.2)
        route.continue_()
    page.route("**/revise", slow)
    page.fill("#wsRev", "aur ek Adopt a Pet page jahan rescue dogs ki photos hon")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsPlanHist .hck-work .hck-mark svg", timeout=1500)
    assert "Adopt a Pet" in page.locator("#wsPlanHist .hck-bub").last.inner_text() and page.input_value("#wsRev") == ""
    assert page.inner_text("#wsPlanHist .hck-label").startswith("Updating the plan")
    assert page.get_attribute("#wsRevBar .go", "aria-label") == "Send" and page.is_disabled("#wsRevBar .go"), "no fake Stop"
    page.wait_for_function("() => /^\\d+s$/.test((document.querySelector('#wsPlanHist .hck-secs') || {}).textContent || '')", timeout=5000)
    if shots:
        page.wait_for_timeout(400)
        page.screenshot(path=f"{shots}/kit-plan-working.png")
    page.wait_for_selector("#wsPlanHist .hck-acts", timeout=60000)
    assert page.locator("#wsPlanHist .hck-work").count() == 0
    assert "has your change" in page.locator("#wsPlanHist .hck-txt").last.inner_text()
    assert page.locator("#wsPlanHist .hck-acts [data-act]").evaluate_all("els => els.map(e => e.dataset.act)") == ["copy", "aloud"]
    assert "Gyan Vidya Mandir" in page.inner_text("#ws .doc") and page.locator("#ws [data-act='approve-plan']").count() == 1
    assert not page.evaluate("document.querySelector('#wsRev').readOnly")
    if shots:
        page.screenshot(path=f"{shots}/kit-plan-done.png")
    page.unroute("**/revise")
    # coming back: her change and Hoola's line are history now, drawn whole
    page.reload()
    page.wait_for_selector("#wsPlanHist .hck-txt:has-text('has your change')", timeout=20000)
    assert page.locator("#wsPlanHist .hck-bub").count() == 2 and page.locator("#wsPlanHist .hck-txt .w").count() == 0
    # a failed change: the row goes, the reason shows, her words are back in the box
    page.route("**/revise", lambda r: r.fulfill(status=502, content_type="application/json", body='{"detail": "Could not rewrite the plan."}'))
    page.fill("#wsRev", "make it shorter")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsPlanHist .li.bad:has-text('your words are back in the box')", timeout=10000)
    assert page.input_value("#wsRev") == "make it shorter" and page.locator("#wsPlanHist .hck-work").count() == 0
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors


def test_the_react_app_chat_on_the_kit_in_a_browser(arena_server, site_env, monkeypatch, tmp_path):
    """The React app's chat (polled): the kit's thread and box, her line at once, the ONE working row, Send becomes
    Stop while Hoola works (the conversation's own stop route), a reply found by the poll lands word by word, Copy /
    Read aloud under it - in light and in dark."""
    monkeypatch.setenv("APP_ENGINE_DIR", str(tmp_path / "appengine"))
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import Message, init_db, session
    init_db()
    base, browser, key = arena_server
    real_tiers(monkeypatch)
    from app import turn_inbox
    from app.appengine import service as AE
    reply = "I added a **Due today** list to the tasks page and kept the colours as they were. " * 2
    stops: list[str] = []

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        await asyncio.sleep(3.0)
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content=reply.strip(), display=reply.strip(), in_history=True))
        return reply
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    from app.agent import santosh
    monkeypatch.setattr(santosh, "stop", lambda conv: stops.append(conv))
    a = AE.create(T, name="Shop staff tasks", brief="A task list for my shop staff")
    shots = os.environ.get("CONSOLE_SHOTS")
    errors: list[str] = []
    for scheme in ("light", "dark"):
        ctx, page = _open(browser, key, base + f"/console/web#/app/{a['id']}", errors, width=1440, height=900, scheme=scheme)
        page.wait_for_selector("#aeHist.hck", timeout=20000)
        page.wait_for_selector("#aeBar.hck-bar textarea#aeSay")
        quality_under(page, "#aeBar")                                  # the React app's box
        if scheme == "light":
            assert "Tell Hoola what this app should do" in page.inner_text("#aeHist") and page.is_disabled("#aeBar .go")
            page.fill("#aeSay", "Add a due today list")
            page.keyboard.press("Enter")
            page.wait_for_selector("#aeHist .hck-bub:has-text('Add a due today list')", timeout=2000)      # at once
            page.wait_for_selector("#aeHist .hck-work .hck-mark svg", timeout=3000)
            assert page.inner_text("#aeHist .hck-label") == "Working on the app" and page.locator("#aeHist .ae-work, #aeHist .dot").count() == 0
            assert page.get_attribute("#aeBar .go", "aria-label") == "Stop"
            page.click("#aeBar .go")
            page.wait_for_function("() => (document.querySelector('#toast') || {}).textContent.includes('Stopping')", timeout=5000)
            assert stops, "Stop reached the conversation's stop route"
            if shots:
                page.screenshot(path=f"{shots}/kit-ae-working.png")
            page.wait_for_selector("#aeHist .hck-txt .w", timeout=15000)          # the polled reply lands, it is not pasted in
            assert len(page.inner_text("#aeHist .hck-txt")) < len(reply.strip())
            page.wait_for_selector("#aeHist .hck-acts", timeout=20000)
            assert page.locator("#aeHist .hck-bub").count() == 1, "her line shown at send is matched to the server's copy"
            assert page.locator("#aeHist .hck-txt strong, #aeHist .hck-txt b").count() >= 1      # the kit's markdown
            assert page.get_attribute("#aeBar .go", "aria-label") == "Send" and page.locator("#aeHist .hck-work").count() == 0
        else:
            page.wait_for_selector("#aeHist .hck-acts", timeout=20000)             # history: whole, with the action row
            assert page.locator("#aeHist .hck-txt .w").count() == 0 and page.locator("#aeHist .hck-bub").count() == 1
            ink = page.evaluate("getComputedStyle(document.querySelector('#aeHist .hck-txt')).color")
            assert ink == "rgb(228, 228, 234)", f"dark theme: the reply is the page's own chat ink ({ink})"
        assert page.locator("#aeHist .hck-acts [data-act]").evaluate_all("els => els.map(e => e.dataset.act)") == ["copy", "aloud"]
        if shots:
            page.screenshot(path=f"{shots}/kit-ae-{scheme}.png")
        ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
