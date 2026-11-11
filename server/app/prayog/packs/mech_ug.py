"""Kernel pack: the classic B.Sc. (undergraduate) mechanics, measurement and properties-of-matter benches.

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/mech_ug.js` (same formulas, same order of operations, so both give the same numbers).
Nothing here repeats a kernel of `packs/mech11.py` (capillary rise, Searle's wire, friction, moments, cantilever
bending, the parallelogram law and the spherometer are all there already).

Kernels, with the textbook relation each one is checked against (1 %):
    torsion      torsional pendulum / inertia table   T = 2π√(I / C),  C = π η r⁴ / (2 L)
    stattorsion  statical (Barton's) torsion          θ = 4 m g a L / (π η r⁴)   (couple from two cords)
    flywheel     moment of inertia of a flywheel      t₁ = √(2 φ (I + m r²) / (m g r − τ_f))
    barpend      bar (compound) pendulum              T = 2π√((k² + h²) / (g h)),  k² = L² / 12
    poiseuille   capillary flow of a liquid           Q = π ρ g h r⁴ / (8 η l)
    jaeger       Jaeger's bubble pressure             H = (2 T / (r g) + h ρ_l) / ρ_m
    unibend      uniform bending of a beam            δ = 3 m g a L² / (2 Y b d³)
    travmicro    travelling microscope + repeats      mean of the readings → the true dimension
    freefall     free fall between two photo-gates    t = √(2 h / g)
    collide1d    collision of two air-track gliders   v₂ = m₁ (1 + e) u₁ / (m₁ + m₂)
Everything is SI and deterministic: no randomness drawn from the system, no wall clock. The repeated-reading
spread of `travmicro` comes from a fixed Lehmer generator, so both twins produce the same readings for ever.
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


# ============================================================================== torsional pendulum / inertia table
def _tors_C(p: dict) -> float:
    """The torsional constant (restoring couple per radian) of the suspension wire."""
    return PI * p["eta"] * p["rw"] ** 4 / (2 * p["Lw"])


def _tors_T(p: dict) -> float:
    c = _tors_C(p)
    return 2 * PI * math.sqrt(p["I"] / c) if c > 0 and p["I"] > 0 else 0.0


def _tors_f(p: dict):
    c = _tors_C(p) / p["I"]
    b = p["b"]

    def f(y):
        return [y[1], -c * y[0] - b * y[1]]
    return f


class Torsion:
    """A disc, a ring or an irregular body hung on a long wire and given a small twist: it oscillates in its own plane."""

    PARAMS = {"eta": 8.0e10, "rw": 0.0004, "Lw": 0.8, "I": 0.0012, "th0": 0.35, "b": 0.0}
    VARS = ["t", "th", "th_deg", "om", "C", "T_calc", "amp_deg"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["th0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _tors_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "th": s["y"][0], "th_deg": s["y"][0] * 180 / PI, "om": s["y"][1],
                "C": _tors_C(p), "T_calc": _tors_T(p), "amp_deg": p["th0"] * 180 / PI}

    @staticmethod
    def measure(p, cfg=None):
        return {"T": _period(_tors_f(p), [p["th0"], 0.0], 0.0005, 400.0), "C": _tors_C(p)}


# ========================================================================= statical torsion (Barton's apparatus)
def _stat_theta(p: dict) -> float:
    """Two cords off a wheel of radius a give a couple 2 m g a; the rod twists by θ = 2 τ L / (π η r⁴)."""
    return 4 * p["m"] * p["g"] * p["a"] * p["Lr"] / (PI * p["eta"] * p["rr"] ** 4)


class StatTorsion:
    """A rod clamped at one end with a torsion wheel at the other: weights on two cords twist it through a steady angle."""

    PARAMS = {"eta": 8.0e10, "rr": 0.002, "Lr": 0.6, "a": 0.05, "m": 0.0, "g": 9.8, "tau": 0.6, "th0": 0.0}
    VARS = ["t", "th", "th_deg", "couple", "th_eq_deg"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "th": p["th0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["th"] = _relax(s["th"], _stat_theta(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "th": s["th"], "th_deg": s["th"] * 180 / PI,
                "couple": 2 * p["m"] * p["g"] * p["a"], "th_eq_deg": _stat_theta(p) * 180 / PI}

    @staticmethod
    def measure(p, cfg=None):
        s = StatTorsion.init(p)
        for _ in range(200):                        # 20 s: the pointer has come to rest
            StatTorsion.step(s, p, 0.1)
        return {"theta": s["th"], "theta_eq": _stat_theta(p)}


# ================================================================================== moment of inertia of a flywheel
def _fly_phi(p: dict) -> float:
    return 2 * PI * p["n"]


def _fly_a1(p: dict) -> float:
    return (p["m"] * p["g"] * p["ra"] - p["tf"]) / (p["I"] + p["m"] * p["ra"] * p["ra"])


def _fly_t1(p: dict) -> float:
    a = _fly_a1(p)
    return math.sqrt(2 * _fly_phi(p) / a) if a > 0 else 0.0


def _fly_state(p: dict, t: float) -> tuple[float, float, int]:
    """Angle turned, angular speed and phase at time t: a constant drive while the mass falls, then friction alone."""
    a1, phi, t1 = _fly_a1(p), _fly_phi(p), _fly_t1(p)
    if t <= t1:
        return 0.5 * a1 * t * t, a1 * t, 0
    om0 = a1 * t1
    a2 = p["tf"] / p["I"]
    td = t - t1
    tstop = om0 / a2 if a2 > 0 else 1e9
    if td >= tstop:
        return phi + om0 * tstop - 0.5 * a2 * tstop * tstop, 0.0, 2
    return phi + om0 * td - 0.5 * a2 * td * td, om0 - a2 * td, 1


def _fly_I_one(p: dict, m: float, n: float, t1: float, N: float) -> float:
    """The working formula: I = m (2 g h − v²) r² / (v² (1 + n/N)), with h = 2πnr and v = 2φr/t₁.

    The falling mass and the number of turns are read from the ROW, so a table of runs at different loads works."""
    phi = 2 * PI * n
    h = p["ra"] * phi
    v = 2 * phi * p["ra"] / t1
    return m * (2 * p["g"] * h - v * v) * p["ra"] * p["ra"] / (v * v * (1 + n / N))


class Flywheel:
    """A heavy flywheel on a horizontal axle. A cord wound n turns on the axle carries a mass; it falls, spins the wheel
    up, slips off, and the wheel then runs down against friction alone."""

    PARAMS = {"I": 0.012, "m": 0.5, "ra": 0.012, "n": 8.0, "tf": 0.012, "g": 9.8}
    VARS = ["t", "ph", "om", "rpm", "drop", "phase", "turns", "t1", "om1", "N", "t2", "v"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ph, om, phase = _fly_state(p, s["t"])
        phi = _fly_phi(p)
        t1 = _fly_t1(p)
        om1 = _fly_a1(p) * t1
        a2 = p["tf"] / p["I"]
        return {"t": s["t"], "ph": ph, "om": om, "rpm": om * 60 / (2 * PI),
                "drop": p["ra"] * min(ph, phi), "phase": float(phase), "turns": ph / (2 * PI),
                "t1": t1, "om1": om1, "N": om1 * om1 / (2 * a2) / (2 * PI) if a2 > 0 else 0.0,
                "t2": om1 / a2 if a2 > 0 else 0.0, "v": om * p["ra"]}

    @staticmethod
    def measure(p, cfg=None):
        t1 = _fly_t1(p)
        om1 = _fly_a1(p) * t1
        a2 = p["tf"] / p["I"]
        return {"t1": t1, "om1": om1, "v": om1 * p["ra"],
                "N": om1 * om1 / (2 * a2) / (2 * PI) if a2 > 0 else 0.0, "t2": om1 / a2 if a2 > 0 else 0.0,
                "h": p["ra"] * _fly_phi(p)}


# ========================================================================================= bar (compound) pendulum
def _bar_k2(p: dict) -> float:
    return p["Lb"] * p["Lb"] / 12


def _bar_T(p: dict) -> float:
    k2 = _bar_k2(p)
    return 2 * PI * math.sqrt((k2 + p["h"] * p["h"]) / (p["g"] * p["h"])) if p["h"] > 0 else 0.0


def _bar_f(p: dict):
    k2 = _bar_k2(p)
    c = p["g"] * p["h"] / (k2 + p["h"] * p["h"])
    b = p["b"]

    def f(y):
        return [y[1], -c * math.sin(y[0]) - b * y[1]]
    return f


class BarPendulum:
    """A uniform metal bar with holes along it, hung on a knife edge through one hole: a compound pendulum."""

    PARAMS = {"Lb": 1.0, "h": 0.35, "g": 9.8, "th0": 0.0873, "b": 0.0}
    VARS = ["t", "th", "th_deg", "om", "k2", "T_calc", "L_eq"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["th0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _bar_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        k2 = _bar_k2(p)
        return {"t": s["t"], "th": s["y"][0], "th_deg": s["y"][0] * 180 / PI, "om": s["y"][1], "k2": k2,
                "T_calc": _bar_T(p), "L_eq": (k2 + p["h"] * p["h"]) / p["h"] if p["h"] > 0 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        return {"T": _period(_bar_f(p), [p["th0"], 0.0], 0.0005, 200.0), "T_small": _bar_T(p)}


# ================================================================== viscosity by capillary flow (Poiseuille's method)
def _pois_Q(p: dict) -> float:
    return PI * p["rho"] * p["g"] * p["hh"] * p["rc"] ** 4 / (8 * p["eta"] * p["lc"])


class Poiseuille:
    """A constant-head reservoir feeds a horizontal capillary; the liquid that runs out is collected in a measuring jar."""

    PARAMS = {"eta": 0.001002, "rho": 998.2, "rc": 0.0005, "lc": 0.15, "hh": 0.25, "g": 9.8, "Vt": 1.0e-5}
    VARS = ["t", "V", "V_ml", "Q", "Q_ml", "full", "t_full"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        q = _pois_Q(p)
        v = q * s["t"]
        return {"t": s["t"], "V": v, "V_ml": v * 1e6, "Q": q, "Q_ml": q * 1e6,
                "full": 1.0 if v >= p["Vt"] else 0.0, "t_full": p["Vt"] / q if q > 0 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        q = _pois_Q(p)
        return {"Q": q, "t_full": p["Vt"] / q if q > 0 else 0.0, "Q_ml": q * 1e6}


# ============================================================================ surface tension by Jaeger's bubble method
def _jaeger_H(p: dict) -> float:
    return (2 * p["Tst"] / (p["r"] * p["g"]) + p["hd"] * p["rhol"]) / p["rhom"]


class Jaeger:
    """Air is pushed slowly into a liquid through a fine orifice; the manometer reads the pressure just as a bubble breaks."""

    PARAMS = {"Tst": 0.07275, "r": 0.0003, "hd": 0.04, "rhol": 998.2, "rhom": 998.2, "g": 9.8, "tau": 1.2, "H0": 0.0}
    VARS = ["t", "H", "H_cm", "H_eq_cm", "p_bubble", "steady"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "H": p["H0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["H"] = _relax(s["H"], _jaeger_H(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        heq = _jaeger_H(p)
        return {"t": s["t"], "H": s["H"], "H_cm": s["H"] * 100, "H_eq_cm": heq * 100,
                "p_bubble": s["H"] * p["rhom"] * p["g"], "steady": 1.0 if abs(s["H"] - heq) < 1e-5 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        s = Jaeger.init(p)
        for _ in range(300):                        # 30 s: bubbles are coming at a steady rate
            Jaeger.step(s, p, 0.1)
        return {"H": s["H"], "H_eq": _jaeger_H(p)}


# ==================================================================================== uniform bending of a beam
def _uni_delta(p: dict) -> float:
    """Equal loads hung at the two overhangs make the bending moment constant between the knife edges."""
    return 3 * p["m"] * p["g"] * p["a"] * p["L"] * p["L"] / (2 * p["Y"] * p["b"] * p["d"] ** 3)


class UniBend:
    """A beam on two knife edges with equal loads hung beyond each edge: it bends into an arc of one radius."""

    PARAMS = {"Y": 2.0e11, "b": 0.025, "d": 0.005, "L": 0.7, "a": 0.12, "m": 0.0, "g": 9.8, "tau": 0.5, "d0": 0.0}
    VARS = ["t", "delta", "delta_mm", "delta_eq_mm", "load_N", "I_beam"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "d": p["d0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["d"] = _relax(s["d"], _uni_delta(p), dt, p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "delta": s["d"], "delta_mm": s["d"] * 1000, "delta_eq_mm": _uni_delta(p) * 1000,
                "load_N": p["m"] * p["g"], "I_beam": p["b"] * p["d"] ** 3 / 12}

    @staticmethod
    def measure(p, cfg=None):
        s = UniBend.init(p)
        for _ in range(200):
            UniBend.step(s, p, 0.1)
        return {"delta": s["d"], "delta_eq": _uni_delta(p)}


# ======================================================== travelling microscope: least count and repeated readings
def _lehmer(seed: int) -> int:
    return (seed * 16807) % 2147483647


def _tm_z(p: dict, i: int) -> float:
    """A fixed, reproducible 'observer' spread: twelve Lehmer uniforms minus six (Irwin-Hall, mean 0, sd 1)."""
    s = (int(p["seed"]) + 1) * 7919 + (i + 1) * 104729
    s = s % 2147483647
    if s == 0:
        s = 1
    u = 0.0
    for _ in range(12):
        s = _lehmer(s)
        u += s / 2147483647
    return u - 6.0


def _tm_lc(p: dict) -> float:
    return p["pitch"] / p["ndiv"]


def _tm_read(p: dict, i: int) -> float:
    lc = _tm_lc(p)
    x = p["L"] + p["ze"] + p["sigma"] * _tm_z(p, i)
    return math.floor(x / lc + 0.5) * lc


def _tm_mean(p: dict) -> float:
    n = max(1, int(p["nrep"]))
    return sum(_tm_read(p, i) for i in range(n)) / n


class TravMicro:
    """A travelling microscope reading a small dimension: main scale + vernier, and a different value every time."""

    PARAMS = {"L": 0.025, "pitch": 0.0005, "ndiv": 50.0, "ze": 0.0, "sigma": 0.00008, "idx": 0.0, "nrep": 10.0,
              "seed": 7.0}
    VARS = ["x", "x_mm", "x_cm", "msr_mm", "vsd", "lc_mm", "lc_cm", "mean_mm", "sd_mm"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        lc = _tm_lc(p)
        x = _tm_read(p, int(p["idx"]))
        nd = math.floor(x / lc + 0.5)
        whole = math.floor(nd / p["ndiv"])
        return {"x": x, "x_mm": x * 1000, "x_cm": x * 100, "msr_mm": whole * p["pitch"] * 1000,
                "vsd": nd - whole * p["ndiv"], "lc_mm": lc * 1000, "lc_cm": lc * 100,
                "mean_mm": _tm_mean(p) * 1000, "sd_mm": TravMicro.measure(p)["sd"] * 1000}

    @staticmethod
    def measure(p, cfg=None):
        n = max(1, int(p["nrep"]))
        xs = [_tm_read(p, i) for i in range(n)]
        mean = sum(xs) / n
        if n > 1:
            var = sum((x - mean) * (x - mean) for x in xs) / (n - 1)
        else:
            var = 0.0
        sd = math.sqrt(var)
        return {"mean": mean, "sd": sd, "se": sd / math.sqrt(n), "x": _tm_read(p, int(p["idx"])),
                "lc": _tm_lc(p)}


# ================================================================= free fall between two photo-gates (digital timing)
def _ff_t(p: dict) -> float:
    return math.sqrt(2 * p["h"] / p["g"])


class FreeFall:
    """An electromagnet drops a steel ball; it breaks the beam of the upper gate and then of the lower one, h apart."""

    PARAMS = {"g": 9.8, "h": 0.5, "t0": 0.0}
    VARS = ["t", "y", "v", "landed", "t_fall", "v_end"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        tf = _ff_t(p)
        t = min(max(s["t"] - p["t0"], 0.0), tf)
        return {"t": s["t"], "y": 0.5 * p["g"] * t * t, "v": p["g"] * t,
                "landed": 1.0 if s["t"] - p["t0"] >= tf else 0.0, "t_fall": tf, "v_end": p["g"] * tf}

    @staticmethod
    def measure(p, cfg=None):
        tf = _ff_t(p)
        return {"t": tf, "v": p["g"] * tf, "v_mid": math.sqrt(p["g"] * p["h"] / 2) * math.sqrt(2)}


# ==================================================================== one-dimensional collisions on an air track
def _coll_v1(p: dict) -> float:
    return ((p["m1"] - p["e"] * p["m2"]) * p["u1"]) / (p["m1"] + p["m2"])


def _coll_v2(p: dict) -> float:
    return (p["m1"] * (1 + p["e"]) * p["u1"]) / (p["m1"] + p["m2"])


class Collide1D:
    """Two gliders on an almost frictionless air track: one is pushed at u1, the other waits at rest."""

    PARAMS = {"m1": 0.2, "m2": 0.3, "u1": 0.4, "e": 1.0, "gap": 0.4, "x20": 0.4}
    VARS = ["t", "x1", "x2", "v1", "v2", "hit", "tc", "p_before", "p_after"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        tc = p["gap"] / p["u1"] if p["u1"] > 0 else 1e9
        v1, v2 = _coll_v1(p), _coll_v2(p)
        if s["t"] <= tc:
            x1, x2, a, b, hit = p["u1"] * s["t"], p["x20"], p["u1"], 0.0, 0.0
        else:
            td = s["t"] - tc
            x1, x2, a, b, hit = p["u1"] * tc + v1 * td, p["x20"] + v2 * td, v1, v2, 1.0
        return {"t": s["t"], "x1": x1, "x2": x2, "v1": a, "v2": b, "hit": hit, "tc": tc,
                "p_before": p["m1"] * p["u1"], "p_after": p["m1"] * a + p["m2"] * b}

    @staticmethod
    def measure(p, cfg=None):
        return {"u1": p["u1"], "v1": _coll_v1(p), "v2": _coll_v2(p),
                "tc": p["gap"] / p["u1"] if p["u1"] > 0 else 0.0}


KERNELS: dict[str, Any] = {"torsion": Torsion, "stattorsion": StatTorsion, "flywheel": Flywheel,
                           "barpend": BarPendulum, "poiseuille": Poiseuille, "jaeger": Jaeger,
                           "unibend": UniBend, "travmicro": TravMicro, "freefall": FreeFall,
                           "collide1d": Collide1D}
FAMILY = {"torsion": "mech", "stattorsion": "mech", "flywheel": "mech", "barpend": "osc_wave",
          "poiseuille": "mech", "jaeger": "mech", "unibend": "mech", "travmicro": "mech",
          "freefall": "mech", "collide1d": "mech"}

TEXTBOOK = {
    "torsion_T": _tors_T,
    "stat_theta": _stat_theta,
    "fly_t1": _fly_t1,
    "bar_T": _bar_T,
    "pois_Q": _pois_Q,
    "jaeger_H": _jaeger_H,
    "uni_delta": _uni_delta,
    "tm_L": lambda p: p["L"] + p["ze"],
    "ff_t": _ff_t,
    "coll_v2": _coll_v2,
}

CALCS = {
    "torsion_eta": {"label": "η (modulus of rigidity)", "unit": "Pa", "needs": ["Lw", "T"],
                    "fn": lambda rows, p: _mean([8 * PI * p["I"] * Lw / (p["rw"] ** 4 * T * T)
                                                 for Lw, T in _rows(rows, "Lw", "T") if T > 0])},
    "torsion_I": {"label": "I (moment of inertia)", "unit": "kg·m²", "needs": ["Lw", "T"],
                  "fn": lambda rows, p: _mean([p["eta"] * p["rw"] ** 4 * T * T / (8 * PI * Lw)
                                               for Lw, T in _rows(rows, "Lw", "T") if Lw > 0])},
    "stat_eta": {"label": "η (modulus of rigidity)", "unit": "Pa", "needs": ["m", "theta"],
                 "fn": lambda rows, p: _mean([4 * m * p["g"] * p["a"] * p["Lr"] / (PI * p["rr"] ** 4 * th)
                                              for m, th in _rows(rows, "m", "theta") if th > 0])},
    "fly_I": {"label": "I (moment of inertia)", "unit": "kg·m²", "needs": ["m", "n", "t1", "N"],
              "fn": lambda rows, p: _mean([_fly_I_one(p, m, n, t1, N)
                                           for m, n, t1, N in _rows(rows, "m", "n", "t1", "N") if t1 > 0 and N > 0])},
    "bar_g": {"label": "g (acceleration due to gravity)", "unit": "m/s²", "needs": ["h", "T"],
              "fn": lambda rows, p: _mean([4 * PI * PI * (p["Lb"] * p["Lb"] / 12 + h * h) / (T * T * h)
                                           for h, T in _rows(rows, "h", "T") if T > 0 and h > 0])},
    "pois_eta": {"label": "η (coefficient of viscosity)", "unit": "Pa·s", "needs": ["hh", "Q"],
                 "fn": lambda rows, p: _mean([PI * p["rho"] * p["g"] * hh * p["rc"] ** 4 / (8 * p["lc"] * Q)
                                              for hh, Q in _rows(rows, "hh", "Q") if Q > 0])},
    "jaeger_T": {"label": "T (surface tension)", "unit": "N/m", "needs": ["hd", "H"],
                 "fn": lambda rows, p: _mean([p["r"] * p["g"] * (H * p["rhom"] - hd * p["rhol"]) / 2
                                              for hd, H in _rows(rows, "hd", "H")])},
    "uni_Y": {"label": "Y (Young's modulus)", "unit": "Pa", "needs": ["m", "delta"],
              "fn": lambda rows, p: _mean([3 * m * p["g"] * p["a"] * p["L"] * p["L"] / (2 * p["b"] * p["d"] ** 3 * d)
                                           for m, d in _rows(rows, "m", "delta") if d > 0])},
    "tm_mean": {"label": "mean reading", "unit": "m", "needs": ["x"],
                "fn": lambda rows, p: _mean([x for (x,) in _rows(rows, "x")])},
    "ff_g": {"label": "g (acceleration due to gravity)", "unit": "m/s²", "needs": ["h", "t"],
             "fn": lambda rows, p: _mean([2 * h / (t * t) for h, t in _rows(rows, "h", "t") if t > 0])},
    "coll_m2": {"label": "m₂ (mass of the second glider)", "unit": "kg", "needs": ["u1", "v1", "v2"],
                "fn": lambda rows, p: _mean([p["m1"] * (u1 - v1) / v2
                                             for u1, v1, v2 in _rows(rows, "u1", "v1", "v2") if v2 != 0])},
}
