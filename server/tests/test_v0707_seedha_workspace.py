"""v0.707 SEEDHA WORKSPACE (owner: "even when ask for website in plan mode it just starts a plan making down that search
with no proper work... why it is not landing on workspace... make a proper fix with perfect smooth transition in pages").

Two faults, both held here:
1. "Build this plan" died with a red "Data ka draft abhi theek nahi" whenever the plan's data / rules draft had a
   problem - nothing was built and she was left on the plan. Now the website is built and the lists + rules wait for
   their own fix (said in the answer).
2. Plan and Build sat on the Studio HOME under a small dotted line for up to a minute while the server wrote the plan.
   Now the page moves to the workspace the moment she sends (her words in the chat, a live work card on the real
   clock, a skeleton of the plan) and the real plan / website opens in the same place. Same for the App Studio."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0407_ek_dimaag import SCHOOL_SPEC, T, arch_env  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401


def test_build_this_plan_never_dies_on_the_data_draft(arch_env, monkeypatch):
    from app.site import architect as AR
    monkeypatch.setattr(AR, "_data_draft", lambda p, spec, ask=None: {"hash": "", "errors": ["draft failed"], "lines": [], "summary": ""})
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    card = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, notices"}).json()
    assert card["data_ready"] is False
    r = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert "The data lists and rules are not applied yet" in out["say"]
    after = c.get(f"/api/site-architect/{card['id']}").json()
    assert after["status"] == "built" and after["site"]


def test_studio_scripts_move_to_the_workspace_first():
    from pathlib import Path
    D = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    ws = (D / "webstudio.js").read_text()
    i = ws.index("if (kind === 'ask') {")
    # v0.784: the call now carries her design picks (startFromAsk(t, design)); the order it pins is unchanged
    assert ws.index("drawPending(plan, t)", i) < ws.index("await startFromAsk(t, design)", i)    # the page moves BEFORE the wait
    assert "PREFILL = t; drawHome('home')" in ws                                           # a failure goes back with her words
    assert "Starting the build" in ws                                                       # her Build tap shows at once
    a = (D / "appstudio.js").read_text()
    assert a.index("drawPending(S(body.brief))") < a.index("await api('POST', '/api/apps'")
    css = (D / "webstudio.css").read_text()
    assert "@keyframes ws-in" in css and ".doc.skel" in css and "prefers-reduced-motion:reduce){.home,.wsp{animation:none}" in css


def test_plan_mode_lands_on_the_workspace_in_a_browser(arch_env, arena_server, monkeypatch):
    from app.site import ai as AI
    from app.site import architect as AR
    slow = AI.ask_json

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            time.sleep(2.5)                                    # the plan takes a while, like the real model
            return json.loads(json.dumps(SCHOOL_SPEC))
        return slow(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.ws.mode', 'plan') }} catch (e) {{}}")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/web#/")
    pg.wait_for_selector("#wsAsk", timeout=20000)
    pg.fill("#wsAsk", "hamare school ka portal - admission, fees, notices")
    t0 = time.time()
    pg.click("form[data-form='ask'] button[type=submit]")
    pg.wait_for_selector(".wsp[data-pending='plan']", timeout=3000)                        # the workspace, at once
    assert time.time() - t0 < 2.0
    assert "hamare school ka portal" in pg.inner_text("#wsPendMsgs") and pg.locator(".doc.skel").count() == 1
    import os
    if os.environ.get("APP_SHOTS"):
        pg.wait_for_timeout(600)
        pg.screenshot(path=f"{os.environ['APP_SHOTS']}/pending-plan.png")
    pg.wait_for_function("() => location.hash.startsWith('#/plan/')", timeout=30000)               # then the real plan opens
    pg.wait_for_selector("#wsPlanMsgs", timeout=10000)
    assert "Build this plan" in pg.inner_text(".stage")
    if os.environ.get("APP_SHOTS"):
        pg.wait_for_timeout(600)
        pg.screenshot(path=f"{os.environ['APP_SHOTS']}/landed-plan.png")
    ctx.close()
    assert not errs, errs


def test_app_studio_lands_on_the_workspace_in_a_browser(arena_server, monkeypatch, tmp_path):
    from tests.test_v128_appdesign import FakeAI
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    from app.appmaker import ai as AAI
    fake = FakeAI()
    monkeypatch.setattr(AAI, "ask_json", fake)
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.as.mode', 'plan') }} catch (e) {{}}")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def slow(route):                                           # the plan takes a moment, like the real model
        if route.request.method == "POST":
            time.sleep(2.0)
        route.continue_()
    pg.route("**/api/apps", slow)
    pg.goto(base + "/console/apps#/")
    pg.wait_for_selector("#asAsk", timeout=20000)
    pg.fill("#asAsk", "Sharma Sweets ki app, ghar pe delivery, order WhatsApp par")
    t0 = time.time()
    pg.click("form[data-form='ask'] button[type=submit]")
    pg.wait_for_selector(".wsp[data-pending]", timeout=3000)                               # the workspace, at once
    assert time.time() - t0 < 2.0 and "Sharma Sweets" in pg.inner_text(".wsp .msgs")
    pg.wait_for_function("() => /^#\\/app\\/[^/]+\\/plan$/.test(location.hash)", timeout=30000)
    pg.wait_for_selector("#asPane .pbody", timeout=15000)
    assert "The plan" in pg.inner_text("#asPane")
    ctx.close()
    assert not errs, errs
