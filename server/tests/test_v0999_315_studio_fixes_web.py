"""v0.999.315 STUDIO FIXES (front end): verified flaws in the Hoola Web Studio page, fixed in webstudio.js / .css.

1 the site chat kept polling only until the first network blip  2 it kept polling after she left the site
3 a failed send looked sent (row stayed, words + files lost)       4 any blip on the chat check made a NEW chat
5 a redraw the server started wiped what she was typing            6 a failed website list read as "No website yet"
7 the phone sidebar stayed 256px wide                              8 Code / History ran off a 390px screen
9 tool names and setting names shown to her                        10 raw HTML error pages shown as the error
11 empty toasts                                                    12 a liked site's colour not checked as #hex
13 an old Show more appended to a new template search              14 the upgrade offer on a site built seconds ago
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (ROOT / "webstudio.js").read_text()
CSS = (ROOT / "webstudio.css").read_text()


def _fn(name: str) -> str:
    """The text of one function in webstudio.js (to the next top-level function)."""
    i = JS.index(name)
    j = JS.find("\n  async function ", i + 10)
    k = JS.find("\n  function ", i + 10)
    ends = [x for x in (j, k) if x > 0]
    return JS[i:min(ends)] if ends else JS[i:]


def test_1_2_thread_polling_survives_blips_and_stops_on_leaving():
    rt = _fn("async function readThread()")
    assert "const c = THREAD.conv, gen = THREAD.gen" in rt
    assert "THREAD.fails = (THREAD.fails || 0) + 1" in rt and "1500 * 2 **" in rt        # backoff on a blip
    assert "threadLater(" in rt and "THREAD.timer = setTimeout(readThread" not in rt
    tl = _fn("function threadLater(")
    assert "gen !== THREAD.gen" in tl and "S(CUR.id) !== S(THREAD.site)" in tl
    route = _fn("async function route()")
    assert "THREAD.gen = (THREAD.gen || 0) + 1; THREAD.conv = ''" in route            # leaving the site ends it for good
    assert "gen: (THREAD.gen || 0) + 1" in JS                                          # every open is a new generation
    assert "setTimeout(readThread" not in JS


def test_3_failed_send_puts_her_words_and_files_back():
    a = _fn("async function ask(text")
    assert "const said = text;" in a and "allFiles = L(THREAD.files).slice()" in a
    assert "THREAD.rows = THREAD.rows.filter(r => S(r.id) !== id)" in a
    assert "box.value = said" in a and "THREAD.files = allFiles" in a
    assert "toast('Not sent: '" in a


def test_4_only_a_gone_chat_is_replaced():
    e = _fn("async function ensureConv()")
    assert "const site = S(CUR.id)" in e and e.index("const site = S(CUR.id)") < e.index("await api(")
    assert "e.status === 404 || e.status === 410" in e and "catch { c = ''; }" not in e
    assert "store.set(convKey(site), c)" in e and "if (!CUR || S(CUR.id) !== site) return c;" in e


def test_5_server_redraws_keep_her_typing():
    assert "function paneTyping()" in JS and "function autoPane()" in JS
    sp = _fn("function startPoll()")
    assert "autoPane()" in sp and "drawPane()" not in sp
    rl = _fn("async function reload(opts = {})")
    assert "if (opts.auto) autoPane(); else drawPane();" in rl
    assert "reload({auto: true}); }, 300);" in JS                                      # the live-stream wake
    assert JS.count("reload({auto: true})") >= 3


def test_6_failed_list_says_so_with_try_again():
    assert "LISTS_ERR = a.status === 'fulfilled' ? ''" in JS
    assert "Your websites could not be loaded." in JS and 'data-act="lists-retry"' in JS
    assert "act === 'lists-retry'" in JS
    assert JS.count("noSites(") >= 2 and "const noSites = empty =>" in JS


def test_7_8_phone_css():
    tail = CSS[CSS.index("v0.999.315 STUDIO FIXES"):]
    assert "@media (max-width:760px)" in tail and ".side{width:auto" in tail.replace(".home>.side,", "")
    assert CSS.index("v0.999.315 STUDIO FIXES") > CSS.index(".side{width:256px")     # the phone rule now comes last
    assert ".ptop.phd{flex-wrap:wrap" in tail and ".ver{flex-wrap:wrap" in tail
    assert ".edbar.upgcan .upgtx{" in tail and "white-space:normal" in tail


def test_9_no_internal_names():
    assert "website_dekho" not in JS and "SITE_MAIL_" not in JS
    assert "S(p.tool)" not in JS and "S(pl.tool)" not in JS
    assert JS.count("|| 'Working', at") == 2


def test_10_raw_errors_are_words():
    assert "function plainErr(" in JS and "The server did not answer properly. Try again." in JS
    assert "await r.text()); return r;" not in JS                                      # raw text was the error message
    assert "JSON.parse(e.message)" not in JS
    assert "return data == null ? {} : data;" in JS


def test_11_no_empty_toasts():
    for m in re.finditer(r"toast\(S\(r\??\.say\)[^;]*\);", JS):
        assert "||" in m.group(0), m.group(0)


def test_12_13_14():
    assert "background:${esc(c)}" not in JS and "HEX(c) || 'transparent'" in JS
    lt = _fn("async function loadTpl(reset)")
    assert "const tok = TPL.req = (TPL.req || 0) + 1" in lt and "tok !== TPL.req" in lt
    assert "function upgOffer(v)" in JS and "u.can && upgOffer(v)" in JS
    assert "86400" in _fn("function upgOffer(v)") and "store.get(UPG_HIDE(v.id))" in JS
    assert 'data-act="upg-hide"' in JS and "d.act === 'upg-hide'" in JS
    assert 'class="upgtx"' in JS


def test_js_parses():
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("no node")
    r = subprocess.run([node, "--check", str(ROOT / "webstudio.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ---------------- a real browser at phone width ----------------
from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: E402,F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import site_env  # noqa: E402,F401  (fixture)

NO_SIDEWAYS = "document.documentElement.scrollWidth <= innerWidth + 1"


def test_phone_walk_home_code_history(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots")))
    errors = []
    # build the site at desktop width (the same path as test_v0663), then walk it on a phone
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + "/console/web#/")
    page.wait_for_selector("#wsAsk", timeout=20000)
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    page.wait_for_selector("#ws .lks button", timeout=120000)
    page.click("#ws [data-act='pick-look']")
    page.wait_for_selector("#ws #wsPane .url", timeout=120000)
    site = page.evaluate("location.hash").split("/")[2]
    # a site built seconds ago does not get the upgrade offer
    assert page.locator("#ws [data-upgrade='can']").count() == 0
    ctx.close()

    ctx = browser.new_context(viewport={"width": 390, "height": 800})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    calls = []
    page.on("request", lambda r: "/messages" in r.url and r.method == "GET" and calls.append(r.url))
    page.goto(base + "/console/web#/")
    page.wait_for_selector("#wsAsk", timeout=20000)
    assert page.evaluate(NO_SIDEWAYS), page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    sw = page.evaluate("[document.querySelector('.side').getBoundingClientRect().width, innerWidth]")
    assert sw[0] >= sw[1] - 2, sw                                                   # the sidebar spans the phone
    for view in ("code", "history"):
        page.goto(base + f"/console/web#/site/{site}/{view}")
        page.wait_for_selector("#wsPane .ptop", timeout=20000)
        if view == "code":
            page.wait_for_selector("#ws [data-file]", timeout=15000)
        else:
            page.wait_for_selector("#wsPane .ver", timeout=15000)
        page.wait_for_timeout(300)
        assert page.evaluate(NO_SIDEWAYS), (view, page.evaluate("[document.documentElement.scrollWidth, innerWidth]"))
        over = page.evaluate("""() => [...document.querySelectorAll('#wsPane .ptop *, #wsPane .ver *')]
            .filter(e => e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).map(e => e.className + ':' + e.textContent.slice(0, 30))""")
        assert not over, (view, over)
    # leaving the site stops the chat polling
    page.goto(base + "/console/web#/")
    page.wait_for_selector("#wsAsk")
    page.wait_for_timeout(500)
    n = len(calls)
    page.wait_for_timeout(4000)
    assert len(calls) == n, calls[n:]
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
