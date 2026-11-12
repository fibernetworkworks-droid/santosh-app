"""v0.623 KOI PATA NA KHOYE (from the ai-website-cloner-template read, docs/research/website_cloner/00_READ.md) - only for
HER OWN old site, ownership already proved by v0.567:

1. every old address (sitemap + same-site links) is kept; each is matched to a new page; nothing is served until her tap
   (hash-bound); then a missing old address answers 301 to its new page (Python serving + nginx's own 404 hand-off);
2. "keep my look": her old page list and each page's section order ride into look 1's brief;
3. her old page next to the new one at the same width, the differences listed;
4. imported photos checked by their BYTES (a .png that is really JPEG is named; a web page posing as a photo is left out)."""
import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0567_koi_bhi_design import _old_site, public_dns  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)
from tests.test_v122_hosting import host_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.841.0"


def _jpeg(size=(800, 600)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, "#336699").save(b, "JPEG")
    return b.getvalue()


def test_old_addresses_are_normalised_filtered_and_matched():
    from app.site import moved as MV
    assert MV.norm_path("https://x.in/About-Us/?a=1#t") == "/About-Us" and MV.norm_path("//") == "/"
    kept = MV.keep_paths(["/", "/about-us.html", "/about-us.html/", "/wp-admin/x", "/brochure.pdf", "/contact.php",
                          "/feed", "/services/catering"], {"/contact.php": "Contact Us"})
    assert [k["path"] for k in kept] == ["/about-us.html", "/contact.php", "/services/catering"]
    assert kept[1]["title"] == "Contact Us"
    pages, maps = MV.sitemap_paths("<urlset><url><loc>https://www.sharma.in/a?x=1</loc></url>"
                                   "<url><loc>https://evil.example/b</loc></url><sitemap><loc>https://sharma.in/s2.xml</loc>"
                                   "</sitemap></urlset>", lambda h: h.endswith("sharma.in"))
    assert pages == ["/a"] and maps == ["https://sharma.in/s2.xml"]
    new = [{"slug": "home", "title": "Home", "path": "/"}, {"slug": "about", "title": "About us", "path": "/about/"},
           {"slug": "contact", "title": "Contact", "path": "/contact/"},
           {"slug": "catering", "title": "Catering services", "path": "/catering/"}]
    assert MV.match({"path": "/services/catering"}, new)["new"] == "/catering/"          # same name, deeper
    assert MV.match({"path": "/our-story.html", "title": ""}, new)["new"] == "/about/"   # story = about
    assert MV.match({"path": "/reach-us.php", "title": "Find us"}, new)["new"] == "/contact/"
    g = MV.match({"path": "/xyz-2019-sale", "title": ""}, new)
    assert g["new"] == "/" and g["guess"]                                               # never silent: flagged


def test_a_photo_is_checked_by_its_bytes():
    from app.site import moved as MV
    j = MV.sniff(_jpeg(), "https://sharma.in/img/shop.png")
    assert j["ok"] and j["type"] == "jpeg" and j["named"] == "png" and "really JPEG" in j["why"] and j["w"] == 800
    h = MV.sniff(b"<!DOCTYPE html><html>login</html>", "https://sharma.in/img/a.jpg")
    assert not h["ok"] and h["type"] == "html" and "web page" in h["why"]
    assert not MV.sniff(b"\xff\xd8\xff garbage")["ok"]                                  # looks like JPEG, will not open
    assert not MV.sniff(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')["ok"]


def _richer_site(token):
    handler, fetched = _old_site(token)
    jpg = _jpeg((900, 700))

    def h2(req):
        p = req.url.path
        if p == "/sitemap.xml":
            return httpx.Response(200, text="<urlset><url><loc>https://sharmasweets.in/old-menu.html</loc></url>"
                                            "<url><loc>https://sharmasweets.in/contact-us.php</loc></url></urlset>")
        if p == "/img/shop.jpg":                       # the page is changed below to add a lying picture too
            return handler(req)
        if p == "/img/fake.png":
            return httpx.Response(200, text="<!doctype html><html>not found</html>", headers={"content-type": "image/png"})
        if p == "/img/real.png":
            return httpx.Response(200, content=jpg, headers={"content-type": "text/plain"})
        r = handler(req)
        if p == "/" and r.status_code == 200:
            t = r.text.replace("</body>", '<img src="/img/fake.png" alt="x"><img src="/img/real.png" alt="Counter"></body>')
            return httpx.Response(200, text=t, headers={"content-type": "text/html; charset=utf-8"})
        return r
    return h2, fetched


def test_import_keeps_old_addresses_layout_and_checked_photos(site_env, public_dns):
    from app.site import inspire as IN
    from app.site import moved as MV
    from app.site import service as S
    h, fetched = _richer_site(IN.own_token(T, "sharmasweets.in"))
    IN.set_transport(httpx.MockTransport(h))
    try:
        pv = IN.read(T, "site", "https://sharmasweets.in")
    finally:
        IN.set_transport(None)
    ref = pv["ref"]
    paths = [x["path"] for x in ref["old_site"]["paths"]]
    assert {"/about", "/sweets", "/old-menu.html", "/contact-us.php"} <= set(paths)
    assert "/private/admin" not in paths and not any("other.example" in p for p in paths)
    assert "/private/admin" not in fetched                                              # robots still respected
    checks = {c["src"].rsplit("/", 1)[-1]: c for c in ref["photo_checks"]}
    assert not checks["fake.png"]["ok"] and checks["fake.png"]["type"] == "html"
    assert checks["real.png"]["ok"] and checks["real.png"]["type"] == "jpeg" and "really JPEG" in checks["real.png"]["why"]
    assert not checks["icon-cart.png"]["ok"] if "icon-cart.png" in checks else True
    assert "purane pate" in pv["say"] and "left out after checking their bytes" in ref["read_by"]
    lay = {x["path"]: x for x in ref["layout"]}
    assert lay["/"]["sections"] is not None and "/about" in lay
    # her tap with keep: the layout rides into look 1, the old addresses wait beside the site
    out = IN.use(T, pv["token"], keep=True)
    assert out["keep"] and out["old_addresses"] == len(paths) and "purane pate jodo" in out["say"]
    f = json.loads(S._load(out["site"]).facts)
    assert f["design_ref"]["keep"] and f["design_ref"]["layout"][0]["path"] == "/"
    note = IN.brief_note(f["design_ref"])
    assert "KEEP HER LAYOUT" in note and "/about" in note and "Hoola's kit" in note
    assert "KEEP HER LAYOUT" not in IN.brief_note({**f["design_ref"], "keep": False})
    assert MV._load(T, out["site"], "moves_src.json")["host"] == "sharmasweets.in"


def test_keep_is_only_for_her_own_site(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import inspire as IN
    from tests.test_v0567_koi_bhi_design import _png
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: {"style": "luxury_dark", "head_kind": "serif", "radius_px": 2,
                                                         "sections": ["hero"], "notes": "x"})
    pv = IN.read(T, "screenshot", data=_png([("#0B0B0E", 0.8), ("#C9A227", 0.2)]))
    with pytest.raises(Exception):
        IN.use(T, pv["token"], keep=True)                    # no brief: a screenshot gives no words (unchanged rule)
    out = IN.use(T, pv["token"], brief="Gold jewellery shop in Akola", keep=True)
    assert out["keep"] is False and out["old_addresses"] == 0


def test_her_tap_then_old_addresses_answer_301(host_env):
    from tests import test_v122_hosting as HV
    if True:
        from app.main import app
        from app.site import edge as E
        from app.site import hosting as H
        from app.site import moved as MV
        c = TestClient(app)
        g, _ = HV._ready_site()
        sid = g["id"]
        with pytest.raises(MV.MovedError):
            MV.propose(T, sid)                                                   # no old site: nothing to propose
        MV.save_source(T, sid, "sharmasweets.in", MV.keep_paths(
            ["/contact-us.php", "/contact", "/xyz-old-offer", "/privacy-policy.html"], {"/contact-us.php": "Contact Us"}))
        p = c.get(f"/api/sites/{sid}/moves").json()
        rows = {r["old"]: r for r in p["rows"]}
        assert "/contact" not in rows                                            # same address on the new site: nothing to do
        assert rows["/contact-us.php"]["new"] == "/contact/" and rows["/xyz-old-offer"]["guess"]
        assert p["hash"] and p["guesses"] == 1 and not p["approved"]
        card = H.launch_request(T, sid)
        H.launch(T, sid, card["hash"])
        host = "sharma-sweets.hoolasites.in"
        assert c.get("/contact-us.php", headers={"host": host}, follow_redirects=False).status_code == 404  # not before her tap
        assert c.post(f"/api/sites/{sid}/moves", json={"hash": "nope"}).status_code == 409
        ok = c.post(f"/api/sites/{sid}/moves", json={"hash": p["hash"], "drop": ["/xyz-old-offer"]}).json()
        assert ok["ok"] and ok["redirects"] == len(p["rows"]) - 1 and ok["live_addresses"] == 1
        r = c.get("/contact-us.php", headers={"host": host}, follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"] == f"https://{host}/contact/"
        r = c.get("/Contact-Us.php/", headers={"host": host}, follow_redirects=False)
        assert r.status_code == 301                                              # case / trailing slash forgiven
        assert c.get("/xyz-old-offer", headers={"host": host}, follow_redirects=False).status_code == 404   # she unticked it
        assert c.get("/_redirects.json", headers={"host": host}).status_code == 404                        # never served
        assert c.get("/", headers={"host": host}).status_code == 200
        # nginx hands its own 404s over; that request is not counted twice
        r = c.get("/contact-us.php", headers={"host": host, "x-hoola-edge": "1"}, follow_redirects=False)
        assert r.status_code == 301
        # a later publish carries the map
        card = H.launch_request(T, sid)
        H.launch(T, sid, card["hash"])
        assert c.get("/contact-us.php", headers={"host": host}, follow_redirects=False).status_code == 301
        conf = E.nginx_conf(base_url="https://api.hoola.example", enabled="/srv/en", access="/srv/a.log")
        assert "@hoola_moved" in conf and "location = /_redirects.json" in conf and "X-Hoola-Edge 1" in conf
        assert "try_files $uri $uri/index.html @hoola_moved;" in conf


def test_old_page_next_to_the_new_one(site_env):
    from app.site import moved as MV
    from app.site import service as S
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    MV.save_source(T, v["id"], "sharmasweets.in", [{"path": "/about", "title": "About"}])
    old = ("<html><body><h1>Fresh mithai since 1962</h1><h2>Wedding orders</h2><a href='tel:+919999988888'>Call</a>"
           "<form><input name=a></form><form><input name=b></form>" + "<img src=x>" * 8 + "</body></html>")
    seen = {}

    def shooter(url, out, slug, widths):
        seen.update(url=url, slug=slug, widths=widths)
        from PIL import Image
        a, b = io.BytesIO(), io.BytesIO()
        Image.new("L", (390, 800), 255).save(a, "PNG")
        Image.new("L", (390, 800), 0).save(b, "PNG")
        return {"390": (a.getvalue(), b.getvalue())}
    rep = MV.compare(T, v["id"], "/", fetch=lambda u: old, shooter=shooter)
    assert seen["url"] == "https://sharmasweets.in/" and seen["slug"] == "home"
    assert any("9999988888" in d for d in rep["differences"]) and any("Wedding orders" in d for d in rep["differences"])
    assert rep["widths"][0]["width"] == 390 and rep["widths"][0]["looks_different"] == 1.0
    assert MV.compare_file(T, v["id"], rep["widths"][0]["old"]).startswith(b"\x89PNG")
    with pytest.raises(MV.MovedError):
        MV.compare_file(T, v["id"], "../../etc/passwd")
    # no browser: still the words comparison, said plainly
    rep2 = MV.compare(T, v["id"], "/", fetch=lambda u: old, shooter=lambda *a: (_ for _ in ()).throw(RuntimeError("no chromium")))
    assert rep2["widths"] == [] and "no browser" in rep2["note"] and rep2["differences"]
    # only HER old site: the address is always built from the proved host
    assert MV.compare(T, v["id"], "https://evil.example/x", fetch=lambda u: seen.update(last=u) or old,
                      shooter=shooter)["old"] == "https://sharmasweets.in/x"


def test_tool_actions_and_her_tap(site_env):
    import asyncio
    from app.agent.site_tools import SITE_HANDLERS, SITE_TOOLS, _TAP_LIKE
    from app.site import moved as MV
    from app.site import service as S
    from tests.test_life import conv_ctx
    assert "moves_ok" in _TAP_LIKE
    enum = next(t for t in SITE_TOOLS if t["name"] == "website")["input_schema"]["properties"]["action"]["enum"]
    assert {"moves", "moves_ok", "compare_old"} <= set(enum)
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    MV.save_source(T, v["id"], "sharmasweets.in", [{"path": "/contact-us.php", "title": "Contact"}])
    ctx = conv_ctx()
    got = asyncio.run(SITE_HANDLERS["website"](ctx, "moves", site=v["id"]))
    assert got["total"] == 1 and got["hash"] and "haan" in got["say"]
    done = asyncio.run(SITE_HANDLERS["website"](ctx, "moves_ok", site=v["id"], hash=got["hash"]))
    assert done["ok"] and done["redirects"] == 1 and done["live_addresses"] == 0
