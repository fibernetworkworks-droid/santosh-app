"""MCP directory + MCP servers the user adds: search, safe addresses, sign-in/key, read vs confirm, isolation."""
import json
import socket

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)


class FakeRemote:
    calls: list = []

    def __init__(self, url, headers):
        self.url, self.headers = url, headers

    def list_tools(self):
        return [{"name": "get_holdings", "description": "Portfolio", "input_schema": {"type": "object"}},
                {"name": "createIssue", "description": "New issue", "input_schema": {"type": "object"}}]

    def call_tool(self, name, args):
        FakeRemote.calls.append((self.url, dict(self.headers), name, args))
        return {"is_error": False, "text": "ok", "data": {"tool": name, "args": args}}


@pytest.fixture
def mcp(bz, monkeypatch):  # noqa: F811
    from app.bazar import custom_mcp, service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    real = socket.getaddrinfo

    def fake_dns(host, *a, **k):
        if host == "evil.example.net":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))]
        if host[0].isdigit():
            return real(host, *a, **k)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]   # any public name
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo", fake_dns)
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FakeRemote(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeRemote.calls = []
    return bz


def _probe(status, headers=None):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, headers=headers or {}, json={})))


def test_directory_loaded_and_searchable():
    from app.bazar import directory
    st = directory.stats()
    assert st["total"] == 50762 and st["sources"]["npm"] > 20000 and st["sources"]["PyPI"] > 20000
    hits = directory.search("tally", limit=5)
    assert any("tally" in h["ref"].lower() or "tally" in h["does"].lower() for h in hits)
    z = directory.search("zerodha kite", limit=10)
    assert any("kite" in h["ref"].lower() for h in z)
    assert directory.get("kukapay/jupiter-mcp")["c"] is True   # crypto swaps flagged
    x = directory.get("https://pypi.org/project/jira-ticket-mcp/")
    assert x and x["r"] == "jira-ticket-mcp"
    j = [h for h in directory.search("jira ticket", limit=30) if h["ref"] == "jira-ticket-mcp"][0]
    assert j["install"].startswith("uvx jira-ticket-mcp") and j["connect"] == "local"
    t0 = __import__("time").time()
    directory.search("postgres database read only", limit=10)
    assert __import__("time").time() - t0 < 1.5


@pytest.mark.parametrize("url", ["http://api.example.com/mcp", "https://localhost/mcp", "https://127.0.0.1/mcp",
                                 "https://169.254.169.254/latest", "https://evil.example.net/mcp", "ftp://x.example.com"])
def test_private_or_insecure_addresses_refused(mcp, url):
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):
        mcp["svc"].mcp_add("default", url, probe_client=_probe(200))


def test_add_open_server_read_runs_write_needs_tap(mcp):
    svc, conv = mcp["svc"], mcp["conv"]
    out = svc.mcp_add("default", "https://tools.example.com/mcp", ref="aranjan/kite-mcp", probe_client=_probe(200))
    assert out["name"] == "kite-mcp"
    assert out["status"] == "ready" and out["name"] == "kite-mcp"
    pid = out["pack_id"]
    found = svc.find("default", "kite")
    mine = [p for p in found["packs"] if p["pack_id"] == pid][0]
    tiers = {t["tool"]: t["tier"] for t in mine["tools"]}
    assert tiers == {"get_holdings": 0, "createIssue": 2}
    r = svc.run("default", conv, pid, "get_holdings", {})
    assert r["data"]["tool"] == "get_holdings"
    w = svc.run("default", conv, pid, "createIssue", {"title": "Bug"})
    assert w["needs_approval"] is True and len(FakeRemote.calls) == 1   # nothing sent yet
    done = svc.decide("default", w["approval_id"], "approve")
    assert done["outcome"]["status"] == "done"
    assert FakeRemote.calls[-1][2:] == ("createIssue", {"title": "Bug"})
    assert svc.activity("default")["payments"][0]["what"] == "kite-mcp"


def test_needs_sign_in_then_key(mcp):
    svc = mcp["svc"]
    out = svc.mcp_add("default", "https://secure.example.com/mcp", name="Notion", probe_client=_probe(401))
    assert out["status"] == "needs_link"
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="Sign in"):
        svc.run("default", mcp["conv"], out["pack_id"], "get_holdings", {})
    # the user pastes an API key in the app instead
    st = svc.mcp_set_key("default", out["pack_id"], "sk-live-123", "X-API-Key")
    assert st["status"] == "ready"
    svc.run("default", mcp["conv"], out["pack_id"], "get_holdings", {})
    assert FakeRemote.calls[-1][1] == {"X-API-Key": "sk-live-123"}
    listed = svc.mcp_list("default")[0]
    assert listed["auth"] == "key" and "sk-live" not in json.dumps(listed)


def test_other_user_cannot_use_my_server(mcp):
    svc = mcp["svc"]
    out = svc.mcp_add("default", "https://tools.example.com/mcp", probe_client=_probe(200))
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="Unknown pack"):
        svc.run("someone-else", mcp["conv"], out["pack_id"], "get_holdings", {})
    assert svc.mcp_remove("someone-else", out["pack_id"]) is False
    assert svc.mcp_remove("default", out["pack_id"]) is True
    with pytest.raises(ToolError):
        svc.run("default", mcp["conv"], out["pack_id"], "get_holdings", {})


def test_dead_address_not_saved(mcp):
    svc = mcp["svc"]
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError, match="No MCP endpoint"):
        svc.mcp_add("default", "https://tools.example.com/", probe_client=_probe(404))
    assert svc.mcp_list("default") == []


def test_find_offers_directory_when_no_pack(mcp):
    res = mcp["svc"].find("default", "jira issues")
    assert res.get("mcp_directory") and "directory_hint" in res


def test_unofficial_whatsapp_automation_not_connectable(mcp):
    from app.bazar import directory
    from app.bazar.connectors.base import ToolError
    hits = [h for h in directory.search("whatsapp", limit=30) if h["connect"] == "not_allowed"]
    assert hits
    with pytest.raises(ToolError, match="WhatsApp"):
        mcp["svc"].mcp_add("default", "https://tools.example.com/mcp", ref=hits[0]["ref"], probe_client=_probe(200))


def test_featured_connectors(mcp):
    from app.bazar import featured
    from app.bazar.connectors.base import ToolError
    svc = mcp["svc"]
    items = featured.items()
    assert len(items) >= 50 and items[0]["india"]           # Indian apps first
    names = {c["name"] for c in items}
    assert {"Notion", "Razorpay", "Zoho CRM", "Stripe", "Linear", "Zapier"} <= names
    for c in items:
        assert c["auth"] in {"oauth_dcr", "oauth_partner", "api_key", "per_user_url", "none"}
        if c["auth"] in ("oauth_dcr", "api_key"):
            assert c["url"].startswith("https://")
    # one tap: OAuth server answers 401 -> sign-in link
    out = svc.mcp_connect_featured("default", "notion", probe_client=_probe(401))
    assert out["status"] == "needs_link" and out["name"] == "Notion"
    lst = {c["id"]: c for c in svc.mcp_featured("default")}
    assert lst["notion"]["status"] == "needs_link" and lst["notion"]["pack_id"] == out["pack_id"]
    # Razorpay key_id:key_secret becomes a Basic header
    monkey = __import__("app.bazar.custom_mcp", fromlist=["x"])
    assert monkey is not None
    r = svc.mcp_connect_featured("default", "razorpay", key="rzp_live_abc:sec123", probe_client=_probe(200))
    assert r["status"] == "ready"
    from app.db import session
    with session() as s:
        from app.bazar.db import CustomMcp
        row = s.get(CustomMcp, r["pack_id"])
        h = monkey.headers_for(s, monkey.to_pack(row), "default")
    assert h["Authorization"].startswith("Basic ") and "rzp_live" not in h["Authorization"]
    with pytest.raises(ToolError, match="built into Santosh"):
        svc.mcp_connect_featured("default", "gmail")
    with pytest.raises(ToolError, match="approved apps"):
        svc.mcp_connect_featured("default", "slack")
    with pytest.raises(ToolError, match="personal"):
        svc.mcp_connect_featured("default", "zapier")
    assert featured.search("notion pages")[0]["id"] == "notion"
    assert svc.find("default", "linear issues")["featured_connectors"][0]["id"] == "linear"
