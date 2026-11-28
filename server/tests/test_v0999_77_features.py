"""v0.999.77 D8 wave 1 (docs/WEB_DESIGN_ENGINE_PLAN.md phase D8): the React website uses her HTML website's OWN forms,
booking and shop on Hoola - the same leads, booking book, products, stock, orders and payments - and the parity
checklist (appengine/parity.py) reads from the code what works, what is partly there and what is not yet.
Done-line of D8: every checklist line "works" (not yet - the checklist says what is left)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.appengine import parity as PY
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setenv("SITE_CRITIC", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pages():
    return [{"slug": "home", "title": "Home", "for": "public", "sections": [
        {"type": "hero", "heading": "Sunrise Bakery", "line": "Fresh bread every morning in Pune.", "cta": "Order now"},
        {"type": "products_grid", "heading": "Today's bakes", "items": ["Pav - pack of 6", "Nankhatai - 250 g"]},
        {"type": "booking_slots", "heading": "Book a cake tasting", "items": ["Tasting - 30 min"]},
        {"type": "contact_block", "heading": "Visit us", "items": []}]}]


SITE = {"id": "site_abc123", "shop": {"on": True, "cod": True, "upi": False, "pickup": True, "products": [
    {"slug": "pav", "title": "Ladi pav", "price": 4000, "unit": "pack of 6", "in_stock": True},
    {"slug": "nankhatai", "title": "Nankhatai", "price": 22000, "unit": "250 g", "in_stock": False}]}}


# ---------------------------------------------------------------- 1. the writer uses her website's addresses
def test_the_writer_wires_forms_booking_and_her_real_shop():
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"phone": "+91 90000 00001", "_site": SITE}, "s", None)
    code, rows = W.page_file(_pages()[0], ctx, {})
    assert 'endpoint="/api/site-forms/site_abc123"' in code                   # contact form + booking: her lead / booking
    assert code.count('endpoint="/api/site-forms/site_abc123"') == 2
    prod = code.split('data-sec="home:1"')[1].split("</div>")[0]
    assert '"slug":"pav"' in prod and '"price":40' in prod and '"inStock":false' in prod and "shop={true}" in prod
    assert "Pav - pack of 6" not in prod                                        # her real shop, not the sketch's words
    lay = W.layout_file(ctx)
    assert 'import ShopCart from "@/islands/ShopCart";' in lay and 'api="/api/site-shop/site_abc123"' in lay
    assert "cod={true}" in lay and "pickup={true}" in lay and "upi={false}" in lay
    bare = W.Ctx("Sunrise Bakery", _pages(), {"phone": "+91 90000 00001"}, "s", None)   # no website behind it: as before
    code2, _ = W.page_file(_pages()[0], bare, {})
    assert "/api/site-forms/" not in code2 and "ShopCart" not in W.layout_file(bare)
    odd = W.Ctx("x", _pages(), {"_site": {"id": "../../etc", "shop": {"on": True, "products": []}}}, "s", None)
    assert odd.site_id == "etc" and odd.forms == "/api/site-forms/etc"         # an id is never a path
    assert "ShopCart.tsx" in " ".join(W.kit_files(rows, True)) and "contact-block.tsx" in " ".join(W.kit_files(rows, True))


def test_kit_files_are_brought_up_to_date_unless_she_changed_them(ae_env):
    from app.appengine import service as AE
    app = AE.create(T, name="Kit", brief="x", render="site")
    root = AE.src_dir(AE._load(T, app["id"]))
    rel = "src/components/blocks/contact-block.tsx"
    (root / rel).write_text("// an older kit\nexport default function X() { return null; }\n")
    out = W.sync_kit(T, app["id"], [rel, "src/islands/ShopCart.tsx"])
    assert out["updated"] == [rel] and "fetch(endpoint" in (root / rel).read_text()      # the cart was already current
    assert (root / "src/islands/ShopCart.tsx").is_file()
    (root / rel).write_text((root / rel).read_text() + "\n// her own change\n")
    out = W.sync_kit(T, app["id"], [rel])
    assert out["kept"] == [rel] and "her own change" in (root / rel).read_text()


# ---------------------------------------------------------------- 2. the parity checklist reads the code
def test_the_parity_checklist_is_read_from_the_code():
    rep = PY.check()
    st = {r["key"]: r["state"] for r in rep["rows"]}
    assert st["forms"] == st["booking"] == st["payments"] == "works"
    # waves 2-5 of the same release: the blog, and the shop's cart kept on her own address; push built in wave 9 (was "not yet")
    assert st["shop"] == "works" and st["push"] == "works" and st["blog"] == "works"
    assert rep["done"] and len(rep["rows"]) == len(PY.CHECKLIST) >= 18   # every row works (was: not done)
    push = next(r for r in rep["rows"] if r["key"] == "push")
    assert push["missing"] == []   # wave 9 (was: "own address" named in what was missing)
    txt = "\n".join(PY.lines(rep))
    assert "[x] Contact and enquiry forms" in txt and "[x] Browser push" in txt   # wave 9 (was "[ ] Browser push")
    assert "parity" in (ROOT / "server/app/appengine/__main__.py").read_text()


def test_the_new_kit_files_pass_the_rules():
    from app.appengine import image as IMG
    from app.appengine import rules as RL
    deps = set(IMG.CORE) | set(IMG.DEV)
    for rel in ("src/islands/ShopCart.tsx", "src/components/blocks/contact-block.tsx",
                "src/components/blocks/booking-slots.tsx", "src/components/blocks/products-grid.tsx"):
        code = (ROOT / "server/app/appengine/template" / rel).read_text()
        assert RL.check_file(rel, code, deps) == [], rel


# ---------------------------------------------------------------- 3. a real React website, walked in Chromium
@pytest.fixture
def shop_site(ae_env, monkeypatch):
    _box()
    from app.net import booking as BK
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    monkeypatch.setattr(BK, "free_slots", lambda tenant, n=12: ["2030-01-07T10:00", "2030-01-07T11:00"][:n])
    monkeypatch.setattr(BK, "say_slot", lambda tenant, iso: "Mon 7 Jan, " + iso[-5:])
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads, cakes, order online.", name="Sunrise Bakery")
    S.shop_setup(T, v["id"], settings={"on": True, "cod": True, "pickup": True},
                 products=[{"title": "Ladi pav", "price": 40, "stock": 20, "unit": "pack of 6"},
                           {"title": "Nankhatai", "price": 220, "stock": 5, "unit": "250 g"}])
    PT._write_version(S._load(v["id"]), _pages(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    return v["id"], out["react"]["id"]


def _serve(dist: Path):
    """The built site served like its live address (speed._respond), and /api/* answered by the REAL server app."""
    import http.server
    import socketserver
    import threading
    from fastapi.testclient import TestClient
    from app import main as M
    from app.appengine import speed as SP
    client = TestClient(M.app)

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _api(self, method: str):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else None
            r = client.request(method, self.path, content=body,
                               headers={k: v for k, v in self.headers.items() if k.lower() in ("content-type", "origin")})
            self.send_response(r.status_code)
            for k, v in r.headers.items():
                if k.lower() not in ("content-length", "transfer-encoding", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(r.content)))
            self.end_headers()
            self.wfile.write(r.content)

        def do_OPTIONS(self):  # noqa: N802
            self._api("OPTIONS")

        def do_POST(self):  # noqa: N802
            self._api("POST")

        def do_GET(self):  # noqa: N802
            if self.path.startswith("/api/"):
                return self._api("GET")
            path = self.path.split("?", 1)[0]
            code, data, ctype, hdr = SP._respond(dist, path[len(SP.PREFIX):])
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            for k, v in hdr.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}{SP.PREFIX}"


def test_a_visitor_sends_a_form_asks_for_a_time_and_orders_on_the_react_site(shop_site):
    from sqlalchemy import select
    from playwright.sync_api import sync_playwright
    from app.appengine import service as AE
    from app.appengine import speed as SP
    from app.db import session
    from app.site.models import SiteLead
    sid, ref = shop_site
    app = AE._load(T, ref)
    dist = AE.ver_dir(app, app.version) / "dist"
    home = (AE.src_dir(app) / "src" / "pages" / "HomePage.tsx").read_text()
    assert f'endpoint="/api/site-forms/{sid}"' in home and '"slug":"ladi-pav"' in home
    srv, base = _serve(dist)
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(base, wait_until="load")
            # the contact form really sends: her lead
            form = pg.locator('section[data-block="contact_block"] form')
            form.scroll_into_view_if_needed()
            form.wait_for()
            pg.wait_for_timeout(800)
            form.get_by_label("Your name").fill("Asha")
            form.get_by_label("Mobile number").fill("9876543210")
            form.get_by_role("button", name="Send message").click()
            pg.get_by_text("Sent", exact=False).first.wait_for(timeout=15000)
            # booking: her real free times, a request she confirms
            bk = pg.locator('section[data-block="booking_slots"]')
            bk.scroll_into_view_if_needed()
            bk.get_by_role("button", name="Mon 7 Jan, 10:00").click(timeout=15000)
            bk.get_by_label("Your name").fill("Ravi")
            bk.get_by_label("Mobile number").fill("9123456780")
            bk.get_by_role("button", name="Request this time").click()
            pg.get_by_text("Request sent for Mon 7 Jan, 10:00", exact=False).first.wait_for(timeout=15000)
            # the shop: add to cart -> details -> order (cash on delivery) -> the order number + its link
            pr = pg.locator('section[data-block="products_grid"]')
            pr.scroll_into_view_if_needed()
            pg.wait_for_timeout(800)
            pr.get_by_role("link", name="Add to cart").first.click()
            dlg = pg.get_by_role("dialog")
            dlg.get_by_role("button", name="One more Ladi pav").click()
            dlg.get_by_role("button", name="Continue").click()
            dlg.get_by_label("Your name").fill("Meera")
            dlg.get_by_label("Mobile number").fill("9988776655")
            dlg.get_by_label("Delivery address").fill("12, Shanti Complex, Pune")
            dlg.get_by_label("PIN code").fill("411001")
            dlg.get_by_role("button", name="Send order").click()
            pg.get_by_text("Keep this link", exact=False).first.wait_for(timeout=15000)
            link = dlg.locator("a.break-all").inner_text()
            assert "?order=" in link and "&t=" in link
            assert "Ladi pav × 2" in dlg.inner_text()
            pg.goto(link, wait_until="load")                                   # the link she keeps: the order again
            pg.get_by_text("Ladi pav × 2", exact=False).first.wait_for(timeout=15000)
            b.close()
    finally:
        srv.shutdown()
    assert not errors, errors
    with session() as s:
        leads = list(s.scalars(select(SiteLead).where(SiteLead.site_id == sid)))
    kinds = sorted(x.kind for x in leads)
    assert kinds == ["booking", "enquiry"] and any(x.slot == "2030-01-07T10:00" for x in leads)


def test_her_product_change_reaches_the_react_site_by_code(shop_site):
    from app.appengine import service as AE
    from app.site import service as S
    sid, ref = shop_site
    S.shop_setup(T, sid, products=[{"title": "Multigrain loaf", "price": 120, "stock": 3}])
    home = (AE.src_dir(AE._load(T, ref)) / "src" / "pages" / "HomePage.tsx").read_text()
    assert '"slug":"multigrain-loaf"' in home and '"price":120' in home
