"""v0.79x 3D SCENES AS CHECKED DATA (owner: "HOW BIG 3D GRAPHICAL STUNNING GAME CAN BE BUILD VIA HOOLA AI" -> "GO BOTH").

The 2D rule, extended to 3D: the model writes a SPEC, Hoola checks it and GENERATES the .tscn (never the model), and every
scene is loaded in the REAL engine before she sees it. Measured in Godot 4.7.2 headless first: Vector3 transforms,
primitive meshes with StandardMaterial3D, lights + shadows, a current camera, a sky / fog / glow environment, 3D collision
shapes, Vector3 animation tracks, and an approved .glb model placed by name all load exactly as written.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.gamedesk import scene as S

COURT = {"name": "Courtyard", "root": {"type": "Node3D", "name": "Courtyard", "children": [
    {"type": "WorldEnvironment", "name": "Env", "environment": {
        "sky": {"top": "#1B2A6B", "horizon": "#F2A65A", "ground": "#2B1D14"},
        "ambient": "#FFE2B8", "ambient_energy": 0.6, "fog": True, "fog_density": 0.02, "glow": True}},
    {"type": "DirectionalLight3D", "name": "Sun",
     "props": {"rotation_degrees": [-50, 30, 0], "light_energy": 1.3, "light_color": "#FFF1D6", "shadow_enabled": True}},
    {"type": "Camera3D", "name": "Cam", "props": {"position": [0, 6, 12], "rotation_degrees": [-22, 0, 0], "fov": 60, "current": True}},
    {"type": "StaticBody3D", "name": "Ground", "children": [
        {"type": "CollisionShape3D", "name": "Shape", "shape": {"kind": "box", "size": [40, 0.5, 40]}},
        {"type": "MeshInstance3D", "name": "Mesh",
         "mesh": {"kind": "plane", "size": [40, 40], "material": {"color": "#6B4A2E", "roughness": 0.9}}}]},
    {"type": "MeshInstance3D", "name": "Diya", "props": {"position": [0, 1.2, 0]},
     "mesh": {"kind": "sphere", "radius": 0.6, "height": 1.2,
              "material": {"color": "#FFB15C", "emission": "#FF8A1F", "emission_energy": 3, "metallic": 0.1, "roughness": 0.4}}},
    {"type": "AnimationPlayer", "name": "Anim", "animations": [{"name": "spin", "length": 2, "loop": True,
        "tracks": [{"path": "Diya:rotation_degrees", "keys": [[0, [0, 0, 0]], [2, [0, 360, 0]]]}]}]},
    {"model": "chair", "name": "Chair1", "props": {"position": [3, 0, 0]}},
    {"model": "chair", "name": "Chair2", "props": {"position": [-3, 0, 0], "rotation_degrees": [0, 90, 0]}},
    {"model": "chair", "name": "Chair3", "props": {"position": [0, 0, -3]}}]}}


def _spec(*children, root_type="Node3D"):
    return {"name": "T", "root": {"type": root_type, "name": "T", "children": list(children)}}


# ================================================================ the checker
def test_a_full_3d_scene_is_accepted():
    assert S.check(COURT, set(), {"courtyard.tscn"}, models={"chair"}) == []


@pytest.mark.parametrize("node, why", [
    ({"type": "Node3D", "name": "A", "props": {"position": [1, 2]}}, "three numbers"),
    ({"type": "Node2D", "name": "A", "mesh": {"kind": "box"}}, "belongs on a MeshInstance3D"),
    ({"type": "MeshInstance3D", "name": "A", "mesh": {"kind": "teapot"}}, "mesh kind must be one of"),
    ({"type": "MeshInstance3D", "name": "A", "mesh": {"kind": "box", "material": {"metallic": 2}}}, "between 0 and 1"),
    ({"type": "MeshInstance3D", "name": "A", "mesh": {"kind": "box", "material": {"shader": "x"}}}, "material key 'shader'"),
    ({"type": "MeshInstance3D", "name": "A", "mesh": {"kind": "box", "script": "x.gd"}}, "mesh key 'script'"),
    ({"type": "Node3D", "name": "A", "environment": {"glow": True}}, "belongs on a WorldEnvironment"),
    ({"type": "WorldEnvironment", "name": "A", "environment": {"shader": 1}}, "environment key 'shader'"),
    ({"type": "WorldEnvironment", "name": "A", "environment": {"sky": {"middle": "#fff"}}}, "sky key 'middle'"),
    ({"type": "CollisionShape3D", "name": "A", "shape": {"kind": "rect"}}, "shape kind must be one of"),
    ({"model": "dragon", "name": "A"}, "not an approved 3D model"),
    ({"model": "chair", "type": "Node3D", "name": "A"}, "only one"),
    ({"model": "../../etc/passwd", "name": "A"}, "must be an asset name"),
])
def test_bad_3d_specs_are_refused_by_name(node, why):
    bad = S.check(_spec(node), set(), {"t.tscn"}, models={"chair"})
    assert any(why in b for b in bad), bad


def test_a_model_cannot_be_the_root_and_2d_scenes_are_unchanged():
    root_model = {"name": "T", "root": {"model": "chair", "name": "T"}}
    assert any("cannot itself be an instance" in b for b in S.check(root_model, set(), {"t.tscn"}, models={"chair"}))
    # a 2D node keeps 2-number positions and 2D shape kinds; a 2D rect shape is still fine
    two_d = _spec({"type": "Area2D", "name": "C", "props": {"position": [1, 2]}, "children": [
        {"type": "CollisionShape2D", "name": "S", "shape": {"kind": "rect", "size": [8, 8]}}]}, root_type="Node2D")
    assert S.check(two_d, set(), {"t.tscn"}) == []


def test_script_source_is_still_refused_in_3d():
    for key in ("source", "code", "gdscript"):
        bad = S.check(_spec({"type": "MeshInstance3D", "name": "A", key: "print(1)"}), set(), {"t.tscn"})
        assert any("script source" in b for b in bad), (key, bad)


# ================================================================ the generator
def test_the_generated_tscn_is_real_godot_3d():
    files, probs = S.build_all([COURT], set(), models={"chair"})
    assert probs == []
    t = files["courtyard.tscn"]
    for want in ('[node name="Courtyard" type="Node3D"]', 'type="StandardMaterial3D"', "albedo_color = Color(",
                 "emission_enabled = true", 'type="SphereMesh"', 'type="PlaneMesh"', "size = Vector2(40.0, 40.0)",
                 'type="BoxShape3D"', "size = Vector3(40.0, 0.5, 40.0)", 'type="ProceduralSkyMaterial"', 'type="Sky"',
                 "background_mode = 2", "fog_enabled = true", "glow_enabled = true", "shadow_enabled = true",
                 "position = Vector3(0.0, 6.0, 12.0)", "rotation_degrees = Vector3(-50.0, 30.0, 0.0)", "current = true",
                 '[ext_resource type="PackedScene" path="res://assets/chair.glb"', "Vector3(0.0, 360.0, 0.0)"):
        assert want in t, want
    assert t.count('instance=ExtResource(') == 3, "one model file, placed three times"
    assert not S.BANNED_TEXT.search(t)


# ================================================================ the real engine
def _godot() -> str:
    from app.gamedesk import engine
    return engine.find() or ""


def _make_glb(godot: str, where: Path) -> Path:
    """A real .glb, written by Godot itself (GLTFDocument) - no Blender needed for the test."""
    proj = where / "mk"
    (proj / "out").mkdir(parents=True)
    (proj / "project.godot").write_text('config_version=5\n[application]\nconfig/name="mk"\n')
    (proj / "mk.gd").write_text(
        "extends SceneTree\nfunc _init() -> void:\n\tvar r = Node3D.new(); r.name = \"Chair\"\n"
        "\tvar m = MeshInstance3D.new(); m.name = \"Seat\"; var b = BoxMesh.new(); b.size = Vector3(1, 0.2, 1); m.mesh = b\n"
        "\tr.add_child(m); m.owner = r\n\tvar d = GLTFDocument.new(); var s = GLTFState.new()\n"
        "\td.append_from_scene(r, s); d.write_to_filesystem(s, \"res://out/chair.glb\")\n\tquit()\n")
    subprocess.run([godot, "--headless", "--path", str(proj), "--script", "res://mk.gd"], capture_output=True, timeout=120)
    glb = proj / "out" / "chair.glb"
    assert glb.is_file(), "Godot did not write the test model"
    return glb


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_loads_a_3d_scene_with_models_and_counts_what_is_in_it(tmp_path):
    glb = _make_glb(_godot(), tmp_path)
    files, probs = S.build_all([COURT], set(), models={"chair"})
    assert probs == []
    rep = S.verify(files, {}, tmp_path / "job", models={"chair": glb})
    assert rep["verdict"] == "PASS", rep
    row = rep["scenes"][0]
    assert row["three"] is True and row["loaded"] is True
    assert row["meshes"] == 5, "plane + diya + one seat inside each of the three chairs, counted by the engine"
    assert row["lights"] == 1 and row["cameras"] == 1 and row["animations"] == ["spin"]
    assert rep["trouble"] == [] and rep["errors"] == []


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_a_missing_model_file_is_a_fail_never_a_pass(tmp_path):
    files, probs = S.build_all([COURT], set(), models={"chair"})
    assert probs == []
    rep = S.verify(files, {}, tmp_path / "job", models={"chair": tmp_path / "nope.glb"})
    assert rep["verdict"] == "FAIL", rep
    assert rep["why"], "a FAIL must say why in words"


# ================================================================ the words the model and the user see
def test_the_prompt_tool_and_view_speak_3d_honestly():
    from app.agent import tools
    from app.gamedesk import ai
    assert "3D models you may place:" in Path(ai.__file__).read_text(encoding="utf-8")   # offered per call, from her approved assets
    assert "A REAL MODEL is placed with" in ai.SCENE and "TileMaps and shaders are NOT available" in ai.SCENE
    desc = next(t["description"] for t in tools.TOOLS if t["name"] == "game_scenes")
    assert "2D and 3D" in desc and "cannot SEE how it looks" in desc and "none is ever invented" in desc and len(desc) <= 1200
    src = Path(S.__file__).read_text(encoding="utf-8")
    assert "cannot SEE a 3D scene" in src
