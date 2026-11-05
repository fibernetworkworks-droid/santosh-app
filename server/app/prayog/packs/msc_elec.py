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
        top three channels, exact for a Gaussian), its width at half height above a baseline read two widths below
        it (the left side only, so a neighbour on the high side cannot lift it), and its net area within
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
        bl = (ex[j - 1] + ex[j] + ex[min(n - 1, j + 1)]) / 3.0
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
                "chan_pk": pk["chan"]}


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


def _first_line(p: dict) -> float:
    idx = int(round(p["src"]))
    return SRC[idx][1][0][0]


# ============================================================================================ tables
KERNELS: dict[str, Any] = {"msc_gspec": MscGspec}
FAMILY = {"msc_gspec": "em"}
TEXTBOOK = {"msc_gs_E": _gs_E, "msc_gs_fwhm": _gs_fwhm, "msc_gs_res": _gs_res, "msc_gs_eff": _gs_eff,
            "msc_gs_edge": _gs_edge}
CALCS: dict[str, dict] = {}
