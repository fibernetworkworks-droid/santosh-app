"""v0.330 PLAY STORE LAUNCH (App Sahayak Phase 5): package name, upload key, her sealed Play service-account key, listing within
Play's limits, icon / feature graphic / screenshots, privacy + deletion pages, data-safety answers, the store bundle (.aab),
and the Google Play Developer API sequence (edit -> bundle -> track -> listing -> images -> commit) on a faked Google;
production only from her tap. The real AAB is built in CI (appgen-check.yml bundleRelease)."""
import io
import json
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from tests.test_v0314_app_backend import _shop_app
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)

SA = {"type": "service_account", "project_id": "her-play", "private_key_id": "k1", "client_email": "hoola-release@her-play.iam.gserviceaccount.com",
      "private_key": "-----BEGIN PRIVATE KEY-----\nMIIfake\n-----END PRIVATE KEY-----\n", "client_id": "1", "token_uri": "https://oauth2.googleapis.com/token"}


class AabBuild(FakeBuild):
    """Build machine stand-in: 'aab' builds return a bundle zip and remember the gradle file they were given."""
    def __init__(self):
        super().__init__()
        self.kinds, self.gradle = [], ""

    def __call__(self, src, key, progress, kind="apk"):
        self.kinds.append(kind)
        if kind != "aab":
            return super().__call__(src, key, progress)
        self.gradle = (src / "app/build.gradle.kts").read_text()
        assert (src / "keys/preview.p12").exists()
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("base/manifest/AndroidManifest.xml", "x")
        return {"ok": True, "log": "BUILD SUCCESSFUL", "apk": b.getvalue(), "seconds": 30, "where": "fake"}


class FakeGoogle:
    def __init__(self, draft_only=False):
        self.calls, self.draft_only = [], draft_only

    def __call__(self, method, url, headers, data, params):
        assert headers["Authorization"] == "Bearer tok"
        path = url.split("/applications/")[1]
        self.calls.append((method, path.split("?")[0], (json.loads(json.dumps(data)) if isinstance(data, dict) else type(data).__name__)))
        if method == "POST" and path.endswith("/edits"):
            return 200, {"id": "e1"}
        if path.endswith("/bundles"):
            return 200, {"versionCode": 2000}
        if "/tracks/" in path and self.draft_only and data["releases"][0]["status"] != "draft":
            return 400, {"error": {"message": "Only releases with status draft may be created on draft app."}}
        return 200, {}


def _ready(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.appmaker.android import store as ST
    aid, conv = _shop_app(fake)
    ab = AabBuild()
    RN.set_runner(ab)
    AN.build(T, aid, conv)
    monkeypatch.setattr(ST, "_token", lambda creds: "tok")
    return aid, conv, ab


def test_setup_key_listing_pages_and_safety(droid_env, monkeypatch):
    from app.appmaker.android import store as ST
    from app.main import app
    c = TestClient(app)
    aid, _conv, _ab = _ready(droid_env, monkeypatch)
    v = c.get(f"/api/apps/{aid}/store").json()
    assert v["proposed"] == "com.sharmakirana.app" and v["package"] == "" and v["steps"][0]["done"] is True
    assert c.post(f"/api/apps/{aid}/store/setup", json={"package": "Bad Name"}).status_code == 400
    assert c.post(f"/api/apps/{aid}/store/setup", json={"package": "in.hoola.preview.x"}).status_code == 400
    v = c.post(f"/api/apps/{aid}/store/setup", json={}).json()
    assert v["package"] == "com.sharmakirana.app"
    cert = c.get(f"/api/apps/{aid}/store-cert")
    assert cert.status_code == 200 and b"BEGIN CERTIFICATE" in cert.content and b"PRIVATE" not in cert.content
    # her service-account key: checked, sealed, never returned
    assert c.post(f"/api/apps/{aid}/store/credentials", json={"json": "{\"type\": \"user\"}"}).status_code == 400
    v = c.post(f"/api/apps/{aid}/store/credentials", json={"json": json.dumps(SA)}).json()
    assert v["account"].startswith("hoo…@her-play") and "private_key" not in json.dumps(v)
    from app.appmaker import service as AS
    sealed = (ST._dir(AS._load(aid)) / "play.sealed").read_text()
    assert "PRIVATE KEY" not in sealed and "hoola-release" not in sealed
    # listing within Play's limits (template when no model), her edit checked
    v = c.post(f"/api/apps/{aid}/store/listing", json={"regen": True}).json()
    lst = v["listing"]
    assert lst["title"] and len(lst["title"]) <= 30 and len(lst["short"]) <= 80 and len(lst["full"]) <= 4000
    assert c.post(f"/api/apps/{aid}/store/listing", json={"edit": {"title": "x" * 31}}).status_code == 400
    v = c.post(f"/api/apps/{aid}/store/listing", json={"edit": {"short": "Order groceries and track them"}}).json()
    assert v["listing"]["short"] == "Order groceries and track them"
    # graphics Play needs
    g = ST.graphics(AS._load(aid))
    assert Image.open(io.BytesIO(g["icon"])).size == (512, 512) and Image.open(io.BytesIO(g["featureGraphic"])).size == (1024, 500)
    # the public pages + data safety from what the app really holds
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        key = json.loads(s.get(AppProject, aid).android)["app_key"]
    pr = c.get(f"/api/app-api/{key}/privacy")
    assert pr.status_code == 200 and "Privacy policy" in pr.text and "Crash reports" in pr.text and "<script" not in pr.text
    dl = c.get(f"/api/app-api/{key}/delete-account")
    assert dl.status_code == 200 and "Delete my account" in dl.text
    assert v["privacy_url"].endswith(f"/api/app-api/{key}/privacy")
    kinds = " ".join(x["type"] for x in v["data_safety"])
    assert "Phone number" in kinds and "Purchase history" in kinds and "Crash logs" in kinds and "Location" in kinds
    assert all(x["shared"] == "No" for x in v["data_safety"])


def test_bundle_upload_sequence_draft_fallback_and_production_tap(droid_env, monkeypatch):
    from app.appmaker.android import service as AN
    from app.appmaker.android import store as ST
    from app.main import app
    c = TestClient(app)
    aid, conv, ab = _ready(droid_env, monkeypatch)
    c.post(f"/api/apps/{aid}/store/setup", json={"package": "com.sharmakirana.app"})
    assert c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"}).status_code == 400     # no key yet
    c.post(f"/api/apps/{aid}/store/credentials", json={"json": json.dumps(SA)})
    v = c.post(f"/api/apps/{aid}/store/build", json={}).json()
    assert v["status"] == "built" and v["bundle"]["file"].endswith(".aab") and ab.kinds[-1] == "aab"
    assert 'applicationId = "com.sharmakirana.app"' in ab.gradle and '?: ""' not in ab.gradle   # store package + upload key password
    vc = v["bundle"]["version_code"]
    assert vc > AN.get(T, aid)["history"][0]["version_code"]
    # the next preview build keeps going up past the store code
    AN.build(T, aid, conv)
    assert AN.get(T, aid)["history"][0]["version_code"] > vc
    # internal testing through Google's API, in order
    g = FakeGoogle()
    monkeypatch.setattr(ST, "_http", g)
    v = c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"}).json()
    assert v["status"] == "done", v
    seq = [(m, p.split("/edits")[-1]) for m, p, _ in g.calls]
    assert seq[0] == ("POST", "") and seq[1] == ("POST", "/e1/bundles") and seq[2] == ("PUT", "/e1/tracks/internal")
    assert ("PUT", "/e1/listings/en-IN") in seq and ("POST", "/e1/listings/en-IN/icon") in seq
    assert ("POST", "/e1/listings/en-IN/featureGraphic") in seq and seq[-1] == ("POST", "/e1:commit")
    track_body = next(d for m, p, d in g.calls if "/tracks/" in p)
    assert track_body["releases"][0]["versionCodes"] == ["2000"] and track_body["releases"][0]["status"] == "completed"
    assert v["releases"][0]["track"] == "internal" and v["locked"] is True
    assert c.post(f"/api/apps/{aid}/store/setup", json={"package": "com.other.app"}).status_code == 400   # permanent now
    # production: never from the tool, never without her tap
    import asyncio
    from app.agent.tools import Ctx, ToolError, dispatch
    assert c.post(f"/api/apps/{aid}/store/publish", json={"track": "production"}).status_code == 400
    try:
        asyncio.run(dispatch("app_banao", {"action": "store", "app": aid, "step": "production"}, Ctx(tenant_id=T, conversation_id=conv)))
        raise AssertionError("tool sent production")
    except ToolError:
        pass
    v = c.post(f"/api/apps/{aid}/store/publish", json={"track": "production", "her_tap": True}).json()
    assert v["releases"][0]["track"] == "production"
    # a brand-new app Google hasn't reviewed: the release goes as a draft and she is told what to do
    g2 = FakeGoogle(draft_only=True)
    monkeypatch.setattr(ST, "_http", g2)
    c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"})
    statuses = [d["releases"][0]["status"] for m, p, d in g2.calls if "/tracks/" in p]
    assert statuses == ["completed", "draft"]
    from app.db import Message, session
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "Google Play par chali gayi" in str(m.content)]
    assert any("draft" in n for n in notes)
    # a Google refusal is said plainly
    monkeypatch.setattr(ST, "_http", lambda *a: (403, {"error": {"message": "The caller does not have permission"}}))
    v = c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"}).json()
    assert v["status"] == "failed" and "permission" in v["error"]
    # the tool reads the state
    seen = asyncio.run(dispatch("app_dekho", {"what": "store", "app": aid}, Ctx(tenant_id=T, conversation_id=conv)))
    assert seen["package"] == "com.sharmakirana.app" and seen["console_steps"]
