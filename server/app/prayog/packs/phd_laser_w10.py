"""Kernel pack `phd_laser_w10`: Ph.D. laser spectroscopy, atomic physics, interferometry and quantum optics,
wave 10 (kernels `pl10_*`).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/phd_laser_w10.js` (same formulas, same order of operations, same numbers).

Every kernel here is a SWEEP (the wave-9 pattern): the student sets one control `x` (a cursor frequency, an RF
frequency, a current, a crystal angle, a sample position, a delay, a polariser setting...) in one or more stages
`s`, and reads the instrument. `read(p, s, x, k)` gives the reading (k numbers the reading, so a photon count is the
same Poisson number on both sides), `xs(p, s)` lists the settings a careful student takes, `fit(rows, p)` works the
result out of the recorded rows exactly as the rig does, and `measure(p)` runs the plan and the fit. A lab may ask for
one of several results with the parameter `q`; the lab's check compares `measure()["res"]` with the textbook relation
in TEXTBOOK.

Photon counting (TCSPC, Hong-Ou-Mandel, CHSH, single-photon interference) is a Poisson draw from the lab's own seed
(Lehmer generator; above 50 counts the Gaussian approximation): SIMULATED DATA, and the labs say so. Everything else is
deterministic and rounded to the instrument's least count. No randomness from the system, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
LN2 = math.log(2.0)
C0 = 299792458.0               # speed of light, m/s (exact)
H = 6.62607015e-34             # Planck constant, J s (exact, SI 2019)
HBAR = H / (2.0 * PI)
KB = 1.380649e-23              # Boltzmann constant, J/K (exact, SI 2019)
MUB = 9.2740100783e-24         # Bohr magneton, J/T (CODATA 2018)
MU0 = 1.25663706212e-6         # vacuum permeability, N/A^2 (CODATA 2018)
AMU = 1.66053906660e-27        # atomic mass unit, kg (CODATA 2018)
RINF = 10973731.568160         # Rydberg constant, 1/m (CODATA 2018)
ME_MP = 1.0 / 1836.15267343    # electron / proton mass ratio (CODATA 2018)
ZETA3 = 1.2020569031595942     # Riemann zeta(3)


# ============================================================================================ helpers (twinned)
def _q(v: float, q: float) -> float:
    """Round to the least count q."""
    return math.floor(v / q + 0.5) * q


def _erfc(x: float) -> float:
    """Abramowitz and Stegun 7.1.26 (|error| < 1.5e-7), the same expression in both twins."""
    if x < 0:
        return 2.0 - _erfc(-x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    return poly * math.exp(-x * x)


class Rnd:
    """Lehmer (MINSTD) generator s -> 16807 s mod (2^31 - 1)."""

    def __init__(self, seed: float) -> None:
        self.s = int(abs(seed)) % 2147483646 + 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647.0

    def count(self, mean: float) -> float:
        """A Poisson count of this mean: Knuth's product up to 50, the Gaussian (Box-Muller) approximation above."""
        if mean <= 0:
            return 0.0
        if mean > 50:
            u1 = self.next()
            u2 = self.next()
            z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * PI * u2)
            n = math.floor(mean + math.sqrt(mean) * z + 0.5)
            return float(n) if n > 0 else 0.0
        lim = math.exp(-mean)
        k, pr = 0, 1.0
        while True:
            pr *= self.next()
            if pr <= lim:
                return float(k)
            k += 1


def _cnt(p: dict, k: int, mean: float) -> float:
    return Rnd(p["seed"] + 977.0 * k).count(mean)


def _linfit(pts: list) -> list | None:
    n = len(pts)
    if n < 2:
        return None
    sx = sy = sxx = sxy = 0.0
    for q in pts:
        sx += q[0]
        sy += q[1]
        sxx += q[0] * q[0]
        sxy += q[0] * q[1]
    den = n * sxx - sx * sx
    if abs(den) < 1e-300:
        return None
    m = (n * sxy - sx * sy) / den
    return [m, (sy - m * sx) / n]


def _stage(rows: list, s: int) -> list:
    out = []
    for r in rows or []:
        try:
            if int(float(r["s"]) + 0.5) == s and math.isfinite(float(r["x"])) and math.isfinite(float(r["y"])):
                out.append(r)
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _rng(a: float, b: float, d: float) -> list:
    n = int(math.floor((b - a) / d + 0.5))
    return [a + d * i for i in range(n + 1)]


def _half(pts: list, lvl: float, side: int, i0: int) -> float | None:
    i = i0
    while 0 <= i + side < len(pts):
        a, b = pts[i], pts[i + side]
        if (a[1] - lvl) * (b[1] - lvl) <= 0 and a[1] != b[1]:
            return a[0] + (lvl - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        i += side
    return None


def _sorted(rows: list, key: str = "y") -> list:
    pts = [[float(r["x"]), float(r[key])] for r in rows]
    pts.sort(key=lambda q: q[0])
    return pts


def _peakwidth(pts: list, base: float):
    """The highest point of pts and the half-height crossings round it: [centre, FWHM, top]."""
    best, ib = -1e300, -1
    for i, q in enumerate(pts):
        if q[1] > best:
            best, ib = q[1], i
    if ib < 0:
        return None
    lvl = base + (best - base) / 2.0
    a = _half(pts, lvl, -1, ib)
    b = _half(pts, lvl, 1, ib)
    if a is None or b is None:
        return None
    return [(a + b) / 2.0, b - a, best]


def _pk(fn, x: float, w: float, d: float) -> list:
    """Peak search of a scope trace fn round the cursor x (+-w, grid d), refined by a parabola through three points."""
    n = int(math.floor(2.0 * w / d + 0.5))
    best, xb = -1e300, x
    for i in range(n + 1):
        v = x - w + d * i
        y = fn(v)
        if y > best:
            best, xb = y, v
    y0, y1, y2 = fn(xb - d), fn(xb), fn(xb + d)
    den = y0 - 2.0 * y1 + y2
    c = xb + (d * (y0 - y2) / (2.0 * den) if den < 0 else 0.0)
    return [c, fn(c)]


def _bisect(fn, a: float, b: float, lvl: float) -> float:
    fa = fn(a) - lvl
    for _ in range(60):
        m = (a + b) / 2.0
        fm = fn(m) - lvl
        if (fa <= 0) == (fm <= 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2.0


def _fit3(pts: list):
    """Least squares y = a + b cos(ph) + c sin(ph) over [ph, y] points: [a, b, c] (normal equations, Cramer)."""
    s = [[0.0] * 3 for _ in range(3)]
    t = [0.0, 0.0, 0.0]
    for q in pts:
        v = [1.0, math.cos(q[0]), math.sin(q[0])]
        for i in range(3):
            t[i] += v[i] * q[1]
            for j in range(3):
                s[i][j] += v[i] * v[j]

    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))

    d0 = det(s)
    if abs(d0) < 1e-300:
        return None
    out = []
    for c in range(3):
        m = [[t[i] if j == c else s[i][j] for j in range(3)] for i in range(3)]
        out.append(det(m) / d0)
    return out


def _gmin(fn, lo: float, hi: float, n: int, lg: bool) -> float:
    """Minimum of fn on [lo, hi]: the lowest of n + 1 grid points (log-spaced if lg), refined by the parabola through
    it and its neighbours. Twin-safe: only the grid index is chosen by comparison."""
    a = math.log(lo) if lg else lo
    b = math.log(hi) if lg else hi
    d = (b - a) / n
    best, ib = 1e300, 1
    for i in range(1, n):
        u = a + d * i
        v = fn(math.exp(u) if lg else u)
        if v < best:
            best, ib = v, i
    u0, u1, u2 = a + d * (ib - 1), a + d * ib, a + d * (ib + 1)
    y0 = fn(math.exp(u0) if lg else u0)
    y2 = fn(math.exp(u2) if lg else u2)
    den = y0 - 2.0 * best + y2
    u = u1 + (d * (y0 - y2) / (2.0 * den) if den > 0 else 0.0)
    return math.exp(u) if lg else u


class _Sweep:
    """A one-control sweep in NST stages (see the module note)."""

    PARAMS: dict = {"x": 0.0, "s": 0.0}
    VARS = ["t", "x", "y"]
    NST = 1

    @classmethod
    def read(cls, p, s, x, k):            # pragma: no cover - every kernel overrides it
        return {"y": 0.0}

    @classmethod
    def xs(cls, p, s):                    # pragma: no cover
        return []

    @classmethod
    def fit(cls, rows, p):                # pragma: no cover
        return 0.0

    @classmethod
    def plan(cls, p):
        out = []
        for s in range(cls.NST):
            for x in cls.xs(p, s):
                out.append([s, x])
        return out

    @classmethod
    def run(cls, p):
        rows = []
        i = 0
        for sx in cls.plan(p):
            r = cls.read(p, sx[0], sx[1], i)
            i += 1
            row = {"s": sx[0], "x": sx[1]}
            row.update(r)
            rows.append(row)
        return rows

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @classmethod
    def view(cls, st, p, cfg=None):
        r = cls.read(p, int(p["s"] + 0.5), p["x"], 0)
        return {"t": st.get("t", 0.0), "x": p["x"], "y": r["y"]}

    @classmethod
    def measure(cls, p, cfg=None):
        rows = cls.run(p)
        return {"res": cls.fit(rows, p), "n": float(len(rows))}


def _qi(p) -> int:
    return int(p["q"] + 0.5)


# ============================================================================================ saturated absorption
class SatAbs(_Sweep):
    """Doppler-free saturated absorption of the Rb D2 line (780.24 nm) in a natural Rb vapour cell, read as the
    pump-on minus reference difference signal so the Doppler background cancels. Each hyperfine transition F -> F'
    gives a Lorentzian Lamb dip of width w = G sqrt(1 + s0) + lw (natural width G power broadened by the pump, plus the
    laser line width); two transitions sharing the lower level give a crossover exactly half way, from the atoms whose
    Doppler shift puts one beam on each, so its size carries the Doppler factor of that velocity. Frequencies in MHz,
    offsets from the strongest line of each group. Stage 0: 87Rb F=2 group, stage 1: 85Rb F=3 group (cursor x on a
    peak, the scope's peak search reads its centre); stage 2: the F=2 -> F'=3 dip width against the pump saturation
    x = I/Isat. q: 0 = 87Rb F'=3-F'=2 splitting, 1 = 85Rb F'=4-F'=3, 2 = natural width G."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "T": 296.0, "d87a": 266.650, "d87b": 156.947, "d85a": 120.640,
              "d85b": 63.401, "G": 6.0666, "lw": 1.0, "s0": 0.5, "lam": 780.241}
    NST = 3

    @staticmethod
    def dop(p, m):
        """Doppler FWHM (MHz) of the D2 line at the cell temperature for mass m (u)."""
        nu = C0 / (p["lam"] * 1e-9)
        return nu * math.sqrt(8.0 * KB * p["T"] * LN2 / (m * AMU * C0 * C0)) / 1e6

    @staticmethod
    def dens(p):
        """Vapour density relative to 296 K: solid-Rb vapour pressure log10 P = 7.738 - 4215 / T over T."""
        return math.pow(10.0, 7.738 - 4215.0 / p["T"]) / p["T"] / (math.pow(10.0, 7.738 - 4215.0 / 296.0) / 296.0)

    @classmethod
    def lines(cls, p, s):
        if s == 1:
            a, b, m, S = p["d85a"], p["d85b"], 84.911789738, [0.5556, 0.3194, 0.125]
        else:
            a, b, m, S = p["d87a"], p["d87b"], 86.909180527, [0.7, 0.25, 0.05]
        nu = [0.0, -a, -(a + b)]
        D = cls.dop(p, m)
        out = []
        for i in range(3):
            out.append([nu[i], S[i]])
        for i in range(3):
            for j in range(i + 1, 3):
                dv = (nu[i] - nu[j]) / 2.0
                out.append([(nu[i] + nu[j]) / 2.0, 2.0 * math.sqrt(S[i] * S[j]) * math.exp(-4.0 * LN2 * (dv / D) * (dv / D))])
        return out

    @staticmethod
    def width(p, s0):
        return p["G"] * math.sqrt(1.0 + s0) + p["lw"]

    @classmethod
    def sig(cls, p, s, v, s0):
        w = cls.width(p, s0)
        amp = 0.05 * cls.dens(p) * s0 / (1.0 + s0)
        tot = 0.0
        for ln in cls.lines(p, s):
            u = 2.0 * (v - ln[0]) / w
            tot += ln[1] / (1.0 + u * u)
        return amp * tot

    @classmethod
    def read(cls, p, s, x, k):
        if s < 2:
            c = _pk(lambda v: cls.sig(p, s, v, p["s0"]), x, 10.0, 0.05)
            return {"y": _q(c[0], 0.01), "h": _q(c[1] * 1000.0, 0.001)}
        c = _pk(lambda v: cls.sig(p, 0, v, x), 0.0, 4.0, 0.05)
        half = c[1] / 2.0
        a = _bisect(lambda v: -cls.sig(p, 0, v, x), c[0] - 60.0, c[0], -half)
        b = _bisect(lambda v: cls.sig(p, 0, v, x), c[0], c[0] + 60.0, half)
        return {"y": _q(b - a, 0.01), "h": _q(c[1] * 1000.0, 0.001)}

    @classmethod
    def xs(cls, p, s):
        if s == 2:
            return [0.25, 0.5, 1.0, 2.0, 3.0, 4.0]
        return [_q(ln[0], 2.0) for ln in cls.lines(p, s)]

    @classmethod
    def fit(cls, rows, p):
        q = _qi(p)
        if q < 2:
            c = sorted(float(r["y"]) for r in _stage(rows, q))
            if len(c) < 6:
                return 0.0
            return c[5] - c[2]
        f = _linfit([[math.sqrt(1.0 + float(r["x"])), float(r["y"])] for r in _stage(rows, 2)])
        return f[0] if f else 0.0


# ============================================================================================ optical pumping
class OptPump(_Sweep):
    """Optical pumping of natural Rb (D1 light, circularly polarised) in the axial field of a Helmholtz pair. RF at
    frequency f (kHz) depumps the sublevels when h f = gF muB |B| (the low-field limit of the Breit-Rabi formula; the
    quadratic Zeeman shift at a few tens of microtesla is a few tens of hertz and is left out), so the transmitted light
    dips at a coil current I for each isotope. The coil field k I adds to the horizontal Earth's field Be along the axis
    (stage 0) or opposes it (stage 1: the current reversed). k = (4/5)^(3/2) mu0 N / R. For F = I + 1/2,
    gF = gJ / (2 I + 1). Stage 2: the transmitted light against time after the pumping light is unblocked,
    1 - A exp(-t / tau). q: 0 = gF of 87Rb, 1 = nuclear spin of 85Rb, 2 = Earth's horizontal field (microtesla),
    3 = pumping time (ms)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "I85": 2.5, "I87": 1.5, "gJ": 2.00233113, "Be": 3.6e-5, "N": 135.0,
              "R": 0.275, "tau": 8.0, "A": 0.2}
    NST = 3

    @staticmethod
    def k(p):
        return math.pow(0.8, 1.5) * MU0 * p["N"] / p["R"]

    @staticmethod
    def gf(p, I):
        return p["gJ"] / (2.0 * I + 1.0)

    @classmethod
    def cur(cls, p, s, f, I):
        B = H * f * 1000.0 / (cls.gf(p, I) * MUB)
        return (B - p["Be"]) / cls.k(p) if s == 0 else (B + p["Be"]) / cls.k(p)

    @classmethod
    def read(cls, p, s, x, k):
        if s < 2:
            return {"y": _q(cls.cur(p, s, x, p["I87"]) * 1000.0, 0.01), "y2": _q(cls.cur(p, s, x, p["I85"]) * 1000.0, 0.01)}
        return {"y": _q(1.0 - p["A"] * math.exp(-x / p["tau"]), 0.0001)}

    @classmethod
    def xs(cls, p, s):
        if s == 2:
            return [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 14.0, 18.0, 24.0, 80.0]
        return [600.0, 800.0, 1000.0, 1200.0, 1400.0]

    @classmethod
    def lines(cls, rows, key):
        a = _linfit([[float(r["x"]), float(r[key])] for r in _stage(rows, 0)])
        b = _linfit([[float(r["x"]), float(r[key])] for r in _stage(rows, 1)])
        return a, b

    @classmethod
    def fit(cls, rows, p):
        q = _qi(p)
        k = cls.k(p)
        if q < 3:
            a, b = cls.lines(rows, "y" if q == 0 else "y2")
            if not a or not b:
                return 0.0
            m = (a[0] + b[0]) / 2.0                    # mA per kHz
            if m <= 0:
                return 0.0
            g = H * 1000.0 / (MUB * k * m / 1000.0)
            if q == 0:
                return g
            if q == 1:
                return (p["gJ"] / g - 1.0) / 2.0
            return k * (b[1] - a[1]) / 2.0 / 1000.0 * 1e6
        st = _stage(rows, 2)
        if len(st) < 4:
            return 0.0
        inf = None
        for r in st:
            if inf is None or float(r["x"]) > inf[0]:
                inf = [float(r["x"]), float(r["y"])]
        pts = [[float(r["x"]), math.log(inf[1] - float(r["y"]))] for r in st
               if float(r["x"]) < inf[0] and inf[1] - float(r["y"]) > 0.01]
        f = _linfit(pts)
        return -1.0 / f[0] if f and f[0] < 0 else 0.0


# ============================================================================================ H / D isotope shift
class HDShift(_Sweep):
    """A scanning monochromator whose wavelength counter reads dial = lam_air (1 + a) + b (a small calibration error).
    Stage 0: the helium lamp's lines (index x, NIST air wavelengths) calibrate the counter. Stage 1: the Balmer lines
    n = 3..6 of the hydrogen lamp, stage 2: of the deuterium lamp. lam_vac = 1 / (R_M (1/4 - 1/n^2)) with
    R_M = R_inf / (1 + me / M) for the proton and the deuteron; lam_air = lam_vac / n_air. q: 0 = R_H (1/m),
    1 = the deuteron / proton mass ratio from R_D / R_H."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "a": 2.0e-4, "b": 0.35, "rd": 1.99900750139, "nair": 1.000277}
    NST = 3
    HE = [447.1479, 501.5678, 587.5621, 667.8151, 706.5188]

    @staticmethod
    def lam(p, n, deut):
        me_m = ME_MP / p["rd"] if deut else ME_MP
        R = RINF / (1.0 + me_m)
        return 1e9 / (R * (0.25 - 1.0 / (n * n))) / p["nair"]

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            la = cls.HE[int(x + 0.5)]
        else:
            la = cls.lam(p, x, s == 2)
        return {"y": _q(la * (1.0 + p["a"]) + p["b"], 0.0002)}

    @classmethod
    def xs(cls, p, s):
        return [0.0, 1.0, 2.0, 3.0, 4.0] if s == 0 else [3.0, 4.0, 5.0, 6.0]

    @classmethod
    def ryd(cls, rows, p, s, cal):
        sxy = sxx = 0.0
        for r in _stage(rows, s):
            n = float(r["x"])
            la = (float(r["y"]) - cal[1]) / cal[0] * p["nair"] * 1e-9
            u = 0.25 - 1.0 / (n * n)
            sxy += u / la
            sxx += u * u
        return sxy / sxx if sxx > 0 else 0.0

    @classmethod
    def fit(cls, rows, p):
        cal = _linfit([[cls.HE[int(float(r["x"]) + 0.5)], float(r["y"])] for r in _stage(rows, 0)
                       if 0 <= int(float(r["x"]) + 0.5) < 5])
        if not cal or len(_stage(rows, 1)) < 2:
            return 0.0
        rh = cls.ryd(rows, p, 1, cal)
        if _qi(p) == 0:
            return rh
        if len(_stage(rows, 2)) < 2:
            return 0.0
        rD = cls.ryd(rows, p, 2, cal)
        me_md = (1.0 + ME_MP) * rh / rD - 1.0
        return ME_MP / me_md if me_md > 0 else 0.0


# ============================================================================================ diode laser
class DiodeLaser(_Sweep):
    """A free-running diode laser. Light out from the steady state of the rate equations with a spontaneous-emission
    factor beta: with r = I / Ith the normalised photon number is s = ((r - 1) + sqrt((r - 1)^2 + 4 beta r)) / 2, and
    P = eta Ith s (so P -> eta (I - Ith) well above threshold). The threshold rises with temperature as
    Ith(T) = Ith0 exp((T - 25) / T0). The wavelength tunes with current (dlI, nm/mA) and case temperature (dlT, nm/K),
    mode hops averaged out. Stage 0: P against I at 25 C, stage 1: wavelength against I at 25 C, stage 2: wavelength
    against the case temperature at Iop. q: 0 = threshold (mA), 1 = slope efficiency (W/A), 2 = dlI, 3 = dlT."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "Ith": 32.5, "eta": 0.82, "beta": 1.0e-4, "T0": 60.0, "lam0": 780.0,
              "dlI": 0.0065, "dlT": 0.27, "Iop": 60.0, "Imax": 90.0}
    NST = 3

    @staticmethod
    def power(p, I, T):
        ith = p["Ith"] * math.exp((T - 25.0) / p["T0"])
        r = I / ith
        s = ((r - 1.0) + math.sqrt((r - 1.0) * (r - 1.0) + 4.0 * p["beta"] * r)) / 2.0
        return p["eta"] * ith * s                  # mW, with I in mA and eta in W/A

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            return {"y": _q(cls.power(p, x, 25.0), 0.01)}
        if s == 1:
            return {"y": _q(p["lam0"] + p["dlI"] * (x - p["Iop"]), 0.0001)}
        return {"y": _q(p["lam0"] + p["dlT"] * (x - 25.0), 0.0001)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return _rng(0.0, p["Imax"], p["Imax"] / 18.0)
        if s == 1:
            return _rng(p["Iop"] - 20.0, p["Iop"] + 20.0, 5.0)
        return _rng(15.0, 35.0, 2.5)

    @classmethod
    def fit(cls, rows, p):
        q = _qi(p)
        if q < 2:
            st = _stage(rows, 0)
            top = 0.0
            for r in st:
                top = max(top, float(r["y"]))
            f = _linfit([[float(r["x"]), float(r["y"])] for r in st if float(r["y"]) > 0.25 * top])
            if not f or f[0] <= 0:
                return 0.0
            return -f[1] / f[0] if q == 0 else f[0]
        f = _linfit([[float(r["x"]), float(r["y"])] for r in _stage(rows, q - 1)])
        return f[0] if f else 0.0


# ============================================================================================ frequency lock
class FreqLock(_Sweep):
    """A diode laser locked to a saturated-absorption dip (Lorentzian, FWHM Gd MHz, height Hd V). Side-of-fringe
    (m = 0): the error signal is the dip signal minus half its height, locked at the half-height point, slope Hd / Gd.
    Dither lock (m = 1): the current is dithered by a MHz and a lock-in gives a y'(detuning), zero at the line centre,
    slope 8 a Hd / Gd^2 (lock-in gain 1). An integrating servo of gain Ki (Hz per V/MHz) closes the loop with
    unity-gain frequency fu = D Ki, so a frequency disturbance at f is suppressed to f / sqrt(f^2 + fu^2).
    White free-running frequency noise S0 (Hz^2/Hz) leaves sigma^2 = S0 (B - fu atan(B / fu)) in a band B; on the side of
    the fringe, intensity noise (RIN, 1/Hz) of the signal Hd/2 is read as a frequency error and written onto the laser
    inside the loop band, adding (Hd / 2)^2 RIN / D^2 fu atan(B / fu) (D in V/Hz). Stage 0: error signal against the
    detuning from the lock point (MHz), stage 1: suppression against the disturbance frequency (Hz), stage 2: rms
    out-of-loop frequency noise (kHz) against the measurement band B (Hz). q: 0 = lock bandwidth fu (Hz),
    1 = residual rms frequency noise in 100 kHz (kHz)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "m": 0.0, "Gd": 12.0, "Hd": 0.8, "a": 1.0, "Ki": 3.0e5, "S0": 2.0e5,
              "rin": 1.0e-10}
    NST = 3

    @staticmethod
    def slope(p):
        return p["Hd"] / p["Gd"] if p["m"] < 0.5 else 8.0 * p["a"] * p["Hd"] / (p["Gd"] * p["Gd"])

    @classmethod
    def fu(cls, p):
        return cls.slope(p) * p["Ki"]

    @staticmethod
    def err(p, d):
        if p["m"] < 0.5:
            u = 2.0 * (d + p["Gd"] / 2.0) / p["Gd"]
            return p["Hd"] / (1.0 + u * u) - p["Hd"] / 2.0
        u = 2.0 * d / p["Gd"]
        return -p["a"] * p["Hd"] * 8.0 * d / (p["Gd"] * p["Gd"]) / ((1.0 + u * u) * (1.0 + u * u))

    @classmethod
    def sigma(cls, p, B):
        fu = cls.fu(p)
        v = p["S0"] * (B - fu * math.atan(B / fu))
        if p["m"] < 0.5:
            D = cls.slope(p) / 1e6
            v += (p["Hd"] / 2.0) * (p["Hd"] / 2.0) * p["rin"] / (D * D) * fu * math.atan(B / fu)
        return math.sqrt(v)

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            return {"y": _q(cls.err(p, x), 0.0001)}
        if s == 1:
            fu = cls.fu(p)
            return {"y": _q(x / math.sqrt(x * x + fu * fu), 0.0001)}
        return {"y": _q(cls.sigma(p, x) / 1000.0, 0.01)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return _rng(-0.5, 0.5, 0.25)
        if s == 1:
            return [1000.0, 3000.0, 10000.0, 30000.0, 100000.0, 300000.0]
        return [1000.0, 10000.0, 100000.0]

    @classmethod
    def fit(cls, rows, p):
        f = _linfit([[float(r["x"]), float(r["y"])] for r in _stage(rows, 0)])
        if not f or f[0] == 0:
            return 0.0
        D = abs(f[0])
        if _qi(p) == 1:
            for r in _stage(rows, 2):
                if abs(float(r["x"]) - 100000.0) < 1.0:
                    return float(r["y"])
            return 0.0
        g = _linfit([[1.0 / (float(r["x"]) * float(r["x"])), 1.0 / (float(r["y"]) * float(r["y"]))]
                     for r in _stage(rows, 1) if float(r["y"]) > 0])
        if not g or g[0] <= 0:
            return 0.0
        return math.sqrt(g[0]) if D > 0 else 0.0


# ============================================================================================ second harmonic
def _sell(cry, lam, ext):
    """Sellmeier indices (lam in micrometres): [n_o, n_e]. cry 0 = KDP, 1 = BBO."""
    l2 = lam * lam
    if cry < 0.5:
        no = 2.259276 + 0.01008956 / (l2 - 0.012942625) + 13.00522 * l2 / (l2 - 400.0)
        ne = 2.132668 + 0.008637494 / (l2 - 0.012281043) + 3.2279924 * l2 / (l2 - 400.0)
    else:
        no = 2.7359 + 0.01878 / (l2 - 0.01822) - 0.01354 * l2
        ne = 2.3753 + 0.01224 / (l2 - 0.01667) - 0.01516 * l2
    return [math.sqrt(no), math.sqrt(ne)]


class SHG(_Sweep):
    """Type-I (ooe) second harmonic generation of a 1064 nm beam in a negative uniaxial crystal of length L (mm).
    Undepleted pump: P2 = eta P^2 sinc^2(dk L / 2) with dk = (4 pi / lam) (n_e(2w, theta) - n_o(w)) and
    1 / n_e(theta)^2 = cos^2 theta / n_o^2 + sin^2 theta / n_e^2 (Sellmeier indices). The crystal is cut at thc to the
    optic axis and tilted by the external angle x; inside, theta = thc + asin(sin x / n_o(w)). Stage 0: P2 (mW)
    against the fundamental power P (W) at the tilt of the peak, stage 1: P2 against the tilt at Pf. q: 0 = the
    exponent of P2 against P (2 for SHG), 1 = the phase-matching angle (degrees)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "cry": 1.0, "lam": 1.064, "L": 5.0, "thc": 22.5, "eta": 1.0e-4,
              "Pf": 2.0, "span": 0.5}
    NST = 2

    @staticmethod
    def theta_pm(p):
        w = _sell(p["cry"], p["lam"], 0)
        v = _sell(p["cry"], p["lam"] / 2.0, 0)
        s2 = (1.0 / (w[0] * w[0]) - 1.0 / (v[0] * v[0])) / (1.0 / (v[1] * v[1]) - 1.0 / (v[0] * v[0]))
        return math.asin(math.sqrt(s2)) * 180.0 / PI

    @staticmethod
    def internal(p, x):
        n = _sell(p["cry"], p["lam"], 0)[0]
        return p["thc"] + math.asin(math.sin(x * PI / 180.0) / n) * 180.0 / PI

    @classmethod
    def ext_of(cls, p, th):
        n = _sell(p["cry"], p["lam"], 0)[0]
        return math.asin(n * math.sin((th - p["thc"]) * PI / 180.0)) * 180.0 / PI

    @classmethod
    def eff(cls, p, x):
        th = cls.internal(p, x) * PI / 180.0
        w = _sell(p["cry"], p["lam"], 0)
        v = _sell(p["cry"], p["lam"] / 2.0, 0)
        ne = 1.0 / math.sqrt(math.cos(th) * math.cos(th) / (v[0] * v[0]) + math.sin(th) * math.sin(th) / (v[1] * v[1]))
        dk = 4.0 * PI / (p["lam"] * 1e-6) * (ne - w[0])
        u = dk * p["L"] * 1e-3 / 2.0
        return 1.0 if abs(u) < 1e-12 else (math.sin(u) / u) * (math.sin(u) / u)

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            v = p["eta"] * x * x * cls.eff(p, cls.ext_of(p, cls.theta_pm(p)))
        else:
            v = p["eta"] * p["Pf"] * p["Pf"] * cls.eff(p, x)
        return {"y": _q(v * 1000.0, 0.0001)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
        c = _q(cls.ext_of(p, cls.theta_pm(p)), 0.05)
        return _rng(c - p["span"], c + p["span"], p["span"] / 25.0)

    @classmethod
    def fit(cls, rows, p):
        if _qi(p) == 0:
            f = _linfit([[math.log(float(r["x"])), math.log(float(r["y"]))] for r in _stage(rows, 0)
                         if float(r["x"]) > 0 and float(r["y"]) > 0])
            return f[0] if f else 0.0
        pw = _peakwidth(_sorted(_stage(rows, 1)), 0.0)
        if not pw:
            return 0.0
        return cls.internal(p, pw[0])


# ============================================================================================ z-scan
class ZScan(_Sweep):
    """Z-scan of a thin sample (length Ls mm) through the focus of a Gaussian beam (waist w0 um, lam nm, peak on-axis
    intensity I0 W/m^2): x = z / z0 with z0 = pi w0^2 / lam. Open aperture: the two-photon absorption sum
    T = sum_m (-q0)^m / ((m + 1)^1.5 (1 + x^2)^m), q0 = beta I0 Leff. Closed aperture (small aperture, the on-axis
    Sheik-Bahae result): T = 1 + 4 dPhi x / ((x^2 + 9)(x^2 + 1)) with dPhi = k n2 I0 Leff, multiplied by the open-aperture
    trace (the usual product approximation); the two detectors read together, and dividing them removes the
    absorption. Leff = (1 - exp(-alpha L)) / alpha. Stage 0: open aperture against z (mm), stage 1: closed and open
    together. q: 0 = n2 (m^2/W), 1 = beta (m/W)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "n2": 3.0e-18, "beta": 0.0, "I0": 1.0e13, "w0": 20.0, "lam": 532.0,
              "Ls": 1.0, "alpha": 10.0}
    NST = 2

    @staticmethod
    def z0(p):
        return PI * p["w0"] * 1e-6 * p["w0"] * 1e-6 / (p["lam"] * 1e-9) * 1000.0      # mm

    @staticmethod
    def leff(p):
        L = p["Ls"] * 1e-3
        return L if p["alpha"] <= 0 else (1.0 - math.exp(-p["alpha"] * L)) / p["alpha"]

    @staticmethod
    def topen(q0, x):
        tot = 0.0
        for m in range(30):
            tot += math.pow(-q0, m) / (math.pow(m + 1.0, 1.5) * math.pow(1.0 + x * x, m))
        return tot

    @staticmethod
    def fclose(x):
        return 4.0 * x / ((x * x + 9.0) * (x * x + 1.0))

    @classmethod
    def read(cls, p, s, x, k):
        u = x / cls.z0(p)
        q0 = p["beta"] * p["I0"] * cls.leff(p)
        to = cls.topen(q0, u)
        if s == 0:
            return {"y": _q(to, 0.0001)}
        dp = 2.0 * PI / (p["lam"] * 1e-9) * p["n2"] * p["I0"] * cls.leff(p)
        return {"y": _q(to * (1.0 + dp * cls.fclose(u)), 0.0001), "y2": _q(to, 0.0001)}

    @classmethod
    def xs(cls, p, s):
        z0 = cls.z0(p)
        return [_q(z0 * u, 0.1) for u in _rng(-6.0, 6.0, 0.5)]

    @classmethod
    def fit(cls, rows, p):
        z0 = cls.z0(p)
        if _qi(p) == 1:
            st = _stage(rows, 0)
            if len(st) < 5:
                return 0.0
            def err(q0):
                e = 0.0
                for r in st:
                    d = cls.topen(q0, float(r["x"]) / z0) - float(r["y"])
                    e += d * d
                return e

            return _gmin(err, 0.0, 0.95, 95, False) / (p["I0"] * cls.leff(p))
        sfy = sff = 0.0
        for r in _stage(rows, 1):
            if float(r["y2"]) <= 0:
                continue
            fx = cls.fclose(float(r["x"]) / z0)
            sfy += fx * (float(r["y"]) / float(r["y2"]) - 1.0)
            sff += fx * fx
        if sff <= 0:
            return 0.0
        dp = sfy / sff
        return dp / (2.0 * PI / (p["lam"] * 1e-9) * p["I0"] * cls.leff(p))


# ============================================================================================ TCSPC
def _emg(t, tau, sig):
    """A unit exponential exp(-t / tau) started at t = 0 and convolved with a Gaussian IRF of rms sig."""
    if sig <= 0:
        return math.exp(-t / tau) if t >= 0 else 0.0
    a = sig / tau - t / sig
    return math.exp(sig * sig / (2.0 * tau * tau) - t / tau) * 0.5 * _erfc(a / math.sqrt(2.0))


class TCSPC(_Sweep):
    """Time-correlated single photon counting: the histogram of photon arrival times after a short excitation pulse,
    collected until the peak bin holds about Np counts. Decay = (1 - a2) exp(-t / t1) + a2 exp(-t / t2) after the pulse
    at t = tz, convolved with the instrument response (Gaussian, rms irf), plus a flat background bg per bin. Times in
    the lab's unit (ns, or ms for the multichannel-scaling mode of a slow emitter). x = start of a bin of width bw.
    Counts are Poisson draws: SIMULATED DATA. q: 0 = single lifetime (tail fit), 1 = fast component, 2 = slow
    component (two-step tail fit: the slow tail first, then the fast part after it is taken off)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "t1": 4.08, "t2": 20.0, "a2": 0.0, "tz": 3.0, "irf": 0.1, "bw": 0.5,
              "Np": 200000.0, "bg": 20.0, "span": 40.0, "seed": 7.0, "ms": 0.0}

    @staticmethod
    def shape(p, t):
        u = t - p["tz"]
        return (1.0 - p["a2"]) * _emg(u, p["t1"], p["irf"]) + p["a2"] * _emg(u, p["t2"], p["irf"])

    @classmethod
    def read(cls, p, s, x, k):
        mean = p["Np"] * cls.shape(p, x + p["bw"] / 2.0) + p["bg"]
        c = _cnt(p, k, mean)
        return {"y": c}

    @classmethod
    def xs(cls, p, s):
        return _rng(0.0, p["span"], p["span"] / 60.0)

    @staticmethod
    def tail(pts, bg):
        """Weighted log-linear fit of counts - bg against t (weights = counts): [slope, intercept]."""
        sw = sx = sy = sxx = sxy = 0.0
        for q in pts:
            v = q[1] - bg
            if v <= 0:
                continue
            w = v
            y = math.log(v)
            sw += w
            sx += w * q[0]
            sy += w * y
            sxx += w * q[0] * q[0]
            sxy += w * q[0] * y
        den = sw * sxx - sx * sx
        if sw <= 0 or abs(den) < 1e-300:
            return None
        m = (sw * sxy - sx * sy) / den
        return [m, (sy - m * sx) / sw]

    @classmethod
    def fit(cls, rows, p):
        pts = [[float(r["x"]) + p["bw"] / 2.0, float(r["y"])] for r in _stage(rows, 0)]
        pre = [q[1] for q in pts if q[0] < p["tz"] - 4.0 * p["irf"] - p["bw"]]
        bg = sum(pre) / len(pre) if pre else 0.0
        t0 = p["tz"] + 5.0 * p["irf"] + p["bw"]
        q = _qi(p)
        if q == 0:
            f = cls.tail([v for v in pts if v[0] > t0], bg)
            return -1.0 / f[0] if f and f[0] < 0 else 0.0
        f = cls.fit2([v for v in pts if v[0] > t0], bg, p["span"])
        if not f:
            return 0.0
        return f[0] if q == 1 else f[1]

    @staticmethod
    def chi(pts, bg, t1, t2):
        """Weighted (Poisson, 1/counts) least squares of counts - bg = A1 exp(-t/t1) + A2 exp(-t/t2) for fixed t1, t2."""
        s11 = s12 = s22 = b1 = b2 = 0.0
        for q in pts:
            w = 1.0 / max(q[1], 1.0)
            e1 = math.exp(-q[0] / t1)
            e2 = math.exp(-q[0] / t2)
            y = q[1] - bg
            s11 += w * e1 * e1
            s12 += w * e1 * e2
            s22 += w * e2 * e2
            b1 += w * e1 * y
            b2 += w * e2 * y
        den = s11 * s22 - s12 * s12
        if abs(den) < 1e-300:
            return 1e300
        a1 = (b1 * s22 - b2 * s12) / den
        a2 = (s11 * b2 - s12 * b1) / den
        c = 0.0
        for q in pts:
            d = q[1] - bg - a1 * math.exp(-q[0] / t1) - a2 * math.exp(-q[0] / t2)
            c += d * d / max(q[1], 1.0)
        return c

    @classmethod
    def best1(cls, pts, bg, t2, span):
        return _gmin(lambda t1: cls.chi(pts, bg, t1, t2), span / 400.0, t2 * 0.6, 50, True)

    @classmethod
    def fit2(cls, pts, bg, span):
        """The two lifetimes [fast, slow] that minimise chi-square (the fast one found for each trial slow one)."""
        if len(pts) < 6:
            return None
        t2 = _gmin(lambda u: cls.chi(pts, bg, cls.best1(pts, bg, u, span), u), span / 100.0, span, 50, True)
        return [cls.best1(pts, bg, t2, span), t2]


# ============================================================================================ pump-probe
class PumpProbe(_Sweep):
    """Degenerate pump-probe transient absorption with a delay stage: delay t = 2 (x - xz) / c (x in mm, t in ps).
    The bleach signal dT/T = A exp(-t / tc) for t > 0, convolved with the pump-probe cross-correlation (Gaussian, rms
    sig ps). Stage 0: dT/T (x 1000) against the stage position at the probe wavelength lp, stage 1: the transient
    spectrum at delay td, a Gaussian band of FWHM wb nm at the bleach peak lb. q: 0 = relaxation time tc (ps),
    1 = the bleach peak wavelength (nm)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "A": 40.0, "tc": 1.6, "sig": 0.08, "xz": 25.0, "lb": 870.0, "wb": 28.0,
              "td": 0.5}
    NST = 2

    @staticmethod
    def delay(p, x):
        return 2.0 * (x - p["xz"]) * 1e-3 / C0 * 1e12

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            v = p["A"] * _emg(cls.delay(p, x), p["tc"], p["sig"])
        else:
            u = (x - p["lb"]) / p["wb"]
            v = p["A"] * _emg(p["td"], p["tc"], p["sig"]) * math.exp(-4.0 * LN2 * u * u)
        return {"y": _q(v, 0.001)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            step = p["tc"] * C0 * 1e-12 / 2.0 * 1e3 / 4.0
            return [_q(p["xz"] - 3.0 * step + step * i, 0.0001) for i in range(26)]
        return _rng(p["lb"] - 1.5 * p["wb"], p["lb"] + 1.5 * p["wb"], p["wb"] / 10.0)

    @classmethod
    def fit(cls, rows, p):
        if _qi(p) == 1:
            pw = _peakwidth(_sorted(_stage(rows, 1)), 0.0)
            return pw[0] if pw else 0.0
        st = _stage(rows, 0)
        top = None
        for r in st:
            if top is None or float(r["y"]) > top[1]:
                top = [float(r["x"]), float(r["y"])]
        if top is None:
            return 0.0
        pts = [[2.0 * float(r["x"]) * 1e-3 / C0 * 1e12, math.log(float(r["y"]))] for r in st
               if float(r["x"]) > top[0] + 0.03 and float(r["y"]) > 0.02 * top[1]]
        f = _linfit(pts)
        return -1.0 / f[0] if f and f[0] < 0 else 0.0


# ============================================================================================ magneto-optical trap
class MOT(_Sweep):
    """A Rb-87 magneto-optical trap, a SIMULATED INSTRUMENT. Atom number from fluorescence: each atom scatters
    R = (G / 2) st / (1 + st + 4 (det / G)^2) photons per second; a lens collecting the fraction eta sends them to a
    photodiode of responsivity resp (A/W) on a transimpedance Rf (ohm). Temperature by time of flight: the cloud's
    rms size grows as sig^2 = sig0^2 + kB T t^2 / m. Loading from the background vapour (density nv, room temperature
    Tr) at the rate R = (1/2) nv A vc^4 (m / (2 kB Tr))^(3/2) (A = the capture area, about the beam diameter squared),
    N(t) = R tl (1 - exp(-t / tl)). Stage 0: fluorescence voltage (x = number of the reading), stage 1: rms size
    against the time of flight (ms), stage 2: N against the loading time (s). q: 0 = N, 1 = T (uK), 2 = vc (m/s)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "Tk": 120.0, "vc": 25.0, "tl": 1.5, "G": 6.0666, "st": 3.0,
              "det": -12.0, "eta": 0.004, "resp": 0.5, "Rf": 1.0e6, "sig0": 0.6, "nv": 1.0e14, "d": 0.02, "Tr": 296.0}
    NST = 3
    M87 = 86.909180527 * AMU

    @staticmethod
    def scat(p):
        g = 2.0 * PI * p["G"] * 1e6
        dd = p["det"] / p["G"]
        return g / 2.0 * p["st"] / (1.0 + p["st"] + 4.0 * dd * dd)

    @staticmethod
    def ephot():
        return H * C0 / 780.241e-9

    @classmethod
    def volt(cls, p, n):
        return n * cls.scat(p) * cls.ephot() * p["eta"] * p["resp"] * p["Rf"]

    @classmethod
    def rate(cls, p):
        return 0.5 * p["nv"] * p["d"] * p["d"] * math.pow(p["vc"], 4.0) * math.pow(cls.M87 / (2.0 * KB * p["Tr"]), 1.5)

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            return {"y": _q(cls.volt(p, cls.rate(p) * p["tl"]), 0.0001)}
        if s == 1:
            t = x * 1e-3
            sg = math.sqrt(p["sig0"] * p["sig0"] * 1e-6 + KB * p["Tk"] * 1e-6 * t * t / cls.M87)
            return {"y": _q(sg * 1000.0, 0.001)}
        n = cls.rate(p) * p["tl"] * (1.0 - math.exp(-x / p["tl"]))
        return {"y": _q(cls.volt(p, n), 0.0001)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return [1.0, 2.0, 3.0]
        if s == 1:
            return [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
        return [0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0, 15.0]

    @classmethod
    def fit(cls, rows, p):
        q = _qi(p)
        per = cls.volt(p, 1.0)
        if q == 0:
            st = _stage(rows, 0)
            return sum(float(r["y"]) for r in st) / len(st) / per if st else 0.0
        if q == 1:
            f = _linfit([[(float(r["x"]) * 1e-3) * (float(r["x"]) * 1e-3), (float(r["y"]) * 1e-3) * (float(r["y"]) * 1e-3)]
                         for r in _stage(rows, 1)])
            return f[0] * cls.M87 / KB * 1e6 if f else 0.0
        st = _stage(rows, 2)
        if len(st) < 4:
            return 0.0
        end = None
        for r in st:
            if end is None or float(r["x"]) > end[0]:
                end = [float(r["x"]), float(r["y"])]
        pts = [[float(r["x"]), math.log(1.0 - float(r["y"]) / end[1])] for r in st
               if float(r["x"]) < end[0] and float(r["y"]) < 0.97 * end[1]]
        f = _linfit(pts)
        if not f or f[0] >= 0:
            return 0.0
        tl = -1.0 / f[0]
        R = end[1] / per / tl
        return math.pow(R / (0.5 * p["nv"] * p["d"] * p["d"] * math.pow(cls.M87 / (2.0 * KB * p["Tr"]), 1.5)), 0.25)


# ============================================================================================ BEC
class BEC(_Sweep):
    """Bose-Einstein condensation of Rb-87 in a harmonic magnetic trap (frequencies fx, fy, fz Hz), a SIMULATED
    INSTRUMENT. Forced RF evaporation to a final frequency x (kHz above the trap bottom) leaves a cloud at
    T = h x / (eta kB) with N = Ni (T / Ti)^ga atoms (an illustrative evaporation trajectory). The ideal Bose gas in the
    trap condenses below Tc = 0.9405 hbar wbar N^(1/3) / kB (0.9405 = zeta(3)^(-1/3)); below Tc the condensed fraction
    is 1 - (T / Tc)^3. A time-of-flight absorption image is fitted with a Thomas-Fermi parabola on a thermal Gaussian
    (the bimodal profile): the wings give T, the areas give N and N0/N. Readings: T (nK, from the wings), N, and the
    condensate fraction. Result: Tc (nK) of a cloud of Nref atoms, from the shots that show a condensate."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "fx": 30.0, "fy": 30.0, "fz": 120.0, "eta": 10.0, "Ni": 3.0e6,
              "Ti": 1200.0, "ga": 0.6, "Nref": 1.0e6}

    @staticmethod
    def wbar(p):
        return 2.0 * PI * math.pow(p["fx"] * p["fy"] * p["fz"], 1.0 / 3.0)

    @classmethod
    def tc(cls, p, n):
        return math.pow(ZETA3, -1.0 / 3.0) * HBAR * cls.wbar(p) * math.pow(n, 1.0 / 3.0) / KB * 1e9

    @classmethod
    def shot(cls, p, x):
        T = H * x * 1000.0 / (p["eta"] * KB) * 1e9
        n = p["Ni"] * math.pow(T / p["Ti"], p["ga"])
        tc = cls.tc(p, n)
        f = 1.0 - math.pow(T / tc, 3.0) if T < tc else 0.0
        return [T, n, f]

    @classmethod
    def read(cls, p, s, x, k):
        r = cls.shot(p, x)
        return {"y": _q(r[0], 0.1), "N": _q(r[1], 100.0), "f": _q(r[2], 0.001)}

    @classmethod
    def xs(cls, p, s):
        return [60.0, 52.0, 46.0, 42.0, 38.0, 34.0, 30.0, 26.0, 22.0, 18.0]

    @classmethod
    def fit(cls, rows, p):
        tot, k = 0.0, 0
        for r in _stage(rows, 0):
            f = float(r["f"])
            if 0.05 < f < 0.95:
                tc = float(r["y"]) / math.pow(1.0 - f, 1.0 / 3.0)
                tot += tc * math.pow(p["Nref"] / float(r["N"]), 1.0 / 3.0)
                k += 1
        return tot / k if k else 0.0


# ============================================================================================ Michelson metrology
class MichMetro(_Sweep):
    """Michelson interferometer metrology. Stage 0 (He-Ne, 632.8 nm in air): the moving mirror is driven by a
    micrometer of nominal travel x (um) whose real travel is cal x; a photodiode counter counts the whole fringes
    N = floor(2 cal x / lam). Stage 1 (LED, Gaussian spectrum, centre ll, FWHM dl nm): fringe visibility against the
    path difference x (um), V = exp(-(pi dnu x / c)^2 / (4 ln 2)), whose FWHM is the coherence length
    lc = 4 ln2 ll^2 / (pi dl). Stage 2 (sodium lamp): the D1-D2 doublet beats, V = |cos(pi x dsig)| times the envelope
    of lines of FWHM dn (GHz, Gaussian); read at the beat maxima. q: 0 = displacement for 100 um set, 1 = LED coherence
    length (um), 2 = Na line width (GHz), 3 = LED line width (nm)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "cal": 1.0237, "lh": 632.816, "ll": 625.0, "dl": 17.0, "l1": 588.995,
              "l2": 589.592, "dn": 1.7}
    NST = 3

    @staticmethod
    def vled(p, x):
        dnu = C0 * p["dl"] * 1e-9 / (p["ll"] * 1e-9 * p["ll"] * 1e-9)
        a = PI * dnu * x * 1e-6 / C0
        return math.exp(-a * a / (4.0 * LN2))

    @staticmethod
    def vna(p, x):
        ds = 1.0 / (p["l1"] * 1e-9) - 1.0 / (p["l2"] * 1e-9)
        a = PI * p["dn"] * 1e9 * x * 1e-6 / C0
        return abs(math.cos(PI * x * 1e-6 * ds)) * math.exp(-a * a / (4.0 * LN2))

    @staticmethod
    def beat(p):
        return 1.0 / (1.0 / (p["l1"] * 1e-9) - 1.0 / (p["l2"] * 1e-9)) * 1e6        # um

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            return {"y": float(math.floor(2.0 * p["cal"] * x * 1000.0 / p["lh"]))}
        if s == 1:
            return {"y": _q(cls.vled(p, x), 0.001)}
        return {"y": _q(cls.vna(p, x), 0.001)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return [20.0, 40.0, 60.0, 80.0, 100.0]
        if s == 1:
            lc = 4.0 * LN2 * p["ll"] * p["ll"] / (PI * p["dl"]) / 1000.0
            return [_q(lc * u, 0.01) for u in _rng(0.0, 1.2, 0.05)]
        b = cls.beat(p)
        return [_q(b * 50.0 * i, 0.1) for i in range(0, 7)]

    @classmethod
    def fit(cls, rows, p):
        q = _qi(p)
        if q == 0:
            for r in _stage(rows, 0):
                if abs(float(r["x"]) - 100.0) < 1e-6:
                    return float(r["y"]) * p["lh"] / 2.0 / 1000.0
            return 0.0
        if q in (1, 3):
            pts = [[-float(r["x"]), float(r["y"])] for r in _stage(rows, 1)] + \
                  [[float(r["x"]), float(r["y"])] for r in _stage(rows, 1) if float(r["x"]) > 0]
            pts.sort(key=lambda v: v[0])
            pw = _peakwidth(pts, 0.0)
            if not pw:
                return 0.0
            return pw[1] if q == 1 else 4.0 * LN2 * p["ll"] * p["ll"] / (PI * pw[1] * 1000.0)
        pts = [[float(r["x"]) * 1e-6 * (float(r["x"]) * 1e-6), math.log(float(r["y"]))] for r in _stage(rows, 2)
               if float(r["y"]) > 0]
        f = _linfit(pts)
        if not f or f[0] >= 0:
            return 0.0
        return math.sqrt(-f[0] * 4.0 * LN2) * C0 / PI / 1e9


# ============================================================================================ Hong-Ou-Mandel
class HOM(_Sweep):
    """Hong-Ou-Mandel dip: degenerate SPDC photon pairs (lam nm) through interference filters of FWHM dl nm meet on a
    50:50 beam splitter; one input arm's path is changed by x (um). Coincidences in a time t: C0 t (1 - V exp(-(x/w)^2
    4 ln2)) + accidentals, with the dip FWHM w = 4 ln2 lam^2 / (pi dl) (the photons' coherence length, Gaussian
    spectra) and the visibility V = V0 cos^2(th) (th = polarisation mismatch set by a half-wave plate). Counts are
    Poisson draws: SIMULATED DATA. q: 0 = visibility, 1 = coherence length (um)."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "lam": 810.0, "dl": 5.0, "V0": 0.96, "th": 0.0, "C0": 1200.0, "t": 60.0,
              "acc": 2.0, "seed": 31.0}

    @staticmethod
    def w(p):
        return 4.0 * LN2 * p["lam"] * p["lam"] / (PI * p["dl"]) / 1000.0

    @classmethod
    def vis(cls, p):
        c = math.cos(p["th"] * PI / 180.0)
        return p["V0"] * c * c

    @classmethod
    def read(cls, p, s, x, k):
        u = x / cls.w(p)
        mean = (p["C0"] * (1.0 - cls.vis(p) * math.exp(-4.0 * LN2 * u * u)) + p["acc"]) * p["t"]
        c = _cnt(p, k, mean)
        return {"y": c, "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        w = cls.w(p)
        return [_q(w * u, 0.5) for u in _rng(-3.0, 3.0, 0.25)]

    @classmethod
    def fit(cls, rows, p):
        st = _stage(rows, 0)
        w = 0.0
        for r in st:
            w = max(w, abs(float(r["x"])))
        far = [float(r["y"]) / float(r["T"]) - p["acc"] for r in st if abs(float(r["x"])) > 0.66 * w]
        if not far:
            return 0.0
        c0 = sum(far) / len(far)
        pts = []
        for r in st:
            d = 1.0 - (float(r["y"]) / float(r["T"]) - p["acc"]) / c0
            if d > 0.2:
                pts.append([float(r["x"]) * float(r["x"]), math.log(d)])
        f = _linfit(pts)
        if not f or f[0] >= 0:
            return 0.0
        if _qi(p) == 0:
            return math.exp(f[1])
        return 2.0 * math.sqrt(LN2 / -f[0])


# ============================================================================================ CHSH
class CHSH(_Sweep):
    """Polarisation-entangled photon pairs from a two-crystal type-I SPDC source, state (|HH> + |VV>)/sqrt2 mixed down
    to a visibility V. Coincidence rate for analysers at a, b: R0/4 (1 + V cos 2(a - b)) + accidentals acc (known
    from the singles and the coincidence window, and taken off). E(a, b) from the four orthogonal combinations;
    S = E(a,b) - E(a,b') + E(a',b) + E(a',b') at a = 0, a' = 45, b = 22.5, b' = 67.5 degrees. Stage 0: correlation
    curve, a = 0 (x = 0..8 -> b = 0..180 step 22.5) and a = 45 (x = 9..17); stage 1: the 16 CHSH settings
    (x = 4 i + j, a = 0, 45, 90, 135 and b = 22.5, 67.5, 112.5, 157.5). Counts are Poisson draws: SIMULATED DATA.
    q: 0 = S, 1 = the polarisation correlation visibility."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "V": 0.93, "R0": 4000.0, "acc": 3.0, "t": 30.0, "seed": 41.0}
    NST = 2
    A = [0.0, 45.0, 90.0, 135.0]
    B = [22.5, 67.5, 112.5, 157.5]

    @classmethod
    def ab(cls, s, x):
        i = int(x + 0.5)
        if s == 0:
            return [0.0 if i < 9 else 45.0, 22.5 * (i % 9)]
        return [cls.A[i // 4], cls.B[i % 4]]

    @classmethod
    def read(cls, p, s, x, k):
        a, b = cls.ab(s, x)
        mean = (p["R0"] / 4.0 * (1.0 + p["V"] * math.cos(2.0 * (a - b) * PI / 180.0)) + p["acc"]) * p["t"]
        return {"y": _cnt(p, k, mean), "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        return [float(i) for i in range(18)] if s == 0 else [float(i) for i in range(16)]

    @classmethod
    def fit(cls, rows, p):
        def n(r):
            return float(r["y"]) / float(r["T"]) - p["acc"]

        if _qi(p) == 1:
            vs = []
            for half in (0, 1):
                st = [r for r in _stage(rows, 0) if (int(float(r["x"]) + 0.5) >= 9) == (half == 1)]
                if not st:
                    continue
                hi = max(n(r) for r in st)
                lo = min(n(r) for r in st)
                vs.append((hi - lo) / (hi + lo))
            return sum(vs) / len(vs) if vs else 0.0
        N = {}
        for r in _stage(rows, 1):
            N[int(float(r["x"]) + 0.5)] = n(r)
        if len(N) < 16:
            return 0.0

        def E(i, j):
            pp, mm = N[4 * i + j], N[4 * (i + 2) + j + 2]
            pm, mp = N[4 * i + j + 2], N[4 * (i + 2) + j]
            return (pp + mm - pm - mp) / (pp + mm + pm + mp)

        return E(0, 0) - E(0, 1) + E(1, 0) + E(1, 1)


# ============================================================================================ quantum eraser
class Eraser(_Sweep):
    """Single-photon Mach-Zehnder interference and the quantum eraser. A piezo moves one mirror: phase
    ph = 2 pi x / Vf (x in volts, Vf volts per fringe). Counts in a time t: Rc t (1 + Vis cos ph) / 2. Stage 0: plain
    interferometer, Vis = V0. Stage 1: a half-wave plate marks the path by turning one arm's polarisation through psi,
    Vis = V0 |cos psi| (which-path information). Stage 2: a polariser at psi/2 after the beam splitter erases the mark,
    Vis = V0 again (half the light). The source is an attenuated laser (mean photon number per gate well below one) or
    heralded single photons (counts = coincidences with the herald). Counts are Poisson draws: SIMULATED DATA.
    Visibility from a least-squares fit of a + b cos ph + c sin ph. q: 0 = visibility with the eraser, 1 = with
    which-path information."""

    PARAMS = {"x": 0.0, "s": 0.0, "q": 0.0, "V0": 0.94, "psi": 90.0, "Rc": 20000.0, "t": 10.0, "Vf": 4.0, "seed": 53.0}
    NST = 3

    @classmethod
    def vis(cls, p, s):
        if s == 1:
            return p["V0"] * abs(math.cos(p["psi"] * PI / 180.0))
        return p["V0"]

    @classmethod
    def read(cls, p, s, x, k):
        ph = 2.0 * PI * x / p["Vf"]
        c = math.cos(p["psi"] * PI / 360.0)
        r = p["Rc"] * (c * c if s == 2 else 1.0)
        mean = r * p["t"] * (1.0 + cls.vis(p, s) * math.cos(ph)) / 2.0
        return {"y": _cnt(p, k, mean), "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        return _rng(0.0, 2.0 * p["Vf"], p["Vf"] / 8.0)

    @classmethod
    def fit(cls, rows, p):
        s = 2 if _qi(p) == 0 else 1
        pts = [[2.0 * PI * float(r["x"]) / p["Vf"], float(r["y"])] for r in _stage(rows, s)]
        if len(pts) < 4:
            return 0.0
        c = _fit3(pts)
        if not c or c[0] <= 0:
            return 0.0
        return math.sqrt(c[1] * c[1] + c[2] * c[2]) / c[0]


# ============================================================================================ tables
KERNELS: dict[str, Any] = {
    "pl10_satabs": SatAbs, "pl10_oppump": OptPump, "pl10_hdshift": HDShift, "pl10_diodelaser": DiodeLaser,
    "pl10_freqlock": FreqLock, "pl10_shg": SHG, "pl10_zscan": ZScan, "pl10_tcspc": TCSPC, "pl10_pumpprobe": PumpProbe,
    "pl10_mot": MOT, "pl10_bec": BEC, "pl10_michmetro": MichMetro, "pl10_hom": HOM, "pl10_chsh": CHSH,
    "pl10_eraser": Eraser,
}
FAMILY = {k: "optics" for k in KERNELS}


def _tb_oppump(p):
    q = _qi(p)
    if q == 0:
        return p["gJ"] / (2.0 * p["I87"] + 1.0)
    if q == 1:
        return p["I85"]
    if q == 2:
        return p["Be"] * 1e6
    return p["tau"]


def _tb_lock(p):
    if _qi(p) == 0:
        return FreqLock.fu(p)
    return FreqLock.sigma(p, 100000.0) / 1000.0


TEXTBOOK = {
    # the hyperfine splittings of the 5P3/2 level and the natural width of the D2 line (Steck)
    "pl10_sat": lambda p: [p["d87a"], p["d85a"], p["G"]][_qi(p)],
    # gF = gJ / (2 I + 1) for F = I + 1/2; the nuclear spin; the horizontal Earth's field; the pumping time
    "pl10_pump": _tb_oppump,
    # R_H = R_inf / (1 + me / mp); the deuteron / proton mass ratio (CODATA)
    "pl10_ryd": lambda p: RINF / (1.0 + ME_MP) if _qi(p) == 0 else p["rd"],
    "pl10_diode": lambda p: [p["Ith"], p["eta"], p["dlI"], p["dlT"]][_qi(p)],
    "pl10_lock": _tb_lock,
    # P2 ~ P^2; the type-I phase-matching angle from the Sellmeier indices
    "pl10_shgpm": lambda p: 2.0 if _qi(p) == 0 else SHG.theta_pm(p),
    "pl10_nl": lambda p: p["n2"] if _qi(p) == 0 else p["beta"],
    "pl10_life": lambda p: p["t1"] if _qi(p) < 2 else p["t2"],
    "pl10_relax": lambda p: p["tc"] if _qi(p) == 0 else p["lb"],
    "pl10_motq": lambda p: [MOT.rate(p) * p["tl"], p["Tk"], p["vc"]][_qi(p)],
    # ideal Bose gas in a harmonic trap: kB Tc = zeta(3)^(-1/3) hbar wbar N^(1/3)
    "pl10_tc": lambda p: BEC.tc(p, p["Nref"]),
    "pl10_mich": lambda p: [p["cal"] * 100.0, 4.0 * LN2 * p["ll"] * p["ll"] / (PI * p["dl"]) / 1000.0, p["dn"],
                            p["dl"]][_qi(p)],
    "pl10_homv": lambda p: HOM.vis(p) if _qi(p) == 0 else HOM.w(p),
    # S = 2 sqrt2 V (Tsirelson's bound 2 sqrt2 for V = 1; local realism needs S <= 2)
    "pl10_bell": lambda p: 2.0 * math.sqrt(2.0) * p["V"] if _qi(p) == 0 else p["V"],
    "pl10_erase": lambda p: p["V0"] if _qi(p) == 0 else p["V0"] * abs(math.cos(p["psi"] * PI / 180.0)),
}
