"""Runs INSIDE Blender (the official binary with `-b --python runner.py -- job.json`, or Python with the official `bpy`
module: `python -I runner.py job.json`). Standalone on purpose: it imports nothing from Hoola.

1. empty scene, scripts never auto-run
2. the (already guard-checked) script runs with cut-down builtins and an import gate, with Hoola's H helpers
3. Hoola's own code then: facts about every object (size, triangles, materials, holes for 3D print), a camera and
   lights when the script made none, renders of the asked views (+ turntable frames), exports, the .blend
4. result.json for the server (errors with the script's own line numbers)

Only this file reads her inputs (photos / fonts listed in job.json) and writes into the job folder."""
import builtins
import json
import math
import os
import sys
import time
import traceback

import bpy  # noqa: E402

try:
    import bmesh  # noqa: E402
    import mathutils  # noqa: E402
    from mathutils import Vector  # noqa: E402
except Exception:  # pragma: no cover
    bmesh = mathutils = Vector = None

ALLOWED = {"bpy", "bmesh", "mathutils", "math", "random", "colorsys", "itertools", "functools", "collections",
           "statistics", "mathutils.noise", "mathutils.geometry", "mathutils.bvhtree", "mathutils.kdtree", "bmesh.ops",
           "bmesh.types", "bmesh.utils", "bmesh.geometry"}
SAFE_BUILTINS = ["abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset", "int",
                 "isinstance", "issubclass", "len", "list", "map", "max", "min", "next", "iter", "pow", "print", "range",
                 "repr", "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple", "zip", "chr", "ord", "hash",
                 "format", "callable", "id", "bytes", "complex", "property", "True", "False", "None", "Exception",
                 "ValueError", "TypeError", "KeyError", "IndexError", "RuntimeError", "ZeroDivisionError",
                 "AttributeError", "StopIteration", "ArithmeticError", "LookupError", "NotImplementedError",
                 "__build_class__"]


def _args():
    a = sys.argv
    if "--" in a:
        return a[a.index("--") + 1:]
    return a[1:]


JOB = json.load(open(_args()[0], encoding="utf-8"))
OUT = JOB["out_dir"]
RESULT = {"ok": False, "errors": [], "warnings": [], "renders": [], "frames": [], "exports": {}, "stats": {},
          "blender": getattr(bpy.app, "version_string", "")}


def _save_result():
    with open(os.path.join(OUT, "result.json"), "w", encoding="utf-8") as f:
        json.dump(RESULT, f)


def _gate(name, globals_=None, locals_=None, fromlist=(), level=0):
    if level or name not in ALLOWED:
        raise ImportError(f"import {name} allowed nahi")
    return __import__(name, globals_, locals_, fromlist, level)


def _safe_getattr(o, name, *default):
    if not isinstance(name, str) or name.startswith("_"):
        raise AttributeError(name)
    return getattr(o, name, *default)


def _safe_setattr(o, name, value):
    if not isinstance(name, str) or name.startswith("_") or name in ("filepath", "filepath_raw", "expression"):
        raise AttributeError(name)
    setattr(o, name, value)


def _safe_hasattr(o, name):
    return isinstance(name, str) and not name.startswith("_") and hasattr(o, name)


# ---------------------------------------------------------------- H helpers (trusted code, offered to the script)
def _rgba(c, alpha=1.0):
    if isinstance(c, str):
        h = c.strip().lstrip("#")
        if len(h) == 3:
            h = "".join(x * 2 for x in h)
        try:
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        except ValueError:
            r, g, b = 0.8, 0.8, 0.8

        def lin(v):  # sRGB hex -> linear, as Blender expects in node colour sockets
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        return (lin(r), lin(g), lin(b), alpha)
    c = tuple(c)
    return c if len(c) == 4 else (c[0], c[1], c[2], alpha)


def _sock(node, *names):
    for n in names:
        if n in node.inputs:
            return node.inputs[n]
    return None


class _H:
    """Small, safe building blocks. Lengths in metres."""

    def mat(self, name, color="#cccccc", metal=0.0, rough=0.5, emit=None, emit_strength=0.0, alpha=1.0,
            transmission=0.0, coat=0.0):
        m = bpy.data.materials.new(str(name)[:60])
        m.use_nodes = True
        p = m.node_tree.nodes.get("Principled BSDF")
        if p is not None:
            for keys, val in ((("Base Color",), _rgba(color)), (("Metallic",), float(metal)),
                              (("Roughness",), float(rough)), (("Alpha",), float(alpha)),
                              (("Transmission Weight", "Transmission"), float(transmission)),
                              (("Coat Weight", "Clearcoat"), float(coat))):
                s = _sock(p, *keys)
                if s is not None:
                    s.default_value = val
            if emit is not None:
                s = _sock(p, "Emission Color", "Emission")
                if s is not None:
                    s.default_value = _rgba(emit)
                s = _sock(p, "Emission Strength")
                if s is not None:
                    s.default_value = float(emit_strength or 1.0)
        m.diffuse_color = _rgba(color, alpha)
        return m

    def give(self, obj, mat):
        if obj is not None and mat is not None and getattr(obj, "data", None) is not None \
                and hasattr(obj.data, "materials"):
            obj.data.materials.clear()
            obj.data.materials.append(mat)
        return obj

    def _place(self, name, loc, rot, mat):
        o = bpy.context.active_object
        o.name = str(name)[:60]
        if loc is not None:
            o.location = loc
        if rot is not None:
            o.rotation_euler = [math.radians(a) for a in rot]
        if mat is not None:
            self.give(o, mat)
        return o

    def box(self, name, size=(1, 1, 1), loc=(0, 0, 0), rot=None, mat=None, bevel=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = self._place(name, loc, rot, mat)
        o.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if bevel:
            self.bevel(o, bevel)
        return o

    def cyl(self, name, r=0.5, depth=1.0, loc=(0, 0, 0), rot=None, mat=None, verts=64, smooth=True):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=int(verts))
        o = self._place(name, loc, rot, mat)
        if smooth:
            self.smooth(o)
        return o

    def cone(self, name, r1=0.5, r2=0.0, depth=1.0, loc=(0, 0, 0), rot=None, mat=None, verts=64):
        bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, vertices=int(verts))
        return self.smooth(self._place(name, loc, rot, mat))

    def sphere(self, name, r=0.5, loc=(0, 0, 0), mat=None, smooth=True, segments=48):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=int(segments), ring_count=max(8, int(segments) // 2))
        o = self._place(name, loc, None, mat)
        if smooth:
            self.smooth(o)
        return o

    def torus(self, name, major=0.5, minor=0.1, loc=(0, 0, 0), rot=None, mat=None):
        bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor)
        return self.smooth(self._place(name, loc, rot, mat))

    def plane(self, name, size=1.0, loc=(0, 0, 0), rot=None, mat=None):
        bpy.ops.mesh.primitive_plane_add(size=size)
        return self._place(name, loc, rot, mat)

    def text(self, name, body, size=0.3, loc=(0, 0, 0), rot=(90, 0, 0), extrude=None, mat=None, font="", align="CENTER"):
        bpy.ops.object.text_add()
        o = self._place(name, loc, rot, mat)
        o.data.body = str(body)[:200]
        o.data.size = float(size)
        o.data.extrude = float(size) * 0.08 if extrude is None else float(extrude)
        o.data.align_x = align if align in ("LEFT", "CENTER", "RIGHT") else "CENTER"
        f = self._font(font or ("devanagari" if any("ऀ" <= ch <= "ॿ" for ch in str(body)) else ""))
        if f is not None:
            o.data.font = f
        return o

    def _font(self, key):
        path = (JOB.get("fonts") or {}).get(key or "")
        if not path or not os.path.isfile(path):
            return None
        try:
            return bpy.data.fonts.load(path, check_existing=True)
        except Exception:
            return None

    def image(self, name):
        """Her photo (one of the names given) as a Blender image, for textures."""
        path = (JOB.get("inputs") or {}).get(str(name))
        if not path or not os.path.isfile(path):
            raise ValueError(f"photo '{name}' nahi mili; naam ye hain: {', '.join(JOB.get('inputs') or {}) or 'koi nahi'}")
        return bpy.data.images.load(path, check_existing=True)

    def image_mat(self, name, image_name, rough=0.5):
        img = self.image(image_name)
        m = bpy.data.materials.new(str(name)[:60])
        m.use_nodes = True
        nt = m.node_tree
        p = nt.nodes.get("Principled BSDF")
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        if p is not None:
            nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
            s = _sock(p, "Roughness")
            if s is not None:
                s.default_value = rough
        return m

    def image_plane(self, name, image_name, width=1.0, loc=(0, 0, 0), rot=(90, 0, 0)):
        img = self.image(image_name)
        w, h = img.size[0] or 1, img.size[1] or 1
        bpy.ops.mesh.primitive_plane_add(size=1)
        o = self._place(name, loc, rot, self.image_mat(str(name) + " photo", image_name))
        o.scale = (width, width * h / w, 1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return o

    def smooth(self, obj, auto=True):
        try:
            for p in obj.data.polygons:
                p.use_smooth = True
        except Exception:
            pass
        return obj

    def bevel(self, obj, width=0.02, segments=3):
        m = obj.modifiers.new("Bevel", "BEVEL")
        m.width = float(width)
        m.segments = int(segments)
        m.limit_method = "ANGLE"
        return obj

    def array(self, obj, count=3, offset=(1.1, 0, 0)):
        m = obj.modifiers.new("Array", "ARRAY")
        m.count = int(count)
        m.relative_offset_displace = offset
        return obj

    def boolean(self, obj, cutter, op="DIFFERENCE", apply=True):
        m = obj.modifiers.new("Bool", "BOOLEAN")
        m.object = cutter
        m.operation = op
        if apply:
            self.apply(obj)
            cutter.hide_render = True
            cutter.hide_viewport = True
        return obj

    def apply(self, obj):
        for m in list(obj.modifiers):
            try:
                with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj],
                                               selected_editable_objects=[obj]):
                    bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:  # keep going: an unapplied modifier still renders
                RESULT["warnings"].append(f"modifier {m.name} on {obj.name} not applied: {e}")
        return obj

    def parent(self, child, parent):
        child.parent = parent
        return child

    def floor(self, size=20.0, color="#f2f2f2", z=0.0):
        return self.plane("Hoola floor", size=size, loc=(0, 0, z), mat=self.mat("Floor", color, rough=0.8))

    def world(self, color="#ffffff", strength=1.0):
        w = bpy.context.scene.world or bpy.data.worlds.new("World")
        bpy.context.scene.world = w
        w.use_nodes = True
        bg = w.node_tree.nodes.get("Background")
        if bg is not None:
            bg.inputs[0].default_value = _rgba(color)
            bg.inputs[1].default_value = float(strength)
        return w

    def hex(self, color, alpha=1.0):
        return _rgba(color, alpha)

    def radians(self, deg):
        return math.radians(deg)


H = _H()


# ---------------------------------------------------------------- after the script: facts, camera, lights
def _mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type in ("MESH", "CURVE", "FONT", "SURFACE", "META")
            and not o.hide_render]


def _bbox():
    lo, hi = [1e18] * 3, [-1e18] * 3
    found = False
    dg = bpy.context.evaluated_depsgraph_get()
    for o in _mesh_objects():
        if o.name == "Hoola floor" or o.name.startswith("Hoola backdrop"):
            continue
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
            found = True
    if not found:
        return Vector((-1, -1, 0)), Vector((1, 1, 1))
    return Vector(lo), Vector(hi)


def _stats(check_print):
    dg = bpy.context.evaluated_depsgraph_get()
    objs, tris_total = [], 0
    for o in bpy.context.scene.objects:
        item = {"name": o.name[:60], "type": o.type}
        if o.type in ("MESH", "CURVE", "FONT", "SURFACE", "META") and not o.hide_render:
            ev = o.evaluated_get(dg)
            try:
                me = ev.to_mesh()
                tris = sum(max(0, len(p.vertices) - 2) for p in me.polygons)
                item["tris"] = tris
                tris_total += tris
                item["mats"] = [m.name for m in getattr(o.data, "materials", []) if m][:6]
                item["size_m"] = [round(v, 3) for v in ev.dimensions]
                if check_print and o.type == "MESH" and o.name != "Hoola floor":
                    bm = bmesh.new()
                    bm.from_mesh(me)
                    nm = sum(1 for e in bm.edges if not e.is_manifold)
                    bm.free()
                    item["open_edges"] = nm
                ev.to_mesh_clear()
            except Exception:
                pass
        objs.append(item)
    lo, hi = _bbox()
    size = [round(hi[i] - lo[i], 3) for i in range(3)]
    return {"objects": objs[:80], "count": len(objs), "tris": tris_total, "size_m": size,
            "materials": len(bpy.data.materials)}


def _ensure_light(lo, hi):
    if any(o.type == "LIGHT" for o in bpy.context.scene.objects):
        return False
    c = (lo + hi) / 2
    r = max((hi - lo).length / 2, 0.3)
    for name, off, energy, size in (("Hoola key", (1.2, -1.4, 1.6), 900, 2.5), ("Hoola fill", (-1.6, -0.8, 0.8), 300, 3.5),
                                    ("Hoola rim", (0.2, 1.8, 1.4), 500, 2.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy * r * r
        ld.size = size * r
        lo_ = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(lo_)
        lo_.location = c + Vector(off) * r * 2.2
        lo_.rotation_euler = (c - lo_.location).to_track_quat("-Z", "Y").to_euler()
    if bpy.context.scene.world is None:
        H.world(JOB.get("render", {}).get("background", "#f4f4f6"), 0.6)
    return True


VIEWS = {"front": (0, -1, 0.15), "three_quarter": (0.75, -1, 0.55), "side": (1, 0, 0.15), "back": (0, 1, 0.2),
         "top": (0.0001, -0.0001, 1), "low": (0.6, -1, 0.05)}


def _place_camera(cam, lo, hi, direction):
    c = (lo + hi) / 2
    r = max((hi - lo).length / 2, 0.05)
    d = Vector(direction).normalized()
    fov = cam.data.angle
    dist = r / math.sin(min(fov, 1.2) / 2) * 1.12
    cam.location = c + d * dist
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = max(1000.0, dist * 10)
    cam.data.clip_start = max(0.001, dist / 1000)


def _camera(lo, hi):
    sc = bpy.context.scene
    if sc.camera is not None:
        return sc.camera, False
    cd = bpy.data.cameras.new("Hoola camera")
    cd.lens = 50
    cam = bpy.data.objects.new("Hoola camera", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam, True


def _setup_render(rj):
    sc = bpy.context.scene
    try:
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = int(rj.get("samples", 32))
        sc.cycles.use_denoising = True
        try:
            sc.cycles.denoiser = "OPENIMAGEDENOISE"
        except Exception:
            pass
        sc.cycles.max_bounces = 6
        sc.render.threads_mode = "FIXED"
        sc.render.threads = max(1, int(rj.get("threads", 2)))
    except Exception as e:
        RESULT["warnings"].append(f"Cycles nahi mila, Workbench: {e}")
        sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = int(rj.get("width", 1024))
    sc.render.resolution_y = int(rj.get("height", 1024))
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = bool(rj.get("transparent"))
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        pass


def _render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _export(fmt, base):
    p = os.path.join(OUT, base + "." + fmt)
    hidden = [o for o in bpy.context.scene.objects if o.name.startswith("Hoola ")]
    for o in bpy.context.scene.objects:
        o.select_set(o not in hidden and o.type in ("MESH", "CURVE", "FONT", "SURFACE", "META", "EMPTY", "ARMATURE"))
    if fmt == "glb":
        bpy.ops.export_scene.gltf(filepath=p, export_format="GLB", use_selection=True, export_apply=True)
    elif fmt == "stl":
        bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True, apply_modifiers=True)
    elif fmt == "obj":
        bpy.ops.wm.obj_export(filepath=p, export_selected_objects=True, apply_modifiers=True, export_materials=False)
    elif fmt == "fbx":
        bpy.ops.export_scene.fbx(filepath=p, use_selection=True)
    elif fmt == "usdz":
        bpy.ops.wm.usd_export(filepath=p, selected_objects_only=True)
    elif fmt == "blend":
        bpy.ops.wm.save_as_mainfile(filepath=p, compress=True, copy=True)
    else:
        raise ValueError(fmt)
    return p


def main():
    t0 = time.time()
    try:
        bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    except Exception:
        pass
    bpy.ops.wm.read_factory_settings(use_empty=True)
    code = open(JOB["script"], encoding="utf-8").read()
    safe = {k: getattr(builtins, k) for k in SAFE_BUILTINS if hasattr(builtins, k)}
    safe.update({"__import__": _gate, "getattr": _safe_getattr, "setattr": _safe_setattr, "hasattr": _safe_hasattr})
    import random as _random
    _random.seed(int(JOB.get("seed", 7)))
    g = {"__builtins__": safe, "__name__": "hoola_scene", "bpy": bpy, "bmesh": bmesh, "mathutils": mathutils,
         "Vector": Vector, "math": math, "random": _random, "H": H}
    try:
        exec(compile(code, "hoola_scene.py", "exec"), g)
    except BaseException as e:  # the script's own error: say the line, not ours
        tb = traceback.extract_tb(e.__traceback__)
        lines = [f"line {fr.lineno}: {fr.line}" for fr in tb if fr.filename == "hoola_scene.py"]
        RESULT["errors"].append(f"{type(e).__name__}: {e}" + (f" ({lines[-1]})" if lines else ""))
        RESULT["seconds"] = round(time.time() - t0, 1)
        _save_result()
        return
    RESULT["script_s"] = round(time.time() - t0, 1)
    rj = JOB.get("render") or {}
    bpy.context.view_layer.update()
    lo, hi = _bbox()
    RESULT["stats"] = _stats(bool(JOB.get("print")))
    if RESULT["stats"]["tris"] > int(JOB.get("max_tris", 3_000_000)):
        RESULT["errors"].append(f"model bahut bhaari hai ({RESULT['stats']['tris']} triangles): kam detail karo")
        _save_result()
        return
    RESULT["auto_lights"] = _ensure_light(lo, hi)
    cam, auto_cam = _camera(lo, hi)
    RESULT["auto_camera"] = auto_cam
    _setup_render(rj)
    views = [v for v in (rj.get("views") or ["three_quarter"]) if v in VIEWS][:4] or ["three_quarter"]
    if rj.get("render", True):
        for v in views:
            if auto_cam or len(views) > 1:
                _place_camera(cam, lo, hi, VIEWS[v])
            p = os.path.join(OUT, f"view_{v}.png")
            _render(p)
            RESULT["renders"].append({"view": v, "file": os.path.basename(p)})
        n = int(rj.get("turntable", 0) or 0)
        if n:
            sc = bpy.context.scene
            sc.cycles.samples = max(4, int(rj.get("samples", 32)) // 3) if sc.render.engine == "CYCLES" else 0
            sc.render.resolution_x = sc.render.resolution_y = min(720, int(rj.get("width", 1024)))
            base = VIEWS["three_quarter"]
            for i in range(n):
                a = 2 * math.pi * i / n
                d = (base[0] * math.cos(a) - base[1] * math.sin(a), base[0] * math.sin(a) + base[1] * math.cos(a), base[2])
                _place_camera(cam, lo, hi, d)
                p = os.path.join(OUT, f"turn_{i:03d}.png")
                _render(p)
                RESULT["frames"].append(os.path.basename(p))
    for fmt in JOB.get("exports") or []:
        try:
            RESULT["exports"][fmt] = os.path.basename(_export(fmt, JOB.get("base", "hoola_3d")))
        except Exception as e:
            RESULT["warnings"].append(f"{fmt} export nahi hua: {e}")
    RESULT["ok"] = True
    RESULT["seconds"] = round(time.time() - t0, 1)
    _save_result()


try:
    main()
except BaseException as e:  # our own failure: still leave a result
    RESULT["errors"].append(f"runner: {type(e).__name__}: {e}")
    _save_result()
