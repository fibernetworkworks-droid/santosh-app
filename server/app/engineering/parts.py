"""v0.362 HOOLA CAD PRO: the standard-parts helper library a CAD script gets as `H` (pure CadQuery + math, runs inside
the locked box). Sizes come from the ISO / DIN tables engineers use; anything not in a table is refused with a plain
reason instead of being invented.

Holes:      H.hole(m, kind)            clearance / tap / cbore / csk diameters (ISO 273 medium, ISO 4762, ISO 10642)
            H.cbore(wp, m, depth=None) counterbored hole for a socket cap screw on the selected face's workplane
            H.csk(wp, m)               countersunk hole for a flat head screw
Fasteners:  H.socket_screw(m, l)       ISO 4762 socket head cap screw (simplified: head + hex socket + shank)
            H.hex_bolt(m, l)           ISO 4014 / 4017 hex head bolt (simplified)
            H.nut(m)                   ISO 4032 hex nut           H.washer(m)  ISO 7089 plain washer
Motion:     H.spur_gear(module, teeth, width, bore=0, pressure_angle=20)   true involute teeth
            H.bearing(code)            deep-groove ball bearing envelope (6000-6010, 6200-6210, 608, 625, 626)
            H.shaft(d, length, keyway=False)   shaft with an optional DIN 6885 keyway
Profiles:   H.extrusion(size, length)  aluminium T-slot profile 2020 / 2040 / 3030 / 4040 (outline, slots, centre bore)
            H.pipe(od, wall, length)   H.flange(od, id, thickness, bolts, bolt_circle, bolt_hole)
Threads:    H.thread_note(m) the drawing note. v0.365 REAL threads: H.thread(m, length) threaded rod (ISO 68-1 profile,
            helical sweep) and H.thread_tool(m, length) the solid to CUT for a modelled internal thread. Slow (~3-10 s each):
            only when the thread itself matters (3D print, a screw model); else keep the plain hole + note.
Sheet:      v0.365 H.sheet(segments, width, t, r=None, k=0.44) bent sheet part from a press-brake profile
            [(length, bend_deg), ..., (length, 0)] -> the folded solid; its flat length / pattern go to flat.dxf.
            H.tray(l, w, h, t, r=None, k=0.44) a 4-flange tray / box with corner reliefs + its flat pattern.
Freeform:   v0.365 H.smooth_loft(sections) a smooth B-spline body through [(z, width, depth, roundness 0..1, dx, dy), ...]
            (grips, handles, bottles, nozzles, ducts); H.spline_sweep(points, radius) a round tube along a 3-D spline.
Checks:     v0.365 H.expect(...) her numbers as checks the box measures on the result (size, hole count / diameter,
            volume, wall); H.analyze(...) FEA after the build; H.cam(...) CNC G-code after the build. See the guide.
"""
from __future__ import annotations

import math

import cadquery as cq

# metric coarse: (pitch, tap drill, clearance medium, cbore dia, cbore depth (head h), csk dia, head_dia, head_h,
#                 hex key, nut s (across flats), nut m (height), washer od, washer h)
METRIC = {
    2: (0.40, 1.6, 2.4, 4.4, 2.2, 4.4, 3.8, 2.0, 1.5, 4.0, 1.6, 5.0, 0.3),
    2.5: (0.45, 2.05, 2.9, 5.4, 2.7, 5.5, 4.5, 2.5, 2.0, 5.0, 2.0, 6.0, 0.5),
    3: (0.50, 2.5, 3.4, 6.5, 3.3, 6.72, 5.5, 3.0, 2.5, 5.5, 2.4, 7.0, 0.5),
    4: (0.70, 3.3, 4.5, 8.0, 4.4, 8.96, 7.0, 4.0, 3.0, 7.0, 3.2, 9.0, 0.8),
    5: (0.80, 4.2, 5.5, 10.0, 5.4, 11.2, 8.5, 5.0, 4.0, 8.0, 4.7, 10.0, 1.0),
    6: (1.00, 5.0, 6.6, 11.0, 6.5, 13.44, 10.0, 6.0, 5.0, 10.0, 5.2, 12.0, 1.6),
    8: (1.25, 6.8, 9.0, 15.0, 8.6, 17.92, 13.0, 8.0, 6.0, 13.0, 6.8, 16.0, 1.6),
    10: (1.50, 8.5, 11.0, 18.0, 10.8, 22.4, 16.0, 10.0, 8.0, 16.0, 8.4, 20.0, 2.0),
    12: (1.75, 10.2, 13.5, 20.0, 13.0, 26.88, 18.0, 12.0, 10.0, 18.0, 10.8, 24.0, 2.5),
    16: (2.00, 14.0, 17.5, 26.0, 17.5, 33.6, 24.0, 16.0, 14.0, 24.0, 14.8, 30.0, 3.0),
    20: (2.50, 17.5, 22.0, 33.0, 21.5, 40.32, 30.0, 20.0, 17.0, 30.0, 18.0, 37.0, 3.0),
    24: (3.00, 21.0, 26.0, 40.0, 25.5, 48.0, 36.0, 24.0, 19.0, 36.0, 21.5, 44.0, 4.0),
}
BEARINGS = {  # code: (id, od, width)
    "608": (8, 22, 7), "625": (5, 16, 5), "626": (6, 19, 6),
    "6000": (10, 26, 8), "6001": (12, 28, 8), "6002": (15, 32, 9), "6003": (17, 35, 10), "6004": (20, 42, 12),
    "6005": (25, 47, 12), "6006": (30, 55, 13), "6007": (35, 62, 14), "6008": (40, 68, 15), "6009": (45, 75, 16),
    "6010": (50, 80, 16), "6200": (10, 30, 9), "6201": (12, 32, 10), "6202": (15, 35, 11), "6203": (17, 40, 12),
    "6204": (20, 47, 14), "6205": (25, 52, 15), "6206": (30, 62, 16), "6207": (35, 72, 17), "6208": (40, 80, 18),
    "6209": (45, 85, 19), "6210": (50, 90, 20),
}
# DIN 6885 A: shaft d range -> (key width b, key height h, shaft keyway depth t1)
KEYS = [(6, 8, 2, 2, 1.2), (8, 10, 3, 3, 1.8), (10, 12, 4, 4, 2.5), (12, 17, 5, 5, 3.0), (17, 22, 6, 6, 3.5),
        (22, 30, 8, 7, 4.0), (30, 38, 10, 8, 5.0), (38, 44, 12, 8, 5.0), (44, 50, 14, 9, 5.5), (50, 58, 16, 10, 6.0),
        (58, 65, 18, 11, 7.0), (65, 75, 20, 12, 7.5)]
EXTRUSIONS = {"2020": (20, 6.2, 4.2), "2040": (20, 6.2, 4.2), "3030": (30, 8.2, 6.8), "4040": (40, 8.2, 6.8)}  # side, slot w, bore


def _m(m) -> tuple:
    key = float(m) if float(m) not in (2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 24.0) else int(m)
    if key not in METRIC:
        raise ValueError(f"M{m} table mein nahi (M2, M2.5, M3, M4, M5, M6, M8, M10, M12, M16, M20, M24)")
    return METRIC[key]


def hole(m, kind: str = "clearance") -> float:
    """Diameter in mm: clearance (ISO 273 medium) | tap (tap drill) | cbore (counterbore dia) | csk (countersink dia)."""
    t = _m(m)
    return {"clearance": t[2], "tap": t[1], "cbore": t[3], "csk": t[5]}[kind]


def cbore(wp, m, depth=None):
    t = _m(m)
    return wp.cboreHole(t[2], t[3], t[4] if t[4] else t[7], depth)


def csk(wp, m, depth=None):
    t = _m(m)
    return wp.cskHole(t[2], t[5], 90, depth)


def thread_note(m, length=None) -> str:
    t = _m(m)
    return f"M{m}x{t[0]:g}" + (f" - {length:g} deep" if length else "") + " (tap drill {:g})".format(t[1])


def socket_screw(m, length):
    t = _m(m)
    head = cq.Workplane("XY").circle(t[6] / 2).extrude(t[7])
    head = head.faces(">Z").workplane().polygon(6, t[8] / math.cos(math.pi / 6)).cutBlind(-t[7] * 0.6)
    shank = cq.Workplane("XY").circle(float(m) / 2).extrude(-length)
    return head.union(shank)


def hex_bolt(m, length):
    t = _m(m)
    head = cq.Workplane("XY").polygon(6, t[9] / math.cos(math.pi / 6)).extrude(t[10] * 0.85)
    shank = cq.Workplane("XY").circle(float(m) / 2).extrude(-length)
    return head.union(shank)


def nut(m):
    t = _m(m)
    return (cq.Workplane("XY").polygon(6, t[9] / math.cos(math.pi / 6)).extrude(t[10])
            .faces(">Z").workplane().hole(t[1]))


def washer(m):
    t = _m(m)
    return cq.Workplane("XY").circle(t[11] / 2).circle(t[2] / 2).extrude(t[12])


def _involute_tooth_pts(module, teeth, pa_deg, steps=8):
    """Points (x, y) of one tooth outline (involute flanks, root to tip), centred on +y."""
    pa = math.radians(pa_deg)
    rp = module * teeth / 2
    rb = rp * math.cos(pa)
    ra = rp + module
    rf = max(rp - 1.25 * module, 0.5 * rb)
    def inv(a):
        return math.tan(a) - a
    # half tooth angle at the pitch circle (tooth thickness = pi*m/2)
    half_p = math.pi / (2 * teeth) + inv(pa)
    flank = []
    r_start = max(rb, rf)
    for i in range(steps + 1):
        r = r_start + (ra - r_start) * i / steps
        a = math.acos(min(1.0, rb / r))
        th = half_p - inv(a)
        flank.append((r, th))
    right = [(r * math.sin(th), r * math.cos(th)) for r, th in flank]
    left = [(-x, y) for x, y in reversed(right)]
    root_r = rf
    root_th = half_p + math.pi / (2 * teeth) * 0.5
    start = (root_r * math.sin(root_th), root_r * math.cos(root_th))
    end = (-start[0], start[1])
    return [start] + right + left + [end], rf


def spur_gear(module, teeth, width, bore=0.0, pressure_angle=20.0):
    """True involute spur gear, pitch diameter = module x teeth. Raises for teeth < 8."""
    teeth = int(teeth)
    if teeth < 8:
        raise ValueError("gear ke kam se kam 8 daante")
    tooth, rf = _involute_tooth_pts(module, teeth, pressure_angle)
    pts = []
    for k in range(teeth):
        a = 2 * math.pi * k / teeth          # counter-clockwise, the same way each tooth is drawn
        ca, sa = math.cos(a), math.sin(a)
        pts += [(x * ca - y * sa, x * sa + y * ca) for x, y in tooth]
    g = cq.Workplane("XY").polyline(pts).close().extrude(width)
    if bore:
        g = g.faces(">Z").workplane().hole(bore)
    return g


def bearing(code):
    code = str(code)
    if code not in BEARINGS:
        raise ValueError(f"bearing {code} table mein nahi ({', '.join(BEARINGS)})")
    d, D, b = BEARINGS[code]
    ring = (D - d) / 2
    outer = cq.Workplane("XY").circle(D / 2).circle(D / 2 - ring * 0.3).extrude(b)
    inner = cq.Workplane("XY").circle(d / 2 + ring * 0.3).circle(d / 2).extrude(b)
    return outer.union(inner)


def shaft(d, length, keyway=False, key_length=None):
    s = cq.Workplane("XY").circle(d / 2).extrude(length)
    if keyway:
        row = next((k for k in KEYS if k[0] < d <= k[1]), None)
        if row is None:
            raise ValueError(f"shaft {d} mm ke liye DIN 6885 key table mein nahi (6-75 mm)")
        b, t1 = row[2], row[4]
        kl = key_length or min(length * 0.6, 4 * d)
        cut = cq.Workplane("XY").box(b, t1 * 2, kl).translate((0, d / 2, length / 2))
        s = s.cut(cut)
    return s


def extrusion(size, length):
    size = str(size)
    if size not in EXTRUSIONS:
        raise ValueError(f"extrusion {size} nahi ({', '.join(EXTRUSIONS)})")
    a, slot, bore = EXTRUSIONS[size]
    w = a * (2 if size == "2040" else 1)
    p = cq.Workplane("XY").rect(w, a).extrude(length)
    depth = a * 0.3
    for x in ([0] if w == a else [-a / 2, a / 2]):
        for (dx, dy, rw, rh) in ((x, a / 2 - depth / 2, slot, depth), (x, -a / 2 + depth / 2, slot, depth)):
            p = p.cut(cq.Workplane("XY").center(dx, dy).rect(rw, rh).extrude(length))
        p = p.cut(cq.Workplane("XY").center(x, 0).circle(bore / 2).extrude(length))
    for sx in (w / 2 - depth / 2, -w / 2 + depth / 2):
        p = p.cut(cq.Workplane("XY").center(sx, 0).rect(depth, slot).extrude(length))
    return p


def pipe(od, wall, length):
    return cq.Workplane("XY").circle(od / 2).circle(od / 2 - wall).extrude(length)


def flange(od, id, thickness, bolts=4, bolt_circle=None, bolt_hole=None):
    bc = bolt_circle or (od + id) / 2
    bh = bolt_hole or max(4.0, (od - id) / 6)
    f = cq.Workplane("XY").circle(od / 2).circle(id / 2).extrude(thickness)
    return f.faces(">Z").workplane().polarArray(bc / 2, 0, 360, int(bolts)).hole(bh)


# ---------------------------------------------------------------- v0.365 real threads
# A helical sweep + boolean union failed on about 1 size in 5 in OpenCASCADE (empty or broken solids, measured on
# M3-M24 x 6-30 mm). So a thread is built as an exact FACETED surface instead: radius r(theta, z) from the ISO 68-1
# profile on a fine grid, sewn into one closed solid - no boolean, valid every time, and cutting it from a part (a
# tapped hole) is a boolean between flat faces, which OCC does reliably.
def _iso_r(u, p, ri, ro):
    u %= p
    wc, wr = p / 8, p / 4
    fl = (p - wc - wr) / 2
    if u < wc / 2:
        return ro
    if u < wc / 2 + fl:
        return ro - (ro - ri) * (u - wc / 2) / fl
    if u < wc / 2 + fl + wr:
        return ri
    if u < wc / 2 + 2 * fl + wr:
        return ri + (ro - ri) * (u - wc / 2 - fl - wr) / fl
    return ro


def _faceted_thread(ri, ro, p, length, nt=48):
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeSolid,
                                    BRepBuilderAPI_Sewing)
    from OCP.gp import gp_Pnt
    from OCP.TopoDS import TopoDS
    nz = max(2, min(360, int(math.ceil(length / (p / 8)))))
    zs = [length * j / nz for j in range(nz + 1)]
    P = [[gp_Pnt(*(lambda r, th: (r * math.cos(th), r * math.sin(th), z))(
        _iso_r(z - p * (2 * math.pi * i / nt) / (2 * math.pi), p, ri, ro), 2 * math.pi * i / nt)) for i in range(nt)]
         for z in zs]
    sew = BRepBuilderAPI_Sewing(1e-6)

    def face(*pts):
        mp = BRepBuilderAPI_MakePolygon()
        for q in pts:
            mp.Add(q)
        mp.Close()
        sew.Add(BRepBuilderAPI_MakeFace(mp.Wire(), True).Face())
    for j in range(nz):
        for i in range(nt):
            a, b, c, d = P[j][i], P[j][(i + 1) % nt], P[j + 1][(i + 1) % nt], P[j + 1][i]
            face(a, b, c)
            face(a, c, d)
    face(*P[0])
    face(*P[nz])
    sew.Perform()
    sol = cq.Solid(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sew.SewedShape())).Solid())
    if sol.Volume() < 0:
        sol = cq.Solid(sol.wrapped.Reversed())
    return cq.Workplane("XY").add(sol.fix())


def _thread_size(m, length, pitch):
    if not (0 < length <= 80):
        raise ValueError("thread length 0-80 mm")
    p = float(pitch or _m(m)[0])
    THREADS[0] += 1
    if THREADS[0] > 6:
        raise ValueError("ek part mein 6 real threads tak (baaki holes + H.thread_note)")
    return p, m / 2 - 5 / 8 * 0.866025 * p, m / 2


THREADS = [0]


def thread(m, length, pitch=None):
    """ISO metric external thread (rod) along +Z from z=0, major diameter m (faceted, ~2-6 s)."""
    p, ri, ro = _thread_size(m, length, pitch)
    return _faceted_thread(ri, ro, p, length)


def thread_tool(m, length, pitch=None):
    """The solid to CUT for an internal (tapped) thread of size m along +Z from z=0: part.cut(tool.translate(...))."""
    p, ri, ro = _thread_size(m, length, pitch)
    return _faceted_thread(ri, ro + 0.05, p, length)


# ---------------------------------------------------------------- v0.365 sheet metal
FLAT: dict = {}


def _ba(angle_deg, r, t, k):
    return math.radians(abs(angle_deg)) * (r + k * t)       # bend allowance (DIN 6935 / K-factor method)


def sheet(segments, width, t, r=None, k=0.44):
    """Press-brake part: segments = [(flange length mm, bend angle deg to the next), ..., (last length, 0)].
    Lengths are OUTSIDE (mould-line) sizes like a drawing; + angle bends up (counter-clockwise seen from -Y).
    Built as the real bent strip (straight flanges + bend arcs of inside radius r), width along Y."""
    r = float(r if r is not None else t)
    if not (0.3 <= t <= 20) or not (1 <= len(segments) <= 12) or width <= 0:
        raise ValueError("sheet: t 0.3-20 mm, 1-12 segments, width > 0")
    segs = [(float(sg[0]), float(sg[1]) if len(sg) > 1 else 0.0) for sg in segments]
    segs[-1] = (segs[-1][0], 0.0)
    sb = [math.tan(math.radians(abs(a)) / 2) * (r + t) for _L, a in segs]
    rm = r + t / 2
    x, z, hd = 0.0, 0.0, 0.0
    wp = cq.Workplane("XZ").moveTo(0, 0)
    flat = 0.0
    pieces = []
    for i, (L, a) in enumerate(segs):
        s_len = L - (sb[i - 1] if i else 0.0) - (sb[i] if a else 0.0)
        pieces.append(["flat", round(s_len, 4)])
        if s_len <= 0.05:
            raise ValueError(f"sheet: flange {i + 1} ({L} mm) bend ke liye chhota hai")
        flat += s_len
        x, z = x + s_len * math.cos(hd), z + s_len * math.sin(hd)
        wp = wp.lineTo(x, z)
        if a:
            sg = 1 if a > 0 else -1
            cx, cz = x - sg * rm * math.sin(hd), z + sg * rm * math.cos(hd)
            h2 = hd + math.radians(a)
            hm = hd + math.radians(a) / 2
            mx, mz = cx + sg * rm * math.sin(hm), cz - sg * rm * math.cos(hm)
            ex, ez = cx + sg * rm * math.sin(h2), cz - sg * rm * math.cos(h2)
            wp = wp.threePointArc((mx, mz), (ex, ez))
            x, z, hd = ex, ez, h2
            flat += _ba(a, r, t, k)
            pieces.append(["bend", round(_ba(a, r, t, k), 4), a])
    path = wp.wire().val()
    prof = cq.Workplane("YZ").center(-width / 2, 0).rect(width, t)
    solid = prof.sweep(cq.Workplane("XZ").add(path), transition="right")
    FLAT["sheet"] = {"kind": "strip", "length": round(flat, 3), "width": float(width), "t": t, "r": r, "k": k,
                     "pieces": pieces,
                     "bends": [{"at": round(sum(sg[0] for sg in segs[:i + 1]), 3), "angle": sg[1]}
                               for i, sg in enumerate(segs) if sg[1]]}
    return solid


def tray(l, w, h, t, r=None, k=0.44):
    """Open box / tray: base l x w (outside), four walls of height h (outside), bends 90 deg, corner reliefs."""
    r = float(r if r is not None else t)
    base = cq.Workplane("XY").box(l, w, t, centered=(True, True, False))
    walls = (cq.Workplane("XY").rect(l, w).rect(l - 2 * t, w - 2 * t).extrude(h))
    body = base.union(walls)
    try:
        body = body.faces("<Z").edges().fillet(min(r + t, h / 2, t * 3) * 0.99)
    except Exception:
        pass
    sb = math.tan(math.radians(45)) * (r + t)
    ba = _ba(90, r, t, k)
    flange = h - sb
    FLAT["sheet"] = {"kind": "tray", "base": [round(l - 2 * sb, 3), round(w - 2 * sb, 3)], "flange": round(flange, 3),
                     "ba": round(ba, 3), "length": round(l - 2 * sb + 2 * (ba + flange), 3),
                     "width": round(w - 2 * sb + 2 * (ba + flange), 3), "t": t, "r": r, "k": k,
                     "relief": round(t + r, 3)}
    return body


# ---------------------------------------------------------------- v0.365 freeform
def _superellipse(wd, dp, roundness, n=48):
    e = 2 + 8 * (1 - max(0.0, min(1.0, roundness)))           # 1 -> ellipse, 0 -> almost a rounded box
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        c, s = math.cos(th), math.sin(th)
        pts.append((wd / 2 * math.copysign(abs(c) ** (2 / e), c), dp / 2 * math.copysign(abs(s) ** (2 / e), s)))
    return pts


def smooth_loft(sections):
    """Smooth B-spline solid through sections [(z, width, depth, roundness=1, dx=0, dy=0), ...] (2-30, z rising)."""
    if not (2 <= len(sections) <= 30):
        raise ValueError("smooth_loft: 2-30 sections")
    wires = []
    for sec in sections:
        z, wd, dp = float(sec[0]), float(sec[1]), float(sec[2])
        rnd = float(sec[3]) if len(sec) > 3 else 1.0
        dx = float(sec[4]) if len(sec) > 4 else 0.0
        dy = float(sec[5]) if len(sec) > 5 else 0.0
        pts = [cq.Vector(px + dx, py + dy, z) for px, py in _superellipse(wd, dp, rnd)]
        wires.append(cq.Wire.makePolygon(pts, close=True) if rnd < 0.05 else
                     cq.Wire.assembleEdges([cq.Edge.makeSpline(pts + [pts[0]], periodic=False)]))
    return cq.Workplane("XY").add(cq.Solid.makeLoft(wires, ruled=False))


def spline_sweep(points, radius):
    """Round tube / handle of `radius` along a smooth 3-D spline through points [(x, y, z), ...]."""
    if len(points) < 2 or len(points) > 40:
        raise ValueError("spline_sweep: 2-40 points")
    vs = [cq.Vector(*map(float, p)) for p in points]
    path = cq.Wire.assembleEdges([cq.Edge.makeSpline(vs)])
    t0 = path.tangentAt(0)
    prof = cq.Workplane(cq.Plane(origin=vs[0], xDir=t0.cross(cq.Vector(0, 0, 1)) if abs(t0.z) < 0.99 else cq.Vector(1, 0, 0),
                                 normal=t0)).circle(radius)
    return prof.sweep(cq.Workplane().add(path), transition="round")


# ---------------------------------------------------------------- v0.365 requests to the box (recorded, run after)
EXPECT: list = []
STUDIES: list = []
CAM: list = []


def expect(**kw):
    """Her numbers as measured checks: size=(x, y, z) [mm, +-tol], holes={'d': 5.5, 'count': 4} (vertical or any axis),
    volume=(lo, hi), min_wall=t, tol=0.5. Several calls allowed."""
    allowed = {"size", "holes", "volume", "tol", "name", "max_size", "solids"}
    bad = set(kw) - allowed
    if bad:
        raise ValueError(f"expect: {', '.join(sorted(bad))} nahi ({', '.join(sorted(allowed))})")
    EXPECT.append(kw)


def analyze(kind="static", **kw):
    """FEA after the build. kind static | thermal | modal. See the guide for fixed / loads / temps / heat / convection."""
    if kind not in ("static", "thermal", "modal", "flow"):
        raise ValueError("analyze kind: static / thermal / modal / flow")
    if kind == "flow" and kw.get("domain") is None:
        raise ValueError("flow: domain=<the FLUID body> chahiye (channel / cavity / box minus the part)")
    if len(STUDIES) >= 3:
        raise ValueError("ek part par 3 analysis tak")
    STUDIES.append({"kind": kind, **kw})


DRAWING: dict = {}
FITS: list = []


def fit(d, code):
    """A toleranced size on the drawing: H.fit(20, 'H7') for a bore, H.fit(20, 'g6') for a shaft (ISO 286)."""
    import re as _re
    if not _re.fullmatch(r"(js|[A-Za-z])\d{1,2}", str(code)):
        raise ValueError("fit like 'H7', 'H8', 'g6', 'h6', 'k6', 'p6', 'js7'")
    if not (0 < float(d) <= 500):
        raise ValueError("fit size 0-500 mm")
    FITS.append({"d": float(d), "fit": str(code)})


def drawing(projection="first", tolerance="m", notes=None, part_no=""):
    """Drawing settings: projection 'first' (India / ISO E, default) or 'third' (US); general tolerance class of
    ISO 2768 ('f' fine, 'm' medium, 'c' coarse, 'v' very coarse); up to 4 extra notes; her part number."""
    if projection not in ("first", "third") or tolerance not in ("f", "m", "c", "v"):
        raise ValueError("drawing: projection first / third, tolerance f / m / c / v")
    DRAWING.update({"projection": projection, "tolerance": tolerance,
                    "notes": [str(n)[:70] for n in (notes or [])][:4], "part_no": str(part_no)[:30]})


def cam(**kw):
    """2.5D CNC G-code after the build: tool_d, stepdown, stepover, feed, plunge, rpm, ops=['face','pocket','drill','profile']."""
    if CAM:
        raise ValueError("ek hi H.cam")
    CAM.append(kw)


class _H:
    """What the script sees as `H` (only these names)."""
    hole = staticmethod(hole)
    cbore = staticmethod(cbore)
    csk = staticmethod(csk)
    thread_note = staticmethod(thread_note)
    socket_screw = staticmethod(socket_screw)
    hex_bolt = staticmethod(hex_bolt)
    nut = staticmethod(nut)
    washer = staticmethod(washer)
    spur_gear = staticmethod(spur_gear)
    bearing = staticmethod(bearing)
    shaft = staticmethod(shaft)
    extrusion = staticmethod(extrusion)
    pipe = staticmethod(pipe)
    flange = staticmethod(flange)
    thread = staticmethod(thread)
    thread_tool = staticmethod(thread_tool)
    sheet = staticmethod(sheet)
    tray = staticmethod(tray)
    smooth_loft = staticmethod(smooth_loft)
    spline_sweep = staticmethod(spline_sweep)
    expect = staticmethod(expect)
    analyze = staticmethod(analyze)
    cam = staticmethod(cam)
    fit = staticmethod(fit)
    drawing = staticmethod(drawing)


H = _H()
