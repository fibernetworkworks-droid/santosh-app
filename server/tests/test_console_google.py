"""Hoola Console Google sign-in for any real user: name + email only at login (no Google app review needed), Google apps
connected as a separate step, cancel goes back to the console, and HOOLA_SIGNUP=invite keeps new accounts closed."""
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

KEY = "owner-key-for-google-tests"
REAL_CLIENT = httpx.AsyncClient     # captured once: each fake Google below wraps the real client, never another fake
ALL = ("openid email profile https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar "
       "https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/spreadsheets")


@pytest.fixture
def con(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setenv("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.in")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csecret")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        yield c, monkeypatch
    get_settings.cache_clear()


def _q(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def _google(monkeypatch, email, scope):
    from app import accounts

    def handler(req: httpx.Request):
        if req.url.host == "oauth2.googleapis.com":
            body = {"access_token": "A1", "expires_in": 3600, "scope": scope}
            if "gmail" in scope:
                body["refresh_token"] = "R1"
            return httpx.Response(200, json=body)
        return httpx.Response(200, json={"email": email, "name": email.split("@")[0].title(), "sub": "g-" + email})
    monkeypatch.setattr(accounts.httpx, "AsyncClient", lambda **k: REAL_CLIENT(transport=httpx.MockTransport(handler)))


def _sign_in(c, monkeypatch, email, apps=False, scope="openid email profile"):
    _google(monkeypatch, email, scope)
    loc = c.get("/auth/google/start?web=1" + ("&apps=1" if apps else ""), follow_redirects=False).headers["location"]
    st = _q(loc)["state"]
    return c.get(f"/auth/google/callback?code=abc&state={st}", follow_redirects=False)


def _token(c, r):
    code = _q(r.headers["location"])["code"]
    return c.post("/api/console/exchange", json={"code": code}).json()["session_token"]


def test_console_sign_in_asks_only_name_and_email(con):
    c, mp = con
    from app import accounts
    q = _q(accounts.start_google(web=True))
    assert q["scope"].split() == ["openid", "email", "profile"]
    assert q["prompt"] == "select_account" and "access_type" not in q and q["state"].startswith("cw_")
    # the console's "Google apps jodiye" asks for the apps, with a refresh token
    q = _q(accounts.start_google(web=True, apps=True))
    assert "gmail.modify" in q["scope"] and "auth/drive" in q["scope"] and q["access_type"] == "offline"
    assert q["prompt"] == "consent" and q["state"].startswith("cw_g.")
    # the phone app's one consent is unchanged
    q = _q(accounts.start_google())
    assert "gmail.modify" in q["scope"] and q["access_type"] == "offline" and not q["state"].startswith("cw_")


def test_any_user_signs_in_then_connects_apps(con):
    c, mp = con
    r = _sign_in(c, mp, "asha@example.com")
    assert r.status_code in (302, 307) and r.headers["location"].startswith("/console/?code=")
    assert "google=apps" not in r.headers["location"]
    H = {"Authorization": f"Bearer {_token(c, r)}"}
    me = c.get("/api/console/me", headers=H).json()
    assert me["email"] == "asha@example.com" and me["google_apps"] == {"gmail": False, "calendar": False, "drive": False,
                                                                       "docs": False, "sheets": False}
    # Google apps jodiye: same person, apps added
    r = _sign_in(c, mp, "asha@example.com", apps=True, scope=ALL)
    assert r.headers["location"].startswith("/console/?code=") and r.headers["location"].endswith("&google=apps")
    H2 = {"Authorization": f"Bearer {_token(c, r)}"}
    me2 = c.get("/api/console/me", headers=H2).json()
    assert me2["tenant"] == me["tenant"] and all(me2["google_apps"].values())
    # signing in again with name + email only keeps her apps (Google sends back what she already granted)
    r = _sign_in(c, mp, "asha@example.com", scope=ALL)
    me3 = c.get("/api/console/me", headers={"Authorization": f"Bearer {_token(c, r)}"}).json()
    assert all(me3["google_apps"].values())


def test_cancel_on_google_goes_back_to_console(con):
    c, mp = con
    from app import accounts
    st = _q(accounts.start_google(web=True))["state"]
    r = c.get(f"/auth/google/callback?error=access_denied&state={st}", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"].startswith("/console/?error=")
    # the phone flow still shows its page
    st2 = _q(accounts.start_google())["state"]
    assert c.get(f"/auth/google/callback?error=access_denied&state={st2}").status_code == 400


def test_invite_mode_keeps_new_accounts_closed(con):
    c, mp = con
    mp.setenv("HOOLA_SIGNUP", "invite")
    mp.setenv("HOOLA_SIGNUP_ALLOW", "friend@gmail.com, @newtika.in")
    mp.setenv("OWNER_EMAILS", "meghana@example.com")
    from app.config import get_settings
    get_settings.cache_clear()
    r = _sign_in(c, mp, "stranger@gmail.com")
    assert r.headers["location"].startswith("/console/?error=") and "invite" in r.headers["location"]
    from app.db import User, session
    from sqlalchemy import select
    with session() as s:
        assert s.scalar(select(User).where(User.email == "stranger@gmail.com")) is None     # nothing was made
    for ok in ("friend@gmail.com", "sandesh@newtika.in", "meghana@example.com"):
        r = _sign_in(c, mp, ok)
        assert r.headers["location"].startswith("/console/?code="), ok
    # someone who already has a Hoola always gets back in
    mp.setenv("HOOLA_SIGNUP_ALLOW", "")
    get_settings.cache_clear()
    assert _sign_in(c, mp, "friend@gmail.com").headers["location"].startswith("/console/?code=")
    assert _sign_in(c, mp, "other@newtika.in").headers["location"].startswith("/console/?error=")
