"""v0.351 DUKAAN (built as 0.344) (web design Phase 7 step 1, owner: "START PHASE 3"): a real online shop on any Hoola website. Products
with her prices and stock, a cart, checkout, UPI to HER UPI ID or cash on delivery, orders she moves along, a private
tracking link. The server decides every price and total (a cart that says otherwise is ignored), stock can never go
below zero even when two buyers race for the last piece, money is never marked received by Hoola (the customer tells,
she confirms), and the whole path is walked in a real browser."""
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

SHOP = {"on": True, "cod": True, "pickup": True, "delivery": "40", "free_above": "2000", "upi": "sharmasweets@okhdfcbank"}
PRODUCTS = [{"title": "Kaju Katli", "price": "900", "unit": "1 kg", "stock": 3},
            {"title": "Motichoor Laddoo", "price": "600", "unit": "1 kg"}]
BUYER = {"name": "Asha", "phone": "9876543210", "address": "12 Station Road, Akot", "pincode": "444101"}


def test_money_is_exact():
    from app.site import shop as SH
    assert SH.paise("₹1,250.50") == 125050 and SH.paise(900) == 90000 and SH.paise("Rs 45.5") == 4550
    assert SH.rupees(12500000) == "₹1,25,000" and SH.rupees(125050) == "₹1,250.50" and SH.rupees(99900) == "₹999"
    for bad in ("abc", "-5", "1.234", ""):
        with pytest.raises(SH.ShopError):
            SH.paise(bad)


def _built_shop(S):
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    out = S.shop_setup(T, v["id"], SHOP, PRODUCTS)
    assert "2 naye products" in out["say"]
    return v["id"]


_IP = iter(range(1, 10_000))


def _order(S, sid, items, **kw):
    return S.shop_order(sid, {**BUYER, "method": "upi", "items": items, **kw}, ip=f"10.0.{next(_IP)}.1")


def test_the_server_decides_prices_stock_and_payment(site_env):
    from app.site import service as S
    from app.site import shop as SH
    sid = _built_shop(S)
    live = S._assemble_live(S._load(sid))
    shop = (live / "shop" / "index.html").read_text()
    assert 'data-hoola-buy="kaju-katli"' in shop and "₹900" in shop and 'name="hoola-shop"' in shop
    assert (live / "assets" / "hoola-shop.js").exists() and 'href="shop/"' in (live / "index.html").read_text()   # in the menu
    # a cart that claims its own price / total is ignored
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 2, "price": 1}, {"slug": "motichoor-laddoo", "qty": 1}], total=5)
    assert o["total"] == "₹2,400" and o["delivery"] == "₹0" and o["number"] == "O-1001"         # free above ₹2,000
    assert o["pay"]["vpa"] == "sharmasweets@okhdfcbank" and "am=2400.00" in o["pay"]["link"] and o["pay"]["qr"].startswith("data:image/svg+xml")
    small = _order(S, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod")
    assert small["total"] == "₹640" and "pay" not in small                                     # ₹40 delivery under ₹2,000
    assert next(p for p in SH.products(sid) if p["slug"] == "kaju-katli")["stock"] == 1
    for items, why in (([{"slug": "kaju-katli", "qty": 2}], "sirf 1 bache"),
                       ([{"slug": "no-such", "qty": 1}], "ab dukaan mein nahi"),
                       ([], "Cart khaali")):
        with pytest.raises(SH.ShopError) as e:
            _order(S, sid, items)
        assert why in str(e.value)
    with pytest.raises(SH.ShopError):
        _order(S, sid, [{"slug": "kaju-katli", "qty": 1}], phone="12345")
    # payment: the customer tells, SHE confirms; a cancel gives the stock back
    with pytest.raises(SH.ShopError) as e:
        S.shop_paid(sid, o["number"], o["token"], "ab")
    assert "UTR" in str(e.value)
    with pytest.raises(SH.ShopError):
        S.shop_paid(sid, o["number"], "wrong-token", "UTR123456789")
    told = S.shop_paid(sid, o["number"], o["token"], "UTR123456789")
    assert told["status"] == "payment_told" and told["utr_told"]
    assert S.shop_track(sid, o["number"], o["token"])["status"] == "payment_told"
    with pytest.raises(S.SiteError):
        S.shop_move(T, sid, o["number"], "delivered")                                             # no skipping steps
    for step in ("confirmed", "packed", "shipped", "delivered"):
        assert S.shop_move(T, sid, o["number"], step)["order"]["status"] == step
    S.shop_move(T, sid, small["number"], "cancelled")
    k = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    S.shop_move(T, sid, k["number"], "cancelled")
    assert next(p for p in SH.products(sid) if p["slug"] == "kaju-katli")["stock"] == 1          # given back
    summ = S.shop_orders(T, sid)["summary"]
    assert summ["orders"] == 3 and summ["sales"] == "₹2,400"


def test_two_buyers_never_both_get_the_last_piece(site_env):
    from app.site import service as S
    from app.site import shop as SH
    sid = _built_shop(S)
    SH.upsert_products(sid, [{"slug": "kaju-katli", "stock": 1}])
    got, refused, other = [], [], []
    gate = threading.Barrier(5)

    def buy(i):
        gate.wait()
        try:
            got.append(S.shop_order(sid, {**BUYER, "method": "cod", "items": [{"slug": "kaju-katli", "qty": 1}]}, ip=f"9.9.9.{i}"))
        except SH.ShopError:
            refused.append(i)
        except Exception as e:                       # e.g. a locked database: must not happen silently
            other.append(repr(e))
    ts = [threading.Thread(target=buy, args=(i,)) for i in range(5)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(got) == 1 and len(refused) + len(other) == 4, (got, refused, other)
    assert next(p for p in SH.products(sid, False) if p["slug"] == "kaju-katli")["stock"] == 0


def test_public_endpoints_and_owner_only(site_env):
    from app.main import app, current_tenant
    from app.site import service as S
    sid = _built_shop(S)
    c = TestClient(app)
    r = c.get(f"/api/site-shop/{sid}/products")
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "*"
    assert {p["slug"] for p in r.json()["products"]} == {"kaju-katli", "motichoor-laddoo"} and "stock" not in r.json()["products"][0]
    o = c.post(f"/api/site-shop/{sid}/order", json={**BUYER, "method": "upi", "items": [{"slug": "kaju-katli", "qty": 1}]}).json()
    assert o["ok"] and o["total"] == "₹940"
    bad = c.post(f"/api/site-shop/{sid}/order", json={**BUYER, "items": [{"slug": "kaju-katli", "qty": 50}]})
    assert bad.status_code == 409 and not bad.json()["ok"]
    assert c.get(f"/api/site-shop/{sid}/order/{o['number']}?t=nope").status_code == 404
    assert c.get(f"/api/site-shop/{sid}/order/{o['number']}?t={o['token']}").json()["pay"]["amount"] == "₹940"
    assert c.post(f"/api/site-shop/{sid}/order/{o['number']}/paid", json={"token": o["token"], "utr": "123456789012"}).json()["status"] == "payment_told"
    assert c.get(f"/api/sites/{sid}/shop/orders").json()["orders"][0]["utr"] == "123456789012"
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        other = c.get(f"/api/sites/{sid}/shop/orders")
        assert other.status_code in (400, 403, 404) and "9876543210" not in other.text          # not hers: nothing shown
        assert c.post(f"/api/sites/{sid}/shop/orders/{o['number']}", json={"to": "confirmed"}).status_code in (400, 403, 404)
    finally:
        app.dependency_overrides.pop(current_tenant, None)
    S.shop_setup(T, sid, {"on": False})
    assert c.get(f"/api/site-shop/{sid}/products").status_code == 404
    assert c.post(f"/api/site-shop/{sid}/order", json={**BUYER, "items": [{"slug": "kaju-katli", "qty": 1}]}).status_code == 403


@pytest.fixture
def shop_server(site_env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from app.site import service as S
    sid = _built_shop(S)                 # built BEFORE this test's own browser starts (the build checks in Chromium too)
    from tests.test_v161_console_e2e import _free_port
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
    try:
        pw = sync_api.sync_playwright().start()
        import os
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium: {str(e)[:60]}")
        yield f"http://127.0.0.1:{port}", browser, sid
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_a_customer_buys_in_a_real_browser(shop_server):
    from app.site import service as S
    base, browser, sid = shop_server
    preview = S.view(S._load(sid))["preview"]
    pg = browser.new_page(viewport={"width": 390, "height": 844})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + preview + "shop/")
    pg.wait_for_selector(".hs-cart-b", state="attached")      # the site's CSP refuses eval, so no wait_for_function here
    pg.click('[data-hoola-buy="kaju-katli"]')
    pg.click('[data-hoola-buy="kaju-katli"]')
    pg.click('[data-hoola-buy="motichoor-laddoo"]')
    assert pg.inner_text(".hs-cart-b b") == "3"
    import os
    shots = os.environ.get("SHOP_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/shop-page.png", full_page=True)
    pg.click(".hs-cart-b")
    assert "₹1,800" in pg.inner_text(".hs-cart") and "₹600" in pg.inner_text(".hs-cart")
    if shots:
        pg.screenshot(path=f"{shots}/shop-cart.png")
    pg.click(".hs-shop-in .btn-primary")                                       # Aage badhein
    for k, v in BUYER.items():
        pg.fill(f'.hs-checkout [name="{k}"]', v)
    pg.click('.hs-checkout button[type="submit"]')
    pg.wait_for_selector(".hs-shop-pay")
    txt = pg.inner_text(".hs-shop-in")
    assert "Order O-1001" in txt and "Total: ₹2,400" in txt and "sharmasweets@okhdfcbank" in txt
    assert pg.get_attribute(".hs-shop-pay img", "src").startswith("data:image/svg+xml")
    assert pg.get_attribute(".hs-shop-pay a", "href").startswith("upi://pay?")
    assert pg.inner_text(".hs-cart-b b") == "0"                              # the cart is empty after ordering
    if shots:
        pg.screenshot(path=f"{shots}/shop-pay.png")
    pg.fill('.hs-shop-pay [name="utr"]', "UTR998877665")
    pg.click('.hs-shop-pay button[type="submit"]')
    pg.wait_for_selector(".hs-status:has-text('Payment')")
    track = pg.get_attribute(".hs-track a", "href")
    pg2 = browser.new_page()
    pg2.goto(track)
    pg2.wait_for_selector(".hs-status")
    assert "Payment" in pg2.inner_text(".hs-status")
    o = S.shop_orders(T, sid)["orders"][0]
    assert o["status"] == "payment_told" and o["utr"] == "UTR998877665" and o["phone"] == "9876543210"
    assert not errs, errs


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.834.0"
    assert "0.834.0+833" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
