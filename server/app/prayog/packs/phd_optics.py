"""Kernel pack `phd_optics`: Ph.D. laser spectroscopy, interferometry, photon statistics, signal recovery and plasma
diagnostics (see `packs/__init__.py`). Its exact JavaScript twin is `app/static/prayog/packs/phd_optics.js`; the test
suite runs both and demands the same numbers.

Everything here is deterministic. Every noisy or counting process is drawn from a Lehmer generator (as in
`modern_ug.py`) seeded by the lab's own `seed` parameter, never by the clock, so a lab always gives the same noise and
the Python and JavaScript twins give the same noise too. A quantity the student measures is FOUND on the simulated
response (a lock-in average, a variance, a fit, a numerical search); the textbook relation it should agree with is
written separately in TEXTBOOK and is never used by the simulation to hand the answer back.

Physical constants are the 2019 SI defining values (CODATA); a constant from CODATA 2018 is named as such. Every
other number that is not a definition lives in a lab or a family file with its source, or is labelled illustrative.
"""
from __future__ import annotations

import math
from typing import Any

PI = math.pi
H = 6.62607015e-34          # Planck constant, exact (SI 2019)
C = 2.99792458e8            # speed of light in vacuum, exact
QE = 1.602176634e-19        # elementary charge, exact
KB = 1.380649e-23           # Boltzmann constant, exact
ME = 9.1093837015e-31       # electron mass, CODATA 2018
AMU = 1.66053906660e-27     # atomic mass unit, CODATA 2018


# ------------------------------------------------------------------------------------------------ helpers
def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _slope(xs: list[float], ys: list[float]) -> list[float]:
    """Least-squares line y = a + b x -> [a, b]. [0, 0] when it cannot be formed."""
    n = len(xs)
    if n < 2:
        return [0.0, 0.0]
    sx = sy = sxy = sxx = 0.0
    for i in range(n):
        sx += xs[i]
        sy += ys[i]
        sxy += xs[i] * ys[i]
        sxx += xs[i] * xs[i]
    d = n * sxx - sx * sx
    if d == 0:
        return [0.0, 0.0]
    b = (n * sxy - sx * sy) / d
    return [(sy - b * sx) / n, b]


class Rnd:
    """Lehmer (MINSTD) generator: s -> 16807 s mod (2^31 - 1). Every product stays under 2^53, so Python and
    JavaScript walk the same stream exactly. `gauss` is Box-Muller on that stream."""

    def __init__(self, seed: float) -> None:
        s = int(abs(seed)) % 2147483646
        self.s = s + 1
        self.has = False
        self.z1 = 0.0

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647.0

    def gauss(self) -> float:
        if self.has:
            self.has = False
            return self.z1
        u1 = self.next()
        u2 = self.next()
        r = math.sqrt(-2.0 * math.log(u1))
        self.z1 = r * math.sin(2.0 * PI * u2)
        self.has = True
        return r * math.cos(2.0 * PI * u2)

    def poisson(self, mean: float) -> int:
        """Knuth's product method below 400; above that the Poisson number is a Gaussian of the same mean and
        variance (accurate to a few parts in a thousand of the standard deviation and exact in the limit)."""
        if mean <= 0:
            return 0
        if mean >= 400.0:
            v = math.floor(mean + math.sqrt(mean) * self.gauss() + 0.5)
            return int(v) if v > 0 else 0
        lim = math.exp(-mean)
        k, p = 0, 1.0
        while True:
            p *= self.next()
            if p <= lim:
                return k
            k += 1
            if k > 100000:
                return k


def fft(re: list[float], im: list[float], inverse: bool = False) -> None:
    """In-place radix-2 FFT (length a power of two). The inverse is NOT divided by n."""
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
    length = 2
    sgn = 1.0 if inverse else -1.0
    while length <= n:
        ang = sgn * 2.0 * PI / length
        half = length // 2
        wr = [math.cos(ang * k) for k in range(half)]
        wi = [math.sin(ang * k) for k in range(half)]
        for s in range(0, n, length):
            for k in range(half):
                a = s + k
                b = a + half
                tr = re[b] * wr[k] - im[b] * wi[k]
                ti = re[b] * wi[k] + im[b] * wr[k]
                re[b] = re[a] - tr
                im[b] = im[a] - ti
                re[a] += tr
                im[a] += ti
        length *= 2


class _Base:
    """Shared plumbing: a small clock so view() has something to move with; the physics is in the statics."""

    PARAMS: dict[str, float] = {}
    VARS: list[str] = ["t"]

    @classmethod
    def init(cls, p, cfg=None):
        return {"t": 0.0}

    @classmethod
    def step(cls, s, p, dt, cfg=None):
        s["t"] = s.get("t", 0.0) + dt


# ============================================================================================ lock-in amplifier
class PhdLockin(_Base):
    """A lock-in amplifier recovering a small chopped signal A cos(2 pi f t + phi) from broadband noise `en`
    (V/sqrt(Hz)). The input is multiplied by the reference 2 cos(2 pi f t + phr) and by -2 sin(...), each product
    goes through a single-pole RC low-pass of time constant `tc`, and the display shows the output averaged over
    the last 4 tc after 8 tc of settling. So X = A cos(phi - phr), Y = A sin(phi - phr), R = sqrt(X^2 + Y^2) = A,
    theta = phi - phr. The noise is white Gaussian, drawn from the lab's seed; ten samples per period."""

    PARAMS = {"A": 2.0e-5, "f": 137.0, "phi": 35.0, "en": 3.0e-7, "tc": 3.0, "phr": 0.0, "dual": 1.0, "seed": 5.0}
    VARS = ["t", "X", "Y", "R", "theta", "sigma"]

    @staticmethod
    def read(p: dict, tc: float, phr: float, k: float) -> list[float]:
        """One display reading [X, Y] with reference phase `phr` (degrees) and time constant `tc`; `k` numbers the
        reading so that every reading has its own noise."""
        f = p["f"]
        dt = 1.0 / (10.0 * f)
        nset = int(8.0 * tc / dt)
        navg = int(4.0 * tc / dt)
        alpha = 1.0 - math.exp(-dt / tc)
        rnd = Rnd(p["seed"] + 101.0 * k)
        srms = p["en"] * math.sqrt(10.0 * f / 2.0)
        w = 2.0 * PI * f
        ph = p["phi"] * PI / 180.0
        pr = phr * PI / 180.0
        x = y = sx = sy = 0.0
        for n in range(nset + navg):
            t = n * dt
            v = p["A"] * math.cos(w * t + ph) + srms * rnd.gauss()
            x += alpha * (2.0 * v * math.cos(w * t + pr) - x)
            y += alpha * (-2.0 * v * math.sin(w * t + pr) - y)
            if n >= nset:
                sx += x
                sy += y
        return [sx / navg, sy / navg]

    @staticmethod
    def sigma(p: dict, tc: float) -> float:
        """Expected scatter of one display reading (V): en / (2 sqrt(tc)) after the 4 tc average."""
        return p["en"] / (2.0 * math.sqrt(tc))

    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt

    @staticmethod
    def view(s, p, cfg=None):
        d = (p["phi"] - p["phr"]) * PI / 180.0
        return {"t": s.get("t", 0.0), "X": p["A"] * math.cos(d), "Y": p["A"] * math.sin(d), "R": p["A"],
                "theta": p["phi"] - p["phr"], "sigma": PhdLockin.sigma(p, p["tc"])}

    @staticmethod
    def measure(p, cfg=None):
        if p["dual"] >= 0.5:
            xy = PhdLockin.read(p, p["tc"], p["phr"], 0.0)
            return {"R": math.sqrt(xy[0] ** 2 + xy[1] ** 2), "theta": math.atan2(xy[1], xy[0]) * 180.0 / PI + p["phr"],
                    "X": xy[0], "Y": xy[1]}
        a = b = 0.0
        for j in range(6):                               # single phase: turn the reference round in 60 degree steps
            ph = 60.0 * j
            xj = PhdLockin.read(p, p["tc"], ph, float(j))[0]
            a += xj * math.cos(ph * PI / 180.0) / 3.0
            b += xj * math.sin(ph * PI / 180.0) / 3.0
        return {"R": math.sqrt(a * a + b * b), "theta": -math.atan2(b, a) * 180.0 / PI, "X": a, "Y": b}


def _lockin_A(p: dict) -> float:
    return p["A"]


# ============================================================================================ Johnson noise
class PhdJohnson(_Base):
    """Thermal (Johnson-Nyquist) noise of a resistor R at temperature T, read through an amplifier of voltage gain
    `G`, input noise `en` (V/sqrt(Hz)) and noise bandwidth `df`. The mean-square output is
    G^2 df (4 kB T R + en^2). `n` Gaussian samples (a bandwidth df gives 2 df independent samples a second) are
    drawn from the seed and their mean square is the reading, so the readings carry the sqrt(2/n) scatter of a
    real measurement. The student reads the mean square for several resistors and a shorted input."""

    PARAMS = {"T": 300.0, "df": 10000.0, "G": 1000.0, "en": 2.0e-9, "n": 100000.0, "seed": 3.0, "R": 10000.0}
    VARS = ["t", "v2", "vrms", "vn_th"]
    RS = [0.0, 1.0e3, 2.0e3, 5.0e3, 1.0e4, 2.0e4, 5.0e4, 1.0e5]

    @staticmethod
    def v2_true(p: dict, r: float) -> float:
        return p["G"] ** 2 * p["df"] * (4.0 * KB * p["T"] * r + p["en"] ** 2)

    @staticmethod
    def msq(p: dict, r: float, k: float) -> float:
        """Mean square of n samples, the reading of one measurement with the input resistor `r`."""
        rnd = Rnd(p["seed"] + 977.0 * k)
        sd = math.sqrt(PhdJohnson.v2_true(p, r))
        n = int(p["n"])
        s = 0.0
        for _ in range(n):
            v = sd * rnd.gauss()
            s += v * v
        return s / n

    @staticmethod
    def view(s, p, cfg=None):
        v2 = PhdJohnson.v2_true(p, p["R"])
        return {"t": s.get("t", 0.0), "v2": v2, "vrms": math.sqrt(v2), "vn_th": math.sqrt(4.0 * KB * p["T"] * p["R"] * p["df"])}

    @staticmethod
    def measure(p, cfg=None):
        xs, ys = [], []
        for i, r in enumerate(PhdJohnson.RS):
            xs.append(r)
            ys.append(PhdJohnson.msq(p, r, float(i)))
        ab = _slope(xs, ys)
        e2 = ab[0] / (p["G"] ** 2 * p["df"])
        kb = ab[1] / (4.0 * p["T"] * p["df"] * p["G"] ** 2)
        return {"kB": kb, "kB23": kb * 1.0e23, "en": math.sqrt(e2) if e2 > 0 else 0.0}


def _kb(p: dict) -> float:
    return KB * 1.0e23                       # in units of 1e-23 J/K, so the checker's relative error is meaningful


# ============================================================================================ shot noise
class PhdShot(_Base):
    """Shot noise of a photocurrent I read through a transimpedance amplifier Rf. The current noise density is
    2 q I + 4 kB T / Rf (shot plus the feedback resistor's Johnson noise), so the mean-square output voltage is
    Rf^2 df (2 q I + 4 kB T / Rf). `Iscale` scales the seven currents the bench offers (1 = up to 2 mA). The charge q is the one the student finds, from the slope of the output
    mean square against the current; the Johnson term is the intercept. Samples are drawn from the seed."""

    PARAMS = {"Rf": 1.0e4, "df": 20000.0, "n": 40000.0, "seed": 11.0, "T": 300.0, "I": 2.0e-4, "q": QE, "Iscale": 1.0}
    VARS = ["t", "v2", "vrms", "i_shot"]
    IS = [0.0, 5.0e-5, 1.0e-4, 2.0e-4, 5.0e-4, 1.0e-3, 2.0e-3]

    @staticmethod
    def v2_true(p: dict, i: float) -> float:
        return p["Rf"] ** 2 * p["df"] * (2.0 * p["q"] * i + 4.0 * KB * p["T"] / p["Rf"])

    @staticmethod
    def msq(p: dict, i: float, k: float) -> float:
        rnd = Rnd(p["seed"] + 977.0 * k)
        sd = math.sqrt(PhdShot.v2_true(p, i))
        n = int(p["n"])
        s = 0.0
        for _ in range(n):
            v = sd * rnd.gauss()
            s += v * v
        return s / n

    @staticmethod
    def view(s, p, cfg=None):
        v2 = PhdShot.v2_true(p, p["I"])
        return {"t": s.get("t", 0.0), "v2": v2, "vrms": math.sqrt(v2), "i_shot": math.sqrt(2.0 * p["q"] * p["I"] * p["df"])}

    @staticmethod
    def measure(p, cfg=None):
        xs, ys = [], []
        for j, i0 in enumerate(PhdShot.IS):
            i = i0 * p["Iscale"]
            xs.append(i)
            ys.append(PhdShot.msq(p, i, float(j)))
        ab = _slope(xs, ys)
        q = ab[1] / (2.0 * p["Rf"] ** 2 * p["df"])
        return {"q": q, "q19": q * 1.0e19, "floor": ab[0]}


def _qe(p: dict) -> float:
    return QE * 1.0e19                       # in units of 1e-19 C


# ============================================================================================ noise spectra
class PhdPsd(_Base):
    """An FFT spectrum analyser looking at a resistor in front of an amplifier. The one-sided voltage noise density
    is S(f) = S_w (1 + fc / f), with the white floor S_w = 4 kB T R + en^2 and an excess 1/f term that equals the
    white floor at the corner `fc`. Each record is a real time series of `N` samples built from that spectrum
    (random Gaussian amplitude and phase in every bin, inverse FFT); the analyser multiplies it by a Hann window,
    takes the FFT and averages `nseg` records. The floor and the corner are then found by a weighted least-squares
    fit of P(f) = a + b / f (the weights follow the model, as the scatter of a chi-squared estimate does)."""

    PARAMS = {"T": 300.0, "R": 10000.0, "en": 5.0e-9, "fc": 150.0, "fs": 8000.0, "N": 256.0, "nseg": 256.0, "seed": 17.0}
    VARS = ["t", "Sw", "Sf_low"]

    @staticmethod
    def sw(p: dict) -> float:
        return 4.0 * KB * p["T"] * p["R"] + p["en"] ** 2

    @staticmethod
    def spec(p: dict, f: float) -> float:
        return PhdPsd.sw(p) * (1.0 + p["fc"] / f)

    @staticmethod
    def record(p: dict, rnd: Rnd) -> list[float]:
        n = int(p["N"])
        re = [0.0] * n
        im = [0.0] * n
        half = n // 2
        for k in range(1, half):
            c = math.sqrt(PhdPsd.spec(p, k * p["fs"] / n) * p["fs"] * n / 4.0)
            g1 = rnd.gauss()
            g2 = rnd.gauss()
            re[k] = c * g1
            im[k] = c * g2
            re[n - k] = c * g1
            im[n - k] = -c * g2
        re[half] = math.sqrt(PhdPsd.spec(p, half * p["fs"] / n) * p["fs"] * n / 2.0) * rnd.gauss()
        fft(re, im, True)
        return [v / n for v in re]

    @staticmethod
    def psd(p: dict, nseg: int | None = None) -> list[list[float]]:
        """The averaged one-sided power spectrum [[f, P], ...] for bins 1 .. N/2 - 1."""
        n = int(p["N"])
        ns = int(p["nseg"]) if nseg is None else nseg
        rnd = Rnd(p["seed"])
        win = [0.5 - 0.5 * math.cos(2.0 * PI * i / n) for i in range(n)]
        sw2 = sum(w * w for w in win)
        acc = [0.0] * (n // 2)
        for _ in range(ns):
            x = PhdPsd.record(p, rnd)
            re = [x[i] * win[i] for i in range(n)]
            im = [0.0] * n
            fft(re, im)
            for k in range(1, n // 2):
                acc[k] += re[k] * re[k] + im[k] * im[k]
        return [[k * p["fs"] / n, 2.0 * acc[k] / (ns * p["fs"] * sw2)] for k in range(1, n // 2)]

    @staticmethod
    def fit(sp: list[list[float]]) -> list[float]:
        """Weighted fit of P = a + b / f -> [a, b]."""
        m = _mean([q[1] for q in sp])
        a, b = m, 0.0
        for _ in range(4):
            s11 = s12 = s22 = r1 = r2 = 0.0
            for f, pv in sp:
                mod = a + b / f
                if mod <= 0:
                    mod = m
                w = 1.0 / (mod * mod)
                s11 += w
                s12 += w / f
                s22 += w / (f * f)
                r1 += w * pv
                r2 += w * pv / f
            d = s11 * s22 - s12 * s12
            if d == 0:
                break
            a = (r1 * s22 - r2 * s12) / d
            b = (s11 * r2 - s12 * r1) / d
        return [a, b]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "Sw": PhdPsd.sw(p), "Sf_low": PhdPsd.spec(p, p["fs"] / p["N"])}

    @staticmethod
    def measure(p, cfg=None):
        ab = PhdPsd.fit(PhdPsd.psd(p))
        return {"floor": ab[0], "floor18": ab[0] * 1.0e18, "fc": ab[1] / ab[0] if ab[0] > 0 else 0.0}


def _psd_floor(p: dict) -> float:
    return (4.0 * KB * p["T"] * p["R"] + p["en"] ** 2) * 1.0e18          # in nV^2/Hz


# ============================================================================================ boxcar averager
class PhdBoxcar(_Base):
    """A boxcar integrator on a repetitive pulse A exp(-t / tau). Each shot the gate (width `w`, opening `td` after
    the trigger) averages the signal, and the average carries Gaussian noise of rms vn / sqrt(2 w) (a white noise
    density vn in V/sqrt(Hz) seen through a gate of width w). The gate average of the pulse alone is
    A (tau / w) (1 - exp(-w / tau)) exp(-td / tau). The output is the mean of `nav` shots. The student finds the
    decay time from the slope of ln(output) against gate delay."""

    PARAMS = {"tau": 2.0e-6, "A": 1.0, "vn": 3.0e-4, "w": 5.0e-7, "td": 0.0, "nav": 20000.0, "seed": 23.0}
    VARS = ["t", "sig", "sigma1", "snr"]
    NDEL = 8

    @staticmethod
    def sig(p: dict, td: float) -> float:
        return p["A"] * (p["tau"] / p["w"]) * (1.0 - math.exp(-p["w"] / p["tau"])) * math.exp(-td / p["tau"])

    @staticmethod
    def sigma1(p: dict) -> float:
        return p["vn"] / math.sqrt(2.0 * p["w"])

    @staticmethod
    def output(p: dict, td: float, nav: int, rnd: Rnd) -> float:
        s = PhdBoxcar.sig(p, td)
        sg = PhdBoxcar.sigma1(p)
        acc = 0.0
        for _ in range(nav):
            acc += s + sg * rnd.gauss()
        return acc / nav

    @staticmethod
    def view(s, p, cfg=None):
        sig = PhdBoxcar.sig(p, p["td"])
        sg = PhdBoxcar.sigma1(p) / math.sqrt(max(p["nav"], 1.0))
        return {"t": s.get("t", 0.0), "sig": sig, "sigma1": PhdBoxcar.sigma1(p), "snr": sig / sg}

    @staticmethod
    def measure(p, cfg=None):
        rnd = Rnd(p["seed"])
        xs, ys = [], []
        for j in range(PhdBoxcar.NDEL):
            td = 0.3 * p["tau"] * j
            y = PhdBoxcar.output(p, td, int(p["nav"]), rnd)
            if y > 0:
                xs.append(td)
                ys.append(math.log(y))
        b = _slope(xs, ys)[1]
        return {"tau": -1.0 / b if b < 0 else 0.0}


def _boxcar_tau(p: dict) -> float:
    return p["tau"]


# ============================================================================================ Hanbury Brown-Twiss
class PhdG2(_Base):
    """A Hanbury Brown-Twiss correlator: a beam splitter, two photon counters with mean rates R1 and R2, and a
    coincidence histogram of `nb` bins of width `bw` centred on zero delay, accumulated over `Ts` seconds. The
    expected number of coincidences in a bin at delay tau is R1 R2 Ts bw g2(tau). For thermal light (`kind` = 1,
    a laser beam through a rotating ground-glass disc, pseudo-thermal) g2(tau) = 1 + exp(-(tau / tc)^2) (the model
    for a Gaussian speckle decorrelation); for a laser (`kind` = 0) g2 = 1. Each bin is a Poisson number from the
    seed. g2(0) is the zero-delay bin over the mean of the far bins; the coherence time is fitted from the dip."""

    PARAMS = {"tc": 5.0e-5, "kind": 1.0, "R1": 2.0e5, "R2": 2.0e5, "Ts": 30.0, "nb": 81.0, "bw": 6.25e-6, "seed": 9.0}
    VARS = ["t", "g2_0", "Cinf"]

    @staticmethod
    def g2(p: dict, tau: float) -> float:
        if p["kind"] < 0.5:
            return 1.0
        return 1.0 + math.exp(-(tau / p["tc"]) ** 2)

    @staticmethod
    def hist(p: dict, ts: float | None = None) -> list[float]:
        nb = int(p["nb"])
        ts = p["Ts"] if ts is None else ts
        rnd = Rnd(p["seed"])
        out = []
        for i in range(nb):
            tau = (i - (nb - 1) // 2) * p["bw"]
            out.append(float(rnd.poisson(p["R1"] * p["R2"] * ts * p["bw"] * PhdG2.g2(p, tau))))
        return out

    @staticmethod
    def analyse(p: dict, h: list[float]) -> list[float]:
        nb = len(h)
        mid = (nb - 1) // 2
        far = [h[i] for i in range(nb) if abs(i - mid) * p["bw"] > 3.0 * p["tc"]]
        cinf = _mean(far)
        g20 = h[mid] / cinf if cinf > 0 else 0.0
        xs, ys = [], []
        for i in range(nb):
            tau = (i - mid) * p["bw"]
            if abs(tau) < 1.5 * p["tc"] and cinf > 0 and h[i] / cinf - 1.0 > 0.05:
                xs.append(tau * tau)
                ys.append(math.log(h[i] / cinf - 1.0))
        b = _slope(xs, ys)[1]
        tce = 1.0 / math.sqrt(-b) if b < 0 else 0.0
        return [g20, tce, cinf]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "g2_0": PhdG2.g2(p, 0.0), "Cinf": p["R1"] * p["R2"] * p["Ts"] * p["bw"]}

    @staticmethod
    def measure(p, cfg=None):
        a = PhdG2.analyse(p, PhdG2.hist(p))
        return {"g2_0": a[0], "tc": a[1], "Cinf": a[2]}


def _g2_zero(p: dict) -> float:
    return 1.0 + (1.0 if p["kind"] >= 0.5 else 0.0)


# ============================================================================================ Poisson counting
class PhdPoisson(_Base):
    """A counter on a source of true rate `rate` with a non-paralysable dead time `td`: after each registered count
    the counter is blind for td, so the registered intervals are td + an exponential interval of mean 1 / rate.
    The stream is simulated event by event from the seed for `nwin` windows of `tw` seconds. The student reads
    the counts per window (mean and variance) and the interval distribution. At a low rate (rate x td << 1) the
    variance equals the mean and the mean interval is 1 / rate; at a high rate the dead time makes the counts
    more regular than Poisson (Fano factor 1 / (1 + rate td)^2)."""

    PARAMS = {"rate": 200.0, "td": 1.0e-5, "tw": 1.0, "nwin": 1000.0, "seed": 13.0}
    VARS = ["t", "mean", "fano", "gap"]

    @staticmethod
    def stream(p: dict) -> dict:
        nwin = int(p["nwin"])
        tot = nwin * p["tw"]
        rnd = Rnd(p["seed"])
        counts = [0] * nwin
        t = 0.0
        ev = 0
        gaps: list[float] = []
        while True:
            g = p["td"] - math.log(rnd.next()) / p["rate"]
            t += g
            if t >= tot:
                break
            counts[int(t / p["tw"])] += 1
            ev += 1
            if len(gaps) < 20000:
                gaps.append(g)
        return {"counts": counts, "events": ev, "total": tot, "gaps": gaps}

    @staticmethod
    def stats(counts: list[int]) -> list[float]:
        n = len(counts)
        m = sum(counts) / n if n else 0.0
        v = 0.0
        for c in counts:
            v += (c - m) ** 2
        v = v / (n - 1.0) if n > 1 else 0.0
        return [m, v]

    @staticmethod
    def view(s, p, cfg=None):
        r = p["rate"]
        m = p["tw"] * r / (1.0 + r * p["td"])
        return {"t": s.get("t", 0.0), "mean": m, "fano": 1.0 / (1.0 + r * p["td"]) ** 2, "gap": 1.0 / r + p["td"]}

    @staticmethod
    def measure(p, cfg=None):
        st = PhdPoisson.stream(p)
        mv = PhdPoisson.stats(st["counts"])
        return {"mean": mv[0], "var": mv[1], "fano": mv[1] / mv[0] if mv[0] > 0 else 0.0,
                "gap": st["total"] / st["events"] if st["events"] > 0 else 0.0}


def _poisson_gap(p: dict) -> float:
    return 1.0 / p["rate"] + p["td"]


# ============================================================================================ heralded single photons
class PhdAntibunch(_Base):
    """The Grangier anticorrelation experiment: a heralding detector G fires `NG` times; each heralded event holds
    one photon, except a fraction `q` that hold two (a second pair). The photon(s) meet a 50:50 beam splitter and
    a detector of efficiency `eta` on each output, T and R. For n photons the chance of a T click is
    1 - (1 - eta/2)^n, of an R click the same, and of both 1 - 2 (1 - eta/2)^n + (1 - eta)^n. The counts N_GT,
    N_GR and N_GTR are drawn as Poisson numbers from the seed, and the student works out
    alpha = N_G N_GTR / (N_GT N_GR). alpha = 0 is a perfect single photon; classical light cannot go below 1."""

    PARAMS = {"q": 0.02, "eta": 0.5, "NG": 4.0e8, "seed": 21.0}
    VARS = ["t", "alpha"]

    @staticmethod
    def probs(p: dict) -> list[float]:
        e = p["eta"]
        q = p["q"]
        pt1 = e / 2.0
        pt2 = 1.0 - (1.0 - e / 2.0) ** 2
        pb2 = 1.0 - 2.0 * (1.0 - e / 2.0) ** 2 + (1.0 - e) ** 2
        return [(1.0 - q) * pt1 + q * pt2, q * pb2]          # P(T click) = P(R click), P(T and R)

    @staticmethod
    def alpha_exact(p: dict) -> float:
        pt, pb = PhdAntibunch.probs(p)
        return pb / (pt * pt) if pt > 0 else 0.0

    @staticmethod
    def counts(p: dict) -> list[float]:
        pt, pb = PhdAntibunch.probs(p)
        rnd = Rnd(p["seed"])
        ng = p["NG"]
        return [ng, float(rnd.poisson(ng * pt)), float(rnd.poisson(ng * pt)), float(rnd.poisson(ng * pb))]

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "alpha": PhdAntibunch.alpha_exact(p)}

    @staticmethod
    def measure(p, cfg=None):
        c = PhdAntibunch.counts(p)
        return {"alpha": c[0] * c[3] / (c[1] * c[2]) if c[1] > 0 and c[2] > 0 else 0.0}


def _antibunch_alpha(p: dict) -> float:
    return PhdAntibunch.alpha_exact(p)


# ============================================================================================ Fabry-Perot
class PhdFp(_Base):
    """A scanning Fabry-Perot cavity: two mirrors of intensity reflectivity `R`, length `L`, one mirror on a piezo
    that moves `kz` metres per volt. Light of wavelength `lam` (and, for a two-mode laser, a second mode `dnu` hertz
    higher with relative power `amp2`) is transmitted as the Airy function 1 / (1 + F sin^2(delta / 2)),
    F = 4 R / (1 - R)^2, delta = 4 pi (L + kz V) nu / c. The student reads the transmitted intensity against the
    scan voltage: the peak spacing in volts is one free spectral range (lambda / 2 of mirror travel) and the peak
    width gives the finesse. The trace has 12000 points over 0 .. `Vmax`."""

    PARAMS = {"L": 0.15, "R": 0.95, "lam": 6.328e-7, "kz": 1.0e-8, "dnu": 0.0, "amp2": 0.0, "Vmax": 120.0}
    VARS = ["t", "fsr_hz", "fsr_v"]
    NPT = 12000

    @staticmethod
    def trans(p: dict, v: float) -> float:
        fco = 4.0 * p["R"] / (1.0 - p["R"]) ** 2
        nu0 = C / p["lam"]
        d1 = 4.0 * PI * (p["L"] + p["kz"] * v) * nu0 / C
        y = 1.0 / (1.0 + fco * math.sin(d1 / 2.0) ** 2)
        if p["amp2"] > 0:
            d2 = 4.0 * PI * (p["L"] + p["kz"] * v) * (nu0 + p["dnu"]) / C
            y += p["amp2"] / (1.0 + fco * math.sin(d2 / 2.0) ** 2)
        return y

    @staticmethod
    def trace(p: dict) -> list[float]:
        n = PhdFp.NPT
        return [PhdFp.trans(p, p["Vmax"] * i / (n - 1.0)) for i in range(n)]

    @staticmethod
    def peaks(p: dict, y: list[float]) -> dict:
        """Find the strong peaks: runs above half the global maximum; their volts, and widths by interpolation."""
        n = len(y)
        dv = p["Vmax"] / (n - 1.0)
        hm = 0.5 * max(y)
        pos, wid = [], []
        i = 0
        while i < n:
            if y[i] > hm:
                j = i
                while j < n and y[j] > hm:
                    j += 1
                if i > 0 and j < n:
                    k = i
                    for m in range(i, j):
                        if y[m] > y[k]:
                            k = m
                    a = (i - 1) + (hm - y[i - 1]) / (y[i] - y[i - 1])
                    b = (j - 1) + (hm - y[j - 1]) / (y[j] - y[j - 1])
                    pos.append(k * dv)
                    wid.append((b - a) * dv)
                i = j
            else:
                i += 1
        return {"pos": pos, "wid": wid}

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "fsr_hz": C / (2.0 * p["L"]), "fsr_v": p["lam"] / (2.0 * p["kz"])}

    @staticmethod
    def measure(p, cfg=None):
        pk = PhdFp.peaks(p, PhdFp.trace(p))
        ps, ws = pk["pos"], pk["wid"]
        if len(ps) < 2:
            return {"finesse": 0.0, "fsr_v": 0.0, "fsr_hz": 0.0}
        fsrv = (ps[-1] - ps[0]) / (len(ps) - 1.0)
        return {"finesse": fsrv / _mean(ws), "fsr_v": fsrv, "fsr_hz": C / (2.0 * p["L"])}


def _fp_finesse(p: dict) -> float:
    return PI * math.sqrt(p["R"]) / (1.0 - p["R"])


# ============================================================================================ Langmuir probe
class PhdLangmuir(_Base):
    """A cylindrical Langmuir probe of area `Ap` in a plasma of electron temperature `Te` (eV), density `ne` and
    plasma potential `Vp`, ion mass `M` (amu). Single probe: electrons I_e = Ies exp((V - Vp) / Te) below Vp and Ies
    above it, minus the ion saturation current Iis = exp(-1/2) e ne Ap sqrt(e Te / M) (Bohm), with
    Ies = (1/4) e ne vbar Ap, vbar = sqrt(8 e Te / (pi me)). Double probe (two identical probes, floating pair):
    I = Iis tanh(V / (2 Te)). Emissive probe: a heated wire emits Iem (Richardson, wire temperature
    Tw = 300 + Kh Ih^2) so its floating potential Vf = Vp + Te ln((Iis + Iem) / Ies) climbs to Vp as the emission
    reaches the electron saturation current (an idealised, space-charge-free emitter). Noise: 0.3 % of each current
    and 0.05 V on the floating-potential voltmeter, from the seed. Wire work function `W`, Richardson constant `Ar`
    and heating `Kh` are illustrative."""

    PARAMS = {"Te": 3.0, "ne": 1.0e16, "Vp": 8.0, "M": 39.948, "Ap": 2.0e-6, "noise": 0.003, "seed": 31.0,
              "W": 4.5, "Ar": 6.0e5, "Kh": 250.0, "V": 0.0}
    VARS = ["t", "I", "Iis", "Ies", "Vf"]

    @staticmethod
    def iis(p: dict) -> float:
        return math.exp(-0.5) * QE * p["ne"] * p["Ap"] * math.sqrt(QE * p["Te"] / (p["M"] * AMU))

    @staticmethod
    def ies(p: dict) -> float:
        return 0.25 * QE * p["ne"] * math.sqrt(8.0 * QE * p["Te"] / (PI * ME)) * p["Ap"]

    @staticmethod
    def single(p: dict, v: float) -> float:
        e = PhdLangmuir.ies(p) * (math.exp((v - p["Vp"]) / p["Te"]) if v < p["Vp"] else 1.0)
        return e - PhdLangmuir.iis(p)

    @staticmethod
    def double(p: dict, v: float) -> float:
        return PhdLangmuir.iis(p) * math.tanh(v / (2.0 * p["Te"]))

    @staticmethod
    def iem(p: dict, ih: float) -> float:
        tw = 300.0 + p["Kh"] * ih * ih
        return p["Ar"] * tw * tw * p["Ap"] * math.exp(-p["W"] * QE / (KB * tw))

    @staticmethod
    def vfloat(p: dict, ih: float) -> float:
        tot = PhdLangmuir.iis(p) + PhdLangmuir.iem(p, ih)
        ies = PhdLangmuir.ies(p)
        return p["Vp"] + p["Te"] * math.log(tot / ies) if tot < ies else p["Vp"]

    @staticmethod
    def sweep_single(p: dict) -> list[list[float]]:
        rnd = Rnd(p["seed"])
        out = []
        for k in range(241):
            v = -40.0 + 0.25 * k
            out.append([v, PhdLangmuir.single(p, v) * (1.0 + p["noise"] * rnd.gauss())])
        return out

    @staticmethod
    def sweep_double(p: dict) -> list[list[float]]:
        rnd = Rnd(p["seed"] + 1.0)
        out = []
        for k in range(241):
            v = -30.0 + 0.25 * k
            out.append([v, PhdLangmuir.double(p, v) * (1.0 + p["noise"] * rnd.gauss())])
        return out

    @staticmethod
    def sweep_emissive(p: dict) -> list[list[float]]:
        rnd = Rnd(p["seed"] + 2.0)
        return [[0.1 * k, PhdLangmuir.vfloat(p, 0.1 * k) + 0.05 * rnd.gauss()] for k in range(36)]

    @staticmethod
    def fit_single(p: dict, sw: list[list[float]]) -> dict:
        """Te from the slope of ln(electron current) against V in the transition region, after taking the ion
        saturation current off; Vp from where that line meets the electron saturation plateau."""
        iis = -_mean([q[1] for q in sw[:20]])
        imax = _mean([q[1] for q in sw[-15:]]) + iis
        xs, ys = [], []
        for v, i in sw:
            ie = i + iis
            if 0.02 * imax < ie < 0.5 * imax:
                xs.append(v)
                ys.append(math.log(ie))
        ab = _slope(xs, ys)
        te = 1.0 / ab[1] if ab[1] > 0 else 0.0
        vp = (math.log(imax) - ab[0]) / ab[1] if ab[1] > 0 else 0.0
        ne = iis / (math.exp(-0.5) * QE * p["Ap"] * math.sqrt(QE * te / (p["M"] * AMU))) if te > 0 else 0.0
        return {"Te": te, "Vp": vp, "ne": ne, "Iis": iis, "a": ab[0], "imax": imax}

    @staticmethod
    def fit_double(p: dict, sw: list[list[float]]) -> dict:
        sat = _mean([abs(q[1]) for q in sw if abs(q[0]) >= 25.0])
        num = den = 0.0
        for v, i in sw:
            if abs(i) < 0.7 * sat:
                num += v * math.atanh(i / sat)
                den += v * v
        te = den / (2.0 * num) if num > 0 else 0.0
        ne = sat / (math.exp(-0.5) * QE * p["Ap"] * math.sqrt(QE * te / (p["M"] * AMU))) if te > 0 else 0.0
        return {"Te": te, "ne": ne, "Iis": sat}

    @staticmethod
    def fit_emissive(sw: list[list[float]]) -> float:
        return _mean([q[1] for q in sw[-6:]])

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "I": PhdLangmuir.single(p, p["V"]), "Iis": PhdLangmuir.iis(p), "Ies": PhdLangmuir.ies(p),
                "Vf": p["Vp"] + p["Te"] * math.log(PhdLangmuir.iis(p) / PhdLangmuir.ies(p))}

    @staticmethod
    def measure(p, cfg=None):
        a = PhdLangmuir.fit_single(p, PhdLangmuir.sweep_single(p))
        b = PhdLangmuir.fit_double(p, PhdLangmuir.sweep_double(p))
        return {"Te": a["Te"], "Te_double": b["Te"], "Vp": a["Vp"], "ne": a["ne"], "ne_double": b["ne"],
                "Vp_emissive": PhdLangmuir.fit_emissive(PhdLangmuir.sweep_emissive(p))}


def _lang_te(p: dict) -> float:
    return p["Te"]


def _lang_vp(p: dict) -> float:
    return p["Vp"]


# ============================================================================================ Paschen curve
class PhdPaschen(_Base):
    """Breakdown voltage of a gas between parallel plates: V_b = B pd / (ln(A pd) - ln(ln(1 + 1/gam))), with p the
    pressure in Torr, d the gap in cm, A and B the gas constants (1/(cm Torr) and V/(cm Torr)) and gam the
    secondary-electron coefficient of the cathode. Breakdown is reported to 0.3 % scatter (seeded). The student
    scans pd on a log grid and finds the minimum by a quadratic fit to the lowest points."""

    PARAMS = {"A": 15.0, "B": 365.0, "gam": 0.01, "noise": 0.003, "seed": 41.0, "pd": 1.0}
    VARS = ["t", "Vb", "pdmin", "Vmin"]
    NPT = 121

    @staticmethod
    def vb(p: dict, pd: float) -> float:
        den = math.log(p["A"] * pd) - math.log(math.log(1.0 + 1.0 / p["gam"]))
        return p["B"] * pd / den if den > 0 else 0.0

    @staticmethod
    def grid(p: dict) -> list[float]:
        """pd values from just above the lowest possible value up to 300 Torr cm, log-spaced."""
        lo = math.exp(1.0) * math.log(1.0 + 1.0 / p["gam"]) / p["A"] * 0.3 * 1.6
        out = []
        for i in range(PhdPaschen.NPT):
            out.append(lo * math.exp(math.log(300.0 / lo) * i / (PhdPaschen.NPT - 1.0)))
        return out

    @staticmethod
    def scan(p: dict) -> list[list[float]]:
        rnd = Rnd(p["seed"])
        return [[pd, PhdPaschen.vb(p, pd) * (1.0 + p["noise"] * rnd.gauss())] for pd in PhdPaschen.grid(p)]

    @staticmethod
    def minimum(sc: list[list[float]]) -> list[float]:
        """The lowest point, refined by a quadratic fit of V against ln(pd) over it and its five neighbours."""
        k = 0
        for i in range(len(sc)):
            if sc[i][1] > 0 and (sc[k][1] <= 0 or sc[i][1] < sc[k][1]):
                k = i
        lo = max(0, k - 4)
        hi = min(len(sc), k + 5)
        pts = [q for q in sc[lo:hi] if q[1] > 0]
        n = len(pts)
        xs = [math.log(q[0]) for q in pts]
        ys = [q[1] for q in pts]
        m = _mean(xs)
        xs = [x - m for x in xs]
        s0, s1, s2, s3, s4, t0, t1, t2 = float(n), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        for i in range(n):
            x = xs[i]
            s1 += x
            s2 += x * x
            s3 += x ** 3
            s4 += x ** 4
            t0 += ys[i]
            t1 += x * ys[i]
            t2 += x * x * ys[i]
        # solve [s0 s1 s2; s1 s2 s3; s2 s3 s4] [a b c] = [t0 t1 t2] by Cramer's rule
        d = s0 * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2)
        if d == 0:
            return [sc[k][0], sc[k][1]]
        da = t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)
        db = s0 * (t1 * s4 - s3 * t2) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - t1 * s2)
        dc = s0 * (s2 * t2 - t1 * s3) - s1 * (s1 * t2 - t1 * s2) + t0 * (s1 * s3 - s2 * s2)
        a, b, c = da / d, db / d, dc / d
        if c <= 0:
            return [sc[k][0], sc[k][1]]
        x0 = -b / (2.0 * c)
        return [math.exp(x0 + m), a + b * x0 + c * x0 * x0]

    @staticmethod
    def view(s, p, cfg=None):
        e = math.exp(1.0) * math.log(1.0 + 1.0 / p["gam"]) / p["A"]
        return {"t": s.get("t", 0.0), "Vb": PhdPaschen.vb(p, p["pd"]), "pdmin": e, "Vmin": p["B"] * e}

    @staticmethod
    def measure(p, cfg=None):
        mn = PhdPaschen.minimum(PhdPaschen.scan(p))
        return {"pdmin": mn[0], "Vmin": mn[1]}


def _paschen_vmin(p: dict) -> float:
    return math.exp(1.0) * p["B"] * math.log(1.0 + 1.0 / p["gam"]) / p["A"]


# ============================================================================================ optical tweezers
class PhdTweezers(_Base):
    """A bead of radius `a` in water (viscosity `eta`, temperature `T`) held in an optical trap whose stiffness is
    kappa = kp P (`kp` N/m per mW of laser power, `P` in mW). Overdamped Brownian motion in the trap is an
    Ornstein-Uhlenbeck process, stepped exactly: x' = x e^(-dt/tau) + sqrt(kB T / kappa (1 - e^(-2 dt/tau))) g,
    with tau = gamma / kappa and the Stokes drag gamma = 6 pi eta a. `N` samples at `fs` hertz are recorded from the
    seed. Three ways to the stiffness: equipartition kappa = kB T / <x^2>; the corner frequency fc = kappa / (2 pi
    gamma) of the Lorentzian power spectrum; and Stokes drag, moving the stage at speed `v` so the bead lags by
    x_d = gamma v / kappa. With kappa known from the drag the same record gives kB, and with kappa from equipartition
    the corner frequency gives the viscosity. `kp` is the lab's own illustrative number."""

    PARAMS = {"a": 5.0e-7, "eta": 1.0e-3, "T": 295.0, "kp": 2.0e-6, "P": 5.0, "fs": 5000.0, "N": 262144.0, "seg": 2048.0,
              "nseg": 32.0, "v": 1.0e-4, "Td": 10.0, "seed": 71.0}
    VARS = ["t", "kappa", "fc", "gamma", "xrms"]

    @staticmethod
    def gamma(p: dict) -> float:
        return 6.0 * PI * p["eta"] * p["a"]

    @staticmethod
    def kappa(p: dict) -> float:
        return p["kp"] * p["P"]

    @staticmethod
    def record(p: dict, n: int, seed_add: float, drift: float) -> list[float]:
        """n samples of the bead position (m); `drift` is the trap-centre lag-free offset (m) for the drag test."""
        k = PhdTweezers.kappa(p)
        tau = PhdTweezers.gamma(p) / k
        dt = 1.0 / p["fs"]
        a = math.exp(-dt / tau)
        sd = math.sqrt(KB * p["T"] / k * (1.0 - a * a))
        rnd = Rnd(p["seed"] + seed_add)
        x = math.sqrt(KB * p["T"] / k) * rnd.gauss()
        out = []
        for _ in range(n):
            x = a * x + sd * rnd.gauss()
            out.append(x + drift)
        return out

    @staticmethod
    def spectrum(p: dict, xs: list[float], nseg: int | None = None) -> list[list[float]]:
        """Averaged one-sided power spectrum [[f, P(m^2/Hz)], ...] of Hann-windowed segments of the record."""
        sg = int(p["seg"])
        ns = int(p["nseg"]) if nseg is None else nseg
        ns = min(ns, len(xs) // sg)
        win = [0.5 - 0.5 * math.cos(2.0 * PI * i / sg) for i in range(sg)]
        sw2 = sum(w * w for w in win)
        acc = [0.0] * (sg // 2)
        for s in range(ns):
            m = _mean(xs[s * sg:(s + 1) * sg])
            re = [(xs[s * sg + i] - m) * win[i] for i in range(sg)]
            im = [0.0] * sg
            fft(re, im)
            for k in range(1, sg // 2):
                acc[k] += re[k] * re[k] + im[k] * im[k]
        return [[k * p["fs"] / sg, 2.0 * acc[k] / (ns * p["fs"] * sw2)] for k in range(1, sg // 2)]

    @staticmethod
    def corner(sp: list[list[float]], fs: float = 5000.0) -> float:
        """Corner frequency by the aliasing-corrected Lorentzian (the spectrum of a position sampled at fs):
        1/S = c0 + c1 cos(2 pi f / fs), with a = exp(-dt/tau) given by c0 / |c1| = (1 + a^2) / (2 a). A weighted
        least-squares fit of the line, weights S^2 (the scatter of 1/S is proportional to 1/S)."""
        c0 = 1.0 / sp[0][1]
        c1 = -0.5 * c0
        for _ in range(5):
            s11 = s12 = s22 = r1 = r2 = 0.0
            for f, pv in sp:
                u = math.cos(2.0 * PI * f / fs)
                mod = 1.0 / (c0 + c1 * u)
                if mod <= 0:
                    mod = pv
                w = mod * mod
                y = 1.0 / pv
                s11 += w
                s12 += w * u
                s22 += w * u * u
                r1 += w * y
                r2 += w * u * y
            d = s11 * s22 - s12 * s12
            if d == 0:
                break
            c0 = (r1 * s22 - r2 * s12) / d
            c1 = (s11 * r2 - s12 * r1) / d
        if c1 >= 0 or c0 <= 0:
            return 0.0
        q = c0 / (-c1)
        if q <= 1.0:
            return 0.0
        a = q - math.sqrt(q * q - 1.0)
        return -math.log(a) * fs / (2.0 * PI)

    @staticmethod
    def view(s, p, cfg=None):
        k = PhdTweezers.kappa(p)
        g = PhdTweezers.gamma(p)
        return {"t": s.get("t", 0.0), "kappa": k, "fc": k / (2.0 * PI * g), "gamma": g, "xrms": math.sqrt(KB * p["T"] / k)}

    @staticmethod
    def measure(p, cfg=None):
        n = int(p["N"])
        xs = PhdTweezers.record(p, n, 0.0, 0.0)
        m = _mean(xs)
        x2 = _mean([(x - m) ** 2 for x in xs])
        k_eq = KB * p["T"] / x2
        fc = PhdTweezers.corner(PhdTweezers.spectrum(p, xs), p["fs"])
        g = PhdTweezers.gamma(p)
        nd = int(p["Td"] * p["fs"])
        xd = _mean(PhdTweezers.record(p, nd, 1.0, g * p["v"] / PhdTweezers.kappa(p))) - m
        k_dr = g * p["v"] / xd if xd > 0 else 0.0
        return {"k_eq": k_eq, "k_eq_u": k_eq * 1.0e6, "k_psd": 2.0 * PI * g * fc, "k_drag": k_dr, "fc": fc,
                "kB_est": k_dr * x2 / p["T"], "eta_est": k_eq / (2.0 * PI * fc * 6.0 * PI * p["a"]) if fc > 0 else 0.0}


def _tw_kappa(p: dict) -> float:
    return p["kp"] * p["P"] * 1.0e6                  # in micronewtons per metre (pN per nm x 1000), so the checker's relative error is meaningful


KERNELS: dict[str, Any] = {"phd_lockin": PhdLockin, "phd_johnson": PhdJohnson, "phd_shot": PhdShot, "phd_psd": PhdPsd,
                           "phd_boxcar": PhdBoxcar, "phd_g2": PhdG2, "phd_poisson": PhdPoisson,
                           "phd_antibunch": PhdAntibunch, "phd_fp": PhdFp, "phd_langmuir": PhdLangmuir,
                           "phd_paschen": PhdPaschen, "phd_tweezers": PhdTweezers}
FAMILY = {k: "optics" for k in KERNELS}
TEXTBOOK = {
    "phd_lockin_A": _lockin_A,
    "phd_o_kB": _kb,
    "phd_o_qe": _qe,
    "phd_psd_floor": _psd_floor,
    "phd_boxcar_tau": _boxcar_tau,
    "phd_g2_zero": _g2_zero,
    "phd_poisson_gap": _poisson_gap,
    "phd_antibunch_alpha": _antibunch_alpha,
    "phd_fp_finesse": _fp_finesse,
    "phd_lang_te": _lang_te,
    "phd_lang_vp": _lang_vp,
    "phd_paschen_vmin": _paschen_vmin,
    "phd_tw_kappa": _tw_kappa,
}
CALCS: dict[str, dict] = {}
