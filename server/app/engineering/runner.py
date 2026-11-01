"""Runs ONE CadQuery script in the sandbox (child process; started by sandbox.py with no network and no secrets).

python runner.py job.json -> writes part.step, part.stl, mesh.json and result.json in the job folder.
The script gets `cq` and `math` only, cut-down builtins and an import gate; it builds `result` and the runner checks and
exports it. Never prints anything Hoola trusts: the parent reads result.json only."""
import builtins
import json
import math
import sys
import time
import traceback
from pathlib import Path

SAFE_BUILTINS = {n: getattr(builtins, n) for n in (
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset", "int", "isinstance",
    "len", "list", "map", "max", "min", "pow", "range", "reversed", "round", "set", "slice", "sorted", "str", "sum",
    "tuple", "zip", "print", "ValueError", "TypeError", "ZeroDivisionError", "Exception", "True", "False", "None")
    if hasattr(builtins, n)}
ALLOWED = {"cadquery", "math"}
HLR_VIEWS = {"front": (0, -1, 0), "top": (0, 0, 1), "right": (1, 0, 0), "iso": (-1.75, -1.1, 1.6)}   # v0.362


def _gate(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in ALLOWED:
        raise ImportError(f"import {name} allowed nahi (sirf cadquery aur math)")
    return builtins.__import__(name, globals, locals, fromlist, level)


class _Locked(Exception):
    pass


def _deny(*_a, **_k):
    raise _Locked("network / programs / files band hain is box mein")


_LOCK_TARGETS = (("socket", ("socket", "create_connection", "create_server", "socketpair", "fromfd", "getaddrinfo")),
                 ("os", ("system", "popen", "fork", "forkpty", "kill", "killpg", "execv", "execve", "execl", "execle",
                         "execlp", "execlpe", "execvp", "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv",
                         "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp", "remove", "unlink", "rmdir",
                         "removedirs", "rename", "replace", "chmod", "chown", "putenv", "setuid", "setgid")),
                 ("subprocess", ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput")),
                 ("shutil", ("rmtree", "move", "copy", "copy2", "copyfile", "copytree")))


def _lockdown() -> list:
    """v0.361 the fourth wall, for servers where `unshare -rn` is not allowed: while HER script runs, every function
    that reaches the network, starts a program or deletes / moves files raises, in this process. Undone after the
    script, before the runner's own export. Returns what to put back."""
    import importlib
    saved = []
    for mod_name, names in _LOCK_TARGETS:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        for n in names:
            if hasattr(mod, n):
                saved.append((mod, n, getattr(mod, n)))
                setattr(mod, n, _deny)
    return saved


def _unlock(saved: list) -> None:
    for mod, n, v in saved:
        setattr(mod, n, v)


def _her_file(out: Path):
    """v0.362 H.her_file(name): open a STEP / STL she uploaded to this project (inputs/ only, read-only)."""
    import re as _re

    def load(name: str):
        import cadquery as cq
        if not _re.fullmatch(r"[\w\-. ]{1,80}\.(step|stp|stl)", str(name), _re.I):
            raise ValueError("file ka naam galat hai (sirf .step / .stp / .stl)")
        p = out.parent / "inputs" / str(name)
        if not p.is_file():
            raise ValueError(f"'{name}' is project mein upload nahi hai")
        if p.suffix.lower() in (".step", ".stp"):
            return cq.importers.importStep(str(p))
        return cq.Workplane("XY").add(cq.Shape.importStl(str(p)))
    return load


def _parts_of(cq, obj) -> list:
    """[(name, shape, colour)] for an Assembly (every leaf), else []."""
    out = []
    if isinstance(obj, cq.Assembly):
        for name, child in obj.traverse():
            if child.obj is None:
                continue
            sh = child.obj.val() if isinstance(child.obj, cq.Workplane) else child.obj
            if isinstance(sh, cq.Shape):
                sh = sh.moved(child.loc) if child.loc is not None else sh
                col = child.color.toTuple()[:3] if child.color is not None else None
                out.append((name.split("/")[-1], sh, col))
    return out


def _shape(cq, obj):
    if isinstance(obj, cq.Workplane):
        vals = [v for v in obj.vals() if isinstance(v, cq.Shape)]
        if not vals:
            raise ValueError("result mein koi solid nahi")
        return vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
    if isinstance(obj, cq.Assembly):
        return obj.toCompound()
    if isinstance(obj, cq.Shape):
        return obj
    raise ValueError(f"result cadquery Workplane / Shape hona chahiye, mila {type(obj).__name__}")


def main() -> None:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(job["out_dir"])
    res: dict = {"ok": False, "errors": []}
    t0 = time.time()
    try:
        import cadquery as cq
        sys.path.insert(0, str(Path(__file__).resolve().parent))   # -I leaves the runner's folder off the path
        import parts as _parts
        from parts import H
        H.her_file = _her_file(out)
        g = {"__builtins__": {**SAFE_BUILTINS, "__import__": _gate}, "cq": cq, "math": math, "H": H, "__name__": "hoola_part"}
        saved = _lockdown()
        try:
            exec(compile(job["code"], "hoola_part.py", "exec"), g)
        finally:
            _unlock(saved)
        if "result" not in g:
            raise ValueError("script ne `result` set nahi kiya")
        obj = g["result"]
        parts = _parts_of(cq, obj)
        shape = _shape(cq, obj)
        bb = shape.BoundingBox()
        solids = shape.Solids()
        res.update({
            "valid": bool(shape.isValid()), "volume_mm3": round(float(shape.Volume()), 3),
            "area_mm2": round(float(shape.Area()), 3), "solids": len(solids), "faces": len(shape.Faces()),
            "bbox": {"x": round(bb.xlen, 3), "y": round(bb.ylen, 3), "z": round(bb.zlen, 3),
                     "min": [round(bb.xmin, 3), round(bb.ymin, 3), round(bb.zmin, 3)]},
        })
        com = shape.Center()
        res["com"] = [round(com.x, 3), round(com.y, 3), round(com.z, 3)]
        res["parts"] = [{"name": n, "volume_mm3": round(float(s.Volume()), 3), "valid": bool(s.isValid()),
                         "color": [round(c, 3) for c in col] if col else None} for n, s, col in parts]
        size = max(bb.xlen, bb.ylen, bb.zlen, 1.0)
        # v0.365 her numbers measured, analysis / CAM / sheet requests handed to the next stage
        if _parts.EXPECT:
            import geom
            res["expect"] = geom.check_expect(shape, _parts.EXPECT)
        res["studies"] = _parts.STUDIES[:3]
        res["cam"] = _parts.CAM[:1]
        if _parts.FLAT.get("sheet"):
            res["sheet"] = _parts.FLAT["sheet"]
        big = len(parts) > 40 or len(shape.Faces()) > 4000          # v0.365 big assemblies: coarser mesh, no HLR
        exported = []
        if parts:                                         # an assembly keeps its parts, names and colours in STEP / GLB
            obj.save(str(out / "part.step"))
            obj.export(str(out / "part.glb"))
        else:
            cq.exporters.export(shape, str(out / "part.step"))
            cq.Assembly().add(shape, name="part", color=cq.Color(0.48, 0.57, 0.69)).export(str(out / "part.glb"))
        exported += ["part.step", "part.glb"]
        cq.exporters.export(shape, str(out / "part.stl"), tolerance=size / 800, angularTolerance=0.2)
        exported.append("part.stl")
        for name, fn in (("part.3mf", lambda: cq.exporters.export(cq.Workplane("XY").add(shape), str(out / "part.3mf"))),
                         ("section.dxf", lambda: cq.exporters.export(
                             cq.Workplane("XY").add(shape.translate(cq.Vector(0, 0, -(bb.zmin + bb.zlen / 2)))).section(0),
                             str(out / "section.dxf")))):
            try:                                          # nice-to-have files never fail the part
                fn()
                exported.append(name)
            except Exception as e:
                res.setdefault("notes", []).append(f"{name}: {type(e).__name__}")
        from cadquery.occ_impl.exporters.svg import getSVG
        hlr = {}
        for view, d in ({} if big else HLR_VIEWS).items():
            try:
                hlr[view] = getSVG(shape, {"projectionDir": d, "showHidden": view != "iso", "showAxes": False,
                                           "width": 900, "height": 700, "marginLeft": 40, "marginTop": 40,
                                           "strokeWidth": -1.0, "hiddenColor": (150, 150, 150)})
            except Exception as e:
                res.setdefault("notes", []).append(f"hlr {view}: {type(e).__name__}")
        (out / "hlr.json").write_text(json.dumps(hlr), encoding="utf-8")
        res["exported"] = exported
        # v0.362 one mesh, with each triangle's part index and the parts' colours, so views keep the assembly colours
        palette = [(0.48, 0.57, 0.69), (0.85, 0.65, 0.20), (0.36, 0.62, 0.45), (0.70, 0.40, 0.38), (0.55, 0.47, 0.72),
                   (0.40, 0.62, 0.70), (0.72, 0.60, 0.42), (0.50, 0.52, 0.56)]
        pieces = [(s, col) for _n, s, col in parts] if parts else [(shape, None)]
        V, T, C, colors = [], [], [], []
        for i, (s, col) in enumerate(pieces):
            vv, tt = s.tessellate(size / (150 if big else 500), 0.35 if big else 0.2)
            base = len(V)
            V += [[round(p.x, 4), round(p.y, 4), round(p.z, 4)] for p in vv]
            T += [[a + base, b + base, c + base] for a, b, c in tt]
            C += [i] * len(tt)
            colors.append(list(col) if col else list(palette[i % len(palette)]))
        (out / "mesh.json").write_text(json.dumps({"v": V, "t": T, "c": C, "colors": colors}), encoding="utf-8")
        res["ok"] = True
    except Exception as e:     # the model gets the real reason to fix the script
        tb = traceback.extract_tb(e.__traceback__)
        line = next((f.lineno for f in reversed(tb) if f.filename == "hoola_part.py"), 0)
        res["errors"].append((f"line {line}: " if line else "") + f"{type(e).__name__}: {str(e)[:400]}")
    res["seconds"] = round(time.time() - t0, 2)
    (out / "result.json").write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
