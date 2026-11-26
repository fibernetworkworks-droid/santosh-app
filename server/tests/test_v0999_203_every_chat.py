"""v0.999.203 EVERY CHAT LIKE CLAUDE (owner: "NOW DEPLOYE THIS LAST 3 UPDATES SAME TO FULL HOOLA EVERY SECTION AND EVERY TOOLS
AND FEATURES. EVERY CHAT PANEL IN HOOLA"): the main chat's v0.999.197 (reply + her message), v0.999.198 (home greeting,
typing box, the row under it) and v0.999.199 (the sent message lands at the top, room kept, held until she scrolls) in
every chat panel - the shared kit (chatkit.js / .css, every desk and studio), the panels with their own chat (Interactive,
Vocal, Create, Hoola Code, Web / App Studio) and the phone (hoola_thread.dart, Hoola Code's session)."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def _r(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_the_kit_carries_the_three_updates():
    css, js = _r(CON / "chatkit.css"), _r(CON / "chatkit.js")
    assert "--hck0-rw:400;--hck0-rb:600;--hck0-hw:430;--hck0-gw:330}" in css
    assert css.count("--hck0-rw:360;--hck0-rb:530;--hck0-hw:400;--hck0-gw:290}") == 2, "dark: the OS setting and data-theme"
    for rule in (".hck-txt{font-weight:var(--hck0-rw,400)}",
                 '.hck-txt h3.mdh{font-size:28px;line-height:1.3;font-variation-settings:"opsz" 28}',
                 ".hck-txt code,.hck-txt pre{font-family:'JetBrains Mono'",
                 ".hck-bub{font-family:var(--hck-fb);font-size:16px;font-weight:var(--hck0-hw,430);line-height:1.4;animation:hckLand .2s ease-out both}",
                 "@keyframes hckLand{from{opacity:0;transform:translateY(6px)}",
                 ".hck-bar textarea,.hck-bar textarea::placeholder{font-size:16px;font-weight:var(--hck0-hw,430)}",
                 ".hck-under,.hck-under *{font-size:14px;font-weight:var(--hck0-hw,430);line-height:1.4}"):
        assert rule in css, rule
    assert "function lander(root, box)" in js and "window.HoolaChat.lander = lander;" in js
    assert "if (o.still || !landAt(m))" in js, "history is drawn still; only a message she sends lands"
    assert "get holding() { return L.held; }" in js


def test_every_kit_page_loads_the_light_weights():
    pages = [p for p in CON.glob("*.html") if "chatkit.css" in _r(p)]
    assert len(pages) >= 15
    for p in pages:
        s = _r(p)
        if "Literata" in s:
            assert "Literata:ital,opsz,wght@0,7..72,300..700" in s, p.name   # 330 / 290 / 360 / 530 need the range


def test_panels_that_scroll_themselves_leave_the_held_view():
    assert "K.stick && !K.t.holding" in _r(CON / "code.js") and "k.stick = !k.t.holding" in _r(CON / "code.js")
    ws = _r(CON / "webstudio.js")
    assert "THREAD.pinned && !(KIT && KIT.t.holding)" in ws and "if (el && !K.t.holding)" in ws
    assert "if (!t.holding) scroll.scrollTop" in _r(CON / "aiapps.js")
    assert "!T.holding) st.box.scrollTop" in _r(CON / "design" / "hd-ai.js")
    assert "if (!T.holding) msgs.scrollTop" in _r(ROOT / "server" / "app" / "static" / "prayog" / "studio" / "studio.js")
    ix = _r(CON / "interactive.js")
    assert "HoolaChat.lander(t, log)" in ix and "C.landNow = true" in ix and "me.classList.add('hx-landed')" in ix


def test_every_home_greeting_and_box():
    g = "font-size:clamp(28px,5.4vw,38px);font-weight:var(--hck0-gw,330);line-height:1.2"
    for f, sel in (("webstudio.css", ".hero h1{"), ("hoolacode.css", "#app .hcd-home h1{"), ("studio.css", ".hero h1{"),
                   ("vocal2.css", "#hvRoot .hv-heroh{"), ("interactive2.css", "#hxRoot .hx-herob>.hx-serif{")):
        s = _r(CON / f)
        blk = s[s.index("v0.999.203 EVERY CHAT"):]
        assert sel + "font-family:'Literata'" in blk and g in blk, f
        assert "font-size:16px;font-weight:var(--hck0-hw,430)" in blk, f


def test_the_phone_lands_too():
    d = _r(ROOT / "lib" / "ui" / "chat" / "hoola_thread.dart")
    assert "class ThreadLander extends ChangeNotifier" in d and "class HoolaRiseIn" in d
    assert "_land.land();" in d and "height: _land.room" in d
    assert "bodyLarge(c).copyWith(height: 1.4)" in d
    code = _r(ROOT / "lib" / "ui" / "code" / "code_session.dart")
    assert "_lander.land();" in code and "_lander.held" in code and "size: small ? 15.5 : 16, height: 1.4" in code
    assert "fontSize: reply ? 28 : null, height: reply ? 1.3" in _r(ROOT / "lib" / "ui" / "chat" / "hoola_md.dart")
    assert (ROOT / "test" / "every_chat_landing_test.dart").exists()


PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/static/console/chatkit.css"></head>
<body style="margin:0"><div id="sc" style="height:300px;overflow:auto;width:560px"><div id="r"></div></div>
<div id="out" style="height:300px;overflow:auto;width:560px"><div><div id="r2"></div></div></div>
<script src="/static/console/md.js"></script><script src="/static/console/mark.js"></script>
<script src="/static/console/stream.js"></script><script src="/static/console/chatkit.js"></script></body></html>"""

WALK = """async () => {
  const out = {}; const w = ms => new Promise(r => setTimeout(r, ms));
  const sc = document.getElementById('sc');
  const top = n => n.getBoundingClientRect().top - sc.getBoundingClientRect().top;
  const para = 'A line of the answer that keeps growing down the panel while she reads her own question above it. ';
  const t = HoolaChat.mount(document.getElementById('r'), {scroller: sc});
  const H = []; for (let i = 0; i < 6; i++) { H.push({id: 'q' + i, role: 'her', text: 'Earlier question ' + i}); H.push({id: 'a' + i, role: 'hoola', text: para.repeat(4)}); }
  t.sync({key: 'a', messages: H, working: false});
  out.historyAtEnd = Math.abs(sc.scrollHeight - sc.scrollTop - sc.clientHeight) < 2;
  const me = t.her('Which invoices are still unpaid?', {pending: true});
  await w(700);
  out.landed = top(me); out.holding = t.holding;
  out.weights = {txt: getComputedStyle(document.querySelector('.hck-txt')).fontWeight, bub: getComputedStyle(me.querySelector('.hck-bub')).fontWeight,
                 size: getComputedStyle(me.querySelector('.hck-bub')).fontSize, lh: getComputedStyle(me.querySelector('.hck-bub')).lineHeight};
  t.begin('Reading the books');
  const moved = [];
  for (let n = 1; n <= 14; n++) { t.text(para.repeat(n)); for (let k = 0; k < 6; k++) { await w(60); moved.push(Math.round(top(me) - out.landed)); } }
  out.moved = Math.max(...moved.map(Math.abs));
  const txts = document.querySelectorAll('#r .hck-txt'); out.past = txts[txts.length - 1].getBoundingClientRect().bottom > sc.getBoundingClientRect().bottom + 50;
  sc.dispatchEvent(new WheelEvent('wheel', {deltaY: -200, bubbles: true})); sc.scrollTop -= 200; await w(700);
  out.released = !t.holding && top(me) > out.landed + 150;
  t.end();
  // a panel that hands the kit a stand-in scroller (Web Studio, App Studio, Game Dev) still lands, in the box that scrolls
  const t2 = HoolaChat.mount(document.getElementById('r2'), {scroller: document.createElement('div')});
  t2.sync({key: 'b', messages: H.slice(0, 6), working: false});
  const me2 = t2.her('A question in a studio', {pending: true}); await w(700);
  const box = document.getElementById('out');
  out.standIn = Math.round(me2.getBoundingClientRect().top - box.getBoundingClientRect().top);
  document.documentElement.dataset.theme = 'dark'; await w(30);
  out.dark = {txt: getComputedStyle(document.querySelector('.hck-txt')).fontWeight, bub: getComputedStyle(me.querySelector('.hck-bub')).fontWeight};
  return out;
}"""


def test_a_kit_chat_lands_like_the_main_chat(arena_server):
    base, browser, _key = arena_server
    ctx = browser.new_context(viewport={"width": 900, "height": 900})
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        pg.route(base + "/__kit201", lambda r: r.fulfill(status=200, content_type="text/html", body=PAGE))
        pg.goto(base + "/__kit201"); pg.wait_for_function("() => window.HoolaChat && window.HoolaChat.lander && window.HoolaStream")
        o = pg.evaluate(WALK)
    finally:
        ctx.close()
    assert not errs, errs
    assert o["historyAtEnd"], "history opens at its end, nothing landed"
    assert abs(o["landed"] - 16) <= 3 and o["holding"], o
    assert o["weights"] == {"txt": "400", "bub": "430", "size": "16px", "lh": "22.4px"}, o["weights"]
    assert o["moved"] <= 1, f"her message moved {o['moved']} px while the reply grew"
    assert o["past"], "the reply really grew past the panel"
    assert o["released"], "once she scrolls the view is hers"
    assert abs(o["standIn"] - 16) <= 3, o["standIn"]
    assert o["dark"] == {"txt": "360", "bub": "400"}, o["dark"]
