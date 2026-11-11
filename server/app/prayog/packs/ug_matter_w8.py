"""Kernel pack: B.Sc. nuclear / radiation physics and solid state physics, wave 8 (undergraduate Prayogshala).

New physics never goes into `kernels.py`; it lives here and in the EXACT JavaScript twin
`app/static/prayog/packs/ug_matter_w8.js` (same formulas, same order of operations, so both give the same numbers).

Kernels, with the relation each one is checked against:
    um8_beta    beta particles through aluminium   N = N0 exp(-mu_m x) up to the range R; R from Katz and Penfold,
               R [g/cm^2] = 0.412 E^(1.265 - 0.0954 ln E); mu_m = 17 E^-1.14 cm^2/g (empirical)
    um8_k40     potassium-40 in a salt under a GM tube   A = m f_K N_A theta ln2 / (M_K T_half), counted with efficiency eps
    um8_ion     charged-particle stopping (Bethe-Bloch, PDG form, no shell or density corrections)
               -dE/dx = K z_eff^2 (Z/A) (1/beta^2) [ (1/2) ln(2 me c^2 beta^2 gamma^2 Tmax / I^2) - beta^2 ]
               with the Barkas effective charge z_eff = z (1 - exp(-125 beta z^(-2/3))); CSDA range by integration
    um8_xrd     powder diffractometer: Bragg 2 d sin(theta) = lambda, Scherrer L = K lambda / (beta cos theta)
    um8_revsat  reverse saturation current of a germanium junction   I_s = C T^3 exp(-Eg / (k T))
Counting is Poisson from the lab's own seed (Lehmer generator, the same stream in both twins): SIMULATED DATA.
Everything else is deterministic: no randomness drawn from the system, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
LN2 = math.log(2.0)
NA = 6.02214076e23            # CODATA / SI 2019
KB_EV = 8.617333262e-5        # Boltzmann constant in eV/K, CODATA 2018
YEAR = 3.15576e7              # Julian year in seconds
ME = 0.51099895               # electron rest energy, MeV (CODATA 2018)
AMU = 931.49410242            # atomic mass unit, MeV (CODATA 2018)
MU0 = 1.25663706212e-6      # vacuum permeability, CODATA 2018
KBB = 0.307075                # 4 pi N_A r_e^2 m_e c^2, MeV cm^2 / mol (PDG)


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


def _linfit(pts: list[list[float]]):
    """Least-squares straight line y = m x + c (plain loops, so both twins add in the same order)."""
    n = len(pts)
    if n < 2:
        return None
    sx = sy = sxx = sxy = 0.0
    for q in pts:
        sx += q[0]
        sy += q[1]
        sxx += q[0] * q[0]
        sxy += q[0] * q[1]
    den = n * sxx - sx * sx
    if abs(den) < 1e-300:
        return None
    m = (n * sxy - sx * sy) / den
    return [m, (sy - m * sx) / n]


class Rnd:
    """Lehmer (MINSTD) generator: s -> 16807 s mod (2^31 - 1); every product stays under 2^53 in both twins."""

    def __init__(self, seed: float) -> None:
        s = int(abs(seed)) % 2147483646
        self.s = s + 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647.0

    def poisson(self, mean: float) -> int:
        """Knuth's product method; a big mean is split into equal parts (a sum of Poisson numbers is Poisson)."""
        if mean <= 0:
            return 0
        if mean > 400:
            k = int(mean / 400) + 1
            total = 0
            for _ in range(k):
                total += self.poisson(mean / k)
            return total
        lim = math.exp(-mean)
        k, p = 0, 1.0
        while True:
            p *= self.next()
            if p <= lim:
                return k
            k += 1
            if k > 100000:
                return k


# ============================================================================================ beta absorption
class BetaAbsorb:
    """A sealed pure beta source under an end-window GM tube with aluminium absorbers of areal density x (g/cm^2).

    The beta part of the rate falls as N0 exp(-mu_m x) and stops at the range R; behind the range only the
    bremsstrahlung `brem` (a small, weakly absorbed tail) and the background `bg` are left. R is the Katz-Penfold
    relation and mu_m the empirical 17 E^-1.14 cm^2/g, both for the end-point energy `E` (MeV). The tube loses counts
    to its dead time `tau`. This is a simplified model: a real curve rounds off into the tail just before R.
    """

    PARAMS = {"x": 0.0, "E": 0.7637, "N0": 400.0, "brem": 0.4, "bg": 0.5, "tau": 2.5e-4, "t": 100.0,
              "seed": 17.0, "rho": 2.699}
    VARS = ["t", "rate", "net", "x_mg"]

    @staticmethod
    def range_kp(E: float) -> float:
        return 0.412 * math.pow(E, 1.265 - 0.0954 * math.log(E))

    @staticmethod
    def mu_m(E: float) -> float:
        return 17.0 * math.pow(E, -1.14)

    @staticmethod
    def beta_rate(p: dict) -> float:
        x = max(p["x"], 0.0)
        if x >= BetaAbsorb.range_kp(p["E"]):
            return 0.0
        return p["N0"] * math.exp(-BetaAbsorb.mu_m(p["E"]) * x)

    @staticmethod
    def true_rate(p: dict) -> float:
        return p["bg"] + p["brem"] + BetaAbsorb.beta_rate(p)

    @staticmethod
    def obs_rate(p: dict) -> float:
        r = BetaAbsorb.true_rate(p)
        return r / (1.0 + r * p["tau"])

    @staticmethod
    def counts(p: dict, k: int = 0) -> int:
        rnd = Rnd(p["seed"] + 977.0 * k)
        return rnd.poisson(BetaAbsorb.obs_rate(p) * max(p["t"], 0.0))

    @staticmethod
    def end_point(p: dict) -> float:
        """The thickness where the beta part of the simulated rate vanishes, found by bisection on the rate."""
        lo, hi = 0.0, 5.0
        for _ in range(200):
            mid = (lo + hi) / 2
            q = dict(p)
            q["x"] = mid
            if BetaAbsorb.beta_rate(q) > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "rate": BetaAbsorb.obs_rate(p), "net": BetaAbsorb.beta_rate(p),
                "x_mg": p["x"] * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        return {"R": BetaAbsorb.end_point(p), "mu": BetaAbsorb.mu_m(p["E"]), "rate": BetaAbsorb.obs_rate(p)}


# ============================================================================================ potassium-40 in a salt
class K40Salt:
    """A tray of a potassium salt (mass `m` kg, potassium mass fraction `fK`) under an end-window GM tube.

    Natural potassium carries the isotope K-40 (abundance `ab`, half-life `T12` years); a fraction `br` of its decays
    emits a beta particle. The tube sees a fraction `eff` of those betas (a design value of this tray and tube,
    not a material constant). Counts are Poisson numbers from the lab's seed: SIMULATED DATA."""

    PARAMS = {"m": 0.1, "fK": 0.52445, "MK": 39.0983, "ab": 1.17e-4, "T12": 1.248e9, "br": 0.8928, "eff": 0.002,
              "bg": 0.45, "tau": 2.5e-4, "t": 600.0, "seed": 29.0, "on": 1.0}
    VARS = ["t", "A", "beta", "net", "rate"]

    @staticmethod
    def activity(p: dict) -> float:
        nk = p["m"] * 1000.0 * p["fK"] / p["MK"] * NA * p["ab"]
        return nk * LN2 / (p["T12"] * YEAR)

    @staticmethod
    def net_rate(p: dict) -> float:
        return K40Salt.activity(p) * p["br"] * p["eff"] * (1.0 if p["on"] > 0.5 else 0.0)

    @staticmethod
    def obs_rate(p: dict) -> float:
        r = p["bg"] + K40Salt.net_rate(p)
        return r / (1.0 + r * p["tau"])

    @staticmethod
    def counts(p: dict, k: int = 0) -> int:
        rnd = Rnd(p["seed"] + 977.0 * k)
        return rnd.poisson(K40Salt.obs_rate(p) * max(p["t"], 0.0))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "A": K40Salt.activity(p), "beta": K40Salt.activity(p) * p["br"],
                "net": K40Salt.net_rate(p), "rate": K40Salt.obs_rate(p)}

    @staticmethod
    def measure(p, cfg=None):
        q = dict(p)
        q["on"] = 1.0
        a = K40Salt.activity(q)
        return {"net": K40Salt.net_rate(q), "A": a, "specific": a / (q["m"] * 1000.0 * q["fK"])}


# ============================================================================================ stopping of ions (Bethe-Bloch)
class IonStop:
    """Electronic stopping of a fast ion (charge z, mass Mu atomic mass units, kinetic energy E MeV per nucleon) in a
    medium of electrons per mass ZA (mol/g), mean excitation energy I (eV) and density rho (g/cm^3).

    Bethe-Bloch in the PDG form, WITHOUT the shell, Barkas-Andersen, Bloch or density-effect corrections, and with
    the Barkas effective charge for ions that are not fully stripped. Valid from a few MeV per nucleon up to a few
    GeV; below `Ec` (MeV per nucleon) the ion is taken to stop at once. `mode`: 0 the stopping-power curve,
    1 the CSDA range of a proton, 2 projectiles of different z at one speed, 3 the Bragg curve of a heavy ion.
    `n` is the number of energy steps the student's program uses."""

    PARAMS = {"mode": 0.0, "z": 1.0, "Mu": 1.007276, "E": 10.0, "ZA": 0.55508, "I": 75.0, "rho": 1.0,
              "n": 20.0, "Ec": 1.0, "nref": 4000.0}
    VARS = ["t", "S", "dEdx", "R", "zeff", "beta"]

    @staticmethod
    def kin(E: float, Mu: float) -> list[float]:
        M = Mu * AMU
        g = 1.0 + E * Mu / M
        b2 = 1.0 - 1.0 / (g * g)
        return [g, b2, M]

    @staticmethod
    def zeff(z: float, b2: float) -> float:
        return z * (1.0 - math.exp(-125.0 * math.sqrt(b2) * math.pow(z, -2.0 / 3.0)))

    @staticmethod
    def S(E: float, p: dict) -> float:
        """Mass stopping power, MeV cm^2 / g, at E MeV per nucleon."""
        k = IonStop.kin(E, p["Mu"])
        g, b2, M = k[0], k[1], k[2]
        r = ME / M
        tmax = 2.0 * ME * b2 * g * g / (1.0 + 2.0 * g * r + r * r)
        Imev = p["I"] * 1e-6
        L = 0.5 * math.log(2.0 * ME * b2 * g * g * tmax / (Imev * Imev)) - b2
        ze = IonStop.zeff(p["z"], b2)
        return KBB * ze * ze * p["ZA"] / b2 * L

    @staticmethod
    def range_n(p: dict, n: float) -> float:
        """CSDA range (g/cm^2) from Ec to E: the integral of dT / S over the ion's kinetic energy T = Mu E, by the
        midpoint rule on n equal steps of ln E."""
        n = max(1, int(round(n)))
        a, b = math.log(p["Ec"]), math.log(p["E"])
        h = (b - a) / n
        total = 0.0
        for i in range(n):
            e = math.exp(a + (i + 0.5) * h)
            total += e * h * p["Mu"] / IonStop.S(e, p)
        return total

    @staticmethod
    def s_min(p: dict) -> list[float]:
        """The minimum of the stopping-power curve (the minimum-ionising point), by golden section on ln E."""
        lo, hi = math.log(50.0), math.log(1.0e5)
        gr = (math.sqrt(5.0) - 1.0) / 2.0
        for _ in range(200):
            a = hi - gr * (hi - lo)
            b = lo + gr * (hi - lo)
            if IonStop.S(math.exp(a), p) < IonStop.S(math.exp(b), p):
                hi = b
            else:
                lo = a
        e = math.exp((lo + hi) / 2)
        return [e, IonStop.S(e, p)]

    @staticmethod
    def bragg(p: dict, n: float) -> list[list[float]]:
        """March the ion through the target in n equal depth steps of the reference range: [depth g/cm^2, energy loss
        per g/cm^2 in MeV] at each step, until it falls below Ec."""
        n = max(4, int(round(n)))
        R = IonStop.range_n(p, p["nref"])
        dx = R / n
        e = p["E"]
        x = 0.0
        out = []
        for _ in range(4 * n):
            if e <= p["Ec"]:
                break
            s = IonStop.S(e, p)
            out.append([x, s])
            e1 = e - 0.5 * dx * s / p["Mu"]
            if e1 <= p["Ec"]:
                x += (e - p["Ec"]) * p["Mu"] / s
                e = p["Ec"]
                break
            s1 = IonStop.S(e1, p)
            e = e - dx * s1 / p["Mu"]
            x += dx
        return out

    @staticmethod
    def stop_depth(p: dict, n: float) -> float:
        n = max(4, int(round(n)))
        R = IonStop.range_n(p, p["nref"])
        dx = R / n
        e = p["E"]
        x = 0.0
        for _ in range(4 * n):
            if e <= p["Ec"]:
                break
            s = IonStop.S(e, p)
            e1 = e - 0.5 * dx * s / p["Mu"]
            if e1 <= p["Ec"]:
                x += (e - p["Ec"]) * p["Mu"] / s
                break
            s1 = IonStop.S(e1, p)
            e2 = e - dx * s1 / p["Mu"]
            if e2 <= p["Ec"]:
                x += (e - p["Ec"]) * p["Mu"] / s1
                break
            e = e2
            x += dx
        return x

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        k = IonStop.kin(p["E"], p["Mu"])
        S = IonStop.S(p["E"], p)
        return {"t": s.get("t", 0.0), "S": S, "dEdx": S * p["rho"], "R": IonStop.range_n(p, p["n"]),
                "zeff": IonStop.zeff(p["z"], k[1]), "beta": math.sqrt(k[1])}

    @staticmethod
    def measure(p, cfg=None):
        k = IonStop.kin(p["E"], p["Mu"])
        sm = IonStop.s_min(p)
        return {"S": IonStop.S(p["E"], p), "R": IonStop.range_n(p, p["nref"]), "Rn": IonStop.range_n(p, p["n"]),
                "zeff": IonStop.zeff(p["z"], k[1]), "Smin": sm[1], "Emin": sm[0],
                "depth": IonStop.stop_depth(p, p["n"])}


# ============================================================================================ X-ray powder diffraction
class PowderXRD:
    """A powder on a theta-2theta diffractometer with Cu K-alpha1 X-rays (wavelength `lam`).

    The lattice `lat`: 0 simple cubic, 1 body-centred cubic, 2 face-centred cubic, 3 diamond / zinc blende,
    4 hexagonal (a, c; reflections with h - k = 3n and l odd are absent), 5 body-centred tetragonal (a, c; h + k + l
    even), 6 rhombohedral in hexagonal axes (a, c; -h + k + l = 3n). Line positions are exact Bragg angles; a line is a
    Gaussian of width beta_tot = sqrt(beta_size^2 + binst^2), beta_size = K lam / (L cos theta) (Scherrer). Relative
    heights come from a simple model (multiplicity and the Lorentz-polarisation factor), not structure factors."""

    PARAMS = {"tth": 30.0, "lam": 1.5406e-10, "a": 3.6149e-10, "c": 0.0, "lat": 2.0, "L": 4.0e-8, "K": 0.9,
              "binst": 0.08, "I0": 1000.0, "bg": 20.0, "ph": 1.0, "pk": 1.0, "pl": 1.0}
    VARS = ["t", "I", "tth"]

    @staticmethod
    def allowed(h: int, k: int, l: int, lat: int) -> bool:
        if lat == 1:
            return (h + k + l) % 2 == 0
        if lat == 2:
            return (h % 2 == k % 2) and (k % 2 == l % 2)
        if lat == 3:
            if not ((h % 2 == k % 2) and (k % 2 == l % 2)):
                return False
            if h % 2 == 1:
                return True
            return (h + k + l) % 4 == 0
        if lat == 4:
            return not ((h - k) % 3 == 0 and l % 2 == 1)
        if lat == 5:                                   # I4_1/amd (anatase)
            if (h + k + l) % 2 != 0:
                return False
            if l == 0 and (h % 2 != 0 or k % 2 != 0):
                return False
            if h == 0 and (k + l) % 2 != 0:
                return False
            if h == k and (2 * h + l) % 4 != 0:
                return False
            if h == 0 and k == 0 and l % 4 != 0:
                return False
            return True
        if lat == 6:                                   # R-3c in hexagonal axes (hematite)
            if (-h + k + l) % 3 != 0:
                return False
            if (h == 0 or k == 0) and l % 2 != 0:
                return False
            if h == 0 and k == 0 and l % 6 != 0:
                return False
            return True
        return True

    @staticmethod
    def dsp(h: int, k: int, l: int, p: dict) -> float:
        lat = int(round(p["lat"]))
        a = p["a"]
        if lat <= 3:
            return a / math.sqrt(h * h + k * k + l * l)
        c = p["c"]
        if lat == 5:
            return 1.0 / math.sqrt((h * h + k * k) / (a * a) + l * l / (c * c))
        return 1.0 / math.sqrt(4.0 / 3.0 * (h * h + h * k + k * k) / (a * a) + l * l / (c * c))

    @staticmethod
    def lines(p: dict, lo: float = 15.0, hi: float = 100.0) -> list[list[float]]:
        """[2theta deg, relative height, h, k, l, N] of every allowed line between lo and hi, one per d spacing."""
        lat = int(round(p["lat"]))
        seen = {}
        hmax = 6 if lat <= 3 else 4
        lmax = 6 if lat <= 3 else 16
        for h in range(0, hmax + 1):
            for k in range(0, hmax + 1):
                if lat <= 3 and k > h:
                    continue
                for l in range(0, lmax + 1):
                    if lat <= 3 and l > k:
                        continue
                    if h == 0 and k == 0 and l == 0:
                        continue
                    if not PowderXRD.allowed(h, k, l, lat):
                        continue
                    d = PowderXRD.dsp(h, k, l, p)
                    sn = p["lam"] / (2.0 * d)
                    if sn >= 1.0:
                        continue
                    tth = 2.0 * math.asin(sn) * 180.0 / PI
                    if tth < lo or tth > hi:
                        continue
                    key = str(round(d * 1e14))
                    th = tth / 2.0 * PI / 180.0
                    lp = (1.0 + math.cos(2 * th) ** 2) / (math.sin(th) ** 2 * math.cos(th))
                    if key in seen:
                        seen[key][1] += lp
                        continue
                    seen[key] = [tth, lp, h, k, l, h * h + k * k + l * l]
        out = sorted(seen.values(), key=lambda q: q[0])
        if out:
            top = max(q[1] for q in out)
            for q in out:
                q[1] = q[1] / top
        return out

    @staticmethod
    def width(tth: float, p: dict) -> float:
        """FWHM in degrees 2theta of a line at tth: size broadening (Scherrer) added in quadrature to the instrument."""
        th = tth / 2.0 * PI / 180.0
        bs = p["K"] * p["lam"] / (p["L"] * math.cos(th)) * 180.0 / PI
        return math.sqrt(bs * bs + p["binst"] * p["binst"])

    @staticmethod
    def intensity(tth: float, p: dict) -> float:
        tot = p["bg"]
        for q in PowderXRD.lines(p):
            w = PowderXRD.width(q[0], p)
            sg = w / 2.3548200450309493
            dx = tth - q[0]
            if abs(dx) < 8 * w:
                tot += p["I0"] * q[1] * math.exp(-dx * dx / (2 * sg * sg))
        return tot

    @staticmethod
    def peak(p: dict) -> float:
        """2theta of the chosen (ph pk pl) line."""
        d = PowderXRD.dsp(int(round(p["ph"])), int(round(p["pk"])), int(round(p["pl"])), p)
        return 2.0 * math.asin(p["lam"] / (2.0 * d)) * 180.0 / PI

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": PowderXRD.intensity(p["tth"], p), "tth": p["tth"]}

    @staticmethod
    def measure(p, cfg=None):
        """Scherrer on the chosen line: the measured width with the instrument taken off in quadrature."""
        t2 = PowderXRD.peak(p)
        w = PowderXRD.width(t2, p)
        b = math.sqrt(max(w * w - p["binst"] * p["binst"], 0.0)) * PI / 180.0
        th = t2 / 2.0 * PI / 180.0
        return {"L": p["K"] * p["lam"] / (b * math.cos(th)), "tth": t2, "fwhm": w,
                "a": p["lam"] / (2.0 * math.sin(th)) * math.sqrt(p["ph"] ** 2 + p["pk"] ** 2 + p["pl"] ** 2)}


# ============================================================================================ reverse saturation current
class RevSat:
    """A germanium p-n junction held at a reverse bias Vr in a stirred bath at temperature T (degrees C).

    The reverse current is the saturation current of the junction, I_s = C T^3 exp(-Eg / (k T)) (T in kelvin),
    with the band gap Eg (eV) taken as constant over the range used. C is fixed by I_s at 300 K (`I300`, a design
    value of this diode). The bath heats towards its set point `Tset` with a time constant `tau`."""

    PARAMS = {"Eg": 0.66, "I300": 2.0e-6, "Vr": 1.0, "T0": 27.0, "Tset": 27.0, "tau": 120.0}
    VARS = ["t", "T", "I", "I_uA"]

    @staticmethod
    def i_s(Tc: float, p: dict) -> float:
        T = Tc + 273.15
        c = p["I300"] / (300.0 ** 3 * math.exp(-p["Eg"] / (KB_EV * 300.0)))
        v = 1.0 - math.exp(-max(p["Vr"], 0.0) / (KB_EV * T))
        return c * T * T * T * math.exp(-p["Eg"] / (KB_EV * T)) * v

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "T": p["T0"]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["T"] = p["Tset"] + (s["T"] - p["Tset"]) * math.exp(-dt / p["tau"])
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        i = RevSat.i_s(s["T"], p)
        return {"t": s["t"], "T": s["T"], "I": i, "I_uA": i * 1e6}

    @staticmethod
    def measure(p, cfg=None):
        """Eg back from the slope of ln(I_s / T^3) against 1/T between 30 and 80 degrees C."""
        pts = []
        for i in range(6):
            Tc = 30.0 + 10.0 * i
            T = Tc + 273.15
            pts.append([1.0 / T, math.log(RevSat.i_s(Tc, p) / (T * T * T))])
        f = _linfit(pts)
        return {"Eg": -f[0] * KB_EV if f else 0.0, "I": RevSat.i_s(p["T0"], p)}


# ============================================================================================ piezoelectric resonator
class Piezo:
    """A piezoelectric disc as its Butterworth-Van Dyke circuit: the static capacitance C0 in parallel with the motional
    branch R1, L1, C1. The coupling coefficient k fixes C1 = k^2 C0 / (1 - k^2), so C1 / (C0 + C1) = k^2, and the
    series resonance `fs` fixes L1 = 1 / ((2 pi fs)^2 C1). A generator of amplitude V0 drives the disc through a sense
    resistor Rs; the voltage across Rs peaks near the resonance fr (minimum impedance) and dips near the
    antiresonance fa (maximum impedance), and k_eff^2 = 1 - (fr / fa)^2."""

    PARAMS = {"f": 90000.0, "fs": 100000.0, "C0": 2.0e-9, "k": 0.55, "R1": 4.0, "Rs": 100.0, "V0": 1.0}
    VARS = ["t", "Vr", "Z"]

    @staticmethod
    def zabs(f: float, p: dict) -> list[float]:
        """|Z| of the disc and the voltage across the sense resistor at frequency f."""
        w = 2.0 * PI * f
        c1 = p["k"] * p["k"] * p["C0"] / (1.0 - p["k"] * p["k"])
        l1 = 1.0 / ((2.0 * PI * p["fs"]) ** 2 * c1)
        mr, mi = p["R1"], w * l1 - 1.0 / (w * c1)          # motional branch
        cr, ci = 0.0, -1.0 / (w * p["C0"])                    # static capacitance
        nr, ni = mr * cr - mi * ci, mr * ci + mi * cr          # product
        dr, di = mr + cr, mi + ci                              # sum
        den = dr * dr + di * di
        zr, zi = (nr * dr + ni * di) / den, (ni * dr - nr * di) / den
        tr, ti = zr + p["Rs"], zi
        vr = p["V0"] * p["Rs"] / math.sqrt(tr * tr + ti * ti)
        return [math.sqrt(zr * zr + zi * zi), vr]

    @staticmethod
    def extreme(p: dict, lo: float, hi: float, sign: float) -> float:
        """The frequency of the minimum (sign 1) or maximum (sign -1) of |Z| between lo and hi, by golden section."""
        gr = (math.sqrt(5.0) - 1.0) / 2.0
        for _ in range(200):
            a = hi - gr * (hi - lo)
            b = lo + gr * (hi - lo)
            if sign * Piezo.zabs(a, p)[0] < sign * Piezo.zabs(b, p)[0]:
                hi = b
            else:
                lo = a
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        z = Piezo.zabs(p["f"], p)
        return {"t": s.get("t", 0.0), "Vr": z[1], "Z": z[0]}

    @staticmethod
    def measure(p, cfg=None):
        fa0 = p["fs"] / math.sqrt(1.0 - p["k"] * p["k"])
        fr = Piezo.extreme(p, 0.8 * p["fs"], 0.5 * (p["fs"] + fa0), 1.0)
        fa = Piezo.extreme(p, 0.5 * (p["fs"] + fa0), 1.2 * fa0, -1.0)
        return {"fr": fr, "fa": fa, "k": math.sqrt(1.0 - (fr / fa) ** 2)}


# ============================================================================================ Gouy balance
class Gouy:
    """A long tube of powder hanging from a balance with its lower end between the poles of an electromagnet and its
    upper end far outside the field. The apparent change of mass is  dm = (chi_v - chi_air) A B^2 / (2 mu0 g),  with
    chi_v the SI volume susceptibility of the packed powder, chi_v = 4 pi chim 1e-6 rho / M (chim the molar
    susceptibility in cgs units of 1e-6 cm^3/mol, rho the packed density g/cm^3, M the molar mass g/mol). The field
    is B = kB I of the magnet current, saturating gently as B = Bs tanh(kB I / Bs)."""

    PARAMS = {"I": 0.0, "kB": 0.25, "Bs": 1.2, "chim": 1460.0, "rho": 1.2, "M": 249.68, "A": 5.0e-5, "chiair": 3.7e-7,
              "g": 9.81, "m0": 0.012}
    VARS = ["t", "B", "dm", "m"]

    @staticmethod
    def field(p: dict) -> float:
        return p["Bs"] * math.tanh(p["kB"] * max(p["I"], 0.0) / p["Bs"])

    @staticmethod
    def chiv(p: dict) -> float:
        return 4.0 * PI * p["chim"] * 1e-6 * p["rho"] / p["M"]

    @staticmethod
    def dm(B: float, p: dict) -> float:
        return (Gouy.chiv(p) - p["chiair"]) * p["A"] * B * B / (2.0 * MU0 * p["g"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        B = Gouy.field(p)
        d = Gouy.dm(B, p)
        return {"t": s.get("t", 0.0), "B": B, "dm": d, "m": p["m0"] + d}

    @staticmethod
    def measure(p, cfg=None):
        """chim back from the slope of dm against B^2 at five currents."""
        pts = []
        for i in range(5):
            q = dict(p)
            q["I"] = 0.5 + 0.5 * i
            B = Gouy.field(q)
            pts.append([B * B, Gouy.dm(B, q)])
        f = _linfit(pts)
        sl = f[0] if f else 0.0
        chiv = sl * 2.0 * MU0 * p["g"] / p["A"] + p["chiair"]
        return {"chim": chiv * p["M"] / (4.0 * PI * 1e-6 * p["rho"]), "chiv": chiv}


KERNELS: dict[str, Any] = {"um8_gouy": Gouy, "um8_piezo": Piezo, "um8_beta": BetaAbsorb, "um8_k40": K40Salt, "um8_ion": IonStop, "um8_xrd": PowderXRD,
                           "um8_revsat": RevSat}
FAMILY = {"um8_gouy": "solid", "um8_piezo": "solid", "um8_beta": "nuclear", "um8_k40": "nuclear", "um8_ion": "nuclear", "um8_xrd": "solid", "um8_revsat": "solid"}


def _eg_fit(rows, p):
    pts = [[1.0 / (x[0] + 273.15), math.log(x[1] * 1e-6 / (x[0] + 273.15) ** 3)]
           for x in _rows(rows, "T", "I") if x[1] > 0]
    f = _linfit(pts)
    return -f[0] * KB_EV if f else 0.0


def _beta_mu(rows, p):
    pts = [[x[0], math.log(x[1])] for x in _rows(rows, "xm", "net") if x[1] > 0]
    f = _linfit(pts)
    return -f[0] if f else 0.0


CALCS = {
    "um8_eg": {"label": "Eg (band gap)", "unit": "eV", "needs": ["T", "I"], "fn": _eg_fit},
    "um8_beta_mu": {"label": "mu_m (mass absorption coefficient)", "unit": "cm²/g", "needs": ["xm", "net"],
                   "fn": _beta_mu},
}

TEXTBOOK = {
    # Katz and Penfold (1952): range of beta particles of end-point energy E in aluminium
    "um8_beta_range": lambda p: 0.412 * math.pow(p["E"], 1.265 - 0.0954 * math.log(p["E"])),
    # K-40 activity of the salt counted with the tray efficiency
    "um8_k40_net": lambda p: p["m"] * 1000.0 * p["fK"] / p["MK"] * NA * p["ab"] * LN2 / (p["T12"] * YEAR)
    * p["br"] * p["eff"],
    # Bethe-Bloch mass stopping power at E (closed form, the same formula)
    "um8_bethe_S": lambda p: IonStop.S(p["E"], p),
    # Barkas effective charge at the ion's speed
    "um8_zeff": lambda p: p["z"] * (1.0 - math.exp(-125.0 * math.sqrt(IonStop.kin(p["E"], p["Mu"])[1])
                                                 * math.pow(p["z"], -2.0 / 3.0))),
    # CSDA range: the integral of dT / S evaluated by Simpson's rule on 2000 intervals of ln E (independent quadrature)
    "um8_csda": lambda p: _simpson_range(p),
    # Scherrer equation on the instrument-corrected width
    "um8_scherrer": lambda p: p["L"],
    # coupling coefficient of the BVD circuit: k_eff^2 = C1 / (C0 + C1)
    "um8_keff": lambda p: p["k"],
    # Gouy: the molar susceptibility of the sample
    "um8_chim": lambda p: p["chim"],
    # band gap from the T^3 law
    "um8_eg": lambda p: p["Eg"],
}


def _simpson_range(p: dict) -> float:
    n = 2000
    a, b = math.log(p["Ec"]), math.log(p["E"])
    h = (b - a) / n
    tot = 0.0
    for i in range(n + 1):
        e = math.exp(a + i * h)
        f = e * p["Mu"] / IonStop.S(e, p)
        w = 1.0 if i == 0 or i == n else (4.0 if i % 2 == 1 else 2.0)
        tot += w * f
    return tot * h / 3.0
