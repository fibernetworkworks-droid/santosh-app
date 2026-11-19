"""v0.531 PRAYOGSHALA step 2 - the lab wired into the coding loop (owner: "GO STEP 2").

Step 1 (v0.456) built the sealed Docker box and nothing called it, which by this repo's own rule means it did not work
yet. This is the caller: `devsahayak/lab.py` + two loop tools (`run_check`, `grep_log`), the bug proof measured
locally in seconds instead of a pushed red CI commit, the plan's done_when lines RUN instead of assumed, and the
lab's evidence handed to the own review and written into the PR. Everything stays behind `dev_lab`, which is off
until `lab_check` passes on her VPS."""
import json

import pytest

from app.devlab import service as LS
from app.devlab import spec as SP
from app.devsahayak import lab as LAB
from tests.test_tech_devsahayak import CALC, REPO, T, _join, dev  # noqa: F401
from tests.test_v0350_kadam_ba_kadam import Script, tu

FIXED = CALC.replace("    return s / len(items)\n", "    return s\n")
TEST_NEW = "from app.calc import total\n\n\ndef test_empty():\n    assert total([]) == 0\n"


class FakeLab:
    """The Lab's surface, with the answers scripted. The real box is proved by `python -m app.devlab check`."""

    def __init__(self, usable=True, results=None, proof=None, done=None):
        self.usable, self.cmd, self.source = usable, "python3 -m pytest -q", "AGENTS.md"
        self.results = list(results or [])
        self._proof, self._done = proof, done
        self.seen, self.greps, self.closed = [], [], False

    def run(self, overlay=None, only="", label=""):
        self.seen.append({"overlay": dict(overlay or {}), "only": only, "label": label})
        return self.results.pop(0) if self.results else {
            "stage": "check", "ok": True, "cmd": self.cmd, "seconds": 1.2, "shown": "2 passed", "log": "/tmp/a.log",
            "say": "`python3 -m pytest -q` PASS (1.2s).", "cut": 0}

    def grep(self, pattern):
        self.greps.append(pattern)
        return f"E   assert total([]) == 0   <- {pattern}"

    def proof(self, changes, tests):
        self.seen.append({"proof": [c["path"] for c in changes], "tests": list(tests)})
        return dict(self._proof) if self._proof else {}

    def done_when(self, lines, overlay, cap=2):
        self.seen.append({"done_when": list(lines)})
        return list(self._done or [])

    def close(self):
        self.closed = True


def _loop(monkeypatch, S, lab, turns):
    """Drive the real edit loop with a scripted model and this lab; returns (script, out)."""
    from app.db import session
    from app.devsahayak import loop as L
    from app.devsahayak.models import DevTask
    with session() as s_:
        t = DevTask(tenant_id=T, number="D-0001", kind="fix", repo=REPO, text="Khaali cart par crash", base="main")
        s_.add(t)
        s_.flush()
        s_.expunge(t)
    script = Script(turns)
    monkeypatch.setattr(L, "BRAIN", script)
    _base, _read, _ctx, out = L.run(S.gh(T), t, "", [], lab=lab)
    return script, out


# ---------------------------------------------------------------- the switch, and the shut lab
def test_the_switch_and_the_box_are_two_separate_doors(monkeypatch):
    """v0.533: the switch is ON now (her VPS answered lab_check with every wall holding), so `ready()` speaks about
    the BOX. With the switch off it speaks about the switch. A shut lab always says which door is closed."""
    from app.config import get_settings
    assert get_settings().dev_lab is True
    monkeypatch.setattr(get_settings(), "dev_lab", False, raising=False)
    off = LAB.ready(T)
    assert off["ok"] is False and "dev_lab off" in off["why"] and "lab_check" in off["why"]
    monkeypatch.setattr(get_settings(), "dev_lab", True, raising=False)
    from app.devlab import box
    monkeypatch.setattr(box, "docker", lambda: "")
    on = LAB.ready(T)
    assert on["ok"] is False and "docker is not on this machine" in on["why"]      # the honest reason, not the switch


def test_a_shut_lab_gives_the_loop_no_tools_and_changes_nothing(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    script, out = _loop(monkeypatch, S, None, [[tu(1, "read_file", path="app/calc.py")],
                                               [tu(2, "done", explain="dekh liya")]])
    assert "run_check" not in {x["name"] for x in script.tools}
    assert "HER CHECK IS RUNNABLE" not in script.system and out["checks"] == []


def test_for_task_never_raises_and_says_why(monkeypatch):
    monkeypatch.setattr(LAB, "ready", lambda tenant="": {"ok": True, "why": ""})
    monkeypatch.setattr(LAB.Lab, "__init__", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("docker gaya")))
    assert LAB.for_task(T, type("T", (), {"number": "D-1", "repo": REPO, "base": "main", "id": "x"})(), "") is None


# ---------------------------------------------------------------- the two tools
def test_the_tools_appear_and_the_duty_is_stated(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    lab = FakeLab()
    script, out = _loop(monkeypatch, S, lab, [[tu(1, "run_check", why="pehle fail dekhna hai")],
                                              [tu(2, "done", explain="ho gaya")]])
    assert {"run_check", "grep_log"} <= {x["name"] for x in script.tools}
    assert "HER CHECK IS RUNNABLE" in script.system and "python3 -m pytest -q" in script.system
    assert "it proves nothing" in script.system and "do NOT invent a result" in script.system
    assert out["checks"] and out["checks"][0]["ok"] is True
    assert out["checks"][0]["why"] == "pehle fail dekhna hai"            # what it expected is kept with the run


def test_a_check_runs_on_the_edits_not_on_the_base(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    lab = FakeLab()
    _loop(monkeypatch, S, lab, [[tu(1, "read_file", path="app/calc.py")],
                                [tu(2, "edit_file", path="app/calc.py", old="return s / len(items)", new="return s")],
                                [tu(3, "new_file", path="tests/test_empty.py", content=TEST_NEW)],
                                [tu(4, "run_check", only="tests/test_empty.py")],
                                [tu(5, "done", explain="ho gaya")]])
    run = [x for x in lab.seen if "overlay" in x][-1]
    assert run["only"] == "tests/test_empty.py"
    assert "return s\n" in run["overlay"]["app/calc.py"] and "/ len(items)" not in run["overlay"]["app/calc.py"]
    assert run["overlay"]["tests/test_empty.py"] == TEST_NEW             # a brand-new file is in the box too


def test_a_failing_check_comes_back_with_its_end_and_the_log_hint(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    lab = FakeLab(results=[{"stage": "check", "ok": False, "cmd": "python3 -m pytest -q", "seconds": 3.1, "cut": 9000,
                            "shown": "…\nE   assert 10.0 == 20\nFAILED tests/test_calc.py::test_total",
                            "say": "`python3 -m pytest -q` FAIL - exit code 1 (3.1s).", "log": "/tmp/r.log"}])
    script, out = _loop(monkeypatch, S, lab, [[tu(1, "run_check")], [tu(2, "grep_log", pattern="assert")],
                                              [tu(3, "done", explain="x", risk="y")]])
    said = [str(b.get("content")) for c in script.seen if isinstance(c, list) for b in c if isinstance(b, dict)]
    first = next(x for x in said if "FAIL" in x)
    assert "FAILED tests/test_calc.py::test_total" in first and "grep_log to search it" in first
    assert any("assert total([]) == 0" in x for x in said) and lab.greps == ["assert"]
    assert out["checks"][0]["ok"] is False


def test_a_setup_failure_tells_it_to_stop_not_to_retry(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    lab = FakeLab(results=[{"stage": "setup", "why": "the setup command did not finish", "out": "pip: no such package"}])
    script, _ = _loop(monkeypatch, S, lab, [[tu(1, "run_check")], [tu(2, "done", explain="x", risk="lab nahi chala")]])
    said = [str(b.get("content")) for c in script.seen if isinstance(c, list) for b in c if isinstance(b, dict)]
    msg = next(x for x in said if "dependencies" in x)
    assert "Do not retry" in msg and "Say this in risk" in msg and "pip: no such package" in msg


def test_the_check_cap_and_grep_before_any_check(monkeypatch):
    lab = LAB.Lab.__new__(LAB.Lab)                       # no clone, no docker: only the guards are under test
    lab.ws, lab.runs, lab.last, lab.why = {"ok": True, "cmd": "pytest", "source": "AGENTS.md"}, LAB.MAX_RUNS, {}, ""
    lab.LS = LS
    assert lab.run({})["stage"] == "cap"
    lab.ws["last_log"] = ""
    assert "Run run_check first" in lab.grep("x")


# ---------------------------------------------------------------- the local proof replaces a CI round
def _record_patches(S, monkeypatch):
    """The plain fake answers a PATCH on a PR without applying it; record the bodies so the PR note can be checked."""
    import httpx
    from app.devsahayak import gh as G
    inner = G._TRANSPORT.handler
    S.FAKE.pr_patch = []

    def handler(req):
        if req.method == "PATCH" and "/pulls/" in req.url.path:
            import json as _j
            body = _j.loads(req.content)
            S.FAKE.pr_patch.append(body)
            S.FAKE.prs[1].update(body)
            return httpx.Response(200, json=S.FAKE.prs[1])
        return inner(req)
    G.set_transport(httpx.MockTransport(handler))


def _armed(S, monkeypatch, proof=None, done=None):
    _record_patches(S, monkeypatch)
    lab = FakeLab(proof=proof, done=done)
    monkeypatch.setattr(LAB, "for_task", lambda *a, **k: lab)
    monkeypatch.setattr(S, "explore_review", lambda *a, **k: {"summary": "ok", "verdict": "comment", "comments": []})
    return lab


def test_the_local_proof_replaces_the_pushed_red_commit(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)
    from tests.test_tech_devsahayak import FIX_ANSWER
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    lab = _armed(S, monkeypatch, proof={"state": "proven_local", "cmd": "python3 -m pytest -q", "source": "AGENTS.md",
                                        "red": {"ok": False, "seconds": 2.0}, "green": {"ok": True, "seconds": 2.4}})
    v = S.start(T, "fix", "Khaali cart par ZeroDivisionError")
    t = S.get_task(T, v["number"])
    assert t["proof"]["state"] == "proven_local" and t["proof"]["local"] is True
    assert "Proven in the lab" in v["say"] and lab.closed is True
    commits = [c for c in S.FAKE.commits.values() if "by Hoola" in str(c.get("message"))]
    assert len(commits) == 1                              # ONE clean commit: no deliberate red commit on her branch
    assert any("Proven in the lab" in (p.get("body") or "") for p in S.FAKE.pr_patch)
    assert any("Checked in the lab" in (p.get("body") or "") for p in S.FAKE.pr_patch)


def test_a_test_that_passes_without_the_fix_is_said_plainly(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)
    from tests.test_tech_devsahayak import FIX_ANSWER
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    _armed(S, monkeypatch, proof={"state": "not_proven_local", "cmd": "python3 -m pytest -q", "source": "CI",
                                  "red": {"ok": True, "seconds": 1.0}, "green": {"ok": True, "seconds": 1.1}})
    v = S.start(T, "fix", "Khaali cart par ZeroDivisionError")
    assert "does not prove the bug" in v["say"]
    assert "NOT proven" in S._lab_note(S.get_task(T, v["number"])["proof"])


def test_done_when_lines_are_run_and_their_verdicts_reported(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)
    from tests.test_tech_devsahayak import FIX_ANSWER
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    lab = _armed(S, monkeypatch, proof={"state": "checked_local", "cmd": "pytest", "source": "AGENTS.md",
                                        "green": {"ok": True, "seconds": 2.0}},
                 done=[{"line": "python3 -m pytest -q", "verdict": "VERIFIED", "seconds": 2.0},
                       {"line": "total([]) == 0", "verdict": "not performed", "why": "yeh command nahi hai"}])
    v = S.start(T, "fix", "Khaali cart par crash")
    with __import__("app.db", fromlist=["session"]).session() as s_:
        from app.devsahayak.models import DevTask
        row = s_.get(DevTask, v["id"])
        row.plan = json.dumps({"done_when": ["python3 -m pytest -q", "total([]) == 0"], "goal": "g", "steps": ["s"]})
        s_.flush()
    t = S.get_task(T, v["number"])
    note = S._lab_note({**t["proof"], "done_when": lab._done})
    assert "[x] `python3 -m pytest -q` - VERIFIED" in note and "[ ] `total([]) == 0` - not performed" in note


def test_the_own_review_is_shown_what_was_measured(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    seen = {}
    monkeypatch.setattr(S, "explore_review", lambda g, repo, head, pr_text, *a, **k: seen.update(pr=pr_text) or
                        {"summary": "ok", "verdict": "comment", "comments": []})
    from app.db import session
    from app.devsahayak.models import DevTask
    with session() as s_:
        t = DevTask(tenant_id=T, number="D-0009", kind="fix", repo=REPO, base="main", text="x", pr_number=1,
                    status="ci_running", pr_body="body", head_sha="abc",
                    changes=json.dumps([{"path": "app/calc.py", "new": FIXED, "old_sha": "s"}]),
                    proof=json.dumps({"state": "check_failed_local", "local": True, "cmd": "pytest",
                                      "source": "AGENTS.md", "green": {"ok": False, "seconds": 3.0}}))
        s_.add(t)
        s_.flush()
        s_.expunge(t)
    S.FAKE.prs[1] = {"number": 1, "files": [{"filename": "app/calc.py", "status": "modified", "additions": 1,
                                             "patch": "@@ -1,2 +1,2 @@\n-    return s / len(items)\n+    return s\n"}],
                     "state": "open", "draft": True, "head": {"sha": "abc"}, "user": {"login": "hoola"}, "body": "b"}
    S._ready_or_self_review(T, t, S.gh(T), "ready")
    assert "lab_evidence" in seen["pr"] and "Her check fails" in seen["pr"] and "MEASURED, not claimed" in seen["pr"]


# ---------------------------------------------------------------- the devlab side of step 2
def test_an_overlay_may_not_escape_the_checkout(tmp_path):
    ov = LS.write_overlay(str(tmp_path), {"app/x.py": "1", "../../etc/passwd": "x", "/etc/shadow": "x",
                                          ".git/config": "x", "a/../../b": "x"})
    assert ov["wrote"] == ["app/x.py"] and len(ov["refused"]) == 4
    assert (tmp_path / "app" / "x.py").read_text() == "1"
    assert LS.safe_rel("ok/path.py") == "ok/path.py" and LS.safe_rel("") == "" and LS.safe_rel("x" * 500) == ""


def test_one_file_narrowing_is_honest():
    assert SP.one_file("python3 -m pytest -q", "python", "tests/t.py") == "python3 -m pytest -q tests/t.py"
    assert SP.one_file("npm test --silent", "node", "a.test.js") == "npm test --silent -- a.test.js"
    assert SP.one_file("make check", "python", "tests/t.py") == ""        # cannot be narrowed: the caller says so
    assert SP.one_file("pytest", "python", "../../etc/passwd") == ""


def test_a_workspace_is_cloned_once_and_the_snapshot_built_on_the_first_check(monkeypatch, tmp_path):
    from app.devlab import box
    calls = {"materialize": 0, "snapshot": 0, "run": 0}
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "AGENTS.md").write_text("## Commands\n- Test: python3 -m pytest -q\n")
    monkeypatch.setattr(box, "available", lambda: {"ok": True, "docker": "27", "base_built": True})
    monkeypatch.setattr(LS, "materialize", lambda *a, **k: calls.__setitem__("materialize", calls["materialize"] + 1)
                        or {"ok": True, "dir": str(tmp_path), "paths": ["pyproject.toml", "AGENTS.md"], "mb": 1})
    monkeypatch.setattr(LS, "snapshot", lambda *a, **k: calls.__setitem__("snapshot", calls["snapshot"] + 1)
                        or {"ok": True, "image": "img:1", "cached": False, "seconds": 9.0})
    monkeypatch.setattr(box, "run_in", lambda *a, **k: calls.__setitem__("run", calls["run"] + 1)
                        or {"rc": 0, "out": "2 passed", "secs": 1.0, "timed_out": False})
    ws = LS.open_workspace("a/b", "main", "tok", {"ok": "1"})
    assert ws["ok"] and ws["cmd"] == "python3 -m pytest -q" and calls["snapshot"] == 0   # nothing built yet
    r1 = LS.run_on(ws, overlay={"app/calc.py": "x = 1\n"})
    r2 = LS.run_on(ws)
    assert r1["ok"] and r2["ok"] and calls == {"materialize": 1, "snapshot": 1, "run": 2}  # one clone, one snapshot
    assert r1["files_written"] == 1 and ws["runs"] == 2 and ws["last_log"]
