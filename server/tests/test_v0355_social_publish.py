"""v0.355 SOCIAL MEDIA MANAGER Phase 2: a calendar post goes out to Instagram and / or her Facebook Page - only the exact post
she approved (hash of caption + hashtags + pictures + platforms + format + time), at its time or on her Publish now tap.
Pictures: her upload (bytes checked, kept as JPEG) or a Brand poster; Meta fetches them from a short-lived signed link.
Instagram: image / carousel / Reel (container processed, polled) / Story, the 24-hour API post cap read first, the publish
permission checked; Facebook: photo / several photos / video / text. Missed (> 1 day late) is never posted late."""
import io
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from tests import test_v0353_social_manager as P1
from tests.test_v0353_social_manager import social  # noqa: F401  (the shared fixture)

T = "default"
LOG: list[tuple[str, dict]] = []
IGS: dict = {}


def _form(req) -> dict:
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()} if req.content else {}


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    path = urlparse(u).path
    if req.method == "POST" and path.endswith("/1789/media"):
        f = _form(req)
        LOG.append(("ig_container", f))
        IGS["n"] = IGS.get("n", 0) + 1
        return httpx.Response(200, json={"id": f"C{IGS['n']}"})
    if req.method == "GET" and path.endswith("/1789/content_publishing_limit"):
        return httpx.Response(200, json={"data": [{"quota_usage": IGS.get("used", 3), "config": {"quota_total": 50}}]})
    if req.method == "GET" and "/C" in path and "status_code" in u:
        IGS["polls"] = IGS.get("polls", 0) + 1
        return httpx.Response(200, json={"status_code": "IN_PROGRESS" if IGS["polls"] < 3 else "FINISHED"})
    if req.method == "POST" and path.endswith("/1789/media_publish"):
        LOG.append(("ig_publish", _form(req)))
        return httpx.Response(200, json={"id": "IGM9"})
    if req.method == "GET" and path.endswith("/IGM9"):
        return httpx.Response(200, json={"permalink": "https://www.instagram.com/p/IGM9/"})
    if req.method == "POST" and path.endswith("/PAGE1/photos"):
        f = _form(req)
        LOG.append(("fb_photo", f))
        if f.get("published") == "false":
            return httpx.Response(200, json={"id": f"PH{len(LOG)}"})
        return httpx.Response(200, json={"id": "PH1", "post_id": "PAGE1_77"})
    if req.method == "POST" and path.endswith("/PAGE1/feed"):
        LOG.append(("fb_feed", _form(req)))
        return httpx.Response(200, json={"id": "PAGE1_88"})
    if req.method == "POST" and path.endswith("/PAGE1/videos"):
        LOG.append(("fb_video", _form(req)))
        return httpx.Response(200, json={"id": "V1"})
    if req.method == "GET" and (path.endswith("/PAGE1_77") or path.endswith("/PAGE1_88") or path.endswith("/V1")):
        return httpx.Response(200, json={"permalink_url": "https://facebook.com/" + path.rsplit("/", 1)[-1]})
    return P1.handler(req)


@pytest.fixture
def pub(social, monkeypatch, tmp_path):
    from app.social import meta as M
    from app.social import publish as SP
    monkeypatch.setenv("SOCIAL_DIR", str(tmp_path / "social"))
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(M, "_sleep", lambda s: None)
    LOG.clear()
    IGS.clear()
    D = social
    P1._hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    D.finish_link("facebook", "FBCODE", P1._state_from(D.connect_url(T, "facebook")), background=False)
    return D, SP


def _jpeg(w=1080, h=1350, color=(200, 80, 40)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, "PNG")          # PNG on purpose: stored as JPEG
    return b.getvalue()


MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2000


def _post(D, fmt="image", platforms="instagram,facebook", caption="Smile bright this Diwali! Call us.", slot=None):
    with D.session() as s:
        p = D.SocialPost(tenant_id=T, slot=slot or "2026-11-08T12:00", platforms=platforms, fmt=fmt, pillar="Our work",
                         hook="Smile bright", caption=caption, hashtags=json.dumps(["#akola", "#smile"]), status="draft")
        s.add(p)
        s.flush()
        return p.id


# ---------------------------------------------------------------- tests
def test_assets_checked_kept_as_jpeg_and_signed_links(pub):
    D, SP = pub
    a = SP.add_asset(T, _jpeg(2000, 2500), "photo.png")
    assert a["kind"] == "image" and a["width"] == 1440 and a["height"] == 1800
    with D.session() as s:
        row = s.get(SP.SocialAsset, a["id"])
        assert row.path.endswith(".jpg") and open(row.path, "rb").read(2) == b"\xff\xd8"
    v = SP.add_asset(T, MP4, "clip.mp4")
    assert v["kind"] == "video"
    with pytest.raises(D.SocialError):
        SP.add_asset(T, b"%PDF-1.7 not a picture", "x.jpg")
    from app import main
    with TestClient(main.app) as c:
        q = parse_qs(urlparse(a["url"]).query)
        ok = c.get(f"/api/social/media/{a['id']}", params={"e": q["e"][0], "s": q["s"][0]})
        assert ok.status_code == 200 and ok.headers["content-type"] == "image/jpeg"
        assert c.get(f"/api/social/media/{a['id']}", params={"e": q["e"][0], "s": "0" * 32}).status_code == 404
        old = int(time.time()) - 10
        assert c.get(f"/api/social/media/{a['id']}", params={"e": old, "s": SP._sig(a["id"], old)}).status_code == 404


def test_problems_and_approval_bound_to_exact_post(pub):
    D, SP = pub
    pid = _post(D)
    with D.session() as s:
        assert "Instagram ke liye photo" in " ".join(SP.problems(s.get(D.SocialPost, pid)))
    a = SP.add_asset(T, _jpeg())
    SP.attach(T, pid, [a["id"]])
    D.set_post(T, pid, status="approved")
    SP.attach(T, pid, [SP.add_asset(T, _jpeg(color=(1, 2, 3)))["id"]])            # a change after her OK ...
    assert D.calendar(T) and next(p for p in D.calendar(T) if p["id"] == pid)["status"] == "draft"   # ... needs her OK again
    with pytest.raises(D.SocialError):
        SP.publish_post(T, pid)                                                  # not approved -> never sent
    reel = _post(D, fmt="reel")
    SP.attach(T, reel, [a["id"]])
    car = _post(D, fmt="carousel")
    SP.attach(T, car, [a["id"]])
    blank = _post(D, platforms="facebook", caption="Only [price] today")
    with D.session() as s:
        assert "video" in " ".join(SP.problems(s.get(D.SocialPost, reel)))
        assert "2 se 10" in " ".join(SP.problems(s.get(D.SocialPost, car)))
        assert "[ ]" in " ".join(SP.problems(s.get(D.SocialPost, blank)))


def test_publish_now_image_to_instagram_and_facebook(pub):
    D, SP = pub
    pid = _post(D)
    SP.attach(T, pid, [SP.add_asset(T, _jpeg())["id"]])
    r = SP.publish_post(T, pid, by_tap=True)
    assert r["status"] == "published"
    assert r["results"]["instagram"] == {"id": "IGM9", "link": "https://www.instagram.com/p/IGM9/"}
    assert r["results"]["facebook"]["link"] == "https://facebook.com/PAGE1_77"
    cont = next(f for k, f in LOG if k == "ig_container")
    assert cont["image_url"].startswith("https://hoola.test/api/social/media/") and cont["caption"].startswith("Smile bright this Diwali")
    assert "#akola #smile" in cont["caption"] and next(f for k, f in LOG if k == "ig_publish")["creation_id"] == "C1"
    post = next(p for p in D.calendar(T) if p["id"] == pid)
    assert post["status"] == "published" and post["result"]["instagram"]["id"] == "IGM9"
    with pytest.raises(D.SocialError):
        SP.publish_post(T, pid, by_tap=True)                                     # never twice
    with pytest.raises(D.SocialError):
        D.set_post(T, pid, caption="change after posting")
    assert any("Posted" in e["text"] for e in D.desk_view(T)["events"])


def test_reel_waits_for_instagram_then_publishes_and_facebook_video(pub):
    D, SP = pub
    pid = _post(D, fmt="reel")
    SP.attach(T, pid, [SP.add_asset(T, MP4)["id"]])
    r = SP.publish_post(T, pid, by_tap=True)
    assert r["status"] == "published" and IGS["polls"] == 3
    cont = next(f for k, f in LOG if k == "ig_container")
    assert cont["media_type"] == "REELS" and cont["video_url"]
    assert any(k == "fb_video" for k, _ in LOG)


def test_carousel_story_and_facebook_multi_photo(pub):
    D, SP = pub
    car = _post(D, fmt="carousel")
    SP.attach(T, car, [SP.add_asset(T, _jpeg(color=(i, i, i)))["id"] for i in range(3)])
    assert SP.publish_post(T, car, by_tap=True)["status"] == "published"
    conts = [f for k, f in LOG if k == "ig_container"]
    assert [c.get("is_carousel_item") for c in conts[:3]] == ["true"] * 3 and conts[3]["media_type"] == "CAROUSEL"
    assert conts[3]["children"] == "C1,C2,C3"
    feed = next(f for k, f in LOG if k == "fb_feed")
    assert "attached_media[2]" in feed and sum(1 for k, f in LOG if k == "fb_photo" and f.get("published") == "false") == 3
    LOG.clear()
    story = _post(D, fmt="story", platforms="instagram")
    SP.attach(T, story, [SP.add_asset(T, _jpeg(1080, 1920))["id"]])
    SP.publish_post(T, story, by_tap=True)
    c = next(f for k, f in LOG if k == "ig_container")
    assert c["media_type"] == "STORIES" and "caption" not in c


def test_quota_and_missing_permission_are_plain_reasons(pub):
    D, SP = pub
    pid = _post(D, platforms="instagram")
    SP.attach(T, pid, [SP.add_asset(T, _jpeg())["id"]])
    IGS["used"] = 49
    r = SP.publish_post(T, pid, by_tap=True)
    assert r["status"] == "failed" and "limit" in r["results"]["instagram"]["error"]
    IGS["used"] = 2
    with D.session() as s:
        a = s.scalars(D.select(D.SocialAccount).where(D.SocialAccount.platform == "instagram")).first()
        a.scopes = "instagram_business_basic,instagram_business_manage_insights"            # connected in Phase 1
    D.set_post(T, pid, status="approved")
    r = SP.publish_post(T, pid)
    assert r["status"] == "failed" and "Reconnect Instagram" in r["results"]["instagram"]["error"]


def test_scheduled_publish_at_slot_missed_when_late_and_hash_guard(pub):
    D, SP = pub
    ist = timezone(timedelta(hours=5, minutes=30))
    at = datetime(2026, 11, 8, 12, 5, tzinfo=ist)
    due = _post(D, slot="2026-11-08T12:00")
    later = _post(D, slot="2026-11-09T12:00")
    late = _post(D, slot="2026-11-06T09:00")
    for pid in (due, later, late):
        SP.attach(T, pid, [SP.add_asset(T, _jpeg())["id"]])
        D.set_post(T, pid, status="approved")
    with D.session() as s:                         # changed behind her back after approval -> must not go out
        s.get(D.SocialPost, later).caption = "sneaky edit"
    r = SP.run_publisher(T, at)
    assert r == {"sent": 1, "failed": 0}
    cal = {p["id"]: p for p in D.calendar(T)}
    assert cal[due]["status"] == "published" and cal[late]["status"] == "missed" and cal[later]["status"] == "approved"
    r = SP.run_publisher(T, datetime(2026, 11, 9, 12, 1, tzinfo=ist))
    assert r == {"sent": 0, "failed": 1} and next(p for p in D.calendar(T) if p["id"] == later)["status"] == "failed"
    assert "publish" in D.due_jobs(T, at)


def test_poster_attached_and_needs_ok_again(pub):
    D, SP = pub
    pid = _post(D)
    SP.attach(T, pid, [SP.add_asset(T, _jpeg())["id"]])
    D.set_post(T, pid, status="approved")
    seen = {}

    def render(tenant, brief, size):
        seen.update(brief=brief, size=size)
        return _jpeg(1080, 1350, (90, 60, 200))
    a = SP.make_poster(T, pid, render=render)
    assert seen == {"brief": "Smile bright", "size": "insta_post"} and a["source"] == "poster"
    p = next(x for x in D.calendar(T) if x["id"] == pid)
    assert p["status"] == "draft" and [m["id"] for m in p["media"]] == [a["id"]]      # poster replaces, OK needed again


def test_api_upload_attach_publish(pub):
    D, SP = pub
    from app import main
    pid = _post(D)
    with TestClient(main.app) as c:
        assert c.post(f"/api/social/posts/{pid}/publish").status_code == 400            # no picture yet: why, at once
        up = c.post("/api/social/media", files={"file": ("p.png", _jpeg(), "image/png")}).json()
        assert up["kind"] == "image"
        assert c.post(f"/api/social/posts/{pid}/media", json={"assets": [up["id"]]}).json()["media"] == [up["id"]]
        assert c.post(f"/api/social/posts/{pid}/publish").json() == {"started": pid}
        for _ in range(100):
            if next(p for p in D.calendar(T) if p["id"] == pid)["status"] == "published":
                break
            time.sleep(0.05)
        assert next(p for p in D.calendar(T) if p["id"] == pid)["status"] == "published"
        assert c.delete(f"/api/social/posts/{pid}/media/{up['id']}").status_code == 400   # posted posts don't change


def test_console_phone_and_privacy_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "data-scpub" in js and "/api/social/media" in js and "/poster" in js and "form: fd" in js and "Reconnect to allow posting" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "socialPublish(" in dart and "_addPhoto(" in dart and "Post now?" in dart
    api = (root / "lib/api.dart").read_text()
    assert "/api/social/posts/$id/publish" in api and "/api/social/media" in api
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "Instagram and Facebook" in pv and "instagram_business_content_publish" not in pv and "Social Media Manager" in pv
