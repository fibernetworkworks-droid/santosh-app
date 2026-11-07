"""v0.663 STUDIO JAANCH: every Web Studio section walked end to end; what did not work is fixed.

Found by walking every section in a real browser:
- Code > Download ZIP / React + Vite saved the zip only into her Hoola files; nothing reached her computer.
- Publish > Connect your domain made the DNS records, but the Studio never showed them (they went to the chat only),
  so 'Hoola gives you the exact records to add' showed no records, no 'check' and no tap to apply.
- Publish called /moves on every open and got a 404 for any site without an old site (a red error each time).
- History marked the newest version as current even after she restored an older one on her live address.
- Health said ': 30 din mein ...' for a site with no name yet.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

JS = Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "webstudio.js"


def _built(monkeypatch, name="Sharma Sweets"):
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    from app.site import service as S
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots in this test")))
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par", "", name=name)
    return v


def test_download_moves_and_care(site_env, monkeypatch):
    from app.main import app
    v = _built(monkeypatch, name="")
    c = TestClient(app)
    assert c.get(f"/api/sites/{v['id']}/download").status_code == 400            # nothing built yet: said, not a broken zip
    assert c.post(f"/api/sites/{v['id']}/plan", json={}).status_code == 200
    assert c.post(f"/api/sites/{v['id']}/look", json={"index": 1}).status_code == 200
    for fmt, tail in (("zip", ".zip"), ("react", "-react.zip")):
        r = c.get(f"/api/sites/{v['id']}/download?format={fmt}")
        assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
        assert "attachment" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith(tail)
        names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
        assert any(n.endswith("index.html") for n in names), names[:5]
    assert c.post(f"/api/sites/{v['id']}/export", json={}).json()["file_id"]          # the chat's export still files it
    # an ordinary site has no old site: the Studio's quiet read is not an error, the plain one still is
    assert c.get(f"/api/sites/{v['id']}/moves").status_code == 404
    q = c.get(f"/api/sites/{v['id']}/moves?quiet=1")
    assert q.status_code == 200 and q.json() == {"none": True, "rows": []}
    say = c.get(f"/api/sites/{v['id']}/care?days=30").json()["say"]
    assert not say.startswith(":") and say.startswith("S-")


def test_studio_js_markers():
    js = JS.read_text()
    assert "/download?format=" in js and "a.download = fn" in js and "URL.createObjectURL(blob)" in js
    assert "function dnsCard(host)" in js and "${dnsCard(host)}" in js
    for act in ("dns-apply", "dns-check", "dns-undo"):
        assert f"act === '{act}'" in js and f'data-act="{act}"' in js
    assert "/api/sites-dns/${enc(d.plan)}/apply" in js and "{hash: d.hash}" in js        # her tap carries the plan's hash
    assert "moves?quiet=1" in js and "const onAir" in js
    assert "__wsDbg" not in js


def test_every_section_in_a_browser(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    monkeypatch.setenv("SITES_BASE_DOMAIN", "hoolasites.in")
    monkeypatch.setenv("SITES_DIRECT_IP", "139.59.10.30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    from app.site import dns as D
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots")))
    monkeypatch.setattr(D, "lookup", lambda name, type_="A": {r: [] for r in ("cf", "google", "quad9")})
    errors, bad = [], []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("response", lambda r: "/api/" in r.url and r.status >= 400 and not r.url.endswith("/undo") and bad.append((r.url, r.status)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + "/console/web")
    page.wait_for_selector("#wsAsk", timeout=20000)
    for h, words in (("#/sites", "No website yet"), ("#/starred", "Nothing starred yet"), ("#/templates", "Sweet shop")):
        page.goto(base + "/console/web" + h)
        page.wait_for_selector(f"#ws :text('{words}')", timeout=8000)
    page.goto(base + "/console/web#/")
    page.wait_for_selector("#wsAsk")
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    page.wait_for_selector("#ws .lks button", timeout=120000)
    page.click("#ws [data-act='pick-look']")
    page.wait_for_selector("#ws #wsPane .url", timeout=120000)                     # the built site's preview
    # every view opens and draws something
    for view, words in (("code", "Hero"), ("cloud", "No lists yet"), ("integrations", "Shop and cart"), ("health", "Visitors"),
                        ("settings", "Business details"), ("history", "pehla version"), ("publish", "Connect your domain")):
        page.click(f"#ws [data-view='{view}']")
        page.wait_for_selector(f"#wsPane :text('{words}')", timeout=15000)
    # Code: both downloads reach her computer
    page.click("#ws [data-view='code']")
    page.wait_for_selector("#ws [data-file]")
    for fmt, tail in (("zip", ".zip"), ("react", "-react.zip")):
        with page.expect_download(timeout=30000) as dl:
            page.click(f"#ws [data-act='export'][data-fmt='{fmt}']")
        assert dl.value.suggested_filename.endswith(tail), dl.value.suggested_filename
    # a saved code change is a second version (so History has one to restore)
    page.locator("#ws [data-file]").nth(1).click()
    page.wait_for_selector("#wsCodeT", timeout=8000)
    page.click("#ws form[data-form='code'] [type=submit]")
    for _ in range(60):
        if "v2" in page.inner_text("#wsPill"):
            break
        page.wait_for_timeout(1000)
    # Publish: check -> her tap -> live; then her domain shows its records and a check
    page.click("#ws [data-view='publish']")
    page.click("#ws [data-act='launch']")
    page.wait_for_selector("#ws [data-act='golive']", timeout=15000)
    page.click("#ws [data-act='golive']")
    page.wait_for_selector("#wsPane .kv:has-text('s-0001.hoolasites.in')", timeout=15000)
    page.fill("#wsDom", "sharmasweets.in")
    page.click("#ws form[data-form='domain'] [type=submit]")
    try:
        page.wait_for_selector("#ws [data-dns]", timeout=15000)
    except Exception:
        raise AssertionError((bad, page.evaluate("document.querySelector('#toast')?.textContent"), page.inner_text("#wsPane")[:800]))
    card = page.inner_text("#ws [data-dns]")
    assert "DNS for sharmasweets.in" in card and "139.59.10.30" in card and "_hoola.sharmasweets.in" in card
    page.click("#ws [data-act='dns-check']")
    page.wait_for_selector("#ws [data-dnsout] .kv", timeout=15000)
    assert "0 of 3 records" in page.inner_text("#ws [data-dnsout]")
    # History: an older version restored -> that one is marked Live
    page.click("#ws [data-view='history']")
    page.wait_for_selector("#ws [data-act='rollback']", timeout=15000)
    page.locator("#ws [data-act='rollback']").last.click()
    page.wait_for_selector("#wsPane .ver:has-text('pehla version') :text('Live')", timeout=15000)
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
    assert not bad, bad
