"""Kernel pack `msc_elec`: the M.Sc. benches of nuclear spectroscopy, microwaves and advanced electronics
(see `packs/__init__.py`). Its exact JavaScript twin is `app/static/prayog/packs/msc_elec.js`; the test suite runs
both and demands the same numbers. Every kernel here is prefixed `msc_`.

Deterministic: counting statistics come from a Lehmer generator seeded by the lab's own `seed` parameter, never
from the clock, so the same lab always gives the same spectrum in both twins.

Nuclear data (gamma energies, intensities per decay) are NNDC / ENSDF evaluated values; resolution figures for
scintillators are the typical values of G. F. Knoll, Radiation Detection and Measurement. The photopeak share and
the intrinsic efficiency of a SIMULATED crystal are lab settings, said so in every lab that uses them.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
C = 2.99792458e8            # speed of light, exact
ME_KEV = 510.99895          # electron rest energy, keV (CODATA 2018)
QE = 1.602176634e-19
ME = 9.1093837015e-31       # electron mass, kg (CODATA 2018)


def _clamp(v: float, a: float, b: float) -> float:
    return a if v < a else (b if v > b else v)


class Rnd:
    """Lehmer (MINSTD) generator: s -> 16807 s mod (2^31 - 1)."""

    def __init__(self, seed: float) -> None:
        s = int(abs(seed)) % 2147483646
        self.s = s + 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647.0

    def poisson(self, mean: float) -> int:
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


# ============================================================================================ gamma spectrometer
# Index order is fixed: the rigs and the families refer to a source by this number.
# (name, [(energy keV, photons per decay, relative activity weight), ...])   NNDC / ENSDF
SRC: list[tuple[str, list[tuple[float, float, float]]]] = [
    ("Cs-137", [(661.657, 0.851, 1.0)]),
    ("Co-60", [(1173.228, 0.9985, 1.0), (1332.492, 0.999826, 1.0)]),
    ("Na-22", [(511.0, 1.806, 1.0), (1274.537, 0.99944, 1.0)]),
    ("Ba-133", [(80.998, 0.329, 1.0), (276.399, 0.07164, 1.0), (302.851, 0.1833, 1.0),
                (356.013, 0.6205, 1.0), (383.849, 0.0894, 1.0)]),
    ("Am-241", [(59.541, 0.359, 1.0)]),
    ("Eu-152", [(121.782, 0.2853, 1.0), (244.697, 0.0755, 1.0), (344.279, 0.2659, 1.0), (778.905, 0.1293, 1.0),
                (964.057, 0.1451, 1.0), (1085.837, 0.1011, 1.0), (1112.076, 0.1367, 1.0), (1408.013, 0.2087, 1.0)]),
    # soil: world-average activity concentrations (UNSCEAR 2000): K-40 400, U-238 series 35, Th-232 series 30 Bq/kg
    ("Soil", [(609.312, 0.4549, 35.0), (1120.287, 0.1492, 35.0), (1764.494, 0.1531, 35.0), (911.204, 0.258, 30.0),
              (968.971, 0.158, 30.0), (2614.511, 0.358, 30.0), (1460.822, 0.1066, 400.0)]),
]


class MscGspec:
    """A gamma source in front of a scintillation (or germanium) detector feeding a multichannel analyser.

    Photons of each line of the source reach the crystal with the geometric efficiency of an on-axis point source
    in front of a disc of radius `rad` at distance `d`, omega = (1 - d / sqrt(d^2 + rad^2)) / 2. A line of energy E
    is stopped with total intrinsic probability et(E) = min(0.98, et662 (662 / E)^kE); the share that ends in the
    full-energy photopeak is pf(E) = 1 / (1 + (E / 662)(1 / pf662 - 1)); the rest is the Compton continuum, whose
    shape is the Klein-Nishina electron spectrum with its edge at 2 alpha / (1 + 2 alpha) E.

    Every peak and the continuum are smeared by the detector's resolution, FWHM(E)^2 = w0^2 + R662^2 * 662 * E
    (so a scintillator has FWHM proportional to sqrt(E), the Knoll rule, and a germanium detector adds a noise
    term w0). The MCA has `nch` channels of `gain` keV starting at `off` keV. Counts are Poisson numbers drawn from
    the lab's own `seed`."""

    PARAMS = {"src": 0.0, "gain": 2.0, "off": 0.0, "nch": 1024.0, "R662": 0.07, "w0": 0.0, "pf662": 0.35,
              "et662": 0.55, "kE": 0.6, "act": 37.0, "d": 10.0, "rad": 3.81, "t": 100.0, "seed": 5.0, "bg": 0.0,
              "task": 0.0}
    VARS = ["t", "rate", "E0", "fwhm0", "omega"]

    @staticmethod
    def fwhm(e: float, p: dict) -> float:
        return math.sqrt(p["w0"] * p["w0"] + p["R662"] * p["R662"] * 662.0 * e)

    @staticmethod
    def pf(e: float, p: dict) -> float:
        if p["pf662"] <= 0.0:
            return 0.0
        if p["pf662"] >= 1.0:
            return 1.0
        return 1.0 / (1.0 + (e / 662.0) * (1.0 / p["pf662"] - 1.0))

    @staticmethod
    def et(e: float, p: dict) -> float:
        return min(0.98, p["et662"] * math.pow(662.0 / e, p["kE"]))

    @staticmethod
    def omega(p: dict) -> float:
        return 0.5 * (1.0 - p["d"] / math.sqrt(p["d"] * p["d"] + p["rad"] * p["rad"]))

    @staticmethod
    def lines(p: dict) -> list[dict]:
        """Every line of the chosen source with the counts it puts in the photopeak and in the continuum."""
        idx = int(round(p["src"]))
        idx = 0 if idx < 0 else (len(SRC) - 1 if idx >= len(SRC) else idx)
        om = MscGspec.omega(p)
        out = []
        for (e, inten, w) in SRC[idx][1]:
            n = p["t"] * p["act"] * 1000.0 * w * inten * om * MscGspec.et(e, p)
            pf = MscGspec.pf(e, p)
            out.append({"E": e, "I": inten, "w": w, "npk": n * pf, "ncomp": n * (1.0 - pf)})
        return out

    @staticmethod
    def expected(p: dict) -> list[float]:
        """The noise-free spectrum: expected counts in every channel."""
        n = int(round(p["nch"]))
        gain, off = p["gain"], p["off"]
        ex = [p["bg"] * p["t"] * gain] * n
        s2pi = math.sqrt(2.0 * PI)
        for ln in MscGspec.lines(p):
            e0 = ln["E"]
            sg0 = MscGspec.fwhm(e0, p) / 2.3548200450309493
            # the photopeak
            if ln["npk"] > 0:
                lo = max(0, int((e0 - off) / gain - 6.0 * sg0 / gain))
                hi = min(n - 1, int((e0 - off) / gain + 6.0 * sg0 / gain) + 1)
                for i in range(lo, hi + 1):
                    x = off + gain * (i + 0.5) - e0
                    ex[i] += ln["npk"] * gain * math.exp(-0.5 * (x / sg0) ** 2) / (sg0 * s2pi)
            # the Compton continuum (Klein-Nishina electron spectrum), smeared by the resolution
            if ln["ncomp"] > 0:
                al = e0 / ME_KEV
                emin = 1.0 / (1.0 + 2.0 * al)
                raw = [0.0] * n
                tot = 0.0
                for j in range(n):
                    tj = off + gain * (j + 0.5)
                    eps = 1.0 - tj / e0
                    if eps < emin or eps >= 1.0:
                        continue
                    cs = 1.0 - (1.0 / eps - 1.0) / al
                    f = eps + 1.0 / eps - (1.0 - cs * cs)
                    raw[j] = f
                    tot += f
                if tot > 0:
                    for j in range(n):
                        if raw[j] > 0:
                            raw[j] = raw[j] / tot
                    for i in range(n):
                        ei = off + gain * (i + 0.5)
                        sg = MscGspec.fwhm(ei if ei > 1.0 else 1.0, p) / 2.3548200450309493
                        w = int(4.0 * sg / gain) + 1
                        jlo, jhi = max(0, i - w), min(n - 1, i + w)
                        acc = 0.0
                        for j in range(jlo, jhi + 1):
                            if raw[j] > 0:
                                xx = (j - i) * gain
                                acc += raw[j] * math.exp(-0.5 * (xx / sg) ** 2)
                        ex[i] += ln["ncomp"] * acc * gain / (sg * s2pi)
        return ex

    @staticmethod
    def counts(p: dict) -> list[int]:
        rnd = Rnd(p["seed"])
        return [rnd.poisson(m) for m in MscGspec.expected(p)]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ls = MscGspec.lines(p)
        top = MscGspec.main_line(p)
        return {"t": s.get("t", 0.0), "rate": sum(x["npk"] + x["ncomp"] for x in ls) / max(p["t"], 1e-9),
                "E0": top["E"], "fwhm0": MscGspec.fwhm(top["E"], p), "omega": MscGspec.omega(p)}

    @staticmethod
    def main_line(p: dict) -> dict:
        """The line with the tallest photopeak (counts / peak width): what the strongest peak of the spectrum is."""
        best, bh = None, -1.0
        for ln in MscGspec.lines(p):
            h = ln["npk"] / MscGspec.fwhm(ln["E"], p)
            if h > bh:
                bh, best = h, ln
        return best or {"E": 0.0, "I": 0.0, "w": 1.0, "npk": 0.0, "ncomp": 0.0}

    @staticmethod
    def find_peak(ex: list[float], p: dict) -> dict:
        """Look for the tallest peak of a spectrum numerically: its channel and energy (log-parabola through the
        top three channels, exact for a Gaussian), its width at half height above a baseline read 2.2 widths either side
        of it (the lower of the two), and its net area within
        1.25 widths either side."""
        n = len(ex)
        gain, off = p["gain"], p["off"]
        i0, vmax = 1, -1.0
        for i in range(1, n - 1):
            if ex[i] > vmax:
                vmax, i0 = ex[i], i
        a, b, c = ex[i0 - 1], ex[i0], ex[i0 + 1]
        if a > 0 and b > 0 and c > 0:
            la, lb, lc = math.log(a), math.log(b), math.log(c)
            den = la - 2.0 * lb + lc
            dx = 0.5 * (la - lc) / den if den != 0 else 0.0
        else:
            dx = 0.0
        pos = i0 + dx
        epk = off + gain * (pos + 0.5)
        hh = vmax / 2.0
        l = i0
        while l > 0 and ex[l] > hh:
            l -= 1
        r = i0
        while r < n - 1 and ex[r] > hh:
            r += 1
        rough = max(r - l, 2)
        j = max(1, i0 - int(2.2 * rough))
        k = min(n - 2, i0 + int(2.2 * rough))
        bl = min((ex[j - 1] + ex[j] + ex[min(n - 1, j + 1)]) / 3.0, (ex[k - 1] + ex[k] + ex[k + 1]) / 3.0)
        top = vmax - bl
        half = top / 2.0
        l = i0
        while l > 0 and ex[l] - bl > half:
            l -= 1
        y0, y1 = ex[l] - bl, ex[l + 1] - bl
        if y0 > 0 and y1 > 0 and y1 != y0:          # interpolate the logarithm: exact for a Gaussian
            xl = l + (math.log(half) - math.log(y0)) / (math.log(y1) - math.log(y0))
        else:
            xl = l + (half - y0) / (y1 - y0) if y1 != y0 else l
        fw = 2.0 * (pos - xl) * gain
        w = int(1.25 * rough + 0.5)
        area = 0.0
        for i in range(max(0, i0 - w), min(n - 1, i0 + w) + 1):
            area += ex[i] - bl
        return {"chan": pos, "E": epk, "fwhm": fw, "area": area, "height": vmax}

    @staticmethod
    def edge(ex: list[float], p: dict) -> float:
        """Compton edge of a spectrum: the steepest point of the falling side of the continuum (the inflection of a
        sharp edge smeared by the detector's resolution), found numerically."""
        n = len(ex)
        gain, off = p["gain"], p["off"]
        i0, vmax = 1, -1.0
        for i in range(1, n - 1):
            if ex[i] > vmax:
                vmax, i0 = ex[i], i
        best, bi = 0.0, i0
        for i in range(i0, n - 1):
            d = ex[i + 1] - ex[i - 1]
            if d < best:
                best, bi = d, i
        return off + gain * (bi + 0.5)

    @staticmethod
    def measure(p, cfg=None):
        ex = MscGspec.expected(p)
        pk = MscGspec.find_peak(ex, p)
        top = MscGspec.main_line(p)
        flux = p["t"] * p["act"] * 1000.0 * top["w"] * top["I"]
        return {"E_pk": pk["E"], "fwhm_pk": pk["fwhm"], "res_pk": pk["fwhm"] / pk["E"] if pk["E"] > 0 else 0.0,
                "eff_pk": pk["area"] / flux if flux > 0 else 0.0, "edge": MscGspec.edge(ex, p),
                "chan_pk": pk["chan"],
                # what a scintillator comparison reads: the resolution of the photopeak, or (no photopeak at all,
                # as in plastic) the Compton edge
                "cmp_pk": (pk["fwhm"] / pk["E"] if pk["E"] > 0 else 0.0) if p["pf662"] > 0 else MscGspec.edge(ex, p)}


def _gs_E(p: dict) -> float:
    """The textbook energy of the strongest line of the source (nuclear data)."""
    return MscGspec.main_line(p)["E"]


def _gs_fwhm(p: dict) -> float:
    return MscGspec.fwhm(MscGspec.main_line(p)["E"], p)


def _gs_res(p: dict) -> float:
    e = MscGspec.main_line(p)["E"]
    return MscGspec.fwhm(e, p) / e


def _gs_eff(p: dict) -> float:
    e = MscGspec.main_line(p)["E"]
    return MscGspec.omega(p) * MscGspec.et(e, p) * MscGspec.pf(e, p)


def _gs_edge(p: dict) -> float:
    """Klein-Nishina Compton edge of the (only or strongest) line: T = 2 alpha / (1 + 2 alpha) E."""
    e = MscGspec.main_line(p)["E"] if p["pf662"] > 0 else _first_line(p)
    al = e / ME_KEV
    return 2.0 * al / (1.0 + 2.0 * al) * e


def _gs_cmp(p: dict) -> float:
    return _gs_res(p) if p["pf662"] > 0 else _gs_edge(p)


def _first_line(p: dict) -> float:
    idx = int(round(p["src"]))
    return SRC[idx][1][0][0]


# ============================================================================================ microwave bench
def _beta(f: float, a: float, er: float = 1.0) -> float:
    """Phase constant of the TE10 mode of a rectangular guide of broad side `a`, filled with a medium of relative
    permittivity er: beta = sqrt(er k0^2 - (pi / a)^2)."""
    k0 = 2.0 * PI * f / C
    v = er * k0 * k0 - (PI / a) * (PI / a)
    return math.sqrt(v) if v > 0 else 0.0


def _er_from_shift(delta: float, p: dict) -> float:
    """The permittivity that moves the minimum by `delta` (toward the generator) when a slab of length ls sits against
    the short: tan(beta (ls - delta)) = (beta / beta_d) tan(beta_d ls), solved by bisection."""
    b = _beta(p["f"], p["a"])
    k0 = 2.0 * PI * p["f"] / C
    x = math.tan(b * (p["ls"] - delta))
    hi = ((1.55 / p["ls"]) ** 2 + (PI / p["a"]) ** 2) / (k0 * k0)       # beta_d ls < pi / 2: one root
    lo = 1.0001
    for _ in range(80):
        mid = (lo + hi) / 2.0
        bd = _beta(p["f"], p["a"], mid)
        f = (b / bd) * math.tan(bd * p["ls"]) - x
        if f > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


class MscMwLine:
    """A slotted waveguide line (X band, TE10) terminated by a load, with a square-law detector on the probe.

    The standing wave is |E|^2 = 1 + g^2 + 2 g cos(phi - 2 beta s), s the distance from the load plane back toward
    the generator, g and phi the magnitude and phase of the reflection coefficient of the load. The probe at scale
    reading x sees s = xl - x (the load plane xl is the unknown of the bench). A short circuit has g = gs and phi = pi.
    With a dielectric slab of length `ls` and relative permittivity `er` against the short (sam = 1) the load seen
    from the line is the slab: its input reactance is jX, X = (beta / beta_d) tan(beta_d ls), and it moves every
    minimum.

    The reading is the detector current, p0 |E|^2 / 4. `measure` finds the minima, the maxima and the width at
    twice the minimum numerically from that response and works out the guide wavelength, the VSWR (two ways), the
    load impedance and the permittivity, the way the student does."""

    PARAMS = {"f": 9.5e9, "a": 0.02286, "g": 0.5, "phi": 1.0, "gs": 0.995, "xl": 0.1105, "x": 0.05, "p0": 100.0,
              "sam": 0.0, "ls": 0.004, "er": 2.6, "task": 0.0}
    VARS = ["t", "I", "x_mm", "lam_g", "vswr"]

    @staticmethod
    def lam_g(p: dict) -> float:
        return 2.0 * PI / _beta(p["f"], p["a"])

    @staticmethod
    def gamma(p: dict, short: bool) -> tuple[float, float]:
        """Magnitude and phase of the reflection coefficient at the plane the standing wave is measured from."""
        if p["sam"] > 0:
            b = _beta(p["f"], p["a"])
            bd = _beta(p["f"], p["a"], p["er"])
            xr = (b / bd) * math.tan(bd * p["ls"]) if bd > 0 else 0.0
            return p["gs"], PI - 2.0 * math.atan(xr)
        if short:
            return p["gs"], PI
        return p["g"], p["phi"]

    @staticmethod
    def power(p: dict, x: float, short: bool = False) -> float:
        b = _beta(p["f"], p["a"])
        g, ph = MscMwLine.gamma(p, short)
        s = p["xl"] - x - (p["ls"] if p["sam"] > 0 else 0.0)
        return p["p0"] * (1.0 + g * g + 2.0 * g * math.cos(ph - 2.0 * b * s)) / 4.0

    @staticmethod
    def _extrema(p: dict, short: bool, sign: float) -> list[float]:
        """Positions of the minima (sign = 1) or maxima (sign = -1) of the response over the slot (0 to 100 mm):
        a scan every 0.05 mm, then a golden-section search in the bracket."""
        n = 2000
        xs = [0.1 * i / n for i in range(n + 1)]
        ys = [sign * MscMwLine.power(p, x, short) for x in xs]
        out = []
        gr = 0.6180339887498949
        for i in range(1, n):
            if ys[i] < ys[i - 1] and ys[i] <= ys[i + 1]:
                lo, hi = xs[i - 1], xs[i + 1]
                c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
                fc, fd = sign * MscMwLine.power(p, c, short), sign * MscMwLine.power(p, d, short)
                for _ in range(60):
                    if fc < fd:
                        hi, d, fd = d, c, fc
                        c = hi - gr * (hi - lo)
                        fc = sign * MscMwLine.power(p, c, short)
                    else:
                        lo, c, fc = c, d, fd
                        d = lo + gr * (hi - lo)
                        fd = sign * MscMwLine.power(p, d, short)
                out.append((lo + hi) / 2.0)
        return out

    @staticmethod
    def minima(p: dict, short: bool = False) -> list[float]:
        return MscMwLine._extrema(p, short, 1.0)

    @staticmethod
    def maxima(p: dict, short: bool = False) -> list[float]:
        return MscMwLine._extrema(p, short, -1.0)

    @staticmethod
    def width_2min(p: dict, xmin: float) -> float:
        """Distance between the two points either side of a minimum where the power is twice the minimum."""
        pm = MscMwLine.power(p, xmin)
        tot = 0.0
        for direction in (1.0, -1.0):
            lo, hi = 0.0, 0.01
            for _ in range(70):
                mid = (lo + hi) / 2.0
                if MscMwLine.power(p, xmin + direction * mid) < 2.0 * pm:
                    lo = mid
                else:
                    hi = mid
            tot += (lo + hi) / 2.0
        return tot

    @staticmethod
    def zload(s: float, d: float, lam: float) -> tuple[float, float]:
        """Normalised load impedance from the VSWR S and the distance d of the first minimum from the load:
        z = (1 - j S tan(beta d)) / (S - j tan(beta d))."""
        t = math.tan(2.0 * PI * d / lam)
        den = s * s + t * t
        return s * (1.0 + t * t) / den, t * (1.0 - s * s) / den

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": MscMwLine.power(p, p["x"]), "x_mm": p["x"] * 1000.0,
                "lam_g": MscMwLine.lam_g(p) * 1000.0, "vswr": (1.0 + p["g"]) / (1.0 - p["g"])}

    @staticmethod
    def measure(p, cfg=None):
        mins = MscMwLine.minima(p)
        maxs = MscMwLine.maxima(p)
        lam = 2.0 * (mins[1] - mins[0]) if len(mins) > 1 else 0.0
        pmin = min(MscMwLine.power(p, x) for x in mins)
        pmax = max(MscMwLine.power(p, x) for x in maxs)
        vswr = math.sqrt(pmax / pmin)
        half = lam / 2.0
        if p["sam"] > 0:
            ref = MscMwLine.minima(dict(p, sam=0.0), True)
            sh = (ref[0] - mins[0]) % half
            if sh > half / 2.0:
                sh -= half
            er = _er_from_shift(sh, p)
            return {"lam_g": lam, "vswr": vswr, "s_dm": 0.0, "zr": 0.0, "zi": 0.0, "dmin": 0.0, "er": er, "shift": sh,
                    "res": er}
        ref = MscMwLine.minima(p, True)
        delta = (mins[0] - ref[0]) % half                    # the minimum moved toward the load by delta
        dmin = (half - delta) % half
        zr, zi = MscMwLine.zload(vswr, dmin, lam)
        w = MscMwLine.width_2min(p, mins[0])
        sdm = math.sqrt(1.0 + 1.0 / (math.sin(PI * w / lam) ** 2))
        res = [lam, vswr, sdm, zr][int(round(p["task"])) if round(p["task"]) < 4 else 0]
        return {"lam_g": lam, "vswr": vswr, "s_dm": sdm, "zr": zr, "zi": zi, "dmin": dmin, "er": 0.0, "shift": delta,
                "res": res}


def _mw_lamg(p: dict) -> float:
    return MscMwLine.lam_g(p)


def _mw_res(p: dict) -> float:
    """The textbook value of whatever the task asks for: guide wavelength, VSWR (twice), load resistance, or the
    permittivity of the slab."""
    t = int(round(p["task"]))
    if p["sam"] > 0:
        return p["er"]
    if t == 0:
        return MscMwLine.lam_g(p)
    if t in (1, 2):
        return (1.0 + p["g"]) / (1.0 - p["g"])
    return (1.0 - p["g"] * p["g"]) / (1.0 + p["g"] * p["g"] - 2.0 * p["g"] * math.cos(p["phi"]))


# ---- reflex klystron
class MscKlys:
    """A reflex klystron. The electrons leave the cavity at the beam voltage V0 and are turned back by the reflector
    at -vr; the time they spend in the reflector space, in cycles, is N = 2 L f sqrt(2 m V0 / e) / (V0 + vr). The
    tube oscillates only when N is near n + 3/4 (n = 1, 2, 3...): each n is a MODE. Within a mode the power follows
    cos^2(pi dN / 0.75) (zero at dN = +-3/8), falls as 1/N from mode to mode, and the frequency is pulled linearly
    through +-f0 / 2Q (electronic tuning)."""

    PARAMS = {"V0": 300.0, "L": 0.00126, "f0": 9.0e9, "Q": 400.0, "vr": 180.0, "P0": 30.0, "mode": 2.0, "task": 0.0}
    VARS = ["t", "P", "f_GHz", "N"]

    @staticmethod
    def K(p: dict) -> float:
        return 2.0 * p["L"] * p["f0"] * math.sqrt(2.0 * ME * p["V0"] / QE)

    @staticmethod
    def N(p: dict, vr: float) -> float:
        return MscKlys.K(p) / (p["V0"] + vr)

    @staticmethod
    def locate(p: dict, vr: float) -> tuple[int, float]:
        n = MscKlys.N(p, vr)
        k = int(math.floor(n - 0.75 + 0.5))
        return k, n - (k + 0.75)

    @staticmethod
    def power(p: dict, vr: float) -> float:
        k, dn = MscKlys.locate(p, vr)
        if k < 1 or abs(dn) >= 0.375:
            return 0.0
        return p["P0"] * (1.75 / (k + 0.75)) * math.cos(PI * dn / 0.75) ** 2

    @staticmethod
    def freq(p: dict, vr: float) -> float:
        k, dn = MscKlys.locate(p, vr)
        if k < 1 or abs(dn) >= 0.375:
            return p["f0"]
        return p["f0"] - p["f0"] / (2.0 * p["Q"]) * (dn / 0.375)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "P": MscKlys.power(p, p["vr"]), "f_GHz": MscKlys.freq(p, p["vr"]) / 1e9,
                "N": MscKlys.N(p, p["vr"])}

    @staticmethod
    def measure(p, cfg=None):
        """The centre of the chosen mode and its electronic tuning range, found by scanning the reflector voltage."""
        m = int(round(p["mode"]))
        best, vc = -1.0, 0.0
        for i in range(1, 50000):
            vr = i * 0.01
            k, _ = MscKlys.locate(p, vr)
            if k != m:
                continue
            pw = MscKlys.power(p, vr)
            if pw > best:
                best, vc = pw, vr
        half = best / 2.0
        lo = vc
        while lo > 0.01 and MscKlys.power(p, lo) > half:
            lo -= 0.01
        hi = vc
        while MscKlys.locate(p, hi)[0] == m and MscKlys.power(p, hi) > half:
            hi += 0.01
        return {"vr_c": vc, "P_c": best, "f_c": MscKlys.freq(p, vc),
                "et_range": abs(MscKlys.freq(p, lo) - MscKlys.freq(p, hi))}


def _ky_vr(p: dict) -> float:
    return MscKlys.K(p) / (round(p["mode"]) + 0.75) - p["V0"]


# ---- Gunn oscillator
class MscGunn:
    """A Gunn diode. Below the threshold field the current rises with the voltage (resistance R0); above Vth = Eth
    Lg the electrons move to the slow valley, a domain forms and the current falls to a fraction `r` of its peak. The
    domain crosses the transit length in Lg / vd, so the oscillation frequency is vd / Lg. The power peaks at k Vth."""

    PARAMS = {"V": 8.0, "Lg": 10.5e-6, "vd": 1.0e5, "Eth": 3.2e5, "R0": 20.0, "r": 0.7, "Vk": 1.0, "R1": 250.0,
              "Pm": 15.0, "k": 2.7, "task": 0.0}
    VARS = ["t", "I_mA", "P", "f_GHz"]

    @staticmethod
    def vth(p: dict) -> float:
        return p["Eth"] * p["Lg"]

    @staticmethod
    def cur(p: dict, v: float) -> float:
        vt = MscGunn.vth(p)
        if v <= vt:
            return v / p["R0"]
        return vt / p["R0"] * (p["r"] + (1.0 - p["r"]) * math.exp(-(v - vt) / p["Vk"])) + (v - vt) / p["R1"]

    @staticmethod
    def power(p: dict, v: float) -> float:
        vt = MscGunn.vth(p)
        if v <= vt:
            return 0.0
        u = (v - vt) / ((p["k"] - 1.0) * vt)
        return p["Pm"] * u * math.exp(1.0 - u)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I_mA": MscGunn.cur(p, p["V"]) * 1000.0, "P": MscGunn.power(p, p["V"]),
                "f_GHz": (p["vd"] / p["Lg"] / 1e9) if p["V"] > MscGunn.vth(p) else 0.0}

    @staticmethod
    def measure(p, cfg=None):
        """The threshold voltage as the current maximum of a scan, and the bias of greatest power."""
        bi, bv, bp, bpv = -1.0, 0.0, -1.0, 0.0
        for i in range(0, 12001):
            v = i * 0.001
            c = MscGunn.cur(p, v)
            if c > bi:
                bi, bv = c, v
            pw = MscGunn.power(p, v)
            if pw > bp:
                bp, bpv = pw, v
        return {"vth_m": bv, "I_pk": bi, "v_opt": bpv, "P_max": bp, "f": p["vd"] / p["Lg"]}


def _gu_vth(p: dict) -> float:
    return p["Eth"] * p["Lg"]


# ============================================================================================ advanced electronics
class MscOsc:
    """A feedback oscillator: an amplifier of gain A and a frequency-selective feedback network. It oscillates at the
    frequency where the phase of the loop is right, found here by scanning the network's response (not by reading
    the formula back), and only when A is at least the loss of the network at that frequency.

    The network is described by Z(w) = 1 / beta(j w), whose imaginary part must vanish:
      kind 0, RC phase shift (three equal sections):  Z = (1 - 5 a^2) - j (6 a - a^3),  a = 1 / (w R C)
      kind 1, Wien bridge (R, C equal):               Z = 3 + j (x - 1 / x),             x = w R C
      kind 2, Colpitts (L, C1 = C, C2):               Im Z = w L - 1 / w C1 - 1 / w C2,  gain needed C2 / C1
      kind 3, Hartley (L1 = L, L2, M, C):             Im Z = w (L1 + L2 + 2 M) - 1 / (w C), gain needed (L2 + M) / (L1 + M)
    Above the minimum gain the output grows to the supply limit Vsat."""

    PARAMS = {"kind": 1.0, "R": 10000.0, "C": 1.0e-8, "L": 1.0e-3, "C2": 1.0e-8, "L2": 1.0e-3, "M": 0.0, "A": 3.5,
              "Vsat": 12.0, "t": 0.0, "task": 0.0}
    VARS = ["t", "f_kHz", "amin", "vo"]

    @staticmethod
    def zloop(p: dict, w: float) -> tuple[float, float]:
        k = int(round(p["kind"]))
        if k == 0:
            a = 1.0 / (w * p["R"] * p["C"])
            return 1.0 - 5.0 * a * a, -(6.0 * a - a ** 3)
        if k == 1:
            x = w * p["R"] * p["C"]
            return 3.0, x - 1.0 / x
        if k == 2:
            return p["C2"] / p["C"], w * p["L"] - 1.0 / (w * p["C"]) - 1.0 / (w * p["C2"])
        return (p["L2"] + p["M"]) / (p["L"] + p["M"]), w * (p["L"] + p["L2"] + 2.0 * p["M"]) - 1.0 / (w * p["C"])

    @staticmethod
    def solve(p: dict) -> tuple[float, float]:
        """The angular frequency at which Im Z changes sign, and the minimum amplifier gain |Re Z| there."""
        lo_w, hi_w = 1.0e2, 1.0e10
        n = 4000
        prev_w = lo_w
        prev = MscOsc.zloop(p, prev_w)[1]
        for i in range(1, n + 1):
            w = lo_w * math.pow(hi_w / lo_w, i / n)
            cur = MscOsc.zloop(p, w)[1]
            if (prev < 0) != (cur < 0) and prev != 0:
                a, b = prev_w, w
                for _ in range(80):
                    m = math.sqrt(a * b)
                    if (MscOsc.zloop(p, m)[1] < 0) == (MscOsc.zloop(p, a)[1] < 0):
                        a = m
                    else:
                        b = m
                w0 = math.sqrt(a * b)
                return w0, abs(MscOsc.zloop(p, w0)[0])
            prev_w, prev = w, cur
        return 0.0, 0.0

    @staticmethod
    def amplitude(p: dict) -> float:
        w0, amin = MscOsc.solve(p)
        if w0 <= 0 or p["A"] < amin:
            return 0.0
        return p["Vsat"] * math.tanh(2.5 * (p["A"] / amin - 1.0))

    @staticmethod
    def wave(p: dict, t: float) -> float:
        w0, _ = MscOsc.solve(p)
        return MscOsc.amplitude(p) * math.sin(w0 * t)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        w0, amin = MscOsc.solve(p)
        return {"t": s.get("t", 0.0), "f_kHz": w0 / (2.0 * PI) / 1000.0, "amin": amin, "vo": MscOsc.amplitude(p)}

    @staticmethod
    def measure(p, cfg=None):
        w0, amin = MscOsc.solve(p)
        return {"f": w0 / (2.0 * PI), "amin": amin, "vo": MscOsc.amplitude(p)}


def _osc_f(p: dict) -> float:
    k = int(round(p["kind"]))
    if k == 0:
        return 1.0 / (2.0 * PI * math.sqrt(6.0) * p["R"] * p["C"])
    if k == 1:
        return 1.0 / (2.0 * PI * p["R"] * p["C"])
    if k == 2:
        return 1.0 / (2.0 * PI * math.sqrt(p["L"] * p["C"] * p["C2"] / (p["C"] + p["C2"])))
    return 1.0 / (2.0 * PI * math.sqrt((p["L"] + p["L2"] + 2.0 * p["M"]) * p["C"]))


class MscFilt:
    """A filter on the bench, driven by a sine of frequency `f`. kind 0 second-order Sallen-Key low pass, kind 1
    high pass (equal R, C, gain K = 3 - sqrt 2: Butterworth), kind 2 band pass (a high-pass corner at 1/2 pi R C
    followed by a low-pass corner at 1/2 pi R2 C2, buffered), kind 3 all-pass phase shifter, kind 4 passive RC low
    pass, kind 5 passive RC high pass. H(j w) is the exact transfer function; the gain and phase are what a
    voltmeter and a phase meter read. `measure` finds the -3 dB corner by scanning the response."""

    PARAMS = {"kind": 0.0, "R": 10000.0, "C": 1.0e-8, "K": 1.5858, "R2": 1000.0, "C2": 1.0e-8, "f": 1000.0, "task": 0.0}
    VARS = ["t", "gain", "gain_db", "phase"]

    @staticmethod
    def h(p: dict, f: float) -> tuple[float, float]:
        """Gain and phase (degrees) at frequency f."""
        w = 2.0 * PI * f
        k = int(round(p["kind"]))
        s_re, s_im = 0.0, w
        w0 = 1.0 / (p["R"] * p["C"])
        if k in (0, 1):
            # den = s^2 + (3 - K) w0 s + w0^2
            dre = -w * w + w0 * w0
            dim = (3.0 - p["K"]) * w0 * w
            if k == 0:
                nre, nim = p["K"] * w0 * w0, 0.0
            else:
                nre, nim = -p["K"] * w * w, 0.0
        elif k == 2:
            a = w * p["R"] * p["C"]
            b = w * p["R2"] * p["C2"]
            # (j a / (1 + j a)) * (1 / (1 + j b))
            nre, nim = 0.0, a
            dre = 1.0 - a * b
            dim = a + b
        elif k == 3:
            a = w * p["R"] * p["C"]
            nre, nim = 1.0, -a
            dre, dim = 1.0, a
        elif k == 4:
            a = w * p["R"] * p["C"]
            nre, nim = 1.0, 0.0
            dre, dim = 1.0, a
        else:
            a = w * p["R"] * p["C"]
            nre, nim = 0.0, a
            dre, dim = 1.0, a
        den = dre * dre + dim * dim
        re = (nre * dre + nim * dim) / den
        im = (nim * dre - nre * dim) / den
        return math.hypot(re, im), math.degrees(math.atan2(im, re))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        g, ph = MscFilt.h(p, p["f"])
        return {"t": s.get("t", 0.0), "gain": g, "gain_db": 20.0 * math.log10(max(g, 1e-12)), "phase": ph}

    @staticmethod
    def corner(p: dict, falling: bool, ref: float) -> float:
        """The frequency where the gain crosses ref / sqrt 2: scanned over 0.1 Hz to 10 MHz, then bisected. falling
        is True for the crossing where the gain goes down as f rises."""
        n = 3000
        target = ref / math.sqrt(2.0)
        prev_f = 0.1
        prev = MscFilt.h(p, prev_f)[0] - target
        for i in range(1, n + 1):
            f = 0.1 * math.pow(1.0e8, i / n)
            cur = MscFilt.h(p, f)[0] - target
            if (prev > 0 and cur <= 0) if falling else (prev < 0 and cur >= 0):
                a, b = prev_f, f
                for _ in range(80):
                    m = math.sqrt(a * b)
                    c = MscFilt.h(p, m)[0] - target
                    if (c > 0) == (prev > 0):
                        a = m
                    else:
                        b = m
                return math.sqrt(a * b)
            prev_f, prev = f, cur
        return 0.0

    @staticmethod
    def measure(p, cfg=None):
        k = int(round(p["kind"]))
        if k == 3:                                           # the all-pass: where the phase passes -90 degrees
            a, b = 0.1, 1.0e7
            for _ in range(100):
                m = math.sqrt(a * b)
                if MscFilt.h(p, m)[1] > -90.0:
                    a = m
                else:
                    b = m
            return {"fc": math.sqrt(a * b), "fh": 0.0, "h0": 1.0, "slope": 0.0}
        if k in (0, 4):
            h0 = MscFilt.h(p, 0.1)[0]
            fc = MscFilt.corner(p, True, h0)
            g1 = MscFilt.h(p, fc * 30.0)[0]
            g2 = MscFilt.h(p, fc * 300.0)[0]
            return {"fc": fc, "fh": 0.0, "h0": h0, "slope": 20.0 * math.log10(g2 / g1)}
        if k in (1, 5):
            h0 = MscFilt.h(p, 1.0e7)[0]
            fc = MscFilt.corner(p, False, h0)
            g1 = MscFilt.h(p, fc / 30.0)[0]
            g2 = MscFilt.h(p, fc / 300.0)[0]
            return {"fc": fc, "fh": 0.0, "h0": h0, "slope": 20.0 * math.log10(g2 / g1)}
        fm = math.sqrt(1.0 / (p["R"] * p["C"] * p["R2"] * p["C2"])) / (2.0 * PI)
        h0 = MscFilt.h(p, fm)[0]
        lo = MscFilt.corner(p, False, h0)
        hi = MscFilt.corner(p, True, h0)
        return {"fc": lo, "fh": hi, "h0": h0, "slope": 0.0}


def _filt_fc(p: dict) -> float:
    return 1.0 / (2.0 * PI * p["R"] * p["C"])


# ============================================================================================ tables
KERNELS: dict[str, Any] = {"msc_gspec": MscGspec, "msc_mwline": MscMwLine, "msc_klys": MscKlys, "msc_gunn": MscGunn, "msc_osc": MscOsc, "msc_filt": MscFilt}
FAMILY = {"msc_gspec": "em", "msc_mwline": "em", "msc_klys": "em", "msc_gunn": "em", "msc_osc": "circuit", "msc_filt": "circuit"}
TEXTBOOK = {"msc_gs_E": _gs_E, "msc_gs_fwhm": _gs_fwhm, "msc_gs_res": _gs_res, "msc_gs_eff": _gs_eff,
            "msc_gs_edge": _gs_edge, "msc_gs_cmp": _gs_cmp,
            "msc_mw_lamg": _mw_lamg, "msc_mw_res": _mw_res, "msc_ky_vr": _ky_vr, "msc_gu_vth": _gu_vth,
            "msc_osc_f": _osc_f, "msc_filt_fc": _filt_fc}
CALCS: dict[str, dict] = {}
