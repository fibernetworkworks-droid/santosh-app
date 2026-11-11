"""Kernel pack: Class XI-XII mechanics, properties of matter and heat set-ups that the shared kernels did not cover.

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/mech11.js` (same formulas, same order of operations, so both give the same numbers).

Kernels, with the textbook relation each one is checked against (1 %):
    capillary    rise in a capillary tube            h = 2 T cosθ / (r ρ g)
    searle       Young's modulus (Searle's apparatus) e = 4 m g L / (π d² Y)
    friction     block on a horizontal surface        F = μ R,  R = (m + added) g
    moments       metre scale on a knife edge          M y = m x
    beambend     depression of a loaded beam          δ = m g L³ / (3 Y I)  (cantilever) or / (48 Y I) (centre)
    vecforce     parallelogram law (Gravesand)        R² = P² + Q² + 2 P Q cos θ
    spherometer  radius of a spherical surface        R = l² / (6 h) + h / 2
Everything is SI and deterministic: no randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi


def _sub(dt: float, h: float) -> tuple[int, float]:
    n = max(1, int(math.ceil(dt / h - 1e-9)))
    return n, dt / n


def _relax(x: float, target: float, dt: float, tau: float) -> float:
    """One step of x -> target with time constant tau, in fixed 5 ms sub-steps (identical in the JS twin)."""
    n, h = _sub(dt, 0.005)
    t = max(tau, 1e-6)
    for _ in range(n):
        x += (target - x) * (h / t)
    return x


def _rk4(f, y: list[float], h: float) -> list[float]:
    k1 = f(y)
    k2 = f([y[i] + h / 2 * k1[i] for i in range(len(y))])
    k3 = f([y[i] + h / 2 * k2[i] for i in range(len(y))])
    k4 = f([y[i] + h * k3[i] for i in range(len(y))])
    return [y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(len(y))]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


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


# ------------------------------------------------------------------------------------- surface tension: capillary rise
def _cap_h(p: dict) -> float:
    return 2 * p["T"] * math.cos(p["theta"]) / (p["r"] * p["rho"] * p["g"])


class Capillary:
    """A capillary tube dipped in a liquid: the liquid climbs until surface tension balances the weight of the column."""

    PARAMS = {"T": 0.07275, "rho": 998.2, "r": 0.00025, "theta": 0.0, "g": 9.8, "tau": 1.6, "h0": 0.0}
    VARS = ["t", "h", "h_mm", "h_cm", "heq", "rise"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "h": p["h0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["h"] = _relax(s["h"], _cap_h(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "h": s["h"], "h_mm": s["h"] * 1000, "h_cm": s["h"] * 100, "heq": _cap_h(p),
                "rise": 1.0 if abs(s["h"] - _cap_h(p)) > 1e-5 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        s = Capillary.init(p)
        for _ in range(240):                        # 24 s: the meniscus has settled
            Capillary.step(s, p, 0.1)
        return {"h": s["h"], "heq": _cap_h(p)}


# ------------------------------------------------------------------------------- Young's modulus: Searle's apparatus
def _searle_e(p: dict) -> float:
    a = PI * p["d"] * p["d"] / 4
    return p["m"] * p["g"] * p["L"] / (a * p["Y"])


class Searle:
    """Two long wires side by side; the load on the experimental wire stretches it and the micrometer reads e."""

    PARAMS = {"Y": 2.0e11, "L": 1.5, "d": 0.000559, "m": 0.0, "g": 9.8, "tau": 0.9, "e0": 0.0}
    VARS = ["t", "e", "e_mm", "stress", "strain", "load_N"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "e": p["e0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["e"] = _relax(s["e"], _searle_e(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        a = PI * p["d"] * p["d"] / 4
        return {"t": s["t"], "e": s["e"], "e_mm": s["e"] * 1000, "stress": p["m"] * p["g"] / a,
                "strain": s["e"] / p["L"], "load_N": p["m"] * p["g"]}

    @staticmethod
    def measure(p, cfg=None):
        s = Searle.init(p)
        for _ in range(200):                        # 20 s under the load
            Searle.step(s, p, 0.1)
        return {"e": s["e"], "e_eq": _searle_e(p)}


# ------------------------------------------------------------------------------------ limiting friction, horizontal
class Friction:
    """A block on a horizontal surface pulled by a thread over a pulley. One coefficient (static = kinetic, said so)."""

    PARAMS = {"mu": 0.3, "m": 0.2, "add": 0.0, "F": 0.0, "g": 9.8, "len": 0.3}
    VARS = ["t", "s", "v", "a", "moving", "R", "F_now"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "s": 0.0, "v": 0.0, "a": 0.0}

    @staticmethod
    def _adv(s, p, h):
        mass = p["m"] + p["add"]
        drive = p["F"]
        fr = p["mu"] * mass * p["g"]
        if s["v"] == 0.0:
            if abs(drive) <= fr:
                s["a"] = 0.0
                return
            a = (drive - fr * (1.0 if drive > 0 else -1.0)) / mass
        else:
            a = (drive - fr * (1.0 if s["v"] > 0 else -1.0)) / mass
        v2 = s["v"] + a * h
        if s["v"] != 0.0 and (v2 > 0) != (s["v"] > 0):
            s["s"] += s["v"] * s["v"] / (-2 * a) if a != 0 else 0.0
            s["v"], s["a"] = 0.0, 0.0
            return
        s["s"] += s["v"] * h + 0.5 * a * h * h
        s["v"], s["a"] = v2, a
        if s["s"] <= 0.0 or s["s"] >= p["len"]:
            s["s"] = min(max(s["s"], 0.0), p["len"])
            s["v"], s["a"] = 0.0, 0.0

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        for _ in range(n):
            Friction._adv(s, p, h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "s": s["s"], "v": s["v"], "a": s["a"], "moving": 1.0 if s["v"] != 0.0 else 0.0,
                "R": (p["m"] + p["add"]) * p["g"], "F_now": p["F"]}

    @staticmethod
    def _moves(p, f):
        q = dict(p, F=f, len=1e6)
        s = {"t": 0.0, "s": 1.0, "v": 0.0, "a": 0.0}
        for _ in range(250):                        # 0.5 s: did the block leave its place?
            Friction._adv(s, q, 0.002)
        return s["s"] > 1.0 + 1e-9

    @staticmethod
    def measure(p, cfg=None):
        lo, hi = 0.0, 4 * (p["m"] + p["add"]) * p["g"] + 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if Friction._moves(p, mid):
                hi = mid
            else:
                lo = mid
        return {"F_min": hi, "R": (p["m"] + p["add"]) * p["g"]}


# -------------------------------------------------------------------------------------- principle of moments
def _mom_tilt(p: dict, y: float) -> float:
    """The tilt the scale settles at with the known mass at distance y: g (M y - m x) cos θ = k θ."""
    lo, hi = -0.30, 0.30
    for _ in range(50):
        mid = (lo + hi) / 2
        if p["g"] * (p["M"] * y - p["m"] * p["x"]) * math.cos(mid) - p["k"] * mid > 0:
            lo = mid
        else:
            hi = mid
    th = (lo + hi) / 2
    return min(max(th, -0.12), 0.12)                # the scale's end comes to rest on the stand


class Moments:
    """A metre scale on a knife edge at its centre of gravity: the unknown body on one side, a known mass on the other."""

    PARAMS = {"m": 0.0523, "M": 0.05, "x": 0.2, "y": 0.2, "g": 9.8, "k": 0.6, "I": 0.004, "c": 0.9}
    VARS = ["t", "th", "tilt_deg", "balanced", "left_N", "right_N"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [_mom_tilt(p, p["y"]), 0.0]}

    @staticmethod
    def _f(p):
        def f(y):
            tq = p["g"] * (p["M"] * p["y"] - p["m"] * p["x"]) * math.cos(y[0]) - p["k"] * y[0]
            return [y[1], tq / p["I"] - p["c"] * y[1]]
        return f

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = Moments._f(p)
        lim = 0.12
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
            if s["y"][0] > lim:
                s["y"] = [lim, min(0.0, s["y"][1])]
            elif s["y"][0] < -lim:
                s["y"] = [-lim, max(0.0, s["y"][1])]
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        th = s["y"][0]
        return {"t": s["t"], "th": th, "tilt_deg": th * 180 / PI, "balanced": 1.0 if abs(th) < 0.004 else 0.0,
                "left_N": p["m"] * p["g"], "right_N": p["M"] * p["g"]}

    @staticmethod
    def measure(p, cfg=None):
        lo, hi = 0.0, 0.6
        for _ in range(60):                         # slide the known mass until the scale is level
            mid = (lo + hi) / 2
            if _mom_tilt(p, mid) < 0:
                lo = mid
            else:
                hi = mid
        y = (lo + hi) / 2
        return {"y": y, "tilt": _mom_tilt(p, y)}


# ------------------------------------------------------------------------------------- depression of a loaded beam
def _beam_I(p: dict) -> float:
    return p["b"] * p["t"] ** 3 / 12


def _beam_cf(p: dict) -> float:
    return 3.0 if p["mode"] < 0.5 else 48.0


def _beam_delta(p: dict) -> float:
    return p["m"] * p["g"] * p["L"] ** 3 / (_beam_cf(p) * p["Y"] * _beam_I(p))


class BeamBend:
    """A clamped metre scale (cantilever) or one resting on two knife edges, loaded and sagging by δ."""

    PARAMS = {"Y": 1.0e10, "b": 0.028, "t": 0.005, "L": 0.5, "m": 0.0, "g": 9.8, "mode": 0.0, "tau": 0.5, "d0": 0.0}
    VARS = ["t", "delta", "delta_mm", "delta_cm", "load_N"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "d": p["d0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["d"] = _relax(s["d"], _beam_delta(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "delta": s["d"], "delta_mm": s["d"] * 1000, "delta_cm": s["d"] * 100,
                "load_N": p["m"] * p["g"]}

    @staticmethod
    def measure(p, cfg=None):
        s = BeamBend.init(p)
        for _ in range(200):
            BeamBend.step(s, p, 0.1)
        return {"delta": s["d"], "delta_eq": _beam_delta(p)}


# ----------------------------------------------------------------------------- parallelogram law (Gravesand's board)
def _vec_beta(p: dict, a: float) -> float:
    s = p["P"] * math.sin(a) / p["Q"]
    return math.asin(min(1.0, max(-1.0, s)))


def _vec_alpha(p: dict) -> float:
    """The angle the left thread makes with the vertical when the three forces are in equilibrium."""
    lo, hi = 1e-9, PI / 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if p["P"] * math.cos(mid) + p["Q"] * math.cos(_vec_beta(p, mid)) > p["W"]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


class VecForce:
    """Two weights over pulleys hold up a third: at the knot the three forces balance, so P and Q's resultant is W."""

    PARAMS = {"P": 1.47, "Q": 1.47, "W": 1.96, "g": 9.8, "tau": 0.8, "a0": 0.05}
    VARS = ["t", "alpha", "beta", "theta", "theta_deg", "R", "settled"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "a": p["a0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["a"] = _relax(s["a"], _vec_alpha(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        a = s["a"]
        b = _vec_beta(p, a)
        th = a + b
        return {"t": s["t"], "alpha": a, "beta": b, "theta": th, "theta_deg": th * 180 / PI,
                "R": math.sqrt(p["P"] ** 2 + p["Q"] ** 2 + 2 * p["P"] * p["Q"] * math.cos(th)),
                "settled": 1.0 if abs(a - _vec_alpha(p)) < 1e-4 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        a = _vec_alpha(p)
        b = _vec_beta(p, a)
        th = a + b
        return {"alpha": a, "beta": b, "theta": th,
                "W_calc": math.sqrt(p["P"] ** 2 + p["Q"] ** 2 + 2 * p["P"] * p["Q"] * math.cos(th))}


# --------------------------------------------------------------------------------------------------- spherometer
def _sph_h(p: dict) -> float:
    d = p["R"] * p["R"] - p["l"] * p["l"] / 3
    return p["R"] - math.sqrt(d) if d > 0 else p["R"]


class Spherometer:
    """A spherometer on a spherical surface: its central screw measures the sagitta h over the legs' circle."""

    PARAMS = {"R": 0.15, "l": 0.045, "pitch": 0.001, "ndiv": 100.0, "convex": 1.0, "lc": 0.0}
    VARS = ["h", "h_mm", "turns", "div", "R_meas", "lc_mm"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        h = _sph_h(p)
        lc = p["pitch"] / p["ndiv"]
        turns = math.floor(h / p["pitch"] + 1e-9)
        div = math.floor((h - turns * p["pitch"]) / lc + 0.5)
        if div >= p["ndiv"]:
            turns, div = turns + 1, 0
        return {"h": h, "h_mm": h * 1000, "turns": float(turns), "div": float(div),
                "R_meas": p["l"] * p["l"] / (6 * h) + h / 2 if h > 0 else 0.0, "lc_mm": lc * 1000}

    @staticmethod
    def measure(p, cfg=None):
        h = _sph_h(p)
        return {"h": h, "R": p["l"] * p["l"] / (6 * h) + h / 2 if h > 0 else 0.0}


KERNELS: dict[str, Any] = {"capillary": Capillary, "searle": Searle, "friction": Friction, "moments": Moments,
                           "beambend": BeamBend, "vecforce": VecForce, "spherometer": Spherometer}
FAMILY = {"capillary": "mech", "searle": "mech", "friction": "mech", "moments": "mech", "beambend": "mech",
          "vecforce": "mech", "spherometer": "mech"}

TEXTBOOK = {
    "cap_h": _cap_h,
    "searle_e": _searle_e,
    "friction_Fmin": lambda p: p["mu"] * (p["m"] + p["add"]) * p["g"],
    "moments_y": lambda p: p["m"] * p["x"] / p["M"],
    "beam_delta": _beam_delta,
    "vec_W": lambda p: p["W"],
    "sph_R": lambda p: p["R"],
}

CALCS = {
    "cap_T": {"label": "T (surface tension)", "unit": "N/m", "needs": ["r", "h"],
              "fn": lambda rows, p: _mean([h * r * p["rho"] * p["g"] / (2 * math.cos(p["theta"]))
                                           for r, h in _rows(rows, "r", "h") if r > 0])},
    "searle_Y": {"label": "Y (Young's modulus)", "unit": "Pa", "needs": ["m", "e"],
                 "fn": lambda rows, p: _mean([4 * m * p["g"] * p["L"] / (PI * p["d"] * p["d"] * e)
                                              for m, e in _rows(rows, "m", "e") if e > 0])},
    "friction_mu": {"label": "μ", "unit": "", "needs": ["R", "F"],
                    "fn": lambda rows, p: (lambda rs: (sum(R * F for R, F in rs) / sum(R * R for R, F in rs))
                                           if sum(R * R for R, F in rs) > 0 else 0.0)(_rows(rows, "R", "F"))},
    "moments_m": {"label": "mass of the body", "unit": "kg", "needs": ["x", "y"],
                  "fn": lambda rows, p: _mean([p["M"] * y / x for x, y in _rows(rows, "x", "y") if x > 0])},
    "beam_Y": {"label": "Y (Young's modulus)", "unit": "Pa", "needs": ["m", "delta"],
               "fn": lambda rows, p: _mean([m * p["g"] * p["L"] ** 3 / (_beam_cf(p) * _beam_I(p) * d)
                                            for m, d in _rows(rows, "m", "delta") if d > 0])},
    "vec_W_calc": {"label": "weight of the body", "unit": "N", "needs": ["P", "Q", "th"],
                   "fn": lambda rows, p: _mean([math.sqrt(P * P + Q * Q + 2 * P * Q * math.cos(th))
                                                for P, Q, th in _rows(rows, "P", "Q", "th")])},
    "sph_R": {"label": "R (radius of curvature)", "unit": "m", "needs": ["l", "h"],
              "fn": lambda rows, p: _mean([l * l / (6 * h) + h / 2 for l, h in _rows(rows, "l", "h") if h > 0])},
    "mix_c_liquid": {"label": "c (liquid)", "unit": "J/(kg·K)", "needs": ["Tf"],
                     "fn": lambda rows, p: _mean([(p["m1"] * p["c1"] * (p["T1"] - Tf) - p["mc"] * p["cc"] * (Tf - p["T2"]))
                                                  / (p["m2"] * (Tf - p["T2"]))
                                                  for (Tf,) in _rows(rows, "Tf") if Tf > p["T2"]])},
}
