"""v0.338 APP STORE LAUNCH (App Sahayak Phase 7): her iPhone app on the App Store from HER Apple account. asc.py (runs in
her builds repo with her secrets): the ES256 JWT, the official App Store Connect API sequence (app by bundle id -> editable
version -> version + app-info localizations -> 6.9" screenshot set, reserve / PUT / commit with MD5 -> TestFlight build onto
the version; review submission -> item -> submitted) on a faked Apple. Server: listing within Apple's limits, support page,
App Privacy answers, push / submit through the Mac (faked), submit only from her tap, the tool never submits."""
import base64
import hashlib
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.test_v0314_app_backend import _shop_app
from tests.test_v0332_iphone import FakeMac, FakeSwift
from tests.test_v128_appdesign import T
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def _png(w=1320, h=2868) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (w, h), (240, 236, 230)).save(b, "PNG")
    return b.getvalue()


def _p8():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    k = ec.generate_private_key(ec.SECP256R1())
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return k, pem


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---------------------------------------------------------------- asc.py
def test_jwt_es256_verifies():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    from app.appmaker.ios import asc
    k, pem = _p8()
    tok = asc.token("2X9R4HXF34", "57246542-96fe-1a63-e053-0824d011072a", pem, now=1_800_000_000)
    h, p, sig = tok.split(".")
    assert json.loads(_unb64(h)) == {"alg": "ES256", "kid": "2X9R4HXF34", "typ": "JWT"}
    body = json.loads(_unb64(p))
    assert body["aud"] == "appstoreconnect-v1" and body["iss"].startswith("5724") and body["exp"] - body["iat"] == 19 * 60
    raw = _unb64(sig)
    assert len(raw) == 64
    k.public_key().verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
                          f"{h}.{p}".encode(), ec.ECDSA(hashes.SHA256()))


class FakeApple:
    """App Store Connect stand-in: records every call; the blob PUT must carry no bearer token."""
    def __init__(self, has_app=True, versions=(), build_state="VALID"):
        self.calls, self.has_app, self.versions, self.build_state = [], has_app, list(versions), build_state
        self.puts, self.commits, self.bodies = [], [], {}

    def __call__(self, method, url, headers, body):
        if url.startswith("https://blob.example/"):
            assert "Authorization" not in headers and headers.get("Content-Type") == "image/png"
            self.puts.append(len(body))
            return 200, b""
        assert headers["Authorization"].startswith("Bearer ")
        path = url.split("api.appstoreconnect.apple.com")[1]
        p0 = path.split("?")[0]
        self.calls.append(f"{method} {p0}")
        data = json.loads(body) if body else None
        self.bodies[f"{method} {p0}"] = data
        j = lambda o: (200, json.dumps(o).encode())            # noqa: E731
        if p0 == "/v1/apps":
            assert "filter%5BbundleId%5D=com.sharmakirana.app" in path
            return j({"data": [{"id": "app1", "type": "apps"}] if self.has_app else []})
        if p0 == "/v1/apps/app1/appStoreVersions":
            return j({"data": self.versions})
        if method == "POST" and p0 == "/v1/appStoreVersions":
            assert data["data"]["attributes"]["platform"] == "IOS"
            return j({"data": {"id": "ver1", "type": "appStoreVersions", "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"}}})
        if p0.endswith("/appStoreVersionLocalizations") and method == "GET":
            return j({"data": []})
        if method == "POST" and p0 == "/v1/appStoreVersionLocalizations":
            return j({"data": {"id": "loc1"}})
        if p0 == "/v1/apps/app1/appInfos":
            return j({"data": [{"id": "info1", "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"}}]})
        if p0 == "/v1/appInfos/info1/appInfoLocalizations":
            return j({"data": [{"id": "il1", "attributes": {"locale": "en-US"}}]})
        if p0 == "/v1/appStoreVersionLocalizations/loc1/appScreenshotSets":
            return j({"data": []})
        if method == "POST" and p0 == "/v1/appScreenshotSets":
            assert data["data"]["attributes"]["screenshotDisplayType"] == "APP_IPHONE_67"
            return j({"data": {"id": "set1"}})
        if method == "POST" and p0 == "/v1/appScreenshots":
            n = len(self.puts) + len(self.commits)
            size = data["data"]["attributes"]["fileSize"]
            return j({"data": {"id": f"sh{n}", "attributes": {"uploadOperations": [
                {"method": "PUT", "url": f"https://blob.example/{n}/a", "offset": 0, "length": size // 2,
                 "requestHeaders": [{"name": "Content-Type", "value": "image/png"}]},
                {"method": "PUT", "url": f"https://blob.example/{n}/b", "offset": size // 2, "length": size - size // 2,
                 "requestHeaders": [{"name": "Content-Type", "value": "image/png"}]}]}}})
        if method == "PATCH" and p0.startswith("/v1/appScreenshots/"):
            self.commits.append(data["data"]["attributes"])
            return j({})
        if p0 == "/v1/builds":
            assert "filter%5Bversion%5D=105" in path
            return j({"data": [{"id": "b9", "attributes": {"processingState": self.build_state}}]})
        if method == "POST" and p0 == "/v1/reviewSubmissions":
            return j({"data": {"id": "rs1"}})
        if method == "POST" and p0 == "/v1/reviewSubmissionItems":
            r = data["data"]["relationships"]
            assert r["reviewSubmission"]["data"]["id"] == "rs1" and r["appStoreVersion"]["data"]["id"] == "ver1"
            return j({"data": {"id": "rsi1"}})
        if method == "PATCH":
            return j({})
        raise AssertionError(f"unexpected {method} {path}")


STORE = {"bundle_id": "com.sharmakirana.app", "version": "1.2", "build": "105", "locale": "en-US",
         "listing": {"name": "Sharma Kirana", "subtitle": "Groceries to your door", "keywords": "kirana,grocery,atta",
                     "description": "Order groceries.", "promotionalText": "Fresh in 30 minutes"},
         "privacyPolicyUrl": "https://h.test/api/app-api/k/privacy", "supportUrl": "https://h.test/api/app-api/k/support"}


def test_push_sequence_on_a_faked_apple(tmp_path, monkeypatch):
    from app.appmaker.ios import asc
    fake = FakeApple()
    monkeypatch.setattr(asc, "_http", fake)
    shots = []
    for i in range(2):
        f = tmp_path / f"s{i}.png"
        f.write_bytes(_png())
        shots.append(f)
    out = asc.push(STORE, shots, asc.Client("t"))
    assert out == {"ok": True, "app": "app1", "version": "ver1", "version_string": "1.2", "screenshots": 2, "build": "b9",
                   "state": "PREPARE_FOR_SUBMISSION"}
    assert fake.calls[:3] == ["GET /v1/apps", "GET /v1/apps/app1/appStoreVersions", "POST /v1/appStoreVersions"]
    assert fake.calls[-1] == "PATCH /v1/appStoreVersions/ver1"           # the build goes on last
    assert fake.bodies["PATCH /v1/appStoreVersions/ver1"]["data"]["relationships"]["build"]["data"] == {"type": "builds", "id": "b9"}
    loc = fake.bodies["POST /v1/appStoreVersionLocalizations"]["data"]["attributes"]
    assert loc["locale"] == "en-US" and loc["keywords"] == "kirana,grocery,atta" and loc["supportUrl"].endswith("/support")
    assert "whatsNew" not in loc                                          # Apple refuses What's New on a first version
    info = fake.bodies["PATCH /v1/appInfoLocalizations/il1"]["data"]["attributes"]
    assert info == {"name": "Sharma Kirana", "subtitle": "Groceries to your door", "privacyPolicyUrl": STORE["privacyPolicyUrl"]}
    assert len(fake.puts) == 4 and sum(fake.puts) == 2 * len(_png())     # each file in its two parts
    assert fake.commits[0] == {"uploaded": True, "sourceFileChecksum": hashlib.md5(_png()).hexdigest()}


def test_push_refusals(tmp_path, monkeypatch):
    from app.appmaker.ios import asc
    monkeypatch.setattr(asc, "_http", FakeApple(has_app=False))
    with pytest.raises(asc.AscError, match="NO_APP_RECORD"):
        asc.push(STORE, [], asc.Client("t"))
    monkeypatch.setattr(asc, "_http", FakeApple(build_state="PROCESSING"))
    with pytest.raises(asc.AscError, match="BUILD_PROCESSING"):
        asc.push(STORE, [], asc.Client("t"))
    small = tmp_path / "x.png"
    small.write_bytes(_png(1206, 2622))                                     # a 6.3" shot does not fit the 6.9" slot
    monkeypatch.setattr(asc, "_http", FakeApple())
    with pytest.raises(asc.AscError, match="1320x2868"):
        asc.push(STORE, [small], asc.Client("t"))
    assert asc.LIMITS["subtitle"] == 30 and asc.LIMITS["keywords"] == 100


def test_existing_version_is_reused_and_submit(monkeypatch):
    from app.appmaker.ios import asc
    fake = FakeApple(versions=[{"id": "ver1", "attributes": {"versionString": "1.1", "appStoreState": "PREPARE_FOR_SUBMISSION"}}])
    monkeypatch.setattr(asc, "_http", fake)
    out = asc.submit(STORE, asc.Client("t"))
    assert out["submitted"] and out["submission"] == "rs1"
    assert "POST /v1/appStoreVersions" not in fake.calls
    assert fake.bodies["PATCH /v1/appStoreVersions/ver1"]["data"]["attributes"] == {"versionString": "1.2"}
    assert fake.calls[-3:] == ["POST /v1/reviewSubmissions", "POST /v1/reviewSubmissionItems", "PATCH /v1/reviewSubmissions/rs1"]
    assert fake.bodies["PATCH /v1/reviewSubmissions/rs1"]["data"]["attributes"] == {"submitted": True}


def test_main_without_secrets_writes_the_reason(tmp_path, monkeypatch):
    from app.appmaker.ios import asc
    for k in ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_P8"):
        monkeypatch.delenv(k, raising=False)
    (tmp_path / "hoola_qa").mkdir()
    (tmp_path / "hoola_qa/store.json").write_text(json.dumps(STORE))
    assert asc.main(["push", str(tmp_path)]) == 1
    res = json.loads((tmp_path / "asc_result.json").read_text())
    assert res == {"ok": False, "error": "MISSING_SECRET ASC_KEY_ID ASC_ISSUER_ID ASC_KEY_P8"}


# ---------------------------------------------------------------- server side
class StoreMac(FakeMac):
    """The Mac stand-in also answers kinds store / review the way asc.py would (and checks store.json)."""
    def __init__(self):
        super().__init__()
        self.store_json = None

    def __call__(self, src, key, kind):
        if kind in ("store", "review"):
            self.calls.append(kind)
            self.store_json = json.loads((src / "hoola_qa/store.json").read_text())
            assert (src / "hoola_qa/asc.py").exists()
            if kind == "store":
                return {"ok": True, "log": "", "asc": {"ok": True, "version_string": self.store_json["version"], "screenshots": 5,
                                                       "state": "PREPARE_FOR_SUBMISSION"}}
            return {"ok": True, "log": "", "asc": {"ok": True, "submitted": True, "submission": "rs1",
                                                   "version_string": self.store_json["version"]}}
        return super().__call__(src, key, kind)


def _https(monkeypatch):
    from app.appmaker import service as AS
    s = AS._settings()
    monkeypatch.setattr(s, "public_base_url", "https://hoola.test", raising=False)


def test_listing_limits_and_edits(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker.ios import appstore as AP
    from app.site import ai as SA
    monkeypatch.setattr(SA, "ask_json", lambda *a, **k: {"name": "Sharma Kirana Grocery Delivery Pune Fresh",
                                                         "subtitle": "Atta, dal, butter at your door in 30 minutes",
                                                         "keywords": "Kirana, grocery,kirana,app,atta, dal ,iphone," + "x" * 90,
                                                         "description": "Order groceries.", "promotionalText": "Fresh daily"})
    aid, _conv = _shop_app(fake)
    v = AP.listing(T, aid, regen=True)
    lst = v["listing"]
    assert len(lst["name"]) <= 30 and len(lst["subtitle"]) <= 30 and lst["by"] == "opus"
    assert lst["keywords"] == "kirana,grocery,atta,dal"                    # lower case, no repeats, no app / iphone, fits 100
    with pytest.raises(AP.AppStoreError, match="30"):
        AP.listing(T, aid, edit={"subtitle": "x" * 31})
    v = AP.listing(T, aid, edit={"subtitle": "Groceries at your door"})
    assert v["listing"]["subtitle"] == "Groceries at your door" and v["listing"]["edited"]
    monkeypatch.setattr(SA, "ask_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model")))
    v = AP.listing(T, aid, regen=True)
    assert v["listing"]["by"] == "template" and len(v["listing"]["keywords"]) <= 100 and v["listing"]["name"]


def test_push_and_submit_through_the_mac(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker.ios import appstore as AP
    from app.appmaker.ios import service as IO
    from app.main import app
    _https(monkeypatch)
    monkeypatch.setattr(IO, "_ask", FakeSwift())
    mac = StoreMac()
    IO.set_runner(mac)
    try:
        aid, conv = _shop_app(fake)
        c = TestClient(app)
        v = c.get(f"/api/apps/{aid}/appstore").json()
        assert [s["done"] for s in v["steps"]] == [False, False, False, False] and v["support_url"].endswith("/support")
        types = [x["type"] for x in v["privacy_answers"]]
        assert "Location > Precise Location" in types and "Diagnostics > Crash Data" in types and "Purchases > Purchase History" in types
        assert all(x["tracking"] is False for x in v["privacy_answers"])
        r = c.post(f"/api/apps/{aid}/appstore/push", json={})
        assert r.status_code == 400 and "TestFlight" in r.json()["detail"]          # needs a TestFlight build first
        assert c.post(f"/api/apps/{aid}/ios", json={"kind": "testflight"}).json()["testflight"]["build"]
        assert c.post(f"/api/apps/{aid}/appstore/push", json={}).status_code == 400   # and a listing
        c.post(f"/api/apps/{aid}/appstore/listing", json={"regen": True})
        v = c.post(f"/api/apps/{aid}/appstore/push", json={}).json()
        assert v["status"] == "ready" and v["steps"][2]["done"], v["error"]
        sj = mac.store_json
        assert sj["shots"][0] == "app_start" and "hoola_login" not in sj["shots"] and len(sj["shots"]) <= 6
        assert sj["privacyPolicyUrl"].startswith("https://hoola.test/api/app-api/") and sj["bundle_id"].startswith("in.hoola.app.")
        assert sj["version"] and sj["build"] and sj["listing"]["name"]
        # Submit for Review: never without her tap
        r = c.post(f"/api/apps/{aid}/appstore/submit", json={})
        assert r.status_code == 400 and "tap" in r.json()["detail"]
        v = c.post(f"/api/apps/{aid}/appstore/submit", json={"her_tap": True}).json()
        assert v["status"] == "in_review" and v["steps"][3]["done"] and v["submissions"][0]["id"] == "rs1"
        assert mac.calls[-2:] == ["store", "review"]
        # the public support page
        key = sj["privacyPolicyUrl"].split("/app-api/")[1].split("/")[0]
        page = c.get(f"/api/app-api/{key}/support")
        assert page.status_code == 200 and "Delete my account" in page.text and "9876543210" in page.text
    finally:
        IO.set_runner(None)


def test_apple_refusals_become_her_steps():
    from app.appmaker.ios import appstore as AP
    assert "New App" in AP.why_line("NO_APP_RECORD com.x.app")
    assert "TestFlight" in AP.why_line("NO_BUILD 105")
    assert "10-30" in AP.why_line("BUILD_PROCESSING 105 PROCESSING")
    assert "ASC_KEY_P8" in AP.why_line("MISSING_SECRET ASC_KEY_P8")
    assert "Key ID" in AP.why_line("GET /v1/apps -> 401 NOT_AUTHORIZED: bad")


def test_tool_never_submits(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.agent.app_tools import APP_TOOLS, _act
    from app.agent.tools import Ctx, ToolError
    from app.appmaker.ios import service as IO
    monkeypatch.setattr(IO, "_ask", FakeSwift())
    IO.set_runner(StoreMac())
    try:
        aid, conv = _shop_app(fake)
        tool = next(t for t in APP_TOOLS if t["name"] == "app_banao")
        assert tool["input_schema"]["properties"]["astep"]["enum"] == ["listing", "push"]
        ctx = Ctx(tenant_id=T, conversation_id=conv)
        out = _act(ctx, "appstore", {"app": aid, "astep": "listing"})
        assert out["listing"]["name"]
        with pytest.raises(ToolError):
            _act(ctx, "appstore", {"app": aid, "astep": "submit"})
    finally:
        IO.set_runner(None)


def test_project_carries_the_store_files(tmp_path):
    from app.appmaker.ios import gen as G
    sp = json.loads((Path(__file__).resolve().parents[1] / "app/appmaker/android/fixture/spec.json").read_text())
    sp["ios"] = {"store": {"version": "1.0", "build": "101", "listing": {"name": "Sharma Kirana"}, "shots": ["app_start", "home"]}}
    G.write_project(sp, tmp_path / "p")
    assert (tmp_path / "p/hoola_qa/asc.py").exists()
    st = json.loads((tmp_path / "p/hoola_qa/store.json").read_text())
    assert st["bundle_id"] == "in.hoola.preview.fixture" and st["shots"] == ["app_start", "home"]
    wf = (Path(__file__).resolve().parents[1] / "app_builder/hoola-ios.yml").read_text()
    for s in ("inputs.kind == 'store'", "inputs.kind == 'review'", "SIM_KIND=max", "asc.py push", "asc.py submit",
              "ios/asc_result.json", "ASC_KEY_P8: ${{ secrets.ASC_KEY_P8 }}"):
        assert s in wf, s
