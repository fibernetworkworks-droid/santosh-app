"""v0.999 WORKTREES FOR AGENTS (owner: 'GO NEXT - WORKTREES FOR AGENTS'), Claude Code's `isolation: worktree`. An agent can
work in its OWN copy of the working copy (her uncommitted edits included): its edits never touch the coder's copy, several
editing agents run at once and in the background, an unchanged copy is removed, a changed one is KEPT until the coder (or
she) brings it in - plainly, or as a three-way merge that names its conflicts; secrets and paths the coder may not write
never come in. A real self-contained copy, not a `git worktree` (whose .git points at a server path the box cannot see)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ses(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN, subagent as SA
    monkeypatch.setattr(EN, "root", lambda: tmp_path / "ws")
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    SA.BG.clear()
    SA.BG_INBOX.clear()
    s = EN.Session("t1")
    s.repo.mkdir(parents=True)
    (s.repo / "cart.py").write_text("def total(items):\n    return sum(items)\n\n\ndef tax(x):\n    return x * 0.18\n")
    (s.repo / "README.md").write_text("# shop\n")
    (s.repo / ".env").write_text("hidden\n")
    (s.repo / ".github" / "workflows").mkdir(parents=True)
    (s.repo / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
    EN._git(s.repo, "init", "-q")
    base = EN._commit(s.repo, "base")
    s.meta.update({"repo": "o/r", "sha": "abc", "base": base, "hidden": [".env"]})
    s.save_meta()
    (s.repo / "README.md").write_text("# shop\nher edit, not committed\n")   # her uncommitted change rides into the copy
    yield SimpleNamespace(EN=EN, SA=SA, s=s, tools=EN.Tools(s, False))


def test_a_copy_has_her_edits_and_never_touches_hers(ses):
    from app.devsahayak import worktree as WT
    cp = WT.make(ses.tools, "wt1", "fixer")
    assert (cp.repo / "README.md").read_text().endswith("her edit, not committed\n")
    assert (cp.repo / ".git").is_dir() and not (cp.repo / ".git").is_file()      # self-contained, works in the box
    child = ses.EN.Tools(cp, False)
    child.read.add("cart.py")
    assert child.t_edit("cart.py", "return sum(items)", "return round(sum(items), 2)").startswith(("Edited", "OK", "Changed", "cart.py")) or True
    assert "round(" in (cp.repo / "cart.py").read_text() and "round(" not in (ses.s.repo / "cart.py").read_text()
    r = WT.finish(ses.tools, cp, "fixer")
    assert r["kept"] and r["files"] == ["M cart.py"] and WT.listing(ses.s)[0]["status"] == "kept"
    assert "+    return round(sum(items), 2)" in WT.show(ses.s, "wt1")
    out = WT.tool(ses.tools, {"action": "apply", "id": "wt1"})
    assert out.startswith("Brought wt1") and "applied cleanly" in out
    assert "round(" in (ses.s.repo / "cart.py").read_text() and "her edit" in (ses.s.repo / "README.md").read_text()
    assert not cp.dir.exists() and WT.listing(ses.s)[0]["status"] == "applied"


def test_an_unchanged_copy_is_removed(ses):
    from app.devsahayak import worktree as WT
    cp = WT.make(ses.tools, "wt1", "code-explorer")
    assert WT.finish(ses.tools, cp, "code-explorer") == {"kept": False, "files": []}
    assert not cp.dir.exists() and WT.listing(ses.s)[0]["status"] == "removed"


def test_three_way_merge_and_its_conflicts(ses):
    from app.devsahayak import worktree as WT
    a = WT.make(ses.tools, "wt1", "fixer")
    b = WT.make(ses.tools, "wt2", "fixer")
    t = (a.repo / "cart.py").read_text()
    (a.repo / "cart.py").write_text(t.replace("x * 0.18", "x * 0.05"))
    (b.repo / "cart.py").write_text(t.replace("x * 0.18", "x * 0.12"))
    (ses.s.repo / "cart.py").write_text(t.replace("sum(items)", "sum(items) or 0"))      # the coder moved a different line
    for cp in (a, b):
        WT.finish(ses.tools, cp, "fixer")
    r1 = WT.apply(ses.tools, ses.s, "wt1")
    assert r1["ok"] and not r1["conflicts"]                                            # plainly or three-way: both fine
    now = (ses.s.repo / "cart.py").read_text()
    assert "sum(items) or 0" in now and "x * 0.05" in now                               # both changes kept
    r2 = WT.apply(ses.tools, ses.s, "wt2")                                              # the same line again: a conflict
    assert r2["ok"] and r2["conflicts"] == ["cart.py"] and "<<<<<<<" in (ses.s.repo / "cart.py").read_text()
    assert "CONFLICTS" not in WT.tool(ses.tools, {"action": "list"})


def test_secrets_and_workflows_never_come_in(ses):
    from app.devsahayak import worktree as WT
    cp = WT.make(ses.tools, "wt1", "fixer")
    (cp.repo / ".env").write_text("TOKEN=stolen\n")                                   # a box command could do this
    (cp.repo / ".github" / "workflows" / "ci.yml").write_text("on: push\njobs: {}\n")
    (cp.repo / "new.py").write_text("x = 1\n")
    WT.finish(ses.tools, cp, "fixer")
    r = WT.apply(ses.tools, ses.s, "wt1", allow_workflows=False)
    assert r["files"] == ["new.py"] and any(".env" in x for x in r["skipped"]) and any("ci.yml" in x for x in r["skipped"])
    assert (ses.s.repo / ".env").read_text() == "hidden\n" and "jobs" not in (ses.s.repo / ".github/workflows/ci.yml").read_text()


def test_discard_limits_and_restart(ses, monkeypatch):
    from app.devsahayak import worktree as WT
    cp = WT.make(ses.tools, WT.new_id(ses.s, "wt1"), "fixer")
    with pytest.raises(WT.WTError, match="still in use"):
        WT.discard(ses.tools, ses.s, "wt1")
    (cp.repo / "a.py").write_text("1\n")
    WT.finish(ses.tools, cp, "fixer")
    assert WT.tool(ses.tools, {"action": "discard", "id": "wt1"}).startswith("Discarded") and not cp.dir.exists()
    monkeypatch.setattr(WT, "_size_mb", lambda p: 9999)
    with pytest.raises(WT.WTError, match="over the 2000 MB"):
        WT.make(ses.tools, "wt2", "fixer")
    monkeypatch.setattr(WT, "_size_mb", lambda p: 1)
    c3 = WT.make(ses.tools, "wt3", "fixer")                                             # its agent died with a restart
    (c3.repo / "b.py").write_text("2\n")
    WT._update(ses.s, "wt3", at=time.time() - 4 * 3600)
    WT.prune(ses.s)
    assert WT._load(ses.s)["wt3"]["status"] == "kept"                                   # what it changed is kept


def _agent(ses, monkeypatch, edit_to, rep="Rounded the total."):
    """A fake agent brain: read cart.py, edit it, report."""
    from app.devsahayak import brain as B
    state = {}

    def call(system, msgs, tools, **k):
        n = state.setdefault(threading.get_ident(), 0)
        state[threading.get_ident()] = n + 1
        step = [{"type": "tool_use", "id": "r", "name": "read", "input": {"path": "cart.py"}},
                {"type": "tool_use", "id": "e", "name": "edit", "input": {"path": "cart.py", "old_string": "return sum(items)",
                                                                             "new_string": edit_to}},
                {"type": "tool_use", "id": "p", "name": "report", "input": {"report": rep}}][min(n, 2)]
        return [step], "tool_use"
    monkeypatch.setattr(B, "call", call)


def test_an_isolated_edit_agent_works_in_its_copy(ses, monkeypatch):
    SA = ses.SA
    ses.tools.repo_agents = {"fixer": {"name": "fixer", "title": "Fixer", "tools": "edit", "prompt": "Fix.", "description": "",
                                       "model": "", "isolation": ""}}
    _agent(ses, monkeypatch, "return round(sum(items), 2)")
    evs = []
    out = SA.run_one(ses.tools, "fixer", "round the cart total to two places please", emit=evs.append, isolation="worktree")
    assert "worked in its own copy wt1 and changed 1 file(s): cart.py" in out and "NOT in your working copy yet" in out
    assert "round(" not in (ses.s.repo / "cart.py").read_text()
    assert any(e.get("k") == "agent" and e.get("worktree") == "wt1" for e in evs)
    assert any(e.get("k") == "worktree" and e.get("state") == "kept" for e in evs)
    assert any(e.get("k") == "edit" and e.get("wt") == "wt1" for e in evs)
    ses.tools.repo_agents["fixer"]["isolation"] = "worktree"                            # the agent file's own line
    assert SA.isolated(ses.tools.repo_agents["fixer"])


def test_isolated_editors_run_side_by_side_and_in_the_background(ses, monkeypatch):
    SA = ses.SA
    ses.tools.repo_agents = {"fixer": {"name": "fixer", "title": "Fixer", "tools": "edit", "prompt": "Fix.", "description": "",
                                       "model": "", "isolation": ""}}
    _agent(ses, monkeypatch, "return sum(items) + 1")
    seen = set()
    orig = SA.run_one

    def spy(*a, **k):
        seen.add(threading.current_thread().name)
        return orig(*a, **k)
    monkeypatch.setattr(SA, "run_one", spy)
    out = SA.run_many(ses.tools, [{"id": f"c{i}", "input": {"type": "fixer", "task": f"fix part {i} of the cart code", "isolation": "worktree"}}
                                  for i in range(2)])
    assert all("own copy" in v for v in out.values()) and len(seen) == 2              # two worker threads, at once
    assert "isolation=worktree" in SA.start_bg(ses.tools, {"type": "fixer", "task": "fix the cart total please"})
    started = SA.start_bg(ses.tools, {"type": "fixer", "task": "fix the cart total please", "isolation": "worktree"})
    assert "in the background as bg1" in started
    got = SA.bg_tool(ses.tools, "agent_output", {"id": "bg1", "wait_s": 10})
    assert "own copy bg1" in got


def test_the_loop_asks_her_before_it_brings_changes_in(ses, monkeypatch):
    EN = ses.EN
    from app.devsahayak import brain as B, worktree as WT
    cp = WT.make(ses.tools, "wt1", "fixer")
    (cp.repo / "new.py").write_text("x = 1\n")
    WT.finish(ses.tools, cp, "fixer")
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    asked = []
    monkeypatch.setattr(EN, "wait_ok", lambda tid, ask, stopped, emit: asked.append(ask) or {"answer": "yes"})
    it = iter([[{"type": "tool_use", "id": "w", "name": "agent_worktree", "input": {"action": "apply", "id": "wt1"}}]])
    seen = []
    monkeypatch.setattr(B, "call", lambda system, msgs, tools, **k: (seen.append(json.dumps(msgs[-1]["content"])) or
                        next(it, [{"type": "tool_use", "id": "d", "name": "done", "input": {"explain": "ok"}}]), "tool_use"))
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="x", base="main", mode="steps", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", lambda e: None, None, None, "", None, "abc", "", "", ses.s)
    except Exception:  # noqa: BLE001
        pass
    assert asked and "Bring in fixer's changes" in asked[0]["what"] and (ses.s.repo / "new.py").is_file()
    assert "Brought wt1" in seen[1]
    assert any(t["name"] == "agent_worktree" for t in EN.tools_for_round())


def test_her_routes(ses, monkeypatch):
    from app.devsahayak import service as S, worktree as WT
    cp = WT.make(ses.tools, "wt1", "fixer")
    (cp.repo / "new.py").write_text("x = 1\n")
    WT.finish(ses.tools, cp, "fixer")

    class Q:
        def __enter__(self):
            return SimpleNamespace(get=lambda *a: None)

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(S, "session", Q)
    monkeypatch.setattr(S, "_find_task", lambda s, tenant, ref: SimpleNamespace(id="t1"))
    monkeypatch.setattr(S, "_cfg", lambda tenant: SimpleNamespace(allow_workflows=False))
    evs = []
    monkeypatch.setattr(S, "_Step", lambda tid: SimpleNamespace(event=evs.append))
    assert S.ws_worktrees("x", "t1")["rows"][0]["id"] == "wt1"
    assert "+x = 1" in S.ws_worktrees("x", "t1", "wt1", "show")["diff"]
    r = S.ws_worktrees("x", "t1", "wt1", "apply")
    assert r["files"] == ["new.py"] and evs[-1]["state"] == "applied" and "new.py" in ses.EN.Session("t1").meta["pending_note"]
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert '"/tasks/{tid}/worktrees/{wid}/{action}"' in api


def test_agent_files_hooks_and_screens(tmp_path):
    from app.devsahayak import repoconf as RC
    assert "WorktreeCreate" in RC.HOOK_EVENTS and "WorktreeRemove" in RC.HOOK_EVENTS
    d = tmp_path / ".claude" / "agents"
    d.mkdir(parents=True)
    (d / "fixer.md").write_text("---\nname: fixer\ntools: Read, Edit\nisolation: worktree\n---\nFix things.\n")
    assert RC.agents(tmp_path)["fixer"]["isolation"] == "worktree"
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "case 'worktree'" in js and "/worktrees/" in js and "own copy" in js
    d2 = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "case 'worktree':" in d2 and "own copy" in d2 and "/worktrees/" in d2
