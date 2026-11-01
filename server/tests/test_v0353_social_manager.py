"""v0.353 SOCIAL MEDIA MANAGER Phase 1: hire -> set up -> connect Instagram (Instagram Login) and a Facebook Page (Facebook
Login for Business) through Hoola's one Meta app -> read posts + numbers -> baseline -> strategy + 30-day calendar (Opus
faked, rules fallback) -> she approves / edits; hourly token renewal, dead-token alert once, Meta data-deletion callback
(signed_request verified), API + console + phone wiring. Meta is a mock transport; nothing is published in Phase 1."""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

T = "default"
ROOT = Path(__file__).resolve().parents[2]
CALLS: list[str] = []
STATE: dict = {}
NOW = datetime.now(timezone.utc)


def _iso(days_ago: int, hour: int) -> str:
    d = (NOW - timedelta(days=days_ago)).replace(hour=hour, minute=5, second=0, microsecond=0)
    return d.strftime("%Y-%m-%dT%H:%M:%S+0000")


IG_MEDIA = [{"id": f"m{i}", "caption": f"Post {i} #akola", "media_type": "CAROUSEL_ALBUM" if i % 3 == 0 else "VIDEO",
             "media_product_type": "FEED" if i % 3 == 0 else "REELS", "timestamp": _iso(i * 3, 13 if i % 2 else 7),
             "permalink": f"https://instagram.com/p/m{i}", "like_count": 100 - i * 5, "comments_count": 10 - i}
            for i in range(8)]


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    CALLS.append(req.method + " " + u.split("?")[0])
    q = parse_qs(urlparse(u).query)
    tok = (q.get("access_token") or [""])[0]
    if u.startswith("https://api.instagram.com/oauth/access_token"):
        body = parse_qs(req.content.decode())
        assert body["code"] == ["IGCODE"] and body["client_secret"] == ["igsecret"]
        return httpx.Response(200, json={"access_token": "IG_SHORT", "user_id": 1789, "permissions": "instagram_business_basic,instagram_business_manage_insights,instagram_business_content_publish"})
    if u.startswith("https://graph.instagram.com/access_token"):
        return httpx.Response(200, json={"access_token": "IG_LONG", "token_type": "bearer", "expires_in": 5184000})
    if u.startswith("https://graph.instagram.com/refresh_access_token"):
        return httpx.Response(200, json={"access_token": "IG_LONG2", "expires_in": 5184000})
    if u.startswith("https://graph.instagram.com/v25.0/me/media"):
        if STATE.get("ig_dead"):
            return httpx.Response(400, json={"error": {"message": "Error validating access token", "code": 190}})
        return httpx.Response(200, json={"data": IG_MEDIA})
    if u.startswith("https://graph.instagram.com/v25.0/me"):
        if STATE.get("ig_dead"):
            return httpx.Response(400, json={"error": {"message": "Error validating access token", "code": 190}})
        return httpx.Response(200, json={"user_id": "1789", "username": "sharmadental", "name": "Sharma Dental",
                                         "account_type": STATE.get("ig_type", "BUSINESS"), "followers_count": 2340,
                                         "media_count": 8, "profile_picture_url": "https://cdn.example/p.jpg"})
    if u.startswith("https://graph.instagram.com/v25.0/m") and "/insights" in u:
        mid = urlparse(u).path.split("/")[2]
        n = int(mid[1:])
        if "views" in q["metric"][0] and n == 5:
            return httpx.Response(400, json={"error": {"message": "metric views not supported", "code": 100}})
        vals = {"reach": 1000 - n * 50, "saved": 12 - n, "shares": 5, "views": 3000, "total_interactions": 120}
        return httpx.Response(200, json={"data": [{"name": m, "values": [{"value": vals[m]}]} for m in q["metric"][0].split(",")]})
    if u.startswith("https://graph.facebook.com/v25.0/oauth/access_token"):
        if "fb_exchange_token" in q:
            return httpx.Response(200, json={"access_token": "FB_USER_LONG", "expires_in": 5184000})
        assert q["code"] == ["FBCODE"] and q["client_secret"] == ["fbsecret"]
        return httpx.Response(200, json={"access_token": "FB_USER_SHORT"})
    if u.startswith("https://graph.facebook.com/v25.0/me/accounts"):
        return httpx.Response(200, json={"data": [{"id": "PAGE1", "name": "Sharma Dental Clinic", "access_token": "PAGE_TOK",
                                                   "category": "Dentist", "followers_count": 900}]})
    if u.startswith("https://graph.facebook.com/v25.0/me"):
        return httpx.Response(200, json={"id": "FBUSER9", "name": "Meghana"})
    if u.startswith("https://graph.facebook.com/v25.0/PAGE1/posts"):
        return httpx.Response(200, json={"data": [{"id": "PAGE1_p1", "message": "Free check-up camp", "created_time": _iso(2, 18),
                                                   "permalink_url": "https://fb.com/p1", "status_type": "added_photos",
                                                   "shares": {"count": 3}, "reactions": {"summary": {"total_count": 40}},
                                                   "comments": {"summary": {"total_count": 6}}}]})
    if u.startswith("https://graph.facebook.com/v25.0/PAGE1_p1/insights"):
        return httpx.Response(200, json={"data": [{"name": "post_impressions_unique", "values": [{"value": 800}]}]})
    return httpx.Response(500, text="unexpected " + u)


@pytest.fixture
def social(env, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.test")
    monkeypatch.setenv("INSTAGRAM_APP_ID", "igapp")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "igsecret")
    monkeypatch.setenv("META_APP_ID", "fbapp")
    monkeypatch.setenv("META_APP_SECRET", "fbsecret")
    monkeypatch.setenv("META_LOGIN_CONFIG_ID", "CFG1")
    monkeypatch.setenv("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.social import desk as D
    from app.social import meta as M
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    CALLS.clear()
    STATE.clear()
    yield D
    M.set_http(None)
    get_settings.cache_clear()


def _hire_and_setup(D):
    from app.employee import hire
    hire.hire(T, "social")
    D.onboard(T, business="Sharma Dental", city="Akola", sells="Root canal, implants", customers="families",
              goal="More WhatsApp enquiries", languages=["Hinglish"], trust="seekh")


def _state_from(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


FAKE = {"pillars": [{"name": "Smile stories", "why": "patients love results"}, {"name": "Tooth tips", "why": "saves"}],
        "rhythm": {"feed_per_week": 4, "stories_per_week": 3, "reels_share": 0.6}, "goal_metric": "WhatsApp enquiries",
        "hashtags": ["#akola", "dentist akola"], "best_hours": [13, 19],
        "posts": [{"date": None, "time": "13:00", "platforms": ["instagram", "facebook", "tiktok"], "format": "reel",
                   "pillar": "Smile stories", "hook": f"Hook {i}", "caption": f"Caption {i} [price]", "hashtags": ["akola", "#smile"],
                   "visual": "patient smiling", "cta": "WhatsApp us"} for i in range(10)]
        + [{"date": "1999-01-01", "caption": "out of range"}, {"date": None, "caption": ""}]}


# ---------------------------------------------------------------- tests
def test_hire_gate_and_setup(social):
    D = social
    from app.employee import hire
    cat = {c["key"]: c for c in hire.catalog(T)}
    assert cat["social"]["live"] and cat["social"]["never"]
    assert D.desk_view(T) == {"hired": False, "status": "none"}
    with pytest.raises(D.SocialError):
        D.connect_url(T, "instagram")                       # no desk work before hiring
    hire.hire(T, "social")
    v = D.desk_view(T)
    assert v["hired"] and not v["onboarded"] and v["connect"] == {"instagram": True, "facebook": True}
    with pytest.raises(D.SocialError):
        D.onboard(T, business="")
    D.onboard(T, business="Sharma Dental", city="Akola", languages=["Hinglish", "Marathi"], trust="saathi")
    v = D.desk_view(T)
    assert v["onboarded"] and v["profile"]["languages"] == ["Hinglish", "Marathi"] and v["trust"] == "saathi"
    assert D.due_jobs(T) == []                               # nothing runs until an account is connected


def test_connect_instagram_reads_posts_baseline_and_calendar(social):
    D = social
    _hire_and_setup(D)
    url = D.connect_url(T, "instagram")
    p = urlparse(url)
    qs = parse_qs(p.query)
    assert p.netloc == "www.instagram.com" and qs["client_id"] == ["igapp"]
    assert qs["redirect_uri"] == ["https://hoola.test/api/social/instagram/callback"]
    assert "instagram_business_content_publish" in qs["scope"][0]           # v0.355 Phase 2 asks to post too (her tap per post)
    st = _state_from(url)
    r = D.finish_link("instagram", "IGCODE#_", st, background=False)
    assert r["accounts"] == ["@sharmadental"]
    with pytest.raises(D.SocialError):
        D.finish_link("instagram", "IGCODE", st, background=False)           # a state works once
    acc = D.accounts(T)[0]
    assert acc["followers"] == 2340 and acc["status"] == "ok" and acc["expires_at"]
    with D.session() as s:
        row = s.get(D.SocialAccount, acc["id"])
        assert row.token_enc and "IG_LONG" not in row.token_enc                # sealed, never stored plain
    v = D.desk_view(T)
    b = v["baseline"]
    assert v["state"] == "ready" and v["calendar_status"] == "draft"
    assert b["posts_read"] == 8 and b["followers"] == 2340 and b["avg_reach"] > 0 and b["eng_rate"] > 0
    assert {f["fmt"] for f in b["formats"]} == {"reel", "carousel"} and b["top_posts"][0]["permalink"].endswith("m0")
    assert len(b["best_hours"]) >= 1
    cal = v["calendar"]
    assert 8 <= len(cal) <= 26 and all(c["status"] == "draft" and c["source"] == "rules" for c in cal)
    assert all(c["hashtags"] and c["caption"] and c["slot"][10] == "T" for c in cal)
    assert any(e["kind"] == "connect" for e in v["events"]) and any("calendar" in e["text"] for e in v["events"])


def test_personal_instagram_is_refused_with_the_switch_guide(social):
    D = social
    _hire_and_setup(D)
    STATE["ig_type"] = "PERSONAL"
    with pytest.raises(D.SocialError) as e:
        D.finish_link("instagram", "IGCODE", _state_from(D.connect_url(T, "instagram")), background=False)
    assert "professional" in str(e.value) and D.accounts(T) == []


def test_facebook_page_connects_with_config_id(social):
    D = social
    _hire_and_setup(D)
    url = D.connect_url(T, "facebook")
    qs = parse_qs(urlparse(url).query)
    assert url.startswith("https://www.facebook.com/v25.0/dialog/oauth") and qs["config_id"] == ["CFG1"] and "scope" not in qs
    r = D.finish_link("facebook", "FBCODE", _state_from(url), background=False)
    assert r["accounts"] == ["Sharma Dental Clinic"]
    acc = D.accounts(T)[0]
    assert acc["platform"] == "facebook" and acc["followers"] == 900
    b = D.desk_view(T)["baseline"]
    assert b["posts_read"] == 1 and b["avg_reach"] == 800 and b["top_posts"][0]["eng"] == 49


def test_opus_plan_cleaned_and_draft_replaced_but_approved_kept(social):
    D = social
    _hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", _state_from(D.connect_url(T, "instagram")), background=False)
    start = D._plan_inputs(T)["start"]
    fake = json.loads(json.dumps(FAKE))
    for i, p in enumerate(fake["posts"]):
        if p["date"] is None:
            p["date"] = (datetime.fromisoformat(start) + timedelta(days=i)).date().isoformat()
    asked = {}

    def opus(system, prompt, kind, images, timeout, **kw):
        asked.update(kind=kind, prompt=prompt, max_tokens=kw.get("max_tokens"))
        return fake
    first = D.calendar(T)[0]["id"]
    D.set_post(T, first, status="approved")
    r = D.build_plan(T, ask=opus)
    assert asked["kind"] == "social_plan" and "Sharma Dental" in asked["prompt"] and "NEVER invent prices" not in asked["prompt"]
    assert r["source"] == "opus" and r["posts"] == 10                          # junk / out-of-range slots dropped
    cal = D.calendar(T)
    assert any(c["id"] == first and c["status"] == "approved" for c in cal)   # her approval survives a re-plan
    opus_posts = [c for c in cal if c["source"] == "opus"]
    assert len(opus_posts) == 10 and all(c["platforms"] == ["instagram", "facebook"] for c in opus_posts)   # tiktok dropped
    assert opus_posts[0]["hashtags"] == ["#akola", "#smile"]
    stg = D.desk_view(T)["strategy"]
    assert stg["source"] == "opus" and stg["hashtags"][1] == "#dentistakola" and stg["pillars"][0]["name"] == "Smile stories"


def test_edit_after_approval_asks_again_and_approve_all(social):
    D = social
    _hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", _state_from(D.connect_url(T, "instagram")), background=False)
    pid = D.calendar(T)[0]["id"]
    assert D.set_post(T, pid, status="approved")["status"] == "approved"
    assert D.set_post(T, pid, caption="New words")["status"] == "draft"
    with pytest.raises(D.SocialError):
        D.set_post(T, pid, slot="tomorrow")
    n = D.approve_calendar(T)["approved"]
    assert n == len(D.calendar(T)) and D.desk_view(T)["calendar_status"] == "approved"


def test_dead_token_alerts_once_and_recovers(social):
    D = social
    _hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", _state_from(D.connect_url(T, "instagram")), background=False)
    aid = D.accounts(T)[0]["id"]
    STATE["ig_dead"] = True
    for _ in range(2):
        with pytest.raises(D.SocialError):
            D.sync_account(aid)
    ev = [e for e in D.desk_view(T)["events"] if e["kind"] == "alert"]
    assert len(ev) == 1 and "connect it again" in ev[0]["text"] and D.accounts(T)[0]["status"] == "expired"
    STATE["ig_dead"] = False
    D.sync_account(aid)
    assert D.accounts(T)[0]["status"] == "ok" and any(e["kind"] == "recovered" for e in D.desk_view(T)["events"])


def test_hourly_watch_renews_instagram_and_warns_facebook_once(social):
    D = social
    _hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", _state_from(D.connect_url(T, "instagram")), background=False)
    D.finish_link("facebook", "FBCODE", _state_from(D.connect_url(T, "facebook")), background=False)
    with D.session() as s:
        for a in s.scalars(D.select(D.SocialAccount)).all():
            a.connected_at = D.now() - timedelta(days=50)
            a.expires_at = D.now() + timedelta(days=5)
    r = D.watch(T)
    assert r == {"refreshed": 1, "warned": 1}
    assert D.watch(T)["warned"] == 0                                   # one warning, not one an hour
    ig = next(a for a in D.accounts(T) if a["platform"] == "instagram")
    assert datetime.fromisoformat(ig["expires_at"]) > D.now() + timedelta(days=50)


def test_scheduler_runs_jobs_on_her_clock(social):
    D = social
    _hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", _state_from(D.connect_url(T, "instagram")), background=False)
    ist = timezone(timedelta(hours=5, minutes=30))
    monday9 = datetime(2026, 11, 2, 9, 30, tzinfo=ist)
    jobs = {"publish", "inbox", "hourly", "daily", "weekly", "morning", "growth"}   # + v0.369 morning, v0.370 growth
    assert set(D.due_jobs(T, monday9)) == jobs
    done = D.run_due(at=monday9, force=True)
    assert {j for _, j in done} == jobs
    assert D.due_jobs(T, monday9 + timedelta(minutes=10)) == ["publish"]
    from app.employee import hire
    hire.pause(T, "social")
    assert D.run_due(at=monday9 + timedelta(hours=2), force=True) == []        # paused = no jobs
    assert any("best post" in e["text"] for e in D.desk_view(T)["events"])


def _signed(payload: dict, secret: str) -> str:
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), p.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{sig}.{p}"


def test_api_connect_callback_deletion_and_run(social):
    D = social
    from app import main
    from app.employee import hire
    with TestClient(main.app) as c:
        assert c.get("/api/social/desk").json() == {"hired": False, "status": "none"}
        hire.hire(T, "social")
        assert c.post("/api/social/onboard", json={"business": "Sharma Dental", "languages": "Hinglish, Hindi"}).json()["profile"]["languages"] == ["Hinglish", "Hindi"]
        assert c.post("/api/social/run/daily").status_code == 400                # nothing connected yet
        url = c.get("/api/social/connect/instagram").json()["url"]
        bad = c.get("/api/social/instagram/callback", params={"code": "x", "state": "soc_in_nope"})
        assert bad.status_code == 400 and "purana" in bad.text
        denied = c.get("/api/social/instagram/callback", params={"error": "access_denied", "error_reason": "user_denied"})
        assert denied.status_code == 400
        ok = c.get("/api/social/instagram/callback", params={"code": "IGCODE#_", "state": _state_from(url)})
        assert ok.status_code == 200 and "@sharmadental" in ok.text
        import time
        for _ in range(100):                                   # the first read runs in the background after connecting
            if D.desk_view(T)["state"] == "ready":
                break
            time.sleep(0.1)
        acc = D.accounts(T)[0]
        r = c.post("/api/social/meta/deletion", data={"signed_request": _signed({"user_id": "1789", "algorithm": "HMAC-SHA256"}, "wrong")})
        assert r.status_code == 400 and D.accounts(T)
        r = c.post("/api/social/meta/deletion", data={"signed_request": _signed({"user_id": "1789", "algorithm": "HMAC-SHA256"}, "igsecret")})
        js = r.json()
        assert r.status_code == 200 and js["confirmation_code"].startswith("hoola-") and js["url"].endswith(js["confirmation_code"])
        assert D.accounts(T) == [] and c.get(f"/api/social/meta/deletion/{js['confirmation_code']}").status_code == 200
        with D.session() as s:
            assert s.scalars(D.select(D.SocialMedia).where(D.SocialMedia.account == acc["id"])).first() is None
        assert c.post("/api/social/run/bogus").status_code == 404


def test_console_and_phone_are_wired():
    js = (ROOT / "server/app/static/console/employees.js").read_text()
    assert "/api/social/desk" in js and "/api/social/connect/" in js and "social(" in js and "/api/social/calendar/approve" in js
    v2 = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "socialdesk" in v2 and "hired.social" in v2
    html = (ROOT / "server/app/static/console/v2.html").read_text()
    assert 'id="v-socialdesk"' in html
    dart = (ROOT / "lib/ui/employees_screen.dart").read_text()
    assert "SocialDeskScreen" in dart and "socialDesk(" in dart
    api = (ROOT / "lib/api.dart").read_text()
    assert "/api/social/desk" in api and "/api/social/connect/" in api
    plan = (ROOT / "docs/SOCIAL_EMPLOYEE_PLAN.md").read_text()
    assert "Phase 1" in plan
