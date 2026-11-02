"""GEAR TOOTH STRENGTH: the gear's root is now the real TROCHOID a hob cuts (it had a sharp corner and no fillet),
and the teeth are checked to ISO 6336 for bending (does a tooth snap off) and pitting (do the flanks crumble).

The geometry is proved TWICE, independently: the trochoid Hoola generates is measured with ISO's own 30-degree
tangent rule, and compared with ISO 6336-3's closed-form equations. They agree to under 1 % on the root chord and
the bending arm for 10 to 200 teeth, which is the real check on both. The factors are checked against their
published values (Z_H = 2.495 at 20 degrees) and the whole thing against hand-worked numbers.
"""
import math

import pytest

cq = pytest.importorskip("cadquery")


def _two_ways(z, m=1.0, x=0.0):
    from app.engineering import gears
    return gears.iso_root(m, z, 20.0, x), gears.measured_root(gears.profile(m, z, 20.0, x))


def test_the_generated_root_and_the_standards_equations_agree():
    """The one test that proves the trochoid generator AND the ISO transcription at the same time."""
    for z in (10, 12, 17, 20, 25, 30, 50, 80, 120, 200):
        iso, me = _two_ways(z)
        assert me["s_Fn_m"] == pytest.approx(iso["s_Fn_m"], rel=0.01), f"root chord, z={z}"
        assert me["h_Fa_m"] == pytest.approx(iso["h_Fa_m"], rel=0.01), f"bending arm, z={z}"
        assert me["rho_F_m"] == pytest.approx(iso["rho_F_m"], rel=0.03), f"fillet radius, z={z}"
        assert 28.0 <= me["tangent_deg"] <= 32.0                      # it really is the 30 degree tangent


def test_the_fillet_sits_on_the_root_circle_and_meets_the_flank():
    import numpy as np

    from app.engineering import gears
    for z, m in ((14, 2.0), (20, 1.0), (40, 3.0), (90, 1.5)):
        pr = gears.profile(m, z, 20.0)
        r = np.linalg.norm(pr["half"], axis=1)
        assert r.min() == pytest.approx(pr["rf"], abs=1e-4)           # the hob's tip just touches the root circle
        assert r.max() == pytest.approx(pr["ra"], rel=1e-5)
        assert pr["join_gap_mm"] < 0.01 * m                           # fillet and involute meet, no step
        assert pr["rho_fP"] == pytest.approx(0.38 * m)


def test_iso_numbers_for_a_standard_20_tooth_gear():
    """Worked by hand from ISO 6336-3 (G, E, H, theta, then the factors) and pinned here."""
    from app.engineering import gears
    iso = gears.iso_root(1.0, 20, 20.0, 0.0)
    assert iso["G"] == pytest.approx(-0.87, abs=1e-6)                  # rho_fP - h_fP + x
    assert iso["E"] == pytest.approx(0.0643566, abs=1e-6)
    assert iso["H"] == pytest.approx(-0.89655, abs=1e-4)
    assert iso["theta_deg"] == pytest.approx(46.19, abs=0.05)
    assert iso["s_Fn_m"] == pytest.approx(1.9430, rel=2e-3)
    assert iso["rho_F_m"] == pytest.approx(0.5725, rel=2e-3)
    assert iso["h_Fa_m"] == pytest.approx(1.9021, rel=2e-3)
    assert iso["Y_Fa"] == pytest.approx(3.2635, rel=3e-3)
    assert iso["Y_Sa"] == pytest.approx(1.5528, rel=3e-3)
    assert iso["q_s_in_range"]


def test_undercut_is_found_and_a_profile_shift_cures_it():
    from app.engineering import gears
    few = gears.profile(1.0, 10, 20.0)
    assert few["undercut"] and few["below_classical_limit"]
    assert few["teeth_for_no_undercut"] == pytest.approx(17.1, abs=0.1)
    ok = gears.profile(1.0, 20, 20.0)
    assert not ok["undercut"] and not ok["below_classical_limit"]
    assert not gears.profile(1.0, 10, 20.0, 0.5)["undercut"]           # shifted out: the hob no longer cuts in
    # A ROUNDED hob tip undercuts less than the sharp-cornered rack the 17-tooth rule assumes: its straight flank
    # stops 0.74 m below the pitch line instead of 1.0 m, which moves the real limit to about 2 x 0.74 / sin^2(20)
    # = 12.6 teeth. Measured on the generated tooth, both ways round:
    assert not gears.profile(1.0, 12, 20.0)["undercut"]                 # standard hob, rho_fP = 0.38 m
    assert gears.profile(1.0, 12, 20.0, 0.0, {"rho_fP": 0.0})["undercut"]   # sharp corner: it does cut in
    mid = gears.profile(1.0, 14, 20.0)
    assert not mid["undercut"] and mid["below_classical_limit"]         # so 14 teeth is only a WARNING, not a fault


def test_the_published_factors():
    from app.engineering import gears
    r = gears.pair(2.0, 20, 60, 20.0, 15.0, 1400.0)
    f = r["factors"]
    assert f["Z_H"] == pytest.approx(2.495, abs=0.002)                 # ISO 6336-2's own value at 20 degrees
    nu, E = 0.29, 200000.0                                             # Z_E from the table's own constants
    assert f["Z_E"] == pytest.approx(math.sqrt(1 / (math.pi * 2 * (1 - nu ** 2) / E)), rel=1e-3)
    assert 1.6 <= r["contact_ratio"] <= 1.75                           # a standard 20/60 pair: textbook 1.6-1.7
    assert r["ratio"] == 3.0 and r["d1_mm"] == 40.0
    assert r["tangential_N"] == pytest.approx(2000 * 15.0 / 40.0, rel=1e-6)
    assert r["speed_m_s"] == pytest.approx(math.pi * 40.0 * 1400 / 60000.0, abs=1e-3)
    kv_slow, _ = gears.kv_agma(1.0, 8)
    kv_fast, note = gears.kv_agma(40.0, 6)
    assert 1.0 < kv_slow < kv_fast and note                            # rough gear, high speed: Hoola says so
    assert gears.grade_for("case hardened steel")[0] == "case hardened"
    assert gears.grade_for("nylon")[1] < gears.grade_for("steel")[1]


def test_the_stresses_move_the_way_the_physics_says():
    from app.engineering import gears
    base = gears.pair(2.0, 20, 60, 20.0, 15.0, 1400.0, application="uniform", quality=8)
    twice = gears.pair(2.0, 20, 60, 20.0, 30.0, 1400.0, application="uniform", quality=8)
    assert twice["bending_MPa"] == pytest.approx(2 * base["bending_MPa"], rel=1e-3)      # bending is linear in load
    assert twice["contact_MPa"] == pytest.approx(math.sqrt(2) * base["contact_MPa"], rel=0.01)  # contact as sqrt
    wide = gears.pair(2.0, 20, 60, 40.0, 15.0, 1400.0, application="uniform", quality=8)
    assert wide["bending_MPa"] < 0.55 * base["bending_MPa"]
    big_m = gears.pair(4.0, 20, 60, 20.0, 15.0, 1400.0, application="uniform", quality=8)
    assert big_m["bending_MPa"] < 0.3 * base["bending_MPa"]            # module is the strongest move (~1/m²)
    rough = gears.pair(2.0, 20, 60, 20.0, 15.0, 1400.0, application="heavy shock", quality=6)
    assert rough["bending_MPa"] > base["bending_MPa"]
    soft = gears.pair(3.0, 20, 60, 25.0, 40.0, 900.0, material="mild steel")
    hard = gears.pair(3.0, 20, 60, 25.0, 40.0, 900.0, material="case hardened")
    assert not soft["ok"] and hard["ok"] and hard["bending_sf"] > 2 * soft["bending_sf"]
    assert soft["bending_MPa"] == pytest.approx(hard["bending_MPa"], rel=1e-9)   # same load: only the ALLOWABLE moved
    with pytest.raises(gears.GearError):
        gears.pair(2.0, 4, 60, 20.0, 15.0, 1400.0)


def test_the_gear_solid_has_the_real_root(tmp_path):
    from app.engineering import parts
    parts.GEARS.clear()
    g = parts.spur_gear(2.0, 20, 10, bore=8)
    sh = g.val()
    assert sh.isValid() and sh.Volume() > 0
    rec = parts.GEARS[-1]
    assert rec["teeth"] == 20 and rec["module"] == 2.0 and not rec["undercut"]
    parts.GEARS.clear()
    parts.spur_gear(1.0, 10, 5)
    assert parts.GEARS[-1]["undercut"]                                  # 10 teeth: the hob cuts the flank
    parts.GEARS.clear()
    parts.GEAR_DUTY.clear()
    parts.gear_duty(2.0, 20, 60, 20, 15.0, 1400.0, application="medium shock")
    assert parts.GEAR_DUTY[0]["pinion_teeth"] == 20
    with pytest.raises(ValueError, match="8 daante"):
        parts.spur_gear(2.0, 5, 10)
    parts.GEARS.clear()
    parts.GEAR_DUTY.clear()


def test_the_calculator_and_the_guide_know_gears():
    from app.agent.eng_tools import ENG_TOOLS
    from app.engineering import ai, calc
    r = calc.run("gear", {"module": 3.0, "pinion_teeth": 20, "wheel_teeth": 60, "width_mm": 25.0,
                          "torque_Nm": 40.0, "rpm": 900.0, "material": "case hardened"})
    assert r["ok"] and r["bending_sf"] > 1.4 and "DRAFT" in r["note"]
    tool = next(t for t in ENG_TOOLS if t["name"] == "eng_calc")
    assert "gear" in tool["input_schema"]["properties"]["kind"]["enum"] and "ISO 6336" in tool["description"]
    assert "H.gear_duty" in ai.GUIDE and "case hardened" in ai.GUIDE and "1/module" in ai.GUIDE
    from app.engineering.report import gear_rows
    rows = gear_rows(r)
    assert any("Tooth bending" in x for x in rows) and any("Flank pitting" in x for x in rows)
    assert any("Assumed:" in x for x in rows)


GEAR = """TITLE: Gearbox pair
MATERIAL: {mat}
ASSUMED: none
PLAN: pinion + wheel
NOTES: test
```python
import cadquery as cq
pinion = H.spur_gear({m}, 20, 20, bore=10)
wheel = H.spur_gear({m}, 60, 20, bore=16).translate(({cc}, 0, 0))
H.gear_duty({m}, 20, 60, 20, torque_Nm=40, rpm=900, application='uniform', min_sf=1.4)
result = cq.Assembly(name='gearbox').add(pinion, name='pinion').add(wheel, name='wheel')
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


def test_a_gear_too_weak_for_its_torque_comes_back(desk):
    desk["replies"] += [GEAR.format(m=1.5, cc=60, mat="steel"),
                        GEAR.format(m=4, cc=160, mat="case hardened steel")]
    p = desk["svc"].start("default", "", "gearbox: 20 and 60 tooth steel gears, 40 Nm at 900 rpm")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    back = desk["seen"][1]
    assert "Tooth bending" in back and "Flank pitting" in back       # both told the designer what was wrong
    assert "module" in back and "case-hardened" in back
    v = d["latest"]
    gd = v["gear_duty"][0]
    assert gd["module"] == 4.0 and gd["bending_sf"] >= 1.4 and gd["pitting_sf"] >= 1.4
    assert gd["material"] == "case hardened"                         # it took the harder steel, as advised
    assert all(c["ok"] for c in v["checks"] if "Gear" in c["name"])
    assert "analysis.pdf" in v["files"]
