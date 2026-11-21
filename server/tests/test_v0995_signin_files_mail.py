"""v0.995 B6 SIGN-IN, FILES, EMAIL (owner: "GO B6" on docs/research/lovable/03_backend_vs_hoola.md, gap 7).

A website linked to its app backend gets: Google sign-in (her own web client id; the ID token checked on the server -
signature, audience, single-use nonce; Google's script allowed by the CSP only for that site), the website's files in the
Studio (private unless in a public list; an unused one can be deleted), and its own emails through her mail service -
sign-in codes + password reset (the code hashed, never logged, the answer never says who has an account) and receipts
that repeat nothing the visitor typed."""
import io
import json
import re
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0455_suraksha import _google, _jwks, _key, _token
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CID = "1234567890-abcdefgh12.apps.googleusercontent.com"
APP = Path(__file__).resolve().parents[1] / "app"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.67"


def _linked(sid, key=""):
    from app.main import app
    from app.site import service as S
    c = TestClient(app, headers={"Authorization": f"Bearer {key}"} if key else None)
    S.design_app(T, sid, "customers apna order track karein")
    c.post(f"/api/sites/{sid}/link-app")
    return c


def _mail_on(monkeypatch):
    from app.config import get_settings
    from app.site import sitemail as SM
    monkeypatch.setattr(get_settings(), "site_mail_provider", "capture")
    SM.CAPTURED.clear()


def _wait_mail():
    for t in threading.enumerate():
        if t.name == "site-mail":
            t.join(10)


def test_google_sign_in_on_a_website(app_site):
    from app.appmaker import sign as SG
    from app.site import gsignin as GS
    sid = app_site
    c = _linked(sid)
    api = f"/api/site-app/{sid}"
    v = c.get(f"/api/sites/{sid}/signin").json()
    assert v["on"] is False and v["ready"] is False and isinstance(v["origins"], list) and "Authorized JavaScript origins" in v["how"]
    assert "google" not in c.get(f"{api}/schema").json()["sign"]["ways"]
    assert not GS.on(sid)
    assert c.put(f"/api/sites/{sid}/signin", json={"on": True, "client_id": "not-a-client-id"}).status_code == 400
    assert c.put(f"/api/sites/{sid}/signin", json={"on": True}).status_code == 400                 # no client id yet
    r = c.put(f"/api/sites/{sid}/signin", json={"on": True, "client_id": CID}).json()
    assert r["on"] and r["ready"] and r["client_id"] == CID and "on" in r["say"]
    sch = c.get(f"{api}/schema").json()
    assert "google" in sch["sign"]["ways"] and sch["sign"]["google_server_client_id"] == CID
    # the CSP lets Google's sign-in in for THIS site only
    assert GS.on(sid) and GS.on(sid + "~p")
    csp = GS.headers({"Content-Security-Policy": "default-src 'self'; script-src 'self'; frame-src https://www.google.com; "
                                                 "connect-src 'self'; style-src 'self' 'unsafe-inline'"}, sid)["Content-Security-Policy"]
    assert "script-src 'self' https://accounts.google.com/gsi/client" in csp
    assert "frame-src https://www.google.com https://accounts.google.com/gsi/" in csp
    assert "connect-src 'self' https://accounts.google.com/gsi/" in csp and "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style" in csp
    assert "unsafe-eval" not in csp and "accounts.google.com" not in GS.headers({"Content-Security-Policy": "script-src 'self'"}, "other")[
        "Content-Security-Policy"]
    good, evil = _key(), _key()
    SG._JWKS.clear()                        # an earlier suite's fake Google keys must not answer for this one
    SG.set_fetch(lambda url: _jwks(good.public_key()))
    try:
        # a password member first: the same email via Google is the same person
        a = c.post(f"{api}/signup", json={"email": "asha@gmail.com", "password": "asha-pass-1", "name": "Asha", "consent": True}).json()
        n = c.post(f"{api}/google/nonce").json()["nonce"]
        forged = _token(evil, _google(nonce=n, aud=CID))
        assert c.post(f"{api}/google", json={"id_token": forged, "nonce": n, "consent": True}).status_code == 401
        n = c.post(f"{api}/google/nonce").json()["nonce"]
        other = _token(good, _google(nonce=n, aud="999-someoneelse1.apps.googleusercontent.com"))
        assert c.post(f"{api}/google", json={"id_token": other, "nonce": n}).status_code == 401
        n = c.post(f"{api}/google/nonce").json()["nonce"]
        same = c.post(f"{api}/google", json={"id_token": _token(good, _google(nonce=n, aud=CID)), "nonce": n}).json()
        assert same["new"] is False and same["me"]["id"] == a["me"]["id"]
        assert c.post(f"{api}/google", json={"id_token": _token(good, _google(nonce=n, aud=CID)), "nonce": n}).status_code == 401   # nonce spent
        # a new person: the privacy tick first (the nonce survives the refusal)
        n = c.post(f"{api}/google/nonce").json()["nonce"]
        t2 = _token(good, _google(sub="g-2", email="ravi@gmail.com", nonce=n, aud=CID))
        assert c.post(f"{api}/google", json={"id_token": t2, "nonce": n}).status_code == 400
        new = c.post(f"{api}/google", json={"id_token": t2, "nonce": n, "consent": True}).json()
        assert new["new"] is True and new["me"]["email"] == "ravi@gmail.com"
        me = c.get(f"{api}/me", headers={"Authorization": "Bearer " + new["token"]}).json()["me"]
        assert me["email"] == "ravi@gmail.com"
    finally:
        SG.set_fetch(None)
        SG._JWKS.clear()            # the test's fake Google keys must not stay cached for the next suite
    off = c.put(f"/api/sites/{sid}/signin", json={"on": False}).json()
    assert off["ready"] is False and "google" not in c.get(f"{api}/schema").json()["sign"]["ways"] and not GS.on(sid)


def test_email_codes_sign_in_and_reset(app_site, monkeypatch):
    from app.site import sitemail as SM
    sid = app_site
    c = _linked(sid)
    api = f"/api/site-app/{sid}"
    assert c.get(f"{api}/schema").json()["security"]["email_code"] is False                     # no mail service yet
    assert c.post(f"{api}/email-code/start", json={"email": "a@x.in"}).status_code == 503
    _mail_on(monkeypatch)
    assert c.get(f"{api}/schema").json()["security"]["email_code"] is True
    a = c.post(f"{api}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha", "consent": True}).json()
    old = {"Authorization": "Bearer " + a["token"]}
    # nobody with this email: the same answer, and nothing is sent
    ghost = c.post(f"{api}/email-code/start", json={"email": "nobody@x.in", "purpose": "reset"}).json()
    real = c.post(f"{api}/email-code/start", json={"email": "asha@x.in", "purpose": "reset"}).json()
    assert ghost["say"] == real["say"] and ghost["ok"] and real["sent_to"] == "a***a@x.in"
    assert [m["to"] for m in SM.CAPTURED] == ["asha@x.in"]
    mail = SM.CAPTURED[-1]
    assert mail["subject"].startswith("Reset your password") and "ignore this" in mail["body"]
    code = re.search(r"\b(\d{6})\b", mail["body"]).group(1)
    bad = "000000" if code != "000000" else "111111"
    assert c.post(f"{api}/email-code/verify", json={"email": "asha@x.in", "code": bad, "purpose": "reset",
                                                    "password": "new-pass-22"}).status_code == 400
    assert c.post(f"{api}/email-code/verify", json={"email": "asha@x.in", "code": code, "purpose": "reset",
                                                    "password": "short"}).status_code == 400           # the code is kept
    ok = c.post(f"{api}/email-code/verify", json={"email": "asha@x.in", "code": code, "purpose": "reset", "password": "new-pass-22"}).json()
    assert ok["token"] and ok["say"] == "Your new password is set."
    assert c.get(f"{api}/me", headers=old).json()["me"] is None                                 # signed out everywhere
    assert c.post(f"{api}/login", json={"email": "asha@x.in", "password": "new-pass-22"}).status_code == 200
    assert c.post(f"{api}/email-code/verify", json={"email": "asha@x.in", "code": code, "purpose": "reset",
                                                    "password": "again-pass-3"}).status_code == 400       # a code works once
    # a new visitor signs in with a code (the tick first)
    c.post(f"{api}/email-code/start", json={"email": "ravi@x.in", "purpose": "login"})
    code2 = re.search(r"\b(\d{6})\b", SM.CAPTURED[-1]["body"]).group(1)
    assert SM.CAPTURED[-1]["subject"].startswith("Your sign-in code")
    assert c.post(f"{api}/email-code/verify", json={"email": "ravi@x.in", "code": code2, "purpose": "login"}).status_code == 400
    new = c.post(f"{api}/email-code/verify", json={"email": "ravi@x.in", "code": code2, "purpose": "login", "name": "Ravi",
                                                   "consent": True}).json()
    assert new["me"]["email"] == "ravi@x.in" and new["me"]["name"] == "Ravi"
    # the log has no code and no full address; the Studio switch turns codes off
    m = c.get(f"/api/sites/{sid}/mail").json()
    blob = json.dumps(m)
    assert code not in blob and code2 not in blob and "asha@x.in" not in blob and m["sent_today"] == 2
    assert {x["kind"] for x in m["log"]} == {"reset_code", "login_code"}
    c.put(f"/api/sites/{sid}/mail", json={"codes": False})
    assert c.get(f"{api}/schema").json()["security"]["email_code"] is False
    assert c.post(f"{api}/email-code/start", json={"email": "asha@x.in"}).status_code == 503


def test_receipts_say_nothing_the_visitor_typed(app_site, monkeypatch):
    from app.config import get_settings
    from app.site import sitemail as SM
    sid = app_site
    c = _linked(sid)
    api = f"/api/site-app/{sid}"
    _mail_on(monkeypatch)
    a = c.post(f"{api}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha", "consent": True}).json()
    ha = {"Authorization": "Bearer " + a["token"]}
    c.post(f"{api}/c/orders", headers=ha, json={"item": "Kaju katli SECRET-WORDS", "phone": "9876500000"})
    _wait_mail()
    assert SM.CAPTURED == []                                                                      # off until she turns it on
    assert c.put(f"/api/sites/{sid}/mail", json={"receipts": ["nope"]}).status_code == 400
    assert c.put(f"/api/sites/{sid}/mail", json={"receipts": ["orders"], "reply_to": "shop@sharma.in"}).json()["receipts"] == ["orders"]
    row = c.post(f"{api}/c/orders", headers=ha, json={"item": "Kaju katli SECRET-WORDS", "phone": "9876500000"}).json()
    _wait_mail()
    assert len(SM.CAPTURED) == 1
    got = SM.CAPTURED[0]
    assert got["to"] == "asha@x.in" and got["reply_to"] == "shop@sharma.in" and row["id"][-8:] in got["body"]
    assert "SECRET-WORDS" not in got["body"] + got["subject"] and "9876500000" not in got["body"]
    # the daily cap holds
    monkeypatch.setattr(get_settings(), "site_mail_daily", 1)
    c.post(f"{api}/c/orders", headers=ha, json={"item": "Laddoo", "phone": "9876500000"})
    _wait_mail()
    assert len(SM.CAPTURED) == 1
    assert c.get(f"/api/sites/{sid}/mail").json()["log"][0]["why"] == "daily limit reached"


def test_files_are_private_and_listed_for_her(app_site):
    from PIL import Image
    from app.appmaker import backend as BE
    from app.site import applink as AL
    from app.site import service as S
    sid = app_site
    c = _linked(sid)
    api = f"/api/site-app/{sid}"
    p = AL.project(S._load(sid))
    BE.change_schema(p, {"add_list": [{"key": "proofs", "label": "Proofs", "rules": {"create": "member", "read": "own"},
                                       "fields": [{"key": "note", "type": "text"}, {"key": "pic", "type": "photo"}]}]}, "test")
    a = c.post(f"{api}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "consent": True}).json()
    b = c.post(f"{api}/signup", json={"email": "ravi@x.in", "password": "ravi-pass-1", "consent": True}).json()
    ha, hb = {"Authorization": "Bearer " + a["token"]}, {"Authorization": "Bearer " + b["token"]}
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 10, 10)).save(buf, "PNG")
    up = c.post(f"{api}/upload", headers=ha, content=buf.getvalue()).json()
    fid = up["id"]
    assert c.get(f"{api}/file/{fid}", headers=ha).status_code == 200
    assert c.get(f"{api}/file/{fid}", headers=hb).status_code == 404                              # another member
    assert c.get(f"{api}/file/{fid}").status_code == 404                                          # a visitor
    fl = c.get(f"/api/sites/{sid}/files").json()
    one = next(x for x in fl["files"] if x["id"] == fid)
    assert one["public"] is False and one["used_in"] == [] and one["kind"] == "photo" and one["size"] > 0 and fl["bytes"] >= one["size"]
    assert "private" in fl["say"].lower()
    row = c.post(f"{api}/c/proofs", headers=ha, json={"note": "x", "pic": fid}).json()
    used = next(x for x in c.get(f"/api/sites/{sid}/files").json()["files"] if x["id"] == fid)
    assert used["used_in"] == [{"list": "proofs", "row": row["id"]}]
    assert c.delete(f"/api/sites/{sid}/files/{fid}").status_code == 409                          # an entry holds it
    up2 = c.post(f"{api}/upload", headers=ha, content=buf.getvalue()).json()["id"]
    assert c.delete(f"/api/sites/{sid}/files/{up2}").json()["ok"]
    assert all(x["id"] != up2 for x in c.get(f"/api/sites/{sid}/files").json()["files"])
    assert c.delete(f"/api/sites/{sid}/files/../../etc").status_code in (400, 404, 405)


def test_a_preview_copy_never_sends_email(app_site, monkeypatch):
    from app.site import applink as AL
    from app.site import service as S
    from app.site import sitemail as SM
    from app.site import twin as TW
    sid = app_site
    _linked(sid)
    _mail_on(monkeypatch)
    main = AL.project(S._load(sid))
    tw = TW.make(main, "preview")
    assert SM.public(main)["codes"] is True and SM.public(tw)["codes"] is False
    assert SM.send(tw, "Sharma", "asha@x.in", "receipt", "x", "y") is False and SM.CAPTURED == []
    TW.drop(tw.id)


def test_the_page_script_and_wiring():
    js = (APP / "site" / "assets" / "hoola-app.js").read_text()
    assert "https://accounts.google.com/gsi/client" in js and "renderButton" in js and "'/google/nonce'" in js
    assert "'/email-code/start'" in js and "'/email-code/verify'" in js and "sec.email_code" in js and "t.forgot" in js
    ws = (APP / "static" / "console" / "webstudio.js").read_text()
    assert 'data-coll="__signin">Sign-in' in ws and 'data-coll="__files">Files' in ws and 'data-coll="__mail">Emails' in ws
    assert "accessPane" in ws and "/signin`" in ws and "/files`" in ws and "/mail`" in ws
    import inspect
    from app.site import hosting as H
    assert "GS.headers(h" in inspect.getsource(H._sec_headers)
    src = (APP / "site" / "sitemail.py").read_text()
    assert "log.warning(\"site mail %s to %s failed: %s\", kind, mask(to), type(e).__name__)" in src   # never the code or the text


def test_sign_in_files_and_emails_in_a_browser(app_site, arena_server, monkeypatch):
    from tests.test_v0808_wapas import _fast_checks
    _fast_checks(monkeypatch)
    _mail_on(monkeypatch)
    base, browser, key = arena_server
    sid = app_site
    c = _linked(sid, key)
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{base}/console/web#/site/{sid}")
    page.locator('[data-view="cloud"]').first.wait_for(timeout=30000)
    page.click('[data-view="cloud"]')
    page.locator("#wsRowAdd").wait_for(timeout=20000)
    page.click('[data-coll="__signin"]')
    page.locator("#wsGForm").wait_for(timeout=20000)
    page.fill("#wsGForm input[name=client_id]", CID)
    page.check("#wsGForm input[name=on]")
    page.click("#wsGForm button[type=submit]")
    page.locator("#wsGForm .pill:has-text('On'), #wsGForm :text('On')").first.wait_for(timeout=20000)
    assert c.get(f"/api/sites/{sid}/signin").json()["ready"] is True
    page.click('[data-coll="__mail"]')
    page.locator("#wsMailForm").wait_for(timeout=20000)
    page.check("#wsMailForm input[value=orders]")
    page.click("#wsMailForm button[type=submit]")
    page.wait_for_function("() => true", timeout=2000)
    for _ in range(40):
        if c.get(f"/api/sites/{sid}/mail").json()["receipts"] == ["orders"]:
            break
        page.wait_for_timeout(250)
    assert c.get(f"/api/sites/{sid}/mail").json()["receipts"] == ["orders"]
    page.click('[data-coll="__files"]')
    page.locator("#wsCloud h2:has-text('Files')").wait_for(timeout=20000)
    assert "private" in page.inner_text("#wsCloud").lower()
    ctx.close()
    assert not errors, errors
