"""v0.317 SEO EMPLOYEE Phase 0 + 1: hire from the Employee Hub (desk only after hiring), onboarding -> full audit ->
frozen baseline -> 90-day roadmap (Opus faked, rules fallback), KPIs against the baseline, hourly watch alerts on change,
daily / weekly / monthly jobs on her clock, Google Analytics organic numbers, the monthly report PDF, the API + tools.
Mock website + Google APIs from test_v103_seo."""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from tests import test_v103_seo as base

T = "default"
IST = timezone(timedelta(hours=5, minutes=30))

GA4 = {"summaries": {"accountSummaries": [{"displayName": "Sharma", "propertySummaries": [
    {"property": "properties/111", "displayName": "Other site"}, {"property": "properties/222", "displayName": "Sharma Dental"}]}]},
       "streams": {"properties/111": {"dataStreams": [{"webStreamData": {"defaultUri": "https://other.example"}}]},
                   "properties/222": {"dataStreams": [{"webStreamData": {"defaultUri": "https://www.shop.example"}}]}},
       "report": {"rows": [
           {"dimensionValues": [{"value": "Organic Search"}], "metricValues": [{"value": "420"}, {"value": "37"}]},
           {"dimensionValues": [{"value": "Direct"}], "metricValues": [{"value": "300"}, {"value": "12"}]}]}}
LINKY = """<html lang="en"><head><title>Sharma Dental Akola</title><meta name="viewport" content="width=device-width">
<meta name='description' content='Dentist in Akola for root canal, implants and braces with same day appointments and fair prices.'>
</head><body><h1>Dentist in Akola</h1><img src="http://cdn.shop.example/a.jpg" alt="clinic">
<a href="/services">Services</a> <a href="/gone">Gone</a> <a href="/old">Old</a> <a href="/a">A</a></body></html>"""
PAGE = ("<html lang='en'><head><title>{t} page of Sharma Dental</title><meta name='viewport' content='width=device-width'>"
        "<meta name='description' content='Dentist in Akola for root canal, implants and braces with same day appointments and fair prices.'>"
        "</head><body><h1>{t}</h1><p>" + "words " * 300 + "</p>{link}</body></html>")
CHAIN = {"/a": "/b", "/b": "/c", "/c": "/d", "/d": "/e"}


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    if u.startswith("https://analyticsadmin.googleapis.com/v1beta/accountSummaries"):
        return httpx.Response(200, json=GA4["summaries"])
    if u.startswith("https://analyticsadmin.googleapis.com/v1beta/properties/"):
        prop = "/".join(req.url.path.split("/")[2:4])
        return httpx.Response(200, json=GA4["streams"].get(prop, {}))
    if u.startswith("https://analyticsdata.googleapis.com/v1beta/properties/222:runReport"):
        return httpx.Response(200, json=GA4["report"])
    if u.startswith("https://shop.example"):
        p = req.url.path
        if WATCH.get("down") and p == "/":
            return httpx.Response(503, text="down")
        if p == "/robots.txt" and WATCH.get("block"):
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        if p == "/" and WATCH.get("linky"):
            return httpx.Response(200, text=LINKY, headers={"content-type": "text/html"})
        if p == "/sitemap.xml" and WATCH.get("linky"):
            return httpx.Response(200, text="<urlset><url><loc>https://shop.example/services</loc></url>"
                                            "<url><loc>https://shop.example/lonely</loc></url></urlset>")
        if WATCH.get("linky") and (p in CHAIN or p in ("/e", "/lonely")):
            nxt = CHAIN.get(p)
            return httpx.Response(200, text=PAGE.format(t=p.strip("/").upper(), link=f'<a href="{nxt}">next</a>' if nxt else ""))
        if p == "/gone":
            return httpx.Response(404, text="gone")
    return base.handler(req)


WATCH: dict = {}


@pytest.fixture
def seo(env, monkeypatch):
    from app.seo import service as S
    monkeypatch.setattr(S, "today", lambda t: base.DAY)
    monkeypatch.setattr(S, "_safe", lambda u: u if "://" in u else "https://" + u)
    monkeypatch.setattr(S, "_token", lambda t, force=False: "tok")
    S.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    base.STATE["home"] = base.HOME
    WATCH.clear()
    yield S
    S.set_http(None)


def _connect_google(S, analytics=True):
    with S.session() as s:
        s.add(S.SeoGoogle(tenant_id=T, address="her@x.in", scopes=S.GSC_SCOPE + (" " + S.GA4_SCOPE if analytics else "")))


FAKE_PLAN = {"items": [
    {"week": 1, "workstream": "technical", "title": "Remove noindex from the contact page", "why": "noindex on /contact", "impact": 3, "effort": 1},
    {"week": 2, "workstream": "content", "title": "Lift 'dentist in akola' from 6.4 to the top 3", "why": "900 impressions", "impact": 3, "effort": 2},
    {"week": 3, "workstream": "local", "title": "Complete the Business Profile", "why": "local calls", "impact": 2, "effort": 1, "owner": "her"},
    {"week": 5, "workstream": "ai_search", "title": "FAQ on the root canal page", "why": "long questions", "impact": 2, "effort": 2},
    {"week": 99, "workstream": "nonsense", "title": "x" * 400, "impact": 9, "effort": "a"},
    {"title": ""}]}


# ---------------------------------------------------------------- Phase 0: hire
def test_hire_pause_leave_and_desk_only_after_hiring(seo):
    from app.employee import hire
    from app.seo import desk
    cat = {c["key"]: c for c in hire.catalog(T)}
    assert cat["seo"]["live"] and cat["seo"]["status"] == "none" and not cat["social"]["live"]
    assert desk.desk_view(T) == {"hired": False, "status": "none"}
    with pytest.raises(hire.HireError):
        hire.hire(T, "social")                             # "coming" employees can't be hired yet
    with pytest.raises(seo.SeoError):
        desk.onboard(T, "shop.example", background=False)  # no desk work before hiring
    hire.hire(T, "seo")
    assert hire.hired_keys(T) == {"seo": "hired"} and hire.working_tenants("seo") == [T]
    v = desk.desk_view(T)
    assert v["hired"] and not v["onboarded"] and v["trust"] == "seekh"
    hire.pause(T, "seo")
    assert hire.hired_keys(T) == {"seo": "paused"} and hire.working_tenants("seo") == []   # paused = desk stays, jobs stop
    hire.resume(T, "seo")
    assert hire.hire(T, "seo")["already"]
    hire.leave(T, "seo")
    assert hire.hired_keys(T) == {} and desk.desk_view(T)["hired"] is False and hire.working_tenants("seo") == []
    assert hire.hire(T, "seo")["status"] == "hired"         # can be hired again (a new row, history kept)


# ---------------------------------------------------------------- Phase 1: onboarding -> baseline -> roadmap
def test_onboarding_builds_baseline_and_opus_roadmap(seo):
    from app.employee import hire
    from app.seo import desk
    _connect_google(seo)
    hire.hire(T, "seo")
    asked = {}

    def opus(system, prompt, kind, images, timeout, **kw):
        asked.update(kind=kind, prompt=prompt, max_tokens=kw.get("max_tokens"))
        return FAKE_PLAN
    r = desk.onboard(T, "shop.example", "Sharma Dental", "Akola", ["Root canal", "Implants"], goal="More calls for implants",
                     competitors=["smile.example"], trust="saathi", weekday=4, morning_time="10:00", background=False, ask=opus)
    assert asked["kind"] == "seo_plan" and asked["max_tokens"] == 4000
    assert "dentist in akola" in asked["prompt"] and "More calls for implants" in asked["prompt"]
    assert r["audit"]["pages"] >= 2 and r["roadmap"]["source"] == "opus"
    b = r["baseline"]
    assert b["score"] is not None and b["gsc"]["clicks"] == 60 and b["ga4"] == {
        "property": "properties/222", "organic_sessions": 420, "leads": 37, "all_sessions": 720,
        "start": b["ga4"]["start"], "end": b["ga4"]["end"]}
    items = desk.roadmap(T)
    assert len(items) == 5 and all(1 <= x["week"] <= 13 and 1 <= x["impact"] <= 3 for x in items)
    assert next(x for x in items if x["title"].startswith("x"))["workstream"] == "technical"      # junk cleaned, not trusted
    assert max(len(x["title"]) for x in items) <= 150
    v = desk.desk_view(T)
    assert v["onboarded"] and v["state"] == "ready" and v["roadmap_status"] == "draft" and v["trust"] == "saathi"
    assert v["goals"]["goal"] == "More calls for implants" and v["competitors"] == ["smile.example"]
    assert {k["name"] for k in v["kpis"]} >= {"SEO score", "Clicks from Google (28 days)", "Leads / orders from Google"}
    assert seo.settings(T)["weekday"] == 4 and v["schedule"][2]["every"] == "Every Friday"
    desk.approve_roadmap(T)
    assert desk.desk_view(T)["roadmap_status"] == "approved"
    it = items[0]
    desk.set_item(T, it["id"], "done")
    with pytest.raises(seo.SeoError):
        desk.set_item(T, it["id"], "bogus")
    desk.build_roadmap(T, v["site"]["id"], ask=lambda *a, **k: {})           # rebuild: rules plan, done work kept
    after = desk.roadmap(T)
    assert any(x["id"] == it["id"] and x["status"] == "done" for x in after) and any(x["source"] == "rules" for x in after)
    assert desk.desk_view(T)["roadmap_status"] == "approved"                  # an approved plan stays approved


def test_rules_roadmap_without_a_model(seo):
    from app.employee import hire
    from app.seo import desk
    hire.hire(T, "seo")
    r = desk.onboard(T, "shop.example", "Sharma Dental", "Akola", ["Root canal"], background=False)
    assert r["roadmap"]["source"] == "rules" and len(r["roadmap"]["items"]) >= 5
    ws = {x["workstream"] for x in r["roadmap"]["items"]}
    assert {"technical", "local", "ai_search", "authority", "reporting"} <= ws
    assert "gsc" not in r["baseline"]                    # Search Console not connected: no fake zeros


# ---------------------------------------------------------------- the full crawl's new checks
def test_full_crawl_finds_link_problems(seo):
    from app.seo import desk
    WATCH["linky"] = True
    seo.save_site(T, "shop.example", "Sharma Dental", city="Akola")
    r = seo.crawl(T, max_pages=100, cap=500)
    codes = {(t["code"], t["url"].replace("https://shop.example", "")) for t in seo.tasks(T)}
    assert ("broken_link", "/") in codes                   # / links to /gone (404)
    assert ("redirect_link", "/") in codes                 # / links to /old (301 -> /services)
    assert ("orphan", "/lonely") in codes                  # in the sitemap, nobody links to it
    assert ("deep", "/e") in codes                         # / -> /a -> /b -> /c -> /d -> /e
    assert ("mixed", "/") in codes                         # http:// picture on an https page
    assert ("dup_desc", "/b") in codes or ("dup_desc", "/a") in codes
    assert r["pages"] >= 7
    assert seo.crawl(T, max_pages=1000)["pages"] <= 60     # a one-off check keeps the old 60-page cap
    assert desk.KEY == "seo"


# ---------------------------------------------------------------- 24/7
def test_watch_alerts_once_on_change_and_says_when_recovered(seo):
    from app.employee import hire
    from app.seo import desk
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", background=False)
    sid = desk.desk_view(T)["site"]["id"]
    pub = []
    orig = seo._publish
    seo._publish = lambda t, k, p, c="": pub.append((k, p))
    try:
        assert desk.watch(T, sid)["alerts"] == []
        WATCH["block"] = True
        assert desk.watch(T, sid)["alerts"] == ["robots.txt ab poori site ko Google se rok raha hai (Disallow: /)."]
        assert desk.watch(T, sid)["alerts"] == []          # still blocked: no second alert
        WATCH["block"] = False
        WATCH["down"] = True
        a = desk.watch(T, sid)["alerts"]
        assert a and "khul nahi" in a[0]
        WATCH["down"] = False
        desk.watch(T, sid)
    finally:
        seo._publish = orig
    kinds = [(e["kind"], e["level"]) for e in desk.desk_view(T)["events"]]
    assert ("recovered", "ok") in kinds and sum(1 for k in kinds if k == ("alert", "bad")) == 2
    assert [k for k, _ in pub].count("seo_alert") == 2


def test_scheduler_runs_each_job_once_on_her_clock(seo, monkeypatch):
    from app.employee import hire
    from app.seo import desk
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", weekday=0, background=False)
    sid = desk.desk_view(T)["site"]["id"]
    ran = []
    monkeypatch.setattr(desk, "watch", lambda t, s: ran.append("hourly") or {})
    monkeypatch.setattr(desk, "daily", lambda t, s: ran.append("daily") or {})
    monkeypatch.setattr(desk, "weekly", lambda t, s: ran.append("weekly") or {})
    monkeypatch.setattr(desk, "monthly_report", lambda t, s, conv="": ran.append("monthly") or {})
    mon = datetime(2026, 6, 1, 8, 0, tzinfo=IST)            # Monday the 1st, 8 am
    assert sorted(desk.due_jobs(T, sid, mon)) == ["daily", "hourly", "monthly", "weekly"]
    desk.run_due(mon, force=True)
    assert sorted(ran) == ["daily", "hourly", "monthly", "weekly"]
    ran.clear()
    desk.run_due(mon + timedelta(minutes=30), force=True)
    assert ran == []                                        # nothing twice
    desk.run_due(mon + timedelta(hours=1), force=True)
    assert ran == ["hourly"]
    ran.clear()
    desk.run_due(mon + timedelta(days=1), force=True)       # Tuesday: hourly + daily only
    assert sorted(ran) == ["daily", "hourly"]
    ran.clear()
    hire.pause(T, "seo")
    desk.run_due(mon + timedelta(days=2), force=True)
    assert ran == []                                        # paused: no jobs


def test_daily_keeps_speed_and_fills_baseline_when_google_joins_later(seo):
    from app.employee import hire
    from app.seo import desk
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", background=False)
    sid = desk.desk_view(T)["site"]["id"]
    assert "gsc" not in desk.desk_view(T)["baseline"]
    _connect_google(seo)
    desk.daily(T, sid)
    v = desk.desk_view(T)
    assert v["baseline"]["gsc"]["clicks"] == 60 and v["latest"]["ga4"]["leads"] == 37
    assert seo.SeoStat.__tablename__ and not seo.summary(T)["stats"]        # the daily pull does not add trend rows


def test_monthly_report_pdf_is_made_and_delivered(seo):
    from app.employee import hire
    from app.seo import desk
    _connect_google(seo, analytics=False)
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", "Sharma Dental", background=False)
    sid = desk.desk_view(T)["site"]["id"]
    seo.performance(T, sid, 28)
    seo.performance(T, sid, 28)
    title, md = desk.report_markdown(T, sid)
    assert "SEO report" in title and "> [!KEY]" in md and "[chart: line" in md and "| Measure | Baseline | Now | Change |" in md
    r = desk.monthly_report(T, sid)
    assert r["file"] and r["pages"] >= 1
    assert any(e["kind"] == "report" for e in desk.desk_view(T)["events"])


# ---------------------------------------------------------------- API + tools
def test_api_hire_onboard_desk(seo, monkeypatch):
    from app.main import app
    from app.seo import desk
    monkeypatch.setattr(desk.threading, "Thread", lambda target, args=(), kwargs=None, daemon=None: type(
        "T", (), {"start": lambda self: target(*args, **(kwargs or {}))})())
    with TestClient(app) as c:
        me = c.get("/api/console/me").json()
        assert me["employees"] == {}
        cat = c.get("/api/employees").json()
        assert any(e["key"] == "seo" and e["live"] for e in cat["employees"])
        assert c.post("/api/employees/social/hire").status_code == 400
        assert c.post("/api/seo/onboard", json={"url": "shop.example"}).status_code == 400    # not hired yet
        assert c.post("/api/employees/seo/hire", json={"trust": "seekh"}).json()["status"] == "hired"
        assert c.get("/api/console/me").json()["employees"] == {"seo": "hired"}
        r = c.post("/api/seo/onboard", json={"url": "shop.example", "name": "Sharma Dental", "city": "Akola",
                                             "services": "Root canal, Implants", "competitors": "smile.example",
                                             "goal": "More calls", "weekday": 2}).json()
        assert r["state"] == "first_run"
        d = c.get("/api/seo/desk").json()
        assert d["onboarded"] and d["state"] == "ready" and d["roadmap_count"] >= 5 and d["site"]["url"] == "https://shop.example/"
        assert c.post("/api/seo/roadmap/approve").json()["roadmap_status"] == "approved"
        item = d["board"]["planned"][0]["id"]
        assert c.post(f"/api/seo/roadmap/item/{item}", json={"status": "doing"}).json()["status"] == "doing"
        assert c.put("/api/employees/seo/settings", json={"trust": "saathi"}).json()["trust"] == "saathi"
        assert c.post("/api/seo/run/hourly").json()["started"] == "hourly"
        assert c.post("/api/seo/run/bogus").status_code == 404
        assert c.post("/api/employees/seo/pause").json()["status"] == "paused"
        assert c.post("/api/employees/seo/leave").json()["status"] == "left"
        assert c.get("/api/seo/desk").json()["hired"] is False


def test_tools_desk_and_report(seo):
    import asyncio
    from app.agent.seo_tools import seo as seo_tool
    from app.agent.seo_tools import seo_dekho
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire
    from app.seo import desk
    ctx = Ctx(tenant_id=T, conversation_id="c1")
    assert asyncio.run(seo_dekho(ctx, what="desk"))["hired"] is False
    with pytest.raises(ToolError):
        asyncio.run(seo_tool(ctx, action="report_pdf"))
    hire.hire(T, "seo")
    desk.onboard(T, "shop.example", background=False)
    v = asyncio.run(seo_dekho(ctx, what="desk"))
    assert v["onboarded"] and "sites" not in v
    assert asyncio.run(seo_tool(ctx, action="roadmap"))["source"] == "rules"
    assert asyncio.run(seo_tool(ctx, action="report_pdf"))["file"]


def test_console_and_phone_are_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    con = root / "server/app/static/console"
    html, js, emp = (con / "v2.html").read_text(), (con / "v2.js").read_text(), (con / "employees.js").read_text()
    assert 'id="v-hire"' in html and 'id="v-seodesk"' in html and "/static/console/employees.js?v=" in html
    assert "HoolaEmployees(" in js and "syncEmployees(ME.employees" in js and "['seodesk', 'SEO Desk']" in js
    assert "esc(" in emp and "innerHTML = `" in emp and "/api/seo/desk" in emp
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "class EmployeesScreen" in dart and "class SeoDeskScreen" in dart and "withValues(" not in dart
    assert "EmployeesScreen(app: app)" in (root / "lib/ui/profile_screen.dart").read_text()
    api = (root / "lib/api.dart").read_text()
    for m in ("employees()", "employeeAct(", "seoDesk()", "seoOnboard(", "seoRoadmapApprove()", "seoRoadmapItem(", "seoRun("):
        assert m in api, m
