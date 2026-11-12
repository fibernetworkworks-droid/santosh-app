"""Kernel pack `phd_cond_w10`: Ph.D. research techniques of condensed matter, wave 10 (kernels `pk10_*`).

Low temperature and superconductivity, quantum transport, semiconductor characterisation, magnetic resonance and
hyperfine methods, magnetism and magneto-optics. New physics never goes into `kernels.py`; it lives here and in the
EXACT JavaScript twin `app/static/prayog/packs/phd_cond_w10.js` (same formulas, same order of operations).

Every kernel is a SWEEP like the wave-9 packs: the student sets one control `x` (a temperature, a field, a current,
a velocity, a delay...) in one of the kernel's stages `s` and reads the instrument. `read(p, s, x, k)` gives the
reading, `plan(p)` lists the settings a careful student takes (after a first survey, so the fine steps sit where the
signal is), `fit(rows, p)` works the result out of the recorded rows exactly as the rig does - it never reads the
hidden unknown - and `measure(p)` runs the plan and the fit. The lab's check compares `measure()["res"]` with the
relation in TEXTBOOK.

These are research instruments (cryostats, magnets, spectrometers, a dilution refrigerator). The data is SIMULATED
DATA from the published model named in each kernel, noiseless and rounded to the instrument's least count. No
randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
H = 6.62607015e-34            # Planck constant, J s (exact, SI 2019)
QE = 1.602176634e-19          # elementary charge, C (exact, SI 2019)
KB = 1.380649e-23             # Boltzmann constant, J/K (exact, SI 2019)
NA = 6.02214076e23            # Avogadro constant (exact, SI 2019)
HBAR = H / (2.0 * PI)
MUB = 9.2740100783e-24        # Bohr magneton, J/T (CODATA 2018)
MUN = 5.0507837461e-27        # nuclear magneton, J/T (CODATA 2018)
ME = 9.1093837015e-31         # electron mass, kg (CODATA 2018)
MU0 = 1.25663706212e-6        # vacuum permeability, N/A^2 (CODATA 2018)
EPS0 = 8.8541878128e-12       # vacuum permittivity, F/m (CODATA 2018)
C0 = 299792458.0              # speed of light, m/s (exact)
RGAS = NA * KB                # molar gas constant
RK = H / (QE * QE)            # von Klitzing constant h/e^2 (exact in SI 2019)
L0 = 2.44e-8                  # Sommerfeld value of the Lorenz number, W ohm / K^2 (pi^2/3 (k/e)^2 = 2.443e-8)
# Fe-57 Moessbauer constants (from memory - verify): ground state I = 1/2, mu_g = +0.09044 muN; 14.4 keV state
# I = 3/2, mu_e = -0.1549 muN; gamma energy 14.4125 keV
MU_G = 0.09044
MU_E = -0.1549
EGAM = 14412.5 * QE


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


def _logi(u: float) -> float:
    """The logistic step 1 / (1 + e^-u), safe for large |u|."""
    if u >= 0:
        return 1.0 / (1.0 + math.exp(-u))
    e = math.exp(u)
    return e / (1.0 + e)


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


def _pts(rows: list, key: str = "y") -> list:
    pts = [[float(r["x"]), float(r[key])] for r in rows]
    pts.sort(key=lambda q: q[0])
    return pts


def _rng(a: float, b: float, d: float) -> list:
    n = int(math.floor((b - a) / d + 0.5))
    return [a + d * i for i in range(n + 1)]


def _grid(a: float, b: float, d: float) -> list:
    """Points of the fixed grid of step d (multiples of d) between a and b."""
    i0 = int(math.ceil(a / d - 1e-9))
    i1 = int(math.floor(b / d + 1e-9))
    return [d * i for i in range(i0, i1 + 1)]


def _merge(a: list, b: list) -> list:
    """Sorted union of two lists of settings (duplicates within 1e-9 dropped)."""
    out = []
    for v in sorted(a + b):
        if not out or abs(v - out[-1]) > 1e-9 * max(1.0, abs(v)):
            out.append(v)
    return out


def _vertex(x0: float, y0: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """x of the vertex of the parabola through three points (x1 the middle one)."""
    d = (x0 - x1) * (x0 - x2) * (x1 - x2)
    if d == 0:
        return x1
    a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / d
    b = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / d
    if a == 0:
        return x1
    return -b / (2.0 * a)


def _peakx(pts: list, sign: float = 1.0) -> float | None:
    """x of the largest (sign 1) or smallest (sign -1) point, refined by a parabola through it and its neighbours."""
    if len(pts) < 3:
        return None
    ib, best = -1, -1e300
    for i in range(len(pts)):
        v = sign * pts[i][1]
        if v > best:
            best, ib = v, i
    if ib <= 0 or ib >= len(pts) - 1:
        return pts[ib][0]
    a, b, c = pts[ib - 1], pts[ib], pts[ib + 1]
    return _vertex(a[0], a[1], b[0], b[1], c[0], c[1])


def _zeros_down(pts: list, frac: float, gap: float) -> list:
    """Crossings from + to - of a derivative trace (each line centre), between neighbours closer than `gap`, both
    neighbours above `frac` of the largest |y| of a window of 3 points either side."""
    big = 0.0
    for q in pts:
        if abs(q[1]) > big:
            big = abs(q[1])
    out = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if a[1] > 0 >= b[1] and b[0] - a[0] <= gap:
            lo = max(0, i - 3)
            hi = min(len(pts) - 1, i + 4)
            mx = mn = 0.0
            for j in range(lo, hi + 1):
                if pts[j][1] > mx:
                    mx = pts[j][1]
                if pts[j][1] < mn:
                    mn = pts[j][1]
            if mx > frac * big and -mn > frac * big:
                out.append(a[0] + (0.0 - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
    return out


def _bisect(f, lo: float, hi: float, n: int = 100) -> float:
    """Root of f between lo and hi (f(lo) and f(hi) of opposite signs)."""
    flo = f(lo)
    for _ in range(n):
        mid = (lo + hi) / 2.0
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2.0


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
    def stages(cls, p):
        return list(range(cls.NST))

    @classmethod
    def plan(cls, p):
        out = []
        for s in cls.stages(p):
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


def _typ(p) -> int:
    return int(p["typ"] + 0.5)


# ============================================================================================ superconductor R(T)
class SCRT(_Sweep):
    """Four-probe resistance of a superconductor against temperature. The normal state is a straight line
    Rn = Rres + a T just above the transition; the fall is the logistic step R = Rn / (1 + exp(-(T - Tc)/w)), so R is
    half of Rn exactly at Tc. A field B lowers Tc along the empirical parabola Bc(T) = Bc0 (1 - (T/Tc0)^2), i.e.
    Tc(B) = Tc0 sqrt(1 - B/Bc0). Stage 0: zero field; stage 1: the field B1; stage 2: one reading at room temperature
    (R300) for the residual resistance ratio. Readings in milliohm at 1e-4 mohm."""

    PARAMS = {"x": 100.0, "s": 0.0, "Tc0": 92.0, "Bc0": 120.0, "w": 0.4, "Rres": 0.005, "a": 5.0e-5, "B1": 7.0,
              "R300": 0.02, "lo": 15.0, "hi": 25.0, "dT": 1.0}
    NST = 3

    @staticmethod
    def tcb(p, B):
        r = 1.0 - B / p["Bc0"]
        return p["Tc0"] * math.sqrt(r) if r > 0 else 0.0

    @classmethod
    def read(cls, p, s, x, k):
        if s == 2:
            return {"y": _q(1000.0 * p["R300"], 1e-4)}
        B = p["B1"] if s == 1 else 0.0
        R = (p["Rres"] + p["a"] * x) * _logi((x - cls.tcb(p, B)) / p["w"])
        return {"y": _q(1000.0 * R, 1e-4)}

    @classmethod
    def xs(cls, p, s):
        if s == 2:
            return [300.0]
        tc = cls.tcb(p, p["B1"] if s == 1 else 0.0)
        a = _grid(tc - p["lo"], tc + p["hi"], p["dT"])
        b = _grid(tc - 5.0 * p["w"], tc + 5.0 * p["w"], p["w"] / 4.0)
        return [v for v in _merge(a, b) if v > 0.3]

    @staticmethod
    def tc_of(st):
        """Tc of one sweep: the straight line through the top five temperatures, then where R/Rn = 1/2."""
        pts = _pts(st)
        if len(pts) < 8:
            return 0.0
        f = _linfit(pts[-5:])
        if not f:
            return 0.0
        rr = [[q[0], q[1] / (f[0] * q[0] + f[1])] for q in pts]
        for i in range(len(rr) - 1, 0, -1):
            a, b = rr[i - 1], rr[i]
            if a[1] <= 0.5 < b[1]:
                return a[0] + (0.5 - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        return 0.0

    @classmethod
    def fit(cls, rows, p):
        return cls.tc_of(_stage(rows, 0))


# ============================================================================================ critical current
class SCJc(_Sweep):
    """Transport I-V of a superconducting bridge or wire: V = Ec L (I/Ic)^n (the power-law E-J relation) with the
    criterion Ec = 1 uV/cm = 1e-4 V/m. Ic(T, B) = Ic0 (1 - (T/Tc)^2)^1.5 / (1 + B/B0) (illustrative temperature law,
    Kim-type field law). Stage 0: T1, zero field; stage 1: T2, zero field; stage 2: T1 in the field B1. x = current
    (A); the voltage is read in microvolt at 1e-4 uV."""

    PARAMS = {"x": 0.0, "s": 0.0, "Ic0": 2.0, "Tc": 92.0, "B0": 1.0, "n": 15.0, "L": 0.002, "Ec": 1.0e-4,
              "area": 2.0e-12, "T1": 77.0, "T2": 60.0, "B1": 0.5}
    NST = 3

    @staticmethod
    def ic(p, T, B):
        t = T / p["Tc"]
        if t >= 1:
            return 0.0
        return p["Ic0"] * math.pow(1.0 - t * t, 1.5) / (1.0 + B / p["B0"])

    @classmethod
    def cond(cls, p, s):
        if s == 1:
            return [p["T2"], 0.0]
        if s == 2:
            return [p["T1"], p["B1"]]
        return [p["T1"], 0.0]

    @classmethod
    def read(cls, p, s, x, k):
        c = cls.cond(p, s)
        ic = cls.ic(p, c[0], c[1])
        v = 0.0 if x <= 0 or ic <= 0 else p["Ec"] * p["L"] * math.pow(x / ic, p["n"])
        return {"y": _q(1.0e6 * v, 1e-4)}

    @classmethod
    def xs(cls, p, s):
        c = cls.cond(p, s)
        ic = cls.ic(p, c[0], c[1])
        return [ic * (0.6 + 0.05 * i) for i in range(13)]

    @staticmethod
    def ic_of(st, vc):
        """Ic of one sweep: where V crosses the criterion voltage, interpolated on log V against log I."""
        pts = _pts(st)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a[1] > 0 and b[1] > 0 and a[1] <= vc < b[1]:
                la, lb = math.log(a[1]), math.log(b[1])
                return math.exp(math.log(a[0]) + (math.log(vc) - la) * (math.log(b[0]) - math.log(a[0])) / (lb - la))
        return 0.0

    @classmethod
    def fit(cls, rows, p):
        ic = cls.ic_of(_stage(rows, 0), 1.0e6 * p["Ec"] * p["L"])
        return ic / p["area"]


# ============================================================================================ magnetometry (SQUID / VSM)
class Magnet(_Sweep):
    """Sample magnetometer (SQUID or vibrating sample). The moment m is read in emu (1 emu = 1e-3 A m^2).
    Stage 0: M-H descending from +Bm, stage 1: ascending, stage 2: zero-field-cooled M-T, stage 3: field-cooled M-T.
    typ 0 paramagnetic salt: Brillouin function of n mol of ions (g, J) - Curie law at low field.
    typ 1 ferromagnetic nanoparticles: N single-domain particles of moment mu = Ms V, Neel-Arrhenius blocking with the
          measuring time tm: TB = K V / (kB ln(tm/tau0)) (Bean and Livingston 1959). Above TB the Langevin function;
          ZFC below TB the blocked susceptibility N Ms^2 V / (3K); FC below TB frozen at its value at TB.
    typ 2 superconductor: a sphere of volume Vs shields -3/2 Vs B/mu0 times f = 1 - (T/Tc)^4 (ZFC) and expels a
          fraction fFC of that on field cooling.
    typ 3 ferrite nanoparticle powder / typ 4 magnetic thin film: a soft ferromagnet, branches ms tanh((B -+ Bc)/Bw)
          plus a linear background chi B from the holder; ms(T) = ms0 sqrt(1 - T/Tc) (mean-field form near Tc)."""

    PARAMS = {"x": 0.0, "s": 0.0, "typ": 0.0, "T0": 2.0, "Bm": 5.0, "Bf": 0.01, "Tlo": 2.0, "Thi": 300.0,
              "nmol": 1.0e-5, "g": 2.0, "J": 3.5,
              "N": 1.0e17, "Ms": 4.8e5, "V": 5.236e-25, "K": 1.6e4, "tm": 100.0, "tau0": 1.0e-9, "Bc": 0.02, "Bw": 0.05,
              "Vs": 1.0e-9, "Tc": 9.25, "fFC": 0.3, "Bp": 0.1,
              "ms0": 0.08, "chi": 1.0e-5, "mass": 1.0e-6, "lcm": 1.0e-8}
    NST = 4

    @staticmethod
    def brill(J, x):
        a = (2.0 * J + 1.0) / (2.0 * J)
        b = 1.0 / (2.0 * J)
        if abs(a * x) < 0.05:
            a2, b2 = a * a, b * b
            return (a2 - b2) * x / 3.0 - (a2 * a2 - b2 * b2) * x * x * x / 45.0 + 2.0 * (a2 * a2 * a2 - b2 * b2 * b2) * math.pow(x, 5) / 945.0

        def coth(u):
            e = math.exp(-2.0 * abs(u))
            c = (1.0 + e) / (1.0 - e)
            return c if u > 0 else -c
        return a * coth(a * x) - b * coth(b * x)

    @staticmethod
    def lang(x):
        if abs(x) < 0.05:
            return x / 3.0 - x * x * x / 45.0 + 2.0 * math.pow(x, 5) / 945.0
        e = math.exp(-2.0 * abs(x))
        c = (1.0 + e) / (1.0 - e)
        return (c if x > 0 else -c) - 1.0 / x

    @classmethod
    def tb(cls, p):
        return p["K"] * p["V"] / (KB * math.log(p["tm"] / p["tau0"]))

    @classmethod
    def m_si(cls, p, s, x):
        t = _typ(p)
        if s <= 1:
            B, T = x, p["T0"]
        else:
            B, T = p["Bf"], x
        if t == 0:
            mu = p["g"] * MUB * p["J"]
            return p["nmol"] * NA * mu * cls.brill(p["J"], mu * B / (KB * T))
        if t == 1:
            mu = p["Ms"] * p["V"]
            tb = cls.tb(p)
            if s <= 1:
                if T >= tb:
                    return p["N"] * mu * cls.lang(mu * B / (KB * T))
                ms = p["N"] * mu
                sh = p["Bc"] if s == 0 else -p["Bc"]
                return ms * math.tanh((B + sh) / p["Bw"])
            if T >= tb:
                return p["N"] * mu * cls.lang(mu * B / (KB * T))
            if s == 2:
                return p["N"] * p["Ms"] * p["Ms"] * p["V"] / (3.0 * p["K"]) * B
            return p["N"] * mu * cls.lang(mu * B / (KB * tb))
        if t == 2:
            tt = T / p["Tc"]
            f = 1.0 - tt * tt * tt * tt if tt < 1 else 0.0
            full = -1.5 * p["Vs"] * B / MU0 * f
            if s <= 1:
                bp = p["Bp"] * f
                if abs(B) <= bp:
                    return full
                if bp <= 0:
                    return 0.0
                sg = 1.0 if B > 0 else -1.0
                decay = math.exp(-(abs(B) - bp) / bp)
                return -1.5 * p["Vs"] * sg * bp / MU0 * f * decay
            return full if s == 2 else p["fFC"] * full
        # typ 3 / 4: soft ferromagnet with a holder background
        r = 1.0 - T / p["Tc"]
        ms = p["ms0"] * math.sqrt(r) if r > 0 else 0.0
        if s == 0:
            return ms * math.tanh((B + p["Bc"]) / p["Bw"]) + p["chi"] * B
        if s == 1:
            return ms * math.tanh((B - p["Bc"]) / p["Bw"]) + p["chi"] * B
        return ms * math.tanh(B / p["Bw"]) + p["chi"] * B

    @classmethod
    def read(cls, p, s, x, k):
        return {"y": _q(1000.0 * cls.m_si(p, s, x), p["lcm"])}

    @classmethod
    def stages(cls, p):
        t = _typ(p)
        if t in (3, 4):
            return [0, 1, 3]
        return [0, 1, 2, 3]

    @classmethod
    def xs(cls, p, s):
        t = _typ(p)
        if s <= 1:
            bm = p["Bm"]
            pts = [bm * (1.0 - 0.1 * i) for i in range(21)]
            if t in (1, 3, 4):
                pts = _merge(pts, [p["Bc"] * c for c in (-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0)])
            pts = sorted(pts, reverse=True)
            return pts if s == 0 else sorted(pts)
        if t == 0:
            return _merge(_rng(2.0, 20.0, 2.0), _rng(30.0, 300.0, 30.0))
        if t == 1:
            tb = cls.tb(p)
            return _merge(_rng(p["Tlo"], p["Thi"], 10.0), _grid(0.8 * tb, 1.3 * tb, 1.0))
        if t == 2:
            return _rng(p["Tlo"], 1.5 * p["Tc"], 0.5 if p["Tc"] < 20 else 4.0)
        d = _q(p["Tc"] / 80.0, 0.5)
        return _merge(_rng(300.0, 0.7 * p["Tc"], 50.0), _grid(0.75 * p["Tc"], 1.05 * p["Tc"], d))

    @classmethod
    def fit(cls, rows, p):
        t = _typ(p)
        if t == 0:
            pts = []
            for r in _stage(rows, 3):
                x, y = float(r["x"]), float(r["y"])
                if x >= 20.0 and y > 0:
                    pts.append([x, 1.0 / y])
            f = _linfit(pts)
            if not f or f[0] <= 0:
                return 0.0
            c = 1.0e-3 / (f[0] * p["Bf"])                        # Curie constant of the sample, A m^2 K / T
            return math.sqrt(3.0 * KB * c / (p["nmol"] * NA)) / MUB
        if t == 1:
            fc = _pts(_stage(rows, 3))
            if len(fc) < 4:
                return 0.0
            return fc[-1][1] * fc[-1][0] / fc[0][1]
        if t == 2:
            pts = []
            for r in _stage(rows, 2):
                x, y = float(r["x"]), float(r["y"])
                if y < -20.0 * p["lcm"]:
                    pts.append([x * x * x * x, y])
            f = _linfit(pts)
            if not f or f[0] <= 0 or f[1] >= 0:
                return 0.0
            return math.pow(-f[1] / f[0], 0.25)
        if t == 3:
            pts = []
            for r in _stage(rows, 0):
                x, y = float(r["x"]), float(r["y"])
                if x >= 0.6 * p["Bm"]:
                    pts.append([x, y])
            f = _linfit(pts)
            return f[1] * 1.0e-3 / p["mass"] if f else 0.0          # A m^2 / kg = emu / g
        st = _pts(_stage(rows, 3))
        if len(st) < 4:
            return 0.0
        bgv = st[-1][1]
        top = st[0][1] - bgv
        pts = []
        for q in st:
            y = q[1] - bgv
            if y > 1e-3 * top:
                pts.append([q[0], y * y])
        f = _linfit(pts)
        if not f or f[0] >= 0:
            return 0.0
        return -f[1] / f[0]


# ============================================================================================ dilution refrigerator
class Dilution(_Sweep):
    """A 3He-4He dilution refrigerator with an ideal heat exchanger: the cooling power at the mixing chamber is
    Qdot = 84 ndot T^2 (W, ndot in mol/s; Pobell). With a heater power P on the mixing chamber and a residual heat
    leak Q0 it settles at T = sqrt((P + Q0) / (84 ndot)). x = heater power (uW); y = T (mK) at 1e-3 mK."""

    PARAMS = {"x": 0.0, "s": 0.0, "nd": 1.0e-4, "Q0": 1.0e-7, "cf": 84.0}

    @classmethod
    def read(cls, p, s, x, k):
        T = math.sqrt((x * 1.0e-6 + p["Q0"]) / (p["cf"] * p["nd"]))
        return {"y": _q(1000.0 * T, 1e-3)}

    @classmethod
    def xs(cls, p, s):
        return [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]

    @classmethod
    def fit(cls, rows, p):
        pts = [[float(r["x"]) * 1.0e-6, math.pow(float(r["y"]) * 1.0e-3, 2)] for r in _stage(rows, 0)]
        f = _linfit(pts)
        if not f or f[0] <= 0:
            return 0.0
        return 1.0 / (p["cf"] * f[0])


# ============================================================================================ relaxation calorimetry
class HCRelax(_Sweep):
    """Heat capacity by the relaxation method. The platform hangs from a weak link of conductance K(T) =
    K0 (T/2 K); a heater power P0 raises it by dT = P0/K and, switched off, it relaxes with tau = C/K, so C = K tau.
    typ 0 normal metal: C = n (gam T + beta T^3) with beta = (12 pi^4 / 5) R / ThD^3 (Debye).
    typ 1 superconductor: the same above Tc; below, the electrons give a gam Tc exp(-b Tc/T) (phenomenological).
    typ 2 magnetic insulator: lattice beta T^3 plus a two-level (Schottky) anomaly n R (D/T)^2 e^(D/T)/(1 + e^(D/T))^2.
    x = T (K); the reading is tau (s) at 1e-6 s and dT (mK) at 1e-6 mK."""

    PARAMS = {"x": 4.0, "s": 0.0, "typ": 0.0, "nmol": 1.0e-4, "gam": 6.95e-4, "ThD": 343.0, "Tc": 9.25, "a": 9.17,
              "b": 1.5, "D": 5.0, "fr": 1.0, "K0": 2.0e-7, "P0": 2.0e-9, "Tlo": 1.0, "Thi": 10.0, "dT": 0.5}

    @staticmethod
    def beta(p):
        return 12.0 * math.pow(PI, 4) * RGAS / (5.0 * math.pow(p["ThD"], 3))

    @classmethod
    def cmol(cls, p, T):
        t = _typ(p)
        lat = cls.beta(p) * T * T * T
        if t == 0:
            return p["gam"] * T + lat
        if t == 1:
            if T >= p["Tc"]:
                return p["gam"] * T + lat
            return p["a"] * p["gam"] * p["Tc"] * math.exp(-p["b"] * p["Tc"] / T) + lat
        u = p["D"] / T
        e = math.exp(-u)
        return lat + p["fr"] * RGAS * u * u * e / ((1.0 + e) * (1.0 + e))

    @classmethod
    def read(cls, p, s, x, k):
        K = p["K0"] * x / 2.0
        C = p["nmol"] * cls.cmol(p, x)
        return {"y": _q(C / K, 1e-6), "dT": _q(1000.0 * p["P0"] / K, 1e-6)}

    @classmethod
    def xs(cls, p, s):
        if _typ(p) == 1:
            return _merge(_rng(p["Tlo"], p["Thi"], p["dT"]), _grid(p["Tc"] + 0.1, p["Tc"] + 6.0, 0.5))
        return _rng(p["Tlo"], p["Thi"], p["dT"])

    @staticmethod
    def cpts(rows, p):
        out = []
        for r in _stage(rows, 0):
            T, tau, dT = float(r["x"]), float(r["y"]), float(r["dT"])
            if T > 0 and dT > 0:
                out.append([T, p["P0"] / (dT * 1.0e-3) * tau / p["nmol"]])
        out.sort(key=lambda q: q[0])
        return out

    @staticmethod
    def schottky_fit(pts, lo, hi):
        """Least squares of C = B T^3 + A f(D/T) over D (golden section), B and A linear: returns D."""
        def ssr(D):
            s11 = s12 = s22 = s1y = s2y = syy = 0.0
            for q in pts:
                T, c = q[0], q[1]
                u = D / T
                e = math.exp(-u)
                f1 = T * T * T
                f2 = u * u * e / ((1.0 + e) * (1.0 + e))
                s11 += f1 * f1
                s12 += f1 * f2
                s22 += f2 * f2
                s1y += f1 * c
                s2y += f2 * c
                syy += c * c
            det = s11 * s22 - s12 * s12
            if det == 0:
                return 1e300
            bb = (s1y * s22 - s2y * s12) / det
            aa = (s2y * s11 - s1y * s12) / det
            res = 0.0
            for q in pts:
                u = D / q[0]
                e = math.exp(-u)
                r = q[1] - bb * q[0] * q[0] * q[0] - aa * u * u * e / ((1.0 + e) * (1.0 + e))
                res += r * r
            return res
        g = (math.sqrt(5.0) - 1.0) / 2.0
        a, b = lo, hi
        c, d = b - g * (b - a), a + g * (b - a)
        fc, fd = ssr(c), ssr(d)
        for _ in range(50):
            if fc < fd:
                b, d, fd = d, c, fc
                c = b - g * (b - a)
                fc = ssr(c)
            else:
                a, c, fc = c, d, fd
                d = a + g * (b - a)
                fd = ssr(d)
        return (a + b) / 2.0

    @classmethod
    def fit(cls, rows, p):
        t = _typ(p)
        pts = cls.cpts(rows, p)
        if len(pts) < 4:
            return 0.0
        if t == 2:
            return cls.schottky_fit(pts, 0.2, 40.0)
        if t == 1:
            top = pts[-1][0]
            ln = [[q[0] * q[0], q[1] / q[0]] for q in pts if q[0] >= top - 5.0]
            f = _linfit(ln)
            return f[1] if f else 0.0
        ln = [[q[0] * q[0], q[1] / q[0]] for q in pts]
        f = _linfit(ln)
        if not f or f[0] <= 0:
            return 0.0
        return math.pow(12.0 * math.pow(PI, 4) * RGAS / (5.0 * f[0]), 1.0 / 3.0)


# ============================================================================================ thermal conductivity
class KappaLT(_Sweep):
    """Steady-state thermal conductivity at low temperature. A heater P on the free end of a rod (length L, area A),
    the other end on the bath at Tb: the hot end settles where (A/L) * integral of kappa dT from Tb to Th = P
    (Simpson, 64 strips; bisection on Th). The apparent kappa = P L / (A dT) belongs to the mean temperature.
    typ 0 metal: 1/kappa = W0/T + bet T^2 (electrons, Wiedemann-Franz W0 = rho0/L0 plus phonon scattering).
    typ 1 alloy (stainless steel): kappa = c1 T^c2.
    typ 2 insulating crystal: 1/kappa = 1/(Ab T^3) + U T^3 exp(-Th/(3 T)) with the boundary (Casimir) coefficient
    Ab = 2 pi^2 kB^4 ell / (15 hbar^3 v^2). x = Tb (K); y = dT (mK) at 1e-5 mK."""

    PARAMS = {"x": 2.0, "s": 0.0, "typ": 0.0, "rho0": 1.0e-10, "bet": 2.0e-5, "c1": 0.06, "c2": 1.1, "ell": 1.0e-3,
              "vs": 6.0e3, "U": 1.0e-6, "ThD": 1000.0, "L": 0.02, "A": 3.0e-6, "P": 1.0e-6, "Tlo": 1.0, "Thi": 20.0,
              "dT": 1.0}

    @staticmethod
    def kap(p, T):
        t = _typ(p)
        if t == 0:
            return 1.0 / (p["rho0"] / L0 / T + p["bet"] * T * T)
        if t == 1:
            return p["c1"] * math.pow(T, p["c2"])
        ab = 2.0 * PI * PI * math.pow(KB, 4) * p["ell"] / (15.0 * math.pow(HBAR, 3) * p["vs"] * p["vs"])
        return 1.0 / (1.0 / (ab * T * T * T) + p["U"] * T * T * T * math.exp(-p["ThD"] / (3.0 * T)))

    @classmethod
    def heat(cls, p, a, b):
        n = 64
        h = (b - a) / n
        s = cls.kap(p, a) + cls.kap(p, b)
        for i in range(1, n):
            s += (4.0 if i % 2 == 1 else 2.0) * cls.kap(p, a + i * h)
        return s * h / 3.0 * p["A"] / p["L"]

    @classmethod
    def read(cls, p, s, x, k):
        k0 = cls.kap(p, x)
        hi = x + 50.0 * p["P"] * p["L"] / (p["A"] * k0) + 1e-6
        th = _bisect(lambda T: cls.heat(p, x, T) - p["P"], x, hi, 80)
        return {"y": _q(1000.0 * (th - x), 1e-5)}

    @classmethod
    def xs(cls, p, s):
        return _rng(p["Tlo"], p["Thi"], p["dT"])

    @staticmethod
    def kpts(rows, p):
        out = []
        for r in _stage(rows, 0):
            T, d = float(r["x"]), float(r["y"]) * 1.0e-3
            if d > 0:
                out.append([T + d / 2.0, p["P"] * p["L"] / (p["A"] * d)])
        out.sort(key=lambda q: q[0])
        return out

    @classmethod
    def fit(cls, rows, p):
        t = _typ(p)
        pts = cls.kpts(rows, p)
        if len(pts) < 4:
            return 0.0
        if t == 0:
            f = _linfit([[q[0] * q[0] * q[0], q[0] / q[1]] for q in pts])
            return f[1] * L0 if f else 0.0
        if t == 1:
            f = _linfit([[math.log(q[0]), math.log(q[1])] for q in pts])
            return math.exp(f[1] + f[0] * math.log(4.2)) if f else 0.0
        low = [q for q in pts if q[0] <= 3.0]
        if not low:
            return 0.0
        tot = 0.0
        for q in low:
            tot += q[1] / (q[0] * q[0] * q[0])
        ab = tot / len(low)
        return ab * 15.0 * math.pow(HBAR, 3) * p["vs"] * p["vs"] / (2.0 * PI * PI * math.pow(KB, 4))


# ============================================================================================ quantum Hall effect
class QHall(_Sweep):
    """Integer quantum Hall effect of a 2D electron gas of density n (simulated, smoothed staircase). The filling factor
    is nu = n h / (e B). The Hall conductance in e^2/h is a sum of logistic steps: GaAs (gr 0, spin resolved)
    sum_k F((nu - k + 1/2)/G), graphene (gr 1) 2 + 4 sum_k F((nu - 4k)/(4 G)); the step width G = G0/B + gT T/B
    widens at low field so the staircase melts into the classical line nu. R_xy = (h/e^2)/sigma. R_xx = rho0 (L/W) S
    with S = sum of sech^2 bumps / (4G) (1 at low field), rho0 = 1/(n e mu). Stage 0 at T1 (1.5 K), stage 1 at T2
    (0.3 K); x = B (T)."""

    PARAMS = {"x": 0.0, "s": 0.0, "n": 3.0e15, "gr": 0.0, "mu": 100.0, "G0": 0.12, "gT": 0.02, "LW": 3.0,
              "T1": 1.5, "T2": 0.3, "Bmax": 9.0, "dB": 0.1}
    NST = 2

    @classmethod
    def sig(cls, p, B, T):
        nu = p["n"] * H / (QE * B)
        G = p["G0"] / B + p["gT"] * T / B
        s = 0.0
        bump = 0.0
        if p["gr"] < 0.5:
            kmax = int(nu + 12.0 * G + 6.0)
            for k in range(1, kmax + 1):
                u = (nu - k + 0.5) / G
                s += _logi(u)
                if abs(u) < 60:
                    c = math.cosh(u / 2.0)
                    bump += 1.0 / (c * c)
            return [s, bump / (4.0 * G)]
        g4 = 4.0 * G
        kmax = int(nu / 4.0 + 12.0 * G + 6.0)
        s = 2.0 * _logi(nu / g4)
        for k in range(1, kmax + 1):
            u = (nu - 4.0 * k) / g4
            s += 4.0 * _logi(u)
            if abs(u) < 60:
                c = math.cosh(u / 2.0)
                bump += 1.0 / (c * c)
        return [s, bump / (4.0 * G)]

    @classmethod
    def read(cls, p, s, x, k):
        T = p["T2"] if s == 1 else p["T1"]
        rho0 = 1.0 / (p["n"] * QE * p["mu"])
        if x <= 0:
            return {"y": 0.0, "y2": _q(rho0 * p["LW"], 1e-3)}
        sg = cls.sig(p, x, T)
        return {"y": _q(RK / sg[0], 1e-3), "y2": _q(rho0 * p["LW"] * sg[1], 1e-3)}

    @classmethod
    def xs(cls, p, s):
        return _rng(0.0, p["Bmax"], p["dB"] if s == 1 else 2.0 * p["dB"])

    @classmethod
    def fit(cls, rows, p):
        st = _stage(rows, 1)
        lo = []
        for r in st:
            x = float(r["x"])
            if 0 < x <= 0.5:
                lo.append([x, float(r["y"])])
        f = _linfit(lo)
        if not f or f[0] <= 0:
            return 0.0
        n = 1.0 / (QE * f[0])
        pts = sorted([[float(r["x"]), float(r["y"]), float(r["y2"])] for r in st], key=lambda q: q[0])
        if not pts or pts[0][0] > 0:
            return 0.0
        ref = pts[0][2]
        tot, cnt = 0.0, 0
        run = []
        for q in pts + [[1e9, 0.0, 1e300]]:
            if q[0] > 1.0 and q[2] <= 1e-4 * ref:
                run.append(q)
                continue
            if run:
                b = run[len(run) // 2]
                nu = n * H / (QE * b[0])
                if p["gr"] < 0.5:
                    i_nu = math.floor(nu + 0.5)
                else:
                    i_nu = 4.0 * math.floor((nu - 2.0) / 4.0 + 0.5) + 2.0
                if i_nu >= 1:
                    tot += i_nu * b[1]
                    cnt += 1
                run = []
        return tot / cnt if cnt else 0.0


# ============================================================================================ Shubnikov-de Haas
class SdH(_Sweep):
    """Shubnikov-de Haas oscillations by the Lifshitz-Kosevich formula (fundamental only):
    R = rho0 [1 + 4 (X/sinh X) exp(-pi/(wc tq)) cos(2 pi F/B - pi)], X = 2 pi^2 kB T m*/(hbar e B), wc = e B/m*.
    The frequency F = n h/(gs e) for a 2D gas (gs = 2 for GaAs, 4 for graphene); for bismuth F is the extremal
    cross-section of one pocket. Stage 0: R against B at T1 (12 points a period, evenly spaced in 1/B, down from Bhi); stage 1: the oscillation
    amplitude at the field Bf against T. typ 0 GaAs 2DEG, 1 graphene, 2 bismuth (3D). Readings in ohm at 1e-5."""

    PARAMS = {"x": 1.0, "s": 0.0, "typ": 0.0, "n": 3.0e15, "F": 6.3, "ms": 0.067, "tq": 1.0e-12, "rho0": 10.0,
              "T1": 1.5, "Bf": 2.0, "Bhi": 4.0, "nper": 9.0}
    NST = 2

    @classmethod
    def freq(cls, p):
        t = _typ(p)
        if t == 0:
            return p["n"] * H / (2.0 * QE)
        if t == 1:
            return p["n"] * H / (4.0 * QE)
        return p["F"]

    @classmethod
    def amp(cls, p, B, T):
        m = p["ms"] * ME
        X = 2.0 * PI * PI * KB * T * m / (HBAR * QE * B)
        rt = X / math.sinh(X) if X > 1e-6 else 1.0
        wc = QE * B / m
        return 4.0 * p["rho0"] * rt * math.exp(-PI / (wc * p["tq"]))

    @classmethod
    def read(cls, p, s, x, k):
        if s == 1:
            return {"y": _q(cls.amp(p, p["Bf"], x), 1e-5)}
        if x <= 0:
            return {"y": _q(p["rho0"], 1e-5)}
        F = cls.freq(p)
        v = p["rho0"] + cls.amp(p, x, p["T1"]) * math.cos(2.0 * PI * F / x - PI)
        return {"y": _q(v, 1e-5)}

    @classmethod
    def xs(cls, p, s):
        if s == 1:
            return [0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
        F = cls.freq(p)
        u0 = 1.0 / p["Bhi"]
        n = int(12.0 * p["nper"] + 0.5)
        return [1.0 / (u0 + (n - i) / (12.0 * F)) for i in range(n + 1)]

    @classmethod
    def ratio(cls, p, m, T, T0):
        def rt(t):
            X = 2.0 * PI * PI * KB * t * m * ME / (HBAR * QE * p["Bf"])
            return X / math.sinh(X) if X > 1e-6 else 1.0
        return rt(T) / rt(T0)

    @classmethod
    def mass_of(cls, rows, p):
        pts = _pts(_stage(rows, 1))
        if len(pts) < 3 or pts[0][1] <= 0:
            return 0.0
        T0, A0 = pts[0][0], pts[0][1]
        tot, n = 0.0, 0
        for q in pts[1:]:
            if q[1] <= 0:
                continue
            want = q[1] / A0
            m = _bisect(lambda mm: cls.ratio(p, mm, q[0], T0) - want, 1e-4, 3.0, 80)
            tot += m
            n += 1
        return tot / n if n else 0.0

    @classmethod
    def freq_of(cls, rows, p):
        pts = [[1.0 / float(r["x"]), float(r["y"])] for r in _stage(rows, 0) if float(r["x"]) > 0]
        pts.sort(key=lambda q: q[0])
        mx = []
        for i in range(1, len(pts) - 1):
            a, b, c = pts[i - 1], pts[i], pts[i + 1]
            if b[1] > a[1] and b[1] >= c[1] and b[1] > p["rho0"]:
                mx.append(_vertex(a[0], a[1], b[0], b[1], c[0], c[1]))
        if len(mx) < 3:
            return 0.0
        f = _linfit([[float(i), mx[i]] for i in range(len(mx))])
        if not f or f[0] == 0:
            return 0.0
        return 1.0 / abs(f[0])

    @classmethod
    def fit(cls, rows, p):
        t = _typ(p)
        if t == 2:
            return cls.mass_of(rows, p)
        F = cls.freq_of(rows, p)
        return F * (2.0 if t == 0 else 4.0) * QE / H


# ============================================================================================ Hall bar + van der Pauw
class HallMob(_Sweep):
    """Hall bar and van der Pauw transport of a doped layer of sheet density ns. Mobility by Matthiessen's rule,
    1/mu = 1/(muL (T/300)^-al) + 1/(muI (T/300)^1.5) (lattice and ionised-impurity scattering). Stage 0: Hall bar at
    300 K, x = B (T): V_H = I B/(e ns) (uV), V_xx = I Rs Lb/Wb (mV). Stage 1: van der Pauw square at 300 K, x = 0 / 1 =
    the two four-terminal resistances (ohm), both Rs ln2/pi for the square. Stage 2: Hall bar at B1, x = T (K)."""

    PARAMS = {"x": 0.0, "s": 0.0, "ns": 3.0e18, "muL": 0.14, "al": 2.4, "muI": 0.6, "I": 1.0e-4, "LW": 3.0, "B1": 0.5,
              "sgn": -1.0}
    NST = 3

    @staticmethod
    def mu(p, T):
        t = T / 300.0
        return 1.0 / (1.0 / (p["muL"] * math.pow(t, -p["al"])) + 1.0 / (p["muI"] * math.pow(t, 1.5)))

    @classmethod
    def read(cls, p, s, x, k):
        if s == 1:
            rs = 1.0 / (QE * p["ns"] * cls.mu(p, 300.0))
            return {"y": _q(rs * math.log(2.0) / PI, 1e-4)}
        T = x if s == 2 else 300.0
        B = p["B1"] if s == 2 else x
        rs = 1.0 / (QE * p["ns"] * cls.mu(p, T))
        return {"y": _q(1.0e6 * p["sgn"] * p["I"] * B / (QE * p["ns"]), 1e-4), "y2": _q(1.0e3 * p["I"] * rs * p["LW"], 1e-5)}

    @classmethod
    def xs(cls, p, s):
        if s == 1:
            return [0.0, 1.0]
        if s == 2:
            return [20.0, 30.0, 50.0, 77.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0]
        return _rng(-1.0, 1.0, 0.25)

    @staticmethod
    def vdp(ra, rb):
        """Sheet resistance from exp(-pi Ra/Rs) + exp(-pi Rb/Rs) = 1 (van der Pauw), by bisection."""
        lo, hi = 0.1 * (ra + rb), 20.0 * (ra + rb)
        return _bisect(lambda rs: math.exp(-PI * ra / rs) + math.exp(-PI * rb / rs) - 1.0, lo, hi, 100)

    @classmethod
    def fit(cls, rows, p):
        st0 = _stage(rows, 0)
        f = _linfit([[float(r["x"]), float(r["y"]) * 1.0e-6] for r in st0])
        if not f or f[0] == 0:
            return 0.0
        ns = p["I"] / (QE * abs(f[0]))
        r = [None, None]
        for row in _stage(rows, 1):
            i = int(float(row["x"]) + 0.5)
            if i in (0, 1):
                r[i] = float(row["y"])
        if r[0] is None or r[1] is None:
            return 0.0
        rs = cls.vdp(r[0], r[1])
        return 1.0 / (QE * ns * rs)


# ============================================================================================ Seebeck coefficient
class Seebeck(_Sweep):
    """Thermoelectric power against copper leads at a mean temperature of 300 K: V = Voff + (S - SCu) dT (uV), the
    offset Voff from the leads and the amplifier. Stage 0: differential steady state, dT = -dT0 and +dT0 (the offset
    cancels); stage 1: quasi-static slope, dT swept; stage 2: four-probe resistivity, x = I (mA), V = I rho L/A (uV)."""

    PARAMS = {"x": 0.0, "s": 0.0, "S": 2.0e-4, "SCu": 1.83e-6, "Voff": 3.2, "rho": 1.0e-5, "Ls": 0.005, "As": 4.0e-6,
              "dT0": 1.0}
    NST = 3

    @classmethod
    def read(cls, p, s, x, k):
        if s == 2:
            return {"y": _q(1.0e6 * x * 1.0e-3 * p["rho"] * p["Ls"] / p["As"], 1e-3)}
        return {"y": _q(p["Voff"] + 1.0e6 * (p["S"] - p["SCu"]) * x, 1e-3)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return [-p["dT0"], p["dT0"]]
        if s == 1:
            return _rng(-2.0, 2.0, 0.5)
        return [10.0, 20.0, 30.0, 40.0, 50.0]

    @classmethod
    def fit(cls, rows, p):
        v = [None, None]
        for r in _stage(rows, 0):
            x = float(r["x"])
            if x < 0:
                v[0] = [x, float(r["y"])]
            elif x > 0:
                v[1] = [x, float(r["y"])]
        if v[0] is None or v[1] is None:
            return 0.0
        return (v[1][1] - v[0][1]) / (v[1][0] - v[0][0]) * 1.0e-6 + p["SCu"]


# ============================================================================================ DLTS
class DLTS(_Sweep):
    """Deep level transient spectroscopy with a double boxcar. After each filling pulse the capacitance recovers as
    dC(t) = dC0 exp(-e t), dC0 = C0 NT/(2 ND), with the emission rate e = sig gam T^2 exp(-Ea/(kB T)). The boxcar
    signal S(T) = dC0 [exp(-e t1) - exp(-e t2)] (t2 = 2 t1) peaks where e = ln 2 / t1 (the rate window). Stage i =
    rate window t1 = tw * [1, 2, 5, 10][i]; x = T (K); y = S (fF) at 1e-4 fF."""

    PARAMS = {"x": 200.0, "s": 0.0, "Ea": 0.55, "sig": 1.0e-19, "gam": 1.07e25, "NT": 1.0e19, "ND": 1.0e21,
              "C0": 100.0, "tw": 1.0e-3}
    NST = 4
    WIN = [1.0, 2.0, 5.0, 10.0]

    @classmethod
    def rate(cls, p, T):
        return p["sig"] * p["gam"] * T * T * math.exp(-p["Ea"] * QE / (KB * T))

    @classmethod
    def t1(cls, p, s):
        return p["tw"] * cls.WIN[s]

    @classmethod
    def read(cls, p, s, x, k):
        e = cls.rate(p, x)
        t1 = cls.t1(p, s)
        dc0 = 1000.0 * p["C0"] * p["NT"] / (2.0 * p["ND"])
        return {"y": _q(dc0 * (math.exp(-e * t1) - math.exp(-e * 2.0 * t1)), 1e-4)}

    @classmethod
    def tpeak(cls, p, s):
        want = math.log(2.0) / cls.t1(p, s)
        return _bisect(lambda T: cls.rate(p, T) - want, 20.0, 800.0, 80)

    @classmethod
    def xs(cls, p, s):
        tp = cls.tpeak(p, s)
        return _grid(tp - 6.0, tp + 6.0, 0.5)

    @classmethod
    def arr(cls, rows, p):
        out = []
        for s in range(4):
            pk = _peakx(_pts(_stage(rows, s)))
            if pk:
                out.append([1.0 / pk, math.log(math.log(2.0) / cls.t1(p, s) / (pk * pk))])
        return out

    @classmethod
    def fit(cls, rows, p):
        f = _linfit(cls.arr(rows, p))
        if not f or f[0] >= 0:
            return 0.0
        return -f[0] * KB / QE


# ============================================================================================ C-V profiling
class CVProf(_Sweep):
    """High-frequency C-V of a junction of area A, in the depletion approximation.
    typ 0 Schottky diode on n-type: 1/C^2 = 2 (Vbi - V - kT/q) / (q eps ND A^2).
    typ 1 one-sided abrupt p+-n junction: the same with Vbi = (kT/q) ln(NA ND / ni^2).
    typ 2 MOS capacitor on p-type: accumulation C = Cox below VFB; depletion 1/C^2 = 1/Cox^2 + 2 (V - VFB)/(q eps NA A^2);
    no lower than the strong-inversion Cmin. VFB = phims - Qox/Cox. x = V (volt); y = C (pF) at 1e-4 pF."""

    PARAMS = {"x": 0.0, "s": 0.0, "typ": 0.0, "ND": 1.0e22, "NA": 1.0e25, "Vbi": 0.6, "A": 1.0e-6, "er": 11.7,
              "T": 300.0, "ni": 1.0e16, "tox": 1.0e-8, "erox": 3.9, "phims": -0.9, "Qox": 5.0e-4, "Vlo": -4.0,
              "Vhi": 0.2}

    @classmethod
    def vbi(cls, p):
        if _typ(p) == 1:
            return KB * p["T"] / QE * math.log(p["NA"] * p["ND"] / (p["ni"] * p["ni"]))
        return p["Vbi"]

    @classmethod
    def cox(cls, p):
        return p["erox"] * EPS0 * p["A"] / p["tox"]

    @classmethod
    def vfb(cls, p):
        return p["phims"] - p["Qox"] / (p["erox"] * EPS0 / p["tox"])

    @classmethod
    def cap(cls, p, V):
        eps = p["er"] * EPS0
        if _typ(p) < 2:
            arg = cls.vbi(p) - V - KB * p["T"] / QE
            if arg <= 0:
                arg = 1e-6
            return math.sqrt(QE * eps * p["ND"] * p["A"] * p["A"] / (2.0 * arg))
        cox = cls.cox(p)
        vfb = cls.vfb(p)
        if V <= vfb:
            return cox
        inv = 1.0 / (cox * cox) + 2.0 * (V - vfb) / (QE * eps * p["NA"] * p["A"] * p["A"])
        c = 1.0 / math.sqrt(inv)
        phif = KB * p["T"] / QE * math.log(p["NA"] / p["ni"])
        wmax = math.sqrt(4.0 * eps * phif / (QE * p["NA"]))
        cmin = 1.0 / (1.0 / cox + wmax / (eps * p["A"]))
        return c if c > cmin else cmin

    @classmethod
    def read(cls, p, s, x, k):
        return {"y": _q(1.0e12 * cls.cap(p, x), 1e-4)}

    @classmethod
    def xs(cls, p, s):
        if _typ(p) == 2:
            v0 = cls.vfb(p)
            return _rng(v0 - 2.0, v0 + 3.0, 0.1)
        return _rng(p["Vlo"], p["Vhi"], 0.2)

    @classmethod
    def fit(cls, rows, p):
        t = _typ(p)
        eps = p["er"] * EPS0
        pts = _pts(_stage(rows, 0))
        if len(pts) < 4:
            return 0.0
        if t < 2:
            f = _linfit([[q[0], 1.0 / math.pow(q[1] * 1.0e-12, 2)] for q in pts])
            if not f or f[0] >= 0:
                return 0.0
            if t == 0:
                return -2.0 / (QE * eps * p["A"] * p["A"] * f[0])
            return -f[1] / f[0] + KB * p["T"] / QE
        cmax = cmin = pts[0][1]
        for q in pts:
            cmax = max(cmax, q[1])
            cmin = min(cmin, q[1])
        dep = [[q[0], 1.0 / math.pow(q[1] * 1.0e-12, 2)] for q in pts if 1.02 * cmin < q[1] < 0.98 * cmax]
        f = _linfit(dep)
        if not f or f[0] <= 0:
            return 0.0
        return (1.0 / math.pow(cmax * 1.0e-12, 2) - f[1]) / f[0]


# ============================================================================================ Haynes-Shockley
class HaynesShockley(_Sweep):
    """Haynes-Shockley: a laser pulse injects N minority carriers at x = 0 of a bar in a drift field E; they drift at
    v = mu E, spread with D = mu kB T/e and recombine with lifetime tau: n(d, t) ~ exp(-(d - v t)^2/(4 D t) - t/tau)/sqrt(t).
    The collector at distance d sees the pulse peak at the root of (v^2 + 4D/tau) t^2 + 2 D t - d^2 = 0 (exact for this
    profile). Stage 0: E fixed, x = d (mm); stage 1: d fixed, x = E (V/cm). Reading: peak time (us, 1e-4), full
    width at half maximum (us), peak height (mV)."""

    PARAMS = {"x": 5.0, "s": 0.0, "mu": 0.19, "T": 300.0, "tau": 5.0e-5, "E0": 4000.0, "d0": 0.005, "sc": 100.0}
    NST = 2

    @classmethod
    def prof(cls, p, d, E, t):
        v = p["mu"] * E
        D = p["mu"] * KB * p["T"] / QE
        return math.exp(-math.pow(d - v * t, 2) / (4.0 * D * t) - t / p["tau"]) / math.sqrt(t)

    @classmethod
    def peak(cls, p, d, E):
        v = p["mu"] * E
        D = p["mu"] * KB * p["T"] / QE
        a = v * v + 4.0 * D / p["tau"]
        return (-D + math.sqrt(D * D + d * d * a)) / a

    @classmethod
    def fwhm(cls, p, d, E, t0):
        top = cls.prof(p, d, E, t0)
        lo = _bisect(lambda t: cls.prof(p, d, E, t) - top / 2.0, t0 * 0.2, t0, 80)
        hi = _bisect(lambda t: cls.prof(p, d, E, t) - top / 2.0, t0, t0 * 5.0, 80)
        return hi - lo

    @classmethod
    def read(cls, p, s, x, k):
        d = x * 1.0e-3 if s == 0 else p["d0"]
        E = p["E0"] if s == 0 else x * 100.0
        t0 = cls.peak(p, d, E)
        return {"y": _q(1.0e6 * t0, 1e-4), "y2": _q(1.0e6 * cls.fwhm(p, d, E, t0), 1e-4),
                "y3": _q(p["sc"] * math.sqrt(1.0e-6) * cls.prof(p, d, E, t0), 1e-4)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        return [10.0, 15.0, 20.0, 25.0, 30.0]

    @classmethod
    def fit(cls, rows, p):
        f = _linfit([[float(r["x"]) * 1.0e-3, float(r["y"]) * 1.0e-6] for r in _stage(rows, 0)])
        if not f or f[0] <= 0:
            return 0.0
        return 1.0 / (f[0] * p["E0"])


# ============================================================================================ solar cell EQE + dark I-V
class SolarEQE(_Sweep):
    """Solar cell: external quantum efficiency EQE = eta (1 - R) (1 - exp(-alpha W)) with alpha = a0 (E - Eg)^pw above
    the gap (pw 2 indirect, 0.5 direct); and the dark I-V of the one-diode model with series and shunt resistance,
    I = I0 (exp((V - I Rs)/(n kT/q)) - 1) + (V - I Rs)/Rsh, solved by bisection on I. Stage 0: x = wavelength (nm),
    y = EQE (%) at 1e-3; stage 1: x = V (volt), y = I (mA) at 1e-7 mA."""

    PARAMS = {"x": 500.0, "s": 0.0, "Eg": 1.12, "a0": 1.0e6, "pw": 2.0, "W": 1.8e-4, "R": 0.05, "eta": 0.95,
              "nid": 1.3, "I0": 1.0e-10, "Rs": 0.1, "Rsh": 1.0e8, "T": 300.0, "l0": 350.0, "l1": 1200.0,
              "Va": 0.05, "Vb": 0.6}
    NST = 2

    @classmethod
    def eqe(cls, p, lam):
        if lam <= 0:
            return 0.0
        E = 1239.84198 / lam
        if E <= p["Eg"]:
            return 0.0
        a = p["a0"] * math.pow(E - p["Eg"], p["pw"])
        return p["eta"] * (1.0 - p["R"]) * (1.0 - math.exp(-a * p["W"]))

    @classmethod
    def cur(cls, p, V):
        vt = p["nid"] * KB * p["T"] / QE

        def g(I):
            vj = V - I * p["Rs"]
            return p["I0"] * (math.exp(vj / vt) - 1.0) + vj / p["Rsh"] - I
        hi = V / p["Rs"] if V > 0 else 1e-9
        return _bisect(g, 0.0, hi, 120)

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            return {"y": _q(100.0 * cls.eqe(p, x), 1e-3)}
        return {"y": _q(1000.0 * cls.cur(p, x), 1e-7)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return _rng(p["l0"], p["l1"], 25.0)
        return _rng(p["Va"], p["Vb"], 0.025)

    @classmethod
    def fit(cls, rows, p):
        pts = []
        for r in _stage(rows, 1):
            I = float(r["y"]) * 1.0e-3
            if 1.0e-6 <= I <= 1.0e-4:
                pts.append([float(r["x"]), math.log(I)])
        f = _linfit(pts)
        if not f or f[0] <= 0:
            return 0.0
        return QE / (KB * p["T"] * f[0])


# ============================================================================================ Moessbauer
class Moss(_Sweep):
    """Fe-57 Moessbauer transmission spectrum with a constant-acceleration drive (velocity scale calibrated). Lines are
    Lorentzians of full width G (mm/s) and fractional depth a: counts = N0 (1 - sum a_i / (1 + ((v - v_i)/(G/2))^2)).
    typ 0 magnetic sextet: v = dIS + (B/Eg c)(... ) for the six allowed m -> m' transitions, intensities 3:2:1:1:2:3,
    lines 1 and 6 shifted by +eps, 2-5 by -eps (first-order quadrupole shift); typ 1 singlet at dIS; typ 2 quadrupole
    doublet at dIS -+ QS/2. Stage 0: survey (0.25 mm/s); stage 1: fine steps G/6 across each line."""

    PARAMS = {"x": 0.0, "s": 0.0, "typ": 0.0, "B": 33.0, "dIS": 0.0, "eps": 0.0, "QS": 0.0, "G": 0.25, "dep": 0.06,
              "N0": 1.0e6, "vmax": 10.0}
    NST = 2

    @staticmethod
    def kv():
        """Velocity (mm/s) per tesla per unit of (g m): muN c / E_gamma * 1000."""
        return MUN * C0 / EGAM * 1000.0

    @classmethod
    def lines(cls, p):
        t = _typ(p)
        if t == 1:
            return [[p["dIS"], 1.0]]
        if t == 2:
            return [[p["dIS"] - p["QS"] / 2.0, 1.0], [p["dIS"] + p["QS"] / 2.0, 1.0]]
        ge = MU_E / 1.5
        gg = MU_G / 0.5
        out = []
        trans = [[-1.5, -0.5, 3.0, 1.0], [-0.5, -0.5, 2.0, -1.0], [0.5, -0.5, 1.0, -1.0],
                 [-0.5, 0.5, 1.0, -1.0], [0.5, 0.5, 2.0, -1.0], [1.5, 0.5, 3.0, 1.0]]
        for tr in trans:
            v = -(ge * tr[0] - gg * tr[1]) * p["B"] * cls.kv()
            out.append([p["dIS"] + v + tr[3] * p["eps"], tr[2] / 3.0])
        out.sort(key=lambda q: q[0])
        return out

    @classmethod
    def read(cls, p, s, x, k):
        a = 0.0
        hw = p["G"] / 2.0
        for ln in cls.lines(p):
            u = (x - ln[0]) / hw
            a += p["dep"] * ln[1] / (1.0 + u * u)
        return {"y": _q(p["N0"] * (1.0 - a), 1.0)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            vm = p["vmax"] if _typ(p) == 0 else 4.0
            return _rng(-vm, vm, 0.25)
        out = []
        st = p["G"] / 6.0
        for ln in cls.lines(p):
            out = _merge(out, _grid(ln[0] - p["G"], ln[0] + p["G"], st))
        return out

    @classmethod
    def centres(cls, rows, p):
        pts = _pts(_stage(rows, 1))
        groups, cur = [], []
        for q in pts:
            if cur and q[0] - cur[-1][0] > p["G"] / 3.0:
                groups.append(cur)
                cur = []
            cur.append(q)
        if cur:
            groups.append(cur)
        out = []
        for g in groups:
            if len(g) < 3:
                continue
            ib = 0
            for i in range(len(g)):
                if g[i][1] < g[ib][1]:
                    ib = i
            if ib == 0 or ib == len(g) - 1:
                continue
            ys = [1.0 / max(p["N0"] - q[1], 1.0) for q in (g[ib - 1], g[ib], g[ib + 1])]
            out.append(_vertex(g[ib - 1][0], ys[0], g[ib][0], ys[1], g[ib + 1][0], ys[2]))
        return out

    @classmethod
    def fit(cls, rows, p):
        t = _typ(p)
        c = cls.centres(rows, p)
        if t == 1:
            return c[0] if len(c) == 1 else 0.0
        if t == 2:
            return c[1] - c[0] if len(c) == 2 else 0.0
        if len(c) != 6:
            return 0.0
        k = (-MU_E + MU_G) * cls.kv()                       # outer line separation per tesla is 2k
        return (c[5] - c[0]) / (2.0 * k)


# ============================================================================================ FMR
class FMR(_Sweep):
    """Ferromagnetic resonance, field swept at fixed microwave frequencies. Kittel: sphere (typ 0) f = gp B;
    thin film magnetised in plane (typ 1) f = gp sqrt(B (B + mu0 Ms)), gp = g muB / h. Peak-to-peak width of the
    derivative line dBpp = dB0 + (2/sqrt3) alpha f / gp (Gilbert damping). Signal = -2u/(1 + u^2)^2 with
    u = (B - Br)/(sqrt3/2 dBpp). Stage i = frequency f = [4, 8, 12, 16][i] GHz; x = B (T); y = signal (arb.)."""

    PARAMS = {"x": 0.1, "s": 0.0, "typ": 0.0, "g": 2.0, "Ms": 0.0, "alpha": 1.0e-4, "dB0": 5.0e-5}
    NST = 4
    FR = [4.0e9, 8.0e9, 12.0e9, 16.0e9]

    @classmethod
    def gp(cls, p):
        return p["g"] * MUB / H

    @classmethod
    def br(cls, p, f):
        b = f / cls.gp(p)
        if _typ(p) == 0:
            return b
        m = p["Ms"]
        return (-m + math.sqrt(m * m + 4.0 * b * b)) / 2.0

    @classmethod
    def dbpp(cls, p, f):
        return p["dB0"] + 2.0 / math.sqrt(3.0) * p["alpha"] * f / cls.gp(p)

    @classmethod
    def read(cls, p, s, x, k):
        f = cls.FR[s]
        u = (x - cls.br(p, f)) / (math.sqrt(3.0) / 2.0 * cls.dbpp(p, f))
        return {"y": _q(-1000.0 * 2.0 * u / math.pow(1.0 + u * u, 2), 1e-3)}

    @classmethod
    def xs(cls, p, s):
        f = cls.FR[s]
        b, w = cls.br(p, f), cls.dbpp(p, f)
        return [b + w * (-2.0 + 0.2 * i) for i in range(21)]

    @classmethod
    def res(cls, rows, p):
        out = []
        for s in range(4):
            pts = _pts(_stage(rows, s))
            if len(pts) < 5:
                continue
            f = cls.FR[s]
            z = _zeros_down(pts, 0.3, 1.0)
            if z:
                out.append([f, z[0]])
        return out

    @classmethod
    def fit(cls, rows, p):
        r = cls.res(rows, p)
        if len(r) < 3:
            return 0.0
        if _typ(p) == 0:
            f = _linfit([[q[1], q[0]] for q in r])
            return f[0] * H / MUB if f else 0.0
        f = _linfit([[q[1], q[0] * q[0] / q[1]] for q in r])
        if not f or f[0] <= 0:
            return 0.0
        return f[1] / f[0]


# ============================================================================================ ESR
class ESR(_Sweep):
    """Electron spin resonance at a fixed X-band frequency f, field-modulated (first-derivative) detection. Lines to
    second order in the isotropic hyperfine constant A (field units): B_m = B0 - A m - (A^2/(2 B0)) (I(I+1) - m^2),
    B0 = h f/(g muB), m = -I..I. Derivative Lorentzian of peak-to-peak width dBpp. typ 0 DPPH (no resolved hyperfine),
    typ 1 Mn2+ in MgO (I = 5/2), typ 2 a radical with one alpha proton (I = 1/2). x = B (mT); y = signal (arb.)."""

    PARAMS = {"x": 330.0, "s": 0.0, "typ": 0.0, "g": 2.0036, "A": 0.0, "I": 0.0, "f": 9.5e9, "dBpp": 0.15}

    @classmethod
    def b0(cls, p):
        return H * p["f"] / (p["g"] * MUB) * 1000.0

    @classmethod
    def lines(cls, p):
        b0 = cls.b0(p)
        out = []
        n = int(2.0 * p["I"] + 0.5)
        for i in range(n + 1):
            m = -p["I"] + i
            out.append(b0 - p["A"] * m - p["A"] * p["A"] / (2.0 * b0) * (p["I"] * (p["I"] + 1.0) - m * m))
        out.sort()
        return out

    @classmethod
    def read(cls, p, s, x, k):
        hw = math.sqrt(3.0) / 2.0 * p["dBpp"]
        v = 0.0
        for b in cls.lines(p):
            u = (x - b) / hw
            v += -2.0 * u / math.pow(1.0 + u * u, 2)
        return {"y": _q(1000.0 * v, 1e-3)}

    @classmethod
    def xs(cls, p, s):
        out = []
        w = p["dBpp"]
        for b in cls.lines(p):
            out = _merge(out, [b + w * (-2.0 + 0.25 * i) for i in range(17)])
        return out

    @classmethod
    def fit(cls, rows, p):
        z = _zeros_down(_pts(_stage(rows, 0)), 0.2, 0.5 * p["dBpp"])
        t = _typ(p)
        if t == 0:
            if len(z) != 1:
                return 0.0
            return H * p["f"] / (MUB * z[0] * 1.0e-3)
        n = int(2.0 * p["I"] + 0.5) + 1
        if len(z) != n or n < 2:
            return 0.0
        return (z[-1] - z[0]) / (n - 1)


# ============================================================================================ positron annihilation
class Positron(_Sweep):
    """Positron annihilation with a Na-22 source sandwiched in the sample. Stage 0: fast-fast lifetime spectrum (start
    1274 keV, stop 511 keV): counts per channel of width dt = N dt sum_i (I_i/tau_i) exp(-t'/tau_i) convolved with a
    Gaussian resolution sigma (exponentially modified Gaussian), plus a flat background; x = t (ns). Stage 1: 1D angular
    correlation, x = theta (mrad): metal (typ 0) = free-electron parabola (thF^2 - th^2) below the Fermi cut-off thF
    plus a Gaussian core part; polymer (typ 1) = a narrow para-positronium Gaussian on a broad one."""

    PARAMS = {"x": 0.0, "s": 0.0, "typ": 0.0, "t1": 0.165, "t2": 0.4, "t3": 2.5, "i2": 0.0, "i3": 0.0, "sg": 0.106,
              "tz": 2.0, "Nt": 1.0e9, "dt": 0.025, "bg": 20.0, "thF": 6.8, "cw": 9.0, "cf": 0.15, "pw": 0.6,
              "pf": 0.15, "Na": 1.0e5}
    NST = 2

    @classmethod
    def emg(cls, t, tau, sg):
        u = t / tau
        z = (sg / tau - t / sg) / math.sqrt(2.0)
        return 0.5 / tau * math.exp(sg * sg / (2.0 * tau * tau) - u) * _erfc(z)

    @classmethod
    def read(cls, p, s, x, k):
        if s == 1:
            th = x
            if _typ(p) == 0:
                par = (p["thF"] * p["thF"] - th * th) / (p["thF"] * p["thF"]) if abs(th) < p["thF"] else 0.0
                v = p["Na"] * ((1.0 - p["cf"]) * par + p["cf"] * math.exp(-th * th / (2.0 * p["cw"] * p["cw"])))
            else:
                v = p["Na"] * (p["pf"] * math.exp(-th * th / (2.0 * p["pw"] * p["pw"]))
                               + (1.0 - p["pf"]) * math.exp(-th * th / (2.0 * p["cw"] * p["cw"])))
            return {"y": _q(v, 1.0)}
        t = x - p["tz"]
        i1 = 1.0 - p["i2"] - p["i3"]
        f = i1 * cls.emg(t, p["t1"], p["sg"])
        if p["i2"] > 0:
            f += p["i2"] * cls.emg(t, p["t2"], p["sg"])
        if p["i3"] > 0:
            f += p["i3"] * cls.emg(t, p["t3"], p["sg"])
        return {"y": _q(p["Nt"] * p["dt"] * f + p["bg"], 1.0)}

    @classmethod
    def xs(cls, p, s):
        if s == 1:
            return _rng(-15.0, 15.0, 1.0)
        if _typ(p) == 0:
            return _merge(_rng(0.0, 1.5, 0.25), _rng(1.5, 5.0, 0.05))
        return _merge(_rng(0.0, 1.5, 0.25), _merge(_rng(1.5, 4.0, 0.1), _rng(4.0, 20.0, 0.5)))

    @classmethod
    def fit(cls, rows, p):
        pts = _pts(_stage(rows, 0))
        if len(pts) < 10:
            return 0.0
        bg = pts[0][1]
        ib = 0
        for i in range(len(pts)):
            if pts[i][1] > pts[ib][1]:
                ib = i
        tp = pts[ib][0]
        if _typ(p) == 0:
            lo, hi = tp + 0.6, tp + 2.6
        else:
            lo, hi = tp + 6.0, tp + 16.0
        ln = []
        for q in pts:
            if lo <= q[0] <= hi and q[1] - bg > 200.0:
                ln.append([q[0], math.log(q[1] - bg)])
        f = _linfit(ln)
        if not f or f[0] >= 0:
            return 0.0
        return -1.0 / f[0]


# ============================================================================================ MOKE
class MOKE(_Sweep):
    """Magneto-optic Kerr effect of a thin film. Longitudinal MOKE along the marked axis (in-plane field): descending
    and ascending branches th = thK tanh((B -+ Bc)/Bw) (mrad, phenomenological loop; the coercive field is where th
    crosses zero). Remanence against the in-plane angle phi after saturating along phi: uniaxial (typ 0, 1)
    |cos(phi - phE)|, fourfold cubic (typ 2) max(|cos|, |sin|) of (phi - phE). Polar MOKE (out-of-plane field) of an
    in-plane film: th = thP clamp(B/Bs) (hard axis, Bs = mu0 Ms). Stages: 0 descending, 1 ascending, 2 remanence
    against phi (deg), 3 polar loop. x = field (mT) or angle; y = Kerr rotation (mrad) at 1e-5."""

    PARAMS = {"x": 0.0, "s": 0.0, "typ": 0.0, "Bc": 2.0, "Bw": 0.5, "thK": 0.25, "phE": 30.0, "thP": 2.0,
              "Bs": 1700.0, "Bmax": 10.0}
    NST = 4

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            v = p["thK"] * math.tanh((x + p["Bc"]) / p["Bw"])
        elif s == 1:
            v = p["thK"] * math.tanh((x - p["Bc"]) / p["Bw"])
        elif s == 2:
            a = (x - p["phE"]) * PI / 180.0
            if _typ(p) == 2:
                v = p["thK"] * max(abs(math.cos(a)), abs(math.sin(a)))
            else:
                v = p["thK"] * abs(math.cos(a))
        else:
            r = x / p["Bs"]
            if r > 1:
                r = 1.0
            if r < -1:
                r = -1.0
            v = p["thP"] * r
        return {"y": _q(v, 1e-5)}

    @classmethod
    def xs(cls, p, s):
        if s == 2:
            return _rng(0.0, 180.0, 10.0)
        if s == 3:
            return _rng(-2.0 * p["Bs"], 2.0 * p["Bs"], 0.25 * p["Bs"])
        a = _rng(-p["Bmax"], p["Bmax"], p["Bmax"] / 5.0)
        c = -p["Bc"] if s == 0 else p["Bc"]
        b = _grid(c - 2.0 * p["Bw"], c + 2.0 * p["Bw"], p["Bw"] / 4.0)
        pts = _merge(a, b)
        return sorted(pts, reverse=True) if s == 0 else pts

    @staticmethod
    def zero(st):
        pts = _pts(st)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a[1] < 0 <= b[1] and b[1] != a[1]:
                return a[0] - a[1] * (b[0] - a[0]) / (b[1] - a[1])
        return None

    @classmethod
    def fit(cls, rows, p):
        z0 = cls.zero(_stage(rows, 0))
        z1 = cls.zero(_stage(rows, 1))
        if z0 is None or z1 is None:
            return 0.0
        return (z1 - z0) / 2.0


# ============================================================================================ registry
KERNELS: dict[str, Any] = {
    "pk10_sctc": SCRT, "pk10_jc": SCJc, "pk10_mag": Magnet, "pk10_dil": Dilution, "pk10_hcr": HCRelax,
    "pk10_ktc": KappaLT, "pk10_qhe": QHall, "pk10_sdh": SdH, "pk10_hall": HallMob, "pk10_seeb": Seebeck,
    "pk10_dlts": DLTS, "pk10_cv": CVProf, "pk10_hs": HaynesShockley, "pk10_eqe": SolarEQE, "pk10_moss": Moss,
    "pk10_fmr": FMR, "pk10_esr": ESR, "pk10_pos": Positron, "pk10_moke": MOKE,
}
FAMILY = {k: "solid" for k in KERNELS}


def _mag_truth(p):
    t = _typ(p)
    if t == 0:
        return p["g"] * math.sqrt(p["J"] * (p["J"] + 1.0))
    if t == 1:
        return Magnet.tb(p)
    if t == 2:
        return p["Tc"]
    if t == 3:
        return p["ms0"] * math.sqrt(1.0 - p["T0"] / p["Tc"]) / p["mass"]
    return p["Tc"]


TEXTBOOK = {
    "pk10t_tc": lambda p: p["Tc0"],
    "pk10t_jc": lambda p: SCJc.ic(p, p["T1"], 0.0) / p["area"],
    "pk10t_mag": _mag_truth,
    "pk10t_nd": lambda p: p["nd"],
    "pk10t_hcr": lambda p: [p["ThD"], p["gam"], p["D"]][_typ(p)],
    # Wiedemann-Franz residual resistivity; kappa = c1 4.2^c2 for the alloy; the Casimir boundary length
    "pk10t_ktc": lambda p: [p["rho0"], p["c1"] * math.pow(4.2, p["c2"]), p["ell"]][_typ(p)],
    "pk10t_rk": lambda p: RK,
    "pk10t_sdh": lambda p: p["ms"] if _typ(p) == 2 else p["n"],
    "pk10t_mu": lambda p: HallMob.mu(p, 300.0),
    "pk10t_s": lambda p: p["S"],
    "pk10t_ea": lambda p: p["Ea"],
    "pk10t_cv": lambda p: [p["ND"], CVProf.vbi(p), CVProf.vfb(p)][_typ(p)],
    "pk10t_hs": lambda p: p["mu"],
    "pk10t_nid": lambda p: p["nid"],
    "pk10t_moss": lambda p: [p["B"], p["dIS"], p["QS"]][_typ(p)],
    "pk10t_fmr": lambda p: p["g"] if _typ(p) == 0 else p["Ms"],
    "pk10t_esr": lambda p: p["g"] if _typ(p) == 0 else p["A"],
    "pk10t_pos": lambda p: p["t1"] if _typ(p) == 0 else p["t3"],
    "pk10t_hc": lambda p: p["Bc"],
}
