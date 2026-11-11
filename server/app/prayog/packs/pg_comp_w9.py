"""Kernel pack: M.Sc. "Computational physics" and "Materials synthesis and characterisation" practicals, wave 9.

ONE workstation rig (`pc9-workstation`) serves every lab of this pack. Two kinds of kernel live here:

COMPUTE kernels (the reference is shown - a computational practical measures the error of a method):
    pc9_xcom   photon mass attenuation coefficient of a compound by the mixture rule, from the NIST elemental
               tables (Hubbell and Seltzer, NISTIR 5632), against NIST's own compound table. The tables below were
               FETCHED from physics.nist.gov/PhysRefData/XrayMassCoef on 11 Nov 2026 (the standard energy grid,
               15 keV - 20 MeV), not written from memory.

ANALYSIS kernels (SIMULATED DATA - the hidden sample value is what the student measures and is never shown):
    pc9_qd     quantum-dot absorption edge -> Tauc fit -> dot radius by the Brus (effective-mass) equation
    pc9_bet    nitrogen isotherm -> BET specific surface area, total pore volume -> Gurvich pore size 4V/S
    pc9_dsc    DSC trace -> glass transition (half height), melting peak, crystallinity from the enthalpies
    pc9_tga    TGA mass curve -> number of steps (DTG peaks), mass loss of a step, DTG peak temperature
    pc9_xrd    powder pattern -> Williamson-Hall size and strain, Scherrer size, cubic lattice parameter
    pc9_tem    TEM bright field -> mean grain size; selected-area diffraction rings -> d-spacings (camera equation)
    pc9_gas    gas-sensor resistance transient -> sensitivity Ra/Rg, response and recovery times (t90)
    pc9_film   sputtered film -> thickness from X-ray reflectivity (Kiessig) fringes; grain size by Scherrer

Every kernel keeps the shape of the other computational packs:
    PARAMS  the problem's numbers, `n` (grid / data points / energy) and `what` (which result is reported)
    init    computes the whole run once; step advances a clock only
    view    val (the answer of the run), exact (the reference or the hidden sample value), err, nused and the
            curves the monitor draws (cx / ce reference, cy what the method built, px / py data points)
    measure {val, exact, err, nused}
Anything random is the seeded Lehmer generator (16807, mod 2^31 - 1), never the clock. The JavaScript twin is
`app/static/prayog/packs/pg_comp_w9.js`, same formulas in the same order. Every name carries the prefix `pc9_`.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
_M = 2147483647
NA = 6.02214076e23            # 1/mol, exact (SI 2019)
QE = 1.602176634e-19          # C, exact (SI 2019)
H = 6.62607015e-34            # J s, exact (SI 2019)
ME = 9.1093837015e-31         # kg, CODATA 2018
EPS0 = 8.8541878128e-12       # F/m, CODATA 2018
VSTP = 22414.0                # cm3/mol, molar volume of an ideal gas at 0 C, 1 atm (rounded)
SIG_N2 = 0.162e-18            # m2, cross-sectional area of an adsorbed N2 molecule (IUPAC 1985 recommendation)
RHO_LN2 = 0.808               # g/cm3, liquid nitrogen at 77 K (from memory - verify)
M_N2 = 28.0134                # g/mol


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


def _base(val: float, exact: float, nused: float, cx: list, ce: list, cy: list, px: list, py: list, **extra) -> dict:
    s = {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(nused),
         "cx": cx, "ce": ce, "cy": cy, "px": px, "py": py}
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


# ============================================================================================ photon attenuation (NIST)
# Fetched 11 Nov 2026 from https://physics.nist.gov/PhysRefData/XrayMassCoef/ (J. H. Hubbell and S. M. Seltzer,
# NISTIR 5632): mu/rho in cm2/g on the standard grid (MeV). Element pages ElemTab/zNN.html, compounds ComTab/*.html,
# compositions (fraction by weight) and densities from tab1.html / tab2.html of the same site.
XC = {
    "E": [0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0],
    "water": [1.673, 0.8096, 0.3756, 0.2683, 0.2269, 0.2059, 0.1837, 0.1707, 0.1505, 0.137, 0.1186, 0.1061, 0.09687, 0.08956, 0.07865, 0.07072, 0.06323, 0.05754, 0.04942, 0.03969, 0.03403, 0.03031, 0.0277, 0.02429, 0.02219, 0.01941, 0.01813],
    "bone": [9.032, 4.001, 1.331, 0.6655, 0.4242, 0.3148, 0.2229, 0.1855, 0.148, 0.1309, 0.1113, 0.09908, 0.09022, 0.08332, 0.07308, 0.06566, 0.05871, 0.05346, 0.04607, 0.03745, 0.03257, 0.02946, 0.02734, 0.02467, 0.02314, 0.02132, 0.02068],
    "tissue": [1.699, 0.823, 0.379, 0.2688, 0.2264, 0.2048, 0.1823, 0.1693, 0.1492, 0.1358, 0.1175, 0.1052, 0.09598, 0.08873, 0.07793, 0.07006, 0.06265, 0.05701, 0.04895, 0.03931, 0.03369, 0.03, 0.02741, 0.02401, 0.02193, 0.01915, 0.01787],
    "a150": [1.394, 0.7068, 0.3481, 0.2562, 0.2198, 0.2008, 0.1803, 0.168, 0.1485, 0.1353, 0.1173, 0.1049, 0.09579, 0.08857, 0.07777, 0.06992, 0.06253, 0.05691, 0.0488, 0.03907, 0.03335, 0.02958, 0.0269, 0.02338, 0.02117, 0.01819, 0.01675],
    "z1": [0.3764, 0.3695, 0.357, 0.3458, 0.3355, 0.326, 0.3091, 0.2944, 0.2651, 0.2429, 0.2112, 0.1893, 0.1729, 0.1599, 0.1405, 0.1263, 0.1129, 0.1027, 0.08769, 0.06921, 0.05806, 0.05049, 0.04498, 0.03746, 0.03254, 0.02539, 0.02153],
    "z6": [0.8071, 0.442, 0.2562, 0.2076, 0.1871, 0.1753, 0.161, 0.1514, 0.1347, 0.1229, 0.1066, 0.09546, 0.08715, 0.08058, 0.07076, 0.06361, 0.0569, 0.05179, 0.04442, 0.03562, 0.03047, 0.02708, 0.02469, 0.02154, 0.01959, 0.01698, 0.01575],
    "z7": [1.236, 0.6178, 0.3066, 0.2288, 0.198, 0.1817, 0.1639, 0.1529, 0.1353, 0.1233, 0.1068, 0.09557, 0.08719, 0.08063, 0.07081, 0.06364, 0.05693, 0.0518, 0.0445, 0.03579, 0.03073, 0.02742, 0.02511, 0.02209, 0.02024, 0.01782, 0.01673],
    "z8": [1.836, 0.8651, 0.3779, 0.2585, 0.2132, 0.1907, 0.1678, 0.1551, 0.1361, 0.1237, 0.107, 0.09566, 0.08729, 0.0807, 0.07087, 0.06372, 0.05697, 0.05185, 0.04459, 0.03597, 0.031, 0.02777, 0.02552, 0.02263, 0.02089, 0.01866, 0.0177],
    "z9": [2.492, 1.133, 0.4487, 0.2828, 0.2214, 0.192, 0.1639, 0.1496, 0.1298, 0.1176, 0.1015, 0.09073, 0.08274, 0.07649, 0.06717, 0.06037, 0.05399, 0.04915, 0.04228, 0.03422, 0.0296, 0.02663, 0.02457, 0.02195, 0.02039, 0.01846, 0.01769],
    "z11": [4.694, 2.057, 0.7197, 0.3969, 0.2804, 0.2268, 0.1796, 0.1585, 0.1335, 0.1199, 0.1029, 0.09185, 0.08372, 0.07736, 0.06788, 0.061, 0.05454, 0.04968, 0.04282, 0.03487, 0.03037, 0.02753, 0.02559, 0.02319, 0.02181, 0.02023, 0.0197],
    "z12": [6.358, 2.763, 0.9306, 0.4881, 0.3292, 0.257, 0.1951, 0.1686, 0.1394, 0.1245, 0.1065, 0.09492, 0.08647, 0.07988, 0.07008, 0.06296, 0.05629, 0.05129, 0.04426, 0.03613, 0.03159, 0.02873, 0.02681, 0.02445, 0.02313, 0.02168, 0.02127],
    "z15": [12.39, 5.352, 1.7, 0.8096, 0.4916, 0.3494, 0.2324, 0.1865, 0.1432, 0.125, 0.1055, 0.09359, 0.08511, 0.07854, 0.06884, 0.06182, 0.05526, 0.05039, 0.04358, 0.0359, 0.03172, 0.02915, 0.02747, 0.02552, 0.02452, 0.02364, 0.02363],
    "z16": [15.5, 6.708, 2.113, 0.9872, 0.5849, 0.4053, 0.2585, 0.202, 0.1506, 0.1302, 0.1091, 0.09665, 0.08781, 0.08102, 0.07098, 0.06373, 0.05697, 0.05193, 0.04498, 0.03715, 0.03293, 0.03036, 0.02872, 0.02682, 0.02589, 0.02517, 0.02529],
    "z17": [17.84, 7.739, 2.425, 1.117, 0.6483, 0.4395, 0.2696, 0.205, 0.148, 0.1266, 0.1054, 0.09311, 0.08453, 0.07795, 0.06826, 0.06128, 0.05478, 0.04994, 0.04328, 0.03585, 0.03188, 0.0295, 0.02798, 0.02628, 0.02549, 0.02496, 0.0252],
    "z19": [25.03, 10.93, 3.413, 1.541, 0.8679, 0.5678, 0.3251, 0.2345, 0.1582, 0.1319, 0.108, 0.09495, 0.086, 0.07922, 0.06929, 0.06216, 0.05556, 0.05068, 0.04399, 0.03666, 0.03282, 0.03054, 0.02915, 0.02766, 0.02704, 0.02687, 0.02737],
    "z20": [29.79, 13.06, 4.08, 1.83, 1.019, 0.6578, 0.3656, 0.2571, 0.1674, 0.1376, 0.1116, 0.09783, 0.08851, 0.08148, 0.07122, 0.06388, 0.05709, 0.05207, 0.04524, 0.0378, 0.03395, 0.0317, 0.03035, 0.02892, 0.02839, 0.02838, 0.02903],
    "z26": [57.08, 25.68, 8.176, 3.629, 1.958, 1.205, 0.5952, 0.3717, 0.1964, 0.146, 0.1099, 0.094, 0.08414, 0.07704, 0.06699, 0.05995, 0.0535, 0.04883, 0.04265, 0.03621, 0.03312, 0.03146, 0.03057, 0.02991, 0.02994, 0.03092, 0.03224],
    "z30": [81.17, 37.19, 12.07, 5.384, 2.892, 1.76, 0.8364, 0.4973, 0.2341, 0.1617, 0.1141, 0.09539, 0.0845, 0.07695, 0.06656, 0.05941, 0.05296, 0.04834, 0.04235, 0.03634, 0.0336, 0.03225, 0.0316, 0.03138, 0.03175, 0.03335, 0.03509],
    "z82": [111.6, 86.36, 30.32, 14.36, 8.041, 5.021, 2.419, 5.549, 2.014, 0.9985, 0.4031, 0.2323, 0.1614, 0.1248, 0.0887, 0.07102, 0.05876, 0.05222, 0.04606, 0.04234, 0.04197, 0.04272, 0.04391, 0.04675, 0.04972, 0.05658, 0.06206],
}
XC_COMP = [
    [[1, 0.111898], [8, 0.888102]],                                                    # water, liquid
    [[1, 0.034], [6, 0.155], [7, 0.042], [8, 0.435], [11, 0.001], [12, 0.002], [15, 0.103], [16, 0.003],
     [20, 0.225]],                                                                     # bone, cortical (ICRU-44)
    [[1, 0.102], [6, 0.143], [7, 0.034], [8, 0.708], [11, 0.002], [15, 0.003], [16, 0.003], [17, 0.002],
     [19, 0.003]],                                                                     # tissue, soft (ICRU-44)
    [[1, 0.10133], [6, 0.775498], [7, 0.035057], [8, 0.052315], [9, 0.017423], [20, 0.018377]],  # A-150 plastic
    [[82, 1.0]],                                                                       # lead
]
XC_NAME = ["water", "bone", "tissue", "a150", "z82"]
XC_RHO = [1.0, 1.92, 1.06, 1.127, 11.35]          # g/cm3, NIST tab1 / tab2


def _xc_interp(tab: list[float], ekev: float) -> float:
    """log-log interpolation in a NIST table (the way XCOM and the NIST tables are meant to be read)."""
    G = XC["E"]
    e = ekev / 1000.0
    if e <= G[0]:
        return tab[0]
    if e >= G[len(G) - 1]:
        return tab[len(G) - 1]
    i = 0
    while i < len(G) - 2 and G[i + 1] < e:
        i += 1
    f = (math.log(e) - math.log(G[i])) / (math.log(G[i + 1]) - math.log(G[i]))
    return math.exp(math.log(tab[i]) + (math.log(tab[i + 1]) - math.log(tab[i])) * f)


def _xc_mix(mat: int, ekev: float) -> float:
    s = 0.0
    for zw in XC_COMP[mat]:
        s += zw[1] * _xc_interp(XC["z" + str(zw[0])], ekev)
    return s


def _xc_mat(p: dict) -> int:
    return max(0, min(4, _i(p["mat"])))


def _xc_exact(p: dict) -> float:
    return _xc_interp(XC[XC_NAME[_xc_mat(p)]], p["n"])


class PcXcom(_Base):
    """mu/rho of a material at photon energy n (keV): the mixture rule sum w_i (mu/rho)_i over the elemental tables,
    against NIST's tabulated compound. A lead absorber is a single element, so its mixture is the table itself."""
    PARAMS = {"mat": 0.0, "n": 662.0, "method": 0.0, "what": 0.0}

    @staticmethod
    def init(p, cfg=None):
        mat = _xc_mat(p)
        ek = p["n"]
        val = _xc_mix(mat, ek)
        ex = _xc_exact(p)
        cx, ce, cy = [], [], []
        for e in XC["E"]:
            cx.append(e * 1000.0)
            ce.append(math.log10(_xc_interp(XC[XC_NAME[mat]], e * 1000.0)))
            cy.append(math.log10(_xc_mix(mat, e * 1000.0)))
        mu = val * XC_RHO[mat]
        return _base(val, ex, len(XC_COMP[mat]), cx, ce, cy, [ek], [math.log10(val)],
                     mu=mu, hvl=math.log(2.0) / mu, rho=XC_RHO[mat])


# ============================================================================================ quantum dots (Brus)
def _qd_ab(p: dict) -> list[float]:
    """Brus (1984) effective-mass terms in eV: a / R^2 confinement and b / R Coulomb (1.786 e^2 / 4 pi eps0 eps R)."""
    a = H * H / (8.0 * ME) * (1.0 / p["me"] + 1.0 / p["mh"]) / QE
    b = 1.786 * QE / (4.0 * PI * EPS0 * p["eps"])
    return [a, b]


def _qd_E1(p: dict) -> float:
    ab = _qd_ab(p)
    R = p["R"] * 1e-9
    return p["Eg"] + ab[0] / (R * R) - ab[1] / R


def _qd_radius(p: dict, E1: float) -> float:
    """Invert the Brus equation for R (nm): a u^2 - b u - (E1 - Eg) = 0 with u = 1/R."""
    ab = _qd_ab(p)
    disc = ab[1] * ab[1] + 4.0 * ab[0] * (E1 - p["Eg"])
    if disc < 0:
        return 0.0
    u = (ab[1] + math.sqrt(disc)) / (2.0 * ab[0])
    return 1e9 / u


def _qd_exact(p: dict) -> float:
    w = _i(p["what"])
    E1 = _qd_E1(p)
    if w == 1:
        return E1 - p["Eg"]
    if w == 2:
        return E1
    return p["R"]


class PcQd(_Base):
    """SIMULATED absorption spectrum of a direct-gap quantum-dot sample (Tauc form alpha ~ sqrt(E - E1) / E above the
    first transition E1, with the dot radius R set by the Brus equation), plus seeded 'detector' noise. The analysis is
    the student's: a Tauc plot (alpha E)^2 against E, a straight line through its middle part, the intercept E1, then
    the Brus equation inverted for R. what = 0 radius (nm), 1 blue shift E1 - Eg (eV), 2 optical gap E1 (eV)."""
    PARAMS = {"Eg": 2.42, "me": 0.19, "mh": 0.8, "eps": 8.9, "R": 2.0, "what": 0.0, "n": 160.0, "method": 0.0,
              "noise": 0.003, "seed": 11.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(8, _i(p["n"]))
        E1 = _qd_E1(p)
        lo = p["Eg"] - 0.15
        hi = max(p["Eg"] + 1.2, E1 + 0.9)
        st = _lcg(p["seed"])
        Es, ys = [], []
        for k in range(n):
            E = lo + (hi - lo) * k / (n - 1)
            d = E - E1
            al = math.sqrt(d) / E if d > 0 else 0.0
            al = al * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0))
            Es.append(E)
            ys.append((al * E) * (al * E))
        ymax = 0.0
        for y in ys:
            if y > ymax:
                ymax = y
        fx, fy = [], []
        for k in range(n):
            if 0.15 * ymax <= ys[k] <= 0.65 * ymax:
                fx.append(Es[k])
                fy.append(ys[k])
        ln = _line(fx, fy)
        E0 = -ln[0] / ln[1] if ln[1] != 0 else 0.0
        w = _i(p["what"])
        if w == 1:
            val = E0 - p["Eg"]
        elif w == 2:
            val = E0
        else:
            val = _qd_radius(p, E0)
        cx = [E0, hi]
        cy = [0.0, ln[0] + ln[1] * hi]
        return _base(val, _qd_exact(p), len(fx), cx, [], cy, _thin(Es, 160), _thin(ys, 160), E0=E0, Eg=p["Eg"],
                     shift=E0 - p["Eg"], Rfit=_qd_radius(p, E0))


# ============================================================================================ BET surface area
def _bet_vm(p: dict) -> float:
    """Monolayer capacity (cm3 STP per gram) that gives the sample's specific surface area S (m2/g)."""
    return p["S"] * VSTP / (NA * SIG_N2)


def _bet_vplat(p: dict) -> float:
    """Gas volume (cm3 STP / g) that fills the pores: Vp = d S / 4 (Gurvich) as liquid N2, turned into gas."""
    Vp = p["d"] * p["S"] * 1e-3 / 4.0
    return Vp * VSTP * RHO_LN2 / M_N2


def _bet_v(p: dict, x: float) -> float:
    vm = _bet_vm(p)
    C = p["C"]
    if x <= 0.35:
        return vm * C * x / ((1.0 - x) * (1.0 - x + C * x))
    v35 = vm * C * 0.35 / (0.65 * (0.65 + C * 0.35))
    vp = _bet_vplat(p)
    return v35 + (vp - v35) * (1.0 - math.exp(-(x - 0.35) / 0.08))


def _bet_exact(p: dict) -> float:
    return p["d"] if _i(p["what"]) == 1 else p["S"]


class PcBet(_Base):
    """SIMULATED nitrogen adsorption isotherm at 77 K of a mesoporous powder (BET form up to p/p0 = 0.35, then pore
    filling to a plateau), with seeded noise. The analysis: the BET plot x / (v (1 - x)) against x over 0.05 - 0.30
    gives the monolayer volume vm = 1 / (slope + intercept) and C = 1 + slope / intercept; S = vm NA sigma / 22414;
    the volume at the highest p/p0 is the total pore volume Vp; the Gurvich pore size is 4 Vp / S.
    what = 0 specific surface area (m2/g), 1 mean pore diameter (nm)."""
    PARAMS = {"S": 250.0, "C": 100.0, "d": 6.0, "what": 0.0, "n": 48.0, "method": 0.0, "noise": 0.003, "seed": 7.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(8, _i(p["n"]))
        st = _lcg(p["seed"])
        xs, vs = [], []
        for k in range(n):
            x = 0.02 + 0.97 * k / (n - 1)
            v = _bet_v(p, x) * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0))
            xs.append(x)
            vs.append(v)
        fx, fy = [], []
        for k in range(n):
            if 0.05 <= xs[k] <= 0.30:
                fx.append(xs[k])
                fy.append(xs[k] / (vs[k] * (1.0 - xs[k])))
        ln = _line(fx, fy)
        vm = 1.0 / (ln[0] + ln[1]) if (ln[0] + ln[1]) != 0 else 0.0
        C = 1.0 + ln[1] / ln[0] if ln[0] != 0 else 0.0
        S = vm * NA * SIG_N2 / VSTP
        Vp = vs[n - 1] * M_N2 / (VSTP * RHO_LN2)
        d = 4.0 * Vp / S * 1e3 if S > 0 else 0.0
        val = d if _i(p["what"]) == 1 else S
        cx, cy = [], []
        for k in range(31):
            x = 0.02 + 0.33 * k / 30
            cx.append(x)
            cy.append(vm * C * x / ((1.0 - x) * (1.0 - x + C * x)))
        return _base(val, _bet_exact(p), len(fx), cx, [], cy, xs, vs, vm=vm, C=C, S=S, Vp=Vp, d=d)


# ============================================================================================ DSC of a polymer
def _dsc_c(p: dict, T: float) -> float:
    """Apparent specific heat (J/g K) the DSC sees: baseline, the glass-transition step, the melting endotherm and
    (for a quenched polymer such as PET) the cold-crystallisation exotherm, each peak a Gaussian of area dH (J/g)."""
    c = p["cp0"] + p["slope"] * (T - p["T0"]) + p["dcp"] / (1.0 + math.exp(-(T - p["Tg"]) / p["wg"]))
    c += p["dHm"] * math.exp(-0.5 * ((T - p["Tm"]) / p["wm"]) ** 2) / (p["wm"] * math.sqrt(2.0 * PI))
    if p["dHcc"] > 0:
        c -= p["dHcc"] * math.exp(-0.5 * ((T - p["Tcc"]) / p["wcc"]) ** 2) / (p["wcc"] * math.sqrt(2.0 * PI))
    return c


def _dsc_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["Tm"]
    if w == 2:
        return (p["dHm"] - p["dHcc"]) / p["H100"]
    return p["Tg"]


def _dsc_area(Ts: list[float], cs: list[float], lo: float, hi: float) -> float:
    """Peak area above the straight baseline joining the trace at lo and hi (trapezoid rule)."""
    idx = [k for k in range(len(Ts)) if lo <= Ts[k] <= hi]
    if len(idx) < 3:
        return 0.0
    a, b = idx[0], idx[len(idx) - 1]
    s = 0.0
    for j in range(len(idx) - 1):
        k = idx[j]
        b0 = cs[a] + (cs[b] - cs[a]) * (Ts[k] - Ts[a]) / (Ts[b] - Ts[a])
        b1 = cs[a] + (cs[b] - cs[a]) * (Ts[k + 1] - Ts[a]) / (Ts[b] - Ts[a])
        s += 0.5 * ((cs[k] - b0) + (cs[k + 1] - b1)) * (Ts[k + 1] - Ts[k])
    return s


class PcDsc(_Base):
    """SIMULATED DSC heating trace of a polymer at beta K/min (heat flow in W/g, with seeded noise). The analysis: the
    glass transition at half height between the extrapolated baselines (ASTM E1356 midpoint), the melting point at the
    endotherm's maximum (parabola through the top three points), the crystallinity Xc = (dHm - dHcc) / dH100 from the
    peak areas. The analysis windows gl..gh, ml..mh, cl..ch are the ones read off the trace by eye.
    what = 0 Tg (C), 1 Tm (C), 2 crystallinity (fraction)."""
    PARAMS = {"Tg": 78.0, "dcp": 0.3, "wg": 2.0, "Tm": 255.0, "dHm": 50.0, "wm": 4.0, "Tcc": 135.0, "dHcc": 25.0,
              "wcc": 4.0, "H100": 140.0, "cp0": 1.2, "slope": 0.002, "T0": 25.0, "T1": 300.0, "beta": 10.0,
              "gl": 50.0, "gh": 105.0, "ml": 225.0, "mh": 285.0, "cl": 110.0, "ch": 160.0,
              "what": 0.0, "n": 400.0, "method": 0.0, "noise": 0.001, "seed": 5.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(40, _i(p["n"]))
        st = _lcg(p["seed"])
        f = p["beta"] / 60.0
        Ts, hf, cs = [], [], []
        for k in range(n):
            T = p["T0"] + (p["T1"] - p["T0"]) * k / (n - 1)
            q = f * _dsc_c(p, T) * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0))
            Ts.append(T)
            hf.append(q)
            cs.append(q / f)
        w = _i(p["what"])
        bx1, by1, bx2, by2 = [], [], [], []
        for k in range(n):
            if p["gl"] <= Ts[k] <= p["gl"] + 12.0:
                bx1.append(Ts[k])
                by1.append(cs[k])
            if p["gh"] - 12.0 <= Ts[k] <= p["gh"]:
                bx2.append(Ts[k])
                by2.append(cs[k])
        l1 = _line(bx1, by1)
        l2 = _line(bx2, by2)
        Tg = 0.0
        for k in range(n - 1):
            if Ts[k] < p["gl"] or Ts[k + 1] > p["gh"]:
                continue
            m0 = 0.5 * (l1[0] + l1[1] * Ts[k] + l2[0] + l2[1] * Ts[k])
            m1 = 0.5 * (l1[0] + l1[1] * Ts[k + 1] + l2[0] + l2[1] * Ts[k + 1])
            d0 = cs[k] - m0
            d1 = cs[k + 1] - m1
            if d0 < 0 <= d1:
                Tg = Ts[k] + (Ts[k + 1] - Ts[k]) * (-d0) / (d1 - d0)
                break
        kb = -1
        for k in range(1, n - 1):
            if p["ml"] <= Ts[k] <= p["mh"] and (kb < 0 or cs[k] > cs[kb]):
                kb = k
        Tm = 0.0
        if kb > 0:
            y0, y1, y2 = cs[kb - 1], cs[kb], cs[kb + 1]
            den = y0 - 2.0 * y1 + y2
            Tm = Ts[kb] + (0.5 * (y0 - y2) / den if den != 0 else 0.0) * (Ts[kb + 1] - Ts[kb])
        dHm = _dsc_area(Ts, cs, p["ml"], p["mh"])
        dHcc = -_dsc_area(Ts, cs, p["cl"], p["ch"]) if p["dHcc"] > 0 else 0.0
        Xc = (dHm - dHcc) / p["H100"]
        val = Tm if w == 1 else Xc if w == 2 else Tg
        return _base(val, _dsc_exact(p), n, _thin(Ts, 200), [], _thin(hf, 200), [], [], Tg=Tg, Tm=Tm, dHm=dHm,
                     dHcc=dHcc, Xc=Xc)


# ============================================================================================ TGA
def _tga_steps(p: dict) -> list[list[float]]:
    out = []
    for j in (1, 2, 3):
        if p["D" + str(j)] > 0:
            out.append([p["T" + str(j)], p["D" + str(j)], p["w" + str(j)]])
    return out


def _tga_m(p: dict, T: float) -> float:
    m = 100.0
    for s in _tga_steps(p):
        m -= s[1] / (1.0 + math.exp(-(T - s[0]) / s[2]))
    return m


def _tga_exact(p: dict) -> float:
    w = _i(p["what"])
    ss = _tga_steps(p)
    if w == 2:
        return float(len(ss))
    k = max(1, min(len(ss), _i(p["k"]))) - 1
    return ss[k][0] if w == 1 else ss[k][1]


class PcTga(_Base):
    """SIMULATED thermogravimetric curve (mass % against T at a constant heating rate, seeded balance noise): each
    decomposition step is a sigmoid of mass D_k centred on T_k. The analysis: the DTG curve -dm/dT by central
    differences, its peaks counted (a peak = a step), each peak temperature from a parabola through the top three DTG
    points, and each step's mass loss as the drop between the plateaux half-way between neighbouring DTG peaks.
    what = 0 mass loss of step k (%), 1 DTG peak temperature of step k (C), 2 the number of steps."""
    PARAMS = {"T1": 95.0, "D1": 14.43, "w1": 2.5, "T2": 125.0, "D2": 14.43, "w2": 2.5, "T3": 255.0, "D3": 7.215,
              "w3": 4.0, "T0": 30.0, "Tend": 350.0, "k": 1.0, "what": 0.0, "n": 640.0, "method": 0.0,
              "noise": 0.00002, "seed": 3.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(40, _i(p["n"]))
        st = _lcg(p["seed"])
        Ts, ms = [], []
        for k in range(n):
            T = p["T0"] + (p["Tend"] - p["T0"]) * k / (n - 1)
            Ts.append(T)
            ms.append(_tga_m(p, T) * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0)))
        dt = [0.0] * n
        for k in range(1, n - 1):
            dt[k] = -(ms[k + 1] - ms[k - 1]) / (Ts[k + 1] - Ts[k - 1])
        top = 0.0
        for v in dt:
            if v > top:
                top = v
        peaks = []
        for k in range(3, n - 3):
            if dt[k] < 0.05 * top:
                continue
            ok = True
            for j in range(k - 3, k + 4):
                if (j < k and dt[j] >= dt[k]) or (j > k and dt[j] > dt[k]):
                    ok = False
            if ok:
                y0, y1, y2 = dt[k - 1], dt[k], dt[k + 1]
                den = y0 - 2.0 * y1 + y2
                peaks.append(Ts[k] + (0.5 * (y0 - y2) / den if den != 0 else 0.0) * (Ts[k + 1] - Ts[k]))
        np_ = len(peaks)

        def m_at(T: float) -> float:
            for k in range(n - 1):
                if Ts[k] <= T <= Ts[k + 1]:
                    return ms[k] + (ms[k + 1] - ms[k]) * (T - Ts[k]) / (Ts[k + 1] - Ts[k])
            return ms[0] if T < Ts[0] else ms[n - 1]
        w = _i(p["what"])
        k = max(1, min(max(np_, 1), _i(p["k"]))) - 1
        loss, tpk = 0.0, 0.0
        if np_ > 0:
            left = p["T0"] if k == 0 else 0.5 * (peaks[k - 1] + peaks[k])
            right = p["Tend"] if k == np_ - 1 else 0.5 * (peaks[k] + peaks[k + 1])
            loss = m_at(left) - m_at(right)
            tpk = peaks[k]
        val = float(np_) if w == 2 else tpk if w == 1 else loss
        return _base(val, _tga_exact(p), np_, _thin(Ts, 200), [], _thin(ms, 200), _thin(Ts, 200), _thin(dt, 200),
                     peaks=peaks, loss=loss, tpk=tpk, nsteps=float(np_))


# ============================================================================================ powder XRD
def _xrd_refl(p: dict) -> list[list[float]]:
    """Allowed reflections in the scan, as [2theta (deg), d (nm), N or 0, multiplicity], sorted by angle and merged
    when two families share one d. lat 0 = fcc (h k l unmixed), 1 = bcc (h + k + l even), 2 = wurtzite (hexagonal:
    00l with l odd and h - k = 3n with l odd are absent)."""
    lat = _i(p["lat"])
    a, c, lam = p["a"], p["c"], p["lam"]
    out = []
    if lat == 2:
        for h in range(0, 4):
            for k in range(0, h + 1):
                for l in range(0, 5):
                    if h == 0 and k == 0 and l == 0:
                        continue
                    if l % 2 == 1 and (h - k) % 3 == 0:
                        continue
                    inv = 4.0 / 3.0 * (h * h + h * k + k * k) / (a * a) + l * l / (c * c)
                    d = 1.0 / math.sqrt(inv)
                    sn = lam / (2.0 * d)
                    if sn >= 1:
                        continue
                    tt = 2.0 * math.asin(sn) * 180.0 / PI
                    mult = (6.0 if h == k or k == 0 else 12.0) * (1.0 if l == 0 else 2.0) if h > 0 else 2.0
                    out.append([tt, d, 0.0, mult])
    else:
        seen = {}
        for h in range(0, 7):
            for k in range(0, h + 1):
                for l in range(0, k + 1):
                    if h == 0:
                        continue
                    N = h * h + k * k + l * l
                    if lat == 0 and not ((h % 2 == k % 2) and (k % 2 == l % 2)):
                        continue
                    if lat == 1 and (h + k + l) % 2 == 1:
                        continue
                    d = a / math.sqrt(N)
                    sn = lam / (2.0 * d)
                    if sn >= 1:
                        continue
                    if N in seen:
                        out[seen[N]][3] += 8.0
                        continue
                    seen[N] = len(out)
                    out.append([2.0 * math.asin(sn) * 180.0 / PI, d, float(N), 8.0])
    res = [r for r in out if p["tt0"] <= r[0] <= p["tt1"]]
    res.sort(key=lambda r: r[0])
    return res


def _xrd_beta(p: dict, tt: float) -> float:
    """FWHM in degrees 2theta: Kλ / (L cos θ) (size) + 4 ε tan θ (strain) + the instrument's own width."""
    th = tt * PI / 360.0
    return (p["K"] * p["lam"] / (p["L"] * math.cos(th)) + 4.0 * p["eps"] * math.tan(th)) * 180.0 / PI + p["bi"]


def _xrd_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["eps"]
    if w == 2:
        return p["a"]
    return p["L"]


class PcXrd(_Base):
    """SIMULATED powder pattern (Cu K-alpha1) of a cubic or wurtzite nanopowder: Gaussian lines at the Bragg angles,
    each of FWHM Kλ/(L cos θ) + 4ε tan θ + the instrument width, intensity = multiplicity x Lorentz-polarisation, on a
    flat background, with seeded counting noise. The analysis: background = the lowest count; each line found as a
    local maximum, its centre and height from a parabola through log(counts) of the top three points, its FWHM from the
    half-height crossings; minus the instrument width; Williamson-Hall β cos θ against 4 sin θ (intercept Kλ/L,
    slope ε); Scherrer on the first line; the cubic lattice parameter from each line's d sqrt(h2 + k2 + l2), indexed
    by the lattice's own sequence. what = 0 size by W-H (nm), 1 strain by W-H, 2 lattice parameter (nm), 3 Scherrer
    size of the first line (nm)."""
    PARAMS = {"lat": 0.0, "a": 0.35238, "c": 0.0, "L": 20.0, "eps": 0.0, "bi": 0.08, "lam": 0.15406, "K": 0.9,
              "tt0": 30.0, "tt1": 100.0, "what": 0.0, "n": 4000.0, "method": 0.0, "noise": 0.002, "seed": 9.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(200, _i(p["n"]))
        refl = _xrd_refl(p)
        st = _lcg(p["seed"])
        I0 = []
        top = 0.0
        for r in refl:
            th = r[0] * PI / 360.0
            lp = (1.0 + math.cos(2.0 * th) ** 2) / (math.sin(th) ** 2 * math.cos(th))
            I0.append(r[3] * lp)
            if r[3] * lp > top:
                top = r[3] * lp
        bg = 0.02 * top
        xs, ys = [], []
        for k in range(n):
            x = p["tt0"] + (p["tt1"] - p["tt0"]) * k / (n - 1)
            y = bg
            for j in range(len(refl)):
                b = _xrd_beta(p, refl[j][0])
                y += I0[j] * math.exp(-4.0 * math.log(2.0) * (x - refl[j][0]) ** 2 / (b * b))
            ys.append(y * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0)))
            xs.append(x)
        lo = ys[0]
        for y in ys:
            if y < lo:
                lo = y
        z = [y - lo for y in ys]
        zmax = 0.0
        for v in z:
            if v > zmax:
                zmax = v
        found = []
        m = max(2, _i(0.15 / ((p["tt1"] - p["tt0"]) / (n - 1))))
        for k in range(m, n - m):
            if z[k] < 0.04 * zmax:
                continue
            ok = True
            for j in range(k - m, k + m + 1):
                if (j < k and z[j] >= z[k]) or (j > k and z[j] > z[k]):
                    ok = False
                    break
            if ok and z[k - m] > 0 and z[k + m] > 0:
                l0, l1, l2 = math.log(z[k - m]), math.log(z[k]), math.log(z[k + m])
                den = l0 - 2.0 * l1 + l2
                dx = 0.5 * (l0 - l2) / den if den != 0 else 0.0
                h = math.exp(l1 - 0.25 * (l0 - l2) * dx)
                cen = xs[k] + dx * (xs[k + m] - xs[k])
                half = 0.5 * h
                i = k
                while i > 0 and z[i] > half:
                    i -= 1
                xl = xs[i] + (xs[i + 1] - xs[i]) * (half - z[i]) / (z[i + 1] - z[i])
                i = k
                while i < n - 1 and z[i] > half:
                    i += 1
                xr = xs[i - 1] + (xs[i] - xs[i - 1]) * (z[i - 1] - half) / (z[i - 1] - z[i])
                found.append([cen, xr - xl])
        X, Y, A = [], [], []
        for j in range(len(found)):
            th = found[j][0] * PI / 360.0
            bb = (found[j][1] - p["bi"]) * PI / 180.0
            X.append(4.0 * math.sin(th))
            Y.append(bb * math.cos(th))
            if j < len(refl) and refl[j][2] > 0:
                A.append(p["lam"] / (2.0 * math.sin(th)) * math.sqrt(refl[j][2]))
        ln = _line(X, Y)
        Lwh = p["K"] * p["lam"] / ln[0] if ln[0] > 0 else 0.0
        Lsch = p["K"] * p["lam"] / Y[0] if len(Y) > 0 and Y[0] > 0 else 0.0
        am = 0.0
        for v in A:
            am += v
        am = am / len(A) if len(A) > 0 else 0.0
        w = _i(p["what"])
        val = ln[1] if w == 1 else am if w == 2 else Lsch if w == 3 else Lwh
        cx = [0.0, X[len(X) - 1] if len(X) else 1.0]
        cy = [ln[0], ln[0] + ln[1] * cx[1]]
        return _base(val, _xrd_exact(p), len(found), _thin(xs, 400), [], _thin(ys, 400), X, Y, wh=[cx, cy],
                     nfound=float(len(found)), nrefl=float(len(refl)), Lwh=Lwh, strain=ln[1], Lsch=Lsch, a_fit=am)


# ============================================================================================ TEM: SAED + grain size
C_LIGHT = 299792458.0         # m/s, exact (SI)


def _tem_lambda(V: float) -> float:
    """Relativistic electron wavelength (m) at accelerating voltage V (volts)."""
    return H / math.sqrt(2.0 * ME * QE * V * (1.0 + QE * V / (2.0 * ME * C_LIGHT * C_LIGHT)))


def _tem_N(lat: int, k: int) -> float:
    seq = [3.0, 4.0, 8.0, 11.0, 12.0, 16.0] if lat == 0 else [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    return seq[max(0, min(len(seq) - 1, k - 1))]


def _tem_grains(p: dict) -> list[float]:
    st = _lcg(p["seed"])
    out = []
    for i in range(_i(p["Ng"])):
        u1 = _u(st)
        u2 = _u(st)
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * PI * u2)
        out.append(p["D0"] * math.exp(p["sg"] * z))
    return out


def _mean_sd(xs: list[float]) -> list[float]:
    s = 0.0
    for x in xs:
        s += x
    m = s / len(xs)
    q = 0.0
    for x in xs:
        q += (x - m) * (x - m)
    return [m, math.sqrt(q / len(xs))]


def _tem_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        return p["a"] / math.sqrt(_tem_N(_i(p["lat"]), _i(p["k"])))
    ms = _mean_sd(_tem_grains(p))
    return ms[1] if _i(p["what"]) == 2 else ms[0]


class PcTem(_Base):
    """SIMULATED TEM of a nanopowder. Bright field: a population of grains (log-normal diameters about D0) imaged with n
    pixels across a field 20 D0 wide, each diameter read to the nearest pixel; the mean of the measured diameters is
    the grain size (the hidden truth is the mean of the true diameters). Selected-area diffraction: rings of radius
    R = λ L / d on a 60 mm detector with n pixels across, each radius read to the nearest pixel; d = λ L / R with λ the
    relativistic electron wavelength. what = 0 mean grain size (nm), 1 d-spacing of ring k (nm), 2 the standard
    deviation of the size distribution (nm). The same image analysis serves an SEM micrograph of particles."""
    PARAMS = {"D0": 12.0, "sg": 0.25, "Ng": 300.0, "V": 200000.0, "Lc": 0.5, "a": 0.40782, "lat": 0.0, "k": 1.0,
              "what": 0.0, "n": 1024.0, "method": 0.0, "seed": 61.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(64, _i(p["n"]))
        w = _i(p["what"])
        lat = _i(p["lat"])
        if w == 1:
            lam = _tem_lambda(p["V"])
            pix = 0.06 / n
            rs, ds, rx = [], [], []
            for k in range(1, 7):
                d = p["a"] / math.sqrt(_tem_N(lat, k)) * 1e-9
                R = lam * p["Lc"] / d
                Rm = _i(R / pix) * pix
                rx.append(float(k))
                rs.append(R * 1e3)
                ds.append(lam * p["Lc"] / Rm * 1e9 if Rm > 0 else 0.0)
            kk = max(1, min(6, _i(p["k"])))
            val = ds[kk - 1]
            return _base(val, _tem_exact(p), n, rx, [], rs, rx, rs, lam=lam, dsp=ds, Lc=p["Lc"])
        gs = _tem_grains(p)
        pix = 20.0 * p["D0"] / n
        meas = []
        for g in gs:
            meas.append(_i(g / pix) * pix)
        ms = _mean_sd(meas)
        val = ms[1] if w == 2 else ms[0]
        bins = [0.0] * 20
        top = 3.0 * p["D0"]
        for m in meas:
            b = int(math.floor(m / top * 20))
            if 0 <= b < 20:
                bins[b] += 1.0
        cx = [top * (i + 0.5) / 20 for i in range(20)]
        return _base(val, _tem_exact(p), len(meas), cx, [], bins, [], [], pix=pix, mean=ms[0], sd=ms[1])


# ============================================================================================ gas sensor transient
def _gas_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["tr"] * math.log(10.0)
    if w == 2:
        return p["td"] * math.log(10.0)
    return p["Ra"] / p["Rg"]


class PcGas(_Base):
    """SIMULATED resistance transient of a metal-oxide gas sensor at its operating temperature: in air Ra; the gas is
    let in at t1 and R falls exponentially (time constant tr) towards Rg; the gas is shut off at t2 and R recovers
    (time constant td). Sampled at n points with seeded noise. The analysis: Ra = mean before t1, Rg = mean of the last
    tenth before t2, sensitivity S = Ra / Rg; response time = from t1 to 90 % of the change, recovery time = from t2
    back to within 10 % of Ra (both by linear interpolation between samples).
    what = 0 sensitivity Ra / Rg, 1 response time t90 (s), 2 recovery time (s)."""
    PARAMS = {"Ra": 2.0e6, "Rg": 1.0e5, "tr": 8.0, "td": 40.0, "t1": 60.0, "t2": 360.0, "T": 900.0, "what": 0.0,
              "n": 900.0, "method": 0.0, "noise": 0.002, "seed": 71.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(50, _i(p["n"]))
        st = _lcg(p["seed"])
        Ra, Rg = p["Ra"], p["Rg"]
        R2 = Rg + (Ra - Rg) * math.exp(-(p["t2"] - p["t1"]) / p["tr"])
        ts, Rs = [], []
        for k in range(n):
            t = p["T"] * k / (n - 1)
            if t < p["t1"]:
                R = Ra
            elif t < p["t2"]:
                R = Rg + (Ra - Rg) * math.exp(-(t - p["t1"]) / p["tr"])
            else:
                R = Ra + (R2 - Ra) * math.exp(-(t - p["t2"]) / p["td"])
            ts.append(t)
            Rs.append(R * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0)))
        sa, na, sg, ng = 0.0, 0, 0.0, 0
        for k in range(n):
            if ts[k] < p["t1"]:
                sa += Rs[k]
                na += 1
            elif p["t2"] - 0.1 * (p["t2"] - p["t1"]) <= ts[k] < p["t2"]:
                sg += Rs[k]
                ng += 1
        ra = sa / na if na else 0.0
        rg = sg / ng if ng else 0.0
        lvl = ra - 0.9 * (ra - rg)
        tres = 0.0
        for k in range(n - 1):
            if ts[k] >= p["t1"] and Rs[k] > lvl >= Rs[k + 1]:
                tres = ts[k] + (ts[k + 1] - ts[k]) * (Rs[k] - lvl) / (Rs[k] - Rs[k + 1]) - p["t1"]
                break
        lv2 = rg + 0.9 * (ra - rg)
        trec = 0.0
        for k in range(n - 1):
            if ts[k] >= p["t2"] and Rs[k] < lv2 <= Rs[k + 1]:
                trec = ts[k] + (ts[k + 1] - ts[k]) * (lv2 - Rs[k]) / (Rs[k + 1] - Rs[k]) - p["t2"]
                break
        w = _i(p["what"])
        sens = ra / rg if rg > 0 else 0.0
        val = tres if w == 1 else trec if w == 2 else sens
        return _base(val, _gas_exact(p), n, _thin(ts, 300), [], _thin([r / 1e3 for r in Rs], 300), [], [],
                     Ra=ra, Rg=rg, sens=sens, tres=tres, trec=trec)


# ============================================================================================ sputtered film: XRR + XRD
def _xrr_R(p: dict, th: float) -> float:
    """Specular X-ray reflectivity of one film (decrement delta1, thickness d) on a substrate (delta2), no absorption or
    roughness, above both critical angles so every perpendicular wavevector is real (Parratt for one layer)."""
    s2 = math.sin(th) * math.sin(th)
    k0 = math.sqrt(s2)
    k1 = math.sqrt(s2 - 2.0 * p["dl1"])
    k2 = math.sqrt(s2 - 2.0 * p["dl2"])
    r01 = (k0 - k1) / (k0 + k1)
    r12 = (k1 - k2) / (k1 + k2)
    ph = 4.0 * PI * k1 * p["d"] / p["lam"]
    c = math.cos(ph)
    return (r01 * r01 + r12 * r12 + 2.0 * r01 * r12 * c) / (1.0 + r01 * r01 * r12 * r12 + 2.0 * r01 * r12 * c)


def _quad(xs: list[float], ys: list[float]) -> list[float]:
    """Least-squares parabola y = a + b x + c x^2 by the normal equations and Cramer's rule."""
    s0 = float(len(xs))
    s1 = s2 = s3 = s4 = t0 = t1 = t2 = 0.0
    for k in range(len(xs)):
        x = xs[k]
        s1 += x
        s2 += x * x
        s3 += x * x * x
        s4 += x * x * x * x
        t0 += ys[k]
        t1 += x * ys[k]
        t2 += x * x * ys[k]
    D = s0 * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2)
    if abs(D) < 1e-300:
        return [0.0, 0.0, 0.0]
    a = (t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)) / D
    b = (s0 * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2)) / D
    c = (s0 * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2)) / D
    return [a, b, c]


def _film_exact(p: dict) -> float:
    return p["L"] if _i(p["what"]) == 1 else p["d"]


class PcFilm(_Base):
    """SIMULATED characterisation of a sputtered film. what = 0: thickness from the Kiessig fringes of an X-ray
    reflectivity scan (Cu K-alpha1, theta from th0 to th1 degrees, n points, seeded noise): the fringe minima are
    located (parabola through log R), numbered j = 0, 1, 2 ..., and sin^2 theta_j = c + (lambda / 2d)^2 (m0 + j)^2 is a
    parabola in j whose leading coefficient gives d (no need to know m0 or the critical angle). what = 1: grain size
    of the same film by the Scherrer equation on its first diffraction line (the pc9_xrd analysis)."""
    PARAMS = {"d": 20.0, "dl1": 2.2e-5, "dl2": 7.6e-6, "lam": 0.15406, "th0": 0.5, "th1": 2.5, "noise": 0.003,
              "lat": 0.0, "a": 0.36149, "c": 0.0, "L": 15.0, "eps": 0.0, "bi": 0.08, "K": 0.9, "tt0": 30.0,
              "tt1": 100.0, "what": 0.0, "n": 2000.0, "method": 0.0, "seed": 83.0}

    @staticmethod
    def init(p, cfg=None):
        if _i(p["what"]) == 1:
            q = dict(p)
            q["what"] = 3.0
            q["noise"] = 0.002
            s = PcXrd.init(q)
            s["exact"] = _film_exact(p)
            s["err"] = _err(s["val"], s["exact"])
            return s
        n = max(100, _i(p["n"]))
        st = _lcg(p["seed"])
        ths, lr = [], []
        for k in range(n):
            tdeg = p["th0"] + (p["th1"] - p["th0"]) * k / (n - 1)
            R = _xrr_R(p, tdeg * PI / 180.0) * (1.0 + p["noise"] * (2.0 * _u(st) - 1.0))
            ths.append(tdeg)
            lr.append(math.log10(R))
        step = (p["th1"] - p["th0"]) / (n - 1)
        m = max(2, _i(0.02 / step))
        mins = []
        for k in range(m, n - m):
            ok = True
            for j in range(k - m, k + m + 1):
                if (j < k and lr[j] <= lr[k]) or (j > k and lr[j] < lr[k]):
                    ok = False
                    break
            if ok:
                y0, y1, y2 = lr[k - 1], lr[k], lr[k + 1]
                den = y0 - 2.0 * y1 + y2
                mins.append(ths[k] + (0.5 * (y0 - y2) / den if den != 0 else 0.0) * step)
        js, ys = [], []
        for j in range(len(mins)):
            s = math.sin(mins[j] * PI / 180.0)
            js.append(float(j))
            ys.append(s * s)
        val = 0.0
        if len(js) >= 3:
            cf = _quad(js, ys)
            if cf[2] > 0:
                val = p["lam"] / (2.0 * math.sqrt(cf[2]))
        return _base(val, _film_exact(p), len(mins), _thin(ths, 400), [], _thin(lr, 400), js, ys, mins=mins)


# ============================================================================================ registry
KERNELS: dict[str, Any] = {"pc9_xcom": PcXcom, "pc9_qd": PcQd, "pc9_bet": PcBet, "pc9_dsc": PcDsc, "pc9_tga": PcTga,
                           "pc9_xrd": PcXrd, "pc9_tem": PcTem, "pc9_gas": PcGas, "pc9_film": PcFilm}
FAMILY = {k: "comp" for k in KERNELS}

TEXTBOOK = {"pc9_xcom_v": _xc_exact, "pc9_qd_v": _qd_exact, "pc9_bet_v": _bet_exact, "pc9_dsc_v": _dsc_exact,
            "pc9_tga_v": _tga_exact, "pc9_xrd_v": _xrd_exact, "pc9_tem_v": _tem_exact, "pc9_gas_v": _gas_exact,
            "pc9_film_v": _film_exact}


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
    """The answer of the run on the finest data (the largest n): for a measurement the truth is hidden, so the
    student reports the run with the most data points, not the one closest to a value nobody is shown."""
    rs = _rows(rows, "n", "val")
    if not rs:
        return 0.0
    b = rs[0]
    for r in rs:
        if r[0] >= b[0]:
            b = r
    return b[1]


def _best(rows, p) -> float:
    rs = _rows(rows, "n", "val", "err")
    if not rs:
        return 0.0
    b = rs[0]
    for r in rs:
        if r[2] < b[2] or (r[2] == b[2] and r[0] > b[0]):
            b = r
    return b[1]


CALCS = {
    "pc9_finest": {"label": "answer on the finest data", "unit": "", "needs": ["n", "val"], "fn": _finest},
    "pc9_best": {"label": "best value", "unit": "", "needs": ["n", "val", "err"], "fn": _best},
}
