"""v0.145 Supabase's official MCP server (mcp.supabase.com/mcp) as a Hoola connection: one-tap sign-in or a sbp_ token, her
project / read-only / feature groups as Supabase's documented URL parameters, and every write on her tap."""
import socket

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)

TOOLS = ["list_tables", "list_migrations", "execute_sql", "apply_migration", "get_advisors", "query_logs",
         "generate_typescript_types", "search_docs", "deploy_edge_function", "create_project", "get_project_url"]


FAKE_PAT = "sbp" + "_" + "x" * 40   # built at runtime: not a real token


class FakeSupa:
    calls: list = []

    def __init__(self, url, headers):
        self.url, self.headers = url, headers

    def list_tools(self):
        return [{"name": t, "description": t, "input_schema": {"type": "object"}} for t in TOOLS]

    def call_tool(self, name, args):
        FakeSupa.calls.append((name, args, self.url, dict(self.headers)))
        return {"is_error": False, "text": "ok", "data": {"tool": name}}


@pytest.fixture
def sb(bz, monkeypatch):  # noqa: F811
    from app.bazar import custom_mcp, service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.18.2.2", 443))])
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FakeSupa(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeSupa.calls = []
    return bz


def _probe(status):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json={})))


def _row(pid):
    from app.bazar.db import CustomMcp
    from app.db import session
    with session() as s:
        r = s.get(CustomMcp, pid)
        return r.url, r.caution, r.auth


def test_url_parameters_and_checks():
    from app.bazar import featured
    c = featured.get("supabase")
    assert c["url"] == "https://mcp.supabase.com/mcp" and c["auth"] == "oauth_dcr" and c["caution"]
    u = featured.supabase_url(c)
    assert u == "https://mcp.supabase.com/mcp?read_only=true&features=database,debugging,development,docs"
    u = featured.supabase_url(c, False, ["functions", "account", "nuke"], "abcdefghijklmnopqrst")
    assert "read_only" not in u and "project_ref=abcdefghijklmnopqrst" in u and "features=functions" in u
    assert "account" not in u and "nuke" not in u and "skip_elicitations" not in u
    with pytest.raises(ValueError):
        featured.supabase_url(c, True, None, "ABC; drop")
    st = featured.supabase_settings(featured.supabase_url(c, True, ["database"], "abcdefghijklmnopqrst"))
    assert st == {"project": "abcdefghijklmnopqrst", "readonly": True, "features": ["database"]}
    assert "Supabase" in featured.public(c)["how_to_connect"]


def test_one_tap_sign_in_then_settings_change_keeps_the_same_row(sb):
    svc = sb["svc"]
    out = svc.mcp_connect_featured("default", "supabase", probe_client=_probe(401))
    assert out["status"] == "needs_link" and out["settings"]["readonly"] and "Ek project" in out["note"]
    url, caution, auth = _row(out["pack_id"])
    assert caution is True and auth == "oauth" and "read_only=true" in url
    # pretend she signed in: the oauth connection is ready -> changing settings keeps the sign-in, same row, new address
    from app.bazar import service as bsvc
    real = bsvc.pack_status
    bsvc.pack_status = lambda s, user, pack: "ready" if pack.id == out["pack_id"] else real(s, user, pack)
    try:
        out2 = svc.mcp_connect_featured("default", "supabase", probe_client=_probe(401), project="abcdefghijklmnopqrst")
    finally:
        bsvc.pack_status = real
    assert out2["pack_id"] == out["pack_id"] and out2["status"] == "ready"
    url, _, _ = _row(out["pack_id"])
    assert "project_ref=abcdefghijklmnopqrst" in url and "read_only=true" in url     # read-only kept from before
    lst = {x["id"]: x for x in svc.mcp_featured("default")}
    assert lst["supabase"]["settings"]["project"] == "abcdefghijklmnopqrst"
    with pytest.raises(Exception):
        svc.mcp_connect_featured("default", "supabase", probe_client=_probe(401), project="Not-A-Ref")


def test_token_reads_writes_and_read_only_sql(sb):
    svc, conv = sb["svc"], sb["conv"]
    with pytest.raises(Exception, match="sbp_"):
        svc.mcp_connect_featured("default", "supabase", key="eyJhbGciOiJIUzI1NiJ9.service_role", probe_client=_probe(200))
    out = svc.mcp_connect_featured("default", "supabase", key=FAKE_PAT,
                                   probe_client=_probe(200), project="abcdefghijklmnopqrst", readonly=True)
    assert out["status"] == "ready" and out["settings"]["login"] == "token"
    pid = out["pack_id"]
    mine = [p for p in svc.find("default", "supabase")["packs"] if p["pack_id"] == pid][0]
    tiers = {t["tool"]: t["tier"] for t in mine["tools"]}
    for t in ("list_tables", "list_migrations", "get_advisors", "query_logs", "generate_typescript_types", "search_docs",
              "get_project_url", "execute_sql"):
        assert tiers[t] == 0, t                       # execute_sql is a read while read_only=true
    for t in ("apply_migration", "deploy_edge_function", "create_project"):
        assert tiers[t] >= 2, t
    r = svc.run("default", conv, pid, "execute_sql", {"query": "select count(*) from orders"})
    assert r["data"]["tool"] == "execute_sql"
    assert FakeSupa.calls[-1][3]["Authorization"].startswith("Bearer sbp_") and "read_only=true" in FakeSupa.calls[-1][2]
    w = svc.run("default", conv, pid, "apply_migration", {"name": "x", "query": "alter table t add c int"})
    assert w["needs_approval"] is True
    # read-only off: SQL needs her tap too; the saved token is kept when only settings change
    out2 = svc.mcp_connect_featured("default", "supabase", probe_client=_probe(200), readonly=False)
    assert out2["pack_id"] == pid and "Read-only band" in out2["note"]
    mine = [p for p in svc.find("default", "supabase")["packs"] if p["pack_id"] == pid][0]
    assert {t["tool"]: t["tier"] for t in mine["tools"]}["execute_sql"] >= 2
    from app import scrub
    assert FAKE_PAT not in scrub.text("token " + FAKE_PAT + " here")
