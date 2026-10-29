"""v0.162 MCP connections that really work: spec sign-in (challenge, scopes, client auth), refused tokens refreshed
once, plain errors instead of 'unhandled errors in a TaskGroup', featured list fixes (PayPal address, partner -> one tap,
money servers always ask)."""
import base64
import http.server
import json
import threading

import httpx
import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_custom_mcp import _probe, mcp  # noqa: F401  (fixture)


def _server(status, body=b"", headers=None):
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(status)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/mcp"


def test_remote_errors_are_plain():
    from app.bazar.connectors.mcp_remote import McpHttpRemote, RemoteAuthError, RemoteError
    srv, url = _server(401, headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    try:
        with pytest.raises(RemoteAuthError) as e:
            McpHttpRemote(url, "old-token").list_tools()
        assert e.value.status == 401 and "invalid_token" in e.value.www
    finally:
        srv.shutdown()
    srv, url = _server(500, b"boom")
    try:
        with pytest.raises(RemoteError) as e:
            McpHttpRemote(url, "t").list_tools()
        assert "TaskGroup" not in str(e.value) and "500" in str(e.value)
    finally:
        srv.shutdown()


def _oauth_handler(seen, methods, scope_in_challenge=""):
    def handler(req: httpx.Request):
        p = req.url.path
        if req.method == "POST" and p == "/mcp":
            www = 'Bearer resource_metadata="https://mcp.app.test/.well-known/custom-prm"'
            if scope_in_challenge:
                www += f', scope="{scope_in_challenge}"'
            return httpx.Response(401, headers={"WWW-Authenticate": www})
        if p == "/.well-known/custom-prm":   # only advertised through the challenge header
            return httpx.Response(200, json={"authorization_servers": ["https://auth.app.test"],
                                             "scopes_supported": ["read", "write", "offline_access"]})
        if p == "/.well-known/oauth-authorization-server":
            return httpx.Response(200, json={"issuer": "https://auth.app.test",
                                             "authorization_endpoint": "https://auth.app.test/authorize",
                                             "token_endpoint": "https://auth.app.test/token",
                                             "registration_endpoint": "https://auth.app.test/register",
                                             "token_endpoint_auth_methods_supported": methods})
        if p == "/register":
            seen["reg"] = json.loads(req.content)
            return httpx.Response(201, json={"client_id": "cid", "client_secret": "sec",
                                             "token_endpoint_auth_method": seen["reg"]["token_endpoint_auth_method"]})
        if p == "/token":
            seen.setdefault("tok", []).append((dict(httpx.QueryParams(req.content.decode())),
                                               req.headers.get("authorization", "")))
            return httpx.Response(200, json={"access_token": "AT", "refresh_token": "RT", "expires_in": 3600})
        return httpx.Response(404)
    return handler


def test_sign_in_follows_the_challenge_scopes_and_client_auth(bz):  # noqa: F811
    from app.bazar import mcp_auth
    from app.bazar.db import Connection
    from app.db import session
    seen = {}
    client = httpx.Client(transport=httpx.MockTransport(_oauth_handler(seen, ["client_secret_basic"])))
    with session() as s:
        bz["svc"].ensure_user(s, "default")
        url = mcp_auth.start(s, "default", "custom:x", "https://mcp.app.test/mcp", client=client)
    q = dict(httpx.URL(url).params)
    assert q["scope"] == "read write offline_access"          # from the resource metadata (no mcp:tools needed)
    assert seen["reg"]["token_endpoint_auth_method"] == "client_secret_basic"   # 'none' not offered by this server
    assert seen["reg"]["client_name"] == "Hoola"
    with session() as s:
        mcp_auth.finish(s, q["state"], "CODE", client=client)
    body, auth = seen["tok"][0]
    assert "client_secret" not in body and auth == "Basic " + base64.b64encode(b"cid:sec").decode()
    with session() as s:
        conn = s.scalars(select(Connection).where(Connection.provider == "custom:x")).one()
        assert mcp_auth.access_token(s, conn, client=client, force=True) == "AT"   # forced refresh after a refusal
    body, auth = seen["tok"][1]
    assert body["grant_type"] == "refresh_token" and body["resource"] == "https://mcp.app.test/mcp" and auth.startswith("Basic ")


def test_challenge_scope_wins_and_public_client_when_allowed(bz):  # noqa: F811
    from app.bazar import mcp_auth
    from app.db import session
    seen = {}
    client = httpx.Client(transport=httpx.MockTransport(_oauth_handler(seen, ["none", "client_secret_post"], "read")))
    with session() as s:
        bz["svc"].ensure_user(s, "default")
        url = mcp_auth.start(s, "default", "custom:y", "https://mcp.app.test/mcp", client=client)
    assert dict(httpx.URL(url).params)["scope"] == "read"
    assert seen["reg"]["token_endpoint_auth_method"] == "none"


class FlakyRemote:
    """First token is refused (expired early); the refreshed one works."""
    calls: list = []

    def __init__(self, url, headers):
        self.headers = headers

    def _check(self):
        from app.bazar.connectors.mcp_remote import RemoteAuthError
        FlakyRemote.calls.append(dict(self.headers))
        if self.headers.get("Authorization") != "Bearer FRESH":
            raise RemoteAuthError(401, 'Bearer error="invalid_token"')

    def list_tools(self):
        self._check()
        return [{"name": "get_things", "description": "", "input_schema": {"type": "object"}}]

    def call_tool(self, name, args):
        self._check()
        return {"is_error": False, "text": "ok", "data": {"ok": True}}


def _linked(mcp, monkeypatch, refresh_ok):  # noqa: F811
    from app.bazar import mcp_auth, service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    from app.bazar.db import Connection
    from app.bazar.security import vault
    from app.db import session
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FlakyRemote(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FlakyRemote.calls = []
    out = mcp["svc"].mcp_add("default", "https://secure.example.com/mcp", name="Things", probe_client=_probe(401))
    with session() as s:
        mcp_auth.save(s, "default", "custom:" + out["pack_id"], {"access_token": "OLD", "refresh_token": "RT"},
                      {"token_endpoint": "https://secure.example.com/token", "client_id": "c"})

    def fake_refresh(endpoint, data, client, method=""):
        if not refresh_ok:
            raise mcp_auth.LinkError("Token exchange failed (400): invalid_grant")
        return {"access_token": "FRESH", "refresh_token": "RT2", "expires_in": 3600}
    monkeypatch.setattr(mcp_auth, "_token_request", fake_refresh)
    return out["pack_id"], Connection, vault


def test_refused_token_is_refreshed_once_and_the_call_goes_through(mcp, monkeypatch):  # noqa: F811
    pid, _, _ = _linked(mcp, monkeypatch, refresh_ok=True)
    r = mcp["svc"].run("default", mcp["conv"], pid, "get_things", {})
    assert r["data"] == {"ok": True}
    assert [c["Authorization"] for c in FlakyRemote.calls][-1] == "Bearer FRESH"


def test_dead_sign_in_says_link_again_and_is_marked_expired(mcp, monkeypatch):  # noqa: F811
    from app.bazar.connectors.base import ToolError
    from app.db import session
    pid, Connection, _ = _linked(mcp, monkeypatch, refresh_ok=False)
    with pytest.raises(ToolError) as e:
        mcp["svc"].run("default", mcp["conv"], pid, "get_things", {})
    assert "phir 'Link'" in str(e.value) and "TaskGroup" not in str(e.value)
    with session() as s:
        st = s.scalars(select(Connection.status).where(Connection.provider == "custom:" + pid)).all()
    assert "active" not in st


def test_featured_fixes():
    from app.bazar import featured
    assert featured.get("paypal")["url"] == "https://mcp.paypal.com/mcp"
    for fid in ("ramp", "square", "figma", "gamma", "vercel"):
        assert featured.get(fid)["auth"] == "oauth_dcr"
    for fid in ("razorpay", "paypal", "stripe", "mercury", "ramp", "square"):
        assert featured.get(fid)["caution"] is True


def test_old_payment_rows_ask_before_every_write(mcp):  # noqa: F811
    from app.bazar import custom_mcp
    from app.bazar.db import CustomMcp
    row = CustomMcp(id="mcp-old", user_id="default", url="https://mcp.stripe.com", name="Stripe",
                    directory_ref="featured:stripe", auth="oauth", caution=False, status="active")
    pack = custom_mcp.to_pack(row)
    assert pack.config["caution"] is True
