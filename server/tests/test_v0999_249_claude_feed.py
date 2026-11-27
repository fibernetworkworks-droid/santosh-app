"""v0.999 THE CLAUDE CODE FEED (owner: "GO DEEP IN CLAUDE CODE REPLY WHEN CODE IS DEVELOPING ... A PERFECT BACKEND WORK
WHILE SHOWING THE PROPER FEED TO USER ... SAME AS CLAUDE CODE WORKS 100 %"): what Hoola Code shows while it works, held
by tests - the real change with line numbers (read before and after, not guessed from the edit), searches counted as
matches in files, a finished command said in the past ("Ran the unit tests"), a running command's lines live on her
screen, the step's own clock, Claude's words streamed as they are written, the to-do list shown once and updated in
place, "Thought for Ns", Esc to stop, and the reply rules Claude Code follows."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401
from tests.test_v0768_hoola_code_shell import TASKS, _console, _shot

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- the server side
def test_the_real_change_has_line_numbers_and_true_counts():
    from app.devsahayak import engine as E
    old = "a\nb\nc\nd\ne\nf\ng\nh\n"
    new = "a\nb\nC\nd\ne\nf\ng\nh\ni\n"
    rows, add, rem = E.real_hunk(old, new)
    assert (add, rem) == (2, 1)
    assert ["-", 3, None, "c"] in rows and ["+", None, 3, "C"] in rows and ["+", None, 9, "i"] in rows
    assert [" ", 2, 2, "b"] in rows and ["@", None, None, ""] in rows        # two parts, a gap between them
    big = "\n".join(str(i) for i in range(500))
    rows, add, rem = E.real_hunk("", big)
    assert add == 500 and len(rows) == E.HUNK_ROWS + 1 and rows[-1][0] == "…"   # counts are whole, rows are capped


class _Ses:
    def __init__(self, repo):
        self.repo = repo


class _Tools:
    def __init__(self, repo):
        self.s = _Ses(repo)
        self.before = None
        self.todos = []

    def _rel(self, p):
        return str(p).lstrip("./")


def test_an_edit_step_carries_the_file_before_and_after(tmp_path):
    from app.devsahayak import engine as E
    f = tmp_path / "app.py"
    f.write_text("def total(x):\n    return sum(x)\n\nprint(total([1]))\n")
    tl = _Tools(tmp_path)
    inp = {"path": "app.py", "old_string": "return sum(x)", "new_string": "return sum(x or [])"}
    tl.before = E._snap(tl, "edit", inp)
    f.write_text("def total(x):\n    return sum(x or [])\n\nprint(total([1]))\n")
    ev = E.event(tl, "edit", inp, "Edited app.py (+1 -1).")[0]
    assert ev["k"] == "edit" and (ev["added"], ev["removed"]) == (1, 1)
    assert ["-", 2, None, "    return sum(x)"] in ev["hunk"] and ["+", None, 2, "    return sum(x or [])"] in ev["hunk"]
    assert [" ", 1, 1, "def total(x):"] in ev["hunk"]                      # the lines around it, like Claude Code
    assert ev["diff"] == ["-     return sum(x)", "+     return sum(x or [])"]   # the old short list stays for old phones
    tl.before = E._snap(tl, "write", {"path": "new.py"})                   # a new file: everything is added
    (tmp_path / "new.py").write_text("x = 1\ny = 2\n")
    ev = E.event(tl, "write", {"path": "new.py", "content": "x = 1\ny = 2\n"}, "Created new.py (2 lines).")[0]
    assert ev["k"] == "new" and ev["added"] == 2 and ev["hunk"][0] == ["+", None, 1, "x = 1"]
    tl.before = E._snap(tl, "edit", inp)
    ev = E.event(tl, "edit", inp, "Not applied: old_string was not found.")[0]
    assert ev["k"] == "refused"                                             # a change that did not land shows no diff


def test_searches_are_counted_like_claude_code():
    from app.devsahayak import engine as E
    assert E.grep_counts("a.py\nb.py\n... 3 more", "files") == (5, 5)
    assert E.grep_counts("a.py:3:total\na.py:9:total\nb.py:1:total", "content") == (3, 2)
    assert E.grep_counts("a.py:4\nb.py:0\nc.py:2", "count") == (6, 2)
    assert E.grep_counts("No matches.", "files") == (0, 0)
    ev = E.event(_Tools(Path(".")), "grep", {"pattern": "total", "mode": "content"}, "a.py:3:total\nb.py:1:total")[0]
    assert ev == {"k": "search", "q": "total", "n": 2, "files": 2}
    ev = E.event(_Tools(Path(".")), "glob", {"pattern": "**/*.py"}, "a.py\nb.py\n... 10 more")[0]
    assert ev["glob"] is True and ev["n"] == 12


def test_a_finished_command_is_said_in_the_past():
    from app.devsahayak import engine as E
    assert E.did_words("Run the unit tests") == "Ran the unit tests"
    assert E.did_words("Install the packages") == "Installed the packages"
    assert E.did_words("Pytest on the cart") == "Ran: pytest on the cart"
    tl = _Tools(Path("."))
    tl.last_bash = {"cmd": "pytest -q", "rc": 0, "secs": 3.1, "timed_out": False, "tail": ["3 passed"]}
    ev = E.event(tl, "bash", {"command": "pytest -q", "description": "Run the unit tests"}, "exit code 0\n3 passed")[0]
    assert ev["desc"] == "Run the unit tests" and ev["did"] == "Ran the unit tests" and ev["cmd"] == "pytest -q"


def test_a_running_command_prints_live_and_the_step_has_a_clock():
    from app.devlab import box
    got = []
    rc, txt, secs = box._run_stream([sys.executable, "-c", "print('one'); print('two', flush=True)"], 20, got.append)
    assert rc == 0 and got == ["one", "two"] and "two" in txt
    rc, txt, _ = box._run_stream([sys.executable, "-c", "import time; print('x', flush=True); time.sleep(5)"], 1, lambda _l: None)
    assert rc == 124 and "timed out" in txt
    from app.devsahayak import engine as E
    from app.devsahayak import service as S
    E.NOW_STEP["tq1"] = "Running the unit tests"
    E.NOW_TOOL["tq1"] = "bash"
    E.LIVE_OUT["tq1"] = ["collecting", "3 passed"]
    S._RUNNING.add("tq1")
    try:
        st = S.live_state("tq1")
        assert st["now"] == "Running the unit tests" and st["out"] == ["collecting", "3 passed"] and st["tool"] == "bash"
        assert st["t0"] > 0
        d = S.live_delta({**st, "out": ["collecting"]}, st)
        assert d == {"out": ["collecting", "3 passed"]}
    finally:
        E.NOW_STEP.pop("tq1", None)
        S._RUNNING.discard("tq1")
    assert "tq1" not in E.LIVE_OUT and "tq1" not in E.NOW_AT                 # the step ended: its clock and lines go


def test_a_command_s_live_lines_never_carry_a_secret():
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    at = src.index("def on_line(line: str)")
    body = src[at:src.index("r = box.run_in(img", at)]
    assert "[secret hidden]" in body and "scrub(line)" in body and "hoola-lab-proxy" in body


def test_claude_s_words_stream_as_they_are_written(monkeypatch):
    from app.devsahayak import brain as B

    class _Msg:
        content = []
        stop_reason = "end_turn"
        usage = None

    class _Stream:
        text_stream = ["The crash ", "comes from ", "**total()**."]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            m = _Msg()
            m.content = [{"type": "text", "text": "The crash comes from **total()**."}]
            return m

    class _Msgs:
        def __init__(self):
            self.kw = None

        def stream(self, **kw):
            self.kw = kw
            return _Stream()

        def create(self, **kw):
            raise AssertionError("a call with a live screen streams")

    class _C:
        messages = _Msgs()

    monkeypatch.setattr(B, "_client", lambda: _C)
    monkeypatch.setattr(B, "model_for", lambda *a, **k: "claude-test")
    seen = []
    B.TEXT_SINK.fn = seen.append
    try:
        blocks, stop = B._claude_call("sys", [{"role": "user", "content": "hi"}], [], 500, False)
    finally:
        B.TEXT_SINK.fn = None
    assert seen[0] == "" and seen[-1] == "The crash comes from **total()**." and len(seen) == 4
    assert blocks == [{"type": "text", "text": "The crash comes from **total()**."}] and stop == "end_turn"


def test_the_reply_rules_are_claude_code_s():
    from app.devsahayak import engine as E
    s = E.SYSTEM
    assert "Before your first tool call, say in one sentence" in s
    assert "lead with the result" in s and "`path/to/file.py:42`" in s
    assert "say that FIRST" in s and "Never say done, fixed or passing unless you\n  saw it pass in this session" in s


def test_the_page_draws_the_feed_like_claude_code():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    for k in ("case 'look':", "case 'made':", "case 'server':", "case 'gap':"):
        assert k in js                                                     # steps the server made that the page never drew
    assert "/stream`" in js and "getReader()" in js and "Esc to stop" in js
    assert "Updated the to-do list" in js and "Thought" in js and "hunkHTML" in js
    css = (ROOT / "server/app/static/console/hoolacode.css").read_text()
    assert ".hcd-diff.num span{display:grid" in css and ".hcd-out{" in css


# ---------------------------------------------------------------- the page, in a real browser
STEPS = [{"k": "say", "text": "I will **find the crash** first.", "at": "2026-11-10T10:00:02+00:00", "n": 0},
         {"k": "todo", "items": [{"content": "Find the crash", "status": "in_progress"}, {"content": "Fix it", "status": "pending"}],
          "at": "2026-11-10T10:00:03+00:00", "n": 1},
         {"k": "search", "q": "total(", "n": 7, "files": 3, "at": "2026-11-10T10:00:05+00:00"},
         {"k": "list", "path": "**/*.py", "glob": True, "n": 12, "at": "2026-11-10T10:00:06+00:00"},
         {"k": "think", "text": "The empty cart hits sum(None).", "secs": 4, "at": "2026-11-10T10:00:10+00:00"},
         {"k": "edit", "path": "app/cart.py", "added": 1, "removed": 1, "diff": ["- return sum(x)", "+ return sum(x or [])"],
          "hunk": [[" ", 11, 11, "def total(x):"], ["-", 12, None, "    return sum(x)"], ["+", None, 12, "    return sum(x or [])"],
                   [" ", 13, 13, ""]], "at": "2026-11-10T10:00:20+00:00"},
         {"k": "bash", "cmd": "pytest -q tests/test_cart.py", "desc": "Run the cart tests", "did": "Ran the cart tests", "rc": 0,
          "seconds": 3.4, "tail": ["4 passed in 3.2s"], "at": "2026-11-10T10:00:30+00:00"},
         {"k": "todo", "items": [{"content": "Find the crash", "status": "completed"}, {"content": "Fix it", "status": "in_progress"}],
          "at": "2026-11-10T10:00:31+00:00"},
         {"k": "look", "path": "web/cart.html", "shots": ["a.png", "b.png"], "errors": 0, "at": "2026-11-10T10:00:40+00:00"}]


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_the_feed_in_a_real_browser(arena_server):  # noqa: F811
    ctx, pg, errs, calls, state = _console(arena_server)
    srv = 1_800_000_000.0
    task = {**TASKS[0], "text": "Empty cart crashes", "steps": STEPS, "notes": [], "log": [], "diff": "", "found": {},
            "last_n": 8, "now": "Running the whole test suite", "srv_now": srv,
            "now_info": {"tool": "bash", "t0": srv - 7, "out": []}}
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=task))
    ev = [{"id": 0, "kind": "code_open", "payload": {"live": "", "now": "Running the whole test suite", "n": 8, "running": True,
                                                     "out": [], "t0": srv - 7, "tool": "bash", "srv": srv}},
          {"id": 0, "kind": "code_live", "payload": {"out": ["collected 41 items", "tests/test_cart.py ....", "tests/test_api.py ......"]}}]
    body = "".join(f"data: {json.dumps(e)}\n\n" for e in ev)
    pg.route("**/api/devsahayak/tasks/dt1/stream", lambda r: r.fulfill(status=200, headers={"Content-Type": "text/event-stream"}, body=body))
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector("#hcdCol .hcd-fold")
    feed = pg.locator("#hcdCol")
    text = feed.text_content()
    assert "7 matches in 3 files" in text and "Found 12 files" in text and "Ran the cart tests" in text
    assert "Updated the to-do list · 0 of 2 done" in text                 # the older list is one line, the newest is drawn
    assert pg.locator("#hcdCol .hcd-todo").count() == 1 and "Fix it" in pg.locator("#hcdCol .hcd-todo").text_content()
    assert "Thought for 4s" in text and "Opened web/cart.html in a browser · 2 screenshots" in text
    assert "The empty cart hits" not in pg.locator("#hcdCol .hcd-fin:visible").all_text_contents().__str__()   # thinking stays folded
    # the change opens by itself (it is small), with old and new line numbers
    diff = pg.locator("#hcdCol .hcd-diff.num")
    assert diff.count() == 1 and diff.is_visible()
    assert diff.locator("span.del b").first.text_content() == "12" and "sum(x or [])" in diff.locator("span.add").text_content()
    # the running row: the step, its own clock, Esc to stop, and the command's live lines under it
    pg.wait_for_function("() => document.querySelector('#hcdCol .hcd-out') && document.querySelector('#hcdCol .hcd-out').textContent.includes('test_api')", timeout=8000)
    lab = pg.locator("#hcdCol .hck-work").text_content()
    assert "Running the whole test suite" in lab and "Esc to stop" in lab and "7s" in lab
    _shot(pg, "claude-feed")
    stops = []
    pg.route("**/api/devsahayak/tasks/dt1/stop", lambda r: (stops.append(1), r.fulfill(json={"ok": True})))
    pg.locator("#hcdCol").click(position={"x": 5, "y": 5})
    pg.keyboard.press("Escape")
    pg.wait_for_function("() => true")
    pg.wait_for_timeout(600)
    assert stops == [1]                                                   # Esc stops, like Claude Code
    assert not errs, errs
    ctx.close()


def test_the_phone_says_it_the_same_way():
    words = (ROOT / "lib/ui/code/code_words.dart").read_text()
    sess = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "sans: true" not in words                                       # the reply font = the web page's (Literata, her Chat font)
    assert "s['did']" in words and "class CodeHunk" in words and "CodeHunk(rows: hunk)" in words
    assert "String codeMatches(" in words and "matches')} in ${codeCount(f, 'file')}" in words
    assert "_liveOut(t)" in sess and "next['now_info'] = ni" in sess and "cs(s['did'])" in sess
    assert "'Found ${codeCount(s['n'], 'file')} · '" in sess
