"""v0.649 HOOLA WEB STUDIO - the website builder as its own full-screen app (owner-approved prototype: "PERFECT").

Held here:
- /console/web serves the Studio with the console's strict CSP; the console's "Web Development" row opens it (the old
  in-console panel webdev.js is gone, so nothing builds into the home page any more);
- Build | Plan on the home: Build = the site is made and its plan accepted at once (the three looks start); Plan = the
  architect's plan written from her words, revised in the chat, built only by "Build this plan" (the hash she saw);
- THREE FULL LOOKS (service._full_looks): every other page of the plan is written ONCE, and each look is assembled as the
  WHOLE site in its own design, served at /api/site-preview/<token>/__looks/<i>/full/; after she picks a look the build
  writes NO page again (they were written for the looks);
- in a real browser (Playwright, skipped without Chromium): the home has its own sidebar and no inner focus line on the
  ask box; one line in Build mode lands in the site's workspace with the three looks; each look's own pages open inside
  the preview at computer / tablet / phone size; plan mode shows the plan as a document; no two buttons overlap, no
  sideways scroll at phone width, no script errors, server text never becomes HTML. Screenshots: CONSOLE_SHOTS=<folder>.
"""
import os
import re
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.864.0"


def test_studio_is_its_own_app():
    html = (CONSOLE / "webstudio.html").read_text()
    js = (CONSOLE / "webstudio.js").read_text()
    v2 = (CONSOLE / "v2.js").read_text()
    v2h = (CONSOLE / "v2.html").read_text()
    assert re.search(r'/static/console/webstudio\.js\?v=[\d.]+"', html) and "webstudio.css" in html and "md.js" in html
    assert not (CONSOLE / "webdev.js").exists() and "webdev.js" not in v2h and 'id="v-webdev"' not in v2h
    assert "location.assign('/console/web'" in v2 and "HoolaWebDev" not in v2
    # Build | Plan, and both start with the three full looks
    assert "api('POST', '/api/site-architect', {words: text" in js and "const body = {brief: text" in js and "api('POST', '/api/sites', body)" in js
    assert "/plan`, {conversation_id: conv}" in js and "/approve`, {hash: d.hash" in js and "/revise`, {words: t}" in js
    assert "/look`, {index: LOOK" in js and "data-dev" in js and "tablet" in js
    # her own thread per site, never the home chat; every server value through esc(); colours only as #hex
    assert "never start a new website unless I ask" in js and "hoola.wdp.conv." in js and "Plan mode: reply with the PLAN only" in js   # v0.782 TEEN MODE: the plan hint now asks for the plan's sections
    assert js.count("esc(") > 100 and ".map(HEX)" in js
    for act in ("golive", "rollback", "takedown", "delete"):
        assert "confirm(" in js.split(f"act === '{act}'", 1)[1][:400]
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = c.get("/console/web")
    assert r.status_code == 200 and "Hoola Web Studio" in r.text
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"] and r.headers["x-frame-options"] == "DENY"


def test_three_full_looks_then_no_page_written_twice(site_env, monkeypatch):
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    from app.site import build as B
    from app.site import service as S
    c = TestClient(app)
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par. Phone 98765 43210", "", name="Sharma Sweets")
    assert c.post(f"/api/sites/{v['id']}/plan", json={}).status_code == 200
    g = S.get(T, v["id"])
    assert g["status"] == "looks" and len(g["looks"]) == 3
    assert all(lk["full"] and lk["preview"].endswith(f"__looks/{i}/full/") for i, lk in enumerate(g["looks"]))
    pages = [p["slug"] for p in g["plan"]["pages"]]
    assert len(pages) >= 3
    base = B.site_dir(T, v["id"]) / "looks"
    for i in range(3):
        for slug in pages:
            f = base / str(i) / "full" / ("index.html" if slug == "home" else f"{slug}/index.html")
            assert f.is_file(), f
    # each look is the same words in its own design
    a = (base / "0" / "full" / "index.html").read_text()
    b = (base / "1" / "full" / "index.html").read_text()
    assert a != b
    # every section of the plan was written exactly once (3 look heroes / tops + the rest once)
    secs = [x[1] for x in site_env.calls if x[0] == "section"]
    total = sum(len(p["sections"]) for p in S._j(S._load(v["id"]).plan, {})["pages"])
    tops = sum(1 for x in secs if x.startswith("s-home-"))
    assert len(secs) == len(set(secs)) + (tops - len({x for x in secs if x.startswith("s-home-")}))
    assert len({x for x in secs}) == total
    # the full look is served by its preview token
    tok = g["preview"].rsplit("/api/site-preview/", 1)[1].strip("/")
    other = next(s for s in pages if s != "home")
    r = c.get(f"/api/site-preview/{tok}/__looks/2/full/{other}/")
    assert r.status_code == 200 and "<html" in r.text.lower()
    # she picks a look -> the build writes no page again
    n = len(site_env.calls)
    assert c.post(f"/api/sites/{v['id']}/look", json={"index": 2}).status_code == 200
    again = [x for x in site_env.calls[n:] if x[0] == "section"]
    assert again == [], again
    assert S.get(T, v["id"])["status"] == "ready"


def test_full_looks_stay_page_tops_when_off_or_too_big(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import service as S
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    monkeypatch.setenv("SITE_FULL_LOOKS_MAX", "3")
    get_settings.cache_clear()
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par", "", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    g = S.get(T, v["id"])
    assert all(not lk["full"] and lk["preview"].endswith(f"__looks/{i}/site/") for i, lk in enumerate(g["looks"]))
    secs = [x[1] for x in site_env.calls if x[0] == "section"]
    assert secs and all(x.startswith("s-home-") for x in secs)                 # page tops only, as before


_OVERLAP = """() => {
  const vis = [...document.querySelectorAll('#ws button, #ws a.b, #ws a.nav')].filter(b => b.offsetParent && b.getClientRects().length);
  const bad = [];
  for (const b of vis) if (b.scrollWidth > b.clientWidth + 2 && !b.closest('.views, .lks')) bad.push('clipped: ' + b.textContent.trim().slice(0, 40));
  const r = vis.map(b => [b, b.getBoundingClientRect()]);
  for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
    const [a, A] = r[i], [b, B] = r[j];
    if (a.contains(b) || b.contains(a) || A.width < 1 || B.width < 1) continue;
    if (A.left < B.right - 1 && B.left < A.right - 1 && A.top < B.bottom - 1 && B.top < A.bottom - 1)
      bad.push('overlap: ' + a.textContent.trim().slice(0, 30) + ' / ' + b.textContent.trim().slice(0, 30));
  }
  return bad;
}"""


def _no_overlap(page, where):
    bad = page.evaluate(_OVERLAP)
    assert not bad, f"{where}: {bad}"


def test_studio_in_a_real_browser(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots in this test")))
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + "/console/web")
    page.wait_for_selector("#ws .side .brand", timeout=20000)
    assert "What should we build" in page.inner_text("#ws") or "Got an idea" in page.inner_text("#ws") or "What are we making" in page.inner_text("#ws")  # v0.836 L12: the greeting rotates by time of day (was one fixed line) and page.locator("#ws .side a.nav").count() >= 4
    page.click("#wsAsk")
    st = page.evaluate("""() => { const t = document.querySelector('#wsAsk'), s = getComputedStyle(t);
        return [s.outlineStyle, s.borderTopWidth, getComputedStyle(t.closest('.ask')).boxShadow]; }""")
    assert st[0] == "none" and st[1] == "0px" and st[2] != "none", st
    _no_overlap(page, "studio home")
    # v0.651 her screenshot: pressing Plan dropped the send button to a new line - the row must not move
    pos = lambda: page.evaluate("JSON.stringify([document.querySelector('#ws .go').getBoundingClientRect().top, document.querySelector('#ws .ask').getBoundingClientRect().height])")
    for width in (1240, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        before = pos()
        page.click("#ws [data-mode='plan']")
        assert pos() == before, (width, before, pos())
        page.click("#ws [data-mode='build']")
        assert pos() == before, width
    if shots:
        page.screenshot(path=f"{shots}/studio-home.png", full_page=True)
    # Build mode: one line -> the site's workspace -> three complete looks
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    # v0.655 while the looks are made: the real steps with live timers in the work panel and the chat
    try:
        page.wait_for_selector("#wsAct .acts li", timeout=30000)
        assert page.locator("#wsState .chatact .tm").count() == 1
        if shots:
            page.screenshot(path=f"{shots}/studio-working.png")
    except Exception:
        pass                                   # the fake AI can finish before the screen draws the working state
    page.wait_for_selector("#ws .lks button", timeout=120000)
    page.wait_for_selector("#wsState details.actd", timeout=15000)
    assert re.match(r"Worked for \d+(m \d+)?s · \d+ steps", page.inner_text("#wsState details.actd summary"))
    page.click("#wsState details.actd summary")
    # v0.777 CHAT JAISA: a FINISHED step reads past tense (Lovable's Reading -> Read), so the done list says "Planned"
    assert page.locator("#wsState .acts li").count() >= 4 and "Planned three designs" in page.inner_text("#wsState .acts")
    assert page.locator("#ws .lks button").count() == 3 and "every page works" in page.inner_text("#ws .ptop + .ptop")
    assert page.locator("#ws #wsPane .frame iframe").count() == 1
    frame = page.frame_locator("#ws #wsPane .frame iframe")
    frame.locator("body").wait_for(timeout=15000)
    for dev, w in (("tablet", 820), ("phone", 390), ("pc", 1280)):
        page.click(f"#ws [data-dev='{dev}']")
        page.wait_for_selector(f"#ws .frame.{dev} iframe")
        assert page.evaluate("parseInt(document.querySelector('#ws .frame iframe').style.width)") == w
        if shots:
            page.screenshot(path=f"{shots}/studio-looks-{dev}.png")
    page.click("#ws [data-look='1']")
    page.wait_for_selector("#ws [data-look='1'][aria-pressed=true]")
    src = page.get_attribute("#ws .frame iframe", "src")
    assert src.endswith("__looks/1/full/")
    _no_overlap(page, "looks")
    assert page.input_value("#wsTh") == ""
    # her screenshot (7 Nov): a sent line must land in the chat at once
    page.fill("#wsTh", "Shop mein Royal Canin 3kg add karo")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .me", timeout=5000)
    assert "Royal Canin" in page.inner_text("#wsMsgs") and page.input_value("#wsTh") == ""
    # plan mode: the plan is a document from her words; nothing is built before "Build this plan"
    page.goto(base + "/console/web#/")
    page.wait_for_selector("#wsAsk")
    page.click("#ws [data-mode='plan']")
    page.fill("#wsAsk", "hamare school ka portal - admission, fees, chhutti ki arzi, notices")
    page.keyboard.press("Enter")
    page.wait_for_selector("#ws .doc", timeout=30000)
    page.wait_for_function("() => (document.querySelector('#ws .doc') || {}).innerText?.includes('Gyan Vidya Mandir')",
                           timeout=30000)                  # v0.707 the skeleton doc shows first, the real plan after
    doc = page.inner_text("#ws .doc")
    assert "Gyan Vidya Mandir" in doc and "Admissions" in doc and "hamare school ka portal" in doc
    assert page.locator("#ws [data-act='approve-plan']").count() == 1
    _no_overlap(page, "plan")
    if shots:
        page.screenshot(path=f"{shots}/studio-plan.png", full_page=True)
    # her screenshot (7 Nov): a plan change takes a minute - her line and a working row show at once, not nothing
    import time as _t
    def slow(route):
        _t.sleep(2.5)
        route.continue_()
    page.route("**/revise", slow)
    page.fill("#wsRev", "aur ek Adopt a Pet page jahan rescue dogs ki photos hon")
    page.click("#ws form[data-form='revise'] .send")
    page.wait_for_selector("#wsPlanMsgs [data-work]", timeout=1500)
    assert "Adopt a Pet" in page.inner_text("#wsPlanMsgs") and page.input_value("#wsRev") == ""
    page.wait_for_selector("#wsPlanMsgs [data-work]", state="detached", timeout=60000)
    assert "Adopt a Pet" in page.inner_text("#wsPlanMsgs")
    page.unroute("**/revise")
    page.click("#ws [data-act='approve-plan']")
    page.wait_for_selector("#ws .lks button, #ws .box", timeout=120000)
    assert "/console/web#/site/" in page.url
    ctx.close()
    # phone width: no sideways scroll on the home
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/console/web")
    page.wait_for_selector("#wsAsk")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    if shots:
        page.screenshot(path=f"{shots}/studio-phone.png", full_page=True)
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
