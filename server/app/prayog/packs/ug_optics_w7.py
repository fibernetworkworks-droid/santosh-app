"""Kernel pack: the B.Sc. / B.Tech applied-optics bench (wave 7 of the undergraduate Prayogshala build-out).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/ug_optics_w7.js` (same formulas, same order of operations, so both give the same numbers).

Every kernel here is a "set the control, read the detector" instrument and exposes the same three pieces:
    read(p)   the detector readings at the present settings (`x`, and `stage` / `A` where the set-up has them)
    plan(p)   the settings a careful student records, in order (the studio's walk-through follows exactly this plan)
    calc      the reduction of the recorded table to the result (registered in CALCS; the studio and the server use it)
`measure(p)` runs plan -> read -> calc, so each lab's check proves the whole path against the textbook value.

Kernels, with the relation each one is checked against (1 %):
    w7_tir        critical emergence from a prism     n = sqrt(1 + ((sin e + cos A) / sin A)^2);  liquid film: n_l = sin A sqrt(n^2 - sin^2 e) - cos A sin e
    w7_wollaston  air film in a liquid cell           n = 1 / sin(half the angle between the two cut-offs)
    w7_nodal      two thin lenses on a nodal slide    F = f1 f2 / (f1 + f2 - d);  second principal point F d / f1 in front of the rear lens
    w7_biprism    Fresnel's biprism                   lambda = beta sqrt(d1 d2) / D;  mica: t = S lambda / (beta (mu - 1))
    w7_fringes    fringe counting (Michelson)         lambda = 2 dx / N;  air: n - 1 = N lambda P0 / (2 L P);  rod: alpha = N lambda / (2 L0 dT)
    w7_fabry      Fabry-Perot                         lambda = 2 dx / N;  finesse = pi sqrt(R) / (1 - R)
    w7_fts        Fourier-transform spectroscopy      Gaussian band: visibility V(x) = exp(-2 pi^2 s^2 x^2);  FWHM = 2.3548 s lambda0^2
    w7_corona     diffraction by many equal discs     dark rings at pi d sin(theta) / lambda = 3.8317, 7.0156 (zeros of J1)
    w7_resolve    telescope with a slit aperture      Rayleigh: lambda / a = s / D
    w7_malus      polariser and analyser              I = Imin + (Imax - Imin) cos^2(theta - theta0)
    w7_babinet    Babinet compensator                 delta from the fringe shift, tan(psi) from the analyser;  sin 2chi = sin 2psi sin delta
    w7_nearfield  near field of a multimode fibre     I(r) / I(0) = 1 - (r / a)^g  (the index profile's shape)
    w7_bend       bend loss of a step-index fibre     guided fraction = 1 - [2a/R + (3 / (2 n2 k R))^(2/3)] / (2 Delta)   (Gloge)
    w7_splice     lateral offset at a splice          eta = (2/pi) [acos(u) - u sqrt(1 - u^2)],  u = offset / 2a
    w7_mfd        far field of a single-mode fibre    P(theta) = P0 exp(-2 theta^2 / theta0^2),  MFD = 2 lambda / (pi theta0)
    w7_ld         laser diode L-I curve               P = eta (I - Ith) above threshold
Everything is SI and deterministic: no randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
J1_ZEROS = [3.8317059702075125, 7.015586669815619, 10.173468135062722]     # zeros of J1 (Abramowitz and Stegun, table 9.5)
SIG_FWHM = 2.3548200450309493                                               # 2 sqrt(2 ln 2)


def _fin(v: float) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


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


def _mean(xs: list[float]) -> float:
    s = 0.0
    for x in xs:
        s += x
    return s / len(xs) if xs else 0.0


def _line(xs: list[float], ys: list[float]) -> list[float]:
    """Least-squares y = m x + c; [0, 0] when it cannot be drawn."""
    n = len(xs)
    if n < 2:
        return [0.0, 0.0]
    sx = sy = sxx = sxy = 0.0
    for i in range(n):
        sx += xs[i]
        sy += ys[i]
        sxx += xs[i] * xs[i]
        sxy += xs[i] * ys[i]
    den = n * sxx - sx * sx
    if den == 0.0:
        return [0.0, 0.0]
    m = (n * sxy - sx * sy) / den
    return [m, (sy - m * sx) / n]


def _sqrt(v: float) -> float:
    return math.sqrt(v) if v > 0.0 else 0.0


def _asin(v: float) -> float:
    return math.asin(_clamp(v, -1.0, 1.0))


def _acos(v: float) -> float:
    return math.acos(_clamp(v, -1.0, 1.0))


def _ln(v: float) -> float:
    return math.log(v) if v > 0.0 else 0.0


def _sinc2(u: float) -> float:
    if abs(u) < 1e-9:
        return 1.0
    q = math.sin(u) / u
    return q * q


def _j1(u: float) -> float:
    """Bessel J1 by its power series (40 terms): good to 1e-10 for |u| <= 15, which covers the first three rings."""
    h = u / 2.0
    term = h
    tot = h
    for k in range(1, 40):
        term = -term * h * h / (k * (k + 1.0))
        tot += term
    return tot


class _Scan:
    """Time plays no part: the studio just calls step(). view() is read(), measure() is plan -> read -> calc."""

    PARAMS: dict[str, float] = {}
    VARS: list[str] = []
    CALC = ""

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @classmethod
    def view(cls, s, p, cfg=None):
        return cls.read(p)

    @classmethod
    def table(cls, p):
        rows = []
        for st in cls.plan(p):
            q = dict(p)
            q.update(st)
            row = dict(st)
            row.update(cls.read(q))
            rows.append(row)
        return rows

    @classmethod
    def measure(cls, p, cfg=None):
        rows = cls.table(p)
        return {"result": _fin(cls.calc(rows, p)), "rows": float(len(rows))}


# ===================================================================================== critical emergence from a prism
class Tir(_Scan):
    """A prism of angle A on a spectrometer, lit at grazing incidence through one face by a broad sodium source.

    The last ray to get in enters at 90 degrees, so inside it makes the critical angle r1 with the first normal
    (sin r1 = n_out / n, n_out = 1 for air or n_l for a liquid film held on that face). It meets the second face at
    r2 = A - r1 and leaves at e, with sin e = n sin r2. The telescope therefore sees a field that is bright on one side
    and dark on the other; the edge is at the reading x0 + e, and the Gaussian eyepiece finds the face normal at x0
    (the cross-wire's own reflection falls back on the cross-wire). `refl` is how far that reflection is off.
    """

    PARAMS = {"A": PI / 3, "n": 1.5168, "nl": 1.0, "mode": 0.0, "x0": 0.6109, "x": 0.6109, "fov": 0.02}
    VARS = ["x", "bright", "refl", "e"]

    @staticmethod
    def e(p):
        nout = p["nl"] if p["mode"] > 0.5 else 1.0
        r1 = _asin(nout / p["n"])
        return _asin(p["n"] * math.sin(p["A"] - r1))

    @staticmethod
    def read(p):
        e = Tir.e(p)
        return {"x": p["x"], "bright": _clamp(0.5 + (p["x"] - (p["x0"] + e)) / p["fov"], 0.0, 1.0),
                "refl": 2.0 * (p["x"] - p["x0"]), "e": e}

    @staticmethod
    def plan(p):
        return [{"x": p["x0"] + Tir.e(p)}, {"x": p["x0"]}]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "refl")
        if len(r) < 2:
            return 0.0
        norm = r[0]
        for q in r:
            if abs(q[1]) < abs(norm[1]):
                norm = q
        edge = r[0]
        for q in r:
            if abs(q[0] - norm[0]) > abs(edge[0] - norm[0]):
                edge = q
        e = edge[0] - norm[0]
        sa, ca = math.sin(p["A"]), math.cos(p["A"])
        if p["mode"] > 0.5:
            return _fin(sa * _sqrt(p["n"] * p["n"] - math.sin(e) * math.sin(e)) - ca * math.sin(e))
        if sa == 0.0:
            return 0.0
        q2 = (math.sin(e) + ca) / sa
        return _fin(_sqrt(1.0 + q2 * q2))


# ===================================================================================== Wollaston's air film
class Wollaston(_Scan):
    """A thin air film sealed between two glass plates, stood in a liquid cell on a turntable.

    Light crosses the film until the angle it makes with the film's normal, measured in the liquid, reaches the
    critical angle C with sin C = 1 / n (the glass plates have parallel faces and drop out). Turning the cell either
    way from the straight-through reading x0 the transmitted light is cut off at x0 - C and at x0 + C. Before that the
    film passes T = (1 - R)^2 with R the unpolarised Fresnel reflectance of one liquid-air surface.
    """

    PARAMS = {"n": 1.3330, "x0": 1.5708, "x": 1.5708}
    VARS = ["x", "T"]

    @staticmethod
    def read(p):
        th = p["x"] - p["x0"]
        s = p["n"] * math.sin(abs(th))
        if s >= 1.0:
            return {"x": p["x"], "T": 0.0}
        ct = math.sqrt(1.0 - s * s)
        ci = math.cos(th)
        rs = (p["n"] * ci - ct) / (p["n"] * ci + ct)
        rp = (p["n"] * ct - ci) / (p["n"] * ct + ci)
        R = (rs * rs + rp * rp) / 2.0
        return {"x": p["x"], "T": (1.0 - R) * (1.0 - R)}

    @staticmethod
    def plan(p):
        c = _asin(1.0 / p["n"])
        return [{"x": p["x0"] - c}, {"x": p["x0"] + c}]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x")
        if len(r) < 2:
            return 0.0
        lo = hi = r[0][0]
        for q in r:
            lo = min(lo, q[0])
            hi = max(hi, q[0])
        s = math.sin((hi - lo) / 2.0)
        return _fin(1.0 / s) if s > 0.0 else 0.0


# ===================================================================================== the nodal slide
class Nodal(_Scan):
    """Two thin converging lenses f1 (front) and f2 (rear) a distance d apart on a nodal slide, in parallel light.

    Equivalent focal length F = f1 f2 / (f1 + f2 - d). The second principal (nodal) point lies F d / f1 in front of the
    rear lens; turned end for end (stage 1) the lenses swap and it is F d / f2. `x` is how far the slide's vertical
    axis stands in front of the rear lens. Turning the slide through `rot` moves the image sideways by
    (x - h) sin(rot), so the image stays still only when the axis passes through the nodal point; the screen in focus
    is then exactly F from the axis. `D` is the axis-to-screen distance with the image in focus.
    """

    PARAMS = {"f1": 0.15, "f2": 0.20, "d": 0.05, "stage": 0.0, "x": 0.02, "rot": 0.0873, "mode": 0.0}
    VARS = ["x", "shift", "D", "stage"]

    @staticmethod
    def F(p):
        den = p["f1"] + p["f2"] - p["d"]
        return p["f1"] * p["f2"] / den if den != 0.0 else 0.0

    @staticmethod
    def h(p):
        front = p["f2"] if p["stage"] > 0.5 else p["f1"]
        return Nodal.F(p) * p["d"] / front if front != 0.0 else 0.0

    @staticmethod
    def read(p):
        h = Nodal.h(p)
        return {"x": p["x"], "shift": (p["x"] - h) * math.sin(p["rot"]), "D": Nodal.F(p) + p["x"] - h, "stage": p["stage"]}

    @staticmethod
    def plan(p):
        return [{"stage": 0.0, "x": Nodal.h(dict(p, stage=0.0))}, {"stage": 1.0, "x": Nodal.h(dict(p, stage=1.0))}]

    @staticmethod
    def calc(rows, p):
        r = [q for q in _rows(rows, "stage", "x", "shift", "D") if abs(q[2]) <= 2e-4]
        if p["mode"] > 0.5:
            return _mean([q[1] for q in r if q[0] < 0.5])
        return _mean([q[3] for q in r])


# ===================================================================================== Fresnel's biprism
class Biprism(_Scan):
    """A slit, a biprism of small angle alpha a distance a from it, and a micrometer eyepiece D from the slit.

    The biprism makes two virtual slits d = 2 a (nb - 1) alpha apart; the fringes have width beta = lambda D / d.
    `stage` says what is on the bench: 0 the fringes; 1 and 2 a convex lens (focal length f) at its two conjugate
    positions, giving sharp images of the two slits d1 and d2 apart with d = sqrt(d1 d2); 3 the fringes again with a
    thin mica sheet over one half of the biprism, which carries the whole pattern sideways by S = (mu - 1) t D / d.
    `x` is the cross-wire's position, `N` the number of fringes counted from the centre of the pattern.
    """

    PARAMS = {"lam": 5.893e-7, "alpha": 0.0087266, "nb": 1.5168, "a": 0.10, "D": 1.0, "f": 0.20, "t": 1.2e-5,
              "mu": 1.58, "stage": 0.0, "x": 0.0, "mode": 0.0}
    VARS = ["x", "N", "I", "stage"]

    @staticmethod
    def geo(p):
        d = 2.0 * p["a"] * (p["nb"] - 1.0) * p["alpha"]
        beta = p["lam"] * p["D"] / d if d != 0.0 else 0.0
        disc = _sqrt(p["D"] * p["D"] - 4.0 * p["f"] * p["D"])
        u1 = (p["D"] - disc) / 2.0
        v1 = (p["D"] + disc) / 2.0
        d1 = d * v1 / u1 if u1 != 0.0 else 0.0
        d2 = d * u1 / v1 if v1 != 0.0 else 0.0
        S = (p["mu"] - 1.0) * p["t"] * p["D"] / d if d != 0.0 else 0.0
        return {"d": d, "beta": beta, "d1": d1, "d2": d2, "S": S}

    @staticmethod
    def read(p):
        g = Biprism.geo(p)
        st = p["stage"]
        if 0.5 < st < 2.5:
            half = (g["d1"] if st < 1.5 else g["d2"]) / 2.0
            u = (abs(p["x"]) - half) / 3e-5
            return {"x": p["x"], "N": 0.0, "I": math.exp(-u * u), "stage": st}
        off = g["S"] if st > 2.5 else 0.0
        N = (p["x"] - off) / g["beta"] if g["beta"] != 0.0 else 0.0
        c = math.cos(PI * N)
        return {"x": p["x"], "N": N, "I": c * c, "stage": st}

    @staticmethod
    def plan(p):
        g = Biprism.geo(p)
        out = [{"stage": 0.0, "x": -10.0 * g["beta"]}, {"stage": 0.0, "x": 10.0 * g["beta"]}]
        if p["mode"] > 0.5:
            out.append({"stage": 3.0, "x": g["S"]})
            return out
        out += [{"stage": 1.0, "x": -g["d1"] / 2.0}, {"stage": 1.0, "x": g["d1"] / 2.0},
                {"stage": 2.0, "x": -g["d2"] / 2.0}, {"stage": 2.0, "x": g["d2"] / 2.0}]
        return out

    @staticmethod
    def _span(r, st):
        xs = [q[1] for q in r if abs(q[0] - st) < 0.5]
        if len(xs) < 2:
            return 0.0
        lo = hi = xs[0]
        for v in xs:
            lo = min(lo, v)
            hi = max(hi, v)
        return hi - lo

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "x", "N")
        f0 = [q for q in r if q[0] < 0.5]
        if len(f0) < 2:
            return 0.0
        lo = hi = f0[0]
        for q in f0:
            if q[1] < lo[1]:
                lo = q
            if q[1] > hi[1]:
                hi = q
        if hi[2] == lo[2]:
            return 0.0
        beta = (hi[1] - lo[1]) / (hi[2] - lo[2])
        if p["mode"] > 0.5:
            c0 = lo[1] - lo[2] * beta
            sh = [q[1] - q[2] * beta - c0 for q in r if q[0] > 2.5]
            if not sh or beta == 0.0 or p["mu"] == 1.0:
                return 0.0
            return _fin(_mean(sh) * p["lam"] / (beta * (p["mu"] - 1.0)))
        d1 = Biprism._span(r, 1.0)
        d2 = Biprism._span(r, 2.0)
        return _fin(beta * _sqrt(d1 * d2) / p["D"]) if p["D"] != 0.0 else 0.0


# ===================================================================================== fringe counting
class Fringes(_Scan):
    """A Michelson interferometer used as a fringe counter. `N` fringes cross the detector as the control `x` changes.

    mode 0: x is the travel of the movable mirror,           N = 2 x / lambda
    mode 1: x is the air pressure in a cell of length L,     N = 2 L (n - 1) (x / P0) / lambda   (n - 1 = dn at P0)
    mode 2: x is the temperature of a rod of length L0 that carries one mirror,  N = 2 alpha L0 (x - T0) / lambda
    """

    PARAMS = {"lam": 6.328e-7, "mode": 0.0, "x": 0.0, "L": 0.05, "dn": 2.765e-4, "P0": 101325.0, "L0": 0.20,
              "al": 5.5e-7, "T0": 25.0}
    VARS = ["x", "N", "I"]

    @staticmethod
    def per(p):
        """Fringes per unit of the control."""
        if p["mode"] < 0.5:
            return 2.0 / p["lam"]
        if p["mode"] < 1.5:
            return 2.0 * p["L"] * p["dn"] / (p["P0"] * p["lam"])
        return 2.0 * p["al"] * p["L0"] / p["lam"]

    @staticmethod
    def read(p):
        x = p["x"] - (p["T0"] if p["mode"] > 1.5 else 0.0)
        N = Fringes.per(p) * x
        c = math.cos(PI * N)
        return {"x": p["x"], "N": N, "I": c * c}

    @staticmethod
    def plan(p):
        per = Fringes.per(p)
        if per == 0.0:
            return []
        if p["mode"] < 0.5:
            return [{"x": 50.0 * k / per} for k in range(5)]
        if p["mode"] < 1.5:
            return [{"x": 5.0 * k / per} for k in range(8)]
        nb = 5.0 * max(1.0, math.ceil(2.0 * per))          # a batch of fringes that takes at least ~10 K of heating
        return [{"x": p["T0"] + nb * k / per} for k in range(6)]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "N")
        m = _line([q[0] for q in r], [q[1] for q in r])[0]
        if m == 0.0:
            return 0.0
        if p["mode"] < 0.5:
            return _fin(2.0 / m)
        if p["mode"] < 1.5:
            return _fin(m * p["lam"] * p["P0"] / (2.0 * p["L"]))
        return _fin(m * p["lam"] / (2.0 * p["L0"]))


# ===================================================================================== Fabry-Perot
class Fabry(_Scan):
    """Two plane mirrors of reflectance R facing each other; one moves along the axis by x.

    Transmitted intensity (Airy): I = 1 / (1 + Fc sin^2(2 pi x / lambda)), Fc = 4R / (1 - R)^2. A ring collapses at the
    centre for every half wavelength of travel, so N = 2 x / lambda (mode 0, coarse screw). In mode 1 the fine (piezo)
    travel is scanned across two neighbouring maxima; the finesse is their spacing over their full width at half height.
    """

    PARAMS = {"lam": 6.328e-7, "R": 0.90, "mode": 0.0, "x": 0.0}
    VARS = ["x", "N", "I"]

    @staticmethod
    def fc(p):
        q = 1.0 - p["R"]
        return 4.0 * p["R"] / (q * q) if q != 0.0 else 0.0

    @staticmethod
    def read(p):
        s = math.sin(2.0 * PI * p["x"] / p["lam"])
        return {"x": p["x"], "N": 2.0 * p["x"] / p["lam"], "I": 1.0 / (1.0 + Fabry.fc(p) * s * s)}

    @staticmethod
    def plan(p):
        if p["mode"] < 0.5:
            return [{"x": 25.0 * k * p["lam"]} for k in range(5)]
        fc = Fabry.fc(p)
        hw = p["lam"] / (2.0 * PI) * _asin(1.0 / _sqrt(fc)) if fc > 0.0 else 0.0
        fsr = p["lam"] / 2.0
        return [{"x": -hw}, {"x": hw}, {"x": fsr - hw}, {"x": fsr + hw}]

    @staticmethod
    def calc(rows, p):
        if p["mode"] < 0.5:
            r = _rows(rows, "x", "N")
            m = _line([q[0] for q in r], [q[1] for q in r])[0]
            return _fin(2.0 / m) if m != 0.0 else 0.0
        xs = sorted(q[0] for q in _rows(rows, "x"))
        if len(xs) < 4:
            return 0.0
        w = ((xs[1] - xs[0]) + (xs[3] - xs[2])) / 2.0
        if w == 0.0:
            return 0.0
        return _fin(((xs[2] + xs[3]) / 2.0 - (xs[0] + xs[1]) / 2.0) / w)


# ===================================================================================== Fourier-transform spectroscopy
class Fts(_Scan):
    """White light through an interference filter into a Michelson interferometer.

    The filter's band is taken as a Gaussian in wavenumber, centre 1 / lam0 and full width at half height
    fwhm / lam0^2, i.e. standard deviation s. Its interferogram against the path difference x is
        I(x) = 1/2 [1 + V(x) cos(2 pi x / lam0)],   V(x) = exp(-2 pi^2 s^2 x^2).
    stage 0 is the interferometer: `N` fringes counted from zero path difference and the fringe visibility `V` there.
    stage 1 is the computer: it samples that interferogram (NS points out to XS) and takes its cosine transform; `x` is
    then the wavelength under the cursor and `T` the transformed spectrum there, as a fraction of its peak.
    """

    PARAMS = {"lam0": 5.5e-7, "fwhm": 1.0e-8, "mode": 0.0, "stage": 0.0, "x": 0.0, "XS": 6.0e-5, "NS": 400.0}
    VARS = ["x", "N", "V", "I", "T", "stage"]

    @staticmethod
    def s(p):
        return p["fwhm"] / (p["lam0"] * p["lam0"]) / SIG_FWHM

    @staticmethod
    def vis(p, x):
        q = PI * Fts.s(p) * x
        return math.exp(-2.0 * q * q)

    @staticmethod
    def spec(p, lam):
        """Cosine transform of the sampled interferogram at wavelength lam (trapezoid rule, one side)."""
        n = int(p["NS"])
        if n < 2 or lam <= 0.0:
            return 0.0
        dx = p["XS"] / n
        tot = 0.0
        for j in range(n + 1):
            x = j * dx
            w = 0.5 if (j == 0 or j == n) else 1.0
            tot += w * 0.5 * Fts.vis(p, x) * math.cos(2.0 * PI * x / p["lam0"]) * math.cos(2.0 * PI * x / lam)
        return tot * dx

    @staticmethod
    def read(p):
        if p["stage"] > 0.5:
            pk = Fts.spec(p, p["lam0"])
            return {"x": p["x"], "N": 0.0, "V": 0.0, "I": 0.0, "T": Fts.spec(p, p["x"]) / pk if pk != 0.0 else 0.0,
                    "stage": p["stage"]}
        V = Fts.vis(p, p["x"])
        return {"x": p["x"], "N": p["x"] / p["lam0"], "V": V,
                "I": 0.5 * (1.0 + V * math.cos(2.0 * PI * p["x"] / p["lam0"])), "T": 0.0, "stage": p["stage"]}

    @staticmethod
    def half(p, sign):
        """The wavelength on one side of the peak where the transformed spectrum is half its peak (bisection)."""
        pk = Fts.spec(p, p["lam0"])
        lo, hi = p["lam0"], p["lam0"] + sign * 3.0 * p["fwhm"]
        for _ in range(50):
            mid = (lo + hi) / 2.0
            if Fts.spec(p, mid) > 0.5 * pk:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    @staticmethod
    def plan(p):
        if p["mode"] > 0.5:
            return [{"stage": 1.0, "x": Fts.half(p, -1.0)}, {"stage": 1.0, "x": Fts.half(p, 1.0)}]
        return [{"stage": 0.0, "x": 5.0 * k * p["lam0"]} for k in range(6)]

    @staticmethod
    def calc(rows, p):
        if p["mode"] > 0.5:
            xs = [q[1] for q in _rows(rows, "stage", "x") if q[0] > 0.5]
            if len(xs) < 2:
                return 0.0
            lo = hi = xs[0]
            for v in xs:
                lo = min(lo, v)
                hi = max(hi, v)
            return hi - lo
        r = [q for q in _rows(rows, "stage", "x", "N", "V") if q[0] < 0.5]
        m = _line([q[1] for q in r], [q[2] for q in r])[0]
        if m == 0.0:
            return 0.0
        lam0 = 1.0 / m
        pts = [q for q in r if 0.0 < q[3] < 1.0]
        k = _line([q[1] * q[1] for q in pts], [_ln(q[3]) for q in pts])[0]
        if k >= 0.0:
            return 0.0
        s = _sqrt(-k / 2.0) / PI
        return _fin(SIG_FWHM * s * lam0 * lam0)


# ===================================================================================== the corona of lycopodium powder
class Corona(_Scan):
    """A glass plate dusted with equal opaque spheres of diameter `dia` in a laser beam; a screen D away.

    By Babinet's principle every particle diffracts like a circular hole of the same size, so the screen carries the
    Airy pattern I = (2 J1(u) / u)^2, u = pi dia sin(theta) / lambda, with dark rings where J1 vanishes.
    `x` is the cursor's distance from the centre of the pattern.
    """

    PARAMS = {"dia": 3.2e-5, "lam": 6.328e-7, "D": 1.0, "x": 0.0}
    VARS = ["x", "I"]

    @staticmethod
    def read(p):
        th = math.atan2(abs(p["x"]), p["D"])
        u = PI * p["dia"] * math.sin(th) / p["lam"]
        if u < 1e-6:
            return {"x": p["x"], "I": 1.0}
        if u > 15.0:
            return {"x": p["x"], "I": 0.0}
        q = 2.0 * _j1(u) / u
        return {"x": p["x"], "I": q * q}

    @staticmethod
    def plan(p):
        out = []
        for z in J1_ZEROS[:2]:
            out.append({"x": p["D"] * math.tan(_asin(z * p["lam"] / (PI * p["dia"])))})
        return out

    @staticmethod
    def calc(rows, p):
        xs = sorted(abs(q[0]) for q in _rows(rows, "x"))
        vals = []
        for i, x in enumerate(xs[:3]):
            s = math.sin(math.atan2(x, p["D"]))
            if s > 0.0:
                vals.append(J1_ZEROS[i] * p["lam"] / (PI * s))
        return _mean(vals)


# ===================================================================================== resolving power of a telescope
class Resolve(_Scan):
    """Two narrow bright slits s apart, D from a telescope whose objective is covered by a slit of width x.

    Each source gives the single-slit pattern sinc^2(pi x theta / lambda), centred s / D apart. `dip` is the intensity
    midway between the two images over the intensity at one image's centre. Rayleigh's limit (the centre of one on the
    first minimum of the other, lambda / x = s / D) is where the dip reads 8 / pi^2 = 0.8106.
    """

    PARAMS = {"s": 2.0e-3, "D": 3.0, "lam": 5.893e-7, "x": 2.0e-3}
    VARS = ["x", "dip"]

    @staticmethod
    def read(p):
        ang = p["s"] / p["D"]
        mid = 2.0 * _sinc2(PI * p["x"] * ang / (2.0 * p["lam"]))
        pk = 1.0 + _sinc2(PI * p["x"] * ang / p["lam"])
        return {"x": p["x"], "dip": min(1.0, mid / pk)}

    @staticmethod
    def plan(p):
        return [{"x": p["lam"] * p["D"] / p["s"]}]

    @staticmethod
    def calc(rows, p):
        return _mean([q[0] for q in _rows(rows, "x")]) / p["lam"] if p["lam"] != 0.0 else 0.0


# ===================================================================================== Malus's law
class Malus(_Scan):
    """Polarised light of direction th0 through an analyser at x on to a photodiode.

    I = I0 [ext + (1 - ext) cos^2(x - th0)]: `ext` is the fraction that still gets through when the analyser is
    crossed (the source's and the polaroid's finite extinction).
    mode 0 the direction th0, mode 1 the exponent of the cosine (Malus: 2), mode 2 the extinction ratio Imax / Imin.
    """

    PARAMS = {"th0": 0.6109, "I0": 4.0e-4, "ext": 0.002, "mode": 0.0, "x": 0.0}
    VARS = ["x", "I"]

    @staticmethod
    def read(p):
        c = math.cos(p["x"] - p["th0"])
        return {"x": p["x"], "I": p["I0"] * (p["ext"] + (1.0 - p["ext"]) * c * c)}

    @staticmethod
    def plan(p):
        if p["mode"] > 1.5:
            return [{"x": p["th0"]}, {"x": p["th0"] + PI / 2.0}]
        return [{"x": k * PI / 9.0} for k in range(9)]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "I")
        if len(r) < 2:
            return 0.0
        if p["mode"] > 1.5:
            lo = hi = r[0][1]
            for q in r:
                lo = min(lo, q[1])
                hi = max(hi, q[1])
            return _fin(hi / lo) if lo > 0.0 else 0.0
        C = S = a = 0.0
        for q in r:
            C += q[1] * math.cos(2.0 * q[0])
            S += q[1] * math.sin(2.0 * q[0])
            a += q[1]
        a = a / len(r)
        th0 = 0.5 * math.atan2(S, C)
        if th0 < 0.0:
            th0 += PI
        if p["mode"] < 0.5:
            return th0
        imin = a - 2.0 * _sqrt(C * C + S * S) / len(r)
        xs, ys = [], []
        for q in r:
            c = abs(math.cos(q[0] - th0))
            if c * c > 0.15 and q[1] - imin > 0.0:
                xs.append(_ln(c))
                ys.append(_ln(q[1] - imin))
        return _line(xs, ys)[0]


# ===================================================================================== Babinet compensator
class Babinet(_Scan):
    """Elliptically polarised light analysed with a Babinet compensator and an analyser.

    Along the compensator's two axes the light has amplitudes cos(psi) and sin(psi) and a phase difference `del`.
    Sliding the wedge by x adds 2 pi x / beta. With the analyser at A the cross-wire sees
        I = (cos A cos psi)^2 + (sin A sin psi)^2 + 2 cos A sin A cos psi sin psi cos(del + 2 pi x / beta).
    stage 0 is the calibration with plane-polarised light at 45 degrees (psi = 45 degrees, del = 0): crossed (A = 135
    degrees) the dark fringes sit at x = 0, beta, ... stage 1 is the light under test: the dark fringe has moved, which
    gives del, and it goes perfectly black only when the analyser is at 90 degrees + psi.
    mode 0 the ratio of the ellipse's axes, mode 1 the tilt of its major axis, mode 2 the phase difference.
    """

    PARAMS = {"psi": 0.5236, "del": 1.0472, "beta": 2.0e-3, "stage": 0.0, "A": 2.3562, "x": 0.0, "mode": 0.0}
    VARS = ["x", "A", "I", "stage"]

    @staticmethod
    def read(p):
        psi = p["psi"] if p["stage"] > 0.5 else PI / 4.0
        de = p["del"] if p["stage"] > 0.5 else 0.0
        a, b = math.cos(psi), math.sin(psi)
        c, s = math.cos(p["A"]), math.sin(p["A"])
        ph = de + 2.0 * PI * p["x"] / p["beta"]
        return {"x": p["x"], "A": p["A"], "I": c * a * c * a + s * b * s * b + 2.0 * c * s * a * b * math.cos(ph),
                "stage": p["stage"]}

    @staticmethod
    def plan(p):
        xs = p["beta"] * (1.0 - p["del"] / (2.0 * PI))
        return [{"stage": 0.0, "A": 3.0 * PI / 4.0, "x": 0.0}, {"stage": 0.0, "A": 3.0 * PI / 4.0, "x": p["beta"]},
                {"stage": 1.0, "A": 3.0 * PI / 4.0, "x": xs}, {"stage": 1.0, "A": PI / 2.0 + p["psi"], "x": xs}]

    @staticmethod
    def ellipse(psi, de, mode):
        if mode < 0.5:
            return abs(math.tan(0.5 * _asin(math.sin(2.0 * psi) * math.sin(de))))
        if mode < 1.5:
            return 0.5 * math.atan2(math.sin(2.0 * psi) * math.cos(de), math.cos(2.0 * psi))
        return de

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "A", "x")
        c0 = [q[2] for q in r if q[0] < 0.5]
        t1 = [q for q in r if q[0] > 0.5]
        if len(c0) < 2 or not t1:
            return 0.0
        lo = hi = c0[0]
        for v in c0:
            lo = min(lo, v)
            hi = max(hi, v)
        beta = hi - lo
        if beta == 0.0:
            return 0.0
        far = t1[0]
        for q in t1:
            if abs(q[1] - 3.0 * PI / 4.0) > abs(far[1] - 3.0 * PI / 4.0):
                far = q
        psi = far[1] - PI / 2.0
        frac = (_mean([q[2] for q in t1]) - lo) / beta
        frac = frac - math.floor(frac)
        de = 2.0 * PI * (1.0 - frac)
        return _fin(Babinet.ellipse(psi, de, p["mode"]))


# ===================================================================================== near field of a multimode fibre
class NearField(_Scan):
    """The end face of a multimode fibre imaged with magnification M on to a small detector that scans across it.

    For a fully (uniformly) excited fibre the near-field intensity follows the local numerical aperture,
    I(r) / I(0) = [n^2(r) - n2^2] / [n1^2 - n2^2] = 1 - (r / a)^g for a power-law profile of exponent g
    (g = 2 parabolic, g large a step). `x` is the detector's position in the image plane, r = |x| / M.
    """

    PARAMS = {"g": 2.0, "a": 2.5e-5, "M": 400.0, "P0": 1.0e-6, "x": 0.0}
    VARS = ["x", "P"]

    @staticmethod
    def read(p):
        u = abs(p["x"]) / (p["M"] * p["a"])
        return {"x": p["x"], "P": p["P0"] * (1.0 - math.pow(u, p["g"])) if u < 1.0 else 0.0}

    @staticmethod
    def plan(p):
        return [{"x": p["M"] * p["a"] * k} for k in (0.0, 0.3, 0.45, 0.6, 0.75, 0.9)]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "P")
        if not r:
            return 0.0
        pk = r[0][1]
        for q in r:
            pk = max(pk, q[1])
        xs, ys = [], []
        for q in r:
            u = abs(q[0]) / (p["M"] * p["a"])
            if 0.0 < u < 1.0 and 0.0 < q[1] < pk:
                xs.append(_ln(u))
                ys.append(_ln(1.0 - q[1] / pk))
        return _line(xs, ys)[0]


# ===================================================================================== bend loss
class Bend(_Scan):
    """A step-index multimode fibre (core radius a, cladding index n2, relative index difference Dl) wound on a mandrel.

    Gloge's count of the modes a bend of radius R still guides:
        guided fraction = 1 - [2 a / R + (3 / (2 n2 k R))^(2/3)] / (2 Dl),   k = 2 pi / lambda.
    stage 0 is the fibre laid straight (the reference power P0), stage 1 one full turn on a mandrel of radius x.
    """

    PARAMS = {"Dl": 0.01, "a": 2.5e-5, "n2": 1.45, "lam": 8.5e-7, "P0": 1.0e-4, "stage": 0.0, "x": 0.03}
    VARS = ["x", "P", "dB", "stage"]

    @staticmethod
    def term(p, R):
        k = 2.0 * PI / p["lam"]
        return 2.0 * p["a"] / R + math.pow(3.0 / (2.0 * p["n2"] * k * R), 2.0 / 3.0)

    @staticmethod
    def read(p):
        f = 1.0
        if p["stage"] > 0.5 and p["x"] > 0.0:
            f = _clamp(1.0 - Bend.term(p, p["x"]) / (2.0 * p["Dl"]), 0.0, 1.0)
        return {"x": p["x"], "P": p["P0"] * f, "dB": -10.0 * math.log10(f) if f > 0.0 else 99.0, "stage": p["stage"]}

    @staticmethod
    def plan(p):
        return [{"stage": 0.0, "x": 0.03}] + [{"stage": 1.0, "x": R} for R in (0.03, 0.02, 0.012, 0.008, 0.006)]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "x", "P")
        ref = _mean([q[2] for q in r if q[0] < 0.5])
        if ref <= 0.0:
            return 0.0
        vals = []
        for q in r:
            if q[0] > 0.5 and q[1] > 0.0 and 0.0 < q[2] < ref:
                vals.append(Bend.term(p, q[1]) / (2.0 * (1.0 - q[2] / ref)))
        return _mean(vals)


# ===================================================================================== splice loss
class Splice(_Scan):
    """Two identical step-index multimode fibres butted in a V-groove with a sideways offset `off` between the cores.

    With the power spread evenly over the modes, the fraction coupled is the common area of the two core circles:
        eta = (2 / pi) [acos(u) - u sqrt(1 - u^2)],  u = off / (2 a).
    stage 0 is the unbroken reference fibre, stage 1 the fibre with the splice in it.
    """

    PARAMS = {"off": 1.0e-5, "a": 2.5e-5, "P0": 1.0e-4, "stage": 0.0}
    VARS = ["P", "stage"]

    @staticmethod
    def eta(p):
        u = _clamp(p["off"] / (2.0 * p["a"]), 0.0, 1.0)
        return 2.0 / PI * (_acos(u) - u * _sqrt(1.0 - u * u))

    @staticmethod
    def read(p):
        return {"P": p["P0"] * (Splice.eta(p) if p["stage"] > 0.5 else 1.0), "stage": p["stage"]}

    @staticmethod
    def plan(p):
        return [{"stage": 0.0}, {"stage": 1.0}]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "P")
        ref = _mean([q[1] for q in r if q[0] < 0.5])
        out = _mean([q[1] for q in r if q[0] > 0.5])
        if ref <= 0.0 or out <= 0.0:
            return 0.0
        return 10.0 * math.log10(ref / out)


# ===================================================================================== mode field diameter
class Mfd(_Scan):
    """The far field of a single-mode fibre, scanned with a detector on a goniometer arm at angle x.

    The fundamental mode is close to a Gaussian of spot size w0, so P(x) = P0 exp(-2 x^2 / th0^2) with
    th0 = lambda / (pi w0); the mode field diameter is 2 w0.
    """

    PARAMS = {"w0": 4.6e-6, "lam": 1.31e-6, "P0": 1.0e-6, "x": 0.0}
    VARS = ["x", "P"]

    @staticmethod
    def read(p):
        th0 = p["lam"] / (PI * p["w0"])
        q = p["x"] / th0
        return {"x": p["x"], "P": p["P0"] * math.exp(-2.0 * q * q)}

    @staticmethod
    def plan(p):
        return [{"x": k * 1.5 * PI / 180.0} for k in range(5)]

    @staticmethod
    def calc(rows, p):
        r = [q for q in _rows(rows, "x", "P") if q[1] > 0.0]
        m = _line([q[0] * q[0] for q in r], [_ln(q[1]) for q in r])[0]
        if m >= 0.0:
            return 0.0
        return _fin(2.0 * p["lam"] / (PI * _sqrt(-2.0 / m)))


# ===================================================================================== laser diode
class LaserDiode(_Scan):
    """Light against drive current for a laser diode.

    Below threshold the junction is an LED of small slope s; above it the output rises steeply with slope eta:
        P = s I (I <= Ith),   P = s Ith + eta (I - Ith) (I > Ith).
    The threshold is where the two straight lines meet. mode 0 the threshold current, mode 1 the slope efficiency.
    """

    PARAMS = {"Ith": 0.020, "eta": 0.5, "s": 0.012, "mode": 0.0, "x": 0.0}
    VARS = ["x", "P"]

    @staticmethod
    def read(p):
        i = max(0.0, p["x"])
        if i <= p["Ith"]:
            return {"x": p["x"], "P": p["s"] * i}
        return {"x": p["x"], "P": p["s"] * p["Ith"] + p["eta"] * (i - p["Ith"])}

    @staticmethod
    def plan(p):
        return [{"x": p["Ith"] * k} for k in (0.3, 0.5, 0.7, 1.1, 1.2, 1.3, 1.4)]

    @staticmethod
    def calc(rows, p):
        r = sorted(_rows(rows, "x", "P"), key=lambda q: q[0])
        if len(r) < 7:
            return 0.0
        lo, hi = r[:3], r[-4:]
        l1 = _line([q[0] for q in lo], [q[1] for q in lo])
        l2 = _line([q[0] for q in hi], [q[1] for q in hi])
        if p["mode"] > 0.5:
            return l2[0]
        if l2[0] == l1[0]:
            return 0.0
        return _fin((l1[1] - l2[1]) / (l2[0] - l1[0]))


KERNELS: dict[str, Any] = {
    "w7_tir": Tir, "w7_wollaston": Wollaston, "w7_nodal": Nodal, "w7_biprism": Biprism, "w7_fringes": Fringes,
    "w7_fabry": Fabry, "w7_fts": Fts, "w7_corona": Corona, "w7_resolve": Resolve, "w7_malus": Malus,
    "w7_babinet": Babinet, "w7_nearfield": NearField, "w7_bend": Bend, "w7_splice": Splice, "w7_mfd": Mfd,
    "w7_ld": LaserDiode,
}
FAMILY = {k: "optics" for k in KERNELS}


def _calc(cls):
    def fn(rows, p):
        try:
            return _fin(cls.calc(rows, p))
        except (ZeroDivisionError, ValueError, OverflowError):
            return 0.0
    return fn


CALCS = {
    "w7_tir": {"label": "refractive index", "unit": "", "needs": ["x", "refl"], "fn": _calc(Tir)},
    "w7_wollaston": {"label": "refractive index", "unit": "", "needs": ["x"], "fn": _calc(Wollaston)},
    "w7_nodal": {"label": "focal length / principal point", "unit": "m", "needs": ["stage", "x", "shift", "D"], "fn": _calc(Nodal)},
    "w7_biprism": {"label": "wavelength / thickness", "unit": "m", "needs": ["stage", "x", "N"], "fn": _calc(Biprism)},
    "w7_fringes": {"label": "from the fringe count", "unit": "", "needs": ["x", "N"], "fn": _calc(Fringes)},
    "w7_fabry": {"label": "wavelength / finesse", "unit": "", "needs": ["x", "N"], "fn": _calc(Fabry)},
    "w7_fts": {"label": "width of the pass band", "unit": "m", "needs": ["stage", "x", "N", "V"], "fn": _calc(Fts)},
    "w7_corona": {"label": "particle diameter", "unit": "m", "needs": ["x"], "fn": _calc(Corona)},
    "w7_resolve": {"label": "resolving power", "unit": "", "needs": ["x"], "fn": _calc(Resolve)},
    "w7_malus": {"label": "from the analyser readings", "unit": "", "needs": ["x", "I"], "fn": _calc(Malus)},
    "w7_babinet": {"label": "the ellipse", "unit": "", "needs": ["stage", "A", "x"], "fn": _calc(Babinet)},
    "w7_nearfield": {"label": "profile exponent g", "unit": "", "needs": ["x", "P"], "fn": _calc(NearField)},
    "w7_bend": {"label": "relative index difference", "unit": "", "needs": ["stage", "x", "P"], "fn": _calc(Bend)},
    "w7_splice": {"label": "splice loss", "unit": "dB", "needs": ["stage", "P"], "fn": _calc(Splice)},
    "w7_mfd": {"label": "mode field diameter", "unit": "m", "needs": ["x", "P"], "fn": _calc(Mfd)},
    "w7_ld": {"label": "threshold / slope", "unit": "", "needs": ["x", "P"], "fn": _calc(LaserDiode)},
}

TEXTBOOK = {
    # the prism's own index (or the liquid film's): what the critical-emergence formula must give back
    "w7_tir": lambda p: p["nl"] if p["mode"] > 0.5 else p["n"],
    # sin C = 1 / n at the liquid-air film
    "w7_wollaston": lambda p: p["n"],
    # two thin lenses: F = f1 f2 / (f1 + f2 - d); second principal point F d / f1 in front of the rear lens
    "w7_nodal": lambda p: (p["f1"] * p["f2"] / (p["f1"] + p["f2"] - p["d"])) * (p["d"] / p["f1"] if p["mode"] > 0.5 else 1.0),
    # the lamp's wavelength, or the mica sheet's thickness
    "w7_biprism": lambda p: p["t"] if p["mode"] > 0.5 else p["lam"],
    "w7_fringes": lambda p: p["lam"] if p["mode"] < 0.5 else (p["dn"] if p["mode"] < 1.5 else p["al"]),
    # finesse of an ideal etalon: pi sqrt(R) / (1 - R)
    "w7_fabry": lambda p: p["lam"] if p["mode"] < 0.5 else PI * math.sqrt(p["R"]) / (1.0 - p["R"]),
    "w7_fts": lambda p: p["fwhm"],
    "w7_corona": lambda p: p["dia"],
    # Rayleigh: the least angle resolved is lambda / a, and here it equals s / D
    "w7_resolve": lambda p: p["D"] / p["s"],
    "w7_malus": lambda p: p["th0"] if p["mode"] < 0.5 else (2.0 if p["mode"] < 1.5 else 1.0 / p["ext"]),
    # the polarisation ellipse from (psi, delta): sin 2chi = sin 2psi sin delta, tan 2alpha = tan 2psi cos delta
    "w7_babinet": lambda p: Babinet.ellipse(p["psi"], p["del"], p["mode"]),
    "w7_nearfield": lambda p: p["g"],
    "w7_bend": lambda p: p["Dl"],
    # overlap of two equal circles a distance `off` apart, in decibels
    "w7_splice": lambda p: -10.0 * math.log10(2.0 / PI * (math.acos(p["off"] / (2.0 * p["a"]))
                                                           - p["off"] / (2.0 * p["a"]) * math.sqrt(1.0 - (p["off"] / (2.0 * p["a"])) ** 2))),
    "w7_mfd": lambda p: 2.0 * p["w0"],
    "w7_ld": lambda p: p["eta"] if p["mode"] > 0.5 else p["Ith"],
}
