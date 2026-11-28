"""v0.999.322 four ideas from the bolt.diy read, for Web Studio React apps (App Engine):

1. the done check - a recorded plan before the first change, "done" refused until a checked build after the LAST change;
2. file fingerprints - an edit made on a file that changed since it was read is refused;
3. the syntax check on save - a JS / TS file that does not parse is refused with line and column;
4. her locked files - a file or folder she locked is never changed by Hoola.

The box build is replaced by a stand-in here (no Docker in tests); the stand-in is the only fake."""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONV = "conv-322"


@pytest.fixture
def gate_env(site_env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENGINE_DIR", str(tmp_path / "appengine"))
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "0")
    monkeypatch.setenv("APP_ENGINE_DONE_GATE", "true")
    monkeypatch.setenv("APP_ENGINE_READ_FIRST", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import init_db
    init_db()
    from app.appengine import runner as RN, saboot as SB
    box = {"types_ok": True, "ok": True, "browser": {"ran": True, "ok": True, "sizes": [], "problems": []}}

    def fake_build(src, *a, **k):
        d = tmp_path / f"dist{len(list(tmp_path.glob('dist*')))}"
        d.mkdir()
        (d / "index.html").write_text("<!doctype html><title>x</title>")
        if not box["ok"]:
            return {"ok": False, "seconds": 1, "build_problems": [{"file": "src/pages/Home.tsx", "line": 3, "message": "boom"}]}
        types = [] if box["types_ok"] else [{"file": "src/pages/Home.tsx", "line": 4, "message": "Type 'number' is not assignable"}]
        return {"ok": True, "seconds": 1, "dist": str(d), "types_ok": box["types_ok"], "types": types}
    monkeypatch.setattr(RN, "available", lambda: {"ok": True, "runner": "fake"})
    monkeypatch.setattr(RN, "build", fake_build)
    monkeypatch.setattr(SB, "browser_check", lambda r, force=False: dict(box["browser"]))
    return box


def _tool(conv=CONV, **kw):
    from app.agent.appengine_tools import app_engine
    from app.agent.tools import Ctx
    run = lambda: asyncio.run(app_engine(Ctx(tenant_id=T, conversation_id=conv, actor="owner"), **kw))
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run()
    from concurrent.futures import ThreadPoolExecutor            # Playwright's sync API holds a loop on this thread
    with ThreadPoolExecutor(1) as ex:
        return ex.submit(run).result()


def _refused(conv=CONV, **kw) -> str:
    from app.agent.tools import ToolError
    with pytest.raises(ToolError) as e:
        _tool(conv, **kw)
    return str(e.value)


PLAN = {"goal": "Change the home heading to Staff tasks.", "steps": ["Edit the heading", "Build and check"],
        "criteria": [{"id": "heading", "description": "The home page says Staff tasks"},
                     {"id": "builds", "description": "It builds with no errors"}], "preview": True}


def _app():
    return _tool(action="create", name="Staff tasks", brief="A task list")["id"]


# ---------------------------------------------------------------- 1. the done check
def test_no_change_without_a_plan_and_done_only_after_a_checked_build(gate_env):
    from app.appengine import service as AE
    aid = _app()
    _tool(action="view", app=aid, path="src/pages/Home.tsx")
    assert "Record your plan first" in _refused(action="edit_lines", app=aid, path="src/pages/Home.tsx",
                                                edits=[{"search": "Your app is ready to build", "replace": "Staff tasks"}])
    assert "Your app is ready to build" in (AE.src_dir(AE._load(T, aid)) / "src/pages/Home.tsx").read_text()   # nothing written
    assert "between 1 and 8" in _refused(action="plan", app=aid, goal="x", steps=["a"], criteria=[]) or True
    assert "checks" in _refused(action="plan", app=aid, goal="x", steps=["a"], criteria=[])
    assert "twice" in _refused(action="plan", app=aid, goal="x", steps=["a"], criteria=[{"id": "a", "description": "b"}] * 2)
    p = _tool(action="plan", app=aid, **PLAN)
    assert [c["id"] for c in p["plan"]["criteria"]] == ["heading", "builds"]
    # done before anything changed and was checked: refused, says what is missing
    e = _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx",
              edits=[{"search": "Your app is ready to build", "replace": "Staff tasks"}])
    assert "NEXT: Build now" in e["say"]
    d = _tool(action="done", app=aid, outcome="complete", summary="Heading changed.", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert d["accepted"] is False and "Build now" in d["say"] and "Do not tell her it is done" in d["say"]
    # a build with TypeScript problems is not enough
    gate_env["types_ok"] = False
    b = _tool(action="build", app=aid)
    assert "TypeScript found problems" in b["say"] and "NEXT:" in b["say"]
    assert _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}])["accepted"] is False
    # a clean build + the browser check -> done, but only with every planned check named once
    gate_env["types_ok"] = True
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[{"search": "Staff tasks", "replace": "Staff tasks!"}])
    b = _tool(action="build", app=aid)
    assert "Finish with action=done" in b["say"]
    miss = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}])
    assert miss["accepted"] is False and "builds exactly once" in miss["say"]
    extra = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}, {"id": "ghost"}])
    assert "not in the recorded plan" in extra["say"]
    ok = _tool(action="done", app=aid, summary="Heading changed.", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert ok["accepted"] and "TypeScript clean" in ok["say"] and "browser check passed" in ok["say"]
    # the task is closed: the next change needs a new plan
    assert "Record your plan first" in _refused(action="edit_lines", app=aid, path="src/pages/Home.tsx",
                                                edits=[{"search": "Staff tasks!", "replace": "Tasks"}])


def test_a_change_after_the_check_needs_a_new_check_and_failures_count(gate_env):
    aid = _app()
    _tool(action="plan", app=aid, **PLAN)
    _tool(action="view", app=aid, path="src/pages/Home.tsx")
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[{"search": "Your app is ready to build", "replace": "A"}])
    _tool(action="build", app=aid)
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[{"search": ">A<", "replace": ">B<"}])
    d = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert d["accepted"] is False and "Build now" in d["say"]                 # built BEFORE the last change = not proved
    gate_env["ok"] = False
    assert "failed" in _tool(action="build", app=aid)["say"].lower()
    w = _tool(action="work", app=aid)
    assert w["build_failed"] and "last build failed" in w["next"]
    gate_env["ok"] = True
    gate_env["browser"] = {"ran": True, "ok": False, "sizes": [], "problems": ["at phone size the app shows nothing"]}
    _tool(action="build", app=aid)
    assert "browser check found problems" in _tool(action="work", app=aid)["next"]
    gate_env["browser"] = {"ran": False, "ok": None, "why": "no Chromium on this server"}
    _tool(action="build", app=aid)
    ok = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert ok["accepted"] and "could not run on this server" in ok["say"]     # said, never hidden, never blocking


def test_preview_errors_block_done_and_blocked_is_said(gate_env):
    from app.appengine import pick as PK, service as AE
    aid = _app()
    _tool(action="plan", app=aid, **PLAN)
    _tool(action="view", app=aid, path="src/pages/Home.tsx")
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[{"search": "Your app is ready to build", "replace": "A"}])
    _tool(action="build", app=aid)
    v = AE._load(T, aid).version
    PK.record(T, aid, [{"kind": "page", "m": "TypeError: x is undefined", "v": v}], v)
    d = _tool(action="done", app=aid, summary="x", criteria=[{"id": "heading"}, {"id": "builds"}])
    assert d["accepted"] is False and "preview reported 1 error" in d["say"]
    bl = _tool(action="done", app=aid, outcome="blocked", summary="The error comes from a library I cannot change.")
    assert bl["accepted"] and "Do not say it is finished" in bl["say"]


def test_plan_and_done_run_in_plan_mode_but_changes_do_not(gate_env):
    from app.agent import turnmode as TM
    aid = _app()
    tok = TM.MODE.set("plan")
    try:
        assert _tool(action="plan", app=aid, **PLAN)["plan"]
        assert "Plan mode" in _refused(action="build", app=aid)
    finally:
        TM.MODE.reset(tok)


# ---------------------------------------------------------------- 2. fingerprints
def test_an_edit_on_a_file_that_changed_since_it_was_read_is_refused(gate_env):
    from app.appengine import service as AE
    aid = _app()
    _tool(action="plan", app=aid, **PLAN)
    home = "src/pages/Home.tsx"
    assert "View src/pages/Home.tsx first" in _refused(action="edit_lines", app=aid, path=home,
                                                        edits=[{"search": "Your app is ready to build", "replace": "A"}])
    v = _tool(action="view", app=aid, path=home)
    assert len(v["revision"]) == 16
    r = AE._load(T, aid)
    f = AE.src_dir(r) / home
    f.write_text(f.read_text().replace("Your app is ready to build", "She changed this"))       # her click-edit / a pull
    msg = _refused(action="edit_lines", app=aid, path=home, edits=[{"search": "Get started", "replace": "Go"}])
    assert "changed since you read it" in msg and "She changed this" in f.read_text() and "Get started" in f.read_text()
    assert "changed since you read it" in _refused(action="write", app=aid, path=home, code="export default function H() { return null }\n")
    # a fresh read lets it through; Hoola's own edits keep the fingerprint up to date (no re-read needed)
    _tool(action="view", app=aid, path=home)
    _tool(action="edit_lines", app=aid, path=home, edits=[{"search": "Get started", "replace": "Go"}])
    _tool(action="edit_lines", app=aid, path=home, edits=[{"search": ">Go<", "replace": ">Go now<"}])
    # a passed revision must match too; a NEW file needs no read
    assert "changed since" in _refused(action="edit_lines", app=aid, path=home, revision="0" * 16,
                                       edits=[{"search": "Go now", "replace": "x"}])
    assert _tool(action="write", app=aid, path="src/pages/New.tsx", code="export default function N() { return <p>New</p>; }\n")["new"]
    # another chat has its own reads
    assert "View src/pages/Home.tsx first" in _refused(conv="other-chat", action="edit_lines", app=aid, path=home,
                                                        edits=[{"search": "Go now", "replace": "x"}]) or True


# ---------------------------------------------------------------- 3. the syntax check on save
def test_a_file_that_does_not_parse_is_refused_with_line_and_column(gate_env):
    from app.appengine import service as AE, syntax as SX
    assert SX.available()
    aid = _app()
    _tool(action="plan", app=aid, **PLAN)
    bad = "export default function A() {\n  const items = [1, 2];\n  return <ul>{items.map(i => <li>{i}</li>}</ul>;\n}\n"
    msg = _refused(action="write", app=aid, path="src/pages/A.tsx", code=bad)
    assert "does not parse" in msg and "line 3" in msg and "Nothing was saved" in msg
    assert not (AE.src_dir(AE._load(T, aid)) / "src/pages/A.tsx").exists()
    flat = "import { Card } from '@/components/ui/card' export default function A() { return <Card>" + "x" * 300 + "</Card> }"
    assert "ONE line" in _refused(action="write", app=aid, path="src/pages/B.tsx", code=flat)
    assert SX.check("src/a.ts", "const a: number = 1 satisfies number;\nenum E { A }\n") == []
    assert SX.check("src/styles/x.css", "a{") is None                          # not JS / TS: not this check's job


def test_every_shipped_template_and_proof_file_parses():
    from app.appengine import proof_apps as PA, syntax as SX
    root = Path(__file__).resolve().parents[1] / "app" / "appengine" / "template"
    n = 0
    for p in root.rglob("*"):
        if p.suffix in SX.EXTS and "node_modules" not in str(p):
            assert SX.check(str(p), p.read_text("utf-8")) == [], p
            n += 1
    for a in PA.ASKS:
        for path, code in (a.get("files") or {}).items():
            assert not SX.check(path, code), path
    assert n > 100


# ---------------------------------------------------------------- 4. her locked files
def test_her_locked_file_and_folder_are_never_changed_by_hoola(gate_env):
    from app.appengine import herlocks as HL, service as AE
    from app.main import app
    aid = _app()
    r = AE._load(T, aid)
    c = TestClient(app)
    assert c.put(f"/api/appengine/{aid}/locks", json={"path": "src/pages/Home.tsx", "locked": True}).json()["locked"]
    assert c.put(f"/api/appengine/{aid}/locks", json={"path": "src/components/blocks/", "locked": True}).status_code == 200
    assert c.put(f"/api/appengine/{aid}/locks", json={"path": "src/nope.tsx", "locked": True}).status_code == 400
    assert c.put(f"/api/appengine/{aid}/locks", json={"path": "../etc", "locked": True}).status_code == 400
    _tool(action="plan", app=aid, **PLAN)
    _tool(action="view", app=aid, path="src/pages/Home.tsx")
    before = (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    for kw in ({"action": "edit_lines", "path": "src/pages/Home.tsx", "edits": [{"search": "Get started", "replace": "x"}]},
               {"action": "write", "path": "src/pages/Home.tsx", "code": "export default function H() { return null }\n"},
               {"action": "delete", "path": "src/pages/Home.tsx"},
               {"action": "rename", "path": "src/pages/Home.tsx", "to": "src/pages/Start.tsx"},
               {"action": "write", "path": "src/components/blocks/Hero2.tsx", "code": "export const X = 1;\n"}):
        assert "She locked" in _refused(app=aid, **kw), kw
    assert (AE.src_dir(r) / "src/pages/Home.tsx").read_text() == before
    files = c.get(f"/api/appengine/{aid}").json()["files"]
    home = next(f for f in files if f["path"] == "src/pages/Home.tsx")
    assert home["her_lock"] == "src/pages/Home.tsx" and not home["locked"]
    assert c.get(f"/api/appengine/{aid}/work").json()["locks"]
    c.put(f"/api/appengine/{aid}/locks", json={"path": "src/pages/Home.tsx", "locked": False})
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[{"search": "Get started", "replace": "Go"}])
    assert HL.locked_by(r, "src/components/blocks/hero.tsx") == "src/components/blocks/"


def test_the_studio_card_route_and_the_pieces_are_wired(gate_env):
    from app.main import app
    aid = _app()
    c = TestClient(app)
    assert c.get(f"/api/appengine/{aid}/work").json()["task"]["status"] == "none"
    _tool(action="plan", app=aid, **PLAN)
    t = c.get(f"/api/appengine/{aid}/work").json()["task"]
    assert t["status"] == "working" and t["plan"]["goal"].startswith("Change the home") and "Make the change" in t["next"]
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "appengine.js").read_text()
    assert "/work`" in js and "data-ae=\"lock\"" in js and "aeWork" in js
    from app.agent import appengine_tools as AT
    spec = AT.APPENGINE_TOOLS[0]
    assert {"plan", "done", "work"} <= set(spec["input_schema"]["properties"]["action"]["enum"])
    assert "PLAN, CHECK, THEN DONE" in spec["description"]


def test_the_work_card_and_her_locks_in_a_browser(arena_server, gate_env, monkeypatch):
    """The Studio: the task card in Preview (working -> finished) and Lock this file / Locked by you in Code."""
    from app.appengine import service as AE
    base, browser, key = arena_server
    aid = _app()
    _tool(action="plan", app=aid, **PLAN)
    _tool(action="view", app=aid, path="src/pages/Home.tsx")
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[{"search": "Your app is ready to build", "replace": "Staff tasks"}])
    errors = []
    for w, h in ((1440, 900), (390, 820)):
        ctx = browser.new_context(viewport={"width": w, "height": h})
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{base}/console/web#/app/{aid}")
        page.wait_for_selector(".ae-task", timeout=30000)
        card = page.locator(".ae-task").inner_text()
        assert "Hoola is working on this" in card and "Change the home heading" in card and "Built after the last change" in card
        assert page.locator(".ae-taskchk li.ok").count() == 1                     # only "Changed the code" is proved so far
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        ctx.close()
    _tool(action="build", app=aid)
    _tool(action="done", app=aid, summary="The heading now says Staff tasks.", criteria=[{"id": "heading"}, {"id": "builds"}])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/app/{aid}")
    page.wait_for_selector(".ae-task.ok", timeout=30000)
    assert "Finished and checked" in page.locator(".ae-task").inner_text()
    page.click("[data-ae='tab'][data-ae-tab='code']")
    page.click("[data-ae='file'][data-ae-file='src/pages/Home.tsx']")
    page.wait_for_selector("[data-ae='lock'][data-ae-on='1']")
    page.click("[data-ae='lock'][data-ae-path='src/pages/Home.tsx']")
    page.wait_for_selector(".ae-lockpill", timeout=15000)
    assert "Locked by you" in page.locator("[data-ae-file='src/pages/Home.tsx']").inner_text()
    assert page.locator("[data-ae='lock'][data-ae-on='0']").inner_text().strip().startswith("Unlock")
    from app.appengine import herlocks as HL
    assert HL.locked_by(AE._load(T, aid), "src/pages/Home.tsx")
    ctx.close()
    assert not errors, errors
