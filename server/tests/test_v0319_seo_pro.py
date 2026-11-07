"""v0.319 SEO PRO (ideas studied in claude-seo, MIT; Hoola's own code): health score in 7 parts + priorities, page drift
(17 rules), AI crawler map (search vs training bots), schema validation / retired types / templates, content quality
(word floors, stuffing, filler, unsourced claims, byline), images (weight bands, size, lazy, format), hreflang, near
duplicates, templated titles, scaled pages, NAP, business.site links, parasite pages, security headers + redirect hops,
llms.txt, E-E-A-T + local scorecards, report envelope, Google updates ledger; Search Console URL Inspection + Sitemaps,
CrUX history, LCP parts + screenshots, IndexNow, the drop alert, the hourly home-page drift alert, the scaled-content
gate on Hoola-built big websites, the tools and both apps."""
import json
from pathlib import Path

import httpx
import pytest

from tests import test_v0317_seo_employee as emp
from tests import test_v103_seo as base

T = "default"
ROOT = Path(__file__).resolve().parents[2]
LOG: dict = {"inspect": [], "indexnow": [], "crux": 0}
STATE: dict = {}

PSI = {"loadingExperience": {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3100}}},
       "lighthouseResult": {"categories": {"performance": {"score": .6}}, "audits": {
           "lcp-breakdown-insight": {"details": {"type": "list", "items": [{"type": "table", "items": [
               {"subpart": "timeToFirstByte", "label": "TTFB", "duration": 900},
               {"subpart": "resourceLoadDelay", "duration": 400},
               {"subpart": "resourceLoadDuration", "duration": 1500},
               {"subpart": "elementRenderDelay", "duration": 300}]}]}},
           "final-screenshot": {"details": {"type": "screenshot", "data": "data:image/jpeg;base64,AAAA"}}}}}


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    if u.startswith("https://www.googleapis.com/pagespeedonline"):
        return httpx.Response(200, json=PSI)
    if u.startswith("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"):
        b = json.loads(req.content)
        LOG["inspect"].append(b["inspectionUrl"])
        bad = b["inspectionUrl"].rstrip("/").endswith("services") and not STATE.get("indexed_all")
        return httpx.Response(200, json={"inspectionResult": {"indexStatusResult": {
            "verdict": "NEUTRAL" if bad else "PASS",
            "coverageState": "Crawled - currently not indexed" if bad else "Submitted and indexed",
            "googleCanonical": b["inspectionUrl"], "userCanonical": b["inspectionUrl"], "lastCrawlTime": "2026-10-20T10:00:00Z"},
            "richResultsResult": {"detectedItems": [{"richResultType": "Review snippets", "items": [{"issues": [
                {"issueMessage": "Missing field 'author'", "severity": "WARNING"}]}]}]}}})
    if "/sitemaps" in u and u.startswith("https://www.googleapis.com/webmasters/v3/sites/"):
        return httpx.Response(200, json={"sitemap": [{"path": "https://shop.example/sitemap.xml", "lastDownloaded": "2026-10-25",
                                                      "errors": 2, "warnings": 0, "contents": [{"type": "web", "submitted": "2"}]}]})
    if u.startswith("https://chromeuxreport.googleapis.com/"):
        LOG["crux"] += 1
        return httpx.Response(200, json={"record": {
            "collectionPeriods": [{"lastDate": {"year": 2026, "month": 10, "day": d}} for d in (11, 18, 25)],
            "metrics": {"largest_contentful_paint": {"percentilesTimeseries": {"p75s": [3200, 2900, 2600]}},
                        "cumulative_layout_shift": {"percentilesTimeseries": {"p75s": ["0.12", "0.10", "0.05"]}}}}})
    if u.startswith("https://api.indexnow.org/"):
        LOG["indexnow"].append(json.loads(req.content))
        return httpx.Response(200)
    if u.startswith("https://shop.example"):
        p = req.url.path
        if STATE.get("key") and p == f"/{STATE['key']}.txt":
            return httpx.Response(200, text=STATE["key"])
        if p == "/llms.txt":
            return httpx.Response(404, text="no")
        if req.method == "HEAD" and p.endswith(".jpg"):
            return httpx.Response(200, headers={"content-length": str(900 * 1024)})
        if p == "/robots.txt" and STATE.get("ai_block"):
            return httpx.Response(200, text="User-agent: GPTBot\nDisallow: /\n\nUser-agent: OAI-SearchBot\nDisallow: /\n\n"
                                            "User-agent: *\nDisallow: /private/\n")
    return emp.handler(req)


@pytest.fixture
def seo(env, monkeypatch):
    from app.seo import service as S
    monkeypatch.setattr(S, "today", lambda t: base.DAY)
    monkeypatch.setattr(S, "_safe", lambda u: u if "://" in u else "https://" + u)
    monkeypatch.setattr(S, "_token", lambda t, force=False: "tok")
    S.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    base.STATE["home"] = base.HOME
    emp.WATCH.clear()
    STATE.clear()
    LOG.update(inspect=[], indexnow=[], crux=0)
    yield S
    S.set_http(None)


def _page(url, **k):
    d = {"url": url, "status": 200, "title": "", "description": "", "h1": [], "h2": [], "words": 400, "https": True,
         "text_sample": "", "schema_types": [], "imgs": [], "hreflang": []}
    d.update(k)
    return d


# ---------------------------------------------------------------- pure checks
def test_health_parts_priorities_and_critical_cap():
    from app.seo import pro as P
    iss = [{"code": "title_short", "level": "warn", "url": "https://a.in/x"},
           {"code": "schema_missing_field", "level": "warn", "url": "https://a.in/"},
           {"code": "img_heavy", "level": "info", "url": "https://a.in/x"}]
    h = P.health(iss, 10, {"field_data": True, "grades": {"lcp": "poor", "inp": "good", "cls": "ni"}}, "https://a.in/")
    parts = {x["key"]: x["score"] for x in h["parts"]}
    assert set(parts) == set(P.WEIGHTS) and sum(P.WEIGHTS.values()) == 100
    assert parts["performance"] == 50 and parts["technical"] == 100 and parts["onpage"] < 100 and parts["schema"] < 100
    assert h["counts"] == {"critical": 0, "high": 0, "medium": 2, "low": 1} and 0 < h["total"] < 100
    crit = P.health(iss + [{"code": "robots_block", "level": "bad", "url": "https://a.in/"}], 10)
    assert crit["total"] <= 40 and crit["counts"]["critical"] == 1
    assert P.priority({"code": "noindex", "level": "bad", "url": "https://a.in/"}, "https://a.in/") == "critical"
    assert P.priority({"code": "noindex", "level": "bad", "url": "https://a.in/x"}, "https://a.in/") == "high"
    assert P.category("ai_search_blocked") == "ai" and P.category("unknown_code") == "technical"


def test_drift_rules():
    from app.seo import pro as P
    old = _page("https://a.in/s", title="Root canal in Akola", description="Painless", h1=["Root canal"], h2=["A", "B"],
                canonical="https://a.in/s", schema_types=["Dentist"], schema_hash="1", og={"og:title": "x"}, text_hash="t1",
                words=900, hreflang=[("hi", "https://a.in/hi/s")])
    new = dict(old, title="", description="New", h1=[], h2=["C"], canonical="https://a.in/other", noindex=True,
               schema_types=[], og={}, text_hash="t2", words=300, hreflang=[])
    rules = {x["rule"]: x["level"] for x in P.drift(old, new)}
    for r, lvl in (("title_removed", "bad"), ("desc_changed", "warn"), ("h1_removed", "bad"), ("canonical_changed", "bad"),
                   ("noindex_added", "bad"), ("schema_removed", "bad"), ("og_removed", "warn"), ("h2_changed", "info"),
                   ("content_changed", "info"), ("words_dropped", "warn"), ("hreflang_removed", "warn")):
        assert rules.get(r) == lvl, (r, rules)
    assert [x["rule"] for x in P.drift(old, dict(old, status=500))] == ["status_error"]
    assert P.drift(old, dict(old)) == []                                       # nothing changed, nothing said
    sch = P.drift(old, dict(old, schema_hash="2", schema_types=["Dentist", "FAQPage"]))
    assert [x["rule"] for x in sch] == ["schema_changed"] and "FAQPage" in sch[0]["text"]
    assert len(P.DRIFT_RULES) == 17


def test_ai_bots_tell_search_from_training():
    from app.seo import pro as P
    r = P.ai_bots("User-agent: GPTBot\nDisallow: /\n\nUser-agent: OAI-SearchBot\nDisallow: /\n", "https://a.in/")
    rows = {x["bot"]: x for x in r["rows"]}
    assert not rows["GPTBot"]["allowed"] and rows["GPTBot"]["kind"] == "training"
    assert not rows["OAI-SearchBot"]["allowed"] and rows["Googlebot"]["allowed"] and rows["ClaudeBot"]["allowed"]
    codes = {i["code"]: i["level"] for i in r["issues"]}
    assert codes == {"ai_search_blocked": "warn", "ai_training_blocked": "info"}
    g = P.ai_bots("User-agent: Googlebot\nDisallow: /\n", "https://a.in/")
    assert any(i["code"] == "google_blocked" and i["level"] == "bad" for i in g["issues"])
    assert P.ai_bots("", "https://a.in/")["issues"] == []


def test_schema_validation_and_templates():
    from app.seo import pro as P
    blocks = ['{"@context": "https://schema.org", "@type": "Dentist", "name": "Sharma"}',
              '{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}',
              '{"@context": "https://schema.org", "@graph": [{"@type": "HowTo", "name": "x"}, {"@type": "Product"}]}',
              '{"broken": ']
    r = P.schema_parse(blocks)
    assert r["types"] == ["Dentist", "FAQPage", "HowTo", "Product"] and r["hash"]
    codes = [p["code"] for p in r["problems"]]
    assert "schema_invalid" in codes and "schema_faq" in codes and "schema_retired" in codes
    miss = [p["text"] for p in r["problems"] if p["code"] == "schema_missing_field"]
    assert any("Dentist" in t and "address" in t for t in miss) and any("Product" in t and "name" in t for t in miss)
    b = {"name": "Sharma Dental", "url": "https://a.in/", "phone": "9822000000", "city": "Akola"}
    assert P.schema_template("organization", b)["telephone"] == "9822000000"
    bc = P.schema_template("breadcrumb", b, {"url": "https://a.in/services/root-canal"})
    assert [i["name"] for i in bc["itemListElement"]] == ["Home", "Services", "Root Canal"]
    art = P.schema_template("article", b, {"title": "Tooth pain at night"})
    assert art["@type"] == "Article" and "datePublished" not in art                   # empty fields left out, never invented
    with pytest.raises(ValueError):
        P.schema_template("howto", b)


def test_content_quality_checks():
    from app.seo import pro as P
    filler = "Look no further. In today's fast-paced world we are a game-changer. "
    p = _page("https://a.in/blog/teeth", words=600, schema_types=["BlogPosting"],
              text_sample=filler + "Studies show 87% of people and 45% of kids. " + "teeth " * 40 + " ".join(f"word{i}" for i in range(400)))
    codes = {i["code"] for i in P.quality(p)}
    assert {"word_floor", "filler", "claims", "byline"} <= codes
    stuffed = _page("https://a.in/s", text_sample="dentist akola best " * 120)
    assert any(i["code"] == "stuffing" for i in P.quality(stuffed))
    ok = _page("https://a.in/about", words=900, author="A", published="2026-01-01", ext_links=2,
               text_sample="We opened in 2009 near Station Road. " * 30)
    assert P.quality(ok) == []
    assert P.page_type(_page("https://a.in/", is_home=True)) == "home" and P.page_type(_page("https://a.in/services/x/")) == "service"


def test_images_hreflang_and_page_checks():
    from app.seo import pro as P
    imgs = [{"src": f"https://a.in/i{n}.jpg", "w": None, "h": None, "loading": ""} for n in range(9)]
    p = _page("https://a.in/", imgs=imgs, js_shell=True,
              hreflang=[("hi", "https://a.in/hi/"), ("en-uk1", "https://a.in/en/")])
    iss = P.page_checks(p, {"https://a.in/i0.jpg": 800 * 1024, "https://a.in/i1.jpg": 250 * 1024})
    codes = {i["code"]: i["level"] for i in iss}
    assert codes["img_heavy"] == "warn" and "img_size" in codes and "img_lazy" in codes and "img_format" in codes
    assert codes["js_only"] == "warn" and {i["level"] for i in iss if i["code"] == "hreflang"} == {"warn", "info"}
    a = _page("https://a.in/", hreflang=[("en", "https://a.in/"), ("hi", "https://a.in/hi/")])
    b = _page("https://a.in/hi/", hreflang=[("hi", "https://a.in/hi/")])
    assert [i["code"] for i in P.hreflang_site([a, b])] == ["hreflang_return"]
    assert P.page_checks(_page("https://a.in/x", status=404, js_shell=True)) == []


def test_site_checks_duplicates_templates_scaled_nap_parasite_security():
    from app.seo import pro as P
    same = "Our clinic in Akola offers root canal treatment with modern machines and caring doctors every day. " * 12
    dup = [_page("https://a.in/x", text_sample=same), _page("https://a.in/y", text_sample=same + " extra words here")]
    assert P.near_duplicates(dup)[0]["code"] == "near_dup"
    tpl = [_page(f"https://a.in/dentist/c{i}", title=f"Best Dentist in City{i} | Sharma") for i in range(12)]
    assert P.templated_meta(tpl)[0]["code"] == "meta_template"
    loc = [_page(f"https://a.in/areas/a{i}", text_sample=same + f" area {i}") for i in range(52)]
    sc = P.scaled_pages(loc)
    assert sc and sc[0]["code"] == "scaled" and sc[0]["level"] == "bad"
    assert P.scaled_pages(loc[:20]) == []                                    # under the location warn line
    pages = [_page("https://a.in/", is_home=True, phones=["+91 98220 11111"], text_sample="Station Road Akola"),
             _page("https://a.in/contact", is_contact=True, ext=["https://sharma.business.site/"])]
    nap = P.nap(pages, {"phone": "9822000000", "pin": "444001"})
    assert [i["level"] for i in nap] == ["warn", "info"]
    assert P.gbp_links(pages)[0]["code"] == "gbp_link"
    hacked = [_page("https://a.in/blog/x", title="Best online casino bonus")]
    assert P.parasite(hacked, ["Root canal"])[0]["level"] == "bad" and P.parasite(hacked, ["casino"]) == []
    sec = P.security({"content-type": "text/html"}, ["http://a.in/", "https://a.in/", "https://www.a.in/"], "https://a.in/")
    assert {i["code"] for i in sec} == {"sec_headers", "redirect_hops"}
    good = {"strict-transport-security": "x", "x-content-type-options": "nosniff", "referrer-policy": "x", "x-frame-options": "DENY"}
    assert P.security(good, ["https://a.in/"], "https://a.in/") == []
    assert P.llms_txt(False, "https://a.in/")[0]["level"] == "info" and P.llms_txt(True, "https://a.in/") == []


def test_eeat_local_envelope_and_updates():
    from app.seo import pro as P
    pages = [_page("https://a.in/", is_home=True, schema_types=["Dentist"], phones=["9822000000"], title="Dentist in Akola",
                   text_sample="Since 2009 we have served Akola 444001. ISO 9001 certified.", map=True),
             _page("https://a.in/about"), _page("https://a.in/contact", is_contact=True), _page("https://a.in/privacy-policy"),
             _page("https://a.in/testimonials")]
    e = P.eeat(pages, {"pin": "444001", "same_as": ["https://facebook.com/x"]})
    assert [p["key"] for p in e["parts"]] == ["experience", "expertise", "authority", "trust"]
    assert [p["max"] for p in e["parts"]] == [20, 25, 25, 30] and 40 <= e["total"] <= 100
    loc = P.local_score(pages, {"city": "Akola", "phone": "9822000000", "same_as": ["x"]}, [])
    got = {p["key"]: p["score"] for p in loc["parts"]}
    assert got["gbp"] is None and got["reviews"] is None and got["onpage"] == 20 and got["schema"] == 10 and loc["total"] == 100
    env = P.envelope("content")
    assert env["principle"] and env["fail_check"] and env["signal"]
    ups = P.updates_between("2026-05-15", "2026-06-30")         # padded a week back: rollouts take ~2 weeks
    assert [u["date"] for u in ups] == ["2026-05-21", "2026-06-24"]


# ---------------------------------------------------------------- the crawl + the desk
def test_crawl_saves_health_drift_priorities(seo):
    S = seo
    base.site(S)
    STATE["ai_block"] = True
    r = S.crawl(T)
    assert r["health"]["total"] > 0 and r["drift"] == []
    pro = S.pro_view(T)
    assert {"health", "eeat", "local", "ai_bots", "drift", "hops"} <= set(pro)
    assert not next(b for b in pro["ai_bots"] if b["bot"] == "OAI-SearchBot")["allowed"] and pro["llms"] is False
    ts = S.tasks(T)
    assert all(t["priority"] in ("critical", "high", "medium", "low") and t["category"] for t in ts)
    assert [t["priority"] for t in ts] == sorted((t["priority"] for t in ts), key=["critical", "high", "medium", "low"].index)
    codes = {t["code"] for t in ts}
    assert {"ai_search_blocked", "sec_headers", "llms_txt", "stuffing"} <= codes
    assert len({(t["code"], t["url"]) for t in ts}) == len(ts)                   # one task per kind per page
    assert S.sites(T)[0]["health"] == r["health"]["total"]
    score_before = r["score"]
    base.STATE["home"] = base.HOME.replace("<title>Sharma Dental</title>", "<title>Best Dentist in Akola | Sharma Dental Clinic</title>")
    r2 = S.crawl(T)
    assert any(x["rule"] == "title_changed" for x in r2["drift"]) and "badlav" in r2["say"]
    assert isinstance(score_before, int)


def test_weekly_index_check_drift_alerts_crux_shots_indexnow(seo):
    from app.employee import hire
    from app.seo import desk
    S = seo
    emp._connect_google(S)
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", "Sharma Dental", "Akola", ["Root canal"], background=False, ask=lambda *a, **k: emp.FAKE_PLAN)
    k = desk.indexnow_key(T)
    assert not k["live"] and k["file"].endswith(f"/{k['key']}.txt") and "Put a file" in k["say"]
    STATE["key"] = k["key"]
    assert desk.indexnow_key(T)["live"]
    from app.config import get_settings
    import os
    os.environ["PAGESPEED_API_KEY"] = "k"
    get_settings.cache_clear()
    try:
        base.STATE["home"] = base.HOME.replace("<title>Sharma Dental</title>", "<title>Best Dentist in Akola | Sharma Dental Clinic</title>")
        sid = desk.desk_view(T)["site"]["id"]
        out = desk.weekly(T, sid)
    finally:
        os.environ.pop("PAGESPEED_API_KEY", None)
        get_settings.cache_clear()
    assert out["index"]["checked"] >= 2 and out["index"]["indexed"] == out["index"]["checked"] - 1
    assert LOG["inspect"][0] == "https://shop.example/"
    ts = {(t["code"], t["url"].rstrip("/").rsplit("/", 1)[-1]) for t in S.tasks(T)}
    assert ("gsc_not_indexed", "services") in ts and ("gsc_sitemap", "sitemap.xml") in ts
    S.crawl(T)                                                               # the crawl leaves Google's findings alone
    assert any(t["code"] == "gsc_not_indexed" for t in S.tasks(T))
    STATE["indexed_all"] = True
    desk.index_check(T, sid)
    assert not any(t["code"] == "gsc_not_indexed" for t in S.tasks(T))
    assert any(t["code"] == "gsc_not_indexed" for t in S.tasks(T, status="fixed"))
    assert out["crux"]["weeks"] == 3 and out["drift"]["other"] >= 1
    assert LOG["indexnow"] and LOG["indexnow"][0]["urlList"] == ["https://shop.example/"] and LOG["indexnow"][0]["key"] == k["key"]
    v = desk.desk_view(T)
    assert v["index"]["checked"] and len(v["crux"]["weeks"]) == 3 and v["pro"]["health"]["total"]
    assert set(v["shots"]) == {"mobile", "desktop"} and v["shots"]["mobile"]["img"].startswith("data:image/")
    assert v["latest"]["cwv"]["lcp_parts"][0] == {"part": "timetofirstbyte", "label": "Server response (TTFB)", "ms": 900}
    assert all(x["fail_check"] and x["signal"] and x["principle"] for x in desk.roadmap(T))
    title, md = desk.report_markdown(T, sid)
    assert "# Website health" in md and "Early sign:" in md and "URL Inspection" in md


def test_drop_alert_names_google_updates(seo):
    from app.seo import desk
    S = seo
    base.site(S)
    sid = S.sites(T)[0]["id"]
    desk.ensure_tables()
    with S.session() as s:
        s.add(desk.SeoDesk(site_id=sid, tenant_id=T))
    assert desk.drop_alert(T, sid, {"clicks": 100}, {"clicks": 90}) is None
    r = desk.drop_alert(T, sid, {"clicks": 100, "start": "2026-05-01"}, {"clicks": 50, "end": "2026-05-28"})
    assert r["pct"] == 50 and any(u["name"].startswith("May 2026 core") for u in r["updates"])
    with S.session() as s:
        texts = [e.text for e in s.query(desk.SeoEvent).all()]
    assert any("May 2026 core update" in t for t in texts)


def test_hourly_watch_alerts_home_drift_once(seo):
    from app.employee import hire
    from app.seo import desk
    S = seo
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", "Sharma Dental", "Akola", ["Root canal"], background=False, ask=lambda *a, **k: emp.FAKE_PLAN)
    sid = desk.desk_view(T)["site"]["id"]
    assert desk.watch(T, sid)["alerts"] == []
    base.STATE["home"] = base.HOME.replace("<title>Sharma Dental</title>", "")
    a = desk.watch(T, sid)["alerts"]
    assert len(a) == 1 and "Title hat gaya" in a[0]
    assert desk.watch(T, sid)["alerts"] == []                                  # one alert, not one an hour


def test_crux_and_lcp_parts_shapes(seo):
    S = seo
    base.site(S)
    with pytest.raises(S.SeoError):
        S.crux_history(T)                                                      # needs the server's Google API key
    assert S.lcp_parts({"audits": {"largest-contentful-paint-element": {"details": {"items": [{}, {"items": [
        {"phase": "TTFB", "timing": 500}, {"phase": "Load Delay", "timing": 100}, {"phase": "Load Time", "timing": 200},
        {"phase": "Render Delay", "timing": 50}]}]}}}}) == [
        {"part": "ttfb", "label": "Server response (TTFB)", "ms": 500},
        {"part": "loaddelay", "label": "Main picture starts late", "ms": 100},
        {"part": "loadtime", "label": "Main picture download", "ms": 200},
        {"part": "renderdelay", "label": "Shown late (render delay)", "ms": 50}]
    assert S.lcp_parts({}) == []
    assert "LCP mein sabse zyada samay" in S.pagespeed(T)["say"]


def test_schema_kinds_and_tools(seo):
    import asyncio

    from app.agent import seo_tools as ST
    from app.agent.tools import Ctx, ToolError
    S = seo
    base.site(S)
    S.crawl(T)
    ctx = Ctx(tenant_id=T, conversation_id="c1")
    run = lambda fn, *a, **k: asyncio.run(fn(ctx, *a, **k))                      # noqa: E731
    org = run(ST.seo, "schema", kind="organization")
    assert '"@type": "Organization"' in org["text"] and "Organization" in org["say"]
    assert '"@type": "Dentist"' in run(ST.seo, "schema")["text"]                    # LocalBusiness stays the default
    bc = run(ST.seo, "schema", kind="breadcrumb", url="https://shop.example/services")
    assert '"Services"' in bc["text"]
    with pytest.raises(ToolError):
        run(ST.seo, "schema", kind="howto")
    h = run(ST.seo_dekho, "health")
    assert h["health"]["total"] and len(h["ai_bots"]) == len(__import__("app.seo.pro", fromlist=["x"]).AI_BOTS)
    assert run(ST.seo_dekho, "changes")["changes"] == []
    assert run(ST.seo_dekho, "updates")["updates"][-1]["date"] == "2026-09-24"
    emp._connect_google(S)
    got = run(ST.seo, "inspect", urls=["https://shop.example/", "https://shop.example/services"])
    assert "1 / 2" in got["say"] and got["pages"][0]["rich"][0]["issues"] == ["Missing field 'author'"]
    with pytest.raises(ToolError):
        run(ST.seo, "indexnow")                                                 # only for a hired SEO Specialist
    names = {t["name"]: t for t in ST.SEO_TOOLS}
    assert "inspect" in names["seo"]["input_schema"]["properties"]["action"]["enum"]
    assert "health" in names["seo_dekho"]["input_schema"]["properties"]["what"]["enum"]


def test_big_website_scaled_content_gate():
    from app.site import sitemap as SM
    br = {"designs": {}}
    raw = {"pages": [{"slug": "home", "title": "Home", "sections": ["hero"]}],
           "collections": [{"key": "areas", "label": "Service areas", "fields": [{"key": "time", "label": "Time"}],
                            "items": [{"title": f"Area {i}", "data": {"time": "45 min"}} for i in range(70)]},
                           {"key": "sweets", "label": "Sweets", "fields": [{"key": "price", "label": "Price"}],
                            "items": [{"title": f"Sweet {i}", "data": {"price": f"{100 + i}"}} for i in range(12)]}]}
    plan = SM.clean(raw, br, {"pages": []}, 150)
    cols = {c["key"]: c for c in plan["collections"]}
    assert len(cols["areas"]["items"]) == SM.LOCATION_STOP == 50                # place pages stop at 50
    assert len(cols["sweets"]["items"]) == 12
    g = plan["gate"]
    assert len(g) == 1 and g[0]["collection"] == "areas" and g[0]["location"] and "scaled content" in g[0]["say"]


def test_console_phone_and_notices_are_wired():
    js = (ROOT / "server/app/static/console/employees.js").read_text()
    assert "em-health" in js and "AI search" in js and "seo/run/indexnow" in js and "fail_check" in js and "em-shot" in js
    dart = (ROOT / "lib/ui/employees_screen.dart").read_text()
    assert "_HealthCard" in dart and "'ai_bots'" in dart and "fail_check" in dart and "seoRun(" in dart
    assert "claude-seo" in (ROOT / "THIRD_PARTY_NOTICES.md").read_text() and "MIT" in (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
