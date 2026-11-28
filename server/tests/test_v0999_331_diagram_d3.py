"""HOOLA DIAGRAM D3 (docs/DIAGRAM_TOOL_PLAN.md): the editable engine - draw.io in her workspace. Her hand edits are
saved as versions, Hoola reads before it changes (a change on an older copy is refused), Hoola's change reaches her
open editor id by id as ONE undoable step and outlined, her selection reaches Hoola, .drawio download, and the editor
runs in its own sandbox. Ends with a real-browser walk: she moves a box, Hoola changes another, her move stays, Ctrl+Z
takes Hoola's change back."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from app.diagram import drawio as DR
from app.diagram import drawio_xml as X
from app.diagram import live as L
from app.diagram import runners as R
from app.diagram import service as S

CELLS = ('<mxCell id="a" value="Browser" style="rounded=1;" vertex="1" parent="1"><mxGeometry x="40" y="40" width="120" '
         'height="50" as="geometry"/></mxCell><mxCell id="b" value="API" style="rounded=1;" vertex="1" parent="1">'
         '<mxGeometry x="260" y="40" width="120" height="50" as="geometry"/></mxCell><mxCell id="e" edge="1" '
         'source="a" target="b" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>')
SCRATCH_EDITOR = os.environ.get("DIAGRAM_DRAWIO_DIR", "")


# ------------------------------------------------------------------ the XML engine-C works with
def test_xml_is_normalised_and_checked():
    xml, probs = X.normalize(CELLS, "Flow")
    assert not probs and xml.startswith("<mxfile") and '<mxCell id="0"' in xml and '<mxCell id="1" parent="0"' in xml
    assert X.normalize("<mxCell id=\"x\" value=\"&lt;script&gt;\" vertex=\"1\" parent=\"1\"/>")[1]   # a script label
    assert X.normalize('<mxCell id="a" vertex="1" parent="1"/><mxCell id="a" vertex="1" parent="1"/>')[1]  # twice
    assert "is not a cell" in X.normalize('<mxCell id="e" edge="1" source="ghost" parent="1"/>')[1][0]
    assert "DOCTYPE" in X.normalize('<!DOCTYPE x [<!ENTITY e "x">]><root/>')[1][0]
    assert "parse" in X.normalize("<mxCell id='a'")[1][0]
    assert "one page" in X.normalize('<mxfile><diagram/><diagram/></mxfile>')[1][0]


def test_a_compressed_page_from_the_editor_is_read_and_a_bomb_is_not():
    import base64
    import urllib.parse
    import zlib
    model = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + CELLS + "</root></mxGraphModel>"
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = base64.b64encode(c.compress(urllib.parse.quote(model).encode()) + c.flush()).decode()
    xml, probs = X.normalize(f'<mxfile><diagram id="p" name="P">{packed}</diagram></mxfile>')
    assert not probs and {r["id"] for r in X.listing(xml)} == {"a", "b", "e"} and "<mxGraphModel" in xml
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    bomb = base64.b64encode(c.compress(b"A" * (X.MAX_XML + 10)) + c.flush()).decode()
    assert len(bomb) < 20000 and "could not be read" in X.normalize(f"<mxfile><diagram>{bomb}</diagram></mxfile>")[1][0]


def test_ops_change_cell_by_cell_all_or_nothing():
    xml, _ = X.normalize(CELLS)
    new, ids, probs = X.apply_ops(xml, [{"op": "update", "id": "b", "value": "API server", "x": 300},
                                        {"op": "add", "id": "c", "value": "Cache", "x": 500, "y": 40},
                                        {"op": "add", "id": "e2", "edge": True, "source": "b", "target": "c"}])
    assert not probs and ids == ["b", "c", "e2"]
    rows = {r["id"]: r for r in X.listing(new)}
    assert rows["b"]["label"] == "API server" and rows["b"]["box"][0] == "300" and rows["a"]["box"][0] == "40"
    gone, ids, _ = X.apply_ops(new, [{"op": "delete", "id": "b"}])
    assert {r["id"] for r in X.listing(gone)} == {"a", "c"}                 # b and both of its edges went
    same, ids, probs = X.apply_ops(xml, [{"op": "update", "id": "b", "value": "ok"}, {"op": "update", "id": "zz"}])
    assert probs and same == "" and ids == []                               # one bad op = nothing changes
    assert X.apply_ops(xml, [{"op": "add", "id": "a"}])[2]                  # an id that exists is not added again


def test_fingerprint_ignores_reserialising_but_not_edits():
    xml, _ = X.normalize(CELLS)
    shuffled = xml.replace('style="rounded=1;" vertex="1"', 'vertex="1" style="rounded=1;"').replace("><", ">\n<")
    assert X.fingerprint(xml) == X.fingerprint(shuffled)
    moved, _, _ = X.apply_ops(xml, [{"op": "update", "id": "a", "x": 41}])
    assert X.fingerprint(moved) != X.fingerprint(xml)


# ------------------------------------------------------------------ routing, guide, the link
def test_editable_words_route_to_drawio_and_the_guide_is_next_ai_draw_ios():
    assert S.route("drawio")[:2] == ("drawio", "drawio") and S.route("editable")[:2] == ("drawio", "drawio")
    assert S.route("architecture", engine="drawio")[:2] == ("drawio", "drawio")
    assert any(c["engine"] == "drawio" for c in S.catalogue())
    g = S.guide("drawio")
    assert g["ok"] and "next-ai-draw-io's drawing guide" in g["guide"] and "action=read first" in g["guide"] and "SELECTED" in g["guide"]


def test_editor_link_is_signed_for_one_diagram_and_expires(env):
    tok = L.sign("t1", "dg-abc")
    assert L.verify(tok) == ("t1", "dg-abc")
    body, mac = tok.split(".")
    assert L.verify(body + "." + ("0" * len(mac))) is None                  # tampered
    assert L.verify(L.sign("t1", "dg-abc", hours=-1)) is None               # expired
    assert L.link("t1", "dg-abc").startswith("/diagram-edit/")


# ------------------------------------------------------------------ her edits, Hoola's changes, the gate
@pytest.fixture()
def fake_editor(env, monkeypatch, tmp_path):
    """The engine's drawing without a browser: the export writes a small SVG / PNG (the real editor walk is below)."""
    monkeypatch.setattr(DR, "ready", lambda: True)

    def export(xml, out, fmt="png"):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        if fmt == "png":
            Path(out).write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
        else:
            Path(out).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" content="x"><text>{len(xml)}</text></svg>')
        return {"ok": True, "file": str(out), "png": str(out)}
    monkeypatch.setattr(R, "drawio_export", export)
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda *a, **k: None)


def test_her_edit_hoola_reads_then_changes_and_the_open_editor_gets_it(fake_editor):
    from app import artifacts
    d = S.draw("t1", "c1", "drawio", "Shop flow", CELLS)
    assert d["ok"] and d["engine"] == "drawio" and d["editor"].startswith("/diagram-edit/") and Path(d["_look"]).is_file()
    did, aid = d["diagram_id"], d["artifact_id"]
    assert artifacts.current_source(aid)[1] == "diagram" and S.by_artifact("t1", aid)["id"] == did
    st = L.state("t1", did)
    assert st["ok"] and st["rev"] == 1 and "Browser" in st["xml"]
    # she moves box a in her editor and selects b
    moved, _, _ = X.apply_ops(st["xml"], [{"op": "update", "id": "a", "x": 140, "y": 120}])
    r = L.save("t1", did, moved, '<svg xmlns="http://www.w3.org/2000/svg"/>', applied_rev=1)
    assert r["ok"] and r["changed"] and r["rev"] == 2
    assert L.save("t1", did, moved.replace("><", ">\n<"), "", applied_rev=2) == {"ok": True, "rev": 2, "changed": False}
    L.select("t1", did, ["b"])
    # Hoola has not read since her edit: refused
    no = S.change("t1", "c1", did, [{"op": "update", "id": "b", "value": "API server"}])
    assert no["ok"] is False and "read" in no["said"]
    rd = S.read("t1", did)
    assert [c["id"] for c in rd["selected"]] == ["b"] and "SELECTED" in rd["said"]
    ch = S.change("t1", "c1", did, [{"op": "update", "id": "b", "value": "API server"}])
    assert ch["ok"] and ch["changed"] == ["b"] and Path(ch["_look"]).is_file(), ch
    xml_now = L.state("t1", did)["xml"]
    rows = {c["id"]: c for c in X.listing(xml_now)}
    assert rows["b"]["label"] == "API server" and rows["a"]["box"][:2] == ["140", "120"]     # her move kept
    # her open editor (still at rev 2) gets the change once, id by id
    p = L.poll("t1", did, 2)
    assert p["rev"] == 3 and len(p["changes"]) == 1 and p["changes"][0]["ops"][0]["id"] == "b"
    assert L.poll("t1", did, 3)["changes"] == []
    # a save from an editor that has not applied it yet is refused, then accepted once it has
    assert L.save("t1", did, moved, "", applied_rev=2)["stale"] is True
    assert L.save("t1", did, xml_now, "", applied_rev=3)["ok"]


def test_editable_copy_of_an_archify_or_design_diagram(fake_editor, monkeypatch):
    # an archify diagram already saved (its engine's own run is covered in D2) - here only the hand-over
    m = {"id": "dg-orig", "engine": "archify", "type": "architecture", "title": "App", "artifact_id": "art-x"}
    S._save_meta("t1", m)
    S._save_desc("t1", m, '{"meta": {"title": "App"}}')
    e = S.editable("t1", "dg-orig")
    assert e["ok"] and "from_id=dg-orig" in e["said"] and "App" in e["description"]
    d = S.draw("t1", "c1", "drawio", "", CELLS, from_id="dg-orig")
    assert d["ok"] and d["title"] == "App"
    assert S._meta("t1", "dg-orig")["editable_id"] == d["diagram_id"]
    again = S.editable("t1", "dg-orig")
    assert again["diagram_id"] == d["diagram_id"] and again["editor"].startswith("/diagram-edit/")


def test_a_full_redraw_also_waits_for_a_read_after_her_edit(fake_editor):
    d = S.draw("t1", "c1", "drawio", "Flow", CELLS)
    st = L.state("t1", d["diagram_id"])
    moved, _, _ = X.apply_ops(st["xml"], [{"op": "update", "id": "a", "x": 99}])
    L.save("t1", d["diagram_id"], moved, "", applied_rev=st["rev"])
    r = S.draw("t1", "c1", "", "", CELLS, diagram_id=d["diagram_id"])
    assert r["ok"] is False and "read" in r["said"]


# ------------------------------------------------------------------ the routes
@pytest.fixture()
def client(fake_editor, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    ed = tmp_path / "editor"
    (ed / "js").mkdir(parents=True)
    (ed / "index.html").write_text("<html><head><title>draw.io</title></head><body></body></html>")
    (ed / "js" / "app.min.js").write_text("/*app*/")
    monkeypatch.setattr(DR, "editor_dir", lambda: ed)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        yield c, {"Authorization": f"Bearer {KEY}"}


def test_routes_are_sandboxed_token_only_and_never_see_her_sign_in(client):
    c, h = client
    d = S.draw("default", "c1", "drawio", "Shop flow", CELLS)
    tok = d["editor"].rsplit("/", 1)[1]
    page = c.get(f"/diagram-edit/{tok}?lang=ar")
    csp = page.headers["content-security-policy"]
    assert page.status_code == 200 and "sandbox allow-scripts" in csp and "allow-same-origin" not in csp
    assert 'dir="rtl"' in page.text and "/diagram-edit/hoola/host.js" in page.text and "Shop flow" in page.text
    assert c.get("/diagram-edit/not.atoken").status_code == 403
    idx = c.get("/diagram-edit/e/index.html")
    assert '<head><script src="/diagram-edit/hoola/bridge.js"></script>' in idx.text      # injected at serve time
    assert idx.headers["access-control-allow-origin"] == "*" and "sandbox" in idx.headers["content-security-policy"]
    assert c.get("/diagram-edit/e/js/app.min.js").status_code == 200
    assert c.get("/diagram-edit/e/../../etc/passwd").status_code == 404
    assert c.get("/diagram-edit/e/__hoola_host.html").status_code == 404
    assert c.get("/diagram-edit/hoola/evil.js").status_code == 404
    s = c.get(f"/api/diagram/live/{tok}/state").json()
    assert s["ok"] and s["rev"] == 1
    moved, _, _ = X.apply_ops(s["xml"], [{"op": "update", "id": "a", "x": 77}])
    assert c.post(f"/api/diagram/live/{tok}/save", json={"xml": moved, "applied_rev": 1}).json()["rev"] == 2
    assert c.post(f"/api/diagram/live/{tok}/select", json={"ids": ["a"]}).json()["ok"]
    assert c.get(f"/api/diagram/live/{tok}/poll?rev=2").json()["changes"] == []
    f = c.get(f"/api/diagram/live/{tok}/file")
    assert f.headers["content-disposition"].endswith('.drawio"') and 'x="77"' in f.text
    assert c.get(f"/api/diagram/open/{d['artifact_id']}").status_code == 401              # signed-in only
    o = c.get(f"/api/diagram/open/{d['artifact_id']}", headers=h).json()
    assert o["editable"] and o["url"].startswith("/diagram-edit/")


def test_console_panel_has_edit_by_hand_and_never_reloads_her_editor():
    js = (Path(__file__).resolve().parents[1] / "app/static/console/panel.js").read_text()
    assert 'data-a="hand"' in js and "async function handView" in js and "/api/diagram/open/" in js
    assert "t.view === 'hand'" in js                                              # a new version does not reload it
    assert "'allow-scripts allow-popups allow-modals allow-downloads'" in js       # no allow-same-origin
    assert "Change the diagram" in js                                             # changes go to the diagram tool
    web = Path(S.__file__).with_name("web")
    assert "hoola:apply" in (web / "bridge.js").read_text() and "m.endUpdate()" in (web / "bridge.js").read_text()
    assert "credentials: 'omit'" in (web / "host.js").read_text()


# ------------------------------------------------------------------ the real-browser walk
@pytest.mark.skipif(not (SCRATCH_EDITOR or DR.ready()) or not R.chrome_path(),
                    reason="needs the draw.io editor (python -m app.diagram setup) and Chrome")
def test_walk_her_move_stays_hoolas_change_is_outlined_and_ctrl_z_takes_it_back(env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    if SCRATCH_EDITOR:
        monkeypatch.setenv("DIAGRAM_DRAWIO_DIR", SCRATCH_EDITOR)
    from app.config import get_settings
    get_settings.cache_clear()
    assert DR.ready()
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda *a, **k: None)
    import uvicorn

    from app import main
    from tests.test_v161_console_e2e import _free_port
    d = S.draw("default", "c1", "drawio", "Shop flow", CELLS)
    assert d["ok"], d
    did = d["diagram_id"]
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(600):
        if srv.started:
            break
        time.sleep(0.05)
    pw = sync_api.sync_playwright().start()
    try:
        b = pw.chromium.launch(executable_path=R.chrome_path(), args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 1300, "height": 860})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.goto(f"http://127.0.0.1:{port}{d['editor']}?lang=en")
        page.wait_for_function("document.getElementById('st').dataset.state === 'ready'", timeout=60000)
        ed = next(f for f in page.frames if "/diagram-edit/e/index.html" in f.url)
        ed.wait_for_function("!!window.EditorUi", timeout=30000)
        # she drags box a (the editor's own move, as her mouse does) and selects b
        ui = "(window.__hoolaUiForTest || (()=>{ throw new Error('no ui') })())"
        ed.evaluate("""() => { const p = EditorUi.prototype; const o = p.updateActionStates;
                              p.updateActionStates = function(){ window.__hoolaUiForTest = this; return o.apply(this, arguments); }; }""")
        ed.locator(".geDiagramContainer").first.click(position={"x": 600, "y": 500})
        page.keyboard.press("Control+a")                      # any selection change makes draw.io call the hook
        page.keyboard.press("Escape")
        ed.wait_for_function("!!window.__hoolaUiForTest", timeout=15000)
        ed.evaluate(f"() => {{ const g = {ui}.editor.graph; g.moveCells([g.model.getCell('a')], 100, 80); }}")
        page.wait_for_function("document.getElementById('st').dataset.state === 'saved'", timeout=30000)
        rows = {c["id"]: c for c in X.listing(L.state("default", did)["xml"])}
        assert rows["a"]["box"][:2] == ["140", "120"], rows["a"]                       # her move reached the server
        ed.evaluate(f"() => {{ const g = {ui}.editor.graph; g.setSelectionCells([g.model.getCell('b')]); }}")
        for _ in range(60):
            if (S._meta("default", did) or {}).get("selection") == ["b"]:
                break
            time.sleep(0.25)
        rd = S.read("default", did)
        assert [c["id"] for c in rd["selected"]] == ["b"]                              # Hoola sees her selection
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(1) as pool:                        # as the tool runs it: off the caller's thread
            ch = pool.submit(S.change, "default", "c1", did, [{"op": "update", "id": "b", "value": "API server"}]).result()
        assert ch["ok"], ch
        ed.wait_for_function(f"{ui}.editor.graph.model.getCell('b').value === 'API server'", timeout=20000)
        assert ed.evaluate(f"{ui}.editor.graph.model.getCell('a').geometry.x") == 140   # her move untouched
        assert page.evaluate("document.getElementById('st').textContent").startswith("Hoola changed")
        # one Ctrl+Z takes Hoola's whole change back, her move stays
        ed.evaluate(f"() => {ui}.actions.get('undo').funct()")
        assert ed.evaluate(f"{ui}.editor.graph.model.getCell('b').value") == "API"
        assert ed.evaluate(f"{ui}.editor.graph.model.getCell('a').geometry.x") == 140
        for _ in range(80):                                                            # and the server follows
            rows = {c["id"]: c for c in X.listing(L.state("default", did)["xml"])}
            if rows["b"]["label"] == "API":
                break
            time.sleep(0.25)
        assert rows["b"]["label"] == "API" and rows["a"]["box"][:2] == ["140", "120"]
        assert not errors, errors
        b.close()
    finally:
        pw.stop()
        srv.should_exit = True
        th.join(timeout=10)


@pytest.mark.skipif(not (SCRATCH_EDITOR or DR.ready()) or not R.chrome_path(),
                    reason="needs the draw.io editor (python -m app.diagram setup) and Chrome")
def test_console_workspace_edit_by_hand_opens_her_editor(env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    if SCRATCH_EDITOR:
        monkeypatch.setenv("DIAGRAM_DRAWIO_DIR", SCRATCH_EDITOR)
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda *a, **k: None)
    import uvicorn

    from app import main
    from tests.test_v161_console_e2e import _free_port
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(1) as pool:
        d = pool.submit(S.draw, "default", "c1", "drawio", "Shop flow", CELLS).result()
    assert d["ok"], d
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    pw = sync_api.sync_playwright().start()
    try:
        b = pw.chromium.launch(executable_path=R.chrome_path(), args=["--no-sandbox"])
        ctx = b.new_context(viewport={"width": 1400, "height": 900})
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{KEY}'); }} catch (e) {{}}" """
          (function(){ let f; Object.defineProperty(window, 'HoolaPanel', {configurable: true,
            get(){ return f; }, set(v){ f = c => (window.__PN = v(c)); } }); })();""")
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.goto(f"http://127.0.0.1:{port}/console/")
        page.wait_for_selector("#app:not([hidden])", timeout=30000)
        page.wait_for_function("!!window.__PN", timeout=15000)
        page.evaluate(f"() => window.__PN.open({{type: 'page', ref: '{d['artifact_id']}', title: 'Shop flow'}})")
        hand = page.locator('[data-a="hand"]').first
        hand.wait_for(state="visible", timeout=20000)
        hand.click()
        frame = page.locator("iframe.pnhand")
        frame.wait_for(timeout=15000)
        assert "allow-same-origin" not in (frame.get_attribute("sandbox") or "")
        assert (frame.bounding_box() or {}).get("height", 0) >= 500                  # the editor gets the whole pane
        host = next(f for f in page.frames if "/diagram-edit/" in f.url and "/e/" not in f.url)
        host.wait_for_function("document.getElementById('st').dataset.state === 'ready'", timeout=60000)
        assert not errors, errors
        b.close()
    finally:
        pw.stop()
        srv.should_exit = True
        th.join(timeout=10)
