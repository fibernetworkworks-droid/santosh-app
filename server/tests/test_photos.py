"""Google Photos: connecting, the Picker flow (pick -> ready -> send to phone / email / PC), uploads into albums,
the big-upload confirm card, and honest limits."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import app.photos.models  # noqa: F401  (tables)
from app.agent import photos_tools as pt
from app.agent.tools import Ctx, ToolError
from tests.test_life import conv_ctx

ME = "meghana@fnw.in"
JPEG = b"\xff\xd8\xff\xe0fakejpegdata"


class FakePhotos:
    def __init__(self):
        self.sessions = {}
        self.picked = {}
        self.uploads = {}
        self.albums = {}
        self.items = []
        self.n = 0

    def _id(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def __call__(self, req: httpx.Request):
        u = req.url
        if u.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/photospicker.mediaitems.readonly "
                                                      "https://www.googleapis.com/auth/photoslibrary.appendonly"})
        if u.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at"
        if u.host == "photospicker.googleapis.com":
            p = u.path.removeprefix("/v1")
            if p == "/sessions" and req.method == "POST":
                sid = self._id("ses")
                self.sessions[sid] = {"id": sid, "pickerUri": f"https://photos.google.com/picker/{sid}",
                                      "mediaItemsSet": False}
                return httpx.Response(200, json=self.sessions[sid])
            if p.startswith("/sessions/"):
                sid = p.split("/")[2]
                if sid not in self.sessions:
                    return httpx.Response(404)
                if req.method == "DELETE":
                    self.sessions[sid]["deleted"] = True
                    return httpx.Response(200, json={})
                return httpx.Response(200, json=self.sessions[sid])
            if p == "/mediaItems":
                return httpx.Response(200, json={"mediaItems": self.picked.get(u.params["sessionId"], [])})
        if u.host == "lh3.googleusercontent.com":
            assert u.path.endswith("=d") or u.path.endswith("=dv")
            return httpx.Response(200, content=JPEG)
        if u.host == "photoslibrary.googleapis.com":
            p = u.path.removeprefix("/v1")
            if p == "/uploads":
                assert req.headers["x-goog-upload-protocol"] == "raw"
                tok = self._id("up")
                self.uploads[tok] = req.content
                return httpx.Response(200, text=tok)
            if p == "/mediaItems:batchCreate":
                body = json.loads(req.content)
                out = []
                for it in body["newMediaItems"]:
                    mid = self._id("m")
                    rec = {"id": mid, "filename": it["simpleMediaItem"]["fileName"],
                           "productUrl": f"https://photos.google.com/lr/photo/{mid}", "album": body.get("albumId")}
                    self.items.append(rec)
                    out.append({"uploadToken": it["simpleMediaItem"]["uploadToken"], "status": {"message": "Success"},
                                "mediaItem": rec})
                return httpx.Response(200, json={"newMediaItemResults": out})
            if p == "/albums" and req.method == "GET":
                return httpx.Response(200, json={"albums": list(self.albums.values())})
            if p == "/albums" and req.method == "POST":
                aid = self._id("alb")
                self.albums[aid] = {"id": aid, "title": json.loads(req.content)["album"]["title"],
                                    "productUrl": f"https://photos.google.com/lr/album/{aid}"}
                return httpx.Response(200, json=self.albums[aid])
            if p == "/mediaItems:search":
                aid = json.loads(req.content)["albumId"]
                return httpx.Response(200, json={"mediaItems": [i for i in self.items if i["album"] == aid]})
        return httpx.Response(400, json={"error": {"message": f"unhandled {req.method} {u}"}})


@pytest.fixture
def ph(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    fake = FakePhotos()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    from app.photos import accounts as pa
    url = pa.start_link("default")
    assert "photospicker.mediaitems.readonly" in httpx.URL(url).params["scope"]
    state = httpx.URL(url).params["state"]
    assert pa.is_link_state(state) and state.startswith("gph_")
    out = pa.finish_link("code", state)
    assert out["address"] == ME and out["tenant"] == "default"
    yield fake
    ma.set_http(None)


def run(name, ctx, **args):
    return asyncio.run(pt.PHOTOS_HANDLERS[name](ctx, **args))


def _events(conv, kind):
    from sqlalchemy import select
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == kind)
                                             .order_by(Event.id)).all()]


def _notices(conv):
    from sqlalchemy import select
    from app.db import Message, session
    with session() as s:
        return [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv)).all()]


def test_pick_then_send_to_phone_and_email(ph):
    from app.photos import service as ps
    ctx = conv_ctx()
    out = run("photos_pick", ctx, purpose="Ramesh ko email karna")
    pick = out["pick_id"]
    card = _events(ctx.conversation_id, "photos_pick")[-1]
    assert card["picker_uri"].endswith("/autoclose") and card["status"] == "waiting"
    with pytest.raises(ToolError, match="abhi photos nahi chuni"):
        run("photos_send", ctx, pick_id=pick)
    assert ps.poll_tick() == 0                                   # still choosing
    sid = next(iter(ph.sessions))
    ph.sessions[sid]["mediaItemsSet"] = True
    ph.picked[sid] = [
        {"id": "p1", "type": "PHOTO", "createTime": "2026-10-18T10:00:00Z",
         "mediaFile": {"baseUrl": "https://lh3.googleusercontent.com/a1", "mimeType": "image/jpeg", "filename": "shop.jpg",
                       "mediaFileMetadata": {"width": 4000, "height": 3000}}},
        {"id": "p2", "type": "PHOTO", "createTime": "2026-10-18T10:05:00Z",
         "mediaFile": {"baseUrl": "https://lh3.googleusercontent.com/a2", "mimeType": "image/jpeg", "filename": "board.jpg"}},
    ]
    assert ps.poll_tick() == 1
    assert ph.sessions[sid].get("deleted")                       # finished sessions are cleaned up
    assert any("2 photos chun li gayi" in (n or "") for n in _notices(ctx.conversation_id))
    st = run("photos_picked", ctx, pick_id=pick)
    assert st["status"] == "ready" and [i["filename"] for i in st["items"]] == ["shop.jpg", "board.jpg"]
    assert "base_url" not in st["items"][0]                       # private download links stay on the server
    sent = run("photos_send", ctx, pick_id=pick, to="phone")
    assert sent["count"] == 2 and [e["name"] for e in _events(ctx.conversation_id, "pc_file")] == ["shop.jpg", "board.jpg"]
    mail = run("photos_send", ctx, pick_id=pick, to="for_email", ids=["p1"])
    assert mail["count"] == 1 and mail["files"][0]["file_id"]
    from app.db import PcFile, session
    with session() as s:
        f = s.get(PcFile, mail["files"][0]["file_id"])
        assert Path(f.stored_path).read_bytes() == JPEG and f.direction == "mail"


def test_upload_into_album_from_email_and_file(ph, monkeypatch):
    from app.mailbox import service as ms
    ctx = conv_ctx()
    monkeypatch.setattr(ms, "attachment", lambda tenant, ref, att: ("diwali.jpg", "image/jpeg", JPEG))
    f = ms.store_bytes("default", "stall.png", b"\x89PNGfake", "mail")
    out = run("photos_upload", ctx, sources=[{"email_id": "mbx~1", "attachment_id": "1"}, {"file_id": f.id}],
              album="Diwali Expo 2026")
    assert out["uploaded"] == 2 and out["album_url"].startswith("https://photos.google.com/lr/album/")
    assert [i["filename"] for i in ph.items] == ["diwali.jpg", "stall.png"] and all(i["album"] for i in ph.items)
    again = run("photos_upload", ctx, sources=[{"file_id": f.id}], album="diwali expo 2026")   # same album reused
    assert again["uploaded"] == 1 and len(ph.albums) == 1
    alb = run("photos_albums", ctx, action="list")
    assert alb["albums"][0]["title"] == "Diwali Expo 2026" and "delete" in alb["limits"]
    items = run("photos_albums", ctx, action="items", album="Diwali Expo 2026")
    assert items["count"] == 3
    doc = ms.store_bytes("default", "notes.txt", b"hello", "mail")
    bad = run("photos_upload", ctx, sources=[{"file_id": doc.id}])
    assert bad["uploaded"] == 0 and "photo ya video nahi" in bad["problems"][0]


def test_big_upload_needs_the_tap(ph):
    from app.bazar.connectors.photos import PhotosExecutor
    from app.bazar.packs.registry import Pack
    from app.mailbox import service as ms
    from app.photos import service as ps
    ctx = conv_ctx()
    files = [ms.store_bytes("default", f"img{i}.jpg", JPEG, "mail") for i in range(21)]
    res = asyncio.run(asyncio.to_thread(ps.plan_or_upload, "default", ctx.conversation_id,
                                        [{"file_id": f.id} for f in files], "Expo"))
    assert "pending_id" in res and ph.items == []
    pack = Pack(**json.loads((Path(__file__).parents[1] / "app" / "bazar" / "packs" / "manifests" / "santosh-photos.json").read_text()))
    bctx = SimpleNamespace(user=SimpleNamespace(id="default"))
    ex = PhotosExecutor()
    card = ex.call(pack, "confirm_change", {"pending_id": res["pending_id"]}, bctx)
    assert card.title == "Itni photos upload karein?" and "21" in card.items[0]["name"]
    out = ex.execute(pack, card.action["name"], card.action["args"], bctx)
    assert out["uploaded"] == 21 and len(ph.items) == 21
    from app.bazar.connectors.base import ToolError as BzErr
    with pytest.raises(BzErr):
        ex.call(pack, "confirm_change", {"pending_id": res["pending_id"]}, bctx)   # already done


def test_not_connected(env):
    with pytest.raises(ToolError, match="Profile > Google Photos"):
        run("photos_pick", Ctx("someone", "c"))
