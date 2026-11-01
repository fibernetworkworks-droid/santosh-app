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
Threads:    real threads are not modelled (industry practice: STEP carries the hole size, the drawing notes the
            thread); H.thread_note(m) gives the note text for the drawing.
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


H = _H()
