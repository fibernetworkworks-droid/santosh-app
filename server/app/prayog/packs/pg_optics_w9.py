"""Kernel pack: the M.Sc. optics, lasers and spectroscopy bench (wave 9 of the Prayogshala build-out).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/pg_optics_w9.js` (same formulas, same order of operations, so both give the same numbers).

Every kernel is a "set the control, read the instrument" set-up with three pieces:
    read(p)   the readings at the present settings (`x`, and `A` / `stage` where the set-up has them)
    plan(p)   the settings a careful student records, in order (the studio's walk-through follows exactly this plan)
    calc      the reduction of the recorded table to the result (registered in CALCS; the studio and the server use it)
`measure(p)` runs plan -> read -> calc, so each lab's check proves the whole path against the textbook value.

Kernels (prefix po9_), with the relation each one is checked against (1 %):
    po9_fp        Fabry-Perot rings          2 t sigma cos(theta) = m;  d(sigma) = sigma (u1 / u2 - 1);  t = 1 / (2 sigma du);  finesse = du / ring width
    po9_zeeman    Zeeman pattern             d(sigma) = e B / (4 pi m c) (M_u g_u - M_l g_l); Fabry-Perot etalon or Lummer-Gehrcke plate
    po9_biref     a retarding plate          delta = 2 pi dn t / lambda;  Babinet fringe shift, or I(90) / (I(0) + I(90)) = sin^2(delta / 2)
    po9_ellipse   elliptically polarised     sin 2chi = sin 2phi sin delta;  quarter-wave plate + analyser, or Babinet compensator
    po9_photoel   photoelastic model         disc: N = 8 F C / (pi D lambda);  four-point beam: N = 3 C F a / (h^2 lambda)
    po9_eo        Kerr and Pockels cells     Kerr: Gamma = 2 pi K l E^2;  Pockels: Gamma = 2 pi n^3 r V / lambda (x L / d transverse)
    po9_faraday   Faraday rotation           rho = V B l;  V(lambda) = V(589.3 nm) (589.3 nm / lambda)^2 (Becquerel / Cauchy)
    po9_fraun     Fraunhofer diffraction     mesh / cross grating, circle (zeros of J1), square, slit, double slit, grating
    po9_cdev      constant deviation drum    drum = lambda + e(lambda) (quadratic); calibrated on three Hg lines
    po9_rowland   concave grating, Rowland   d (sin alpha + sin(s / R)) = m lambda;  plate factor d cos(beta) / (m R);  RP = m N
    po9_band      band heads (Deslandres)    nu(v', v") = Te + G'(v') - G"(v"),  G(v) = we (v + 1/2) - wexe (v + 1/2)^2
    po9_spec      a scanned spectrum         Gaussian bands: the vertex of three points about each band
    po9_film      film step                  multiple-beam step: t = (lambda / 2)(shift / spacing);  FECO: t = m (lambda_m - lambda'_m) / 2
    po9_stoney    Stoney's equation          sigma_f = M_s h_s^2 (1 / R1 - 1 / R0) / (6 h_f);  Newton's rings r^2 = m R lambda
    po9_photom    photometry                 E = I / d^2;  E_e = E / K
    po9_ao        acousto-optics             Raman-Nath: sin theta_m = m lambda f / v;  Bragg: sin theta_B = lambda f / (2 v);  eta = sin^2((pi/2) sqrt(P / P100))
Everything is SI and deterministic: no randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
C_LIGHT = 299792458.0                     # m/s, exact (SI)
H_PLANCK = 6.62607015e-34                 # J s, exact (SI)
J1_ZEROS = [3.8317059702075125, 7.015586669815619, 10.173468135062722, 13.323691936314223]
SINC2_HALF = 1.3915573144528073           # sin(u)^2 / u^2 = 1/2
NA_REF = 5.893e-7                         # the sodium wavelength the Verdet constants are quoted at
HG_CAL = [4.046565e-7, 4.358335e-7, 5.460750e-7]   # Hg I lines in air (NIST ASD)


def _fin(v: float) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _rnd(v: float) -> float:
    return math.floor(v + 0.5)


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


def _jn(n: int, u: float) -> float:
    """Bessel J_n by its power series (40 terms): good for |u| <= 12."""
    h = u / 2.0
    term = 1.0
    for k in range(1, n + 1):
        term = term * h / k
    tot = term
    for k in range(1, 40):
        term = -term * h * h / (k * (k + n))
        tot += term
    return tot


def _sorted_by(r: list[list[float]], i: int) -> list[list[float]]:
    out = [list(q) for q in r]
    for a in range(1, len(out)):                         # insertion sort: the same order in both twins
        q = out[a]
        b = a - 1
        while b >= 0 and out[b][i] > q[i]:
            out[b + 1] = out[b]
            b -= 1
        out[b + 1] = q
    return out


def _airy(F: float, ph: float) -> float:
    s = math.sin(PI * ph)
    return 1.0 / (1.0 + F * s * s)


def _coef(R: float) -> float:
    return 4.0 * R / ((1.0 - R) * (1.0 - R)) if R < 1.0 else 1e9


class _Scan:
    PARAMS: dict[str, float] = {}
    VARS: list[str] = []

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


# ===================================================================================== Fabry-Perot etalon rings
class Fp(_Scan):
    """A Fabry-Perot etalon of spacing t in front of a lens of focal length f; a micrometer eyepiece in the focal plane
    reads the distance x of a ring from the centre. Ring of order m of a line of wavenumber sigma: 2 t sigma cos(theta)
    = m, with cos(theta) = f / sqrt(f^2 + x^2) =: u. A second component (a hyperfine satellite or the other D line) lies
    dsig higher. The eyepiece cross-wire sees the Airy sum of both. `c` (0 main, 1 second) and `n` (ring number from the
    centre) say which ring the cross-wire is on - what the student sees by eye. mode 0 splitting, 1 spacing, 2 finesse."""

    PARAMS = {"lam": 5.460750e-7, "ds": 10.0, "w2": 0.6, "t": 0.01, "f": 0.3, "R": 0.9, "mode": 0.0, "x": 0.004}
    VARS = ["x", "I", "c", "n"]

    @staticmethod
    def read(p):
        x = abs(p["x"])
        u = p["f"] / math.sqrt(p["f"] * p["f"] + x * x)
        s1 = 1.0 / p["lam"]
        s2 = s1 + p["ds"]
        F = _coef(p["R"])
        p1 = 2.0 * p["t"] * s1 * u
        p2 = 2.0 * p["t"] * s2 * u
        I = (_airy(F, p1) + p["w2"] * _airy(F, p2)) / (1.0 + p["w2"])
        d1 = abs(p1 - _rnd(p1))
        d2 = abs(p2 - _rnd(p2))
        c = 1.0 if (p["w2"] > 0.0 and d2 < d1) else 0.0
        ph = p2 if c > 0.5 else p1
        M = math.floor(2.0 * p["t"] * s1)
        return {"x": p["x"], "I": I, "c": c, "n": M - _rnd(ph) + 1.0}

    @staticmethod
    def xr(p, s, m):
        cs = m / (2.0 * p["t"] * s)
        if cs >= 1.0 or cs <= 0.0:
            return 0.0
        return p["f"] * math.tan(math.acos(cs))

    @staticmethod
    def plan(p):
        s1 = 1.0 / p["lam"]
        s2 = s1 + p["ds"]
        M = math.floor(2.0 * p["t"] * s1)
        if p["mode"] > 1.5:
            h = _asin(1.0 / _sqrt(_coef(p["R"]))) / PI
            return [{"x": Fp.xr(p, s1, M - 1.0)}, {"x": Fp.xr(p, s1, M - 1.0 + h)}, {"x": Fp.xr(p, s1, M - 1.0 - h)},
                    {"x": Fp.xr(p, s1, M - 2.0)}]
        out = [{"x": Fp.xr(p, s1, M)}, {"x": Fp.xr(p, s1, M - 1.0)}, {"x": Fp.xr(p, s1, M - 2.0)}]
        if p["mode"] < 0.5:
            out += [{"x": Fp.xr(p, s2, M)}, {"x": Fp.xr(p, s2, M - 1.0)}]
        return out

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "c", "n")
        f = p["f"]
        s1 = 1.0 / p["lam"]
        us = []
        for q in r:
            us.append([f / math.sqrt(f * f + q[0] * q[0]), q[1], q[2]])
        if p["mode"] > 1.5:
            ring1 = [q[0] for q in us if q[1] < 0.5 and abs(q[2] - 2.0) < 0.5]
            ring2 = [q[0] for q in us if q[1] < 0.5 and abs(q[2] - 3.0) < 0.5]
            if len(ring1) < 3 or not ring2:
                return 0.0
            ring1 = [q[0] for q in _sorted_by([[v] for v in ring1], 0)]
            du = ring1[1] - _mean(ring2)
            w = ring1[len(ring1) - 1] - ring1[0]
            return du / w if w > 0.0 else 0.0
        main = [q for q in us if q[1] < 0.5]
        if p["mode"] > 0.5:
            l = _line([q[2] for q in main], [q[0] for q in main])
            return -1.0 / (2.0 * s1 * l[0]) if l[0] < 0.0 else 0.0
        ds = []
        for q in us:
            if q[1] > 0.5:
                for m in main:
                    if abs(m[2] - q[2]) < 0.5:
                        ds.append(s1 * (m[0] / q[0] - 1.0))
                        break
        return _mean(ds)


# ===================================================================================== Zeeman effect
def _zcomps(p) -> list[float]:
    """The Zeeman components in Lorentz units, M_u g_u - M_l g_l, sorted and without repeats; the longitudinal view
    (view 1) shows only the sigma components (Delta M = +-1)."""
    out: list[float] = []
    ju = int(_rnd(p["ju"]))
    jl = int(_rnd(p["jl"]))
    for a in range(-ju, ju + 1):
        for b in range(-jl, jl + 1):
            if abs(a - b) > 1:
                continue
            if p["view"] > 0.5 and a == b:
                continue
            k = a * p["gu"] - b * p["gl"]
            k = _rnd(k * 1e6) / 1e6
            seen = False
            for q in out:
                if abs(q - k) < 1e-9:
                    seen = True
            if not seen:
                out.append(k)
    return [q[0] for q in _sorted_by([[v] for v in out], 0)]


class Zeeman(_Scan):
    """A lamp between the poles of an electromagnet (field B, read on a gaussmeter); the light is analysed by a
    Fabry-Perot etalon (meth 0: rings, 2 t sigma u = m, u = cos theta) or a Lummer-Gehrcke plate (meth 1: fringes near
    grazing emergence, 2 t sigma sqrt(n^2 - cos^2 alpha) = m). Each component is shifted by k e B / (4 pi m_e c). The
    reading `c` is the rank of the component the cross-wire is on, counted from the long-wavelength side, and `n` the
    order number - what the student identifies in the pattern. mode 0 e/m, 1 Bohr magneton, 2 g of the upper level."""

    PARAMS = {"lam": 5.460750e-7, "B": 0.5, "em": 1.75882001076e11, "gu": 2.0, "gl": 1.5, "ju": 1.0, "jl": 2.0,
              "meth": 0.0, "view": 0.0, "t": 0.003, "f": 0.3, "R": 0.9, "nlg": 1.5168, "tl": 0.003, "mode": 0.0,
              "x": 0.004}
    VARS = ["x", "I", "c", "n"]
    ALO = 0.02

    @staticmethod
    def dl(p):
        return p["em"] * p["B"] / (4.0 * PI * C_LIGHT)

    @staticmethod
    def q(p, x):
        if p["meth"] > 0.5:
            a = math.atan(abs(x) / p["f"])
            cs = math.cos(a)
            return _sqrt(p["nlg"] * p["nlg"] - cs * cs)
        return p["f"] / math.sqrt(p["f"] * p["f"] + x * x)

    @staticmethod
    def thick(p):
        return p["tl"] if p["meth"] > 0.5 else p["t"]

    @staticmethod
    def base(p, smin):
        if p["meth"] > 0.5:
            cs = math.cos(Zeeman.ALO)
            return math.ceil(2.0 * p["tl"] * smin * _sqrt(p["nlg"] * p["nlg"] - cs * cs))
        return math.floor(2.0 * p["t"] * smin)

    @staticmethod
    def read(p):
        ks = _zcomps(p)
        s0 = 1.0 / p["lam"]
        dl = Zeeman.dl(p)
        qv = Zeeman.q(p, p["x"])
        th = Zeeman.thick(p)
        F = _coef(p["R"])
        I = 0.0
        best = 9.0
        c = 0.0
        ph_c = 0.0
        for i in range(len(ks)):
            ph = 2.0 * th * (s0 + ks[i] * dl) * qv
            I += _airy(F, ph)
            d = abs(ph - _rnd(ph))
            if d < best:
                best = d
                c = i + 1.0
                ph_c = ph
        M = Zeeman.base(p, s0 + ks[0] * dl) if ks else 0.0
        n = (_rnd(ph_c) - M + 1.0) if p["meth"] > 0.5 else (M - _rnd(ph_c) + 1.0)
        return {"x": p["x"], "I": I / max(1, len(ks)), "c": c, "n": n}

    @staticmethod
    def xof(p, s, m):
        if p["meth"] > 0.5:
            g = m / (2.0 * p["tl"] * s)
            cc = p["nlg"] * p["nlg"] - g * g
            if cc <= 0.0 or cc >= 1.0:
                return 0.0
            return p["f"] * math.tan(math.acos(math.sqrt(cc)))
        cs = m / (2.0 * p["t"] * s)
        if cs >= 1.0 or cs <= 0.0:
            return 0.0
        return p["f"] * math.tan(math.acos(cs))

    @staticmethod
    def plan(p):
        ks = _zcomps(p)
        if not ks:
            return []
        s0 = 1.0 / p["lam"]
        dl = Zeeman.dl(p)
        lo = s0 + ks[0] * dl
        hi = s0 + ks[len(ks) - 1] * dl
        M = Zeeman.base(p, lo)
        st = 1.0 if p["meth"] > 0.5 else -1.0
        out = []
        for j in range(2):
            m = M + st * j
            out.append({"x": Zeeman.xof(p, lo, m)})
            out.append({"x": Zeeman.xof(p, hi, m)})
        return out

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "c", "n")
        if len(r) < 2:
            return 0.0
        ks = _zcomps(p)
        if len(ks) < 2:
            return 0.0
        cmin = r[0][1]
        cmax = r[0][1]
        for q in r:
            cmin = min(cmin, q[1])
            cmax = max(cmax, q[1])
        s0 = 1.0 / p["lam"]
        sp = []
        for a in r:
            if abs(a[1] - cmin) > 0.5:
                continue
            for b in r:
                if abs(b[1] - cmax) < 0.5 and abs(b[2] - a[2]) < 0.5:
                    sp.append(s0 * (Zeeman.q(p, a[0]) / Zeeman.q(p, b[0]) - 1.0))
                    break
        tot = _mean(sp)
        if tot <= 0.0:
            return 0.0
        span = ks[len(ks) - 1] - ks[0]
        if p["mode"] > 1.5:
            dl = p["em"] * p["B"] / (4.0 * PI * C_LIGHT)
            return tot / dl / 2.0 if dl > 0.0 else 0.0
        if span <= 0.0 or p["B"] <= 0.0:
            return 0.0
        dl = tot / span
        if p["mode"] > 0.5:
            return H_PLANCK * C_LIGHT * dl / p["B"]
        return 4.0 * PI * C_LIGHT * dl / p["B"]


# ===================================================================================== birefringence of a plate
class Biref(_Scan):
    """A crystal plate of thickness t and birefringence dn (retardation delta = 2 pi dn t / lambda).
    mode 0 / 2 Babinet compensator between crossed polarisers: the dark fringe sits where the compensator's phase
    2 pi (x - x0) / beta cancels the plate's (stage 0 without, stage 1 with the plate). mode 1 / 3 rotating analyser:
    the plate at 45 degrees to the polariser, I(theta) = cos^2 theta - cos 2theta sin^2(delta / 2).
    Result: mode 0 / 1 birefringence dn, mode 2 / 3 retardation dn t (a path difference)."""

    PARAMS = {"dn": 0.0091, "t": 3.0e-5, "lam": 5.893e-7, "beta": 0.004, "x0": 0.005, "mode": 0.0, "stage": 0.0,
              "A": 0.0, "x": 0.005}
    VARS = ["x", "A", "I"]

    @staticmethod
    def delta(p):
        return 2.0 * PI * p["dn"] * p["t"] / p["lam"]

    @staticmethod
    def babinet(p):
        m = int(_rnd(p["mode"]))
        return m == 0 or m == 2

    @staticmethod
    def read(p):
        d = Biref.delta(p) if p["stage"] > 0.5 else 0.0
        if Biref.babinet(p):
            ph = 2.0 * PI * (p["x"] - p["x0"]) / p["beta"] - d
            s = math.sin(ph / 2.0)
            return {"x": p["x"], "I": s * s}
        s = math.sin(d / 2.0)
        c = math.cos(p["A"])
        return {"x": p["x"], "I": c * c - math.cos(2.0 * p["A"]) * s * s}

    @staticmethod
    def plan(p):
        if Biref.babinet(p):
            return [{"stage": 0.0, "x": p["x0"]}, {"stage": 0.0, "x": p["x0"] + p["beta"]},
                    {"stage": 1.0, "x": p["x0"] + p["beta"] * Biref.delta(p) / (2.0 * PI)}]
        return [{"stage": 1.0, "A": 0.0}, {"stage": 1.0, "A": PI / 4.0}, {"stage": 1.0, "A": PI / 2.0}]

    @staticmethod
    def calc(rows, p):
        if Biref.babinet(p):
            r = _rows(rows, "stage", "x")
            z = _sorted_by([q for q in r if q[0] < 0.5], 1)
            s = [q[1] for q in r if q[0] > 0.5]
            if len(z) < 2 or not s:
                return 0.0
            beta = z[1][1] - z[0][1]
            if beta <= 0.0:
                return 0.0
            d = 2.0 * PI * (s[0] - z[0][1]) / beta
        else:
            r = _rows(rows, "A", "I")
            if len(r) < 2:
                return 0.0
            i0 = r[0]
            i9 = r[0]
            for q in r:
                if abs(q[0]) < abs(i0[0]):
                    i0 = q
                if abs(q[0] - PI / 2.0) < abs(i9[0] - PI / 2.0):
                    i9 = q
            tot = i0[1] + i9[1]
            if tot <= 0.0:
                return 0.0
            d = 2.0 * _asin(_sqrt(i9[1] / tot))
        if int(_rnd(p["mode"])) >= 2:
            return d * p["lam"] / (2.0 * PI)
        return d * p["lam"] / (2.0 * PI * p["t"])


# ===================================================================================== elliptically polarised light
def _cm(a, b):
    return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]


def _ca(a, b):
    return [a[0] + b[0], a[1] + b[1]]


def _cs(a, k):
    return [a[0] * k, a[1] * k]


class Ellipse(_Scan):
    """Plane light (polariser at 0) through a retarding plate of retardation delta with its fast axis at phi: elliptical
    light. mode 0 / 1 (quarter-wave plate and analyser): stage 0 the analyser at 0, 45, 90 and 135 degrees gives the
    azimuth of the major axis; stage 1 a quarter-wave plate set along that axis (A) turns the light plane, and the
    analyser's null x gives the ellipticity angle chi = x - 90 deg - A. mode 2 / 3 (Babinet compensator, axes along
    the plate's): the dark fringe's shift gives delta; the analyser that blackens it gives psi = phi; sin 2chi =
    sin 2psi sin delta. Result: mode 0 / 3 the ellipticity b / a, mode 1 the azimuth, mode 2 the retardation."""

    PARAMS = {"del": 1.2, "phi": 0.5235987755982988, "lam": 5.893e-7, "beta": 0.004, "x0": 0.005, "mode": 0.0,
              "stage": 0.0, "A": 0.0, "x": 0.0}
    VARS = ["x", "I"]

    @staticmethod
    def field(p):
        c = math.cos(p["phi"])
        s = math.sin(p["phi"])
        e = [math.cos(p["del"]), math.sin(p["del"])]
        ex = [c * c + s * s * e[0], s * s * e[1]]
        ey = [c * s * (1.0 - e[0]), -c * s * e[1]]
        return ex, ey

    @staticmethod
    def stokes(ex, ey):
        s0 = ex[0] * ex[0] + ex[1] * ex[1] + ey[0] * ey[0] + ey[1] * ey[1]
        s1 = ex[0] * ex[0] + ex[1] * ex[1] - ey[0] * ey[0] - ey[1] * ey[1]
        s2 = 2.0 * (ex[0] * ey[0] + ex[1] * ey[1])
        s3 = 2.0 * (ex[0] * ey[1] - ex[1] * ey[0])
        return [s0, s1, s2, s3]

    @staticmethod
    def qwp(ex, ey, a):
        ca = math.cos(a)
        sa = math.sin(a)
        ea = _ca(_cs(ex, ca), _cs(ey, sa))
        eb = _ca(_cs(ex, -sa), _cs(ey, ca))
        eb = _cm(eb, [0.0, 1.0])
        return _ca(_cs(ea, ca), _cs(eb, -sa)), _ca(_cs(ea, sa), _cs(eb, ca))

    @staticmethod
    def ana(ex, ey, th):
        a = _ca(_cs(ex, math.cos(th)), _cs(ey, math.sin(th)))
        return a[0] * a[0] + a[1] * a[1]

    @staticmethod
    def babinet(p):
        return int(_rnd(p["mode"])) >= 2

    @staticmethod
    def read(p):
        if Ellipse.babinet(p):
            d = p["del"] if p["stage"] > 0.5 else 0.0
            g = 2.0 * PI * (p["x"] - p["x0"]) / p["beta"]
            c = math.cos(p["phi"])
            s = math.sin(p["phi"])
            ar = p["A"] - p["phi"]
            e2 = [-s * math.cos(d - g), -s * math.sin(d - g)]
            amp = _ca([c * math.cos(ar), 0.0], _cs(e2, math.sin(ar)))
            return {"x": p["x"], "I": amp[0] * amp[0] + amp[1] * amp[1]}
        ex, ey = Ellipse.field(p)
        if p["stage"] > 0.5:
            ex, ey = Ellipse.qwp(ex, ey, Ellipse.truth(p)[0])
        return {"x": p["x"], "I": Ellipse.ana(ex, ey, p["A"])}

    @staticmethod
    def truth(p):
        ex, ey = Ellipse.field(p)
        S = Ellipse.stokes(ex, ey)
        return [0.5 * math.atan2(S[2], S[1]), 0.5 * _asin(S[3] / S[0])]

    @staticmethod
    def plan(p):
        if Ellipse.babinet(p):
            return [{"stage": 0.0, "A": PI / 2.0, "x": p["x0"]}, {"stage": 0.0, "A": PI / 2.0, "x": p["x0"] + p["beta"]},
                    {"stage": 1.0, "A": PI / 2.0, "x": p["x0"] + p["beta"] * p["del"] / (2.0 * PI)}]
        al = Ellipse.truth(p)[0]
        ex, ey = Ellipse.field(p)
        ox, oy = Ellipse.qwp(ex, ey, al)
        S = Ellipse.stokes(ox, oy)
        nul = 0.5 * math.atan2(S[2], S[1]) + PI / 2.0
        return [{"stage": 0.0, "A": 0.0}, {"stage": 0.0, "A": PI / 4.0}, {"stage": 0.0, "A": PI / 2.0},
                {"stage": 0.0, "A": 3.0 * PI / 4.0}, {"stage": 1.0, "A": nul}]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "A", "x")
        m = int(_rnd(p["mode"]))
        if Ellipse.babinet(p):
            z = _sorted_by([q for q in r if q[0] < 0.5], 2)
            s = [q for q in r if q[0] > 0.5]
            if len(z) < 2 or not s:
                return 0.0
            beta = z[1][2] - z[0][2]
            if beta <= 0.0:
                return 0.0
            d = 2.0 * PI * (s[0][2] - z[0][2]) / beta
            if m == 2:
                return d
            psi = abs(s[0][1] - PI / 2.0 - p["phi"])
            chi = 0.5 * _asin(math.sin(2.0 * psi) * math.sin(d))
            return abs(math.tan(chi))
        ri = _rows(rows, "stage", "A", "I")
        z = [q for q in ri if q[0] < 0.5]
        if len(z) < 4:
            return 0.0

        def at(a):
            best = z[0]
            for q in z:
                if abs(q[1] - a) < abs(best[1] - a):
                    best = q
            return best[2]

        al = 0.5 * math.atan2(at(PI / 4.0) - at(3.0 * PI / 4.0), at(0.0) - at(PI / 2.0))
        if m == 1:
            return al
        s = [q for q in ri if q[0] > 0.5]
        if not s:
            return 0.0
        chi = s[0][1] - PI / 2.0 - al
        while chi > PI / 2.0:
            chi -= PI
        while chi < -PI / 2.0:
            chi += PI
        return abs(math.tan(chi))


# ===================================================================================== photoelasticity
class Photoel(_Scan):
    """A photoelastic model in a polariscope (dark field: I = sin^2(pi N) at the point watched). Fringe order
    N = C (sigma1 - sigma2) h / lambda with C the stress-optic coefficient. Disc of diameter D under a diametral load F
    (centre): N = 8 F C / (pi D lambda). Beam of depth hb in four-point bending, loads F/2 at a from each support
    (outer fibre): N = 3 C F a / (hb^2 lambda). `n` counts the dark fringes that have passed the point.
    mode 0 the stress-optic coefficient C, mode 1 the fringe order per newton dN/dF."""

    PARAMS = {"C": 5.5e-11, "D": 0.05, "hb": 0.012, "a": 0.03, "lam": 5.461e-7, "shape": 0.0, "pol": 1.0,
              "mode": 0.0, "x": 0.0}
    VARS = ["x", "I", "n"]

    @staticmethod
    def k(p):
        if p["shape"] > 0.5:
            return 3.0 * p["C"] * p["a"] / (p["hb"] * p["hb"] * p["lam"])
        return 8.0 * p["C"] / (PI * p["D"] * p["lam"])

    @staticmethod
    def read(p):
        N = Photoel.k(p) * max(0.0, p["x"])
        s = math.sin(PI * N)
        return {"x": p["x"], "I": s * s, "n": _rnd(N)}

    @staticmethod
    def plan(p):
        k = Photoel.k(p)
        out = [{"x": 0.0}]
        for i in range(1, 5):
            out.append({"x": i / k})
        return out

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "x", "n")
        if len(r) < 3:
            return 0.0
        l = _line([q[1] for q in r], [q[0] for q in r])
        if l[0] <= 0.0:
            return 0.0
        k = 1.0 / l[0]
        if p["mode"] > 0.5:
            return k
        if p["shape"] > 0.5:
            return k * p["hb"] * p["hb"] * p["lam"] / (3.0 * p["a"])
        return k * PI * p["D"] * p["lam"] / 8.0


# ===================================================================================== Kerr and Pockels cells
class Eo(_Scan):
    """An electro-optic cell at 45 degrees between crossed polarisers: P = P0 sin^2(Gamma / 2).
    kind 0 Kerr cell (liquid, plates d apart, path l): Gamma = 2 pi K l (V / d)^2.  kind 1 longitudinal Pockels cell
    (KDP, field along the beam): Gamma = 2 pi n^3 r V / lambda.  kind 2 transverse Pockels cell (lithium niobate, length
    L, electrodes d apart): Gamma = 2 pi n^3 r V L / (lambda d). With a quarter-wave bias, a small signal of amplitude
    Vm at frequency f modulates the light by m = sin(pi Vm H / V_pi), H = 1 / sqrt(1 + (f / fc)^2).
    mode 0 the constant (K or r), 1 the half-wave voltage, 2 V_pi from the modulation depth, 3 the bandwidth fc."""

    PARAMS = {"kind": 0.0, "K": 2.4e-12, "l": 0.05, "d": 0.005, "r": 1.06e-11, "n": 1.51, "L": 0.02,
              "lam": 6.328e-7, "fc": 2.0e4, "f0": 1.0e3, "P0": 1.0e-3, "mode": 0.0, "A": 0.0, "x": 0.0}
    VARS = ["x", "A", "P", "m"]

    @staticmethod
    def vpi(p):
        k = int(_rnd(p["kind"]))
        n3 = p["n"] * p["n"] * p["n"]
        if k == 0:
            return p["d"] / _sqrt(2.0 * p["K"] * p["l"])
        if k == 1:
            return p["lam"] / (2.0 * n3 * p["r"])
        return p["lam"] * p["d"] / (2.0 * n3 * p["r"] * p["L"])

    @staticmethod
    def gam(p, v):
        vp = Eo.vpi(p)
        if int(_rnd(p["kind"])) == 0:
            return PI * (v / vp) * (v / vp)
        return PI * v / vp

    @staticmethod
    def read(p):
        m = int(_rnd(p["mode"]))
        if m >= 2:
            if m == 2:
                vm = p["x"]
                f = p["f0"]
            else:
                vm = 0.05 * Eo.vpi(p)
                f = p["A"]
            hh = 1.0 / math.sqrt(1.0 + (f / p["fc"]) * (f / p["fc"]))
            return {"x": p["x"], "A": p["A"], "P": 0.5 * p["P0"], "m": abs(math.sin(PI * vm * hh / Eo.vpi(p)))}
        s = math.sin(Eo.gam(p, p["x"]) / 2.0)
        return {"x": p["x"], "A": p["A"], "P": p["P0"] * s * s, "m": 0.0}

    @staticmethod
    def plan(p):
        m = int(_rnd(p["mode"]))
        vp = Eo.vpi(p)
        if m == 2:
            return [{"x": vp * k} for k in (0.01, 0.02, 0.03, 0.04, 0.05)]
        if m == 3:
            fc = p["fc"]
            return [{"A": fc * k} for k in (0.02, 0.25, 0.5, 1.0, 1.5, 2.5)]
        return [{"x": vp * k} for k in (0.2, 0.4, 0.6, 0.8, 1.0, 1.2)]

    @staticmethod
    def calc(rows, p):
        m = int(_rnd(p["mode"]))
        k = int(_rnd(p["kind"]))
        if m == 2:
            r = _rows(rows, "x", "m")
            if len(r) < 2:
                return 0.0
            l = _line([q[0] for q in r], [_asin(q[1]) for q in r])
            return PI / l[0] if l[0] > 0.0 else 0.0
        if m == 3:
            r = _sorted_by(_rows(rows, "A", "m"), 0)
            if len(r) < 2 or r[0][1] <= 0.0:
                return 0.0
            a0 = _asin(r[0][1])
            fs = []
            for q in r:
                h = _asin(q[1]) / a0
                if 0.0 < h < 0.99:
                    fs.append(q[0] / math.sqrt(1.0 / (h * h) - 1.0))
            return _mean(fs)
        r = _rows(rows, "x", "P")
        if len(r) < 2:
            return 0.0
        top = r[0]
        for q in r:
            if q[1] > top[1]:
                top = q
        if top[1] <= 0.0:
            return 0.0
        vs = []
        for q in r:
            if 0.0 < q[0] <= top[0] and q[1] > 0.0:
                g = 2.0 * _asin(_sqrt(q[1] / top[1]))
                if g <= 0.0:
                    continue
                vs.append(q[0] * math.sqrt(PI / g) if k == 0 else q[0] * PI / g)
        vp = _mean(vs)
        if vp <= 0.0:
            return 0.0
        if m == 1:
            return vp
        n3 = p["n"] * p["n"] * p["n"]
        if k == 0:
            return p["d"] * p["d"] / (2.0 * p["l"] * vp * vp)
        if k == 1:
            return p["lam"] / (2.0 * n3 * vp)
        return p["lam"] * p["d"] / (2.0 * n3 * p["L"] * vp)


# ===================================================================================== Faraday rotation
class Faraday(_Scan):
    """A glass rod of length l in the field B = kB I of an electromagnet or solenoid (read on a gaussmeter), between a
    polariser at 0 and an analyser at x. The plane of polarisation turns by rho = V(lambda) B l, so the null moves to
    x = 90 deg + rho. V(lambda) = V (589.3 nm / lambda)^2 (Becquerel's formula with a Cauchy index).
    mode 0 the Verdet constant (sodium lamp); mode 1 tungsten lamp and three filters (stage = filter): the power p in
    V ~ lambda^-p; mode 2 magneto-optic modulation, analyser at 45 deg, alternating current of amplitude A: depth
    m = sin(2 rho)."""

    PARAMS = {"V": 9.22, "l": 0.1, "kB": 0.05, "lam": 5.893e-7, "l0": 4.5e-7, "l1": 5.5e-7, "l2": 6.5e-7,
              "mode": 0.0, "stage": 0.0, "A": 0.0, "x": 1.5707963267948966}
    VARS = ["x", "A", "B", "P", "m"]

    @staticmethod
    def lam(p):
        if int(_rnd(p["mode"])) == 1:
            s = int(_rnd(p["stage"]))
            return p["l0"] if s <= 0 else (p["l1"] if s == 1 else p["l2"])
        return p["lam"]

    @staticmethod
    def vl(p, lam):
        return p["V"] * (NA_REF / lam) * (NA_REF / lam)

    @staticmethod
    def read(p):
        B = p["kB"] * p["A"]
        rho = Faraday.vl(p, Faraday.lam(p)) * B * p["l"]
        if int(_rnd(p["mode"])) == 2:
            return {"x": p["x"], "A": p["A"], "B": B, "P": 0.0, "m": abs(math.sin(2.0 * rho))}
        c = math.cos(p["x"] - rho)
        return {"x": p["x"], "A": p["A"], "B": B, "P": c * c, "m": 0.0}

    @staticmethod
    def null(p, A, lam):
        return PI / 2.0 + Faraday.vl(p, lam) * p["kB"] * A * p["l"]

    @staticmethod
    def plan(p):
        m = int(_rnd(p["mode"]))
        if m == 2:
            return [{"A": a} for a in (0.5, 1.0, 1.5, 2.0)]
        if m == 1:
            out = []
            for s in range(3):
                lam = p["l0"] if s == 0 else (p["l1"] if s == 1 else p["l2"])
                out.append({"stage": float(s), "A": 0.0, "x": Faraday.null(p, 0.0, lam)})
                out.append({"stage": float(s), "A": 4.0, "x": Faraday.null(p, 4.0, lam)})
            return out
        return [{"A": a, "x": Faraday.null(p, a, p["lam"])} for a in (0.0, 1.0, 2.0, 3.0, 4.0)]

    @staticmethod
    def calc(rows, p):
        m = int(_rnd(p["mode"]))
        if m == 2:
            r = _rows(rows, "B", "m")
            if len(r) < 2:
                return 0.0
            l = _line([q[0] for q in r], [_asin(q[1]) / 2.0 for q in r])
            return l[0] / p["l"]
        if m == 1:
            r = _rows(rows, "stage", "B", "x")
            xs = []
            ys = []
            for s in range(3):
                g = [q for q in r if abs(q[0] - s) < 0.5]
                if len(g) < 2:
                    continue
                lo = g[0]
                hi = g[0]
                for q in g:
                    if q[1] < lo[1]:
                        lo = q
                    if q[1] > hi[1]:
                        hi = q
                if hi[1] - lo[1] <= 0.0:
                    continue
                v = (hi[2] - lo[2]) / ((hi[1] - lo[1]) * p["l"])
                lam = p["l0"] if s == 0 else (p["l1"] if s == 1 else p["l2"])
                if v > 0.0:
                    xs.append(math.log(lam))
                    ys.append(math.log(v))
            if len(xs) < 2:
                return 0.0
            return -_line(xs, ys)[0]
        r = _rows(rows, "B", "x")
        if len(r) < 2:
            return 0.0
        return _line([q[0] for q in r], [q[1] for q in r])[0] / p["l"]


# ===================================================================================== Fraunhofer diffraction
class Fraun(_Scan):
    """A He-Ne laser beam through an object; a screen at L, read with a cursor at x (s = sin atan(x / L)).
    mode 0 a wire mesh / cross grating along one row of spots (pitch d, open width a, N periods lit): I = sinc^2 x
    comb, spots at d s = m lambda;  mode 1 a circular aperture of diameter a: (2 J1(v) / v)^2, dark rings at the zeros
    of J1;  mode 2 a square aperture / mode 3 a single slit of width a: sinc^2, dark at a s = m lambda;  mode 4 a double
    slit (d apart): cos^2 x sinc^2, bright at d s = m lambda;  mode 5 a grating of pitch d: the laser wavelength.
    `m` is the order counted from the centre, as the student counts the spots or the dark bands."""

    PARAMS = {"lam": 6.328e-7, "L": 1.0, "a": 1.0e-4, "d": 2.5e-4, "N": 20.0, "mode": 0.0, "x": 0.0}
    VARS = ["x", "I", "m"]

    @staticmethod
    def s(p, x):
        return math.sin(math.atan(x / p["L"]))

    @staticmethod
    def comb(N, u):
        sn = math.sin(u)
        if abs(sn) < 1e-9:
            return 1.0
        q = math.sin(N * u) / (N * sn)
        return q * q

    @staticmethod
    def read(p):
        m = int(_rnd(p["mode"]))
        s = Fraun.s(p, p["x"])
        lam = p["lam"]
        ua = PI * p["a"] * s / lam
        ud = PI * p["d"] * s / lam
        if m == 1:
            j = 1.0 if abs(ua) < 1e-9 else 2.0 * _jn(1, ua) / ua
            I = j * j
            best = 0
            for i in range(len(J1_ZEROS)):
                if abs(abs(ua) - J1_ZEROS[i]) < abs(abs(ua) - J1_ZEROS[best]):
                    best = i
            k = 0.0 if abs(ua) < 0.5 * J1_ZEROS[0] else best + 1.0
        elif m == 2 or m == 3:
            I = _sinc2(ua)
            k = _rnd(abs(p["a"] * s / lam))
        elif m == 4:
            c = math.cos(ud)
            I = c * c * _sinc2(ua)
            k = _rnd(abs(p["d"] * s / lam))
        else:
            I = _sinc2(ua) * Fraun.comb(p["N"], ud)
            k = _rnd(abs(p["d"] * s / lam))
        return {"x": p["x"], "I": I, "m": k}

    @staticmethod
    def xs(p, s):
        if s >= 1.0:
            return 0.0
        return p["L"] * math.tan(math.asin(s))

    @staticmethod
    def plan(p):
        m = int(_rnd(p["mode"]))
        lam = p["lam"]
        if m == 1:
            return [{"x": Fraun.xs(p, J1_ZEROS[i] * lam / (PI * p["a"]))} for i in range(2)]
        if m == 2 or m == 3:
            return [{"x": Fraun.xs(p, k * lam / p["a"])} for k in (1.0, 2.0, 3.0)]
        if m == 5:
            return [{"x": Fraun.xs(p, k * lam / p["d"])} for k in (1.0, 2.0)]
        return [{"x": Fraun.xs(p, k * lam / p["d"])} for k in (1.0, 2.0, 3.0)]

    @staticmethod
    def calc(rows, p):
        m = int(_rnd(p["mode"]))
        out = []
        for q in _rows(rows, "x", "m"):
            s = abs(Fraun.s(p, q[0]))
            k = q[1]
            if s <= 0.0 or k < 0.5:
                continue
            if m == 1:
                i = int(_rnd(k)) - 1
                if 0 <= i < len(J1_ZEROS):
                    out.append(J1_ZEROS[i] * p["lam"] / (PI * s))
            elif m == 2 or m == 3:
                out.append(k * p["lam"] / s)
            elif m == 5:
                out.append(p["d"] * s / k)
            else:
                out.append(k * p["lam"] / s)
        return _mean(out)


# ===================================================================================== constant deviation spectrometer
class Cdev(_Scan):
    """A constant deviation (Pellin-Broca) spectrometer whose drum is engraved in wavelength but reads
    lambda + e(lambda), e = e0 + e1 (lambda - 550 nm) + e2 (lambda - 550 nm)^2 (the instrument's error). Stage 0 the
    mercury lamp: three known lines calibrate it (a quadratic through the three points); stage 1 the lamp under test:
    the corrected wavelengths of two of its lines. mode 0 their separation, mode 1 the wavelength of the first."""

    PARAMS = {"l1": 5.769610e-7, "l2": 5.790670e-7, "e0": 8.0e-10, "e1": 0.004, "e2": 1.0e4, "w": 1.5e-10,
              "mode": 0.0, "stage": 0.0, "x": 5.5e-7}
    VARS = ["x", "I"]

    @staticmethod
    def drum(p, lam):
        q = lam - 5.5e-7
        return lam + p["e0"] + p["e1"] * q + p["e2"] * q * q

    @staticmethod
    def read(p):
        lines = HG_CAL if p["stage"] < 0.5 else [p["l1"], p["l2"]]
        I = 0.0
        for lam in lines:
            z = (p["x"] - Cdev.drum(p, lam)) / p["w"]
            I += math.exp(-z * z)
        return {"x": p["x"], "I": I}

    @staticmethod
    def plan(p):
        out = [{"stage": 0.0, "x": Cdev.drum(p, lam)} for lam in HG_CAL]
        return out + [{"stage": 1.0, "x": Cdev.drum(p, p["l1"])}, {"stage": 1.0, "x": Cdev.drum(p, p["l2"])}]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "x")
        z = _sorted_by([q for q in r if q[0] < 0.5], 1)
        u = _sorted_by([q for q in r if q[0] > 0.5], 1)
        if len(z) < 3 or not u:
            return 0.0
        xs = [z[0][1], z[1][1], z[2][1]]

        def lam(x):
            tot = 0.0
            for i in range(3):
                w = 1.0
                for j in range(3):
                    if j != i:
                        den = xs[i] - xs[j]
                        if den == 0.0:
                            return 0.0
                        w *= (x - xs[j]) / den
                tot += w * HG_CAL[i]
            return tot

        if p["mode"] > 0.5:
            return lam(u[0][1])
        if len(u) < 2:
            return 0.0
        return lam(u[len(u) - 1][1]) - lam(u[0][1])


# ===================================================================================== concave grating, Rowland mounting
class Rowland(_Scan):
    """A concave grating of radius R and pitch d in a Rowland mounting: slit, grating and plate on the Rowland circle;
    light at incidence alpha, order m. A line of wavelength lambda lands at the arc length s = R beta on the plate,
    d (sin alpha + sin beta) = m lambda; a comparator reads s. Each line has the grating's own profile, sinc^2 of
    pi (lambda - lambda_i) / dl with dl = lambda_i / (m N) (Rayleigh). Lines la < lb are standards, lu the unknown.
    mode 0 the plate factor at (la + lb) / 2, mode 1 the unknown wavelength (interpolated), mode 2 the resolving power
    from the half-intensity width of la (Rayleigh limit = FWHM / 0.886)."""

    PARAMS = {"R": 1.0, "d": 1.6666666666666667e-6, "al": 0.17453292519943295, "m": 1.0, "N": 5000.0,
              "la": 5.460750e-7, "lb": 5.769610e-7, "lu": 5.790670e-7, "mode": 0.0, "x": 0.15}
    VARS = ["x", "I"]

    @staticmethod
    def lam(p, x):
        return p["d"] * (math.sin(p["al"]) + math.sin(x / p["R"])) / p["m"]

    @staticmethod
    def pos(p, lam):
        return p["R"] * _asin(p["m"] * lam / p["d"] - math.sin(p["al"]))

    @staticmethod
    def read(p):
        lam = Rowland.lam(p, p["x"])
        I = 0.0
        for li in (p["la"], p["lb"], p["lu"]):
            dl = li / (p["m"] * p["N"])
            I += _sinc2(PI * (lam - li) / dl)
        return {"x": p["x"], "I": I}

    @staticmethod
    def plan(p):
        m = int(_rnd(p["mode"]))
        if m == 2:
            dl = p["la"] / (p["m"] * p["N"])
            h = SINC2_HALF * dl / PI
            return [{"x": Rowland.pos(p, p["la"] - h)}, {"x": Rowland.pos(p, p["la"])},
                    {"x": Rowland.pos(p, p["la"] + h)}]
        out = [{"x": Rowland.pos(p, p["la"])}, {"x": Rowland.pos(p, p["lb"])}]
        if m == 1:
            out.append({"x": Rowland.pos(p, p["lu"])})
        return out

    @staticmethod
    def calc(rows, p):
        m = int(_rnd(p["mode"]))
        r = _sorted_by(_rows(rows, "x"), 0)
        if len(r) < 2:
            return 0.0
        if m == 2:
            if len(r) < 3:
                return 0.0
            fw = Rowland.lam(p, r[len(r) - 1][0]) - Rowland.lam(p, r[0][0])
            return p["la"] * (2.0 * SINC2_HALF / PI) / fw if fw > 0.0 else 0.0
        dx = r[1][0] - r[0][0]
        if dx <= 0.0:
            return 0.0
        pf = (p["lb"] - p["la"]) / dx
        if m == 1:
            if len(r) < 3:
                return 0.0
            return p["la"] + (r[2][0] - r[0][0]) * pf
        return pf


# ===================================================================================== band heads, Deslandres table
class Band(_Scan):
    """A recorded band spectrum (diatomic molecule, upper state ', lower state "), read with a comparator calibrated in
    wavelength. Band (v', v"): nu = Te + G'(v') - G"(v"), G(v) = we (v + 1/2) - wexe (v + 1/2)^2 (rotation left out:
    the head is taken as the band origin). Heads degraded to the red. The plan reads the heads (2,0), (1,0), (0,0),
    (0,1), (0,2): in order of wavelength. mode 0 wexe", 1 we", 2 we', 3 wexe'."""

    PARAMS = {"Te": 2068895.0, "we1": 87005.0, "wx1": 352.0, "we0": 97923.0, "wx0": 697.0, "w": 2.0e-11,
              "W": 4.0e-10, "mode": 0.0, "x": 4.84e-7}
    VARS = ["x", "I"]
    BANDS = [[2.0, 0.0], [1.0, 0.0], [0.0, 0.0], [0.0, 1.0], [0.0, 2.0], [1.0, 1.0]]

    @staticmethod
    def nu(p, v1, v0):
        g1 = p["we1"] * (v1 + 0.5) - p["wx1"] * (v1 + 0.5) * (v1 + 0.5)
        g0 = p["we0"] * (v0 + 0.5) - p["wx0"] * (v0 + 0.5) * (v0 + 0.5)
        return p["Te"] + g1 - g0

    @staticmethod
    def read(p):
        I = 0.0
        for b in Band.BANDS:
            h = 1.0 / Band.nu(p, b[0], b[1])
            a = math.pow(0.7, b[0] + b[1])
            dx = p["x"] - h
            if dx >= 0.0:
                I += a * math.exp(-dx / p["W"])
            else:
                z = dx / p["w"]
                I += a * math.exp(-z * z)
        return {"x": p["x"], "I": I}

    @staticmethod
    def plan(p):
        return [{"x": 1.0 / Band.nu(p, b[0], b[1])} for b in Band.BANDS[:5]]

    @staticmethod
    def calc(rows, p):
        r = _sorted_by(_rows(rows, "x"), 0)
        if len(r) < 5 or r[0][0] <= 0.0:
            return 0.0
        n = [1.0 / q[0] for q in r[:5]]          # (2,0) (1,0) (0,0) (0,1) (0,2)
        m = int(_rnd(p["mode"]))
        if m <= 1:
            a = n[2] - n[3]
            b = n[3] - n[4]
            wx = (a - b) / 2.0
            return wx if m == 0 else a + 2.0 * wx
        a = n[1] - n[2]
        b = n[0] - n[1]
        wx = (a - b) / 2.0
        return a + 2.0 * wx if m == 2 else wx


# ===================================================================================== a scanned spectrum
class Spec(_Scan):
    """A scanning spectrometer whose drum x reads the wavelength. kind 0 absorption by a solution (bands c1..c5):
    T = exp(-a sum exp(-((x - c) / w)^2)); kind 1 emission (fluorescence bands); kind 2 sunlight: a smooth continuum
    with narrow dark Fraunhofer lines of width w. Each band is located from three readings about it (on a grid of gs):
    the vertex of the parabola through ln(-ln T), ln I or I. mode 0 / 2 the position of band tb, mode 1 the mean
    spacing of the bands in wavenumber."""

    PARAMS = {"kind": 0.0, "c1": 5.07e-7, "c2": 5.26e-7, "c3": 5.46e-7, "c4": 5.66e-7, "c5": 0.0, "w": 6.0e-9,
              "a": 1.0, "tb": 2.0, "gs": 1.0e-9, "Ts": 5778.0, "mode": 0.0, "x": 5.3e-7}
    VARS = ["x", "S"]

    @staticmethod
    def cs(p) -> list[float]:
        return [c for c in (p["c1"], p["c2"], p["c3"], p["c4"], p["c5"]) if c > 0.0]

    @staticmethod
    def read(p):
        k = int(_rnd(p["kind"]))
        tot = 0.0
        for c in Spec.cs(p):
            z = (p["x"] - c) / p["w"]
            tot += math.exp(-z * z)
        if k == 1:
            return {"x": p["x"], "S": tot}
        if k == 2:
            lam = p["x"]
            if lam <= 1e-8:
                return {"x": p["x"], "S": 0.0}
            ref = 5.0e-7
            b = 0.014387768775039337 / p["Ts"]
            cont = (ref / lam) ** 5 * (math.exp(b / ref) - 1.0) / (math.exp(b / lam) - 1.0)
            return {"x": p["x"], "S": cont * (1.0 - p["a"] * tot)}
        return {"x": p["x"], "S": math.exp(-p["a"] * tot)}

    @staticmethod
    def targets(p) -> list[float]:
        c = Spec.cs(p)
        if int(_rnd(p["mode"])) == 1:
            return c
        i = int(_rnd(p["tb"])) - 1
        return [c[i]] if 0 <= i < len(c) else []

    @staticmethod
    def plan(p):
        out = []
        h = p["w"] / 2.0
        for c in Spec.targets(p):
            g = _rnd(c / p["gs"]) * p["gs"]
            out += [{"x": g - h}, {"x": g}, {"x": g + h}]
        return out

    @staticmethod
    def vertex(p, a, b, c):
        k = int(_rnd(p["kind"]))

        def y(v):
            if k == 1:
                return _ln(v)
            if k == 2:
                return v
            return _ln(-_ln(v)) if 0.0 < v < 1.0 else 0.0

        x1, x2, x3 = a[0], b[0], c[0]
        y1, y2, y3 = y(a[1]), y(b[1]), y(c[1])
        den = (x1 - x2) * (x1 - x3) * (x2 - x3)
        if den == 0.0:
            return 0.0
        A = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / den
        Bq = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / den
        if A == 0.0:
            return 0.0
        return -Bq / (2.0 * A)

    @staticmethod
    def calc(rows, p):
        r = _sorted_by(_rows(rows, "x", "S"), 0)
        if len(r) < 3:
            return 0.0
        groups = []
        cur = [r[0]]
        for i in range(1, len(r)):
            if r[i][0] - r[i - 1][0] > 1.5 * p["w"]:
                groups.append(cur)
                cur = []
            cur.append(r[i])
        groups.append(cur)
        vs = []
        for g in groups:
            if len(g) >= 3:
                mid = len(g) // 2
                v = Spec.vertex(p, g[mid - 1], g[mid], g[mid + 1])
                if v > 0.0:
                    vs.append(v)
        if not vs:
            return 0.0
        if int(_rnd(p["mode"])) == 1:
            if len(vs) < 2:
                return 0.0
            return (1.0 / vs[0] - 1.0 / vs[len(vs) - 1]) / (len(vs) - 1)
        return vs[0]


# ===================================================================================== thickness of a film at a step
class Film(_Scan):
    """An evaporated film of thickness t ends in a sharp step; both the film and the bare glass are over-coated with
    silver and faced with a silvered flat (gap G). mode 0 multiple-beam Fizeau fringes in monochromatic light: the gap
    grows lambda / 2 per fringe spacing s along x; on the film the gap is t smaller, so the fringes shift by
    (2 t / lambda) s (stage 0 the bare glass, stage 1 the film). mode 1 fringes of equal chromatic order in white light
    through a spectrometer (x = wavelength): bright where 2 G = m lambda; G = T0 on the glass, T0 - t on the film."""

    PARAMS = {"t": 1.2e-7, "lam": 5.461e-7, "s": 4.0e-4, "F": 60.0, "T0": 2.0e-6, "mode": 0.0, "stage": 0.0,
              "A": 5.0e-7, "x": 4.0e-4}
    VARS = ["x", "A", "I"]

    @staticmethod
    def read(p):
        tt = p["t"] if p["stage"] > 0.5 else 0.0
        if p["mode"] > 0.5:
            G = p["T0"] - tt
            if p["A"] <= 0.0:
                return {"x": p["x"], "A": p["A"], "I": 0.0}
            return {"x": p["x"], "A": p["A"], "I": _airy(p["F"], 2.0 * G / p["A"])}
        gap = (p["lam"] / 2.0) * (p["x"] / p["s"]) - tt
        return {"x": p["x"], "A": p["A"], "I": _airy(p["F"], 2.0 * gap / p["lam"])}

    @staticmethod
    def order(p):
        return math.ceil(2.0 * p["T0"] / 6.5e-7)

    @staticmethod
    def plan(p):
        if p["mode"] > 0.5:
            m = Film.order(p)
            return [{"stage": 0.0, "A": 2.0 * p["T0"] / m}, {"stage": 0.0, "A": 2.0 * p["T0"] / (m + 1.0)},
                    {"stage": 1.0, "A": 2.0 * (p["T0"] - p["t"]) / m}]
        return [{"stage": 0.0, "x": p["s"]}, {"stage": 0.0, "x": 2.0 * p["s"]},
                {"stage": 1.0, "x": p["s"] * (1.0 + 2.0 * p["t"] / p["lam"])}]

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "A" if p["mode"] > 0.5 else "x")
        z = _sorted_by([q for q in r if q[0] < 0.5], 1)
        f = [q for q in r if q[0] > 0.5]
        if len(z) < 2 or not f:
            return 0.0
        if p["mode"] > 0.5:
            hi = z[len(z) - 1][1]
            lo = z[0][1]
            if hi - lo <= 0.0:
                return 0.0
            m = _rnd(lo / (hi - lo))
            return m * (hi - f[0][1]) / 2.0
        s = z[1][1] - z[0][1]
        if s <= 0.0:
            return 0.0
        return (p["lam"] / 2.0) * (f[0][1] - z[0][1]) / s


# ===================================================================================== Stoney: stress from curvature
class Stoney(_Scan):
    """A substrate (thickness hs, biaxial modulus Ms = E / (1 - nu)) of radius R0 before coating; a film of thickness
    hf and stress sigma bends it to 1 / R1 = 1 / R0 + 6 sigma hf / (Ms hs^2) (Stoney). The radius is read with Newton's
    rings against an optical flat: dark ring m at r^2 = m R lambda. Stage 0 before coating, stage 1 after.
    mode 0 the change in curvature, mode 1 the film stress."""

    PARAMS = {"sig": 2.0e8, "hf": 5.0e-7, "hs": 1.0e-3, "Ms": 9.35e10, "R0": 100.0, "lam": 5.893e-7, "mode": 0.0,
              "stage": 0.0, "x": 0.01}
    VARS = ["x", "I", "m"]

    @staticmethod
    def kap(p):
        return 6.0 * p["sig"] * p["hf"] / (p["Ms"] * p["hs"] * p["hs"])

    @staticmethod
    def radius(p, stage):
        if stage < 0.5:
            return p["R0"]
        return 1.0 / (1.0 / p["R0"] + Stoney.kap(p))

    @staticmethod
    def read(p):
        R = Stoney.radius(p, p["stage"])
        q = p["x"] * p["x"] / (R * p["lam"])
        s = math.sin(PI * q)
        return {"x": p["x"], "I": s * s, "m": _rnd(q)}

    @staticmethod
    def plan(p):
        out = []
        for st in (0.0, 1.0):
            R = Stoney.radius(p, st)
            for m in (2.0, 4.0, 6.0):
                out.append({"stage": st, "x": math.sqrt(m * R * p["lam"])})
        return out

    @staticmethod
    def calc(rows, p):
        r = _rows(rows, "stage", "x", "m")
        Rs = []
        for st in (0.0, 1.0):
            g = [q for q in r if abs(q[0] - st) < 0.5]
            if len(g) < 2:
                return 0.0
            l = _line([q[2] for q in g], [q[1] * q[1] for q in g])
            if l[0] <= 0.0:
                return 0.0
            Rs.append(l[0] / p["lam"])
        k = 1.0 / Rs[1] - 1.0 / Rs[0]
        if p["mode"] > 0.5:
            return p["Ms"] * p["hs"] * p["hs"] * k / (6.0 * p["hf"])
        return k


# ===================================================================================== photometry
class Photom(_Scan):
    """A lamp of luminous intensity Iv on a photometer bench; a lux meter (illuminance E = Iv / d^2) and a radiometer
    (irradiance E / K, K the luminous efficacy of the lamp's radiation) at distance d.
    mode 0 the luminous intensity, 1 the power n in E ~ d^-n (the inverse-square check), 2 the irradiance at 1 m."""

    PARAMS = {"Iv": 65.0, "K": 15.0, "mode": 0.0, "x": 0.5}
    VARS = ["x", "E", "Ee"]

    @staticmethod
    def read(p):
        d = max(p["x"], 0.05)
        E = p["Iv"] / (d * d)
        return {"x": p["x"], "E": E, "Ee": E / p["K"]}

    @staticmethod
    def plan(p):
        return [{"x": d} for d in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0)]

    @staticmethod
    def calc(rows, p):
        m = int(_rnd(p["mode"]))
        if m == 1:
            r = _rows(rows, "x", "E")
            r = [q for q in r if q[0] > 0.0 and q[1] > 0.0]
            if len(r) < 2:
                return 0.0
            return -_line([math.log(q[0]) for q in r], [math.log(q[1]) for q in r])[0]
        key = "Ee" if m == 2 else "E"
        r = [q for q in _rows(rows, "x", key) if q[0] > 0.0]
        if len(r) < 2:
            return 0.0
        return _line([1.0 / (q[0] * q[0]) for q in r], [q[1] for q in r])[0]


# ===================================================================================== acousto-optics
class Ao(_Scan):
    """A laser beam crosses a sound wave of frequency f and speed v (wavelength v / f).
    mode 0 Raman-Nath (a thin water cell, many orders): orders at sin theta_m = m lambda f / v on a screen at L,
    intensities J_m(nu)^2;  mode 1 Bragg (a crystal set at the Bragg angle): one first order deflected by 2 theta_B,
    sin theta_B = lambda f / (2 v);  mode 2 the Bragg cell's efficiency against the drive power A:
    eta = sin^2((pi / 2) sqrt(A / P100)). Result: modes 0 / 1 the speed of sound, mode 2 P100."""

    PARAMS = {"v": 1497.0, "f": 1.0e7, "lam": 6.328e-7, "L": 1.0, "nu": 1.5, "P100": 1.0, "ws": 3.0e-4,
              "mode": 0.0, "A": 0.0, "x": 0.0}
    VARS = ["x", "A", "I", "m", "eta"]

    @staticmethod
    def xb(p):
        sb = p["lam"] * p["f"] / (2.0 * p["v"])
        return p["L"] * math.tan(2.0 * _asin(sb))

    @staticmethod
    def eta(p, A):
        s = math.sin(PI / 2.0 * _sqrt(A / p["P100"]))
        return s * s

    @staticmethod
    def read(p):
        m = int(_rnd(p["mode"]))
        if m == 2:
            return {"x": p["x"], "A": p["A"], "I": 0.0, "m": 0.0, "eta": Ao.eta(p, p["A"])}
        x = p["x"]
        if m == 1:
            e = Ao.eta(p, p["A"] if p["A"] > 0.0 else 0.5 * p["P100"])
            z0 = x / p["ws"]
            z1 = (x - Ao.xb(p)) / p["ws"]
            I = (1.0 - e) * math.exp(-z0 * z0) + e * math.exp(-z1 * z1)
            return {"x": x, "A": p["A"], "I": I, "m": 1.0 if abs(z1) < abs(z0) else 0.0, "eta": e}
        I = 0.0
        best = 0.0
        bd = 1e30
        for k in range(-3, 4):
            sk = k * p["lam"] * p["f"] / p["v"]
            xk = p["L"] * math.tan(math.asin(sk)) if abs(sk) < 1.0 else 1e9
            z = (x - xk) / p["ws"]
            jk = _jn(abs(k), p["nu"])
            I += jk * jk * math.exp(-z * z)
            if abs(x - xk) < bd:
                bd = abs(x - xk)
                best = abs(k)
        return {"x": x, "A": p["A"], "I": I, "m": best, "eta": 0.0}

    @staticmethod
    def plan(p):
        m = int(_rnd(p["mode"]))
        if m == 2:
            return [{"A": p["P100"] * k} for k in (0.1, 0.2, 0.3, 0.4, 0.5)]
        if m == 1:
            return [{"x": 0.0}, {"x": Ao.xb(p)}]
        out = []
        for k in (1.0, 2.0, 3.0):
            sk = k * p["lam"] * p["f"] / p["v"]
            out.append({"x": p["L"] * math.tan(_asin(sk))})
        return out

    @staticmethod
    def calc(rows, p):
        m = int(_rnd(p["mode"]))
        if m == 2:
            out = []
            for q in _rows(rows, "A", "eta"):
                a = _asin(_sqrt(q[1]))
                if q[0] > 0.0 and a > 0.0:
                    out.append(PI * PI * q[0] / (4.0 * a * a))
            return _mean(out)
        out = []
        for q in _rows(rows, "x", "m"):
            if q[1] < 0.5 or q[0] <= 0.0:
                continue
            th = math.atan(q[0] / p["L"])
            if m == 1:
                out.append(p["lam"] * p["f"] / (2.0 * math.sin(th / 2.0)))
            else:
                out.append(q[1] * p["lam"] * p["f"] / math.sin(th))
        return _mean(out)


# ===================================================================================== ellipsometry
def _c(a, b=0.0):
    return [a, b]


def _cadd(a, b):
    return [a[0] + b[0], a[1] + b[1]]


def _csub(a, b):
    return [a[0] - b[0], a[1] - b[1]]


def _cmul(a, b):
    return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]


def _cdiv(a, b):
    d = b[0] * b[0] + b[1] * b[1]
    if d == 0.0:
        return [0.0, 0.0]
    return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]


def _cabs2(a):
    return a[0] * a[0] + a[1] * a[1]


def _csqrt(a):
    r = math.sqrt(a[0] * a[0] + a[1] * a[1])
    re = _sqrt((r + a[0]) / 2.0)
    im = _sqrt((r - a[0]) / 2.0)
    return [re, im if a[1] >= 0.0 else -im]


def _cexpi(t):
    return [math.cos(t), math.sin(t)]


class Ellips(_Scan):
    """An ellipsometer at angle of incidence phi (stage 0, 1, 2 = phi0, phi1, phi2). The sample reflects with
    rho = r_p / r_s = tan(Psi) e^(i Delta): a film (index n1, thickness d) on a substrate N2 = n2 + i k2 (Airy summation,
    beta = 2 pi d N1 cos(theta1) / lambda), or a bulk metal N2 (sample 1). meth 0 null ellipsometry (polariser x,
    quarter-wave compensator at +45 deg, analyser A): the null is at A = Psi, x = (270 deg - Delta) / 2. meth 1 rotating
    analyser, polariser at 45 deg: I0 = |r_p|^2, I90 = |r_s|^2, I45 - I135 = 2 Re(r_p r_s*). The film's thickness is found
    by matching rho(d) over one period of d; the metal's index from eps = sin^2 phi [1 + tan^2 phi ((1 - rho)/(1 + rho))^2].
    mode 0 film thickness, 1 metal's n, 2 metal's k."""

    PARAMS = {"phi0": 1.0471975511965976, "phi1": 1.2217304763960306, "phi2": 1.1344640137963142, "n1": 1.457,
              "d": 1.0e-7, "n2": 3.882, "k2": 0.019, "lam": 6.328e-7, "sample": 0.0, "meth": 0.0, "mode": 0.0,
              "stage": 0.0, "A": 0.0, "x": 0.0}
    VARS = ["x", "A", "I"]

    @staticmethod
    def phi(p, st):
        s = int(_rnd(st))
        return p["phi0"] if s <= 0 else (p["phi1"] if s == 1 else p["phi2"])

    @staticmethod
    def rho(p, ph, d):
        n0 = _c(1.0)
        n2 = _c(p["n2"], p["k2"])
        s0 = math.sin(ph)
        c0 = _c(math.cos(ph))

        def cosin(N):
            q = _cdiv(_c(s0), N)
            return _csqrt(_csub(_c(1.0), _cmul(q, q)))

        def rp(Na, ca, Nb, cb):
            return _cdiv(_csub(_cmul(Nb, ca), _cmul(Na, cb)), _cadd(_cmul(Nb, ca), _cmul(Na, cb)))

        def rs(Na, ca, Nb, cb):
            return _cdiv(_csub(_cmul(Na, ca), _cmul(Nb, cb)), _cadd(_cmul(Na, ca), _cmul(Nb, cb)))

        c2 = cosin(n2)
        if p["sample"] > 0.5:
            return [rp(n0, c0, n2, c2), rs(n0, c0, n2, c2)]
        n1 = _c(p["n1"])
        c1 = cosin(n1)
        b = _cmul(_c(2.0 * PI * d / p["lam"]), _cmul(n1, c1))
        e = _cmul(_cexpi(-2.0 * b[0]), _c(math.exp(2.0 * b[1])))
        out = []
        for f in (rp, rs):
            a = f(n0, c0, n1, c1)
            g = f(n1, c1, n2, c2)
            ge = _cmul(g, e)
            out.append(_cdiv(_cadd(a, ge), _cadd(_c(1.0), _cmul(a, ge))))
        return out

    @staticmethod
    def psidel(p, st):
        r = Ellips.rho(p, Ellips.phi(p, st), p["d"])
        q = _cdiv(r[0], r[1])
        return [math.atan(math.sqrt(_cabs2(q))), math.atan2(q[1], q[0])]

    @staticmethod
    def read(p):
        r = Ellips.rho(p, Ellips.phi(p, p["stage"]), p["d"])
        rp, rs = r[0], r[1]
        A = p["A"]
        if p["meth"] > 0.5:
            amp = _cadd(_cmul(_c(math.cos(A)), rp), _cmul(_c(math.sin(A)), rs))
            return {"x": p["x"], "A": A, "I": 2.0 * _cabs2(amp) / (_cabs2(rp) + _cabs2(rs))}
        P = p["x"]
        c = math.cos(PI / 4.0)
        a = _c(c * math.cos(P) + c * math.sin(P))
        b = _cmul(_c(-c * math.cos(P) + c * math.sin(P)), _c(0.0, -1.0))
        ex = _csub(_cmul(_c(c), a), _cmul(_c(c), b))
        ey = _cadd(_cmul(_c(c), a), _cmul(_c(c), b))
        amp = _cadd(_cmul(_c(math.cos(A)), _cmul(rp, ex)), _cmul(_c(math.sin(A)), _cmul(rs, ey)))
        return {"x": P, "A": A, "I": 2.0 * _cabs2(amp) / (_cabs2(rp) + _cabs2(rs))}

    @staticmethod
    def plan(p):
        out = []
        for st in (0.0, 1.0, 2.0):
            if p["meth"] > 0.5:
                for a in (0.0, PI / 4.0, PI / 2.0, 3.0 * PI / 4.0):
                    out.append({"stage": st, "A": a})
            else:
                pd = Ellips.psidel(p, st)
                P = (1.5 * PI - pd[1]) / 2.0
                while P < 0.0:
                    P += PI
                while P >= PI:
                    P -= PI
                out.append({"stage": st, "x": P, "A": pd[0]})
        return out

    @staticmethod
    def measured(rows, p):
        """(phi, tan Psi, Delta or cos Delta) for each angle from the table."""
        out = []
        r = _rows(rows, "stage", "A", "I") if p["meth"] > 0.5 else _rows(rows, "stage", "x", "A")
        for st in (0.0, 1.0, 2.0):
            g = [q for q in r if abs(q[0] - st) < 0.5]
            if not g:
                continue
            ph = Ellips.phi(p, st)
            if p["meth"] > 0.5:
                if len(g) < 4:
                    continue

                def at(a):
                    best = g[0]
                    for q in g:
                        if abs(q[1] - a) < abs(best[1] - a):
                            best = q
                    return best[2]

                i0 = at(0.0)
                i9 = at(PI / 2.0)
                if i0 <= 0.0 or i9 <= 0.0:
                    continue
                cd = (at(PI / 4.0) - at(3.0 * PI / 4.0)) / (2.0 * math.sqrt(i0 * i9))
                out.append([ph, math.sqrt(i0 / i9), _acos(cd), 1.0])
            else:
                A = g[0][2]
                psi = A
                while psi < 0.0:
                    psi += PI
                while psi >= PI:
                    psi -= PI
                if psi > PI / 2.0:
                    psi = PI - psi
                out.append([ph, math.tan(psi), 1.5 * PI - 2.0 * g[0][1], 0.0])
        return out

    @staticmethod
    def miss(p, ph, d, m):
        r = Ellips.rho(p, ph, d)
        q = _cdiv(r[0], r[1])
        tp = math.sqrt(_cabs2(q))
        if m[3] > 0.5:
            cd = q[0] / tp if tp > 0.0 else 0.0
            return (tp - m[1]) * (tp - m[1]) + (cd - math.cos(m[2])) * (cd - math.cos(m[2]))
        z = _csub(q, _cmul(_c(m[1]), _cexpi(m[2])))
        return _cabs2(z)

    @staticmethod
    def thick(p, m):
        ph = m[0]
        s = math.sin(ph)
        per = p["lam"] / (2.0 * _sqrt(p["n1"] * p["n1"] - s * s))
        if per <= 0.0:
            return 0.0
        best = 0.0
        bv = 1e30
        for i in range(400):
            d = per * i / 400.0
            v = Ellips.miss(p, ph, d, m)
            if v < bv:
                bv = v
                best = d
        lo = best - per / 400.0
        hi = best + per / 400.0
        g = 0.6180339887498949
        for _ in range(60):
            a = hi - g * (hi - lo)
            b = lo + g * (hi - lo)
            if Ellips.miss(p, ph, a, m) < Ellips.miss(p, ph, b, m):
                hi = b
            else:
                lo = a
        return (lo + hi) / 2.0

    @staticmethod
    def metal(m):
        ph = m[0]
        rho = _cmul(_c(m[1]), _cexpi(m[2]))
        if m[3] > 0.5:
            rho = _cmul(_c(m[1]), [math.cos(m[2]), -math.sin(m[2])])
        f = _cdiv(_csub(_c(1.0), rho), _cadd(_c(1.0), rho))
        t = math.tan(ph)
        s = math.sin(ph)
        eps = _cmul(_c(s * s), _cadd(_c(1.0), _cmul(_c(t * t), _cmul(f, f))))
        return _csqrt(eps)

    @staticmethod
    def calc(rows, p):
        ms = Ellips.measured(rows, p)
        if not ms:
            return 0.0
        m = int(_rnd(p["mode"]))
        vals = []
        for q in ms:
            if m == 0:
                vals.append(Ellips.thick(p, q))
            else:
                N = Ellips.metal(q)
                vals.append(N[0] if m == 1 else N[1])
        return _mean(vals)


# ===================================================================================== optical particle counter
OPC_EDGES = [3.0e-7, 5.0e-7, 7.0e-7, 1.0e-6, 2.0e-6, 3.0e-6, 5.0e-6, 1.0e-5]


def _erf(x: float) -> float:
    """Abramowitz and Stegun 7.1.26 (|error| < 1.5e-7)."""
    sg = 1.0 if x >= 0.0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x)
    return sg * y


class Aerosol(_Scan):
    """SIMULATED DATA. An optical particle counter samples air at flow Q for a time t and sorts the particles by the
    light each one scatters into eight size channels (lower edges 0.3, 0.5, 0.7, 1, 2, 3, 5, 10 um). The air carries a
    lognormal number distribution: total N, count median diameter cmd, geometric standard deviation sg. Channel k counts
    N Q t (F(e_k+1) - F(e_k)), F the lognormal CDF. mode 0 the number concentration above 0.3 um (sum of counts / (Q t)),
    mode 1 the median diameter of the counted particles (log interpolation of the cumulative count)."""

    PARAMS = {"N": 1.5e8, "cmd": 6.0e-7, "sg": 2.0, "Q": 4.717e-5, "t": 60.0, "mode": 0.0, "x": 1.0}
    VARS = ["x", "C"]

    @staticmethod
    def F(p, d):
        if d <= 0.0:
            return 0.0
        return 0.5 * (1.0 + _erf(math.log(d / p["cmd"]) / (math.sqrt(2.0) * math.log(p["sg"]))))

    @staticmethod
    def read(p):
        k = int(_rnd(p["x"]))
        if k < 1 or k > len(OPC_EDGES):
            return {"x": p["x"], "C": 0.0}
        lo = Aerosol.F(p, OPC_EDGES[k - 1])
        hi = Aerosol.F(p, OPC_EDGES[k]) if k < len(OPC_EDGES) else 1.0
        return {"x": p["x"], "C": p["N"] * p["Q"] * p["t"] * (hi - lo)}

    @staticmethod
    def plan(p):
        return [{"x": float(k)} for k in range(1, len(OPC_EDGES) + 1)]

    @staticmethod
    def calc(rows, p):
        r = _sorted_by(_rows(rows, "x", "C"), 0)
        if len(r) < 2:
            return 0.0
        tot = 0.0
        for q in r:
            tot += q[1]
        if p["mode"] < 0.5:
            return tot / (p["Q"] * p["t"])
        half = tot / 2.0
        c = 0.0
        for q in r:
            k = int(_rnd(q[0]))
            if k < 1 or k > len(OPC_EDGES):
                continue
            if c + q[1] >= half and q[1] > 0.0:
                lo = OPC_EDGES[k - 1]
                hi = OPC_EDGES[k] if k < len(OPC_EDGES) else 2.0 * lo
                f = (half - c) / q[1]
                return math.exp(math.log(lo) + f * (math.log(hi) - math.log(lo)))
            c += q[1]
        return 0.0

    @staticmethod
    def truth(p):
        if p["mode"] < 0.5:
            return p["N"] * (1.0 - Aerosol.F(p, OPC_EDGES[0]))
        f0 = Aerosol.F(p, OPC_EDGES[0])
        target = f0 + (1.0 - f0) / 2.0
        a = OPC_EDGES[0]
        b = 1.0e-4
        for _ in range(80):
            m = math.sqrt(a * b)
            if Aerosol.F(p, m) < target:
                a = m
            else:
                b = m
        return a


KERNELS: dict[str, Any] = {
    "po9_fp": Fp, "po9_zeeman": Zeeman, "po9_biref": Biref, "po9_ellipse": Ellipse, "po9_photoel": Photoel,
    "po9_eo": Eo, "po9_faraday": Faraday, "po9_fraun": Fraun, "po9_cdev": Cdev, "po9_rowland": Rowland,
    "po9_band": Band, "po9_spec": Spec, "po9_film": Film, "po9_stoney": Stoney, "po9_photom": Photom, "po9_ao": Ao,
    "po9_ellipso": Ellips, "po9_aerosol": Aerosol,
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
    "po9_fp": {"label": "from the ring readings", "unit": "", "needs": ["x", "c", "n"], "fn": _calc(Fp)},
    "po9_zeeman": {"label": "from the Zeeman pattern", "unit": "", "needs": ["x", "c", "n"], "fn": _calc(Zeeman)},
    "po9_biref": {"label": "birefringence / retardation", "unit": "", "needs": ["stage", "I"], "fn": _calc(Biref)},
    "po9_ellipse": {"label": "the polarisation ellipse", "unit": "", "needs": ["stage", "A", "I"], "fn": _calc(Ellipse)},
    "po9_photoel": {"label": "stress-optic coefficient", "unit": "", "needs": ["x", "n"], "fn": _calc(Photoel)},
    "po9_eo": {"label": "electro-optic constant / half-wave voltage", "unit": "", "needs": ["x"], "fn": _calc(Eo)},
    "po9_faraday": {"label": "Verdet constant", "unit": "", "needs": ["B"], "fn": _calc(Faraday)},
    "po9_fraun": {"label": "from the diffraction pattern", "unit": "m", "needs": ["x", "m"], "fn": _calc(Fraun)},
    "po9_cdev": {"label": "corrected wavelength", "unit": "m", "needs": ["stage", "x"], "fn": _calc(Cdev)},
    "po9_rowland": {"label": "from the plate", "unit": "", "needs": ["x"], "fn": _calc(Rowland)},
    "po9_band": {"label": "vibrational constant", "unit": "1/m", "needs": ["x"], "fn": _calc(Band)},
    "po9_spec": {"label": "band position", "unit": "", "needs": ["x", "S"], "fn": _calc(Spec)},
    "po9_film": {"label": "film thickness", "unit": "m", "needs": ["stage"], "fn": _calc(Film)},
    "po9_stoney": {"label": "curvature / film stress", "unit": "", "needs": ["stage", "x", "m"], "fn": _calc(Stoney)},
    "po9_photom": {"label": "luminous intensity", "unit": "", "needs": ["x", "E", "Ee"], "fn": _calc(Photom)},
    "po9_ao": {"label": "speed of sound / P100", "unit": "", "needs": ["m"], "fn": _calc(Ao)},
    "po9_ellipso": {"label": "film thickness / optical constants", "unit": "", "needs": ["stage", "A", "I"], "fn": _calc(Ellips)},
    "po9_aerosol": {"label": "number concentration / median diameter", "unit": "", "needs": ["x", "C"], "fn": _calc(Aerosol)},
}


def _zt(p):
    ks = _zcomps(p)
    if int(_rnd(p["mode"])) == 2:
        return (ks[len(ks) - 1] - ks[0]) / 2.0 if ks else 0.0
    return p["em"] * H_PLANCK / (4.0 * PI) if int(_rnd(p["mode"])) == 1 else p["em"]


def _eot(p):
    m = int(_rnd(p["mode"]))
    if m == 3:
        return p["fc"]
    if m >= 1:
        return Eo.vpi(p)
    k = int(_rnd(p["kind"]))
    return p["K"] if k == 0 else p["r"]


def _bandt(p):
    m = int(_rnd(p["mode"]))
    return [p["wx0"], p["we0"], p["we1"], p["wx1"]][m] if 0 <= m <= 3 else 0.0


def _spect(p):
    c = Spec.cs(p)
    if int(_rnd(p["mode"])) == 1:
        return (1.0 / c[0] - 1.0 / c[len(c) - 1]) / (len(c) - 1) if len(c) > 1 else 0.0
    i = int(_rnd(p["tb"])) - 1
    return c[i] if 0 <= i < len(c) else 0.0


def _rowt(p):
    m = int(_rnd(p["mode"]))
    if m == 2:
        return p["m"] * p["N"]
    if m == 1:
        return p["lu"]
    lam = (p["la"] + p["lb"]) / 2.0
    beta = math.asin(p["m"] * lam / p["d"] - math.sin(p["al"]))
    return p["d"] * math.cos(beta) / (p["m"] * p["R"])


TEXTBOOK = {
    # a satellite dsig above the line; the etalon spacing; the ideal finesse pi sqrt(R) / (1 - R)
    "po9_fp": lambda p: [p["ds"], p["t"], PI * math.sqrt(p["R"]) / (1.0 - p["R"])][int(_rnd(p["mode"]))],
    # e/m (CODATA 2018), the Bohr magneton (e/m) hbar / 2, and the upper level's g from the outer sigma components
    "po9_zeeman": _zt,
    "po9_biref": lambda p: p["dn"] * p["t"] if int(_rnd(p["mode"])) >= 2 else p["dn"],
    # the ellipse from Stokes' parameters: sin 2chi = S3 / S0, tan 2alpha = S2 / S1
    "po9_ellipse": lambda p: (Ellipse.truth(p)[0] if int(_rnd(p["mode"])) == 1 else
                              (p["del"] if int(_rnd(p["mode"])) == 2 else abs(math.tan(Ellipse.truth(p)[1])))),
    "po9_photoel": lambda p: Photoel.k(p) if p["mode"] > 0.5 else p["C"],
    "po9_eo": _eot,
    # V at the lamp's wavelength; the Becquerel power 2; V again for the modulation method
    "po9_faraday": lambda p: 2.0 if int(_rnd(p["mode"])) == 1 else Faraday.vl(p, p["lam"]),
    "po9_fraun": lambda p: p["lam"] if int(_rnd(p["mode"])) == 5 else (p["d"] if int(_rnd(p["mode"])) in (0, 4) else p["a"]),
    "po9_cdev": lambda p: p["l1"] if p["mode"] > 0.5 else p["l2"] - p["l1"],
    "po9_rowland": _rowt,
    "po9_band": _bandt,
    "po9_spec": _spect,
    "po9_film": lambda p: p["t"],
    "po9_stoney": lambda p: p["sig"] if p["mode"] > 0.5 else Stoney.kap(p),
    "po9_photom": lambda p: [p["Iv"], 2.0, p["Iv"] / p["K"]][int(_rnd(p["mode"]))],
    "po9_ao": lambda p: p["P100"] if int(_rnd(p["mode"])) == 2 else p["v"],
    # the film thickness d, or the metal's own n and k
    "po9_ellipso": lambda p: [p["d"], p["n2"], p["k2"]][int(_rnd(p["mode"]))],
    # the lognormal's own number above 0.3 um, or the median of that truncated distribution
    "po9_aerosol": Aerosol.truth,
}
