"""Kernel pack `elec11`: the physics the Class XI / XII electricity, optics and electronics set-ups need that the
shared kernels.py does not already carry (see `packs/__init__.py`). Its exact JavaScript twin is
`app/static/prayog/packs/elec11.js`; both must give the same numbers.

Most of Current Electricity needs NO new kernel at all - the general `circuit` kernel (modified nodal analysis driven
by `lab.cfg.net`) already solves a galvanometer bridge, a potentiometer wire or a conversion circuit - so this pack
carries their TEXTBOOK formulas only. New kernels here are the ones the solver cannot do: a Zener diode in reverse
breakdown, a common-emitter transistor, a light-dependent resistor, single-slit diffraction and Malus's law.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
VT = 0.025852                 # thermal voltage at 300 K, the same constant kernels.py uses


# ============================================================================================ TEXTBOOK (circuit labs)
def _galv_half_ig(p: dict) -> float:
    """Cell Eb, series resistance Rh, galvanometer Rg with a shunt Sh across it: the current through the coil.
    Ohm's law + Kirchhoff, written out by hand - this is what the half-deflection reading is checked against."""
    return p["Eb"] * p["Sh"] / (p["Rh"] * (p["Rg"] + p["Sh"]) + p["Rg"] * p["Sh"])


def _galv_volt_ig(p: dict) -> float:
    """Galvanometer Rg in series with Rser across a supply Eb of internal resistance Rint (converted voltmeter)."""
    return p["Eb"] / (p["Rint"] + p["Rser"] + p["Rg"])


def _galv_amm_ig(p: dict) -> float:
    """Converted ammeter: the shunted galvanometer in series with the load Rl and the standard ammeter Ram."""
    return p["Eb"] * p["Sht"] / ((p["Rl"] + p["Ram"]) * (p["Rg"] + p["Sht"]) + p["Rg"] * p["Sht"])


def _pot_balance(p: dict) -> float:
    """Potentiometer: the balancing length (as a fraction of the wire) for a cell of emf Ec.
    The driver E0 sends I = E0/(Rh + Rw) through the wire of total resistance Rw, so the potential gradient is
    I*Rw per unit length and the balance comes where that equals Ec."""
    return p["Ec"] * (p["Rh"] + p["Rw"]) / (p["Rw"] * p["E0"])


def _pot_drop(p: dict) -> float:
    """The potential difference across the first `lj` (fraction) of the potentiometer wire, carrying a steady current."""
    return p["E0"] * p["Rw"] * p["lj"] / (p["Rh"] + p["Rw"])


def _bridge_comb_x(p: dict) -> float:
    """What is in the right gap of the metre bridge, from the three link keys: R1 alone (ka), R2 alone (kb), the two
    in parallel (both), or the two in series (the link key `ser`)."""
    r1, r2 = p["R1"], p["R2"]
    if p["ser"] >= 0.5:
        return r1 + r2
    if p["ka"] >= 0.5 and p["kb"] >= 0.5:
        return r1 * r2 / (r1 + r2)
    return r1 if p["ka"] >= 0.5 else r2


def _bridge_comb_l(p: dict) -> float:
    """Metre bridge, balancing length as a fraction from end A: R / X = l / (100 - l)."""
    return p["Rk"] / (p["Rk"] + _bridge_comb_x(p))


# ============================================================================================ Zener diode
class Zener:
    """A Zener diode in series with Rs across a supply Eb. Forward: the Shockley equation. Reverse: almost no current
    until the breakdown voltage Vz, then a steep rise with a small dynamic resistance Rz.

    The breakdown branch is the textbook piecewise-linear model I = (|V| - Vz)/Rz with the corner rounded over
    `knee` volts the way a real diode's is: I_bd = (u + sqrt(u^2 + knee^2)) / (2 Rz), u = |V| - Vz. That is a smooth
    maximum of u and 0, so a volt or two past breakdown it is the straight line the textbook draws (which is what the
    lab's check compares against), and at the knee itself it bends instead of snapping.
    `Eb` is the applied voltage: positive = forward bias, negative = reverse bias. Deterministic (bisection)."""

    PARAMS = {"Eb": -1.0, "Rs": 1000.0, "Vz": 5.1, "Rz": 10.0, "Is": 5e-9, "nD": 1.8, "knee": 0.02}
    VARS = ["t", "V_Z", "I_Z", "V_Rs", "P_Z"]

    @staticmethod
    def current(v: float, p: dict) -> float:
        """Current through the Zener for a voltage v across it (forward positive), in amperes."""
        fwd = p["Is"] * (math.exp(min(v / (p["nD"] * VT), 80.0)) - 1.0)
        u = -v - p["Vz"]
        k = p["knee"]
        bd = (u + math.sqrt(u * u + k * k)) / (2 * p["Rz"])
        return fwd - bd

    @staticmethod
    def solve(p: dict) -> float:
        """Eb = I Rs + V, solved for V by bisection (the current is monotonic in V)."""
        lo, hi = -abs(p["Vz"]) - abs(p["Eb"]) - 5.0, abs(p["Eb"]) + 5.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if Zener.current(mid, p) * p["Rs"] + mid > p["Eb"]:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        v = Zener.solve(p)
        i = Zener.current(v, p)
        return {"t": s.get("t", 0.0), "V_Z": v, "I_Z": i, "V_Rs": p["Eb"] - v, "P_Z": abs(v * i)}

    @staticmethod
    def measure(p, cfg=None):
        v = Zener.solve(p)
        return {"V_Z": v, "I_Z": Zener.current(v, p), "Vz_mag": -v}


def _zener_vr(p: dict) -> float:
    """Textbook: past breakdown the Zener holds V = Vz + Rz I with I = (|Eb| - Vz)/(Rs + Rz) (reverse bias)."""
    e = -p["Eb"]
    return -(p["Vz"] + p["Rz"] * (e - p["Vz"]) / (p["Rs"] + p["Rz"]))


# ============================================================================================ transistor (CE)
class Transistor:
    """n-p-n transistor in common-emitter. The base-emitter junction is a diode (Shockley), so the base current
    follows Vbb = Ib Rb + Vbe; the collector current is Ic = beta Ib (1 + Vce/VA) (Early effect) multiplied by a
    saturation factor 1 - exp(-Vce/Vsat) that pulls Ic down below the knee, where the collector junction is forward
    biased. Vce = Vcc - Ic Rc closes the loop; both loops are solved by bisection, so the numbers are deterministic."""

    PARAMS = {"Vbb": 2.0, "Rb": 100000.0, "Vcc": 6.0, "Rc": 1000.0, "beta": 200.0, "VA": 80.0,
              "Is": 1e-14, "nB": 1.0, "Vsat": 0.06}
    VARS = ["t", "I_b", "I_c", "V_be", "V_ce", "gain"]

    @staticmethod
    def base(p: dict) -> tuple[float, float]:
        """(Ib, Vbe): Vbb = Ib Rb + nB VT ln(Ib/Is + 1), by bisection on Ib."""
        lo, hi = 0.0, max(p["Vbb"], 0.0) / max(p["Rb"], 1e-9) + 1e-12
        for _ in range(200):
            mid = (lo + hi) / 2
            if mid * p["Rb"] + p["nB"] * VT * math.log(mid / p["Is"] + 1.0) > p["Vbb"]:
                hi = mid
            else:
                lo = mid
        ib = (lo + hi) / 2
        return ib, p["nB"] * VT * math.log(ib / p["Is"] + 1.0)

    @staticmethod
    def _ic_at(vce: float, ib: float, p: dict) -> float:
        return p["beta"] * ib * (1 + max(vce, 0.0) / p["VA"]) * (1 - math.exp(-max(vce, 0.0) / p["Vsat"]))

    @staticmethod
    def collector(p: dict) -> tuple[float, float]:
        """(Ic, Vce): Vce = Vcc - Ic Rc with Ic(Vce) above, by bisection on Vce (Ic rises with Vce)."""
        ib, _ = Transistor.base(p)
        lo, hi = 0.0, max(p["Vcc"], 0.0)
        for _ in range(200):
            mid = (lo + hi) / 2
            if mid + Transistor._ic_at(mid, ib, p) * p["Rc"] > p["Vcc"]:
                hi = mid
            else:
                lo = mid
        vce = (lo + hi) / 2
        return Transistor._ic_at(vce, ib, p), vce

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ib, vbe = Transistor.base(p)
        ic, vce = Transistor.collector(p)
        return {"t": s.get("t", 0.0), "I_b": ib, "I_c": ic, "V_be": vbe, "V_ce": vce,
                "gain": ic / ib if ib > 0 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        ib, vbe = Transistor.base(p)
        ic, vce = Transistor.collector(p)
        return {"I_b": ib, "I_c": ic, "V_be": vbe, "V_ce": vce}


def _trans_ic(p: dict) -> float:
    """Textbook, active region (Vce well above the knee, so the saturation factor is 1):
    Ic = beta Ib (1 + Vce/VA) with Vce = Vcc - Ic Rc gives Ic = beta Ib (1 + Vcc/VA) / (1 + beta Ib Rc / VA)."""
    ib, _ = Transistor.base(p)
    g = p["beta"] * ib
    return g * (1 + p["Vcc"] / p["VA"]) / (1 + g * p["Rc"] / p["VA"])


# ============================================================================================ light-dependent resistor
class Ldr:
    """A light-dependent resistor lit by a small lamp at a distance d. A point source of luminous intensity `Iv`
    (candela) gives an illuminance E = Iv/d^2 (inverse-square law) plus the room's own `Eamb`; the cell's resistance
    follows the manufacturer's straight line on log-log paper, R = A E^(-gamma)."""

    PARAMS = {"d": 0.2, "Iv": 2.0, "Eamb": 5.0, "A": 60000.0, "gamma": 0.8, "Eb": 5.0, "Rs": 1000.0}
    VARS = ["t", "E_lux", "R_ldr", "I_c", "V_ldr"]

    @staticmethod
    def lux(p: dict) -> float:
        return p["Iv"] / (p["d"] * p["d"]) + p["Eamb"]

    @staticmethod
    def res(p: dict) -> float:
        return p["A"] * math.pow(Ldr.lux(p), -p["gamma"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        r = Ldr.res(p)
        i = p["Eb"] / (p["Rs"] + r)
        return {"t": s.get("t", 0.0), "E_lux": Ldr.lux(p), "R_ldr": r, "I_c": i, "V_ldr": i * r}

    @staticmethod
    def measure(p, cfg=None):
        return {"R_ldr": Ldr.res(p), "E_lux": Ldr.lux(p)}


def _ldr_R(p: dict) -> float:
    return p["A"] * math.pow(p["Iv"] / (p["d"] * p["d"]) + p["Eamb"], -p["gamma"])


# ============================================================================================ single-slit diffraction
class Diffraction:
    """Fraunhofer diffraction at a single slit of width `a`, light of wavelength `lam`, screen at distance `D`.
    Intensity I(theta) = I0 sinc^2(pi a sin(theta) / lam); the minima are at a sin(theta) = m lam. The pattern is
    traced on the screen in real distance x = D tan(theta), so the small-angle formula x = m lam D / a is only
    approached, never assumed."""

    PARAMS = {"a": 0.0001, "lam": 6.5e-7, "D": 1.0, "x": 0.0, "I0": 1.0}
    VARS = ["t", "inten", "theta", "x_first_min", "width"]

    @staticmethod
    def inten_at(x: float, p: dict) -> float:
        th = math.atan2(x, p["D"])
        b = PI * p["a"] * math.sin(th) / p["lam"]
        return p["I0"] if abs(b) < 1e-12 else p["I0"] * (math.sin(b) / b) ** 2

    @staticmethod
    def _x_of_b(b: float, p: dict) -> float:
        s = min(b * p["lam"] / (PI * p["a"]), 0.999999)
        return p["D"] * math.tan(math.asin(s))

    @staticmethod
    def min_x(p: dict, m: int = 1) -> float:
        """The m-th dark fringe on the screen: the darkest point of the traced intensity between the secondary maxima
        on either side of it, found by a ternary search on the real intensity (never read off a formula)."""
        lo = Diffraction._x_of_b((m - 0.5) * PI, p)
        hi = Diffraction._x_of_b((m + 0.5) * PI, p)
        for _ in range(200):
            a1 = lo + (hi - lo) / 3
            a2 = hi - (hi - lo) / 3
            if Diffraction.inten_at(a1, p) < Diffraction.inten_at(a2, p):
                hi = a2
            else:
                lo = a1
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        x1 = Diffraction.min_x(p, 1)
        return {"t": s.get("t", 0.0), "inten": Diffraction.inten_at(p["x"], p),
                "theta": math.atan2(p["x"], p["D"]), "x_first_min": x1, "width": 2 * x1}

    @staticmethod
    def measure(p, cfg=None):
        return {"x1": Diffraction.min_x(p, 1), "x2": Diffraction.min_x(p, 2)}


def _diff_x1(p: dict) -> float:
    """Textbook: the first minimum is at a sin(theta) = lam, so x = D tan(theta) with sin(theta) = lam/a."""
    th = math.asin(p["lam"] / p["a"])
    return p["D"] * math.tan(th)


# ============================================================================================ polarisation
class Polaroid:
    """Two polaroids. Unpolarised light of intensity I0 loses half its intensity in the polariser (which also absorbs
    a little, transmittance k1); the analyser passes a fraction cos^2(theta - theta0) of what is left (Malus's law),
    with its own transmittance k2. `theta0` is the angle at which the analyser's axis is parallel to the polariser's,
    which the analyser's own scale does not show - that is what the experiment finds."""

    PARAMS = {"I0": 1000.0, "theta": 0.0, "theta0": 0.0, "k1": 0.8, "k2": 0.8, "leak": 0.002}
    VARS = ["t", "inten", "frac"]

    @staticmethod
    def inten(p: dict, th: float) -> float:
        c = math.cos(th - p["theta0"])
        return p["I0"] * 0.5 * p["k1"] * p["k2"] * (c * c + p["leak"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        i = Polaroid.inten(p, p["theta"])
        return {"t": s.get("t", 0.0), "inten": i, "frac": i / max(p["I0"], 1e-12)}

    @staticmethod
    def measure(p, cfg=None):
        return {"inten": Polaroid.inten(p, p["theta"]), "imax": Polaroid.inten(p, p["theta0"])}


def _malus_I(p: dict) -> float:
    c = math.cos(p["theta"] - p["theta0"])
    return p["I0"] * 0.5 * p["k1"] * p["k2"] * (c * c + p["leak"])


KERNELS: dict[str, Any] = {"zener": Zener, "transistor": Transistor, "ldr": Ldr,
                           "diffraction": Diffraction, "polaroid": Polaroid}
FAMILY = {"zener": "circuit", "transistor": "circuit", "ldr": "circuit",
          "diffraction": "optics", "polaroid": "optics"}
TEXTBOOK = {
    "galv_half_ig": _galv_half_ig,
    "galv_volt_ig": _galv_volt_ig,
    "galv_amm_ig": _galv_amm_ig,
    "pot_balance": _pot_balance,
    "pot_drop": _pot_drop,
    "bridge_comb_l": _bridge_comb_l,
    "zener_Vr": _zener_vr,
    "trans_ic": _trans_ic,
    "ldr_R": _ldr_R,
    "diff_x1": _diff_x1,
    "malus_I": _malus_I,
}
