"""v0.395 REAL DRAWINGS (box side): orthographic views as VECTOR hidden-line geometry straight from the kernel, and
the features a shop needs measured on the B-rep - every hole stack (diameter, through / blind + depth, counterbore,
countersink) and outside radii - in each view's own 2-D coordinates. drawing.py lays them out on the sheet.

A view is a camera direction d (from the eye into the part) and an up vector u; screen right r = d x u. The shape is
turned so that r -> X, u -> Y, -d -> Z, and OCC's hidden-line removal looks down -Z, so its output IS the view in
model millimetres (no SVG parsing, no pixel guessing)."""
from __future__ import annotations

import math
from typing import Any

# first angle (India / ISO E): top view BELOW the front, the view from the LEFT drawn on the RIGHT
# third angle (US / ISO A):   top view ABOVE the front, the view from the RIGHT drawn on the RIGHT
VIEWS = {
    "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),     # seen FROM the left
    "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),   # seen FROM the right
}


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def frame(view: str):
    d, u = VIEWS[view]
    return d, u, _cross(d, u)


def to2d(view: str, p) -> list[float]:
    _d, u, r = frame(view)
    return [round(_dot(r, p), 4), round(_dot(u, p), 4)]


def _polylines(compounds, tol: float) -> list[list[list[float]]]:
    import cadquery as cq
    from OCP.BRepLib import BRepLib
    out = []
    for c in compounds:
        if c.IsNull():
            continue
        BRepLib.BuildCurves3d_s(c, 1e-6)
        for e in cq.Shape(c).Edges():
            try:
                L = e.Length()
                if L < 1e-6:
                    continue
                kind = e.geomType()
                n = 1 if kind == "LINE" else max(8, min(180, int(L / max(tol, 1e-3))))
                pts = [e.positionAt(i / n) for i in range(n + 1)]
                out.append([[round(p.x, 4), round(p.y, 4)] for p in pts])
            except Exception:
                continue
    return out


def project(shape, view: str) -> dict[str, Any]:
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Ax3
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    d, u, r = frame(view)
    tr = gp_Trsf()
    # world -> view: r -> X, u -> Y, -d -> Z
    src = gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(-d[0], -d[1], -d[2]), gp_Dir(*r))
    tr.SetTransformation(src)
    import cadquery as cq
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    moved = cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped, tr, True).Shape())
    bb = shape.BoundingBox()
    size = max(bb.xlen, bb.ylen, bb.zlen, 1.0)
    algo = HLRBRep_Algo()
    algo.Add(moved.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _polylines([h.VCompound(), h.OutLineVCompound()], size / 200)
    hid = _polylines([h.HCompound(), h.OutLineHCompound()], size / 200)
    xs = [p[0] for pl in vis for p in pl] or [0.0]
    ys = [p[1] for pl in vis for p in pl] or [0.0]
    return {"vis": vis, "hid": hid, "box": [min(xs), min(ys), max(xs), max(ys)], "d": d, "u": u, "r": r}


# ---------------------------------------------------------------- features
def _cyl_faces(shape):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder
    out = []
    for f in shape.Faces():
        try:
            ad = BRepAdaptor_Surface(f.wrapped)
            t = ad.GetType()
            if t not in (GeomAbs_Cylinder, GeomAbs_Cone):
                continue
            g = ad.Cylinder() if t == GeomAbs_Cylinder else ad.Cone()
            ax = g.Axis()
            loc, dr = ax.Location(), ax.Direction()
            d = (dr.X(), dr.Y(), dr.Z())
            if d[2] < -1e-9 or (abs(d[2]) < 1e-9 and (d[1] < -1e-9 or (abs(d[1]) < 1e-9 and d[0] < 0))):
                d = (-d[0], -d[1], -d[2])
            o = (loc.X(), loc.Y(), loc.Z())
            s = _dot(o, d)
            p0 = (o[0] - s * d[0], o[1] - s * d[1], o[2] - s * d[2])          # axis point nearest the origin
            u0, u1, v0, v1 = f._uvBounds()
            n, c = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
            rel = (c.x - p0[0], c.y - p0[1], c.z - p0[2])
            t_c = _dot(rel, d)
            radial = (rel[0] - t_c * d[0], rel[1] - t_c * d[1], rel[2] - t_c * d[2])
            inward = _dot(radial, (n.x, n.y, n.z)) < 0                        # normal toward the axis = a hole
            ts, rs = [], []
            for e in f.Edges():
                for k in range(9):
                    p = e.positionAt(k / 8)
                    q = (p.x - p0[0], p.y - p0[1], p.z - p0[2])
                    tq = _dot(q, d)
                    ts.append(tq)
                    rs.append(math.dist(q, (tq * d[0], tq * d[1], tq * d[2])))
            span = 0.0
            if t == GeomAbs_Cylinder:
                span = (u1 - u0)
            out.append({"kind": "cyl" if t == GeomAbs_Cylinder else "cone", "d": d, "p0": p0,
                        "r": g.Radius() if t == GeomAbs_Cylinder else None, "t": (min(ts), max(ts)),
                        "rmin": min(rs), "rmax": max(rs), "inward": inward, "span": span,
                        "half_angle": math.degrees(g.SemiAngle()) if t != GeomAbs_Cylinder else None,
                        "mid": (c.x, c.y, c.z)})
        except Exception:
            continue
    return out


def _same_axis(a, b, tol=1e-3) -> bool:
    return (abs(_dot(a["d"], b["d"])) > 1 - 1e-6 and math.dist(a["p0"], b["p0"]) < tol * 10)


def hole_stacks(shape) -> list[dict[str, Any]]:
    """Coaxial hole faces grouped into stacks: main bore + counterbore / countersink, through or blind."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_OUT
    faces = [f for f in _cyl_faces(shape) if f["inward"]]
    groups: list[list[dict]] = []
    for f in faces:
        for g in groups:
            if _same_axis(g[0], f):
                g.append(f)
                break
        else:
            groups.append([f])
    cls = BRepClass3d_SolidClassifier(shape.wrapped)

    def outside(p) -> bool:
        cls.Perform(gp_Pnt(*p), 1e-6)
        return cls.State() == TopAbs_OUT
    stacks = []
    for g in groups:
        d, p0 = g[0]["d"], g[0]["p0"]
        cyl = [f for f in g if f["kind"] == "cyl"]
        if not cyl:
            continue
        # merge split cylinder faces of one radius
        segs: dict[float, list[float]] = {}
        for f in cyl:
            k = round(f["r"], 3)
            t0, t1 = f["t"]
            if k in segs:
                segs[k] = [min(segs[k][0], t0), max(segs[k][1], t1)]
            else:
                segs[k] = [t0, t1]
        cones = [f for f in g if f["kind"] == "cone"]
        T0 = min([s[0] for s in segs.values()] + [c["t"][0] for c in cones])
        T1 = max([s[1] for s in segs.values()] + [c["t"][1] for c in cones])
        r_main = min(segs)
        eps = 0.05

        def at(t):
            return (p0[0] + t * d[0], p0[1] + t * d[1], p0[2] + t * d[2])
        open0, open1 = outside(at(T0 - eps)), outside(at(T1 + eps))
        if not (open0 or open1):
            continue                                                     # an internal cavity, not a drilled hole
        top_t = T1 if open1 else T0                                      # the entry end
        sgn = -1 if open1 else 1                                         # direction into the part
        m0, m1 = segs[r_main]
        through = open0 and open1 and (m1 - m0) > 0
        depth = abs((m0 if open1 else m1) - top_t) if not through else T1 - T0
        st = {"axis_d": d, "entry": at(top_t), "into": tuple(sgn * x for x in d), "dia": round(2 * r_main, 3),
              "through": bool(through and len(segs) == 1 and not cones) or bool(through),
              "depth": round(depth, 3), "cbore": None, "csk": None}
        bigger = sorted((r for r in segs if r > r_main + 1e-3), reverse=False)
        for r in bigger:
            t0, t1 = segs[r]
            if abs((t1 if open1 else t0) - top_t) < 1e-3:              # touches the entry face
                st["cbore"] = [round(2 * r, 3), round(t1 - t0, 3)]
                break
        for c in cones:
            if abs((c["t"][1] if open1 else c["t"][0]) - top_t) < 0.05 + 1e-3 or st["cbore"] is None:
                st["csk"] = [round(2 * c["rmax"], 3), round(2 * (c["half_angle"] or 45), 1)]
                break
        if through:
            st["depth"] = None
        stacks.append(st)
    return stacks


def outer_arcs(shape) -> list[dict[str, Any]]:
    """Outside cylindrical faces (rounds, bosses): radius, whether a full circle, a point on them."""
    out = []
    for f in _cyl_faces(shape):
        if f["inward"] or f["kind"] != "cyl":
            continue
        out.append({"axis_d": f["d"], "r": round(f["r"], 3), "full": f["span"] > 2 * math.pi - 1e-3, "at": f["mid"],
                    "center": f["p0"]})
    return out


def drawing_data(shape, projection: str = "first") -> dict[str, Any]:
    side = "left" if projection == "first" else "right"
    names = ["front", "top", side]
    views = {}
    for n in names:
        views[n] = project(shape, n)
    holes = []
    for h in hole_stacks(shape):
        ax = h["axis_d"]
        # the view that looks INTO the hole's entry face shows it as a visible circle; else a parallel view
        view = next((n for n in names if _dot(frame(n)[0], h["into"]) > 0.999), None)
        far = False
        if view is None:
            view = next((n for n in names if abs(_dot(frame(n)[0], ax)) > 0.999), None)
            far = True
        if view is None:
            continue
        holes.append({"view": view, "far": far, "c": to2d(view, h["entry"]), "dia": h["dia"], "through": h["through"],
                      "depth": h["depth"], "cbore": h["cbore"], "csk": h["csk"],
                      "axis": "XYZ"[max(range(3), key=lambda i: abs(ax[i]))]})
    arcs = []
    for a in outer_arcs(shape):
        view = next((n for n in names if abs(_dot(frame(n)[0], a["axis_d"])) > 0.999), None)
        if view is None:
            continue
        arcs.append({"view": view, "r": a["r"], "full": a["full"], "at": to2d(view, a["at"]),
                     "c": to2d(view, a["center"])})
    bb = shape.BoundingBox()
    return {"projection": projection, "views": views, "holes": holes, "arcs": arcs,
            "bbox": [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)]}
