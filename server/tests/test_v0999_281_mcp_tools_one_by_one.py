"""v0.999 MCP TOOLS ONE BY ONE (owner: 'GO NEXT - MCP TOOLS LISTED ONE BY ONE'), Claude Code's way: every tool of her MCP
servers and of the repo's servers she allowed is a tool of its own, mcp__<server>__<tool>, with its real input schema;
too many = held back behind mcp_tool_search (keywords or select:); the call still goes through the same doors (her
connector layer with its phone cards, the repo's box / allowed address); permission rules and hook matchers see the
real name."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _snap(n_tools=2, tier=1):
    tools = [{"name": "search_pages", "description": "Search her Notion pages", "tier": 1,
              "schema": {"$schema": "x", "type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
             {"name": "create_page", "description": "Create a page", "tier": 2, "schema": {"type": "object", "properties": {}}}]
    tools += [{"name": f"extra_tool_{i}", "description": f"Extra thing number {i}", "tier": tier, "schema": {}} for i in range(n_tools - 2)]
    return [{"pack_id": "mcp-ab12", "name": "Notion", "status": "ready", "tools": tools},
            {"pack_id": "mcp-off", "name": "Jira", "status": "needs_link", "tools": [{"name": "x", "schema": {}}]}]


@pytest.fixture
def ses(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN, mcptools as MT
    from app.agent import mcp_live as ML
    monkeypatch.setattr(EN, "root", lambda: tmp_path / "ws")
    EN.PERMIT.clear()
    MT.MAP.clear()
    s = EN.Session("t1")
    s.repo.mkdir(parents=True)
    (s.repo / "a.py").write_text("x = 1\n")
    EN._git(s.repo, "init", "-q")
    s.meta.update({"repo": "o/r", "base": EN._commit(s.repo, "base"), "hidden": []})
    s.save_meta()
    tl = EN.Tools(s, False)
    tl.tenant, tl.repo_mcp, tl.conf = "her", {}, {}
    snap = {"v": _snap()}
    monkeypatch.setattr(ML, "snapshot", lambda tenant: snap["v"])
    yield SimpleNamespace(EN=EN, MT=MT, s=s, tools=tl, snap=snap)


def test_names_like_claude_code():
    from app.devsahayak import mcptools as MT
    taken = set()
    a = MT.direct_name("Notion", "search_pages", taken)
    assert a == "mcp__notion__search_pages"
    long = MT.direct_name("My Very Long Server Name!!", "a-tool-with-a-really-really-long-name-indeed", set())
    assert len(long) <= 64 and long.startswith("mcp__my_very_long_server_name__")
    assert MT.direct_name("Notion", "search_pages", {a}) != a                   # never two tools with one name


def test_a_small_set_comes_in_one_by_one(ses):
    MT, tl = ses.MT, ses.tools
    rt = [{"name": "read"}]
    text = MT.attach(tl, rt)
    names = [t["name"] for t in rt]
    assert names == ["read", "mcp__notion__search_pages", "mcp__notion__create_page"]   # Jira is not ready: left out
    sp = rt[1]
    assert sp["input_schema"] == {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    assert sp["description"].startswith("[her MCP server Notion] Search her Notion pages")
    assert "confirm card on her phone" in rt[2]["description"] and "confirm card" not in sp["description"]
    assert "is a tool of its own, named mcp__<server>__<tool>" in text and "mcp_tool_search" not in names


def test_many_tools_wait_behind_the_search(ses):
    MT, tl = ses.MT, ses.tools
    ses.snap["v"] = _snap(n_tools=90)
    rt = [{"name": "read"}]
    text = MT.attach(tl, rt)
    assert [t["name"] for t in rt] == ["read", "mcp_tool_search"] and "held back - there are 90" in text
    assert "mcp__notion__extra_tool_7" in text
    out = MT.search(tl, "notion search pages")
    assert "mcp__notion__search_pages" in out and "mcp__notion__search_pages" in [t["name"] for t in rt]
    out = MT.search(tl, "select:mcp__notion__extra_tool_3,mcp__nope__x")
    assert "mcp__notion__extra_tool_3" in [t["name"] for t in rt] and "Unknown names: mcp__nope__x" in out
    assert "No MCP tool matches" in MT.search(tl, "zzzz")


def test_a_call_by_its_own_name_goes_through_her_connector_layer(ses, monkeypatch):
    MT, tl = ses.MT, ses.tools
    from app.agent import bazar_tools as BT
    got = []

    async def fake(ctx, pack, tool, args):
        got.append((ctx.tenant_id, pack, tool, args))
        return {"pages": ["Roadmap"]}
    monkeypatch.setattr(BT, "bazar_run", fake)
    MT.attach(tl, [])
    out = tl.run("mcp__notion__search_pages", {"query": "roadmap"})
    assert got == [("her", "mcp-ab12", "search_pages", {"query": "roadmap"})]
    assert '<mcp_result server="mcp-ab12" tool="search_pages">' in out and "Roadmap" in out
    assert "Unknown tool mcp__gone__x" in tl.run("mcp__gone__x", {})
    ev = ses.EN.event(tl, "mcp__notion__search_pages", {"query": "roadmap"}, out)[0]
    assert ev == {"k": "mcp", "action": "call", "server": "Notion", "tool": "search_pages", "direct": "mcp__notion__search_pages"}


def test_repo_servers_only_after_her_ok(ses):
    MT, tl, s = ses.MT, ses.tools, ses.s
    tl.repo_mcp = {"github": {"ok": True, "kind": "http", "url": "https://x"}}
    MT.attach(tl, rt := [])
    assert not any(t["name"].startswith("mcp__github") for t in rt)              # not allowed: nothing listed
    s.meta.setdefault("allow", {})["mcp"] = ["github"]
    MT.remember(tl, "github", [{"name": "create_issue", "description": "Open an issue",
                                "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}}}])
    assert "mcp__github__create_issue" in [t["name"] for t in rt]               # loaded into this round at once
    MT.attach(tl, rt2 := [])
    assert "mcp__github__create_issue" in [t["name"] for t in rt2]              # and next round, from the kept list
    assert MT.target("t1", "mcp__github__create_issue") == ("repo:github", "create_issue")
    s.meta["mcp_lists"]["github"]["at"] = 0                                     # a day old: listed again when asked
    MT.attach(tl, rt3 := [])
    assert not any(t["name"].startswith("mcp__github") for t in rt3)


def test_rules_hooks_permission_and_the_reviewer_see_the_real_name(ses):
    from app.devsahayak import repoconf as RC, judge as JG
    for rule, ok in (("mcp__notion__search_pages", True), ("mcp__notion", True), ("mcp__notion__*", True),
                     ("mcp__jira", False), ("mcp__notion__create_page", False), ("Bash", False)):
        assert RC.rule_matches(rule, "mcp__notion__search_pages", {"query": "x"}) is ok, rule
    conf = {"hooks": {"PreToolUse": [{"matcher": "mcp__notion__.*", "commands": ["echo hi"]}]}}
    assert RC.hooks_for(conf, "PreToolUse", "mcp__notion__search_pages") and not RC.hooks_for(conf, "PreToolUse", "mcp__jira__x")
    assert JG.needs_review("mcp__notion__search_pages", {})
    ses.tools.repo_mcp = {"github": {"ok": True}}
    ses.MT.MAP["t1"] = {"mcp__github__create_issue": ("repo:github", "create_issue")}
    ask = ses.EN.needs_ok("t1", "auto", ses.s, "mcp__github__create_issue", {"title": "x"})
    assert ask and ask["server"] == "github" and "create_issue" in ask["what"]


def test_the_loop_runs_a_direct_tool_and_a_deny_rule_stops_it(ses, monkeypatch):
    EN, MT = ses.EN, ses.MT
    from app.devsahayak import brain as B
    from app.agent import bazar_tools as BT
    ran = []

    async def fake(ctx, pack, tool, args):
        ran.append(tool)
        return "ok"
    monkeypatch.setattr(BT, "bazar_run", fake)
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    monkeypatch.setattr(MT, "_repo", lambda tools: [])
    for deny, expect in (([], ["search_pages"]), (["mcp__notion__search_pages"], [])):
        ran.clear()
        (ses.s.repo / ".claude").mkdir(exist_ok=True)
        (ses.s.repo / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"deny": deny}}))
        it = iter([[{"type": "tool_use", "id": "m", "name": "mcp__notion__search_pages", "input": {"query": "q"}}]])
        sent_tools = []
        monkeypatch.setattr(B, "call", lambda system, msgs, tools, **k: (sent_tools.append([t["name"] for t in tools]) or
                            next(it, [{"type": "tool_use", "id": "d", "name": "done", "input": {"explain": "ok"}}]), "tool_use"))
        t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="x", base="main", mode="", tenant_id="her", conv="")
        try:
            EN._round(None, t, "tok", "", False, "", lambda e: None, None, None, "", None, "sha", "", "", ses.s)
        except Exception:  # noqa: BLE001
            pass
        assert "mcp__notion__search_pages" in sent_tools[0] and ran == expect


def test_screens():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "case 'toolsearch'" in js and "Loaded MCP tools" in js
    d = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "case 'toolsearch':" in d and "Loaded MCP tools" in d
