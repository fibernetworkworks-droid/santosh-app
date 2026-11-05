"""Kernel pack `sn_elec`: the undergraduate SENSOR, INSTRUMENT, ANALOG and COMMUNICATION benches of
`syllabus/physics/ug.json` (chapters "Electronic instrumentation and sensors", "Analog electronics and devices" and
"Communication electronics and microwaves"). Its exact JavaScript twin is `app/static/prayog/packs/sn_elec.js`; the test
suite runs both on the same inputs and demands the same numbers, so the two files carry the same formulas step by step.

Every kernel is prefixed `sn_`. All of them are deterministic and in SI units: no wall clock, no hidden randomness.

Sensors (static physics, read on a meter):
  sn_lvdt     LVDT: secondary EMF against core displacement, read by a phase-sensitive detector on the sampled waveform
  sn_strain   cantilever + metal-foil strain gauge in a quarter / half / full Wheatstone bridge + instrumentation amp
  sn_capl     coaxial capacitive level probe
  sn_ultra    ultrasonic time of flight: the echo time is found by scanning the sampled echo for the first crossing
  sn_tsens    AD590 / LM35 / LM75 / Pt100 against a reference thermometer
  sn_photo    photodiode photocurrent against the irradiance of an LED at a distance
  sn_mload    loading of a divider by a meter's input resistance
  sn_mbw      the AC reading of a meter against frequency (single-pole roll-off), -3 dB point found by bisection
  sn_vac      rotary-pump pump-down, integrated with RK4

Waveform benches (read on a scope; every reading is found on the SAMPLED waveform, never from the formula):
  sn_scope    two-channel scope measurement: Vpp, mean, period, phase of an RC network
  sn_pulse    pulse through an RC and the scope's own bandwidth: rise, fall and delay times
  sn_shape    diode clipper and clamper
  sn_mv       555 astable, 555 monostable and UJT relaxation oscillator (capacitor ODE solved exactly between events)
  sn_ce       common-emitter amplifier, one or two RC-coupled stages: complex small-signal response
  sn_am       amplitude modulation (transmitter side)
  sn_fm       frequency modulation and a zero-crossing frequency discriminator
  sn_ant      dipole antenna pattern, peak field and half-power beamwidth
  sn_bias     fixed, collector-feedback and voltage-divider bias of a common-emitter transistor
  sn_opa      op-amp comparator (trip point, slew rate), integrator and differentiator on a scope
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
VT = 0.025852                    # thermal voltage at 300 K, the same constant the other packs use
EPS0 = 8.8541878128e-12          # F/m, CODATA 2018
QE = 1.602176634e-19             # C, exact
HP = 6.62607015e-34              # J s, exact
CL = 2.99792458e8                # m/s, exact
NW = 2400                        # samples on a scope trace


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _ols(xs: list, ys: list) -> float:
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(a * b for a, b in zip(xs, ys))
    sxx = sum(a * a for a in xs)
    den = n * sxx - sx * sx
    return 0.0 if den == 0 else (n * sxy - sx * sy) / den


def _cross(y: list, dt: float, level: float, rising: bool = True) -> list:
    """Times at which y crosses `level` (linear interpolation between samples), in the requested direction."""
    out = []
    for i in range(1, len(y)):
        a, b = y[i - 1] - level, y[i] - level
        if rising and a < 0 <= b and b != a:
            out.append((i - 1 + (0 - a) / (b - a)) * dt)
        elif (not rising) and a >= 0 > b:
            out.append((i - 1 + (0 - a) / (b - a)) * dt)
    return out


class _Static:
    """Shared plumbing: a kernel that holds nothing over time."""

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


# ================================================================================================== LVDT
class Lvdt(_Static):
    """Linear variable differential transformer. The primary carries V_p (rms) at f_ex; the two secondaries are wound in
    opposition, so the output is zero at the centre and grows with the core's displacement x, in phase with the primary
    for x > 0 and in antiphase for x < 0. Output rms  V_s = V_p S x / (1 + (x/x_s)^2): linear near the centre, rolling
    off beyond the linear range (x_s is set far outside it). A small quadrature residual V_q (rms) is left at the null,
    as in every real LVDT. The meter shows the output of a phase-sensitive detector, the mean of v(t) sign(sin w t),
    taken over the sampled waveform: it keeps the sign of x and ignores the quadrature residual."""

    PARAMS = {"x": 0.0, "Vp": 3.0, "fex": 2500.0, "S": 20.0, "xs": 0.05, "Vq": 0.0015, "xu": 0.0037}
    VARS = ["t", "x_mm", "Vout_mV", "Vpp_mV", "phase"]
    NS = 400

    @staticmethod
    def wave(p: dict) -> tuple[list, list]:
        n = Lvdt.NS
        vs = p["Vp"] * p["S"] * p["x"] / (1.0 + (p["x"] / p["xs"]) ** 2)
        a, q = math.sqrt(2.0) * vs, math.sqrt(2.0) * p["Vq"]
        tt, vv = [], []
        for i in range(n):
            ph = 2.0 * PI * 2.0 * (i + 0.5) / n           # two excitation cycles
            tt.append((i + 0.5) / n * 2.0 / p["fex"])
            vv.append(a * math.sin(ph) + q * math.cos(ph))
        return tt, vv

    @staticmethod
    def read(p: dict) -> tuple[float, float]:
        """(phase-sensitive detector output in volts, peak-to-peak in volts)."""
        tt, vv = Lvdt.wave(p)
        n = len(vv)
        acc = 0.0
        for i in range(n):
            ph = 2.0 * PI * 2.0 * (i + 0.5) / n
            acc += vv[i] * (1.0 if math.sin(ph) >= 0 else -1.0)
        return (acc / n) * PI / (2.0 * math.sqrt(2.0)), max(vv) - min(vv)

    @staticmethod
    def view(s, p, cfg=None):
        d, pp = Lvdt.read(p)
        return {"t": s.get("t", 0.0), "x_mm": p["x"] * 1000.0, "Vout_mV": d * 1000.0, "Vpp_mV": pp * 1000.0,
                "phase": 0.0 if p["x"] >= 0 else 180.0}

    @staticmethod
    def measure(p, cfg=None):
        d, pp = Lvdt.read(p)
        return {"Vout": d, "Vpp": pp}


def _lvdt_v(p: dict) -> float:
    """Textbook, linear range: V_s = V_p S x."""
    return p["Vp"] * p["S"] * p["x"]


# ================================================================================================== strain gauge
class Strain(_Static):
    """A steel (or other) cantilever with a load m g at distance L from the gauge, strain epsilon = 6 m g L/(E b h^2).
    The gauge changes by dR/R = GF epsilon. The Wheatstone bridge (excitation V_s) has `nb` active arms:
      nb 1  quarter bridge, one gauge:                  V = V_s d / (2 (2 + d))
      nb 2  half bridge, tension + compression gauges:   V = V_s d / 2
      nb 4  full bridge, four gauges:                    V = V_s d
    with d = dR/R, exact. An instrumentation amplifier of gain G follows, with its offset V_off."""

    PARAMS = {"m": 0.5, "L": 0.2, "b": 0.025, "h": 0.002, "E": 200.0e9, "GF": 2.0, "Vs": 5.0, "Rg": 350.0, "nb": 1.0,
              "G": 100.0, "Voff": 0.0032, "g": 9.80665, "mu": 0.773}
    VARS = ["t", "eps_ue", "Vb_mV", "Vout_V", "dR"]

    @staticmethod
    def strain(p: dict) -> float:
        return 6.0 * p["m"] * p["g"] * p["L"] / (p["E"] * p["b"] * p["h"] * p["h"])

    @staticmethod
    def bridge(p: dict) -> float:
        d = p["GF"] * Strain.strain(p)
        k = int(round(p["nb"]))
        if k == 1:
            return p["Vs"] * d / (2.0 * (2.0 + d))
        if k == 2:
            return p["Vs"] * d / 2.0
        return p["Vs"] * d

    @staticmethod
    def view(s, p, cfg=None):
        e = Strain.strain(p)
        vb = Strain.bridge(p)
        return {"t": s.get("t", 0.0), "eps_ue": e * 1e6, "Vb_mV": vb * 1000.0, "Vout_V": p["G"] * vb + p["Voff"],
                "dR": p["Rg"] * p["GF"] * e}

    @staticmethod
    def measure(p, cfg=None):
        e = Strain.strain(p)
        vb = Strain.bridge(p)
        return {"strain": e, "Vb": vb, "Vout": p["G"] * vb + p["Voff"]}


def _strain_vb(p: dict) -> float:
    """Textbook: V_b = V_s n GF epsilon / 4 (the small-strain form for n active arms)."""
    return p["Vs"] * round(p["nb"]) * p["GF"] * Strain.strain(p) / 4.0


# ================================================================================================== capacitive level
class Capl(_Static):
    """A coaxial probe of length H (inner radius a, tube radius b) standing in a tank. The liquid, of relative
    permittivity e_r, fills the gap up to level h: the dry part and the wet part are capacitors in parallel,
        C = 2 pi eps0 (H + (e_r - 1) h) / ln(b/a) + C_stray
    where C_stray is the cable and the meter's lead capacitance."""

    PARAMS = {"h": 0.1, "H": 0.3, "a": 0.003, "b": 0.010, "er": 80.2, "Cs": 12.0e-12, "hu": 0.137}
    VARS = ["t", "h_cm", "C_pF"]

    @staticmethod
    def cap(p: dict, h: float) -> float:
        return 2.0 * PI * EPS0 * (p["H"] + (p["er"] - 1.0) * h) / math.log(p["b"] / p["a"]) + p["Cs"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "h_cm": p["h"] * 100.0, "C_pF": Capl.cap(p, p["h"]) * 1e12}

    @staticmethod
    def measure(p, cfg=None):
        d = 0.01
        return {"C": Capl.cap(p, p["h"]), "dCdh": (Capl.cap(p, p["h"] + d) - Capl.cap(p, p["h"])) / d}


def _capl_slope(p: dict) -> float:
    return 2.0 * PI * EPS0 * (p["er"] - 1.0) / math.log(p["b"] / p["a"])


# ================================================================================================== ultrasonic ranging
class Ultra(_Static):
    """Ultrasonic time of flight. A burst of 8 cycles at f leaves the transmitter t0 after the trigger (electronics
    latency), travels to the target at distance d and back at the speed of sound c = 331.3 sqrt(1 + T/273.15), and
    arrives with amplitude A. The receiver's comparator fires at the first sample whose magnitude exceeds 20 % of the
    burst peak. The echo time is found by SCANNING the received waveform: a coarse pass in 5 us steps to the first
    crossing, then a fine pass in 0.1 us steps."""

    PARAMS = {"d": 0.5, "T": 20.0, "t0": 1.8e-4, "f": 40000.0, "A": 1.0, "dx": 0.737}
    VARS = ["t", "d_cm", "te_ms", "c"]

    @staticmethod
    def speed(T: float) -> float:
        return 331.3 * math.sqrt(1.0 + T / 273.15)

    @staticmethod
    def signal(p: dict, t: float) -> float:
        ta = 2.0 * p["d"] / Ultra.speed(p["T"]) + p["t0"]
        if t < ta or t >= ta + 8.0 / p["f"]:
            return 0.0
        return p["A"] * math.sin(2.0 * PI * p["f"] * (t - ta))

    @staticmethod
    def echo_time(p: dict) -> float:
        thr = 0.2 * p["A"]
        tmax = 2.0 * 5.0 / Ultra.speed(p["T"]) + p["t0"] + 1.0e-3
        k = 0
        step = 5.0e-6
        while k * step < tmax:
            if abs(Ultra.signal(p, k * step)) > thr:
                break
            k += 1
        lo = max(0.0, (k - 1) * step)
        j = 0
        while j < 51:
            if abs(Ultra.signal(p, lo + j * 1.0e-7)) > thr:
                return lo + j * 1.0e-7
            j += 1
        return lo + 50 * 1.0e-7

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "d_cm": p["d"] * 100.0, "te_ms": Ultra.echo_time(p) * 1000.0,
                "c": Ultra.speed(p["T"])}

    @staticmethod
    def measure(p, cfg=None):
        te = Ultra.echo_time(p)
        return {"te": te, "d_est": Ultra.speed(p["T"]) * (te - p["t0"]) / 2.0}


def _ultra_d(p: dict) -> float:
    return p["d"]


# ================================================================================================== temperature sensors
class Tsens(_Static):
    """Four temperature sensors against a reference thermometer in a stirred bath.
      dev 0  AD590 current source:  I = (T + 273.15) uA per kelvin, read as microamperes
      dev 1  LM35:                  V = 10 mV per degree Celsius, read in millivolts
      dev 2  LM75B digital sensor:  11-bit code, 0.125 degC per LSB, read as degC
      dev 3  Pt100 (IEC 60751):     R = R0 (1 + A t + B t^2), A = 3.9083e-3, B = -5.775e-7, read in ohms
    Each specimen has a small gain error `ge` (a fraction) and the bath a small offset `off` (degC) between the sensor
    and the reference thermometer; both are simulation settings inside the datasheet limits."""

    PARAMS = {"dev": 0.0, "T": 25.0, "ge": 0.0, "off": 0.0, "R0": 100.0, "Tu": 47.3}
    VARS = ["t", "T", "reading"]
    A = 3.9083e-3
    B = -5.775e-7

    @staticmethod
    def raw(p: dict, T: float) -> float:
        te = T + p["off"]
        k = int(round(p["dev"]))
        if k == 0:
            return (te + 273.15) * (1.0 + p["ge"])
        if k == 1:
            return 10.0 * te * (1.0 + p["ge"])
        if k == 2:
            return te * (1.0 + p["ge"])
        return p["R0"] * (1.0 + Tsens.A * te + Tsens.B * te * te) * (1.0 + p["ge"])

    @staticmethod
    def reading(p: dict, T: float) -> float:
        v = Tsens.raw(p, T)
        if int(round(p["dev"])) == 2:
            return math.floor(v / 0.125 + 0.5) * 0.125
        return v

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "T": p["T"], "reading": Tsens.reading(p, p["T"])}

    @staticmethod
    def measure(p, cfg=None):
        return {"reading": Tsens.reading(p, p["T"]), "slope": Tsens.raw(p, p["T"] + 0.5) - Tsens.raw(p, p["T"] - 0.5)}


def _tsens_slope(p: dict) -> float:
    k = int(round(p["dev"]))
    g = 1.0 + p["ge"]
    if k == 0:
        return g
    if k == 1:
        return 10.0 * g
    if k == 2:
        return g
    return p["R0"] * (Tsens.A + 2.0 * Tsens.B * (p["T"] + p["off"])) * g


# ================================================================================================== photodiode
class Photo(_Static):
    """A photodiode under an LED of radiant intensity I_e at distance d: irradiance E = I_e / d^2, optical power on the
    chip P = E A, photocurrent I = R P + I_dark, with the responsivity R = eta lambda q / (h c) of an ideal photodiode of
    quantum efficiency eta."""

    PARAMS = {"d": 0.10, "Ie": 0.13, "lam": 940.0e-9, "eta": 0.8, "A": 7.5e-6, "Id": 2.0e-9}
    VARS = ["t", "d_cm", "E", "P_uW", "I_uA"]

    @staticmethod
    def resp(p: dict) -> float:
        return p["eta"] * p["lam"] * QE / (HP * CL)

    @staticmethod
    def view(s, p, cfg=None):
        e = p["Ie"] / (p["d"] * p["d"])
        pw = e * p["A"]
        return {"t": s.get("t", 0.0), "d_cm": p["d"] * 100.0, "E": e, "P_uW": pw * 1e6,
                "I_uA": (Photo.resp(p) * pw + p["Id"]) * 1e6}

    @staticmethod
    def measure(p, cfg=None):
        def cur(d):
            return Photo.resp(p) * (p["Ie"] / (d * d)) * p["A"] + p["Id"]
        d1, d2 = p["d"], p["d"] * 1.5
        pw = lambda d: (p["Ie"] / (d * d)) * p["A"]  # noqa: E731
        return {"I": cur(d1), "R": (cur(d1) - cur(d2)) / (pw(d1) - pw(d2))}


def _photo_r(p: dict) -> float:
    return p["eta"] * p["lam"] * QE / (HP * CL)


# ================================================================================================== meter loading
class Mload(_Static):
    """A source Vs behind R1, loading R2 to ground; a meter of input resistance Rm across R2."""

    PARAMS = {"Vs": 5.0, "R1": 1.0e6, "R2": 1.0e6, "Rm": 1.0e7}
    VARS = ["t", "Vm", "Vt", "err_pct"]

    @staticmethod
    def volts(p: dict) -> tuple[float, float]:
        rp = p["R2"] * p["Rm"] / (p["R2"] + p["Rm"])
        return p["Vs"] * rp / (p["R1"] + rp), p["Vs"] * p["R2"] / (p["R1"] + p["R2"])

    @staticmethod
    def view(s, p, cfg=None):
        vm, vt = Mload.volts(p)
        return {"t": s.get("t", 0.0), "Vm": vm, "Vt": vt, "err_pct": 100.0 * (vm - vt) / vt}

    @staticmethod
    def measure(p, cfg=None):
        vm, vt = Mload.volts(p)
        return {"Vm": vm, "Vt": vt, "err": 100.0 * (vm - vt) / vt}


def _mload_err(p: dict) -> float:
    rth = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
    return -100.0 * rth / (rth + p["Rm"])


# ================================================================================================== meter bandwidth
class Mbw(_Static):
    """An AC meter's reading of a constant input V against frequency, V / sqrt(1 + (f/fc)^2). The -3 dB frequency is
    found by bisection on the response itself (reading = V/sqrt 2), 80 steps over 1 Hz ... 1 GHz."""

    PARAMS = {"f": 1000.0, "V": 1.0, "fc": 20000.0}
    VARS = ["t", "f_kHz", "reading", "err_pct"]

    @staticmethod
    def reading(p: dict, f: float) -> float:
        return p["V"] / math.sqrt(1.0 + (f / p["fc"]) ** 2)

    @staticmethod
    def view(s, p, cfg=None):
        r = Mbw.reading(p, p["f"])
        return {"t": s.get("t", 0.0), "f_kHz": p["f"] / 1000.0, "reading": r, "err_pct": 100.0 * (r - p["V"]) / p["V"]}

    @staticmethod
    def measure(p, cfg=None):
        lo, hi = 1.0, 1.0e9
        tgt = p["V"] / math.sqrt(2.0)
        for _ in range(80):
            mid = math.sqrt(lo * hi)
            if Mbw.reading(p, mid) > tgt:
                lo = mid
            else:
                hi = mid
        return {"f3": math.sqrt(lo * hi), "reading": Mbw.reading(p, p["f"])}


def _mbw_f3(p: dict) -> float:
    return p["fc"]


# ================================================================================================== rotary pump
class Vac(_Static):
    """Pump-down of a chamber of volume V by a pump of speed S to an ultimate pressure P_u:
    dP/dt = -(S/V)(P - P_u), integrated with RK4 in 10 ms steps. Pressure in millibar, speed in m^3/s."""

    PARAMS = {"t": 0.0, "P0": 1013.25, "Pu": 0.05, "Vch": 0.02, "S": 0.00167}
    VARS = ["t", "P"]

    @staticmethod
    def pressure(p: dict, t: float) -> float:
        k = p["S"] / p["Vch"]
        P = p["P0"]
        h = 0.01
        n = int(t / h + 0.5)
        f = lambda x: -k * (x - p["Pu"])  # noqa: E731
        for _ in range(n):
            k1 = f(P)
            k2 = f(P + 0.5 * h * k1)
            k3 = f(P + 0.5 * h * k2)
            k4 = f(P + h * k3)
            P += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        return P

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "P": Vac.pressure(p, p["t"])}

    @staticmethod
    def measure(p, cfg=None):
        return {"P": Vac.pressure(p, p["t"])}


def _vac_p(p: dict) -> float:
    return p["Pu"] + (p["P0"] - p["Pu"]) * math.exp(-p["S"] * p["t"] / p["Vch"])


# ================================================================================================== WAVEFORM BENCHES
# ================================================================================================== scope measurement
class Scope(_Static):
    """The scope-measurement bench. Channel 1 shows a sine of peak A on a DC level V_dc; channel 2 shows the same signal
    after an RC low-pass (R, C): amplitude A/sqrt(1 + x^2), lag atan(x), x = 2 pi f R C. The trace is NW samples
    over `n` whole periods; the period is found from successive rising crossings of the channel's own mean level, the
    peak-to-peak value from the largest and smallest sample, and the phase from the delay between the two channels'
    crossings as a fraction of the period."""

    PARAMS = {"f": 1000.0, "A": 2.0, "Vdc": 0.5, "R": 10000.0, "C": 1.0e-8, "n": 4.0}
    VARS = ["t", "T_ms", "Vpp1", "Vpp2", "phase"]

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list]:
        n = int(round(p["n"]))
        span = n / p["f"]
        dt = span / NW
        x = 2.0 * PI * p["f"] * p["R"] * p["C"]
        g = 1.0 / math.sqrt(1.0 + x * x)
        ph = math.atan(x)
        a, b = [], []
        for i in range(NW):
            wt = 2.0 * PI * p["f"] * i * dt
            a.append(p["Vdc"] + p["A"] * math.sin(wt))
            b.append(p["Vdc"] + p["A"] * g * math.sin(wt - ph))
        return dt, a, b

    @staticmethod
    def analyse(p: dict) -> dict:
        dt, a, b = Scope.trace(p)
        ma = sum(a) / len(a)
        mb = sum(b) / len(b)
        ca = _cross(a, dt, ma)
        cb = _cross(b, dt, mb)
        T = (ca[-1] - ca[0]) / (len(ca) - 1)
        lag = 0.0
        for t in cb:
            if t >= ca[0] - 1e-12:
                lag = t - ca[0]
                break
        if lag >= T:
            lag -= T
        return {"T": T, "f": 1.0 / T, "Vpp1": max(a) - min(a), "Vdc1": ma, "Vpp2": max(b) - min(b), "phase": lag / T * 360.0}

    @staticmethod
    def view(s, p, cfg=None):
        m = Scope.analyse(p)
        return {"t": s.get("t", 0.0), "T_ms": m["T"] * 1000.0, "Vpp1": m["Vpp1"], "Vpp2": m["Vpp2"], "phase": m["phase"]}

    @staticmethod
    def measure(p, cfg=None):
        return Scope.analyse(p)


def _scope_phase(p: dict) -> float:
    return math.degrees(math.atan(2.0 * PI * p["f"] * p["R"] * p["C"]))


# ================================================================================================== pulse timing
def _ramp_stage(y: float, u0: float, r: float, dt: float, tau: float) -> float:
    """Exact first-order response  tau y' = u - y  to the ramp u = u0 + r t, over dt."""
    e = math.exp(-dt / tau)
    return u0 + r * dt - r * tau + (y - u0 + r * tau) * e


def _ramp_cascade(y1: float, y2: float, u0: float, r: float, dt: float, t1: float, t2: float) -> tuple[float, float]:
    """Exact response of two first-order stages in cascade (time constants t1 then t2) to the ramp u = u0 + r t."""
    if abs(t1 - t2) < 1e-6 * t1:
        t2 = t1 * (1.0 + 1e-6)
    alpha = u0 - r * t1
    beta = y1 - alpha
    e1 = math.exp(-dt / t1)
    n1 = alpha + r * dt + beta * e1
    k = 1.0 / (1.0 - t2 / t1)
    gamma = y2 - (alpha - r * t2 + beta * k)
    n2 = alpha + r * (dt - t2) + beta * k * e1 + gamma * math.exp(-dt / t2)
    return n1, n2


class Pulse(_Static):
    """A pulse through an RC low-pass, seen on a scope of bandwidth BW. The scope is a first-order channel of time
    constant 1/(2 pi BW) (so its own 10-90 % rise time is 0.35/BW), the generator's edge is a ramp of duration t_g, and
    both channels are solved EXACTLY between the corners of the input (the ramps and the sample instants). Channel 1 is
    the generator, channel 2 the RC output. Rise and fall times are the 10-90 % intervals, the delay is the interval
    between the 50 % points of the two channels, all found on the sampled traces."""

    PARAMS = {"R": 10000.0, "C": 1.0e-9, "tg": 5.0e-9, "BW": 1.0e8, "Vh": 5.0}
    VARS = ["t", "tr_us", "tf_us", "td_us"]

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list]:
        tau = p["R"] * p["C"]
        ts = 1.0 / (2.0 * PI * p["BW"])
        tt = tau + ts + p["tg"]
        t_on, width, span = 2.0 * tt, 14.0 * tt, 30.0 * tt
        dt0 = span / NW
        tg, vh = p["tg"], p["Vh"]
        corners = sorted([t_on, t_on + tg, t_on + width, t_on + width + tg])

        def u_at(t):
            if t <= corners[0]:
                return 0.0
            if t < corners[1]:
                return vh * (t - corners[0]) / tg
            if t <= corners[2]:
                return vh
            if t < corners[3]:
                return vh * (1.0 - (t - corners[2]) / tg)
            return 0.0

        ya = yb = yc = 0.0
        a, b = [], []
        t = 0.0
        ci = 0
        for i in range(NW):
            tend = (i + 1) * dt0
            while t < tend - 1e-30:
                nxt = tend
                while ci < len(corners) and corners[ci] <= t + 1e-30:
                    ci += 1
                if ci < len(corners) and corners[ci] < nxt:
                    nxt = corners[ci]
                h = nxt - t
                if h <= 0:
                    break
                r = (u_at(t + 0.75 * h) - u_at(t + 0.25 * h)) / (0.5 * h)
                u0 = u_at(t + 0.5 * h) - r * 0.5 * h
                ya = _ramp_stage(ya, u0, r, h, ts)
                yb, yc = _ramp_cascade(yb, yc, u0, r, h, tau, ts)
                t = nxt
            a.append(ya)
            b.append(yc)
        return dt0, a, b

    @staticmethod
    def analyse(p: dict) -> dict:
        dt, a, b = Pulse.trace(p)
        top = max(b)
        r10 = _cross(b, dt, 0.1 * top, True)
        r90 = _cross(b, dt, 0.9 * top, True)
        f90 = _cross(b, dt, 0.9 * top, False)
        f10 = _cross(b, dt, 0.1 * top, False)
        r50a = _cross(a, dt, 0.5 * max(a), True)
        r50b = _cross(b, dt, 0.5 * top, True)
        return {"tr": r90[0] - r10[0], "tf": f10[0] - f90[0], "td": r50b[0] - r50a[0], "top": top}

    @staticmethod
    def view(s, p, cfg=None):
        m = Pulse.analyse(p)
        return {"t": s.get("t", 0.0), "tr_us": m["tr"] * 1e6, "tf_us": m["tf"] * 1e6, "td_us": m["td"] * 1e6}

    @staticmethod
    def measure(p, cfg=None):
        return Pulse.analyse(p)


def _pulse_tr(p: dict) -> float:
    return math.log(9.0) * p["R"] * p["C"]


# ================================================================================================== clipper / clamper
class Shape(_Static):
    """A diode clipper or clamper with a piecewise-linear diode (forward drop V_f, slope resistance r_d) and a bias
    source V_b. Input: a sine of peak V_p. `mode`:
      0 positive clipper   series R, diode to the bias:  the top is cut at V_b + V_f
      1 negative clipper   the bottom is cut at V_b - V_f
      2 positive clamper   series C, diode, load R_L:    the bottom is pushed to V_b - V_f
      3 negative clamper   the top is pushed to V_b + V_f
    The clampers are stepped (backward Euler, 200 steps a cycle) for 40 cycles so the capacitor has settled; the last
    two cycles are the trace."""

    PARAMS = {"mode": 2.0, "Vp": 5.0, "f": 1000.0, "R": 10000.0, "C": 1.0e-6, "RL": 10000000.0, "Vb": 0.0, "Vf": 0.65, "rd": 5.0}
    VARS = ["t", "Vmax", "Vmin", "Vpp"]
    SPC = 200

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list]:
        mode = int(round(p["mode"]))
        spc = Shape.SPC
        dt = 1.0 / (p["f"] * spc)
        cyc = 40 if mode >= 2 else 4
        vin, vout = [], []
        vo = 0.0
        vi_prev = 0.0
        c_dt = p["C"] / dt
        for k in range(cyc * spc + 1):
            vi = p["Vp"] * math.sin(2.0 * PI * p["f"] * k * dt)
            if mode == 0:
                lim = p["Vb"] + p["Vf"]
                vo = vi if vi <= lim else lim + (vi - lim) * p["rd"] / (p["R"] + p["rd"])
            elif mode == 1:
                lim = p["Vb"] - p["Vf"]
                vo = vi if vi >= lim else lim + (vi - lim) * p["rd"] / (p["R"] + p["rd"])
            elif k > 0:
                src = c_dt * (vi - vi_prev + vo)
                g = c_dt + 1.0 / p["RL"]
                v = src / g
                if mode == 2:
                    if v < p["Vb"] - p["Vf"]:
                        v = (src + (p["Vb"] - p["Vf"]) / p["rd"]) / (g + 1.0 / p["rd"])
                else:
                    if v > p["Vb"] + p["Vf"]:
                        v = (src + (p["Vb"] + p["Vf"]) / p["rd"]) / (g + 1.0 / p["rd"])
                vo = v
            vi_prev = vi
            if k > (cyc - 2) * spc:
                vin.append(vi)
                vout.append(vo)
        return dt, vin, vout

    @staticmethod
    def levels(p: dict) -> dict:
        dt, vin, vout = Shape.trace(p)
        mode = int(round(p["mode"]))
        hi, lo = max(vout), min(vout)
        return {"Vmax": hi, "Vmin": lo, "Vpp": hi - lo, "Vdc": sum(vout) / len(vout),
                "Vlvl": hi if mode in (0, 3) else lo}

    @staticmethod
    def view(s, p, cfg=None):
        m = Shape.levels(p)
        return {"t": s.get("t", 0.0), "Vmax": m["Vmax"], "Vmin": m["Vmin"], "Vpp": m["Vpp"]}

    @staticmethod
    def measure(p, cfg=None):
        return Shape.levels(p)


def _shape_lvl(p: dict) -> float:
    mode = int(round(p["mode"]))
    if mode in (0, 3):
        return p["Vb"] + p["Vf"]
    return p["Vb"] - p["Vf"]


# ================================================================================================== 555 / UJT
class Mv(_Static):
    """Timing circuits whose capacitor voltage is solved exactly between comparator events.
      kind 0  555 astable:   C charges to 2/3 V_cc through R1 + R2, then discharges through R2 to 1/3 V_cc
      kind 1  555 monostable: a trigger (falling input) starts the output; C charges through R1 to 2/3 V_cc, ends it
      kind 2  UJT relaxation oscillator: C charges through R1 toward V_cc until V_p = eta V_cc + V_d, then drops to V_v
      kind 3  transistor astable multivibrator (V_BE and V_CE(sat) taken as zero): each base charges from -V_cc toward +V_cc
              through its resistor (R1 then R2, one capacitor C) until it reaches 0 V, then the other transistor turns off
    The output is the average of the logic level over each sample interval, so an edge falls between two samples as a
    fraction exactly as a real scope's finite bandwidth would draw it, and the edge time is recovered by interpolation."""

    PARAMS = {"kind": 0.0, "R1": 1000.0, "R2": 10000.0, "C": 1.0e-7, "Vcc": 9.0, "eta": 0.65, "Vd": 0.5, "Vv": 1.0}
    VARS = ["t", "f", "width", "duty"]

    @staticmethod
    def span(p: dict) -> float:
        k = int(round(p["kind"]))
        if k == 0:
            return 4.4 * (p["R1"] + 2.0 * p["R2"]) * p["C"]
        if k == 1:
            return 8.0 * p["R1"] * p["C"]
        if k == 3:
            return 8.5 * (p["R1"] + p["R2"]) * p["C"]
        return 5.5 * p["R1"] * p["C"]

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list, list]:
        k = int(round(p["kind"]))
        span = Mv.span(p)
        dt0 = span / NW
        vcc = p["Vcc"]
        vc, hi = (-vcc if k == 3 else 0.0), (k in (0, 3))
        vcs, vos, vts = [], [], []
        tc = p["R1"] * p["C"]
        trig = [0.5 * tc, 4.5 * tc, 8.5 * tc]
        tw = 0.05 * tc
        ti = 0
        t = 0.0
        for i in range(NW):
            tend = (i + 1) * dt0
            high_t = 0.0
            while t < tend:
                rem = tend - t
                if k == 0:
                    if hi:
                        tau, thr, tgt = (p["R1"] + p["R2"]) * p["C"], 2.0 * vcc / 3.0, vcc
                        tcx = tau * math.log((tgt - vc) / (tgt - thr)) if vc < thr else 0.0
                    else:
                        tau, thr, tgt = p["R2"] * p["C"], vcc / 3.0, 0.0
                        tcx = tau * math.log(vc / thr) if vc > thr else 0.0
                    if tcx <= rem:
                        vc = thr
                        if hi:
                            high_t += tcx
                        t += tcx
                        hi = not hi
                    else:
                        vc = tgt + (vc - tgt) * math.exp(-rem / tau)
                        if hi:
                            high_t += rem
                        t = tend
                elif k == 1:
                    nxt = trig[ti] if ti < len(trig) else 1e30
                    if hi and nxt <= t:
                        ti += 1
                        nxt = trig[ti] if ti < len(trig) else 1e30
                    if hi:
                        tau, thr = p["R1"] * p["C"], 2.0 * vcc / 3.0
                        tcx = tau * math.log((vcc - vc) / (vcc - thr))
                        if tcx <= rem:
                            high_t += tcx
                            t += tcx
                            hi = False
                            vc = 0.0
                        else:
                            vc = vcc + (vc - vcc) * math.exp(-rem / tau)
                            high_t += rem
                            t = tend
                    else:
                        if nxt <= tend:
                            t = max(t, nxt)
                            hi = True
                            ti += 1
                        else:
                            t = tend
                elif k == 3:
                    tau = (p["R1"] if hi else p["R2"]) * p["C"]
                    tcx = tau * math.log((vcc - vc) / vcc)
                    if tcx <= rem:
                        if hi:
                            high_t += tcx
                        t += tcx
                        vc = -vcc
                        hi = not hi
                    else:
                        vc = vcc + (vc - vcc) * math.exp(-rem / tau)
                        if hi:
                            high_t += rem
                        t = tend
                else:
                    tau, tgt = p["R1"] * p["C"], vcc
                    thr = p["eta"] * vcc + p["Vd"]
                    tcx = tau * math.log((tgt - vc) / (tgt - thr)) if vc < thr else 0.0
                    if tcx <= rem:
                        t += tcx
                        vc = p["Vv"]
                    else:
                        vc = tgt + (vc - tgt) * math.exp(-rem / tau)
                        t = tend
            vcs.append(vc)
            vos.append(vcc * high_t / dt0 if k != 2 else 0.0)
            tt = (i + 0.5) * dt0
            low = 0.0
            for q in trig:
                if q <= tt < q + tw:
                    low = 1.0
            vts.append(vcc * (1.0 - low))
        return dt0, vcs, vos, vts

    @staticmethod
    def analyse(p: dict) -> dict:
        k = int(round(p["kind"]))
        dt, vc, vo, vt = Mv.trace(p)
        out = {"f": 0.0, "T": 0.0, "width": 0.0, "duty": 0.0, "Thigh": 0.0, "Tlow": 0.0, "main": 0.0}
        if k == 0 or k == 3:
            lvl = 0.5 * p["Vcc"]
            r = _cross(vo, dt, lvl, True)
            fl = _cross(vo, dt, lvl, False)
            T = (r[-1] - r[0]) / (len(r) - 1)
            lows = []
            for q in r:
                prev = [x for x in fl if x < q]
                if prev:
                    lows.append(q - prev[-1])
            tl = sum(lows) / len(lows)
            out.update({"T": T, "f": 1.0 / T, "Tlow": tl, "Thigh": T - tl, "duty": (T - tl) / T, "main": 1.0 / T})
        elif k == 1:
            lvl = 0.5 * p["Vcc"]
            r = _cross(vo, dt, lvl, True)
            fl = _cross(vo, dt, lvl, False)
            w = fl[0] - r[0]
            out.update({"width": w, "main": w})
        else:
            lvl = 0.5 * (max(vc) + min(vc))
            r = _cross(vc, dt, lvl, True)
            use = r[1:] if len(r) >= 3 else r
            T = (use[-1] - use[0]) / (len(use) - 1)
            out.update({"T": T, "f": 1.0 / T, "main": 1.0 / T})
        return out

    @staticmethod
    def view(s, p, cfg=None):
        m = Mv.analyse(p)
        return {"t": s.get("t", 0.0), "f": m["f"], "width": m["width"], "duty": m["duty"]}

    @staticmethod
    def measure(p, cfg=None):
        return Mv.analyse(p)


def _mv_main(p: dict) -> float:
    k = int(round(p["kind"]))
    if k == 0:
        return 1.44 / ((p["R1"] + 2.0 * p["R2"]) * p["C"])
    if k == 1:
        return 1.1 * p["R1"] * p["C"]
    if k == 3:
        return 1.0 / (0.693 * (p["R1"] + p["R2"]) * p["C"])
    thr = p["eta"] * p["Vcc"] + p["Vd"]
    return 1.0 / (p["R1"] * p["C"] * math.log((p["Vcc"] - p["Vv"]) / (p["Vcc"] - thr)))


# ================================================================================================== CE amplifier
def _c_mul(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def _c_div(a, b):
    d = b[0] * b[0] + b[1] * b[1]
    return ((a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d)


def _c_add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _c_par(a, b):
    return _c_div(_c_mul(a, b), _c_add(a, b))


class Ce(_Static):
    """Common-emitter amplifier, voltage-divider bias, one or two RC-coupled stages. DC: with a constant V_BE,
        I_C = (V_th - V_BE) / (R_th/beta + R_E (beta + 1)/beta).
    Small signal: g_m = I_C/V_T, r_pi = beta/g_m, C_pi = g_m/(2 pi f_T) - C_mu. Each stage (complex arithmetic, s = j w):
        Z_e = R_E / (1 + s R_E C_E),   Z_b = r_pi + (beta + 1) Z_e,   Z_in = R_B || Z_b      (R_B = R1 || R2)
        v_b/v_s = Z_in / (R_s + 1/(s C_in) + Z_in),   i_c = beta v_b/Z_b,
        a high-frequency pole at 1/(R_th,in C_m), C_m = C_pi + C_mu (1 + g_m R_L'),  R_th,in = R_s || R_B || r_pi.
    The last stage drives R_L through C_out; a first stage of two drives the second through C_in (its source resistance
    is R_C and its load is the second stage's mid-band input resistance R_B || r_pi). The mid-band gain, the lower and
    upper -3 dB frequencies are found by SCANNING the response over 1 Hz ... 10 GHz, 100 points a decade."""

    PARAMS = {"Vcc": 12.0, "R1": 47000.0, "R2": 10000.0, "Rc": 2200.0, "Re": 680.0, "RL": 10000.0, "Rs": 50.0,
              "Cin": 1.0e-6, "CE": 220.0e-6, "Cout": 1.0e-6, "beta": 200.0, "Vbe": 0.65, "fT": 3.0e8,
              "Cmu": 4.5e-12, "stages": 1.0, "f": 10000.0, "fmid": 10000.0}
    VARS = ["t", "Ic_mA", "Vce", "gm_mS"]

    @staticmethod
    def bias(p: dict) -> tuple[float, float]:
        vth = p["Vcc"] * p["R2"] / (p["R1"] + p["R2"])
        rth = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
        b = p["beta"]
        ic = (vth - p["Vbe"]) / (rth / b + p["Re"] * (b + 1.0) / b)
        return ic, p["Vcc"] - ic * p["Rc"] - ic * (b + 1.0) / b * p["Re"]

    @staticmethod
    def stage(p: dict, w: float, rs: float, last: bool, rl_hf: float) -> tuple[float, float]:
        ic, _ = Ce.bias(p)
        gm = ic / VT
        rpi = p["beta"] / gm
        cpi = gm / (2.0 * PI * p["fT"]) - p["Cmu"]
        rb = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
        ze = _c_div((p["Re"], 0.0), (1.0, w * p["Re"] * p["CE"]))
        zb = _c_add((rpi, 0.0), _c_mul((p["beta"] + 1.0, 0.0), ze))
        zin = _c_par((rb, 0.0), zb)
        zcin = _c_div((1.0, 0.0), (0.0, w * p["Cin"]))
        vbvs = _c_div(zin, _c_add(_c_add((rs, 0.0), zcin), zin))
        ibvs = _c_div(vbvs, zb)
        icvs = _c_mul((p["beta"], 0.0), ibvs)
        rlp = p["Rc"] * rl_hf / (p["Rc"] + rl_hf)
        cm = cpi + p["Cmu"] * (1.0 + gm * rlp)
        rthin = 1.0 / (1.0 / rs + 1.0 / rb + 1.0 / rpi)
        hf = _c_div((1.0, 0.0), (1.0, w * rthin * cm))
        if last:
            zco = _c_div((1.0, 0.0), (0.0, w * p["Cout"]))
            zl = _c_add((p["RL"], 0.0), zco)
            zo = _c_mul(_c_par((p["Rc"], 0.0), zl), _c_div((p["RL"], 0.0), zl))
        else:
            zo = (p["Rc"], 0.0)
        h = _c_mul(_c_mul(icvs, hf), zo)
        return (-h[0], -h[1])

    @staticmethod
    def resp(p: dict, f: float) -> tuple[float, float]:
        w = 2.0 * PI * f
        ic, _ = Ce.bias(p)
        gm = ic / VT
        rpi = p["beta"] / gm
        rb = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
        rin = rb * rpi / (rb + rpi)
        if int(round(p["stages"])) == 1:
            return Ce.stage(p, w, p["Rs"], True, p["RL"])
        h1 = Ce.stage(p, w, p["Rs"], False, rin)
        h2 = Ce.stage(p, w, p["Rc"], True, p["RL"])
        return _c_mul(h1, h2)

    @staticmethod
    def gain(p: dict, f: float) -> float:
        h = Ce.resp(p, f)
        return math.sqrt(h[0] * h[0] + h[1] * h[1])

    @staticmethod
    def phase(p: dict, f: float) -> float:
        h = Ce.resp(p, f)
        return math.degrees(math.atan2(h[1], h[0]))

    @staticmethod
    def scan(p: dict) -> dict:
        am = Ce.gain(p, p["fmid"])
        tgt = am / math.sqrt(2.0)
        n = 1000
        fl = fh = 0.0
        prev_f, prev_g = 1.0, Ce.gain(p, 1.0)
        for i in range(1, n + 1):
            f = math.pow(10.0, 10.0 * i / n)
            g = Ce.gain(p, f)
            if fl == 0.0 and prev_g < tgt <= g:
                fl = math.pow(10.0, math.log10(prev_f) + (math.log10(f) - math.log10(prev_f)) * (tgt - prev_g) / (g - prev_g))
            if fl != 0.0 and fh == 0.0 and prev_g >= tgt > g:
                fh = math.pow(10.0, math.log10(prev_f) + (math.log10(f) - math.log10(prev_f)) * (prev_g - tgt) / (prev_g - g))
            prev_f, prev_g = f, g
        return {"Amid": am, "fL": fl, "fH": fh}

    @staticmethod
    def view(s, p, cfg=None):
        ic, vce = Ce.bias(p)
        return {"t": s.get("t", 0.0), "Ic_mA": ic * 1000.0, "Vce": vce, "gm_mS": ic / VT * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        m = Ce.scan(p)
        m["A"] = Ce.gain(p, p["f"])
        m["phase"] = Ce.phase(p, p["f"])
        return m


def _ce_amid(p: dict) -> float:
    ic, _ = Ce.bias(p)
    gm = ic / VT
    rpi = p["beta"] / gm
    rb = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
    rin = rb * rpi / (rb + rpi)
    a1 = gm * (p["Rc"] * p["RL"] / (p["Rc"] + p["RL"])) * rin / (p["Rs"] + rin)
    if int(round(p["stages"])) == 1:
        return a1
    return gm * p["Rc"] * rin / (p["Rs"] + rin) * (gm * (p["Rc"] * p["RL"] / (p["Rc"] + p["RL"])) * rin / (p["Rc"] + rin))


# ================================================================================================== AM
class Am(_Static):
    """Amplitude modulation. A modulator of sensitivity k_a (per volt) gives the modulation index m = k_a V_m, and
        s(t) = V_c (1 + m sin w_m t) sin w_c t.
    The trace is 6000 samples over two message cycles (75 a carrier cycle). V_max and V_min are the largest and smallest
    carrier PEAK, found cycle by cycle on the samples; m is then (V_max - V_min)/(V_max + V_min)."""

    PARAMS = {"Vc": 2.0, "Vm": 0.5, "fc": 20000.0, "fm": 500.0, "ka": 0.4}
    VARS = ["t", "m", "Vmax", "Vmin"]
    NS = 6000

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list]:
        n = Am.NS
        span = 2.0 / p["fm"]
        dt = span / n
        m = p["ka"] * p["Vm"]
        msg, am = [], []
        for i in range(n):
            t = i * dt
            msg.append(p["Vm"] * math.sin(2.0 * PI * p["fm"] * t))
            am.append(p["Vc"] * (1.0 + m * math.sin(2.0 * PI * p["fm"] * t)) * math.sin(2.0 * PI * p["fc"] * t + 0.3))
        return dt, msg, am

    @staticmethod
    def analyse(p: dict) -> dict:
        dt, msg, am = Am.trace(p)
        per = int(round(Am.NS / (2.0 * p["fc"] / p["fm"])))
        env = []
        for b in range(0, len(am) - per + 1, per):
            env.append(max(am[b:b + per]))
        vmax, vmin = max(env), min(env)
        return {"Vmax": vmax, "Vmin": vmin, "m": (vmax - vmin) / (vmax + vmin), "Vc_est": 0.5 * (vmax + vmin)}

    @staticmethod
    def view(s, p, cfg=None):
        a = Am.analyse(p)
        return {"t": s.get("t", 0.0), "m": a["m"], "Vmax": a["Vmax"], "Vmin": a["Vmin"]}

    @staticmethod
    def measure(p, cfg=None):
        return Am.analyse(p)


def _am_m(p: dict) -> float:
    return p["ka"] * p["Vm"]


# ================================================================================================== FM
class Fm(_Static):
    """Frequency modulation:  s(t) = V_c sin(2 pi f_c t + beta sin 2 pi f_m t),  beta = k_f V_m / f_m, so the frequency
    swings by +- k_f V_m about f_c. The trace is 12000 samples over two message cycles. The instantaneous frequency is
    1 / (interval between successive rising zero crossings); the deviation is half the spread of those values. A
    frequency discriminator (a zero-crossing counter of gain k_d hertz per volt) gives the recovered message
    amplitude = deviation / k_d."""

    PARAMS = {"Vc": 2.0, "Vm": 1.0, "fc": 20000.0, "fm": 250.0, "kf": 1500.0, "kd": 1000.0}
    VARS = ["t", "df_kHz", "beta", "Vrec"]
    NS = 12000

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list]:
        n = Fm.NS
        dt = 2.0 / p["fm"] / n
        beta = p["kf"] * p["Vm"] / p["fm"]
        msg, fm = [], []
        for i in range(n):
            t = i * dt
            msg.append(p["Vm"] * math.sin(2.0 * PI * p["fm"] * t))
            fm.append(p["Vc"] * math.sin(2.0 * PI * p["fc"] * t + beta * math.sin(2.0 * PI * p["fm"] * t)))
        return dt, msg, fm

    @staticmethod
    def analyse(p: dict) -> dict:
        dt, msg, fm = Fm.trace(p)
        cr = _cross(fm, dt, 0.0, True)
        fs = [1.0 / (cr[i + 1] - cr[i]) for i in range(len(cr) - 1)]
        hi, lo = max(fs), min(fs)
        df = 0.5 * (hi - lo)
        return {"df": df, "fc_est": 0.5 * (hi + lo), "beta": df / p["fm"], "Vrec": df / p["kd"],
                "bw": 2.0 * (df + p["fm"])}

    @staticmethod
    def view(s, p, cfg=None):
        a = Fm.analyse(p)
        return {"t": s.get("t", 0.0), "df_kHz": a["df"] / 1000.0, "beta": a["beta"], "Vrec": a["Vrec"]}

    @staticmethod
    def measure(p, cfg=None):
        return Fm.analyse(p)


def _fm_df(p: dict) -> float:
    return p["kf"] * p["Vm"]


# ================================================================================================== op-amp on a scope
class Opa(_Static):
    """An op-amp circuit on the scope, sampled over `n` periods (NW samples). `kind`:
      0 comparator / zero-crossing detector: out follows clamp(A0 (v_in - V_ref), +-V_sat) but can only slew at SR volts per
        second. v_in = -V_p cos(2 pi f t). The trip point is the input at the instant the edge, extended back along its
        straight slewing line, leaves the rail; the slew rate is the 10-90 % swing over the time between those crossings.
      1 integrator: R in, C and a leakage resistor R_f in feedback, square input +-V_p; solved exactly between the
        samples (the input is constant in each): vo' = -v_in/(R C) - vo/(R_f C). The slope is a least-squares line
        through the first half-cycle.
      2 differentiator: R and C in series with the input, a series resistor R_s limits the high-frequency gain, triangle
        input of peak V_p: the output is the ideal -R C dv/dt low-passed with time constant R_s C. Its amplitude is half the
        spread of the samples."""

    PARAMS = {"kind": 0.0, "f": 1000.0, "Vp": 2.0, "R": 10000.0, "C": 1.0e-8, "Rf": 1.0e7, "Rs": 1000.0, "Vref": 1.0,
              "A0": 200000.0, "Vsat": 13.0, "SR": 500000.0, "n": 1.0}
    VARS = ["t", "trip", "SR_us", "slope", "amp"]

    @staticmethod
    def trace(p: dict) -> tuple[float, list, list]:
        k = int(round(p["kind"]))
        n = int(round(p["n"]))
        span = n / p["f"]
        dt = span / NW
        vin, out = [], []
        o = 0.0
        for i in range(NW):
            t = i * dt
            if k == 0:
                v = -p["Vp"] * math.cos(2.0 * PI * p["f"] * t)
                if i == 0:
                    o = _clamp(p["A0"] * (v - p["Vref"]), -p["Vsat"], p["Vsat"])
                else:
                    for sub in range(1, 9):                     # 8 sub-steps a sample, so an edge starts where the input crosses
                        vs = -p["Vp"] * math.cos(2.0 * PI * p["f"] * (t - dt + dt * sub / 8.0))
                        tgt = _clamp(p["A0"] * (vs - p["Vref"]), -p["Vsat"], p["Vsat"])
                        o = o + _clamp(tgt - o, -p["SR"] * dt / 8.0, p["SR"] * dt / 8.0)
            elif k == 1:
                half = NW // (2 * n)
                v = p["Vp"] if (i // half) % 2 == 0 else -p["Vp"]
                e = math.exp(-dt / (p["Rf"] * p["C"]))
                o = _clamp(o * e + (-v * p["Rf"] / p["R"]) * (1.0 - e), -p["Vsat"], p["Vsat"])
            else:
                ph = (i % (NW // n)) / (NW // n)
                v = p["Vp"] * (4.0 * ph if ph < 0.25 else 2.0 - 4.0 * ph if ph < 0.75 else 4.0 * ph - 4.0)
                slope = p["Vp"] * 4.0 * p["f"] * (1.0 if (ph < 0.25 or ph >= 0.75) else -1.0)
                tgt = _clamp(-p["R"] * p["C"] * slope, -p["Vsat"], p["Vsat"])
                e = math.exp(-dt / (p["Rs"] * p["C"]))
                o = o * e + tgt * (1.0 - e)
            vin.append(v)
            out.append(o)
        return dt, vin, out

    @staticmethod
    def analyse(p: dict) -> dict:
        k = int(round(p["kind"]))
        dt, vin, out = Opa.trace(p)
        res = {"trip": 0.0, "SR": 0.0, "vlo": 0.0, "vhi": 0.0, "slope": 0.0, "vpp": 0.0, "amp": 0.0}
        if k == 0:
            lo, hi = min(out), max(out)
            sw = hi - lo
            t10 = _cross(out, dt, lo + 0.1 * sw, True)
            t90 = _cross(out, dt, lo + 0.9 * sw, True)
            res["SR"] = 0.8 * sw / (t90[0] - t10[0])
            j = 0
            while out[j] < lo + 1.0:
                j += 1
            s = (out[j + 1] - out[j]) / dt
            tdep = j * dt - (out[j] - lo) / s
            res["trip"] = -p["Vp"] * math.cos(2.0 * PI * p["f"] * tdep)
            res["vlo"], res["vhi"] = lo, hi
        elif k == 1:
            half = NW // (2 * int(round(p["n"])))
            xs = [i * dt for i in range(20, half - 20)]
            ys = [out[i] for i in range(20, half - 20)]
            res["slope"] = _ols(xs, ys)
            res["vpp"] = max(out) - min(out)
        else:
            res["amp"] = 0.5 * (max(out) - min(out))
        return res

    @staticmethod
    def view(s, p, cfg=None):
        a = Opa.analyse(p)
        return {"t": s.get("t", 0.0), "trip": a["trip"], "SR_us": a["SR"] / 1e6, "slope": a["slope"], "amp": a["amp"]}

    @staticmethod
    def measure(p, cfg=None):
        return Opa.analyse(p)


def _opa_main(p: dict) -> float:
    k = int(round(p["kind"]))
    if k == 0:
        return p["Vref"]
    if k == 1:
        return -p["Vp"] / (p["R"] * p["C"])
    return 4.0 * p["Vp"] * p["f"] * p["R"] * p["C"]


# ================================================================================================== dipole antenna
class Ant(_Static):
    """Far field of a centre-fed linear dipole of length L = ell lambda carrying a sinusoidal current of peak I0, at distance r
    and angle theta from its axis:  |E| = eta I0 / (2 pi r) |cos(pi ell cos theta) - cos(pi ell)| / sin theta  (eta = 376.73 ohm).
    The peak field and the half-power beamwidth are found by SCANNING theta from 0.5 to 179.5 degrees in half-degree steps
    (the beamwidth is the angular distance between the two crossings of E_max/sqrt 2, interpolated linearly)."""

    PARAMS = {"th": 90.0, "ell": 0.5, "I0": 0.1, "r": 5.0}
    VARS = ["t", "E", "rel"]
    ETA = 376.730313668

    @staticmethod
    def pat(p: dict, th: float) -> float:
        a = math.radians(th)
        s = math.sin(a)
        if abs(s) < 1e-9:
            return 0.0
        return abs(math.cos(PI * p["ell"] * math.cos(a)) - math.cos(PI * p["ell"])) / s

    @staticmethod
    def field(p: dict, th: float) -> float:
        return Ant.ETA * p["I0"] / (2.0 * PI * p["r"]) * Ant.pat(p, th)

    @staticmethod
    def scan(p: dict) -> dict:
        es = [Ant.field(p, 0.5 + 0.5 * i) for i in range(359)]
        emax = max(es)
        half = emax / math.sqrt(2.0)
        left = right = 0.0
        for i in range(1, 359):
            if es[i - 1] < half <= es[i] and left == 0.0:
                left = 0.5 + 0.5 * (i - 1) + 0.5 * (half - es[i - 1]) / (es[i] - es[i - 1])
            if es[i - 1] >= half > es[i]:
                right = 0.5 + 0.5 * (i - 1) + 0.5 * (es[i - 1] - half) / (es[i - 1] - es[i])
        return {"Emax": emax, "hpbw": right - left}

    @staticmethod
    def view(s, p, cfg=None):
        e = Ant.field(p, p["th"])
        return {"t": s.get("t", 0.0), "E": e, "rel": e / (Ant.ETA * p["I0"] / (2.0 * PI * p["r"]))}

    @staticmethod
    def measure(p, cfg=None):
        return Ant.scan(p)


def _ant_emax(p: dict) -> float:
    return Ant.ETA * p["I0"] / (2.0 * PI * p["r"]) * (1.0 - math.cos(PI * p["ell"]))


# ================================================================================================== BJT bias circuits
class Bias(_Static):
    """Three ways of biasing a common-emitter transistor from V_cc, with a constant V_BE and a current gain beta:
      cfg 0  fixed bias:            I_B = (V_cc - V_BE)/R_B
      cfg 1  collector-to-base:     I_B = (V_cc - V_BE)/(R_F + (beta + 1) R_C)
      cfg 2  voltage divider + R_E: I_C = (V_th - V_BE)/(R_th/beta + R_E (beta + 1)/beta)
    and I_C = beta I_B in the first two. V_CE follows from the loop."""

    PARAMS = {"cfg": 0.0, "Vcc": 12.0, "beta": 200.0, "Vbe": 0.65, "Rb": 1200000.0, "Rf": 470000.0, "R1": 47000.0,
              "R2": 10000.0, "Rc": 2200.0, "Re": 680.0}
    VARS = ["t", "Ic_mA", "Vce", "Ib_uA"]

    @staticmethod
    def solve(p: dict) -> tuple[float, float, float]:
        k = int(round(p["cfg"]))
        b = p["beta"]
        if k == 0:
            ib = (p["Vcc"] - p["Vbe"]) / p["Rb"]
            ic = b * ib
            vce = p["Vcc"] - ic * p["Rc"]
        elif k == 1:
            ib = (p["Vcc"] - p["Vbe"]) / (p["Rf"] + (b + 1.0) * p["Rc"])
            ic = b * ib
            vce = p["Vcc"] - (ic + ib) * p["Rc"]
        else:
            vth = p["Vcc"] * p["R2"] / (p["R1"] + p["R2"])
            rth = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
            ic = (vth - p["Vbe"]) / (rth / b + p["Re"] * (b + 1.0) / b)
            ib = ic / b
            vce = p["Vcc"] - ic * p["Rc"] - (ic + ib) * p["Re"]
        return ic, vce, ib

    @staticmethod
    def view(s, p, cfg=None):
        ic, vce, ib = Bias.solve(p)
        return {"t": s.get("t", 0.0), "Ic_mA": ic * 1000.0, "Vce": vce, "Ib_uA": ib * 1e6}

    @staticmethod
    def measure(p, cfg=None):
        ic, vce, ib = Bias.solve(p)
        return {"Ic": ic, "Vce": vce, "Ib": ib}


def _bias_ic(p: dict) -> float:
    """Textbook: fixed bias I_C = beta (V_cc - V_BE)/R_B; collector feedback I_C = beta (V_cc - V_BE)/(R_F + beta R_C);
    divider (I_E taken equal to I_C):  I_C = (V_th - V_BE)/(R_E + R_th/beta)."""
    k = int(round(p["cfg"]))
    b = p["beta"]
    if k == 0:
        return b * (p["Vcc"] - p["Vbe"]) / p["Rb"]
    if k == 1:
        return b * (p["Vcc"] - p["Vbe"]) / (p["Rf"] + b * p["Rc"])
    vth = p["Vcc"] * p["R2"] / (p["R1"] + p["R2"])
    rth = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
    return (vth - p["Vbe"]) / (p["Re"] + rth / b)


# ================================================================================================== registry
KERNELS: dict[str, Any] = {
    "sn_lvdt": Lvdt, "sn_strain": Strain, "sn_capl": Capl, "sn_ultra": Ultra, "sn_tsens": Tsens, "sn_photo": Photo,
    "sn_mload": Mload, "sn_mbw": Mbw, "sn_vac": Vac, "sn_scope": Scope, "sn_pulse": Pulse, "sn_shape": Shape,
    "sn_mv": Mv, "sn_ce": Ce, "sn_am": Am, "sn_fm": Fm, "sn_opa": Opa, "sn_ant": Ant, "sn_bias": Bias,
}
FAMILY = {k: "circuit" for k in KERNELS}
TEXTBOOK = {
    "sn_lvdt_v": _lvdt_v, "sn_strain_vb": _strain_vb, "sn_capl_slope": _capl_slope, "sn_ultra_d": _ultra_d,
    "sn_tsens_slope": _tsens_slope, "sn_photo_r": _photo_r, "sn_mload_err": _mload_err, "sn_mbw_f3": _mbw_f3,
    "sn_vac_p": _vac_p, "sn_scope_phase": _scope_phase, "sn_pulse_tr": _pulse_tr, "sn_shape_lvl": _shape_lvl,
    "sn_mv_main": _mv_main, "sn_ce_amid": _ce_amid, "sn_am_m": _am_m, "sn_fm_df": _fm_df, "sn_opa_main": _opa_main, "sn_ant_emax": _ant_emax, "sn_bias_ic": _bias_ic,
}
CALCS: dict[str, dict] = {}
