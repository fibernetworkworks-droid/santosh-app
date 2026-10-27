"""v0.70 "Hoola mera Google Drive kyun nahi khol raha?"

Two real reasons found in the code: (1) Google refused to refresh her sign-in (expired / revoked; with the Cloud
project's OAuth app in 'Testing' mode this happens every 7 days) -> tools crashed with a raw RefreshError;
(2) she signed in without ticking the Drive box -> a vague "not connected". Now both say exactly what to do,
the refusal is remembered, a 'google_reconnect' card goes to the chat, and google_status explains it all."""
import asyncio
from pathlib import Path

import httpx
import pytest

T = "default"


@pytest.fixture
def g(env, monkeypatch):
    for k, v in {"SECRET_KEY": "s" * 32, "PUBLIC_BASE_URL": "https://hoola.example", "GOOGLE_OAUTH_CLIENT_ID": "cid",
                 "GOOGLE_OAUTH_CLIENT_SECRET": "csec", "GOOGLE_SERVICE_ACCOUNT_JSON": "", "GOOGLE_DRIVE_FOLDER_ID": ""}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import tools
    tools._reconnect_told.clear()
    seen = []
    from app.events import bus
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload=None, *a, **k: (seen.append((kind, payload)),
                                                                                    real(conv, kind, payload, *a, **k))[1])
    calls = {"n": 0}

    def drive(req: httpx.Request):
        calls["n"] += 1
        if req.headers.get("authorization") == "Bearer fresh":
            if req.url.path.endswith("/about"):
                return httpx.Response(200, json={"user": {"emailAddress": "meghana@gmail.com"}})
            return httpx.Response(200, json={"files": []})
        return httpx.Response(401, json={"error": {"message": "Invalid Credentials"}})
    from app.mailbox import accounts as ma
    ma.set_http(httpx.Client(transport=httpx.MockTransport(drive)))
    yield seen
    ma.set_http(None)


def _signin(scopes: str):
    from app import accounts
    from app.db import OAuthConnection, session
    with session() as s:
        s.add(OAuthConnection(user_id=T, provider="google", account_email="meghana@gmail.com",
                              access_token_enc=accounts.encrypt("old"), refresh_token_enc=accounts.encrypt("r"),
                              scopes=scopes))


def _run(name, **a):
    from app.agent.tools import Ctx, dispatch
    return asyncio.run(dispatch(name, a, Ctx(tenant_id=T, conversation_id="c1")))


def test_no_drive_box_ticked_says_exactly_that(g):
    from app.agent.tools import ToolError
    _signin("openid email https://www.googleapis.com/auth/gmail.modify")
    with pytest.raises(ToolError) as e:
        _run("drive_find", query="invoice")
    assert "tick" in str(e.value) and "Google Drive jodiye" in str(e.value)
    st = _run("google_status")
    assert st["signin"]["allowed"]["drive"] is False and st["signin"]["allowed"]["gmail"] is True
    assert not st["ok"] and "tick" in st["say"]


def test_refused_refresh_is_a_clear_reconnect_and_a_card(g, monkeypatch):
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    from app.agent.tools import ToolError
    from app.db import OAuthConnection, session
    _signin("openid email https://www.googleapis.com/auth/drive")

    def refused(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.", {})
    monkeypatch.setattr(Credentials, "refresh", refused)
    with pytest.raises(ToolError) as e:
        _run("drive_find", query="invoice")
    msg = str(e.value)
    assert "RefreshError" not in msg and "meghana@gmail.com" in msg and "Publish app" in msg and "don't retry" in msg
    with session() as s:
        assert "invalid_grant" in s.query(OAuthConnection).one().last_error
    cards = [p for k, p in g if k == "google_reconnect"]
    assert len(cards) == 1 and "Google Drive jodiye" in cards[0]["text"]
    with pytest.raises(ToolError):               # a second failure does not spam another card
        _run("drive_find", query="bill")
    assert len([1 for k, _ in g if k == "google_reconnect"]) == 1
    st = _run("google_status")
    assert not st["ok"] and st["signin"]["last_error"] and "Testing" in st["say"]
    from app.drive import accounts as da
    assert any(v["status"] == "error" for v in da.views(T))
    from app.push import render
    assert render("google_reconnect", {"text": "x"}, "Santosh")[0].startswith("Santosh")

    # Google accepts again (she re-linked / app published): the error clears by itself
    def ok(self, request):
        self.token = "fresh"
    monkeypatch.setattr(Credentials, "refresh", ok)
    st = _run("google_status")
    assert st["ok"] and st["drive"][0]["seen_as"] == "meghana@gmail.com" and st["say"] == "Google Drive theek chal raha hai."
    with session() as s:
        assert s.query(OAuthConnection).one().last_error is None


def test_status_api_and_tool_wiring(g):
    from fastapi.testclient import TestClient
    from app.agent import prompts
    assert "google_status" in Path(prompts.__file__).read_text()
    from app.main import app
    from app.voice import VOICE_TOOL_NAMES
    r = TestClient(app).get("/api/google/status?live=false").json()
    assert r["server_ready"] and r["signin"] is None and "Google Drive jodiye" in r["say"]
    assert "google_status" in VOICE_TOOL_NAMES
