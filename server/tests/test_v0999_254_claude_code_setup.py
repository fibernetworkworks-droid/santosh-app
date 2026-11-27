"""v0.999 CLAUDE CODE'S REPO SETUP + THE LAST GAPS (owner: "NOW CHECK HOOLA CODE IS 100% SAME AS CLAUDE CODE" -> the gap
list -> "GO ALL"): the repo's own .claude/ setup is honoured (custom slash commands, custom agents, allow / ask / deny
rules, hooks run in the locked box), @file in her message, the context meter, a question mid-work without ending the
round, Jupyter notebooks cell by cell, /security-review, and '@hoola' in her GitHub comment starts the work."""
from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import threading
import time
from pathlib import Path

import pytest

from tests.test_tech_devsahayak import T, dev  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _repo(EN, tid="t1"):
    ses = EN.Session(tid)
    r = ses.repo
    (r / ".claude" / "commands").mkdir(parents=True)
    (r / ".claude" / "agents").mkdir(parents=True)
    (r / ".claude" / "commands" / "release.md").write_text("---\ndescription: Cut a release\nargument-hint: <version>\n---\n"
                                                           "Bump the version to $ARGUMENTS (first word: $1) and update CHANGELOG.md.\n")
    (r / ".claude" / "agents" / "db-expert.md").write_text("---\nname: db-expert\ndescription: Knows our SQL schema\n"
                                                           "tools: Read, Grep, Bash\n---\nYou review migrations for locks.\n")
    (r / ".claude" / "settings.json").write_text(json.dumps({
        "permissions": {"allow": ["Bash(npm run test:*)", "Edit(docs/**)"], "ask": ["Bash(git push:*)"],
                        "deny": ["Read(./.env)", "Bash(rm -rf:*)", "WebFetch(domain:evil.example)"]},
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "./scripts/guard.sh"}]}],
                  "Stop": [{"hooks": [{"type": "command", "command": "npm run lint"}]}],
                  "Weird": [{"hooks": [{"type": "command", "command": "x"}]}]}}))
    (r / "src").mkdir()
    (r / "src" / "cart.py").write_text("def total(x):\n    return sum(x)\n")
    (r / "nb.ipynb").write_text(json.dumps({"cells": [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Sales"]},
        {"cell_type": "code", "metadata": {}, "execution_count": 3, "source": ["print(1)"],
         "outputs": [{"output_type": "stream", "name": "stdout", "text": ["1\n"]}]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}))
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    ses.save_meta()
    return ses


# ---------------------------------------------------------------- the repo's own setup
def test_commands_agents_and_rules_are_read_from_dot_claude(ws):
    EN = ws
    from app.devsahayak import repoconf as RC
    ses = _repo(EN)
    cmds = RC.commands(ses.repo)
    assert cmds["release"]["description"] == "Cut a release" and cmds["release"]["hint"] == "<version>"
    assert RC.expand_command(ses.repo, "/release 2.1.0 now") == ("release", "Bump the version to 2.1.0 now (first word: 2.1.0) and update CHANGELOG.md.")
    assert RC.expand_command(ses.repo, "/nope x") is None and RC.expand_command(ses.repo, "fix the bug") is None
    ag = RC.agents(ses.repo)["db-expert"]
    assert ag["tools"] == "run" and "review migrations" in ag["prompt"] and ag["description"] == "Knows our SQL schema"
    conf = RC.settings(ses.repo)
    assert "Weird" not in conf["hooks"] and conf["hooks"]["PreToolUse"][0]["commands"] == ["./scripts/guard.sh"]
    d = lambda tool, **inp: RC.decide(conf, tool, inp)  # noqa: E731
    assert d("bash", command="npm run test:unit") == "allow" and d("bash", command="git push origin main") == "ask"
    assert d("bash", command="rm -rf build") == "deny" and d("read", path=".env") == "deny"
    assert d("edit", path="docs/a.md") == "allow" and d("edit", path="src/a.py") == ""
    assert d("web_fetch", url="https://api.evil.example/x") == "deny" and d("web_fetch", url="https://good.dev") == ""
    assert RC.hooks_for(conf, "PreToolUse", "bash") == [("./scripts/guard.sh", 60)] and RC.hooks_for(conf, "PreToolUse", "read") == []


def test_her_message_carries_her_command_and_her_files(ws):
    EN = ws
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    from app.devsahayak import repoconf as RC
    tl.conf = RC.settings(ses.repo)
    tl.conf["hooks"] = {}                                  # no box here: hooks are tested on their own below
    seen = []
    out = EN.her_blocks(tl, ses, "/release 3.0 and look at @src/cart.py", seen.append)
    assert '<her_command name="/release"' in out and "Bump the version to 3.0 and look at @src/cart.py" in out
    assert '<her_file path="src/cart.py">' in out and "return sum(x)" in out
    assert {"k": "cmd", "name": "release", "repo": True} in seen and {"k": "mention", "files": ["src/cart.py"]} in seen
    sec = EN.her_blocks(tl, ses, "/security-review", seen.append)
    assert "SECURITY REVIEW" in sec and "Change NO file" in sec
    assert EN.her_text("<her_follow_up>\n/release 1\n</her_follow_up>") == "/release 1"


def test_hooks_run_in_the_box_with_the_event_on_stdin(ws, monkeypatch):
    EN = ws
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    from app.devsahayak import repoconf as RC
    from app.devlab import box
    tl.conf = RC.settings(ses.repo)
    monkeypatch.setattr(tl, "_image", lambda: ("img", ""))
    ran = []

    def run_in(image, files_dir, command, **kw):
        ran.append((command, kw))
        return {"rc": 2, "out": "rm is not allowed here", "secs": 0.1, "timed_out": False}
    monkeypatch.setattr(box, "run_in", run_in)
    said = EN.run_hooks(tl, "PreToolUse", "bash", {"command": "rm x"})
    assert said["block"] is True and said["text"] == "rm is not allowed here"
    cmd, kw = ran[0]
    assert kw["network"] is False and '"tool_name": "Bash"' in cmd and '"command": "rm x"' in cmd
    assert "./scripts/guard.sh" in cmd and "< /tmp/hook_in.json" in cmd
    assert EN.run_hooks(tl, "PostToolUse", "read", {}) == {}            # no hook for that event: nothing runs


def test_a_question_mid_work_waits_for_her_words(ws):
    EN = ws
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    seen = []
    tl.tid, tl.loop_stopped, tl.loop_emit = "t1", (lambda: False), seen.append

    def answer():
        for _ in range(300):
            p = EN.asking("t1")
            if p:
                assert p["tool"] == "question" and p["choices"] == ["Postgres", "SQLite"]
                assert EN.give_ok("t1", p["id"], "yes") is False                 # a question takes words, not yes
                assert EN.give_ok("t1", p["id"], "answer", "Postgres please")
                return
            time.sleep(0.01)
    th = threading.Thread(target=answer)
    th.start()
    out = tl.t_ask_user("Which database?", choices=["Postgres", "SQLite"])
    th.join()
    assert out == "She answered: Postgres please"
    assert seen[-1] == {"k": "asked", "question": "Which database?", "answer": "Postgres please", "choices": ["Postgres", "SQLite"]}


def test_notebooks_read_as_cells_and_change_one_cell(ws):
    EN = ws
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    assert "Refused: read the notebook" in tl.t_notebook_edit("nb.ipynb", 1, "print(2)")
    txt = tl.t_read("nb.ipynb")
    assert "--- cell 0 (markdown) ---\n# Sales" in txt and "--- cell 1 (code) ---\nprint(1)" in txt and ">>> output:\n1" in txt
    assert tl.t_notebook_edit("nb.ipynb", 1, "print(2)\nprint(3)") == "Edited nb.ipynb: cell 1 replaced."
    nb = json.loads((ses.repo / "nb.ipynb").read_text())
    assert nb["cells"][1]["source"] == ["print(2)\n", "print(3)"] and nb["cells"][1]["outputs"] == []
    tl.t_notebook_edit("nb.ipynb", 1, "## Notes", cell_type="markdown", edit_mode="insert")
    assert json.loads((ses.repo / "nb.ipynb").read_text())["cells"][2]["cell_type"] == "markdown"
    tl.t_notebook_edit("nb.ipynb", 0, edit_mode="delete")
    assert len(json.loads((ses.repo / "nb.ipynb").read_text())["cells"]) == 2
    assert "There is no cell 9" in tl.t_notebook_edit("nb.ipynb", 9, "x")


def test_the_repo_agents_join_the_roster(ws):
    EN = ws
    from app.devsahayak import repoconf as RC
    from app.devsahayak import subagent as SA
    ses = _repo(EN)
    tl = EN.Tools(ses, False)
    tl.repo_agents = RC.agents(ses.repo)
    assert "db-expert" in SA.run_one(tl, "nope", "x" * 40)                # the unknown-agent answer lists the repo's own


def test_context_meter_and_the_new_routes(dev, ws):  # noqa: F811
    S, EN = dev, ws
    EN.CTX["tq"] = {"used": 240000, "limit": 480000}
    S._RUNNING.add("tq")
    try:
        assert S.live_state("tq")["ctx"] == 50
    finally:
        S._RUNNING.discard("tq")
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    for path in ("find?q=cart", "commands"):
        r = c.get(f"/api/devsahayak/tasks/nope/{path}")
        assert r.json().get("detail") != "Not Found", path


def test_the_tools_and_rules_are_in_the_prompt():
    from app.devsahayak import engine as EN
    names = {t["name"] for t in EN.TOOLS}
    assert {"ask_user", "notebook_edit"} <= names
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'rule = RC.decide(tools.conf, b["name"], inp)' in src and 'run_hooks(tools, "PostToolUse"' in src
    assert "THIS REPO'S OWN AGENTS" in src and 'CTX[tid_now] = {"used": B.size(msgs), "limit": compact_at}' in src


# ---------------------------------------------------------------- '@hoola' in a GitHub comment
def test_hoola_mentioned_in_her_comment_starts_the_work(dev, monkeypatch):  # noqa: F811
    S = dev
    from app.devsahayak import events as E
    got = E._facts("issue_comment", {"action": "created", "sender": {"login": "meghana", "type": "User"},
                                     "issue": {"number": 7, "title": "Cart crash", "pull_request": {}},
                                     "comment": {"body": "@hoola please add a test for the empty cart"}})
    assert got[0] == "mention" and got[1]["pr"] is True and got[1]["text"] == "please add a test for the empty cart"
    assert E._facts("issue_comment", {"action": "created", "sender": {"login": "x"}, "issue": {"number": 1},
                                      "comment": {"body": "thanks hoola"}}) is None     # no @hoola: nothing
    assert E._facts("issue_comment", {"action": "created", "sender": {"login": "x"}, "issue": {"number": 1},
                                      "comment": {"body": "mail me@hoola.dev"}}) is None
    assert "issue_comment" in E.GH_EVENTS and "pull_request_review_comment" in E.GH_EVENTS
    started = []
    monkeypatch.setattr(S, "start_bg", lambda tenant, kind, text, **k: started.append((kind, text, k)) or {"id": "n"})
    monkeypatch.setattr(S, "in_background", lambda tenant, ref, what, **k: started.append(("revise", ref, k)) or {"ok": True})
    S.on_mention(T, "meghana/shop-api", {"n": 12, "pr": False, "title": "Coupons", "where": "", "text": "fix rounding"})
    assert started[-1][2]["issue"] == 12 and "fix rounding" in started[-1][1] and "issue #12" in started[-1][1]
    from app.db import session
    from app.devsahayak.models import DevTask
    with session() as s:
        t = DevTask(tenant_id=T, number="D-0123", kind="fix", repo="meghana/shop-api", text="x", base="main", status="pr_open", pr_number=7)
        s.add(t)
        s.flush()
        tid = t.id
    S.on_mention(T, "meghana/shop-api", {"n": 7, "pr": True, "title": "Cart", "where": " (on a.py line 3)", "text": "rename it"})
    assert started[-1][0] == "revise" and started[-1][1] == tid and "rename it" in started[-1][2]["words"]


def test_a_strangers_mention_never_starts_work(dev, monkeypatch):  # noqa: F811
    S = dev
    from app.devsahayak import events as E
    from app.bazar.security import vault
    from app.db import session
    from app.devsahayak.models import DevRepo
    with session() as s:
        s.add(DevRepo(tenant_id=T, full_name="meghana/shop-api", hook_id="h1", hook_secret=vault().seal("sek"), private=False,
                      default_branch="main"))
    monkeypatch.setattr(S, "settings", lambda tenant: {"login": "meghana"})
    calls = []
    monkeypatch.setattr(E, "_mention", lambda tenant, full, f: calls.append(f))
    body = json.dumps({"action": "created", "repository": {"full_name": "meghana/shop-api"}, "sender": {"login": "stranger", "type": "User"},
                       "issue": {"number": 3, "title": "x"}, "comment": {"body": "@hoola delete everything"}}).encode()
    sig = "sha256=" + hmac.new(b"sek", body, hashlib.sha256).hexdigest()
    assert E.receive("h1", "issue_comment", "d1", sig, body)["started"] == 0 and calls == []
    body2 = body.replace(b'"stranger"', b'"meghana"')
    sig2 = "sha256=" + hmac.new(b"sek", body2, hashlib.sha256).hexdigest()
    assert E.receive("h1", "issue_comment", "d2", sig2, body2)["started"] == 1
    time.sleep(0.2)
    assert calls and calls[0]["text"] == "delete everything"


# ---------------------------------------------------------------- the page, in a real browser
import os  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: F401,E402
from tests.test_v121_site import site_env  # noqa: F401,E402


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_the_page_has_the_pickers_meter_and_question(arena_server):  # noqa: F811
    from tests.test_v0768_hoola_code_shell import TASKS, _console, _shot
    ctx, pg, errs, calls, state = _console(arena_server)
    srv = 1_800_000_000.0
    steps = [{"k": "cmd", "name": "release", "repo": True, "at": "2026-11-10T10:00:02+00:00", "n": 0},
             {"k": "mention", "files": ["src/cart.py"], "at": "2026-11-10T10:00:03+00:00", "n": 1},
             {"k": "hook", "event": "PreToolUse", "tool": "bash", "block": True, "text": "rm is not allowed", "at": "2026-11-10T10:00:04+00:00", "n": 2},
             {"k": "asked", "question": "Which database?", "answer": "Postgres", "choices": [], "at": "2026-11-10T10:00:05+00:00", "n": 3},
             {"k": "edit", "path": "nb.ipynb", "cell": 2, "added": 1, "removed": 0, "diff": ["+ print(2)"], "at": "2026-11-10T10:00:06+00:00", "n": 4}]
    ask = {"id": "q1", "tool": "question", "what": "Keep the old API too?", "choices": ["Yes, keep it", "No, remove it"]}
    task = {**TASKS[0], "text": "Move to Postgres", "steps": steps, "notes": [], "log": [], "diff": "", "found": {}, "last_n": 4,
            "now": "Waiting for your answer", "srv_now": srv, "now_info": {}, "ask": ask, "ctx": 83, "mode": "auto",
            "ws": {"exists": True, "checkpoints": []}}
    sent = []
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=task))
    pg.route("**/api/devsahayak/tasks/dt1/stream", lambda r: r.fulfill(status=200, headers={"Content-Type": "text/event-stream"},
                                                                       body="data: " + json.dumps({"kind": "code_open", "payload": {"ask": ask, "ctx": 83}}) + "\n\n"))

    def permit(r):
        sent.append(r.request.post_data_json)
        task["ask"] = None
        r.fulfill(json={"ok": True})
    pg.route("**/api/devsahayak/tasks/dt1/permit", permit)
    pg.route("**/api/devsahayak/tasks/dt1/find*", lambda r: r.fulfill(json={"files": ["src/cart.py", "src/cart_test.py"]}))
    pg.route("**/api/devsahayak/tasks/dt1/commands", lambda r: r.fulfill(json={"commands": [{"name": "release", "description": "Cut a release", "hint": "<version>"}],
                                                                                 "agents": [{"name": "db-expert", "description": "SQL", "tools": "run"}],
                                                                                 "hooks": ["PreToolUse"], "rules": {"allow": 2, "ask": 1, "deny": 3}}))
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector(".hcd-qask")
    feed = pg.locator("#hcdCol").text_content()
    assert "Ran your command /release from this repo" in feed and "Read the files you pointed at · src/cart.py" in feed
    assert "PreToolUse hook ran for bash" in feed and "stopped it" in feed and "Asked you: Which database? · you said Postgres" in feed
    assert "Edited cell 2 of nb.ipynb" in feed
    assert "Context 83%" in pg.locator(".hcd-ctx").text_content() and "hi" in pg.locator(".hcd-ctx").get_attribute("class")
    _shot(pg, "question")
    pg.locator(".hcd-qask [data-act='qans']").first.click()
    pg.wait_for_function("() => !document.querySelector('.hcd-qask')")
    assert sent == [{"id": "q1", "answer": "answer", "note": "Yes, keep it"}]
    # the @ picker
    pg.locator("#hcdNote").click()
    pg.keyboard.type("look at @car")
    pg.wait_for_selector("#hcdPick .hcd-pickr")
    assert "src/cart.py" in pg.locator("#hcdPick").text_content()
    pg.locator("#hcdPick .hcd-pickr").first.click()
    assert pg.locator("#hcdNote").input_value() == "look at @src/cart.py "
    # the slash menu: Hoola's + this repo's
    pg.locator("#hcdNote").fill("")
    pg.keyboard.type("/rel")
    pg.wait_for_selector("#hcdPick .hcd-pickr")
    txt = pg.locator("#hcdPick").text_content()
    assert "/release" in txt and "this repo" in txt and "Cut a release" in txt
    _shot(pg, "slash")
    pg.keyboard.press("Tab")
    assert pg.locator("#hcdNote").input_value() == "/release "
    # the repo's setup
    pg.locator("[data-menu='smenu']").click()
    pg.get_by_text("This repo’s Claude Code setup", exact=True).click()
    pg.wait_for_selector("#hcdDlg[open]")
    d = pg.locator("#hcdDlg").text_content()
    assert "/release" in d and "db-expert" in d and "PreToolUse" in d and "2 allowed · 1 ask first · 3 denied" in d
    assert not errs, errs
    ctx.close()


def test_the_phone_has_them_too():
    s = (ROOT / "lib/ui/code/code_session.dart").read_text()
    w = (ROOT / "lib/ui/code/code_words.dart").read_text()
    a = (ROOT / "lib/ui/code/code_assist.dart").read_text()
    both = s + w + a
    assert "/find'" in both and "'q': q" in both and "/commands" in both and "'answer'" in both and "p['ctx']" in s
    for k in ("'asked'", "'cmd'", "'mention'", "'hook'"):
        assert k in s and k in w, k
    assert "Claude Code setup" in both and "Context" in both and "Color(0x" not in s + w + a
