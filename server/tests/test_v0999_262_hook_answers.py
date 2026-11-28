"""v0.999 HOOK ANSWERS LIKE CLAUDE CODE (owner: 'Hook answers ... LETS WORK ON IT'): a repo's hook can answer in JSON on stdout
the way Claude Code reads it - PreToolUse permissionDecision allow / deny / ask (+ reason) and updatedInput, decision
block + reason (PostToolUse / Stop / SubagentStop / UserPromptSubmit), additionalContext (SessionStart / UserPromptSubmit /
PostToolUse), continue:false + stopReason (the round stops), systemMessage (shown to her); exit 2 + stderr still blocks,
any other exit is a non-blocking error. Hooks now see Claude Code's own field names (tool_input.file_path)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_one_answer_read_like_claude_code():
    from app.devsahayak.repoconf import hook_answer as A
    a = A("PreToolUse", 2, "{\"decision\": \"approve\"}", "rm is not allowed")
    assert a["block"] and a["reason"] == "rm is not allowed" and a["decision"] == ""          # exit 2: JSON ignored
    a = A("PreToolUse", 1, "", "lint crashed")
    assert not a["block"] and a["error"] == "lint crashed"                                    # other exits never block
    j = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "no prod"}}
    a = A("PreToolUse", 0, json.dumps(j), "")
    assert a["decision"] == "deny" and a["reason"] == "no prod"
    j = {"hookSpecificOutput": {"permissionDecision": "allow", "updatedInput": {"command": "npm test -- --ci"}}, "systemMessage": "CI mode"}
    a = A("PreToolUse", 0, json.dumps(j), "")
    assert a["decision"] == "allow" and a["updated"] == {"command": "npm test -- --ci"} and a["message"] == "CI mode"
    assert A("PreToolUse", 0, '{"decision": "block", "reason": "old way"}', "")["decision"] == "deny"    # the older fields
    assert A("PreToolUse", 0, '{"decision": "approve"}', "")["decision"] == "allow"
    a = A("Stop", 0, '{"decision": "block", "reason": "tests still red"}', "")
    assert a["block"] and a["reason"] == "tests still red"
    a = A("PostToolUse", 0, json.dumps({"hookSpecificOutput": {"additionalContext": "file is generated, do not edit"}}), "")
    assert a["context"] == "file is generated, do not edit" and not a["block"]
    a = A("Stop", 0, '{"continue": false, "stopReason": "budget used"}', "")
    assert a["stop"] and a["stop_reason"] == "budget used"
    assert A("SessionStart", 0, "branch: main, 3 open issues", "")["context"] == "branch: main, 3 open issues"
    assert A("PostToolUse", 0, "formatted 2 files", "")["context"] == "" and A("PostToolUse", 0, "formatted 2 files", "")["shown"]


def test_hooks_see_claude_codes_field_names():
    from app.devsahayak import repoconf as RC
    j = RC.hook_input("PreToolUse", "t1", "edit", {"path": "src/a.py", "old_string": "x", "new_string": "y", "_secret": 1})
    assert j["tool_name"] == "Edit" and j["tool_input"] == {"file_path": "src/a.py", "old_string": "x", "new_string": "y"}
    assert RC.from_claude_input("edit", {"file_path": "src/b.py", "new_string": "z"}) == {"path": "src/b.py", "new_string": "z"}
    assert RC.hook_input("PreToolUse", "t1", "notebook_edit", {"path": "n.ipynb", "cell": 2})["tool_input"] == {"notebook_path": "n.ipynb", "cell_number": 2}


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _hooked(EN, hooks):
    ses = EN.Session("t1")
    (ses.repo / ".claude").mkdir(parents=True, exist_ok=True)
    (ses.repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": hooks}))
    ses.save_meta()
    return ses


def test_run_hooks_keeps_json_and_stderr_apart_and_merges(ws, monkeypatch):
    EN = ws
    from app.devsahayak import repoconf as RC
    from app.devlab import box
    ses = _hooked(EN, {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "a"}, {"type": "command", "command": "b"}]}]})
    tl = EN.Tools(ses, False)
    tl.conf = RC.settings(ses.repo)
    monkeypatch.setattr(tl, "_image", lambda: ("img", ""))
    answers = iter([(0, json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}), ""),
                    (0, json.dumps({"hookSpecificOutput": {"permissionDecision": "ask", "permissionDecisionReason": "touches deploy"}}), "warn")])
    seen = []

    def run_in(image, files_dir, command, **kw):
        sep = re.search(r"printf '\\n(HOOLA_HOOK_ERR_\w+)", command).group(1)
        seen.append(json.loads(re.search(r"\n(\{.*\})\n", command).group(1)))
        rc, so, se = next(answers)
        return {"rc": rc, "out": so + "\n" + sep + "\n" + se}
    monkeypatch.setattr(box, "run_in", run_in)
    said = EN.run_hooks(tl, "PreToolUse", "bash", {"command": "make deploy"})
    assert said["decision"] == "ask" and said["reason"] == "touches deploy"        # the stricter answer wins
    assert seen[0]["tool_input"] == {"command": "make deploy"} and seen[0]["tool_name"] == "Bash"


def _round(EN, monkeypatch, hooks, brain_steps, tmp_mode=""):
    """One real round with fakes for the checkout, the brain, the tools and the hooks' answers."""
    from app.devsahayak import brain as B
    ses = _hooked(EN, {k: [{"hooks": [{"type": "command", "command": "x"}]}] for k in hooks})
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    ran = []
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: ran.append((name, dict(inp))) or "ok")
    monkeypatch.setattr(EN, "run_hooks", lambda tools, event, tool="", inp=None, out="", prompt="", emit=None:
                        {"block": False, "text": "", "decision": "", "reason": "", "updated": None, "context": "", "stop": False,
                         "stop_reason": "", "message": "", **(hooks.get(event) or {})})
    steps = iter(brain_steps)
    seen = []

    def call(system, msgs, tools, **k):
        seen.append(msgs[-1]["content"])
        return next(steps), "tool_use"
    monkeypatch.setattr(B, "call", call)
    evs = []
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="fix it", base="main", mode=tmp_mode, tenant_id="", conv="")
    try:
        out = EN._round(None, t, "tok", "", False, "", evs.append, None, None, "", None, "sha", "", "", ses)
    except Exception as e:      # the quality gate / git parts after done are not what this test checks
        out = e
    return ran, seen, evs, out


BASH = [{"type": "tool_use", "id": "b1", "name": "bash", "input": {"command": "npm test"}}]
DONE = [{"type": "tool_use", "id": "d1", "name": "done", "input": {"explain": "done"}}]


def test_the_loop_follows_deny_change_allow_context_and_stop(ws, monkeypatch):
    EN = ws
    ran, seen, evs, _ = _round(EN, monkeypatch, {"PreToolUse": {"decision": "deny", "reason": "no tests on prod"}}, [BASH, DONE])
    assert ran == [] and "no tests on prod" in json.dumps(seen[1])
    ran, seen, evs, _ = _round(EN, monkeypatch, {"PreToolUse": {"updated": {"command": "npm test -- --ci"}}}, [BASH, DONE])
    assert ran == [("bash", {"command": "npm test -- --ci"})]
    # allow skips her yes even in 'ask each step'; without it the step would wait for her
    ran, seen, evs, _ = _round(EN, monkeypatch, {"PreToolUse": {"decision": "allow"}}, [BASH, DONE], tmp_mode="steps")
    assert ran and not any(e.get("k") == "perm" for e in evs)
    ran, seen, evs, _ = _round(EN, monkeypatch, {"PostToolUse": {"context": "generated file - do not edit"}}, [BASH, DONE])
    assert "<post_tool_hook>" in json.dumps(seen[1]) and "generated file" in json.dumps(seen[1])
    ran, seen, evs, out = _round(EN, monkeypatch, {"PreToolUse": {"stop": True, "stop_reason": "budget used"}}, [BASH, BASH, DONE])
    assert ran == [] and len(seen) == 1 and any(e.get("k") == "hook" and e.get("stop") for e in evs)


def test_the_screens_say_what_the_hook_did():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "allowed it" in js and "asked you first" in js and "changed the step" in js and "stopped the work" in js and "hcd-hookmsg" in js
    d = (ROOT / "lib/ui/code/code_session.dart").read_text() + (ROOT / "lib/ui/code/code_words.dart").read_text()
    assert "and allowed it" in d and "and changed the step" in d and "stopped the work" in d and "s['msg']" in d
