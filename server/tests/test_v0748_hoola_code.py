"""v0.748 HOOLA CODE (owner: "we have already built the Hoola Code - first check the code and then a design same like
Claude Code" -> the 6-screen canvas -> "GO"): Developer Sahayak as a console page. The work runs in the background and
the page watches it: every step stored as a structured record (read / search / edit + diff / tests / refused), her
words while it works reach the loop before its next step, Stop ends it and pushes nothing - and the page itself walked
in a real browser. Driven by the same scripted model and fake GitHub as the v0.350 loop tests."""
import time

import pytest

from tests.test_tech_devsahayak import T, _join, dev  # noqa: F401
from tests.test_v0350_kadam_ba_kadam import Script, tu
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


def test_every_step_is_a_structured_record(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    monkeypatch.setattr(S, "model_json", lambda *a, **k: pytest.fail("the one-shot path must not run"))
    from app.devsahayak import loop as L
    monkeypatch.setattr(L, "BRAIN", Script([
        [{"type": "text", "text": "Small fix. I'll read total() first."}, tu(1, "search_code", words="total")],
        [tu(2, "edit_file", path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")],      # refused: not read
        [tu(3, "read_file", path="app/calc.py")],
        [tu(4, "edit_file", path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")],
        [tu(5, "done", explain="divide by zero", pr_title="Fix total()", pr_summary="- sum", test_plan="- [ ] pytest", risk="none")],
    ]))
    v = S.start(T, "fix", "ZeroDivisionError in total()")
    steps = S.get_task(T, v["number"])["steps"]
    kinds = [s["k"] for s in steps]
    assert kinds[:5] == ["say", "search", "refused", "read", "edit"], kinds
    assert steps[0]["text"].startswith("Small fix") and steps[1]["q"] == "total"
    assert "read_file app/calc.py first" in steps[2]["why"]
    ed = steps[4]
    assert ed["path"] == "app/calc.py" and ed["added"] == 1 and ed["removed"] == 1
    assert ed["diff"] == ["-     return s / len(items)", "+     return s"] and all("at" in s for s in steps)


def test_her_note_reaches_the_loop_and_stop_pushes_nothing(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    monkeypatch.setattr(S, "model_json", lambda *a, **k: pytest.fail("the one-shot path must not run"))
    from app.devsahayak import loop as L
    seen, gate = [], {"go": False}

    def brain(system, messages, tools):
        seen.append(messages[-1]["content"])
        n = len(seen)
        if n == 1:
            return [tu(1, "list_dir", path="")], "tool_use"
        while not gate["go"]:                                   # wait until the test has queued her note
            time.sleep(0.02)
        return [tu(n, "list_dir", path="app")], "tool_use"      # keeps working until Stop
    monkeypatch.setattr(L, "BRAIN", brain)
    v = S.start_bg(T, "fix", "ZeroDivisionError in total()")
    assert v["running"] is True and v["status"] == "new"
    assert S.add_note(T, v["id"], "also handle a None price")["queued"]
    gate["go"] = True
    t = _wait(S, v["id"], lambda t: any(s["k"] == "note" for s in t["steps"]))
    assert any(s["k"] == "note" and "None price" in s["text"] for s in t["steps"])
    assert any(isinstance(c, list) and any(b.get("type") == "text" and "None price" in b.get("text", "") for b in c) for c in seen)
    assert S.stop(T, v["id"])["stopping"]
    t = _wait(S, v["id"], lambda t: not t["running"])
    assert t["status"] == "cancelled" and t["steps"][-1]["k"] == "stopped" and not t["pr_number"]
    assert not any(b.startswith("hoola/") for b in S.FAKE.refs)                 # nothing pushed
    with pytest.raises(S.DevError, match="not working"):
        S.add_note(T, v["id"], "too late")


def test_routes_and_the_switch(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    assert c.get("/api/console/config").json()["hoola_code"] is False          # pinned off for old suites
    monkeypatch.setattr(S, "_work", lambda *a, **k: time.sleep(0.3))
    r = c.post("/api/devsahayak/tasks/start", json={"kind": "fix", "text": "crash in total()"}).json()
    assert r["running"] is True and r["number"].startswith("D-")
    assert c.post(f"/api/devsahayak/tasks/{r['id']}/note", json={"text": "use Decimal"}).json()["queued"]
    assert c.post(f"/api/devsahayak/tasks/{r['id']}/bg/nope").status_code == 404
    assert c.post(f"/api/devsahayak/tasks/{r['id']}/bg/plan_ok", json={"hash": "x"}).status_code == 400   # not waiting
    _wait(S, r["id"], lambda t: not t["running"])
    assert c.post(f"/api/devsahayak/tasks/{r['id']}/note", json={"text": "late"}).status_code == 400


def test_the_plain_callback_still_works():
    """Every older caller passes a plain lambda: no hooks, nothing changes."""
    from app.devsahayak import loop as L
    assert L._hook(lambda line: None, "event") is None and L._hook(None, "inbox") is None


TASKS = [{"id": "dt1", "number": "D-0042", "kind": "fix", "repo": "meghana/shop-api", "status": "new", "title": "Fix login 500",
          "running": True, "at": "2026-11-10T10:00:00+00:00", "updated": "2026-11-10T10:03:00+00:00", "files": [], "ci": {}, "checks": [],
          "proof": {}, "self_review": {}, "plan": {}, "pr_number": 0},
         {"id": "dt2", "number": "D-0041", "kind": "write", "repo": "meghana/shop-api", "status": "plan_wait", "title": "<b>Orders to Postgres</b>",
          "running": False, "at": "2026-11-10T09:00:00+00:00", "updated": "2026-11-10T09:05:00+00:00", "files": [], "ci": {}, "checks": [],
          "proof": {}, "self_review": {}, "plan": {}, "pr_number": 0}]
OV = {"settings": {"github": True, "login": "meghana", "default_repo": "meghana/shop-api", "permissions": ["Contents"], "never": ["Never push to main"]},
      "repos": [{"repo": "meghana/shop-api", "private": True}], "tasks": TASKS, "reviews": [], "actions": [], "kinds": {}}
FULL = {**TASKS[0], "text": "POST /login returns 500", "steps": [
    {"k": "say", "text": "Small fix.", "at": "2026-11-10T10:00:05+00:00"},
    {"k": "read", "path": "app/auth/views.py", "lines": [0, 0], "at": "2026-11-10T10:00:12+00:00"},
    {"k": "check", "ok": False, "seconds": 9, "cmd": "pytest -q", "only": "", "tail": ["1 failed, 46 passed"], "at": "2026-11-10T10:01:20+00:00"},
    {"k": "edit", "path": "app/auth/views.py", "added": 1, "removed": 1, "diff": ["- a", "+ b"], "at": "2026-11-10T10:01:52+00:00"}],
    "log": [], "diff": "", "found": {}, "notes_waiting": 0}
PLAN = {**TASKS[1], "text": "Move orders", "hash": "h1", "tier": "large", "steps": [], "log": [], "diff": "", "found": {},
        "plan": {"goal": "orders in Postgres", "files": [{"path": "app/store.py", "why": "new store"}], "steps": ["Add the store"],
                 "done_when": ["31 tests pass"], "risk": "ids"}}


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True,
                                                                   "panel": True, "projects": True, "human": True, "hoola_code": True}))
    pg.route("**/api/devsahayak", lambda r: r.fulfill(json=OV))
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=FULL))
    pg.route("**/api/devsahayak/tasks/dt2", lambda r: r.fulfill(json=PLAN))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.wait_for_selector(".sn[data-v='code']")
    pg.locator(".sn[data-v='code']").click()
    pg.wait_for_selector(".hcd-home")
    home = pg.locator(".hcd").text_content()
    assert "What should Hoola code today?" in home and "Running" in home and "Needs you" in home and "<b>Orders to Postgres</b>" in home
    assert pg.locator(".hcd-kind[data-kind]").count() == 5
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector(".hcd-step")
    s = pg.locator(".hcd-feed").text_content()
    assert "Small fix." in s and "Read app/auth/views.py" in s and "Ran your tests" in s and "failed" in s and "Edited app/auth/views.py" in s
    assert pg.locator(".hcd-diff span.add").count() >= 1 and pg.locator("#hcdStop").count() == 1 and pg.locator("#hcdNote").count() == 1
    pg.locator("[data-tid='dt2']").click()
    pg.wait_for_selector("#hcdYes")
    p = pg.locator(".hcd-card").text_content()
    assert "orders in Postgres" in p and "31 tests pass" in p and "waits for your OK" in p
    assert not errs, errs
    ctx.close()
