"""v0.402 ECC SPECIALISTS (owner: "GO ECC PHASE 1"): the right expert at each moment of a coding job, adapted from ECC's
MIT-licensed agents - a CI fix round gets the fixer for the failure's language, a PR review gets the reviewer discipline +
the language reviewer + focused passes on big / sensitive / untested PRs - each behind its own switch (off until the
review card and the fix card show they help). The review card measures old vs new on 12 fixed practice PRs."""
from pathlib import Path

from app.devsahayak import specialists as SP
from app.quality import review_tasks as RT
from app.quality import reviewcard as RC
from tests.test_v0350_kadam_ba_kadam import tu

ROOT = Path(__file__).resolve().parents[2]


def test_languages_from_files_and_logs():
    assert SP.lang_of(["app/a.py", "app/b.py", "web/x.ts"]) == "python"
    assert SP.lang_of(["lib/x.dart"]) == "dart" and SP.lang_of(["README.md"]) == ""
    assert SP.lang_of_log("Traceback (most recent call last):\n  File \"app/x.py\", line 3") == "python"
    assert SP.lang_of_log("src/a.ts(4,2): error TS2322: Type 'string' is not assignable") == "js"
    assert SP.lang_of_log("e: file:///w/src/Money.kt:3:5 Unresolved reference: gst") == "kotlin"
    assert SP.lang_of_log("lib/money.dart:3:7: Error: The getter 'x' isn't defined") == "dart"
    assert SP.lang_of_log("something failed", ["src/Main.java"]) == "java"


def test_the_reviewer_and_fixer_texts():
    a = SP.review_addendum(["app/orders.py"])
    assert "Can I cite the exact added line" in a and "ZERO COMMENTS IS A VALID REVIEW" in a and "PYTHON REVIEWER" in a
    assert "MUTABLE DEFAULT" in a and SP.CREDIT in a
    assert "FLUTTER / DART REVIEWER" in SP.review_addendum(["lib/a.dart"])
    f = SP.fix_addendum("e: Money.kt:3 Unresolved reference: pct", ["src/Money.kt"])
    assert "CI FIX SPECIALIST" in f and "NEVER make CI green by weakening it" in f and "KOTLIN fixes" in f


def test_which_prs_earn_focused_passes():
    assert SP.focus_passes(["README.md"], "+ docs", 3) == []                                    # docs only
    assert SP.focus_passes(["app/x.py", "tests/test_x.py"], "+ return a + b", 4) == []           # small, tested, plain
    assert SP.focus_passes(["app/x.py", "tests/test_x.py"], "+ token = req['token']", 4) == ["security"]
    assert SP.focus_passes(["app/x.py"], "+ return a + b", 4) == ["tests"]                       # no test in the PR
    assert SP.focus_passes(["app/x.py", "tests/test_x.py"], "+ x", 200) == ["security", "silent", "tests"]


def test_comments_from_several_passes_merge():
    m = SP.merge_comments([[{"path": "a.py", "line": 10, "body": "short", "severity": "medium"}],
                           [{"path": "a.py", "line": 11, "body": "a much longer and better reason", "severity": "high"},
                            {"path": "b.py", "line": 10, "body": "other", "severity": "low"}]])
    assert len(m) == 2 and m[0]["severity"] == "high" and m[0]["body"].startswith("a much longer")


class Brain:
    """A scripted reviewer: records every system prompt; comments on the planted line when told where it is."""

    def __init__(self, spot=None, verdict="comment"):
        self.systems, self.spot, self.verdict = [], spot, verdict

    def __call__(self, system, messages, tools):
        self.systems.append(system)
        n = len(self.systems)
        if self.spot:
            return [tu(n, "comment", path=self.spot[0], line=self.spot[1], severity="high",
                       body="This line breaks: input X gives Y because Z."),
                    tu(n + 100, "done", summary="One real problem.", verdict="request_changes")], "tool_use"
        return [tu(n, "done", summary="Clean change.", verdict=self.verdict)], "tool_use"


def _pr(pid):
    return next(p for p in RT.PRS if p["id"] == pid)


def test_explore_review_old_and_new(monkeypatch):
    from app.config import get_settings
    from app.devsahayak import loop as L
    from app.devsahayak import service as S
    from app.quality.codecard import MemGh
    pr = _pr("sql_injection")
    head, parts, added = RC.pr_inputs(pr)
    b = Brain(spot=(pr["bug"]["path"], RC.spot_line(pr)))
    monkeypatch.setattr(L, "BRAIN", b)
    monkeypatch.setattr(get_settings(), "dev_spec_review", False, raising=False)
    old = S.explore_review(MemGh(head), "r", "h", "<pr></pr>", parts, added)
    assert len(b.systems) == 1 and "REVIEW DISCIPLINE" not in b.systems[0]               # old = one plain pass
    b.systems.clear()
    monkeypatch.setattr(get_settings(), "dev_spec_review", True, raising=False)
    new = S.explore_review(MemGh(head), "r", "h", "<pr></pr>", parts, added)
    assert "REVIEW DISCIPLINE" in b.systems[0] and "PYTHON REVIEWER" in b.systems[0]
    assert any("FOCUSED PASS - SECURITY" in s for s in b.systems[1:])                     # sql -> security pass
    assert any("FOCUSED PASS - TESTS" in s for s in b.systems[1:])                         # no test file in this PR
    assert len(new["comments"]) == 1 and new["loop"]["passes"][0] == "main" and len(new["loop"]["passes"]) >= 3
    assert old["verdict"] == new["verdict"] == "request_changes"


def test_the_review_card_marks(monkeypatch):
    for pr in RT.PRS:                                       # every planted problem sits on a line the PR ADDED
        head, parts, added = RC.pr_inputs(pr)
        if pr["bug"]:
            assert RC.spot_line(pr) in added[pr["bug"]["path"]], pr["id"]
    bug, clean = _pr("delivery_off_by_one"), _pr("clean_refactor")
    line = RC.spot_line(bug)
    hit = {"verdict": "request_changes", "comments": [{"path": bug["bug"]["path"], "line": line, "severity": "high", "body": "x"}]}
    assert RC.score(bug, hit)["right"]
    near_miss = {"verdict": "request_changes", "comments": [{"path": bug["bug"]["path"], "line": line + 9, "severity": "high", "body": "x"}]}
    r = RC.score(bug, near_miss)
    assert not r["caught"] and r["false_alarms"] == 1
    assert not RC.score(bug, {"verdict": "comment", "comments": hit["comments"]})["right"]     # caught, wrong verdict
    assert RC.score(clean, {"verdict": "comment", "comments": [{"path": "a", "line": 1, "severity": "low", "body": "nit"}]})["right"]
    r = RC.score(clean, {"verdict": "comment", "comments": [{"path": "a", "line": 1, "severity": "medium", "body": "x"}]})
    assert not r["right"] and r["false_alarms"] == 1
    hoola = {"verdict": "comment", "comments": [{"path": "a", "line": 1, "severity": "high", "body": "[Hoola check] secret"}]}
    assert RC.score(clean, hoola)["quiet"]                                                    # automatic checks are not the model


def test_the_review_card_runs_both_modes(monkeypatch):
    from app.devsahayak import loop as L
    from app.quality import toolchoice

    class Smart(Brain):
        def __call__(self, system, messages, tools):
            first = messages[0]["content"]
            pr = next(p for p in RT.PRS if p["title"] in first)
            if pr["bug"] and "REVIEW DISCIPLINE" in system:        # only the NEW reviewer finds it
                self.spot = (pr["bug"]["path"], RC.spot_line(pr))
            else:
                self.spot = None
            return super().__call__(system, messages, tools)
    monkeypatch.setattr(L, "BRAIN", Smart())
    cd = RC.card(only=["delivery_off_by_one", "clean_refactor"], parallel=1)
    old, new = cd["modes"]
    assert (old["mode"], new["mode"]) == ("old", "new")
    assert old["caught"] == 0 and new["caught"] == 1 and old["quiet"] == new["quiet"] == 1
    text = "\n".join(RC.lines(cd))
    assert "new vs old: +1 right" in text and "MISS [old] delivery_off_by_one - missed the bug" in text
    from app.config import get_settings
    assert get_settings().dev_spec_review is False                                             # the switch is put back



def test_the_fix_card_spec_switch(monkeypatch):
    from app.devsahayak import loop as L
    from app.quality import code_tasks2 as C2
    from app.quality import codecard as K
    seen = []

    def brain(system, messages, tools):
        seen.append(system)
        return [tu(1, "done", explain="nothing")], "tool_use"
    monkeypatch.setattr(L, "BRAIN", brain)
    K.run_task(next(t for t in C2.TASKS if t["id"] == "fix_sunday_count"), 3, 1.0, spec=True)
    assert "CI FIX SPECIALIST" in seen[-1] and "PYTHON fixes" in seen[-1]
    K.run_task(next(t for t in C2.TASKS if t["id"] == "fix_sunday_count"), 3, 1.0, spec=False)
    assert "CI FIX SPECIALIST" not in seen[-1]
    K.run_task(next(t for t in C2.TASKS if t["id"] == "feature_cod_fee"), 3, 1.0, spec=True)
    assert "CI FIX SPECIALIST" not in seen[-1]                                                  # only fix jobs


def test_jobs_settings_and_credit():
    from app.config import Settings
    s = Settings()
    assert s.dev_spec_review is False and s.dev_spec_fix is False                               # off until the cards say so
    yml = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "- review_card" in yml and "- fix_card_spec" in yml and "app.quality review --label vps-ops" in yml
    notes = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
    assert "## ECC" in notes and "Affaan Mustafa" in notes and "specialists.py" in notes
