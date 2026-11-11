"""v0.352 PEHLE CI, PHIR PR (owner: "Run your CI on a draft branch, and fix until it passes, before opening the PR --- go").
A repo with CI gets a DRAFT PR; the worker tick watches her CI every minute: red -> Hoola reads the failure and commits a fix
(with the 8-tool loop when it is on), up to DEV_CI_ROUNDS; green -> the PR is marked ready for review (GitHub GraphQL).
No CI result in DEV_CI_WAIT_MIN -> ready with a 'no tests ran' note. Merge stays her tap. A repo without CI: PR as before."""
from datetime import timedelta

import httpx
import pytest

from tests.test_tech_devsahayak import FIX_ANSWER, REPO, T, _join, dev  # noqa: F401

CI_YML = "name: CI\non:\n  pull_request:\njobs:\n  test:\n    runs-on: ubuntu-latest\n"


@pytest.fixture
def cidev(dev, monkeypatch):  # noqa: F811
    """The same fake GitHub, but the repo has a real CI workflow and GitHub's GraphQL 'ready for review' answers."""
    from app.devsahayak import gh as G
    S = dev
    fake = S.FAKE
    tree = fake.trees[fake.commits[fake.refs["main"]]["tree"]]
    tree.append({"path": ".github/workflows/ci.yml", "mode": "100644", "type": "blob", "sha": fake._blob(CI_YML.encode())})
    fake.ready = []
    inner = fake.handler

    def handler(req: httpx.Request) -> httpx.Response:
        import json as _j
        if req.url.path == "/graphql":
            body = _j.loads(req.content)
            n = int(body["variables"]["id"].removeprefix("PR_"))
            fake.prs[n]["draft"] = False
            fake.ready.append(n)
            return httpx.Response(200, json={"data": {"markPullRequestReadyForReview": {"pullRequest": {"isDraft": False}}}})
        for n, pr in fake.prs.items():
            pr.setdefault("node_id", f"PR_{n}")
        return inner(req)
    G.set_transport(httpx.MockTransport(handler))
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)       # these tests drive the one-shot answers
    monkeypatch.setattr(get_settings(), "dev_fix_proof", False, raising=False)  # v0.447 proof run off here: tested in its own file
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    _join(S)
    return S


def _run(fake, sha, conclusion):
    fake.check_runs[sha] = [{"id": 5, "name": "pytest", "status": "completed", "conclusion": conclusion}]


def _says(S):
    return [p.get("say", "") for _, p in S.EVENTS if isinstance(p, dict)]


def test_red_then_fix_then_green_then_ready(cidev, monkeypatch):
    S = cidev
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash ho raha hai", conv="c1")
    assert v["status"] == "ci_running" and fake.prs[1]["draft"] is True               # a DRAFT first
    assert "PASS hone par hi" in v["say"]
    head1 = fake.prs[1]["head"]["sha"]
    _run(fake, head1, "failure")
    fixed = {"explain": "test galat tha", "files": [{"path": "tests/test_calc.py", "why": "fix", "edits": [
        {"find": "def test_empty():", "replace": "def test_empty_cart():"}]}]}
    monkeypatch.setattr(S, "model_json", lambda *a, **k: fixed)
    S._ci_step(T, v["id"])                                                           # red -> a fix commit, still a draft
    t = S.get_task(T, v["number"])
    head2 = fake.prs[1]["head"]["sha"]
    assert t["status"] == "ci_running" and head2 != head1 and fake.prs[1]["draft"] is True
    assert "test_empty_cart" in fake.files_at(fake.refs[t["branch"]])["tests/test_calc.py"]
    _run(fake, head2, "success")
    S._ci_step(T, v["id"])                                                           # green -> ready for review
    t = S.get_task(T, v["number"])
    assert t["status"] == "pr_open" and fake.prs[1]["draft"] is False and fake.ready == [1]
    assert any("CI PASS (1 fix round ke baad)" in s for s in _says(S))
    assert not fake.merges                                                           # never merged by itself


def test_it_stops_after_the_rounds_and_tells_her(cidev, monkeypatch):
    S = cidev
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_ci_rounds", 1, raising=False)
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    _run(fake, fake.prs[1]["head"]["sha"], "failure")
    monkeypatch.setattr(S, "model_json", lambda *a, **k: {"explain": "x", "files": [{"path": "app/calc.py", "why": "x",
                        "edits": [{"find": "    s = 0\n", "replace": "    s = 0  # start\n"}]}]})
    S._ci_step(T, v["id"])                                                           # round 1
    _run(fake, fake.prs[1]["head"]["sha"], "failure")
    S._ci_step(T, v["id"])                                                           # rounds used up
    t = S.get_task(T, v["number"])
    assert t["status"] == "checks_failed" and fake.prs[1]["draft"] is True
    assert any("1 fix round(s) done and CI still fails" in s for s in _says(S))


def test_no_ci_result_means_ready_with_a_note(cidev):
    S = cidev
    from app.db import now
    v = S.start(T, "fix", "Checkout crash")
    assert S._ci_step(T, v["id"]) is None                                            # just pushed: wait
    S._ci_step(T, v["id"], now() + timedelta(minutes=16))
    t = S.get_task(T, v["number"])
    assert t["status"] == "pr_open" and S.FAKE.prs[1]["draft"] is False
    assert any("no CI ran on this PR" in s for s in _says(S))


def test_the_tick_drives_the_loop(cidev):
    S = cidev
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    _run(fake, fake.prs[1]["head"]["sha"], "success")
    S.tick()
    assert S.get_task(T, v["number"])["status"] == "pr_open" and fake.ready == [1]


def test_a_repo_without_ci_is_reviewed_by_hoola_itself_before_the_handover(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    v = S.start(T, "fix", "Checkout crash")                                         # deploy.yml only = no CI
    # v0.443: the draft is opened, Hoola's own review runs inside the push, and the card is already the handover
    assert v["status"] == "pr_open" and "ready for review" in v["say"]
    # (this fake has no GraphQL, so its own draft flag never flips; the cidev tests cover the real mark-ready)


def test_a_ci_fix_round_explores_with_the_tools_on_the_branch(cidev, monkeypatch):
    S = cidev
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    _run(fake, fake.prs[1]["head"]["sha"], "failure")
    from app.config import get_settings
    from app.devsahayak import loop as L
    monkeypatch.setattr(get_settings(), "dev_loop", True, raising=False)
    seen = []
    turns = [[{"type": "tool_use", "id": "a", "name": "read_file", "input": {"path": "app/calc.py"}}],
             [{"type": "tool_use", "id": "b", "name": "done", "input": {"explain": "theek kiya"}}]]

    def brain(system, messages, tools):
        seen.append(messages[0]["content"])
        return turns.pop(0), "tool_use"
    monkeypatch.setattr(L, "BRAIN", brain)
    S._ci_step(T, v["id"])
    assert "open PR branch (commit" in seen[0] and "<ci_log>" in seen[0] and "AssertionError" in seen[0]
