"""Kernel pack: the M.Sc. / Ph.D. "Computational physics" practicals (DU PH-DSE5221, DSE5142, standard research methods).

The B.Sc. pack (`comp_ug`) compares a numerical method with a closed-form answer. This one does the same at the next
level: Monte Carlo (Ising, spins, random walks, decay chains, scattering, photons, integration, deviates), partial
differential equations (finite differences, finite elements, FDTD, particle-in-cell), eigenproblems (tight binding,
Schrodinger by shooting and split-step, exact diagonalisation by Lanczos), N-body dynamics and Bayesian fitting by MCMC.

Every kernel keeps the shape of the B.Sc. pack so ONE workstation rig (`comp3-workstation`) serves them all:

    PARAMS  cas (which problem), method, n (steps / samples / nodes) and the problem's own numbers
    init    runs the whole computation once and keeps the result
    step    advances a clock only
    view    val (the numerical answer), exact (the reference), err (|val-exact|/|exact|), nused, and the curves the
            monitor draws: cx / ce (the reference), cy (what the method built), px / py (nodes or points used), plus
            optional lat (a lattice), pts (particles), cy2 / ce2 (a second curve)
    measure {val, exact, err, nused}

Every kernel is named `cr_*`, and its EXACT JavaScript twin is `app/static/prayog/packs/comp3_adv.js` (same formulas, same
order of operations). Anything random is a seeded Lehmer generator (16807, mod 2^31 - 1), never the clock.

The reference ("exact") of each kernel, and how exact it is:
    cr_interp   f(x) itself                                                     exact
    cr_pde      Fourier series (heat) / d'Alembert (wave) of a plucked string   exact
    cr_fem      sin(pi x) or x(1-x)/2 for -u'' = f                               exact
    cr_fit      the parameter the data were generated from                      statistical (stated in each lab)
    cr_mle      the parameter the data were generated from                      statistical
    cr_dev      the exact probability of the interval (erf / closed form)       statistical
    cr_walk     <R^2> = N steps; P(origin) = exact lattice sum                  statistical
    cr_decay    Bateman equations                                               statistical
    cr_twolevel tanh(x) and x^2 sech^2(x) (Boltzmann, independent spins)        statistical
    cr_ising    1-D transfer matrix; 2-D Onsager energy and magnetisation       statistical (+ finite size, stated)
    cr_binder   2/ln(1+sqrt2) = 2.2692 J/kB (Onsager 1944)                      statistical + finite-size crossing
    cr_mcint    exact integrals of sin x and exp(-x^2)                          statistical
    cr_scatter  pi a^2 (hard sphere); pi b0^2 (Rutherford)                      statistical
    cr_photon   Beer-Lambert e^(-mu d) and first-collision probabilities        statistical
    cr_poly     the roots the polynomial was built from / Cardano                exact
    cr_tb       -2t cos(ka), 2 t |f(k)| band widths; -4t/pi per site             exact
    cr_schro    n + 1/2, n^2 pi^2/2, -1/(2 n^2) (atomic units)                  exact
    cr_nbody    Kepler's third law; the virial theorem                           exact / time average (stated)
    cr_spin     spin-wave (harmonic) energy and helicity modulus, low T         exact limit; anharmonic part stated
    cr_ed       free-fermion energy of the transverse-field Ising ring;           exact / Bethe ansatz limit
                1/4 - ln 2 for the Heisenberg chain
    cr_mcmc     the posterior integrated on a grid / the Gaussian posterior      exact (quadrature) / analytic
    cr_fdtd     transfer matrix of the slab or Bragg stack                       exact
    cr_pic      omega_p (cold plasma), two-stream dispersion relation            exact (cold fluid)
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
_M = 2147483647


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


def _gauss(st: list[float]) -> float:
    """One standard normal number (Box-Muller, the cosine member of the pair)."""
    u1 = _u(st)
    u2 = _u(st)
    return math.sqrt(-2.0 * math.log(u1 if u1 > 1e-300 else 1e-300)) * math.cos(2 * PI * u2)


def _marks(N: int) -> list[int]:
    """60 sample counts spread logarithmically up to N (the running-estimate curve)."""
    out: list[int] = []
    for i in range(1, 61):
        v = _i(math.pow(float(N), i / 60.0))
        if v < 1:
            v = 1
        if not out or v > out[-1]:
            out.append(v)
    return out


def _erf(x: float) -> float:
    """erf by the all-positive series 2/sqrt(pi) e^(-x^2) sum 2^n x^(2n+1) / (1 3 5 ... (2n+1)); no cancellation."""
    sg = 1.0
    if x < 0:
        x = -x
        sg = -1.0
    if x > 6.0:
        return sg
    term = x
    s = x
    n = 0
    while n < 400:
        n += 1
        term = term * 2.0 * x * x / (2 * n + 1)
        s += term
        if term < 1e-17 * s:
            break
    return sg * 2.0 / math.sqrt(PI) * math.exp(-x * x) * s


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (small systems)."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        piv = c
        for r in range(c + 1, n):
            if abs(M[r][c]) > abs(M[piv][c]):
                piv = r
        M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        if abs(d) < 1e-300:
            d = 1e-300
        for r in range(c + 1, n):
            f = M[r][c] / d
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n]
        for k in range(r + 1, n):
            s -= M[r][k] * x[k]
        d = M[r][r]
        if abs(d) < 1e-300:
            d = 1e-300
        x[r] = s / d
    return x


def _tri(a: list[float], b: list[float], c: list[float], d: list[float]) -> list[float]:
    """Thomas algorithm: a sub-diagonal (a[0] unused), b diagonal, c super-diagonal, d right-hand side."""
    n = len(d)
    cp = [0.0] * n
    dp = [0.0] * n
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x = [0.0] * n
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
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


# ============================================================================================ interpolation
def _ip_f(cas: int, x: float) -> float:
    if cas == 1:
        return 1.0 / (1.0 + 25.0 * x * x)
    return math.sin(x)


def _ip_df(cas: int, x: float) -> float:
    if cas == 1:
        d = 1.0 + 25.0 * x * x
        return -50.0 * x / (d * d)
    return math.cos(x)


def _lagr(xs: list[float], ys: list[float], x: float) -> float:
    tot = 0.0
    for i in range(len(xs)):
        L = 1.0
        for j in range(len(xs)):
            if j != i:
                L = L * (x - xs[j]) / (xs[i] - xs[j])
        tot += ys[i] * L
    return tot


def _spline_fit(xs: list[float], ys: list[float], d0: float, d1: float) -> list[float]:
    """Second derivatives M of the clamped cubic spline through equally spaced nodes."""
    n = len(xs) - 1
    h = xs[1] - xs[0]
    a = [0.0] * (n + 1)
    b = [0.0] * (n + 1)
    c = [0.0] * (n + 1)
    d = [0.0] * (n + 1)
    b[0] = h / 3.0
    c[0] = h / 6.0
    d[0] = (ys[1] - ys[0]) / h - d0
    for i in range(1, n):
        a[i] = h / 6.0
        b[i] = 2.0 * h / 3.0
        c[i] = h / 6.0
        d[i] = (ys[i + 1] - 2.0 * ys[i] + ys[i - 1]) / h
    a[n] = h / 6.0
    b[n] = h / 3.0
    d[n] = d1 - (ys[n] - ys[n - 1]) / h
    return _tri(a, b, c, d)


def _spline_at(xs: list[float], ys: list[float], M: list[float], x: float) -> float:
    n = len(xs) - 1
    h = xs[1] - xs[0]
    j = int(math.floor((x - xs[0]) / h))
    if j < 0:
        j = 0
    if j > n - 1:
        j = n - 1
    l = xs[j + 1] - x
    r = x - xs[j]
    return (M[j] * l * l * l + M[j + 1] * r * r * r) / (6.0 * h) + (ys[j] / h - M[j] * h / 6.0) * l \
        + (ys[j + 1] / h - M[j + 1] * h / 6.0) * r


class CrInterp(_Base):
    """Lagrange polynomial through n+1 equally spaced nodes, or the clamped cubic spline through the same nodes."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "x": 1.3, "xa": 0.0, "xb": PI}

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(2, _i(p["n"]))
        xa, xb = p["xa"], p["xb"]
        xs = _grid(xa, xb, n)
        ys = [_ip_f(cas, q) for q in xs]
        if meth == 0:
            ev = lambda q: _lagr(xs, ys, q)
        else:
            M = _spline_fit(xs, ys, _ip_df(cas, xa), _ip_df(cas, xb))
            ev = lambda q: _spline_at(xs, ys, M, q)
        val = ev(p["x"])
        exact = _ip_f(cas, p["x"])
        cx = _grid(xa, xb, 120)
        return _base(val, exact, n + 1, cx, [_ip_f(cas, q) for q in cx], [ev(q) for q in cx], xs, ys)


def _ip_exact(p: dict) -> float:
    return _ip_f(_i(p["cas"]), p["x"])


# ============================================================================================ finite differences
def _hat(y: float) -> float:
    return 2.0 * y if y <= 0.5 else 2.0 * (1.0 - y)


def _hat_ext(x: float) -> float:
    """The plucked-string profile continued as an odd function of period 2."""
    y = x - 2.0 * math.floor((x + 1.0) / 2.0)
    if y < 0:
        return -_hat(-y)
    return _hat(y)


def _pde_exact_at(p: dict, x: float) -> float:
    cas = _i(p["cas"])
    t = p["tend"]
    if cas == 1:
        return 0.5 * (_hat_ext(x - p["c"] * t) + _hat_ext(x + p["c"] * t))
    tot = 0.0
    m = 1
    while m <= 61:
        b = 8.0 / (m * m * PI * PI) * (1.0 if (m % 4) == 1 else -1.0)
        tot += b * math.sin(m * PI * x) * math.exp(-p["c"] * m * m * PI * PI * t)
        m += 2
    return tot


def _lap(u: list[float]) -> list[float]:
    n = len(u)
    out = [0.0] * n
    for j in range(1, n - 1):
        out[j] = u[j + 1] - 2.0 * u[j] + u[j - 1]
    return out


def _implicit_solve(rhs: list[float], coef: float, diag: float) -> list[float]:
    """Solve (diag on the diagonal, coef off it) u = rhs on the interior points; the ends stay zero."""
    n = len(rhs)
    m = n - 2
    a = [coef] * m
    b = [diag] * m
    c = [coef] * m
    d = [rhs[j + 1] for j in range(m)]
    x = _tri(a, b, c, d)
    return [0.0] + x + [0.0]


class CrPde(_Base):
    """u_t = c u_xx (heat) or u_tt = c^2 u_xx (wave) on (0, 1) with a plucked-string start. n = grid intervals; the
    time step follows from the stability number r (heat: c dt / dx^2; wave: c dt / dx). Explicit or implicit."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 40.0, "tend": 0.5, "c": 0.1, "r": 0.4, "xp": 0.3}

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        nx = max(10, _i(p["n"]))
        dx = 1.0 / nx
        if cas == 0:
            dt0 = p["r"] * dx * dx / p["c"]
        else:
            dt0 = p["r"] * dx / p["c"]
        n = max(2, _i(p["tend"] / dt0))
        dt = p["tend"] / n
        xs = _grid(0.0, 1.0, nx)
        u = [_hat(q) for q in xs]
        blown = 0.0
        if cas == 0:
            r = p["c"] * dt / (dx * dx)
            stab = r
            for _ in range(n):
                L = _lap(u)
                if meth == 0:
                    u = [u[j] + r * L[j] for j in range(nx + 1)]
                else:
                    rhs = [u[j] + 0.5 * r * L[j] for j in range(nx + 1)]
                    u = _implicit_solve(rhs, -0.5 * r, 1.0 + r)
                if max(abs(q) for q in u) > 1e9:
                    blown = 1.0
                    break
        else:
            nu = p["c"] * dt / dx
            stab = nu
            n2 = nu * nu
            L = _lap(u)
            if meth == 0:
                un = [u[j] + 0.5 * n2 * L[j] for j in range(nx + 1)]
            else:
                rhs = [u[j] + 0.25 * n2 * L[j] for j in range(nx + 1)]
                un = _implicit_solve(rhs, -0.25 * n2, 1.0 + 0.5 * n2)
            up = u
            u = un
            for _ in range(n - 1):
                L = _lap(u)
                Lp = _lap(up)
                if meth == 0:
                    un = [2.0 * u[j] - up[j] + n2 * L[j] for j in range(nx + 1)]
                else:
                    rhs = [2.0 * u[j] - up[j] + 0.25 * n2 * (2.0 * L[j] + Lp[j]) for j in range(nx + 1)]
                    un = _implicit_solve(rhs, -0.25 * n2, 1.0 + 0.5 * n2)
                up = u
                u = un
                if max(abs(q) for q in u) > 1e9:
                    blown = 1.0
                    break
        jp = _i(p["xp"] * nx)
        val = u[jp]
        exact = _pde_exact_at(p, jp * dx)
        ce = [_pde_exact_at(p, q) for q in xs]
        return _base(val, exact, nx, xs, ce, list(u), [jp * dx], [val], stab=stab, steps=float(n), blown=blown)


def _pde_exact(p: dict) -> float:
    nx = max(10, _i(p["n"]))
    return _pde_exact_at(p, _i(p["xp"] * nx) / nx)


# ============================================================================================ finite elements
class CrFem(_Base):
    """-u'' = f on (0, 1), u(0) = u(1) = 0, linear elements on n equal cells, load vector by 2-point Gauss."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "xp": 0.4}

    @staticmethod
    def _f(cas: int, x: float) -> float:
        if cas == 1:
            return 1.0
        return PI * PI * math.sin(PI * x)

    @staticmethod
    def exact_at(cas: int, x: float) -> float:
        if cas == 1:
            return 0.5 * x * (1.0 - x)
        return math.sin(PI * x)

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(2, _i(p["n"]))
        h = 1.0 / n
        g = 0.5773502691896257
        b = [0.0] * (n - 1)
        for e in range(n):
            x0 = e * h
            x1 = x0 + h
            xm = 0.5 * (x0 + x1)
            for gp in (-g, g):
                x = xm + gp * 0.5 * h
                f = CrFem._f(cas, x)
                w = 0.5 * h
                if e - 1 >= 0 and e - 1 < n - 1:       # node e is the left end of cell e: hat function phi_e
                    b[e - 1] += f * w * (x1 - x) / h
                if e < n - 1:                          # node e+1 is the right end of cell e
                    b[e] += f * w * (x - x0) / h
        m = n - 1
        a = [-1.0 / h] * m
        d = [2.0 / h] * m
        c = [-1.0 / h] * m
        u = [0.0] + _tri(a, d, c, b) + [0.0]
        xs = _grid(0.0, 1.0, n)
        xp = p["xp"]
        j = int(math.floor(xp / h))
        if j > n - 1:
            j = n - 1
        val = u[j] + (u[j + 1] - u[j]) * (xp - xs[j]) / h
        exact = CrFem.exact_at(cas, xp)
        cx = _grid(0.0, 1.0, 100)
        cy = []
        for q in cx:
            jj = int(math.floor(q / h))
            if jj > n - 1:
                jj = n - 1
            cy.append(u[jj] + (u[jj + 1] - u[jj]) * (q - xs[jj]) / h)
        return _base(val, exact, n, cx, [CrFem.exact_at(cas, q) for q in cx], cy, xs, u)


def _fem_exact(p: dict) -> float:
    return CrFem.exact_at(_i(p["cas"]), p["xp"])


# ============================================================================================ least squares
def _fit_design(cas: int, x: float) -> list[float]:
    if cas == 2:
        return [1.0, x, x * x]
    return [1.0, x]


class CrFit(_Base):
    """Straight line (equal or unequal errors) and a parabola fitted to seeded noisy data; the unknown is the
    slope (lines) or the curvature (parabola) the data were generated from."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 200.0, "seed": 4242.0, "a": 2.0, "b": 1.0, "c": -0.3,
              "sig": 0.5, "xmax": 10.0}

    @staticmethod
    def truth(p) -> float:
        return p["c"] if _i(p["cas"]) == 2 else p["a"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(5, _i(p["n"]))
        st = _lcg(p["seed"])
        xs, ys, sg = [], [], []
        for i in range(n):
            x = p["xmax"] * i / (n - 1)
            s = p["sig"] * (0.25 + 1.5 * x / p["xmax"]) if cas == 1 else p["sig"]
            y = p["b"] + p["a"] * x + (p["c"] * x * x if cas == 2 else 0.0) + s * _gauss(st)
            xs.append(x)
            ys.append(y)
            sg.append(s)
        m = 3 if cas == 2 else 2
        w = [1.0 / (s * s) if meth == 1 else 1.0 for s in sg]
        A = [[0.0] * m for _ in range(m)]
        bv = [0.0] * m
        for i in range(n):
            row = _fit_design(cas, xs[i])
            for r in range(m):
                bv[r] += w[i] * row[r] * ys[i]
                for q in range(m):
                    A[r][q] += w[i] * row[r] * row[q]
        beta = _solve(A, bv)
        rss = 0.0
        chi2 = 0.0
        for i in range(n):
            row = _fit_design(cas, xs[i])
            f = 0.0
            for r in range(m):
                f += beta[r] * row[r]
            rss += (ys[i] - f) * (ys[i] - f)
            chi2 += (ys[i] - f) * (ys[i] - f) / (sg[i] * sg[i])
        cov_diag = []
        for r in range(m):
            e = [0.0] * m
            e[r] = 1.0
            cov_diag.append(_solve(A, e)[r])
        scale = 1.0 if meth == 1 else rss / max(1, n - m)
        k = m - 1
        perr = math.sqrt(max(cov_diag[k] * scale, 0.0))
        val = beta[k]
        cx = _grid(0.0, p["xmax"], 60)

        def tr(x):
            return p["b"] + p["a"] * x + (p["c"] * x * x if cas == 2 else 0.0)

        def fit(x):
            row = _fit_design(cas, x)
            return sum(beta[r] * row[r] for r in range(m))

        stride = max(1, (n + 119) // 120)
        px = [xs[i] for i in range(0, n, stride)]
        py = [ys[i] for i in range(0, n, stride)]
        return _base(val, CrFit.truth(p), n, cx, [tr(x) for x in cx], [fit(x) for x in cx], px, py,
                     chi2r=chi2 / max(1, n - m), perr=perr)


def _fit_exact(p: dict) -> float:
    return CrFit.truth(p)


# ============================================================================================ maximum likelihood
def _golden_max(f, a: float, b: float, iters: int) -> float:
    gr = 0.6180339887498949
    c = b - gr * (b - a)
    d = a + gr * (b - a)
    fc = f(c)
    fd = f(d)
    for _ in range(iters):
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - gr * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + gr * (b - a)
            fd = f(d)
    return 0.5 * (a + b)


class CrMle(_Base):
    """Maximum-likelihood estimate by maximising ln L numerically: a Poisson mean, a Gaussian width, an
    exponential lifetime; with the Pearson chi-square of the fitted model."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 1000.0, "seed": 777.0, "lam": 4.0, "sg": 2.0, "mu": 10.0, "tau": 2.2}

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        N = max(10, _i(p["n"]))
        st = _lcg(p["seed"])
        NB = 20
        if cas == 0:
            lam = p["lam"]
            K = _i(lam + 4.0 * math.sqrt(lam)) + 2
            cnt = [0.0] * (K + 1)
            S1 = 0.0
            e0 = math.exp(-lam)
            for _ in range(N):
                u = _u(st)
                k = 0
                pk = e0
                cum = pk
                while u > cum and k < 200:
                    k += 1
                    pk = pk * lam / k
                    cum += pk
                S1 += k
                cnt[k if k < K else K] += 1.0
            est = _golden_max(lambda q: S1 * math.log(q) - N * q, 1e-3, 4.0 * (S1 / N + 1.0), 80)
            truth = lam

            def pmf(l):
                out = []
                pk = math.exp(-l)
                tot = 0.0
                for k in range(K):
                    out.append(pk)
                    tot += pk
                    pk = pk * l / (k + 1)
                out.append(max(1.0 - tot, 0.0))
                return out

            cx = [float(k) for k in range(K + 1)]
            ce = [N * q for q in pmf(truth)]
            pf = [N * q for q in pmf(est)]
            obs = cnt
        elif cas == 1:
            mu, sg = p["mu"], p["sg"]
            vals = [mu + sg * _gauss(st) for _ in range(N)]
            mean = 0.0
            for v in vals:
                mean += v
            mean /= N
            S2 = 0.0
            for v in vals:
                S2 += (v - mean) * (v - mean)
            est = _golden_max(lambda q: -N * math.log(q) - S2 / (2.0 * q * q), 1e-3, 5.0 * math.sqrt(S2 / N) + 1.0, 80)
            truth = sg
            lo, hi = mu - 4.0 * sg, mu + 4.0 * sg
            bw = (hi - lo) / NB
            obs = [0.0] * (NB + 2)
            for v in vals:
                j = int(math.floor((v - lo) / bw)) + 1
                obs[0 if j < 0 else (NB + 1 if j > NB else j)] += 1.0

            def cdf(q, m, s):
                return 0.5 * (1.0 + _erf((q - m) / (s * math.sqrt(2.0))))

            def binp(m, s):
                out = [cdf(lo, m, s)]
                for j in range(NB):
                    out.append(cdf(lo + (j + 1) * bw, m, s) - cdf(lo + j * bw, m, s))
                out.append(1.0 - cdf(hi, m, s))
                return out
            cx = [lo + (j - 0.5) * bw for j in range(NB + 2)]
            ce = [N * q for q in binp(mu, truth)]
            pf = [N * q for q in binp(mean, est)]
        else:
            tau = p["tau"]
            S1 = 0.0
            hi = 5.0 * tau
            bw = hi / NB
            obs = [0.0] * (NB + 1)
            for _ in range(N):
                u = _u(st)
                x = -tau * math.log(u if u > 1e-300 else 1e-300)
                S1 += x
                j = int(math.floor(x / bw))
                obs[j if j < NB else NB] += 1.0
            est = _golden_max(lambda q: -N * math.log(q) - S1 / q, 1e-3, 4.0 * (S1 / N + 1.0), 80)
            truth = tau

            def binp(t):
                out = []
                for j in range(NB):
                    out.append(math.exp(-j * bw / t) - math.exp(-(j + 1) * bw / t))
                out.append(math.exp(-hi / t))
                return out
            cx = [(j + 0.5) * bw for j in range(NB + 1)]
            ce = [N * q for q in binp(truth)]
            pf = [N * q for q in binp(est)]
        chi2 = 0.0
        nb = 0
        for j in range(len(obs)):
            if pf[j] > 5.0:
                chi2 += (obs[j] - pf[j]) * (obs[j] - pf[j]) / pf[j]
                nb += 1
        dof = max(1, nb - 2)
        return _base(est, truth, N, cx, ce, list(obs), cx, pf, chi2r=chi2 / dof, dof=float(dof))


def _mle_exact(p: dict) -> float:
    cas = _i(p["cas"])
    return p["lam"] if cas == 0 else (p["sg"] if cas == 1 else p["tau"])


# ============================================================================================ random deviates
def _norm_cdf_table(m: int, lim: float) -> tuple[list[float], list[float]]:
    xs = _grid(-lim, lim, m)
    return xs, [0.5 * (1.0 + _erf(q / math.sqrt(2.0))) for q in xs]


class CrDev(_Base):
    """Random numbers from a given distribution by the inverse transform and by acceptance-rejection."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 31415.0, "lam": 1.0, "xb": 1.0, "kb": 1.0}

    @staticmethod
    def _bin_pmf() -> list[float]:
        out = []
        for k in range(6):
            c = 1.0
            for i in range(1, k + 1):
                c = c * (5 - k + i) / i
            out.append(c * math.pow(0.3, k) * math.pow(0.7, 5 - k))
        return out

    @staticmethod
    def exact(p) -> float:
        cas = _i(p["cas"])
        if cas == 1:
            return _erf(p["xb"] / math.sqrt(2.0))
        if cas == 2:
            return CrDev._bin_pmf()[_i(p["kb"])]
        return 1.0 - math.exp(-p["lam"] * p["xb"])

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        N = max(100, _i(p["n"]))
        st = _lcg(p["seed"])
        lam = p["lam"]
        NB = 20
        trials = 0
        if cas == 2:
            pm = CrDev._bin_pmf()
            pmax = max(pm)
            cum = []
            c = 0.0
            for q in pm:
                c += q
                cum.append(c)
            obs = [0.0] * 6
            for _ in range(N):
                if meth == 0:
                    u = _u(st)
                    trials += 1
                    k = 0
                    while k < 5 and u > cum[k]:
                        k += 1
                else:
                    while True:
                        trials += 1
                        k = int(math.floor(_u(st) * 6.0))
                        if k > 5:
                            k = 5
                        if _u(st) * pmax < pm[k]:
                            break
                obs[k] += 1.0
            cx = [float(k) for k in range(6)]
            ce = [N * q for q in pm]
            val = obs[_i(p["kb"])] / N
        else:
            if cas == 1:
                lo, hi = -4.0, 4.0
                tx, tc = _norm_cdf_table(4000, 8.0)
            else:
                lo, hi = 0.0, 6.0 / lam
            bw = (hi - lo) / NB
            obs = [0.0] * NB
            inside = 0.0
            for _ in range(N):
                if cas == 0:
                    if meth == 0:
                        u = _u(st)
                        trials += 1
                        x = -math.log(u if u > 1e-300 else 1e-300) / lam
                    else:
                        while True:
                            trials += 1
                            x = _u(st) * 10.0 / lam
                            if _u(st) < math.exp(-lam * x):
                                break
                else:
                    if meth == 0:
                        u = _u(st)
                        trials += 1
                        a, b = 0, len(tx) - 1
                        while b - a > 1:
                            mid = (a + b) // 2
                            if tc[mid] <= u:
                                a = mid
                            else:
                                b = mid
                        x = tx[a] + (tx[b] - tx[a]) * (u - tc[a]) / (tc[b] - tc[a])
                    else:
                        while True:
                            trials += 1
                            x = -6.0 + 12.0 * _u(st)
                            if _u(st) < math.exp(-0.5 * x * x):
                                break
                if (cas == 1 and abs(x) < p["xb"]) or (cas == 0 and x < p["xb"]):
                    inside += 1.0
                j = int(math.floor((x - lo) / bw))
                if 0 <= j < NB:
                    obs[j] += 1.0
            val = inside / N
            cx = [lo + (j + 0.5) * bw for j in range(NB)]
            if cas == 1:
                ce = [N * 0.5 * (_erf((lo + (j + 1) * bw) / math.sqrt(2.0)) - _erf((lo + j * bw) / math.sqrt(2.0)))
                      for j in range(NB)]
            else:
                ce = [N * (math.exp(-lam * (lo + j * bw)) - math.exp(-lam * (lo + (j + 1) * bw))) for j in range(NB)]
        chi2 = 0.0
        nb = 0
        for j in range(len(obs)):
            if ce[j] > 5.0:
                chi2 += (obs[j] - ce[j]) * (obs[j] - ce[j]) / ce[j]
                nb += 1
        return _base(val, CrDev.exact(p), N, cx, ce, list(obs), [], [], chi2r=chi2 / max(1, nb - 1),
                     eff=N / max(trials, 1))


def _dev_exact(p: dict) -> float:
    return CrDev.exact(p)


# ============================================================================================ random walk
def _ret_prob(d: int, N: int) -> float:
    """Exact probability to be back at the origin after N steps (N even) on the d-dimensional cubic lattice."""
    if N % 2 == 1:
        return 0.0
    h = N // 2
    fact = [1.0]
    for i in range(1, N + 1):
        fact.append(fact[-1] * i)
    tot = 0.0

    def rec(k, left, acc):
        nonlocal tot
        if k == d - 1:
            tot += acc / (fact[left] * fact[left])
            return
        for a in range(left + 1):
            rec(k + 1, left - a, acc / (fact[a] * fact[a]))
    rec(0, h, fact[N])
    return tot / math.pow(2.0 * d, N)


class CrWalk(_Base):
    """Unit-step random walks on a d-dimensional cubic lattice: the mean square displacement and the return probability."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 4000.0, "seed": 2718.0, "dim": 2.0, "steps": 16.0}

    @staticmethod
    def exact(p) -> float:
        N = max(2, _i(p["steps"]))
        if _i(p["cas"]) == 1:
            return _ret_prob(max(1, _i(p["dim"])), N)
        return float(N)

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        W = max(10, _i(p["n"]))
        d = max(1, _i(p["dim"]))
        N = max(2, _i(p["steps"]))
        st = _lcg(p["seed"])
        r2m = [0.0] * (N + 1)
        home = 0.0
        path = [[0.0] * d]
        for w in range(W):
            pos = [0] * d
            for m in range(1, N + 1):
                k = int(math.floor(_u(st) * 2 * d))
                if k > 2 * d - 1:
                    k = 2 * d - 1
                pos[k // 2] += 1 if (k % 2) == 0 else -1
                r2 = 0
                for q in pos:
                    r2 += q * q
                r2m[m] += r2
                if w == 0:
                    path.append([float(q) for q in pos])
            if sum(abs(q) for q in pos) == 0:
                home += 1.0
        for m in range(N + 1):
            r2m[m] /= W
        val = home / W if cas == 1 else r2m[N]
        cx = [float(m) for m in range(N + 1)]
        if d >= 2:
            px = [q[0] for q in path]
            py = [q[1] for q in path]
        else:
            px = [float(m) for m in range(len(path))]
            py = [q[0] for q in path]
        return _base(val, CrWalk.exact(p), W, cx, [float(m) for m in range(N + 1)], r2m, px, py,
                     path_dim=float(min(d, 2)))


def _walk_exact(p: dict) -> float:
    return CrWalk.exact(p)


# ============================================================================================ decay chain
class CrDecay(_Base):
    """Monte Carlo decay of N0 nuclei: a single decay, a parent-daughter chain, and transient equilibrium."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 1234.0, "l1": 0.5, "l2": 1.5, "tend": 3.0}

    @staticmethod
    def _bateman(p, t: float) -> tuple[float, float]:
        l1, l2 = p["l1"], p["l2"]
        a = math.exp(-l1 * t)
        if abs(l2 - l1) < 1e-12:
            return a, l1 * t * a
        return a, l1 / (l2 - l1) * (a - math.exp(-l2 * t))

    @staticmethod
    def exact(p) -> float:
        cas = _i(p["cas"])
        a, b = CrDecay._bateman(p, p["tend"])
        if cas == 0:
            return a
        if cas == 1:
            return b
        return b / a

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        N = max(100, _i(p["n"]))
        st = _lcg(p["seed"])
        NT = 40
        tend = p["tend"]
        dtb = tend / NT
        d1 = [0.0] * (NT + 2)           # parents decaying in each time bin
        d2 = [0.0] * (NT + 2)           # daughters decaying in each time bin
        for _ in range(N):
            u = _u(st)
            t1 = -math.log(u if u > 1e-300 else 1e-300) / p["l1"]
            j1 = int(math.floor(t1 / dtb))
            d1[j1 if j1 <= NT else NT + 1] += 1.0
            if cas > 0:
                u = _u(st)
                t2 = t1 - math.log(u if u > 1e-300 else 1e-300) / p["l2"]
                j2 = int(math.floor(t2 / dtb))
                d2[j2 if j2 <= NT else NT + 1] += 1.0
        cx = [dtb * k for k in range(NT + 1)]
        parents, daughters = [], []
        c1 = 0.0
        c2 = 0.0
        for k in range(NT + 1):
            parents.append((N - c1) / N)
            daughters.append((c1 - c2) / N)
            c1 += d1[k]
            c2 += d2[k]
        ex = [CrDecay._bateman(p, t) for t in cx]
        if cas == 0:
            val = parents[NT]
            ce = [e[0] for e in ex]
            cy = parents
        elif cas == 1:
            val = daughters[NT]
            ce = [e[1] for e in ex]
            cy = daughters
        else:
            val = daughters[NT] / parents[NT] if parents[NT] > 0 else 0.0
            ce = [e[1] / e[0] for e in ex]
            cy = [daughters[k] / parents[k] if parents[k] > 0 else 0.0 for k in range(NT + 1)]
        return _base(val, CrDecay.exact(p), N, cx, ce, cy, [cx[NT]], [val], parent_frac=parents[NT],
                     daughter_frac=daughters[NT])


def _decay_exact(p: dict) -> float:
    return CrDecay.exact(p)


# ============================================================================================ two-level spins
class CrTwoLevel(_Base):
    """N independent two-level spins in a field (Metropolis): magnetisation tanh(x) and specific heat x^2 sech^2(x),
    x = mu B / kT."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 4000.0, "seed": 9001.0, "x": 1.0, "ns": 40.0}

    @staticmethod
    def exact_at(cas: int, x: float) -> float:
        if cas == 1:
            ch = math.cosh(x)
            return x * x / (ch * ch)
        return math.tanh(x)

    @staticmethod
    def _run(cas: int, x: float, ns: int, sweeps: int, st: list[float]) -> tuple[float, list[float]]:
        s = [1.0] * ns
        burn = sweeps // 5 + 50
        for _ in range(burn):
            for j in range(ns):
                dE = 2.0 * s[j] * x
                if dE <= 0.0 or _u(st) < math.exp(-dE):
                    s[j] = -s[j]
        sm = 0.0
        se = 0.0
        se2 = 0.0
        for _ in range(sweeps):
            for j in range(ns):
                dE = 2.0 * s[j] * x
                if dE <= 0.0 or _u(st) < math.exp(-dE):
                    s[j] = -s[j]
            tot = 0.0
            for j in range(ns):
                tot += s[j]
                e = -s[j] * x
                se += e
                se2 += e * e
            sm += tot / ns
        m = sm / sweeps
        cnt = float(sweeps * ns)
        c = se2 / cnt - (se / cnt) * (se / cnt)
        return (c if cas == 1 else m), s

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        ns = max(4, _i(p["ns"]))
        sw = max(100, _i(p["n"]))
        st = _lcg(p["seed"])
        val, spins = CrTwoLevel._run(cas, p["x"], ns, sw, st)
        xs = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
        px, py = [], []
        for xv in xs:
            v, _ = CrTwoLevel._run(cas, xv, ns, sw // 6 + 20, st)
            px.append(xv)
            py.append(v)
        cx = _grid(0.0, 3.2, 64)
        ce = [CrTwoLevel.exact_at(cas, q) for q in cx]
        return _base(val, CrTwoLevel.exact_at(cas, p["x"]), sw, cx, ce, [], px, py, lat=list(spins), lw=float(ns),
                     lh=1.0)


def _two_exact(p: dict) -> float:
    return CrTwoLevel.exact_at(_i(p["cas"]), p["x"])


# ============================================================================================ Monte Carlo integration
class CrMcInt(_Base):
    """Hit-or-miss, sample-mean and importance-sampling Monte Carlo integration, with the standard error N^-1/2."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 24680.0}

    @staticmethod
    def exact(p) -> float:
        if _i(p["cas"]) == 1:
            return 0.5 * math.sqrt(PI) * _erf(1.0)
        return 2.0

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        N = max(10, _i(p["n"]))
        st = _lcg(p["seed"])
        marks = _marks(N)
        mi = 0
        run = []
        hit = 0.0
        tot = 0.0
        sq = 0.0
        if cas == 1:
            a, b, top = 0.0, 1.0, 1.0
        else:
            a, b, top = 0.0, PI, 1.0
        area = (b - a) * top
        c1 = 1.0 - math.exp(-1.0)
        est = 0.0
        for i in range(1, N + 1):
            if meth == 0:
                x = a + (b - a) * _u(st)
                y = top * _u(st)
                f = math.exp(-x * x) if cas == 1 else math.sin(x)
                if y <= f:
                    hit += 1.0
                est = area * hit / i
            else:
                if meth == 1:
                    x = a + (b - a) * _u(st)
                    g = (b - a) * (math.exp(-x * x) if cas == 1 else math.sin(x))
                elif cas == 1:
                    x = -math.log(1.0 - _u(st) * c1)
                    g = c1 * math.exp(x - x * x)
                else:
                    u = _u(st)
                    if u < 0.5:
                        x = PI * math.sqrt(u / 2.0)
                        pdf = 4.0 * x / (PI * PI)
                    else:
                        x = PI * (1.0 - math.sqrt((1.0 - u) / 2.0))
                        pdf = 4.0 * (PI - x) / (PI * PI)
                    g = math.sin(x) / pdf if pdf > 1e-300 else 0.0
                tot += g
                sq += g * g
                est = tot / i
            while mi < len(marks) and marks[mi] == i:
                run.append(est)
                mi += 1
        if meth == 0:
            ph = hit / N
            se = area * math.sqrt(max(ph * (1.0 - ph), 0.0) / N)
        else:
            mean = tot / N
            var = sq / N - mean * mean
            se = math.sqrt(max(var, 0.0) / N)
        cx = [float(q) for q in marks]
        ex = CrMcInt.exact(p)
        return _base(est, ex, N, cx, [ex for _ in cx], run, [cx[-1]], [est], se=se)


def _mcint_exact(p: dict) -> float:
    return CrMcInt.exact(p)


# ============================================================================================ scattering
class CrScatter(_Base):
    """Classical scattering by random impact parameters: hard sphere (isotropic) and Rutherford."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 50000.0, "seed": 8128.0, "a": 1.0, "R": 1.5, "thmin": 1.0471975511965976,
              "what": 0.0}

    @staticmethod
    def exact(p) -> float:
        cas, w = _i(p["cas"]), _i(p["what"])
        if cas == 0:
            return PI * p["a"] * p["a"] if w == 0 else 0.5
        b0 = 0.5 * p["a"] / math.tan(0.5 * p["thmin"])
        return PI * b0 * b0

    @staticmethod
    def init(p, cfg=None):
        cas, w = _i(p["cas"]), _i(p["what"])
        N = max(100, _i(p["n"]))
        st = _lcg(p["seed"])
        a, R = p["a"], p["R"]
        NB = 20
        obs = [0.0] * NB
        cmin = math.cos(p["thmin"])
        nhit = 0.0
        nback = 0.0
        ncut = 0.0
        for _ in range(N):
            b2 = R * R * _u(st)
            if cas == 0:
                if b2 < a * a:
                    nhit += 1.0
                    c = 2.0 * b2 / (a * a) - 1.0
                else:
                    continue
            else:
                q = 0.25 * a * a
                c = (b2 - q) / (b2 + q)
                nhit += 1.0
                if c < cmin:
                    ncut += 1.0
            if c < 0.0:
                nback += 1.0
            j = int(math.floor((c + 1.0) * 0.5 * NB))
            obs[j if j < NB else NB - 1] += 1.0
        if cas == 0:
            val = PI * R * R * nhit / N if w == 0 else nback / max(nhit, 1.0)
        else:
            val = PI * R * R * ncut / N
        cx = [-1.0 + (j + 0.5) * 2.0 / NB for j in range(NB)]
        ce = []
        for j in range(NB):
            lo = -1.0 + j * 2.0 / NB
            hi = lo + 2.0 / NB
            if cas == 0:
                ce.append(N * (a * a / (R * R)) / NB)
            else:
                q = 0.25 * a * a
                f = lambda c: min(1.0, q * (1.0 + c) / (1.0 - c + 1e-300) / (R * R)) if c < 1.0 else 1.0
                ce.append(N * (f(hi) - f(lo)))
        return _base(val, CrScatter.exact(p), N, cx, ce, list(obs), [], [], nhit=nhit)


def _scatter_exact(p: dict) -> float:
    return CrScatter.exact(p)


# ============================================================================================ polynomial roots
def _horner(co: list[float], x: float) -> float:
    r = 0.0
    for k in range(len(co) - 1, -1, -1):
        r = r * x + co[k]
    return r


def _dhorner(co: list[float], x: float) -> float:
    r = 0.0
    for k in range(len(co) - 1, 0, -1):
        r = r * x + k * co[k]
    return r


def _poly_co(cas: int) -> list[float]:
    if cas == 1:
        return [-5.0, -2.0, 0.0, 1.0]
    if cas == 2:
        return [2.0, -3.0, 0.0, 1.0]
    return [-6.0, 11.0, -6.0, 1.0]


def _poly_root(cas: int) -> float:
    if cas == 1:                                   # Cardano: t^3 + p t + q = 0, one real root
        D = math.sqrt(6.25 - 8.0 / 27.0)
        return math.pow(2.5 + D, 1.0 / 3.0) + math.pow(2.5 - D, 1.0 / 3.0)
    if cas == 2:
        return 1.0
    return 3.0


class CrPoly(_Base):
    """A root of a polynomial by bisection, Newton-Raphson and the secant method (or, for a double root, by Newton,
    modified Newton and the secant method)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "xa": 2.5, "xb": 3.5, "x0": 3.4, "x1": 3.3, "gx0": 0.5, "gx1": 3.6}

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(1, _i(p["n"]))
        co = _poly_co(cas)
        f = lambda q: _horner(co, q)
        it = []
        if cas != 2 and meth == 0:
            a, b = p["xa"], p["xb"]
            fa = f(a)
            for _ in range(n):
                mid = 0.5 * (a + b)
                fm = f(mid)
                it.append(mid)
                if (fm < 0) == (fa < 0):
                    a, fa = mid, fm
                else:
                    b = mid
        elif (cas != 2 and meth == 1) or (cas == 2 and meth <= 1):
            mult = 2.0 if (cas == 2 and meth == 1) else 1.0
            x = p["x0"]
            for _ in range(n):
                d = _dhorner(co, x)
                if abs(d) < 1e-14:
                    break
                x = x - mult * f(x) / d
                it.append(x)
        else:
            x0, x1 = p["x0"], p["x1"]
            f0, f1 = f(x0), f(x1)
            for _ in range(n):
                if abs(f1 - f0) < 1e-14:
                    break
                x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
                x0, f0, x1, f1 = x1, f1, x2, f(x2)
                it.append(x1)
        val = it[-1] if it else p["x0"]
        exact = _poly_root(cas)
        cx = _grid(p["gx0"], p["gx1"], 80)
        return _base(val, exact, len(it), cx, [f(q) for q in cx], [], list(it), [f(q) for q in it])


def _poly_exact(p: dict) -> float:
    return _poly_root(_i(p["cas"]))


# ============================================================================================ photons in a slab
class CrPhoton(_Base):
    """Monte Carlo photon transport through an infinite slab (normal incidence, isotropic scattering)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 5551.0, "d": 2.0, "mus": 0.6, "mua": 0.15}

    @staticmethod
    def exact(p) -> float:
        cas = _i(p["cas"])
        mut = p["mus"] + p["mua"]
        e = math.exp(-mut * p["d"])
        if cas == 0:
            return e
        if cas == 1:
            return p["mus"] / mut
        return (1.0 / mut - (p["d"] + 1.0 / mut) * e) / (1.0 - e)

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        N = max(100, _i(p["n"]))
        st = _lcg(p["seed"])
        d = p["d"]
        mut = p["mus"] + p["mua"]
        pabs = p["mua"] / mut
        NB = 20
        first = [0.0] * NB
        dose = [0.0] * NB
        prim = 0.0
        ninter = 0.0
        nscat1 = 0.0
        zsum = 0.0
        T = 0.0
        Rf = 0.0
        Af = 0.0
        for _ in range(N):
            z = 0.0
            uz = 1.0
            nsc = 0
            firstev = True
            for _s in range(10000):
                u = _u(st)
                s = -math.log(u if u > 1e-300 else 1e-300) / mut
                z = z + uz * s
                if z < 0.0:
                    Rf += 1.0
                    break
                if z > d:
                    T += 1.0
                    if nsc == 0:
                        prim += 1.0
                    break
                j = int(math.floor(z / d * NB))
                if firstev:
                    firstev = False
                    first[j if j < NB else NB - 1] += 1.0
                    ninter += 1.0
                    zsum += z
                if _u(st) < pabs:
                    Af += 1.0
                    dose[j if j < NB else NB - 1] += 1.0
                    break
                if nsc == 0:
                    nscat1 += 1.0
                nsc += 1
                uz = 2.0 * _u(st) - 1.0
        if cas == 0:
            val = prim / N
        elif cas == 1:
            val = nscat1 / max(ninter, 1.0)
        else:
            val = zsum / max(ninter, 1.0)
        bw = d / NB
        cx = [(j + 0.5) * bw for j in range(NB)]
        ce = [N * (math.exp(-mut * j * bw) - math.exp(-mut * (j + 1) * bw)) for j in range(NB)]
        return _base(val, CrPhoton.exact(p), N, cx, ce, list(first), [], [], cy2=list(dose),
                     Tf=T / N, Rf=Rf / N, Af=Af / N, prim=prim / N)


def _photon_exact(p: dict) -> float:
    return CrPhoton.exact(p)


# ============================================================================================ Ising model
TC2 = 2.0 / math.log(1.0 + math.sqrt(2.0))


def _ellipk(k: float) -> float:
    """Complete elliptic integral of the first kind K(k) by the arithmetic-geometric mean."""
    a, b = 1.0, math.sqrt(max(1.0 - k * k, 0.0))
    for _ in range(40):
        a, b = 0.5 * (a + b), math.sqrt(a * b)
        if abs(a - b) < 1e-15:
            break
    return PI / (2.0 * a)


def _ising_e1(T: float, L: int) -> float:
    t = math.tanh(1.0 / T)
    return -(t + math.pow(t, L - 1)) / (1.0 + math.pow(t, L))


def _ising_e2(T: float) -> float:
    K = 1.0 / T
    s2 = math.sinh(2.0 * K)
    c2 = math.cosh(2.0 * K)
    k = 2.0 * s2 / (c2 * c2)
    th = s2 / c2
    return -(c2 / s2) * (1.0 + (2.0 / PI) * (2.0 * th * th - 1.0) * _ellipk(k))


def _ising_m2(T: float) -> float:
    s2 = math.sinh(2.0 / T)
    if s2 <= 1.0:
        return 0.0
    return math.pow(1.0 - math.pow(s2, -4.0), 0.125)


def _ising_c(ef, T: float) -> float:
    h = 1e-5
    return (ef(T + h) - ef(T - h)) / (2.0 * h)


def _ising_exact(p: dict) -> float:
    d = _i(p["dim"])
    w = _i(p["what"])
    T = p["T"]
    L = max(4, _i(p["L"]))
    if d == 1:
        if w == 1:
            return _ising_e1(T, L)
        if w == 2:
            return _ising_c(lambda q: _ising_e1(q, L), T)
        return 0.0
    if w == 0:
        return _ising_m2(T)
    if w == 1:
        return _ising_e2(T)
    return _ising_c(_ising_e2, T)


def _ising_sim(d: int, L: int, T: float, meth: int, sweeps: int, st: list[float], marks: list[int] | None = None,
               what: int = 0) -> dict:
    """Run the simulation; returns the averages of |m|, m^2, m^4, e, e^2 and the final lattice."""
    N = L if d == 1 else L * L
    nbr = []
    for i in range(N):
        if d == 1:
            nbr.append([(i + 1) % L, (i - 1) % L])
        else:
            x = i % L
            y = i // L
            nbr.append([y * L + (x + 1) % L, y * L + (x - 1) % L, ((y + 1) % L) * L + x, ((y - 1) % L) * L + x])
    s = [1] * N
    padd = 1.0 - math.exp(-2.0 / T)
    burn = sweeps // 5 + 30
    ncl = [1]                                    # cluster flips per Wolff sweep (fixed after the burn-in)

    def cluster():
        seed = int(math.floor(_u(st) * N))
        if seed > N - 1:
            seed = N - 1
        sp = s[seed]
        s[seed] = -sp
        stack = [seed]
        size = 1
        while stack:
            i = stack.pop()
            for j in nbr[i]:
                if s[j] == sp and _u(st) < padd:
                    s[j] = -sp
                    stack.append(j)
                    size += 1
        return size

    def sweep():
        if meth == 0:                            # N single-site trials at random sites
            for _ in range(N):
                i = int(math.floor(_u(st) * N))
                if i > N - 1:
                    i = N - 1
                tot = 0
                for j in nbr[i]:
                    tot += s[j]
                dE = 2 * s[i] * tot
                if dE <= 0 or _u(st) < math.exp(-dE / T):
                    s[i] = -s[i]
        else:
            for _ in range(ncl[0]):
                cluster()

    if meth == 1:                                # burn-in: learn the mean cluster size, then keep it fixed
        flips = 0
        cnt = 0
        for _ in range(burn):
            done = 0
            while done < N:
                sz = cluster()
                done += sz
                flips += sz
                cnt += 1
        ncl[0] = max(1, _i(N * cnt / max(flips, 1)))
    else:
        for _ in range(burn):
            sweep()
    am = 0.0
    m2 = 0.0
    m4 = 0.0
    se = 0.0
    se2 = 0.0
    run = []
    mi = 0
    for k in range(1, sweeps + 1):
        sweep()
        M = 0
        for q in s:
            M += q
        m = M / N
        bond = 0
        for i in range(N):
            bond += s[i] * (s[nbr[i][0]] if d == 1 else s[nbr[i][0]] + s[nbr[i][2]])
        e = -bond / N
        am += abs(m)
        m2 += m * m
        m4 += m * m * m * m
        se += e
        se2 += e * e
        if marks is not None:
            if what == 0:
                est = am / k
            elif what == 1:
                est = se / k
            else:
                mean = se / k
                est = N * (se2 / k - mean * mean) / (T * T)
            while mi < len(marks) and marks[mi] == k:
                run.append(est)
                mi += 1
    n = float(sweeps)
    e1 = se / n
    return {"am": am / n, "m2": m2 / n, "m4": m4 / n, "e": e1, "C": N * (se2 / n - e1 * e1) / (T * T),
            "lat": [float(q) for q in s], "run": run, "N": N}


class CrIsing(_Base):
    """The Ising model by Metropolis or Wolff cluster updates, in 1-D (exact transfer matrix) and 2-D (Onsager)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 1000.0, "seed": 60221.0, "dim": 2.0, "L": 16.0, "T": 1.8, "what": 0.0}

    @staticmethod
    def init(p, cfg=None):
        d = _i(p["dim"])
        L = max(4, _i(p["L"]))
        n = max(20, _i(p["n"]))
        w = _i(p["what"])
        st = _lcg(p["seed"])
        marks = _marks(n)
        r = _ising_sim(d, L, p["T"], _i(p["method"]), n, st, marks, w)
        val = r["am"] if w == 0 else (r["e"] if w == 1 else r["C"])
        ex = _ising_exact(p)
        cx = [float(q) for q in marks]
        return _base(val, ex, n, cx, [ex for _ in cx], r["run"], [cx[-1]], [val], lat=r["lat"],
                     lw=float(L), lh=float(1 if d == 1 else L), m2=r["m2"], m4=r["m4"],
                     am=r["am"], en=r["e"], cv=r["C"])


# ============================================================================================ Binder cumulant crossing
class CrBinder(_Base):
    """The 2-D Ising critical temperature from the crossing of the Binder cumulants of two lattice sizes."""

    PARAMS = {"cas": 0.0, "method": 1.0, "n": 600.0, "seed": 1066.0, "L1": 8.0, "L2": 16.0, "Tlo": 2.1,
              "Thi": 2.45, "nT": 6.0}

    @staticmethod
    def init(p, cfg=None):
        n = max(20, _i(p["n"]))
        nT = max(3, _i(p["nT"]))
        meth = _i(p["method"])
        st = _lcg(p["seed"])
        Ts = _grid(p["Tlo"], p["Thi"], nT - 1)
        U1, U2 = [], []
        lat = []
        for T in Ts:
            for L, U in ((_i(p["L1"]), U1), (_i(p["L2"]), U2)):
                r = _ising_sim(2, L, T, meth, n, st)
                U.append(1.0 - r["m4"] / (3.0 * r["m2"] * r["m2"]) if r["m2"] > 0 else 0.0)
                lat = r["lat"]
                lw = float(L)
        val = Ts[nT // 2]
        found = 0.0
        for k in range(nT - 1):
            d0 = U2[k] - U1[k]
            d1 = U2[k + 1] - U1[k + 1]
            if d0 > 0.0 and d1 <= 0.0:
                val = Ts[k] + (Ts[k + 1] - Ts[k]) * d0 / (d0 - d1)
                found = 1.0
                break
        if found == 0.0:
            val = Ts[0] if U2[0] - U1[0] <= 0.0 else Ts[nT - 1]
        return _base(val, TC2, n, Ts, [], U1, [val], [0.0], cy2=U2, lat=lat, lw=lw, lh=lw, vline=TC2,
                     found=found)


def _binder_exact(p: dict) -> float:
    return TC2


# ============================================================================================ tight binding
def _jacobi_eig(a: list[list[float]]) -> list[float]:
    """Eigenvalues of a real symmetric matrix by cyclic Jacobi rotations (sorted, ascending)."""
    n = len(a)
    a = [list(r) for r in a]
    for _sw in range(60):
        off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                off += a[i][j] * a[i][j]
        if off < 1e-26:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) < 1e-14:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = (1.0 if theta >= 0.0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp = a[k][p]
                    akq = a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk = a[p][k]
                    aqk = a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return sorted(a[i][i] for i in range(n))


def _tb_ring(N: int, t: float) -> list[list[float]]:
    H = [[0.0] * N for _ in range(N)]
    for i in range(N):
        H[i][(i + 1) % N] -= t
        H[(i + 1) % N][i] -= t
    return H


def _tb_torus(L: int, t: float) -> list[list[float]]:
    N = L * L
    H = [[0.0] * N for _ in range(N)]
    for y in range(L):
        for x in range(L):
            i = y * L + x
            for j in (y * L + (x + 1) % L, ((y + 1) % L) * L + x):
                H[i][j] -= t
                H[j][i] -= t
    return H


def _graphene_fk(kx: float, ky: float) -> tuple[float, float]:
    """f(k) = 1 + e^(i k.a1) + e^(i k.a2) with k.a1 = kx, k.a2 = ky (fractional coordinates)."""
    return 1.0 + math.cos(kx) + math.cos(ky), math.sin(kx) + math.sin(ky)


def _graphene_bands(kx: float, ky: float, t: float) -> list[float]:
    re, im = _graphene_fk(kx, ky)
    H = [[0.0, 0.0, -t * re, t * im], [0.0, 0.0, -t * im, -t * re],
         [-t * re, -t * im, 0.0, 0.0], [t * im, -t * re, 0.0, 0.0]]
    ev = _jacobi_eig(H)
    return [ev[0], ev[3]]


def _sq_dos_bin(t: float, lo: float, hi: float) -> float:
    tot = 0.0
    m = 40
    for q in range(m):
        e = lo + (hi - lo) * (q + 0.5) / m
        x = abs(e) / (4.0 * t)
        if x >= 1.0:
            continue
        tot += _ellipk(math.sqrt(1.0 - x * x)) / (2.0 * PI * PI * t) * (hi - lo) / m
    return tot


def _tb_gs(t: float, ev: list[float], N: int) -> float:
    s = 0.0
    for k in range(N // 2):
        s += 2.0 * ev[k]
    return s / N


class CrTb(_Base):
    """Tight-binding bands: a periodic chain and a periodic square cluster by Jacobi diagonalisation of the real-space
    Hamiltonian; graphene by diagonalising the Bloch Hamiltonian on a k mesh."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 16.0, "t": 1.0, "what": 0.0}

    @staticmethod
    def exact(p) -> float:
        cas, w, t = _i(p["cas"]), _i(p["what"]), p["t"]
        if w == 1:
            return -4.0 * t / PI if cas == 0 else -16.0 * t / (PI * PI)
        return (4.0, 8.0, 6.0)[cas] * t

    @staticmethod
    def init(p, cfg=None):
        cas, w, t = _i(p["cas"]), _i(p["what"]), p["t"]
        n = max(4, _i(p["n"]))
        NBIN = 24
        if cas == 0:
            ev = _jacobi_eig(_tb_ring(n, t))
            N = n
        elif cas == 1:
            ev = _jacobi_eig(_tb_torus(n, t))
            N = n * n
        else:
            ev = []
            for a in range(n):
                for b in range(n):
                    ev.extend(_graphene_bands(2 * PI * a / n, 2 * PI * b / n, t))
            ev.sort()
            N = 2 * n * n
        if w == 1:
            val = _tb_gs(t, ev, N)
        else:
            val = ev[-1] - ev[0]
        Emax = (2.0, 4.0, 3.0)[cas] * t
        bw = 2.0 * Emax / NBIN
        cnt = [0.0] * NBIN
        for e in ev:
            j = int(math.floor((e + Emax) / bw))
            cnt[0 if j < 0 else (NBIN - 1 if j >= NBIN else j)] += 1.0
        cx = [-Emax + (j + 0.5) * bw for j in range(NBIN)]
        cy = [c / (len(ev) * bw) for c in cnt]
        ce = []
        if cas == 0:
            for j in range(NBIN):
                lo = max(-1.0, min(1.0, (-Emax + j * bw) / (2.0 * t)))
                hi = max(-1.0, min(1.0, (-Emax + (j + 1) * bw) / (2.0 * t)))
                ce.append((math.asin(hi) - math.asin(lo)) / PI / bw)
        elif cas == 1:
            for j in range(NBIN):
                ce.append(_sq_dos_bin(t, -Emax + j * bw, -Emax + (j + 1) * bw) / bw)
        # the band structure along a path, exact and from the diagonalisation
        NK = 60
        bk = [i / NK for i in range(NK + 1)]
        e1, e2, n1, n2 = [], [], [], []
        for i in range(NK + 1):
            u = bk[i]
            if cas == 0:
                k = -PI + 2.0 * PI * u
                e1.append(-2.0 * t * math.cos(k))
                n1.append(_jacobi_eig([[-2.0 * t * math.cos(k)]])[0])
            elif cas == 1:                      # Gamma - X - M - Gamma
                if u < 1.0 / 3.0:
                    kx, ky = PI * 3.0 * u, 0.0
                elif u < 2.0 / 3.0:
                    kx, ky = PI, PI * (3.0 * u - 1.0)
                else:
                    kx = PI * (3.0 - 3.0 * u)
                    ky = kx
                e1.append(-2.0 * t * (math.cos(kx) + math.cos(ky)))
                n1.append(_jacobi_eig([[-2.0 * t * (math.cos(kx) + math.cos(ky))]])[0])
            else:                               # Gamma - M - K - Gamma in fractional coordinates
                if u < 1.0 / 3.0:
                    kx, ky = PI * 3.0 * u, 0.0
                elif u < 2.0 / 3.0:
                    kx, ky = PI + (2.0 * PI / 3.0 - PI) * (3.0 * u - 1.0), (2.0 * PI / 3.0) * (3.0 * u - 1.0)
                else:
                    f = 3.0 - 3.0 * u
                    kx, ky = 2.0 * PI / 3.0 * f, 2.0 * PI / 3.0 * f
                re, im = _graphene_fk(kx, ky)
                r = math.sqrt(re * re + im * im)
                e1.append(t * r)
                e2.append(-t * r)
                b = _graphene_bands(kx, ky, t)
                n1.append(b[1])
                n2.append(b[0])
        return _base(val, CrTb.exact(p), n, cx, ce, cy, [], [], bk=bk, be1=e1, be2=e2, bn1=n1, bn2=n2,
                     nlevels=float(len(ev)))


def _tb_exact(p: dict) -> float:
    return CrTb.exact(p)


# ============================================================================================ Schrodinger equation
def _fft(re: list[float], im: list[float], inv: bool) -> None:
    """In-place radix-2 FFT (length a power of two); inv gives the unnormalised inverse transform."""
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
        ang = 2.0 * PI / ln * (1.0 if inv else -1.0)
        wr = math.cos(ang)
        wi = math.sin(ang)
        for i in range(0, n, ln):
            cr, ci = 1.0, 0.0
            for k in range(ln // 2):
                a = i + k
                b = a + ln // 2
                tr = re[b] * cr - im[b] * ci
                ti = re[b] * ci + im[b] * cr
                re[b] = re[a] - tr
                im[b] = im[a] - ti
                re[a] += tr
                im[a] += ti
                cr, ci = cr * wr - ci * wi, cr * wi + ci * wr
        ln <<= 1


def _numerov_nodes(kfun, h: float, n: int, u1: float) -> tuple[int, list[float]]:
    """Integrate u'' = -k(x) u from u0 = 0, u1 given; count the sign changes."""
    u = [0.0] * (n + 1)
    u[1] = u1
    h2 = h * h / 12.0
    km = kfun(0)
    kc = kfun(1)
    nodes = 0
    for i in range(1, n):
        kp = kfun(i + 1)
        u[i + 1] = (2.0 * (1.0 - 5.0 * h2 * kc) * u[i] - (1.0 + h2 * km) * u[i - 1]) / (1.0 + h2 * kp)
        if u[i + 1] * u[i] < 0.0:
            nodes += 1
        km, kc = kc, kp
    return nodes, u


class CrSchro(_Base):
    """Eigenvalues of the 1-D Schrodinger equation: shooting with the Numerov method (node counting + bisection) and
    imaginary-time split-step Fourier. cas 0 harmonic oscillator, 1 infinite well, 2 hydrogen radial (atomic units)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 400.0, "lev": 0.0, "ell": 0.0}

    @staticmethod
    def exact(p) -> float:
        cas, lev = _i(p["cas"]), _i(p["lev"])
        if cas == 1:
            return (lev + 1) * (lev + 1) * PI * PI / 2.0
        if cas == 2:
            nn = lev + _i(p["ell"]) + 1
            return -1.0 / (2.0 * nn * nn)
        return lev + 0.5

    @staticmethod
    def _shoot(cas: int, lev: int, ell: int, n: int):
        if cas == 0:
            xm = 8.0
            h = 2.0 * xm / n
            lo, hi = 0.0, lev + 3.0
            kf = lambda E: (lambda i: 2.0 * (E - 0.5 * (-xm + i * h) * (-xm + i * h)))
            u1 = 1e-6
        elif cas == 1:
            h = 1.0 / n
            lo, hi = 0.0, (lev + 2) * (lev + 2) * PI * PI / 2.0
            kf = lambda E: (lambda i: 2.0 * E)
            u1 = h
        else:
            rm = 40.0 + 6.0 * lev
            h = rm / n
            nn = lev + ell + 1
            lo, hi = -1.0 / (2.0 * max(nn - 1, 1) * max(nn - 1, 1)) if nn > 1 else -0.6, -1.0 / (2.0 * (nn + 2) * (nn + 2))
            lo = -0.6
            hi = -0.5 / ((lev + ell + 3) * (lev + ell + 3))
            L2 = ell * (ell + 1)

            def kf(E):
                def kk(i):
                    r = i * h
                    if i == 0:
                        return 0.0
                    return 2.0 * (E + 1.0 / r) - L2 / (r * r)
                return kk
            u1 = math.pow(h, ell + 1)
        nit = 0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            nodes, _u = _numerov_nodes(kf(mid), h, n, u1)
            if nodes > lev:
                hi = mid
            else:
                lo = mid
            nit += 1
        E = 0.5 * (lo + hi)
        nodes, u = _numerov_nodes(kf(E), h, n, u1)
        if cas == 0:
            xs = [-xm + i * h for i in range(n + 1)]
        elif cas == 1:
            xs = [i * h for i in range(n + 1)]
        else:
            xs = [i * h for i in range(n + 1)]
        return E, xs, u

    @staticmethod
    def _split(lev: int, n: int, dtau: float):
        Ng = 64
        Lh = 7.0
        dx = 2.0 * Lh / Ng
        xs = [-Lh + i * dx for i in range(Ng)]
        V = [0.5 * q * q for q in xs]
        ks = []
        for i in range(Ng):
            kk = i if i < Ng // 2 else i - Ng
            ks.append(2.0 * PI * kk / (Ng * dx))
        eV = [math.exp(-0.5 * dtau * v) for v in V]
        eT = [math.exp(-0.5 * dtau * k * k) for k in ks]
        found = []
        E = 0.0
        psi = []
        for ll in range(lev + 1):
            re = [math.exp(-0.5 * q * q * 0.3) * (1.0 + 0.3 * q * (ll + 1) + 0.1 * q * q * q * (ll % 2)) for q in xs]
            im = [0.0] * Ng
            for _ in range(n):
                re = [re[i] * eV[i] for i in range(Ng)]
                im = [im[i] * eV[i] for i in range(Ng)]
                _fft(re, im, False)
                re = [re[i] * eT[i] for i in range(Ng)]
                im = [im[i] * eT[i] for i in range(Ng)]
                _fft(re, im, True)
                re = [re[i] / Ng * eV[i] for i in range(Ng)]
                im = [im[i] / Ng * eV[i] for i in range(Ng)]
                for f in found:
                    ov = 0.0
                    for i in range(Ng):
                        ov += f[i] * re[i] * dx
                    re = [re[i] - ov * f[i] for i in range(Ng)]
                nrm = 0.0
                for i in range(Ng):
                    nrm += re[i] * re[i] * dx
                nrm = math.sqrt(nrm)
                re = [q / nrm for q in re]
            # <H> = <T> + <V>
            r2 = list(re)
            i2 = [0.0] * Ng
            _fft(r2, i2, False)
            T = 0.0
            tot = 0.0
            for i in range(Ng):
                w = r2[i] * r2[i] + i2[i] * i2[i]
                T += 0.5 * ks[i] * ks[i] * w
                tot += w
            T /= tot
            Vv = 0.0
            for i in range(Ng):
                Vv += V[i] * re[i] * re[i] * dx
            E = T + Vv
            found.append(re)
            psi = re
        return E, xs, psi, V

    @staticmethod
    def init(p, cfg=None):
        cas, meth, lev, ell = _i(p["cas"]), _i(p["method"]), _i(p["lev"]), _i(p["ell"])
        n = max(8, _i(p["n"]))
        ex = CrSchro.exact(p)
        if cas == 0 and meth == 1:
            E, xs, psi, V = CrSchro._split(lev, n, 0.04)
            scale = 1.0
            cy = [E + 0.6 * q for q in psi]
            ce = V
            cx = xs
        else:
            E, xs, u = CrSchro._shoot(cas, lev, ell, n)
            nrm = 0.0
            hh = xs[1] - xs[0]
            for q in u:
                nrm += q * q * hh
            nrm = math.sqrt(nrm)
            sgn = 1.0
            u = [q / nrm for q in u]
            if cas == 0:
                ce = [0.5 * q * q for q in xs]
                cy = [E + 0.6 * q for q in u]
            elif cas == 1:
                ce = [0.0 for _ in xs]
                cy = [E + 0.5 * ex / 3.0 * q / 1.5 for q in u]
            else:
                ce = [(-1.0 / q if q > 0 else 0.0) + ell * (ell + 1) / (2.0 * q * q) if q > 0.2 else 0.0 for q in xs]
                cy = [E + 0.25 * q for q in u]
            cx = xs
        return _base(E, ex, n, cx, ce, cy, [cx[0], cx[-1]], [E, E], hl1=E, hl2=ex)


def _schro_exact(p: dict) -> float:
    return CrSchro.exact(p)


# ============================================================================================ N-body
def _kepler_acc(x: float, y: float) -> tuple[float, float]:
    r2 = x * x + y * y
    r3 = r2 * math.sqrt(r2)
    return -x / r3, -y / r3


def _cluster_acc(pos: list[list[float]], m: float, eps2: float) -> tuple[list[list[float]], float]:
    n = len(pos)
    acc = [[0.0, 0.0, 0.0] for _ in range(n)]
    virial = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            dx = pos[j][0] - pos[i][0]
            dy = pos[j][1] - pos[i][1]
            dz = pos[j][2] - pos[i][2]
            r2 = dx * dx + dy * dy + dz * dz + eps2
            inv = 1.0 / (r2 * math.sqrt(r2))
            fx, fy, fz = m * dx * inv, m * dy * inv, m * dz * inv
            acc[i][0] += fx
            acc[i][1] += fy
            acc[i][2] += fz
            acc[j][0] -= fx
            acc[j][1] -= fy
            acc[j][2] -= fz
            virial -= m * m * (dx * dx + dy * dy + dz * dz) * inv
    return acc, virial


class CrNbody(_Base):
    """Gravitational N-body dynamics: a Kepler orbit by Euler, velocity Verlet or RK4 (period against Kepler's third
    law), and a 16-star cluster whose time-averaged virial ratio must be one."""

    PARAMS = {"cas": 0.0, "method": 1.0, "n": 200.0, "ecc": 0.5, "seed": 1999.0, "tend": 20.0, "ns": 16.0}

    @staticmethod
    def exact(p) -> float:
        if _i(p["cas"]) == 1:
            return 1.0
        return 2.0 * PI

    @staticmethod
    def _kepler(p):
        meth = _i(p["method"])
        n = max(8, _i(p["n"]))
        e = p["ecc"]
        T = 2.0 * PI
        dt = T / n
        x, y = 1.0 - e, 0.0
        vx, vy = 0.0, math.sqrt((1.0 + e) / (1.0 - e))
        E0 = 0.5 * (vx * vx + vy * vy) - 1.0 / math.sqrt(x * x + y * y)
        ts, Es = [0.0], [0.0]
        trail = [x, y]
        t = 0.0
        tc = 0.0
        prev_vr = 0.0
        prev_t = 0.0
        seen_neg = False
        for _ in range(4 * n):
            if meth == 0:
                ax, ay = _kepler_acc(x, y)
                vx, vy = vx + dt * ax, vy + dt * ay
                x, y = x + dt * vx, y + dt * vy
            elif meth == 1:
                ax, ay = _kepler_acc(x, y)
                vx += 0.5 * dt * ax
                vy += 0.5 * dt * ay
                x += dt * vx
                y += dt * vy
                ax, ay = _kepler_acc(x, y)
                vx += 0.5 * dt * ax
                vy += 0.5 * dt * ay
            else:
                def f(s):
                    ax, ay = _kepler_acc(s[0], s[1])
                    return [s[2], s[3], ax, ay]
                s0 = [x, y, vx, vy]
                k1 = f(s0)
                k2 = f([s0[i] + 0.5 * dt * k1[i] for i in range(4)])
                k3 = f([s0[i] + 0.5 * dt * k2[i] for i in range(4)])
                k4 = f([s0[i] + dt * k3[i] for i in range(4)])
                s1 = [s0[i] + dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) for i in range(4)]
                x, y, vx, vy = s1
            t += dt
            r = math.sqrt(x * x + y * y)
            vr = (x * vx + y * vy) / r
            En = 0.5 * (vx * vx + vy * vy) - 1.0 / r
            ts.append(t)
            Es.append((En - E0) / abs(E0))
            trail.append(x)
            trail.append(y)
            if vr < 0.0:
                seen_neg = True
            if seen_neg and prev_vr < 0.0 <= vr and tc == 0.0:
                tc = prev_t + dt * (-prev_vr) / (vr - prev_vr)
            prev_vr, prev_t = vr, t
            if tc > 0.0 and t > 1.3 * tc:
                break
        if tc == 0.0:
            tc = t
        return tc, ts, Es, trail, E0

    @staticmethod
    def _cluster(p):
        meth = _i(p["method"])
        n = max(20, _i(p["n"]))
        ns = max(4, _i(p["ns"]))
        st = _lcg(p["seed"])
        m = 1.0 / ns
        eps2 = 0.01
        pos, vel = [], []
        while len(pos) < ns:
            q = [2.0 * _u(st) - 1.0, 2.0 * _u(st) - 1.0, 2.0 * _u(st) - 1.0]
            if q[0] * q[0] + q[1] * q[1] + q[2] * q[2] <= 1.0:
                pos.append(q)
        for _ in range(ns):
            v = []
            for _k in range(3):
                g = 0.0
                for _j in range(12):
                    g += _u(st)
                v.append(g - 6.0)
            vel.append(v)
        for k in range(3):
            cm = 0.0
            cv = 0.0
            for i in range(ns):
                cm += pos[i][k]
                cv += vel[i][k]
            cm /= ns
            cv /= ns
            for i in range(ns):
                pos[i][k] -= cm
                vel[i][k] -= cv
        acc, W = _cluster_acc(pos, m, eps2)
        K = 0.0
        for v in vel:
            K += 0.5 * m * (v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
        sc = math.sqrt(abs(W) / (2.0 * K))
        for v in vel:
            for k in range(3):
                v[k] *= sc
        tend = p["tend"]
        dt = tend / n
        ts, run, inst = [], [], []
        sK = 0.0
        sW = 0.0
        for step in range(n + 1):
            acc, W = _cluster_acc(pos, m, eps2)
            K = 0.0
            for v in vel:
                K += 0.5 * m * (v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
            sK += 2.0 * K
            sW += -W
            ts.append(step * dt)
            run.append(sK / sW)
            inst.append(2.0 * K / (-W))
            if step == n:
                break
            if meth == 0:
                for i in range(ns):
                    for k in range(3):
                        vel[i][k] += dt * acc[i][k]
                        pos[i][k] += dt * vel[i][k]
            else:
                for i in range(ns):
                    for k in range(3):
                        vel[i][k] += 0.5 * dt * acc[i][k]
                        pos[i][k] += dt * vel[i][k]
                acc2, _w = _cluster_acc(pos, m, eps2)
                for i in range(ns):
                    for k in range(3):
                        vel[i][k] += 0.5 * dt * acc2[i][k]
        return sK / sW, ts, run, inst, pos

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        ex = CrNbody.exact(p)
        if cas == 1:
            val, ts, run, inst, pos = CrNbody._cluster(p)
            pts = []
            for q in pos:
                pts.append(q[0])
                pts.append(q[1])
            return _base(val, ex, _i(p["n"]), ts, [1.0 for _ in ts], run, [], [], cy2=inst, pts=pts, pw=2.0)
        tc, ts, Es, trail, E0 = CrNbody._kepler(p)
        stride = max(1, len(ts) // 300)
        tx = [ts[i] for i in range(0, len(ts), stride)]
        ty = [Es[i] for i in range(0, len(ts), stride)]
        tr = []
        for i in range(0, len(trail) // 2, max(1, (len(trail) // 2) // 300)):
            tr.append(trail[2 * i])
            tr.append(trail[2 * i + 1])
        return _base(tc, ex, _i(p["n"]), tx, [0.0 for _ in tx], ty, [], [], pts=[trail[-2], trail[-1]], pw=2.0,
                     trail=tr, dE=Es[-1])


def _nbody_exact(p: dict) -> float:
    return CrNbody.exact(p)


# ============================================================================================ XY and Heisenberg spins
class CrSpin(_Base):
    """Classical O(n) spins by Metropolis: the 2-D XY model (n = 2) and the 3-D Heisenberg model (n = 3). At low T
    the spin-wave (harmonic) theory is exact: e = e0 + (n_dof N - g) T / 2N, helicity modulus Y = 1 - T/4 (XY)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 800.0, "seed": 4711.0, "L": 8.0, "T": 0.2, "what": 0.0}

    @staticmethod
    def exact(p) -> float:
        cas, w, T = _i(p["cas"]), _i(p["what"]), p["T"]
        L = max(3, _i(p["L"]))
        if cas == 0:
            N = L * L
            if w == 1:
                return 1.0 - T / 4.0 * (1.0 - 1.0 / N)
            return -2.0 + 0.5 * T * (N - 1.0) / N
        N = L * L * L
        return -3.0 + T * (N - 1.0) / N

    @staticmethod
    def init(p, cfg=None):
        cas, w, T = _i(p["cas"]), _i(p["what"]), p["T"]
        L = max(3, _i(p["L"]))
        n = max(20, _i(p["n"]))
        st = _lcg(p["seed"])
        dim = 2 if cas == 0 else 3
        N = L ** dim
        nbr = []
        for i in range(N):
            if dim == 2:
                x, y = i % L, i // L
                nbr.append([y * L + (x + 1) % L, y * L + (x - 1) % L, ((y + 1) % L) * L + x, ((y - 1) % L) * L + x])
            else:
                x, y, z = i % L, (i // L) % L, i // (L * L)
                nbr.append([z * L * L + y * L + (x + 1) % L, z * L * L + y * L + (x - 1) % L,
                            z * L * L + ((y + 1) % L) * L + x, z * L * L + ((y - 1) % L) * L + x,
                            ((z + 1) % L) * L * L + y * L + x, ((z - 1) % L) * L * L + y * L + x])
        sp = [[1.0, 0.0, 0.0] for _ in range(N)]
        delta = 0.5 if T < 0.5 else 1.0
        delta = delta * math.sqrt(T) * 2.0 if T < 0.5 else delta

        def sweep():
            for _ in range(N):
                i = int(math.floor(_u(st) * N))
                if i > N - 1:
                    i = N - 1
                while True:
                    a = 2.0 * _u(st) - 1.0
                    b = 2.0 * _u(st) - 1.0
                    c = (2.0 * _u(st) - 1.0) if dim == 3 else 0.0
                    if a * a + b * b + c * c <= 1.0:
                        break
                s = sp[i]
                nx = s[0] + delta * a
                ny = s[1] + delta * b
                nz = s[2] + delta * c if dim == 3 else 0.0
                nn = math.sqrt(nx * nx + ny * ny + nz * nz)
                nx, ny, nz = nx / nn, ny / nn, nz / nn
                hx = hy = hz = 0.0
                for j in nbr[i]:
                    hx += sp[j][0]
                    hy += sp[j][1]
                    hz += sp[j][2]
                dE = -((nx - s[0]) * hx + (ny - s[1]) * hy + (nz - s[2]) * hz)
                if dE <= 0.0 or _u(st) < math.exp(-dE / T):
                    sp[i] = [nx, ny, nz]

        for _ in range(n // 5 + 40):
            sweep()
        marks = _marks(n)
        mi = 0
        se = 0.0
        sy = 0.0
        run = []
        for k in range(1, n + 1):
            sweep()
            e = 0.0
            for i in range(N):
                s = sp[i]
                for jj in range(0, len(nbr[i]), 2):
                    t2 = sp[nbr[i][jj]]
                    e -= s[0] * t2[0] + s[1] * t2[1] + s[2] * t2[2]
            e /= N
            se += e
            if cas == 0:
                # helicity modulus along x: Y = <e_x> - (1/(T N)) <(sum sin(th_i - th_j))^2>
                ex_ = 0.0
                cur = 0.0
                for i in range(N):
                    s = sp[i]
                    t2 = sp[nbr[i][0]]
                    ex_ += s[0] * t2[0] + s[1] * t2[1]
                    cur += s[1] * t2[0] - s[0] * t2[1]
                sy += ex_ / N - cur * cur / (T * N)
            if w == 0:
                est = se / k
            else:
                est = sy / k
            while mi < len(marks) and marks[mi] == k:
                run.append(est)
                mi += 1
        val = se / n if w == 0 else sy / n
        ex = CrSpin.exact(p)
        cx = [float(q) for q in marks]
        lat = []
        for i in range(L * L):
            s = sp[i]
            lat.append(math.atan2(s[1], s[0]) if cas == 0 else s[2])
        return _base(val, ex, n, cx, [ex for _ in cx], run, [cx[-1]], [val], lat=lat, lw=float(L), lh=float(L),
                     latkind=float(cas))


def _spin_exact(p: dict) -> float:
    return CrSpin.exact(p)


# ============================================================================================ exact diagonalisation
def _tri_min(al: list[float], be: list[float]) -> float:
    n = len(al)
    r = 0.0
    for b in be:
        r = max(r, abs(b))
    lo = min(al) - 2.0 * r - 1.0
    hi = max(al) + 2.0 * r + 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        cnt = 0
        q = al[0] - mid
        if q < 0.0:
            cnt += 1
        for i in range(1, n):
            if abs(q) < 1e-300:
                q = 1e-300
            q = al[i] - mid - be[i - 1] * be[i - 1] / q
            if q < 0.0:
                cnt += 1
        if cnt >= 1:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def _dot(a: list[float], b: list[float]) -> float:
    r = 0.0
    for i in range(len(a)):
        r += a[i] * b[i]
    return r


def _lanczos(apply, dim: int, iters: int) -> float:
    v = [1.0 + 0.01 * ((i * 7919) % 101) for i in range(dim)]
    nrm = math.sqrt(_dot(v, v))
    v = [q / nrm for q in v]
    vp = [0.0] * dim
    beta = 0.0
    al: list[float] = []
    be: list[float] = []
    best = None
    for k in range(iters):
        w = apply(v)
        a = _dot(w, v)
        w = [w[i] - a * v[i] - beta * vp[i] for i in range(dim)]
        al.append(a)
        b = math.sqrt(_dot(w, w))
        if k % 5 == 4 or b < 1e-12:
            e = _tri_min(al, be)
            if best is not None and abs(e - best) < 1e-12:
                return e
            best = e
        if b < 1e-12 or len(al) >= dim:
            break
        be.append(b)
        vp = v
        v = [q / b for q in w]
        beta = b
    return _tri_min(al, be[:len(al) - 1])


def _ed_tfim(N: int, h: float) -> float:
    dim = 1 << N

    def diag(s):
        d = 0.0
        for i in range(N):
            a = 1.0 - 2.0 * ((s >> i) & 1)
            b = 1.0 - 2.0 * ((s >> ((i + 1) % N)) & 1)
            d -= a * b
        return d
    dg = [diag(s) for s in range(dim)]

    def apply(v):
        w = [dg[s] * v[s] for s in range(dim)]
        for s in range(dim):
            x = v[s]
            for i in range(N):
                w[s ^ (1 << i)] -= h * x
        return w
    return _lanczos(apply, dim, 120)


def _tfim_exact(N: int, h: float) -> float:
    tot = 0.0
    for m in range(N):
        k = (2 * m + 1) * PI / N
        tot += math.sqrt(1.0 + h * h - 2.0 * h * math.cos(k))
    return -tot


def _ed_heis(N: int) -> float:
    states = []
    for s in range(1 << N):
        c = 0
        for i in range(N):
            c += (s >> i) & 1
        if c == N // 2:
            states.append(s)
    idx = {s: k for k, s in enumerate(states)}
    dim = len(states)
    dg = []
    flips = []
    for s in states:
        d = 0.0
        fl = []
        for i in range(N):
            j = (i + 1) % N
            a = (s >> i) & 1
            b = (s >> j) & 1
            if a == b:
                d += 0.25
            else:
                d -= 0.25
                fl.append(idx[s ^ (1 << i) ^ (1 << j)])
        dg.append(d)
        flips.append(fl)

    def apply(v):
        w = [dg[k] * v[k] for k in range(dim)]
        for k in range(dim):
            x = 0.5 * v[k]
            for t in flips[k]:
                w[t] += x
        return w
    return _lanczos(apply, dim, 120)


class CrEd(_Base):
    """Lanczos exact diagonalisation of a spin-1/2 ring: the transverse-field Ising chain (free-fermion energy) and
    the Heisenberg chain (Bethe-ansatz energy per site 1/4 - ln 2 after extrapolating in 1/N^2)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "h": 1.0}

    @staticmethod
    def exact(p) -> float:
        if _i(p["cas"]) == 1:
            return 0.25 - math.log(2.0)
        N = max(4, _i(p["n"]))
        return _tfim_exact(N, p["h"]) / N

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        N = max(4, _i(p["n"]))
        if cas == 1:
            N -= N % 2
            sizes = list(range(4, N + 1, 2))
            e = {}
            for k in sizes:
                e[k] = _ed_heis(k) / k
            if N >= 6:
                val = (N * N * e[N] - (N - 2) * (N - 2) * e[N - 2]) / (N * N - (N - 2) * (N - 2))
            else:
                val = e[N]
            ex = CrEd.exact(p)
            cx = [1.0 / (k * k) for k in sizes]
            return _base(val, ex, N, cx, [ex for _ in cx], [e[k] for k in sizes], list(cx), [e[k] for k in sizes],
                         eN=e[N])
        h = p["h"]
        sizes = list(range(4, N + 1, 2))
        ed = [_ed_tfim(k, h) / k for k in sizes]
        ce = [_tfim_exact(k, h) / k for k in sizes]
        val = ed[-1]
        return _base(val, ce[-1], N, [float(k) for k in sizes], ce, ed, [float(k) for k in sizes], ed)


def _ed_exact(p: dict) -> float:
    return CrEd.exact(p)


# ============================================================================================ MCMC fitting
def _trap_shape(t: float) -> float:
    """A transit light-curve shape: a flat-bottomed dip with linear ingress and egress (centre 0, depth 1)."""
    a = abs(t)
    if a >= 0.25:
        return 0.0
    if a <= 0.15:
        return 1.0
    return (0.25 - a) / 0.10


def _ssq(d: list[float]) -> float:
    r = 0.0
    for q in d:
        r += q * q
    return r


class CrMcmc(_Base):
    """Metropolis MCMC for the parameters of a spectral line, a decay curve and a transit; the posterior mean and
    width are compared with the posterior integrated directly (a grid, or the exact Gaussian for a linear model)."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 3003.0, "what": 0.0, "sig": 0.3}

    @staticmethod
    def _setup(p):
        cas = _i(p["cas"])
        sig = p["sig"]
        st = _lcg(p["seed"])
        if cas == 0:
            M = 30
            xs = [-3.0 + 6.0 * i / (M - 1) for i in range(M)]
            A0, x00, w = 2.0, 0.3, 0.6
            ys = [A0 * math.exp(-(q - x00) * (q - x00) / (2 * w * w)) + sig * _gauss(st) for q in xs]
            model = lambda q, a, b: a * math.exp(-(q - b) * (q - b) / (2 * w * w))
            return cas, xs, ys, sig, model, (0.0, 5.0), (-2.0, 2.0), A0
        if cas == 1:
            M = 30
            xs = [5.0 * i / (M - 1) for i in range(M)]
            A0, tau0 = 3.0, 1.5
            ys = [A0 * math.exp(-q / tau0) + sig * _gauss(st) for q in xs]
            model = lambda q, a, b: a * math.exp(-q / b)
            return cas, xs, ys, sig, model, (0.0, 8.0), (0.4, 5.0), tau0
        M = 60
        xs = [-0.5 + i / (M - 1) for i in range(M)]
        d0 = 0.01
        ys = [1.0 - d0 * _trap_shape(q) + sig * _gauss(st) for q in xs]
        return cas, xs, ys, sig, None, (0.0, 0.05), None, d0

    @staticmethod
    def init(p, cfg=None):
        n = max(200, _i(p["n"]))
        w = _i(p["what"])
        cas, xs, ys, sig, model, ra, rb, truth = CrMcmc._setup(p)
        M = len(xs)
        st = _lcg(p["seed"] + 17.0)
        if cas == 2:
            sm = 0.0
            sy = 0.0
            for i in range(M):
                m_ = _trap_shape(xs[i])
                sm += m_ * m_
                sy += m_ * (1.0 - ys[i])
            gm = sy / sm
            gs = sig / math.sqrt(sm)
            lo, hi = gm - 4.0 * gs, gm + 4.0 * gs
            post = lambda q: math.exp(-0.5 * (q - gm) * (q - gm) / (gs * gs)) / (gs * math.sqrt(2 * PI))
            logp = lambda th: -0.5 * _ssq([ys[i] - (1.0 - th[0] * _trap_shape(xs[i])) for i in range(M)]) / (sig * sig)
            th = [gm]
            step = [2.4 * gs]
            ex = gm if w == 0 else gs
        else:
            GA, GB = 120, 120
            ga = [ra[0] + (ra[1] - ra[0]) * (i + 0.5) / GA for i in range(GA)]
            gb = [rb[0] + (rb[1] - rb[0]) * (i + 0.5) / GB for i in range(GB)]
            lp = []
            best = -1e300
            for a in ga:
                row = []
                for b in gb:
                    s = 0.0
                    for i in range(M):
                        d = ys[i] - model(xs[i], a, b)
                        s += d * d
                    v = -0.5 * s / (sig * sig)
                    row.append(v)
                    if v > best:
                        best = v
                lp.append(row)
            wgt = [[math.exp(v - best) for v in row] for row in lp]
            prim_vals = ga if cas == 0 else gb
            marg = []
            for k in range(GA if cas == 0 else GB):
                if cas == 0:
                    marg.append(sum(wgt[k]))
                else:
                    marg.append(sum(wgt[a][k] for a in range(GA)))
            tot = sum(marg)
            gm = sum(prim_vals[k] * marg[k] for k in range(len(marg))) / tot
            gs = math.sqrt(sum((prim_vals[k] - gm) ** 2 * marg[k] for k in range(len(marg))) / tot)
            ex = gm if w == 0 else gs
            prim_w = (prim_vals[1] - prim_vals[0])
            post = None
            lo, hi = gm - 4.0 * gs, gm + 4.0 * gs
            # step sizes from the posterior width of each parameter (marginals on the grid)
            other = gb if cas == 0 else ga
            om = []
            for k in range(len(other)):
                if cas == 0:
                    om.append(sum(wgt[a][k] for a in range(GA)))
                else:
                    om.append(sum(wgt[k]))
            ot = sum(om)
            omean = sum(other[k] * om[k] for k in range(len(om))) / ot
            osd = math.sqrt(sum((other[k] - omean) ** 2 * om[k] for k in range(len(om))) / ot)
            if cas == 0:
                step = [2.0 * gs, 2.0 * osd]
                th = [gm, omean]
                logp = lambda t: (-1e300 if not (ra[0] < t[0] < ra[1] and rb[0] < t[1] < rb[1]) else
                                  -0.5 * _ssq([ys[i] - model(xs[i], t[0], t[1]) for i in range(M)]) / (sig * sig))
            else:
                step = [2.0 * osd, 2.0 * gs]
                th = [omean, gm]
                logp = lambda t: (-1e300 if not (ra[0] < t[0] < ra[1] and rb[0] < t[1] < rb[1]) else
                                  -0.5 * _ssq([ys[i] - model(xs[i], t[0], t[1]) for i in range(M)]) / (sig * sig))
        k0 = 0 if cas != 1 else 1
        if cas == 2:
            lo2, hi2 = 0.0, 0.05
        cur = logp(th)
        burn = n // 5
        marks = _marks(n)
        mi = 0
        s1 = 0.0
        s2 = 0.0
        cnt = 0
        run = []
        NH = 30
        hist = [0.0] * NH
        acc = 0.0
        est = 0.0
        for it in range(1, n + burn + 1):
            prop = [th[j] + step[j] * (2.0 * _u(st) - 1.0) * 1.7320508075688772 for j in range(len(th))]
            if cas == 2 and not (0.0 < prop[0] < 0.05):
                lq = -1e300
            else:
                lq = logp(prop)
            if lq >= cur or _u(st) < math.exp(lq - cur):
                th = prop
                cur = lq
                acc += 1.0
            if it > burn:
                v = th[k0]
                cnt += 1
                s1 += v
                s2 += v * v
                j = int(math.floor((v - lo) / (hi - lo) * NH))
                if 0 <= j < NH:
                    hist[j] += 1.0
                mean = s1 / cnt
                est = mean if w == 0 else math.sqrt(max(s2 / cnt - mean * mean, 0.0))
                while mi < len(marks) and marks[mi] == cnt:
                    run.append(est)
                    mi += 1
        val = est
        bw = (hi - lo) / NH
        hx = [lo + (j + 0.5) * bw for j in range(NH)]
        hy = [hist[j] / (cnt * bw) for j in range(NH)]
        if post is not None:
            hz = [post(q) for q in hx]
        else:
            hz = []
            for q in hx:
                k = int(math.floor((q - prim_vals[0]) / prim_w + 0.5))
                hz.append(marg[k] / (tot * prim_w) if 0 <= k < len(marg) else 0.0)
        cx = [float(q) for q in marks]
        return _base(val, ex, n, cx, [ex for _ in cx], run, [cx[-1]], [val], hx=hx, hy=hy, hz=hz,
                     accept=acc / (n + burn), truth=truth,
                     dx=list(xs), dy=list(ys))


def _mcmc_exact(p: dict) -> float:
    return CrMcmc.init(dict(p, n=200.0))["exact"]


# ============================================================================================ FDTD (1-D)
def _tm_T(layers: list[tuple[float, float]], w: float) -> float:
    """Exact transmittance of a stack in vacuum at angular frequency w (c = 1): the characteristic-matrix product."""
    a_r, a_i, b_r, b_i, c_r, c_i, d_r, d_i = 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0
    for nr, thick in layers:
        dl = nr * w * thick
        cs = math.cos(dl)
        sn = math.sin(dl)
        # layer matrix [[cs, -i sn / n], [-i n sn, cs]]
        m12_i = -sn / nr
        m21_i = -nr * sn
        na_r = a_r * cs - b_i * m21_i
        na_i = a_i * cs + b_r * m21_i
        nb_r = a_r * 0.0 - a_i * m12_i + b_r * cs
        nb_i = a_r * m12_i + a_i * 0.0 + b_i * cs
        nc_r = c_r * cs - d_i * m21_i
        nc_i = c_i * cs + d_r * m21_i
        nd_r = -c_i * m12_i + d_r * cs
        nd_i = c_r * m12_i + d_i * cs
        a_r, a_i, b_r, b_i, c_r, c_i, d_r, d_i = na_r, na_i, nb_r, nb_i, nc_r, nc_i, nd_r, nd_i
    sr = a_r + b_r + c_r + d_r
    si = a_i + b_i + c_i + d_i
    return 4.0 / (sr * sr + si * si)


def _fdtd_layers(p: dict) -> list[tuple[float, float]]:
    cas = _i(p["cas"])
    n = max(10, _i(p["n"]))
    if cas == 0:
        nr = p["n1"]
        return [(nr, float(max(1, _i(n / (4.0 * nr)))))]
    nh, nl = p["n1"], p["n2"]
    dh = float(max(1, _i(n / (4.0 * nh))))
    dl = float(max(1, _i(n / (4.0 * nl))))
    out = []
    for _ in range(_i(p["np"])):
        out.append((nh, dh))
        out.append((nl, dl))
    return out


def _fdtd_run(layers: list[tuple[float, float]], n: int, freqs: list[float]) -> list[float]:
    """Energy spectrum |E(w)|^2 of the field behind the structure (or behind vacuum when layers is empty)."""
    pad = 30
    total = 0
    for _nr, th in layers:
        total += int(th)
    N = pad + total + pad + 10
    eps = [1.0] * (N + 1)
    pos = pad
    for nr, th in layers:
        for _ in range(int(th)):
            eps[pos] = nr * nr
            pos += 1
    E = [0.0] * (N + 1)
    H = [0.0] * (N + 1)
    wc = 2.0 * PI / n
    tau = 1.2 * n
    t0 = 4.0 * tau
    xs, xp = 6, N - 8
    steps = int(t0 * 2.0 + 40 * n)
    cr = [1.0] * len(freqs)
    ci = [0.0] * len(freqs)
    sr = [0.0] * len(freqs)
    si = [0.0] * len(freqs)
    cw = [math.cos(wc * f) for f in freqs]
    sw = [math.sin(wc * f) for f in freqs]
    e1_old = 0.0
    eN_old = 0.0
    for t in range(steps):
        for i in range(N):
            H[i] += E[i + 1] - E[i]
        e1_old = E[1]
        eN_old = E[N - 1]
        for i in range(1, N):
            E[i] += (H[i] - H[i - 1]) / eps[i]
        tt = t - t0
        E[xs] += math.exp(-(tt / tau) * (tt / tau)) * math.cos(wc * tt)
        E[0] = e1_old
        E[N] = eN_old
        v = E[xp]
        for j in range(len(freqs)):
            sr[j] += v * cr[j]
            si[j] -= v * ci[j]
            cr[j], ci[j] = cr[j] * cw[j] - ci[j] * sw[j], cr[j] * sw[j] + ci[j] * cw[j]
    return [sr[j] * sr[j] + si[j] * si[j] for j in range(len(freqs))]


class CrFdtd(_Base):
    """1-D FDTD (Yee, Courant number 1) transmission through a dielectric slab or a Bragg mirror, against the exact
    characteristic-matrix result. n = grid cells per vacuum wavelength of the design frequency."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 40.0, "n1": 2.0, "n2": 1.5, "np": 3.0, "wr": 0.8}

    @staticmethod
    def init(p, cfg=None):
        n = max(10, _i(p["n"]))
        layers = _fdtd_layers(p)
        grid = [0.45 + 1.1 * j / 33.0 for j in range(34)]
        freqs = [p["wr"]] + grid
        ref = _fdtd_run([], n, freqs)
        out = _fdtd_run(layers, n, freqs)
        wc = 2.0 * PI / n
        Tn = [out[j] / ref[j] if ref[j] > 0 else 0.0 for j in range(len(freqs))]
        ex = [_tm_T(layers, wc * f) for f in freqs]
        return _base(Tn[0], ex[0], n, grid, ex[1:], Tn[1:], [p["wr"]], [Tn[0]], ncells=float(sum(th for _n, th in layers)))


def _fdtd_exact(p: dict) -> float:
    return _tm_T(_fdtd_layers(p), 2.0 * PI / max(10, _i(p["n"])) * p["wr"])


# ============================================================================================ particle-in-cell
def _two_stream_gamma(k: float, v0: float) -> float:
    """Growth rate of the cold symmetric two-stream instability (total plasma frequency 1): from
    (w^2 - k^2 v0^2)^2 = w^2 + k^2 v0^2, the smaller root w^2 = [(2a+1) - sqrt(1+8a)]/2 with a = k^2 v0^2."""
    a = k * k * v0 * v0
    W = ((2.0 * a + 1.0) - math.sqrt(1.0 + 8.0 * a)) / 2.0
    return math.sqrt(-W) if W < 0.0 else 0.0


class CrPic(_Base):
    """1-D electrostatic particle-in-cell code (cloud-in-cell, leapfrog, plasma frequency 1). cas 0: a cold plasma
    oscillation (omega = omega_p); cas 1: the two-stream instability growth rate. n = time steps per plasma period."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 32.0, "np": 800.0, "kk": 0.6123724356957945, "v0": 1.0,
              "amp": 0.001}

    @staticmethod
    def exact(p) -> float:
        if _i(p["cas"]) == 1:
            return _two_stream_gamma(p["kk"], p["v0"])
        return 1.0

    @staticmethod
    def init(p, cfg=None):
        cas = _i(p["cas"])
        n = max(8, _i(p["n"]))
        Np = max(100, _i(p["np"]))
        Ng = 32
        k1 = 1.0 if cas == 0 else p["kk"]
        L = 2.0 * PI / k1
        dx = L / Ng
        dt = 2.0 * PI / n
        amp = p["amp"] if cas == 0 else 1e-5
        x, v = [], []
        for i in range(Np):
            x0 = (i + 0.5) * L / Np
            v0 = 0.0
            if cas == 1:
                v0 = p["v0"] if (i % 2) == 0 else -p["v0"]
            xx = x0 + amp * math.sin(k1 * x0) / (k1 if cas == 0 else 1.0)
            x.append(xx % L)
            v.append(v0)
        wq = L / Np                                      # charge carried by one macro-particle (n0 = 1)

        def field(xp):
            ne = [0.0] * Ng
            for xx in xp:
                g = xx / dx
                j = int(math.floor(g))
                f = g - j
                ne[j % Ng] += (1.0 - f) * wq / dx
                ne[(j + 1) % Ng] += f * wq / dx
            E = [0.0] * Ng
            run = 0.0
            for j in range(Ng):
                run += dx * (1.0 - ne[j])
                E[j] = run
            mean = sum(E) / Ng
            return [q - mean for q in E]

        def gather(E, xx):                               # E_j sits half a cell to the right of node j
            g = xx / dx - 0.5
            j = int(math.floor(g))
            f = g - j
            return (1.0 - f) * E[j % Ng] + f * E[(j + 1) % Ng]

        def mode(E):
            a = 0.0
            for j in range(Ng):
                a += E[j] * math.sin(k1 * (j + 0.5) * dx)
            return 2.0 * a / Ng

        E = field(x)
        for i in range(Np):
            v[i] += 0.5 * dt * gather(E, x[i])           # charge -1, mass 1: a = -E ; start half a step back
        A0 = mode(E)
        ts, As = [0.0], [A0]
        tmax = 6.0 * 2.0 * PI if cas == 0 else 70.0
        nsteps = int(tmax / dt)
        t = 0.0
        for _ in range(nsteps):
            for i in range(Np):
                v[i] -= dt * gather(E, x[i])
                x[i] = (x[i] + dt * v[i]) % L
            t += dt
            E = field(x)
            a = mode(E)
            ts.append(t)
            As.append(a)
            if cas == 1 and abs(a) > 0.03:
                break
        ex = CrPic.exact(p)
        stride = max(1, len(ts) // 240)
        if cas == 0:
            crossings = []
            for i in range(1, len(ts)):
                if As[i - 1] > 0.0 >= As[i] or As[i - 1] < 0.0 <= As[i]:
                    crossings.append(ts[i - 1] + dt * As[i - 1] / (As[i - 1] - As[i]))
            if len(crossings) >= 3:
                val = PI * (len(crossings) - 1) / (crossings[-1] - crossings[0])
            else:
                val = 0.0
            cx = [ts[i] for i in range(0, len(ts), stride)]
            cy = [As[i] / A0 for i in range(0, len(ts), stride)]
            ce = [math.cos(q * ex) for q in cx]
        else:
            lo_th, hi_th = 1e-3, 2e-2
            sx = sy = sxx = sxy = 0.0
            m_ = 0
            for i in range(len(ts)):
                aa = abs(As[i])
                if lo_th <= aa <= hi_th:
                    ly = math.log(aa)
                    sx += ts[i]
                    sy += ly
                    sxx += ts[i] * ts[i]
                    sxy += ts[i] * ly
                    m_ += 1
            den = m_ * sxx - sx * sx
            val = (m_ * sxy - sx * sy) / den if m_ >= 3 and abs(den) > 1e-12 else 0.0
            cx = [ts[i] for i in range(0, len(ts), stride)]
            cy = [math.log(max(abs(As[i]), 1e-12)) for i in range(0, len(ts), stride)]
            # the theoretical line through the middle of the fitted window
            ly0 = math.log(1e-3)
            t0w = 0.0
            for i in range(len(ts)):
                if abs(As[i]) >= 1e-3:
                    t0w = ts[i]
                    break
            ce = [ly0 + ex * (q - t0w) for q in cx]
        pts = []
        for i in range(0, Np, max(1, Np // 300)):
            pts.append(x[i] / L)
            pts.append(v[i])
        return _base(val, ex, n, cx, ce, cy, [], [], pts=pts, pw=1.0, ptskind=1.0, vmax=max(abs(q) for q in v) + 0.2)


def _pic_exact(p: dict) -> float:
    return CrPic.exact(p)


# ============================================================================================ registration
KERNELS: dict[str, Any] = {"cr_interp": CrInterp, "cr_pde": CrPde, "cr_fem": CrFem, "cr_fit": CrFit, "cr_mle": CrMle,
                           "cr_dev": CrDev, "cr_walk": CrWalk, "cr_decay": CrDecay, "cr_twolevel": CrTwoLevel,
                           "cr_mcint": CrMcInt, "cr_scatter": CrScatter, "cr_poly": CrPoly, "cr_photon": CrPhoton,
                           "cr_ising": CrIsing, "cr_binder": CrBinder, "cr_tb": CrTb, "cr_schro": CrSchro,
                           "cr_nbody": CrNbody, "cr_spin": CrSpin, "cr_ed": CrEd, "cr_mcmc": CrMcmc,
                           "cr_fdtd": CrFdtd, "cr_pic": CrPic}
FAMILY = {k: "comp" for k in KERNELS}

TEXTBOOK = {
    "cr_interp_f": _ip_exact, "cr_pde_u": _pde_exact, "cr_fem_u": _fem_exact, "cr_fit_p": _fit_exact,
    "cr_mle_p": _mle_exact, "cr_dev_f": _dev_exact, "cr_walk_v": _walk_exact, "cr_decay_v": _decay_exact,
    "cr_two_v": _two_exact, "cr_mcint_I": _mcint_exact, "cr_scatter_s": _scatter_exact, "cr_poly_x": _poly_exact,
    "cr_photon_v": _photon_exact, "cr_ising_v": _ising_exact, "cr_binder_T": _binder_exact, "cr_tb_E": _tb_exact,
    "cr_schro_E": _schro_exact, "cr_nbody_v": _nbody_exact, "cr_spin_v": _spin_exact, "cr_ed_E": _ed_exact,
    "cr_mcmc_v": _mcmc_exact, "cr_fdtd_T": _fdtd_exact, "cr_pic_v": _pic_exact,
}


def _best(rows, p) -> float:
    """The answer at the finest setting the student ran: the row with the largest n."""
    rs = _rows(rows, "n", "val")
    if not rs:
        return 0.0
    best = rs[0]
    for r in rs:
        if r[0] > best[0]:
            best = r
    return best[1]


def _order(rows, p) -> float:
    """The slope of log(error) against log(n): err ~ n^-order (zero errors are left out)."""
    pts = [[math.log(n), math.log(e)] for n, e in _rows(rows, "n", "err") if n > 0 and e > 0]
    if len(pts) < 2:
        return 0.0
    sx = sum(q[0] for q in pts)
    sy = sum(q[1] for q in pts)
    sxx = sum(q[0] * q[0] for q in pts)
    sxy = sum(q[0] * q[1] for q in pts)
    den = len(pts) * sxx - sx * sx
    if abs(den) < 1e-30:
        return 0.0
    return -(len(pts) * sxy - sx * sy) / den


CALCS = {
    "cr_best": {"label": "best value", "unit": "", "needs": ["n", "val"], "fn": _best},
    "cr_order": {"label": "order of the method", "unit": "", "needs": ["n", "err"], "fn": _order},
}
