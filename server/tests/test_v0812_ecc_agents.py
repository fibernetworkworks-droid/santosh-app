"""v0.794 ECC AGENTS (owner: "ADD ALL MISSING ECC AGENTS TO HOOLA CODE --- MAKE HOOLA CODE MORE POWERFULL AND SMOOTH
THUS CAN PERFROM ANY HARD CODING TASK SMOOTLY AND PERFECTLY LIKE CLAUDE CODE").

- `devsahayak/ecc/`: every ECC agent (github.com/affaan-m/ECC v2.2.3, MIT) that fits a coding session, adapted as text
  - 63 of 71, the 8 left out each with a written reason; ECC's coding rules for 21 languages + common;
- `devsahayak/subagent.py`: the engine's `agent` tool - a fresh specialist with its own tool level (read / run /
  edit) in the same working copy, several read / run agents at once, a report back to the coder;
- the coder's system prompt carries the roster + how to use it + the repo's coding rules;
- ECC's pre-commit check runs on the diff before `done` is accepted (one clean-up chance);
- the old PR review / CI fix paths reach the new languages (React, Vue, C++, C#, PHP, Ruby, F#, Django ...)."""
from __future__ import annotations

import re
import threading

import pytest

from tests.test_tech_devsahayak import REPO, dev  # noqa: F401
from tests.test_v0787_hoola_code_engine import on, tu  # noqa: F401
from tests.test_v0789_hoola_code_safety import box  # noqa: F401

# every agent file in ECC v2.2.3 (agents/*.md), so the count is pinned without the ECC repo on the machine
ECC_ALL = """a11y-architect agent-evaluator architect bengali-reviewer build-error-resolver chief-of-staff code-architect
code-explorer code-reviewer code-simplifier comment-analyzer commit-reviewer conversation-analyzer cpp-build-resolver
cpp-reviewer csharp-reviewer dart-build-resolver database-reviewer django-build-resolver django-reviewer doc-updater
docs-lookup e2e-runner fastapi-reviewer flutter-reviewer fsharp-reviewer gan-evaluator gan-generator gan-planner
go-build-resolver go-reviewer harmonyos-app-resolver harness-optimizer healthcare-reviewer homelab-architect
java-build-resolver java-reviewer kotlin-build-resolver kotlin-reviewer loop-operator marketing-agent mle-reviewer
network-architect network-config-reviewer network-troubleshooter opensource-forker opensource-packager
opensource-sanitizer performance-optimizer php-reviewer planner pr-test-analyzer python-reviewer pytorch-build-resolver
rag-pipeline-reviewer react-build-resolver react-reviewer refactor-cleaner ruby-reviewer rust-build-resolver
rust-reviewer security-reviewer seo-specialist silent-failure-hunter spec-miner swift-build-resolver swift-reviewer
tdd-guide type-design-analyzer typescript-reviewer vue-reviewer""".split()


# ---------------------------------------------------------------- the catalogue
def test_every_ecc_agent_is_in_or_left_out_with_a_reason():
    from app.devsahayak import ecc
    cat = {k: a for k, a in ecc.catalog().items() if not a["ecc"].startswith("agency:")}   # v0.814 The Agency rides beside
    assert len(ECC_ALL) == 71
    assert set(cat) | set(ecc.NOT_ADDED) == set(ECC_ALL)                 # nothing forgotten
    assert not set(cat) & set(ecc.NOT_ADDED)
    assert len(cat) == 63 and all(len(why) > 30 for why in ecc.NOT_ADDED.values())


def test_each_agent_is_adapted_for_hoola():
    from app.devsahayak import ecc
    from app.devsahayak.ecc.base import GROUPS, TOOL_LEVELS
    for name, a in ecc.catalog().items():
        assert a["group"] in GROUPS and a["tools"] in TOOL_LEVELS, name
        assert 600 <= len(a["prompt"]) <= 3200, (name, len(a["prompt"]))
        assert "adapted from" in a["prompt"][:200].lower(), name           # credited in its own first line
        assert a["when"] and a["title"], name
        low = a["prompt"].lower()
        for bad in ("prompt defense baseline", "~/.claude", "context7", "task tool", "slash command", "mcp server"):
            assert bad not in low, (name, bad)                              # Claude Code-only parts dropped
        for rx in (a["files"], a["words"]):
            if rx:
                re.compile(rx)
    groups = {g: sum(1 for a in ecc.catalog().values() if a["group"] == g) for g in GROUPS}
    assert groups["review"] >= 20 and groups["fix"] >= 12 and groups["plan"] >= 4 and groups["explore"] >= 2
    # read-only reviewers really cannot change anything; the fixers can
    assert ecc.get("security-reviewer")["tools"] in ("read", "run") and ecc.get("react-build-resolver")["tools"] == "edit"
    assert ecc.get("React reviewer") is ecc.get("react_reviewer") is ecc.get("react-reviewer")


def test_rules_for_the_repos_languages():
    from app.devsahayak import ecc
    R = ecc.rules()
    assert len(R) == 22 and "common" in R
    py = ecc.rules_for(["app/a.py", "app/b.py", "README.md"])
    assert "PYTHON RULES" in py and R["common"][:40] in py and "repo's own rules" in py
    web = ecc.rules_for(["src/App.tsx", "src/x.ts", "src/y.ts"])
    assert "REACT RULES" in web.upper() and R["js"][:40] in web
    assert len(ecc.rules_for(["a.py", "b.go", "c.rs", "d.kt", "e.swift"], cap=4000)) < 4400   # stays inside its cap


def test_languages_suggestions_and_the_roster():
    from app.devsahayak import ecc
    assert ecc.langs_of(["a.py", "b.py", "c.ts"]) == ["python", "js"]
    assert ecc.langs_of(["angular.json", "src/a.ts"])[0] == "angular"
    assert ecc.langs_of(["manage.py", "shop/models.py"])[0] == "django"
    s = ecc.suggest(["src/App.tsx", "src/Cart.tsx", "src/api.ts"], "add a login page")
    assert s[0] == "react-reviewer" and "security-reviewer" in s and "code-reviewer" in s
    assert ecc.suggest(["lib/main.dart", "pubspec.yaml"])[0] == "flutter-reviewer"
    r = ecc.roster(["app/a.py"], "fix the bug")
    assert all(f"- {n} [" in r for n in ecc.catalog())                     # every agent named once
    assert "Best fits for this repo: python-reviewer" in r
    assert len(r) < 20000


# ---------------------------------------------------------------- ECC's pre-commit check
def _diff(path, *added):
    body = "\n".join("+" + a for a in added)
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1,2 +10,{len(added)} @@\n{body}\n"


def test_gate_catches_leftovers_and_spares_tests_and_docs():
    from app.devsahayak import ecc
    g = ecc.gate(_diff("src/cart.js", "const a = 1;", "console.log(a);"))
    assert g == [{"path": "src/cart.js", "line": 11, "what": "a console.log left in", "hard": False}]
    assert ecc.gate(_diff("tests/cart.test.js", "console.log(a);")) == []          # fine in a test
    assert ecc.gate(_diff("README.md", "console.log(a);", "<<<<<<< HEAD")) == [
        {"path": "README.md", "line": 11, "what": "a merge conflict marker", "hard": True}]
    assert ecc.gate(_diff("app/x.py", "    breakpoint()"))[0]["hard"] is True
    assert "focused test" in ecc.gate(_diff("tests/a.spec.ts", "it.only('x', () => {})"))[0]["what"]
    assert ecc.gate(_diff("app/x.py", "    return total  # debugger is not a statement here")) == []
    key = "sk_live_" + "51HoolaTestKeyNotReal000000000000"
    assert any("key" in f["what"] for f in ecc.gate(_diff("app/pay.py", f'KEY = "{key}"')))
    txt = ecc.gate_text(g)
    assert "src/cart.js:11" in txt and "call done" in txt


# ---------------------------------------------------------------- the old PR review / CI fix paths
def test_review_and_fix_paths_reach_the_new_languages():
    from app.devsahayak import specialists as SP
    a = SP.review_addendum(["src/App.tsx"])
    assert "JAVASCRIPT / TYPESCRIPT REVIEWER" in a and "REACT REVIEWER" in a.upper()
    assert "PHP REVIEWER" in SP.review_addendum(["src/Cart.php"]).upper()
    assert "adapted from ECC's cpp-reviewer" in SP.review_addendum(["src/a.cpp", "src/a.h"])
    py = SP.review_addendum(["app/orders.py"])
    assert "PYTHON REVIEWER" in py and "MUTABLE DEFAULT" in py                     # the v0.402 text is unchanged
    f = SP.fix_addendum("src/a.cpp:3:5: error: 'x' was not declared in this scope", ["src/a.cpp"])
    assert "CI FIX SPECIALIST" in f and "adapted from ECC's cpp-build-resolver" in f
    assert "KOTLIN fixes" in SP.fix_addendum("e: Money.kt:3 Unresolved reference: pct", ["src/Money.kt"])


# ---------------------------------------------------------------- the agent tool in a real round
class Router:
    """A scripted Claude: the coder's turns in order, and each agent's turns by its name (agents run in threads)."""

    def __init__(self, main, subs):
        self.main, self.subs, self.calls, self.lock = list(main), {k: list(v) for k, v in subs.items()}, [], threading.Lock()
        self.messages = self
        self.threads = set()

    def create(self, **kw):
        with self.lock:
            self.calls.append(kw)
            system = kw["system"][0]["text"]
            if system.startswith("You are a specialist agent"):
                self.threads.add(threading.current_thread().name)
                who = next(k for k in self.subs if f"adapted from ECC's {k}" in system or f"adapted from the agency's {k.replace('-', ' ')}" in system.lower() or f"adapted from The Agency's {k}" in system)
                blocks = self.subs[who].pop(0)
            else:
                blocks = self.main.pop(0)
        if callable(blocks):
            blocks = blocks(kw)
        stop = "tool_use" if any(b.get("type") == "tool_use" for b in blocks) else "end_turn"
        return type("R", (), {"content": blocks, "stop_reason": stop, "model": kw.get("model"), "usage": None})()


def _round(on, monkeypatch, main, subs, tid):  # noqa: F811
    from app.devlab import box
    from app.devsahayak import brain as B
    from app.devsahayak import engine as EN
    if not getattr(box.available, "__name__", "") == "<lambda>":
        monkeypatch.setattr(box, "available", lambda: {"ok": True})     # nothing here runs a command
    events = []

    class Hook:
        def event(self, ev):
            events.append(ev)

        def stopped(self):
            return False

    class G:
        def branch_sha(self, repo, base):
            return on.FAKE.refs["main"]
    B.CLIENT = Router(main, subs)
    t = type("T", (), {"id": tid, "repo": REPO, "base": "main", "model": "", "effort": "", "kind": "fix",
                       "text": "total() crashes on an empty cart"})()
    _, _, ctx, out = EN.run(G(), t, "tok", "", on_step=Hook())
    return B.CLIENT, events, ctx, out


def _sub_turns(path="app/calc.py", report="No real finding: the change is small and correct."):
    return [[tu(91, "read", path=path)], [tu(92, "report", report=report)]]


def test_a_round_hands_work_to_two_agents_at_once_and_passes_the_gate(on, monkeypatch):  # noqa: F811
    seen = {}

    def ask_two(kw):
        seen["tools"] = [x["name"] for x in kw["tools"]]
        seen["system"] = kw["system"][0]["text"]
        return [tu(3, "agent", type="python-reviewer", task="Review the change in app/calc.py: total() no longer divides by len(items)."),
                tu(4, "agent", type="security-reviewer", task="Check app/calc.py for any security problem in the new total() code.")]

    def after_agents(kw):
        res = [b for b in kw["messages"][-1]["content"] if b.get("type") == "tool_result"]
        seen["agent_results"] = [r["content"] for r in res]
        return [tu(5, "done", explain="fixed", pr_title="Fix total")]

    def after_gate(kw):
        seen["gate_note"] = kw["messages"][-1]["content"][0]["content"]
        return [tu(6, "edit", path="app/calc.py", old_string="    breakpoint()\n", new_string="")]
    main = [[tu(1, "read", path="app/calc.py")],
            [tu(2, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    breakpoint()\n    return s\n")],
            ask_two, after_agents, after_gate,
            [tu(7, "done", explain="total() no longer divides", pr_title="Fix total on empty cart", test_plan="-", risk="none")]]
    both = threading.Barrier(2, timeout=20)             # each agent's first step waits for the other: only side by side passes

    def meet(kw):
        both.wait()
        return [tu(91, "read", path="app/calc.py")]
    subs = {n: [meet, [tu(92, "report", report="No real finding: the change is small and correct.")]]
            for n in ("python-reviewer", "security-reviewer")}
    client, events, ctx, out = _round(on, monkeypatch, main, subs, "ecc-round")
    # the coder saw the roster, the rules and the agent tool
    assert "agent" in seen["tools"] and "AGENTS YOU CAN HAND WORK TO" in seen["system"]
    assert "python-reviewer [run]" in seen["system"] and "PYTHON RULES" in seen["system"]
    # both agents ran, in their own threads, with their own tools, and their reports came back
    subs = [c for c in client.calls if c["system"][0]["text"].startswith("You are a specialist agent")]
    assert len(subs) == 4 and not both.broken
    names = {x["name"] for x in subs[0]["tools"]}
    assert "report" in names and "edit" not in names and "write" not in names and "agent" not in names
    assert "Total() no longer divides" not in subs[0]["messages"][0]["content"]          # it sees only its task
    assert all("No real finding" in r for r in seen["agent_results"])
    assert [e["state"] for e in events if e["k"] == "agent"].count("done") == 2
    # the gate stopped the first done (a breakpoint left in), the coder cleaned up, the second done finished
    assert "QUALITY GATE" in seen["gate_note"] and "app/calc.py" in seen["gate_note"]
    assert any(e["k"] == "gate" for e in events)
    assert ctx["found"]["loop"]["finished"] is True
    assert out["files"] and "breakpoint" not in out["files"][0]["content"]


def test_the_gate_only_judges_files_that_would_ship(box, monkeypatch):  # noqa: F811
    """A key file a command planted is hidden and can never be changed by the coder: the gate must not demand it."""
    key = "sk-ant-api03-" + "abcdefghijklmnopqrstuvwxyz0123"
    main = [[tu(1, "bash", command="mkdir -p cfg; python3 -c \"open('cfg/app.ini','w').write('API_KEY = ' + '%s' + chr(10))\"" % key)],
            [tu(2, "read", path="cfg/app.ini"), tu(3, "write", path="ok.md", content="fine\n")],
            [tu(4, "done", explain="Added ok.md.", pr_title="Add ok.md")]]
    client, events, ctx, out = _round(box, monkeypatch, main, {}, "ecc-gate-hidden")
    assert not any(e["k"] == "gate" for e in events) and ctx["found"]["loop"]["finished"] is True
    assert [f["path"] for f in out["files"]] == ["ok.md"] and len(client.calls) == 3


def test_an_edit_agent_reads_first_and_its_reads_are_not_the_coders(on, monkeypatch):  # noqa: F811
    from app.devsahayak import engine as EN
    from app.devsahayak import subagent as SA
    ses = EN.Session("ecc-edit")
    ses.ensure(REPO, on.FAKE.refs["main"], "tok")
    tl = EN.Tools(ses, allow_workflows=False, lab_spec={})
    turns = [[tu(1, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
             [tu(2, "read", path="app/calc.py")],
             [tu(3, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
             [tu(4, "write", path=".github/workflows/x.yml", content="on: push")],
             [tu(5, "report", report="Fixed the divide at app/calc.py:4; ran nothing.")]]
    from app.devsahayak import brain as B
    B.CLIENT = Router([], {"build-error-resolver": turns})
    events = []
    out = SA.run_one(tl, "build-error-resolver", "The empty-cart test fails with ZeroDivisionError in app/calc.py total().",
                     emit=events.append)
    subs = B.CLIENT.calls
    first_result = subs[1]["messages"][-1]["content"][0]["content"]
    assert first_result.startswith("Refused: read")                         # read before edit holds for agents too
    assert subs[4]["messages"][-1]["content"][0]["content"].startswith("Refused")   # workflows stay hers
    assert "return s / len(items)" not in (ses.repo / "app/calc.py").read_text()
    assert "changed 1 file(s)" in out and "Fixed the divide" in out
    assert "app/calc.py" not in tl.read                                     # the coder must still read it itself
    assert any(e.get("by") == "build-error-resolver" and e["k"] == "edit" for e in events)
    assert SA.run_one(tl, "no-such-agent", "x" * 40).startswith("Unknown agent")
    assert SA.run_one(tl, "code-reviewer", "short").startswith("Refused")


def test_the_round_cap_and_the_switch(on, monkeypatch):  # noqa: F811
    from app.config import get_settings
    from app.devsahayak import engine as EN
    from app.devsahayak import subagent as SA
    monkeypatch.setattr(get_settings(), "dev_agent_max", 1, raising=False)
    ses = EN.Session("ecc-cap")
    ses.ensure(REPO, on.FAKE.refs["main"], "tok")
    tl = EN.Tools(ses, allow_workflows=False, lab_spec={})
    from app.devsahayak import brain as B
    B.CLIENT = Router([], {"code-explorer": _sub_turns()})
    calls = [{"id": "a", "input": {"type": "code-explorer", "task": "Map where total() is called and tested."}},
             {"id": "b", "input": {"type": "code-explorer", "task": "Map where total() is called and tested again."}}]
    res = SA.run_many(tl, calls)
    assert "No real finding" in res["a"] and res["b"].startswith("Refused: the agent limit")
    monkeypatch.setattr(get_settings(), "dev_ecc_agents", False, raising=False)
    assert "agent" not in [x["name"] for x in EN.tools_for_round()]
    assert "AGENTS YOU CAN HAND WORK TO" not in EN.ecc_system(["a.py"])


def test_route_and_page():
    from pathlib import Path
    from app.devsahayak import api
    src = Path(api.__file__).read_text()
    assert '@r.get("/agents")' in src and "not_added" in src
    js = (Path(api.__file__).parents[1] / "static" / "console" / "code.js").read_text()
    assert "case 'agent':" in js and "case 'gate':" in js and "by ${esc(s.by)}" in js
    notes = (Path(api.__file__).parents[3] / "THIRD_PARTY_NOTICES.md").read_text()
    assert "v0.794" in notes and "affaan-m/ECC" in notes
