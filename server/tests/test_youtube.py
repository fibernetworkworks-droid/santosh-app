"""Santosh YouTube: search / stats / channels / comments on the official Data API, Gemini watching a video, the user's
channel (videos, analytics, playlists), reply / edit / upload behind confirm cards, and YouTube in Santosh Notebook."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.youtube.models  # noqa: F401
from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_life import conv_ctx

ME = "meghana@fnw.in"
MY_CH = "UC" + "m" * 22
OTHER_CH = "UC" + "o" * 22


def _vid(i, ch=OTHER_CH, views=1000, title=None):
    return {"id": i, "snippet": {"title": title or f"Video {i}", "channelTitle": "FNW Academy" if ch == MY_CH else "Tech Guru",
                                 "channelId": ch, "publishedAt": "2026-10-01T10:00:00Z", "description": "About fiber",
                                 "categoryId": "28", "tags": ["fiber"], "thumbnails": {"high": {"url": f"https://i.ytimg.com/{i}.jpg"}}},
            "statistics": {"viewCount": str(views), "likeCount": "50", "commentCount": "7"},
            "contentDetails": {"duration": "PT12M5S"}, "status": {"privacyStatus": "public"}}


class FakeYT:
    def __init__(self):
        self.videos = {"aaaaaaaaaaa": _vid("aaaaaaaaaaa", views=250000, title="GPON basics in Hindi"),
                       "bbbbbbbbbbb": _vid("bbbbbbbbbbb", views=1200),
                       "mmmmmmmmmmm": _vid("mmmmmmmmmmm", MY_CH, views=4300, title="FNW Flow demo")}
        self.calls = []
        self.posted = []
        self.put = []
        self.uploaded = None

    def __call__(self, req: httpx.Request):
        u, p = req.url, req.url.params
        try:
            body = json.loads(req.content) if req.content and req.headers.get("content-type", "").startswith("application/json") else None
        except ValueError:
            body = None
        self.calls.append((req.method, u.path, dict(p)))
        if u.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/youtube.force-ssl "
                                                      "https://www.googleapis.com/auth/yt-analytics.readonly"})
        if u.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        authed = req.headers.get("authorization") == "Bearer at"
        assert authed or p.get("key") == "yt-key", (u.path, dict(p))
        path = u.path.removeprefix("/youtube/v3")
        if u.host == "youtubeanalytics.googleapis.com":
            assert authed and p["ids"] == "channel==MINE"
            if p.get("dimensions") == "video":
                return httpx.Response(200, json={"columnHeaders": [{"name": "video"}, {"name": "views"}],
                                                 "rows": [["mmmmmmmmmmm", 4300]]})
            return httpx.Response(200, json={"columnHeaders": [{"name": "views"}, {"name": "subscribersGained"}], "rows": [[5200, 31]]})
        if u.path.startswith("/upload/youtube/v3/videos"):
            if req.method == "POST":
                assert p["uploadType"] == "resumable"
                self.uploaded = {"meta": json.loads(req.content)}
                return httpx.Response(200, headers={"location": "https://www.googleapis.com/upload/youtube/v3/videos?upload_id=x1"})
            self.uploaded["bytes"] = req.content
            return httpx.Response(200, json={"id": "nnnnnnnnnnn"})
        if path == "/search":
            if p["type"] == "channel":
                return httpx.Response(200, json={"items": [{"id": {"channelId": OTHER_CH}}]})
            items = [{"id": {"videoId": k}} for k, v in self.videos.items() if p["q"].lower() in v["snippet"]["title"].lower() or p["q"] == "*"]
            assert p["regionCode"] == "IN"
            return httpx.Response(200, json={"items": items})
        if path == "/videos" and req.method == "GET":
            ids = p["id"].split(",")
            return httpx.Response(200, json={"items": [self.videos[i] for i in ids if i in self.videos]})
        if path == "/videos" and req.method == "PUT":
            self.put.append(json.loads(req.content))
            return httpx.Response(200, json=json.loads(req.content))
        if path == "/channels":
            cid = MY_CH if p.get("mine") == "true" else (p.get("id") or OTHER_CH)
            assert p.get("mine") != "true" or authed
            subs = "1500" if cid == MY_CH else "2500000"
            return httpx.Response(200, json={"items": [{"id": cid, "snippet": {"title": "FNW Academy" if cid == MY_CH else "Tech Guru",
                                                                                "customUrl": "@x", "publishedAt": "2020-01-01T00:00:00Z"},
                                                        "statistics": {"subscriberCount": subs, "videoCount": "40", "viewCount": "9000000"},
                                                        "contentDetails": {"relatedPlaylists": {"uploads": "UU" + cid[2:]}}}]})
        if path == "/playlistItems" and req.method == "GET":
            mine = p["playlistId"] == "UU" + MY_CH[2:]
            ids = ["mmmmmmmmmmm"] if mine else ["aaaaaaaaaaa", "bbbbbbbbbbb"]
            return httpx.Response(200, json={"items": [{"contentDetails": {"videoId": i}} for i in ids]})
        if path == "/commentThreads":
            return httpx.Response(200, json={"items": [{"snippet": {"totalReplyCount": 0, "topLevelComment": {"id": "c1", "snippet": {
                "authorDisplayName": "Ramesh", "textDisplay": "Price kya hai?", "likeCount": 3, "publishedAt": "2026-10-10T00:00:00Z"}}}}]})
        if path == "/comments" and req.method == "GET":
            return httpx.Response(200, json={"items": [{"id": "c1", "snippet": {"authorDisplayName": "Ramesh", "textDisplay": "Price kya hai?"}}]})
        if path in ("/comments", "/playlists", "/playlistItems") and req.method == "POST":
            assert authed
            self.posted.append((path, json.loads(req.content)))
            if path == "/playlists":
                return httpx.Response(200, json={"id": "PL1", "snippet": json.loads(req.content)["snippet"],
                                                 "status": json.loads(req.content)["status"]})
            return httpx.Response(200, json={"id": "new"})
        if path == "/playlists":
            return httpx.Response(200, json={"items": [{"id": "PL1", "snippet": {"title": "Training"}, "status": {"privacyStatus": "private"},
                                                        "contentDetails": {"itemCount": 2}}]})
        return httpx.Response(404, json={"error": {"message": f"unhandled {path}"}})


@pytest.fixture
def yt(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec", "YOUTUBE_API_KEY": "yt-key"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    fake = FakeYT()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    yield fake
    ma.set_http(None)


def _connect():
    from app import main
    with TestClient(main.app) as c:
        url = c.get("/api/youtube/link").json()["url"]
        assert "youtube.force-ssl" in httpx.URL(url).params["scope"] and "state=gyt_" in url
        page = c.get("/auth/google/callback", params={"code": "c", "state": httpx.URL(url).params["state"]})
        assert page.status_code == 200 and "FNW Academy" in page.text
        st = c.get("/api/youtube/accounts").json()
        assert st["accounts"][0]["channel"] == "FNW Academy" and st["public_search"]


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def test_search_video_channel_comments_with_api_key(yt):
    ctx = conv_ctx()
    out = run("youtube_search", {"query": "gpon"}, ctx)
    v = out["videos"][0]
    assert v["title"] == "GPON basics in Hindi" and v["views_text"] == "2.5 lakh" and v["duration"] == "12:05"
    card = _events(ctx.conversation_id, "youtube")[-1]
    assert card["items"][0]["url"] == "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    det = run("youtube_video", {"videos": ["https://youtu.be/bbbbbbbbbbb"]}, ctx)
    assert det["videos"][0]["likes"] == 50
    ch = run("youtube_channel", {"channel": "Tech Guru"}, ctx)
    assert ch["subscribers_text"] == "25.0 lakh" and len(ch["latest_videos"]) == 2
    com = run("youtube_comments", {"video": "aaaaaaaaaaa"}, ctx)
    assert com["comments"][0] == {"id": "c1", "author": "Ramesh", "text": "Price kya hai?", "likes": 3, "replies": 0, "when": "2026-10-10"}
    assert all(c[2].get("key") == "yt-key" for c in yt.calls if "/youtube/v3" in c[1])      # public calls use the API key


def test_watch_uses_gemini(yt, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.youtube import service as ys
    seen = {}
    monkeypatch.setattr(ys, "gemini_video", lambda url, prompt: seen.update(url=url, prompt=prompt) or "[02:10] Splitter 1:32 ...")
    out = run("youtube_watch", {"video": "https://www.youtube.com/watch?v=aaaaaaaaaaa", "question": "splitter ratio?"}, conv_ctx())
    assert out["answer"].startswith("[02:10]") and seen["url"].endswith("aaaaaaaaaaa") and "splitter ratio?" in seen["prompt"]
    assert out["video"] == "GPON basics in Hindi"


def test_watch_needs_gemini_key(yt):
    with pytest.raises(ToolError, match="GEMINI_API_KEY"):
        run("youtube_watch", {"video": "aaaaaaaaaaa"}, conv_ctx())


def test_my_channel_analytics_and_playlists(yt):
    _connect()
    ctx = conv_ctx()
    me = run("youtube_my_channel", {}, ctx)
    assert me["title"] == "FNW Academy" and me["latest_videos"][0]["title"] == "FNW Flow demo"
    a = run("youtube_analytics", {"days": 7}, ctx)
    assert a["rows"] == [{"views": 5200, "subscribersGained": 31}]
    top = run("youtube_analytics", {"by": "video"}, ctx)
    assert top["rows"][0]["title"] == "FNW Flow demo"
    pl = run("youtube_playlist", {"action": "create", "title": "Client demos"}, ctx)
    assert pl["privacy"] == "private"
    add = run("youtube_playlist", {"action": "add", "playlist": "training", "videos": ["aaaaaaaaaaa"]}, ctx)
    assert add["added"] == 1


def test_reply_edit_upload_need_the_tap(bz, yt):  # noqa: F811
    _connect()
    ctx = Ctx("default", bz["conv"])
    run("youtube_reply", {"comment_id": "c1", "text": "Namaste Ramesh ji, price Rs 999 hai."}, ctx)
    assert not any(p[0] == "/comments" for p in yt.posted)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Comment ka jawab post karein?" and "Price kya hai?" in json.dumps(card)
    bz["svc"].decide("default", card["id"], "approve")
    assert yt.posted[-1] == ("/comments", {"snippet": {"parentId": "c1", "textOriginal": "Namaste Ramesh ji, price Rs 999 hai."}})
    with pytest.raises(ToolError, match="aapke channel ka nahi"):
        run("youtube_update_video", {"video": "aaaaaaaaaaa", "title": "x"}, ctx)
    run("youtube_update_video", {"video": "mmmmmmmmmmm", "title": "FNW Flow demo 2026", "privacy": "unlisted"}, ctx)
    assert yt.put == []
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert yt.put[0]["snippet"]["title"] == "FNW Flow demo 2026" and yt.put[0]["snippet"]["categoryId"] == "28"
    assert yt.put[0]["status"]["privacyStatus"] == "unlisted"
    from app.mailbox import service as ms
    f = ms.store_bytes("default", "demo.mp4", b"\x00\x00\x00\x18ftypmp42video", "mail")
    run("youtube_upload", {"file_id": f.id, "title": "Demo", "description": "FNW Flow"}, ctx)
    assert yt.uploaded is None
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert yt.uploaded["meta"]["status"]["privacyStatus"] == "private" and yt.uploaded["bytes"].startswith(b"\x00\x00\x00\x18ftyp")


def test_notebook_gets_video_notes(env, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.notebook import ingest
    from app.youtube import service as ys
    ingest.set_http(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"title": "OLT setup", "author_name": "FNW"}))))
    monkeypatch.setattr(ys, "notes_for_notebook", lambda url: "[00:30] Step 1: login to OLT\n[02:00] Step 2: add ONU")
    try:
        got = ingest.from_web("https://youtu.be/aaaaaaaaaaa")
    finally:
        ingest.set_http(None)
    assert got["kind"] == "youtube" and "Step 2: add ONU" in got["text"] and "Gemini" in got["note"]


def test_nothing_configured(env):
    with pytest.raises(ToolError, match="YOUTUBE_API_KEY"):
        run("youtube_search", {"query": "x"}, Ctx("someone", "c"))
    with pytest.raises(ToolError, match="Profile > YouTube"):
        run("youtube_my_channel", {}, Ctx("someone", "c"))
