"""Kernel pack `modern_ug`: the physics of the B.Sc. benches for modern / atomic physics, nuclear and radiation
physics, solid state physics and nanomaterials (see `packs/__init__.py`). Its exact JavaScript twin is
`app/static/prayog/packs/modern_ug.js`; the test suite runs both and demands the same numbers.

Everything here is deterministic: no randomness from the wall clock. A counting experiment draws its Poisson
numbers from a Lehmer generator seeded by the lab's own `seed` parameter, so the same lab always gives the same
counts (and the Python and JavaScript twins give the same counts too).

Physical constants are the 2019 SI defining values (CODATA); every material number lives in a lab or a family
file with its source, never here.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
H = 6.62607015e-34          # Planck constant, exact (SI 2019)
C = 2.99792458e8            # speed of light in vacuum, exact
QE = 1.602176634e-19        # elementary charge, exact
KB = 1.380649e-23           # Boltzmann constant, exact
VT = 0.025852               # kT/e at 300 K, the same constant the other packs use
LN2 = math.log(2.0)


# ------------------------------------------------------------------------------------------------ small helpers
def _clamp(v: float, a: float, b: float) -> float:
    return a if v < a else (b if v > b else v)


def _slope(pts: list[list[float]]) -> float:
    """Least-squares slope of y against x (0.0 when it cannot be formed)."""
    n = len(pts)
    if n < 2:
        return 0.0
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    d = n * sxx - sx * sx
    return 0.0 if d == 0 else (n * sxy - sx * sy) / d


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _rows(rows: list[dict], keys: list[str]) -> list[list[float]]:
    out = []
    for r in rows or []:
        vals = []
        ok = True
        for k in keys:
            v = r.get(k)
            try:
                f = float(v)
            except (TypeError, ValueError):
                ok = False
                break
            if not math.isfinite(f):
                ok = False
                break
            vals.append(f)
        if ok:
            out.append(vals)
    return out


class Rnd:
    """Lehmer (MINSTD) generator: s -> 16807 s mod (2^31 - 1). Every product stays under 2^53, so Python and
    JavaScript walk the same stream exactly."""

    def __init__(self, seed: float) -> None:
        s = int(abs(seed)) % 2147483646
        self.s = s + 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647.0

    def poisson(self, mean: float) -> int:
        """Knuth's product method. A mean above 400 would underflow exp(-mean), so it is split into equal
        parts and the parts added: the sum of independent Poisson numbers is Poisson with the sum of the
        means, so this is exact (and the same rule in both twins)."""
        if mean <= 0:
            return 0
        if mean > 400:
            k = int(mean / 400) + 1
            total = 0
            for _ in range(k):
                total += self.poisson(mean / k)
            return total
        lim = math.exp(-mean)
        k, p = 0, 1.0
        while True:
            p *= self.next()
            if p <= lim:
                return k
            k += 1
            if k > 100000:
                return k


# ============================================================================================ photoelectric effect
class Photocell:
    """A vacuum photocell lit through a filter of wavelength `lam`, with a retarding voltage `Vr` on the anode.

    A photon gives one electron the energy h c / lam; the electron needs the work function `phi` (in electron
    volts) to leave the cathode, so the fastest electrons arrive with (h c / lam) / e - phi volts of energy and
    the current is cut off exactly at that stopping potential Vs. Below cut-off the current falls smoothly
    because only the electrons with enough energy left reach the anode: this lab uses I = Isat (1 - V/Vs)^1.5,
    a smooth cut-off shape that reaches zero AT the stopping potential, which is the quantity the experiment
    measures. The saturation current is proportional to the light power `P` (one electron per photon), which is
    how the lab shows that intensity changes the current but never the stopping potential.

    `lam1..lam5` are the mercury lines the filters pass; the rig reads them and sets `lam` to each in turn."""

    PARAMS = {"lam": 5.461e-7, "phi": 2.14, "Vr": 0.0, "P": 1.0, "Isat0": 1.2e-9, "dark": 2.0e-12,
              "lam1": 3.6502e-7, "lam2": 4.0466e-7, "lam3": 4.3583e-7, "lam4": 5.4607e-7, "lam5": 5.7907e-7}
    VARS = ["t", "I", "I_nA", "V", "Vs", "Isat", "E_ph"]

    @staticmethod
    def stop_v(p: dict) -> float:
        return H * C / (p["lam"] * QE) - p["phi"]

    @staticmethod
    def frac(v: float, vs: float) -> float:
        if vs <= 0:
            return 0.0
        if v <= 0:
            return 1.0
        if v >= vs:
            return 0.0
        return math.pow(1.0 - v / vs, 1.5)

    @staticmethod
    def current(v: float, p: dict) -> float:
        return p["dark"] + p["Isat0"] * max(p["P"], 0.0) * Photocell.frac(v, Photocell.stop_v(p))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        vs = Photocell.stop_v(p)
        return {"t": s.get("t", 0.0), "I": Photocell.current(p["Vr"], p),
                "I_nA": Photocell.current(p["Vr"], p) * 1e9, "V": p["Vr"], "Vs": vs,
                "Isat": p["dark"] + p["Isat0"] * max(p["P"], 0.0), "E_ph": H * C / (p["lam"] * QE)}

    @staticmethod
    def measure(p, cfg=None):
        """The stopping potential read off the simulated curve: the smallest retarding voltage at which the
        photocurrent has fallen to the dark current, found by bisection (never read off the formula)."""
        lo, hi = 0.0, 12.0
        if Photocell.frac(0.0, Photocell.stop_v(p)) <= 0:
            return {"Vs": 0.0, "I": Photocell.current(p["Vr"], p)}
        for _ in range(200):
            mid = (lo + hi) / 2
            if Photocell.frac(mid, Photocell.stop_v(p)) > 0:
                lo = mid
            else:
                hi = mid
        return {"Vs": (lo + hi) / 2, "I": Photocell.current(p["Vr"], p)}


def _photo_vs(p: dict) -> float:
    """Einstein's photoelectric equation: e Vs = h c / lam - e phi."""
    return H * C / (p["lam"] * QE) - p["phi"]


# ============================================================================================ LED band gap (Planck)
class LedGap:
    """A light-emitting diode in series with Rs across a supply Eb. A photon of the LED's peak wavelength costs
    the energy h c / lam, so the junction only conducts once the applied voltage reaches V0 = h c / (e lam).

    The forward current follows the Shockley equation I = Is (e^(V / n V_T) - 1) with the saturation current set
    so that the LED reaches the reference current `Iref` exactly at V0 - which is how a real LED behaves to
    within a few per cent, and what makes the turn-on voltage a measure of the photon energy. The experiment
    measures V0 for LEDs of four or more colours and gets Planck's constant from the slope of V0 against 1/lam.

    `lam1..lam5` are the peak wavelengths of the LEDs in the kit; the rig reads them and sets `lam` to each."""

    PARAMS = {"lam": 6.3e-7, "Iref": 0.001, "nD": 2.0, "Rs": 220.0, "Eb": 3.0,
              "lam1": 6.3e-7, "lam2": 5.9e-7, "lam3": 5.25e-7, "lam4": 4.7e-7, "lam5": 4.05e-7}
    VARS = ["t", "V", "I", "V0", "lam_nm"]

    @staticmethod
    def gap_v(p: dict) -> float:
        return H * C / (QE * p["lam"])

    @staticmethod
    def i_sat(p: dict) -> float:
        return p["Iref"] * math.exp(-LedGap.gap_v(p) / (p["nD"] * VT))

    @staticmethod
    def current(v: float, p: dict) -> float:
        return LedGap.i_sat(p) * (math.exp(min(v / (p["nD"] * VT), 90.0)) - 1.0)

    @staticmethod
    def solve(p: dict) -> float:
        """Eb = I Rs + V, by bisection on V (the current rises with V)."""
        lo, hi = 0.0, max(p["Eb"], 0.0)
        for _ in range(200):
            mid = (lo + hi) / 2
            if mid + LedGap.current(mid, p) * p["Rs"] > p["Eb"]:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    @staticmethod
    def turn_on(p: dict) -> float:
        """The turn-on voltage: the forward voltage at which the current reaches Iref, by bisection."""
        lo, hi = 0.0, 10.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if LedGap.current(mid, p) < p["Iref"]:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        v = LedGap.solve(p)
        return {"t": s.get("t", 0.0), "V": v, "I": LedGap.current(v, p), "V0": LedGap.turn_on(p),
                "lam_nm": p["lam"] * 1e9}

    @staticmethod
    def measure(p, cfg=None):
        v = LedGap.solve(p)
        return {"V0": LedGap.turn_on(p), "V": v, "I": LedGap.current(v, p)}


def _led_v0(p: dict) -> float:
    """e V0 = h c / lam: the photon energy of the light the LED gives out."""
    return H * C / (QE * p["lam"])


# ============================================================================================ Franck-Hertz tube
class FranckHertz:
    """A Franck-Hertz tube: electrons are accelerated through a vapour by the grid voltage `Vg` and collected
    after a small retarding voltage. Whenever an electron has gained the first excitation energy `Ue` of the
    atom it can lose all of it in one inelastic collision, so the collector current rises and falls with a
    period of exactly Ue volts.

    The current is modelled as a steeply rising envelope times a periodic term,
        I = Ioff + Iscale e^((V - Vmid)/V0) (1 + damp cos(2 pi (V - Vc) / Ue)) / (1 + damp),
    with `Vc` the contact potential. Because the envelope is exponential, the stationary points of that product
    depend on (V - Vc) only through its remainder modulo Ue, so the peaks are EXACTLY Ue volts apart however
    steeply the envelope rises - which is the quantity the experiment measures."""

    PARAMS = {"Vg": 0.0, "Ue": 4.9, "Vc": 1.5, "V0": 7.0, "Vmid": 20.0, "damp": 0.85,
              "Iscale": 1.0e-9, "Ioff": 1.0e-11, "Vmax": 32.0, "Vt": 2.5}
    VARS = ["t", "I", "I_nA", "V", "n_peaks"]

    @staticmethod
    def current(v: float, p: dict) -> float:
        """`Vt` is the voltage below which no electron reaches the collector at all (it cannot climb the
        retarding voltage), so the curve starts from nothing instead of showing a bump at the contact
        potential. The factor is exponential, so it has died away long before the first peak and does not
        move it."""
        if v < 0:
            v = 0.0
        if v <= p["Vt"]:
            return p["Ioff"]
        on = 1.0 - math.exp(-(v - p["Vt"]) / 0.5)
        env = math.exp(_clamp((v - p["Vmid"]) / max(p["V0"], 1e-9), -60.0, 60.0))
        per = 1.0 + p["damp"] * math.cos(2 * PI * (v - p["Vc"]) / max(p["Ue"], 1e-9))
        return p["Ioff"] + p["Iscale"] * on * env * per / (1.0 + p["damp"])

    @staticmethod
    def peaks(p: dict) -> list[float]:
        """Every current maximum inside 0 .. Vmax, each found by a ternary search in its own period window."""
        out: list[float] = []
        ue = max(p["Ue"], 1e-9)
        n = 1
        while True:
            centre = p["Vc"] + n * ue
            lo, hi = centre - ue / 2, centre + ue / 2
            if lo < 0.5:
                n += 1
                if centre > p["Vmax"]:
                    break
                continue
            if hi > p["Vmax"]:
                break
            for _ in range(200):
                a1 = lo + (hi - lo) / 3
                a2 = hi - (hi - lo) / 3
                if FranckHertz.current(a1, p) < FranckHertz.current(a2, p):
                    lo = a1
                else:
                    hi = a2
            out.append((lo + hi) / 2)
            n += 1
        return out

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": FranckHertz.current(p["Vg"], p),
                "I_nA": FranckHertz.current(p["Vg"], p) * 1e9, "V": p["Vg"],
                "n_peaks": float(len(FranckHertz.peaks(p)))}

    @staticmethod
    def measure(p, cfg=None):
        pk = FranckHertz.peaks(p)
        pts = [[float(i + 1), v] for i, v in enumerate(pk)]
        return {"spacing": _slope(pts), "n_peaks": float(len(pk)),
                "V1": pk[0] if pk else 0.0, "I": FranckHertz.current(p["Vg"], p)}


def _fh_spacing(p: dict) -> float:
    """The peaks of a Franck-Hertz curve are one excitation potential apart."""
    return p["Ue"]


# ============================================================================================ grating spectrometer
class Grating:
    """A plane transmission grating of `Nl` rulings per metre in a spectrometer, lit by a hydrogen discharge
    tube. The Balmer line from level `nq` down to level `nl` has 1 / lam = Rh (1/nl^2 - 1/nq^2), and the grating
    sends it out at the angle sin(theta) = order lam Nl. The experiment reads theta on the spectrometer circle
    for each line and works the Rydberg constant back out of it."""

    PARAMS = {"Nl": 600000.0, "order": 1.0, "nq": 3.0, "nl": 2.0, "Rh": 10967758.3}
    VARS = ["t", "lam", "theta", "lam_nm"]

    @staticmethod
    def wavelength(p: dict) -> float:
        inv = p["Rh"] * (1.0 / (p["nl"] * p["nl"]) - 1.0 / (p["nq"] * p["nq"]))
        return 1.0 / inv if inv > 0 else 0.0

    @staticmethod
    def angle(p: dict) -> float:
        s = Grating.wavelength(p) * p["order"] * p["Nl"]
        return math.asin(s) if -1.0 <= s <= 1.0 else 0.0

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        lam = Grating.wavelength(p)
        return {"t": s.get("t", 0.0), "lam": lam, "theta": Grating.angle(p), "lam_nm": lam * 1e9}

    @staticmethod
    def measure(p, cfg=None):
        """The wavelength as the STUDENT gets it: from the simulated diffraction angle through the grating
        equation lam = sin(theta) / (order Nl)."""
        th = Grating.angle(p)
        lam = math.sin(th) / (p["order"] * p["Nl"]) if p["order"] * p["Nl"] != 0 else 0.0
        return {"lam": lam, "theta": th}


def _balmer_lam(p: dict) -> float:
    """Balmer's formula with the Rydberg constant of hydrogen: 1 / lam = Rh (1/nl^2 - 1/nq^2)."""
    return 1.0 / (p["Rh"] * (1.0 / (p["nl"] * p["nl"]) - 1.0 / (p["nq"] * p["nq"])))


# ============================================================================================ GM counter (plateau)
class GmTube:
    """A Geiger-Muller tube with a sealed source in front of it, on a counter with a timer.

    Below the starting voltage `Vs` the tube does not count at all; above it the count rate climbs steeply and
    then flattens into the plateau, which rises only a few per cent per 100 V (`slope`); past `Vp` the tube goes
    into continuous discharge and the rate runs away. Every count takes the tube `tau` seconds of dead time, so
    the observed rate is N / (1 + N tau) and the true rate comes back as Nobs / (1 - Nobs tau).

    The counts themselves are Poisson numbers drawn from the lab's own `seed`, so a run of `nrep` counts of
    `t` seconds each is the same every time the lab is opened - but still scatters about the mean the way real
    counts do, which is what the counting-statistics experiment measures."""

    PARAMS = {"V": 450.0, "Vs": 330.0, "Vp": 650.0, "slope": 0.03, "rise": 25.0, "N0": 60.0, "bg": 0.5,
              "tau": 2.5e-4, "t": 10.0, "nrep": 50.0, "seed": 7.0}
    VARS = ["t", "rate", "rate_true", "counts", "V"]

    @staticmethod
    def plateau(p: dict) -> float:
        v = p["V"]
        if v <= p["Vs"]:
            return 0.0
        f = (1.0 - math.exp(-(v - p["Vs"]) / max(p["rise"], 1e-9))) * (1.0 + p["slope"] * (v - p["Vs"]) / 100.0)
        if v > p["Vp"]:
            d = (v - p["Vp"]) / 40.0
            f *= 1.0 + d * d
        return f

    @staticmethod
    def true_rate(p: dict) -> float:
        return (p["N0"] + p["bg"]) * GmTube.plateau(p)

    @staticmethod
    def obs_rate(p: dict) -> float:
        r = GmTube.true_rate(p)
        return r / (1.0 + r * p["tau"])

    @staticmethod
    def counts(p: dict, n: int) -> list[int]:
        """`n` successive counts of `t` seconds, from the lab's seed."""
        rnd = Rnd(p["seed"])
        mean = GmTube.obs_rate(p) * max(p["t"], 0.0)
        return [rnd.poisson(mean) for _ in range(max(0, n))]

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "rate": GmTube.obs_rate(p), "rate_true": GmTube.true_rate(p),
                "counts": GmTube.obs_rate(p) * p["t"], "V": p["V"]}

    @staticmethod
    def measure(p, cfg=None):
        """What the student works out: the dead-time corrected rate from the observed one."""
        obs = GmTube.obs_rate(p)
        cs = GmTube.counts(p, int(p["nrep"]))
        mean = _mean([float(c) for c in cs])
        var = _mean([(c - mean) ** 2 for c in cs]) * (len(cs) / (len(cs) - 1.0)) if len(cs) > 1 else 0.0
        return {"rate": obs, "rate_corr": obs / (1.0 - obs * p["tau"]), "mean_counts": mean,
                "sd_counts": math.sqrt(var), "ratio": math.sqrt(var) / math.sqrt(mean) if mean > 0 else 0.0}


def _gm_true_rate(p: dict) -> float:
    """The tube's own counting curve, written out: nothing counts below the starting voltage, the plateau rises
    `slope` per 100 V, and past Vp the tube goes into continuous discharge."""
    v = p["V"]
    if v <= p["Vs"]:
        return 0.0
    f = (1.0 - math.exp((p["Vs"] - v) / p["rise"])) * (1.0 + p["slope"] * (v - p["Vs"]) / 100.0)
    if v > p["Vp"]:
        f = f * (1.0 + ((v - p["Vp"]) / 40.0) ** 2)
    return (p["N0"] + p["bg"]) * f


# ============================================================================================ absorption of gamma rays
class GmAbsorb:
    """A sealed gamma source, a stack of absorber sheets of total thickness `x`, and a GM tube at a fixed
    distance. The narrow-beam attenuation law says the rate falls as exp(-mu x) above the background `bg`, so
    the half-value thickness is ln 2 / mu. Counts are Poisson numbers from the lab's own seed."""

    PARAMS = {"x": 0.0, "mu": 20.14, "N0": 80.0, "bg": 0.5, "tau": 2.5e-4, "t": 60.0, "seed": 11.0}
    VARS = ["t", "rate", "net", "x_mm"]

    @staticmethod
    def true_rate(p: dict) -> float:
        return p["bg"] + p["N0"] * math.exp(-p["mu"] * max(p["x"], 0.0))

    @staticmethod
    def obs_rate(p: dict) -> float:
        r = GmAbsorb.true_rate(p)
        return r / (1.0 + r * p["tau"])

    @staticmethod
    def counts(p: dict, k: int = 0) -> int:
        rnd = Rnd(p["seed"] + 977.0 * k)
        return rnd.poisson(GmAbsorb.obs_rate(p) * max(p["t"], 0.0))

    @staticmethod
    def half_thickness(p: dict) -> float:
        """The thickness at which the NET rate falls to half its unshielded value, by bisection on the
        simulated rate (never read off the formula)."""
        n0 = GmAbsorb.true_rate({**p, "x": 0.0}) - p["bg"]
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if GmAbsorb.true_rate({**p, "x": mid}) - p["bg"] > n0 / 2:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "rate": GmAbsorb.obs_rate(p),
                "net": GmAbsorb.obs_rate(p) - p["bg"], "x_mm": p["x"] * 1000.0}

    @staticmethod
    def measure(p, cfg=None):
        return {"rate": GmAbsorb.obs_rate(p), "x_half": GmAbsorb.half_thickness(p),
                "net": GmAbsorb.obs_rate(p) - p["bg"]}


def _gm_hvl(p: dict) -> float:
    """Half-value thickness of the attenuation law: x_half = ln 2 / mu."""
    return LN2 / p["mu"]


# ============================================================================================ half-life of a source
class GmDecay:
    """A short-lived source in front of a GM tube. Its activity falls as exp(-ln2 t / T), so the net count rate
    above the background halves every half-life T. Counts are Poisson numbers from the lab's own seed."""

    PARAMS = {"t": 0.0, "T": 3257.4, "N0": 120.0, "bg": 0.5, "tau": 2.5e-4, "tc": 60.0, "seed": 13.0}
    VARS = ["t", "rate", "net", "frac"]

    @staticmethod
    def true_rate(p: dict) -> float:
        return p["bg"] + p["N0"] * math.exp(-LN2 * max(p["t"], 0.0) / max(p["T"], 1e-9))

    @staticmethod
    def obs_rate(p: dict) -> float:
        r = GmDecay.true_rate(p)
        return r / (1.0 + r * p["tau"])

    @staticmethod
    def counts(p: dict, k: int = 0) -> int:
        rnd = Rnd(p["seed"] + 977.0 * k)
        return rnd.poisson(GmDecay.obs_rate(p) * max(p["tc"], 0.0))

    @staticmethod
    def half_time(p: dict) -> float:
        """The time at which the NET rate has fallen to half, by bisection on the simulated decay."""
        lo, hi = 0.0, max(p["T"], 1e-9) * 20.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if GmDecay.true_rate({**p, "t": mid}) - p["bg"] > p["N0"] / 2:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        q = {**p, "t": p["t"] + s.get("t", 0.0)}
        return {"t": s.get("t", 0.0), "rate": GmDecay.obs_rate(q), "net": GmDecay.obs_rate(q) - p["bg"],
                "frac": math.exp(-LN2 * max(q["t"], 0.0) / max(p["T"], 1e-9))}

    @staticmethod
    def measure(p, cfg=None):
        return {"t_half": GmDecay.half_time(p), "rate": GmDecay.obs_rate(p),
                "net": GmDecay.obs_rate(p) - p["bg"]}


def _decay_T(p: dict) -> float:
    """The half-life itself: the net rate halves in T seconds."""
    return p["T"]


# ============================================================================================ four-probe resistivity
class FourProbe:
    """A semiconductor slice of thickness `w` in an oven, with four equally spaced probes a distance `s` apart.
    A constant current `I` goes through the outer probes and the voltage `V` is read between the inner two.

    For a slice much thinner than the probe spacing the geometry correction G7(w/s) = (2 s / w) ln 2 turns the
    infinite-medium result rho0 = 2 pi s (V / I) into rho = rho0 / G7 = pi w V / (ln 2 I). In an intrinsic
    semiconductor the carrier number goes as exp(-Eg / 2 k T), so the resistivity follows
    rho = rho300 exp((Eg e / 2k)(1/T - 1/300)); the slope of ln rho against 1/T gives the band gap."""

    PARAMS = {"T": 300.0, "Eg": 0.67, "rho300": 0.46, "I": 0.002, "s": 0.002, "w": 0.0005}
    VARS = ["t", "V", "rho", "T", "lnrho"]

    @staticmethod
    def rho(p: dict) -> float:
        return p["rho300"] * math.exp(p["Eg"] * QE / (2 * KB) * (1.0 / max(p["T"], 1e-9) - 1.0 / 300.0))

    @staticmethod
    def probe_v(p: dict) -> float:
        return p["I"] * FourProbe.rho(p) * LN2 / (PI * p["w"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        v = FourProbe.probe_v(p)
        return {"t": s.get("t", 0.0), "V": v, "rho": FourProbe.rho(p), "T": p["T"],
                "lnrho": math.log(max(FourProbe.rho(p), 1e-300))}

    @staticmethod
    def measure(p, cfg=None):
        """The resistivity as the student gets it: from the probe voltage through the four-probe formula."""
        v = FourProbe.probe_v(p)
        return {"V": v, "rho": PI * p["w"] * v / (LN2 * p["I"]), "T": p["T"]}


def _fourprobe_rho(p: dict) -> float:
    """Intrinsic resistivity against temperature: rho = rho300 exp((Eg e / 2k)(1/T - 1/300))."""
    return p["rho300"] * math.exp(p["Eg"] * QE / (2 * KB) * (1.0 / p["T"] - 1.0 / 300.0))


# ============================================================================================ Hall effect
class HallBar:
    """A thin semiconductor bar of thickness `th` carrying a current `I` across a magnetic field `B`. The
    carriers are pushed to one face until the transverse field balances the magnetic force, so the Hall voltage
    is VH = sg I B / (n e th), where `n` is the carrier number per cubic metre and `sg` is +1 for holes and -1
    for electrons. The Hall coefficient RH = VH th / (I B) = sg / (n e), and with the measured conductivity it
    gives the mobility mu = |RH| / rho.

    `n21` is that carrier number in units of 10^21 per cubic metre: a lab parameter has to stay inside the Lab
    Scene Language's numeric range, and 10^21 per cubic metre is the natural unit for a doped semiconductor."""

    PARAMS = {"B": 0.2, "I": 0.005, "th": 0.0005, "n21": 2.0, "sg": -1.0, "rho": 0.02, "wid": 0.004}
    VARS = ["t", "Vh", "RH", "B", "I"]

    @staticmethod
    def hall_v(p: dict) -> float:
        return p["sg"] * p["I"] * p["B"] / (p["n21"] * 1e21 * QE * p["th"])

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        vh = HallBar.hall_v(p)
        rh = vh * p["th"] / (p["I"] * p["B"]) if p["I"] * p["B"] != 0 else 0.0
        return {"t": s.get("t", 0.0), "Vh": vh, "RH": rh, "B": p["B"], "I": p["I"]}

    @staticmethod
    def measure(p, cfg=None):
        vh = HallBar.hall_v(p)
        rh = vh * p["th"] / (p["I"] * p["B"]) if p["I"] * p["B"] != 0 else 0.0
        return {"Vh": vh, "RH": rh, "mu": abs(rh) / p["rho"] if p["rho"] > 0 else 0.0}


def _hall_vh(p: dict) -> float:
    """VH = I B / (n e t), with the sign of the carrier (n = n21 x 10^21 per cubic metre)."""
    return p["sg"] * p["I"] * p["B"] / (p["n21"] * 1e21 * QE * p["th"])


# ============================================================================================ UV-visible spectrum of a colloid
class Colloid:
    """A gold colloid in a 1 cm cuvette in a UV-visible spectrophotometer. Small gold spheres have a surface
    plasmon absorption band in the green, and both its position and its height above the 450 nm absorbance grow
    with the particle diameter. This lab follows the published empirical relations of Haiss et al. (2007):

        lam_spr = 512 + 6.53 exp(0.0216 d)      (d in nm)
        d = exp(3.00 (A_spr / A_450) - 2.20)

    The modelled spectrum is a Lorentzian plasmon band of width `wid` on an interband background that decays to
    the red, and its two free heights are fixed so that A(450) and A(lam_spr) are exactly what those relations
    demand. The experiment reads the two absorbances off the recorded spectrum and gets the diameter back.
    The method is only as good as the relations themselves: they were fitted for spherical citrate-capped gold
    between about 5 and 100 nm, and say nothing about silver or about rods."""

    PARAMS = {"d": 20.0, "conc": 1.0, "lam": 5.2e-7, "A450": 0.5, "wid": 60.0, "bgdecay": 120.0}
    VARS = ["t", "A", "lam_nm", "lam_spr", "A_spr"]
    B1 = 3.00
    B2 = 2.20

    @staticmethod
    def lam_spr(p: dict) -> float:
        return 512.0 + 6.53 * math.exp(0.0216 * p["d"])

    @staticmethod
    def ratio(p: dict) -> float:
        return (math.log(max(p["d"], 1e-6)) + Colloid.B2) / Colloid.B1

    @staticmethod
    def _coef(p: dict) -> tuple[float, float]:
        """The Lorentzian and background heights that give A(450) and A(lam_spr) their required values."""
        ls = Colloid.lam_spr(p)
        a450 = p["A450"] * max(p["conc"], 0.0)
        aspr = Colloid.ratio(p) * a450
        hw = max(p["wid"], 1e-6) / 2
        l450 = 1.0 / (1.0 + ((450.0 - ls) / hw) ** 2)          # Lorentzian at 450 nm
        bspr = math.exp(-(ls - 450.0) / max(p["bgdecay"], 1e-6))  # background at the peak
        det = l450 * bspr - 1.0
        if abs(det) < 1e-12:
            return 0.0, a450
        a = (a450 * bspr - aspr) / det
        b = (aspr * l450 - a450) / det
        return a, b

    @staticmethod
    def absorbance(lam_nm: float, p: dict) -> float:
        a, b = Colloid._coef(p)
        ls = Colloid.lam_spr(p)
        hw = max(p["wid"], 1e-6) / 2
        lor = 1.0 / (1.0 + ((lam_nm - ls) / hw) ** 2)
        bg = math.exp(-(lam_nm - 450.0) / max(p["bgdecay"], 1e-6))
        return a * lor + b * bg

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "A": Colloid.absorbance(p["lam"] * 1e9, p), "lam_nm": p["lam"] * 1e9,
                "lam_spr": Colloid.lam_spr(p), "A_spr": Colloid.absorbance(Colloid.lam_spr(p), p)}

    @staticmethod
    def peak_nm(p: dict) -> float:
        """The band maximum found on the modelled spectrum itself, by a ternary search between 450 and 750 nm."""
        lo, hi = 450.0, 750.0
        for _ in range(200):
            a1 = lo + (hi - lo) / 3
            a2 = hi - (hi - lo) / 3
            if Colloid.absorbance(a1, p) < Colloid.absorbance(a2, p):
                lo = a1
            else:
                hi = a2
        return (lo + hi) / 2

    @staticmethod
    def measure(p, cfg=None):
        """The diameter as the student gets it: the two absorbances read off the spectrum, put into Haiss's
        relation."""
        ls = Colloid.lam_spr(p)
        a450 = Colloid.absorbance(450.0, p)
        aspr = Colloid.absorbance(ls, p)
        d = math.exp(Colloid.B1 * (aspr / a450) - Colloid.B2) if a450 > 0 else 0.0
        return {"d_est": d, "A450": a450, "A_spr": aspr, "lam_spr": ls, "peak_nm": Colloid.peak_nm(p)}


def _colloid_d(p: dict) -> float:
    """The diameter the colloid really has in this lab."""
    return p["d"]


# ============================================================================================ tables
KERNELS: dict[str, Any] = {"photocell": Photocell, "ledgap": LedGap, "fhtube": FranckHertz, "grating": Grating,
                           "gmtube": GmTube, "gmabsorb": GmAbsorb, "gmdecay": GmDecay, "fourprobe": FourProbe,
                           "hallbar": HallBar, "colloid": Colloid}
FAMILY = {"photocell": "em", "ledgap": "circuit", "fhtube": "em", "grating": "optics", "gmtube": "em",
          "gmabsorb": "em", "gmdecay": "em", "fourprobe": "em", "hallbar": "em", "colloid": "optics"}
TEXTBOOK = {
    "photo_Vs": _photo_vs,
    "led_V0": _led_v0,
    "fh_spacing": _fh_spacing,
    "balmer_lam": _balmer_lam,
    "gm_true_rate": _gm_true_rate,
    "gm_hvl": _gm_hvl,
    "decay_T": _decay_T,
    "fourprobe_rho": _fourprobe_rho,
    "hall_vh": _hall_vh,
    "colloid_d": _colloid_d,
}
CALCS: dict[str, dict] = {
    "photo_h": {"label": "h (Planck)", "unit": "J·s", "needs": ["f", "Vs"],
                "fn": lambda rows, p: QE * _slope(_rows(rows, ["f", "Vs"]))},
    "led_h": {"label": "h (Planck)", "unit": "J·s", "needs": ["f", "V0"],
              "fn": lambda rows, p: QE * _slope(_rows(rows, ["f", "V0"]))},
    "fh_Ue": {"label": "first excitation potential", "unit": "V", "needs": ["n", "Vp"],
              "fn": lambda rows, p: _slope(_rows(rows, ["n", "Vp"]))},
    "balmer_R": {"label": "Rydberg constant", "unit": "1/m", "needs": ["nq", "lam"],
                 "fn": lambda rows, p: _mean([1.0 / (lam * (1.0 / (p["nl"] * p["nl"]) - 1.0 / (nq * nq)))
                                              for nq, lam in _rows(rows, ["nq", "lam"])
                                              if lam > 0 and nq * nq != p["nl"] * p["nl"]])},
    "gm_mu": {"label": "attenuation coefficient", "unit": "1/m", "needs": ["x", "net"],
              "fn": lambda rows, p: -_slope([[x, math.log(net)] for x, net in _rows(rows, ["x", "net"]) if net > 0])},
    "decay_half": {"label": "half-life", "unit": "s", "needs": ["t", "net"],
                   "fn": lambda rows, p: (lambda m: LN2 / -m if m < 0 else 0.0)(
                       _slope([[t, math.log(net)] for t, net in _rows(rows, ["t", "net"]) if net > 0]))},
    "bandgap_Eg": {"label": "band gap", "unit": "eV", "needs": ["invT", "lnrho"],
                   "fn": lambda rows, p: 2 * KB * _slope(_rows(rows, ["invT", "lnrho"])) / QE},
    "hall_RH": {"label": "Hall coefficient", "unit": "m³/C", "needs": ["B", "Vh"],
                "fn": lambda rows, p: _mean([vh * p["th"] / (p["I"] * b) for b, vh in _rows(rows, ["B", "Vh"])
                                             if b != 0 and p["I"] != 0])},
    "nano_d": {"label": "particle diameter", "unit": "nm", "needs": ["A450", "Aspr"],
               "fn": lambda rows, p: _mean([math.exp(Colloid.B1 * (asp / a4) - Colloid.B2)
                                            for a4, asp in _rows(rows, ["A450", "Aspr"]) if a4 > 0])},
}
