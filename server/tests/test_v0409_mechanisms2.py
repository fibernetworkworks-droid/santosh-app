"""MECHANISMS 2: closed loops (four-bar checked against the analytic solution), joint torque from loads (checked
against beam statics AND MuJoCo's own gravity forces), gear / belt couplings, SDF + MJCF + SRDF in the package
(MuJoCo loads the MJCF), a motor too weak sent back to the designer."""
import io
import json
import math
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engineering"))


def _bar(p, q, z, w=6):
    v = q - p
    return (cq.Workplane("XY").box(float(np.linalg.norm(v)), w, 4, centered=(False, True, True))
            .rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(v[1], v[0]))).translate((p[0], p[1], z)).val())


def _fourbar(a=20.0, b=70.0, c=50.0, d=80.0):
    A, D = np.array([0.0, 0.0]), np.array([d, 0.0])
    B = A + a * np.array([0.0, 1.0])
    dv = D - B
    L = np.linalg.norm(dv)
    x = (b * b - c * c + L * L) / (2 * L)
    C = B + x * dv / L + math.sqrt(b * b - x * x) * np.array([-dv[1], dv[0]]) / L
    parts = [("ground", _bar(A, D, 0)), ("crank", _bar(A, B, 6)), ("coupler", _bar(B, C, 12)), ("rocker", _bar(D, C, 18))]
    joints = [{"name": "j_crank", "parent": "ground", "child": "crank", "origin": (0, 0, 0), "axis": (0, 0, 1),
               "limits": (-180, 180), "driver": True},
              {"name": "j_bc", "parent": "crank", "child": "coupler", "origin": (B[0], B[1], 0), "axis": (0, 0, 1),
               "limits": (-180, 180)},
              {"name": "j_rocker", "parent": "ground", "child": "rocker", "origin": (D[0], D[1], 0), "axis": (0, 0, 1),
               "limits": (-180, 180)},
              {"name": "j_cd", "parent": "coupler", "child": "rocker", "origin": (C[0], C[1], 0), "axis": (0, 0, 1),
               "closure": True}]
    return parts, joints, (A, B, C, D)


def test_four_bar_matches_the_analytic_linkage(tmp_path):
    import kinematics
    parts, joints, (A, B, C, D) = _fourbar()
    r = kinematics.run(parts, joints, {"name": "fourbar"}, "steel", tmp_path)
    assert r["ok"] and r["loops"] == ["j_cd"] and r["drivers"] == ["j_crank"]
    fb = r["fourbar"][0]
    assert fb["grashof"].startswith("crank-rocker")
    a, b, c, d = 20, 70, 50, 80
    mus = []
    for k in range(361):
        cm = (b * b + c * c - a * a - d * d + 2 * a * d * math.cos(math.radians(k))) / (2 * b * c)
        mu = math.degrees(math.acos(cm))
        mus.append(min(mu, 180 - mu))
    assert fb["min_transmission_deg"] == pytest.approx(min(mus), abs=0.5)           # 57.1°
    # the solved pose keeps every link length
    js = [dict(j, kind="revolute", limits_si=(-math.pi, math.pi)) for j in joints]
    mech = kinematics.Mech(kinematics.tree([p[0] for p in parts], js), js, [])
    qq, ok, _ = kinematics.solve_path(mech, {"j_crank": math.radians(60)}, 100)
    W = mech.tf(qq)
    Cn = (W["rocker"] @ np.array([C[0], C[1], 0, 1.0]))[:2]
    Bn = 20 * np.array([math.cos(math.radians(150)), math.sin(math.radians(150))])
    assert ok and np.linalg.norm(Cn - Bn) == pytest.approx(70, abs=1e-3) and np.linalg.norm(Cn - D) == pytest.approx(50, abs=1e-3)
    names = set(zipfile.ZipFile(tmp_path / "robot_urdf.zip").namelist())
    assert {"fourbar/robot.urdf", "fourbar/robot.sdf", "fourbar/robot.xml", "fourbar/robot.srdf"} <= names
    rows = {x["check"]: x for x in r["urdf"]["rows"]}
    assert all(x["ok"] for x in rows.values())


def test_a_non_grashof_linkage_locks():
    import kinematics
    parts, joints, _ = _fourbar(a=45, b=40, c=50, d=60)              # s + l = 100 > p + q = 95
    js = [dict(j, kind="revolute", limits_si=(-math.pi, math.pi)) for j in joints]
    mech = kinematics.Mech(kinematics.tree([p[0] for p in parts], js), js, [])
    _q, ok, _e = kinematics.solve_path(mech, {"j_crank": math.radians(179)}, 100, steps=30)
    assert not ok                                                     # the crank cannot turn all the way


def _arm2():
    base = cq.Workplane("XY").box(40, 40, 40, centered=(True, True, False)).val()
    l1 = cq.Workplane("XY").box(150, 20, 10, centered=(False, True, True)).translate((0, 30, 50)).val()
    l2 = cq.Workplane("XY").box(100, 16, 8, centered=(False, True, True)).translate((150, 50, 50)).val()
    parts = [("base", base), ("link1", l1), ("link2", l2)]
    joints = [{"name": "shoulder", "parent": "base", "child": "link1", "origin": (0, 30, 50), "axis": (0, 1, 0),
               "limits": (-90, 90)},
              {"name": "elbow", "parent": "link1", "child": "link2", "origin": (150, 50, 50), "axis": (0, 1, 0),
               "limits": (-120, 120)}]
    return parts, joints


def test_holding_torque_matches_statics_and_mujoco(tmp_path):
    import kinematics
    parts, joints = _arm2()
    r = kinematics.run(parts, joints, {"name": "arm2", "payload": {"part": "link2", "kg": 0.5, "at": (250, 50, 50)}},
                       "aluminium", tmp_path)
    m1, m2 = 150 * 20 * 10 * 2.7e-6, 100 * 16 * 8 * 2.7e-6
    g = 9.80665
    exact = g * (m1 * 0.075 + m2 * 0.200 + 0.5 * 0.250)               # arm straight out, horizontal
    sh = next(x for x in r["torque"] if x["joint"] == "shoulder")
    assert sh["static"] == pytest.approx(exact, rel=0.01)
    el = next(x for x in r["torque"] if x["joint"] == "elbow")
    assert el["static"] == pytest.approx(g * (m2 * 0.05 + 0.5 * 0.1), rel=0.01)
    j_sh = next(j for j in r["joints"] if j["name"] == "shoulder")
    dyn = next((x for x in (r.get("dynamics") or {}).get("rows") or [] if x["joint"] == "shoulder"), None)
    want = max(round(sh["need"] * 1.5, 3), round(dyn["peak"] * 1.25, 4) if dyn else 0.0)
    assert j_sh["effort"] == pytest.approx(want, rel=1e-6)          # need x 1.5, or the real move's peak x 1.25 (v0.425)
    mujoco = pytest.importorskip("mujoco")
    z = zipfile.ZipFile(tmp_path / "robot_urdf.zip")
    z.extractall(tmp_path / "pkg")
    model = mujoco.MjModel.from_xml_path(str(tmp_path / "pkg" / "arm2" / "robot.xml"))
    data = mujoco.MjData(model)
    q = {"shoulder": 0.4, "elbow": -0.7}
    for jn, v in q.items():
        data.qpos[model.joint(jn).qposadr[0]] = v
    mujoco.mj_forward(model, data)
    js = [dict(j, kind="revolute", limits_si=(-math.pi, math.pi)) for j in joints]
    mech = kinematics.Mech(kinematics.tree(["base", "link1", "link2"], js), js, [])
    props = {}
    from fea import material
    for n, s in parts:
        props[n] = kinematics.mass_props(s, material("aluminium")[1]["rho"] * 1000)
    gv = np.array([0, 0, -9.80665])
    for jn in q:
        a, b = dict(q), dict(q)
        a[jn] -= 1e-5
        b[jn] += 1e-5
        ours = (kinematics._potential(mech, b, props, None, 300, gv) - kinematics._potential(mech, a, props, None, 300, gv)) / 2e-5
        theirs = float(data.qfrc_bias[model.joint(jn).dofadr[0]])
        assert ours == pytest.approx(theirs, rel=1e-3, abs=1e-6), jn       # MuJoCo's own gravity force


def test_gear_coupling_and_mimic(tmp_path):
    import kinematics
    plate = cq.Workplane("XY").box(120, 60, 5).val()
    g1 = cq.Workplane("XY").circle(20).extrude(6).translate((-20, 0, 3)).val()
    g2 = cq.Workplane("XY").circle(40).extrude(6).translate((40, 0, 3)).val()
    js = [{"name": "spin1", "parent": "plate", "child": "gear1", "kind": "continuous", "origin": (-20, 0, 0), "axis": (0, 0, 1)},
          {"name": "spin2", "parent": "plate", "child": "gear2", "kind": "continuous", "origin": (40, 0, 0), "axis": (0, 0, 1)}]
    import parts as lib
    lib.COUPLES.clear()
    lib.couple("spin2", "spin1", teeth=(20, 40))
    r = kinematics.run([("plate", plate), ("gear1", g1), ("gear2", g2)], js, {"name": "gears"}, "steel", tmp_path,
                       list(lib.COUPLES))
    assert r["couplings"][0]["ratio"] == -0.5 and [j["joint"] for j in r["range"]] == ["spin1"]
    urdf = ET.fromstring((tmp_path / "robot.urdf").read_text())
    mim = next(j for j in urdf.findall("joint") if j.get("name") == "spin2").find("mimic")
    assert mim.get("joint") == "spin1" and float(mim.get("multiplier")) == -0.5
    rows = {x["check"]: x for x in r["urdf"]["rows"]}
    assert rows["MuJoCo loads the MJCF"]["ok"]


def test_srdf_groups_and_collision_pairs(tmp_path):
    import kinematics
    parts, joints = _arm2()
    kinematics.run(parts, joints, {"name": "arm2"}, "aluminium", tmp_path)
    srdf = ET.fromstring(zipfile.ZipFile(tmp_path / "robot_urdf.zip").read("arm2/robot.srdf"))
    assert srdf.find("group/chain").get("base_link") == "base"
    reasons = {(d.get("link1"), d.get("link2")): d.get("reason") for d in srdf.findall("disable_collisions")}
    assert reasons[("base", "link1")] == "Adjacent" and reasons[("link1", "link2")] == "Adjacent"
    assert set(reasons.values()) <= {"Adjacent", "Never", "Default", "Always"}


def test_loop_that_does_not_close_is_named(tmp_path):
    import kinematics
    parts, joints, _ = _fourbar()
    joints[3] = {**joints[3], "origin": (joints[3]["origin"][0] + 60, joints[3]["origin"][1] + 60, 0)}
    r = kinematics.run(parts, joints, {}, "steel", tmp_path)
    assert not r["ok"] and "is not on part 'coupler'" in " ".join(r["problems"])


WEAK = """TITLE: Arm
MATERIAL: steel
ASSUMED: none
PLAN: two link arm
NOTES: test
```python
import cadquery as cq
base = cq.Workplane('XY').box(40, 40, 40, centered=(True, True, False))
link = cq.Workplane('XY').box({L}, 20, 10, centered=(False, True, True)).translate((0, 30, 50))
result = cq.Assembly(name='arm_assy').add(base, name='base').add(link, name='link')
H.joint('shoulder', parent='base', child='link', origin=(0, 30, 50), axis=(0, 1, 0), limits=(-90, 90), effort=0.5)
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


def test_a_motor_too_weak_is_sent_back(desk):
    # steel 200 x 20 x 10 at 0.1 m: ~0.31 N m > her 0.5? no - 0.31 < 0.5 passes; 400 mm long needs ~1.2 N m > 0.5
    desk["replies"] += [WEAK.format(L=400), WEAK.format(L=150)]
    p = desk["svc"].start("default", "", "steel arm on a base, shoulder motor 0.5 N m, give me the URDF and SDF")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "needs" in desk["seen"][1] and "her motor gives 0.5" in desk["seen"][1]
    tq = next(c for c in d["latest"]["checks"] if c["name"] == "Joint shoulder torque")
    assert tq["ok"]
