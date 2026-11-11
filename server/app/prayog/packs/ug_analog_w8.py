"""Kernel pack `ug_analog_w8`: the undergraduate ANALOG ELECTRONICS, DEVICES and INSTRUMENT set-ups of
`syllabus/physics/ug.json` (wave 8). Its exact JavaScript twin is `app/static/prayog/packs/ug_analog_w8.js`; the test
suite runs both on the same inputs and demands the same numbers, so the two files carry the same formulas step by step.

Every kernel is prefixed `u8_`, is deterministic (fixed sample counts, fixed bisection counts, no randomness, no wall
clock) and works in SI units. The rig `ug8-analog-bench` draws the bench; every reading on its meters and its scope
comes from these functions.

Devices (DC, read on meters):
  u8_diode    p-n junction / LED / diode-connected transistor in a series circuit: Shockley + series + shunt resistance,
              solved by bisection; cut-in voltage, dynamic resistance and a Boltzmann-constant fit (DC meters or Arduino ADC)
  u8_tunnel   tunnel diode, the Sze empirical I-V (tunnel + excess + thermal current); peak, valley, PVR and NDR by scanning
  u8_bjt      n-p-n transistor, forward-active Ebers-Moll with the Early effect; h-parameters by finite differences and
              the transistor switch (NOT gate) transfer
Amplifiers and analog systems:
  u8_pp       class B / AB complementary push-pull output, piecewise-linear dead zone; THD by a DFT of the sampled output
  u8_opa      single-pole op-amp in inverting / non-inverting feedback; -3 dB frequency by bisection
  u8_diff     four-resistor difference amplifier with a finite-gain op-amp; differential, common-mode gain and CMRR
  u8_acomp    op-amp analog computer: simultaneous equations, first- and second-order ODEs, integrated by RK4
  u8_filt     second-order active filters (Sallen-Key low / high pass, band-pass, notch); cut-offs by bisection
  u8_jfet     self-biased common-source JFET amplifier (square law); gain and corners by scanning
  u8_dac      4-bit voltage-mode R-2R ladder solved by nodal analysis, buffered by a non-inverting stage
  u8_adc      8-bit successive-approximation converter (ADC0804 style, half-LSB offset), the SAR loop run bit by bit
  u8_sh       sample-and-hold: acquisition through the switch and droop on hold, exact exponential steps
  u8_reg      bridge rectifier + reservoir capacitor + 7805-type regulator: ripple, dropout, line and load regulation
  u8_pll      565-type phase-locked loop in the averaged phase domain (RK4): lock and capture ranges by bisection
Instruments:
  u8_count    universal counter: frequency (gate), period and average period, counting edges of the sampled signal
  u8_dfm      distortion factor meter: total rms, then the residual through a tunable notch
  u8_tstat    on-off thermostat in a heated bath: switching temperatures and times, exact exponential heating / cooling
  u8_noise    capacitive (electric-field) pick-up into a cable, unshielded or with a grounded / floating shield
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
KB = 1.380649e-23                # J/K, exact (SI 2019)
QE = 1.602176634e-19             # C, exact (SI 2019)
VT300 = 0.025852                 # thermal voltage at 300 K, the constant the other packs use
NS = 2400                        # samples on a scope trace


def _bis(f, lo: float, hi: float, n: int = 100) -> float:
    """Root of f in [lo, hi] by plain bisection with a fixed number of halvings (deterministic, twin-exact)."""
    flo = f(lo)
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if (fm > 0.0) == (flo > 0.0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _ols(xs: list, ys: list) -> float:
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(a * b for a, b in zip(xs, ys))
    sxx = sum(a * a for a in xs)
    den = n * sxx - sx * sx
    return 0.0 if den == 0 else (n * sxy - sx * sy) / den


def _cross(y: list, dt: float, level: float, rising: bool = True) -> list:
    out = []
    for i in range(1, len(y)):
        a, b = y[i - 1] - level, y[i] - level
        if rising and a < 0 <= b and b != a:
            out.append((i - 1 + (0 - a) / (b - a)) * dt)
        elif (not rising) and a >= 0 > b:
            out.append((i - 1 + (0 - a) / (b - a)) * dt)
    return out


def _cmul(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def _cdiv(a, b):
    d = b[0] * b[0] + b[1] * b[1]
    return ((a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d)


def _cabs(a) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1])


class _Static:
    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


# ================================================================================================== p-n diode / LED
class Diode(_Static):
    """A diode in series with R_ser across a supply V_s. The junction voltage V_j carries
        I = I_s (exp(V_j/(n V_T)) - 1) + V_j/R_sh,   V_T = k_B T / q,
    the terminal voltage is V = V_j + I R_s, and the loop is V_s = I R_ser + V. V_j is found by bisection (the loop
    function falls monotonically with V_j). `adc` = 1 reads the two voltages through a 10-bit converter on its 1.1 V
    reference (an Arduino's analogRead): each reading is rounded down to a whole count, as the converter does."""

    PARAMS = {"Vs": 1.0, "Rser": 100.0, "Is": 7.03e-9, "n": 1.80, "Rs": 0.034, "Rsh": 1.0e9, "T": 300.0,
              "kB": KB, "adc": 0.0}
    VARS = ["t", "V", "I_mA"]
    KB_VS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00, 1.10, 1.20, 1.35, 1.50]
    LSB = 1.1 / 1024.0

    @staticmethod
    def vt(p: dict) -> float:
        return p["kB"] * p["T"] / QE

    @staticmethod
    def i_of(p: dict, vj: float) -> float:
        return p["Is"] * (math.exp(vj / (p["n"] * Diode.vt(p))) - 1.0) + vj / p["Rsh"]

    @staticmethod
    def solve(p: dict, vs: float) -> tuple[float, float]:
        """(terminal voltage, current) for a supply vs."""
        r = p["Rser"] + p["Rs"]
        lo = min(vs, 0.0) - 1.0
        hi = max(vs, 0.0) + 1.0
        vj = _bis(lambda x: vs - Diode.i_of(p, x) * r - x, lo, hi, 100)
        i = Diode.i_of(p, vj)
        return vj + i * p["Rs"], i

    @staticmethod
    def v_at(p: dict, i: float) -> float:
        """Terminal voltage at a given current (bisection on V_j)."""
        vj = _bis(lambda x: Diode.i_of(p, x) - i, -2.0, 4.0, 100)
        return vj + i * p["Rs"]

    @staticmethod
    def read(p: dict, vs: float) -> tuple[float, float]:
        v, i = Diode.solve(p, vs)
        if int(round(p["adc"])) == 1:
            v = math.floor(v / Diode.LSB) * Diode.LSB
            vr = math.floor(i * p["Rser"] / Diode.LSB) * Diode.LSB
            i = vr / p["Rser"]
        return v, i

    @staticmethod
    def kfit(p: dict) -> float:
        xs, ys = [], []
        for vs in Diode.KB_VS:
            v, i = Diode.read(p, vs)
            if i > 0:
                xs.append(v)
                ys.append(math.log(i))
        m = _ols(xs, ys)
        return QE / (p["n"] * p["T"] * m) if m > 0 else 0.0

    @staticmethod
    def view(s, p, cfg=None):
        v, i = Diode.solve(p, p["Vs"])
        return {"t": s.get("t", 0.0), "V": v, "I_mA": i * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        v, i = Diode.read(p, p["Vs"])
        return {"V": v, "I": i, "Vcut": Diode.v_at(p, 1.0e-3),
                "rd": (Diode.v_at(p, 0.0105) - Diode.v_at(p, 0.0095)) / 0.001,
                "Irev": -Diode.i_of(p, -5.0), "kfit": Diode.kfit(p)}


def _diode_vcut(p: dict) -> float:
    """Textbook (Shockley, no shunt): V = n V_T ln(I/I_s + 1) + I R_s at I = 1 mA."""
    vt = p["kB"] * p["T"] / QE
    return p["n"] * vt * math.log(1.0e-3 / p["Is"] + 1.0) + 1.0e-3 * p["Rs"]


def _diode_kb(p: dict) -> float:
    return p["kB"]


# ================================================================================================== tunnel diode
class Tunnel(_Static):
    """Tunnel diode held at a voltage V by a stiff (low-resistance) source. The Sze empirical characteristic:
        I = I_p (V/V_p) exp(1 - V/V_p) + I_v exp(A_2 (V - V_v)) + I_s (exp(V/(n V_T)) - 1)
    (tunnel current, excess current, ordinary diffusion current). Peak, valley and the most negative slope are found
    by SCANNING V from 0 to 0.6 V in 0.1 mV steps."""

    PARAMS = {"V": 0.1, "Ip": 1.0e-3, "Vp": 0.065, "Iv": 1.2e-4, "Vv": 0.35, "A2": 15.0, "Is": 1.0e-12, "n": 1.0}
    VARS = ["t", "V", "I_mA"]

    @staticmethod
    def i_of(p: dict, v: float) -> float:
        return (p["Ip"] * (v / p["Vp"]) * math.exp(1.0 - v / p["Vp"]) + p["Iv"] * math.exp(p["A2"] * (v - p["Vv"]))
                + p["Is"] * (math.exp(v / (p["n"] * VT300)) - 1.0))

    @staticmethod
    def scan(p: dict) -> dict:
        n = 6001
        ii = [Tunnel.i_of(p, 0.0001 * k) for k in range(n)]
        kp = 0
        while kp < n - 1 and ii[kp + 1] >= ii[kp]:
            kp += 1
        kv = kp
        while kv < n - 1 and ii[kv + 1] <= ii[kv]:
            kv += 1
        ipk = ii[kp]
        smin = 0.0
        for k in range(kp + 1, kv + 1):
            s = (ii[k] - ii[k - 1]) / 0.0001
            if s < smin:
                smin = s
        return {"Ipk": ipk, "Vpk": 0.0001 * kp, "Ival": ii[kv], "Vval": 0.0001 * kv, "pvr": ipk / ii[kv],
                "Rneg": 1.0 / smin if smin < 0 else 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "V": p["V"], "I_mA": Tunnel.i_of(p, p["V"]) * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        m = Tunnel.scan(p)
        m["I"] = Tunnel.i_of(p, p["V"])
        return m


def _tunnel_ip(p: dict) -> float:
    """Textbook: the tunnel term alone peaks at V = V_p with the value I_p."""
    return p["Ip"]


# ================================================================================================== BJT
class Bjt(_Static):
    """n-p-n transistor in the forward-active region (Ebers-Moll with the Early effect), T = 300 K:
        I_B = (I_s/beta_F) (exp(V_BE/V_T) - 1) / (1 + V_CE/V_Ar)
        I_C = I_s (exp(V_BE/V_T) - 1) (1 + V_CE/V_A) (1 - exp(-V_CE/V_sat))
    V_Ar is a small reverse feedback (it gives h_re), the last factor pulls I_C down in saturation. For the
    h-parameters the base current and V_CE are set and V_BE follows. For the switch (NOT gate) V_in drives the base
    through R_b, R_c is the collector load from V_cc, and V_CE is solved by nested bisection."""

    PARAMS = {"Ib": 2.0e-5, "Vce": 5.0, "Is": 1.0e-14, "bF": 250.0, "VA": 80.0, "VAr": 150.0, "Vsat": 0.05,
              "Vin": 0.0, "Vcc": 5.0, "Rb": 10000.0, "Rc": 1000.0, "dIb": 5.0e-6, "dVce": 1.0}
    VARS = ["t", "Vbe", "Ic_mA", "Vout"]

    @staticmethod
    def vbe(p: dict, ib: float, vce: float) -> float:
        return VT300 * math.log(ib * p["bF"] * (1.0 + vce / p["VAr"]) / p["Is"] + 1.0)

    @staticmethod
    def ic(p: dict, ib: float, vce: float) -> float:
        x = Bjt.vbe(p, ib, vce)
        return p["Is"] * (math.exp(x / VT300) - 1.0) * (1.0 + vce / p["VA"]) * (1.0 - math.exp(-vce / p["Vsat"]))

    @staticmethod
    def hparams(p: dict) -> dict:
        ib, vce, d, dv = p["Ib"], p["Vce"], p["dIb"], p["dVce"]
        hie = (Bjt.vbe(p, ib + d, vce) - Bjt.vbe(p, ib - d, vce)) / (2.0 * d)
        hfe = (Bjt.ic(p, ib + d, vce) - Bjt.ic(p, ib - d, vce)) / (2.0 * d)
        hoe = (Bjt.ic(p, ib, vce + dv) - Bjt.ic(p, ib, vce - dv)) / (2.0 * dv)
        hre = (Bjt.vbe(p, ib, vce + dv) - Bjt.vbe(p, ib, vce - dv)) / (2.0 * dv)
        return {"hie": hie, "hfe": hfe, "hoe": hoe, "hre": hre}

    @staticmethod
    def ib_in(p: dict, vin: float, vce: float) -> float:
        """Base current with V_in driving the base through R_b (bisection on V_BE)."""
        if vin <= 0.0:
            return 0.0
        k = p["Is"] / p["bF"] / (1.0 + vce / p["VAr"])
        x = _bis(lambda v: vin - p["Rb"] * k * (math.exp(v / VT300) - 1.0) - v, 0.0, vin, 80)
        return k * (math.exp(x / VT300) - 1.0)

    @staticmethod
    def vout(p: dict, vin: float) -> float:
        def g(vce):
            ib = Bjt.ib_in(p, vin, vce)
            if ib <= 0.0:
                return p["Vcc"] - vce
            return p["Vcc"] - Bjt.ic(p, ib, vce) * p["Rc"] - vce
        return _bis(g, 1.0e-9, p["Vcc"], 60)

    @staticmethod
    def vth(p: dict) -> float:
        """Input voltage at which the output sits at V_cc/2 (exact inversion of the model)."""
        vce = 0.5 * p["Vcc"]
        ic = (p["Vcc"] - vce) / p["Rc"]
        e = ic / (p["Is"] * (1.0 + vce / p["VA"]) * (1.0 - math.exp(-vce / p["Vsat"]))) + 1.0
        ib = p["Is"] / p["bF"] * (e - 1.0) / (1.0 + vce / p["VAr"])
        return VT300 * math.log(e) + p["Rb"] * ib

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Vbe": Bjt.vbe(p, p["Ib"], p["Vce"]), "Ic_mA": Bjt.ic(p, p["Ib"], p["Vce"]) * 1000.0,
                "Vout": p["Vcc"]}

    @staticmethod
    def measure(p, cfg=None):
        m = Bjt.hparams(p)
        m["Vbe"] = Bjt.vbe(p, p["Ib"], p["Vce"])
        m["Ic"] = Bjt.ic(p, p["Ib"], p["Vce"])
        m["Vout"] = Bjt.vout(p, p["Vin"])
        m["Vth"] = Bjt.vth(p)
        return m


def _bjt_hfe(p: dict) -> float:
    """Textbook: I_C = beta_F I_B (1 + V_CE/V_A)(1 + V_CE/V_Ar)(1 - exp(-V_CE/V_sat)), linear in I_B."""
    v = p["Vce"]
    return p["bF"] * (1.0 + v / p["VA"]) * (1.0 + v / p["VAr"]) * (1.0 - math.exp(-v / p["Vsat"]))


def _bjt_vth(p: dict) -> float:
    """Textbook switch threshold with a constant beta and no Early effect: V_in = V_T ln(I_C/I_s) + R_b I_C/beta."""
    ic = 0.5 * p["Vcc"] / p["Rc"]
    return VT300 * math.log(ic / p["Is"]) + p["Rb"] * ic / p["bF"]


# ================================================================================================== push-pull
class PushPull(_Static):
    """Complementary emitter-follower push-pull stage, piecewise-linear: no output until the input passes the
    turn-on voltage V_g of one transistor, then v_out = v_in - V_g (positive half) or v_in + V_g (negative half).
    `mode` 1 adds two bias diodes (V_bias) that shrink the dead zone to max(0, V_g - V_bias): class AB. One period is
    sampled at NS mid-points; the fundamental is a one-term DFT and THD = sqrt(2 rms^2 / b_1^2 - 1)."""

    PARAMS = {"Vp": 3.0, "Vg": 0.6, "Vbias": 0.55, "mode": 0.0, "RL": 8.0, "f": 1000.0}
    VARS = ["t", "Vop", "thd_pct"]

    @staticmethod
    def dz(p: dict) -> float:
        return max(0.0, p["Vg"] - p["Vbias"]) if int(round(p["mode"])) == 1 else p["Vg"]

    @staticmethod
    def wave(p: dict) -> list:
        d = PushPull.dz(p)
        out = []
        for i in range(NS):
            v = p["Vp"] * math.sin(2.0 * PI * (i + 0.5) / NS)
            out.append(v - d if v > d else v + d if v < -d else 0.0)
        return out

    @staticmethod
    def analyse(p: dict) -> dict:
        y = PushPull.wave(p)
        b1 = 0.0
        ms = 0.0
        for i in range(NS):
            b1 += y[i] * math.sin(2.0 * PI * (i + 0.5) / NS)
            ms += y[i] * y[i]
        b1 = 2.0 * b1 / NS
        ms = ms / NS
        thd = math.sqrt(max(0.0, 2.0 * ms / (b1 * b1) - 1.0)) if b1 > 0 else 0.0
        return {"Vop": max(y), "b1": b1, "rms": math.sqrt(ms), "thd": thd, "Pout": ms / p["RL"]}

    @staticmethod
    def view(s, p, cfg=None):
        a = PushPull.analyse(p)
        return {"t": s.get("t", 0.0), "Vop": a["Vop"], "thd_pct": a["thd"] * 100.0}

    @staticmethod
    def measure(p, cfg=None):
        return PushPull.analyse(p)


def _pp_thd(p: dict) -> float:
    """Textbook (Fourier series of a sine with a dead zone d = V_g/V_p, theta_0 = asin d):
        b_1 = (V_p/pi)(pi - 2 theta_0 - 2 d cos theta_0)
        rms^2 = (1/pi)[V_p^2((pi - 2 theta_0)/2 + d cos theta_0) - 4 V_p V_g cos theta_0 + V_g^2 (pi - 2 theta_0)]."""
    vp, vg = p["Vp"], PushPull.dz(p)
    d = vg / vp
    t0 = math.asin(d)
    c = math.cos(t0)
    b1 = vp / PI * (PI - 2.0 * t0 - 2.0 * d * c)
    ms = (vp * vp * ((PI - 2.0 * t0) / 2.0 + d * c) - 4.0 * vp * vg * c + vg * vg * (PI - 2.0 * t0)) / PI
    return math.sqrt(max(0.0, 2.0 * ms / (b1 * b1) - 1.0))


# ================================================================================================== op-amp frequency response
class Opa(_Static):
    """Single-pole op-amp A(f) = A_0 / (1 + j f/f_a) (gain-bandwidth product A_0 f_a) with feedback fraction
    beta = R_1/(R_1 + R_f). Non-inverting: H = A/(1 + A beta); inverting: H = -(R_f/(R_1 + R_f)) A/(1 + A beta).
    The -3 dB frequency is found by bisection on log f; GBW is then f_3 times the noise gain 1/beta."""

    PARAMS = {"A0": 2.0e5, "fa": 5.0, "R1": 1000.0, "Rf": 10000.0, "cfg": 0.0, "f": 1000.0, "Vin": 0.01}
    VARS = ["t", "gain", "ph"]

    @staticmethod
    def h(p: dict, f: float):
        a = _cdiv((p["A0"], 0.0), (1.0, f / p["fa"]))
        b = p["R1"] / (p["R1"] + p["Rf"])
        cl = _cdiv(a, (1.0 + a[0] * b, a[1] * b))
        if int(round(p["cfg"])) == 0:
            k = -p["Rf"] / (p["R1"] + p["Rf"])
            return (cl[0] * k, cl[1] * k)
        return cl

    @staticmethod
    def gain(p: dict, f: float) -> float:
        return _cabs(Opa.h(p, f))

    @staticmethod
    def f3(p: dict) -> float:
        g0 = Opa.gain(p, 1.0e-3)
        t = g0 / math.sqrt(2.0)
        lf = _bis(lambda x: Opa.gain(p, 10.0 ** x) - t, -1.0, 9.0, 80)
        return 10.0 ** lf

    @staticmethod
    def view(s, p, cfg=None):
        hh = Opa.h(p, p["f"])
        return {"t": s.get("t", 0.0), "gain": _cabs(hh), "ph": math.degrees(math.atan2(hh[1], hh[0]))}

    @staticmethod
    def measure(p, cfg=None):
        f3 = Opa.f3(p)
        hh = Opa.h(p, p["f"])
        return {"G0": Opa.gain(p, 1.0e-3), "f3": f3, "gbw": f3 * (1.0 + p["Rf"] / p["R1"]), "gain": _cabs(hh),
                "ph": math.degrees(math.atan2(hh[1], hh[0]))}


def _opa_gbw(p: dict) -> float:
    return p["A0"] * p["fa"]


# ================================================================================================== difference amplifier
class Diff(_Static):
    """Four-resistor difference amplifier (V_1 to R_1 at the inverting input, R_2 feedback; V_2 through R_3 to the
    non-inverting input, R_4 to ground). R_4 is off its nominal value by a fraction eps (the resistors' mismatch).
    With a finite open-loop gain A_0:
        V_out = A_0 (V_2 R_4'/(R_3 + R_4') - V_1 R_2/(R_1 + R_2)) / (1 + A_0 R_1/(R_1 + R_2))."""

    PARAMS = {"R1": 10000.0, "R2": 100000.0, "R3": 10000.0, "R4": 100000.0, "eps": 0.004, "A0": 2.0e5,
              "Vd": 0.1, "Vc": 1.0, "mode": 0.0}
    VARS = ["t", "Vout"]

    @staticmethod
    def out(p: dict, v1: float, v2: float) -> float:
        r4 = p["R4"] * (1.0 + p["eps"])
        b = p["R1"] / (p["R1"] + p["R2"])
        return p["A0"] * (v2 * r4 / (p["R3"] + r4) - v1 * p["R2"] / (p["R1"] + p["R2"])) / (1.0 + p["A0"] * b)

    @staticmethod
    def gains(p: dict) -> dict:
        ad = (Diff.out(p, -0.5 * p["Vd"], 0.5 * p["Vd"])) / p["Vd"]
        acm = Diff.out(p, p["Vc"], p["Vc"]) / p["Vc"]
        cm = abs(ad / acm) if acm != 0 else 0.0
        return {"Ad": ad, "Acm": acm, "cmrr": cm, "cmrr_db": 20.0 * math.log10(cm) if cm > 0 else 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        if int(round(p["mode"])) == 0:
            v = Diff.out(p, -0.5 * p["Vd"], 0.5 * p["Vd"])
        else:
            v = Diff.out(p, p["Vc"], p["Vc"])
        return {"t": s.get("t", 0.0), "Vout": v}

    @staticmethod
    def measure(p, cfg=None):
        return Diff.gains(p)


def _diff_acm(p: dict) -> float:
    """Textbook ideal op-amp: A_cm = R_4'/(R_3 + R_4') (1 + R_2/R_1) - R_2/R_1."""
    r4 = p["R4"] * (1.0 + p["eps"])
    return r4 / (p["R3"] + r4) * (1.0 + p["R2"] / p["R1"]) - p["R2"] / p["R1"]


# ================================================================================================== analog computer
class Acomp(_Static):
    """Op-amp analog computer, every integrator of time constant R C (R = the integrator resistor, C = the capacitor):
      cfg 0  simultaneous equations a1 x + b1 y = c1, a2 x + b2 y = c2: two integrators in a loop relax as
             R C dx/dt = c1 - a1 x - b1 y,  R C dy/dt = c2 - a2 x - b2 y   (settles when the matrix is positive definite)
      cfg 1  first order:  R C dv/dt = -v, v(0) = V_0
      cfg 2  second order: x'' + 2 zeta w x' + w^2 x = 0, w = 1/(R C), x(0) = V_0
    Each is integrated by RK4 with a fixed number of steps; the readings are taken on the computed solution."""

    PARAMS = {"cfg": 2.0, "R": 100000.0, "C": 1.0e-7, "a1": 2.0, "b1": 1.0, "c1": 5.0, "a2": 1.0, "b2": 3.0,
              "c2": 10.0, "V0": 5.0, "z": 0.2}
    VARS = ["t", "rc"]

    @staticmethod
    def simul(p: dict) -> tuple[float, float]:
        rc = p["R"] * p["C"]
        dt = rc / 50.0
        x = y = 0.0

        def d(x, y):
            return ((p["c1"] - p["a1"] * x - p["b1"] * y) / rc, (p["c2"] - p["a2"] * x - p["b2"] * y) / rc)
        for _ in range(1500):
            k1 = d(x, y)
            k2 = d(x + 0.5 * dt * k1[0], y + 0.5 * dt * k1[1])
            k3 = d(x + 0.5 * dt * k2[0], y + 0.5 * dt * k2[1])
            k4 = d(x + dt * k3[0], y + dt * k3[1])
            x += dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
            y += dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
        return x, y

    @staticmethod
    def first(p: dict) -> tuple[list, float, float]:
        rc = p["R"] * p["C"]
        dt = 5.0 * rc / NS
        v = p["V0"]
        ys = []
        for _ in range(NS):
            ys.append(v)
            k1 = -v / rc
            k2 = -(v + 0.5 * dt * k1) / rc
            k3 = -(v + 0.5 * dt * k2) / rc
            k4 = -(v + dt * k3) / rc
            v += dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        c = _cross(ys, dt, p["V0"] / math.e, False)
        return ys, dt, c[0] if c else 0.0

    @staticmethod
    def second(p: dict) -> tuple[list, float, float]:
        w = 1.0 / (p["R"] * p["C"])
        dt = 3.0 * (2.0 * PI / w) / NS
        x, v = p["V0"], 0.0
        ys = []
        z = p["z"]

        def a(x, v):
            return -2.0 * z * w * v - w * w * x
        for _ in range(NS):
            ys.append(x)
            k1x, k1v = v, a(x, v)
            k2x, k2v = v + 0.5 * dt * k1v, a(x + 0.5 * dt * k1x, v + 0.5 * dt * k1v)
            k3x, k3v = v + 0.5 * dt * k2v, a(x + 0.5 * dt * k2x, v + 0.5 * dt * k2v)
            k4x, k4v = v + dt * k3v, a(x + dt * k3x, v + dt * k3v)
            x += dt / 6.0 * (k1x + 2.0 * k2x + 2.0 * k3x + k4x)
            v += dt / 6.0 * (k1v + 2.0 * k2v + 2.0 * k3v + k4v)
        dn = _cross(ys, dt, 0.0, False)
        fd = 1.0 / (dn[1] - dn[0]) if len(dn) >= 2 else 0.0
        return ys, dt, fd

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "rc": p["R"] * p["C"]}

    @staticmethod
    def measure(p, cfg=None):
        x, y = Acomp.simul(p)
        _, _, tau = Acomp.first(p)
        _, _, fd = Acomp.second(p)
        return {"x": x, "y": y, "tau": tau, "fd": fd}


def _acomp_fd(p: dict) -> float:
    """Textbook: the damped frequency f_d = sqrt(1 - zeta^2) / (2 pi R C)."""
    return math.sqrt(1.0 - p["z"] * p["z"]) / (2.0 * PI * p["R"] * p["C"])


def _acomp_x(p: dict) -> float:
    """Cramer's rule: x = (c1 b2 - b1 c2)/(a1 b2 - b1 a2)."""
    return (p["c1"] * p["b2"] - p["b1"] * p["c2"]) / (p["a1"] * p["b2"] - p["b1"] * p["a2"])


# ================================================================================================== active filters
class Filt(_Static):
    """Second-order active filter, x = f/f_0, f_0 = 1/(2 pi R C), D = 1 - x^2 + j x/Q:
      kind 0  Sallen-Key low-pass   H = K / D,            Q = 1/(3 - K)  (equal R and C)
      kind 1  Sallen-Key high-pass  H = -K x^2 / D,        Q = 1/(3 - K)
      kind 2  band-pass             H = (j x/Q) / D        (unity gain at f_0)
      kind 3  band-reject (notch)   H = (1 - x^2) / D      (unity gain far from f_0)
    Cut-off frequencies (|H| = reference/sqrt 2) are found by bisection on log f; for a band filter fc is the lower
    edge and fc2 the upper one."""

    PARAMS = {"kind": 0.0, "R": 10000.0, "C": 1.0e-8, "K": 1.586, "Q": 2.0, "f": 1000.0}
    VARS = ["t", "gain", "f0"]

    @staticmethod
    def f0(p: dict) -> float:
        return 1.0 / (2.0 * PI * p["R"] * p["C"])

    @staticmethod
    def q(p: dict) -> float:
        k = int(round(p["kind"]))
        return 1.0 / (3.0 - p["K"]) if k <= 1 else p["Q"]

    @staticmethod
    def h(p: dict, f: float):
        x = f / Filt.f0(p)
        k = int(round(p["kind"]))
        d = (1.0 - x * x, x / Filt.q(p))
        if k == 0:
            num = (p["K"], 0.0)
        elif k == 1:
            num = (-p["K"] * x * x, 0.0)
        elif k == 2:
            num = (0.0, x / Filt.q(p))
        else:
            num = (1.0 - x * x, 0.0)
        return _cdiv(num, d)

    @staticmethod
    def ref(p: dict) -> float:
        return p["K"] if int(round(p["kind"])) <= 1 else 1.0

    @staticmethod
    def edges(p: dict) -> tuple[float, float]:
        f0 = Filt.f0(p)
        t = Filt.ref(p) / math.sqrt(2.0)
        k = int(round(p["kind"]))
        lf0 = math.log10(f0)

        def g(x):
            return _cabs(Filt.h(p, 10.0 ** x)) - t
        if k == 0:
            return 10.0 ** _bis(g, lf0 - 2.0, lf0 + 2.0, 80), 0.0
        if k == 1:
            return 10.0 ** _bis(g, lf0 - 2.0, lf0 + 2.0, 80), 0.0
        lo = 10.0 ** _bis(g, lf0 - 2.0, lf0, 80)
        hi = 10.0 ** _bis(g, lf0, lf0 + 2.0, 80)
        return lo, hi

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "gain": _cabs(Filt.h(p, p["f"])), "f0": Filt.f0(p)}

    @staticmethod
    def measure(p, cfg=None):
        a, b = Filt.edges(p)
        hh = Filt.h(p, p["f"])
        return {"fc": a, "fc2": b, "f0": Filt.f0(p), "gain": _cabs(hh), "ph": math.degrees(math.atan2(hh[1], hh[0]))}


def _filt_fc(p: dict) -> float:
    """Textbook: low-pass x_c^2 = u, u^2 - (2 - 1/Q^2) u - 1 = 0; high-pass x_c = 1/x_c(low-pass); band-pass and
    notch edges x = sqrt(1 + 1/(4 Q^2)) -/+ 1/(2 Q) (the lower one returned)."""
    f0 = 1.0 / (2.0 * PI * p["R"] * p["C"])
    k = int(round(p["kind"]))
    if k <= 1:
        q = 1.0 / (3.0 - p["K"])
        a = 2.0 - 1.0 / (q * q)
        u = (a + math.sqrt(a * a + 4.0)) / 2.0
        return f0 * math.sqrt(u) if k == 0 else f0 / math.sqrt(u)
    q = p["Q"]
    return f0 * (math.sqrt(1.0 + 1.0 / (4.0 * q * q)) - 1.0 / (2.0 * q))


# ================================================================================================== JFET common source
class Jfet(_Static):
    """Self-biased common-source JFET amplifier. Square law I_D = I_DSS (1 - V_GS/V_P)^2 with V_GS = -I_D R_S, solved by
    bisection; g_m = 2 sqrt(I_D I_DSS)/|V_P|. Small signal: mid-band A = g_m (R_D || R_L) R_G/(R_G + R_sig) times
        input coupling (C_in, R_sig + R_G), output coupling (C_out, R_D + R_L), the source network
        (1 + j f/f_z)/(1 + j f/f_p)/(1 + g_m R_S) with f_z = 1/(2 pi R_S C_S), f_p = (1 + g_m R_S) f_z,
        and one Miller pole 1/(2 pi (R_sig || R_G)(C_gs + C_gd (1 + g_m R_L'))).
    Mid-band gain and the -3 dB corners are found by SCANNING 1 Hz ... 100 MHz (40 points a decade, then bisection)."""

    PARAMS = {"Vdd": 15.0, "Idss": 0.010, "Vp": -4.0, "Rs": 680.0, "Rd": 2200.0, "RL": 10000.0, "Rg": 1.0e6,
              "Rsig": 10000.0, "Cin": 1.0e-7, "Cout": 1.0e-6, "Cs": 2.2e-5, "Cgs": 4.0e-12, "Cgd": 1.0e-12, "f": 10000.0}
    VARS = ["t", "Id_mA", "Vgs", "Vds", "gm_mS"]

    @staticmethod
    def bias(p: dict) -> tuple[float, float]:
        a = abs(p["Vp"])
        hi = min(p["Idss"], a / p["Rs"])
        idd = _bis(lambda i: p["Idss"] * (1.0 - i * p["Rs"] / a) ** 2 - i, 0.0, hi, 100)
        return idd, 2.0 * math.sqrt(idd * p["Idss"]) / a

    @staticmethod
    def h(p: dict, f: float):
        idd, gm = Jfet.bias(p)
        rl = p["Rd"] * p["RL"] / (p["Rd"] + p["RL"])
        am = gm * rl * p["Rg"] / (p["Rg"] + p["Rsig"])
        f1 = 1.0 / (2.0 * PI * (p["Rsig"] + p["Rg"]) * p["Cin"])
        f2 = 1.0 / (2.0 * PI * (p["Rd"] + p["RL"]) * p["Cout"])
        fz = 1.0 / (2.0 * PI * p["Rs"] * p["Cs"])
        fp = (1.0 + gm * p["Rs"]) * fz
        rp = p["Rsig"] * p["Rg"] / (p["Rsig"] + p["Rg"])
        fh = 1.0 / (2.0 * PI * rp * (p["Cgs"] + p["Cgd"] * (1.0 + gm * rl)))
        hh = (-am, 0.0)
        hh = _cmul(hh, _cdiv((0.0, f / f1), (1.0, f / f1)))
        hh = _cmul(hh, _cdiv((0.0, f / f2), (1.0, f / f2)))
        hh = _cmul(hh, _cdiv((1.0, f / fz), (1.0 + gm * p["Rs"], (1.0 + gm * p["Rs"]) * f / fp)))
        hh = _cdiv(hh, (1.0, f / fh))
        return hh

    @staticmethod
    def gain(p: dict, f: float) -> float:
        return _cabs(Jfet.h(p, f))

    @staticmethod
    def scan(p: dict) -> dict:
        best, lb = 0.0, 0.0
        for i in range(321):
            lf = 8.0 * i / 320.0
            g = Jfet.gain(p, 10.0 ** lf)
            if g > best:
                best, lb = g, lf
        t = best / math.sqrt(2.0)
        fl = 10.0 ** _bis(lambda x: Jfet.gain(p, 10.0 ** x) - t, 0.0, lb, 80)
        fh = 10.0 ** _bis(lambda x: Jfet.gain(p, 10.0 ** x) - t, lb, 8.0, 80)
        return {"Amid": best, "fL": fl, "fH": fh}

    @staticmethod
    def view(s, p, cfg=None):
        idd, gm = Jfet.bias(p)
        return {"t": s.get("t", 0.0), "Id_mA": idd * 1000.0, "Vgs": -idd * p["Rs"], "Vds": p["Vdd"] - idd * (p["Rd"] + p["Rs"]),
                "gm_mS": gm * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        m = Jfet.scan(p)
        idd, gm = Jfet.bias(p)
        hh = Jfet.h(p, p["f"])
        m.update({"Id": idd, "gm": gm, "A": _cabs(hh), "ph": math.degrees(math.atan2(hh[1], hh[0]))})
        return m


def _jfet_amid(p: dict) -> float:
    """Textbook: A_mid = g_m (R_D || R_L) R_G/(R_G + R_sig), g_m = (2 I_DSS/|V_P|)(1 - V_GS/V_P)."""
    a = abs(p["Vp"])
    # the bias point from the quadratic: I_D = I_DSS (1 - I_D R_S/a)^2
    k = p["Rs"] / a
    aa = p["Idss"] * k * k
    bb = -(2.0 * p["Idss"] * k + 1.0)
    idd = (-bb - math.sqrt(bb * bb - 4.0 * aa * p["Idss"])) / (2.0 * aa)
    gm = 2.0 * p["Idss"] / a * (1.0 - idd * p["Rs"] / a)
    return gm * (p["Rd"] * p["RL"] / (p["Rd"] + p["RL"])) * p["Rg"] / (p["Rg"] + p["Rsig"])


# ================================================================================================== R-2R DAC
class Dac(_Static):
    """4-bit voltage-mode R-2R ladder: node k (k = 0 the LSB end) has a 2R leg to bit k (V_ref or 0 V); neighbouring
    nodes are joined by R; the LSB node also has a 2R termination to ground. The node voltages are solved by the
    Thomas (tridiagonal) algorithm; the MSB node drives a non-inverting buffer of gain 1 + R_f/R_g."""

    PARAMS = {"D": 9.0, "Vref": 5.0, "R": 10000.0, "Rf": 6200.0, "Rg": 10000.0}
    VARS = ["t", "Vout"]
    NB = 4

    @staticmethod
    def node(p: dict, code: int) -> float:
        n, r = Dac.NB, p["R"]
        g2, g1 = 1.0 / (2.0 * r), 1.0 / r
        a, b, c, d = [], [], [], []
        for k in range(n):
            bit = (code >> k) & 1
            diag = g2 + (g2 if k == 0 else g1) + (g1 if k < n - 1 else 0.0)
            a.append(-g1 if k > 0 else 0.0)
            b.append(diag)
            c.append(-g1 if k < n - 1 else 0.0)
            d.append(g2 * p["Vref"] * bit)
        for k in range(1, n):
            m = a[k] / b[k - 1]
            b[k] -= m * c[k - 1]
            d[k] -= m * d[k - 1]
        x = d[n - 1] / b[n - 1]
        return x

    @staticmethod
    def vout(p: dict, code: int) -> float:
        return Dac.node(p, code) * (1.0 + p["Rf"] / p["Rg"])

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Vout": Dac.vout(p, int(round(p["D"])))}

    @staticmethod
    def measure(p, cfg=None):
        fs = Dac.vout(p, 15)
        return {"Vout": Dac.vout(p, int(round(p["D"]))), "lsb": (fs - Dac.vout(p, 0)) / 15.0, "fs": fs}


def _dac_v(p: dict) -> float:
    """Textbook: V_out = V_ref (1 + R_f/R_g) D / 2^n."""
    return p["Vref"] * (1.0 + p["Rf"] / p["Rg"]) * round(p["D"]) / 16.0


# ================================================================================================== SAR ADC
class Adc(_Static):
    """8-bit successive-approximation converter: span V_ref (ADC0804 style: V_ref/2 on its pin sets the span), the
    internal comparison levels sit half an LSB low so that the code is the NEAREST one. The SAR loop tries each bit
    from the MSB down and keeps it when V_in is at or above the trial level."""

    PARAMS = {"Vin": 2.0, "Vref": 5.0}
    VARS = ["t", "code"]

    @staticmethod
    def code(p: dict, vin: float) -> int:
        lsb = p["Vref"] / 256.0
        c = 0
        for b in range(7, -1, -1):
            trial = c | (1 << b)
            if vin >= (trial - 0.5) * lsb:
                c = trial
        return c

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "code": float(Adc.code(p, p["Vin"]))}

    @staticmethod
    def measure(p, cfg=None):
        return {"code": float(Adc.code(p, p["Vin"])), "lsb": p["Vref"] / 256.0}


def _adc_code(p: dict) -> float:
    """Textbook: the nearest code, min(255, floor(V_in/LSB + 1/2)), LSB = V_ref/256."""
    return float(max(0, min(255, math.floor(p["Vin"] / (p["Vref"] / 256.0) + 0.5))))


# ================================================================================================== sample and hold
class Sh(_Static):
    """Sample-and-hold with an analog switch of on-resistance R_on fed through R_src from a DC level V_s. With the
    switch closed at t = 0 the hold capacitor charges as V_s (1 - exp(-t/tau)), tau = (R_src + R_on) C_h (exact steps);
    after 6 tau the switch opens and a leakage current I_leak droops the capacitor at I_leak/C_h. The 10 % and 90 %
    crossings of the sampled trace give the acquisition time t_90 - t_10 = tau ln 9."""

    PARAMS = {"Vs": 2.0, "Rsrc": 1000.0, "Ron": 125.0, "Ch": 1.0e-8, "Ileak": 1.0e-9}
    VARS = ["t", "tau_us"]

    @staticmethod
    def trace(p: dict) -> tuple[list, list, float]:
        tau = (p["Rsrc"] + p["Ron"]) * p["Ch"]
        span = 10.0 * tau
        dt = span / NS
        e = math.exp(-dt / tau)
        sw, vc = [], []
        v = 0.0
        for i in range(NS):
            t = i * dt
            on = 1.0 if t < 6.0 * tau else 0.0
            sw.append(5.0 * on)
            vc.append(v)
            if on > 0:
                v = p["Vs"] + (v - p["Vs"]) * e
            else:
                v -= p["Ileak"] / p["Ch"] * dt
        return sw, vc, dt

    @staticmethod
    def analyse(p: dict) -> dict:
        sw, vc, dt = Sh.trace(p)
        a = _cross(vc, dt, 0.1 * p["Vs"], True)
        b = _cross(vc, dt, 0.9 * p["Vs"], True)
        tacq = b[0] - a[0] if a and b else 0.0
        k1, k2 = int(7.0 / 10.0 * NS), int(9.5 / 10.0 * NS)
        droop = (vc[k1] - vc[k2]) / ((k2 - k1) * dt)
        return {"tacq": tacq, "tau": tacq / math.log(9.0), "droop": droop}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "tau_us": (p["Rsrc"] + p["Ron"]) * p["Ch"] * 1e6}

    @staticmethod
    def measure(p, cfg=None):
        return Sh.analyse(p)


def _sh_tau(p: dict) -> float:
    return (p["Rsrc"] + p["Ron"]) * p["Ch"]


# ================================================================================================== 7805 supply
class Reg(_Static):
    """Bridge rectifier (two diode drops V_f) and a reservoir capacitor C on a transformer secondary of V_sec rms at
    f = 50 Hz, feeding a 7805-type regulator that draws I_o + I_q. Over one half-period, from a crest, the capacitor
    voltage is max(V_m - I t / C, V_m |cos w t|), V_m = sqrt 2 V_sec - 2 V_f (sampled at NS points). The regulator gives
    V_nom + k_l (v_in - 10 V) - R_o I_o, or v_in - V_do when it drops out. The DC readings are the sample means; line
    regulation is dV_out/dV_in (the input's mean) for V_sec +- 1 V, load regulation -dV_out/dI_o for I_o +- 0.1 A."""

    PARAMS = {"Vsec": 15.0, "f": 50.0, "Cf": 2.2e-3, "Io": 0.5, "Iq": 0.005, "Vf": 0.85, "Vnom": 5.0, "kl": 1.7e-4,
              "Ro": 0.01, "Vdo": 2.0}
    VARS = ["t", "Vin", "Vout"]

    @staticmethod
    def run(p: dict, vsec: float, io: float) -> dict:
        vm = math.sqrt(2.0) * vsec - 2.0 * p["Vf"]
        w = 2.0 * PI * p["f"]
        th = 0.5 / p["f"]
        it = io + p["Iq"]
        si = so = 0.0
        vmin, vmax, omin, omax = 1e9, -1e9, 1e9, -1e9
        for i in range(NS):
            t = (i + 0.5) / NS * th
            vin = max(vm - it * t / p["Cf"], vm * abs(math.cos(w * t)))
            vo = min(p["Vnom"] + p["kl"] * (vin - 10.0) - p["Ro"] * io, vin - p["Vdo"])
            si += vin
            so += vo
            vmin, vmax = min(vmin, vin), max(vmax, vin)
            omin, omax = min(omin, vo), max(omax, vo)
        return {"Vin": si / NS, "Vout": so / NS, "Vmin": vmin, "rin": vmax - vmin, "rout": omax - omin}

    @staticmethod
    def view(s, p, cfg=None):
        r = Reg.run(p, p["Vsec"], p["Io"])
        return {"t": s.get("t", 0.0), "Vin": r["Vin"], "Vout": r["Vout"]}

    @staticmethod
    def measure(p, cfg=None):
        r = Reg.run(p, p["Vsec"], p["Io"])
        a, b = Reg.run(p, p["Vsec"] - 1.0, p["Io"]), Reg.run(p, p["Vsec"] + 1.0, p["Io"])
        c, d = Reg.run(p, p["Vsec"], p["Io"] - 0.1), Reg.run(p, p["Vsec"], p["Io"] + 0.1)
        r["line"] = (b["Vout"] - a["Vout"]) / (b["Vin"] - a["Vin"])
        r["Rout"] = (c["Vout"] - d["Vout"]) / 0.2
        return r


def _reg_line(p: dict) -> float:
    return p["kl"]


# ================================================================================================== PLL
class Pll(_Static):
    """565-type PLL in the averaged phase domain. Free-running VCO f_0 = 0.3/(R_1 C_1); the phase detector gives
    K_d sin(theta) (K_d = 1 V), the loop filter (3.6 kOhm internal x C_2, tau) gives v_c, and the VCO runs at
    f_0 + K_f v_c with K_f = 8 f_0/V (the lock range the 565 data sheet states, V = total supply):
        d theta/dt = 2 pi (f_in - f_0 - K_f v_c),   tau dv_c/dt = sin(theta) - v_c   (RK4, dt = 1/(40 K_f), 12 tau).
    The loop holds lock (tracking) when started at its locked state for a slightly nearer input; it CAPTURES when
    started free-running (v_c = 0). Each edge is found by bisection on the offset f_in - f_0."""

    PARAMS = {"R1": 6800.0, "C1": 1.0e-8, "C2": 1.0e-6, "V": 10.0, "fin": 4500.0, "mode": 0.0}
    VARS = ["t", "f0"]

    @staticmethod
    def f0(p: dict) -> float:
        return 0.3 / (p["R1"] * p["C1"])

    @staticmethod
    def run(p: dict, df: float, th: float, vc: float, n_tau: float) -> bool:
        kf = 8.0 * Pll.f0(p) / p["V"]
        tau = 3600.0 * p["C2"]
        dt = 1.0 / (40.0 * kf)
        n = int(n_tau * tau / dt)
        w = 2.0 * PI

        def d(th, vc):
            return (w * (df - kf * vc), (math.sin(th) - vc) / tau)
        tail = int(n * 0.6)
        tha = th
        for i in range(n):
            k1 = d(th, vc)
            k2 = d(th + 0.5 * dt * k1[0], vc + 0.5 * dt * k1[1])
            k3 = d(th + 0.5 * dt * k2[0], vc + 0.5 * dt * k2[1])
            k4 = d(th + dt * k3[0], vc + dt * k3[1])
            th += dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
            vc += dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
            if i == tail:
                tha = th
        return abs(th - tha) < 0.25 * PI

    @staticmethod
    def locked(p: dict, df: float, mode: int) -> bool:
        kf = 8.0 * Pll.f0(p) / p["V"]
        if mode == 0:
            s = (abs(df) - 0.002 * kf) / kf
            s = max(0.0, min(0.999, s)) * (1.0 if df >= 0 else -1.0)
            return Pll.run(p, df, math.asin(s), s, 12.0)
        return Pll.run(p, df, 0.0, 0.0, 60.0)

    @staticmethod
    def edge(p: dict, mode: int) -> float:
        kf = 8.0 * Pll.f0(p) / p["V"]
        lo, hi = 0.0, 1.5 * kf
        for _ in range(14):
            mid = 0.5 * (lo + hi)
            if Pll.locked(p, mid, mode):
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "f0": Pll.f0(p)}

    @staticmethod
    def measure(p, cfg=None):
        return {"f0": Pll.f0(p), "lock": Pll.edge(p, 0), "capture": Pll.edge(p, 1)}


def _pll_lock(p: dict) -> float:
    """Textbook (565 data sheet): the lock range on either side of f_0 is 8 f_0 / V."""
    return 8.0 * (0.3 / (p["R1"] * p["C1"])) / p["V"]


def _pll_capture(p: dict) -> float:
    """Textbook (Gayakwad, the 565): f_C = (1/2 pi) sqrt(2 pi f_L / tau), tau = 3.6 kOhm C_2."""
    fl = _pll_lock(p)
    return math.sqrt(2.0 * PI * fl / (3600.0 * p["C2"])) / (2.0 * PI)


# ================================================================================================== universal counter
class Count(_Static):
    """A universal counter counting edges. Frequency mode: the gate is open for T_g and the counter totals the input's
    rising edges, N = floor(f T_g + phi) - floor(phi) (phi = the input's phase, a fraction of a cycle, when the gate
    opens); it shows N/T_g. Period mode: the input's own edges open the gate for N_p periods and the counter totals the
    10 MHz time-base clock, M = floor(f_clk N_p / f + psi) - floor(psi); it shows M/(f_clk N_p)."""

    PARAMS = {"f": 1234.5678, "ph": 0.37, "ps": 0.61, "fclk": 1.0e7, "Tg": 1.0, "Np": 1.0}
    VARS = ["t", "f"]

    @staticmethod
    def freq(p: dict, tg: float) -> tuple[float, int]:
        n = math.floor(p["f"] * tg + p["ph"]) - math.floor(p["ph"])
        return n / tg, int(n)

    @staticmethod
    def period(p: dict, np_: float) -> tuple[float, int]:
        m = math.floor(p["fclk"] * np_ / p["f"] + p["ps"]) - math.floor(p["ps"])
        return m / (p["fclk"] * np_), int(m)

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "f": Count.freq(p, p["Tg"])[0]}

    @staticmethod
    def measure(p, cfg=None):
        ff, n = Count.freq(p, p["Tg"])
        tp, m = Count.period(p, p["Np"])
        return {"fF": ff, "N": float(n), "Tp": tp, "M": float(m), "f1": Count.freq(p, 1.0)[0]}


def _count_f(p: dict) -> float:
    return p["f"]


# ================================================================================================== distortion factor meter
class Dfm(_Static):
    """A generator's output: the fundamental V_1 at f_0 with harmonics h_n V_1 (n = 2 ... 5). The meter reads the total
    rms first (SET LEVEL), then the rms left after a tunable notch of quality Q centred on f_n,
        H(x) = (1 - x^2) / (1 - x^2 + j x/Q),   x = n f_0 / f_n,
    each harmonic passing with its own |H| and phase. The rms values are taken over two sampled cycles."""

    PARAMS = {"V1": 1.0, "h2": 0.03, "h3": 0.02, "h4": 0.005, "h5": 0.004, "f0": 100000.0, "Q": 10.0, "fn": 100000.0}
    VARS = ["t", "D_pct"]

    @staticmethod
    def rms(p: dict, fn: float, notch: bool) -> float:
        amp = [p["V1"], p["V1"] * p["h2"], p["V1"] * p["h3"], p["V1"] * p["h4"], p["V1"] * p["h5"]]
        mag, ph = [], []
        for n in range(1, 6):
            if notch:
                x = n * p["f0"] / fn
                hh = _cdiv((1.0 - x * x, 0.0), (1.0 - x * x, x / p["Q"]))
                mag.append(_cabs(hh))
                ph.append(math.atan2(hh[1], hh[0]))
            else:
                mag.append(1.0)
                ph.append(0.0)
        s = 0.0
        for i in range(NS):
            th = 4.0 * PI * (i + 0.5) / NS
            v = 0.0
            for k in range(5):
                v += amp[k] * mag[k] * math.sin((k + 1) * th + ph[k])
            s += v * v
        return math.sqrt(s / NS)

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "D_pct": 100.0 * Dfm.rms(p, p["fn"], True) / Dfm.rms(p, p["fn"], False)}

    @staticmethod
    def measure(p, cfg=None):
        tot = Dfm.rms(p, p["fn"], False)
        res = Dfm.rms(p, p["fn"], True)
        best = Dfm.rms(p, p["f0"], True)
        return {"Vtot": tot, "Vres": res, "D": res / tot, "Dbest": best / tot}


def _dfm_d(p: dict) -> float:
    """Textbook distortion factor: sqrt(sum of the harmonics' squares) / sqrt(fundamental^2 + that sum)."""
    hs = p["h2"] ** 2 + p["h3"] ** 2 + p["h4"] ** 2 + p["h5"] ** 2
    return math.sqrt(hs) / math.sqrt(1.0 + hs)


# ================================================================================================== thermostat
class Tstat(_Static):
    """An on-off thermostat in a water bath heated by P and losing heat to the room as hA (T - T_a). The dial is set to
    D; the thermostat's real set point is a + b D (its calibration) and it switches the heater off at set point + H/2
    and on at set point - H/2. Between switchings T relaxes exactly towards T_a + P/(hA) (heater on) or T_a (off), time
    constant C/(hA), in steps of 0.5 s; a switching inside a step is placed at its exact time on the exponential."""

    PARAMS = {"D": 50.0, "a": 1.5, "b": 0.97, "H": 3.0, "P": 500.0, "hA": 10.0, "Cth": 4186.0, "Ta": 25.0}
    VARS = ["t", "Tset"]
    DT = 0.5

    @staticmethod
    def run(p: dict) -> dict:
        ts = p["a"] + p["b"] * p["D"]
        ton, toff = ts - 0.5 * p["H"], ts + 0.5 * p["H"]
        tinf = p["Ta"] + p["P"] / p["hA"]
        tau = p["Cth"] / p["hA"]
        e = math.exp(-Tstat.DT / tau)
        t, temp, heat = 0.0, p["Ta"], True
        ev = []
        for _ in range(40000):
            tgt = tinf if heat else p["Ta"]
            nt = tgt + (temp - tgt) * e
            thr = toff if heat else ton
            if (heat and nt >= thr) or ((not heat) and nt <= thr):
                tc = -tau * math.log((thr - tgt) / (temp - tgt))
                ev.append((t + tc, thr, 0 if heat else 1))
                heat = not heat
                tgt = tinf if heat else p["Ta"]
                nt = tgt + (thr - tgt) * math.exp(-(Tstat.DT - tc) / tau)
            temp = nt
            t += Tstat.DT
            if len(ev) >= 5:
                break
        out = {"Ton": ton, "Toff": toff, "theat": 0.0, "tcool": 0.0, "ev": ev}
        if len(ev) >= 4:
            out["tcool"] = ev[1][0] - ev[0][0]
            out["theat"] = ev[2][0] - ev[1][0]
        return out

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Tset": p["a"] + p["b"] * p["D"]}

    @staticmethod
    def measure(p, cfg=None):
        r = Tstat.run(p)
        return {"Ton": r["Ton"], "Toff": r["Toff"], "theat": r["theat"], "tcool": r["tcool"]}


def _tstat_theat(p: dict) -> float:
    """Textbook: heating from T_on to T_off towards T_inf takes tau ln((T_inf - T_on)/(T_inf - T_off))."""
    ts = p["a"] + p["b"] * p["D"]
    ton, toff = ts - 0.5 * p["H"], ts + 0.5 * p["H"]
    tinf = p["Ta"] + p["P"] / p["hA"]
    return p["Cth"] / p["hA"] * math.log((tinf - ton) / (tinf - toff))


# ================================================================================================== cable noise pick-up
class Noise(_Static):
    """Capacitive (electric-field) pick-up from a nearby conductor at V_1, f into a receiving wire loaded by R and
    stray capacitance C_2g to ground (H. W. Ott's two-conductor model):
        V_N = j w R C_12 V_1 / (1 + j w R (C_12 + C_2g)).
    A grounded shield leaves only a fraction k of C_12 (the part the shield does not cover); a floating shield, or no
    shield, leaves all of it. The amplitude is read on the sampled trace."""

    PARAMS = {"V1": 10.0, "f": 10000.0, "R": 10000.0, "C12": 5.0e-12, "C2g": 1.0e-10, "k": 1.0, "sg": 1.0}
    VARS = ["t", "VN_mV"]

    @staticmethod
    def ceff(p: dict) -> float:
        return p["C12"] * (p["k"] if int(round(p["sg"])) == 1 else 1.0)

    @staticmethod
    def hv(p: dict):
        w = 2.0 * PI * p["f"]
        c = Noise.ceff(p)
        return _cdiv((0.0, w * p["R"] * c * p["V1"]), (1.0, w * p["R"] * (c + p["C2g"])))

    @staticmethod
    def wave(p: dict) -> tuple[list, list, float]:
        hh = Noise.hv(p)
        a, ph = _cabs(hh), math.atan2(hh[1], hh[0])
        dt = 3.0 / p["f"] / NS
        src, vn = [], []
        for i in range(NS):
            th = 2.0 * PI * p["f"] * i * dt
            src.append(p["V1"] * math.sin(th))
            vn.append(a * math.sin(th + ph))
        return src, vn, dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "VN_mV": _cabs(Noise.hv(p)) * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        _, vn, _ = Noise.wave(p)
        return {"VN": 0.5 * (max(vn) - min(vn)), "Ceff": Noise.ceff(p)}


def _noise_vn(p: dict) -> float:
    w = 2.0 * PI * p["f"]
    c = p["C12"] * (p["k"] if int(round(p["sg"])) == 1 else 1.0)
    return w * p["R"] * c * p["V1"] / math.sqrt(1.0 + (w * p["R"] * (c + p["C2g"])) ** 2)


# ================================================================================================== registry
KERNELS: dict[str, Any] = {
    "u8_diode": Diode, "u8_tunnel": Tunnel, "u8_bjt": Bjt, "u8_pp": PushPull, "u8_opa": Opa, "u8_diff": Diff,
    "u8_acomp": Acomp, "u8_filt": Filt, "u8_jfet": Jfet, "u8_dac": Dac, "u8_adc": Adc, "u8_sh": Sh, "u8_reg": Reg,
    "u8_pll": Pll, "u8_count": Count, "u8_dfm": Dfm, "u8_tstat": Tstat, "u8_noise": Noise,
}
FAMILY = {k: "circuit" for k in KERNELS}
FAMILY["u8_tstat"] = "thermo"
TEXTBOOK = {
    "u8_diode_vcut": _diode_vcut, "u8_diode_kb": _diode_kb, "u8_tunnel_ip": _tunnel_ip, "u8_bjt_hfe": _bjt_hfe,
    "u8_bjt_vth": _bjt_vth, "u8_pp_thd": _pp_thd, "u8_opa_gbw": _opa_gbw, "u8_diff_acm": _diff_acm,
    "u8_acomp_fd": _acomp_fd, "u8_acomp_x": _acomp_x, "u8_filt_fc": _filt_fc, "u8_jfet_amid": _jfet_amid,
    "u8_dac_v": _dac_v, "u8_adc_code": _adc_code, "u8_sh_tau": _sh_tau, "u8_reg_line": _reg_line,
    "u8_pll_lock": _pll_lock, "u8_pll_capture": _pll_capture, "u8_count_f": _count_f, "u8_dfm_d": _dfm_d,
    "u8_tstat_theat": _tstat_theat, "u8_noise_vn": _noise_vn,
}
CALCS: dict[str, dict] = {}
