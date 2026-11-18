"""Kernel pack `pg_elec_w9`: the M.Sc. ELECTRONICS set-ups of `syllabus/physics/pg.json` (wave 9). Its exact JavaScript
twin is `app/static/prayog/packs/pg_elec_w9.js`; the test suite runs both on the same inputs and demands the same numbers,
so the two files carry the same formulas step by step (explicit loops, never Python's compensated `sum()`).

Every kernel is prefixed `pe9_`, is deterministic (fixed sample counts, fixed bisection counts, no randomness, no wall
clock) and works in SI units. The rig `pe9-elec-bench` draws the bench; every number on its meters and its scope comes
from these functions.

  pe9_reg     regulated supplies: zener shunt, zener-referenced series transistor (emitter follower), IC regulator;
              line and load regulation by finite differences, output ripple from a sampled rippling input
  pe9_conv    converters: 4-bit binary-weighted and R-2R DACs with per-leg resistor errors, 8-bit SAR ADC run bit by bit
  pe9_filt    passive RC low-pass, high-pass and the loaded two-section band-pass; corners by bisection
  pe9_lcr     series and parallel (coil || capacitor) resonance: current against frequency, extremum by golden search,
              half-power points by bisection
  pe9_opl     op-amp linear circuits on a single-pole op-amp: inverting, non-inverting, summing, difference, follower,
              averaging; closed-loop gain G/(1 + NG/A(jf))
  pe9_intdiff op-amp integrator (with its DC leak) and differentiator (with its input resistor) driven by square, sine
              and triangle waves; the periodic steady state by exact first-order-hold steps
  pe9_cmp     zero-crossing detector (open-loop transfer), precision peak detector (sampled), three-op-amp
              instrumentation amplifier with a mismatched difference stage
  pe9_tri     triangle-wave generator: Schmitt comparator + integrator, the loop stepped exactly and its period read
  pe9_sweep   five time-base generators as a capacitor charging towards an asymptote between two levels
  pe9_tuned   single-tuned and double-tuned (two coupled identical tanks) amplifier responses
  pe9_cnt     asynchronous (ripple) and synchronous mod-N counters: count sequence, modulus and output delays
  pe9_amfm    amplitude and frequency modulation: sampled signals, sideband lines by a DFT, Bessel J0 carrier null
  pe9_acomp   op-amp analog computer: falling body, simultaneous equations, damped second-order equation (RK4)
  pe9_pa      class A (series-fed) and class B push-pull power amplifiers: power, efficiency and THD from samples
  pe9_opp     op-amp parameters: offset voltage, bias current, CMRR, slew rate and gain-bandwidth from their test circuits
  pe9_xtal    quartz crystal oscillator: load-capacitance pulling and an AT-cut cubic temperature curve
  pe9_ce      a common-emitter stage designed for a gain (unbypassed emitter resistor): gain, bandwidth, input impedance
  pe9_mv      multivibrators: transistor, 555 and op-amp; astable, monostable and bistable (as a toggle / Schmitt)
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
VT = 0.025852                    # thermal voltage at 300 K (k T / q), the constant the other packs use


def _bis(f, lo: float, hi: float, n: int = 100) -> float:
    flo = f(lo)
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if (fm > 0.0) == (flo > 0.0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _gold(f, lo: float, hi: float, n: int = 120) -> float:
    """Maximum of a unimodal f on [lo, hi] by golden-section search with a fixed number of steps."""
    g = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c = b - g * (b - a)
    d = a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(n):
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    return 0.5 * (a + b)


def _cross(y: list, dt: float, level: float, rising: bool = True) -> list:
    out = []
    for i in range(1, len(y)):
        a, b = y[i - 1] - level, y[i] - level
        if rising and a < 0 <= b and b != a:
            out.append((i - 1 + (0 - a) / (b - a)) * dt)
        elif (not rising) and a >= 0 > b:
            out.append((i - 1 + (0 - a) / (b - a)) * dt)
    return out


def _maxv(a: list) -> float:
    m = a[0]
    for v in a:
        if v > m:
            m = v
    return m


def _minv(a: list) -> float:
    m = a[0]
    for v in a:
        if v < m:
            m = v
    return m


def _mean(a: list) -> float:
    s = 0.0
    for v in a:
        s += v
    return s / len(a)


def _sinc(y: list, dt: float, f: float) -> tuple[float, float]:
    """(sine, cosine) Fourier coefficients of y at frequency f over the whole record: 2/N sum y sin, 2/N sum y cos."""
    s = c = 0.0
    n = len(y)
    for i in range(n):
        th = 2.0 * PI * f * i * dt
        s += y[i] * math.sin(th)
        c += y[i] * math.cos(th)
    return 2.0 * s / n, 2.0 * c / n


def _ols(xs: list, ys: list) -> tuple[float, float]:
    n = len(xs)
    sx = sy = sxy = sxx = 0.0
    for i in range(n):
        sx += xs[i]
        sy += ys[i]
        sxy += xs[i] * ys[i]
        sxx += xs[i] * xs[i]
    den = n * sxx - sx * sx
    m = 0.0 if den == 0 else (n * sxy - sx * sy) / den
    return m, (sy - m * sx) / n


def _cabs(re: float, im: float) -> float:
    return math.sqrt(re * re + im * im)


def _cdiv(a, b):
    d = b[0] * b[0] + b[1] * b[1]
    return ((a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d)


def _j0(x: float) -> float:
    """Bessel J0 by its power series, 40 terms (exact to double precision for x < 10)."""
    s, t = 0.0, 1.0
    q = -0.25 * x * x
    for k in range(40):
        s += t
        t = t * q / ((k + 1.0) * (k + 1.0))
    return s


def _jn(n: int, x: float) -> float:
    """Bessel J_n (n >= 0) by its power series, 40 terms."""
    t = 1.0
    for k in range(n):
        t = t * (0.5 * x) / (k + 1.0)
    s = 0.0
    q = -0.25 * x * x
    for k in range(40):
        s += t
        t = t * q / ((k + 1.0) * (k + 1.0 + n))
    return s


class _Static:
    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


# ===================================================================================================== regulators
class Reg(_Static):
    """kind 0 zener shunt (series R_s, zener V_z with slope resistance r_z): V_o = (V_in r_z + V_z R_s - I_L R_s r_z)
    / (R_s + r_z), or V_in - I_L R_s when the zener current would be negative. kind 1 series transistor: the same zener
    divider feeds the base of an emitter follower that draws I_L / (beta + 1) from it; V_o = V_b - V_T ln(I_L/I_s + 1).
    kind 2 IC regulator: V_o = V_nom + k_l (V_in - 10 V) - R_o I_L, or V_in - V_do in dropout. Line regulation is
    dV_o/dV_in by a +-1 V central difference, the output resistance -dV_o/dI_L by +-10 mA, and the output ripple is
    max - min of V_o over a triangular ripple of V_r peak to peak on the input (a 100 Hz full-wave ripple)."""

    PARAMS = {"kind": 0.0, "Vin": 15.0, "IL": 0.02, "Rs": 100.0, "Vz": 6.2, "rz": 5.0, "beta": 100.0, "Is": 1.0e-13,
              "Vnom": 5.0, "kl": 1.7e-4, "Ro": 0.01, "Vdo": 2.0, "Vr": 1.0}
    VARS = ["t", "Vout"]
    NR = 400

    @staticmethod
    def out(p: dict, vin: float, il: float) -> float:
        k = int(round(p["kind"]))
        if k == 2:
            return min(p["Vnom"] + p["kl"] * (vin - 10.0) - p["Ro"] * il, vin - p["Vdo"])
        rs, rz = p["Rs"], p["rz"]
        idraw = il if k == 0 else il / (p["beta"] + 1.0)
        v = (vin * rz + p["Vz"] * rs - idraw * rs * rz) / (rs + rz)
        if (vin - v) / rs - idraw < 0.0:
            v = vin - idraw * rs
        if k == 0:
            return v
        return v - VT * math.log(il / p["Is"] + 1.0)

    @staticmethod
    def ripple(p: dict, vin: float, il: float) -> tuple[list, list, float]:
        dt = 0.01 / Reg.NR
        a, b = [], []
        for i in range(Reg.NR):
            x = i / Reg.NR
            tri = 2.0 * x if x < 0.5 else 2.0 - 2.0 * x
            v = vin + p["Vr"] * (tri - 0.5)
            a.append(v)
            b.append(Reg.out(p, v, il))
        return a, b, dt

    @staticmethod
    def run(p: dict, vin: float, il: float) -> dict:
        a, b, dt = Reg.ripple(p, vin, il)
        return {"Vout": Reg.out(p, vin, il), "rin": _maxv(a) - _minv(a), "rout": _maxv(b) - _minv(b)}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Vout": Reg.out(p, p["Vin"], p["IL"])}

    @staticmethod
    def measure(p, cfg=None):
        r = Reg.run(p, p["Vin"], p["IL"])
        r["line"] = (Reg.out(p, p["Vin"] + 1.0, p["IL"]) - Reg.out(p, p["Vin"] - 1.0, p["IL"])) / 2.0
        r["Rout"] = (Reg.out(p, p["Vin"], p["IL"] - 0.01) - Reg.out(p, p["Vin"], p["IL"] + 0.01)) / 0.02
        return r


def _reg_line(p: dict) -> float:
    k = int(round(p["kind"]))
    return p["kl"] if k == 2 else p["rz"] / (p["Rs"] + p["rz"])


# ===================================================================================================== converters
class Conv(_Static):
    """kind 0 R-2R ladder DAC (current mode: each 2R leg is switched to the op-amp's virtual earth or to earth; the
    MSB leg carries V_ref/(2R), each next leg half the one before), kind 1 binary-weighted DAC (bit i through
    2^(3-i) R), both into a transimpedance op-amp of feedback R_f; leg resistor errors e0..e3 (MSB first) scale each
    leg's current by 1/(1 + e). Output shown as a positive voltage. kind 2: an 8-bit successive-approximation ADC on
    V_ref with a comparator offset V_off, the SAR loop run bit by bit (half-LSB offset as in an ADC0804)."""

    PARAMS = {"kind": 0.0, "D": 9.0, "Vref": 5.0, "R": 10000.0, "Rf": 10000.0, "e0": 0.004, "e1": -0.003, "e2": 0.002,
              "e3": -0.001, "Vin": 2.0, "Voff": 0.004}
    VARS = ["t", "out"]

    @staticmethod
    def dac(p: dict, d: int) -> float:
        k = int(round(p["kind"]))
        es = [p["e0"], p["e1"], p["e2"], p["e3"]]
        i = 0.0
        for b in range(4):                    # b = 0 is the MSB
            if (d >> (3 - b)) & 1:
                if k == 0:
                    ideal = p["Vref"] / (2.0 * p["R"]) / (2.0 ** b)
                else:
                    ideal = p["Vref"] / (p["R"] * (2.0 ** b))
                i += ideal / (1.0 + es[b])
        return i * p["Rf"]

    @staticmethod
    def adc(p: dict, vin: float) -> int:
        lsb = p["Vref"] / 256.0
        code = 0
        for b in range(7, -1, -1):
            trial = code | (1 << b)
            if vin - p["Voff"] >= (trial - 0.5) * lsb:
                code = trial
        return code

    @staticmethod
    def dac_fit(p: dict) -> dict:
        xs, ys = [], []
        for d in range(16):
            xs.append(float(d))
            ys.append(Conv.dac(p, d))
        m, c = _ols(xs, ys)
        inl = 0.0
        for d in range(16):
            e = abs(ys[d] - (m * d + c)) / m
            if e > inl:
                inl = e
        return {"lsb": m, "off": c, "inl": inl, "fs": ys[15]}

    @staticmethod
    def view(s, p, cfg=None):
        k = int(round(p["kind"]))
        return {"t": s.get("t", 0.0), "out": float(Conv.adc(p, p["Vin"])) if k == 2 else Conv.dac(p, int(round(p["D"])))}

    @staticmethod
    def measure(p, cfg=None):
        k = int(round(p["kind"]))
        if k == 2:
            return {"code": float(Conv.adc(p, p["Vin"])), "lsb": p["Vref"] / 256.0, "main": float(Conv.adc(p, p["Vin"]))}
        r = Conv.dac_fit(p)
        r["Vout"] = Conv.dac(p, int(round(p["D"])))
        r["main"] = r["lsb"]
        return r


def _conv_main(p: dict) -> float:
    k = int(round(p["kind"]))
    if k == 2:
        lsb = p["Vref"] / 256.0
        return float(max(0, min(255, math.floor((p["Vin"] - p["Voff"]) / lsb + 0.5))))
    return p["Vref"] * p["Rf"] / (p["R"] * (16.0 if k == 0 else 8.0))


# ===================================================================================================== passive filters
class Filt(_Static):
    """kind 0 RC low-pass 1/(1 + j w R C); kind 1 CR high-pass j w R C/(1 + j w R C); kind 2 a C1-R1 high-pass section
    loaded by an R2-C2 low-pass section: H = j w R1 C1 / (1 - w^2 R1 C1 R2 C2 + j w (R1 C1 + R2 C2 + R1 C2)). The -3 dB
    points are found by bisection on |H| against its pass-band value; for the band-pass, f0 = sqrt(f_L f_H) (the
    response is symmetric in log f). The roll-off is the slope in dB per decade between 10 and 100 times the corner."""

    PARAMS = {"kind": 0.0, "R": 10000.0, "C": 1.0e-8, "R2": 100000.0, "C2": 1.0e-10, "f": 1000.0, "Vin": 1.0}
    VARS = ["t", "gain_db"]

    @staticmethod
    def h(p: dict, f: float) -> tuple[float, float]:
        k = int(round(p["kind"]))
        w = 2.0 * PI * f
        if k == 0:
            return _cdiv((1.0, 0.0), (1.0, w * p["R"] * p["C"]))
        if k == 1:
            return _cdiv((0.0, w * p["R"] * p["C"]), (1.0, w * p["R"] * p["C"]))
        r1, c1, r2, c2 = p["R"], p["C"], p["R2"], p["C2"]
        return _cdiv((0.0, w * r1 * c1), (1.0 - w * w * r1 * c1 * r2 * c2, w * (r1 * c1 + r2 * c2 + r1 * c2)))

    @staticmethod
    def mag(p: dict, f: float) -> float:
        a = Filt.h(p, f)
        return _cabs(a[0], a[1])

    @staticmethod
    def db(p: dict, f: float) -> float:
        return 20.0 * math.log10(Filt.mag(p, f))

    @staticmethod
    def phase(p: dict, f: float) -> float:
        a = Filt.h(p, f)
        return math.atan2(a[1], a[0]) * 180.0 / PI

    @staticmethod
    def corners(p: dict) -> dict:
        k = int(round(p["kind"]))
        lf = lambda f: math.log10(f)                                                     # noqa: E731
        if k < 2:
            fn = 1.0 / (2.0 * PI * p["R"] * p["C"])
            fc = 10.0 ** _bis(lambda x: Filt.mag(p, 10.0 ** x) - 1.0 / math.sqrt(2.0), lf(fn) - 3.0, lf(fn) + 3.0, 80)
            far = fc * 10.0 if k == 0 else fc / 10.0
            far2 = fc * 100.0 if k == 0 else fc / 100.0
            roll = abs(Filt.db(p, far2) - Filt.db(p, far))
            return {"fc": fc, "fL": fc, "fH": fc, "roll": roll}
        f0 = 1.0 / (2.0 * PI * math.sqrt(p["R"] * p["C"] * p["R2"] * p["C2"]))
        hm = Filt.mag(p, f0) / math.sqrt(2.0)
        fl = 10.0 ** _bis(lambda x: Filt.mag(p, 10.0 ** x) - hm, lf(f0) - 4.0, lf(f0), 80)
        fh = 10.0 ** _bis(lambda x: Filt.mag(p, 10.0 ** x) - hm, lf(f0), lf(f0) + 4.0, 80)
        roll = abs(Filt.db(p, fh * 100.0) - Filt.db(p, fh * 10.0))
        return {"fc": math.sqrt(fl * fh), "fL": fl, "fH": fh, "roll": roll, "Amax": Filt.mag(p, f0)}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "gain_db": Filt.db(p, p["f"])}

    @staticmethod
    def measure(p, cfg=None):
        r = Filt.corners(p)
        r["gain_db"] = Filt.db(p, p["f"])
        return r


def _filt_fc(p: dict) -> float:
    k = int(round(p["kind"]))
    if k < 2:
        return 1.0 / (2.0 * PI * p["R"] * p["C"])
    return 1.0 / (2.0 * PI * math.sqrt(p["R"] * p["C"] * p["R2"] * p["C2"]))


# ===================================================================================================== resonance
class Lcr(_Static):
    """mode 0 series R-L-C on a generator of V rms: I = V/|R + j(wL - 1/(wC))|. mode 1 parallel: a coil (L with its
    resistance R) in parallel with C; the generator current I = V |1/(R + j w L) + j w C|. The resonant frequency is
    the extremum of I (golden-section search on log f), the half-power frequencies by bisection, Q = f_r / bandwidth."""

    PARAMS = {"mode": 0.0, "R": 47.0, "L": 0.022, "C": 4.7e-8, "f": 1000.0, "V": 1.0}
    VARS = ["t", "I_mA"]

    @staticmethod
    def cur(p: dict, f: float) -> float:
        w = 2.0 * PI * f
        if int(round(p["mode"])) == 0:
            return p["V"] / _cabs(p["R"], w * p["L"] - 1.0 / (w * p["C"]))
        y = _cdiv((1.0, 0.0), (p["R"], w * p["L"]))
        return p["V"] * _cabs(y[0], y[1] + w * p["C"])

    @staticmethod
    def analyse(p: dict) -> dict:
        par = int(round(p["mode"])) == 1
        f0 = 1.0 / (2.0 * PI * math.sqrt(p["L"] * p["C"]))
        sg = -1.0 if par else 1.0
        x0 = _gold(lambda x: sg * Lcr.cur(p, 10.0 ** x), math.log10(f0) - 0.5, math.log10(f0) + 0.5, 120)
        fr = 10.0 ** x0
        ir = Lcr.cur(p, fr)
        if par:
            lev = lambda x: 1.0 / Lcr.cur(p, 10.0 ** x) - math.sqrt(0.5) / ir      # noqa: E731  |Z| at 0.707 max
        else:
            lev = lambda x: Lcr.cur(p, 10.0 ** x) - ir / math.sqrt(2.0)              # noqa: E731
        f1 = 10.0 ** _bis(lev, x0 - 1.0, x0, 80)
        f2 = 10.0 ** _bis(lev, x0, x0 + 1.0, 80)
        return {"fr": fr, "Ir": ir, "f1": f1, "f2": f2, "Q": fr / (f2 - f1)}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I_mA": Lcr.cur(p, p["f"]) * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        r = Lcr.analyse(p)
        r["I"] = Lcr.cur(p, p["f"])
        return r


def _lcr_fr(p: dict) -> float:
    if int(round(p["mode"])) == 0:
        return 1.0 / (2.0 * PI * math.sqrt(p["L"] * p["C"]))
    return math.sqrt(1.0 / (p["L"] * p["C"]) - (p["R"] / p["L"]) ** 2) / (2.0 * PI)


def _lcr_q(p: dict) -> float:
    if int(round(p["mode"])) == 0:
        return math.sqrt(p["L"] / p["C"]) / p["R"]
    return 2.0 * PI * _lcr_fr(p) * p["L"] / p["R"]


# ===================================================================================================== op-amp linear
class Opl(_Static):
    """A single-pole op-amp A(jf) = A0/(1 + j f/f_a) in six circuits. Each has an ideal gain G (from input 1) and a noise
    gain NG = 1 + R_f / (the resistance from the inverting input to the sources): kind 0 inverting G = -R_f/R_1;
    1 non-inverting 1 + R_f/R_1; 2 summing (two inputs of R_1) -R_f/R_1 each, NG = 1 + 2 R_f/R_1; 3 difference (R_1,
    R_f on both sides) G = R_f/R_1 on V_2 - V_1; 4 voltage follower G = 1, NG = 1; 5 averaging = the summer with
    R_f = R_1/2. Closed loop: G/(1 + NG/A(jf)); the -3 dB frequency is f_a (1 + A0/NG) exactly."""

    PARAMS = {"kind": 0.0, "R1": 10000.0, "Rf": 100000.0, "A0": 200000.0, "fa": 5.0, "V1": 0.05, "V2": 0.03,
              "f": 1000.0}
    VARS = ["t", "gain"]

    @staticmethod
    def gng(p: dict) -> tuple[float, float]:
        k = int(round(p["kind"]))
        r = p["Rf"] / p["R1"]
        if k == 0:
            return -r, 1.0 + r
        if k == 1:
            return 1.0 + r, 1.0 + r
        if k == 2 or k == 5:
            return -r, 1.0 + 2.0 * r
        if k == 3:
            return r, 1.0 + r
        return 1.0, 1.0

    @staticmethod
    def gain(p: dict, f: float) -> float:
        g, ng = Opl.gng(p)
        a = _cdiv((p["A0"], 0.0), (1.0, f / p["fa"]))
        d = _cdiv((ng, 0.0), a)
        return abs(g) / _cabs(1.0 + d[0], d[1])

    @staticmethod
    def dc_out(p: dict) -> float:
        k = int(round(p["kind"]))
        g, ng = Opl.gng(p)
        lo = 1.0 / (1.0 + ng / p["A0"])
        if k == 2 or k == 5:
            return g * (p["V1"] + p["V2"]) * lo
        if k == 3:
            return g * (p["V2"] - p["V1"]) * lo
        return g * p["V1"] * lo

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "gain": Opl.gain(p, p["f"])}

    @staticmethod
    def measure(p, cfg=None):
        g, ng = Opl.gng(p)
        g0 = Opl.gain(p, 0.01)
        f3 = 10.0 ** _bis(lambda x: Opl.gain(p, 10.0 ** x) - g0 / math.sqrt(2.0), 0.0, 9.0, 90)
        return {"gain": g0, "f3": f3, "gbw": f3 * ng, "dc": Opl.dc_out(p), "at_f": Opl.gain(p, p["f"])}


def _opl_gain(p: dict) -> float:
    return abs(Opl.gng(p)[0])


# ===================================================================================================== integrator / differentiator
class IntDiff(_Static):
    """kind 0 integrator: input R, feedback C shunted by R_f: y obeys tau_f dy/dt = -(R_f/R) x - y, tau_f = R_f C.
    kind 1 differentiator: input R_s in series with C, feedback R: the capacitor voltage v obeys R_s C dv/dt = x - v and
    y = -R (x - v)/R_s. wave 0 square, 1 sine, 2 triangle of peak V_p at f. Each is stepped with the exact first-order-
    hold solution over one period of N samples; the periodic steady state follows from linearity (y0 = y_T/(1 - e^(-T/
    tau))). The time constant RC is then read from the output exactly as the student does: from its peak-to-peak value
    (or, for a differentiator on a square wave, from the 1/e decay of the spike, giving R_s C)."""

    PARAMS = {"kind": 0.0, "wave": 0.0, "R": 10000.0, "C": 1.0e-8, "Rf": 1.0e7, "Rs": 1000.0, "Vp": 1.0, "f": 1000.0}
    VARS = ["t", "Vpp"]
    N = 4000

    @staticmethod
    def x_at(p: dict, i: int) -> float:
        n = IntDiff.N
        w = int(round(p["wave"]))
        u = i / n
        if w == 0:
            return p["Vp"] if u < 0.5 else -p["Vp"]
        if w == 1:
            return p["Vp"] * math.sin(2.0 * PI * u)
        q = u + 0.25
        q = q - math.floor(q)
        return p["Vp"] * (4.0 * q - 1.0 if q < 0.5 else 3.0 - 4.0 * q)

    @staticmethod
    def _pass(p: dict, s0: float) -> list:
        """One period from state s0; returns the states at every sample (N + 1 values)."""
        n = IntDiff.N
        k = int(round(p["kind"]))
        h = 1.0 / p["f"] / n
        tau = p["Rf"] * p["C"] if k == 0 else p["Rs"] * p["C"]
        g = -p["Rf"] / p["R"] if k == 0 else 1.0
        e = math.exp(-h / tau)
        kk = tau / h * (1.0 - e)
        st = [s0]
        s = s0
        xa = IntDiff.x_at(p, 0) * g
        for i in range(n):
            xb = IntDiff.x_at(p, (i + 1) % n) * g        # a square wave's jump is a one-sample ramp
            s = xb + (s - xa) * e - (xb - xa) * kk
            st.append(s)
            xa = xb
        return st

    @staticmethod
    def trace(p: dict) -> tuple[list, list, float]:
        n = IntDiff.N
        k = int(round(p["kind"]))
        tau = p["Rf"] * p["C"] if k == 0 else p["Rs"] * p["C"]
        st = IntDiff._pass(p, 0.0)
        y0 = st[n] / (1.0 - math.exp(-1.0 / p["f"] / tau))
        st = IntDiff._pass(p, y0)
        xs, ys = [], []
        for i in range(n):
            x = IntDiff.x_at(p, i)
            xs.append(x)
            ys.append(st[i] if k == 0 else -p["R"] * (x - st[i]) / p["Rs"])
        return xs, ys, 1.0 / p["f"] / n

    @staticmethod
    def analyse(p: dict) -> dict:
        xs, ys, dt = IntDiff.trace(p)
        k, w = int(round(p["kind"])), int(round(p["wave"]))
        vpp = _maxv(ys) - _minv(ys)
        T = 1.0 / p["f"]
        if k == 0:
            rc = p["Vp"] * T / (2.0 * vpp) if w == 0 else (2.0 * p["Vp"] / (2.0 * PI * p["f"] * vpp) if w == 1 else
                                                           p["Vp"] * T / (4.0 * vpp))
            dec = 0.0
        else:
            dec = 0.0
            if w == 0:
                n = len(ys)
                j, pk = 0, 0.0
                for i in range(n):
                    if abs(ys[i]) > pk:
                        pk, j = abs(ys[i]), i
                lev = pk / math.e
                for i in range(j + 1, n):
                    if abs(ys[i]) <= lev:
                        a, b = abs(ys[i - 1]), abs(ys[i])
                        dec = (i - 1 + (a - lev) / (a - b) - j) * dt
                        break
                rc = dec * p["R"] / p["Rs"]
            elif w == 1:
                rc = vpp / (2.0 * 2.0 * PI * p["f"] * p["Vp"])
            else:
                rc = vpp / (8.0 * p["Vp"] * p["f"])
        return {"Vpp": vpp, "tau": rc, "decay": dec}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Vpp": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        return IntDiff.analyse(p)


def _intdiff_rc(p: dict) -> float:
    return p["R"] * p["C"]


# ===================================================================================================== comparators etc.
class Cmp(_Static):
    """kind 0 zero-crossing detector: an open-loop op-amp V_o = clip(A0 (V_in - V_os), +-V_sat); the trip point is where
    V_o passes zero. kind 1 precision peak detector: the capacitor C (load R_L) follows the input whenever the input
    exceeds it, otherwise discharges as exp(-t/(R_L C)); sampled over 8 periods of a sine of peak V_p at f, the last
    period gives the held peak and the ripple. kind 2 three-op-amp instrumentation amplifier: input stage gain
    1 + 2R/R_g, difference stage R1 = R3 = R_a, R2 = R_b, R4 = R_b (1 + eps): A_d and the common-mode gain A_cm."""

    PARAMS = {"kind": 0.0, "Vin": 0.0, "A0": 200000.0, "Vos": 0.00184, "Vsat": 13.0, "Vp": 2.0, "f": 1000.0,
              "Ch": 1.0e-6, "RL": 100000.0, "R": 10000.0, "Rg": 1000.0, "Ra": 10000.0, "Rb": 10000.0, "eps": 0.002}
    VARS = ["t", "Vo"]
    NP = 8
    NPER = 500

    @staticmethod
    def zcd(p: dict, vin: float) -> float:
        v = p["A0"] * (vin - p["Vos"])
        return max(-p["Vsat"], min(p["Vsat"], v))

    @staticmethod
    def peak(p: dict) -> tuple[list, list, float]:
        n = Cmp.NP * Cmp.NPER
        dt = 1.0 / p["f"] / Cmp.NPER
        e = math.exp(-dt / (p["RL"] * p["Ch"]))
        xs, ys = [], []
        v = 0.0
        for i in range(n):
            x = p["Vp"] * math.sin(2.0 * PI * i / Cmp.NPER)
            v = v * e
            if x > v:
                v = x
            xs.append(x)
            ys.append(v)
        return xs[n - Cmp.NPER:], ys[n - Cmp.NPER:], dt

    @staticmethod
    def ina(p: dict, rg: float) -> tuple[float, float]:
        g1 = 1.0 + 2.0 * p["R"] / rg
        r1, r2, r3, r4 = p["Ra"], p["Rb"], p["Ra"], p["Rb"] * (1.0 + p["eps"])
        kp = r4 / (r3 + r4)
        acm = kp * (1.0 + r2 / r1) - r2 / r1
        ad = g1 * 0.5 * (r2 / r1 + kp * (1.0 + r2 / r1))
        return ad, acm

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Vo": Cmp.zcd(p, p["Vin"])}

    @staticmethod
    def measure(p, cfg=None):
        k = int(round(p["kind"]))
        if k == 0:
            trip = _bis(lambda x: Cmp.zcd(p, x), -0.1, 0.1, 100)
            return {"trip": trip, "Vo": Cmp.zcd(p, p["Vin"]), "main": trip}
        if k == 1:
            xs, ys, dt = Cmp.peak(p)
            hi, lo = _maxv(ys), _minv(ys)
            return {"Vpk": hi, "ripple": hi - lo, "Vdc": _mean(ys), "main": hi}
        ad, acm = Cmp.ina(p, p["Rg"])
        return {"Ad": ad, "Acm": acm, "cmrr_db": 20.0 * math.log10(ad / abs(acm)), "main": acm}


def _cmp_main(p: dict) -> float:
    k = int(round(p["kind"]))
    if k == 0:
        return p["Vos"]
    if k == 1:
        return p["Vp"]
    r4 = p["Rb"] * (1.0 + p["eps"])
    kp = r4 / (p["Ra"] + r4)
    return kp * (1.0 + p["Rb"] / p["Ra"]) - p["Rb"] / p["Ra"]


# ===================================================================================================== triangle generator
class Tri(_Static):
    """A non-inverting Schmitt comparator (output +-V_sat, thresholds +-V_sat R1/R2) drives an inverting integrator of R
    and C whose output feeds the comparator back. The integrator ramps at V_sat/(RC) between the thresholds: f =
    R2/(4 R1 R C), amplitude V_sat R1/R2. The loop is stepped over two periods (exact ramps, the switch instant found
    inside the step) and the period and the amplitude are read from the sampled output."""

    PARAMS = {"R1": 10000.0, "R2": 20000.0, "R": 10000.0, "C": 1.0e-8, "Vsat": 13.0}
    VARS = ["t", "f"]
    NS = 2000

    @staticmethod
    def trace(p: dict) -> tuple[list, list, float]:
        vth = p["Vsat"] * p["R1"] / p["R2"]
        T = 4.0 * vth * p["R"] * p["C"] / p["Vsat"]
        dt = 2.0 * T / Tri.NS
        v, s = -vth, p["Vsat"]
        ys, sq = [], []
        for _ in range(Tri.NS):
            ys.append(v)
            sq.append(s)
            dv = s / (p["R"] * p["C"]) * dt
            nv = v + dv
            if s > 0 and nv >= vth:
                over = (nv - vth) / abs(dv) * dt
                s = -p["Vsat"]
                nv = vth + s / (p["R"] * p["C"]) * over
            elif s < 0 and nv <= -vth:
                over = (-vth - nv) / abs(dv) * dt
                s = p["Vsat"]
                nv = -vth + s / (p["R"] * p["C"]) * over
            v = nv
        return ys, sq, dt

    @staticmethod
    def analyse(p: dict) -> dict:
        ys, sq, dt = Tri.trace(p)
        c = _cross(ys, dt, 0.0, True)
        per = c[1] - c[0] if len(c) > 1 else 0.0
        return {"f": 1.0 / per if per > 0 else 0.0, "amp": 0.5 * (_maxv(ys) - _minv(ys))}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "f": p["R2"] / (4.0 * p["R1"] * p["R"] * p["C"])}

    @staticmethod
    def measure(p, cfg=None):
        return Tri.analyse(p)


def _tri_f(p: dict) -> float:
    return p["R2"] / (4.0 * p["R1"] * p["R"] * p["C"])


# ===================================================================================================== sweep generators
class Sweep(_Static):
    """A sweep is a capacitor voltage rising from V_lo towards an asymptote V_inf with time constant tau, reset at V_hi.
    Period T = tau ln((V_inf - V_lo)/(V_inf - V_hi)), slope (linearity) error e_s = (V_hi - V_lo)/(V_inf - V_lo).
      kind 0 RC sweep (gated at amplitude V_s): 0 -> V_s, V_inf = V, tau = RC
      kind 1 UJT with a constant-current charger: V_v -> V_p, I = (V_z - V_be)/R, V_inf = I r_o, tau = r_o C
      kind 2 UJT sawtooth (RC charger): V_v -> V_p = eta V + V_d, V_inf = V, tau = RC
      kind 3 zener sawtooth (a transistor fires at V_z + V_be and discharges to V_ce,sat): V_inf = V, tau = RC
      kind 4 bootstrap sweep (follower gain A): 0 -> V_s, V_inf = V/(1 - A), tau = RC/(1 - A)
    The waveform is sampled over two periods (retrace taken as instantaneous) and the period is read from it."""

    PARAMS = {"kind": 0.0, "V": 20.0, "R": 10000.0, "C": 1.0e-7, "Vs": 2.0, "eta": 0.6, "Vd": 0.6, "Vv": 2.0,
              "Vz": 5.6, "Vbe": 0.6, "ro": 1.0e6, "A": 0.98, "Vce": 0.2}
    VARS = ["t", "T"]
    NS = 2000

    @staticmethod
    def levels(p: dict) -> tuple[float, float, float, float]:
        k = int(round(p["kind"]))
        rc = p["R"] * p["C"]
        if k == 0:
            return 0.0, p["Vs"], p["V"], rc
        if k == 1:
            i = (p["Vz"] - p["Vbe"]) / p["R"]
            return p["Vv"], p["eta"] * p["V"] + p["Vd"], i * p["ro"], p["ro"] * p["C"]
        if k == 2:
            return p["Vv"], p["eta"] * p["V"] + p["Vd"], p["V"], rc
        if k == 3:
            return p["Vce"], p["Vz"] + p["Vbe"], p["V"], rc
        return 0.0, p["Vs"], p["V"] / (1.0 - p["A"]), rc / (1.0 - p["A"])

    @staticmethod
    def period(p: dict) -> float:
        lo, hi, vi, tau = Sweep.levels(p)
        return tau * math.log((vi - lo) / (vi - hi))

    @staticmethod
    def trace(p: dict) -> tuple[list, float]:
        lo, hi, vi, tau = Sweep.levels(p)
        T = Sweep.period(p)
        dt = 2.0 * T / Sweep.NS
        ys = []
        for i in range(Sweep.NS):
            t = i * dt
            t = t - T * math.floor(t / T)
            ys.append(vi - (vi - lo) * math.exp(-t / tau))
        return ys, dt

    @staticmethod
    def analyse(p: dict) -> dict:
        ys, dt = Sweep.trace(p)
        lo, hi, vi, tau = Sweep.levels(p)
        mid = 0.5 * (lo + hi)
        c = _cross(ys, dt, mid, True)
        per = c[1] - c[0] if len(c) > 1 else 0.0
        es = (hi - lo) / (vi - lo)
        return {"T": per, "es": es, "lo": lo, "hi": hi}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "T": Sweep.period(p)}

    @staticmethod
    def measure(p, cfg=None):
        return Sweep.analyse(p)


def _sweep_t(p: dict) -> float:
    return Sweep.period(p)


# ===================================================================================================== tuned amplifiers
class Tuned(_Static):
    """kind 0 single tuned: gain A0/sqrt(1 + x^2); kind 1 double tuned (two identical tanks coupled with k Q = kq):
    gain A0 2 kq / sqrt((1 + kq^2 - x^2)^2 + 4 x^2); x = Q (f/f0 - f0/f), f0 = 1/(2 pi sqrt(L C)) (the narrow-band
    response of a tuned stage). The centre f0 is the geometric mean of the half-power frequencies (bisection)."""

    PARAMS = {"kind": 0.0, "L": 1.0e-4, "C": 1.0e-9, "Q": 40.0, "kq": 1.0, "A0": 50.0, "f": 500000.0}
    VARS = ["t", "gain"]

    @staticmethod
    def gain(p: dict, f: float) -> float:
        f0 = 1.0 / (2.0 * PI * math.sqrt(p["L"] * p["C"]))
        x = p["Q"] * (f / f0 - f0 / f)
        if int(round(p["kind"])) == 0:
            return p["A0"] / math.sqrt(1.0 + x * x)
        kq = p["kq"]
        a = 1.0 + kq * kq - x * x
        return p["A0"] * 2.0 * kq / math.sqrt(a * a + 4.0 * x * x)

    @staticmethod
    def analyse(p: dict) -> dict:
        f0 = 1.0 / (2.0 * PI * math.sqrt(p["L"] * p["C"]))
        gm = Tuned.gain(p, f0)
        if int(round(p["kind"])) == 1 and p["kq"] > 1.0:
            gm = p["A0"]                                   # over-coupled: the humps reach A0
        lev = lambda x: Tuned.gain(p, 10.0 ** x) - gm / math.sqrt(2.0)   # noqa: E731
        x0 = math.log10(f0)
        f1 = 10.0 ** _bis(lev, x0 - 1.0, x0, 80)
        f2 = 10.0 ** _bis(lev, x0, x0 + 1.0, 80)
        return {"f0": math.sqrt(f1 * f2), "f1": f1, "f2": f2, "bw": f2 - f1, "Gmax": gm}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "gain": Tuned.gain(p, p["f"])}

    @staticmethod
    def measure(p, cfg=None):
        return Tuned.analyse(p)


def _tuned_f0(p: dict) -> float:
    return 1.0 / (2.0 * PI * math.sqrt(p["L"] * p["C"]))


# ===================================================================================================== counters
class Cnt(_Static):
    """A mod-N counter of n = ceil(log2 N) JK flip-flops (J = K = 1 for the ripple counter). kind 0 asynchronous: stage
    i toggles t_pd after stage i-1 falls (stage 0 after the clock edge), so the delay of a bit is (its position in the
    ripple + 1) t_pd; the count is cleared when it reaches N (a NAND decode, asynchronous clear). kind 1 synchronous:
    every stage clocked together, each output changes t_pd after the edge; the next-state logic resets to 0 after
    N - 1. The kernel runs 4 N clock cycles, counts the MSB's rising edges for the division ratio and records the
    largest delay after a clock edge (the MSB's, on the transition into N/2 or the highest count)."""

    PARAMS = {"kind": 0.0, "N": 10.0, "tpd": 2.5e-8, "fclk": 1.0e5}
    VARS = ["t", "mod"]

    @staticmethod
    def bits(p: dict) -> int:
        n = int(round(p["N"]))
        b = 1
        while (1 << b) < n:
            b += 1
        return b

    @staticmethod
    def run(p: dict) -> dict:
        n = int(round(p["N"]))
        nb = Cnt.bits(p)
        msb = 1 << (nb - 1)
        k = int(round(p["kind"]))
        c, edges, dmax, seq = 0, 0, 0.0, []
        for _ in range(4 * n):
            old = c
            nxt = c + 1
            if k == 1 and c == n - 1:
                nxt = 0
            if k == 0:
                ch = old ^ (nxt & ((1 << nb) - 1))
                last = 0
                for i in range(nb):
                    if (ch >> i) & 1:
                        last = i
                d = (last + 1) * p["tpd"]
                if nxt == n:
                    nxt = 0                                # cleared after the decode
            else:
                d = p["tpd"] if old != nxt else 0.0
            if (old & msb) == 0 and (nxt & msb) != 0:
                edges += 1
                if d > dmax:
                    dmax = d
            c = nxt
            if len(seq) < n:
                seq.append(c)
        return {"mod": 4.0 * n / edges if edges else 0.0, "delay": dmax, "seq": seq}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "mod": p["N"]}

    @staticmethod
    def measure(p, cfg=None):
        r = Cnt.run(p)
        return {"mod": r["mod"], "delay": r["delay"], "fout": p["fclk"] / r["mod"] if r["mod"] else 0.0}


def _cnt_mod(p: dict) -> float:
    return float(int(round(p["N"])))


# ===================================================================================================== AM / FM
class AmFm(_Static):
    """kind 0 AM: v = V_c (1 + m sin w_m t) sin w_c t, m = k_a V_m; kind 1 FM: v = V_c sin(w_c t + beta sin w_m t),
    beta = k_f V_m / f_m. One message period is sampled (f_c / f_m whole carrier cycles, 64 samples a cycle); the
    carrier and side-band lines are the sine coefficients of a DFT at f_c + n f_m (signed, so a carrier null is a sign
    change). The envelope's largest and smallest values give m; the ideal detector's output is m V_c (AM) or
    k_d k_f V_m (FM discriminator)."""

    PARAMS = {"kind": 0.0, "Vc": 2.0, "Vm": 0.5, "fc": 20000.0, "fm": 500.0, "ka": 0.4, "kf": 1500.0, "kd": 0.001}
    VARS = ["t", "m"]
    SPC = 64

    @staticmethod
    def signal(p: dict) -> tuple[list, float]:
        nc = int(round(p["fc"] / p["fm"]))
        n = nc * AmFm.SPC
        dt = 1.0 / p["fm"] / n
        y = []
        k = int(round(p["kind"]))
        for i in range(n):
            t = i * dt
            if k == 0:
                y.append(p["Vc"] * (1.0 + p["ka"] * p["Vm"] * math.sin(2.0 * PI * p["fm"] * t)) * math.sin(2.0 * PI * p["fc"] * t))
            else:
                beta = p["kf"] * p["Vm"] / p["fm"]
                y.append(p["Vc"] * math.sin(2.0 * PI * p["fc"] * t + beta * math.sin(2.0 * PI * p["fm"] * t)))
        return y, dt

    @staticmethod
    def lines(p: dict) -> list:
        y, dt = AmFm.signal(p)
        out = []
        for n in range(-3, 4):
            s, c = _sinc(y, dt, p["fc"] + n * p["fm"])
            out.append(s if int(round(p["kind"])) == 1 else _cabs(s, c))
        return out

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "m": p["ka"] * p["Vm"]}

    @staticmethod
    def measure(p, cfg=None):
        k = int(round(p["kind"]))
        ln = AmFm.lines(p)
        if k == 0:
            y, dt = AmFm.signal(p)
            hi = _maxv(y)
            lo = 0.0
            spc = AmFm.SPC
            nc = len(y) // spc
            mn = 1e9
            for j in range(nc):
                q = 0.0
                for i in range(j * spc, (j + 1) * spc):
                    if y[i] > q:
                        q = y[i]
                if q < mn:
                    mn = q
            lo = mn
            m = (hi - lo) / (hi + lo)
            return {"m": m, "usb": ln[4], "lsb": ln[2], "car": ln[3], "demod": m * p["Vc"], "main": m}
        return {"car": ln[3], "s1": ln[4], "s2": ln[5], "beta": p["kf"] * p["Vm"] / p["fm"],
                "demod": p["kd"] * p["kf"] * p["Vm"], "main": ln[3] / p["Vc"]}


def _amfm_main(p: dict) -> float:
    if int(round(p["kind"])) == 0:
        return p["ka"] * p["Vm"]
    return _j0(p["kf"] * p["Vm"] / p["fm"])


# ===================================================================================================== analog computer
class Acomp(_Static):
    """Integrators of R and C (time constant tau = RC) and summers. kind 0 falling body: -V_g into integrator 1 gives
    the velocity v = V_g t/tau; integrator 2 starts at V_0 (the height) and gives y = V_0 - V_g t^2/(2 tau^2); the
    landing time is where y = 0 (T0 = tau sqrt(2 V_0/V_g)). kind 1 simultaneous equations a1 x + b1 y = c1, a2 x + b2 y =
    c2: tau dx/dt = c1 - a1 x - b1 y, tau dy/dt = c2 - a2 x - b2 y settle at the solution. kind 2 x'' + 2 z w x' + w^2 x
    = 0 with w = 1/tau from x = V_0: the damped frequency from the zero crossings. All by RK4, fixed steps."""

    PARAMS = {"kind": 0.0, "R": 100000.0, "C": 1.0e-7, "Vg": 1.0, "V0": 5.0, "a1": 2.0, "b1": 1.0, "c1": 5.0,
              "a2": 1.0, "b2": 3.0, "c2": 10.0, "z": 0.2}
    VARS = ["t", "main"]
    NS = 1500

    @staticmethod
    def f(p: dict, k: int, s: list) -> list:
        tau = p["R"] * p["C"]
        if k == 0:
            return [p["Vg"] / tau, -s[0] / tau]
        if k == 1:
            return [(p["c1"] - p["a1"] * s[0] - p["b1"] * s[1]) / tau, (p["c2"] - p["a2"] * s[0] - p["b2"] * s[1]) / tau]
        w = 1.0 / tau
        return [s[1], -2.0 * p["z"] * w * s[1] - w * w * s[0]]

    @staticmethod
    def run(p: dict) -> tuple[list, list, float]:
        k = int(round(p["kind"]))
        tau = p["R"] * p["C"]
        span = 2.0 * tau * math.sqrt(2.0 * p["V0"] / p["Vg"]) if k == 0 else (12.0 * tau if k == 1 else 6.0 * PI * tau)
        dt = span / Acomp.NS
        s = [0.0, p["V0"]] if k == 0 else ([0.0, 0.0] if k == 1 else [p["V0"], 0.0])
        a, b = [], []
        for _ in range(Acomp.NS):
            a.append(s[0])
            b.append(s[1])
            k1 = Acomp.f(p, k, s)
            s2 = [s[0] + 0.5 * dt * k1[0], s[1] + 0.5 * dt * k1[1]]
            k2 = Acomp.f(p, k, s2)
            s3 = [s[0] + 0.5 * dt * k2[0], s[1] + 0.5 * dt * k2[1]]
            k3 = Acomp.f(p, k, s3)
            s4 = [s[0] + dt * k3[0], s[1] + dt * k3[1]]
            k4 = Acomp.f(p, k, s4)
            s = [s[0] + dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]),
                 s[1] + dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])]
        return a, b, dt

    @staticmethod
    def analyse(p: dict) -> dict:
        k = int(round(p["kind"]))
        a, b, dt = Acomp.run(p)
        if k == 0:
            c = _cross(b, dt, 0.0, False)
            t0 = c[0] if c else 0.0
            return {"T0": t0, "main": t0, "vland": p["Vg"] * t0 / (p["R"] * p["C"])}
        if k == 1:
            return {"x": a[-1], "y": b[-1], "main": a[-1]}
        c = _cross(a, dt, 0.0, False)
        per = c[1] - c[0] if len(c) > 1 else 0.0
        return {"fd": 1.0 / per if per > 0 else 0.0, "main": 1.0 / per if per > 0 else 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "main": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        return Acomp.analyse(p)


def _acomp_main(p: dict) -> float:
    k = int(round(p["kind"]))
    tau = p["R"] * p["C"]
    if k == 0:
        return tau * math.sqrt(2.0 * p["V0"] / p["Vg"])
    if k == 1:
        return (p["c1"] * p["b2"] - p["b1"] * p["c2"]) / (p["a1"] * p["b2"] - p["b1"] * p["a2"])
    return math.sqrt(1.0 - p["z"] * p["z"]) / (2.0 * PI * tau)


# ===================================================================================================== power amplifiers
class Pa(_Static):
    """kind 0 series-fed class A: collector load R_L on V_cc, biased at I_C = V_cc/(2 R_L); an ideal linear transistor
    gives i = I_C + v_d/R_L, clipped at 0 and at V_cc/R_L (cut-off and saturation). kind 1 class B push-pull on +-V_cc:
    each transistor conducts once the drive passes its V_be dead zone V_g: v_o = sign(v_d) max(|v_d| - V_g, 0), clipped
    at +-V_cc. One period of NS samples gives P_o = <v_o^2>/R_L (the a.c. part), the supply power (class A: V_cc <i>;
    class B: V_cc <|v_o|>/R_L), the efficiency and the total harmonic distortion (harmonics 2..9 by a DFT)."""

    PARAMS = {"kind": 0.0, "Vcc": 12.0, "RL": 8.0, "Vd": 3.0, "Vg": 0.6}
    VARS = ["t", "eta"]
    NS = 720

    @staticmethod
    def wave(p: dict) -> tuple[list, list]:
        k = int(round(p["kind"]))
        vo, isup = [], []
        for i in range(Pa.NS):
            vd = p["Vd"] * math.sin(2.0 * PI * i / Pa.NS)
            if k == 0:
                ic = p["Vcc"] / (2.0 * p["RL"]) + vd / p["RL"]
                ic = max(0.0, min(p["Vcc"] / p["RL"], ic))
                vo.append((ic - p["Vcc"] / (2.0 * p["RL"])) * p["RL"])
                isup.append(ic)
            else:
                a = abs(vd) - p["Vg"]
                v = a if a > 0.0 else 0.0
                v = min(v, p["Vcc"])
                v = v if vd >= 0.0 else -v
                vo.append(v)
                isup.append(abs(v) / p["RL"])
        return vo, isup

    @staticmethod
    def analyse(p: dict) -> dict:
        vo, isup = Pa.wave(p)
        n = Pa.NS
        m = 0.0
        for v in vo:
            m += v
        m /= n
        po = 0.0
        for v in vo:
            po += (v - m) * (v - m)
        po = po / n / p["RL"]
        pdc = p["Vcc"] * _mean(isup)
        h = []
        for k in range(1, 10):
            s = c = 0.0
            for i in range(n):
                th = 2.0 * PI * k * i / n
                s += vo[i] * math.sin(th)
                c += vo[i] * math.cos(th)
            h.append(_cabs(2.0 * s / n, 2.0 * c / n))
        hs = 0.0
        for k in range(1, 9):
            hs += h[k] * h[k]
        return {"Po": po, "Pdc": pdc, "eta": po / pdc if pdc > 0 else 0.0, "Vo": h[0],
                "thd": math.sqrt(hs) / h[0] if h[0] > 0 else 0.0}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "eta": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        return Pa.analyse(p)


def _pa_eta(p: dict) -> float:
    if int(round(p["kind"])) == 0:
        return (p["Vd"] / p["Vcc"]) ** 2
    return PI * p["Vd"] / (4.0 * p["Vcc"])


# ===================================================================================================== op-amp parameters
class Opp(_Static):
    """test 0 input offset voltage: non-inverting gain 1 + R_f/R_1 = 1001 (R_1 = 100 ohm, R_f = 100 kohm), inputs
    earthed: V_o = 1001 V_os + I_b R_f. test 1 bias current: a follower with 1 Mohm in series with the + input,
    V_o = V_os - I_b 1 Mohm; with the resistor shorted V_o = V_os. test 2 CMRR: a difference amplifier of gain 100 with
    both inputs at V_cm = +-5 V: dV_o = 100 dV_cm / CMRR (matched precision resistors). test 3 slew rate: a follower on
    a 10 V peak-to-peak square wave, the output edge a ramp of slope SR (10 % -> 90 %). test 4 gain-bandwidth: an
    inverting gain of 100 (noise gain 101), the -3 dB frequency f_a (1 + A0/101)."""

    PARAMS = {"test": 0.0, "Vos": 1.0e-3, "Ib": 8.0e-8, "cmrr_db": 90.0, "SR": 5.0e5, "A0": 2.0e5, "fa": 5.0,
              "f": 1000.0}
    VARS = ["t", "Vo"]

    @staticmethod
    def gain100(p: dict, f: float) -> float:
        a = _cdiv((p["A0"], 0.0), (1.0, f / p["fa"]))
        d = _cdiv((101.0, 0.0), a)
        return 100.0 / _cabs(1.0 + d[0], d[1])

    @staticmethod
    def readings(p: dict) -> dict:
        cm = 10.0 ** (p["cmrr_db"] / 20.0)
        g0 = Opp.gain100(p, 0.01)
        f3 = 10.0 ** _bis(lambda x: Opp.gain100(p, 10.0 ** x) - g0 / math.sqrt(2.0), 0.0, 9.0, 90)
        return {"vo_off": 1001.0 * p["Vos"] + p["Ib"] * 1.0e5, "vo_b0": p["Vos"], "vo_b1": p["Vos"] - p["Ib"] * 1.0e6,
                "dvo_cm": 100.0 * 10.0 / cm, "rise": 8.0 / p["SR"], "f3": f3, "g_f": Opp.gain100(p, p["f"])}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Vo": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        r = Opp.readings(p)
        r["Vos_m"] = r["vo_off"] / 1001.0
        r["Ib_m"] = (r["vo_b0"] - r["vo_b1"]) / 1.0e6
        r["cmrr_m"] = 20.0 * math.log10(100.0 * 10.0 / r["dvo_cm"])
        r["SR_m"] = 8.0 / r["rise"]
        r["gbw"] = r["f3"] * 101.0
        return r


def _opp_gbw(p: dict) -> float:
    return p["A0"] * p["fa"]


# ===================================================================================================== crystal oscillator
class Xtal(_Static):
    """Butterworth-Van Dyke crystal: motional L1, C1 (series resonance f_s = 1/(2 pi sqrt(L1 C1))) shunted by C0. In an
    oscillator with load capacitance C_L it runs at f_L = f_s (1 + C1/(2 (C0 + C_L))). An AT-cut crystal's frequency
    follows a cubic in temperature about its inflection T_i: df/f = a3 (T - T_i)^3 + a1 (T - T_i) (ppm)."""

    PARAMS = {"L1": 0.012, "C1": 2.0e-14, "C0": 5.0e-12, "CL": 2.0e-11, "T": 25.0, "Ti": 25.0, "a3": 1.0e-4,
              "a1": -0.2}
    VARS = ["t", "f"]

    @staticmethod
    def freq(p: dict, cl: float, t: float) -> float:
        fs = 1.0 / (2.0 * PI * math.sqrt(p["L1"] * p["C1"]))
        u = t - p["Ti"]
        return fs * (1.0 + p["C1"] / (2.0 * (p["C0"] + cl))) * (1.0 + 1.0e-6 * (p["a3"] * u * u * u + p["a1"] * u))

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "f": Xtal.freq(p, p["CL"], p["T"])}

    @staticmethod
    def measure(p, cfg=None):
        fs = 1.0 / (2.0 * PI * math.sqrt(p["L1"] * p["C1"]))
        return {"f": Xtal.freq(p, p["CL"], p["T"]), "fs": fs, "ppm": (Xtal.freq(p, p["CL"], p["T"]) / Xtal.freq(p, p["CL"], p["Ti"]) - 1.0) * 1e6}


def _xtal_f(p: dict) -> float:
    fs = 1.0 / (2.0 * PI * math.sqrt(p["L1"] * p["C1"]))
    u = p["T"] - p["Ti"]
    return fs * (1.0 + p["C1"] / (2.0 * (p["C0"] + p["CL"]))) * (1.0 + 1.0e-6 * (p["a3"] * u * u * u + p["a1"] * u))


# ===================================================================================================== multivibrators
class Mv(_Static):
    """tech 0 transistor, 1 IC 555, 2 op-amp; mode 0 astable, 1 monostable, 2 bistable.
      transistor astable: each half RC ln((2 V_cc - V_ce - V_be)/(V_cc - V_be)) (base swings from -(V_cc - V_ce - V_be)
        back to V_be through R), halves R1 C and R2 C; monostable: the same for R C; bistable: toggled by trigger pulses
        at f_trig, the output a square wave at f_trig / 2.
      555 astable: t_high = (R1 + R2) C ln 2, t_low = R2 C ln 2; monostable: R C ln 3; bistable (trigger and threshold
        pins on a triangle input of peak V_p): output switches at V_cc/3 and 2 V_cc/3.
      op-amp astable: T = 2 R C ln((1 + b)/(1 - b)), b = R1/(R1 + R2); monostable (clamp diode V_d): R C ln((1 + V_d/V_sat)
        /(1 - b)); bistable (Schmitt trigger): thresholds +-b V_sat.
    'main' is the period (astable), the pulse width (monostable) or the upper threshold (555 / op-amp bistable), or the
    output period (transistor bistable)."""

    PARAMS = {"tech": 0.0, "mode": 0.0, "R1": 10000.0, "R2": 22000.0, "R": 10000.0, "C": 1.0e-7, "Vcc": 9.0,
              "Vbe": 0.65, "Vce": 0.1, "Vsat": 13.0, "Vd": 0.7, "ftrig": 1000.0}
    VARS = ["t", "main"]

    @staticmethod
    def times(p: dict) -> dict:
        tech, mode = int(round(p["tech"])), int(round(p["mode"]))
        C = p["C"]
        if tech == 0:
            lg = math.log((2.0 * p["Vcc"] - p["Vce"] - p["Vbe"]) / (p["Vcc"] - p["Vbe"]))
            if mode == 0:
                a, b = p["R1"] * C * lg, p["R2"] * C * lg
                return {"main": a + b, "duty": a / (a + b), "thi": a, "tlo": b}
            if mode == 1:
                return {"main": p["R"] * C * lg, "duty": 0.0, "thi": p["R"] * C * lg, "tlo": 0.0}
            return {"main": 2.0 / p["ftrig"], "duty": 0.5, "thi": 1.0 / p["ftrig"], "tlo": 1.0 / p["ftrig"]}
        if tech == 1:
            if mode == 0:
                a, b = (p["R1"] + p["R2"]) * C * math.log(2.0), p["R2"] * C * math.log(2.0)
                return {"main": a + b, "duty": a / (a + b), "thi": a, "tlo": b}
            if mode == 1:
                return {"main": p["R"] * C * math.log(3.0), "duty": 0.0, "thi": p["R"] * C * math.log(3.0), "tlo": 0.0}
            return {"main": 2.0 * p["Vcc"] / 3.0, "duty": 0.5, "thi": 2.0 * p["Vcc"] / 3.0, "tlo": p["Vcc"] / 3.0}
        b = p["R1"] / (p["R1"] + p["R2"])
        if mode == 0:
            t = 2.0 * p["R"] * C * math.log((1.0 + b) / (1.0 - b))
            return {"main": t, "duty": 0.5, "thi": 0.5 * t, "tlo": 0.5 * t}
        if mode == 1:
            w = p["R"] * C * math.log((1.0 + p["Vd"] / p["Vsat"]) / (1.0 - b))
            return {"main": w, "duty": 0.0, "thi": w, "tlo": 0.0}
        return {"main": b * p["Vsat"], "duty": 0.5, "thi": b * p["Vsat"], "tlo": -b * p["Vsat"]}

    @staticmethod
    def trace(p: dict) -> tuple[list, list, float]:
        """A sampled output (and timing node) for the scope, from the same times."""
        tech, mode = int(round(p["tech"])), int(round(p["mode"]))
        t = Mv.times(p)
        n = 1200
        if mode == 2 and tech > 0:                         # Schmitt / 555 bistable on a triangle input
            vp = p["Vcc"] if tech == 1 else 1.5 * t["thi"]
            dt = 2.0e-3 / n
            xs, ys, hi = [], [], True
            for i in range(n):
                u = (2.0 * i / n) % 1.0
                x = vp * (2.0 * u if u < 0.5 else 2.0 - 2.0 * u) if tech == 1 else vp * (4.0 * u - 1.0 if u < 0.5 else 3.0 - 4.0 * u)
                if x >= t["thi"]:
                    hi = False
                if x <= t["tlo"]:
                    hi = True
                xs.append(x)
                ys.append((p["Vcc"] if hi else 0.0) if tech == 1 else (p["Vsat"] if hi else -p["Vsat"]))
            return xs, ys, dt
        per = t["thi"] + t["tlo"] if mode != 1 else 2.0 * t["thi"]
        dt = 3.0 * per / n
        xs, ys = [], []
        for i in range(n):
            u = (i * dt) % per
            hi = u < t["thi"]
            vtop = p["Vsat"] if tech == 2 else p["Vcc"]
            vbot = -p["Vsat"] if tech == 2 else 0.0
            ys.append(vtop if hi else vbot)
            xs.append(vtop * 0.8 if (mode == 1 and u < dt * 4) else 0.0)
        return xs, ys, dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "main": Mv.times(p)["main"]}

    @staticmethod
    def measure(p, cfg=None):
        return Mv.times(p)


def _mv_main(p: dict) -> float:
    tech, mode = int(round(p["tech"])), int(round(p["mode"]))
    if tech == 0:
        k = math.log((2.0 * p["Vcc"] - p["Vce"] - p["Vbe"]) / (p["Vcc"] - p["Vbe"]))
        return (p["R1"] + p["R2"]) * p["C"] * k if mode == 0 else (p["R"] * p["C"] * k if mode == 1 else 2.0 / p["ftrig"])
    if tech == 1:
        return (p["R1"] + 2.0 * p["R2"]) * p["C"] * math.log(2.0) if mode == 0 else (
            p["R"] * p["C"] * math.log(3.0) if mode == 1 else 2.0 * p["Vcc"] / 3.0)
    b = p["R1"] / (p["R1"] + p["R2"])
    if mode == 0:
        return 2.0 * p["R"] * p["C"] * math.log((1.0 + b) / (1.0 - b))
    if mode == 1:
        return p["R"] * p["C"] * math.log((1.0 + p["Vd"] / p["Vsat"]) / (1.0 - b))
    return b * p["Vsat"]


# ===================================================================================================== CE amplifier design
def _cm(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


class Ce(_Static):
    """Voltage-divider-biased common-emitter stage, emitter resistance split into an unbypassed Re1 (the design choice
    that sets the gain) and a bypassed Re2 (C_E). Bias: V_th = V_cc R2/(R1 + R2), R_th = R1 || R2, I_E = (V_th - V_BE) /
    (Re1 + Re2 + R_th/(beta + 1)), r_e = V_T/I_E. With Z_e = Re1 + Re2 || 1/(j w C_E), Z_b = (beta + 1)(r_e + Z_e) and
    Z_in = R_th || Z_b, the gain from the generator (through a test resistor R_x and C_in) is
        Z_in/(Z_in + R_x + 1/(j w C_in)) * alpha (R_c || R_L)/(r_e + Z_e) * j w C_o (R_c + R_L)/(1 + j w C_o (R_c + R_L))
        * 1/(1 + j w (R_c || R_L) C_x)   (C_x = C_mu + the probe's capacitance: the dominant high-frequency pole).
    The mid-band gain is read at 10 kHz, the half-power frequencies by bisection, Z_in from the drop with R_x."""

    PARAMS = {"Vcc": 12.0, "R1": 47000.0, "R2": 10000.0, "Rc": 2200.0, "RL": 10000.0, "Re1": 68.0, "Re2": 932.0,
              "beta": 200.0, "Vbe": 0.65, "Cin": 1.0e-5, "CE": 1.0e-4, "Co": 1.0e-5, "Cx": 2.4e-11, "f": 10000.0,
              "Rx": 0.0}
    VARS = ["t", "gain"]

    @staticmethod
    def bias(p: dict) -> tuple[float, float, float]:
        vth = p["Vcc"] * p["R2"] / (p["R1"] + p["R2"])
        rth = p["R1"] * p["R2"] / (p["R1"] + p["R2"])
        ie = (vth - p["Vbe"]) / (p["Re1"] + p["Re2"] + rth / (p["beta"] + 1.0))
        return ie, VT / ie, rth

    @staticmethod
    def h(p: dict, f: float, rx: float) -> tuple[float, float]:
        ie, re, rth = Ce.bias(p)
        w = 2.0 * PI * f
        zce = _cdiv((1.0, 0.0), (0.0, w * p["CE"]))
        ze2 = _cdiv(_cm((p["Re2"], 0.0), zce), (p["Re2"] + zce[0], zce[1]))
        ze = (p["Re1"] + ze2[0], ze2[1])
        zb = ((p["beta"] + 1.0) * (re + ze[0]), (p["beta"] + 1.0) * ze[1])
        zin = _cdiv(_cm((rth, 0.0), zb), (rth + zb[0], zb[1]))
        cin = _cdiv((1.0, 0.0), (0.0, w * p["Cin"]))
        div = _cdiv(zin, (zin[0] + rx + cin[0], zin[1] + cin[1]))
        rp = p["Rc"] * p["RL"] / (p["Rc"] + p["RL"])
        alpha = p["beta"] / (p["beta"] + 1.0)
        av = _cdiv((alpha * rp, 0.0), (re + ze[0], ze[1]))
        to = w * p["Co"] * (p["Rc"] + p["RL"])
        ho = _cdiv((0.0, to), (1.0, to))
        hh = _cdiv((1.0, 0.0), (1.0, w * rp * p["Cx"]))
        return _cm(_cm(div, av), _cm(ho, hh))

    @staticmethod
    def gain(p: dict, f: float, rx: float) -> float:
        a = Ce.h(p, f, rx)
        return _cabs(a[0], a[1])

    @staticmethod
    def analyse(p: dict) -> dict:
        am = Ce.gain(p, 10000.0, 0.0)
        lev = lambda x: Ce.gain(p, 10.0 ** x, 0.0) - am / math.sqrt(2.0)   # noqa: E731
        fl = 10.0 ** _bis(lev, -1.0, 4.0, 80)
        fh = 10.0 ** _bis(lev, 4.0, 9.0, 80)
        g1 = Ce.gain(p, 10000.0, 1000.0)
        return {"Amid": am, "fL": fl, "fH": fh, "Zin": 1000.0 * g1 / (am - g1)}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "gain": Ce.gain(p, p["f"], p["Rx"])}

    @staticmethod
    def measure(p, cfg=None):
        return Ce.analyse(p)


def _ce_amid(p: dict) -> float:
    ie, re, rth = Ce.bias(p)
    rp = p["Rc"] * p["RL"] / (p["Rc"] + p["RL"])
    return p["beta"] / (p["beta"] + 1.0) * rp / (re + p["Re1"])


# ===================================================================================================== registry
KERNELS: dict[str, Any] = {
    "pe9_reg": Reg, "pe9_conv": Conv, "pe9_filt": Filt, "pe9_lcr": Lcr, "pe9_opl": Opl, "pe9_intdiff": IntDiff,
    "pe9_cmp": Cmp, "pe9_tri": Tri, "pe9_sweep": Sweep, "pe9_tuned": Tuned, "pe9_cnt": Cnt, "pe9_amfm": AmFm,
    "pe9_acomp": Acomp, "pe9_pa": Pa, "pe9_opp": Opp, "pe9_xtal": Xtal, "pe9_mv": Mv, "pe9_ce": Ce,
}
FAMILY = {k: "circuit" for k in KERNELS}
TEXTBOOK = {
    "pe9_reg_line": _reg_line, "pe9_conv_main": _conv_main, "pe9_filt_fc": _filt_fc, "pe9_lcr_fr": _lcr_fr,
    "pe9_lcr_q": _lcr_q, "pe9_opl_gain": _opl_gain, "pe9_intdiff_rc": _intdiff_rc, "pe9_cmp_main": _cmp_main,
    "pe9_tri_f": _tri_f, "pe9_sweep_t": _sweep_t, "pe9_tuned_f0": _tuned_f0, "pe9_cnt_mod": _cnt_mod,
    "pe9_amfm_main": _amfm_main, "pe9_acomp_main": _acomp_main, "pe9_pa_eta": _pa_eta, "pe9_opp_gbw": _opp_gbw,
    "pe9_xtal_f": _xtal_f, "pe9_mv_main": _mv_main, "pe9_ce_amid": _ce_amid,
}
CALCS: dict[str, dict] = {}
