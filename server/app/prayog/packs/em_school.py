"""Prayogshala kernel pack: school (Class 6-10) electricity, magnetism and static electricity.

New physics only - the general `circuit` kernel in kernels.py already serves every set-up that is just a netlist
(bulb circuits, cells in series, resistors in series / parallel, a tester), so those labs add a TEXTBOOK formula
here and no kernel at all. The kernels below are the ones the shared file has no physics for:

    coilfield    the magnetic field of a current (straight wire / circular coil / solenoid) by Biot-Savart,
                 summed in code, and the compass deflection tan(theta) = B / B_H it causes
    barmagnet    a bar magnet as two poles: the equatorial neutral point (found by bisection), the period of a
                 suspended magnet (found by integrating its equation of motion) and the force between two magnets
    estatic      two charged balls (or the two foil strips of an electroscope) hanging apart: the equilibrium
                 separation, found by bisection on the exact torque balance
    jouleheat    the heating effect of a current: a nichrome coil warming a known mass of water
    wirecircuit  a real wire (rho, length, diameter) measured with an ammeter and a voltmeter in a true circuit

Every TEXTBOOK formula here is the closed-form expression a textbook prints; the kernel reaches the same number by
a different road (a sum, a bisection, an integration), so `lsl.run_check` compares two independent calculations.
Deterministic throughout: no randomness, no wall clock. The exact JavaScript twin is
`app/static/prayog/packs/em_school.js` - the test suite runs both and demands the same numbers.
"""
from __future__ import annotations

import math
from typing import Any

from ..kernels import Circuit

PI = math.pi
MU0 = 4e-7 * PI
EPS0 = 8.8541878128e-12                      # CODATA 2018
KE = 1.0 / (4 * PI * EPS0)
SEGS = 2000                                  # Biot-Savart elements along a wire / around a loop
HSTEP = 0.0005                               # integration sub-step (s) for the suspended magnet


# --------------------------------------------------------------------------------------- shared numerics (twinned)
def _rk4(f, y, h):
    k1 = f(y)
    k2 = f([y[i] + h / 2 * k1[i] for i in range(len(y))])
    k3 = f([y[i] + h / 2 * k2[i] for i in range(len(y))])
    k4 = f([y[i] + h * k3[i] for i in range(len(y))])
    return [y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(len(y))]


def _period(f, y0, h, tmax):
    """Time between two successive downward zero crossings of y[0]."""
    y, t, cross = list(y0), 0.0, []
    while t < tmax and len(cross) < 2:
        y2 = _rk4(f, y, h)
        if y[0] > 0 >= y2[0]:
            cross.append(t + h * y[0] / (y[0] - y2[0]))
        y, t = y2, t + h
    return cross[1] - cross[0] if len(cross) == 2 else 0.0


def _bisect(f, lo, hi, n=80):
    flo = f(lo)
    for _ in range(n):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def _area(dia: float) -> float:
    return PI * dia * dia / 4


# --------------------------------------------------------------------------------------- the field of a current
class CoilField:
    """The magnetic field of a steady current and the compass needle it turns.

    kind 0 = a straight wire of length `wireL`, the point `d` metres away from its middle;
    kind 1 = a circular coil of `N` turns, radius `a`, the point `d` metres from the centre along the axis;
    kind 2 = a solenoid, length `Lsol`, `nsol` turns per metre, radius `a`, core `mur`, at its centre.
    B is SUMMED from Biot-Savart elements (straight wire, one loop) or over the turns (solenoid); the textbook
    closed form is in TEXTBOOK. The compass sits with its needle along the magnetic meridian, so it turns through
    tan(theta) = B / B_H."""

    PARAMS = {"kind": 0.0, "Eb": 3.0, "Rs": 6.0, "d": 0.03, "N": 1.0, "a": 0.05, "Lsol": 0.30,
              "nsol": 1000.0, "mur": 1.0, "BH": 4.0e-5, "rev": 1.0, "wireL": 1.0, "key": 1.0}
    VARS = ["t", "I", "B", "theta", "tan_theta"]

    @staticmethod
    def current(p):
        return (p["Eb"] / max(p["Rs"], 1e-9)) * (1.0 if p["key"] >= 0.5 else 0.0) * (1.0 if p["rev"] >= 0 else -1.0)

    @staticmethod
    def field(p):
        """|B| in tesla at the lab's point, by adding up the current elements (never a formula)."""
        I = abs(CoilField.current(p))
        if I == 0.0:
            return 0.0
        if p["kind"] < 0.5:                                   # straight wire along x, point at perpendicular d
            L, d, B = p["wireL"], max(p["d"], 1e-6), 0.0
            dx = L / SEGS
            for i in range(SEGS):
                x = -L / 2 + (i + 0.5) * dx
                r2 = x * x + d * d
                B += MU0 * I * dx * d / (4 * PI * r2 * math.sqrt(r2))
            return B
        if p["kind"] < 1.5:                                   # circular coil, on its axis at z = d
            a, z, B = p["a"], p["d"], 0.0
            dl = 2 * PI * a / SEGS
            r2 = a * a + z * z
            for _ in range(SEGS):                             # every element adds the same axial component
                B += MU0 * I * dl * a / (4 * PI * r2 * math.sqrt(r2))
            return B * p["N"]
        a, L = p["a"], p["Lsol"]                              # solenoid: add the turns, each a loop on the axis
        turns = max(1, int(round(p["nsol"] * L)))
        B = 0.0
        for i in range(turns):
            z = -L / 2 + (i + 0.5) * (L / turns)
            r2 = a * a + z * z
            B += MU0 * I * a * a / (2 * r2 * math.sqrt(r2))
        return B * p["mur"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        B = CoilField.field(p)
        sgn = 1.0 if CoilField.current(p) >= 0 else -1.0
        tt = sgn * B / max(p["BH"], 1e-12)
        return {"t": s["t"], "I": CoilField.current(p), "B": sgn * B, "tan_theta": tt, "theta": math.atan(tt)}

    @staticmethod
    def measure(p, cfg=None):
        B = CoilField.field(p)
        tt = B / max(p["BH"], 1e-12)
        return {"B": B, "I": abs(CoilField.current(p)), "tan_theta": tt, "theta": math.atan(tt)}


# --------------------------------------------------------------------------------------- a bar magnet
class BarMagnet:
    """A bar magnet of moment m and length Lbar, treated as two poles of strength qm = m / Lbar at its ends.

    np_d  the EQUATORIAL neutral point: with the magnet's N pole pointing north, the distance east or west of
          its centre where its own field exactly cancels the earth's horizontal field. Found by bisection on the
          vector sum of the two poles' fields.
    T     the period of the magnet hung by a thread in the earth's field, from integrating I d2(theta)/dt2 =
          -m B_H sin(theta).
    F     the force between two such magnets, like poles facing, centre to centre d: the four pole pairs added.
    """

    PARAMS = {"m": 1.0, "Lbar": 0.05, "wbar": 0.01, "mass": 0.03, "BH": 4.0e-5, "d": 0.07,
              "theta0": 0.1745, "dnp": 0.13}
    VARS = ["t", "theta", "omega", "B_eq", "np_d", "F"]

    @staticmethod
    def _qm(p):
        return p["m"] / max(p["Lbar"], 1e-9)

    @staticmethod
    def b_eq(p, d):
        """|B| at an equatorial point d from the centre, by adding the two poles' fields as vectors."""
        q, l = BarMagnet._qm(p), p["Lbar"] / 2
        r = math.sqrt(l * l + d * d)
        bx = 0.0
        for sgn in (1.0, -1.0):                              # N pole at +l (+q), S pole at -l (-q)
            k = MU0 * (sgn * q) / (4 * PI * r * r * r)
            bx += k * (0.0 - sgn * l)
        return abs(bx)

    @staticmethod
    def inertia(p):
        return p["mass"] * (p["Lbar"] * p["Lbar"] + p["wbar"] * p["wbar"]) / 12

    @staticmethod
    def force(p, d):
        q, l = BarMagnet._qm(p), p["Lbar"] / 2
        f = 0.0
        for sa, xa in ((1.0, l), (-1.0, -l)):                # this magnet's poles
            for sb, xb in ((1.0, d - l), (-1.0, d + l)):     # the other magnet's, like poles facing
                r = xb - xa
                f += MU0 * (sa * q) * (sb * q) / (4 * PI * r * r)
        return f

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["theta0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        f = BarMagnet._ode(p)
        n = max(1, int(math.ceil(dt / HSTEP - 1e-9)))
        h = dt / n
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def _ode(p):
        w2 = p["m"] * p["BH"] / BarMagnet.inertia(p)
        return lambda y: [y[1], -w2 * math.sin(y[0])]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "theta": s["y"][0], "omega": s["y"][1], "B_eq": BarMagnet.b_eq(p, p["dnp"]),
                "np_d": 0.0, "F": BarMagnet.force(p, p["d"])}

    @staticmethod
    def measure(p, cfg=None):
        d = _bisect(lambda x: BarMagnet.b_eq(p, x) - p["BH"], 0.005, 2.0)
        T = _period(BarMagnet._ode(p), [p["theta0"], 0.0], HSTEP, 120.0)
        return {"np_d": d, "T": T, "F": BarMagnet.force(p, p["d"]), "B_eq": BarMagnet.b_eq(p, p["dnp"])}


# --------------------------------------------------------------------------------------- static electricity
class EStatic:
    """Two light balls (or the two foil strips of an electroscope) of mass `mass` on threads of length `Lth`,
    each carrying charge q. They hang apart until the thread's pull, gravity and the Coulomb repulsion balance:
        tan(theta) = k q^2 / ( (2 Lth sin theta)^2 mass g ).
    The kernel solves that exactly by bisection; the textbook small-angle result is in TEXTBOOK."""

    PARAMS = {"q": 3.4e-9, "Lth": 0.2, "mass": 1.0e-4, "g": 9.8, "charged": 1.0}
    VARS = ["t", "theta", "r", "F", "q"]

    @staticmethod
    def _theta(p):
        if p["charged"] < 0.5 or p["q"] == 0.0:
            return 0.0
        kq2 = KE * p["q"] * p["q"]
        mg = p["mass"] * p["g"]

        def f(th):
            r = 2 * p["Lth"] * math.sin(th)
            return math.tan(th) - kq2 / (r * r * mg)
        return _bisect(f, 1e-5, PI / 2 - 1e-4)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        th = EStatic._theta(p)
        r = 2 * p["Lth"] * math.sin(th)
        F = KE * p["q"] * p["q"] / (r * r) if r > 0 else 0.0
        return {"t": s["t"], "theta": th, "r": r, "F": F, "q": p["q"]}

    @staticmethod
    def measure(p, cfg=None):
        v = EStatic.view({"t": 0.0}, p)
        return {"r": v["r"], "theta": v["theta"], "F": v["F"]}


# --------------------------------------------------------------------------------------- heating effect
class JouleHeat:
    """A nichrome coil of resistivity `rho`, length `Lw` and diameter `dia` carries the current of a battery
    (emf Eb, internal resistance rint) and warms `mw` kg of water of specific heat capacity `cw` in a lagged
    calorimeter: mw cw dT/dt = I^2 R - hloss (T - Ta). With hloss = 0 this is Joule's law, H = I^2 R t."""

    PARAMS = {"Eb": 6.0, "rint": 0.5, "rho": 1.09e-6, "Lw": 0.5, "dia": 0.000559, "mw": 0.1,
              "cw": 4186.0, "hloss": 0.0, "Ta": 28.0, "tsec": 180.0, "key": 1.0}
    VARS = ["t", "T", "dT", "I", "R", "P"]

    @staticmethod
    def wire_r(p):
        return p["rho"] * p["Lw"] / _area(p["dia"])

    @staticmethod
    def current(p):
        if p["key"] < 0.5:
            return 0.0
        return p["Eb"] / (JouleHeat.wire_r(p) + p["rint"])

    @staticmethod
    def power(p):
        I = JouleHeat.current(p)
        return I * I * JouleHeat.wire_r(p)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["Ta"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n = max(1, int(math.ceil(dt / 0.01 - 1e-9)))
        h = dt / n
        cap = p["mw"] * p["cw"]
        for _ in range(n):
            s["T"] += h * (JouleHeat.power(p) - p["hloss"] * (s["T"] - p["Ta"])) / cap
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "T": s["T"], "dT": s["T"] - p["Ta"], "I": JouleHeat.current(p),
                "R": JouleHeat.wire_r(p), "P": JouleHeat.power(p)}

    @staticmethod
    def measure(p, cfg=None):
        s = JouleHeat.init(p)
        left = p["tsec"]
        while left > 1e-9:
            h = min(1.0, left)
            JouleHeat.step(s, p, h)
            left -= h
        return {"dT": s["T"] - p["Ta"], "T": s["T"], "I": JouleHeat.current(p), "R": JouleHeat.wire_r(p),
                "P": JouleHeat.power(p)}


# --------------------------------------------------------------------------------------- a real wire, measured
_WNET = {"net": {"nodes": 4, "els": [
    {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
    {"id": "K", "kind": "S", "a": 1, "b": 4, "param": "key"},
    {"id": "AM", "kind": "R", "a": 4, "b": 2, "value": 0.01},
    {"id": "RH", "kind": "R", "a": 2, "b": 3, "value": {"param": "Rh", "k": 1, "c": 0.01}},
    {"id": "RX", "kind": "R", "a": 3, "b": 0, "value": "Rxcalc"},
    {"id": "VM", "kind": "R", "a": 3, "b": 0, "value": 1000000.0}]}}


class WireCircuit:
    """A length of resistance wire in a real circuit: cell, plug key, ammeter in series, voltmeter across the
    wire, rheostat to change the current. The wire's resistance comes from the material and the gauge,
    R = rho L / A, and the reading R = V / I comes out of the circuit solver (the same MNA as `circuit`)."""

    PARAMS = {"Eb": 3.0, "rho": 1.09e-6, "Lw": 1.0, "dia": 0.000559, "Rh": 2.0, "key": 1.0}
    VARS = ["t", "I_AM", "V_VM", "R", "Rwire"]

    @staticmethod
    def wire_r(p):
        return p["rho"] * p["Lw"] / _area(p["dia"])

    @staticmethod
    def _p(p):
        q = dict(p)
        q["Rxcalc"] = WireCircuit.wire_r(p)
        return q

    @staticmethod
    def init(p, cfg=None):
        return Circuit.init(WireCircuit._p(p), _WNET)

    @staticmethod
    def step(s, p, dt, cfg=None):
        Circuit.step(s, WireCircuit._p(p), dt, _WNET)

    @staticmethod
    def view(s, p, cfg=None):
        v = Circuit.view(s, WireCircuit._p(p), _WNET)
        i = v["I_AM"]
        return {"t": v["t"], "I_AM": i, "V_VM": v["V_VM"], "R": (v["V_VM"] / i) if i != 0 else 0.0,
                "Rwire": WireCircuit.wire_r(p)}

    @staticmethod
    def measure(p, cfg=None):
        q = WireCircuit._p(p)
        s = Circuit.init(q, _WNET)
        v = Circuit.view(s, q, _WNET)
        i = v["I_AM"]
        return {"R": (v["V_VM"] / i) if i != 0 else 0.0, "I_AM": i, "V_VM": v["V_VM"]}


KERNELS: dict[str, Any] = {"coilfield": CoilField, "barmagnet": BarMagnet, "estatic": EStatic,
                           "jouleheat": JouleHeat, "wirecircuit": WireCircuit}
FAMILY = {"coilfield": "em", "barmagnet": "em", "estatic": "em", "jouleheat": "circuit", "wirecircuit": "circuit"}


def _cfield_B(p):
    """The closed form a textbook prints, for each of the three shapes."""
    I = abs(p["Eb"] / max(p["Rs"], 1e-9)) * (1.0 if p["key"] >= 0.5 else 0.0)
    if p["kind"] < 0.5:                                    # finite straight wire, perpendicular distance d
        L, d = p["wireL"], max(p["d"], 1e-6)
        return MU0 * I / (2 * PI * d) * (L / 2) / math.sqrt(d * d + L * L / 4)
    if p["kind"] < 1.5:                                    # circular coil, on the axis
        a, z = p["a"], p["d"]
        return MU0 * p["N"] * I * a * a / (2 * (a * a + z * z) ** 1.5)
    a, L = p["a"], p["Lsol"]                               # solenoid, at its centre
    return MU0 * p["mur"] * p["nsol"] * I * (L / 2) / math.sqrt(a * a + L * L / 4)


TEXTBOOK = {
    # circuits that need no new kernel: the law the MNA solver is checked against
    "ser_R": lambda p: p["R1"] + p["R2"],
    "par_R": lambda p: p["R1"] * p["R2"] / (p["R1"] + p["R2"]),
    "bulb_I": lambda p: p["Eb"] / (p["Rb"] + p["rint"]),
    "tester_I": lambda p: p["Eb"] / (p["Rb"] + p["rint"] + p["Rsam"]),
    # the new kernels
    "cfield_B": _cfield_B,
    "cfield_tan": lambda p: _cfield_B(p) / p["BH"],
    "bm_npeq": lambda p: math.sqrt((MU0 * p["m"] / (4 * PI * p["BH"])) ** (2.0 / 3.0) - (p["Lbar"] / 2) ** 2),
    "bm_T": lambda p: 2 * PI * math.sqrt(BarMagnet.inertia(p) / (p["m"] * p["BH"])),
    "bm_F": lambda p: (MU0 * BarMagnet._qm(p) ** 2 / (4 * PI)
                       * (1 / (p["d"] - p["Lbar"]) ** 2 - 2 / p["d"] ** 2 + 1 / (p["d"] + p["Lbar"]) ** 2)),
    "es_r": lambda p: (2 * KE * p["q"] * p["q"] * p["Lth"] / (p["mass"] * p["g"])) ** (1.0 / 3.0),
    "joule_dT": lambda p: JouleHeat.power(p) * p["tsec"] / (p["mw"] * p["cw"]),
    "wire_R": lambda p: p["rho"] * p["Lw"] / _area(p["dia"]),
}
