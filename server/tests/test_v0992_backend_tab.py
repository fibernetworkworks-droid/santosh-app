"""v0.991 B5 BACKEND TAB (owner: "GO B5" on docs/research/lovable/03_backend_vs_hoola.md, gap 6).

The Web Studio's Cloud tab runs the website's backend: entries she can add / change / delete, member roles, the change
log, backups + restore (her confirm), secrets typed once and never shown again, outside services approved by her tap,
usage + limits - on the existing /api/apps/* routes plus three new ones (overview, add an entry, change log)."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

JS = Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "webstudio.js"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.36"


def _linked(sid, key=""):
    from app.main import app
    from app.site import service as S
    c = TestClient(app, headers={"Authorization": f"Bearer {key}"} if key else None)
    S.design_app(T, sid, "customers apna order track karein")
    c.post(f"/api/sites/{sid}/link-app")
    return c


def test_overview_add_entry_and_change_log(app_site):
    sid = app_site
    c = _linked(sid)
    o = c.get(f"/api/sites/{sid}/backend").json()
    assert o["app"]["id"] and [x["key"] for x in o["lists"]] == ["orders", "notices"]
    assert o["usage"]["rows"] == 0 and isinstance(o["backups"], list) and o["connect"]["secrets"] == []
    assert o["rule_tests"] is None                                                       # never run from here
    r = c.post(f"/api/sites/{sid}/app/rows/orders", json={"item": "Kaju katli", "phone": "9876500000", "qty": 2})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    bad = c.post(f"/api/sites/{sid}/app/rows/orders", json={"item": "No phone"})       # the same field checks
    assert bad.status_code == 400
    assert c.post(f"/api/sites/{sid}/app/rows/nope", json={}).status_code in (400, 404)
    rows = c.get(f"/api/sites/{sid}/app/rows/orders").json()["rows"]
    assert [x["id"] for x in rows] == [rid]
    assert c.patch(f"/api/sites/{sid}/app/rows/orders/{rid}", json={"qty": 3}).status_code == 200
    lg = c.get(f"/api/sites/{sid}/app/log").json()["log"]
    assert lg and lg[0]["list"] == "orders" and any(x["by"] == "You (owner)" for x in lg)
    assert c.delete(f"/api/sites/{sid}/app/rows/orders/{rid}").status_code == 200
    assert c.get(f"/api/sites/{sid}/backend").json()["usage"]["rows"] == 0


def test_secrets_backups_and_limits_through_the_apps_routes(app_site):
    sid = app_site
    c = _linked(sid)
    ref = c.get(f"/api/sites/{sid}/backend").json()["app"]["id"]
    assert c.put(f"/api/apps/{ref}/connect/secrets/sheet_key", json={"value": "very-secret-value-123"}).status_code == 200
    o = c.get(f"/api/sites/{sid}/backend")
    assert o.json()["connect"]["secrets"] == ["sheet_key"] and "very-secret-value-123" not in o.text   # never shown again
    c.post(f"/api/sites/{sid}/app/rows/orders", json={"item": "A", "phone": "9876500001"})
    snap = c.post(f"/api/apps/{ref}/backups/now", json={}).json()
    assert snap["rows"] >= 1
    names = [b["name"] for b in c.get(f"/api/sites/{sid}/backend").json()["backups"]]
    assert snap["name"] in names
    c.post(f"/api/sites/{sid}/app/rows/orders", json={"item": "B", "phone": "9876500002"})
    pv = c.post(f"/api/apps/{ref}/backups/preview", json={"name": snap["name"]}).json()
    assert pv["go_away"] == 1                                                            # nothing changed by a preview
    assert c.get(f"/api/sites/{sid}/backend").json()["usage"]["rows"] == 2
    lim = c.put(f"/api/apps/{ref}/usage", json={"rows": 5000})
    assert lim.status_code == 200 and lim.json()["limits"]["rows"] == 5000
    assert c.put(f"/api/apps/{ref}/usage", json={"rows": 1}).status_code == 400          # never below what is used


def test_a_site_not_on_the_app_backend_is_said(app_site, monkeypatch):
    from app.config import get_settings
    from app.main import app
    from app.site import service as S
    monkeypatch.setattr(get_settings(), "site_app_link", False)
    S.design_app(T, app_site, "customers apna order track karein")
    r = TestClient(app).get(f"/api/sites/{app_site}/backend")
    assert r.status_code == 409 and "not on the app backend" in r.json()["detail"]


def test_studio_pins():
    js = JS.read_text()
    for k in ("__log", "__backups", "__secrets", "__usage"):
        assert f'data-coll="{k}"' in js
    assert "async function backendPane" in js and "/backend`" in js and "/app/log?limit=200" in js
    assert 'type="password"' in js and "never shown again" in js                         # the secure secret form
    assert "Restore now?" in js and "backups/preview" in js                              # restore = preview + her confirm
    assert 'id="wsRowAdd"' in js and "data-rowdel" in js and "data-role=" in js


def test_backend_area_in_a_browser(app_site, arena_server, monkeypatch):
    from tests.test_v0808_wapas import _fast_checks
    _fast_checks(monkeypatch)                     # no page checks inside the walk (the walk's own browser is running)
    base, browser, key = arena_server
    sid = app_site
    c = _linked(sid, key)
    assert c.post(f"/api/sites/{sid}/app/rows/orders", json={"item": "Kaju katli", "phone": "9876500000"}).status_code == 200
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{base}/console/web#/site/{sid}")
    page.locator('[data-view="cloud"]').first.wait_for(timeout=30000)
    page.click('[data-view="cloud"]')
    page.locator("#wsRowAdd").wait_for(timeout=20000)
    assert "Kaju katli" in page.inner_text("#wsCloud")
    page.click('[data-coll="__log"]')
    page.locator("#wsCloud h2:has-text('Change log')").wait_for(timeout=20000)
    assert "You (owner)" in page.inner_text("#wsCloud")
    page.click('[data-coll="__secrets"]')
    page.locator("#wsSecForm").wait_for(timeout=20000)
    page.fill("#wsSecForm input[name=name]", "my_key")
    page.fill("#wsSecForm input[name=value]", "secret-shown-nowhere-42")
    page.click("#wsSecForm button[type=submit]")
    page.locator("#wsCloud code:has-text('my_key')").wait_for(timeout=20000)
    assert "secret-shown-nowhere-42" not in page.content()
    page.click('[data-coll="__backups"]')
    page.locator("#wsBkNow").wait_for(timeout=20000)
    page.click("#wsBkNow")
    page.locator("#wsCloud [data-bkname]").first.wait_for(timeout=20000)
    page.click('[data-coll="__usage"]')
    page.locator("#wsUseForm").wait_for(timeout=20000)
    assert page.input_value("#wsUseForm input[name=rows]")
    ctx.close()
    assert not errors, errors
    assert json.dumps(errors) == "[]"
