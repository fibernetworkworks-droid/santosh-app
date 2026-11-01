"""HOOLA MECHANISMS: joints between named assembly parts -> tree check, mass properties from the B-rep, collision
sweep with the free range, URDF (+ meshes) checked by parsing it back, motion GIF + exploded view, and a collision
inside her asked range sent back to the designer."""
import io
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

cq = pytest.importorskip("cadquery")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engineering"))


def _arm():
    base = cq.Workplane("XY").box(60, 60, 40, centered=(True, True, False)).val()
    arm1 = cq.Workplane("XY").box(120, 20, 20, centered=(False, True, False)).translate((0, 0, 40)).val()
    arm2 = cq.Workplane("XY").box(80, 16, 16, centered=(False, True, False)).translate((120, 0, 60)).val()
    return [("base", base), ("arm1", arm1), ("arm2", arm2)]


JOINTS = [{"name": "shoulder", "parent": "base", "child": "arm1", "kind": "revolute", "origin": (0, 0, 40),
           "axis": (0, 0, 1), "limits": (-150, 150)},
          {"name": "elbow", "parent": "arm1", "child": "arm2", "kind": "revolute", "origin": (120, 0, 68),
           "axis": (0, 1, 0), "limits": (-90, 90)}]


def test_tree_problems_are_named():
    import kinematics
    bad = kinematics.tree(["a", "b"], [{"name": "j", "parent": "a", "child": "c", "kind": "revolute", "axis": (0, 0, 1),
                                        "limits": (0, 10)},
                                       {"name": "j", "parent": "b", "child": "a", "kind": "hinge", "axis": (0, 0, 0),
                                        "limits": (5, 1)}])
    text = " | ".join(bad["problems"])
    for want in ("two joints share a name", "'c' is not a part", "kind hinge", "axis is zero", "limits 5"):
        assert want in text, want


def test_mass_inertia_urdf_and_free_range(tmp_path):
    import kinematics
    wall = cq.Workplane("XY").box(10, 200, 80, centered=(True, True, False)).translate((0, 110, 0)).val()
    parts = _arm() + [("wall", wall)]
    js = JOINTS + [{"name": "w", "parent": "base", "child": "wall", "kind": "fixed", "origin": (0, 0, 0)}]
    r = kinematics.run(parts, js, {"name": "demo arm"}, "aluminium", tmp_path)
    assert r["ok"] and r["robot"] == "demo_arm" and r["root"] == "base"
    arm1 = next(x for x in r["links"] if x["name"] == "arm1")
    assert arm1["mass_kg"] == pytest.approx(120 * 20 * 20 * 2.70e-6, rel=1e-4)      # 0.1296 kg
    shoulder = next(x for x in r["range"] if x["joint"] == "shoulder")
    assert shoulder["collides"] and shoulder["collides"][0]["parts"] == ["arm1", "wall"]
    assert shoulder["free"][1] < 150                                              # the wall stops it early
    elbow = next(x for x in r["range"] if x["joint"] == "elbow")
    assert elbow["free"] == [-90.0, 90.0] and not elbow["collides"]
    assert all(row["ok"] for row in r["urdf"]["rows"])
    root = ET.fromstring((tmp_path / "robot.urdf").read_text())
    links = {l.get("name"): l for l in root.findall("link")}
    ixx = float(links["arm1"].find("inertial/inertia").get("ixx"))
    assert ixx == pytest.approx(0.1296 * (0.02 ** 2 + 0.02 ** 2) / 12, rel=1e-3)   # m (b² + c²) / 12
    el = next(j for j in root.findall("joint") if j.get("name") == "elbow")
    assert el.find("origin").get("xyz").split() == ["0.12", "0", "0.028"]          # relative to arm1's frame
    lim = el.find("limit")
    assert float(lim.get("lower")) == pytest.approx(-1.5708, abs=1e-4) and lim.get("effort")
    z = zipfile.ZipFile(tmp_path / "robot_urdf.zip")
    assert {"demo_arm/robot.urdf", "demo_arm/meshes/arm1.stl", "demo_arm/meshes/base.stl"} <= set(z.namelist())
    kin = json.loads((tmp_path / "kin.json").read_text())
    assert len(kin["frames"]) == 16 and set(kin["explode"]) == {"base", "arm1", "arm2", "wall"}


def test_prismatic_and_continuous_limits(tmp_path):
    import kinematics
    base = cq.Workplane("XY").box(100, 20, 10, centered=(False, True, False)).val()
    slider = cq.Workplane("XY").box(20, 20, 10, centered=(False, True, False)).translate((0, 0, 10)).val()
    wheel = cq.Workplane("XZ").circle(8).extrude(5).translate((10, -10, 15)).val()
    r = kinematics.run([("rail", base), ("slider", slider), ("wheel", wheel)],
                       [{"name": "slide", "parent": "rail", "child": "slider", "kind": "prismatic", "origin": (0, 0, 10),
                         "axis": (1, 0, 0), "limits": (0, 80)},
                        {"name": "spin", "parent": "slider", "child": "wheel", "kind": "continuous",
                         "origin": (10, -10, 15), "axis": (0, 1, 0)}], {}, "steel", tmp_path)
    root = ET.fromstring((tmp_path / "robot.urdf").read_text())
    sl = next(j for j in root.findall("joint") if j.get("name") == "slide")
    assert sl.get("type") == "prismatic" and float(sl.find("limit").get("upper")) == pytest.approx(0.08)
    sp = next(j for j in root.findall("joint") if j.get("name") == "spin")
    assert sp.get("type") == "continuous" and sp.find("limit").get("lower") is None
    assert next(x for x in r["range"] if x["joint"] == "slide")["unit"] == "mm"


def test_motion_gif_and_explode_render(tmp_path):
    import kinematics
    from app.engineering import report
    parts = _arm()
    kinematics.run(parts, JOINTS, {}, "aluminium", tmp_path)
    kin = json.loads((tmp_path / "kin.json").read_text())
    V, T, C = [], [], []
    for i, (_n, s) in enumerate(parts):
        vv, tt = s.tessellate(1.0, 0.3)
        b = len(V)
        V += [[p.x, p.y, p.z] for p in vv]
        T += [[a + b, c + b, d + b] for a, c, d in tt]
        C += [i] * len(tt)
    mesh = {"v": V, "t": T, "c": C, "colors": [[0.5, 0.6, 0.7]] * 3}
    gif = report.motion_gif(mesh, kin, 200)
    from PIL import Image
    im = Image.open(io.BytesIO(gif))
    assert im.format == "GIF" and im.n_frames == 16
    assert report.explode_png(mesh, kin, 300)[:4] == b"\x89PNG"


ARM = """TITLE: Arm
MATERIAL: aluminium
ASSUMED: none
PLAN: base, arm, a post
NOTES: test
```python
import cadquery as cq
base = cq.Workplane('XY').box(60, 60, 40, centered=(True, True, False))
arm = cq.Workplane('XY').box(120, 20, 20, centered=(False, True, False)).translate((0, 0, 40))
post = cq.Workplane('XY').box(10, 10, 80, centered=(True, True, False)).translate(({post_x}, 0, 0))
result = cq.Assembly(name='arm_assy').add(base, name='base').add(arm, name='arm').add(post, name='post')
H.joint('shoulder', parent='base', child='arm', kind='revolute', origin=(0, 0, 40), axis=(0, 0, 1), limits=(-60, 60))
H.joint('mount', parent='base', child='post', kind='fixed')
H.robot(name='desk_arm')
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


def test_collision_in_her_range_is_redesigned(desk):
    # a post at x = 80 sits in the arm's sweep (-60..60 deg); the fix moves it out to x = 200 ... beyond the arm's reach
    desk["replies"] += [ARM.format(post_x=80), ARM.format(post_x=-200)]
    p = desk["svc"].start("default", "", "base with a swinging arm, +-60 degrees, and a post; give me the URDF")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "mechanism: joint shoulder can only move" in desk["seen"][1]
    v = d["latest"]
    assert v["kinematics"]["ok"] and v["kinematics"]["robot"] == "desk_arm"
    assert {"robot_urdf.zip", "motion.gif", "explode.png"} <= set(v["files"])
    rng = next(c for c in v["checks"] if c["name"] == "Joint shoulder range")
    assert rng["ok"]
