"""v0.693 HOOLA APP STUDIO: the native-app builder as its own app at /console/apps (the Web Studio's twin).

Held here: the page is served like the Web Studio (same CSP), the console sidebar opens it, every app job's progress
lines become server-timed steps in English (design: looks, every screen with a count, checks; Android / iPhone: Kotlin
per screen, compile rounds, ready / failed), the app view carries those steps + the build state at a glance, and a real
browser walks every page of the Studio on a real designed app (the model is the v0.128 fake that writes real screens)."""
import os
import time
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401
from tests.test_v128_appdesign import T, app_env  # noqa: F401
from tests.test_life import conv_ctx

D = Path(__file__).resolve().parents[1] / "app"


def test_page_route_and_sidebar_row(env):
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/console/apps")
    assert r.status_code == 200 and "Hoola App Studio" in r.text
    assert "appstudio.js" in r.text and "webstudio.css" in r.text and "appstudio.css" in r.text and "vendor/qrcode.js" in r.text
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"] and r.headers["x-frame-options"] == "DENY"
    v2 = (D / "static" / "console" / "v2.js").read_text()
    assert "['appdev','App Development']" in v2 and "location.assign('/console/apps'" in v2 and "IC.appdev" in v2


def test_engine_lines_become_english_steps():
    from app.appmaker import activity as A
    assert A.english("Kotlin: Cart (3/11)") == ("Writing Kotlin for every screen", "Cart", "kotlin", 3, 11)
    assert A.english("Compile ki galtiyan theek: round 2")[:2] == ("Fixing compile errors", "round 2")
    assert A.english("Jaanch chal rahi hai", "har screen · Android + iPhone · 360 px")[0] == "Checking every screen"
    assert A.english("Look 2: Warm market", "Look 2 / 3: home screen ban raha hai") == ("Look 2: Warm market", "", "look2", None, None)
    assert A.english("Device check: cart crash hui - theek kar raha hoon")[0] == "Fixing crashes found on the phone check"
    lab, note, *_ = A.english("Rok diya", "Aapke kehne par roka")
    assert lab == "Paused" and note == ""                                 # a Hinglish note never reaches the English Studio


def test_build_hooks_write_a_timed_log(app_env, tmp_path):
    from app.appmaker import activity as A
    A.on_build(T, "app_x", "android", {"status": "writing", "now": "Screens Kotlin mein likh raha hoon"})
    A.on_build(T, "app_x", "android", {"now": "Kotlin: Home (1/3)"}, {"home": "writing"})
    A.on_build(T, "app_x", "android", {"now": "Kotlin: Cart (2/3)"}, {"home": "written", "cart": "writing"})
    A.on_build(T, "app_x", "android", {"now": "Android Studio ki tarah compile ho raha hai"})
    a = A.read(T, "app_x")
    labels = [s["label"] for s in a["steps"]]
    assert labels == ["Writing every screen in Kotlin", "Writing Kotlin for every screen", "Compiling the Android app"]
    k = a["steps"][1]
    assert k["done"] == 1 and k["total"] == 3 and k["note"] == "Cart" and k["state"] == "done" and k["end"] >= k["at"]
    assert a["steps"][-1]["state"] == "run" and a["job"] == "android" and a["now"] >= a["started"]
    A.on_build(T, "app_x", "android", {"status": "ready", "now": ""})
    a = A.read(T, "app_x")
    assert a["ended"] and a["steps"][-1]["label"] == "Android app ready" and not any(s["state"] == "run" for s in a["steps"])
    A.on_build(T, "app_y", "ios", {"status": "failed", "error": "no mac"})             # nothing started: nothing written
    assert A.read(T, "app_y")["steps"] == []


def _designed_app():
    from app.appmaker import service as S
    ctx = conv_ctx()
    v = S.new(T, "Sharma Sweets ki app, ghar pe delivery, order WhatsApp par", ctx.conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main road, Akot", "upi_id": "sharma@okicici"})
    S.approve_plan(T, v["id"], ctx.conversation_id)
    S.choose_look(T, v["id"], 0, None, ctx.conversation_id)
    return S.get(T, v["id"])


def test_design_run_is_logged_and_the_view_carries_it(app_env):
    v = _designed_app()
    assert v["status"] == "ready", v.get("error")
    a = v["activity"]
    labels = [s["label"] for s in a["steps"]]
    assert "Designing every screen" in labels and "Checking every screen" in labels and a["ended"]
    d = next(s for s in a["steps"] if s["label"] == "Designing every screen")
    assert d["total"] >= 5 and d["done"] >= d["total"] - 1 and d["key"] == "design"
    assert labels[-1] == "App design ready" and not any(s["state"] == "run" for s in a["steps"])
    assert all("raha" not in (s.get("note") or "") for s in a["steps"])                # English notes only
    assert v["builds"]["android"] == {"status": None, "build": None, "now": None} and "conv" in v
    from app.appmaker import service as S
    lst = S.everything(T)["apps"]
    assert lst and "builds" in lst[0] and "activity" not in lst[0]                       # the list stays light


def test_studio_script_markers():
    js = (D / "static" / "console" / "appstudio.js").read_text()
    for m in ("'/api/apps'", "/api/apps-ideas?", "/plan', {drop:", "/look', {index:", "/approve', {hash: S(CUR.hash)}",
              "/android`", "/ios`", "/store`", "/appstore`", "/crashes`", "/rollout`", "/ops?days=7", "/members`",
              "track: 'production', her_tap: true", "/appstore/submit', {her_tap: true}", "/rollout/' + what, {her_tap: true}",
              "App Studio: this chat is only about app", "hoola.as.conv.", "data-t0", "Approve design", "qrcode(0, 'M')"):
        assert m in js, m
    assert "allow-same-origin" not in js                         # the model-written prototype never shares our origin
    assert js.count("confirm(") >= 7                             # every irreversible / public step asks first


def test_every_studio_page_in_a_real_browser(app_env, arena_server):
    import threading
    out = {}
    th = threading.Thread(target=lambda: out.update(v=_designed_app()))   # the engine's own Chromium runs off this
    th.start()                                                            # test's Playwright thread
    th.join(600)
    v = out["v"]
    base, browser, key = arena_server
    errs = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")   # the sandboxed prototype frame has no storage
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/console/apps#/")
        pg.wait_for_selector(".hero h1", timeout=20000)
        assert "What app should we make today?" in pg.inner_text(".hero h1")
        if os.environ.get("APP_SHOTS"):
            pg.wait_for_timeout(800)
            pg.screenshot(path=f"{os.environ['APP_SHOTS']}/home-{scheme}.png")
        assert "Sharma Sweets" in pg.inner_text(".side") and "Sharma Sweets" in pg.inner_text(".grid")
        if scheme == "dark":
            ctx.close()
            continue
        pg.goto(base + "/console/apps#/apps")
        pg.wait_for_selector("#asAll .card", timeout=10000)
        pg.fill("#asFind", "zzz-nothing")
        assert pg.is_visible("#asNone")
        pg.goto(base + "/console/apps#/ideas")
        pg.wait_for_selector("#asIdeas .icard", timeout=20000)
        assert "ideas" in pg.inner_text("#asIdeaCount")
        want = {"plan": "The plan", "looks": "Pick a look", "screens": "designed", "prototype": "Try it on your own phone",
                "android": "Android app", "iphone": "iPhone app", "store": "Google Play", "data": "Members and roles",
                "business": "Everything your app runs on", "health": "Crashes", "settings": "App details",
                "history": "Every design change is kept"}
        for view, text in want.items():
            pg.goto(base + f"/console/apps#/app/{v['id']}/{view}")
            try:
                pg.wait_for_function("([t, v]) => { const p = document.querySelector('#asPane'); const pb = p && p.querySelector('.pbody, .stage');"
                                   " return pb && pb.innerText.includes(t) && (v === 'history' || !!p.querySelector(`.views [data-view='${v}'][aria-current='page']`)); }",
                                   arg=[text, view], timeout=20000)
            except Exception:
                raise AssertionError(f"{view}: " + pg.inner_text("#asPane")[:600])
            assert pg.locator(f".views [data-view='{view}'][aria-current='page']").count() == (0 if view == "history" else 1)
            if os.environ.get("APP_SHOTS"):
                pg.wait_for_timeout(1200)
                pg.screenshot(path=f"{os.environ['APP_SHOTS']}/{view}.png")
        pg.goto(base + f"/console/apps#/app/{v['id']}/screens")
        pg.wait_for_selector("#asPane .scrn img[src^='blob:']", timeout=20000)         # real screen images with her token
        # "Approve design" is open only when the server's checks have nothing blocking (and then it sends the hash)
        assert pg.locator("#asPane [data-act='approve']").is_enabled() == (not v["checks"]["blocking"])
        if v["checks"]["blocking"]:
            assert "blocking" in pg.inner_text("#asPane")
        assert "Worked for" in pg.inner_text("#asState")                               # the server's timed steps
        pg.goto(base + f"/console/apps#/app/{v['id']}/prototype")
        pg.wait_for_selector("#asPane iframe[sandbox='allow-scripts allow-forms']", timeout=10000)
        assert pg.locator("#asPane .qr svg").count() == 1
        ctx.close()
    assert not errs, errs
