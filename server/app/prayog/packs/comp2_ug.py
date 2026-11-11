"""Kernel pack: the UG "Computational physics" practicals, second set (spectra, quadrature, quantum, special functions,
linear algebra, ... ). Prefix `cq_` everywhere so nothing collides with `comp_ug`.

Every kernel has the shape the workstation rig (`comp2-workstation`) expects, the same as `comp_ug`:

    PARAMS  cas (which problem), method (which numerical method), n (the setting: samples / nodes / strips / grid
            points / iterations) + the problem's own numbers
    init    runs the whole computation once and keeps the result
    step    advances a clock only
    view    val (numerical answer), exact (analytic answer), err (relative), nused (work done) and the curves the
            monitor draws: cx / ce (the exact curve), cy (what the method built, same x as cx) and px / py (nodes)
    measure {val, exact, err, nused}

Everything is deterministic and in SI or in the named dimensionless units; a random method is seeded from a lab
parameter. The exact JavaScript twin is `app/static/prayog/packs/comp2_ug.js`: same formulas, same order.
Chaotic kernels use only + - * / (no libm) so both languages give bit-identical iterates.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
EH_EV = 27.211386245981          # Hartree energy in eV (CODATA 2022, NIST)
KB_EV = 8.617333262e-5           # Boltzmann constant in eV/K (CODATA 2022 / SI exact)


def _i(v: float) -> int:
    return int(math.floor(v + 0.5))


def _err(val: float, exact: float) -> float:
    return abs(val - exact) / max(abs(exact), 1e-30)


def _grid(a: float, b: float, m: int) -> list[float]:
    return [a + (b - a) * i / m for i in range(m + 1)]


def _mk(params: dict, run, name: str):
    """A kernel class from its PARAMS and a run(p) -> state function (the same shape on both sides)."""
    def init(p, cfg=None):
        return run(p)

    def step(s, p, dt, cfg=None):
        s["t"] += dt

    def view(s, p, cfg=None):
        return dict(s)

    def measure(p, cfg=None):
        s = run(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}

    return type(name, (), {"PARAMS": params, "VARS": ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"],
                           "init": staticmethod(init), "step": staticmethod(step), "view": staticmethod(view),
                           "measure": staticmethod(measure)})


def _state(val, exact, nused, cx=None, ce=None, cy=None, px=None, py=None, **more):
    d = {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(nused),
         "cx": cx or [], "ce": ce or [], "cy": cy or [], "px": px or [], "py": py or []}
    d.update(more)
    return d


# ============================================================================================ Fourier coefficients
# f has period 2 pi; a_k = (1/pi) int f cos kt dt, b_k = (1/pi) int f sin kt dt, a_0/2 = the mean.
_FOUR_LIST = [  # per waveform: the nonzero coefficients the practical measures, as (ab, k): ab 0 = a_k, 1 = b_k
    [(1, 1), (1, 3), (1, 5), (1, 7)],
    [(0, 1), (0, 3), (0, 5), (0, 7)],
    [(0, 0), (1, 1), (0, 2), (0, 4)],
    [(0, 0), (0, 2), (0, 4), (0, 6)]]


def _four_f(cas: int, t: float, A: float) -> float:
    t = t - 2 * PI * math.floor(t / (2 * PI))            # into [0, 2 pi)
    if cas == 0:
        if abs(t) < 1e-12 or abs(t - PI) < 1e-12:
            return 0.0
        return A if t < PI else -A
    if cas == 1:                                          # even triangle, +A at t = 0, -A at t = pi
        u = t if t <= PI else 2 * PI - t
        return A * (1.0 - 2.0 * u / PI)
    s = math.sin(t)
    if cas == 2:
        return A * s if s > 0 else 0.0
    return A * abs(s)


def _four_exact(p: dict) -> float:
    cas, A = _i(p["cas"]), p["A"]
    ab, k = _FOUR_LIST[cas][_i(p["cidx"]) % 4]
    if cas == 0:
        return 4 * A / (k * PI)
    if cas == 1:
        return 8 * A / (k * k * PI * PI)
    if cas == 2:
        if k == 0:
            return A / PI
        if ab == 1:
            return A / 2
        return -2 * A / (PI * (k * k - 1))
    if k == 0:
        return 2 * A / PI
    return -4 * A / (PI * (k * k - 1))


def _four_coef(cas: int, ab: int, k: int, N: int, A: float, fs: list[float]) -> float:
    s = 0.0
    for j in range(N):
        t = 2 * PI * j / N
        s += fs[j] * (math.cos(k * t) if ab == 0 else math.sin(k * t))
    return s / N if (k == 0) else 2.0 * s / N


def _four_run(p: dict) -> dict:
    cas, N, A = _i(p["cas"]), max(8, _i(p["n"])), p["A"]
    fs = [_four_f(cas, 2 * PI * j / N, A) for j in range(N)]
    ab, k = _FOUR_LIST[cas][_i(p["cidx"]) % 4]
    val = _four_coef(cas, ab, k, N, A, fs)
    exact = _four_exact(p)
    # the partial sum of the first H harmonics built from the NUMERICAL coefficients (Gibbs overshoot on a square wave)
    H = 9
    coefs = []
    for kk in range(0, H + 1):
        coefs.append((_four_coef(cas, 0, kk, N, A, fs), _four_coef(cas, 1, kk, N, A, fs) if kk > 0 else 0.0))
    cx = _grid(0.0, 2 * PI, 120)
    ce = [_four_f(cas, t, A) for t in cx]
    cy = []
    for t in cx:
        s = coefs[0][0]
        for kk in range(1, H + 1):
            s += coefs[kk][0] * math.cos(kk * t) + coefs[kk][1] * math.sin(kk * t)
        cy.append(s)
    st = max(1, N // 64)
    px = [2 * PI * j / N for j in range(0, N, st)]
    py = [fs[j] for j in range(0, N, st)]
    return _state(val, exact, N, cx, ce, cy, px, py)


CqFourier = _mk({"cas": 0.0, "cidx": 0.0, "n": 64.0, "A": 1.0}, _four_run, "CqFourier")


# ============================================================================================ DFT / FFT
def _dft_bins(x: list[float], nb: int) -> list[tuple[float, float]]:
    """The first nb DFT bins by the defining sum (N multiplications each)."""
    N = len(x)
    out = []
    for m in range(nb):
        re = 0.0
        im = 0.0
        for j in range(N):
            a = 2 * PI * ((j * m) % N) / N
            re += x[j] * math.cos(a)
            im -= x[j] * math.sin(a)
        out.append((re, im))
    return out


def _fft(x: list[float]) -> list[tuple[float, float]]:
    """Iterative radix-2 Cooley-Tukey; len(x) must be a power of two."""
    N = len(x)
    re = list(x)
    im = [0.0] * N
    j = 0
    for i in range(1, N):                                  # bit reversal
        bit = N >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
    ln = 2
    while ln <= N:
        ang = -2 * PI / ln
        for i0 in range(0, N, ln):
            for k in range(ln // 2):
                wr, wi = math.cos(ang * k), math.sin(ang * k)
                a, b = i0 + k, i0 + k + ln // 2
                tr = re[b] * wr - im[b] * wi
                ti = re[b] * wi + im[b] * wr
                re[b], im[b] = re[a] - tr, im[a] - ti
                re[a], im[a] = re[a] + tr, im[a] + ti
        ln <<= 1
    return [(re[i], im[i]) for i in range(N)]


def _dsinc(x: float, w: float) -> float:
    """sin(pi w x)/(pi x) with its limit w at x = 0."""
    if abs(x) < 1e-12:
        return w
    return math.sin(PI * w * x) / (PI * x)


def _dft_exact_f(cas: int, nu: float, p: dict) -> float:
    if cas == 0:
        return abs(_dsinc(nu, 2 * p["a"]))
    if cas == 1:
        return abs(_dsinc(nu - p["f0"], p["L"]) + _dsinc(nu + p["f0"], p["L"])) / 2
    return p["sg"] * math.sqrt(2 * PI) * math.exp(-2 * PI * PI * p["sg"] * p["sg"] * nu * nu)


def _dirichlet4(w: float) -> float:
    s = math.sin(w / 2)
    return 4.0 if abs(s) < 1e-12 else abs(math.sin(2 * w) / s)


def _dft_side_exact() -> float:
    best = 0.0
    for i in range(4001):
        w = PI / 2 + (PI / 2) * i / 4000
        v = _dirichlet4(w)
        if v > best:
            best = v
    return best


def _dft_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if cas == 3:
        return _dft_side_exact()
    return _dft_exact_f(cas, _i(p["nu"] * p["L"]) / p["L"], p)


def _dft_run(p: dict) -> dict:
    cas, meth, N = _i(p["cas"]), _i(p["method"]), max(4, _i(p["n"]))
    L = p["L"]
    if cas == 3:
        x = [1.0 if j < 4 else 0.0 for j in range(N)]
        nb = N // 2 + 1
        X = _fft(x) if meth == 1 else _dft_bins(x, nb)
        mags = [math.hypot(X[k][0], X[k][1]) for k in range(nb)]
        val = 0.0
        for k in range(N // 4 + 1, nb):
            if mags[k] > val:
                val = mags[k]
        cx = _grid(0.0, 1.0, 200)
        ce = [_dirichlet4(PI * c) for c in cx]
        px = [2.0 * k / N for k in range(nb)]
        ops = N * math.log2(N) if meth == 1 else float(N) * N
        return _state(val, _dft_side_exact(), ops, cx, ce, [], px, mags)
    dt = L / N
    a = p["a"]
    x = []
    for j in range(N):
        t = -L / 2 + dt * j
        if cas == 0:
            x.append(0.5 if abs(abs(t) - a) < 1e-9 else (1.0 if abs(t) < a else 0.0))
        elif cas == 1:
            x.append(math.cos(2 * PI * p["f0"] * t))
        else:
            x.append(math.exp(-t * t / (2 * p["sg"] * p["sg"])))
    m = _i(p["nu"] * L)
    nmax = _i(p["numax"] * L)
    nb = min(N // 2, max(nmax, m)) + 1
    X = _fft(x) if meth == 1 else _dft_bins(x, nb)
    mags = [dt * math.hypot(X[k][0], X[k][1]) for k in range(nb)]
    val = mags[m] if m < nb else 0.0
    exact = _dft_exact_f(cas, m / L, p)
    cx = _grid(0.0, p["numax"], 160)
    ce = [_dft_exact_f(cas, c, p) for c in cx]
    px = [k / L for k in range(nb) if k / L <= p["numax"] + 1e-9]
    py = mags[:len(px)]
    ops = N * math.log2(N) if meth == 1 else float(N) * N
    return _state(val, exact, ops, cx, ce, [], px, py)


CqDft = _mk({"cas": 0.0, "method": 1.0, "n": 64.0, "L": 16.0, "a": 1.0, "f0": 0.55, "sg": 0.5, "nu": 0.25,
             "numax": 1.0}, _dft_run, "CqDft")


# ============================================================================================ Gauss quadrature
def _gauleg(n: int) -> tuple[list[float], list[float]]:
    xs = [0.0] * n
    ws = [0.0] * n
    for i in range((n + 1) // 2):
        z = math.cos(PI * (i + 0.75) / (n + 0.5))
        pp = 1.0
        for _ in range(100):
            p1, p2 = 1.0, 0.0
            for j in range(1, n + 1):
                p3 = p2
                p2 = p1
                p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / j
            pp = n * (z * p1 - p2) / (z * z - 1.0)
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) < 1e-15:
                break
        xs[i], xs[n - 1 - i] = -z, z
        ws[i] = ws[n - 1 - i] = 2.0 / ((1.0 - z * z) * pp * pp)
    return xs, ws


def _gaulag(n: int) -> tuple[list[float], list[float]]:
    xs = [0.0] * n
    ws = [0.0] * n
    z = 0.0
    for i in range(n):
        if i == 0:
            z = 3.0 / (1.0 + 2.4 * n)
        elif i == 1:
            z += 15.0 / (1.0 + 2.5 * n)
        else:
            ai = i - 1
            z += ((1.0 + 2.55 * ai) / (1.9 * ai) + 0.0) * (z - xs[i - 2])
        pp, p2 = 1.0, 1.0
        for _ in range(100):
            p1, p2 = 1.0, 0.0
            for j in range(1, n + 1):
                p3 = p2
                p2 = p1
                p1 = ((2.0 * j - 1.0 - z) * p2 - (j - 1.0) * p3) / j
            pp = (n * p1 - n * p2) / z
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) <= 1e-14 * max(1.0, abs(z)):
                break
        xs[i] = z
        ws[i] = -1.0 / (pp * n * p2)
    return xs, ws


def _gauher(n: int) -> tuple[list[float], list[float]]:
    xs = [0.0] * n
    ws = [0.0] * n
    pim4 = 0.7511255444649425
    z = 0.0
    for i in range((n + 1) // 2):
        if i == 0:
            z = math.sqrt(2.0 * n + 1.0) - 1.85575 * math.pow(2.0 * n + 1.0, -1.0 / 6.0)
        elif i == 1:
            z -= 1.14 * math.pow(n, 0.426) / z
        elif i == 2:
            z = 1.86 * z - 0.86 * xs[0]
        elif i == 3:
            z = 1.91 * z - 0.91 * xs[1]
        else:
            z = 2.0 * z - xs[i - 2]
        pp = 1.0
        for _ in range(100):
            p1, p2 = pim4, 0.0
            for j in range(1, n + 1):
                p3 = p2
                p2 = p1
                p1 = z * math.sqrt(2.0 / j) * p2 - math.sqrt((j - 1.0) / j) * p3
            pp = math.sqrt(2.0 * n) * p2
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) < 1e-14:
                break
        xs[i], xs[n - 1 - i] = z, -z
        ws[i] = ws[n - 1 - i] = 2.0 / (pp * pp)
    return xs, ws


def _gq_f(meth: int, x: float, p: dict) -> float:
    if meth == 0:
        return 4.0 / (1.0 + x * x)
    if meth == 1:
        return math.sin(p["wl"] * x)
    return math.cos(p["wh"] * x)


def _gq_exact(p: dict) -> float:
    meth = _i(p["method"])
    if meth == 0:
        return PI
    if meth == 1:
        return p["wl"] / (1.0 + p["wl"] * p["wl"])
    return math.sqrt(PI) * math.exp(-p["wh"] * p["wh"] / 4.0)


def _gq_run(p: dict) -> dict:
    meth, n = _i(p["method"]), max(1, min(40, _i(p["n"])))
    if meth == 0:
        xs, ws = _gauleg(n)
        xs = [0.5 * (x + 1.0) for x in xs]                   # [-1, 1] -> [0, 1]
        ws = [0.5 * w for w in ws]
        lo, hi = 0.0, 1.0
    elif meth == 1:
        xs, ws = _gaulag(n)
        lo, hi = 0.0, 12.0
    else:
        xs, ws = _gauher(n)
        lo, hi = -6.0, 6.0
    val = 0.0
    for x, w in zip(xs, ws):
        val += w * _gq_f(meth, x, p)
    cx = _grid(lo, hi, 160)
    if meth == 0:
        ce = [_gq_f(0, c, p) for c in cx]
    elif meth == 1:
        ce = [math.exp(-c) * _gq_f(1, c, p) for c in cx]
    else:
        ce = [math.exp(-c * c) * _gq_f(2, c, p) for c in cx]
    px = list(xs)
    if meth == 0:
        py = [_gq_f(0, x, p) for x in xs]
    elif meth == 1:
        py = [math.exp(-x) * _gq_f(1, x, p) for x in xs]
    else:
        py = [math.exp(-x * x) * _gq_f(2, x, p) for x in xs]
    wsum = sum(ws)
    return _state(val, _gq_exact(p), n, cx, ce, [], px, py, wsum=wsum)


CqGauss = _mk({"cas": 0.0, "method": 0.0, "n": 4.0, "wl": 1.0, "wh": 1.0}, _gq_run, "CqGauss")


# ============================================================================================ radial Schrodinger
def _sturm(d: list[float], e2: float, x: float) -> int:
    """Number of eigenvalues of the symmetric tridiagonal matrix (diagonal d, constant off-diagonal e, e2 = e*e) below x."""
    cnt = 0
    q = d[0] - x
    if q < 0:
        cnt += 1
    for i in range(1, len(d)):
        if q == 0:
            q = 1e-300
        q = d[i] - x - e2 / q
        if q < 0:
            cnt += 1
    return cnt


def _tri_eig(d: list[float], e: float, k: int) -> float:
    lo = min(d) - 2 * abs(e)
    hi = max(d) + 2 * abs(e)
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if _sturm(d, e * e, mid) > k:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def _tri_solve(d: list[float], e: float, rhs: list[float]) -> list[float]:
    """Thomas algorithm for the tridiagonal system (diagonal d, constant off-diagonal e)."""
    n = len(d)
    c = [0.0] * n
    b = [0.0] * n
    den = d[0]
    c[0] = e / den
    b[0] = rhs[0] / den
    for i in range(1, n):
        den = d[i] - e * c[i - 1]
        if den == 0:
            den = 1e-300
        c[i] = e / den
        b[i] = (rhs[i] - e * b[i - 1]) / den
    x = [0.0] * n
    x[n - 1] = b[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = b[i] - c[i] * x[i + 1]
    return x


def _tri_vec(d: list[float], e: float, lam: float) -> list[float]:
    """The eigenvector for eigenvalue lam by inverse iteration with a shift a hair off it."""
    n = len(d)
    sh = lam - 1e-9 * max(1.0, abs(lam))
    dd = [x - sh for x in d]
    v = [1.0 + 0.5 * math.sin(0.37 * (j + 1)) for j in range(n)]
    for _ in range(3):
        v = _tri_solve(dd, e, v)
        s = math.sqrt(sum(x * x for x in v))
        v = [x / s for x in v]
    return v


def _lagu(n: int, a: float, x: float) -> float:
    """generalized Laguerre L_n^a(x), by the recurrence."""
    if n == 0:
        return 1.0
    p0, p1 = 1.0, 1.0 + a - x
    for j in range(1, n):
        p0, p1 = p1, ((2.0 * j + 1.0 + a - x) * p1 - (j + a) * p0) / (j + 1.0)
    return p1


def _sch_setup(p: dict):
    """Returns (x grid, diagonal, off-diagonal, energy factor to the reported unit, exact value, label data)."""
    cas, N, ll = _i(p["cas"]), max(20, _i(p["n"])), _i(p["ll"])
    k = _i(p["kst"])
    if cas == 0:                                           # hydrogen-like, atomic units, reduced mass mu
        mu, rmax = p["mu"], p["rmax"]
        h = rmax / (N + 1)
        xs = [h * (j + 1) for j in range(N)]
        d = [1.0 / (mu * h * h) + ll * (ll + 1) / (2 * mu * x * x) - 1.0 / x for x in xs]
        e = -1.0 / (2 * mu * h * h)
        nq = k + ll + 1
        return xs, d, e, EH_EV, -mu / (2.0 * nq * nq) * EH_EV, h
    if cas == 1:                                           # Hulthen: energies in hbar^2/(2 m a^2), lengths in a
        g, xmax = p["g"], p["rmax"]
        h = xmax / (N + 1)
        xs = [h * (j + 1) for j in range(N)]
        d = [2.0 / (h * h) + ll * (ll + 1) / (x * x) - g / (math.exp(x) - 1.0) for x in xs]
        e = -1.0 / (h * h)
        unit = EH_EV / (2.0 * p["aa"] * p["aa"])
        nq = k + 1
        ex = -math.pow((g - nq * nq) / (2.0 * nq), 2) * unit
        return xs, d, e, unit, ex, h
    lam, y0, y1 = p["lam"], p["ymin"], p["rmax"]           # Morse, energies in eps0 = hbar^2 a^2/(2 mu), y = a (r - re)
    h = (y1 - y0) / (N + 1)
    xs = [y0 + h * (j + 1) for j in range(N)]
    d = [2.0 / (h * h) + lam * lam * (math.exp(-2 * x) - 2 * math.exp(-x)) for x in xs]
    e = -1.0 / (h * h)
    ex = math.pow(lam - k - 0.5, 2) * p["e0"]              # binding below dissociation, reported as a positive number
    return xs, d, e, p["e0"], ex, h


def _sch_exact_u(p: dict, x: float) -> float:
    cas, ll, k = _i(p["cas"]), _i(p["ll"]), _i(p["kst"])
    if cas == 0:
        mu = p["mu"]
        if ll == 0 and k == 0:
            return 2 * math.pow(mu, 1.5) * x * math.exp(-mu * x)
        if ll == 0 and k == 1:
            return math.pow(mu, 1.5) / (2 * math.sqrt(2.0)) * x * (2 - mu * x) * math.exp(-mu * x / 2)
        if ll == 1 and k == 0:
            return math.pow(mu, 2.5) / (2 * math.sqrt(6.0)) * x * x * math.exp(-mu * x / 2)
        return float("nan")
    if cas == 1 and ll == 0 and k == 0:
        kap = (p["g"] - 1.0) / 2.0
        return (1.0 - math.exp(-x)) * math.exp(-kap * x)
    if cas == 2 and k == 0:
        xi = 2 * p["lam"] * math.exp(-x)
        return math.pow(xi, p["lam"] - 0.5) * math.exp(-xi / 2)
    return float("nan")


def _sch_run(p: dict) -> dict:
    cas = _i(p["cas"])
    xs, d, e, unit, exact, h = _sch_setup(p)
    k = _i(p["kst"])
    lam = _tri_eig(d, e, k)
    val = lam * unit if cas != 2 else -lam * unit
    v = _tri_vec(d, e, lam)
    u = [a / math.sqrt(h) for a in v]                       # integral u^2 dx = 1
    big = max(abs(a) for a in u)
    for a in u:
        if abs(a) > 0.05 * big:
            if a < 0:
                u = [-b for b in u]
            break
    x0, x1 = p["xd0"], p["xd1"]
    cx = _grid(x0, x1, 200)
    raw = [_sch_exact_u(p, c) for c in cx]
    ce = []
    if raw and raw[0] == raw[0]:
        s = 0.0
        for i in range(len(cx) - 1):
            s += 0.5 * (raw[i] * raw[i] + raw[i + 1] * raw[i + 1]) * (cx[i + 1] - cx[i])
        f = 1.0 / math.sqrt(s)
        ce = [r * f for r in raw]
    idx = [j for j in range(len(xs)) if x0 <= xs[j] <= x1]
    st = max(1, len(idx) // 90)
    px = [xs[j] for j in idx[::st]]
    py = [u[j] for j in idx[::st]]
    return _state(val, exact, len(xs), cx, ce, [], px, py)


CqSchro = _mk({"cas": 0.0, "kst": 0.0, "ll": 0.0, "n": 400.0, "mu": 1.0, "rmax": 40.0, "g": 10.0, "aa": 5.0, "lam": 18.1357,
               "ymin": -0.6, "e0": 121.336, "xd0": 0.0, "xd1": 20.0}, _sch_run, "CqSchro")


# ============================================================================================ special functions
def _legendre_rec(n: int, x: float) -> float:
    if n == 0:
        return 1.0
    p0, p1 = 1.0, x
    for j in range(1, n):
        p0, p1 = p1, ((2.0 * j + 1.0) * x * p1 - j * p0) / (j + 1.0)
    return p1


def _binomial(m: int, k: int) -> float:
    c = 1.0
    for i in range(1, k + 1):
        c = c * (m - k + i) / i
    return c


def _legendre_sum(n: int, x: float) -> float:
    s = 0.0
    for k in range(n // 2 + 1):
        s += math.pow(-1.0, k) * _binomial(n, k) * _binomial(2 * n - 2 * k, n) * math.pow(x, n - 2 * k)
    return s / math.pow(2.0, n)


def _laguerre_rec(n: int, x: float) -> float:
    return _lagu(n, 0.0, x)


def _laguerre_sum(n: int, x: float) -> float:
    s = 0.0
    f = 1.0
    for k in range(n + 1):
        if k > 0:
            f = f * k
        s += math.pow(-1.0, k) * _binomial(n, k) * math.pow(x, k) / f
    return s


def _hermite_rec(n: int, x: float) -> float:
    if n == 0:
        return 1.0
    p0, p1 = 1.0, 2.0 * x
    for j in range(1, n):
        p0, p1 = p1, 2.0 * x * p1 - 2.0 * j * p0
    return p1


def _hermite_sum(n: int, x: float) -> float:
    s = 0.0
    for m in range(n // 2 + 1):
        c = 1.0                                              # n! / (m! (n-2m)!)
        for i in range(1, n + 1):
            c = c * i
        for i in range(1, m + 1):
            c = c / i
        for i in range(1, n - 2 * m + 1):
            c = c / i
        s += math.pow(-1.0, m) * c * math.pow(2.0 * x, n - 2 * m)
    return s


def _bessel_series(n: int, x: float) -> float:
    t = math.pow(x / 2.0, n)
    for i in range(1, n + 1):
        t = t / i
    s = t
    for k in range(1, 80):
        t = -t * (x / 2.0) * (x / 2.0) / (k * (k + n))
        s += t
    return s


def _bessel_up(n: int, x: float) -> float:
    if abs(x) < 1e-9:
        return _bessel_series(n, x)
    j0, j1 = _bessel_series(0, x), _bessel_series(1, x)
    if n == 0:
        return j0
    for j in range(1, n):
        j0, j1 = j1, (2.0 * j / x) * j1 - j0
    return j1


def _bessel_down(n: int, x: float) -> float:
    """Miller's backward recurrence: start far above n, then normalise with J0 + 2 sum J_2k = 1."""
    if abs(x) < 1e-9:
        return _bessel_series(n, x)
    m = 2 * ((n + _i(math.sqrt(40.0 * n)) + 4) // 2)
    jp, jc = 0.0, 1e-30
    ans = 0.0
    norm = 0.0
    for j in range(m, 0, -1):
        jm = (2.0 * j / x) * jc - jp
        jp, jc = jc, jm
        if abs(jc) > 1e10:
            jc *= 1e-10
            jp *= 1e-10
            ans *= 1e-10
            norm *= 1e-10
        if j - 1 == n:
            ans = jc
        if (j - 1) % 2 == 0 and j - 1 > 0:
            norm += 2.0 * jc
    norm += jc
    return ans / norm


def _spec_fn(cas: int, meth: int, n: int, x: float) -> tuple[float, float]:
    if cas == 0:
        return _legendre_rec(n, x), _legendre_sum(n, x)
    if cas == 2:
        return _laguerre_rec(n, x), _laguerre_sum(n, x)
    if cas == 3:
        return _hermite_rec(n, x), _hermite_sum(n, x)
    return (_bessel_up(n, x) if meth == 0 else _bessel_down(n, x)), _bessel_series(n, x)


def _spec_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if cas == 1:
        return 2.0 / (2 * _i(p["deg"]) + 1)
    return _spec_fn(cas, 0, _i(p["n"]), p["x"])[1]


def _orth_val(meth: int, N: int, m1: int, m2: int) -> tuple[float, list[float], list[float]]:
    f = lambda x: _legendre_rec(m1, x) * _legendre_rec(m2, x)   # noqa: E731
    if meth == 2:
        xs, ws = _gauleg(N)
        return sum(w * f(x) for x, w in zip(xs, ws)), xs, [f(x) for x in xs]
    N = N + (N % 2)
    h = 2.0 / N
    xs = [-1.0 + h * i for i in range(N + 1)]
    ys = [f(x) for x in xs]
    if meth == 0:
        s = 0.5 * (ys[0] + ys[N])
        for i in range(1, N):
            s += ys[i]
        return s * h, xs, ys
    s = ys[0] + ys[N]
    for i in range(1, N):
        s += (4.0 if i % 2 == 1 else 2.0) * ys[i]
    return s * h / 3.0, xs, ys


def _spec_run(p: dict) -> dict:
    cas, meth, n = _i(p["cas"]), _i(p["method"]), max(1, _i(p["n"]))
    if cas == 1:
        deg = _i(p["deg"])
        val, xs, ys = _orth_val(meth, n, deg, deg)
        cross, _, _ = _orth_val(meth, n, deg, deg + 2)
        cx = _grid(-1.0, 1.0, 120)
        ce = [math.pow(_legendre_sum(deg, c), 2) for c in cx]
        return _state(val, 2.0 / (2 * deg + 1), n, cx, ce, [], xs, ys, cross=abs(cross))
    x0 = p["x"]
    val, ex = _spec_fn(cas, meth, n, x0)
    cx = _grid(p["xa"], p["xb"], 120)
    ce = [_spec_fn(cas, meth, n, c)[1] for c in cx]
    cy = [_spec_fn(cas, meth, n, c)[0] for c in cx]
    return _state(val, ex, n, cx, ce, cy, [x0], [val])


CqSpecial = _mk({"cas": 0.0, "method": 0.0, "n": 6.0, "deg": 4.0, "x": 0.6, "xa": -1.0, "xb": 1.0}, _spec_run, "CqSpecial")


# ============================================================================================ linear systems
def _det3(a: list[list[float]]) -> float:
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def _cramer(a: list[list[float]], b: list[float]) -> list[float]:
    d = _det3(a)
    out = []
    for c in range(3):
        m = [[(b[r] if cc == c else a[r][cc]) for cc in range(3)] for r in range(3)]
        out.append(_det3(m) / d)
    return out


def _ls_matrix(p: dict) -> tuple[list[list[float]], list[float]]:
    if _i(p["cas"]) == 0:                                   # three clockwise mesh currents
        r1, r2, r3, rb, rd, rf = p["r1"], p["r2"], p["r3"], p["rb"], p["rd"], p["rf"]
        a = [[r1 + rb + rf, -rb, -rf], [-rb, r2 + rb + rd, -rd], [-rf, -rd, r3 + rd + rf]]
        return a, [p["e1"], p["e2"], p["e3"]]
    k1, k2, k3, k4 = p["k1"], p["k2"], p["k3"], p["k4"]    # three masses between two walls
    a = [[k1 + k2, -k2, 0.0], [-k2, k2 + k3, -k3], [0.0, -k3, k3 + k4]]
    return a, [p["f1"], p["f2"], p["f3"]]


def _gauss_elim(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        piv = c
        for r in range(c + 1, n):
            if abs(m[r][c]) > abs(m[piv][c]):
                piv = r
        m[c], m[piv] = m[piv], m[c]
        for r in range(c + 1, n):
            f = m[r][c] / m[c][c]
            for cc in range(c, n + 1):
                m[r][cc] -= f * m[c][cc]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = m[r][n]
        for cc in range(r + 1, n):
            s -= m[r][cc] * x[cc]
        x[r] = s / m[r][r]
    return x


def _ls_exact(p: dict) -> float:
    a, b = _ls_matrix(p)
    return _cramer(a, b)[_i(p["pick"])]


def _ls_run(p: dict) -> dict:
    meth, n, pick = _i(p["method"]), max(1, _i(p["n"])), _i(p["pick"])
    a, b = _ls_matrix(p)
    xe = _cramer(a, b)
    exact = xe[pick]
    if meth == 0:
        x = _gauss_elim(a, b)
        return _state(x[pick], exact, 3 * 3 * 3 / 3, [1.0, 2.0, 3.0], list(xe), list(x), [1.0, 2.0, 3.0], list(x))
    x = [0.0, 0.0, 0.0]
    hist = []
    for _ in range(n):
        for i in range(3):
            s = b[i]
            for j in range(3):
                if j != i:
                    s -= a[i][j] * x[j]
            x[i] = s / a[i][i]
        hist.append(x[pick])
    cx = [float(i + 1) for i in range(n)]
    return _state(x[pick], exact, 3 * 3 * n, cx, [exact] * n, list(hist), cx, list(hist))


CqLinsys = _mk({"cas": 0.0, "method": 1.0, "n": 6.0, "pick": 0.0, "r1": 10.0, "r2": 15.0, "r3": 25.0, "rb": 20.0,
                "rd": 30.0, "rf": 40.0, "e1": 12.0, "e2": 0.0, "e3": -6.0,
                "k1": 300.0, "k2": 200.0, "k3": 250.0, "k4": 400.0, "f1": 1.0, "f2": 2.0, "f3": 0.5}, _ls_run, "CqLinsys")


# ============================================================================================ eigenvalues
def _chain_exact(M: int, kk: int) -> float:
    return 2.0 - 2.0 * math.cos(kk * PI / (M + 1))


def _jacobi_sweeps(a: list[list[float]], nsw: int) -> list[float]:
    """Cyclic Jacobi rotations on a symmetric 3x3 matrix; returns the smallest diagonal after each sweep (0 = before)."""
    a = [list(r) for r in a]
    hist = [min(a[0][0], a[1][1], a[2][2])]
    for _ in range(nsw):
        for pp, qq in ((0, 1), (0, 2), (1, 2)):
            if abs(a[pp][qq]) < 1e-300:
                continue
            th = (a[qq][qq] - a[pp][pp]) / (2.0 * a[pp][qq])
            t = (1.0 if th >= 0 else -1.0) / (abs(th) + math.sqrt(th * th + 1.0))
            c = 1.0 / math.sqrt(t * t + 1.0)
            s = t * c
            for k in range(3):                                 # columns p, q
                akp, akq = a[k][pp], a[k][qq]
                a[k][pp], a[k][qq] = c * akp - s * akq, s * akp + c * akq
            for k in range(3):                                 # rows p, q
                apk, aqk = a[pp][k], a[qq][k]
                a[pp][k], a[qq][k] = c * apk - s * aqk, s * apk + c * aqk
        hist.append(min(a[0][0], a[1][1], a[2][2]))
    return hist


def _inertia(p: dict) -> tuple[list[list[float]], float]:
    cas = _i(p["cas"])
    m = p["mass"]
    if cas == 1:                                               # uniform cube about a corner, axes along the edges
        a2 = p["sa"] * p["sa"]
        t = [[2.0 / 3, -0.25, -0.25], [-0.25, 2.0 / 3, -0.25], [-0.25, -0.25, 2.0 / 3]]
        return [[m * a2 * v for v in r] for r in t], m * a2 / 6.0
    a, b, c = p["sa"], p["sb"], p["sc"]                        # cuboid about its centre, axes turned by th1 (z), th2 (x)
    i1, i2, i3 = m * (b * b + c * c) / 12.0, m * (a * a + c * c) / 12.0, m * (a * a + b * b) / 12.0
    c1, s1, c2, s2, c3, s3 = (math.cos(p["th1"]), math.sin(p["th1"]), math.cos(p["th2"]), math.sin(p["th2"]),
                              math.cos(p["th3"]), math.sin(p["th3"]))
    rz = [[c1, -s1, 0.0], [s1, c1, 0.0], [0.0, 0.0, 1.0]]
    rx = [[1.0, 0.0, 0.0], [0.0, c2, -s2], [0.0, s2, c2]]
    rw = [[c3, -s3, 0.0], [s3, c3, 0.0], [0.0, 0.0, 1.0]]
    rzx = [[sum(rz[i][k] * rx[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    r = [[sum(rzx[i][k] * rw[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    dg = [i1, i2, i3]
    t = [[sum(r[i][k] * dg[k] * r[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    return t, min(i1, i2, i3)


def _eig_run(p: dict) -> dict:
    cas, meth, n = _i(p["cas"]), _i(p["method"]), max(1, _i(p["n"]))
    if cas != 0:
        a, ex = _inertia(p)
        hist = _jacobi_sweeps(a, n)
        cx = [float(i) for i in range(n + 1)]
        return _state(hist[-1], ex, n * 3, cx, [ex] * (n + 1), hist, cx, hist)
    M = _i(p["mdim"])
    if meth == 0:
        ex = _chain_exact(M, M)
    else:
        ex = _chain_exact(M, 1)
    v = [1.0 / (1.0 + 0.37 * j) for j in range(M)]
    d = [2.0] * M
    est = 0.0
    hist = []
    for _ in range(n):
        if meth == 0:
            w = [2.0 * v[j] - (v[j - 1] if j > 0 else 0.0) - (v[j + 1] if j < M - 1 else 0.0) for j in range(M)]
            num = sum(w[j] * v[j] for j in range(M))
            den = sum(v[j] * v[j] for j in range(M))
            est = num / den                                   # Rayleigh quotient of the current vector
            nr = math.sqrt(sum(a * a for a in w))
            v = [a / nr for a in w]
        else:
            w = _tri_solve(d, -1.0, v)
            num = sum(v[j] * v[j] for j in range(M))
            den = sum(w[j] * v[j] for j in range(M))
            est = num / den                                   # (v.v)/(v.A^-1 v) -> smallest eigenvalue
            nr = math.sqrt(sum(a * a for a in w))
            v = [a / nr for a in w]
        hist.append(est)
    cx = [float(i + 1) for i in range(n)]
    return _state(est, ex, n * M, cx, [ex] * n, hist, cx, hist)


CqEig = _mk({"cas": 0.0, "method": 0.0, "n": 10.0, "mdim": 6.0, "mass": 1.0, "sa": 1.0, "sb": 2.0, "sc": 3.0,
             "th1": 0.6, "th2": 0.4, "th3": 0.9}, _eig_run, "CqEig")


def _eig_exact(p: dict) -> float:
    if _i(p["cas"]) != 0:
        return _inertia(p)[1]
    M = _i(p["mdim"])
    return _chain_exact(M, M if _i(p["method"]) == 0 else 1)


# ============================================================================================ logistic map
def _lm_settled(r: float, T: int, per: int) -> bool:
    """True if, after T transient iterations from x = 0.3, the orbit repeats with period `per` (to 1e-7)."""
    x = 0.3
    for _ in range(T):
        x = r * x * (1.0 - x)
    x0 = x
    for _ in range(per):
        x = r * x * (1.0 - x)
    return abs(x - x0) < 1e-7


def _lm_superstable(k: int, guess: float) -> float:
    """The r at which the critical point x = 1/2 returns to itself after 2^k steps (Newton on f^(2^k)(1/2) - 1/2)."""
    r = guess
    m = 1 << k
    for _ in range(60):
        x = 0.5
        d = 0.0
        for _ in range(m):
            d = x * (1.0 - x) + r * (1.0 - 2.0 * x) * d
            x = r * x * (1.0 - x)
        step = (x - 0.5) / d
        r = r - step
        if abs(step) < 1e-14:
            break
    return r


def _lm_series(n: int) -> list[float]:
    """Superstable parameters R_0 = 2, R_1, ... R_n."""
    rs = [2.0, _lm_superstable(1, 3.2)]
    for k in range(2, n + 1):
        d = 4.2 if k == 2 else 4.6692
        rs.append(_lm_superstable(k, rs[k - 1] + (rs[k - 1] - rs[k - 2]) / d))
    return rs


FEIG = 4.669201609102990           # Feigenbaum's delta (J. Stat. Phys. 19, 25, 1978; OEIS A006890)


def _lm_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if cas == 0:
        return 3.0
    if cas == 1:
        return 1.0 + math.sqrt(6.0)
    return FEIG


def _lm_diagram(r0: float, r1: float) -> tuple[list[float], list[float]]:
    bx, by = [], []
    for i in range(240):
        r = r0 + (r1 - r0) * i / 239.0
        x = 0.3
        for _ in range(400):
            x = r * x * (1.0 - x)
        for _ in range(36):
            x = r * x * (1.0 - x)
            bx.append(r)
            by.append(x)
    return bx, by


def _lm_run(p: dict) -> dict:
    cas, n = _i(p["cas"]), max(2, _i(p["n"]))
    if cas == 2:
        n = min(n, 9)
        rs = _lm_series(n)
        val = (rs[n - 1] - rs[n - 2]) / (rs[n] - rs[n - 1])
        bx, by = _lm_diagram(2.9, 3.6)
        return _state(val, FEIG, n, [], [], [], rs, [0.5] * len(rs), bx=bx, by=by, mx=[], my=[])
    lo, hi, per = (2.9, 3.1, 1) if cas == 0 else (3.40, 3.50, 2)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if _lm_settled(mid, n, per):
            lo = mid
        else:
            hi = mid
    val = 0.5 * (lo + hi)
    ex = _lm_exact(p)
    bx, by = _lm_diagram(2.9, 3.6)
    return _state(val, ex, n * 40, [], [], [], [val], [0.5], bx=bx, by=by, mx=[ex], my=[0.5])


CqMap = _mk({"cas": 0.0, "n": 1000.0}, _lm_run, "CqMap")


# ============================================================================================ Lorenz system
def _lz_f(s: list[float], sg: float, rho: float, be: float) -> list[float]:
    return [sg * (s[1] - s[0]), s[0] * (rho - s[2]) - s[1], s[0] * s[1] - be * s[2]]


def _lz_rk4(s: list[float], h: float, sg: float, rho: float, be: float) -> list[float]:
    k1 = _lz_f(s, sg, rho, be)
    k2 = _lz_f([s[i] + 0.5 * h * k1[i] for i in range(3)], sg, rho, be)
    k3 = _lz_f([s[i] + 0.5 * h * k2[i] for i in range(3)], sg, rho, be)
    k4 = _lz_f([s[i] + h * k3[i] for i in range(3)], sg, rho, be)
    return [s[i] + h / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) for i in range(3)]


def _lz_g(w: list[float], sg: float, rho: float, be: float) -> list[float]:
    """State (x, y, z) and the 3 x 3 matrix Phi (row-major) of the variational equation Phi' = J Phi."""
    x, y, z = w[0], w[1], w[2]
    out = [sg * (y - x), x * (rho - z) - y, x * y - be * z]
    jac = [[-sg, sg, 0.0], [rho - z, -1.0, -x], [y, x, -be]]
    for i in range(3):
        for j in range(3):
            out.append(jac[i][0] * w[3 + j] + jac[i][1] * w[6 + j] + jac[i][2] * w[9 + j])
    return out


def _lz_det(w: list[float]) -> float:
    a = [[w[3], w[4], w[5]], [w[6], w[7], w[8]], [w[9], w[10], w[11]]]
    return _det3(a)


def _lz_run(p: dict) -> dict:
    sg, rho, be, T, n = p["sg"], p["rho"], p["be"], p["T"], max(10, _i(p["n"]))
    h = T / n
    w = [1.0, 1.0, 1.0] + [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    for _ in range(n):
        k1 = _lz_g(w, sg, rho, be)
        k2 = _lz_g([w[i] + 0.5 * h * k1[i] for i in range(12)], sg, rho, be)
        k3 = _lz_g([w[i] + 0.5 * h * k2[i] for i in range(12)], sg, rho, be)
        k4 = _lz_g([w[i] + h * k3[i] for i in range(12)], sg, rho, be)
        w = [w[i] + h / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) for i in range(12)]
    val = _lz_det(w)
    ex = math.exp(-(sg + 1.0 + be) * T)
    s = [1.0, 1.0, 1.0]                                  # the attractor itself: x against z, drawn at a fixed fine step
    px, py = [], []
    for i in range(2400):
        s = _lz_rk4(s, 0.01, sg, rho, be)
        if i % 2 == 0 and i > 200:
            px.append(s[0])
            py.append(s[2])
    mx, my = [0.0], [0.0]
    if rho > 1.0:
        c = math.sqrt(be * (rho - 1.0))
        mx += [c, -c]
        my += [rho - 1.0, rho - 1.0]
    return _state(val, ex, n * 4, [], [], [], px, py, mx=mx, my=my)


CqLorenz = _mk({"n": 20.0, "sg": 10.0, "rho": 28.0, "be": 8.0 / 3.0, "T": 1.0}, _lz_run, "CqLorenz")


# ============================================================================================ boundary value problems
def _bvp_exact_at(cas: int, x: float, L: float, B: float) -> float:
    if cas == 0:
        return B * math.sin(x) / math.sin(L)
    return B * math.sinh(x) / math.sinh(L)


def _bvp_exact(p: dict) -> float:
    return _bvp_exact_at(_i(p["cas"]), p["L"] / 2.0, p["L"], p["B"])


def _bvp_run(p: dict) -> dict:
    cas, meth, n, L, B = _i(p["cas"]), _i(p["method"]), max(2, _i(p["n"])), p["L"], p["B"]
    n += n % 2
    h = L / n
    q = 1.0 if cas == 0 else -1.0                         # y'' + q y = 0
    xs = [h * i for i in range(n + 1)]
    if meth == 0:                                         # finite differences: tridiagonal system for the n-1 interior values
        m = n - 1
        d = [q - 2.0 / (h * h)] * m
        rhs = [0.0] * m
        rhs[m - 1] = -B / (h * h)
        y = [0.0] + _tri_solve(d, 1.0 / (h * h), rhs) + [B]
    else:                                                 # shooting: RK4 for y' = v, v' = -q y; the slope found by the secant rule
        def shot(s: float) -> list[float]:
            y, v = 0.0, s
            out = [0.0]
            for _ in range(n):
                k1y, k1v = v, -q * y
                k2y, k2v = v + 0.5 * h * k1v, -q * (y + 0.5 * h * k1y)
                k3y, k3v = v + 0.5 * h * k2v, -q * (y + 0.5 * h * k2y)
                k4y, k4v = v + h * k3v, -q * (y + h * k3y)
                y += h / 6.0 * (k1y + 2 * k2y + 2 * k3y + k4y)
                v += h / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v)
                out.append(y)
            return out
        a0, a1 = shot(0.0), shot(1.0)
        s = (B - a0[n]) / (a1[n] - a0[n])
        y = shot(s)
    val = y[n // 2]
    ex = _bvp_exact_at(cas, L / 2.0, L, B)
    cx = _grid(0.0, L, 100)
    return _state(val, ex, n, cx, [_bvp_exact_at(cas, c, L, B) for c in cx], [], xs, y)


CqBvp = _mk({"cas": 0.0, "method": 0.0, "n": 8.0, "L": 1.5, "B": 1.0}, _bvp_run, "CqBvp")


# ============================================================================================ PDEs
def _pde_exact_at(cas: int, x: float, y: float, p: dict) -> float:
    if cas == 0:                                          # Laplace on the unit square, u(x, 1) = sin(pi x), other sides 0
        return math.sin(PI * x) * math.sinh(PI * y) / math.sinh(PI)
    if cas == 1:                                          # heat: u(x, 0) = sin(pi x), ends held at 0
        return math.exp(-PI * PI * p["al"] * p["T"]) * math.sin(PI * x)
    return math.cos(PI * p["cw"] * p["T"]) * math.sin(PI * x)     # wave on a string fixed at both ends


def _pde_exact(p: dict) -> float:
    return _pde_exact_at(_i(p["cas"]), 0.5, 0.5, p)


def _pde_run(p: dict) -> dict:
    cas, meth, n = _i(p["cas"]), _i(p["method"]), max(4, _i(p["n"]))
    n += n % 2
    h = 1.0 / n
    xs = [h * i for i in range(n + 1)]
    ex = _pde_exact(p)
    nu = float(0.0)
    if cas == 0:
        m = n + 1
        u = [[0.0] * m for _ in range(m)]
        for i in range(m):
            u[i][n] = math.sin(PI * xs[i])                 # u[i][j]: x index i, y index j; top edge y = 1
        w = 1.0
        if meth == 2:
            w = 2.0 / (1.0 + math.sin(PI / n))
        sweeps = 0
        for sweeps in range(1, 20001):
            if meth == 0:
                new = [row[:] for row in u]
                dm = 0.0
                for i in range(1, n):
                    for j in range(1, n):
                        new[i][j] = 0.25 * (u[i + 1][j] + u[i - 1][j] + u[i][j + 1] + u[i][j - 1])
                        dm = max(dm, abs(new[i][j] - u[i][j]))
                u = new
            else:
                dm = 0.0
                for i in range(1, n):
                    for j in range(1, n):
                        g = 0.25 * (u[i + 1][j] + u[i - 1][j] + u[i][j + 1] + u[i][j - 1])
                        dv = w * (g - u[i][j])
                        u[i][j] += dv
                        dm = max(dm, abs(dv))
            if dm < 1e-11:
                break
        val = u[n // 2][n // 2]
        cx = _grid(0.0, 1.0, 100)
        ce = [_pde_exact_at(0, c, 0.5, p) for c in cx]
        return _state(val, ex, sweeps, cx, ce, [], xs, [u[i][n // 2] for i in range(m)])
    T = p["T"]
    if cas == 1:                                          # heat equation, fixed time step dt = 'dt'
        al, dt = p["al"], p["dt"]
        steps = max(1, _i(T / dt))
        dt = T / steps
        r = al * dt / (h * h)
        u = [math.sin(PI * x) for x in xs]
        mi = n - 1
        for _ in range(steps):
            old = u[:]
            if meth == 0:                                 # FTCS
                for i in range(1, n):
                    u[i] = old[i] + r * (old[i + 1] - 2.0 * old[i] + old[i - 1])
            else:
                if meth == 1:                             # BTCS
                    rhs = old[1:n]
                    diag = [1.0 + 2.0 * r] * mi
                else:                                     # Crank-Nicolson
                    rhs = [old[i] + 0.5 * r * (old[i + 1] - 2.0 * old[i] + old[i - 1]) for i in range(1, n)]
                    diag = [1.0 + r] * mi
                off = -r if meth == 1 else -0.5 * r
                sol = _tri_solve(diag, off, rhs)
                u = [0.0] + sol + [0.0]
        val = u[n // 2]
        cx = _grid(0.0, 1.0, 100)
        ce = [_pde_exact_at(1, c, 0.0, p) for c in cx]
        return _state(val, ex, steps * n, cx, ce, [], xs, u, rnum=r)
    c, nu = p["cw"], p["nu"]                              # wave equation, leapfrog with Courant number nu = c dt / h
    dt = nu * h / c
    steps = max(1, _i(T / dt))
    u0 = [math.sin(PI * x) for x in xs]
    u1 = u0[:]
    for i in range(1, n):                                 # first step from u_t = 0
        u1[i] = u0[i] + 0.5 * nu * nu * (u0[i + 1] - 2.0 * u0[i] + u0[i - 1])
    for _ in range(steps - 1):
        u2 = u1[:]
        for i in range(1, n):
            u2[i] = 2.0 * u1[i] - u0[i] + nu * nu * (u1[i + 1] - 2.0 * u1[i] + u1[i - 1])
        u0, u1 = u1, u2
    tt = steps * dt
    val = u1[n // 2]
    ex = math.cos(PI * c * tt) * math.sin(PI * 0.5)
    cx = _grid(0.0, 1.0, 100)
    ce = [math.cos(PI * c * tt) * math.sin(PI * z) for z in cx]
    return _state(val, ex, steps * n, cx, ce, [], xs, u1, tend=tt)


CqPde = _mk({"cas": 0.0, "method": 2.0, "n": 10.0, "al": 1.0, "dt": 0.002, "T": 0.1, "cw": 1.0, "nu": 0.8}, _pde_run, "CqPde")


# ============================================================================================ Planck's law
H_SI = 6.62607015e-34              # exact in the 2019 SI
C_SI = 299792458.0                 # exact
K_SI = 1.380649e-23                # exact


def _pl_xstar() -> float:
    """The non-zero root of (x - 5) e^x + 5 = 0, by 200 bisections: the Wien displacement constant."""
    lo, hi = 4.0, 6.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if (mid - 5.0) * math.exp(mid) + 5.0 < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _pl_m(lam: float, T: float) -> float:
    return 2 * PI * H_SI * C_SI * C_SI / math.pow(lam, 5) / (math.exp(H_SI * C_SI / (lam * K_SI * T)) - 1.0)


def _pl_exact(p: dict) -> float:
    cas, T = _i(p["cas"]), p["T"]
    xs = _pl_xstar()
    if cas == 0:
        return 2 * math.pow(PI, 5) * math.pow(K_SI, 4) / (15 * math.pow(H_SI, 3) * C_SI * C_SI) * math.pow(T, 4)
    if cas == 1:
        return H_SI * C_SI / (K_SI * xs * T)
    if cas == 2:
        return (math.exp(xs) - 1.0) / xs
    return 1.0 - math.exp(-xs)


def _pl_peak(T: float, n: int) -> float:
    """Golden-section search for the maximum of M(lambda) between 0.2 and 5 times the textbook peak position."""
    g = 0.5 * (math.sqrt(5.0) - 1.0)
    a, b = 0.2 * 2.9e-3 / T, 5.0 * 2.9e-3 / T
    c = b - g * (b - a)
    d = a + g * (b - a)
    fc, fd = _pl_m(c, T), _pl_m(d, T)
    for _ in range(n):
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = _pl_m(c, T)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = _pl_m(d, T)
    return 0.5 * (a + b)


def _pl_run(p: dict) -> dict:
    cas, n, T = _i(p["cas"]), max(2, _i(p["n"])), p["T"]
    exact = _pl_exact(p)
    lp = 2.9e-3 / T
    if cas == 0:
        m = n + n % 2
        xmax = 50.0
        h = xmax / m
        s = 0.0                                          # Simpson on x^3/(e^x - 1), x = hc/(lambda k T); f(0) = 0
        for i in range(m + 1):
            x = h * i
            f = 0.0 if i == 0 else x * x * x / (math.exp(x) - 1.0)
            s += f * (1.0 if i == 0 or i == m else (4.0 if i % 2 == 1 else 2.0))
        integral = s * h / 3.0
        val = 2 * PI * math.pow(K_SI, 4) * math.pow(T, 4) / (math.pow(H_SI, 3) * C_SI * C_SI) * integral
        cx = _grid(0.0, 20.0, 120)
        ce = [0.0 if c == 0 else c * c * c / (math.exp(c) - 1.0) for c in cx]
        return _state(val, exact, m, cx, ce, [], [h * i for i in range(0, m + 1, max(1, m // 40))],
                      [0.0 if i == 0 else (h * i) ** 3 / (math.exp(h * i) - 1.0) for i in range(0, m + 1, max(1, m // 40))])
    lam = _pl_peak(T, n)
    x = H_SI * C_SI / (lam * K_SI * T)
    if cas == 1:
        val = lam
    elif cas == 2:
        val = (math.exp(x) - 1.0) / x
    else:
        val = 1.0 - math.exp(-x)
    cx = _grid(0.1 * lp, 5.0 * lp, 120)
    mp = _pl_m(lp, T)
    ce = [_pl_m(c, T) / mp for c in cx]
    cy = [min(1.6, (2 * PI * C_SI * K_SI * T / math.pow(c, 4)) / mp) for c in cx]
    return _state(val, exact, n, cx, ce, cy, [lam], [_pl_m(lam, T) / mp])


CqPlanck = _mk({"cas": 0.0, "n": 40.0, "T": 5772.0}, _pl_run, "CqPlanck")


# ============================================================================================ least-squares fitting
def _lcg_seed(seed: float) -> list[float]:
    s = _i(seed) % 2147483647
    return [float(s if s > 0 else 1)]


def _lcg_u(st: list[float]) -> float:
    st[0] = (st[0] * 16807.0) % 2147483647
    return st[0] / 2147483647


def _fit_true(cas: int, x: float, p: dict) -> float:
    if cas == 0:
        return p["a0"] + p["b0"] * x
    if cas == 1:
        return p["a0"] * math.pow(x, p["b0"])
    if cas == 2:
        return p["a0"] * math.exp(-x / p["b0"])
    return p["a0"] + p["b0"] * x + p["c0"] * x * x


def _fit_exact(p: dict) -> float:
    cas = _i(p["cas"])
    return p["c0"] if cas == 3 else p["b0"]


def _fit_solve(rows: list[list[float]], ys: list[float], wt: list[float]) -> tuple[list[float], list[float]]:
    """Weighted normal equations A^T W A c = A^T W y by Gauss elimination, and sqrt(diag of the inverse) for each c."""
    m = len(rows[0])
    ata = [[0.0] * m for _ in range(m)]
    aty = [0.0] * m
    for r, y, w in zip(rows, ys, wt):
        for i in range(m):
            aty[i] += w * r[i] * y
            for j in range(m):
                ata[i][j] += w * r[i] * r[j]
    c = _gauss_elim(ata, aty)
    sd = []
    for i in range(m):
        e = [1.0 if j == i else 0.0 for j in range(m)]
        col = _gauss_elim(ata, e)
        sd.append(math.sqrt(col[i]))
    return c, sd


def _fit_run(p: dict) -> dict:
    cas, N, wted, sig = _i(p["cas"]), max(4, _i(p["n"])), _i(p["wt"]), p["sig"]
    st = _lcg_seed(p["seed"])
    xs, ys, ss = [], [], []
    for i in range(N):
        x = p["x0"] + (p["x1"] - p["x0"]) * (i + 0.5) / N
        yt = _fit_true(cas, x, p)
        u1, u2 = _lcg_u(st), _lcg_u(st)
        g = math.sqrt(-2.0 * math.log(u1 if u1 > 1e-300 else 1e-300)) * math.cos(2 * PI * u2)
        xs.append(x)
        ys.append(yt * (1.0 + sig * g))
        ss.append(sig * abs(yt))
    if cas in (1, 2):                                      # linearise: ln y against ln x, or against x
        ly = [math.log(y) for y in ys]
        rows = [[1.0, math.log(x)] if cas == 1 else [1.0, x] for x in xs]
        wt = [1.0] * N
        c, sd = _fit_solve(rows, ly, wt)
        if cas == 1:
            val, unc = c[1], sd[1] * sig
            fitf = lambda x: math.exp(c[0]) * math.pow(x, c[1])        # noqa: E731
        else:
            val, unc = -1.0 / c[1], sd[1] * sig / (c[1] * c[1])
            fitf = lambda x: math.exp(c[0] + c[1] * x)                 # noqa: E731
    else:
        rows = [[1.0, x] if cas == 0 else [1.0, x, x * x] for x in xs]
        wt = [1.0 / (s * s) for s in ss] if wted == 1 else [1.0] * N
        c, sd = _fit_solve(rows, ys, wt)
        j = 1 if cas == 0 else 2
        val = c[j]
        if wted == 1:
            unc = sd[j]
        else:                                              # unweighted: scale by the scatter of the residuals
            ssr = 0.0
            for r, y in zip(rows, ys):
                f = sum(r[i] * c[i] for i in range(len(c)))
                ssr += (y - f) * (y - f)
            unc = sd[j] * math.sqrt(ssr / (N - len(c)))
        fitf = (lambda x: c[0] + c[1] * x) if cas == 0 else (lambda x: c[0] + c[1] * x + c[2] * x * x)   # noqa: E731
    cx = _grid(p["x0"], p["x1"], 80)
    stp = max(1, N // 60)
    return _state(val, _fit_exact(p), N, cx, [_fit_true(cas, x, p) for x in cx], [fitf(x) for x in cx],
                  xs[::stp], ys[::stp], unc=unc)


CqFit = _mk({"cas": 0.0, "wt": 1.0, "n": 200.0, "seed": 2024.0, "sig": 0.04, "x0": 1.0, "x1": 10.0, "a0": 2.0, "b0": 3.0,
             "c0": 0.5}, _fit_run, "CqFit")


# ============================================================================================ registration
def _slope(pts: list[list[float]]) -> float:
    """Least-squares slope of y on x (written out the same way on both sides)."""
    sx = sum(q[0] for q in pts)
    sy = sum(q[1] for q in pts)
    sxx = sum(q[0] * q[0] for q in pts)
    sxy = sum(q[0] * q[1] for q in pts)
    den = len(pts) * sxx - sx * sx
    if abs(den) < 1e-30:
        return 0.0
    return (len(pts) * sxy - sx * sy) / den


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


def _best(rows, p) -> float:
    rs = _rows(rows, "n", "val")
    if not rs:
        return 0.0
    best = rs[0]
    for r in rs:
        if r[0] > best[0]:
            best = r
    return best[1]


def _order(rows, p) -> float:
    return -_slope([[math.log(n), math.log(e)] for n, e in _rows(rows, "n", "err") if n > 0 and e > 0])


def _ratio(rows, p) -> float:
    """Error factor per iteration, exp(slope of ln(error) against n)."""
    pts = [[n, math.log(e)] for n, e in _rows(rows, "n", "err") if e > 1e-15]
    return math.exp(_slope(pts)) if len(pts) >= 2 else 0.0


KERNELS: dict[str, Any] = {"cq_fourier": CqFourier, "cq_dft": CqDft, "cq_gauss": CqGauss, "cq_schro": CqSchro,
                           "cq_special": CqSpecial, "cq_linsys": CqLinsys, "cq_eig": CqEig,
                           "cq_map": CqMap, "cq_lorenz": CqLorenz, "cq_bvp": CqBvp, "cq_pde": CqPde, "cq_planck": CqPlanck,
                           "cq_fit": CqFit}
FAMILY = {k: "comp" for k in KERNELS}

TEXTBOOK = {
    "cq_fourier_c": _four_exact,
    "cq_dft_F": _dft_exact,
    "cq_gauss_I": _gq_exact,
    "cq_schro_E": lambda p: _sch_setup(p)[4],
    "cq_special_v": _spec_exact,
    "cq_linsys_x": _ls_exact,
    "cq_eig_l": _eig_exact,
    "cq_map_r": _lm_exact,
    "cq_lorenz_det": lambda p: math.exp(-(p["sg"] + 1.0 + p["be"]) * p["T"]),
    "cq_bvp_y": _bvp_exact,
    "cq_pde_u": _pde_exact,
    "cq_planck_v": _pl_exact,
    "cq_fit_p": _fit_exact,
}

CALCS = {
    "cq_best": {"label": "best value", "unit": "", "needs": ["n", "val"], "fn": _best},
    "cq_order": {"label": "order of the method", "unit": "", "needs": ["n", "err"], "fn": _order},
    "cq_ratio": {"label": "error factor per iteration", "unit": "", "needs": ["n", "err"], "fn": _ratio},
}
