"""v0.451 ECC PHASE 4 - PLAN PEHLE (owner: "GO PHASE 4").

From ECC's orch-pipeline: "Ceremony scales to blast radius" + GATE 1 after the plan. A trivial / small job goes straight
to work as before; a standard or large one gets a READ-ONLY plan pass first (it cannot edit - the edit tools are not
given); a LARGE one waits for her Haan before a single file is touched. The approved plan then rides into the edit loop
("the planning docs ARE the handoff"), its done_when lines go into the PR, and v0.445's own review is checked against
them."""
import pytest

from tests.test_tech_devsahayak import CALC, REPO, T, _join, dev  # noqa: F401

FIXED = CALC.replace("    return s / len(items)\n", "    return s\n")
PLAN = {"goal": "Khaali cart par total 0 lautaye", "risk": "api/handlers.py total() ko call karta hai",
        "files": [{"path": "app/calc.py", "why": "divide hata do", "new": False},
                  {"path": "tests/test_calc.py", "why": "khaali cart ka test", "new": False}],
        "steps": ["app/calc.py: divide hatao", "tests/test_calc.py: khaali cart ka test jodo"],
        "done_when": ["pytest tests/test_calc.py pass ho", "total([]) == 0"], "questions": [], "base_sha": ""}
EDIT_OUT = {"explain": "divide hata diya", "pr_title": "Fix total() on empty cart", "pr_summary": "- sum",
            "test_plan": "- CI", "risk": "callers",
            "files": [{"path": "app/calc.py", "why": "fix", "content": FIXED}]}


@pytest.fixture
def pl(dev, monkeypatch):  # noqa: F811
    """The loop on, but both passes stubbed: plan_run gives PLAN, run gives one real file change and records its prompt."""
    from app.config import get_settings
    from app.devsahayak import loop as L
    S = dev
    _join(S)
    monkeypatch.setattr(get_settings(), "dev_loop", True, raising=False)
    monkeypatch.setattr(get_settings(), "dev_fix_proof", False, raising=False)
    monkeypatch.setattr(S, "explore_review", lambda *a, **k: {"summary": "ok", "verdict": "comment", "comments": []})
    seen = {"plan": [], "run": []}

    def plan_run(g, t, rules, extra_files, issue_txt="", **k):
        seen["plan"].append({"kind": t.kind, "text": t.text})
        return dict(PLAN, base_sha=S.FAKE.refs["main"])
    def run(g, t, rules, extra_files, allow=False, issue_txt="", **k):
        seen["run"].append(k.get("plan_txt") or "")
        return S.FAKE.refs["main"], [], {"found": {"read": []}, "context": ""}, dict(EDIT_OUT)
    monkeypatch.setattr(L, "plan_run", plan_run)
    monkeypatch.setattr(L, "run", run)
    S.SEEN = seen
    return S


def _says(S):
    return [p.get("say", "") for _, p in S.EVENTS if isinstance(p, dict)]


def test_the_tier_table_scores_her_asks():
    from app.devsahayak import plan as P
    def tier(kind, text, files=None):
        return P.assess(kind, text, files or [])["tier"]
    assert tier("explain", "checkout crash kyun hota hai") == "trivial"
    assert tier("docs", "README mein install steps likho") == "trivial"
    assert tier("fix", "Khaali cart par ZeroDivisionError, app/calc.py line 5") == "small"
    assert tier("tests", "app/calc.py ke tests likho", ["app/calc.py"]) == "small"
    assert tier("write", "ek chhota helper banao jo date format kare") == "small"
    assert tier("fix", "checkout mein kuch gadbad hai theek karo") == "standard"      # vague, never 'large'
    assert tier("write", "dashboard par naya chart jodo") == "standard"
    assert tier("write", "signup page par OTP login lagao") == "standard"             # trigger: at least standard
    assert tier("write", "Payment gateway jodo: razorpay checkout, webhook, refund aur invoice") == "large"
    assert tier("write", "poora admin panel refactor karo") == "large"
    assert P.needs_plan("standard") and P.needs_plan("large")
    assert not P.needs_plan("small") and not P.needs_plan("trivial")
    assert P.waits("large") and not P.waits("standard")


def test_a_small_job_plans_nothing_and_works_as_before(pl):
    S = pl
    v = S.start(T, "fix", "Khaali cart par ZeroDivisionError aata hai, app/calc.py line 5")
    assert S.SEEN["plan"] == [] and v["tier"] == "small"          # no plan pass at all
    assert v["status"] in ("pr_open", "ci_running") and S.SEEN["run"] == [""]


def test_a_large_job_plans_first_waits_and_touches_nothing(pl):
    S = pl
    fake = S.FAKE
    before = dict(fake.refs)
    v = S.start(T, "write", "Payment gateway jodo: razorpay checkout, webhook, refund aur invoice", conv="c1")
    assert v["tier"] == "large" and v["status"] == "plan_wait" and len(S.SEEN["plan"]) == 1
    assert S.SEEN["run"] == [] and fake.refs == before and not fake.prs    # NOTHING was written
    assert v["plan"]["steps"] == PLAN["steps"] and v["plan"]["done_when"] == PLAN["done_when"]
    assert any("aapki haan chahiye" in s for s in _says(S))
    assert any(k == "devsahayak_plan" for k, _ in S.EVENTS)

    out = S.plan_ok(T, v["number"], v["hash"], by_tap=True)               # her Haan -> the work runs
    assert out["status"] in ("ready", "pr_open", "ci_running")
    assert len(S.SEEN["run"]) == 1 and "<approved_plan>" in S.SEEN["run"][0]
    assert "DONE WHEN" in S.SEEN["run"][0] and "total([]) == 0" in S.SEEN["run"][0]


def test_her_haan_is_hers_alone(pl):
    S = pl
    v = S.start(T, "write", "poora admin panel refactor karo")
    assert v["status"] == "plan_wait"
    with pytest.raises(S.DevError, match="card se"):
        S.plan_ok(T, v["number"], v["hash"])                              # not by tap
    with pytest.raises(S.DevError, match="Card badal"):
        S.plan_ok(T, v["number"], "wrong-hash", by_tap=True)
    out = S.plan_ok(T, v["number"], v["hash"], by_tap=True, note="Razorpay hi rakhna, Stripe nahi")
    assert "Razorpay hi rakhna" in S.SEEN["run"][0]                       # her words ride with the plan
    with pytest.raises(S.DevError):                                       # and only once
        S.plan_ok(T, v["number"], v["hash"], by_tap=True)
    assert out["status"] in ("ready", "pr_open", "ci_running")


def test_a_standard_job_shows_the_plan_and_starts_at_once(pl):
    S = pl
    v = S.start(T, "write", "dashboard par naya chart jodo")
    assert v["tier"] == "standard" and len(S.SEEN["plan"]) == 1
    assert v["status"] != "plan_wait" and len(S.SEEN["run"]) == 1         # no waiting
    assert "<approved_plan>" in S.SEEN["run"][0]
    assert any("kaam shuru kar raha hoon" in s for s in _says(S))


def test_the_plan_reaches_the_pr_and_the_own_review(pl):
    S = pl
    v = S.start(T, "write", "dashboard par naya chart jodo")
    body = S.get_task(T, v["number"], )["id"] and S.FAKE.prs[1]["body"] if S.FAKE.prs else ""
    assert "Done when" in body and "total([]) == 0" in body              # a reviewer sees the target
    from app.devsahayak import plan as P
    txt = P.as_text(PLAN)
    assert "acceptance criteria" in txt and "do not widen" in txt


def test_a_plan_pass_cannot_edit_anything(dev, monkeypatch):  # noqa: F811
    """The real plan loop: the edit tools are not offered, and anything else is refused in words."""
    from app.db import session
    from app.devsahayak import loop as L
    from app.devsahayak.models import DevTask
    S = dev
    _join(S)
    assert {x["name"] for x in L.PLAN_TOOLS} == {"list_dir", "search_code", "read_file", "find_usages", "done"}
    with session() as s_:
        t = DevTask(tenant_id=T, number="D-0099", kind="write", repo=REPO, text="payment gateway jodo",
                    base="main")
        s_.add(t)
        s_.flush()
        s_.expunge(t)
    turns = [[{"type": "tool_use", "id": "a", "name": "read_file", "input": {"path": "app/calc.py"}}],
             [{"type": "tool_use", "id": "b", "name": "edit_file",
               "input": {"path": "app/calc.py", "old": "return s / len(items)", "new": "return s"}}],
             [{"type": "tool_use", "id": "c", "name": "done", "input": dict(PLAN)}]]
    said = []

    def brain(system, messages, tools):
        if isinstance(messages[-1].get("content"), list):
            said.extend(str(x.get("content") or "") for x in messages[-1]["content"])
        return (turns.pop(0) if turns else [{"type": "tool_use", "id": "z", "name": "done", "input": dict(PLAN)}]), "tool_use"
    monkeypatch.setattr(L, "BRAIN", brain)
    refs_before = dict(S.FAKE.refs)
    out = L.plan_run(S.gh(T), t, "", [])
    assert out["steps"] == PLAN["steps"] and out["done_when"] == PLAN["done_when"]
    assert any("not available while planning" in x for x in said)
    assert S.FAKE.refs == refs_before and not S.FAKE.prs            # the plan pass wrote nothing at all


def test_the_switches(pl, monkeypatch):
    S = pl
    from app.config import get_settings
    s = get_settings()
    assert s.dev_plan_first is True and s.dev_plan_gate is True
    monkeypatch.setattr(s, "dev_plan_gate", False, raising=False)
    v = S.start(T, "write", "poora admin panel refactor karo")           # large, but nothing waits now
    assert v["tier"] == "large" and v["status"] != "plan_wait" and len(S.SEEN["run"]) == 1
    monkeypatch.setattr(s, "dev_plan_first", False, raising=False)
    S.SEEN["plan"].clear()
    v2 = S.start(T, "write", "Payment gateway jodo: razorpay checkout, webhook, refund aur invoice")
    assert S.SEEN["plan"] == [] and v2["status"] != "plan_wait"           # no plan pass at all
