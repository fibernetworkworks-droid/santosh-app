"""Kernel pack `ug_modern_w8`: the B.Sc. MODERN / ATOMIC PHYSICS and MICROWAVE set-ups of
`syllabus/physics/ug.json` that were still unbuilt (DU LOCF 2019 C-IX Elements of Modern Physics Lab, C-XI Quantum
Mechanics Lab, C-XIII Electromagnetic Theory Lab). Its exact JavaScript twin is `app/static/prayog/packs/ug_modern_w8.js`;
the server's tests run both and compare the numbers.

    w8_diode     directly heated vacuum diode: Richardson-Dushman emission, Child's law below saturation
    w8_ion       mercury-vapour tube with an ion collector: ionisation onset
    w8_thomson   cathode-ray tube in crossed electric and magnetic fields (Thomson's e/m)
    w8_mag       cylindrical diode in a solenoid (magnetron cut-off, e/m)
    w8_focus     cathode-ray tube in a long solenoid (helical focusing) or near a bar magnet (circular arc)
    w8_oil       Millikan's oil drops: Stokes fall, balancing and rise-and-fall
    w8_zeeman    normal Zeeman effect of the cadmium red line seen through a Fabry-Perot etalon
    w8_bb        tungsten lamp as a black body seen through a narrow filter by a photodetector
    w8_mw        3 cm microwave optics bench: reflection, prism refraction, polarisation, double slit

A reading is SIMULATED from the physical model (a balance found by bisection, a focus found by scanning, a peak found
by a search, a slope by least squares); the textbook formula is only what it is checked against. Deterministic: fixed
step counts, no randomness, no wall clock. Physical constants are CODATA 2018 (e, m_e, h, k_B, mu_0, c).
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
QE = 1.602176634e-19        # elementary charge, C (exact, SI 2019 / CODATA 2018)
ME = 9.1093837015e-31       # electron mass, kg (CODATA 2018)
H = 6.62607015e-34          # Planck constant, J s (exact)
KB = 1.380649e-23           # Boltzmann constant, J/K (exact)
C = 2.99792458e8            # speed of light, m/s (exact)
MU0 = 1.25663706212e-6      # magnetic constant, N/A^2 (CODATA 2018)
EM = QE / ME                # e/m of the electron, C/kg
A0 = 4 * PI * ME * QE * KB * KB / (H * H * H)   # Richardson's constant, A/(m^2 K^2)
DEG = PI / 180
GOLD = 0.6180339887498949


# ============================================================================================ helpers
def _fit(pts: list[list[float]]) -> list[float]:
    """Least-squares straight line [slope, intercept] (zeros when it cannot be formed)."""
    n = len(pts)
    if n < 2:
        return [0.0, 0.0]
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    d = n * sxx - sx * sx
    if d == 0:
        return [0.0, 0.0]
    m = (n * sxy - sx * sy) / d
    return [m, (sy - m * sx) / n]


def _rows(rows: list[dict], keys: list[str]) -> list[list[float]]:
    out = []
    for r in rows or []:
        vals = []
        ok = True
        for k in keys:
            try:
                vals.append(float(r.get(k)))
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            out.append(vals)
    return out


def _bisect(f, lo: float, hi: float, n: int) -> float:
    """The point between lo and hi where f changes sign (fixed number of halvings); -1 when it does not."""
    flo = f(lo)
    if (flo > 0) == (f(hi) > 0):
        return -1.0
    for _ in range(n):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _golden_max(f, lo: float, hi: float, n: int) -> float:
    c, d = hi - GOLD * (hi - lo), lo + GOLD * (hi - lo)
    fc, fd = f(c), f(d)
    for _ in range(n):
        if fc > fd:
            hi, d, fd = d, c, fc
            c = hi - GOLD * (hi - lo)
            fc = f(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + GOLD * (hi - lo)
            fd = f(d)
    return (lo + hi) / 2


# ============================================================================================ vacuum diode
class W8Diode:
    """A directly heated tungsten-filament diode. The filament temperature follows the heating current through the
    lab's pyrometer calibration T = T0 + kT If (illustrative). The saturation current is Richardson-Dushman,
    Is = A0 S T^2 exp(-e phi / k T); below saturation the anode current is space-charge limited, Isc = Kc Va^1.5
    (Child's law), and the two are joined smoothly: Ia = Is / (1 + (Is / Isc)^6)^(1/6)."""

    PARAMS = {"If": 2.0, "Va": 0.0, "phi": 4.55, "Sa": 2e-6, "Kc": 1e-5, "T0": 400.0, "kT": 800.0, "Vmax": 150.0}
    VARS = ["t", "T", "Is", "Ia", "Ia_uA"]
    IFS = [2.0, 2.1, 2.2, 2.3, 2.4, 2.5]

    @staticmethod
    def temp(p, i_f):
        return p["T0"] + p["kT"] * i_f

    @staticmethod
    def sat(p, t):
        return A0 * p["Sa"] * t * t * math.exp(-p["phi"] * QE / (KB * t))

    @staticmethod
    def anode(p, i_f, va):
        if va <= 0:
            return 0.0
        isat = W8Diode.sat(p, W8Diode.temp(p, i_f))
        isc = p["Kc"] * va ** 1.5
        return isat / (1.0 + (isat / isc) ** 6) ** (1.0 / 6.0)

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        t = W8Diode.temp(p, p["If"])
        ia = W8Diode.anode(p, p["If"], p["Va"])
        return {"t": s.get("t", 0.0), "T": t, "Is": W8Diode.sat(p, t), "Ia": ia, "Ia_uA": ia * 1e6}

    @staticmethod
    def measure(p, cfg=None):
        pts = []
        for i_f in W8Diode.IFS:
            t = W8Diode.temp(p, i_f)
            pts.append([1.0 / t, math.log(W8Diode.anode(p, i_f, p["Vmax"]) / (t * t))])
        m = _fit(pts)[0]
        return {"phi": -m * KB / QE, "T": W8Diode.temp(p, p["If"]), "Ia": W8Diode.anode(p, p["If"], p["Va"])}


# ============================================================================================ mercury ionisation
class W8Ion:
    """A mercury-vapour tube with a separate ion collector held negative (Lenard's method). Electrons accelerated
    through V ionise mercury atoms only once e V exceeds the ionisation energy; just above the threshold the ion
    current rises linearly with the excess energy. The thermal spread of the electron energies rounds the knee:
    I = leak + G s ln(1 + exp((V - Ui) / s)). The straight part extrapolates back to exactly Ui."""

    PARAMS = {"V": 0.0, "Ui": 10.4375, "G": 2e-8, "s": 0.15, "leak": 2e-11, "Vmax": 20.0}
    VARS = ["t", "I", "I_nA"]
    VFIT = [14.0, 15.0, 16.0, 17.0, 18.0]

    @staticmethod
    def current(p, v):
        x = (v - p["Ui"]) / p["s"]
        sp = x + math.log1p(math.exp(-x)) if x > 0 else math.log1p(math.exp(x))
        return p["leak"] + p["G"] * p["s"] * sp

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        i = W8Ion.current(p, p["V"])
        return {"t": s.get("t", 0.0), "I": i, "I_nA": i * 1e9}

    @staticmethod
    def measure(p, cfg=None):
        f = _fit([[v, W8Ion.current(p, v)] for v in W8Ion.VFIT])
        return {"Vi": -f[1] / f[0] if f[0] else 0.0, "I": W8Ion.current(p, p["V"])}


# ============================================================================================ Thomson e/m
class W8Thomson:
    """A cathode-ray tube: electrons accelerated through Va pass between deflecting plates (length l, gap d) and drift
    a distance L to the screen. Helmholtz coils (B = kB Ic) give a magnetic field across the same region. The electric
    deflection is yE = E l (l/2 + L) / (2 Va); the magnetic one is yB = (e/m) B l (l/2 + L) / v with
    v = sqrt(2 (e/m) Va). The spot returns to the centre when E = v B."""

    PARAMS = {"Va": 1500.0, "Vp": 0.0, "Ic": 0.0, "em": EM, "l": 0.02, "d": 0.004, "L": 0.15, "kB": 4.2e-3}
    VARS = ["t", "y", "y_mm", "B", "E"]

    @staticmethod
    def defl(p, vp, b):
        v = math.sqrt(2 * p["em"] * p["Va"])
        g = p["l"] * (p["l"] / 2 + p["L"])
        return (vp / p["d"]) * g / (2 * p["Va"]) - p["em"] * b * g / v

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        y = W8Thomson.defl(p, p["Vp"], p["kB"] * p["Ic"])
        return {"t": s.get("t", 0.0), "y": y, "y_mm": y * 1000, "B": p["kB"] * p["Ic"], "E": p["Vp"] / p["d"]}

    @staticmethod
    def measure(p, cfg=None):
        vp = p["Vp"] if p["Vp"] > 0 else 150.0
        b = _bisect(lambda bb: W8Thomson.defl(p, vp, bb), 0.0, 0.05, 80)
        e = vp / p["d"]
        return {"em": e * e / (2 * p["Va"] * b * b) if b > 0 else 0.0, "Bbal": b,
                "y": W8Thomson.defl(p, p["Vp"], p["kB"] * p["Ic"])}


# ============================================================================================ magnetron e/m
class W8Magnetron:
    """A cylindrical diode (anode radius a, filament radius b) on the axis of a long solenoid, B = mu0 n Is. Below
    the critical field Bc = sqrt(8 Va / ((e/m) a^2 (1 - b^2/a^2)^2)) every electron reaches the anode; above it the
    paths curl back. The spread of emission velocities smears the cut-off into Ia = I0 / (1 + exp((B - Bc)/(w Bc))),
    with I0 = Kd Va^1.5 the space-charge-limited current; the current is half its full value at exactly Bc."""

    PARAMS = {"Va": 6.0, "Is": 0.0, "em": EM, "a": 4e-3, "b": 1e-4, "n": 1e4, "Kd": 1e-4, "w": 0.04}
    VARS = ["t", "B", "Ia", "Ia_mA"]

    @staticmethod
    def geo(p):
        return p["a"] * p["a"] * (1 - p["b"] * p["b"] / (p["a"] * p["a"])) ** 2

    @staticmethod
    def bc(p, va):
        return math.sqrt(8 * va / (p["em"] * W8Magnetron.geo(p)))

    @staticmethod
    def current(p, va, b):
        if va <= 0:
            return 0.0
        bc = W8Magnetron.bc(p, va)
        x = (b - bc) / (p["w"] * bc)
        x = 60.0 if x > 60 else x
        return p["Kd"] * va ** 1.5 / (1 + math.exp(x))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        b = MU0 * p["n"] * p["Is"]
        i = W8Magnetron.current(p, p["Va"], b)
        return {"t": s.get("t", 0.0), "B": b, "Ia": i, "Ia_mA": i * 1000}

    @staticmethod
    def measure(p, cfg=None):
        va = p["Va"]
        half = p["Kd"] * va ** 1.5 / 2
        b = _bisect(lambda bb: W8Magnetron.current(p, va, bb) - half, 0.0, 0.05, 80)
        return {"em": 8 * va / (b * b * W8Magnetron.geo(p)) if b > 0 else 0.0, "Bh": b,
                "Ia": W8Magnetron.current(p, va, MU0 * p["n"] * p["Is"])}


# ============================================================================================ focusing / bar magnet
class W8Focus:
    """meth 0 - helical (Busch) focusing: a cathode-ray tube on the axis of a long solenoid, B = mu0 n Ic. A small
    transverse kick from the X plates draws a line of length len0 on the screen. In the field every electron follows a
    helix of the same pitch; after the drift L its phase is th = (e/m) B L / v and the line shrinks to
    len0 |sin(th/2) / (th/2)|, a point at the first focus th = 2 pi, where e/m = 8 pi^2 Va / (B^2 L^2).
    meth 1 - bar magnet: a short magnet end-on at distance x gives B = mu0 M / (2 pi x^3) across the tube; the beam
    follows a circular arc of radius r = v / ((e/m) B) and is deflected by y = r - sqrt(r^2 - L^2) after the length L;
    a deflection magnetometer in the tube's place reads tan(theta) = B / BH."""

    PARAMS = {"meth": 0.0, "Va": 800.0, "Ic": 0.0, "em": EM, "L": 0.13, "n": 1e4, "len0": 0.02,
              "x": 0.15, "Mm": 1.0, "BH": 3.5e-5}
    VARS = ["t", "B", "ell_mm", "y_mm", "thm"]

    @staticmethod
    def ell(p, b):
        v = math.sqrt(2 * p["em"] * p["Va"])
        th = p["em"] * b * p["L"] / v
        if th < 1e-9:
            return p["len0"]
        return p["len0"] * abs(math.sin(th / 2) / (th / 2))

    @staticmethod
    def bar_b(p, x):
        return MU0 * p["Mm"] / (2 * PI * x * x * x)

    @staticmethod
    def bar_y(p, b):
        if b <= 0:
            return 0.0
        r = math.sqrt(2 * p["Va"] / p["em"]) / b
        if r <= p["L"]:
            return r
        return r - math.sqrt(r * r - p["L"] * p["L"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        if p["meth"] > 0.5:
            b = W8Focus.bar_b(p, p["x"])
            return {"t": s.get("t", 0.0), "B": b, "ell_mm": 0.0, "y_mm": W8Focus.bar_y(p, b) * 1000,
                    "thm": math.atan(b / p["BH"]) / DEG}
        b = MU0 * p["n"] * p["Ic"]
        return {"t": s.get("t", 0.0), "B": b, "ell_mm": W8Focus.ell(p, b) * 1000, "y_mm": 0.0, "thm": 0.0}

    @staticmethod
    def measure(p, cfg=None):
        if p["meth"] > 0.5:
            b = W8Focus.bar_b(p, p["x"])
            y = W8Focus.bar_y(p, b)
            ll = p["L"] * p["L"] + y * y
            return {"em": 8 * p["Va"] * y * y / (b * b * ll * ll), "Bf": b, "y": y}
        n, bmax = 4000, 0.03
        prev, prev2, found = -1.0, -1.0, -1.0
        for k in range(n + 1):
            v = W8Focus.ell(p, bmax * k / n)
            if k >= 2 and prev < prev2 and prev <= v:
                found = bmax * (k - 1) / n
                break
            prev2, prev = prev, v
        if found < 0:
            return {"em": 0.0, "Bf": 0.0, "y": 0.0}
        db = bmax / n
        b = _golden_max(lambda bb: -W8Focus.ell(p, bb), found - db, found + db, 80)
        return {"em": 8 * PI * PI * p["Va"] / (b * b * p["L"] * p["L"]), "Bf": b, "y": 0.0}


# ============================================================================================ Millikan oil drop
class W8Oil:
    """Millikan's apparatus: oil drops between horizontal plates a distance d apart. A drop of radius a falls at the
    Stokes terminal speed vg = 2 a^2 rho g / (9 eta); with the plates at V it moves up at
    (q V/d - m g) / (6 pi eta a). The rig offers five drops of the lab's (radius, number of charges). Balancing:
    q = m g d / Vb with a from the fall. Rise and fall: q = 6 pi eta a (vg + vr) d / V. The Cunningham slip correction
    of a real sub-micron drop (a few per cent) is not modelled, and the lab says so."""

    PARAMS = {"meth": 0.0, "drop": 0.0, "V": 0.0, "e": QE, "eta": 1.81e-5, "rho": 886.0, "g": 9.81, "d": 5e-3,
              "s": 1e-3}
    VARS = ["t", "y", "vel", "a"]
    RAD = [0.62e-6, 0.71e-6, 0.80e-6, 0.66e-6, 0.75e-6]
    NQ = [1.0, 2.0, 4.0, 3.0, 5.0]

    @staticmethod
    def idx(p):
        i = int(math.floor(p["drop"] + 0.5))
        return 0 if i < 0 else (4 if i > 4 else i)

    @staticmethod
    def vel(p, i, v):
        """Upward velocity of drop i with the plates at v (negative = falling)."""
        a = W8Oil.RAD[i]
        m = 4.0 / 3.0 * PI * a * a * a * p["rho"]
        q = W8Oil.NQ[i] * p["e"]
        return (q * v / p["d"] - m * p["g"]) / (6 * PI * p["eta"] * a)

    @staticmethod
    def radius(p, vg):
        return math.sqrt(9 * p["eta"] * vg / (2 * p["rho"] * p["g"]))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0, "y": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt
        s["y"] += W8Oil.vel(p, W8Oil.idx(p), p["V"]) * dt

    @staticmethod
    def view(s, p, cfg=None):
        i = W8Oil.idx(p)
        return {"t": s.get("t", 0.0), "y": s.get("y", 0.0), "vel": W8Oil.vel(p, i, p["V"]), "a": W8Oil.RAD[i]}

    @staticmethod
    def measure(p, cfg=None):
        i = W8Oil.idx(p)
        vg = -W8Oil.vel(p, i, 0.0)
        a = W8Oil.radius(p, vg)
        if p["meth"] > 0.5:
            v = p["V"] if p["V"] > 0 else 500.0
            vr = W8Oil.vel(p, i, v)
            q = 6 * PI * p["eta"] * a * (vg + vr) * p["d"] / v
        else:
            vb = _bisect(lambda vv: W8Oil.vel(p, i, vv), 0.0, 2000.0, 80)
            q = 4.0 / 3.0 * PI * a * a * a * p["rho"] * p["g"] * p["d"] / vb if vb > 0 else 0.0
        return {"e": q / W8Oil.NQ[i], "e19": q / W8Oil.NQ[i] * 1e19, "q": q, "vg": vg}


def _oil_e(rows, p):
    qs = [r[0] for r in _rows(rows, ["q"]) if r[0] > 0]
    if not qs:
        return 0.0
    q1 = min(qs)
    tot = 0.0
    for q in qs:
        k = math.floor(q / q1 + 0.5)
        tot += q / (k if k > 0 else 1)
    return tot / len(qs)


# ============================================================================================ Zeeman effect
class W8Zeeman:
    """The cadmium 643.8 nm line (a 1D2 -> 1P1 singlet: the normal Zeeman triplet) between the poles of an
    electromagnet, seen through a Fabry-Perot etalon of spacing t and a lens of focal length f. Each sigma component
    is shifted by d_sigma = (e/m) B / (4 pi c) in wavenumber. A ring of order m has cos(theta) = m / (2 t sigma) and
    diameter D = 2 f tan(theta); rings are numbered p = 2, 3 from the centre (the innermost order is skipped, it may
    vanish as the field changes). Air is taken as n = 1 in the etalon."""

    PARAMS = {"B": 0.0, "em": EM, "lam": 6.4384696e-7, "t": 3e-3, "f": 0.3}
    VARS = ["t", "B", "D2p", "D2m", "D3p", "D3m"]

    @staticmethod
    def diam(p, sig, ring):
        m = math.floor(2 * p["t"] / p["lam"]) - ring + 1
        c = m / (2 * p["t"] * sig)
        if c >= 1:
            return 0.0
        return 2 * p["f"] * math.tan(math.acos(c))

    @staticmethod
    def rings(p, b):
        s0 = 1.0 / p["lam"]
        ds = p["em"] * b / (4 * PI * C)
        return [W8Zeeman.diam(p, s0 + ds, 2), W8Zeeman.diam(p, s0 - ds, 2),
                W8Zeeman.diam(p, s0 + ds, 3), W8Zeeman.diam(p, s0 - ds, 3)]

    @staticmethod
    def em_from(p, b, r):
        d2 = ((r[2] * r[2] - r[0] * r[0]) + (r[3] * r[3] - r[1] * r[1])) / 2
        dsig = ((r[0] * r[0] - r[1] * r[1]) + (r[2] * r[2] - r[3] * r[3])) / 2 / (4 * p["t"] * d2)
        return 4 * PI * C * dsig / b

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        r = W8Zeeman.rings(p, p["B"])
        return {"t": s.get("t", 0.0), "B": p["B"], "D2p": r[0], "D2m": r[1], "D3p": r[2], "D3m": r[3]}

    @staticmethod
    def measure(p, cfg=None):
        b = p["B"] if p["B"] > 0 else 0.6
        return {"em": W8Zeeman.em_from(p, b, W8Zeeman.rings(p, b)), "B": b}


# ============================================================================================ black-body Planck
class W8BB:
    """A tungsten lamp at temperature T (read on an optical pyrometer) seen through a narrow filter at lam by a
    photodetector. The detector current follows Planck's law, I = K / (exp(h c / (lam k T)) - 1). In the Wien limit
    ln I falls linearly with 1/T, slope -h c / (lam k), which gives h. The emissivity of tungsten changes a little with
    temperature; that is folded into K and not modelled."""

    PARAMS = {"T": 2000.0, "h": H, "lam": 6.5e-7, "K": 1e-2}
    VARS = ["t", "I", "I_nA"]
    TS = [1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0, 2600.0]

    @staticmethod
    def current(p, t):
        return p["K"] / math.expm1(p["h"] * C / (p["lam"] * KB * t))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        i = W8BB.current(p, p["T"])
        return {"t": s.get("t", 0.0), "I": i, "I_nA": i * 1e9}

    @staticmethod
    def measure(p, cfg=None):
        m = _fit([[1.0 / t, math.log(W8BB.current(p, t))] for t in W8BB.TS])[0]
        return {"h": -m * p["lam"] * KB / C, "h34": -m * p["lam"] * KB / C * 1e34, "I": W8BB.current(p, p["T"])}


# ============================================================================================ microwave optics
class W8Mw:
    """A 3 cm microwave optics bench: Gunn transmitter with a horn, a receiving horn with a crystal (square-law)
    detector on a pivoting arm. part 0: reflection from a metal plate, peak at th = inc. part 1: a prism of apex A
    (normal incidence on the first face) deviates the beam by asin(n sin A) - A. part 2: the receiver turned by phi
    reads I0 cos^2(phi) (Malus). part 3: a double slit (centre spacing ds, width as) gives
    I0 cos^2(pi ds sin th / lam) (sin(al)/al)^2 with al = pi as sin th / lam; its first zero is at
    ds sin th = lam / 2. Beams are Gaussian of half width w
    (degrees). Angles in degrees."""

    PARAMS = {"part": 0.0, "th": 0.0, "inc": 45.0, "n": 1.5, "A": 30.0, "w": 8.0, "phi": 0.0, "lam": 0.02848,
              "ds": 0.065, "as_": 0.015, "I0": 1.0}
    VARS = ["t", "I"]

    @staticmethod
    def dev(p):
        return math.asin(p["n"] * math.sin(p["A"] * DEG)) / DEG - p["A"]

    @staticmethod
    def signal(p, part, th, phi):
        if part < 0.5:
            x = (th - p["inc"]) / p["w"]
            return p["I0"] * math.exp(-x * x)
        if part < 1.5:
            x = (th - W8Mw.dev(p)) / p["w"]
            return p["I0"] * math.exp(-x * x)
        if part < 2.5:
            c = math.cos(phi * DEG)
            return p["I0"] * c * c
        s = math.sin(th * DEG)
        be = PI * p["ds"] * s / p["lam"]
        al = PI * p["as_"] * s / p["lam"]
        env = 1.0 if abs(al) < 1e-12 else math.sin(al) / al
        cb = math.cos(be)
        return p["I0"] * cb * cb * env * env

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": W8Mw.signal(p, p["part"], p["th"], p["phi"])}

    @staticmethod
    def first_max(p, part, lo, hi):
        """The first local maximum of the signal above lo (0.05 degree scan, then a golden refinement)."""
        n = int(round((hi - lo) / 0.05))
        prev2, prev = -1.0, -1.0
        for k in range(n + 1):
            th = lo + 0.05 * k
            v = W8Mw.signal(p, part, th, 0.0)
            if k >= 2 and prev > prev2 and prev >= v:
                c = lo + 0.05 * (k - 1)
                return _golden_max(lambda tt: W8Mw.signal(p, part, tt, 0.0), c - 0.05, c + 0.05, 60)
            prev2, prev = prev, v
        return -1.0

    @staticmethod
    def first_min(p, part, lo, hi):
        """The first local minimum of the signal above lo (0.05 degree scan, then a golden refinement). For the
        double slit it is the first zero of cos^2, which the single-slit envelope cannot move."""
        n = int(round((hi - lo) / 0.05))
        prev2, prev = -1.0, -1.0
        for k in range(n + 1):
            th = lo + 0.05 * k
            v = W8Mw.signal(p, part, th, 0.0)
            if k >= 2 and prev < prev2 and prev <= v:
                c = lo + 0.05 * (k - 1)
                return _golden_max(lambda tt: -W8Mw.signal(p, part, tt, 0.0), c - 0.05, c + 0.05, 60)
            prev2, prev = prev, v
        return -1.0

    @staticmethod
    def measure(p, cfg=None):
        dv = W8Mw.first_max(p, 1.0, 0.0, 70.0)
        th1 = W8Mw.first_min(p, 3.0, 2.0, 60.0)
        rr = W8Mw.first_max(p, 0.0, 0.0, 89.0)
        return {"n": math.sin((p["A"] + dv) * DEG) / math.sin(p["A"] * DEG) if dv >= 0 else 0.0,
                "lam": 2 * p["ds"] * math.sin(th1 * DEG) if th1 > 0 else 0.0, "r": rr,
                "I": W8Mw.signal(p, p["part"], p["th"], p["phi"])}


# ============================================================================================ tables
KERNELS: dict[str, Any] = {"w8_diode": W8Diode, "w8_ion": W8Ion, "w8_thomson": W8Thomson, "w8_mag": W8Magnetron,
                           "w8_focus": W8Focus, "w8_oil": W8Oil, "w8_zeeman": W8Zeeman, "w8_bb": W8BB, "w8_mw": W8Mw}
FAMILY = {"w8_diode": "em", "w8_ion": "em", "w8_thomson": "em", "w8_mag": "em", "w8_focus": "em", "w8_oil": "mech",
          "w8_zeeman": "optics", "w8_bb": "optics", "w8_mw": "optics"}
TEXTBOOK = {
    "w8_phi": lambda p: p["phi"],
    "w8_ui": lambda p: p["Ui"],
    "w8_em": lambda p: p["em"],
    "w8_e19": lambda p: p["e"] * 1e19,
    "w8_h34": lambda p: p["h"] * 1e34,
    "w8_n": lambda p: p["n"],
    "w8_lam": lambda p: p["lam"],
}
CALCS: dict[str, dict] = {
    "w8_c_phi": {"label": "work function", "unit": "eV", "needs": ["invT", "lnIT2"],
                 "fn": lambda rows, p: -_fit(_rows(rows, ["invT", "lnIT2"]))[0] * KB / QE},
    "w8_c_ui": {"label": "ionisation potential", "unit": "V", "needs": ["V", "I"],
                "fn": lambda rows, p: (lambda f: -f[1] / f[0] if f[0] else 0.0)(_fit(_rows(rows, ["V", "I"])))},
    "w8_c_h": {"label": "Planck's constant", "unit": "J s", "needs": ["invT", "lnI"],
               "fn": lambda rows, p: -_fit(_rows(rows, ["invT", "lnI"]))[0] * p["lam"] * KB / C},
    "w8_c_e": {"label": "electronic charge", "unit": "C", "needs": ["q"], "fn": _oil_e},
}
