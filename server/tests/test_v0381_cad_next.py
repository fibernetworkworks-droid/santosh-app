"""CAD next phase: laminar CFD (checked against Poiseuille pipe flow), fatigue life (Shigley stress-life), VDI 2230
style bolted joints, and the desk loop: a part that would crack from fatigue goes back to be redesigned; a flow study
runs on its own FLUID body exported from the CAD script."""
import math

import pytest

skfem = pytest.importorskip("skfem")
cq = pytest.importorskip("cadquery")


def test_pipe_flow_matches_poiseuille():
    from app.engineering import fea
    D, L = 10.0, 60.0
    pipe = cq.Workplane("YZ").circle(D / 2).extrude(L).val()
    r = fea.flow(pipe, {"inlet": "<X", "outlet": ">X", "flow_lpm": 0.06, "fluid": "water", "nodes": 2500,
                        "inertia": False})
    q = 0.06 / 60 / 1000
    exact_dp = 128 * 1e-3 * (L / 1000) * q / (math.pi * (D / 1000) ** 4)          # 0.244 Pa
    exact_umax = 2 * q * 1e9 / (math.pi * (D / 2) ** 2)                            # 25.5 mm/s
    assert abs(r["max_speed_mm_s"] - exact_umax) / exact_umax < 0.06
    assert 0.95 * exact_dp < r["pressure_drop_Pa"] < 1.2 * exact_dp            # + a short entrance length
    assert abs(r["mass_balance_pct"] - 100) < 1.0
    assert r["regime"] == "laminar" and r["valid"] and r["surface"]["t"]


def test_turbulent_flow_is_flagged_not_valid():
    from app.engineering import fea
    pipe = cq.Workplane("YZ").circle(5).extrude(30).val()
    r = fea.flow(pipe, {"inlet": "<X", "outlet": ">X", "flow_lpm": 30, "fluid": "water", "nodes": 600,
                        "inertia": False})
    assert r["reynolds"] > 2000 and r["valid"] is False and r["turbulent_estimate_Pa_per_m"] > 0


def test_fatigue_life_and_endurance_follow_shigley():
    from app.engineering import calc, fea
    en = fea.endurance("steel", fea.MATERIALS["steel"], "machined", 20, 90)
    assert en["ka"] == pytest.approx(4.51 * 400 ** -0.265, abs=1e-3)                 # Marin surface factor
    assert en["kb"] == pytest.approx(1.24 * 20 ** -0.107, abs=1e-3)
    ok = calc.fatigue(120, -120, "steel", finish="ground", size_mm=10)
    assert ok["predicted_cycles"].startswith("infinite") and ok["fatigue_sf"] > 1
    bad = calc.fatigue(150, -150, "aluminium")
    assert float(bad["predicted_cycles"]) < 1e6 and bad["fatigue_sf"] < 1
    notch = calc.fatigue(100, 0, "steel", kt=2.5)
    assert notch["Kf"] == pytest.approx(2.2) and notch["sigma_a_MPa"] == pytest.approx(110)


def test_bolted_joint_vdi_style():
    from app.engineering import calc
    j = calc.joint(12, "8.8", grip_mm=40, plates="steel", load_N=20000, bolts=4, shear_N=8000)
    assert 0.1 < j["load_factor_C"] < 0.3                                           # stiff plates take most load
    assert j["preload_N"] == round(0.75 * 580 * 84.3) and j["ok"]
    weak = calc.joint(6, "4.6", grip_mm=10, plates="aluminium", load_N=30000, bolts=2, shear_N=20000)
    assert weak["ok"] is False and weak["safety"]["separation"] < 1.2
    with pytest.raises(calc.CalcError):
        calc.joint(7, "8.8")


def test_static_study_reports_fatigue():
    from app.engineering import fea
    bar = cq.Workplane("XY").box(100, 10, 10, centered=(False, True, True)).val()
    r = fea.static(bar, {"fixed": "<X", "loads": [{"faces": ">X", "force": [0, 0, -150]}], "material": "aluminium",
                         "nodes": 1200, "converge": False, "fatigue": {"load": "reversed", "life": 1e7}})
    f = r["fatigue"]
    assert f["load"] == "reversed" and f["sigma_m_MPa"] == 0 and f["passes"] in (True, False)
    assert f["sigma_a_MPa"] == pytest.approx(r["peak_vm_away_MPa"], rel=1e-3)


# ---------------------------------------------------------------- desk loop
FATIGUE = """TITLE: Pedal arm
SIZE: 150 x 20 x {t}
MATERIAL: aluminium
ASSUMED: none
PLAN: arm fixed at one end, pedal load at the tip, millions of presses
NOTES: test
```python
import cadquery as cq
result = cq.Workplane('XY').box(150, 20, {t}, centered=(False, True, False))
H.analyze('static', fixed='<X', loads=[{{'faces': '>X', 'force': (0, 0, -300)}}], nodes=700, converge=False,
          fatigue={{'load': 'zero_to_max', 'life': 1e7, 'min_sf': 1.5}})
```"""

FLOW = """TITLE: Manifold block
SIZE: 60 x 30 x 30
MATERIAL: aluminium
ASSUMED: none
PLAN: block with a 10 mm bore, water through it
NOTES: test
```python
import cadquery as cq
block = cq.Workplane('XY').box(60, 30, 30)
bore = cq.Workplane('YZ').circle(5).extrude(60).translate((-30, 0, 0))
result = block.cut(bore)
H.analyze('flow', domain=bore, inlet='<X', outlet='>X', flow_lpm=0.03, fluid='water', nodes=900, inertia=False,
          max_dp_pa=50)
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


def test_part_that_would_crack_is_redesigned(desk):
    desk["replies"] += [FATIGUE.format(t=5), FATIGUE.format(t=16)]
    p = desk["svc"].start("default", "", "aluminium pedal arm 150 mm, 30 kg presses, 10 million cycles")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "fatigue: under her repeated load" in desk["seen"][1]
    st = d["latest"]["analysis"][0]
    assert st["fatigue"]["passes"] is True and d["latest"]["bbox"]["z"] == 16


def test_flow_study_runs_on_the_fluid_body(desk):
    desk["replies"].append(FLOW)
    p = desk["svc"].start("default", "", "manifold block with a 10 mm bore, water 0.03 L/min, pressure drop")
    desk["svc"].run_job(p["id"])
    v = desk["svc"].get("default", p["id"])["latest"]
    st = v["analysis"][0]
    assert st["ok"] and st["kind"] == "flow" and st["valid"] and 0 < st["pressure_drop_Pa"] < 50
    assert any("Flow (laminar CFD)" in line for line in st["lines"])
    assert "fea_0.png" in v["files"] and "analysis.pdf" in v["files"]


def test_flow_without_a_fluid_body_is_refused():
    from app.engineering import parts
    with pytest.raises(ValueError, match="domain"):
        parts.analyze("flow", inlet="<X", outlet=">X")
