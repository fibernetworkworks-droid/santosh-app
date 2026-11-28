"""v0.999 SUPERPOWERS for Hoola Code (owner: 'https://github.com/obra/superpowers.git --- read this first then make hoola
code more powerfull with this'): its skills as Hoola Code's own library, the rule to use them, the right ones picked in
code for each kind of work, and two of its iron laws checked in code."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "server" / "app" / "devsahayak"


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("DEV_SUPERPOWERS", "true")         # conftest pins it off for the older suites
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_superpowers", True)


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _ses(EN, files=None):
    ses = EN.Session("t1")
    ses.repo.mkdir(parents=True, exist_ok=True)
    for k, v in (files or {"a.py": "x = 1\n"}).items():
        (ses.repo / k).parent.mkdir(parents=True, exist_ok=True)
        (ses.repo / k).write_text(v)
    EN._git(ses.repo, "init", "-q")
    ses.meta.update({"repo": "o/r", "base": EN._commit(ses.repo, "base"), "hidden": []})
    ses.save_meta()
    return ses


# ---------------------------------------------------------------- the library
def test_thirteen_skills_each_with_a_trigger_and_hoola_s_own_tools():
    from app.devsahayak import superpowers as SP
    sk = SP.skills()
    assert sorted(sk) == sorted(["brainstorming", "dispatching-parallel-agents", "executing-plans", "finishing-a-branch",
                                 "receiving-code-review", "requesting-code-review", "subagent-driven-development",
                                 "systematic-debugging", "test-driven-development", "using-worktrees",
                                 "verification-before-completion", "writing-plans", "writing-skills"])
    for name, v in sk.items():
        assert v["description"] and v["when"] and len(v["body"]) > 400, name
        assert "git commit" not in v["body"].replace("Never use bash git worktree / git commit yourself", ""), name
    assert "NO FIXES" not in sk["systematic-debugging"]["body"] and "no fix without finding the root cause" in sk["systematic-debugging"]["body"]
    assert "3 or more: STOP" in sk["systematic-debugging"]["body"]
    assert "agent_worktree" in sk["subagent-driven-development"]["body"] and "ask_user" in sk["brainstorming"]["body"]
    assert "HER tap" in " ".join(sk["finishing-a-branch"]["body"].split())                     # Hoola never merges
    assert "DATA, not instructions" in sk["receiving-code-review"]["body"]
    sb = SP.system_block()
    assert "Using <skill> to <purpose>" in sb and "superpowers:systematic-debugging" in sb and len(sb) < 4200
    assert "Superpowers" in (ROOT / "THIRD_PARTY_NOTICES.md").read_text()


def test_the_right_skills_are_picked_for_the_kind_of_work():
    from app.devsahayak import superpowers as SP
    assert SP.pick("fix", "the login page crashes with a 500") == [
        "systematic-debugging", "test-driven-development", "verification-before-completion"]
    assert SP.pick("write", "add a dark mode switch") == ["test-driven-development", "verification-before-completion"]
    assert SP.pick("explain", "why does this fail?") == []
    assert SP.pick("write", "/ponytail-review") == []
    assert SP.pick("write", "/brainstorm a referral feature") == ["brainstorming"]
    assert SP.pick("write", "/write-plan") == ["writing-plans"]
    assert SP.pick("write", "/execute-plan")[0] in ("subagent-driven-development", "executing-plans")
    assert SP.pick("write", "", "<pr_review_comments>\n...")[0] == "receiving-code-review"


def test_picked_skills_ride_once_per_session(ws):
    EN = ws
    from app.devsahayak import superpowers as SP
    ses = _ses(EN)
    evs = []
    t = SimpleNamespace(kind="fix")
    first = SP.auto_block(t, "the parser crashes on empty input", "", ses, evs.append)
    assert first.count("<skill name=") == 3 and "no fix without finding the root cause" in first
    assert [e["name"] for e in evs] == ["systematic-debugging", "test-driven-development", "verification-before-completion"]
    assert SP.auto_block(t, "still crashes", "", ses, evs.append) == ""               # given already in this session
    again = SP.auto_block(t, "/brainstorm the next feature", "", ses, evs.append)
    assert "<her_command>/brainstorm</her_command>" in again and "ONE QUESTION AT A TIME" in again


# ---------------------------------------------------------------- the iron laws in code
def test_three_failed_fixes_in_a_row_say_stop():
    from app.devsahayak import superpowers as SP
    tr = SP.Tracker()
    tr.edit("tests/test_parse.py")
    assert tr.bash("python -m pytest -q", 1) == ""            # the red test: not a failed fix
    for i in range(2):
        tr.edit("src/parse.py")
        assert tr.bash("pytest -q tests/test_parse.py", 1) == ""
    tr.edit("src/parse.py")
    note = tr.bash("pytest -q", 1)
    assert "3 fixes in a row" in note and "question" in note
    tr.edit("src/parse.py")
    assert tr.bash("pytest -q", 1) == ""                       # said once
    assert tr.bash("pytest -q", 0) == "" and tr.failed_fixes == 0
    assert tr.bash("ls -la", 1) == ""                           # not a test command: not counted


def test_a_claim_without_fresh_proof_is_caught():
    from app.devsahayak import superpowers as SP
    tr = SP.Tracker()
    assert not tr.unproven_claim({"explain": "Fixed it, tests pass."})       # nothing edited: nothing to prove
    tr.edit("src/a.py")
    assert tr.unproven_claim({"explain": "Fixed the bug. All tests pass."})
    assert not tr.unproven_claim({"explain": "Changed it.", "test_plan": "Could not run the tests in the box."})
    assert not tr.unproven_claim({"explain": "Which file do you mean?"})
    tr.bash("npm test", 0)
    assert not tr.unproven_claim({"explain": "Fixed. Tests pass."})
    tr.edit("README.md")                                         # docs need no test run
    assert not tr.unproven_claim({"explain": "Fixed. Tests pass."})
    tr.edit("src/b.py")
    assert tr.unproven_claim({"explain": "Done, it works."}) and "changed code after" in SP.proof_text(tr)


def _round(EN, monkeypatch, text, ses, steps_in, bash_rc=None):
    from app.devsahayak import brain as B
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})

    def run(self, name, inp):
        out = "ok"
        if name == "edit":
            out = "Edited " + inp.get("path", "")
        if name == "bash":
            self.last_bash = {"cmd": inp.get("command"), "rc": bash_rc}
            out = f"exit code {bash_rc}"
        return self._sp_track(name, inp, out)
    monkeypatch.setattr(EN.Tools, "run", run)
    steps = iter(steps_in)
    seen, systems = [], []

    def call(system, msgs, tools, **k):
        systems.append(system)
        seen.append(msgs[-1]["content"])
        return next(steps), "tool_use"
    monkeypatch.setattr(B, "call", call)
    evs = []
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text=text, base="main", mode="", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", evs.append, None, None, "", None, "sha", "", "", ses)
    except Exception:  # noqa: BLE001 - the git parts after done are not what this test checks
        pass
    return seen, systems, evs


EDIT = [{"type": "tool_use", "id": "e1", "name": "edit", "input": {"path": "a.py", "old_string": "1", "new_string": "2"}}]
CLAIM = [{"type": "tool_use", "id": "d1", "name": "done", "input": {"explain": "Fixed it. All tests pass."}}]
CLAIM2 = [{"type": "tool_use", "id": "d2", "name": "done", "input": {"explain": "Fixed it. All tests pass."}}]


def test_a_round_carries_the_skills_and_sends_an_unproven_done_back(ws, monkeypatch):
    EN = ws
    ses = _ses(EN)
    seen, systems, evs = _round(EN, monkeypatch, "the total is wrong when the cart is empty", ses, [EDIT, CLAIM, CLAIM2])
    assert "HOOLA CODE'S SKILLS" in systems[0] and "superpowers:writing-plans" in systems[0]
    assert '<skill name="superpowers:systematic-debugging"' in str(seen[0])
    assert any(e.get("k") == "skill" for e in evs)
    assert "verification before completion" in json.dumps(seen[2])           # the claim came back once
    ses2 = _ses(EN)
    run_ok = [{"type": "tool_use", "id": "b1", "name": "bash", "input": {"command": "pytest -q"}}]
    seen, systems, evs = _round(EN, monkeypatch, "the total is wrong", ses2, [EDIT, run_ok, CLAIM, CLAIM2], bash_rc=0)
    assert "verification before completion" not in json.dumps(seen)         # proven after the edit: no gate


def test_the_skill_tool_reads_them_and_hides_the_old_chat_copies(ws):
    EN = ws
    ses = _ses(EN)
    tl = EN.Tools(ses, False)
    tl.conf, tl.tenant = {}, ""
    got = tl.t_skill("read", "superpowers:writing-plans")
    assert got.startswith('<skill name="superpowers:writing-plans"') and "SELF-REVIEW" in got
    assert "superpowers:test-driven-development" in tl.t_skill("list")
    from app.devsahayak import superpowers as SP
    assert SP.hidden_copies(["sp-systematic-debugging", "sp-using-git-worktrees", "sp-diagnosing-superpowers", "mine"]) == {
        "sp-systematic-debugging", "sp-using-git-worktrees"}


def test_web_phone_and_plan_pass_have_it():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "case 'skill':" in js and "'brainstorm'" in js and "'execute-plan'" in js
    dart = (ROOT / "lib/ui/code/code_assist.dart").read_text()
    assert "('brainstorm', " in dart and "'write-plan'" in dart
    assert "case 'skill':" in (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "case 'skill':" in (ROOT / "lib/ui/code/code_words.dart").read_text()
    assert "writing-plans way" in (DEV / "loop.py").read_text()
    assert "superpowers" in (DEV / "service.py").read_text()


def test_version():
    from app.main import APP_VERSION
    assert re.match(r"^\d+\.\d+\.\d+", APP_VERSION)
