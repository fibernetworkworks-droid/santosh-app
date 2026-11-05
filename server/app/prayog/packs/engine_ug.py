"""Kernel pack `engine_ug`: THREE engines the lab kernels could not build on, each with an exact JavaScript twin in
`app/static/prayog/packs/engine_ug.js` (the test suite runs both and demands the same numbers, so the two files carry
the same formulas step for step).

1. A TWO-ELEMENT RAY TRACER (`eng_lensmirror`, `eng_twolens`, `eng_liquid`)
   One surface-by-surface tracer: every surface is a sphere (or a plane) with a vertex, a signed radius, and a pair of
   refractive indices or a mirror. A ray is refracted with the vector form of Snell's law or reflected at each surface
   in turn, and goes back through the surfaces it has already crossed after a mirror. Nothing here is the thin-lens
   or the mirror formula: the image is where two traced rays meet.
     eng_lensmirror  a convex lens and a convex (or concave) mirror: the mirror is slid until the image of the pin
                     falls on the pin itself, which puts the mirror's centre of curvature on the lens's own image.
     eng_twolens     a convex lens and a concave lens: the real image of the first becomes a virtual object of the
                     second.
     eng_liquid      a liquid layer on a surface: (0) a convex lens lying on a plane mirror with a film of liquid
                     between them, a plano-concave liquid lens; (1) a concave mirror with a liquid poured in, whose
                     flat top refracts the light on the way in and on the way out.

2. AN AC PHASOR / SMALL-SIGNAL ENGINE (`eng_acphasor`, `eng_acsono`)
   A sinusoidal source on R, L and C in series, in parallel (a coil in parallel with a capacitor), or on a coil alone,
   solved as complex impedance. It reports |Z|, the phase angle, the amplitudes across each part, and a time-domain
   trace of the source and the current for the oscilloscope. `measure` FINDS the resonance frequency (the zero of the
   phase), Q and the bandwidth (the half-power points) by searching the response, the way a student does.
   `eng_acsono` is a wire carrying the mains-frequency current in a magnet's field: the force alternates at the
   mains frequency, and the wire answers like a driven damped string.

3. A CLOCKED SEQUENTIAL LOGIC KERNEL (`eng_ff`, `eng_count`, `eng_shift`)
   Gate-level NAND networks stepped in unit gate delays (every gate looks at its inputs as they were one delay ago):
   SR / clocked SR / D / JK / master-slave JK flip-flops, a four-stage ripple counter that shows the carry rippling
   from stage to stage, and a four-bit shift register of edge-triggered D flip-flops. The state is the signals
   on the wires, never a stored truth table, so a level-triggered JK really does race around.

Everything is SI, deterministic (fixed-count bisection, fixed steps, no randomness, no wall clock).
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
TMIN = 1e-9          # a ray never re-hits the surface it is standing on


# ================================================================================================ the surface tracer
def _unit(v: list[float]) -> list[float]:
    L = math.sqrt(v[0] * v[0] + v[1] * v[1])
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


def _surf(vx: float, R: float, nl: float, nr: float, mirror: bool = False) -> dict:
    """A surface with its vertex at x = vx. R is the signed radius (the centre of curvature is at x = vx + R);
    R = 0 is a plane. A refracting surface has index nl on its left and nr on its right; a mirror reflects."""
    return {"vx": vx, "R": R, "nl": nl, "nr": nr, "m": mirror}


def _lens(cx: float, R1: float, R2: float, n: float, d: float) -> list[dict]:
    """A thick lens centred at x = cx: left face R1, right face R2 (signed), centre thickness d, glass index n."""
    return [_surf(cx - d / 2, R1, 1.0, n), _surf(cx + d / 2, R2, n, 1.0)]


def _hit(o: list[float], d: list[float], s: dict) -> float | None:
    """The ray parameter of the hit with a surface: the branch of the sphere nearest the vertex."""
    vx, R = s["vx"], s["R"]
    if R == 0:
        if abs(d[0]) < 1e-15:
            return None
        t = (vx - o[0]) / d[0]
        return t if t > TMIN else None
    cx = vx + R
    ox, oy = o[0] - cx, o[1]
    bq = ox * d[0] + oy * d[1]
    cq = ox * ox + oy * oy - R * R
    disc = bq * bq - cq
    if disc < 0:
        return None
    sq = math.sqrt(disc)
    best = None
    bx = 0.0
    for t in (-bq - sq, -bq + sq):
        if t > TMIN:
            x = o[0] + t * d[0]
            if best is None or abs(x - vx) < abs(bx - vx):
                best, bx = t, x
    return best


def _trace(surfs: list[dict], o: list[float], d: list[float]) -> tuple[list[list[float]], list[float]] | None:
    """Follow a ray from o along d through the surfaces in order, forward first; a mirror turns it round, and it then
    meets the earlier surfaces again, backwards. Returns the points where it touched a surface and its last direction."""
    pts = [[o[0], o[1]]]
    i, step = -1, 1
    n = len(surfs)
    for _ in range(40):
        i += step
        if i < 0 or i >= n:
            break
        s = surfs[i]
        t = _hit(o, d, s)
        if t is None:
            return None
        o = [o[0] + t * d[0], o[1] + t * d[1]]
        pts.append([o[0], o[1]])
        if s["R"] == 0:
            nrm = [-1.0 if d[0] > 0 else 1.0, 0.0]
        else:
            nrm = _unit([o[0] - (s["vx"] + s["R"]), o[1]])
            if nrm[0] * d[0] + nrm[1] * d[1] > 0:
                nrm = [-nrm[0], -nrm[1]]
        if s["m"]:
            dot = d[0] * nrm[0] + d[1] * nrm[1]
            d = [d[0] - 2 * dot * nrm[0], d[1] - 2 * dot * nrm[1]]
            step = -step
        else:
            n1, n2 = (s["nl"], s["nr"]) if step > 0 else (s["nr"], s["nl"])
            d = _refract(d, nrm, n1, n2)
            if d is None:
                return None
    return pts, d


def _image(surfs: list[dict], xo: float, h: float, aim: float = 1e-4) -> list[float] | None:
    """Where the object point (xo, h) is imaged: two rays aimed at the first vertex a hair either side of the axis."""
    x0 = surfs[0]["vx"]
    ra = _trace(surfs, [xo, h], _unit([x0 - xo, aim - h]))
    rb = _trace(surfs, [xo, h], _unit([x0 - xo, -aim - h]))
    if ra is None or rb is None:
        return None
    return _meet(ra[0][-1], ra[1], rb[0][-1], rb[1])


def _sharp(scr: float, img_x: float, ok: bool) -> float:
    """How sharp the image looks on a screen at scr (1 = in focus); a virtual image never forms on a screen."""
    if not ok:
        return 0.0
    q = (scr - img_x) / 0.004
    return 1 / (1 + q * q)


def _draw(surfs: list[dict], xo: float, h: float, aims: list[float], L: float) -> list[dict]:
    """The polylines the 3-D scene draws: rays from the object through the system, the last leg L long."""
    out = []
    x0 = surfs[0]["vx"]
    for a in aims:
        r = _trace(surfs, [xo, h], _unit([x0 - xo, a - h]))
        if r is None:
            continue
        pts, d = r
        end = [pts[-1][0] + L * d[0], pts[-1][1] + L * d[1]]
        out.append({"p": [[q[0], q[1]] for q in pts] + [end], "v": 0})
    return out


def _bisect(f, lo: float, hi: float, n: int = 70) -> float:
    flo = f(lo)
    for _ in range(n):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


# ================================================================================================ lens + mirror
class LensMirror:
    """A biconvex lens centred at x = 0 and a spherical mirror with its pole at x = a, on one axis. The object (a pin
    of height h) is at x = -u. mir = 1 puts the mirror in the beam; mir = 0 takes it away, so the lens alone makes its
    image at v (found on a screen at scr). convex = 1 is a convex mirror (centre of curvature behind it)."""

    PARAMS = {"R": 0.15, "n": 1.5168, "d": 0.003, "u": 0.30, "h": 0.003, "a": 0.08, "Rm": 0.20,
              "convex": 1.0, "mir": 0.0, "scr": 0.28}
    VARS = ["rays", "img_x", "img_y", "coin", "v_lens", "real", "sharp"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _surfs(p, with_mirror):
        sf = _lens(0.0, p["R"], -p["R"], p["n"], p["d"])
        if with_mirror:
            Rs = p["Rm"] if p["convex"] >= 0.5 else -p["Rm"]
            sf.append(_surf(p["a"], Rs, 1.0, 1.0, True))
        return sf

    @staticmethod
    def view(s, p, cfg=None):
        with_m = p["mir"] >= 0.5
        sf = LensMirror._surfs(p, with_m)
        im = _image(sf, -p["u"], p["h"])
        im0 = _image(LensMirror._surfs(p, False), -p["u"], p["h"])
        ok = im is not None
        rim = math.sqrt(max(p["R"] * p["d"] - p["d"] * p["d"] / 4, 0.0)) * 0.8
        rays = _draw(sf, -p["u"], p["h"], [rim, 0.0, -rim], 1.2)
        v_lens = im0[0] if im0 else 0.0
        real0 = bool(im0 and im0[0] > 0)
        if with_m:
            ix, iy = (im[0], im[1]) if ok else (0.0, 0.0)
            coin = ix - (-p["u"]) if ok else 9.0
            real = 1.0 if ok and ix < 0 else 0.0
            sharp = 1 / (1 + (coin / 0.004) * (coin / 0.004)) if ok else 0.0
        else:
            ix, iy = (im0[0], im0[1]) if im0 else (0.0, 0.0)
            coin = 9.0
            real = 1.0 if real0 else 0.0
            sharp = _sharp(p["scr"], ix, real0)
        return {"rays": rays, "img_x": ix, "img_y": iy, "coin": coin, "v_lens": v_lens, "real": real, "sharp": sharp}

    @staticmethod
    def measure(p, cfg=None):
        """What a careful student gets: v from the lens alone, then the mirror position a* where the pin and its
        image coincide (no parallax), then R = v - a* and f = R / 2."""
        q = dict(p, h=0.002, mir=1.0)
        im0 = _image(LensMirror._surfs(q, False), -q["u"], q["h"])
        if im0 is None or im0[0] <= 0.03:
            return {"v": 0.0, "a": 0.0, "R_est": 0.0, "f_est": 0.0}
        v = im0[0]

        def g(a):
            qq = dict(q, a=a)
            im = _image(LensMirror._surfs(qq, True), -qq["u"], qq["h"])
            return (im[0] + qq["u"]) if im else 9.0
        # the mirror comes in from the lens side: the first sign change of the parallax is the coincidence
        a0 = None
        a_prev, g_prev = 0.02, g(0.02)
        k = 1
        while 0.02 + k * 0.002 < v - 0.004:
            a_now = 0.02 + k * 0.002
            g_now = g(a_now)
            if g_prev != 9.0 and g_now != 9.0 and (g_prev > 0) != (g_now > 0):
                a0 = _bisect(g, a_prev, a_now)
                break
            a_prev, g_prev = a_now, g_now
            k += 1
        if a0 is None:
            return {"v": v, "a": 0.0, "R_est": 0.0, "f_est": 0.0}
        return {"v": v, "a": a0, "R_est": v - a0, "f_est": (v - a0) / 2}


# ================================================================================================ two lenses
class TwoLens:
    """A convex lens L1 at x = 0 and a biconcave lens L2 at x = a. The object is at x = -u. mir = 1 puts L2 in the
    beam; mir = 0 takes it out. scr is the screen position (from L1) for the sharpness of the final image."""

    PARAMS = {"R": 0.15, "n": 1.5168, "d": 0.002, "u": 0.30, "h": 0.003, "a": 0.13, "R2": 0.30, "d2": 0.0006,
              "n2": 1.5168, "mir": 0.0, "scr": 0.45}
    VARS = ["rays", "img_x", "img_y", "real", "v1", "sharp"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _surfs(p, with_l2):
        sf = _lens(0.0, p["R"], -p["R"], p["n"], p["d"])
        if with_l2:
            sf += _lens(p["a"], -p["R2"], p["R2"], p["n2"], p["d2"])
        return sf

    @staticmethod
    def view(s, p, cfg=None):
        with_l2 = p["mir"] >= 0.5
        sf = TwoLens._surfs(p, with_l2)
        im = _image(sf, -p["u"], p["h"])
        im0 = _image(TwoLens._surfs(p, False), -p["u"], p["h"])
        rim = math.sqrt(max(p["R"] * p["d"] - p["d"] * p["d"] / 4, 0.0)) * 0.8
        rays = _draw(sf, -p["u"], p["h"], [rim, 0.0, -rim], 1.0)
        v1 = im0[0] if im0 else 0.0
        ix, iy = (im[0], im[1]) if im else (0.0, 0.0)
        # the image counts as real when the rays are still converging as they leave the last lens
        real = bool(im and ix > (p["a"] if with_l2 else 0.0))
        return {"rays": rays, "img_x": ix, "img_y": iy, "real": 1.0 if real else 0.0, "v1": v1,
                "sharp": _sharp(p["scr"], ix, real)}

    @staticmethod
    def measure(p, cfg=None):
        """v1 from the convex lens alone, then the final image with L2 in: u2 = v1 - a (a virtual object) and
        v2 = image - a give f2 = u2 v2 / (u2 - v2), negative for a concave lens."""
        q = dict(p, h=0.002, mir=1.0)
        im0 = _image(TwoLens._surfs(q, False), -q["u"], q["h"])
        im = _image(TwoLens._surfs(q, True), -q["u"], q["h"])
        if im0 is None or im is None:
            return {"v1": 0.0, "v2": 0.0, "f2": 0.0}
        u2, v2 = im0[0] - q["a"], im[0] - q["a"]
        den = u2 - v2
        return {"v1": im0[0], "v2": v2, "f2": (u2 * v2 / den) if abs(den) > 1e-12 else 0.0}


# ================================================================================================ a liquid layer
class Liquid:
    """A liquid layer on a surface. mode 0: a biconvex lens lies on a plane mirror (its lower face touches the mirror
    at the centre) and a film of liquid fills the wedge between them: a plano-concave liquid lens. The pin is H above
    the lens centre. mode 1: a concave mirror (radius R) with liquid poured in, whose flat top is at x = 0 and whose
    pole is a depth t below; the pin is H above the flat top. liq = 1 puts the liquid in; liq = 0 leaves it dry."""

    PARAMS = {"mode": 0.0, "R": 0.15, "n": 1.5168, "d": 0.003, "nl": 1.333, "liq": 0.0, "H": 0.15, "h": 0.003,
              "t": 0.003}
    VARS = ["rays", "img_x", "img_y", "coin", "real"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _surfs(p, liq=None):
        nl = p["nl"] if (p["liq"] >= 0.5 if liq is None else liq) else 1.0
        if p["mode"] < 0.5:
            sf = _lens(0.0, p["R"], -p["R"], p["n"], p["d"])
            sf[1]["nr"] = nl                                  # the lower face now meets the liquid
            sf.append(_surf(p["d"] / 2, 0.0, nl, nl, True))   # the plane mirror under the lens centre
            return sf
        return [_surf(0.0, 0.0, 1.0, nl), _surf(p["t"], -p["R"], nl, nl, True)]

    @staticmethod
    def view(s, p, cfg=None):
        sf = Liquid._surfs(p)
        im = _image(sf, -p["H"], p["h"])
        rays = _draw(sf, -p["H"], p["h"], [0.01, 0.0, -0.01] if p["mode"] < 0.5 else [0.012, 0.0, -0.012], 0.6)
        ok = im is not None
        ix, iy = (im[0], im[1]) if ok else (0.0, 0.0)
        coin = (ix + p["H"]) if ok else 9.0
        return {"rays": rays, "img_x": ix, "img_y": iy, "coin": coin, "real": 1.0 if ok and ix < 0 else 0.0}

    @staticmethod
    def _coincide(p, liq, lo, hi):
        """The pin height at which the pin and its image coincide, found by bisection on the parallax in [lo, hi]."""
        q = dict(p, h=0.002)

        def g(H):
            im = _image(Liquid._surfs(q, liq), -H, q["h"])
            return (im[0] + H) if im else 9.0
        return _bisect(g, lo, hi)

    @staticmethod
    def measure(p, cfg=None):
        """The two pin heights a student reads (dry, then with the liquid) and the refractive index worked out from
        them: mode 0 from 1/F = 1/f1 + 1/f2 with the lens's own glass index known, mode 1 as H(dry) / H(liquid)."""
        if p["mode"] < 0.5:
            Fg = p["R"] / (2 * (p["n"] - 1))
            Hd = Liquid._coincide(p, False, 0.75 * Fg, 1.5 * Fg)
            Hl = Liquid._coincide(p, True, Hd, 3.0 * Hd)        # the liquid lens is concave: F only gets longer
            nl = 1 + 2 * (p["n"] - 1) * (1 - Hd / Hl)
        else:
            Hd = Liquid._coincide(p, False, 0.58 * p["R"], 1.15 * p["R"])
            Hl = Liquid._coincide(p, True, 0.58 * p["R"], 1.15 * p["R"])
            nl = Hd / Hl
        return {"H_dry": Hd, "H_liq": Hl, "nl": nl}


# ================================================================================================ AC phasor engine
def _cmul(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def _cdiv(a, b):
    den = b[0] * b[0] + b[1] * b[1]
    return ((a[0] * b[0] + a[1] * b[1]) / den, (a[1] * b[0] - a[0] * b[1]) / den)


def _cabs(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1])


def _lc(p):
    """The coil's inductance as it stands: L, times kfe when the iron core is in."""
    return p["L"] * (p["kfe"] if p["core"] >= 0.5 else 1.0)


class AcPhasor:
    """A sinusoidal source of amplitude V and frequency f on a network solved as complex impedance (e^{jwt}).
    topo 0: R + coil (r, L) + C in series.   topo 1: Rin in series with [coil (r, L) in parallel with C].
    topo 2: the coil alone (r in series with L).   core = 1 pushes an iron core into the coil, which multiplies its
    inductance by kfe. V is the amplitude of the source. The traces are two cycles."""

    PARAMS = {"topo": 0.0, "V": 6.0, "f": 50.0, "R": 0.0, "L": 0.1, "C": 1e-6, "r": 5.0, "Rin": 0.0, "core": 0.0,
              "kfe": 1.0}
    VARS = ["Zmag", "phi", "I", "Vcoil", "Vx", "VR", "pf", "tt", "vs", "ic", "vx"]
    NS = 200

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _solve(p, f):
        """The phasors at frequency f: total impedance Z, the current I (V is the reference), and the voltages across
        the coil, across the C (or the tank), and across R."""
        w = 2 * PI * f
        V = (p["V"], 0.0)
        Lc = _lc(p)
        zc = (p["r"], w * Lc)
        topo = int(round(p["topo"]))
        if topo == 0:
            zC = (0.0, -1.0 / (w * p["C"])) if p["C"] > 0 else (0.0, 0.0)
            Z = (p["R"] + p["r"] + zC[0], w * Lc + zC[1])
            I = _cdiv(V, Z)
            return Z, I, _cmul(I, zc), _cmul(I, zC), (p["R"] * I[0], p["R"] * I[1])
        if topo == 1:
            zC = (0.0, -1.0 / (w * p["C"]))
            zp = _cdiv(_cmul(zc, zC), (zc[0] + zC[0], zc[1] + zC[1]))
            Z = (p["Rin"] + zp[0], zp[1])
            I = _cdiv(V, Z)
            vp = _cmul(I, zp)
            return Z, I, vp, vp, (p["Rin"] * I[0], p["Rin"] * I[1])
        Z = (p["r"], w * Lc)
        I = _cdiv(V, Z)
        return Z, I, _cmul(I, zc), _cmul(I, zc), (0.0, 0.0)

    @staticmethod
    def view(s, p, cfg=None):
        Z, I, vcoil, vx, vr = AcPhasor._solve(p, p["f"])
        w = 2 * PI * p["f"]
        n = AcPhasor.NS
        T = 1.0 / p["f"]
        tt, vs, ii, vxx = [], [], [], []
        for k in range(n):
            t = 2 * T * k / n
            c, sn = math.cos(w * t), math.sin(w * t)
            tt.append(t)
            vs.append(p["V"] * c)
            ii.append(I[0] * c - I[1] * sn)
            vxx.append(vx[0] * c - vx[1] * sn)
        Zm = _cabs(Z)
        return {"Zmag": Zm, "phi": math.atan2(Z[1], Z[0]), "I": _cabs(I), "Vcoil": _cabs(vcoil), "Vx": _cabs(vx),
                "VR": _cabs(vr), "pf": Z[0] / Zm if Zm > 0 else 0.0, "tt": tt, "vs": vs, "ic": ii, "vx": vxx}

    @staticmethod
    def _peak(ph):
        """The peak of one cycle of a phasor sampled on a fine grid: what a scope's cursor reads."""
        m = 0.0
        n = 2000
        for k in range(n):
            th = 2 * PI * k / n
            y = abs(ph[0] * math.cos(th) - ph[1] * math.sin(th))
            if y > m:
                m = y
        return m

    @staticmethod
    def measure(p, cfg=None):
        topo = int(round(p["topo"]))
        if topo == 2:
            # impedance from the scope: peak V over peak I, then L from Z and the coil's DC resistance
            Z, I, vc, vx, vr = AcPhasor._solve(p, p["f"])
            Zs = AcPhasor._peak((p["V"], 0.0)) / AcPhasor._peak(I)
            w = 2 * PI * p["f"]
            Lest = math.sqrt(max(Zs * Zs - p["r"] * p["r"], 0.0)) / w
            return {"Z": Zs, "L_est": Lest, "f0": 0.0, "Q": 0.0, "bw": 0.0}
        fg = 1.0 / (2 * PI * math.sqrt(_lc(p) * p["C"]))

        def zim(f):
            return AcPhasor._solve(p, f)[0][1]

        def resp(f):
            Z, I = AcPhasor._solve(p, f)[0:2]
            return _cabs(Z) if topo == 1 else _cabs(I)
        # resonance = the frequency at which the current is in phase with the source (the zero of the reactance)
        f0 = _bisect(zim, fg * 0.2, fg * 5.0, 90)
        half = resp(f0) / math.sqrt(2.0)
        fl = _bisect(lambda f: resp(f) - half, f0 / 3.0, f0)
        fh = _bisect(lambda f: resp(f) - half, f0, f0 * 3.0)
        bw = fh - fl
        return {"Z": 0.0, "L_est": 0.0, "f0": f0, "Q": f0 / bw if bw > 0 else 0.0, "bw": bw}


class AcSono:
    """A sonometer wire of linear density mu under tension T = M g, vibrating length l, carrying the current of a
    transformer secondary V (rms, through a rheostat Rh and its own resistance Rw) between the poles of a horse-shoe
    magnet. The force B I w alternates at the mains frequency fm, so the wire is a driven damped string (quality
    factor Q): its amplitude peaks when l is such that the string's natural frequency meets fm. Only the odd modes
    are driven (the magnet is at the middle)."""

    PARAMS = {"mu": 0.00147, "M": 0.5, "l": 0.5, "fm": 49.93, "V": 6.0, "Rh": 5.0, "Rw": 0.1, "B": 0.05,
              "w": 0.03, "Q": 40.0, "g": 9.80665}
    VARS = ["amp", "I", "fn", "T"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _amp(p, l):
        T = p["M"] * p["g"]
        v = math.sqrt(T / p["mu"])
        Z = (p["Rh"] + p["Rw"], 0.0)
        I = _cabs(_cdiv((p["V"] * math.sqrt(2.0), 0.0), Z))          # amplitude of the secondary's current
        F0 = p["B"] * I * p["w"]
        meff = p["mu"] * l / 2
        w = 2 * PI * p["fm"]
        re, im = 0.0, 0.0
        for k in (1, 3):
            wn = k * PI * v / l
            a = wn * wn - w * w
            b = w * wn / p["Q"]
            den = a * a + b * b
            re += a / den
            im += -b / den
        return (F0 / meff) * math.sqrt(re * re + im * im), I, v / (2 * l), T

    @staticmethod
    def view(s, p, cfg=None):
        a, I, fn, T = AcSono._amp(p, p["l"])
        return {"amp": a, "I": I, "fn": fn, "T": T}

    @staticmethod
    def measure(p, cfg=None):
        """Slide the bridge until the wire jumps highest: a scan of l, then the zero of the slope for the top."""
        lo, hi = 0.15, 0.95
        best_l, best_a = lo, -1.0
        for k in range(0, 801):
            l = lo + (hi - lo) * k / 800.0
            a = AcSono._amp(p, l)[0]
            if a > best_a:
                best_a, best_l = a, l
        h = 1e-5

        def slope(l):
            return AcSono._amp(p, l + h)[0] - AcSono._amp(p, l - h)[0]
        l = _bisect(slope, best_l - 0.002, best_l + 0.002, 60)
        T = p["M"] * p["g"]
        return {"l_res": l, "f_est": math.sqrt(T / p["mu"]) / (2 * l)}


# ================================================================================================ gate-level logic
def _nand(*bits: int) -> int:
    for b in bits:
        if not b:
            return 1
    return 0


def _settle(gates, sig, maxt: int = 80):
    """Advance in unit gate delays until nothing changes. Returns (ticks used, settled?)."""
    for t in range(maxt):
        new = []
        for out, ins in gates:
            new.append(_nand(*[sig[i] for i in ins]))
        changed = False
        for k, (out, ins) in enumerate(gates):
            if sig[out] != new[k]:
                changed = True
        if not changed:
            return t, True
        for k, (out, ins) in enumerate(gates):
            sig[out] = new[k]
    return maxt, False


def _ticks(gates, sig, n: int, watch=None, log=None, t0: int = 0):
    """Advance exactly n unit delays; when `watch` is given, log [tick, value] each time watch(sig) changes."""
    last = watch(sig) if watch else None
    for t in range(n):
        new = []
        for out, ins in gates:
            new.append(_nand(*[sig[i] for i in ins]))
        for k, (out, ins) in enumerate(gates):
            sig[out] = new[k]
        if watch:
            w = watch(sig)
            if w != last:
                log.append([t0 + t + 1, w])
                last = w


# ---- flip-flop netlists ------------------------------------------------------------------------------------------
def _ff_gates(kind: int):
    if kind == 0:      # SR latch of two NANDs, active-low inputs Sb and Rb
        return [("Q", ["Sb", "Qb"]), ("Qb", ["Rb", "Q"])]
    if kind == 1:      # clocked RS
        return [("a", ["S", "CK"]), ("b", ["R", "CK"]), ("Q", ["a", "Qb"]), ("Qb", ["b", "Q"])]
    if kind == 2:      # gated D latch
        return [("nd", ["D", "D"]), ("a", ["D", "CK"]), ("b", ["nd", "CK"]), ("Q", ["a", "Qb"]), ("Qb", ["b", "Q"])]
    if kind == 3:      # level-triggered JK
        return [("a", ["J", "CK", "Qb"]), ("b", ["K", "CK", "Q"]), ("Q", ["a", "Qb"]), ("Qb", ["b", "Q"])]
    return [("nck", ["CK", "CK"]),                         # master-slave JK
            ("ma", ["J", "CK", "Qb"]), ("mb", ["K", "CK", "Q"]), ("M", ["ma", "Mb"]), ("Mb", ["mb", "M"]),
            ("sa", ["M", "nck"]), ("sb", ["Mb", "nck"]), ("Q", ["sa", "Qb"]), ("Qb", ["sb", "Q"])]


def _ff_inputs(kind: int, a: int, b: int) -> dict:
    if kind == 0:
        return {"Sb": a, "Rb": b}
    if kind == 1:
        return {"S": a, "R": b}
    if kind == 2:
        return {"D": a}
    return {"J": a, "K": b}


def _ff_signals(kind: int, q: int, a: int, b: int, ck: int) -> dict:
    sig = {"CK": ck, "Q": q, "Qb": 1 - q}
    sig.update(_ff_inputs(kind, a, b))
    for out, ins in _ff_gates(kind):
        if out not in sig:
            sig[out] = 1
    if kind == 4:
        sig["M"], sig["Mb"] = q, 1 - q
    return sig


class FlipFlop:
    """One flip-flop wired from NAND gates, kind: 0 SR latch (inputs active low), 1 clocked RS, 2 gated D latch,
    3 level-triggered JK, 4 master-slave JK. a is S / J / D / Sb, b is R / K / Rb. A clock pulse is CK high for tw gate
    delays and then low. q0 is the state the circuit starts in."""

    PARAMS = {"kind": 1.0, "a": 0.0, "b": 0.0, "q0": 0.0, "tw": 24.0}
    VARS = ["Q", "Qb", "osc", "toggles", "a_n", "b_n", "M", "ck"]

    @staticmethod
    def init(p, cfg=None):
        kind = int(round(p["kind"]))
        a = 1 if kind == 0 else int(round(p["a"]))
        b = 1 if kind == 0 else int(round(p["b"]))
        sig = _ff_signals(kind, int(round(p["q0"])), a, b, 0)
        _settle(_ff_gates(kind), sig)
        return {"t": 0.0, "sig": sig, "toggles": 0, "osc": 0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def force(s, p, q):
        """Preset (q = 1) or clear (q = 0) the stored bit: the direct set / reset line of the real chips."""
        kind = int(round(p["kind"]))
        sg = s["sig"]
        sg["Q"], sg["Qb"] = q, 1 - q
        if kind == 4:
            sg["M"], sg["Mb"] = q, 1 - q
        _settle(_ff_gates(kind), sg)

    @staticmethod
    def drive(s, p, a, b):
        """Set the data inputs (the clock stays where it is) and let the gates settle."""
        kind = int(round(p["kind"]))
        s["sig"].update(_ff_inputs(kind, int(a), int(b)))
        t, ok = _settle(_ff_gates(kind), s["sig"])
        s["osc"] = 0 if ok else 1
        return ok

    @staticmethod
    def clock(s, p):
        """One clock pulse: CK high for tw delays, then low until the gates settle. Counts how often Q flipped."""
        kind = int(round(p["kind"]))
        g = _ff_gates(kind)
        sg = s["sig"]
        tw = int(round(p["tw"]))
        log: list = []
        sg["CK"] = 1
        _ticks(g, sg, tw, lambda x: x["Q"], log, 0)
        sg["CK"] = 0
        t, ok = _settle(g, sg)
        s["osc"] = 0 if ok else 1
        s["toggles"] = len(log)
        return {"toggles": len(log), "settled": 1.0 if ok else 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        sg = s["sig"]
        kind = int(round(p["kind"]))
        a = {0: "Sb", 1: "S", 2: "D", 3: "J", 4: "J"}[kind]
        b = {0: "Rb", 1: "R", 2: "D", 3: "K", 4: "K"}[kind]
        return {"Q": float(sg["Q"]), "Qb": float(sg["Qb"]), "osc": float(s.get("osc", 0)),
                "toggles": float(s.get("toggles", 0)), "a_n": float(sg[a]), "b_n": float(sg[b]),
                "M": float(sg.get("M", sg["Q"])), "ck": float(sg["CK"])}

    @staticmethod
    def _valid(kind, a, b):
        if kind == 0:
            return not (a == 0 and b == 0)
        if kind in (1, 3):
            return not (a == 1 and b == 1)
        return True

    @staticmethod
    def measure(p, cfg=None):
        """The circuit's own characteristic table: every (input, input, Q) combination, one clock pulse each, read as
        one binary number (the combinations with no defined answer, such as S = R = 1, count as 0)."""
        kind = int(round(p["kind"]))
        sig = 0
        idx = 0
        for a in (0, 1):
            for b in (0, 1):
                for q0 in (0, 1):
                    if not (kind == 2 and b == 1) and FlipFlop._valid(kind, a, b):
                        q = dict(p, a=float(a), b=float(b), q0=float(q0))
                        st = FlipFlop.init(q)
                        FlipFlop.drive(st, q, a, b)
                        if kind != 0:
                            FlipFlop.clock(st, q)
                        sig += st["sig"]["Q"] * (2 ** idx)
                    idx += 1
        return {"sig": float(sig)}


# ---- ripple counter ----------------------------------------------------------------------------------------------
def _count_gates(nst: int, down: int):
    gates = []
    for k in range(nst):
        c = "CK" if k == 0 else ("Q%d" % (k - 1) if not down else "Qb%d" % (k - 1))
        P = "%d" % k
        gates += [("nck" + P, [c, c]),
                  ("ma" + P, ["J", c, "Qb" + P]), ("mb" + P, ["J", c, "Q" + P]),
                  ("M" + P, ["ma" + P, "Mb" + P]), ("Mb" + P, ["mb" + P, "M" + P]),
                  ("sa" + P, ["M" + P, "nck" + P]), ("sb" + P, ["Mb" + P, "nck" + P]),
                  ("Q" + P, ["sa" + P, "Qb" + P]), ("Qb" + P, ["sb" + P, "Q" + P])]
    return gates


def _count_word(sig, nst: int) -> int:
    return sum(sig["Q%d" % k] * (1 << k) for k in range(nst))


class Counter:
    """A four-stage ripple counter of master-slave JK flip-flops, each with J = K = 1 and clocked by the previous
    stage (Q for an up counter, Q-bar for a down counter). The carry ripples: every stage waits for the one before."""

    PARAMS = {"down": 0.0, "tw": 40.0, "tl": 60.0}
    VARS = ["word", "Q0", "Q1", "Q2", "Q3", "ripple", "glitch", "ck"]
    NST = 4

    @staticmethod
    def _reset_sig(p):
        sig = {"CK": 0, "J": 1}
        for k in range(Counter.NST):
            P = "%d" % k
            sig.update({"Q" + P: 0, "Qb" + P: 1, "M" + P: 0, "Mb" + P: 1})
            for nm in ("nck", "ma", "mb", "sa", "sb"):
                sig[nm + P] = 1
        _settle(_count_gates(Counter.NST, int(round(p["down"]))), sig)
        return sig

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "sig": Counter._reset_sig(p), "events": [], "n": 0, "start": 0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def reset(s, p):
        s["sig"] = Counter._reset_sig(p)
        s["events"] = []
        s["n"] = 0
        s["start"] = 0

    @staticmethod
    def clock(s, p):
        """One input pulse. `events` is the list of [gate delay, count] every time the four outputs change, so the
        ripple of the carry is on record."""
        n = Counter.NST
        g = _count_gates(n, int(round(p["down"])))
        sg = s["sig"]
        log: list = []
        s["start"] = _count_word(sg, n)
        sg["CK"] = 1
        _ticks(g, sg, int(round(p["tw"])), lambda x: _count_word(x, n), log, 0)
        sg["CK"] = 0
        _ticks(g, sg, int(round(p["tl"])), lambda x: _count_word(x, n), log, int(round(p["tw"])))
        s["events"] = log
        s["n"] += 1
        return {"events": log, "word": float(_count_word(sg, n))}

    @staticmethod
    def view(s, p, cfg=None):
        sg = s["sig"]
        ev = s.get("events", [])
        word = _count_word(sg, Counter.NST)
        out = {"word": float(word), "ripple": float(len(ev)), "glitch": 0.0, "ck": float(sg["CK"])}
        for k in range(Counter.NST):
            out["Q%d" % k] = float(sg["Q%d" % k])
        if ev:
            first = s.get("start", 0)
            out["glitch"] = float(sum(1 for e in ev[:-1] if e[1] != first and e[1] != word))
        return out

    @staticmethod
    def measure(p, cfg=None):
        """Sixteen input pulses from the cleared counter: after pulse k the word should be (k + 1) mod 16 (up) or
        (-(k + 1)) mod 16 (down). The reading is the sum of (k + 1) x word_k over the sixteen pulses."""
        st = Counter.init(p)
        tot = 0
        for k in range(16):
            Counter.clock(st, p)
            tot += (k + 1) * _count_word(st["sig"], Counter.NST)
        return {"sum": float(tot)}


# ---- shift register ----------------------------------------------------------------------------------------------
def _dff_gates(P: str, d: str, ck: str):
    """A positive-edge-triggered D flip-flop of six NAND gates (the 7474 core)."""
    return [("n1" + P, ["n4" + P, "n2" + P]), ("n2" + P, ["n1" + P, ck]),
            ("n3" + P, ["n2" + P, ck, "n4" + P]), ("n4" + P, ["n3" + P, d]),
            ("Q" + P, ["n2" + P, "Qb" + P]), ("Qb" + P, ["Q" + P, "n3" + P])]


def _shift_gates(nst: int):
    gates = []
    for k in range(nst):
        gates += _dff_gates("%d" % k, "SI" if k == 0 else "Q%d" % (k - 1), "CK")
    return gates


class Shift:
    """A four-bit serial-in shift register: four edge-triggered D flip-flops on one clock, the data input SI into the
    first and each flip-flop's Q into the next. On every rising edge everything moves one place."""

    PARAMS = {"si": 0.0, "word": 11.0, "tw": 30.0}
    VARS = ["word_out", "Q0", "Q1", "Q2", "Q3", "ck", "si"]
    NST = 4

    @staticmethod
    def init(p, cfg=None):
        sig = {"CK": 0, "SI": int(round(p["si"]))}
        for k in range(Shift.NST):
            P = "%d" % k
            sig.update({"Q" + P: 0, "Qb" + P: 1, "n1" + P: 1, "n2" + P: 1, "n3" + P: 1, "n4" + P: 1})
        _settle(_shift_gates(Shift.NST), sig)
        return {"t": 0.0, "sig": sig}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def drive(s, p, si):
        s["sig"]["SI"] = int(si)
        _settle(_shift_gates(Shift.NST), s["sig"])

    @staticmethod
    def clock(s, p):
        g = _shift_gates(Shift.NST)
        sg = s["sig"]
        sg["CK"] = 1
        _ticks(g, sg, int(round(p["tw"])))
        sg["CK"] = 0
        _settle(g, sg)
        return {"word": float(Shift._word(sg))}

    @staticmethod
    def _word(sg):
        return sum(sg["Q%d" % k] * (1 << k) for k in range(Shift.NST))

    @staticmethod
    def view(s, p, cfg=None):
        sg = s["sig"]
        out = {"word_out": float(Shift._word(sg)), "ck": float(sg["CK"]), "si": float(sg["SI"])}
        for k in range(Shift.NST):
            out["Q%d" % k] = float(sg["Q%d" % k])
        return out

    @staticmethod
    def measure(p, cfg=None):
        """Feed the four bits of `word` in, most significant first, one clock each: the register then holds the word
        (the first bit in is now in Q3). The reading is Q0 + 2 Q1 + 4 Q2 + 8 Q3 read back from the wires."""
        st = Shift.init(p)
        w = int(round(p["word"])) & 15
        for k in range(Shift.NST):
            Shift.drive(st, p, (w >> (Shift.NST - 1 - k)) & 1)
            Shift.clock(st, p)
        return {"word": float(Shift._word(st["sig"]))}


KERNELS: dict[str, Any] = {"eng_lensmirror": LensMirror, "eng_twolens": TwoLens, "eng_liquid": Liquid,
                           "eng_acphasor": AcPhasor, "eng_acsono": AcSono, "eng_ff": FlipFlop,
                           "eng_count": Counter, "eng_shift": Shift}
FAMILY = {"eng_lensmirror": "optics", "eng_twolens": "optics", "eng_liquid": "optics", "eng_acphasor": "circuit",
          "eng_acsono": "osc_wave", "eng_ff": "circuit", "eng_count": "circuit", "eng_shift": "circuit"}


# ================================================================================================ textbook formulas
def _ff_next(kind, a, b, q):
    if kind == 0:
        return q if (a and b) else (1 if not a else 0)
    if kind == 1:
        return 1 if a else (q if not b else 0)
    if kind == 2:
        return a
    return (a and (1 - q)) or ((1 - b) and q)


def _ff_sig(p):
    kind = int(round(p["kind"]))
    tot = 0
    idx = 0
    for a in (0, 1):
        for b in (0, 1):
            for q0 in (0, 1):
                if not (kind == 2 and b == 1) and FlipFlop._valid(kind, a, b):
                    tot += int(bool(_ff_next(kind, a, b, q0))) * (2 ** idx)
                idx += 1
    return float(tot)


def _count_sum(p):
    down = int(round(p["down"]))
    tot = 0
    for k in range(16):
        tot += (k + 1) * (((k + 1) % 16) if not down else ((-(k + 1)) % 16))
    return float(tot)


TEXTBOOK = {
    "eng_lensmirror_f": lambda p: p["Rm"] / 2,
    "eng_twolens_f2": lambda p: -p["R2"] / (2 * (p["n2"] - 1)),
    "eng_liquid_nl": lambda p: p["nl"],
    "eng_coil_L": _lc,
    "eng_series_f0": lambda p: 1.0 / (2 * PI * math.sqrt(_lc(p) * p["C"])),
    "eng_series_Q": lambda p: math.sqrt(_lc(p) / p["C"]) / (p["R"] + p["r"]),
    "eng_sono_f": lambda p: p["fm"],
    "eng_ff_sig": _ff_sig,
    "eng_count_sum": _count_sum,
    "eng_shift_word": lambda p: float(int(round(p["word"])) & 15),
}


# ================================================================================================ results from a table
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


def _coil_L(rows, p):
    """L = sqrt(Z^2 - r^2) / (2 pi f), with Z = V / I and r the DC resistance, from the AC readings."""
    vals = []
    for V, I, r in _rows(rows, ["V", "I", "r"]):
        if I > 0 and p["f"] > 0:
            Z = V / I
            vals.append(math.sqrt(max(Z * Z - r * r, 0.0)) / (2 * PI * p["f"]))
    return _mean(vals)


def _sono_f(rows, p):
    """f = (1 / 2l) sqrt(T / mu), the mean over the resonance lengths found."""
    vals = []
    for l, M in _rows(rows, ["l", "M"]):
        if l > 0 and M > 0:
            vals.append(math.sqrt(M * p["g"] / p["mu"]) / (2 * l))
    return _mean(vals)


def _lm_f(rows, p):
    """f of the mirror = (v - a) / 2 from the lens image distance v and the mirror position a."""
    return _mean([(v - a) / 2 for v, a in _rows(rows, ["v", "a"])])


def _tl_f(rows, p):
    """f2 = u2 v2 / (u2 - v2) with u2 = v1 - a and v2 = the final image position xi - a."""
    vals = []
    for v1, a, xi in _rows(rows, ["v1", "a", "xi"]):
        u2, v2 = v1 - a, xi - a
        if abs(u2 - v2) > 1e-9:
            vals.append(u2 * v2 / (u2 - v2))
    return _mean(vals)


def _liq_n(rows, p):
    """mode 0: n = 1 + 2 (n_glass - 1) (1 - H_dry / H_liq);  mode 1: n = H_dry / H_liq."""
    vals = []
    for Hd, Hl in _rows(rows, ["Hd", "Hl"]):
        if Hl > 0:
            vals.append(1 + 2 * (p["n"] - 1) * (1 - Hd / Hl) if p["mode"] < 0.5 else Hd / Hl)
    return _mean(vals)


CALCS = {
    "eng_coil_L": {"label": "L", "unit": "H", "needs": ["V", "I", "r"], "fn": _coil_L},
    "eng_sono_f": {"label": "f of the mains", "unit": "Hz", "needs": ["l", "M"], "fn": _sono_f},
    "eng_lm_f": {"label": "f of the mirror", "unit": "m", "needs": ["v", "a"], "fn": _lm_f},
    "eng_tl_f": {"label": "f of the concave lens", "unit": "m", "needs": ["v1", "a", "xi"], "fn": _tl_f},
    "eng_liq_n": {"label": "n of the liquid", "unit": "", "needs": ["Hd", "Hl"], "fn": _liq_n},
}
