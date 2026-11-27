"""v0.999 HOOLA CODE'S ENGINE, CLAUDE CODE'S WAY (owner: 'Build items 1, 2, 3, 4 and 8-9 first', after reading
anthropics/claude-code): (1) read-only calls of one reply run side by side, (2) big outputs saved whole with a path the
model can read / grep, (3) fallback models when the model is busy / down / gone, (4) compaction guards - compact and ask
again on 'prompt is too long', stop after 3 failed summaries, stop a round whose context refills right after each
summary, summarise a long idle session through its own cached request; (8) 11 more hook events, (9) prompt / agent /
http / mcp_tool hooks, onFailure, and the newer JSON fields."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _ses(EN, hooks=None, tid="t1"):
    ses = EN.Session(tid)
    (ses.repo / ".claude").mkdir(parents=True, exist_ok=True)
    (ses.repo / ".claude" / "settings.json").write_text(json.dumps({"hooks": hooks or {}}))
    ses.save_meta()
    return ses


# ---------------------------------------------------------------- 1. parallel reads
def test_read_only_calls_of_one_reply_run_side_by_side(ws, monkeypatch):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _ses(EN)
    (ses.repo / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"deny": ["Read(./secret.txt)"]}}))
    tl = EN.Tools(ses, False)
    tl.conf = RC.settings(ses.repo)
    live, peak, order = [0], [0], []
    lock = threading.Lock()

    def run(self, name, inp):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        time.sleep(0.2)
        with lock:
            live[0] -= 1
        order.append(inp.get("path") or inp.get("pattern"))
        return f"{name} ok"
    monkeypatch.setattr(EN.Tools, "run", run)
    uses = [{"id": "1", "name": "read", "input": {"path": "a.py"}}, {"id": "2", "name": "read", "input": {"path": "b.py"}},
            {"id": "3", "name": "grep", "input": {"pattern": "x"}}, {"id": "4", "name": "read", "input": {"path": "secret.txt"}},
            {"id": "5", "name": "edit", "input": {"path": "a.py"}}, {"id": "6", "name": "read", "input": {"path": "a.py"}}]
    t0 = time.time()
    got = EN.parallel_reads(tl, uses)
    assert set(got) == {"1", "2", "3"} and peak[0] == 3 and time.time() - t0 < 0.5     # side by side
    # the denied read and the read AFTER the edit are left to the loop, in order


# ---------------------------------------------------------------- 2. big outputs saved
def test_big_outputs_are_saved_and_readable(ws):
    EN = ws
    ses = _ses(EN)
    tl = EN.Tools(ses, False)
    big = "\n".join(f"line {i} " + ("x" * 50) + (" NEEDLE" if i == 2500 else "") for i in range(1, 5001))
    out = tl.spill(big, 50000)
    assert len(out) < 60000 and "The WHOLE output (5000 lines) is saved: read @out/o1.txt" in out
    assert "line 1 " in out and "line 5000 " in out
    assert "  2500\tline 2500" in tl.t_read("@out/o1.txt", offset=2500, limit=1)
    assert tl.t_grep("NEEDLE", path="@out/o1.txt").startswith("2500:line 2500")
    assert tl.spill("small") == "small"
    assert "No saved output" in tl.t_read("@out/o99.txt")
    assert "No file" in tl.t_read("@out/../../etc/passwd")          # only @out/oN.txt, nothing else


# ---------------------------------------------------------------- 3. fallback models
class _Err(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.status_code = code


def test_fallback_models(monkeypatch):
    from app.devsahayak import brain as B
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_fallback_models", "claude-sonnet-5-5,claude-opus-5-5,claude-haiku-5-5")
    B.GONE.clear()
    B.FALLBACK.note = None
    seen = []

    def once(st, model, *a, **k):
        seen.append(model)
        if model == "claude-opus-5-5":
            raise _Err("Overloaded", 529)
        return [{"type": "text", "text": "hi"}], "end_turn"
    monkeypatch.setattr(B, "_claude_once", once)
    monkeypatch.setattr(B, "model_for", lambda: "claude-opus-5-5")
    assert B._claude_call("s", [], [], 100, False)[0][0]["text"] == "hi" and seen == ["claude-opus-5-5", "claude-sonnet-5-5"]
    assert B.FALLBACK.note == ("claude-opus-5-5", "claude-sonnet-5-5", "overloaded")
    seen.clear()
    monkeypatch.setattr(B, "_claude_once", lambda st, model, *a, **k: (_ for _ in ()).throw(_Err("credit balance is too low", 400)))
    with pytest.raises(_Err):
        B._claude_call("s", [], [], 100, False)                    # a credit / bad-request error is not retried elsewhere

    def gone(st, model, *a, **k):
        if model == "claude-opus-5-5":
            raise _Err("model: claude-opus-5-5 not found", 404)
        return [{"type": "text", "text": "ok"}], "end_turn"
    monkeypatch.setattr(B, "_claude_once", gone)
    B._claude_call("s", [], [], 100, False)
    assert "claude-opus-5-5" in B.GONE and B.fallback_models("claude-sonnet-5-5") == ["claude-haiku-5-5"]
    assert B.too_long(_Err("prompt is too long: 210000 tokens > 200000 maximum", 400)) and not B.too_long(_Err("overloaded"))
    B.GONE.clear()


# ---------------------------------------------------------------- 4. compaction guards
def _round(EN, monkeypatch, brain, hooks=None, mode=""):
    from app.devsahayak import brain as B
    ses = _ses(EN, hooks)
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: {"bash": "exit code 1\nboom"}.get(name, "ok"))
    monkeypatch.setattr(B, "call", brain)
    evs = []
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="fix it", base="main", mode=mode, tenant_id="", conv="")
    try:
        out = EN._round(None, t, "tok", "", False, "", evs.append, None, None, "", None, "sha", "", "", ses)
    except Exception as e:  # noqa: BLE001 - what comes after done is not what these tests check
        out = e
    return evs, out


DONE = [{"type": "tool_use", "id": "d1", "name": "done", "input": {"explain": "done"}}]
BASH = [{"type": "tool_use", "id": "b1", "name": "bash", "input": {"command": "npm test"}}]


def test_too_long_compacts_and_asks_again(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B
    calls, comp = [], []
    monkeypatch.setattr(EN, "compact", lambda msgs, **k: comp.append(len(msgs)) or msgs)

    def brain(system, msgs, tools, **k):
        calls.append(1)
        if len(calls) == 1:
            raise _Err("prompt is too long: 1200000 tokens > 1000000 maximum", 400)
        return DONE, "tool_use"
    evs, _ = _round(EN, monkeypatch, brain)
    assert len(calls) >= 2 and comp and any("too long for the model" in str(e.get("text")) for e in evs)


def test_thrash_and_circuit_breaker(ws, monkeypatch):
    EN = ws
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_ws_compact_chars", 10, raising=False)
    monkeypatch.setattr(get_settings(), "dev_ws_clear_chars", 10 ** 9, raising=False)
    comp = []
    monkeypatch.setattr(EN, "compact", lambda msgs, **k: comp.append(1) or msgs)        # never gets smaller
    evs, out = _round(EN, monkeypatch, lambda *a, **k: (BASH, "tool_use"))
    assert len(comp) == 3 and any("fills up again right after every summary" in str(e.get("text")) for e in evs)
    assert EN.thrashing([1, 2, 3]) and not EN.thrashing([1, 4, 9]) and not EN.thrashing([1, 2])
    comp.clear()

    def bad(msgs, **k):
        comp.append(1)
        raise RuntimeError("summary refused")
    monkeypatch.setattr(EN, "compact", bad)
    n = [0]

    def brain(*a, **k):
        n[0] += 1
        return (DONE if n[0] > 6 else BASH), "tool_use"
    evs, _ = _round(EN, monkeypatch, brain)
    assert len(comp) == 3 and any("failed 3 times" in str(e.get("text")) for e in evs)   # then no more tries


def test_idle_compaction_reuses_the_sessions_own_request(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B
    ses = _ses(EN)
    msgs = [{"role": "user", "content": "please fix the cart"}]
    for i in range(10):
        msgs += [{"role": "assistant", "content": [{"type": "text", "text": f"step {i} " + "y" * 2000}]},
                 {"role": "user", "content": [{"type": "text", "text": f"result {i}"}]}]
    ses.save_messages(msgs)
    EN.save_prefix(ses, "THE SYSTEM PROMPT", [{"name": "read", "input_schema": {}}])
    sent = {}

    def call(system, m, tools, **k):
        sent.update(system=system, tools=tools, n=len(m), last=json.dumps(m[-1]))
        return [{"type": "text", "text": "SUMMARY of the cart work"}], "end_turn"
    monkeypatch.setattr(B, "call", call)
    assert EN.idle_compact("t1", min_chars=1000)
    assert sent["system"] == "THE SYSTEM PROMPT" and sent["tools"][0]["name"] == "read"      # the same request start
    assert sent["n"] == len(msgs) and "session is idle" in sent["last"]                       # her conversation + one line
    new = EN.Session("t1").messages()
    assert "SUMMARY of the cart work" in new[0]["content"] and "please fix the cart" in new[0]["content"] and len(new) < len(msgs)
    assert not EN.idle_compact("t1", min_chars=10 ** 9)                                       # small: nothing to do


# ---------------------------------------------------------------- 8 + 9. hooks
def test_hook_specs_types_and_new_events(ws):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _ses(EN, {
        "Stop": [{"hooks": [{"type": "prompt", "prompt": "Are all tasks done? $ARGUMENTS", "timeout": 20}]}],
        "SubagentStop": [{"hooks": [{"type": "agent", "prompt": "Check the agent's work"}]}],
        "PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "http", "url": "https://hooks.example.com/x", "headers": {"X-A": "1", "X-K": "${KEY}"}},
                                                      {"type": "http", "url": "http://plain.example.com"}]}],
        "PermissionRequest": [{"hooks": [{"type": "mcp_tool", "server": "guard", "tool": "check", "input": {"e": "${EVENT}"}}]}],
        "TaskCompleted": [{"hooks": [{"type": "command", "command": "make check", "onFailure": "block"}]}],
        "Weird": [{"hooks": [{"type": "command", "command": "x"}]}]})
    conf = RC.settings(ses.repo)
    for ev in ("Stop", "SubagentStop", "PostToolUse", "PermissionRequest", "TaskCompleted"):
        assert ev in conf["hooks"], ev
    assert "Weird" not in conf["hooks"]
    assert RC.hooks_for(conf, "Stop")[0] == {"type": "prompt", "prompt": "Are all tasks done? $ARGUMENTS", "model": "", "timeout": 20, "on_failure": ""}
    http = RC.hooks_for(conf, "PostToolUse", "edit")
    assert len(http) == 1 and http[0]["headers"] == {"X-A": "1"}                      # http:// dropped, ${secret} header never sent
    assert RC.hooks_for(conf, "TaskCompleted")[0]["on_failure"] == "block"
    assert len(RC.HOOK_EVENTS) == 22                     # v0.999 + WorktreeCreate / WorktreeRemove


def test_newer_answer_fields():
    from app.devsahayak.repoconf import hook_answer as A, judge_answer as J
    a = A("PermissionRequest", 0, json.dumps({"hookSpecificOutput": {"decision": {"behavior": "allow", "updatedInput": {"command": "ls"}}}}), "")
    assert a["decision"] == "allow" and a["updated"] == {"command": "ls"}
    assert A("PostToolUse", 0, json.dumps({"hookSpecificOutput": {"updatedToolOutput": "cleaned"}}), "")["output"] == "cleaned"
    assert A("PermissionDenied", 0, json.dumps({"hookSpecificOutput": {"retry": True}}), "")["retry"]
    assert A("UserPromptSubmit", 0, json.dumps({"hookSpecificOutput": {"sessionTitle": "Cart fix"}}), "")["title"] == "Cart fix"
    assert A("PreToolUse", 0, json.dumps({"hookSpecificOutput": {"permissionDecision": "defer"}}), "")["decision"] == ""
    assert A("SubagentStart", 0, json.dumps({"hookSpecificOutput": {"additionalContext": "use pytest"}}), "")["context"] == "use pytest"
    assert json.loads(J("Stop", 'Sure. {"ok": false, "reason": "tests are red"}')) == {"decision": "block", "reason": "tests are red"}
    assert json.loads(J("PreToolUse", '{"ok": false, "reason": "no"}'))["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert J("Stop", '{"ok": true}') == "{}" and J("Stop", "no json") == ""


def test_run_hooks_by_type(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B, repoconf as RC
    ses = _ses(EN, {
        "Stop": [{"hooks": [{"type": "prompt", "prompt": "Done? $ARGUMENTS"}]}],
        "PostToolUse": [{"hooks": [{"type": "http", "url": "https://hooks.example.com/x"}]}],
        "TaskCompleted": [{"hooks": [{"type": "command", "command": "make check", "onFailure": "block"}]}],
        "PermissionRequest": [{"hooks": [{"type": "mcp_tool", "server": "guard", "tool": "check"}]}]})
    tl = EN.Tools(ses, False)
    tl.conf, tl.net = RC.settings(ses.repo), {"hosts": []}
    seen = {}

    def call(system, msgs, tools, **k):
        seen["ask"] = msgs[0]["content"]
        return [{"type": "text", "text": '{"ok": false, "reason": "2 tests still fail"}'}], "end_turn"
    monkeypatch.setattr(B, "call", call)
    said = EN.run_hooks(tl, "Stop")
    assert said["block"] and said["text"] == "2 tests still fail" and '"hook_event_name": "Stop"' in seen["ask"]
    said = EN.run_hooks(tl, "PostToolUse", "edit", {"path": "a.py"}, "ok")       # host not allowed for this repo
    assert not said["block"] and "add hooks.example.com to this repo's network hosts" in said["message"]
    import httpx
    from app.agent import duniya_tools as DU
    monkeypatch.setattr(DU, "_guard_url", lambda u: u)
    posted = {}
    monkeypatch.setattr(httpx, "post", lambda url, content, **k: posted.update(url=url, body=content) or
                        SimpleNamespace(status_code=200, text=json.dumps({"hookSpecificOutput": {"updatedToolOutput": "trimmed"}})))
    tl.net = {"hosts": ["hooks.example.com"]}
    said = EN.run_hooks(tl, "PostToolUse", "edit", {"path": "a.py"}, "ok")
    assert said["output"] == "trimmed" and json.loads(posted["body"])["tool_input"]["file_path"] == "a.py"
    monkeypatch.setattr(tl, "_image", lambda: ("", "no box"))
    said = EN.run_hooks(tl, "TaskCompleted", extra={"task_subject": "x"})
    assert said["block"] and "could not run" in said["text"]                      # onFailure: block
    said = EN.run_hooks(tl, "PermissionRequest", "bash", {"command": "ls"})
    assert said["decision"] == "" and "allow the server guard" in said["message"]


def test_the_loop_follows_the_new_events(ws, monkeypatch):
    EN = ws
    from app.devsahayak import brain as B
    calls = []

    def fake_hooks(tools, event, tool="", inp=None, out="", prompt="", emit=None, extra=None):
        calls.append((event, tool, extra))
        base = {"block": False, "text": "", "decision": "", "reason": "", "updated": None, "context": "", "stop": False,
                "stop_reason": "", "message": "", "output": None, "retry": False, "title": ""}
        if event == "PermissionRequest":
            base["decision"] = "allow"
        if event == "PostToolUseFailure":
            base["context"] = "the test DB was not started"
        if event == "PostToolBatch":
            base["context"] = "batch note"
        return base
    monkeypatch.setattr(EN, "run_hooks", fake_hooks)
    seen = []
    steps = iter([BASH + [{"type": "tool_use", "id": "b2", "name": "read", "input": {"path": "a.py"}}], DONE])

    def brain(system, msgs, tools, **k):
        seen.append(json.dumps(msgs[-1]["content"]))
        return next(steps), "tool_use"
    evs, _ = _round(EN, monkeypatch, brain, hooks={k: [{"hooks": [{"type": "command", "command": "x"}]}] for k in
                                                   ("PermissionRequest", "PostToolUseFailure", "PostToolBatch", "PostToolUse")}, mode="steps")
    names = [c[0] for c in calls]
    assert "PermissionRequest" in names and not any(e.get("k") == "perm" for e in evs)     # the hook answered for her
    assert ("PostToolUseFailure", "bash") in [(c[0], c[1]) for c in calls]                 # exit 1 = a failed step
    assert ("PostToolUse", "read") in [(c[0], c[1]) for c in calls]
    assert "the test DB was not started" in seen[1] and "batch note" in seen[1]
    batch = next(c for c in calls if c[0] == "PostToolBatch")[2]["tool_calls"]
    assert [x["tool_name"] for x in batch] == ["Bash", "Read"]


def test_tasks_titles_and_subagents(ws, monkeypatch, tmp_path):
    EN = ws
    from app.devsahayak import repoconf as RC, subagent as SA
    ses = _ses(EN, {"TaskCompleted": [{"hooks": [{"type": "command", "command": "x"}]}],
                    "TaskCreated": [{"hooks": [{"type": "command", "command": "x"}]}],
                    "SubagentStart": [{"hooks": [{"type": "command", "command": "x"}]}]})
    tl = EN.Tools(ses, False)
    tl.conf = RC.settings(ses.repo)
    fired = []

    def fake(tools, event, tool="", inp=None, out="", prompt="", emit=None, extra=None):
        fired.append((event, (extra or {}).get("task_subject") or (extra or {}).get("agent_type")))
        return {"block": event in ("TaskCompleted", "SubagentStart"), "text": "tests still red", "stop": False, "context": ""}
    monkeypatch.setattr(EN, "run_hooks", fake)
    tl.t_todo_write([{"content": "Fix cart", "status": "pending"}])
    out = tl.t_todo_write([{"content": "Fix cart", "status": "completed"}])
    assert ("TaskCreated", "Fix cart") in fired and ("TaskCompleted", "Fix cart") in fired
    assert "NOT complete" in out and EN.Session("t1").meta["todos"][0]["status"] == "in_progress"
    rep = SA._run_one(tl, {"name": "db-expert", "title": "Db expert", "tools": "read", "prompt": "x"}, "Look at the schema please now", None,
                      None, None, None, "", "")
    assert "did not start" in rep and "tests still red" in rep
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "case 'fallback'" in js and "case 'title': return ''" in js
    d = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "case 'fallback':" in d and "case 'title':" in d
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert 'ev.get("k") == "title"' in svc and "_idle_compact(at)" in svc


from tests.test_tech_devsahayak import T, dev  # noqa: F401,E402


def test_the_tick_picks_only_long_sessions_idle_just_under_the_cache(dev, ws, monkeypatch):  # noqa: F811
    S, EN = dev, ws
    import os
    from app.devsahayak import brain as B
    from app.devsahayak.models import DevTask
    from app.db import session
    monkeypatch.setattr(B, "brain_name", lambda: "claude")
    ids = {}
    with session() as s:
        for name in ("idle", "fresh", "small"):
            t = DevTask(tenant_id=T, number="D-09" + name[:2], kind="fix", repo="o/r", text="x", base="main", status="explained")
            s.add(t)
            s.flush()
            ids[name] = t.id
    for name, tid in ids.items():
        ses = EN.Session(tid)
        ses.dir.mkdir(parents=True, exist_ok=True)
        ses.save_messages([{"role": "user", "content": "z" * (900000 if name != "small" else 100)}])
        age = 260 if name != "fresh" else 30
        os.utime(ses.msg_path, (time.time() - age, time.time() - age))
    done = []
    monkeypatch.setattr(EN, "idle_compact", lambda tid, min_chars=0: done.append(tid) or True)
    started = S._idle_compact()
    for _ in range(50):
        if done:
            break
        time.sleep(0.05)
    assert started == [ids["idle"]] and done == [ids["idle"]]
    assert S._idle_compact() == []                                  # once per idle spell
    assert any(st.get("k") == "compact" and "Summarised while idle" in st.get("text", "") for st in S.task_view(EN_task(ids["idle"]), full=True)["steps"])


def EN_task(tid):
    from app.db import session
    from app.devsahayak.models import DevTask
    with session() as s:
        t = s.get(DevTask, tid)
        s.expunge(t)
        return t
