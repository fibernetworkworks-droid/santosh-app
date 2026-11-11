"""Kernel pack: B.Sc. "Computational physics" practicals, wave 8 (DU UGCF 2022 Mathematical Physics I / SEC 7 Scilab
and DU LOCF 2019 Quantum Mechanics, Statistical Mechanics, Applied Dynamics, Digital Signal Processing and Advanced
Mathematical Physics I labs).

Every kernel keeps the shape of the other computational packs so ONE workstation rig (`comp4-workstation`) serves them:

    PARAMS  cas (which problem), method, n (steps / samples / nodes / length) and the problem's own numbers
    init    runs the whole computation once and keeps the result
    step    advances a clock only
    view    val (the numerical answer), exact (the independent reference), err (|val-exact|/|exact|), nused, and the
            curves the monitor draws: cx / ce (the reference), cy (what the method built), px / py (points used)
    measure {val, exact, err, nused}

Kernels are named `cw8_*`; the EXACT JavaScript twin is `app/static/prayog/packs/ug_comp_w8.js` (same formulas, same
order of operations). Anything random is a seeded Lehmer generator (16807, mod 2^31 - 1), never the clock. The
molecular-dynamics kernel uses arithmetic and square roots only, so the two twins follow the same chaotic trajectory
bit for bit.

The reference ("exact") of each kernel, and how exact it is:
    cw8_fact     ln N! and ln C(N, K) by summing logarithms                                exact (to rounding)
    cw8_frame    the finite Galilean / Lorentz / rotation formula                            exact
    cw8_vfield   analytic gradient magnitude, divergence and curl                            exact
    cw8_group    d(omega)/dk of deep-water and capillary waves                               exact
    cw8_gfx      signed area |det A| pi r^2 and the moved centre A c + t                     exact
    cw8_anharm   3/2 h-bar omega (b = 0); a Rayleigh-Ritz oscillator-basis diagonalisation  exact / independent method
    cw8_ljmd     2-D Maxwell: <v>/v_rms = sqrt(pi)/2; equipartition 1; mean density N/A      statistical (model units)
    cw8_levels   heat capacity from the energy fluctuation; entropy (U - F)/T               exact
    cw8_maxwell  sqrt(8kT/pi m), sqrt(3kT/m), sqrt(2kT/m)                                    exact
    cw8_heatcap  3R; Einstein's formula; the Debye integral by its exponential series        exact
    cw8_qdist    Gamma-zeta ratios for the mean energy at mu = 0                             exact
    cw8_fractal  log 4 / log 3, log 3 / log 2, 3/2                                           exact limits (box counting)
    cw8_flow     closed-form pathline, streakline and streamline of a linear unsteady flow   exact
    cw8_game     the evolutionarily stable fraction V/C; the minimax mixed strategy          exact
    cw8_conv     the closed-form linear convolution of two geometric sequences              exact
    cw8_lti      |B/A| on the unit circle; H(1)                                               exact
    cw8_fir      the design cut-off frequency of the windowed-sinc filter                    exact (limit)
    cw8_geod     straight-line and great-circle distance                                     exact
    cw8_constr   4 sqrt(L/g) K(sin(theta0/2)) by the AGM; Atwood (m1-m2)g/(m1+m2); omega sin(theta0)  exact
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
_M = 2147483647
KB = 1.380649e-23            # J/K, exact (SI 2019)
NA = 6.02214076e23           # 1/mol, exact (SI 2019)
QE = 1.602176634e-19         # C, exact (SI 2019)


# ------------------------------------------------------------------------------------------------ shared helpers
def _i(v: float) -> int:
    return int(math.floor(v + 0.5))


def _err(val: float, exact: float) -> float:
    return abs(val - exact) / max(abs(exact), 1e-30)


def _grid(a: float, b: float, m: int) -> list[float]:
    return [a + (b - a) * i / m for i in range(m + 1)]


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


def _lcg(seed: float) -> list[float]:
    s = _i(seed) % _M
    return [float(s if s > 0 else 1)]


def _u(st: list[float]) -> float:
    st[0] = (st[0] * 16807.0) % _M
    return st[0] / _M


def _thin(xs: list[float], m: int) -> list[float]:
    """At most m + 1 evenly picked entries (always the first and the last): the monitor never draws more."""
    n = len(xs)
    if n <= m + 1:
        return list(xs)
    return [xs[_i(i * (n - 1) / m)] for i in range(m + 1)]


def _simpson(f, a: float, b: float, n: int) -> float:
    n = max(2, n - (n % 2))
    h = (b - a) / n
    s = f(a) + f(b)
    for i in range(1, n):
        s += (4.0 if i % 2 == 1 else 2.0) * f(a + h * i)
    return s * h / 3.0


def _sum(xs: list[float]) -> float:
    """A plain left-to-right sum (Python 3.12's sum() of floats is compensated; JavaScript's loop is not)."""
    s = 0.0
    for x in xs:
        s += x
    return s


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


# ============================================================================================ factorials, arrangements
def _lnfact(N: int) -> float:
    s = 0.0
    for k in range(2, N + 1):
        s += math.log(k)
    return s


def _stirling(N: int, meth: int) -> float:
    if N < 1:
        return 0.0
    v = N * math.log(N) - N
    if meth >= 1:
        v += 0.5 * math.log(2 * PI * N)
    if meth >= 2:
        v += 1.0 / (12.0 * N)
    return v


def _fact_K(p: dict, N: int) -> int:
    return max(0, min(N, _i(p["frac"] * N)))


def _fact_exact(p: dict) -> float:
    N = max(1, _i(p["n"]))
    if _i(p["cas"]) == 1:
        K = _fact_K(p, N)
        return _lnfact(N) - _lnfact(K) - _lnfact(N - K)
    return _lnfact(N)


class CwFact(_Base):
    """ln N! (cas 0) and the number of arrangements ln C(N, K) = ln [N! / (K! (N-K)!)] (cas 1) by Stirling's formula
    (method 0: N ln N - N; 1: + ln sqrt(2 pi N); 2: + 1/(12 N)), against the exact sum of logarithms."""
    PARAMS = {"cas": 0.0, "method": 1.0, "n": 20.0, "frac": 0.5}

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        N = max(1, _i(p["n"]))
        K = _fact_K(p, N)

        def approx(m):
            if cas == 1:
                return _stirling(m, meth) - _stirling(_fact_K(p, m), meth) - _stirling(m - _fact_K(p, m), meth)
            return _stirling(m, meth)

        def exact(m):
            if cas == 1:
                k2 = _fact_K(p, m)
                return _lnfact(m) - _lnfact(k2) - _lnfact(m - k2)
            return _lnfact(m)
        val = approx(N)
        ex = _fact_exact(p)
        ms = sorted(set([max(1, _i(1 + (N - 1) * i / 40.0)) for i in range(41)]))
        cx = [float(m) for m in ms]
        ce = [exact(m) for m in ms]
        cy = [approx(m) for m in ms]
        return _base(val, ex, N, cx, ce, cy, [float(N)], [val], K=float(K))


# ============================================================================================ frame transformations
def _frame_exact_at(p: dict, f: float) -> float:
    """The observable after a fraction f of the full transformation, from the finite formula."""
    cas = _i(p["cas"])
    if cas == 1:                                   # Lorentz: rapidities add, so u' = tanh(atanh u - f atanh v)
        return math.tanh(math.atanh(p["u"]) - f * math.atanh(p["v"]))
    if cas == 2:                                   # rotation of the axes by f theta: x' = x cos + y sin
        th = f * p["th"]
        return p["x"] * math.cos(th) + p["y"] * math.sin(th)
    return p["u"] - f * p["v"]                     # Galilean: velocities add


def _frame_exact(p: dict) -> float:
    return _frame_exact_at(p, 1.0)


class CwFrame(_Base):
    """A finite transformation built from n equal small steps X <- X + d G X (d = parameter / n), the way a
    generator builds a group element. cas 0 Galilean boost of a velocity (G nilpotent: exact for any n), cas 1 Lorentz
    boost of a 4-velocity (c = 1; error ~ 1/n^2), cas 2 rotation of the axes acting on a position (error ~ 1/n).
    The observable is u' (cas 0, 1) or x' (cas 2); the reference is the finite formula."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 16.0, "u": 0.6, "v": 0.5, "x": 1.0, "y": 0.5, "th": 0.8}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(1, _i(p["n"]))
        if cas == 2:
            a, b = p["x"], p["y"]
            d = p["th"] / n
        elif cas == 1:
            u = p["u"]
            g = 1.0 / math.sqrt(1.0 - u * u)
            a, b = g, g * u                        # (t, x) components of the 4-velocity
            d = math.atanh(p["v"]) / n
        else:
            a, b = 1.0, p["u"]
            d = p["v"] / n
        obs = []
        for k in range(n + 1):
            if cas == 2:
                obs.append(a)
            else:
                obs.append(b / a)
            if k == n:
                break
            if cas == 2:                           # x' = x + d y, y' = y - d x
                a, b = a + d * b, b - d * a
            elif cas == 1:                         # t' = t - d x, x' = x - d t
                a, b = a - d * b, b - d * a
            else:                                  # t' = t, x' = x - d t
                b = b - d * a
        val = obs[-1]
        ex = _frame_exact(p)
        idx = sorted(set([_i(n * i / 40.0) for i in range(41)]))
        cx = [k / n for k in idx]
        cy = [obs[k] for k in idx]
        ce = [_frame_exact_at(p, k / n) for k in idx]
        inv = a * a - b * b if cas == 1 else (a * a + b * b if cas == 2 else a)
        return _base(val, ex, n, cx, ce, cy, [], [], inv=inv)


# ============================================================================================ vector fields
def _vf_phi(x: float, y: float, z: float) -> float:
    return math.sin(x) * math.cos(y) * math.exp(z)


def _vf_F(x: float, y: float, z: float) -> list[float]:
    return [math.sin(x * y), math.cos(y * z), math.exp(x * z)]


def _vf_G(x: float, y: float, z: float) -> list[float]:
    return [-math.exp(x) * math.sin(y), y * math.sin(x), z * z]


def _vf_exact_at(cas: int, x: float, y: float, z: float) -> float:
    if cas == 1:                                   # div F
        return y * math.cos(x * y) - z * math.sin(y * z) + x * math.exp(x * z)
    if cas == 2:                                   # (curl G)_z = dGy/dx - dGx/dy
        return y * math.cos(x) + math.exp(x) * math.cos(y)
    gx = math.cos(x) * math.cos(y) * math.exp(z)
    gy = -math.sin(x) * math.sin(y) * math.exp(z)
    gz = math.sin(x) * math.cos(y) * math.exp(z)
    return math.sqrt(gx * gx + gy * gy + gz * gz)


def _vf_num_at(cas: int, meth: int, h: float, x: float, y: float, z: float) -> float:
    def d(fn, comp, axis):
        e = [0.0, 0.0, 0.0]
        e[axis] = h
        fp = fn(x + e[0], y + e[1], z + e[2])
        if meth == 1:                              # forward difference
            f0 = fn(x, y, z)
            return ((fp[comp] if comp >= 0 else fp) - (f0[comp] if comp >= 0 else f0)) / h
        fm = fn(x - e[0], y - e[1], z - e[2])      # central difference
        return ((fp[comp] if comp >= 0 else fp) - (fm[comp] if comp >= 0 else fm)) / (2 * h)
    if cas == 1:
        return d(_vf_F, 0, 0) + d(_vf_F, 1, 1) + d(_vf_F, 2, 2)
    if cas == 2:
        return d(_vf_G, 1, 0) - d(_vf_G, 0, 1)
    gx, gy, gz = d(_vf_phi, -1, 0), d(_vf_phi, -1, 1), d(_vf_phi, -1, 2)
    return math.sqrt(gx * gx + gy * gy + gz * gz)


def _vf_exact(p: dict) -> float:
    return _vf_exact_at(_i(p["cas"]), p["x0"], p["y0"], p["z0"])


class CwVfield(_Base):
    """Gradient magnitude |grad phi| of phi = sin x cos y e^z (cas 0), divergence of F = (sin xy, cos yz, e^xz)
    (cas 1) and the z component of the curl of G = (-e^x sin y, y sin x, z^2) (cas 2) at a point, by central (method 0)
    or forward (method 1) differences with step h = 1/n, against the analytic derivative."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 16.0, "x0": 0.7, "y0": 0.4, "z0": 0.3}

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(1, _i(p["n"]))
        h = 1.0 / n
        x0, y0, z0 = p["x0"], p["y0"], p["z0"]
        val = _vf_num_at(cas, meth, h, x0, y0, z0)
        ex = _vf_exact(p)
        cx = _grid(x0 - 1.0, x0 + 1.0, 40)
        ce = [_vf_exact_at(cas, x, y0, z0) for x in cx]
        cy = [_vf_num_at(cas, meth, h, x, y0, z0) for x in cx]
        px = [x0 - h, x0, x0 + h] if meth == 0 else [x0, x0 + h]
        py = [_vf_num_at(cas, meth, h, x, y0, z0) for x in px]
        # a 9 x 9 arrow field in the x-y plane through z0, for the picture in the corner
        arr = []
        for j in range(9):
            for i in range(9):
                xx, yy = x0 - 1.0 + i * 0.25, y0 - 1.0 + j * 0.25
                if cas == 1:
                    F = _vf_F(xx, yy, z0)
                    arr += [xx, yy, F[0], F[1]]
                elif cas == 2:
                    G = _vf_G(xx, yy, z0)
                    arr += [xx, yy, G[0], G[1]]
                else:
                    arr += [xx, yy, math.cos(xx) * math.cos(yy) * math.exp(z0), -math.sin(xx) * math.sin(yy) * math.exp(z0)]
        return _base(val, ex, n, cx, ce, cy, px, py, arrows=arr, h=h)


# ============================================================================================ wave groups and dispersion
def _gw_omega(cas: int, k: float, p: dict) -> float:
    if cas == 1:                                   # capillary waves: omega^2 = (sigma / rho) k^3  (anomalous)
        return math.sqrt(p["s"] * k * k * k)
    return math.sqrt(p["g"] * k)                   # deep-water gravity waves: omega^2 = g k     (normal)


def _gw_exact(p: dict) -> float:
    cas, k = _i(p["cas"]), p["k0"]
    if cas == 1:
        return 1.5 * math.sqrt(p["s"] * k)
    return 0.5 * math.sqrt(p["g"] / k)


class CwGroup(_Base):
    """Two waves of wave numbers k0 -+ dk/2 (dk = w k0 / n) superpose into a beat; the envelope's peak is located on
    a fine grid at time T (parabolic refinement of the largest |psi|^2) and the group velocity is its distance / T.
    The reference is d(omega)/dk at k0: deep water (normal dispersion, v_g = v_p/2) or capillary waves (anomalous
    dispersion, v_g = 3 v_p/2). Model units g = 1, sigma/rho = 1."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 4.0, "k0": 1.0, "w": 0.8, "T": 4.0, "g": 1.0, "s": 1.0}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(1, _i(p["n"]))
        k0, T = p["k0"], p["T"]
        dk = p["w"] * k0 / n
        k1, k2 = k0 - 0.5 * dk, k0 + 0.5 * dk
        w1, w2 = _gw_omega(cas, k1, p), _gw_omega(cas, k2, p)
        Lw = 2 * PI / dk                           # envelope period in x
        M = 2000
        best, bi, vals = -1.0, 0, []
        for i in range(M):
            x = Lw * i / M
            a1 = k1 * x - w1 * T
            a2 = k2 * x - w2 * T
            re = math.cos(a1) + math.cos(a2)
            im = math.sin(a1) + math.sin(a2)
            v = re * re + im * im
            vals.append(v)
            if v > best:
                best, bi = v, i
        ym, y0, yp = vals[(bi - 1) % M], vals[bi], vals[(bi + 1) % M]
        den = ym - 2 * y0 + yp
        off = 0.5 * (ym - yp) / den if abs(den) > 1e-300 else 0.0
        xpk = Lw * (bi + off) / M
        val = xpk / T
        ex = _gw_exact(p)
        vp = _gw_omega(cas, k0, p) / k0
        # the wave on the screen at time T over two envelope lengths of the exact group
        span = 2.0 * Lw
        cx = _grid(0.0, span, 300)
        cy, ce = [], []
        for x in cx:
            a1 = k1 * x - w1 * T
            a2 = k2 * x - w2 * T
            cy.append(math.cos(a1) + math.cos(a2))
            ce.append(2.0 * abs(math.cos(0.5 * (dk * x - (w2 - w1) * T))))
        return _base(val, ex, n, cx, ce, cy, [xpk], [2.0], vp=vp, dk=dk, Lw=Lw)


# ============================================================================================ graphics transformations
def _gfx_map(cas: int, p: dict, x: float, y: float) -> list[float]:
    if cas == 1:                                   # reflection in the line through the origin at angle al
        c, s = math.cos(2 * p["al"]), math.sin(2 * p["al"])
        return [c * x + s * y, s * x - c * y]
    if cas == 2:                                   # shear along x
        return [x + p["sh"] * y, y]
    if cas == 3:                                   # rotation about the origin
        c, s = math.cos(p["th"]), math.sin(p["th"])
        return [c * x - s * y, s * x + c * y]
    return [x + p["tx"], y + p["ty"]]              # translation


def _gfx_det(cas: int) -> float:
    return -1.0 if cas == 1 else 1.0


def _gfx_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if _i(p["what"]) == 1:                         # the centre of the figure, moved by the same map
        return _gfx_map(cas, p, p["cx0"], p["cy0"])[0]
    return _gfx_det(cas) * PI * p["r"] * p["r"]


class CwGfx(_Base):
    """A drawn object - a circle of radius r centred at (cx0, cy0), drawn as a regular n-gon - is translated (cas 0),
    reflected (1), sheared (2) or rotated (3) by mapping every vertex. The measured quantity is read off the moved
    drawing: its signed area by the shoelace formula (what 0; reference det(A) pi r^2, so a reflection flips the sign)
    or the x coordinate of its centroid (what 1; reference the map applied to the centre)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 24.0, "r": 1.0, "cx0": 1.5, "cy0": 0.5,
              "tx": 2.0, "ty": 1.0, "al": 0.5, "sh": 0.6, "th": 0.7}

    @staticmethod
    def init(p, cfg=None):
        cas, what = _i(p["cas"]), _i(p["what"])
        n = max(3, _i(p["n"]))
        xs, ys, ox, oy = [], [], [], []
        for k in range(n):
            a = 2 * PI * k / n
            x = p["cx0"] + p["r"] * math.cos(a)
            y = p["cy0"] + p["r"] * math.sin(a)
            q = _gfx_map(cas, p, x, y)
            ox.append(x)
            oy.append(y)
            xs.append(q[0])
            ys.append(q[1])
        A2, Cx = 0.0, 0.0
        for k in range(n):
            j = (k + 1) % n
            cr = xs[k] * ys[j] - xs[j] * ys[k]
            A2 += cr
            Cx += (xs[k] + xs[j]) * cr
        area = 0.5 * A2
        cxm = Cx / (3.0 * A2) if abs(A2) > 1e-300 else 0.0
        val = cxm if what == 1 else area
        ex = _gfx_exact(p)
        return _base(val, ex, n, ox + [ox[0]], oy + [oy[0]], [], xs + [xs[0]], ys + [ys[0]], area=area, cxm=cxm)


# ============================================================================================ anharmonic radial Schrodinger
def _ah_units(p: dict) -> list[float]:
    """h-bar omega (MeV), the length unit a (fm) and b in oscillator units, from m c^2, k and b in MeV / fm units."""
    hw = p["hbarc"] * math.sqrt(p["kk"] / p["mc2"])
    a = math.sqrt(math.sqrt(p["hbarc"] * p["hbarc"] / (p["mc2"] * p["kk"])))
    return [hw, a, p["bb"] * a * a * a / hw]


def _ah_V(r: float, bm: float) -> float:
    return 0.5 * r * r + bm * r * r * r / 3.0


def _ah_shoot(E: float, bm: float, h: float, N: int, keep: bool):
    """Numerov outward from u(0) = 0, u(h) = h for u'' = 2 (V - E) u; returns u at the last point (and u if keep)."""
    def q(r):
        return 2.0 * (E - _ah_V(r, bm))
    c = h * h / 12.0
    u0, u1 = 0.0, h
    us = [u0, u1] if keep else None
    f0, f1 = 1.0 + c * q(0.0), 1.0 + c * q(h)
    for i in range(1, N):
        r2 = (i + 1) * h
        f2 = 1.0 + c * q(r2)
        u2 = ((12.0 - 10.0 * f1) * u1 - f0 * u0) / f2
        u0, u1, f0, f1 = u1, u2, f1, f2
        if keep:
            us.append(u2)
        if abs(u1) > 1e250:
            break
    return u1, us


def _ah_numerov(p: dict, n: int):
    hw, a, bm = _ah_units(p)
    R = p["rmax"]
    h = R / n
    lo, hi = p["Elo"], p["Ehi"]
    slo = _ah_shoot(lo, bm, h, n, False)[0] > 0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if (_ah_shoot(mid, bm, h, n, False)[0] > 0) == slo:
            lo = mid
        else:
            hi = mid
    E = 0.5 * (lo + hi)
    us = _ah_shoot(E, bm, h, n, True)[1]
    # the wave function is trusted up to its last minimum of |u| (beyond it the round-off tail grows)
    cut = len(us) - 1
    pk = 0.0
    for v in us[: len(us) // 2]:
        pk = max(pk, abs(v))
    for i in range(len(us) // 2, len(us) - 1):
        if abs(us[i + 1]) > abs(us[i]) and abs(us[i]) < 1e-6 * pk:
            cut = i
            break
    s0, s2 = 0.0, 0.0
    for i in range(cut + 1):
        w = 0.5 if i == 0 or i == cut else 1.0
        r = i * h
        s0 += w * us[i] * us[i]
        s2 += w * us[i] * us[i] * r * r
    r2 = s2 / s0 if s0 > 0 else 0.0
    return E, r2, us, h, cut


def _jacobi(A: list[list[float]]) -> list[Any]:
    """Cyclic Jacobi eigen-decomposition of a small symmetric matrix: eigenvalues and the eigenvector columns."""
    n = len(A)
    a = [list(r) for r in A]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(60):
        off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                off += a[i][j] * a[i][j]
        if off < 1e-30:
            break
        for pi in range(n - 1):
            for qi in range(pi + 1, n):
                apq = a[pi][qi]
                if abs(apq) < 1e-300:
                    continue
                th = (a[qi][qi] - a[pi][pi]) / (2.0 * apq)
                t = (1.0 if th >= 0 else -1.0) / (abs(th) + math.sqrt(th * th + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][pi], a[k][qi]
                    a[k][pi] = c * akp - s * akq
                    a[k][qi] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[pi][k], a[qi][k]
                    a[pi][k] = c * apk - s * aqk
                    a[qi][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k][pi], V[k][qi]
                    V[k][pi] = c * vkp - s * vkq
                    V[k][qi] = s * vkp + c * vkq
    return [[a[i][i] for i in range(n)], V]


def _ah_ritz(p: dict) -> list[float]:
    """Independent reference: Rayleigh-Ritz in the lowest NB s-wave states of the 3-D oscillator,
    u_k(r) ~ r e^(-r^2/2) L_k^(1/2)(r^2), H_kl = (2k + 3/2) delta_kl + (b/3) <k|r^3|l>, integrals by the trapezoid
    rule on a fine grid (the integrands are smooth and decay as e^(-r^2), so the rule is exact to round-off)."""
    hw, a, bm = _ah_units(p)
    NB, G, R = 18, 1600, 9.0
    h = R / G
    rs = [i * h for i in range(G + 1)]
    B = []
    for k in range(NB):
        B.append([0.0] * (G + 1))
    for i, r in enumerate(rs):
        t = r * r
        L0, L1 = 1.0, 1.5 - t
        g = r * math.exp(-0.5 * t)
        B[0][i] = g * L0
        if NB > 1:
            B[1][i] = g * L1
        for k in range(1, NB - 1):
            L2 = ((2 * k + 1.5 - t) * L1 - (k + 0.5) * L0) / (k + 1)
            L0, L1 = L1, L2
            B[k + 1][i] = g * L1
    for k in range(NB):                            # normalise on the grid
        s = 0.0
        for i in range(G + 1):
            s += B[k][i] * B[k][i]
        nk = 1.0 / math.sqrt(s * h)
        for i in range(G + 1):
            B[k][i] *= nk
    H = [[0.0] * NB for _ in range(NB)]
    X2 = [[0.0] * NB for _ in range(NB)]
    r3 = [r * r * r for r in rs]
    r2 = [r * r for r in rs]
    for k in range(NB):
        for l in range(k, NB):
            s3, s2 = 0.0, 0.0
            for i in range(G + 1):
                w = B[k][i] * B[l][i]
                s3 += w * r3[i]
                s2 += w * r2[i]
            s3 *= h
            s2 *= h
            H[k][l] = H[l][k] = bm * s3 / 3.0 + ((2 * k + 1.5) if k == l else 0.0)
            X2[k][l] = X2[l][k] = s2
    ev, V = _jacobi(H)
    j0 = 0
    for j in range(NB):
        if ev[j] < ev[j0]:
            j0 = j
    c = [V[k][j0] for k in range(NB)]
    r2m = 0.0
    for k in range(NB):
        for l in range(NB):
            r2m += c[k] * X2[k][l] * c[l]
    return [ev[j0], r2m]


def _ah_exact(p: dict) -> float:
    hw, a, bm = _ah_units(p)
    what = _i(p["what"])
    if abs(bm) < 1e-15:                            # pure oscillator: E0 = 3/2 h-bar omega, <r^2> = 3/2 a^2
        return 1.5 * hw if what == 0 else 1.5 * a * a
    E, r2 = _ah_ritz(p)
    return E * hw if what == 0 else r2 * a * a


class CwAnharm(_Base):
    """s-wave radial equation u'' = (2m/h-bar^2)(V - E) u for V = k r^2 / 2 + b r^3 / 3 (the DU practical, m c^2 =
    940 MeV, k = 100 MeV fm^-2), solved in oscillator units by Numerov shooting on n grid steps with bisection on E.
    what 0: the ground-state energy (MeV); what 1: <r^2> of the ground-state wave function (fm^2). Reference: the exact
    3/2 h-bar omega for b = 0, and an independent Rayleigh-Ritz diagonalisation for b > 0."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 200.0, "hbarc": 197.3269804, "mc2": 940.0, "kk": 100.0,
              "bb": 0.0, "rmax": 7.0, "Elo": 0.5, "Ehi": 3.0}

    @staticmethod
    def init(p, cfg=None):
        what = _i(p["what"])
        n = max(8, _i(p["n"]))
        hw, a, bm = _ah_units(p)
        E, r2, us, h, cut = _ah_numerov(p, n)
        val = E * hw if what == 0 else r2 * a * a
        ex = _ah_exact(p)
        idx = sorted(set([_i(cut * i / 60.0) for i in range(61)]))
        mx = max(abs(v) for v in us[: cut + 1]) or 1.0
        cx = [i * h * a for i in idx]
        cy = [us[i] / mx for i in idx]
        ce = [_ah_V(i * h, bm) for i in idx]
        return _base(val, ex, n, cx, [], cy, [], [], Vr=ce, E=E, hw=hw, a=a, bm=bm)


# ============================================================================================ Lennard-Jones molecular dynamics
def _lj_forces(X: list[float], Y: list[float], L: float, rc2: float, FX: list[float], FY: list[float]) -> float:
    """Pair forces of the truncated and shifted 12-6 potential (reduced units, eps = sigma = m = 1), minimum image."""
    N = len(X)
    for i in range(N):
        FX[i] = 0.0
        FY[i] = 0.0
    ic2 = 1.0 / rc2
    ic6 = ic2 * ic2 * ic2
    shift = 4.0 * (ic6 * ic6 - ic6)
    hL = 0.5 * L
    pe = 0.0
    for i in range(N - 1):
        xi, yi = X[i], Y[i]
        for j in range(i + 1, N):
            dx = xi - X[j]
            dy = yi - Y[j]
            if dx > hL:
                dx -= L
            elif dx < -hL:
                dx += L
            if dy > hL:
                dy -= L
            elif dy < -hL:
                dy += L
            r2 = dx * dx + dy * dy
            if r2 < rc2:
                i2 = 1.0 / r2
                i6 = i2 * i2 * i2
                f = 24.0 * i2 * i6 * (2.0 * i6 - 1.0)
                FX[i] += f * dx
                FY[i] += f * dy
                FX[j] -= f * dx
                FY[j] -= f * dy
                pe += 4.0 * (i6 * i6 - i6) - shift
    return pe


def _lj_run(p: dict, n: int) -> dict:
    side = max(2, _i(p["side"]))
    N = side * side
    L = math.sqrt(N / p["rho"])
    dt = p["dt"]
    rc2 = p["rc"] * p["rc"]
    what = _i(p["what"])
    st = _lcg(p["seed"])
    X, Y, VX, VY = [], [], [], []
    a = L / side
    for j in range(side):
        for i in range(side):
            X.append((i + 0.5) * a)
            Y.append((j + 0.5) * a)
            VX.append(2.0 * _u(st) - 1.0)
            vy = 2.0 * _u(st) - 1.0
            VY.append(0.0 if what == 1 else vy)   # approach to equilibrium: start with every velocity along x
    mx = _sum(VX) / N
    my = _sum(VY) / N
    ke = 0.0
    for i in range(N):
        VX[i] -= mx
        VY[i] -= my
        ke += VX[i] * VX[i] + VY[i] * VY[i]
    sc = math.sqrt(2.0 * (N - 1) * p["T0"] / ke)   # kinetic temperature T0 (2 N - 2 degrees of freedom)
    for i in range(N):
        VX[i] *= sc
        VY[i] *= sc
    FX, FY = [0.0] * N, [0.0] * N
    _lj_forces(X, Y, L, rc2, FX, FY)
    neq = max(0, _i(p["neq"]))
    total = neq + n
    sv, sv2, sx2, sy2, cnt, cnt2, ns = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    hl, sub = 0.5 * L, 0.0
    trace_t, trace_y, e0, e1 = [], [], 0.0, 0.0
    every = max(1, total // 60)
    for step in range(total):
        hdt = 0.5 * dt
        for i in range(N):
            VX[i] += hdt * FX[i]
            VY[i] += hdt * FY[i]
            X[i] += dt * VX[i]
            Y[i] += dt * VY[i]
            if X[i] >= L:
                X[i] -= L
            elif X[i] < 0.0:
                X[i] += L
            if Y[i] >= L:
                Y[i] -= L
            elif Y[i] < 0.0:
                Y[i] += L
        pe = _lj_forces(X, Y, L, rc2, FX, FY)
        kx, ky = 0.0, 0.0
        for i in range(N):
            VX[i] += hdt * FX[i]
            VY[i] += hdt * FY[i]
            kx += VX[i] * VX[i]
            ky += VY[i] * VY[i]
        if step == 0:
            e0 = 0.5 * (kx + ky) + pe
        e1 = 0.5 * (kx + ky) + pe
        if step >= neq:
            ns += 1.0
            sx2 += kx
            sy2 += ky
            c = 0.0
            for i in range(N):
                v2 = VX[i] * VX[i] + VY[i] * VY[i]
                sv += math.sqrt(v2)
                sv2 += v2
                if X[i] < hl:
                    c += 1.0
            cnt += c
            cnt2 += c * c
        if step % every == 0:
            trace_t.append((step + 1) * dt)
            if what == 1:
                trace_y.append(ky / kx if kx > 0 else 0.0)
            elif what == 2:
                trace_y.append(cnt / max(ns, 1.0) / (hl * L) if ns > 0 else 0.0)
            else:
                trace_y.append((sv / (ns * N)) / math.sqrt(sv2 / (ns * N)) if ns > 0 else 0.0)
    out = {"N": float(N), "L": L, "ns": ns, "e0": e0, "e1": e1, "tt": trace_t, "ty": trace_y,
           "X": list(X), "Y": list(Y)}
    if what == 1:
        out["val"] = sy2 / sx2 if sx2 > 0 else 0.0
    elif what == 2:
        m = cnt / ns
        out["val"] = m / (hl * L)
        out["fano"] = (cnt2 / ns - m * m) / m if m > 0 else 0.0
    else:
        out["val"] = (sv / (ns * N)) / math.sqrt(sv2 / (ns * N))
    out["Tk"] = (sx2 + sy2) / (ns * (2.0 * N - 2.0)) if ns > 0 else 0.0
    return out


def _lj_exact(p: dict) -> float:
    w = _i(p["what"])
    if w == 1:
        return 1.0
    if w == 2:
        return p["rho"]
    return 0.5 * math.sqrt(PI)


class CwLjmd(_Base):
    """N = side^2 Lennard-Jones particles in a periodic 2-D box (reduced units: eps = sigma = m = kB = 1, potential
    truncated and shifted at rc), velocity Verlet with time step dt, averaged over n steps after neq steps. what 0:
    <|v|> / sqrt(<v^2>) against the 2-D Maxwell value sqrt(pi)/2 (independent of T); what 1: equipartition
    <v_y^2>/<v_x^2> -> 1 for a start with every velocity along x; what 2: the mean local number density in one quarter
    of the box against N / L^2. Model (reduced) units throughout; the averages are statistical."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 400.0, "side": 6.0, "rho": 0.25, "T0": 1.0,
              "dt": 0.005, "rc": 2.5, "neq": 200.0, "seed": 2024.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(1, _i(p["n"]))
        o = _lj_run(p, n)
        ex = _lj_exact(p)
        pts = []
        for i in range(len(o["X"])):
            pts += [o["X"][i] / o["L"], o["Y"][i] / o["L"]]
        return _base(o["val"], ex, n, o["tt"], [ex for _ in o["tt"]], o["ty"], [], [],
                     pts=pts, Tk=o["Tk"], drift=(o["e1"] - o["e0"]) / max(abs(o["e0"]), 1e-12), fano=o.get("fano", 0.0),
                     Np=o["N"], Lbox=o["L"])


# ============================================================================================ few-level partition functions
def _lv_states(p: dict) -> list[list[float]]:
    """Two particles on L equally spaced levels e_j = j eps: every two-particle state as [energy, weight]."""
    L = max(2, _i(p["L"]))
    st = _i(p["cas"])
    out = []
    for j in range(L):
        for k in range(L):
            if st == 1 and k <= j:                 # Fermi-Dirac: different levels, each pair once
                continue
            if st == 2 and k < j:                  # Bose-Einstein: each pair once, both on one level allowed
                continue
            out.append([(j + k) * p["eps"], 1.0])
    return out


def _lv_thermo(p: dict, T: float) -> list[float]:
    """[Z, U, <E^2>, F] at temperature T (kB = 1); energies measured from the lowest state for stability."""
    ss = _lv_states(p)
    e0 = min(s[0] for s in ss)
    Z, S1, S2 = 0.0, 0.0, 0.0
    for e, g in ss:
        w = g * math.exp(-(e - e0) / T)
        Z += w
        S1 += w * e
        S2 += w * e * e
    U = S1 / Z
    return [Z, U, S2 / Z, e0 - T * math.log(Z)]


def _lv_exact(p: dict) -> float:
    T = p["T"]
    Z, U, E2, F = _lv_thermo(p, T)
    if _i(p["what"]) == 1:
        return (U - F) / T                         # S = (U - F) / T
    return (E2 - U * U) / (T * T)                  # C = (<E^2> - <E>^2) / (kB T^2)


class CwLevels(_Base):
    """Two particles on L equally spaced levels (spacing eps, kB = 1): Maxwell-Boltzmann (distinguishable, cas 0),
    Fermi-Dirac (cas 1) or Bose-Einstein (cas 2) counting of the states. The partition function Z(T) is summed over
    the states; the heat capacity is found as dU/dT (what 0) and the entropy as -dF/dT (what 1) by central (method 0)
    or forward (method 1) differences with step h = T / n. The reference is the same quantity from the fluctuation
    formula C = (<E^2> - <E>^2)/T^2 or from S = (U - F)/T, which need no derivative."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 8.0, "L": 3.0, "eps": 1.0, "T": 0.8}

    @staticmethod
    def init(p, cfg=None):
        meth, what = _i(p["method"]), _i(p["what"])
        n = max(1, _i(p["n"]))
        T = p["T"]

        def q(t):                                  # the function that is differentiated: U (what 0) or -F (what 1)
            th = _lv_thermo(p, t)
            return th[1] if what == 0 else -th[3]

        def deriv(t, h):
            if meth == 1:
                return (q(t + h) - q(t)) / h
            return (q(t + h) - q(t - h)) / (2 * h)
        h = T / n
        val = deriv(T, h)
        ex = _lv_exact(p)
        cx = _grid(0.1 * T, 3.0 * T, 50)
        ce, cy = [], []
        for t in cx:
            Z, U, E2, F = _lv_thermo(p, t)
            ce.append((U - F) / t if what == 1 else (E2 - U * U) / (t * t))
            cy.append(deriv(t, t / n))
        Z = _lv_thermo(p, T)[0]
        return _base(val, ex, n, cx, ce, cy, [T], [val], Z=Z, nstates=float(len(_lv_states(p))))


# ============================================================================================ Maxwell speed distribution
def _mx_m(p: dict) -> float:
    return p["M"] * 1e-3 / NA                     # molecular mass, kg


def _mx_f(v: float, p: dict) -> float:
    m, T = _mx_m(p), p["T"]
    a = m / (2 * KB * T)
    return 4 * PI * math.pow(a / PI, 1.5) * v * v * math.exp(-a * v * v)


def _mx_exact(p: dict) -> float:
    m, T = _mx_m(p), p["T"]
    w = _i(p["what"])
    if w == 1:
        return math.sqrt(3 * KB * T / m)
    if w == 2:
        return math.sqrt(2 * KB * T / m)
    return math.sqrt(8 * KB * T / (PI * m))


class CwMaxwell(_Base):
    """The Maxwell speed distribution f(v) = 4 pi (m / 2 pi kT)^(3/2) v^2 e^(-m v^2 / 2kT) of a real gas (molar mass
    M, temperature T; kB and NA exact SI values) on n intervals of [0, 6 v_p]: the mean speed (what 0) and the rms
    speed (what 1) by Simpson's rule, the most probable speed (what 2) as the peak of the tabulated f refined by a
    parabola through the three largest samples. References: sqrt(8kT/pi m), sqrt(3kT/m), sqrt(2kT/m)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 16.0, "M": 28.0134, "T": 300.0}

    @staticmethod
    def init(p, cfg=None):
        w = _i(p["what"])
        n = max(2, _i(p["n"]))
        vp = math.sqrt(2 * KB * p["T"] / _mx_m(p))
        vmax = 6.0 * vp
        if w == 2:
            h = vmax / n
            fs = [_mx_f(h * i, p) for i in range(n + 1)]
            bi = 0
            for i in range(n + 1):
                if fs[i] > fs[bi]:
                    bi = i
            bi = max(1, min(n - 1, bi))
            den = fs[bi - 1] - 2 * fs[bi] + fs[bi + 1]
            off = 0.5 * (fs[bi - 1] - fs[bi + 1]) / den if abs(den) > 1e-300 else 0.0
            val = h * (bi + off)
            px = [h * i for i in range(n + 1)]
            py = fs
        else:
            k = 2 if w == 1 else 1
            I = _simpson(lambda v: math.pow(v, k) * _mx_f(v, p), 0.0, vmax, n)
            val = math.sqrt(I) if w == 1 else I
            nn = max(2, n - (n % 2))
            px = [vmax * i / nn for i in range(nn + 1)]
            py = [_mx_f(v, p) for v in px]
        ex = _mx_exact(p)
        cx = _grid(0.0, vmax, 80)
        ce = [_mx_f(v, p) for v in cx]
        return _base(val, ex, n, cx, ce, [], _thin(px, 80), _thin(py, 80), vline=ex, vfound=val)


# ============================================================================================ specific heat of solids
R_GAS = NA * KB                                    # 8.314462618... J/(mol K), exact from the SI constants


def _debye_J4(x: float) -> float:
    """Integral_0^x t^4 e^t / (e^t - 1)^2 dt = -x^4/(e^x - 1) + 4 Integral_0^x t^3/(e^t - 1) dt, the last by its
    exponential series pi^4/15 - sum_k e^(-kx) (x^3/k + 3x^2/k^2 + 6x/k^3 + 6/k^4): no quadrature anywhere."""
    s = 0.0
    k = 1
    while k < 20000:
        e = math.exp(-k * x)
        term = e * (x * x * x / k + 3 * x * x / (k * k) + 6 * x / (k * k * k) + 6.0 / (k * k * k * k))
        s += term
        if term < 1e-18 * (PI ** 4 / 15.0) and k > 3:
            break
        k += 1
    J3 = PI ** 4 / 15.0 - s
    return -x ** 4 / math.expm1(x) + 4 * J3


def _hc_einstein_U(T: float, th: float) -> float:
    return 3 * R_GAS * th / math.expm1(th / T)


def _hc_exact(p: dict) -> float:
    meth = _i(p["method"])
    T = p["T"]
    if meth == 1:
        th = p["thE"]
        x = th / T
        return 3 * R_GAS * x * x * math.exp(x) / (math.expm1(x) * math.expm1(x))
    if meth == 2:
        x = p["thD"] / T
        return 9 * R_GAS * _debye_J4(x) / (x * x * x)
    return 3 * R_GAS


def _debye_integrand(t: float) -> float:
    if t == 0.0:
        return 0.0
    em = math.expm1(t)
    return t ** 4 * math.exp(t) / (em * em)


class CwHeatcap(_Base):
    """Molar heat capacity of a solid at temperature T by three models. Dulong-Petit (method 0) and Einstein (method 1):
    C = dU/dT by a central difference of the model's energy (U = 3RT; U = 3R thE / (e^(thE/T) - 1)) with h = T/n.
    Debye (method 2): C = 9R (T/thD)^3 Integral_0^(thD/T) t^4 e^t/(e^t-1)^2 dt by Simpson's rule on n intervals.
    References: 3R; Einstein's closed formula; the Debye integral by its exponential series (no quadrature)."""
    PARAMS = {"cas": 0.0, "method": 2.0, "n": 8.0, "T": 100.0, "thD": 343.0, "thE": 265.7}

    @staticmethod
    def init(p, cfg=None):
        meth = _i(p["method"])
        n = max(2, _i(p["n"]))

        def C_num(T):
            h = T / n
            if meth == 0:
                return (3 * R_GAS * (T + h) - 3 * R_GAS * (T - h)) / (2 * h)
            if meth == 1:
                return (_hc_einstein_U(T + h, p["thE"]) - _hc_einstein_U(T - h, p["thE"])) / (2 * h)
            x = p["thD"] / T
            return 9 * R_GAS * _simpson(_debye_integrand, 0.0, x, n) / (x * x * x)

        def C_ex(T):
            q = dict(p)
            q["T"] = T
            return _hc_exact(q)
        T = p["T"]
        val = C_num(T)
        ex = _hc_exact(p)
        top = max(p["thD"], p["thE"]) * 1.5
        cx = _grid(0.04 * top, top, 50)
        ce = [C_ex(t) for t in cx]
        cy = [C_num(t) for t in cx]
        return _base(val, ex, n, cx, ce, cy, [T], [val], R=R_GAS)


# ============================================================================================ quantum distributions
def _zeta(s: float) -> float:
    """Riemann zeta(s), s > 1, by Euler-Maclaurin: 20 terms summed, the tail by its integral and four Bernoulli terms."""
    N = 20
    tot = 0.0
    for k in range(1, N):
        tot += math.pow(k, -s)
    tot += math.pow(N, 1 - s) / (s - 1) + 0.5 * math.pow(N, -s)
    B = [1.0 / 6, -1.0 / 30, 1.0 / 42, -1.0 / 30]
    fac, poch = 1.0, s
    for j in range(4):
        k2 = 2 * (j + 1)
        fac *= (k2 - 1) * k2
        tot += B[j] / fac * poch * math.pow(N, -s - k2 + 1)
        poch *= (s + k2 - 1) * (s + k2)
    return tot


def _qd_a(p: dict) -> float:
    return 2.0 if _i(p["cas"]) == 1 else 0.5      # density of states ~ e^a: a = 1/2 (non-relativistic), 2 (ultra-relativistic)


def _qd_ratio(meth: int, a: float) -> float:
    """<E>/kT at mu = 0: Gamma(a+2) X(a+2) / (Gamma(a+1) X(a+1)) with X = 1 (MB), eta (FD), zeta (BE)."""
    if meth == 0:
        return a + 1.0
    def X(s):
        z = _zeta(s)
        return (1.0 - math.pow(2.0, 1.0 - s)) * z if meth == 1 else z
    return (a + 1.0) * X(a + 2.0) / X(a + 1.0)


def _qd_kT(p: dict) -> float:
    return KB * p["T"] / QE                       # kT in eV


def _qd_exact(p: dict) -> float:
    return _qd_ratio(_i(p["method"]), _qd_a(p)) * _qd_kT(p)


def _qd_occ(meth: int, x: float) -> float:
    if meth == 1:
        return 1.0 / (math.exp(x) + 1.0)
    if meth == 2:
        return 1.0 / math.expm1(x) if x > 0 else 0.0
    return math.exp(-x)


def _qd_int(meth: int, a: float, n: int) -> float:
    """Integral_0^inf x^a f(x) dx with x = t^2 (so the Bose 1/x end is smooth): Simpson on t in [0, 7], n intervals."""
    def g(t):
        if t == 0.0:
            if meth == 2 and abs(2 * a - 1) < 1e-12:   # 2 t^(2a+1) / (e^(t^2) - 1) -> 2 t^(2a-1) -> 2 for a = 1/2
                return 2.0
            return 0.0
        x = t * t
        return 2.0 * math.pow(t, 2 * a + 1) * _qd_occ(meth, x)
    return _simpson(g, 0.0, 7.0, n)


class CwQdist(_Base):
    """Mean energy per particle of an ideal gas at chemical potential mu = 0, <E> = Int E g(E) f(E) dE / Int g(E) f(E)
    dE, with g ~ E^(1/2) (non-relativistic, cas 0) or E^2 (ultra-relativistic, cas 1) and f the Maxwell-Boltzmann
    (method 0), Fermi-Dirac (1) or Bose-Einstein (2) occupation; both integrals by Simpson's rule on n intervals (after
    E = kT t^2). Reference: <E>/kT = (a+1) X(a+2)/X(a+1) with X = 1, the eta or the zeta function (computed by series).
    Bose-Einstein ultra-relativistic with mu = 0 is black-body radiation: <E> = 2.701 kT."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 16.0, "T": 300.0}

    @staticmethod
    def init(p, cfg=None):
        meth = _i(p["method"])
        n = max(2, _i(p["n"]))
        a = _qd_a(p)
        kT = _qd_kT(p)
        val = _qd_int(meth, a + 1.0, n) / _qd_int(meth, a, n) * kT
        ex = _qd_exact(p)
        cx = _grid(0.0, 8.0, 80)                   # the occupation of the three statistics against E / kT
        ce = [_qd_occ(meth, x) if x > 0 or meth != 2 else 0.0 for x in cx]
        cy = [_qd_occ(0, x) for x in cx]
        cy2 = [_qd_occ(1, x) for x in cx]
        return _base(val, ex, n, cx, ce, cy, [], [], cy2=cy2, kT=kT, ratio=val / kT)


# ============================================================================================ fractals
_FR_V = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]


def _fr_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    sx = _sum(xs)
    sy = _sum(ys)
    sxx = 0.0
    sxy = 0.0
    for i in range(n):
        sxx += xs[i] * xs[i]
        sxy += xs[i] * ys[i]
    den = n * sxx - sx * sx
    return (n * sxy - sx * sy) / den if abs(den) > 1e-300 else 0.0


def _fr_boxes(X: list[float], Y: list[float], k: int) -> int:
    e = float(2 ** k)
    seen = set()
    for i in range(len(X)):
        seen.add(int(math.floor(X[i] * e)) * 4096 + int(math.floor(Y[i] * e)))
    return len(seen)


def _fr_exact(p: dict) -> float:
    if _i(p["cas"]) == 2:
        return 1.5
    return math.log(3.0) / math.log(2.0)


class CwFractal(_Base):
    """Fractal dimension, measured. cas 0 (deterministic): the Sierpinski triangle built by n rounds of exact
    subdivision, box-counted with boxes 2^-k (k = 1..kmax); cas 1 (self-similar, random): the same set from the chaos
    game with n points; cas 2 (a fractal in nature): a rough random-walk profile of n steps, its Hurst exponent H from
    the variogram sqrt(<(y(i+t) - y(i))^2>) ~ t^H over lags 1..32, and the profile's dimension D = 2 - H.
    References: log 3 / log 2 (Sierpinski) and 3/2 (Brownian profile, H = 1/2)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 6.0, "kmax": 6.0, "seed": 4242.0}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(1, _i(p["n"]))
        kmax = max(2, _i(p["kmax"]))
        X, Y = [], []
        if cas == 2:
            st = _lcg(p["seed"])
            S = 0.0
            ys = [0.0]
            for i in range(n):
                S += 1.0 if _u(st) < 0.5 else -1.0
                ys.append(S)
            lags = [1, 2, 4, 8, 16, 32]
            lx, ly = [], []
            for t in lags:
                s, c = 0.0, 0
                for i in range(0, n - t + 1):
                    d = ys[i + t] - ys[i]
                    s += d * d
                    c += 1
                lx.append(math.log(float(t)))
                ly.append(math.log(math.sqrt(s / c)) if c > 0 and s > 0 else 0.0)
            H = _fr_slope(lx, ly)
            val = 2.0 - H
            prof = _thin(ys, 400)
            px = [i / max(1, len(prof) - 1) for i in range(len(prof))]
            return _base(val, _fr_exact(p), n, lx, [ly[0] + 0.5 * (x - lx[0]) for x in lx], ly, lx, ly,
                         H=H, path_x=px, path_y=prof)
        if cas == 1:
            st = _lcg(p["seed"])
            x, y = 1.0 / 3.0, 1.0 / 3.0
            for i in range(n + 20):
                r = _u(st)
                j = 0 if r < 1.0 / 3.0 else (1 if r < 2.0 / 3.0 else 2)
                x = 0.5 * (x + _FR_V[j][0])
                y = 0.5 * (y + _FR_V[j][1])
                if i >= 20:
                    X.append(x)
                    Y.append(y)
        else:
            X, Y = [1.0 / 3.0], [1.0 / 3.0]
            for _ in range(min(n, 9)):
                X2, Y2 = [], []
                for i in range(len(X)):
                    for v in _FR_V:
                        X2.append(0.5 * (X[i] + v[0]))
                        Y2.append(0.5 * (Y[i] + v[1]))
                X, Y = X2, Y2
        lx, ly = [], []
        for k in range(1, kmax + 1):
            lx.append(k * math.log(2.0))
            ly.append(math.log(float(_fr_boxes(X, Y, k))))
        val = _fr_slope(lx, ly)
        ex = _fr_exact(p)
        pts = []
        step = max(1, len(X) // 1500)
        for i in range(0, len(X), step):
            pts += [X[i], Y[i]]
        return _base(val, ex, n, lx, [ly[0] + ex * (x - lx[0]) for x in lx], ly, lx, ly, pts=pts)


# ============================================================================================ flow visualisation
def _fl_vel(p: dict, x: float, y: float, t: float) -> list[float]:
    return [p["a"] * x, -p["a"] * y + p["b"] * math.cos(p["w"] * t)]


def _fl_yp(p: dict, t: float) -> float:
    a, b, w = p["a"], p["b"], p["w"]
    return b / (a * a + w * w) * (a * math.cos(w * t) + w * math.sin(w * t))


def _fl_path_exact(p: dict, t0: float, t1: float) -> list[float]:
    """Exact position at t1 of the fluid particle at (x0, y0) at time t0."""
    a = p["a"]
    x = p["x0"] * math.exp(a * (t1 - t0))
    y = _fl_yp(p, t1) + (p["y0"] - _fl_yp(p, t0)) * math.exp(-a * (t1 - t0))
    return [x, y]


def _fl_stream_exact(p: dict, s: float) -> list[float]:
    """Exact streamline of the frozen field at time T through (x0, y0), at parameter s."""
    a = p["a"]
    c = p["b"] * math.cos(p["w"] * p["T"]) / a
    return [p["x0"] * math.exp(a * s), c + (p["y0"] - c) * math.exp(-a * s)]


def _fl_rk4(p: dict, x: float, y: float, t: float, h: float, steps: int, frozen: bool) -> list[Any]:
    tr = [[x, y]]
    tf = p["T"]
    for _ in range(steps):
        def f(xx, yy, tt):
            return _fl_vel(p, xx, yy, tf if frozen else tt)
        k1 = f(x, y, t)
        k2 = f(x + 0.5 * h * k1[0], y + 0.5 * h * k1[1], t + 0.5 * h)
        k3 = f(x + 0.5 * h * k2[0], y + 0.5 * h * k2[1], t + 0.5 * h)
        k4 = f(x + h * k3[0], y + h * k3[1], t + h)
        x += h * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6.0
        y += h * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6.0
        t += h
        tr.append([x, y])
    return tr


def _fl_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if cas == 2:
        return _fl_stream_exact(p, p["S"])[1]
    if cas == 1:
        return _fl_path_exact(p, p["tau"], p["T"])[1]
    return _fl_path_exact(p, 0.0, p["T"])[1]


class CwFlow(_Base):
    """The unsteady linear flow u = a x, v = -a y + b cos(w t). cas 0: the PATHLINE of the particle at (x0, y0) at
    t = 0, followed to t = T; cas 1: the STREAKLINE at time T of dye released at (x0, y0) - the particle released at
    t = tau is followed; cas 2: the STREAMLINE through (x0, y0) of the frozen field at t = T, followed to parameter S.
    Each by fourth-order Runge-Kutta in n steps; the quantity is y at the end, against the closed-form solution of the
    same linear equations."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "a": 0.3, "b": 1.0, "w": 2.0, "x0": 0.5, "y0": 0.0,
              "T": 3.0, "tau": 1.0, "S": 3.0}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(1, _i(p["n"]))
        if cas == 2:
            tr = _fl_rk4(p, p["x0"], p["y0"], 0.0, p["S"] / n, n, True)
            ex_tr = [_fl_stream_exact(p, p["S"] * k / 60.0) for k in range(61)]
        elif cas == 1:
            tr = _fl_rk4(p, p["x0"], p["y0"], p["tau"], (p["T"] - p["tau"]) / n, n, False)
            # the whole exact streak at time T: particles released at every tau' in [0, T]
            ex_tr = [_fl_path_exact(p, p["T"] * k / 60.0, p["T"]) for k in range(61)]
        else:
            tr = _fl_rk4(p, p["x0"], p["y0"], 0.0, p["T"] / n, n, False)
            ex_tr = [_fl_path_exact(p, 0.0, p["T"] * k / 60.0) for k in range(61)]
        val = tr[-1][1]
        ex = _fl_exact(p)
        return _base(val, ex, n, [q[0] for q in ex_tr], [q[1] for q in ex_tr], [], [q[0] for q in tr],
                     [q[1] for q in tr], xend=tr[-1][0])


# ============================================================================================ game theory
def _gm_exact(p: dict) -> float:
    if _i(p["cas"]) == 1:                          # 2 x 2 zero-sum game: the row player's minimax probability of row 1
        a, b, c, d = p["a"], p["b"], p["c"], p["d"]
        return (d - c) / (a + d - b - c)
    return p["V"] / p["C"]                         # Hawk-Dove: the evolutionarily stable fraction of hawks


class CwGame(_Base):
    """cas 0: the Hawk-Dove game (Maynard Smith): replicator dynamics dp/dt = p (1 - p) (V - C p) / 2 for the hawk
    fraction p, integrated by Euler steps of dt = tend / n; reference the evolutionarily stable state V / C.
    cas 1: a 2 x 2 zero-sum game with payoff matrix [[a, b], [c, d]] to the row player, played by fictitious play for
    n rounds (each player best-responds to the other's past frequencies; ties go to the first strategy); the row
    player's frequency of row 1 against the minimax strategy (d - c) / (a + d - b - c) (Robinson 1951 proved
    convergence)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 40.0, "V": 2.0, "C": 5.0, "p0": 0.1, "tend": 60.0,
              "a": 2.0, "b": -1.0, "c": -1.0, "d": 1.0}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(1, _i(p["n"]))
        ex = _gm_exact(p)
        if cas == 1:
            a, b, c, d = p["a"], p["b"], p["c"], p["d"]
            r1, r2, c1, c2 = 1.0, 0.0, 1.0, 0.0    # counts so far (both open with strategy 1)
            tr = []
            every = max(1, n // 60)
            for k in range(1, n):
                # row best response to the column frequencies; column minimises the row payoff
                ur1 = a * c1 + b * c2
                ur2 = c * c1 + d * c2
                uc1 = a * r1 + c * r2
                uc2 = b * r1 + d * r2
                if ur1 >= ur2:
                    r1 += 1.0
                else:
                    r2 += 1.0
                if uc1 <= uc2:
                    c1 += 1.0
                else:
                    c2 += 1.0
                if k % every == 0:
                    tr.append([float(k + 1), r1 / (r1 + r2)])
            val = r1 / (r1 + r2)
            return _base(val, ex, n, [q[0] for q in tr], [ex for _ in tr], [q[1] for q in tr], [], [],
                         colfreq=c1 / (c1 + c2))
        V, C = p["V"], p["C"]
        h = p["tend"] / n
        x = p["p0"]
        tr = [[0.0, x]]
        for k in range(n):
            x = x + h * x * (1.0 - x) * (V - C * x) / 2.0
            tr.append([(k + 1) * h, x])
        val = x
        return _base(val, ex, n, [q[0] for q in _thin(tr, 60)], [ex for _ in _thin(tr, 60)],
                     [q[1] for q in _thin(tr, 60)], [], [])


# ============================================================================================ discrete convolution
def _cv_x(p: dict, k: int) -> float:
    return math.pow(p["al"], k) if 0 <= k < _i(p["Lx"]) else 0.0


def _cv_h(p: dict, k: int) -> float:
    return math.pow(p["be"], k) if 0 <= k < _i(p["Lh"]) else 0.0


def _cv_exact_at(p: dict, m: int) -> float:
    """Closed form of the linear convolution of two truncated geometric sequences: sum over the overlap."""
    al, be = p["al"], p["be"]
    lo = max(0, m - _i(p["Lh"]) + 1)
    hi = min(m, _i(p["Lx"]) - 1)
    if hi < lo:
        return 0.0
    # sum_{j=lo}^{hi} al^j be^(m-j) = be^m sum (al/be)^j, a finite geometric series
    q = al / be
    if abs(1.0 - q) < 1e-12:                       # equal ratios (e.g. a gate with itself): every term is be^m
        return math.pow(be, m) * (hi - lo + 1)
    return math.pow(be, m) * (math.pow(q, lo) - math.pow(q, hi + 1)) / (1.0 - q)


def _cv_exact(p: dict) -> float:
    return _cv_exact_at(p, _i(p["m"]))


class CwConv(_Base):
    """Linear convolution y = x * h of x[k] = al^k (k < Lx) and h[k] = be^k (k < Lh). Method 0: the circular
    convolution of length n by the DFT (y = IDFT(DFT(x) DFT(h)), both zero-padded to n) - correct only when
    n >= Lx + Lh - 1, otherwise the tail wraps round (time aliasing). Method 1: the direct convolution sum. The
    quantity is y[m], against the closed-form finite geometric sum."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 16.0, "al": 0.8, "be": 0.5, "Lx": 12.0, "Lh": 10.0, "m": 3.0}

    @staticmethod
    def init(p, cfg=None):
        meth = _i(p["method"])
        Lx, Lh = _i(p["Lx"]), _i(p["Lh"])
        Ly = Lx + Lh - 1
        n = max(1, _i(p["n"]))
        m = _i(p["m"])
        if meth == 1:
            y = []
            for k in range(Ly):
                s = 0.0
                for j in range(Lx):
                    s += _cv_x(p, j) * _cv_h(p, k - j)
                y.append(s)
        else:
            N = n
            xr = [_cv_x(p, k) if k < N else 0.0 for k in range(N)]
            hr = [_cv_h(p, k) if k < N else 0.0 for k in range(N)]
            # (a sequence longer than N folds onto itself: that IS the circular convolution of length N)
            for k in range(N, Lx):
                xr[k % N] += _cv_x(p, k)
            for k in range(N, Lh):
                hr[k % N] += _cv_h(p, k)
            Xr, Xi, Hr, Hi = [], [], [], []
            for f in range(N):
                a1 = a2 = b1 = b2 = 0.0
                for k in range(N):
                    ang = 2 * PI * f * k / N
                    c, s = math.cos(ang), math.sin(ang)
                    a1 += xr[k] * c
                    a2 -= xr[k] * s
                    b1 += hr[k] * c
                    b2 -= hr[k] * s
                Xr.append(a1 * b1 - a2 * b2)
                Xi.append(a1 * b2 + a2 * b1)
            y = []
            for k in range(N):
                s = 0.0
                for f in range(N):
                    ang = 2 * PI * f * k / N
                    s += Xr[f] * math.cos(ang) - Xi[f] * math.sin(ang)
                y.append(s / N)
        val = y[m] if m < len(y) else 0.0
        ex = _cv_exact(p)
        K = max(Ly, len(y))
        cx = [float(k) for k in range(K)]
        ce = [_cv_exact_at(p, k) for k in range(K)]
        cy = [y[k] if k < len(y) else 0.0 for k in range(K)]
        return _base(val, ex, n, cx, ce, cy, [float(m)], [val], Ly=float(Ly))


# ============================================================================================ LTI system from a difference equation
def _lti_coef(p: dict) -> list[float]:
    """y[k] = a1 y[k-1] + a2 y[k-2] + b0 x[k] + b1 x[k-1], with poles r e^(+-i th): a1 = 2 r cos th, a2 = -r^2."""
    r, th = p["r"], p["th"]
    return [2.0 * r * math.cos(th), -r * r, p["b0"], p["b1"]]


def _lti_H(p: dict, w: float) -> float:
    a1, a2, b0, b1 = _lti_coef(p)
    nr = b0 + b1 * math.cos(w)
    ni = -b1 * math.sin(w)
    dr = 1.0 - a1 * math.cos(w) - a2 * math.cos(2 * w)
    di = a1 * math.sin(w) + a2 * math.sin(2 * w)
    return math.sqrt((nr * nr + ni * ni) / (dr * dr + di * di))


def _lti_exact(p: dict) -> float:
    if _i(p["what"]) == 1:
        a1, a2, b0, b1 = _lti_coef(p)
        return (b0 + b1) / (1.0 - a1 - a2)        # H(z = 1): the final value of the step response
    return _lti_H(p, p["w0"])


def _lti_run(p: dict, xin, n: int) -> list[float]:
    a1, a2, b0, b1 = _lti_coef(p)
    y = []
    y1 = y2 = x1 = 0.0
    for k in range(n):
        x0 = xin(k)
        v = a1 * y1 + a2 * y2 + b0 * x0 + b1 * x1
        y.append(v)
        y2, y1, x1 = y1, v, x0
    return y


class CwLti(_Base):
    """The LTI system y[k] = a1 y[k-1] + a2 y[k-2] + b0 x[k] + b1 x[k-1] (poles r e^(+-i th), zero at -b1/b0),
    run sample by sample. what 0: the impulse response h[k] for n samples and its DTFT magnitude
    |sum_k h[k] e^(-i w0 k)| at w0, against |B(e^iw0) / A(e^iw0)|; what 1: the step response after n samples, against
    the final value H(1) = (b0 + b1) / (1 - a1 - a2). Both errors fall as r^n: the poles decide how fast."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 32.0, "r": 0.8, "th": 0.6, "b0": 1.0, "b1": 0.5, "w0": 0.6}

    @staticmethod
    def init(p, cfg=None):
        what = _i(p["what"])
        n = max(1, _i(p["n"]))
        if what == 1:
            y = _lti_run(p, lambda k: 1.0, n)
            val = y[-1]
        else:
            y = _lti_run(p, lambda k: 1.0 if k == 0 else 0.0, n)
            re = im = 0.0
            for k in range(n):
                re += y[k] * math.cos(p["w0"] * k)
                im -= y[k] * math.sin(p["w0"] * k)
            val = math.sqrt(re * re + im * im)
        ex = _lti_exact(p)
        cx = [float(k) for k in range(len(y))]
        a1, a2, b0, b1 = _lti_coef(p)
        r, th = p["r"], p["th"]
        poles = [r * math.cos(th), r * math.sin(th), r * math.cos(th), -r * math.sin(th)]
        zeros = [-b1 / b0 if abs(b0) > 1e-300 else 0.0, 0.0]
        return _base(val, ex, n, _thin(cx, 80), [ex for _ in _thin(cx, 80)] if what == 1 else [], _thin(y, 80),
                     _thin(cx, 80), _thin(y, 80), poles=poles, zeros=zeros)


# ============================================================================================ FIR filter design by windowing
def _fir_taps(p: dict, N: int) -> list[float]:
    meth = _i(p["method"])
    wc = p["wc"]
    M = N - 1
    h = []
    for k in range(N):
        t = k - 0.5 * M
        hd = wc / PI if abs(t) < 1e-12 else math.sin(wc * t) / (PI * t)
        if meth == 1:                              # Hann
            wn = 0.5 - 0.5 * math.cos(2 * PI * k / M)
        elif meth == 2:                            # Hamming
            wn = 0.54 - 0.46 * math.cos(2 * PI * k / M)
        else:                                      # rectangular
            wn = 1.0
        h.append(hd * wn)
    return h


def _fir_A(h: list[float], w: float) -> float:
    """Zero-phase amplitude of a symmetric (type I) filter: sum h[k] cos(w (k - M/2))."""
    M = len(h) - 1
    s = 0.0
    for k in range(len(h)):
        s += h[k] * math.cos(w * (k - 0.5 * M))
    return s


class CwFir(_Base):
    """A low-pass FIR filter of odd length N = n designed by windowing the ideal impulse response sin(wc t)/(pi t)
    (method 0 rectangular, 1 Hann, 2 Hamming). The half-amplitude frequency of the designed filter is found from its
    computed response: a scan of A(w) - 1/2 across the transition band, then 60 bisections. The reference is the design
    cut-off wc, where a windowed-sinc filter crosses one half (the transition is centred on the ideal edge)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 31.0, "wc": 1.0}

    @staticmethod
    def init(p, cfg=None):
        N = max(5, _i(p["n"]))
        if N % 2 == 0:
            N += 1
        h = _fir_taps(p, N)
        wc = p["wc"]
        span = 6 * PI / N
        lo, hi = max(1e-6, wc - span), min(PI - 1e-6, wc + span)
        m = 120
        a = lo
        fa = _fir_A(h, a) - 0.5
        b = hi
        for i in range(1, m + 1):                  # the first fall through 1/2
            x = lo + (hi - lo) * i / m
            fx = _fir_A(h, x) - 0.5
            if fa > 0 >= fx:
                b = x
                break
            a, fa = x, fx
        for _ in range(60):
            mid = 0.5 * (a + b)
            if _fir_A(h, mid) - 0.5 > 0:
                a = mid
            else:
                b = mid
        val = 0.5 * (a + b)
        ex = wc
        cx = _grid(0.0, PI, 120)
        ce = [1.0 if w <= wc else 0.0 for w in cx]
        cy = [_fir_A(h, w) for w in cx]
        dB = []
        for w in cx:
            v = abs(_fir_A(h, w))
            dB.append(20 * math.log10(v) if v > 1e-12 else -240.0)
        return _base(val, ex, N, cx, ce, cy, [val], [0.5], taps=h, dB=dB)


# ============================================================================================ geodesics
def _gd_ends(p: dict) -> list[list[float]]:
    if _i(p["cas"]) == 1:                          # two points on a sphere of radius R, given by latitude / longitude
        out = []
        for la, lo in ((p["la1"], p["lo1"]), (p["la2"], p["lo2"])):
            a, b = la * PI / 180.0, lo * PI / 180.0
            out.append([p["R"] * math.cos(a) * math.cos(b), p["R"] * math.cos(a) * math.sin(b), p["R"] * math.sin(a)])
        return out
    return [[p["xa"], p["ya"], 0.0], [p["xb"], p["yb"], 0.0]]


def _gd_exact(p: dict) -> float:
    A, B = _gd_ends(p)
    if _i(p["cas"]) == 1:                          # great-circle distance R * angle (atan2 form, well conditioned)
        cx = A[1] * B[2] - A[2] * B[1]
        cy = A[2] * B[0] - A[0] * B[2]
        cz = A[0] * B[1] - A[1] * B[0]
        dot = A[0] * B[0] + A[1] * B[1] + A[2] * B[2]
        return p["R"] * math.atan2(math.sqrt(cx * cx + cy * cy + cz * cz), dot)
    return math.sqrt((B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2)


class CwGeod(_Base):
    """The shortest path between two points, found numerically: a path of n segments starts off as a curve that is NOT
    the geodesic (a bump in the plane; a straight line in latitude-longitude on the sphere) and is shortened by
    relaxation - every inner point moves to the midpoint of its neighbours (then back onto the sphere) - for 6 n^2 + 50
    sweeps. The quantity is the length of the relaxed path (the sum of its n chords), against the straight-line
    distance (plane, cas 0) or the great-circle distance R x angle (sphere, cas 1)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "xa": 0.0, "ya": 0.0, "xb": 3.0, "yb": 1.0, "bump": 1.0,
              "R": 1.0, "la1": 10.0, "lo1": 0.0, "la2": 50.0, "lo2": 100.0}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(2, _i(p["n"]))
        A, B = _gd_ends(p)
        P = []
        for k in range(n + 1):
            s = k / n
            if cas == 1:
                la = (p["la1"] + (p["la2"] - p["la1"]) * s) * PI / 180.0
                lo = (p["lo1"] + (p["lo2"] - p["lo1"]) * s) * PI / 180.0
                P.append([p["R"] * math.cos(la) * math.cos(lo), p["R"] * math.cos(la) * math.sin(lo), p["R"] * math.sin(la)])
            else:
                bx = A[0] + (B[0] - A[0]) * s
                by = A[1] + (B[1] - A[1]) * s + p["bump"] * math.sin(PI * s)
                P.append([bx, by, 0.0])
        start = [list(q) for q in P]
        sweeps = 6 * n * n + 50
        for _ in range(sweeps):
            for k in range(1, n):
                x = 0.5 * (P[k - 1][0] + P[k + 1][0])
                y = 0.5 * (P[k - 1][1] + P[k + 1][1])
                z = 0.5 * (P[k - 1][2] + P[k + 1][2])
                if cas == 1:
                    rr = math.sqrt(x * x + y * y + z * z)
                    x, y, z = p["R"] * x / rr, p["R"] * y / rr, p["R"] * z / rr
                P[k] = [x, y, z]

        def length(Q):
            s = 0.0
            for k in range(n):
                dx = Q[k + 1][0] - Q[k][0]
                dy = Q[k + 1][1] - Q[k][1]
                dz = Q[k + 1][2] - Q[k][2]
                s += math.sqrt(dx * dx + dy * dy + dz * dz)
            return s
        val = length(P)
        ex = _gd_exact(p)
        if cas == 1:                               # draw longitude / latitude of the paths
            def ll(q):
                return [math.atan2(q[1], q[0]) * 180.0 / PI, math.asin(max(-1.0, min(1.0, q[2] / p["R"]))) * 180.0 / PI]
            c0 = [ll(q) for q in start]
            c1 = [ll(q) for q in P]
        else:
            c0 = [[q[0], q[1]] for q in start]
            c1 = [[q[0], q[1]] for q in P]
        return _base(val, ex, n, [q[0] for q in c0], [q[1] for q in c0], [], [q[0] for q in c1], [q[1] for q in c1],
                     L0=length(start), sweeps=float(sweeps))


# ============================================================================================ constrained Lagrangian mechanics
def _agm_K(k: float) -> float:
    """Complete elliptic integral of the first kind K(k) = pi / (2 AGM(1, sqrt(1 - k^2)))."""
    a, b = 1.0, math.sqrt(1.0 - k * k)
    for _ in range(40):
        a, b = 0.5 * (a + b), math.sqrt(a * b)
        if abs(a - b) < 1e-16 * a:
            break
    return PI / (2.0 * a)


def _cs_exact(p: dict) -> float:
    cas = _i(p["cas"])
    g = p["g"]
    if cas == 1:                                   # Atwood machine: acceleration (what 0) or the string tension (what 1)
        m1, m2 = p["m1"], p["m2"]
        if _i(p["what"]) == 1:
            return 2.0 * m1 * m2 * g / (m1 + m2)
        return (m1 - m2) * g / (m1 + m2)
    if cas == 2:                                   # bead on a hoop spun at w: small oscillations about cos th0 = g/(w^2 R)
        w = p["w"]
        c0 = g / (w * w * p["R"])
        return 2 * PI / (w * math.sqrt(1.0 - c0 * c0))
    th0 = p["th0"] * PI / 180.0                    # pendulum: the exact large-amplitude period
    return 4.0 * math.sqrt(p["L"] / g) * _agm_K(math.sin(0.5 * th0))


def _cs_rk4(f, y: list[float], h: float) -> list[float]:
    n = len(y)
    k1 = f(y)
    k2 = f([y[i] + 0.5 * h * k1[i] for i in range(n)])
    k3 = f([y[i] + 0.5 * h * k2[i] for i in range(n)])
    k4 = f([y[i] + h * k3[i] for i in range(n)])
    return [y[i] + h * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0 for i in range(n)]


class CwConstr(_Base):
    """Lagrange's equations with a constraint, integrated by fourth-order Runge-Kutta with n steps per (expected)
    period. cas 0: a pendulum as a particle in the plane with the constraint x^2 + y^2 = L^2 held by a Lagrange
    multiplier lambda = (v^2 - g y)/r^2 (the string tension per unit mass and length); the period is timed from the
    zero crossings of x and compared with 4 sqrt(L/g) K(sin(theta0/2)). cas 1: an Atwood machine, constraint
    y1 + y2 = const, the multiplier = the tension; the acceleration (what 0) or the tension (what 1) is read from the
    run. cas 2: a bead on a vertical hoop of radius R spun at w (the constraint removes r and phi); its small oscillation
    about the off-axis equilibrium is timed, against 2 pi / (w sin th0)."""
    PARAMS = {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 32.0, "g": 9.80665, "L": 1.0, "th0": 30.0,
              "m1": 0.3, "m2": 0.2, "R": 0.2, "w": 10.0, "amp": 0.0001, "periods": 3.0}

    @staticmethod
    def init(p, cfg=None):
        cas, what = _i(p["cas"]), _i(p["what"])
        n = max(4, _i(p["n"]))
        g = p["g"]
        ex = _cs_exact(p)
        cx, cy, cz = [], [], []
        if cas == 1:
            m1, m2 = p["m1"], p["m2"]
            T1 = 1.0
            h = T1 / n

            def f(s):                               # s = [y1, v1]; y2 = -y1; multiplier from the constraint
                lam = 2.0 * m1 * m2 * g / (m1 + m2)  # solved from m1 a = m1 g - lam, m2 (-a) = m2 g - lam
                return [s[1], (m1 * g - lam) / m1]
            s = [0.0, 0.0]
            for k in range(n):
                s = _cs_rk4(f, s, h)
                cx.append((k + 1) * h)
                cy.append(s[0])
            acc = 2.0 * s[0] / (T1 * T1)
            val = 2.0 * m1 * m2 * g / (m1 + m2) if what == 1 else acc
            if what == 1:                          # the tension measured from the motion: m1 (g - a)
                val = m1 * (g - acc)
            return _base(val, ex, n, cx, [0.5 * ex * t * t for t in cx] if what == 0 else [], cy, [], [])
        if cas == 2:
            w, R = p["w"], p["R"]
            c0 = g / (w * w * R)
            th0 = math.acos(c0)
            Tg = 2 * PI / (w * math.sqrt(1.0 - c0 * c0))
            h = Tg / n

            def f(s):                               # theta'' = sin th (w^2 cos th - g/R)
                return [s[1], math.sin(s[0]) * (w * w * math.cos(s[0]) - g / R)]
            s = [th0 + p["amp"], 0.0]
            nsteps = _i(p["periods"] * n) + 2
            cross, t = [], 0.0
            prev = s[0] - th0
            for k in range(nsteps):
                s2 = _cs_rk4(f, s, h)
                d2 = s2[0] - th0
                if prev > 0 >= d2 or prev < 0 <= d2:
                    cross.append(t + h * prev / (prev - d2))
                s, prev, t = s2, d2, t + h
                cx.append(t)
                cy.append(d2)
            val = 2.0 * (cross[-1] - cross[0]) / (len(cross) - 1) if len(cross) >= 2 else 0.0
            return _base(val, ex, n, _thin(cx, 120), [], _thin(cy, 120), [], [], th0=th0)
        L = p["L"]
        a0 = p["th0"] * PI / 180.0
        Tg = ex
        h = Tg / n

        def f(s):                                   # s = [x, y, vx, vy]; y measured upward from the pivot
            x, y, vx, vy = s
            r2 = x * x + y * y
            lam = (vx * vx + vy * vy - g * y) / r2
            return [vx, vy, -lam * x, -lam * y - g]
        s = [L * math.sin(a0), -L * math.cos(a0), 0.0, 0.0]
        nsteps = _i(p["periods"] * n) + 2
        cross, t = [], 0.0
        for k in range(nsteps):
            s2 = _cs_rk4(f, s, h)
            if s[0] > 0 >= s2[0] or s[0] < 0 <= s2[0]:
                # cubic Hermite between the two steps for the crossing time (x and vx known at both ends)
                lo_t, hi_t = 0.0, h
                for _ in range(60):
                    mt = 0.5 * (lo_t + hi_t)
                    u2 = mt / h
                    h00 = 2 * u2 ** 3 - 3 * u2 ** 2 + 1
                    h10 = u2 ** 3 - 2 * u2 ** 2 + u2
                    h01 = -2 * u2 ** 3 + 3 * u2 ** 2
                    h11 = u2 ** 3 - u2 ** 2
                    xm = h00 * s[0] + h10 * h * s[2] + h01 * s2[0] + h11 * h * s2[2]
                    if (xm > 0) == (s[0] > 0):
                        lo_t = mt
                    else:
                        hi_t = mt
                cross.append(t + 0.5 * (lo_t + hi_t))
            s, t = s2, t + h
            cx.append(s[0])
            cy.append(s[1])
        val = 2.0 * (cross[-1] - cross[0]) / (len(cross) - 1) if len(cross) >= 2 else 0.0
        drift = abs(math.sqrt(s[0] * s[0] + s[1] * s[1]) - L) / L
        return _base(val, ex, n, _thin(cx, 120), [], _thin(cy, 120), [], [], drift=drift)


# ============================================================================================ registry
KERNELS: dict[str, Any] = {
    "cw8_fact": CwFact, "cw8_frame": CwFrame, "cw8_vfield": CwVfield, "cw8_group": CwGroup, "cw8_gfx": CwGfx,
    "cw8_anharm": CwAnharm, "cw8_ljmd": CwLjmd, "cw8_levels": CwLevels, "cw8_maxwell": CwMaxwell,
    "cw8_heatcap": CwHeatcap, "cw8_qdist": CwQdist, "cw8_fractal": CwFractal, "cw8_flow": CwFlow, "cw8_game": CwGame,
    "cw8_conv": CwConv, "cw8_lti": CwLti, "cw8_fir": CwFir, "cw8_geod": CwGeod, "cw8_constr": CwConstr,
}
FAMILY = {k: "comp" for k in KERNELS}

TEXTBOOK = {
    "cw8_fact_v": _fact_exact, "cw8_frame_v": _frame_exact, "cw8_vfield_v": _vf_exact, "cw8_group_v": _gw_exact,
    "cw8_gfx_v": _gfx_exact, "cw8_anharm_v": _ah_exact, "cw8_ljmd_v": _lj_exact, "cw8_levels_v": _lv_exact,
    "cw8_maxwell_v": _mx_exact, "cw8_heatcap_v": _hc_exact, "cw8_qdist_v": _qd_exact, "cw8_fractal_v": _fr_exact,
    "cw8_flow_v": _fl_exact, "cw8_game_v": _gm_exact, "cw8_conv_v": _cv_exact, "cw8_lti_v": _lti_exact,
    "cw8_fir_v": lambda p: p["wc"], "cw8_geod_v": _gd_exact, "cw8_constr_v": _cs_exact,
}


def _best(rows, p) -> float:
    """The answer of the run with the smallest error (ties: the larger n)."""
    rs = _rows(rows, "n", "val", "err")
    if not rs:
        return 0.0
    b = rs[0]
    for r in rs:
        if r[2] < b[2] or (r[2] == b[2] and r[0] > b[0]):
            b = r
    return b[1]


def _order(rows, p) -> float:
    """The order of the method, from the slope of log(error) against log(n): err ~ n^-order."""
    pts = [[math.log(n), math.log(e)] for n, e in _rows(rows, "n", "err") if n > 0 and e > 0]
    if len(pts) < 2:
        return 0.0
    sx = _sum([q[0] for q in pts])
    sy = _sum([q[1] for q in pts])
    sxx = _sum([q[0] * q[0] for q in pts])
    sxy = _sum([q[0] * q[1] for q in pts])
    den = len(pts) * sxx - sx * sx
    if abs(den) < 1e-30:
        return 0.0
    return -(len(pts) * sxy - sx * sy) / den


CALCS = {
    "cw8_best": {"label": "best value", "unit": "", "needs": ["n", "val", "err"], "fn": _best},
    "cw8_order": {"label": "order of the method", "unit": "", "needs": ["n", "err"], "fn": _order},
}
