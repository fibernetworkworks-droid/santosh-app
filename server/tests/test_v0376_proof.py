"""v0.376 PROOF (web design Phase 9, owner: "START PHASE 5"): a 100-page website as numbers, read the same way for Hoola
and for any rival builder - pages built vs planned, broken links and missing files over every page, the judge on a
sample of page types, features verified in the files, rupees and minutes per page; a rival's public site crawled in
Chromium (robots.txt respected, one host, public internet only) and compared side by side."""
import json
import time
from urllib.robotparser import RobotFileParser

import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_the_five_businesses_are_fixed():
    from app.site import proof as PR
    a, b = PR.big_set(), PR.big_set()
    assert a == b and [x["id"] for x in a] == ["big-hospital", "big-coaching", "big-mithai", "big-realestate", "big-isp"]
    for x in a:
        assert x["pages"] == 100 and len(x["brief"]) <= 2000 and len(x["facts"]["lists"]) <= 5500 and x["features"]
        assert "100 page" in x["brief"] and x["facts"]["name"] == x["name"]
    mithai = PR.brief("big-mithai")
    assert "shop" in mithai["features"] and "Kaju Katli ₹" in mithai["facts"]["lists"] and mithai["facts"]["lists"].count("₹") == 60
    assert len(PR.brief("big-isp")["lists"]["service areas"]) == 40
    with pytest.raises(ValueError):
        PR.brief("nope")


def _built(S):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def test_the_card_is_read_from_the_files(site_env):
    from app.site import build as B
    from app.site import proof as PR
    from app.site import service as S
    sid = _built(S)
    S.shop_setup(T, sid, {"on": True, "cod": True}, [{"title": "Kaju Katli", "price": "900", "unit": "1 kg"}])
    S.blog_publish(T, sid, {"title": "Diwali tips", "body": "Mithai lene se pehle teen baatein. " * 20, "meta": {}})
    judged = []
    c = PR.card(sid, 123.0, 30.0, ["note"], judge_fn=lambda shots: judged.append(len(shots)) or {"overall": 7.5})
    assert c["status"] == "ready" and c["built_pages"] >= 5 and c["broken_links"] == 0 and c["missing_files"] == 0
    assert c["features"]["shop"] and c["features"]["blog"] and c["features"]["rss"] and c["features"]["blog_posts"] == 1
    assert not c["features"]["web_app"] and c["features"]["sitemap_urls"] == 0                     # preview: no address yet
    assert c["inr"] == 123.0 and c["inr_per_page"] == round(123.0 / c["built_pages"], 2) and c["notes"] == ["note"]
    assert c["readable_without_js_pct"] == 100.0 and c["one_h1_pct"] >= 80 and c["kb_median"] > 0
    if judged:                                                     # the checks shot pages: the judge saw several kinds
        assert c["judge"] == 7.5 and "home" in c["judge_pages"]
    # a missing picture and a dead link are found on any page
    out = B.out_dir(T, sid, S.get(T, sid)["version"])
    page = out / "contact" / "index.html"
    page.write_text(page.read_text().replace("</main>", '<img src="../assets/img/gone.jpg" alt=""><a href="../nowhere/">x</a></main>'))
    c2 = PR.card(sid, 0, 0, [], judge_fn=lambda s: None)
    assert c2["missing_files"] == 1 and c2["missing"][0]["file"] == "../assets/img/gone.jpg" and c2["broken_links"] >= 1


def test_a_proof_run_end_to_end_with_its_own_builder(site_env, monkeypatch):
    from app.site import proof as PR
    from app.site import service as S
    sid = _built(S)
    monkeypatch.setattr(PR, "_judge_pages", lambda site_id, n=5, judge_fn=None: {"median": 6.8, "pages": {"home": 6.8}})
    seen = []

    def builder(pid, b, budget):
        seen.append((b["id"], budget))
        return sid, 640.0, 75.0, []
    out = PR.start("big-coaching", 99999, builder=builder)
    assert out["budget_inr"] <= 3000 and "100-page proof shuru" in out["say"]
    for _ in range(200):
        if PR.get(out["proof"])["status"] != "running":
            break
        time.sleep(0.2)
    p = PR.get(out["proof"])
    assert p["status"] == "done" and p["name"] == "Vidyapeeth Classes" and seen == [("big-coaching", out["budget_inr"])]
    assert p["card"]["judge"] == 6.8 and p["card"]["minutes"] == 75.0 and p["card"]["built_pages"] > 0
    assert any(x["proof"] == out["proof"] for x in PR.proofs())


def test_the_real_builder_like_an_owner(site_env, monkeypatch):
    """build_big itself (the real flow: site map -> plan -> looks -> build -> shop from her priced list -> blog), smaller."""
    from app.db import session
    from app.site import ai as AI
    from app.site import proof as PR
    from app.site import service as S
    from tests.test_v0315_badi_website import BigFake, _sitemap_raw
    raw = _sitemap_raw()
    for i, it in enumerate(raw["collections"][0]["items"]):
        it["data"]["price"] = f"₹{400 + 20 * i}"                                  # her priced list -> shop products
    monkeypatch.setattr(AI, "ask_json", BigFake(site_env, raw))
    b = dict(PR.brief("big-mithai"))
    b["pages"], b["features"] = 60, ["shop", "blog"]
    b["brief"] = b["brief"].replace("100 page", "60 page")
    b["posts"] = b["posts"][:1]
    with session() as s:
        p = PR.ArenaProof(kind="hoola", brief_id=b["id"])
        s.add(p)
        s.flush()
        pid = p.id
    sid, inr, minutes, notes = PR.build_big(pid, b, 5000)
    r = S._load(sid)
    assert r.tenant_id == PR.TENANT and r.status == "ready", (r.status, notes)
    assert S._j(r.plan, {}).get("big") and notes == []
    c = PR.card(sid, inr, minutes, notes, judge_fn=lambda s: {"overall": 7.0})
    assert c["built_pages"] >= 50 and c["broken_links"] == 0 and c["missing_files"] == 0, (c["broken"], c["missing"])
    assert c["features"]["blog"] and c["features"]["blog_posts"] == 1
    assert c["features"]["shop"] and len(S.shop_info(PR.TENANT, sid)["products"]) >= 40     # from her priced list
    assert PR.get(pid)["site"] == sid


class _Resp:
    def __init__(self, code, text, ctype="text/html"):
        self.status_code, self.text, self.headers = code, text, {"content-type": ctype}


def test_a_rival_is_crawled_and_measured_the_same_way(monkeypatch):
    from app import web as WB
    from app.site import proof as PR
    monkeypatch.setattr(WB, "_public_host", lambda host: None)                 # the test host is not on the internet
    rp = RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /private"])
    monkeypatch.setattr(PR, "_robots", lambda url: rp)
    site = {"https://rival.example/": ("<html><body><div id=root></div></body></html>", 200),                    # a JS app
            "https://rival.example/about": ("<html><body>" + "words " * 80 + "</body></html>", 200),
            "https://rival.example/gone": ("", 404),
            "https://rival.example/sitemap.xml": ("<urlset><url><loc>a</loc></url><url><loc>b</loc></url></urlset>", 200)}
    rendered = {"https://rival.example/": {"links": ["/about", "/gone", "/private/x", "https://other.example/", "mailto:a@b.c",
                                                     "/logo.png", "#top"], "title": "Rival", "desc": "d", "h1": 1, "text": 300,
                                           "ld": ["Organization"], "hreflang": 0, "kb": 2.0},
                "https://rival.example/about": {"links": ["/"], "title": "Rival", "desc": "", "h1": 2, "text": 120, "ld": [],
                                                "hreflang": 0, "kb": 3.0}}
    raw_get = lambda u: _Resp(site.get(u, ("", 404))[1], site.get(u, ("", 404))[0])
    c = PR.crawl("https://rival.example/", render=lambda u: rendered[u], raw_get=raw_get)
    urls = [p["url"] for p in c["pages"]]
    assert urls == ["https://rival.example/", "https://rival.example/about"] and c["sitemap_urls"] == 2
    assert c["broken"] == [{"url": "https://rival.example/gone", "status": 404}]               # private/ never fetched
    card = PR.rival_card(c, [[b"a"], [b"b"]], judge_fn=lambda s: {"overall": 6.0})
    assert card["built_pages"] == 2 and card["broken_links"] == 1 and card["judge"] == 6.0
    assert card["readable_without_js_pct"] == 50.0 and card["unique_titles_pct"] == 50.0 and card["one_h1_pct"] == 50.0
    assert card["json_ld_pct"] == 50.0 and card["description_pct"] == 50.0
    # the same card stored as a rival proof (background=False in tests), then side by side with a Hoola card
    out = PR.rival("big-mithai", "Lovable", "https://rival.example/", crawl_fn=lambda u: c, shots_fn=lambda u: [b"x"],
                   judge_fn=lambda s: {"overall": 6.0}, background=False)
    r = PR.get(out["proof"])
    assert r["status"] == "done" and r["kind"] == "rival" and r["builder"] == "lovable" and r["card"]["built_pages"] == 2
    hoola = {"built_pages": 104, "broken_links": 0, "judge": 7.4, "readable_without_js_pct": 100.0, "kb_median": 30.0}
    cmp_ = PR.compare(hoola, r["card"])
    m = cmp_["metrics"]
    assert m["built_pages"]["better"] == "a" and m["broken_links"]["better"] == "a" and m["judge"]["better"] == "a"
    assert m["kb_median"]["better"] == "b" and m["inr_per_page"]["better"] == ""                 # lower wins; missing = no call
    assert cmp_["wins"]["a"] >= 4


def test_owner_only_endpoints_and_console(site_env):
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.main import app, current_tenant
    c = TestClient(app)
    d = c.get("/api/arena/proofs").json()
    assert len(d["briefs"]) == 5 and d["max_inr"] > 0
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        assert c.get("/api/arena/proofs").status_code == 403
        assert c.post("/api/arena/proofs", json={"brief_id": "big-isp"}).status_code == 403
        assert c.post("/api/arena/proofs/rival", json={"brief_id": "big-isp", "url": "https://x.example"}).status_code == 403
    finally:
        app.dependency_overrides.pop(current_tenant, None)
    assert c.post("/api/arena/proofs/rival", json={"brief_id": "big-isp", "builder": "x", "url": "http://127.0.0.1/"}).status_code == 400
    con = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js = (con / "arena.js").read_text()
    assert "function proofTile" in js and "/api/arena/proofs/compare" in js and "pfRival" in js
    css = (con / "v2.css").read_text()
    assert css.index(".ar-proof .grid2") < css.index("/* ===== v0.288 SIDEBAR FULLY VISIBLE")


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.489.0"
    assert "0.489.0+533" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
