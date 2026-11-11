"""Kernel pack `ph3_nuc`: PhD / M.Sc. benches of nuclear, particle and cosmic-ray physics and of astrophysical data
analysis (see `packs/__init__.py`). Its exact JavaScript twin is `app/static/prayog/packs/ph3_nuc.js`; the test suite
runs both and demands the same numbers. Every kernel here is prefixed `ph3_`.

Deterministic: every counting or noisy process comes from a Lehmer generator seeded by the lab's own `seed`
parameter (never the clock), so the same lab always gives the same counts, spectra and light curves in both twins.

Constants: SI 2019 / CODATA 2018 (c, e, h, m_e c^2) and the IAU 2015 B3 nominal values need no source. Nuclear data
(line energies, intensities, the free-muon lifetime) are NNDC / ENSDF / PDG values; empirical rules of thumb
(Bragg-Kleeman range rule, NaI resolution) are the textbook ones of Knoll and Evans. A number that has no source is
a lab setting, and the lab text says "illustrative".

Astronomical data sets (transit light curve, 21 cm spectra) are SIMULATED from a stated model: they are not
observations of any real star or any real part of the sky.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
C = 2.99792458e8            # speed of light, exact
ME_KEV = 510.99895          # electron rest energy, keV (CODATA 2018)
RE = 2.8179403262e-15       # classical electron radius, m (CODATA 2018)
LN2 = math.log(2.0)
FWHM_K = 2.3548200450309493  # FWHM / sigma of a Gaussian


# ------------------------------------------------------------------------------------------------ small helpers
def _lin(pts: list[list[float]]) -> tuple[float, float]:
    """Least-squares straight line y = m x + c through the points: (m, c); (0, 0) when it cannot be formed."""
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


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _rows(rows: list[dict], keys: list[str]) -> list[list[float]]:
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


class _R:
    """Lehmer (MINSTD) generator: s -> 16807 s mod (2^31 - 1). Every product stays under 2^53, so Python and
    JavaScript walk the same stream exactly."""

    def __init__(self, seed: float) -> None:
        s = int(abs(seed)) % 2147483646
        self.s = s + 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647.0

    def poisson(self, mean: float) -> int:
        """Knuth's product method; a mean above 400 is split into equal parts (a sum of independent Poisson
        numbers is Poisson with the summed mean), the same rule in both twins."""
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

    def gauss(self) -> float:
        """A standard normal number (Box-Muller, the cosine branch)."""
        u1 = self.next()
        u2 = self.next()
        if u1 < 1e-12:
            u1 = 1e-12
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * PI * u2)


# ============================================================================================ coincidence bench
class Ph3Coinc:
    """Two detectors feed a coincidence unit whose gate is `k` unit widths of `tau` seconds. Each detector sees
    a singles rate R1 = A1 + b1 and R2 = A2 + b2. A pair of pulses from two UNRELATED events lands inside the
    gate by chance at the accidental rate 2 k tau R1 R2; events that really come from the same decay (a
    back-to-back pair, a gamma-gamma cascade) add the true rate `Rt`, which does not depend on the gate. So the
    coincidence rate is Rc = Rt + 2 k tau R1 R2, a straight line in the gate setting k: its slope gives the
    resolving time and its intercept the true coincidence rate. Counts of `t` seconds are Poisson numbers from
    the lab's own seed (one count index `j` per reading)."""

    PARAMS = {"A1": 1.5e5, "A2": 1.2e5, "b1": 100.0, "b2": 80.0, "tau": 3.0e-8, "k": 1.0, "Rt": 0.0, "t": 10.0,
              "seed": 31.0, "j": 0.0}
    VARS = ["t", "r1", "r2", "rc", "acc"]

    @staticmethod
    def r1(p: dict) -> float:
        return p["A1"] + p["b1"]

    @staticmethod
    def r2(p: dict) -> float:
        return p["A2"] + p["b2"]

    @staticmethod
    def acc(p: dict) -> float:
        return 2.0 * p["k"] * p["tau"] * Ph3Coinc.r1(p) * Ph3Coinc.r2(p)

    @staticmethod
    def rc(p: dict) -> float:
        return p["Rt"] + Ph3Coinc.acc(p)

    @staticmethod
    def counts(p: dict) -> list[int]:
        """[N1, N2, Nc] of one counting time (reading index `j`)."""
        rnd = _R(p["seed"] + 977.0 * p["j"])
        t = max(p["t"], 0.0)
        return [rnd.poisson(Ph3Coinc.r1(p) * t), rnd.poisson(Ph3Coinc.r2(p) * t), rnd.poisson(Ph3Coinc.rc(p) * t)]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "r1": Ph3Coinc.r1(p), "r2": Ph3Coinc.r2(p), "rc": Ph3Coinc.rc(p),
                "acc": Ph3Coinc.acc(p)}

    @staticmethod
    def fit(rows: list[list[float]]) -> dict:
        """From rows [k, R1, R2, Rc]: the line Rc = Rt + 2 tau R1 R2 k -> tau (from the slope and the mean R1 R2)
        and the intercept Rt."""
        if len(rows) < 2:
            return {"tau": 0.0, "Rt": 0.0}
        m, c = _lin([[r[0], r[3]] for r in rows])
        rr = _mean([r[1] * r[2] for r in rows])
        return {"tau": m / (2.0 * rr) if rr > 0 else 0.0, "Rt": c}

    @staticmethod
    def measure(p, cfg=None):
        """What the student works out, from the noise-free rates at gate settings k = 1..4."""
        rows = []
        for k in (1.0, 2.0, 3.0, 4.0):
            q = dict(p)
            q["k"] = k
            rows.append([k, Ph3Coinc.r1(q), Ph3Coinc.r2(q), Ph3Coinc.rc(q)])
        f = Ph3Coinc.fit(rows)
        return {"tau_fit": f["tau"], "Rt_fit": f["Rt"], "rc": Ph3Coinc.rc(p), "r1": Ph3Coinc.r1(p),
                "r2": Ph3Coinc.r2(p)}


def _coinc_tau(p: dict) -> float:
    return p["tau"]


def _coinc_rt(p: dict) -> float:
    return p["Rt"]


# ============================================================================================ Compton scattering
class Ph3Compton:
    """A collimated gamma source, a small scatterer (a thin rod, no self-absorption: a stated simplification) and a
    NaI(Tl) detector on an arm that swings through the angle `th` (degrees) about the scatterer. A photon of
    energy E0 scattered through th leaves with E' = E0 / (1 + (E0 / mc^2)(1 - cos th)); how many do so per
    steradian is the Klein-Nishina cross-section per electron,
    dsigma/dOmega = (re^2 / 2) (E'/E0)^2 (E'/E0 + E0/E' - sin^2 th).
    The detector turns the scattered line into a photopeak at E' (resolution FWHM = R662 sqrt(662 E')) on a Compton
    shelf, with the photopeak share pf(E) and intrinsic efficiency et(E) of a crystal that is described on its
    efficiency card. The MCA has `nch` channels of `gain` keV. With `coin` = 1 the scatterer is itself a
    scintillator whose recoil-electron pulse (30 keV threshold, always passed above 20 degrees) gates the MCA, which
    removes 98 % of the room background. Counts are Poisson numbers from the lab's seed."""

    PARAMS = {"E0": 661.657, "Ig": 0.851, "act": 3.7e7, "D": 0.25, "Dd": 0.30, "rad": 0.0254, "ne25": 2.77,
              "th": 90.0, "gain": 2.0, "off": 0.0, "nch": 512.0, "R662": 0.075, "pf662": 0.35, "et662": 0.55,
              "kE": 0.6, "t": 600.0, "bg": 0.01, "seed": 17.0, "task": 0.0, "j": 0.0, "coin": 0.0}
    VARS = ["t", "Ep", "dsig", "rate", "fwhm"]
    CAL_AM = 59.5409          # keV, Am-241 gamma (NNDC)
    ANGLES = (20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0)

    @staticmethod
    def eprime(e0: float, th_deg: float) -> float:
        return e0 / (1.0 + (e0 / ME_KEV) * (1.0 - math.cos(th_deg * PI / 180.0)))

    @staticmethod
    def kn(e0: float, th_deg: float) -> float:
        """Klein-Nishina differential cross-section per electron, m^2 / sr."""
        th = th_deg * PI / 180.0
        r = 1.0 / (1.0 + (e0 / ME_KEV) * (1.0 - math.cos(th)))
        s2 = math.sin(th) ** 2
        return 0.5 * RE * RE * r * r * (r + 1.0 / r - s2)

    @staticmethod
    def kn_total(e0: float) -> float:
        a = e0 / ME_KEV
        l = math.log(1.0 + 2.0 * a)
        return 2.0 * PI * RE * RE * ((1.0 + a) / (a * a) * (2.0 * (1.0 + a) / (1.0 + 2.0 * a) - l / a)
                                     + l / (2.0 * a) - (1.0 + 3.0 * a) / ((1.0 + 2.0 * a) ** 2))

    @staticmethod
    def fwhm(e: float, p: dict) -> float:
        return p["R662"] * math.sqrt(662.0 * e)

    @staticmethod
    def pf(e: float, p: dict) -> float:
        return 1.0 / (1.0 + (e / 662.0) * (1.0 / p["pf662"] - 1.0))

    @staticmethod
    def et(e: float, p: dict) -> float:
        return min(0.98, p["et662"] * math.pow(662.0 / e, p["kE"]))

    @staticmethod
    def eff(e: float, p: dict) -> float:
        """Photopeak efficiency of the crystal (the efficiency card)."""
        return Ph3Compton.et(e, p) * Ph3Compton.pf(e, p)

    @staticmethod
    def omega(p: dict) -> float:
        return PI * p["rad"] * p["rad"] / (p["Dd"] * p["Dd"])

    @staticmethod
    def flux(p: dict) -> float:
        """Photons per m^2 per second at the scatterer."""
        return p["act"] * p["Ig"] / (4.0 * PI * p["D"] * p["D"])

    @staticmethod
    def npk(p: dict) -> float:
        """Counts in the photopeak of the scattered line, in the counting time."""
        ep = Ph3Compton.eprime(p["E0"], p["th"])
        return (p["t"] * Ph3Compton.flux(p) * p["ne25"] * 1e25 * Ph3Compton.kn(p["E0"], p["th"])
                * Ph3Compton.omega(p) * Ph3Compton.eff(ep, p))

    @staticmethod
    def line_spec(p: dict, e: float, npk: float) -> list[float]:
        """Expected counts per channel for ONE line: Gaussian photopeak of area `npk`, the Compton shelf
        (Klein-Nishina electron spectrum) and the room background."""
        n = int(round(p["nch"]))
        gain, off = p["gain"], p["off"]
        ex = [p["bg"] * (1.0 - 0.98 * p["coin"]) * p["t"] * gain] * n   # a coincidence gate removes 98 % of the room background
        s2pi = math.sqrt(2.0 * PI)
        sg0 = Ph3Compton.fwhm(e, p) / FWHM_K
        lo = max(0, int((e - off) / gain - 6.0 * sg0 / gain))
        hi = min(n - 1, int((e - off) / gain + 6.0 * sg0 / gain) + 1)
        for i in range(lo, hi + 1):
            x = off + gain * (i + 0.5) - e
            ex[i] += npk * gain * math.exp(-0.5 * (x / sg0) ** 2) / (sg0 * s2pi)
        pfv = Ph3Compton.pf(e, p)
        ncomp = npk * (1.0 - pfv) / pfv
        al = e / ME_KEV
        emin = 1.0 / (1.0 + 2.0 * al)
        raw = [0.0] * n
        tot = 0.0
        for j in range(n):
            tj = off + gain * (j + 0.5)
            eps = 1.0 - tj / e
            if eps < emin or eps >= 1.0:
                continue
            cs = 1.0 - (1.0 / eps - 1.0) / al
            f = eps + 1.0 / eps - (1.0 - cs * cs)
            raw[j] = f
            tot += f
        if tot > 0:
            for j in range(n):
                if raw[j] > 0:
                    ex[j] += ncomp * raw[j] / tot
        return ex

    @staticmethod
    def expected(p: dict) -> list[float]:
        """The spectrum with the detector at angle `th`: the scattered line."""
        ep = Ph3Compton.eprime(p["E0"], p["th"])
        return Ph3Compton.line_spec(p, ep, Ph3Compton.npk(p))

    @staticmethod
    def direct(p: dict, e: float, n: float) -> list[float]:
        """A calibration source (a known line) counted for the same time: `n` counts in its photopeak."""
        return Ph3Compton.line_spec(p, e, n)

    @staticmethod
    def counts(ex: list[float], seed: float) -> list[int]:
        rnd = _R(seed)
        return [rnd.poisson(m) for m in ex]

    @staticmethod
    def find_peak(c: list[float], p: dict) -> dict:
        """The tallest peak of a spectrum, looked for numerically: seven-channel smoothing to find its top, its
        full width at half height above the baseline, then the centroid and the net area within 3 widths
        (baseline = the straight line between the means of two blocks of channels just outside that window)."""
        n = len(c)
        sm = [0.0] * n
        for i in range(3, n - 3):
            sm[i] = (c[i - 3] + c[i - 2] + c[i - 1] + c[i] + c[i + 1] + c[i + 2] + c[i + 3]) / 7.0
        i0, vm = 8, -1.0
        for i in range(8, n - 4):
            if sm[i] > vm:
                vm, i0 = sm[i], i
        # half width from the smoothed profile against a baseline taken far above the peak
        hb = 0.0
        far = min(n - 4, i0 + 40)
        hb = sm[far] if far > i0 else 0.0
        half = hb + 0.5 * (vm - hb)
        a = i0
        while a > 3 and sm[a] > half:
            a -= 1
        b = i0
        while b < n - 4 and sm[b] > half:
            b += 1
        w = max(3.0, float(b - a))
        w = max(w, 3.0)
        sd = w / FWHM_K
        lo = max(4, int(i0 - 3.0 * sd))
        hi = min(n - 5, int(i0 + 3.0 * sd + 0.999))
        blk = max(3, int(sd))
        l0 = max(blk, lo - 2 * blk) + blk // 2
        r0 = min(n - blk - 1, hi + 2 * blk) - blk // 2
        bl = sum(c[l0 - blk:l0 + blk + 1]) / (2 * blk + 1)
        br = sum(c[r0 - blk:r0 + blk + 1]) / (2 * blk + 1)
        xl, xr = float(l0), float(r0)
        s = sx = 0.0
        for i in range(lo, hi + 1):
            base = bl + (br - bl) * (i - xl) / (xr - xl) if xr != xl else bl
            y = c[i] - base
            s += y
            sx += y * (i + 0.5)
        ch = sx / s if s > 0 else float(i0) + 0.5
        return {"ch": ch, "fwhm_ch": w, "area": s / 0.9973, "i0": i0}

    @staticmethod
    def calibrate(p: dict) -> tuple[float, float]:
        """E = a + b ch from the two calibration lines (Am-241 and the source's own direct line), noise-free."""
        q = dict(p)
        na = 2.0e4
        ca = Ph3Compton.find_peak(Ph3Compton.direct(q, Ph3Compton.CAL_AM, na), q)
        cb = Ph3Compton.find_peak(Ph3Compton.direct(q, p["E0"], na), q)
        b = (p["E0"] - Ph3Compton.CAL_AM) / (cb["ch"] - ca["ch"])
        return Ph3Compton.CAL_AM - b * ca["ch"], b

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ep = Ph3Compton.eprime(p["E0"], p["th"])
        return {"t": s.get("t", 0.0), "Ep": ep, "dsig": Ph3Compton.kn(p["E0"], p["th"]),
                "rate": Ph3Compton.npk(p) / max(p["t"], 1e-9), "fwhm": Ph3Compton.fwhm(ep, p)}

    @staticmethod
    def card(p: dict) -> list[list[float]]:
        """The efficiency card: photopeak efficiency at 25 keV steps from 50 to 700 keV."""
        return [[e, Ph3Compton.eff(e, p)] for e in [50.0 + 25.0 * i for i in range(27)]]

    @staticmethod
    def eff_card(card: list[list[float]], e: float) -> float:
        """Photopeak efficiency by interpolating the card (log-log), as a student does."""
        if e <= card[0][0]:
            return card[0][1]
        for i in range(1, len(card)):
            if e <= card[i][0]:
                x0, x1 = math.log(card[i - 1][0]), math.log(card[i][0])
                y0, y1 = math.log(card[i - 1][1]), math.log(card[i][1])
                return math.exp(y0 + (y1 - y0) * (math.log(e) - x0) / (x1 - x0))
        return card[-1][1]

    @staticmethod
    def analyse(p: dict, peaks: list[list[float]]) -> dict:
        """From [angle, E', area] rows: the electron rest energy (the line 1/E' = 1/E0 + (1 - cos th)/mc^2) and
        the total cross-section in barn (1 b = 1e-28 m^2; measured dsigma/dOmega integrated over the angles measured, the unmeasured ends
        filled with the Klein-Nishina curve scaled by the mean measured / predicted ratio)."""
        if len(peaks) < 3:
            return {"mc2": 0.0, "sigma": 0.0, "ratio": 0.0}
        m, _c = _lin([[1.0 - math.cos(a * PI / 180.0), 1.0 / e] for a, e, _ar in peaks])
        card = Ph3Compton.card(p)
        pref = p["t"] * Ph3Compton.flux(p) * p["ne25"] * 1e25 * Ph3Compton.omega(p)
        ds = []
        for a, e, ar in peaks:
            ds.append(ar / (pref * Ph3Compton.eff_card(card, e)))
        ratios = [ds[i] / Ph3Compton.kn(p["E0"], peaks[i][0]) for i in range(len(ds))]
        rm = _mean(ratios)
        pts = sorted(zip([a for a, _e, _ar in peaks], ds))
        tot = 0.0
        for i in range(1, len(pts)):          # trapezoid in angle of 2 pi sin(th) dsigma/dOmega
            a0, d0 = pts[i - 1]
            a1, d1 = pts[i]
            f0 = math.sin(a0 * PI / 180.0) * d0
            f1 = math.sin(a1 * PI / 180.0) * d1
            tot += 0.5 * (f0 + f1) * (a1 - a0) * PI / 180.0
        amin, amax = pts[0][0], pts[-1][0]
        nend = 40
        for k in range(nend):                 # unmeasured ends, midpoint rule on the scaled KN curve
            a = amin * (k + 0.5) / nend
            tot += rm * Ph3Compton.kn(p["E0"], a) * math.sin(a * PI / 180.0) * (amin / nend) * PI / 180.0
            a = amax + (180.0 - amax) * (k + 0.5) / nend
            tot += rm * Ph3Compton.kn(p["E0"], a) * math.sin(a * PI / 180.0) * ((180.0 - amax) / nend) * PI / 180.0
        return {"mc2": 1.0 / m if m > 0 else 0.0, "sigma": 2.0 * PI * tot / 1e-28, "ratio": rm}

    @staticmethod
    def measure(p, cfg=None):
        """The whole experiment on the noise-free spectra: calibrate, put the detector at each angle, find the
        peak, convert its channel to energy, fit."""
        a0, b0 = Ph3Compton.calibrate(p)
        peaks = []
        for ang in Ph3Compton.ANGLES:
            q = dict(p)
            q["th"] = ang
            pk = Ph3Compton.find_peak(Ph3Compton.expected(q), q)
            peaks.append([ang, a0 + b0 * pk["ch"], pk["area"]])
        r = Ph3Compton.analyse(p, peaks)
        return {"mc2": r["mc2"], "sigma": r["sigma"], "ratio": r["ratio"], "Ep": Ph3Compton.eprime(p["E0"], p["th"])}


def _compton_mc2(p: dict) -> float:
    return ME_KEV


def _compton_sigma(p: dict) -> float:
    return Ph3Compton.kn_total(p["E0"]) / 1e-28          # barn


# ============================================================================================ alpha spectrometry
class Ph3Alpha:
    """A sealed alpha source facing a silicon surface-barrier detector in a vacuum chamber, distance `d` metres,
    gas pressure `pr` mbar (air, 15 C), and an optional foil of mass thickness `tf` mg/cm^2 and mass number `Af`.

    Energy loss follows the Bragg-Kleeman rule: the range in air at 15 C and 1013.25 mbar is R(E) = a E^(3/2)
    (cm, MeV), so after an air-equivalent path x the energy is E(x) = (E0^(3/2) - x / a)^(2/3). A gas path of
    d cm at pressure pr is x = d pr / 1013.25; a foil is worth x = tf / (0.56 Af^(1/3)) cm of air (the
    Bragg-Kleeman rule R_m = 0.56 A^(1/3) R_air, R_m in mg/cm^2). Each line is smeared by the detector
    (FWHM w0) and by energy straggling in the path (variance proportional to x). The MCA has `nch` channels of
    `gain` keV. Counts are Poisson numbers from the lab's seed."""

    PARAMS = {"src": 0.0, "pr": 0.0, "d": 0.03, "tf": 0.0, "Af": 197.0, "a": 0.318, "w0": 18.0, "ks": 30.0,
              "gain": 5.0, "off": 0.0, "nch": 1200.0, "rate": 400.0, "t": 120.0, "bg": 0.0005, "seed": 41.0}
    VARS = ["t", "E1", "x", "fwhm"]
    # (energy keV, intensity per decay): ENSDF values (see the lab's sources entry)
    LINES = (
        ((5485.56, 0.848), (5442.80, 0.131), (5388.23, 0.0166)),                   # Am-241
        ((5156.59, 0.7077), (5144.3, 0.1711), (5105.5, 0.1194)),                   # Pu-239
    )

    @staticmethod
    def lines(p: dict) -> tuple:
        i = int(round(p["src"]))
        return Ph3Alpha.LINES[0 if i < 0 else (len(Ph3Alpha.LINES) - 1 if i >= len(Ph3Alpha.LINES) else i)]

    @staticmethod
    def xair(p: dict) -> float:
        """Air-equivalent path, cm."""
        foil = p["tf"] / (0.56 * math.pow(p["Af"], 1.0 / 3.0)) if p["tf"] > 0 else 0.0
        return p["d"] * 100.0 * p["pr"] / 1013.25 + foil

    @staticmethod
    def energy(e0_kev: float, x_cm: float, a: float) -> float:
        """Alpha energy in keV after x cm of air-equivalent path (0 when stopped)."""
        e = e0_kev / 1000.0
        r = math.pow(e, 1.5) - x_cm / a
        return 1000.0 * math.pow(r, 2.0 / 3.0) if r > 0 else 0.0

    @staticmethod
    def fwhm(p: dict) -> float:
        return math.sqrt(p["w0"] * p["w0"] + p["ks"] * p["ks"] * Ph3Alpha.xair(p))

    @staticmethod
    def expected(p: dict) -> list[float]:
        n = int(round(p["nch"]))
        gain, off = p["gain"], p["off"]
        ex = [p["bg"] * p["t"] * gain] * n
        x = Ph3Alpha.xair(p)
        fw = Ph3Alpha.fwhm(p)
        sg = fw / FWHM_K
        s2pi = math.sqrt(2.0 * PI)
        geo = (0.03 / p["d"]) ** 2
        for e0, inten in Ph3Alpha.lines(p):
            e = Ph3Alpha.energy(e0, x, p["a"])
            if e <= 0.0:
                continue
            area = p["rate"] * geo * p["t"] * inten
            lo = max(0, int((e - off) / gain - 6.0 * sg / gain))
            hi = min(n - 1, int((e - off) / gain + 6.0 * sg / gain) + 1)
            for i in range(lo, hi + 1):
                xx = off + gain * (i + 0.5) - e
                ex[i] += area * gain * math.exp(-0.5 * (xx / sg) ** 2) / (sg * s2pi)
        return ex

    @staticmethod
    def counts(p: dict, k: float = 0.0) -> list[int]:
        rnd = _R(p["seed"] + 977.0 * k)
        return [rnd.poisson(m) for m in Ph3Alpha.expected(p)]

    @staticmethod
    def find_peak(c: list[float], p: dict) -> dict:
        """The tallest peak, numerically: top of a 5-channel smoothing, full width at half height by interpolating the
        half-height crossings, centroid of the channels within 1.5 widths of the top (baseline = the smaller of the
        two window-edge averages), net area."""
        n = len(c)
        sm = [0.0] * n
        for i in range(2, n - 2):
            sm[i] = (c[i - 2] + c[i - 1] + c[i] + c[i + 1] + c[i + 2]) / 5.0
        i0, vm = 6, -1.0
        for i in range(6, n - 3):
            if sm[i] > vm:
                vm, i0 = sm[i], i
        half = 0.5 * vm
        a = i0
        while a > 3 and sm[a] > half:
            a -= 1
        b = i0
        while b < n - 4 and sm[b] > half:
            b += 1
        xa = a + (half - sm[a]) / (sm[a + 1] - sm[a]) if sm[a + 1] != sm[a] else float(a)
        xb = b - 1 + (sm[b - 1] - half) / (sm[b - 1] - sm[b]) if sm[b - 1] != sm[b] else float(b)
        w = max(2.0, xb - xa)
        lo = max(2, int(i0 - 1.5 * w))
        hi = min(n - 3, int(i0 + 1.5 * w + 0.999))
        s = sx = 0.0
        for i in range(lo, hi + 1):
            s += c[i]
            sx += c[i] * (i + 0.5)
        ch = sx / s if s > 0 else i0 + 0.5
        return {"ch": ch, "fwhm_ch": w, "area": s, "i0": i0}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ln = Ph3Alpha.lines(p)[0]
        x = Ph3Alpha.xair(p)
        return {"t": s.get("t", 0.0), "E1": Ph3Alpha.energy(ln[0], x, p["a"]), "x": x, "fwhm": Ph3Alpha.fwhm(p)}

    @staticmethod
    def range_fit(pts: list[list[float]]) -> float:
        """pts = [x (cm of air), E (MeV)]: the range in air = where the straight line of E^(3/2) against x reaches
        zero."""
        m, c = _lin([[x, math.pow(e, 1.5)] for x, e in pts if e > 0])
        return -c / m if m < 0 else 0.0

    @staticmethod
    def measure(p, cfg=None):
        """Calibrate on the two sources in vacuum, then take the chosen source at eight pressures: energy of the
        main peak against air path, extrapolate to the range."""
        cal = []
        for s_i in (0.0, 1.0):
            q = dict(p)
            q["src"], q["pr"], q["tf"] = s_i, 0.0, 0.0
            pk = Ph3Alpha.find_peak(Ph3Alpha.expected(q), q)
            cal.append([pk["ch"], Ph3Alpha.LINES[int(s_i)][0][0]])
        b = (cal[0][1] - cal[1][1]) / (cal[0][0] - cal[1][0])
        a0 = cal[0][1] - b * cal[0][0]
        pts = []
        for pr in (0.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0):
            q = dict(p)
            q["pr"], q["tf"] = pr, 0.0
            pk = Ph3Alpha.find_peak(Ph3Alpha.expected(q), q)
            pts.append([q["d"] * 100.0 * pr / 1013.25, (a0 + b * pk["ch"]) / 1000.0])
        q0 = dict(p)
        q0["pr"], q0["tf"] = 0.0, 0.0
        res = Ph3Alpha.fwhm(q0)
        return {"range": Ph3Alpha.range_fit(pts), "res": res, "E0": pts[0][1]}


def _alpha_range(p: dict) -> float:
    return p["a"] * math.pow(Ph3Alpha.lines(p)[0][0] / 1000.0, 1.5)


# ============================================================================================ muon lifetime
class Ph3Muon:
    """Stopped cosmic-ray muons in a scintillator: a start pulse when a muon stops, a stop pulse when its decay
    electron lights the scintillator, and a time-to-amplitude converter that histograms the delay. A mu+ always
    decays with the free lifetime `tp`; a mu- may instead be captured by a nucleus (carbon), which shortens its
    life in the material to `tm` and removes the capture share from the decays that are seen. At sea level the
    mu- / mu+ ratio of stopped muons is `r`. Per start the decay-time density is
    w+ e^(-t/tp) / tp + w- e^(-t/tm) / tp, with w+ = 1 / (1 + r), w- = r / (1 + r). `Rs` starts arrive per hour,
    over `h` hours of data per chunk; a flat accidental background `bgr` per hour per microsecond is added.
    The histogram has `nb` bins of `dt` microseconds from `T0`. Counts are Poisson numbers from the lab's seed
    (one chunk index `j` per chunk of `h` hours). Times in the kernel are microseconds."""

    PARAMS = {"tp": 2.1969811, "tm": 2.026, "r": 1.27, "Rs": 150.0, "bgr": 0.03, "T0": 0.4, "dt": 1.0, "nb": 24.0,
              "h": 12.0, "j": 0.0, "seed": 53.0, "tfit": 12.5, "nbg": 5.0}
    VARS = ["t", "n", "tau"]

    @staticmethod
    def expected(p: dict, hours: float = -1.0) -> list[float]:
        """Noise-free counts per bin for `hours` of data (a chunk when negative)."""
        hh = p["h"] if hours < 0 else hours
        wp = 1.0 / (1.0 + p["r"])
        wm = p["r"] / (1.0 + p["r"])
        out = []
        for i in range(int(round(p["nb"]))):
            t0 = p["T0"] + i * p["dt"]
            t1 = t0 + p["dt"]
            sig = wp * (math.exp(-t0 / p["tp"]) - math.exp(-t1 / p["tp"])) \
                + wm * (p["tm"] / p["tp"]) * (math.exp(-t0 / p["tm"]) - math.exp(-t1 / p["tm"]))
            out.append(p["Rs"] * hh * sig + p["bgr"] * hh * p["dt"])
        return out

    @staticmethod
    def chunk(p: dict) -> list[int]:
        """The chunk `j` of data: Poisson counts per bin."""
        rnd = _R(p["seed"] + 977.0 * p["j"])
        return [rnd.poisson(m) for m in Ph3Muon.expected(p)]

    @staticmethod
    def fit_life(c: list[float], p: dict) -> dict:
        """Mean life from a histogram: the floor is the mean of the last `nbg` bins; the decay is the weighted
        straight line of ln(counts - floor) against the bin centre over the bins up to `tfit` microseconds, each
        weighted by (counts - floor)^2 / counts (the variance of a logarithm of a Poisson count)."""
        nb = len(c)
        nbg = int(round(p["nbg"]))
        bgv = _mean([float(x) for x in c[nb - nbg:]]) if nbg > 0 and nb > nbg else 0.0
        sw = swx = swy = swxx = swxy = 0.0
        for i in range(nb):
            tc = p["T0"] + (i + 0.5) * p["dt"]
            if tc > p["tfit"]:
                break
            y = c[i] - bgv
            if y <= 0.0 or c[i] <= 0.0:
                continue
            w = y * y / c[i]
            ly = math.log(y)
            sw += w
            swx += w * tc
            swy += w * ly
            swxx += w * tc * tc
            swxy += w * tc * ly
        d = sw * swxx - swx * swx
        if d == 0.0 or sw == 0.0:
            return {"tau": 0.0, "bg": bgv, "n": 0.0}
        m = (sw * swxy - swx * swy) / d
        return {"tau": -1.0 / m if m < 0 else 0.0, "bg": bgv, "n": sum(float(x) for x in c)}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ex = Ph3Muon.expected(p)
        return {"t": s.get("t", 0.0), "n": sum(ex), "tau": Ph3Muon.fit_life(ex, p)["tau"]}

    @staticmethod
    def measure(p, cfg=None):
        """The apparent mean life this scintillator would give with unlimited data (the noise-free histogram)."""
        f = Ph3Muon.fit_life(Ph3Muon.expected(p), p)
        return {"tau_fit": f["tau"], "bg": f["bg"], "tau_free": p["tp"]}


def _muon_free(p: dict) -> float:
    return p["tp"]


# ============================================================================================ transit light curve
G_SI = 6.6743e-11            # Newtonian constant, CODATA 2018


class Ph3Transit:
    """SIMULATED photometry of a star with one planet on a circular orbit (not an observation of any real star).

    Period `P` days, planet-to-star radius ratio `k`, impact parameter `b` (so cos i = b / (a/Rs)), stellar mean
    density `rho` kg/m^3 (so a/Rs = (G rho P^2 / 3 pi)^(1/3) by Kepler's third law, the planet's mass being
    negligible), linear limb darkening `u`, mid-transit time `t0` days. Flux is the fraction of the stellar disc not
    hidden by the planet, found by integrating the disc ring by ring. The data are `n = span / cad` points with
    Gaussian noise `sig` (relative flux) drawn from the lab's seed. Times are in days."""

    PARAMS = {"P": 3.2, "k": 0.1, "b": 0.3, "rho": 1410.0, "u": 0.0, "t0": 1.3, "sig": 4.0e-4, "cad": 0.0069444,
              "span": 27.4, "seed": 61.0, "tr": 0.0}
    VARS = ["t", "depth", "dur", "aRs"]
    NRING = 60

    @staticmethod
    def ars(p: dict) -> float:
        per = p["P"] * 86400.0
        return math.pow(G_SI * p["rho"] * per * per / (3.0 * PI), 1.0 / 3.0)

    @staticmethod
    def dur(p: dict) -> float:
        """The first-to-fourth contact duration, days (circular orbit)."""
        a = Ph3Transit.ars(p)
        arg = (math.sqrt(max((1.0 + p["k"]) ** 2 - p["b"] * p["b"], 0.0))) / math.sqrt(max(a * a - p["b"] * p["b"], 1e-12))
        return p["P"] / PI * math.asin(min(1.0, arg))

    @staticmethod
    def blocked(z: float, k: float, u: float) -> float:
        """Fraction of the stellar flux hidden when the planet's centre is z stellar radii from the star's."""
        if z >= 1.0 + k:
            return 0.0
        n = Ph3Transit.NRING
        rmin = max(0.0, z - k)
        rmax = min(1.0, z + k)
        if rmax <= rmin:
            return 0.0
        dr = (rmax - rmin) / n
        tot = 0.0
        for i in range(n):
            r = rmin + (i + 0.5) * dr
            if r <= 0.0:
                continue
            if z < 1e-12:
                arc = 2.0 * PI * r if r < k else 0.0
            elif r + z <= k:
                arc = 2.0 * PI * r
            else:
                cs = (r * r + z * z - k * k) / (2.0 * r * z)
                cs = -1.0 if cs < -1.0 else (1.0 if cs > 1.0 else cs)
                arc = 2.0 * r * math.acos(cs)
            mu = math.sqrt(max(0.0, 1.0 - r * r))
            tot += (1.0 - u * (1.0 - mu)) * arc * dr
        return tot / (PI * (1.0 - u / 3.0))

    @staticmethod
    def flux(p: dict, t: float) -> float:
        a = Ph3Transit.ars(p)
        ph = 2.0 * PI * (t - p["t0"]) / p["P"]
        cp = math.cos(ph)
        if cp <= 0.0:
            return 1.0
        ci = p["b"] / a
        z = a * math.sqrt(math.sin(ph) ** 2 + (ci * cp) ** 2)
        return 1.0 - Ph3Transit.blocked(z, p["k"], p["u"])

    @staticmethod
    def times(p: dict) -> list[float]:
        n = int(p["span"] / p["cad"])
        return [(i + 0.5) * p["cad"] for i in range(n)]

    @staticmethod
    def curve(p: dict, noise: bool = True) -> list[float]:
        rnd = _R(p["seed"])
        out = []
        for t in Ph3Transit.times(p):
            f = Ph3Transit.flux(p, t)
            if noise:
                f += p["sig"] * rnd.gauss()
            out.append(f)
        return out

    @staticmethod
    def bls(t: list[float], f: list[float], p0: float, p1: float, step: float, nbin: int = 160) -> list[list[float]]:
        """Box least squares: for every trial period the phase-folded flux is binned and the box (1 to 14 per
        cent of the period wide) that lowers the sum of squares most is kept. Returns [[period, power], ...]."""
        n = len(t)
        mean = _mean(f)
        out = []
        npg = int((p1 - p0) / step + 0.5) + 1
        mmax = max(2, int(0.14 * nbin))
        for ip in range(npg):
            per = p0 + ip * step
            sm = [0.0] * nbin
            ct = [0] * nbin
            for i in range(n):
                ph = t[i] / per
                ph -= math.floor(ph)
                b = int(ph * nbin)
                if b >= nbin:
                    b = nbin - 1
                sm[b] += f[i] - mean
                ct[b] += 1
            best = 0.0
            for s0 in range(nbin):
                sin = 0.0
                nin = 0
                for m in range(1, mmax + 1):
                    j = (s0 + m - 1) % nbin
                    sin += sm[j]
                    nin += ct[j]
                    if nin > 0 and n - nin > 0:
                        # chi^2 drop of a box at mean+d inside, mean-d' outside: sin^2 n / (nin (n - nin))
                        pw = sin * sin * n / (nin * (n - nin))
                        if sin < 0 and pw > best:
                            best = pw
            out.append([per, best])
        return out

    @staticmethod
    def best_period(t: list[float], f: list[float]) -> float:
        """Coarse then fine box-least-squares search; the period of the tallest peak."""
        c = Ph3Transit.bls(t, f, 0.8, 14.0, 0.02)
        pk = max(c, key=lambda r: r[1])[0]
        fi = Ph3Transit.bls(t, f, pk - 0.04, pk + 0.04, 0.0005, 400)
        return max(fi, key=lambda r: r[1])[0]

    @staticmethod
    def fold(t: list[float], f: list[float], per: float, tref: float, half: float, nb: int) -> list[list[float]]:
        """Phase-fold on (per, tref) and bin the time from -half to +half days: [[dt, mean flux, n], ...]."""
        s = [0.0] * nb
        c = [0] * nb
        for i in range(len(t)):
            x = (t[i] - tref) / per
            x = (x - math.floor(x + 0.5)) * per
            if -half <= x < half:
                b = int((x + half) / (2.0 * half) * nb)
                b = nb - 1 if b >= nb else b
                s[b] += f[i]
                c[b] += 1
        return [[-half + (b + 0.5) * (2.0 * half / nb), s[b] / c[b] if c[b] else 1.0, c[b]] for b in range(nb)]

    @staticmethod
    def depth_of(fold: list[list[float]], tdur: float) -> float:
        """Mean depth within the central half of the transit (days)."""
        sm = 0.0
        n = 0.0
        for x, y, c in fold:
            if abs(x) <= 0.25 * tdur and c > 0:
                sm += y * c
                n += c
        return 1.0 - sm / n if n > 0 else 0.0

    @staticmethod
    def duration_of(fold: list[list[float]], depth: float) -> float:
        """Total duration by a least-squares trapezoid fit (depth fixed, ingress share 0.05..0.5 of the duration)."""
        best, bd = 1e30, 0.0
        for i in range(1, 80):
            dur = 0.02 + i * 0.004                  # 0.024 d ... 0.336 d
            for fr in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5):
                ing = fr * dur
                ss = 0.0
                for x, y, c in fold:
                    ax = abs(x)
                    if ax >= dur / 2:
                        m = 1.0
                    elif ax <= dur / 2 - ing:
                        m = 1.0 - depth
                    else:
                        m = 1.0 - depth * (dur / 2 - ax) / ing
                    ss += c * (y - m) * (y - m)
                if ss < best:
                    best, bd = ss, dur
        return bd

    @staticmethod
    def epoch(t: list[float], f: list[float], per: float) -> float:
        """Mid-transit time (days, within the first period): fold on `per` into 240 phase bins, smooth with a box of
        8 % of the period, take the lowest point, then refine it as the centroid of the dip (1 - flux) within
        +-8 % of the period, twice."""
        nb = 240
        sm = [0.0] * nb
        ct = [0] * nb
        for i in range(len(t)):
            ph = t[i] / per
            ph -= math.floor(ph)
            b = min(nb - 1, int(ph * nb))
            sm[b] += f[i]
            ct[b] += 1
        w = max(3, int(0.08 * nb))
        best, bj = 1e30, 0
        for j in range(nb):
            s_, n_ = 0.0, 0
            for m in range(w):
                k = (j + m) % nb
                s_ += sm[k]
                n_ += ct[k]
            v = s_ / n_ if n_ > 0 else 1e30
            if v < best:
                best, bj = v, j
        tref = ((bj + 0.5 * w) % nb) / nb * per
        for _ in range(2):
            sx = sw = 0.0
            for i in range(len(t)):
                x = (t[i] - tref) / per
                x = (x - math.floor(x + 0.5)) * per
                if abs(x) < 0.08 * per:
                    wt = 1.0 - f[i]
                    sx += wt * x
                    sw += wt
            if sw > 0:
                tref += sx / sw
        return tref

    @staticmethod
    def analyse(p: dict, t: list[float], f: list[float], per: float) -> dict:
        """Everything the student works out from the light curve and the period: mid-time, depth, limb-darkening
        corrected radius ratio, duration, impact parameter and inclination. Only the card values (the star's density,
        so a/Rs, and the limb-darkening coefficient u) are taken from the lab, never the planet's own numbers."""
        a = Ph3Transit.ars(p)
        tref = Ph3Transit.epoch(t, f, per)
        half = min(0.5, 0.1 * per)
        fd = Ph3Transit.fold(t, f, per, tref, half, 100)
        mn = 1.0
        for i in range(1, len(fd) - 1):
            m3 = (fd[i - 1][1] + fd[i][1] + fd[i + 1][1]) / 3.0
            if m3 < mn:
                mn = m3
        dd = Ph3Transit.duration_of(fd, 1.0 - mn)
        dep = Ph3Transit.depth_of(fd, dd)
        dd = Ph3Transit.duration_of(fd, dep)
        b2 = (1.0 + math.sqrt(max(dep, 0.0))) ** 2 - (a * math.sin(PI * dd / per)) ** 2
        bb = math.sqrt(b2) if b2 > 0 else 0.0
        mu = math.sqrt(max(1.0 - bb * bb, 0.0))
        u = p["u"]
        k = math.sqrt(max(dep * (1.0 - u / 3.0) / (1.0 - u * (1.0 - mu)), 0.0))
        cosi = min(1.0, bb / a)
        return {"depth": dep, "k": k, "dur": dd, "b": bb, "inc": math.acos(cosi) * 180.0 / PI, "aRs": a, "t0": tref}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "depth": 1.0 - Ph3Transit.flux(p, p["t0"]), "dur": Ph3Transit.dur(p),
                "aRs": Ph3Transit.ars(p)}

    @staticmethod
    def measure(p, cfg=None):
        """The analysis run on the noise-free light curve with the true period: radius ratio, depth, inclination."""
        q = dict(p)
        t = Ph3Transit.times(q)
        f = Ph3Transit.curve(q, False)
        r = Ph3Transit.analyse(q, t, f, p["P"])
        return {"k_fit": r["k"], "depth": r["depth"], "dur": r["dur"], "inc_fit": r["inc"],
                "inc_true": math.acos(p["b"] / Ph3Transit.ars(p)) * 180.0 / PI}


def _transit_k(p: dict) -> float:
    return p["k"]


# ============================================================================================ 21 cm hydrogen line
class Ph3Hi:
    """SIMULATED 21 cm spectra of the Galactic plane (not an observation of the sky).

    Gas moves on circles about the Galactic centre with the rotation curve
    Theta(R) = Th_inf R / sqrt(R^2 + Rc^2) (scaled so that Theta(R0) = Th0), R0 and Th0 being the IAU 1985
    standard values. Looking along Galactic longitude `l` (latitude 0) a cloud at distance s from the Sun is at
    R = sqrt(R0^2 + s^2 - 2 R0 s cos l) and has the radial velocity relative to the local standard of rest
    v = (Theta(R) R0 / R - Th0) sin l. The gas density falls as exp(-R / Rd); every cloud is a Gaussian of
    dispersion `sv` km/s. The spectrometer has `nch` channels covering the band `bw` Hz about the rest frequency
    f0 = 1420.405751768 MHz, channel i at frequency f0 + bw/2 - i df (so the radio velocity c (f0 - f) / f0 grows with
    i). The antenna sees the sky Doppler-shifted by the observatory's correction `vc` km/s (Earth's orbit and the
    Sun's motion): the observed velocity is the LSR velocity minus vc. Noise `sig` K per channel is Gaussian from
    the lab's seed. The line is optically thin, so N_H = 1.823e18 * integral(T_b dv) cm^-2 (T_b in K, v in km/s)."""

    PARAMS = {"l": 40.0, "Th0": 220.0, "R0": 8.5, "Rc": 1.5, "Rd": 6.0, "sv": 6.0, "Tsc": 4.0, "vc": 12.0,
              "bw": 2.4e6, "nch": 512.0, "sig": 0.25, "seed": 71.0, "task": 0.0}
    VARS = ["t", "vt", "R", "Th"]
    F0 = 1420.405751768e6      # Hz, hydrogen hyperfine line
    NH_K = 1.823e18            # cm^-2 per (K km/s)
    LS = (30.0, 40.0, 50.0, 60.0, 70.0)

    @staticmethod
    def theta(p: dict, r: float) -> float:
        tinf = p["Th0"] * math.sqrt(p["R0"] ** 2 + p["Rc"] ** 2) / p["R0"]
        return tinf * r / math.sqrt(r * r + p["Rc"] ** 2)

    @staticmethod
    def dv(p: dict) -> float:
        """Channel width, km/s."""
        return C * (p["bw"] / p["nch"]) / Ph3Hi.F0 / 1000.0

    @staticmethod
    def vtan(p: dict) -> float:
        """The velocity of the tangent point (the terminal velocity) relative to the LSR, km/s."""
        sl = math.sin(p["l"] * PI / 180.0)
        return Ph3Hi.theta(p, p["R0"] * sl) - p["Th0"] * sl

    @staticmethod
    def profile(p: dict, v: float) -> float:
        """T_b (K) at LSR velocity v: the sum over the line of sight, step 0.05 kpc out to R = 25 kpc."""
        l = p["l"] * PI / 180.0
        sl, cl = math.sin(l), math.cos(l)
        tot = 0.0
        ds = 0.05
        s2pi = math.sqrt(2.0 * PI)
        for i in range(600):
            s = (i + 0.5) * ds
            r = math.sqrt(p["R0"] ** 2 + s * s - 2.0 * p["R0"] * s * cl)
            if r > 25.0 or r < 0.3:
                continue
            vr = (Ph3Hi.theta(p, r) * p["R0"] / r - p["Th0"]) * sl
            x = (v - vr) / p["sv"]
            if abs(x) > 6.0:
                continue
            tot += math.exp(-r / p["Rd"]) * math.exp(-0.5 * x * x) / (p["sv"] * s2pi) * ds
        return p["Tsc"] * tot * 25.0

    @staticmethod
    def vlsr(p: dict, i: int) -> float:
        """LSR velocity of channel i (centre), km/s."""
        return (i + 0.5 - p["nch"] / 2.0) * Ph3Hi.dv(p) + p["vc"]

    @staticmethod
    def expected(p: dict) -> list[float]:
        return [Ph3Hi.profile(p, Ph3Hi.vlsr(p, i)) for i in range(int(round(p["nch"])))]

    @staticmethod
    def spectrum(p: dict, noise: bool = True) -> list[float]:
        ex = Ph3Hi.expected(p)
        if not noise:
            return ex
        rnd = _R(p["seed"] + 977.0 * math.floor(p["l"] + 0.5))
        return [x + p["sig"] * rnd.gauss() for x in ex]

    @staticmethod
    def freq(p: dict, i: int) -> float:
        """Channel frequency, Hz."""
        return Ph3Hi.F0 + p["bw"] / 2.0 - (i + 0.5) * (p["bw"] / p["nch"])

    EDGE_K = 0.63            # half-peak point lies 0.63 sv beyond the true terminal velocity (observatory's simulation)

    @staticmethod
    def edge(p: dict, tb: list[float]) -> float:
        """The terminal velocity (LSR, km/s) from a spectrum: smooth over five channels, find the highest channel
        where the smoothed spectrum is above half its peak, interpolate the crossing, and subtract the
        observatory's edge correction 0.63 sv (the half-peak point of a Gaussian-broadened edge lies that far
        beyond the true edge in this model)."""
        n = len(tb)
        sm = [0.0] * n
        for i in range(2, n - 2):
            sm[i] = (tb[i - 2] + tb[i - 1] + tb[i] + tb[i + 1] + tb[i + 2]) / 5.0
        pk = max(sm)
        half = 0.5 * pk
        hi = 2
        for i in range(2, n - 2):
            if sm[i] > half:
                hi = i
        v0 = Ph3Hi.vlsr(p, hi)
        if hi + 1 < n and sm[hi] != sm[hi + 1]:
            v0 += Ph3Hi.dv(p) * (sm[hi] - half) / (sm[hi] - sm[hi + 1])
        return v0 - Ph3Hi.EDGE_K * p["sv"]

    @staticmethod
    def nh(p: dict, tb: list[float]) -> float:
        """Column density, cm^-2, from the optically thin line: 1.823e18 times the sum of T_b dv."""
        return Ph3Hi.NH_K * sum(tb) * Ph3Hi.dv(p)

    @staticmethod
    def rotation(p: dict, tb: list[float]) -> list[float]:
        """[R kpc, Theta km/s] from one spectrum at p['l']: R = R0 sin l, Theta = v_t + Th0 sin l."""
        sl = math.sin(p["l"] * PI / 180.0)
        return [p["R0"] * sl, Ph3Hi.edge(p, tb) + p["Th0"] * sl]

    @staticmethod
    def measure(p, cfg=None):
        """Mean circular speed over the five pointings, from the noise-free spectra."""
        th = []
        for l in Ph3Hi.LS:
            q = dict(p)
            q["l"] = l
            th.append(Ph3Hi.rotation(q, Ph3Hi.expected(q))[1])
        return {"theta_fit": _mean(th), "nh": Ph3Hi.nh(p, Ph3Hi.expected(p))}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        sl = math.sin(p["l"] * PI / 180.0)
        return {"t": s.get("t", 0.0), "vt": Ph3Hi.vtan(p), "R": p["R0"] * sl, "Th": Ph3Hi.theta(p, p["R0"] * sl)}


def _hi_theta(p: dict) -> float:
    """The true mean circular speed at the five tangent radii."""
    return _mean([Ph3Hi.theta(p, p["R0"] * math.sin(l * PI / 180.0)) for l in Ph3Hi.LS])


# ============================================================================================ registry
KERNELS: dict[str, Any] = {"ph3_coinc": Ph3Coinc, "ph3_compton": Ph3Compton, "ph3_alpha": Ph3Alpha,
                           "ph3_muon": Ph3Muon, "ph3_transit": Ph3Transit, "ph3_hi": Ph3Hi}
FAMILY = {"ph3_coinc": "em", "ph3_compton": "em", "ph3_alpha": "em", "ph3_muon": "em", "ph3_transit": "optics",
          "ph3_hi": "em"}
TEXTBOOK = {
    "ph3_coinc_tau": _coinc_tau,
    "ph3_coinc_rt": _coinc_rt,
    "ph3_compton_mc2": _compton_mc2,
    "ph3_compton_sigma": _compton_sigma,
    "ph3_alpha_range": _alpha_range,
    "ph3_muon_free": _muon_free,
    "ph3_transit_k": _transit_k,
    "ph3_hi_theta": _hi_theta,
}
CALCS: dict[str, dict] = {
    "ph3_coinc_tau": {"label": "resolving time", "unit": "s", "needs": ["k", "r1", "r2", "rc"],
                      "fn": lambda rows, p: Ph3Coinc.fit(_rows(rows, ["k", "r1", "r2", "rc"]))["tau"]},
    "ph3_coinc_rt": {"label": "true coincidence rate", "unit": "1/s", "needs": ["k", "r1", "r2", "rc"],
                     "fn": lambda rows, p: Ph3Coinc.fit(_rows(rows, ["k", "r1", "r2", "rc"]))["Rt"]},
    "ph3_compton_mc2": {"label": "electron rest energy", "unit": "keV", "needs": ["th", "Ep"],
                        "fn": lambda rows, p: (lambda m: 1.0 / m if m > 0 else 0.0)(
                            _lin([[1.0 - math.cos(a * PI / 180.0), 1.0 / e]
                                  for a, e in _rows(rows, ["th", "Ep"]) if e > 0])[0])},
    "ph3_alpha_range": {"label": "range in air", "unit": "cm", "needs": ["x", "E"],
                        "fn": lambda rows, p: Ph3Alpha.range_fit(_rows(rows, ["x", "E"]))},
    "ph3_muon_life": {"label": "mean life", "unit": "us", "needs": ["tc", "n"],
                      "fn": lambda rows, p: (lambda m: -1.0 / m if m < 0 else 0.0)(
                          _lin([[tc, math.log(n)] for tc, n in _rows(rows, ["tc", "n"]) if n > 0])[0])},
}
