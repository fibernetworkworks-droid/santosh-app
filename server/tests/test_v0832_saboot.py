"""v0.832 SABOOT (L11 of docs/LOVABLE_STUDIO_PLAN.md, owner: "L11 SABOOT"): nothing is called done that a check did not prove.

The proof the plan asks for: a PLANTED BAD-RULE app is refused at publish. Around it: the rule tests play the rules on the
real engine (and catch a planted engine bug), the browser check opens a built app at phone + desktop size and walks the
Hoola Cloud journey through the sealed frame, the quick / deep scans name what they found, and the tool says all of it
before it says 'done'."""
import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _refused, _tool, ae_env  # noqa: F401  (fixture + helpers)
from tests.test_v0827_hoola_cloud import ORDERS, _app
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

MENU = {"op": "add_list", "key": "menu", "label": "Menu", "fields": [
    {"key": "dish", "label": "Dish", "type": "text", "required": True}, {"key": "price", "label": "Price", "type": "number"}],
    "rules": {"create": "admin", "read": "public", "update": "admin", "delete": "admin"}}
APP_JS = "document.getElementById('root').textContent = 'Mithai orders - sample app';"
BROKEN_JS = "document.getElementById('root').textContent = 'x'; throw new Error('planted crash');"


def _built(r, js=APP_JS, extra_src=None):
    """A built version 1 without the Docker box: a tiny static app in dist/, the source beside it."""
    from app.appengine import service as AE
    d = AE.ver_dir(r, 1)
    (d / "dist" / "assets").mkdir(parents=True, exist_ok=True)
    (d / "dist" / "index.html").write_text('<!doctype html><html><head><title>x</title></head><body><div id="root"></div>'
                                           '<script src="assets/app.js"></script></body></html>')
    (d / "dist" / "assets" / "app.js").write_text(js)
    shutil.copytree(AE.src_dir(r), d / "src", ignore=shutil.ignore_patterns("node_modules", "dist"), dirs_exist_ok=True)
    for rel, text in (extra_src or {}).items():
        (d / "src" / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / "src" / rel).write_text(text)
    (d / "build.json").write_text(json.dumps({"ok": True, "types_ok": True, "types": [], "version": 1}))
    AE._save(r.id, version=1, status="ready")
    return AE._load(T, r.id)


def _chromium():
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            exe = os.environ.get("HOOLA_CHROMIUM") or ""
            pw.chromium.launch(**({"executable_path": exe} if exe else {})).close()
    except Exception as e:                                  # noqa: BLE001
        pytest.skip("no Chromium here: " + str(e)[:80])


def _checks_on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_PUBLISH_CHECKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()


# ---------------------------------------------------------------- 1. rule tests on the real engine
def test_rule_tests_play_the_real_engine_and_catch_a_planted_bug(ae_env, monkeypatch):
    from app.appengine import cloud as CL
    from app.appengine import saboot as SB
    from app.site import webapp as W
    aid, r = _app([ORDERS, MENU])
    t = SB.rule_tests(r)
    assert t["ok"] and t["lists"] == 2 and t["count"] >= 25, t["failed"]
    names = {(c["list"], c["check"]) for c in t["checks"]}
    assert ("orders", "read as another member") in names and ("menu", "add as a member") in names     # own-isolation + admin-only add
    assert "Rule tests passed" in SB.say_rule_tests(t)
    assert SB.rule_tests_current(r) and SB.overview(r)["rule_tests"]["stale"] is False
    # the scratch dataset leaves nothing behind
    from sqlalchemy import select
    from app.db import session
    with session() as s:
        assert s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id.like(f"ae:{r.id}:t"))).first() is None
    # a rule change makes the old proof stale
    CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "admin"}])
    assert SB.rule_tests_current(r) is None and SB.overview(r)["rule_tests"]["stale"] is True
    # PLANTED ENGINE BUG: "change" lets anyone through -> the rule test fails and names the check
    monkeypatch.setattr(W, "_can_write", lambda *a, **k: True)
    bad = SB.rule_tests(r)
    assert not bad["ok"] and any("change as another member" == f["check"] for f in bad["failed"])
    assert "FAILED" in SB.say_rule_tests(bad) and "should have been 'denied'" in SB.say_rule_tests(bad)


def test_the_tool_plays_the_rules_when_a_rule_changes_and_says_not_done(ae_env):
    aid, r = _app()
    out = _tool(action="cloud_change", app=aid, changes=[ORDERS])
    assert out["rule_tests"]["ok"] and "Rule tests passed" in out["say"]
    out = _tool(action="cloud_change", app=aid, changes=[{"op": "label", "list": "orders", "field": "item", "label": "Thing"}])
    assert "rule_tests" not in out                                    # copy / label changes are never tested
    assert _tool(action="tests", app=aid)["ok"] is True
    assert "Build the app first" in _refused(action="scan", app=aid)


# ---------------------------------------------------------------- 2. the planted bad-rule app is refused at publish
def test_planted_bad_rule_app_is_refused_at_publish(ae_env, monkeypatch):
    from app.appengine import cloud as CL
    from app.appengine import saboot as SB
    from app.appengine import service as AE
    _checks_on(monkeypatch)
    monkeypatch.setattr(SB, "browser_check", lambda r, force=False: {"ran": False, "why": "stub"})
    aid, r = _app([ORDERS, MENU])
    r = _built(r)
    assert AE.publish_check(r, 1) == []                                               # a good app has no blocker
    # PLANT: the rules file is edited by hand (the migration guard is bypassed): anyone can read everyone's phone numbers
    sch = CL.schema(r)
    sch["lists"][0]["rules"]["read"] = "public"
    CL._save_schema(r, sch)
    with pytest.raises(AE.AppEngineError) as e:
        AE.publish(T, aid, 1, confirm=True)
    assert e.value.code == 409 and "Anyone on the internet can read phone" in str(e.value) and "list orders" in str(e.value)
    assert not AE._load(T, aid).live_version
    # fixing the rule lets it through the scan again
    CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "own"}])
    assert AE.publish_check(AE._load(T, aid), 1) == []
    # the other way in: she says yes on purpose (confirm_public) -> kept as her recorded yes, only a warning
    CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "public", "confirm_public": True}])
    q = SB.quick(AE._load(T, aid), 1)
    assert q["ok"] and any(x["level"] == "warn" and "you said yes" in x["say"] for x in q["items"])
    assert AE.publish_check(AE._load(T, aid), 1) == []
    # a rule change away from public drops her old yes
    CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "own"}])
    assert not CL.schema(r)["lists"][0].get("public_ack")


def test_secrets_and_a_failing_rule_test_block_publish(ae_env, monkeypatch):
    from app.appengine import saboot as SB
    from app.appengine import service as AE
    from app.site import webapp as W
    _checks_on(monkeypatch)
    monkeypatch.setattr(SB, "browser_check", lambda r, force=False: {"ran": False, "why": "stub"})
    aid, r = _app([ORDERS])
    r = _built(r, extra_src={"src/pages/Pay.tsx": 'const KEY = "sk-' + "a1B2c3D4e5F6g7H8i9J0k1L2" + '";\nexport default function Pay() { return null; }\n'})
    bl = AE.publish_check(r, 1)
    assert any("src/pages/Pay.tsx:1" in b and "API key" in b for b in bl), bl
    (AE.ver_dir(r, 1) / "src" / "src/pages/Pay.tsx").unlink()
    (AE.ver_dir(r, 1) / "dist/assets/app.js").write_text("var k='ghp_" + "a" * 36 + "';")
    assert any("dist/assets/app.js" in b and "GitHub token" in b for b in AE.publish_check(r, 1))      # the built file is scanned too
    (AE.ver_dir(r, 1) / "dist/assets/app.js").write_text(APP_JS)
    assert AE.publish_check(r, 1) == []
    monkeypatch.setattr(W, "_can_write", lambda *a, **k: True)
    bl = AE.publish_check(r, 1)
    assert any("Rule tests FAILED" in b for b in bl), bl


# ---------------------------------------------------------------- 3. the browser check, in real Chromium
def test_browser_check_walks_the_app_at_phone_and_desktop_size(ae_env):
    _chromium()
    from app.appengine import saboot as SB
    from app.appengine import service as AE
    from app.site import webapp as W
    from sqlalchemy import select
    from app.db import session
    aid, r = _app([ORDERS, MENU])
    r = _built(r)
    b = SB.browser_check(r, force=True)
    assert b["ran"] and b["ok"], (b.get("problems"), b.get("sizes"))
    assert [s["size"] for s in b["sizes"]] == ["phone", "desktop"] and all(s["shows_something"] and s["fits_width"] for s in b["sizes"])
    steps = {s["step"]: s["ok"] for s in b["sizes"][1]["journey"]["steps"]}
    assert steps["reach Hoola Cloud from the app"] and steps["sign up"] and steps["add an entry to 'orders'"]
    assert steps["see it in the list"] and steps["change it"] and steps["remove it"] and steps["sign out"], steps
    assert "walked 8 steps" in SB.say_browser(b) or "walked" in SB.say_browser(b)
    with session() as s:                                          # the check's own people never stay in the preview data
        assert s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.email.like("hoola-check-%"))).first() is None
    assert SB.browser_check(r)["at"] == b["at"]                   # cached for the same version + schema
    # a crashing app fails the check and says what happened
    _built(r, js=BROKEN_JS)
    bad = SB.browser_check(AE._load(T, aid), force=True)
    assert bad["ran"] and not bad["ok"] and any("planted crash" in p for p in bad["problems"]), bad
    assert "FAILED" in SB.say_browser(bad)


def test_the_tool_attaches_the_browser_proof_to_a_build_answer(ae_env):
    _chromium()
    from app.agent import appengine_tools as AT
    aid, r = _app([ORDERS])
    r = _built(r)
    out = AT._prove(T, aid, {"built": True, "say": "Built version 1."})
    assert out["browser_check"]["ok"] and "Browser check passed" in out["say"]
    r = _built(r, js=BROKEN_JS)
    out = AT._prove(T, aid, {"built": True, "say": "Built version 1."})
    assert out["browser_check"]["ok"] is False and "Fix this before you say it is done" in out["say"]
    plain = AT._prove(T, _app()[0], {"built": True, "say": "ok"})                  # no data = no walk
    assert "browser_check" not in plain


# ---------------------------------------------------------------- 4. deep scan + routes
def test_deep_scan_and_routes(ae_env, monkeypatch):
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.appengine import saboot as SB
    monkeypatch.setattr(SB, "browser_check", lambda r, force=False: {"ran": False, "why": "stub"})
    aid, r = _app([ORDERS])
    page = ('export default function A() {\n  const rows = hoola.db.collection("ghost").list();\n'
            '  return <a href="javascript:alert(1)" target="_blank">x</a>;\n}\n')
    r = _built(r, extra_src={"src/pages/A.tsx": page})
    d = SB.deep(r, 1)
    where = {(x["level"], x["say"][:30]) for x in d["items"]}
    assert not d["ok"] and d["fail"] >= 2
    assert any("ghost" in x["say"] and x["level"] == "fail" for x in d["items"])
    assert any("javascript:" in x["say"] and x["level"] == "fail" for x in d["items"])
    assert any("noopener" in x["say"] for x in d["items"]) and any("orders" in x["where"] and x["level"] == "info" for x in d["items"])
    assert "no model reviews the code" in d["not_a_model_review"]
    c = TestClient(main.app)
    h = {"Authorization": f"Bearer {KEY}"}
    assert c.get(f"/api/appengine/{aid}/checks", headers={}).status_code == 401
    ov = c.get(f"/api/appengine/{aid}/checks", headers=h).json()
    assert ov["deep"]["fail"] >= 2
    t = c.post(f"/api/appengine/{aid}/checks/tests", headers=h).json()
    assert t["ok"] and t["lists"] == 1
    assert c.post(f"/api/appengine/{aid}/checks/quick", headers=h).json()["kind"] == "quick"
    assert c.post(f"/api/appengine/{aid}/checks/nope", headers=h).status_code == 400
    # the tool reads the same scans
    assert _tool(action="scan", app=aid, what="deep")["kind"] == "deep" and _tool(action="scan", app=aid)["kind"] == "quick"
    from app.agent import turnmode as TM
    tk = TM.MODE.set("plan")
    try:
        assert _tool(action="tests", app=aid)["ok"]                                    # reads still work in Plan mode
    finally:
        TM.MODE.reset(tk)


# ---------------------------------------------------------------- 5. the Studio's Publish tab, in a real browser
def test_publish_tab_checks_in_a_browser(arena_server, ae_env, monkeypatch):
    base, browser, key = arena_server
    _checks_on(monkeypatch)
    from app.appengine import cloud as CL
    from app.appengine import saboot as SB
    from app.appengine import service as AE
    monkeypatch.setattr(SB, "browser_check", lambda r, force=False: {"ran": False, "why": "stub"})
    aid = AE.create(T, "Mithai orders")["id"]
    r = AE._load(T, aid)
    CL.apply_changes(r, [ORDERS])
    r = _built(r)
    sch = CL.schema(r)
    sch["lists"][0]["rules"]["read"] = "public"                       # the planted bad rule
    CL._save_schema(r, sch)
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/app/{aid}/publish")
    page.locator(".ae-checks h3").wait_for(timeout=20000)
    page.locator("#aeChecks", has_text="Rule tests").wait_for()
    page.click("[data-ae-chk=tests]")
    page.locator("#aeChecks li", has_text="Rule tests").locator(".pill", has_text="Passed").wait_for(timeout=20000)
    page.click("[data-ae-chk=quick]")
    page.locator("#aeChecks", has_text="Stops going live").wait_for(timeout=20000)
    assert "Anyone on the internet can read phone" in page.inner_text("#aeChecks")
    shots = os.environ.get("CONSOLE_SHOTS")
    if shots:
        page.screenshot(path=os.path.join(shots, "ae11-1-checks.png"), full_page=True)
    page.click("[data-ae=publish]")
    page.click("[data-x=yes]")
    page.locator("#aePubMsg .ae-probs", has_text="Anyone on the internet can read phone").wait_for(timeout=20000)
    assert not AE._load(T, aid).live_version
    ctx.close()
    assert not errors, errors


def test_version_story():
    src = open(os.path.join(os.path.dirname(__file__), "..", "app", "main.py"), encoding="utf-8").read()
    assert "SABOOT" in src and "L11" in src
