"""SIGN UP (owner: "THERE WILL BE 2 WAY TO SIGN UP TO HOOLA 1ST SELF REGISTRACTION VIA EMAIL AND OTHER IS GOOGLE" ->
"MAKE IT SAME AS OTHER DOES LIKE CLAUDE AND CHAT GPT"): one 'Log in or sign up' screen - Continue with Google (name +
email only) or an email and a 6-digit code (no password); one account per email whichever way she comes in; the phone
gets a one-time code from the Google page, never the session in a link; Google's error text is escaped."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

APP = Path(__file__).resolve().parents[1] / "app"
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def mail(env, monkeypatch):
    from app import emailauth as EA
    from app.config import get_settings
    from app.site import sitemail as SM
    monkeypatch.setattr(get_settings(), "site_mail_provider", "capture")
    SM.CAPTURED.clear()
    EA._RATE.clear()
    from app.main import app
    return TestClient(app), SM.CAPTURED


def _code(captured) -> str:
    return re.search(r"\b(\d{6})\b", captured[-1]["body"]).group(1)


def test_new_person_signs_up_with_an_email_code(mail):
    c, cap = mail
    r = c.post("/auth/email/start", json={"email": "Asha@Example.com"})
    assert r.status_code == 200 and "a***a@example.com" in r.json()["say"]
    assert cap and cap[-1]["to"] == "asha@example.com" and cap[-1]["subject"].startswith("Your Hoola code")
    code = _code(cap)
    v = c.post("/auth/email/verify", json={"email": "asha@example.com", "code": code}).json()
    assert v["new"] is True and v["needs_name"] is True and v["session_token"]
    me = TestClient(c.app, headers={"Authorization": f"Bearer {v['session_token']}"})
    assert me.post("/auth/email/name", json={"name": "  Asha  Rao "}).json()["name"] == "Asha Rao"
    from app.db import Profile, User, session
    with session() as s:
        u = s.get(User, v["user_id"])
        assert u.email == "asha@example.com" and u.name == "Asha Rao"
        assert s.get(Profile, v["user_id"]).name == "Asha Rao"
    # the same code never works twice
    again = c.post("/auth/email/verify", json={"email": "asha@example.com", "code": code})
    assert again.status_code == 401
    # logging in later = the same account, no name asked
    c.post("/auth/email/start", json={"email": "asha@example.com"})
    v2 = c.post("/auth/email/verify", json={"email": "asha@example.com", "code": _code(cap)}).json()
    assert v2["user_id"] == v["user_id"] and v2["new"] is False and v2["needs_name"] is False


def test_google_and_email_are_one_account(mail):
    c, cap = mail
    from app.db import User, session
    with session() as s:
        u = User(email="ravi@example.com", name="Ravi", google_sub="g-123")
        s.add(u)
        s.flush()
        uid = u.id
    c.post("/auth/email/start", json={"email": "ravi@example.com"})
    v = c.post("/auth/email/verify", json={"email": "RAVI@example.com", "code": _code(cap)}).json()
    assert v["user_id"] == uid and v["new"] is False and v["name"] == "Ravi"


def test_wrong_codes_and_limits(mail):
    c, cap = mail
    assert c.post("/auth/email/start", json={"email": "x@example.com"}).status_code == 200
    good = _code(cap)
    bad = "000000" if good != "000000" else "111111"
    for left in (4, 3, 2, 1):
        r = c.post("/auth/email/verify", json={"email": "x@example.com", "code": bad})
        assert r.status_code == 401 and f"{left} tries left" in r.json()["detail"]
    r = c.post("/auth/email/verify", json={"email": "x@example.com", "code": bad})
    assert "Too many wrong codes" in r.json()["detail"]
    assert c.post("/auth/email/verify", json={"email": "x@example.com", "code": good}).status_code == 401   # dead now
    # a new code replaces the old one; 3 codes per address per 10 minutes
    assert c.post("/auth/email/start", json={"email": "x@example.com"}).status_code == 200
    assert c.post("/auth/email/start", json={"email": "x@example.com"}).status_code == 200
    assert c.post("/auth/email/start", json={"email": "x@example.com"}).status_code == 429
    assert c.post("/auth/email/verify", json={"email": "x@example.com", "code": "12345"}).status_code == 400
    assert c.post("/auth/email/start", json={"email": "not-an-email"}).status_code == 400


def test_code_is_kept_only_as_a_hash_and_expires(mail):
    c, cap = mail
    c.post("/auth/email/start", json={"email": "k@example.com"})
    code = _code(cap)
    from datetime import timedelta

    from app import emailauth as EA
    from app.db import now, session
    with session() as s:
        row = s.query(EA.AuthEmailCode).filter_by(email="k@example.com").one()
        assert code not in row.code_hash and len(row.code_hash) == 64
        row.created_at = now() - timedelta(seconds=EA.CODE_TTL + 5)
    r = c.post("/auth/email/verify", json={"email": "k@example.com", "code": code})
    assert r.status_code == 401 and "expired" in r.json()["detail"]


def test_same_answer_for_known_and_unknown_addresses(mail):
    c, cap = mail
    from app.db import User, session
    with session() as s:
        s.add(User(email="known@example.com", name="K"))
    a = c.post("/auth/email/start", json={"email": "known@example.com"}).json()
    b = c.post("/auth/email/start", json={"email": "nobody@example.com"}).json()
    assert set(a) == set(b) and a["expires_in"] == b["expires_in"]


def test_invite_only_server_refuses_a_new_email(mail, monkeypatch):
    c, cap = mail
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "hoola_signup", "invite")
    monkeypatch.setattr(get_settings(), "hoola_signup_allow", "@team.in")
    c.post("/auth/email/start", json={"email": "out@example.com"})
    assert c.post("/auth/email/verify", json={"email": "out@example.com", "code": _code(cap)}).status_code == 403
    c.post("/auth/email/start", json={"email": "in@team.in"})
    assert c.post("/auth/email/verify", json={"email": "in@team.in", "code": _code(cap)}).json()["new"] is True


def test_no_mail_service_says_so(env):
    from app.main import app
    c = TestClient(app)
    r = c.post("/auth/email/start", json={"email": "a@example.com"})
    assert r.status_code == 503 and "Continue with Google" in r.json()["detail"]
    assert c.get("/healthz").json()["email_login"] is False
    assert c.get("/api/console/config").json()["email"] is False


def _google_on(monkeypatch):
    from app.config import get_settings
    st = get_settings()
    for k, v in (("google_oauth_client_id", "cid.apps.googleusercontent.com"), ("google_oauth_client_secret", "x"),
                 ("public_base_url", "https://hoola.test"), ("secret_key", "k" * 32)):
        monkeypatch.setattr(st, k, v)


def test_phone_google_asks_only_name_and_email(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    q = parse_qs(urlparse(accounts.start_google(phone=True)).query)
    assert q["scope"] == ["openid email profile"] and "access_type" not in q and q["state"][0].startswith("ap_")
    old = parse_qs(urlparse(accounts.start_google()).query)          # an old phone app keeps its one big consent
    assert "gmail.modify" in old["scope"][0] and not old["state"][0].startswith("ap_")


def test_phone_google_gets_a_one_time_code_not_the_session(env, monkeypatch):
    _google_on(monkeypatch)
    from app import accounts
    from app.main import app
    url = accounts.start_google(phone=True)
    state = parse_qs(urlparse(url).query)["state"][0]

    async def fake_finish(code, st):
        return {"session_token": "SESSION-SECRET", "user_id": "u", "email": "a@b.co", "name": "A"}
    monkeypatch.setattr(accounts, "finish_google", fake_finish)
    c = TestClient(app)
    html = c.get("/auth/google/callback", params={"code": "c", "state": state}).text
    assert "SESSION-SECRET" not in html and "auth?session=hc_" in html
    one = re.search(r"session=hc_([A-Za-z0-9_\-]+)", html).group(1)
    assert c.post("/api/console/exchange", json={"code": one}).json()["session_token"] == "SESSION-SECRET"
    assert c.post("/api/console/exchange", json={"code": one}).status_code == 401      # once only


def test_google_error_text_is_escaped(env):
    from app.main import app
    html = TestClient(app).get("/auth/google/callback", params={"error": "<b>x</b><script>alert(1)</script>"}).text
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html


def test_console_and_phone_screens():
    h = (APP / "static/console/v2.html").read_text()
    for t in ("Log in or sign up", "Continue with Google", "Continue with email", "Check your email",
              "What should Hoola call you?", 'autocomplete="one-time-code"', "More ways to sign in", "/privacy"):
        assert t in h, t
    js = (APP / "static/console/v2.js").read_text()
    assert "/auth/email/start" in js and "/auth/email/verify" in js and "/auth/email/name" in js
    d = (ROOT / "lib/ui/setup_screen.dart").read_text()
    assert "Continue with email" in d and "emailVerify" in d and "AutofillHints.oneTimeCode" in d
    a = (ROOT / "lib/api.dart").read_text()
    assert "{'phone': '1'}" in a and "exchangeCode" in a
    assert "startsWith('hc_')" in (ROOT / "lib/state.dart").read_text()
