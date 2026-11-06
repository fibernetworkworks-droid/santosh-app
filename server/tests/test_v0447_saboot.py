"""v0.447 ECC PHASE 3 - SABOOT, prove the bug before fixing it (owner asked for "the next idea from that repo").

From ECC's orch-fix-defect: "reproduce the bug as a new failing test, then fix until it goes green. Proving the bug exists
first is what separates a fix from a tweak." Hoola's own rule already demanded such a test and nothing ever checked it. Now
a fix's TEST is pushed on its own first commit, her CI runs it, and the red run is the proof - then the fix commit lands.
From ECC's verification-loop: the verdict is REPORTED with its evidence (proven / red-but-not-named / NOT proven / not
measured), never claimed."""
import httpx
import pytest

from tests.test_tech_devsahayak import CALC, FIX_ANSWER, REPO, T, _join, dev  # noqa: F401
from tests.test_v0352_pehle_ci import _run, _says, cidev  # noqa: F401

CLEAN = {"summary": "theek hai", "verdict": "comment", "comments": [], "loop": {"steps": 2}}


@pytest.fixture
def pdev(cidev, monkeypatch):  # noqa: F811
    """cidev with the proof run ON (its fixture turns it off), the own review stubbed clean, and PR edits recorded."""
    from app.config import get_settings
    from app.devsahayak import gh as G
    S = cidev
    monkeypatch.setattr(get_settings(), "dev_fix_proof", True, raising=False)
    monkeypatch.setattr(S, "explore_review", lambda *a, **k: CLEAN)
    fake = S.FAKE
    fake.pr_patch = []
    inner = G._TRANSPORT.handler if hasattr(G, "_TRANSPORT") else None

    def handler(req: httpx.Request) -> httpx.Response:
        import json as _j
        if req.method == "PATCH" and req.url.path.endswith(f"/repos/{REPO}/pulls/1"):
            fake.pr_patch.append(_j.loads(req.content))
            fake.prs[1].update(fake.pr_patch[-1])
            return httpx.Response(200, json=fake.prs[1])
        return (inner or fake.handler)(req)
    G.set_transport(httpx.MockTransport(handler))
    return S


def _files(S, branch):
    return S.FAKE.files_at(S.FAKE.refs[branch])


def test_the_test_lands_first_and_a_red_run_proves_the_bug(pdev):
    S = pdev
    fake = S.FAKE
    v = S.start(T, "fix", "Khaali cart par checkout crash", conv="c1")
    # the FIRST commit carries the test only: app/calc.py is still the broken original
    files = _files(S, v["branch"])
    assert "def test_empty" in files["tests/test_calc.py"] and files["app/calc.py"] == CALC
    assert v["status"] == "ci_running" and fake.prs[1]["draft"] is True
    assert v["proof"]["state"] == "wait" and v["proof"]["tests"] == ["tests/test_calc.py"]
    assert "test FAIL hona chahiye" in v["say"] and "saboot" in v["say"]
    test_sha = fake.prs[1]["head"]["sha"]

    _run(fake, test_sha, "failure")                      # her CI: the new test fails on the unfixed code = PROVEN
    S._ci_step(T, v["id"])
    t = S.get_task(T, v["number"])
    assert t["proof"]["state"] == "proven" and t["status"] == "ci_running"
    assert _files(S, t["branch"])["app/calc.py"] != CALC          # now the fix commit is on the branch
    assert fake.prs[1]["draft"] is True                          # still a draft; nothing handed over yet
    assert any("bug saabit ho gaya" in s for s in _says(S))
    assert any("Proven." in (p.get("body") or "") for p in fake.pr_patch)

    _run(fake, fake.prs[1]["head"]["sha"], "success")             # the fix is green -> own review -> ready
    S._ci_step(T, v["id"])
    t = S.get_task(T, v["number"])
    assert t["status"] == "pr_open" and fake.ready == [1] and not fake.merges


def test_a_test_that_passes_on_the_old_code_is_said_plainly(pdev):
    S = pdev
    fake = S.FAKE
    v = S.start(T, "fix", "Khaali cart par checkout crash")
    _run(fake, fake.prs[1]["head"]["sha"], "success")             # green on the UNFIXED code = proves nothing
    S._ci_step(T, v["id"])
    t = S.get_task(T, v["number"])
    assert t["proof"]["state"] == "not_proven"
    assert _files(S, t["branch"])["app/calc.py"] != CALC          # the fix still lands - it is not thrown away
    assert any("saabit nahi karta" in s for s in _says(S))
    assert any("NOT proven" in (p.get("body") or "") for p in fake.pr_patch)


def test_a_red_run_that_does_not_name_the_test_says_so(pdev, monkeypatch):
    S = pdev
    from app.devsahayak import gh as G
    fake = S.FAKE
    v = S.start(T, "fix", "Khaali cart par checkout crash")
    inner = G._TRANSPORT.handler

    def other(req: httpx.Request) -> httpx.Response:
        if "/check-runs/" in req.url.path and req.url.path.endswith("/annotations"):
            return httpx.Response(200, json=[{"path": "app/other.py", "start_line": 2, "annotation_level": "failure",
                                              "message": "ImportError: cannot import name x"}])
        if "/check-runs/" in req.url.path:
            return httpx.Response(200, json={"output": {"title": "1 failed", "summary": "collection error in app/other.py"}})
        return inner(req)
    G.set_transport(httpx.MockTransport(other))
    _run(fake, fake.prs[1]["head"]["sha"], "failure")
    S._ci_step(T, v["id"])
    t = S.get_task(T, v["number"])
    assert t["proof"]["state"] == "proven_unnamed"
    assert any("naam se nahi dikha" in s for s in _says(S))


def test_no_ci_result_is_called_not_measured_never_proven(pdev):
    S = pdev
    from datetime import timedelta

    from app.db import now
    v = S.start(T, "fix", "Khaali cart par checkout crash")
    assert S._ci_step(T, v["id"]) is None                        # just pushed: wait for her CI
    S._ci_step(T, v["id"], now() + timedelta(minutes=16))
    t = S.get_task(T, v["number"])
    assert t["proof"]["state"] == "unknown" and t["status"] == "ci_running"
    assert _files(S, t["branch"])["app/calc.py"] != CALC
    assert any("saboot naap nahi paya" in s for s in _says(S))


def test_a_fix_with_no_test_and_a_feature_skip_the_proof(pdev, monkeypatch):
    S = pdev
    monkeypatch.setattr(S, "model_json", lambda *a, **k: {
        "explain": "x", "pr_title": "Fix total", "files": [{"path": "app/calc.py", "why": "x", "edits": [
            {"find": "    return s / len(items)\n", "replace": "    return s\n"}]}]})
    v = S.start(T, "fix", "Khaali cart par crash")                # no test in the change -> nothing to prove with
    assert v["proof"] == {} and _files(S, v["branch"])["app/calc.py"] != CALC
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    v2 = S.start(T, "write", "Empty cart ka test aur sum")        # a feature, not a fix -> no proof run
    assert v2["proof"] == {}


def test_only_the_test_files_go_in_the_first_commit(pdev):
    from app.devsahayak import rules as R
    from app.devsahayak import service as S2
    assert R.is_test_path("tests/test_calc.py") and R.is_test_path("src/__tests__/cart.test.ts")
    assert R.is_test_path("app/calc_test.go") and not R.is_test_path("app/latest.py")
    ch = [{"path": "app/calc.py"}, {"path": "tests/test_calc.py"}]
    T0 = type("T", (), {"kind": "fix"})()
    assert S2._proof_tests(T0, ch, True) == ["tests/test_calc.py"]
    assert S2._proof_tests(T0, ch, False) == []                                  # no CI in her repo
    assert S2._proof_tests(T0, [{"path": "tests/test_calc.py"}], True) == []     # tests only: no fix to split off
    assert S2._proof_tests(type("T", (), {"kind": "docs"})(), ch, True) == []


def test_the_switch_is_on_by_default():
    from app.config import get_settings
    assert get_settings().dev_fix_proof is True
