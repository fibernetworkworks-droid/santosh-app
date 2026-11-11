"""Kernel pack: the B.Sc. heat, thermoelectric, wave and ultrasound benches (undergraduate Prayogshala).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/heat_wave_ug.js` (same formulas, same order of operations, so both give the same numbers).
Nothing here repeats `packs/wave_heat_school.py` (its fin, bath and slinky kernels are school level) or `packs/mech11.py`.

Kernels, with the textbook relation each one is checked against (1 %):
    hw_searle     Searle's bar, steady flow      K = m c (T_out - T_in) (x2 - x1) / (t A (th1 - th2))
    hw_lees       Lee and Charlton's disc        k = m s (dth/dt) (r + 2h) / (2r + 2h) . d / (pi r^2 (th1 - th2))
    hw_tcouple    thermocouple + water/oil bath  e = a (T - Tc) + q (T^2 - Tc^2);  neutral temperature Tn = -a / (2q)
    hw_rtd        Pt resistance thermometer      R = R0 (1 + A t + B t^2) (IEC 60751);  alpha = (R100 - R0) / (100 R0)
    hw_melde      Melde's string                 f = (p / l) sqrt(T / mu) (transverse),  f = (p / 2l) sqrt(T / mu) (longitudinal)
    hw_lissajous  two SHMs on a CRO              fy / fx = (touches on the top edge) / (touches on the side edge)
    hw_kundt      Kundt's dust tube              v_rod = v_air . L_rod / d,  d = node spacing
    hw_usonic     ultrasonic interferometer      v = 2 f d / n  (n maxima over a reflector move d), beta = 1 / (rho v^2)
Everything is SI and deterministic: no randomness drawn from the system, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi


def _sub(dt: float, h: float) -> tuple[int, float]:
    n = max(1, int(math.ceil(dt / h - 1e-9)))
    return n, dt / n


def _round_to(value: float, lc: float) -> float:
    """A reading taken on an instrument of least count `lc` (both twins round identically)."""
    if lc <= 0:
        return value
    return math.floor(value / lc + 0.5) * lc


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


def _gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a if a else 1


def _bath(s: dict, p: dict, dt: float) -> None:
    """A stirred bath on a heater: C dT/dt = P on - hA (T - Ts), held at Tcap (boiling water, an oil bath's limit)."""
    n, h = _sub(dt, 0.05)
    for _ in range(n):
        s["T"] = s["T"] + (p["P"] * s["on"] - p["hA"] * (s["T"] - p["Ts"])) / p["C"] * h
        if s["T"] > p["Tcap"]:
            s["T"] = p["Tcap"]
    s["t"] += dt


# ------------------------------------------------------------------------------------------ Searle's apparatus
class SearleBar:
    """A lagged metal bar, steam at one end and a water-cooled coil at the other (Searle's apparatus).

    Steady state: the heat the water carries away, H = mdot cw (Tout - Tin), is the heat that went down the bar,
    H = K A (th1 - th2) / (x2 - x1). The coil takes a fraction `eps` of the temperature difference between the cold end
    and the inlet water, so  H = mdot cw eps (Th - Tin) / (1 + mdot cw eps Lb / (K A)),  th(x) = Th - (H / K A) x.
    Every thermometer approaches its steady reading first order in time with the constant `tau`.
    """

    PARAMS = {"K": 401.0, "r": 0.0125, "x1": 0.12, "x2": 0.22, "Lb": 0.40, "Th": 100.0, "Tin": 26.0,
              "mdot": 9.4e-4, "eps": 0.9, "cw": 4186.0, "tau": 420.0, "lc": 0.1}
    VARS = ["t", "th1", "th2", "Tin", "Tout", "H", "grad", "dth1"]

    @staticmethod
    def steady(p):
        A = PI * p["r"] * p["r"]
        KA = p["K"] * A
        C = p["mdot"] * p["cw"]
        H = C * p["eps"] * (p["Th"] - p["Tin"]) / (1 + C * p["eps"] * p["Lb"] / KA)
        g = H / KA
        return {"A": A, "H": H, "g": g, "th1": p["Th"] - g * p["x1"], "th2": p["Th"] - g * p["x2"],
                "Tout": p["Tin"] + H / C}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ss = SearleBar.steady(p)
        e = math.exp(-s["t"] / p["tau"])
        f = 1 - e
        return {"t": s["t"], "th1": p["Tin"] + (ss["th1"] - p["Tin"]) * f, "th2": p["Tin"] + (ss["th2"] - p["Tin"]) * f,
                "Tin": p["Tin"], "Tout": p["Tin"] + (ss["Tout"] - p["Tin"]) * f, "H": ss["H"] * f, "grad": ss["g"] * f,
                "dth1": (ss["th1"] - p["Tin"]) / p["tau"] * e}

    @staticmethod
    def measure(p, cfg=None):
        """Read the four thermometers long after the bar has settled and work K out from the water collected."""
        s = SearleBar.init(p)
        SearleBar.step(s, p, 30 * p["tau"])
        v = SearleBar.view(s, p)
        t_run = 300.0
        m = p["mdot"] * t_run
        A = PI * p["r"] * p["r"]
        K = m * p["cw"] * (v["Tout"] - v["Tin"]) * (p["x2"] - p["x1"]) / (t_run * A * (v["th1"] - v["th2"]))
        return {"K": K, "th1": v["th1"], "th2": v["th2"], "Tin": v["Tin"], "Tout": v["Tout"], "H": v["H"], "m": m}


# ------------------------------------------------------------------------------------------ Lee and Charlton's disc
class LeesDisc:
    """A bad conductor (glass, ebonite) as a thin disc between a heated plate at th1 and a brass disc B.

    Steady: conduction down the sample equals the loss from B's lower face and edge, with its top face covered:
        G1 (th1 - th2) = G2 (th2 - Ts),   G1 = k pi r^2 / d,   G2 = hc pi (r^2 + 2 r h).
    Bare, B cools by Newton's law over its whole surface: C dT/dt = - hc (2 pi r^2 + 2 pi r h) (T - Ts).
    `mode` 0 is the heating with the sample on, 1 the bare cooling from T0, 2 the bare disc heated by the steam chest
    laid straight on it (conductance Gd). Stepped in 0.05 s sub-steps.
    """

    PARAMS = {"k": 1.05, "d": 0.008, "r": 0.025, "h": 0.010, "rho": 8500.0, "s": 380.0, "hc": 9.0, "Th": 100.0,
              "Ts": 30.0, "T0": 30.0, "mode": 0.0, "lc": 0.1, "Gd": 2.0}
    VARS = ["t", "T", "th2", "dTdt", "mB", "C"]

    @staticmethod
    def mass(p):
        return p["rho"] * PI * p["r"] * p["r"] * p["h"]

    @staticmethod
    def conds(p):
        G1 = p["k"] * PI * p["r"] * p["r"] / p["d"]
        G2 = p["hc"] * PI * (p["r"] * p["r"] + 2 * p["r"] * p["h"])
        return G1, G2

    @staticmethod
    def th2(p):
        G1, G2 = LeesDisc.conds(p)
        return (G1 * p["Th"] + G2 * p["Ts"]) / (G1 + G2)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["T0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.05)
        C = LeesDisc.mass(p) * p["s"]
        G1, G2 = LeesDisc.conds(p)
        Gb = p["hc"] * (2 * PI * p["r"] * p["r"] + 2 * PI * p["r"] * p["h"])
        for _ in range(n):
            if p["mode"] < 0.5:
                rate = (G1 * (p["Th"] - s["T"]) - G2 * (s["T"] - p["Ts"])) / C
            elif p["mode"] < 1.5:
                rate = -Gb * (s["T"] - p["Ts"]) / C
            else:
                rate = (p["Gd"] * (p["Th"] - s["T"]) - Gb * (s["T"] - p["Ts"])) / C
            s["T"] = s["T"] + rate * h
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        C = LeesDisc.mass(p) * p["s"]
        G1, G2 = LeesDisc.conds(p)
        Gb = p["hc"] * (2 * PI * p["r"] * p["r"] + 2 * PI * p["r"] * p["h"])
        if p["mode"] < 0.5:
            rate = (G1 * (p["Th"] - s["T"]) - G2 * (s["T"] - p["Ts"])) / C
        elif p["mode"] < 1.5:
            rate = -Gb * (s["T"] - p["Ts"]) / C
        else:
            rate = (p["Gd"] * (p["Th"] - s["T"]) - Gb * (s["T"] - p["Ts"])) / C
        return {"t": s["t"], "T": s["T"], "th2": LeesDisc.th2(p), "dTdt": rate, "mB": LeesDisc.mass(p), "C": C}

    @staticmethod
    def measure(p, cfg=None):
        """Steady th2 (heated 20 000 s), then the bare disc's cooling rate there, and k worked out from the formula."""
        a = dict(p)
        a["mode"] = 0.0
        s = LeesDisc.init(a)
        LeesDisc.step(s, a, 20000.0)
        th2 = s["T"]
        b = dict(p)
        b["mode"] = 1.0
        s2 = {"t": 0.0, "T": th2}
        rate = -LeesDisc.view(s2, b)["dTdt"]
        m = LeesDisc.mass(p)
        k = (m * p["s"] * rate * (p["r"] + 2 * p["h"]) / (2 * p["r"] + 2 * p["h"])) * p["d"] / (PI * p["r"] * p["r"] * (p["Th"] - th2))
        return {"k": k, "th2": th2, "rate": rate, "th1": p["Th"]}


# ------------------------------------------------------------------------------------------ thermocouple
class ThermocoupleBath:
    """A thermocouple with its cold junction at Tc (melting ice) and its hot junction in a stirred bath.

        e(T) = a (T - Tc) + q (T^2 - Tc^2)          (T in degC, e in volts)
    A potentiometer wire gives kp volts per metre, so the null length is l = e / kp. An op-amp amplifier of gain G
    gives Vout = G e. The bath is heated by P watts (switch `on`) and loses hA (T - Ts); it cannot pass Tcap.
    """

    PARAMS = {"a": 38.65e-6, "q": 4.14e-8, "Tc": 0.0, "kp": 0.008, "G": 0.0, "P": 150.0, "C": 1500.0, "hA": 1.0,
              "Ts": 30.0, "T0": 30.0, "on": 0.0, "Tcap": 100.0, "lc": 0.1, "Th": 60.0}
    VARS = ["t", "T", "reading", "e", "l", "Vout", "Tn"]

    @staticmethod
    def emf(p, T):
        return p["a"] * (T - p["Tc"]) + p["q"] * (T * T - p["Tc"] * p["Tc"])

    @staticmethod
    def neutral(p):
        return -p["a"] / (2 * p["q"]) if p["q"] < 0 else 0.0

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["T0"], "on": p["on"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        _bath(s, p, dt)

    @staticmethod
    def view(s, p, cfg=None):
        e = ThermocoupleBath.emf(p, s["T"])
        return {"t": s["t"], "T": s["T"], "reading": _round_to(s["T"], p["lc"]), "e": e, "l": e / p["kp"],
                "Vout": p["G"] * e, "Tn": ThermocoupleBath.neutral(p)}

    @staticmethod
    def measure(p, cfg=None):
        """The hot junction held at Th: the thermo-emf, the potentiometer null length, the amplifier output."""
        s = {"t": 0.0, "T": p["Th"], "on": 0.0}
        v = ThermocoupleBath.view(s, p)
        return {"e": v["e"], "l": v["l"], "Vout": v["Vout"], "slope": p["a"] + 2 * p["q"] * p["Th"],
                "Tn": v["Tn"], "emf": v["e"]}


# ------------------------------------------------------------------------------------------ resistance thermometer
class ResistanceThermometer:
    """A platinum resistance thermometer on a Wheatstone bridge (equal ratio arms), in a stirred bath.

        R(t) = R0 (1 + A t + B t^2)           (IEC 60751 / ITS-90: A = 3.9083e-3, B = -5.775e-7 for platinum)
    Null method: the decade box is set to R. Off-balance method: the bridge output with the fixed arm Rref and the
    supply Vs is  Vg = Vs (R / (R + Rref) - 1/2).
    """

    PARAMS = {"R0": 100.0, "A": 3.9083e-3, "B": -5.775e-7, "Rref": 100.0, "Vs": 5.0, "P": 150.0, "C": 1500.0,
              "hA": 1.0, "Ts": 30.0, "T0": 30.0, "on": 0.0, "Tcap": 100.0, "lc": 0.1, "Tm": 50.0, "mode": 0.0}
    VARS = ["t", "T", "reading", "R", "Vg"]

    @staticmethod
    def res(p, T):
        return p["R0"] * (1 + p["A"] * T + p["B"] * T * T)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["T0"], "on": p["on"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        _bath(s, p, dt)

    @staticmethod
    def view(s, p, cfg=None):
        R = ResistanceThermometer.res(p, s["T"])
        return {"t": s["t"], "T": s["T"], "reading": _round_to(s["T"], p["lc"]), "R": R,
                "Vg": p["Vs"] * (R / (R + p["Rref"]) - 0.5)}

    @staticmethod
    def measure(p, cfg=None):
        R0 = ResistanceThermometer.res(p, 0.0)
        R100 = ResistanceThermometer.res(p, 100.0)
        dt = 0.5
        slope = (ResistanceThermometer.res(p, p["Tm"] + dt) - ResistanceThermometer.res(p, p["Tm"] - dt)) / (2 * dt)
        return {"alpha": (R100 - R0) / (100.0 * R0), "R": ResistanceThermometer.res(p, p["Tm"]), "slope": slope,
                "R0": R0, "R100": R100}


# ------------------------------------------------------------------------------------------ Melde's experiment
class MeldeString:
    """A thread from a tuning fork over a pulley to a pan: tension T = M g, v = sqrt(T / mu).

    Transverse arrangement (fork across the thread): the thread vibrates at f/2. Longitudinal (fork along it): at f.
    p loops fit the length l when l = p lambda / 2, i.e. loops = 2 l f_s / v. The loops are sharp (amplitude
    1 / (1 + (d / w)^2)) only when `loops` is within w of a whole number.
    """

    PARAMS = {"f": 100.0, "mu": 0.0011, "L": 1.0, "M": 0.07, "g": 9.8, "mode": 0.0, "w": 0.012, "p0": 4.0}
    VARS = ["t", "T", "v", "fs", "loops", "p", "amp"]

    @staticmethod
    def fs(p):
        return p["f"] / 2 if p["mode"] < 0.5 else p["f"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        T = p["M"] * p["g"]
        v = math.sqrt(T / p["mu"]) if T > 0 else 0.0
        fs = MeldeString.fs(p)
        loops = 2 * p["L"] * fs / v if v > 0 else 0.0
        pr = math.floor(loops + 0.5)
        d = loops - pr
        amp = 1 / (1 + (d / p["w"]) ** 2) if pr >= 1 else 0.0
        return {"t": s["t"], "T": T, "v": v, "fs": fs, "loops": loops, "p": pr, "amp": amp}

    @staticmethod
    def measure(p, cfg=None):
        """The load for which p0 loops stand, and the fork frequency worked out from it."""
        fs = MeldeString.fs(p)
        v = 2 * p["L"] * fs / p["p0"]
        T = p["mu"] * v * v
        M = T / p["g"]
        k = 1.0 if p["mode"] < 0.5 else 0.5
        f = k * (p["p0"] / p["L"]) * math.sqrt(T / p["mu"])
        return {"M": M, "T": T, "f": f, "v": v}


# ------------------------------------------------------------------------------------------ Lissajous figures
class LissajousCRO:
    """Two sine waves on a CRO: x = ax sin(2 pi fx t), y = ay sin(2 pi fy t + phi).

    fy / fx = (touches on the top edge) / (touches on the side edge). With fy = fx the figure is an ellipse and
    sin(phi) = y0 / ymax (y0 where it cuts the y axis, ymax its top). `mode` 0 = frequency ratio, 1 = phase.
    """

    PARAMS = {"fx": 100.0, "fy": 150.0, "phi": 0.7854, "ax": 1.0, "ay": 1.0, "mode": 0.0}
    VARS = ["t", "x", "y", "ratio", "nt", "ns", "y0", "ymax", "phi_meas"]

    @staticmethod
    def frac(p):
        a = int(math.floor(p["fy"] * 10 + 0.5))
        b = int(math.floor(p["fx"] * 10 + 0.5))
        g = _gcd(a, b)
        return a // g, b // g

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        nt, ns = LissajousCRO.frac(p)
        t = s["t"]
        y0 = p["ay"] * math.sin(p["phi"])
        return {"t": t, "x": p["ax"] * math.sin(2 * PI * p["fx"] * t), "y": p["ay"] * math.sin(2 * PI * p["fy"] * t + p["phi"]),
                "ratio": p["fy"] / p["fx"], "nt": float(nt), "ns": float(ns), "y0": y0, "ymax": p["ay"],
                "phi_meas": math.asin(max(-1.0, min(1.0, y0 / p["ay"])))}

    @staticmethod
    def measure(p, cfg=None):
        nt, ns = LissajousCRO.frac(p)
        v = LissajousCRO.view({"t": 0.0}, p)
        return {"fy": p["fx"] * nt / ns, "nt": float(nt), "ns": float(ns), "phi": v["phi_meas"]}


# ------------------------------------------------------------------------------------------ Kundt's tube
class KundtTube:
    """A rod clamped at its middle, stroked so that it sings its fundamental f = v_rod / (2 L_rod), drives the air in
    a tube. The air column resonates when the piston stands a whole number of half wavelengths from the rod's
    disc; lycopodium dust then heaps at the nodes, d = v_air / (2 f) = v_air L_rod / v_rod apart.
    v_air = 331.3 sqrt(1 + t / 273.15)."""

    PARAMS = {"vr": 3436.0, "Lr": 1.0, "Tc": 25.0, "rho": 8470.0, "Lt": 1.0, "w": 0.18, "Lp": 0.5}
    VARS = ["t", "f", "vair", "d", "clarity", "n"]

    @staticmethod
    def vair(p):
        return 331.3 * math.sqrt(1 + p["Tc"] / 273.15)

    @staticmethod
    def spacing(p):
        return KundtTube.vair(p) * p["Lr"] / p["vr"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        d = KundtTube.spacing(p)
        q = p["Lp"] / d
        n = math.floor(q + 0.5)
        off = (q - n)
        clarity = 1 / (1 + (off / p["w"]) ** 2) if n >= 1 else 0.0
        return {"t": s["t"], "f": p["vr"] / (2 * p["Lr"]), "vair": KundtTube.vair(p), "d": d, "clarity": clarity, "n": float(n)}

    @staticmethod
    def measure(p, cfg=None):
        """Piston set on the 8th half wavelength; the first and last of 8 dust heaps are read on the scale."""
        d = KundtTube.spacing(p)
        x_first = d
        x_last = 8 * d
        d_meas = (x_last - x_first) / 7.0
        v = KundtTube.vair(p) * p["Lr"] / d_meas
        return {"vr": v, "d": d_meas, "Y": p["rho"] * v * v, "vair": KundtTube.vair(p)}


# ------------------------------------------------------------------------------------------ ultrasonic interferometer
class UltrasonicInterferometer:
    """A 2 MHz crystal, a liquid cell and a movable reflector on a micrometer. The standing wave makes the crystal's
    current peak every lambda / 2 of reflector travel:  I(x) = Ib + Ia exp(-alpha x) cos^2(2 pi (x - x0) / lambda),
    lambda = v / f. Then  v = 2 f d / n  and the adiabatic compressibility beta = 1 / (rho v^2)."""

    PARAMS = {"v": 1482.0, "f": 2.0e6, "rho": 998.2, "x0": 0.00012, "Ib": 40.0, "Ia": 25.0, "alpha": 20.0}
    VARS = ["t", "lam", "I", "x"]

    @staticmethod
    def current(p, x):
        lam = p["v"] / p["f"]
        c = math.cos(2 * PI * (x - p["x0"]) / lam)
        return p["Ib"] + p["Ia"] * math.exp(-p["alpha"] * x) * c * c

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "x": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "lam": p["v"] / p["f"], "I": UltrasonicInterferometer.current(p, s["x"]), "x": s["x"]}

    @staticmethod
    def measure(p, cfg=None):
        """Ten successive maxima: their micrometer readings give d, then v and beta."""
        lam = p["v"] / p["f"]
        xs = [p["x0"] + (j + 1) * lam / 2 for j in range(11)]
        d = xs[10] - xs[0]
        v = 2 * p["f"] * d / 10.0
        return {"v": v, "d": d, "lam": 2 * d / 10.0, "beta": 1 / (p["rho"] * v * v)}


KERNELS: dict[str, Any] = {
    "hw_searle": SearleBar,
    "hw_lees": LeesDisc,
    "hw_tcouple": ThermocoupleBath,
    "hw_rtd": ResistanceThermometer,
    "hw_melde": MeldeString,
    "hw_lissajous": LissajousCRO,
    "hw_kundt": KundtTube,
    "hw_usonic": UltrasonicInterferometer,
}
FAMILY = {"hw_searle": "thermo", "hw_lees": "thermo", "hw_tcouple": "thermo", "hw_rtd": "thermo",
          "hw_melde": "osc_wave", "hw_lissajous": "osc_wave", "hw_kundt": "osc_wave", "hw_usonic": "osc_wave"}


def _fit2(xs: list[float], ys: list[float]):
    """Least-squares y = c0 + c1 x + c2 x^2 by the normal equations (Cramer's rule); None if degenerate."""
    n = len(xs)
    if n < 3:
        return None
    s1 = s2 = s3 = s4 = t0 = t1 = t2 = 0.0
    for x in xs:                                  # plain loops (not sum()): both twins add in the same order
        s1 += x
    for x in xs:
        s2 += x * x
    for x in xs:
        s3 += x * x * x
    for x in xs:
        s4 += x * x * x * x
    for y in ys:
        t0 += y
    for x, y in zip(xs, ys):
        t1 += x * y
    for x, y in zip(xs, ys):
        t2 += x * x * y
    det = n * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2)
    if abs(det) < 1e-300:
        return None
    d0 = t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)
    d1 = n * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2)
    d2 = n * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2)
    return d0 / det, d1 / det, d2 / det


def _tc_slope(rows, p):
    """dE/dT at 50 degC from a quadratic fit of the potentiometer readings (E = kp l) against T."""
    r = _rows(rows, "T", "l")
    f = _fit2([x[0] for x in r], [p["kp"] * x[1] for x in r])
    return f[1] + 2 * f[2] * 50.0 if f else 0.0


def _tc_neutral(rows, p):
    """The neutral temperature = the vertex of the parabola through the amplifier readings: Vout/G against T."""
    r = _rows(rows, "T", "Vout")
    g = p["G"] if p["G"] else 1.0
    f = _fit2([x[0] for x in r], [x[1] / g for x in r])
    return -f[1] / (2 * f[2]) if f and f[2] != 0 else 0.0


def _rtd_slope(rows, p):
    """dR/dt at 50 degC from a quadratic fit of the resistance against the bath temperature."""
    r = _rows(rows, "T", "R")
    f = _fit2([x[0] for x in r], [x[1] for x in r])
    return f[1] + 2 * f[2] * 50.0 if f else 0.0


def _rtd_alpha(rows, p):
    """alpha = (R100 - R0) / (100 R0) from the readings nearest the ice point and the steam point."""
    r = _rows(rows, "T", "R")
    if len(r) < 2:
        return 0.0
    lo = min(r, key=lambda x: abs(x[0]))
    hi = min(r, key=lambda x: abs(x[0] - 100.0))
    if lo[1] == 0 or hi[0] == lo[0]:
        return 0.0
    return (hi[1] - lo[1]) / ((hi[0] - lo[0]) * lo[1])


def _liss_fy(rows, p):
    return _mean([x[0] * x[1] / x[2] for x in _rows(rows, "fx", "nt", "ns") if x[2] > 0])


def _usonic_v(rows, p):
    """v = 2 f d / n from the first and last maxima: the readings x (m) and the maximum numbers n."""
    r = sorted(_rows(rows, "n", "x"))
    if len(r) < 2 or r[-1][0] == r[0][0]:
        return 0.0
    return 2 * p["f"] * (r[-1][1] - r[0][1]) / (r[-1][0] - r[0][0])


CALCS = {
    "hw_searle_K": {"label": "K (thermal conductivity)", "unit": "W/(m·K)", "needs": ["m", "t", "dTw", "dth"],
                    "fn": lambda rows, p: _mean([x[0] * p["cw"] * x[2] * (p["x2"] - p["x1"]) / (x[1] * PI * p["r"] * p["r"] * x[3])
                                                 for x in _rows(rows, "m", "t", "dTw", "dth") if x[1] > 0 and x[3] > 0])},
    "hw_lees_k": {"label": "k (thermal conductivity)", "unit": "W/(m·K)", "needs": ["th1", "th2", "dtdt"],
                  "fn": lambda rows, p: _mean([LeesDisc.mass(p) * p["s"] * x[2] * (p["r"] + 2 * p["h"]) / (2 * p["r"] + 2 * p["h"])
                                               * p["d"] / (PI * p["r"] * p["r"] * (x[0] - x[1]))
                                               for x in _rows(rows, "th1", "th2", "dtdt") if x[0] - x[1] > 0])},
    "hw_tc_slope": {"label": "dE/dT at 50 °C", "unit": "V/K", "needs": ["T", "l"], "fn": _tc_slope},
    "hw_tc_neutral": {"label": "neutral temperature", "unit": "°C", "needs": ["T", "Vout"], "fn": _tc_neutral},
    "hw_rtd_slope": {"label": "dR/dt at 50 °C", "unit": "Ω/K", "needs": ["T", "R"], "fn": _rtd_slope},
    "hw_rtd_alpha": {"label": "α (0 to 100 °C)", "unit": "1/K", "needs": ["T", "R"], "fn": _rtd_alpha},
    "hw_melde_f": {"label": "f (tuning fork)", "unit": "Hz", "needs": ["M", "p"],
                   "fn": lambda rows, p: _mean([(1.0 if p["mode"] < 0.5 else 0.5) * (x[1] / p["L"])
                                                * math.sqrt(x[0] * p["g"] / p["mu"])
                                                for x in _rows(rows, "M", "p") if x[0] > 0])},
    "hw_liss_fy": {"label": "f (unknown)", "unit": "Hz", "needs": ["fx", "nt", "ns"], "fn": _liss_fy},
    "hw_liss_phi": {"label": "φ", "unit": "rad", "needs": ["y0", "ymax"],
                    "fn": lambda rows, p: _mean([math.asin(max(-1.0, min(1.0, x[0] / x[1])))
                                                 for x in _rows(rows, "y0", "ymax") if x[1] > 0])},
    "hw_kundt_v": {"label": "v (rod)", "unit": "m/s", "needs": ["Lrod", "dd"],
                   "fn": lambda rows, p: _mean([KundtTube.vair(p) * x[0] / x[1] for x in _rows(rows, "Lrod", "dd") if x[1] > 0])},
    "hw_usonic_v": {"label": "v (ultrasound)", "unit": "m/s", "needs": ["n", "x"], "fn": _usonic_v},
}


TEXTBOOK = {
    # Fourier's law through the bar, written from the water's heat gain (Searle; CRC conductivities)
    "hw_searle_K": lambda p: p["K"],
    # the cooling-rate formula for the disc: the sample's own conductivity is what comes back
    "hw_lees_k": lambda p: p["k"],
    # thermo-emf at the hot junction: e = a (T - Tc) + q (T^2 - Tc^2)
    "hw_tc_emf": lambda p: p["a"] * (p["Th"] - p["Tc"]) + p["q"] * (p["Th"] ** 2 - p["Tc"] ** 2),
    # mean temperature coefficient of a platinum thermometer between 0 and 100 degC (IEC 60751: A + 100 B)
    "hw_rtd_alpha": lambda p: p["A"] + 100.0 * p["B"],
    # slope of the calibration curve at Tm
    "hw_rtd_slope": lambda p: p["R0"] * (p["A"] + 2.0 * p["B"] * p["Tm"]),
    # Melde: the mass for which p0 loops stand gives the fork frequency back
    "hw_melde_f": lambda p: p["f"],
    # Lissajous: the unknown frequency
    "hw_liss_fy": lambda p: p["fy"],
    # Kundt: v_rod = sqrt(Y / rho) is the rod's own speed
    "hw_kundt_v": lambda p: p["vr"],
    # ultrasonic interferometer: v = f lambda
    "hw_usonic_v": lambda p: p["v"],
}
