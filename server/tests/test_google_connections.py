"""v0.999.181 GOOGLE CONNECTIONS (owner: "NOW LETS WORK ON GMAIL, SHEET, FORM, DRIVE ETC CONNECTION TO HOOLA" -> the audit
-> design canvas -> "GO"): one place for every Google app, tied to the Hoola account she is signed in as, with the real
state of every account and app, reconnect, disconnect (revoked at Google) and which account an app uses first; plus the
audit's server fixes."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_signup_email import _google_on
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

APP = Path(__file__).resolve().parents[1] / "app"
ROOT = Path(__file__).resolve().parents[2]
G = "https://www.googleapis.com/auth/"
CORE_SCOPES = " ".join(["openid", "email", "profile", G + "gmail.modify", G + "gmail.settings.basic", G + "calendar",
                        G + "drive", G + "documents", G + "spreadsheets", G + "presentations"])


def _google(monkeypatch, email: str, scope: str, refresh: str = "rt-1", calls: list | None = None):
    """Google's token, profile and revoke answers, without the network."""
    def handler(req: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(req.url))
        if req.url.host == "oauth2.googleapis.com" and req.url.path == "/token":
            body = {"access_token": "at-" + email, "expires_in": 3600, "scope": scope}
            if refresh:
                body["refresh_token"] = refresh
            return httpx.Response(200, json=body)
        if req.url.path.endswith("/revoke"):
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"email": email, "email_verified": True, "name": "Asha", "sub": "g1"})
    from app.mailbox import accounts as mail_acc
    mail_acc.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    real = httpx.post

    def post(url, *a, **k):
        if "revoke" in str(url):
            if calls is not None:
                calls.append(str(url))
            return httpx.Response(200, json={})
        return real(url, *a, **k)
    monkeypatch.setattr(httpx, "post", post)


@pytest.fixture
def hub(env, monkeypatch):
    _google_on(monkeypatch)
    from app import googlehub
    from app.mailbox import accounts as mail_acc
    yield googlehub
    mail_acc.set_http(None)


def _state(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


def test_connect_is_tied_to_her_account_and_asks_google_properly(hub):
    from app.db import MailLinkState, session
    url = hub.start("tA", "core", "web")
    q = parse_qs(urlparse(url).query)
    sc = q["scope"][0].split()
    for need in ("gmail.modify", "calendar", "drive", "spreadsheets", "forms.body", "presentations", "documents"):
        assert G + need in sc
    assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"] and q["include_granted_scopes"] == ["true"]
    st = q["state"][0]
    assert st.startswith("ggl_w") and hub.surface_of(st) == "web" and hub._asked(st) == hub.CORE
    with session() as s:
        assert s.get(MailLinkState, st).tenant_id == "tA"
    ph = _state(hub.start("tA", ["photos"], "phone", hint="me@x.com"))
    assert hub.surface_of(ph) == "phone" and hub._asked(ph) == ["photos"]
    assert parse_qs(urlparse(hub.start("tA", ["youtube"], "web", hint="me@x.com")).query)["login_hint"] == ["me@x.com"]
    with pytest.raises(hub.HubError):
        hub.start("tA", ["nothing"])


def test_first_account_lands_on_her_connection_never_a_new_session(hub, monkeypatch):
    from app.db import AppSession, OAuthConnection, session
    with session() as s:
        n0 = s.query(AppSession).count()
    _google(monkeypatch, "asha@gmail.com", CORE_SCOPES)
    r = hub.finish("code", _state(hub.start("tA", "core")))
    assert r["tenant"] == "tA" and r["where"] == "main" and r["email"] == "asha@gmail.com"
    assert set(r["got"]) >= {"gmail", "calendar", "drive", "docs", "sheets", "slides"} and r["miss"] == ["forms"]
    with session() as s:
        assert s.query(AppSession).count() == n0          # no session, no account switch
        c = s.query(OAuthConnection).filter(OAuthConnection.user_id == "tA").one()
        assert c.refresh_token_enc and G + "gmail.modify" in c.scopes and c.last_error is None
    st = hub.status("tA")
    assert st["accounts"][0]["email"] == "asha@gmail.com" and st["accounts"][0]["first"]
    apps = {a["key"]: a["state"] for a in st["apps"]}
    assert apps["gmail"] == "ok" and apps["forms"] == "none" and apps["photos"] == "none"
    # every app reads it: the per-app modules see the account
    from app.cal import accounts as ca
    from app.drive import accounts as da
    from app.mailbox import accounts as ma
    assert [b.address for b in ma.boxes("tA")] == ["asha@gmail.com"]
    assert [b.address for b in ca.boxes("tA")] == ["asha@gmail.com"]
    assert [b.address for b in da.clients("tA")] == ["asha@gmail.com"]


def test_a_second_account_reaches_every_app_and_can_be_used_first(hub, monkeypatch):
    _google(monkeypatch, "asha@gmail.com", CORE_SCOPES)
    hub.finish("c", _state(hub.start("tA", "core")))
    _google(monkeypatch, "office@biz.com", CORE_SCOPES + " " + G + "forms.body", refresh="rt-2")
    r = hub.finish("c", _state(hub.start("tA", "core")))
    assert r["where"] == "extra" and "forms" in r["got"]
    from app.drive import accounts as da
    from app.forms import accounts as fa
    from app.mailbox import accounts as ma
    assert {b.address for b in ma.boxes("tA")} == {"asha@gmail.com", "office@biz.com"}
    assert [c.address for c in fa.clients("tA")] == ["office@biz.com"]
    st = hub.status("tA")
    assert {a["email"] for a in st["accounts"]} == {"asha@gmail.com", "office@biz.com"}
    gm = next(a for a in st["apps"] if a["key"] == "gmail")
    assert set(gm["working"]) == {"asha@gmail.com", "office@biz.com"}
    hub.set_first("tA", "drive", "asha@gmail.com")
    assert da.clients("tA")[0].address == "asha@gmail.com"
    hub.set_first("tA", "drive", "office@biz.com")
    assert da.clients("tA")[0].address == "office@biz.com"
    with pytest.raises(hub.HubError):
        hub.set_first("tA", "drive", "stranger@x.com")


def test_an_account_google_refused_shows_reconnect_and_goes_last(hub, monkeypatch):
    from app.db import CalendarAccount, OAuthConnection, session
    _google(monkeypatch, "asha@gmail.com", CORE_SCOPES)
    hub.finish("c", _state(hub.start("tA", "core")))
    _google(monkeypatch, "office@biz.com", CORE_SCOPES, refresh="rt-2")
    hub.finish("c", _state(hub.start("tA", "core")))
    with session() as s:
        row = s.query(CalendarAccount).filter(CalendarAccount.address == "office@biz.com").one()
        row.status, row.last_error = "error", "invalid_grant"
    hub.set_first("tA", "calendar", "office@biz.com")
    from app.cal import accounts as ca
    assert ca.boxes("tA")[0].address == "office@biz.com"        # her choice wins
    with session() as s:
        s.query(OAuthConnection).filter(OAuthConnection.user_id == "tA").one().last_error = "invalid_grant"
    st = hub.status("tA")
    assert all(a["state"] == "expired" for a in st["accounts"])
    cal = next(a for a in st["apps"] if a["key"] == "calendar")
    assert cal["state"] == "expired" and "office@biz.com" in cal["expired"]
    assert hub.summary("tA")["expired"] == 2


def test_disconnect_revokes_at_google_and_one_app_only_stops_that_app(hub, monkeypatch):
    from app.db import OAuthConnection, session
    calls: list = []
    _google(monkeypatch, "asha@gmail.com", CORE_SCOPES, calls=calls)
    hub.finish("c", _state(hub.start("tA", "core")))
    hub.disconnect("tA", "asha@gmail.com", "gmail")
    st = {a["key"]: a["state"] for a in hub.status("tA")["apps"]}
    assert st["gmail"] == "none" and st["calendar"] == "ok"
    assert not any("revoke" in u for u in calls)
    r = hub.disconnect("tA", "asha@gmail.com")
    assert r["revoked"] and any("revoke" in u for u in calls)
    with session() as s:
        c = s.query(OAuthConnection).filter(OAuthConnection.user_id == "tA").one()
        assert c.refresh_token_enc is None and "gmail" not in c.scopes
    assert hub.status("tA")["accounts"] == []
    with pytest.raises(hub.HubError):
        hub.disconnect("tA", "nobody@x.com")


def test_callback_goes_back_to_where_she_started(hub, monkeypatch):
    from app.main import app
    _google(monkeypatch, "asha@gmail.com", CORE_SCOPES)
    c = TestClient(app)
    r = c.get("/auth/google/callback", params={"code": "c", "state": _state(hub.start("tA", "core", "web"))},
              follow_redirects=False)
    loc = r.headers["location"]
    assert r.status_code in (302, 307) and loc.startswith("/console/?v=connectors&a=google&gconn=ok")
    q = parse_qs(urlparse(loc).query)
    assert "gmail" in q["got"][0] and q["miss"] == ["forms"] and "asha" not in loc
    r = c.get("/auth/google/callback", params={"code": "c", "state": _state(hub.start("tA", "core", "phone"))})
    assert "santosh://google?ok=1" in r.text and "Back to Hoola" in r.text
    r = c.get("/auth/google/callback", params={"error": "access_denied", "state": _state(hub.start("tA", "core", "web"))},
              follow_redirects=False)
    assert "gconn=err" in r.headers["location"]


def test_routes_need_her_key(hub, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    from app.config import get_settings
    get_settings.cache_clear()
    _google_on(monkeypatch)
    from app.main import app
    c = TestClient(app)
    for m, p in (("GET", "/api/google"), ("POST", "/api/google/connect"), ("POST", "/api/google/disconnect"),
                 ("POST", "/api/google/first")):
        assert c.request(m, p, json={}).status_code == 401
    h = {"Authorization": "Bearer secret-key"}
    assert "apps" in c.get("/api/google", headers=h).json()
    url = c.post("/api/google/connect", json={"apps": ["core"]}, headers=h).json()["url"]
    assert url.startswith("https://accounts.google.com/") and "ggl_w" in url


def test_a_sign_in_never_wipes_the_google_apps_connection(hub, monkeypatch):
    import asyncio
    from app import accounts
    from app.db import OAuthConnection, User, session
    with session() as s:
        u = User(email="asha@gmail.com", name="Asha")
        s.add(u)
        s.flush()
        uid = u.id
        s.add(OAuthConnection(user_id=uid, provider="google", account_email="office@biz.com",
                              refresh_token_enc=accounts.encrypt("rt-office"), scopes=CORE_SCOPES, last_error="invalid_grant"))

    def handler(req):
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "expires_in": 3600, "scope": "openid email profile"})
        return httpx.Response(200, json={"email": "asha@gmail.com", "email_verified": True, "name": "Asha", "sub": "g"})
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real(*a, **{**k, "transport": httpx.MockTransport(handler)}))
    st = parse_qs(urlparse(accounts.start_google(web=True)).query)["state"][0]
    asyncio.run(accounts.finish_google("c", st))
    with session() as s:
        c = s.query(OAuthConnection).filter(OAuthConnection.user_id == uid).one()
        assert c.account_email == "office@biz.com" and accounts.decrypt(c.refresh_token_enc) == "rt-office"
        assert G + "gmail.modify" in c.scopes and c.last_error == "invalid_grant"   # still honestly expired


def test_credentials_refresh_by_themselves_when_expired(hub, monkeypatch):
    from datetime import timedelta
    from app import accounts, google_auth
    from app.db import OAuthConnection, now, session
    with session() as s:
        s.add(OAuthConnection(user_id="tA", provider="google", account_email="a@b.co", scopes=CORE_SCOPES,
                              access_token_enc=accounts.encrypt("old"), refresh_token_enc=accounts.encrypt("rt"),
                              expiry=now() - timedelta(minutes=5)))
    seen = {}
    monkeypatch.setattr(google_auth, "refresh", lambda creds, t, e="": seen.setdefault("refreshed", True))
    monkeypatch.setattr(google_auth, "save_token", lambda *a, **k: None)
    google_auth.credentials_for("tA")
    assert seen.get("refreshed")


def test_mail_watcher_finds_her_google_gmail(hub, monkeypatch):
    from app import accounts
    from app.db import OAuthConnection, User, session
    from app.mailbox import sync
    with session() as s:
        u = User(email="w@x.com", name="W")
        s.add(u)
        s.flush()
        s.add(OAuthConnection(user_id=u.id, provider="google", account_email="w@x.com", scopes=CORE_SCOPES,
                              refresh_token_enc=accounts.encrypt("rt")))
        uid = u.id
    assert accounts.tenant_of_user(uid) in sync.watcher_tenants()


def test_an_expired_mailbox_is_not_asked_every_minute(hub):
    from app.db import MailAccount, session
    from app.mailbox import accounts as ma
    from app.mailbox import sync
    with session() as s:
        s.add(MailAccount(id="mbx1", tenant_id="tA", kind="gmail", address="o@b.co", status="error", last_error=ma.RECONNECT))
        s.add(MailAccount(id="mbx2", tenant_id="tA", kind="gmail", address="p@b.co", status="error", last_error="timeout"))
    dead = sync._dead_boxes()
    assert "mbx1" in dead and "mbx2" not in dead


def test_sheets_and_drive_tools_come_up_with_their_asks():
    from app.agent import tools as T
    for n in ("sheet_read", "sheet_append"):
        assert T.FAMILY_OF[n] == "sheets"
    for n in ("drive_find", "drive_read_file"):
        assert T.FAMILY_OF[n] == "drive"
    from app.agent import admit
    assert "share the file" in admit.EXTRA_KEYS["drive"]


def test_not_connected_sends_one_card_with_the_button(hub, monkeypatch):
    from app.agent import tools as T
    from app.events import bus
    got = []
    monkeypatch.setattr(bus, "publish", lambda conv, kind, p: got.append((kind, p)))

    class Ctx:
        tenant_id, conversation_id = "tA", "cv1"
    e = T.ToolError("Your Google Forms are not connected to Hoola yet. On the web console open Connectors > Google, or in "
                    "the phone app open Settings > Google, and press Connect.")
    T._google_card(Ctx(), "form_create", e, "")
    T._google_card(Ctx(), "form_create", e, "")            # once, not twice
    assert len(got) == 1 and got[0][0] == "google_connect" and got[0][1]["app"] == "forms"
    T._google_card(Ctx(), "weather_now", e, "")             # not a Google tool: no card
    assert len(got) == 1


def test_messages_point_to_the_new_place_and_pages_are_english():
    for p in ("drive/accounts.py", "sheets/accounts.py", "cal/accounts.py", "forms/accounts.py", "slides/accounts.py",
              "photos/accounts.py", "youtube/accounts.py", "google_auth.py"):
        src = (APP / p).read_text()
        code = src.split('"""', 2)[-1]                     # past the module docstring
        assert "Connectors > Google" in src and "Profile > " not in code.replace("# ", ""), p
    for p in ("drive/api.py", "photos/api.py", "forms/api.py"):
        src = (APP / p).read_text()
        assert "kholiye" not in src and "Santosh se" not in src and "Back to Hoola" in src


def test_console_and_phone_are_wired():
    cx = (APP / "static/console/connectors.js").read_text()
    for need in ("['google', 'Google']", "function googleView", "/api/google/connect", "/api/google/disconnect",
                 "/api/google/first", "function gResult", "Connect everyday apps"):
        assert need in cx, need
    v2 = (APP / "static/console/v2.js").read_text()
    assert "window.HOOLA_GCONN" in v2 and "case 'google_reconnect': case 'google_connect':" in v2
    assert "go('connectors', 'google')" in v2 and "/auth/google/start?web=1&apps=1" not in v2
    dart = (ROOT / "lib/ui/shell/hoola_google.dart").read_text()
    for need in ("/api/google" in (ROOT / "lib/api.dart").read_text(), "hoolaGoogleConnect" in dart,
                 "Connect all" in dart, "Disconnect this account" in dart):
        assert need
    assert "hoolaOpenGoogle" in (ROOT / "lib/ui/shell/hoola_settings.dart").read_text()
    assert "case 'google_connect'" in (ROOT / "lib/ui/chat/hoola_cards_all.dart").read_text()
    assert "onGoogleHub" in (ROOT / "lib/main.dart").read_text() and "onGoogleHub" in (ROOT / "lib/state.dart").read_text()
    assert 'android:host="google"' in (ROOT / "tool/AndroidManifest.xml").read_text()
    assert 'data.host == "google"' in (ROOT / "tool/android/kotlin/MainActivity.kt").read_text()


def test_browser_walk_connectors_google(arena_server, monkeypatch):
    base, browser, key = arena_server
    _google_on(monkeypatch)
    from app import accounts
    from app.config import get_settings
    from app.db import CalendarAccount, OAuthConnection, session
    tenant = get_settings().tenant_id
    with session() as s:
        s.add(OAuthConnection(user_id=tenant, provider="google", account_email="asha@gmail.com", scopes=CORE_SCOPES,
                              refresh_token_enc=accounts.encrypt("rt")))
        s.add(CalendarAccount(tenant_id=tenant, address="office@biz.com", status="error", last_error="invalid_grant",
                              refresh_token_enc=accounts.encrypt("rt2")))
    for w, h in ((1280, 860), (390, 844)):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = ctx.new_page()
        errs: list[str] = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + "/console/?v=connectors&a=google&gconn=ok&got=gmail,calendar&miss=forms")
        p.wait_for_selector(".cx-modal [role=dialog]")
        dlg = p.text_content(".cx-modal [role=dialog]")
        assert "Google is connected" in dlg and "Forms: you left it unticked" in dlg
        p.click(".cx-modal [data-cx='close']")
        p.wait_for_selector("[data-g-app='gmail']")
        body = p.text_content(".cx-body")
        assert "asha@gmail.com" in body and "office@biz.com" in body and "Needs reconnecting" in body
        assert "Everyday apps" in body and "More Google apps" in body
        assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        p.click("article[data-g-app='calendar']")
        p.wait_for_selector(".cx-drawer .cx-panel")
        panel = p.text_content(".cx-drawer .cx-panel")
        assert "Accounts Hoola uses for Calendar" in panel and "office@biz.com" in panel
        p.click(".cx-drawer .cx-iconbtn[data-cd='close']")
        p.wait_for_selector(".cx-drawer", state="detached")
        asked = []
        p.route("https://accounts.google.com/**", lambda route: (asked.append(route.request.url), route.abort()))
        p.click("button[data-g-connect='core']:has-text('Connect everyday apps')") if p.locator(
            "button:has-text('Connect everyday apps')").count() else p.click("button[data-g-connect='core']")
        p.wait_for_selector(".cx-modal [data-cx='ok']")
        assert "Continue to Google" in p.text_content(".cx-modal [data-cx='ok']")
        assert not errs, errs          # (after leaving for Google the aborted page has no storage; not ours)
        p.click(".cx-modal [data-cx='ok']")
        p.wait_for_timeout(800)
        assert asked and "ggl_w" in asked[0] and "login_hint" in asked[0]
        ctx.close()
