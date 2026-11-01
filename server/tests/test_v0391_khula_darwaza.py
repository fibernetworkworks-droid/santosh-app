"""v0.391 KHULA DARWAZA (owner: "GO A"): the front-door safety pass.
A1 an empty API_KEY lets a request with no login act as the owner -> a loud startup warning + `python -m app.authcheck`
   + vps-ops auth_check (the live server answered 401 to a no-login /api/me when this shipped: the door is locked).
A2 a key or login token in the ADDRESS (?key=) lands in nginx logs and browser history -> only the Authorization header
   (and the console's WebSocket subprotocol) count now; no Hoola client ever sent ?key=.
A3 the 589 KB main.py.orig leftover is gone."""
import logging
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _client(monkeypatch, env, **extra):
    for k, v in extra.items():
        monkeypatch.setattr(env["settings"], k, v)
    from app.main import app
    return TestClient(app)


def test_the_key_in_the_address_no_longer_opens_anything(env, monkeypatch):
    with _client(monkeypatch, env, api_key="secret") as c:
        assert c.get("/api/me", headers={"Authorization": "Bearer secret"}).status_code == 200
        assert c.get("/api/me?key=secret").status_code == 401                 # the right key, but in the address
        assert c.get("/api/conversations?key=secret").status_code == 401
        assert c.get("/api/me").status_code == 401


def test_a_login_token_in_the_address_is_ignored_too(env, monkeypatch):
    from app import main
    from starlette.requests import Request
    req = Request({"type": "http", "headers": [], "query_string": b"key=some-session-token", "method": "GET", "path": "/"})
    assert main._bearer(req) == ""
    req = Request({"type": "http", "headers": [(b"authorization", b"Bearer tok123")], "query_string": b"", "method": "GET",
                   "path": "/"})
    assert main._bearer(req) == "tok123"


def test_the_voice_socket_takes_no_key_from_the_address(env, monkeypatch):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with _client(monkeypatch, env, api_key="secret") as c:
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect("/api/voice/ws?conv=x&key=secret") as ws:
                ws.receive_text()
        assert e.value.code == 4401


def test_an_open_door_is_said_loudly(env, monkeypatch, caplog):
    from app import authcheck
    monkeypatch.setattr(env["settings"], "api_key", "")
    with caplog.at_level(logging.WARNING, logger="hoola.authcheck"):
        assert authcheck.warn_if_open() is True
    assert "API_KEY is EMPTY" in caplog.text and "OWNER" in caplog.text
    assert "API_KEY in this server's settings: EMPTY" in authcheck.lines()[0]
    monkeypatch.setattr(env["settings"], "api_key", "secret")
    caplog.clear()
    assert authcheck.warn_if_open() is False and not caplog.text
    assert authcheck.lines() == ["API_KEY in this server's settings: set"]


def test_the_live_probe_reads_the_answer(monkeypatch):
    import httpx

    from app import authcheck
    for code, word in ((401, "LOCKED"), (200, "OPEN")):
        monkeypatch.setattr(httpx, "get", lambda url, timeout, _c=code: httpx.Response(_c, request=httpx.Request("GET", url)))
        assert word in authcheck.probe("http://127.0.0.1:8077")[1]


def test_vps_job_and_cleanup():
    yml = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "- auth_check" in yml and "/api/me with no login" in yml and "never the value" in yml
    assert not (ROOT / "server/app/main.py.orig").exists()
    src = (ROOT / "server/app/main.py").read_text()
    assert 'query_params.get("key"' not in src                               # nowhere in the main API any more
