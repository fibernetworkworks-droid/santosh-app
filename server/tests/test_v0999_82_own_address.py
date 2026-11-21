"""v0.999.82 D8 wave 5 (owner's choice: "Own address per site"): a website written in React goes live on its OWN address
(its free <name>.<SITES_BASE_DOMAIN> address or her domain) unsealed - its own origin, so the visitor's browser may keep
her cart and ticks - while the preview under Hoola's address stays sealed. Only that site's own forms / booking / shop
calls reach Hoola from its address; going live stays her tap on the card's hash."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.site import rxhost as RH
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_77_features import _pages
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

HOST = "sunrise-bakery.hoolasites.in"


@pytest.fixture(autouse=True)
def _on(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setenv("SITE_CRITIC", "false")
    monkeypatch.setenv("SITES_BASE_DOMAIN", "hoolasites.in")
    monkeypatch.setenv("SITE_HOSTED_DIR", str(tmp_path / "hosted"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    from app.site import hosting as H
    H.host_map(force=True)


# ---------------------------------------------------------------- 1. by code
def test_only_this_sites_own_visitor_addresses_pass():
    assert RH.allowed("site_abc", "/api/site-forms/site_abc")
    assert RH.allowed("site_abc", "/api/site-forms/site_abc/slots")
    assert RH.allowed("site_abc", "/api/site-shop/site_abc/order/12")
    assert not RH.allowed("site_abc", "/api/site-shop/site_xyz/order")          # another site's shop
    assert not RH.allowed("site_abc", "/api/site-shop/site_abcdef/order")
    assert not RH.allowed("site_abc", "/api/console/login")
    assert not RH.allowed("", "/api/site-forms/")


def test_publish_fills_every_placeholder_for_her_address(tmp_path, monkeypatch):
    src = tmp_path / "dist"
    (src / "about").mkdir(parents=True)
    (src / "assets").mkdir()
    (src / "index.html").write_text('<html><head><link rel="canonical" href="__hoola_origin__/__hoola_base__/"></head>'
                                    '<body><a href="/__hoola_base__/about">About</a></body></html>')
    (src / "about" / "index.html").write_text("<html><head></head><body>About</body></html>")
    (src / "sitemap.xml").write_text("<loc>__hoola_origin__/__hoola_base__/about</loc>")
    (src / "assets" / "a.js").write_text("x")
    (src / "__pages.json").write_text("{}")
    (src / "__spa.html").write_text("spa")

    class R:
        id = "site_abc"
    monkeypatch.setattr(RH, "dist", lambda r: src)
    monkeypatch.setattr(RH, "version", lambda r: 7)
    out = tmp_path / "out"
    assert RH.publish(R(), "her-shop.in", out) == 7
    home = (out / "index.html").read_text()
    assert '<base href="/">' in home and 'href="https://her-shop.in/"' in home and 'href="/about"' in home
    assert "__hoola" not in home and "__hoola" not in (out / "sitemap.xml").read_text()
    assert (out / "assets" / "a.js").read_text() == "x"
    assert not (out / "__pages.json").exists() and not (out / "__spa.html").exists()
    assert json.loads((out / RH.MARK).read_text()) == {"site": "site_abc", "version": 7}


def test_her_address_is_not_sealed_but_keeps_its_rules():
    h = RH.headers()
    assert "sandbox" not in h["Content-Security-Policy"]
    assert "script-src 'self'" in h["Content-Security-Policy"] and "connect-src 'self'" in h["Content-Security-Policy"]
    assert h["Strict-Transport-Security"].startswith("max-age=")


def test_only_hoolas_own_tooling_may_keep_a_value_in_the_browser():
    from app.appengine import rules as RL
    from app.appengine import service as AE
    assert "src/lib/keep.ts" in RL.LOCKED and "src/lib/keep.ts" in AE.TOOLING
    bad = RL.check_file("src/components/sections/X.tsx", "const v = localStorage.getItem('a');", set())
    assert bad and bad[0]["rule"] == "unsafe"                                  # a model-written section still may not


def test_the_checklist_reads_the_own_address():
    from app.appengine import parity as PY
    st = {r["key"]: r for r in PY.check()["rows"]}
    assert st["domains"]["state"] == "works", st["domains"]
    assert st["shop"]["state"] == "works", st["shop"]
    assert st["learning"]["state"] == "works", st["learning"]
    assert st["push"]["state"] == "not yet" and st["live"]["state"] == "not yet"      # possible now, not built yet


# ---------------------------------------------------------------- 2. a real React shop, live on its own address
@pytest.fixture
def live_shop(ae_env, monkeypatch):
    _box()
    from app.net import booking as BK
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    monkeypatch.setattr(BK, "free_slots", lambda tenant, n=12: ["2030-01-07T10:00"][:n])
    monkeypatch.setattr(BK, "say_slot", lambda tenant, iso: "Mon 7 Jan, " + iso[-5:])
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads, cakes, order online.", name="Sunrise Bakery")
    S.shop_setup(T, v["id"], settings={"on": True, "cod": True, "pickup": True},
                 products=[{"title": "Ladi pav", "price": 40, "stock": 20, "unit": "pack of 6"}])
    PT._write_version(S._load(v["id"]), _pages(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    return v["id"], out["react"]["id"]


def test_her_react_shop_goes_live_on_its_own_address_only_on_her_tap(live_shop):
    from playwright.sync_api import sync_playwright
    from app.appengine import speed as SP
    from app.main import app
    sid, _ = live_shop
    c = TestClient(app)
    card = c.post(f"/api/sites/{sid}/launch-request", json={}).json()
    assert card["hosts"] == [HOST] and not card["blockers"] and card["react"] is True, card
    assert c.post(f"/api/sites/{sid}/launch", json={"hash": "wrong"}).status_code == 400
    r = c.post(f"/api/sites/{sid}/launch", json={"hash": card["hash"]})
    assert r.status_code == 200, r.text
    home = c.get("/", headers={"host": HOST})
    assert home.status_code == 200 and "Sunrise Bakery" in home.text
    assert "sandbox" not in home.headers["content-security-policy"]              # its own origin: not sealed
    assert '<base href="/">' in home.text and "__hoola" not in home.text
    assert f'rel="canonical" href="https://{HOST}/"' in home.text
    prods = c.get(f"/api/site-shop/{sid}/products", headers={"host": HOST})       # its own shop answers on its address
    assert prods.status_code == 200 and "ladi-pav" in prods.text
    assert c.post("/api/console/login", json={}, headers={"host": HOST}).status_code == 404   # nothing else of Hoola's
    assert c.get("/api/sites", headers={"host": HOST}).status_code == 404
    # a visitor adds to the cart, reloads: the cart is still there (her own address keeps it)
    import http.server
    import socketserver
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _go(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else None
            res = c.request(method, self.path, content=body,
                            headers={"host": HOST, **({"content-type": self.headers["content-type"]} if self.headers.get("content-type") else {})})
            self.send_response(res.status_code)
            for k, v in res.headers.items():
                if k.lower() not in ("content-length", "transfer-encoding", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(res.content)))
            self.end_headers()
            self.wfile.write(res.content)

        def do_GET(self):  # noqa: N802
            self._go("GET")

        def do_POST(self):  # noqa: N802
            self._go("POST")
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/", wait_until="load")
            pr = pg.locator('section[data-block="products_grid"]')
            pr.scroll_into_view_if_needed()
            pg.wait_for_timeout(800)
            pr.get_by_role("link", name="Add to cart").first.click()
            pg.get_by_role("dialog").get_by_text("Ladi pav").first.wait_for(timeout=15000)
            pg.reload(wait_until="load")
            pg.wait_for_timeout(1500)
            kept = pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hoola:cart:'))")
            assert kept, "the cart was not kept"
            assert pg.evaluate(f"JSON.parse(localStorage.getItem({json.dumps(kept[0])}))")[0]["slug"] == "ladi-pav"
            b.close()
    finally:
        srv.shutdown()
    assert not errors, errors
