"""v0.999.180 GOOGLE SIGN UP (owner: "NOW LETS WORK ON GOOGLE SIGN UP IN HOOLA SIGN UP PAGE FIRST"): Continue with Google
as a real sign-up, like Claude and ChatGPT - a person new to Hoola gets the welcome step with her Google name filled in
(console + phone), an email she already typed is picked for her on Google's page, a Google account whose email Google
has not checked never opens an account, and the name she chose in Hoola is never replaced by Google's."""
from __future__ import annotations

import asyncio
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


def _fake_google(monkeypatch, info: dict):
    """Google's token + profile answers, without the network."""
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "expires_in": 3600, "scope": "openid email profile"})
        return httpx.Response(200, json=info)
    real = httpx.AsyncClient

    def client(*a, **k):
        k["transport"] = httpx.MockTransport(handler)
        return real(*a, **k)
    monkeypatch.setattr(httpx, "AsyncClient", client)


def _state(accounts, **kw) -> str:
    return parse_qs(urlparse(accounts.start_google(**kw)).query)["state"][0]


def test_typed_email_is_picked_on_googles_page(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    q = parse_qs(urlparse(accounts.start_google(web=True, hint=" Asha@Gmail.com ")).query)
    assert q["login_hint"] == ["asha@gmail.com"] and q["scope"] == ["openid email profile"]
    assert "login_hint" not in parse_qs(urlparse(accounts.start_google(web=True, hint="not an email")).query)
    assert "login_hint" not in parse_qs(urlparse(accounts.start_google(web=True, apps=True, hint="a@b.co")).query)
    r = TestClient(__import__("app.main", fromlist=["app"]).app).get(
        "/auth/google/start", params={"web": 1, "hint": "ravi@example.com"}, follow_redirects=False)
    assert r.status_code in (302, 307) and "login_hint=ravi%40example.com" in r.headers["location"]


def test_unchecked_google_email_never_opens_an_account(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    from app.db import User, session
    _fake_google(monkeypatch, {"email": "victim@example.com", "email_verified": False, "name": "X", "sub": "g1"})
    with pytest.raises(accounts.AuthError, match="not checked"):
        asyncio.run(accounts.finish_google("c", _state(accounts, web=True)))
    with session() as s:
        assert s.query(User).filter(User.email == "victim@example.com").count() == 0


def test_new_google_person_is_new_with_her_name_and_profile(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    from app.db import Profile, session
    _fake_google(monkeypatch, {"email": "Meera@Example.com", "email_verified": True, "name": "  Meera   Shah ",
                               "sub": "g-meera"})
    r = asyncio.run(accounts.finish_google("c", _state(accounts, web=True)))
    assert r["new"] is True and r["name"] == "Meera Shah" and r["email"] == "meera@example.com"
    with session() as s:
        assert s.get(Profile, accounts.tenant_of_user(r["user_id"])).name == "Meera Shah"
    again = asyncio.run(accounts.finish_google("c", _state(accounts, web=True)))
    assert again["new"] is False and again["user_id"] == r["user_id"]


def test_her_hoola_name_is_kept(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="ravi@example.com", name="Ravi Bhai")
        s.add(u)
        s.flush()
        uid = u.id
    _fake_google(monkeypatch, {"email": "ravi@example.com", "email_verified": True, "name": "Ravindra Kumar",
                               "sub": "g-ravi"})
    r = asyncio.run(accounts.finish_google("c", _state(accounts, web=True)))
    assert r["user_id"] == uid and r["new"] is False and r["name"] == "Ravi Bhai"
    with session() as s:
        u = s.get(User, uid)
        assert u.name == "Ravi Bhai" and u.google_sub == "g-ravi"


def test_welcome_rides_the_one_time_code_only(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    from app.console import service as console
    from app.main import app

    async def fake_finish(code, st):
        return {"session_token": "SESSION-SECRET", "user_id": "u", "email": "asha@example.com", "name": "Asha Rao",
                "new": True}
    monkeypatch.setattr(accounts, "finish_google", fake_finish)
    c = TestClient(app)
    r = c.get("/auth/google/callback", params={"code": "c", "state": _state(accounts, web=True)},
              follow_redirects=False)
    loc = r.headers["location"]
    assert loc.startswith("/console/?code=") and "Asha" not in loc and "SESSION" not in loc
    code = parse_qs(urlparse(loc).query)["code"][0]
    from app.db import session
    with session() as s:
        row = s.get(console.ConsoleCode, console._sha(code))
        assert json.loads(row.info) == {"new": True, "name": "Asha Rao"} and "asha@" not in row.info
    got = c.post("/api/console/exchange", json={"code": code}).json()
    assert got == {"session_token": "SESSION-SECRET", "new": True, "name": "Asha Rao"}
    plain = console.issue_code("T2")                      # an old-style code (no info) still works
    assert console.exchange_full(plain) == {"session_token": "T2", "new": False, "name": ""}


def test_console_and_phone_welcome_code():
    js = (APP / "static/console/v2.js").read_text()
    assert "function gwelcome(name)" in js and "r.new && !gApps" in js and "'&hint=' + encodeURIComponent(h)" in js
    st = (ROOT / "lib/state.dart").read_text()
    assert "googleWelcome" in st and "takeGoogleWelcome" in st
    assert "takeGoogleWelcome()" in (ROOT / "lib/ui/setup_screen.dart").read_text()
    assert "widget.app.googleWelcome != null" in (ROOT / "lib/main.dart").read_text()
    assert "Future<Map<String, dynamic>> exchangeCode" in (ROOT / "lib/api.dart").read_text()


def test_browser_walk_new_google_person(arena_server, monkeypatch):
    base, browser, _key = arena_server
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "secret_key", "k" * 32)   # the code is sealed with the server's key
    from app import accounts
    from app.console import service as console
    from app.db import Profile, User, session
    with session() as s:
        u = User(email="asha.g@example.com", name="Asha Rao", google_sub="g-asha")
        s.add(u)
        s.flush()
        uid = u.id
    for w, h in ((1280, 820), (390, 844)):
        code = console.issue_code(accounts.issue_session(uid), {"new": True, "name": "Asha Rao"})
        p = browser.new_page(viewport={"width": w, "height": h})
        errs: list[str] = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + "/console/?code=" + code)
        p.wait_for_selector("#lstep3:not([hidden])")
        assert p.input_value("#lname") == "Asha Rao"
        assert "Good to meet you, Asha." in p.text_content("#lgreet")
        assert "code=" not in p.url
        p.fill("#lname", "Asha")
        p.click("#nbtn")
        p.wait_for_selector("#login", state="hidden")
        assert not errs, errs
        p.close()
    with session() as s:
        assert s.get(User, uid).name == "Asha" and s.get(Profile, uid).name == "Asha"
