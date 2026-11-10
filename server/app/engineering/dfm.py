"""v0.403 HOOLA DFM: design-for-manufacturing checks MEASURED on the part's own B-rep (box side, runs after the build
when the script asks with H.make(process, ...)).

Every row = what was measured, the limit, where the limit comes from, a status and a concrete fix:
  pass        a measured value inside a cited limit
  fail        a measured value outside it (goes back to the designer for a fix)
  review      a real risk the numbers cannot settle alone (undercut needs a side action, setups to plan...)
  unverified  the check could not measure (said, never guessed as a pass)
Limits are published starting points (Protolabs Network / Hubs design guides, Protolabs, Formlabs, HP, EOS,
ISO/ASTM 52910); HER shop's numbers override them (H.make(..., limits={...})). Measurements: rays cast with OCC's
exact B-rep intersector (wall thickness, access, undercuts), face normals (draft, overhang), the hole stacks of
views2d (diameters / depths), concave-edge tests with the solid classifier (sharp internal corners)."""
from __future__ import annotations

import math
from typing import Any

SOURCES = {
    "am": "Protolabs Network (Hubs) 3D printing design guides; Formlabs / HP MJF / EOS design rules; ISO/ASTM 52910",
    "cnc": "Protolabs Network (Hubs) 'How to design parts for CNC machining'; Protolabs CNC milling guidelines",
    "sheet": "Protolabs Network (Hubs) sheet metal fabrication design guide; Protolabs sheet metal guidelines",
    "mold": "Protolabs Network (Hubs) injection moulding design guide; Protolabs injection moulding guidelines",
}

# additive: min wall (supported), self-supporting angle from horizontal (None = powder supports), min hole, min feature
AM = {
    "fdm": {"wall": 1.2, "angle": 45.0, "hole": 2.0, "feature": 0.8, "label": "FDM / FFF"},
    "sla": {"wall": 0.5, "angle": 30.0, "hole": 0.5, "feature": 0.2, "label": "SLA / DLP resin"},
    "sls": {"wall": 0.7, "angle": None, "hole": 1.5, "feature": 0.8, "label": "SLS (PA12)"},
    "mjf": {"wall": 0.5, "angle": None, "hole": 1.0, "feature": 0.5, "label": "HP MJF"},
    "metal_pbf": {"wall": 0.4, "angle": 45.0, "hole": 1.5, "feature": 0.4, "label": "metal powder bed (SLM / DMLS)"},
}
CNC = {"wall_metal": 0.8, "wall_plastic": 1.5, "hole_min": 2.5, "hole_depth_x_d": 4.0, "hole_depth_max_x_d": 10.0,
       "pocket_depth_x_w": 4.0, "tool_d": 6.0, "envelope": (400.0, 250.0, 150.0)}
SHEET = {"bend_r_x_t": 1.0, "flange_x_t": 4.0, "hole_x_t": 1.0, "hole_bend_x_t": 2.5}
MOLD = {"draft_deg": 0.5, "draft_good_deg": 1.0, "wall": {"abs": (1.2, 3.5), "pp": (0.8, 3.8), "pc": (1.0, 4.0),
                                                         "nylon": (0.8, 3.0), "pom": (0.8, 3.0), "default": (1.0, 4.0)},
        "uniform_ratio": 2.0, "cavity_mpa": 35.0}
PLASTICS = ("abs", "pla", "petg", "nylon", "pom", "polycarbonate", "pc", "pp", "acrylic", "pa12", "resin")


def _row(check, measured, limit, status, fix="", source=""):
    return {"check": check, "measured": measured, "limit": limit, "status": status, "fix": fix, "source": source}


# ---------------------------------------------------------------- measuring
class Probe:
    def __init__(self, shape):
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
        self.shape = shape
        bb = shape.BoundingBox()
        self.bb = bb
        self.size = max(bb.xlen, bb.ylen, bb.zlen, 1.0)
        self.ix = IntCurvesFace_ShapeIntersector()
        self.ix.Load(shape.wrapped, 1e-6)
        self.cls = BRepClass3d_SolidClassifier(shape.wrapped)

    def hit(self, p, d, start=1e-4) -> float | None:
        """Distance along d from p to the first surface beyond `start`, or None."""
        from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
        self.ix.Perform(gp_Lin(gp_Pnt(*p), gp_Dir(*d)), start, 4 * self.size)
        if not self.ix.IsDone() or self.ix.NbPnt() == 0:
            return None
        return min(self.ix.WParameter(i) for i in range(1, self.ix.NbPnt() + 1))

    def inside(self, p) -> bool:
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN
        self.cls.Perform(gp_Pnt(*p), 1e-7)
        return self.cls.State() == TopAbs_IN

    def samples(self, n: int = 600) -> list[tuple[tuple, tuple, float, int]]:
        """(point, outward normal, area share, face index) spread over the surface by area."""
        faces = self.shape.Faces()
        areas = [max(f.Area(), 0.0) for f in faces]
        tot = sum(areas) or 1.0
        out = []
        for fi, (f, a) in enumerate(zip(faces, areas)):
            k = max(1, int(round(n * a / tot)))
            u0, u1, v0, v1 = f._uvBounds()
            g = max(1, int(math.ceil(math.sqrt(k))))
            from OCP.BRepTopAdaptor import BRepTopAdaptor_FClass2d
            from OCP.gp import gp_Pnt2d
            from OCP.TopAbs import TopAbs_IN
            c2 = BRepTopAdaptor_FClass2d(f.wrapped, 1e-7)
            got = []
            for i in range(g):
                for j in range(g):
                    u = u0 + (u1 - u0) * (i + 0.5) / g
                    v = v0 + (v1 - v0) * (j + 0.5) / g
                    if c2.Perform(gp_Pnt2d(u, v)) != TopAbs_IN:
                        continue
                    nrm, pt = f.normalAt(u, v)
                    got.append(((pt.x, pt.y, pt.z), (nrm.x, nrm.y, nrm.z)))
            for pt, nrm in got[:k] or []:
                out.append((pt, nrm, a / max(len(got[:k]), 1), fi))
        return out


def wall_thickness(pr: Probe, samples) -> dict[str, Any]:
    vals = []
    for p, n, _a, _fi in samples:
        d = (-n[0], -n[1], -n[2])
        t = pr.hit(p, d)
        if t is not None and t > 1e-3:
            vals.append(t)
    if not vals:
        return {"error": "no ray hit the other side"}
    vals.sort()
    k = lambda q: vals[min(len(vals) - 1, int(q * len(vals)))]
    return {"min": round(vals[0], 3), "p05": round(k(0.05), 3), "median": round(k(0.5), 3), "p95": round(k(0.95), 3),
            "max": round(vals[-1], 3), "rays": len(vals)}


def overhang(pr: Probe, samples, angle_deg: float, up=(0, 0, 1)) -> dict[str, Any]:
    """Downward-facing area steeper than the self-supporting angle (faces on the bed excluded)."""
    lim = math.sin(math.radians(90 - angle_deg))           # n.down > cos(angle from vertical)...
    zmin = min(_dot(p, up) for p, _n, _a, _f in samples)
    area = vol = tot = 0.0
    for p, n, a, _fi in samples:
        tot += a
        down = -_dot(n, up)
        h = _dot(p, up) - zmin
        if down > lim and h > 0.05:
            area += a
            vol += a * h * down
    return {"area_mm2": round(area, 1), "pct": round(100 * area / max(tot, 1e-9), 2), "support_mm3": round(vol, 0)}


def orientations(pr: Probe, samples, angle_deg: float) -> list[dict[str, Any]]:
    out = []
    for name, up in (("as modelled (+Z up)", (0, 0, 1)), ("upside down", (0, 0, -1)), ("on +X", (1, 0, 0)),
                     ("on -X", (-1, 0, 0)), ("on +Y", (0, 1, 0)), ("on -Y", (0, -1, 0))):
        o = overhang(pr, samples, angle_deg, up)
        out.append({"orientation": name, "support_area_mm2": o["area_mm2"], "support_mm3": o["support_mm3"]})
    return sorted(out, key=lambda r: r["support_mm3"])


def concave_edges(pr: Probe) -> list[dict[str, Any]]:
    """Sharp concave edges (two faces meeting with material on the OUTSIDE of the angle - an internal corner)."""
    out = []
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    import cadquery as cq
    mp = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(pr.shape.wrapped, TopAbs_EDGE, TopAbs_FACE, mp)
    eps = 2e-3 * pr.size
    for i in range(1, mp.Extent() + 1):
        e = cq.Edge(mp.FindKey(i))
        fl = mp.FindFromIndex(i)
        if fl.Extent() != 2:
            continue
        try:
            fs = [cq.Face(f) for f in fl]
            mid = e.positionAt(0.5)
            tg = e.tangentAt(0.5)
            tg = (tg.x, tg.y, tg.z)
            steps = []
            for f in fs:
                nn = f.normalAt(mid)
                c = _cross((nn.x, nn.y, nn.z), tg)
                L = math.sqrt(_dot(c, c)) or 1.0
                c = (c[0] / L, c[1] / L, c[2] / L)
                q = cq.Vertex.makeVertex(mid.x + c[0] * eps, mid.y + c[1] * eps, mid.z + c[2] * eps)
                if f.distance(q) > eps * 0.2:                      # step INTO the face, not off it
                    c = (-c[0], -c[1], -c[2])
                steps.append(c)
            if abs(_dot(steps[0], steps[1])) > 0.98:               # flat / tangent join
                continue
            q = (mid.x + (steps[0][0] + steps[1][0]) * eps, mid.y + (steps[0][1] + steps[1][1]) * eps,
                 mid.z + (steps[0][2] + steps[1][2]) * eps)
            if not pr.inside(q):                                    # between the two faces is AIR -> inside corner
                out.append({"at": [round(mid.x, 2), round(mid.y, 2), round(mid.z, 2)], "dir": tg,
                            "length": round(e.Length(), 2)})
        except Exception:
            continue
    return out


def access(pr: Probe, samples, dirs) -> dict[str, Any]:
    """Which approach directions reach each surface sample (a ray leaving the surface toward the tool escapes)."""
    reach = []
    for p, n, a, fi in samples:
        ok = []
        for name, d in dirs:
            if _dot(n, d) < -1e-6:                                  # facing away from that tool direction
                continue
            q = (p[0] + n[0] * 1e-3, p[1] + n[1] * 1e-3, p[2] + n[2] * 1e-3)
            if pr.hit(q, d) is None:                                # nothing in the way toward the tool
                ok.append(name)
        reach.append((a, fi, ok))
    return {"reach": reach}


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ---------------------------------------------------------------- per process
def check(shape, spec: dict, holes: list[dict] | None = None, sheet: dict | None = None) -> dict[str, Any]:
    proc = str(spec.get("process", "fdm")).lower().replace(" ", "_")
    lim_over = spec.get("limits") or {}
    material = str(spec.get("material") or "").lower()
    pr = Probe(shape)
    samples = pr.samples(int(spec.get("samples") or 500))
    rows: list[dict] = []
    facts: dict[str, Any] = {}
    if proc in AM:
        L = {**AM[proc], **lim_over}
        src = SOURCES["am"]
        wt = wall_thickness(pr, samples)
        facts["wall"] = wt
        if "error" in wt:
            rows.append(_row("Wall thickness", "-", f">= {L['wall']} mm", "unverified", "", src))
        else:
            st = "pass" if wt["p05"] >= L["wall"] else "fail"
            rows.append(_row("Wall thickness", f"min {wt['min']} / 5th pct {wt['p05']} mm", f">= {L['wall']} mm",
                             st, "" if st == "pass" else f"thicken walls to {L['wall']} mm or more", src))
        if L["angle"] is not None:
            ov = overhang(pr, samples, L["angle"])
            facts["overhang"] = ov
            ors = orientations(pr, samples, L["angle"])
            facts["orientations"] = ors
            best = ors[0]
            st = "pass" if ov["pct"] < 1 else "review"
            rows.append(_row("Overhangs (need support)", f"{ov['area_mm2']:,.0f} mm² ({ov['pct']}% of surface), "
                             f"support ~{ov['support_mm3']:,.0f} mm³", f"steeper than {L['angle']}° from horizontal",
                             st, f"print {best['orientation']} (support ~{best['support_mm3']:,.0f} mm³) or add "
                             "chamfers / 45° slopes" if st != "pass" else "", src))
        else:
            rows.append(_row("Overhangs", "not needed", "powder supports the part", "pass",
                             "add 2 escape holes (>= 3.5 mm) if the part is hollow", src))
        small = [h for h in holes or [] if h["dia"] < L["hole"]]
        rows.append(_row("Smallest hole", f"Ø{min(h['dia'] for h in holes):g} mm" if holes else "no holes",
                         f">= Ø{L['hole']} mm", "fail" if small else "pass",
                         f"open {len(small)} hole(s) to Ø{L['hole']} or drill after printing" if small else "", src))
        bb = pr.bb
        rows.append(_row("Build size", f"{bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm",
                         f"<= {lim_over.get('bed', '220 x 220 x 250')} mm (typical desktop)",
                         "pass" if max(bb.xlen, bb.ylen) <= 220 and bb.zlen <= 250 else "review",
                         "split the part or use a larger printer" if max(bb.xlen, bb.ylen) > 220 or bb.zlen > 250 else "",
                         src))
    elif proc == "cnc":
        L = {**CNC, **lim_over}
        src = SOURCES["cnc"]
        tool_r = float(spec.get("tool_d") or L["tool_d"]) / 2
        plastic = any(w in material for w in PLASTICS)
        wmin = L["wall_plastic"] if plastic else L["wall_metal"]
        wt = wall_thickness(pr, samples)
        facts["wall"] = wt
        if "error" in wt:
            rows.append(_row("Thin walls", "-", f">= {wmin} mm", "unverified", "", src))
        else:
            st = "pass" if wt["p05"] >= wmin else "fail"
            rows.append(_row("Thin walls", f"min {wt['min']} / 5th pct {wt['p05']} mm", f">= {wmin} mm "
                             f"({'plastic' if plastic else 'metal'})", st,
                             "" if st == "pass" else f"thicken to {wmin} mm (thin walls chatter and bend)", src))
        sharp = [e for e in concave_edges(pr) if abs(e["dir"][2]) > 0.95 and e["length"] > 0.5]
        facts["sharp_internal_vertical"] = len(sharp)
        rows.append(_row("Internal vertical corners", f"{len(sharp)} sharp" if sharp else "none sharp",
                         f"radius >= tool radius {tool_r:g} mm (a round end mill cannot cut a sharp inside corner)",
                         "fail" if sharp else "pass",
                         f"add R{tool_r * 1.1:.1f} or more to {len(sharp)} vertical inside corner(s) (e.g. at "
                         f"{sharp[0]['at']}), or dog-bone reliefs / EDM" if sharp else "", src))
        small_r = []
        for f in _concave_cyls(shape):
            if abs(f["d"][2]) > 0.95 and f["r"] < tool_r - 1e-3:
                small_r.append(f["r"])
        if small_r:
            rows.append(_row("Inside corner radii", f"smallest R{min(small_r):g} mm", f">= R{tool_r:g} (tool)", "fail",
                             f"open the corner radii to R{tool_r * 1.1:.1f} or plan a smaller cutter", src))
        deep = [h for h in holes or [] if h.get("depth") and h["depth"] / max(h["dia"], 1e-9) > L["hole_depth_x_d"]]
        too_deep = [h for h in deep if h["depth"] / h["dia"] > L["hole_depth_max_x_d"]]
        rows.append(_row("Hole depth / diameter", (f"deepest {max(h['depth'] / h['dia'] for h in deep):.1f} x d"
                                                   if deep else "all <= 4 x d"),
                         f"<= {L['hole_depth_x_d']:g} x d (standard drills; {L['hole_depth_max_x_d']:g} x d possible)",
                         "fail" if too_deep else ("review" if deep else "pass"),
                         "shorten or step the deep hole(s), or drill from both sides" if deep else "", src))
        small = [h for h in holes or [] if h["dia"] < L["hole_min"]]
        rows.append(_row("Smallest hole", f"Ø{min(h['dia'] for h in holes):g} mm" if holes else "no holes",
                         f">= Ø{L['hole_min']} mm recommended", "review" if small else "pass",
                         "micro-drilling costs more; open to Ø2.5 if allowed" if small else "", src))
        dirs = [("+Z", (0, 0, 1)), ("-Z", (0, 0, -1)), ("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Y", (0, 1, 0)),
                ("-Y", (0, -1, 0))]
        acc = access(pr, samples, dirs)
        need = _setups(acc["reach"])
        facts["setups"] = need
        unreach = need.get("unreachable_pct", 0)
        rows.append(_row("Setups (3-axis)", f"{need['count']} setup(s): {', '.join(need['dirs'])}"
                         + (f"; {unreach}% of the surface reached from no side" if unreach else ""),
                         "fewer is cheaper; every surface reachable", "review" if (need["count"] > 2 or unreach) else "pass",
                         "unreachable areas need 5-axis, a slot / undercut cutter or a redesign" if unreach else
                         ("combine features on fewer sides" if need["count"] > 2 else ""), src))
        bb = pr.bb
        env = sorted(L["envelope"])
        big = any(a > b for a, b in zip(sorted([bb.xlen, bb.ylen, bb.zlen]), env))
        rows.append(_row("Machine envelope", f"{bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm",
                         f"<= {' x '.join(f'{v:g}' for v in L['envelope'])} mm (typical 3-axis mill)",
                         "review" if big else "pass", "check her shop's machine size" if big else "", src))
    elif proc in ("sheet", "sheet_metal"):
        src = SOURCES["sheet"]
        L = {**SHEET, **lim_over}
        if not sheet:
            rows.append(_row("Sheet geometry", "not built with H.sheet / H.tray", "constant thickness, bends known",
                             "unverified", "build the part with H.sheet(...) or H.tray(...)", src))
        else:
            t, r = float(sheet["t"]), float(sheet["r"])
            wt = wall_thickness(pr, samples)
            facts["wall"] = wt
            if "error" not in wt:
                even = abs(wt["median"] - t) < 0.05 * t + 0.02
                rows.append(_row("Constant thickness", f"median {wt['median']} mm", f"= {t:g} mm", "pass" if even else "fail",
                                 "" if even else "the body is not one sheet thickness", src))
            st = "pass" if r >= L["bend_r_x_t"] * t - 1e-9 else "fail"
            rows.append(_row("Inside bend radius", f"R{r:g}", f">= {L['bend_r_x_t']:g} x t = R{L['bend_r_x_t'] * t:g}",
                             st, "" if st == "pass" else f"use R{L['bend_r_x_t'] * t:g} or more (cracking on the outside)",
                             src))
            if sheet.get("kind") == "strip":
                flats = [p[1] for p in sheet.get("pieces") or [] if p[0] == "flat"]
                short = [f_ for f_ in flats if f_ < L["flange_x_t"] * t]
                rows.append(_row("Flange length", f"shortest {min(flats):.2f} mm (flat)" if flats else "-",
                                 f">= {L['flange_x_t']:g} x t = {L['flange_x_t'] * t:g} mm", "fail" if short else "pass",
                                 f"lengthen {len(short)} flange(s) to {L['flange_x_t'] * t:g} mm" if short else "", src))
            small = [h for h in holes or [] if h["dia"] < L["hole_x_t"] * t]
            rows.append(_row("Hole size", f"smallest Ø{min(h['dia'] for h in holes):g}" if holes else "no holes",
                             f">= {L['hole_x_t']:g} x t = Ø{L['hole_x_t'] * t:g}", "fail" if small else "pass",
                             f"open {len(small)} hole(s) to Ø{t:g} or more" if small else "", src))
            bends = [f for f in _all_cyls(shape) if abs(f["r"] - r) < 0.02 or abs(f["r"] - (r + t)) < 0.02]
            near = []
            need = L["hole_bend_x_t"] * t + r
            for h in holes or []:
                hp = h.get("p3")
                if not hp or not bends:
                    continue
                for b in bends:
                    dist = _dist_axis(hp, b) - (r + t) - h["dia"] / 2
                    if dist < need - 1e-6:
                        near.append(round(dist, 2))
                        break
            rows.append(_row("Hole to bend", f"closest edge {min(near):g} mm" if near else "all clear",
                             f">= {L['hole_bend_x_t']:g} t + R = {need:g} mm", "fail" if near else "pass",
                             "move the hole(s) away from the bend or add a relief cut" if near else "", src))
    elif proc in ("molding", "moulding", "injection", "injection_molding"):
        src = SOURCES["mold"]
        L = {**MOLD, **lim_over}
        pull = {"Z": (0, 0, 1), "X": (1, 0, 0), "Y": (0, 1, 0)}[str(spec.get("pull", "Z")).upper()]
        key = next((k for k in ("abs", "pp", "pc", "nylon", "pom") if k in material), "default")
        lo, hi = L["wall"][key]
        wt = wall_thickness(pr, samples)
        facts["wall"] = wt
        if "error" in wt:
            rows.append(_row("Wall thickness", "-", f"{lo}-{hi} mm", "unverified", "", src))
        else:
            ok = wt["p05"] >= lo and wt["median"] <= hi
            rows.append(_row("Wall thickness", f"5th pct {wt['p05']} / median {wt['median']} / 95th pct {wt['p95']} mm",
                             f"{lo}-{hi} mm for {key if key != 'default' else 'most plastics'}", "pass" if ok else "fail",
                             "" if ok else "core out thick areas / thicken thin ones into the range", src))
            ratio = wt["p95"] / max(wt["p05"], 1e-9)      # percentiles: a ray along a wall is not a thickness
            rows.append(_row("Wall uniformity", f"95th / 5th pct = {ratio:.1f}", f"<= {L['uniform_ratio']:g}",
                             "pass" if ratio <= L["uniform_ratio"] else "review",
                             "" if ratio <= L["uniform_ratio"] else "uneven walls sink and warp: core out the thick parts",
                             src))
        zero, low, tot = 0.0, 0.0, 0.0
        for p, n, a, _fi in samples:
            tot += a
            along = abs(_dot(n, pull))
            draft = math.degrees(math.asin(min(1.0, along)))
            if along < 0.999:                                          # side walls (not faces across the pull)
                if draft < L["draft_deg"]:
                    zero += a
                elif draft < L["draft_good_deg"]:
                    low += a
        rows.append(_row("Draft on side walls", f"{zero / max(tot, 1e-9) * 100:.1f}% of the surface below "
                         f"{L['draft_deg']}°, {low / max(tot, 1e-9) * 100:.1f}% below {L['draft_good_deg']}°",
                         f">= {L['draft_deg']}° (1-2° better; +1° per 0.025 mm texture)",
                         "fail" if zero > 0.01 * tot else ("review" if low > 0.01 * tot else "pass"),
                         "add 1-2° draft to the vertical walls (H: taper the extrude / use a draft angle)" if zero or low
                         else "", src))
        under = 0.0
        for p, n, a, _fi in samples:
            s = _dot(n, pull)
            if abs(s) > 0.999:
                continue
            d = pull if s >= 0 else tuple(-x for x in pull)
            q = (p[0] + n[0] * 1e-3, p[1] + n[1] * 1e-3, p[2] + n[2] * 1e-3)
            if pr.hit(q, d) is not None and pr.hit(q, tuple(-x for x in d)) is not None:
                under += a
        rows.append(_row("Undercuts", f"{under / max(tot, 1e-9) * 100:.1f}% of the surface hidden from both mould "
                         "halves", "0% for a simple 2-part mould", "review" if under > 0.005 * tot else "pass",
                         "needs a side action / lifter (more tool cost) or a redesign" if under > 0.005 * tot else "", src))
        proj = _projected_area(shape, pull)
        tons = proj * L["cavity_mpa"] / 9806.65
        facts["projected_mm2"] = proj
        rows.append(_row("Clamp force (estimate)", f"projected {proj:,.0f} mm² -> ~{tons:.1f} t at {L['cavity_mpa']:g} MPa",
                         "the press must exceed it", "review", "ask the moulder for their cavity pressure", src))
    else:
        raise ValueError(f"process '{proc}' nahi (fdm / sla / sls / mjf / metal_pbf / cnc / sheet / molding)")
    fails = [r_ for r_ in rows if r_["status"] == "fail"]
    return {"process": proc, "rows": rows, "facts": facts, "fails": len(fails),
            "reviews": len([r_ for r_ in rows if r_["status"] == "review"]),
            "note": "Measured on the model; limits are published starting points - her shop's numbers override them."}


# ---------------------------------------------------------------- helpers
def _all_cyls(shape) -> list[dict]:
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    out = []
    for f in shape.Faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() != GeomAbs_Cylinder:
            continue
        c = ad.Cylinder()
        ax = c.Axis()
        out.append({"r": c.Radius(), "p": (ax.Location().X(), ax.Location().Y(), ax.Location().Z()),
                    "d": (ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()), "face": f})
    return out


def _concave_cyls(shape) -> list[dict]:
    """Inside fillets: cylinders whose normal points to the axis but that are not holes (span < 360°)."""
    out = []
    for c in _all_cyls(shape):
        f = c["face"]
        u0, u1, v0, v1 = f._uvBounds()
        if u1 - u0 > 2 * math.pi - 1e-3:
            continue
        n, p = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        rel = (p.x - c["p"][0], p.y - c["p"][1], p.z - c["p"][2])
        t = _dot(rel, c["d"])
        rad = (rel[0] - t * c["d"][0], rel[1] - t * c["d"][1], rel[2] - t * c["d"][2])
        if _dot(rad, (n.x, n.y, n.z)) < 0:
            out.append(c)
    return out


def _dist_axis(p, cyl) -> float:
    rel = (p[0] - cyl["p"][0], p[1] - cyl["p"][1], p[2] - cyl["p"][2])
    t = _dot(rel, cyl["d"])
    return math.dist(rel, (t * cyl["d"][0], t * cyl["d"][1], t * cyl["d"][2]))


def _projected_area(shape, pull) -> float:
    """Area of the part's shadow along the pull direction (faces facing the pull, overlapping counted once)."""
    import numpy as np
    vv, tt = shape.tessellate(max(shape.BoundingBox().DiagonalLength / 400, 0.05), 0.2)
    V = np.array([(v.x, v.y, v.z) for v in vv])
    d = np.array(pull, float)
    a = np.cross(d, [1, 0, 0] if abs(d[0]) < 0.9 else [0, 1, 0])
    a /= np.linalg.norm(a)
    b = np.cross(d, a)
    P = np.stack([V @ a, V @ b], 1)
    T = np.array(tt)
    lo, hi = P.min(0), P.max(0)
    res = max((hi - lo).max() / 400, 0.05)
    nx, ny = int((hi[0] - lo[0]) / res) + 2, int((hi[1] - lo[1]) / res) + 2
    grid = np.zeros((nx, ny), bool)
    for t in T:
        p0, p1, p2 = P[t]
        x0, y0 = np.floor((np.minimum(np.minimum(p0, p1), p2) - lo) / res).astype(int)
        x1, y1 = np.ceil((np.maximum(np.maximum(p0, p1), p2) - lo) / res).astype(int)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), indexing="ij")
        cx, cy = lo[0] + (gx + 0.5) * res, lo[1] + (gy + 0.5) * res
        den = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
        if abs(den) < 1e-12:
            continue
        w1 = ((p1[1] - p2[1]) * (cx - p2[0]) + (p2[0] - p1[0]) * (cy - p2[1])) / den
        w2 = ((p2[1] - p0[1]) * (cx - p2[0]) + (p0[0] - p2[0]) * (cy - p2[1])) / den
        m = (w1 >= 0) & (w2 >= 0) & (1 - w1 - w2 >= 0)
        grid[gx[m].clip(0, nx - 1), gy[m].clip(0, ny - 1)] = True
    return float(grid.sum() * res * res)


def _setups(reach) -> dict[str, Any]:
    """Greedy set cover: the fewest approach directions that reach every reachable sample (area weighted)."""
    tot = sum(a for a, _f, _ok in reach) or 1.0
    left = [(a, set(ok)) for a, _f, ok in reach if ok]
    unreach = sum(a for a, _f, ok in reach if not ok)
    chosen = []
    while left:
        cand = {}
        for a, ok in left:
            for d in ok:
                cand[d] = cand.get(d, 0.0) + a
        best = max(cand, key=cand.get)
        chosen.append(best)
        left = [(a, ok) for a, ok in left if best not in ok]
    return {"count": len(chosen), "dirs": chosen, "unreachable_pct": round(100 * unreach / tot, 1)}
