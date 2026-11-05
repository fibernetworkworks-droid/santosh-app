"""Kernel pack `msc_solid`: the M.Sc. physics benches for solid state, materials characterisation, vacuum and
plasma (see `packs/__init__.py`). Its exact JavaScript twin is `app/static/prayog/packs/msc_solid.js`; the test
suite runs both and demands the same numbers. Every kernel name starts with `msc_` so it cannot collide.

Deterministic: the only pseudo-noise (an X-ray scan) is a hash of the scan step, never the clock.
Constants are CODATA / SI 2019; every material number lives in a lab or a family file with its source.

Honest limits (said again in each lab): these are models of the textbook laws - a linear metal R(T), a
Curie-Weiss dielectric, a tanh hysteresis branch, Gaussian powder-diffraction peaks, a Bohm ion current - so the
numbers a student reads are the lab's own, and they are checked against the closed formula of that law.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
H = 6.62607015e-34
C = 2.99792458e8
QE = 1.602176634e-19
KB = 1.380649e-23
ME = 9.1093837015e-31
AMU = 1.66053906660e-27
MU0 = 1.25663706212e-6
EPS0 = 8.8541878128e-12
GRAV = 9.80665
LN2 = math.log(2.0)


def _slope(pts: list[list[float]]) -> float:
    n = len(pts)
    if n < 2:
        return 0.0
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    d = n * sxx - sx * sx
    return 0.0 if d == 0 else (n * sxy - sx * sy) / d


def _line(pts: list[list[float]]) -> tuple[float, float]:
    """Least-squares y = m x + c (0, 0 when it cannot be formed)."""
    n = len(pts)
    if n < 2:
        return 0.0, 0.0
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    d = n * sxx - sx * sx
    if d == 0:
        return 0.0, 0.0
    m = (n * sxy - sx * sy) / d
    return m, (sy - m * sx) / n


def _rows(rows: list[dict], keys: list[str]) -> list[list[float]]:
    out = []
    for r in rows or []:
        vals = []
        ok = True
        for k in keys:
            v = r.get(k)
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


class _Base:
    """The shared time-only init/step; every kernel here is a static response, the student sets the condition."""

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


# ====================================================================================== metal: R against T
class Metal(_Base):
    """A metal wire coil of resistance R0 at the reference temperature Tref. Over a few hundred kelvin a pure
    metal follows R = R0 [1 + alpha (T - Tref)] (alpha = temperature coefficient of resistance)."""

    PARAMS = {"T": 293.0, "R0": 1.2, "alpha": 0.0039, "Tref": 293.0, "I": 0.01}
    VARS = ["t", "R", "V", "T"]

    @staticmethod
    def res(p: dict) -> float:
        return p["R0"] * (1.0 + p["alpha"] * (p["T"] - p["Tref"]))

    @staticmethod
    def view(s, p, cfg=None):
        r = Metal.res(p)
        return {"t": s.get("t", 0.0), "R": r, "V": r * p["I"], "T": p["T"]}

    @staticmethod
    def measure(p, cfg=None):
        """alpha as a student gets it: two resistances 100 K apart, (R2 - R1) / (R1 (T2 - T1))."""
        q1 = dict(p, T=p["Tref"])
        q2 = dict(p, T=p["Tref"] + 100.0)
        r1, r2 = Metal.res(q1), Metal.res(q2)
        return {"alpha": (r2 - r1) / (r1 * 100.0), "R": Metal.res(p), "T": p["T"]}


def _metal_alpha(p: dict) -> float:
    return p["alpha"]


# ====================================================================================== Seebeck coefficient
class Seebeck(_Base):
    """A thermocouple with its hot junction dT kelvin above the cold one: V = Voff + S dT. S is in microvolts per
    kelvin and Voff is the amplifier's own zero error in microvolts, which a straight-line fit absorbs."""

    PARAMS = {"dT": 50.0, "S": 41.0, "Voff": 1.5, "Tcold": 293.0}
    VARS = ["t", "V", "dT", "Th"]

    @staticmethod
    def volts(p: dict) -> float:
        return p["Voff"] + p["S"] * p["dT"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "V": Seebeck.volts(p), "dT": p["dT"], "Th": p["Tcold"] + p["dT"]}

    @staticmethod
    def measure(p, cfg=None):
        v1 = Seebeck.volts(dict(p, dT=20.0))
        v2 = Seebeck.volts(dict(p, dT=80.0))
        return {"S": (v2 - v1) / 60.0, "V": Seebeck.volts(p)}


def _seebeck_S(p: dict) -> float:
    return p["S"]


# ====================================================================================== ionic conductivity
class Ionic(_Base):
    """An ionic crystal pellet (thickness Lp, electrode area Ap). Vacancies hop, so sigma T = A exp(-Ea / k T)."""

    PARAMS = {"T": 500.0, "Ea": 0.8, "A": 4.0e7, "Lp": 0.002, "Ap": 1.0e-4}
    VARS = ["t", "R", "sigma", "T", "lnsT"]

    @staticmethod
    def sigma(p: dict) -> float:
        return p["A"] / p["T"] * math.exp(-p["Ea"] * QE / (KB * p["T"]))

    @staticmethod
    def view(s, p, cfg=None):
        sg = Ionic.sigma(p)
        return {"t": s.get("t", 0.0), "R": p["Lp"] / (sg * p["Ap"]), "sigma": sg, "T": p["T"],
                "lnsT": math.log(sg * p["T"])}

    @staticmethod
    def measure(p, cfg=None):
        t1, t2 = 450.0, 650.0
        a = math.log(Ionic.sigma(dict(p, T=t1)) * t1)
        b = math.log(Ionic.sigma(dict(p, T=t2)) * t2)
        ea = -KB * (b - a) / (1.0 / t2 - 1.0 / t1) / QE
        return {"Ea": ea, "R": Ionic.view({}, p)["R"]}


def _ionic_Ea(p: dict) -> float:
    return p["Ea"]


# ====================================================================================== superconductor R(T)
class Super(_Base):
    """A high-Tc bar on a four-lead holder. Above Tc the normal-state resistance is linear in T (Rn100 at 100 K);
    through the transition (width w) the resistance falls to zero: R = Rn (1 + tanh((T - Tc) / w)) / 2."""

    PARAMS = {"T": 100.0, "Tc": 92.0, "w": 1.2, "Rn100": 0.06, "I": 0.01}
    VARS = ["t", "R", "V", "T"]

    @staticmethod
    def frac(T: float, p: dict) -> float:
        return 0.5 * (1.0 + math.tanh((T - p["Tc"]) / p["w"]))

    @staticmethod
    def rn(T: float, p: dict) -> float:
        return p["Rn100"] * T / 100.0

    @staticmethod
    def res(p: dict) -> float:
        return Super.rn(p["T"], p) * Super.frac(p["T"], p)

    @staticmethod
    def view(s, p, cfg=None):
        r = Super.res(p)
        return {"t": s.get("t", 0.0), "R": r, "V": r * p["I"], "T": p["T"]}

    @staticmethod
    def measure(p, cfg=None):
        """The mid-point Tc: the temperature at which R is half its normal-state value, found by bisection."""
        lo, hi = 40.0, 200.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if Super.frac(mid, p) < 0.5:
                lo = mid
            else:
                hi = mid
        tm = 0.5 * (lo + hi)
        lo, hi = 40.0, 200.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if Super.frac(mid, p) < 0.01:
                lo = mid
            else:
                hi = mid
        return {"Tc": tm, "T0": 0.5 * (lo + hi), "R": Super.res(p)}


def _super_Tc(p: dict) -> float:
    return p["Tc"]


# ====================================================================================== magnetoresistance
class Magres(_Base):
    """A semiconductor bar in a transverse field B: the Lorentz force bends the carriers, so R = R0 [1 + xi (mu B)^2]
    (mu = carrier mobility, xi of order one - taken as 1 in this lab's model)."""

    PARAMS = {"B": 0.0, "mu": 7.7, "R0": 2.0, "xi": 1.0, "I": 0.005}
    VARS = ["t", "R", "V", "B", "dRR"]

    @staticmethod
    def res(p: dict) -> float:
        return p["R0"] * (1.0 + p["xi"] * (p["mu"] * p["B"]) ** 2)

    @staticmethod
    def view(s, p, cfg=None):
        r = Magres.res(p)
        return {"t": s.get("t", 0.0), "R": r, "V": r * p["I"], "B": p["B"], "dRR": r / p["R0"] - 1.0}

    @staticmethod
    def measure(p, cfg=None):
        b1, b2 = 0.2, 0.6
        r1 = Magres.res(dict(p, B=b1))
        r2 = Magres.res(dict(p, B=b2))
        sl = (r2 - r1) / p["R0"] / (b2 * b2 - b1 * b1)
        return {"mu": math.sqrt(sl / p["xi"]) if sl > 0 else 0.0, "R": Magres.res(p)}


def _magres_mu(p: dict) -> float:
    return p["mu"]


# ====================================================================================== Curie-Weiss dielectric
class Ferro(_Base):
    """A ferroelectric crystal plate (second-order transition at Tc, like TGS). Above Tc the permittivity follows
    the Curie-Weiss law eps = eb + C / (T - Tc); below it the law is C / (2 (Tc - T)). The very top of the peak is
    rounded over +-dl kelvin, as in a real crystal."""

    PARAMS = {"T": 340.0, "Tc": 322.15, "C": 3000.0, "eb": 5.0, "dl": 0.6, "Ap": 1.0e-4, "d": 1.0e-3}
    VARS = ["t", "eps", "Cap", "T", "inv"]

    @staticmethod
    def eps(T: float, p: dict) -> float:
        x = T - p["Tc"]
        if x >= 0:
            return p["eb"] + p["C"] / max(x, p["dl"])
        return p["eb"] + p["C"] / (2.0 * max(-x, p["dl"]))

    @staticmethod
    def view(s, p, cfg=None):
        e = Ferro.eps(p["T"], p)
        return {"t": s.get("t", 0.0), "eps": e, "Cap": EPS0 * e * p["Ap"] / p["d"], "T": p["T"], "inv": 1.0 / e}

    @staticmethod
    def measure(p, cfg=None):
        """Tc as the temperature of the permittivity maximum, found by a 0.05 K scan (mean of the top plateau)."""
        best, n = -1.0, 0
        t0 = p["Tc"] - 20.0
        vals = []
        for i in range(0, 801):
            e = Ferro.eps(t0 + 0.05 * i, p)
            vals.append(e)
            if e > best:
                best = e
        tot = 0.0
        for i, e in enumerate(vals):
            if e >= best * (1.0 - 1e-12):
                tot += t0 + 0.05 * i
                n += 1
        return {"Tc": tot / n, "eps": Ferro.eps(p["T"], p), "epsmax": best}


def _ferro_Tc(p: dict) -> float:
    return p["Tc"]


# ====================================================================================== Curie point (inductance)
class Curie(_Base):
    """A coil wound on a ferro- or ferrimagnetic core, heated through its Curie point. The inductance is
    L = L0 [1 + K g(T)] where g falls from 1 to 0 across the transition; Tc is read by the tangent method (the
    tangent at the steepest fall meets the paramagnetic baseline at Tc). g is a logistic of width w centred a
    distance 2 w below Tc, which is exactly where the tangent method puts Tc."""

    PARAMS = {"T": 300.0, "Tc": 573.0, "K": 40.0, "L0": 2.0e-3, "w": 3.0}
    VARS = ["t", "L", "L_mH", "T"]

    @staticmethod
    def ind(T: float, p: dict) -> float:
        g = 1.0 / (1.0 + math.exp((T - (p["Tc"] - 2.0 * p["w"])) / p["w"]))
        return p["L0"] * (1.0 + p["K"] * g)

    @staticmethod
    def view(s, p, cfg=None):
        L = Curie.ind(p["T"], p)
        return {"t": s.get("t", 0.0), "L": L, "L_mH": L * 1e3, "T": p["T"]}

    @staticmethod
    def measure(p, cfg=None):
        """The tangent (steepest-fall) method on a 0.1 K scan: Tc = T_steep + (L_steep - L_baseline) / |slope|."""
        t0 = p["Tc"] - 60.0
        best, bi = 0.0, 0
        for i in range(0, 1201):
            t = t0 + 0.1 * i
            sl = (Curie.ind(t + 0.05, p) - Curie.ind(t - 0.05, p)) / 0.1
            if sl < best:
                best, bi = sl, i
        ts = t0 + 0.1 * bi
        base = Curie.ind(p["Tc"] + 400.0, p)
        return {"Tc": ts + (Curie.ind(ts, p) - base) / -best, "L": Curie.ind(p["T"], p)}


def _curie_Tc(p: dict) -> float:
    return p["Tc"]


# ====================================================================================== liquid crystal N-I
class LiquidCrystal(_Base):
    """A thin nematic cell between crossed polarisers, optic axis at 45 degrees, on a hot stage. The order
    parameter follows Haller's law S = (1 - 0.98 T / Tni)^0.22 and the birefringence is dn = dn0 S, so the light
    passed is I = I0 sin^2(pi dn d / lam). At the nematic-isotropic temperature Tni the order vanishes and the
    field goes dark (apart from a stray-light floor)."""

    PARAMS = {"T": 300.0, "Tni": 308.15, "dn0": 0.32, "d": 2.4e-6, "lam": 6.328e-7, "I0": 1.0, "stray": 0.004}
    VARS = ["t", "I", "S", "T"]

    @staticmethod
    def order(T: float, p: dict) -> float:
        if T >= p["Tni"]:
            return 0.0
        return (1.0 - 0.98 * T / p["Tni"]) ** 0.22

    @staticmethod
    def light(T: float, p: dict) -> float:
        dn = p["dn0"] * LiquidCrystal.order(T, p)
        return p["I0"] * (math.sin(PI * dn * p["d"] / p["lam"]) ** 2) + p["stray"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": LiquidCrystal.light(p["T"], p), "S": LiquidCrystal.order(p["T"], p),
                "T": p["T"]}

    @staticmethod
    def measure(p, cfg=None):
        """Tni by bisection on the order parameter (zero above, positive below)."""
        lo, hi = p["Tni"] - 20.0, p["Tni"] + 20.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if LiquidCrystal.order(mid, p) > 0:
                lo = mid
            else:
                hi = mid
        return {"Tni": 0.5 * (lo + hi), "I": LiquidCrystal.light(p["T"], p)}


def _lc_Tni(p: dict) -> float:
    return p["Tni"]


# ====================================================================================== dielectric / LCR meter
class Dielectric(_Base):
    """A guarded parallel-plate cell (area Ap, gap d) filled by a disc of the sample, read by an LCR meter at
    frequency f. Debye relaxation: eps' = einf + (es - einf) / (1 + (f/fr)^2); loss tan(delta) = eps'' / eps'.
    A nonpolar solid has fr far above the meter's range, so eps' is flat there."""

    PARAMS = {"f": 1000.0, "es": 6.0, "einf": 3.0, "fr": 4.0e4, "Ap": 9.6e-4, "d": 1.0e-3}
    VARS = ["t", "C", "C_pF", "D", "f", "er"]

    @staticmethod
    def eps1(f: float, p: dict) -> float:
        x = f / p["fr"]
        return p["einf"] + (p["es"] - p["einf"]) / (1.0 + x * x)

    @staticmethod
    def eps2(f: float, p: dict) -> float:
        x = f / p["fr"]
        return (p["es"] - p["einf"]) * x / (1.0 + x * x)

    @staticmethod
    def view(s, p, cfg=None):
        e1 = Dielectric.eps1(p["f"], p)
        c = EPS0 * e1 * p["Ap"] / p["d"]
        return {"t": s.get("t", 0.0), "C": c, "C_pF": c * 1e12, "D": Dielectric.eps2(p["f"], p) / e1,
                "f": p["f"], "er": e1}

    @staticmethod
    def measure(p, cfg=None):
        c = EPS0 * Dielectric.eps1(p["f"], p) * p["Ap"] / p["d"]
        return {"er": c * p["d"] / (EPS0 * p["Ap"]), "C": c, "D": Dielectric.eps2(p["f"], p) / Dielectric.eps1(p["f"], p)}


def _diel_er(p: dict) -> float:
    return Dielectric.eps1(p["f"], p)


# ====================================================================================== hysteresis loop tracer
class Loop(_Base):
    """A hysteresis loop traced by sweeping the drive field between +-H0. The branch going up is
    M = Ms tanh((H - Hc_eff) / a) and the branch coming down M = Ms tanh((H + Hc_eff) / a): the magnetisation
    (or flux density B, or polarisation P) lags the field, and the lag is the coercive field. A loop driven only
    weakly does not reach saturation and is narrower, so Hc_eff = Hc [1 - exp(-(H0 / Hc)^2)]. `kind` tells the
    rig what the axes are: 1 = B-H, 2 = P-E, 3 = M-H."""

    PARAMS = {"H": 0.0, "Ms": 1.5, "Hc": 80.0, "a": 32.0, "H0": 400.0, "br": 1.0, "kind": 1.0}
    VARS = ["t", "H", "M", "Hc_eff"]

    @staticmethod
    def hc_eff(p: dict) -> float:
        return p["Hc"] * (1.0 - math.exp(-((p["H0"] / p["Hc"]) ** 2)))

    @staticmethod
    def m(h: float, br: float, p: dict) -> float:
        return p["Ms"] * math.tanh((h - br * Loop.hc_eff(p)) / p["a"])

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "H": p["H"], "M": Loop.m(p["H"], p["br"], p), "Hc_eff": Loop.hc_eff(p)}

    @staticmethod
    def measure(p, cfg=None):
        """One full cycle of 2000 steps each way: Hc from the zero crossing of the falling branch, Mr from H = 0,
        Ms from the field peak, and the loop area = integral of (falling - rising) M dH (trapezoid rule)."""
        n = 2000
        h0 = p["H0"]
        hs = [-h0 + 2.0 * h0 * i / n for i in range(n + 1)]
        up = [Loop.m(h, 1.0, p) for h in hs]
        dn = [Loop.m(h, -1.0, p) for h in hs]
        hc = 0.0
        for i in range(n):
            if dn[i] < 0 <= dn[i + 1]:
                hc = -(hs[i] + (hs[i + 1] - hs[i]) * dn[i] / (dn[i] - dn[i + 1]))
                break
        area = 0.0
        for i in range(n):
            area += 0.5 * ((dn[i] - up[i]) + (dn[i + 1] - up[i + 1])) * (hs[i + 1] - hs[i])
        return {"Hc": hc, "Mr": Loop.m(0.0, -1.0, p), "Ms": up[n], "area": area}


def _loop_Hc(p: dict) -> float:
    return Loop.hc_eff(p)


# ====================================================================================== X-ray powder diffraction
def _hkl_list(ltype: int, z1: float, z2: float, lam: float, a: float, tmax: float = 62.0) -> list[dict]:
    """Every allowed cubic reflection below 2-theta = 2 tmax degrees, merged by N = h2 + k2 + l2."""
    nmax = int((2.0 * a * math.sin(tmax * PI / 180.0) / lam) ** 2) + 1
    out = []
    for n in range(1, nmax + 1):
        mult = 0
        hit = None
        seen = set()
        r = int(math.sqrt(n)) + 1
        for h in range(-r, r + 1):
            for k in range(-r, r + 1):
                for l in range(-r, r + 1):
                    if h * h + k * k + l * l != n:
                        continue
                    key = (h, k, l)
                    if key in seen:
                        continue
                    seen.add(key)
                    mult += 1
                    if hit is None:
                        hit = (abs(h), abs(k), abs(l))
        if not mult:
            continue
        h, k, l = hit
        par = (h % 2, k % 2, l % 2)
        allsame = par[0] == par[1] == par[2]
        s = h + k + l
        f2 = None
        if ltype == 2:                                  # body-centred: h + k + l even
            f2 = 4.0 if s % 2 == 0 else None
        elif ltype == 3:                                # face-centred: all odd or all even
            f2 = 16.0 if allsame else None
        elif ltype == 4:                                # diamond: FCC and h + k + l not 4n + 2
            if allsame:
                if par[0] == 1:
                    f2 = 32.0
                elif s % 4 == 0:
                    f2 = 64.0
        elif ltype == 5:                                # rock salt: |F|^2 = 16 (f1 +- f2)^2
            if allsame:
                f2 = 16.0 * ((z1 + z2) ** 2 if par[0] == 0 else (z1 - z2) ** 2)
        if f2 is None:
            continue
        out.append({"N": n, "m": mult, "f2": f2, "hkl": [h, k, l]})
    return out


class Xrd(_Base):
    """A powder diffractometer (Bragg-Brentano, Cu K-alpha by default) on a cubic powder of lattice parameter a.
    Positions are Bragg's law 2 d sin(theta) = lam with d = a / sqrt(h2 + k2 + l2), and only the reflections the
    structure factor allows appear (BCC: h+k+l even; FCC: h,k,l unmixed; diamond: also h+k+l != 4n+2; rock salt:
    the two-atom basis makes odd lines weak). Each line is a Gaussian of full width beta (2-theta, radians):
    beta_sample = K lam / (L cos(theta)) + 4 eps tan(theta) (size and strain), added in quadrature to the
    instrument width binst. Relative heights use m |F|^2 times the Lorentz-polarisation factor and a smooth
    scattering-factor fall-off: a MODEL, good for positions and widths, not for refining occupancies."""

    PARAMS = {"tth": 30.0, "lam": 1.5406e-10, "a": 4.0495e-10, "ltype": 3.0, "Z1": 13.0, "Z2": 0.0,
              "Lx": 2.0e-7, "eps": 0.0, "binst": 0.1, "K": 0.9, "bg": 40.0, "I0": 10000.0}
    VARS = ["t", "I", "tth", "d"]

    @staticmethod
    def peaks(p: dict) -> list[dict]:
        lam, a = p["lam"], p["a"]
        out = []
        for r in _hkl_list(int(round(p["ltype"])), p["Z1"], p["Z2"], lam, a):
            s = lam * math.sqrt(r["N"]) / (2.0 * a)
            if s >= 1.0:
                continue
            th = math.asin(s)
            tth = 2.0 * th * 180.0 / PI
            if tth > 125.0:
                continue
            bs = p["K"] * lam / (p["Lx"] * math.cos(th)) + 4.0 * p["eps"] * math.tan(th)
            bi = p["binst"] * PI / 180.0
            beta = math.sqrt(bs * bs + bi * bi) * 180.0 / PI              # FWHM in degrees of 2-theta
            sl = s / lam * 1e-10                                          # sin(theta)/lambda in 1/angstrom
            ff = math.exp(-5.0 * sl * sl)                                 # smooth fall of f(theta)
            lp = (1.0 + math.cos(2.0 * th) ** 2) / (math.sin(th) ** 2 * math.cos(th))
            amp = r["m"] * r["f2"] * ff * ff * lp
            out.append({"N": r["N"], "hkl": r["hkl"], "tth": tth, "beta": beta, "amp": amp, "th": th})
        top = max([q["amp"] for q in out] or [1.0])
        for q in out:
            q["amp"] = q["amp"] / top
        return out

    @staticmethod
    def _noise(x: float) -> float:
        i = int(math.floor(x * 50.0 + 0.5))
        s = ((i + 1000) * 2654435761) % 2147483647
        s = (s * 16807) % 2147483647
        s = (s * 16807) % 2147483647
        return s / 2147483647.0 - 0.5

    @staticmethod
    def counts(x: float, p: dict, pk: list[dict] | None = None) -> float:
        pk = pk if pk is not None else Xrd.peaks(p)
        tot = 0.0
        for q in pk:
            z = (x - q["tth"]) / q["beta"]
            if abs(z) < 6.0:
                tot += q["amp"] * math.exp(-4.0 * LN2 * z * z)
        n = Xrd._noise(x)
        return p["bg"] * (1.0 + 0.2 * n) + p["I0"] * tot * (1.0 + 0.006 * n)

    @staticmethod
    def view(s, p, cfg=None):
        th = p["tth"] * PI / 360.0
        return {"t": s.get("t", 0.0), "I": Xrd.counts(p["tth"], p), "tth": p["tth"],
                "d": p["lam"] / (2.0 * math.sin(th)) if th > 0 else 0.0}

    @staticmethod
    def seq(ltype: int) -> list[int]:
        """The allowed N sequence of a lattice type (first 14 lines)."""
        return [r["N"] for r in _hkl_list(ltype, 1.0, 0.0, 1.5406e-10, 12e-10, 85.0)][:14]

    @staticmethod
    def scan_peaks(p: dict, t0: float = 20.0, t1: float = 120.0, dt: float = 0.02) -> list[dict]:
        """Find the lines in a scan: local maxima above 3 % of the strongest, centroid of the top half, FWHM by
        linear interpolation at half height above the background."""
        n = int(round((t1 - t0) / dt))
        pk = Xrd.peaks(p)
        xs = [t0 + dt * i for i in range(n + 1)]
        ys = [Xrd.counts(x, p, pk) for x in xs]
        ymax = max(ys)
        out = []
        i = 3
        while i < n - 3:
            w = ys[i - 3:i + 4]
            if ys[i] == max(w) and ys[i] > p["bg"] * 1.5 + 0.03 * ymax:
                half = p["bg"] + (ys[i] - p["bg"]) / 2.0
                lo = i
                while lo > 0 and ys[lo] > half:
                    lo -= 1
                hi = i
                while hi < n and ys[hi] > half:
                    hi += 1
                xl = xs[lo] + (half - ys[lo]) * (xs[lo + 1] - xs[lo]) / (ys[lo + 1] - ys[lo])
                xh = xs[hi - 1] + (ys[hi - 1] - half) * (xs[hi] - xs[hi - 1]) / (ys[hi - 1] - ys[hi])
                sw = sx = 0.0
                for j in range(lo + 1, hi):
                    wgt = ys[j] - half
                    sw += wgt
                    sx += wgt * xs[j]
                out.append({"tth": sx / sw, "fwhm": xh - xl, "height": ys[i]})
                i = hi + 1
            else:
                i += 1
        return out

    @staticmethod
    def index(peaks: list[dict], lam: float) -> dict:
        """Index a pattern: for each candidate lattice (BCC, FCC, diamond) match sin^2(theta) ratios to its allowed
        N sequence; the best fit wins. Returns the type, the N of each line and a from the highest-angle line."""
        if not peaks:
            return {"ltype": 0, "N": [], "a": 0.0}
        s2 = [math.sin(q["tth"] * PI / 360.0) ** 2 for q in peaks]
        best = None
        for lt in (2, 3, 4):
            sq = Xrd.seq(lt)
            ns = []
            bad = 0.0
            for v in s2:
                target = v / s2[0] * sq[0]
                nn = min(sq, key=lambda x: abs(x - target))
                bad += abs(nn - target) / max(nn, 1)
                ns.append(nn)
            if len(set(ns)) != len(ns):
                continue
            missing = sum(1 for x in sq if ns[0] < x < ns[-1] and x not in ns)
            score = bad + 0.05 * missing
            if best is None or score < best["bad"] - 1e-12:
                best = {"ltype": lt, "N": ns, "bad": score}
        if best is None:
            return {"ltype": 0, "N": [], "a": 0.0}
        a = lam * math.sqrt(best["N"][-1]) / (2.0 * math.sqrt(s2[-1]))
        return {"ltype": best["ltype"], "N": best["N"], "a": a}

    @staticmethod
    def measure(p, cfg=None):
        """A full 20-120 degree scan, the lines found and indexed, a from the highest-angle line, and the
        Williamson-Hall fit of the instrument-corrected widths: beta cos(theta) = K lam / L + 4 eps sin(theta)."""
        pks = Xrd.scan_peaks(p)
        ix = Xrd.index(pks, p["lam"])
        bi = p["binst"] * PI / 180.0
        pts = []
        for q in pks:
            th = q["tth"] * PI / 360.0
            bo = q["fwhm"] * PI / 180.0
            if bo > bi:
                bsam = math.sqrt(bo * bo - bi * bi)
                pts.append([4.0 * math.sin(th), bsam * math.cos(th)])
        m, c = _line(pts)
        return {"a": ix["a"], "ltype": float(ix["ltype"]), "nlines": float(len(pks)),
                "L_wh": p["K"] * p["lam"] / c if c > 0 else 0.0, "eps_wh": m}


def _xrd_a(p: dict) -> float:
    return p["a"]


def _xrd_L(p: dict) -> float:
    return p["Lx"]


# ====================================================================================== Quincke susceptibility
class Quincke(_Base):
    """A liquid in a U-tube with one limb between the pole pieces of an electromagnet. A volume susceptibility chi
    pulls the liquid into the field: h = chi B^2 / (2 mu0 rho g). B = kB I from the coil current I. The solution
    adds the solvent and the solute: chi = chiw + 4 pi chim (c / 1000), with chim the molar susceptibility in
    cm^3/mol (cgs, in units of 1e-6) and c the molarity."""

    PARAMS = {"I": 0.0, "kB": 0.4, "c": 1.0, "chim": 13660.0, "chiw": -9.05e-6, "rho": 1100.0}
    VARS = ["t", "B", "h", "h_mm", "chi"]

    @staticmethod
    def chi(p: dict) -> float:
        return p["chiw"] + 4.0 * PI * p["chim"] * 1e-6 * p["c"] / 1000.0

    @staticmethod
    def rise(p: dict) -> float:
        b = p["kB"] * p["I"]
        return Quincke.chi(p) * b * b / (2.0 * MU0 * p["rho"] * GRAV)

    @staticmethod
    def view(s, p, cfg=None):
        h = Quincke.rise(p)
        return {"t": s.get("t", 0.0), "B": p["kB"] * p["I"], "h": h, "h_mm": h * 1e3, "chi": Quincke.chi(p)}

    @staticmethod
    def measure(p, cfg=None):
        q = dict(p, I=1.5)
        b = q["kB"] * q["I"]
        chi = 2.0 * MU0 * p["rho"] * GRAV * Quincke.rise(q) / (b * b)
        chim = (chi - p["chiw"]) * 1000.0 / (4.0 * PI * p["c"]) * 1e6 if p["c"] > 0 else 0.0
        return {"chi": chi, "chim": chim, "h": Quincke.rise(p)}


def _quincke_chi(p: dict) -> float:
    return Quincke.chi(p)


# ====================================================================================== vacuum pump-down
class Vacuum(_Base):
    """A vessel of volume V pumped at speed S with an outgassing load Q (Pa m3/s). The pressure obeys
    V dP/dt = -S P + Q, so P = Pu + (P0 - Pu) exp(-S t / V) with the ultimate pressure Pu = Q / S. Gaede's equation
    S = (V / t) ln[(P1 - Pu) / (P2 - Pu)] gives the speed from two readings. A Pirani gauge reads true pressure
    only between about 0.1 Pa and 1 kPa (it saturates above and floors below); an ionisation gauge reads from
    1e-6 Pa to 0.1 Pa and is interlocked off above that."""

    PARAMS = {"t": 0.0, "V": 0.05, "S": 1.39e-3, "Q": 7.0e-4, "P0": 101325.0, "Psat": 5000.0}
    VARS = ["t", "P", "Ppir", "Pion", "Pu"]

    @staticmethod
    def press(t: float, p: dict) -> float:
        pu = p["Q"] / p["S"]
        return pu + (p["P0"] - pu) * math.exp(-p["S"] * t / p["V"])

    @staticmethod
    def pirani(P: float, p: dict) -> float:
        r = P / (1.0 + P / p["Psat"])
        return r if r > 0.1 else 0.1

    @staticmethod
    def ion(P: float, p: dict) -> float:
        if P > 0.1:
            return -1.0
        return P if P > 1e-6 else 1e-6

    @staticmethod
    def view(s, p, cfg=None):
        t = p["t"] if p["t"] else s.get("t", 0.0)
        P = Vacuum.press(t, p)
        return {"t": t, "P": P, "Ppir": Vacuum.pirani(P, p), "Pion": Vacuum.ion(P, p), "Pu": p["Q"] / p["S"]}

    @staticmethod
    def _time_at(P: float, p: dict) -> float:
        pu = p["Q"] / p["S"]
        return -p["V"] / p["S"] * math.log((P - pu) / (p["P0"] - pu))

    @staticmethod
    def measure(p, cfg=None):
        """The pumping speed from Gaede's equation between the times the (true) pressure passes 500 and 5 pu."""
        pu = p["Q"] / p["S"]
        p1, p2 = 500.0, max(5.0 * pu, 5.0)
        if p2 >= p1 or pu >= p2:
            p2 = max(pu * 4.0, 1e-9)
        lo, hi = 0.0, 1e6
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if Vacuum.press(mid, p) > p1:
                lo = mid
            else:
                hi = mid
        t1 = 0.5 * (lo + hi)
        lo, hi = 0.0, 1e6
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if Vacuum.press(mid, p) > p2:
                lo = mid
            else:
                hi = mid
        t2 = 0.5 * (lo + hi)
        s = p["V"] / (t2 - t1) * math.log((p1 - pu) / (p2 - pu))
        return {"S": s, "Pu": Vacuum.ion(Vacuum.press(1e6, p), p) if pu < 0.1 else Vacuum.pirani(Vacuum.press(1e6, p), p),
                "t1": t1, "t2": t2}


def _vac_S(p: dict) -> float:
    return p["S"]


def _vac_Pu(p: dict) -> float:
    return p["Q"] / p["S"]


# ====================================================================================== Langmuir probe
class Langmuir(_Base):
    """A cylindrical Langmuir probe (area Ap) in a plasma of electron density ne, electron temperature Te (eV),
    plasma potential Vp and ion mass M (atomic mass units). Collected current (electrons positive):
    I = Ies exp((V - Vp) / Te) - Iis for V < Vp, I = Ies - Iis above it, with the electron current
    Ies = e ne Ap sqrt(e Te / 2 pi me) and the Bohm ion current Iis = 0.61 e ne Ap sqrt(e Te / M)."""

    PARAMS = {"V": 0.0, "Te": 3.0, "Vp": 8.0, "ne": 1.0e16, "Ap": 2.0e-6, "M": 39.948}
    VARS = ["t", "I", "I_uA", "V", "Ies", "Iis", "Vf"]

    @staticmethod
    def ies(p: dict) -> float:
        return QE * p["ne"] * p["Ap"] * math.sqrt(QE * p["Te"] / (2.0 * PI * ME))

    @staticmethod
    def iis(p: dict) -> float:
        return 0.61 * QE * p["ne"] * p["Ap"] * math.sqrt(QE * p["Te"] / (p["M"] * AMU))

    @staticmethod
    def cur(v: float, p: dict) -> float:
        ie = Langmuir.ies(p) * (math.exp((v - p["Vp"]) / p["Te"]) if v < p["Vp"] else 1.0)
        return ie - Langmuir.iis(p)

    @staticmethod
    def view(s, p, cfg=None):
        i = Langmuir.cur(p["V"], p)
        return {"t": s.get("t", 0.0), "I": i, "I_uA": i * 1e6, "V": p["V"], "Ies": Langmuir.ies(p),
                "Iis": Langmuir.iis(p), "Vf": p["Vp"] + p["Te"] * math.log(Langmuir.iis(p) / Langmuir.ies(p))}

    @staticmethod
    def measure(p, cfg=None):
        """Te from the slope of ln(I + Iis) against V in the retarding region, between Vp - 8 Te/3 and Vp - 2/3 Te."""
        v1, v2 = p["Vp"] - 2.0 * p["Te"], p["Vp"] - 0.5 * p["Te"]
        i1 = Langmuir.cur(v1, p) + Langmuir.iis(p)
        i2 = Langmuir.cur(v2, p) + Langmuir.iis(p)
        te = (v2 - v1) / math.log(i2 / i1)
        return {"Te": te, "Ies": Langmuir.ies(p), "I": Langmuir.cur(p["V"], p)}


def _lang_Te(p: dict) -> float:
    return p["Te"]


# ====================================================================================== registry
KERNELS: dict[str, Any] = {
    "msc_metal": Metal, "msc_seebeck": Seebeck, "msc_ionic": Ionic, "msc_super": Super, "msc_magres": Magres,
    "msc_ferro": Ferro, "msc_curie": Curie, "msc_lc": LiquidCrystal, "msc_diel": Dielectric, "msc_loop": Loop,
    "msc_xrd": Xrd, "msc_quincke": Quincke, "msc_vac": Vacuum, "msc_langmuir": Langmuir,
}
FAMILY = {k: ("em" if k not in ("msc_xrd", "msc_lc") else "optics") for k in KERNELS}
FAMILY["msc_vac"] = "thermo"
FAMILY["msc_metal"] = "thermo"

TEXTBOOK = {
    "msc_alpha": _metal_alpha, "msc_S": _seebeck_S, "msc_Ea": _ionic_Ea, "msc_Tc_sc": _super_Tc,
    "msc_mu": _magres_mu, "msc_Tc_fe": _ferro_Tc, "msc_Tc_cu": _curie_Tc, "msc_Tni": _lc_Tni, "msc_er": _diel_er,
    "msc_Hc": _loop_Hc, "msc_a": _xrd_a, "msc_L": _xrd_L, "msc_chi": _quincke_chi, "msc_Spump": _vac_S,
    "msc_Pu": _vac_Pu, "msc_Te": _lang_Te,
}


def _wh(rows, p):
    """Williamson-Hall on rows {x = 4 sin(theta), y = beta cos(theta)} - returns the size L from the intercept."""
    m, c = _line(_rows(rows, ["x", "y"]))
    return p["K"] * p["lam"] / c if c > 0 else 0.0


def _langte(rows, p):
    pts = _rows(rows, ["V", "I"])
    if len(pts) < 3:
        return 0.0
    ion = -min(i for _, i in pts)
    imax = max(i for _, i in pts) + ion
    sel = [[v, math.log(i + ion)] for v, i in pts if 0.02 * imax < i + ion < 0.5 * imax]
    m = _slope(sel)
    return 1.0 / m if m > 0 else 0.0


def _cw(rows, p):
    """Curie-Weiss: 1 / eps against T is a line; it meets zero at the Curie-Weiss temperature."""
    m, c = _line([[t, 1.0 / e] for t, e in _rows(rows, ["T", "eps"]) if e > 0])
    return -c / m if m != 0 else 0.0


CALCS: dict[str, dict] = {
    "msc_alpha": {"label": "temperature coefficient", "unit": "1/K", "needs": ["T", "R"],
                  "fn": lambda rows, p: (lambda mc: mc[0] / (mc[1] + mc[0] * p["Tref"]) if (mc[1] + mc[0] * p["Tref"]) != 0 else 0.0)(
                      _line(_rows(rows, ["T", "R"])))},
    "msc_seeb": {"label": "Seebeck coefficient", "unit": "uV/K", "needs": ["dT", "V"],
                 "fn": lambda rows, p: _slope(_rows(rows, ["dT", "V"]))},
    "msc_Eact": {"label": "activation energy", "unit": "eV", "needs": ["invT", "lnsT"],
                 "fn": lambda rows, p: -KB * _slope(_rows(rows, ["invT", "lnsT"])) / QE},
    "msc_mob": {"label": "mobility", "unit": "m2/Vs", "needs": ["B2", "R"],
                "fn": lambda rows, p: (lambda mc: math.sqrt(mc[0] / (p["xi"] * mc[1])) if mc[1] != 0 and mc[0] / (p["xi"] * mc[1]) > 0 else 0.0)(
                    _line(_rows(rows, ["B2", "R"])))},
    "msc_cw": {"label": "Curie-Weiss temperature", "unit": "K", "needs": ["T", "eps"], "fn": _cw},
    "msc_wh": {"label": "crystallite size", "unit": "m", "needs": ["x", "y"], "fn": _wh},
    "msc_chiq": {"label": "volume susceptibility", "unit": "", "needs": ["B2", "h"],
                 "fn": lambda rows, p: 2.0 * MU0 * p["rho"] * GRAV * _slope(_rows(rows, ["B2", "h"]))},
    "msc_Tel": {"label": "electron temperature", "unit": "eV", "needs": ["V", "I"], "fn": _langte},
    "msc_pump": {"label": "pumping speed", "unit": "m3/s", "needs": ["t", "lnP"],
                 "fn": lambda rows, p: -p["V"] * _slope(_rows(rows, ["t", "lnP"]))},
}
