"""v0.999.46 CA PRACTICE on the console - the CA document desk's pages inside the GST & Accounts section (/console/accounts
#/ca/...): Clients (+ a client's folder), Document inbox, Requests, Channels & storage, on /api/practice/*. Static checks
of the page + a walk in a real browser: a client added, a file from an unknown sender waiting in the inbox, filed to the
client with a tap, then seen in the client's folder."""
import re
from pathlib import Path

import pytest

from tests.test_v0999_44_accounts_desk import acc, acc_server  # noqa: F401  (fixtures)
from tests.test_v0845_bahi_a6 import _valid_gstin

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def test_page_loads_the_ca_practice_script():
    from app.main import APP_VERSION
    html = (CON / "accountsdesk.html").read_text()
    assert f"/static/console/capractice.js?v={APP_VERSION}" in html
    assert html.index("capractice.js") < html.index("accountsdesk.js")
    js = (CON / "accountsdesk.js").read_text()
    for need in ("HoolaCAPractice(", "CA practice", "#/ca/", "data-group"):
        assert need in js, need


def test_four_pages_and_endpoints():
    js = (CON / "capractice.js").read_text()
    for name in ("Clients", "Document inbox", "Requests", "Channels & storage", "Open folder", "Download month as ZIP",
                 "Needs you", "Filed today", "Another client", "New client", "Not for me", "Review &amp; send",
                 "Open in WhatsApp", "No clients yet — add your first client"):
        assert name in js, name
    for ep in ("/api/practice'", "/api/practice/settings", "/api/practice/clients", "/folder`", "/zip?month=", "/api/practice/files/",
               "/api/practice/upload", "/api/practice/inbox", "/file`", "/drop`", "/api/practice/requests", "/draft?month=", "/send`",
               "/api/practice/telegram", "/api/practice/slack"):
        assert ep in js, ep
    assert "remember_sender: true" in js and "new_client: {name}" in js
    assert 'rel="noopener"' in js and 'target="_blank"' in js
    assert js.count('type="password"') >= 3                       # bot token, Slack token, signing secret never shown back
    assert "f.reset()" in js


def test_csp_clean_and_linkedin_not_connectable():
    for f in ("capractice.js", "accountsdesk.js"):
        js = (CON / f).read_text()
        assert not re.search(r"""\son[a-z]+\s*=\s*["']""", js), f   # no inline on*= handlers in the markup
        assert "eval(" not in js and "new Function" not in js
    js = (CON / "capractice.js").read_text()
    i = js.index("card('LinkedIn'")
    li = js[i:i + 300]
    assert "Not possible" in li and "data-set" not in li and "<form" not in li   # shown, never a switch or a form
    css = (CON / "accountsdesk.css").read_text()
    assert ".ca-folder" in css and ".ca-panel" in css and ".ca-ch.off" in css


def test_ca_practice_in_a_real_browser(acc_server, tmp_path):
    base, browser, key, sup = acc_server
    import httpx
    h = {"Authorization": f"Bearer {key}"}
    g = _valid_gstin("27AACCK1234B1Z")
    with httpx.Client(base_url=base, headers=h, timeout=30) as c:
        r = c.post("/api/practice/clients", json={"name": "Kiran Traders", "gstin": g, "phones": ["9876543210"]})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        up = c.post("/api/practice/upload", files={"file": ("note-from-someone.txt", b"Please keep this note for the file.", "text/plain")})
        assert up.status_code == 200, up.text
        f = up.json()["files"][0]
        assert f["status"] == "waiting"
    errors = []
    for width in (1440, 390):
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/accounts")
        pg.wait_for_selector("#adGroup [data-group='ca']", timeout=20000)
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        pg.click("#adGroup [data-group='ca']")
        pg.wait_for_function("() => document.querySelector('#adCa').innerText.includes('Kiran Traders')", timeout=15000)
        tabs = pg.inner_text("#sdTabs")
        for t in ("Clients", "Document inbox", "Requests", "Channels & storage"):
            assert t in tabs, t
        assert pg.evaluate("document.querySelector('#app').hidden")      # the accounts screens step aside
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        if width == 1440:
            pg.wait_for_function("() => document.querySelector('#sdTabs [data-tab=\"ca/inbox\"] .n')?.textContent === '1'", timeout=10000)
            pg.click("#sdTabs [data-tab='ca/inbox']")
            pg.wait_for_selector(f"[data-fid='{f['id']}']", timeout=10000)
            assert "Needs you · 1" in pg.inner_text("#adCa")
            pg.click(f"[data-fid='{f['id']}'] [data-act='other']")
            pg.select_option(f"[data-fid='{f['id']}'] [data-pick]", cid)
            pg.click(f"[data-fid='{f['id']}'] [data-act='file-other']")
            pg.wait_for_function("() => document.querySelector('#adCa').innerText.includes('Needs you · 0')", timeout=10000)
            pg.click("#sdTabs [data-tab='ca/clients']")
            pg.wait_for_selector(f"[data-folder='{cid}']", timeout=10000)
            pg.click(f"[data-folder='{cid}']")
            pg.wait_for_function("() => location.hash.startsWith('#/ca/folder/') && document.querySelector('.ca-files table')", timeout=10000)
            assert "Kiran Traders" in pg.inner_text("#adCa")
            assert pg.locator(".ca-files [data-dl]").count() == 1
            assert "Download month as ZIP" in pg.inner_text("#adCa")
            pg.click("#sdTabs [data-tab='ca/requests']")
            pg.wait_for_selector("[data-review]", timeout=10000)
            pg.click(f"[data-review='{cid}']")
            pg.wait_for_selector("#caPanel #caText", timeout=10000)
            assert "Kiran Traders" in pg.input_value("#caPanel #caText")
            pg.click("#sdTabs [data-tab='ca/channels']")
            pg.wait_for_selector(".ca-ch.off", timeout=10000)
            assert "Not possible" in pg.inner_text(".ca-ch.off")
            pg.click("[data-set='drive_on']")
            pg.wait_for_selector("[data-set='drive_on'][aria-checked='true']", timeout=10000)
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1    # the chat stayed through every page
            pg.click("#adGroup [data-group='acc']")
            pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=10000)
            assert not pg.evaluate("document.querySelector('#app').hidden")
        ctx.close()
    assert not errors, errors
