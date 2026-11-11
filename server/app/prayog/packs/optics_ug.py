"""Prayogshala kernel pack: UNDERGRADUATE WAVE OPTICS (spectrometer, interference, diffraction, polarisation, fibres).

Nine kernels the shared kernels.py and the school optics pack do not have. Each one models the real measurement -
a ray traced face by face, an interference or diffraction integral evaluated and then SEARCHED for its own maximum or
minimum - instead of reading the textbook answer back:

    spectrometer  a prism on the spectrometer table: Snell face by face with a Cauchy n(lambda), the angle of minimum
                  deviation found by scanning the real trace, and the prism's angle from the two reflected beams.
    grating       a plane transmission grating on the same table: the N-slit intensity (Dirichlet kernel x the single
                  ruling's sinc), its principal maximum and first zero located numerically, so the dispersive power
                  and the Rayleigh resolving power are measured, never assumed.
    newtonrings   the air (or liquid) film between a plano-convex lens and a flat plate: the two-beam intensity with
                  its pi reflection shift, the n-th dark ring's radius found as a minimum of that intensity.
    airwedge      the same film as a wedge between two flats held apart by a spacer: the fringe spacing from two
                  located minima ten fringes apart.
    doubleslit    Young's double slit with real slits: the single-slit envelope times the two-slit cosine, fringe
                  spacing from the located maxima on either side of the centre (so the envelope cancels).
    gratingscreen a laser through (or off) a grating onto a screen: the order's spot located on the screen in metres.
    fibrecone     a multimode fibre's acceptance cone: the extreme ray traced out of the end face onto a screen.
    fresnelrefl   Fresnel's reflection coefficients for glass: Brewster's angle found as the minimum of R_p.
    polarimeter   a half-shade polarimeter: the analyser setting found as the minimum of the light through BOTH
                  halves, which is exactly the half-shade match.

Everything is SI, deterministic (no randomness, no wall clock) and written the SAME way in the JavaScript twin
`app/static/prayog/packs/optics_ug.js`, so both give the same numbers.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
R2D = 180.0 / PI


# ------------------------------------------------------------------------------------------------ small helpers
def _tern_min(f, lo: float, hi: float, iters: int = 120) -> float:
    """The argument of the minimum of a unimodal f on [lo, hi], by ternary search."""
    for _ in range(iters):
        a1 = lo + (hi - lo) / 3.0
        a2 = hi - (hi - lo) / 3.0
        if f(a1) < f(a2):
            hi = a2
        else:
            lo = a1
    return (lo + hi) / 2.0


def _tern_max(f, lo: float, hi: float, iters: int = 120) -> float:
    return _tern_min(lambda x: -f(x), lo, hi, iters)


def _bisect(f, lo: float, hi: float, iters: int = 100) -> float:
    """A sign change of f between lo and hi, narrowed by bisection."""
    flo = f(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if flo * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
            flo = f(lo)
    return (lo + hi) / 2.0


def _rows(rows, *keys) -> list[list[float]]:
    out = []
    for r in rows or []:
        try:
            vals = [float(r[k]) for k in keys]
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(v) for v in vals):
            out.append(vals)
    return out


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _slope(pts: list[list[float]]) -> float:
    """Least-squares slope of y against x (pts = [[x, y], ...])."""
    n = len(pts)
    if n < 2:
        return 0.0
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    den = n * sxx - sx * sx
    return (n * sxy - sx * sy) / den if den else 0.0


# ================================================================================================ the spectrometer
class Spectrometer:
    """A prism of refracting angle A on the spectrometer table, in light of wavelength lam. The glass's index follows
    Cauchy's two-term law n(lam) = n0 + nB / lam^2, so every colour has its own deviation. The telescope angle tel is
    where the observer has turned it to."""

    PARAMS = {"A": PI / 3, "n0": 1.504518, "nB": 4.2211e-15, "lam": 5.893e-7, "i": 0.8, "tel": 0.0, "side": 0.12}
    VARS = ["rays", "dev", "e", "r1", "tir", "refl_sep"]

    @staticmethod
    def nlam(p) -> float:
        return p["n0"] + p["nB"] / (p["lam"] * p["lam"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _angles(p, i: float):
        """Snell at the first face, then at the second: (r1, r2, e, deviation). None = the light cannot get out."""
        n = Spectrometer.nlam(p)
        x1 = math.sin(i) / n
        if abs(x1) > 1:
            return None
        r1 = math.asin(x1)
        r2 = p["A"] - r1
        x2 = n * math.sin(r2)
        if abs(x2) > 1:
            return None
        e = math.asin(x2)
        return r1, r2, e, i + e - p["A"]

    @staticmethod
    def _refl_sep(p) -> float:
        """The angle between the beams reflected off the two polished faces, by reflecting one direction off each
        face's normal: for a prism of angle A it comes out 2A, which is how the prism's angle is measured."""
        h = p["A"] / 2.0
        n1 = [-math.cos(h), math.sin(h)]                      # outward normal of the left refracting face
        n2 = [math.cos(h), math.sin(h)]                       # outward normal of the right refracting face
        d = [1.0, 0.0]                                        # the parallel beam from the collimator
        out = []
        for nn in (n1, n2):
            dot = d[0] * nn[0] + d[1] * nn[1]
            out.append([d[0] - 2 * dot * nn[0], d[1] - 2 * dot * nn[1]])
        c = out[0][0] * out[1][0] + out[0][1] * out[1][1]
        return math.acos(max(-1.0, min(1.0, c)))

    @staticmethod
    def view(s, p, cfg=None):
        A, S = p["A"], p["side"]
        apex = [0.0, S * math.cos(A / 2)]
        bl = [-S * math.sin(A / 2), 0.0]
        br = [S * math.sin(A / 2), 0.0]
        ang = Spectrometer._angles(p, p["i"])
        hit1 = [(apex[0] + bl[0]) / 2, (apex[1] + bl[1]) / 2]
        if ang is None:
            return {"rays": [{"p": [[hit1[0] - 0.12, hit1[1]], hit1], "v": 0}], "dev": 0.0, "e": 0.0, "r1": 0.0,
                    "tir": 1.0, "refl_sep": Spectrometer._refl_sep(p)}
        r1, r2, e, dev = ang
        # the deviated beam, drawn from the first face to beyond the second
        face2 = [(apex[0] + br[0]) / 2, (apex[1] + br[1]) / 2]
        start = [hit1[0] - 0.12 * math.cos(p["i"]), hit1[1] - 0.12 * math.sin(p["i"])]
        rays = [{"p": [start, hit1, face2, [face2[0] + 0.16, face2[1] - 0.16 * math.tan(dev)]], "v": 0}]
        return {"rays": rays, "dev": dev, "e": e, "r1": r1, "tir": 0.0, "refl_sep": Spectrometer._refl_sep(p)}

    @staticmethod
    def measure(p, cfg=None):
        """The angle of minimum deviation, found by turning the prism through the whole range and watching the
        traced emergent beam (0.01 degree steps), and the prism's angle from the two reflected beams."""
        best, bi = 10.0, 0.0
        k = 0
        while k <= 6000:
            i = (25.0 + k * 0.01) / R2D
            a = Spectrometer._angles(p, i)
            if a is not None and a[3] < best:
                best, bi = a[3], i
            k += 1
        return {"dm": best, "i_min": bi, "refl_sep": Spectrometer._refl_sep(p)}


def _spect_dm(p) -> float:
    """Textbook: at minimum deviation the ray passes symmetrically, so n = sin((A + dm)/2) / sin(A/2)."""
    n = p["n0"] + p["nB"] / (p["lam"] * p["lam"])
    return 2 * math.asin(min(1.0, n * math.sin(p["A"] / 2))) - p["A"]


def _spect_sep(p) -> float:
    return 2 * p["A"]


# ================================================================================================ the plane grating
class Grating:
    """A plane transmission grating of spacing d, each ruling clear over a width a, with N rulings lit by the beam.
    The intensity at angle th is the single ruling's sinc^2 times the Dirichlet kernel of the N rulings; nothing is
    read off the grating equation - the order's maximum and its first zero are SEARCHED for."""

    PARAMS = {"d": 1.6933333e-6, "a": 8.4666667e-7, "N": 5906.0, "lam": 5.893e-7, "m": 1.0, "tel": 0.0}
    VARS = ["inten", "theta", "tir"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _N(p) -> float:
        return math.floor(p["N"] + 0.5)

    @staticmethod
    def _detune(th: float, p) -> float:
        """The phase between neighbouring rulings, measured from the nearest order (keeps the Dirichlet kernel exact)."""
        g = PI * p["d"] * math.sin(th) / p["lam"]
        return g - PI * math.floor(g / PI + 0.5)

    @staticmethod
    def inten_at(th: float, p) -> float:
        u = Grating._detune(th, p)
        N = Grating._N(p)
        su = math.sin(u)
        arr = N if abs(su) < 1e-12 else math.sin(N * u) / su
        b = PI * p["a"] * math.sin(th) / p["lam"]
        sc = 1.0 if abs(b) < 1e-12 else math.sin(b) / b
        return sc * sc * arr * arr / (N * N)

    @staticmethod
    def order_theta(p, m: float, lam: float | None = None) -> float | None:
        """Where the m-th order really is: the maximum of the traced intensity inside the order's own main lobe."""
        q = p if lam is None else dict(p, lam=lam)
        s = m * q["lam"] / q["d"]
        if abs(s) >= 1:
            return None
        th0 = math.asin(s)
        w = 0.5 * q["lam"] / (Grating._N(q) * q["d"] * math.cos(th0))
        return _tern_max(lambda th: Grating.inten_at(th, q), th0 - w, th0 + w)

    @staticmethod
    def _first_zero(p, m: float) -> float | None:
        """The dark edge of that main lobe: the first sign change of the Dirichlet kernel past the maximum."""
        th = Grating.order_theta(p, m)
        if th is None:
            return None
        N = Grating._N(p)
        wz = p["lam"] / (N * p["d"] * math.cos(th))
        f = lambda x: math.sin(N * Grating._detune(x, p))          # noqa: E731
        lo, hi = th + 1e-3 * wz, th + 1.6 * wz
        if f(lo) * f(hi) > 0:
            return th + wz
        return _bisect(f, lo, hi)

    @staticmethod
    def resolving(p, m: float):
        """Rayleigh: the smallest wavelength difference whose own maximum falls on this line's first dark edge.
        Found by bisection on d(lambda), comparing the two located maxima - not from m x N."""
        th = Grating.order_theta(p, m)
        z = Grating._first_zero(p, m)
        if th is None or z is None:
            return None
        gap = z - th
        f = lambda dl: (Grating.order_theta(p, m, p["lam"] + dl) - th) - gap    # noqa: E731
        lim = p["d"] / m - p["lam"]                      # beyond this the order itself runs off the grating
        hi = min(p["lam"] * 0.5, lim * 0.9)
        if hi <= 0 or f(hi) < 0:
            return None
        dl = _bisect(f, 0.0, hi)
        return {"dlam": dl, "rp": p["lam"] / dl if dl > 0 else 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        th = Grating.order_theta(p, p["m"])
        return {"inten": Grating.inten_at(p["tel"], p), "theta": 0.0 if th is None else th,
                "tir": 1.0 if th is None else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        th = Grating.order_theta(p, p["m"])
        t1 = Grating.order_theta(p, 1.0)
        t2 = Grating.order_theta(p, 2.0)
        h = p["lam"] * 1e-2                              # 1 % either side: a real pair of close lines, not a razor-thin derivative
        a = Grating.order_theta(p, p["m"], p["lam"] + h)
        b = Grating.order_theta(p, p["m"], p["lam"] - h)
        disp = (a - b) / (2 * h) if (a is not None and b is not None) else 0.0
        R = Grating.resolving(p, p["m"]) or {"dlam": 0.0, "rp": 0.0}
        return {"theta": 0.0 if th is None else th, "theta1": 0.0 if t1 is None else t1,
                "theta2": 0.0 if t2 is None else t2, "disp": disp, "rp": R["rp"], "dlam": R["dlam"]}


def _grating_theta(p) -> float:
    """Textbook: d sin(theta) = m lambda."""
    return math.asin(min(1.0, p["m"] * p["lam"] / p["d"]))


def _grating_disp(p) -> float:
    """Textbook: d(theta)/d(lambda) = m / (d cos theta)."""
    th = _grating_theta(p)
    return p["m"] / (p["d"] * math.cos(th))


def _grating_rp(p) -> float:
    """Textbook: the resolving power of a grating is m N."""
    return p["m"] * math.floor(p["N"] + 0.5)


# ================================================================================================ Newton's rings
class NewtonRings:
    """A plano-convex lens of radius of curvature R resting on a plane glass plate, the film between them of index mu,
    lit from above with light of wavelength lam. The two reflections (one of them with a pi change of phase) give
    I(r) = 4 I0 cos^2(delta/2) with delta = 2 pi (2 mu t) / lam + pi and t = r^2 / (2R)."""

    PARAMS = {"R": 0.1, "lam": 5.893e-7, "mu": 1.0, "n": 10.0, "I0": 1.0, "r": 0.0}
    VARS = ["inten", "tfilm", "rn", "dn"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def thickness(r: float, p) -> float:
        return r * r / (2 * p["R"])

    @staticmethod
    def inten_at(r: float, p) -> float:
        d = 2 * PI * (2 * p["mu"] * NewtonRings.thickness(r, p)) / p["lam"] + PI
        c = math.cos(d / 2)
        return 4 * p["I0"] * c * c

    @staticmethod
    def dark_r(p, n: float) -> float:
        """The n-th dark ring: the minimum of the traced intensity between the bright rings on either side of it."""
        k = p["lam"] * p["R"] / max(p["mu"], 1e-12)
        lo = math.sqrt(max(n - 0.45, 0.0) * k)
        hi = math.sqrt((n + 0.45) * k)
        return _tern_min(lambda r: NewtonRings.inten_at(r, p), lo, hi)

    @staticmethod
    def view(s, p, cfg=None):
        r = NewtonRings.dark_r(p, p["n"])
        return {"inten": NewtonRings.inten_at(p["r"], p), "tfilm": NewtonRings.thickness(p["r"], p),
                "rn": r, "dn": 2 * r}

    @staticmethod
    def measure(p, cfg=None):
        r = NewtonRings.dark_r(p, p["n"])
        return {"rn": r, "dn": 2 * r}


def _rings_dn(p) -> float:
    """Textbook: the n-th dark ring has 2 mu t = n lambda, so D_n = 2 sqrt(n lambda R / mu)."""
    return 2 * math.sqrt(p["n"] * p["lam"] * p["R"] / p["mu"])


# ================================================================================================ the air wedge
class AirWedge:
    """Two optical flats in contact at one edge and held apart at a distance L by a spacer of thickness ts: the film
    is a wedge, t(x) = ts x / L, and the same two-beam intensity gives straight fringes parallel to the contact edge."""

    PARAMS = {"lam": 5.893e-7, "mu": 1.0, "ts": 5e-5, "L": 0.05, "n": 10.0, "x": 0.0, "I0": 1.0}
    VARS = ["inten", "tfilm", "xn", "beta"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def thickness(x: float, p) -> float:
        return p["ts"] * x / p["L"]

    @staticmethod
    def inten_at(x: float, p) -> float:
        d = 2 * PI * (2 * p["mu"] * AirWedge.thickness(x, p)) / p["lam"] + PI
        c = math.cos(d / 2)
        return 4 * p["I0"] * c * c

    @staticmethod
    def dark_x(p, n: float) -> float:
        k = p["lam"] * p["L"] / (2 * p["mu"] * max(p["ts"], 1e-12))
        lo, hi = max(n - 0.45, 0.0) * k, (n + 0.45) * k
        return _tern_min(lambda x: AirWedge.inten_at(x, p), lo, hi)

    @staticmethod
    def view(s, p, cfg=None):
        x = AirWedge.dark_x(p, p["n"])
        b = (AirWedge.dark_x(p, p["n"] + 10) - x) / 10.0
        return {"inten": AirWedge.inten_at(p["x"], p), "tfilm": AirWedge.thickness(p["x"], p), "xn": x, "beta": b}

    @staticmethod
    def measure(p, cfg=None):
        x = AirWedge.dark_x(p, p["n"])
        return {"xn": x, "beta": (AirWedge.dark_x(p, p["n"] + 10) - x) / 10.0}


def _wedge_beta(p) -> float:
    """Textbook: the fringe width of a wedge film is beta = lambda L / (2 mu ts)."""
    return p["lam"] * p["L"] / (2 * p["mu"] * p["ts"])


# ================================================================================================ the double slit
class DoubleSlit:
    """Two slits, each of width a, their centres d apart, a screen D away, laser light of wavelength lam.
    I(x) = I0 sinc^2(pi a sin th / lam) cos^2(pi d sin th / lam) with th = atan(x / D): the real envelope times the
    real two-slit term, so a missing order is missing here too."""

    PARAMS = {"a": 4e-5, "d": 5e-4, "D": 1.5, "lam": 6.328e-7, "I0": 1.0, "x": 0.0, "k": 4.0}
    VARS = ["inten", "beta", "xk"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def inten_at(x: float, p) -> float:
        st = math.sin(math.atan2(x, p["D"]))
        b = PI * p["a"] * st / p["lam"]
        g = PI * p["d"] * st / p["lam"]
        sc = 1.0 if abs(b) < 1e-12 else math.sin(b) / b
        c = math.cos(g)
        return p["I0"] * sc * sc * c * c

    @staticmethod
    def bright_x(p, k: float) -> float:
        """The k-th bright fringe: the maximum of the traced intensity inside that fringe."""
        beta = p["lam"] * p["D"] / p["d"]
        x0 = k * beta
        return _tern_max(lambda x: DoubleSlit.inten_at(x, p), x0 - 0.4 * beta, x0 + 0.4 * beta)

    @staticmethod
    def view(s, p, cfg=None):
        k = max(1.0, math.floor(p["k"] + 0.5))
        xp = DoubleSlit.bright_x(p, k)
        xm = DoubleSlit.bright_x(p, -k)
        return {"inten": DoubleSlit.inten_at(p["x"], p), "beta": (xp - xm) / (2 * k), "xk": xp}

    @staticmethod
    def measure(p, cfg=None):
        v = DoubleSlit.view({}, p)
        return {"beta": v["beta"], "xk": v["xk"]}


def _dslit_beta(p) -> float:
    """Textbook: the fringe width of a double slit is beta = lambda D / d."""
    return p["lam"] * p["D"] / p["d"]


# ================================================================================================ grating + screen
class GratingScreen:
    """A laser through (or off) a grating of spacing d onto a screen D away: the m-th order's spot sits at
    x = D tan(theta_m), and theta_m is found from the same N-slit intensity, not from the grating equation."""

    PARAMS = {"d": 1.6666667e-6, "a": 8.3333333e-7, "N": 1000.0, "D": 0.5, "lam": 6.328e-7, "m": 1.0, "x": 0.0}
    VARS = ["inten", "theta", "xm", "tir"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def order_theta(p, m: float) -> float | None:
        return Grating.order_theta({**Grating.PARAMS, **{k: p[k] for k in ("d", "a", "N", "lam")}, "m": m}, m)

    @staticmethod
    def spot_x(p, m: float) -> float | None:
        th = GratingScreen.order_theta(p, m)
        return None if th is None else p["D"] * math.tan(th)

    @staticmethod
    def view(s, p, cfg=None):
        th = GratingScreen.order_theta(p, p["m"])
        g = {**Grating.PARAMS, **{k: p[k] for k in ("d", "a", "N", "lam")}, "m": p["m"]}
        return {"inten": Grating.inten_at(math.atan2(p["x"], p["D"]), g), "theta": 0.0 if th is None else th,
                "xm": 0.0 if th is None else p["D"] * math.tan(th), "tir": 1.0 if th is None else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        out = {}
        for m in (1.0, 2.0):
            x = GratingScreen.spot_x(p, m)
            out[f"x{int(m)}"] = 0.0 if x is None else x
        x = GratingScreen.spot_x(p, p["m"])
        out["xm"] = 0.0 if x is None else x
        return out


def _gscreen_x(p) -> float:
    """Textbook: d sin(theta) = m lambda and the screen is D away, so x = D tan(theta)."""
    s = p["m"] * p["lam"] / p["d"]
    return p["D"] * math.tan(math.asin(min(1.0, s)))


# ================================================================================================ optical fibre
class FibreCone:
    """A step-index multimode fibre, core index n1, cladding n2, core diameter dcore, its far end dz above a screen.
    Light leaves the end face inside the acceptance cone; the extreme ray is traced out to the screen, so the lit
    patch has a diameter W = dcore + 2 dz tan(theta_a)."""

    PARAMS = {"n1": 1.492, "n2": 1.402, "dz": 0.02, "dcore": 0.001, "nout": 1.0}
    VARS = ["na", "theta_a", "W"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def theta_a(p) -> float:
        na = math.sqrt(max(p["n1"] * p["n1"] - p["n2"] * p["n2"], 0.0))
        return math.asin(min(1.0, na / p["nout"]))

    @staticmethod
    def spot(p) -> float:
        return p["dcore"] + 2 * p["dz"] * math.tan(FibreCone.theta_a(p))

    @staticmethod
    def view(s, p, cfg=None):
        W = FibreCone.spot(p)
        th = math.atan2(W - p["dcore"], 2 * p["dz"])
        return {"na": math.sin(th) * p["nout"], "theta_a": FibreCone.theta_a(p), "W": W}

    @staticmethod
    def measure(p, cfg=None):
        W = FibreCone.spot(p)
        th = math.atan2(W - p["dcore"], 2 * p["dz"])
        return {"W": W, "na": math.sin(th) * p["nout"]}


def _fibre_na(p) -> float:
    """Textbook: NA = sqrt(n1^2 - n2^2) (and sin of the acceptance angle in air)."""
    return math.sqrt(max(p["n1"] * p["n1"] - p["n2"] * p["n2"], 0.0))


# ================================================================================================ Brewster's angle
class FresnelRefl:
    """Light reflected off a glass surface of index n from a medium nout. Fresnel's coefficients give R_s and R_p;
    R_p falls to zero at one angle, and that angle is SEARCHED for, which is how Brewster's angle is measured."""

    PARAMS = {"n": 1.5168, "nout": 1.0, "th": 0.9, "I0": 1.0}
    VARS = ["Rs", "Rp", "Itot", "thb"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _coef(th: float, p):
        n1, n2 = p["nout"], p["n"]
        st = n1 * math.sin(th) / n2
        if abs(st) > 1:
            return 1.0, 1.0
        ct = math.sqrt(max(1 - st * st, 0.0))
        ci = math.cos(th)
        rs = (n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)
        rp = (n1 * ct - n2 * ci) / (n1 * ct + n2 * ci)
        return rs * rs, rp * rp

    @staticmethod
    def brewster(p) -> float:
        return _tern_min(lambda th: FresnelRefl._coef(th, p)[1], 0.05, 1.5)

    @staticmethod
    def view(s, p, cfg=None):
        Rs, Rp = FresnelRefl._coef(p["th"], p)
        return {"Rs": Rs, "Rp": Rp, "Itot": p["I0"] * (Rs + Rp) / 2, "thb": FresnelRefl.brewster(p)}

    @staticmethod
    def measure(p, cfg=None):
        th = FresnelRefl.brewster(p)
        Rs, Rp = FresnelRefl._coef(th, p)
        return {"thb": th, "Rp_min": Rp, "Rs_at": Rs}


def _brewster_th(p) -> float:
    """Textbook: tan(theta_B) = n2 / n1."""
    return math.atan(p["n"] / p["nout"])


# ================================================================================================ the polarimeter
class Polarimeter:
    """A half-shade polarimeter: the two halves of the field are polarised at +beta and -beta to the polariser's own
    plane. An optically active solution of concentration conc in a tube of length Ldm decimetres turns the plane by
    alpha x Ldm x conc degrees. The analyser setting that matches the two halves is found as the minimum of the light
    through BOTH halves together, which is exactly where a human sees them equally dim."""

    PARAMS = {"alpha": 66.5, "Ldm": 2.0, "conc": 0.1, "lam": 5.893e-7, "beta": 0.05236, "phi": 1.5708, "I0": 1.0}
    VARS = ["il", "ir", "itot", "match"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def rotation(p) -> float:
        return p["alpha"] * p["Ldm"] * p["conc"] / R2D

    @staticmethod
    def halves(p, phi: float, conc: float):
        th = p["alpha"] * p["Ldm"] * conc / R2D
        cl = math.cos(phi - th - p["beta"])
        cr = math.cos(phi - th + p["beta"])
        return p["I0"] * cl * cl, p["I0"] * cr * cr

    @staticmethod
    def match_at(p, conc: float) -> float:
        """Turn the analyser from just before 90 degrees and find where the whole field goes dimmest."""
        def tot(phi):
            a, b = Polarimeter.halves(p, phi, conc)
            return a + b
        return _tern_min(tot, PI / 2 - 0.2, PI / 2 + 1.2)

    @staticmethod
    def view(s, p, cfg=None):
        il, ir = Polarimeter.halves(p, p["phi"], p["conc"])
        return {"il": il, "ir": ir, "itot": il + ir, "match": Polarimeter.match_at(p, p["conc"])}

    @staticmethod
    def measure(p, cfg=None):
        zero = Polarimeter.match_at(p, 0.0)
        full = Polarimeter.match_at(p, p["conc"])
        return {"phi0": zero, "phi": full, "rot": full - zero}


def _polari_rot(p) -> float:
    """Textbook: the rotation is alpha x L(dm) x c(g/mL), in degrees."""
    return p["alpha"] * p["Ldm"] * p["conc"] / R2D


# ================================================================================================ registration
KERNELS: dict[str, Any] = {
    "spectrometer": Spectrometer, "planegrating": Grating, "newtonrings": NewtonRings, "airwedge": AirWedge,
    "doubleslit": DoubleSlit, "gratingscreen": GratingScreen, "fibrecone": FibreCone,
    "fresnelrefl": FresnelRefl, "polarimeter": Polarimeter,
}
FAMILY = {k: "optics" for k in KERNELS}
TEXTBOOK = {
    "spect_dm": _spect_dm,
    "spect_sep": _spect_sep,
    "grating_theta": _grating_theta,
    "grating_disp": _grating_disp,
    "grating_rp": _grating_rp,
    "rings_dn": _rings_dn,
    "wedge_beta": _wedge_beta,
    "dslit_beta": _dslit_beta,
    "gscreen_x": _gscreen_x,
    "fibre_na": _fibre_na,
    "brewster_th": _brewster_th,
    "polari_rot": _polari_rot,
}
CALCS: dict[str, dict] = {
    "spect_n": {"label": "n", "unit": "", "needs": ["dm"],
                "fn": lambda rows, p: _mean([math.sin((p["A"] + d) / 2) / math.sin(p["A"] / 2)
                                             for (d,) in _rows(rows, "dm")])},
    "spect_prism_A": {"label": "A", "unit": "rad", "needs": ["sep"],
                      "fn": lambda rows, p: _mean([s / 2 for (s,) in _rows(rows, "sep")])},
    "grating_lam": {"label": "wavelength", "unit": "m", "needs": ["m", "theta"],
                    "fn": lambda rows, p: _mean([p["d"] * math.sin(t) / m for m, t in _rows(rows, "m", "theta") if m])},
    "grating_R": {"label": "resolving power", "unit": "", "needs": ["rp"],
                  "fn": lambda rows, p: _mean([r for (r,) in _rows(rows, "rp")])},
    "rings_R": {"label": "R (lens)", "unit": "m", "needs": ["n", "dsq"],
                "fn": lambda rows, p: _slope(_rows(rows, "n", "dsq")) * p["mu"] / (4 * p["lam"])},
    "wedge_t": {"label": "thickness", "unit": "m", "needs": ["n", "x"],
                "fn": lambda rows, p: p["lam"] * p["L"] / (2 * p["mu"] * _slope(_rows(rows, "n", "x")))
                if _slope(_rows(rows, "n", "x")) > 0 else 0.0},
    "dslit_lam": {"label": "wavelength", "unit": "m", "needs": ["beta"],
                  "fn": lambda rows, p: _mean([b * p["d"] / p["D"] for (b,) in _rows(rows, "beta")])},
    "gscreen_lam": {"label": "wavelength", "unit": "m", "needs": ["m", "x"],
                    "fn": lambda rows, p: _mean([p["d"] * math.sin(math.atan2(x, p["D"])) / m
                                                 for m, x in _rows(rows, "m", "x") if m])},
    "gscreen_d": {"label": "grating spacing", "unit": "m", "needs": ["m", "x"],
                  "fn": lambda rows, p: _mean([m * p["lam"] / math.sin(math.atan2(x, p["D"]))
                                               for m, x in _rows(rows, "m", "x") if x > 0])},
    "fibre_NA": {"label": "NA", "unit": "", "needs": ["dz", "W"],
                 "fn": lambda rows, p: _mean([math.sin(math.atan2(W - p["dcore"], 2 * z))
                                              for z, W in _rows(rows, "dz", "W") if z > 0])},
    "brewster_n": {"label": "n", "unit": "", "needs": ["thb"],
                   "fn": lambda rows, p: _mean([math.tan(t) * p["nout"] for (t,) in _rows(rows, "thb")])},
    "polari_alpha": {"label": "specific rotation", "unit": "deg/(dm·g/mL)", "needs": ["c", "rot"],
                     "fn": lambda rows, p: _mean([r * R2D / (c * p["Ldm"]) for c, r in _rows(rows, "c", "rot") if c > 0])},
}
