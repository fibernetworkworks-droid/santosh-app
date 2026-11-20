"""v0.999.38 SOCIAL DESK - the Social Media Manager's own section (the SEO desk's twin): its chat (kind 'social', out of
her Hoola chats) beside the desk's screens; a turn in that chat (or a call started from it) knows the desk and has the
social desk tool in view; the tool reads and edits drafts only - posting, sending, approving and ads stay her taps; the
phone calls the Social Media Manager on that chat."""
import asyncio
import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0353_social_manager import _hire_and_setup, _state_from, social  # noqa: F401  (the fixture: a fake Meta)

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
T = "default"


def _connected(D):
    _hire_and_setup(D)
    D.finish_link("instagram", "IGCODE#_", _state_from(D.connect_url(T, "instagram")), background=False)


def test_social_chat_is_its_own_and_knows_the_desk(social):  # noqa: F811
    from app.main import app
    from app import socialchat
    D = social
    with TestClient(app) as c:
        r = c.get("/api/social/chat").json()                 # not hired yet: a chat still opens and says so
        assert r["id"]
        _connected(D)
        socialchat.forget(T)
        home = c.post("/api/conversations").json()["id"]
        sid = c.post("/api/social/chat/new").json()["id"]    # the untouched first chat is reused
        assert sid == r["id"]
        ids = [x["id"] for x in c.get("/api/conversations").json()["conversations"]]
        assert home in ids and sid not in ids                # never in her Hoola chat list
        assert socialchat.is_social(sid) and not socialchat.is_social(home)
        assert c.get(f"/api/social/chat/{sid}/ok").json()["ok"] and c.get(f"/api/social/chat/{home}/ok").status_code == 404
        from app import convs
        convs.mark(T, sid, "message")
        assert convs.current(T) != sid                       # never 'the chat she is in'
    b = socialchat.block(T)
    assert "<social_desk>" in b and "Sharma Dental" in b and "@sharmadental" in b
    assert "can NOT post" in b and "never invent a figure" in b and "Calendar: draft" in b
    assert "Today I need you to" in socialchat.greeting(T) and "approve your calendar" in socialchat.greeting(T)


def test_a_call_from_the_social_chat_is_a_social_turn(social):  # noqa: F811
    from app import callconv, socialchat
    from app.db import Conversation, session
    _connected(social)
    sid = socialchat.current(T)["id"]
    with session() as s:
        c = Conversation(tenant_id=T, kind="call", origin_conv=sid)
        s.add(c)
        s.flush()
        call = c.id
    assert callconv.origin_of(call) == sid and socialchat.is_social(call)


def test_the_tool_edits_drafts_and_never_puts_anything_live(social):  # noqa: F811
    from app.agent.socialdesk_tools import social_desk
    from app.agent.tools import Ctx, ToolError
    D = social
    run = lambda **a: asyncio.run(social_desk(Ctx(T, "c1"), **a))   # noqa: E731
    with pytest.raises(ToolError):
        run(action="read")                                   # not hired: refused
    _connected(D)
    s = run(action="read")
    assert s["hired"] and s["posts"]["drafts"] >= 8 and s["accounts"][0]["handle"] == "@sharmadental"
    cal = run(action="read", what="calendar")["posts"]
    pid = cal[0]["id"]
    D.set_post(T, pid, status="approved")
    r = run(action="edit_post", post_id=pid, caption="New words for the post")
    assert r["status"] == "draft" and "after her OK" in r["note"]   # an edit after her OK needs her OK again
    assert [p for p in D.calendar(T) if p["id"] == pid][0]["caption"] == "New words for the post"
    with pytest.raises(ToolError):
        run(action="edit_post", post_id=pid, status="approved")     # it can never approve a post
    with pytest.raises(ToolError):
        run(action="publish", post_id=pid)                          # nor post, send or start an ad
    with pytest.raises(ToolError):
        asyncio.run(social_desk(Ctx(T, "c1", actor="customer:x"), action="edit_post", post_id=pid, caption="x"))
    from app.agent.tools import TOOLS
    spec = [t for t in TOOLS if t["name"] == "social_desk"][0]
    assert set(spec["input_schema"]["properties"]["action"]["enum"]) == {"read", "edit_post", "draft_reply", "ignore", "run"}
    assert spec["input_schema"]["properties"]["status"]["enum"] == ["draft", "skipped"]


def test_turn_hooks_and_admission():
    src = (ROOT / "server/app/agent/santosh.py").read_text()
    assert "_socc.is_social(conversation_id)" in src and "_socc.block" in src and "adm.admit_families(_socc.FAMILIES)" in src
    from app import socialchat
    from app.agent import admit
    assert set(socialchat.FAMILIES) <= set(admit.FAMILY_OF.values())
    assert admit.FAMILY_OF["social_desk"] == "socialdesk"
    assert '"social", "video")' in (ROOT / "server/app/callconv.py").read_text() and '"social", "video")' in (ROOT / "server/app/convs.py").read_text()


def test_page_and_wiring():
    from app.main import app, APP_VERSION
    c = TestClient(app)
    r = c.get("/console/social")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "socialdesk.js" in r.text
    html = (CON / "socialdesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "md.js", "mark.js", "stream.js", "seodesk.css", "socialdesk.css", "socialdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    js = (CON / "socialdesk.js").read_text()
    for need in ("/api/social/chat", "/api/social/desk", "/api/social/inbox", "/api/social/calendar/approve", "/api/social/onboard",
                 "/api/ads/metaads", "/api/social/ytads", "/api/employees/social/settings", "HoolaChat.mount", "quality: true",
                 "hoola.social.side", "confirm(", "made PAUSED"):
        assert need in js, need
    for tab in ("today", "calendar", "inbox", "growth", "ads", "reports"):
        assert f"['{tab}'," in js
    emp = (CON / "employees.js").read_text()
    assert "location.assign('/console/social')" in emp and "HOOLA_FULL_DESK" in emp
    assert "window.HOOLA_FULL_DESK = true" in (CON / "v2.js").read_text()


def test_phone_calls_the_social_media_manager():
    es = (ROOT / "lib/ui/employees_screen.dart").read_text()
    assert "_callSocial" in es and "'/console/social'" in es and "app.api!.socialChat()" in es
    assert "socialChat()" in (ROOT / "lib/api.dart").read_text()


# ---------------------------------------------------------------- the page in a real browser
@pytest.fixture
def social_server(social, monkeypatch):  # noqa: F811
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.social import meta as M
    from tests.test_v0353_social_manager import handler
    import httpx
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    _connected(social)
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
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_social_desk_in_a_real_browser(social_server):
    base, browser, key = social_server
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/social")
        pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=20000)
        try:
            pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('Ask me anything')", timeout=20000)
        except Exception:
            raise AssertionError(f"chat empty: errors={errors} thread={pg.inner_text('#sdThread')[:300]!r} page={pg.inner_text('body')[:600]!r}")
        assert "Sharma Dental" in pg.inner_text(".sd-top")
        assert "Needs you" in pg.inner_text("#sdPage") and "Approve your calendar" in pg.inner_text("#sdPage")
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, words in (("calendar", "Calendar"), ("inbox", "Inbox"), ("growth", "Growth"), ("ads", "Ads"),
                           ("reports", "Reports & settings"), ("today", "Needs you")):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            pg.wait_for_function(f"() => document.querySelector('#sdPage h1')?.innerText.includes({words!r}) || document.querySelector('#sdPage').innerText.includes({words!r})", timeout=10000)
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1     # the chat stayed while the page loaded
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        if width == 1440 and scheme == "light":
            pg.click("#sdTabs [data-tab='calendar']")
            pg.wait_for_selector("#sdPage .so-post")
            n0 = pg.locator("#sdPage .so-post [data-ok]").count()
            pg.locator("#sdPage .so-post [data-ok]").first.click()           # her OK on one post
            pg.wait_for_function(f"() => document.querySelectorAll('#sdPage .so-post [data-ok]').length < {n0}", timeout=10000)
            pg.locator("#sdPage [data-ask]").first.click()                   # Ask on a post puts it in the chat as the subject
            pg.wait_for_selector("#sdCtx:not([hidden]) .pill")
            assert "About:" in pg.inner_text("#sdCtx")
            pg.click("#sdCtx button")
            pg.click("#sdTabs [data-tab='inbox']")
            pg.wait_for_selector("#sdPage [data-box='leads']")
            pg.click("#sdPage [data-box='leads']")
            pg.wait_for_selector("#sdPage [data-box='leads'][aria-pressed='true']")
            pg.click("#sdSwap")
            assert pg.evaluate("document.querySelector('#sdBody').classList.contains('right')")
            pg.click("#sdSwap")
            pg.click("#sdFold")
            assert pg.evaluate("document.querySelector('#sdChat').classList.contains('folded')")
            pg.click("#sdFold")
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
            for tab in ("calendar", "inbox", "growth", "ads", "reports", "today"):
                pg.click(f"#sdTabs [data-tab='{tab}']")
                time.sleep(0.6)
                pg.screenshot(path=f"{shots}/socialdesk_{tab}_{scheme}_{width}.png", full_page=False)
        ctx.close()
    assert not errors, errors
