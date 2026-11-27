"""v0.999 AN AGENT'S OWN MODEL (owner: 'Agent model ... WORK ON IT SAME AS CLAUDE CODE'): the `model:` line of an agent file
(.claude/agents/*.md or a plugin's) is followed like Claude Code - inherit / none = the session's model, haiku / sonnet / opus
= that Claude model on whichever brain Hoola Code runs on, a full id the brain can run; anything else = the session's model,
said in the report. The coder's own model comes back after an agent that ran in its thread."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    yield EN


def _repo(EN):
    ses = EN.Session("t1")
    a = ses.repo / ".claude" / "agents"
    a.mkdir(parents=True)
    (a / "quick.md").write_text("---\nname: quick\ndescription: Fast look\ntools: Read, Grep\nmodel: haiku\n---\nLook fast.\n")
    (a / "deep.md").write_text("---\nname: deep\ndescription: Hard thinking\ntools: Read\nmodel: opus\n---\nThink hard.\n")
    (a / "same.md").write_text("---\nname: same\ndescription: Session model\ntools: Read\nmodel: inherit\n---\nRead.\n")
    (a / "odd.md").write_text("---\nname: odd\ndescription: Bad model\ntools: Read\nmodel: gpt-9-turbo\n---\nRead.\n")
    (a / "fixer.md").write_text("---\nname: fixer\ndescription: Edits\ntools: Read, Edit\nmodel: sonnet\n---\nFix.\n")
    return ses


def test_the_model_line_is_read(ws):
    from app.devsahayak import repoconf as RC
    ag = RC.agents(_repo(ws).repo)
    assert ag["quick"]["model"] == "haiku" and ag["deep"]["model"] == "opus" and ag["same"]["model"] == "inherit"


def test_aliases_on_each_brain(monkeypatch):
    from app.devsahayak import brain as B, subagent as SA
    monkeypatch.setattr(B, "brain_name", lambda: "claude")
    assert SA.agent_model("haiku") == ("claude-haiku-5-5", "") and SA.agent_model("Opus") == ("claude-opus-5-5", "")
    assert SA.agent_model("inherit") == ("", "") and SA.agent_model("") == ("", "")
    assert SA.agent_model("claude-sonnet-5-5") == ("claude-sonnet-5-5", "")
    m, why = SA.agent_model("gpt-9-turbo")
    assert m == "" and "session's model" in why
    monkeypatch.setattr(B, "brain_name", lambda: "qwen")
    assert SA.agent_model("haiku") == ("anthropic/claude-haiku-5.5", "")
    assert SA.agent_model("qwen/qwen3.8-max") == ("qwen/qwen3.8-max", "")
    assert SA.agent_model("claude-haiku-5-5")[0] == ""            # a bare Claude id means nothing through OpenRouter
    assert SA.model_label("anthropic/claude-haiku-5.5") == "Haiku 5.5" and SA.model_label("claude-opus-5-5") == "Opus 5.5"


def test_each_agent_runs_on_its_own_model_and_the_coder_gets_its_back(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B, repoconf as RC, subagent as SA
    ses = _repo(EN)
    tools = EN.Tools(ses, False)
    tools.repo_agents = RC.agents(ses.repo)
    monkeypatch.setattr(B, "brain_name", lambda: "claude")
    seen = []

    def call(system, msgs, specs, **k):
        seen.append(B.model_for())
        return [{"type": "tool_use", "id": "r1", "name": "report", "input": {"text": "all fine"}}], "tool_use"
    monkeypatch.setattr(B, "call", call)
    B.PICK.model, B.PICK.effort = "claude-sonnet-5-5", "high"
    evs = []
    out = SA.run_one(tools, "quick", "Look at the cart module and report what it does", emit=evs.append,
                     pick=("claude-sonnet-5-5", "high"))
    assert seen[-1] == "claude-haiku-5-5" and out.startswith("[Quick on Haiku 5.5")
    assert any(e.get("k") == "agent" and e.get("model") == "Haiku 5.5" for e in evs)
    assert B.PICK.model == "claude-sonnet-5-5" and not getattr(B.PICK, "agent", False)      # the coder's model is back
    SA.run_one(tools, "same", "Look at the cart module and report what it does", pick=("claude-sonnet-5-5", "high"))
    assert seen[-1] == "claude-sonnet-5-5"
    out = SA.run_one(tools, "odd", "Look at the cart module and report what it does", pick=("claude-sonnet-5-5", "high"))
    assert seen[-1] == "claude-sonnet-5-5" and "cannot run here" in out
    monkeypatch.setattr(B, "brain_name", lambda: "qwen")
    B.PICK.model = ""
    SA.run_one(tools, "deep", "Look at the cart module and report what it does", pick=("", "high"))
    assert seen[-1] == "anthropic/claude-opus-5.5" and B.qwen_model() != "anthropic/claude-opus-5.5"   # pinned only while it runs


def test_a_repo_edit_agent_never_runs_side_by_side(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B, repoconf as RC, subagent as SA
    import threading
    ses = _repo(EN)
    tools = EN.Tools(ses, False)
    tools.repo_agents = RC.agents(ses.repo)
    main = threading.get_ident()
    where = {}
    monkeypatch.setattr(SA, "run_one", lambda t, name, task, files=None, **k: where.setdefault(name, threading.get_ident()) and "ok")
    SA.run_many(tools, [{"id": "a", "input": {"type": "quick", "task": "x" * 20}}, {"id": "b", "input": {"type": "deep", "task": "x" * 20}},
                        {"id": "c", "input": {"type": "fixer", "task": "x" * 20}}])
    assert where["fixer"] == main and where["quick"] != main


def test_the_screens_show_it():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "' · on ' + esc(s.model)" in js and "' · model ' + esc(a.model)" in js
    dart = "".join(p.read_text() for p in (ROOT / "lib/ui/code").glob("*.dart"))
    assert "on ${cs(s['model'])}" in dart and "model ${cs(a['model'])}" in dart and "on ${_s(s['model'])}" in dart
