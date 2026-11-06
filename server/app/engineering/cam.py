"""v0.365 HOOLA CAM: 2.5D CNC G-code for a part Hoola designed (3-axis mill, part flat on the table, Z up).

Operations, in machining order:
  face     one pass over the stock top down to the part top
  pocket   every upward floor below the top: inward offset rings (stepover) at each stepdown, down to that floor
  drill    every vertical hole: peck drilling with explicit moves (works on GRBL, Fanuc, Marlin-CNC: no canned cycles)
  profile  the outside outline (largest section near the bottom), offset by the tool radius, climb, stepdowns to
           the bottom, with holding tabs left on the last pass when asked
Units mm, G90 absolute, G21, G17, work zero = part's bottom-left corner of the bounding box at the TOP of the part.
DRAFT G-code: simulate in her CAM viewer and dry-run above the stock before cutting."""
from __future__ import annotations

import math
from typing import Any

DEFAULTS = {"tool_d": 6.0, "stepdown": 1.5, "stepover": 0.45, "feed": 800.0, "plunge": 250.0, "rpm": 12000,
            "safe_z": 5.0, "stock_top": 0.5, "drill_peck": 2.0, "tabs": 0, "ops": ["face", "pocket", "drill", "profile"]}


class CamError(Exception):
    pass


def _pts(wire, step: float) -> list[tuple[float, float]]:
    n = max(8, int(wire.Length() / max(step, 0.2)))
    out = []
    for i in range(n + 1):
        p = wire.positionAt(i / n)
        out.append((p.x, p.y))
    return out


def _offsets(wire, first: float, step: float, max_rings: int = 60) -> list:
    """Inward rings: offset2D(-first), then every -step until nothing is left (OCC offsets, arcs at corners)."""
    rings = []
    d = first
    for _ in range(max_rings):
        try:
            got = wire.offset2D(-d, "arc")
        except Exception:
            break
        got = [w for w in got if w.Length() > 0.5]
        if not got:
            break
        rings.append(got)
        d += step
    return rings


def run(shape, spec: dict[str, Any]) -> dict[str, Any]:
    import cadquery as cq
    o = {**DEFAULTS, **{k: v for k, v in (spec or {}).items() if k in DEFAULTS}}
    td = float(o["tool_d"])
    if not (0.5 <= td <= 25):
        raise CamError("tool_d 0.5-25 mm")
    tr = td / 2
    sd = max(0.1, min(float(o["stepdown"]), td))
    so = max(0.1, min(float(o["stepover"]), 0.9)) * td
    feed, plunge, rpm = float(o["feed"]), float(o["plunge"]), int(o["rpm"])
    safe = float(o["safe_z"])
    bb = shape.BoundingBox()
    top = bb.zmax
    ox, oy = bb.xmin, bb.ymin
    lines: list[str] = []
    paths: list[dict[str, Any]] = []          # for the preview: {"op", "pts": [[x, y], ...], "z"}
    length = {"cut": 0.0, "rapid": 0.0}
    cur = [0.0, 0.0, safe]

    def mv(code, x=None, y=None, z=None, f=None):
        nx = cur[0] if x is None else x
        ny = cur[1] if y is None else y
        nz = cur[2] if z is None else z
        dist = math.dist(cur, (nx, ny, nz))
        length["rapid" if code == "G0" else "cut"] += dist
        cur[:] = [nx, ny, nz]
        w = [code] + [f"{a}{v:.3f}" for a, v in (("X", x), ("Y", y), ("Z", z)) if v is not None]
        if f:
            w.append(f"F{f:.0f}")
        lines.append(" ".join(w))

    def X(v):
        return v - ox

    def Y(v):
        return v - oy

    def Z(v):
        return v - top

    lines += ["%", "(HOOLA CAM - DRAFT: simulate and dry-run before cutting)", f"(tool: {td:g} mm flat end mill)",
              "(zero: X0 Y0 = part bounding-box corner, Z0 = part top)", "G21 G90 G17 G94", f"M3 S{rpm}",
              f"G0 Z{safe:.3f}"]
    ops = [str(x).lower() for x in o["ops"]]
    done = []
    # face
    if "face" in ops and float(o["stock_top"]) > 0:
        z = 0.0
        y = -tr * 0.5
        mv("G0", X(bb.xmin) - td, Y(bb.ymin) + y)
        mv("G1", z=z, f=plunge)
        row = 0
        pts = []
        while y <= bb.ylen + tr * 0.5:
            xa, xb = (X(bb.xmin) - td, X(bb.xmax) + td) if row % 2 == 0 else (X(bb.xmax) + td, X(bb.xmin) - td)
            mv("G1", xa, Y(bb.ymin) + y, f=feed)
            mv("G1", xb, f=feed)
            pts += [[xa, y], [xb, y]]
            y += so
            row += 1
        mv("G0", z=safe)
        paths.append({"op": "face", "pts": pts})
        done.append("face")
    # pockets: upward planar floors below the top
    if "pocket" in ops:
        n_p = 0
        for f in shape.Faces():
            try:
                if f.geomType() != "PLANE":
                    continue
                c = f.Center()
                n = f.normalAt(c)
                if n.z < 0.999 or c.z >= top - 0.05 or c.z <= bb.zmin + 0.05:
                    continue
                floor = c.z
                outer = f.outerWire()
                rings = _offsets(outer, tr, so)
                if not rings:
                    continue
                n_p += 1
                depths = []
                z = top
                while z - sd > floor + 1e-6:
                    z -= sd
                    depths.append(z)
                depths.append(floor)
                for zz in depths:
                    for ring in reversed(rings):                    # from the middle outwards
                        for w in ring:
                            pts = _pts(w, td / 4)
                            mv("G0", X(pts[0][0]), Y(pts[0][1]))
                            mv("G1", z=Z(zz), f=plunge)
                            for px, py in pts[1:]:
                                mv("G1", X(px), Y(py), f=feed)
                            paths.append({"op": "pocket", "pts": [[X(a), Y(b)] for a, b in pts]})
                    mv("G0", z=safe)
            except Exception:
                continue
        if n_p:
            done.append(f"pocket x{n_p}")
    # drill
    if "drill" in ops:
        try:
            from . import geom
        except ImportError:                     # inside the box: plain module next to this one
            import geom
        hs = [h for h in geom.holes(shape) if h["axis"] == "Z" and h.get("z")]
        if hs:
            lines.append(f"(drill {len(hs)} holes; change to a drill of each size or helix with the end mill)")
        for h in sorted(hs, key=lambda h: (h["d"], h["xy"][0], h["xy"][1])):
            x, y = h["xy"]
            zb = max(h["z"][0], bb.zmin) - (0.5 if h["z"][0] <= bb.zmin + 0.01 else 0.0)
            lines.append(f"(hole d{h['d']:g} at X{X(x):.3f} Y{Y(y):.3f})")
            mv("G0", X(x), Y(y))
            mv("G0", z=1.0)
            zc = 0.0
            while zc > Z(zb) + 1e-6:
                zc = max(Z(zb), zc - float(o["drill_peck"]))
                mv("G1", z=zc, f=plunge)
                mv("G0", z=1.0)
            mv("G0", z=safe)
            paths.append({"op": "drill", "pts": [[X(x), Y(y)]], "d": h["d"]})
        if hs:
            done.append(f"drill x{len(hs)}")
    # profile
    if "profile" in ops:
        zcut = bb.zmin + min(0.2, bb.zlen / 4)
        try:
            wp = cq.Workplane("XY").add(shape.translate(cq.Vector(0, 0, -zcut))).section(0)
            faces = [f for v in wp.vals() for f in (v.Faces() if hasattr(v, "Faces") else [])]
            outer = max(faces, key=lambda f: f.Area()).outerWire()
            ring = outer.offset2D(tr, "arc")[0]
        except Exception as e:
            raise CamError(f"profile outline nahi mila: {type(e).__name__}")
        pts = _pts(ring, td / 4)
        z = 0.0
        tabs = int(o["tabs"] or 0)
        bottom = Z(bb.zmin) - 0.3
        while z > bottom + 1e-6:
            z = max(bottom, z - sd)
            last = z <= bottom + 1e-6
            mv("G0", X(pts[0][0]), Y(pts[0][1]))
            mv("G1", z=z, f=plunge)
            nn = len(pts)
            for i, (px, py) in enumerate(pts[1:], 1):
                if last and tabs and any(abs(i - k * nn / tabs) < max(1, nn * 0.02) for k in range(tabs)):
                    mv("G1", X(px), Y(py), z + min(2.0, bb.zlen * 0.3), f=feed)
                    mv("G1", z=z, f=plunge)
                    continue
                mv("G1", X(px), Y(py), f=feed)
            mv("G0", z=safe)
        paths.append({"op": "profile", "pts": [[X(a), Y(b)] for a, b in pts]})
        done.append("profile")
    lines += [f"G0 Z{safe:.3f}", "M5", "G0 X0 Y0", "M30", "%"]
    minutes = length["cut"] / max(feed, 1) + length["rapid"] / 3000.0
    return {"gcode": "\n".join(lines) + "\n", "ops": done, "lines": len(lines), "tool_d": td, "stepdown": sd,
            "stepover_mm": round(so, 3), "feed": feed, "rpm": rpm, "cut_m": round(length["cut"] / 1000, 2),
            "minutes": round(minutes * 1.15, 1), "stock_mm": [round(bb.xlen + 2 * td, 1), round(bb.ylen + 2 * td, 1),
                                                               round(bb.zlen + float(o["stock_top"]), 1)],
            "paths": paths, "size": [round(bb.xlen, 3), round(bb.ylen, 3)]}
