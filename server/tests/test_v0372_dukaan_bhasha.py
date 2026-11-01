"""v0.372 DUKAAN BHASHA (App Sahayak Phase 36): the Play / App Store listing in the app's own languages - translated once
within each store's limits (cached by the English text, her own words win), uploaded as that language's listing on Play
(hi-IN ...) and as an App Store localization ("hi"); a failed translation never blocks the English upload."""
import json

from fastapi.testclient import TestClient

from tests.test_v0330_play_store import SA, FakeGoogle, _ready
from tests.test_v128_appdesign import T
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


class FakeTr:
    def __init__(self):
        self.calls = 0

    def __call__(self, system, prompt, max_tokens=0, kind="", images=None, effort=None):
        self.calls += 1
        src = json.loads(prompt.split("LISTING (data): ", 1)[1])
        return {k: ("हिंदी " + v)[: 30 if k in ("title", "name", "subtitle") else 4000] for k, v in src.items()}


def test_play_listing_in_hindi(droid_env, monkeypatch):
    from app.appmaker import i18n as I
    from app.appmaker.android import store as ST
    from app.main import app
    from app.site import ai as SAI
    c = TestClient(app)
    aid, conv, ab = _ready(droid_env, monkeypatch)
    I.set_langs(T, aid, ["en", "hi", "xx"])
    c.post(f"/api/apps/{aid}/store/setup", json={"package": "com.sharmakirana.app"})
    c.post(f"/api/apps/{aid}/store/credentials", json={"json": json.dumps(SA)})
    c.post(f"/api/apps/{aid}/store/build", json={})
    tr = FakeTr()
    monkeypatch.setattr(SAI, "ask_json", tr)
    g = FakeGoogle()
    monkeypatch.setattr(ST, "_http", g)
    v = c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"}).json()
    assert v["status"] == "done", v
    hi = [d for m, p, d in g.calls if m == "PUT" and p.endswith("/listings/hi-IN")]
    assert hi and hi[0]["language"] == "hi-IN" and hi[0]["title"].startswith("हिंदी") and len(hi[0]["title"]) <= 30
    assert ("PUT", "/e1/listings/en-IN") in [(m, p.split("/edits")[-1]) for m, p, _ in g.calls]
    n = tr.calls
    c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"})
    assert tr.calls == n                                           # same English listing: not translated (or paid) twice
    # her own words win; too long is refused
    assert c.post(f"/api/apps/{aid}/store/listing_lang", json={"lang": "hi", "values": {"title": "x" * 40}}).status_code == 400
    sv = c.post(f"/api/apps/{aid}/store/listing_lang", json={"lang": "hi", "values": {"title": "शर्मा किराना"}}).json()
    assert sv["languages"]["hi"]["title"] == "शर्मा किराना" and sv["languages"]["hi"]["edited"] is True
    g2 = FakeGoogle()
    monkeypatch.setattr(ST, "_http", g2)
    c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"})
    assert [d for m, p, d in g2.calls if p.endswith("/listings/hi-IN")][0]["title"] == "शर्मा किराना"
    # a translation failure never blocks the English upload
    monkeypatch.setattr(SAI, "ask_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("model down")))
    c.post(f"/api/apps/{aid}/store/listing_lang", json={"lang": "hi", "values": {}})
    g3 = FakeGoogle()
    monkeypatch.setattr(ST, "_http", g3)
    assert c.post(f"/api/apps/{aid}/store/publish", json={"track": "internal"}).json()["status"] == "done"


def test_apple_localization_pushed():
    from app.appmaker.ios import asc

    class C:
        def __init__(self):
            self.calls = []

        def call(self, method, path, body=None, ok404=False):
            self.calls.append((method, path, body))
            if path.startswith("/v1/apps?"):
                return {"data": [{"id": "app1"}]}
            if "/appStoreVersions" in path and method == "GET":
                return {"data": [{"id": "ver1", "attributes": {"versionString": "1.0", "appStoreState": "PREPARE_FOR_SUBMISSION"}}]}
            if path.endswith("/appStoreVersionLocalizations") and method == "GET":
                return {"data": []}
            if path == "/v1/appStoreVersionLocalizations":
                return {"data": {"id": "loc-" + body["data"]["attributes"]["locale"]}}
            if path.endswith("/appInfos"):
                return {"data": [{"id": "info1", "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"}}]}
            if path.endswith("/appInfoLocalizations") and method == "GET":
                return {"data": []}
            if path.startswith("/v1/builds?"):
                return {"data": [{"id": "b1", "attributes": {"processingState": "VALID"}}]}
            return {"data": {}}
    c = C()
    store = {"bundle_id": "in.x.app", "version": "1.0", "build": "3", "locale": "en-US",
             "listing": {"name": "Sharma Kirana", "description": "Order groceries"},
             "localizations": {"hi": {"name": "शर्मा किराना", "description": "किराना मंगाइए", "keywords": "किराना,दुकान"}}}
    try:
        asc.push(store, [], c)
    except Exception:
        pass
    locs = [b["data"]["attributes"].get("locale") for m, p, b in c.calls if m == "POST" and b and p in ("/v1/appStoreVersionLocalizations", "/v1/appInfoLocalizations")]
    assert "hi" in locs and "en-US" in locs
