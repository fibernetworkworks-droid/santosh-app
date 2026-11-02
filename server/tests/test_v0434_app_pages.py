"""v0.434 APP PAGES + LOGIN AUR SURAKSHA (web Step 3 = W2 + W3 of docs/WEB_PLATFORM_PLAN.md).

W2: the website's app pages are a real in-page app per area (member / staff) - menu per role, tables with sort / search /
filter / pages / bulk select, detail pages with linked lists, multi-step forms with checks + uploads, kanban, calendar.
W3: phone OTP (hash only, expiry, tries, rate limits, consent for a new account), staff 2-step login (TOTP), sessions
(one / all ended), DPDP consent + export + delete, the audit log with WHO, private (staff-only) fields, the matrix."""
import json
import os

import pytest
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.446.0"


@pytest.fixture
def linked(app_site, monkeypatch):
    from app.config import get_settings
    from app.site import service as S
    monkeypatch.setattr(get_settings(), "site_sms_provider", "capture")
    monkeypatch.setattr(get_settings(), "secret_key", "test-secret-key-for-2fa-only-0123456789")   # the 2FA key is encrypted
    S.design_app(T, app_site, "customers apna order track karein")
    return app_site


def _signup(c, base, email, name, consent=True):
    return c.post(f"{base}/signup", json={"email": email, "password": "pass-word-1", "name": name, "consent": consent})


def _h(tok):
    return {"Authorization": "Bearer " + tok}


# ---------------------------------------------------------------- pure pieces
def test_totp_matches_rfc6238_and_phone_numbers_are_checked():
    from app.site import security as SEC
    from app.site import webapp as W
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"               # RFC 6238 test key "12345678901234567890"
    assert SEC._totp_at(secret, 59) == "287082" and SEC._totp_at(secret, 1111111109) == "081804"
    assert SEC.totp_ok(secret, "287082", at=59) and SEC.totp_ok(secret, "287082", at=80)   # one step of clock drift
    assert not SEC.totp_ok(secret, "287083", at=59) and not SEC.totp_ok(secret, "12", at=59)
    assert SEC.phone10("+91 98765 43210") == "9876543210" and SEC.phone10("09876543210") == "9876543210"
    for bad in ("12345", "5876543210", "abcdefghij"):
        with pytest.raises(W.AppError):
            SEC.phone10(bad)


# ---------------------------------------------------------------- phone OTP
def test_phone_otp_login_hash_only_expiry_tries_consent_and_limits(linked, monkeypatch):
    from app.config import get_settings
    from app.db import session
    from app.main import app
    from app.site import security as SEC
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    assert c.get(f"{base}/schema").json()["security"]["otp"] is True
    r = c.post(f"{base}/otp/start", json={"phone": "98765 43210"}).json()
    assert r["sent_to"] == "98******10"
    code = SEC.CAPTURED["9876543210"]
    with session() as s:                                                  # only the hash is kept
        row = s.query(SEC.SiteAppOtp).filter_by(phone="9876543210").one()
        assert code not in row.code_h and len(row.code_h) == 64
    assert c.post(f"{base}/otp/verify", json={"phone": "9876543210", "code": "000000"}).status_code == 400
    r = c.post(f"{base}/otp/verify", json={"phone": "9876543210", "code": code})
    assert r.status_code == 400 and "privacy" in r.json()["error"]       # a NEW account needs her tick
    ok = c.post(f"{base}/otp/verify", json={"phone": "9876543210", "code": code, "name": "Meena", "consent": True}).json()
    assert ok["me"]["phone"] == "98******10" and ok["token"]
    assert c.get(f"{base}/me", headers=_h(ok["token"])).json()["me"]["name"] == "Meena"
    assert c.post(f"{base}/otp/verify", json={"phone": "9876543210", "code": code}).status_code == 400   # used once
    # the same number next time logs into the SAME account (no consent asked again)
    c.post(f"{base}/otp/start", json={"phone": "9876543210"})
    again = c.post(f"{base}/otp/verify", json={"phone": "9876543210", "code": SEC.CAPTURED["9876543210"]}).json()
    assert again["me"]["id"] == ok["me"]["id"]
    c.post(f"{base}/otp/start", json={"phone": "9876543210"})
    assert c.post(f"{base}/otp/start", json={"phone": "9876543210"}).status_code == 429   # 3 codes per 10 minutes
    # five wrong tries burn the code
    c.post(f"{base}/otp/start", json={"phone": "9123456780"})
    for _ in range(5):
        c.post(f"{base}/otp/verify", json={"phone": "9123456780", "code": "111111"})
    r = c.post(f"{base}/otp/verify", json={"phone": "9123456780", "code": SEC.CAPTURED["9123456780"]})
    assert r.status_code == 429
    monkeypatch.setattr(get_settings(), "site_sms_provider", "")
    assert c.post(f"{base}/otp/start", json={"phone": "9000000001"}).status_code == 503       # no SMS = says so
    assert c.get(f"{base}/schema").json()["security"]["otp"] is False


# ---------------------------------------------------------------- consent, 2-step, sessions, export, delete
def test_signup_consent_is_recorded_and_required_on_new_pages(linked):
    from app.db import session
    from app.main import app
    from app.site import webapp as W
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    assert _signup(c, base, "no@x.in", "No", consent=False).status_code == 400
    assert _signup(c, base, "yes@x.in", "Yes").status_code == 200
    old = c.post(f"{base}/signup", json={"email": "old@x.in", "password": "pass-word-1"})   # a page built before v0.434
    assert old.status_code == 200
    with session() as s:
        got = {m.email: m.consent for m in s.query(W.SiteAppMember).all()}
    assert json.loads(got["yes@x.in"])["v"] == 1 and got["old@x.in"] is None and "no@x.in" not in got


def test_staff_two_step_login_sessions_and_sign_out_everywhere(linked):
    from app.main import app
    from app.site import security as SEC
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    a = _signup(c, base, "ravi@x.in", "Ravi").json()
    assert c.post(f"{base}/2fa/start", headers=_h(a["token"])).status_code == 403          # members do not need it
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{linked}/app/members").json()["members"]}
    c.post(f"/api/sites/{linked}/app/members/{mem['ravi@x.in']}/role", json={"role": "staff"})
    ua1 = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/120.0 Mobile"}
    ua2 = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/120.0"}
    t1 = c.post(f"{base}/login", json={"email": "ravi@x.in", "password": "pass-word-1"}, headers=ua1).json()["token"]
    st = c.post(f"{base}/2fa/start", headers=_h(t1)).json()
    assert st["uri"].startswith("otpauth://totp/") and len(st["secret"]) >= 32
    assert c.post(f"{base}/2fa/confirm", headers=_h(t1), json={"code": "000000"}).status_code == 400
    import time
    assert c.post(f"{base}/2fa/confirm", headers=_h(t1), json={"code": SEC._totp_at(st["secret"], int(time.time()))}).json()["two_fa"]
    step = c.post(f"{base}/login", json={"email": "ravi@x.in", "password": "pass-word-1"}, headers=ua2).json()
    assert step.get("need_2fa") and "token" not in step                                   # password alone is not enough
    assert c.post(f"{base}/2fa/login", json={"ticket": step["ticket"], "code": "123456"}).status_code == 400
    assert c.post(f"{base}/2fa/login", json={"ticket": step["ticket"][:-2] + "00", "code": "1"}).status_code == 401
    t2 = c.post(f"{base}/2fa/login", headers=ua2,
                json={"ticket": step["ticket"], "code": SEC._totp_at(st["secret"], int(time.time()))}).json()["token"]
    ses = c.get(f"{base}/sessions", headers=_h(t2)).json()["sessions"]
    assert {"Chrome on Android", "Chrome on Windows"} <= {s["device"] for s in ses} and sum(s["this"] for s in ses) == 1
    other = next(s for s in ses if s["device"] == "Chrome on Android")
    c.post(f"{base}/sessions/{other['id']}/end", headers=_h(t2))
    assert c.get(f"{base}/me", headers=_h(t1)).json()["me"] is None                      # that device is logged out
    assert c.get(f"{base}/me", headers=_h(t2)).json()["me"]["two_fa"] is True
    c.post(f"{base}/logout-all", headers=_h(t2))
    assert c.get(f"{base}/me", headers=_h(t2)).json()["me"] is None


def test_export_and_delete_my_data_and_private_fields(linked):
    from app.appmaker import backend as BE
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    p = AL.project(S._load(linked))
    BE.change_schema(p, {"add": [{"coll": "orders", "key": "cost", "label": "Cost price", "type": "number", "private": True}]}, "cost")
    a = _signup(c, base, "asha@x.in", "Asha").json()
    b = _signup(c, base, "boss@x.in", "Boss").json()
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{linked}/app/members").json()["members"]}
    c.post(f"/api/sites/{linked}/app/members/{mem['boss@x.in']}/role", json={"role": "admin"})
    hb = _h(c.post(f"{base}/login", json={"email": "boss@x.in", "password": "pass-word-1"}).json()["token"])
    ha = _h(a["token"])
    row = c.post(f"{base}/c/orders", headers=ha, json={"item": "Barfi", "phone": "9876500000", "cost": 5}).json()
    c.patch(f"{base}/c/orders/{row['id']}", headers=hb, json={"cost": 40})
    assert "cost" not in c.get(f"{base}/c/orders", headers=ha).json()["rows"][0]          # staff-only field
    assert c.get(f"{base}/c/orders", headers=hb).json()["rows"][0]["cost"] == 40
    m = {x["list"]: x for x in c.get(f"{base}/matrix", headers=hb).json()["matrix"]}
    assert m["orders"]["staff_see"] == ["Cost price"] and m["orders"]["create"] == "login wale"
    # the audit log: who did what (admin only)
    assert c.get(f"{base}/audit", headers=ha).status_code == 403
    log_ = c.get(f"{base}/audit", headers=hb).json()["audit"]
    assert log_[0]["by"].startswith("Boss") and "cost" in log_[0]["fields"] and log_[1]["by"].startswith("Asha")
    own = c.get(f"/api/sites/{linked}/audit").json()
    assert own["linked"] and len(own["audit"]) >= 2 and own["matrix"]
    # her data: everything she owns, then gone
    ex = c.get(f"{base}/me/export", headers=ha).json()
    assert ex["account"]["email"] == "asha@x.in" and ex["account"]["consent"]["v"] == 1
    assert [x["item"] for x in ex["lists"]["Orders"]] == ["Barfi"] and "cost" not in ex["lists"]["Orders"][0]
    assert c.post(f"{base}/me/delete", headers=ha).json()["ok"]
    assert c.get(f"{base}/me", headers=ha).json()["me"] is None
    assert c.get(f"{base}/c/orders", headers=hb).json()["rows"] == []


# ---------------------------------------------------------------- the pages
def test_account_and_staff_pages_are_app_shells(linked):
    from app.site import build as B
    from app.site import service as S
    g = S.get(T, linked)
    out = B.out_dir(T, linked, g["version"])
    acct, adm = (out / "account" / "index.html").read_text(), (out / "admin" / "index.html").read_text()
    assert 'data-hoola-app="shell" data-area="member"' in acct and 'data-hoola-app="shell" data-area="staff"' in adm
    assert 'data-privacy="../privacy/"' in acct
    js = (out / "assets" / "hoola-app.js").read_text()
    for k in ("function table(", "function kanban(", "function calendar(", "function detail(", "function formView(",
              "/otp/start", "/2fa/login", "/me/export", "/logout-all", "hs-appx", "aria-sort"):
        assert k in js, k
    css = (out / "assets" / "site.css").read_text()
    assert ".hs-kanban" in css and ".hs-cal-grid" in css and ".hs-appx-table" in css


def test_app_pages_work_in_a_real_browser(linked):
    """Chromium opens the built account + staff pages; every API call goes to the real Hoola API (TestClient)."""
    pw = pytest.importorskip("playwright.sync_api")
    from app.main import app
    from app.site import build as B
    from app.site import service as S
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    _signup(c, base, "asha@x.in", "Asha")
    _signup(c, base, "boss@x.in", "Boss")
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{linked}/app/members").json()["members"]}
    c.post(f"/api/sites/{linked}/app/members/{mem['boss@x.in']}/role", json={"role": "admin"})
    ha = _h(c.post(f"{base}/login", json={"email": "asha@x.in", "password": "pass-word-1"}).json()["token"])
    for i, item in enumerate(["Kaju katli", "Barfi", "Laddoo"]):
        c.post(f"{base}/c/orders", headers=ha, json={"item": item, "qty": i + 1, "phone": "9876500000"})
    g = S.get(T, linked)
    out = B.out_dir(T, linked, g["version"])
    ORIGIN = "http://hoola.test"

    def handle(route):
        u = route.request.url
        path = u[len(ORIGIN):]
        if path.startswith("/api/"):
            h = {k: v for k, v in route.request.headers.items() if k.lower() in ("authorization", "content-type")}
            r = c.request(route.request.method, path, content=route.request.post_data_buffer, headers=h)
            return route.fulfill(status=r.status_code, body=r.content, headers={"content-type": r.headers.get("content-type", "application/json")})
        rel = path.split("?")[0].split("#")[0].lstrip("/")
        f = out / (rel + "index.html" if (not rel or rel.endswith("/")) else rel)
        if not f.exists():
            return route.fulfill(status=404, body="")
        ct = "text/html" if f.suffix == ".html" else "text/css" if f.suffix == ".css" else "application/javascript" if f.suffix == ".js" else "application/octet-stream"
        body = f.read_bytes()
        if f.suffix == ".html":                   # the page's API address points at our stand-in origin
            body = body.replace(f'content="/api/site-app/{linked}"'.encode(), f'content="{ORIGIN}/api/site-app/{linked}"'.encode())
        return route.fulfill(status=200, body=body, headers={"content-type": ct})

    exe = os.environ.get("HOOLA_CHROMIUM") or None
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = b.new_page()
        page.route(f"{ORIGIN}/**", handle)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        # the member: logs in, sees her own area, opens her table, sorts, searches, opens a row, fills the steps
        page.goto(f"{ORIGIN}/account/")
        page.wait_for_selector(".hs-app-login input[name=email]")
        page.fill(".hs-app-login input[name=email]", "asha@x.in")
        page.fill(".hs-app-login input[name=password]", "pass-word-1")
        page.click(".hs-app-login button[type=submit]")
        page.wait_for_selector(".hs-appx-nav a[data-r='c/orders']")
        assert page.locator(".hs-appx-nav a[data-r='audit']").count() == 0               # not in a member's menu
        page.click(".hs-appx-nav a[data-r='c/orders']")
        page.wait_for_selector(".hs-appx-table tbody tr")
        assert page.locator(".hs-appx-table tbody tr").count() == 3
        page.click(".hs-appx-table thead button:has-text('Item')")
        assert page.locator(".hs-appx-table tbody tr td a").first.text_content() == "Barfi"   # sorted A-Z
        page.fill(".hs-appx-tools input[type=search]", "lad")
        assert page.locator(".hs-appx-table tbody tr").count() == 1
        page.click(".hs-appx-table tbody tr td a")
        page.wait_for_selector(".hs-appx-dl")
        assert "Laddoo" in page.locator(".hs-appx-main h2").text_content()
        page.goto(f"{ORIGIN}/account/#/member/c/orders/new")
        page.wait_for_selector(".hs-app-form")
        page.click(".hs-app-form button[type=submit]")                                    # empty required field
        assert page.locator("[name=item][aria-invalid=true]").count() == 1                # checked before the trip
        page.fill(".hs-app-form [name=item]", "Rasgulla")
        page.fill(".hs-app-form [name=phone]", "12")
        page.click(".hs-app-form button[type=submit]")
        assert page.locator("[name=phone][aria-invalid=true]").count() == 1
        assert page.locator("[name=item][aria-invalid=false]").count() == 1
        page.fill(".hs-app-form [name=phone]", "9876500001")
        page.click(".hs-app-form button[type=submit]")
        page.wait_for_selector(".hs-form-msg.ok")
        # My account: this device, download my data
        page.goto(f"{ORIGIN}/account/#/member/me")
        page.wait_for_selector(".hs-appx-rel li")
        assert page.locator(".hs-appx-rel button").count() >= 2                            # sign out everywhere + data
        # the staff app: board + calendar views exist for the workflow list, audit is in the admin's menu
        page.click(".hs-app-me button")                                                    # log out
        page.goto(f"{ORIGIN}/admin/")
        page.wait_for_selector(".hs-app-login input[name=email]")
        page.fill(".hs-app-login input[name=email]", "boss@x.in")
        page.fill(".hs-app-login input[name=password]", "pass-word-1")
        page.click(".hs-app-login button[type=submit]")
        page.wait_for_selector(".hs-appx-nav a[data-r='audit']")
        page.goto(f"{ORIGIN}/admin/#/staff/c/orders/board")
        page.wait_for_selector(".hs-kanban .hs-lane")
        assert page.locator(".hs-lane").count() == 3 and page.locator(".hs-kcard").count() == 4
        page.goto(f"{ORIGIN}/admin/#/staff/c/orders")
        page.wait_for_selector(".hs-appx-table tbody tr")
        page.locator(".hs-appx-table tbody input[type=checkbox]").first.check()
        assert page.locator(".hs-appx-bulk").is_visible()
        page.goto(f"{ORIGIN}/admin/#/staff/audit")
        page.wait_for_selector(".hs-appx-main table tbody tr")
        page.goto(f"{ORIGIN}/admin/#/staff/matrix")
        page.wait_for_selector(".hs-appx-main table tbody tr")
        b.close()
    assert errors == []
