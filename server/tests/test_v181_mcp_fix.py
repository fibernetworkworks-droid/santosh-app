"""v0.181: guard two MCP fixes so they cannot silently regress.

1. access_token() must not let two concurrent callers burn a rotating refresh token (that logged users out).
2. The 'pehle poochho' (ask first) toggle must produce a NeedsApproval card for read-only tools, not just tier 2.
"""
import datetime as dt
import json
import threading
import time
from unittest.mock import patch


def _mk_conn(tenant: str, provider: str, expires_in: int = 30) -> str:
    """Create a User (via ensure_user) + a Connection row; return the real user_id."""
    from app.bazar.db import Connection, session_factory
    from app.bazar.security import vault
    from app.bazar.service import ensure_user, session as core_session

    with core_session() as s:
        user = ensure_user(s, tenant)
        user_id = user.id
        s.commit()

    bundle = {
        "access_token": "old", "refresh_token": "r0",
        "token_endpoint": "https://auth.example/token", "client_id": "cid",
        "client_secret": "", "resource": "https://srv.example/mcp",
    }
    with session_factory() as s:
        s.add(Connection(
            user_id=user_id, provider=provider,
            token_enc=vault().seal(json.dumps(bundle)),
            status="active",
            expires_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(seconds=expires_in),
        ))
        s.commit()
    return user_id


def test_concurrent_refresh_does_not_log_out(env):
    from app.bazar import mcp_auth
    from app.bazar.db import Connection, session_factory

    provider = "custom:mcp-race"
    user_id = _mk_conn("u-race", provider)

    calls: list[str] = []
    lock = threading.Lock()

    def fake_refresh(endpoint, data, client):
        with lock:
            calls.append(data["refresh_token"])
            n = len(calls)
        if data["refresh_token"] == "r0" and n == 1:
            time.sleep(0.15)
            return {"access_token": "new", "refresh_token": "r1", "expires_in": 3600}
        raise mcp_auth.LinkError(f"invalid_grant on token {data['refresh_token']!r} (double refresh)")

    results: list[str] = []
    errors: list[BaseException] = []

    def go():
        try:
            with session_factory() as s:
                conn = s.query(Connection).filter_by(user_id=user_id, provider=provider, status="active").one()
                results.append(mcp_auth.access_token(s, conn))
        except BaseException as e:
            errors.append(e)
            results.append(f"ERR:{type(e).__name__}")

    with patch.object(mcp_auth, "_token_request", side_effect=fake_refresh):
        ts = [threading.Thread(target=go) for _ in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=15)

    assert len(results) == 2, f"only {len(results)} of 2 threads finished: {results!r}"
    assert not errors, f"errors: {[repr(e) for e in errors]}"
    assert sorted(results) == ["new", "new"], f"results: {results!r}"
    assert len(calls) == 1, f"refresh called {len(calls)} times: {calls!r}"
    with session_factory() as s:
        row = s.query(Connection).filter_by(user_id=user_id, provider=provider, status="active").first()
        assert row is not None, "active connection was lost"
        assert row.status == "active", row.status


def test_ask_first_toggle_produces_approval(env):
    from app.bazar.connectors.base import NeedsApproval
    from app.bazar.connectors.mcp_remote import McpExecutor
    from app.bazar.packs.registry import Pack
    from app.bazar.service import _ctx, ensure_user, session as core_session

    pack_id = "mcp-ask-test"
    result = None
    with core_session() as s:
        user = ensure_user(s, "u-ask")
        ctx = _ctx(s, user, None)
        user_id = user.id

        pack = Pack(
            id=pack_id, name="AskServer",
            category="My MCP servers", sub_category="MCP server",
            pack_type="Custom MCP", layer="L1", phase="MVP", priority="P1",
            description="", notes="", master_list_row=0, executor="mcp",
            config={"custom": True, "provider": "custom:mcp-ask-test",
                    "endpoint": "https://example.com/mcp", "owner": user_id,
                    "auth": "none", "key_header": "Authorization", "caution": False},
            tools=[], keywords=[],
        )

        with patch("app.mcp_prefs.enabled", return_value=True), \
             patch("app.mcp_prefs.prefs", return_value={"list_things": (True, True)}), \
             patch.object(Pack, "tier_of", return_value=1):
            ex = McpExecutor()
            result = ex.call(pack, "list_things", {"q": "x"}, ctx)

    assert isinstance(result, NeedsApproval), f"expected NeedsApproval, got {type(result).__name__}: {result!r}"
    assert result.action["name"] == "list_things"
    assert result.action["pack_id"] == pack_id
