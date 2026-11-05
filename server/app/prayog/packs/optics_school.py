"""Prayogshala kernel pack: SCHOOL OPTICS (NCERT Class 6-10 light).

Four kernels the shared kernels.py does not have, each a real 2-D ray / geometry trace (never the textbook formula
read back):

    shadowbox   a lamp, an opaque object and a screen on one bench: the sharp shadow, the umbra and penumbra of an
                extended filament, and the straight / bent pipe test of rectilinear propagation.
    pinhole     a pinhole camera: the inverted image's height and the blur circle of a finite hole.
    planemirror a plane mirror on a drawing board: the law of reflection by vector reflection, the virtual image
                found where two reflected rays meet, and the images of two inclined mirrors by repeated reflection.
    slabray     a rectangular glass slab: Snell's law in vector form at both faces, the angle of refraction, the
                angle of emergence and the lateral displacement.

Everything is SI, deterministic (no randomness, no wall clock) and written the SAME way in the JavaScript twin
`app/static/prayog/packs/optics_school.js`, so both give the same numbers.
"""
from __future__ import annotations

import math
from typing import Any

R2D = 180.0 / math.pi


# ------------------------------------------------------------------------------------------------ small 2-D helpers
def _unit(v: list[float]) -> list[float]:
    L = math.hypot(v[0], v[1])
    return [v[0] / L, v[1] / L] if L > 0 else [0.0, 0.0]


def _refract(d: list[float], nrm: list[float], n1: float, n2: float) -> list[float] | None:
    """Snell in vector form (d, nrm unit, nrm against d). None = total internal reflection."""
    cosi = -(d[0] * nrm[0] + d[1] * nrm[1])
    r = n1 / n2
    k = 1 - r * r * (1 - cosi * cosi)
    if k < 0:
        return None
    ct = math.sqrt(k)
    return [r * d[0] + (r * cosi - ct) * nrm[0], r * d[1] + (r * cosi - ct) * nrm[1]]


def _meet(p1: list[float], d1: list[float], p2: list[float], d2: list[float]) -> list[float] | None:
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-18:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return [p1[0] + t * d1[0], p1[1] + t * d1[1]]


def _ang(d: list[float]) -> float:
    """The angle a direction makes with the normal (the y axis), always positive."""
    return math.atan2(abs(d[0]), abs(d[1]))


def _q6(x: float) -> int:
    return int(math.floor(x * 1e6 + 0.5))


# ------------------------------------------------------------------------------------------------ shadows
class ShadowBox:
    """A lamp at x = 0 (a filament of height s), an opaque object of height h standing at x = a, a screen at x = D.
    The shadow's edge is where the ray from the lamp over the object's top lands on the screen."""

    PARAMS = {"h": 0.06, "a": 0.30, "D": 0.90, "s": 0.004, "bend": 0.0, "tilt": 0.0, "plen": 0.30, "bore": 0.009}
    VARS = ["rays", "shadow", "umbra", "pen", "mag", "see"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _edge(p, y0):
        """Where the ray leaving the filament at height y0 and grazing the object's top (a, h) meets the screen."""
        a, D, h = p["a"], p["D"], p["h"]
        d = _unit([a - 0.0, h - y0])
        return y0 + d[1] / d[0] * D

    @staticmethod
    def _see(p):
        """Can the eye see the lamp down the pipe? A straight pipe accepts 2 bore / length; a bend blocks it."""
        half = 2 * p["bore"] / max(p["plen"], 1e-9)
        return 1.0 if (abs(p["bend"]) <= 2 * p["bore"] / max(p["plen"] / 2, 1e-9) and abs(p["tilt"]) <= half) else 0.0

    @staticmethod
    def view(s, p, cfg=None):
        sharp = ShadowBox._edge(p, 0.0)
        inner = ShadowBox._edge(p, p["s"] / 2)                 # the ray from the top of the filament
        outer = ShadowBox._edge(p, -p["s"] / 2)                # the ray from the bottom of the filament
        rays = [{"p": [[0.0, 0.0], [p["a"], p["h"]], [p["D"], sharp]], "v": 0},
                {"p": [[0.0, 0.0], [p["D"], 0.0]], "v": 0}]
        return {"rays": rays, "shadow": sharp, "umbra": inner, "pen": outer - inner,
                "mag": p["D"] / p["a"], "see": ShadowBox._see(p)}

    @staticmethod
    def measure(p, cfg=None):
        v = ShadowBox.view(None, p)
        return {"shadow": v["shadow"], "umbra": v["umbra"], "pen": v["pen"], "see": v["see"]}


# ------------------------------------------------------------------------------------------------ pinhole camera
class Pinhole:
    """An object of height h at distance u in front of a pinhole of diameter dp; the screen is v behind it.
    Every ray that gets through passes the hole, so the image is inverted and v/u times the object."""

    PARAMS = {"h": 0.09, "u": 0.60, "v": 0.15, "dp": 0.0015}
    VARS = ["rays", "img_h", "img_y", "blur", "mag", "crisp"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _top(p):
        """The ray from the object's top through the centre of the hole, out to the screen."""
        o = [-p["u"], p["h"]]
        d = _unit([0.0 - o[0], 0.0 - o[1]])
        return [p["v"], d[1] / d[0] * p["v"]]

    @staticmethod
    def view(s, p, cfg=None):
        top = Pinhole._top(p)
        blur = p["dp"] * (p["u"] + p["v"]) / p["u"]
        img = abs(top[1])
        rays = [{"p": [[-p["u"], p["h"]], [0.0, 0.0], top], "v": 0},
                {"p": [[-p["u"], 0.0], [0.0, 0.0], [p["v"], 0.0]], "v": 0}]
        return {"rays": rays, "img_h": img, "img_y": top[1], "blur": blur, "mag": p["v"] / p["u"],
                "crisp": img / (img + blur) if img + blur > 0 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        v = Pinhole.view(None, p)
        return {"img_h": v["img_h"], "blur": v["blur"], "mag": v["mag"]}


# ------------------------------------------------------------------------------------------------ plane mirrors
class PlaneMirror:
    """A plane mirror lying along the x axis of the drawing board, its silvered face towards +y.
    A ray strikes the pole at i to the normal; a point object sits d in front; a second mirror stands at theta."""

    PARAMS = {"i": 0.5236, "d": 0.09, "theta": 1.0472, "sep": 0.02}
    VARS = ["rays", "r", "img_y", "img", "N"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _reflect(d, nrm):
        dot = d[0] * nrm[0] + d[1] * nrm[1]
        return [d[0] - 2 * dot * nrm[0], d[1] - 2 * dot * nrm[1]]

    @staticmethod
    def _ray(p, L=0.14):
        """The incident and reflected legs of one ray at the pole (0, 0)."""
        d = _unit([math.sin(p["i"]), -math.cos(p["i"])])
        rd = PlaneMirror._reflect(d, [0.0, 1.0])
        return [[-L * d[0], -L * d[1]], [0.0, 0.0], [L * rd[0], L * rd[1]]], rd

    @staticmethod
    def _image(p):
        """Where two rays from the object, reflected by the mirror, appear to come from (behind the mirror)."""
        o = [0.0, p["d"]]
        out = []
        for sx in (-p["sep"], p["sep"]):
            hit = [sx, 0.0]
            d = _unit([hit[0] - o[0], hit[1] - o[1]])
            out.append((hit, PlaneMirror._reflect(d, [0.0, 1.0])))
        return _meet(out[0][0], out[0][1], out[1][0], out[1][1])

    @staticmethod
    def _images_in_wedge(p):
        """Two mirrors at theta, the object on the bisector: reflect it in both mirrors again and again and count
        the distinct images (the orbit of the point). For theta = 360/k this is k - 1, the school's formula."""
        th = p["theta"]
        c2, s2 = math.cos(2 * th), math.sin(2 * th)
        start = [p["d"] * math.cos(th / 2), p["d"] * math.sin(th / 2)]
        pts = [start]
        seen = {(_q6(start[0]), _q6(start[1]))}
        i = 0
        while i < len(pts) and len(pts) < 200:
            q = pts[i]
            i += 1
            for nxt in ([q[0], -q[1]],                                   # mirror A: along the x axis
                        [c2 * q[0] + s2 * q[1], s2 * q[0] - c2 * q[1]]):  # mirror B: along theta
                k = (_q6(nxt[0]), _q6(nxt[1]))
                if k not in seen:
                    seen.add(k)
                    pts.append(nxt)
        return float(len(pts) - 1)

    @staticmethod
    def view(s, p, cfg=None):
        legs, rd = PlaneMirror._ray(p)
        img = PlaneMirror._image(p) or [0.0, 0.0]
        rays = [{"p": legs, "v": 0},
                {"p": [[0.0, 0.0], [0.0, 0.06]], "v": 1},
                {"p": [[0.0, p["d"]], [img[0], img[1]]], "v": 1}]
        return {"rays": rays, "r": _ang(rd), "img_y": img[1], "img": abs(img[1]),
                "N": PlaneMirror._images_in_wedge(p)}

    @staticmethod
    def measure(p, cfg=None):
        v = PlaneMirror.view(None, p)
        return {"r": v["r"], "img": v["img"], "N": v["N"]}


# ------------------------------------------------------------------------------------------------ glass slab
class SlabRay:
    """A rectangular glass slab of thickness t and refractive index n, its top face on y = 0. A ray strikes the top
    face at the origin at i to the normal; Snell's law is applied in vector form at both faces."""

    PARAMS = {"t": 0.05, "n": 1.5168, "i": 0.5236, "w": 0.09}
    VARS = ["rays", "r", "e", "shift", "tir"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _trace(p):
        d0 = _unit([math.sin(p["i"]), -math.cos(p["i"])])
        d1 = _refract(d0, [0.0, 1.0], 1.0, p["n"])
        if d1 is None or d1[1] >= 0:
            return None
        hit = [d1[0] / -d1[1] * p["t"], -p["t"]]
        d2 = _refract(d1, [0.0, -1.0], p["n"], 1.0)
        if d2 is None:
            return None
        return d0, d1, hit, d2

    @staticmethod
    def view(s, p, cfg=None):
        tr = SlabRay._trace(p)
        if tr is None:
            return {"rays": [], "r": 0.0, "e": 0.0, "shift": 0.0, "tir": 1.0}
        d0, d1, hit, d2 = tr
        L = 0.07
        rays = [{"p": [[-L * d0[0], -L * d0[1]], [0.0, 0.0], hit, [hit[0] + L * d2[0], hit[1] + L * d2[1]]], "v": 0},
                {"p": [[0.0, 0.0], [L * d0[0], L * d0[1]]], "v": 1}]
        shift = abs(d0[0] * hit[1] - d0[1] * hit[0])
        return {"rays": rays, "r": _ang(d1), "e": _ang(d2), "shift": shift, "tir": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        v = SlabRay.view(None, p)
        return {"r": v["r"], "e": v["e"], "shift": v["shift"]}


KERNELS: dict[str, Any] = {"shadowbox": ShadowBox, "pinhole": Pinhole, "planemirror": PlaneMirror, "slabray": SlabRay}
FAMILY = {"shadowbox": "optics", "pinhole": "optics", "planemirror": "optics", "slabray": "optics"}

# ------------------------------------------------------------------------------------------------ textbook formulas
TEXTBOOK = {
    "shadow_h": lambda p: p["h"] * p["D"] / p["a"],
    "shadow_pen": lambda p: p["s"] * (p["D"] - p["a"]) / p["a"],
    "pinhole_h": lambda p: p["h"] * p["v"] / p["u"],
    "planemirror_r": lambda p: p["i"],
    "planemirror_img": lambda p: p["d"],
    "incl_N": lambda p: 360.0 / (p["theta"] * R2D) - 1.0,
    "slabray_r": lambda p: math.asin(math.sin(p["i"]) / p["n"]),
    "slabray_shift": lambda p: p["t"] * math.sin(p["i"] - math.asin(math.sin(p["i"]) / p["n"]))
                               / math.cos(math.asin(math.sin(p["i"]) / p["n"])),
}


# ------------------------------------------------------------------------------------------------ results from a table
def _rows(rows, keys):
    out = []
    for r in rows or []:
        vals = []
        ok = True
        for k in keys:
            v = r.get(k) if isinstance(r, dict) else None
            try:
                f = float(v)
            except (TypeError, ValueError):
                ok = False
                break
            if not math.isfinite(f):
                ok = False
                break
            vals.append(f)
        if ok:
            out.append(vals)
    return out


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


CALCS = {
    "shadow_h0": {"label": "height of the object", "unit": "m", "needs": ["a", "D", "sh"],
                  "fn": lambda rows, p: _mean([sh * a / D for a, D, sh in _rows(rows, ["a", "D", "sh"]) if D > 0])},
    "pinhole_h0": {"label": "height of the object", "unit": "m", "needs": ["u", "v", "hi"],
                   "fn": lambda rows, p: _mean([hi * u / v for u, v, hi in _rows(rows, ["u", "v", "hi"]) if v > 0])},
    "mirror_law_r": {"label": "r / i", "unit": "", "needs": ["ai", "ar"],
                     "fn": lambda rows, p: _mean([ar / ai for ai, ar in _rows(rows, ["ai", "ar"]) if ai > 0])},
    "incl_360": {"label": "theta x (N + 1)", "unit": "°", "needs": ["th", "nim"],
                 "fn": lambda rows, p: _mean([th * (nim + 1) for th, nim in _rows(rows, ["th", "nim"])])},
    "slabray_n": {"label": "n", "unit": "", "needs": ["ai", "ar"],
                  "fn": lambda rows, p: _mean([math.sin(ai) / math.sin(ar) for ai, ar in _rows(rows, ["ai", "ar"])
                                               if math.sin(ar) > 0])},
}
