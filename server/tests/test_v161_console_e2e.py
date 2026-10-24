"""v0.161 the console in a real browser (Playwright + Chromium) against a local server with a slow fake brain:
first word under 2 s, never a raw markdown sign while a 40-line answer with a table, code and a list streams in, Stop
works, and a reload mid-reply continues without a duplicate. Skipped where no browser is installed (CI / sandbox).
Screenshots: set CONSOLE_SHOTS=<folder>."""
import asyncio
import os
import socket
import threading
import time
from pathlib import Path

import pytest

from tests.test_v161_stream import KEY, StreamingClaude, _text

ANSWER = """## GST ka October hisaab

Aapke **October** ke bills dekh liye. Yeh raha *short* hisaab, aur neeche poori list hai.

1. Bijli ka bill: theek hai
2. Kiraya: chadh gaya
   - landlord ko yaad dilana hai
   - receipt maangni hai
3. Internet: kam hua

| Kharcha | Rakam | Badlav |
|---|---:|---|
| Bijli | ₹1,240 | +4% |
| Kiraya | ₹18,000 | +10% |
| Internet | ₹799 | -20% |
| Paani | ₹310 | 0% |
| Gas | ₹1,105 | +2% |

> Dhyaan rahe: kiraya agle mahine se badhega.

```python
total = 1240 + 18000 + 799 + 310 + 1105
print(total)
```

Aur kuch baatein:

- Bills ki photo Drive mein hain
- Agle hafte GST return file karna hai
- Main reminder laga doon?

Agar haan bolein to main reminder laga deta hoon. SENTINEL-END
"""


def _pieces(text, n=4):
    return [text[i:i + n] for i in range(0, len(text), n)]


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def server(env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    monkeypatch.setenv("CONSOLE_STREAM", "true")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):              # the app's startup (tables, workers) can take a while on a cold machine
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


WATCH = """() => {
  window.__bad = [];
  const check = () => document.querySelectorAll('.mh .textmd').forEach(el => {
    const c = el.cloneNode(true); c.querySelectorAll('pre, code').forEach(x => x.remove());
    const t = c.textContent || '';
    if (/\\*\\*|`|(^|\\n)\\s*\\|/.test(t) || /\\]\\(/.test(t)) window.__bad.push(t.slice(-120));
  });
  new MutationObserver(check).observe(document.body, {subtree: true, childList: true, characterData: true});
}"""


def _shot(page, name):
    d = os.environ.get("CONSOLE_SHOTS")
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(d) / f"{name}.png"), full_page=False)


def _send(page, text):
    page.fill("#msg", text)
    page.press("#msg", "Enter")
    return time.monotonic()


def test_console_streams_stops_and_resumes(server):
    base, browser = server
    from app.agent import set_client
    slow = StreamingClaude([[_text(["Namaste! ", "Bataiye kya karna hai?"])],
                            [_text(_pieces(ANSWER))], [_text([f"shabd{i} " for i in range(400)])],
                            [_text(_pieces(ANSWER))]], delay=0.03)
    set_client(slow)
    for size, name in (((1366, 860), "desktop"), ((390, 844), "phone")):
        ctx = browser.new_context(viewport={"width": size[0], "height": size[1]})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
        page = ctx.new_page()
        page.goto(base + "/console/")
        page.wait_for_selector("#app:not([hidden])")
        if name == "phone":   # the layout check only; the streaming checks run once on desktop
            _shot(page, "phone-landing")
            ctx.close()
            continue
        page.evaluate(WATCH)
        _send(page, "namaste")          # warm-up: the first turn after a server start pays one-time imports
        page.wait_for_selector(".racts", timeout=30000)

        # 1. first word under 2 s, no raw markdown at any point, the finished answer rendered properly
        t0 = _send(page, "October ka hisaab do")
        page.wait_for_function("() => [...document.querySelectorAll('.mh .textmd')].some(e => e.textContent.trim().length)",
                               timeout=5000)
        assert time.monotonic() - t0 < 2.0
        _shot(page, "desktop-streaming")
        page.wait_for_function("() => document.querySelectorAll('.racts').length >= 2", timeout=90000)
        assert page.evaluate("window.__bad") == []
        assert page.locator(".mh .mdt tbody tr").count() == 5
        assert page.locator(".mh .cb code").count() == 1 and page.locator(".mh ol > li").count() == 3
        assert page.locator(".ra[data-act='retry']").count() == 1
        _shot(page, "desktop-done")

        # 2. Stop works: the reply ends at once, marked stopped
        _send(page, "lambi kahani sunao")
        page.wait_for_function("() => document.querySelectorAll('.mh .textmd').length >= 3 && "
                               "[...document.querySelectorAll('.mh .textmd')].pop().textContent.length > 40", timeout=10000)
        page.click("#stopBtn")
        page.wait_for_selector("text=Theek hai, maine kaam rok diya", timeout=3000)
        page.wait_for_selector(".rstop", timeout=3000)
        _shot(page, "desktop-stopped")

        # 3. reload mid-reply: the words so far come back and the reply finishes once, without a duplicate
        _send(page, "phir se October ka hisaab")
        page.wait_for_function("() => [...document.querySelectorAll('.mh .textmd')].pop().textContent.length > 120",
                               timeout=10000)
        page.reload()
        page.wait_for_selector("#app:not([hidden])")
        page.wait_for_function("() => [...document.querySelectorAll('.mh .textmd')].some(e => e.textContent.includes('GST ka October'))",
                               timeout=10000)
        page.wait_for_function("() => document.body.innerText.split('SENTINEL-END').length - 1 >= 2", timeout=90000)
        time.sleep(1.0)
        assert page.evaluate("document.body.innerText.split('SENTINEL-END').length - 1") == 2   # answer 1 + answer 3
        assert page.evaluate("document.body.innerText.split('GST ka October hisaab').length - 1") == 2
        _shot(page, "desktop-after-reload")
        ctx.close()
