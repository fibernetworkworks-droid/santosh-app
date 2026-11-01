"""v0.370 SOCIAL MEDIA MANAGER Phase 5 - growth through the Facebook-Login link to her Instagram (hashtag search and
Business Discovery exist only there): posts that tag her -> UGC permission flow (ask = a comment from her account on her
tap, a recorded yes, then a credited DRAFT), up to 5 hashtags + 5 competitors read weekly against her numbers, a creator
check (public numbers + fake-follower signals + ASCI #ad), and A/B hook styles. Meta is a mock transport."""
import io
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from tests import test_v0353_social_manager as P1
from tests.test_v0353_social_manager import social  # noqa: F401  (the shared fixture)

T = "default"
SENT: list[tuple[str, dict]] = []
STATE: dict = {}
NOW = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S+0000")


def _jpeg() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (900, 900), (10, 120, 200)).save(b, "JPEG")
    return b.getvalue()


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    path = urlparse(u).path
    q = parse_qs(urlparse(u).query)
    if u.startswith("https://cdn.example/ugc.jpg"):
        return httpx.Response(200, content=_jpeg(), headers={"content-type": "image/jpeg"})
    if req.method == "GET" and path == "/v25.0/debug_token" and STATE.get("scopes") is not None:
        return httpx.Response(200, json={"data": {"scopes": STATE["scopes"]}})
    if req.method == "GET" and path == "/v25.0/PAGE1" and "instagram_business_account" in q.get("fields", [""])[0]:
        return httpx.Response(200, json={"instagram_business_account": {"id": "IGB1", "username": "sharmadental"}, "id": "PAGE1"})
    if req.method == "GET" and path == "/v25.0/IGB1/tags":
        return httpx.Response(200, json={"data": [
            {"id": "t1", "username": "happy_patient", "caption": "Best smile makeover @sharmadental!", "media_type": "IMAGE",
             "media_url": "https://cdn.example/ugc.jpg", "permalink": "https://instagram.com/p/t1", "timestamp": _iso(1), "like_count": 40},
            {"id": "t2", "username": "sharmadental", "caption": "own", "media_type": "IMAGE", "timestamp": _iso(1)}]})
    if req.method == "GET" and path == "/v25.0/ig_hashtag_search":
        assert q["user_id"] == ["IGB1"] and q["access_token"] == ["FB_USER_LONG"]   # hashtag search = the USER token
        STATE["hashtag_searches"] = STATE.get("hashtag_searches", 0) + 1
        return httpx.Response(200, json={"data": [{"id": "H_" + q["q"][0]}]})
    if req.method == "GET" and path.startswith("/v25.0/H_") and path.endswith("/top_media"):
        return httpx.Response(200, json={"data": [
            {"id": f"x{i}", "caption": f"Idea {i}\nmore", "media_type": "VIDEO" if i % 2 else "CAROUSEL_ALBUM", "like_count": 100 * i,
             "comments_count": 5, "permalink": f"https://instagram.com/p/x{i}", "timestamp": _iso(i)} for i in range(1, 5)]})
    if req.method == "GET" and path == "/v25.0/IGB1" and "business_discovery" in q.get("fields", [""])[0]:
        f = q["fields"][0]
        user = f.split("username(")[1].split(")")[0]
        if user == "notbiz":
            return httpx.Response(400, json={"error": {"message": "Invalid user id", "code": 110}})
        fol = {"rivaldental": 5000, "fakefame": 200000}.get(user, 1000)
        likes = 30000 if user == "fakefame" else 120
        comm = 10 if user == "fakefame" else 8
        f0 = STATE.get("follow_bump", 0) if user == "rivaldental" else 0
        return httpx.Response(200, json={"business_discovery": {"username": user, "name": user.title(), "followers_count": fol + f0,
                                                                "media_count": 300, "media": {"data": [
            {"id": f"{user}{i}", "caption": "x", "media_type": "VIDEO" if i < 3 else "IMAGE", "like_count": likes, "comments_count": comm,
             "timestamp": _iso(i * 2), "permalink": "https://instagram.com/p/z"} for i in range(6)]}}})
    if req.method == "POST" and path == "/v25.0/IGB1/mentions":
        f = {k: v[0] for k, v in parse_qs(req.content.decode()).items()}
        SENT.append(("mention", f))
        return httpx.Response(200, json={"id": "MC1"})
    return P1.handler(req)


@pytest.fixture
def gr(social, monkeypatch, tmp_path):
    from app.social import growth as G
    from app.social import meta as M
    monkeypatch.setenv("SOCIAL_DIR", str(tmp_path / "social"))
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    SENT.clear()
    STATE.clear()
    D = social
    P1._hire_and_setup(D)
    D.finish_link("facebook", "FBCODE", P1._state_from(D.connect_url(T, "facebook")), background=False)
    return D, G


def test_link_needs_the_facebook_page(social, monkeypatch):
    D = social
    from app.social import growth as G
    from app.social import meta as M
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    P1._hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    with pytest.raises(D.SocialError) as e:
        G.link(T)
    assert "Facebook Page" in str(e.value)
    assert G.listen(T)["ok"] is False
    assert G.view(T)["link"]["ok"] is False                 # the desk view never calls Meta


def test_page_without_instagram_permission_is_told_plainly(social, monkeypatch):
    D = social
    from app.social import growth as G
    from app.social import meta as M
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    STATE.clear()
    STATE["scopes"] = ["pages_show_list", "pages_read_engagement"]
    P1._hire_and_setup(D)
    D.finish_link("facebook", "FBCODE", P1._state_from(D.connect_url(T, "facebook")), background=False)
    with pytest.raises(D.SocialError) as e:
        G.link(T)
    assert "Reconnect Facebook Page" in str(e.value)


def test_tags_become_ugc_and_permission_flow(gr):
    D, G = gr
    r = G.listen(T, weekly=False)
    assert r["ok"] and r["ugc_new"] == 1                       # her own post is not UGC
    assert G.listen(T, weekly=False)["ugc_new"] == 0           # read once
    u = G.ugc_list(T)[0]
    assert u["username"] == "happy_patient" and u["status"] == "new"
    with pytest.raises(D.SocialError):
        G.ugc_repost(T, u["id"])                               # never without a recorded yes
    G.ugc_ask(T, u["id"])
    assert SENT[-1][0] == "mention" and SENT[-1][1]["media_id"] == "t1" and "@happy_patient" in SENT[-1][1]["message"]
    assert "YES" in SENT[-1][1]["message"]
    with pytest.raises(D.SocialError):
        G.ugc_permission(T, u["id"], True, "")                 # a yes needs their words
    G.ugc_permission(T, u["id"], True, "Commented 'YES go ahead' on 2 Nov")
    r = G.ugc_repost(T, u["id"])
    post = next(p for p in D.calendar(T) if p["id"] == r["post_id"])
    assert post["status"] == "draft" and "Credit: @happy_patient" in post["caption"] and len(post["media"]) == 1
    assert G.ugc_list(T)[0]["status"] == "reposted"
    assert any("tag you" in e["text"] for e in D.desk_view(T)["events"])


def test_watch_limits_and_weekly_read(gr):
    D, G = gr
    with pytest.raises(D.SocialError):
        G.set_watch(T, hashtags=["a1", "b2", "c3", "d4", "e5", "f6"])
    with pytest.raises(D.SocialError):
        G.set_watch(T, competitors=["bad name!"])
    G.set_watch(T, hashtags=["#akoladentist", "dentalcare", "akoladentist"], competitors=["@rivaldental", "notbiz"])
    w = G.watch_view(T)
    assert [h["name"] for h in w["hashtags"]] == ["akoladentist", "dentalcare"] and len(w["competitors"]) == 2
    r = G.listen(T, weekly=True)
    assert r["watched"] == 3 and any("notbiz" in e for e in r["errors"])
    w = G.watch_view(T)
    comp = next(c for c in w["competitors"] if c["name"] == "rivaldental")["last"]
    assert comp["followers"] == 5000 and comp["avg_eng"] == 128 and comp["posts_7d"] == 4 and comp["formats"][0]["posts"] == 3
    tag = w["hashtags"][0]["last"]
    assert tag["ideas"] and tag["ideas"][0]["line"] == "Idea 4" and tag["posts"] == 4
    assert next(c for c in w["competitors"] if c["name"] == "notbiz")["error"]
    STATE["follow_bump"] = 150
    G.listen(T, weekly=True)
    c2 = next(c for c in G.watch_view(T)["competitors"] if c["name"] == "rivaldental")
    assert c2["last"]["followers"] - c2["prev"]["followers"] == 150
    assert STATE["hashtag_searches"] == 2                       # hashtag ids cached: Meta counts unique searches a week
    G.listen(T, weekly=False)                                   # daily run: competitors are not re-read
    assert any(e["text"].startswith("Competitors:") for e in D.desk_view(T)["events"])


def test_creator_check_signals_and_ascii_ad(gr):
    D, G = gr
    ok = G.creator_check(T, "rivaldental")
    assert ok["followers"] == 5000 and ok["signals"] == [] and ok["eng_rate"] == 2.56
    bad = G.creator_check(T, "@fakefame", caption="Loved this clinic! Book now")
    assert bad["signals"] and "disclosure" in bad and "never a verdict" in bad["note"]
    with pytest.raises(D.SocialError):
        G.creator_check(T, "notbiz")


def test_ab_hook_styles_and_planner(gr):
    D, G = gr
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    styles = ["question"] * 3 + ["number"] * 3
    with D.session() as s:
        for i, st in enumerate(styles):
            s.add(D.SocialPost(tenant_id=T, slot=f"2026-10-{10 + i}T12:00", platforms="instagram", fmt="image", hook=f"h{i}",
                               caption="c", status="published", hook_style=st, result=json.dumps({"instagram": {"id": f"m{i}"}})))
        for m in s.scalars(D.select(D.SocialMedia).where(D.SocialMedia.tenant_id == T)).all():
            n = int(m.media_id[1:]) if m.media_id[1:].isdigit() else 9
            m.likes, m.comments, m.shares, m.saves = (300 if n < 3 else 50), 0, 0, 0
    r = G.ab_report(T)
    assert r["winner"] == "question" and {x["style"] for x in r["styles"]} == {"question", "number"}
    plan = D._rules_plan(D._plan_inputs(T))
    styles_used = [p["hook_style"] for p in plan["posts"] if p["hook_style"]]
    assert styles_used.count("question") > len(styles_used) / 3     # the winner leads the next calendar
    D.build_plan(T)
    assert any(p for p in D.calendar(T) if p["status"] == "draft")
    with D.session() as s:
        assert s.scalars(D.select(D.SocialPost.hook_style).where(D.SocialPost.status == "draft", D.SocialPost.hook_style.is_not(None))).first()


def test_scheduler_and_api(gr):
    D, G = gr
    ist = timezone(timedelta(hours=5, minutes=30))
    assert "growth" in D.due_jobs(T, datetime(2026, 11, 3, 8, 30, tzinfo=ist))
    assert "growth" not in D.due_jobs(T, datetime(2026, 11, 3, 7, 30, tzinfo=ist))
    from app import main
    with TestClient(main.app) as c:
        assert c.post("/api/social/growth/watch", json={"competitors": ["rivaldental"], "hashtags": ["dentalcare"]}).status_code == 200
        assert c.post("/api/social/growth/watch", json={"competitors": ["x y"]}).status_code == 400
        G.listen(T, weekly=True)
        v = c.get("/api/social/desk").json()["growth"]
        assert v["link"]["ok"] and v["link"]["username"] == "sharmadental" and v["watch"]["competitors"][0]["last"]["followers"] == 5000
        uid = v["ugc"][0]["id"]
        assert c.post(f"/api/social/ugc/{uid}/repost").status_code == 400
        assert c.post(f"/api/social/ugc/{uid}/ask", json={}).json()["status"] == "asked"
        assert c.post(f"/api/social/ugc/{uid}/permission", json={"granted": False}).json()["status"] == "refused"
        assert c.post(f"/api/social/ugc/{uid}/ignore").json()["status"] == "ignored"
        assert c.post(f"/api/social/ugc/{uid}/nope").status_code == 404
        assert c.post("/api/social/creator/check", json={"username": "rivaldental"}).json()["followers"] == 5000
        assert c.post("/api/social/run/growth").status_code == 200


def test_console_phone_privacy_wired():
    root = P1.ROOT
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "/api/social/growth/watch" in js and "data-ugask" in js and "/api/social/creator/check" in js and "Hook styles" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "socialUgc(" in dart and "Make a credited draft" in dart and "Check a creator" in dart
    assert "/api/social/ugc/$id/$action" in (root / "lib/api.dart").read_text()
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "never logs in as anyone else" in pv
    from app.social import meta as M
    assert {"instagram_basic", "instagram_manage_insights", "instagram_manage_comments"} <= set(M.FB_SCOPES)
