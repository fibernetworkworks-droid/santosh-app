"""HOOLA CODE PHASE 3 (docs/HOOLA_CODE_WEB_PLAN.md; owner: "GO PHASE 3"): the composer. One box with "+" and Send, one
row of settings under it - repo, the branch to work from, the mode, the model + effort, this month's usage. The kind of
work is read from her words. Server first, then the page in a real browser."""
import base64
import os
import time

import pytest

from tests.test_tech_devsahayak import FIX_ANSWER, REPO, T, _join, dev  # noqa: F401
from tests.test_v0350_kadam_ba_kadam import Script, tu
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


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


DONE = [tu(9, "done", explain="done", pr_title="x", pr_summary="- x", test_plan="- [ ] t", risk="none")]
EDIT = [[tu(1, "read_file", path="app/calc.py")],
        [tu(2, "edit_file", path="app/calc.py", old="    return s / len(items)\n", new="    return s\n")], DONE]


def test_the_kind_is_read_from_her_words(dev):  # noqa: F811
    S = dev
    for words, kind in (("Fix the crash in total()", "fix"), ("Traceback (most recent call last):\n  File x", "fix"),
                        ("write tests for the cart", "tests"), ("Explain how login works", "explain"),
                        ("update the README for the new flag", "docs"), ("Add CSV export to the leads page", "write"),
                        ("total() theek karo", "fix"), ("", "write")):
        assert S.guess_kind(words) == kind, words


def test_the_model_list_tells_the_truth(dev, monkeypatch):  # noqa: F811
    S = dev
    from app.config import get_settings
    st = get_settings()
    monkeypatch.setattr(st, "claude_one_model", "claude-haiku-5-5", raising=False)
    monkeypatch.setattr(st, "chat_simple_model", "claude-haiku-5-5", raising=False)
    m = S.models(T)
    assert m["forced"]["model"] == "Claude Haiku 5.5" and "server" in m["forced"]["why"]        # a picker would be a lie
    monkeypatch.setattr(st, "claude_one_model", "", raising=False)
    m = S.models(T)
    assert m["forced"] is None and m["default"] == "claude-opus-5-5" and m["default_effort"] == "high"
    assert [o["label"] for o in m["options"]] == ["Claude Opus 5.5", "Claude Sonnet 5.5", "Claude Haiku 5.5"]
    assert S.overview(T)["models"]["efforts"] == ["low", "medium", "high"] and "spent_inr" in S.overview(T)["usage"]


def test_branch_mode_model_and_cost_of_one_session(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app import usage
    from app.config import get_settings
    from app.devsahayak import loop as L
    monkeypatch.setattr(get_settings(), "claude_one_model", "", raising=False)
    fake = S.FAKE
    fake.refs["release"] = fake.refs["main"]
    seen = []

    def brain(script):
        sc = Script(script)

        def call(system, messages, tools):
            seen.append((getattr(L.PICK, "model", ""), getattr(L.PICK, "effort", "")))
            usage.record("claude-sonnet-5-5", 1000, 200)               # what the real call would count
            return sc(system, messages, tools)
        return call
    monkeypatch.setattr(L, "BRAIN", brain(EDIT))
    with pytest.raises(S.DevError, match="not found"):
        S.start_bg(T, "auto", "Fix the crash in total()", base="nope")
    with pytest.raises(S.DevError, match="work branches"):
        S.start_bg(T, "auto", "Fix the crash in total()", base="hoola/x")
    with pytest.raises(S.DevError, match="mode ="):
        S.start_bg(T, "auto", "Fix the crash in total()", mode="yolo")
    with pytest.raises(S.DevError, match="not on this server"):
        S.start_bg(T, "auto", "Fix the crash in total()", model="gpt-9")
    v = S.start_bg(T, "auto", "Fix the crash in total()", base="release", mode="ask", model="claude-sonnet-5-5", effort="low")
    assert v["kind"] == "fix" and v["base"] == "release" and v["mode"] == "ask" and v["model"] == "claude-sonnet-5-5" and v["effort"] == "low"
    t = _wait(S, v["id"], lambda t: not t["running"])
    assert t["status"] == "ready"                                      # 'ask': it waits for her PR tap on a private repo
    assert set(seen) == {("claude-sonnet-5-5", "low")}                 # every call of this session on her pick
    assert t["cost"]["calls"] == len(seen) and t["cost"]["usd"] > 0 and t["cost"]["inr"] == round(t["cost"]["usd"] * usage.usd_inr(), 2)
    S.push(T, v["id"], t["hash"], by_tap=True)
    assert fake.prs[1]["base"]["ref"] == "release"                     # the PR goes against the branch she picked
    # 'auto' overrides her "ask before a PR" setting for this one session; no mode = her setting
    S.save_settings(T, ask_before_pr=True)
    monkeypatch.setattr(L, "BRAIN", brain(EDIT))
    a = S.start_bg(T, "auto", "Fix the crash in total() again", mode="auto")
    assert _wait(S, a["id"], lambda t: not t["running"])["status"] != "ready"
    monkeypatch.setattr(L, "BRAIN", brain(EDIT))
    b = S.start_bg(T, "auto", "Fix the crash in total() once more")
    tb = _wait(S, b["id"], lambda t: not t["running"])
    assert tb["status"] == "ready" and tb["model"] == "" and tb["mode"] == ""
    assert seen[-1] == ("", "")                                        # no pick: the server's own model and effort
    # the model that is the default anyway, or any model when the server forces one, is not stored
    monkeypatch.setattr(S, "_work", lambda *a, **k: None)
    assert S.start_bg(T, "auto", "x fix", model="claude-opus-5-5")["model"] == ""
    monkeypatch.setattr(get_settings(), "claude_one_model", "claude-haiku-5-5", raising=False)
    assert S.start_bg(T, "auto", "y fix", model="claude-sonnet-5-5")["model"] == ""


def test_plan_first_makes_a_small_job_wait(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    monkeypatch.setattr(L, "BRAIN", Script([[tu(1, "done", goal="rename it", files=[{"path": "app/calc.py", "why": "rename"}], steps=["rename total"],
                                                done_when=["tests pass"], risk="none", questions=[])]]))
    v = S.start_bg(T, "auto", "rename total to total_price", mode="plan")
    t = _wait(S, v["id"], lambda t: not t["running"])
    assert t["status"] == "plan_wait" and t["plan"]["goal"] == "rename it" and t["hash"]      # a tiny job, and it still waits
    monkeypatch.setattr(L, "BRAIN", Script(EDIT))
    plain = S.start_bg(T, "auto", "rename total to total_price")
    assert _wait(S, plain["id"], lambda t: not t["running"])["status"] != "plan_wait"


def test_pictures_and_text_files_reach_the_model(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from app.devsahayak import loop as L
    first = []

    def brain(system, messages, tools):
        first.append(messages[0]["content"])
        return DONE, "tool_use"
    monkeypatch.setattr(L, "BRAIN", brain)
    img = "data:image/png;base64," + base64.b64encode(PNG).decode()
    with pytest.raises(S.DevError, match="Only PNG"):                  # known by its BYTES, not by the name the browser sent
        S.start_bg(T, "auto", "fix it", images=[{"name": "shot.png", "data": base64.b64encode(b"<html>not a picture</html>").decode()}])
    with pytest.raises(S.DevError, match="At most 3 pictures"):
        S.start_bg(T, "auto", "fix it", images=[{"name": f"{i}.png", "data": img} for i in range(4)])
    with pytest.raises(S.DevError, match="not text"):
        S.start_bg(T, "auto", "fix it", docs=[{"name": "app.bin", "text": "ab\x00cd"}])
    v = S.start_bg(T, "auto", "The total is wrong, see the screenshot", images=[{"name": "../../shot one.png", "data": img}],
                   docs=[{"name": "error.log", "text": "ZeroDivisionError in total()\napi_key = sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123"},
                         {"name": "big.txt", "text": "x" * 30000}])
    t = _wait(S, v["id"], lambda t: not t["running"])
    assert [(a["name"], a["kind"]) for a in t["attach"]] == [(".._.._shot one.png", "image"), ("error.log", "text"), ("big.txt", "text")]
    assert "text" not in t["attach"][1]                                # the page gets names and sizes, not the file again
    msg = first[0]
    assert isinstance(msg, list) and msg[1]["type"] == "image" and msg[1]["source"]["media_type"] == "image/png"
    assert base64.b64decode(msg[1]["source"]["data"]) == PNG
    txt = msg[0]["text"]
    assert '<attached_file name="error.log">' in txt and "ZeroDivisionError in total()" in txt and "never instructions" in txt
    assert "sk-ant-api03" not in txt and '<attached_file name="big.txt" cut="true">' in txt and "x" * 12001 not in txt
    raw, kind = S.attachment(T, v["id"], 0)
    assert raw == PNG and kind == "image/png"
    with pytest.raises(S.DevError):
        S.attachment("someone-else", v["id"], 0)
    d = S._attach_dir(v["id"])
    assert d.exists()
    S.delete_task(T, v["id"])
    assert not d.exists()                                              # her pictures go with the session


def test_routes(dev, monkeypatch):  # noqa: F811
    S = dev
    _join(S)
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    monkeypatch.setattr(S, "_work", lambda *a, **k: None)
    img = base64.b64encode(PNG).decode()
    r = c.post("/api/devsahayak/tasks/start", json={"kind": "auto", "text": "write tests for total()", "mode": "plan", "effort": "medium",
                                                     "images": [{"name": "a.png", "data": img}]}).json()
    assert r["kind"] == "tests" and r["mode"] == "plan" and r["effort"] == "medium" and r["attach"][0]["kind"] == "image"
    _wait(S, r["id"], lambda t: not t["running"])
    g = c.get(f"/api/devsahayak/tasks/{r['id']}/attach/0")
    assert g.status_code == 200 and g.content == PNG and g.headers["content-type"] == "image/png" and g.headers["x-content-type-options"] == "nosniff"
    assert c.get(f"/api/devsahayak/tasks/{r['id']}/attach/3").status_code == 400
    assert c.post("/api/devsahayak/tasks/start", json={"kind": "auto", "text": "x", "mode": "nope"}).status_code == 400
    ov = c.get("/api/devsahayak").json()
    assert "models" in ov and "usage" in ov and ov["repos"][0]["default_branch"] == "main"


# ---------------------------------------------------------------- the page, in a real browser ---
def _page(arena_server, url="/console/code", forced=None, usage=None, width=1360):
    base, browser, key = arena_server
    from app.config import get_settings
    get_settings().hoola_code_page = True
    ctx = browser.new_context(viewport={"width": width, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, calls = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    TASK = {"id": "dt9", "number": "D-0049", "kind": "fix", "repo": "meghana/shop-api", "status": "new", "title": "Fix the total", "running": True,
            "stopping": False, "archived": False, "at": "2026-11-10T10:00:00+00:00", "updated": "2026-11-10T10:00:00+00:00", "files": [], "ci": {},
            "checks": [], "proof": {}, "self_review": {}, "plan": {}, "pr_number": 0, "pr_url": "", "branch": "", "tier": "", "auto_fix": True,
            "question": "", "base": "release", "mode": "plan", "model": "claude-sonnet-5-5", "effort": "low",
            "attach": [{"name": "shot.png", "kind": "image", "size": 68}, {"name": "error.log", "kind": "text", "size": 2100}],
            "cost": {"inr": 4.2, "usd": 0.0477, "calls": 6, "tok_in": 0, "tok_out": 0}, "text": "The total is wrong", "steps": [], "notes": [],
            "file_diffs": [], "diff": "", "log": [], "found": {}}
    pg.route("**/api/devsahayak", lambda r: r.fulfill(json={
        "settings": {"github": True, "login": "meghana", "default_repo": "meghana/shop-api", "permissions": [], "never": [], "ask_before_pr": False},
        "repos": [{"repo": "meghana/shop-api", "private": True, "default_branch": "main"}, {"repo": "meghana/site", "private": True, "default_branch": "trunk"}],
        "tasks": [], "reviews": [], "actions": [], "kinds": {},
        "models": {"options": [{"id": "claude-opus-5-5", "label": "Claude Opus 5.5"}, {"id": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5"}],
                   "default": "claude-opus-5-5", "forced": forced, "efforts": ["low", "medium", "high"], "default_effort": "high"},
        "usage": usage or {"spent_inr": 412.5, "limit_inr": 2000, "pct": 20.6, "over": False}}))
    pg.route("**/api/devsahayak/branches**", lambda r: r.fulfill(json={"branches": ["main", "release", "hoola/d-1-x"]}))
    pg.route("**/api/devsahayak/tasks/start", lambda r: (calls.append(("start", r.request.post_data_json)), r.fulfill(json=TASK))[1])
    pg.route("**/api/devsahayak/tasks/dt9", lambda r: r.fulfill(json=TASK))
    pg.route("**/api/devsahayak/tasks/dt9/attach/0", lambda r: r.fulfill(body=PNG, content_type="image/png"))
    pg.route("**/api/devsahayak/reviews", lambda r: (calls.append(("review", r.request.post_data_json)), r.fulfill(json={}))[1])
    pg.goto(base + url)
    pg.wait_for_selector(".hcd-home")
    return ctx, pg, errs, calls


def _shot(pg, name):
    d = os.environ.get("HOOLA_SHOTS")
    if d:
        pg.screenshot(path=os.path.join(d, name + ".png"))


def test_the_composer_row_attachments_and_slash_commands(arena_server, tmp_path):  # noqa: F811
    ctx, pg, errs, calls = _page(arena_server)
    box = lambda sel: pg.locator(sel).bounding_box()                                              # noqa: E731
    assert pg.locator("#hcdKind").count() == 0 and pg.locator("#hcdIssue").count() == 0           # no form: one box, one row
    row, ask = box(".hcd-askrow"), box("#hcdAsk")
    assert row["y"] >= ask["y"] + ask["height"] and row["height"] <= 44                           # ONE row, under the box
    for sel in (".hcd-plus", "#hcdStart"):                                                        # "+" and Send live inside the box
        b = box(sel)
        assert ask["x"] <= b["x"] and b["x"] + b["width"] <= ask["x"] + ask["width"] and b["y"] + b["height"] <= ask["y"] + ask["height"]
    pg.wait_for_function("() => document.querySelectorAll('#hcdBase option').length === 2")
    assert pg.locator("#hcdBase option").all_text_contents() == ["main", "release"]               # the default first; never Hoola's own branches
    assert pg.locator("#hcdMode").input_value() == "auto" and pg.locator("#hcdModel").input_value() == "claude-opus-5-5"
    use = pg.locator(".hcd-use")
    assert pg.locator("#hcdEffort").input_value() == "high" and use.text_content() == "21%" and "Rs 413 of your Rs 2,000 monthly limit" in use.get_attribute("title")
    assert pg.locator("#hcdRepo option").first.text_content() == "shop-api"                       # short in the row, the full name on hover
    # attach a screenshot and a log; a video is refused in words
    shot, logf, vid = tmp_path / "shot.png", tmp_path / "error.log", tmp_path / "clip.mp4"
    shot.write_bytes(PNG)
    logf.write_text("ZeroDivisionError in total()")
    vid.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    pg.locator("#hcdFile").set_input_files([str(shot), str(logf), str(vid)])
    pg.wait_for_function("() => document.querySelectorAll('#hcdTray .hcd-att').length === 2")
    assert "pictures or text files" in pg.locator("#toast").text_content()
    assert pg.locator("#hcdTray img").count() == 1 and "error.log" in pg.locator("#hcdTray").text_content()
    # the "+" menu and typed slash commands set things; her words stay hers
    pg.locator(".hcd-plus").click()
    menu = pg.locator(".hmenu").text_content()
    assert "Add files or photos" in menu and "/plan" in menu and "/review" in menu
    pg.get_by_text("/tests", exact=True).click()
    assert "Write tests" in pg.locator("#hcdTray").text_content()
    pg.locator("#hcdBase").select_option("release")
    pg.locator("#hcdModel").select_option("claude-sonnet-5-5")
    pg.locator("#hcdEffort").select_option("low")
    pg.locator("#hcdLine").fill("/plan cover the empty cart")
    _shot(pg, "p3-1-composer")
    pg.keyboard.press("Enter")                                                                    # Enter starts
    pg.wait_for_selector("#hcdTop")
    sent = [c for c in calls if c[0] == "start"][-1][1]
    assert sent["text"] == "cover the empty cart" and sent["kind"] == "tests" and sent["mode"] == "plan"
    assert sent["repo"] == "meghana/shop-api" and sent["base"] == "release" and sent["model"] == "claude-sonnet-5-5" and sent["effort"] == "low"
    assert [d["name"] for d in sent["docs"]] == ["error.log"] and sent["docs"][0]["text"] == "ZeroDivisionError in total()"
    assert sent["images"][0]["name"] == "shot.png" and sent["images"][0]["data"].startswith("data:image/png;base64,")
    # the session shows what she attached and what it runs on
    pg.wait_for_function("() => { const i = document.querySelector('#hcdCol img.hcd-pic'); return i && i.src.startsWith('blob:') && i.naturalWidth === 1; }")
    assert "error.log" in pg.locator("#hcdCol .hcd-me").text_content()
    rail = pg.locator("#hcdRail").text_content()
    assert "Works from" in rail and "release" in rail and "Plan first" in rail and "Claude Sonnet 5.5 · low" in rail and "Rs 4.20" in rail
    _shot(pg, "p3-2-session")
    # back home: the box is empty again, and /review goes to the reviews screen
    pg.locator("[data-go='home']").first.click()
    pg.wait_for_selector("#hcdLine")
    assert pg.locator("#hcdLine").input_value() == "" and pg.locator("#hcdTray .hcd-att").count() == 0
    pg.locator("#hcdLine").fill("/review 12")
    pg.keyboard.press("Enter")
    pg.wait_for_selector("#hcdRevNew")
    assert ("review", {"repo": "meghana/shop-api", "pr": 12}) in calls and len([c for c in calls if c[0] == "start"]) == 1
    assert not errs, errs
    ctx.close()


def test_a_forced_model_is_shown_not_offered_and_a_link_prefills(arena_server):  # noqa: F811
    forced = {"model": "Claude Haiku 5.5", "why": "Every Claude call on this server runs on this model (the server's own setting)."}
    ctx, pg, errs, calls = _page(arena_server, url="/console/code?prompt=Fix%20the%20footer&repo=meghana/site&branch=trunk-2&mode=ask",
                                 forced=forced, usage={"spent_inr": 0, "limit_inr": 0, "pct": 0, "over": False}, width=1000)
    assert pg.url.endswith("/console/code")                                                       # the link's words are used once, then gone
    assert pg.locator("#hcdLine").input_value() == "Fix the footer" and pg.locator("#hcdRepo").input_value() == "meghana/site"
    assert pg.locator("#hcdMode").input_value() == "ask" and pg.locator("#hcdBase").input_value() == "trunk-2"
    assert pg.locator("#hcdModel").count() == 0 and pg.locator("#hcdEffort").count() == 0         # no choice is offered
    fx = pg.locator("#hcdModelFixed")
    assert fx.text_content() == "Claude Haiku 5.5" and "server's own setting" in fx.get_attribute("title")
    assert pg.locator(".hcd-use").count() == 0                                                    # nothing spent, no limit: no figure
    assert len(calls) == 0                                                                        # a link never starts anything
    row = pg.locator(".hcd-askrow").bounding_box()
    assert row["x"] >= 0 and row["x"] + row["width"] <= 1000
    pg.locator("#hcdRepo").select_option("meghana/shop-api")                                      # another repo: its own default branch
    pg.wait_for_function("() => document.querySelector('#hcdBase option').textContent === 'main'")
    assert pg.locator("#hcdLine").input_value() == "Fix the footer"                               # her words survive the change
    _shot(pg, "p3-3-forced")
    assert not errs, errs
    ctx.close()
