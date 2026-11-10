"""v0.667 PREMIUM STUDIO: the Figma design ('Hoola Web Studio - Premium redesign', owner: 'GO BUILD THE DESIGN') built into
the Web Studio - Literata headline + replies, the sans for everything she taps, the mono for ticking numbers; a dark
'New website' with Cmd/Ctrl K; site cards with a tint + 'Edited ...'; the top bar with a dark Publish; her request as the
first chat bubble; Hoola's name + time above each reply; the live work card (title, step, whole clock, progress, every
step's time, parts writing at once, Pause); 'Worked for' + Version N ready + Go live + next steps after a build; LIVE tag,
page pills and a browser frame on the live canvas."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v0664_asli_samay import _slow_fake
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ST = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_design_markers():
    js, css, html = (ST / "webstudio.js").read_text(), (ST / "webstudio.css").read_text(), (ST / "webstudio.html").read_text()
    assert "JetBrains+Mono" in html and "7..72,500" in html                       # the three typefaces load
    for m in ("class=\"eyebrow\"", "<kbd>", "class=\"tsep\"", "b dark", "working wcard", "chatact wcard", "class=\"wfoot\"",
              "class=\"vcard\"", "Go live…", "class=\"sugg\"", "class=\"who\"", "class=\"dday\"", "class=\"livetag\"",
              "class=\"bwin\"", "id=\"wsLUrl\"", "statusText(", "ago(v.updated_at)", "metaKey || e.ctrlKey"):
        assert m in js, m
    assert "font-family:'Literata'" in css and "--solid:#17161C" in css and "--live:#E5484D" in css and "--live:#F2777A" in css
    assert ".hero h1{font-family:'Literata'" in css and "font-size:52px" in css
    # weights stop at 600 in the new layer
    layer = css.split("v0.667 PREMIUM STUDIO", 1)[1]
    assert "font-weight:700" not in layer and "font-weight:800" not in layer


def test_design_in_a_browser(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "false")
    monkeypatch.setenv("SITE_PARALLEL", "2")
    monkeypatch.setenv("SITE_WORKER", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots")))
    _slow_fake(monkeypatch, per=0.1, n=12)
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/console/web")
    page.wait_for_selector("#wsAsk", timeout=20000)
    fam = page.evaluate("getComputedStyle(document.querySelector('.hero h1')).fontFamily")
    assert "Literata" in fam, fam
    assert page.locator("#ws .eyebrow").count() == 1 and page.locator("#ws .new kbd").count() == 1
    # Ctrl/Cmd K from another page comes back to the ask box
    page.goto(base + "/console/web#/sites")
    page.wait_for_selector("#wsFind")
    page.keyboard.press("Control+k")
    page.wait_for_selector("#wsAsk", timeout=5000)
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    page.wait_for_selector("#ws .lks button", timeout=120000)
    assert "Sharma Sweets mithai" in page.inner_text("#wsMsgs .me")              # her request opens the chat
    assert page.locator("#wsMsgs .who").count() >= 1
    page.click("#ws [data-act='pick-look']")
    page.wait_for_selector("#wsState .wcard .whead .tm", timeout=30000)        # the live work card
    head = page.inner_text("#wsState .wcard .wt")
    assert head.startswith("Building your website"), head
    assert page.locator("#wsState .wcard .wfoot").count() == 1
    page.wait_for_selector("#ws .lbar .livetag", timeout=30000)
    assert page.locator("#ws .bwin .bchrome").count() == 1
    assert page.evaluate("getComputedStyle(document.querySelector('.top .b.dark')).backgroundColor") == "rgb(23, 22, 28)"
    page.wait_for_selector("#ws #wsPane .url", timeout=180000)                 # built
    page.wait_for_selector("#wsState .vcard", timeout=15000)
    assert "Version 1 is ready" in page.inner_text("#wsState .vcard")
    assert page.inner_text("#wsState details.actd.done summary").startswith("Worked for")
    page.click("#wsState .vcard [data-view='publish']")
    page.wait_for_selector("#wsPane :text('Connect your domain')", timeout=15000)
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
