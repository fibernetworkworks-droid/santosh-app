"""v0.143 GitHub's official MCP server (api.githubcopilot.com/mcp/) as a Hoola connection: her fine-grained token (or the
one she gave Developer Sahayak), GitHub's own headers (lockdown always, toolsets, read-only), and every write on her tap."""
import socket

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)

TOOLS = ["get_file_contents", "search_code", "issue_read", "pull_request_read", "actions_list", "list_commits",
         "create_issue", "issue_write", "merge_pull_request", "push_files", "add_issue_comment", "actions_run_trigger"]


class FakeGitHub:
    calls: list = []
    seen: list = []

    def __init__(self, url, headers):
        self.url, self.headers = url, headers
        FakeGitHub.seen.append(dict(headers))

    def list_tools(self):
        return [{"name": t, "description": t, "input_schema": {"type": "object"}} for t in TOOLS]

    def call_tool(self, name, args):
        FakeGitHub.calls.append((name, args, dict(self.headers)))
        return {"is_error": False, "text": "ok", "data": {"tool": name}}


@pytest.fixture
def gh(bz, monkeypatch):  # noqa: F811
    from app.bazar import custom_mcp, service
    from app.bazar.agent.toolbox import default_executors
    from app.bazar.connectors.mcp_remote import McpExecutor
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("140.82.112.21", 443))])
    ex = default_executors()
    ex["mcp"] = McpExecutor(remote_factory=lambda url, h: FakeGitHub(url, h))
    McpExecutor._cache.clear()
    service.set_executors(ex)
    FakeGitHub.calls, FakeGitHub.seen = [], []
    return bz


def _ok():
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))


def _headers(pid):
    from app.bazar import custom_mcp
    from app.bazar.db import CustomMcp
    from app.db import session
    with session() as s:
        row = s.get(CustomMcp, pid)
        return custom_mcp.headers_for(s, custom_mcp.to_pack(row), "default"), row.caution


def test_github_connects_with_her_token_and_github_headers(gh):
    from app.bazar import featured
    svc = gh["svc"]
    c = featured.get("github")
    assert c["auth"] == "api_key" and c["url"] == "https://api.githubcopilot.com/mcp/" and c["caution"]
    pub = featured.public(c)
    assert "fine-grained" in pub["how_to_connect"] and "repos" in pub["options"]["toolsets"]
    out = svc.mcp_connect_featured("default", "github", key="github_pat_11ABCDEFG0123456789_secret", probe_client=_ok())
    assert out["status"] == "ready" and out["settings"]["lockdown"] and not out["settings"]["readonly"]
    assert out["settings"]["toolsets"] == ["context", "repos", "issues", "pull_requests", "actions", "users"]
    h, caution = _headers(out["pack_id"])
    assert caution is True
    assert h["Authorization"] == "Bearer github_pat_11ABCDEFG0123456789_secret"
    assert h["X-MCP-Lockdown"] == "true" and h["X-MCP-Toolsets"].startswith("context,repos") and "X-MCP-Readonly" not in h
    # changing settings = connect again (same row, new headers); unknown toolsets dropped, context always kept
    out2 = svc.mcp_connect_featured("default", "github", key="github_pat_11ABCDEFG0123456789_secret", probe_client=_ok(),
                                    readonly=True, toolsets=["code_security", "dependabot", "hack_the_planet"])
    assert out2["pack_id"] == out["pack_id"]
    h, _ = _headers(out["pack_id"])
    assert h["X-MCP-Readonly"] == "true" and h["X-MCP-Toolsets"] == "context,code_security,dependabot"
    lst = {x["id"]: x for x in svc.mcp_featured("default")}
    assert lst["github"]["settings"] == {"toolsets": ["context", "code_security", "dependabot"], "readonly": True,
                                         "lockdown": True}
    assert "key" not in str(lst["github"]["settings"]).lower()
    # a classic token works but gets the fine-grained advice
    out3 = svc.mcp_connect_featured("default", "github", key="ghp_0123456789abcdefghijABCDEFGHIJ012345", probe_client=_ok())
    assert "Fine-grained" in out3["note"]


def test_reads_run_writes_wait_for_her_tap(gh):
    svc, conv = gh["svc"], gh["conv"]
    out = svc.mcp_connect_featured("default", "github", key="github_pat_11XYZ_secret", probe_client=_ok())
    pid = out["pack_id"]
    mine = [p for p in svc.find("default", "github")["packs"] if p["pack_id"] == pid][0]
    tiers = {t["tool"]: t["tier"] for t in mine["tools"]}
    for t in ("get_file_contents", "search_code", "issue_read", "pull_request_read", "actions_list", "list_commits"):
        assert tiers[t] == 0, t
    for t in ("create_issue", "issue_write", "merge_pull_request", "push_files", "add_issue_comment", "actions_run_trigger"):
        assert tiers[t] >= 2, t
    r = svc.run("default", conv, pid, "issue_read", {"owner": "o", "repo": "r", "issue_number": 3, "method": "get"})
    assert r["data"]["tool"] == "issue_read"
    w = svc.run("default", conv, pid, "merge_pull_request", {"owner": "o", "repo": "r", "pullNumber": 7})
    assert w["needs_approval"] is True and [c[0] for c in FakeGitHub.calls] == ["issue_read"]
    # she can't switch the tap off for a write on a code server
    from app import mcp_prefs
    assert mcp_prefs.locked("merge_pull_request", True) and mcp_prefs.locked("create_issue", True)
    assert not mcp_prefs.locked("issue_read", True)
    done = svc.decide("default", w["approval_id"], "approve")
    assert done["outcome"]["status"] == "done" and FakeGitHub.calls[-1][0] == "merge_pull_request"
    assert FakeGitHub.calls[-1][2]["X-MCP-Lockdown"] == "true"


def test_one_tap_with_the_developer_sahayak_token_and_no_token_in_chat(gh):
    import asyncio
    svc = gh["svc"]
    from app.agent.tools import Ctx, ToolError, dispatch
    ctx = Ctx("default", gh["conv"])
    # no token anywhere: the tool says "add it in the app", never asks for it in chat
    with pytest.raises(ToolError, match="never in chat"):
        asyncio.run(dispatch("bazar_mcp", {"action": "connect", "featured": "github"}, ctx))
    assert {x["id"]: x for x in svc.mcp_featured("default")}["github"]["can_reuse"] is False
    from app.bazar.security import vault
    from app.db import session
    from app.devsahayak.models import DevSettings
    with session() as s:
        st = s.get(DevSettings, "default") or DevSettings(tenant_id="default")
        st.token_sealed = vault().seal("github_pat_11DEV_token")
        s.merge(st)
    assert {x["id"]: x for x in svc.mcp_featured("default")}["github"]["can_reuse"] is True
    from app.bazar import custom_mcp
    real_probe = custom_mcp.probe
    custom_mcp.probe = lambda url, headers=None, client=None: real_probe(url, headers, _ok())
    try:
        out = asyncio.run(dispatch("bazar_mcp", {"action": "connect", "featured": "github", "readonly": True}, ctx))
    finally:
        custom_mcp.probe = real_probe
    assert out["status"] == "ready" and out["settings"]["token"] == "developer_sahayak" and out["settings"]["readonly"]
    assert "github_pat" not in str(out)
    h, _ = _headers(out["pack_id"])
    assert h["Authorization"] == "Bearer github_pat_11DEV_token" and h["X-MCP-Readonly"] == "true"


def test_changing_settings_keeps_the_saved_token(gh):
    svc = gh["svc"]
    out = svc.mcp_connect_featured("default", "github", key="github_pat_11KEEP_secret", probe_client=_ok())
    out2 = svc.mcp_connect_featured("default", "github", probe_client=_ok(), readonly=True, toolsets=["issues"])
    assert out2["pack_id"] == out["pack_id"] and out2["settings"]["readonly"]
    h, _ = _headers(out["pack_id"])
    assert h["Authorization"] == "Bearer github_pat_11KEEP_secret" and h["X-MCP-Toolsets"] == "context,issues"
