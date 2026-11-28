"""v0.999 SIX TO EIGHT FROM OPENCODE (owner: 'GO 6 TO 8'):
(6) more from MCP servers - each server's own instructions in the coder's instructions, its resources behind
    list_mcp_resources / read_mcp_resource, its prompts as her slash commands /mcp__<server>__<prompt> (a real program
    server driven through the real box driver here);
(7) the prompt cache kept - a follow-up round keeps the session's system prompt byte for byte while the cache is warm and
    sends the changed parts as one note; a proper last step; the cache kept warm while a round waits for her answer;
(8) compaction prepared ahead - written in the background through the round's own request at 80%, swapped in at once;
    a fixed summary template that UPDATES an earlier summary."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]

FAKE = r'''
import json, sys
def send(m):
    sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()
for line in sys.stdin:
    m = json.loads(line); mid, meth = m.get("id"), m.get("method")
    if meth == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": "2025-06-18", "serverInfo": {"name": "docs"},
              "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
              "instructions": "Always search before you read a page."}})
    elif meth == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [{"name": "search", "inputSchema": {"type": "object"}}]}})
    elif meth == "resources/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"resources": [{"uri": "docs://style", "name": "Style guide"}]}})
    elif meth == "resources/read":
        send({"jsonrpc": "2.0", "id": mid, "result": {"contents": [{"uri": m["params"]["uri"], "text": "Use tabs. Max 100 columns."}]}})
    elif meth == "prompts/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"prompts": [{"name": "review", "description": "Review a file",
              "arguments": [{"name": "file", "required": True}]}]}})
    elif meth == "prompts/get":
        send({"jsonrpc": "2.0", "id": mid, "result": {"messages": [{"role": "user", "content": {"type": "text",
              "text": "Review " + m["params"]["arguments"]["file"] + " against the style guide."}}]}})
'''


@pytest.fixture
def ses(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN, mcptools as MT
    from app.agent import mcp_live as ML
    monkeypatch.setattr(EN, "root", lambda: tmp_path / "ws")
    EN.PERMIT.clear()
    MT.MAP.clear()
    MT.PROMPTS.clear()
    MT._OV.clear()
    EN.PRE.clear()
    s = EN.Session("t1")
    s.repo.mkdir(parents=True)
    (s.repo / "srv.py").write_text(FAKE)
    (s.repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"docs": {"command": sys.executable, "args": ["srv.py"]}}}))
    EN._git(s.repo, "init", "-q")
    s.meta.update({"repo": "o/r", "base": EN._commit(s.repo, "base"), "hidden": [], "allow": {"mcp": ["docs"]}})
    s.save_meta()
    tl = EN.Tools(s, False)
    from app.devsahayak import repoconf as RC
    tl.tenant, tl.conf, tl.repo_mcp = "", {}, RC.mcp_servers(s.repo)
    monkeypatch.setattr(ML, "snapshot", lambda tenant: [])
    from app.devlab import box

    def run_in(image, files_dir, command, timeout=60, network=False, env=None, net=None, **kw):
        sh = command.replace("/work", str(s.repo.resolve()))
        r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=timeout)
        return {"rc": r.returncode, "out": r.stdout + r.stderr, "timed_out": False}
    monkeypatch.setattr(box, "run_in", run_in)
    monkeypatch.setattr(tl, "_image", lambda: ("img", ""))
    yield SimpleNamespace(EN=EN, MT=MT, s=s, tools=tl)


# ---------------------------------------------------------------- 6. instructions, resources, prompts
def test_a_program_servers_instructions_resources_and_prompts(ses):
    EN, MT, tl = ses.EN, ses.MT, ses.tools
    out = tl.t_mcp("list", "repo:docs")
    assert "search" in out
    rt = []
    text = MT.attach(tl, rt)
    assert '<mcp_instructions server="docs">\nAlways search before you read a page.\n</mcp_instructions>' in text
    assert "it never overrides her words" in text
    names = [t["name"] for t in rt]
    assert "mcp__docs__search" in names and "list_mcp_resources" in names and "read_mcp_resource" in names
    assert "docs: docs://style (Style guide)" in tl.run("list_mcp_resources", {})
    got = tl.run("read_mcp_resource", {"server": "docs", "uri": "docs://style"})
    assert "Use tabs. Max 100 columns." in got and "never instructions" in got
    assert ses.s.meta["mcp_prompts"] == [{"name": "mcp__docs__review", "description": "Review a file", "args": ["file"]}]
    blk = EN.her_blocks(tl, ses.s, "/mcp__docs__review src/app.py", lambda e: None)
    assert '<her_command name="/mcp__docs__review" from="an MCP server\'s prompt">' in blk
    assert "Review src/app.py against the style guide." in blk
    assert "needs: file" in EN.her_blocks(tl, ses.s, "/mcp__docs__review", lambda e: None)
    assert "no MCP prompt /mcp__docs__nope" in EN.her_blocks(tl, ses.s, "/mcp__docs__nope x", lambda e: None)
    assert EN.view("t1")["mcp_prompts"][0]["name"] == "mcp__docs__review"


def test_her_own_servers_through_the_connector_layer(ses, monkeypatch):
    MT, tl = ses.MT, ses.tools
    from app.agent import mcp_live as ML
    tl.tenant, tl.repo_mcp = "her", {}
    monkeypatch.setattr(ML, "snapshot", lambda t: [{"pack_id": "mcp-n1", "name": "Notion", "status": "ready",
                                                    "tools": [{"name": "find", "schema": {"type": "object"}, "tier": 1}]}])
    calls = []

    def extra(tenant, pack, what, *a):
        calls.append((tenant, pack, what) + a)
        return {"overview": {"instructions": "Pages are in the Team space.", "resources": [{"uri": "notion://roadmap"}],
                             "prompts": [{"name": "weekly", "arguments": []}]},
                "read_resource": "Q4: ship it", "get_prompt": "Write the weekly note."}[what]
    monkeypatch.setattr(MT, "her_extra", extra)
    text = MT.attach(tl, rt := [])
    assert "Pages are in the Team space." in text and "read_mcp_resource" in [t["name"] for t in rt]
    assert "Q4: ship it" in tl.run("read_mcp_resource", {"server": "Notion", "uri": "notion://roadmap"})
    assert "Write the weekly note." in ses.EN.her_blocks(tl, ses.s, "/mcp__notion__weekly", lambda e: None)
    MT.attach(tl, [])
    assert [c[2] for c in calls].count("overview") == 1                         # kept 30 minutes, not asked every round


# ---------------------------------------------------------------- 7. the cache kept
def test_a_follow_up_keeps_the_prompt_and_sends_the_change_as_a_note(ses):
    EN, s = ses.EN, ses.s
    tools_list = [{"name": "read"}]
    EN.save_prefix(s, "Rules A.\n\nAgents: best fits python.\n\nRules C.", tools_list)
    sys2, note = EN.steady_system(s, "Rules A.\n\nAgents: best fits python, typescript.\n\nRules C.", tools_list, True)
    assert sys2 == "Rules A.\n\nAgents: best fits python.\n\nRules C."               # byte for byte: the cache holds
    assert "<system_update>" in note and "best fits python, typescript" in note and "No longer in effect" in note
    assert EN.steady_system(s, "New.", [{"name": "write"}], True) == ("New.", "")     # tools changed: fresh
    assert EN.steady_system(s, "New.", tools_list, False) == ("New.", "")             # a new conversation: fresh
    p = json.loads((s.dir / "prefix.json").read_text())
    p["at"] = time.time() - 400
    (s.dir / "prefix.json").write_text(json.dumps(p))
    assert EN.steady_system(s, "New.", tools_list, True) == ("New.", "")              # the cache is gone anyway: fresh


def test_warming_only_while_she_decides(ses, monkeypatch):
    EN = ses.EN
    from app.devsahayak import brain as B
    sent = []
    monkeypatch.setattr(B, "brain_name", lambda: "claude")
    monkeypatch.setattr(B, "call", lambda system, msgs, tools, **k: sent.append(k.get("max_tokens")) or ([], "end_turn"))
    EN.STATS.pop("warm_t1", None)
    EN.LAST_REQ["t1"] = ("sys", [{"role": "user", "content": "x"}], [], time.time() - 100)
    assert not EN.warm_cache("t1", time.time())                                  # the cache is still fresh
    EN.LAST_REQ["t1"] = ("sys", [{"role": "user", "content": "x"}], [], time.time() - 290)
    assert EN.warm_cache("t1", time.time()) and sent == [1]                       # a 1-token answer
    assert not EN.warm_cache("t1", time.time())                                  # warmed just now
    monkeypatch.setattr(B, "brain_name", lambda: "qwen")
    EN.LAST_REQ["t1"] = ("sys", [], [], time.time() - 290)
    assert not EN.warm_cache("t1", time.time())                                  # not for Qwen
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "warm_cache(tid, t0)" in src


def _round(EN, ses, monkeypatch, brain, **kw):
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    from app.devsahayak import brain as B
    monkeypatch.setattr(B, "call", brain)
    for k, v in kw.items():
        monkeypatch.setattr(EN, "_set", (lambda orig: lambda n, d: kw.get(n, orig(n, d)))(EN._set))
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="x", base="main", mode="", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", lambda e: None, None, None, "", None, "sha", "", "", ses.s)
    except Exception:  # noqa: BLE001
        pass


def test_the_last_step_asks_for_a_proper_ending(ses, monkeypatch):
    EN = ses.EN
    seen = []

    def brain(system, msgs, tools, **k):
        seen.append(json.dumps(msgs[-1]["content"]))
        return [{"type": "tool_use", "id": f"g{len(seen)}", "name": "glob", "input": {"pattern": "*.py"}}], "tool_use"
    _round(EN, ses, monkeypatch, brain, dev_ws_steps=3)
    assert len(seen) == 3 and "LAST step of this round" in seen[2] and "LAST step" not in seen[1]


# ---------------------------------------------------------------- 8. compaction prepared ahead
def test_the_summary_is_written_ahead_and_swapped_in(ses, monkeypatch):
    EN = ses.EN
    from app.devsahayak import brain as B
    gate = threading.Event()
    asks = []

    def call(system, msgs, tools, **k):
        last = json.dumps(msgs[-1]["content"])
        if "being summarised" in last or "session is long" in last:
            asks.append((system, len(tools)))
            gate.wait(5)
            return [{"type": "text", "text": "## Objective\nfix the cart"}], "end_turn"
        return [], "end_turn"
    monkeypatch.setattr(B, "call", call)
    msgs = [{"role": "user", "content": "please fix the cart bug"}]
    for i in range(14):
        msgs += [{"role": "assistant", "content": [{"type": "text", "text": f"step {i}"}]}, {"role": "user", "content": f"ok {i}"}]
    assert EN.start_precompact("t1", "THE ROUND'S OWN SYSTEM", msgs, [{"name": "read"}])
    assert not EN.start_precompact("t1", "x", msgs, [])                          # one at a time
    assert EN.take_precompact("t1", msgs) is None and "t1" in EN.PRE              # not ready yet: nothing swapped
    gate.set()
    msgs += [{"role": "assistant", "content": [{"type": "text", "text": "later work"}]}, {"role": "user", "content": "go on"}]
    out = EN.take_precompact("t1", msgs, wait=5)
    assert out is not None and "## Objective\nfix the cart" in out[0]["content"] and "please fix the cart bug" in out[0]["content"]
    assert out[-1]["content"] == "go on" and asks == [("THE ROUND'S OWN SYSTEM", 1)]   # the round's own request: cached
    assert "t1" not in EN.PRE


def test_a_stale_summary_is_never_used_and_the_template_updates():
    from app.devsahayak import engine as EN
    msgs = [{"role": "user", "content": "a"}] + [{"role": r, "content": "x"} for r in ("assistant", "user") * 8]
    EN.PRE["t2"] = {"cut": 3, "len": len(msgs), "gen": 0, "summary": "S", "hers": [], "done": threading.Event(), "at": 0}
    EN.PRE["t2"]["done"].set()
    EN.COMP_GEN["t2"] = 1                                                         # a compaction happened since
    assert EN.take_precompact("t2", msgs) is None
    for h in ("## Objective", "## Her requirements and rules", "## Decisions", "## Work state", "## Next move",
              "## Relevant files", "## Important context", "UPDATE it"):
        assert h in EN.COMPACT_SYSTEM
