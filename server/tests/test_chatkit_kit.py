"""HOOLA CHAT KIT (owner: "EVERY CHAT SECTION MUST HAVE SAME FEATURE, DESIGN AND TEXT LANDING, TIMING, SPACING ... CURRENTLY
HOOLA CHAT AND HOOLA CODE IS PERFECT ... DO IT SAME FOR ALL TOOLS AND FEATURES" -> prototype -> "GO"): the one thread
every chat panel mounts (static/console/chatkit.js + chatkit.css) and its phone twin (lib/ui/chat/hoola_thread.dart).
The numbers are the main chat's own - these tests hold the kit to them and walk it in a real browser."""
from __future__ import annotations

import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def _r(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_the_kit_runs_the_main_chats_own_landing():
    js, css = _r(CON / "chatkit.js"), _r(CON / "chatkit.css")
    # the same pacer and the same soft-focus renderer the main chat uses - not a second copy of either
    assert "new HoolaStream.Pacer(" in js and "new HoolaMD.Live(box, {soft: true})" in js
    assert "HoolaMark.think(24)" in js
    assert "setTimeout(" not in re.sub(r"setTimeout\(\(\) => \{ (s|b)\.textContent = 'Copy'; \}, 1500\)", "", js), \
        "the kit never times words itself; the pacer does"
    stream = _r(CON / "stream.js")
    assert "this.acc / 34" in stream, "34 ms a word is the pace every panel shares"
    assert "const SOFT_MS = 460" in _r(CON / "md.js")
    assert ".hck-txt .w{animation:hckWord var(--hck-soft,.46s) ease both}" in css
    assert "@keyframes hckWord{from{opacity:0;filter:blur(3px)}to{opacity:1;filter:none}}" in css


def test_the_kit_has_the_main_chats_numbers():
    css = _r(CON / "chatkit.css")
    for rule in (
        ".hck{--hck-gap:44px;",                                   # between turns
        ".hck-txt{font-family:var(--hck-fr);font-size:16px;font-weight:400;line-height:1.5;",
        ".hck-txt p{margin:0 0 16px}",
        ".hck-txt h3.mdh{font-size:22px}.hck-txt h4.mdh{font-size:20px}.hck-txt h5.mdh,.hck-txt h6.mdh{font-size:17px}",
        "max-width:680px",                                        # the prose cap
        "border-radius:18px 18px 6px 18px",                       # her bubble
        "animation:hckRise .32s",
        "animation:hckShim 1.8s linear infinite",                 # the moving light on the working row
    ):
        assert rule in css, rule
    # colours: only the kit's own tokens inside the rules, each falling back to the page's token and a theme default
    body = css[css.index(".hck{--hck-gap"):css.index("/* the thinking mark")]
    assert not re.findall(r"var\(--(?!hck)[a-z0-9-]+", body), "kit rules read --hck-* only"
    assert "--hck-ink:var(--chat-ink,var(--ink,var(--hck0-ink)))" in css
    assert ':root[data-theme="dark"],.hck-dark{--hck0-ink:#E6E5E1' in css
    assert "@media (prefers-reduced-motion:reduce)" in css


def test_the_kit_only_offers_what_works_by_itself():
    js = _r(CON / "chatkit.js")
    assert "const acts = opts.acts || ['copy', 'aloud'];" in js, "Good / Not right / Ask again only where a panel asks for them"
    assert "speechSynthesis" in js and "navigator.clipboard.writeText" in js
    assert "window.HoolaChat = {mount, bar, fmtSecs, plain};" in js


def test_the_phone_kit_shares_the_numbers():
    d = _r(ROOT / "lib" / "ui" / "chat" / "hoola_thread.dart")
    assert "const kThreadMsPerWord = 34;" in d and "const kThreadSoftMs = 460;" in d
    chat = _r(ROOT / "lib" / "ui" / "chat" / "hoola_chat.dart")
    assert "const kLandMsPerWord = 34;" in chat and "const kLandSoftMs = 460;" in chat, "the reference the kit copies"
    for cls in ("class HoolaLanding", "class HoolaHerBubble", "class HoolaWorkingRow", "class HoolaReplyActions",
                "class HoolaThreadView", "class HoolaMsg", "class HoolaOnDark"):
        assert cls in d, cls
    assert "(waiting ~/ 80).clamp(0, 2)" in d, "the console's capped catch-up"
    assert "Color(0x" not in d, "theme roles only"


PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/static/console/chatkit.css"></head>
<body><div id="sc" style="height:420px;overflow:auto;width:560px"><div id="r"></div></div><div id="bar"></div>
<script src="/static/console/md.js"></script><script src="/static/console/mark.js"></script>
<script src="/static/console/stream.js"></script><script src="/static/console/chatkit.js"></script></body></html>"""

WALK = """async () => {
  const out = {}; const w = ms => new Promise(r => setTimeout(r, ms)); const q = s => document.querySelectorAll(s);
  const t = HoolaChat.mount(document.getElementById('r'), {scroller: document.getElementById('sc'), acts: ['copy','aloud','up','down'], onAct: (k, tx, v) => { out.act = [k, v]; }});
  const H = [{id: 1, role: 'her', text: 'old question'}, {id: 2, role: 'hoola', text: 'old **answer**'}];
  t.sync({key: 'a', messages: H, working: false});
  out.history = {me: q('.hck-me').length, txt: q('.hck-txt').length, landing: q('.hck-txt .w').length, acts: q('.hck-ra').length};
  t.her('new question', {pending: true});
  t.sync({key: 'a', messages: H, working: true, label: 'Reading the sheet'});
  out.working = {busy: t.busy, label: document.querySelector('.hck-label').textContent, mark: !!document.querySelector('.hck-mark svg, .hck-mark .hm3'), acts: q('.hck-ra').length};
  const H2 = [...H, {id: 3, role: 'her', text: 'new question'}];
  t.sync({key: 'a', messages: H2, working: true, label: 'Reading the sheet', steps: [{id: 's1', label: 'Open the file'}]});
  out.herOnce = q('.hck-me').length;
  t.sync({key: 'a', messages: H2, working: true, steps: [{id: 's1', label: 'Open the file', state: 'done'}]});
  const long = 'Here is the new answer with a good number of words so that the pacer has something to land over time. '.repeat(3);
  t.sync({key: 'a', messages: [...H2, {id: 4, role: 'hoola', text: long.slice(0, 80)}], working: true});
  await w(250);
  out.partial = {words: q('.hck-txt')[1].textContent.length, soft: q('.hck-txt .w').length > 0, fold: document.querySelector('.hck-fold .sm')?.textContent || ''};
  const H4 = [...H2, {id: 4, role: 'hoola', text: long}];
  t.sync({key: 'a', messages: H4, working: true}); await w(150);
  t.sync({key: 'a', messages: H4, working: false});
  out.stillLanding = t.busy && q('.hck-txt')[1].textContent.length < long.trim().length;
  await w(4200);
  out.done = {busy: t.busy, whole: q('.hck-txt')[1].textContent.trim() === long.trim(), acts: q('.hck-ra').length, work: q('.hck-work').length};
  document.querySelector('[data-act="up"]').click(); await w(20);
  t.sync({key: 'a', messages: [...H4, {id: 5, role: 'her', text: 'third'}, {id: 6, role: 'hoola', text: 'A reply that came in one piece lands too.'}], working: false});
  out.onePiece = t.busy; await w(1600); out.onePieceDone = {busy: t.busy, txt: q('.hck-txt').length};
  t.sync({key: 'b', messages: [{id: 9, role: 'her', text: 'another chat'}], working: false});
  out.otherChat = {me: q('.hck-me').length, txt: q('.hck-txt').length};
  t.clear(); t.her('live'); t.begin(); t.step({id: 1, label: 'Search'}); await w(60); t.step({id: 1, label: 'Search', state: 'done'});
  t.delta('Hello '); t.delta('world'); await t.final('Hello world, done.'); t.end();
  out.live = {fold: document.querySelector('.hck-fold .sm').textContent, text: document.querySelector('.hck-txt').textContent, busy: t.busy};
  t.clear(); t.her('x'); t.begin(); t.delta('<img src=x onerror=window.__pwn=1> <b>raw</b>'); await t.final('<img src=x onerror=window.__pwn=1> <b>raw</b>'); t.end();
  out.safe = {img: q('.hck-txt img').length, pwn: !!window.__pwn};
  const bar = HoolaChat.bar(document.getElementById('bar'), {onSend: v => { out.sent = v; }, onStop: () => { out.stopped = true; }});
  bar.value = 'hi'; bar.input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));
  bar.working = true; out.stopLabel = document.querySelector('.hck-bar .go').getAttribute('aria-label'); document.querySelector('.hck-bar .go').click();
  return out;
}"""


def test_the_kit_in_a_real_browser(arena_server):
    base, browser, _key = arena_server
    ctx = browser.new_context(viewport={"width": 900, "height": 700})
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        pg.route(base + "/__kit", lambda r: r.fulfill(status=200, content_type="text/html", body=PAGE))
        pg.goto(base + "/__kit"); pg.wait_for_function("() => window.HoolaChat && window.HoolaStream && window.HoolaMD && window.HoolaMark")
        o = pg.evaluate(WALK)
    finally:
        ctx.close()
    assert not errs, errs
    assert o["history"] == {"me": 1, "txt": 1, "landing": 0, "acts": 4}, "history is drawn whole, never re-landed"
    assert o["working"]["busy"] and o["working"]["label"] == "Reading the sheet" and o["working"]["mark"]
    assert o["working"]["acts"] == 0, "no actions under an old reply while a new turn runs"
    assert o["herOnce"] == 2, "her message shown at send is matched to the server's copy, not drawn twice"
    assert o["partial"]["soft"] and o["partial"]["fold"].startswith("Worked for "), "words start -> the steps fold"
    assert o["stillLanding"], "the reply keeps landing at reading pace after the server says it is finished"
    assert o["done"] == {"busy": False, "whole": True, "acts": 4, "work": 0}
    assert o["act"] == ["up", "up"]
    assert o["onePiece"] and o["onePieceDone"] == {"busy": False, "txt": 3}, "a reply in one piece lands like a streamed one"
    assert o["otherChat"] == {"me": 1, "txt": 0}, "another chat redraws from its own history"
    assert o["live"] == {"fold": "Worked for 1s", "text": "Hello world, done.", "busy": False}
    assert o["safe"] == {"img": 0, "pwn": False}, "her customers' and the model's text is never run as HTML"
    assert o["sent"] == "hi" and o["stopLabel"] == "Stop" and o["stopped"] is True
