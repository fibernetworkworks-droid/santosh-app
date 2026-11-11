"""v0.365 runs the after-build stage in the box: FEA studies (fea.py) and CNC G-code (cam.py) on the part's own STEP.

python analysis_runner.py job.json -> analysis.json (+ fea_<i>.json surfaces, part.nc) in the job folder.
Only Hoola's own code runs here (no script of hers); the parent reads analysis.json only."""
import json
import sys
import time
import traceback
from pathlib import Path


BOLT_WORDS = ("bolt", "screw", "nut", "washer", "stud", "rivet")


def _contact(out: Path, spec: dict, cq) -> dict:
    """The assembly's own parts (apart_<i>.brep); the bolt / screw / nut / washer solids are left out because each
    bolt is the preloaded connector in the analysis, not a loose solid."""
    import contact
    names = json.loads((out / "aparts.json").read_text(encoding="utf-8")) if (out / "aparts.json").exists() else []
    if len(names) < 2:
        raise ValueError("contact analysis runs on an assembly (result = cq.Assembly, 2+ parts)")
    skip = set(spec.get("skip") or [])
    shapes = []
    for i, n in enumerate(names):
        low = n.lower()
        if n in skip or (spec.get("bolts") and any(w in low for w in BOLT_WORDS)):
            continue
        shapes.append((n, cq.Shape.importBrep(str(out / f"apart_{i}.brep"))))
    return contact.solve(shapes, spec)


def main() -> None:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(job["out_dir"])
    res: dict = {"ok": False, "errors": [], "studies": [], "cam": None}
    t0 = time.time()
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import cadquery as cq
        import fea
        shape = cq.importers.importStep(str(out / "part.step")).val()
        solids = shape.Solids()
        if len(solids) > 1:                    # an assembly is analysed as ONE glued body (said in the result)
            fused = solids[0]
            for s in solids[1:]:
                fused = fused.fuse(s)
            shape = fused.clean()
            glued = True
        else:
            shape = solids[0] if solids else shape
            glued = False
        for i, spec in enumerate(job.get("studies") or []):
            try:
                target = shape
                if spec.get("domain_file"):               # v0.381 flow: the fluid body, not the part
                    import re as _re
                    if not _re.fullmatch(r"domain_\d\.step", str(spec["domain_file"])):
                        raise ValueError("domain file")
                    dsh = cq.importers.importStep(str(out / spec["domain_file"])).val()
                    ds = dsh.Solids()
                    target = ds[0] if len(ds) == 1 else dsh
                elif spec.get("kind") in ("flow", "cfd"):
                    raise ValueError("flow needs H.analyze('flow', domain=<fluid body>, ...)")
                if spec.get("kind", "static") in ("static", "stress") and (spec.get("contact") or spec.get("bolts")):
                    r = _contact(out, spec, cq)                 # v0.386 parts that touch, open, slide, with bolts
                    (out / f"fea_{i}.json").write_text(json.dumps(r.pop("surface")), encoding="utf-8")
                    res["studies"].append({"ok": True, **r, "glued_assembly": False})
                    continue
                r = fea.run(target, spec)
                (out / f"fea_{i}.json").write_text(json.dumps(r.pop("surface")), encoding="utf-8")
                r["glued_assembly"] = glued
                res["studies"].append({"ok": True, **r})
            except Exception as e:
                res["studies"].append({"ok": False, "kind": spec.get("kind"), "error": f"{type(e).__name__}: {str(e)[:300]}"})
        if job.get("cam"):
            try:
                import cam
                r = cam.run(shape, job["cam"])
                (out / "part.nc").write_text(r.pop("gcode"), encoding="utf-8")
                (out / "cam_paths.json").write_text(json.dumps(r.pop("paths")), encoding="utf-8")
                res["cam"] = {"ok": True, **r}
            except Exception as e:
                res["cam"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}
        res["ok"] = True
    except Exception as e:
        res["errors"].append(f"{type(e).__name__}: {str(e)[:400]}")
        res["trace"] = traceback.format_exc()[-800:]
    res["seconds"] = round(time.time() - t0, 1)
    (out / "analysis.json").write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
