"""v0.357 ENGINEERING DESK Phase 1: hire the CAD Engineer -> words -> CadQuery in a locked box -> checks -> STEP / STL /
views / drawing PDF, fixes from the real error, changes as new versions, signed files, guard, limits."""
import json
import time

import pytest

GOOD = """TITLE: Wall bracket
SIZE: 80 x 40 x 30
ASSUMED: 2 holes 8 mm
NOTES: L bracket
```python
import cadquery as cq
w, d, t = 80, 40, 10
base = cq.Workplane('XY').box(w, d, t).faces('>Z').workplane().pushPoints([(-28, 0), (28, 0)]).hole(8)
wall = cq.Workplane('XY').box(w, 8, 30).translate((0, 16, 10))
result = base.union(wall)
```"""
BROKEN = GOOD.replace("result = base.union(wall)", "result = base.union(wall).edges().fillet(50)")
CHANGED = GOOD.replace("hole(8)", "hole(10)").replace("TITLE: Wall bracket", "TITLE: Wall bracket v2")


@pytest.fixture
def eng(env, monkeypatch, tmp_path):
    pytest.importorskip("cadquery")
    monkeypatch.setenv("ENG_WORKER", "false")
    monkeypatch.setenv("ENG_DIR", str(tmp_path / "eng"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("ENG_LOOK_ROUNDS", "0")          # v0.362: the vision review has its own tests below
    from app.engineering import ai, service
    replies, seen = [], []

    def fake_ask(system, prompt, images=None, max_tokens=8000, think=False):
        seen.append({"system": system, "prompt": prompt, "images": len(images or []), "think": think})
        return replies.pop(0)
    monkeypatch.setattr(ai, "ask", fake_ask)
    from app.employee import hire
    yield {"svc": service, "replies": replies, "hire": hire, "seen": seen}
    get_settings.cache_clear()


def test_needs_the_hire_first(eng):
    with pytest.raises(eng["svc"].EngError, match="not hired"):
        eng["svc"].start("default", "", "L bracket 80 x 40 mm")


def test_words_to_step_stl_views_and_drawing(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket 80 x 40 x 30 mm, two 8 mm holes")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "done" and d["title"] == "Wall bracket"
    v = d["latest"]
    assert v["bbox"]["x"] == 80 and v["bbox"]["y"] == 40 and v["bbox"]["z"] == 30
    assert all(c["ok"] for c in v["checks"]) and {c["name"] for c in v["checks"]} >= {"Valid solid", "One body", "Size as asked"}
    assert set(v["files"]) >= {"part.step", "part.stl", "drawing.pdf", "iso.png", "front.png", "top.png", "right.png", "part.py"}
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get(v["files"]["part.step"])
    assert r.status_code == 200 and b"ISO-10303-21" in r.content[:200]
    assert c.get(v["files"]["drawing.pdf"]).content[:4] == b"%PDF"
    assert c.get(v["files"]["iso.png"]).content[:4] == b"\x89PNG"
    assert c.get(v["files"]["part.step"].replace("sig=", "sig=x")).status_code == 404     # tampered link


def test_kernel_error_goes_back_to_the_model_and_gets_fixed(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"] += [BROKEN, GOOD]
    p = eng["svc"].start("default", "", "L bracket")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "done" and len(d["versions"]) == 1 and not eng["replies"]


def test_unsafe_script_never_runs(eng):
    eng["hire"].hire("default", "cad")
    bad = "TITLE: x\nSIZE: 1 x 1 x 1\n```python\nimport os\nos.system('id')\nresult = 1\n```"
    eng["replies"] += [bad, bad, bad, bad]
    p = eng["svc"].start("default", "", "anything")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "failed" and "import os" in d["error"]


def test_change_makes_a_new_version_keeping_the_old(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket")
    eng["svc"].run_job(p["id"])
    eng["replies"].append(CHANGED)
    eng["svc"].change("default", p["id"], "holes 10 mm karo")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert [v["n"] for v in d["versions"]] == [1, 2] and d["latest"]["words"] == "holes 10 mm karo"
    assert d["versions"][0]["volume_mm3"] > d["versions"][1]["volume_mm3"]       # bigger holes, less material


def test_size_mismatch_is_flagged(eng):
    eng["hire"].hire("default", "cad")
    wrong = GOOD.replace("SIZE: 80 x 40 x 30", "SIZE: 100 x 40 x 30")
    eng["replies"] += [wrong, wrong, wrong, wrong]
    p = eng["svc"].start("default", "", "bracket 100 mm long")
    eng["svc"].run_job(p["id"])
    v = eng["svc"].get("default", p["id"])["latest"]
    size = [c for c in v["checks"] if c["name"] == "Size as asked"][0]
    assert size["ok"] is False and "expected" in size["note"]


def test_other_tenant_cannot_see_or_change_her_part(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket")
    with pytest.raises(eng["svc"].EngError, match="was not found"):
        eng["svc"].get("other", p["id"])
    assert eng["svc"].projects("other") == []


def test_daily_cap(eng, monkeypatch):
    monkeypatch.setenv("ENG_DAILY_PARTS", "1")
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket")
    eng["svc"].run_job(p["id"])
    with pytest.raises(eng["svc"].EngError, match="Aaj ke 1"):
        eng["svc"].start("default", "", "another part")


def test_guard_rules():
    from app.engineering import guard
    assert guard.problems("import cadquery as cq\nresult = cq.Workplane('XY').box(1, 2, 3)\n") == []
    p = guard.problems("import subprocess\nresult = cq.exporters.export(1, '/etc/x')\n")
    assert any("subprocess" in x for x in p) and any("export" in x for x in p)
    assert guard.problems("import cadquery as cq\nx = 1\n") == ["set `result = ...` (cadquery Workplane / Shape) at the end of the script"]
    assert any("__class__" in x for x in guard.problems("result = ().__class__\n"))


def test_catalog_has_the_engineering_group():
    from app.employee import hire
    eng_keys = [k for k, c in hire.CATALOG.items() if c.get("group") == "Research, CAD, Hardware & Industrial Tech"]
    assert len(eng_keys) == 10 and hire.CATALOG["cad"]["live"] is True
    assert sum(1 for k in eng_keys if hire.CATALOG[k].get("live")) == 1


def test_v0361_lockdown_holds_without_a_network_namespace(env, monkeypatch, tmp_path):
    """v0.361 her VPS (Ubuntu 24.04) refuses `unshare -rn`: the fourth wall must stop a program / socket by itself."""
    pytest.importorskip("cadquery")
    monkeypatch.setenv("ENG_NO_NET", "false")
    from app.engineering import sandbox
    sandbox._NET_OK = None
    marker = tmp_path / "pwned"
    code = (f"import cadquery as cq\nx = cq.exporters.os.system('touch {marker}')\n"     # bypasses guard on purpose
            "result = cq.Workplane('XY').box(1, 1, 1)\n")
    r = sandbox.run(tmp_path / "a", code)
    assert r["ok"] is False and "band" in r["errors"][0] and not marker.exists()
    code2 = "import cadquery as cq\nimport math\nresult = cq.Workplane('XY').box(10, 10, 10)\n"
    r2 = sandbox.run(tmp_path / "b", code2)
    assert r2["ok"] and (tmp_path / "b" / "part.step").exists()                         # the runner's own export still works
    sandbox._NET_OK = None



# ---------------------------------------------------------------- v0.362 HOOLA CAD PRO
ASM = """TITLE: Gear unit
SIZE: 120 x 64 x 36
MATERIAL: aluminium
PLAN: base plate + gear + bearing + screw
ASSUMED: none
NOTES: small gear unit
```python
import cadquery as cq
plate = cq.Workplane('XY').box(120, 60, 10).faces('>Z').workplane().rarray(90, 30, 2, 2).hole(H.hole(6))
gear = H.spur_gear(2, 30, 12, bore=20)
result = (cq.Assembly(name='gear_unit')
          .add(plate, name='base_plate', color=cq.Color(0.6, 0.6, 0.65))
          .add(gear, name='spur_gear', loc=cq.Location((0, 0, 5)), color=cq.Color(0.85, 0.65, 0.2))
          .add(H.bearing('6204'), name='bearing_6204', loc=cq.Location((0, 0, 17))))
```"""


def test_v0362_parts_library_is_real_and_valid():
    pytest.importorskip("cadquery")
    from app.engineering.parts import H
    g = H.spur_gear(2, 24, 10, bore=8).val()
    assert g.isValid() and abs(g.BoundingBox().xlen - 52) < 0.1            # tip dia = m (z + 2)
    assert H.hole(6) == 6.6 and H.hole(6, "tap") == 5.0 and H.hole(8, "cbore") == 15.0
    assert H.bearing("6204").val().BoundingBox().xlen == pytest.approx(47, abs=0.01)
    assert H.shaft(20, 80, keyway=True).val().isValid()
    with pytest.raises(ValueError, match="table"):
        H.hole(7)


def test_v0362_assembly_bom_mass_and_every_file(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(ASM)
    p = eng["svc"].start("default", "", "gear unit assembly: base plate, gear, bearing")
    eng["svc"].run_job(p["id"])
    v = eng["svc"].get("default", p["id"])["latest"]
    assert [x["name"] for x in v["parts"]] == ["base_plate", "spur_gear", "bearing_6204"]
    assert v["material"] == "aluminium" and v["mass_g"] == pytest.approx(v["volume_mm3"] * 2.7 / 1000, rel=0.01)
    assert set(v["files"]) >= {"part.step", "part.stl", "part.3mf", "part.glb", "section.dxf", "drawing.pdf"}
    assert "fits_220_bed" in v["print"] and v["com"] and len(v["com"]) == 3
    assert eng["seen"][0]["think"] is True                                  # an assembly gets extended thinking
    from fastapi.testclient import TestClient
    from app.main import app
    pdf = TestClient(app).get(v["files"]["drawing.pdf"]).content
    assert pdf[:4] == b"%PDF" and pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages") == 2   # shaded + line views


def test_v0362_vision_review_finds_a_miss_and_the_fix_uses_the_pictures(eng, monkeypatch):
    monkeypatch.setenv("ENG_LOOK_ROUNDS", "1")
    eng["hire"].hire("default", "cad")
    eng["replies"] += [GOOD, '{"ok": false, "problems": ["the ask wants 3 holes, the plate has 2"]}', GOOD]
    p = eng["svc"].start("default", "", "L bracket with three holes")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "done" and d["latest"]["review"]["problems"] == ["the ask wants 3 holes, the plate has 2"]
    fix_call = eng["seen"][2]
    assert "design review: the ask wants 3 holes" in fix_call["prompt"] and fix_call["images"] == 4


def test_v0362_her_step_file_and_sketch_reach_the_design(eng, tmp_path):
    import cadquery as cq
    eng["hire"].hire("default", "cad")
    src = tmp_path / "her.step"
    cq.exporters.export(cq.Workplane("XY").box(50, 50, 5), str(src))
    uses = GOOD.replace("result = base.union(wall)", "result = base.union(wall).union(H.her_file('her.step').translate((0, 0, -7.5)))") \
               .replace("SIZE: 80 x 40 x 30", "SIZE: 80 x 50 x 35")
    eng["replies"].append(uses)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    p = eng["svc"].start("default", "", "bracket that sits on my plate", images=[png], files=[("her.step", src.read_bytes())])
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "done", d["error"]
    assert "her.step" in eng["seen"][0]["prompt"] and eng["seen"][0]["images"] == 1
    assert d["inputs"] == ["sketch_1.png", "her.step"]


def test_v0362_fake_step_and_wrong_types_are_refused(eng):
    eng["hire"].hire("default", "cad")
    with pytest.raises(eng["svc"].EngError, match="asli STEP"):
        eng["svc"].start("default", "", "bracket", files=[("x.step", b"hello")])
    with pytest.raises(eng["svc"].EngError, match="step / .stp / .stl"):
        eng["svc"].start("default", "", "bracket", files=[("x.exe", b"MZ")])
    with pytest.raises(eng["svc"].EngError, match="PNG, JPG"):
        eng["svc"].start("default", "", "bracket", images=[b"GIF89a"])
