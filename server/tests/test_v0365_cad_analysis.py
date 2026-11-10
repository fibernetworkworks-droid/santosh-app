"""v0.365 HOOLA CAD ANALYSIS: FEA checked against textbook answers, the engineering calculator against ISO tables,
real threads, sheet metal + flat pattern, freeform, her numbers measured (H.expect), CNC G-code, and the whole loop:
a weak part comes back from the FEA and is redesigned until it meets her safety factor."""
import math

import pytest

skfem = pytest.importorskip("skfem")
cq = pytest.importorskip("cadquery")


def _bar():
    return cq.Workplane("XY").box(100, 10, 10, centered=(False, True, True)).val()


# ---------------------------------------------------------------- FEA vs theory
def test_static_cantilever_matches_beam_theory():
    from app.engineering import fea
    r = fea.static(_bar(), {"fixed": "<X", "loads": [{"faces": ">X", "force": [0, 0, -100]}], "material": "steel",
                            "nodes": 2500, "converge": False, "min_sf": 2})
    exact = 100 * 100 ** 3 / (3 * 200000 * (10 ** 4 / 12))            # PL³/3EI = 0.2 mm
    assert abs(r["max_disp_mm"] - exact) / exact < 0.06
    assert r["equilibrium_error_pct"] < 1.0                            # reactions balance the load
    assert 50 < r["peak_vm_away_MPa"] < 75                             # σ = M c / I = 60 MPa at the root
    assert r["passes"] is True and r["safety_factor"] > 3
    assert r["surface"]["t"] and len(r["surface"]["tc"]) == len(r["surface"]["t"])


def test_thermal_bar_matches_conduction():
    from app.engineering import fea
    r = fea.thermal(_bar(), {"temps": [{"faces": "<X", "temp": 20}], "heat": [{"faces": ">X", "watts": 2}],
                             "material": "aluminium", "nodes": 1500})
    exact = 20 + 2 * 100 / (0.167 * 100)                               # T = T0 + Q L / (k A)
    assert abs(r["t_max_C"] - exact) < 0.2


def test_modal_cantilever_first_frequency():
    from app.engineering import fea
    r = fea.modal(_bar(), {"fixed": "<X", "material": "steel", "modes": 2, "nodes": 1500, "avoid_hz": [700, 900]})
    exact = 1.875 ** 2 / (2 * math.pi * 100 ** 2) * math.sqrt(200000 * (10 ** 4 / 12) / (7.85e-9 * 100))
    assert abs(r["frequencies_hz"][0] - exact) / exact < 0.05          # ~815 Hz
    assert r["resonance"]["ok"] is False                               # her 700-900 Hz band is hit


def test_bad_selector_is_a_plain_error():
    from app.engineering import fea
    with pytest.raises(fea.FeaError):
        fea.static(_bar(), {"fixed": "<X", "loads": [{"faces": "%SPHERE", "force": [0, 0, -1]}], "nodes": 600,
                            "converge": False})


# ---------------------------------------------------------------- calculator
def test_iso_fits_and_stack_and_bolt_and_beam():
    from app.engineering import calc
    f = calc.fit(25, "H7/g6")
    assert f["hole_mm"] == [25.0, 25.021] and f["shaft_mm"] == [24.98, 24.993] and f["kind"] == "clearance"
    assert calc.fit(25, "H7/p6")["kind"] == "interference" and calc.fit(25, "H7/k6")["kind"] == "transition"
    s = calc.stack([{"nominal": 50, "tol": 0.1}, {"nominal": 20, "tol": 0.05, "dir": -1},
                    {"nominal": 29.5, "tol": 0.05, "dir": -1}], lower=0.2, upper=0.8, runs=20000)
    assert s["worst_case"] == [0.3, 0.7] and s["worst_case_ok"] and s["cpk"] > 1.33
    b = calc.bolt(8, "8.8", 4, shear_N=20000)
    assert b["tensile_area_mm2"] == 36.6 and b["ok"] and 20 < b["torque_Nm"] < 30
    bm = calc.beam("cantilever", 100, {"type": "rect", "b": 10, "h": 10}, load_N=100)
    assert bm["max_deflection_mm"] == 0.2 and bm["max_bending_stress_MPa"] == 60.0
    assert calc.pipe(0.5, 20, 1)["regime"] == "laminar"
    with pytest.raises(calc.CalcError):
        calc.fit(25, "X9/q2")


# ---------------------------------------------------------------- library: threads, sheet, freeform, checks
def test_real_thread_and_tapped_hole_are_valid():
    from app.engineering import parts
    rod = parts.thread(8, 12).val()
    assert rod.isValid() and math.pi * 3.0 ** 2 * 12 < rod.Volume() < math.pi * 4 ** 2 * 12
    block = cq.Workplane("XY").box(20, 20, 12).cut(parts.thread_tool(8, 12).translate((0, 0, -6))).val()
    assert block.isValid() and len(block.Solids()) == 1


def test_sheet_metal_flat_length_and_dxf():
    from app.engineering import parts, report
    z = parts.sheet([(40, 90), (30, -90), (25, 0)], 50, 2)
    v = z.val()
    assert v.isValid()
    fl = parts.FLAT["sheet"]
    # outside 40 + 30 + 25 = 95, minus 4 setbacks of (r + t) = 4, plus 2 bend allowances of π/2 (2 + 0.44·2)
    assert abs(fl["length"] - (95 - 4 * 4 + 2 * math.pi / 2 * (2 + 0.88))) < 1e-3
    assert abs(v.Volume() - fl["length"] * 50 * 2) / v.Volume() < 0.02
    dxf = report.flat_dxf(fl)
    assert "BEND" in dxf and dxf.count("\nLINE\n") == 4 + 2
    t = parts.tray(120, 80, 30, 1.5)
    assert t.val().isValid() and parts.FLAT["sheet"]["kind"] == "tray"


def test_freeform_bodies_are_valid():
    from app.engineering import parts
    g = parts.smooth_loft([(0, 30, 25, 1), (40, 34, 28, 0.8, 2), (90, 26, 22, 1), (110, 20, 18, 1)]).val()
    assert g.isValid() and g.BoundingBox().zlen == pytest.approx(110, abs=0.01)
    assert parts.spline_sweep([(0, 0, 0), (30, 10, 20), (60, 0, 40)], 5).val().isValid()


def test_her_numbers_are_measured():
    from app.engineering import geom
    p = (cq.Workplane("XY").box(80, 50, 12).faces(">Z").workplane()
         .rect(60, 30, forConstruction=True).vertices().hole(5.5)).val()
    rows = geom.check_expect(p, [{"size": (80, 50, 12)}, {"holes": {"d": 5.5, "count": 4}},
                                 {"holes": {"d": 6.6, "count": 2}}, {"max_size": (70, 70, 70)}])
    assert [r["ok"] for r in rows] == [True, True, False, False]


def test_cnc_gcode_for_a_plate():
    from app.engineering import cam
    p = (cq.Workplane("XY").box(80, 50, 12).faces(">Z").workplane().rect(60, 30, forConstruction=True).vertices()
         .hole(5.5).faces(">Z").workplane().rect(30, 16).cutBlind(-5)).val()
    r = cam.run(p, {"tabs": 3})
    assert r["ops"] == ["face", "pocket x1", "drill x4", "profile"]
    g = r["gcode"]
    assert g.startswith("%") and "G21" in g and "M30" in g and g.count("(hole d5.5") == 4
    assert r["minutes"] > 0 and r["stock_mm"][0] == 92


# ---------------------------------------------------------------- the whole loop on the desk
WEAK = """TITLE: Shelf bracket
SIZE: 120 x 30 x {t}
MATERIAL: aluminium
ASSUMED: none
PLAN: plate fixed at one end, 200 kg-ish load at the tip
NOTES: test
```python
import cadquery as cq
result = cq.Workplane('XY').box(120, 30, {t}, centered=(False, True, False))
H.expect(size=(120, 30, {t}))
H.analyze('static', fixed='<X', loads=[{{'faces': '>X', 'force': (0, 0, -800)}}], min_sf=2, nodes=700, converge=False)
H.cam(ops=['profile'])
```"""


@pytest.fixture
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("ENG_WORKER", "false")
    monkeypatch.setenv("ENG_DIR", str(tmp_path / "eng"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("ENG_LOOK_ROUNDS", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.engineering import ai, service
    replies, seen = [], []

    def fake_ask(system, prompt, images=None, max_tokens=8000, think=False):
        seen.append(prompt)
        return replies.pop(0)
    monkeypatch.setattr(ai, "ask", fake_ask)
    from app.employee import hire
    hire.hire("default", "cad")
    yield {"svc": service, "replies": replies, "seen": seen}
    get_settings.cache_clear()


def test_weak_part_is_sent_back_and_strengthened(desk):
    desk["replies"] += [WEAK.format(t=4), WEAK.format(t=14)]
    p = desk["svc"].start("default", "", "aluminium shelf bracket 120 x 30, 80 kg at the tip, safety factor 2")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "too weak under her load" in desk["seen"][1]               # the FEA told the designer where and why
    v = d["latest"]
    st = v["analysis"][0]
    assert st["ok"] and st["passes"] is True and st["safety_factor"] >= 2 and st["lines"]
    assert v["bbox"]["z"] == 14 and all(c["ok"] for c in v["checks"])
    assert any(c["name"].startswith("Asked:") for c in v["checks"])
    assert v["cam"]["ok"] and v["cam"]["ops"] == ["profile"]
    assert set(v["files"]) >= {"analysis.pdf", "fea_0.png", "part.nc"}


def test_missed_requirement_goes_back_to_the_model(desk):
    bad = WEAK.format(t=14).replace("H.expect(size=(120, 30, 14))", "H.expect(size=(120, 30, 20))")
    bad = bad.replace("H.analyze('static', fixed='<X', loads=[{'faces': '>X', 'force': (0, 0, -800)}], min_sf=2, nodes=700, converge=False)\n", "")
    good = bad.replace("box(120, 30, 14", "box(120, 30, 20").replace("SIZE: 120 x 30 x 14", "SIZE: 120 x 30 x 20")
    desk["replies"] += [bad, good]
    p = desk["svc"].start("default", "", "plate 120 x 30 x 20")
    desk["svc"].run_job(p["id"])
    assert "her requirement 'Size' fails" in desk["seen"][1]
    assert desk["svc"].get("default", p["id"])["latest"]["bbox"]["z"] == 20


def test_calc_tool_is_registered():
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF.get("eng_calc") == "eng" and "eng_calc" in HANDLERS
