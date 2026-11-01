"""v0.367 TURANT (App Sahayak Phase 31): instant notifications for the Android apps - her tap registers the app's packages
in Hoola's Firebase project (official Firebase Management API, faked here), the next build carries Firebase Messaging as
plain resources + the real PushHook, phones register their token after sign-in, and status / new-order / assignment events
push through FCM HTTP v1 (faked) to the right accounts only; off / no key = nothing changes."""
import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app/appmaker"


def gs_json(pkg: str) -> str:
    return json.dumps({"project_info": {"project_number": "123456789012", "project_id": "newtika-hoola"},
                       "client": [{"client_info": {"mobilesdk_app_id": "1:123456789012:android:abcdef0123456789",
                                                   "android_client_info": {"package_name": pkg}},
                                   "api_key": [{"current_key": "AIzaFakeKeyForTests_0123456789abcdef"}]}]})


def test_generator_adds_firebase_only_when_on(tmp_path):
    from app.appmaker.android import gen as G
    sp = json.loads((ROOT / "android/fixture/spec.json").read_text())
    G.write_project(sp, tmp_path / "off")
    assert "const val ON = false" in (tmp_path / "off/app/src/main/java/hoola/kit/PushHook.kt").read_text()
    assert "firebase" not in (tmp_path / "off/app/build.gradle.kts").read_text()
    assert "HoolaPush" not in (tmp_path / "off/app/src/main/AndroidManifest.xml").read_text()
    sp["fcm"] = gs_json(sp["app"]["app_id"])
    G.write_project(sp, tmp_path / "on")
    hook = (tmp_path / "on/app/src/main/java/hoola/kit/PushHook.kt").read_text()
    assert "const val ON = true" in hook and "FirebaseMessagingService" in hook and '"/push-token"' in hook
    assert "implementation(libs.firebase.messaging)" in (tmp_path / "on/app/build.gradle.kts").read_text()
    man = (tmp_path / "on/app/src/main/AndroidManifest.xml").read_text()
    assert 'android:name="hoola.kit.HoolaPush"' in man and "com.google.firebase.MESSAGING_EVENT" in man
    res = (tmp_path / "on/app/src/main/res/values/google_services.xml").read_text()
    assert "1:123456789012:android:abcdef0123456789" in res and "gcm_defaultSenderId" in res
    assert G.fcm_config({"fcm": "{not json", "app": {"app_id": "x.y"}}) == {}


def test_enable_register_and_push(droid_env, monkeypatch, tmp_path):
    from app import push as P
    from app.appmaker import turant as TU
    from app.appmaker.android import spec as SP
    from app.config import get_settings
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    assert c.get(f"/api/apps/{aid}/turant").json()["configured"] is False
    assert c.put(f"/api/apps/{aid}/turant", json={"on": True}).status_code == 409          # no Firebase key on the server
    sa = tmp_path / "sa.json"
    sa.write_text(json.dumps({"project_id": "newtika-hoola"}))
    monkeypatch.setattr(get_settings(), "fcm_service_account_file", str(sa))
    made = []

    def fake_call(method, url, body=None):
        if url.endswith("/androidApps?pageSize=100"):
            return {"apps": []}
        if method == "POST":
            made.append(body["packageName"])
            return {"done": True, "response": {"appId": "1:1:android:" + body["packageName"][-6:]}}
        if url.endswith("/config"):
            return {"configFileContents": base64.b64encode(gs_json(made[-1]).encode()).decode()}
        return {}
    monkeypatch.setattr(TU, "_call", fake_call)
    monkeypatch.setattr(TU, "_mgmt", lambda: (None, "newtika-hoola"))
    res = c.put(f"/api/apps/{aid}/turant", json={"on": True})
    v = res.json()
    assert res.status_code == 200, v
    assert v["on"] and made == [SP.app_id_for(aid)] and v["packages"] == [SP.app_id_for(aid)], (v, made)
    # phones: tokens only from signed-in accounts
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    assert c.post(f"{api}/push-token", json={"token": "x" * 40}).status_code == 401
    assert c.post(f"{api}/push-token", json={"token": "short"}, headers=ha).status_code == 400
    c.post(f"{api}/push-token", json={"token": "asha-phone-token-" + "a" * 30}, headers=ha)
    c.post(f"{api}/push-token", json={"token": "ravi-phone-token-" + "r" * 30}, headers=hr)
    assert c.get(f"/api/apps/{aid}/turant").json()["tokens"] == 2
    # events -> FCM v1 (faked), run inline instead of the pool
    sent = []

    class Res:
        def __init__(self, code=200, text=""):
            self.status_code, self.text = code, text

    class Creds:
        token = "t"
    monkeypatch.setattr(P, "_credentials", lambda: (Creds(), "newtika-hoola"))
    monkeypatch.setattr(TU.httpx, "post", lambda url, json=None, headers=None, timeout=0: (sent.append(json["message"]), Res())[1])

    class Inline:
        @staticmethod
        def submit(fn, *a):
            fn(*a)
    monkeypatch.setattr(P, "_pool", Inline)
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    o = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    assert [m["token"][:4] for m in sent] == ["ravi"] and sent[0]["data"]["title"] == "New order"        # staff hear a new order
    sent.clear()
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Packed"}, headers=hr)
    assert [m["token"][:4] for m in sent] == ["asha"] and "Packed" in sent[0]["data"]["title"]          # the customer hears it
    assert sent[0]["android"]["priority"] == "HIGH" and set(sent[0]["data"]) == {"title", "body", "id"}
    sent.clear()
    c.patch(f"/api/apps/{aid}/data/orders/{o['id']}", json={"assign": mem["ravi@example.com"]["id"]})
    assert [m["token"][:4] for m in sent] == ["ravi"] and sent[0]["data"]["title"] == "Given to you"
    # an uninstalled phone's token is dropped
    monkeypatch.setattr(TU.httpx, "post", lambda url, json=None, headers=None, timeout=0: Res(404, '{"error":{"status":"NOT_FOUND","details":[{"errorCode":"UNREGISTERED"}]}}'))
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
    assert c.get(f"/api/apps/{aid}/turant").json()["tokens"] == 1
    # off = no pushes
    c.put(f"/api/apps/{aid}/turant", json={"on": False})
    sent.clear()
    monkeypatch.setattr(TU.httpx, "post", lambda url, json=None, headers=None, timeout=0: (sent.append(json["message"]), Res())[1])
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Cancelled"}, headers=hr)
    assert sent == []


def test_ci_and_tool_markers():
    wf = (ROOT.parents[2] / ".github/workflows/appgen-check.yml").read_text()
    assert "fcm:" in wf and "firebase" in wf.lower()
    assert "turant" in (ROOT.parent / "agent/app_tools.py").read_text()
    assert "Instant notifications" in (ROOT.parent / "static/console/build.js").read_text()
