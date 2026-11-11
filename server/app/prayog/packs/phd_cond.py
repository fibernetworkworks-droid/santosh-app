"""Kernel pack `phd_cond`: research-level condensed-matter benches - low temperature and superconductivity, quantum
transport, magnetic resonance and hyperfine methods. Exact JavaScript twin: `app/static/prayog/packs/phd_cond.js`
(the test suite runs both and demands the same numbers). Every kernel and every TEXTBOOK / CALCS key starts `phd_`.

Honest limits, said again in each lab: SQUIDs, a dilution refrigerator, a Josephson junction, a quantum Hall sample, a
tunnel junction and a Moessbauer spectrometer are SIMULATED INSTRUMENTS here. Their numbers come from the published
model named in each lab's sources (RSJ model, Ambegaokar-Baratoff, HLN weak localisation, Lifshitz-Kosevich, BCS density
of states, Bloch equations, ...), never from a real device. Deterministic: noise is a hash of a lab parameter (seed).
Constants are SI 2019 / CODATA; material numbers live in lab or family files and are marked sourced or illustrative.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
H = 6.62607015e-34
HBAR = H / (2 * PI)
QE = 1.602176634e-19
KB = 1.380649e-23
MUB = 9.2740100783e-24
MUN = 5.0507837461e-27
ME = 9.1093837015e-31
MU0 = 1.25663706212e-6
NA = 6.02214076e23
CLIGHT = 299792458.0
PHI0 = H / (2 * QE)
RK = H / (QE * QE)
KJ = 2 * QE / H


def _hash(seed: float, k: float) -> float:
    """Deterministic pseudo-noise in [-1, 1) from a lab parameter and an index (same arithmetic in the JS twin)."""
    x = math.sin(seed * 12.9898 + k * 78.233) * 43758.5453
    return 2.0 * (x - math.floor(x)) - 1.0


def _line(pts):
    n = len(pts)
    if n < 2:
        return 0.0, 0.0
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    d = n * sxx - sx * sx
    if d == 0:
        return 0.0, 0.0
    m = (n * sxy - sx * sy) / d
    return m, (sy - m * sx) / n


def _rows(rows, keys):
    out = []
    for r in rows or []:
        vals = []
        ok = True
        for k in keys:
            v = r.get(k)
            try:
                f = float(v)
            except (TypeError, ValueError):
                ok = False
                break
            if not math.isfinite(f):
                ok = False
                break
            vals.append(f)
        if ok:
            out.append(vals)
    return out


class _Base:
    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


def _sech2(x: float) -> float:
    e = math.exp(-2.0 * abs(x))
    return 4.0 * e / ((1.0 + e) * (1.0 + e))


def _digamma(x: float) -> float:
    r = 0.0
    while x < 8.0:
        r -= 1.0 / x
        x += 1.0
    x2 = 1.0 / (x * x)
    return r + math.log(x) - 0.5 / x - x2 * (1.0 / 12 - x2 * (1.0 / 120 - x2 * (1.0 / 252 - x2 * (1.0 / 240))))


# ============================================================================ superconductor R(T), four-probe
class ScRT(_Base):
    """Four-probe R(T) of a superconducting bar: R = Rn(T) * (1 + tanh((T - Tc(B))/w))/2 with a linear normal state
    Rn = Rres + a T and Tc(B) = Tc0 [1 - (B/Bc2)^2] (the usual parabolic phase boundary)."""

    PARAMS = {"T": 100.0, "B": 0.0, "Tc0": 92.0, "Bc2": 120.0, "w": 0.6, "Rres": 0.02, "a": 0.0004, "I": 0.001}
    VARS = ["t", "R", "V", "T"]

    @staticmethod
    def tc(p):
        return p["Tc0"] * (1.0 - (p["B"] / p["Bc2"]) ** 2)

    @staticmethod
    def rn(p, T):
        return p["Rres"] + p["a"] * T

    @staticmethod
    def res(p, T=None):
        T = p["T"] if T is None else T
        return ScRT.rn(p, T) * 0.5 * (1.0 + math.tanh((T - ScRT.tc(p)) / p["w"]))

    @staticmethod
    def view(s, p, cfg=None):
        r = ScRT.res(p)
        return {"t": s.get("t", 0.0), "R": r, "V": r * p["I"], "T": p["T"]}

    @staticmethod
    def measure(p, cfg=None):
        """Tc as the temperature where R has fallen to half the extrapolated normal-state value (bisection), and the
        residual resistance ratio R(300 K) / Rn(0)."""
        lo, hi = 1.0, 3.0 * p["Tc0"]
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if ScRT.res(p, mid) / ScRT.rn(p, mid) < 0.5:
                lo = mid
            else:
                hi = mid
        # normal-state line from two readings well above the transition
        t1, t2 = hi + 20 * p["w"] + 5.0, hi + 20 * p["w"] + 55.0
        r1, r2 = ScRT.res(p, t1), ScRT.res(p, t2)
        m = (r2 - r1) / (t2 - t1)
        r0 = r1 - m * t1
        return {"Tc": 0.5 * (lo + hi), "RRR": ScRT.res(p, 300.0) / r0 if r0 > 0 else 0.0, "R": ScRT.res(p)}


def _scrt_Tc(p):
    return ScRT.tc(p)


# ============================================================================ critical current
class ScIc(_Base):
    """Transport I-V of a superconducting bridge: E = Ec (I/Ic)^n, so V = Vc (I/Ic)^n with Vc = Ec L (Ec = 1 uV/cm).
    Ic(T, B) = Ic0 [1 - (T/Tc)^2]^1.5 / (1 + B/B0) (Ginzburg-Landau-like T law, Kim-model field law: empirical)."""

    PARAMS = {"I": 0.5, "T": 20.0, "B": 0.0, "Tc": 92.0, "Ic0": 2.0, "B0": 1.0, "n": 15.0, "Lv": 0.002, "Ec": 1e-4,
              "area": 1.0e-9}
    VARS = ["t", "V", "I", "Ic"]

    @staticmethod
    def ic(p):
        t = p["T"] / p["Tc"]
        return 0.0 if t >= 1 else p["Ic0"] * (1.0 - t * t) ** 1.5 / (1.0 + p["B"] / p["B0"])

    @staticmethod
    def volts(p, I=None):
        I = p["I"] if I is None else I
        ic = ScIc.ic(p)
        return 0.0 if ic <= 0 or I <= 0 else p["Ec"] * p["Lv"] * (I / ic) ** p["n"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "V": ScIc.volts(p), "I": p["I"], "Ic": ScIc.ic(p)}

    @staticmethod
    def measure(p, cfg=None):
        """Ic by the voltage criterion Vc = Ec L (bisection on the I-V curve), Jc = Ic / area."""
        vc = p["Ec"] * p["Lv"]
        lo, hi = 0.0, 10.0 * max(ScIc.ic(p), 1e-12)
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if ScIc.volts(p, mid) < vc:
                lo = mid
            else:
                hi = mid
        ic = 0.5 * (lo + hi)
        return {"Ic": ic, "Jc": ic / p["area"], "V": ScIc.volts(p)}


def _scic_Ic(p):
    return ScIc.ic(p)


# ============================================================================ Meissner effect, mutual inductance
class AcSusc(_Base):
    """Two-coil mutual-inductance susceptibility of a superconducting sphere of radius a. Shielded volume fraction
    f = 1 - (1 - lam/a)^3 with the London depth lam(T) = lam0 / sqrt(1 - (T/Tc)^4) (Gorter-Casimir) and
    lam0 = sqrt(m / (mu0 ns e^2)). chi' = -f S(T), S the sharp transition; chi'' = chi2 sech^2 peaks at Tc."""

    PARAMS = {"T": 50.0, "Tc": 92.0, "w": 0.5, "a": 1.0e-6, "ns": 2.0e28, "chi2": 0.12}
    VARS = ["t", "chi1", "chi2", "T"]

    @staticmethod
    def lam0(p):
        return math.sqrt(ME / (MU0 * p["ns"] * QE * QE))

    @staticmethod
    def lam(p, T):
        t = T / p["Tc"]
        return AcSusc.lam0(p) / math.sqrt(1.0 - t ** 4) if t < 1 else 1e30

    @staticmethod
    def chi1(p, T=None):
        T = p["T"] if T is None else T
        x = min(AcSusc.lam(p, T) / p["a"], 1.0)
        f = 1.0 - (1.0 - x) ** 3
        return -f * 0.5 * (1.0 - math.tanh((T - p["Tc"]) / p["w"]))

    @staticmethod
    def chi2(p, T=None):
        T = p["T"] if T is None else T
        return p["chi2"] * _sech2((T - p["Tc"]) / p["w"])

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "chi1": AcSusc.chi1(p), "chi2": AcSusc.chi2(p), "T": p["T"]}

    @staticmethod
    def measure(p, cfg=None):
        """lam0 from the low-temperature plateau (T = 0.05 Tc) of chi': 1 - f = (1 - lam/a)^3. Tc from the peak of
        chi'' on a 0.01 K grid, refined by a parabola."""
        T0 = 0.05 * p["Tc"]
        f = -AcSusc.chi1(p, T0)
        lam = p["a"] * (1.0 - (1.0 - f) ** (1.0 / 3.0))
        lam0 = lam * math.sqrt(1.0 - 0.05 ** 4)
        n = int(p["Tc"] * 0.2 / 0.01)
        best, bt = -1.0, 0.0
        t0 = 0.9 * p["Tc"]
        for i in range(2 * n + 1):
            t = t0 + 0.01 * i
            c = AcSusc.chi2(p, t)
            if c > best:
                best, bt = c, t
        a, b, c = AcSusc.chi2(p, bt - 0.01), best, AcSusc.chi2(p, bt + 0.01)
        d = a - 2 * b + c
        tc = bt + (0.01 * 0.5 * (a - c) / d if d != 0 else 0.0)
        return {"lam0": lam0, "Tc": tc, "f": f}


def _acsusc_lam0(p):
    return math.sqrt(ME / (MU0 * p["ns"] * QE * QE))


# ============================================================================ cryogenic thermometers
CVD_A, CVD_B, CVD_C = 3.9083e-3, -5.775e-7, -4.183e-12     # IEC 60751
DIODE_EG = 1.17      # eV, Si extrapolated to 0 K (Sze)


class Therm(_Base):
    """A thermometer at bath temperature T. sensor 1 silicon diode (ideal diode at constant current), 2 platinum RTD
    (IEC 60751 Callendar-Van Dusen), 3 RuO2 thick-film resistor (variable-range hopping R = R0 exp(sqrt(T0/T))),
    4 thermocouple (illustrative Seebeck law). Self-heating P / G raises the sensor above the bath."""

    PARAMS = {"T": 77.0, "sensor": 1.0, "I": 1.0e-5, "G": 1.0e-3, "R0": 100.0, "Rinf": 1000.0, "T0": 20.0,
              "s0": 40.0e-6, "Tk": 60.0, "Tref": 300.0}
    VARS = ["t", "X", "T", "dTheat"]

    @staticmethod
    def _cs(p):
        i0, t0, v0 = 1.0e-5, 300.0, 0.6
        return i0 / (t0 ** 3) * math.exp(-(v0 - DIODE_EG) * QE / (KB * t0))

    @staticmethod
    def bare(p, T):
        k = int(round(p["sensor"]))
        if k == 1:
            return DIODE_EG + (KB * T / QE) * (math.log(p["I"] / Therm._cs(p)) - 3.0 * math.log(T))
        if k == 2:
            t = T - 273.15
            c = CVD_C * (t - 100.0) * t ** 3 if t < 0 else 0.0
            return p["R0"] * (1.0 + CVD_A * t + CVD_B * t * t + c)
        if k == 3:
            return p["Rinf"] * math.exp(math.sqrt(p["T0"] / T))
        return p["s0"] * ((T - p["Tref"]) - p["Tk"] * math.log((T + p["Tk"]) / (p["Tref"] + p["Tk"])))

    @staticmethod
    def power(p, T):
        k = int(round(p["sensor"]))
        x = Therm.bare(p, T)
        if k == 1:
            return p["I"] * x
        if k in (2, 3):
            return p["I"] * p["I"] * x
        return 0.0

    @staticmethod
    def dtheat(p, T=None):
        T = p["T"] if T is None else T
        return Therm.power(p, T) / p["G"]

    @staticmethod
    def read(p, T=None):
        T = p["T"] if T is None else T
        return Therm.bare(p, T + Therm.dtheat(p, T))

    @staticmethod
    def slope_exact(p, T):
        k = int(round(p["sensor"]))
        if k == 1:
            return (Therm.bare(p, T) - DIODE_EG) / T - 3.0 * KB / QE
        if k == 2:
            t = T - 273.15
            d = CVD_A + 2 * CVD_B * t
            if t < 0:
                d += CVD_C * (4.0 * t ** 3 - 300.0 * t ** 2)
            return p["R0"] * d
        if k == 3:
            return -Therm.bare(p, T) * 0.5 * math.sqrt(p["T0"]) / (T ** 1.5)
        return p["s0"] * T / (T + p["Tk"])

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "X": Therm.read(p), "T": p["T"], "dTheat": Therm.dtheat(p)}

    @staticmethod
    def measure(p, cfg=None):
        """Sensitivity dX/dT by a calibration at T - 1 K and T + 1 K (what the student does), self-heating in."""
        a, b = Therm.read(p, p["T"] - 1.0), Therm.read(p, p["T"] + 1.0)
        return {"S": (b - a) / 2.0, "X": Therm.read(p), "dTheat": Therm.dtheat(p)}


def _therm_S(p):
    return Therm.slope_exact(p, p["T"])


# ============================================================================ Josephson junction (RSJ model)
class Josephson(_Base):
    """Resistively shunted junction, dphi/dtau = i + irf sin(Omega tau) - sin phi (time in hbar/(2e Ic Rn), current in
    Ic). The tunnel junction (normal resistance Rn) has Ic Rn = pi Delta tanh(Delta/2kT) / (2e) (Ambegaokar-Baratoff);
    an on-chip shunt Rs << Rn makes it overdamped, so the voltage scale is Ic Rs. The mean voltage over whole drive
    periods is <dphi/dtau> Ic Rs; with microwaves it locks to V = n h f / 2e (Shapiro steps)."""

    PARAMS = {"I": 0.0, "Delta": 1.4e-3, "Tb": 4.2, "Rn": 2.0, "Rs": 0.04, "f": 16.0e9, "Irf": 4.2e-4, "rf": 0.0}
    VARS = ["t", "V", "I", "Ic"]

    @staticmethod
    def icrn(p):
        return PI * p["Delta"] / 2.0 * math.tanh(p["Delta"] * QE / (2.0 * KB * p["Tb"]))   # volts (Delta in eV)

    @staticmethod
    def ic(p):
        return Josephson.icrn(p) / p["Rn"]

    @staticmethod
    def omega(p):
        return H * p["f"] / (2.0 * QE * Josephson.ic(p) * p["Rs"])

    @staticmethod
    def volts(p, I=None, rf=None, nper=40, skip=30, spp=40):
        """Mean voltage (V) at bias I by RK4 integration over whole drive periods."""
        I = p["I"] if I is None else I
        rf = p["rf"] if rf is None else rf
        i = I / Josephson.ic(p)
        irf = (p["Irf"] / Josephson.ic(p)) if rf > 0.5 else 0.0
        om = Josephson.omega(p)
        if irf == 0.0:
            dt = 0.05
            phi, n = 0.0, 0
            tot = 0.0
            nsteps = 12000
            for k in range(nsteps):
                k1 = i - math.sin(phi)
                k2 = i - math.sin(phi + 0.5 * dt * k1)
                k3 = i - math.sin(phi + 0.5 * dt * k2)
                k4 = i - math.sin(phi + dt * k3)
                d = dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
                phi += d
                if k >= nsteps // 2:
                    tot += d
                    n += 1
            return tot / (n * dt) * Josephson.ic(p) * p["Rs"]
        per = 2.0 * PI / om
        dt = per / spp
        phi, t, tot = 0.0, 0.0, 0.0

        def fn(tt, ph):
            return i + irf * math.sin(om * tt) - math.sin(ph)
        for k in range((nper + skip) * spp):
            k1 = fn(t, phi)
            k2 = fn(t + 0.5 * dt, phi + 0.5 * dt * k1)
            k3 = fn(t + 0.5 * dt, phi + 0.5 * dt * k2)
            k4 = fn(t + dt, phi + dt * k3)
            d = dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
            phi += d
            t += dt
            if k >= skip * spp:
                tot += d
        return tot / (nper * per) * Josephson.ic(p) * p["Rs"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "V": Josephson.volts(p, p["I"], p["rf"], 4, 4, 20), "I": p["I"], "Ic": Josephson.ic(p)}

    @staticmethod
    def measure(p, cfg=None):
        """V1 = voltage on the first Shapiro step (bias in the middle of the plateau, microwaves on)."""
        ic = Josephson.ic(p)
        v1 = Josephson.volts(p, math.sqrt(1.0 + Josephson.omega(p) ** 2) * ic, 1.0)
        return {"V1": v1, "Ic": ic, "f": 2.0 * QE * v1 / H}


def _jj_f(p):
    return p["f"]


# ============================================================================ DC SQUID
class DcSquid(_Base):
    """Symmetric DC SQUID in the zero-inductance limit, overdamped junctions: Ic(Phi) = 2 I0 |cos(pi Phi/Phi0)| and
    V = (Rn/2) sqrt(Ib^2 - Ic^2) for Ib > Ic (Clarke and Braginski). Flux Phi = Mi Icoil + Phi_off."""

    PARAMS = {"Icoil": 0.0, "I0": 10.0e-6, "Rn": 4.0, "Ib": 24.0e-6, "Mi": 2.0e-10, "Poff": 0.1, "vn": 0.0, "seed": 3.0}
    VARS = ["t", "V", "Icoil", "Phi"]

    @staticmethod
    def volts(p, ic_coil=None):
        ic_coil = p["Icoil"] if ic_coil is None else ic_coil
        phi = p["Mi"] * ic_coil + p["Poff"] * PHI0
        ic = 2.0 * p["I0"] * abs(math.cos(PI * phi / PHI0))
        return 0.5 * p["Rn"] * math.sqrt(p["Ib"] ** 2 - ic ** 2) if p["Ib"] > ic else 0.0

    @staticmethod
    def noisy(p, ic_coil, k):
        return DcSquid.volts(p, ic_coil) + p["vn"] * _hash(p["seed"], k)

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "V": DcSquid.volts(p), "Icoil": p["Icoil"], "Phi": (p["Mi"] * p["Icoil"] + p["Poff"] * PHI0) / PHI0}

    @staticmethod
    def measure(p, cfg=None):
        """Period of V against coil current from the maxima of a fine trace over four periods, then
        Phi0 = Mi x period; modulation depth and transfer function VPhi (maximum slope)."""
        per0 = PHI0 / p["Mi"]
        n = 800
        xs = [(-1.0 + 4.0 * i / n) * per0 for i in range(n + 1)]
        vs = [DcSquid.volts(p, x) for x in xs]
        pk = []
        for i in range(1, n):
            if vs[i] > vs[i - 1] and vs[i] >= vs[i + 1]:
                a, b, c = vs[i - 1], vs[i], vs[i + 1]
                d = a - 2 * b + c
                pk.append(xs[i] + ((xs[1] - xs[0]) * 0.5 * (a - c) / d if d != 0 else 0.0))
        per = (pk[-1] - pk[0]) / (len(pk) - 1) if len(pk) > 1 else 0.0
        vmax, vmin = max(vs), min(vs)
        slope = 0.0
        dphi = (xs[1] - xs[0]) * p["Mi"] / PHI0
        for i in range(1, n):
            slope = max(slope, abs(vs[i + 1] - vs[i - 1]) / (2.0 * dphi))
        return {"Phi0": p["Mi"] * per, "dV": vmax - vmin, "VPhi": slope}


def _squid_Phi0(p):
    return PHI0


# ============================================================================ integer quantum Hall (simulated)
class Qhe(_Base):
    """Two-dimensional electron gas, density n: filling nu = n h / (e B). rho_xy = h / (nu_eff e^2) with nu_eff a
    staircase of tanh steps (width w = w0 + a T in nu), rho_xx = rho0 + peaks at half-integer filling. An illustrative
    broadening model: the plateau VALUES are exact (h / i e^2), the shapes are not a real sample."""

    PARAMS = {"B": 6.0, "n": 3.0e15, "T": 1.5, "w0": 0.05, "wT": 0.012, "rho0": 5.0, "rhop": 0.4}
    VARS = ["t", "rxy", "rxx", "B"]

    @staticmethod
    def nu(p, B=None):
        B = p["B"] if B is None else B
        return p["n"] * H / (QE * B)

    @staticmethod
    def width(p):
        return p["w0"] + p["wT"] * p["T"]

    @staticmethod
    def nueff(p, B=None):
        nu = Qhe.nu(p, B)
        w = Qhe.width(p)
        s = 0.0
        for k in range(1, 61):
            s += 0.5 * (1.0 + math.tanh((nu - (k - 0.5)) / w))
        return s

    @staticmethod
    def rxy(p, B=None):
        B = p["B"] if B is None else B
        ne = Qhe.nueff(p, B)
        return RK / ne if ne > 1e-9 else 1e9

    @staticmethod
    def rxx(p, B=None):
        B = p["B"] if B is None else B
        nu = Qhe.nu(p, B)
        w = Qhe.width(p)
        s = 0.0
        for k in range(1, 61):
            s += _sech2((nu - (k - 0.5)) / w)
        return p["rho0"] + p["rhop"] * RK / max(nu, 1.0) * s

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "rxy": Qhe.rxy(p), "rxx": Qhe.rxx(p), "B": p["B"]}

    @staticmethod
    def measure(p, cfg=None):
        """The nu = 2 plateau value x 2 = h/e^2: the B near n h/(2e) (+-15 %) where rho_xy is flattest."""
        b2 = p["n"] * H / (2.0 * QE)
        best, bb = 1e300, b2
        for i in range(-60, 61):
            b = b2 * (1.0 + 0.15 * i / 60.0)
            d = abs(Qhe.rxy(p, b * 1.001) - Qhe.rxy(p, b * 0.999))
            if d < best:
                best, bb = d, b
        return {"RK": 2.0 * Qhe.rxy(p, bb), "B2": bb, "n": 0.0}


def _qhe_RK(p):
    return RK


# ============================================================================ Shubnikov-de Haas
class Sdh(_Base):
    """rho_xx of a 2DEG with spin-degenerate Landau levels (Lifshitz-Kosevich):
    rho = rho0 [1 + 2 exp(-pi/(muq B)) X/sinh X cos(2 pi F/B + pi)], F = n h/(2e), X = 2 pi^2 kB T m*/(hbar e B)."""

    PARAMS = {"B": 5.0, "n": 3.0e15, "T": 1.5, "mstar": 0.067, "muq": 3.0, "rho0": 50.0}
    VARS = ["t", "rho", "B", "F"]

    @staticmethod
    def F(p):
        return p["n"] * H / (2.0 * QE)

    @staticmethod
    def amp(p, B=None, T=None):
        B = p["B"] if B is None else B
        T = p["T"] if T is None else T
        x = 2.0 * PI * PI * KB * T * p["mstar"] * ME / (HBAR * QE * B)
        return 2.0 * math.exp(-PI / (p["muq"] * B)) * (x / math.sinh(x) if x > 1e-9 else 1.0)

    @staticmethod
    def rho(p, B=None, T=None):
        B = p["B"] if B is None else B
        return p["rho0"] * (1.0 + Sdh.amp(p, B, T) * math.cos(2.0 * PI * Sdh.F(p) / B + PI))

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "rho": Sdh.rho(p), "B": p["B"], "F": Sdh.F(p)}

    @staticmethod
    def measure(p, cfg=None):
        """n from the 1/B spacing of the maxima of rho_xx over 0.8 T - 12 T, spin degeneracy 2."""
        n = 3000
        x0, x1 = 1.0 / 12.0, 1.0 / 0.8
        xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
        ys = [Sdh.rho(p, 1.0 / x) for x in xs]
        pk = []
        dx = xs[1] - xs[0]
        for i in range(1, n):
            if ys[i] > ys[i - 1] and ys[i] >= ys[i + 1]:
                a, b, c = ys[i - 1], ys[i], ys[i + 1]
                d = a - 2 * b + c
                pk.append(xs[i] + (dx * 0.5 * (a - c) / d if d != 0 else 0.0))
        m, c0 = _line([[float(i), v] for i, v in enumerate(pk)]) if len(pk) > 2 else (0.0, 0.0)
        return {"n": 2.0 * QE / (H * m) if m > 0 else 0.0, "peaks": float(len(pk)), "F": Sdh.F(p)}


def _sdh_n(p):
    return p["n"]


# ============================================================================ weak localisation (HLN)
class WeakLoc(_Base):
    """2-D weak localisation magnetoconductance (Hikami-Larkin-Nagaoka, strong spin-orbit absent):
    ds(B) = (e^2 / (pi h)) [psi(1/2 + Bphi/B) - ln(Bphi/B)], Bphi = hbar / (4 e Lphi^2), Lphi = L1 T^(-pexp/2) (T in K)."""

    PARAMS = {"B": 0.01, "T": 2.0, "L1": 1.0e-6, "pexp": 1.0, "noise": 0.0, "seed": 5.0}
    VARS = ["t", "ds", "B", "Bphi"]

    @staticmethod
    def Lphi(p):
        return p["L1"] * p["T"] ** (-0.5 * p["pexp"])

    @staticmethod
    def Bphi(p):
        return HBAR / (4.0 * QE * WeakLoc.Lphi(p) ** 2)

    @staticmethod
    def ds(p, B=None, bphi=None):
        B = p["B"] if B is None else B
        bphi = WeakLoc.Bphi(p) if bphi is None else bphi
        x = bphi / B
        return (QE * QE / (PI * H)) * (_digamma(0.5 + x) - math.log(x))

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "ds": WeakLoc.ds(p), "B": p["B"], "Bphi": WeakLoc.Bphi(p)}

    @staticmethod
    def fit(pts):
        """Least-squares Bphi (tesla) over a log grid refined twice; pts = [[B, ds]]."""
        def sse(bp):
            s = 0.0
            for b, d in pts:
                e = d - (QE * QE / (PI * H)) * (_digamma(0.5 + bp / b) - math.log(bp / b))
                s += e * e
            return s
        lo, hi = 1e-6, 1.0
        for _ in range(4):
            best, bb = 1e300, lo
            for i in range(41):
                bp = lo * (hi / lo) ** (i / 40.0)
                v = sse(bp)
                if v < best:
                    best, bb = v, bp
            r = (hi / lo) ** (1.0 / 40.0)
            lo, hi = bb / r, bb * r
        return 0.5 * (lo + hi)

    @staticmethod
    def measure(p, cfg=None):
        bp = WeakLoc.Bphi(p)
        pts = [[bp * m, WeakLoc.ds(p, bp * m)] for m in (0.05, 0.1, 0.2, 0.4, 0.7, 1.0, 1.5, 2.5, 4.0, 6.0)]
        fb = WeakLoc.fit(pts)
        return {"Bphi": fb, "Lphi": math.sqrt(HBAR / (4.0 * QE * fb))}


def _wl_Lphi(p):
    return WeakLoc.Lphi(p)


# ============================================================================ NIS tunnelling (Giaever)
class Tunnel(_Base):
    """Normal-metal / superconductor tunnel junction, conductance Gn: I(V) = (Gn/e) int_Delta^inf N(E) [f(E-eV) -
    f(E+eV)] dE with the BCS density of states N = E / sqrt(E^2 - Delta^2); Delta(T) = Delta0 tanh(1.74 sqrt(Tc/T - 1)),
    Delta0 = 1.764 kB Tc. The integral uses E = Delta cosh u (no singularity)."""

    PARAMS = {"V": 0.0, "Tc": 1.2, "T": 0.1, "Gn": 1.0e-3}
    VARS = ["t", "I", "V", "Delta"]

    @staticmethod
    def gap(p):
        if "_gap" in p:
            return p["_gap"]
        t = p["T"]
        if t >= p["Tc"]:
            return 0.0
        return 1.764 * KB * p["Tc"] * math.tanh(1.74 * math.sqrt(p["Tc"] / t - 1.0))

    @staticmethod
    def cur(p, V=None):
        V = p["V"] if V is None else V
        d = Tunnel.gap(p)
        kt = KB * p["T"]
        ev = QE * V
        if d <= 0:
            return p["Gn"] * V
        umax = math.acosh(max((abs(ev) + 40.0 * kt) / d, 1.0) + 1.0)
        n = 400
        h = umax / n
        s = 0.0
        for i in range(n + 1):
            u = i * h
            e = d * math.cosh(u)
            x1 = (e - ev) / kt
            x2 = (e + ev) / kt
            f1 = 0.0 if x1 > 700 else 1.0 / (math.exp(x1) + 1.0)
            f2 = 0.0 if x2 > 700 else 1.0 / (math.exp(x2) + 1.0)
            wgt = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
            s += wgt * e * (f1 - f2)
        return p["Gn"] / QE * s * h / 3.0

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": Tunnel.cur(p), "V": p["V"], "Delta": Tunnel.gap(p)}

    @staticmethod
    def fit(pts, p):
        """Gap (eV) by fitting I(V) of the BCS model to the measured points [[V, I]] at the known T (golden search
        on Delta, sum of squared residuals in units of Gn Delta0 / e)."""
        d0 = 1.764 * KB * p["Tc"]
        sc = p["Gn"] * d0 / QE

        def sse(d):
            q = dict(p)
            q["_gap"] = d
            s2 = 0.0
            for v, i in pts:
                e = (Tunnel.cur(q, v) - i) / sc
                s2 += e * e
            return s2
        lo, hi = 0.5 * d0, 1.5 * d0
        g = (math.sqrt(5.0) - 1.0) / 2.0
        a, b = hi - g * (hi - lo), lo + g * (hi - lo)
        fa, fb = sse(a), sse(b)
        for _ in range(40):
            if fa < fb:
                hi, b, fb = b, a, fa
                a = hi - g * (hi - lo)
                fa = sse(a)
            else:
                lo, a, fa = a, b, fb
                b = lo + g * (hi - lo)
                fb = sse(b)
        return 0.5 * (lo + hi) / QE

    @staticmethod
    def measure(p, cfg=None):
        d0 = Tunnel.gap(p)
        pts = [[d0 / QE * m, Tunnel.cur(p, d0 / QE * m)] for m in (0.6, 0.9, 1.0, 1.05, 1.1, 1.2, 1.4, 1.8, 2.4)]
        d = Tunnel.fit(pts, p)
        return {"Delta": d, "Gap": d}


def _tun_gap(p):
    return 1.764 * KB * p["Tc"] / QE


# ============================================================================ NMR (Bloch equations)
class Bloch(_Base):
    """Pulsed NMR of a spin-1/2 sample. Larmor omega = gamma B; probe resonance is a Lorentzian in the RF frequency;
    inversion recovery M(tau) = M0 (1 - 2 exp(-tau/T1)); Hahn echo amplitude M0 exp(-2 tau/T2); CPMG echo n at time
    2 n tau uses the same envelope. Noise is a hash of `seed`."""

    PARAMS = {"B": 0.5, "gamma": 2.6752218744e8, "T1": 1.5, "T2": 0.4, "M0": 1.0, "fq": 2000.0, "noise": 0.0,
              "seed": 7.0, "frf": 0.0, "tau": 1.0, "G": 0.0, "Dm": 2.3e-9}
    VARS = ["t", "S", "f", "M"]

    @staticmethod
    def fL(p):
        return p["gamma"] * p["B"] / (2.0 * PI)

    @staticmethod
    def resp(p, f):
        d = (f - Bloch.fL(p)) / p["fq"]
        return p["M0"] / (1.0 + d * d)

    @staticmethod
    def ir(p, tau):
        return p["M0"] * (1.0 - 2.0 * math.exp(-tau / p["T1"]))

    @staticmethod
    def echo(p, tau):
        """Hahn echo at 2 tau; in a field gradient G diffusion adds exp(-(2/3) gamma^2 G^2 D tau^3) (Carr-Purcell)."""
        return p["M0"] * math.exp(-2.0 * tau / p["T2"] - (2.0 / 3.0) * (p["gamma"] * p["G"]) ** 2 * p["Dm"] * tau ** 3)

    @staticmethod
    def cpmg(p, tau):
        """CPMG echo train: the envelope at echo time 2 tau is exp(-2 tau / T2); closely spaced pi pulses refocus the
        diffusion loss."""
        return p["M0"] * math.exp(-2.0 * tau / p["T2"])

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "S": Bloch.resp(p, p["frf"]), "f": Bloch.fL(p), "M": Bloch.ir(p, p["tau"])}

    @staticmethod
    def measure(p, cfg=None):
        """Larmor frequency from the peak of the probe response (golden search); T1 from the inversion-recovery
        straight line ln(M0 - M) ... ; T2 from the echo straight line ln(echo)."""
        lo, hi = Bloch.fL(p) * 0.9, Bloch.fL(p) * 1.1
        g = (math.sqrt(5.0) - 1.0) / 2.0
        a, b = hi - g * (hi - lo), lo + g * (hi - lo)
        for _ in range(120):
            if Bloch.resp(p, a) > Bloch.resp(p, b):
                hi = b
            else:
                lo = a
            a, b = hi - g * (hi - lo), lo + g * (hi - lo)
        fl = 0.5 * (lo + hi)
        t1 = [[p["T1"] * k, math.log(p["M0"] - Bloch.ir(p, p["T1"] * k))] for k in (0.1, 0.3, 0.6, 1.0, 1.6, 2.4)]
        m1, _c = _line(t1)
        t2 = [[2 * p["T2"] * k, math.log(Bloch.echo(p, p["T2"] * k))] for k in (0.1, 0.2, 0.4, 0.7, 1.0)]
        m2, _c2 = _line(t2)
        return {"fL": fl, "gamma": 2.0 * PI * fl / p["B"], "T1": -1.0 / m1 if m1 < 0 else 0.0, "T2": -1.0 / m2 if m2 < 0 else 0.0}


def _bloch_gamma(p):
    return p["gamma"]


# ============================================================================ pulsed-field-gradient diffusion
class Pfg(_Base):
    """Stejskal-Tanner PFG spin echo: E = exp(-gamma^2 g^2 delta^2 D (Delta - delta/3))."""

    PARAMS = {"g": 0.1, "gamma": 2.6752218744e8, "delta": 2.0e-3, "Dl": 0.02, "D": 2.3e-9, "noise": 0.0, "seed": 9.0}
    VARS = ["t", "E", "g", "b"]

    @staticmethod
    def bfac(p, g=None):
        g = p["g"] if g is None else g
        return (p["gamma"] * g * p["delta"]) ** 2 * (p["Dl"] - p["delta"] / 3.0)

    @staticmethod
    def E(p, g=None):
        return math.exp(-p["D"] * Pfg.bfac(p, g))

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "E": Pfg.E(p), "g": p["g"], "b": Pfg.bfac(p)}

    @staticmethod
    def measure(p, cfg=None):
        pts = [[Pfg.bfac(p, g), math.log(Pfg.E(p, g))] for g in (0.02, 0.05, 0.08, 0.12, 0.16, 0.2)]
        m, _c = _line(pts)
        return {"D": -m}


def _pfg_D(p):
    return p["D"]


# ============================================================================ ESR (field-modulated derivative)
class Esr(_Base):
    """Resonance h f = g muB B0 at fixed RF frequency f. Field-modulated detection gives the first derivative of a
    Lorentzian line of half width at half height dB: S(B) = -2 x / (1 + x^2)^2, x = (B - B0)/dB. The extrema are
    dBpp = 2 dB / sqrt(3) apart."""

    PARAMS = {"B": 0.0005, "f": 1.4e7, "g": 2.0036, "dB": 3.0e-5, "amp": 1.0}
    VARS = ["t", "S", "B", "B0"]

    @staticmethod
    def B0(p):
        return H * p["f"] / (p["g"] * MUB)

    @staticmethod
    def sig(p, B=None):
        B = p["B"] if B is None else B
        x = (B - Esr.B0(p)) / p["dB"]
        return -2.0 * p["amp"] * x / (1.0 + x * x) ** 2

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "S": Esr.sig(p), "B": p["B"], "B0": Esr.B0(p)}

    @staticmethod
    def measure(p, cfg=None):
        """Zero crossing of the derivative signal (bisection between its two extrema) -> g = h f / (muB B0);
        peak-to-peak width from the extrema (golden search)."""
        b0 = Esr.B0(p)
        lo, hi = b0 - 0.5 * p["dB"], b0 + 0.5 * p["dB"]
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if Esr.sig(p, mid) > 0:
                lo = mid
            else:
                hi = mid
        bz = 0.5 * (lo + hi)
        a, b = bz - 3 * p["dB"], bz
        gr = (math.sqrt(5.0) - 1.0) / 2.0
        x1, x2 = b - gr * (b - a), a + gr * (b - a)
        for _ in range(100):
            if Esr.sig(p, x1) > Esr.sig(p, x2):
                b = x2
            else:
                a = x1
            x1, x2 = b - gr * (b - a), a + gr * (b - a)
        xl = 0.5 * (a + b)
        a, b = bz, bz + 3 * p["dB"]
        x1, x2 = b - gr * (b - a), a + gr * (b - a)
        for _ in range(100):
            if Esr.sig(p, x1) < Esr.sig(p, x2):
                b = x2
            else:
                a = x1
            x1, x2 = b - gr * (b - a), a + gr * (b - a)
        xr = 0.5 * (a + b)
        return {"g": H * p["f"] / (MUB * bz), "B0": bz, "dBpp": xr - xl}


def _esr_g(p):
    return p["g"]


# ============================================================================ continuous-wave NMR
class NmrCw(_Base):
    """Fixed RF frequency f, swept field: resonance B0 = 2 pi f / gamma. The lock-in output is the derivative of a
    Lorentzian absorption line (half width dB)."""

    PARAMS = {"B": 0.3, "f": 1.5e7, "gamma": 2.6752218744e8, "dB": 2.0e-5, "amp": 1.0}
    VARS = ["t", "S", "B", "B0"]

    @staticmethod
    def B0(p):
        return 2.0 * PI * p["f"] / p["gamma"]

    @staticmethod
    def sig(p, B=None):
        B = p["B"] if B is None else B
        x = (B - NmrCw.B0(p)) / p["dB"]
        return -2.0 * p["amp"] * x / (1.0 + x * x) ** 2

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "S": NmrCw.sig(p), "B": p["B"], "B0": NmrCw.B0(p)}

    @staticmethod
    def measure(p, cfg=None):
        b0 = NmrCw.B0(p)
        lo, hi = b0 - 0.5 * p["dB"], b0 + 0.5 * p["dB"]
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if NmrCw.sig(p, mid) > 0:
                lo = mid
            else:
                hi = mid
        bz = 0.5 * (lo + hi)
        gam = 2.0 * PI * p["f"] / bz
        return {"gamma": gam, "B0": bz, "gI": HBAR * gam / MUN}


# ============================================================================ Moessbauer 57Fe
EG = 14412.5      # eV, 57Fe gamma energy (unsourced / illustrative)
GG, GE = 0.18124, -0.10348      # 57Fe ground and 14.4 keV excited-state g-factors (unsourced / illustrative)
# transitions m_g -> m_e of an M1 14.4 keV line, with the 3:2:1:1:2:3 intensities
MB_LINES = [(-0.5, -1.5, 3.0), (-0.5, -0.5, 2.0), (-0.5, 0.5, 1.0), (0.5, -0.5, 1.0), (0.5, 0.5, 2.0), (0.5, 1.5, 3.0)]


class Mossbauer(_Base):
    """Transmission of a 57Fe absorber against source velocity: six Lorentzian lines at
    v = delta + eps_i + c mu_N B (g_e m_e - g_g m_g) / E_gamma (c = light speed), intensities 3:2:1:1:2:3 and
    quadrupole shift eps (+eps outer and middle pair, -eps in between). Idealised: no counting noise."""

    PARAMS = {"v": 0.0, "Bhf": 33.0, "delta": 0.0, "eps": 0.0, "wid": 0.25e-3, "depth": 0.1}
    VARS = ["t", "T", "v"]

    @staticmethod
    def pos(p):
        out = []
        sh = (1.0, -1.0, 1.0, 1.0, -1.0, 1.0)
        for k, (mg, me, ia) in enumerate(MB_LINES):
            e = MUN * p["Bhf"] * (GE * me - GG * mg) / QE
            out.append((p["delta"] + p["eps"] * sh[k] + CLIGHT * e / EG, ia))
        return out

    @staticmethod
    def trans(p, v=None):
        v = p["v"] if v is None else v
        s = 0.0
        for x0, ia in Mossbauer.pos(p):
            d = (v - x0) / (0.5 * p["wid"])
            s += ia / 12.0 / (1.0 + d * d)
        return 1.0 - p["depth"] * s * 2.0

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "T": Mossbauer.trans(p), "v": p["v"]}

    @staticmethod
    def measure(p, cfg=None):
        """Scan -12..+12 mm/s, find the six dips (parabola on the minima), then B_hf from the outer-line spacing,
        isomer shift from the centroid of the six lines."""
        n = 4800
        vs = [-12.0e-3 + 24.0e-3 * i / n for i in range(n + 1)]
        ts = [Mossbauer.trans(p, v) for v in vs]
        dx = vs[1] - vs[0]
        pk = []
        for i in range(1, n):
            if ts[i] < ts[i - 1] and ts[i] <= ts[i + 1] and ts[i] < 1.0 - 0.1 * p["depth"]:
                a, b, c = ts[i - 1], ts[i], ts[i + 1]
                d = a - 2 * b + c
                pk.append(vs[i] + (dx * 0.5 * (a - c) / d if d != 0 else 0.0))
        if len(pk) < 6:
            return {"Bhf": 0.0, "delta": 0.0, "eps": 0.0}
        pk = pk[:6]
        coef = CLIGHT * MUN / QE / EG * 2.0 * (1.5 * abs(GE) + 0.5 * GG)
        eps = ((pk[0] + pk[5]) + (pk[2] + pk[3]) - 2.0 * (pk[1] + pk[4])) / 12.0
        return {"Bhf": (pk[5] - pk[0]) / coef, "delta": sum(pk) / 6.0 - eps / 3.0, "eps": eps}


def _mb_B(p):
    return p["Bhf"]


KERNELS: dict[str, Any] = {
    "phd_scrt": ScRT, "phd_scic": ScIc, "phd_acsusc": AcSusc, "phd_therm": Therm, "phd_jj": Josephson,
    "phd_dcsquid": DcSquid, "phd_qhe": Qhe, "phd_sdh": Sdh, "phd_weakloc": WeakLoc, "phd_tunnel": Tunnel,
    "phd_bloch": Bloch, "phd_pfg": Pfg, "phd_esr": Esr, "phd_nmrcw": NmrCw, "phd_mossbauer": Mossbauer,
}
FAMILY = {k: "em" for k in KERNELS}
FAMILY["phd_therm"] = "thermo"
FAMILY["phd_scrt"] = "thermo"

TEXTBOOK = {
    "phd_Tc": _scrt_Tc, "phd_Ic": _scic_Ic, "phd_lam0": _acsusc_lam0, "phd_thermS": _therm_S, "phd_Phi0": _squid_Phi0,
    "phd_RK": _qhe_RK, "phd_sdhn": _sdh_n, "phd_Lphi": _wl_Lphi, "phd_gap": _tun_gap, "phd_gamma": _bloch_gamma,
    "phd_D": _pfg_D, "phd_g": _esr_g, "phd_Bhf": _mb_B,
    "phd_fJ": lambda p: p["f"],
    "phd_gI": lambda p: HBAR * p["gamma"] / MUN,
}

CALCS: dict[str, dict] = {}
