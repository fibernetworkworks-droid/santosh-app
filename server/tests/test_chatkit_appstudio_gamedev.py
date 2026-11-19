"""HOOLA CHAT KIT in App Studio (/console/apps) and Hoola Game Dev (/console/games).

Both pages have their own Hoola thread per app / per game. It is now drawn by the shared chat kit (console/chatkit.js +
chatkit.css): her message is the kit's bubble the moment she sends, Hoola's reply lands word by word, ONE working row
shows the real step and the clock, and the newest reply carries Copy / Read aloud, plus Good answer / Not right /
Ask again on the main chat's own routes (POST /feedback, /retry). Both pages still read the conversation by polling;
each read hands the kit the whole list.

Held here: the static wiring (the four scripts + the stylesheet, in order, on the page's own stamp; the old waiting
markup is gone), and a REAL BROWSER walk of each thread. No model is called: the conversation's routes are answered by
the test (the same shapes the server sends), so a whole turn - send, steps, the reply being written, the saved reply,
thumbs, Ask again, Stop - is walked deterministically."""
from __future__ import annotations

from tests._hq_wiring import pick_low, quality_under, real_tiers  # v0.999.30 WIRED
import json
import os
import re
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0783_gamedev import Walk, _game, _hired, gd_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401  (fixture)
from tests.test_v128_appdesign import T, app_env  # noqa: F401

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
KIT_SCRIPTS = ["md.js", "mark.js", "stream.js", "chatkit.js"]
HINT = "\n\n[Web console language preference: Reply in English unless I explicitly request another language.]"


# ================================================================ 1. static
def _order(html: str, names: list[str]) -> list[int]:
    return [html.index(f"/static/console/{n}?v=") for n in names]


def test_pages_load_the_kit_in_order_on_their_own_stamp():
    from app.main import APP_VERSION
    for page, script, css in (("appstudio.html", "appstudio.js", "appstudio.css"), ("gamedev.html", "gamedev.js", "gamedev.css")):
        html = (CON / page).read_text()
        at = _order(html, KIT_SCRIPTS + [script])
        assert at == sorted(at), page                                   # md, mark, stream, chatkit, then the page's script
        for f in KIT_SCRIPTS + [script, "chatkit.css", css]:
            assert f"/static/console/{f}?v={APP_VERSION}" in html, (page, f)      # one stamp: a changed file never sits in a cache
        assert html.index("chatkit.css?v=") < html.index(css + "?v=")   # the page's token map comes after the kit's defaults
        assert "family=Schibsted+Grotesk" in html and "Literata" in html           # the reply serif is loaded
        for f in KIT_SCRIPTS + ["chatkit.css"]:
            assert (CON / f).is_file(), f


def test_threads_are_the_kits_and_the_old_waiting_markup_is_gone():
    a, g = (CON / "appstudio.js").read_text(), (CON / "gamedev.js").read_text()
    for name, js in (("appstudio", a), ("gamedev", g)):
        assert "window.HoolaChat.mount(" in js and ".sync(" in js, name
        assert ".her(text, {pending: true})" in js, name                # her words show the moment she sends
        assert "/feedback`, {turn: THREAD.turn, value}" in js and "/retry`)" in js and "/stop`)" in js, name
        assert "KIT_OPTS.startedAt" in js, name                         # the clock runs from her message, not from the redraw
        for gone in ("Hoola is working", "Working · step", "Reading your ask", "THREAD.sig"):
            assert gone not in js, (name, gone)
        r = subprocess.run(["node", "--check", str(CON / f"{name}.js")], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
    # App Studio: the chat's own spinner card and "who" line are gone; the BUILD job card (#asState) and the start card stay
    assert "working wcard" not in a and '<div class="who">' not in a and 'class="ho"' not in a and 'class="me"' not in a
    assert 'box.innerHTML = `<div class="chatact wcard">' in a and "const card = `<div class=\"chatact wcard\">" in a
    assert "#asSend.stop" in a and "drawSend()" in a                     # the composer keeps Build | Plan; its button is Stop while working
    # Game Dev: no dot card, no own bubbles; the box is the kit's bar with the same id the page always had
    for gone in ("gdv-working", "gdv-workh", 'class="gdv-me"', 'class="gdv-ho"', "gdv-who", "gdv-worked", "gdv-stepl"):
        assert gone not in g, gone
    assert "window.HoolaChat.bar(" in g and "BAR.input.id = 'gdvTh'" in g and "onStop: stopTurn" in g
    assert 'data-gdv-form="thread"' in g and 'id="gdvMsgs"' in g
    assert not re.search(r"\son[a-z]+\s*=\s*['\"]", g)                   # still no inline handlers (script-src 'self')


def test_page_css_maps_tokens_and_never_restyles_the_kit():
    acss, gcss = (CON / "appstudio.css").read_text(), (CON / "gamedev.css").read_text()
    assert ".ws-app :is(.hck,.hck-bar,.hck-jump){--hck-bubble:var(--me);--acc-rgb:" in acss
    assert ':root[data-theme="dark"] .ws-app :is(.hck,.hck-bar,.hck-jump){--acc-rgb:' in acss      # the mark's colour in dark too
    assert ".gdv-engine :is(.hck,.hck-bar,.hck-jump){" in gcss and "--hck-violet:var(--pri)" in gcss
    for css in (acss, gcss):
        # tokens and the page's own blocks only: no rule here reaches inside a kit part
        for rule in re.findall(r"([^{}]*)\{[^{}]*\}", css):
            sel = rule.strip()
            if "hck-" not in sel:
                continue
            assert not re.search(r"\.hck-(txt|bub|work|label|acts|ra|ts|fold|me|ho|mark|secs|steps)\b", sel), sel
    for dead in (".gdv-me{", ".gdv-ho{", ".gdv-working{", ".gdv-stepl{", ".gdv-who{"):
        assert dead not in gcss, dead


# ================================================================ 2. the conversation, answered by the test
class Chat:
    """The routes of one conversation, in the server's own shapes: /messages, /timeline (steps, message events with
    their turn, busy, branches), /live (the reply being written), and the POSTs (recorded, never run)."""

    def __init__(self, conv: str):
        self.conv, self.rows, self.events, self.branches = conv, [], [], []
        self.busy, self.live, self.posts, self.n, self.back = False, None, [], 0, 0.0

    def at(self) -> str:
        """Now, on the real clock (the pages match steps to a turn by time); `back` seconds ago while history is seeded."""
        if self.back:
            self.back = max(1.0, self.back - 5)
        return (datetime.now(timezone.utc) - timedelta(seconds=self.back)).replace(tzinfo=None).isoformat()

    def say(self, role: str, text: str, turn: str = "") -> dict:
        self.n += 1
        row = {"id": self.n, "role": role, "text": text, "at": self.at()}
        self.rows.append(row)
        pl = {"role": role, "text": text, "source": "user" if role == "user" else "agent"}
        if turn:
            pl.update(turn=turn, seg=0)
        self.events.append({"id": 100 + len(self.events), "kind": "message", "payload": pl, "at": row["at"], "conv": self.conv})
        return row

    def step(self, sid: str, label: str, state: str = "running"):
        old = next((e for e in self.events if e["kind"] == "step" and e["payload"]["id"] == sid), None)
        if old:
            old["payload"].update(label=label, state=state)
            old["updated_at"] = self.at()
        else:
            self.events.append({"id": 100 + len(self.events), "kind": "step", "at": self.at(), "conv": self.conv,
                                "payload": {"id": sid, "tool": "app_banao", "label": label, "state": state}})

    def handle(self, route):
        req = route.request
        path = req.url.split("/api/conversations/" + self.conv, 1)[1]
        if req.method == "POST":
            self.posts.append((path, json.loads(req.post_data or "{}")))
            return route.fulfill(status=202 if path in ("/messages", "/retry") else 200, json={"accepted": True})
        if path.startswith("/messages"):
            return route.fulfill(json={"messages": self.rows[-60:]})
        if path.startswith("/timeline"):
            return route.fulfill(json={"events": self.events, "busy": self.busy, "branches": self.branches, "has_more": False})
        if path.startswith("/live"):
            return route.fulfill(status=200, json=self.live) if self.live else route.fulfill(status=204, body="")
        return route.fulfill(status=404, json={"detail": "not here"})

    def mount(self, pg):
        pg.route(re.compile(r"/api/conversations/" + re.escape(self.conv) + r"(/|$)"), self.handle)

    def sent(self, path: str) -> list[dict]:
        return [b for p, b in self.posts if p == path]


THREAD = """root => { const q = s => [...document.querySelectorAll(root + ' ' + s)];
  const w = document.querySelector(root + ' .hck-work');
  return {hck: !!document.querySelector(root + '.hck[role=log]'),
    her: q('.hck-me .hck-bub').map(e => e.textContent), replies: q('.hck-txt').map(e => e.innerText.trim()),
    acts: q('.hck-acts [data-act]').map(e => e.dataset.act), rows: q('.hck-acts').length,
    work: w ? {hidden: w.hidden, label: w.querySelector('.hck-label').textContent, mark: !!w.querySelector('.hck-mark .hm3'),
               secs: w.querySelector('.hck-secs').textContent} : null,
    steps: q('.hck-ts .tx').map(e => e.textContent), folds: q('.hck-fold summary').map(e => e.textContent.trim()),
    landing: q('.hck-txt .w').length, stopped: q('.hck-stopped').length,
    serif: (() => { const t = document.querySelector(root + ' .hck-txt'); if (!t) return null; const c = getComputedStyle(t);
                    return [c.fontFamily.split(',')[0].replace(/['"]/g, ''), c.fontSize, c.lineHeight]; })(),
    bub: (() => { const t = document.querySelector(root + ' .hck-bub'); return t ? getComputedStyle(t).fontSize : null; })()}; }"""
# every word that ever landed softly (the kit wraps only the newest words in .w, so history must never count here)
WATCH = """window.__landed = 0; new MutationObserver(ms => { for (const m of ms) for (const n of m.addedNodes)
  if (n.nodeType === 1 && (n.matches?.('.hck-txt .w') || n.querySelector?.('.hck-txt .w'))) window.__landed++; })
  .observe(document, {subtree: true, childList: true});"""


def _shot(pg, name: str):
    if os.environ.get("APP_SHOTS"):                                          # for a human to look at: APP_SHOTS=<dir>
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{os.environ['APP_SHOTS']}/kit-{name}.png")


def _turn(pg, chat: Chat, root: str, box: str, say: str, answer: str, turn: str, stop_sel: str):
    """She sends `say`; the test plays the server: her row, a step, the reply being written, then the saved reply."""
    before = pg.evaluate(THREAD, root)
    pg.fill(box, say)
    pg.press(box, "Enter")
    pg.wait_for_function("([r, n]) => document.querySelectorAll(r + ' .hck-me .hck-bub').length === n && !!document.querySelector(r + ' .hck-work')",
                         arg=[root, len(before["her"]) + 1], timeout=5000)
    now = pg.evaluate(THREAD, root)
    assert now["her"][-1] == say and now["work"]["mark"] and not now["work"]["hidden"], now      # shown at once, ONE working row
    assert now["rows"] == 0                                                 # no action row while Hoola works
    assert pg.locator(stop_sel).count() == 1                                # Send is Stop now
    posted = chat.sent("/messages")[-1]
    assert posted["text"].startswith(say + "\n\n[Web console ") and posted["client_id"]
    chat.say("user", posted["text"])                                        # the server saved her message (hints and all)
    chat.busy = True
    chat.step("s-" + turn, "Reading the design")
    pg.wait_for_function("r => [...document.querySelectorAll(r + ' .hck-ts .tx')].some(e => e.textContent === 'Reading the design')", arg=root, timeout=8000)
    mid = pg.evaluate(THREAD, root)
    assert mid["work"]["label"] == "Reading the design" and len(mid["her"]) == len(before["her"]) + 1, mid   # the real step; her message once
    _shot(pg, root[1:4] + "-working")
    chat.step("s-" + turn, "Reading the design", "done")
    half = answer[: len(answer) // 2]
    chat.live = {"turn": turn, "seg": 0, "seq": 1, "text": half}            # the reply being written (a snapshot that grows)
    pg.wait_for_function("([r, n]) => document.querySelectorAll(r + ' .hck-txt').length === n", arg=[root, len(before["replies"]) + 1], timeout=8000)
    assert "Worked for" in " ".join(pg.evaluate(THREAD, root)["folds"])      # the steps folded when the words began
    _shot(pg, root[1:4] + "-landing")
    chat.live = {"turn": turn, "seg": 0, "seq": 2, "text": answer}
    chat.say("assistant", answer, turn)                                      # saved; the stream is over
    chat.live, chat.busy = None, False
    pg.wait_for_function("r => document.querySelectorAll(r + ' .hck-acts').length === 1 && !document.querySelector(r + ' .hck-work')", arg=root, timeout=20000)
    return before


def _check_thread(pg, chat: Chat, root: str, box: str, stop_sel: str, send_sel: str):
    first = pg.evaluate(THREAD, root)
    assert first["hck"], first
    # history is drawn whole (never re-landed), her hint lines never show, the reply is the kit's serif 16 / 24
    assert first["her"] == ["Make it warmer"] and first["replies"] and "warmer" in first["replies"][0], first
    assert pg.evaluate("() => window.__landed") == 0
    assert first["serif"] == ["Literata", "16px", "24px"] and first["bub"] == "16px", first
    assert first["folds"] and first["folds"][0].startswith("Worked for") and first["steps"] == ["Changing the colours"], first
    assert first["acts"] == ["copy", "aloud", "up", "down", "again"] and first["work"] is None, first
    assert pg.locator(stop_sel).count() == 0

    # ---- a whole turn
    answer = "## Hindi is in\n\nEvery screen now has **Hindi** words. Tap the globe on the home screen to switch. " + "More words follow here. " * 12
    _turn(pg, chat, root, box, "Add Hindi", answer, "t_2", stop_sel)
    done = pg.evaluate(THREAD, root)
    assert done["her"] == ["Make it warmer", "Add Hindi"], done              # her message is never drawn twice
    assert len(done["replies"]) == 2 and done["replies"][1].startswith("Hindi is in") and "More words follow here." in done["replies"][1], done
    assert pg.evaluate("() => window.__landed") > 0                           # the new reply landed word by word
    assert len(done["folds"]) == 2 and done["steps"].count("Reading the design") == 1, done    # its steps folded ONCE, above the words
    assert done["acts"] == ["copy", "aloud", "up", "down", "again"] and done["rows"] == 1, done    # only under the newest reply
    assert pg.locator(stop_sel).count() == 0 and pg.locator(send_sel).count() == 1
    _shot(pg, root[1:4] + "-done")

    # ---- Good answer: the main chat's route, with the reply's own turn
    pg.click(root + " .hck-acts [data-act=up]")
    pg.wait_for_function("r => document.querySelector(r + ' .hck-acts [data-act=up]').getAttribute('aria-pressed') === 'true'", arg=root)
    pg.wait_for_timeout(300)
    assert chat.sent("/feedback") == [{"turn": "t_2", "value": "up"}], chat.posts

    # ---- Ask again: the old answer leaves, her message stays once, the new answer lands under it
    pg.click(root + " .hck-acts [data-act=again]")
    pg.wait_for_function("r => !!document.querySelector(r + ' .hck-work') && document.querySelectorAll(r + ' .hck-txt').length === 1", arg=root, timeout=8000)
    assert chat.sent("/retry") == [{}] or len(chat.sent("/retry")) == 1
    again = pg.evaluate(THREAD, root)
    assert again["her"] == ["Make it warmer", "Add Hindi"] and len(again["replies"]) == 1, again
    asked = next(r for r in chat.rows if r["role"] == "user" and r["text"].startswith("Add Hindi"))
    chat.busy = True
    chat.say("user", asked["text"])                                          # the server runs her message once more...
    chat.branches = [{"id": 1, "kind": "retry", "anchor": next(e["id"] for e in chat.events if e["payload"].get("text") == asked["text"]),
                      "active": 1, "count": 2}]
    chat.say("assistant", "A fresh answer: Hindi is on every screen.", "t_3")    # ...and the list still carries both
    chat.busy = False
    pg.wait_for_function("r => document.querySelectorAll(r + ' .hck-acts').length === 1 && !document.querySelector(r + ' .hck-work')", arg=root, timeout=20000)
    fresh = pg.evaluate(THREAD, root)
    assert fresh["her"] == ["Make it warmer", "Add Hindi"], fresh
    assert len(fresh["replies"]) == 2 and fresh["replies"][1].startswith("A fresh answer"), fresh

    # ---- she writes again while Hoola is still on the message before: each answer lands under its own message
    order = "r => [...document.querySelector(r).children].map(c => c.classList.contains('hck-me') ? 'her' : c.classList.contains('hck-ho') ? (c.querySelector('.hck-work') ? 'work' : 'hoola') : 'x')"
    n = len(chat.sent("/messages"))
    pg.fill(box, "First thing")
    pg.press(box, "Enter")
    pg.wait_for_function("([r, n]) => document.querySelectorAll(r + ' .hck-me').length === n", arg=[root, 3], timeout=5000)
    chat.say("user", chat.sent("/messages")[n]["text"])
    chat.busy = True
    pg.wait_for_timeout(1700)
    pg.fill(box, "Second thing")
    pg.press(box, "Enter")                                                   # Enter still sends while the button is Stop
    pg.wait_for_function("([r, n]) => document.querySelectorAll(r + ' .hck-me').length === n", arg=[root, 4], timeout=5000)
    assert len(chat.sent("/messages")) == n + 2
    chat.say("assistant", "Answer to the first thing.", "t_4")
    pg.wait_for_function("r => /Answer to the first thing/.test(document.querySelector(r).innerText)", arg=root, timeout=8000)
    assert pg.evaluate(order, root)[-3:] == ["her", "work", "her"] or pg.evaluate(order, root)[-3:] == ["her", "hoola", "her"]
    chat.say("user", chat.sent("/messages")[n + 1]["text"])                  # her second message is saved: its own turn starts under it
    pg.wait_for_function("r => (" + order + ")(r).slice(-4).join() === 'her,hoola,her,work'", arg=root, timeout=8000)
    chat.say("assistant", "Answer to the second thing.", "t_5")
    chat.busy = False
    pg.wait_for_function("r => document.querySelectorAll(r + ' .hck-acts').length === 1 && !document.querySelector(r + ' .hck-work')", arg=root, timeout=20000)
    two = pg.evaluate(THREAD, root)
    assert pg.evaluate(order, root)[-4:] == ["her", "hoola", "her", "hoola"] and two["her"][-2:] == ["First thing", "Second thing"], two
    assert two["replies"][-2:] == ["Answer to the first thing.", "Answer to the second thing."] and two["rows"] == 1, two

    # ---- Stop: the main chat's route; the working row goes, Send is back
    pg.fill(box, "Make the buttons round")
    pg.press(box, "Enter")
    pg.wait_for_selector(stop_sel, timeout=5000)
    chat.say("user", chat.sent("/messages")[-1]["text"])
    chat.busy = True
    pg.wait_for_timeout(1200)
    pg.click(stop_sel)
    pg.wait_for_function("r => !document.querySelector(r + ' .hck-work')", arg=root, timeout=8000)
    assert len(chat.sent("/stop")) == 1 and pg.locator(stop_sel).count() == 0
    chat.busy = False
    pg.wait_for_timeout(3200)                                                # the read after Stop must not start waiting again
    end = pg.evaluate(THREAD, root)
    assert end["work"] is None and end["her"][-1] == "Make the buttons round", end
    assert pg.inner_text(root + " .hck-note") == "Stopped"                   # said in one quiet line


def _seed(chat: Chat):
    chat.back = 900.0                                                        # an earlier talk
    chat.say("assistant", "Hello! I am Hoola. What shall we make?")          # the greeting: before her first message, never shown
    chat.say("user", "Make it warmer\n\n[Web console App Studio: this chat is only about app A-1 \"Sweets ]shop[\" (app id x).]" + HINT)
    chat.step("s-1", "Changing the colours")
    chat.step("s-1", "Changing the colours", "done")
    chat.say("assistant", "## Done\n\nThe colours are **warmer** now.\n\n- Saffron buttons\n- Cream paper", "t_1")
    chat.back = 0.0


# ================================================================ 3. App Studio
def test_app_studio_thread_in_a_real_browser(app_env, arena_server, monkeypatch):
    from app.appmaker import service as S
    from tests.test_life import conv_ctx
    out = {}

    def make():
        ctx = conv_ctx()
        out["v"] = S.new(T, "Sharma Sweets ki app, ghar pe delivery", ctx.conversation_id, name="Sharma Sweets")
    th = threading.Thread(target=make)
    th.start()
    th.join(300)
    v = out["v"]
    base, browser, key = arena_server
    real_tiers(monkeypatch)
    errs = []
    for scheme in ("light", "dark"):
        chat = Chat("conv_kit_as")
        _seed(chat)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.as.conv.{v['id']}', '{chat.conv}'); }} catch (e) {{}}")
        ctx.add_init_script(WATCH)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        chat.mount(pg)
        pg.goto(base + f"/console/apps#/app/{v['id']}/plan")
        pg.wait_for_selector("#asThread .hck-acts", timeout=20000)
        quality_under(pg, "form[data-form=thread]")                     # the app's box
        assert pg.locator("#asMsgs .wcard, #asMsgs .working, #asMsgs .who, #asMsgs .me, #asMsgs .ho").count() == 0     # the old thread is gone
        assert pg.locator("form[data-form=thread] [data-cmode]").count() == 2                # the composer keeps Build | Plan
        if scheme == "dark":                                                 # the kit follows the page's theme
            ink = pg.evaluate("() => getComputedStyle(document.querySelector('#asThread .hck-txt')).color")
            assert [int(x) for x in re.findall(r"\d+", ink)[:3]][0] > 180, ink
            if os.environ.get("APP_SHOTS"):
                pg.screenshot(path=f"{os.environ['APP_SHOTS']}/kit-appstudio-dark.png")
            ctx.close()
            continue
        _check_thread(pg, chat, "#asThread", "#asTh", "#asSend.stop", "#asSend:not(.stop)")
        if os.environ.get("APP_SHOTS"):
            pg.screenshot(path=f"{os.environ['APP_SHOTS']}/kit-appstudio-light.png")
        ctx.close()
    # ---- an app nobody has talked about yet: her brief and Hoola's first line are the kit's, with the starter asks;
    #      the first message replaces them at once (no reply row is offered under Hoola's opening line)
    chat = Chat("conv_kit_as0")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.as.conv.{v['id']}', '{chat.conv}'); }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    chat.mount(pg)
    pg.goto(base + f"/console/apps#/app/{v['id']}/plan")
    pg.wait_for_selector("#asThread .hck-txt", timeout=20000)
    first = pg.evaluate(THREAD, "#asThread")
    assert first["her"] == ["Sharma Sweets ki app, ghar pe delivery"] and len(first["replies"]) == 1 and first["rows"] == 0, first
    assert pg.locator("#asThread .as-intro [data-ask]").count() == 4 and "only about Sharma Sweets" in pg.inner_text("#asThread .as-intro")
    _shot(pg, "appstudio-intro")
    pg.click("#asThread [data-ask] >> nth=0")
    assert pg.input_value("#asTh") == "Make the colours warmer"               # a starter fills her box; she sends it herself
    pg.press("#asTh", "Enter")
    pg.wait_for_selector("#asThread .hck-work", timeout=5000)
    now = pg.evaluate(THREAD, "#asThread")
    assert now["her"] == ["Make the colours warmer"] and now["replies"] == [] and now["work"]["mark"], now
    assert "[Web console App Studio: this chat is only about app" in chat.sent("/messages")[-1]["text"]      # the app's hint still rides
    ctx.close()
    assert not errs, errs


# ================================================================ 4. Hoola Game Dev
def test_game_dev_thread_in_a_real_browser(gd_server, monkeypatch):
    """The game's own thread on the kit, in the engine's dark look whatever the system theme is; the box is the kit's
    bar (same id, same form); a poll never wipes what she is typing and never restarts the game in the viewport."""
    from tests.test_v0783_gamedev import _lum
    base, browser, key = gd_server
    _hired()
    gid = _game(build=True, title="Rickshaw Racer")
    real_tiers(monkeypatch)                                              # after the hire: with credits on a hire needs its package
    chat = Chat("conv_kit_gd")
    _seed(chat)
    w = Walk(browser, base, key, init=f"localStorage.setItem('hoola.gamedev.conv.{gid}', '{chat.conv}'); localStorage.setItem('hoola.theme', 'light');" + WATCH)
    chat.mount(w.pg)
    try:
        w.open(f"#/game/{gid}/play")
        w.pg.wait_for_selector("#gdvThread .hck-acts", timeout=20000)
        quality_under(w.pg, "#gdvBar")                                  # the game's box
        w.pg.wait_for_selector("#gdvPane iframe", timeout=15000)
        w.pg.evaluate("() => { document.querySelector('#gdvPane iframe').__kept = 1; }")
        assert w.pg.locator('section.gdv-chat form[data-gdv-form="thread"] #gdvBar.hck-bar textarea#gdvTh').count() == 1
        assert w.pg.locator("#gdvThread.hck.hck-tight").count() == 1                       # a 340px dock: the kit's tight gap
        assert w.pg.locator("#gdvMsgs .gdv-working, #gdvMsgs .gdv-me, #gdvMsgs .gdv-ho, #gdvMsgs .gdv-who").count() == 0
        # always dark, even when the console's own choice is Light
        look = w.pg.evaluate("""() => { const c = (s, p) => getComputedStyle(document.querySelector(s))[p];
            return {ink: c('#gdvThread .hck-txt', 'color'), bub: c('#gdvThread .hck-bub', 'backgroundColor'), bubInk: c('#gdvThread .hck-bub', 'color'),
                    bar: c('#gdvBar', 'backgroundColor'), barInk: c('#gdvTh', 'color'), fold: c('#gdvThread .hck-fold summary', 'color')}; }""")
        assert _lum(look["ink"]) > 0.6 and _lum(look["bubInk"]) > 0.6 and _lum(look["barInk"]) > 0.6 and _lum(look["fold"]) > 0.25, look
        assert _lum(look["bub"]) < 0.05 and _lum(look["bar"]) < 0.05, look
        _check_thread(w.pg, chat, "#gdvThread", "textarea#gdvTh", "#gdvBar .hck-ib.go.stop", "#gdvBar .hck-ib.go:not(.stop)")
        # what she is typing stays through the polls (the game re-reads every 3 s), and the running game is never restarted
        w.pg.fill("textarea#gdvTh", "half a thought")
        w.pg.wait_for_timeout(7000)
        assert w.pg.input_value("textarea#gdvTh") == "half a thought"
        assert w.pg.evaluate("() => document.querySelector('#gdvPane iframe').__kept") == 1
        # the form still sends (the page's own submit), and a suggestion fills the bar so its button wakes
        w.pg.evaluate("() => document.querySelector('form[data-gdv-form=thread]').requestSubmit()")
        w.pg.wait_for_function("() => [...document.querySelectorAll('#gdvThread .hck-bub')].pop().textContent === 'half a thought'", timeout=5000)
        assert w.pg.input_value("textarea#gdvTh") == "" and chat.sent("/messages")[-1]["text"].startswith("half a thought\n\n[Web console Game Dev:")
        _shot(w.pg, "gdv-end")
        w.check()
    finally:
        w.close()


def test_game_dev_first_lines_and_a_first_message(gd_server):
    """A game nobody has talked about yet: her brief and Hoola's first line are the kit's too, with the suggestions;
    the first message replaces them at once (no reply row is offered for Hoola's opening line)."""
    base, browser, key = gd_server
    _hired()
    gid = _game(title="Chai Hop")
    chat = Chat("conv_kit_gd2")
    w = Walk(browser, base, key, init=f"localStorage.setItem('hoola.gamedev.conv.{gid}', '{chat.conv}');")
    chat.mount(w.pg)
    try:
        w.open(f"#/game/{gid}/design")
        w.pg.wait_for_selector("#gdvThread .hck-txt", timeout=20000)
        first = w.pg.evaluate(THREAD, "#gdvThread")
        assert first["her"] == ["ek chai cup jo chhaton par uchhalta hai"] and len(first["replies"]) == 1 and first["rows"] == 0, first
        assert w.pg.locator("#gdvThread [data-gdv-fill-th]").count() == 3
        _shot(w.pg, "gdv-intro")
        w.pg.click("#gdvThread [data-gdv-fill-th] >> nth=0")
        assert w.pg.input_value("textarea#gdvTh") and w.pg.locator("#gdvBar .hck-ib.go").is_enabled()
        w.pg.press("textarea#gdvTh", "Enter")
        w.pg.wait_for_selector("#gdvThread .hck-work", timeout=5000)
        now = w.pg.evaluate(THREAD, "#gdvThread")
        assert len(now["her"]) == 1 and now["replies"] == [] and now["work"]["mark"], now      # the talk starts clean
        _shot(w.pg, "gdv-first")
        w.check()
    finally:
        w.close()
