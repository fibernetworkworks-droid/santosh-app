"""v0.103 SEO Sahayak: crawl of her own site (robots.txt honoured, same host), on-page + site issues, fix list that learns
(fixed on re-crawl), Core Web Vitals from PageSpeed, Search Console numbers + opportunities + cannibalisation (official API,
read-only), keyword plan, page brief, LocalBusiness schema, Business Profile post / review reply drafts that wait for her
Haan, report, weekly note, tools + API."""
import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)
HOME = """<html lang="en"><head><title>Sharma Dental</title><meta name="viewport" content="width=device-width">
<script type="application/ld+json">{"@type": "WebSite"}</script></head>
<body><h1>Welcome</h1><p>We fix teeth.</p><img src="a.jpg"><a href="/services">Services</a> <a href="/contact">Contact</a>
<a href="/private/x">x</a> <a href="https://other.example/">out</a></body></html>"""
SERVICES = ("<html lang='en'><head><title>Root Canal and Implants in Akola | Sharma Dental</title>"
            "<meta name='description' content='Painless root canal, implants and braces in Akola. Same day appointments, fair prices. Call Sharma Dental today.'>"
            "<meta name='viewport' content='width=device-width'></head><body><h1>Root canal in Akola</h1>"
            + "<p>" + "painless treatment explained in simple steps " * 60 + "</p></body></html>")
CONTACT = "<html><head><title>Sharma Dental</title><meta name='robots' content='noindex'></head><body><h1>Contact</h1></body></html>"
STATE = {"home": HOME}


def gsc_rows(body):
    dims = body["dimensions"]
    cur = body["startDate"] >= "2026-09-22"
    if dims == ["date"]:
        return [{"keys": ["d"], "clicks": 60 if cur else 100, "impressions": 3000 if cur else 2500, "ctr": .02, "position": 9.0}]
    return [
        {"keys": ["dentist in akola", "https://shop.example/"], "clicks": 20, "impressions": 900, "ctr": .022, "position": 6.4},
        {"keys": ["root canal cost akola", "https://shop.example/services"], "clicks": 3, "impressions": 300, "ctr": .01, "position": 2.1},
        {"keys": ["dentist in akola", "https://shop.example/services"], "clicks": 1, "impressions": 80, "ctr": .0125, "position": 14.0},
        {"keys": ["what is the best way to stop tooth pain at night at home", "https://shop.example/services"],
         "clicks": 0, "impressions": 40, "ctr": 0, "position": 25.0},
    ]


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    if u.startswith("https://www.googleapis.com/pagespeedonline"):
        return httpx.Response(200, json={
            "loadingExperience": {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 4300},
                                              "INTERACTION_TO_NEXT_PAINT": {"percentile": 180},
                                              "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 15}}},
            "lighthouseResult": {"categories": {"performance": {"score": .42}},
                                 "audits": {"img": {"title": "Properly size images", "details": {"type": "opportunity", "overallSavingsMs": 2100}},
                                            "x": {"title": "tiny", "details": {"type": "opportunity", "overallSavingsMs": 50}}}}})
    if u.startswith("https://www.googleapis.com/webmasters/v3/sites/") and req.method == "POST":
        return httpx.Response(200, json={"rows": gsc_rows(json.loads(req.content))})
    if u == "https://www.googleapis.com/webmasters/v3/sites":
        return httpx.Response(200, json={"siteEntry": [{"siteUrl": "sc-domain:shop.example", "permissionLevel": "siteOwner"}]})
    if u.startswith("https://shop.example"):
        path = req.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\nSitemap: https://shop.example/sitemap.xml\n")
        if path == "/sitemap.xml":
            return httpx.Response(200, text="<urlset><url><loc>https://shop.example/services</loc></url><url><loc>https://shop.example/old</loc></url></urlset>")
        if path == "/":
            return httpx.Response(200, text=STATE["home"], headers={"content-type": "text/html; charset=utf-8"})
        if path == "/services":
            return httpx.Response(200, text=SERVICES)
        if path == "/contact":
            return httpx.Response(200, text=CONTACT)
        if path == "/old":
            return httpx.Response(301, headers={"location": "/services"})
        return httpx.Response(404, text="nope")
    return httpx.Response(500, text="unexpected " + u)


@pytest.fixture
def seo(env, monkeypatch):
    from app.seo import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    monkeypatch.setattr(S, "_safe", lambda u: u if "://" in u else "https://" + u)
    S.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    STATE["home"] = HOME
    yield S
    S.set_http(None)


def site(S):
    return S.save_site(T, "shop.example", "Sharma Dental", city="Akola", phone="9822000000", street="Station Road", pin="444001",
                       schema_type="Dentist", hours="Mo-Sa 10:00-20:00", services=["Root canal", "Dental implants"])


def test_rules():
    from app.seo import rules as R
    assert R.cwv_grade("lcp", 2400) == "good" and R.cwv_grade("inp", 300) == "ni" and R.cwv_grade("cls", .3) == "poor"
    assert R.intent("dentist near me") == "local" and R.intent("root canal price akola") == "transactional"
    assert R.intent("best dentist in akola") == "commercial" and R.intent("daant dard kaise roke") == "informational"
    o = R.opportunity({"query": "q", "page": "p", "clicks": 2, "impressions": 500, "ctr": .004, "position": 8})
    assert o["kind"] == "striking" and o["gain"] > 0
    assert R.opportunity({"query": "q", "page": "p", "clicks": 1, "impressions": 500, "ctr": .002, "position": 2})["kind"] == "low_ctr"
    assert R.opportunity({"query": "q", "page": "p", "clicks": 0, "impressions": 5, "ctr": 0, "position": 8}) is None
    sc = R.local_schema({"name": "A", "phone": "1", "city": "Akola", "pin": "444001", "schema_type": "Dentist"})
    assert '"@type": "Dentist"' in sc and '"addressCountry": "IN"' in sc
    assert len(R.title_suggestion("Root Canal Treatment", "Akola", "Sharma Dental")) <= 60
    assert R.site_issues([], "User-agent: *\nDisallow: /\n", True)[0]["code"] == "robots_block"


def test_audit_learns(seo):
    S = seo
    assert site(S)["site"]["url"] == "https://shop.example/"
    r = S.crawl(T)
    assert r["pages"] == 3 and r["sitemap"] and r["blocked"] == ["https://shop.example/private/x"], r
    ts = S.tasks(T)
    codes = {(t["code"], t["url"].rstrip("/").rsplit("/", 1)[-1]) for t in ts}
    assert ("title_short", "shop.example") in codes and ("city", "shop.example") in codes and ("schema", "shop.example") in codes
    assert ("noindex", "contact") in codes and ("img_alt", "shop.example") in codes
    assert ("dup_title", "shop.example") in codes
    assert not any(t["url"].endswith("/services") and t["level"] != "info" for t in ts)
    assert all("private" not in p["url"] for p in S.pages(T))
    assert 0 < r["score"] < 100
    STATE["home"] = HOME.replace("<title>Sharma Dental</title>", "<title>Best Dentist in Akola | Sharma Dental Clinic</title>")
    t = next(x for x in ts if x["code"] == "img_alt")
    S.close_task(T, t["id"], "ignored")
    r2 = S.crawl(T)
    assert r2["fixed"] >= 2 and not any(x["code"] == "title_short" and x["url"] == "https://shop.example/" for x in S.tasks(T))
    assert any(x["code"] == "img_alt" for x in S.tasks(T, status="ignored"))
    with pytest.raises(S.SeoError):
        S.close_task(T, t["id"], "bogus")


def test_speed_gsc(seo, monkeypatch):
    S = seo
    from app.config import get_settings
    monkeypatch.setenv("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")
    get_settings.cache_clear()
    from app import accounts as acc
    from app.db import now, session
    site(S)
    ps = S.pagespeed(T)
    assert ps["grades"] == {"lcp": "poor", "inp": "good", "cls": "ni"} and ps["cls"] == .15 and ps["lab_score"] == 42
    assert ps["fixes"] == [{"title": "Properly size images", "save_ms": 2100}] and "kharab" in ps["say"]
    with pytest.raises(S.SeoError):
        S.performance(T)
    with session() as s:
        s.add(S.SeoGoogle(tenant_id=T, address="m@x.in", access_token_enc=acc.encrypt("tok"), refresh_token_enc=acc.encrypt("r"),
                          expiry=now() + timedelta(hours=1)))
    p = S.performance(T)
    assert p["property"] == "sc-domain:shop.example" and p["current"]["clicks"] == 60 and p["change"]["clicks"] == -40
    assert p["end"] == "2026-10-19" and p["long_queries"] == 1
    kinds = {(o["kind"], o["query"]) for o in p["opportunities"]}
    assert ("striking", "dentist in akola") in kinds and ("low_ctr", "root canal cost akola") in kinds
    assert p["cannibal"][0]["query"] == "dentist in akola"
    assert p["intent_mix"]["transactional"] == 300
    kp = S.keyword_plan(T)
    hit = next(k for k in kp["keywords"] if k["keyword"] == "root canal in akola")
    assert hit["position"] == 2.1 and len(kp["keywords"]) == 8
    assert S.summary(T)["stats"][0]["clicks"] == 60
    assert S.report_file(T)["file"]["name"].endswith(".xlsx")
    get_settings.cache_clear()


def test_drafts_haan(seo):
    S = seo
    site(S)
    S.crawl(T)
    b = S.content_brief(T, "root canal price in akola")
    assert "Root Canal" in b["text"] and "FAQ" in b["text"] and "/services" in b["text"]
    sc = S.schema_draft(T)
    assert "Station Road" in sc["text"] and "Dentist" in sc["text"]
    g = S.gbp_post(T, "Free dental check-up camp this Sunday", "first 50 patients")
    assert "9822000000" in g["text"]
    rr = S.review_reply(T, "waited 2 hours", 1, "Ravi Kumar")
    assert "Ravi ji" in rr["text"] and "9822000000" in rr["text"]
    assert "shukriya" in S.review_reply(T, "great", 5)["text"]
    assert {d["status"] for d in S.drafts(T)} == {"ready"}
    ok = S.approve_draft(T, rr["draft_id"], "Edited reply")
    assert ok["text"] == "Edited reply" and "khud publish nahi" in ok["say"]
    with pytest.raises(S.SeoError):
        S.content_brief(T, " ")
    assert S.send_morning(T)["text"].startswith("SEO:")


def test_tools_api(seo):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("seo") == "seo_work" and roles.kind_of("seo_dekho") == "read" and "seo" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["seo_agency"]["role"] == "seo_specialist"
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    run("seo", action="site", url="https://shop.example", name="Sharma Dental", city="Akola", services=["Root canal"])
    assert run("seo", action="audit")["pages"] == 3
    assert run("seo_dekho", what="rules")["never"]
    d = run("seo", action="review_reply", review="good", stars=4)
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["seo"](staff, action="approve", draft_id=d["draft_id"]))
    with TestClient(main.app) as cl:
        assert "seo" in cl.get("/healthz").json()["features"]
        sm = cl.get("/api/seo/summary").json()
        assert sm["site"]["url"] == "https://shop.example/" and sm["open_tasks"] > 0 and sm["gsc"]["connected"] is False
        tid = cl.get("/api/seo/tasks").json()["tasks"][0]["id"]
        assert cl.post(f"/api/seo/tasks/{tid}", json={"status": "done"}).status_code == 200
        assert cl.post("/api/seo/speed", json={}).json()["lab_score"] == 42
        assert cl.post("/api/seo/schema", json={}).status_code == 200
        dr = cl.get("/api/seo/drafts").json()["drafts"]
        assert cl.post(f"/api/seo/drafts/{dr[0]['id']}", json={}).status_code == 200
        assert cl.post("/api/seo/performance", json={}).status_code == 400
        assert cl.post("/api/seo/bogus", json={}).status_code == 404
        assert cl.post("/api/seo/site", json={"url": "nodot"}).status_code == 400
        assert cl.post("/api/seo/report", json={}).status_code == 200
