"""Kernel pack: Ph.D. research techniques - X-ray and electron methods, thin films and vacuum, plasma diagnostics (wave 10).

ONE workstation rig (`px10-workstation`) serves every lab of this pack: the instrument that recorded the data stands
beside a workstation, and the student analyses the record. Every kernel ANALYSES SIMULATED DATA: the instrument
record is generated from a hidden sample value (a film thickness, a stress, a spring constant, a K edge ...) with
seeded noise, and the analysis is the real one a research group would run on it. The hidden value is what the student
measures; it is never shown before the result.

    px10_moseley  X-ray fluorescence lines / absorption edges of Cu, Zn, Zr, Mo, Ag -> Moseley fit (screening, Rydberg)
    px10_ruth     alpha scattering off gold / aluminium foil -> the 1/sin^4(theta/2) law and the nuclear charge
    px10_mwi      quadrature microwave interferometer on an argon discharge -> line-integrated electron density
    px10_profilo  stylus profilometer scan across a film step -> step height and roughness Rq
    px10_stoney   wafer curvature (laser deflection or profilometer) -> film stress by Stoney, thermal stress vs T
    px10_spin     spin coating: thickness against spin speed (Meyerhofer) and radial uniformity (Emslie-Bonner-Peck)
    px10_imp      impedance spectra -> bulk and grain-boundary resistance, relaxation time, activation energy
    px10_rock     high-resolution XRD rocking curve -> perpendicular strain of an epitaxial film, mosaic spread
    px10_qcm      electron-beam evaporation with a quartz crystal monitor (Sauerbrey) -> rate vs beam power, thickness
    px10_afm      AFM: thermal-noise spring constant, adhesion from force curves, roughness, step height
    px10_saed     TEM: camera constant from a gold standard, d-spacings (rings, single-crystal spots), particle size
    px10_stm      STM: lattice spacing from a line profile, barrier height from I(z), surface-state onset from dI/dV

Kernel shape (as the other analysis packs): PARAMS (the instrument's numbers, `n` the amount of data the analysis
uses, `what` the reported result), init computes the whole analysis once, step only advances a clock, view gives
val (the answer of the analysis), exact (the hidden sample value), err, nused and the curves the monitor draws
(cx / cy the record, px / py the points the analysis used). Anything random is the seeded Lehmer generator (16807,
mod 2^31 - 1), never the clock. The JavaScript twin is `app/static/prayog/packs/phd_xfilm_w10.js`: same formulas in
the same order. Every name the registry sees carries the prefix `px10_`.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
_M = 2147483647
QE = 1.602176634e-19          # C, exact (SI 2019)
H = 6.62607015e-34            # J s, exact (SI 2019)
HBAR = H / (2.0 * PI)
KB = 1.380649e-23             # J/K, exact (SI 2019)
ME = 9.1093837015e-31         # kg, CODATA 2018
EPS0 = 8.8541878128e-12       # F/m, CODATA 2018
C_LIGHT = 299792458.0         # m/s, exact
RE = 2.8179403262e-15         # m, classical electron radius, CODATA 2018
NA = 6.02214076e23            # 1/mol, exact


def _i(v: float) -> int:
    return int(math.floor(v + 0.5))


def _err(val: float, exact: float) -> float:
    return abs(val - exact) / max(abs(exact), 1e-30)


def _lcg(seed: float) -> list[float]:
    s = _i(seed) % _M
    return [float(s if s > 0 else 1)]


def _u(st: list[float]) -> float:
    st[0] = (st[0] * 16807.0) % _M
    return st[0] / _M


def _gauss(st: list[float]) -> float:
    u1 = _u(st)
    u2 = _u(st)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * PI * u2)


def _thin(xs: list[float], m: int) -> list[float]:
    n = len(xs)
    if n <= m + 1:
        return list(xs)
    return [xs[_i(i * (n - 1) / m)] for i in range(m + 1)]


def _line(xs: list[float], ys: list[float]) -> list[float]:
    """Least-squares straight line y = a + b x, summed left to right (the JS twin sums the same way)."""
    n = len(xs)
    if n < 2:
        return [0.0, 0.0]
    sx = 0.0
    sy = 0.0
    sxx = 0.0
    sxy = 0.0
    for k in range(n):
        sx += xs[k]
        sy += ys[k]
        sxx += xs[k] * xs[k]
        sxy += xs[k] * ys[k]
    den = n * sxx - sx * sx
    if abs(den) < 1e-300:
        return [0.0, 0.0]
    b = (n * sxy - sx * sy) / den
    return [(sy - b * sx) / n, b]


def _solve3(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination on a 3 x 3 system (no pivoting needed for the normal equations used here)."""
    m = [[A[r][0], A[r][1], A[r][2], b[r]] for r in range(3)]
    for c in range(3):
        piv = c
        for r in range(c + 1, 3):
            if abs(m[r][c]) > abs(m[piv][c]):
                piv = r
        if piv != c:
            m[c], m[piv] = m[piv], m[c]
        if abs(m[c][c]) < 1e-300:
            return [0.0, 0.0, 0.0]
        for r in range(c + 1, 3):
            f = m[r][c] / m[c][c]
            for k in range(c, 4):
                m[r][k] -= f * m[c][k]
    x = [0.0, 0.0, 0.0]
    for r in range(2, -1, -1):
        s = m[r][3]
        for k in range(r + 1, 3):
            s -= m[r][k] * x[k]
        x[r] = s / m[r][r]
    return x


def _quad(xs: list[float], ys: list[float]) -> list[float]:
    """Least-squares parabola y = c0 + c1 x + c2 x^2."""
    s0 = s1 = s2 = s3 = s4 = t0 = t1 = t2 = 0.0
    for k in range(len(xs)):
        x = xs[k]
        y = ys[k]
        x2 = x * x
        s0 += 1.0
        s1 += x
        s2 += x2
        s3 += x2 * x
        s4 += x2 * x2
        t0 += y
        t1 += x * y
        t2 += x2 * y
    return _solve3([[s0, s1, s2], [s1, s2, s3], [s2, s3, s4]], [t0, t1, t2])


def _peak(xs: list[float], ys: list[float], k: int, m: int, logp: bool) -> list[float]:
    """Centre and height of a peak at index k from a parabola through the points k - m, k, k + m (on log y for a
    Gaussian line, on y itself otherwise)."""
    n = len(ys)
    if k - m < 0 or k + m > n - 1:
        return [xs[k], ys[k]]
    a, b, c = ys[k - m], ys[k], ys[k + m]
    if logp:
        if a <= 0 or b <= 0 or c <= 0:
            return [xs[k], ys[k]]
        a, b, c = math.log(a), math.log(b), math.log(c)
    den = a - 2.0 * b + c
    dx = 0.5 * (a - c) / den if den != 0 else 0.0
    if dx > 1.0:
        dx = 1.0
    if dx < -1.0:
        dx = -1.0
    top = b - 0.25 * (a - c) * dx
    if logp:
        top = math.exp(top)
    return [xs[k] + dx * (xs[k + m] - xs[k]), top]


def _argmax(ys: list[float], lo: int, hi: int) -> int:
    b = lo
    for k in range(lo, hi + 1):
        if ys[k] > ys[b]:
            b = k
    return b


def _gfit(xs: list[float], ys: list[float], k: int, bg: float) -> list[float]:
    """Gaussian line fit: a least-squares parabola through ln(y - bg) of every point of the peak at index k that stands
    above half its height; returns [centre, FWHM, height]. FWHM = sqrt(-4 ln 2 / c2)."""
    n = len(ys)
    half = bg + 0.5 * (ys[k] - bg)
    lo = k
    while lo > 0 and ys[lo - 1] > half:
        lo -= 1
    hi = k
    while hi < n - 1 and ys[hi + 1] > half:
        hi += 1
    if hi - lo < 2:
        lo = max(0, k - 1)
        hi = min(n - 1, k + 1)
    X, Y = [], []
    for j in range(lo, hi + 1):
        if ys[j] - bg > 0:
            X.append(xs[j] - xs[k])
            Y.append(math.log(ys[j] - bg))
    c = _quad(X, Y)
    if c[2] >= 0:
        return [xs[k], 0.0, ys[k]]
    x0 = -c[1] / (2.0 * c[2])
    top = math.exp(c[0] - c[1] * c[1] / (4.0 * c[2])) + bg
    return [xs[k] + x0, math.sqrt(-4.0 * math.log(2.0) / c[2]), top]


def _base(val: float, exact: float, nused: float, cx: list, cy: list, px: list, py: list, **extra) -> dict:
    s = {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(nused),
         "cx": cx, "ce": [], "cy": cy, "px": px, "py": py}
    s.update(extra)
    return s


class _Base:
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @classmethod
    def step(cls, s, p, dt, cfg=None):
        s["t"] += dt

    @classmethod
    def view(cls, s, p, cfg=None):
        return dict(s)

    @classmethod
    def measure(cls, p, cfg=None):
        s = cls.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ Moseley
# K-alpha1 and K-edge energies (keV) of Cu, Zn, Zr, Mo, Ag - from memory - verify against the NIST X-ray transition
# energies database (Deslattes et al., Rev. Mod. Phys. 75 (2003) 35).
MOS_Z = [29.0, 30.0, 40.0, 42.0, 47.0]
MOS_KA = [8.04778, 8.63886, 15.77508, 17.47934, 22.16292]
MOS_KE = [8.97890, 9.65860, 17.99760, 19.99950, 25.51400]


def _mos_fit(Es: list[float], edge: bool) -> list[float]:
    """sqrt(E / eV) = sqrt(c R) (Z - sigma): c = 3/4 for K-alpha (n = 2 -> 1), 1 for the K edge (n = inf -> 1).
    Returns [sigma, R in eV]."""
    xs = list(MOS_Z)
    ys = [math.sqrt(e * 1000.0) for e in Es]
    ln = _line(xs, ys)
    b = ln[1]
    sig = -ln[0] / b if b != 0 else 0.0
    R = b * b if edge else 4.0 * b * b / 3.0
    return [sig, R]


def _mos_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 2:
        return MOS_KE[max(0, min(4, _i(p["k"])))]
    edge = _i(p["method"]) == 1
    f = _mos_fit(MOS_KE if edge else MOS_KA, edge)
    return f[1] if w == 1 else f[0]


def _mos_spec(p: dict, j: int, edge: bool, n: int, st: list[float]) -> list[list[float]]:
    """One SIMULATED spectrum: counts against energy (keV) for element j. Fluorescence: a Gaussian K-alpha line of
    FWHM fw on a flat background. Edge: transmission of a foil, mu t ~ E^-2.7 with a jump of ratio rj at the edge,
    smeared by the detector resolution (tanh of width fw / 3)."""
    Em = p["Emax"]
    xs, ys = [], []
    for c in range(n):
        E = Em * (c + 0.5) / n
        if edge:
            Ek = MOS_KE[j]
            mu = p["mt"] * (E / Ek) ** -2.7 * (1.0 + (p["rj"] - 1.0) * 0.5 * (1.0 + math.tanh((E - Ek) / (p["fw"] / 3.0))))
            y = math.exp(-mu)
        else:
            y = 0.02 + math.exp(-4.0 * math.log(2.0) * (E - MOS_KA[j]) ** 2 / (p["fw"] * p["fw"]))
        xs.append(E)
        ys.append(y * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0)))
    return [xs, ys]


def _mos_find(p: dict, xs: list[float], ys: list[float], edge: bool) -> float:
    n = len(xs)
    dE = xs[1] - xs[0]
    if edge:
        d = [0.0] * n
        for c in range(1, n - 1):
            if ys[c - 1] > 1e-200 and ys[c + 1] > 1e-200:
                d[c] = (math.log(ys[c - 1]) - math.log(ys[c + 1])) / (2.0 * dE)
        lo = max(1, _i(4.0 / dE))
        k = _argmax(d, lo, n - 2)
        m = max(1, _i(0.25 * p["fw"] / dE))
        return _peak(xs, d, k, m, False)[0]
    lo = ys[0]
    for y in ys:
        if y < lo:
            lo = y
    z = [y - lo for y in ys]
    k = _argmax(z, 0, n - 1)
    m = max(1, _i(0.4 * p["fw"] / dE))
    return _peak(xs, z, k, m, True)[0]


class PxMoseley(_Base):
    """Moseley's law from SIMULATED energy-dispersive spectra. method 0: the K-alpha fluorescence line of each element;
    method 1: the K absorption edge in the transmission of a foil of each element. Each line / edge is located in its
    spectrum (n channels over 0 - Emax), then sqrt(E) is fitted against Z. what = 0 screening constant sigma, 1 the
    Rydberg energy from the slope (eV), 2 the K-edge energy of element k (keV). The reference (`exact`) is the same
    analysis applied to the tabulated energies (or the tabulated edge itself)."""
    PARAMS = {"what": 0.0, "k": 0.0, "method": 0.0, "n": 2048.0, "Emax": 30.0, "fw": 0.16, "mt": 0.6, "rj": 7.0,
              "noise": 0.01, "seed": 11.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(64, _i(p["n"]))
        w = _i(p["what"])
        edge = w == 2 or _i(p["method"]) == 1
        st = _lcg(p["seed"])
        Es = []
        last = [[], []]
        for j in range(5):
            sp = _mos_spec(p, j, edge, n, st)
            Es.append(_mos_find(p, sp[0], sp[1], edge))
            if w == 2 and j == max(0, min(4, _i(p["k"]))):
                last = sp
            elif w != 2 and j == 4:
                last = sp
        f = _mos_fit(Es, edge)
        val = Es[max(0, min(4, _i(p["k"])))] if w == 2 else f[1] if w == 1 else f[0]
        px = list(MOS_Z)
        py = [math.sqrt(e * 1000.0) for e in Es]
        b = math.sqrt(f[1] if edge else 0.75 * f[1])
        fx = [MOS_Z[0] - 2.0, MOS_Z[4] + 2.0]
        fy = [b * (fx[0] - f[0]), b * (fx[1] - f[0])]
        return _base(val, _mos_exact(p), n, _thin(last[0], 400), _thin(last[1], 400), px, py, fit=[fx, fy],
                     energies=Es, sigma=f[0], R=f[1])


# ============================================================================================ Rutherford scattering
def _ruth_ds(Z: float, E: float, th: float) -> float:
    """Rutherford cross-section (m^2/sr) of an alpha (z = 2) of kinetic energy E (MeV) on a fixed point nucleus Z:
    (z Z e^2 / (16 pi eps0 E))^2 / sin^4(theta/2)."""
    a = 2.0 * Z * QE * QE / (16.0 * PI * EPS0 * E * 1.0e6 * QE)
    return a * a / math.sin(th / 2.0) ** 4


RUTH_TH = [20.0, 30.0, 45.0, 60.0, 75.0, 90.0, 120.0, 150.0]


def _ruth_counts(p: dict, Z: float, nt: float, st: list[float]) -> list[float]:
    T = p["n"] * 3600.0
    out = []
    for th in RUTH_TH:
        lam = p["N0"] * nt * _ruth_ds(Z, p["E"], th * PI / 180.0) * p["dO"] * T
        c = lam + math.sqrt(lam) * _gauss(st)
        out.append(c if c > 1.0 else 1.0)
    return out


def _ruth_exact(p: dict) -> float:
    return p["Z"] if _i(p["what"]) == 1 else 4.0


class PxRuth(_Base):
    """SIMULATED alpha scattering: a collimated beam of N0 alphas/s of energy E (MeV) on a foil of nt atoms/m^2,
    a detector of solid angle dO at eight angles, counted for n hours each (Poisson counts, seeded). what = 0: the
    exponent m of N ~ sin^-m(theta/2) from a straight line through ln N against ln sin(theta/2) (the law says 4);
    what = 1: the nuclear charge Z of the foil from its counts against a gold foil (Z = 79) in the same geometry:
    Z = 79 sqrt(<(N / nt) / (N_Au / nt_Au)>). The target recoil is neglected (a fixed nucleus) in the data and in the
    analysis alike."""
    PARAMS = {"what": 0.0, "Z": 79.0, "nt": 1.181e23, "ntr": 1.181e23, "E": 5.486, "N0": 1.0e7, "dO": 0.01,
              "n": 4.0, "seed": 5.0}

    @staticmethod
    def init(p, cfg=None):
        st = _lcg(p["seed"])
        C = _ruth_counts(p, p["Z"], p["nt"], st)
        xs = [math.log(math.sin(th * PI / 360.0)) for th in RUTH_TH]
        ys = [math.log(c) for c in C]
        ln = _line(xs, ys)
        m = -ln[1]
        Zf = p["Z"]
        if _i(p["what"]) == 1:
            Cr = _ruth_counts(p, 79.0, p["ntr"], st)
            s = 0.0
            for k in range(len(C)):
                s += (C[k] / p["nt"]) / (Cr[k] / p["ntr"])
            Zf = 79.0 * math.sqrt(s / len(C))
        val = Zf if _i(p["what"]) == 1 else m
        cx = [xs[0] - 0.1, xs[len(xs) - 1] + 0.05]
        cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]]
        return _base(val, _ruth_exact(p), len(C), cx, cy, xs, ys, counts=C, slope=ln[1], Zfit=Zf)


# ============================================================================================ microwave interferometry
def _mwi_nc(f: float) -> float:
    w = 2.0 * PI * f
    return EPS0 * ME * w * w / (QE * QE)


class PxMwi(_Base):
    """SIMULATED quadrature (I / Q) microwave interferometer across an argon discharge of path L: the density of a
    uniform slab rises as n(t) = (NL / L)(1 - exp(-(t - t0) / tau)) after the discharge is struck at t0; the probe
    phase is phi = phi0 + (2 pi / lambda) L (1 - sqrt(1 - n / nc)), nc = eps0 me w^2 / e^2. The analysis unwraps
    atan2(Q, I) sample by sample (it fails when the phase moves more than pi between samples), takes the phase
    change between the first and the last tenth of the record and inverts the slab formula for the line-integrated
    density NL (m^-2). n = samples in the record."""
    PARAMS = {"NL": 5.0e17, "L": 0.10, "f": 35.0e9, "tau": 0.002, "T": 0.2, "t0": 0.02, "phi0": 0.7, "n": 2000.0,
              "noise": 0.02, "seed": 7.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(20, _i(p["n"]))
        st = _lcg(p["seed"])
        nc = _mwi_nc(p["f"])
        lam = C_LIGHT / p["f"]
        n0 = p["NL"] / p["L"]
        ts, ph = [], []
        prev = 0.0
        acc = 0.0
        for k in range(n):
            t = p["T"] * k / (n - 1)
            dens = n0 * (1.0 - math.exp(-(t - p["t0"]) / p["tau"])) if t > p["t0"] else 0.0
            phi = p["phi0"] + 2.0 * PI / lam * p["L"] * (1.0 - math.sqrt(1.0 - dens / nc))
            I = math.cos(phi) + p["noise"] * _gauss(st)
            Q = math.sin(phi) + p["noise"] * _gauss(st)
            a = math.atan2(Q, I)
            if k == 0:
                acc = a
            else:
                d = a - prev
                while d > PI:
                    d -= 2.0 * PI
                while d < -PI:
                    d += 2.0 * PI
                acc += d
            prev = a
            ts.append(t)
            ph.append(acc)
        m0 = max(1, n // 20)
        m1 = max(1, n // 10)
        a0 = 0.0
        for k in range(m0):
            a0 += ph[k]
        a0 /= m0
        a1 = 0.0
        for k in range(n - m1, n):
            a1 += ph[k]
        a1 /= m1
        dphi = a1 - a0
        q = 1.0 - dphi * lam / (2.0 * PI * p["L"])
        dens = nc * (1.0 - q * q) if q > 0 else nc
        NL = dens * p["L"]
        approx = dphi / (RE * lam)
        return _base(NL, p["NL"], n, _thin(ts, 400), _thin(ph, 400), [], [], dphi=dphi, approx=approx,
                     nc=nc, fringes=dphi / (2.0 * PI))


# ============================================================================================ stylus profilometry
PRO_W = [7.3, 11.9, 17.1, 23.7, 31.3]          # roughness wavelengths (um) of the simulated surface
PRO_A = [1.0, 0.8, 0.6, 0.5, 0.4]


def _pro_surface(p: dict) -> list[list[float]]:
    st = _lcg(p["seed"])
    s2 = 0.0
    for a in PRO_A:
        s2 += a * a / 2.0
    sc = p["rq"] / math.sqrt(s2)
    amp = [a * sc for a in PRO_A]
    ph = [2.0 * PI * _u(st) for _ in PRO_A]
    return [amp, ph]


def _pro_z(p: dict, sf: list[list[float]], x: float) -> float:
    z = p["tilt"] * x + (p["h"] if x > p["xs"] else 0.0)
    for j in range(len(PRO_W)):
        z += sf[0][j] * math.sin(2.0 * PI * x / PRO_W[j] + sf[1][j])
    return z


def _pro_exact(p: dict) -> float:
    return p["rq"] if _i(p["what"]) == 1 else p["h"]


class PxProfilo(_Base):
    """SIMULATED stylus profilometer scan (n points over Lscan um, heights read to lc nm) across the edge of a film:
    a step of height h at xs, a sample tilt and a surface roughness made of five sine waves of total rms rq. The
    analysis levels the scan with one common slope and two levels fitted to the regions either side of the step (10 %
    of the scan kept away from the edge and the ends): the level difference is the step height; the rms of the
    residuals is the roughness Rq. what = 0 step height (nm), 1 roughness Rq (nm). The stylus is treated as a point
    (no tip convolution)."""
    PARAMS = {"what": 0.0, "h": 100.0, "rq": 1.2, "tilt": 0.2, "xs": 1000.0, "Lscan": 2000.0, "lc": 0.1, "n": 4000.0,
              "seed": 13.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(50, _i(p["n"]))
        sf = _pro_surface(p)
        L = p["Lscan"]
        xs, zs = [], []
        for k in range(n):
            x = L * k / (n - 1)
            xs.append(x)
            zs.append(p["lc"] * _i(_pro_z(p, sf, x) / p["lc"]))
        A = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        b = [0.0, 0.0, 0.0]
        used = []
        for k in range(n):
            x = xs[k]
            if (0.05 * L <= x <= p["xs"] - 0.05 * L) or (p["xs"] + 0.05 * L <= x <= 0.95 * L):
                s = 1.0 if x > p["xs"] else 0.0
                v = [1.0, s, x]
                for r in range(3):
                    for c in range(3):
                        A[r][c] += v[r] * v[c]
                    b[r] += v[r] * zs[k]
                used.append(k)
        c = _solve3(A, b)
        q = 0.0
        for k in used:
            s = 1.0 if xs[k] > p["xs"] else 0.0
            r = zs[k] - c[0] - c[1] * s - c[2] * xs[k]
            q += r * r
        rq = math.sqrt(q / len(used)) if used else 0.0
        val = rq if _i(p["what"]) == 1 else c[1]
        lev = [zs[k] - c[2] * xs[k] - c[0] for k in range(n)]
        return _base(val, _pro_exact(p), len(used), _thin(xs, 400), _thin(lev, 400), [], [], step=c[1], Rq=rq,
                     slope=c[2])


# ============================================================================================ film stress (Stoney)
STO_T = [25.0, 75.0, 125.0, 175.0, 225.0]


def _sto_sigma(p: dict, T: float) -> float:
    """Film stress (MPa) at temperature T (C): the residual stress at T0 plus the thermal mismatch stress
    Mf (alpha_s - alpha_f)(T - T0) = -Mf daf (T - T0)."""
    return p["sig"] - p["Mf"] * 1000.0 * p["daf"] * (T - p["T0"])


def _sto_k(p: dict, sigma: float) -> float:
    """Curvature change (1/m) a film stress sigma (MPa) gives by Stoney: dk = 6 sigma tf / (Ms ts^2)."""
    return 6.0 * sigma * 1.0e6 * p["tf"] * 1.0e-6 / (p["Ms"] * 1.0e9 * (p["ts"] * 1.0e-6) ** 2)


def _sto_read(p: dict, kappa: float, n: int, st: list[float]) -> float:
    """Measured curvature (1/m). method 0: two parallel laser beams d apart, spots on a screen L away, their separation
    D = d + 2 L d kappa read n times (noise sd 0.02 mm); method 1: a profilometer scan of n points over +-40 mm,
    z = kappa x^2 / 2 + tilt (noise sd 2 nm), a least-squares parabola."""
    if _i(p["method"]) == 1:
        xs, zs = [], []
        for k in range(n):
            x = -0.04 + 0.08 * k / (n - 1)
            xs.append(x)
            zs.append(kappa * x * x / 2.0 + 1.0e-4 * x + 2.0e-9 * _gauss(st))
        c = _quad(xs, zs)
        return 2.0 * c[2]
    s = 0.0
    for k in range(n):
        s += p["d"] + 2.0 * p["Ls"] * p["d"] * kappa + 2.0e-5 * _gauss(st)
    D = s / n
    return (D - p["d"]) / (2.0 * p["Ls"] * p["d"])


def _sto_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        return -p["Mf"] * 1000.0 * p["daf"]
    return p["sig"]


class PxStoney(_Base):
    """SIMULATED wafer-curvature measurement of film stress. The bare wafer's curvature k0 is read first, then with the
    film; Stoney's equation sigma = Ms ts^2 (k - k0) / (6 tf) gives the film stress, Ms = E/(1 - nu) the substrate's
    biaxial modulus. what = 0 residual stress at T0 (MPa); what = 1 the thermal-stress slope d sigma / dT (MPa/K) from
    the stress measured at five temperatures (straight-line fit). method 0 laser deflection, 1 profilometer scan."""
    PARAMS = {"what": 0.0, "method": 0.0, "sig": -250.0, "tf": 0.5, "ts": 525.0, "Ms": 180.5, "Mf": 107.7,
              "daf": 2.05e-5, "T0": 25.0, "k0": 0.0125, "d": 0.02, "Ls": 2.0, "n": 1280.0, "seed": 17.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(5, _i(p["n"]))
        st = _lcg(p["seed"])
        fac = p["Ms"] * 1.0e9 * (p["ts"] * 1.0e-6) ** 2 / (6.0 * p["tf"] * 1.0e-6) / 1.0e6
        k0 = _sto_read(p, p["k0"], n, st)
        Ts = [p["T0"]] if _i(p["what"]) == 0 else list(STO_T)
        sig = []
        for T in Ts:
            k = _sto_read(p, p["k0"] + _sto_k(p, _sto_sigma(p, T)), n, st)
            sig.append(fac * (k - k0))
        if _i(p["what"]) == 1:
            ln = _line(Ts, sig)
            val = ln[1]
            cx = [Ts[0], Ts[len(Ts) - 1]]
            cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]]
        else:
            val = sig[0]
            cx = [0.0, 1.0]
            cy = [sig[0], sig[0]]
        return _base(val, _sto_exact(p), n, cx, cy, list(Ts), sig, k0=k0, fac=fac)


# ============================================================================================ spin coating
SPIN_W = [1000.0, 1500.0, 2000.0, 3000.0, 4000.0, 6000.0]


def _spin_h(p: dict, w: float) -> float:
    """Final thickness (nm) at spin speed w (rpm), Meyerhofer with evaporation: h = K (w / 1000)^-1/2."""
    return p["K"] * (w / 1000.0) ** -0.5


def _ebp_r0(p: dict, r: float, Kf: float, t: float) -> float:
    """Emslie-Bonner-Peck characteristics: a fluid element starting at r0 with h0(r0) moves to
    r = r0 (1 + 4 Kf h0^2 t)^(3/4); find r0 for a given r by bisection."""
    lo, hi = 0.0, r
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        h0 = p["H0"] * 1.0e-6 * (1.0 + p["a"] * (1.0 - (mid / p["R"]) ** 2))
        rr = mid * (1.0 + 4.0 * Kf * h0 * h0 * t) ** 0.75
        if rr < r:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _ebp_h(p: dict, r: float) -> float:
    """Wet-film thickness (m) at radius r after the flow stage: h = h0(r0) / sqrt(1 + 4 Kf h0^2 t)."""
    w = 2.0 * PI * p["w"] / 60.0
    Kf = p["rho"] * w * w / (3.0 * p["eta"])
    r0 = _ebp_r0(p, r, Kf, p["tf"])
    h0 = p["H0"] * 1.0e-6 * (1.0 + p["a"] * (1.0 - (r0 / p["R"]) ** 2))
    return h0 / math.sqrt(1.0 + 4.0 * Kf * h0 * h0 * p["tf"])


def _spin_unif(p: dict, m: int) -> list[float]:
    """Uniformity (max - min) / mean in per cent over m radii from the centre to 0.9 R, and the profile."""
    hs = []
    rs = []
    for k in range(m):
        r = 0.9 * p["R"] * k / (m - 1)
        rs.append(r)
        hs.append(_ebp_h(p, r))
    lo = hs[0]
    hi = hs[0]
    s = 0.0
    for h in hs:
        if h < lo:
            lo = h
        if h > hi:
            hi = h
        s += h
    return [100.0 * (hi - lo) / (s / m), rs, hs]


def _spin_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return 0.5
    if w == 2:
        return _spin_unif(p, 401)[0]
    return _spin_h(p, p["w"])


class PxSpin(_Base):
    """SIMULATED spin-coating series. Thickness: one film per speed (1000 - 6000 rpm), each measured as a step height
    averaged over n profilometer points (noise sd 1.5 nm a point); a straight line through log h against log w gives
    the exponent and the thickness at the working speed w. Meyerhofer's model with solvent evaporation gives
    h = K w^-1/2 (K, set by the solution's viscosity and solids, is the sample's hidden value). Uniformity: the flow
    stage of Emslie, Bonner and Peck (rho w^2 / (3 eta) acting on an initial puddle thicker at the centre by a fraction a,
    for tf seconds) flattens the film; the uniformity (max - min) / mean over 0 - 0.9 R is read at n radii (an
    ellipsometer map). what = 0 thickness at w (nm), 1 the exponent, 2 the uniformity (%)."""
    PARAMS = {"what": 0.0, "K": 520.0, "w": 3000.0, "H0": 20.0, "a": 0.5, "R": 0.0254, "rho": 1000.0, "eta": 0.1,
              "tf": 1.0, "n": 400.0, "seed": 19.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(5, _i(p["n"]))
        w = _i(p["what"])
        if w == 2:
            u = _spin_unif(p, n)
            return _base(u[0], _spin_exact(p), n, [r * 1000.0 for r in u[1]], [h * 1.0e6 for h in u[2]], [], [],
                         unif=u[0])
        st = _lcg(p["seed"])
        xs, ys, hs = [], [], []
        for om in SPIN_W:
            s = 0.0
            for k in range(n):
                s += _spin_h(p, om) + 1.5 * _gauss(st)
            h = s / n
            hs.append(h)
            xs.append(math.log(om / 1000.0))
            ys.append(math.log(h))
        ln = _line(xs, ys)
        beta = -ln[1]
        hw = math.exp(ln[0] + ln[1] * math.log(p["w"] / 1000.0))
        val = beta if w == 1 else hw
        cx = [xs[0], xs[len(xs) - 1]]
        cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]]
        return _base(val, _spin_exact(p), n, cx, cy, xs, ys, beta=beta, hw=hw, hs=hs)


# ============================================================================================ impedance spectroscopy
IMP_T = [523.0, 548.0, 573.0, 598.0, 623.0]
KB_EV = KB / QE


def _imp_R(R: float, Ea: float, T: float, Tr: float) -> float:
    return R * math.exp(Ea / KB_EV * (1.0 / T - 1.0 / Tr))


def _imp_Z(p: dict, T: float, f: float) -> list[float]:
    """Impedance of (Rb || Cb) in series with (Rgb || Cgb) (only the first when arcs = 1) at temperature T."""
    w = 2.0 * PI * f
    re = 0.0
    im = 0.0
    arcs = [[_imp_R(p["Rb"], p["Ea"], T, p["Tr"]), p["Cb"]]]
    if _i(p["arcs"]) == 2:
        arcs.append([_imp_R(p["Rgb"], p["Eg"], T, p["Tr"]), p["Cgb"]])
    for a in arcs:
        x = w * a[0] * a[1]
        re += a[0] / (1.0 + x * x)
        im -= a[0] * x / (1.0 + x * x)
    return [re, im]


def _imp_scan(p: dict, T: float, n: int, st: list[float]) -> list[list[float]]:
    lf0 = math.log10(p["fmin"])
    lf1 = math.log10(p["fmax"])
    m = max(3, _i((lf1 - lf0) * n)) + 1
    ls, re, mi = [], [], []
    for k in range(m):
        lf = lf0 + (lf1 - lf0) * k / (m - 1)
        z = _imp_Z(p, T, 10.0 ** lf)
        g = 1.0 + p["noise"] * (2.0 * _u(st) - 1.0)
        ls.append(lf)
        re.append(z[0] * g)
        mi.append(-z[1] * g)
    return [ls, re, mi]


def _imp_peaks(ls: list[float], mi: list[float], m: int) -> list[list[float]]:
    """Maxima of -Z'' against log f (the largest point within m points either side), highest frequency first:
    [log f, height] by a parabola through 3 points."""
    out = []
    n = len(mi)
    for k in range(n - 2, 0, -1):
        ok = True
        for j in range(max(0, k - m), min(n - 1, k + m) + 1):
            if (j < k and mi[j] >= mi[k]) or (j > k and mi[j] > mi[k]):
                ok = False
                break
        if ok:
            out.append(_peak(ls, mi, k, max(1, m // 2), False))
    return out


def _imp_exact(p: dict) -> float:
    w = _i(p["what"])
    T = p["T"]
    if w == 3:
        return p["Ea"]
    if w == 1:
        return _imp_R(p["Rgb"], p["Eg"], T, p["Tr"])
    if w == 4:
        return _imp_R(p["Rgb"], p["Eg"], T, p["Tr"]) * p["Cgb"]
    Rb = _imp_R(p["Rb"], p["Ea"], T, p["Tr"])
    if w == 2:
        return Rb * p["Cb"]
    return Rb


class PxImp(_Base):
    """SIMULATED impedance spectra (n points per decade, fmin - fmax, multiplicative noise) of a sample modelled as
    (Rb || Cb) in series with (Rgb || Cgb): two semicircles in the Nyquist plane (one for arcs = 1). Each arc's
    -Z'' has its maximum R / 2 at omega = 1 / (R C): the peaks of -Z'' against log f (parabola through three points)
    give the resistances (2 x the peak height) and the relaxation times 1 / (2 pi f_peak). Resistances follow
    Arrhenius, R = R(Tr) exp(Ea / kB (1/T - 1/Tr)); spectra at five temperatures give Ea from ln Rb against 1/T.
    what = 0 bulk resistance (ohm), 1 grain-boundary resistance (ohm), 2 bulk relaxation time (s), 3 activation
    energy of the bulk (eV), 4 grain-boundary relaxation time (s)."""
    PARAMS = {"what": 0.0, "arcs": 2.0, "Rb": 1.0e5, "Cb": 5.0e-12, "Rgb": 4.0e5, "Cgb": 2.0e-8, "Ea": 0.95,
              "Eg": 1.10, "T": 573.0, "Tr": 573.0, "fmin": 0.01, "fmax": 1.0e7, "n": 20.0, "noise": 0.002,
              "seed": 23.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(2, _i(p["n"]))
        w = _i(p["what"])
        st = _lcg(p["seed"])
        if w == 3:
            xs, ys = [], []
            for T in IMP_T:
                sc = _imp_scan(p, T, n, st)
                pk = _imp_peaks(sc[0], sc[2], max(1, _i(0.5 * n)))
                Rb = 2.0 * pk[0][1] if pk else 1.0
                xs.append(1000.0 / T)
                ys.append(math.log(Rb))
            ln = _line(xs, ys)
            Ea = ln[1] * 1000.0 * KB_EV
            cx = [xs[len(xs) - 1], xs[0]]
            cy = [ln[0] + ln[1] * cx[0], ln[0] + ln[1] * cx[1]]
            return _base(Ea, _imp_exact(p), len(xs), cx, cy, xs, ys, Ea=Ea)
        sc = _imp_scan(p, p["T"], n, st)
        pk = _imp_peaks(sc[0], sc[2], max(1, _i(0.5 * n)))
        j = 1 if (w == 1 or w == 4) else 0
        if j < len(pk):
            R = 2.0 * pk[j][1]
            tau = 1.0 / (2.0 * PI * 10.0 ** pk[j][0])
        else:
            R = 0.0
            tau = 0.0
        val = tau if (w == 2 or w == 4) else R
        return _base(val, _imp_exact(p), len(sc[0]), _thin(sc[1], 400), _thin(sc[2], 400), [], [],
                     npeaks=float(len(pk)), R=R, tau=tau)


# ============================================================================================ HRXRD rocking curve
def _rock_thB(p: dict) -> float:
    return math.asin(p["lam"] / (2.0 * p["d"])) * 180.0 / PI


def _rock_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["mos"] * 3600.0
    if w == 2:
        return p["ws"] * 3600.0
    thB = _rock_thB(p) * PI / 180.0
    return -(p["dw"] * PI / 180.0) / math.tan(thB)


class PxRock(_Base):
    """SIMULATED omega rocking curve (n steps over -0.8 ... +0.4 degrees about the substrate's Bragg angle, Cu K-alpha1,
    symmetric 004 reflection) of an epitaxial film on its substrate: a Gaussian substrate peak of FWHM ws and a film
    peak at dw of FWHM sqrt(wf^2 + mos^2) (the film's own width wf - thickness and instrument - and its mosaic spread),
    with seeded counting noise. Analysis: each peak fitted as a Gaussian (a parabola through log counts of its top
    half) for its centre and FWHM. what = 0 perpendicular strain eps = -d_theta cot(theta_B) of the film, 1 mosaic spread
    sqrt(FWHM^2 - wf^2) (arcsec), 2 FWHM of the substrate peak (arcsec; a bare crystal has sub = 1, no film)."""
    PARAMS = {"what": 0.0, "sub": 0.0, "lam": 0.1540562, "d": 0.1357755, "dw": -0.30, "wf": 0.02, "mos": 0.05,
              "ws": 0.006, "If": 0.25, "n": 2400.0, "noise": 0.02, "seed": 29.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(60, _i(p["n"]))
        st = _lcg(p["seed"])
        thB = _rock_thB(p)
        wfm = math.sqrt(p["wf"] * p["wf"] + p["mos"] * p["mos"])
        xs, ys = [], []
        for k in range(n):
            x = -0.8 + 1.2 * k / (n - 1)
            y = 1.0e-4 + math.exp(-4.0 * math.log(2.0) * x * x / (p["ws"] * p["ws"]))
            if _i(p["sub"]) == 0:
                y += p["If"] * math.exp(-4.0 * math.log(2.0) * (x - p["dw"]) ** 2 / (wfm * wfm))
            xs.append(x)
            ys.append(y * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0)))
        dx = xs[1] - xs[0]
        ks = _argmax(ys, 0, n - 1)
        gs = _gfit(xs, ys, ks, 1.0e-4)
        val = gs[1] * 3600.0
        strain = 0.0
        mos = 0.0
        nf = 1
        if _i(p["sub"]) == 0:
            cut = max(1, ks - _i(4.0 * p["ws"] / dx))
            kf = _argmax(ys, 0, cut)
            gf = _gfit(xs, ys, kf, 1.0e-4)
            strain = -((gf[0] - gs[0]) * PI / 180.0) / math.tan(thB * PI / 180.0)
            mos = math.sqrt(max(0.0, gf[1] * gf[1] - p["wf"] * p["wf"])) * 3600.0
            nf = 2
            val = mos if _i(p["what"]) == 1 else strain if _i(p["what"]) == 0 else val
        return _base(val, _rock_exact(p), nf, _thin(xs, 600), _thin(ys, 600), [], [], thB=thB, strain=strain,
                     mosaic=mos, wsub=gs[1] * 3600.0)


# ============================================================================================ e-beam + QCM
QCM_RHOQ = 2648.0             # kg/m3, AT-cut quartz (from memory - verify)
QCM_MUQ = 2.947e10            # Pa, shear modulus of AT-cut quartz (from memory - verify)
QCM_P = [1.0, 1.5, 2.0, 2.5, 3.0]


def _qcm_rate(p: dict, P: float) -> float:
    """Deposition rate on the substrate (nm/s) at beam power P (kW): the illustrative source model r0 exp(-Pa / P)."""
    return p["r0"] * math.exp(-p["Pa"] / P)


def _qcm_cf(p: dict) -> float:
    """Sauerbrey sensitivity: -df / (dm / A) = 2 f0^2 / sqrt(rho_q mu_q) (Hz per kg/m2)."""
    return 2.0 * p["f0"] * p["f0"] / math.sqrt(QCM_RHOQ * QCM_MUQ)


def _qcm_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        s = 0.0
        for P in QCM_P:
            s += _qcm_rate(p, P) * p["Tst"]
        return s
    return _qcm_rate(p, QCM_P[max(0, min(4, _i(p["k"])))])


class PxQcm(_Base):
    """SIMULATED electron-beam evaporation run: the beam power is held at five settings for Tst seconds each while a
    quartz crystal monitor (fundamental f0) beside the substrate is read n times per step (counter noise sd 0.05 Hz).
    The crystal sees rate / tool of the substrate's rate (tooling factor `tool`). Sauerbrey: a mass dm on area A lowers
    the frequency by df = -2 f0^2 dm / (A sqrt(rho_q mu_q)), so a straight line through f against t in each step
    gives the crystal's mass rate and, with the film density rho, the thickness rate; times the tooling factor, the
    substrate's. what = 0 rate at power index k (nm/s), 1 total film thickness after the run (nm)."""
    PARAMS = {"what": 0.0, "k": 2.0, "rho": 4506.0, "f0": 6.0e6, "tool": 1.15, "r0": 6.0, "Pa": 3.5, "Tst": 120.0,
              "n": 240.0, "seed": 31.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(4, _i(p["n"]))
        st = _lcg(p["seed"])
        Cf = _qcm_cf(p)
        f = p["f0"]
        ts, fs = [], []
        rates = []
        tot = 0.0
        t0 = 0.0
        for P in QCM_P:
            rc = _qcm_rate(p, P) / p["tool"] * 1.0e-9           # m/s on the crystal
            xs, ys = [], []
            for k in range(n):
                t = p["Tst"] * k / (n - 1)
                fr = f - Cf * p["rho"] * rc * t + 0.05 * _gauss(st)
                xs.append(t)
                ys.append(fr)
                ts.append(t0 + t)
                fs.append(fr)
            ln = _line(xs, ys)
            r = -ln[1] / (Cf * p["rho"]) * p["tool"] * 1.0e9
            rates.append(r)
            tot += r * p["Tst"]
            f = f - Cf * p["rho"] * rc * p["Tst"]
            t0 += p["Tst"]
        val = tot if _i(p["what"]) == 1 else rates[max(0, min(4, _i(p["k"])))]
        return _base(val, _qcm_exact(p), n, _thin(ts, 400), _thin(fs, 400), list(QCM_P), rates, rates=rates,
                     thick=tot, Cf=Cf)


# ============================================================================================ AFM
def _afm_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["Fad"]
    if w == 2:
        return p["rq"]
    if w == 3:
        return p["h"]
    return p["k"]


class PxAfm(_Base):
    """SIMULATED AFM data. The optical-lever sensitivity InvOLS (nm/V) is the inverse slope of deflection against piezo
    travel on the hard contact part of a force curve (n points). what = 0 spring constant from the thermal noise:
    k = kB T / <z^2>, z = InvOLS x the deflection signal, n samples of the free cantilever (equipartition, without the
    0.817 first-mode optical-lever correction); what = 1 adhesion force F = k InvOLS dV from the pull-off jump of the
    retract curve (k from the thermal tune), n points per curve; what = 2 roughness Rq of a polymer film (tapping-mode
    line scans, plane levelled), what = 3 step height of a flake on its substrate (two-level fit) - n points a line."""
    PARAMS = {"what": 0.0, "k": 2.0, "inv": 50.0, "T": 296.15, "Fad": 15.0, "rq": 0.8, "h": 0.65, "n": 131072.0,
              "seed": 37.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(64, _i(p["n"]))
        w = _i(p["what"])
        st = _lcg(p["seed"])
        # ---- force curve, contact part: deflection V = (z - z0) / inv, z0 = 20 nm, 0.5 % noise of 1 V
        zs, vs = [], []
        for k in range(min(n, 4096)):
            z = 20.0 + 80.0 * k / (min(n, 4096) - 1)
            zs.append(z)
            vs.append((z - 20.0) / p["inv"] + 0.005 * _gauss(st))
        ln = _line(zs, vs)
        inv = 1.0 / ln[1]
        if w == 2 or w == 3:
            m = n if n < 8192 else 8192
            sf = _pro_surface({"rq": p["rq"], "seed": p["seed"]})
            xs, hs = [], []
            for k in range(m):
                x = 4000.0 * k / (m - 1)
                z = 0.002 * x + (p["h"] if (w == 3 and x > 2000.0) else 0.0)
                for j in range(len(PRO_W)):
                    z += sf[0][j] * math.sin(2.0 * PI * x / (PRO_W[j] * 1.5) + sf[1][j])
                xs.append(x)
                hs.append(0.01 * _i(z / 0.01))
            A = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
            b = [0.0, 0.0, 0.0]
            for k in range(m):
                s = 1.0 if (w == 3 and xs[k] > 2000.0) else 0.0
                v = [1.0, s, xs[k]]
                for r in range(3):
                    for c in range(3):
                        A[r][c] += v[r] * v[c]
                    b[r] += v[r] * hs[k]
            if w == 2:
                A[1][1] = 1.0
            c = _solve3(A, b)
            q = 0.0
            for k in range(m):
                s = 1.0 if (w == 3 and xs[k] > 2000.0) else 0.0
                r = hs[k] - c[0] - c[1] * s - c[2] * xs[k]
                q += r * r
            rq = math.sqrt(q / m)
            val = rq if w == 2 else c[1]
            lev = [hs[k] - c[0] - c[2] * xs[k] for k in range(m)]
            return _base(val, _afm_exact(p), m, _thin(xs, 400), _thin(lev, 400), [], [], inv=inv, Rq=rq, step=c[1])
        if w == 1:
            # retract curve: contact line down to the pull-off at -Fad / k, then free (0); sampled at m points
            m = n if n < 8192 else 8192
            zp = 20.0 - p["Fad"] * 1.0e-9 / p["k"] * 1.0e9      # piezo position (nm) of the pull-off
            rz, rv = [], []
            vmin = 0.0
            for k in range(m):
                z = 60.0 - 60.0 * k / (m - 1)
                v = (z - 20.0) / p["inv"] if z >= zp else 0.0
                rz.append(z)
                rv.append(v)
                if v < vmin:
                    vmin = v
            F = p["k"] * inv * 1.0e-9 * (-vmin) * 1.0e9          # nN, k from the cantilever's thermal tune
            return _base(F, _afm_exact(p), m, _thin(rz, 400), _thin(rv, 400), [], [], inv=inv, kfit=p["k"], Fad=F)
        # ---- thermal tune: the spring constant
        sdz = math.sqrt(KB * p["T"] / p["k"]) * 1.0e9            # nm
        mth = n
        s2 = 0.0
        for k in range(mth):
            v = sdz / p["inv"] * _gauss(st)
            s2 += v * v
        kfit = KB * p["T"] / ((s2 / mth) * (inv * 1.0e-9) ** 2)
        return _base(kfit, _afm_exact(p), mth, _thin(zs, 400), _thin(vs, 400), [], [], inv=inv, kfit=kfit)


# ============================================================================================ TEM / SAED
def _saed_lambda(V: float) -> float:
    """Relativistic electron wavelength (nm) at accelerating voltage V (volts)."""
    return 1.0e9 * H / math.sqrt(2.0 * ME * QE * V * (1.0 + QE * V / (2.0 * ME * C_LIGHT * C_LIGHT)))


SAED_N = [3.0, 4.0, 8.0, 11.0, 12.0, 16.0]     # fcc rings: 111, 200, 220, 311, 222, 400


def _saed_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 0:
        return _saed_lambda(p["V"]) * p["L"]
    if w == 1:
        return p["aS"] / math.sqrt(SAED_N[max(0, min(5, _i(p["k"]) - 1))])
    if w == 2:
        return p["aF"] * math.sqrt(3.0) / 2.0
    st = _lcg(p["seed"])
    s = 0.0
    m = _i(p["Ng"])
    for _ in range(m):
        s += p["D0"] * math.exp(p["sg"] * _gauss(st))
    return s / m


class PxSaed(_Base):
    """SIMULATED TEM data, every length read to the nearest detector / image pixel (n pixels across). The camera
    constant lambda L (nm mm) comes from the ring radii of a gold standard (fcc, aG): lambda L = R d averaged over four
    rings. what = 0 that camera constant; what = 1 the d-spacing of ring k of a polycrystalline fcc film (lattice aS)
    = (lambda L from gold) / R; what = 2 the 100 d-spacing of a hexagonal single-crystal flake (lattice aF) from the
    six first-order spots of its [001] pattern; what = 3 the mean particle size of a gold nanoparticle sample from a
    bright-field image (Ng particles, log-normal, field 20 D0)."""
    PARAMS = {"what": 0.0, "k": 1.0, "V": 200.0e3, "L": 800.0, "aG": 0.40782, "aS": 0.40495, "aF": 0.3160,
              "W": 60.0, "D0": 12.0, "sg": 0.25, "Ng": 200.0, "n": 2048.0, "seed": 41.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(64, _i(p["n"]))
        w = _i(p["what"])
        lam = _saed_lambda(p["V"])
        pix = p["W"] / n
        lamL = lam * p["L"]
        if w == 3:
            st = _lcg(p["seed"])
            ipix = 20.0 * p["D0"] / n
            m = _i(p["Ng"])
            s = 0.0
            ds = []
            for _ in range(m):
                d = p["D0"] * math.exp(p["sg"] * _gauss(st))
                dm = ipix * _i(d / ipix)
                ds.append(dm)
                s += dm
            hx, hy = [], []
            for b in range(16):
                lo = 3.0 * p["D0"] * b / 16.0
                hi = 3.0 * p["D0"] * (b + 1) / 16.0
                c = 0
                for d in ds:
                    if lo <= d < hi:
                        c += 1
                hx.append(0.5 * (lo + hi))
                hy.append(float(c))
            return _base(s / m, _saed_exact(p), m, hx, hy, [], [], pix=ipix, lam=lam)
        Rg = []
        cal = 0.0
        for j in range(4):
            d = p["aG"] / math.sqrt(SAED_N[j])
            R = pix * _i((lamL / d) / pix)
            Rg.append(R)
            cal += R * d
        cal /= 4.0
        val = cal
        px = [1.0, 2.0, 3.0, 4.0]
        py = list(Rg)
        if w == 1:
            ds = []
            py = []
            for j in range(6):
                d = p["aS"] / math.sqrt(SAED_N[j])
                R = pix * _i((lamL / d) / pix)
                py.append(R)
                ds.append(cal / R)
            px = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
            val = ds[max(0, min(5, _i(p["k"]) - 1))]
        elif w == 2:
            d = p["aF"] * math.sqrt(3.0) / 2.0
            s = 0.0
            px, py = [], []
            for j in range(6):
                ang = PI / 3.0 * j + 0.31
                gx = pix * _i((lamL / d) * math.cos(ang) / pix)
                gy = pix * _i((lamL / d) * math.sin(ang) / pix)
                px.append(gx)
                py.append(gy)
                s += math.sqrt(gx * gx + gy * gy)
            val = cal / (s / 6.0)
        return _base(val, _saed_exact(p), n, [], [], px, py, cal=cal, lam=lam, pix=pix)


# ============================================================================================ STM
def _stm_ldos(p: dict, E: float) -> float:
    """LDOS (arb.) of the Au(111) surface: a flat bulk part plus the 2D Shockley surface-state band that switches on at
    E0 (a step, smeared by w)."""
    return 1.0 + 0.6 * 0.5 * (1.0 + math.tanh((E - p["E0"]) / p["wE"]))


def _lncosh(x: float) -> float:
    a = abs(x)
    return a + math.log1p(math.exp(-2.0 * a)) - math.log(2.0)


def _stm_I(p: dict, V: float) -> float:
    """Tunnel current (arb.) at bias V: the integral of the LDOS from 0 to V, done exactly
    (the integral of tanh((E - E0) / w) is w ln cosh((E - E0) / w))."""
    return V + 0.3 * (V + p["wE"] * (_lncosh((V - p["E0"]) / p["wE"]) - _lncosh(-p["E0"] / p["wE"])))


def _stm_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["phi"]
    if w == 2:
        return p["E0"]
    return p["a"]


class PxStm(_Base):
    """SIMULATED STM data. what = 0 lattice spacing a (nm): a constant-current line profile along a close-packed row,
    z = A cos(2 pi x / a) + noise, n points over 6 nm; the atom maxima (parabola through three points) are fitted
    against their number - the slope is a. what = 1 apparent barrier height (eV): I(z) = I0 exp(-2 kappa z) recorded
    at n tip heights over 0.3 nm (2 % noise), kappa from the slope of ln I, phi = hbar^2 kappa^2 / (2 me). what = 2 the
    onset of the surface state (eV): I(V) recorded at n bias points (-1 ... +1 V, 0.2 % noise), dI/dV as the slope of a
    least-squares line over +-40 mV, the onset where dI/dV crosses half way up its step."""
    PARAMS = {"what": 0.0, "a": 0.288, "phi": 4.5, "E0": -0.487, "wE": 0.03, "n": 1200.0, "seed": 43.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(20, _i(p["n"]))
        w = _i(p["what"])
        st = _lcg(p["seed"])
        if w == 1:
            xs, ys = [], []
            kap = math.sqrt(2.0 * ME * p["phi"] * QE) / HBAR * 1.0e-9    # 1/nm
            for k in range(n):
                z = 0.3 * k / (n - 1)
                I = math.exp(-2.0 * kap * z) * (1.0 + 0.02 * (2.0 * _u(st) - 1.0))
                xs.append(z)
                ys.append(math.log(I))
            ln = _line(xs, ys)
            kf = -ln[1] / 2.0 * 1.0e9
            phi = HBAR * HBAR * kf * kf / (2.0 * ME) / QE
            cx = [0.0, 0.3]
            cy = [ln[0], ln[0] + ln[1] * 0.3]
            return _base(phi, _stm_exact(p), n, cx, cy, _thin(xs, 200), _thin(ys, 200), kappa=kf)
        if w == 2:
            vs, Is = [], []
            for k in range(n):
                V = -1.0 + 2.0 * k / (n - 1)
                vs.append(V)
                Is.append(_stm_I(p, V) * (1.0 + 0.002 * (2.0 * _u(st) - 1.0)))
            g = []
            for k in range(n):
                X, Y = [], []
                for j in range(n):
                    if abs(vs[j] - vs[k]) <= 0.04:
                        X.append(vs[j])
                        Y.append(Is[j])
                g.append(_line(X, Y)[1])
            gl = 0.0
            cl = 0
            gh = 0.0
            ch = 0
            for k in range(1, n - 1):
                if vs[k] < -0.85:
                    gl += g[k]
                    cl += 1
                if -0.3 < vs[k] < -0.1:
                    gh += g[k]
                    ch += 1
            gl = gl / cl if cl else 1.0
            gh = gh / ch if ch else 1.0
            half = 0.5 * (gl + gh)
            E0 = vs[0]
            for k in range(1, n - 1):
                if g[k] < half <= g[k + 1]:
                    E0 = vs[k] + (vs[k + 1] - vs[k]) * (half - g[k]) / (g[k + 1] - g[k])
                    break
            return _base(E0, _stm_exact(p), n, _thin(vs, 400), _thin(g, 400), [], [], onset=E0)
        xs, zs = [], []
        for k in range(n):
            x = 6.0 * k / (n - 1)
            xs.append(x)
            zs.append(0.02 * math.cos(2.0 * PI * x / p["a"]) + 0.0015 * _gauss(st))
        m = max(1, _i(0.15 * p["a"] / (xs[1] - xs[0])))
        win = max(1, _i(0.4 * p["a"] / (xs[1] - xs[0])))
        peaks = []
        for k in range(m, n - m):
            if zs[k] < 0.01:
                continue
            ok = True
            for j in range(max(0, k - win), min(n - 1, k + win) + 1):
                if (j < k and zs[j] >= zs[k]) or (j > k and zs[j] > zs[k]):
                    ok = False
                    break
            if ok:
                peaks.append(_peak(xs, zs, k, m, False)[0])
        idx = [float(j) for j in range(len(peaks))]
        ln = _line(idx, peaks)
        return _base(ln[1], _stm_exact(p), len(peaks), _thin(xs, 600), _thin(zs, 600), [], [], npk=float(len(peaks)))


# ============================================================================================ PLD + RHEED
def _pld_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        return p["mos"] * 3600.0
    return p["c"] / p["npm"]


class PxPld(_Base):
    """SIMULATED pulsed-laser deposition run. what = 0 growth rate per pulse from RHEED: the specular-spot intensity in
    layer-by-layer growth oscillates once per monolayer, I = b + a exp(-theta / 12) cos(2 pi theta) + noise, theta = the
    coverage in unit cells = f t / npm (npm pulses per unit cell, the hidden value; f the repetition rate), sampled n
    times a second. The analysis finds the oscillation maxima (a rough period from upward crossings of the mean, with
    a +-0.05 hysteresis, sets the search window; parabola through three points), fits their times against their number (the period T) and gives
    c / (T f) nm per pulse. what = 1 crystallinity: the film's mosaic spread from its rocking curve (the px10_rock
    analysis on the substrate's 002 reflection, 192 n omega steps)."""
    PARAMS = {"what": 0.0, "c": 1.168, "npm": 28.0, "f": 2.0, "Np": 600.0, "n": 10.0, "noise": 0.02, "seed": 47.0,
              "d": 0.19525, "dw": -0.25, "wf": 0.02, "mos": 0.08, "ws": 0.006}

    @staticmethod
    def init(p, cfg=None):
        if _i(p["what"]) == 1:
            q = dict(PxRock.PARAMS)
            q["what"] = 1.0
            q["d"] = p["d"]
            q["dw"] = p["dw"]
            q["wf"] = p["wf"]
            q["mos"] = p["mos"]
            q["ws"] = p["ws"]
            q["n"] = p["n"] * 192.0
            q["seed"] = p["seed"]
            s = PxRock.init(q)
            s["exact"] = _pld_exact(p)
            s["err"] = _err(s["val"], s["exact"])
            return s
        st = _lcg(p["seed"])
        T = p["Np"] / p["f"]
        m = max(20, _i(T * p["n"]))
        ts, ys = [], []
        for k in range(m):
            t = T * k / (m - 1)
            th = p["f"] * t / p["npm"]
            ts.append(t)
            ys.append(0.3 + 0.6 * math.exp(-th / 12.0) * math.cos(2.0 * PI * th) + p["noise"] * _gauss(st))
        mean = 0.0
        for y in ys:
            mean += y
        mean /= m
        cr = 0
        low = False
        for k in range(m):
            if ys[k] < mean - 0.05:
                low = True
            elif low and ys[k] > mean + 0.05:
                cr += 1
                low = False
        Pest = T / cr if cr > 0 else T
        win = max(1, _i(0.3 * Pest / (ts[1] - ts[0])))
        mx = []
        for k in range(1, m - 1):
            if ys[k] < mean:
                continue
            ok = True
            for j in range(max(0, k - win), min(m - 1, k + win) + 1):
                if (j < k and ys[j] >= ys[k]) or (j > k and ys[j] > ys[k]):
                    ok = False
                    break
            if ok:
                mx.append(_peak(ts, ys, k, max(1, win // 3), False)[0])
        idx = [float(j) for j in range(len(mx))]
        ln = _line(idx, mx)
        per = ln[1]
        rate = p["c"] / (per * p["f"]) if per > 0 else 0.0
        return _base(rate, _pld_exact(p), len(mx), _thin(ts, 600), _thin(ys, 600), [], [], period=per,
                     ppu=per * p["f"], nmax=float(len(mx)))


KERNELS: dict[str, Any] = {"px10_moseley": PxMoseley, "px10_ruth": PxRuth, "px10_mwi": PxMwi,
                           "px10_profilo": PxProfilo, "px10_stoney": PxStoney, "px10_spin": PxSpin, "px10_imp": PxImp,
                           "px10_rock": PxRock, "px10_qcm": PxQcm, "px10_afm": PxAfm, "px10_saed": PxSaed,
                           "px10_stm": PxStm, "px10_pld": PxPld}
FAMILY = {k: "comp" for k in KERNELS}

TEXTBOOK = {"px10_moseley_v": _mos_exact, "px10_ruth_v": _ruth_exact, "px10_mwi_v": lambda p: p["NL"],
            "px10_profilo_v": _pro_exact, "px10_stoney_v": _sto_exact, "px10_spin_v": _spin_exact,
            "px10_imp_v": _imp_exact, "px10_rock_v": _rock_exact, "px10_qcm_v": _qcm_exact,
            "px10_afm_v": _afm_exact, "px10_saed_v": _saed_exact, "px10_stm_v": _stm_exact, "px10_pld_v": _pld_exact}


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


def _finest(rows, p) -> float:
    """The answer of the run on the most data (the largest n): the sample's value is hidden, so the student reports
    the run with the most data, not the one closest to a value nobody is shown."""
    rs = _rows(rows, "n", "val")
    if not rs:
        return 0.0
    b = rs[0]
    for r in rs:
        if r[0] >= b[0]:
            b = r
    return b[1]


CALCS = {
    "px10_finest": {"label": "answer on the most data", "unit": "", "needs": ["n", "val"], "fn": _finest},
}
