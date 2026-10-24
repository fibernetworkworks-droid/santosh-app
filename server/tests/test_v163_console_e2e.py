"""v0.163 the side panel in a real browser (Playwright + Chromium; skipped without one). Gate: a PDF, a Hoola page, a
video, a website preview and an app prototype open without leaving the chat; page versions switch; no preview can read
the login (document.cookie / localStorage / the parent). Also: the page bridge saves through the console, a page error
shows "Theek karo" which tells Hoola in chat, Share needs the Haan card, and "Banaya hua" opens items.
Screenshots: set CONSOLE_SHOTS=<folder>."""
import threading
import time

import pytest

from tests.test_v161_console_e2e import _free_port, _shot
from tests.test_v161_stream import KEY, StreamingClaude, _text

PAGE = """<!doctype html><html><head><title>EMI</title></head><body>
<h1 id="h">EMI calculator VERSION</h1><button id="save" onclick="santosh.storage.set('loan', 250000).then(()=>document.getElementById('h').dataset.saved='1')">Save</button>
<button id="boom" onclick="setTimeout(function(){ undefinedFunctionCall(); })">Boom</button>
</body></html>"""
PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
       b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF")


@pytest.fixture
def panel_server(env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    for k, v in (("CONSOLE_STREAM", "true"), ("CHAT_SESSIONS", "true"), ("SIDE_PANEL", "true"), ("API_KEY", KEY),
                 ("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")):
        monkeypatch.setenv(k, v)
    port = _free_port()
    monkeypatch.setenv("PUBLIC_BASE_URL", f"http://127.0.0.1:{port}")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import pakka

    async def title(system, text, settings):
        return "Panel wali chat"
    monkeypatch.setattr(pakka, "_ask", title)
    import uvicorn
    from app import main
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started, "local server did not start in 60 s"
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch()
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def _seed(conv):
    from app.db import Artifact, ArtifactVersion, session
    from app.events import bus
    from app.mailbox import service as ms
    with session() as s:
        a = Artifact(tenant_id="default", conversation_id=conv, title="EMI calculator", summary="Loan EMI", version=2,
                     status="ready")
        s.add(a)
        s.flush()
        aid = a.id
        for v in (1, 2):
            s.add(ArtifactVersion(artifact_id=aid, version=v, html=PAGE.replace("VERSION", f"v{v}")))
    pdf = ms.store_bytes("default", "bill.pdf", PDF, "to_phone").id
    mp4 = ms.store_bytes("default", "reel.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64, "to_phone").id
    bus.publish(conv, "artifact", {"id": aid, "title": "EMI calculator", "version": 2, "status": "ready", "summary": "Loan EMI"})
    bus.publish(conv, "pc_file", {"file_id": pdf, "name": "bill.pdf", "title": "Bijli ka bill"})
    bus.publish(conv, "pc_file", {"file_id": mp4, "name": "reel.mp4", "title": "Diwali reel"})
    bus.publish(conv, "site_board", {"id": "site_1", "title": "Chai Point website", "status": "ready",
                                     "preview": "/api/site-preview/tok-site/"})
    bus.publish(conv, "app_board", {"id": "app_1", "title": "Darzi app", "status": "ready", "preview": "/api/app-preview/tok-app/"})
    return aid


def _card_open(page, title):
    page.locator(".cd", has_text=title).locator("[data-pn]").click()


def test_side_panel_in_the_browser(panel_server):
    base, browser = panel_server
    from app.agent import set_client
    set_client(StreamingClaude([[_text(["Error ", "theek kar raha hoon."])]], delay=0.01))
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
    page = ctx.new_page()
    page.goto(base + "/console/")
    page.wait_for_selector("#app:not([hidden])")
    page.wait_for_function("() => /\\/console\\/c\\/conv_/.test(location.pathname)")
    conv = page.url.rsplit("/", 1)[1]
    aid = _seed(conv)
    page.reload()
    page.wait_for_selector(".cd >> text=EMI calculator", timeout=15000)

    # a Hoola page: opens beside the chat, versions switch, the frame can't read the login
    _card_open(page, "EMI calculator")
    page.wait_for_selector("#app.pn .panel .pnframe")
    frame = page.frame_locator(".pnitem:not([hidden]) .pnframe")
    frame.locator("#h").wait_for()
    assert "v2" in frame.locator("#h").inner_text()
    f = next(fr for fr in page.frames if f"/a/{aid}/" in fr.url)
    probe = f.evaluate("""() => { const r = {};
      try { r.cookie = document.cookie } catch (e) { r.cookie = 'blocked' }
      try { r.ls = localStorage.getItem('hoola.console.token') } catch (e) { r.ls = 'blocked' }
      try { r.parent = window.parent.localStorage.getItem('hoola.console.token') } catch (e) { r.parent = 'blocked' }
      try { r.pdoc = window.parent.document.title } catch (e) { r.pdoc = 'blocked' }
      return r }""")
    assert probe["cookie"] in ("blocked", "") and probe["ls"] in ("blocked", None)
    assert probe["parent"] == "blocked" and probe["pdoc"] == "blocked"
    assert "allow-same-origin" not in page.get_attribute(".pnitem:not([hidden]) .pnframe", "sandbox")
    _shot(page, "p3-page")
    page.select_option(".pnitem:not([hidden]) .pnsel", "1")
    page.frame_locator(".pnitem:not([hidden]) .pnframe").locator("#h:has-text('v1')").wait_for(timeout=10000)
    page.select_option(".pnitem:not([hidden]) .pnsel", "2")
    frame = page.frame_locator(".pnitem:not([hidden]) .pnframe")
    frame.locator("#h:has-text('v2')").wait_for(timeout=10000)
    # the page bridge saves through the console (for this page only)
    frame.locator("#save").click()
    frame.locator("#h[data-saved='1']").wait_for(timeout=10000)
    from app import artifacts
    assert artifacts.state_all("default", aid).get("loan") == 250000
    # code view
    page.click(".pnitem:not([hidden]) .bseg button[data-v='code']")
    page.wait_for_selector(".pnitem:not([hidden]) .pcode >> text=EMI calculator v2")
    page.click(".pnitem:not([hidden]) .bseg button[data-v='preview']")
    frame = page.frame_locator(".pnitem:not([hidden]) .pnframe")
    frame.locator("#boom").click()
    # a page error -> Theek karo -> Hoola is told in chat
    page.wait_for_selector(".pnitem:not([hidden]) .pnerr:not([hidden])", timeout=10000)
    _shot(page, "p3-page-error")
    page.click(".pnitem:not([hidden]) .pnerr .btn")
    page.wait_for_selector(".mu >> text=error aa raha hai", timeout=10000)
    page.wait_for_selector("text=Error theek kar raha hoon.", timeout=20000)

    # share needs her Haan in the chat
    page.click(".pnitem:not([hidden]) [data-a='share']")
    page.wait_for_selector(".cd >> text=Share: EMI calculator", timeout=10000)
    card = page.locator(".cd", has_text="Share: EMI calculator").last
    card.locator(".slidec").focus()
    page.keyboard.press("Enter")
    page.wait_for_selector(".cd input.fld[aria-label='Share link']", timeout=10000)
    assert "/s/" in page.input_value(".cd input.fld[aria-label='Share link']")

    # a PDF, a video, a website preview and an app prototype: each opens in its own tab, still in the chat
    _card_open(page, "Bijli ka bill")
    page.wait_for_selector(".pnitem:not([hidden]) iframe.pnframe[src^='blob:']", timeout=10000)
    _shot(page, "p3-pdf")
    _card_open(page, "Diwali reel")
    page.wait_for_selector(".pnitem:not([hidden]) video.pnmedia[src^='blob:']", timeout=10000)
    page.locator(".cd", has_text="Chai Point website").locator("button", has_text="Studio").count()   # the build card itself
    # website + app previews come from Banaya hua (their chat cards belong to the Build studio)
    page.click("#snav [data-v='bana']")
    page.wait_for_selector("#bana .libit", timeout=10000)
    assert page.locator("#bana .libit").count() >= 5
    _shot(page, "p3-library")
    page.locator("#bana .libit", has_text="Chai Point website").click()
    page.wait_for_selector(".pnitem:not([hidden]) iframe.pnframe[src='/api/site-preview/tok-site/']", timeout=10000)
    page.locator("#bana .libit", has_text="Darzi app").click()
    page.wait_for_selector(".pnitem:not([hidden]) .pnview.phone iframe.pnframe[src='/api/app-preview/tok-app/']", timeout=10000)
    for fr in page.query_selector_all(".pnframe:not([src^='blob:'])"):
        assert "allow-same-origin" not in (fr.get_attribute("sandbox") or "")
    assert page.locator(".pntab").count() == 5 and page.url.endswith(conv)               # never left the chat
    _shot(page, "p3-tabs")
    # tabs close; the last one closes the panel
    for _ in range(5):
        page.locator(".pntab .pnx").first.click()
    page.wait_for_function("() => !document.getElementById('app').classList.contains('pn')")
    ctx.close()

    phone = browser.new_context(viewport={"width": 390, "height": 844})
    phone.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
    p2 = phone.new_page()
    p2.goto(f"{base}/console/c/{conv}")
    p2.wait_for_selector(".cd >> text=EMI calculator", timeout=15000)
    p2.locator(".cd", has_text="EMI calculator").first.locator("[data-pn]").click()
    p2.wait_for_selector("#app.pn .panel .pnframe")
    p2.wait_for_timeout(600)
    _shot(p2, "p3-phone-sheet")
    phone.close()
