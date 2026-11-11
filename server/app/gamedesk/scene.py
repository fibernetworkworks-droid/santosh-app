"""v0.456 SCENES AS CHECKED DATA (docs/GAME_MOAT_PLAN.md §5.2 - the ceiling).

THE CEILING THIS LIFTS. Every Hoola game until now was at most 12 GDScript files (120 KB) on ONE plain root node,
building every node in code. That is genuinely right for match-3, idle, runner and puzzle games, where one engine plus
a lot of Game Bible data IS the game. It is false for a platformer or a story game, where the game largely IS its
scenes - so "Hoola can make a bigger game" was a claim the architecture could not keep.

THE RULE, AND WHY IT IS NOT NEGOTIABLE. The model NEVER writes a .tscn. It writes a declarative spec; this module
validates it and GENERATES the scene file. Measured in Godot 4.7.2 before a line of this was designed: a
`[sub_resource type="GDScript"]` embedded in a .tscn RUNS, and the embedded script reached `DirAccess` - which
`guard.py` has banned in every .gd file since v0.370. So a scene the model could write freehand is a hole straight
through the only thing protecting her games. Hence:
  * scripts attach ONLY by filename, to a .gd file that guard.py already checked;
  * a spec carrying script SOURCE in any shape is refused;
  * and the emitted text is re-scanned for an embedded script before it ships (defence in depth: this module is the
    only writer, but a bug in it must not become a hole).

WHAT A SPEC CAN SAY (checked in code, never in a prompt): a tree of nodes from an allowlist, each with a name, a
transform, typed properties, an optional script, collision shapes, and AnimationPlayer tracks; and INSTANCES of
another scene of the same game, which is how content actually scales - one Coin.tscn placed 200 times is data, not
200 scripts. Caps on nodes, scenes and bytes; instancing cycles refused; sibling names unique.

HOW IT IS PROVED: `verify()` writes the scenes into a real project with the guarded scripts and loads them in the
REAL engine, headless, with a quit timer - because a scene with an unknown node type does not error, it HANGS, so
"never reached the end" is itself a failure. Nothing here reports a scene as good on the strength of generating it.

v0.79x 3D: the same rule for 3D scenes - meshes with real materials, lights with shadows, a camera, a sky / fog / glow
environment, 3D physics shapes, and her APPROVED 3D models (res://assets/<key>.glb, made on the Assets tab) placed by
name, all proved in the real engine (models are imported first, exactly as a build does).

NOT BUILT, said plainly: TileMaps / GridMaps (they need a TileSet / MeshLibrary, which is art and a second pipeline), and
shaders. A headless check cannot SEE a 3D scene: it proves the scene loads and counts what is in it, not how it looks.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")

MAX_SCENES = 40
MAX_NODES = 300                      # per scene
MAX_TOTAL_NODES = 2000               # per game
MAX_BYTES = 400_000                  # all scenes together
MAX_ANIMS = 12
MAX_KEYS = 120
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
FILE = re.compile(r"^[a-z][a-z0-9_]{0,39}\.tscn$")

# Node types a 2D game needs. An unknown type does not error in Godot - it HANGS the load - so this allowlist is what
# keeps a typo from becoming a silent hang.
NODES = {
    "Node", "Node2D", "CanvasLayer", "Control", "CharacterBody2D", "RigidBody2D", "StaticBody2D", "Area2D",
    "CollisionShape2D", "Sprite2D", "AnimatedSprite2D", "ColorRect", "TextureRect", "NinePatchRect", "Label",
    "RichTextLabel", "Button", "TextureButton", "ProgressBar", "TextureProgressBar", "Timer", "AnimationPlayer",
    "Camera2D", "Path2D", "PathFollow2D", "Line2D", "Polygon2D", "Marker2D", "AudioStreamPlayer",
    "AudioStreamPlayer2D", "GPUParticles2D", "CPUParticles2D", "VBoxContainer", "HBoxContainer", "GridContainer",
    "CenterContainer", "PanelContainer", "MarginContainer", "ScrollContainer", "SubViewportContainer", "VisibleOnScreenNotifier2D",
}
# Properties we will write, with how to render them. Anything not here is dropped and NAMED, never guessed at.
VEC2 = {"position", "scale", "size", "offset", "velocity", "global_position", "pivot_offset"}
FLOATS = {"fov", "near", "far", "light_energy", "omni_range", "spot_range", "spot_angle", "mass", "rotation_degrees", "rotation", "wait_time", "speed_scale", "modulate_a", "value", "max_value", "min_value", "width",
          "zoom_x", "zoom_y", "gravity_scale", "friction", "radius", "height", "one_shot_delay"}
INTS = {"z_index", "layer", "max_lines", "amount"}
BOOLS = {"shadow_enabled", "current", "visible", "one_shot", "autostart", "flip_h", "flip_v", "disabled", "emitting", "centered"}
STRINGS = {"text", "animation", "tooltip_text", "placeholder_text"}
COLORS = {"light_color", "color", "modulate", "self_modulate", "font_color"}
SHAPES = {"rect": "RectangleShape2D", "circle": "CircleShape2D", "capsule": "CapsuleShape2D"}
# v0.79x 3D SCENES (owner: "HOW BIG 3D GRAPHICAL STUNNING GAME" -> "GO BOTH"). Measured in Godot 4.7.2 headless before a
# line was written: Vector3 position / rotation_degrees / scale, primitive meshes carrying a StandardMaterial3D, lights with
# shadows, a current Camera3D, a WorldEnvironment (colour or procedural sky, ambient, fog, glow), 3D collision shapes,
# Vector3 animation tracks, and an approved .glb model placed by its asset name all load exactly as written.
NODES3D = {
    "Node3D", "MeshInstance3D", "Camera3D", "DirectionalLight3D", "OmniLight3D", "SpotLight3D", "WorldEnvironment",
    "StaticBody3D", "RigidBody3D", "CharacterBody3D", "AnimatableBody3D", "Area3D", "CollisionShape3D", "Path3D",
    "PathFollow3D", "Marker3D", "GPUParticles3D", "CPUParticles3D", "AudioStreamPlayer3D", "VisibleOnScreenNotifier3D",
}
VEC3 = {"position", "rotation_degrees", "scale"}            # Vector3 on a 3D node (rotation_degrees is a float in 2D)
SHAPES3D = {"box": "BoxShape3D", "sphere": "SphereShape3D", "capsule": "CapsuleShape3D", "cylinder": "CylinderShape3D"}
MESHES = {"box": "BoxMesh", "sphere": "SphereMesh", "cylinder": "CylinderMesh", "capsule": "CapsuleMesh",
          "plane": "PlaneMesh", "prism": "PrismMesh", "torus": "TorusMesh"}
MODEL_KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")          # an approved 3D model asset: res://assets/<key>.glb
NODES = NODES | NODES3D
# Never, in any shape: a script's source inside a scene.
BANNED_TEXT = re.compile(r'sub_resource\s+type\s*=\s*"GDScript"|script/source|\bExpression\b|\bGDExtension\b|'
                         r'\bClassDB\b|source_code\s*=', re.I)
BANNED_KEYS = {"source", "script_source", "code", "gdscript", "script/source", "source_code", "eval", "exec"}


class SceneError(G.GameError):
    pass


# ---------------------------------------------------------------- rendering values
def _f(v: Any) -> str:
    x = float(v)
    if not (-1e7 < x < 1e7):
        raise SceneError(f"{v} is out of range")
    return repr(round(x, 4))


def _vec2(v: Any) -> str:
    if not (isinstance(v, (list, tuple)) and len(v) == 2):
        raise SceneError(f"{v!r} must be two numbers, like [120, 300]")
    return f"Vector2({_f(v[0])}, {_f(v[1])})"


def _vec3(v: Any) -> str:
    if not (isinstance(v, (list, tuple)) and len(v) == 3):
        raise SceneError(f"{v!r} must be three numbers, like [0, 1.5, -4]")
    return f"Vector3({_f(v[0])}, {_f(v[1])}, {_f(v[2])})"


def _unit(v: Any, what: str) -> str:
    x = float(v)
    if not 0.0 <= x <= 1.0:
        raise SceneError(f"{what} must be between 0 and 1")
    return _f(x)


def _color(v: Any) -> str:
    if isinstance(v, (list, tuple)) and len(v) in (3, 4):
        vals = [max(0.0, min(1.0, float(x))) for x in v] + ([1.0] if len(v) == 3 else [])
        return "Color(" + ", ".join(_f(x) for x in vals) + ")"
    t = str(v or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", t):
        raise SceneError(f"{v!r} must be a colour like #4CC2FF or [0.3, 0.7, 1]")
    nums = [int(t[i:i + 2], 16) / 255 for i in range(0, len(t), 2)]
    if len(nums) == 3:
        nums.append(1.0)
    return "Color(" + ", ".join(_f(x) for x in nums) + ")"


def _str(v: Any) -> str:
    s = str(v)[:400]
    if "\n" in s or "\r" in s:
        s = s.replace("\r", " ").replace("\n", " ")
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _prop(key: str, val: Any, three: bool = False) -> str | None:
    """One property line, or None when we do not write that key (the caller names it). `three`: a 3D node, where
    position / rotation_degrees / scale are Vector3."""
    if three and key in VEC3:
        return _vec3(val)
    if key in VEC2:
        return _vec2(val)
    if key in FLOATS:
        return _f(val)
    if key in INTS:
        return str(int(val))
    if key in BOOLS:
        return "true" if bool(val) else "false"
    if key in STRINGS:
        return _str(val)
    if key in COLORS:
        return _color(val)
    return None


# ---------------------------------------------------------------- 3D resources (mesh + material, shape, environment)
def _check_material(m: Any, path: str) -> list[str]:
    if m is None:
        return []
    if not isinstance(m, dict):
        return [f"{path}: a material must be an object"]
    out = []
    for k in m:
        if k not in ("color", "metallic", "roughness", "emission", "emission_energy", "unshaded"):
            out.append(f"{path}: Hoola does not write the material key '{k}' (it is dropped, not guessed)")
    try:
        if "color" in m: _color(m["color"])
        if "emission" in m: _color(m["emission"])
        if "metallic" in m: _unit(m["metallic"], "metallic")
        if "roughness" in m: _unit(m["roughness"], "roughness")
        if "emission_energy" in m and not 0 <= float(m["emission_energy"]) <= 16:
            out.append(f"{path}: emission_energy must be 0 - 16")
    except (SceneError, TypeError, ValueError) as e:
        out.append(f"{path}: {e}")
    return out


def _material_block(mid: str, m: dict) -> str:
    lines = [f'[sub_resource type="StandardMaterial3D" id="{mid}"]']
    if "color" in m: lines.append(f"albedo_color = {_color(m['color'])}")
    if "metallic" in m: lines.append(f"metallic = {_unit(m['metallic'], 'metallic')}")
    if "roughness" in m: lines.append(f"roughness = {_unit(m['roughness'], 'roughness')}")
    if "emission" in m:
        lines += ["emission_enabled = true", f"emission = {_color(m['emission'])}"]
        if "emission_energy" in m: lines.append(f"emission_energy_multiplier = {_f(m['emission_energy'])}")
    if m.get("unshaded"): lines.append("shading_mode = 0")
    return "\n".join(lines)


def _check_mesh(me: Any, path: str) -> list[str]:
    if not isinstance(me, dict) or str(me.get("kind")) not in MESHES:
        return [f"{path}: mesh kind must be one of {', '.join(sorted(MESHES))}"]
    out = [f"{path}: Hoola does not write the mesh key '{k}' (it is dropped, not guessed)" for k in me
           if k not in ("kind", "size", "radius", "height", "inner_radius", "outer_radius", "material")]
    try:
        if "size" in me:
            (_vec2 if me["kind"] == "plane" else _vec3)(me["size"])
        for k in ("radius", "height", "inner_radius", "outer_radius"):
            if k in me and not 0 < float(me[k]) <= 10000:
                out.append(f"{path}: mesh {k} must be above 0")
    except (SceneError, TypeError, ValueError) as e:
        out.append(f"{path}: {e}")
    return out + _check_material(me.get("material"), path)


def _mesh_blocks(sid: str, me: dict) -> list[str]:
    blocks, lines = [], [f'[sub_resource type="{MESHES[me["kind"]]}" id="{sid}"]']
    if "size" in me:
        lines.append(f"size = {(_vec2 if me['kind'] == 'plane' else _vec3)(me['size'])}")
    for k in ("radius", "height", "inner_radius", "outer_radius"):
        if k in me:
            lines.append(f"{k} = {_f(me[k])}")
    if isinstance(me.get("material"), dict):
        blocks.append(_material_block(sid + "_mat", me["material"]))
        lines.append(f'material = SubResource("{sid}_mat")')
    return blocks + ["\n".join(lines)]


ENV_KEYS = {"background", "sky", "ambient", "ambient_energy", "fog", "fog_density", "glow"}


def _check_env(en: Any, path: str) -> list[str]:
    if not isinstance(en, dict):
        return [f"{path}: environment must be an object"]
    out = [f"{path}: Hoola does not write the environment key '{k}'" for k in en if k not in ENV_KEYS]
    try:
        if "background" in en: _color(en["background"])
        if "ambient" in en: _color(en["ambient"])
        if "sky" in en:
            sk = en["sky"]
            if not isinstance(sk, dict):
                out.append(f"{path}: sky must be an object of colours (top, horizon, ground)")
            else:
                for k, v in sk.items():
                    if k not in ("top", "horizon", "ground"):
                        out.append(f"{path}: sky key '{k}' is not one Hoola writes")
                    else:
                        _color(v)
        if "fog_density" in en and not 0 <= float(en["fog_density"]) <= 1:
            out.append(f"{path}: fog_density must be 0 - 1")
        if "ambient_energy" in en and not 0 <= float(en["ambient_energy"]) <= 16:
            out.append(f"{path}: ambient_energy must be 0 - 16")
    except (SceneError, TypeError, ValueError) as e:
        out.append(f"{path}: {e}")
    return out


def _env_blocks(eid: str, en: dict) -> list[str]:
    blocks, lines = [], [f'[sub_resource type="Environment" id="{eid}"]']
    if isinstance(en.get("sky"), dict):
        sk = en["sky"]
        mat = [f'[sub_resource type="ProceduralSkyMaterial" id="{eid}_skym"]']
        if "top" in sk: mat.append(f"sky_top_color = {_color(sk['top'])}")
        if "horizon" in sk:
            mat += [f"sky_horizon_color = {_color(sk['horizon'])}", f"ground_horizon_color = {_color(sk['horizon'])}"]
        if "ground" in sk: mat.append(f"ground_bottom_color = {_color(sk['ground'])}")
        blocks.append("\n".join(mat))
        blocks.append(f'[sub_resource type="Sky" id="{eid}_sky"]\nsky_material = SubResource("{eid}_skym")')
        lines += ["background_mode = 2", f'sky = SubResource("{eid}_sky")']
    elif "background" in en:
        lines += ["background_mode = 1", f"background_color = {_color(en['background'])}"]
    if "ambient" in en:
        lines += ["ambient_light_source = 2", f"ambient_light_color = {_color(en['ambient'])}"]
    if "ambient_energy" in en: lines.append(f"ambient_light_energy = {_f(en['ambient_energy'])}")
    if en.get("fog"):
        lines.append("fog_enabled = true")
        if "fog_density" in en: lines.append(f"fog_density = {_f(en['fog_density'])}")
    if en.get("glow"): lines.append("glow_enabled = true")
    return blocks + ["\n".join(lines)]


# ---------------------------------------------------------------- the checker
def check(spec: dict, scripts: set[str], scenes: set[str], _seen: set[str] | None = None,
          models: set[str] | None = None) -> list[str]:
    """Everything wrong with one scene spec, in plain words. Empty list = it can be generated."""
    out: list[str] = []
    name = str((spec or {}).get("name") or "")
    if not NAME.match(name):
        out.append(f"scene name {name!r}: a letter then letters / digits / _ , up to 32 characters")
    root = (spec or {}).get("root")
    if not isinstance(root, dict):
        out.append("the scene has no root node")
        return out
    if root.get("instance") or root.get("model") is not None:
        out.append("the root of a scene cannot itself be an instance of another scene or a model")
    count = {"n": 0, "anims": 0}

    def walk(node: Any, path: str, siblings: set[str]) -> None:
        if not isinstance(node, dict):
            out.append(f"{path}: a node must be an object")
            return
        count["n"] += 1
        if count["n"] > MAX_NODES:
            if count["n"] == MAX_NODES + 1:
                out.append(f"more than {MAX_NODES} nodes in one scene - split it, or place instances instead")
            return
        nm = str(node.get("name") or "")
        if not NAME.match(nm):
            out.append(f"{path}: node name {nm!r} is not allowed (a letter then letters / digits / _)")
        elif nm in siblings:
            out.append(f"{path}: two children both called {nm!r}")
        siblings.add(nm)
        for k in node:
            if str(k).lower() in BANNED_KEYS:
                out.append(f"{path}/{nm}: '{k}' is refused - a scene may never carry script source "
                           "(an embedded script in a .tscn RUNS and escapes the code guard)")
        inst = node.get("instance")
        model = node.get("model")
        three = False
        if model is not None:
            # v0.79x a real 3D model: an APPROVED asset of this game, placed by its name (res://assets/<key>.glb)
            three = True
            if node.get("type") or inst:
                out.append(f"{path}/{nm}: give a model, a type or an instance - only one")
            elif not MODEL_KEY.match(str(model)):
                out.append(f"{path}/{nm}: model {model!r} must be an asset name like chair")
            elif str(model) not in (models or set()):
                out.append(f"{path}/{nm}: model {model!r} is not an approved 3D model of this game "
                           "(make it and approve it on the Assets tab first)")
        elif inst:
            pos = (node.get("props") or {}).get("position")
            three = isinstance(pos, (list, tuple)) and len(pos) == 3
            if node.get("type"):
                out.append(f"{path}/{nm}: give either a type or an instance, not both")
            if not FILE.match(str(inst)):
                out.append(f"{path}/{nm}: instance {inst!r} must be a scene file like coin.tscn")
            elif str(inst) not in scenes:
                out.append(f"{path}/{nm}: instance {inst!r} is not a scene of this game")
            elif str(inst) in (_seen or set()):
                out.append(f"{path}/{nm}: {inst} instancing itself (a loop) - Godot would never finish loading it")
        else:
            t = str(node.get("type") or "")
            three = t in NODES3D
            if t not in NODES:
                out.append(f"{path}/{nm}: node type {t!r} is not one Hoola writes"
                           + (" (an unknown type does not error in Godot, it hangs the load)" if t else ""))
        scr = node.get("script")
        if scr is not None:
            if not isinstance(scr, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}\.gd", scr):
                out.append(f"{path}/{nm}: script {scr!r} must be a .gd file name")
            elif scr not in scripts:
                out.append(f"{path}/{nm}: script {scr!r} is not a file of this game")
        sh = node.get("shape")
        if sh is not None:
            kinds = SHAPES3D if three else SHAPES
            if not isinstance(sh, dict) or str(sh.get("kind")) not in kinds:
                out.append(f"{path}/{nm}: shape kind must be one of {', '.join(sorted(kinds))}")
            elif three:
                try:
                    if "size" in sh: _vec3(sh["size"])
                except SceneError as e:
                    out.append(f"{path}/{nm}.shape: {e}")
        me = node.get("mesh")
        if me is not None:
            if str(node.get("type")) != "MeshInstance3D":
                out.append(f"{path}/{nm}: a mesh belongs on a MeshInstance3D")
            out.extend(_check_mesh(me, f"{path}/{nm}"))
        en = node.get("environment")
        if en is not None:
            if str(node.get("type")) != "WorldEnvironment":
                out.append(f"{path}/{nm}: an environment belongs on a WorldEnvironment")
            out.extend(_check_env(en, f"{path}/{nm}"))
        for k, v in (node.get("props") or {}).items():
            try:
                if _prop(str(k), v, three) is None:
                    out.append(f"{path}/{nm}: Hoola does not write the property '{k}' (it is dropped, not guessed)")
            except SceneError as e:
                out.append(f"{path}/{nm}.{k}: {e}")
        anims = node.get("animations")
        if anims is not None:
            if str(node.get("type")) != "AnimationPlayer":
                out.append(f"{path}/{nm}: animations belong on an AnimationPlayer")
            if not isinstance(anims, list) or not anims:
                out.append(f"{path}/{nm}: animations must be a non-empty list")
            else:
                count["anims"] += len(anims)
                if count["anims"] > MAX_ANIMS:
                    out.append(f"more than {MAX_ANIMS} animations in one scene")
                for an in anims[:MAX_ANIMS]:
                    out.extend(_check_anim(an, f"{path}/{nm}"))
        kids = node.get("children") or []
        if not isinstance(kids, list):
            out.append(f"{path}/{nm}: children must be a list")
            return
        kid_names: set[str] = set()
        for c in kids:
            walk(c, f"{path}/{nm}", kid_names)

    walk(root, "", set())
    return out[:30]


def _check_anim(an: Any, path: str) -> list[str]:
    out: list[str] = []
    if not isinstance(an, dict):
        return [f"{path}: an animation must be an object"]
    nm = str(an.get("name") or "")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", nm):
        out.append(f"{path}: animation name {nm!r} is not allowed")
    try:
        ln = float(an.get("length") or 1.0)
        if not (0.05 <= ln <= 120):
            out.append(f"{path}/{nm}: length must be 0.05 - 120 seconds")
    except (TypeError, ValueError):
        out.append(f"{path}/{nm}: length must be a number")
    tracks = an.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        out.append(f"{path}/{nm}: an animation needs at least one track")
        return out
    for tr in tracks[:20]:
        if not isinstance(tr, dict):
            out.append(f"{path}/{nm}: a track must be an object")
            continue
        p = str(tr.get("path") or "")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_/]{0,63}:[a-z_][a-z0-9_:]{0,31}", p):
            out.append(f"{path}/{nm}: track path {p!r} must look like Body:position or Body:modulate")
        keys = tr.get("keys")
        if not isinstance(keys, list) or not keys:
            out.append(f"{path}/{nm}: track {p} has no keys")
            continue
        if len(keys) > MAX_KEYS:
            out.append(f"{path}/{nm}: track {p} has {len(keys)} keys (max {MAX_KEYS})")
        last = -1.0
        for k in keys[:MAX_KEYS]:
            if not (isinstance(k, (list, tuple)) and len(k) == 2):
                out.append(f"{path}/{nm}: a key must be [time, value]")
                break
            try:
                t = float(k[0])
            except (TypeError, ValueError):
                out.append(f"{path}/{nm}: key time {k[0]!r} is not a number")
                break
            if t < last:
                out.append(f"{path}/{nm}: track {p} keys must go forward in time")
                break
            last = t
    return out


# ---------------------------------------------------------------- the generator
def _value_for(path: str, v: Any) -> str:
    """A track's key value, typed from the property the path ends in."""
    prop = path.rsplit(":", 1)[-1]
    if prop in COLORS:
        return _color(v)
    if isinstance(v, (list, tuple)) and len(v) == 3 and prop in VEC3 | VEC2:   # a 3D track: Vector3
        return _vec3(v)
    if prop in VEC2:
        return _vec2(v)
    if prop in BOOLS:
        return "true" if bool(v) else "false"
    if isinstance(v, (list, tuple)):
        return _vec3(v) if len(v) == 3 else _vec2(v)
    return _f(v)


def _anim_blocks(anims: list, prefix: str) -> tuple[list[str], dict[str, str]]:
    """Animation + AnimationLibrary sub-resources for one AnimationPlayer."""
    blocks: list[str] = []
    ids: dict[str, str] = {}
    for i, an in enumerate(anims):
        aid = f"{prefix}_anim_{i}"
        name = str(an["name"])
        lines = [f'[sub_resource type="Animation" id="{aid}"]', f'resource_name = "{name}"',
                 f"length = {_f(an.get('length') or 1.0)}"]
        if an.get("loop"):
            lines.append("loop_mode = 1")
        for ti, tr in enumerate(an["tracks"]):
            p = str(tr["path"])
            keys = list(tr["keys"])
            times = ", ".join(_f(k[0]) for k in keys)
            trans = ", ".join("1" for _ in keys)
            vals = ", ".join(_value_for(p, k[1]) for k in keys)
            lines += [f'tracks/{ti}/type = "value"', f"tracks/{ti}/imported = false",
                      f"tracks/{ti}/enabled = true", f'tracks/{ti}/path = NodePath("{p}")',
                      f"tracks/{ti}/interp = 1", f"tracks/{ti}/loop_wrap = true",
                      "tracks/%d/keys = {" % ti,
                      f'"times": PackedFloat32Array({times}),',
                      f'"transitions": PackedFloat32Array({trans}),',
                      '"update": 0,',
                      f'"values": [{vals}]', "}"]
        blocks.append("\n".join(lines))
        ids[name] = aid
    lib = f"{prefix}_lib"
    body = ",\n".join(f'"{n}": SubResource("{i}")' for n, i in ids.items())
    blocks.append(f'[sub_resource type="AnimationLibrary" id="{lib}"]\n_data = {{\n{body}\n}}')
    return blocks, {"__lib__": lib}


def build(spec: dict, scripts: set[str], scenes: set[str], models: set[str] | None = None) -> str:
    """spec -> the .tscn text. Call `check()` first: this assumes a checked spec and still refuses the hole."""
    bad = check(spec, scripts, scenes, models=models)
    if bad:
        raise SceneError("; ".join(bad[:4]))
    ext: dict[str, str] = {}                            # res path -> id
    kinds: dict[str, str] = {}                          # res path -> ext_resource type
    subs: list[str] = []
    nodes: list[str] = []

    def ext_id(path: str, kind: str) -> str:
        if path not in ext:
            stem = re.sub(r"[^a-z0-9]", "", path.split(".")[0].lower())[:12] or "r"
            ext[path] = f"{len(ext) + 1}_{stem}"
            kinds[path] = kind
        return ext[path]

    def emit(node: dict, parent: str | None) -> None:
        nm = node["name"]
        head = f'[node name="{nm}"'
        three = (str(node.get("type") or "") in NODES3D or node.get("model") is not None
                 or (node.get("instance") and isinstance((node.get("props") or {}).get("position"), (list, tuple))
                     and len((node.get("props") or {}).get("position")) == 3))
        if node.get("model") is not None:
            head += f' parent="{parent or "."}" instance=ExtResource("{ext_id("assets/" + str(node["model"]) + ".glb", "PackedScene")}")'
        elif node.get("instance"):
            head += f' parent="{parent or "."}" instance=ExtResource("{ext_id(str(node["instance"]), "PackedScene")}")'
        else:
            head += f' type="{node["type"]}"' + (f' parent="{parent}"' if parent is not None else "")
        lines = [head + "]"]
        if node.get("script"):
            lines.append(f'script = ExtResource("{ext_id(str(node["script"]), "Script")}")')
        if node.get("shape"):
            sid = f"shape_{len(subs)}"
            kind = (SHAPES3D if three else SHAPES)[str(node["shape"]["kind"])]
            subs.append(_shape_block(sid, kind, node["shape"]))
            lines.append(f'shape = SubResource("{sid}")')
        if node.get("mesh"):
            mid = f"mesh_{len(subs)}"
            subs.extend(_mesh_blocks(mid, node["mesh"]))
            lines.append(f'mesh = SubResource("{mid}")')
        if node.get("environment"):
            eid = f"env_{len(subs)}"
            subs.extend(_env_blocks(eid, node["environment"]))
            lines.append(f'environment = SubResource("{eid}")')
        for k, v in (node.get("props") or {}).items():
            got = _prop(str(k), v, three)
            if got is not None:
                lines.append(f"{k} = {got}")
        if node.get("animations"):
            blocks, meta = _anim_blocks(list(node["animations"]), f"{nm.lower()}{len(subs)}")
            subs.extend(blocks)
            lines.append('libraries = {\n"": SubResource("%s")\n}' % meta["__lib__"])
        nodes.append("\n".join(lines))
        here = "." if parent is None else (nm if parent == "." else f"{parent}/{nm}")
        for c in node.get("children") or []:
            emit(c, here)

    emit(dict(spec["root"]), None)
    ext_lines = [f'[ext_resource type="{kinds[p]}" path="res://{p}" id="{i}"]' for p, i in ext.items()]
    steps = len(ext_lines) + len(subs) + 1
    text = "\n".join([f"[gd_scene load_steps={steps} format=3]", ""] + ext_lines + [""] + subs + [""] + nodes) + "\n"
    if BANNED_TEXT.search(text):                        # defence in depth: the generator is the only writer
        raise SceneError("refusing to write a scene that carries script source or dynamic code")
    return text


def _shape_block(sid: str, kind: str, sh: dict) -> str:
    if kind == "BoxShape3D":
        return f'[sub_resource type="{kind}" id="{sid}"]\nsize = {_vec3(sh.get("size") or [1, 1, 1])}'
    if kind == "SphereShape3D":
        return f'[sub_resource type="{kind}" id="{sid}"]\nradius = {_f(sh.get("radius") or 0.5)}'
    if kind in ("CapsuleShape3D", "CylinderShape3D"):
        return (f'[sub_resource type="{kind}" id="{sid}"]\nradius = {_f(sh.get("radius") or 0.5)}\n'
                f"height = {_f(sh.get('height') or 2)}")
    if kind == "RectangleShape2D":
        return f'[sub_resource type="{kind}" id="{sid}"]\nsize = {_vec2(sh.get("size") or [32, 32])}'
    if kind == "CircleShape2D":
        return f'[sub_resource type="{kind}" id="{sid}"]\nradius = {_f(sh.get("radius") or 8)}'
    return (f'[sub_resource type="{kind}" id="{sid}"]\nradius = {_f(sh.get("radius") or 8)}\n'
            f"height = {_f(sh.get('height') or 32)}")


# ---------------------------------------------------------------- a whole game's scenes
def build_all(specs: list[dict], scripts: set[str], models: set[str] | None = None) -> tuple[dict[str, str], list[str]]:
    """(files, problems) for every scene of a game. Order-independent: instancing is resolved against ALL names."""
    if not isinstance(specs, list):
        return {}, ["scenes must be a list"]
    if len(specs) > MAX_SCENES:
        return {}, [f"{len(specs)} scenes (max {MAX_SCENES})"]
    names: dict[str, dict] = {}
    problems: list[str] = []
    for sp in specs:
        nm = str((sp or {}).get("name") or "")
        f = f"{nm.lower()}.tscn"
        if f in names:
            problems.append(f"two scenes both called {nm}")
            continue
        if f == "main.tscn":
            problems.append("main.tscn is Hoola's own root scene - name the scene something else")
            continue
        names[f] = sp
    known = set(names)
    out: dict[str, str] = {}
    total_nodes = 0
    for f, sp in names.items():
        bad = check(sp, scripts, known, _seen={f}, models=models)
        if bad:
            problems += [f"{f}: {b}" for b in bad[:4]]
            continue
        try:
            out[f] = build(sp, scripts, known, models=models)
        except SceneError as e:
            problems.append(f"{f}: {e}")
            continue
        total_nodes += out[f].count("[node name=")
    if total_nodes > MAX_TOTAL_NODES:
        problems.append(f"{total_nodes} nodes across all scenes (max {MAX_TOTAL_NODES})")
    size = sum(len(v) for v in out.values())
    if size > MAX_BYTES:
        problems.append(f"the scenes are {size // 1024} KB (max {MAX_BYTES // 1024} KB)")
    return ({} if problems else out), problems[:20]


# ---------------------------------------------------------------- proved in the real engine
# Measured in Godot 4.7.2: an unknown node type does NOT make instantiate() fail - the engine logs "Cannot get class"
# and "A placeholder will be created instead", and hands back a scene with a plain Node in place of the real one. So
# instantiate() succeeding is NOT proof a scene is good, and a placeholder is a silently broken game. These are the log
# signatures that mean the load went wrong even when it "worked".
TROUBLE = re.compile(r"Cannot get class|placeholder will be created|Script inherits from native type|"
                     r"Failed loading resource|Parse Error|Condition \"[^\"]*\" is true|"
                     r"Attempt to open script .* failed|Can't open file|Invalid type in function", re.I)

PROBE = '''extends Node
# Hoola's scene check (not part of a game): loads every generated scene, counts what came out, and quits.
func _ready() -> void:
	var names: PackedStringArray = __SCENES__
	var out: Array = []
	for n in names:
		var path := "res://" + n
		var ok := ResourceLoader.exists(path)
		var nodes := 0
		var anims: Array = []
		var meshes := 0
		var lights := 0
		var cameras := 0
		var three := false
		if ok:
			var ps = load(path)
			if ps == null:
				ok = false
			else:
				var inst = ps.instantiate()
				if inst == null:
					ok = false
				else:
					nodes = _count(inst)
					three = inst is Node3D
					for c in _all(inst):
						if c is AnimationPlayer:
							for a in c.get_animation_list():
								anims.append(a)
						if c is MeshInstance3D and c.mesh != null:
							meshes += 1
						if c is Light3D:
							lights += 1
						if c is Camera3D:
							cameras += 1
					inst.free()
		out.append({"scene": n, "loaded": ok, "nodes": nodes, "animations": anims, "three": three,
			"meshes": meshes, "lights": lights, "cameras": cameras})
	print("HOOLA_SCN " + JSON.stringify(out))
	get_tree().quit()

func _count(n: Node) -> int:
	var k := 1
	for c in n.get_children():
		k += _count(c)
	return k

func _all(n: Node) -> Array:
	var got: Array = [n]
	for c in n.get_children():
		got += _all(c)
	return got
'''


def verify(files: dict[str, str], scripts: dict[str, str], job: Path, title: str = "Scenes",
           orientation: str = "portrait", models: dict[str, Path] | None = None) -> dict[str, Any]:
    """Load every generated scene in the REAL engine. A bad scene HANGS the load rather than erroring, so the run
    carries a quit timer and 'never reached the end' is itself the failure."""
    from . import engine, template
    import json
    import shutil
    if not engine.find():
        return {"verdict": "NOT ASSESSED", "why": "Godot is not installed on this server (deploy/setup_godot.py)",
                "scenes": []}
    shutil.rmtree(job, ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    names = sorted(files)
    probe = PROBE.replace("__SCENES__", "PackedStringArray([" + ", ".join(f'"{n}"' for n in names) + "])")
    base = dict(scripts)
    base["main.gd"] = "extends Node\n"                  # the check's own root; the game's main.gd is not run here
    out = template.files(title, orientation, base)
    out["hoola_scenecheck.gd"] = probe
    out["project.godot"] = out["project.godot"].replace(
        'HoolaProbe="*res://hoola_probe.gd"', 'HoolaProbe="*res://hoola_probe.gd"\nHoolaSceneCheck="*res://hoola_scenecheck.gd"')
    out.update(files)
    for name, txt in out.items():
        p = job / "proj" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    # v0.79x a 3D scene may place her APPROVED models (res://assets/<key>.glb): copy them in and let the engine import
    # them first, exactly like a real build does - a model that does not import is then a load failure, never a pass
    if models:
        (job / "proj" / "assets").mkdir(parents=True, exist_ok=True)
        for key, src in models.items():
            if MODEL_KEY.match(str(key)) and Path(src).is_file():
                shutil.copyfile(src, job / "proj" / "assets" / f"{key}.glb")
        engine._run(job, ["--path", "proj", "--import"], "sceneimport.log", 180)
    code, logtxt, to = engine._run(job, ["--path", "proj", "--quit-after", "600"], "scenecheck.log", 180)
    m = re.search(r"HOOLA_SCN (\[.*\])", logtxt or "")
    errs = engine.errors_in(logtxt or "")
    if not m:
        return {"verdict": "FAIL", "scenes": [],
                "why": ("the engine never finished loading the scenes - a scene with an unknown node type hangs "
                        "instead of failing" if to else "the check did not report"),
                "errors": errs[:6], "log": (logtxt or "")[-400:]}
    rows = json.loads(m.group(1))
    bad = [r for r in rows if not r.get("loaded")]
    # instantiate() is not the whole test: the engine substitutes a placeholder for an unknown node type and reports
    # success, so the log's own trouble lines decide too.
    trouble = sorted({t.strip()[:200] for t in (logtxt or "").splitlines() if TROUBLE.search(t)})[:6]
    ok = not bad and not errs and not trouble
    return {"verdict": "PASS" if ok else "FAIL", "scenes": rows, "errors": errs[:6], "trouble": trouble,
            "loaded": len(rows) - len(bad), "of": len(rows),
            "why": ("; ".join(f"{r['scene']} did not load" for r in bad[:4])
                    or (trouble[0] if trouble else "")
                    or ("; ".join(errs[:2]) if errs else "every scene loaded in the real engine"))}


# ================================================================ a game's scenes: propose -> check -> prove -> her OK
class GameScene(Base):
    __tablename__ = "game_scenes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(40), default="")        # Level1 -> level1.tscn
    words: Mapped[str] = mapped_column(Text, default="")             # what she asked for
    spec: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | approved | rejected | failed
    nodes: Mapped[int] = mapped_column(Integer, default=0)           # as the ENGINE counted them, instances expanded
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameScene.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _scripts_of(tenant: str, gid: str) -> dict[str, str]:
    g = G._get(tenant, gid)
    return {k: v for k, v in G._current_files(g).items() if k.endswith(".gd")}


def _models_of(tenant: str, gid: str) -> dict[str, Path]:
    """Her APPROVED 3D models for this game, {asset key: the .glb on disk} - the same files a build copies to
    res://assets/<key>.glb. Empty when the game has no long project or no approved model."""
    try:
        from . import assets as A
        got = A.for_game(tenant, gid)
    except Exception:                                   # noqa: BLE001 - no models is never a reason to fail a scene
        return {}
    if not got:
        return {}
    out: dict[str, Path] = {}
    for rel, src in (got[1] or {}).items():
        m = re.fullmatch(r"assets/([a-z][a-z0-9_]{0,39})\.glb", str(rel))
        if m:
            out[m.group(1)] = Path(src)
    return out


def _rows(tenant: str, sid: str) -> list[GameScene]:
    ensure_table()
    with session() as s:
        got = s.scalars(select(GameScene).where(GameScene.tenant_id == tenant, GameScene.studio_id == sid)
                        .order_by(GameScene.created_at)).all()
        for r in got:
            s.expunge(r)
    return got


def view(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    rows = _rows(tenant, st.id)
    return {"studio_id": st.id, "game_id": st.game_id,
            "scenes": [{"id": r.id, "name": r.name, "file": f"{r.name.lower()}.tscn", "status": r.status,
                        "nodes": r.nodes, "words": r.words, "report": r.report or {},
                        "spec_nodes": str(r.spec).count("'name'"), "at": r.created_at.isoformat() if r.created_at else ""}
                       for r in rows],
            "in_the_game": [f"{r.name.lower()}.tscn" for r in rows if r.status == "approved"],
            "limits": {"scenes": MAX_SCENES, "nodes_per_scene": MAX_NODES, "nodes_total": MAX_TOTAL_NODES},
            "node_types": sorted(NODES),
            "how": ("The model never writes a .tscn - it writes a spec, Hoola checks it and generates the scene, then "
                    "loads it in the real engine before you ever see it. A scene may not carry script source: an "
                    "embedded script in a .tscn RUNS and would escape the code guard."),
            "three_d": "3D scenes: meshes with real materials, lights and shadows, a camera, a sky / fog / glow, 3D physics and your approved 3D models from the Assets tab.",
            "not_built": "TileMaps / GridMaps (they need a TileSet or MeshLibrary of art) and shaders. The check proves a 3D scene loads and counts what is in it; it cannot see how it looks."}


def propose(tenant: str, ref: str, words: str, name: str = "") -> dict[str, Any]:
    """Her words -> a scene spec from the model -> checked -> generated -> PROVED in the real engine -> a draft."""
    from . import ai
    ensure_table()
    st = _studio(tenant, ref)
    why = G.problem(words)
    if why:
        raise SceneError(why)
    scripts = _scripts_of(tenant, st.game_id)
    if not scripts:
        raise SceneError("Pehle game ka ek chalne wala version chahiye (scenes uske scripts se judte hain).")
    rows = _rows(tenant, st.id)
    if len(rows) >= MAX_SCENES:
        raise SceneError(f"{MAX_SCENES} scenes tak.")
    others = {f"{r.name.lower()}.tscn" for r in rows if r.status == "approved"}
    models = _models_of(tenant, st.game_id)
    spec = ai.scene_spec(G._get(tenant, st.game_id).design or "", sorted(scripts), sorted(others), words, name,
                         models=sorted(models))
    nm = str(spec.get("name") or name or "Scene1")
    spec["name"] = nm
    file = f"{nm.lower()}.tscn"
    bad = check(spec, set(scripts), others | {file}, _seen={file}, models=set(models))
    if bad:
        raise SceneError("Scene theek nahi bana: " + "; ".join(bad[:3]))
    built, probs = build_all([spec], set(scripts), models=set(models))
    if probs:
        raise SceneError("; ".join(probs[:3]))
    # every APPROVED scene goes in too, so an instance of one is proved as it will really load
    approved = _approved_files(tenant, st.id, set(scripts), set(models))
    rep = verify({**approved, **built}, scripts, G._pdir(tenant, st.game_id) / "scenecheck", models=models)
    mine = next((r for r in rep.get("scenes", []) if r.get("scene") == file), {})
    with session() as s:
        row = GameScene(tenant_id=tenant, studio_id=st.id, name=nm, words=str(words or "")[:500], spec=spec,
                        status="draft" if rep["verdict"] == "PASS" else "failed",
                        nodes=int(mine.get("nodes") or 0), report=rep)
        s.add(row)
        s.flush()
        s.expunge(row)
    return {"id": row.id, "name": nm, "file": file, "status": row.status, "nodes": row.nodes,
            "verdict": rep["verdict"], "why": rep["why"],
            "animations": mine.get("animations") or [],
            "three_d": bool(mine.get("three")), "meshes": int(mine.get("meshes") or 0),
            "lights": int(mine.get("lights") or 0), "cameras": int(mine.get("cameras") or 0),
            "say": ("Scene ban gaya aur asli engine mein khul bhi gaya - dekhiye aur 'haan' boliye."
                    if row.status == "draft" else "Scene asli engine mein nahi khula: " + rep["why"])}


def _approved_files(tenant: str, sid: str, scripts: set[str], models: set[str] | None = None) -> dict[str, str]:
    specs = [r.spec for r in _rows(tenant, sid) if r.status == "approved" and r.spec]
    out, _ = build_all(specs, scripts, models=models)
    return out


def approve(tenant: str, ref: str, sid_or_name: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    ensure_table()
    with session() as s:
        row = s.scalars(select(GameScene).where(GameScene.studio_id == st.id,
                                                (GameScene.id == sid_or_name) | (GameScene.name == sid_or_name))).first()
        if row is None:
            raise SceneError("Woh scene nahi mila.")
        if row.status == "failed":
            raise SceneError("Yeh scene asli engine mein khula hi nahi - pehle dobara banwaiye.")
        row.status = "approved"
        row.updated_at = now()
        nm = row.name
    return {"name": nm, "status": "approved",
            "say": f"{nm} game mein jayega - agli build mein dikhega."}


def reject(tenant: str, ref: str, sid_or_name: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    ensure_table()
    with session() as s:
        row = s.scalars(select(GameScene).where(GameScene.studio_id == st.id,
                                                (GameScene.id == sid_or_name) | (GameScene.name == sid_or_name))).first()
        if row is None:
            raise SceneError("Woh scene nahi mila.")
        row.status = "rejected"
        row.updated_at = now()
        nm = row.name
    return {"name": nm, "status": "rejected", "say": f"{nm} hata diya."}


def for_game(tenant: str, game_id: str) -> dict[str, str]:
    """The approved scenes of this game's Studio project, as files for the build. Hoola's own - the model never
    wrote them. Empty for a game with no Studio project or no approved scene, so an old game builds exactly as before."""
    from . import studio as S
    ensure_table()
    try:
        with session() as s:
            st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant,
                                                      S.GameStudio.game_id == game_id)).first()
            if st is None:
                return {}
            sid = st.id
        scripts = set(_scripts_of(tenant, game_id))
        return _approved_files(tenant, sid, scripts, set(_models_of(tenant, game_id)))
    except Exception:                                   # noqa: BLE001 - a scene problem must never stop a build
        log.exception("scenes for game %s", game_id)
        return {}
