"""3D STUDIO DESK: the 3D Studio artist's own section, built like the finance desks - its own chat (kind 'studio3d') with the desk
block + the 3D tool in view; making a model in real Blender (a fake box here), following it while it builds, the renders / files /
print check, a change in her words as a new version, her usual choices + units (mm or inches) used for every new model; GLOBAL: sizes
in her units, every word English (the old 'taiyaar' gone); the refusals kept; walked in a browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.test_v141_blender import GOOD, fake   # noqa: F401

T = "default"


@pytest.fixture
def bdk(fake, monkeypatch):        # noqa: F811
    from app import b3chat as B
    from app.blender3d import sandbox
    monkeypatch.setattr(sandbox, "health", lambda: {"installed": True, "kind": "py", "no_network": True})
    B._OF.clear()
    B._BLOCK.clear()
    fa, runs, service = fake
    fa.scripts = [GOOD] * 6
    return B


def _hire():
    from app.employee import hire
    hire.hire(T, "blender_3d", trust="seekh")


def test_hire_chat_block_and_wiring(bdk):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert bdk.summary(T)["hired"] is False and "Hire me from AI Employees" in bdk.greeting(T)
    with pytest.raises(PermissionError):
        bdk.do(T, "make", {"brief": "a cup"})
    _hire()
    d = bdk.summary(T)
    assert d["hired"] and "AI-generated" in d["foot"] and d["desk"]["health"]["ready"] is True
    assert {n["go"] for n in d["desk"]["needs"]} >= {"make", "settings"}
    chat = bdk.current(T)
    assert bdk.is_3d(chat["id"]) and bdk.owns(T, chat["id"])
    assert "<studio3d_desk>" in bdk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_b3c.is_3d(conversation_id)" in src and "adm.admit_families(_b3c.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"studio3d"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/3d")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "b3desk.js" in r.text
    html = (root / "server/app/static/console/b3desk.html").read_text()
    for x in ("chatkit.js", "ncdesk.css", "b3desk.css", "b3desk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/3d')" in (root / "server/app/static/console/v2.js").read_text()
    assert "blender_3d: 'b3desk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["blender_3d"]["desk"] == "b3desk"
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["blender_3d"] in bdk.FAMILIES


def test_guards_and_refusals(bdk):
    _hire()
    with pytest.raises(PermissionError):
        bdk.do(T, "settings", {"units": "my password is hunter2"})
    with pytest.raises(bdk.B3DeskError):
        bdk.do(T, "make", {"brief": "a working pistol part I can print in STL"})
    with pytest.raises(bdk.B3DeskError):
        bdk.do(T, "settings", {"units": "furlongs"})
    with pytest.raises(bdk.B3DeskError):
        bdk.do(T, "nope", {})
    v = bdk.do(T, "make", {"brief": "A clay tea cup, 12 cm, gold handle"})
    from app.employee import hire
    hire.pause(T, "blender_3d")
    assert bdk.do(T, "get", {"id": v["id"]})["number"] == v["number"]          # reads still work
    with pytest.raises(PermissionError):
        bdk.do(T, "make", {"brief": "another cup"})


def test_make_change_defaults_units(bdk):
    S = bdk._S()
    _hire()
    s = bdk.do(T, "settings", {"defaults": {"exports": ["stl", "glb", "nope"], "views": ["front"], "print": True}, "units": "imperial"})
    assert s["units"] == "imperial" and s["defaults"]["exports"] == ["stl", "glb"] and s["set"]
    v = bdk.do(T, "make", {"brief": "A wall hook for a 2 cm pipe"})
    assert v["options"]["exports"] == ["stl", "glb"] and v["options"]["views"] == ["front"] and v["options"]["print"] is True
    k = bdk.summary(T)["desk"]
    assert len(k["busy"]) == 1
    S.run_job(v["id"])
    p = bdk.do(T, "get", {"id": v["id"]})
    assert p["status"] == "done" and p["stage"] == "ready" and p["print_check"]["closed"]
    k = bdk.summary(T)["desk"]
    assert k["done"] == 1 and dict(k["by_format"]) == {"STL": 1, "GLB": 1} and "inches" in bdk.block(T)
    v2 = bdk.do(T, "make", {"brief": "A cup", "exports": ["obj"], "print": False})                  # her choice on the job wins over the defaults
    assert v2["options"]["exports"] == ["obj"]
    bdk.do(T, "change", {"id": v["id"], "words": "make it 3 cm longer"})
    S.run_job(v["id"])
    p = bdk.do(T, "get", {"id": v["id"]})
    assert p["version"] == 2 and len(p["history"]) == 2
    assert "taiyaar" not in p["stage"]
    r = bdk.do(T, "delete", {"id": v2["id"]})
    assert r["ok"]


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def b3_server(bdk, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(bdk, b3_server):
    S = bdk._S()
    base, browser, key = b3_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/3d")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # settings: inches + usual files
    go(pg, "#/settings", "form[data-form=units]")
    pg.select_option("form[data-form=units] [name=units]", "imperial")
    pg.click("form[data-form=units] [type=submit]")
    pg.wait_for_selector("#b3Site:has-text('inches')", timeout=20000)
    pg.check("form[data-form=defs] input[name=exports][value=stl]")
    pg.click("form[data-form=defs] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    snap(pg, "b3-settings-1440")
    # make from an idea -> the model page follows the build
    go(pg, "#/make", "form[data-form=make]")
    pg.click("[data-idea='0']")
    assert "glass jar" in pg.input_value("form[data-form=make] [name=brief]")
    pg.check("form[data-form=make] input[name=turntable]")
    snap(pg, "b3-make-1440")
    pg.click("form[data-form=make] [type=submit]")
    pg.wait_for_selector(".b3-run", timeout=30000)
    snap(pg, "b3-building-1440")
    pid = pg.evaluate("location.hash.split('/').pop()")
    S.run_job(pid)
    pg.wait_for_selector(".b3-shots img", timeout=30000)
    pg.wait_for_selector("text=Download", timeout=30000)
    assert " in" in pg.inner_text(".cs-hero")                         # the size in inches
    snap(pg, "b3-model-1440")
    # change it in words -> version 2
    pg.fill("form[data-form=change] [name=words]", "Make the lid dark blue")
    pg.click("form[data-form=change] [type=submit]")
    pg.wait_for_selector(".b3-run", timeout=30000)
    S.run_job(pid)
    pg.wait_for_selector("text=Version 2", timeout=30000)
    go(pg, "#/models", ".b3-card")
    snap(pg, "b3-models-1440")
    go(pg, "#/today", ".b3-card")
    snap(pg, "b3-today-1440")
    for route, sel in (("#/today", "text=Needs you"), ("#/make", "form[data-form=make]"), ("#/models", ".b3-card"), (f"#/models/{pid}", ".b3-shots"),
                       ("#/settings", "form[data-form=defs]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#b3Page *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        if route.startswith("#/models/"):
            snap(pg, "b3-model-390")
    snap(pg, "b3-settings-390")
    assert not errs, errs
