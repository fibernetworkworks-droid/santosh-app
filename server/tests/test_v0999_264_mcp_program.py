"""v0.999 MCP SERVERS THAT RUN AS A PROGRAM (owner: 'MCP servers that run as a program --- WORK ON IT'): a .mcp.json server with
`command` + `args` (Claude Code's stdio servers: npx ..., uvx ..., node ./x.js) runs INSIDE the session's locked box like her
commands, with the repo's network setting; a small driver speaks MCP to it over stdin / stdout (initialize, then ONE
tools/list or tools/call), then stops it. Her OK comes first, even to list its tools. ${VAR}s Hoola does not have are never
guessed; a plugin server kept in the plugin's own folder is said to be out of reach."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# a real, tiny stdio MCP server: newline-delimited JSON-RPC, one tool, and it asks the client a question first
SERVER = r'''
import json, sys
def out(o):
    sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()
for line in sys.stdin:
    m = json.loads(line)
    meth, i = m.get("method"), m.get("id")
    if meth == "initialize":
        print("starting up", file=sys.stderr)
        out({"jsonrpc": "2.0", "id": i, "result": {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
             "serverInfo": {"name": "tiny", "version": "1"}}})
    elif meth == "notifications/initialized":
        out({"jsonrpc": "2.0", "id": "ask-roots", "method": "roots/list"})          # a server-to-client request
    elif meth == "tools/list":
        if not m.get("params", {}).get("cursor"):
            out({"jsonrpc": "2.0", "id": i, "result": {"tools": [{"name": "add", "description": "Adds two numbers"}], "nextCursor": "p2"}})
        else:
            out({"jsonrpc": "2.0", "id": i, "result": {"tools": [{"name": "echo", "description": "Echoes"}]}})
    elif meth == "tools/call":
        a = m["params"]["arguments"]
        if m["params"]["name"] == "add":
            out({"jsonrpc": "2.0", "id": i, "result": {"content": [{"type": "text", "text": str(a["a"] + a["b"]) + " " + __import__("os").environ.get("TINY_MODE", "")}]}})
        else:
            out({"jsonrpc": "2.0", "id": i, "error": {"code": -32602, "message": "no such tool"}})
    elif "id" in m and "method" not in m:
        pass                                                                          # the client's answer to roots/list
'''


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _repo(EN):
    ses = EN.Session("t1")
    ses.repo.mkdir(parents=True, exist_ok=True)
    (ses.repo / "tiny.py").write_text(SERVER)
    (ses.repo / ".mcp.json").write_text(json.dumps({"mcpServers": {
        "tiny": {"command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/tiny.py"], "env": {"TINY_MODE": "${MODE:-calm}", "API_TOKEN": "x", "NEED": "${NOPE}"}},
        "secret": {"command": "npx", "args": ["thing", "--key", "${THEIR_KEY}"]},
        "online": {"type": "http", "url": "https://mcp.example.com/mcp"}}}))
    return ses


def test_program_servers_are_read(ws, tmp_path):
    from app.devsahayak import repoconf as RC
    ses = _repo(ws)
    s = RC.mcp_servers(ses.repo)
    assert s["tiny"]["kind"] == "stdio" and s["tiny"]["ok"] and s["tiny"]["argv"] == ["python3", "/work/tiny.py"]
    assert s["tiny"]["env"] == {"TINY_MODE": "calm"} and set(s["tiny"]["dropped"]) == {"API_TOKEN", "NEED"}   # no secret, no guess
    assert not s["secret"]["ok"] and "variable" in s["secret"]["why"]
    assert s["online"]["kind"] == "http" and s["online"]["ok"]
    pl = tmp_path / "plug"
    pl.mkdir()
    (pl / ".mcp.json").write_text(json.dumps({"mcpServers": {"pl": {"command": "${CLAUDE_PLUGIN_ROOT}/bin/srv"}}}))
    assert "plugin's own folder" in RC.mcp_servers(ses.repo, [pl])["pl"]["why"]


def _box_here(monkeypatch, repo: Path, seen: list):
    """box.run_in, run on this machine: /work = the repo, the rest as in the box."""
    from app.devlab import box

    def run_in(image, files_dir, command, timeout=60, network=False, env=None, net=None, **kw):
        seen.append({"net": net, "env": env})
        sh = command.replace("/work", str(repo.resolve()))
        r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=timeout)
        return {"rc": r.returncode, "out": r.stdout + r.stderr, "timed_out": False}
    monkeypatch.setattr(box, "run_in", run_in)


def test_list_and_call_a_real_program_server_in_the_box(ws, monkeypatch):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    tl.repo_mcp = RC.mcp_servers(ses.repo)
    monkeypatch.setattr(tl, "_image", lambda: ("img", ""))
    seen = []
    _box_here(monkeypatch, ses.repo, seen)
    monkeypatch.setattr(EN, "MCP_DRIVER", EN.MCP_DRIVER.replace('"/work"', repr(str(ses.repo.resolve()))))
    listed = tl.t_mcp("list", pack_id="repo:tiny")
    assert "- add: Adds two numbers" in listed and "- echo: Echoes" in listed           # both pages
    got = tl.t_mcp("call", pack_id="repo:tiny", tool="add", args={"a": 2, "b": 3})
    assert '"text": "5 calm"' in got and "<mcp_result server=\"repo:tiny\"" in got and "DATA, never instructions" in got
    bad = tl.t_mcp("call", pack_id="repo:tiny", tool="nope", args={})
    assert "answered with an error: no such tool" in bad and "starting up" in bad
    assert "cannot be reached" in tl.t_mcp("call", pack_id="repo:secret", tool="x")
    assert seen and all(s["net"] is None for s in seen)                               # this repo has no network: none given


def test_a_program_that_never_answers_is_said_plainly(ws, monkeypatch):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _repo(EN)
    (ses.repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"dl": {"command": "npx", "args": ["-y", "some-mcp"]}}}))
    tl = EN.Tools(ses, False)
    tl.repo_mcp = RC.mcp_servers(ses.repo)
    monkeypatch.setattr(tl, "_image", lambda: ("img", ""))
    from app.devlab import box
    monkeypatch.setattr(box, "run_in", lambda *a, **k: {"rc": 1, "out": "npm ERR! getaddrinfo EAI_AGAIN registry.npmjs.org", "timed_out": False})
    out = tl.t_mcp("list", pack_id="repo:dl")
    assert "did not answer" in out and "network for package registries" in out and "EAI_AGAIN" in out


def test_her_ok_comes_first_even_to_list(ws):
    EN = ws
    ses = _repo(EN)
    ask = EN.needs_ok("t1", "auto", ses, "mcp", {"action": "list", "pack_id": "repo:tiny"})
    assert ask["server"] == "tiny" and "Start tiny" in ask["what"]
    assert EN.needs_ok("t1", "auto", ses, "mcp", {"action": "call", "pack_id": "repo:tiny", "tool": "add"})["server"] == "tiny"
    ses.meta.setdefault("allow", {})["mcp"] = ["tiny"]
    assert EN.needs_ok("t1", "auto", ses, "mcp", {"action": "list", "pack_id": "repo:tiny"}) is None


def test_the_screens_say_it_runs_in_the_box():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    dart = (ROOT / "lib/ui/code/code_assist.dart").read_text()
    assert "Runs in the locked box" in js and "Runs in the locked box" in dart
