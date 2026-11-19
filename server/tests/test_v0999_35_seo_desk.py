"""v0.999.34 SEO DESK - the SEO Specialist's own section: its chat (kind 'seo', out of her Hoola chats) beside the desk's
screens; a turn in that chat (or a call started from it) knows the desk and has the SEO + website tools in view; it may
change a website only when Hoola built it, after her yes; the phone calls the SEO Specialist on that chat."""
import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0317_seo_employee import seo  # noqa: F401  (the fixture: mock website + Google)

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
T = "default"


def _onboard():
    from app.employee import hire
    from app.seo import desk
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", name="Sharma Dental", city="Akola", background=False)


def test_seo_chat_is_its_own_and_knows_the_desk(seo):  # noqa: F811
    from app.main import app
    from app import seochat
    with TestClient(app) as c:
        r = c.get("/api/seo/chat").json()                   # not hired yet: a chat still opens and says so
        assert r["id"] and r["can_change"] is False
        _onboard()
        seochat.forget(T)
        home = c.post("/api/conversations").json()["id"]
        sid = c.get("/api/seo/chat").json()["id"]
        assert sid == r["id"]                               # the same SEO chat comes back
        ids = [x["id"] for x in c.get("/api/conversations").json()["conversations"]]
        assert home in ids and sid not in ids              # never in her Hoola chat list
        assert seochat.is_seo(sid) and not seochat.is_seo(home)
        msgs = c.get(f"/api/conversations/{sid}/messages").json()["messages"]
        assert msgs and "SEO Specialist" in msgs[0]["text"]
        new = c.post("/api/seo/chat/new").json()           # an untouched chat is reused, never a pile of empty ones
        assert new["id"] == sid
        from app import convs
        convs.mark(T, sid, "message")
        assert convs.current(T) != sid                     # never 'the chat she is in'
    b = seochat.block(T)
    assert "<seo_desk>" in b and "shop.example" in b and "NOT built by Hoola" in b and "Shall I make this change?" in b
    assert "never invent a figure" in b


def test_a_call_from_the_seo_chat_is_an_seo_turn(seo):  # noqa: F811
    from app import callconv, seochat
    from app.db import Conversation, session
    _onboard()
    sid = seochat.current(T)["id"]
    with session() as s:
        c = Conversation(tenant_id=T, kind="call", origin_conv=sid)
        s.add(c)
        s.flush()
        call = c.id
    assert callconv.origin_of(call) == sid and seochat.is_seo(call)


def test_changes_only_on_a_site_hoola_built(seo, monkeypatch):  # noqa: F811
    from app import seochat
    from app.site import hosting
    _onboard()
    monkeypatch.setattr(hosting, "host_map", lambda force=False: {"www.shop.example": {"site": "site_9", "tenant": T, "role": "main"},
                                                                   "other.example": {"site": "site_8", "tenant": "someone", "role": "main"}})
    seochat.forget(T)
    assert seochat.hoola_site(T, "https://shop.example/") == {"site": "site_9", "host": "www.shop.example"}
    assert seochat.hoola_site(T, "other.example") is None                  # another account's site is never hers
    b = seochat.block(T)
    assert "BUILT AND HOSTED BY HOOLA" in b and "site_9" in b and "ONLY after she said yes" in b


def test_turn_hooks_and_admission():
    src = (ROOT / "server/app/agent/santosh.py").read_text()
    assert "_seoc.is_seo(conversation_id)" in src and "_seoc.block" in src and "adm.admit_families(_seoc.FAMILIES)" in src
    from app import seochat
    from app.agent import admit
    assert set(seochat.FAMILIES) <= set(admit.FAMILY_OF.values())   # both families really exist
    assert '"seo", "social")' in (ROOT / "server/app/callconv.py").read_text()


def test_page_and_wiring():
    from app.main import app
    from app.main import APP_VERSION
    c = TestClient(app)
    r = c.get("/console/seo")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "seodesk.js" in r.text
    html = (CON / "seodesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "md.js", "mark.js", "stream.js", "seodesk.css"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html
    js = (CON / "seodesk.js").read_text()
    for need in ("/api/seo/chat", "/api/seo/desk", "/api/seo/intel", "/api/seo/onboard", "/api/seo/roadmap/approve",
                 "/api/employees/seo/settings", "HoolaChat.mount", "quality: true", "hoola.seo.side"):
        assert need in js, need
    for tab in ("overview", "plan", "health", "search", "local", "reports"):
        assert f"['{tab}'," in js
    emp = (CON / "employees.js").read_text()
    assert "location.assign('/console/seo')" in emp


def test_phone_calls_the_seo_specialist():
    cs = (ROOT / "lib/call_session.dart").read_text()
    assert "String? convFor;" in cs and "_callConv = convFor ?? app.conversationId;" in cs and "conv: _callConv!" in cs
    assert cs.count("convFor = null;") >= 2                 # cleared when a call ends or fails to start
    es = (ROOT / "lib/ui/employees_screen.dart").read_text()
    assert "_callSeo" in es and "app.voiceCall.convFor = _s(r['id']);" in es and "'/console/seo'" in es
    assert "seoChat()" in (ROOT / "lib/api.dart").read_text()


# ---------------------------------------------------------------- the page in a real browser
@pytest.fixture
def seo_server(seo, monkeypatch):  # noqa: F811
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _onboard()                                   # hired before credits are on (with credits on, hiring needs its package)
    from tests._hq_wiring import real_tiers
    tenant = real_tiers(monkeypatch)
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, tenant
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_seo_desk_in_a_real_browser(seo_server):
    from tests._hq_wiring import quality_under
    base, browser, key, tenant = seo_server
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/seo")
        pg.wait_for_selector("#sdTabs [data-tab='overview']", timeout=20000)
        try:
            pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('Ask me anything')", timeout=20000)
        except Exception:
            raise AssertionError(f"chat empty: errors={errors} thread={pg.inner_text('#sdThread')[:300]!r} page={pg.inner_text('body')[:600]!r}")
        assert "Sharma Dental" in pg.inner_text(".sd-top") or "shop.example" in pg.inner_text(".sd-top")
        assert "Needs you" in pg.inner_text("#sdPage") and "From Google" in pg.inner_text("#sdPage")
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, words in (("plan", "90-day plan"), ("health", "Site health"), ("search", "Search"), ("local", "Local & Maps"),
                           ("reports", "Reports & settings"), ("overview", "Needs you")):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            pg.wait_for_function(f"() => document.querySelector('#sdPage h1')?.innerText.includes({words!r}) || document.querySelector('#sdPage').innerText.includes({words!r})", timeout=10000)
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1     # the chat stayed while the page loaded
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        if width == 1440 and scheme == "light":
            quality_under(pg, "#sdBar")                      # her tier + credits under the chat's own box
            pg.locator("#sdPage [data-ask]").first.click()   # Ask on a number puts it in the chat as the subject
            pg.wait_for_selector("#sdCtx:not([hidden]) .pill")
            assert "About:" in pg.inner_text("#sdCtx")
            pg.click("#sdCtx button")
            assert pg.is_hidden("#sdCtx")
            pg.click("#sdTabs [data-tab='plan']")
            pg.wait_for_selector("#sdPage .task")
            pg.locator("#sdPage .task").first.click()
            pg.wait_for_selector("#sdPage .detail")
            pg.locator("#sdPage .detail [data-st='doing']").click()
            pg.wait_for_function("() => [...document.querySelectorAll('.col')].find(c => c.querySelector('h4').innerText.startsWith('Doing'))?.querySelectorAll('.task').length >= 1", timeout=10000)
            pg.click("#sdTabs [data-tab='health']")
            pg.wait_for_selector("#sdPage .prob, #sdPage .empty")
            pg.click("#sdSwap")
            assert pg.evaluate("document.querySelector('#sdBody').classList.contains('right')")
            pg.click("#sdSwap")
            pg.click("#sdFold")
            assert pg.evaluate("document.querySelector('#sdChat').classList.contains('folded')")
            pg.click("#sdFold")
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
            for tab in ("plan", "health", "search", "local", "reports", "overview"):
                pg.click(f"#sdTabs [data-tab='{tab}']")
                time.sleep(0.6)
                pg.screenshot(path=f"{shots}/seodesk_{tab}_{scheme}_{width}.png", full_page=False)
        ctx.close()
    assert not errors, errors
