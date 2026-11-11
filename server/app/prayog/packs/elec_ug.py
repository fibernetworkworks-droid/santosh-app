"""Kernel pack `elec_ug`: the physics the undergraduate ANALOG and DIGITAL electronics set-ups need
(`syllabus/physics/ug.json`, chapters "Analog electronics and devices" and "Digital electronics, microprocessors and
microcontrollers"). Its exact JavaScript twin is `app/static/prayog/packs/elec_ug.js`; the test suite runs both on the
same inputs and demands the same numbers, so the two files carry the same formulas step for step.

Nothing here is new where the shared `circuit` kernel (modified nodal analysis on `lab.cfg.net`) already does the job,
and nothing here repeats `packs/elec11.py` - the common-emitter transistor, the Zener characteristic and the LDR live
there and are reused as they stand. What the solver cannot do, and so lives here:

  fet          a JFET / MOSFET channel (square law with the triode region and channel-length modulation)
  opamp        an operational amplifier with a FINITE open-loop gain and output saturation, on its resistor network
  zenreg       a Zener shunt regulator WITH A LOAD (line and load regulation)
  solar        a solar cell as the single-diode model (series and shunt resistance), so the fill factor is real
  rectifier    a transformer secondary, 1-4 diodes and a capacitor filter, integrated in the time domain
  logic_gate   a logic gate built out of 2-input NAND gates, node by node
  logic_arith  adders and subtractors built out of those gates

Every kernel is deterministic: fixed-count bisection, fixed time steps, no randomness and no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
VT = 0.025852                 # thermal voltage at 300 K, the same constant kernels.py and packs/elec11.py use
NS = 2000                     # samples in one mains cycle (the rectifier's integration step and its averaging grid)
CYC = 40                      # cycles run before the rectifier's output is averaged: the filter has settled by then


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _bit(v: Any) -> int:
    return 1 if float(v) >= 0.5 else 0


# ==================================================================================================== FET (JFET / MOSFET)
class Fet:
    """A field-effect transistor's channel, the way every textbook writes it.

    `kind` 0 = n-channel JFET (depletion): the Shockley square law I_D = I_DSS (1 - V_GS/V_P)^2 in saturation, with
    V_P the (negative) pinch-off voltage. `kind` 1 = n-channel enhancement MOSFET: I_D = (k/2)(V_GS - V_th)^2.
    Below the knee (V_DS < V_GS - V_P, or V_DS < V_GS - V_th) the channel is a resistor and the current follows the
    triode expression, which meets the saturation value exactly at the knee. Channel-length modulation multiplies
    both by (1 + lambda V_DS), so the saturation curves tilt the way real ones do.

    The drain sits on V_DD through R_D, so V_DS = V_DD - I_D R_D closes the loop; it is solved by bisection on V_DS
    (the drain current only rises with V_DS, so the loop equation is monotonic)."""

    PARAMS = {"kind": 0.0, "Idss": 0.008, "Vp": -3.0, "kn": 0.02, "Vth": 2.1, "lam": 0.02,
              "Vgs": 0.0, "Vdd": 12.0, "Rd": 1000.0}
    VARS = ["t", "I_d", "V_ds", "V_gs", "V_rd", "gm"]

    @staticmethod
    def id_at(vds: float, p: dict) -> float:
        """Drain current for a given drain-source voltage, in amperes."""
        vds = max(vds, 0.0)
        if p["kind"] < 0.5:
            vov = p["Vgs"] - p["Vp"]
            if vov <= 0.0:
                return 0.0
            a = p["Idss"] / (p["Vp"] * p["Vp"])
            core = a * (2 * vov * vds - vds * vds) if vds < vov else a * vov * vov
        else:
            vov = p["Vgs"] - p["Vth"]
            if vov <= 0.0:
                return 0.0
            core = p["kn"] * (vov * vds - 0.5 * vds * vds) if vds < vov else 0.5 * p["kn"] * vov * vov
        return core * (1 + p["lam"] * vds)

    @staticmethod
    def solve(p: dict) -> tuple[float, float]:
        """(I_D, V_DS) on the load line V_DS = V_DD - I_D R_D."""
        lo, hi = 0.0, max(p["Vdd"], 0.0)
        for _ in range(80):
            mid = (lo + hi) / 2
            if mid + Fet.id_at(mid, p) * p["Rd"] > p["Vdd"]:
                hi = mid
            else:
                lo = mid
        vds = (lo + hi) / 2
        return Fet.id_at(vds, p), vds

    @staticmethod
    def gm(p: dict) -> float:
        """Transconductance at the operating point: the measured slope dI_D/dV_GS over +- 1 mV on the gate."""
        d = 0.001
        hi = Fet.solve(dict(p, Vgs=p["Vgs"] + d))[0]
        lo = Fet.solve(dict(p, Vgs=p["Vgs"] - d))[0]
        return (hi - lo) / (2 * d)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        i, v = Fet.solve(p)
        return {"t": s.get("t", 0.0), "I_d": i, "V_ds": v, "V_gs": p["Vgs"], "V_rd": i * p["Rd"], "gm": Fet.gm(p)}

    @staticmethod
    def measure(p, cfg=None):
        i, v = Fet.solve(p)
        return {"I_d": i, "V_ds": v, "gm": Fet.gm(p)}


def _fet_id(p: dict) -> float:
    """Textbook, saturation: I_D = A (1 + lambda V_DS) with V_DS = V_DD - I_D R_D, solved in closed form,
    A = I_DSS (1 - V_GS/V_P)^2 for a JFET or (k/2)(V_GS - V_th)^2 for a MOSFET."""
    if p["kind"] < 0.5:
        vov = p["Vgs"] - p["Vp"]
        a = 0.0 if vov <= 0 else p["Idss"] * vov * vov / (p["Vp"] * p["Vp"])
    else:
        vov = p["Vgs"] - p["Vth"]
        a = 0.0 if vov <= 0 else 0.5 * p["kn"] * vov * vov
    return a * (1 + p["lam"] * p["Vdd"]) / (1 + a * p["lam"] * p["Rd"])


# ==================================================================================================== operational amplifier
class Opamp:
    """An operational amplifier on its resistor network, with a finite open-loop gain A0 and output saturation.

    The inverting node takes up to three inputs V1, V2, V3 through R1, R2, R3 and the feedback R_f from the output;
    the non-inverting node takes V4 through Ra with Rb to ground, so V_p = V4 Rb/(Ra + Rb). One Kirchhoff equation at
    the inverting node with V_o = A0 (V_p - V_n) gives the output in closed form:

        V_o = (V_p G - S) / (1/R_f + G/A0),   G = 1/R1 + 1/R2 + 1/R3 + 1/R_f,  S = V1/R1 + V2/R2 + V3/R3

    which is the ideal result shifted by the finite-gain error G/A0, exactly as the textbook derivation says. Past
    the rails the output sticks at +- V_sat and the inverting node is no longer a virtual earth, so V_n is then read
    back from the same Kirchhoff equation. `open` >= 0.5 removes the feedback altogether: that is the comparator,
    V_o = A0 (V4 - V1) clipped at the rails. An unused resistor is left at 1 G-ohm, which is what "not connected"
    means on a real board."""

    PARAMS = {"A0": 200000.0, "Vsat": 13.5, "R1": 1000.0, "R2": 1e9, "R3": 1e9, "Rf": 10000.0,
              "Ra": 0.0, "Rb": 1e9, "V1": 0.0, "V2": 0.0, "V3": 0.0, "V4": 0.0, "open": 0.0}
    VARS = ["t", "V_o", "V_n", "V_p", "V_1", "V_2", "V_3", "V_4", "sat"]

    @staticmethod
    def solve(p: dict) -> tuple[float, float, float]:
        """(V_o, V_n, V_p), in volts."""
        vp = p["V4"] * p["Rb"] / max(p["Ra"] + p["Rb"], 1e-12)
        if p["open"] >= 0.5:
            raw = p["A0"] * (vp - p["V1"])
            return _clamp(raw, -p["Vsat"], p["Vsat"]), p["V1"], vp
        gi = 1.0 / p["R1"] + 1.0 / p["R2"] + 1.0 / p["R3"]
        g = gi + 1.0 / p["Rf"]
        s = p["V1"] / p["R1"] + p["V2"] / p["R2"] + p["V3"] / p["R3"]
        vo = (vp * g - s) / (1.0 / p["Rf"] + g / p["A0"])
        if abs(vo) > p["Vsat"]:
            vo = p["Vsat"] if vo > 0 else -p["Vsat"]
            return vo, (s + vo / p["Rf"]) / g, vp
        return vo, vp - vo / p["A0"], vp

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        vo, vn, vp = Opamp.solve(p)
        return {"t": s.get("t", 0.0), "V_o": vo, "V_n": vn, "V_p": vp, "V_1": p["V1"], "V_2": p["V2"],
                "V_3": p["V3"], "V_4": p["V4"], "sat": 1.0 if abs(vo) >= p["Vsat"] - 1e-9 else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        vo, vn, vp = Opamp.solve(p)
        return {"V_o": vo, "V_n": vn, "V_p": vp}


def _opamp_vo(p: dict) -> float:
    """Textbook, the ideal op-amp (V_n = V_p, no input current), clipped at the rails."""
    vp = p["V4"] * p["Rb"] / max(p["Ra"] + p["Rb"], 1e-12)
    if p["open"] >= 0.5:
        return _clamp(p["A0"] * (vp - p["V1"]), -p["Vsat"], p["Vsat"])
    gi = 1.0 / p["R1"] + 1.0 / p["R2"] + 1.0 / p["R3"]
    s = p["V1"] / p["R1"] + p["V2"] / p["R2"] + p["V3"] / p["R3"]
    return _clamp(vp * (1 + p["Rf"] * gi) - p["Rf"] * s, -p["Vsat"], p["Vsat"])


# ==================================================================================================== Zener shunt regulator
class Zenreg:
    """A Zener shunt regulator: V_in through R_s to the Zener (cathode to the positive rail, so reverse biased) with
    the load R_L across it. The Zener's reverse branch is the textbook piecewise-linear law I = (V - V_z)/R_z with the
    corner rounded over `knee` volts, the same model `packs/elec11.py` uses, plus the leakage I_s below breakdown.

    One node equation closes it:  (V_o - V_in)/R_s + I_z(V_o) + V_o/R_L = 0, monotonic in V_o, so bisection."""

    PARAMS = {"Vin": 12.0, "Rs": 470.0, "Vz": 5.1, "Rz": 7.0, "RL": 1000.0, "Is": 5e-9, "knee": 0.02}
    VARS = ["t", "V_o", "I_z", "I_s", "I_L", "V_Rs", "P_z"]

    @staticmethod
    def iz(v: float, p: dict) -> float:
        u = v - p["Vz"]
        return (u + math.sqrt(u * u + p["knee"] * p["knee"])) / (2 * p["Rz"]) + p["Is"]

    @staticmethod
    def solve(p: dict) -> float:
        lo, hi = 0.0, max(p["Vin"], 0.0)
        for _ in range(100):
            mid = (lo + hi) / 2
            if (mid - p["Vin"]) / p["Rs"] + Zenreg.iz(mid, p) + mid / p["RL"] > 0:
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
        vo = Zenreg.solve(p)
        iz, il = Zenreg.iz(vo, p), vo / p["RL"]
        return {"t": s.get("t", 0.0), "V_o": vo, "I_z": iz, "I_L": il, "I_s": iz + il,
                "V_Rs": p["Vin"] - vo, "P_z": vo * iz}

    @staticmethod
    def measure(p, cfg=None):
        vo = Zenreg.solve(p)
        return {"V_o": vo, "I_z": Zenreg.iz(vo, p), "I_L": vo / p["RL"]}


def _zenreg_vo(p: dict) -> float:
    """Textbook, past breakdown: the Zener is V_z in series with R_z, so the node gives
    V_o = (V_in/R_s + V_z/R_z) / (1/R_s + 1/R_z + 1/R_L)."""
    return (p["Vin"] / p["Rs"] + p["Vz"] / p["Rz"]) / (1.0 / p["Rs"] + 1.0 / p["Rz"] + 1.0 / p["RL"])


# ==================================================================================================== solar cell
class Solar:
    """A solar cell as the single-diode model every photovoltaics text starts from:

        I = I_ph - I_s (e^((V + I R_s)/(n_s n V_T)) - 1) - (V + I R_s)/R_sh

    `Iph` is the light-generated current (it rises with the irradiance on the cell), `Rs` the series resistance of
    the fingers and contacts and `Rsh` the shunt resistance of the edges. The equation is implicit in I, so it is
    solved by bisection; the maximum-power point is then found by a ternary search on the real I-V curve, never from
    a rule of thumb, and the fill factor is P_m/(I_sc V_oc)."""

    PARAMS = {"Iph": 0.12, "Is": 1e-9, "nD": 1.3, "ns": 1.0, "Rser": 0.3, "Rsh": 10000.0, "RL": 10.0}
    VARS = ["t", "V_o", "I_o", "P_o", "R_L"]

    @staticmethod
    def _diode(vj: float, p: dict) -> float:
        return p["Is"] * (math.exp(min(vj / (p["ns"] * p["nD"] * VT), 80.0)) - 1.0)

    @staticmethod
    def i_at(v: float, p: dict) -> float:
        """Cell current at a terminal voltage v (amperes; negative past the open-circuit voltage)."""
        lo, hi = -(p["Iph"] + 1.0), p["Iph"] + 1.0
        for _ in range(70):
            mid = (lo + hi) / 2
            vj = v + mid * p["Rser"]
            if mid + Solar._diode(vj, p) + vj / p["Rsh"] - p["Iph"] > 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    @staticmethod
    def on_load(p: dict) -> float:
        """Current with the load R_L across the cell (V = I R_L)."""
        lo, hi = 0.0, p["Iph"] + 1.0
        for _ in range(70):
            mid = (lo + hi) / 2
            vj = mid * (p["RL"] + p["Rser"])
            if mid + Solar._diode(vj, p) + vj / p["Rsh"] - p["Iph"] > 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    @staticmethod
    def voc(p: dict) -> float:
        lo, hi = 0.0, 5.0 * max(p["ns"], 1.0)
        for _ in range(100):
            mid = (lo + hi) / 2
            if Solar.i_at(mid, p) < 0:
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
        i = Solar.on_load(p)
        v = i * p["RL"]
        return {"t": s.get("t", 0.0), "V_o": v, "I_o": i, "P_o": v * i, "R_L": p["RL"]}

    @staticmethod
    def measure(p, cfg=None):
        isc = Solar.i_at(0.0, p)
        voc = Solar.voc(p)
        lo, hi = 0.0, voc
        for _ in range(100):
            a1 = lo + (hi - lo) / 3
            a2 = hi - (hi - lo) / 3
            if a1 * Solar.i_at(a1, p) < a2 * Solar.i_at(a2, p):
                lo = a1
            else:
                hi = a2
        vm = (lo + hi) / 2
        im = Solar.i_at(vm, p)
        pm = vm * im
        return {"I_sc": isc, "V_oc": voc, "V_m": vm, "I_m": im, "P_m": pm,
                "FF": pm / (isc * voc) if isc * voc > 0 else 0.0}


def _solar_voc(p: dict) -> float:
    """Textbook: with no shunt leakage the whole photocurrent goes into the diode at open circuit, so
    V_oc = n_s n V_T ln(I_ph/I_s + 1)."""
    return p["ns"] * p["nD"] * VT * math.log(p["Iph"] / p["Is"] + 1.0)


# ==================================================================================================== rectifier + filter
class Rectifier:
    """A transformer secondary of peak voltage V_p at frequency f, a rectifier (`kind` 1 = half-wave, 2 = full-wave
    with a centre-tapped transformer, 3 = bridge), an optional capacitor filter C and the load R_L.

    Each conducting diode costs `Vd` volts and the source plus diode resistance is R_s, so the voltage offered to the
    load is v_r(t) = V_p sin(2 pi f t) - V_d for half-wave, |V_p sin| - V_d for the centre tap and |V_p sin| - 2 V_d
    for the bridge (two diodes conduct at a time). With no capacitor the load simply divides that whenever it is
    positive. With a capacitor the output is integrated in the time domain,

        C dV_o/dt = max(0, (v_r - V_o)/R_s) - V_o/R_L

    at a fixed step of one cycle divided by 2000, which is how the ripple, the DC level and the regulation come out
    of the simulation instead of out of a formula. `measure` runs 40 cycles so the filter has settled, then averages
    the next cycle on that same grid: V_dc is the mean, V_rms the root mean square, V_ac the RMS of the ripple alone
    (what a true-RMS meter on AC shows) and the ripple factor is V_ac/V_dc."""

    PARAMS = {"Vp": 12.0, "f": 50.0, "kind": 2.0, "C": 0.0, "RL": 1000.0, "Vd": 0.7, "Rs": 1.0}
    VARS = ["t", "V_in", "V_rect", "V_o", "I_L"]

    @staticmethod
    def _drops(p: dict) -> float:
        return 2.0 if p["kind"] >= 2.5 else 1.0

    @staticmethod
    def vrect(t: float, p: dict) -> float:
        v = p["Vp"] * math.sin(2 * PI * p["f"] * t)
        if p["kind"] < 1.5:
            return v - p["Vd"]
        return abs(v) - Rectifier._drops(p) * p["Vd"]

    @staticmethod
    def _h(p: dict) -> float:
        return 1.0 / (max(p["f"], 1e-6) * NS)

    @staticmethod
    def out(t: float, vo: float, p: dict) -> float:
        """The load voltage: the capacitor's own voltage when there is a filter, otherwise the divided v_r."""
        if p["C"] > 0:
            return vo
        vr = Rectifier.vrect(t, p)
        return vr * p["RL"] / (p["RL"] + p["Rs"]) if vr > 0 else 0.0

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "vo": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        h = Rectifier._h(p)
        n = max(1, int(math.ceil(dt / h - 1e-9)))
        hh = dt / n
        for _ in range(n):
            if p["C"] > 0:
                vr = Rectifier.vrect(s["t"], p)
                idio = max(0.0, (vr - s["vo"]) / p["Rs"])
                s["vo"] = max(0.0, s["vo"] + hh * (idio - s["vo"] / p["RL"]) / p["C"])
            s["t"] += hh

    @staticmethod
    def view(s, p, cfg=None):
        vo = Rectifier.out(s["t"], s.get("vo", 0.0), p)
        return {"t": s["t"], "V_in": p["Vp"] * math.sin(2 * PI * p["f"] * s["t"]),
                "V_rect": Rectifier.vrect(s["t"], p), "V_o": vo, "I_L": vo / p["RL"]}

    @staticmethod
    def measure(p, cfg=None):
        h = Rectifier._h(p)
        s = Rectifier.init(p)
        for _ in range(CYC * NS):
            Rectifier.step(s, p, h)
        su = sq = 0.0
        mx = -1e30
        mn = 1e30
        for _ in range(NS):
            v = Rectifier.out(s["t"], s["vo"], p)
            su += v
            sq += v * v
            mx = max(mx, v)
            mn = min(mn, v)
            Rectifier.step(s, p, h)
        vdc = su / NS
        vrms = math.sqrt(sq / NS)
        vac = math.sqrt(max(0.0, vrms * vrms - vdc * vdc))
        return {"V_dc": vdc, "V_rms": vrms, "V_ac": vac, "V_pp": mx - mn,
                "ripple": vac / vdc if vdc > 0 else 0.0}


def _rect_vdc(p: dict) -> float:
    """Textbook, ideal diodes and no filter: V_dc = V_p/pi for half-wave, 2 V_p/pi for full-wave and the bridge."""
    return p["Vp"] / PI if p["kind"] < 1.5 else 2 * p["Vp"] / PI


# ==================================================================================================== digital logic
def _nand(a: int, b: int) -> int:
    return 1 - a * b


def _not(a: int) -> int:
    return _nand(a, a)


def _and(a: int, b: int) -> int:
    n = _nand(a, b)
    return _nand(n, n)


def _or(a: int, b: int) -> int:
    return _nand(_not(a), _not(b))


def _xor(a: int, b: int) -> int:
    """The four-NAND exclusive-OR: n1 = A.B, n2 = A.n1, n3 = B.n1, Y = n2.n3 (every bar a NAND)."""
    n1 = _nand(a, b)
    return _nand(_nand(a, n1), _nand(b, n1))


class LogicGate:
    """One logic gate, built out of 2-input NAND gates only, evaluated node by node (never from a truth table).
    `fn` picks the gate: 1 NOT, 2 AND, 3 OR, 4 XOR, 5 NAND, 6 NOR, 7 XNOR. The internal nodes n1..n4 are the real
    NAND outputs on the breadboard, which is what the student probes."""

    PARAMS = {"A": 0.0, "B": 0.0, "fn": 4.0, "Vcc": 5.0}
    VARS = ["t", "Y", "n1", "n2", "n3", "n4", "A_in", "B_in"]

    @staticmethod
    def nodes(p: dict) -> dict:
        a, b, fn = _bit(p["A"]), _bit(p["B"]), int(round(p["fn"]))
        n1 = n2 = n3 = n4 = 0
        if fn == 1:
            n1 = _nand(a, a)
            y = n1
        elif fn == 2:
            n1 = _nand(a, b)
            n2 = _nand(n1, n1)
            y = n2
        elif fn == 3:
            n1 = _nand(a, a)
            n2 = _nand(b, b)
            n3 = _nand(n1, n2)
            y = n3
        elif fn == 5:
            n1 = _nand(a, b)
            y = n1
        elif fn == 6:
            n1 = _nand(a, a)
            n2 = _nand(b, b)
            n3 = _nand(n1, n2)
            n4 = _nand(n3, n3)
            y = n4
        elif fn == 7:
            n1 = _nand(a, b)
            n2 = _nand(a, n1)
            n3 = _nand(b, n1)
            n4 = _nand(n2, n3)
            y = _nand(n4, n4)
        else:
            n1 = _nand(a, b)
            n2 = _nand(a, n1)
            n3 = _nand(b, n1)
            n4 = _nand(n2, n3)
            y = n4
        return {"Y": float(y), "n1": float(n1), "n2": float(n2), "n3": float(n3), "n4": float(n4),
                "A_in": float(a), "B_in": float(b)}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        out = LogicGate.nodes(p)
        out["t"] = s.get("t", 0.0)
        return out

    @staticmethod
    def measure(p, cfg=None):
        n = LogicGate.nodes(p)
        return {"Y": n["Y"], "n1": n["n1"], "n4": n["n4"]}


def _logic_y(p: dict) -> float:
    """Textbook: the same gate written straight from its Boolean definition, with no NAND network at all."""
    a, b, fn = _bit(p["A"]), _bit(p["B"]), int(round(p["fn"]))
    if fn == 1:
        return float(1 - a)
    if fn == 2:
        return float(a * b)
    if fn == 3:
        return float(1 if (a or b) else 0)
    if fn == 5:
        return float(1 - a * b)
    if fn == 6:
        return float(0 if (a or b) else 1)
    if fn == 7:
        return float(1 if a == b else 0)
    return float(1 if a != b else 0)


class LogicArith:
    """Adders and subtractors, each built from the NAND gates above. `fn` picks the circuit:
    1 half adder, 2 full adder, 3 half subtractor, 4 full subtractor, 5 four-bit ripple-carry adder (A and B are
    then whole numbers 0-15 in `An` and `Bn`). `value` is the arithmetic the circuit claims: S + 2 C for an adder,
    D - 2 B_out for a subtractor, SUM + 16 C_out for the four-bit adder."""

    PARAMS = {"A": 0.0, "B": 0.0, "Cin": 0.0, "fn": 1.0, "An": 0.0, "Bn": 0.0}
    VARS = ["t", "S", "Cout", "D", "Bout", "SUM", "value", "A_in", "B_in", "Cin_in"]

    @staticmethod
    def nodes(p: dict) -> dict:
        a, b, c = _bit(p["A"]), _bit(p["B"]), _bit(p["Cin"])
        fn = int(round(p["fn"]))
        s = co = d = bo = 0
        sm = 0
        if fn == 1:
            s, co = _xor(a, b), _and(a, b)
            value = s + 2 * co
        elif fn == 2:
            s1, c1 = _xor(a, b), _and(a, b)
            s, co = _xor(s1, c), _or(c1, _and(s1, c))
            value = s + 2 * co
        elif fn == 3:
            d, bo = _xor(a, b), _and(_not(a), b)
            value = d - 2 * bo
        elif fn == 4:
            x = _xor(a, b)
            d = _xor(x, c)
            bo = _or(_and(_not(x), c), _and(_not(a), b))
            value = d - 2 * bo
        else:
            an, bn, carry = int(round(p["An"])), int(round(p["Bn"])), c
            for i in range(4):
                ai, bi = (an >> i) & 1, (bn >> i) & 1
                s1, c1 = _xor(ai, bi), _and(ai, bi)
                si = _xor(s1, carry)
                carry = _or(c1, _and(s1, carry))
                sm += si << i
            co, s = carry, sm & 1
            value = sm + 16 * co
        return {"S": float(s), "Cout": float(co), "D": float(d), "Bout": float(bo), "SUM": float(sm),
                "value": float(value), "A_in": float(a), "B_in": float(b), "Cin_in": float(c)}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        out = LogicArith.nodes(p)
        out["t"] = s.get("t", 0.0)
        return out

    @staticmethod
    def measure(p, cfg=None):
        return dict(LogicArith.nodes(p))


def _arith_value(p: dict) -> float:
    """Textbook: plain arithmetic on the input bits, with no gates in sight."""
    a, b, c = _bit(p["A"]), _bit(p["B"]), _bit(p["Cin"])
    fn = int(round(p["fn"]))
    if fn in (1, 2):
        return float(a + b + (c if fn == 2 else 0))
    if fn in (3, 4):
        return float(a - b - (c if fn == 4 else 0))
    return float(int(round(p["An"])) + int(round(p["Bn"])) + c)


# ==================================================================================================== learner's tables
def _rows(rs: list[dict], keys: list[str]) -> list[list[float]]:
    out = []
    for r in rs:
        vals = []
        ok = True
        for k in keys:
            v = r.get(k)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                ok = False
                break
            vals.append(float(v))
        if ok:
            out.append(vals)
    return out


def _slope(pts: list[list[float]]) -> float:
    """Least-squares slope of y on x."""
    n = len(pts)
    if n < 2:
        return 0.0
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    den = n * sxx - sx * sx
    return 0.0 if den == 0 else (n * sxy - sx * sy) / den


def _calc_fet_vp(rs: list[dict], p: dict | None = None) -> float:
    """Pinch-off (or threshold) voltage from the transfer characteristic: sqrt(I_D) is a straight line in V_GS for
    the square law, so the line through the readings cuts the V_GS axis at V_P."""
    pts = [[x[0], math.sqrt(max(x[1], 0.0))] for x in _rows(rs, ["Vgs", "Id"])]
    m = _slope(pts)
    if m == 0 or len(pts) < 2:
        return 0.0
    n = len(pts)
    mx = sum(q[0] for q in pts) / n
    my = sum(q[1] for q in pts) / n
    return mx - my / m


def _calc_opamp_gain(rs: list[dict], p: dict | None = None) -> float:
    return _slope(_rows(rs, ["Vin", "Vout"]))


def _calc_line_reg(rs: list[dict], p: dict | None = None) -> float:
    """Line regulation in millivolts of output per volt of input."""
    return 1000.0 * _slope(_rows(rs, ["Vin", "Vo"]))


def _calc_solar_ff(rs: list[dict], p: dict | None = None) -> float:
    """Fill factor from the student's own I-V table: the best power in it over I_sc V_oc."""
    pts = _rows(rs, ["V", "I"])
    if not pts:
        return 0.0
    isc = voc = 0.0
    for v, i in pts:
        if i > isc:
            isc = i
        if v > voc:
            voc = v
    pm = 0.0
    for v, i in pts:
        pm = max(pm, v * i)
    return pm / (isc * voc) if isc * voc > 0 else 0.0


def _calc_ripple(rs: list[dict], p: dict | None = None) -> float:
    pts = _rows(rs, ["Vdc", "Vac"])
    vals = [q[1] / q[0] for q in pts if q[0] != 0]
    return sum(vals) / len(vals) if vals else 0.0


def _calc_truth_sig(rs: list[dict], p: dict | None = None) -> float:
    """The output column of a truth table read as a binary number, the top row the least significant bit: one number
    that says whether the whole table is right."""
    tot = 0.0
    for i, q in enumerate(_rows(rs, ["Y"])):
        tot += (1 if q[0] >= 0.5 else 0) * (2 ** i)
    return tot


KERNELS: dict[str, Any] = {"fet": Fet, "opamp": Opamp, "zenreg": Zenreg, "solar": Solar,
                           "rectifier": Rectifier, "logic_gate": LogicGate, "logic_arith": LogicArith}
FAMILY = {"fet": "circuit", "opamp": "circuit", "zenreg": "circuit", "solar": "circuit",
          "rectifier": "circuit", "logic_gate": "circuit", "logic_arith": "circuit"}
TEXTBOOK = {
    "fet_id": _fet_id,
    "opamp_vo": _opamp_vo,
    "zenreg_vo": _zenreg_vo,
    "solar_voc": _solar_voc,
    "rect_vdc": _rect_vdc,
    "logic_y": _logic_y,
    "arith_value": _arith_value,
}
CALCS = {
    "fet_vp": {"label": "V_P", "unit": "V", "needs": ["Vgs", "Id"], "fn": _calc_fet_vp},
    "opamp_gain": {"label": "gain", "unit": "", "needs": ["Vin", "Vout"], "fn": _calc_opamp_gain},
    "zen_line_reg": {"label": "line regulation", "unit": "mV/V", "needs": ["Vin", "Vo"], "fn": _calc_line_reg},
    "solar_ff": {"label": "fill factor", "unit": "", "needs": ["V", "I"], "fn": _calc_solar_ff},
    "rect_ripple": {"label": "ripple factor", "unit": "", "needs": ["Vdc", "Vac"], "fn": _calc_ripple},
    "truth_sig": {"label": "truth-table signature", "unit": "", "needs": ["Y"], "fn": _calc_truth_sig},
}
