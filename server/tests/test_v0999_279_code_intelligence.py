"""v0.999 CODE INTELLIGENCE (owner: 'GO NEXT - CODE INTELLIGENCE (LSP)'), Claude Code's LSP tool: one `lsp` tool asks a
language server in the session's locked box - goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol,
goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls, diagnostics - and after the coder edits a file the
server's problems arrive at its next step. Servers: the box's own (pyright, typescript-language-server, gopls ...), the
repo's .lsp.json and her plugins' lspServers (Claude Code's format); one the repo / a plugin names is a program, so she is
asked before it starts the first time. These tests drive the REAL pyright where this machine has it."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HAS_PYRIGHT = bool(shutil.which("pyright-langserver"))


@pytest.fixture
def ses(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN, lsp as LS
    monkeypatch.setattr(EN, "root", lambda: tmp_path / "ws")
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    LS._PENDING.clear()
    s = EN.Session("t1")
    s.repo.mkdir(parents=True)
    (s.repo / "cart.py").write_text('def total(items: list[int]) -> int:\n    """Sum of the cart."""\n    return sum(items)\n')
    (s.repo / "shop.py").write_text("from cart import total\n\n\ndef checkout(xs):\n    return total(xs) + 1\n")
    (s.repo / "node_modules").mkdir()
    EN._git(s.repo, "init", "-q")
    s.meta.update({"repo": "o/r", "base": EN._commit(s.repo, "base"), "hidden": []})
    s.save_meta()
    yield SimpleNamespace(EN=EN, LS=LS, s=s, tools=EN.Tools(s, False))


def _local(monkeypatch, LS, tmp_path):
    """Run the box driver straight on this machine (no Docker here): same driver, same job, same parsing."""
    def run(tools, job, timeout):
        jf = tmp_path / "job.json"
        jf.write_text(json.dumps(job))
        p = subprocess.run([sys.executable, "-c", LS.DRIVER], cwd=str(tools.s.repo), env={**os.environ, "HOOLA_LSP_JOB": str(jf)},
                           capture_output=True, text=True, timeout=timeout)
        return LS._parse(p.stdout)
    monkeypatch.setattr(LS, "_exec", run)


def test_where_servers_come_from(tmp_path, monkeypatch):
    from app.devsahayak import lsp as LS, plugins as PL
    (tmp_path / ".lsp.json").write_text(json.dumps({"mypy-ls": {"command": "pylsp", "args": ["-v"],
                                                    "extensionToLanguage": {".py": "python"}, "startupTimeout": 9000,
                                                    "settings": {"pylsp": {"plugins": {}}}}, "bad": {"command": ""}}))
    plug = tmp_path / "plug"
    (plug / ".claude-plugin").mkdir(parents=True)
    (plug / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "go", "lspServers": {
        "gopls-plus": {"command": "gopls", "extensionToLanguage": {".go": "go"}}}}))
    monkeypatch.setattr(PL, "roots", lambda tenant: [plug])
    every = LS.servers(tmp_path, "her")
    names = [s["name"] for s in every]
    assert names[:2] == ["mypy-ls", "gopls-plus"] and "pyright" in names and "bad" not in names
    assert LS.server_for(tmp_path, "a/b.py", every=every)["name"] == "mypy-ls"          # the repo's own wins
    assert LS.server_for(tmp_path, "x.go", every=every)["origin"] == "plugin:plug"
    assert LS.server_for(tmp_path, "x.tsx", every=every)["name"] == "typescript"
    assert LS.server_for(tmp_path, "notes.txt", every=every) is None
    s = every[0]
    assert s["candidates"] == [["pylsp", "-v"]] and s["start_s"] == 9 and s["settings"]["pylsp"] == {"plugins": {}}


@pytest.mark.skipif(not HAS_PYRIGHT, reason="pyright-langserver is not on this machine")
def test_the_real_pyright_answers_every_operation(ses, monkeypatch, tmp_path):
    LS, tl = ses.LS, ses.tools
    _local(monkeypatch, LS, tmp_path)
    d = LS.tool(tl, {"operation": "goToDefinition", "filePath": "shop.py", "line": 5, "character": 13})
    assert "cart.py:1:5" in d and "def total" in d
    r = LS.tool(tl, {"operation": "findReferences", "filePath": "cart.py", "line": 1, "character": 6})
    assert "3 references in 2 files" in r and "shop.py:5:12" in r                  # shop.py opened by itself (git grep)
    h = LS.tool(tl, {"operation": "hover", "filePath": "cart.py", "line": 1, "character": 6})
    assert "def total(items: list[int]) -> int" in h and "Sum of the cart." in h
    assert "function checkout" in LS.tool(tl, {"operation": "documentSymbol", "filePath": "shop.py"})
    assert "checkout - shop.py:4" in LS.tool(tl, {"operation": "incomingCalls", "filePath": "cart.py", "line": 1, "character": 6})
    assert "function total - cart.py:1" in LS.tool(tl, {"operation": "workspaceSymbol", "query": "total"})
    (ses.s.repo / "shop.py").write_text("from cart import total\n\n\ndef checkout(xs):\n    return total(xs) + nope\n")
    dg = LS.tool(tl, {"operation": "diagnostics", "filePath": "shop.py"})
    assert '5:24 error: "nope" is not defined' in dg
    out = tl.run("lsp", {"operation": "hover", "filePath": "cart.py", "line": 1, "character": 6})   # the coder's own call
    assert "Sum of the cart." in out


def test_honest_answers_when_it_cannot(ses, monkeypatch, tmp_path):
    LS, tl = ses.LS, ses.tools
    _local(monkeypatch, LS, tmp_path)
    (ses.s.repo / "lib.rs").write_text("fn main() {}\n")
    monkeypatch.setattr(LS, "BUILTIN", [dict(b, candidates=[["no-such-rust-analyzer"]]) if b["name"] == "rust-analyzer" else b
                                        for b in LS.BUILTIN])
    assert "No language server for .rs files in this box: no-such-rust-analyzer is not installed" in LS.tool(
        tl, {"operation": "hover", "filePath": "lib.rs", "line": 1, "character": 4})
    assert "No language server covers .txt" in LS.tool(tl, {"operation": "hover", "filePath": "a.txt", "line": 1, "character": 1})
    assert "needs line and character" in LS.tool(tl, {"operation": "hover", "filePath": "cart.py"})
    assert "operation must be one of" in LS.tool(tl, {"operation": "rename"})


def test_a_repo_named_server_waits_for_her_once(ses):
    EN = ses.EN
    (ses.s.repo / ".lsp.json").write_text(json.dumps({"repo-ls": {"command": "./tools/ls.sh", "extensionToLanguage": {".py": "python"}}}))
    ask = EN.needs_ok("t1", "auto", ses.s, "lsp", {"operation": "hover", "filePath": "cart.py"})
    assert ask and ask["tool"] == "lsp" and ask["server"] == "repo-ls" and "./tools/ls.sh" in ask["what"]
    EN.PERMIT["t1"] = {**ask, "id": "p1", "_ev": SimpleNamespace(set=lambda: None)}
    assert EN.give_ok("t1", "p1", "always")                                         # 'always' remembers this server
    ses.s.__init__("t1")
    assert ses.s.meta["allow"]["lsp"] == ["repo-ls"] and not ses.s.meta["allow"].get("edits")
    assert EN.needs_ok("t1", "auto", ses.s, "lsp", {"operation": "hover", "filePath": "cart.py"}) is None
    (ses.s.repo / ".lsp.json").unlink()
    assert EN.needs_ok("t1", "steps", ses.s, "lsp", {"operation": "hover", "filePath": "cart.py"}) is None   # the box's own


def test_diagnostics_arrive_at_the_next_step_after_an_edit(ses, monkeypatch):
    EN, LS = ses.EN, ses.LS
    from app.devsahayak import brain as B
    calls = []

    def fake(tools, job, timeout):
        calls.append(job)
        return {"ok": True, "diagnostics": {"cart.py": [{"line": 3, "col": 12, "sev": 1, "msg": '"itemz" is not defined',
                                                        "source": "Pyright", "code": "reportUndefinedVariable"},
                                                       {"line": 1, "col": 1, "sev": 3, "msg": "an info line"}]}}
    monkeypatch.setattr(LS, "_exec", fake)
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    steps = iter([
        [{"type": "tool_use", "id": "r", "name": "read", "input": {"path": "cart.py"}}],
        [{"type": "tool_use", "id": "e", "name": "edit", "input": {"path": "cart.py", "old_string": "sum(items)", "new_string": "sum(itemz)"}}],
    ])
    seen = []
    monkeypatch.setattr(B, "call", lambda system, msgs, tools, **k: (seen.append(json.dumps(msgs[-1]["content"])) or
                        next(steps, [{"type": "tool_use", "id": "d", "name": "done", "input": {"explain": "ok"}}]), "tool_use"))
    evs = []
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="x", base="main", mode="", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", evs.append, None, None, "", None, "sha", "", "", ses.s)
    except Exception:  # noqa: BLE001
        pass
    assert calls and calls[0]["op"] == "diagnostics" and calls[0]["files"] == ["cart.py"]
    assert '3:12 error: \\"itemz\\" is not defined [Pyright reportUndefinedVariable]' in seen[2]
    assert "an info line" not in seen[2]                                               # problems only
    assert any(e.get("k") == "diagnostics" for e in evs) and any(e.get("k") == "lsp" for e in [EN.event(ses.tools, "lsp",
                                                                 {"operation": "hover", "filePath": "a.py"}, "At a.py:1:1")[0]])


def test_no_problems_means_nothing_is_said(ses, monkeypatch):
    LS = ses.LS
    monkeypatch.setattr(LS, "_exec", lambda tools, job, timeout: {"ok": True, "diagnostics": {"cart.py": []}})
    assert LS.after_edits(ses.tools, ["cart.py", "missing.py", "notes.txt"])
    assert LS.take("t1", wait=5) == "" and "t1" not in LS._PENDING
    (ses.s.repo / ".lsp.json").write_text(json.dumps({"repo-ls": {"command": "x", "extensionToLanguage": {".py": "python"}}}))
    assert not LS.after_edits(ses.tools, ["cart.py"])                                  # not started before she allowed it
    assert LS.after_edits(ses.tools, ["cart.py"], {"repo-ls"})


def test_agents_get_it_and_the_box_has_the_servers():
    from app.devsahayak import subagent as SA, repoconf as RC
    from app.devlab import box
    assert "lsp" in [t["name"] for t in SA.tool_specs("read")] and "lsp" in [t["name"] for t in SA.tool_specs("edit")]
    assert RC._claude_name("lsp") == "LSP" and RC.rule_matches("LSP", "lsp", {})
    assert box.BASE_REV == "4" and "pyright@1" in box.DOCKERFILE_TEXT and "typescript-language-server@4" in box.DOCKERFILE_TEXT
    assert (ROOT / "deploy" / "devlab" / "Dockerfile").read_text() == box.DOCKERFILE_TEXT
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "case 'lsp'" in js and "case 'diagnostics'" in js and "Found the references" in js
    d = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "case 'lsp':" in d and "case 'diagnostics':" in d and "Found the references" in d
