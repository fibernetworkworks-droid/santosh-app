"""Prayogshala kernel pack: M.Sc. OPTICS, INTERFEROMETRY AND SPECTROSCOPY (every kernel and calc is named `msc_...`).

Interferometers (the `msc-interferometer` rig):
    msc_michelson  a Michelson interferometer with a micrometer-driven mirror. The central intensity is built from the
                   path difference 2(x - z0 - plate) for a laser, a sodium doublet or a white-light band, and the
                   readings are SEARCHED for: fringes counted over a mirror travel (wavelength), visibility minima of the
                   doublet (line separation) and the white-light fringe-contrast peak with and without a plate in one
                   arm (index of the plate).
    msc_gascell    a Mach-Zehnder, Jamin or Michelson interferometer with a gas cell in one arm: fringes counted while
                   the pressure rises from vacuum, whole fringes plus the fraction from the last two maxima.

Spectroscopy (the `msc-spectrograph` rig; each kernel has a static `profile(x, p, mode)` = what the monochromator sees
at x, and `axis(p)` = the range it can scan):
    msc_iodine     I2 B-X vibronic bands in absorption (Morse progression): anharmonicity from the band spacings.
    msc_rovib      rotation-vibration bands of a diatomic gas (HCl with both chlorine isotopes, CO): rotational constant
                   by combination differences, band centre and force constant.
    msc_raman      Stokes and anti-Stokes Raman lines of a liquid: shift, and temperature from the line-height ratio.
    msc_fluor      absorption and emission bands: Stokes shift.
    msc_tauc       transmission of a thin film of a direct-gap semiconductor: optical gap by a Tauc plot.
    msc_varshni    band-edge luminescence at two temperatures: Varshni shift of the gap.
    msc_decay      exponential luminescence decay on an oscilloscope: lifetime.
    msc_glow       a thermoluminescence glow curve (first order): trap depth from the heating-rate shift of the peak.
    msc_beer       Beer-Lambert absorbance of a dye at several concentrations: molar absorptivity.

SI inside the interferometers; the spectra are in the units a student reads (nm, cm^-1, K, ms). Deterministic: no
randomness, no wall clock. The exact JavaScript twin is `app/static/prayog/packs/msc_optics.js`.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
HC_EV_NM = 1239.84198            # h c in eV nm (CODATA)
KB_EV = 8.617333262e-5           # Boltzmann constant in eV / K
C2_CMK = 1.438777                # second radiation constant h c / k in cm K
H_PLANCK = 6.62607015e-34
C_LIGHT = 2.99792458e8
AMU = 1.66053906660e-27


# ------------------------------------------------------------------------------------------------ helpers
def _tern_max(f, lo: float, hi: float, iters: int = 80) -> float:
    for _ in range(iters):
        a1 = lo + (hi - lo) / 3.0
        a2 = hi - (hi - lo) / 3.0
        if f(a1) > f(a2):
            hi = a2
        else:
            lo = a1
    return (lo + hi) / 2.0


def _tern_min(f, lo: float, hi: float, iters: int = 80) -> float:
    return _tern_max(lambda x: -f(x), lo, hi, iters)


def _bisect(f, lo: float, hi: float, iters: int = 80) -> float:
    flo = f(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if flo * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
            flo = f(lo)
    return (lo + hi) / 2.0


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


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _slope(pts: list[list[float]]) -> float:
    n = len(pts)
    if n < 2:
        return 0.0
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    den = n * sxx - sx * sx
    return (n * sxy - sx * sy) / den if den else 0.0


def _line(pts: list[list[float]]) -> tuple[float, float]:
    """(slope, intercept) of y on x."""
    n = len(pts)
    if n < 2:
        return 0.0, 0.0
    m = _slope(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    return m, (sy - m * sx) / n


def _peaks(f, lo: float, hi: float, n: int, thr: float) -> list[list[float]]:
    """Every local maximum of f on [lo, hi] above thr x the highest point, refined: [[x, f(x)], ...]."""
    step = (hi - lo) / n
    ys = [f(lo + i * step) for i in range(n + 1)]
    top = max(ys)
    out = []
    for i in range(1, n):
        if ys[i] > ys[i - 1] and ys[i] >= ys[i + 1] and ys[i] > thr * top:
            x = _tern_max(f, lo + (i - 1) * step, lo + (i + 1) * step, 60)
            out.append([x, f(x)])
    return out


def _gauss(u: float, u0: float, sg: float) -> float:
    z = (u - u0) / sg
    return math.exp(-0.5 * z * z)


class _Base:
    """Time plays no part in these kernels; the studio just calls step()."""

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


# ================================================================================================ Michelson
class MscMichelson(_Base):
    """A Michelson interferometer. The mirror is at micrometer reading x; the arms are equal when x = z0 (plus the
    plate's extra path, (np - 1) tp, when the plate is in the fixed arm). Path difference D = 2 (x - z0 - ins (np-1) tp).
    src 0 = one line lam (laser), 1 = the two lines lam and lam2 (sodium doublet), 2 = white light (a Gaussian band
    of wavenumbers centred on 1/570 nm, 2.2e5 per metre wide). The central spot has I = (1 - V cos(2 pi D / lam)) / 2."""

    PARAMS = {"lam": 6.328e-7, "lam2": 0.0, "np": 1.5168, "tp": 1.0e-3, "z0": 1.0e-3, "src": 0.0, "ins": 0.0,
              "x": 1.0e-3, "D": 2.0e-4}
    VARS = ["inten", "vis", "delta"]
    NU_WHITE = 1.0 / 5.7e-7
    SIG_WHITE = 2.2e5

    @staticmethod
    def delta(p, x: float, ins: float | None = None) -> float:
        i = p["ins"] if ins is None else ins
        return 2.0 * (x - p["z0"] - i * (p["np"] - 1.0) * p["tp"])

    @staticmethod
    def vis_at(p, x: float, src: float | None = None, ins: float | None = None) -> float:
        s = int(p["src"] if src is None else src)
        d = MscMichelson.delta(p, x, ins)
        if s == 0:
            return 1.0
        if s == 1:
            if p["lam2"] <= 0:
                return 1.0
            return abs(math.cos(PI * d * (1.0 / p["lam"] - 1.0 / p["lam2"])))
        return math.exp(-2.0 * PI * PI * MscMichelson.SIG_WHITE ** 2 * d * d)

    @staticmethod
    def inten_at(p, x: float, src: float | None = None, ins: float | None = None) -> float:
        s = int(p["src"] if src is None else src)
        d = MscMichelson.delta(p, x, ins)
        if s == 0:
            return 0.5 * (1.0 - math.cos(2 * PI * d / p["lam"]))
        if s == 1:
            if p["lam2"] <= 0:
                return 0.5 * (1.0 - math.cos(2 * PI * d / p["lam"]))
            return 0.5 * (1.0 - 0.5 * (math.cos(2 * PI * d / p["lam"]) + math.cos(2 * PI * d / p["lam2"])))
        v = math.exp(-2.0 * PI * PI * MscMichelson.SIG_WHITE ** 2 * d * d)
        return 0.5 * (1.0 - v * math.cos(2 * PI * MscMichelson.NU_WHITE * d))

    @staticmethod
    def count(p, x0: float, dist: float) -> int:
        """Bright fringes that pass the centre while the mirror moves dist from x0 (laser line)."""
        step = p["lam"] / 40.0
        n = int(dist / step)
        prev2 = prev = None
        c = 0
        for i in range(n + 1):
            v = MscMichelson.inten_at(p, x0 + i * step, 0, 0)
            if prev2 is not None and prev > prev2 and prev >= v:
                c += 1
            prev2, prev = prev, v
        return c

    @staticmethod
    def minima(p, lo: float, hi: float, step: float) -> list[float]:
        """Positions of the visibility minima of the doublet between lo and hi."""
        n = int((hi - lo) / step)
        f = lambda x: MscMichelson.vis_at(p, x, 1, 0)         # noqa: E731
        vs = [f(lo + i * step) for i in range(n + 1)]
        out = []
        for i in range(1, n):
            if vs[i] < vs[i - 1] and vs[i] <= vs[i + 1]:
                out.append(_tern_min(f, lo + (i - 1) * step, lo + (i + 1) * step, 60))
        return out

    @staticmethod
    def zpd(p, ins: float, lo: float = 0.0, hi: float = 4e-3, step: float = 2.5e-7) -> float:
        """The mirror position where the white-light fringes have their best contrast."""
        n = int((hi - lo) / step)
        f = lambda x: MscMichelson.vis_at(p, x, 2, ins)       # noqa: E731
        bi, bv = 0, -1.0
        for i in range(n + 1):
            v = f(lo + i * step)
            if v > bv:
                bi, bv = i, v
        return _tern_max(f, lo + (bi - 1) * step, lo + (bi + 1) * step, 80)

    @staticmethod
    def view(s, p, cfg=None):
        return {"inten": MscMichelson.inten_at(p, p["x"]), "vis": MscMichelson.vis_at(p, p["x"]),
                "delta": MscMichelson.delta(p, p["x"])}

    @staticmethod
    def measure(p, cfg=None):
        n = MscMichelson.count(p, p["z0"] + 5e-4, p["D"])
        lam = 2.0 * p["D"] / n if n > 0 else 0.0
        dl = 0.0
        if p["lam2"] > 0:
            mins = MscMichelson.minima(p, p["z0"], p["z0"] + 1.6e-3, 2e-6)
            if len(mins) >= 3:
                sp = (mins[2] - mins[0]) / 2.0
                lm = 0.5 * (p["lam"] + p["lam2"])
                dl = lm * lm / (2.0 * sp)
        z1 = MscMichelson.zpd(p, 0.0)
        z2 = MscMichelson.zpd(p, 1.0)
        return {"lam": lam, "N": float(n), "dlam": dl, "dz": z2 - z1, "n": 1.0 + (z2 - z1) / p["tp"]}


def _mich_lam(p) -> float:
    return p["lam"]


def _mich_dline(p) -> float:
    return abs(p["lam2"] - p["lam"])


def _mich_n(p) -> float:
    return p["np"]


# ================================================================================================ gas cell
class MscGasCell(_Base):
    """A gas cell of length L in one arm; the gas has refractive index 1 + dn1 P (P in atmospheres, Gladstone-Dale).
    The beam crosses the cell `arms` times (1 in a Mach-Zehnder or Jamin, 2 in a Michelson); `arch` only chooses the
    drawing. The central intensity is (1 + cos(2 pi arms dn1 P L / lam)) / 2, bright at vacuum."""

    PARAMS = {"lam": 6.328e-7, "L": 0.25, "dn1": 2.7651e-4, "arms": 1.0, "arch": 0.0, "P": 0.0}
    VARS = ["inten", "phase"]

    @staticmethod
    def phase(p, P: float) -> float:
        return 2.0 * PI * p["arms"] * p["dn1"] * P * p["L"] / p["lam"]

    @staticmethod
    def inten_at(p, P: float) -> float:
        return 0.5 * (1.0 + math.cos(MscGasCell.phase(p, P)))

    @staticmethod
    def fringes(p, P1: float) -> float:
        """Fringes that pass while the pressure rises from vacuum to P1: whole bright fringes counted over a fine
        pressure scan, plus the fraction from where the last bright fringe sat."""
        total = MscGasCell.phase(p, P1) / (2 * PI)
        n = int(total * 40) + 40
        step = P1 / n
        f = lambda q: MscGasCell.inten_at(p, q)                # noqa: E731
        vs = [f(i * step) for i in range(n + 1)]
        mx = []
        for i in range(1, n):
            if vs[i] > vs[i - 1] and vs[i] >= vs[i + 1]:
                mx.append(_tern_max(f, (i - 1) * step, (i + 1) * step, 60))
        m = len(mx)
        if m == 0:
            return 0.0
        prev = mx[m - 2] if m >= 2 else 0.0
        return m + (P1 - mx[m - 1]) / (mx[m - 1] - prev)

    @staticmethod
    def view(s, p, cfg=None):
        return {"inten": MscGasCell.inten_at(p, p["P"]), "phase": MscGasCell.phase(p, p["P"])}

    @staticmethod
    def measure(p, cfg=None):
        N = MscGasCell.fringes(p, 1.0)
        return {"N": N, "dn1": N * p["lam"] / (p["arms"] * p["L"])}


def _gas_dn1(p) -> float:
    return p["dn1"]


# ================================================================================================ spectra
class _Spec(_Base):
    """Common to every spectrograph kernel. x is in the unit axis() names; profile(x, p, mode) is the signal there."""

    MODES: list[str] = []
    CONTROL: dict | None = None
    VARS = ["sig"]

    @staticmethod
    def view(s, p, cfg=None):
        return {"sig": 0.0}


# ------------------------------------------------------------------------------------------------ iodine
class MscIodine(_Spec):
    """I2 B <- X absorption in the visible: the v'' = 0 progression of Morse bands
    nu(v') = Te + we'(v'+1/2) - wexe'(v'+1/2)^2 - G''(0), v' = 8 .. 40 (cm^-1), each a Gaussian of 3 cm^-1 sigma.
    The band heights are an illustrative envelope; hot bands and rotational structure are not modelled."""

    PARAMS = {"Te": 15769.01, "we1": 125.69, "wx1": 0.764, "we0": 214.50, "wx0": 0.607, "vlo": 8.0, "vhi": 40.0,
              "sig": 3.0}

    @staticmethod
    def nu_band(p, v: float) -> float:
        return (p["Te"] + p["we1"] * (v + 0.5) - p["wx1"] * (v + 0.5) ** 2
                - (p["we0"] * 0.5 - p["wx0"] * 0.25))

    @staticmethod
    def axis(p):
        return {"lo": 500.0, "hi": 620.0, "n": 6000, "xlabel": "Wavelength (nm)", "unit": "nm", "ylabel": "Absorbance",
                "ymax": 1.15}

    @staticmethod
    def profile(x, p, mode=0):
        nu = 1.0e7 / x
        tot = 0.0
        v = int(p["vlo"])
        while v <= int(p["vhi"]):
            env = math.exp(-0.5 * ((v - 24.0) / 11.0) ** 2)
            tot += env * _gauss(nu, MscIodine.nu_band(p, v), p["sig"])
            v += 1
        return tot

    @staticmethod
    def lines(p, mode=0):
        pk = _peaks(lambda x: MscIodine.profile(x, p), 500.0, 620.0, 6000, 0.03)
        pk.sort(key=lambda a: -a[0])                    # from the red end: rising wavenumber = rising v'
        return [{"k": i + 1, "x": a[0], "y": a[1]} for i, a in enumerate(pk)]

    @staticmethod
    def measure(p, cfg=None):
        ls = MscIodine.lines(p)
        nus = [1.0e7 / l["x"] for l in ls]
        pts = [[i + 0.5, nus[i + 1] - nus[i]] for i in range(len(nus) - 1)]
        m = _slope(pts)
        return {"wx1": -m / 2.0, "nbands": float(len(ls))}


def _iod_wx(p) -> float:
    return p["wx1"]


# ------------------------------------------------------------------------------------------------ rotation-vibration
class MscRovib(_Spec):
    """Rotation-vibration band of a diatomic gas in absorption at temperature T. G(1) - G(0) = we - 2 wexe is the band
    origin, B_v = Be - ae (v + 1/2). R(J) = nu0 + (B1+B0)(J+1) + (B1-B0)(J+1)^2 and P(J) = nu0 - (B1+B0) J + (B1-B0) J^2
    from the lower level J; heights go as (J+1) or J times the Boltzmann factor of the lower level. m3 > 0 adds the
    second isotopologue (wavenumbers x rho, B x rho^2, weight w2 of the first); width is the Gaussian FWHM."""

    PARAMS = {"we": 2990.946, "wx": 52.8186, "Be": 10.59341, "ae": 0.30718, "m1": 1.00782503, "m2": 34.96885268,
              "m3": 36.96590259, "w2": 0.3198, "T": 300.0, "fwhm": 0.6, "Jmax": 22.0, "lo": 2600.0, "hi": 3120.0}

    @staticmethod
    def mu(m1: float, m2: float) -> float:
        return m1 * m2 / (m1 + m2)

    @staticmethod
    def rho(p) -> float:
        if p["m3"] <= 0:
            return 1.0
        return math.sqrt(MscRovib.mu(p["m1"], p["m2"]) / MscRovib.mu(p["m1"], p["m3"]))

    @staticmethod
    def B0(p) -> float:
        return p["Be"] - 0.5 * p["ae"]

    @staticmethod
    def B1(p) -> float:
        return p["Be"] - 1.5 * p["ae"]

    @staticmethod
    def line_list(p, minor: bool):
        r = MscRovib.rho(p) if minor else 1.0
        nu0 = (p["we"] - 2 * p["wx"]) * r
        b0 = MscRovib.B0(p) * r * r
        b1 = MscRovib.B1(p) * r * r
        w = p["w2"] if minor else 1.0
        out = []
        for j in range(0, int(p["Jmax"]) + 1):
            bz = math.exp(-C2_CMK * b0 * j * (j + 1) / p["T"])
            out.append((nu0 + (b1 + b0) * (j + 1) + (b1 - b0) * (j + 1) ** 2, w * (j + 1) * bz))
            if j > 0:
                out.append((nu0 - (b1 + b0) * j + (b1 - b0) * j * j, w * j * bz))
        return out

    @staticmethod
    def axis(p):
        return {"lo": p["lo"], "hi": p["hi"], "n": 8000, "xlabel": "Wavenumber (cm⁻¹)", "unit": "cm⁻¹",
                "ylabel": "Absorbance", "ymax": 1.15}

    @staticmethod
    def profile(x, p, mode=0, major_only=False):
        sg = p["fwhm"] / 2.354820045
        tot = 0.0
        sets = [MscRovib.line_list(p, False)]
        if p["m3"] > 0 and not major_only:
            sets.append(MscRovib.line_list(p, True))
        for ls in sets:
            for nu, a in ls:
                if abs(x - nu) < 8 * sg:
                    tot += a * _gauss(x, nu, sg)
        return tot

    @staticmethod
    def lines(p, mode=0):
        pk = _peaks(lambda x: MscRovib.profile(x, p, 0, True), p["lo"], p["hi"], 8000, 0.02)
        pk.sort(key=lambda a: a[0])
        if len(pk) < 3:
            return []
        gi = max(range(len(pk) - 1), key=lambda i: pk[i + 1][0] - pk[i][0])
        out = []
        for i in range(gi + 1, len(pk)):
            out.append({"k": i - gi, "x": pk[i][0], "y": pk[i][1]})
        for i in range(gi, -1, -1):
            out.append({"k": -(gi - i + 1), "x": pk[i][0], "y": pk[i][1]})
        return out

    @staticmethod
    def kforce(p, nu: float) -> float:
        mu = MscRovib.mu(p["m1"], p["m2"]) * AMU
        return 4 * PI * PI * (C_LIGHT * 100.0 * nu) ** 2 * mu

    @staticmethod
    def measure(p, cfg=None):
        ls = MscRovib.lines(p)
        d = {l["k"]: l["x"] for l in ls}
        num = den = 0.0
        for j in range(1, 6):
            if j in d and -(j + 1) in d:
                xj = j + 0.5
                num += xj * (d[j] - d[-(j + 1)])
                den += xj * xj
        b0 = num / den / 4.0 if den else 0.0
        mid = 0.5 * (d.get(1, 0.0) + d.get(-1, 0.0))
        return {"B0": b0, "numid": mid, "kf": MscRovib.kforce(p, mid) if mid else 0.0}


def _rv_b0(p) -> float:
    return p["Be"] - 0.5 * p["ae"]


def _rv_kf(p) -> float:
    return MscRovib.kforce(p, p["we"] - 2 * p["wx"])


# ------------------------------------------------------------------------------------------------ Raman
class MscRaman(_Spec):
    """Raman lines of a liquid excited at lamL (nm). Lines at +s (Stokes) and -s (anti-Stokes); with nuL = 1e7/lamL the
    anti-Stokes / Stokes ratio is ((nuL + s) / (nuL - s))^4 exp(-hc s / kT). Gaussian lines of width sig (cm^-1).
    Relative heights of the weaker lines are illustrative; the shifts are the literature values."""

    PARAMS = {"s1": 459.0, "a1": 1.0, "s2": 314.0, "a2": 0.45, "s3": 218.0, "a3": 0.35, "T": 300.0, "lamL": 532.0,
              "sig": 4.0}

    @staticmethod
    def components(p):
        nuL = 1.0e7 / p["lamL"]
        out = []
        for s, a in ((p["s1"], p["a1"]), (p["s2"], p["a2"]), (p["s3"], p["a3"])):
            if s > 0 and a > 0:
                out.append((s, a))
                out.append((-s, a * ((nuL + s) / (nuL - s)) ** 4 * math.exp(-C2_CMK * s / p["T"])))
        return out

    @staticmethod
    def axis(p):
        top = max(p["s1"], p["s2"], p["s3"]) + 150.0
        return {"lo": -top, "hi": top, "n": 6000, "xlabel": "Raman shift (cm⁻¹)", "unit": "cm⁻¹",
                "ylabel": "Counts (relative)", "ymax": 1.15}

    @staticmethod
    def profile(x, p, mode=0):
        tot = 0.0
        for s, a in MscRaman.components(p):
            tot += a * _gauss(x, s, p["sig"])
        return tot

    @staticmethod
    def lines(p, mode=0):
        ax = MscRaman.axis(p)
        pk = _peaks(lambda x: MscRaman.profile(x, p), ax["lo"], ax["hi"], ax["n"], 0.002)
        st = sorted([a for a in pk if a[0] > 0], key=lambda a: -a[1])
        out = [{"k": i + 1, "x": a[0], "y": a[1]} for i, a in enumerate(st)]
        if st:
            best = st[0][0]
            near = [a for a in pk if a[0] < 0 and abs(a[0] + best) < 25.0]
            if near:
                out.append({"k": -1, "x": near[0][0], "y": near[0][1]})
        return out

    @staticmethod
    def measure(p, cfg=None):
        ls = MscRaman.lines(p)
        d = {l["k"]: l for l in ls}
        s1 = d[1]["x"] if 1 in d else 0.0
        T = 0.0
        if 1 in d and -1 in d and d[-1]["y"] > 0:
            nuL = 1.0e7 / p["lamL"]
            s = d[1]["x"]
            ratio = ((nuL + s) / (nuL - s)) ** 4 * d[1]["y"] / d[-1]["y"]
            T = C2_CMK * s / math.log(ratio) if ratio > 1 else 0.0
        return {"s1": s1, "T": T}


def _ram_s1(p) -> float:
    return p["s1"]


# ------------------------------------------------------------------------------------------------ fluorescence
class MscFluor(_Spec):
    """Absorption band (mode 0) and emission band (mode 1) of a fluorophore, Gaussian in wavenumber about the stated
    peak wavelengths. sa and se are the sigmas in cm^-1."""

    PARAMS = {"abs": 347.5, "em": 450.0, "sa": 2000.0, "se": 1500.0}
    MODES = ["Absorption", "Emission"]

    @staticmethod
    def axis(p):
        lo = math.floor((min(p["abs"], p["em"]) - 90.0) / 10.0) * 10.0
        hi = math.ceil((max(p["abs"], p["em"]) + 110.0) / 10.0) * 10.0
        return {"lo": lo, "hi": hi, "n": 4000, "xlabel": "Wavelength (nm)", "unit": "nm", "ylabel": "Signal (relative)",
                "ymax": 1.15}

    @staticmethod
    def profile(x, p, mode=0):
        nu = 1.0e7 / x
        if int(mode) == 0:
            return _gauss(nu, 1.0e7 / p["abs"], p["sa"])
        return _gauss(nu, 1.0e7 / p["em"], p["se"])

    @staticmethod
    def lines(p, mode=0):
        ax = MscFluor.axis(p)
        pk = _peaks(lambda x: MscFluor.profile(x, p, mode), ax["lo"], ax["hi"], ax["n"], 0.3)
        return [{"k": int(mode) + 1, "x": a[0], "y": a[1]} for a in pk[:1]]

    @staticmethod
    def measure(p, cfg=None):
        a = MscFluor.lines(p, 0)
        e = MscFluor.lines(p, 1)
        xa = a[0]["x"] if a else 0.0
        xe = e[0]["x"] if e else 0.0
        return {"abs": xa, "em": xe, "stokes": (1.0e7 / xa - 1.0e7 / xe) if xa and xe else 0.0}


def _fl_stokes(p) -> float:
    return 1.0e7 / p["abs"] - 1.0e7 / p["em"]


# ------------------------------------------------------------------------------------------------ Tauc
class MscTauc(_Spec):
    """Transmission T = exp(-alpha t) of a film of thickness t (cm) of a direct-gap semiconductor, with
    (alpha E)^2 = B2 (E - Eg) above the gap and no absorption below (reflection and tails ignored)."""

    PARAMS = {"Eg": 2.42, "B2": 1.7e11, "t": 4.0e-5}

    @staticmethod
    def alpha(p, E: float) -> float:
        return math.sqrt(p["B2"] * (E - p["Eg"])) / E if E > p["Eg"] else 0.0

    @staticmethod
    def axis(p):
        edge = HC_EV_NM / p["Eg"]
        return {"lo": math.floor(edge * 0.75 / 10.0) * 10.0, "hi": math.ceil(edge * 1.25 / 10.0) * 10.0, "n": 3000,
                "xlabel": "Wavelength (nm)", "unit": "nm", "ylabel": "Transmittance", "ymax": 1.05}

    @staticmethod
    def profile(x, p, mode=0):
        return math.exp(-MscTauc.alpha(p, HC_EV_NM / x) * p["t"])

    @staticmethod
    def measure(p, cfg=None):
        ax = MscTauc.axis(p)
        f = lambda x, lvl: MscTauc.profile(x, p) - lvl          # noqa: E731
        x90 = _bisect(lambda x: f(x, 0.9), ax["lo"], ax["hi"])
        x03 = _bisect(lambda x: f(x, 0.03), ax["lo"], ax["hi"])
        e1, e2 = HC_EV_NM / x90, HC_EV_NM / x03
        pts = []
        for i in range(12):
            e = e1 + (e2 - e1) * i / 11.0
            T = MscTauc.profile(HC_EV_NM / e, p)
            a = -math.log(T) / p["t"]
            pts.append([e, (a * e) ** 2])
        m, c = _line(pts)
        return {"Eg": -c / m if m else 0.0}


def _tauc_eg(p) -> float:
    return p["Eg"]


# ------------------------------------------------------------------------------------------------ Varshni
class MscVarshni(_Spec):
    """Band-edge luminescence of a direct-gap semiconductor at temperature T (K): a Gaussian in photon energy centred
    on Eg(T) = Eg0 - al T^2 / (T + be), sigma = 0.8 kT. The peak is taken as the gap."""

    PARAMS = {"Eg0": 1.519, "al": 5.405e-4, "be": 204.0, "T": 300.0}
    CONTROL = {"param": "T", "label": "Sample temperature", "unit": "K", "values": [300.0, 77.0], "digits": 0,
               "scale": 1.0}

    @staticmethod
    def gap(p, T: float) -> float:
        return p["Eg0"] - p["al"] * T * T / (T + p["be"])

    @staticmethod
    def axis(p):
        return {"lo": 780.0, "hi": 920.0, "n": 3000, "xlabel": "Wavelength (nm)", "unit": "nm",
                "ylabel": "Luminescence (relative)", "ymax": 1.15}

    @staticmethod
    def profile(x, p, mode=0):
        sg = 0.8 * KB_EV * p["T"]
        return _gauss(HC_EV_NM / x, MscVarshni.gap(p, p["T"]), sg)

    @staticmethod
    def lines(p, mode=0):
        ax = MscVarshni.axis(p)
        pk = _peaks(lambda x: MscVarshni.profile(x, p), ax["lo"], ax["hi"], ax["n"], 0.3)
        return [{"k": 1, "x": a[0], "y": a[1]} for a in pk[:1]]

    @staticmethod
    def measure(p, cfg=None):
        e = {}
        for T in (300.0, 77.0):
            q = dict(p, T=T)
            ls = MscVarshni.lines(q)
            e[T] = HC_EV_NM / ls[0]["x"] if ls else 0.0
        return {"E300": e[300.0], "E77": e[77.0], "dE": e[77.0] - e[300.0]}


def _vs_dE(p) -> float:
    return MscVarshni.gap(p, 77.0) - MscVarshni.gap(p, 300.0)


# ------------------------------------------------------------------------------------------------ decay
class MscDecay(_Spec):
    """A luminescence decay V0 exp(-t / tau) on an oscilloscope, t in milliseconds, tau in seconds."""

    PARAMS = {"tau": 3.0e-3, "V0": 1.0}

    @staticmethod
    def axis(p):
        return {"lo": 0.0, "hi": 6000.0 * p["tau"], "n": 1200, "xlabel": "Time (ms)", "unit": "ms",
                "ylabel": "Signal (V)", "ymax": 1.1 * p["V0"]}

    @staticmethod
    def profile(x, p, mode=0):
        return p["V0"] * math.exp(-x * 1.0e-3 / p["tau"])

    @staticmethod
    def measure(p, cfg=None):
        ax = MscDecay.axis(p)
        t = _bisect(lambda x: MscDecay.profile(x, p) - p["V0"] / math.e, 0.0, ax["hi"])
        return {"tau": t * 1.0e-3}


def _dec_tau(p) -> float:
    return p["tau"]


# ------------------------------------------------------------------------------------------------ glow curve
class MscGlow(_Spec):
    """First-order (Randall-Wilkins) thermoluminescence: I(T) = s exp(-E / kT) exp(-(s / beta) int_T0^T exp(-E / kT') dT'),
    heated linearly at beta K/s from T0. The integral is done by Simpson's rule at 0.5 K or finer."""

    PARAMS = {"E": 1.0, "s": 1.0e12, "beta": 1.0, "T0": 300.0}
    CONTROL = {"param": "beta", "label": "Heating rate", "unit": "K/s", "values": [0.5, 1.0, 2.0, 4.0], "digits": 1,
               "scale": 1.0}

    @staticmethod
    def _f(p, T: float) -> float:
        return math.exp(-p["E"] / (KB_EV * T))

    @staticmethod
    def integral(p, T: float) -> float:
        if T <= p["T0"]:
            return 0.0
        n = 2 * max(1, int(math.ceil((T - p["T0"]) / 1.0)))
        h = (T - p["T0"]) / n
        s = MscGlow._f(p, p["T0"]) + MscGlow._f(p, T)
        for i in range(1, n):
            s += (4 if i % 2 else 2) * MscGlow._f(p, p["T0"] + i * h)
        return s * h / 3.0

    @staticmethod
    def axis(p):
        return {"lo": 300.0, "hi": 520.0, "n": 220, "xlabel": "Temperature (K)", "unit": "K",
                "ylabel": "TL intensity (relative)", "ymax": 1.15}

    @staticmethod
    def profile(x, p, mode=0):
        return p["s"] * MscGlow._f(p, x) * math.exp(-(p["s"] / p["beta"]) * MscGlow.integral(p, x))

    @staticmethod
    def ln_i(p, T: float) -> float:
        return math.log(p["s"]) - p["E"] / (KB_EV * T) - (p["s"] / p["beta"]) * MscGlow.integral(p, T)

    @staticmethod
    def peak(p) -> float:
        """The top of the glow curve: where the slope of ln I, taken from two nearby points, changes sign."""
        g = lambda T: MscGlow.ln_i(p, T + 0.05) - MscGlow.ln_i(p, T - 0.05)     # noqa: E731
        return _bisect(g, p["T0"] + 10.0, 520.0, 80)

    @staticmethod
    def lines(p, mode=0):
        t = MscGlow.peak(p)
        return [{"k": 1, "x": t, "y": MscGlow.profile(t, p)}]

    @staticmethod
    def measure(p, cfg=None):
        pts = []
        for b in (0.5, 1.0, 2.0, 4.0):
            q = dict(p, beta=b)
            tm = MscGlow.peak(q)
            pts.append([1.0 / tm, math.log(tm * tm / b)])
        return {"E": _slope(pts) * KB_EV, "Tm1": MscGlow.peak(dict(p, beta=1.0))}


def _tl_E(p) -> float:
    return p["E"]


# ------------------------------------------------------------------------------------------------ Beer-Lambert
class MscBeer(_Spec):
    """A dye in a cell of path l (cm) at concentration c (mol/L): A = eps c l at the band peak, Gaussian in wavenumber
    (sigma sg cm^-1, a model shape; the peak wavelength and eps are the literature values)."""

    PARAMS = {"eps": 116000.0, "lam0": 529.8, "sg": 600.0, "c": 5.0e-6, "l": 1.0}
    CONTROL = {"param": "c", "label": "Concentration", "unit": "µM", "values": [1e-6, 2e-6, 3e-6, 4e-6, 5e-6, 6e-6],
               "digits": 0, "scale": 1.0e6}

    @staticmethod
    def axis(p):
        return {"lo": 420.0, "hi": 640.0, "n": 2200, "xlabel": "Wavelength (nm)", "unit": "nm", "ylabel": "Absorbance",
                "ymax": 0.8}

    @staticmethod
    def profile(x, p, mode=0):
        return p["eps"] * p["c"] * p["l"] * _gauss(1.0e7 / x, 1.0e7 / p["lam0"], p["sg"])

    @staticmethod
    def lines(p, mode=0):
        ax = MscBeer.axis(p)
        pk = _peaks(lambda x: MscBeer.profile(x, p), ax["lo"], ax["hi"], ax["n"], 0.3)
        return [{"k": 1, "x": a[0], "y": a[1]} for a in pk[:1]]

    @staticmethod
    def measure(p, cfg=None):
        num = den = 0.0
        for c in (1e-6, 2e-6, 3e-6, 4e-6, 5e-6):
            q = dict(p, c=c)
            ls = MscBeer.lines(q)
            num += c * ls[0]["y"]
            den += c * c
        return {"eps": num / den / p["l"] if den else 0.0}


def _beer_eps(p) -> float:
    return p["eps"]


# ================================================================================================ registration
KERNELS: dict[str, Any] = {
    "msc_michelson": MscMichelson, "msc_gascell": MscGasCell, "msc_iodine": MscIodine, "msc_rovib": MscRovib,
    "msc_raman": MscRaman, "msc_fluor": MscFluor, "msc_tauc": MscTauc, "msc_varshni": MscVarshni,
    "msc_decay": MscDecay, "msc_glow": MscGlow, "msc_beer": MscBeer,
}
FAMILY = {k: "optics" for k in KERNELS}
TEXTBOOK = {
    "msc_mich_lam": _mich_lam, "msc_mich_dline": _mich_dline, "msc_mich_n": _mich_n, "msc_gas_dn1": _gas_dn1,
    "msc_iod_wx": _iod_wx, "msc_rv_b0": _rv_b0, "msc_rv_kf": _rv_kf, "msc_ram_s1": _ram_s1,
    "msc_fl_stokes": _fl_stokes, "msc_tauc_eg": _tauc_eg, "msc_vs_dE": _vs_dE, "msc_dec_tau": _dec_tau,
    "msc_tl_E": _tl_E, "msc_beer_eps": _beer_eps,
}


def _by_k(rows) -> dict[float, float]:
    return {k: x for k, x in _rows(rows, "k", "x")}


def _c_mich_lam(rows, p) -> float:
    return _mean([2.0 * d / n for d, n in _rows(rows, "d", "N") if n > 0])


def _c_mich_dline(rows, p) -> float:
    pts = sorted(_rows(rows, "k", "x"))
    sp = _slope([[a, b] for a, b in pts])
    if sp <= 0 or p["lam2"] <= 0:
        return 0.0
    lm = 0.5 * (p["lam"] + p["lam2"])
    return lm * lm / (2.0 * sp)


def _c_mich_n(rows, p) -> float:
    z1 = _mean([x for k, x in _rows(rows, "k", "x") if k == 0])
    z2 = _mean([x for k, x in _rows(rows, "k", "x") if k == 1])
    if not z1 or not z2 or p["tp"] <= 0:
        return 0.0
    return 1.0 + (z2 - z1) / p["tp"]


def _c_gas_dn1(rows, p) -> float:
    pts = _rows(rows, "P", "N")
    num = sum(a * b for a, b in pts)
    den = sum(a * a for a, b in pts)
    if den <= 0 or p["arms"] <= 0 or p["L"] <= 0:
        return 0.0
    return num / den * p["lam"] / (p["arms"] * p["L"])


def _c_iod_wx(rows, p) -> float:
    pts = sorted(_rows(rows, "k", "x"))
    nus = [(k, 1.0e7 / x) for k, x in pts if x > 0]
    sl = [[0.5 * (nus[i][0] + nus[i + 1][0]), nus[i + 1][1] - nus[i][1]] for i in range(len(nus) - 1)
          if abs(nus[i + 1][0] - nus[i][0] - 1.0) < 1e-9]
    return -_slope(sl) / 2.0


def _c_rot_b(rows, p) -> float:
    d = _by_k(rows)
    num = den = 0.0
    for j in range(1, 8):
        if float(j) in d and float(-(j + 1)) in d:
            xj = j + 0.5
            num += xj * (d[float(j)] - d[float(-(j + 1))])
            den += xj * xj
    return num / den / 4.0 if den else 0.0


def _c_force(rows, p) -> float:
    d = _by_k(rows)
    if 1.0 in d and -1.0 in d:
        return MscRovib.kforce(p, 0.5 * (d[1.0] + d[-1.0]))
    return 0.0


def _c_raman_s(rows, p) -> float:
    return _mean([x for k, x in _rows(rows, "k", "x") if k == 1])


def _c_stokes(rows, p) -> float:
    xa = _mean([x for k, x in _rows(rows, "k", "x") if k == 1])
    xe = _mean([x for k, x in _rows(rows, "k", "x") if k == 2])
    return 1.0e7 / xa - 1.0e7 / xe if xa > 0 and xe > 0 else 0.0


def _c_tauc(rows, p) -> float:
    pts = []
    for x, T in _rows(rows, "x", "y"):
        if x > 0 and 0.005 < T < 0.995 and p["t"] > 0:
            e = HC_EV_NM / x
            a = -math.log(T) / p["t"]
            pts.append([e, (a * e) ** 2])
    m, c = _line(pts)
    return -c / m if m else 0.0


def _c_varshni(rows, p) -> float:
    a = _mean([HC_EV_NM / x for c, x in _rows(rows, "c", "x") if c == 77.0 and x > 0])
    b = _mean([HC_EV_NM / x for c, x in _rows(rows, "c", "x") if c == 300.0 and x > 0])
    return a - b if a and b else 0.0


def _c_decay(rows, p) -> float:
    pts = [[x, math.log(y)] for x, y in _rows(rows, "x", "y") if y > 0]
    m = _slope(pts)
    return -1.0e-3 / m if m < 0 else 0.0


def _c_glow(rows, p) -> float:
    pts = [[1.0 / x, math.log(x * x / c)] for c, x in _rows(rows, "c", "x") if x > 0 and c > 0]
    return _slope(pts) * KB_EV


def _c_beer(rows, p) -> float:
    pts = _rows(rows, "c", "y")
    num = sum(a * b for a, b in pts)
    den = sum(a * a for a, b in pts)
    return num / den / p["l"] if den and p["l"] else 0.0


CALCS: dict[str, dict] = {
    "msc_c_mich_lam": {"label": "wavelength", "unit": "m", "needs": ["d", "N"], "fn": _c_mich_lam},
    "msc_c_mich_dline": {"label": "D-line separation", "unit": "m", "needs": ["k", "x"], "fn": _c_mich_dline},
    "msc_c_mich_n": {"label": "n of the plate", "unit": "", "needs": ["k", "x"], "fn": _c_mich_n},
    "msc_c_gas_dn1": {"label": "n - 1 at 1 atm", "unit": "", "needs": ["P", "N"], "fn": _c_gas_dn1},
    "msc_c_iod_wx": {"label": "wexe'", "unit": "cm-1", "needs": ["k", "x"], "fn": _c_iod_wx},
    "msc_c_rot_b": {"label": "B0", "unit": "cm-1", "needs": ["k", "x"], "fn": _c_rot_b},
    "msc_c_force": {"label": "force constant", "unit": "N/m", "needs": ["k", "x"], "fn": _c_force},
    "msc_c_raman_s": {"label": "Raman shift", "unit": "cm-1", "needs": ["k", "x"], "fn": _c_raman_s},
    "msc_c_stokes": {"label": "Stokes shift", "unit": "cm-1", "needs": ["k", "x"], "fn": _c_stokes},
    "msc_c_tauc": {"label": "optical gap", "unit": "eV", "needs": ["x", "y"], "fn": _c_tauc},
    "msc_c_varshni": {"label": "gap shift", "unit": "eV", "needs": ["c", "x"], "fn": _c_varshni},
    "msc_c_decay": {"label": "lifetime", "unit": "s", "needs": ["x", "y"], "fn": _c_decay},
    "msc_c_glow": {"label": "trap depth", "unit": "eV", "needs": ["c", "x"], "fn": _c_glow},
    "msc_c_beer": {"label": "molar absorptivity", "unit": "L/(mol cm)", "needs": ["c", "y"], "fn": _c_beer},
}
