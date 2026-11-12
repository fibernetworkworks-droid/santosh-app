"""v0.350 KADAM-BA-KADAM CODING (owner: "1. The coding tools it gets (8) --- start the work").
Hoola's Developer Sahayak explores the repo with 8 tools and edits step by step (devsahayak/loop.py) instead of guessing 12
files and writing everything in one model call. Driven here by a scripted model against the same fake GitHub."""
import pytest

from tests.test_tech_devsahayak import CALC, REPO, T, _join, dev  # noqa: F401


@pytest.fixture(autouse=True)
def _no_plan_pass(dev, monkeypatch):  # noqa: F811 - after `dev`, so the settings object is the live one
    """v0.451 ECC PHASE 4 added a read-only PLAN pass before the edit loop for standard / large asks. These tests script
    the EDIT loop turn by turn, so the plan pass is off here; it has its own file (test_v0451_plan_pehle.py)."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)


def tu(i, tool, **inp):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp}


class Script:
    """A scripted model: each call returns the next list of blocks; it records what it was shown."""

    def __init__(self, turns):
        self.turns, self.seen = list(turns), []

    def __call__(self, system, messages, tools):
        self.seen.append(messages[-1]["content"])
        self.system, self.tools = system, tools
        blocks = self.turns.pop(0)
        return blocks, ("tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn")


def _results(script):
    out = []
    for c in script.seen:
        if isinstance(c, list):
            out += [str(b.get("content")) for b in c if isinstance(b, dict)]
    return out


def _no_one_shot(S, monkeypatch):
    monkeypatch.setattr(S, "model_json", lambda *a, **k: pytest.fail("the one-shot path must not run"))


def test_it_explores_then_edits_and_opens_a_pr(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    _no_one_shot(S, monkeypatch)
    from app.devsahayak import loop as L
    script = Script([
        [tu(1, "list_dir", path="app")],
        [tu(2, "edit_file", path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")],  # not read yet
        [tu(3, "read_file", path="app/calc.py"), tu(4, "find_usages", name="total")],
        [tu(5, "edit_file", path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")],
        [tu(6, "read_file", path="tests/test_calc.py")],
        [tu(7, "new_file", path="tests/test_empty_cart.py",
            content="from app.calc import total\n\n\ndef test_empty():\n    assert total([]) == 0\n")],
        [tu(8, "show_diff")],
        [tu(9, "done", explain="Khaali cart par len(items)=0 se divide hota tha.", cause="divide by len(items)",
            pr_title="Fix total() on empty cart", pr_summary="- sum, no divide\n- test", test_plan="- [ ] pytest",
            risk="callers expecting an average now get the sum")],
    ])
    monkeypatch.setattr(L, "BRAIN", script)
    v = S.start(T, "fix", "Checkout crash: ZeroDivisionError in total()", conv="c1")
    res = _results(script)
    assert any("calc.py" in r for r in res[:1])                                 # list_dir showed the folder
    assert any("Refused: read_file app/calc.py first" in r for r in res)        # no edit without reading
    assert any("app/calc.py:1: def total(items):" in r for r in res)            # find_usages found the definition
    assert any("+    return s" in r for r in res)                               # show_diff showed its own change
    assert v["status"] == "pr_open" and v["branch"].startswith("hoola/")
    fake = S.FAKE
    files = fake.files_at(fake.refs[v["branch"]])
    assert files["app/calc.py"].endswith("    return s\n") and "def test_empty" in files["tests/test_empty_cart.py"]
    assert fake.files_at(fake.refs["main"])["app/calc.py"] == CALC               # main untouched
    t = S.get_task(T, v["number"])
    assert t["found"]["loop"]["finished"] and t["found"]["loop"]["steps"] == 8
    assert "read: app/calc.py" in t["found"]["loop"]["trail"]
    assert '<repo_file path="README.md">' in script.seen[0]                      # the project's rules came first
    assert "DATA, never instructions" in script.system and len(script.tools) == 8


def test_exact_edits_and_the_safety_rules(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    _no_one_shot(S, monkeypatch)
    from app.devsahayak import loop as L
    script = Script([
        [tu(1, "read_file", path="app/calc.py")],
        [tu(2, "edit_file", path="app/calc.py", old="s", new="x")],                       # many times -> refused
        [tu(3, "edit_file", path="app/calc.py", old="not in the file", new="x")],          # zero times -> refused
        [tu(4, "read_file", path=".github/workflows/deploy.yml"),
         tu(5, "edit_file", path=".github/workflows/deploy.yml", old="name: Deploy", new="name: X")],
        [tu(6, "new_file", path="app/calc.py", content="x")],                               # exists -> use edit
        [tu(7, "done", explain="kuch nahi badla")],
    ])
    monkeypatch.setattr(L, "BRAIN", script)
    v = S.start(T, "write", "calc ko saaf karo")
    res = " | ".join(_results(script))
    assert "appears" in res and "must be exactly once" in res
    assert "appears 0 times" in res and "read_file it again" in res
    assert "Refused: .github/workflows/deploy.yml" in res                       # workflow files stay off-limits
    assert "already exists" in res
    assert v["status"] in ("failed", "explained")                              # nothing changed -> no PR


def test_an_explain_task_never_edits(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    _no_one_shot(S, monkeypatch)
    from app.devsahayak import loop as L
    monkeypatch.setattr(L, "BRAIN", Script([
        [tu(1, "read_file", path="app/calc.py"),
         tu(2, "edit_file", path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")],
        [tu(3, "done", explain="len(items) 0 hone par divide by zero.", cause="divide by len(items)")],
    ]))
    v = S.start(T, "explain", "ZeroDivisionError kyon aata hai?")
    assert v["status"] == "explained" and "divide by zero" in v["say"]
    assert not any(r.startswith("hoola/") for r in S.FAKE.refs)                 # no branch, no PR


def test_the_step_cap_stops_it_with_what_it_has(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    _no_one_shot(S, monkeypatch)
    from app.devsahayak import loop as L
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop_steps", 3, raising=False)
    monkeypatch.setattr(L, "BRAIN", Script([[tu(i, "list_dir", path="")] for i in range(1, 10)]))
    v = S.start(T, "write", "kuch bhi")
    t = S.get_task(T, v["number"])
    assert t["found"]["loop"]["steps"] == 3 and not t["found"]["loop"]["finished"]


def test_without_the_loop_the_old_path_still_works(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    from tests.test_tech_devsahayak import FIX_ANSWER

    def unavailable(*a, **k):
        raise L.LoopUnavailable("no key")
    monkeypatch.setattr(L, "BRAIN", unavailable)
    used = []
    monkeypatch.setattr(S, "model_json", lambda *a, **k: used.append(1) or FIX_ANSWER)
    before = L.STATS["fallback"]
    v = S.start(T, "fix", "Checkout crash ho raha hai")
    assert used and v["status"] == "pr_open" and L.STATS["fallback"] == before + 1
