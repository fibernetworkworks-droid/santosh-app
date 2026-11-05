"""Kernel pack `em_ug`: the physics the UNDERGRADUATE electricity, magnetism, AC-circuit, network and
instrumentation set-ups need (B.Sc. physics, DU / UGC LOCF practical lists) that the shared kernels.py does not
already carry. Its exact JavaScript twin is `app/static/prayog/packs/em_ug.js`; both must give the same numbers,
and the server's tests run both and compare.

Two rules shaped this file.

1. A DC network needs NO new kernel. The shared `circuit` kernel is a general modified-nodal-analysis solver
   driven by `lab.cfg.net`, so Kirchhoff's laws, Thevenin, Norton, superposition and maximum power transfer are
   one netlist (the network-theorems trainer panel) read in different ways. Only their TEXTBOOK formulas, written
   out by hand here, and one CALCS entry are new.
2. The AC set-ups DO need new kernels: the circuit solver has no inductor and no sinusoidal source, and a lab's
   `cfg` may carry a netlist for the `circuit` kernel alone. So the AC work is done in complex arithmetic here -
   exactly the phasor algebra a textbook does - and a resonance frequency is found by SEARCHING the simulated
   response, never by printing the formula it is checked against.

Deterministic throughout: fixed iteration counts, no randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
MU0 = 4e-7 * PI


# =================================================================================== DC network trainer (circuit)
# One panel, one netlist: two bench supplies E1 and E2 feed node 2 through R1 and R2; R3 hangs from node 2 to
# earth; the load branch is R4 in series with the load RL. Every formula below is written out by hand from
# Kirchhoff's laws, so it is an independent check of the solver's answer.
def _net_rp(p: dict) -> float:
    """R1, R2 and R3 in parallel: what is seen at node 2 when both supplies are replaced by their own short."""
    return 1.0 / (1.0 / p["R1"] + 1.0 / p["R2"] + 1.0 / p["R3"])


def _net_rth(p: dict) -> float:
    """Thevenin resistance at the load terminals: R4 in series with (R1 || R2 || R3)."""
    return p["R4"] + _net_rp(p)


def _net_voc(p: dict) -> float:
    """Open-circuit (Thevenin) voltage at the load terminals. With the load open no current flows in R4, so the
    terminal voltage is the node-2 voltage: superposition of the two supplies through the parallel group."""
    return (p["E1"] / p["R1"] + p["E2"] / p["R2"]) * _net_rp(p)


def _net_il(p: dict) -> float:
    """Load current from the Thevenin equivalent: I = Voc / (Rth + RL)."""
    return _net_voc(p) / (_net_rth(p) + p["RL"])


def _net_isc(p: dict) -> float:
    """Short-circuit (Norton) current at the load terminals."""
    return _net_voc(p) / _net_rth(p)


def _net_vl(p: dict) -> float:
    """Voltage across the load: Voc RL / (Rth + RL). At RL = Rth it is exactly half the open-circuit voltage,
    which is the condition for maximum power transfer."""
    return _net_voc(p) * p["RL"] / (_net_rth(p) + p["RL"])


def _net_i3(p: dict) -> float:
    """Current down R3, straight from the node equation at node 2. With the load branch in place the series pair
    R4 + RL loads node 2 as one resistance, so
        V2 (1/R1 + 1/R2 + 1/R3 + 1/(R4 + RL)) = E1/R1 + E2/R2,  I3 = V2 / R3."""
    g = 1.0 / p["R1"] + 1.0 / p["R2"] + 1.0 / p["R3"] + 1.0 / (p["R4"] + p["RL"])
    return (p["E1"] / p["R1"] + p["E2"] / p["R2"]) / g / p["R3"]


def _calc_net_rth(rows: list[dict], p: dict) -> float:
    """Thevenin resistance from the two readings a student takes: the open-circuit voltage (rows marked kind 0)
    and the short-circuit current (rows marked kind 1). Rth = Voc / Isc."""
    voc, nv, isc, ni = 0.0, 0, 0.0, 0
    for r in rows or []:
        try:
            k, v, i = float(r["kind"]), float(r["V"]), float(r["I"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (math.isfinite(v) and math.isfinite(i)):
            continue
        if k < 0.5:
            voc, nv = voc + v, nv + 1
        else:
            isc, ni = isc + i, ni + 1
    if not nv or not ni or isc == 0.0:
        return 0.0
    return (voc / nv) / (isc / ni)


# =================================================================================== series / parallel LCR (AC)
class Lcr:
    """A resistance, an inductance and a capacitance driven by a sine of frequency f and amplitude V, in the two
    arrangements the laboratory uses. `mode` 0 = the three in SERIES; `mode` 1 = the coil (R + jwL) in PARALLEL
    with C, fed from the generator through a series resistance Rs.

    Everything is the textbook's own phasor algebra in complex numbers: Z = R + j(wL - 1/(wC)) in series, and
    Y = 1/(R + jwL) + jwC in parallel. The RESONANT FREQUENCY is not printed from a formula: it is found by
    searching the simulated response for the frequency at which the current through the generator is greatest
    (series) or least (parallel), with a golden-section search of a fixed number of steps, so the number the
    student measures is the number the response really has. Q and the bandwidth come from the half-power points
    of that same simulated curve, found by bisection."""

    PARAMS = {"R": 50.0, "L": 0.01, "C": 1e-7, "f": 5000.0, "V": 1.0, "mode": 0.0}
    VARS = ["t", "Z", "I", "V_R", "V_L", "V_C", "phase", "gain"]

    # ---------------------------------------------------------------- complex helpers (a + jb as a 2-list)
    @staticmethod
    def _zser(p: dict, f: float) -> tuple[float, float]:
        w = 2 * PI * f
        return p["R"], w * p["L"] - 1.0 / (w * p["C"])

    @staticmethod
    def _zpar(p: dict, f: float) -> tuple[float, float]:
        """The coil in parallel with C: Z = 1 / (1/(R + jwL) + jwC)."""
        w = 2 * PI * f
        a, b = p["R"], w * p["L"]
        d = a * a + b * b
        ya, yb = a / d, -b / d + w * p["C"]
        dy = ya * ya + yb * yb
        return ya / dy, -yb / dy

    @staticmethod
    def _z(p: dict, f: float) -> tuple[float, float]:
        return Lcr._zpar(p, f) if p["mode"] >= 0.5 else Lcr._zser(p, f)

    @staticmethod
    def _current(p: dict, f: float) -> float:
        """Magnitude of the current the generator drives: V / |Z|, the reading of the meter in the supply lead."""
        a, b = Lcr._z(p, f)
        return p["V"] / math.sqrt(a * a + b * b)

    @staticmethod
    def _peak(p: dict) -> float:
        """The frequency at which the generator current turns: a maximum in series, a minimum in parallel.
        Golden-section search over a bracket four octaves wide around 1/(2*pi*sqrt(LC)) - the bracket only has
        to contain the turning point; the answer is read off the simulated response."""
        f0 = 1.0 / (2 * PI * math.sqrt(p["L"] * p["C"]))
        lo, hi = f0 / 4.0, f0 * 4.0
        want_max = p["mode"] < 0.5
        g = 0.6180339887498949
        c, d = hi - g * (hi - lo), lo + g * (hi - lo)
        fc, fd = Lcr._current(p, c), Lcr._current(p, d)
        for _ in range(120):
            better = (fc > fd) if want_max else (fc < fd)
            if better:
                hi, d, fd = d, c, fc
                c = hi - g * (hi - lo)
                fc = Lcr._current(p, c)
            else:
                lo, c, fc = c, d, fd
                d = lo + g * (hi - lo)
                fd = Lcr._current(p, d)
        return (lo + hi) / 2

    @staticmethod
    def _half(p: dict, fr: float, ipk: float, lo: float, hi: float) -> float:
        """The frequency between lo and hi at which the current is 1/sqrt(2) of its peak (bisection)."""
        want = ipk / math.sqrt(2.0)
        for _ in range(120):
            mid = (lo + hi) / 2
            above = Lcr._current(p, mid) > want
            if (mid < fr) == above:
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
        a, b = Lcr._z(p, p["f"])
        zmag = math.sqrt(a * a + b * b)
        i = p["V"] / zmag
        w = 2 * PI * p["f"]
        return {"t": s.get("t", 0.0), "Z": zmag, "I": i,
                "V_R": i * p["R"], "V_L": i * w * p["L"], "V_C": i / (w * p["C"]),
                "phase": math.atan2(b, a), "gain": p["R"] / zmag}

    @staticmethod
    def measure(p, cfg=None):
        fr = Lcr._peak(p)
        ipk = Lcr._current(p, fr)
        if p["mode"] < 0.5:                        # series: the half-power points sit either side of the peak
            f1 = Lcr._half(p, fr, ipk, fr / 8.0, fr)
            f2 = Lcr._half(p, fr, ipk, fr, fr * 8.0)
            bw = f2 - f1
            return {"fr": fr, "f1": f1, "f2": f2, "bw": bw, "Q": fr / bw if bw > 0 else 0.0,
                    "Ipk": ipk, "Zr": p["V"] / ipk}
        return {"fr": fr, "Ipk": ipk, "Zr": p["V"] / ipk,
                "Q": 2 * PI * fr * p["L"] / p["R"] if p["R"] > 0 else 0.0}


def _lcr_fr(p: dict) -> float:
    """Series resonance: the reactances cancel, wL = 1/(wC), so f = 1/(2 pi sqrt(LC))."""
    return 1.0 / (2 * PI * math.sqrt(p["L"] * p["C"]))


def _lcr_far(p: dict) -> float:
    """Anti-resonance of a real coil (R, L) in parallel with C: the frequency at which the impedance of the
    combination is GREATEST, so the current drawn from a constant-voltage generator is least - which is what the
    meter in the supply lead shows. Differentiating

        |Z|^2 = (R^2 + w^2 L^2) / ((1 - w^2 LC)^2 + (w R C)^2)

    with respect to w^2 and setting it to zero gives the quadratic (LC)^2 L^2 u^2 + 2 (LC)^2 R^2 u
    = L^2 + 2 L C R^2 - R^4 C^2 in u = w^2, whose positive root is

        w^2 = sqrt(w0^4 + 2 w0^2 R^2 / L^2) - R^2 / L^2,   w0^2 = 1/(LC).

    For a good coil this is w0 to within 1/(4 Q^4); the familiar unity-power-factor formula
    sqrt(1/(LC) - R^2/L^2) is a different frequency, lower by about 1/(2 Q^2)."""
    w02 = 1.0 / (p["L"] * p["C"])
    k = p["R"] * p["R"] / (p["L"] * p["L"])
    return math.sqrt(math.sqrt(w02 * w02 + 2 * w02 * k) - k) / (2 * PI)


def _lcr_bw(p: dict) -> float:
    """Bandwidth of a series circuit: R / (2 pi L)."""
    return p["R"] / (2 * PI * p["L"])


# =================================================================================== RC filter / RC-RL phase (AC)
class RcFilter:
    """A resistance and a capacitance in series across a sine generator. `mode` 0 takes the output across the
    CAPACITOR (a low-pass filter), `mode` 1 across the RESISTANCE (a high-pass filter). Phasor algebra again:
    the current leads the applied voltage by arctan(1/(wCR)), and the cut-off is where the output has fallen to
    1/sqrt(2) of the input - found here by bisection on the simulated gain, not read off a formula."""

    PARAMS = {"R": 1000.0, "C": 1e-7, "f": 1000.0, "V": 1.0, "mode": 0.0}
    VARS = ["t", "Z", "I", "gain", "dB", "phase", "V_R", "V_C"]

    @staticmethod
    def _gain(p: dict, f: float) -> float:
        x = 1.0 / (2 * PI * f * p["C"])
        z = math.sqrt(p["R"] * p["R"] + x * x)
        return (x if p["mode"] < 0.5 else p["R"]) / z

    @staticmethod
    def _cut(p: dict) -> float:
        """The cut-off frequency: bisection on the simulated gain between a decade below and a decade above
        1/(2 pi R C). The bracket only has to contain the point; the gain curve is the simulation's own."""
        f0 = 1.0 / (2 * PI * p["R"] * p["C"])
        lo, hi = f0 / 20.0, f0 * 20.0
        want = 1.0 / math.sqrt(2.0)
        rising = p["mode"] >= 0.5
        for _ in range(140):
            mid = (lo + hi) / 2
            if (RcFilter._gain(p, mid) > want) == rising:
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
        x = 1.0 / (2 * PI * p["f"] * p["C"])
        z = math.sqrt(p["R"] * p["R"] + x * x)
        i = p["V"] / z
        g = RcFilter._gain(p, p["f"])
        return {"t": s.get("t", 0.0), "Z": z, "I": i, "gain": g, "dB": 20 * math.log10(g),
                "phase": math.atan2(x, p["R"]) if p["mode"] < 0.5 else math.atan2(p["R"], x),
                "V_R": i * p["R"], "V_C": i * x}

    @staticmethod
    def measure(p, cfg=None):
        fc = RcFilter._cut(p)
        return {"fc": fc, "gain": RcFilter._gain(p, p["f"]), "Zc": 1.0 / (2 * PI * p["f"] * p["C"])}


def _rc_fc(p: dict) -> float:
    """Cut-off of a series RC filter: f = 1/(2 pi R C), where the reactance equals the resistance."""
    return 1.0 / (2 * PI * p["R"] * p["C"])


# =================================================================================== AC bridges
class AcBridge:
    """A four-arm alternating-current bridge. Each arm is a resistance, an inductance and a capacitance in
    SERIES, which is all four of the bridges in the syllabus need:
        De Sauty   - two resistive ratio arms against two capacitors;
        Owen       - a coil against a resistance and two capacitors;
        Maxwell    - a coil against a resistance in parallel with a capacitor (its series form here);
        universal  - the same frame read as R, L or C.
    The detector current is Thevenin's theorem applied to the bridge, exactly as the textbook derivation does:
        Vth = V (Z3/(Z1 + Z3) - Z4/(Z2 + Z4)),  Zth = Z1 Z3/(Z1 + Z3) + Z2 Z4/(Z2 + Z4),  Ig = Vth/(Zth + Zg).
    Balance is the detector current going to zero, found by a golden-section search on the balancing element -
    the simulated detector reading, not a formula. Arms 1 and 2 are the upper pair, 3 and 4 the lower pair, so
    arm 1 is above arm 3 and arm 2 above arm 4."""

    PARAMS = {"f": 1000.0, "V": 5.0, "Rg": 1000.0,
              "R1": 1000.0, "L1": 0.0, "C1": 0.0, "R2": 1000.0, "L2": 0.0, "C2": 0.0,
              "R3": 0.0, "L3": 0.0, "C3": 1e-7, "R4": 0.0, "L4": 0.0, "C4": 1e-7,
              "bal": 1000.0}
    VARS = ["t", "I_G", "V_G", "Z1", "Z2", "Z3", "Z4"]

    @staticmethod
    def _arm(p: dict, n: int) -> tuple[float, float]:
        w = 2 * PI * p["f"]
        r, l, c = p["R%d" % n], p["L%d" % n], p["C%d" % n]
        x = w * l
        if c > 0:
            x -= 1.0 / (w * c)
        return r, x

    @staticmethod
    def _div(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
        d = b[0] * b[0] + b[1] * b[1]
        return (a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d

    @staticmethod
    def _mul(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
        return a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]

    @staticmethod
    def _ig(p: dict) -> tuple[float, float]:
        z1, z2, z3, z4 = (AcBridge._arm(p, n) for n in (1, 2, 3, 4))
        s13 = (z1[0] + z3[0], z1[1] + z3[1])
        s24 = (z2[0] + z4[0], z2[1] + z4[1])
        d13 = AcBridge._div(z3, s13)
        d24 = AcBridge._div(z4, s24)
        vth = (p["V"] * (d13[0] - d24[0]), p["V"] * (d13[1] - d24[1]))
        p13 = AcBridge._div(AcBridge._mul(z1, z3), s13)
        p24 = AcBridge._div(AcBridge._mul(z2, z4), s24)
        zth = (p13[0] + p24[0] + p["Rg"], p13[1] + p24[1])
        return AcBridge._div(vth, zth)

    @staticmethod
    def _detector(p: dict, which: str, value: float) -> float:
        q = dict(p)
        q[which] = value
        a, b = AcBridge._ig(q)
        return math.sqrt(a * a + b * b)

    @staticmethod
    def _turn(p: dict, which: str, lo: float, hi: float) -> float:
        """Turn one dial until the detector is quietest: a golden-section search of a fixed number of steps."""
        g = 0.6180339887498949
        c, d = hi - g * (hi - lo), lo + g * (hi - lo)
        fc = AcBridge._detector(p, which, c)
        fd = AcBridge._detector(p, which, d)
        for _ in range(100):
            if fc < fd:
                hi, d, fd = d, c, fc
                c = hi - g * (hi - lo)
                fc = AcBridge._detector(p, which, c)
            else:
                lo, c, fc = c, d, fd
                d = lo + g * (hi - lo)
                fd = AcBridge._detector(p, which, d)
        return (lo + hi) / 2

    @staticmethod
    def _balance(p: dict, cfg: dict | None) -> dict:
        """Balance the bridge the way it is really done. A purely resistive-against-capacitive bridge (De Sauty,
        a universal bridge in its R or C setting) comes to a true null on ONE dial. A bridge with a coil in an
        arm has both a resistance and a reactance to cancel, so the two dials are turned ALTERNATELY, each in
        turn taken to the quietest point, until neither moves - which is exactly the instruction in the manual.
        The element names and ranges come from the lab's cfg.measure."""
        m = (cfg or {}).get("measure") or {}
        one = m.get("param", "bal")
        lo, hi = float(m.get("lo", 1.0)), float(m.get("hi", 1e5))
        two = m.get("param2")
        q = dict(p)
        if not two:
            q[one] = AcBridge._turn(q, one, lo, hi)
        else:
            lo2, hi2 = float(m.get("lo2", 1.0)), float(m.get("hi2", 1e5))
            for _ in range(14):                     # alternate rounds; each round is one pass of each dial
                q[one] = AcBridge._turn(q, one, lo, hi)
                q[two] = AcBridge._turn(q, two, lo2, hi2)
        a, b = AcBridge._ig(q)
        out = {"bal": q[one], "I_G": math.sqrt(a * a + b * b)}
        out[one] = q[one]
        if two:
            out[two] = q[two]
            out["bal2"] = q[two]
        return out

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        a, b = AcBridge._ig(p)
        out = {"t": s.get("t", 0.0), "I_G": math.sqrt(a * a + b * b),
               "V_G": math.sqrt(a * a + b * b) * p["Rg"]}
        for n in (1, 2, 3, 4):
            r, x = AcBridge._arm(p, n)
            out["Z%d" % n] = math.sqrt(r * r + x * x)
        return out

    @staticmethod
    def measure(p, cfg=None):
        return AcBridge._balance(p, cfg)


def _desauty_c(p: dict) -> float:
    """De Sauty: with two pure capacitors below and two resistances above, balance needs
    R1/R2 = C4/C3, so the unknown C3 = C4 R2/R1."""
    return p["C4"] * p["R2"] / p["R1"]


def _desauty_r2(p: dict) -> float:
    """The same balance read the other way: the ratio arm R2 at balance = R1 C3 / C4."""
    return p["R1"] * p["C3"] / p["C4"]


def _owen_l(p: dict) -> float:
    """Owen's bridge. Arm 1 is the unknown coil (R1 + jwL1), arm 2 is R2 in series with the variable standard
    capacitor C2, arm 3 is the fixed resistance R3 and arm 4 the standard capacitor C4. Balance is Z2 Z3 = Z1 Z4:

        (R2 - j/(w C2)) R3 = (R1 + j w L1) (-j/(w C4))  =  L1/C4 - j R1/(w C4),

    so the real parts give L1 = R2 R3 C4 and the imaginary parts R1 = R3 C4 / C2. The inductance therefore does
    not depend on the frequency at all, which is the whole point of Owen's bridge."""
    return p["R2"] * p["R3"] * p["C4"]


def _owen_r2(p: dict) -> float:
    """The same balance solved for the arm the student turns: R2 at balance = L1 / (R3 C4)."""
    return p["L1"] / (p["R3"] * p["C4"])


def _owen_c2(p: dict) -> float:
    """And for the capacitor dial: C2 at balance = R3 C4 / R1, which is how the coil's own resistance is read."""
    return p["R3"] * p["C4"] / p["R1"]


def _uni_r2(p: dict) -> float:
    """The universal bridge with all four arms resistive is a Wheatstone bridge driven by the oscillator:
    balance is R2 R3 = R1 R4, so the dial reads R2 = R1 R4 / R3."""
    return p["R1"] * p["R4"] / p["R3"]


KERNELS: dict[str, Any] = {"lcr": Lcr, "rcfilter": RcFilter, "acbridge": AcBridge}
FAMILY = {"lcr": "circuit", "rcfilter": "circuit", "acbridge": "circuit"}
TEXTBOOK = {
    "net_rth": _net_rth,
    "net_voc": _net_voc,
    "net_isc": _net_isc,
    "net_il": _net_il,
    "net_vl": _net_vl,
    "net_i3": _net_i3,
    "lcr_fr": _lcr_fr,
    "lcr_far": _lcr_far,
    "lcr_bw": _lcr_bw,
    "rc_fc": _rc_fc,
    "desauty_c": _desauty_c,
    "desauty_r2": _desauty_r2,
    "owen_l": _owen_l,
    "owen_r2": _owen_r2,
    "owen_c2": _owen_c2,
    "uni_r2": _uni_r2,
}
CALCS = {
    "net_rth": {"label": "Rth", "unit": "Ω", "needs": ["V", "I", "kind"], "fn": _calc_net_rth},
}
