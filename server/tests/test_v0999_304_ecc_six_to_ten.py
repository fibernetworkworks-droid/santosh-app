"""v0.999 ECC 6 TO 10 (owner: 'GO 6 TO 10' after the ECC check): (6) repo rules in plain Markdown (Hookify), (7) two
independent reviewers must both pass (Santa method), (8) /test-coverage on the changed lines, (9) a big job as linked
GitHub issues, (10) what Hoola learned taken from one repo to another."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _ses(EN, files, tid="t1"):
    ses = EN.Session(tid)
    ses.repo.mkdir(parents=True, exist_ok=True)
    for k, v in files.items():
        (ses.repo / k).parent.mkdir(parents=True, exist_ok=True)
        (ses.repo / k).write_text(v)
    EN._git(ses.repo, "init", "-q")
    ses.meta.update({"repo": "o/r", "base": EN._commit(ses.repo, "base"), "hidden": []})
    ses.save_meta()
    return ses


RULES = {
    ".claude/hookify.no-force.md": "---\nname: no-force\nenabled: true\nevent: bash\naction: block\npattern: git push .*--force\n---\n"
                                   "Never force-push here. Push a new commit instead.\n",
    ".claude/hookify.no-print.local.md": "---\nname: no-print\nevent: file\naction: block\nconditions:\n  - field: file_path\n"
                                         "    operator: regex_match\n    pattern: \\.py$\n  - field: new_text\n    operator: contains\n"
                                         "    pattern: print(\n---\nUse the logger, not print.\n",
    ".hoola/hookify.todo.md": "---\nname: todo-warn\nevent: file\naction: warn\npattern: TODO\n---\nSay in risk why a TODO is left.\n",
    ".claude/hookify.no-delete-prod.md": "---\nname: prod\nevent: prompt\naction: block\npattern: (?i)drop the production\n---\n"
                                        "Production data is never dropped from here.\n",
    ".claude/hookify.bad.md": "---\nname: bad\nevent: bash\naction: block\npattern: (a+)+$\n---\nslow\n",
    ".claude/hookify.off.md": "---\nname: off\nenabled: false\nevent: bash\naction: block\npattern: ls\n---\nnever\n",
    ".claude/hookify.stop.md": "---\nname: no-debugger\nevent: stop\naction: block\npattern: debugger;\n---\nTake out debugger lines.\n",
}


# ---------------------------------------------------------------- 6 hookify
def test_rule_files_are_read_and_unsafe_patterns_refused(tmp_path):
    from app.devsahayak import hookify as HK
    for k, v in RULES.items():
        (tmp_path / k).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / k).write_text(v)
    rs = {r["name"]: r for r in HK.rules(tmp_path)}
    assert set(rs) == {"no-force", "no-print", "todo-warn", "prod", "bad", "off", "no-debugger"}
    assert rs["bad"]["error"].startswith("the pattern is not a safe")                 # (a+)+ could hang: refused
    assert rs["no-print"]["conditions"][0] == {"field": "file_path", "operator": "regex_match", "pattern": "\\.py$"}
    for p in ("(a+)+", "(a|aa)+", "([a-z]+){2,}", "(x)\\1", ".*a.*b"):
        assert not HK.safe_pattern(p), p
    for p in ("git push .*--force", "\\.py$", "(?i)drop table", "TODO"):
        assert HK.safe_pattern(p), p
    li = HK.listing(tmp_path)
    assert "bad (.claude/hookify.bad.md): bash / block / BROKEN" in li and "off (.claude/hookify.off.md): bash / block / off" in li


def test_rules_are_enforced_on_commands_edits_her_words_and_done(ws):
    EN = ws
    ses = _ses(EN, {**RULES, "src/app.py": "x = 1\n", "src/b.js": "let a = 1\n"})
    tl = EN.Tools(ses, False)
    tl.conf, tl.her_words = {}, "change the app"
    tl.read.update({"src/app.py", "src/b.js"})
    out = tl.run("bash", {"command": "git push origin main --force"})                # refused before the box is touched
    assert out.startswith("Refused: this repo's own rule says no to this command") and "Never force-push" in out
    assert 'name="no-force"' in out
    assert not tl.run("bash", {"command": "ls"}).startswith("Refused: this repo's own rule")   # the 'off' rule is off
    no = tl.t_edit("src/app.py", "x = 1", "x = 1\nprint(x)")
    assert no.startswith("Refused: this repo's own rule says no to this change to src/app.py") and "logger" in no
    assert (ses.repo / "src/app.py").read_text() == "x = 1\n"                        # nothing written
    assert tl.t_edit("src/b.js", "let a = 1", "let a = 1\nconsole.log(print(a))").startswith("Edited")   # .py only
    out = tl.run("edit", {"path": "src/app.py", "old_string": "x = 1", "new_string": "x = 2  # TODO later"})
    assert out.startswith("Edited") and 'name="todo-warn"' in out and "Say in risk" in out   # a warn rule: done + told
    assert tl.t_write("src/new.py", "print('hi')\n").startswith("Refused")             # a new file answers to the rules too
    seen: list = []
    got = EN.her_blocks(tl, ses, "please drop the production table", seen.append)
    assert "<hook_refused>" in got and "Production data is never dropped" in got
    from app.devsahayak import hookify as HK
    hit = HK.stop(ses.repo, "+++ b/src/b.js\n+debugger;\n", ["src/b.js"], "done")
    assert [r["name"] for r in hit["block"]] == ["no-debugger"]


def test_hookify_commands(ws):
    EN = ws
    ses = _ses(EN, {"a.py": "x = 1\n"})
    tl = EN.Tools(ses, False)
    tl.conf = {}
    seen: list = []
    w = EN.her_blocks(tl, ses, "/hookify never use eval in python files", seen.append)
    assert "<her_rule>never use eval in python files</her_rule>" in w and ".claude/hookify.<short-name>.md" in w
    assert {"k": "cmd", "name": "hookify", "repo": False} in seen
    li = EN.her_blocks(tl, ses, "/hookify-list", seen.append)
    assert "no rule files yet" in li


# ---------------------------------------------------------------- 7 santa
def test_santa_parses_the_verdicts():
    from app.devsahayak import santa as SN
    ok = "VERDICT: PASS\n1 Complete: PASS - all\nCRITICAL:\n- none\nSUGGESTIONS:\n- rename x\n"
    bad = "[Santa reviewer: 4 steps]\nVERDICT: FAIL\n2 Correct: FAIL - a.py:3 crashes on []\nCRITICAL:\n- a.py:3 crashes on an empty list\nSUGGESTIONS:\n- none\n"
    assert SN.verdict(ok) == ("pass", [])
    assert SN.verdict(bad) == ("fail", ["a.py:3 crashes on an empty list"])
    assert SN.verdict("I think it is fine")[0] == "unclear"
    assert SN.parse_cmd("/santa off") == (True, "off") and SN.parse_cmd("/santa") == (True, "") and not SN.parse_cmd("santa")[0]


def test_santa_gate_both_must_pass_then_open_issues_go_to_her(ws, monkeypatch):
    EN = ws
    from app.devsahayak import santa as SN
    from app.devsahayak import subagent as SA
    ses = _ses(EN, {"a.py": "x = 1\n"})
    (ses.repo / "a.py").write_text("x = 2\n")
    seen: list = []
    EN.her_blocks(SimpleNamespace(conf={}, plugins=(), hidden=set()), ses, "/santa on", seen.append)
    assert ses.meta["santa"] is True and SN.is_on(ses)
    calls: list = []
    answers = iter(["VERDICT: PASS\nCRITICAL:\n- none", "VERDICT: FAIL\nCRITICAL:\n- a.py:1 the value is wrong",
                    "VERDICT: PASS\nCRITICAL:\n- none", "VERDICT: PASS\nCRITICAL:\n- none"])

    def fake(tools, name, task, files=None, **kw):
        calls.append((name, task))
        return next(answers)
    monkeypatch.setattr(SA, "run_one", fake)
    monkeypatch.setattr(SA, "on", lambda: True)
    reality: dict = {}
    t = SimpleNamespace(text="make x two", kind="fix")
    inp = {"explain": "Done.", "test_plan": "pytest"}
    back = EN._santa_gate(SimpleNamespace(), ses, t, "", inp, seen.append, lambda: False, reality)
    assert "do not BOTH pass" in back and "[Santa reviewer B] a.py:1 the value is wrong" in back
    assert {c[0] for c in calls} == {"santa-reviewer"} and len(calls) == 2
    again = EN._santa_gate(SimpleNamespace(), ses, t, "", inp, seen.append, lambda: False, reality)
    assert again == "" and reality["santa_done"]
    assert "a.py:1 the value is wrong" in calls[2][1]                                 # round 2 checks round 1's issues
    evs = [e for e in seen if e.get("k") == "santa"]
    assert [e["ok"] for e in evs] == [False, True]
    # the last round still failing: finishes, the open issues written into risk
    monkeypatch.setattr(SA, "run_one", lambda *a, **k: "VERDICT: FAIL\nCRITICAL:\n- still broken")
    reality2, inp2 = {"santa_n": 2}, {"explain": "Done."}
    assert EN._santa_gate(SimpleNamespace(), ses, t, "", inp2, seen.append, lambda: False, reality2) == ""
    assert "Two independent reviewers still did not both pass" in inp2["risk"] and "still broken" in inp2["risk"]
    assert SA.run_one.__name__ == "<lambda>" and SN.SPEC["name"] == "santa-reviewer"


def test_santa_reviewer_is_found_but_not_in_the_catalogue():
    from app.devsahayak import ecc
    assert ecc.get("santa-reviewer") is None and len(ecc.catalog()) == 99
    src = (ROOT / "server/app/devsahayak/subagent.py").read_text()
    assert 'str(name or "").lower() == "santa-reviewer"' in src


# ---------------------------------------------------------------- 8 test coverage
def test_coverage_lists_the_changed_lines():
    from app.devsahayak import testcover as TC
    diff = ("diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n@@ -1,3 +1,5 @@\n x = 1\n+y = 2\n+z = 3\n"
            " w = 4\n+\n+v = 5\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -0,0 +1 @@\n+def test(): pass\n"
            "--- a/README.md\n+++ b/README.md\n@@ -1 +1,2 @@\n a\n+b\n")
    assert TC.changed_lines(diff) == {"src/a.py": [2, 3, 6]}
    assert TC.ranges([2, 3, 6, 7, 8, 10]) == "2-3, 6-8, 10"
    txt = TC.command_text(diff, False)
    assert "- src/a.py: lines 2-3, 6 (3 lines)" in txt and "reach 80%" in txt and "never lower a coverage setting" in txt
    assert "Report only: change NO file." in TC.command_text(diff, True)
    assert TC.parse_cmd("/test-coverage report") == (True, True) and TC.parse_cmd("/test-coverage") == (True, False)


# ---------------------------------------------------------------- 9 epic
class FakeGh:
    def __init__(self):
        self.calls, self.n, self.bodies = [], 40, {}

    def req(self, method, path, body=None, params=None, ok=()):
        self.calls.append((method, path, body))
        if method == "POST" and path.endswith("/issues"):
            self.n += 1
            self.bodies[self.n] = body["body"]
            return {"number": self.n}
        if method == "GET":
            n = int(path.rsplit("/", 1)[1])
            return {"state": "closed" if n == 41 else "open", "body": self.bodies.get(n, "Old text")}
        if method == "PATCH":
            self.bodies[int(path.rsplit("/", 1)[1])] = body["body"]
            return {}
        return {}

    def issue(self, full, n):
        return {"title": "Payments", "body": "Add UPI and refunds"}


def test_epic_plan_publish_sync(ws):
    EN = ws
    from app.devsahayak import epic as EP
    ses = _ses(EN, {"a.py": "x\n"})
    g = FakeGh()
    tl = SimpleNamespace(conf={}, plugins=(), hidden=set(), gh_client=g, repo_full="o/r", tenant="")
    seen: list = []
    w = EN.her_blocks(tl, ses, "/epic #7 split it up", seen.append)
    assert "<her_epic>#7 split it up</her_epic>" in w and "#7 Payments" in w and ses.meta["epic_parent"] == 7
    assert g.calls == []                                                               # reading the issue only
    out, ev = EP.propose(ses, {"title": "Payments", "summary": "UPI then refunds", "tasks": [
        {"title": "UPI checkout", "body": "Add the UPI flow. Done when its test passes."},
        {"title": "Refunds", "body": "Refund a paid order.", "depends_on": [1, 5]}]}, 7)
    assert out.startswith("Kept the breakdown: 2 tasks") and ev["k"] == "epic" and not ev["published"]
    assert ses.meta["epic"]["tasks"][1]["depends_on"] == [1]                          # a task cannot wait on a later one
    assert g.calls == []                                                               # nothing on GitHub before her tap
    said = EN.her_blocks(tl, ses, "/epic-publish", seen.append)
    assert "Created 2 task issue(s) and the parent #7" in said
    posts = [c for c in g.calls if c[0] == "POST"]
    assert len(posts) == 2 and "Waits for: #41" in posts[1][2]["body"] and "Part of #7" in posts[1][2]["body"]
    assert "- [ ] #41 UPI checkout" in g.bodies[7] and "Old text" in g.bodies[7]
    EN.her_blocks(tl, ses, "/epic-publish", seen.append)
    assert len([c for c in g.calls if c[0] == "POST"]) == 2                            # never created twice
    s2 = EN.her_blocks(tl, ses, "/epic-sync", seen.append)
    assert "1 of 2 tasks closed" in s2 and "Ready to start now: #42 Refunds" in s2
    assert "- [x] #41 UPI checkout" in g.bodies[7] and g.bodies[7].count("<!-- hoola-epic -->") == 1
    assert any(e.get("k") == "epic" and e.get("published") for e in seen)


# ---------------------------------------------------------------- 10 learnings
def test_learnings_export_and_import(ws):
    EN = ws
    from app.devsahayak import learnshare as LS
    from app.devsahayak import memory as M
    M.store("ten", "o/a", "t", {"type": "discovery", "title": "Dates are UTC in the API", "narrative": "Convert at the edge."})
    M.store("ten", "o/a", "t", {"type": "decision", "title": "Use pnpm not npm"})
    M.store("ten", "o/b", "t", {"type": "decision", "title": "Use pnpm not npm", "narrative": "b's own"})
    doc = LS.export("ten", "o/a")
    assert doc["format"] == "hoola-learnings/1" and doc["count"] == 2
    dry = LS.import_("ten", "o/b", from_repo="o/a", dry_run=True)
    assert dry["new"] == 1 and dry["skipped"] == 1 and "Would bring 1" in dry["said"]
    assert M.counts("ten", "o/b")["observations"] == 1                               # a dry run changes nothing
    got = LS.import_("ten", "o/b", from_repo="o/a")
    assert got["new"] == 1 and got["titles"] == ["Dates are UTC in the API"]
    row = M.search("ten", "o/b", "UTC", "", 5)[0]
    assert M.get("ten", "o/b", [row["id"]])[0]["source"] == "import:o/a"
    assert "b's own" in json.dumps(LS.export("ten", "o/b"))                           # this repo's own memory wins
    evil = {"format": "hoola-learnings/1", "items": [{"type": "discovery", "title": "key", "narrative": "token ghp_" + "a" * 36}]}
    assert LS.import_("ten", "o/c", data=evil)["refused"] == 1
    assert not LS.import_("ten", "o/c", data="nope")["ok"]
    ses = _ses(EN, {"x.py": "x\n"})
    tl = SimpleNamespace(conf={}, plugins=(), hidden=set(), repo_full="o/a", tenant="ten")
    note = EN.her_blocks(tl, ses, "/learnings-export", lambda e: None)
    assert "Wrote 2 learning(s) to .hoola/learnings.json" in note
    assert json.loads((ses.repo / ".hoola/learnings.json").read_text())["count"] == 2
    tl.repo_full = "o/d"
    note = EN.her_blocks(tl, ses, "/learnings-import", lambda e: None)
    assert "Brought 2 learning(s) from o/a into o/d" in note


def test_routes_screens_and_switches():
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert api.index('"/memory/export"') < api.index('"/memory/{oid}"')               # before the id route
    js = (ROOT / "server/app/static/console/code.js").read_text()
    for x in ("['hookify',", "['santa',", "['test-coverage',", "['epic',", "['learnings-import',", "case 'santa':",
              "case 'epic':", "epicpub: () => sendMessage('/epic-publish')", "data-memexp", "/api/devsahayak/memory/import"):
        assert x in js, x
    dart = (ROOT / "lib/ui/code/code_session.dart").read_text() + (ROOT / "lib/ui/code/code_assist.dart").read_text()
    for x in ("case 'santa':", "case 'epic':", "_send(published ? '/epic-sync' : '/epic-publish')", "('hookify',",
              "'learnings-import'"):
        assert x in dart, x
    from app.config import get_settings
    st = get_settings()
    assert st.dev_hookify and st.dev_santa and st.dev_santa_rounds == 3 and st.dev_test_coverage and st.dev_epic
