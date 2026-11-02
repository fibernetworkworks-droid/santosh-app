"""CAMS, SLOTS, DYNAMICS: a cam designed from the follower motion (laws checked at textbook points, roller
geometry, pressure angle / undercut / cusp checks), a pin-in-slot loop (Scotch yoke = R cos theta exactly), and
the mechanism moved in MuJoCo (slow move = statics, fast move = more, a weak motor saturates, cam torque = follower
force x ds/dtheta)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engineering"))

SEG = [{"type": "rise", "lift": 10, "deg": 120, "law": "cycloidal"}, {"type": "dwell", "deg": 60},
       {"type": "return", "lift": 10, "deg": 120, "law": "cycloidal"}, {"type": "dwell", "deg": 60}]


def test_motion_laws_at_textbook_points():
    import cams
    b = math.radians(120)
    for law, vmax, amax in (("cycloidal", 2 * 10 / b, 2 * math.pi * 10 / b ** 2),
                            ("harmonic", math.pi * 10 / (2 * b), math.pi ** 2 * 10 / (2 * b ** 2)),
                            ("345", 1.875 * 10 / b, 5.7735 * 10 / b ** 2)):
        pg = cams.program([{**SEG[0], "law": law}, SEG[1], {**SEG[2], "law": law}, SEG[3]], 7200)
        i = int(np.argmin(abs(pg["theta"] - math.radians(60))))
        assert pg["s"][i] == pytest.approx(5.0, abs=1e-3), law                     # half lift at half angle
        assert pg["v"].max() == pytest.approx(vmax, rel=2e-3), law
        assert pg["a"].max() == pytest.approx(amax, rel=3e-3), law
    with pytest.raises(ValueError, match="360"):
        cams.program([{"type": "rise", "lift": 5, "deg": 100}])
    with pytest.raises(ValueError, match="end where it started"):
        cams.program([{"type": "rise", "lift": 5, "deg": 180}, {"type": "return", "lift": 3, "deg": 180}])


def test_roller_cam_geometry_and_checks():
    import cams
    spec = {"segments": SEG, "base_radius": 30, "roller_radius": 6, "rpm": 120}
    d = cams.design(spec)
    from scipy.spatial import cKDTree
    dist, _ = cKDTree(d["profile"]).query(d["pitch"])
    assert dist.min() == pytest.approx(6, abs=0.05) and dist.max() == pytest.approx(6, abs=0.3)
    rows = {r["check"]: r for r in d["rows"]}
    assert rows["Pressure angle"]["ok"] and rows["Undercut (pitch curve vs roller)"]["ok"]
    assert cams.solid(spec, d).val().isValid()
    bad = cams.design({"segments": [{"type": "rise", "lift": 25, "deg": 40, "law": "harmonic"}, {"type": "dwell", "deg": 140},
                                    {"type": "return", "lift": 25, "deg": 40, "law": "harmonic"}, {"type": "dwell", "deg": 140}],
                       "base_radius": 12, "roller_radius": 10})
    brow = {r["check"]: r for r in bad["rows"]}
    assert not brow["Pressure angle"]["ok"] and not brow["Undercut (pitch curve vs roller)"]["ok"]
    flat = cams.design({"segments": SEG, "base_radius": 5, "follower": "flat"})
    assert not flat["rows"][0]["ok"]                                                # cusps on a tiny base circle


def _run(tmp, parts, joints, robot, coup=None):
    import kinematics
    return kinematics.run(parts, joints, robot, "steel", tmp, coup)


def test_scotch_yoke_slot(tmp_path):
    import kinematics
    frame = cq.Workplane("XY").box(200, 20, 6).translate((0, -60, 0)).val()
    crank = cq.Workplane("XY").box(36, 8, 4, centered=(False, True, True)).translate((-3, 0, 6)).val()
    yoke = cq.Workplane("XY").box(12, 80, 4).translate((30, 0, 12)).val()
    J = [{"name": "crank_spin", "parent": "frame", "child": "crank", "kind": "continuous", "origin": (0, 0, 0),
          "axis": (0, 0, 1), "driver": True},
         {"name": "yoke_slide", "parent": "frame", "child": "yoke", "kind": "prismatic", "origin": (30, -60, 0),
          "axis": (1, 0, 0), "limits": (-80, 80)},
         {"name": "pin", "parent": "yoke", "child": "crank", "kind": "slot", "origin": (30, 0, 0), "axis": (0, 0, 1),
          "direction": (0, 1, 0), "travel": (-40, 40)}]
    r = _run(tmp_path, [("frame", frame), ("crank", crank), ("yoke", yoke)], J, {"name": "yoke"})
    assert r["ok"] and r["slots"] == ["pin"] and r["passive"] == ["yoke_slide"]
    js = [dict(j, limits_si=(-0.08, 0.08) if j["kind"] == "prismatic" else (-math.pi, math.pi)) for j in J]
    mech = kinematics.Mech(kinematics.tree(["frame", "crank", "yoke"], js), js, [])
    for deg in (30, 90, 200):
        qq, ok, _ = kinematics.solve_path(mech, {"crank_spin": math.radians(deg)}, 200)
        assert ok and qq["yoke_slide"] * 1000 == pytest.approx(30 * math.cos(math.radians(deg)) - 30, abs=1e-3)
    rows = {x["check"]: x for x in r["urdf"]["rows"]}
    assert rows["MuJoCo loads the MJCF"]["ok"]
    dyn = r["dynamics"]
    assert dyn["ok"] and dyn["loop_gap_m"] < 5e-4
    assert dyn["rows"][0]["peak_speed"] == pytest.approx(180, rel=0.05)              # one turn in 2 s


def _pendulum(L=150):
    base = cq.Workplane("XY").box(40, 40, 40, centered=(True, True, False)).val()
    link = cq.Workplane("XY").box(L, 20, 10, centered=(False, True, True)).translate((0, 30, 50)).val()
    J = [{"name": "shoulder", "parent": "base", "child": "link", "origin": (0, 30, 50), "axis": (0, 1, 0),
          "limits": (-90, 90)}]
    return [("base", base), ("link", link)], J


def test_slow_move_equals_statics_fast_move_needs_more(tmp_path):
    pytest.importorskip("mujoco")
    parts, J = _pendulum()
    m = 150 * 20 * 10 * 7.85e-6
    static = m * 9.80665 * 0.075                                                     # horizontal: m g L/2
    slow = _run(tmp_path / "s", parts, J, {"name": "p", "move_time_s": 30})
    assert slow["dynamics"]["rows"][0]["peak"] == pytest.approx(static, rel=0.03)
    fast = _run(tmp_path / "f", parts, J, {"name": "p", "move_time_s": 0.3})
    assert fast["dynamics"]["rows"][0]["peak"] > 1.5 * static
    assert fast["dynamics"]["rows"][0]["sized_to"] == pytest.approx(fast["dynamics"]["rows"][0]["peak"] * 1.25, rel=1e-3)
    weak = _run(tmp_path / "w", parts, [{**J[0], "effort": 0.3 * static}], {"name": "p", "move_time_s": 2})
    row = weak["dynamics"]["rows"][0]
    assert row["saturated_pct"] > 2 and not row["ok"] and not weak["dynamics"]["ok"]


def test_cam_torque_is_follower_force_times_ds_dtheta(tmp_path):
    pytest.importorskip("mujoco")
    import parts as lib
    lib.COUPLES.clear()
    lib.CAMS.clear()
    plate = cq.Workplane("XY").box(200, 200, 4).translate((0, 0, -10)).val()
    camw = lib.disc_cam("c1", SEG, base_radius=30, roller_radius=6, rpm=60, cam_joint="cam_spin", follower_joint="lift")
    rod = cq.Workplane("XY").box(8, 60, 8, centered=(True, False, False)).translate((0, 36, 0)).val()
    J = [{"name": "cam_spin", "parent": "plate", "child": "cam", "kind": "continuous", "origin": (0, 0, 0), "axis": (0, 0, 1)},
         {"name": "lift", "parent": "plate", "child": "rod", "kind": "prismatic", "origin": (0, 36, 4), "axis": (0, 1, 0),
          "limits": (0, 12)}]
    g = 9.80665
    r = _run(tmp_path, [("plate", plate), ("cam", camw.val()), ("rod", rod)], J,
             {"name": "cammech", "gravity": (0, -g, 0), "cams": dict(lib.CAMS), "move_time_s": 2.0}, list(lib.COUPLES))
    assert r["ok"] and r["couplings"][0]["cam"] == "c1"
    row = next(x for x in r["dynamics"]["rows"] if x["joint"] == "cam_spin")
    import cams
    pg = cams.program(SEG, 7200)
    w = 2 * math.pi                                                                    # 60 rpm
    m = 8 * 60 * 8 * 7.85e-6
    tau = m * (g + pg["a"] * w * w / 1000) * pg["v"] / 1000                           # F x ds/dtheta (m / rad)
    assert row["follower_peak"] == pytest.approx(float(np.max(np.abs(tau))), rel=0.12)
    assert row["cam_peak"] >= row["follower_peak"] * 0.9                              # + the eccentric disc's own torque
    fl = next(x for x in r["dynamics"]["rows"] if x["joint"] == "lift")
    assert fl["worst_error"] < 0.5                                                     # the follower kept to the curve


CAM = """TITLE: Cam
MATERIAL: steel
ASSUMED: none
PLAN: cam + follower
NOTES: test
```python
import cadquery as cq
plate = cq.Workplane('XY').box(200, 200, 4).translate((0, 0, -10))
cam = H.disc_cam('main', [{{'type': 'rise', 'lift': 25, 'deg': {deg}, 'law': 'harmonic'}}, {{'type': 'dwell', 'deg': {dwell}}},
                     {{'type': 'return', 'lift': 25, 'deg': {deg}, 'law': 'harmonic'}}, {{'type': 'dwell', 'deg': {dwell}}}],
            base_radius={rb}, roller_radius=6, rpm=30)
result = cq.Assembly(name='cam_assy').add(plate, name='plate').add(cam, name='cam')
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


def test_a_steep_cam_is_redesigned(desk):
    desk["replies"] += [CAM.format(deg=40, dwell=140, rb=15), CAM.format(deg=150, dwell=30, rb=60)]
    p = desk["svc"].start("default", "", "cam that lifts a roller follower 25 mm and back each turn, 30 rpm")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "cam main: Pressure angle" in desk["seen"][1]
    v = d["latest"]
    assert all(c["ok"] for c in v["checks"] if c["name"].startswith("Cam main"))
    assert "camcurve.png" in v["files"]
