"""v0.368 TURANT IPHONE (App Sahayak Phase 32): iPhone instant notifications through APNs with the business's own Apple push
key (sealed, checked, never returned); the iPhone build gets the push capability + PushHub only when the key is set; iOS
tokens register with platform ios; pushes go to APNs (faked) with an ES256 JWT, the bundle id as topic; bad tokens dropped."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app/appmaker"


def _p8() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    k = ec.generate_private_key(ec.SECP256R1())
    return k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


def test_ios_project_push_only_when_on(tmp_path):
    from app.appmaker.ios import gen as IG
    sp = json.loads((ROOT / "android/fixture/spec.json").read_text())
    IG.write_project(sp, tmp_path / "off")
    assert "static let pushOn = false" in (tmp_path / "off/Sources/App/AppTokens.swift").read_text()
    assert "aps-environment" not in (tmp_path / "off/project.yml").read_text()
    sp["ios_push"] = True
    IG.write_project(sp, tmp_path / "on")
    assert "static let pushOn = true" in (tmp_path / "on/Sources/App/AppTokens.swift").read_text()
    y = (tmp_path / "on/project.yml").read_text()
    assert "entitlements:" in y and "aps-environment: production" in y
    import yaml
    doc = yaml.safe_load(y)
    assert doc["targets"]["App"]["entitlements"]["properties"]["aps-environment"] == "production"
    assert "@UIApplicationDelegateAdaptor(HoolaAppDelegate.self)" in (tmp_path / "on/Sources/App/HoolaApp.swift").read_text()
    kit = (tmp_path / "on/Sources/Kit/Push.swift").read_text()
    assert "registerForRemoteNotifications" in kit and '"platform": "ios"' in kit


def test_key_tokens_and_apns(droid_env, monkeypatch):
    from app.appmaker import turant as TU
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    assert c.put(f"/api/apps/{aid}/turant/ios", json={"key_id": "ABC", "team_id": "TEAM123456", "p8": _p8()}).status_code == 400
    assert c.put(f"/api/apps/{aid}/turant/ios", json={"key_id": "ABCDE12345", "team_id": "TEAM123456", "p8": "not a key"}).status_code == 400
    p8 = _p8()
    v = c.put(f"/api/apps/{aid}/turant/ios", json={"key_id": "abcde12345", "team_id": "TEAM123456", "p8": p8}).json()
    assert v["ios"] is True and v["ios_key"]["key_id"] == "ABCDE12345" and "PRIVATE" not in json.dumps(v)
    assert "PRIVATE" not in TU._ios_file(TU.AS._load(aid) if hasattr(TU, "AS") else __import__("app.appmaker.service", fromlist=["x"])._load(aid)).read_text()
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    c.post(f"{api}/push-token", json={"token": "a1" * 32, "platform": "ios"}, headers=ha)
    sent = []

    class Res:
        def __init__(self, code=200, text=""):
            self.status_code, self.text = code, text

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            sent.append((url, json, headers))
            return Res()
    monkeypatch.setattr(TU, "_apns_client", lambda: FakeClient())

    class Inline:
        @staticmethod
        def submit(fn, *a):
            fn(*a)
    from app import push as P
    monkeypatch.setattr(P, "_pool", Inline)
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    o = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Packed"}, headers=hr)
    assert len(sent) == 1
    url, payload, hdr = sent[0]
    assert url.endswith("/3/device/" + "a1" * 32) and hdr["apns-push-type"] == "alert" and hdr["authorization"].startswith("bearer ")
    from app.appmaker.ios import service as IS
    assert hdr["apns-topic"] == IS.bundle_id(IS.AS._load(aid) if hasattr(IS, "AS") else None)
    head, body, sig = hdr["authorization"].split(" ")[1].split(".")
    import base64
    pad = lambda x: x + "=" * (-len(x) % 4)
    assert json.loads(base64.urlsafe_b64decode(pad(head))) == {"alg": "ES256", "kid": "ABCDE12345"}
    assert json.loads(base64.urlsafe_b64decode(pad(body)))["iss"] == "TEAM123456" and len(base64.urlsafe_b64decode(pad(sig))) == 64
    assert "Packed" in payload["aps"]["alert"]["title"]
    # Apple says the token is gone -> dropped
    monkeypatch.setattr(FakeClient, "post", lambda self, url, json=None, headers=None: Res(410, '{"reason":"Unregistered"}'))
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
    assert c.get(f"/api/apps/{aid}/turant").json()["tokens"] == 0
    assert c.put(f"/api/apps/{aid}/turant/ios", json={"clear": True}).json()["ios"] is False
