"""Prayogshala kernels: the TRUE behaviour of every lab, in code (never in a prompt).

Each kernel has a JavaScript twin in `static/prayog/kernels.js` that runs on the learner's phone. The twin must give the
SAME numbers (tests/test_v0409_prayog.py runs both on the same inputs), so a slip on either side shows up at once.

Kernel shape (both languages):
    PARAMS            defaults, SI units
    vars(cfg)         names a lab may bind bodies / instruments to
    init(p, cfg)      -> state dict
    step(s, p, dt, cfg)   advance the state by dt seconds (static kernels: nothing)
    view(s, p, cfg)   -> {var: number | list}
    measure(p, cfg)   -> readings an experiment takes, FROM the simulation (period from zero crossings, null point by
                      bisection, image from traced rays...)
TEXTBOOK[name](p) is the NCERT formula a reading is checked against (tolerance 1 %); CALCS[name](rows, p) turns a
learner's observation table into the result (g, k, mu, n, v...). Algorithms here and in the JS twin must stay
step-for-step identical.
"""
from __future__ import annotations

import math
from typing import Any, Callable

PI = math.pi
MU0 = 4e-7 * PI
H = 0.0005            # integration sub-step (s) for the mechanical kernels


def _rk4(f: Callable, y: list[float], h: float) -> list[float]:
    k1 = f(y)
    k2 = f([y[i] + h / 2 * k1[i] for i in range(len(y))])
    k3 = f([y[i] + h / 2 * k2[i] for i in range(len(y))])
    k4 = f([y[i] + h * k3[i] for i in range(len(y))])
    return [y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(len(y))]


def _sub(dt: float, h: float) -> tuple[int, float]:
    n = max(1, int(math.ceil(dt / h - 1e-9)))
    return n, dt / n


def _period(f: Callable, y0: list[float], h: float, tmax: float) -> float:
    """Time between two successive downward zero crossings of y[0] (linear interpolation)."""
    y, t, cross = list(y0), 0.0, []
    while t < tmax and len(cross) < 2:
        y2 = _rk4(f, y, h)
        if y[0] > 0 >= y2[0]:
            cross.append(t + h * y[0] / (y[0] - y2[0]))
        y, t = y2, t + h
    return cross[1] - cross[0] if len(cross) == 2 else 0.0


# ------------------------------------------------------------------------------------------------ mechanics
def _pend_f(p):
    g, L, b = p["g"], p["L"], p["b"]
    return lambda y: [y[1], -(g / L) * math.sin(y[0]) - b * y[1]]


class Pendulum:
    PARAMS = {"L": 1.0, "g": 9.8, "theta0": 0.0873, "b": 0.0}
    VARS = ["t", "theta", "bob_x", "bob_y", "omega"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["theta0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _pend_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        th = s["y"][0]
        return {"t": s["t"], "theta": th, "omega": s["y"][1], "bob_x": p["L"] * math.sin(th), "bob_y": -p["L"] * math.cos(th)}

    @staticmethod
    def measure(p, cfg=None):
        return {"T": _period(_pend_f(p), [p["theta0"], 0.0], H, 60.0)}


def _spring_f(p):
    k, m, c = p["k"], p["m"], p["c"]
    return lambda y: [y[1], -(k / m) * y[0] - (c / m) * y[1]]


class Spring:
    PARAMS = {"k": 20.0, "m": 0.2, "c": 0.0, "g": 9.8, "x0": 0.03, "L0": 0.15}
    VARS = ["t", "x", "ext", "bob_y", "v"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["x0"], 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        f = _spring_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        ext = p["m"] * p["g"] / p["k"] + s["y"][0]
        return {"t": s["t"], "x": s["y"][0], "v": s["y"][1], "ext": ext, "bob_y": -(p["L0"] + ext)}

    @staticmethod
    def measure(p, cfg=None):
        T = _period(_spring_f(p), [p["x0"], 0.0], H, 60.0)
        q = dict(p, c=2 * math.sqrt(p["k"] * p["m"]))          # critically damped: settles at the static extension
        y, t = [p["x0"], 0.0], 0.0
        f = _spring_f(q)
        while t < 20.0:
            y = _rk4(f, y, 0.002)
            t += 0.002
        return {"T": T, "ext": p["m"] * p["g"] / p["k"] + y[0]}


class Incline:
    """Block on a rough incline, pulled up the slope by F. One friction coefficient (static = kinetic, said in the lab)."""
    PARAMS = {"angle": 0.5236, "mu": 0.3, "m": 1.0, "F": 0.0, "g": 9.8, "len": 1.5}
    VARS = ["t", "s", "v", "a", "px", "py", "moving"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "s": p["len"] * 0.2, "v": 0.0, "a": 0.0}

    @staticmethod
    def _adv(s, p, h):
        m, g, th, mu, F = p["m"], p["g"], p["angle"], p["mu"], p["F"]
        drive = F - m * g * math.sin(th)
        fr = mu * m * g * math.cos(th)
        if s["v"] == 0.0:
            if abs(drive) <= fr:
                s["a"] = 0.0
                return
            a = (drive - fr * (1.0 if drive > 0 else -1.0)) / m
        else:
            a = (drive - fr * (1.0 if s["v"] > 0 else -1.0)) / m
        v2 = s["v"] + a * h
        if s["v"] != 0.0 and (v2 > 0) != (s["v"] > 0):
            s["s"] += s["v"] * s["v"] / (-2 * a) if a != 0 else 0.0
            s["v"], s["a"] = 0.0, 0.0
            return
        s["s"] += s["v"] * h + 0.5 * a * h * h
        s["v"], s["a"] = v2, a
        if s["s"] <= 0.0 or s["s"] >= p["len"]:
            s["s"] = min(max(s["s"], 0.0), p["len"])
            s["v"], s["a"] = 0.0, 0.0

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.002)
        for _ in range(n):
            Incline._adv(s, p, h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "s": s["s"], "v": s["v"], "a": s["a"], "px": s["s"] * math.cos(p["angle"]),
                "py": s["s"] * math.sin(p["angle"]), "moving": 1.0 if s["v"] != 0.0 else 0.0}

    @staticmethod
    def _moves(p, F):
        q = dict(p, F=F, len=1e6)
        s = {"t": 0.0, "s": 1.0, "v": 0.0, "a": 0.0}
        for _ in range(250):
            Incline._adv(s, q, 0.002)
        return s["s"] > 1.0 + 1e-9

    @staticmethod
    def measure(p, cfg=None):
        lo, hi = 0.0, 4 * p["m"] * p["g"] + 1.0
        for _ in range(60):                          # smallest pull that starts the block moving UP the slope
            mid = (lo + hi) / 2
            if Incline._moves(p, mid):
                hi = mid
            else:
                lo = mid
        q = dict(p, len=1e6)
        s = {"t": 0.0, "s": 1.0, "v": 0.0, "a": 0.0}
        for _ in range(500):                         # 1 s from rest
            Incline._adv(s, q, 0.002)
        return {"F_min": hi, "a": 2 * (s["s"] - 1.0)}


def _stokes_f(p):
    a0 = p["g"] * (1 - p["sigma"] / p["rho"])
    b = 9 * p["eta"] / (2 * p["rho"] * p["r"] ** 2)
    return lambda y: [y[1], a0 - b * y[1]]


def _stokes_h(p):
    tau = 2 * p["rho"] * p["r"] ** 2 / (9 * p["eta"])
    return min(0.002, tau / 20), tau


class Stokes:
    """Steel ball falling through glycerine: weight - buoyancy - 6 pi eta r v."""
    PARAMS = {"r": 0.001, "rho": 7800.0, "sigma": 1260.0, "eta": 1.49, "g": 9.8, "depth": 0.8}
    VARS = ["t", "y", "v", "ball_y"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [0.0, 0.0]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        if s["y"][0] >= p["depth"]:
            s["t"] += dt
            return
        h0, _ = _stokes_h(p)
        n, h = _sub(dt, h0)
        f = _stokes_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        if s["y"][0] >= p["depth"]:
            s["y"] = [p["depth"], 0.0]
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "y": s["y"][0], "v": s["y"][1], "ball_y": -s["y"][0]}

    @staticmethod
    def measure(p, cfg=None):
        h, tau = _stokes_h(p)
        y, t, f = [0.0, 0.0], 0.0, _stokes_f(p)
        while t < 40 * tau + 0.01:
            y = _rk4(f, y, h)
            t += h
        return {"v_t": y[1]}


# ------------------------------------------------------------------------------------------------ heat
class Cooling:
    PARAMS = {"T0": 90.0, "Ts": 30.0, "k": 0.02}
    VARS = ["t", "T"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["T0"]]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.05)
        f = lambda y: [-p["k"] * (y[0] - p["Ts"])]
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "T": s["y"][0]}

    @staticmethod
    def measure(p, cfg=None):
        s = Cooling.init(p)
        for _ in range(60):
            Cooling.step(s, p, 1.0)
        return {"T60": s["y"][0]}


class Boyle:
    """Gas in a syringe at fixed temperature: the gauge reads P = nRT / V (ideal gas). Particles drawn are illustrative."""
    PARAMS = {"n": 0.004, "Temp": 300.0, "V": 1e-4, "R": 8.314, "area": 1e-3}
    VARS = ["P", "P_kPa", "V_mL", "PV", "piston_h"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        P = p["n"] * p["R"] * p["Temp"] / p["V"]
        return {"P": P, "P_kPa": P / 1000, "V_mL": p["V"] * 1e6, "PV": P * p["V"], "piston_h": p["V"] / p["area"]}

    @staticmethod
    def measure(p, cfg=None):
        return {"P": Boyle.view({}, p)["P"]}


def _mix_f(p):
    C1 = p["m1"] * p["c1"]
    C2 = p["m2"] * p["c2"] + p["mc"] * p["cc"]
    return lambda y: [-p["hA"] * (y[0] - y[1]) / C1, p["hA"] * (y[0] - y[1]) / C2]


class Mixtures:
    """Hot solid dropped into water in a calorimeter; heat flows until both share one temperature (no loss)."""
    PARAMS = {"m1": 0.1, "c1": 900.0, "T1": 100.0, "m2": 0.15, "c2": 4186.0, "T2": 25.0, "mc": 0.05, "cc": 385.0, "hA": 5.0}
    VARS = ["t", "Ts", "Tw"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": [p["T1"], p["T2"]]}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n, h = _sub(dt, 0.1)
        f = _mix_f(p)
        for _ in range(n):
            s["y"] = _rk4(f, s["y"], h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "Ts": s["y"][0], "Tw": s["y"][1]}

    @staticmethod
    def measure(p, cfg=None):
        y, t, f = [p["T1"], p["T2"]], 0.0, _mix_f(p)
        while t < 3000.0 and abs(y[0] - y[1]) > 1e-7:
            y = _rk4(f, y, 0.1)
            t += 0.1
        return {"Tf": y[1]}


# ------------------------------------------------------------------------------------------------ waves
def _sound_v(Tc: float) -> float:
    return 331.3 * math.sqrt(1 + Tc / 273.15)


class Resonance:
    """Closed tube over water + tuning fork. Loudness peaks when h + 0.3 d = (2n - 1) lambda / 4."""
    PARAMS = {"f": 512.0, "Tc": 20.0, "d": 0.04, "h": 0.12, "damp": 0.03}
    VARS = ["loud", "h", "v", "lambda", "water_y"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _loud(p, h):
        k = 2 * PI * p["f"] / _sound_v(p["Tc"])
        c = math.cos(k * (h + 0.3 * p["d"]))
        return p["damp"] / math.sqrt(c * c + p["damp"] * p["damp"])

    @staticmethod
    def view(s, p, cfg=None):
        v = _sound_v(p["Tc"])
        return {"loud": Resonance._loud(p, p["h"]), "h": p["h"], "v": v, "lambda": v / p["f"], "water_y": -p["h"]}

    @staticmethod
    def measure(p, cfg=None):
        peaks, prev2, prev = [], 0.0, 0.0
        i = 0
        while len(peaks) < 2 and i < 20000:
            h = 0.005 + i * 1e-4
            cur = Resonance._loud(p, h)
            if i >= 2 and prev > prev2 and prev >= cur:
                peaks.append(h - 1e-4)
            prev2, prev, i = prev, cur, i + 1
        if len(peaks) < 2:
            return {"l1": 0.0, "l2": 0.0, "v_meas": 0.0}
        return {"l1": peaks[0], "l2": peaks[1], "v_meas": 2 * p["f"] * (peaks[1] - peaks[0])}


class Sonometer:
    PARAMS = {"Tn": 39.2, "mu": 0.001, "f": 256.0, "l": 0.3, "damp": 0.01}
    VARS = ["loud", "fw", "l", "amp"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _fw(p, l):
        return math.sqrt(p["Tn"] / p["mu"]) / (2 * l)

    @staticmethod
    def _loud(p, l):
        x = (Sonometer._fw(p, l) ** 2 - p["f"] ** 2) / (p["f"] ** 2)
        return p["damp"] / math.sqrt(x * x + p["damp"] * p["damp"])

    @staticmethod
    def view(s, p, cfg=None):
        loud = Sonometer._loud(p, p["l"])
        return {"loud": loud, "fw": Sonometer._fw(p, p["l"]), "l": p["l"], "amp": 0.012 * loud * math.sin(40 * s["t"])}

    @staticmethod
    def measure(p, cfg=None):
        best, bl = -1.0, 0.0
        i = 0
        while i <= 95000:
            l = 0.05 + i * 1e-5
            v = Sonometer._loud(p, l)
            if v > best:
                best, bl = v, l
            i += 1
        return {"l_res": bl}


# ------------------------------------------------------------------------------------------------ circuits
def _val(spec: Any, p: dict) -> float:
    """An element value: a number, a param name, or {param, k, c} = c + k * p[param]."""
    if isinstance(spec, (int, float)):
        return float(spec)
    if isinstance(spec, str):
        return float(p[spec])
    return float(spec.get("c", 0.0)) + float(spec.get("k", 1.0)) * float(p[spec["param"]])


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        piv = c
        for r in range(c + 1, n):
            if abs(M[r][c]) > abs(M[piv][c]):
                piv = r
        if abs(M[piv][c]) < 1e-300:
            raise ValueError("circuit is not solvable (a node floats)")
        M[c], M[piv] = M[piv], M[c]
        for r in range(c + 1, n):
            fct = M[r][c] / M[c][c]
            if fct != 0.0:
                for k in range(c, n + 1):
                    M[r][k] -= fct * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        acc = M[r][n]
        for k in range(r + 1, n):
            acc -= M[r][k] * x[k]
        x[r] = acc / M[r][r]
    return x


VT = 0.025852                  # thermal voltage at 300 K


class Circuit:
    """DC + transient Modified Nodal Analysis. cfg.net = {nodes: N, els: [{id, kind R|V|C|D|S, a, b, value...}]}.
    Node 0 is ground. V: a = + terminal. D: anode a. S (switch): closed when its param >= 0.5. C: backward Euler."""
    PARAMS: dict[str, float] = {}

    @staticmethod
    def vars(cfg):
        out = ["t"]
        for e in cfg["net"]["els"]:
            out += ["I_" + e["id"], "V_" + e["id"]]
        return out + ["N_%d" % i for i in range(cfg["net"]["nodes"] + 1)]

    @staticmethod
    def init(p, cfg=None):
        s = {"t": 0.0, "vc": {e["id"]: 0.0 for e in cfg["net"]["els"] if e["kind"] == "C"}, "x": None, "ic": {}}
        Circuit._solve_at(s, p, cfg, 0.0)
        return s

    @staticmethod
    def _solve_at(s, p, cfg, h):
        net = cfg["net"]
        nn = net["nodes"]
        vs = [e for e in net["els"] if e["kind"] == "V"]
        size = nn + len(vs)
        guess = s.get("vd") or {}
        vd = {e["id"]: guess.get(e["id"], 0.6) for e in net["els"] if e["kind"] == "D"}
        x = [0.0] * size
        for _ in range(200):
            A = [[0.0] * size for _ in range(size)]
            b = [0.0] * size

            def g(a, bn, G):
                if a:
                    A[a - 1][a - 1] += G
                if bn:
                    A[bn - 1][bn - 1] += G
                if a and bn:
                    A[a - 1][bn - 1] -= G
                    A[bn - 1][a - 1] -= G

            def inj(a, bn, I):                       # current I flowing from a to bn inside the element
                if a:
                    b[a - 1] -= I
                if bn:
                    b[bn - 1] += I

            for i in range(nn):
                A[i][i] += 1e-12                     # gmin: a floating node never makes the matrix singular
            j = 0
            for e in net["els"]:
                k, a, bn = e["kind"], e["a"], e["b"]
                if k == "R":
                    g(a, bn, 1.0 / max(_val(e["value"], p), 1e-9))
                elif k == "S":
                    g(a, bn, 1e6 if float(p[e["param"]]) >= 0.5 else 1e-12)
                elif k == "C":
                    if h > 0:
                        G = _val(e["value"], p) / h
                        g(a, bn, G)
                        inj(a, bn, -G * s["vc"][e["id"]])
                    else:
                        g(a, bn, 1e-12)
                elif k == "D":
                    Is, nv = _val(e.get("Is", 1e-12), p), _val(e.get("n", 1.8), p) * VT
                    v0 = vd[e["id"]]
                    ex = math.exp(min(v0 / nv, 80.0))
                    Gd = Is / nv * ex + 1e-12
                    Id = Is * (ex - 1)
                    g(a, bn, Gd)
                    inj(a, bn, Id - Gd * v0)
                elif k == "V":
                    r = nn + j
                    if a:
                        A[a - 1][r] += 1.0
                        A[r][a - 1] += 1.0
                    if bn:
                        A[bn - 1][r] -= 1.0
                        A[r][bn - 1] -= 1.0
                    b[r] = _val(e["value"], p)
                    j += 1
            x = _solve(A, b)
            if not vd:
                break
            worst = 0.0
            for e in net["els"]:
                if e["kind"] != "D":
                    continue
                va = x[e["a"] - 1] if e["a"] else 0.0
                vb = x[e["b"] - 1] if e["b"] else 0.0
                new = va - vb
                old = vd[e["id"]]
                step = max(-0.1, min(0.1, new - old))       # voltage limiting keeps Newton stable
                vd[e["id"]] = old + step
                worst = max(worst, abs(new - old))
            if worst < 1e-12:
                break
        s["x"], s["vd"], s["h"] = x, vd, h

    @staticmethod
    def step(s, p, dt, cfg=None):
        if not s["vc"]:
            Circuit._solve_at(s, p, cfg, 0.0)
            s["t"] += dt
            return
        n, h = _sub(dt, 0.0005)
        for _ in range(n):
            Circuit._solve_at(s, p, cfg, h)
            for e in cfg["net"]["els"]:
                if e["kind"] == "C":
                    vnew = Circuit._node(s, e["a"]) - Circuit._node(s, e["b"])
                    s["ic"][e["id"]] = _val(e["value"], p) * (vnew - s["vc"][e["id"]]) / h
                    s["vc"][e["id"]] = vnew
        s["t"] += dt

    @staticmethod
    def _node(s, i):
        return s["x"][i - 1] if i else 0.0

    @staticmethod
    def view(s, p, cfg=None):
        net = cfg["net"]
        if s.get("x") is None:
            Circuit._solve_at(s, p, cfg, 0.0)
        if not s["vc"]:
            Circuit._solve_at(s, p, cfg, 0.0)
        out = {"t": s["t"]}
        nn, j = net["nodes"], 0
        for i in range(nn + 1):
            out["N_%d" % i] = Circuit._node(s, i)
        for e in net["els"]:
            va, vb = Circuit._node(s, e["a"]), Circuit._node(s, e["b"])
            v = va - vb
            k = e["kind"]
            if k == "R":
                cur = v / max(_val(e["value"], p), 1e-9)
            elif k == "S":
                cur = v * (1e6 if float(p[e["param"]]) >= 0.5 else 1e-12)
            elif k == "C":
                cur = s["ic"].get(e["id"], 0.0)
            elif k == "D":
                Is, nv = _val(e.get("Is", 1e-12), p), _val(e.get("n", 1.8), p) * VT
                cur = Is * (math.exp(min(v / nv, 80.0)) - 1)
            else:
                cur = -s["x"][nn + j]                  # MNA source current, flipped to "out of the + terminal"
                j += 1
            out["I_" + e["id"]] = cur
            out["V_" + e["id"]] = v
        return out

    @staticmethod
    def measure(p, cfg=None):
        m = cfg.get("measure") or {"mode": "value"}
        if m["mode"] == "null":                      # jockey position where the galvanometer reads zero
            lo, hi = float(m.get("lo", 0.01)), float(m.get("hi", 0.99))

            def cur(x):
                q = dict(p)
                q[m["param"]] = x
                s = Circuit.init(q, cfg)
                return Circuit.view(s, q, cfg)[m["var"]]
            flo = cur(lo)
            for _ in range(60):
                mid = (lo + hi) / 2
                fm = cur(mid)
                if (fm > 0) == (flo > 0):
                    lo, flo = mid, fm
                else:
                    hi = mid
            return {m["param"]: (lo + hi) / 2}
        if m["mode"] == "time_to":                   # time for var to reach `frac` of `final`
            s = Circuit.init(p, cfg)
            final, frac = float(m["final"]), float(m.get("frac", 0.632))
            prev_t, prev_v = 0.0, Circuit.view(s, p, cfg)[m["var"]]
            while s["t"] < float(m.get("tmax", 60.0)):
                Circuit.step(s, p, 0.001, cfg)
                v = Circuit.view(s, p, cfg)[m["var"]]
                if v >= frac * final:
                    return {"t_" + m["var"]: prev_t + 0.001 * (frac * final - prev_v) / (v - prev_v)}
                prev_t, prev_v = s["t"], v
            return {"t_" + m["var"]: 0.0}
        s = Circuit.init(p, cfg)
        vw = Circuit.view(s, p, cfg)
        out = {k: vw[k] for k in m.get("vars", [])}
        if m["mode"] == "ratio":                     # e.g. R = V (voltmeter) / I (ammeter)
            out[m["as"]] = vw[m["num"]] / vw[m["den"]] if vw[m["den"]] != 0 else 0.0
        return out


# ------------------------------------------------------------------------------------------------ optics (2D, exact)
def _refract(d, nrm, n1, n2):
    """Snell in vector form. d, nrm unit vectors, nrm against d. Returns the new direction or None (total reflection)."""
    cosi = -(d[0] * nrm[0] + d[1] * nrm[1])
    r = n1 / n2
    k = 1 - r * r * (1 - cosi * cosi)
    if k < 0:
        return None
    ct = math.sqrt(k)
    return [r * d[0] + (r * cosi - ct) * nrm[0], r * d[1] + (r * cosi - ct) * nrm[1]]


def _circle_hit(o, d, cx, R, near_left):
    """Ray o + t d against the circle centred (cx, 0); the hit nearest the pole side."""
    ox, oy = o[0] - cx, o[1]
    bq = ox * d[0] + oy * d[1]
    cq = ox * ox + oy * oy - R * R
    disc = bq * bq - cq
    if disc < 0:
        return None
    sq = math.sqrt(disc)
    ts = sorted([-bq - sq, -bq + sq])
    for t in ts:
        if t > 1e-12:
            x = o[0] + t * d[0]
            if (x < cx) == near_left:
                return [x, o[1] + t * d[1]]
    return None


def _norm(v):
    L = math.hypot(v[0], v[1])
    return [v[0] / L, v[1] / L]


def _sharp(scr, img_x):
    """How sharp the image looks on a screen at scr (1 = in focus); a virtual image never forms on a screen."""
    if img_x <= 0:
        return 0.0
    q = (scr - img_x) / 0.004
    return 1 / (1 + q * q)


def _meet(p1, d1, p2, d2):
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-18:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return [p1[0] + t * d1[0], p1[1] + t * d1[1]]


class Mirror:
    """Concave spherical mirror, pole at x = 0 facing +x, centre at (R, 0). Object of height h at x = u."""
    PARAMS = {"R": 0.3, "u": 0.45, "h": 0.03, "convex": 0.0, "scr": 0.3}
    VARS = ["rays", "img_x", "img_h", "real", "f", "sharp"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _trace(p, y_aim):
        R = p["R"]
        cx = R if p["convex"] < 0.5 else -R
        o = [p["u"], p["h"]]
        d = _norm([0.0 - o[0], y_aim - o[1]])
        hit = _circle_hit(o, d, cx, R, near_left=(cx > 0))
        if hit is None:
            return None
        nrm = _norm([hit[0] - cx, hit[1]])
        dot = d[0] * nrm[0] + d[1] * nrm[1]
        r = [d[0] - 2 * dot * nrm[0], d[1] - 2 * dot * nrm[1]]
        return o, hit, r

    @staticmethod
    def _image(p):
        a = Mirror._trace(p, -1e-4)
        b = Mirror._trace(p, 1e-4)
        if not a or not b:
            return None
        return _meet(a[1], a[2], b[1], b[2])

    @staticmethod
    def view(s, p, cfg=None):
        img = Mirror._image(p) or [0.0, 0.0]
        rays = []
        for aim in (p["h"], 0.0, -p["h"] * 0.6):
            tr = Mirror._trace(p, aim)
            if not tr:
                continue
            o, hit, r = tr
            L = 2.0
            rays.append({"p": [o, hit, [hit[0] + L * r[0], hit[1] + L * r[1]]], "v": 0})
            if img[0] < 0:
                rays.append({"p": [hit, img], "v": 1})
        f = p["R"] / 2 * (1 if p["convex"] < 0.5 else -1)
        return {"rays": rays, "img_x": img[0], "img_h": img[1], "real": 1.0 if img[0] > 0 else 0.0, "f": f,
                "sharp": _sharp(p["scr"], img[0])}

    @staticmethod
    def measure(p, cfg=None):
        q = dict(p, h=0.002)
        img = Mirror._image(q) or [0.0, 0.0]
        return {"v": img[0], "m": img[1] / q["h"]}


class Lens:
    """Biconvex glass lens centred at x = 0 (thickness d, surfaces R1 = R2 = R), object of height h at x = -u."""
    PARAMS = {"R": 0.2, "n": 1.5, "d": 0.0025, "u": 0.4, "h": 0.03, "ap": 0.04, "scr": 0.3}
    VARS = ["rays", "img_x", "img_h", "real", "f", "sharp"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _trace(p, y_aim):
        R, n, d = p["R"], p["n"], p["d"]
        o = [-p["u"], p["h"]]
        dr = _norm([-d / 2 - o[0], y_aim - o[1]])
        c1 = -d / 2 + R                                # first surface: centre right of it
        h1 = _circle_hit(o, dr, c1, R, near_left=True)
        if h1 is None:
            return None
        d1 = _refract(dr, _norm([h1[0] - c1, h1[1]]), 1.0, n)
        if d1 is None:
            return None
        c2 = d / 2 - R                                 # second surface: centre left of it
        h2 = _circle_hit(h1, d1, c2, R, near_left=False)
        if h2 is None:
            return None
        n2 = _norm([h2[0] - c2, h2[1]])
        d2 = _refract(d1, [-n2[0], -n2[1]], n, 1.0)
        if d2 is None:
            return None
        return o, h1, h2, d2

    @staticmethod
    def _image(p):
        a = Lens._trace(p, -1e-4)
        b = Lens._trace(p, 1e-4)
        if not a or not b:
            return None
        return _meet(a[2], a[3], b[2], b[3])

    @staticmethod
    def view(s, p, cfg=None):
        img = Lens._image(p) or [0.0, 0.0]
        rays = []
        edge = math.sqrt(max(p["R"] * p["d"] - p["d"] * p["d"] / 4, 0.0)) * 0.8     # inside the lens rim
        for aim in (edge, 0.0, -edge):
            tr = Lens._trace(p, aim)
            if not tr:
                continue
            o, h1, h2, d2 = tr
            rays.append({"p": [o, h1, h2, [h2[0] + 2.0 * d2[0], h2[1] + 2.0 * d2[1]]], "v": 0})
            if img[0] < 0:
                rays.append({"p": [h2, img], "v": 1})
        f = 1 / ((p["n"] - 1) * (2 / p["R"]))
        return {"rays": rays, "img_x": img[0], "img_h": img[1], "real": 1.0 if img[0] > 0 else 0.0, "f": f,
                "sharp": _sharp(p["scr"], img[0])}

    @staticmethod
    def measure(p, cfg=None):
        q = dict(p, h=0.002)
        img = Lens._image(q) or [0.0, 0.0]
        return {"v": img[0], "m": img[1] / q["h"]}


class Prism:
    """Triangular glass prism, apex angle A, ray incident at angle i on the first face."""
    PARAMS = {"A": 1.0472, "n": 1.5, "i": 0.8, "side": 0.12}
    VARS = ["rays", "dev", "e", "tir"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _angles(p, i):
        r1 = math.asin(math.sin(i) / p["n"])
        r2 = p["A"] - r1
        x = p["n"] * math.sin(r2)
        if abs(x) > 1:
            return None
        e = math.asin(x)
        return r1, r2, e, i + e - p["A"]

    @staticmethod
    def view(s, p, cfg=None):
        A, S = p["A"], p["side"]
        apex = [0.0, S * math.cos(A / 2)]
        bl = [-S * math.sin(A / 2), 0.0]
        br = [S * math.sin(A / 2), 0.0]
        ang = Prism._angles(p, p["i"])
        rays = []
        hit1 = [(apex[0] + bl[0]) / 2, (apex[1] + bl[1]) / 2]
        n1 = _norm([-math.cos(A / 2), math.sin(A / 2)])          # outward normal of the left face
        din = [math.cos(math.atan2(-n1[1], -n1[0]) + p["i"]), math.sin(math.atan2(-n1[1], -n1[0]) + p["i"])]
        start = [hit1[0] - 0.12 * din[0], hit1[1] - 0.12 * din[1]]
        if ang is None:
            return {"rays": [{"p": [start, hit1], "v": 0}], "dev": 0.0, "e": 0.0, "tir": 1.0}
        d1 = _refract(din, n1, 1.0, p["n"])
        # second face: from apex to br
        e2 = [br[0] - apex[0], br[1] - apex[1]]
        hit2 = _meet(hit1, d1, apex, e2) or hit1
        n2 = _norm([math.cos(A / 2), math.sin(A / 2)])
        d2 = _refract(d1, [-n2[0], -n2[1]], p["n"], 1.0) or d1
        end = [hit2[0] + 0.16 * d2[0], hit2[1] + 0.16 * d2[1]]
        rays.append({"p": [start, hit1, hit2, end], "v": 0})
        rays.append({"p": [hit1, [hit1[0] + 0.2 * din[0], hit1[1] + 0.2 * din[1]]], "v": 1})
        return {"rays": rays, "dev": ang[3], "e": ang[2], "tir": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        best, bi = 10.0, 0.0
        k = 0
        while k <= 6000:
            i = math.radians(25 + k * 0.01)
            a = Prism._angles(p, i)
            if a is not None and a[3] < best:
                best, bi = a[3], i
            k += 1
        return {"dm": best, "i_min": bi}


class Slab:
    """A mark under a glass slab of thickness t, seen from above: it looks raised (apparent depth)."""
    PARAMS = {"t": 0.05, "n": 1.5}
    VARS = ["rays", "app", "shift"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def _apparent(p, ang):
        o = [0.0, -p["t"]]
        d = [math.sin(ang), math.cos(ang)]
        hit = [o[0] + p["t"] * math.tan(ang), 0.0]
        out = _refract(d, [0.0, -1.0], p["n"], 1.0)
        # extend the emerging ray back to the axis x = 0
        if out is None or abs(out[0]) < 1e-18:
            return None, hit, out
        k = -hit[0] / out[0]
        return hit[1] + k * out[1], hit, out

    @staticmethod
    def view(s, p, cfg=None):
        rays = []
        app = 0.0
        for ang in (0.25, -0.25):
            y, hit, out = Slab._apparent(p, ang)
            if out is None:
                continue
            rays.append({"p": [[0.0, -p["t"]], hit, [hit[0] + 0.15 * out[0], hit[1] + 0.15 * out[1]]], "v": 0})
            rays.append({"p": [hit, [0.0, y]], "v": 1})
        y0, _, _ = Slab._apparent(p, 0.001)
        app = -(y0 or 0.0)
        return {"rays": rays, "app": app, "shift": p["t"] - app}

    @staticmethod
    def measure(p, cfg=None):
        y, _, _ = Slab._apparent(p, 0.001)
        return {"app": -(y or 0.0)}


# ------------------------------------------------------------------------------------------------ EM induction
class Induction:
    """A bar magnet (dipole m) moving at speed v along the axis of an N-turn coil of radius a: emf = -N dPhi/dt.
    It starts |z0| on the side it comes from and runs through the coil; past the far end it starts again."""
    PARAMS = {"N": 200.0, "a": 0.02, "m": 1.0, "v": 0.5, "z0": -0.15}
    VARS = ["t", "z", "emf", "flux"]

    @staticmethod
    def _start(p):
        return -abs(p["z0"]) if p["v"] >= 0 else abs(p["z0"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "z": Induction._start(p)}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["z"] += p["v"] * dt
        if abs(s["z"]) > abs(p["z0"]):
            s["z"] = Induction._start(p)
        s["t"] += dt

    @staticmethod
    def _emf(p, z):
        a2 = p["a"] * p["a"]
        return p["N"] * 3 * MU0 * p["m"] * a2 * z * p["v"] / (2 * (a2 + z * z) ** 2.5)

    @staticmethod
    def view(s, p, cfg=None):
        a2 = p["a"] * p["a"]
        z = s["z"]
        return {"t": s["t"], "z": z, "emf": Induction._emf(p, z), "flux": p["N"] * MU0 * p["m"] * a2 / (2 * (a2 + z * z) ** 1.5)}

    @staticmethod
    def measure(p, cfg=None):
        if abs(p["v"]) < 1e-9:
            return {"emf_peak": 0.0}
        s, best = Induction.init(p), 0.0
        dt = 1e-5 / abs(p["v"])
        n = int(abs(p["z0"]) / 1e-5) + 2
        for _ in range(n):
            Induction.step(s, p, dt)
            best = max(best, abs(Induction._emf(p, s["z"])))
        return {"emf_peak": best}


# ------------------------------------------------------------------------------------------------ measuring instruments
class Gauge:
    """Vernier callipers (kind 0) or screw gauge (kind 1) closed on an object of true size L (with zero error ze)."""
    PARAMS = {"kind": 0.0, "L": 0.02345, "ze": 0.0, "msd": 0.001, "nv": 10.0, "pitch": 0.0005, "ndiv": 50.0}
    VARS = ["jaw", "lc", "main", "div", "reading"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        raw = p["L"] + p["ze"]
        if p["kind"] < 0.5:
            lc = p["msd"] / p["nv"]
            unit = p["msd"]
            div_n = p["nv"]
        else:
            lc = p["pitch"] / p["ndiv"]
            unit = p["pitch"]
            div_n = p["ndiv"]
        main = math.floor(raw / unit + 1e-9) * unit
        div = math.floor((raw - main) / lc + 0.5)
        if div >= div_n:
            main, div = main + unit, 0
        return {"jaw": raw, "lc": lc, "main": main, "div": float(div), "reading": main + div * lc - p["ze"]}

    @staticmethod
    def measure(p, cfg=None):
        return {"reading": Gauge.view({}, p)["reading"]}


KERNELS: dict[str, Any] = {
    "pendulum": Pendulum, "spring": Spring, "incline": Incline, "stokes": Stokes, "cooling": Cooling, "boyle": Boyle,
    "mixtures": Mixtures, "resonance": Resonance, "sonometer": Sonometer, "circuit": Circuit, "mirror": Mirror,
    "lens": Lens, "prism": Prism, "slab": Slab, "induction": Induction, "gauge": Gauge,
}
FAMILY = {"pendulum": "mech", "spring": "osc_wave", "incline": "mech", "stokes": "mech", "cooling": "thermo",
          "boyle": "thermo", "mixtures": "thermo", "resonance": "osc_wave", "sonometer": "osc_wave", "circuit": "circuit",
          "mirror": "optics", "lens": "optics", "prism": "optics", "slab": "optics", "induction": "em", "gauge": "mech"}



# --------------------------------------------------------------------------------------------- kernel packs
def _load_packs() -> list[str]:
    """Merge every `app/prayog/packs/<name>.py` into KERNELS / FAMILY / TEXTBOOK / CALCS. A broken pack is
    logged and skipped, never fatal: one bad pack must not take the whole lab down."""
    import importlib
    import logging
    import pkgutil

    from . import packs as _packs

    log = logging.getLogger("santosh.prayog")
    loaded = []
    for mod in sorted(m.name for m in pkgutil.iter_modules(_packs.__path__)):
        try:
            m = importlib.import_module(f"{_packs.__name__}.{mod}")
            for name, K in (getattr(m, "KERNELS", {}) or {}).items():
                if name in KERNELS:
                    raise ValueError(f"kernel '{name}' is already taken")
                KERNELS[name] = K
            FAMILY.update(getattr(m, "FAMILY", {}) or {})
            TEXTBOOK.update(getattr(m, "TEXTBOOK", {}) or {})
            CALCS.update(getattr(m, "CALCS", {}) or {})
            loaded.append(mod)
        except Exception as e:                       # noqa: BLE001 - one bad pack is skipped, not fatal
            log.warning("prayog kernel pack %s left out: %s", mod, e)
    return loaded



def kernel_vars(name: str, cfg: dict | None) -> list[str]:
    K = KERNELS[name]
    return K.vars(cfg or {}) if hasattr(K, "vars") else list(K.VARS)


def params_for(name: str, over: dict | None) -> dict:
    p = dict(KERNELS[name].PARAMS)
    p.update({k: float(v) for k, v in (over or {}).items()})
    return p


# ------------------------------------------------------------------------------------------------ NCERT formulas
def _diode_v(p):
    """Independent check of the circuit solver: E = I Rs + n Vt ln(I / Is + 1), solved by bisection on I."""
    Is, n = p.get("Is", 1e-12), p.get("nD", 1.8)
    lo, hi = 0.0, p["Eb"] / p["Rs"]
    for _ in range(200):
        mid = (lo + hi) / 2
        if mid * p["Rs"] + n * VT * math.log(mid / Is + 1) > p["Eb"]:
            hi = mid
        else:
            lo = mid
    return n * VT * math.log(lo / Is + 1)


def _thin(u, f):
    return u * f / (u - f)


TEXTBOOK: dict[str, Callable[[dict], float]] = {
    "pendulum_T": lambda p: 2 * PI * math.sqrt(p["L"] / p["g"]),
    "spring_T": lambda p: 2 * PI * math.sqrt(p["m"] / p["k"]),
    "spring_ext": lambda p: p["m"] * p["g"] / p["k"],
    "incline_Fmin": lambda p: p["m"] * p["g"] * (math.sin(p["angle"]) + p["mu"] * math.cos(p["angle"])),
    "incline_a": lambda p: (p["F"] - p["m"] * p["g"] * (math.sin(p["angle"]) + p["mu"] * math.cos(p["angle"]))) / p["m"],
    "stokes_v": lambda p: 2 * p["r"] ** 2 * (p["rho"] - p["sigma"]) * p["g"] / (9 * p["eta"]),
    "cooling_T60": lambda p: p["Ts"] + (p["T0"] - p["Ts"]) * math.exp(-60 * p["k"]),
    "boyle_P": lambda p: p["n"] * p["R"] * p["Temp"] / p["V"],
    "mix_Tf": lambda p: ((p["m1"] * p["c1"] * p["T1"] + (p["m2"] * p["c2"] + p["mc"] * p["cc"]) * p["T2"])
                         / (p["m1"] * p["c1"] + p["m2"] * p["c2"] + p["mc"] * p["cc"])),
    "sound_v": lambda p: _sound_v(p["Tc"]),
    "sono_l": lambda p: math.sqrt(p["Tn"] / p["mu"]) / (2 * p["f"]),
    "ohm_R": lambda p: p["Rx"],
    "bridge_l": lambda p: p["Rk"] / (p["Rk"] + p["Sx"]),
    "pot_r": lambda p: p["r_int"],
    "diode_V": lambda p: _diode_v(p),
    "rc_tau": lambda p: p["Rr"] * p["Cc"],
    "mirror_v": lambda p: _thin(p["u"], p["R"] / 2),
    "lens_v": lambda p: _thin(p["u"], 1 / ((p["n"] - 1) * (2 / p["R"]))),
    "prism_n": lambda p: p["n"],
    "prism_dm": lambda p: 2 * math.asin(p["n"] * math.sin(p["A"] / 2)) - p["A"],
    "slab_app": lambda p: p["t"] / p["n"],
    "induct_peak": lambda p: (p["N"] * 3 * MU0 * p["m"] * p["a"] ** 2 * (p["a"] / 2) * abs(p["v"])
                              / (2 * (p["a"] ** 2 + p["a"] ** 2 / 4) ** 2.5)),
    "gauge_L": lambda p: p["L"],
}


# ------------------------------------------------------------------------------------------------ result from a table
def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _rows(rows, *keys):
    out = []
    for r in rows or []:
        try:
            vals = [float(r[k]) for k in keys]
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(v) for v in vals):
            out.append(vals)
    return out


def _pot_r(rows, p):
    """Balance length with the shunt key open (l1) and closed (l2): r = Rb (l1 - l2) / l2."""
    rs = _rows(rows, "k2", "l")
    l1 = _mean([l for k, l in rs if k < 0.5])
    l2 = _mean([l for k, l in rs if k >= 0.5])
    return p["Rb"] * (l1 - l2) / l2 if l1 > 0 and l2 > 0 else 0.0


def _res_v(rows, p):
    """First and second resonance lengths (lowest and highest recorded): v = 2 f (l2 - l1)."""
    hs = sorted(h for (h,) in _rows(rows, "h"))
    return 2 * p["f"] * (hs[-1] - hs[0]) if len(hs) >= 2 else 0.0


CALCS: dict[str, dict] = {
    "pendulum_g": {"label": "g", "unit": "m/s²", "needs": ["L", "T"],
                   "fn": lambda rows, p: _mean([4 * PI * PI * L / (T * T) for L, T in _rows(rows, "L", "T") if T > 0])},
    "spring_k_static": {"label": "k", "unit": "N/m", "needs": ["m", "ext"],
                        "fn": lambda rows, p: _mean([m * p["g"] / e for m, e in _rows(rows, "m", "ext") if e > 0])},
    "spring_k_shm": {"label": "k", "unit": "N/m", "needs": ["m", "T"],
                     "fn": lambda rows, p: _mean([4 * PI * PI * m / (T * T) for m, T in _rows(rows, "m", "T") if T > 0])},
    "incline_mu": {"label": "μ", "unit": "", "needs": ["angle", "F"],
                   "fn": lambda rows, p: _mean([(F - p["m"] * p["g"] * math.sin(a)) / (p["m"] * p["g"] * math.cos(a))
                                                for a, F in _rows(rows, "angle", "F")])},
    "stokes_eta": {"label": "η", "unit": "Pa·s", "needs": ["r", "v"],
                   "fn": lambda rows, p: _mean([2 * r * r * (p["rho"] - p["sigma"]) * p["g"] / (9 * v)
                                                for r, v in _rows(rows, "r", "v") if v > 0])},
    "cooling_k": {"label": "k", "unit": "1/s", "needs": ["t", "T"],
                  "fn": lambda rows, p: _mean([-math.log((T - p["Ts"]) / (p["T0"] - p["Ts"])) / t
                                               for t, T in _rows(rows, "t", "T") if t > 0 and T > p["Ts"]])},
    "boyle_pv": {"label": "PV", "unit": "J", "needs": ["P", "V"],
                 "fn": lambda rows, p: _mean([P * V for P, V in _rows(rows, "P", "V")])},
    "mix_c": {"label": "c (solid)", "unit": "J/(kg·K)", "needs": ["Tf"],
              "fn": lambda rows, p: _mean([(p["m2"] * p["c2"] + p["mc"] * p["cc"]) * (Tf - p["T2"]) / (p["m1"] * (p["T1"] - Tf))
                                           for (Tf,) in _rows(rows, "Tf") if p["T1"] != Tf])},
    "res_v": {"label": "v (sound)", "unit": "m/s", "needs": ["h"], "fn": _res_v},
    "sono_mu": {"label": "μ (wire)", "unit": "kg/m", "needs": ["f", "l", "Tn"],
                "fn": lambda rows, p: _mean([T / (4 * l * l * f * f) for f, l, T in _rows(rows, "f", "l", "Tn") if l > 0 and f > 0])},
    "ohm_R": {"label": "R", "unit": "Ω", "needs": ["V", "I"],
              "fn": lambda rows, p: _mean([V / I for V, I in _rows(rows, "V", "I") if I != 0])},
    "bridge_S": {"label": "S", "unit": "Ω", "needs": ["R", "l"],
                 "fn": lambda rows, p: _mean([R * (1 - l) / l for R, l in _rows(rows, "R", "l") if 0 < l < 1])},
    "pot_r": {"label": "r (cell)", "unit": "Ω", "needs": ["k2", "l"], "fn": _pot_r},
    "diode_knee": {"label": "knee voltage", "unit": "V", "needs": ["V", "I"],
                   "fn": lambda rows, p: min([V for V, I in _rows(rows, "V", "I") if I >= 0.001] or [0.0])},
    "rc_tau": {"label": "τ", "unit": "s", "needs": ["tau"],
               "fn": lambda rows, p: _mean([t for (t,) in _rows(rows, "tau")])},
    "mirror_f": {"label": "f", "unit": "m", "needs": ["u", "v"],
                 "fn": lambda rows, p: _mean([u * v / (u + v) for u, v in _rows(rows, "u", "v") if u + v != 0])},
    "lens_f": {"label": "f", "unit": "m", "needs": ["u", "v"],
               "fn": lambda rows, p: _mean([u * v / (u + v) for u, v in _rows(rows, "u", "v") if u + v != 0])},
    "prism_n": {"label": "n", "unit": "", "needs": ["i", "d"],
                "fn": lambda rows, p: (math.sin((p["A"] + min(d for _, d in _rows(rows, "i", "d"))) / 2) / math.sin(p["A"] / 2))
                if _rows(rows, "i", "d") else 0.0},
    "slab_n": {"label": "n", "unit": "", "needs": ["t", "a"],
               "fn": lambda rows, p: _mean([t / a for t, a in _rows(rows, "t", "a") if a > 0])},
    "induct_ratio": {"label": "emf / v", "unit": "V·s/m", "needs": ["v", "emf"],
                     "fn": lambda rows, p: _mean([e / v for v, e in _rows(rows, "v", "emf") if v != 0])},
    "gauge_mean": {"label": "mean size", "unit": "m", "needs": ["reading"],
                   "fn": lambda rows, p: _mean([r for (r,) in _rows(rows, "reading")])},
}


def calc(name: str, rows: list[dict], p: dict) -> float:
    return float(CALCS[name]["fn"](rows, p))


PACKS = _load_packs()          # last: every pack merges into the tables above
