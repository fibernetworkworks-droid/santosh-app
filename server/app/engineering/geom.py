"""v0.365 measuring a finished B-rep: holes (diameter, axis, depth), used by H.expect checks and by CAM drilling.
Runs inside the boxes (needs cadquery / OCP)."""
from __future__ import annotations

from typing import Any


def holes(shape) -> list[dict[str, Any]]:
    """Every cylindrical HOLE (material outside the cylinder), one entry per axis line + diameter."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    out: list[dict[str, Any]] = []
    for f in shape.Faces():
        try:
            ad = BRepAdaptor_Surface(f.wrapped)
            if ad.GetType() != GeomAbs_Cylinder:
                continue
            cyl = ad.Cylinder()
            ax = cyl.Axis()
            loc, dr = ax.Location(), ax.Direction()
            r = cyl.Radius()
            u0, u1, v0, v1 = f._uvBounds()
            n, c = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)       # (normal, point) at the middle of the face
            # a point on the face; the vector from the axis to it, compared with the outward normal
            ox, oy, oz = loc.X(), loc.Y(), loc.Z()
            dx, dy, dz = dr.X(), dr.Y(), dr.Z()
            vx, vy, vz = c.x - ox, c.y - oy, c.z - oz
            t = vx * dx + vy * dy + vz * dz
            rx, ry, rz = vx - t * dx, vy - t * dy, vz - t * dz
            if rx * n.x + ry * n.y + rz * n.z > 0:        # normal points away from the axis -> a boss, not a hole
                continue
            bb = f.BoundingBox()
            # canonical axis line: the point on the axis closest to the origin
            s = ox * dx + oy * dy + oz * dz
            px, py, pz = ox - s * dx, oy - s * dy, oz - s * dz
            if dz < 0 or (abs(dz) < 1e-9 and (dy < 0 or (abs(dy) < 1e-9 and dx < 0))):
                dx, dy, dz = -dx, -dy, -dz
            key = (round(2 * r, 2), round(px, 2), round(py, 2), round(pz, 2), round(dx, 3), round(dy, 3), round(dz, 3))
            hit = next((h for h in out if h["_key"] == key), None)
            span = [bb.zmin, bb.zmax] if abs(dz) > 0.999 else None
            if hit:
                if span and hit.get("z"):
                    hit["z"] = [min(hit["z"][0], span[0]), max(hit["z"][1], span[1])]
                continue
            axis = "Z" if abs(dz) > 0.999 else "X" if abs(dx) > 0.999 else "Y" if abs(dy) > 0.999 else "other"
            out.append({"_key": key, "d": round(2 * r, 3), "axis": axis, "xy": [round(px, 3), round(py, 3)],
                        "z": span})
        except Exception:
            continue
    for h in out:
        h.pop("_key", None)
    return out


def check_expect(shape, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """H.expect(...) -> measured pass / fail rows (want vs got)."""
    bb = shape.BoundingBox()
    got_size = sorted([bb.xlen, bb.ylen, bb.zlen])
    rows: list[dict[str, Any]] = []
    hl = None
    for it in items:
        tol = float(it.get("tol") or 0)
        nm = str(it.get("name") or "")
        if "size" in it:
            want = [float(v) for v in it["size"]][:3]
            tl = tol or max(0.5, 0.01 * max(want))
            exact = [bb.xlen, bb.ylen, bb.zlen]
            ok = all(abs(a - b) <= tl for a, b in zip(exact, want)) or \
                all(abs(a - b) <= tl for a, b in zip(got_size, sorted(want)))
            rows.append({"name": nm or "Size", "ok": ok, "want": f"{' x '.join(f'{v:g}' for v in want)} mm ±{tl:g}",
                         "got": f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm"})
        if "max_size" in it:
            want = [float(v) for v in it["max_size"]][:3]
            ok = all(a <= b + 1e-6 for a, b in zip(got_size, sorted(want)))
            rows.append({"name": nm or "Fits inside", "ok": ok, "want": f"<= {' x '.join(f'{v:g}' for v in want)} mm",
                         "got": f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm"})
        if "holes" in it:
            spec = it["holes"] if isinstance(it["holes"], dict) else {"count": int(it["holes"])}
            hl = hl if hl is not None else holes(shape)
            d = spec.get("d")
            tl = float(spec.get("tol") or 0.05)
            sel = [h for h in hl if (d is None or abs(h["d"] - float(d)) <= tl)
                   and (not spec.get("axis") or h["axis"] == str(spec["axis"]).upper())]
            n_want = spec.get("count")
            ok = (len(sel) == int(n_want)) if n_want is not None else bool(sel)
            rows.append({"name": nm or (f"Holes Ø{float(d):g}" if d is not None else "Holes"), "ok": ok,
                         "want": f"{n_want if n_want is not None else '>=1'} x Ø{d if d is not None else 'any'}",
                         "got": f"{len(sel)} found" + (f" (all: {', '.join(sorted({f'Ø{h['d']:g}' for h in hl}))})" if hl else "")})
        if "volume" in it:
            lo, hi = (float(v) for v in it["volume"])
            v = float(shape.Volume())
            rows.append({"name": nm or "Volume", "ok": lo <= v <= hi, "want": f"{lo:,.0f}-{hi:,.0f} mm³",
                         "got": f"{v:,.0f} mm³"})
        if "solids" in it:
            n = len(shape.Solids())
            rows.append({"name": nm or "Bodies", "ok": n == int(it["solids"]), "want": str(it["solids"]), "got": str(n)})
    return rows

