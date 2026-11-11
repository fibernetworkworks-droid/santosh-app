"""Kernel pack: B.Sc. oscillation, elasticity, heat-flow and harmonic-analysis benches (undergraduate Prayogshala, wave 7).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/ug_mech_w7.js` (same formulas, same order of operations, so both give the same numbers).

Kernels, with the textbook relation each one is checked against (1 %):
    w7_pend      simple / bar pendulum, damped, any amplitude   T = 2 pi sqrt(Leq / g) (1 + th0^2 / 16);  A = A0 exp(-gam t)
    w7_kater     Kater's reversible pendulum                    g = 8 pi^2 / ((T1^2 + T2^2)/(h1 + h2) + (T1^2 - T2^2)/(h1 - h2))
    w7_coupled   two coupled pendulums / two coupled gliders    kappa = (w2^2 - w1^2) / (w2^2 + w1^2)
    w7_spring    loaded helical spring, alone / series / parallel   T = 2 pi sqrt((m + ms/3) / k),  k = eta r^4 / (4 N R^3)
    w7_torsion   Maxwell's needle and Searle's two bars         eta = 2 pi l (ms - mh) L^2 / (r^4 (T1^2 - T2^2));  sigma = T2^2 / (2 T1^2) - 1
    w7_stefan    tungsten lamp as a radiator                    P = e sigma A (T^4 - T0^4)
    w7_cbarnes   Callendar and Barnes' constant-flow tube       J = (V1 I1 - V2 I2) / ((m1 - m2) s dT)
    w7_angstrom  Angstrom's periodically heated bar             D = (x2 - x1)^2 / (2 dt ln(A1 / A2))
    w7_cool      two calorimeters cooling (method of cooling)   (ml cl + W) / (mw cw + W) = tl / tw
    w7_fourier   harmonics of a square / triangular / clipped wave   b_n from the Fourier integral
Everything is SI unless a parameter says otherwise, and deterministic: no randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi


def _sub(dt: float, h: float) -> tuple[int, float]:
    n = max(1, int(math.ceil(dt / h - 1e-9)))
    return n, dt / n


def _rk4(f, y: list[float], h: float) -> list[float]:
    k1 = f(y)
    k2 = f([y[i] + h / 2 * k1[i] for i in range(len(y))])
    k3 = f([y[i] + h / 2 * k2[i] for i in range(len(y))])
    k4 = f([y[i] + h * k3[i] for i in range(len(y))])
    return [y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(len(y))]


def _period(f, y0: list[float], h: float, tmax: float) -> float:
    """The full period from two successive downward zero crossings of y[0] (linear interpolation between steps)."""
    y = list(y0)
    t = 0.0
    cross: list[float] = []
    while t < tmax and len(cross) < 2:
        y2 = _rk4(f, y, h)
        if y[0] > 0 and y2[0] <= 0:
            cross.append(t + h * y[0] / (y[0] - y2[0]))
        y = y2
        t = t + h
    return cross[1] - cross[0] if len(cross) == 2 else 0.0


def _decay(f, y0: list[float], h: float, npk: int, tmax: float) -> float:
    """The amplitude decay rate from the first and the npk-th maximum of y[0] on the positive side:
    gam = ln(A_first / A_last) / (t_last - t_first)."""
    y = list(y0)
    t = 0.0
    pk: list[list[float]] = []
    while t < tmax and len(pk) < npk:
        y2 = _rk4(f, y, h)
        if y[1] > 0 and y2[1] <= 0 and y[0] > 0:
            fr = y[1] / (y[1] - y2[1])
            pk.append([t + h * fr, y[0] + fr * (y2[0] - y[0])])
        y = y2
        t = t + h
    if len(pk) < 2 or pk[-1][1] <= 0 or pk[-1][0] <= pk[0][0]:
        return 0.0
    return math.log(pk[0][1] / pk[-1][1]) / (pk[-1][0] - pk[0][0])


# ============================================================================== simple / bar pendulum, damped
def _pend_leq(p: dict) -> float:
    """Length of the equivalent simple pendulum: L for a bob on a thread, (k^2 + h^2) / h for a uniform bar."""
    if p["kind"] < 0.5:
        return p["L"]
    return (p["Lb"] * p["Lb"] / 12 + p["h"] * p["h"]) / p["h"] if p["h"] > 0 else 0.0


def _pend_f(p: dict):
    c = p["g"] / _pend_leq(p)
    b = 2 * p["gam"]

    def f(y):
        return [y[1], -c * math.sin(y[0]) - b * y[1]]
    return f


def _pend_T0(p: dict) -> float:
    return 2 * PI * math.sqrt(_pend_leq(p) / p["g"])


def _pend_lim_series(p: dict) -> float:
    """Amplitude at which T = (1 + eps) T0, from T = T0 (1 + th^2/16 + 11 th^4/3072)."""
    a = 11.0 / 3072.0
    b = 1.0 / 16.0
    return math.sqrt((-b + math.sqrt(b * b + 4 * a * p["eps"])) / (2 * a))


class Pendulum:
    """A bob on a thread (kind 0) or a uniform bar on a knife edge (kind 1), with a light damper:
        th'' + 2 gam th' + (g / Leq) sin th = 0.
    `mode` chooses what `measure` works out: 0 the period, 1 the decay rate, 2 the SHM amplitude limit."""

    PARAMS = {"kind": 0.0, "L": 1.0, "Lb": 1.0, "h": 0.3, "g": 9.8, "th0": 0.0873, "gam": 0.0, "eps": 0.01, "mode": 0.0}
    VARS = ["t", "th", "th_deg", "om", "Leq", "T0"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["th0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _pend_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "th": s["y"][0], "th_deg": s["y"][0] * 180 / PI, "om": s["y"][1], "Leq": _pend_leq(p),
                "T0": _pend_T0(p)}

    @staticmethod
    def measure(p, cfg=None):
        f = _pend_f(p)
        T = _period(f, [p["th0"], 0.0], 0.0005, 200.0)
        out = {"T": T, "T0": _pend_T0(p), "g": 4 * PI * PI * _pend_leq(p) / (T * T) if T > 0 else 0.0, "gam": 0.0, "th_lim": 0.0}
        if p["mode"] > 0.5 and p["mode"] < 1.5:
            out["gam"] = _decay(f, [p["th0"], 0.0], 0.001, 11, 400.0)
        if p["mode"] > 1.5:
            q = dict(p)
            q["gam"] = 0.0
            fq = _pend_f(q)
            Tsmall = _period(fq, [0.02, 0.0], 0.001, 200.0)
            lo = 0.05
            hi = 1.2
            for _ in range(14):
                mid = (lo + hi) / 2
                if _period(fq, [mid, 0.0], 0.001, 200.0) > (1 + p["eps"]) * Tsmall:
                    hi = mid
                else:
                    lo = mid
            out["th_lim"] = (lo + hi) / 2
        return out


# ============================================================================== Kater's reversible pendulum
def _kater_f(p: dict, h: float):
    c = p["g"] * h / (p["k2"] + h * h)

    def f(y):
        return [y[1], -c * math.sin(y[0])]
    return f


class Kater:
    """A rigid bar with two knife edges K1, K2 facing each other, h1 and h2 from the centre of gravity (k2 = the square
    of the radius of gyration about it). `side` 0 hangs it from K1, 1 from K2:  T = 2 pi sqrt((k2 + h^2) / (g h))."""

    PARAMS = {"h1": 0.60, "h2": 0.35, "k2": 0.21, "g": 9.8, "th0": 0.05, "side": 0.0}
    VARS = ["t", "th", "th_deg", "om", "T_calc"]

    @staticmethod
    def hh(p):
        return p["h1"] if p["side"] < 0.5 else p["h2"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["th0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _kater_f(p, Kater.hh(p))
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        h = Kater.hh(p)
        return {"t": s["t"], "th": s["y"][0], "th_deg": s["y"][0] * 180 / PI, "om": s["y"][1],
                "T_calc": 2 * PI * math.sqrt((p["k2"] + h * h) / (p["g"] * h))}

    @staticmethod
    def measure(p, cfg=None):
        T1 = _period(_kater_f(p, p["h1"]), [p["th0"], 0.0], 0.0005, 200.0)
        T2 = _period(_kater_f(p, p["h2"]), [p["th0"], 0.0], 0.0005, 200.0)
        den = (T1 * T1 + T2 * T2) / (p["h1"] + p["h2"]) + (T1 * T1 - T2 * T2) / (p["h1"] - p["h2"])
        return {"T1": T1, "T2": T2, "g": 8 * PI * PI / den if den > 0 else 0.0}


# ============================================================================== two coupled oscillators
def _cpl_w(p: dict) -> list[float]:
    """Squares of the two normal-mode angular frequencies: in phase, then out of phase."""
    if p["kind"] < 0.5:
        w1 = p["g"] / p["L"]
        w2 = w1 + 2 * p["kc"] * p["a"] * p["a"] / (p["m"] * p["L"] * p["L"])
    else:
        w1 = p["k"] / p["m"]
        w2 = (p["k"] + 2 * p["kc"]) / p["m"]
    return [w1, w2]


def _cpl_f(p: dict):
    w = _cpl_w(p)
    w1 = w[0]
    c = (w[1] - w[0]) / 2
    b = 2 * p["gam"]

    def f(y):
        return [y[1], -w1 * y[0] - c * (y[0] - y[2]) - b * y[1], y[3], -w1 * y[2] - c * (y[2] - y[0]) - b * y[3]]
    return f


def _cpl_y0(p: dict, mode: float) -> list[float]:
    if mode < 0.5:
        return [p["A0"], 0.0, p["A0"], 0.0]
    if mode < 1.5:
        return [p["A0"], 0.0, -p["A0"], 0.0]
    return [p["A0"], 0.0, 0.0, 0.0]


class Coupled:
    """Two equal pendulums joined by a light spring a from the pivots (kind 0), or two equal gliders between three
    springs on an air track (kind 1). `mode` 0 starts them in phase, 1 out of phase, 2 with only the first displaced
    (beats). Coordinates are angles (rad) for the pendulums and displacements (m) for the gliders."""

    PARAMS = {"kind": 0.0, "L": 0.6, "g": 9.8, "a": 0.3, "m": 0.2, "kc": 2.0, "k": 4.0, "gam": 0.0, "mode": 0.0, "A0": 0.08}
    VARS = ["t", "x1", "x2", "v1", "v2", "w1", "w2"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": _cpl_y0(p, p["mode"])}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _cpl_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        w = _cpl_w(p)
        return {"t": s["t"], "x1": s["y"][0], "x2": s["y"][2], "v1": s["y"][1], "v2": s["y"][3],
                "w1": math.sqrt(w[0]), "w2": math.sqrt(w[1])}

    @staticmethod
    def measure(p, cfg=None):
        f = _cpl_f(p)
        T1 = _period(f, _cpl_y0(p, 0.0), 0.0005, 200.0)
        T2 = _period(f, _cpl_y0(p, 1.0), 0.0005, 200.0)
        kap = (T1 * T1 - T2 * T2) / (T1 * T1 + T2 * T2) if T1 > 0 and T2 > 0 else 0.0
        gam = _decay(f, _cpl_y0(p, 0.0), 0.001, 11, 400.0) if p["gam"] > 0 else 0.0
        return {"T1": T1, "T2": T2, "kappa": kap, "Tb": T1 * T2 / (T1 - T2) if T1 > T2 else 0.0, "gam": gam}


# ============================================================================== loaded helical spring(s)
def _spr_k1(p: dict) -> float:
    """Stiffness of the first spring: given directly, or from its wire and coil (geo = 1): k = eta r^4 / (4 N R^3)."""
    if p["geo"] > 0.5:
        return p["eta"] * p["rw"] ** 4 / (4 * p["Nt"] * p["Rc"] ** 3)
    return p["k1"]


def _spr_keff(p: dict) -> float:
    k1 = _spr_k1(p)
    if p["mode"] < 0.5:
        return k1
    if p["mode"] < 1.5:
        return k1 * p["k2"] / (k1 + p["k2"])
    return k1 + p["k2"]


class SpringLoad:
    """A mass m on a helical spring of mass ms (alone, mode 0), or on two light springs in series (1) / parallel (2).
    Static: extension = m g / k. Dynamic: x'' = -(k / (m + ms/3)) x about the rest position."""

    PARAMS = {"k1": 20.0, "k2": 30.0, "mode": 0.0, "ms": 0.03, "m": 0.2, "g": 9.8, "x0": 0.02, "geo": 0.0,
              "eta": 7.93e10, "rw": 0.0005, "Rc": 0.01, "Nt": 60.0}
    VARS = ["t", "x", "v", "ext", "keff"]

    @staticmethod
    def f(p):
        c = _spr_keff(p) / (p["m"] + p["ms"] / 3)

        def f(y):
            return [y[1], -c * y[0]]
        return f

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["x0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = SpringLoad.f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        k = _spr_keff(p)
        return {"t": s["t"], "x": s["y"][0], "v": s["y"][1], "ext": p["m"] * p["g"] / k, "keff": k}

    @staticmethod
    def measure(p, cfg=None):
        T = _period(SpringLoad.f(p), [p["x0"], 0.0], 0.0002, 100.0)
        k = 4 * PI * PI * (p["m"] + p["ms"] / 3) / (T * T) if T > 0 else 0.0
        return {"T": T, "ext": p["m"] * p["g"] / _spr_keff(p), "k": k,
                "eta": 4 * p["Nt"] * p["Rc"] ** 3 * k / p["rw"] ** 4}


# ============================================================================== Maxwell's needle / Searle's two bars
def _tor_I(p: dict, pos: float) -> float:
    if p["kind"] < 0.5:
        mo = p["ms"] if pos < 0.5 else p["mh"]
        mi = p["mh"] if pos < 0.5 else p["ms"]
        return p["I0"] + 2 * mo * (3 * p["Ln"] / 8) ** 2 + 2 * mi * (p["Ln"] / 8) ** 2
    return p["Mb"] * (p["Lbar"] * p["Lbar"] + p["wb"] * p["wb"]) / 12


def _tor_C(p: dict, pos: float) -> float:
    """Restoring couple per radian: torsion of the wire (pi eta r^4 / 2l), or for Searle's bars swinging in the
    horizontal plane (pos 0) the bending of the wire (pi Y r^4 / 2l)."""
    mod = p["Y"] if (p["kind"] > 0.5 and pos < 0.5) else p["eta"]
    return PI * mod * p["rw"] ** 4 / (2 * p["lw"])


def _tor_f(p: dict, pos: float):
    c = _tor_C(p, pos) / _tor_I(p, pos)

    def f(y):
        return [y[1], -c * y[0]]
    return f


class TorsionRig:
    """kind 0, Maxwell's needle: a hollow tube of length Ln on a wire, holding two solid (ms) and two hollow (mh)
    cylinders each Ln/4 long; pos 0 = solids outside, 1 = hollows outside.
    kind 1, Searle's apparatus: two equal bars joined at their middles by the wire; pos 0 = the bars swing in a
    horizontal plane and bend the wire (Young's modulus), 1 = one bar clamped, the other twists the wire (rigidity)."""

    PARAMS = {"kind": 0.0, "eta": 8.22e10, "Y": 2.119e11, "rw": 0.0004, "lw": 0.5, "Ln": 0.4, "ms": 0.25, "mh": 0.06,
              "I0": 0.002, "Mb": 0.45, "Lbar": 0.3, "wb": 0.012, "pos": 0.0, "th0": 0.2}
    VARS = ["t", "th", "th_deg", "om", "T_calc"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["th0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _tor_f(p, p["pos"])
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "th": s["y"][0], "th_deg": s["y"][0] * 180 / PI, "om": s["y"][1],
                "T_calc": 2 * PI * math.sqrt(_tor_I(p, p["pos"]) / _tor_C(p, p["pos"]))}

    @staticmethod
    def measure(p, cfg=None):
        T1 = _period(_tor_f(p, 0.0), [p["th0"], 0.0], 0.0005, 400.0)
        T2 = _period(_tor_f(p, 1.0), [p["th0"], 0.0], 0.0005, 400.0)
        r4 = p["rw"] ** 4
        if p["kind"] < 0.5:
            eta = 2 * PI * p["lw"] * (p["ms"] - p["mh"]) * p["Ln"] * p["Ln"] / (r4 * (T1 * T1 - T2 * T2))
            return {"T1": T1, "T2": T2, "eta": eta, "Y": 0.0, "sigma": 0.0}
        inert = _tor_I(p, 0.0)
        return {"T1": T1, "T2": T2, "Y": 8 * PI * inert * p["lw"] / (T1 * T1 * r4),
                "eta": 8 * PI * inert * p["lw"] / (T2 * T2 * r4), "sigma": T2 * T2 / (2 * T1 * T1) - 1}


# ============================================================================== Stefan's law with a tungsten lamp
def _stef_T(p: dict, V: float) -> float:
    """Filament temperature at V volts: V^2 / R(T) = em sigma A (T^4 - T0^4), R = R0 (T / T0)^nR (bisection)."""
    lo = p["T0"]
    hi = 4000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        R = p["R0"] * (mid / p["T0"]) ** p["nR"]
        if V * V / R > p["em"] * p["sigma"] * p["A"] * (mid ** 4 - p["T0"] ** 4):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _stef_read(p: dict, V: float) -> list[float]:
    """What the meters give at V volts: the current, and from it the filament's R, T (from R) and P = V I."""
    T = _stef_T(p, V)
    R = p["R0"] * (T / p["T0"]) ** p["nR"]
    cur = V / R
    Tm = p["T0"] * ((V / cur) / p["R0"]) ** (1 / p["nR"])
    return [cur, V / cur, Tm, V * cur]


class StefanLamp:
    """A vacuum tungsten lamp: all the electrical power leaves the filament as radiation."""

    PARAMS = {"sigma": 5.670374e-8, "em": 0.35, "A": 2.0e-5, "T0": 300.0, "R0": 1.0, "nR": 1.2, "V": 6.0}
    VARS = ["t", "V", "I", "R", "T", "P"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        r = _stef_read(p, p["V"])
        return {"t": s["t"], "V": p["V"], "I": r[0], "R": r[1], "T": r[2], "P": r[3]}

    @staticmethod
    def measure(p, cfg=None):
        a = _stef_read(p, p["V"])
        b = _stef_read(p, 1.5 * p["V"])
        return {"sigma": a[3] / (p["em"] * p["A"] * (a[2] ** 4 - p["T0"] ** 4)),
                "n": math.log(b[3] / a[3]) / math.log(b[2] / a[2]), "T": a[2], "P": a[3], "I": a[0]}


# ============================================================================== Callendar and Barnes' continuous flow
def _cb_dT(p: dict, V: float, mdot: float) -> float:
    """Steady rise of the water: V^2 / Rh = J s mdot dT + hl dT  (mdot in g/s, s in cal/(g K), J in J/cal)."""
    return (V * V / p["Rh"]) / (p["J"] * p["s"] * mdot + p["hl"])


class CallendarBarnes:
    """Water flows steadily through a glass tube over a heater wire inside a vacuum jacket; two thermometers read the
    rise dT. The reading settles first order in time with the constant `tau`."""

    PARAMS = {"J": 4.1855, "s": 1.0, "hl": 0.25, "mdot": 1.5, "mdot2": 0.9, "V": 6.0, "Rh": 2.0, "Tin": 25.0, "tau": 40.0}
    VARS = ["t", "dT", "I", "P", "Tout"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "dT": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.05)
        tgt = _cb_dT(p, p["V"], p["mdot"])
        for _ in range(n):
            s["dT"] = s["dT"] + (tgt - s["dT"]) * (h / p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "dT": s["dT"], "I": p["V"] / p["Rh"], "P": p["V"] * p["V"] / p["Rh"], "Tout": p["Tin"] + s["dT"]}

    @staticmethod
    def measure(p, cfg=None):
        """Run 1 at (V, mdot). Run 2 at mdot2 with the voltage turned (bisection) until the rise is the same."""
        d1 = _cb_dT(p, p["V"], p["mdot"])
        lo = 0.0
        hi = p["V"] * 3
        for _ in range(50):
            mid = (lo + hi) / 2
            if _cb_dT(p, mid, p["mdot2"]) < d1:
                lo = mid
            else:
                hi = mid
        V2 = (lo + hi) / 2
        P1 = p["V"] * p["V"] / p["Rh"]
        P2 = V2 * V2 / p["Rh"]
        return {"J": (P1 - P2) / ((p["mdot"] - p["mdot2"]) * p["s"] * d1), "dT": d1, "V2": V2, "P1": P1, "P2": P2}


# ============================================================================== Angstrom's method
def _ang_ab(p: dict) -> list[float]:
    """Decay constant a and phase constant b of the temperature wave: (a + i b)^2 = (mu + i w) / D."""
    w = 2 * PI / p["tau"]
    r = math.sqrt(p["mu"] * p["mu"] + w * w) / p["D"]
    return [math.sqrt((r + p["mu"] / p["D"]) / 2), math.sqrt((r - p["mu"] / p["D"]) / 2), w]


def _ang_T(p: dict, x: float, t: float) -> float:
    ab = _ang_ab(p)
    return p["Tm"] + p["A0"] * math.exp(-ab[0] * x) * math.sin(ab[2] * t - ab[1] * x)


def _ang_scan(p: dict, x: float) -> list[float]:
    """One heating period sampled 3600 times: the amplitude (half the swing) and the time of the maximum."""
    n = 3600
    hi = -1e30
    lo = 1e30
    tpk = 0.0
    for i in range(n):
        t = p["tau"] * i / n
        v = _ang_T(p, x, t)
        if v > hi:
            hi = v
            tpk = t
        if v < lo:
            lo = v
    return [(hi - lo) / 2, tpk]


class AngstromBar:
    """A long bar heated and cooled at one end with the period tau; thermocouples at x1 and x2 follow the damped
    temperature wave  T(x, t) = Tm + A0 exp(-a x) sin(w t - b x). mu is the surface-loss rate (1/s)."""

    PARAMS = {"D": 1.1625e-4, "tau": 120.0, "x1": 0.05, "x2": 0.15, "mu": 0.002, "A0": 20.0, "Tm": 60.0,
              "rho": 8960.0, "cp": 385.0}
    VARS = ["t", "T1", "T2"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "T1": _ang_T(p, p["x1"], s["t"]), "T2": _ang_T(p, p["x2"], s["t"])}

    @staticmethod
    def measure(p, cfg=None):
        s1 = _ang_scan(p, p["x1"])
        s2 = _ang_scan(p, p["x2"])
        lag = s2[1] - s1[1]
        if lag < 0:
            lag += p["tau"]
        dx = p["x2"] - p["x1"]
        D = dx * dx / (2 * lag * math.log(s1[0] / s2[0]))
        return {"D": D, "K": D * p["rho"] * p["cp"], "A1": s1[0], "A2": s2[0], "lag": lag}


# ============================================================================== specific heat by cooling
def _cool_C(p: dict, which: float) -> float:
    """Heat capacity of the calorimeter with its contents: equal volumes of water (which 0) or of the liquid (1)."""
    W = p["mc"] * p["cc"]
    if which < 0.5:
        return p["rhow"] * p["Vol"] * p["cw"] + W
    return p["rhol"] * p["Vol"] * p["cl"] + W


def _cool_time(p: dict, which: float) -> float:
    """Time to cool from Ta to Tb in the same enclosure (0.05 s steps, the crossings interpolated)."""
    C = _cool_C(p, which)
    T = p["T0"]
    t = 0.0
    h = 0.05
    ta = -1.0
    while t < 1.0e5:
        T2 = T - p["hA"] * (T - p["Ts"]) / C * h
        if ta < 0 and T >= p["Ta"] and T2 < p["Ta"]:
            ta = t + h * (T - p["Ta"]) / (T - T2)
        if T >= p["Tb"] and T2 < p["Tb"]:
            return t + h * (T - p["Tb"]) / (T - T2) - ta
        T = T2
        t = t + h
    return 0.0


class CoolingPair:
    """Two identical blackened calorimeters in the same double-walled enclosure at Ts, one with water and one with an
    equal volume of the liquid: C dT/dt = -hA (T - Ts) for each. `which` chooses the one being followed."""

    PARAMS = {"cl": 2010.0, "rhol": 810.0, "Vol": 6.0e-5, "cw": 4186.0, "rhow": 998.2, "mc": 0.05, "cc": 385.0,
              "hA": 0.35, "Ts": 28.0, "T0": 72.0, "Ta": 65.0, "Tb": 55.0, "which": 0.0}
    VARS = ["t", "T", "C"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["T0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.05)
        C = _cool_C(p, p["which"])
        for _ in range(n):
            s["T"] = s["T"] - p["hA"] * (s["T"] - p["Ts"]) / C * h
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "T": s["T"], "C": _cool_C(p, p["which"])}

    @staticmethod
    def measure(p, cfg=None):
        tw = _cool_time(p, 0.0)
        tl = _cool_time(p, 1.0)
        W = p["mc"] * p["cc"]
        mw = p["rhow"] * p["Vol"]
        ml = p["rhol"] * p["Vol"]
        return {"tw": tw, "tl": tl, "cl": ((mw * p["cw"] + W) * tl / tw - W) / ml}


# ============================================================================== harmonics of a complex wave
def _wave(p: dict, ph: float) -> float:
    """One cycle (ph in 0..1) of a unit odd wave: 0 square, 1 triangle, 2 a sine clipped at `clip` of its peak."""
    ph = ph - math.floor(ph)
    if p["shape"] < 0.5:
        return 1.0 if ph < 0.5 else -1.0
    if p["shape"] < 1.5:
        if ph < 0.25:
            return 4 * ph
        if ph < 0.75:
            return 2 - 4 * ph
        return 4 * ph - 4
    v = math.sin(2 * PI * ph)
    if v > p["clip"]:
        return p["clip"]
    if v < -p["clip"]:
        return -p["clip"]
    return v


def _harm(p: dict, n: float) -> float:
    """Amplitude of the n-th sine harmonic by the Fourier integral (midpoint rule, 4096 strips)."""
    N = 4096
    acc = 0.0
    for i in range(N):
        ph = (i + 0.5) / N
        acc += _wave(p, ph) * math.sin(2 * PI * n * ph)
    return p["A"] * 2 * acc / N


def _harm_exact(p: dict, n: float) -> float:
    if p["shape"] < 0.5:
        return p["A"] * 4 / (n * PI)
    if p["shape"] < 1.5:
        return p["A"] * 8 / (n * n * PI * PI) * math.sin(n * PI / 2)
    al = math.asin(p["clip"])
    if n < 1.5:
        first = (al - math.sin(2 * al) / 2) / 2
    else:
        first = (math.sin((n - 1) * al) / (n - 1) - math.sin((n + 1) * al) / (n + 1)) / 2
    return p["A"] * 4 / PI * (first + p["clip"] * math.cos(n * al) / n)


class Harmonics:
    """A function generator feeds a narrow tunable filter; the CRO shows the harmonic the filter passes.
    `n` is the harmonic the filter is tuned to."""

    PARAMS = {"shape": 0.0, "A": 2.0, "f0": 1000.0, "clip": 0.5, "n": 3.0}
    VARS = ["t", "y", "an", "a1", "ratio"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        an = _harm(p, p["n"])
        a1 = _harm(p, 1.0)
        return {"t": s["t"], "y": p["A"] * _wave(p, s["t"] * p["f0"]), "an": an, "a1": a1, "ratio": abs(an / a1)}

    @staticmethod
    def measure(p, cfg=None):
        an = _harm(p, p["n"])
        a1 = _harm(p, 1.0)
        return {"an": abs(an), "a1": abs(a1), "ratio": abs(an / a1)}


# ============================================================================== trolley on an inclined plane
def _trol_mu(p: dict) -> float:
    return p["mus"] if p["lock"] > 0.5 else p["mur"]


def _trol_a(p: dict) -> float:
    """Acceleration down the slope of a trolley released from rest: g (sin th - mu cos th), zero if it cannot move."""
    a = p["g"] * (math.sin(p["angle"]) - _trol_mu(p) * math.cos(p["angle"]))
    return a if a > 0 else 0.0


class Trolley:
    """A trolley released from rest on an inclined plane, wheels locked (sliding friction mus) or free (rolling
    resistance mur). Friction is taken as kinetic once it moves; a gentle release starts it (said in the lab)."""

    PARAMS = {"angle": 0.4363, "mus": 0.3, "mur": 0.012, "lock": 1.0, "g": 9.8, "d": 1.0}
    VARS = ["t", "s", "v", "a"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "s": 0.0, "v": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        a = _trol_a(p)
        s["s"] += s["v"] * dt + 0.5 * a * dt * dt
        s["v"] += a * dt
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "s": s["s"], "v": s["v"], "a": _trol_a(p)}

    @staticmethod
    def measure(p, cfg=None):
        a = _trol_a(p)
        if a <= 0:
            return {"a": 0.0, "tg": 0.0, "mu": 0.0}
        tg = math.sqrt(2 * p["d"] / a)
        return {"a": a, "tg": tg, "mu": math.tan(p["angle"]) - 2 * p["d"] / (p["g"] * math.cos(p["angle"]) * tg * tg)}


# ============================================================================== two-dimensional collision of two pucks
def _c2_geo(p: dict):
    """Puck A (m1) moves along +x at u with its centre a height b above puck B's (m2, at rest at the origin).
    Returns (contact time, contact x of A, unit normal n from A to B at contact)."""
    D = 2 * p["R"]
    b = p["b"]
    cx = -math.sqrt(D * D - b * b)                 # A's centre at contact, relative to B
    tc = (cx - p["x0"]) / p["u"]
    return tc, cx, (-cx / D, -b / D)


def _c2_after(p: dict):
    """Velocities after the impact: the impulse acts along the line of centres; e is the coefficient of restitution."""
    tc, cx, n = _c2_geo(p)
    un = p["u"] * n[0]                             # A's velocity along the normal (B is at rest)
    m1, m2, e = p["m1"], p["m2"], p["e"]
    j = (1 + e) * m1 * m2 / (m1 + m2) * un         # impulse on B along n
    v1 = (p["u"] - j / m1 * n[0], -j / m1 * n[1])
    v2 = (j / m2 * n[0], j / m2 * n[1])
    return v1, v2


def _c2_pos(p: dict, t: float):
    tc, cx, n = _c2_geo(p)
    if t <= tc:
        return (p["x0"] + p["u"] * t, p["b"]), (0.0, 0.0)
    v1, v2 = _c2_after(p)
    d = t - tc
    return (cx + v1[0] * d, p["b"] + v1[1] * d), (v2[0] * d, v2[1] * d)


def _c2_ke_ratio(p: dict) -> float:
    """KE after / KE before from the closed form: 1 - (1 - e^2) m2 / (m1 + m2) cos^2(phi), phi = angle of the line of centres."""
    tc, cx, n = _c2_geo(p)
    return 1 - (1 - p["e"] ** 2) * p["m2"] / (p["m1"] + p["m2"]) * n[0] ** 2


class Collision2D:
    """Virtual air table: two pucks, an oblique impact, restitution e. Deterministic, frictionless."""

    PARAMS = {"m1": 0.2, "m2": 0.3, "u": 0.5, "b": 0.03, "R": 0.04, "e": 1.0, "x0": -0.4}
    VARS = ["t", "x1", "y1", "x2", "y2"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        a, b = _c2_pos(p, s["t"])
        return {"t": s["t"], "x1": a[0], "y1": a[1], "x2": b[0], "y2": b[1]}

    @staticmethod
    def measure(p, cfg=None):
        v1, v2 = _c2_after(p)
        px = p["m1"] * v1[0] + p["m2"] * v2[0]
        py = p["m1"] * v1[1] + p["m2"] * v2[1]
        ke = (p["m1"] * (v1[0] ** 2 + v1[1] ** 2) + p["m2"] * (v2[0] ** 2 + v2[1] ** 2)) / (p["m1"] * p["u"] ** 2)
        return {"px": px / (p["m1"] * p["u"]), "py": py / (p["m1"] * p["u"]), "ke": ke,
                "v1x": v1[0], "v1y": v1[1], "v2x": v2[0], "v2y": v2[1]}


KERNELS: dict[str, Any] = {
    "w7_pend": Pendulum,
    "w7_kater": Kater,
    "w7_coupled": Coupled,
    "w7_spring": SpringLoad,
    "w7_torsion": TorsionRig,
    "w7_stefan": StefanLamp,
    "w7_cbarnes": CallendarBarnes,
    "w7_angstrom": AngstromBar,
    "w7_cool": CoolingPair,
    "w7_fourier": Harmonics,
    "w7_trolley": Trolley,
    "w7_coll2d": Collision2D,
}
FAMILY = {"w7_pend": "mech", "w7_kater": "mech", "w7_coupled": "osc_wave", "w7_spring": "osc_wave", "w7_torsion": "mech",
          "w7_stefan": "thermo", "w7_cbarnes": "thermo", "w7_angstrom": "thermo", "w7_cool": "thermo",
          "w7_fourier": "osc_wave", "w7_trolley": "mech", "w7_coll2d": "mech"}


def _cpl_kappa(p: dict) -> float:
    w = _cpl_w(p)
    return (w[1] - w[0]) / (w[1] + w[0])


TEXTBOOK = {
    # finite-amplitude period of a pendulum to second order: T = 2 pi sqrt(Leq / g) (1 + th0^2 / 16)
    "w7_pend_T": lambda p: _pend_T0(p) * (1 + p["th0"] * p["th0"] / 16),
    # g from the timed period of a bar pendulum is the local g
    "w7_pend_g": lambda p: p["g"],
    # the amplitude of a lightly damped oscillator falls as exp(-gam t)
    "w7_pend_gam": lambda p: p["gam"],
    # amplitude at which the period is (1 + eps) times the small-swing period, from the series in th0
    "w7_pend_lim": _pend_lim_series,
    # Bessel's formula returns the local g whatever the two periods are
    "w7_kater_g": lambda p: p["g"],
    # coupling coefficient from the two normal-mode frequencies
    "w7_coupled_kappa": _cpl_kappa,
    "w7_coupled_gam": lambda p: p["gam"],
    # period of a loaded spring with one third of its own mass added to the load
    "w7_spring_T": lambda p: 2 * PI * math.sqrt((p["m"] + p["ms"] / 3) / _spr_keff(p)),
    "w7_spring_k": _spr_keff,
    "w7_spring_eta": lambda p: p["eta"],
    "w7_tors_eta": lambda p: p["eta"],
    "w7_tors_Y": lambda p: p["Y"],
    "w7_tors_sigma": lambda p: p["Y"] / (2 * p["eta"]) - 1,
    # Stefan-Boltzmann constant (CODATA 2018, exact) and the exponent of T
    "w7_stefan_sigma": lambda p: p["sigma"],
    "w7_stefan_n": lambda p: 4.0,
    "w7_cbarnes_J": lambda p: p["J"],
    "w7_angstrom_D": lambda p: p["D"],
    "w7_cool_cl": lambda p: p["cl"],
    # relative amplitude of the n-th harmonic from the closed-form Fourier coefficients
    "w7_fourier_ratio": lambda p: abs(_harm_exact(p, p["n"]) / _harm_exact(p, 1.0)),
    # coefficient of friction of the trolley in the chosen state (locked: sliding; free: rolling)
    "w7_trolley_mu": _trol_mu,
    # time over the gate distance from rest: t = sqrt(2 d / (g (sin th - mu cos th)))
    "w7_trolley_t": lambda p: math.sqrt(2 * p["d"] / _trol_a(p)) if _trol_a(p) > 0 else 0.0,
    # oblique impact with restitution e along the line of centres: KE kept = 1 - (1 - e^2) m2 / (m1 + m2) cos^2 phi
    "w7_coll2d_ke": _c2_ke_ratio,
    # total momentum after / before (both components) is 1 for any e
    "w7_coll2d_px": lambda p: 1.0,
}
CALCS: dict[str, Any] = {}
