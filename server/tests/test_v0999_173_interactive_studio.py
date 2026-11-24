"""v0.999.173 THE STUDIO, REDESIGNED (owner: "NOW LETS WORK ON INTERACTIVE SECTION STUDIO -- MAKE IT PERFECT ADVANCE,
PREMIUM AND ALSO WIRE IT PROPERLY"): the Studio library (counts, filters, search, sort, cards or rows, live progress, a
menu on every video, a first-visit page with three ways to start) and the editor (scene cards that move / copy / remove,
the stage with a playable sketch, a timeline sized by each scene's length, Scene / Face / Voice / Engine / Video tools,
every engine priced for this video, the itemised price and the Make button) - each control wired to a real route, and
the whole page walked in a real browser at computer and phone width."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def test_the_editor_saves_are_real(ix):
    """Every editor control maps to a field the server keeps: order, copies, looks, shape, frame, brand, products."""
    from app.main import app
    c = TestClient(app)
    p = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt")
    sc = p["scenes"]
    moved = [sc[1], sc[0], sc[2], json.loads(json.dumps(sc[2]))]
    moved[3]["look"] = {"kind": "bar_chart", "bars": [{"label": "Mon", "value": "12"}, {"label": "Tue", "value": "19"}]}
    r = c.put(f"/api/interactive/studio/project?id={p['id']}", json={"scenes": moved, "aspect": "1:1", "brand": "Café Azul"}).json()
    assert [s["say"] for s in r["scenes"]][:2] == [sc[1]["say"], sc[0]["say"]] and len(r["scenes"]) == 4
    assert r["scenes"][3]["look"]["kind"] == "bar_chart" and r["aspect"] == "1:1" and r["brand"] == "Café Azul"
    r = c.put(f"/api/interactive/studio/project?id={p['id']}", json={"shape": "product", "items": [{"name": "Pastel de nata", "price": "€1.20"}, {"name": ""}]}).json()
    assert r["shape"] == "product" and r["items"] == [{"name": "Pastel de nata", "price": "€1.20", "note": ""}]
    q = c.get(f"/api/interactive/x/quote?id={p['id']}").json()
    assert q["quote"]["key"] and q["quote"]["credits"] >= 0 and isinstance(q["problems"], list)
    cmp = c.get(f"/api/interactive/x/compare?id={p['id']}").json()
    assert cmp["chosen"] == r["engine"] and cmp["engines"]
    r = c.put(f"/api/interactive/studio/project?id={p['id']}", json={"shape": "reel"}).json()
    assert r["aspect"] == "9:16"
    r = c.put(f"/api/interactive/studio/project?id={p['id']}", json={"aspect": "1:1"}).json()
    assert r["aspect"] == "9:16"                                       # a reel stays vertical
    assert c.post("/api/interactive/hub/duplicate", json={"id": p["id"]}).json()["id"] != p["id"]
    assert c.post("/api/interactive/hub/trash", json={"id": p["id"]}).json()["ok"] is True
    ov = c.get("/api/interactive/hub/overview").json()
    assert p["id"] in [x["id"] for x in ov["trash"]] and p["id"] not in [x["id"] for x in ov["projects"]]


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    for a in ("'vmenu'", "'lf'", "'lview'", "'lsort'", "'lclear'", "'ltrash'", "'lfrom'", "'scmove'", "'scdup'", "'delsc'",
              "'scprev'", "'scnext'", "'edplay'", "'edview'", "'lookset'", "'baradd'", "'bardel'", "'faceset'", "'engset'",
              "'paspect'", "'itadd'", "'itdel'", "'edhear'", "'tool'", "'scene'"):
        assert f"case {a}:" in js, a
    # every button the Studio draws has its case
    import re
    drawn = set(re.findall(r'data-a="([a-z]+)"', js[js.index("the Studio (v0.999.173"):js.index("// ------------------------------------------------------------------ pages ---")]))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "function tool(p, sc)" not in js and "UI.tool === 'Look'" not in js
    assert "/compare?id=" in js and "/quote?id=" in js and "/project?id=" in js
    for c in (".hx-kpis", ".hx-lgrid", ".hx-lr", ".hx-lempty", ".hx-ed", ".hx-edb", ".hx-scc", ".hx-tl", ".hx-looks", ".hx-faces", ".hx-engs", ".hx-edmk"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def _walk_library_and_editor(pg, base, vp, shots):
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=studio]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")                                # the sidebar is a drawer on a phone
    pg.click("#hxRoot .hx-side [data-p=studio]")
    pg.wait_for_selector("#hxRoot .hx-kpis", timeout=15000)
    assert pg.locator(".hx-lc").count() == 3
    assert "Videos" in pg.inner_text(".hx-kpis") and "3" in pg.inner_text(".hx-kpi >> nth=0")
    pg.click(".hx-lf [data-val=ready]")
    assert pg.locator(".hx-lc").count() == 1
    pg.click(".hx-lf [data-val=all]")
    pg.fill("#hxLq", "plants")
    assert pg.locator(".hx-lc").count() == 1 and "Spanish" in pg.inner_text("#hxLibList")
    pg.fill("#hxLq", "zzz-none")
    assert "No videos match" in pg.inner_text("#hxLibList")
    pg.click("[data-a=lclear]")
    pg.click(".hx-lv [data-val=list]")
    assert pg.locator(".hx-lr").count() == 3
    if shots:
        pg.screenshot(path=f"{shots}/ix173-list-{vp['width']}.png", full_page=True)
    pg.click(".hx-lv [data-val=grid]")
    pg.click(".hx-lc >> nth=0 >> [data-a=vmenu]")
    pg.wait_for_selector("text=Save as a template", timeout=8000)
    pg.keyboard.press("Escape")
    if shots:
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{shots}/ix173-library-{vp['width']}.png", full_page=True)
    assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
    # the editor
    pg.click(".hx-lc:has-text('Portuguese') .hx-lco")
    pg.wait_for_selector("#hxRoot .hx-edb", timeout=15000)
    assert pg.locator(".hx-scc").count() == 3 and pg.locator(".hx-tlb[data-n]").count() == 3
    pg.wait_for_selector(".hx-edmk .hx-pbox", timeout=10000)
    assert "Total" in pg.inner_text(".hx-edmk")
    pg.click(".hx-tlb[data-n='2']")
    assert "pastel de nata" in pg.inner_text("#hxEdStage") and pg.get_attribute(".hx-scc[data-n='2']", "class").endswith("on")
    pg.click(".hx-scc[data-n='2'] [data-a=scmove][data-d='-1']")
    _until(lambda: "pastel" in pg.input_value(".hx-scc[data-n='1'] textarea"))
    pg.click(".hx-scc[data-n='1'] [data-a=scdup]")
    _until(lambda: pg.locator(".hx-scc").count() == 4)
    pg.once("dialog", lambda d: d.accept())
    pg.click(".hx-scc[data-n='2'] [data-a=delsc]")
    _until(lambda: pg.locator(".hx-scc").count() == 3)
    pg.click(".hx-edtabs [data-val=Scene]")
    pg.click(".hx-lkt[data-val=big_number]")
    pg.wait_for_selector("[data-lk=value]", timeout=8000)
    pg.fill("[data-lk=value]", "1,200")
    assert "1,200" in pg.inner_text("#hxEdStage")
    for t in ("Face", "Voice", "Video"):
        pg.click(f".hx-edtabs [data-val={t}]")
        assert pg.inner_text("#hxEdTool").strip()
    pg.click(".hx-edtabs [data-val=Engine]")
    pg.wait_for_selector(".hx-eng", timeout=10000)
    assert "credit" in pg.inner_text(".hx-engs")
    if shots:
        pg.screenshot(path=f"{shots}/ix173-editor-{vp['width']}.png", full_page=True)
    assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
    pg.click(".hx-edh [data-a=go][data-p=studio]")
    pg.wait_for_selector("#hxRoot .hx-kpis", timeout=15000)


def test_the_studio_in_a_real_browser(ix_server, tmp_path):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    # the first visit: nothing made yet
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=studio]", timeout=25000)
    pg.click("#hxRoot .hx-side [data-p=studio]")
    pg.wait_for_selector("#hxRoot .hx-lempty", timeout=15000)
    assert pg.locator(".hx-lst").count() == 3 and pg.locator(".hx-how li").count() == 3
    if shots:
        pg.wait_for_timeout(700)
        pg.screenshot(path=f"{shots}/ix173-empty-1440.png", full_page=True)
    ctx.close()
    # three videos: a plan, a plan waiting for numbers, a finished one
    a = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt", kind="presenter")
    b = S.draft("default", "Spring sale: 20% off all plants until 30 April", lang="es", shape="reel")
    c = S.draft("default", "A short lesson on photosynthesis", lang="de", kind="lesson")
    with S._LOCK:
        d = S._load("default")
        for p in d["projects"]:
            if p["id"] == c["id"]:
                p["status"], p["video"] = "ready", {"duration": 24.0, "made": "2026-11-24T10:00:00Z", "credits": 0}
        S._store("default", d)
    S.video_path("default", c["id"]).parent.mkdir(parents=True, exist_ok=True)
    S.video_path("default", c["id"]).write_bytes(b"\x00")
    assert a["id"] and b["id"]
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        S.save("default", a["id"], {"scenes": a["scenes"]})            # each width starts from the same plan
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        _walk_library_and_editor(pg, base, vp, shots)
        ctx.close()
    assert not errors, errors
