"""v0.538 BADA CATALOGUE (web Step 6 part 1 = W8 content at scale + W10 speed of docs/WEB_PLATFORM_PLAN.md; checkpoint
"5,000-product marketplace, load test passed").

Her file / Sheet / dataset -> preview (nothing written) -> her Apply -> pages BY CODE: 5,000 product pages, listing pages
of 48 with numbered pages, a filter index, split sitemaps, the thin / duplicate gate (noindex + canonical, left out of the
sitemaps), photos fetched once and resized to AVIF / WebP / JPEG, every text file pre-compressed, every page under the
100 KB HTML budget; her shop's products synced (price + stock); a checkout retried with the same id is ONE order, and
parallel checkouts never share an order number."""
import csv
import gzip
import io
import json
import re
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0351_dukaan import BUYER, SHOP
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

BRANDS = ["Amul", "Haldiram", "Bikaji", "Britannia", "Parle", "MTR", "Tata", "Patanjali"]
KINDS = ["Namkeen", "Sweets", "Biscuits", "Spices", "Tea", "Ghee"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.769.0"


def _csv(n: int, dup_every: int = 0, thin_every: int = 0, bad_rows: bool = True) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SKU", "Product Name", "Brand", "Category", "MRP", "Stock", "Description", "Image URL"])
    for i in range(n):
        name = f"{KINDS[i % 6]} Pack {i:05d}"
        desc = (f"Fresh {KINDS[i % 6].lower()} from {BRANDS[i % 8]}, packed in Akola. Good for families and guests, keeps "
                f"for three months in a dry place. Pack number {i}.")
        if thin_every and i % thin_every == 1:
            desc = ""
        if dup_every and i % dup_every == 2 and i > 2:   # same content as item i-1 under another SKU
            prev = i - 1
            name = f"{KINDS[prev % 6]} Pack {prev:05d}"
            desc = (f"Fresh {KINDS[prev % 6].lower()} from {BRANDS[prev % 8]}, packed in Akola. Good for families and guests, keeps "
                    f"for three months in a dry place. Pack number {prev}.")
            w.writerow([f"SKU{i:05d}", name, BRANDS[prev % 8], KINDS[prev % 6], str(50 + prev % 400), "25", desc, ""])
            continue
        w.writerow([f"SKU{i:05d}", name, BRANDS[i % 8], KINDS[i % 6], str(50 + i % 400), "25", desc,
                    f"https://cdn.example.in/p/{i}.jpg" if i < 6 else ""])
    if bad_rows:
        w.writerow(["SKU99998", "", "Amul", "Ghee", "100", "1", "no name", ""])
        w.writerow(["SKU99999", "Broken price", "Amul", "Ghee", "free", "1", "x", ""])
    return buf.getvalue().encode()


def _site(S, shop=True):
    v = S.new(T, "Sharma Mart kirana ki website", name="Sharma Mart", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    if shop:
        S.shop_setup(T, v["id"], {**SHOP, "upi": "sharmamart@okhdfcbank"}, [])
    return v["id"]


def _jpeg(color=(200, 80, 40), size=(1400, 1000)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "JPEG")
    return b.getvalue()


def test_mapping_preview_writes_nothing_and_apply_is_idempotent(site_env, monkeypatch):
    from app.main import app
    from app.site import catalog as CAT
    from app.site import service as S
    sid = _site(S)
    c = TestClient(app)
    rows = CAT.parse_file(_csv(30, dup_every=10, thin_every=7))
    m = CAT.guess_mapping(rows)
    assert (m["title"], m["key"], m["price"], m["image"], m["description"], m["stock"]) == \
        ("Product Name", "SKU", "MRP", "Image URL", "Description", "Stock")
    assert m["facets"] == ["Brand", "Category"]
    r = c.post(f"/api/sites/{sid}/catalog/preview", files={"file": ("products.csv", _csv(30, dup_every=10, thin_every=7), "text/csv")},
               data={"coll": "products", "label": "Products"})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["items"] == 30 and p["new"] == 30 and p["rejected"] == 2
    assert {x["why"].split(":")[0] for x in p["rejected_rows"]} == {"naam khaali", "daam ank nahi"}
    assert p["dup"] == 2 and p["thin"] >= 3 and p["mapping"]["filters"] == ["Brand", "Category"]
    assert CAT.lists(T, sid)["lists"] == []                                              # nothing written yet
    assert c.post(f"/api/sites/{sid}/catalog/apply", json={"hash": "0" * 20}).status_code == 409
    a = c.post(f"/api/sites/{sid}/catalog/apply", json={"hash": p["hash"]}).json()
    assert a["added"] == 30 and a["live"] == 30 and a["dup"] == 2
    assert a["shop"]["products"] == 30                                                   # priced items = her shop's products
    # the same file again: nothing changes, nobody's address moves
    p2 = c.post(f"/api/sites/{sid}/catalog/preview", files={"file": ("p.csv", _csv(30, dup_every=10, thin_every=7), "text/csv")},
                data={"coll": "products"}).json()
    assert (p2["new"], p2["changed"], p2["same"]) == (0, 0, 30)
    a2 = c.post(f"/api/sites/{sid}/catalog/apply", json={"hash": p2["hash"]}).json()
    assert (a2["added"], a2["changed"], a2["hidden"]) == (0, 0, 0)
    # a smaller file with replace: the missing items are hidden, never deleted; bringing them back keeps their address
    p3 = c.post(f"/api/sites/{sid}/catalog/preview", files={"file": ("p.csv", _csv(20, dup_every=10, thin_every=7, bad_rows=False), "text/csv")},
                data={"coll": "products"}).json()
    assert p3["hidden_if_replace"] == 10
    a3 = c.post(f"/api/sites/{sid}/catalog/apply", json={"hash": p3["hash"], "replace": True}).json()
    assert a3["hidden"] == 10 and a3["live"] == 20
    from app.db import session
    from sqlalchemy import select
    with session() as s:
        before = dict(s.execute(select(CAT.SiteCatalogItem.key, CAT.SiteCatalogItem.slug)).all())
    p4 = CAT.preview(T, sid, "products", CAT.parse_file(_csv(30, dup_every=10, thin_every=7)))
    CAT.apply(T, sid, p4["hash"])
    with session() as s:
        after = dict(s.execute(select(CAT.SiteCatalogItem.key, CAT.SiteCatalogItem.slug)).all())
    assert after == before and len(after) == 30
    # her own mapping wins; a wrong column is named
    with pytest.raises(CAT.CatalogError, match="Nope"):
        CAT.preview(T, sid, "products", rows, {"title": "Nope"})
    with pytest.raises(CAT.CatalogError):
        CAT.preview(T, sid, "assets", rows)                                              # a reserved address


def test_five_thousand_product_marketplace_builds_fast_small_and_indexable(site_env, monkeypatch):
    """The checkpoint's catalogue half: 5,000 products -> every page by code, listings of 48, filters, split sitemaps,
    the quality gate, pre-compressed files, every page under the 100 KB HTML budget."""
    from app.site import build as B
    from app.site import catalog as CAT
    from app.site import service as S
    from app.site import speed as SPD
    monkeypatch.setattr(CAT, "SITEMAP_MAX", 2000)                                       # 3 product sitemap files
    monkeypatch.setattr(CAT, "_FETCH", lambda url: _jpeg())
    monkeypatch.setattr(CAT, "start_images", lambda site_id: None)
    sid = _site(S)
    rows = CAT.parse_file(_csv(5000, dup_every=500, thin_every=1000))
    p = CAT.preview(T, sid, "products", rows, label="Products", item_label="Product")
    assert p["items"] == 5000 and p["dup"] == 5 and p["thin"] == 4      # 4 "copies" differ from their thin original; item 1 has a photo
    t0 = time.time()
    a = CAT.apply(T, sid, p["hash"])
    t_apply = time.time() - t0
    assert a["live"] == 5000 and a["shop"]["products"] == 5000
    CAT.images(sid)                                                                      # 6 photos fetched once, resized once
    assert CAT._count(sid, "products")["photos"] == 6
    r = S._load(sid)
    ctx = S._ctx(r)
    ctx["noindex"] = False                                                              # as published on her address
    out = B.site_dir(r.tenant_id, r.id) / "bigtest"
    t0 = time.time()
    res = B.assemble(ctx, ctx["plan"], S._sections(r), {x["name"]: x for x in json.loads(r.photos or "[]")}, out,
                     "https://sharmamart.in", S.form_endpoint(r))
    t_build = time.time() - t0
    print(f"\napply {t_apply:.1f}s  build {t_build:.1f}s  pages {res['pages']}  noindex {res['catalog']['noindex']}")
    designed = any(pg["slug"] == "products" for pg in ctx["plan"].get("pages", []))   # her designed page carries listing page 1
    assert res["catalog"]["pages"] == 5000 + 105 - designed and res["catalog"]["noindex"] == 9     # 105 listing pages of 48
    assert t_build < 240
    item = out / "products" / "namkeen-pack-00000" / "index.html"
    html = item.read_text()
    assert "₹50" in html and 'data-hoola-buy="products/namkeen-pack-00000"' in html and "<picture>" in html
    assert 'type="image/avif"' in html and 'width="' in html                             # no layout shift
    assert "More: Brand Amul" in html                                                    # links to its own family
    # the quality gate: a duplicate points at the original and is not indexed; a thin page is shown but not indexed
    dup = (out / "products" / "spices-pack-00501-2" / "index.html").read_text()
    assert 'name="robots" content="noindex,follow"' in dup and 'rel="canonical" href="https://sharmamart.in/products/spices-pack-00501/"' in dup
    thin = (out / "products" / "ghee-pack-01001" / "index.html").read_text()
    assert 'content="noindex,follow"' in thin
    # listing pages: 48 cards, numbered pages, the filter bar with counts on page 1 only
    l1 = (out / "products" / "index.html").read_text()
    assert l1.count('class="hs-cat-card"') == 48 and 'href="../products/page/105/"' in l1 and 'data-hoola-catalog=' in l1
    assert "Amul (625)" in l1 and "hoola-catalog.js" in l1
    l50 = (out / "products" / "page" / "50" / "index.html").read_text()
    assert l50.count('class="hs-cat-card"') == 48 and 'aria-current="page">50<' in l50 and 'data-hoola-catalog=' not in l50
    assert (out / "products" / "page" / "105" / "index.html").read_text().count('class="hs-cat-card"') == 5000 - 104 * 48
    # the filter index: one row per item, facets as small numbers
    idx = json.loads((out / "assets" / "catalog" / "products.json").read_text())
    assert len(idx["items"]) == 5000 and [f["label"] for f in idx["facets"]] == ["Brand", "Category"]
    assert idx["items"][0][:4] == ["namkeen-pack-00000", "Namkeen Pack 00000", 50.0, "₹50"] and idx["items"][0][4].endswith("-320.webp")
    # split sitemaps: an index + pages + 3 product files; thin / duplicate items left out
    sm = (out / "sitemap.xml").read_text()
    assert "<sitemapindex" in sm and sm.count("<sitemap>") == 4
    locs = sum(len(re.findall("<loc>", (out / f"sitemap-products-{k}.xml").read_text())) for k in (1, 2, 3))
    assert locs == 5000 - 9 + 105 - designed                                           # page 1 of a designed list is in sitemap-pages
    assert "spices-pack-00501-2" not in "".join((out / f"sitemap-products-{k}.xml").read_text() for k in (1, 2, 3))
    assert "Sitemap: https://sharmamart.in/sitemap.xml" in (out / "robots.txt").read_text()
    # W10: every page under the 100 KB budget, every text file pre-compressed (and still byte-for-byte the same page)
    bud = SPD.budget(out)
    assert bud["over_count"] == 0 and bud["pages"] >= 5105, bud
    assert gzip.decompress((out / "products" / "index.html.gz").read_bytes()) == l1.encode()
    assert len(list(out.rglob("*.gz"))) >= 5000
    assert not any(n.endswith(".gz") for n in __import__("zipfile").ZipFile(io.BytesIO(B.export_zip(out))).namelist())
    # the shop page no longer lists 5,000 products; it points to the list
    shop = (out / "shop" / "index.html").read_text()
    assert 'href="../products/">Products (5000)' in shop and shop.count('class="hs-prod"') == 0


def test_photos_are_fetched_once_and_never_from_a_private_address(site_env, monkeypatch):
    from app.site import catalog as CAT
    from app.site import service as S
    sid = _site(S, shop=False)
    calls = []

    def fetch(url):
        calls.append(url)
        if "broken" in url:
            raise CAT.CatalogError("photo 404")
        return _jpeg((10, 20, 30), (900, 600))
    monkeypatch.setattr(CAT, "_FETCH", fetch)
    monkeypatch.setattr(CAT, "start_images", lambda site_id: None)      # the test runs the photo job itself
    rows = [{"Name": "Dr. Asha Rao", "Speciality": "Child doctor", "Photo": "https://cdn.example.in/asha.jpg",
             "About": "Twenty years of caring for children in Akola, morning and evening clinic."},
            {"Name": "Dr. Ravi Jain", "Speciality": "Bones", "Photo": "https://cdn.example.in/broken.jpg",
             "About": "Bone and joint care, sports injuries and physiotherapy advice."},
            {"Name": "Dr. Mehta", "Speciality": "Eyes", "Photo": "http://insecure.example.in/x.jpg", "About": ""}]
    p = CAT.preview(T, sid, "doctors", rows, label="Our doctors")
    assert p["photos"] == 2                                       # an http photo is not fetched
    CAT.apply(T, sid, p["hash"])
    assert CAT.images(sid) == {"todo": 2, "done": 2, "ok": 1, "bad": 1, "running": False}
    assert CAT.images(sid)["todo"] == 0 and len(calls) == 2      # made once: a second run fetches nothing
    cache = CAT._img_cache(sid)
    names = sorted(x.name for x in cache.glob("c-*"))
    assert any(n.endswith("-320.avif") for n in names) and any(n.endswith("-640.webp") for n in names)
    assert not any(n.endswith("-1024.jpg") for n in names)        # never upscaled past her 900 px photo
    # the real fetcher refuses a private / non-https address before any request
    monkeypatch.setattr(CAT, "_FETCH", None)
    from app.appmaker import connect as CN
    for bad in ("http://example.in/a.jpg", "https://user:pw@example.in/a.jpg", "https://example.in:8443/a.jpg"):
        with pytest.raises(CAT.CatalogError):
            CAT._fetch(bad)
    monkeypatch.setattr(CN, "_RESOLVE", lambda host, port: [(2, 1, 6, "", ("10.0.0.5", port))])
    with pytest.raises(Exception):
        CAT._fetch("https://internal.example.in/a.jpg")


def test_dataset_and_designed_template(site_env, monkeypatch):
    """A dataset Hoola already holds becomes a list; a list with her designed page keeps that page as page 1."""
    from app import datasets as DS
    from app.site import build as B
    from app.site import catalog as CAT
    from app.site import service as S
    sid = _site(S, shop=False)
    d = DS.save(T, [{"title": f"Flat {i} in Civil Lines", "bhk": f"{1 + i % 3} BHK", "rent": str(9000 + i * 100),
                     "area": f"{600 + i * 10} sq ft, east facing, second floor, lift and parking, near the market"}
                    for i in range(120)], name="flats")
    p = CAT.preview(T, sid, "flats", CAT.from_dataset(T, d["id"]), label="Flats for rent")
    assert p["items"] == 120 and p["mapping"]["filters"] == ["bhk"] and p["mapping"]["price"] == "rent"
    CAT.apply(T, sid, p["hash"])
    r = S._load(sid)
    ctx = S._ctx(r)
    plan = json.loads(json.dumps(ctx["plan"]))
    plan["pages"].append({"slug": "flats", "title": "Flats for rent", "nav": "Flats", "sections": []})
    out = B.site_dir(r.tenant_id, r.id) / "t2"
    B.assemble({**ctx, "plan": plan}, plan, S._sections(r), {}, out, "", "")
    page1 = (out / "flats" / "index.html").read_text()
    assert page1.count('class="hs-cat-card"') == 48 and "data-hoola-catalog=" in page1
    assert (out / "flats" / "page" / "3" / "index.html").exists() and not (out / "flats" / "page" / "4").exists()
    assert "₹9,000" in (out / "flats" / "flat-0-in-civil-lines" / "index.html").read_text()
    assert CAT.price_text("123456.5") == "₹1,23,456.50" and CAT.price_text("x") == ""


def test_a_retried_checkout_is_one_order_and_parallel_ones_never_share_a_number(site_env):
    from app.site import catalog as CAT
    from app.site import service as S
    from app.site import shop as SH
    sid = _site(S)
    CAT.apply(T, sid, CAT.preview(T, sid, "products", CAT.parse_file(_csv(10, bad_rows=False)))["hash"])
    body = {**BUYER, "method": "upi", "items": [{"slug": "products/namkeen-pack-00000", "qty": 2}], "cid": "c-abc123"}
    a = S.shop_order(sid, body, ip="10.1.0.1")
    b = S.shop_order(sid, body, ip="10.1.0.2")
    assert a["number"] == b["number"] and b.get("again") is True and b["pay"]["amount"] == a["pay"]["amount"]
    assert len(SH.orders(sid)) == 1
    assert next(p for p in SH.products(sid) if p["slug"] == "products/namkeen-pack-00000")["stock"] == 23   # taken ONCE
    nums, errs = [], []

    def one(i):
        try:
            nums.append(S.shop_order(sid, {**BUYER, "method": "upi", "items": [{"slug": "products/sweets-pack-00001", "qty": 1}],
                                           "cid": f"c-par-{i}"}, ip=f"10.2.{i}.1")["number"])
        except Exception as e:                                                         # noqa: BLE001
            errs.append(e)
    ts = [threading.Thread(target=one, args=(i,)) for i in range(12)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs, errs
    assert len(set(nums)) == 12 and len(SH.orders(sid)) == 13


def test_console_panel_script_and_nginx_serve_the_twins():
    root = Path(__file__).resolve().parents[1] / "app"
    con = (root / "static/console/build.js").read_text()
    assert "async function catalogBox" in con and "/catalog/apply" in con and "/catalog/preview" in con
    js = (root / "site/assets/hoola-catalog.js").read_text()
    assert "fetch(url)" in js and "history.replaceState" in js
    from app.site import edge
    conf = edge.nginx_conf("https://hoola.ainewtika.com", enabled="/x", access="/y", ssl=False)
    assert "gzip_static on;" in conf and "stale-while-revalidate" in conf
    from app.site import checks as CK
    assert callable(CK.catalog_slugs)


@pytest.mark.skipif(__import__("os").environ.get("HOOLA_LOAD") != "1", reason="the load proof runs in CI (HOOLA_LOAD=1)")
def test_marketplace_load_proof_four_workers(site_env, monkeypatch, tmp_path):
    """THE CHECKPOINT: a 5,000-product marketplace (5 approved sellers + her own goods) built from one file, then 2,000
    visitors x 3 pages + 600 buyers (40 % on one product with 25 left, every 4th checkout sent twice at once) against 4
    server worker processes on one database. No lost order, no double order, unique numbers, stock never below 0 and
    equal to what the orders took, no server error."""
    import asyncio
    import http.server
    import os
    import socket
    import socketserver
    import subprocess
    import sys
    import httpx
    from app.site import build as B
    from app.site import catalog as CAT
    from app.site import loadtest as LT
    from app.site import service as S
    from app.site import shop as SH
    from app.site import shopplus as SPL
    monkeypatch.setattr(CAT, "start_images", lambda site_id: None)
    sid = _site(S)
    for k, nm in enumerate(["Amul Store", "Haldiram Point", "Bikaji Mart", "Parle Depot", "MTR Corner"]):
        SPL.apply_vendor(sid, {"name": nm, "phone": f"98765000{k:02d}"}, ip=f"10.9.9.{k}")
    for v in SPL.vendors(T, sid)["vendors"]:
        SPL.set_vendor(T, sid, v["id"], {"status": "approved", "commission": 10})
    raw = _csv(5000, bad_rows=False).decode().splitlines()
    sellers = ["Amul Store", "Haldiram Point", "Bikaji Mart", "Parle Depot", "MTR Corner", ""]
    rows = [raw[0] + ",Seller"] + [ln + "," + sellers[i % 6] for i, ln in enumerate(raw[1:])]
    p = CAT.preview(T, sid, "products", CAT.parse_file("\n".join(rows).encode()), label="Products")
    a = CAT.apply(T, sid, p["hash"])
    assert a["live"] == 5000 and a["shop"]["sellers"]["linked"] == 4167
    r = S._load(sid)
    ctx = S._ctx(r)
    out = tmp_path / "site"
    t0 = time.time()
    B.assemble(ctx, ctx["plan"], S._sections(r), {}, out, "https://bazaar.example.in", S.form_endpoint(r))
    build_s = time.time() - t0
    before = {x["slug"]: x["stock"] for x in SH.products(sid)}
    hot = "products/tea-pack-00004"

    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    class Static(socketserver.ThreadingTCPServer):      # the test's stand-in for Caddy / nginx (Python's default queue is 5)
        allow_reuse_address, daemon_threads, request_queue_size = True, True, 1024
    static = Static(("127.0.0.1", 0), lambda *a, **k: Q(*a, directory=str(out), **k))
    threading.Thread(target=static.serve_forever, daemon=True).start()
    s_ = socket.socket()
    s_.bind(("127.0.0.1", 0))
    port = s_.getsockname()[1]
    s_.close()
    envv = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "WORKER_TICK_SECONDS": "3600",
            "SITE_SHOP_IP_CAP": "100000", "SITE_SHOP_DAY_CAP": "100000"}
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
                            "--workers", os.environ.get("HOOLA_LOAD_WORKERS", "4"), "--log-level", "warning"], env=envv)
    try:
        for _ in range(120):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        idx = json.loads((out / "assets" / "catalog" / "products.json").read_text())
        paths = ["/products/", "/products/page/7/", "/assets/catalog/products.json"] + [f"/products/{it[0]}/" for it in idx["items"][:400]]
        res = asyncio.run(LT.run(f"http://127.0.0.1:{static.server_address[1]}", f"http://127.0.0.1:{port}/api/site-shop/{sid}",
                                 paths, [x for x in before if x.startswith("products/")], hot=hot,
                                 visitors=int(os.environ.get("HOOLA_LOAD_VISITORS", "2000")),
                                 buyers=int(os.environ.get("HOOLA_LOAD_BUYERS", "600"))))
    finally:
        srv.terminate()
        srv.wait(timeout=60)
        static.shutdown()
    v = LT.verify(sid, before, res)
    print(json.dumps({"build_seconds": round(build_s, 1), **{k: x for k, x in res.items() if k != "accepted"}, **v}, indent=1))
    assert v["passed"], v["problems"]
    assert res["page_codes"].get(200) == res["page_views"]
    hot_orders = sum(1 for nums in res["accepted"].values() if nums) and v["orders"]
    assert hot_orders and next(x for x in SH.products(sid) if x["slug"] == hot)["stock"] == 0     # the hot one sold out exactly
    assert v["orders"] == v["accepted"] and v["sold_out_refusals"] > 0
    assert not res["no_answer"], res["no_answer"]                     # every checkout answered (none timed out)
