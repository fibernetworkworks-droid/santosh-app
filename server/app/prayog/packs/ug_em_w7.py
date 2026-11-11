"""Kernel pack `ug_em_w7`: the B.Sc. ELECTRICITY AND MAGNETISM set-ups that were still unbuilt in
`syllabus/physics/ug.json` (DU LOCF 2019 / UGCF 2022 practical lists, Indu Prakash's Practical Physics).
Its exact JavaScript twin is `app/static/prayog/packs/ug_em_w7.js`; the server's tests run both and compare.

    w7_bg         ballistic galvanometer with lamp and scale (six set-ups: constants, leakage, Rayleigh,
                  mutual inductance, earth inductor, search coil in a solenoid / Hall-probe gaussmeter)
    w7_carey      Carey Foster bridge                 w7_potlow    low resistance on a potentiometer
    w7_anderson   Anderson's bridge                   w7_unibridge universal R / L / C bridge
    w7_qmeter     Q-meter                             w7_tau       RC and RL time constants
    w7_xfmr       transformer under load              w7_motor     permanent-magnet DC motor
    w7_gen        AC / DC generator                   w7_fallmag   magnet falling through a coil
    w7_gconv      galvanometer into a meter           w7_srcreg    constant-voltage / constant-current source
    w7_magneto    deflection and vibration magnetometers

One rule runs through the file: a reading is SIMULATED and the textbook formula is only what it is checked
against. Throws of the galvanometer come from integrating its equation of motion, null points from searching
the solved network for zero detector current, time constants from integrating the circuit, emfs from
differentiating the flux numerically. Every network (DC or AC) goes through one small nodal solver in complex
arithmetic. Deterministic throughout: fixed step counts, no randomness, no wall clock.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
MU0 = 4e-7 * PI
GOLD = 0.6180339887498949


# ============================================================================================ complex helpers
def _cdiv(ar: float, ai: float, br: float, bi: float) -> tuple[float, float]:
    d = br * br + bi * bi
    return (ar * br + ai * bi) / d, (ai * br - ar * bi) / d


def _cmul(ar: float, ai: float, br: float, bi: float) -> tuple[float, float]:
    return ar * br - ai * bi, ar * bi + ai * br


def _par(ar: float, ai: float, br: float, bi: float) -> tuple[float, float]:
    """Two impedances in parallel: ab / (a + b)."""
    nr, ni = _cmul(ar, ai, br, bi)
    return _cdiv(nr, ni, ar + br, ai + bi)


def _solve(n: int, els: list) -> list:
    """Nodal analysis in complex numbers. Node 0 is earth; nodes 1..n are unknown. Each element is
    [a, b, Zr, Zi, Er, Ei]: an impedance Z from node a to node b in series with an emf E that drives current
    from a to b, so the branch current a -> b is (Va - Vb + E) / Z. Returns the node voltages as a list of
    [re, im] with index 0 the earth. Gaussian elimination with partial pivoting."""
    ar = [[0.0] * (n + 1) for _ in range(n)]
    ai = [[0.0] * (n + 1) for _ in range(n)]
    for e in els:
        a, b = int(e[0]), int(e[1])
        yr, yi = _cdiv(1.0, 0.0, e[2], e[3])
        jr, ji = _cmul(yr, yi, e[4], e[5])          # the emf as a current source: E / Z, flowing a -> b
        if a > 0:
            ar[a - 1][a - 1] += yr
            ai[a - 1][a - 1] += yi
            ar[a - 1][n] -= jr
            ai[a - 1][n] -= ji
        if b > 0:
            ar[b - 1][b - 1] += yr
            ai[b - 1][b - 1] += yi
            ar[b - 1][n] += jr
            ai[b - 1][n] += ji
        if a > 0 and b > 0:
            ar[a - 1][b - 1] -= yr
            ai[a - 1][b - 1] -= yi
            ar[b - 1][a - 1] -= yr
            ai[b - 1][a - 1] -= yi
    for c in range(n):
        best, row = -1.0, c
        for r in range(c, n):
            m = ar[r][c] * ar[r][c] + ai[r][c] * ai[r][c]
            if m > best:
                best, row = m, r
        if row != c:
            ar[c], ar[row] = ar[row], ar[c]
            ai[c], ai[row] = ai[row], ai[c]
        pr, pi_ = ar[c][c], ai[c][c]
        for r in range(c + 1, n):
            fr, fi = _cdiv(ar[r][c], ai[r][c], pr, pi_)
            if fr == 0.0 and fi == 0.0:
                continue
            for k in range(c, n + 1):
                mr, mi = _cmul(fr, fi, ar[c][k], ai[c][k])
                ar[r][k] -= mr
                ai[r][k] -= mi
    out = [[0.0, 0.0] for _ in range(n + 1)]
    for c in range(n - 1, -1, -1):
        sr, si = ar[c][n], ai[c][n]
        for k in range(c + 1, n):
            mr, mi = _cmul(ar[c][k], ai[c][k], out[k + 1][0], out[k + 1][1])
            sr -= mr
            si -= mi
        xr, xi = _cdiv(sr, si, ar[c][c], ai[c][c])
        out[c + 1][0] = xr
        out[c + 1][1] = xi
    return out


def _branch(v: list, e: list) -> tuple[float, float]:
    """The current a -> b in element e for the solved node voltages v."""
    a, b = int(e[0]), int(e[1])
    return _cdiv(v[a][0] - v[b][0] + e[4], v[a][1] - v[b][1] + e[5], e[2], e[3])


def _golden(f, lo: float, hi: float, n: int) -> float:
    """The minimum of f between lo and hi: a golden-section search of a fixed number of steps."""
    c, d = hi - GOLD * (hi - lo), lo + GOLD * (hi - lo)
    fc, fd = f(c), f(d)
    for _ in range(n):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - GOLD * (hi - lo)
            fc = f(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + GOLD * (hi - lo)
            fd = f(d)
    return (lo + hi) / 2


def _zero(f, lo: float, hi: float, n: int) -> float:
    """The point between lo and hi where f changes sign (bisection, fixed steps); -1 when it does not."""
    flo, fhi = f(lo), f(hi)
    if (flo > 0) == (fhi > 0):
        return -1.0
    for _ in range(n):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ============================================================================================ ballistic galvanometer
class Bg:
    """A moving-coil ballistic galvanometer read with a lamp and scale. The coil obeys
        Im th'' + b th' + c th = Kc i,
    with Kc = nAB, c the torsion constant of the suspension and b = b0 + Kc^2 / R the damping: b0 from the air
    and Kc^2 / R from the current the moving coil itself induces in a closed circuit of total resistance R. A
    charge q passed in a time short against the period leaves the coil with the angular velocity Kc q / Im, and
    the first throw is found by INTEGRATING that equation (RK4), never from the formula. The spot of light moves
    d = 2 D th on a scale at distance D.

    `mode` picks the set-up on the same instrument:
      0  constants: steady deflection from a potential divider, throw from a capacitor, critical damping resistance
      1  high resistance by leakage of a charged capacitor
      2  Rayleigh's method: self-inductance in a Wheatstone bridge
      3  mutual inductance by the absolute method (reversal of the primary current)
      4  earth inductor: a coil turned through 180 degrees in the Earth's field
      5  field along a solenoid: a search coil and the reversal of the solenoid current (meth 0), or a
         Hall-probe gaussmeter read directly (meth 1)."""

    PARAMS = {"mode": 0.0, "Kc": 0.01, "c": 4e-8, "Im": 6.485e-8, "b0": 2e-9, "G": 150.0, "D": 1.0,
              # mode 0: potential divider E - Rh - r, series box R; capacitor Cq charged to Vq
              "E": 2.0, "Rh": 9999.0, "r": 1.0, "R": 350.0, "Cq": 1e-7, "Vq": 2.0, "part": 0.0,
              # mode 1: leakage
              "Cl": 5e-7, "Vl": 1.0, "Rx": 5e7, "tl": 0.0,
              # mode 2: Rayleigh bridge  P, Q ratio arms; the coil (Lx, rl) in the third arm, S balances it
              "Lx": 0.05, "rl": 12.0, "P": 10.0, "Q": 10.0, "Eb": 2.0, "rs": 0.05, "Rb": 2.0, "Rser": 5000.0,
              # mode 3: mutual inductance; primary current Ip, secondary circuit resistance Rs2
              "Mx": 0.004, "Ip": 0.5, "Rs2": 9850.0, "r3": 0.005,
              # mode 4: earth inductor
              "Ne": 800.0, "re": 0.1, "BH": 3.5e-5, "BV": 3.2e-5, "axis": 0.0,
              # mode 5: solenoid and search coil
              "ns": 2000.0, "Ls": 0.4, "as_": 0.025, "Is": 2.0, "x": 0.0, "Nc": 1000.0, "rc": 0.01, "meth": 0.0}
    VARS = ["t", "theta", "d"]

    # ---------------------------------------------------------------- the equation of motion
    @staticmethod
    def damping(p: dict, rtot: float) -> float:
        """b for a circuit of total resistance rtot (galvanometer included); rtot <= 0 means open circuit."""
        return p["b0"] + (p["Kc"] * p["Kc"] / rtot if rtot > 0 else 0.0)

    @staticmethod
    def t0(p: dict) -> float:
        return 2 * PI * math.sqrt(p["Im"] / p["c"])

    @staticmethod
    def rk4(th: float, om: float, p: dict, b: float, drive: float, h: float) -> tuple[float, float]:
        im, c = p["Im"], p["c"]
        a1 = (drive - b * om - c * th) / im
        t2, o2 = th + 0.5 * h * om, om + 0.5 * h * a1
        a2 = (drive - b * o2 - c * t2) / im
        t3, o3 = th + 0.5 * h * o2, om + 0.5 * h * a2
        a3 = (drive - b * o3 - c * t3) / im
        t4, o4 = th + h * o3, om + h * a3
        a4 = (drive - b * o4 - c * t4) / im
        return th + h * (om + 2 * o2 + 2 * o3 + o4) / 6, om + h * (a1 + 2 * a2 + 2 * a3 + a4) / 6

    @staticmethod
    def throw(p: dict, q: float, rtot: float, periods: float, per: int) -> dict:
        """Pass the charge q and follow the coil. Returns the first throw th1, the next throw th2 on the other
        side (0 if the coil never comes back through zero), and the time between them (half a period)."""
        b = Bg.damping(p, rtot)
        h = Bg.t0(p) / per
        n = int(periods * per)
        th, om = 0.0, p["Kc"] * q / p["Im"]
        sgn = 1.0 if om >= 0 else -1.0
        th1, th2, t1, t2 = 0.0, 0.0, 0.0, 0.0
        found = 0
        for i in range(n):
            th_n, om_n = Bg.rk4(th, om, p, b, 0.0, h)
            if found == 0 and om * sgn > 0 and om_n * sgn <= 0:
                tau = om / (om - om_n) * h
                th1, t1, found = th + 0.5 * om * tau, i * h + tau, 1
            elif found == 1 and om * sgn < 0 and om_n * sgn >= 0:
                tau = om / (om - om_n) * h
                th2, t2, found = th + 0.5 * om * tau, i * h + tau, 2
            th, om = th_n, om_n
            if found == 2:
                break
        if found < 2 or th1 * th2 >= 0:              # never swung back through zero: not oscillatory
            return {"th1": th1, "th2": 0.0, "half": 0.0}
        return {"th1": th1, "th2": th2, "half": t2 - t1}

    @staticmethod
    def dscale(p: dict, th: float) -> float:
        return 2.0 * p["D"] * th

    # ---------------------------------------------------------------- the circuits
    @staticmethod
    def divider(p: dict) -> tuple[float, float]:
        """Mode 0. A cell E through the high box Rh and the small resistance r; the pd across r drives the
        galvanometer through the series box R. Returns (galvanometer current, total circuit resistance)."""
        v = _solve(2, [[0, 1, p["Rh"], 0.0, p["E"], 0.0], [1, 0, p["r"], 0.0, 0.0, 0.0],
                       [1, 2, p["R"] + 1e-9, 0.0, 0.0, 0.0], [2, 0, p["G"], 0.0, 0.0, 0.0]])
        return v[2][0] / p["G"], p["G"] + p["R"] + p["r"] * p["Rh"] / (p["r"] + p["Rh"])

    @staticmethod
    def rayleigh_net(p: dict, s: float, extra: float, emf: float) -> float:
        """Mode 2. Bridge: battery Eb (internal Rb) across nodes 1 and 0; P from 1 to 2, Q from 1 to 3; the coil
        arm (rl + extra, with an emf `emf` in it) from 2 to 0; S from 3 to 0; galvanometer from 2 to 3.
        Returns the galvanometer current 2 -> 3."""
        els = [[0, 1, p["Rb"], 0.0, p["Eb"], 0.0], [1, 2, p["P"], 0.0, 0.0, 0.0], [1, 3, p["Q"], 0.0, 0.0, 0.0],
               [2, 0, p["rl"] + extra, 0.0, emf, 0.0], [3, 0, s, 0.0, 0.0, 0.0],
               [2, 3, p["G"] + p["Rser"], 0.0, 0.0, 0.0]]
        v = _solve(3, els)
        return (v[2][0] - v[3][0]) / (p["G"] + p["Rser"])

    @staticmethod
    def rayleigh(p: dict) -> dict:
        s = _zero(lambda x: Bg.rayleigh_net(p, x, 0.0, 0.0), 0.01, 500.0, 60)      # steady balance
        # the current in the coil arm at balance, by solving the same network for the node voltage
        els = [[0, 1, p["Rb"], 0.0, p["Eb"], 0.0], [1, 2, p["P"], 0.0, 0.0, 0.0], [1, 3, p["Q"], 0.0, 0.0, 0.0],
               [2, 0, p["rl"], 0.0, 0.0, 0.0], [3, 0, s, 0.0, 0.0, 0.0],
               [2, 3, p["G"] + p["Rser"], 0.0, 0.0, 0.0]]
        v = _solve(3, els)
        i0 = v[2][0] / p["rl"]
        # breaking the battery circuit: the coil's flux Lx i0 collapses; the charge that goes through the
        # galvanometer is (flux) x (galvanometer current per volt of emf in the coil arm, battery arm open).
        open_els = [[1, 2, p["P"], 0.0, 0.0, 0.0], [1, 3, p["Q"], 0.0, 0.0, 0.0],
                    [2, 0, p["rl"], 0.0, 1.0, 0.0], [3, 0, s, 0.0, 0.0, 0.0],
                    [2, 3, p["G"] + p["Rser"], 0.0, 0.0, 0.0]]
        vo = _solve(3, open_els)
        g_per_volt = (vo[2][0] - vo[3][0]) / (p["G"] + p["Rser"])
        q = abs(p["Lx"] * i0 * g_per_volt)                                         # the throw's side is the key's choice
        ig = abs(Bg.rayleigh_net(p, s, p["rs"], 0.0))                                # steady, with rs put in the arm
        # the circuit the swinging coil sees (battery key open): G in series with (P + Q) || (rl + S)
        rdamp = p["G"] + p["Rser"] + (p["P"] + p["Q"]) * (p["rl"] + s) / (p["P"] + p["Q"] + p["rl"] + s)
        return {"S": s, "i0": i0, "q": q, "ig": ig, "rdamp": rdamp}

    @staticmethod
    def sol_b(p: dict, x: float) -> float:
        """Mode 5. Field on the axis of the solenoid at x from its centre: the sum of 400 current rings
        (Biot-Savart for each ring), not the closed formula."""
        n = 400
        dz = p["Ls"] / n
        a2 = p["as_"] * p["as_"]
        tot = 0.0
        for i in range(n):
            z = -p["Ls"] / 2 + (i + 0.5) * dz - x
            tot += MU0 * (p["ns"] * dz * p["Is"]) * a2 / (2.0 * ((a2 + z * z) * math.sqrt(a2 + z * z)))
        return tot

    @staticmethod
    def setup(p: dict) -> dict:
        """For the set mode: the charge passed, the steady galvanometer current of the calibration step, and
        the total resistance of the circuit the swinging coil is closed through (0 = open)."""
        m = int(round(p["mode"]))
        if m == 0:
            ig, rt = Bg.divider(p)
            return {"q": p["Cq"] * p["Vq"], "ig": ig, "rq": 0.0}
        if m == 1:
            # the charge left after leaking for tl through Rx: dq/dt = -q / (Rx Cl), integrated (RK4, 200 steps)
            q = p["Cl"] * p["Vl"]
            k = 1.0 / (p["Rx"] * p["Cl"])
            h = p["tl"] / 200.0
            for _ in range(200):
                k1 = -k * q
                k2 = -k * (q + 0.5 * h * k1)
                k3 = -k * (q + 0.5 * h * k2)
                k4 = -k * (q + h * k3)
                q += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
            return {"q": q, "ig": 0.0, "rq": 0.0}
        if m == 2:
            r = Bg.rayleigh(p)
            return {"q": r["q"], "ig": r["ig"], "rq": r["rdamp"]}
        if m == 3:
            rt = p["Rs2"] + p["G"]
            return {"q": 2.0 * p["Mx"] * p["Ip"] / rt, "ig": p["Ip"] * p["r3"] / (rt + p["r3"]), "rq": rt}
        if m == 4:
            rt = p["Rs2"] + p["G"]
            area = PI * p["re"] * p["re"]
            b = p["BV"] if p["axis"] >= 0.5 else p["BH"]
            return {"q": 2.0 * p["Ne"] * area * b / rt, "ig": 0.0, "rq": rt}
        rt = p["Rs2"] + p["G"]
        return {"q": 2.0 * p["Nc"] * PI * p["rc"] * p["rc"] * Bg.sol_b(p, p["x"]) / rt, "ig": 0.0, "rq": rt}

    @staticmethod
    def cdr(p: dict) -> float:
        """The external resistance at which the motion just stops being oscillatory, found by closing the
        galvanometer through less and less resistance and watching whether the coil swings back through zero."""
        q = p["Cq"] * p["Vq"]

        def osc(rext: float) -> float:
            t = Bg.throw(p, q, rext + p["G"], 12.0, 400)
            return 1.0 if t["th2"] != 0.0 else -1.0
        return _zero(osc, 1.0, 50000.0, 40)

    # ---------------------------------------------------------------- kernel interface
    @staticmethod
    def init(p, cfg=None):
        su = Bg.setup(p)
        return {"t": 0.0, "theta": 0.0, "omega": p["Kc"] * su["q"] / p["Im"], "b": Bg.damping(p, su["rq"])}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n = max(1, int(math.ceil(dt / (Bg.t0(p) / 400.0) - 1e-9)))
        h = dt / n
        for _ in range(n):
            s["theta"], s["omega"] = Bg.rk4(s["theta"], s["omega"], p, s["b"], 0.0, h)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s["t"], "theta": s["theta"], "d": Bg.dscale(p, s["theta"])}

    @staticmethod
    def measure(p, cfg=None):
        m = int(round(p["mode"]))
        su = Bg.setup(p)
        t = Bg.throw(p, su["q"], su["rq"], 1.6, 2000)
        d1, d2 = Bg.dscale(p, t["th1"]), abs(Bg.dscale(p, t["th2"]))
        lam = math.log(d1 / d2) if d1 > 0 and d2 > 0 else 0.0
        # the period is timed with the galvanometer on OPEN circuit (air damping only), as in the laboratory
        period = 2.0 * Bg.throw(p, 1e-7, 0.0, 1.6, 2000)["half"]
        phi = Bg.dscale(p, p["Kc"] * su["ig"] / p["c"])                 # steady deflection of the calibration step
        out = {"q": su["q"], "d1": d1, "d2": d2, "lam": lam, "T": period, "phi": phi, "ig": su["ig"]}
        corr = d1 * (1.0 + lam / 2.0)
        if m == 0:
            out["Si"] = phi / su["ig"] if su["ig"] > 0 else 0.0
            out["Sq"] = corr / su["q"] if su["q"] > 0 else 0.0
            if p["part"] >= 1.5:
                out["Rc"] = Bg.cdr(p)
        elif m == 1:
            q0 = dict(p)
            q0["tl"] = 0.0
            s0 = Bg.setup(q0)
            t0 = Bg.throw(p, s0["q"], 0.0, 1.6, 2000)
            d0 = Bg.dscale(p, t0["th1"])
            out["d0"] = d0
            out["Rest"] = p["tl"] / (p["Cl"] * math.log(d0 / d1)) if p["tl"] > 0 and d1 > 0 and d0 > d1 else 0.0
        elif m == 2:
            out["Lest"] = p["rs"] * period / (2 * PI) * corr / phi if phi > 0 else 0.0
        elif m == 3:
            out["Mest"] = p["r3"] * period / (4 * PI) * corr / phi if phi > 0 else 0.0
        elif m == 4:
            o = dict(p)
            o["axis"] = 1.0 - (1.0 if p["axis"] >= 0.5 else 0.0)
            so = Bg.setup(o)
            to = Bg.throw(p, so["q"], so["rq"], 1.6, 2000)
            do = Bg.dscale(p, to["th1"])
            dv, dh = (d1, do) if p["axis"] >= 0.5 else (do, d1)
            out["dH"], out["dV"] = dh, dv
            out["dip"] = math.atan2(dv, dh) * 180.0 / PI
        else:
            out["B"] = Bg.sol_b(p, p["x"])
            # the charge constant of the instrument from its own period and current sensitivity: q = (T / 2 pi)(c / Kc) th
            kq = period / (2 * PI) * p["c"] / p["Kc"] / (2.0 * p["D"])
            out["Best"] = kq * corr * (p["Rs2"] + p["G"]) / (2.0 * p["Nc"] * PI * p["rc"] * p["rc"])
        return out


def _bg_sq(p: dict) -> float:
    """Charge sensitivity (metres of scale per coulomb): the current sensitivity times 2 pi / T0."""
    return 2.0 * p["D"] * p["Kc"] / math.sqrt(p["Im"] * p["c"])


def _bg_si(p: dict) -> float:
    return 2.0 * p["D"] * p["Kc"] / p["c"]


def _bg_cdr(p: dict) -> float:
    """Critical damping: b0 + Kc^2 / (G + Rc) = 2 sqrt(Im c)."""
    return p["Kc"] * p["Kc"] / (2.0 * math.sqrt(p["Im"] * p["c"]) - p["b0"]) - p["G"]


def _bg_dip(p: dict) -> float:
    return math.atan2(p["BV"], p["BH"]) * 180.0 / PI


def _bg_bsol(p: dict) -> float:
    """Finite solenoid on its axis: B = (mu0 n I / 2)(cos a1 - cos a2)."""
    a, half, x = p["as_"], p["Ls"] / 2, p["x"]
    return MU0 * p["ns"] * p["Is"] / 2.0 * ((x + half) / math.sqrt((x + half) ** 2 + a * a)
                                             - (x - half) / math.sqrt((x - half) ** 2 + a * a))


# ============================================================================================ Carey Foster bridge
class Carey:
    """Carey Foster's bridge. Four gaps in a row hold XL, P, Q, YR; the metre wire (rho ohm per metre, with end
    resistances al and be) joins the outer ends. The battery is across P + Q, the galvanometer between the P-Q
    junction and the jockey at l metres from the left end. The galvanometer current is the solved network; the
    null point is where it changes sign."""

    PARAMS = {"XL": 0.5, "YR": 0.0, "P": 1.0, "Q": 1.0, "rho": 1.4, "al": 0.004, "be": 0.006, "E": 2.0,
              "Rb": 1.0, "G": 80.0, "l": 0.5, "Xu": 0.37, "std": 0.5}
    VARS = ["t", "I_G", "l"]

    @staticmethod
    def ig(p: dict, l: float, xl: float, yr: float) -> float:
        # nodes: 1 = X-P junction (battery +), 0 = Q-Y junction, 2 = P-Q junction, 3 = jockey,
        #        4 = left end of the wire, 5 = right end of the wire
        els = [[0, 1, p["Rb"], 0.0, p["E"], 0.0], [1, 2, p["P"], 0.0, 0.0, 0.0], [2, 0, p["Q"], 0.0, 0.0, 0.0],
               [1, 4, xl + 1e-6, 0.0, 0.0, 0.0], [4, 3, p["al"] + p["rho"] * l, 0.0, 0.0, 0.0],
               [3, 5, p["be"] + p["rho"] * (1.0 - l), 0.0, 0.0, 0.0], [5, 0, yr + 1e-6, 0.0, 0.0, 0.0],
               [2, 3, p["G"], 0.0, 0.0, 0.0]]
        v = _solve(5, els)
        return (v[2][0] - v[3][0]) / p["G"]

    @staticmethod
    def null(p: dict, xl: float, yr: float) -> float:
        return _zero(lambda l: Carey.ig(p, l, xl, yr), 0.0, 1.0, 50)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I_G": Carey.ig(p, p["l"], p["XL"], p["YR"]), "l": p["l"]}

    @staticmethod
    def measure(p, cfg=None):
        l1 = Carey.null(p, p["XL"], p["YR"])
        l2 = Carey.null(p, p["YR"], p["XL"])
        return {"l1": l1, "l2": l2, "dl": l2 - l1, "diff": p["rho"] * (l2 - l1) if l1 >= 0 and l2 >= 0 else 0.0}


# ============================================================================================ potentiometer, low resistance
class PotLow:
    """A low resistance by comparing potential differences on a potentiometer. The driver cell E0 (with the
    rheostat Rh) sets a steady fall of potential along the wire of resistance Rw and length Lw. A second
    circuit (E2, R2) sends ONE current through the unknown Rx and a standard low resistance Sd in series. The
    pd across each is balanced in turn against the wire: Rx / Sd = l1 / l2. `sel` 0 balances Rx, 1 balances Sd."""

    PARAMS = {"E0": 2.0, "Rh": 150.0, "Rw": 12.0, "Lw": 10.0, "E2": 2.0, "R2": 6.0, "Rx": 0.27, "Sd": 0.1,
              "G": 80.0, "sel": 0.0, "l": 5.0}
    VARS = ["t", "I_G", "l"]

    @staticmethod
    def ig(p: dict, l: float, sel: float) -> float:
        first, second = (p["Sd"], p["Rx"]) if sel >= 0.5 else (p["Rx"], p["Sd"])
        f = l / p["Lw"]
        # nodes: 1 = high end A of the wire, 0 = low end B, 2 = jockey, 3 = far end of the resistance being
        # compared, 4 = far end of the other one
        els = [[0, 1, p["Rh"], 0.0, p["E0"], 0.0], [1, 2, p["Rw"] * f + 1e-9, 0.0, 0.0, 0.0],
               [2, 0, p["Rw"] * (1.0 - f) + 1e-9, 0.0, 0.0, 0.0], [1, 3, first, 0.0, 0.0, 0.0],
               [3, 4, second, 0.0, 0.0, 0.0], [4, 1, p["R2"], 0.0, p["E2"], 0.0], [3, 2, p["G"], 0.0, 0.0, 0.0]]
        v = _solve(4, els)
        return (v[3][0] - v[2][0]) / p["G"]

    @staticmethod
    def null(p: dict, sel: float) -> float:
        return _zero(lambda l: PotLow.ig(p, l, sel), 0.0, p["Lw"], 50)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I_G": PotLow.ig(p, p["l"], p["sel"]), "l": p["l"]}

    @staticmethod
    def measure(p, cfg=None):
        l1, l2 = PotLow.null(p, 0.0), PotLow.null(p, 1.0)
        return {"l1": l1, "l2": l2, "Rest": p["Sd"] * l1 / l2 if l1 > 0 and l2 > 0 else 0.0}


# ============================================================================================ Anderson's bridge
class Anderson:
    """Anderson's bridge. Source across a and c; the coil (Lx, rl) with the series resistance r1 from a to b;
    R3 from b to c; R2 from a to d; R4 from d to c; the resistance r from d to e and the capacitor C from e
    to c; the detector (headphones Rg) from b to e. At balance
        r1 + rl = R2 R3 / R4,   Lx = C (R3 / R4) [ r (R4 + R2) + R2 R4 ].
    The two dials r1 and r are turned alternately, each to the quietest point of the solved detector current."""

    PARAMS = {"Lx": 0.15, "rl": 60.0, "r1": 500.0, "R2": 1000.0, "R3": 1000.0, "R4": 1000.0, "r": 100.0,
              "C": 1e-7, "f": 1000.0, "V": 5.0, "Rg": 2000.0, "Ro": 50.0}
    VARS = ["t", "I_G"]

    @staticmethod
    def ig(p: dict, r1: float, r: float) -> float:
        w = 2 * PI * p["f"]
        # nodes: 1 = a, 0 = c, 2 = b, 3 = d, 4 = e
        els = [[0, 1, p["Ro"], 0.0, p["V"], 0.0], [1, 2, p["rl"] + r1, w * p["Lx"], 0.0, 0.0],
               [2, 0, p["R3"], 0.0, 0.0, 0.0], [1, 3, p["R2"], 0.0, 0.0, 0.0], [3, 0, p["R4"], 0.0, 0.0, 0.0],
               [3, 4, r + 1e-6, 0.0, 0.0, 0.0], [4, 0, 0.0, -1.0 / (w * p["C"]), 0.0, 0.0],
               [2, 4, p["Rg"], 0.0, 0.0, 0.0]]
        v = _solve(4, els)
        dr, di = v[2][0] - v[4][0], v[2][1] - v[4][1]
        return math.sqrt(dr * dr + di * di) / p["Rg"]

    @staticmethod
    def balance(p: dict) -> tuple[float, float]:
        r1, r = p["r1"], p["r"]
        for _ in range(12):
            r1 = _golden(lambda x: Anderson.ig(p, x, r), 0.0, 5000.0, 70)
            r = _golden(lambda x: Anderson.ig(p, r1, x), 0.0, 5000.0, 70)
        return r1, r

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I_G": Anderson.ig(p, p["r1"], p["r"])}

    @staticmethod
    def measure(p, cfg=None):
        r1, r = Anderson.balance(p)
        lest = p["C"] * p["R3"] / p["R4"] * (r * (p["R4"] + p["R2"]) + p["R2"] * p["R4"])
        return {"r1": r1, "r": r, "I_G": Anderson.ig(p, r1, r), "Lest": lest, "rlest": p["R2"] * p["R3"] / p["R4"] - r1}


# ============================================================================================ universal R / L / C bridge
class UniBridge:
    """A universal (LCR) bridge: one four-arm frame, the function switch `fn` choosing what stands in the arms.
        fn 0  R  Wheatstone:       unknown Rx | range Rr || main dial Dm | ratio Ra        Rx = Rr Dm / Ra
        fn 1  L  Maxwell-Wien:     coil (Lx, rx) | range Rr || main dial Dm | Cs in parallel with the loss dial Dl
                                                                             Lx = Rr Dm Cs,  rx = Rr Dm / Dl
        fn 2  C  series comparison: capacitor (Cx, rx in series) | range Rr || standard Cs in series with the
                                  loss dial Dl | main dial Dm               Cx = Cs Dm / Rr,  rx = Dl Rr / Dm
    Arm order: unknown from a to b, Rr from b to c, the third arm from a to d, the fourth from d to c; source
    across a and c, detector across b and d. Balance = both dials turned alternately to the quietest point."""

    PARAMS = {"fn": 1.0, "Rx": 470.0, "Lx": 0.082, "Cx": 4.7e-8, "rx": 35.0, "Rr": 1000.0, "Ra": 1000.0,
              "Cs": 1e-7, "Dm": 500.0, "Dl": 5000.0, "f": 1000.0, "V": 5.0, "Rg": 2000.0, "Ro": 50.0}
    VARS = ["t", "I_G"]

    @staticmethod
    def ig(p: dict, dm: float, dl: float) -> float:
        w = 2 * PI * p["f"]
        fn = int(round(p["fn"]))
        if fn == 0:
            zx = (p["Rx"], 0.0)
            z3 = (dm + 1e-6, 0.0)
            z4 = (p["Ra"], 0.0)
        elif fn == 1:
            zx = (p["rx"], w * p["Lx"])
            z3 = (dm + 1e-6, 0.0)
            z4 = _par(dl + 1e-6, 0.0, 0.0, -1.0 / (w * p["Cs"]))
        else:
            zx = (p["rx"], -1.0 / (w * p["Cx"]))
            z3 = (dl + 1e-6, -1.0 / (w * p["Cs"]))
            z4 = (dm + 1e-6, 0.0)
        # nodes: 1 = a, 0 = c, 2 = b, 3 = d
        els = [[0, 1, p["Ro"], 0.0, p["V"], 0.0], [1, 2, zx[0], zx[1], 0.0, 0.0], [2, 0, p["Rr"], 0.0, 0.0, 0.0],
               [1, 3, z3[0], z3[1], 0.0, 0.0], [3, 0, z4[0], z4[1], 0.0, 0.0], [2, 3, p["Rg"], 0.0, 0.0, 0.0]]
        v = _solve(3, els)
        dr, di = v[2][0] - v[3][0], v[2][1] - v[3][1]
        return math.sqrt(dr * dr + di * di) / p["Rg"]

    @staticmethod
    def balance(p: dict) -> tuple[float, float]:
        fn = int(round(p["fn"]))
        dm, dl = p["Dm"], p["Dl"]
        if fn == 0:
            return _golden(lambda x: UniBridge.ig(p, x, dl), 1.0, 11110.0, 80), dl
        lo, hi = (10.0, 1e6) if fn == 1 else (0.0, 2000.0)
        for _ in range(12):
            dm = _golden(lambda x: UniBridge.ig(p, x, dl), 1.0, 11110.0, 80)
            dl = _golden(lambda x: UniBridge.ig(p, dm, x), lo, hi, 80)
        return dm, dl

    @staticmethod
    def value(p: dict, dm: float, dl: float) -> float:
        fn = int(round(p["fn"]))
        if fn == 0:
            return p["Rr"] * dm / p["Ra"]
        if fn == 1:
            return p["Rr"] * dm * p["Cs"]
        return p["Cs"] * dm / p["Rr"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I_G": UniBridge.ig(p, p["Dm"], p["Dl"])}

    @staticmethod
    def measure(p, cfg=None):
        dm, dl = UniBridge.balance(p)
        return {"Dm": dm, "Dl": dl, "I_G": UniBridge.ig(p, dm, dl), "val": UniBridge.value(p, dm, dl)}


def _uni_truth(p: dict) -> float:
    fn = int(round(p["fn"]))
    return p["Rx"] if fn == 0 else (p["Lx"] if fn == 1 else p["Cx"])


# ============================================================================================ Q-meter
class QMeter:
    """A Q-meter. The oscillator sends a measured current through a very small resistance Rsh, so a known small
    voltage e is injected in series with the coil and the tuning capacitor C. The coil is L and R with its own
    self-capacitance Cd across it. An electronic voltmeter across C reads Vc, and the dial is marked Q = Vc / e.
    C is turned for the largest reading at each frequency: that maximum is found by searching the solved
    circuit. Indicated Q is lower than the coil's own wL / R by the factor (1 + Cd / C)."""

    PARAMS = {"L": 2.5e-4, "R": 8.0, "Cd": 8e-12, "f": 1e6, "C": 1e-10, "e": 0.02, "Rsh": 0.02}
    VARS = ["t", "Q", "Vc"]

    @staticmethod
    def vc(p: dict, f: float, c: float) -> float:
        w = 2 * PI * f
        zr, zi = _par(p["R"], w * p["L"], 0.0, -1.0 / (w * p["Cd"]))
        xc = -1.0 / (w * c)
        ir, ii = _cdiv(p["e"], 0.0, p["Rsh"] + zr, zi + xc)
        vr, vi = _cmul(ir, ii, 0.0, xc)
        return math.sqrt(vr * vr + vi * vi)

    @staticmethod
    def tune(p: dict, f: float) -> float:
        return _golden(lambda c: -QMeter.vc(p, f, c), 1e-11, 6e-10, 90)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        v = QMeter.vc(p, p["f"], p["C"])
        return {"t": s.get("t", 0.0), "Vc": v, "Q": v / p["e"]}

    @staticmethod
    def measure(p, cfg=None):
        c1 = QMeter.tune(p, p["f"])
        c2 = QMeter.tune(p, 2.0 * p["f"])
        q1 = QMeter.vc(p, p["f"], c1) / p["e"]
        cd = (c1 - 4.0 * c2) / 3.0
        w = 2 * PI * p["f"]
        return {"C1": c1, "C2": c2, "Q": q1, "Cdest": cd, "Lest": 1.0 / (w * w * (c1 + cd)), "Qtrue": q1 * (1.0 + cd / c1)}


# ============================================================================================ RC / RL time constant
class Tau:
    """A step of voltage V0 applied to R and C in series (mode 0, the voltage across C is watched) or to R and
    a coil of inductance L and resistance rl (mode 1, the voltage across R is watched: it follows the current).
    The generator has the output resistance Rg. The circuit's differential equation is INTEGRATED (RK4) and the
    time constant is the time the trace takes to reach 63.2 % (1 - 1/e) of its final value."""

    PARAMS = {"mode": 0.0, "R": 10000.0, "C": 1e-7, "L": 0.1, "rl": 40.0, "Rg": 50.0, "V0": 4.0}
    VARS = ["t", "v"]

    @staticmethod
    def rate(p: dict) -> float:
        if p["mode"] >= 0.5:
            return (p["R"] + p["rl"] + p["Rg"]) / p["L"]
        return 1.0 / ((p["R"] + p["Rg"]) * p["C"])

    @staticmethod
    def final(p: dict) -> float:
        if p["mode"] >= 0.5:
            return p["V0"] * p["R"] / (p["R"] + p["rl"] + p["Rg"])
        return p["V0"]

    @staticmethod
    def run(p: dict, frac: float) -> float:
        """Time for the watched voltage to rise from 0 to frac of its final value."""
        k = Tau.rate(p)
        h = 1.0 / (k * 400.0)
        y, vf = 0.0, Tau.final(p)
        for i in range(4000):
            k1 = k * (vf - y)
            k2 = k * (vf - (y + 0.5 * h * k1))
            k3 = k * (vf - (y + 0.5 * h * k2))
            k4 = k * (vf - (y + h * k3))
            yn = y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
            if yn >= frac * vf:
                return (i + (frac * vf - y) / (yn - y)) * h
            y = yn
        return 0.0

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "v": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt
        s["v"] = Tau.final(p) * (1.0 - math.exp(-Tau.rate(p) * s["t"]))

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "v": s.get("v", 0.0)}

    @staticmethod
    def measure(p, cfg=None):
        return {"tau": Tau.run(p, 1.0 - math.exp(-1.0)), "thalf": Tau.run(p, 0.5), "vf": Tau.final(p)}


def _tau_tb(p: dict) -> float:
    if p["mode"] >= 0.5:
        return p["L"] / (p["R"] + p["rl"] + p["Rg"])
    return (p["R"] + p["Rg"]) * p["C"]


# ============================================================================================ transformer
class Xfmr:
    """A small mains-type transformer on a low-voltage AC supply, as its equivalent circuit: primary winding
    resistance R1 and leakage reactance X1; the core as Rc (iron loss) in parallel with Xm (magnetising); an
    ideal transformer of turns ratio nr = Ns / Np; then the secondary R2 and X2 and the load RL (RL <= 0 means
    the secondary is open). The network is solved with everything referred to the primary."""

    PARAMS = {"nr": 0.5, "V1": 12.0, "RL": 20.0, "R1": 1.2, "X1": 0.8, "R2": 0.35, "X2": 0.2,
              "Rc": 900.0, "Xm": 450.0}
    VARS = ["t", "V2", "I1", "I2", "eta"]

    @staticmethod
    def solve(p: dict, rl: float) -> dict:
        n2 = p["nr"] * p["nr"]
        mr, mi = _par(p["Rc"], 0.0, 0.0, p["Xm"])
        if rl > 0:
            sr, si = (p["R2"] + rl) / n2, p["X2"] / n2
            # nodes: 1 = supply, 2 = the core node
            els = [[0, 1, 1e-6, 0.0, p["V1"], 0.0], [1, 2, p["R1"], p["X1"], 0.0, 0.0],
                   [2, 0, mr, mi, 0.0, 0.0], [2, 0, sr, si, 0.0, 0.0]]
        else:
            els = [[0, 1, 1e-6, 0.0, p["V1"], 0.0], [1, 2, p["R1"], p["X1"], 0.0, 0.0], [2, 0, mr, mi, 0.0, 0.0]]
        v = _solve(2, els)
        i1r, i1i = _branch(v, els[1])
        e = math.sqrt(v[2][0] * v[2][0] + v[2][1] * v[2][1])
        i1 = math.sqrt(i1r * i1r + i1i * i1i)
        pin = v[1][0] * i1r + v[1][1] * i1i
        if rl > 0:
            i2r, i2i = _branch(v, els[3])
            i2 = math.sqrt(i2r * i2r + i2i * i2i) / p["nr"]
            v2 = i2 * rl
        else:
            i2, v2 = 0.0, e * p["nr"]
        pout = i2 * i2 * rl if rl > 0 else 0.0
        return {"V2": v2, "I1": i1, "I2": i2, "Pin": pin, "Pout": pout, "eta": pout / pin if pin > 0 else 0.0}

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        r = Xfmr.solve(p, p["RL"])
        return {"t": s.get("t", 0.0), "V2": r["V2"], "I1": r["I1"], "I2": r["I2"], "eta": r["eta"]}

    @staticmethod
    def measure(p, cfg=None):
        r = Xfmr.solve(p, p["RL"])
        o = Xfmr.solve(p, 0.0)
        r["V2open"] = o["V2"]
        r["ratio"] = o["V2"] / p["V1"]
        r["P0"] = o["Pin"]
        return r


# ============================================================================================ DC motor
class Motor:
    """A small permanent-magnet DC motor running light. Electrical: V = I Ra + k w. Mechanical:
    J dw/dt = k I - Tf - bv w (Tf the friction of the brushes and bearings, bv the windage). The speed is found
    by RUNNING the motor from rest (RK4) until it settles, not from the steady-state formula."""

    PARAMS = {"V": 6.0, "k": 0.012, "Ra": 2.4, "Tf": 0.0008, "bv": 2e-6, "J": 4e-6}
    VARS = ["t", "w", "I", "rpm"]

    @staticmethod
    def acc(p: dict, w: float) -> float:
        i = (p["V"] - p["k"] * w) / p["Ra"]
        tq = p["k"] * i - p["bv"] * w
        if w <= 0 and tq <= p["Tf"]:
            return 0.0                                  # too little torque to break away
        return (tq - p["Tf"]) / p["J"]

    @staticmethod
    def advance(p: dict, w: float, h: float) -> float:
        k1 = Motor.acc(p, w)
        k2 = Motor.acc(p, w + 0.5 * h * k1)
        k3 = Motor.acc(p, w + 0.5 * h * k2)
        k4 = Motor.acc(p, w + h * k3)
        return max(0.0, w + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6)

    @staticmethod
    def tm(p: dict) -> float:
        return p["J"] / (p["bv"] + p["k"] * p["k"] / p["Ra"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "w": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        n = max(1, int(math.ceil(dt / (Motor.tm(p) / 20.0) - 1e-9)))
        for _ in range(n):
            s["w"] = Motor.advance(p, s["w"], dt / n)
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        w = s.get("w", 0.0)
        return {"t": s.get("t", 0.0), "w": w, "I": (p["V"] - p["k"] * w) / p["Ra"], "rpm": w * 60.0 / (2 * PI)}

    @staticmethod
    def measure(p, cfg=None):
        w, h = 0.0, Motor.tm(p) / 40.0
        for _ in range(1200):                           # 30 time constants
            w = Motor.advance(p, w, h)
        i = (p["V"] - p["k"] * w) / p["Ra"]
        return {"w": w, "rpm": w * 60.0 / (2 * PI), "I": i, "kest": (p["V"] - i * p["Ra"]) / w if w > 0 else 0.0}


def _motor_w(p: dict) -> float:
    return max(0.0, (p["k"] * p["V"] - p["Ra"] * p["Tf"]) / (p["k"] * p["k"] + p["Ra"] * p["bv"]))


# ============================================================================================ generator
class Gen:
    """A coil of N turns and area A turned at f revolutions a second in a field B. The flux linkage is
    N B A cos(2 pi f t); the emf is minus its rate of change, taken NUMERICALLY (central difference) at 2000
    points of one turn. `mode` 0: slip rings, the emf reaches the brushes as it is (AC). `mode` 1: a split-ring
    commutator swaps the connections every half turn, so the brushes see |emf| (pulsating DC)."""

    PARAMS = {"mode": 0.0, "N": 200.0, "B": 0.05, "A": 0.0012, "f": 10.0}
    VARS = ["t", "emf", "flux"]

    @staticmethod
    def flux(p: dict, t: float) -> float:
        return p["N"] * p["B"] * p["A"] * math.cos(2 * PI * p["f"] * t)

    @staticmethod
    def emf(p: dict, t: float) -> float:
        h = 1.0 / (p["f"] * 20000.0)
        e = -(Gen.flux(p, t + h) - Gen.flux(p, t - h)) / (2 * h)
        return abs(e) if p["mode"] >= 0.5 else e

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        t = s.get("t", 0.0)
        return {"t": t, "emf": Gen.emf(p, t), "flux": Gen.flux(p, t)}

    @staticmethod
    def measure(p, cfg=None):
        n = 2000
        pk, tot, sq = 0.0, 0.0, 0.0
        for i in range(n):
            e = Gen.emf(p, (i + 0.5) / (n * p["f"]))
            if abs(e) > pk:
                pk = abs(e)
            tot += e
            sq += e * e
        return {"peak": pk, "mean": tot / n, "rms": math.sqrt(sq / n), "w": 2 * PI * p["f"]}


def _gen_peak(p: dict) -> float:
    return p["N"] * p["B"] * p["A"] * 2 * PI * p["f"]


# ============================================================================================ falling magnet
class FallMag:
    """A short bar magnet of dipole moment m dropped from rest, a height h above a flat coil of N turns and
    radius a, down the coil's axis. The flux through the coil is that of a dipole on the axis,
        Phi = mu0 m a^2 / (2 (a^2 + z^2)^(3/2)),
    and the emf is -N dPhi/dt taken numerically while the magnet falls freely (the coil feeds a high-impedance
    ADC, so the induced current and its braking are negligible). The ADC samples at fs."""

    PARAMS = {"m": 0.75, "N": 500.0, "a": 0.02, "h": 0.4, "g": 9.8, "fs": 5000.0}
    VARS = ["t", "emf", "z"]

    @staticmethod
    def link(p: dict, z: float) -> float:
        a2 = p["a"] * p["a"]
        return p["N"] * MU0 * p["m"] * a2 / (2.0 * ((a2 + z * z) * math.sqrt(a2 + z * z)))

    @staticmethod
    def zt(p: dict, t: float) -> float:
        return -p["h"] + 0.5 * p["g"] * t * t

    @staticmethod
    def emf(p: dict, t: float) -> float:
        d = 1e-6
        return -(FallMag.link(p, FallMag.zt(p, t + d)) - FallMag.link(p, FallMag.zt(p, t - d))) / (2 * d)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        t = s.get("t", 0.0)
        return {"t": t, "emf": FallMag.emf(p, t), "z": FallMag.zt(p, t)}

    @staticmethod
    def measure(p, cfg=None):
        tc = math.sqrt(2.0 * p["h"] / p["g"])               # the instant the magnet is at the coil's centre
        t0 = math.sqrt(2.0 * max(p["h"] - 6.0 * p["a"], 0.0) / p["g"])
        t1 = math.sqrt(2.0 * (p["h"] + 6.0 * p["a"]) / p["g"])
        n = int((t1 - t0) * p["fs"])
        lo, hi, tlo, thi, a1, a2 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        for i in range(n + 1):
            t = t0 + i / p["fs"]
            e = FallMag.emf(p, t)
            if e < lo:
                lo, tlo = e, t
            if e > hi:
                hi, thi = e, t
            if t < tc:
                a1 += e / p["fs"]
            else:
                a2 += e / p["fs"]
        pk = (abs(lo) + abs(hi)) / 2
        v = math.sqrt(2.0 * p["g"] * p["h"])
        return {"pk1": lo if tlo < thi else hi, "pk2": hi if tlo < thi else lo, "pk": pk, "dt": abs(thi - tlo),
                "area1": a1, "area2": a2, "v": v,
                "mest": pk * p["a"] * p["a"] * 25.0 * math.sqrt(5.0) / (24.0 * p["N"] * MU0 * v)}


def _fall_pk(p: dict) -> float:
    """Peak emf of a dipole passing a coil at speed v: (24 / (25 sqrt 5)) N mu0 m v / a^2, at z = -+ a/2."""
    return 24.0 / (25.0 * math.sqrt(5.0)) * p["N"] * MU0 * p["m"] * math.sqrt(2.0 * p["g"] * p["h"]) / (p["a"] * p["a"])


# ============================================================================================ galvanometer into a meter
class GConv:
    """A moving-coil galvanometer of resistance G and figure of merit kf (amperes per division, n divisions to
    full scale) turned into a voltmeter (mode 0: a high resistance Rs in series) or an ammeter (mode 1: a
    shunt Sh in parallel). `stage` picks the circuit being read:
        0  cell E, high box R and the galvanometer in series (the full deflection for the half-deflection method)
        1  the same with the shunt box S across the galvanometer
        2  the converted meter on test: Vt volts (mode 0) or It amperes (mode 1) applied to it."""

    PARAMS = {"mode": 0.0, "stage": 0.0, "G": 96.0, "kf": 2e-5, "n": 30.0, "E": 2.0, "R": 4000.0, "S": 96.0,
              "Vr": 3.0, "Ir": 0.3, "Rs": 4904.0, "Sh": 0.192, "Vt": 2.0, "It": 0.2}
    VARS = ["t", "theta", "Ig"]

    @staticmethod
    def ig(p: dict) -> float:
        st = int(round(p["stage"]))
        if st == 0:
            v = _solve(1, [[0, 1, p["R"], 0.0, p["E"], 0.0], [1, 0, p["G"], 0.0, 0.0, 0.0]])
            return v[1][0] / p["G"]
        if st == 1:
            v = _solve(1, [[0, 1, p["R"], 0.0, p["E"], 0.0], [1, 0, p["G"], 0.0, 0.0, 0.0],
                           [1, 0, p["S"], 0.0, 0.0, 0.0]])
            return v[1][0] / p["G"]
        if p["mode"] < 0.5:
            v = _solve(2, [[0, 1, 1e-6, 0.0, p["Vt"], 0.0], [1, 2, p["Rs"], 0.0, 0.0, 0.0], [2, 0, p["G"], 0.0, 0.0, 0.0]])
            return v[2][0] / p["G"]
        # a current It driven into G || Sh: a 1 megohm source resistance behind a large emf
        v = _solve(1, [[0, 1, 1e6, 0.0, p["It"] * 1e6, 0.0], [1, 0, p["G"], 0.0, 0.0, 0.0], [1, 0, p["Sh"], 0.0, 0.0, 0.0]])
        return v[1][0] / p["G"]

    @staticmethod
    def theta(p: dict) -> float:
        return GConv.ig(p) / p["kf"]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        i = GConv.ig(p)
        return {"t": s.get("t", 0.0), "Ig": i, "theta": i / p["kf"]}

    @staticmethod
    def measure(p, cfg=None):
        a = dict(p)
        a["stage"] = 0.0
        th0 = GConv.theta(a)
        b = dict(p)
        b["stage"] = 1.0

        def half(s: float) -> float:
            b["S"] = s
            return GConv.theta(b) - th0 / 2.0
        sh = _zero(half, 0.01, 1e5, 70)                      # the shunt that halves the deflection
        gest = p["R"] * sh / (p["R"] - sh)
        kest = p["E"] / ((p["R"] + gest) * th0)
        igf = p["n"] * kest
        need = p["Vr"] / igf - gest if p["mode"] < 0.5 else igf * gest / (p["Ir"] - igf)
        return {"theta": GConv.theta(p), "th0": th0, "Shalf": sh, "Gest": gest, "kest": kest, "need": need}


def _gconv_need(p: dict) -> float:
    igf = p["n"] * p["kf"]
    return p["Vr"] / igf - p["G"] if p["mode"] < 0.5 else igf * p["G"] / (p["Ir"] - igf)


# ============================================================================================ CV / CC source
class SrcReg:
    """A regulated bench source feeding a load RL. mode 0, constant voltage: it behaves as V0 behind a small
    output resistance ro until the current reaches the limit Ilim, where the voltage folds down steeply.
    mode 1, constant current: it behaves as I0 in parallel with a large output resistance Ro until the voltage
    reaches the compliance limit Vmax. The operating point is where the source's characteristic meets the load
    line V = I RL, found by bisection on the current."""

    PARAMS = {"mode": 0.0, "V0": 9.0, "ro": 0.25, "Ilim": 1.0, "I0": 0.01, "Ro": 50000.0, "Vmax": 12.0, "RL": 30.0}
    VARS = ["t", "V", "I"]

    @staticmethod
    def vsrc(p: dict, i: float) -> float:
        """Terminal voltage the source can hold while delivering the current i."""
        if p["mode"] < 0.5:
            v = p["V0"] - p["ro"] * i
            if i > p["Ilim"]:
                v -= (i - p["Ilim"]) * 2000.0             # the current limiter takes over
            return v
        v = (p["I0"] - i) * p["Ro"]
        return min(v, p["Vmax"] + (p["I0"] - i) * 1.0)

    @staticmethod
    def point(p: dict, rl: float) -> tuple[float, float]:
        top = (p["Ilim"] * 1.2 + p["V0"] / 1000.0) if p["mode"] < 0.5 else p["I0"]
        i = _zero(lambda x: SrcReg.vsrc(p, x) - x * rl, 0.0, top, 60)
        if i < 0:
            i = top
        return i * rl, i

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        v, i = SrcReg.point(p, p["RL"])
        return {"t": s.get("t", 0.0), "V": v, "I": i}

    @staticmethod
    def measure(p, cfg=None):
        v, i = SrcReg.point(p, p["RL"])
        v2, i2 = SrcReg.point(p, p["RL"] * 2.0)
        rout = -(v2 - v) / (i2 - i) if i2 != i else 0.0
        return {"V": v, "I": i, "rout": rout}


def _src_rout(p: dict) -> float:
    return p["ro"] if p["mode"] < 0.5 else p["Ro"]


# ============================================================================================ magnetometers
class Magneto:
    """A bar magnet of moment M and magnetic half-length l, and the Earth's horizontal field H (tesla).
    Deflection magnetometer: the compass box sits d from the magnet's centre, on the magnet's axis (pos 0,
    Tan A) or on its perpendicular bisector (pos 1, Tan B), the arm lying east-west; the needle turns until
    tan(theta) = B / H, B being the SUM of the fields of the magnet's two poles at the needle. Vibration
    magnetometer: the magnet (moment of inertia Im) swings in H alone; its equation th'' = -(M H / Im) sin th is
    integrated from a small release angle and the period timed between passages through the meridian."""

    PARAMS = {"M": 0.5, "H": 3.6e-5, "l": 0.04, "d": 0.2, "pos": 0.0, "Im": 4.2e-5, "amp": 5.0}
    VARS = ["t", "theta", "B"]

    @staticmethod
    def field(p: dict) -> float:
        qm = p["M"] / (2.0 * p["l"])                       # pole strength
        k = MU0 / (4 * PI)
        if p["pos"] < 0.5:
            return k * qm * (1.0 / (p["d"] - p["l"]) ** 2 - 1.0 / (p["d"] + p["l"]) ** 2)
        r2 = p["d"] * p["d"] + p["l"] * p["l"]
        return 2.0 * k * qm / r2 * (p["l"] / math.sqrt(r2))

    @staticmethod
    def period(p: dict) -> float:
        k = p["M"] * p["H"] / p["Im"]
        t_guess = 2 * PI / math.sqrt(k)
        h = t_guess / 2000.0
        th, om = p["amp"] * PI / 180.0, 0.0
        crossings, tprev, tfirst = 0, 0.0, 0.0
        for i in range(5000):
            a1 = -k * math.sin(th)
            t2, o2 = th + 0.5 * h * om, om + 0.5 * h * a1
            a2 = -k * math.sin(t2)
            t3, o3 = th + 0.5 * h * o2, om + 0.5 * h * a2
            a3 = -k * math.sin(t3)
            t4, o4 = th + h * o3, om + h * a3
            a4 = -k * math.sin(t4)
            thn = th + h * (om + 2 * o2 + 2 * o3 + o4) / 6
            omn = om + h * (a1 + 2 * a2 + 2 * a3 + a4) / 6
            if th > 0 >= thn:                               # passing the meridian, going one way
                tc = (i + th / (th - thn)) * h
                crossings += 1
                if crossings == 1:
                    tfirst = tc
                else:
                    tprev = tc
                    break
            th, om = thn, omn
        return tprev - tfirst if crossings >= 2 else 0.0

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        b = Magneto.field(p)
        return {"t": s.get("t", 0.0), "B": b, "theta": math.atan2(b, p["H"]) * 180.0 / PI}

    @staticmethod
    def measure(p, cfg=None):
        b = Magneto.field(p)
        th = math.atan2(b, p["H"])
        t = Magneto.period(p)
        d, l = p["d"], p["l"]
        if p["pos"] < 0.5:
            ratio = 4 * PI / MU0 * (d * d - l * l) ** 2 / (2.0 * d) * math.tan(th)
        else:
            ratio = 4 * PI / MU0 * (d * d + l * l) * math.sqrt(d * d + l * l) * math.tan(th)
        prod = 4 * PI * PI * p["Im"] / (t * t) if t > 0 else 0.0
        return {"theta": th * 180.0 / PI, "T": t, "MbyH": ratio, "MH": prod,
                "Mest": math.sqrt(ratio * prod), "Hest": math.sqrt(prod / ratio) if ratio > 0 else 0.0}


# ============================================================================================ tables
KERNELS: dict[str, Any] = {"w7_bg": Bg, "w7_carey": Carey, "w7_potlow": PotLow, "w7_anderson": Anderson,
                           "w7_unibridge": UniBridge, "w7_qmeter": QMeter, "w7_tau": Tau, "w7_xfmr": Xfmr,
                           "w7_motor": Motor, "w7_gen": Gen, "w7_fallmag": FallMag, "w7_gconv": GConv,
                           "w7_srcreg": SrcReg, "w7_magneto": Magneto}
FAMILY = {k: "circuit" for k in KERNELS}
FAMILY.update({"w7_bg": "em", "w7_gen": "em", "w7_fallmag": "em", "w7_magneto": "em", "w7_motor": "em", "w7_xfmr": "em"})

TEXTBOOK = {
    "w7_bg_sq": _bg_sq, "w7_bg_si": _bg_si, "w7_bg_cdr": _bg_cdr,
    "w7_bg_rx": lambda p: p["Rx"], "w7_bg_lx": lambda p: p["Lx"], "w7_bg_mx": lambda p: p["Mx"],
    "w7_bg_dip": _bg_dip, "w7_bg_bsol": _bg_bsol,
    "w7_carey_diff": lambda p: p["XL"] - p["YR"],
    "w7_potlow_rx": lambda p: p["Rx"],
    "w7_anderson_l": lambda p: p["Lx"],
    "w7_uni_val": _uni_truth,
    "w7_q_l": lambda p: p["L"],
    "w7_tau": _tau_tb,
    "w7_xfmr_ratio": lambda p: p["nr"],
    "w7_motor_w": _motor_w,
    "w7_gen_peak": _gen_peak,
    "w7_fall_pk": _fall_pk,
    "w7_gconv_need": _gconv_need,
    "w7_src_rout": _src_rout,
    "w7_mag_h": lambda p: p["H"],
}
CALCS: dict[str, dict] = {}
