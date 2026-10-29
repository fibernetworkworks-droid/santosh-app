"""v0.162 many chats in a real browser (Playwright + Chromium; skipped without one): a chat keeps its link across a
reload, two chats work at once and both finish (busy badge, no stopped stream), Ctrl+K finds a word from a 2-week-old
chat and opens it at that message, Edit makes a version with ‹ › arrows that switch back, rename + pin from the menu.
Screenshots: set CONSOLE_SHOTS=<folder>."""
import threading
import time
from datetime import timedelta

import pytest
from sqlalchemy import select

from tests.test_v161_console_e2e import _free_port, _shot
from tests.test_v161_stream import KEY, StreamingClaude, _text


@pytest.fixture
def sess_server(env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    for k, v in (("CONSOLE_STREAM", "true"), ("CHAT_SESSIONS", "true"), ("API_KEY", KEY), ("CONSOLE_V2", "false")):
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import pakka

    async def title(system, text, settings):   # auto titles get their own answer (not the scripted chat replies)
        return "Pune ka mausam" if "Pune" in text else "Naya sawaal jawab"
    monkeypatch.setattr(pakka, "_ask", title)
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


def _old_chat():
    """A chat from two weeks ago with a word to find."""
    from app.db import Conversation, Event, Message, now, session
    from app.events import bus
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        cid = c.id
    bus.publish(cid, "message", {"role": "user", "text": "Sharma ji ka kiraya agreement kab khatam hoga?", "source": "user"})
    with session() as s:
        s.add(Message(conversation_id=cid, role="user", content="Sharma ji ka kiraya agreement kab khatam hoga?",
                      display="Sharma ji ka kiraya agreement kab khatam hoga?"))
    bus.publish(cid, "message", {"role": "assistant", "text": "Agreement 31 March ko khatam hoga.", "source": "agent"})
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=[{"type": "text", "text": "Agreement 31 March"}],
                      display="Agreement 31 March ko khatam hoga."))
    with session() as s:
        for m in s.scalars(select(Message).where(Message.conversation_id == cid)).all():
            m.created_at = m.created_at - timedelta(days=14)
        for e in s.scalars(select(Event).where(Event.conversation_id == cid)).all():
            e.created_at = e.created_at - timedelta(days=14)
        s.get(Conversation, cid).last_at = now() - timedelta(days=14)
    return cid


def _send(page, text):
    page.fill("#msg", text)
    page.press("#msg", "Enter")


def test_many_chats_in_the_browser(sess_server):
    base, browser = sess_server
    from app.agent import set_client
    old = _old_chat()
    brain = StreamingClaude([
        [_text(["Namaste! ", "Bataiye."])],                                          # warm-up
        [_text([f"lambi{i} " for i in range(160)])],                                 # chat A (slow)
        [_text(["Chat B ", "ka jawab ", "aa gaya."])],                               # chat B, while A works
        [_text(["Mumbai ", "mein ", "dhoop hai."])],                                 # after the edit
    ], delay=0.03)
    set_client(brain)
    ctx = browser.new_context(viewport={"width": 1366, "height": 860})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
    page = ctx.new_page()
    page.goto(base + "/console/")
    page.wait_for_selector("#app:not([hidden])")
    page.wait_for_selector("#searchBtn:not([hidden])")
    _send(page, "namaste")
    page.wait_for_selector(".racts", timeout=30000)
    url_a = page.url
    assert "/console/c/conv_" in url_a                                               # every chat has a link

    # two chats at once: A keeps working while she opens B and asks there
    _send(page, "Pune ka mausam? lamba jawab do")
    page.wait_for_function("() => [...document.querySelectorAll('.mh .textmd')].pop().textContent.includes('lambi3')", timeout=10000)
    page.click("#newChat")
    page.wait_for_function("u => location.href !== u", arg=url_a, timeout=5000)
    page.wait_for_selector("#recents .rcw .spin", timeout=5000)                       # A's busy badge
    _shot(page, "p2-two-chats-busy")
    _send(page, "chat B ka sawaal")
    page.wait_for_selector("text=Chat B ka jawab aa gaya.", timeout=20000)
    url_b = page.url
    page.wait_for_function("() => !document.querySelector('#recents .rcw .spin')", timeout=60000)   # A finished too
    page.goto(url_a)                                                                  # the link opens A, finished
    page.wait_for_selector("#app:not([hidden])")
    page.wait_for_function("() => document.body.innerText.includes('lambi159')", timeout=15000)
    assert page.url == url_a

    # reload keeps the chat
    page.goto(url_b)
    page.wait_for_selector("text=Chat B ka jawab aa gaya.", timeout=15000)
    page.reload()
    page.wait_for_selector("text=Chat B ka jawab aa gaya.", timeout=15000)
    assert page.url == url_b

    # search finds a word from a 2-week-old chat and opens it at that message
    page.keyboard.press("Control+k")
    page.fill(".sbox input", "agreement")
    page.wait_for_selector(".sr", timeout=10000)
    _shot(page, "p2-search")
    page.click(".sr")
    page.wait_for_function("id => location.pathname.endsWith(id)", arg=old, timeout=10000)
    page.wait_for_selector(".flash", timeout=10000)
    assert "Sharma ji ka kiraya agreement" in page.inner_text("#col")

    # edit in chat B: a second version with arrows, and back to the first one
    page.goto(url_b)
    page.wait_for_selector(".mu[data-eid]", timeout=15000)
    bubble = page.locator(".mu[data-eid]").last
    bubble.hover()
    bubble.locator(".medit").click()
    page.fill(".mu.editing textarea", "Mumbai ka mausam?")
    page.press(".mu.editing textarea", "Enter")
    page.wait_for_selector("text=Mumbai mein dhoop hai.", timeout=20000)
    page.wait_for_selector(".barrows >> text=2/2", timeout=10000)
    _shot(page, "p2-edit-version-2")
    page.click(".barrows button[aria-label='Pichhla version']")
    page.wait_for_selector(".barrows >> text=1/2", timeout=10000)
    assert "chat B ka sawaal" in page.inner_text("#col") and "Mumbai ka mausam" not in page.inner_text("#col")

    # rename + pin from the menu
    row = page.locator(f"#recents [data-row='{url_b.rsplit('/', 1)[1]}']")
    row.hover()
    row.locator(".rcm").click()
    page.click(".rmenu >> text=Pin karo")
    page.wait_for_selector("#recents .rg >> text=Pinned", timeout=5000)
    row = page.locator(f"#recents [data-row='{url_b.rsplit('/', 1)[1]}']")
    row.hover()
    row.locator(".rcm").click()
    page.click(".rmenu >> text=Naam badlo")
    page.fill(".rcren input", "Mausam wali chat")
    page.press(".rcren input", "Enter")
    page.wait_for_selector("#recents >> text=Mausam wali chat", timeout=5000)
    _shot(page, "p2-list-pinned")
    ctx.close()

    phone = browser.new_context(viewport={"width": 390, "height": 844})
    phone.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
    p2 = phone.new_page()
    p2.goto(url_b)
    p2.wait_for_selector("#app:not([hidden])")
    p2.click("#menu")
    p2.wait_for_selector("#recents .rcw", timeout=5000)
    p2.wait_for_timeout(700)                                                          # the drawer's slide-in
    box = p2.locator(".side").bounding_box()
    assert box and box["x"] >= -1                                                     # fully on screen
    _shot(p2, "p2-phone-drawer")
    phone.close()
