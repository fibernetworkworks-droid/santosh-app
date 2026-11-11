"""Prayogshala kernel pack: the school set-ups of wave 7 (Class 6-10 activities and Class 11-12 Section A / B
practicals and activities that were still unbuilt).

Every kernel has an EXACT JavaScript twin in `app/static/prayog/packs/school_w7.js` (same formulas, same loops,
same numbers). Deterministic: no randomness, no wall clock. Most set-ups here are steady readings, so a kernel is a
pure function of its params (and of the time `t` where something cools or swings); `measure` gives the reading the
lab's check compares with the textbook formula.

    motion      sw7_rollout, sw7_pull, sw7_trolley, sw7_roller, sw7_dincline, sw7_proj, sw7_fall, sw7_crater, sw7_stairs,
                sw7_pend_decay
    measuring   sw7_jet, sw7_cuboid, sw7_upthrust, sw7_density, sw7_balance, sw7_vessel, sw7_sheet, sw7_pscale, sw7_lenscomb
    heat/sound  sw7_solidsound, sw7_echo, sw7_tins, sw7_waxcool, sw7_bimetal, sw7_level, sw7_loss
    electric    sw7_plating, sw7_liquid, sw7_swing, sw7_dmm, sw7_dtest
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi


def _rt(v: float, lc: float) -> float:
    """A reading on an instrument of least count `lc` (both twins round identically)."""
    if lc <= 0:
        return v
    return math.floor(v / lc + 0.5) * lc


def _ix(p, key: str, n: int) -> int:
    i = int(math.floor(p[key] + 0.5))
    return 0 if i < 0 else (n - 1 if i > n - 1 else i)


def _k(params: dict, fn, meas=None):
    """A kernel from a pure function fn(p, t) -> readings."""
    class _K:
        PARAMS = dict(params)
        VARS = ["t"] + sorted(k for k in fn(dict(params), 0.0).keys() if k != "t")

        @staticmethod
        def init(p, cfg=None):
            return {"t": 0.0}

        @staticmethod
        def step(s, p, dt, cfg=None):
            s["t"] += dt

        @staticmethod
        def view(s, p, cfg=None):
            d = fn(p, s.get("t", 0.0))
            d["t"] = s.get("t", 0.0)
            return d

        @staticmethod
        def measure(p, cfg=None):
            return meas(p) if meas else fn(p, 0.0)
    return _K


# =================================================================================================== MOTION
def _rollout(p, t):
    c = p["c%d" % _ix(p, "surf", 4)]
    return {"c": c, "d": p["h"] / c, "v0": math.sqrt(10 * p["g"] * p["h"] / 7)}


def _rollout_m(p):
    """Roll the ball out step by step: it leaves the ramp at v0 and is slowed at a = 5 c g / 7 until it stops."""
    c = p["c%d" % _ix(p, "surf", 4)]
    v = math.sqrt(10 * p["g"] * p["h"] / 7)
    a = 5 * c * p["g"] / 7
    x, dt = 0.0, 0.0005
    for _ in range(400000):
        if v - a * dt <= 0:
            x += v * v / (2 * a)
            break
        x += v * dt - 0.5 * a * dt * dt
        v -= a * dt
    return {"d": x, "c_meas": p["h"] / x}


def _pull(p, t):
    mu = p["mu_s"] if p["mode"] < 0.5 else p["mu_r"]
    W = p["m"] * p["g"]
    return {"F": mu * W, "W": W, "mu": mu}


def _trolley(p, t):
    v = math.sqrt(2 * p["g"] * p["h"])
    u = p["M"] * v / (p["M"] + p["mb"])
    s = (p["M"] + p["mb"]) * u * u / (2 * p["mu"] * p["mb"] * p["g"])
    return {"v": v, "s": s, "KE": 0.5 * p["M"] * v * v}


def _roller(p, t):
    sn = math.sin(p["ang"] * PI / 180)
    return {"F": p["m"] * p["g"] * sn, "sin": sn}


def _roller_m(p):
    """Slope of the F against sin(theta) graph through the origin, over four angles."""
    sxy = sxx = 0.0
    for a in (20.0, 30.0, 40.0, 50.0):
        q = dict(p)
        q["ang"] = a
        r = _roller(q, 0.0)
        sxy += r["F"] * r["sin"]
        sxx += r["sin"] * r["sin"]
    return {"W": sxy / sxx, "F": _roller(p, 0.0)["F"]}


def _dincline(p, t):
    t1 = math.tan(p["a1"] * PI / 180)
    t2 = math.tan(p["a2"] * PI / 180)
    h2 = p["h1"] * (1 - p["c"] / t1) / (1 + p["c"] / t2)
    return {"h2": h2, "ratio": h2 / p["h1"]}


def _proj(p, t):
    a = p["ang"] * PI / 180
    return {"R": p["v0"] * p["v0"] * math.sin(2 * a) / p["g"], "Hmax": (p["v0"] * math.sin(a)) ** 2 / (2 * p["g"]),
            "tf": 2 * p["v0"] * math.sin(a) / p["g"]}


def _proj_m(p):
    best, ang = -1.0, 0.0
    for i in range(1, 90):
        q = dict(p)
        q["ang"] = float(i)
        R = _proj(q, 0.0)["R"]
        if R > best + 1e-12:
            best, ang = R, float(i)
    return {"ang_max": ang, "R_max": best, "R": _proj(p, 0.0)["R"]}


def _fall(p, t):
    b = _ix(p, "body", 3)
    if b == 0:
        tf, vt = math.sqrt(2 * p["h"] / p["g"]), 0.0
    else:
        A, Cd = (p["A_flat"], p["Cd_flat"]) if b == 1 else (p["A_ball"], p["Cd_ball"])
        vt = math.sqrt(2 * p["m_p"] * p["g"] / (p["rho_air"] * Cd * A))
        tf = vt / p["g"] * math.acosh(math.exp(p["g"] * p["h"] / (vt * vt)))
    return {"tf": tf, "vt": vt, "g_meas": 2 * p["h"] / (tf * tf)}


def _crater(p, t):
    W = p["m"] * p["g"]
    d = W * p["h"] / (p["F"] - W)
    return {"d": d, "PE": W * p["h"], "F_meas": W * (p["h"] + d) / d}


def _stairs(p, t):
    H = p["n"] * p["hs"]
    work = p["m"] * p["g"] * H
    tc = work / p["P"]
    return {"H": H, "tclimb": tc, "work": work, "P_meas": work / tc}


def pend_amp_after(p, n):
    """Swing a damped pendulum (theta'' = -(g/L) sin theta - b theta') for n full swings; the angle it then reaches
    on its starting side, and the time taken. RK4, 2 ms steps (the same loop in the JavaScript twin)."""
    gl, b, h = p["g"] / p["L"], p["b"], 0.002
    th, om, t, count, amp, tn = p["th0"], 0.0, 0.0, 0, p["th0"], 0.0

    def f(a, w):
        return w, -gl * math.sin(a) - b * w
    for _ in range(4000000):
        if count >= n:
            break
        k1 = f(th, om)
        k2 = f(th + 0.5 * h * k1[0], om + 0.5 * h * k1[1])
        k3 = f(th + 0.5 * h * k2[0], om + 0.5 * h * k2[1])
        k4 = f(th + h * k3[0], om + h * k3[1])
        th2 = th + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        om2 = om + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        t += h
        if om > 0 and om2 <= 0 and th2 > 0:            # the turning point on the starting side: one full swing done
            count += 1
            amp, tn = th2, t
        th, om = th2, om2
    return [amp, tn]


def _pend(p, t):
    w = math.sqrt(max(1e-9, p["g"] / p["L"] - p["b"] * p["b"] / 4))
    env = p["th0"] * math.exp(-p["b"] * t / 2)
    return {"theta": env * math.cos(w * t), "env": env}


def _pend_m(p):
    A, tn = pend_amp_after(p, int(math.floor(p["nsw"] + 0.5)))
    return {"A_n": A, "t_n": tn, "gamma": math.log(p["th0"] / A) / tn}


# =================================================================================================== MEASURING
def _jet(p, t):
    y = p["y%d" % _ix(p, "hole", 3)]
    v = math.sqrt(2 * p["g"] * (p["H"] - y))
    tf = math.sqrt(2 * (y + p["S"]) / p["g"])
    return {"x": v * tf, "v": v, "y": y, "P": p["rho"] * p["g"] * (p["H"] - y), "v_meas": v * tf / tf}


def _cuboid(p, t):
    f = _ix(p, "face", 3)
    l1, l2 = ((p["a"], p["b"]), (p["a"], p["c"]), (p["b"], p["c"]))[f]
    W = p["rho"] * p["a"] * p["b"] * p["c"] * p["g"]
    A = l1 * l2
    return {"W": W, "A": A, "P": W / A, "depth": p["ksand"] * W / A, "l1": l1, "l2": l2}


def _upthrust(p, t):
    U = p["rho"] * p["g"] * p["V"] * p["frac"]
    Wt = p["mb"] * p["g"]
    F = U - Wt if U > Wt else 0.0
    return {"U": U, "F": F, "Wt": Wt, "Vd": p["V"] * p["frac"], "U_meas": F + Wt}


def _density(p, t):
    b = _ix(p, "body", 2)
    m, rho = p["m%d" % b], p["rho%d" % b]
    V = _rt(m / rho, p["lcV"])
    return {"m": m, "V": V, "rho_meas": m / V, "floats": 1.0 if rho < p["rho_w"] else 0.0,
            "sub": rho / p["rho_w"] if rho < p["rho_w"] else 1.0}


WEIGHTS = (0.1, 0.05, 0.02, 0.02, 0.01, 0.005, 0.002, 0.002, 0.001, 0.0005, 0.0002, 0.0002, 0.0001, 0.00005,
           0.00002, 0.00002, 0.00001)


def _balance(p, t):
    diff = p["m%d" % _ix(p, "body", 2)] - p["w"]
    div = diff * 2000.0
    return {"diff": diff, "div": 10.0 if div > 10 else (-10.0 if div < -10 else div)}


def _balance_m(p):
    """Weigh as the manual says: try each weight from the box, largest first; keep it if the body is still heavier."""
    m, tot = p["m%d" % _ix(p, "body", 2)], 0.0
    for w in WEIGHTS:
        if tot + w <= m + 1e-9:
            tot += w
    return {"m_read": tot}


def _vessel(p, t):
    v = _ix(p, "vessel", 2)
    D, dep = _rt(p["D%d" % v], p["lc"]), _rt(p["h%d" % v], p["lc"])
    return {"D": D, "dep": dep, "V": PI * D * D * dep / 4}


def _sheet(p, t):
    if _ix(p, "body", 2) == 0:
        return {"th": _rt(p["t0"], p["lc"]), "A": 0.0, "V": 0.0}
    th, A = _rt(p["t1"], p["lc"]), _rt(p["A1"], p["lcA"])
    return {"th": th, "A": A, "V": A * th}


def _pscale(p, t):
    return {"reading": _rt(p["L"], p["lc"])}


def _lenscomb(p, t):
    F = p["f1"] * p["f2"] / (p["f1"] + p["f2"])
    v = p["u"] * F / (p["u"] - F)
    return {"F": F, "v": v, "F_meas": p["u"] * v / (p["u"] + v)}


# =================================================================================================== HEAT AND SOUND
def _solidsound(p, t):
    m = _ix(p, "medium", 3)
    v = 331.3 * math.sqrt(1 + p["Tc"] / 273.15) if m == 2 else math.sqrt(p["Y%d" % m] / p["rho%d" % m])
    dist = p["d%d" % m]
    dt = _rt(dist / v, 1e-6)
    return {"v": v, "dist": dist, "dt": dt, "v_meas": dist / dt}


def _echo(p, t):
    x = (p["r_deg"] - p["i_deg"]) / p["w"]
    return {"loud": math.exp(-x * x)}


def _echo_m(p):
    best, r = -1.0, 0.0
    for i in range(10, 81):
        q = dict(p)
        q["r_deg"] = float(i)
        L = _echo(q, 0.0)["loud"]
        if L > best + 1e-12:
            best, r = L, float(i)
    return {"r_peak": r, "loud": _echo(p, 0.0)["loud"]}


def _tins(p, t):
    a = p["a%d" % _ix(p, "tin", 2)]
    dT = a * p["G"] * p["A"] / p["hA"] * (1 - math.exp(-p["tm"] * p["hA"] / p["C"]))
    T = _rt(p["Ta"] + dT, 0.1)
    return {"T": T, "rise": T - p["Ta"]}


def _tins_m(p):
    q0, q1 = dict(p), dict(p)
    q0["tin"], q1["tin"] = 0.0, 1.0
    r0, r1 = _tins(q0, 0.0), _tins(q1, 0.0)
    return {"ratio": r0["rise"] / r1["rise"], "T": _tins(p, 0.0)["T"]}


def _wax_T(p, t):
    k = p["hA"] / (p["m"] * p["c"])
    t1 = math.log((p["T0"] - p["Ts"]) / (p["Tm"] - p["Ts"])) / k
    tp = p["Lf"] * p["m"] / (p["hA"] * (p["Tm"] - p["Ts"]))
    if t <= t1:
        return p["Ts"] + (p["T0"] - p["Ts"]) * math.exp(-k * t)
    if t <= t1 + tp:
        return p["Tm"]
    return p["Ts"] + (p["Tm"] - p["Ts"]) * math.exp(-k * (t - t1 - tp))


def _waxcool(p, t):
    T = _wax_T(p, t)
    return {"T": T, "reading": _rt(T, p["lc"])}


def _waxcool_m(p):
    """Read the thermometer every 30 s; the melting point is the first reading that holds for four readings."""
    got, run, last = p["T0"], 0, -1e9
    for i in range(0, 121):
        r = _rt(_wax_T(p, 30.0 * i), p["lc"])
        run = run + 1 if abs(r - last) < 1e-9 else 1
        last = r
        if run >= 4:
            got = r
            break
    return {"Tm_meas": got, "reading": _rt(p["T0"], p["lc"])}


def _bimetal(p, t):
    dT = p["T"] - p["T0"]
    kap = 1.5 * (p["a1"] - p["a2"]) * dT / p["ts"]
    defl = (1 - math.cos(kap * p["Ls"])) / kap if abs(kap) > 1e-9 else 0.0
    return {"kap": kap, "defl": defl, "da_meas": 4 * defl * p["ts"] / (3 * p["Ls"] * p["Ls"] * dT) if dT != 0 else 0.0}


def _level(p, t):
    dT = p["T"] - p["T0"]
    dh = p["V0"] * (p["gam"] - p["gg"]) * dT / p["a"]
    return {"dh": dh, "gapp_meas": p["a"] * dh / (p["V0"] * dT) if dT != 0 else 0.0}


def _loss(p, t):
    k = p["h"] * p["A"] * p["f"] / (p["m"] * p["c"])
    lg = math.log((p["T0"] - p["Ts"]) / (p["T0"] - p["drop"] - p["Ts"]))
    td = _rt(lg / k, 1.0)
    return {"k": k, "tdrop": td, "k_meas": lg / td, "T": p["Ts"] + (p["T0"] - p["Ts"]) * math.exp(-k * t)}


# =================================================================================================== ELECTRIC
def _plating(p, t):
    Z = p["M"] / (p["n"] * p["F"])
    dm = _rt(Z * p["I"] * p["tm"], p["lc"])
    return {"dm": dm, "Q": p["I"] * p["tm"], "Z_meas": dm / (p["I"] * p["tm"])}


def _liquid(p, t):
    s = p["s%d" % _ix(p, "liq", 5)]
    Rl = p["cellk"] / s
    I = (p["V"] - p["Vf"]) / (p["Rs"] + Rl)
    return {"I": I, "Rl": Rl, "glow": 1.0 if I > 2e-4 else 0.0, "s_meas": p["cellk"] / ((p["V"] - p["Vf"]) / I - p["Rs"])}


def _swing(p, t):
    F = p["B"] * p["I"] * p["Lr"]
    a = math.atan(F / (p["m"] * p["g"]))
    sg = (1.0 if p["sI"] >= 0 else -1.0) * (1.0 if p["sB"] >= 0 else -1.0)
    return {"ang": sg * a * 180 / PI, "F": F, "B_meas": p["m"] * p["g"] * math.tan(a) / (p["I"] * p["Lr"])}


def _dmm(p, t):
    m = _ix(p, "mode", 5)
    if m == 0:
        r = _rt(p["R"], 10.0)
    elif m == 1:
        r = _rt(p["E"], 0.01)
    elif m == 2:
        r = _rt(p["Vac"], 0.1)
    elif m == 3:
        r = _rt(p["E"] / p["R"], 1e-5)
    else:
        r = _rt(p["Rc"], 0.1)
    return {"reading": r, "beep": 1.0 if (m == 4 and p["Rc"] < 30) else 0.0}


def _dtest(p, t):
    d = _ix(p, "dev", 2)
    Vf = p["n%d" % d] * p["Vt"] * math.log(p["It"] / p["Is%d" % d] + 1)
    fwd = p["dir"] >= 0
    return {"reading": _rt(Vf, 0.001) if fwd else 0.0, "ol": 0.0 if fwd else 1.0, "conducts": 1.0 if fwd else 0.0}


G = 9.8
KERNELS: dict[str, Any] = {
    "sw7_rollout": _k({"h": 0.03, "surf": 2.0, "c0": 0.03, "c1": 0.04, "c2": 0.08, "c3": 0.30, "g": G}, _rollout, _rollout_m),
    "sw7_pull": _k({"m": 0.8, "mu_s": 0.35, "mu_r": 0.02, "mode": 0.0, "g": G}, _pull),
    "sw7_trolley": _k({"M": 0.5, "mb": 0.2, "mu": 0.4, "h": 0.08, "g": G}, _trolley),
    "sw7_roller": _k({"m": 0.25, "ang": 30.0, "g": G}, _roller, _roller_m),
    "sw7_dincline": _k({"h1": 0.12, "a1": 20.0, "a2": 14.0, "c": 0.01}, _dincline),
    "sw7_proj": _k({"v0": 3.0, "ang": 45.0, "g": G}, _proj, _proj_m),
    "sw7_fall": _k({"h": 2.0, "g": G, "body": 0.0, "m_p": 0.00499, "A_flat": 0.06237, "Cd_flat": 1.28,
                   "A_ball": 0.002827, "Cd_ball": 0.47, "rho_air": 1.2}, _fall),
    "sw7_crater": _k({"m": 0.2, "h": 0.5, "F": 40.0, "g": G}, _crater),
    "sw7_stairs": _k({"m": 45.0, "n": 20.0, "hs": 0.17, "P": 320.0, "g": G}, _stairs),
    "sw7_pend_decay": _k({"L": 1.0, "g": G, "th0": 0.2618, "b": 0.02, "nsw": 20.0}, _pend, _pend_m),
    "sw7_jet": _k({"H": 0.30, "S": 0.30, "y0": 0.05, "y1": 0.12, "y2": 0.20, "hole": 0.0, "g": G, "rho": 998.0}, _jet),
    "sw7_cuboid": _k({"a": 0.10, "b": 0.05, "c": 0.025, "rho": 7874.0, "face": 2.0, "g": G, "ksand": 2e-6}, _cuboid),
    "sw7_upthrust": _k({"V": 0.001, "mb": 0.03, "rho": 998.0, "frac": 1.0, "g": G}, _upthrust),
    "sw7_density": _k({"body": 0.0, "m0": 0.006, "rho0": 240.0, "m1": 0.03937, "rho1": 7874.0, "rho_w": 998.0,
                      "lcV": 5e-7}, _density),
    "sw7_balance": _k({"m0": 0.0437, "m1": 0.11826, "body": 0.0, "w": 0.0}, _balance, _balance_m),
    "sw7_vessel": _k({"vessel": 0.0, "D0": 0.0652, "h0": 0.0874, "D1": 0.0486, "h1": 0.0752, "lc": 0.0001}, _vessel),
    "sw7_sheet": _k({"body": 1.0, "t0": 0.00046, "t1": 0.00112, "A1": 0.00236, "lc": 0.00001, "lcA": 0.00005}, _sheet),
    "sw7_pscale": _k({"L": 0.1374, "lc": 0.002}, _pscale),
    "sw7_lenscomb": _k({"f1": 0.20, "f2": 0.30, "u": 0.40}, _lenscomb),
    "sw7_solidsound": _k({"medium": 0.0, "Y0": 1.1e10, "rho0": 650.0, "Y1": 3.0e9, "rho1": 1150.0, "Tc": 25.0,
                         "d0": 1.0, "d1": 5.0, "d2": 1.0}, _solidsound),
    "sw7_echo": _k({"i_deg": 40.0, "r_deg": 40.0, "w": 6.0}, _echo, _echo_m),
    "sw7_tins": _k({"tin": 0.0, "a0": 0.95, "a1": 0.25, "G": 800.0, "A": 0.006, "hA": 0.35, "C": 860.0, "Ta": 30.0,
                   "tm": 2400.0}, _tins, _tins_m),
    "sw7_waxcool": _k({"T0": 80.0, "Ts": 28.0, "Tm": 57.0, "hA": 0.3, "m": 0.03, "c": 2500.0, "Lf": 2.0e5, "lc": 0.5},
                     _waxcool, _waxcool_m),
    "sw7_bimetal": _k({"a1": 19e-6, "a2": 11.8e-6, "ts": 0.001, "Ls": 0.15, "T0": 25.0, "T": 125.0}, _bimetal),
    "sw7_level": _k({"V0": 1.0e-4, "gam": 4.9e-4, "gg": 2.55e-5, "a": 7.07e-6, "T0": 25.0, "T": 45.0}, _level),
    "sw7_loss": _k({"m": 0.15, "c": 4186.0, "A": 0.012, "h": 12.0, "f": 1.0, "T0": 70.0, "Ts": 28.0, "drop": 5.0}, _loss),
    "sw7_plating": _k({"I": 0.5, "tm": 1200.0, "M": 0.063546, "n": 2.0, "F": 96485.33212, "lc": 1e-6}, _plating),
    "sw7_liquid": _k({"liq": 0.0, "s0": 0.05, "s1": 1e-4, "s2": 0.4, "s3": 0.3, "s4": 1.7, "V": 6.0, "cellk": 50.0,
                     "Rs": 330.0, "Vf": 1.8}, _liquid),
    "sw7_swing": _k({"B": 0.08, "I": 2.0, "Lr": 0.05, "m": 0.004, "g": G, "sI": 1.0, "sB": 1.0}, _swing),
    "sw7_dmm": _k({"mode": 0.0, "R": 4720.0, "E": 9.24, "Vac": 12.3, "Rc": 0.4}, _dmm),
    "sw7_dtest": _k({"dev": 0.0, "dir": 1.0, "It": 1e-3, "n0": 1.8, "Is0": 3e-9, "n1": 2.0, "Is1": 2e-18, "Vt": 0.02585},
                   _dtest),
}
KERNELS["sw7_pend_decay"].amp_after = staticmethod(pend_amp_after)
FAMILY = {k: "mech" for k in KERNELS}
FAMILY.update({"sw7_lenscomb": "optics", "sw7_solidsound": "osc_wave", "sw7_echo": "osc_wave", "sw7_tins": "thermo",
               "sw7_waxcool": "thermo", "sw7_bimetal": "thermo", "sw7_level": "thermo", "sw7_loss": "thermo",
               "sw7_plating": "em", "sw7_liquid": "em", "sw7_swing": "em", "sw7_dmm": "em", "sw7_dtest": "em"})

TEXTBOOK = {
    "sw7_rollout_d": lambda p: p["h"] / p["c%d" % _ix(p, "surf", 4)],                 # m g h = c m g d
    "sw7_pull_F": lambda p: (p["mu_s"] if p["mode"] < 0.5 else p["mu_r"]) * p["m"] * p["g"],
    "sw7_trolley_KE": lambda p: p["M"] * p["g"] * p["h"],                             # the potential energy it lost
    "sw7_roller_W": lambda p: p["m"] * p["g"],                                        # F = W sin(theta)
    "sw7_dincline_h2": lambda p: (p["h1"] * (math.tan(p["a1"] * PI / 180) - p["c"]) * math.tan(p["a2"] * PI / 180)
                                 / (math.tan(p["a1"] * PI / 180) * (math.tan(p["a2"] * PI / 180) + p["c"]))),
    "sw7_proj_ang": lambda p: 45.0,                                                   # R = v0^2 sin(2 theta) / g
    "sw7_fall_t": lambda p: math.sqrt(2 * p["h"] / p["g"]),
    "sw7_crater_F": lambda p: p["F"],
    "sw7_stairs_P": lambda p: p["P"],
    "sw7_pend_gamma": lambda p: p["b"] / 2,                                           # A = A0 exp(-b t / 2)
    "sw7_jet_v": lambda p: math.sqrt(2 * p["g"] * (p["H"] - p["y%d" % _ix(p, "hole", 3)])),   # Torricelli
    "sw7_cuboid_P": lambda p: p["rho"] * p["g"] * (p["c"], p["b"], p["a"])[_ix(p, "face", 3)],  # P = rho g (height)
    "sw7_upthrust_U": lambda p: p["rho"] * p["g"] * p["V"] * p["frac"],               # Archimedes
    "sw7_density_rho": lambda p: p["rho%d" % _ix(p, "body", 2)],
    "sw7_balance_m": lambda p: p["m%d" % _ix(p, "body", 2)],
    "sw7_vessel_V": lambda p: PI * p["D%d" % _ix(p, "vessel", 2)] ** 2 * p["h%d" % _ix(p, "vessel", 2)] / 4,
    "sw7_sheet_V": lambda p: p["A1"] * p["t1"],
    "sw7_pscale_L": lambda p: p["L"],
    "sw7_lens_F": lambda p: 1 / (1 / p["f1"] + 1 / p["f2"]),                          # P = P1 + P2
    "sw7_sound_v": lambda p: (331.3 * math.sqrt(1 + p["Tc"] / 273.15) if _ix(p, "medium", 3) == 2
                             else math.sqrt(p["Y%d" % _ix(p, "medium", 3)] / p["rho%d" % _ix(p, "medium", 3)])),
    "sw7_echo_r": lambda p: p["i_deg"],                                               # angle of reflection = incidence
    "sw7_tins_ratio": lambda p: p["a0"] / p["a1"],
    "sw7_wax_Tm": lambda p: p["Tm"],
    "sw7_bimetal_da": lambda p: p["a1"] - p["a2"],
    "sw7_level_gapp": lambda p: p["gam"] - p["gg"],
    "sw7_loss_k": lambda p: p["h"] * p["A"] * p["f"] / (p["m"] * p["c"]),
    "sw7_plating_Z": lambda p: p["M"] / (p["n"] * p["F"]),                            # Faraday's first law
    "sw7_liquid_s": lambda p: p["s%d" % _ix(p, "liq", 5)],
    "sw7_swing_B": lambda p: p["B"],
    "sw7_dmm_R": lambda p: p["R"],
    "sw7_dtest_Vf": lambda p: p["n%d" % _ix(p, "dev", 2)] * p["Vt"] * math.log(p["It"] / p["Is%d" % _ix(p, "dev", 2)] + 1),
}
