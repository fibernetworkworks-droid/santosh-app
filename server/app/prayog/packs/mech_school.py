"""Prayogshala kernel pack: Class 6-10 mechanics (NCERT Science VI-X + the NCERT Class IX Laboratory Manual).

Four kernels, one per piece of apparatus:
    track     - a body running along a straight track: uniform motion (motor on, level track) and uniformly
                accelerated motion (motor off, one end of the track raised). The reading is the TIME to a mark.
    pullblock - a block on a horizontal surface pulled by a spring balance: the least pull that just moves it is
                the limiting friction mu N. Same algorithm as the shared `incline` kernel with theta = 0.
    buoy      - a solid hanging from a spring balance and lowered into a liquid: upthrust, loss of weight,
                density by displacement, and the fraction of a floating body that stays under.
    sucker    - a rubber suction cup on a smooth plate: the pull that takes it off is (P_atm - P_in) x area.

Deterministic, SI, no randomness and no wall clock: the JavaScript twin in
`app/static/prayog/packs/mech_school.js` runs the same algorithms step for step.
This pack adds no CALCS entries on purpose (each rig computes its own result from the record book).
"""
from __future__ import annotations

import math

PI = math.pi


def _sub(dt: float, h: float) -> tuple[int, float]:
    n = max(1, math.ceil(dt / h - 1e-9))
    return n, dt / n


# ------------------------------------------------------------------------------------------------ motion on a track
class Track:
    """A body on a straight track: s = u t + 1/2 acc t^2, stopped by the buffer at s = len.

    `u` is the steady speed of a motor-driven car (acc = 0); `acc` is the acceleration of a free trolley on a
    track whose far end is raised (u = 0). `mark` is the scale mark the run is timed to."""

    PARAMS = {"u": 0.25, "acc": 0.0, "len": 1.0, "mark": 0.8}
    VARS = ["t", "s", "v", "car_x"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "s": 0.0, "v": p["u"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt
        x = p["u"] * s["t"] + 0.5 * p["acc"] * s["t"] * s["t"]
        if x >= p["len"]:
            s["s"], s["v"] = p["len"], 0.0
        else:
            s["s"], s["v"] = x, p["u"] + p["acc"] * s["t"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "s": s["s"], "v": s["v"], "car_x": s["s"]}

    @staticmethod
    def measure(p, cfg=None):
        """Time the run to `mark` by stepping the motion, exactly as the stopwatch does."""
        mark = min(p["mark"], p["len"])
        s = Track.init(p)
        h, t, prev = 0.0002, 0.0, 0.0
        while s["t"] < 30.0:
            prev = s["s"]
            Track.step(s, p, h)
            if s["s"] >= mark:
                t = s["t"] - h * (s["s"] - mark) / max(s["s"] - prev, 1e-12)
                break
        return {"t_mark": t, "v_mark": p["u"] + p["acc"] * t}


# ------------------------------------------------------------------------------------------------ friction: pull a block
class PullBlock:
    """Block (mass m plus `load` on top) on a horizontal surface, pulled along it by a force P.

    It stays at rest while P <= mu N, N = (m + load) g; after that a = (P - mu N) / (m + load)."""

    PARAMS = {"mu": 0.35, "m": 0.5, "load": 0.0, "P": 0.0, "g": 9.8, "len": 0.3}
    VARS = ["t", "s", "v", "a", "moving", "N", "f", "P"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "s": 0.0, "v": 0.0, "a": 0.0}

    @staticmethod
    def _adv(s, p, h):
        M = p["m"] + p["load"]
        fr = p["mu"] * M * p["g"]
        drive = p["P"]
        if s["v"] == 0.0:
            if abs(drive) <= fr:
                s["a"] = 0.0
                return
            a = (drive - fr * (1.0 if drive > 0 else -1.0)) / M
        else:
            a = (drive - fr * (1.0 if s["v"] > 0 else -1.0)) / M
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
            PullBlock._adv(s, p, h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        M = p["m"] + p["load"]
        return {"t": s["t"], "s": s["s"], "v": s["v"], "a": s["a"], "moving": 1.0 if s["v"] != 0.0 else 0.0,
                "N": M * p["g"], "f": p["mu"] * M * p["g"], "P": p["P"]}

    @staticmethod
    def _moves(p, P):
        q = dict(p, P=P, len=1e6)
        s = {"t": 0.0, "s": 1.0, "v": 0.0, "a": 0.0}
        for _ in range(250):
            PullBlock._adv(s, q, 0.002)
        return s["s"] > 1.0 + 1e-9

    @staticmethod
    def measure(p, cfg=None):
        lo, hi = 0.0, 4 * (p["m"] + p["load"]) * p["g"] * max(p["mu"], 0.25) + 1.0
        for _ in range(60):                      # the least pull that just starts the block moving
            mid = (lo + hi) / 2
            if PullBlock._moves(p, mid):
                hi = mid
            else:
                lo = mid
        return {"P_min": hi, "N": (p["m"] + p["load"]) * p["g"]}


# ------------------------------------------------------------------------------------------------ upthrust and density
class Buoy:
    """A solid of volume V hanging from a spring balance, lowered into a liquid of density rho_l.

    `frac` is the fraction of the solid under the surface. Upthrust U = rho_l g V frac (Archimedes), so the
    balance reads W - U; the liquid level in a jar of cross-section Acyl rises by V frac / Acyl. A solid lighter
    than the liquid floats with the fraction rho_s / rho_l under the surface."""

    PARAMS = {"rho_s": 2700.0, "rho_l": 998.0, "V": 1.2e-4, "g": 9.8, "frac": 0.0, "Acyl": 1.264e-3}
    VARS = ["W", "U", "Wapp", "loss", "frac_float", "floats", "dh", "level"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        fr = min(max(p["frac"], 0.0), 1.0)
        W = p["rho_s"] * p["V"] * p["g"]
        U = p["rho_l"] * p["g"] * p["V"] * fr
        Wapp = max(0.0, W - U)
        return {"W": W, "U": U, "Wapp": Wapp, "loss": W - Wapp,
                "frac_float": min(1.0, p["rho_s"] / p["rho_l"]), "floats": 1.0 if p["rho_s"] < p["rho_l"] else 0.0,
                "dh": p["V"] * fr / p["Acyl"], "level": p["V"] * fr / p["Acyl"]}

    @staticmethod
    def measure(p, cfg=None):
        W = p["rho_s"] * p["V"] * p["g"]
        U = p["rho_l"] * p["g"] * p["V"]
        Wapp = max(0.0, W - U)
        dh = p["V"] / p["Acyl"]                  # the rise of the liquid level, as the jar's scale shows it
        Vm = p["Acyl"] * dh                      # volume read back off that rise
        return {"W": W, "U": U, "Wapp": Wapp, "loss": W - Wapp, "dh": dh,
                "rho": (W / p["g"]) / Vm, "frac_float": min(1.0, p["rho_s"] / p["rho_l"])}


# ------------------------------------------------------------------------------------------------ atmospheric pressure
class Sucker:
    """A rubber suction cup of diameter d pressed on a smooth plate: the air inside is at P_in, outside at P_atm,
    so the plate holds it with a force (P_atm - P_in) x pi d^2 / 4. A bigger pull than that takes it off."""

    PARAMS = {"Patm": 101325.0, "Pin": 0.0, "d": 0.01, "P": 0.0, "g": 9.8}
    VARS = ["t", "P", "A", "F_hold", "off"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "off": 0.0}

    @staticmethod
    def _hold(p):
        return (p["Patm"] - p["Pin"]) * PI * p["d"] * p["d"] / 4

    @staticmethod
    def step(s, p, dt, cfg=None):
        if p["P"] > Sucker._hold(p):
            s["off"] = 1.0
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "P": p["P"], "A": PI * p["d"] * p["d"] / 4, "F_hold": Sucker._hold(p), "off": s["off"]}

    @staticmethod
    def measure(p, cfg=None):
        lo, hi = 0.0, 4 * Sucker._hold(p) + 1.0
        for _ in range(60):                      # the least pull that takes the sucker off
            mid = (lo + hi) / 2
            s = Sucker.init(p)
            Sucker.step(s, dict(p, P=mid), 0.01)
            if s["off"] > 0.5:
                hi = mid
            else:
                lo = mid
        return {"F_off": hi, "A": PI * p["d"] * p["d"] / 4}


# ------------------------------------------------------------------------------------------------ registration
KERNELS = {"track": Track, "pullblock": PullBlock, "buoy": Buoy, "sucker": Sucker}
FAMILY = {"track": "mech", "pullblock": "mech", "buoy": "mech", "sucker": "mech"}
TEXTBOOK = {
    # s = u t + 1/2 a t^2 solved for t
    "track_t": lambda p: (min(p["mark"], p["len"]) / p["u"] if abs(p["acc"]) < 1e-12 else
                          (-p["u"] + math.sqrt(p["u"] * p["u"] + 2 * p["acc"] * min(p["mark"], p["len"]))) / p["acc"]),
    "friction_Pmin": lambda p: p["mu"] * (p["m"] + p["load"]) * p["g"],
    "arch_loss": lambda p: p["rho_l"] * p["g"] * p["V"],
    "solid_rho": lambda p: p["rho_s"],
    "sucker_F": lambda p: (p["Patm"] - p["Pin"]) * PI * p["d"] * p["d"] / 4,
}
CALCS: dict = {}
