"""v0.999.175 APPS, REDESIGNED (owner: "NOW SAME WAY FOR APPS SECTION -- GIVE ME DESIGN AND PREMIMUM, ADVANCE VIEW -- WITH PROPER
WIRING" -> design claude.ai/artifact/EW7fbQi3VZeBoTyPyG88Ke -> "GO"): every app with its real state on this server (read from
the engines it uses), where it opens and what it costs; many names, a batch, translate and a B-roll shot run on the page;
from a sheet goes through a template; an app that is not connected opens what it needs instead of a page that cannot work."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import hub as H
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app.main import app
    return TestClient(app)


def test_every_app_says_its_real_state(ix, monkeypatch):
    c = _client()
    r = c.get("/api/interactive/hub/apps").json()
    ids = [a["id"] for a in r["apps"]]
    assert ids == ["podcast", "cleanup", "ownvoice", "music", "broll", "translate", "dub", "lipsync", "batch", "names", "sheet", "aiface"]
    for a in r["apps"]:
        assert a["where"] in ("here", "vocal", "create") and a["cost"] in ("free", "free_draft", "free_drafts", "priced") and a["line"]
        assert isinstance(a["ready"], bool) and (a["ready"] or a["needs"])
    on = {a["id"]: a["ready"] for a in r["apps"]}
    assert on["batch"] and on["names"] and on["sheet"] and on["translate"]       # these need no outside engine
    from app.cinema import kie
    monkeypatch.setattr(kie, "configured", lambda: True)
    assert {a["id"]: a["ready"] for a in c.get("/api/interactive/hub/apps").json()["apps"]}["lipsync"] is True
    monkeypatch.setattr(kie, "configured", lambda: False)
    assert {a["id"]: a["ready"] for a in c.get("/api/interactive/hub/apps").json()["apps"]}["lipsync"] is False
    assert c.get("/api/interactive/hub/apps").json()["recent"] == []
    c.post("/api/interactive/hub/apps/used", json={"id": "names"})
    c.post("/api/interactive/hub/apps/used", json={"id": "dub"})
    assert [a["id"] for a in c.get("/api/interactive/hub/apps").json()["recent"]] == ["dub", "names"]
    assert c.post("/api/interactive/hub/apps/used", json={"id": "nope"}).status_code == 404


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("apps (v0.999.175"):js.index("// ------------------------------------------------------------------ pages ---")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert 'data-a="app"' not in js and "Each one is a real Hoola tool; nothing here is a placeholder" not in js
    for r in ("/apps/used", "/apps`", "/personalise", "/batch", "/translate", "/broll/quote?seconds=", "/estimate?engine="):
        assert r in js, r
    for c in (".hx-agrid", ".hx-ac", ".hx-ati", ".hx-ast", ".hx-afeat", ".hx-arl", ".hx-abg", ".hx-anck"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def _open(pg, base, vp):
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=apps]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")
    pg.click("#hxRoot .hx-side [data-p=apps]")
    pg.wait_for_selector("#hxRoot .hx-agrid", timeout=15000)


def test_apps_in_a_real_browser(ix_server, monkeypatch):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []

    def think(system, prompt):
        lines = [ln.split(". ", 1)[1] for ln in prompt.split("Lines:\n", 1)[1].splitlines() if ". " in ln]
        return {"lines": [f"[es] {x}" for x in lines]}
    monkeypatch.setattr(H, "_think", think)
    p = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt")
    S.save("default", p["id"], {"title": "Thank-you from Bloom", "scenes": [{"say": "{name}, thank you for trusting Bloom Florist.", "look": {"kind": "title", "text": "Thank you, {name}"}},
                                                                            {"say": "We are always here for you.", "look": {"kind": "none"}}]})
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        _open(pg, base, vp)
        assert pg.locator(".hx-ac").count() == 12 and pg.locator(".hx-afeat").count() == 2
        pg.click(".hx-tchips [data-val=many]")
        assert pg.locator(".hx-ac").count() == 4
        pg.click(".hx-tchips [data-val=all]")
        pg.fill("#hxAq", "zzz")
        assert "No apps match" in pg.inner_text("#hxAppList")
        pg.fill("#hxAq", "")
        n_ready = pg.locator(".hx-ast.ok").count()
        pg.check("#hxAready")
        assert pg.locator(".hx-ac").count() == n_ready < 12
        pg.uncheck("#hxAready")
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/ix175-apps-{vp['width']}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        # an app that is not connected says what it needs
        pg.click(".hx-ac:has-text('Lip sync a video') [data-a=aopen]")
        pg.wait_for_selector("#hxDlg .hx-dlg", timeout=5000)
        assert "lip-sync engine" in pg.inner_text("#hxDlg") and "Meanwhile" in pg.inner_text("#hxDlg")
        if shots and vp["width"] > 900:
            pg.wait_for_timeout(300)
            pg.screenshot(path=f"{shots}/ix175-need-1440.png")
        pg.keyboard.press("Escape")
        # many names, right here
        pg.click(".hx-ac:has-text('One video, many names') [data-a=aopen]")
        pg.wait_for_selector("#hxArNames", timeout=10000)
        assert pg.locator(".hx-tpr").count() == 1 and "Thank-you from Bloom" in pg.inner_text(".hx-tpr")
        pg.fill("#hxArNames", "Amara\nKenji\nAmara\nSofía")
        assert "3 names" in pg.inner_text("#hxArN") and "Kenji, thank you" in pg.inner_text("#hxArList")
        if shots:
            pg.wait_for_timeout(300)
            pg.screenshot(path=f"{shots}/ix175-names-{vp['width']}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        pg.click("[data-a=arnames]")
        pg.wait_for_selector("#hxRoot .hx-kpis", timeout=15000)
        titles = [x["title"] for x in S._load("default")["projects"]]
        assert "Thank-you from Bloom - Kenji" in titles and titles.count("Thank-you from Bloom - Amara") == (1 if vp["width"] > 900 else 2)   # duplicates left out
        ctx.close()
    # a batch, translate and a B-roll shot at computer width
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    _open(pg, base, {"width": 1440})
    assert pg.locator(".hx-arec .hx-arp").count() == 1                  # recently used: many names
    pg.click(".hx-ac:has-text('A batch of videos') [data-a=aopen]")
    pg.wait_for_selector("#hxArBatch", timeout=10000)
    pg.fill("#hxArBatch", "Our new hours are 9 am to 7 pm.\n\nThis week: 20% off every plant.")
    assert "2 scripts" in pg.inner_text("#hxArN")
    before = len(S._load("default")["projects"])
    pg.click("[data-a=arbatch]")
    pg.wait_for_selector("#hxRoot .hx-kpis", timeout=15000)
    assert len(S._load("default")["projects"]) == before + 2
    pg.click(".hx-side [data-p=apps]")
    pg.wait_for_selector("#hxRoot .hx-agrid", timeout=15000)
    pg.click(".hx-ac:has-text('Translate a video') [data-a=aopen]")
    pg.wait_for_selector(".hx-tpr", timeout=10000)
    pg.click(".hx-tpr:has-text('Thank-you from Bloom')")
    pg.click("[data-a=arpick][data-k=tlang]")
    pg.wait_for_selector(".hoola-menu, [role=menu]", timeout=5000)
    pg.keyboard.type("Spanish")
    pg.wait_for_timeout(300)
    pg.locator("[role=menuitem]:has-text('Spanish'), [role=menuitemradio]:has-text('Spanish')").first.click()
    _until(lambda: not pg.locator("[data-a=artrans]").is_disabled())
    pg.click("[data-a=artrans]")
    pg.wait_for_selector("#hxRoot .hx-edb", timeout=15000)
    assert S._load("default")["projects"][0]["lang"] == "es"
    pg.click(".hx-side [data-p=apps]")
    pg.wait_for_selector("#hxRoot .hx-agrid", timeout=15000)
    if "Not connected" in pg.inner_text(".hx-ac:has-text('A B-roll shot')"):
        pg.click(".hx-ac:has-text('A B-roll shot') [data-a=aopen]")
        pg.wait_for_selector("#hxDlg", timeout=5000)
        assert "B-roll engine" in pg.inner_text("#hxDlg")
        pg.keyboard.press("Escape")
    ctx.close()
    assert not errors, errors


def test_broll_runs_here_with_its_price(ix_server, monkeypatch):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    from app.interactive import engines as EN
    real = H._app_ready
    monkeypatch.setattr(H, "_app_ready", lambda: {**real(), "broll": True})
    monkeypatch.setattr(EN, "connected", lambda eid: True)
    with S._LOCK:
        d = S._load("default")
        d["broll"] = [{"id": "br_1", "prompt": "Coffee poured into a white cup, close up", "seconds": 6, "aspect": "16:9", "engine": "gemini_broll",
                       "status": "failed", "error": "The engine could not make it.", "made": "", "credits": 30, "created": S._now_iso()}]
        S._store("default", d)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    _open(pg, base, {"width": 1440})
    pg.click(".hx-ac:has-text('A B-roll shot') [data-a=aopen]")
    pg.wait_for_selector("#hxArBr", timeout=10000)
    pg.wait_for_selector("[data-a=abmake]:not([disabled])", timeout=10000)
    assert "credit" in pg.inner_text("[data-a=abmake]") and pg.locator(".hx-abs").count() == 1
    pg.click("[data-a=abs][data-val='8']")
    _until(lambda: "8-second" in pg.inner_text(".hx-tprice"))
    pg.click("[data-a=abidea] >> nth=1")
    assert "Rain on a shop window" in pg.input_value("#hxArBr")
    if shots:
        pg.screenshot(path=f"{shots}/ix175-broll-1440.png", full_page=True)
    ctx.close()
    assert not errors, errors
