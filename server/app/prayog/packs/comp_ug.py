"""Kernel pack: the UG "Computational physics" practicals (DU / UGC LOCF Mathematical Physics, SEC Numerical
Techniques, Applied Dynamics, Statistical Mechanics labs).

A computational practical has no glassware, but it is still a real measurement: the student runs a NUMERICAL METHOD
at a chosen step size / sample count and compares the answer with the EXACT analytic value. The physics of the
practical is how that error falls as the step gets smaller - the order of the method.

So every kernel here has the same shape, which lets one studio rig (`comp-workstation`) serve them all:

    PARAMS  cas (which problem), method (which numerical method), n (steps / nodes / iterations) + the problem's own
            physical numbers
    init    runs the whole computation once and keeps the result
    step    advances a clock only (the computation is not a time evolution)
    view    val (the numerical answer), exact (the analytic answer), err (|val-exact|/|exact|), nused,
            and the curves the monitor draws: cx / ce (the exact function or solution), cy (what the method built),
            px / py (the nodes or iterates the method actually used)
    measure {val, exact, err, nused} - what the check compares

New physics never goes into `kernels.py`; this file and its EXACT JavaScript twin
`app/static/prayog/packs/comp_ug.js` carry it, with the same formulas in the same order, so both give the same
numbers. Everything is deterministic: no randomness anywhere but a seeded Lehmer generator, and no wall clock.

Kernels and the textbook value each one is checked against (1 %):
    cp_root    root of f(x) = 0 by bisection / Newton-Raphson / secant
                 x^m = a            -> a^(1/m)
                 floating sphere    -> d = R(1 + 2 cos(acos(1-2s)/3 + 4pi/3))  (cap volume = s x sphere volume)
                 alpha = tan alpha  -> the same equation solved to machine precision by 200 bisections
    cp_quad    definite integral by trapezoid / Simpson 1/3 / Simpson 3/8 / Gauss-Legendre
                 1/x -> ln(b/a);  A sin(wx) -> A(cos wa - cos wb)/w;  x^k -> (b^(k+1)-a^(k+1))/(k+1)
                 Lorentzian delta sequence -> (atan(b/eps) - atan(a/eps))/pi
    cp_ode1    first-order IVP by Euler / RK2 (Heun) / RK4
                 decay -> y0 e^(-lam t);  RC -> C E (1 - e^(-t/RC));  cooling -> Ts + (T0-Ts) e^(-kt)
                 logistic -> K y0 e^(rt) / (K + y0 (e^(rt) - 1))
    cp_diff    derivative from tabulated values: forward / backward / central / five-point, step h = h0/n
                 A sin(wx) -> A w cos(wx);  A e^(wx) -> A w e^(wx);  A x^k -> A k x^(k-1)
    cp_approx  f(x) from a Taylor partial sum or a Lagrange interpolating polynomial -> f(x) itself
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi


def _i(v: float) -> int:
    """Rounding written the same way on both sides (Python's round() is banker's, JavaScript's Math.round is not)."""
    return int(math.floor(v + 0.5))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


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


def _err(val: float, exact: float) -> float:
    return abs(val - exact) / max(abs(exact), 1e-30)


def _grid(a: float, b: float, m: int) -> list[float]:
    return [a + (b - a) * i / m for i in range(m + 1)]


# ============================================================================================ root finding
def _root_f(cas: int, x: float, p: dict) -> float:
    if cas == 1:                                   # floating sphere: cap volume = s x sphere volume
        R = p["R"]
        return x * x * x - 3 * R * x * x + 4 * p["s"] * R * R * R
    if cas == 2:
        return math.tan(x) - x
    return math.pow(x, p["m"]) - p["a"]


def _root_df(cas: int, x: float, p: dict) -> float:
    if cas == 1:
        return 3 * x * x - 6 * p["R"] * x
    if cas == 2:
        t = math.tan(x)
        return t * t
    return p["m"] * math.pow(x, p["m"] - 1)


def _bisect(cas: int, p: dict, a: float, b: float, iters: int) -> list[float]:
    """`iters` halvings of [a, b]; returns every midpoint, the last one being the answer."""
    fa = _root_f(cas, a, p)
    out = []
    for _ in range(iters):
        mid = 0.5 * (a + b)
        fm = _root_f(cas, mid, p)
        out.append(mid)
        if (fm < 0) == (fa < 0):
            a, fa = mid, fm
        else:
            b = mid
    return out


def _root_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if cas == 1:
        s = min(max(p["s"], 1e-9), 1 - 1e-9)
        return p["R"] * (1 + 2 * math.cos(math.acos(1 - 2 * s) / 3 + 4 * PI / 3))
    if cas == 2:                                   # no closed form: the same equation to machine precision
        xs = _bisect(2, p, p["xa"], p["xb"], 200)
        return xs[-1]
    return math.pow(p["a"], 1.0 / p["m"])


class CpRoot:
    """Root of f(x) = 0 three ways. The error after n iterations is the practical's real measurement:
    bisection halves it every step, Newton-Raphson roughly squares it, the secant method is in between."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 12.0, "a": 2.0, "m": 2.0, "R": 0.05, "s": 0.6,
              "x0": 1.0, "x1": 2.0, "xa": 0.0, "xb": 4.0}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(2, _i(p["n"]))
        xa, xb = p["xa"], p["xb"]
        if meth == 0:
            it = _bisect(cas, p, xa, xb, n)
        elif meth == 1:                            # Newton-Raphson from x0
            x, it = p["x0"], []
            for _ in range(n):
                d = _root_df(cas, x, p)
                if abs(d) < 1e-14:
                    break
                x = x - _root_f(cas, x, p) / d
                it.append(x)
        else:                                      # secant from the two starting guesses x0 and x1
            x0, x1, it = p["x0"], p["x1"], []
            f0, f1 = _root_f(cas, x0, p), _root_f(cas, x1, p)
            for _ in range(n):
                if abs(f1 - f0) < 1e-14:
                    break
                x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
                x0, f0, x1, f1 = x1, f1, x2, _root_f(cas, x2, p)
                it.append(x1)
        val = it[-1] if it else p["x0"]
        exact = _root_exact(p)
        cx = _grid(xa, xb, 60)
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(len(it)),
                "cx": cx, "ce": [_root_f(cas, x, p) for x in cx], "cy": [],
                "px": list(it), "py": [_root_f(cas, x, p) for x in it]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpRoot.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ quadrature
def _quad_f(cas: int, x: float, p: dict) -> float:
    if cas == 1:
        return p["A"] * math.sin(p["w"] * x)
    if cas == 2:
        return p["A"] * math.pow(x, p["kk"])
    if cas == 3:                                   # Lorentzian: one of the sequences that tend to a delta function
        e = p["eps"]
        return e / (PI * (x * x + e * e))
    return 1.0 / x


def _quad_exact(p: dict) -> float:
    cas = _i(p["cas"])
    a, b = p["xa"], p["xb"]
    if cas == 1:
        return p["A"] * (math.cos(p["w"] * a) - math.cos(p["w"] * b)) / p["w"]
    if cas == 2:
        k = p["kk"]
        return p["A"] * (math.pow(b, k + 1) - math.pow(a, k + 1)) / (k + 1)
    if cas == 3:
        return (math.atan(b / p["eps"]) - math.atan(a / p["eps"])) / PI
    return math.log(b / a)


def _gauleg(n: int, a: float, b: float) -> tuple[list[float], list[float]]:
    """Gauss-Legendre nodes and weights on [a, b]: Newton's method on the Legendre recurrence."""
    xs = [0.0] * n
    ws = [0.0] * n
    m = (n + 1) // 2
    xm, xl = 0.5 * (b + a), 0.5 * (b - a)
    for i in range(1, m + 1):
        z = math.cos(PI * (i - 0.25) / (n + 0.5))
        pp = 1.0
        for _ in range(60):
            p1, p2 = 1.0, 0.0
            for j in range(1, n + 1):
                p3 = p2
                p2 = p1
                p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j
            pp = n * (z * p1 - p2) / (z * z - 1.0)
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) <= 3e-15:
                break
        xs[i - 1] = xm - xl * z
        xs[n - i] = xm + xl * z
        ws[i - 1] = 2 * xl / ((1 - z * z) * pp * pp)
        ws[n - i] = ws[i - 1]
    return xs, ws


def _nq(meth: int, n: int) -> int:
    """Each rule needs its own kind of n: Simpson 1/3 an even number of strips, Simpson 3/8 a multiple of three."""
    if meth == 1:
        return max(2, n - (n % 2))
    if meth == 2:
        return max(3, n - (n % 3))
    if meth == 3:
        return max(1, min(64, n))          # Gauss-Legendre: real node tables stop well short of this
    return max(1, n)


class CpQuad:
    """A definite integral by four rules. Trapezoid error falls as h^2, Simpson as h^4, and Gauss-Legendre with
    n points is exact for every polynomial up to degree 2n-1."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 8.0, "xa": 1.0, "xb": 2.0, "A": 1.0, "w": 1.0, "kk": 2.0, "eps": 0.2}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = _nq(meth, max(1, _i(p["n"])))
        a, b = p["xa"], p["xb"]
        px: list[float] = []
        if meth == 3:
            xs, ws = _gauleg(n, a, b)
            val = 0.0
            for i in range(n):
                val += ws[i] * _quad_f(cas, xs[i], p)
            px = list(xs)
        else:
            h = (b - a) / n
            xs = [a + h * i for i in range(n + 1)]
            fs = [_quad_f(cas, x, p) for x in xs]
            if meth == 0:
                val = 0.5 * (fs[0] + fs[n])
                for i in range(1, n):
                    val += fs[i]
                val *= h
            elif meth == 1:
                val = fs[0] + fs[n]
                for i in range(1, n):
                    val += (4.0 if i % 2 == 1 else 2.0) * fs[i]
                val *= h / 3.0
            else:
                val = fs[0] + fs[n]
                for i in range(1, n):
                    val += (2.0 if i % 3 == 0 else 3.0) * fs[i]
                val *= 3.0 * h / 8.0
            px = list(xs)
        exact = _quad_exact(p)
        cx = _grid(a, b, 60)
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(n),
                "cx": cx, "ce": [_quad_f(cas, x, p) for x in cx], "cy": [],
                "px": px, "py": [_quad_f(cas, x, p) for x in px]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpQuad.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ first-order IVP
def _ode1_f(cas: int, t: float, y: float, p: dict) -> float:
    if cas == 1:                                   # RC charging: R dq/dt + q/C = E
        return (p["Em"] - y / p["Cc"]) / p["Rr"]
    if cas == 2:                                   # Newton's law of cooling
        return -p["kk"] * (y - p["Ts"])
    if cas == 3:                                   # logistic growth / autocatalysis
        return p["rr"] * y * (1 - y / p["Kk"])
    return -p["lam"] * y                           # radioactive decay


def _ode1_exact(cas: int, t: float, p: dict) -> float:
    if cas == 1:
        return p["Cc"] * p["Em"] * (1 - math.exp(-t / (p["Rr"] * p["Cc"]))) + p["y0"] * math.exp(-t / (p["Rr"] * p["Cc"]))
    if cas == 2:
        return p["Ts"] + (p["y0"] - p["Ts"]) * math.exp(-p["kk"] * t)
    if cas == 3:
        e = math.exp(p["rr"] * t)
        return p["Kk"] * p["y0"] * e / (p["Kk"] + p["y0"] * (e - 1))
    return p["y0"] * math.exp(-p["lam"] * t)


class CpOde1:
    """dy/dt = f(t, y) by Euler, RK2 (Heun) and RK4 over [0, tmax] in n steps. The global error falls as h,
    h^2 and h^4: that is what the student measures against the known analytic solution."""

    PARAMS = {"cas": 0.0, "method": 2.0, "n": 20.0, "y0": 1.0, "tmax": 10.0, "lam": 0.1,
              "Rr": 1000.0, "Cc": 0.001, "Em": 5.0, "kk": 0.02, "Ts": 30.0, "rr": 0.5, "Kk": 1000.0}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(1, _i(p["n"]))
        tmax = p["tmax"]
        h = tmax / n
        t, y = 0.0, p["y0"]
        px, py = [0.0], [y]
        for _ in range(n):
            if meth == 0:
                y = y + h * _ode1_f(cas, t, y, p)
            elif meth == 1:
                k1 = _ode1_f(cas, t, y, p)
                k2 = _ode1_f(cas, t + h, y + h * k1, p)
                y = y + h * 0.5 * (k1 + k2)
            else:
                k1 = _ode1_f(cas, t, y, p)
                k2 = _ode1_f(cas, t + h / 2, y + h / 2 * k1, p)
                k3 = _ode1_f(cas, t + h / 2, y + h / 2 * k2, p)
                k4 = _ode1_f(cas, t + h, y + h * k3, p)
                y = y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            t = t + h
            px.append(t)
            py.append(y)
        exact = _ode1_exact(cas, tmax, p)
        cx = _grid(0.0, tmax, 60)
        return {"t": 0.0, "val": y, "exact": exact, "err": _err(y, exact), "nused": float(n),
                "cx": cx, "ce": [_ode1_exact(cas, x, p) for x in cx], "cy": list(py),
                "px": list(px), "py": list(py)}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpOde1.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ differentiation
def _fd_f(cas: int, x: float, p: dict) -> float:
    if cas == 1:
        return p["A"] * math.exp(p["w"] * x)
    if cas == 2:
        return p["A"] * math.pow(x, p["kk"])
    return p["A"] * math.sin(p["w"] * x)


def _fd_exact(p: dict) -> float:
    cas = _i(p["cas"])
    x = p["x"]
    if cas == 1:
        return p["A"] * p["w"] * math.exp(p["w"] * x)
    if cas == 2:
        return p["A"] * p["kk"] * math.pow(x, p["kk"] - 1)
    return p["A"] * p["w"] * math.cos(p["w"] * x)


class CpDiff:
    """The derivative of a tabulated quantity at x, from values a step h = h0/n apart. Forward and backward
    differences are first order in h, the central difference second, the five-point formula fourth - until h is
    so small that the round-off in the subtraction of two nearly equal numbers takes over."""

    PARAMS = {"cas": 0.0, "method": 2.0, "n": 10.0, "x": 1.0, "h0": 0.4, "A": 1.0, "w": 2.0, "kk": 3.0}
    VARS = ["t", "val", "exact", "err", "nused", "hstep", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(1, _i(p["n"]))
        h = p["h0"] / n
        x = p["x"]
        f = lambda z: _fd_f(cas, z, p)             # noqa: E731 - the same shape as the JS twin
        if meth == 0:
            val = (f(x + h) - f(x)) / h
            px = [x, x + h]
        elif meth == 1:
            val = (f(x) - f(x - h)) / h
            px = [x - h, x]
        elif meth == 2:
            val = (f(x + h) - f(x - h)) / (2 * h)
            px = [x - h, x, x + h]
        else:
            val = (-f(x + 2 * h) + 8 * f(x + h) - 8 * f(x - h) + f(x - 2 * h)) / (12 * h)
            px = [x - 2 * h, x - h, x, x + h, x + 2 * h]
        exact = _fd_exact(p)
        half = max(2 * p["h0"], abs(x) * 0.6, 1e-6)
        cx = _grid(x - half, x + half, 60)
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(n), "hstep": h,
                "cx": cx, "ce": [f(z) for z in cx],
                "cy": [f(x) + exact * (z - x) for z in cx],    # the true tangent, for the eye
                "px": px, "py": [f(z) for z in px]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpDiff.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ series / interpolation
def _ap_f(cas: int, x: float) -> float:
    if cas == 1:
        return math.sin(x)
    if cas == 2:
        return math.cos(x)
    if cas == 3:
        return math.log(1 + x)
    return math.exp(x)


def _taylor(cas: int, x: float, n: int) -> float:
    """The first n terms of the Maclaurin series, summed in order (term k built from term k-1)."""
    if cas == 1 or cas == 2:
        s = 0.0
        term = x if cas == 1 else 1.0
        k = 1 if cas == 1 else 0
        for _ in range(n):
            s += term
            term = -term * x * x / ((k + 1) * (k + 2))
            k += 2
        return s
    if cas == 3:
        s = 0.0
        term = x
        for k in range(1, n + 1):
            s += term / k
            term = -term * x
        return s
    s = 0.0
    term = 1.0
    for k in range(1, n + 1):
        s += term
        term = term * x / k
    return s


def _lagrange(cas: int, x: float, p: dict, n: int) -> tuple[float, list[float]]:
    """Lagrange polynomial through n+1 equally spaced nodes on [xa, xb], evaluated at x."""
    nodes = _grid(p["xa"], p["xb"], n)
    val = 0.0
    for i in range(n + 1):
        term = _ap_f(cas, nodes[i])
        for j in range(n + 1):
            if j != i:
                term *= (x - nodes[j]) / (nodes[i] - nodes[j])
        val += term
    return val, nodes


class CpApprox:
    """A function value from a Taylor partial sum or from a Lagrange interpolating polynomial, against the
    function itself: the truncation error is what the student measures."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 6.0, "x": 1.0, "xa": 0.0, "xb": 2.0}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(1, _i(p["n"]))
        if meth == 1:
            val, nodes = _lagrange(cas, p["x"], p, n)
            px = list(nodes)
        else:
            val = _taylor(cas, p["x"], n)
            px = [p["x"]]
        exact = _ap_f(cas, p["x"])
        cx = _grid(p["xa"], p["xb"], 60)
        if meth == 1:
            cy = [_lagrange(cas, z, p, n)[0] for z in cx]
        else:
            cy = [_taylor(cas, z, n) for z in cx]
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(n),
                "cx": cx, "ce": [_ap_f(cas, z) for z in cx], "cy": cy,
                "px": px, "py": [_ap_f(cas, z) for z in px]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpApprox.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}



# ============================================================================================ second-order IVP
def _ode2_rates(p: dict) -> tuple[float, float]:
    """(gamma, omega0) of  m x" + c x' + k x = F cos(wf t)."""
    return p["cc"] / (2 * p["mm"]), math.sqrt(p["kk"] / p["mm"])


def _ode2_exact(t: float, p: dict) -> float:
    """The closed-form free motion for x(0) = x0, v(0) = 0, in whichever damping regime the numbers give."""
    g, w0 = _ode2_rates(p)
    x0 = p["x0"]
    if g <= 1e-12 * max(w0, 1.0):
        return x0 * math.cos(w0 * t)
    if abs(g - w0) <= 1e-8 * w0:                       # critically damped
        return x0 * math.exp(-g * t) * (1 + g * t)
    if g < w0:                                         # underdamped
        wd = math.sqrt(w0 * w0 - g * g)
        return x0 * math.exp(-g * t) * (math.cos(wd * t) + (g / wd) * math.sin(wd * t))
    rt = math.sqrt(g * g - w0 * w0)                    # overdamped
    rp, rm = -g + rt, -g - rt
    A = -x0 * rm / (rp - rm)
    B = x0 * rp / (rp - rm)
    return A * math.exp(rp * t) + B * math.exp(rm * t)


def _ode2_amp(p: dict) -> float:
    """Steady-state amplitude of the driven oscillator: (F/m) / sqrt((w0^2 - w^2)^2 + (2 g w)^2)."""
    g, w0 = _ode2_rates(p)
    w = p["wf"]
    return (p["FF"] / p["mm"]) / math.sqrt((w0 * w0 - w * w) ** 2 + (2 * g * w) ** 2)


def _ode2_truth(p: dict) -> float:
    return _ode2_amp(p) if _i(p["cas"]) == 1 else _ode2_exact(p["tmax"], p)


class CpOde2:
    """m x" + c x' + k x = F cos(wt) - the mechanical oscillator and, with m -> L, c -> R, k -> 1/C, the LCR
    circuit. Free motion is compared with the closed form of its own damping regime; the driven case is compared
    with the resonance formula for the steady-state amplitude."""

    PARAMS = {"cas": 0.0, "method": 2.0, "n": 200.0, "mm": 1.0, "cc": 0.0, "kk": 4.0, "FF": 0.0, "wf": 1.0,
              "x0": 0.1, "tmax": 10.0}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(2, _i(p["n"]))
        h = p["tmax"] / n
        m, c, k, F, wf = p["mm"], p["cc"], p["kk"], p["FF"], p["wf"]
        f = lambda t, y: [y[1], (F * math.cos(wf * t) - c * y[1] - k * y[0]) / m]   # noqa: E731
        y = [p["x0"], 0.0]
        t = 0.0
        px, py = [0.0], [y[0]]
        for _ in range(n):
            if meth == 0:
                d = f(t, y)
                y = [y[0] + h * d[0], y[1] + h * d[1]]
            elif meth == 1:
                k1 = f(t, y)
                k2 = f(t + h, [y[0] + h * k1[0], y[1] + h * k1[1]])
                y = [y[0] + h * 0.5 * (k1[0] + k2[0]), y[1] + h * 0.5 * (k1[1] + k2[1])]
            else:
                k1 = f(t, y)
                k2 = f(t + h / 2, [y[0] + h / 2 * k1[0], y[1] + h / 2 * k1[1]])
                k3 = f(t + h / 2, [y[0] + h / 2 * k2[0], y[1] + h / 2 * k2[1]])
                k4 = f(t + h, [y[0] + h * k3[0], y[1] + h * k3[1]])
                y = [y[0] + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]),
                     y[1] + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])]
            t += h
            px.append(t)
            py.append(y[0])
        if cas == 1:                                   # the driven amplitude, from the last fifth of the run
            t0 = p["tmax"] * 0.8
            amp = 0.0
            for i in range(len(px)):
                if px[i] >= t0 and abs(py[i]) > amp:
                    amp = abs(py[i])
            val, exact = amp, _ode2_amp(p)
            ce = [_ode2_amp(p) for _ in range(61)]
        else:
            val, exact = y[0], _ode2_exact(p["tmax"], p)
            ce = None
        cx = _grid(0.0, p["tmax"], 60)
        if ce is None:
            ce = [_ode2_exact(z, p) for z in cx]
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(n),
                "cx": cx, "ce": ce, "cy": list(py), "px": list(px), "py": list(py)}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpOde2.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ Monte Carlo
_LCG_M = 2147483647


def _lcg(seed: float) -> list[float]:
    """Lehmer generator (minimal standard, 16807): one mutable slot, so both languages step it identically."""
    s = _i(seed) % _LCG_M
    return [float(s if s > 0 else 1)]


def _u(st: list[float]) -> float:
    st[0] = (st[0] * 16807.0) % _LCG_M
    return st[0] / _LCG_M


def _gauss2(st: list[float]) -> tuple[float, float]:
    """One Box-Muller pair from two uniforms."""
    u1 = _u(st)
    u2 = _u(st)
    r = math.sqrt(-2.0 * math.log(u1 if u1 > 1e-300 else 1e-300))
    return r * math.cos(2 * PI * u2), r * math.sin(2 * PI * u2)


def _binom(m: int, kk: int) -> float:
    """C(m, k) / 2^m - the exact macrostate probability of k heads in m tosses."""
    c = 1.0
    for i in range(1, kk + 1):
        c = c * (m - kk + i) / i
    return c / math.pow(2.0, m)


def _mc_exact(p: dict) -> float:
    cas = _i(p["cas"])
    if cas == 1:
        return math.e - 1.0
    if cas == 2:
        return 0.5
    if cas == 3:
        return _binom(_i(p["mtoss"]), _i(p["khead"]))
    if cas == 4:
        return 1.0 / math.sqrt(12.0 * _i(p["mtoss"]))
    if cas == 5:
        return 1.0 / p["rate"]
    if cas == 6:
        sx, sy, rho = p["sx"], p["sy"], p["rho"]
        x0, y0 = p["mx"], p["my"]
        return math.sqrt(y0 * y0 * sx * sx + x0 * x0 * sy * sy + 2 * x0 * y0 * rho * sx * sy)
    return PI


def _mc_run(p: dict, N: int, marks: list[int]) -> tuple[float, list[float]]:
    """The estimate from N samples, and the running estimate at each mark (for the screen)."""
    cas = _i(p["cas"])
    st = _lcg(p["seed"])
    hit = 0.0
    tot = 0.0
    sq = 0.0
    out = []
    mi = 0
    m = max(1, _i(p["mtoss"]))
    kk = _i(p["khead"])
    for i in range(1, N + 1):
        if cas == 0:
            x, y = _u(st), _u(st)
            if x * x + y * y <= 1.0:
                hit += 1
            est = 4.0 * hit / i
        elif cas == 1:
            tot += math.exp(_u(st))
            est = tot / i
        elif cas == 2:
            tot += _u(st)
            est = tot / i
        elif cas == 3:
            h = 0
            for _ in range(m):
                if _u(st) < 0.5:
                    h += 1
            if h == kk:
                hit += 1
            est = hit / i
        elif cas == 4:                                 # the central limit theorem: the spread of the mean of m
            g = 0.0
            for _ in range(m):
                g += _u(st)
            g = g / m
            tot += g
            sq += g * g
            v = sq / i - (tot / i) * (tot / i)
            est = math.sqrt(v if v > 0 else 0.0)
        elif cas == 5:                                 # exponential waiting times by the inverse transform
            tot += -math.log(_u(st)) / p["rate"]
            est = tot / i
        else:                                          # error propagation: the spread of f = x y
            z1, z2 = _gauss2(st)
            xx = p["mx"] + p["sx"] * z1
            yy = p["my"] + p["sy"] * (p["rho"] * z1 + math.sqrt(1 - p["rho"] * p["rho"]) * z2)
            fv = xx * yy
            tot += fv
            sq += fv * fv
            v = sq / i - (tot / i) * (tot / i)
            est = math.sqrt(v if v > 0 else 0.0)
        while mi < len(marks) and marks[mi] == i:
            out.append(est)
            mi += 1
    while len(out) < len(marks):
        out.append(est if N > 0 else 0.0)
    return est, out


def _mc_marks(N: int) -> list[int]:
    """60 sample counts spread logarithmically up to N: the screen's running-estimate curve."""
    out = []
    for i in range(1, 61):
        v = _i(math.pow(float(N), i / 60.0))
        if v < 1:
            v = 1
        if not out or v > out[-1]:
            out.append(v)
    return out


class CpMonteCarlo:
    """Monte Carlo and sampling statistics with a seeded Lehmer generator: pi by acceptance-rejection, an integral
    by the sample mean, coin-toss macrostates, the central limit theorem, an exponential population mean, and the
    error-propagation formula checked against the scatter of a function of two correlated variables.
    The error falls as 1/sqrt(N) - which is the real lesson, and is measurable here."""

    PARAMS = {"cas": 0.0, "method": 0.0, "n": 4000.0, "seed": 12345.0, "mtoss": 10.0, "khead": 5.0,
              "rate": 0.5, "mx": 4.0, "my": 2.5, "sx": 0.08, "sy": 0.05, "rho": 0.0}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py"]

    @staticmethod
    def init(p, cfg=None):
        N = max(10, _i(p["n"]))
        marks = _mc_marks(N)
        val, run = _mc_run(p, N, marks)
        exact = _mc_exact(p)
        cx = [float(x) for x in marks]
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(N),
                "cx": cx, "ce": [exact for _ in cx], "cy": list(run), "px": [cx[-1]], "py": [val]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpMonteCarlo.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


# ============================================================================================ projectile
def _proj_exact(p: dict) -> float:
    cas = _i(p["cas"])
    u, th, g = p["u"], p["th"], p["g"]
    if cas == 1:
        return u * u * math.sin(th) * math.sin(th) / (2 * g)
    if cas == 2:
        return 2 * u * math.sin(th) / g
    return u * u * math.sin(2 * th) / g


class CpProjectile:
    """A projectile integrated step by step: the range, the greatest height and the time of flight come out of the
    trajectory (with the landing point found by interpolating the last step), and each is compared with the
    textbook formula for motion under gravity alone."""

    PARAMS = {"cas": 0.0, "method": 2.0, "n": 100.0, "u": 30.0, "th": 0.7854, "g": 9.8}
    VARS = ["t", "val", "exact", "err", "nused", "cx", "ce", "cy", "px", "py", "tflight", "hmax", "range_m"]

    @staticmethod
    def init(p, cfg=None):
        cas, meth = _i(p["cas"]), _i(p["method"])
        n = max(4, _i(p["n"]))
        u, th, g = p["u"], p["th"], p["g"]
        tend = 2 * u * math.sin(th) / g
        h = (tend * 1.2) / n                           # the grid is laid over a fifth more than the flight needs
        f = lambda y: [y[2], y[3], 0.0, -g]            # noqa: E731 - state is [x, y, vx, vy]
        y = [0.0, 0.0, u * math.cos(th), u * math.sin(th)]
        px, py = [0.0], [0.0]
        hmax = 0.0
        tf = 0.0
        rng = 0.0
        t = 0.0
        for _ in range(n):
            prev = list(y)
            if meth == 0:
                d = f(y)
                y = [y[i] + h * d[i] for i in range(4)]
            elif meth == 1:
                k1 = f(y)
                k2 = f([y[i] + h * k1[i] for i in range(4)])
                y = [y[i] + h * 0.5 * (k1[i] + k2[i]) for i in range(4)]
            else:
                k1 = f(y)
                k2 = f([y[i] + h / 2 * k1[i] for i in range(4)])
                k3 = f([y[i] + h / 2 * k2[i] for i in range(4)])
                k4 = f([y[i] + h * k3[i] for i in range(4)])
                y = [y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(4)]
            t += h
            if y[1] > hmax:
                hmax = y[1]
            if prev[1] >= 0 > y[1] and tf == 0.0:      # landing: interpolate the step that crosses the ground
                fr = prev[1] / (prev[1] - y[1])
                tf = t - h + fr * h
                rng = prev[0] + fr * (y[0] - prev[0])
            if tf == 0.0 or len(px) < 2:
                px.append(y[0])
                py.append(y[1])
        if tf == 0.0:                                  # never came down inside the grid: report what there is
            tf = t
            rng = y[0]
        val = [rng, hmax, tf][cas] if cas in (0, 1, 2) else rng
        exact = _proj_exact(p)
        R = _proj_exact({**p, "cas": 0.0})
        cx = _grid(0.0, R, 60)
        ce = [z * math.tan(th) - g * z * z / (2 * u * u * math.cos(th) * math.cos(th)) for z in cx]
        return {"t": 0.0, "val": val, "exact": exact, "err": _err(val, exact), "nused": float(n),
                "cx": cx, "ce": ce, "cy": [], "px": list(px), "py": list(py),
                "tflight": tf, "hmax": hmax, "range_m": rng}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return dict(s)

    @staticmethod
    def measure(p, cfg=None):
        s = CpProjectile.init(p)
        return {"val": s["val"], "exact": s["exact"], "err": s["err"], "nused": s["nused"]}


KERNELS: dict[str, Any] = {"cp_root": CpRoot, "cp_quad": CpQuad, "cp_ode1": CpOde1, "cp_diff": CpDiff,
                           "cp_approx": CpApprox, "cp_ode2": CpOde2, "cp_mc": CpMonteCarlo, "cp_proj": CpProjectile}
FAMILY = {"cp_root": "comp", "cp_quad": "comp", "cp_ode1": "comp", "cp_diff": "comp", "cp_approx": "comp",
          "cp_ode2": "comp", "cp_mc": "comp", "cp_proj": "comp"}

TEXTBOOK = {
    "cp_root_x": _root_exact,
    "cp_quad_I": _quad_exact,
    "cp_ode1_y": lambda p: _ode1_exact(_i(p["cas"]), p["tmax"], p),
    "cp_diff_d": _fd_exact,
    "cp_approx_f": lambda p: _ap_f(_i(p["cas"]), p["x"]),
    "cp_ode2_x": _ode2_truth,
    "cp_mc_v": _mc_exact,
    "cp_proj_v": _proj_exact,
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
    """The order of the method, from the slope of log(error) against log(n): err ~ n^-order."""
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
    "cp_best": {"label": "best value", "unit": "", "needs": ["n", "val"], "fn": _best},
    "cp_order": {"label": "order of the method", "unit": "", "needs": ["n", "err"], "fn": _order},
    "cp_mean_val": {"label": "mean value", "unit": "", "needs": ["val"],
                    "fn": lambda rows, p: _mean([v for (v,) in _rows(rows, "val")])},
}
