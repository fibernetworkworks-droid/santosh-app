"""Kernel pack: PhD "Nuclear, particle and cosmic-ray physics", "Radio astronomy and astrophysics data" and
"Computational physics" research techniques, wave 10.

ONE workstation rig (`pa10-workstation`) serves every lab of this pack. Every kernel ANALYSES DATA the way the research
technique does - a time-of-flight fit, a cos^n fit, a Frank-Tamm fit, a walk-corrected timing spectrum, a drift-scan
Gaussian, a Hubble fit, a parallax mean and a main-sequence turn-off, a Lomb-Scargle / PDM period search, a Numerov
shooting or a split-step propagation.

  * Detector, telescope and archive data are SIMULATED DATA: they come from the kernel with a hidden value (a muon
    speed, an exponent, a beam width, a Hubble constant, a period ...) and seeded noise. The analysis is real, the
    measurement is not; every lab says so.
  * The computational lab (Schrodinger) shows its reference: a closed form (oscillator, hydrogen) or an independent
    method (finite differences, Richardson-extrapolated) for the double well.

Every kernel keeps the shape of the other workstation packs:
    PARAMS  the problem's numbers, `n` (data volume / grid) and `what` (which result is reported), `method`
    init    computes the whole run once; step advances a clock only
    view    val (the answer of the run), exact (the hidden / reference value), err, nused and the curves the monitor
            draws (cx / ce reference, cy what the method built, px / py data points)
    measure {val, exact, err, nused}
Anything random is the seeded Lehmer generator (16807, mod 2^31 - 1), never the clock; Gaussian deviates by Box-Muller.
The JavaScript twin is `app/static/prayog/packs/phd_astro_w10.js`, same formulas in the same order. Every name carries
the prefix `pa10_`.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
_M = 2147483647
C_SI = 299792458.0            # m/s, exact (SI)
C_NS = 0.299792458            # m/ns
C_KMS = 299792.458            # km/s
KB = 1.380649e-23             # J/K, exact (SI 2019)
FT = 369.81                   # Frank-Tamm: alpha / (hbar c) in photons per eV per cm (PDG, passage of particles)
HARTREE_EV = 27.211386245988  # eV, CODATA 2018
SIDEREAL = 0.25068            # degrees of sky per minute of time (360 deg / 1436.07 min)
FW = 2.0 * math.sqrt(2.0 * math.log(2.0))     # FWHM / sigma of a Gaussian


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


def _g(st: list[float]) -> float:
    a = _u(st)
    b = _u(st)
    return math.sqrt(-2.0 * math.log(a)) * math.cos(2.0 * PI * b)


def _poisson(st: list[float], mu: float) -> int:
    lim = math.exp(-mu)
    k = 0
    q = _u(st)
    while q > lim:
        k += 1
        q *= _u(st)
    return k


def _thin(xs: list[float], m: int) -> list[float]:
    n = len(xs)
    if n <= m + 1:
        return list(xs)
    return [xs[_i(i * (n - 1) / m)] for i in range(m + 1)]


def _wline(xs: list[float], ys: list[float], ws: list[float]) -> list[float]:
    """Weighted least-squares straight line y = a + b x, summed left to right (the JS twin sums the same way)."""
    n = len(xs)
    if n < 2:
        return [0.0, 0.0]
    sw = 0.0
    sx = 0.0
    sy = 0.0
    sxx = 0.0
    sxy = 0.0
    for k in range(n):
        w = ws[k]
        sw += w
        sx += w * xs[k]
        sy += w * ys[k]
        sxx += w * xs[k] * xs[k]
        sxy += w * xs[k] * ys[k]
    den = sw * sxx - sx * sx
    if abs(den) < 1e-300:
        return [0.0, 0.0]
    b = (sw * sxy - sx * sy) / den
    return [(sy - b * sx) / sw, b]


def _line(xs: list[float], ys: list[float]) -> list[float]:
    return _wline(xs, ys, [1.0] * len(xs))


def _hist(vals: list[float], lo: float, hi: float, nb: int) -> list[list[float]]:
    cx = [lo + (hi - lo) * (k + 0.5) / nb for k in range(nb)]
    cy = [0.0] * nb
    for v in vals:
        k = int(math.floor((v - lo) / (hi - lo) * nb))
        if 0 <= k < nb:
            cy[k] += 1.0
    return [cx, cy]


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (small dense systems)."""
    n = len(b)
    M = [list(A[r]) + [b[r]] for r in range(n)]
    for c in range(n):
        piv = c
        for r in range(c + 1, n):
            if abs(M[r][c]) > abs(M[piv][c]):
                piv = r
        if piv != c:
            M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        if abs(d) < 1e-300:
            return [0.0] * n
        for r in range(c + 1, n):
            f = M[r][c] / d
            if f != 0.0:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n]
        for k in range(r + 1, n):
            s -= M[r][k] * x[k]
        x[r] = s / M[r][r]
    return x


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


# ============================================================================================ muon time of flight
def _tof_exact(p: dict) -> float:
    return p["beta"]


class PaTof(_Base):
    """Two scintillator paddles at separations d = 0 ... dmax; for every muon the start-stop time is
    t = t0 + d / (beta c) + timing jitter. The mean time at each separation, fitted against d, has slope 1 / v.
    SIMULATED: every muon is given the same hidden beta (the real spread of muon energies is left out)."""
    PARAMS = {"beta": 0.9965, "t0": 12.0, "sig": 0.8, "dmax": 2.5, "nd": 6.0, "n": 3200.0, "what": 0.0, "method": 0.0,
              "seed": 101.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(5, _i(p["n"]))
        nd = max(3, _i(p["nd"]))
        st = _lcg(p["seed"])
        xs, ys = [], []
        for k in range(nd):
            d = p["dmax"] * k / (nd - 1)
            s = 0.0
            for _ in range(n):
                s += p["t0"] + d / (p["beta"] * C_NS) + p["sig"] * _g(st)
            xs.append(d)
            ys.append(s / n)
        ab = _line(xs, ys)
        b = ab[1]
        v = 1.0 / b if b > 0 else 0.0
        val = v / C_NS
        cx = [0.0, p["dmax"]]
        cy = [ab[0], ab[0] + b * p["dmax"]]
        return _base(val, _tof_exact(p), nd * n, cx, [], cy, xs, ys, slope=b, offset=ab[0], v=v)


# ============================================================================================ cosmic-ray zenith law
def _zen_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["I0"]
    if w == 2:
        return p["I0"] * 2.0 * PI / (p["nexp"] + 2.0)
    return p["nexp"]


class PaZenith(_Base):
    """A two-detector coincidence telescope tilted to zenith angles 0 ... amax counts for n minutes at each angle.
    Rate = eff I0 cos^nexp(theta) A^2 / D^2 (a narrow telescope). A weighted straight line of ln(rate) against
    ln(cos theta) gives the exponent (slope) and the vertical intensity (intercept); the flux through a horizontal
    surface is J = I0 2 pi / (n + 2). SIMULATED: counts are Poisson (Gaussian approximation) about the hidden law.
    what = 0 exponent, 1 vertical intensity (m^-2 s^-1 sr^-1), 2 flux J (m^-2 s^-1)."""
    PARAMS = {"nexp": 2.0, "I0": 70.0, "A": 0.09, "D": 1.0, "eff": 0.95, "amax": 75.0, "na": 6.0, "n": 960.0,
              "what": 0.0, "method": 0.0, "seed": 103.0}

    @staticmethod
    def init(p, cfg=None):
        na = max(3, _i(p["na"]))
        T = max(1.0, p["n"]) * 60.0
        st = _lcg(p["seed"])
        G = p["A"] * p["A"] / (p["D"] * p["D"])
        xs, ys, ws, px, py = [], [], [], [], []
        for k in range(na):
            th = p["amax"] * k / (na - 1)
            c = math.cos(th * PI / 180.0)
            mu = p["eff"] * p["I0"] * G * math.pow(c, p["nexp"]) * T
            N = max(1, _i(mu + math.sqrt(mu) * _g(st)))
            xs.append(math.log(c))
            ys.append(math.log(N / T))
            ws.append(float(N))
            px.append(th)
            py.append(N / T * 60.0)
        ab = _wline(xs, ys, ws)
        nf = ab[1]
        I0 = math.exp(ab[0]) / (p["eff"] * G)
        J = I0 * 2.0 * PI / (nf + 2.0)
        w = _i(p["what"])
        val = I0 if w == 1 else J if w == 2 else nf
        cx, cy = [], []
        for k in range(31):
            th = p["amax"] * k / 30.0
            cx.append(th)
            cy.append(math.exp(ab[0]) * math.pow(math.cos(th * PI / 180.0), nf) * 60.0)
        return _base(val, _zen_exact(p), na * p["n"], cx, [], cy, px, py, nfit=nf, I0fit=I0, J=J)


# ============================================================================================ relativistic dynamics
def _rel_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        return C_SI * C_SI / (p["mc2"] * 1.0e6) / 1.0e11
    return p["mc2"]


class PaReldyn(_Base):
    """Sr-90 beta electrons selected in a field B on a circle of radius r (p = e B r, so pc = c B r in eV), their
    speed read by the crossed-field selector (v = E / B) and their kinetic energy by a calibrated detector.
    E^2 = (pc)^2 + (mc^2)^2 means (pc)^2 - T^2 = 2 mc^2 T: the slope of that line is twice the rest energy, and
    e/m = gamma v / (B r). SIMULATED: per-electron energy resolution sT and selector spread sv about the
    relativistic truth (CODATA electron). what = 0 rest energy (MeV), 1 e/m (1e11 C/kg)."""
    PARAMS = {"r": 0.2, "mc2": 0.51099895, "Bmin": 0.004, "Bmax": 0.016, "nb": 7.0, "sT": 0.05, "sv": 0.004,
              "n": 640.0, "what": 0.0, "method": 0.0, "seed": 107.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(2, _i(p["n"]))
        nb = max(3, _i(p["nb"]))
        st = _lcg(p["seed"])
        xs, ys, Bs, ems = [], [], [], []
        for k in range(nb):
            B = p["Bmin"] + (p["Bmax"] - p["Bmin"]) * k / (nb - 1)
            pc = C_SI * B * p["r"] / 1.0e6
            E = math.sqrt(pc * pc + p["mc2"] * p["mc2"])
            T = E - p["mc2"]
            beta = pc / E
            sT = 0.0
            sb = 0.0
            for _ in range(n):
                sT += T * (1.0 + p["sT"] * _g(st))
                sb += beta * (1.0 + p["sv"] * _g(st))
            Tm = sT / n
            bm = min(sb / n, 0.999999)
            xs.append(Tm)
            ys.append(pc * pc - Tm * Tm)
            Bs.append(B * 1000.0)
            ems.append(bm * C_SI / math.sqrt(1.0 - bm * bm) / (B * p["r"]) / 1.0e11)
        ab = _line(xs, ys)
        mfit = ab[1] / 2.0
        em = 0.0
        for e in ems:
            em += e
        em = em / nb
        if _i(p["what"]) == 1:
            val = em
            px, py = Bs, ems
            cx, cy = [Bs[0], Bs[nb - 1]], [em, em]
        else:
            val = mfit
            px, py = xs, ys
            cx, cy = [0.0, xs[nb - 1]], [ab[0], ab[0] + ab[1] * xs[nb - 1]]
        return _base(val, _rel_exact(p), nb * n, cx, [], cy, px, py, mfit=mfit, em=em)


# ============================================================================================ Cherenkov threshold
def _cher_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        return p["eps"] * FT * p["dE"] * (1.0 - 1.0 / (p["nidx"] * p["nidx"]))
    return 1.0 / p["nidx"]


class PaCher(_Base):
    """A test beam of pions (momentum pmin ... pmax) crosses a radiator of thickness L (cm). The mean number of
    photoelectrons is N = eps * 369.81 * dE * L * (1 - 1 / (beta^2 n^2)) (Frank-Tamm), linear in x = 1 / beta^2:
    N = a + b x, so n^2 = -a / b, the threshold velocity beta_th = 1 / n = sqrt(-b / a), and the light yield at
    beta = 1 is (a + b) / L photoelectrons per cm. SIMULATED: Poisson (Gaussian approximation) photoelectron counts
    about the hidden refractive index. what = 0 threshold velocity, 1 light yield (p.e. / cm)."""
    PARAMS = {"nidx": 1.333, "L": 10.0, "mass": 139.57039, "pmin": 250.0, "pmax": 2000.0, "np": 8.0, "eps": 0.08,
              "dE": 1.0, "n": 400.0, "what": 0.0, "method": 0.0, "seed": 109.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(2, _i(p["n"]))
        npnt = max(3, _i(p["np"]))
        st = _lcg(p["seed"])
        K = p["eps"] * FT * p["dE"] * p["L"]
        xs, ys = [], []
        for k in range(npnt):
            pm = p["pmin"] + (p["pmax"] - p["pmin"]) * k / (npnt - 1)
            beta = pm / math.sqrt(pm * pm + p["mass"] * p["mass"])
            mu = K * (1.0 - 1.0 / (beta * beta * p["nidx"] * p["nidx"]))
            if mu < 0.0:
                mu = 0.0
            s = 0.0
            for _ in range(n):
                v = mu + math.sqrt(mu) * _g(st)
                s += v if v > 0.0 else 0.0
            xs.append(1.0 / (beta * beta))
            ys.append(s / n)
        ab = _line(xs, ys)
        a, b = ab[0], ab[1]
        bth = math.sqrt(-b / a) if (a > 0 and b < 0) else 0.0
        yl = (a + b) / p["L"]
        val = yl if _i(p["what"]) == 1 else bth
        x0 = 1.0
        x1 = xs[0]
        cx = [x0, x1]
        cy = [a + b * x0, a + b * x1]
        return _base(val, _cher_exact(p), npnt * n, cx, [], cy, xs, ys, bth=bth, yld=yl, nfit=(1.0 / bth if bth > 0 else 0.0))


# ============================================================================================ SiPM timing
def _sipm_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        return p["mu"]
    return FW * math.sqrt(2.0) * p["sig"] * 1000.0


class PaSipm(_Base):
    """what = 0: two identical scintillator + SiPM detectors see the same annihilation pair. Each pulse rises
    linearly to its amplitude A in tr; A is spread (photopeak and Compton events, uniform 0.3 - 1 of Am). A
    constant-fraction discriminator fires at a fixed fraction of A, so the time difference is the detectors' own
    jitter; a leading-edge discriminator fires at a fixed level L and walks by tr L / A, which is removed by a
    straight-line fit of the time difference against 1/A1 - 1/A2. CTR = FWHM of the corrected difference (ps).
    what = 1: a low-light finger spectrum: k ~ Poisson(mu) photoelectrons, charge k * gain + noise; the pedestal
    fraction gives mu = -ln(N0 / N). SIMULATED: the per-detector jitter sig and mu are hidden.
    method = 0 constant fraction, 1 leading edge with walk correction."""
    PARAMS = {"sig": 0.09, "tr": 1.2, "Am": 100.0, "thr": 0.1, "mu": 1.5, "gain": 1.0, "enc": 0.08, "n": 20000.0,
              "what": 0.0, "method": 0.0, "seed": 113.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(20, _i(p["n"]))
        st = _lcg(p["seed"])
        if _i(p["what"]) == 1:
            qs = []
            n0 = 0
            for _ in range(n):
                k = _poisson(st, p["mu"])
                q = p["gain"] * k + p["enc"] * _g(st)
                qs.append(q)
                if q < 0.5 * p["gain"]:
                    n0 += 1
            mu = -math.log(n0 / n) if n0 > 0 else 0.0
            hi = p["mu"] + 4.0 * math.sqrt(p["mu"]) + 1.5
            h = _hist(qs, -0.5, hi, 80)
            return _base(mu, _sipm_exact(p), n, h[0], [], h[1], [], [], n0=float(n0), mufit=mu)
        lev = p["thr"] * p["Am"]
        le = _i(p["method"]) == 1
        ds, xs = [], []
        for _ in range(n):
            a1 = p["Am"] * (0.3 + 0.7 * _u(st))
            a2 = p["Am"] * (0.3 + 0.7 * _u(st))
            t1 = p["sig"] * _g(st)
            t2 = p["sig"] * _g(st)
            if le:
                ds.append((t1 + p["tr"] * lev / a1) - (t2 + p["tr"] * lev / a2))
                xs.append(1.0 / a1 - 1.0 / a2)
            else:
                ds.append(t1 - t2)
                xs.append(0.0)
        slope = 0.0
        if le:
            slope = _line(xs, ds)[1]
        m = 0.0
        for k in range(n):
            m += ds[k] - slope * xs[k]
        m = m / n
        v = 0.0
        rs = []
        for k in range(n):
            r = (ds[k] - slope * xs[k] - m) * 1000.0
            rs.append(r)
            v += r * r
        sd = math.sqrt(v / (n - 1))
        ctr = FW * sd
        h = _hist(rs, -4.0 * sd, 4.0 * sd, 41)
        return _base(ctr, _sipm_exact(p), n, h[0], [], h[1], [], [], walk=slope, sd=sd)


# ============================================================================================ radio telescope
def _rad_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["Trx"] + p["Tcold"]
    if w == 2:
        return p["S"]
    return p["fwhm"]


class PaRadio(_Base):
    """what = 0: a drift scan of the Sun through a Gaussian beam. Its time FWHM converts to an angle on the sky
    (0.25068 deg per minute times cos dec); the Sun's own disc (taken as a Gaussian of FWHM ssun) is removed in
    quadrature. The FWHM is fitted as a parabola in ln(T - baseline) over the top half of the scan.
    what = 1: Y-factor: total power on an absorber at Thot and on cold sky at Tcold, each integrated for n seconds
    (radiometer noise 1 / sqrt(bandwidth tau)); Trx = (Thot - Y Tcold) / (Y - 1); system temperature on the cold sky
    Tsys = Trx + Tcold. what = 2: a drift scan of a point source (Cas A / Cyg A): the amplitude of the known beam
    shape on a constant baseline gives the antenna temperature Ta, and S = 2 k Ta / Ae (Jy).
    n = drift scans averaged (what 0 and 2) or seconds of integration (what 1). SIMULATED DATA."""
    PARAMS = {"fwhm": 6.0, "dec": -10.0, "ssun": 0.53, "Tpk": 250.0, "Tb": 120.0, "sig": 3.0, "Thot": 290.0,
              "Tcold": 8.0, "Trx": 95.0, "bw": 1.0e6, "S": 1500.0, "D": 2.3, "eta": 0.6, "sdec": 58.8, "sigf": 0.15,
              "n": 16.0, "what": 0.0, "method": 0.0, "seed": 127.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(1.0, p["n"])
        st = _lcg(p["seed"])
        w = _i(p["what"])
        if w == 1:
            r = 1.0 / math.sqrt(p["bw"] * n)
            Ph = (p["Trx"] + p["Thot"]) * (1.0 + r * _g(st))
            Pc = (p["Trx"] + p["Tcold"]) * (1.0 + r * _g(st))
            Y = Ph / Pc
            trx = (p["Thot"] - Y * p["Tcold"]) / (Y - 1.0)
            ts = trx + p["Tcold"]
            g = (Ph - Pc) / (p["Thot"] - p["Tcold"])
            cx = [-trx * 1.2, p["Thot"]]
            cy = [Pc + g * (cx[0] - p["Tcold"]), Pc + g * (cx[1] - p["Tcold"])]
            return _base(ts, _rad_exact(p), n, cx, [], cy, [p["Tcold"], p["Thot"]], [Pc, Ph], Y=Y, Trx=trx)
        m = 400
        if w == 2:
            wt = p["fwhm"] / (SIDEREAL * math.cos(p["sdec"] * PI / 180.0))
            Ae = p["eta"] * PI * p["D"] * p["D"] / 4.0
            Ta = p["S"] * 1.0e-26 * Ae / (2.0 * KB)
            sg = p["sigf"] / math.sqrt(n)
            ts, ys, gs = [], [], []
            for k in range(m):
                t = -3.0 * wt + 6.0 * wt * k / (m - 1)
                gb = math.exp(-4.0 * math.log(2.0) * t * t / (wt * wt))
                ts.append(t)
                gs.append(gb)
                ys.append(p["Tb"] + Ta * gb + sg * _g(st))
            # least squares for baseline c and amplitude a in y = c + a g
            s1 = float(m)
            sg1 = 0.0
            sgg = 0.0
            sy = 0.0
            sgy = 0.0
            for k in range(m):
                sg1 += gs[k]
                sgg += gs[k] * gs[k]
                sy += ys[k]
                sgy += gs[k] * ys[k]
            den = s1 * sgg - sg1 * sg1
            a = (s1 * sgy - sg1 * sy) / den
            c = (sy - a * sg1) / s1
            S = 2.0 * KB * a / Ae / 1.0e-26
            cy = [c + a * gs[k] for k in range(m)]
            return _base(S, _rad_exact(p), m * n, _thin(ts, 200), [], _thin(cy, 200), _thin(ts, 200), _thin(ys, 200),
                         Ta=a, base=c, Ae=Ae)
        weff = math.sqrt(p["fwhm"] * p["fwhm"] + p["ssun"] * p["ssun"])
        cd = math.cos(p["dec"] * PI / 180.0)
        wt = weff / (SIDEREAL * cd)
        sg = p["sig"] / math.sqrt(n)
        ts, ys = [], []
        for k in range(m):
            t = -3.0 * wt + 6.0 * wt * k / (m - 1)
            ts.append(t)
            ys.append(p["Tb"] + p["Tpk"] * math.exp(-4.0 * math.log(2.0) * t * t / (wt * wt)) + sg * _g(st))
        e = m // 8
        bl = 0.0
        for k in range(e):
            bl += ys[k] + ys[m - 1 - k]
        bl = bl / (2 * e)
        top = 0.0
        for k in range(m):
            if ys[k] - bl > top:
                top = ys[k] - bl
        A = [[0.0] * 3 for _ in range(3)]
        bb = [0.0] * 3
        used = 0
        for k in range(m):
            y = ys[k] - bl
            if y > 0.5 * top:
                t = ts[k]
                row = [1.0, t, t * t]
                ly = math.log(y)
                for i2 in range(3):
                    for j2 in range(3):
                        A[i2][j2] += row[i2] * row[j2]
                    bb[i2] += row[i2] * ly
                used += 1
        c3 = _solve(A, bb)
        ww = FW * math.sqrt(-1.0 / (2.0 * c3[2])) if c3[2] < 0 else 0.0
        sky = ww * SIDEREAL * cd
        beam = math.sqrt(sky * sky - p["ssun"] * p["ssun"]) if sky > p["ssun"] else 0.0
        cy = []
        for k in range(m):
            t = ts[k]
            cy.append(bl + math.exp(c3[0] + c3[1] * t + c3[2] * t * t))
        return _base(beam, _rad_exact(p), used, _thin(ts, 200), [], _thin(cy, 200), _thin(ts, 200), _thin(ys, 200),
                     wtime=ww, sky=sky, base=bl)


# ============================================================================================ Hubble's law
H_LINES = [6562.80, 4861.33, 5006.84]      # air wavelengths, angstrom: H-alpha, H-beta, [O III] (from memory - verify)


def _hub_exact(p: dict) -> float:
    return p["H0"]


class PaHubble(_Base):
    """n galaxies at known distances d (Mpc, a calibrated standard candle, taken as exact) recede at H0 d plus a
    peculiar velocity (Gaussian, sv). Each spectrum's H-alpha, H-beta and [O III] lines are measured with a
    wavelength error sl (angstrom); z = mean(lambda_obs / lambda_0 - 1), v = c z (low redshift). The Hubble constant
    is the least-squares slope of v against d through the origin. SIMULATED DATA: no SDSS spectrum is read."""
    PARAMS = {"H0": 70.0, "dmin": 20.0, "dmax": 400.0, "sv": 300.0, "sl": 1.0, "n": 200.0, "what": 0.0,
              "method": 0.0, "seed": 131.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(3, _i(p["n"]))
        st = _lcg(p["seed"])
        ds, vs = [], []
        zfar = 0.0
        dfar = 0.0
        for _ in range(n):
            d = p["dmin"] + (p["dmax"] - p["dmin"]) * _u(st)
            vt = p["H0"] * d + p["sv"] * _g(st)
            z = vt / C_KMS
            zs = 0.0
            for lam in H_LINES:
                zs += (lam * (1.0 + z) + p["sl"] * _g(st)) / lam - 1.0
            zm = zs / len(H_LINES)
            ds.append(d)
            vs.append(C_KMS * zm)
            if d > dfar:
                dfar = d
                zfar = zm
        sdv = 0.0
        sdd = 0.0
        for k in range(n):
            sdv += ds[k] * vs[k]
            sdd += ds[k] * ds[k]
        H = sdv / sdd
        return _base(H, _hub_exact(p), n, [0.0, p["dmax"]], [], [0.0, H * p["dmax"]], _thin(ds, 300), _thin(vs, 300),
                     zfar=zfar, dfar=dfar)


# ============================================================================================ cluster colour-magnitude
def _cmd_exact(p: dict) -> float:
    return p["age"] if _i(p["what"]) == 1 else p["dist"]


class PaCmd(_Base):
    """A toy open cluster: n stars drawn from a Salpeter mass function (alpha, Mlo - Mhi). Main-sequence scalings:
    L = M^3.5, lifetime t = 10 Gyr M^-2.5, colour BP-RP = 0.82 - 0.95 log10(M); stars older than their lifetime have
    left the main sequence and are not in the list. Each member has a Gaia-like parallax (error sp, mas) and G
    (error sg). Distance = 1000 / mean parallax (pc); the turn-off is the brightest main-sequence star: its absolute
    G gives L, M = L^(1/3.5) and the age 10 Gyr M^-2.5. SIMULATED DATA built on these scalings - an age ESTIMATE,
    not an isochrone fit. what = 0 distance (pc), 1 turn-off age (Gyr)."""
    PARAMS = {"dist": 400.0, "age": 0.8, "Mlo": 0.6, "Mhi": 6.0, "alpha": 2.35, "sp": 0.04, "sg": 0.003,
              "MGsun": 4.67, "n": 4000.0, "what": 0.0, "method": 0.0, "seed": 137.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(10, _i(p["n"]))
        st = _lcg(p["seed"])
        e = 1.0 - p["alpha"]
        lo = math.pow(p["Mlo"], e)
        hi = math.pow(p["Mhi"], e)
        dm = 5.0 * math.log10(p["dist"]) - 5.0
        pis, cs, gs = [], [], []
        gmin = 99.0
        for _ in range(n):
            M = math.pow(lo + _u(st) * (hi - lo), 1.0 / e)
            life = 10.0 * math.pow(M, -2.5)
            pp = 1000.0 / p["dist"] + p["sp"] * _g(st)
            gg = p["MGsun"] - 2.5 * 3.5 * math.log10(M) + dm + p["sg"] * _g(st)
            if life < p["age"]:
                continue
            pis.append(pp)
            cs.append(0.82 - 0.95 * math.log10(M))
            gs.append(gg)
            if gg < gmin:
                gmin = gg
        s = 0.0
        for q in pis:
            s += q
        dist = 1000.0 / (s / len(pis)) if pis else 0.0
        MG = gmin - 5.0 * math.log10(dist) + 5.0 if dist > 0 else 0.0
        L = math.pow(10.0, -0.4 * (MG - p["MGsun"]))
        M = math.pow(L, 1.0 / 3.5)
        age = 10.0 * math.pow(M, -2.5)
        val = age if _i(p["what"]) == 1 else dist
        py = [-g for g in gs]
        c0 = min(cs) if cs else 0.0
        c1 = max(cs) if cs else 1.0
        return _base(val, _cmd_exact(p), len(pis), [c0, c1], [], [-gmin, -gmin], _thin(cs, 600), _thin(py, 600),
                     dfit=dist, agefit=age, Mto=M, nmem=float(len(pis)))


# ============================================================================================ variable-star period
def _lsp_shape(kind: int, ph: float) -> float:
    a = 2.0 * PI * ph
    if kind == 1:
        return -(math.sin(a) + 0.5 * math.sin(2 * a) + 0.3 * math.sin(3 * a) + 0.15 * math.sin(4 * a))
    if kind == 2:
        d1 = ph - math.floor(ph + 0.5)
        d2 = ph - 0.5 - math.floor(ph)
        return math.exp(-d1 * d1 / 0.0018) + 0.4 * math.exp(-d2 * d2 / 0.0018)
    return -(math.sin(a) + 0.35 * math.sin(2 * a) + 0.12 * math.sin(3 * a))


def _lsp_norm(kind: int) -> list[float]:
    lo = 1e30
    hi = -1e30
    for k in range(2000):
        s = _lsp_shape(kind, k / 2000.0)
        lo = min(lo, s)
        hi = max(hi, s)
    return [lo, hi - lo]


def _lsp_absmag(p: dict, P: float) -> float:
    return p["plA"] * (math.log10(P) - 1.0) + p["plB"]


def _lsp_m0(p: dict) -> float:
    if _i(p["kind"]) == 0:
        return _lsp_absmag(p, p["P"]) + 5.0 * math.log10(p["dist"]) - 5.0
    return p["mag"]


def _lsp_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["A"]
    if w == 2:
        return p["dist"]
    return p["P"]


def _ls_power(ts: list[float], ys: list[float], f: float) -> float:
    w = 2.0 * PI * f
    s2 = 0.0
    c2 = 0.0
    for t in ts:
        s2 += math.sin(2.0 * w * t)
        c2 += math.cos(2.0 * w * t)
    tau = math.atan2(s2, c2) / (2.0 * w)
    yc = 0.0
    ys2 = 0.0
    cc = 0.0
    ss = 0.0
    for k in range(len(ts)):
        c = math.cos(w * (ts[k] - tau))
        s = math.sin(w * (ts[k] - tau))
        yc += ys[k] * c
        ys2 += ys[k] * s
        cc += c * c
        ss += s * s
    return 0.5 * (yc * yc / cc + ys2 * ys2 / ss)


def _pdm_theta(ts: list[float], ys: list[float], f: float, var: float, nb: int) -> float:
    sm = [0.0] * nb
    sq = [0.0] * nb
    nn = [0] * nb
    for k in range(len(ts)):
        ph = ts[k] * f
        ph = ph - math.floor(ph)
        b = int(ph * nb)
        if b >= nb:
            b = nb - 1
        sm[b] += ys[k]
        sq[b] += ys[k] * ys[k]
        nn[b] += 1
    num = 0.0
    dof = 0
    for b in range(nb):
        if nn[b] > 1:
            num += sq[b] - sm[b] * sm[b] / nn[b]
            dof += nn[b] - 1
    if dof <= 0 or var <= 0:
        return 1.0
    return (num / dof) / var


def _lsp_fit(ts: list[float], ys: list[float], f: float) -> list:
    """4-harmonic least-squares Fourier fit at frequency f: [coefficients, residual sum of squares]."""
    H = 4
    nc = 2 * H + 1
    A = [[0.0] * nc for _ in range(nc)]
    bv = [0.0] * nc
    rows = []
    for k in range(len(ts)):
        ph = 2.0 * PI * ts[k] * f
        row = [1.0]
        for h in range(1, H + 1):
            row.append(math.cos(h * ph))
            row.append(math.sin(h * ph))
        rows.append(row)
        for i2 in range(nc):
            for j2 in range(nc):
                A[i2][j2] += row[i2] * row[j2]
            bv[i2] += row[i2] * ys[k]
    co = _solve(A, bv)
    r2 = 0.0
    for k in range(len(ts)):
        v = 0.0
        for i2 in range(nc):
            v += co[i2] * rows[k][i2]
        r2 += (ys[k] - v) * (ys[k] - v)
    return [co, r2]


class PaLsp(_Base):
    """A survey light curve: n epochs at random times over span days, magnitude m0 + A s(phase) / ptp(s) + noise.
    Shapes: kind 0 Cepheid, 1 RR Lyrae (Fourier series), 2 detached eclipsing binary (two Gaussian eclipses, the
    secondary 0.4 deep). method 0 Lomb-Scargle (power maximum), 1 phase dispersion minimisation (10 bins, theta
    minimum); the coarse frequency grid (step 1 / (5 span)) is refined twenty times finer around the best point and
    by a parabola through the top three. The amplitude is the peak-to-peak of a 4-harmonic least-squares fit at that
    period; the distance (Cepheid) uses its mean magnitude and the period-luminosity relation
    M_V = plA (log10 P - 1) + plB. SIMULATED DATA. what = 0 period (d), 1 amplitude (mag), 2 distance (pc)."""
    PARAMS = {"P": 5.37, "A": 0.8, "kind": 0.0, "dist": 1500.0, "mag": 12.0, "plA": -2.43, "plB": -4.05,
              "span": 120.0, "sig": 0.02, "fmin": 0.05, "fmax": 2.5, "nbin": 10.0, "n": 200.0, "what": 0.0, "method": 0.0,
              "seed": 139.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(20, _i(p["n"]))
        st = _lcg(p["seed"])
        kind = _i(p["kind"])
        nrm = _lsp_norm(kind)
        m0 = _lsp_m0(p)
        ts, ys = [], []
        for _ in range(n):
            t = p["span"] * _u(st)
            s = (_lsp_shape(kind, t / p["P"]) - (nrm[0] if kind == 2 else 0.0)) / nrm[1]
            ts.append(t)
            ys.append(m0 + p["A"] * s + p["sig"] * _g(st))
        mean = 0.0
        for y in ys:
            mean += y
        mean = mean / n
        yc = [y - mean for y in ys]
        var = 0.0
        for y in yc:
            var += y * y
        var = var / (n - 1)
        pdm = _i(p["method"]) == 1
        nbin = max(5, _i(p["nbin"]))

        def score(f: float) -> float:
            return -_pdm_theta(ts, yc, f, var, nbin) if pdm else _ls_power(ts, yc, f)

        df = 1.0 / (5.0 * p["span"])
        nf = int((p["fmax"] - p["fmin"]) / df) + 1
        fs, sc = [], []
        bi = 0
        for k in range(nf):
            f = p["fmin"] + df * k
            v = score(f)
            fs.append(f)
            sc.append(v)
            if v > sc[bi]:
                bi = k
        f0 = fs[bi]
        d2 = df / 20.0
        best = sc[bi]
        fb = f0
        vals = []
        for k in range(-20, 21):
            f = f0 + d2 * k
            v = score(f)
            vals.append(v)
            if v > best:
                best = v
                fb = f
        kb = _i((fb - f0) / d2) + 20
        if 0 < kb < 40:
            a, b, c = vals[kb - 1], vals[kb], vals[kb + 1]
            den = a - 2.0 * b + c
            if den < 0:
                fb = fb + 0.5 * d2 * (a - c) / den
        # refine: the frequency where a 4-harmonic least-squares fit leaves the smallest residual (13 trial
        # frequencies, step d2 / 2, and a parabola through the best three)
        best = 1e300
        kq = 0
        chis = []
        for k in range(13):
            f = fb + 0.5 * d2 * (k - 6)
            c2 = _lsp_fit(ts, ys, f)[1]
            chis.append(c2)
            if c2 < best:
                best = c2
                kq = k
        fq = fb + 0.5 * d2 * (kq - 6)
        if 0 < kq < 12:
            a, b, c = chis[kq - 1], chis[kq], chis[kq + 1]
            den = a - 2.0 * b + c
            if den > 0:
                fq = fq + 0.25 * d2 * (a - c) / den
        fb = fq
        P = 1.0 / fb
        H = 4
        co = _lsp_fit(ts, ys, fb)[0]
        lo = 1e30
        hi = -1e30
        mx, my = [], []
        for k in range(400):
            ph = k / 400.0
            v = co[0]
            for h in range(1, H + 1):
                v += co[2 * h - 1] * math.cos(2.0 * PI * h * ph) + co[2 * h] * math.sin(2.0 * PI * h * ph)
            lo = min(lo, v)
            hi = max(hi, v)
            if k % 4 == 0:
                mx.append(ph)
                my.append(v)
        amp = hi - lo
        Mv = _lsp_absmag(p, P)
        dist = math.pow(10.0, (co[0] - Mv + 5.0) / 5.0)
        w = _i(p["what"])
        val = amp if w == 1 else dist if w == 2 else P
        if w == 0:
            return _base(val, _lsp_exact(p), n, _thin(fs, 400), [], _thin(sc, 400), [], [], Pfit=P, amp=amp, dfit=dist,
                         fbest=fb)
        px = []
        for t in ts:
            q = t / P
            px.append(q - math.floor(q))
        return _base(val, _lsp_exact(p), n, mx, [], my, _thin(px, 300), _thin(ys, 300), Pfit=P, amp=amp, dfit=dist,
                     fbest=fb)


# ============================================================================================ Schrodinger equation
def _sch_pot(p: dict, x: float) -> float:
    k = _i(p["pot"])
    if k == 1:
        q = x / p["a"]
        return p["V0"] * (q * q - 1.0) * (q * q - 1.0)
    return 0.5 * x * x


def _sch_nodes(p: dict, E: float, n: int) -> int:
    """Numerov outward integration of psi'' = f psi; returns the number of sign changes of psi (or u)."""
    hyd = _i(p["pot"]) == 2
    if hyd:
        h = p["rmax"] / n
        l = _i(p["l"])
        x0 = 0.0
    else:
        h = 2.0 * p["L"] / n
        x0 = -p["L"]
        l = 0
    h12 = h * h / 12.0

    def f(x: float) -> float:
        if hyd:
            return l * (l + 1) / (x * x) - 2.0 / x - 2.0 * E
        return 2.0 * (_sch_pot(p, x) - E)

    y0 = 0.0
    y1 = math.pow(h, l + 1) if hyd else 1e-6
    f1 = f(x0 + h)
    nodes = 0
    fprev = 0.0
    for i in range(1, n):
        x2 = x0 + (i + 1) * h
        f2 = f(x2)
        term0 = 0.0 if (hyd and i == 1) else (1.0 - h12 * fprev) * y0
        y2 = (2.0 * (1.0 + 5.0 * h12 * f1) * y1 - term0) / (1.0 - h12 * f2)
        if (y2 < 0) != (y1 < 0) and y2 != 0.0:
            nodes += 1
        y0, y1 = y1, y2
        fprev, f1 = f1, f2
        if abs(y1) > 1e200:
            y0 *= 1e-200
            y1 *= 1e-200
    return nodes


def _sch_shoot(p: dict, n: int, k: int) -> float:
    if _i(p["pot"]) == 2:
        lo, hi = -0.6, -1e-6
    else:
        lo, hi = 0.0, 40.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if _sch_nodes(p, mid, n) <= k:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _fd_count(p: dict, N: int, E: float) -> int:
    """Sturm count: eigenvalues of the finite-difference Hamiltonian -(1/2) d2/dx2 + V on N interior points below E."""
    h = 2.0 * p["L"] / (N + 1)
    off = -0.5 / (h * h)
    cnt = 0
    q = 1.0
    for i in range(N):
        x = -p["L"] + (i + 1) * h
        d = 1.0 / (h * h) + _sch_pot(p, x) - E
        q = d - (off * off / q if i > 0 else 0.0)
        if q == 0.0:
            q = 1e-300
        if q < 0:
            cnt += 1
    return cnt


def _fd_eig(p: dict, N: int, k: int) -> float:
    lo, hi = 0.0, 40.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if _fd_count(p, N, mid) <= k:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _dw_ref(p: dict, k: int) -> float:
    """Double-well reference: finite differences on 1500 and 3000 points, Richardson-extrapolated (error ~ h^2)."""
    e1 = _fd_eig(p, 1500, k)
    e2 = _fd_eig(p, 3000, k)
    h1 = 2.0 * p["L"] / 1501.0
    h2 = 2.0 * p["L"] / 3001.0
    return (e2 * h1 * h1 - e1 * h2 * h2) / (h1 * h1 - h2 * h2)


def _sch_exact(p: dict) -> float:
    pot = _i(p["pot"])
    k = _i(p["k"])
    if _i(p["method"]) == 1:
        return PI / (_dw_ref(p, 1) - _dw_ref(p, 0))
    if pot == 0:
        return k + 0.5
    if pot == 2:
        nq = k + _i(p["l"]) + 1
        return -0.5 / (nq * nq) * HARTREE_EV
    return _dw_ref(p, k)


def _fft(re: list[float], im: list[float], inv: bool) -> None:
    """In-place iterative radix-2 FFT (length a power of two)."""
    n = len(re)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    ln = 2
    while ln <= n:
        ang = (2.0 if inv else -2.0) * PI / ln
        wr = math.cos(ang)
        wi = math.sin(ang)
        for i in range(0, n, ln):
            cr = 1.0
            ci = 0.0
            for k in range(ln // 2):
                a = i + k
                b = a + ln // 2
                tr = re[b] * cr - im[b] * ci
                ti = re[b] * ci + im[b] * cr
                re[b] = re[a] - tr
                im[b] = im[a] - ti
                re[a] += tr
                im[a] += ti
                t = cr * wr - ci * wi
                ci = cr * wi + ci * wr
                cr = t
        ln <<= 1
    if inv:
        for i in range(n):
            re[i] /= n
            im[i] /= n


def _fd_vec(p: dict, N: int, E: float) -> list[float]:
    """Eigenvector of the finite-difference Hamiltonian at eigenvalue E by inverse iteration (three tridiagonal
    solves with the Thomas algorithm, shift just below E)."""
    h = 2.0 * p["L"] / (N + 1)
    off = -0.5 / (h * h)
    sh = E - 1e-7 * (1.0 + abs(E))
    dg = []
    v = []
    for i in range(N):
        x = -p["L"] + (i + 1) * h
        dg.append(1.0 / (h * h) + _sch_pot(p, x) - sh)
        v.append(1.0 + x)
    for _ in range(3):
        cp = [0.0] * N
        dp = [0.0] * N
        cp[0] = off / dg[0]
        dp[0] = v[0] / dg[0]
        for i in range(1, N):
            m = dg[i] - off * cp[i - 1]
            cp[i] = off / m
            dp[i] = (v[i] - off * dp[i - 1]) / m
        y = [0.0] * N
        y[N - 1] = dp[N - 1]
        for i in range(N - 2, -1, -1):
            y[i] = dp[i] - cp[i] * y[i + 1]
        s = 0.0
        for q in y:
            s += q * q
        s = math.sqrt(s)
        v = [q / s for q in y]
    return v


class PaSchro(_Base):
    """Units hbar = m = 1 (oscillator: omega = 1; hydrogen: atomic units, energies reported in eV).
    method 0 shooting: Numerov outward on n steps; the k-th eigenvalue is where the node count of psi jumps from k to
    k + 1 (bisection, 64 halvings). pot 0 oscillator V = x^2 / 2 (exact k + 1/2), 1 double well
    V = V0 ((x/a)^2 - 1)^2 (reference: finite differences on 1500 and 3000 points, Richardson-extrapolated),
    2 hydrogen radial u'' = (l(l+1)/r^2 - 2/r - 2E) u (exact -13.6057 / n^2 eV).
    method 1 split-step Fourier on the double well (128 grid points, n steps per unit time): the state
    (psi0 + psi1) / sqrt 2 (the left-localised doublet, from the 3000-point eigenvectors) is propagated with
    exp(-iV dt/2) exp(-iT dt) exp(-iV dt/2); the probability on the right rises as (1 - cos(dE t)) / 2 and the
    tunnelling time is that of its first maximum (a parabola through the top three samples). Reference pi / dE."""
    PARAMS = {"pot": 0.0, "k": 0.0, "L": 8.0, "V0": 4.0, "a": 1.5, "l": 0.0, "rmax": 60.0, "n": 400.0,
              "what": 0.0, "method": 0.0, "seed": 0.0}

    @staticmethod
    def init(p, cfg=None):
        if _i(p["method"]) == 1:
            return PaSchro._split(p)
        n = max(20, _i(p["n"]))
        k = _i(p["k"])
        E = _sch_shoot(p, n, k)
        val = E * HARTREE_EV if _i(p["pot"]) == 2 else E
        ex = _sch_exact(p)
        # the wave function at that energy, normalised to its largest value, and the potential for the plot
        cx, ce, cy = [], [], []
        hyd = _i(p["pot"]) == 2
        m = 200
        h = (p["rmax"] if hyd else 2.0 * p["L"]) / m
        x0 = 0.0 if hyd else -p["L"]
        l = _i(p["l"])
        h12 = h * h / 12.0
        ys = [0.0, math.pow(h, l + 1) if hyd else 1e-6]

        def f(x: float) -> float:
            if hyd:
                return l * (l + 1) / (x * x) - 2.0 / x - 2.0 * E
            return 2.0 * (_sch_pot(p, x) - E)

        for i in range(1, m):
            x1 = x0 + i * h
            x2 = x0 + (i + 1) * h
            fp = f(x0 + (i - 1) * h) if not (hyd and i == 1) else 0.0
            t0 = 0.0 if (hyd and i == 1) else (1.0 - h12 * fp) * ys[i - 1]
            ys.append((2.0 * (1.0 + 5.0 * h12 * f(x1)) * ys[i] - t0) / (1.0 - h12 * f(x2)))
        best = 0.0
        for i in range(m + 1):
            if abs(ys[i]) > best and i < m * 0.85:
                best = abs(ys[i])
        for i in range(m + 1):
            x = x0 + i * h
            cx.append(x)
            yv = ys[i] / best if best > 0 else 0.0
            cy.append(max(-1.5, min(1.5, yv)))
            if hyd:
                ce.append(max(-1.5, (l * (l + 1) / (x * x) - 2.0 / x) * 0.5 if x > 0 else -1.5))
            else:
                ce.append(min(1.5, _sch_pot(p, x) / max(abs(E), 1e-9) * 0.5))
        return _base(val, ex, n, cx, ce, cy, [], [], E=E)

    @staticmethod
    def _split(p):
        n = max(1, _i(p["n"]))
        N = 128
        L = p["L"]
        dx = 2.0 * L / N
        Nf = 3000
        e0 = _fd_eig(p, Nf, 0)
        e1 = _fd_eig(p, Nf, 1)
        v0 = _fd_vec(p, Nf, e0)
        v1 = _fd_vec(p, Nf, e1)
        hf = 2.0 * L / (Nf + 1)
        # left-localised doublet state on the 3000-point grid, sampled onto the 128-point grid (linear interpolation)
        n0 = 0.0
        n1 = 0.0
        for i in range(Nf):
            n0 += v0[i] * v0[i]
            n1 += v1[i] * v1[i]
        s0 = 1.0 / math.sqrt(n0)
        s1 = 1.0 / math.sqrt(n1)
        sgn = 1.0 if v1[Nf // 4] * v0[Nf // 4] > 0 else -1.0
        re, im, xs = [], [], []
        for j in range(N):
            x = -L + j * dx
            xs.append(x)
            q = (x + L) / hf - 1.0
            i0 = int(math.floor(q))
            fr = q - i0
            a = 0.0
            if 0 <= i0 < Nf - 1:
                a = (v0[i0] * s0 + sgn * v1[i0] * s1) * (1.0 - fr) + (v0[i0 + 1] * s0 + sgn * v1[i0 + 1] * s1) * fr
            re.append(a)
            im.append(0.0)
        nn = 0.0
        for j in range(N):
            nn += re[j] * re[j]
        nn = math.sqrt(nn)
        for j in range(N):
            re[j] /= nn
        dt = 1.0 / n
        tmax = 1.4 * PI / (e1 - e0)
        steps = int(tmax / dt) + 1
        vh_c, vh_s, kc, ks = [], [], [], []
        for j in range(N):
            a = -_sch_pot(p, xs[j]) * dt / 2.0
            vh_c.append(math.cos(a))
            vh_s.append(math.sin(a))
            kk = 2.0 * PI * (j if j < N // 2 else j - N) / (2.0 * L)
            b = -0.5 * kk * kk * dt
            kc.append(math.cos(b))
            ks.append(math.sin(b))

        def right() -> float:
            s = 0.0
            for j in range(N // 2, N):
                s += re[j] * re[j] + im[j] * im[j]
            return s

        tsr, prs = [0.0], [right()]
        for st in range(1, steps + 1):
            for j in range(N):
                r, q = re[j], im[j]
                re[j] = r * vh_c[j] - q * vh_s[j]
                im[j] = r * vh_s[j] + q * vh_c[j]
            _fft(re, im, False)
            for j in range(N):
                r, q = re[j], im[j]
                re[j] = r * kc[j] - q * ks[j]
                im[j] = r * ks[j] + q * kc[j]
            _fft(re, im, True)
            for j in range(N):
                r, q = re[j], im[j]
                re[j] = r * vh_c[j] - q * vh_s[j]
                im[j] = r * vh_s[j] + q * vh_c[j]
            tsr.append(st * dt)
            prs.append(right())
        kb = 0
        for i in range(len(prs)):
            if prs[i] > prs[kb]:
                kb = i
        T = tsr[kb]
        if 0 < kb < len(prs) - 1:
            a, b, c = prs[kb - 1], prs[kb], prs[kb + 1]
            den = a - 2.0 * b + c
            if den < 0:
                T = T + 0.5 * dt * (a - c) / den
        dE = e1 - e0
        ce = [0.5 * (1.0 - math.cos(dE * t)) for t in _thin(tsr, 300)]
        return _base(T, _sch_exact(p), steps, _thin(tsr, 300), ce, _thin(prs, 300), [], [], E=dE, steps=float(steps))


# ============================================================================================ wire chamber / drift tube
W_FE55 = 5900.0 / 26.0          # primary electron-ion pairs of a 5.9 keV Fe-55 photon in argon (W = 26 eV, from memory)


def _wire_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["vd"]
    if w == 2:
        return p["sres"]
    return p["dV"]


class PaWire(_Base):
    """what = 0: gas gain against voltage by the Fe-55 photopeak (227 primary pairs; per-event resolution res). The
    Diethorn law ln G = (V ln 2 / (ln(b/a) dV)) ln(V / (K a ln(b/a))) is a straight line of ln G ln(b/a) / V against
    ln(V / (a ln(b/a))): slope ln 2 / dV, intercept -(ln 2 / dV) ln K. what = 1: tracks cross the tube at an impact
    parameter spread uniformly over 0 - b; for a constant drift velocity the drift-time spectrum is flat and its mean
    is b / (2 vd) (timing jitter st). what = 2: three equally spaced planes; the middle hit's residual from the line
    through the outer two has variance 1.5 sigma^2. SIMULATED DATA. what 0 dV (V), 1 vd (cm/us), 2 sigma (um)."""
    PARAMS = {"a": 0.00125, "b": 1.0, "dV": 26.0, "K": 4.8e4, "Vmin": 1500.0, "Vmax": 1900.0, "nv": 9.0, "res": 0.085,
              "vd": 4.0, "st": 0.004, "sres": 150.0, "n": 2000.0, "what": 0.0, "method": 0.0, "seed": 149.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(10, _i(p["n"]))
        st = _lcg(p["seed"])
        w = _i(p["what"])
        lba = math.log(p["b"] / p["a"])
        if w == 1:
            ts = []
            s = 0.0
            for _ in range(n):
                r = p["b"] * _u(st)
                t = r / p["vd"] + p["st"] * _g(st)
                ts.append(t * 1000.0)
                s += t
            mt = s / n
            vd = p["b"] / (2.0 * mt)
            h = _hist(ts, -0.1 * p["b"] / p["vd"] * 1000.0, 1.2 * p["b"] / p["vd"] * 1000.0, 50)
            return _base(vd, _wire_exact(p), n, h[0], [], h[1], [], [], tmean=mt * 1000.0)
        if w == 2:
            rs = []
            v = 0.0
            for _ in range(n):
                x1 = p["sres"] * _g(st)
                x2 = p["sres"] * _g(st)
                x3 = p["sres"] * _g(st)
                r = x2 - 0.5 * (x1 + x3)
                rs.append(r)
                v += r * r
            sd = math.sqrt(v / n)
            sig = sd / math.sqrt(1.5)
            h = _hist(rs, -4.0 * sd, 4.0 * sd, 41)
            return _base(sig, _wire_exact(p), n, h[0], [], h[1], [], [], sres=sd)
        nv = max(3, _i(p["nv"]))
        xs, ys, Vs, Gs = [], [], [], []
        for k in range(nv):
            V = p["Vmin"] + (p["Vmax"] - p["Vmin"]) * k / (nv - 1)
            lnG = V * math.log(2.0) / (lba * p["dV"]) * math.log(V / (p["K"] * p["a"] * lba))
            G = math.exp(lnG)
            q = 0.0
            for _ in range(n):
                q += G * W_FE55 * (1.0 + p["res"] * _g(st))
            Gm = q / n / W_FE55
            xs.append(math.log(V / (p["a"] * lba)))
            ys.append(math.log(Gm) * lba / V)
            Vs.append(V)
            Gs.append(math.log10(Gm))
        ab = _line(xs, ys)
        dV = math.log(2.0) / ab[1] if ab[1] > 0 else 0.0
        Kf = math.exp(-ab[0] / ab[1]) if ab[1] > 0 else 0.0
        cy = []
        for V in Vs:
            x = math.log(V / (p["a"] * lba))
            cy.append((ab[0] + ab[1] * x) * V / lba / math.log(10.0))
        return _base(dV, _wire_exact(p), nv * n, Vs, [], cy, Vs, Gs, Kfit=Kf)


# ============================================================================================ silicon strip detector
MOYAL_MEAN = 0.5772156649015329 + math.log(2.0)      # mean of -ln(Z^2), Z standard normal: Euler's gamma + ln 2


def _si_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return p["mpv"] / p["noise"]
    if w == 2:
        return p["vdep"]
    return p["mpv"] / 1000.0


def _si_mom(st: list[float], mpv: float, wd: float, sn: float, n: int, qs: list | None) -> float:
    """n hits: Moyal deposit MPV + wd (-ln Z^2) plus electronic noise; the MPV back by the method of moments."""
    s = 0.0
    ss = 0.0
    for _ in range(n):
        z = _g(st)
        q = mpv + wd * (-math.log(z * z)) + sn * _g(st)
        if qs is not None:
            qs.append(q)
        s += q
        ss += q * q
    m = s / n
    var = ss / n - m * m
    v2 = var - sn * sn
    wf = math.sqrt(v2 / (PI * PI / 2.0)) if v2 > 0 else 0.0
    return m - MOYAL_MEAN * wf


class PaSi(_Base):
    """Minimum-ionising particles through a 300 um silicon strip: the deposit follows a Landau-like distribution,
    taken here as its Moyal approximation MPV + w (-ln Z^2) (Z standard normal, exactly a Moyal variate) plus
    Gaussian electronic noise. A pedestal run (no particle) gives the noise; the method of moments for a Moyal
    (mean = MPV + 1.2704 w, variance = (pi^2 / 2) w^2 + noise^2) gives the most probable value. The collected
    charge grows as sqrt(V / Vdep) below full depletion and is flat above; the points below the plateau give
    Vdep = V (Q_plateau / Q)^2. SIMULATED DATA. what 0 MPV (ke-), 1 signal-to-noise, 2 depletion voltage (V)."""
    PARAMS = {"mpv": 23000.0, "wd": 1500.0, "noise": 1000.0, "vdep": 65.0, "Vmin": 10.0, "Vmax": 150.0, "nv": 8.0,
              "n": 20000.0, "what": 0.0, "method": 0.0, "seed": 151.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(50, _i(p["n"]))
        st = _lcg(p["seed"])
        w = _i(p["what"])
        if w == 2:
            nv = max(3, _i(p["nv"]))
            Vs, Qs = [], []
            for k in range(nv):
                V = p["Vmin"] + (p["Vmax"] - p["Vmin"]) * k / (nv - 1)
                f = math.sqrt(min(V, p["vdep"]) / p["vdep"])
                Vs.append(V)
                Qs.append(_si_mom(st, p["mpv"] * f, p["wd"] * f, p["noise"], n, None) / 1000.0)
            top = 0.0
            for q in Qs:
                if q > top:
                    top = q
            pl = 0.0
            npl = 0
            for q in Qs:
                if q > 0.97 * top:
                    pl += q
                    npl += 1
            pl = pl / npl
            s = 0.0
            m = 0
            for k in range(nv):
                if Qs[k] < 0.9 * pl:
                    s += Vs[k] * (pl / Qs[k]) * (pl / Qs[k])
                    m += 1
            vd = s / m if m else 0.0
            cx, cy = [], []
            for k in range(41):
                V = p["Vmin"] + (p["Vmax"] - p["Vmin"]) * k / 40.0
                cx.append(V)
                cy.append(pl * math.sqrt(min(V, vd) / vd) if vd > 0 else pl)
            return _base(vd, _si_exact(p), nv * n, cx, [], cy, Vs, Qs, plateau=pl)
        ped = 0.0
        npd = max(20, n // 4)
        for _ in range(npd):
            e = p["noise"] * _g(st)
            ped += e * e
        sn = math.sqrt(ped / npd)
        qs = []
        mp = _si_mom(st, p["mpv"], p["wd"], sn, n, qs)
        val = mp / sn if w == 1 else mp / 1000.0
        h = _hist([q / 1000.0 for q in qs], 0.0, 3.0 * p["mpv"] / 1000.0, 60)
        return _base(val, _si_exact(p), n, h[0], [], h[1], [], [], mpvfit=mp, noisefit=sn)


KERNELS: dict[str, Any] = {"pa10_tof": PaTof, "pa10_zenith": PaZenith, "pa10_reldyn": PaReldyn,
                           "pa10_cher": PaCher, "pa10_sipm": PaSipm, "pa10_radio": PaRadio, "pa10_hubble": PaHubble,
                           "pa10_cmd": PaCmd, "pa10_lsp": PaLsp, "pa10_schro": PaSchro,
                           "pa10_wire": PaWire, "pa10_si": PaSi}
FAMILY = {k: "comp" for k in KERNELS}

TEXTBOOK = {"pa10_tof_v": _tof_exact, "pa10_zenith_v": _zen_exact, "pa10_reldyn_v": _rel_exact,
            "pa10_cher_v": _cher_exact, "pa10_sipm_v": _sipm_exact, "pa10_radio_v": _rad_exact,
            "pa10_hubble_v": _hub_exact, "pa10_cmd_v": _cmd_exact, "pa10_lsp_v": _lsp_exact,
            "pa10_schro_v": _sch_exact, "pa10_wire_v": _wire_exact, "pa10_si_v": _si_exact}


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
    """The answer of the run on the most data (the largest n): the truth is hidden, so the run with the most data
    is reported, not the one closest to a value nobody is shown."""
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
    "pa10_finest": {"label": "answer on the most data", "unit": "", "needs": ["n", "val"], "fn": _finest},
    "pa10_best": {"label": "best value", "unit": "", "needs": ["n", "val", "err"], "fn": _best},
}
