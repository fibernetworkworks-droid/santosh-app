"""Product foundation: Google sign-in, encrypted token vault, sessions, /api/me."""
import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def product(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("API_KEY", "")   # product mode: sessions, not a shared key
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_token_encryption_roundtrip(product):
    from app import accounts
    enc = accounts.encrypt("ya29.secret-token")
    assert enc and enc != "ya29.secret-token"
    assert accounts.decrypt(enc) == "ya29.secret-token"
    assert accounts.decrypt(None) is None


def test_oauth_url_and_state(product):
    from app import accounts
    url = accounts.start_google()
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "gmail.modify" in url and "calendar" in url and "access_type=offline" in url
    assert "redirect_uri=https%3A%2F%2Fsantosh.example.in%2Fauth%2Fgoogle%2Fcallback" in url


def test_full_google_signin_and_session(product, monkeypatch):
    from app import accounts, main
    from app.db import OAuthConnection, User, session as dbsession
    from sqlalchemy import select

    # fake Google's token + userinfo endpoints
    def handler(req: httpx.Request):
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "ACCESS1", "refresh_token": "REFRESH1",
                                             "expires_in": 3600, "scope": " ".join(accounts.GOOGLE_SCOPES)})
        return httpx.Response(200, json={"email": "Meghana@Gmail.com", "name": "Meghana Ingle", "sub": "g-sub-123"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(accounts.httpx, "AsyncClient", lambda **k: real_client(transport=httpx.MockTransport(handler)))

    # make a real state, then complete the flow
    url = accounts.start_google()
    state = url.split("state=")[1]
    import asyncio
    res = asyncio.run(accounts.finish_google("auth-code", state))
    assert res["email"] == "meghana@gmail.com" and res["session_token"]
    uid = res["user_id"]
    with dbsession() as s:
        u = s.scalar(select(User).where(User.email == "meghana@gmail.com"))
        assert u and u.name == "Meghana Ingle" and u.google_sub == "g-sub-123"
        conn = s.scalar(select(OAuthConnection).where(OAuthConnection.user_id == uid))
        assert conn.refresh_token_enc and conn.refresh_token_enc != "REFRESH1"       # stored encrypted
        assert accounts.decrypt(conn.refresh_token_enc) == "REFRESH1"

    # the session token authenticates /api/me
    with TestClient(main.app) as c:
        h = c.get("/healthz").json()
        assert h["google_login"] is True
        me = c.get("/api/me", headers={"Authorization": f"Bearer {res['session_token']}"}).json()
        assert me["signed_in"] and me["email"] == "meghana@gmail.com"
        assert me["connections"][0]["provider"] == "google"
        # disconnect
        assert c.delete("/api/connections/google", headers={"Authorization": f"Bearer {res['session_token']}"}).json()["disconnected"]
        me2 = c.get("/api/me", headers={"Authorization": f"Bearer {res['session_token']}"}).json()
        assert me2["connections"] == []


def test_stale_state_rejected(product):
    from app import accounts
    import asyncio
    with pytest.raises(accounts.AuthError):
        asyncio.run(accounts.finish_google("code", "never-issued-state"))


def test_session_token_grants_api_access(product, monkeypatch):
    from app import accounts, main
    uid = "usr_test"
    from app.db import User, session as dbsession
    with dbsession() as s:
        s.add(User(id=uid, email="x@gmail.com", name="X"))
    token = accounts.issue_session(uid)
    with TestClient(main.app) as c:
        # a protected endpoint accepts the session token
        assert c.get("/api/reminders", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        # a random token is rejected
        assert c.get("/api/me", headers={"Authorization": "Bearer nope"}).json()["signed_in"] is False


def test_gdrive_uses_signed_in_user_creds(product, monkeypatch):
    """When a user has a Google login, drive uses their OAuth creds, not the service account."""
    from app import gdrive, google_auth
    from app.db import OAuthConnection, session as dbsession
    from app import accounts
    with dbsession() as s:
        s.add(OAuthConnection(user_id="usr_abc", provider="google",
                              refresh_token_enc=accounts.encrypt("R"), access_token_enc=accounts.encrypt("A"),
                              scopes=" ".join(accounts.GOOGLE_SCOPES)))
    assert gdrive.configured("usr_abc") is True
    assert google_auth.has_google("usr_abc") is True
    assert google_auth.has_google("nobody") is False
