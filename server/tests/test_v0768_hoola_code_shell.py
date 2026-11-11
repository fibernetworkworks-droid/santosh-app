"""v0.768 HOOLA CODE PHASE 1 (docs/HOOLA_CODE_WEB_PLAN.md; owner: "GO PHASE 1"): the shell and the session laid out like
Claude Code on the web. Server: her own name for a session, archive / unarchive, delete, search, a queued note taken
back. Page: three zones, folded steps, a queue she can take from, and - the bug this phase fixes - a refresh that no
longer wipes what she is typing. The page is walked in a real browser against a mocked API whose answers change
between polls."""
import os
import time

import pytest

from tests.test_tech_devsahayak import T, _join, dev  # noqa: F401
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401
from tests.test_v0350_kadam_ba_kadam import tu


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


def test_rename_archive_search_delete(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    monkeypatch.setattr(S, "_work", lambda *a, **k: None)
    a = S.start_bg(T, "fix", "ZeroDivisionError in total()")
    b = S.start_bg(T, "tests", "cover the coupon rounding path")
    _wait(S, a["id"], lambda t: not t["running"])
    _wait(S, b["id"], lambda t: not t["running"])
    assert S.rename(T, a["id"], "  Fix the   total crash ")["title"] == "Fix the total crash"
    assert S.get_task(T, a["id"])["title"] == "Fix the total crash"
    assert S.rename(T, a["id"], "")["title"].startswith("ZeroDivisionError")            # empty = Hoola's own name again
    assert [t["id"] for t in S.tasks(T, q_text="coupon")] == [b["id"]]                  # search her words
    assert S.tasks(T, q_text="100%_nothing") == []                                      # % and _ are plain characters
    assert S.archive(T, b["id"])["archived"] is True
    assert [t["id"] for t in S.tasks(T)] == [a["id"]] and [t["id"] for t in S.overview(T)["tasks"]] == [a["id"]]
    assert [t["id"] for t in S.tasks(T, archived=True)] == [b["id"]]
    assert S.archive(T, b["id"], False)["archived"] is False and len(S.tasks(T)) == 2
    assert S.delete_task(T, b["id"])["deleted"] == b["id"]
    with pytest.raises(S.DevError):
        S.get_task(T, b["id"])
    with pytest.raises(S.DevError):                                                     # another tenant's session is not found
        S.rename("someone-else", a["id"], "mine now")


def test_a_running_session_is_not_archived_or_deleted_and_a_note_comes_back(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    gate = {"go": False}

    def brain(system, messages, tools):
        while not gate["go"]:
            time.sleep(0.02)
        return [tu(1, "list_dir", path="")], "tool_use"
    monkeypatch.setattr(L, "BRAIN", brain)
    v = S.start_bg(T, "fix", "ZeroDivisionError in total()")
    try:
        with pytest.raises(S.DevError, match="still working"):
            S.archive(T, v["id"])
        with pytest.raises(S.DevError, match="still working"):
            S.delete_task(T, v["id"])
        S.add_note(T, v["id"], "use Decimal")
        S.add_note(T, v["id"], "and add a test")
        assert S.get_task(T, v["id"])["notes"] == ["use Decimal", "and add a test"]
        r = S.drop_note(T, v["id"], 0)
        assert r == {"ok": True, "text": "use Decimal", "left": 1}
        assert S.get_task(T, v["id"])["notes"] == ["and add a test"]
        with pytest.raises(S.DevError, match="already read"):
            S.drop_note(T, v["id"], 5)
    finally:
        S.stop(T, v["id"])
        gate["go"] = True
        _wait(S, v["id"], lambda t: not t["running"])


def test_routes(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    monkeypatch.setattr(S, "_work", lambda *a, **k: None)
    r = c.post("/api/devsahayak/tasks/start", json={"kind": "fix", "text": "crash in total()"}).json()
    _wait(S, r["id"], lambda t: not t["running"])
    u = f"/api/devsahayak/tasks/{r['id']}"
    assert c.patch(u, json={"title": "Total crash"}).json()["title"] == "Total crash"
    assert c.patch(u, json={}).status_code == 400
    assert c.patch(u, json={"archived": True}).json()["archived"] is True
    assert c.get("/api/devsahayak/tasks").json()["tasks"] == []
    assert [t["id"] for t in c.get("/api/devsahayak/tasks?archived=1&q=total").json()["tasks"]] == [r["id"]]
    assert c.delete(u + "/note/0").status_code == 400                                   # nothing queued
    assert c.delete(u).json()["ok"] is True and c.get(u).status_code == 400


# ---------------------------------------------------------------- the page, in a real browser ---
def _task(i, title, status, running, repo="meghana/shop-api", **kw):
    return {"id": f"dt{i}", "number": f"D-004{i}", "kind": "fix", "repo": repo, "status": status, "title": title, "running": running,
            "stopping": False, "archived": False, "at": "2026-11-10T10:00:00+00:00", "updated": "2026-11-10T10:03:00+00:00", "files": [],
            "ci": {}, "checks": [], "proof": {}, "self_review": {}, "plan": {}, "pr_number": 0, "pr_url": "", "branch": "", "tier": "", **kw}


TASKS = [_task(1, "Fix login 500", "new", True),
         _task(2, "<b>Orders to Postgres</b>", "plan_wait", False),
         _task(3, "Footer links", "pr_open", False, repo="meghana/site", pr_number=7, pr_url="https://github.com/meghana/site/pull/7",
               ci={"state": "success"}, files=[{"path": "a/b.py", "added": 6, "removed": 2}])]
STEPS = [{"k": "say", "text": "Small fix.", "at": "2026-11-10T10:00:05+00:00"},
         {"k": "rules", "paths": ["AGENTS.md"], "at": "2026-11-10T10:00:08+00:00"},
         {"k": "read", "path": "app/auth/views.py", "lines": [0, 0], "at": "2026-11-10T10:00:12+00:00"},
         {"k": "read", "path": "app/auth/models.py", "lines": [0, 0], "at": "2026-11-10T10:00:15+00:00"},
         {"k": "search", "q": "login", "n": 3, "at": "2026-11-10T10:00:19+00:00"},
         {"k": "check", "ok": False, "seconds": 9, "cmd": "pytest -q", "only": "", "tail": ["1 failed, 46 passed"], "at": "2026-11-10T10:01:20+00:00"},
         {"k": "edit", "path": "app/auth/views.py", "added": 1, "removed": 1, "diff": ["- a", "+ b"], "at": "2026-11-10T10:01:52+00:00"}]
LATER = {"k": "check", "ok": True, "seconds": 8, "cmd": "pytest -q", "only": "", "tail": [], "at": "2026-11-10T10:02:30+00:00"}
PLAN = {**TASKS[1], "text": "Move orders", "hash": "h1", "tier": "large", "steps": [], "notes": [], "log": [], "diff": "", "found": {},
        "plan": {"goal": "orders in Postgres", "files": [{"path": "app/store.py", "why": "new store"}], "steps": ["Add the store"],
                 "done_when": ["31 tests pass"], "risk": "ids"}}
DONE = {**TASKS[2], "text": "Fix the footer", "steps": STEPS[:5], "notes": [], "log": [], "found": {}, "explain": "Two links pointed at old pages.",
        "diff": "--- a/a/b.py\n+++ b/a/b.py\n-old\n+new"}


def _console(arena_server, width=1360, via_console=False):
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": width, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, calls, state = [], [], {"polls": 0, "notes": ["use Decimal"], "title": "Fix login 500"}
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True,
                                                                   "panel": True, "projects": True, "human": True, "hoola_code": True}))

    def overview(r):
        ts = [{**TASKS[0], "title": state["title"]}] + TASKS[1:]
        r.fulfill(json={"settings": {"github": True, "login": "meghana", "default_repo": "meghana/shop-api", "permissions": ["Contents"],
                                     "never": ["Never push to main"]},
                        "repos": [{"repo": "meghana/shop-api", "private": True}], "tasks": ts, "reviews": [], "actions": [], "kinds": {}})

    def dt1(r):
        m = r.request.method
        if m == "PATCH":
            calls.append(("PATCH", r.request.post_data_json))
            state["title"] = r.request.post_data_json.get("title", state["title"])
            return r.fulfill(json={**TASKS[0], "title": state["title"]})
        state["polls"] += 1
        steps = STEPS + ([LATER] if state["polls"] >= 3 else [])            # a new step lands on the third read
        r.fulfill(json={**TASKS[0], "title": state["title"], "text": "POST /login returns 500", "steps": steps, "notes": state["notes"],
                        "log": [], "diff": "", "found": {}})

    def unq(r):
        calls.append(("DELETE note", r.request.url.rsplit("/", 1)[-1]))
        text = state["notes"].pop(0)
        r.fulfill(json={"ok": True, "text": text, "left": len(state["notes"])})
    pg.route("**/api/devsahayak", overview)
    pg.route("**/api/devsahayak/tasks/dt1", dt1)
    pg.route("**/api/devsahayak/tasks/dt1/note/*", unq)
    pg.route("**/api/devsahayak/tasks/dt2", lambda r: r.fulfill(json=PLAN))
    pg.route("**/api/devsahayak/tasks/dt3", lambda r: r.fulfill(json=DONE))
    from app.config import get_settings
    get_settings().hoola_code_page = True                       # conftest pins the page off for the old suites
    pg.goto(base + "/console/" if via_console else base + "/console/code")
    if via_console:
        pg.wait_for_selector("#composer")
        pg.locator(".sn[data-v='code']").click()
    pg.wait_for_selector(".hcd-home")
    return ctx, pg, errs, calls, state


def _shot(pg, name):
    d = os.environ.get("HOOLA_SHOTS")
    if d:
        pg.screenshot(path=os.path.join(d, name + ".png"))


def test_typing_survives_a_refresh_and_steps_fold(arena_server):  # noqa: F811
    ctx, pg, errs, calls, state = _console(arena_server)
    home = pg.locator(".hcd").text_content()
    assert "What should Hoola code today?" in home and "<b>Orders to Postgres</b>" in home       # her title is text, never HTML
    assert pg.locator(".hcd-lbl").all_text_contents()[:2] == ["shop-api", "site"]                 # grouped by repo
    _shot(pg, "1-home")
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector(".hcd-fold")
    feed = pg.locator("#hcdCol")
    assert "Small fix." in feed.text_content() and "Read the repo's rules, read 2 files, searched 1 time" in feed.text_content()
    assert pg.locator("#hcdCol .hcd-fin").first.is_hidden()                                       # folded by default
    assert "Ran your tests" in feed.text_content() and "1 failed, 46 passed" in feed.text_content()   # a failure is never folded away
    pg.locator("#hcdCol .hcd-fold").first.click()
    assert pg.locator("#hcdCol .hcd-fin").first.is_visible() and "app/auth/models.py" in pg.locator("#hcdCol .hcd-fin").first.text_content()
    # THE BUG THIS PHASE FIXES: she is half way through a message when a new step arrives
    pg.locator("#hcdNote").click()
    pg.keyboard.type("also check the session cook")
    before = feed.text_content()
    pg.wait_for_function("() => document.querySelectorAll('#hcdCol .hcd-step.ok').length === 1", timeout=12000)
    assert feed.text_content() != before
    assert pg.locator("#hcdNote").input_value() == "also check the session cook"
    assert pg.evaluate("document.activeElement.id") == "hcdNote"
    pg.keyboard.type("ie")
    assert pg.locator("#hcdNote").input_value() == "also check the session cookie"
    assert pg.locator("#hcdCol .hcd-fin").first.is_visible()                                      # the fold she opened stays open
    # no rotating ring anywhere (CRISP TEXT)
    assert pg.locator(".hcd-spin").count() == 0
    assert pg.evaluate("getComputedStyle(document.querySelector('.hcd-pulse')).animationName") == "hcdpulse"
    _shot(pg, "2-session")
    # a queued note comes back into the box, in front of what she typed
    assert "use Decimal" in pg.locator("#hcdQueue").text_content()
    pg.locator("[data-act='unq']").click()
    pg.wait_for_function("() => document.querySelector('#hcdNote').value.startsWith('use Decimal')")
    assert ("DELETE note", "0") in calls and pg.locator("#hcdQueue .hcd-q").count() == 0
    assert pg.locator("#hcdStop").count() == 1
    assert not errs, errs
    ctx.close()


def test_layout_rail_sidebar_menus(arena_server):  # noqa: F811
    ctx, pg, errs, calls, state = _console(arena_server, width=1280)   # a 1280 laptop: sessions + chat + rail all fit on its own page
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector("#hcdRail .hcd-rc")
    box = lambda sel: pg.locator(sel).bounding_box()                                              # noqa: E731
    assert box("#hcdRail")["width"] == 300 and box("#hcdCol")["width"] >= 600                 # the chat is never squeezed
    rail = pg.locator("#hcdRail").text_content()
    assert "Changes" in rail and "Progress" in rail and "Run your tests" in rail and "app/auth/views.py" in rail
    for sel in ("#hcdSteer", "#hcdStop", "#hcdTop"):                                              # nothing pushed out of view
        b = box(sel)
        assert b["x"] >= 0 and b["x"] + b["width"] <= 1280 and b["y"] + b["height"] <= 900, sel
    pg.locator("[data-act='rail']").click()
    assert pg.locator("#hcdRail").is_hidden() and box("#hcdCol")["width"] == 760
    pg.locator("[data-act='rail']").click()
    assert pg.locator("#hcdRail").is_visible()
    pg.locator("[data-act='side']").click()
    assert box("#hcdSide")["width"] == 52 and pg.locator("#hcdSide [data-tid]").count() == 2      # running + needs-you stay one click away
    pg.locator("[data-act='side']").click()
    assert box("#hcdSide")["width"] == 272
    # the session menu: rename goes to the server, Verbose opens every step
    pg.locator("[data-menu='title']").click()
    pg.get_by_role("menuitemradio", name="Verbose").or_(pg.get_by_text("Verbose", exact=True)).first.click()
    pg.wait_for_function("() => !document.querySelector('#hcdCol .hcd-fold[data-fold^=\"g\"]')")
    assert pg.locator("#hcdCol .hcd-step").count() >= 5 and pg.locator("#hcdCol .hcd-diff span.add").first.is_visible()
    pg.locator(".hcd-title").click()
    pg.locator("#hcdDlgIn").fill("Login crash")
    pg.locator("#hcdDlg button[value='ok']").click()
    pg.wait_for_function("() => document.querySelector('.hcd-title').textContent === 'Login crash'")
    assert ("PATCH", {"title": "Login crash"}) in calls
    # a narrow window: the rail steps aside by itself and comes back as an overlay on her click
    pg.set_viewport_size({"width": 1000, "height": 900})
    assert pg.locator("#hcdRail").is_hidden()
    pg.wait_for_function("() => document.querySelector('[data-act=\\'rail\\']').getAttribute('aria-pressed') === 'false'")   # the button tells the truth
    pg.locator("[data-act='rail']").click()
    assert pg.locator("#hcdRail").is_visible() and box("#hcdCol")["width"] >= 600                 # an overlay: the chat keeps its width
    pg.locator("[data-act='rail']").click()
    assert pg.locator("#hcdRail").is_hidden()
    _shot(pg, "3-narrow")
    # the plan waits with its two answers; a finished session shows the recap and the merge door
    pg.set_viewport_size({"width": 1360, "height": 900})
    pg.locator("[data-tid='dt2']").click()
    pg.wait_for_selector("#hcdYes")
    assert "orders in Postgres" in pg.locator(".hcd-card").text_content() and pg.locator("#hcdCancel").count() == 1
    assert "starts on the plan" in pg.locator("#hcdNote").get_attribute("placeholder")
    _shot(pg, "4-plan")
    pg.locator("[data-menu='title']").click()                                                     # back to the Normal view (her choice is remembered)
    pg.get_by_text("Normal", exact=True).first.click()
    pg.locator("[data-tid='dt3']").click()
    pg.wait_for_selector(".hcd-recap")
    done = pg.locator("#hcdCol").text_content()
    assert "Worked for" in done and "Two links pointed at old pages." in done and "CI passed. Merging is your tap." in done
    assert pg.locator(".hcd-recap [data-act='mergereq']").is_visible()                            # reachable with the rail hidden too
    assert pg.locator("#hcdRail [data-act='mergereq']").count() == 1 and pg.locator("#hcdRail a[href='https://github.com/meghana/site/pull/7']").count() == 1
    assert "Ask for a change" in pg.locator("#hcdNote").get_attribute("placeholder")
    _shot(pg, "5-done")
    assert not errs, errs
    ctx.close()


def test_its_own_page_with_its_own_sidebar(arena_server):  # noqa: F811
    """Owner: "CREATE A SEPERATE PAGE WITH ITS OWN SIDE BAR FOR HOOLA CODE". The console row opens /console/code; that
    page has ONE sidebar (the sessions), every screen has its own address, and Back returns to the screen before."""
    ctx, pg, errs, calls, state = _console(arena_server, via_console=True)
    assert pg.url.endswith("/console/code") and pg.title() == "Hoola Code"
    assert pg.locator("#snav").count() == 0 and pg.locator("#hcdSide").count() == 1               # the console's sidebar is not here
    assert pg.locator("#hcdSide").bounding_box()["x"] == 0
    assert pg.locator("#hcdSide a[href='/console/']").text_content() == "Back to Hoola"
    pg.locator("[data-tid='dt2']").click()
    pg.wait_for_selector("#hcdYes")
    assert pg.url.endswith("/console/code#/s/dt2")
    pg.locator("[data-go='settings']").click()
    pg.wait_for_selector("#hcdTok")
    assert pg.url.endswith("#/settings") and pg.title() == "Settings · Hoola Code"
    pg.go_back()
    pg.wait_for_selector("#hcdYes")                                                               # Back = the session she was on
    pg.goto(pg.url.split("#")[0] + "#/s/dt3")                                                     # a link opens one session
    pg.reload()
    pg.wait_for_selector(".hcd-recap")
    assert "Two links pointed at old pages." in pg.locator("#hcdCol").text_content()
    _shot(pg, "6-own-page")
    assert not errs, errs
    ctx.close()


def test_the_page_is_off_with_its_switch(dev):  # noqa: F811
    from fastapi.testclient import TestClient
    from app import main
    from app.config import get_settings
    c = TestClient(main.app)
    get_settings().hoola_code_page = False
    assert c.get("/console/code", follow_redirects=False).status_code == 307
    get_settings().hoola_code_page = True
    r = c.get("/console/code")
    assert r.status_code == 200 and "hoolacode.js" in r.text and "script-src 'self'" in r.headers["content-security-policy"]
