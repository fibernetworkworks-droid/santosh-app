"""v0.801 APP STUDIO PREMIUM PASS (owner: "THE WEB CONSOLE APP DEVELOPMENT SECTION LOOKS STALE AND OLD --- MAKE ALL PAGES
FUNCTION PROPERLY, ALIGN THE TEXT, TAB, BUTTONS ETC PERFECT, MAKE IT MORE ADVANCED AND PREMIUM").

Held here: every workspace page carries the same header (title + one plain line, controls on the right), panels carry
one header row, the tab bar has a single current tab that fits the pane, the page never scrolls sideways at phone width,
no Hinglish chrome is left in the Studio, the iPhone runner note is said once, plurals are right, a step with no recorded
time shows no clock, and the motion runs once per page (never on a poll redraw)."""
import threading
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401
from tests.test_v128_appdesign import T, app_env  # noqa: F401
from tests.test_v0693_app_studio import _designed_app

D = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
VIEWS = ("plan", "looks", "screens", "prototype", "android", "iphone", "store", "data", "business", "health", "settings", "history")


def test_markers_and_english_chrome():
    js = (D / "appstudio.js").read_text()
    css = (D / "appstudio.css").read_text()
    for m in ('<header class="phd">', "const ph = (title", "const plural =", "const iosWhy =", "VIEW_IC", "data-fpick",
              "pane.dataset.fresh === '1'", "classList.add('pin')", "Approve design", "Approve plan · make 3 looks"):
        assert m in js, m
    for gone in ("Design pakka`", "Haan, make 3 looks", "Waiting for your Haan", "naya checkout sirf", "Hindi aur Marathi bhi",
                 "gift wrap field\". Only", "orders mein gift wrap", "Udhaar due<"):
        assert gone not in js, gone
    for m in (".ws-app .phd", ".ws-app .pnh", "container-name:aspane", ".ws-app .pbody.pin", "prefers-reduced-motion",
              ".ws-app .mod>.b{margin-top:auto", ".ws-app .chat{width:auto}"):
        assert m in css, m
    assert ".ws-app .pbody.in" not in css                       # '.in' is the input class: it drew a border round the page
    import re
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css.split("v0.794 APP STUDIO PREMIUM PASS")[1])    # tokens only


def test_page_carries_a_fresh_stamp():
    html = (D / "appstudio.html").read_text()
    assert "appstudio.js?v=0.815.0" in html and "appstudio.css?v=0.815.0" in html     # a changed file never sits in the cache


def test_server_lines_in_english(app_env):
    from app.appmaker import quality as Q
    src = Path(Q.__file__).read_text()
    assert "No crash from any phone in" in src and "din mein" not in src.split('"says": (')[-1][:400]
    from app.appmaker import service as S
    assert "Design approved (v" in Path(S.__file__).read_text()


def test_every_page_premium_in_a_real_browser(app_env, arena_server):
    out = {}
    th = threading.Thread(target=lambda: out.update(v=_designed_app()))
    th.start()
    th.join(600)
    v = out["v"]
    base, browser, key = arena_server
    errs = []
    for width in (1440, 390):
        ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844})
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        for view in VIEWS:
            pg.goto(base + f"/console/apps#/app/{v['id']}/{view}")
            pg.wait_for_function("v => { const p = document.querySelector('#asPane'); return p && p.dataset.view === v && p.querySelector('.pbody .phd .pht h2'); }",
                                 arg=view, timeout=20000)
            got = pg.evaluate("""() => {
              const pane = document.querySelector('#asPane'), pb = pane.querySelector('.pbody'), h = pb.querySelector('.phd');
              const pr = pane.getBoundingClientRect(), hr = h.getBoundingClientRect();
              const cur = [...pane.querySelectorAll('.views [aria-current=page]')];
              const pbs = getComputedStyle(pb);
              const txt = pb.innerText;
              return {first: pb.firstElementChild === h, inPane: hr.left >= pr.left && hr.right <= pr.right + 1,
                      cur: cur.length, border: pbs.borderTopWidth, sideways: document.documentElement.scrollWidth - innerWidth,
                      panelsHead: [...pb.querySelectorAll('.panel')].every(p => !p.querySelector(':scope > b')),
                      hinglish: /\\b(pakka|karo|kijiye|banegi|aaya|logon|aur Marathi)\\b/i.test(txt),
                      zero: [...document.querySelectorAll('#asState .tm, #asPane .acts .tm')].some(t => t.textContent.trim() === '0s')};
            }""")
            assert got["first"] and got["inPane"], (view, width, got)
            assert got["cur"] == (0 if view == "history" else 1), (view, got)
            assert got["border"] == "0px", (view, got)              # the page body is never boxed
            assert got["sideways"] <= 1, (view, width, got)          # never scrolls sideways
            assert got["panelsHead"], (view, got)                  # every panel uses the one header row
            assert not got["hinglish"], (view, pg.inner_text("#asPane .pbody")[:400])
            assert not got["zero"], view
            if width == 1440 and view != "history":                 # the whole tab bar fits the pane at desktop width
                fit = pg.evaluate("""() => { const p = document.querySelector('#asPane .ptop').getBoundingClientRect();
                  const b = [...document.querySelectorAll('#asPane .views button')]; return b.every(x => x.getBoundingClientRect().right <= p.right + 1); }""")
                assert fit, view
        # motion once per page: a poll redraw of the same view keeps the page still
        pg.goto(base + f"/console/apps#/app/{v['id']}/business")
        pg.wait_for_function("() => { const p = document.querySelector('#asPane'); return p && p.dataset.view === 'business' && p.querySelector('.pbody.pin .stat'); }", timeout=20000)
        pg.evaluate("() => { document.querySelector('#asPane .pbody').classList.remove('pin'); }")
        pg.click("#asPane .views [data-view='business']")
        pg.wait_for_timeout(600)
        assert pg.locator("#asPane .pbody.pin").count() == 0
        pg.click("#asPane .views [data-view='health']")
        pg.wait_for_function("() => { const p = document.querySelector('#asPane'); return p && p.dataset.view === 'health' && p.querySelector('.pbody.pin'); }", timeout=20000)
        ctx.close()
    assert not errs, errs
