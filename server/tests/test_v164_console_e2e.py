"""v0.164 walkthrough in a real browser (Playwright + Chromium; skipped without one): folders (create, instructions saved,
file added, a chat in the folder gets them, a chat moved in from its menu), drag-and-drop and a pasted screenshot in the
composer, shortcuts (Ctrl+Shift+O, /, Esc stops), the light theme, and phone widths 360 / 390 / 430 with no sideways
scroll. Screenshots: set CONSOLE_SHOTS=<folder>."""
import threading
import time

import pytest

from tests.test_v161_console_e2e import _free_port, _shot
from tests.test_v161_stream import KEY, StreamingClaude, _text


@pytest.fixture
def p4_server(env, monkeypatch, tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    for k, v in (("CONSOLE_STREAM", "true"), ("CHAT_SESSIONS", "true"), ("SIDE_PANEL", "true"), ("CHAT_PROJECTS", "true"),
                 ("API_KEY", KEY), ("PROJECTS_DIR", str(tmp_path / "projects"))):
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import pakka

    async def title(system, text, settings):
        return "Folder wali chat"
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


def _ctx(browser, w, h, scheme="dark"):
    c = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
    return c


DROP = """([sel, name, type, text]) => {
  const dt = new DataTransfer(); dt.items.add(new File([text], name, {type}));
  const el = document.querySelector(sel);
  for (const k of ['dragenter', 'dragover', 'drop']) el.dispatchEvent(new DragEvent(k, {bubbles: true, cancelable: true, dataTransfer: dt}));
}"""
PASTE = """() => {
  const png = Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='), c => c.charCodeAt(0));
  const dt = new DataTransfer(); dt.items.add(new File([png], 'image.png', {type: 'image/png'}));
  const ev = new ClipboardEvent('paste', {bubbles: true, cancelable: true, clipboardData: dt});
  document.getElementById('msg').dispatchEvent(ev);
}"""


def test_phase4_walkthrough(p4_server):
    base, browser = p4_server
    from app.agent import set_client
    set_client(StreamingClaude([[_text(["Namaste! ", "Bataiye."])], [_text([f"shabd{i} " for i in range(300)])],
                                [_text(["Folder ", "ka jawab."])]], delay=0.03))
    ctx = _ctx(browser, 1440, 900)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept("Shaadi ka kaam" if "naam" in d.message else "1" if "number" in d.message.lower() else ""))
    page.goto(base + "/console/")
    page.wait_for_selector("#app:not([hidden])")
    page.wait_for_selector("#projects .pjadd")

    # shortcuts: "/" focuses the composer; Ctrl+Shift+O makes a new chat
    page.locator("body").click(position={"x": 700, "y": 40})
    page.keyboard.press("/")
    assert page.evaluate("document.activeElement.id") == "msg"
    first = page.url
    page.locator("body").click(position={"x": 700, "y": 40})
    page.keyboard.press("Control+Shift+O")
    page.wait_for_function("u => location.href !== u", arg=first, timeout=8000)

    # Esc stops Hoola
    page.fill("#msg", "namaste")
    page.press("#msg", "Enter")
    page.wait_for_selector(".racts", timeout=30000)
    page.fill("#msg", "lambi kahani")
    page.press("#msg", "Enter")
    page.wait_for_selector("#stopBtn:not([hidden])", timeout=10000)
    page.wait_for_function("() => [...document.querySelectorAll('.mh .textmd')].pop().textContent.includes('shabd5')", timeout=10000)
    page.keyboard.press("Escape")
    page.wait_for_selector("text=Theek hai, maine kaam rok diya", timeout=5000)
    chat_to_move = page.url.rsplit("/", 1)[1]

    # drop a file onto the chat, paste a screenshot into the composer
    page.evaluate(DROP, ["#v-chat", "notes.txt", "text/plain", "kal ki list"])
    page.wait_for_selector("#files .fchip:not(.up) >> text=notes.txt", timeout=10000)
    page.evaluate(PASTE)
    page.wait_for_selector("#files .fchip:not(.up) >> text=screenshot-", timeout=10000)
    _shot(page, "p4-drop-paste")
    page.click("#files [data-rm='1']")
    page.click("#files [data-rm='0']")

    # a folder: create, instructions, a file, a chat inside it
    page.click("#projects .pjadd")
    page.wait_for_selector("#project .pjname >> text=Shaadi ka kaam", timeout=8000)
    page.fill("#project .pjta[data-f='instructions']", "Budget 5 lakh. Hamesha Hindi mein.")
    page.wait_for_selector("#project .pjta.saved", timeout=5000)
    page.set_input_files("#project .pjdrop input", files=[{"name": "venue.txt", "mimeType": "text/plain", "buffer": b"Venue Pune 12 Dec"}])
    page.wait_for_selector("#project .pjf >> text=venue.txt", timeout=10000)
    _shot(page, "p4-folder")
    page.click("#project [data-a='chat']")
    page.wait_for_function("() => /\\/console\\/c\\/conv_/.test(location.pathname)")
    page.wait_for_selector("#ttl >> text=Shaadi ka kaam", timeout=8000)
    in_folder = page.url.rsplit("/", 1)[1]
    from app import projects
    block = projects.prompt_block(in_folder)
    assert "Budget 5 lakh" in block and "Venue Pune 12 Dec" in block
    page.fill("#msg", "caterer?")
    page.press("#msg", "Enter")
    page.wait_for_selector("text=Folder ka jawab.", timeout=20000)

    # move the stopped chat into the folder from its menu
    row = page.locator(f"#recents [data-row='{chat_to_move}']")
    row.hover()
    row.locator(".rcm").click()
    page.click(".rmenu >> text=Folder mein daalo")
    page.wait_for_function("() => document.querySelector('#projects .pjrow small')?.textContent === '2'", timeout=8000)
    assert projects.of_chat(chat_to_move)
    _shot(page, "p4-desktop-dark")
    ctx.close()

    # light theme follows the system setting
    light = _ctx(browser, 1440, 900, "light")
    lp = light.new_page()
    lp.goto(f"{base}/console/c/{in_folder}")
    lp.wait_for_selector("text=Folder ka jawab.", timeout=15000)
    bg = lp.evaluate("getComputedStyle(document.body).backgroundColor")
    ink = lp.evaluate("getComputedStyle(document.body).color")
    assert bg == "rgb(247, 245, 255)" and ink == "rgb(27, 21, 48)"
    _shot(lp, "p4-desktop-light")
    light.close()

    # phone widths: no sideways scroll on the chat, the drawer, a folder and Banaya hua
    for w in (360, 390, 430):
        ph = _ctx(browser, w, 820)
        p = ph.new_page()
        p.goto(f"{base}/console/c/{in_folder}")
        p.wait_for_selector("text=Folder ka jawab.", timeout=15000)
        assert p.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"sideways scroll at {w}px"
        _shot(p, f"p4-phone-{w}")
        p.click("#menu")
        p.wait_for_timeout(500)
        p.locator("#projects .pjrow").first.click()
        p.wait_for_selector("#project .pjname", timeout=8000)
        assert p.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"folder sideways at {w}px"
        assert p.evaluate("Math.max(...[...document.querySelectorAll('#v-project *')].map(e => e.getBoundingClientRect().right)) <= innerWidth + 1")
        if w == 390:
            _shot(p, "p4-phone-folder")
        ph.close()
