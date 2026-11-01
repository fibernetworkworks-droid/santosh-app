"""v0.392 SOCIAL MEDIA MANAGER - YouTube on the Social Desk (plan Y1): her channel (Hoola's YouTube sign-in) shows as an
account with subscribers + videos in the numbers; a calendar Reel / Video with YouTube ticked uploads as a Short / video
exactly as approved (title, description, tags, made-for-kids answer, thumbnail, playlist); Google's "private until audit"
answer is told in plain words; a Hoola-wide daily upload guard; YouTube comments in the Social Inbox (reply, hide = held
for review, never deleted). Google is a mock transport."""
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
CALLS: list[tuple[str, str, object]] = []
STATE: dict = {}
NOW = datetime.now(timezone.utc)


def _iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def yt_handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    path = urlparse(u).path
    q = parse_qs(urlparse(u).query)
    assert req.headers.get("authorization") == "Bearer YT_ACCESS"
    if path == "/youtube/v3/channels":
        return httpx.Response(200, json={"items": [{"id": "UCsharma", "snippet": {"title": "Sharma Dental", "customUrl": "@sharmadental"},
                                                    "statistics": {"subscriberCount": "1500", "videoCount": "2", "viewCount": "9000"},
                                                    "contentDetails": {"relatedPlaylists": {"uploads": "UUsharma"}}}]})
    if path == "/youtube/v3/playlistItems" and req.method == "GET":
        return httpx.Response(200, json={"items": [{"contentDetails": {"videoId": "v1short"}}, {"contentDetails": {"videoId": "v2long"}}]})
    if path == "/youtube/v3/videos" and req.method == "GET":
        return httpx.Response(200, json={"items": [
            {"id": "v1short", "snippet": {"title": "Smile in 30 sec", "publishedAt": "2026-10-25T10:00:00Z"},
             "statistics": {"viewCount": "4000", "likeCount": "300", "commentCount": "20"}, "contentDetails": {"duration": "PT45S"},
             "status": {"privacyStatus": "public"}},
            {"id": "v2long", "snippet": {"title": "Root canal explained", "publishedAt": "2026-10-20T10:00:00Z"},
             "statistics": {"viewCount": "5000", "likeCount": "100", "commentCount": "12"}, "contentDetails": {"duration": "PT10M2S"},
             "status": {"privacyStatus": "public"}}]})
    if path == "/upload/youtube/v3/videos" and req.method == "POST":
        body = json.loads(req.content)
        CALLS.append(("upload_meta", "", body))
        return httpx.Response(200, headers={"location": "https://upload.example/session1"})
    if u.startswith("https://upload.example/session1"):
        CALLS.append(("upload_bytes", "", len(req.content)))
        return httpx.Response(200, json={"id": "NEWVID", "status": {"privacyStatus": STATE.get("forced", "public")}})
    if path == "/upload/youtube/v3/thumbnails/set":
        CALLS.append(("thumb", q["videoId"][0], len(req.content)))
        return httpx.Response(200, json={})
    if path == "/youtube/v3/playlistItems" and req.method == "POST":
        CALLS.append(("playlist", "", json.loads(req.content)))
        return httpx.Response(200, json={"id": "pli1"})
    if path == "/youtube/v3/commentThreads":
        assert q["allThreadsRelatedToChannelId"] == ["UCsharma"]
        def th(cid, who, text, hrs, chan="UCother"):
            return {"id": cid, "snippet": {"videoId": "v1short", "totalReplyCount": 0, "topLevelComment": {"id": cid, "snippet": {
                "authorDisplayName": who, "authorChannelId": {"value": chan}, "textOriginal": text, "publishedAt": _iso(hrs)}}}}
        return httpx.Response(200, json={"items": [th("yc1", "@ravi", "Implant ka price kitna hai?", 2), th("yc2", "@neha", "Wow superb 😍", 3),
                                                   th("yc3", "@sharmadental", "Thanks all", 1, "UCsharma"),
                                                   th("yc4", "@bot", "Free followers www.spam.example", 1)]})
    if path == "/youtube/v3/comments" and req.method == "POST":
        CALLS.append(("reply", "", json.loads(req.content)))
        return httpx.Response(200, json={"id": "yr1"})
    if path == "/youtube/v3/comments/setModerationStatus":
        CALLS.append(("moderate", q["id"][0], q["moderationStatus"][0]))
        return httpx.Response(204)
    return httpx.Response(404, json={"error": {"message": f"unhandled {path}"}})


@pytest.fixture
def ytd(social, monkeypatch, tmp_path):
    for k, v in {"GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("SOCIAL_DIR", str(tmp_path / "social"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app import accounts as acc
    from app.db import session
    from app.mailbox import accounts as ma
    from app.youtube.models import YouTubeAccount
    ma.set_http(httpx.Client(transport=httpx.MockTransport(yt_handler)))
    CALLS.clear()
    STATE.clear()
    D = social
    P1._hire_and_setup(D)
    with session() as s:
        s.add(YouTubeAccount(id="gyt_1", tenant_id=T, address="sharma@example.in", channel_id="UCsharma", channel_title="Sharma Dental",
                             is_default=True, access_token_enc=acc.encrypt("YT_ACCESS"), refresh_token_enc=acc.encrypt("R"),
                             expiry=D.now() + timedelta(hours=1)))
    yield D
    ma.set_http(None)


def _jpeg() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1280, 720), (200, 30, 30)).save(b, "JPEG")
    return b.getvalue()


MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 4000


def _yt_account(D):
    return next(a for a in D.desk_view(T)["accounts"] if a["platform"] == "youtube")


def test_channel_shows_and_numbers_are_read(ytd):
    D = ytd
    a = _yt_account(D)
    assert a["name"] == "Sharma Dental" and a["can_post"] and a["can_reply"] is None
    assert D.desk_view(T)["connect"]["youtube"] is True
    D.sync_account(a["id"])
    a = _yt_account(D)
    assert a["followers"] == 1500 and a["handle"] == "@sharmadental"
    with D.session() as s:
        ms = {m.media_id: m for m in s.scalars(D.select(D.SocialMedia).where(D.SocialMedia.platform == "youtube")).all()}
    assert ms["v1short"].fmt == "reel" and ms["v2long"].fmt == "video" and ms["v1short"].views == 4000
    assert D.measure(T)["followers"] >= 1500


def _yt_post(D, SP, fmt="reel", with_thumb=True):
    a = SP.add_asset(T, MP4, "clip.mp4")
    media = [a["id"]] + ([SP.add_asset(T, _jpeg(), "t.jpg")["id"]] if with_thumb else [])
    with D.session() as s:
        p = D.SocialPost(tenant_id=T, slot="2026-11-08T12:00", platforms="youtube", fmt=fmt, hook="Dant chamkao 3 tips mein",
                         caption="Teen aasaan tips.\nDetails ke liye call kijiye.", hashtags=json.dumps(["#dental", "#akola", "#smile", "#tips"]),
                         status="draft", media=json.dumps(media))
        s.add(p)
        s.flush()
        return p.id


def test_short_uploads_as_approved_with_kids_answer_thumbnail_playlist(ytd):
    D = ytd
    from app.social import publish as SP
    from app.social import pulse as PU
    D.desk_view(T)                                              # mirror the channel
    pid = _yt_post(D, SP)
    with D.session() as s:
        assert "bachchon" in " ".join(SP.problems(s.get(D.SocialPost, pid)))    # YouTube requires the made-for-kids answer
    PU.set_settings(T, yt_kids=False, yt_playlist="PLabcdefghij12")
    with pytest.raises(D.SocialError):
        PU.set_settings(T, yt_playlist="not a playlist")
    r = SP.publish_post(T, pid, by_tap=True)
    assert r["status"] == "published" and r["results"]["youtube"]["link"] == "https://www.youtube.com/shorts/NEWVID"
    meta = next(c[2] for c in CALLS if c[0] == "upload_meta")
    assert meta["snippet"]["title"] == "Dant chamkao 3 tips mein #Shorts"
    assert meta["snippet"]["tags"] == ["dental", "akola", "smile", "tips"] and "#dental #akola #smile" in meta["snippet"]["description"]
    assert meta["status"] == {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True}
    assert next(c for c in CALLS if c[0] == "upload_bytes")[2] == len(MP4)
    assert next(c for c in CALLS if c[0] == "thumb")[1] == "NEWVID"
    assert next(c for c in CALLS if c[0] == "playlist")[2]["snippet"]["playlistId"] == "PLabcdefghij12"
    assert "note" not in r["results"]["youtube"]


def test_private_until_audit_is_told_and_long_video_link(ytd):
    D = ytd
    from app.social import publish as SP
    from app.social import pulse as PU
    D.desk_view(T)
    PU.set_settings(T, yt_kids=True)
    STATE["forced"] = "private"
    pid = _yt_post(D, SP, fmt="video", with_thumb=False)
    r = SP.publish_post(T, pid, by_tap=True)
    yt = r["results"]["youtube"]
    assert yt["link"] == "https://www.youtube.com/watch?v=NEWVID" and "PRIVATE" in yt["note"] and "YouTube Studio" in yt["note"]
    meta = next(c[2] for c in CALLS if c[0] == "upload_meta")
    assert meta["snippet"]["title"] == "Dant chamkao 3 tips mein" and meta["status"]["selfDeclaredMadeForKids"] is True


def test_youtube_needs_a_video_and_daily_guard(ytd, monkeypatch):
    D = ytd
    from app.social import publish as SP
    from app.social import pulse as PU
    D.desk_view(T)
    PU.set_settings(T, yt_kids=False)
    with D.session() as s:
        img = D.SocialPost(tenant_id=T, slot="2026-11-08T12:00", platforms="youtube", fmt="image", hook="x", caption="x", status="draft")
        s.add(img)
        s.flush()
        assert "sirf video" in " ".join(SP.problems(img))
    monkeypatch.setenv("YT_DAILY_UPLOADS", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    assert SP.publish_post(T, _yt_post(D, SP), by_tap=True)["status"] == "published"
    r = SP.publish_post(T, _yt_post(D, SP), by_tap=True)
    assert r["status"] == "failed" and "seema" in r["results"]["youtube"]["error"]


def test_youtube_comments_in_social_inbox(ytd):
    D = ytd
    from app.social import inbox as IB
    D.desk_view(T)
    D.sync_account(_yt_account(D)["id"])
    st = IB.run_inbox(T)
    assert st["new"] == 3                                        # her own channel's comment skipped
    items = {i["text"][:10]: i for i in IB.view(T)["items"]}
    assert items["Implant ka"]["cls"] == "lead" and items["Implant ka"]["platform"] == "youtube"
    assert items["Implant ka"]["permalink"] == "https://www.youtube.com/watch?v=v1short&lc=yc1"
    assert not any(c[0] in ("reply", "moderate") for c in CALLS)     # Seekh: nothing goes alone
    IB.reply(T, items["Implant ka"]["id"], "Ji, details DM / call par.")
    assert next(c for c in CALLS if c[0] == "reply")[2] == {"snippet": {"parentId": "yc1", "textOriginal": "Ji, details DM / call par."}}
    IB.hide(T, items["Free follo"]["id"], True)
    assert ("moderate", "yc4", "heldForReview") in CALLS          # held for review, never rejected / deleted
    IB.hide(T, items["Free follo"]["id"], False)
    assert ("moderate", "yc4", "published") in CALLS
    assert IB.run_inbox(T)["new"] == 0


def test_planner_disconnect_and_routes(ytd):
    D = ytd
    D.desk_view(T)
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    plan = D._rules_plan(D._plan_inputs(T))
    reels = [p for p in plan["posts"] if p["format"] == "reel"]
    assert reels and all("youtube" in p["platforms"] for p in reels)
    assert all("youtube" not in p["platforms"] for p in plan["posts"] if p["format"] != "reel")
    from app import main
    with TestClient(main.app) as c:
        assert c.post("/api/social/settings", json={"yt_kids": False}).json()["yt_kids"] is False
        assert c.post("/api/social/settings", json={"yt_playlist": "bad id"}).status_code == 400
        url = c.get("/api/social/connect/youtube").json()["url"]
        assert "youtube.upload" in httpx.URL(url).params["scope"]
    D.disconnect(T, _yt_account(D)["id"])
    from app.youtube import accounts as YA
    assert YA.clients(T) == [] and not any(a["platform"] == "youtube" for a in D.desk_view(T)["accounts"])


def test_console_phone_privacy_wired():
    root = P1.ROOT
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "youtube: 'YouTube'" in js and "data-scyt" in js and "scKids" in js and "Also as YouTube Short" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "'youtube': 'YouTube'" in dart and "Also as YouTube Short" in dart and "yt_kids" in dart
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "YouTube: if you connect your YouTube channel" in pv and "Limited Use" in pv
