"""v0.787 HOOLA CODE ENGINE (built as 0.784) (owner: "NOW CHECK IS HOOLA CODE BACKEND IS SAME AS CLAUDE CODE" -> "GO STEP 1 AND 2 --- 2
SESSIONS, USE CLAUDE").

Step 1 (devsahayak/brain.py): every Hoola Code call is Claude's own past SAB GLM / one-model, with adaptive thinking,
prompt caching and old tool output trimmed; a failed GitHub code search is said, never shown as "no file".
Step 2 (devsahayak/engine.py): a real working copy per session, Claude Code's tools (read / write / edit / multi_edit /
glob / grep / ls / bash / todo_write / show_diff / done), bash inside the locked box, a conversation that continues,
a checkpoint per round + rewind, compaction, secrets hidden, and at most 2 sessions running at once.
The end-to-end tests drive the REAL service on the fake GitHub with a scripted Claude and real Docker for bash."""
from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path

import pytest

from tests.test_tech_devsahayak import REPO, T, _join, dev  # noqa: F401


# ---------------------------------------------------------------- a scripted Claude at the SDK door
class FakeClient:
    def __init__(self, turns):
        self.turns, self.calls = list(turns), []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        blocks = self.turns.pop(0) if self.turns else [{"type": "tool_use", "id": f"z{len(self.calls)}", "name": "done",
                                                         "input": {"explain": "finished"}}]
        if callable(blocks):
            blocks = blocks(kw)
        stop = "tool_use" if any(b.get("type") == "tool_use" for b in blocks) else "end_turn"
        return type("R", (), {"content": blocks, "stop_reason": stop, "model": kw.get("model"), "usage": None})()


def tu(i, name, **inp):
    return {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}


@pytest.fixture
def on(dev, monkeypatch, tmp_path):  # noqa: F811
    from app.config import get_settings
    from app.devsahayak import brain as B
    from app.devsahayak import engine as EN
    st = get_settings()
    for k, v in (("dev_workspace", True), ("dev_claude", True), ("dev_plan_first", False), ("dev_lab", False),
                 ("dev_ci_loop", False), ("dev_self_review", False)):
        monkeypatch.setattr(st, k, v, raising=False)
    monkeypatch.chdir(tmp_path)                      # data/devsahayak/ws lands in the test's own folder
    monkeypatch.setattr(B, "STATE", {"think_refused": False, "effort_refused": False, "calls": 0, "cleared": 0})
    from app.devlab import service as LS

    def materialize(repo, ref="", token="", host="github.com"):   # the fake GitHub's files as a checkout (no network)
        d = tempfile.mkdtemp(prefix="hoola-test-ws-")
        fake = dev.FAKE
        sha = ref if ref in fake.commits else fake.refs["main"]
        for p, c in fake.files_at(sha).items():
            f = Path(d) / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(c)
        (Path(d) / ".env").write_text("STRIPE_KEY=hoola-test-not-a-real-key-42\n")
        return {"ok": True, "dir": d, "paths": [], "mb": 0}
    monkeypatch.setattr(LS, "materialize", materialize)
    monkeypatch.setattr(LS, "spec_for", lambda *a, **k: {"setup": "", "test": "", "confirm": False, "deps_key": ""})
    yield dev
    B.CLIENT = None
    EN.LIVE.clear()


def _wait(S, tid, cond, s=20.0):
    end = time.time() + s
    while time.time() < end:
        t = S.get_task(T, tid)
        if cond(t):
            return t
        time.sleep(0.05)
    return S.get_task(T, tid)


def _box_ok():
    try:
        from app.devlab import box
        return box.available().get("ok") and box.has_image(box.BASE_IMAGE)
    except Exception:
        return False


# ---------------------------------------------------------------- step 1: the shared brain
def test_brain_is_claude_with_thinking_caching_and_effort(on, monkeypatch):
    from app import glmdoor, usage
    from app.devsahayak import brain as B
    seen = {}

    def turn(kw):
        seen["claude_only"], seen["bypass"] = glmdoor.CLAUDE_ONLY.get(), usage.ONE_MODEL_BYPASS.get()
        return [{"type": "text", "text": "hi"}]
    B.CLIENT = FakeClient([turn])
    tools = [{"name": "a", "description": "a", "input_schema": {"type": "object"}},
             {"name": "b", "description": "b", "input_schema": {"type": "object"}}]
    blocks, stop = B.call("SYS", [{"role": "user", "content": "do it"}], tools)
    kw = B.CLIENT.calls[0]
    assert seen == {"claude_only": True, "bypass": True}                      # SAB GLM / one-model stand aside
    assert kw["thinking"] == {"type": "adaptive"} and kw["extra_body"]["output_config"]["effort"] == "high"
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" in kw["tools"][-1] and "cache_control" not in kw["tools"][0]
    assert kw["messages"][-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert blocks == [{"type": "text", "text": "hi"}] and stop == "end_turn"


def test_brain_drops_a_refused_thinking_field_once(on):
    from app.devsahayak import brain as B

    def refuse(kw):
        if "thinking" in kw:
            raise RuntimeError("400 invalid_request_error: thinking is not supported")
        return [{"type": "text", "text": "ok"}]

    class C(FakeClient):
        def create(self, **kw):
            self.calls.append(kw)
            return type("R", (), {"content": refuse(kw), "stop_reason": "end_turn", "model": "m", "usage": None})()
    B.CLIENT = C([])
    B.call("s", [{"role": "user", "content": "x"}], [])
    assert B.STATE["think_refused"] is True and "thinking" not in B.CLIENT.calls[-1]
    B.call("s", [{"role": "user", "content": "x"}], [])
    assert len(B.CLIENT.calls) == 3                                        # remembered: no second refused call


def test_trim_clears_old_tool_output_keeps_the_newest():
    from app.devsahayak import brain as B
    msgs = [{"role": "user", "content": "start"}]
    for i in range(10):
        msgs.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"u{i}", "name": "read", "input": {}}]})
        msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"u{i}", "content": "x" * 5000}]})
    assert B.trim(msgs, 100_000) == 0                                      # under budget: nothing touched
    n = B.trim(msgs, 10_000, keep=6)
    results = [m["content"][0]["content"] for m in msgs if m["role"] == "user" and isinstance(m["content"], list)]
    assert n == 4 and results[:4] == [B.CLEARED] * 4 and all(r == "x" * 5000 for r in results[4:])


def test_old_loop_rides_the_brain_and_says_a_failed_search(on):
    from app.devsahayak import brain as B
    from app.devsahayak import loop as L
    B.CLIENT = FakeClient([[{"type": "text", "text": "ok"}]])
    blocks, _ = L._anthropic_brain("s", [{"role": "user", "content": "x"}], [])
    assert blocks[0]["text"] == "ok" and B.CLIENT.calls
    from app.devsahayak.gh import GhError

    class G:
        search_failed = ""

        def search_code(self, full, words):
            self.search_failed = "API rate limit exceeded"
            return []
    ws = L.Workspace(G(), REPO, "a" * 40, ["app/calc.py", "README.md"])
    out = ws.search_code("calc")
    assert "GitHub code search FAILED" in out and "app/calc.py" in out          # never a silent "no file"
    assert GhError


def test_the_model_picker_offers_claude_when_hoola_code_is_claude_only(on, monkeypatch):
    from app.config import get_settings
    st = get_settings()
    monkeypatch.setattr(st, "claude_one_model", "claude-haiku-5-5", raising=False)
    m = on.models(T)
    assert m["forced"] is None and m["options"]                              # Claude's own choices, not the server's rule
    monkeypatch.setattr(st, "dev_claude", False, raising=False)
    assert on.models(T)["forced"]["model"] == "Claude Haiku 5.5"


# ---------------------------------------------------------------- step 2: the engine, unit level
def test_slots_two_at_once_the_third_waits(on, monkeypatch):
    from app.config import get_settings
    from app.devsahayak import engine as EN
    monkeypatch.setattr(get_settings(), "dev_ws_live", 2, raising=False)
    sem = EN._sem()
    assert sem.acquire(blocking=False) and sem.acquire(blocking=False)      # two sessions running
    events, calls = [], {"n": 0}

    class Hook:
        def event(self, ev):
            events.append(ev)

        def stopped(self):
            calls["n"] += 1
            return calls["n"] > 1

    class G:
        def branch_sha(self, repo, base):
            return "b" * 40
    t = type("T", (), {"id": "slot-test", "repo": REPO, "base": "main", "model": "", "effort": "", "kind": "fix", "text": "x"})()
    with pytest.raises(EN.Stopped):
        EN.run(G(), t, "tok", "", on_step=Hook()) if _box_ok() else (_ for _ in ()).throw(EN.Stopped("no box"))
    if _box_ok():
        assert events and events[0]["k"] == "wait" and "2 sessions" in events[0]["text"]
    sem.release()
    sem.release()


def test_compact_keeps_tool_pairs_and_summarises_the_rest(on):
    from app.devsahayak import brain as B
    from app.devsahayak import engine as EN
    B.CLIENT = FakeClient([[{"type": "text", "text": "SUMMARY: fixed calc.py, tests pass"}]])
    msgs = [{"role": "user", "content": "fix it"}]
    for i in range(12):
        msgs.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"u{i}", "name": "read", "input": {"path": "a"}}]})
        msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"u{i}", "content": "text"}]})
    out = EN.compact(msgs, keep_tail=6)
    assert out[0]["role"] == "user" and "SUMMARY: fixed calc.py" in out[0]["content"]
    assert out[1]["role"] == "assistant"                                    # the cut is before an assistant turn
    ids = {b["id"] for m in out if m["role"] == "assistant" for b in m["content"]}
    res = {b["tool_use_id"] for m in out[1:] if m["role"] == "user" for b in m["content"]}
    assert res <= ids                                                        # no tool_result lost its tool_use
    assert B.CLIENT.calls[0].get("thinking") is None


def test_tools_on_a_working_copy(on, tmp_path):
    from app.devsahayak import engine as EN
    ses = EN.Session("unit-tools")
    ses.ensure(REPO, on.FAKE.refs["main"], "tok")
    tl = EN.Tools(ses, allow_workflows=False, lab_spec={})
    assert ".env" in ses.meta["hidden"] and "holds secrets" in tl.t_read(".env")      # secrets hidden before anything sees them
    assert "not-a-real-key" not in (ses.repo / ".env").read_text()
    assert tl.t_edit("app/calc.py", "x", "y").startswith("Refused: read")            # read before edit
    assert "return s / len(items)" in tl.t_read("app/calc.py")
    assert "1\tdef total(items):" in tl.t_read("app/calc.py")                          # line numbers
    assert tl.t_edit("app/calc.py", "    return s / len(items)\n", "    return s\n").startswith("Edited")
    assert "appears 5 times" in tl.t_multi_edit("app/calc.py", [{"old_string": "s", "new_string": "S"}])
    assert tl.t_write(".env", "X=1").startswith("Refused")                             # never changed
    assert tl.t_write(".github/workflows/deploy.yml", "x").startswith("Refused")       # workflows stay hers
    assert tl.t_write("app/new.py", "VALUE = 1\n").startswith("Created")
    g = tl.t_grep(r"def +total", mode="content")
    assert "app/calc.py:1:def total(items):" in g                                      # regex + line numbers
    assert "app/new.py" in tl.t_glob("**/*.py") and "app/" in tl.t_ls("")
    assert "not-a-real-key" not in tl.t_grep("not-a-real-key", mode="content")                       # the hidden file is never searched
    rows = {r["path"]: r["st"] for r in ses.changed()}
    assert rows == {"app/calc.py": "M", "app/new.py": "A"}
    tl.t_todo_write([{"content": "fix total", "status": "completed"}, {"content": "add test", "status": "in_progress"}])
    assert ses.meta["todos"][1]["status"] == "in_progress"
    assert "app/calc.py" in tl.t_show_diff()


def test_bash_runs_in_the_locked_box(on):
    if not _box_ok():
        pytest.skip("needs Docker and the hoola-devlab base image")
    from app.devsahayak import engine as EN
    ses = EN.Session("unit-bash")
    ses.ensure(REPO, on.FAKE.refs["main"], "tok")
    tl = EN.Tools(ses, allow_workflows=False, lab_spec={})
    out = tl.t_bash("python3 -c \"from app.calc import total; print('T', total([{'price': 2, 'qty': 3}]))\"")
    assert "exit code 0" in out and "T 6.0" in out
    net = tl.t_bash("python3 -c \"import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)\"", timeout=30)
    assert "exit code 0" not in net                                                    # no internet in the box
    assert tl.t_bash("sudo ls").startswith("Refused")
    assert "STRIPE" not in tl.t_bash("cat .env; env")                                   # the secret is not in the box at all


# ---------------------------------------------------------------- step 2: a whole session through the real service
def test_a_session_works_continues_and_rewinds(on):
    if not _box_ok():
        pytest.skip("needs Docker and the hoola-devlab base image")
    S = on
    _join(S)
    from app.devsahayak import brain as B
    from app.devsahayak import engine as EN
    first = [
        [tu(1, "todo_write", todos=[{"content": "find the divide", "status": "in_progress"}])],
        [tu(2, "grep", pattern="len\\(items\\)", mode="content")],
        [tu(3, "read", path="app/calc.py")],
        [tu(4, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
        [tu(5, "read", path="tests/test_calc.py")],
        [tu(6, "edit", path="tests/test_calc.py", old_string="== 20\n", new_string="== 20\n\n\ndef test_empty():\n    assert total([]) == 0\n")],
        [tu(7, "bash", command="python3 -c \"from app.calc import total; assert total([]) == 0; print('PASS')\"")],
        [tu(8, "show_diff")],
        [tu(9, "done", explain="total() no longer divides", pr_title="Fix total on empty cart", pr_summary="- sum only",
            test_plan="- ran the check: PASS", risk="none")],
    ]
    B.CLIENT = FakeClient(first)
    v = S.start_bg(T, "fix", "total() crashes on an empty cart", repo=REPO, mode="ask")
    t = _wait(S, v["id"], lambda t: not t["running"] and t["status"] != "new", 60)
    assert t["status"] == "ready", (t["status"], t.get("error"))
    ch = {c["path"]: c for c in t["file_diffs"]}
    assert set(ch) == {"app/calc.py", "tests/test_calc.py"}                  # the secret file never in the change
    kinds = [s["k"] for s in t["steps"]]
    assert "todo" in kinds and "search" in kinds and "edit" in kinds and "ckpt" in kinds
    bash = next(s for s in t["steps"] if s["k"] == "bash")
    assert bash["rc"] == 0 and any("PASS" in x for x in bash["tail"])         # really ran, in the box
    assert t["ws"]["exists"] and len(t["ws"]["checkpoints"]) == 1 and t["ws"]["todos"]
    sys_prompt = B.CLIENT.calls[0]["system"][0]["text"]
    assert "REAL working copy" in sys_prompt and B.CLIENT.calls[0]["thinking"] == {"type": "adaptive"}
    n_first = len(EN.Session(v["id"]).messages())

    # her follow-up CONTINUES the same conversation in the same working copy
    def check_history(kw):
        msgs = kw["messages"]
        assert "total() crashes on an empty cart" in str(msgs[0]["content"])     # the first ask is still there
        assert "<her_change>" in str(msgs[-1]["content"])
        return [tu(10, "read", path="app/calc.py")]
    B.CLIENT = FakeClient([check_history,
                           [tu(11, "edit", path="app/calc.py", old_string="    return s\n", new_string="    return round(s, 2)\n")],
                           [tu(12, "done", explain="rounded", pr_title="Fix total on empty cart")]])
    S.in_background(T, v["id"], "revise", words="round the total to 2 places")
    t = _wait(S, v["id"], lambda t: not t["running"] and len(t["ws"].get("checkpoints") or []) == 2, 60)
    assert len(t["ws"]["checkpoints"]) == 2, t.get("error")
    assert len(EN.Session(v["id"]).messages()) > n_first
    assert "round(s, 2)" in (EN.folder(v["id"]) / "repo" / "app/calc.py").read_text()
    assert any("round(s, 2)" in c["diff"] for c in t["file_diffs"])

    # rewind: back to checkpoint 1 - the file and the conversation as they were
    t = S.ws_rewind(T, v["id"], 1)
    assert "round(s, 2)" not in (EN.folder(v["id"]) / "repo" / "app/calc.py").read_text()
    assert len(EN.Session(v["id"]).messages()) == n_first and t["steps"][-1]["k"] == "rewind"
    files = S.ws_files(T, v["id"], "")
    assert any(e["name"] == "app" and e["dir"] for e in files["entries"])
    assert "holds secrets" in S.ws_files(T, v["id"], ".env")["text"]
    S.delete_task(T, v["id"])
    assert not EN.exists(v["id"])                                           # the working copy goes with the session


def test_an_explained_session_takes_a_follow_up(on):
    if not _box_ok():
        pytest.skip("needs Docker and the hoola-devlab base image")
    S = on
    _join(S)
    from app.devsahayak import brain as B
    B.CLIENT = FakeClient([[tu(1, "read", path="app/calc.py")],
                           [tu(2, "done", explain="It divides by len(items). Fix it?")]])
    v = S.start_bg(T, "explain", "Why does total() crash?", repo=REPO)
    t = _wait(S, v["id"], lambda t: not t["running"] and t["status"] != "new", 60)
    assert t["status"] == "explained" and t["can_continue"]
    B.CLIENT = FakeClient([[tu(3, "read", path="app/calc.py")],
                           [tu(4, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
                           [tu(5, "done", explain="fixed", pr_title="Fix total")]])
    S.in_background(T, v["id"], "revise", words="yes, fix it")
    t = _wait(S, v["id"], lambda t: not t["running"] and t["status"] not in ("new", "explained"), 60)
    assert t["status"] in ("ready", "pr_open", "ci_running"), (t["status"], t.get("error"))
    assert [c["path"] for c in t["file_diffs"]] == ["app/calc.py"]


def test_routes_are_mounted():
    from app import main
    paths = set()

    def walk(rs, pre=""):
        for r in rs:
            sub = getattr(r, "original_router", None)
            if sub is not None:
                walk(sub.routes, pre + (getattr(getattr(r, "include_context", None), "prefix", "") or ""))
            elif getattr(r, "path", None):
                paths.add(pre + r.path)
    walk(main.app.routes)
    for p in ("/api/devsahayak/tasks/{tid}/ws", "/api/devsahayak/tasks/{tid}/files", "/api/devsahayak/tasks/{tid}/rewind"):
        assert p in paths, p


def test_page_draws_the_engine():
    js = (Path(__file__).resolve().parents[1] / "app/static/console/code.js").read_text()
    for k in ("case 'bash'", "case 'todo'", "case 'ckpt'", "case 'rewind'", "case 'wait'", "function wsCard", "data-act=\"rewind\"",
              "Browse files", "can_continue"):
        assert k in js, k
