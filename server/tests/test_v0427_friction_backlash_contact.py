"""FRICTION, BACKLASH, CAM CONTACT: bearing friction = mu x the real joint load x the pin radius (checked by hand),
gear / belt backlash as a gap (tip play = angle x reach exactly; lost motion and knocks in a fast move), and the cam's
contact force: the return spring that keeps the follower on, Hertz stress against Shigley's own cylinder formula,
the guide jam check, and the MuJoCo follower force agreeing with m (s'' w^2 + g)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engineering"))

SEG = [{"type": "rise", "lift": 10, "deg": 120, "law": "cycloidal"}, {"type": "dwell", "deg": 60},
       {"type": "return", "lift": 10, "deg": 120, "law": "cycloidal"}, {"type": "dwell", "deg": 60}]
G = 9.80665


def _geo(spec):
    import cams
    return cams.geometry(cams.design(spec))


def test_hertz_matches_shigley_cylinders():
    import cams
    n = 50
    geo = {"theta": list(np.linspace(0, 2 * math.pi, n, endpoint=False)), "s": [0.0] * n, "v": [0.0] * n,
           "a": [0.0] * n, "phi": [0.0] * n, "rho": [30.0] * n}
    r = cams.contact(geo, [1000.0] * n, 60, roller_radius=6, width=10, spring_k=0, preload=0,
                     E=((200000.0, 0.29), (200000.0, 0.29)))
    F, L, d1, d2 = 1000.0, 10.0, 12.0, 60.0                       # Shigley eq. 3-73 / 3-74 (diameters)
    k = 2 * (1 - 0.29 ** 2) / 200000.0
    b = math.sqrt(2 * F / (math.pi * L) * k / (1 / d1 + 1 / d2))
    assert r["max_hertz_mpa"] == pytest.approx(2 * F / (math.pi * b * L), rel=1e-3)
    hz = next(x for x in r["rows"] if x["check"].startswith("Contact stress"))
    assert r["rows"][0]["ok"] and not hz["ok"] and "640" in hz["limit"]          # 834 MPa > steel's 640


def test_spring_keeps_the_follower_on_and_a_weak_one_fails():
    import cams
    geo = _geo({"segments": SEG, "base_radius": 30, "roller_radius": 6})
    m, rpm = 0.5, 300
    F = cams.need_from_motion(geo, m, rpm, -G)                       # lifting straight up against gravity
    w = rpm * 2 * math.pi / 60
    assert float(np.min(F)) == pytest.approx(m * (min(geo["a"]) * w * w / 1000 + G), rel=1e-9)
    assert float(np.min(F)) < 0                                       # without a spring it would leave the cam
    bare = cams.contact(geo, F, rpm, spring_k=0, preload=0)
    assert not bare["rows"][0]["ok"] and bare["min_push_n"] == pytest.approx(float(np.min(F)), abs=1e-4)
    d = cams.contact(geo, F, rpm)
    assert d["spring_designed"] and d["rows"][0]["ok"] and d["min_push_n"] > 0
    s_m = np.asarray(geo["s"]) / 1000
    push = F + d["spring_k_n_mm"] * 1000 * s_m + d["preload_n"]
    assert float(np.min(push)) == pytest.approx(d["min_push_n"], rel=1e-3)
    assert np.all(d["spring_k_n_mm"] * 1000 * s_m + d["preload_n"] >= 1.3 * np.maximum(0, -F) - 1e-6)
    slow = cams.contact(geo, cams.need_from_motion(geo, m, 20, -G), 20)
    assert slow["spring_k_n_mm"] == 0 and "not needed" in slow["rows"][1]["measured"]


def test_guide_jams_at_a_steep_pressure_angle():
    import cams
    steep = {"segments": [{"type": "rise", "lift": 25, "deg": 60, "law": "harmonic"}, {"type": "dwell", "deg": 120},
                          {"type": "return", "lift": 25, "deg": 60, "law": "harmonic"}, {"type": "dwell", "deg": 120}],
             "base_radius": 20, "roller_radius": 6}
    geo = _geo(steep)
    F = cams.need_from_motion(geo, 0.2, 30, -G)
    bad = cams.contact(geo, F, 30, guide_mu=0.3, guide_len=20, overhang=40)
    assert not next(r for r in bad["rows"] if r["check"].startswith("Follower guide"))["ok"]
    good = cams.contact(_geo({"segments": SEG, "base_radius": 40, "roller_radius": 6}), F, 30, guide_mu=0.1,
                        guide_len=40, overhang=10)
    assert next(r for r in good["rows"] if r["check"].startswith("Follower guide"))["ok"]


def _cam_mech(lib, tmp, rpm, **kw):
    import kinematics
    lib.COUPLES.clear()
    lib.CAMS.clear()
    plate = cq.Workplane("XY").box(200, 200, 4).translate((0, 0, -10)).val()
    camw = lib.disc_cam("c1", SEG, base_radius=30, roller_radius=6, rpm=rpm, cam_joint="cam_spin", follower_joint="lift", **kw)
    rod = cq.Workplane("XY").box(8, 60, 8, centered=(True, False, False)).translate((0, 36, 0)).val()
    J = [{"name": "cam_spin", "parent": "plate", "child": "cam", "kind": "continuous", "origin": (0, 0, 0), "axis": (0, 0, 1)},
         {"name": "lift", "parent": "plate", "child": "rod", "kind": "prismatic", "origin": (0, 36, 4), "axis": (0, 1, 0),
          "limits": (0, 12)}]
    return kinematics.run([("plate", plate), ("cam", camw.val()), ("rod", rod)], J,
                          {"name": "cammech", "gravity": (0, -G, 0), "cams": dict(lib.CAMS), "move_time_s": 0.4},
                          "steel", tmp, list(lib.COUPLES))


def test_mujoco_follower_force_agrees_with_the_motion(tmp_path):
    pytest.importorskip("mujoco")
    import cams
    import parts as lib
    r = _cam_mech(lib, tmp_path, 300)
    ct = r["cam_contact"]["c1"]
    assert ct["force_from"] == "the MuJoCo move"
    m = 8 * 60 * 8 * 7.85e-6
    geo = lib.CAMS["c1"]["geo"]
    F = cams.need_from_motion(geo, m, 300, -G)
    hand = cams.contact(geo, F, 300)
    assert ct["spring_k_n_mm"] == pytest.approx(hand["spring_k_n_mm"], rel=0.05)
    assert ct["min_push_n"] == pytest.approx(hand["min_push_n"], rel=0.05)
    assert all(x["ok"] for x in ct["rows"])
    weak = _cam_mech(lib, tmp_path / "w", 300, spring_k=0, preload=0)["cam_contact"]["c1"]
    assert not weak["rows"][0]["ok"]                                  # her (no) spring lets it jump


def _pend():
    base = cq.Workplane("XY").box(40, 40, 40, centered=(True, True, False)).val()
    link = cq.Workplane("XY").box(150, 20, 10, centered=(False, True, True)).translate((0, 30, 50)).val()
    J = {"name": "shoulder", "parent": "base", "child": "link", "origin": (0, 30, 50), "axis": (0, 1, 0),
         "limits": (-90, 90)}
    return base, link, J


def test_bearing_friction_is_mu_load_radius(tmp_path):
    pytest.importorskip("mujoco")
    import kinematics
    base, link, J = _pend()
    m = 150 * 20 * 10 * 7.85e-6
    r = kinematics.run([("base", base), ("link", link)], [{**J, "bearing": "dry", "pin_d": 20}],
                       {"name": "p", "move_time_s": 30}, "steel", tmp_path / "a")
    fr = r["dynamics"]["friction"][0]
    assert fr["peak"] == pytest.approx(0.2 * m * G * 0.010, rel=0.03)            # slow: the load = the weight
    assert r["dynamics"]["rows"][0]["peak"] == pytest.approx(m * G * 0.075 + fr["peak"], rel=0.03)
    assert r["dynamics"]["friction_share_pct"] > 0
    c = kinematics.run([("base", base), ("link", link)], [{**J, "friction": 0.05, "damping": 0.001}],
                       {"name": "p", "move_time_s": 30}, "steel", tmp_path / "b")
    assert c["dynamics"]["friction"][0]["peak"] >= 0.05
    import zipfile
    z = zipfile.ZipFile(tmp_path / "b" / "robot_urdf.zip")
    urdf = next(z.read(n).decode() for n in z.namelist() if n.endswith(".urdf"))
    mj = next(z.read(n).decode() for n in z.namelist() if n.endswith("robot.xml"))
    assert 'friction="0.05"' in urdf and 'damping="0.001"' in urdf
    assert 'frictionloss="0.05"' in mj
    import dynamics
    with pytest.raises(ValueError, match="bearing"):
        dynamics.friction_of({**J, "kind": "revolute", "bearing": "magic"})


def test_backlash_tip_play_lost_motion_and_knocks(tmp_path):
    import kinematics
    base, link, J = _pend()
    mot = cq.Workplane("XY").box(20, 20, 20).translate((0, 0, 30)).val()
    J2 = [{"name": "in", "parent": "base", "child": "motor", "origin": (0, 0, 30), "axis": (0, 1, 0), "limits": (-90, 90)},
          {**J, "name": "out", "parent": "base", "child": "link"}]
    parts = [("base", base), ("motor", mot), ("link", link)]
    C = [{"follower": "out", "leader": "in", "ratio": 1.0, "backlash": 1.0}]
    r = kinematics.run(parts, J2, {"name": "bl", "move_time_s": 3, "accuracy_mm": 1.0}, "steel", tmp_path / "s", C)
    bl = r["backlash"][0]
    reach = math.hypot(150, 10)                                                   # the far corner of the link
    assert bl["tip_play_mm"] == pytest.approx(math.radians(1.0) * reach, rel=0.02) and not bl["ok"]
    if r["dynamics"].get("ok") is None:
        pytest.skip("mujoco missing")
    slow = r["dynamics"]["backlash"][0]
    assert slow["knocks"] == 0 and 0.5 <= slow["lost_motion"] < 0.6              # rests on one flank: half the play
    fast = kinematics.run(parts, J2, {"name": "bl", "move_time_s": 0.3}, "steel", tmp_path / "f", C)["dynamics"]["backlash"][0]
    assert fast["knocks"] >= 1 and fast["peak_mesh"] > 5 * slow["peak_mesh"]    # the gap closes the other way: a knock


CAM = """TITLE: Cam
MATERIAL: steel
ASSUMED: none
PLAN: cam + follower
NOTES: test
```python
import cadquery as cq
plate = cq.Workplane('XY').box(200, 200, 4).translate((0, 0, -10))
cam = H.disc_cam('main', [{{'type': 'rise', 'lift': 10, 'deg': 120, 'law': 'cycloidal'}}, {{'type': 'dwell', 'deg': 60}},
                          {{'type': 'return', 'lift': 10, 'deg': 120, 'law': 'cycloidal'}}, {{'type': 'dwell', 'deg': 60}}],
                 base_radius=30, roller_radius=6, rpm=300, cam_joint='cam_spin', follower_joint='lift'{spring})
rod = cq.Workplane('XY').box(8, 60, 8, centered=(True, False, False)).translate((0, 36, 0))
H.joint('cam_spin', 'plate', 'cam', kind='continuous', origin=(0, 0, 0), axis=(0, 0, 1))
H.joint('lift', 'plate', 'rod', kind='prismatic', origin=(0, 36, 4), axis=(0, 1, 0), limits=(0, 12))
H.robot(name='cammech', gravity=(0, -9.80665, 0), move_time_s=0.4)
result = cq.Assembly(name='cam_assy').add(plate, name='plate').add(cam, name='cam').add(rod, name='rod')
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


def test_a_cam_whose_follower_jumps_is_redesigned(desk):
    desk["replies"] += [CAM.format(spring=", spring_k=0.001, preload=0.01"), CAM.format(spring="")]
    p = desk["svc"].start("default", "", "cam that lifts a rod 10 mm and back at 300 rpm")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "cam main: Follower stays on the cam" in desk["seen"][1]
    v = d["latest"]
    rows = [c for c in v["checks"] if c["name"].startswith("Cam main")]
    assert any(c["name"] == "Cam main: Return spring" and "k " in c["note"] for c in rows)
    assert all(c["ok"] for c in rows)
