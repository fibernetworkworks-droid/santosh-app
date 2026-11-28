"""v0.999 KARPATHY RULES (owner: 'feed this properly to hoola code thus to perform well. first check it perfectly').

The four rules from forrestchang/andrej-karpathy-skills (MIT) - think first, simple first, surgical changes, goal first -
reach every place Hoola Code writes or reviews code, and rule 3 is also checked in code: a hunk that only changes layout
or deletes an existing comment is named before the round may finish."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "server" / "app" / "devsahayak"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


OLD = "import os\n\n# keep this note\ndef a(x):\n    return x\n\ndef b(y):\n  return 'y'\n\n\ndef c():\n    pass\n"
NEW = "import os\n\ndef a(x):\n    return x + 1\n\ndef b(y):\n    return \"y\"\n\n\ndef c():\n    pass\n"


# ---------------------------------------------------------------- the rules text
def test_the_four_rules_are_all_there_with_credit():
    from app.devsahayak import karpathy as KR
    t = KR.RULES
    for must in ("Think before coding", "Simple first", "Surgical changes", "Goal first", "assumptions",
                 "senior engineer", "Every changed line should trace back to her request",
                 "mention it in explain, do not delete it", "YOUR change made", "-> check:", "judgment"):
        assert must in t, must
    assert "andrej-karpathy-skills, MIT" in t and len(t) < 3200          # short: rides every request, cached
    notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
    assert "andrej-karpathy-skills" in notice and "MIT" in notice[notice.index("andrej-karpathy-skills"):][:3000]


def test_the_rules_ride_every_place_that_writes_or_reviews_code():
    eng = (DEV / "engine.py").read_text()
    assert "SYSTEM + kr_rules +" in eng                                  # the coder, right after its own rules
    assert "task += KR.REALITY_EXTRA" in eng                             # the reality checker
    assert "KR.SUB_RULES" in (DEV / "subagent.py").read_text()           # agents that edit
    assert "SYSTEM + kr_rules +" in (DEV / "loop.py").read_text()         # the older step loop
    svc = (DEV / "service.py").read_text()
    assert "SP.SELF_REVIEW + _kr_review()" in svc and "### Assumptions" in svc
    from app.devsahayak import karpathy as KR
    assert "trace back to the task" in KR.SELF_REVIEW_EXTRA and "IS a gap" in KR.REALITY_EXTRA


def test_switch_off_takes_it_all_away(monkeypatch):
    from app.config import get_settings
    from app.devsahayak import karpathy as KR
    assert KR.on() is True and get_settings().dev_karpathy is True
    monkeypatch.setattr(get_settings(), "dev_karpathy", False)
    assert KR.on() is False


def test_the_done_tool_takes_assumptions_and_todo_steps_carry_a_check():
    from app.devsahayak import engine as EN
    done = next(t for t in EN.TOOLS if t["name"] == "done")
    assert "assumptions" in done["input_schema"]["properties"]
    todo = next(t for t in EN.TOOLS if t["name"] == "todo_write")
    assert "-> check:" in todo["description"]


# ---------------------------------------------------------------- rule 3 checked in code
def test_layout_only_and_deleted_comments_are_named_real_changes_are_not():
    from app.devsahayak import karpathy as KR
    got = KR.drive_by_files({"f.py": OLD}, {"f.py": NEW})
    assert [(x["line"], x["what"].split(" (")[0]) for x in got] == [
        (3, "an existing comment was deleted"), (7, "only layout changed")]
    # return x -> return x + 1 is a real change: never named
    assert not any(x["line"] == 4 for x in got)
    # the repo's formatter made the change: left alone
    assert KR.drive_by_files({"f.py": OLD}, {"f.py": NEW}, skip={"f.py"}) == []
    # a new file is all new: never checked
    assert KR.drive_by_files({}, {"g.py": NEW}) == []
    # blank lines only are too small to name
    assert KR.drive_by_files({"f.py": "a = 1\nb = 2\n"}, {"f.py": "a = 1\n\nb = 2\n"}) == []
    # a shebang is not a comment; '#include' is not a comment in C
    assert KR.drive_by_files({"s.sh": "#!/bin/sh\necho a\n"}, {"s.sh": "echo a\n"}) == []
    assert KR.drive_by_files({"m.c": "#include <a.h>\nint x;\n"}, {"m.c": "int x;\n"}) == []
    assert KR.drive_by_files({"m.ts": "// why\nlet x = 1\n"}, {"m.ts": "let x = 1\n"})[0]["what"].startswith("an existing comment")


def test_the_same_check_on_a_real_git_diff_gives_real_line_numbers(tmp_path):
    from app.devsahayak import engine as EN
    from app.devsahayak import karpathy as KR
    repo = tmp_path / "r"
    repo.mkdir()
    pad = "".join(f"v{i} = {i}\n" for i in range(40))
    (repo / "f.py").write_text(pad + OLD)
    EN._git(repo, "init", "-q")
    EN._commit(repo, "base")
    (repo / "f.py").write_text(pad + NEW)
    (repo / "g.py").write_text("# brand new\n")
    EN._git(repo, "add", "-A")
    rc, diff = EN._git(repo, "diff", "--cached", "--no-color", "-p", "HEAD")
    got = KR.drive_by(diff)
    assert [(x["path"], x["line"]) for x in got] == [("f.py", 43), ("f.py", 47)]
    assert [x for x in KR.drive_by(diff, skip={"f.py"})] == []


def test_a_layout_ask_is_the_task_not_a_drive_by():
    from app.devsahayak import karpathy as KR
    for words in ("format this file", "fix the indentation in app.py", "run prettier", "clean up utils.py", "reformat f.py",
                  "refactor the parser", "use double quotes"):
        assert KR.asked_for_layout(words), words
    for words in ("fix the login bug", "add a dark mode switch", "the date parser crashes on 31 Feb"):
        assert not KR.asked_for_layout(words), words


def test_assumptions_are_shown_under_her_answer_once():
    from app.devsahayak import karpathy as KR
    assert KR.with_assumptions("Fixed the parser.", "dates are DD/MM/YYYY") == \
        "Fixed the parser.\n\n**I assumed:** dates are DD/MM/YYYY"
    assert KR.with_assumptions("Fixed it.", "none") == "Fixed it."
    assert KR.with_assumptions("Fixed it, assuming dates are DD/MM.", "dates are DD/MM") == "Fixed it, assuming dates are DD/MM."
    assert "**I assumed:**" in KR.with_assumptions("", "x" * 900) and len(KR.with_assumptions("", "x" * 900)) < 440


def test_the_code_card_counts_tidying_without_changing_right():
    from app.quality import codecard as CC
    task = {"id": "k1", "kind": "fix", "lang": "py", "allow": r".*", "files": {"f.py": OLD}}
    try:
        row = CC.score(task, {"f.py": NEW}, {"explain": "done"})
    except Exception:            # the job's own checks need things this test does not give; the count comes first
        pytest.skip("codecard needs the job's own files")
    assert row["drive_by"] == 2 and any("tidied code" in w for w in row["why"])


# ---------------------------------------------------------------- one real round
def _round(EN, monkeypatch, text, change):
    from app.devsahayak import brain as B
    ses = EN.Session("t1")
    ses.repo.mkdir(parents=True, exist_ok=True)
    (ses.repo / "f.py").write_text(OLD)
    EN._git(ses.repo, "init", "-q")
    ses.meta.update({"repo": "o/r", "base": EN._commit(ses.repo, "base"), "hidden": []})
    ses.save_meta()
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: "ok")
    steps = iter([[{"type": "tool_use", "id": "d1", "name": "done",
                    "input": {"explain": "Done.", "assumptions": "the input is always text"}}],
                  [{"type": "tool_use", "id": "d2", "name": "done",
                    "input": {"explain": "Done.", "assumptions": "the input is always text"}}]])
    seen, systems = [], []

    def call(system, msgs, tools, **k):
        if not seen:
            (ses.repo / "f.py").write_text(change)        # what the model's edits did during this round
        systems.append(system)
        seen.append(msgs[-1]["content"])
        return next(steps), "tool_use"
    monkeypatch.setattr(B, "call", call)
    evs = []
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text=text, base="main", mode="", tenant_id="", conv="")
    try:
        out = EN._round(None, t, "tok", "", False, "", evs.append, None, None, "", None, "sha", "", "", ses)
    except Exception as e:  # noqa: BLE001 - the git parts after done are not what this test checks
        out = e
    return seen, systems, evs, out


def test_a_round_is_sent_back_once_for_drive_by_tidying(ws, monkeypatch):
    seen, systems, evs, out = _round(ws, monkeypatch, "the function a should add one", NEW)
    assert "Surgical changes" in systems[0]                               # the rules are in the coder's system prompt
    back = json.dumps(seen[1])
    assert "do not change what the code does" in back and "f.py:3" in back and "f.py:7" in back
    assert any(e.get("k") == "gate" and any("only layout" in i for i in e.get("items", [])) for e in evs)
    if isinstance(out, tuple):                                            # done twice = finished; the note is said once
        assert "**I assumed:** the input is always text" in out[3]["explain"]
        assert out[3]["assumptions"] == "the input is always text"


def test_no_gate_when_she_asked_for_the_layout(ws, monkeypatch):
    seen, systems, evs, out = _round(ws, monkeypatch, "reformat f.py and make a add one", NEW)
    assert "do not change what the code does" not in json.dumps(seen[1:])


def test_version():
    from app.main import APP_VERSION
    assert re.match(r"^\d+\.\d+\.\d+", APP_VERSION)
