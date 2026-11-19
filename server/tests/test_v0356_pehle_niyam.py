"""v0.356 PEHLE NIYAM (owner: "Always read the project's rules first."). Developer Sahayak reads the repo's own rules before any
work - AGENTS.md / CLAUDE.md / CONTRIBUTING / copilot + cursor rules first and longest, then build / lint / CI files, then a
short README; a folder's own AGENTS.md is shown before anything in that folder is changed (an edit there waits until it has
been read); the PR says which rules were read and how they were followed. Same fake GitHub as the other dev tests."""
import pytest

from tests.test_tech_devsahayak import FIX_ANSWER, TOKEN, T, _join, dev  # noqa: F401
from tests.test_v0350_kadam_ba_kadam import Script, _results, tu

ROOT_RULES = "# Rules for agents\n- Tests live in tests/, named test_<thing>.py, pytest only.\n- Never print(); use logging.\n"
APP_RULES = "# app/ rules\n- Every function in app/ has a one-line docstring.\n"


def _add(fake, files):
    tree = fake.trees[fake.commits[fake.refs["main"]]["tree"]]
    for path, text in files.items():
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": fake._blob(text.encode())})



@pytest.fixture(autouse=True)
def _no_plan_pass(dev, monkeypatch):  # noqa: F811 - after `dev`, so the settings object is the live one
    """v0.451 ECC PHASE 4 added a read-only PLAN pass before the edit loop for standard / large asks. These tests script
    the EDIT loop turn by turn, so the plan pass is off here; it has its own file (test_v0451_plan_pehle.py)."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)

@pytest.fixture
def rdev(dev):  # noqa: F811
    S = dev
    _add(S.FAKE, {"AGENTS.md": ROOT_RULES, "app/AGENTS.md": APP_RULES, ".github/copilot-instructions.md": "Use type hints.\n",
                  "pyproject.toml": "[tool.pytest.ini_options]\ntestpaths = ['tests']\n",
                  "node_modules/x/AGENTS.md": "ignore me\n"})
    _join(S)
    return S


def test_rule_files_are_found_and_sorted():
    from app.devsahayak.loop import rule_paths
    rp = rule_paths(["README.md", "CONTRIBUTING.md", "AGENTS.md", ".cursorrules", ".cursor/rules/style.mdc",
                     ".github/copilot-instructions.md", "docs/CONTRIBUTING.md", "pyproject.toml", "package.json",
                     ".github/workflows/deploy.yml", ".github/workflows/tests.yml", "app/AGENTS.md", "web/CLAUDE.md",
                     "node_modules/pkg/AGENTS.md", "app/agents_helper.py", "src/readme.md"])
    assert rp["rules"][0] == "AGENTS.md" and {"CONTRIBUTING.md", ".cursorrules", ".cursor/rules/style.mdc",
                                              ".github/copilot-instructions.md", "docs/CONTRIBUTING.md"} <= set(rp["rules"])
    assert "pyproject.toml" in rp["build"] and ".github/workflows/tests.yml" in rp["build"]       # how CI tests it
    assert ".github/workflows/deploy.yml" not in rp["build"]
    assert rp["readme"] == ["README.md"] and rp["folders"] == ["app/AGENTS.md", "web/CLAUDE.md"]


def test_rules_come_first_and_a_folder_rule_is_read_before_an_edit_there(rdev, monkeypatch):
    S = rdev
    monkeypatch.setattr(S, "model_json", lambda *a, **k: pytest.fail("the one-shot path must not run"))
    from app.devsahayak import loop as L
    edit = dict(path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")
    script = Script([
        [tu(1, "read_file", path="tests/test_calc.py")],
        [tu(2, "edit_file", **edit)],                                    # not read -> refused
        [tu(3, "read_file", path="app/calc.py")],                        # app/AGENTS.md comes with it
        [tu(4, "edit_file", **edit)],
        [tu(5, "done", explain="len 0 se divide.", pr_title="Fix total", pr_summary="- sum", test_plan="- [ ] pytest",
            rules_followed="- app/AGENTS.md: docstring kept\n- AGENTS.md: test in tests/")],
    ])
    monkeypatch.setattr(L, "BRAIN", script)
    v = S.start(T, "fix", "empty cart crash")
    first = script.seen[0]
    assert first.index('<project_rules path="AGENTS.md">') < first.index('<repo_file path="README.md">')
    assert "Tests live in tests/" in first and "Use type hints" in first and "pyproject.toml" in first
    assert "Folders with their OWN rules" in first and "app/AGENTS.md" in first and "node_modules/x/AGENTS.md" not in first
    assert "Every function in app/" not in first                         # folder rules wait for the folder
    assert "FIRST read the project's own rules" in script.system
    res = _results(script)
    assert "Every function in app/" not in res[0]                        # tests/ is not app/
    assert "This folder has its own rules" in res[2] and "Every function in app/" in res[2]
    assert res[3] == "Edited app/calc.py."
    assert v["status"] == "pr_open"
    body = S.FAKE.prs[1]["body"]
    assert "### Project rules" in body and "`AGENTS.md`" in body and "`app/AGENTS.md`" in body and "docstring kept" in body
    t = S.get_task(T, v["number"])
    assert t["found"]["rules"][:1] == ["AGENTS.md"] and "app/AGENTS.md" in t["found"]["rules"]
    assert "read the folder's rules: app/AGENTS.md" in t["found"]["loop"]["trail"]


def test_an_edit_in_a_rules_folder_waits_until_the_rules_are_read(rdev, monkeypatch):
    S = rdev
    from app.devsahayak import loop as L
    from app.devsahayak.gh import Gh
    g = Gh(TOKEN)
    sha = S.FAKE.refs["main"]
    ws = L.Workspace(g, "meghana/flow-api", sha, [x["path"] for x in g.tree("meghana/flow-api", sha)])
    ws.read.add("app/calc.py")                                           # read without its folder rules (e.g. via search)
    out = ws.edit_file("app/calc.py", "    return s / len(items)\n", "    return s\n")
    assert out.startswith("Not applied yet") and "Every function in app/" in out and not ws.changed()
    assert ws.edit_file("app/calc.py", "    return s / len(items)\n", "    return s\n") == "Edited app/calc.py."
    out = ws.new_file("app/new_mod.py", "x = 1\n")                       # rules already shown once -> no second wait
    assert out == "Created app/new_mod.py."


def test_the_one_shot_path_reads_the_rules_first_too(rdev, monkeypatch):
    S = rdev
    from app.devsahayak import loop as L

    def unavailable(*a, **k):
        raise L.LoopUnavailable("no key")
    monkeypatch.setattr(L, "BRAIN", unavailable)
    seen = []
    monkeypatch.setattr(S, "model_json", lambda system, prompt, **k: seen.append((system, prompt)) or FIX_ANSWER)
    v = S.start(T, "fix", "Checkout crash ho raha hai")
    system, prompt = seen[0]
    assert '<project_rules path="AGENTS.md">' in prompt and "FIRST follow the project's own rules" in system
    assert prompt.index('<project_rules path="AGENTS.md">') < prompt.index('path="app/calc.py"')
    assert v["status"] == "pr_open" and "`AGENTS.md`" in S.FAKE.prs[1]["body"]


def test_a_repo_without_rules_says_so(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    script = Script([[tu(1, "done", explain="kuch nahi")]])
    monkeypatch.setattr(L, "BRAIN", script)
    S.start(T, "explain", "kya hai yeh")
    assert "this repo has no rules file" in script.seen[0]
