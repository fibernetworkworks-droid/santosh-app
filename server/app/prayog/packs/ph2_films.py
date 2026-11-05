"""Kernel pack `ph2_films`: thin-film, vacuum, X-ray and semiconductor-characterisation benches for the physics
build-out (see `packs/__init__.py`). Its exact JavaScript twin is `app/static/prayog/packs/ph2_films.js`; the test
suite runs both and demands the same numbers. Every kernel name and every TEXTBOOK / CALCS key starts with `ph2_`.

Deterministic: pseudo-noise is a hash of the sample index and a lab `seed`, never the clock.
Constants are CODATA / SI 2019; every material number lives in a family file with its source or its "unsourced /
illustrative" label.

Honest limits (said again in each lab):
 - ph2_xrd: positions are exact Bragg angles of the cubic cell; line heights come from a model scattering factor
   f = Z exp(-2 s^2) with the atomic positions FIXED (not refined), so this is a lattice-parameter and phase-fraction
   refinement of a fixed structure model (Rietveld-style scale factors), not a full Rietveld refinement.
 - ph2_xrr: exact Parratt recursion with Nevot-Croce roughness; absorption is a fixed small fraction of delta.
 - the others are closed models of the textbook law, checked against that law.
"""
from __future__ import annotations

import cmath
import math
from typing import Any

PI = math.pi
QE = 1.602176634e-19
KB = 1.380649e-23
NA = 6.02214076e23
RE = 2.8179403262e-15
AMU = 1.66053906660e-27
D2R = PI / 180.0


def _line(pts: list[list[float]]) -> tuple[float, float]:
    n = len(pts)
    if n < 2:
        return 0.0, 0.0
    sx = sy = sxy = sxx = 0.0
    for x, y in pts:
        sx += x
        sy += y
        sxy += x * y
        sxx += x * x
    d = n * sxx - sx * sx
    if d == 0:
        return 0.0, 0.0
    m = (n * sxy - sx * sy) / d
    return m, (sy - m * sx) / n


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


def _h(i: int, seed: int) -> float:
    x = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    x = (x ^ (x >> 16)) & 0xFFFFFFFF
    return x / 4294967296.0


def _g(i: int, seed: int) -> float:
    """Roughly standard-normal noise from four hashed uniforms."""
    s = _h(i * 4, seed) + _h(i * 4 + 1, seed) + _h(i * 4 + 2, seed) + _h(i * 4 + 3, seed)
    return (s - 2.0) * 1.7320508075688772


class _Base:
    @staticmethod
    def init(p, cfg=None):
        return {"t": 0.0}

    @staticmethod
    def step(s, p, dt, cfg=None):
        s["t"] += dt


# ====================================================================================== X-ray powder diffraction
FCC = ((0.0, 0.0, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.0))
NOMINAL_A = {1: 5.431, 2: 3.905, 3: 8.39}
ZMV = {1: (8.0, 28.0855), 2: (1.0, 183.484), 3: (8.0, 234.619)}     # formula units per cell, formula mass


def _atoms(t: int, ox: float) -> list[tuple]:
    if t == 2:
        return [(38.0, 0.0, 0.0, 0.0), (22.0, 0.5, 0.5, 0.5), (8.0, 0.5, 0.5, 0.0), (8.0, 0.5, 0.0, 0.5), (8.0, 0.0, 0.5, 0.5)]
    if t == 1:
        basis = [(14.0, 0.0, 0.0, 0.0), (14.0, 0.25, 0.25, 0.25)]
    else:
        x = ox
        basis = [(26.0, 0.125, 0.125, 0.125), (26.0, 0.875, 0.375, 0.375),
                 (26.5, 0.5, 0.5, 0.5), (26.5, 0.25, 0.75, 0.0), (26.5, 0.75, 0.0, 0.25), (26.5, 0.0, 0.25, 0.75),
                 (8.0, x, x, x), (8.0, -x + 0.75, -x + 0.25, x + 0.5), (8.0, -x + 0.25, x + 0.5, -x + 0.75),
                 (8.0, x + 0.5, -x + 0.75, -x + 0.25), (8.0, -x, -x, -x), (8.0, x + 0.25, x + 0.75, -x + 0.5),
                 (8.0, x + 0.75, -x + 0.5, x + 0.25), (8.0, -x + 0.5, x + 0.25, x + 0.75)]
    out = []
    for tr in FCC:
        for z, x, y, w in basis:
            out.append((z, x + tr[0], y + tr[1], w + tr[2]))
    return out


def _mult(h: int, k: int, l: int) -> int:
    nz = (1 if h else 0) + (1 if k else 0) + (1 if l else 0)
    if h == k and k == l:
        perms = 1
    elif h == k or k == l or h == l:
        perms = 3
    else:
        perms = 6
    return perms * (1 << nz)


def _nsf(t: int, a: float, nmax: int, ox: float = 0.256) -> dict[int, float]:
    """N = h^2+k^2+l^2 -> sum over the hkl classes of m |F|^2 (a in angstrom). Absent lines are left out."""
    atoms = _atoms(t, ox)
    sz = 0.0
    for at in atoms:
        sz += at[0]
    out: dict[int, float] = {}
    hmax = int(math.sqrt(nmax)) + 1
    for h in range(0, hmax + 1):
        for k in range(0, h + 1):
            for l in range(0, k + 1):
                n = h * h + k * k + l * l
                if n == 0 or n > nmax:
                    continue
                sa = math.sqrt(n) / (2.0 * a)
                ff = math.exp(-2.0 * sa * sa)
                re = im = 0.0
                for z, x, y, w in atoms:
                    ph = 2.0 * PI * (h * x + k * y + l * w)
                    re += z * ff * math.cos(ph)
                    im += z * ff * math.sin(ph)
                f2 = re * re + im * im
                if f2 < 1e-6 * sz * sz * ff * ff:
                    continue
                out[n] = out.get(n, 0.0) + _mult(h, k, l) * f2
    return out


def _refl(t: int, a: float, lam: float, tmin: float, tmax: float) -> list[dict]:
    """The lines of a cubic phase (a, lam in angstrom) inside the scan: N, 2theta, m|F|^2 and the Lorentz-polarisation factor."""
    nmax = int((2.0 * a / lam) ** 2) + 1
    nsf = _nsf(t, a, nmax)
    out = []
    for n in sorted(nsf):
        s = lam * math.sqrt(n) / (2.0 * a)
        if s >= 1.0:
            continue
        th = math.asin(s)
        tth = 2.0 * th / D2R
        if tth < tmin or tth > tmax:
            continue
        c2 = math.cos(2.0 * th)
        lp = (1.0 + c2 * c2) / (s * s * math.cos(th))
        out.append({"N": n, "tth": tth, "sf": nsf[n], "lp": lp, "G": nsf[n] * lp / (a ** 6)})
    return out


def _phase_list(p: dict) -> list[tuple]:
    out = [(int(round(p["t1"])), p["a1"] * 1e10, p["w1"])]
    if int(round(p["t2"])) > 0:
        out.append((int(round(p["t2"])), p["a2"] * 1e10, 1.0 - p["w1"]))
    return out


def _xrd_peaks(p: dict) -> list[dict]:
    lam = p["lam"] * 1e10
    pk = []
    for t, a, w in _phase_list(p):
        z, m = ZMV[t]
        sp = w * 1.0e4 / (z * m * a ** 3)
        for r in _refl(t, a, lam, p["tmin"] - 2.0, p["tmax"] + 2.0):
            th = r["tth"] * D2R / 2.0
            bs = 0.9 * p["lam"] / (p["Lx"] * math.cos(th)) / D2R
            beta = math.sqrt(p["binst"] ** 2 + bs * bs)
            pk.append({"tth": r["tth"], "area": p["I0"] * sp * r["G"], "beta": beta})
    return pk


def _xrd_counts(x: float, p: dict, pk: list[dict], i: int) -> float:
    base = p["bg"]
    c = 2.0 * math.sqrt(math.log(2.0) / PI)
    for q in pk:
        d = x - q["tth"]
        if abs(d) < 5.0 * q["beta"]:
            base += q["area"] * c / q["beta"] * math.exp(-4.0 * math.log(2.0) * d * d / (q["beta"] ** 2))
    v = base + math.sqrt(max(base, 1.0)) * _g(i, int(p["seed"]))
    return v if v > 0.0 else 0.0


def _xrd_scan(p: dict) -> tuple[list[float], list[float]]:
    pk = _xrd_peaks(p)
    n = int(round((p["tmax"] - p["tmin"]) / 0.02)) + 1
    xs, ys = [], []
    for i in range(n):
        x = p["tmin"] + 0.02 * i
        xs.append(x)
        ys.append(_xrd_counts(x, p, pk, i))
    return xs, ys


def _smooth5(y: list[float]) -> list[float]:
    n = len(y)
    out = []
    for i in range(n):
        lo, hi = max(0, i - 2), min(n - 1, i + 2)
        s = 0.0
        for j in range(lo, hi + 1):
            s += y[j]
        out.append(s / (hi - lo + 1))
    return out


def _find_lines(xs: list[float], ys: list[float]) -> list[dict]:
    """Lines of a scan, found numerically: smoothed local maxima, half-maximum width, centroid, area."""
    n = len(ys)
    if n < 20:
        return []
    sm = _smooth5(ys)
    low = sorted(sm)[: max(1, n // 5)]
    bg = sum(low) / len(low)
    thr = bg + 10.0 * math.sqrt(bg)
    step = xs[1] - xs[0]
    w = 7
    out = []
    for i in range(w, n - w):
        v = sm[i]
        if v < thr:
            continue
        ok = True
        for j in range(i - w, i):
            if sm[j] >= v:
                ok = False
                break
        if ok:
            for j in range(i + 1, i + w + 1):
                if sm[j] > v:
                    ok = False
                    break
        if not ok:
            continue
        half = bg + 0.5 * (v - bg)
        l = i
        while l > 0 and sm[l] > half:
            l -= 1
        r = i
        while r < n - 1 and sm[r] > half:
            r += 1
        xl = xs[l] + (half - sm[l]) / (sm[l + 1] - sm[l]) * step if sm[l + 1] != sm[l] else xs[l]
        xr = xs[r] - (half - sm[r]) / (sm[r - 1] - sm[r]) * step if sm[r - 1] != sm[r] else xs[r]
        fw = xr - xl
        sw = sx = 0.0
        for j in range(l, r + 1):
            wt = ys[j] - bg
            if wt > 0:
                sw += wt
                sx += wt * xs[j]
        c = sx / sw if sw > 0 else xs[i]
        area = 0.0
        for j in range(n):
            if abs(xs[j] - c) <= 2.0 * fw:
                area += (ys[j] - bg) * step
        out.append({"tth": c, "fwhm": fw, "area": area, "height": v - bg})
    return out


def _index_phase(lines: list[dict], lam: float, t: int, used: list[bool]) -> dict | None:
    """Index the unused lines with the allowed reflections of structure t; refine a by least squares on sin^2(theta).
    A trial cell scores its matched lines minus twice the strong lines it predicts that the scan does not show."""
    nsf = _nsf(t, NOMINAL_A[t], 140)
    allowed = sorted(nsf)
    free = [i for i in range(len(lines)) if not used[i]]
    best = None
    for i in free[:5]:
        si = math.sin(lines[i]["tth"] * D2R / 2.0)
        for n0 in allowed[:8]:
            ac = lam * math.sqrt(n0) / (2.0 * si)
            pairs = []
            res = 0.0
            for j in free:
                sj = math.sin(lines[j]["tth"] * D2R / 2.0)
                est = (2.0 * ac * sj / lam) ** 2
                bn, bd = 0, 1e9
                for nk in allowed:
                    d = abs(nk - est)
                    if d < bd:
                        bd, bn = d, nk
                sk = lam * math.sqrt(bn) / (2.0 * ac)
                if sk >= 1.0:
                    continue
                dt = abs(lines[j]["tth"] - 2.0 * math.asin(sk) / D2R)
                if dt < 0.12:
                    pairs.append((j, bn))
                    res += dt * dt
            pred = []
            for nk in allowed:
                sk = lam * math.sqrt(nk) / (2.0 * ac)
                if sk >= 1.0:
                    break
                th = math.asin(sk)
                tk = 2.0 * th / D2R
                if tk < 20.0 or tk > 100.0:
                    continue
                c2 = math.cos(2.0 * th)
                pred.append((tk, nsf[nk] * (1.0 + c2 * c2) / (sk * sk * math.cos(th))))
            top = 0.0
            for _tk, w in pred:
                if w > top:
                    top = w
            miss = 0
            for tk, w in pred:
                if w >= 0.05 * top:
                    seen = False
                    for j in free:
                        if abs(lines[j]["tth"] - tk) < 0.15:
                            seen = True
                            break
                    if not seen:
                        miss += 1
            sc = len(pairs) - 2 * miss
            if best is None or sc > best[0] or (sc == best[0] and ac < best[3] - 1e-9):
                best = (sc, res, pairs, ac)
    if best is None or len(best[2]) < 3:
        return None
    sn = sd = 0.0
    for j, nn in best[2]:
        s2 = math.sin(lines[j]["tth"] * D2R / 2.0) ** 2
        sn += nn * s2
        sd += nn * nn
    k = sn / sd
    return {"a": lam / (2.0 * math.sqrt(k)), "pairs": best[2], "n": len(best[2])}


def _xrd_fit(p: dict) -> dict:
    lam = p["lam"] * 1e10
    xs, ys = _xrd_scan(p)
    lines = _find_lines(xs, ys)
    used = [False] * len(lines)
    out = {"a": 0.0, "a2": 0.0, "w1": 1.0, "L": 0.0, "n1": 0.0, "n2": 0.0, "lines": float(len(lines))}
    ph = _phase_list(p)
    sw = []
    for idx, (t, a_true, w) in enumerate(ph):
        r = _index_phase(lines, lam, t, used)
        if r is None:
            sw.append(0.0)
            continue
        for j, _ in r["pairs"]:
            used[j] = True
        a = r["a"]
        refl = {q["N"]: q for q in _refl(t, a, lam, p["tmin"] - 2.0, p["tmax"] + 2.0)}
        sg = sgg = 0.0
        for j, nn in r["pairs"]:
            q = refl.get(nn)
            if q is None:
                continue
            g = q["sf"] * q["lp"] / (a ** 6)
            sg += lines[j]["area"] * g
            sgg += g * g
        sp = sg / (p["I0"] * sgg) if sgg > 0 else 0.0
        z, m = ZMV[t]
        sw.append(sp * z * m * a ** 3)
        key = "a" if idx == 0 else "a2"
        out[key] = a * 1e-10
        out["n1" if idx == 0 else "n2"] = float(r["n"])
        if idx == 0:
            jl, _ = max(r["pairs"], key=lambda q: lines[q[0]]["tth"])
            th = lines[jl]["tth"] * D2R / 2.0
            bo = lines[jl]["fwhm"] * D2R
            bi = p["binst"] * D2R
            if bo > bi:
                out["L"] = 0.9 * p["lam"] / (math.sqrt(bo * bo - bi * bi) * math.cos(th))
    tot = sum(sw)
    out["w1"] = sw[0] / tot if tot > 0 and len(sw) > 0 else 1.0
    return out


class Xrd(_Base):
    """A cubic powder pattern: Bragg positions of the lattice, line areas from m|F|^2 LP / V^2 with a per-phase scale
    S = w / (Z M V) (the Hill-Howard relation), Scherrer + instrument widths, a flat background and seeded counting noise."""

    PARAMS = {"tth": 30.0, "lam": 1.5406e-10, "a1": 5.43102e-10, "t1": 1.0, "a2": 0.0, "t2": 0.0, "w1": 1.0,
              "Lx": 5.0e-8, "binst": 0.08, "bg": 30.0, "I0": 60.0, "seed": 7.0, "tmin": 20.0, "tmax": 100.0}
    VARS = ["t", "I", "tth"]

    @staticmethod
    def view(s, p, cfg=None):
        pk = _xrd_peaks(p)
        i = int(round((p["tth"] - p["tmin"]) / 0.02))
        return {"t": s.get("t", 0.0), "I": _xrd_counts(p["tth"], p, pk, i), "tth": p["tth"]}

    @staticmethod
    def measure(p, cfg=None):
        r = _xrd_fit(p)
        return {"a": r["a"], "a2": r["a2"], "w1": r["w1"], "L": r["L"], "n1": r["n1"], "n2": r["n2"], "lines": r["lines"]}

    @staticmethod
    def peaks(p):
        return _xrd_peaks(p)

    @staticmethod
    def counts(x, p, pk, i):
        return _xrd_counts(x, p, pk, i)


def _xrd_a(p: dict) -> float:
    return p["a1"]


def _lsq_a(rows: list[dict], p: dict) -> float:
    pts = _rows(rows, ["N", "s2"])
    sn = sd = 0.0
    for n, s2 in pts:
        sn += n * s2
        sd += n * n
    if sn <= 0 or sd <= 0:
        return 0.0
    return p["lam"] / (2.0 * math.sqrt(sn / sd))


# ====================================================================================== X-ray reflectivity (Parratt)
def _delta(rho: float, ze: float, lam: float) -> float:
    return RE * lam * lam * (NA * rho * 1000.0 * ze) / (2.0 * PI)


def _csqrt(z: complex) -> complex:
    m = math.hypot(z.real, z.imag)
    sr = math.sqrt((m + z.real) / 2.0)
    si = math.sqrt(max((m - z.real) / 2.0, 0.0))
    return complex(sr, -si if z.imag < 0 else si)


def _xrr_layers(p: dict) -> list[tuple]:
    lam = p["lam"]
    df = _delta(p["rho_f"], p["ze_f"], lam)
    db = _delta(p["rho_b"], p["ze_b"], lam)
    ds = _delta(p["rho_s"], p["ze_s"], lam)
    bf = p["bfrac"]
    if int(round(p["kind"])) == 1:
        return [(df, df * bf, p["d1"]), (ds, ds * bf, 0.0)]
    out = []
    for _ in range(int(round(p["nrep"]))):
        out.append((df, df * bf, p["d1"] * p["fa"]))
        out.append((db, db * bf, p["d1"] * (1.0 - p["fa"])))
    out.append((ds, ds * bf, 0.0))
    return out


def _parratt(theta: float, lay: list[tuple], lam: float, sig: float) -> float:
    k = 2.0 * PI / lam
    s2 = math.sin(theta) ** 2
    kz = [k * _csqrt(complex(s2, 0.0))]
    for d, b, _t in lay:
        kz.append(k * _csqrt(complex(s2 - 2.0 * d, 2.0 * b)))
    n = len(lay)
    x = complex(0.0, 0.0)
    for j in range(n - 1, -1, -1):
        # interface j / j+1 (layer index j in kz, layer j+1 below it)
        r = (kz[j] - kz[j + 1]) / (kz[j] + kz[j + 1]) * cmath.exp(-2.0 * kz[j] * kz[j + 1] * sig * sig)
        if j + 1 <= n - 1:
            ph = cmath.exp(2j * kz[j + 1] * lay[j][2])
        else:
            ph = complex(0.0, 0.0)
        x = (r + x * ph) / (1.0 + r * x * ph)
    return abs(x) ** 2


def _peakpos(y: list[float], i: int, w: int) -> float:
    """Sub-sample position of a maximum: least-squares parabola over 2w+1 points around index i."""
    s2 = s4 = 0.0
    for u in range(-w, w + 1):
        s2 += u * u
        s4 += u ** 4
    n = 2 * w + 1
    sy = suy = su2y = 0.0
    for u in range(-w, w + 1):
        v = y[i + u]
        sy += v
        suy += u * v
        su2y += u * u * v
    c1 = suy / s2
    c2 = (n * su2y - s2 * sy) / (n * s4 - s2 * s2)
    if c2 >= 0:
        return float(i)
    off = -c1 / (2.0 * c2)
    if off > w:
        off = float(w)
    if off < -w:
        off = float(-w)
    return i + off


def _xrr_scan(p: dict) -> tuple[list[float], list[float]]:
    lay = _xrr_layers(p)
    n = int(round((p["tmax"] - p["tmin"]) / 0.01)) + 1
    xs, ys = [], []
    for i in range(n):
        x = p["tmin"] + 0.01 * i
        r = _parratt(x * D2R / 2.0, lay, p["lam"], p["sig"])
        r = r * (1.0 + 0.004 * _g(i, int(p["seed"]))) + p["bgr"]
        xs.append(x)
        ys.append(r)
    return xs, ys


def _xrr_fit(p: dict) -> dict:
    xs, ys = _xrr_scan(p)
    n = len(ys)
    ly = [math.log10(max(v, 1e-12)) for v in ys]
    tthc = xs[0]
    for i in range(n):
        if ys[i] < 0.5:
            tthc = xs[i]
            break
    w = 4
    mx = []
    for i in range(w, n - w):
        v = ly[i]
        ok = True
        for j in range(i - w, i):
            if ly[j] >= v:
                ok = False
                break
        if ok:
            for j in range(i + 1, i + w + 1):
                if ly[j] > v:
                    ok = False
                    break
        if ok and xs[i] > 1.3 * tthc:
            mx.append(i)
    kind = int(round(p["kind"]))
    if kind == 2 and mx:
        keep = []
        for i in mx:
            dom = True
            for j in mx:
                if j != i and abs(xs[j] - xs[i]) <= 0.5 and ys[j] * 3.0 > ys[i]:
                    dom = False
                    break
            if dom:
                keep.append(i)
        mx = keep
    out = {"d": 0.0, "rho": 0.0, "m0": 0.0, "peaks": float(len(mx)), "tthc": tthc}
    if len(mx) < 3:
        return out
    pos = []
    for i in mx:
        q = _peakpos(ly, i, 3)
        i0 = int(math.floor(q))
        fr = q - i0
        t = xs[i0] + fr * 0.01
        pos.append(math.sin(t * D2R / 2.0) ** 2)
    best = None
    for h2 in range(0, 121):
        m0 = h2 * 0.5
        pts = [[(m0 + i) ** 2, pos[i]] for i in range(len(pos))]
        a, b = _line(pts)
        if a <= 0:
            continue
        sse = 0.0
        for x, y in pts:
            sse += (y - a * x - b) ** 2
        if best is None or sse < best[0] - 1e-18:
            best = (sse, m0, a, b)
    if best is None:
        return out
    _sse, m0, a, b = best
    out["m0"] = m0
    out["d"] = p["lam"] / (2.0 * math.sqrt(a))
    out["rho"] = (b / 2.0) * 2.0 * PI / (RE * p["lam"] ** 2 * NA * 1000.0 * p["ze_f"]) / 1000.0 if b > 0 else 0.0
    return out


class Xrr(_Base):
    """X-ray reflectivity of a film (kind 1) or a multilayer (kind 2) on silicon: exact Parratt recursion with
    Nevot-Croce roughness. 2theta in degrees; absorption beta = bfrac x delta (illustrative)."""

    PARAMS = {"tth": 2.0, "lam": 1.5406e-10, "kind": 1.0, "d1": 4.0e-8, "fa": 0.4, "nrep": 10.0,
              "rho_f": 19300.0, "ze_f": 0.40106, "rho_b": 2329.0, "ze_b": 0.49848, "rho_s": 2329.0, "ze_s": 0.49848,
              "sig": 4.0e-10, "bfrac": 0.05, "bgr": 1.0e-8, "seed": 11.0, "tmin": 0.1, "tmax": 5.0}
    VARS = ["t", "R", "logR", "tth"]

    @staticmethod
    def view(s, p, cfg=None):
        r = _parratt(p["tth"] * D2R / 2.0, _xrr_layers(p), p["lam"], p["sig"]) + p["bgr"]
        return {"t": s.get("t", 0.0), "R": r, "logR": math.log10(max(r, 1e-12)), "tth": p["tth"]}

    @staticmethod
    def measure(p, cfg=None):
        r = _xrr_fit(p)
        return {"d": r["d"], "rho": r["rho"], "m0": r["m0"], "peaks": r["peaks"], "tthc": r["tthc"]}

    @staticmethod
    def refl(tth, p):
        return _parratt(tth * D2R / 2.0, _xrr_layers(p), p["lam"], p["sig"])


def _xrr_d(p: dict) -> float:
    return p["d1"]


def _fringe_d(rows: list[dict], p: dict) -> float:
    pts = _rows(rows, ["m", "s2"])
    a, _b = _line([[m * m, s] for m, s in pts])
    return p["lam"] / (2.0 * math.sqrt(a)) if a > 0 else 0.0


# ====================================================================================== quartz crystal monitor
class Qcm(_Base):
    """A quartz crystal thickness monitor: the film on the crystal lowers its frequency by the Sauerbrey relation
    df = -2 f0^2 rho_f d / sqrt(rho_q mu_q). The substrate sees tool x the thickness the crystal sees."""

    PARAMS = {"t": 0.0, "f0": 6.0e6, "rho_f": 19300.0, "rate": 2.0e-10, "tool": 0.8, "Tdep": 300.0,
              "rho_q": 2648.0, "mu_q": 2.947e10, "seed": 5.0}
    VARS = ["t", "f", "df", "thick_nm"]

    @staticmethod
    def sens(p: dict) -> float:
        return 2.0 * p["f0"] ** 2 / math.sqrt(p["rho_q"] * p["mu_q"])

    @staticmethod
    def freq(p: dict, t: float) -> float:
        th = p["rate"] * t
        return p["f0"] - Qcm.sens(p) * p["rho_f"] * th + 0.4 * _g(int(round(t * 10.0)), int(p["seed"]))

    @staticmethod
    def view(s, p, cfg=None):
        f = Qcm.freq(p, p["t"])
        return {"t": s.get("t", 0.0), "f": f, "df": f - p["f0"], "thick_nm": p["rate"] * p["t"] * 1e9}

    @staticmethod
    def measure(p, cfg=None):
        pts = []
        for i in range(1, 9):
            t = 10.0 * i
            pts.append([t, Qcm.freq(p, t)])
        m, _c = _line(pts)
        rate = -m / (Qcm.sens(p) * p["rho_f"])
        step = p["tool"] * p["rate"] * p["Tdep"]
        tool = step / (rate * p["Tdep"]) if rate != 0 else 0.0
        return {"rate": rate, "tool": tool, "thick": rate * p["Tdep"], "step": step}


def _qcm_rate(p: dict) -> float:
    return p["rate"]


def _qcm_calc(rows: list[dict], p: dict) -> float:
    m, _c = _line(_rows(rows, ["t", "f"]))
    d = Qcm.sens(p) * p["rho_f"]
    return -m / d if d != 0 else 0.0


# ====================================================================================== high-vacuum pump-down
class Vac(_Base):
    """V dP/dt = -S P + Q(t). Stage 0: rotary roughing from atmosphere; stage 1: high-vacuum pump through a tube of
    conductance C (S = Sp C / (Sp + C)) with a leak QL and an outgassing QO exp(-t/tau_o); stage 2: the pump isolated
    at time tc (a rate-of-rise test)."""

    PARAMS = {"t": 0.0, "stage": 1.0, "V": 0.05, "Sr": 0.0028, "Sp": 0.20, "dt": 0.04, "Lt": 0.30, "T": 293.0,
              "Mgas": 28.96, "Pat": 101325.0, "Px": 10.0, "Pur": 1.0, "QL": 5.0e-6, "QO": 1.0e-4, "tauo": 120.0,
              "tc": 900.0}
    VARS = ["t", "P", "logP", "S", "C"]

    @staticmethod
    def cond(p: dict) -> float:
        vb = math.sqrt(8.0 * KB * p["T"] / (PI * p["Mgas"] * AMU))
        return PI / 12.0 * vb * p["dt"] ** 3 / p["Lt"]

    @staticmethod
    def seff(p: dict) -> float:
        c = Vac.cond(p)
        return p["Sp"] * c / (p["Sp"] + c)

    @staticmethod
    def p1(p: dict, t: float) -> float:
        s = Vac.seff(p)
        lam = s / p["V"]
        pinf = p["QL"] / s
        a = p["QO"] / (p["V"] * (lam - 1.0 / p["tauo"]))
        return pinf + (p["Px"] - pinf - a) * math.exp(-lam * t) + a * math.exp(-t / p["tauo"])

    @staticmethod
    def pressure(p: dict) -> float:
        st = int(round(p["stage"]))
        t = p["t"]
        if st == 0:
            return p["Pur"] + (p["Pat"] - p["Pur"]) * math.exp(-p["Sr"] * t / p["V"])
        if st == 1:
            return Vac.p1(p, t)
        pc = Vac.p1(p, p["tc"])
        return (pc + p["QL"] / p["V"] * t
                + p["QO"] * p["tauo"] / p["V"] * math.exp(-p["tc"] / p["tauo"]) * (1.0 - math.exp(-t / p["tauo"])))

    @staticmethod
    def view(s, p, cfg=None):
        pr = Vac.pressure(p)
        return {"t": s.get("t", 0.0), "P": pr, "logP": math.log10(pr), "S": Vac.seff(p), "C": Vac.cond(p)}

    @staticmethod
    def measure(p, cfg=None):
        q = dict(p, stage=1.0)
        pts = []
        for i in range(1, 7):
            q["t"] = float(i)
            pts.append([float(i), math.log(Vac.pressure(q))])
        m, _c = _line(pts)
        s_eff = -p["V"] * m
        c = 1.0 / (1.0 / s_eff - 1.0 / p["Sp"]) if (1.0 / s_eff - 1.0 / p["Sp"]) > 0 else 0.0
        late = dict(p, stage=2.0, tc=1800.0)
        pl = []
        for u in (20.0, 60.0, 100.0, 140.0):
            late["t"] = u
            pl.append([u, Vac.pressure(late)])
        ql = p["V"] * _line(pl)[0]
        early = dict(p, stage=2.0, tc=200.0)
        pe = []
        for u in (10.0, 30.0, 50.0):
            early["t"] = u
            pe.append([u, Vac.pressure(early)])
        qe = p["V"] * _line(pe)[0]
        return {"C": c, "S": s_eff, "QL": ql, "Qout": qe - ql}


def _vac_C(p: dict) -> float:
    return Vac.cond(p)


def _vac_calc(rows: list[dict], p: dict) -> float:
    pts = _rows(rows, ["t", "lnP"])
    m, _c = _line(pts)
    s = -p["V"] * m
    inv = (1.0 / s - 1.0 / p["Sp"]) if s != 0 else 0.0
    return 1.0 / inv if inv > 0 else 0.0


# ====================================================================================== sheet resistance
def _vdp_x(rs: float, r: float) -> float:
    lo, hi = 0.0, rs
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if math.exp(-PI * r * mid / rs) + math.exp(-PI * mid / rs) - 1.0 > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _vdp_solve(r1: float, r2: float) -> float:
    s = r1 + r2
    if s <= 0:
        return 0.0
    lo, hi = 0.01 * s, 100.0 * s
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if math.exp(-PI * r1 / mid) + math.exp(-PI * r2 / mid) - 1.0 > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


class Sheet(_Base):
    """mode 0 = van der Pauw (sel 0: R_AB,CD; sel 1: R_BC,DA), mode 1 = collinear four-point probe on a large film.
    A thermo-EMF offset Voff rides on every voltage; reversing the current cancels it."""

    PARAMS = {"mode": 0.0, "sel": 0.0, "Rs": 95.0, "t": 5.25e-4, "r": 1.18, "I": 1.0e-3, "Voff": 3.5e-6}
    VARS = ["t", "V", "Vrev", "R"]

    @staticmethod
    def res(p: dict) -> float:
        if int(round(p["mode"])) == 1:
            return p["Rs"] * math.log(2.0) / PI
        x = _vdp_x(p["Rs"], p["r"])
        return p["r"] * x if int(round(p["sel"])) == 0 else x

    @staticmethod
    def view(s, p, cfg=None):
        r = Sheet.res(p)
        v = p["I"] * r + p["Voff"]
        vr = -p["I"] * r + p["Voff"]
        return {"t": s.get("t", 0.0), "V": v, "Vrev": vr, "R": (v - vr) / (2.0 * p["I"])}

    @staticmethod
    def measure(p, cfg=None):
        if int(round(p["mode"])) == 1:
            pts = []
            for i in range(1, 6):
                q = dict(p, I=1.0e-3 * i)
                v = Sheet.view({}, q)
                pts.append([q["I"], v["V"]])
            m, _c = _line(pts)
            rs = m * PI / math.log(2.0)
        else:
            a = Sheet.view({}, dict(p, sel=0.0))["R"]
            b = Sheet.view({}, dict(p, sel=1.0))["R"]
            rs = _vdp_solve(a, b)
        return {"Rs": rs, "rho": rs * p["t"]}


def _sheet_Rs(p: dict) -> float:
    return p["Rs"]


def _vdp_calc(rows: list[dict], p: dict) -> float:
    pts = _rows(rows, ["R1", "R2"])
    if not pts:
        return 0.0
    r1 = sum(a for a, _ in pts) / len(pts)
    r2 = sum(b for _, b in pts) / len(pts)
    return _vdp_solve(r1, r2) if r1 > 0 and r2 > 0 else 0.0


def _fpp_calc(rows: list[dict], p: dict) -> float:
    m, _c = _line(_rows(rows, ["I", "V"]))
    return m * PI / math.log(2.0)


# ====================================================================================== Haynes-Shockley
class Hs(_Base):
    """Minority carriers injected at an emitter drift in a field E and spread by diffusion; the collector sees
    n(t) = N exp(-t/tau) / sqrt(4 pi D t) exp(-(L - mu E t)^2 / (4 D t)).  D = mu kT / q (Einstein)."""

    PARAMS = {"t": 0.0, "L": 0.01, "E": 2000.0, "mu": 0.19, "T": 300.0, "tau": 1.0e-4, "N": 1.0e-3, "gain": 50.0}
    VARS = ["t", "V", "td"]

    @staticmethod
    def diff(p: dict) -> float:
        return p["mu"] * KB * p["T"] / QE

    @staticmethod
    def sig(p: dict, t: float) -> float:
        if t <= 0:
            return 0.0
        d = Hs.diff(p)
        v = p["mu"] * p["E"]
        n = p["N"] * math.exp(-t / p["tau"]) / math.sqrt(4.0 * PI * d * t) * math.exp(-(p["L"] - v * t) ** 2 / (4.0 * d * t))
        return p["gain"] * n

    @staticmethod
    def view(s, p, cfg=None):
        return {"t": s.get("t", 0.0), "V": Hs.sig(p, p["t"]), "td": p["L"] / (p["mu"] * p["E"])}

    @staticmethod
    def pulse(p: dict) -> dict:
        """Scan the collector signal numerically: peak time, full width at half maximum, area."""
        td0 = p["L"] / (p["mu"] * p["E"])
        n = 2400
        t0, t1 = 0.3 * td0, 2.2 * td0
        dt = (t1 - t0) / (n - 1)
        ts, ys = [], []
        for i in range(n):
            t = t0 + dt * i
            ts.append(t)
            ys.append(Hs.sig(p, t))
        im = 0
        for i in range(n):
            if ys[i] > ys[im]:
                im = i
        im = min(max(im, 1), n - 2)
        y0, y1, y2 = ys[im - 1], ys[im], ys[im + 1]
        den = y0 - 2.0 * y1 + y2
        off = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        tpk = ts[im] + off * dt
        hm = 0.5 * y1
        l = im
        while l > 0 and ys[l] > hm:
            l -= 1
        r = im
        while r < n - 1 and ys[r] > hm:
            r += 1
        tl = ts[l] + (hm - ys[l]) / (ys[l + 1] - ys[l]) * dt
        tr = ts[r] - (hm - ys[r]) / (ys[r - 1] - ys[r]) * dt
        area = 0.0
        for i in range(n - 1):
            area += 0.5 * (ys[i] + ys[i + 1]) * dt
        return {"tpk": tpk, "fwhm": tr - tl, "area": area, "peak": y1}

    @staticmethod
    def measure(p, cfg=None):
        se = sv = 0.0
        tdl, lav = [], []
        dres = 0.0
        for e in (1000.0, 1500.0, 2000.0, 2500.0, 3000.0):
            q = dict(p, E=e)
            r = Hs.pulse(q)
            v = p["L"] / r["tpk"]
            se += e * e
            sv += v * e
            tdl.append(r["tpk"])
            lav.append(math.log(r["area"] * v))
            if e == 2000.0:
                sg = r["fwhm"] / 2.3548200450309493
                dres = sg * sg * v * v / (2.0 * r["tpk"])
        mu = sv / se
        m, _c = _line([[tdl[i], lav[i]] for i in range(len(tdl))])
        tau = -1.0 / m if m < 0 else 0.0
        return {"mu": mu, "D": dres, "tau": tau}


def _hs_mu(p: dict) -> float:
    return p["mu"]


def _hs_calc(rows: list[dict], p: dict) -> float:
    pts = _rows(rows, ["E", "v"])
    se = sv = 0.0
    for e, v in pts:
        se += e * e
        sv += v * e
    return sv / se if se > 0 else 0.0


# ====================================================================================== solar cell
def _sc_cur(v: float, p: dict) -> float:
    vt = KB * p["T"] / QE
    iph = p["Jsc1"] * p["A"] * p["G"] / 1000.0
    i0 = p["J0"] * p["A"]
    rs = p["rs"] / p["A"]
    rsh = p["rsh"] / p["A"]
    lo, hi = -100.0, iph + 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        ex = (v + mid * rs) / (p["n"] * vt)
        if ex > 700.0:
            ex = 700.0
        f = iph - i0 * (math.exp(ex) - 1.0) - (v + mid * rs) / rsh - mid
        if f > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _sc_sweep(p: dict, dv: float) -> dict:
    i0 = _sc_cur(0.0, p)
    vs, is_ = [0.0], [i0]
    voc = 0.0
    k = 0
    while True:
        k += 1
        v = dv * k
        i = _sc_cur(v, p)
        if i <= 0.0 or k > 4000:
            pi_, vi_ = is_[-1], vs[-1]
            voc = vi_ + pi_ / (pi_ - i) * dv if pi_ != i else vi_
            break
        vs.append(v)
        is_.append(i)
    pw = [vs[j] * is_[j] for j in range(len(vs))]
    im = 0
    for j in range(len(pw)):
        if pw[j] > pw[im]:
            im = j
    im = min(max(im, 1), len(pw) - 2)
    y0, y1, y2 = pw[im - 1], pw[im], pw[im + 1]
    den = y0 - 2.0 * y1 + y2
    off = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    pmax = y1 - 0.25 * (y0 - y2) * off
    return {"Voc": voc, "Isc": i0, "Pmax": pmax, "FF": pmax / (voc * i0), "eta": pmax / (p["G"] * p["A"]),
            "Vmp": vs[im] + off * dv}


class Solar(_Base):
    """Single-diode cell: I = Iph - I0 (exp((V + I Rs)/(n Vt)) - 1) - (V + I Rs)/Rsh, Iph = Jsc1 A G / 1000."""

    PARAMS = {"V": 0.0, "G": 1000.0, "A": 4.0e-4, "Jsc1": 400.0, "n": 1.2, "J0": 1.0e-7, "rs": 5.0e-5, "rsh": 0.1, "T": 300.0}
    VARS = ["t", "I", "Pw", "V"]

    @staticmethod
    def view(s, p, cfg=None):
        i = _sc_cur(p["V"], p)
        return {"t": s.get("t", 0.0), "I": i, "Pw": p["V"] * i, "V": p["V"]}

    @staticmethod
    def measure(p, cfg=None):
        r = _sc_sweep(p, 0.0025)
        return {"Voc": r["Voc"], "Isc": r["Isc"], "Pmax": r["Pmax"], "FF": r["FF"], "eta": r["eta"]}

    @staticmethod
    def exact(p):
        return _sc_sweep(p, 0.0005)


def _sc_Voc(p: dict) -> float:
    vt = KB * p["T"] / QE
    return p["n"] * vt * math.log(p["Jsc1"] * p["G"] / 1000.0 / p["J0"] + 1.0)


def _sc_eta(rows: list[dict], p: dict) -> float:
    pts = _rows(rows, ["V", "I"])
    pm = 0.0
    for v, i in pts:
        if v * i > pm:
            pm = v * i
    return pm / (p["G"] * p["A"]) if p["G"] * p["A"] > 0 else 0.0


# ====================================================================================== registry
KERNELS: dict[str, Any] = {"ph2_xrd": Xrd, "ph2_xrr": Xrr, "ph2_qcm": Qcm, "ph2_vac": Vac, "ph2_sheet": Sheet,
                           "ph2_hs": Hs, "ph2_solar": Solar}
FAMILY = {"ph2_xrd": "optics", "ph2_xrr": "optics", "ph2_qcm": "thermo", "ph2_vac": "thermo", "ph2_sheet": "em",
          "ph2_hs": "em", "ph2_solar": "em"}

TEXTBOOK = {"ph2_a": _xrd_a, "ph2_d": _xrr_d, "ph2_rate": _qcm_rate, "ph2_C": _vac_C, "ph2_Rs": _sheet_Rs,
            "ph2_mu": _hs_mu, "ph2_Voc": _sc_Voc}

CALCS: dict[str, dict] = {
    "ph2_lsq_a": {"label": "lattice parameter", "unit": "m", "needs": ["N", "s2"], "fn": _lsq_a},
    "ph2_fringe": {"label": "film thickness", "unit": "m", "needs": ["m", "s2"], "fn": _fringe_d},
    "ph2_sauerbrey": {"label": "deposition rate", "unit": "m/s", "needs": ["t", "f"], "fn": _qcm_calc},
    "ph2_conductance": {"label": "tube conductance", "unit": "m3/s", "needs": ["t", "lnP"], "fn": _vac_calc},
    "ph2_vdp": {"label": "sheet resistance", "unit": "ohm", "needs": ["R1", "R2"], "fn": _vdp_calc},
    "ph2_fpp": {"label": "sheet resistance", "unit": "ohm", "needs": ["I", "V"], "fn": _fpp_calc},
    "ph2_drift": {"label": "drift mobility", "unit": "m2/Vs", "needs": ["E", "v"], "fn": _hs_calc},
    "ph2_eta": {"label": "efficiency", "unit": "", "needs": ["V", "I"], "fn": _sc_eta},
}
