"""Kernel pack `pg_matter_w9`: M.Sc. solid state, nuclear, modern, wave and microwave set-ups, wave 9 (kernels `pm9_*`).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/pg_matter_w9.js` (same formulas, same order of operations, same numbers).

Every kernel here is a SWEEP: the student sets one control `x` (a voltage, a temperature, a distance, an angle, a
frequency, a channel...) in one or more stages `s`, and reads the instrument. `read(p, s, x, k)` gives the reading
(k numbers the reading, so a count is the same Poisson number on both sides), `plan(p)` lists the settings a careful
student takes, `fit(rows, p)` works the result out of the recorded rows exactly as the rig does, and `measure(p)` runs
the plan and the fit. The lab's check compares `measure()["res"]` with the textbook relation in TEXTBOOK.

Counting data (GM, spark, proportional, scintillation, coincidence counters) is a Poisson draw from the lab's own seed
(Lehmer generator; above 50 counts the Gaussian approximation): SIMULATED DATA. Everything else is deterministic and
rounded to the instrument's least count. No randomness from the system, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
LN2 = math.log(2.0)
NA = 6.02214076e23            # CODATA / SI 2019
KB_EV = 8.617333262e-5        # Boltzmann constant, eV/K (CODATA 2018)
QE = 1.602176634e-19          # elementary charge, C (SI 2019)
YEAR = 3.15576e7              # Julian year, s
ME_KEV = 510.99895            # electron rest energy, keV (CODATA 2018)
ALPHA = 1.0 / 137.035999084   # fine-structure constant (CODATA 2018)
C0 = 299792458.0              # speed of light, m/s
HC_EVNM = 1239.84198          # h c in eV nm (CODATA 2018)
HC_KEVA = 12.3984198          # h c in keV Angstrom


# ============================================================================================ helpers (twinned)
def _q(v: float, q: float) -> float:
    """Round to the least count q (half away from zero is not needed: readings here are positive or symmetric)."""
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


def _half(pts: list, lvl: float, side: int, i0: int) -> float | None:
    """Linear interpolation of where the curve pts ([x, y] sorted by x) crosses `lvl`, walking from the index i0
    to the right (side 1) or to the left (side -1)."""
    i = i0
    while 0 <= i + side < len(pts):
        a, b = pts[i], pts[i + side]
        if (a[1] - lvl) * (b[1] - lvl) <= 0 and a[1] != b[1]:
            return a[0] + (lvl - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        i += side
    return None


def _sorted(rows: list, key_y: str = "y") -> list:
    pts = [[float(r["x"]), float(r[key_y])] for r in rows]
    pts.sort(key=lambda q: q[0])
    return pts


def _peakwidth(pts: list, lo: float, hi: float, base: float):
    """The peak of pts between x = lo and hi above the level `base`: [centre (half-height midpoint), FWHM, top]."""
    best, ib = -1e300, -1
    for i, q in enumerate(pts):
        if lo <= q[0] <= hi and q[1] > best:
            best, ib = q[1], i
    if ib < 0:
        return None
    lvl = base + (best - base) / 2.0
    a = _half(pts, lvl, -1, ib)
    b = _half(pts, lvl, 1, ib)
    if a is None or b is None:
        return None
    return [(a + b) / 2.0, b - a, best]


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


def _rng(a: float, b: float, d: float) -> list:
    n = int(math.floor((b - a) / d + 0.5))
    return [a + d * i for i in range(n + 1)]


# ============================================================================================ GM plateau + dead time
class GMDead(_Sweep):
    """End-window GM tube on a scaler. Stage 0: count rate against the tube voltage V (the plateau). Stage 1, at the
    operating voltage, the TWO-SOURCE method: background (x = 0), source 1 (x = 1), both sources (x = 2), source 2
    (x = 3). The tube is non-paralysable with dead time tau: observed m = n / (1 + n tau)."""

    PARAMS = {"x": 0.0, "s": 0.0, "V": 450.0, "Vs": 330.0, "Vp": 700.0, "slope": 0.04, "n1": 1800.0, "n2": 1500.0,
              "nb": 0.8, "tau": 3.0e-4, "t": 1200.0, "tp": 30.0, "seed": 11.0}
    NST = 2

    @staticmethod
    def eff(p, V):
        if V <= p["Vs"]:
            return 0.0
        r = min(1.0, (V - p["Vs"]) / 30.0)
        g = 1.0 + p["slope"] * max(V - p["Vs"] - 30.0, 0.0) / 100.0
        if V > p["Vp"]:
            g *= 1.0 + ((V - p["Vp"]) / 25.0) ** 2
        return r * g

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            n = (p["n1"] + p["nb"]) * cls.eff(p, x)
            m = n / (1.0 + n * p["tau"])
            c = _cnt(p, k, m * p["tp"])
            return {"y": c / p["tp"], "N": c, "T": p["tp"]}
        f = cls.eff(p, p["V"])
        i = int(x + 0.5)
        n = p["nb"] + (p["n1"] if i in (1, 2) else 0.0) + (p["n2"] if i in (2, 3) else 0.0)
        n *= f
        m = n / (1.0 + n * p["tau"])
        c = _cnt(p, k, m * p["t"])
        return {"y": c / p["t"], "N": c, "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        return _rng(300.0, 760.0, 20.0) if s == 0 else [0.0, 1.0, 2.0, 3.0]

    @staticmethod
    def tau_of(m):
        """Two-source dead time: the tau for which the true rates n = m / (1 - m tau) add up, n1 + n2 = n12 + nb."""
        mb, m1, m12, m2 = m
        if min(m1, m2, m12) <= 0:
            return 0.0

        def g(tau):
            def n(v):
                return v / (1.0 - v * tau)
            return n(m1) + n(m2) - n(m12) - n(mb)

        lo, hi = 0.0, 0.999 / max(m1, m2, m12)
        if g(lo) <= 0:
            return 0.0
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if g(mid) > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    @classmethod
    def fit(cls, rows, p):
        m = [None, None, None, None]
        for r in _stage(rows, 1):
            i = int(float(r["x"]) + 0.5)
            if 0 <= i <= 3:
                m[i] = float(r["y"])
        if any(v is None for v in m):
            return 0.0
        return cls.tau_of(m)


# ============================================================================================ GM efficiency
class GMEff(_Sweep):
    """A sealed source of known activity A (Bq, certificate) emitting y particles per decay on the axis of an
    end-window GM tube of window radius a, at a distance d. The geometric fraction is G = (1 - d / sqrt(d^2 + a^2)) / 2
    and the tube counts a fraction eint of what enters (its intrinsic efficiency). Stage 0: background; stage 1: the
    source at several distances. Dead time tau corrected."""

    PARAMS = {"x": 0.0, "s": 0.0, "A": 3700.0, "yld": 2.0, "eint": 0.9, "a": 0.014, "nb": 0.5, "tau": 2.5e-4,
              "t": 300.0, "seed": 23.0}
    NST = 2

    @staticmethod
    def geo(p, d):
        return 0.5 * (1.0 - d / math.sqrt(d * d + p["a"] * p["a"]))

    @classmethod
    def read(cls, p, s, x, k):
        n = p["nb"] + (p["A"] * p["yld"] * cls.geo(p, x) * p["eint"] if s == 1 else 0.0)
        m = n / (1.0 + n * p["tau"])
        c = _cnt(p, k, m * p["t"])
        return {"y": c / p["t"], "N": c, "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        return [0.0] if s == 0 else [0.02, 0.03, 0.04, 0.05, 0.06]

    @classmethod
    def fit(cls, rows, p):
        b = _stage(rows, 0)
        if not b:
            return 0.0
        mb = float(b[0]["y"])
        nb = mb / (1.0 - mb * p["tau"])
        tot, k = 0.0, 0
        for r in _stage(rows, 1):
            d, m = float(r["x"]), float(r["y"])
            if d <= 0:
                continue
            n = m / (1.0 - m * p["tau"]) - nb
            tot += n / (p["A"] * p["yld"] * cls.geo(p, d))
            k += 1
        return tot / k if k else 0.0


# ============================================================================================ beta absorption, Feather
class BetaFeather(_Sweep):
    """A beta source of up to two groups (end points E1 > E2, fractions f1, f2) counted through aluminium of areal
    density x (g/cm^2). Each group falls as exp(-mu x) up to its range R (Katz-Penfold) and then stops; behind the
    longest range only the bremsstrahlung tail `brem` and the background `bg` remain. mu = 17 E^-1.14 cm^2/g.
    Stage 0: background; stage 1: foils. The range is turned into an end point with Feather's rule
    R = 0.543 E - 0.160 g/cm^2."""

    PARAMS = {"x": 0.0, "s": 0.0, "E1": 2.2785, "f1": 0.5, "E2": 0.5459, "f2": 0.5, "N0": 600.0, "brem": 0.6,
              "bg": 0.5, "tau": 2.5e-4, "t": 200.0, "tl": 1800.0, "seed": 31.0}
    NST = 2

    @staticmethod
    def rkp(E):
        return 0.412 * math.pow(E, 1.265 - 0.0954 * math.log(E))

    @staticmethod
    def mu(E):
        return 17.0 * math.pow(E, -1.14)

    @classmethod
    def beta(cls, p, x):
        r = 0.0
        for E, f in ((p["E1"], p["f1"]), (p["E2"], p["f2"])):
            if f > 0 and x < cls.rkp(E):
                r += f * math.exp(-cls.mu(E) * x)
        return p["N0"] * r

    @classmethod
    def ctime(cls, p, x):
        return p["tl"] if x > 0.6 * cls.rkp(p["E1"]) else p["t"]

    @classmethod
    def read(cls, p, s, x, k):
        n = p["bg"] + ((p["brem"] + cls.beta(p, x)) if s == 1 else 0.0)
        m = n / (1.0 + n * p["tau"])
        tt = p["tl"] if s == 0 else cls.ctime(p, x)
        c = _cnt(p, k, m * tt)
        return {"y": c / tt, "N": c, "T": tt}

    @classmethod
    def coarse(cls, p):
        return [0.0, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0]

    @classmethod
    def plan(cls, p):
        """Background; the coarse foil box up to the first foil with no betas left; then the foil 2.0 g/cm^2 (the tail);
        then stacking 5 mg/cm^2 foils, halving the gap between the last foil with betas and the first without."""
        out = [[0, 0.0]]
        rows = [cls.read(p, 0, 0.0, 0)]
        rows[0].update({"s": 0, "x": 0.0})
        k = 1
        for x in cls.coarse(p):
            r = cls.read(p, 1, x, k)
            k += 1
            r.update({"s": 1, "x": x})
            rows.append(r)
            out.append([1, x])
        lo, hi = cls.bracket(rows, p)
        while lo is not None and hi - lo > 0.0075:
            mid = math.floor((lo + hi) / 2.0 / 0.005 + 0.5) * 0.005
            if mid <= lo or mid >= hi:
                break
            r = cls.read(p, 1, mid, k)
            k += 1
            r.update({"s": 1, "x": mid})
            rows.append(r)
            out.append([1, mid])
            lo, hi = cls.bracket(rows, p)
        return out

    @classmethod
    def bracket(cls, rows, p):
        """[last foil whose counts are clearly (3 sigma) above the tail, first foil after it that is not]."""
        bg = _stage(rows, 0)
        foils = _stage(rows, 1)
        tail = None
        for r in foils:
            if abs(float(r["x"]) - 2.0) < 1e-9:
                tail = r
        if not bg or tail is None:
            return None, None
        mt = float(tail["y"])
        st = math.sqrt(max(float(tail["N"]), 1.0)) / float(tail["T"])
        pts = sorted(([float(r["x"]), float(r["y"]), math.sqrt(max(float(r["N"]), 1.0)) / float(r["T"])] for r in foils),
                     key=lambda q: q[0])
        last = -1
        for i, q in enumerate(pts):
            if q[1] - mt > 3.0 * math.sqrt(q[2] * q[2] + st * st):
                last = i
        if last < 0 or last >= len(pts) - 1:
            return None, None
        return pts[last][0], pts[last + 1][0]

    @classmethod
    def fit(cls, rows, p):
        lo, hi = cls.bracket(rows, p)
        if lo is None:
            return 0.0
        return (lo + hi) / 2.0

    @staticmethod
    def feather(R):
        return (R + 0.160) / 0.543


# ============================================================================================ K-40 with a UX2 standard
class K40Std(_Sweep):
    """Absolute disintegration rate of K-40. A tray under an end-window GM tube is counted empty (stage 0, the
    background), filled with a UX2 (Pa-234m) beta standard of certified emission rate Bstd (stage 1), and filled with
    a weighed potassium salt (stage 2). With the same tray, layer and shelf the counter sees the same fraction eps of
    both; eps from the standard then gives the beta emission rate of the K-40, its specific activity and the PARTIAL
    beta-decay half-life T_beta = ln2 N(K-40) / A_beta."""

    PARAMS = {"x": 0.0, "s": 0.0, "m": 0.1, "fK": 0.52445, "MK": 39.0983, "ab": 1.17e-4, "T12": 1.248e9, "br": 0.8928,
              "Bstd": 1000.0, "eps": 0.002, "bg": 0.45, "tau": 2.5e-4, "t": 3600.0, "seed": 41.0}
    NST = 3

    @staticmethod
    def nk(p):
        return p["m"] * 1000.0 * p["fK"] / p["MK"] * NA * p["ab"]

    @classmethod
    def abeta(cls, p):
        return cls.nk(p) * LN2 / (p["T12"] * YEAR) * p["br"]

    @classmethod
    def read(cls, p, s, x, k):
        n = p["bg"] + (p["Bstd"] * p["eps"] if s == 1 else 0.0) + (cls.abeta(p) * p["eps"] if s == 2 else 0.0)
        m = n / (1.0 + n * p["tau"])
        c = _cnt(p, k, m * p["t"])
        return {"y": c / p["t"], "N": c, "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        return [1.0, 2.0] if s == 0 else [1.0, 2.0, 3.0]

    @classmethod
    def fit(cls, rows, p):
        def mean(s):
            v = _stage(rows, s)
            if not v:
                return None
            tot = 0.0
            for r in v:
                m = float(r["y"])
                tot += m / (1.0 - m * p["tau"])
            return tot / len(v)
        b, sd, kk = mean(0), mean(1), mean(2)
        if b is None or sd is None or kk is None or sd - b <= 0 or kk - b <= 0:
            return 0.0
        eps = (sd - b) / p["Bstd"]
        ab = (kk - b) / eps
        return cls.nk(p) * LN2 / ab / YEAR


# ============================================================================================ spark counter, alpha range
class SparkAlpha(_Sweep):
    """An Am-241 alpha source facing the wire grid of a spark counter across a gap of air d (cm). Stage 0: the
    counting plateau against the high voltage V at d = 1 cm. Stage 1: count against d at the operating voltage. The
    alphas reach the grid while d is below their range; range straggling (relative width sig) smooths the end:
    rate = N0 (1/d^2) erfc((d - R) / (sqrt2 sig R)) / 2. Geiger's rule gives the mean range R = 0.318 E^1.5 cm."""

    PARAMS = {"x": 0.0, "s": 0.0, "E": 5.4857, "N0": 60.0, "sig": 0.015, "Vth": 3200.0, "Vd": 4900.0, "V": 4100.0,
              "bg": 0.02, "t": 120.0, "seed": 53.0}
    NST = 2

    @staticmethod
    def rg(p):
        return 0.318 * math.pow(p["E"], 1.5)

    @staticmethod
    def plateau(p, V):
        if V <= p["Vth"]:
            return 0.0
        f = min(1.0, (V - p["Vth"]) / 250.0)
        if V > p["Vd"]:
            f *= 1.0 + ((V - p["Vd"]) / 120.0) ** 2
        return f

    @classmethod
    def alpha(cls, p, d):
        R = cls.rg(p)
        return p["N0"] / (d * d) * 0.5 * _erfc((d - R) / (math.sqrt(2.0) * p["sig"] * R))

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            n = cls.alpha(p, 1.0) * cls.plateau(p, x) + p["bg"]
        else:
            n = cls.alpha(p, x) * cls.plateau(p, p["V"]) + p["bg"]
        c = _cnt(p, k, n * p["t"])
        return {"y": c / p["t"], "N": c, "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return _rng(3000.0, 5100.0, 100.0)
        return [1.0, 1.5, 2.0, 2.5, 3.0, 3.5] + _rng(3.6, 4.6, 0.1) + [5.0]

    @classmethod
    def fit(cls, rows, p):
        """Mean range: where the solid-angle-corrected count (rate - bg) d^2 falls to half its value near the source."""
        st = _stage(rows, 1)
        if len(st) < 4:
            return 0.0
        pts = sorted(([float(r["x"]), (float(r["y"]) - p["bg"]) * float(r["x"]) * float(r["x"])] for r in st),
                     key=lambda q: q[0])
        top = 0.0
        for q in pts[:3]:
            top += q[1]
        top /= min(3, len(pts))
        v = _half(pts, top / 2.0, 1, 0)
        return v if v is not None else 0.0


# ============================================================================================ proportional counter
class PropCounter(_Sweep):
    """An argon-methane proportional counter and a multichannel analyser. The gas gain grows exponentially with the
    voltage, M = M0 exp(a (V - V0)), so the peak channel is kc E M / M0. Stage 0: peak channel against V. Stage 1: the
    spectrum at the operating voltage Vop, channel by channel: the full-energy line E (Gaussian, FWHM/E =
    2.355 sqrt((F + b) W / E)), the argon escape line E - 2.957 keV when E > 3.2 keV, and for Am-241 the neptunium L
    X-rays."""

    PARAMS = {"x": 0.0, "s": 0.0, "E": 5.895, "Vop": 1700.0, "V0": 1700.0, "a": 0.009, "kc": 33.9, "W": 0.0262,
              "F": 0.17, "b": 0.5, "esc": 0.12, "L1": 0.0, "L2": 0.0, "Ntot": 3.0e6, "seed": 61.0}
    NST = 2

    @classmethod
    def res(cls, p, E):
        return 2.355 * math.sqrt((p["F"] + p["b"]) * p["W"] / E)

    @classmethod
    def chan(cls, p, E, V):
        return p["kc"] * E * math.exp(p["a"] * (V - p["V0"]))

    @classmethod
    def line(cls, p, E, ch, V):
        c = cls.chan(p, E, V)
        sg = cls.res(p, E) * c / 2.355
        return math.exp(-0.5 * ((ch - c) / sg) ** 2) / (sg * math.sqrt(2.0 * PI))

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            return {"y": _q(cls.chan(p, p["E"], x), 0.1)}
        V = p["Vop"]
        d = cls.line(p, p["E"], x, V)
        if p["E"] > 3.2:
            d += p["esc"] * cls.line(p, p["E"] - 2.957, x, V)
        if p["L1"] > 0 or p["L2"] > 0:
            d += p["L1"] * cls.line(p, 13.95, x, V) + p["L2"] * cls.line(p, 17.61, x, V)
        return {"y": _cnt(p, k, p["Ntot"] * d)}

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return _rng(p["Vop"] - 150.0, p["Vop"] + 150.0, 25.0)
        c = cls.chan(p, p["E"], p["Vop"])
        w = cls.res(p, p["E"]) * c
        lo = math.floor((c - 1.6 * w) / 2.0) * 2.0
        hi = math.floor((c + 1.6 * w) / 2.0) * 2.0
        return _rng(max(lo, 2.0), hi, 2.0)

    @classmethod
    def fit(cls, rows, p):
        """Energy resolution FWHM / centroid (in %) of the full-energy line."""
        st = _stage(rows, 1)
        if len(st) < 5:
            return 0.0
        pts = _sorted(st)
        pk = _peakwidth(pts, pts[0][0], pts[-1][0], 0.0)
        if pk is None or pk[0] <= 0:
            return 0.0
        return 100.0 * pk[1] / pk[0]


# ============================================================================================ beta spectrum, Kurie plot
class Kurie(_Sweep):
    """Beta spectrum of up to two groups plus a conversion-electron line, read two ways. Method m = 0: an anthracene
    scintillation spectrometer, channels of fixed width dT (keV) set at the kinetic energy x (keV); method m = 1: a
    magnetic spectrometer at coil current x (A), momentum p = kI x (in m c) with a window dp/p = Rm. The allowed shape
    N(T) dT = C F(Z, W) p W (W0 - W)^2 dT, with the non-relativistic Fermi function F = 2 pi eta / (1 - exp(-2 pi eta)),
    eta = Z alpha W / p. The detector response is idealised (no resolution smearing)."""

    PARAMS = {"x": 0.0, "s": 0.0, "m": 0.0, "T1": 514.0, "Z1": 56.0, "f1": 1.0, "T2": 1175.6, "Z2": 56.0, "f2": 0.0,
              "Tc": 624.2, "fc": 0.08, "wc": 12.0, "dT": 10.0, "kI": 0.5, "Rm": 0.02, "Ntot": 4.0e6, "seed": 71.0}

    @staticmethod
    def fermi(Z, W):
        pp = math.sqrt(W * W - 1.0)
        eta = Z * ALPHA * W / pp
        return 2.0 * PI * eta / (1.0 - math.exp(-2.0 * PI * eta))

    @classmethod
    def shape(cls, Z, T0, T):
        if T <= 0 or T >= T0:
            return 0.0
        W = 1.0 + T / ME_KEV
        W0 = 1.0 + T0 / ME_KEV
        return cls.fermi(Z, W) * math.sqrt(W * W - 1.0) * W * (W0 - W) ** 2

    @classmethod
    def norm(cls, Z, T0):
        n = 400
        h = T0 / n
        tot = 0.0
        for i in range(n + 1):
            T = h * i
            w = 1.0 if i in (0, n) else (4.0 if i % 2 == 1 else 2.0)
            tot += w * cls.shape(Z, T0, T)
        return tot * h / 3.0

    @classmethod
    def dens(cls, p, T):
        """Electrons per keV per decay at kinetic energy T (keV)."""
        d = 0.0
        if p["f1"] > 0:
            d += p["f1"] * cls.shape(p["Z1"], p["T1"], T) / cls.norm(p["Z1"], p["T1"])
        if p["f2"] > 0:
            d += p["f2"] * cls.shape(p["Z2"], p["T2"], T) / cls.norm(p["Z2"], p["T2"])
        if p["fc"] > 0:
            d += p["fc"] * math.exp(-0.5 * ((T - p["Tc"]) / p["wc"]) ** 2) / (p["wc"] * math.sqrt(2.0 * PI))
        return d

    @staticmethod
    def kin(p, x):
        """The kinetic energy (keV) the spectrometer is set to."""
        if p["m"] < 0.5:
            return x
        pp = p["kI"] * x
        return (math.sqrt(pp * pp + 1.0) - 1.0) * ME_KEV

    @classmethod
    def read(cls, p, s, x, k):
        T = cls.kin(p, x)
        if T <= 0:
            return {"y": 0.0}
        if p["m"] < 0.5:
            mean = p["Ntot"] * cls.dens(p, T) * p["dT"]
        else:
            pp = p["kI"] * x
            W = 1.0 + T / ME_KEV
            mean = p["Ntot"] * cls.dens(p, T) * (pp / W) * ME_KEV * p["Rm"] * pp
        return {"y": _cnt(p, k, mean)}

    @classmethod
    def xs(cls, p, s):
        Tm = max(p["T1"], p["T2"] if p["f2"] > 0 else 0.0, p["Tc"] if p["fc"] > 0 else 0.0)
        if p["m"] < 0.5:
            return _rng(p["dT"], 1.15 * Tm, p["dT"])
        pmax = math.sqrt((1.0 + 1.15 * Tm / ME_KEV) ** 2 - 1.0)
        return _rng(0.05, pmax / p["kI"], 0.05)

    @classmethod
    def kurie_pts(cls, rows, p):
        """[W, K] for every row: K = sqrt(N / (p W F)) (scintillation) or sqrt(N / (F p^3)) (magnetic)."""
        out = []
        for r in rows:
            T = cls.kin(p, float(r["x"]))
            n = float(r["y"])
            if T <= 0 or n <= 0:
                continue
            W = 1.0 + T / ME_KEV
            pp = math.sqrt(W * W - 1.0)
            F = cls.fermi(p["Z1"], W)
            K = math.sqrt(n / (pp * W * F)) if p["m"] < 0.5 else math.sqrt(n / (F * pp * pp * pp))
            out.append([W, K, T, n])
        return out

    @classmethod
    def window(cls, rows, p):
        """The end of the continuum: past the spectrum's maximum (sought below 60 % of the highest energy that still
        counts, so a conversion line cannot be taken for it), the first setting where the count falls below 3 % of
        that maximum. The Kurie line is fitted between 35 % and 85 % of that energy."""
        pts = sorted(([cls.kin(p, float(r["x"])), float(r["y"])] for r in rows), key=lambda q: q[0])
        if len(pts) < 6:
            return None
        tlast = 0.0
        for q in pts:
            if q[1] > 0:
                tlast = q[0]
        best, ib = -1.0, -1
        for i, q in enumerate(pts):
            if q[0] <= 0.6 * tlast and q[1] > best:
                best, ib = q[1], i
        if ib < 0:
            return None
        tend = None
        for q in pts[ib:]:
            if q[1] < 0.03 * best:
                tend = q[0]
                break
        return tend

    @classmethod
    def fit(cls, rows, p):
        st = _stage(rows, 0)
        tend = cls.window(st, p)
        if not tend:
            return 0.0
        pts = [[q[0], q[1]] for q in cls.kurie_pts(st, p) if 0.35 * tend <= q[2] <= 0.85 * tend]
        f = _linfit(pts)
        if not f or f[0] >= 0:
            return 0.0
        W0 = -f[1] / f[0]
        return (W0 - 1.0) * ME_KEV


# ============================================================================================ gamma-gamma angular correlation
class AngCorr(_Sweep):
    """Co-60 cascade 4+ -> 2+ -> 0+: two scintillation counters at an angle theta in prompt coincidence.
    C(theta) = C0 W(theta) + chance, W = 1 + a2 cos^2 + a4 cos^4 (point detectors, no finite-solid-angle attenuation).
    Stage 0: the chance rate with a delay in one arm; stage 1: prompt coincidences from 90 to 180 degrees."""

    PARAMS = {"x": 90.0, "s": 0.0, "a2": 0.125, "a4": 0.0416667, "C0": 1000.0, "ch": 5.0, "t": 50000.0, "seed": 83.0}
    NST = 2

    @classmethod
    def read(cls, p, s, x, k):
        c = math.cos(x * PI / 180.0)
        n = p["ch"] + (p["C0"] * (1.0 + p["a2"] * c * c + p["a4"] * c * c * c * c) if s == 1 else 0.0)
        cnt = _cnt(p, k, n * p["t"])
        return {"y": cnt / p["t"], "N": cnt, "T": p["t"]}

    @classmethod
    def xs(cls, p, s):
        return [90.0] if s == 0 else _rng(90.0, 180.0, 15.0)

    @classmethod
    def fit(cls, rows, p):
        """Least squares of W(theta)/W(90) - 1 = a2 cos^2 + a4 cos^4 on the chance-corrected rates: returns a2."""
        ch = _stage(rows, 0)
        pr = _stage(rows, 1)
        if not ch or len(pr) < 3:
            return 0.0
        c0 = float(ch[0]["y"])
        w90 = None
        for r in pr:
            if abs(float(r["x"]) - 90.0) < 1e-6:
                w90 = float(r["y"]) - c0
        if not w90 or w90 <= 0:
            return 0.0
        s11 = s12 = s22 = s1y = s2y = 0.0
        for r in pr:
            c = math.cos(float(r["x"]) * PI / 180.0)
            u, v = c * c, c * c * c * c
            y = (float(r["y"]) - c0) / w90 - 1.0
            s11 += u * u
            s12 += u * v
            s22 += v * v
            s1y += u * y
            s2y += v * y
        den = s11 * s22 - s12 * s12
        if abs(den) < 1e-300:
            return 0.0
        return (s1y * s22 - s2y * s12) / den


# ============================================================================================ Hall effect against temperature
class HallT(_Sweep):
    """A lightly doped germanium slab (thickness d, current I, field B) from 77 K to 420 K. Carriers: n p = ni^2 with
    ni = ni300 (T/300)^1.5 exp(-(Eg0 / 2k)(1/T - 1/300)) (a gap Eg(T) = Eg0 - gamma T, linear, folded into ni300), the
    impurities fully ionised; mobilities mu = mu300 (T/300)^-1.5. R_H = (p mu_p^2 - n mu_n^2) / (e (p mu_p + n mu_n)^2).
    Readings: the Hall voltage V_H = R_H I B / d (mV) and the voltage along the slab V_s = I L / (sigma w d) (mV)."""

    PARAMS = {"x": 300.0, "s": 0.0, "Eg0": 0.782, "ni300": 2.33e19, "N": 2.0e19, "typ": 1.0, "mun": 0.39, "mup": 0.19,
              "I": 1.0e-3, "B": 0.3, "d": 5.0e-4, "w": 5.0e-3, "L": 1.0e-2}

    @staticmethod
    def carriers(p, T):
        ni = p["ni300"] * math.pow(T / 300.0, 1.5) * math.exp(-p["Eg0"] / (2.0 * KB_EV) * (1.0 / T - 1.0 / 300.0))
        maj = p["N"] / 2.0 + math.sqrt(p["N"] * p["N"] / 4.0 + ni * ni)
        mino = ni * ni / maj
        return (mino, maj) if p["typ"] > 0 else (maj, mino)       # (n, p)

    @classmethod
    def rh_sig(cls, p, T):
        n, h = cls.carriers(p, T)
        f = math.pow(T / 300.0, -1.5)
        un, up = p["mun"] * f, p["mup"] * f
        sig = QE * (n * un + h * up)
        rh = (h * up * up - n * un * un) / (QE * (h * up + n * un) ** 2)
        return rh, sig

    @classmethod
    def read(cls, p, s, x, k):
        rh, sig = cls.rh_sig(p, x)
        vh = rh * p["I"] * p["B"] / p["d"] * 1000.0
        vs = p["I"] * p["L"] / (sig * p["w"] * p["d"]) * 1000.0
        return {"y": _q(vh, 0.001), "y2": _q(vs, 0.01)}

    @classmethod
    def xs(cls, p, s):
        return [77.0, 100.0, 150.0, 200.0, 250.0, 300.0, 320.0, 340.0, 360.0, 380.0, 390.0, 400.0, 410.0, 420.0]

    @classmethod
    def fit(cls, rows, p):
        """Band gap from the intrinsic region: slope of ln(|R_H| T^1.5) against 1/T is Eg0 / 2k (T >= 375 K)."""
        pts = []
        for r in _stage(rows, 0):
            T = float(r["x"])
            rh = abs(float(r["y"])) / 1000.0 * p["d"] / (p["I"] * p["B"])
            if T >= 375.0 and rh > 0:
                pts.append([1.0 / T, math.log(rh * math.pow(T, 1.5))])
        f = _linfit(pts)
        return 2.0 * KB_EV * f[0] if f else 0.0


# ============================================================================================ two-probe conductivity
class TwoProbe(_Sweep):
    """A bar (length L, cross-section A) between two probes in a furnace; current I, voltmeter across the same probes,
    so each contact adds Rc. Material mat = 0: intrinsic germanium, sigma = e ni (mu_n + mu_p) with the same ni and
    T^-1.5 mobilities as HallT, so sigma ~ exp(-Eg0 / 2kT). mat = 1: graphite rod, rho(T) = rho300 (1 + ag (T - 300))."""

    PARAMS = {"x": 300.0, "s": 0.0, "mat": 0.0, "Eg0": 0.782, "ni300": 2.33e19, "mun": 0.39, "mup": 0.19,
              "rhog": 1.0e-5, "ag": -4.0e-4, "L": 1.0e-2, "A": 1.0e-6, "Rc": 0.3, "I": 1.0e-4}

    @staticmethod
    def sigma(p, T):
        if p["mat"] > 0.5:
            return 1.0 / (p["rhog"] * (1.0 + p["ag"] * (T - 300.0)))
        ni = p["ni300"] * math.pow(T / 300.0, 1.5) * math.exp(-p["Eg0"] / (2.0 * KB_EV) * (1.0 / T - 1.0 / 300.0))
        f = math.pow(T / 300.0, -1.5)
        return QE * ni * (p["mun"] + p["mup"]) * f

    @classmethod
    def read(cls, p, s, x, k):
        R = p["L"] / (cls.sigma(p, x) * p["A"]) + 2.0 * p["Rc"]
        v = p["I"] * R
        return {"y": _q(v * 1000.0, 0.001)}       # mV

    @classmethod
    def xs(cls, p, s):
        return _rng(300.0, 420.0, 10.0)

    @classmethod
    def fit(cls, rows, p):
        st = _stage(rows, 0)
        if p["mat"] > 0.5:
            for r in st:
                if abs(float(r["x"]) - 300.0) < 1e-6 and float(r["y"]) > 0:
                    R = float(r["y"]) / 1000.0 / p["I"]
                    return p["L"] / (R * p["A"])
            return 0.0
        pts = []
        for r in st:
            if float(r["y"]) > 0:
                R = float(r["y"]) / 1000.0 / p["I"]
                pts.append([1.0 / float(r["x"]), math.log(p["L"] / (R * p["A"]))])
        f = _linfit(pts)
        return -2.0 * KB_EV * f[0] if f else 0.0


# ============================================================================================ diode ideality + band gap
class DiodeIV(_Sweep):
    """A p-n junction in a stirred oil bath at T (K), driven at two fixed currents I1 and I2 from a current source.
    I = I0 (exp(V / (n Vt)) - 1), I0 = C T^3 exp(-Eg0 / kT) with C fixed by I0 at 300 K; series resistance neglected.
    Reading: the junction voltages V1, V2 (mV, 0.1 mV)."""

    PARAMS = {"x": 300.0, "s": 0.0, "Eg0": 1.206, "nid": 1.8, "I300": 1.0e-11, "I1": 1.0e-4, "I2": 1.0e-3}

    @staticmethod
    def i0(p, T):
        c = p["I300"] / (300.0 ** 3 * math.exp(-p["Eg0"] / (KB_EV * 300.0)))
        return c * T * T * T * math.exp(-p["Eg0"] / (KB_EV * T))

    @classmethod
    def volt(cls, p, T, I):
        return p["nid"] * KB_EV * T * math.log(I / cls.i0(p, T) + 1.0)

    @classmethod
    def read(cls, p, s, x, k):
        return {"y": _q(cls.volt(p, x, p["I1"]) * 1000.0, 0.1), "y2": _q(cls.volt(p, x, p["I2"]) * 1000.0, 0.1)}

    @classmethod
    def xs(cls, p, s):
        return _rng(300.0, 380.0, 10.0)

    @staticmethod
    def ideal(p, r):
        T = float(r["x"])
        vt = KB_EV * T
        return (float(r["y2"]) - float(r["y"])) / 1000.0 / (vt * math.log(p["I2"] / p["I1"]))

    @classmethod
    def fit(cls, rows, p):
        pts = []
        for r in _stage(rows, 0):
            T = float(r["x"])
            n = cls.ideal(p, r)
            if n <= 0:
                continue
            i0 = p["I1"] / (math.exp(float(r["y"]) / 1000.0 / (n * KB_EV * T)) - 1.0)
            pts.append([1.0 / T, math.log(i0 / (T * T * T))])
        f = _linfit(pts)
        return -KB_EV * f[0] if f else 0.0


# ============================================================================================ photoconductivity
class PhotoCond(_Sweep):
    """A photoconductive cell (CdS or a thin film) under bias. Stage 0: photocurrent against the lamp distance d (cm),
    I = Ip (d0 / d)^(2 gam) + Id (illumination ~ 1/d^2, a sub-linear response of exponent gam). Stage 1: relative
    spectral response through a monochromator at constant photon flux, R = erfc((Eg - E) / (sqrt2 sw)) / 2,
    E = hc / lambda (an absorption edge broadened by sw). Stage 2: rise after the shutter opens,
    I = Ion (1 - exp(-t/tau)); stage 3: decay after it closes, I = Ion exp(-t/tau)."""

    PARAMS = {"x": 20.0, "s": 0.0, "Eg": 2.42, "sw": 0.03, "gam": 0.8, "Ip": 80.0, "d0": 20.0, "Id": 0.05, "Im": 40.0,
              "Ion": 40.0, "tau": 0.05, "l1": 400.0, "l2": 700.0}
    NST = 4

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            v = p["Ip"] * math.pow(p["d0"] / x, 2.0 * p["gam"]) + p["Id"]
        elif s == 1:
            E = HC_EVNM / x
            v = p["Im"] * 0.5 * _erfc((p["Eg"] - E) / (math.sqrt(2.0) * p["sw"])) + p["Id"]
        elif s == 2:
            v = p["Ion"] * (1.0 - math.exp(-x / p["tau"])) + p["Id"]
        else:
            v = p["Ion"] * math.exp(-x / p["tau"]) + p["Id"]
        return {"y": _q(v, 0.01)}            # microamperes

    @classmethod
    def xs(cls, p, s):
        if s == 0:
            return [10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]
        if s == 1:
            return _rng(p["l1"], p["l2"], 5.0)
        return _rng(0.0, 0.25, 0.025)

    @classmethod
    def fit(cls, rows, p):
        """Band gap from the long-wavelength cut-off: where the response falls to half of its plateau."""
        st = _stage(rows, 1)
        if len(st) < 5:
            return 0.0
        pts = _sorted(st)
        dark = min(q[1] for q in pts)
        top = max(q[1] for q in pts)
        ib = 0
        for i, q in enumerate(pts):
            if q[1] == top:
                ib = i
        lc = _half(pts, dark + (top - dark) / 2.0, 1, ib)
        return HC_EVNM / lc if lc else 0.0


# ============================================================================================ AC susceptibility of YBCO
class ACSusc(_Sweep):
    """A sintered YBCO pellet inside the secondary of a mutual-inductance coil set, the primary driven at fixed
    current, read by a lock-in. The in-phase signal follows the shielded fraction f = erfc((T - Tc) / (sqrt2 dT)) / 2,
    V' = -V0 f (microvolts) on top of the empty-coil offset; the loss peak V'' = Vl exp(-((T - Tc)/dT)^2 / 2)."""

    PARAMS = {"x": 100.0, "s": 0.0, "Tc": 92.0, "dT": 1.2, "V0": 50.0, "Vl": 6.0, "Voff": 2.0}

    @classmethod
    def read(cls, p, s, x, k):
        f = 0.5 * _erfc((x - p["Tc"]) / (math.sqrt(2.0) * p["dT"]))
        return {"y": _q(p["Voff"] - p["V0"] * f, 0.01),
                "y2": _q(p["Vl"] * math.exp(-0.5 * ((x - p["Tc"]) / p["dT"]) ** 2), 0.01)}

    @classmethod
    def xs(cls, p, s):
        return [80.0, 84.0, 86.0, 88.0] + _rng(89.0, 96.0, 0.5) + [98.0, 100.0, 105.0]

    @classmethod
    def fit(cls, rows, p):
        """Tc as the midpoint of the diamagnetic step (in-phase signal half-way between full shielding and normal)."""
        pts = _sorted(_stage(rows, 0))
        if len(pts) < 5:
            return 0.0
        lo, hi = pts[0][1], pts[-1][1]
        v = _half(pts, (lo + hi) / 2.0, 1, 0)
        return v if v is not None else 0.0


# ============================================================================================ LC lattice
class LCLattice(_Sweep):
    """A ladder of series inductors L and shunt capacitors: monatomic (all C, d = 0) or diatomic (C1, C2 alternating,
    d = 1). The phase shift per unit cell phi is read with the CRO (Lissajous figure). Monatomic: sin(phi/2) = f / fc,
    fc = 1 / (pi sqrt(L C)). Diatomic acoustic branch: sin^2(phi/2) = C1 C2 L w^2 (2 s - w^2 L) / 4, s = 1/C1 + 1/C2,
    whose top is fa = sqrt(2 / (L C1)) / 2 pi (C1 > C2)."""

    PARAMS = {"x": 1000.0, "s": 0.0, "d": 0.0, "L": 1.0e-2, "C": 1.0e-7, "C1": 1.0e-7, "C2": 4.7e-8}

    @classmethod
    def phase(cls, p, f):
        w = 2.0 * PI * f
        if p["d"] < 0.5:
            r = f * PI * math.sqrt(p["L"] * p["C"])
            r2 = r * r
        else:
            s = 1.0 / p["C1"] + 1.0 / p["C2"]
            r2 = p["C1"] * p["C2"] * p["L"] * w * w * (2.0 * s - w * w * p["L"]) / 4.0
        if r2 >= 1.0:
            return 180.0
        if r2 <= 0:
            return 0.0
        return 2.0 * math.asin(math.sqrt(r2)) * 180.0 / PI

    @classmethod
    def read(cls, p, s, x, k):
        return {"y": _q(cls.phase(p, x), 0.5)}

    @classmethod
    def xs(cls, p, s):
        if p["d"] < 0.5:
            fc = 1.0 / (PI * math.sqrt(p["L"] * p["C"]))
        else:
            fc = math.sqrt(2.0 / (p["L"] * p["C1"])) / (2.0 * PI)
        out = []
        for i in range(1, 13):
            out.append(math.floor(fc * 0.075 * i / 50.0 + 0.5) * 50.0)
        if p["d"] >= 0.5:
            for m in (1.05, 1.2, 1.35, 1.5, 1.55, 1.6, 1.65, 1.7, 1.75):
                out.append(math.floor(fc * m / 50.0 + 0.5) * 50.0)
        return out

    @staticmethod
    def acoustic(rows):
        """[f, phase] of the readings below the first frequency where the phase reaches 180 degrees (the acoustic
        branch; past it lie the gap and, for the diatomic chain, the optical branch)."""
        pts = sorted(([float(r["x"]), float(r["y"])] for r in _stage(rows, 0)), key=lambda q: q[0])
        out = []
        for q in pts:
            if q[1] >= 179.9:
                break
            out.append(q)
        return out

    @classmethod
    def fit(cls, rows, p):
        pts = []
        for q in cls.acoustic(rows):
            ph = q[1]
            if 5.0 < ph < 170.0:
                f = q[0]
                sn = math.sin(ph / 2.0 * PI / 180.0)
                if p["d"] < 0.5:
                    pts.append([sn, f])
                else:
                    w2 = (2.0 * PI * f) ** 2
                    pts.append([w2, sn * sn / w2])
        if len(pts) < 3:
            return 0.0
        if p["d"] < 0.5:
            sxy = sxx = 0.0
            for q in pts:
                sxy += q[0] * q[1]
                sxx += q[0] * q[0]
            return sxy / sxx
        f = _linfit(pts)
        if not f or f[0] >= 0 or f[1] <= 0:
            return 0.0
        A, B = f[1], -f[0]
        disc = A * A - 4.0 * B
        if disc < 0:
            return 0.0
        w2 = (A - math.sqrt(disc)) / (2.0 * B)
        return math.sqrt(w2) / (2.0 * PI)


# ============================================================================================ pulse echo in solids
class PulseEcho(_Sweep):
    """A longitudinal-wave probe on a block of thickness d: the n-th back-wall echo arrives at t_n = 2 n d / v. The CRO
    time base is read to 0.01 microsecond."""

    PARAMS = {"x": 1.0, "s": 0.0, "v": 6320.0, "d": 0.05, "rho": 2700.0, "att": 4.0}

    @classmethod
    def read(cls, p, s, x, k):
        return {"y": _q(2.0 * x * p["d"] / p["v"] * 1e6, 0.01),
                "y2": _q(100.0 * math.exp(-p["att"] * 2.0 * x * p["d"]), 0.1)}

    @classmethod
    def xs(cls, p, s):
        return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    @classmethod
    def fit(cls, rows, p):
        pts = [[float(r["x"]), float(r["y"]) * 1e-6] for r in _stage(rows, 0)]
        f = _linfit(pts)
        return 2.0 * p["d"] / f[0] if f and f[0] > 0 else 0.0


# ============================================================================================ velocity of sound, CRO phase
class SoundCRO(_Sweep):
    """A loudspeaker at frequency f at one end of a tube, a microphone on a slide: the CRO shows the speaker signal
    against the microphone's (a Lissajous figure). The ellipse closes to a straight line each time the microphone
    moves half a wavelength; v = 331.3 sqrt(1 + t / 273.15) m/s in dry air at t degrees C."""

    PARAMS = {"x": 0.0, "s": 0.0, "f": 3000.0, "tc": 27.0, "x0": 62.0}

    @staticmethod
    def vel(p):
        return 331.3 * math.sqrt(1.0 + p["tc"] / 273.15)

    @classmethod
    def read(cls, p, s, x, k):
        lam = cls.vel(p) / p["f"] * 1000.0
        return {"y": _q(p["x0"] + x * lam / 2.0, 0.5)}      # mm on the slide

    @classmethod
    def xs(cls, p, s):
        return [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]

    @classmethod
    def fit(cls, rows, p):
        pts = [[float(r["x"]), float(r["y"])] for r in _stage(rows, 0)]
        f = _linfit(pts)
        return 2.0 * f[0] / 1000.0 * p["f"] if f else 0.0


# ============================================================================================ Lecher wire
class Lecher(_Sweep):
    """A Lecher line driven at frequency f. A sliding shorting bar finds the current nodes, half a wavelength apart:
    in air (stage 0) lambda0 = c / f; with the wires immersed in a liquid (stage 1) lambda = lambda0 / sqrt(eps)."""

    PARAMS = {"x": 0.0, "s": 0.0, "f": 6.0e8, "eps": 2.2, "x0": 8.0}
    NST = 2

    @classmethod
    def read(cls, p, s, x, k):
        lam = C0 / p["f"] * 100.0
        if s == 1:
            lam /= math.sqrt(p["eps"])
        return {"y": _q(p["x0"] + x * lam / 2.0, 0.1)}      # cm along the wires

    @classmethod
    def xs(cls, p, s):
        lam = C0 / p["f"] * 100.0
        if s == 1:
            lam /= math.sqrt(p["eps"])
        n = int(math.floor((120.0 - p["x0"]) / (lam / 2.0)))
        return [float(i) for i in range(min(n, 9) + 1)]

    @classmethod
    def lam_of(cls, rows, s):
        pts = [[float(r["x"]), float(r["y"])] for r in _stage(rows, s)]
        f = _linfit(pts)
        return 2.0 * f[0] if f else 0.0

    @classmethod
    def fit(cls, rows, p):
        a, b = cls.lam_of(rows, 0), cls.lam_of(rows, 1)
        return (a / b) ** 2 if a > 0 and b > 0 else 0.0


# ============================================================================================ Fourier analysis
class FourierW(_Sweep):
    """A periodic waveform of amplitude A: square (shape 0), triangular (1) or half-wave rectified sine (2). A tuned
    analyser reads the amplitude of the n-th harmonic, c_n = sqrt(a_n^2 + b_n^2), here worked out numerically from M
    samples of one period (midpoint rule), read to 1 mV."""

    PARAMS = {"x": 1.0, "s": 0.0, "shape": 0.0, "A": 2.0, "M": 2000.0}

    @staticmethod
    def wave(p, u):
        sh = int(p["shape"] + 0.5)
        if sh == 0:
            return p["A"] if u < 0.5 else -p["A"]
        if sh == 1:
            if u < 0.25:
                return 4.0 * p["A"] * u
            if u < 0.75:
                return p["A"] * (2.0 - 4.0 * u)
            return p["A"] * (4.0 * u - 4.0)
        v = math.sin(2.0 * PI * u)
        return p["A"] * v if v > 0 else 0.0

    @classmethod
    def coef(cls, p, n):
        M = int(p["M"] + 0.5)
        a = b = 0.0
        for i in range(M):
            u = (i + 0.5) / M
            w = cls.wave(p, u)
            a += w * math.cos(2.0 * PI * n * u)
            b += w * math.sin(2.0 * PI * n * u)
        a *= 2.0 / M
        b *= 2.0 / M
        return math.sqrt(a * a + b * b)

    @classmethod
    def read(cls, p, s, x, k):
        return {"y": _q(cls.coef(p, int(x + 0.5)), 0.001)}

    @classmethod
    def xs(cls, p, s):
        return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]

    @staticmethod
    def second(p):
        return 2 if int(p["shape"] + 0.5) == 2 else 3

    @classmethod
    def fit(cls, rows, p):
        c1 = c2 = None
        n2 = cls.second(p)
        for r in _stage(rows, 0):
            n = int(float(r["x"]) + 0.5)
            if n == 1:
                c1 = float(r["y"])
            if n == n2:
                c2 = float(r["y"])
        return c2 / c1 if c1 and c2 is not None else 0.0


# ============================================================================================ transducers
class Transducer(_Sweep):
    """Four transducers on one bench. typ 0: NTC thermistor R = R25 exp(B (1/T - 1/298.15)) in a water bath;
    typ 1: a foil strain gauge (factor GF) in a quarter bridge on a cantilever, V = Vex GF e / (4 + 2 GF e);
    typ 2: an LVDT on a micrometer, V = S x (1 - c (x / xr)^2); typ 3: a type K thermocouple with its cold junction in
    ice, E = a1 t + a2 t^2. Sensitivity: B (K), GF, S (mV/mm) or the mean Seebeck coefficient (microvolt/K)."""

    PARAMS = {"x": 0.0, "s": 0.0, "typ": 0.0, "R25": 10000.0, "Bt": 3950.0, "GF": 2.0, "Vex": 5.0, "S": 50.0,
              "c": 0.02, "xr": 5.0, "a1": 0.03996, "a2": 1.0e-5}

    @classmethod
    def read(cls, p, s, x, k):
        t = int(p["typ"] + 0.5)
        if t == 0:
            T = x + 273.15
            return {"y": _q(p["R25"] * math.exp(p["Bt"] * (1.0 / T - 1.0 / 298.15)), 1.0)}
        if t == 1:
            e = x * 1e-6
            return {"y": _q(p["Vex"] * p["GF"] * e / (4.0 + 2.0 * p["GF"] * e) * 1000.0, 0.001)}
        if t == 2:
            return {"y": _q(p["S"] * x * (1.0 - p["c"] * (x / p["xr"]) ** 2), 0.1)}
        return {"y": _q(p["a1"] * x + p["a2"] * x * x, 0.001)}

    @classmethod
    def xs(cls, p, s):
        t = int(p["typ"] + 0.5)
        if t == 0:
            return _rng(25.0, 85.0, 10.0)
        if t == 1:
            return _rng(0.0, 1000.0, 100.0)
        if t == 2:
            return _rng(-5.0, 5.0, 1.0)
        return _rng(0.0, 100.0, 10.0)

    @classmethod
    def fit(cls, rows, p):
        t = int(p["typ"] + 0.5)
        st = _stage(rows, 0)
        if t == 0:
            pts = [[1.0 / (float(r["x"]) + 273.15), math.log(float(r["y"]))] for r in st if float(r["y"]) > 0]
            f = _linfit(pts)
            return f[0] if f else 0.0
        if t == 2:
            pts = [[float(r["x"]), float(r["y"])] for r in st if abs(float(r["x"])) <= 2.0 + 1e-9]
        else:
            pts = [[float(r["x"]), float(r["y"])] for r in st]
        f = _linfit(pts)
        if not f:
            return 0.0
        if t == 1:
            return f[0] * 1e6 * 4.0 / (p["Vex"] * 1000.0)
        if t == 3:
            return f[0] * 1000.0
        return f[0]


# ============================================================================================ Stefan's constant
class Stefan(_Sweep):
    """m = 0: a blackened hollow copper body (mass mb, specific heat cb, area Ab, emissivity eb) heated and left to cool
    inside an evacuated enclosure at T0: mb cb dT/dt = -sigma eb Ab (T^4 - T0^4); readings T(t) every dt (RK4 with
    100 sub-steps, 0.1 K thermocouple). m = 1: a tungsten lamp filament (area Af, emissivity ew): P = sigma ew Af T^4 at
    equilibrium, the temperature from the resistance R / R0 = (T / T0)^1.2; readings V, I at set voltages."""

    PARAMS = {"x": 0.0, "s": 0.0, "m": 0.0, "sigma": 5.670374419e-8, "mb": 0.06, "cb": 385.0, "Ab": 5.03e-3,
              "eb": 0.97, "T0": 300.0, "Ti": 620.0, "dt": 20.0, "ew": 0.35, "Af": 1.2e-5, "R0": 1.0}

    @classmethod
    def temp(cls, p, t):
        n = int(math.floor(t / p["dt"] + 0.5)) * 100
        h = t / n if n > 0 else 0.0
        T = p["Ti"]
        k = p["sigma"] * p["eb"] * p["Ab"] / (p["mb"] * p["cb"])
        T04 = p["T0"] ** 4

        def f(u):
            return -k * (u * u * u * u - T04)
        for _ in range(n):
            k1 = f(T)
            k2 = f(T + 0.5 * h * k1)
            k3 = f(T + 0.5 * h * k2)
            k4 = f(T + h * k3)
            T += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        return T

    @classmethod
    def lamp_T(cls, p, V):
        """The filament temperature where V^2 / R(T) = sigma ew Af T^4, R = R0 (T / T0)^1.2 (bisection)."""
        lo, hi = p["T0"], 4000.0
        for _ in range(100):
            mid = (lo + hi) / 2.0
            R = p["R0"] * math.pow(mid / p["T0"], 1.2)
            if V * V / R > p["sigma"] * p["ew"] * p["Af"] * mid ** 4:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    @classmethod
    def read(cls, p, s, x, k):
        if p["m"] < 0.5:
            return {"y": _q(cls.temp(p, x) - 273.15, 0.1)}
        T = cls.lamp_T(p, x)
        R = p["R0"] * math.pow(T / p["T0"], 1.2)
        return {"y": _q(x / R * 1000.0, 0.1)}             # filament current, mA

    @classmethod
    def xs(cls, p, s):
        if p["m"] < 0.5:
            return _rng(0.0, 20.0 * p["dt"], p["dt"])
        return _rng(2.0, 12.0, 1.0)

    @classmethod
    def fit(cls, rows, p):
        st = sorted(([float(r["x"]), float(r["y"])] for r in _stage(rows, 0)), key=lambda q: q[0])
        if len(st) < 4:
            return 0.0
        sxy = sxx = 0.0
        if p["m"] < 0.5:
            for i in range(1, len(st) - 1):
                dTdt = (st[i + 1][1] - st[i - 1][1]) / (st[i + 1][0] - st[i - 1][0])
                T = st[i][1] + 273.15
                yv = -dTdt * p["mb"] * p["cb"] / (p["eb"] * p["Ab"])
                xv = T ** 4 - p["T0"] ** 4
                sxy += xv * yv
                sxx += xv * xv
            return sxy / sxx if sxx > 0 else 0.0
        for q in st:
            V, I = q[0], q[1] / 1000.0
            if I <= 0:
                continue
            R = V / I
            T = p["T0"] * math.pow(R / p["R0"], 1.0 / 1.2)
            xv = p["ew"] * p["Af"] * T ** 4
            sxy += xv * V * I
            sxx += xv * xv
        return sxy / sxx if sxx > 0 else 0.0


# ============================================================================================ copper characteristic X-rays
class CuXray(_Sweep):
    """A copper-anode X-ray tube at V kV, a flat LiF crystal (spacing dc, Angstrom) and a counter at 2 theta.
    Counts/s = bremsstrahlung (Kramers, (lambda / lambda_min - 1) / lambda^2 past the Duane-Hunt limit) + the K lines
    (K-alpha1, K-alpha2 at half its height, K-beta) as Gaussians of angular width wd (degrees FWHM in 2 theta).
    Stage 0: no filter; stage 1: a nickel foil of thickness tn (cm) in the beam, transmission exp(-mu rho t) with
    mu/rho jumping at the nickel K edge (power laws in lambda either side)."""

    PARAMS = {"x": 40.0, "s": 0.0, "V": 30.0, "dc": 2.0135, "la1": 1.540562, "la2": 1.544390, "lb": 1.392218,
              "Ia": 1500.0, "Ib": 300.0, "Ic": 40.0, "wd": 0.30, "tn": 0.0018, "rho": 8.908, "muA": 49.3, "muB": 276.0,
              "edge": 1.48802, "t": 10.0, "seed": 97.0}
    NST = 2

    @classmethod
    def lam(cls, p, tt):
        return 2.0 * p["dc"] * math.sin(tt / 2.0 * PI / 180.0)

    @classmethod
    def ang(cls, p, lam):
        return 2.0 * math.asin(lam / (2.0 * p["dc"])) * 180.0 / PI

    @classmethod
    def trans(cls, p, lam):
        if lam > p["edge"]:
            mu = p["muA"] * math.pow(lam / 1.540562, 2.8)
        else:
            mu = p["muB"] * math.pow(lam / 1.392218, 2.8)
        return math.exp(-mu * p["rho"] * p["tn"])

    @classmethod
    def rate(cls, p, s, tt):
        lam = cls.lam(p, tt)
        lmin = HC_KEVA / p["V"]
        br = p["Ic"] * (lam / lmin - 1.0) / (lam * lam) if lam > lmin else 0.0
        sg = p["wd"] / 2.355
        g = 0.0
        for lv, a in ((p["la1"], 1.0), (p["la2"], 0.5), (p["lb"], p["Ib"] / p["Ia"])):
            g += a * math.exp(-0.5 * ((tt - cls.ang(p, lv)) / sg) ** 2)
        n = br + p["Ia"] * g
        return n * cls.trans(p, lam) if s == 1 else n

    @classmethod
    def read(cls, p, s, x, k):
        c = _cnt(p, k, cls.rate(p, s, x) * p["t"])
        return {"y": c / p["t"], "N": c}

    @classmethod
    def xs(cls, p, s):
        return _rng(36.0, 50.0, 0.1)

    @classmethod
    def fit(cls, rows, p):
        """K-alpha wavelength (weighted K-alpha1 + K-alpha2, unresolved) from the centroid of the strongest peak."""
        pts = _sorted(_stage(rows, 0))
        if len(pts) < 10:
            return 0.0
        best, ib = -1.0, -1
        for i, q in enumerate(pts):
            if q[1] > best:
                best, ib = q[1], i
        lo = pts[max(ib - 25, 0)][1]
        hi = pts[min(ib + 25, len(pts) - 1)][1]
        base = lo if lo < hi else hi
        sw = swy = 0.0
        for q in pts[max(ib - 12, 0): ib + 13]:
            if q[1] - base > (best - base) / 2.0:
                sw += q[1] - base
                swy += (q[1] - base) * q[0]
        if sw <= 0:
            return 0.0
        return cls.lam(p, swy / sw)


# ============================================================================================ microwave Bragg diffraction
class MWBragg(_Sweep):
    """A cubic lattice of metal balls (plane spacing d) on the turntable of a microwave goniometer: crystal at theta,
    receiver at 2 theta. Reflections where 2 d sin(theta) = n lambda, Gaussian in theta (FWHM wb degrees), heights
    A1, A2 on a background. Detector reading in % of full scale (0.1 %)."""

    PARAMS = {"x": 10.0, "s": 0.0, "d": 0.040, "lam": 0.02855, "wb": 3.0, "A1": 80.0, "A2": 45.0, "bk": 4.0}

    @classmethod
    def read(cls, p, s, x, k):
        sg = p["wb"] / 2.355
        v = p["bk"]
        for n, a in ((1, p["A1"]), (2, p["A2"])):
            r = n * p["lam"] / (2.0 * p["d"])
            if r < 1.0:
                th = math.asin(r) * 180.0 / PI
                v += a * math.exp(-0.5 * ((x - th) / sg) ** 2)
        return {"y": _q(v, 0.1)}

    @classmethod
    def xs(cls, p, s):
        return _rng(10.0, 60.0, 0.5)

    @classmethod
    def peaks(cls, rows, p):
        pts = _sorted(_stage(rows, 0))
        out = []
        for i in range(1, len(pts) - 1):
            if pts[i][1] > pts[i - 1][1] and pts[i][1] >= pts[i + 1][1] and pts[i][1] > 3.0 * p["bk"]:
                pk = _peakwidth(pts, pts[i][0] - 0.01, pts[i][0] + 0.01, p["bk"])
                if pk:
                    out.append(pk[0])
        return out

    @classmethod
    def fit(cls, rows, p):
        pk = cls.peaks(rows, p)
        if not pk:
            return 0.0
        tot = 0.0
        for i, th in enumerate(pk[:2]):
            tot += (i + 1) * p["lam"] / (2.0 * math.sin(th * PI / 180.0))
        return tot / min(len(pk), 2)


# ============================================================================================ horn antenna pattern
class HornPattern(_Sweep):
    """A pyramidal horn (aperture a wide in the H-plane, b high in the E-plane) radiating at wavelength lam, received
    by a second horn on a turntable in the far field. E-plane (pl = 0): uniform aperture field, F = sin(v) / v,
    v = pi b sin(theta) / lam. H-plane (pl = 1): cosine-tapered field, F = cos(u) / (1 - (2u/pi)^2), u = pi a sin / lam.
    Square-law detector reading 100 F^2 (%). Gain: G = eff 4 pi a b / lam^2 with eff = 8/pi^2 (the two tapers)."""

    PARAMS = {"x": 0.0, "s": 0.0, "pl": 0.0, "a": 0.070, "b": 0.052, "lam": 0.02855}
    NST = 2

    @classmethod
    def pat(cls, p, th):
        sn = math.sin(th * PI / 180.0)
        if p["pl"] < 0.5:
            v = PI * p["b"] * sn / p["lam"]
            return 1.0 if abs(v) < 1e-12 else math.sin(v) / v
        u = PI * p["a"] * sn / p["lam"]
        den = 1.0 - (2.0 * u / PI) ** 2
        if abs(den) < 1e-9:
            return PI / 4.0
        return math.cos(u) / den

    @classmethod
    def read(cls, p, s, x, k):
        if s == 1:
            g = cls.gain(p) * p["lam"] / (4.0 * PI * x)
            return {"y": _q(1000.0 * g * g, 0.001)}
        f = cls.pat(p, x)
        return {"y": _q(100.0 * f * f, 0.1)}

    @classmethod
    def xs(cls, p, s):
        return _rng(-40.0, 40.0, 1.0) if s == 0 else [0.6, 0.8, 1.0, 1.2]

    @classmethod
    def fit(cls, rows, p):
        pts = _sorted(_stage(rows, 0))
        pk = _peakwidth(pts, -5.0, 5.0, 0.0)
        return pk[1] if pk else 0.0

    @staticmethod
    def gain(p):
        return 8.0 / (PI * PI) * 4.0 * PI * p["a"] * p["b"] / (p["lam"] * p["lam"])


# ============================================================================================ coupled oscillators
class Coupled(_Sweep):
    """Two equal oscillators, weakly coupled. m = 0: two pendulums (length L, bob mass mb) joined by a light spring k:
    w1 = sqrt(g/L) (in phase), w2 = sqrt(g/L + 2k/mb) (in opposite phase). m = 1: two equal LC circuits (L, C) coupled
    by a mutual inductance Mu: w1 = 1/sqrt((L + Mu) C), w2 = 1/sqrt((L - Mu) C). Readings (x): the time of nper
    oscillations in the in-phase mode (0) and in the out-of-phase mode (1), and the beat period 2 pi / (w2 - w1) when
    one oscillator alone is started (2). Coupling kappa = (w2^2 - w1^2) / (w2^2 + w1^2) = (T1^2 - T2^2) / (T1^2 + T2^2)."""

    PARAMS = {"x": 0.0, "s": 0.0, "m": 0.0, "g": 9.81, "L": 0.6, "mb": 0.2, "k": 1.0, "Lc": 1.0e-2, "C": 1.0e-6,
              "Mu": 1.0e-3, "nper": 10.0}

    @staticmethod
    def omegas(p):
        if p["m"] < 0.5:
            return math.sqrt(p["g"] / p["L"]), math.sqrt(p["g"] / p["L"] + 2.0 * p["k"] / p["mb"])
        return 1.0 / math.sqrt((p["Lc"] + p["Mu"]) * p["C"]), 1.0 / math.sqrt((p["Lc"] - p["Mu"]) * p["C"])

    @classmethod
    def read(cls, p, s, x, k):
        w1, w2 = cls.omegas(p)
        i = int(x + 0.5)
        if i == 2:
            t = 2.0 * PI / (w2 - w1)
        else:
            t = p["nper"] * 2.0 * PI / (w1 if i == 0 else w2)
        if p["m"] < 0.5:
            return {"y": _q(t, 0.01)}               # seconds, stopwatch
        return {"y": _q(t * 1000.0, 0.001)}         # milliseconds, storage scope

    @classmethod
    def xs(cls, p, s):
        return [0.0, 1.0, 2.0]

    @classmethod
    def fit(cls, rows, p):
        t1 = t2 = None
        for r in _stage(rows, 0):
            i = int(float(r["x"]) + 0.5)
            if i == 0:
                t1 = float(r["y"])
            if i == 1:
                t2 = float(r["y"])
        if not t1 or not t2:
            return 0.0
        return (t1 * t1 - t2 * t2) / (t1 * t1 + t2 * t2)


# ============================================================================================ gas-filled photocell
class GasPhoto(_Sweep):
    """A gas-filled photocell (photocathode, anode wire, argon at low pressure) lit by a lamp at distance d (cm).
    The photocurrent first saturates as the field collects every photoelectron, I = I0 (d0/d)^2 (1 - exp(-V/V0)),
    then rises again above Vg as the electrons ionise the gas (Townsend gain exp(al (V - Vg))). Stage 0: current
    against the anode voltage at d0; stage 1: current against the lamp distance at Vop (x = 0: lamp off, the dark
    current)."""

    PARAMS = {"x": 0.0, "s": 0.0, "I0": 2.0, "V0": 6.0, "Vg": 35.0, "al": 0.04, "d0": 20.0, "Vop": 60.0, "Id": 0.002}
    NST = 2

    @staticmethod
    def gain(p, V):
        return 1.0 if V <= p["Vg"] else math.exp(p["al"] * (V - p["Vg"]))

    @classmethod
    def read(cls, p, s, x, k):
        if s == 0:
            v = p["I0"] * (1.0 - math.exp(-x / p["V0"])) * cls.gain(p, x) + p["Id"]
        elif x <= 0:
            v = p["Id"]
        else:
            v = p["I0"] * (p["d0"] / x) ** 2 * (1.0 - math.exp(-p["Vop"] / p["V0"])) * cls.gain(p, p["Vop"]) + p["Id"]
        return {"y": _q(v, 0.001)}               # microamperes

    @classmethod
    def xs(cls, p, s):
        return _rng(0.0, 90.0, 5.0) if s == 0 else [0.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]

    @classmethod
    def fit(cls, rows, p):
        """Exponent n of I - Idark ~ d^n (the inverse-square law gives -2 when the current follows the light flux)."""
        st = _stage(rows, 1)
        dark = None
        for r in st:
            if float(r["x"]) <= 0:
                dark = float(r["y"])
        if dark is None:
            return 0.0
        pts = [[math.log(float(r["x"])), math.log(float(r["y"]) - dark)] for r in st
               if float(r["x"]) > 0 and float(r["y"]) - dark > 0]
        f = _linfit(pts)
        return f[0] if f else 0.0


# ============================================================================================ tables
KERNELS: dict[str, Any] = {
    "pm9_gmdt": GMDead, "pm9_gmeff": GMEff, "pm9_betaf": BetaFeather, "pm9_k40": K40Std, "pm9_spark": SparkAlpha,
    "pm9_prop": PropCounter, "pm9_kurie": Kurie, "pm9_angcorr": AngCorr, "pm9_hallt": HallT, "pm9_twop": TwoProbe,
    "pm9_diode": DiodeIV, "pm9_photoc": PhotoCond, "pm9_acsusc": ACSusc, "pm9_lclat": LCLattice, "pm9_echo": PulseEcho,
    "pm9_sound": SoundCRO, "pm9_lecher": Lecher, "pm9_fourier": FourierW, "pm9_trans": Transducer, "pm9_stefan": Stefan,
    "pm9_cuxray": CuXray, "pm9_mwbragg": MWBragg, "pm9_horn": HornPattern, "pm9_coupled": Coupled,
    "pm9_gasphoto": GasPhoto,
}
FAMILY = {k: ("nuclear" if k in ("pm9_gmdt", "pm9_gmeff", "pm9_betaf", "pm9_k40", "pm9_spark", "pm9_prop", "pm9_kurie",
                                 "pm9_angcorr") else "osc_wave" if k in ("pm9_lclat", "pm9_echo", "pm9_sound", "pm9_lecher",
                                                                          "pm9_fourier", "pm9_mwbragg", "pm9_horn",
                                                                          "pm9_coupled")
              else "solid") for k in KERNELS}


def _hp_e(p):
    """E-plane half-power beam width: sin(v)/v = 1/sqrt2 at v = 1.391557 (solved once), so HPBW = 2 asin(1.391557
    lam / (pi b))."""
    return 2.0 * math.asin(1.391557 * p["lam"] / (PI * p["b"])) * 180.0 / PI


def _hp_h(p):
    """H-plane: cos(u)/(1 - (2u/pi)^2) = 1/sqrt2 at u = 1.866585 (solved once)."""
    return 2.0 * math.asin(1.866585 * p["lam"] / (PI * p["a"])) * 180.0 / PI


TEXTBOOK = {
    "pm9_tau": lambda p: p["tau"],
    "pm9_eint": lambda p: p["eint"],
    # Katz and Penfold range of the highest-energy group
    "pm9_range": lambda p: 0.412 * math.pow(p["E1"], 1.265 - 0.0954 * math.log(p["E1"])),
    # partial beta-decay half-life of K-40, in years: T_half / branching ratio
    "pm9_tbeta": lambda p: p["T12"] / p["br"],
    # Geiger's rule for the mean range of alpha particles in air
    "pm9_geiger": lambda p: 0.318 * math.pow(p["E"], 1.5),
    # proportional counter resolution (FWHM, %) from Fano + avalanche statistics
    "pm9_presol": lambda p: 100.0 * 2.355 * math.sqrt((p["F"] + p["b"]) * p["W"] / p["E"]),
    "pm9_endpoint": lambda p: p["T1"] if p["f2"] <= 0 or p["T1"] >= p["T2"] else p["T2"],
    # Co-60 4(2)2(2)0: a2 = 1/8 (Hamilton 1940)
    "pm9_a2": lambda p: p["a2"],
    "pm9_eg0": lambda p: p["Eg0"],
    "pm9_twop": lambda p: p["Eg0"] if p["mat"] < 0.5 else 1.0 / p["rhog"],
    "pm9_egphoto": lambda p: p["Eg"],
    "pm9_tc": lambda p: p["Tc"],
    "pm9_lccut": lambda p: (1.0 / (PI * math.sqrt(p["L"] * p["C"]))) if p["d"] < 0.5
    else math.sqrt(2.0 / (p["L"] * p["C1"])) / (2.0 * PI),
    "pm9_v": lambda p: p["v"],
    "pm9_vsound": lambda p: 331.3 * math.sqrt(1.0 + p["tc"] / 273.15),
    "pm9_eps": lambda p: p["eps"],
    # Fourier series of the three waveforms: square b3/b1 = 1/3, triangle 1/9, half-wave rectified a2/a1 = 4/(3 pi)
    "pm9_fratio": lambda p: [1.0 / 3.0, 1.0 / 9.0, 4.0 / (3.0 * PI)][int(p["shape"] + 0.5)],
    "pm9_sens": lambda p: [p["Bt"], p["GF"], p["S"], 1000.0 * (p["a1"] + 100.0 * p["a2"])][int(p["typ"] + 0.5)],
    "pm9_sigma": lambda p: p["sigma"],
    "pm9_kalpha": lambda p: (2.0 * p["la1"] + p["la2"]) / 3.0,
    "pm9_d": lambda p: p["d"],
    "pm9_hpbw": lambda p: _hp_e(p) if p["pl"] < 0.5 else _hp_h(p),
    # coupling of two equal oscillators: k / (mb g / L + k) for the pendulums, Mu / L for the LC circuits
    "pm9_kappa": lambda p: p["k"] / (p["mb"] * p["g"] / p["L"] + p["k"]) if p["m"] < 0.5 else p["Mu"] / p["Lc"],
    # a photocurrent proportional to the light flux from a point lamp falls as d^-2
    "pm9_isq": lambda p: -2.0,
}
