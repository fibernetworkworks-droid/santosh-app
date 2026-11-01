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
        g = {"__builtins__": {**SAFE_BUILTINS, "__import__": _gate}, "cq": cq, "math": math, "__name__": "hoola_part"}
        saved = _lockdown()
        try:
            exec(compile(job["code"], "hoola_part.py", "exec"), g)
        finally:
            _unlock(saved)
        if "result" not in g:
            raise ValueError("script ne `result` set nahi kiya")
        shape = _shape(cq, g["result"])
        bb = shape.BoundingBox()
        solids = shape.Solids()
        res.update({
            "valid": bool(shape.isValid()), "volume_mm3": round(float(shape.Volume()), 3),
            "area_mm2": round(float(shape.Area()), 3), "solids": len(solids), "faces": len(shape.Faces()),
            "bbox": {"x": round(bb.xlen, 3), "y": round(bb.ylen, 3), "z": round(bb.zlen, 3),
                     "min": [round(bb.xmin, 3), round(bb.ymin, 3), round(bb.zmin, 3)]},
        })
        cq.exporters.export(shape, str(out / "part.step"))
        size = max(bb.xlen, bb.ylen, bb.zlen, 1.0)
        cq.exporters.export(shape, str(out / "part.stl"), tolerance=size / 800, angularTolerance=0.2)
        verts, tris = shape.tessellate(size / 300, 0.3)
        (out / "mesh.json").write_text(json.dumps({"v": [[round(p.x, 4), round(p.y, 4), round(p.z, 4)] for p in verts],
                                                    "t": [list(t) for t in tris]}), encoding="utf-8")
        res["ok"] = True
    except Exception as e:     # the model gets the real reason to fix the script
        tb = traceback.extract_tb(e.__traceback__)
        line = next((f.lineno for f in reversed(tb) if f.filename == "hoola_part.py"), 0)
        res["errors"].append((f"line {line}: " if line else "") + f"{type(e).__name__}: {str(e)[:400]}")
    res["seconds"] = round(time.time() - t0, 2)
    (out / "result.json").write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
