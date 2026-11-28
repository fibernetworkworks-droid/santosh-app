"""v0.999.191 GOOGLE PHOTOS COMPLETE: on a stand-in that checks Google's Photos Library API shapes (revision 20261124):
picked photos stay fetchable (fresh links, session cleaned up later), retries on Google's speed limit, big uploads
through the resumable upload, album positions, Hoola's own photos (filters, captions, send, look), album rename /
cover / add / remove (card) / notes / places / maps, sharing said plainly."""
import asyncio
import json
from datetime import timedelta

import httpx
import pytest

from app.agent import photos_tools as pt
from app.agent.tools import ToolError
from tests.test_life import conv_ctx
from tests.test_photos import JPEG, ME, FakePhotos

CATS = {"LANDSCAPES", "RECEIPTS", "FOOD", "DOCUMENTS", "PEOPLE", "PETS", "SELFIES"}


class FullPhotos(FakePhotos):
    """Adds the Library calls Hoola now makes; refuses any body Google would refuse."""

    def __init__(self):
        super().__init__()
        self.enrich = []
        self.busy = 0          # answer 429 this many times first
        self.resumable = {}
        self.list_calls = 0

    def __call__(self, req: httpx.Request):
        u = req.url
        if self.busy and u.host == "photoslibrary.googleapis.com":
            self.busy -= 1
            return httpx.Response(429, json={"error": {"message": "Quota exceeded"}})
        if u.host == "photospicker.googleapis.com" and u.path == "/v1/mediaItems":
            self.list_calls += 1
            items = self.picked.get(u.params["sessionId"], [])
            for m in items:      # every listing gives new links, like Google
                m["mediaFile"]["baseUrl"] = m["mediaFile"]["baseUrl"].split("_v")[0] + f"_v{self.list_calls}"
            return httpx.Response(200, json={"mediaItems": items})
        if u.host == "lh3.googleusercontent.com":
            assert "=w1024-h1024" in u.path or u.path.endswith(("=d", "=dv"))
            return httpx.Response(200, content=JPEG)
        if u.host == "upload.example":
            assert req.headers["x-goog-upload-command"] in ("upload", "upload, finalize")
            off = int(req.headers["x-goog-upload-offset"])
            rec = self.resumable[u.path]
            assert off == len(rec["got"]), "chunks must arrive in order"
            rec["got"] += req.content
            if req.headers["x-goog-upload-command"] == "upload, finalize":
                assert len(rec["got"]) == rec["size"]
                tok = self._id("up")
                self.uploads[tok] = rec["got"]
                return httpx.Response(200, text=tok)
            assert len(req.content) % rec["gran"] == 0
            return httpx.Response(200)
        if u.host == "photoslibrary.googleapis.com":
            p = u.path.removeprefix("/v1")
            if p == "/uploads" and req.headers.get("x-goog-upload-protocol") == "resumable":
                assert req.headers["x-goog-upload-command"] == "start" and req.headers["content-length"] == "0"
                path = f"/u{len(self.resumable)}"
                self.resumable[path] = {"size": int(req.headers["x-goog-upload-raw-size"]), "got": b"", "gran": 262144}
                return httpx.Response(200, headers={"x-goog-upload-url": f"https://upload.example{path}",
                                                    "x-goog-upload-chunk-granularity": "262144"})
            if p == "/mediaItems:batchCreate":
                body = json.loads(req.content)
                assert len(body["newMediaItems"]) <= 50
                if "albumPosition" in body:
                    assert body.get("albumId"), "Google refuses a position without an album"
                    self.last_position = body["albumPosition"]
                out = []
                for it in body["newMediaItems"]:
                    mid = self._id("m")
                    rec = {"id": mid, "filename": it["simpleMediaItem"]["fileName"], "description": it.get("description", ""),
                           "productUrl": f"https://photos.google.com/lr/photo/{mid}", "album": body.get("albumId"),
                           "baseUrl": f"https://lh3.googleusercontent.com/{mid}", "mimeType": "image/jpeg",
                           "mediaMetadata": {"creationTime": "2026-11-20T10:00:00Z", "width": "4000", "height": "3000",
                                             "photo": {"cameraMake": "Google", "cameraModel": "Pixel 9"}}}
                    self.items.append(rec)
                    out.append({"uploadToken": it["simpleMediaItem"]["uploadToken"], "status": {"message": "Success"},
                                "mediaItem": rec})
                return httpx.Response(200, json={"newMediaItemResults": out})
            if p == "/mediaItems:search":
                body = json.loads(req.content)
                assert body.get("pageSize", 25) <= 100
                assert not (body.get("albumId") and body.get("filters")), "Google refuses album + filters"
                f = body.get("filters") or {}
                if "orderBy" in body:
                    assert body["orderBy"] == "MediaMetadata.creation_time" and "dateFilter" in f
                for c in (f.get("contentFilter") or {}).values():
                    assert set(c) <= CATS | {"NONE"} and len(c) <= 10
                for d in (f.get("dateFilter") or {}).get("dates", []):
                    assert set(d) == {"year", "month", "day"}
                if body.get("albumId"):
                    return httpx.Response(200, json={"mediaItems": [i for i in self.items if i["album"] == body["albumId"]]})
                return httpx.Response(200, json={"mediaItems": list(self.items)})
            if p == "/mediaItems" and req.method == "GET":
                return httpx.Response(200, json={"mediaItems": list(self.items)})
            if p == "/mediaItems:batchGet":
                ids = u.params.get_list("mediaItemIds")
                assert ids and len(ids) <= 50 and len(set(ids)) == len(ids)
                byid = {i["id"]: i for i in self.items}
                return httpx.Response(200, json={"mediaItemResults": [{"mediaItem": byid[i]} for i in ids if i in byid]})
            if p.startswith("/mediaItems/") and req.method == "PATCH":
                assert u.params["updateMask"] == "description"
                body = json.loads(req.content)
                mid = p.split("/")[2]
                rec = next(i for i in self.items if i["id"] == mid)
                rec["description"] = body["description"]
                return httpx.Response(200, json=rec)
            if p.startswith("/albums/") and req.method == "PATCH":
                aid = p.split("/")[2]
                mask = u.params["updateMask"].split(",")
                assert set(mask) <= {"title", "coverPhotoMediaItemId"} and mask
                body = json.loads(req.content)
                if "coverPhotoMediaItemId" in mask:
                    assert any(i["id"] == body["coverPhotoMediaItemId"] and i["album"] == aid for i in self.items), \
                        "Google: the cover must be in the album"
                for k in mask:
                    self.albums[aid][k] = body[k]
                return httpx.Response(200, json=self.albums[aid])
            if p.endswith(":batchAddMediaItems") or p.endswith(":batchRemoveMediaItems"):
                aid = p.split("/")[2].split(":")[0]
                ids = json.loads(req.content)["mediaItemIds"]
                assert 0 < len(ids) <= 50
                for i in self.items:
                    if i["id"] in ids:
                        i["album"] = aid if "batchAdd" in p else None
                return httpx.Response(200, json={})
            if p.endswith(":addEnrichment"):
                body = json.loads(req.content)
                assert body["albumPosition"]["position"] in ("FIRST_IN_ALBUM", "LAST_IN_ALBUM", "AFTER_MEDIA_ITEM",
                                                             "AFTER_ENRICHMENT_ITEM"), "a position is required"
                (kind, val), = body["newEnrichmentItem"].items()
                assert kind in ("textEnrichment", "locationEnrichment", "mapEnrichment")
                if kind == "mapEnrichment":
                    assert set(val) == {"origin", "destination"}
                self.enrich.append(body)
                return httpx.Response(200, json={"enrichmentItem": {"id": self._id("enr")}})
            if ":share" in p or "sharedAlbums" in p:
                return httpx.Response(403, json={"error": {"message": "PERMISSION_DENIED"}})
        return super().__call__(req)


@pytest.fixture
def full(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    from app.photos import accounts as pa, client as pc
    monkeypatch.setattr(pc, "RETRY_WAIT", 0)
    fake = FullPhotos()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    url = pa.start_link("default")
    pa.finish_link("code", httpx.URL(url).params["state"])
    yield fake
    ma.set_http(None)


def run(name, ctx, **args):
    return asyncio.run(pt.PHOTOS_HANDLERS[name](ctx, **args))


def _picked(fake, ctx):
    from app.photos import service as ps
    pick = run("photos_pick", ctx, purpose="look")["pick_id"]
    sid = next(iter(fake.sessions))
    fake.sessions[sid]["mediaItemsSet"] = True
    fake.picked[sid] = [
        {"id": "p1", "type": "PHOTO", "createTime": "2026-10-18T10:00:00Z",
         "mediaFile": {"baseUrl": "https://lh3.googleusercontent.com/a1", "mimeType": "image/jpeg", "filename": "bill.jpg",
                       "mediaFileMetadata": {"width": 4000, "height": 3000, "cameraMake": "Google", "cameraModel": "Pixel 9",
                                             "photoMetadata": {"apertureFNumber": 1.7, "isoEquivalent": 100}}}},
        {"id": "v1", "type": "VIDEO", "createTime": "2026-10-18T10:05:00Z",
         "mediaFile": {"baseUrl": "https://lh3.googleusercontent.com/v1", "mimeType": "video/mp4", "filename": "walk.mp4",
                       "mediaFileMetadata": {"videoMetadata": {"fps": 30, "processingStatus": "PROCESSING"}}}},
    ]
    assert ps.poll_tick() == 1
    return pick, sid


def test_picked_photos_stay_fetchable_then_end(full):
    from app.db import session
    from app.photos import service as ps
    from app.photos.models import PhotosPick
    ctx = conv_ctx()
    pick, sid = _picked(full, ctx)
    st = run("photos_picked", ctx, pick_id=pick)
    assert st["items"][0]["camera"] == "Google Pixel 9" and "f/1.7" in st["items"][0]["settings"]
    assert st["items"][1]["video_status"] == "PROCESSING"
    assert not full.sessions[sid].get("deleted")
    with session() as s:                                    # 51 minutes later the links are stale: fetched again
        s.get(PhotosPick, pick).listed_at -= timedelta(minutes=51)
    calls = full.list_calls
    out = run("photos_send", ctx, pick_id=pick, to="phone")
    assert full.list_calls == calls + 1 and out["count"] == 1
    assert "still being processed" in out["problems"][0]  # a video Google is still processing is said, not sent
    with session() as s:                                    # an hour after picking: cleaned up, said plainly
        s.get(PhotosPick, pick).ready_at -= timedelta(minutes=60)
    ps.poll_tick()
    assert full.sessions[sid].get("deleted")
    with pytest.raises(ToolError, match="about an hour after picking"):
        run("photos_send", ctx, pick_id=pick)


def test_speed_limit_retried(full):
    from app.mailbox import service as ms
    ctx = conv_ctx()
    f = ms.store_bytes("default", "a.jpg", JPEG, "mail")
    full.busy = 2
    out = run("photos_upload", ctx, sources=[{"file_id": f.id}])
    assert out["uploaded"] == 1


def test_big_file_resumable_and_positions(full, monkeypatch):
    from app.mailbox import service as ms
    from app.photos import client as pc
    monkeypatch.setattr(pc, "SIMPLE_MAX", 1000)
    monkeypatch.setattr(pc, "CHUNK", 262144)
    ctx = conv_ctx()
    big = ms.store_bytes("default", "big.jpg", JPEG + b"x" * 600000, "mail")
    small = ms.store_bytes("default", "s.jpg", JPEG, "mail")
    out = run("photos_upload", ctx, sources=[{"file_id": big.id}, {"file_id": small.id}], album="Expo",
              where="first", descriptions=["Stall front", ""], description="Expo 2026")
    assert out["uploaded"] == 2 and full.resumable and list(full.resumable.values())[0]["got"] == JPEG + b"x" * 600000
    assert full.last_position == {"position": "FIRST_IN_ALBUM"}
    assert [i["description"] for i in full.items] == ["Stall front", "Expo 2026"]
    web = run("photos_upload", ctx, sources=[{"file_id": small.id}])   # no album: no position sent
    assert web["uploaded"] == 1


def test_hoola_photos_find_caption_send_look(full, monkeypatch):
    from app.mailbox import service as ms
    from app.net import media
    ctx = conv_ctx()
    fs = [ms.store_bytes("default", f"r{i}.jpg", JPEG, "mail") for i in range(3)]
    run("photos_upload", ctx, sources=[{"file_id": f.id} for f in fs], album="Receipts")
    lst = run("photos_library", ctx, action="list", since="2026-11-01", categories=["receipt", "food"], kind="photo",
              oldest_first=True)
    assert lst["count"] == 3 and lst["items"][0]["camera"] == "Google Pixel 9"
    with pytest.raises(ToolError, match="not one of Google's categories"):
        run("photos_library", ctx, action="list", categories=["cars"])
    with pytest.raises(ToolError, match="does not filter inside an album"):
        run("photos_library", ctx, action="list", album="Receipts", kind="photo")
    cap = run("photos_library", ctx, action="caption", ids=["r0.jpg"], caption="Diwali bill")
    assert cap["items"][0]["caption"] == "Diwali bill"
    sent = run("photos_library", ctx, action="send", ids=["r1.jpg"], to="for_email")
    assert sent["count"] == 1 and sent["files"][0]["file_id"]
    monkeypatch.setattr(media, "understand", lambda *a, **k: "A shop receipt for Rs 1,250")
    seen = run("photos_library", ctx, action="look", ids=["r2.jpg"], question="what total?")
    assert "Rs 1,250" in seen["photos"][0]["seen"]


def test_look_at_picked(full, monkeypatch):
    from app.net import media
    ctx = conv_ctx()
    pick, _ = _picked(full, ctx)
    monkeypatch.setattr(media, "understand", lambda *a, **k: "A printed bill")
    out = run("photos_look", ctx, pick_id=pick, ids=["p1"])
    assert out["looked"] == 1 and out["photos"][0]["seen"] == "A printed bill"


def test_albums_full(full):
    from app.bazar.connectors.photos import PhotosExecutor
    from app.bazar.packs.registry import Pack
    from app.mailbox import service as ms
    from pathlib import Path
    from types import SimpleNamespace
    ctx = conv_ctx()
    fs = [ms.store_bytes("default", f"p{i}.jpg", JPEG, "mail") for i in range(3)]
    run("photos_upload", ctx, sources=[{"file_id": f.id} for f in fs[:2]], album="Trip")
    run("photos_upload", ctx, sources=[{"file_id": fs[2].id}])
    ren = run("photos_albums", ctx, action="rename", album="Trip", title="Goa trip 2026")
    assert ren["album"]["title"] == "Goa trip 2026" and ren["was"] == "Trip"
    cov = run("photos_albums", ctx, action="cover", album="Goa trip", cover="p1.jpg")
    assert cov["cover_set"]
    add = run("photos_albums", ctx, action="add", album="Goa trip", ids=["p2.jpg"])
    assert add["added"] == 1 and sum(1 for i in full.items if i["album"]) == 3
    note = run("photos_albums", ctx, action="note", album="Goa trip", text="Day 1: Baga beach", where="first")
    assert note["note_added"] and full.enrich[-1]["albumPosition"] == {"position": "FIRST_IN_ALBUM"}
    run("photos_albums", ctx, action="place", album="Goa trip", place="Baga Beach", lat=15.55, lng=73.75,
        after=note["id"])
    assert full.enrich[-1]["albumPosition"]["position"] == "AFTER_ENRICHMENT_ITEM"
    mp = run("photos_albums", ctx, action="map", album="Goa trip", place="Mumbai", lat=19.07, lng=72.87,
             to_place="Goa", to_lat=15.49, to_lng=73.82)
    assert "Mumbai to Goa" in mp["map_added"]
    with pytest.raises(ToolError, match="not on Earth"):
        run("photos_albums", ctx, action="place", album="Goa trip", place="X", lat=95, lng=0)
    sh = run("photos_albums", ctx, action="share", album="Goa trip")
    assert sh["can_share"] is False and "Share" in sh["steps"] and sh["url"]
    rem = run("photos_albums", ctx, action="remove", album="Goa trip", ids=["p0.jpg"])
    assert rem["status"] == "needs_approval" and sum(1 for i in full.items if i["album"]) == 3   # nothing yet
    from app.photos import service as ps
    pid = [p for p in [ps.pending("default", x) for x in _pending_ids()] if p and p["action"] == "album_remove"][0]["id"]
    pack = Pack(**json.loads((Path(__file__).parents[1] / "app" / "bazar" / "packs" / "manifests" / "santosh-photos.json").read_text()))
    ex = PhotosExecutor()
    bctx = SimpleNamespace(user=SimpleNamespace(id="default"))
    card = ex.call(pack, "confirm_change", {"pending_id": pid}, bctx)
    assert card.title == "Take these photos out of the album?"
    out = ex.execute(pack, card.action["name"], card.action["args"], bctx)
    assert out["removed"] == 1 and sum(1 for i in full.items if i["album"]) == 2


def _pending_ids():
    from sqlalchemy import select
    from app.db import session
    from app.photos.models import PhotosPending
    with session() as s:
        return [p.id for p in s.scalars(select(PhotosPending)).all()]


def test_tools_registered():
    from app.agent.tools import TOOLS
    names = {t["name"] for t in TOOLS}
    assert {"photos_library", "photos_look"} <= names
    assert len(pt.PHOTOS_TOOLS) == 7
