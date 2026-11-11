"""Prayogshala kernel pack: school (Class 6-10) measurement, sound and heat physics.

New physics for the school set-ups of `syllabus/physics/school-6-10.json` (chapters Measurement, Sound, Heat).
Every kernel here has an EXACT JavaScript twin in `app/static/prayog/packs/wave_heat_school.js`, so the phone and
the server give the same numbers. Deterministic: no randomness, no wall clock.

    length_measure   laying a unit (hand span, cubit, foot step, metre scale, thread) along a length
    conduction_fin   a metal rod / spoon heated at one end: the fin equation, wax pins melting in turn
    thermo_bath      a liquid warmed by a lab burner, with a melting / boiling plateau
    wave_pulse       a pulse on a stretched slinky or string: v = sqrt(T / mu)

No CALCS are added on purpose: the shipped `gauge_mean` (the mean of the `reading` column) is the right
observation-table result for all of these, and tests/test_v0418_prayog.py maps every CALCS name to a kernel by
hand, so a new CALCS name would break it.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi


def _round_to(value: float, lc: float) -> float:
    """A reading taken on an instrument of least count `lc` (both twins must round identically)."""
    if lc <= 0:
        return value
    return math.floor(value / lc + 0.5) * lc


def _sub(dt: float, h: float) -> tuple[int, float]:
    n = max(1, int(math.ceil(dt / h - 1e-9)))
    return n, dt / n


def _sound_v(Tc: float) -> float:
    """Speed of sound in air at t degC: v = 331.3 sqrt(1 + t / 273.15) m/s."""
    return 331.3 * math.sqrt(1 + Tc / 273.15)


# ----------------------------------------------------------------------------------- measurement of a length
class LengthMeasure:
    """Measuring a length by laying a unit along it.

    `L` is the TRUE length of the path being measured (for a curved line, the length along the curve, which a
    thread picks up). `unit` is one unit of the method (a hand span, a cubit, a foot step, 1 mm on a metre
    scale) and `lc` is the smallest part of that unit the eye can read. The reading is the true length rounded
    to the least count, plus any parallax error `par` made by looking from the side instead of from above.
    """

    PARAMS = {"L": 0.237, "unit": 0.001, "lc": 0.001, "par": 0.0}
    VARS = ["t", "L", "unit", "lc", "count", "reading", "par"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        reading = _round_to(p["L"] + p["par"], p["lc"])
        return {"t": s.get("t", 0.0), "L": p["L"], "unit": p["unit"], "lc": p["lc"],
                "count": p["L"] / p["unit"] if p["unit"] else 0.0, "reading": reading, "par": p["par"]}

    @staticmethod
    def measure(p, cfg=None):
        v = LengthMeasure.view({"t": 0.0}, p)
        return {"reading": v["reading"], "count": v["count"], "units": v["reading"] / p["unit"] if p["unit"] else 0.0}


# ----------------------------------------------------------------------------------- conduction along a rod
class ConductionFin:
    """A metal rod (or a spoon handle) heated at one end and losing heat to the room along its length.

    Steady state is the standard fin equation with an insulated far end:
        T(x) = Ts + (Th - Ts) cosh((Lr - x) / lam) / cosh(Lr / lam),
        lam = sqrt(k A / (h P)) = sqrt(k d / (4 h))     for a round rod (A = pi d^2 / 4, P = pi d).
    The rod reaches that profile first order in time, with the diffusion time scale of the point itself,
        tau(x) = x^2 / (4 alpha) + t0,   T(x, t) = Ts + (T(x) - Ts) (1 - e^(-t/tau(x))),
    so a wax-stuck pin at distance x falls when T(x, t) first reaches the wax's melting point.
    """

    PARAMS = {"k": 401.0, "d": 0.012, "Lr": 0.3, "Th": 95.0, "Ts": 30.0, "h": 12.0,
              "alpha": 1.17e-4, "Tmelt": 52.0, "xm": 0.25, "t0": 4.0}
    VARS = ["t", "Tx", "Tend", "Tmid", "lam", "Thot", "frac"]

    @staticmethod
    def lam(p):
        return math.sqrt(p["k"] * p["d"] / (4 * p["h"]))

    @staticmethod
    def steady(p, x):
        lam = ConductionFin.lam(p)
        return p["Ts"] + (p["Th"] - p["Ts"]) * math.cosh((p["Lr"] - x) / lam) / math.cosh(p["Lr"] / lam)

    @staticmethod
    def tau(p, x):
        return x * x / (4 * p["alpha"]) + p["t0"]

    @staticmethod
    def at(p, x, t):
        ss = ConductionFin.steady(p, x)
        return p["Ts"] + (ss - p["Ts"]) * (1 - math.exp(-t / ConductionFin.tau(p, x)))

    @staticmethod
    def melt_time(p, x):
        """When the wax at x reaches its melting point (0 if that point never gets that hot)."""
        ss = ConductionFin.steady(p, x)
        if ss <= p["Tmelt"] + 1e-9 or p["Tmelt"] <= p["Ts"]:
            return 0.0
        return -ConductionFin.tau(p, x) * math.log(1 - (p["Tmelt"] - p["Ts"]) / (ss - p["Ts"]))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        t = s.get("t", 0.0)
        return {"t": t, "Tx": ConductionFin.at(p, p["xm"], t), "Tend": ConductionFin.at(p, p["Lr"], t),
                "Tmid": ConductionFin.at(p, p["Lr"] / 2, t), "lam": ConductionFin.lam(p), "Thot": p["Th"],
                "frac": 1 - math.exp(-t / ConductionFin.tau(p, p["xm"]))}

    @staticmethod
    def measure(p, cfg=None):
        """The thermometer at the measuring point once the rod has settled (it is read after 30 tau)."""
        s = ConductionFin.init(p)
        ConductionFin.step(s, p, 30 * ConductionFin.tau(p, p["Lr"]))
        v = ConductionFin.view(s, p)
        return {"Tx": v["Tx"], "Tend": v["Tend"], "lam": v["lam"], "t_melt": ConductionFin.melt_time(p, p["xm"])}


# ----------------------------------------------------------------------------------- heating, melting, boiling
class ThermoBath:
    """A liquid in a vessel warmed by a lab burner and losing heat to the room:
        C dT/dt = P - hA (T - Ts),
    with a phase plateau: while latent heat Q is left, every joule goes into the change of state and the
    temperature holds at Tp (ice melting at 0 degC, water boiling at 100 degC under one atmosphere). The
    thermometer is read to its least count lc. Stepped in 0.05 s sub-steps so both twins agree exactly.
    """

    PARAMS = {"T0": 28.0, "Ts": 30.0, "P": 0.0, "C": 1256.0, "hA": 2.0, "Tp": 100.0, "Q0": 0.0, "lc": 0.5}
    VARS = ["t", "T", "reading", "Q", "changing"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["T0"], "Q": p["Q0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.05)
        for _ in range(n):
            net = p["P"] - p["hA"] * (s["T"] - p["Ts"])
            if s["Q"] > 0 and s["T"] >= p["Tp"] - 1e-9:
                s["T"] = p["Tp"]
                s["Q"] = s["Q"] - net * h
                if s["Q"] < 0:
                    s["Q"] = 0.0
            else:
                s["T"] = s["T"] + net / p["C"] * h
                if s["Q"] > 0 and s["T"] > p["Tp"]:
                    s["T"] = p["Tp"]
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        changing = 1.0 if (s["Q"] > 0 and abs(s["T"] - p["Tp"]) < 1e-6) else 0.0
        return {"t": s["t"], "T": s["T"], "reading": _round_to(s["T"], p["lc"]), "Q": s["Q"], "changing": changing}

    @staticmethod
    def measure(p, cfg=None):
        """Readings every 5 s: the thermometer now, and the temperature it holds while the state changes."""
        s = ThermoBath.init(p)
        hold: list[float] = []
        while s["t"] < 6000.0 and len(hold) < 5:
            ThermoBath.step(s, p, 5.0)
            v = ThermoBath.view(s, p)
            if v["changing"] > 0.5:
                hold.append(v["reading"])
        plateau = sum(hold) / len(hold) if hold else _round_to(p["Tp"], p["lc"])
        return {"reading": _round_to(p["T0"], p["lc"]), "Tplateau": plateau, "Tplateau_K": plateau + 273.15,
                "T_end": s["T"]}


# ----------------------------------------------------------------------------------- a pulse on a slinky / string
class WavePulse:
    """A pulse sent along a stretched slinky or string of mass per unit length mu under tension Tn.
    It travels at v = sqrt(Tn / mu) and turns back at each fixed end, so the time for `nrefl` lengths is
    nrefl * Lspan / v. A transverse shake moves the coils across the line, a longitudinal push along it;
    both travel at the same speed here because the tension and the mass per unit length do not change."""

    PARAMS = {"Tn": 8.0, "mu": 0.0725, "Lspan": 3.0, "nrefl": 4.0, "mode": 0.0}
    VARS = ["t", "x", "v", "trips", "running", "mode"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "d": 0.0, "running": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        if s["running"] > 0.5:
            s["d"] += math.sqrt(p["Tn"] / p["mu"]) * dt
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        v = math.sqrt(p["Tn"] / p["mu"])
        trips = s["d"] / p["Lspan"]
        leg = trips - math.floor(trips)
        x = leg * p["Lspan"] if int(math.floor(trips)) % 2 == 0 else (1 - leg) * p["Lspan"]
        return {"t": s["t"], "x": x, "v": v, "trips": trips, "running": s["running"], "mode": p["mode"]}

    @staticmethod
    def measure(p, cfg=None):
        """The stopwatch reading for `nrefl` lengths of the slinky, and the speed worked out from it."""
        st = WavePulse.init(p)
        st["running"] = 1.0
        n = int(round(p["nrefl"]))
        target = n * p["Lspan"]
        while st["d"] < target and st["t"] < 600.0:
            WavePulse.step(st, p, 0.001)
        return {"t_trip": st["t"], "v_meas": target / st["t"] if st["t"] > 0 else 0.0,
                "v": math.sqrt(p["Tn"] / p["mu"])}


KERNELS: dict[str, Any] = {
    "length_measure": LengthMeasure,
    "conduction_fin": ConductionFin,
    "thermo_bath": ThermoBath,
    "wave_pulse": WavePulse,
}
FAMILY = {"length_measure": "mech", "conduction_fin": "thermo", "thermo_bath": "thermo",
          "wave_pulse": "osc_wave"}
TEXTBOOK = {
    # a measurement is right when it gives back the true length (NCERT Class VI, Motion and Measurement of Distances)
    "length_true": lambda p: p["L"],
    # fin equation, insulated far end (conduction along a rod, NCERT Class VII Heat / standard heat transfer)
    "fin_Tx": lambda p: (p["Ts"] + (p["Th"] - p["Ts"]) * math.cosh((p["Lr"] - p["xm"]) / math.sqrt(p["k"] * p["d"] / (4 * p["h"])))
                         / math.cosh(p["Lr"] / math.sqrt(p["k"] * p["d"] / (4 * p["h"])))),
    # the temperature of a change of state, in kelvin (0 degC melting, 100 degC boiling at 1 atm)
    "phase_T_K": lambda p: p["Tp"] + 273.15,
    # a thermometer reads the temperature it is put in
    "bath_T": lambda p: p["T0"],
    # speed of a wave on a stretched string: v = sqrt(T / mu) (NCERT Class IX Sound)
    "wave_v": lambda p: math.sqrt(p["Tn"] / p["mu"]),
}
