"""v0.445 ECC PHASE 2 - KHUD KA REVIEW (owner: "ECC Phase 2: Hoola reviews its own PR before marking it 'Ready for review'").

Before a draft PR is handed to her, Hoola reads its OWN work back with the same exploring reviewer it uses on anyone else's
PR (plus specialists.SELF_REVIEW: did the task really get done, does a caller / test break, leftovers). A real problem goes
back as one more fix round and the PR stays a DRAFT; a clean read hands it over. The own review never reaches GitHub, and
merge stays her tap."""
import pytest

from tests.test_tech_devsahayak import T, _join, dev  # noqa: F401
from tests.test_v0352_pehle_ci import _run, _says, cidev  # noqa: F401

FILES = [{"filename": "app/calc.py", "status": "modified", "additions": 2,
          "patch": "@@ -1,3 +1,5 @@\n def total(items):\n+    print('debug total', items)\n+    s = 0\n     return s\n"}]

CLEAN = {"summary": "Change poora hai, caller theek hain.", "verdict": "comment", "comments": [], "loop": {"steps": 3}}
DIRTY = {"summary": "Ek debug print reh gaya.", "verdict": "request_changes", "loop": {"steps": 4},
         "comments": [{"path": "app/calc.py", "line": 2, "severity": "medium", "body": "Debug print reh gaya hai, hataiye."},
                      {"path": "app/calc.py", "line": 3, "severity": "low", "body": "Naam chhota kar sakte hain."}]}


@pytest.fixture
def selfdev(cidev):  # noqa: F811
    """cidev; _files() then serves /pulls/n/files so the own-review gate has a real diff to read."""
    return cidev


def _arm(S, monkeypatch, answers):
    """The own review's answers in order; the PR's files are served as soon as it exists."""
    seen = []

    def fake_review(g, repo, head, pr_text, diff_parts, added_lines, rules="", findings="", extra=""):
        seen.append({"pr_text": pr_text, "extra": extra, "diffs": diff_parts, "added": added_lines})
        return answers[min(len(seen) - 1, len(answers) - 1)]
    monkeypatch.setattr(S, "explore_review", fake_review)
    return seen


def _files(S):
    S.FAKE.prs[1]["files"] = FILES


def test_a_problem_in_its_own_pr_goes_back_for_a_fix_and_the_pr_stays_a_draft(selfdev, monkeypatch):
    S = selfdev
    fake = S.FAKE
    seen = _arm(S, monkeypatch, [DIRTY, CLEAN])
    v = S.start(T, "fix", "Checkout crash ho raha hai", conv="c1")
    monkeypatch.setattr(S, "model_json", lambda *a, **k: {"explain": "debug print hataya", "files": [
        {"path": "tests/test_calc.py", "why": "fix", "edits": [
            {"find": "def test_empty():", "replace": "def test_empty_cart():"}]}]})
    assert v["status"] == "ci_running" and fake.prs[1]["draft"] is True
    _files(S)
    head1 = fake.prs[1]["head"]["sha"]
    _run(fake, head1, "success")
    S._ci_step(T, v["id"])                                   # CI green -> the own review runs, finds the print
    t = S.get_task(T, v["number"])
    assert t["status"] == "ci_running" and fake.prs[1]["draft"] is True and fake.ready == []
    assert t["self_round"] == 1 and t["self_review"]["verdict"] == "request_changes"
    assert len(t["self_review"]["problems"]) == 1            # the low comment never blocks
    assert fake.prs[1]["head"]["sha"] != head1               # a fix commit went on the same branch
    assert seen[0]["extra"].startswith("OWN WORK") and "YOUR OWN work" in seen[0]["pr_text"]
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])                                   # second read is clean -> ready for review
    t = S.get_task(T, v["number"])
    assert t["status"] == "pr_open" and fake.prs[1]["draft"] is False and fake.ready == [1]
    assert any("found no problems" in s for s in _says(S))
    assert not fake.merges                                   # merge is still only her tap


def test_a_clean_own_review_hands_it_over_at_once(selfdev, monkeypatch):
    S = selfdev
    fake = S.FAKE
    seen = _arm(S, monkeypatch, [CLEAN])
    v = S.start(T, "fix", "Checkout crash")
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])
    t = S.get_task(T, v["number"])
    assert t["status"] == "pr_open" and t["self_round"] == 0 and fake.ready == [1]
    assert len(seen) == 1 and seen[0]["added"] == {"app/calc.py": {2, 3}}
    assert not getattr(fake, "reviews", [])                  # the own review NEVER goes to GitHub


def test_it_stops_after_the_rounds_and_names_what_is_still_open(selfdev, monkeypatch):
    S = selfdev
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_self_rounds", 1, raising=False)
    fake = S.FAKE
    _arm(S, monkeypatch, [DIRTY, DIRTY])
    v = S.start(T, "fix", "Checkout crash")
    monkeypatch.setattr(S, "model_json", lambda *a, **k: {"explain": "debug print hataya", "files": [
        {"path": "tests/test_calc.py", "why": "fix", "edits": [
            {"find": "def test_empty():", "replace": "def test_empty_cart():"}]}]})
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])                                   # round 1
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])                                   # no round left -> handed over, said plainly
    t = S.get_task(T, v["number"])
    assert t["status"] == "pr_open" and fake.prs[1]["draft"] is False
    assert any("still open" in s and "Debug print" in s for s in _says(S))


def test_a_repo_without_ci_still_gets_the_own_review(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.config import get_settings
    from tests.test_tech_devsahayak import FIX_ANSWER
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    seen = _arm(S, monkeypatch, [CLEAN])
    monkeypatch.setattr(S, "_has_ci", lambda *a, **k: False)
    orig = S.pr_diff
    monkeypatch.setattr(S, "pr_diff", lambda files, limit=60: orig(FILES, limit))   # the PR exists only mid-push
    v = S.start(T, "fix", "Checkout crash")                  # deploy.yml only = no CI at all
    # no CI to wait for: the own review ran inside the push itself, so the card she gets is already the handover
    assert v["status"] == "pr_open" and len(seen) == 1       # (this fake has no GraphQL to flip its draft flag)
    assert any("has no CI" in s and "found no problems" in s for s in _says(S))


def test_the_gate_never_blocks_a_pr_it_could_not_read(selfdev, monkeypatch):
    S = selfdev

    def boom(*a, **k):
        raise RuntimeError("model down")
    monkeypatch.setattr(S, "explore_review", boom)
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])
    assert S.get_task(T, v["number"])["status"] == "pr_open" and fake.ready == [1]


def test_switch_off_keeps_the_old_behaviour(selfdev, monkeypatch):
    S = selfdev
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_self_review", False, raising=False)
    seen = _arm(S, monkeypatch, [DIRTY])
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])
    assert S.get_task(T, v["number"])["status"] == "pr_open" and seen == []


def test_only_real_severities_block():
    from app.devsahayak import service as S
    out = {"comments": [{"path": "a.py", "line": 1, "severity": "low", "body": "nit"},
                        {"path": "a.py", "line": 2, "severity": "medium", "body": "[Hoola check] OWASP note"},
                        {"path": "a.py", "line": 3, "severity": "high", "body": "Oversell ho jayega"}]}
    bad = S._self_blocking(out, [{"path": "b.py", "line": 9, "severity": "medium", "say": "note"},
                                 {"path": "c.py", "line": 4, "severity": "high", "say": "secret"}])
    assert [b["body"] for b in bad] == ["Oversell ho jayega", "secret"]


def test_the_own_review_reads_the_pr_with_the_self_review_block(selfdev, monkeypatch):
    """Through the real review loop: the system prompt carries SELF_REVIEW and the comment lands on an added line."""
    S = selfdev
    from app.config import get_settings
    from app.devsahayak import loop as L
    monkeypatch.setattr(get_settings(), "dev_spec_review", True, raising=False)
    systems = []
    turns = [[{"type": "tool_use", "id": "a", "name": "comment", "input": {
                  "path": "app/calc.py", "line": 2, "severity": "medium", "body": "Debug print hataiye"}}],
             [{"type": "tool_use", "id": "b", "name": "done", "input": {"summary": "ek print", "verdict": "request_changes"}}]]

    def brain(system, messages, tools):
        systems.append(system)
        return (turns.pop(0), "tool_use") if turns else ([{"type": "tool_use", "id": "z", "name": "done",
                                                           "input": {"summary": "ok", "verdict": "comment"}}], "tool_use")
    monkeypatch.setattr(L, "BRAIN", brain)
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    _files(S)
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])
    assert any("OWN WORK" in sy and "REVIEW DISCIPLINE" in sy for sy in systems)
    t = S.get_task(T, v["number"])
    assert t["self_round"] == 1 and t["status"] == "ci_running"      # its own medium comment sent the work back


def test_the_switches_are_on_by_default():
    from app.config import get_settings
    s = get_settings()
    assert s.dev_self_review is True and s.dev_self_rounds == 2
