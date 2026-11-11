"""HOOLA CODE PHASE 2 (docs/HOOLA_CODE_WEB_PLAN.md; owner: "GO PHASE 2"): review and the pull request. The Changes pane
beside the chat (file by file, line numbers, Compare against a branch), her comments on lines that QUEUE and ride her
next message, Hoola's one question answered in the same session, the own review with "Fix this one", Auto-fix switched
off for one pull request, a merged session archived by itself. Server first, then the page in a real browser."""
import os
import time

import httpx
import pytest

from tests.test_tech_devsahayak import FIX_ANSWER, REPO, T, _join, dev  # noqa: F401
from tests.test_v0352_pehle_ci import _run, cidev  # noqa: F401
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401


@pytest.fixture(autouse=True)
def _no_plan_pass(dev, monkeypatch):  # noqa: F811
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)


def _wait(S, tid, cond, s=10.0):
    end = time.time() + s
    while time.time() < end:
        t = S.get_task(T, tid)
        if cond(t):
            return t
        time.sleep(0.05)
    return S.get_task(T, tid)


def test_her_line_comments_ride_the_next_message(cidev, monkeypatch):  # noqa: F811
    S = cidev
    v = S.start(T, "fix", "Checkout crash ho raha hai")
    _run(S.FAKE, S.FAKE.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])                                                          # CI green: the PR is open for her review
    full = S.get_task(T, v["id"])
    assert full["status"] == "pr_open"
    fd = full["file_diffs"]
    assert fd and fd[0]["path"] and "@@" in fd[0]["diff"] and {"added", "removed", "new", "why"} <= set(fd[0])   # the pane, file by file
    seen = []
    monkeypatch.setattr(S, "model_json", lambda system, prompt, *a, **k: seen.append(prompt) or FIX_ANSWER)
    comments = [{"path": "app/calc.py", "line": 5, "code": "    return s", "text": "Guard the empty cart too"},
                {"path": "app/calc.py", "line": 0, "code": "", "text": "api_key = sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123"},
                {"path": "", "line": 3, "text": "no file = dropped"}, "not a comment"]
    S.revise(T, v["id"], "", comments=comments)                                    # comments alone are a message
    p = seen[-1]
    assert "<her_comments_on_the_diff>" in p and '<comment file="app/calc.py" line="5">' in p
    assert "on this line: return s" in p and "Guard the empty cart too" in p
    assert "sk-ant-api03" not in p and "no file = dropped" not in p                # scrubbed like any text of hers
    with pytest.raises(S.DevError, match="comment on a line"):
        S.revise(T, v["id"], "   ", comments=[])
    assert S._comments_block([{"path": "a.py", "line": 1, "text": "x"}] * 40).count("<comment ") == 20


def test_a_note_while_it_works_carries_her_comments(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    from tests.test_v0350_kadam_ba_kadam import tu
    gate = {"go": False}

    def brain(system, messages, tools):
        while not gate["go"]:
            time.sleep(0.02)
        return [tu(1, "list_dir", path="")], "tool_use"
    monkeypatch.setattr(L, "BRAIN", brain)
    v = S.start_bg(T, "fix", "ZeroDivisionError in total()")
    try:
        S.add_note(T, v["id"], "", comments=[{"path": "app/calc.py", "line": 5, "code": "return s", "text": "use Decimal here"}])
        note = S.get_task(T, v["id"])["notes"][0]
        assert "<her_comments_on_the_diff>" in note and "use Decimal here" in note and 'line="5"' in note
    finally:
        S.stop(T, v["id"])
        gate["go"] = True
        _wait(S, v["id"], lambda t: not t["running"])


def test_her_answer_continues_the_same_session(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_loop", False, raising=False)
    asked = []

    def model(system, prompt, *a, **k):
        asked.append(prompt)
        return {"explain": "Kaun si screen par, aur kya error dikhta hai?", "files": []} if len(asked) == 1 else FIX_ANSWER
    monkeypatch.setattr(S, "model_json", model)
    v = S.start(T, "fix", "app theek nahi chal raha")
    t = S.get_task(T, v["id"])
    assert t["status"] == "explained" and t["question"].endswith("?") and not t["files"]
    with pytest.raises(S.DevError):
        S.answer(T, v["id"], "  ")
    r = S.answer(T, v["id"], "Checkout par, ZeroDivisionError in total()")
    assert r["id"] == v["id"] and r["running"] is True                                # the SAME session, working again
    t = _wait(S, v["id"], lambda t: not t["running"])
    assert t["status"] != "explained" and t["question"] == "" and t["files"]          # now it did the work
    assert "Her answer: Checkout par, ZeroDivisionError" in t["text"] and "Her answer: Checkout par" in asked[-1]
    assert any(s["k"] == "note" and "Checkout par" in s["text"] for s in t["steps"])   # her answer is in the transcript
    with pytest.raises(S.DevError, match="not waiting"):
        S.answer(T, v["id"], "again")
    e = S.start(T, "explain", "total() kya karta hai?")                               # an explanation ending in ? is not a question to her
    assert S.get_task(T, e["id"])["question"] == ""


def test_auto_fix_off_for_one_pull_request(cidev, monkeypatch):  # noqa: F811
    S = cidev
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    assert S.get_task(T, v["id"])["auto_fix"] is True                                 # the default
    assert S.set_auto_fix(T, v["id"], False)["auto_fix"] is False
    head = fake.prs[1]["head"]["sha"]
    _run(fake, head, "failure")
    monkeypatch.setattr(S, "model_json", lambda *a, **k: pytest.fail("auto-fix is off: no fix round may run"))
    out = S._ci_step(T, v["id"])
    t = S.get_task(T, v["id"])
    assert t["status"] == "checks_failed" and fake.prs[1]["head"]["sha"] == head      # told, nothing pushed
    assert "Auto-fix is off" in out["say"]
    assert S.set_auto_fix(T, v["id"], True)["auto_fix"] is True


def test_a_merged_session_archives_itself_when_she_asked(cidev):  # noqa: F811
    S = cidev
    fake = S.FAKE
    a = S.start(T, "fix", "Checkout crash")
    fake.prs[1]["merged"], fake.prs[1]["state"] = True, "closed"
    assert S.refresh(T, a["id"])["status"] == "merged" and S.get_task(T, a["id"])["archived"] is False   # off by default
    assert S.save_settings(T, archive_after_merge=True)["archive_after_merge"] is True
    b = S.start(T, "fix", "Another crash")
    fake.prs[2]["merged"], fake.prs[2]["state"] = True, "closed"
    assert S.refresh(T, b["id"])["status"] == "merged"
    assert S.get_task(T, b["id"])["archived"] is True and b["id"] not in [t["id"] for t in S.tasks(T)]


def test_compare_against_a_branch_and_the_routes(cidev):  # noqa: F811
    S = cidev
    from app.devsahayak import gh as G
    fake = S.FAKE
    v = S.start(T, "fix", "Checkout crash")
    branch = S.get_task(T, v["id"])["branch"]
    inner, asked = fake.handler, []

    def handler(req: httpx.Request) -> httpx.Response:
        p = req.url.path
        if p == f"/repos/{REPO}/branches":
            return httpx.Response(200, json=[{"name": "main"}, {"name": "release"}, {"name": branch}])
        if p.startswith(f"/repos/{REPO}/compare/"):
            asked.append(p.split("/compare/", 1)[1])
            return httpx.Response(200, json={"ahead_by": 2, "behind_by": 1, "files": [
                {"filename": "app/calc.py", "status": "modified", "additions": 1, "deletions": 1,
                 "patch": "@@ -3,3 +3,3 @@\n     s += 1\n-    return s / len(items)\n+    return s\n token = ghp_abcdefghijklmnopqrstuvwxyz0123456789"},
                {"filename": "logo.png", "status": "added", "additions": 0, "deletions": 0}]})
        return inner(req)
    G.set_transport(httpx.MockTransport(handler))
    assert S.branches(T) == ["main", "release", branch]
    c = S.compare(T, v["id"], "release")
    assert asked == [f"release...{branch}"] and c["base"] == "release" and c["ahead"] == 2 and c["behind"] == 1
    assert c["files"][0]["path"] == "app/calc.py" and "+    return s" in c["files"][0]["diff"]
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in c["files"][0]["diff"]     # a key in someone's branch is not shown
    assert c["files"][1]["new"] is True and "binary" in c["files"][1]["diff"]
    with pytest.raises(S.DevError, match="Which branch"):
        S.compare(T, v["id"], "")
    from fastapi.testclient import TestClient
    from app import main
    cl = TestClient(main.app)
    u = f"/api/devsahayak/tasks/{v['id']}"
    assert cl.get(u + "/compare?base=release").json()["ahead"] == 2
    assert cl.get("/api/devsahayak/branches").json()["branches"][1] == "release"
    assert cl.patch(u, json={"auto_fix": False}).json()["auto_fix"] is False
    assert cl.post(u + "/answer", json={"text": "x"}).status_code == 400              # nothing was asked
    assert cl.put("/api/devsahayak/settings", json={"archive_after_merge": True}).json()["archive_after_merge"] is True


def test_nothing_pushed_means_nothing_to_compare(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    monkeypatch.setattr(S, "_work", lambda *a, **k: None)
    v = S.start_bg(T, "fix", "crash")
    _wait(S, v["id"], lambda t: not t["running"])
    with pytest.raises(S.DevError, match="Nothing is pushed yet"):
        S.compare(T, v["id"], "main")


# ---------------------------------------------------------------- the page, in a real browser ---
DIFF = ("--- a/app/calc.py\n+++ b/app/calc.py\n@@ -3,4 +3,5 @@\n     for i in items:\n         s += i[\"price\"] * i[\"qty\"]\n"
        "-    return s / len(items)\n+    parts = split(s)\n+    return parts\n \n")
BASE = {"kind": "fix", "repo": "meghana/shop-api", "stopping": False, "archived": False, "at": "2026-11-10T10:00:00+00:00",
        "updated": "2026-11-10T10:03:00+00:00", "checks": [], "proof": {}, "plan": {}, "tier": "", "notes": [], "log": [], "found": {},
        "auto_fix": True, "question": ""}
PR = {**BASE, "id": "dt1", "number": "D-0041", "status": "pr_open", "title": "Fix the total", "running": False, "text": "total() crashes",
      "pr_number": 7, "pr_url": "https://github.com/meghana/shop-api/pull/7", "branch": "hoola/fix-total", "ci": {"state": "success"},
      "files": [{"path": "app/calc.py", "added": 2, "removed": 1}, {"path": "tests/test_calc.py", "added": 9, "removed": 0, "new": True}],
      "file_diffs": [{"path": "app/calc.py", "added": 2, "removed": 1, "new": False, "why": "the fix", "diff": DIFF},
                     {"path": "tests/test_calc.py", "added": 9, "removed": 0, "new": True, "why": "the proof",
                      "diff": "--- a/tests/test_calc.py\n+++ b/tests/test_calc.py\n@@ -0,0 +1,2 @@\n+def test_total():\n+    assert total([]) == 0"}],
      "diff": DIFF, "explain": "The total divided by the item count.",
      "steps": [{"k": "say", "text": "On it.", "at": "2026-11-10T10:00:05+00:00"}],
      "self_review": {"verdict": "request_changes", "problems": [
          {"path": "app/calc.py", "line": 6, "severity": "medium", "body": "split() is not defined in this file."},
          {"path": "", "line": 0, "severity": "high", "body": "No test covers an empty cart."}]}}
ASK = {**BASE, "id": "dt2", "number": "D-0042", "status": "explained", "title": "App is broken", "running": False, "text": "app theek nahi",
       "pr_number": 0, "pr_url": "", "branch": "", "ci": {}, "files": [], "file_diffs": [], "diff": "", "steps": [], "self_review": {},
       "explain": "Which screen, and what error do you see?", "question": "Which screen, and what error do you see?"}


def _page(arena_server, width=1360):
    base, browser, key = arena_server
    from app.config import get_settings
    get_settings().hoola_code_page = True
    ctx = browser.new_context(viewport={"width": width, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, calls, st = [], [], {"auto_fix": True, "polls": 0}
    pg.on("pageerror", lambda e: errs.append(str(e)))
    short = lambda t: {k: v for k, v in t.items() if k not in ("file_diffs", "diff", "steps", "text")}   # noqa: E731
    pg.route("**/api/devsahayak", lambda r: r.fulfill(json={
        "settings": {"github": True, "login": "meghana", "default_repo": "meghana/shop-api", "permissions": [], "never": []},
        "repos": [{"repo": "meghana/shop-api", "private": True}], "tasks": [short(PR), short(ASK)], "reviews": [], "actions": [], "kinds": {}}))

    def dt1(r):
        if r.request.method == "PATCH":
            calls.append(("PATCH", r.request.post_data_json))
            st["auto_fix"] = r.request.post_data_json.get("auto_fix", st["auto_fix"])
        st["polls"] += 1
        r.fulfill(json={**PR, "auto_fix": st["auto_fix"]})
    pg.route("**/api/devsahayak/tasks/dt1", dt1)
    pg.route("**/api/devsahayak/tasks/dt2", lambda r: r.fulfill(json=ASK))
    pg.route("**/api/devsahayak/tasks/dt1/bg/revise", lambda r: (calls.append(("revise", r.request.post_data_json)), r.fulfill(json=PR))[1])
    pg.route("**/api/devsahayak/tasks/dt2/answer", lambda r: (calls.append(("answer", r.request.post_data_json)), r.fulfill(json=ASK))[1])
    pg.route("**/api/devsahayak/branches**", lambda r: r.fulfill(json={"branches": ["main", "release", "hoola/fix-total"]}))
    pg.route("**/api/devsahayak/tasks/dt1/compare**", lambda r: (calls.append(("compare", r.request.url.split("base=")[1])), r.fulfill(json={
        "base": "release", "head": "hoola/fix-total", "ahead": 3, "behind": 0,
        "files": [{"path": "README.md", "added": 1, "removed": 0, "new": False, "why": "", "diff": "@@ -1,1 +1,2 @@\n # Shop\n+Now with totals."}]}))[1])
    pg.goto(base + "/console/code#/s/dt1")
    pg.wait_for_selector("#hcdCol .hcd-recap")
    return ctx, pg, errs, calls


def _shot(pg, name):
    d = os.environ.get("HOOLA_SHOTS")
    if d:
        pg.screenshot(path=os.path.join(d, name + ".png"))


def test_the_changes_pane_and_comments_on_lines(arena_server):  # noqa: F811
    ctx, pg, errs, calls = _page(arena_server)
    box = lambda sel: pg.locator(sel).bounding_box()                                              # noqa: E731
    assert pg.locator("#hcdPane").is_hidden()
    pg.locator("#hcdTop [data-act='changes']").click()
    pg.wait_for_selector("#hcdPane .hcd-dl")
    assert pg.locator("#hcdRail").is_hidden() and box("#hcdPane")["width"] >= 500 and box("#hcdCol")["width"] >= 340   # beside the chat, not a page
    assert pg.locator("#hcdPane .hcd-pfs .hcd-file").count() == 2
    rows = pg.locator("#hcdDv .hcd-dl")
    nums = rows.evaluate_all("els => els.map(e => [e.className.replace('hcd-dl ', ''), e.children[1].textContent, e.children[2].textContent])")
    assert nums == [["hunk", "", ""], ["ctx", "3", "3"], ["ctx", "4", "4"], ["del", "5", ""], ["add", "", "5"], ["add", "", "6"], ["ctx", "6", "7"]]
    assert pg.locator("#hcdDv .hcd-dl.del .hcd-cadd").count() == 0                                # a removed line has no new line to comment on
    # comment on line 6 of the new file: hover, +, type, Enter
    rows.nth(5).hover()
    rows.nth(5).locator(".hcd-cadd").click()
    pg.locator("#hcdCText").fill("split() is not defined here")
    time.sleep(2.4)                                                                               # a refresh lands while she is writing
    assert pg.locator("#hcdCText").input_value() == "split() is not defined here" and pg.evaluate("document.activeElement.id") == "hcdCText"
    pg.keyboard.press("Enter")
    pg.wait_for_selector("#hcdDv .hcd-cq")
    assert "split() is not defined here" in pg.locator("#hcdDv .hcd-cq").text_content()
    assert "1 comment will go with your next message" in pg.locator("#hcdCc").text_content()
    # a second one on the other file, cancelled with Esc, then a real one
    pg.locator("#hcdPane .hcd-pfs .hcd-file").nth(1).click()
    pg.wait_for_selector("#hcdDv .hcd-pill.ok")                                                   # "new file"
    r2 = pg.locator("#hcdDv .hcd-dl.add").nth(1)
    r2.hover()
    r2.locator(".hcd-cadd").click()
    pg.locator("#hcdCText").fill("nope")
    pg.keyboard.press("Escape")
    assert pg.locator("#hcdCText").count() == 0 and pg.locator("#hcdDv .hcd-cq").count() == 0
    r2.hover()
    r2.locator(".hcd-cadd").click()
    pg.locator("#hcdCText").fill("also test a None price")
    pg.locator("#hcdCForm button[type='submit']").click()
    assert "2 comments will go" in pg.locator("#hcdCc").text_content()
    _shot(pg, "p2-1-pane")
    # they ride her next message - and comments alone are a message
    pg.locator("#hcdNote").click()
    pg.keyboard.type("please fix both")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => !document.querySelector('#hcdCc .hcd-ccn')")
    sent = [c for c in calls if c[0] == "revise"][-1][1]
    assert sent["text"] == "please fix both"
    assert sent["comments"] == [{"path": "app/calc.py", "line": 6, "code": "    return parts", "text": "split() is not defined here"},
                                {"path": "tests/test_calc.py", "line": 2, "code": "    assert total([]) == 0", "text": "also test a None price"}]
    assert pg.locator("#hcdDv .hcd-cq").count() == 0
    # Compare against another branch, as GitHub computes it
    pg.wait_for_selector("#hcdCmp option[value='release']", state="attached")
    assert pg.locator("#hcdCmp option").all_text_contents() == ["this change", "main", "release"]   # never its own branch
    pg.locator("#hcdCmp").select_option("release")
    pg.wait_for_selector("#hcdPane .hcd-pnote")
    assert ("compare", "release") in calls and "3 commit(s) ahead" in pg.locator(".hcd-pnote").text_content()
    assert "Now with totals." in pg.locator("#hcdDv").text_content()
    pg.locator("#hcdCmp").select_option("")
    pg.wait_for_function("() => document.querySelectorAll('#hcdPane .hcd-pfs .hcd-file').length === 2")
    pg.locator("[data-act='pclose']").click()
    assert pg.locator("#hcdPane").is_hidden() and pg.locator("#hcdRail").is_visible()
    assert not errs, errs
    ctx.close()


def test_review_card_pr_menu_and_her_answer(arena_server):  # noqa: F811
    ctx, pg, errs, calls = _page(arena_server)
    rev = pg.locator(".hcd-rev")
    assert "2 points left open" in rev.text_content() and "split() is not defined in this file." in rev.text_content()
    assert rev.locator("[data-act='fixone']").count() == 2 and rev.locator("[data-act='walk']").count() == 1   # only a point with a file can be shown
    rev.locator("[data-act='walk']").click()
    pg.wait_for_selector("#hcdDv .hcd-dh")
    assert "app/calc.py" in pg.locator("#hcdDv .hcd-dh").text_content()
    pg.locator("[data-act='pclose']").click()
    rev.locator("[data-act='fixone']").nth(0).click()
    pg.wait_for_function("() => true")
    time.sleep(0.4)
    one = [c for c in calls if c[0] == "revise"][-1][1]
    assert one["text"] == "Fix this point from your own review: app/calc.py:6 - split() is not defined in this file." and one["comments"] == []
    rev.locator("[data-act='fixall']").click()
    time.sleep(0.4)
    assert "- No test covers an empty cart." in [c for c in calls if c[0] == "revise"][-1][1]["text"]
    # files on the Changes card open the pane at that file
    pg.locator("#hcdRail [data-act='file']").nth(1).click()
    pg.wait_for_selector("#hcdDv .hcd-pill.ok")
    pg.locator("[data-act='pclose']").click()
    # the pull request menu: Auto-fix off for this PR, and the checkout command
    pg.locator("#hcdRail [data-menu='pr']").click()
    pg.get_by_text("Fix a red CI run by itself").click()
    pg.wait_for_function("() => true")
    time.sleep(0.4)
    assert ("PATCH", {"auto_fix": False}) in calls
    pg.locator("#hcdRail [data-menu='pr']").click()
    assert "Off - a failure waits for you" in pg.locator(".hmenu").text_content()
    pg.get_by_text("Copy the checkout command").click()
    time.sleep(0.3)
    assert pg.evaluate("navigator.clipboard.readText()") == "git fetch origin hoola/fix-total && git checkout hoola/fix-total"
    _shot(pg, "p2-2-review")
    # Hoola's one question: asked above the box, answered in the same session
    pg.locator("[data-tid='dt2']").click()
    pg.wait_for_selector("#hcdQ")
    assert "Which screen, and what error do you see?" in pg.locator("#hcdQ").text_content()
    assert "Hoola asks you a question" in pg.locator("#hcdSide").text_content()                  # and it counts as "needs you"
    assert "continues this session" in pg.locator("#hcdNote").get_attribute("placeholder")
    pg.locator("#hcdNote").click()
    pg.keyboard.type("Checkout, ZeroDivisionError")
    pg.keyboard.press("Enter")
    time.sleep(0.4)
    assert ("answer", {"text": "Checkout, ZeroDivisionError"}) in calls
    _shot(pg, "p2-3-question")
    assert not errs, errs
    ctx.close()


def test_the_pane_on_a_narrow_window(arena_server):  # noqa: F811
    ctx, pg, errs, calls = _page(arena_server, width=1000)
    pg.locator("#hcdTop [data-act='changes']").click()
    pg.wait_for_selector("#hcdPane .hcd-dl")
    box = lambda sel: pg.locator(sel).bounding_box()                                              # noqa: E731
    assert box("#hcdSide")["width"] == 52                                                         # the sessions list steps aside for the pane
    p, c = box("#hcdPane"), box("#hcdSteer")
    assert p["x"] + p["width"] <= 1000 and p["width"] >= 420 and c["x"] >= 52 and c["x"] + c["width"] <= p["x"] + 1   # nothing overlaps or leaves the window
    _shot(pg, "p2-4-narrow")
    pg.locator("[data-act='pclose']").click()
    assert box("#hcdSide")["width"] == 272                                                        # and comes back
    assert not errs, errs
    ctx.close()
