"""v0.646 WEB DEVELOPMENT PANEL 2: the panel works ON ITS OWN, end to end (owner: "when I type the prompt it goes to main
chat on homepage ... make it perfect end to end" + "bad with alignment ... clicking the type section borders it with a
blue line").

Held here: the home ask creates the website through /api/sites (never the home chat), the workspace walks plan -> looks ->
build -> preview on the server's own state, every site has its OWN Hoola thread (a separate conversation), the old-site /
screenshot design read happens in the panel, her taps keep confirm() + the server's hash, the `wdp-` prefix keeps the
Game Desk's `.wd-body` out, and in a real browser (Playwright, skipped without Chromium): the ask box has no inner focus
line, no two buttons overlap and no button clips its words in any tab (light, dark, phone), no sideways scroll at phone
width, no script errors, server text never becomes HTML. Screenshots: CONSOLE_SHOTS=<folder>."""
import os
import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.648.0"


def test_console_wiring():
    html = (CONSOLE / "v2.html").read_text()
    js = (CONSOLE / "v2.js").read_text()
    wd = (CONSOLE / "webdev.js").read_text()
    build = (CONSOLE / "build.js").read_text()
    css = (CONSOLE / "v2.css").read_text()
    assert 'id="v-webdev"' in html and re.search(r'/static/console/webdev\.js\?v=[\d.]+"', html)
    assert "['webdev','Web Development']" in js and "HoolaWebDev(" in js and "B?.openSite?.(" in js
    assert "if (v === 'webdev') WD?.open(" in js
    assert "async openSite(p, tab, editMode)" in build and "upsert('site_board', p)" in build
    for tab in ("overview", "build", "edit", "code", "data", "integrations", "publish", "health", "settings"):
        assert f"['{tab}'," in wd
    # nothing from this page goes to the home chat any more
    init = js.split("window.HoolaWebDev && !WD", 1)[1][:400]
    assert "go('chat')" not in init and "composer.requestSubmit" not in init and "say:" not in init
    assert "say(" not in wd.replace("data-wd-say", "")
    # the home ask makes the site here, the steps are the server's own routes, the thread is its own conversation
    assert "api('POST', '/api/sites', {brief: t, conversation_id: conv})" in wd       # never conv "" (= her home chat)
    assert wd.index("api('POST', '/api/conversations')") < wd.index("api('POST', '/api/sites',")
    for route in ("/plan`", "/answers`", "/look`", "/change`", "/resume`", "/stop`"):
        assert route in wd
    assert "api('POST', '/api/conversations')" in wd and "hoola.wdp.conv." in wd
    assert "/messages`, {text," in wd and "never start a new website unless I ask" in wd
    assert "'/api/site-design/read'" in wd and "'/api/site-design/use'" in wd and "proof" in wd
    # her taps: every live / rollback / takedown / redirect write asks first and carries the server's hash
    for act in ("golive", "rollback", "takedown", "delete"):
        blk = wd.split(f"act === '{act}'", 1)[1][:400]
        assert "confirm(" in blk
    assert "{hash: d.hash}" in wd and "hash: S(card.hash)" in wd and "{hash: f.dataset.hash, drop}" in wd
    assert "esc(" in wd and wd.count("esc(") > 80                                        # server text drawn through esc()
    assert ".map(HEX)" in wd and "/^#[0-9a-f]{3,8}$/i" in wd                                 # a look colour is drawn only as #hex
    blk = css.split("v0.646 WEB DEVELOPMENT PANEL 2", 1)[1]
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", blk)                                  # theme tokens only, no raw colours
    assert "#app .wd-" not in blk and 'class="wd-' not in wd and "wd-pill" not in wd               # own prefix, the Game Desk keeps .wd-*
    assert ".wdp-ask:focus-within" in blk and "#app .wdp-ask textarea:focus-visible" in blk


def _site(status="ready", version=1, looks=None):
    """A site as the panel sees it (the real build runs Chromium itself, which cannot nest in this browser test)."""
    import json
    from app.db import session
    from app.site import service as S
    from app.site.models import Site
    v = S.new(T, "Sharma Sweets mithai dukaan ki website <b>Akola</b>", name="Sharma <i>Sweets</i>",
              answers={"phone": "9876543210", "address": "Main Road, Akola"})
    with session() as s:
        r = s.get(Site, v["id"])
        r.status, r.version, r.stage = status, version, "done" if version else "look"
        if looks is not None:
            r.looks = json.dumps(looks)
    return S.get(T, v["id"])


_OVERLAP = """() => {
  const vis = [...document.querySelectorAll('#webdev button, #webdev a.wdp-btn')].filter(b => b.offsetParent && b.getClientRects().length);
  const bad = [];
  for (const b of vis) if (b.scrollWidth > b.clientWidth + 2 && !b.closest('.wdp-tabs')) bad.push('clipped: ' + b.textContent.trim().slice(0, 40));
  const r = vis.map(b => [b, b.getBoundingClientRect()]);
  for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
    const [a, A] = r[i], [b, B] = r[j];
    if (a.contains(b) || b.contains(a) || a.closest('.wdp-tabs') || A.width < 1 || B.width < 1) continue;
    if (A.left < B.right - 1 && B.left < A.right - 1 && A.top < B.bottom - 1 && B.top < A.bottom - 1)
      bad.push('overlap: ' + a.textContent.trim().slice(0, 30) + ' / ' + b.textContent.trim().slice(0, 30));
  }
  return bad;
}"""


def _no_overlap(page, where):
    bad = page.evaluate(_OVERLAP)
    assert not bad, f"{where}: {bad}"


def test_panel_in_a_real_browser(arena_server):
    base, browser, key = arena_server
    looks = [{"style": "warm", "label": f"Look {i}", "shots": {}, "tokens": {"bg": "#ffffff", "primary": "red;x:1", "accent": "#7A1F17"},
              "dna": {"concept": f"Concept <b>{i}</b>"}} for i in range(3)]
    _site("looks", 0, looks)
    g = _site()
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        page.goto(base + "/console/")
        page.wait_for_selector('#snav [data-v="webdev"]', timeout=20000)
        page.click('#snav [data-v="webdev"]')
        page.wait_for_selector("#webdev .wdp-site", timeout=20000)
        home = page.inner_text("#webdev")
        assert "What should we build today?" in home and "Move my old site" in home and "Sweet shop" in home
        assert page.locator("#webdev .wdp-site", has_text="Sharma <i>Sweets</i>").count() == 2   # her name is text, never markup
        # the blue line: focusing the ask leaves the textarea itself without an outline; the CARD carries a soft ring
        page.click("#wdAsk")
        st = page.evaluate("""() => { const t = document.querySelector('#wdAsk'), c = t.closest('.wdp-ask'), s = getComputedStyle(t);
            return [s.outlineStyle, s.borderTopWidth, s.boxShadow, getComputedStyle(c).boxShadow]; }""")
        assert st[0] == "none" and st[1] == "0px" and st[2] == "none" and st[3] != "none", st
        _no_overlap(page, f"home {scheme}")
        if shots:
            page.screenshot(path=f"{shots}/webdev-home-{scheme}.png", full_page=True)
        page.click("#webdev [data-wd-start='old']")
        page.wait_for_selector("#webdev form[data-wd-form=old] input[name=url]")
        _no_overlap(page, f"home old-site {scheme}")
        if scheme == "light":
            # THE FIX: one line in the ask -> a website made by the panel itself, its plan card here; the home chat untouched
            n_before = page.locator("#webdev .wdp-site").count()
            page.click("#webdev [data-wd-type='Clinic']")
            page.fill("#wdAsk", "Dr Mehta clinic Akola ki website banao - timings, doctors aur appointment")
            page.keyboard.press("Enter")
            page.wait_for_selector("#webdev form[data-wd-form=plan]", timeout=20000)
            assert page.evaluate("location.hash || ''") in ("", "#webdev") or "chat" not in page.evaluate("location.hash")
            assert page.locator("#v-webdev").is_visible() and not page.locator("#v-chat").is_visible()
            assert page.input_value("#msg") == ""
            page.wait_for_timeout(800)
            assert page.locator("#app.st").count() == 0                                   # the studio did not jump open
            assert page.locator("#webdev .wdp-steps li.now").inner_text().strip().endswith("Plan")
            assert page.locator("#webdev .wdp-page").count() >= 3
            _no_overlap(page, "plan card")
            if shots:
                page.screenshot(path=f"{shots}/webdev-plan.png", full_page=True)
            # its own Hoola thread: a separate conversation, the words stay in this panel
            conv = page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hoola.wdp.conv.')).map(k => localStorage.getItem(k))")
            assert len(conv) == 1 and conv[0]
            page.fill("#wdpTh", "Is website mein booking slot lagao")
            page.click("#webdev form[data-wd-form=thread] [type=submit]")
            page.locator("#wdpMsgs .wdp-msg.me", has_text="booking slot").wait_for(timeout=10000)
            msgs = page.evaluate(f"""async () => (await (await fetch('/api/conversations/{conv[0]}/messages',
                {{headers: {{Authorization: 'Bearer {key}'}}}})).json()).messages.map(m => m.text)""")
            assert any("booking slot" in m for m in msgs)
            assert page.input_value("#msg") == "" and page.locator("#v-webdev").is_visible()
            page.click("#webdev [data-wd-act='home']")
            page.wait_for_selector("#webdev .wdp-site")
            assert page.locator("#webdev .wdp-site").count() == n_before + 1
            # the three looks: colours only as #hex, a concept is text
            page.locator("#webdev .wdp-site", has_text="Pick a look").first.click()
            page.wait_for_selector("#webdev .wdp-look", timeout=10000)
            assert page.locator("#webdev .wdp-look").count() == 3
            assert page.locator("#webdev .wdp-swatches i").count() == 6                  # 'red;x:1' is not drawn
            assert "Concept <b>0</b>" in page.inner_text("#webdev .wdp-looks")
            _no_overlap(page, "looks")
            if shots:
                page.screenshot(path=f"{shots}/webdev-looks.png", full_page=True)
            page.click("#webdev [data-wd-act='home']")
            page.wait_for_selector("#webdev .wdp-site")
        # the built site: workspace with the preview, then every tab
        page.locator("#webdev .wdp-site", has_text="Ready · v1").first.click()
        page.wait_for_selector("#webdev .wdp-tabs", timeout=10000)
        assert page.locator("#webdev .wdp-tabs button").count() == 9
        assert page.locator("#webdev .wdp-tabs [aria-current=page]").inner_text() == "Workspace"
        page.wait_for_selector("#webdev .wdp-frame iframe", timeout=10000)
        page.click("#webdev [data-wd-dev='phone']")
        page.wait_for_selector("#webdev .wdp-frame.phone")
        _no_overlap(page, f"workspace {scheme}")
        if shots:
            page.screenshot(path=f"{shots}/webdev-workspace-{scheme}.png", full_page=True)
        for tab, needle in (("build", "Live preview and build board"), ("edit", "Visual edit"), ("code", "real code"),
                            ("data", "Lists on this site"), ("integrations", "Shop and cart"), ("publish", "Connect your domain"),
                            ("health", "Speed on real phones"), ("settings", "Business details")):
            page.click(f"#webdev .wdp-tabs [data-wd-tab='{tab}']")
            page.locator("#wdpPane", has_text=needle).wait_for(timeout=15000)
            _no_overlap(page, f"{tab} {scheme}")
            if shots:
                page.screenshot(path=f"{shots}/webdev-{tab}-{scheme}.png", full_page=True)
        assert page.input_value("#webdev input[name=phone]") == "9876543210"
        # build tab -> the existing Website studio opens beside the panel
        page.click("#webdev .wdp-tabs [data-wd-tab='build']")
        page.wait_for_selector("#webdev [data-wd-studio='preview']")
        page.click("#webdev [data-wd-studio='preview']")
        page.wait_for_selector("#app.st", timeout=10000)
        assert "Website studio" in page.inner_text("#studio")
        page.click("#studio [data-ba=close]")
        # integrations ask in this site's thread, never the home chat
        page.click("#webdev .wdp-tabs [data-wd-tab='integrations']")
        page.locator("#webdev [data-wd-ask]", has_text="Add").first.click()
        page.wait_for_selector("#wdpMsgs .wdp-msg.me", timeout=10000)
        assert page.locator("#v-webdev").is_visible() and page.input_value("#msg") == ""
        # publish: the launch check asks the server and shows its card (nothing goes live here)
        page.click("#webdev .wdp-tabs [data-wd-tab='publish']")
        page.wait_for_selector("#webdev [data-wd-act='launch']", timeout=10000)
        page.click("#webdev [data-wd-act='launch']")
        page.wait_for_selector("#wdLaunch .wdp-launch, #wdLaunch .wdp-li", timeout=15000)
        page.click("#webdev [data-wd-act='home']")
        page.wait_for_selector("#webdev .wdp-site")
        ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/console/")
    page.wait_for_selector('#snav [data-v="webdev"]', state="attached", timeout=20000)
    page.evaluate("document.querySelector('#snav [data-v=\"webdev\"]').click()")
    page.wait_for_selector("#webdev .wdp-site")
    wide = "document.querySelector('#webdev').scrollWidth <= document.querySelector('#webdev').clientWidth + 1"
    assert page.evaluate(wide)
    _no_overlap(page, "phone home")
    page.locator("#webdev .wdp-site", has_text="Ready · v1").first.click()
    page.wait_for_selector("#webdev .wdp-tabs")
    assert page.evaluate(wide)
    _no_overlap(page, "phone workspace")
    if shots:
        page.screenshot(path=f"{shots}/webdev-phone.png", full_page=True)
    ctx.close()
    # the seeded site has no files, so its sandboxed preview shows Chromium's JSON viewer for the 404 - that viewer's own
    # localStorage read is refused by the sandbox (as it must be); every other script error fails the test
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert g["id"] and not errors, errors
