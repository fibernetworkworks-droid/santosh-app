"""v0.453 SURAKSHIT LOGIN + SURAKSHA GATE (App Sahayak Pillar I, Phase 60).

The native apps get the login the website got in v0.434, on the same backend: mobile OTP (hashed, rate limited, the
code never shown), Google / Apple checked ON THE SERVER (signature, audience, single-use nonce - a forged or replayed
token is refused), sessions the member can end, staff 2FA, her own data (DPDP). Plus the security gates that read the
real build and BLOCK a store upload when one fails.
"""
import base64
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appmaker"
GOOGLE_AUD = "123-abc.apps.googleusercontent.com"
APPLE_AUD = "in.hoola.preview.fixture"


def _key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _jwks(pub) -> dict:
    n = pub.public_numbers()
    return {"keys": [{"kty": "RSA", "kid": "test-1", "alg": "RS256", "use": "sig",
                      "n": _b64(n.n.to_bytes((n.n.bit_length() + 7) // 8, "big")),
                      "e": _b64(n.e.to_bytes((n.e.bit_length() + 7) // 8, "big"))}]}


def _token(key, claims: dict, kid: str = "test-1", sign_with=None) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    head = _b64(json.dumps({"alg": "RS256", "kid": kid, "typ": "JWT"}).encode())
    body = _b64(json.dumps(claims).encode())
    sig = (sign_with or key).sign(f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{head}.{body}.{_b64(sig)}"


def _google(sub="g-1", email="asha@gmail.com", nonce="", aud=GOOGLE_AUD, verified=True, **kw) -> dict:
    t = int(time.time())
    return {"iss": "https://accounts.google.com", "aud": aud, "sub": sub, "email": email,
            "email_verified": verified, "name": "Asha G", "iat": t, "exp": t + 3600, "nonce": nonce, **kw}


def _setup(droid_env):
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    return c, aid, key, f"/api/app-api/{key}"


def test_her_switches_and_what_the_app_is_told(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.models import AppProject
    from app.db import session
    c, aid, key, api = _setup(droid_env)
    st = c.get(f"/api/apps/{aid}/sign").json()
    assert st["ways"] == ["email_password"] and st["staff_2fa"] is False
    assert [m["list"] for m in st["matrix"]]                                  # the permissions matrix is right here
    assert c.put(f"/api/apps/{aid}/sign", json={"ways": ["carrier_pigeon"]}).status_code == 400
    assert c.put(f"/api/apps/{aid}/sign", json={"ways": []}).status_code == 400
    assert c.put(f"/api/apps/{aid}/sign", json={"ids": {"nope": "x"}}).status_code == 400
    assert c.put(f"/api/apps/{aid}/sign", json={"ids": {"apple_bundle_id": "bad id!"}}).status_code == 400
    v = c.put(f"/api/apps/{aid}/sign", json={"ways": ["email_password", "google"], "staff_2fa": True,
                                             "ids": {"google_web_client_id": GOOGLE_AUD}}).json()
    assert "apple" in v["ways"], "Google login alone must also offer Apple (App Store 4.8)"
    assert v["staff_2fa"] is True and v["ids"]["google_web_client_id"] == GOOGLE_AUD
    assert "apple" in v["problems"]                                           # no bundle id yet: said, not hidden
    pub = c.get(f"{api}/schema").json()["sign"]
    assert "google" in pub["ways"] and "apple" not in pub["ways"]              # not offered until the bundle id is there
    assert pub["google_server_client_id"] == GOOGLE_AUD
    assert "secret" not in json.dumps(pub).lower()
    c.put(f"/api/apps/{aid}/sign", json={"ids": {"apple_bundle_id": APPLE_AUD}})
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    assert set(BE.seed_hint(r)["sign"]["ways"]) >= {"google", "apple"}         # the build carries it
    from app.appmaker import sign as SG
    assert "never draw your own OTP" in SG.prompt_line({"sign": {"ways": ["phone_otp"]}})
    assert SG.prompt_line({"sign": {"ways": ["email_password"]}}) == ""


def test_phone_otp_and_sessions_and_2fa(droid_env, monkeypatch):
    from app.config import get_settings
    from app.site import security as SEC
    from app.site import webapp as W
    monkeypatch.setattr(get_settings(), "secret_key", "test-secret-key-for-2fa-only-0123456789")   # the 2FA secret is encrypted
    c, aid, key, api = _setup(droid_env)
    c.put(f"/api/apps/{aid}/sign", json={"ways": ["email_password", "phone_otp"]})
    assert c.post(f"{api}/login/otp", json={"phone": "9876500002"}).status_code == 503   # no SMS provider yet: said
    monkeypatch.setattr(SEC, "provider", lambda: "capture")
    W._RATE.clear()
    out = c.post(f"{api}/login/otp", json={"phone": "9876500002"}).json()
    assert out["ok"] and out["sent_to"].count("*") >= 6 and "code" not in json.dumps(out)
    code = SEC.CAPTURED["9876500002"]
    assert c.post(f"{api}/login/otp/check", json={"phone": "9876500002", "code": "000000", "consent": True}).status_code == 400
    assert c.post(f"{api}/login/otp/check", json={"phone": "9876500002", "code": code}).status_code == 400   # consent first
    got = c.post(f"{api}/login/otp/check", json={"phone": "9876500002", "code": code, "name": "Asha", "consent": True}).json()
    assert got["token"] and got["me"]["name"] == "Asha"
    h = {"Authorization": "Bearer " + got["token"]}
    assert c.post(f"{api}/login/otp/check", json={"phone": "9876500002", "code": code, "consent": True}).status_code == 400
    sec = c.get(f"{api}/security", headers=h).json()
    assert len(sec["sessions"]) == 1 and sec["sessions"][0]["this"] is True and sec["sessions"][0]["how"] == "signup"
    assert sec["consent"]["via"] == "otp" and sec["staff"] is False
    assert c.get(f"{api}/security").status_code == 401
    mine = c.get(f"{api}/my-data", headers=h).json()
    assert mine["account"]["phone"] == "9876500002" and mine["account"]["name"] == "Asha"
    assert mine["account"]["email"] == "" and mine["account"]["consent"]["via"] == "otp"      # no fake @phone.local shown
    assert "lists" in mine and "pw" not in json.dumps(mine) and "code" not in json.dumps(mine)
    # a second phone, then "sign out everywhere": the first token stops working at once
    W._RATE.clear()
    c.post(f"{api}/login/otp", json={"phone": "9876500002"})
    code2 = SEC.CAPTURED["9876500002"]
    t2 = c.post(f"{api}/login/otp/check", json={"phone": "9876500002", "code": code2, "consent": True}).json()["token"]
    h2 = {"Authorization": "Bearer " + t2}
    assert len(c.get(f"{api}/security", headers=h2).json()["sessions"]) == 2
    other = next(s for s in c.get(f"{api}/security", headers=h2).json()["sessions"] if not s["this"])
    assert c.post(f"{api}/security/end", json={"id": other["id"]}, headers=h2).json()["ok"] is True
    assert c.get(f"{api}/security", headers=h).status_code == 401              # the ended login is dead everywhere
    assert c.get(f"{api}/c/orders", headers=h).status_code == 401
    # staff 2FA: the password is step one, the authenticator code is step two
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m["id"] for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']}/role", json={"role": "staff"})
    hr = _login(c, api, "ravi@example.com", "Ravi")
    start = c.post(f"{api}/security/2fa-start", json={}, headers=hr).json()
    assert start["secret"] and len(start["secret"]) >= 16
    assert c.post(f"{api}/security/2fa-on", json={"code": "000000"}, headers=hr).status_code == 400
    now_code = SEC._totp_at(start["secret"], int(time.time()))
    assert c.post(f"{api}/security/2fa-on", json={"code": now_code}, headers=hr).json()["two_fa"] is True
    step1 = c.post(f"{api}/login", json={"email": "ravi@example.com", "password": "pass-ravi-1"}).json()
    assert step1.get("need_2fa") is True and step1.get("ticket") and "token" not in step1
    assert c.post(f"{api}/login/2fa", json={"ticket": step1["ticket"], "code": "000000"}).status_code == 400
    done = c.post(f"{api}/login/2fa", json={"ticket": step1["ticket"], "code": SEC._totp_at(start["secret"], int(time.time()))}).json()
    assert done["token"]
    c.put(f"/api/apps/{aid}/sign", json={"staff_2fa": True})
    assert c.post(f"{api}/security/2fa-off", json={"code": now_code},
                  headers={"Authorization": "Bearer " + done["token"]}).status_code == 403   # she made it compulsory


def test_google_and_apple_are_checked_on_the_server(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import sign as SG
    c, aid, key, api = _setup(droid_env)
    c.put(f"/api/apps/{aid}/sign", json={"ways": ["google", "apple", "email_password"],
                                         "ids": {"google_web_client_id": GOOGLE_AUD, "apple_bundle_id": APPLE_AUD}})
    good, evil = _key(), _key()
    SG.set_fetch(lambda url: _jwks(good.public_key()))
    try:
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        # a token signed by SOMEBODY ELSE with every claim right
        forged = _token(evil, _google(nonce=n))
        assert c.post(f"{api}/login/google", json={"id_token": forged, "nonce": n, "consent": True}).status_code == 401
        # right key, wrong audience (a token meant for another app)
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        other = _token(good, _google(nonce=n, aud="999-someone-else.apps.googleusercontent.com"))
        assert c.post(f"{api}/login/google", json={"id_token": other, "nonce": n, "consent": True}).status_code == 401
        # right key, expired
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        old = _token(good, {**_google(nonce=n), "exp": int(time.time()) - 600})
        assert c.post(f"{api}/login/google", json={"id_token": old, "nonce": n, "consent": True}).status_code == 401
        # right key, an e-mail Google itself has not verified
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        unver = _token(good, _google(nonce=n, verified=False))
        assert c.post(f"{api}/login/google", json={"id_token": unver, "nonce": n, "consent": True}).status_code == 401
        # right key, nonce from nowhere
        assert c.post(f"{api}/login/google", json={"id_token": _token(good, _google(nonce="made-up")),
                                                   "nonce": "made-up", "consent": True}).status_code == 401
        # the real thing, and the consent tick is needed for a NEW account
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        tok = _token(good, _google(nonce=n))
        assert c.post(f"{api}/login/google", json={"id_token": tok, "nonce": n}).status_code == 400
        got = c.post(f"{api}/login/google", json={"id_token": tok, "nonce": n, "consent": True}).json()
        assert got["token"] and got["new"] is True and got["me"]["email"] == "asha@gmail.com"
        # the SAME token again: the nonce is single use, so a caught token cannot be replayed
        assert c.post(f"{api}/login/google", json={"id_token": tok, "nonce": n, "consent": True}).status_code == 401
        # signing in again is the same account, not a second one
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        again = c.post(f"{api}/login/google", json={"id_token": _token(good, _google(nonce=n)), "nonce": n}).json()
        assert again["new"] is False and again["me"]["id"] == got["me"]["id"]
        assert len(c.get(f"{api}/security", headers={"Authorization": "Bearer " + again["token"]}).json()["sessions"]) == 2
        # Apple sends the e-mail only the FIRST time: the next sign-in must find the SAME account, not make a second
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        quiet = _token(good, {k: v for k, v in _google(nonce=n).items() if k != "email"})
        q = c.post(f"{api}/login/google", json={"id_token": quiet, "nonce": n}).json()
        assert q["new"] is False and q["me"]["id"] == got["me"]["id"], "the provider's sub must identify the account"
        # Apple: its own issuer and audience, and it hashes the nonce
        import hashlib
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        t = int(time.time())
        ap = _token(good, {"iss": "https://appleid.apple.com", "aud": APPLE_AUD, "sub": "a-1",
                           "email": "x@privaterelay.appleid.com", "iat": t, "exp": t + 3600,
                           "nonce": hashlib.sha256(n.encode()).hexdigest()})
        av = c.post(f"{api}/login/apple", json={"id_token": ap, "nonce": n, "consent": True}).json()
        assert av["token"] and av["me"]["email"] == "x@privaterelay.appleid.com"
        # an Apple token sent to the google door is refused (wrong issuer for that provider)
        n = c.get(f"{api}/login/nonce").json()["nonce"]
        assert c.post(f"{api}/login/google", json={"id_token": _token(good, {**_google(nonce=n), "iss": "https://appleid.apple.com"}),
                                                   "nonce": n, "consent": True}).status_code == 401
        assert c.post(f"{api}/login/facebook", json={"id_token": "x"}).status_code == 404
        # a way she turned OFF cannot be used, whatever the token says
        c.put(f"/api/apps/{aid}/sign", json={"ways": ["email_password"]})
        n2 = SG.nonce(BE.by_key(key))["nonce"]
        assert c.post(f"{api}/login/google", json={"id_token": _token(good, _google(nonce=n2)), "nonce": n2,
                                                   "consent": True}).status_code == 503
    finally:
        SG.set_fetch(None)


def test_security_gates_block_the_store(droid_env, monkeypatch):
    from app.appmaker import gates as GT
    from app.appmaker.models import AppProject
    from app.db import session
    c, aid, key, api = _setup(droid_env)
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    GT.set_osv(lambda deps: [[] for _ in deps])
    try:
        # the CI fixture's build machine is a fake, so its APK carries no signature: the gate SAYS so as a WARNING,
        # because the store gets a .aab signed with her upload key - the preview APK's signature is not that gate.
        v0 = GT.scan(r, "android")
        sig = next(x for x in v0["rows"] if x["check"] == "The preview app is signed")
        assert sig["state"] == "warn" and "install nahi hogi" in sig["say"]
        assert v0["ok"] is True, v0["blocks"]
        proj, apk = GT._proj(r, "android")
        assert apk is not None
        import zipfile
        with zipfile.ZipFile(apk, "a") as z:                  # what a really signed APK looks like (v1 scheme)
            z.writestr("META-INF/CERT.RSA", b"\x30\x82 not a real certificate, only its place")
        v = c.post(f"/api/apps/{aid}/security/check", json={"platform": "android"}).json()
        assert v["ok"] is True, v["blocks"]
        assert next(x for x in v["rows"] if x["check"] == "The preview app is signed")["state"] == "pass"
        assert {x["gate"] for x in v["rows"]} >= {"secrets", "permissions", "settings", "libraries", "login", "data"}
        assert v["pass"] >= 8 and v["fail"] == 0
        libs = next(x for x in v["rows"] if x["gate"] == "libraries")
        assert libs["state"] == "pass" and "libraries" in libs["read"]
        assert c.get(f"/api/apps/{aid}/sign").json()["gate"]["ok"] is True
        # OSV unreachable = NOT CHECKED, never a quiet pass
        GT.set_osv(lambda deps: None)
        v2 = GT.scan(r, "android")
        assert next(x for x in v2["rows"] if x["gate"] == "libraries")["state"] == "not_checked"
        assert v2["ok"] is True and v2["not_checked"] >= 1
        # a HIGH hole in a library: fail, and the Play upload is blocked
        GT.set_osv(lambda deps: [[{"id": "GHSA-x", "database_specific": {"severity": "HIGH"}}]] + [[] for _ in deps[1:]])
        v3 = GT.scan(r, "android")
        assert v3["ok"] is False and any("GHSA-x" in b for b in v3["blocks"])
        try:
            GT.must_pass(r, "android")
            raise AssertionError("a failing gate must block the upload")
        except GT.GateError as e:
            assert "store par nahi bheja" in str(e) and "GHSA-x" in str(e)
        # and the gate is really CALLED by both store uploads (v0.393's lesson: a check with no caller is dead code)
        store_src = (ROOT / "android/store.py").read_text()
        apple_src = (ROOT / "ios/appstore.py").read_text()
        assert 'GT.must_pass(r, "android")' in store_src and 'GT.must_pass(r, "ios")' in apple_src
        assert store_src.index("GT.must_pass") < store_src.index("_bg(r.id, _publish)")
        # a key left inside the app is a FAIL too
        GT.set_osv(lambda deps: [[] for _ in deps])
        proj, _apk = GT._proj(r, "android")
        bad = proj / "app/src/main/assets/leak.json"
        bad.write_text(json.dumps({"razorpay": "rzp_live_AbCdEfGh1234567890"}))
        try:
            v4 = GT.scan(r, "android")
            assert v4["ok"] is False
            assert any("Razorpay" in x["say"] for x in v4["rows"] if x["gate"] == "secrets")
        finally:
            bad.unlink()
        # a banned permission is a FAIL (Play policy, CLAUDE.md)
        mf = proj / "app/src/main/AndroidManifest.xml"
        keep = mf.read_text()
        mf.write_text(keep.replace("<uses-permission android:name=\"android.permission.INTERNET\" />",
                                   "<uses-permission android:name=\"android.permission.INTERNET\" />\n"
                                   "    <uses-permission android:name=\"android.permission.READ_SMS\" />"))
        try:
            v5 = GT.scan(r, "android")
            assert v5["ok"] is False and any("READ_SMS" in x["say"] for x in v5["rows"])
        finally:
            mf.write_text(keep)
        assert GT.scan(r, "android")["ok"] is True
    finally:
        GT.set_osv(None)


def test_both_kits_and_both_generators(tmp_path):
    import subprocess
    import sys
    sp = json.loads((ROOT / "android/fixture/spec.json").read_text())
    plain = tmp_path / "plain.json"
    plain.write_text(json.dumps(sp))
    sp2 = json.loads(json.dumps(sp))
    sp2["seed"].setdefault("backend", {})["sign"] = {"ways": ["phone_otp", "google", "apple", "email_password"],
                                                     "google_server_client_id": GOOGLE_AUD, "consent": True, "signup": True}
    lg = tmp_path / "login.json"
    lg.write_text(json.dumps(sp2))
    for spec, on in ((plain, False), (lg, True)):
        out = tmp_path / ("a" + spec.stem)
        r = subprocess.run([sys.executable, str(ROOT / "android/gen.py"), str(spec), str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-700:]
        reg = (out / "app/src/main/java/hoola/app/AppScreens.kt").read_text()
        assert ('"hoola_login" -> SignInScreen()' in reg) is on
        assert '"hoola_security" -> SecurityScreen()' in reg
        assert "hoola_security" in (out / "hoola_qa/screens.txt").read_text()
        g = (out / "app/src/main/java/hoola/kit/SignInGoogle.kt").read_text()
        grad = (out / "app/build.gradle.kts").read_text()
        assert ("CredentialManager" in g) is on and ("libs.googleid" in grad) is on
        iout = tmp_path / ("i" + spec.stem)
        r = subprocess.run([sys.executable, str(ROOT / "ios/gen.py"), str(spec), str(iout)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-700:]
        ireg = (iout / "Sources/App/AppScreens.swift").read_text()
        assert ('case "hoola_login": return AnyView(SignInScreen())' in ireg) is on
        assert 'case "hoola_security": return AnyView(SecurityScreen())' in ireg
        assert ("applesignin" in (iout / "project.yml").read_text()) is on
    kt = (ROOT / "android/template/app/src/main/java/hoola/kit/SignIn.kt").read_text()
    sw = (ROOT / "ios/template/Sources/Kit/SignIn.swift").read_text()
    for src in (kt, sw):                                   # the screens show it; the calls live in the kit's Cloud layer
        assert "/security" in src and "/my-data" in src
    for src in ((ROOT / "android/template/app/src/main/java/hoola/kit/Backend.kt").read_text(),
                (ROOT / "ios/template/Sources/Kit/Backend.swift").read_text()):
        assert "/login/otp/check" in src and "/login/otp" in src and "/login/nonce" in src and "/login/2fa" in src
        assert "id_token" in src                           # the provider's token goes ONLY to this app's own server
    assert "AuthenticationServices" in sw and "SignInWithAppleButton" in sw
    gb = (ROOT / "android/glogin/SignInGoogle.kt").read_text()
    assert "Ways.serverClientId" in gb and "Auth.nonce()" in gb             # the id + nonce come from the server
    assert "client_secret" not in gb and "clientSecret" not in gb           # native sign-in uses no secret at all
