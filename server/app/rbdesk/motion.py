"""A move worked out the way a motion controller plans it: for each axis or joint, a trapezoidal velocity profile (speed and
acceleration limits) or an S-curve (a jerk limit too), whether it reaches full speed, how long each phase lasts, and the peak speed
it really reaches. With several axes, all finish together: the slowest sets the time and the others are slowed to match. With the
load's inertia (or mass) and the drive's torque (or force), it checks the drive can give the acceleration asked."""
from __future__ import annotations

import math
import re
from typing import Any


class MotionError(ValueError):
    pass


_U = {"m": ("m", 1.0), "mm": ("m", 0.001), "cm": ("m", 0.01), "deg": ("deg", 1.0), "°": ("deg", 1.0), "rad": ("deg", 180 / math.pi), "rev": ("deg", 360.0)}
G = 9.80665


def _num(v: str, what: str, line: int) -> float:
    m = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*([a-z°/0-9^]*)\s*", v, re.I)
    if not m:
        raise MotionError(f"Line {line}: {what} '{v}' is not a number.")
    return float(m.group(1))


def _ta(v: float, a: float, j: float | None) -> float:
    """Time to go from rest to v (and the same back to rest)."""
    if not j:
        return v / a
    return v / a + a / j if v >= a * a / j else 2 * math.sqrt(v / j)


def plan(d: float, v: float, a: float, j: float | None) -> dict[str, Any]:
    d = abs(d)
    if d == 0:
        return {"T": 0.0, "vp": 0.0, "ap": 0.0, "Ta": 0.0, "Tv": 0.0, "Tj": 0.0, "full": True}
    ta = _ta(v, a, j)
    if v * ta > d * (1 + 1e-9):
        lo, hi = 0.0, v
        for _ in range(200):
            mid = (lo + hi) / 2
            if mid * _ta(mid, a, j) > d:
                hi = mid
            else:
                lo = mid
        vp = lo
        ta = _ta(vp, a, j)
        tv = 0.0
        full = False
    else:
        vp, tv, full = v, (d - v * ta) / v, True
    if j:
        tj = a / j if vp >= a * a / j else math.sqrt(vp / j)
        ap = min(a, j * tj)
    else:
        tj, ap = 0.0, a
    return {"T": 2 * ta + tv, "vp": vp, "ap": ap, "Ta": ta, "Tv": tv, "Tj": tj, "full": full}


def stretch(d: float, T: float, a: float, j: float | None, vmax: float) -> float:
    """The lower speed that makes this axis take exactly T."""
    lo, hi = 1e-12, vmax
    for _ in range(200):
        mid = (lo + hi) / 2
        if plan(d, mid, a, j)["T"] > T:
            lo = mid
        else:
            hi = mid
    return hi


def profile(p: dict[str, Any], d: float, n: int = 160) -> list[list[float]]:
    """Velocity against time, sampled."""
    T, ta, tv, tj, vp, ap = p["T"], p["Ta"], p["Tv"], p["Tj"], p["vp"], p["ap"]
    if T <= 0:
        return [[0.0, 0.0]]

    def acc_v(t: float) -> float:   # rising part from rest to vp over ta
        if not tj:
            return min(vp, ap * t)
        if t <= tj:
            return 0.5 * (ap / tj) * t * t
        tc = ta - 2 * tj
        if t <= tj + tc:
            return 0.5 * ap * tj + ap * (t - tj)
        r = ta - t
        return vp - 0.5 * (ap / tj) * r * r

    out = []
    for k in range(n + 1):
        t = T * k / n
        if t <= ta:
            v = acc_v(t)
        elif t <= ta + tv:
            v = vp
        else:
            v = acc_v(max(0.0, T - t))
        out.append([round(t, 6), round(v * (1 if d >= 0 else -1), 6)])
    return out


def analyse(text: str, sync: bool = True) -> dict[str, Any]:
    axes: list[dict[str, Any]] = []
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        s = raw.split("#")[0].strip()
        if not s:
            continue
        toks = s.replace(",", " ").split()
        name = toks[0]
        kv: dict[str, str] = {}
        dist = None
        unit = None
        for t in toks[1:]:
            if "=" in t:
                k, v = t.split("=", 1)
                kv[k.lower()] = v
            elif dist is None:
                m = re.fullmatch(r"([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*(m|mm|cm|deg|°|rad|rev)?", t, re.I)
                if not m:
                    raise MotionError(f"Line {n}: '{t}' - give the distance as a number with m, mm, deg or rad.")
                dist, unit = float(m.group(1)), (m.group(2) or "m").lower()
        if dist is None:
            raise MotionError(f"Line {n}: the move's distance is missing - e.g. 'x 0.5m vmax=1 amax=2'.")
        base, f = _U[unit]
        bad = set(kv) - {"vmax", "v", "amax", "a", "jerk", "j", "inertia", "torque", "mass", "force", "vertical", "gear", "friction"}
        if bad:
            raise MotionError(f"Line {n}: {', '.join(sorted(bad))} - use vmax=, amax=, jerk=, inertia= / mass=, torque= / force=, gear=, vertical=1.")
        v = kv.get("vmax", kv.get("v"))
        a = kv.get("amax", kv.get("a"))
        if v is None or a is None:
            raise MotionError(f"Line {n}: give vmax= and amax= (in {base}/s and {base}/s², in the same unit as the distance).")
        vv, aa = _num(v, "vmax", n) * f, _num(a, "amax", n) * f
        jj = _num(kv.get("jerk", kv.get("j")), "jerk", n) * f if kv.get("jerk", kv.get("j")) else None
        if vv <= 0 or aa <= 0 or (jj is not None and jj <= 0):
            raise MotionError(f"Line {n}: speed, acceleration and jerk must be above 0.")
        ax = {"name": name, "line": n, "unit": base, "d": dist * f, "vmax": vv, "amax": aa, "jerk": jj}
        for k in ("inertia", "torque", "mass", "force", "gear", "friction"):
            if k in kv:
                ax[k] = _num(kv[k], k, n)
        ax["vertical"] = kv.get("vertical", "0") in ("1", "yes", "true", "y")
        axes.append(ax)
    if not axes:
        raise MotionError("One axis per line: name, distance, vmax=, amax= (and jerk= for an S-curve) - e.g. 'x 0.5m vmax=1 amax=2 jerk=20'.")
    if len(axes) > 16:
        raise MotionError("Up to 16 axes.")
    for ax in axes:
        ax["plan"] = plan(ax["d"], ax["vmax"], ax["amax"], ax["jerk"])
    T = max(ax["plan"]["T"] for ax in axes)
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", name="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": name})   # noqa: E731
    rows = []
    for ax in axes:
        p0 = ax["plan"]
        p = p0
        scaled = None
        if sync and len(axes) > 1 and p0["T"] < T - 1e-9 and ax["d"]:
            scaled = stretch(ax["d"], T, ax["amax"], ax["jerk"], ax["vmax"])
            p = plan(ax["d"], scaled, ax["amax"], ax["jerk"])
        ax["used"] = p
        u = ax["unit"]
        if not p0["full"] and ax["d"]:
            add("info", "Speed", f"{ax['name']} never reaches its {ax['vmax']:g} {u}/s: the move is too short - it peaks at {p0['vp']:.4g} {u}/s.", "", ax["name"])
        need = None
        if "inertia" in ax or "mass" in ax:
            a_si = p["ap"] * (math.pi / 180 if u == "deg" else 1)
            gear = ax.get("gear") or 1.0
            if u == "deg":
                need = ax.get("inertia", 0) * a_si / gear + (ax.get("friction") or 0)
                have, unit_f = ax.get("torque"), "N·m"
            else:
                need = ax.get("mass", 0) * (a_si + (G if ax["vertical"] else 0)) + (ax.get("friction") or 0)
                have, unit_f = ax.get("force"), "N"
            ax["need"] = {"value": need, "unit": unit_f, "have": have}
            if have is not None:
                if need > have:
                    add("bad", "Drive", f"{ax['name']} needs {need:.3g} {unit_f} to accelerate at {p['ap']:.3g} {u}/s² but the drive gives {have:g} {unit_f}.",
                        f"Lower amax to about {ax['amax'] * have / need * 0.9:.3g} {u}/s², add gearing, or a bigger drive.", ax["name"])
                elif need > 0.8 * have:
                    add("warn", "Drive", f"{ax['name']} uses {need / have * 100:.0f}% of its drive's {unit_f} just to accelerate - little left for disturbances.", "Keep about 20-30% in reserve.", ax["name"])
        rows.append({"name": ax["name"], "unit": u, "d": ax["d"], "vmax": ax["vmax"], "amax": ax["amax"], "jerk": ax["jerk"], "T": p0["T"],
                     "scaled_v": scaled, "vp": p["vp"], "ap": p["ap"], "Ta": p["Ta"], "Tv": p["Tv"], "Tj": p["Tj"], "full": p["full"],
                     "need": ax.get("need"), "curve": profile(p, ax["d"])})
    if any(ax["jerk"] is None for ax in axes):
        add("info", "Jerk", "Axes without a jerk limit start and stop their acceleration instantly - that excites vibration in arms and belts.", "Add jerk= for an S-curve (often 10-50 times amax).")
    slowest = max(axes, key=lambda ax: ax["plan"]["T"])
    out = {"T": T, "axes": rows, "sync": sync, "slowest": slowest["name"], "issues": issues}
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    out["verdict"] = f"The move takes {T:.4g} s" + (f", set by {slowest['name']}" if len(axes) > 1 else "") + (f" - {out['counts']['bad']} drive limit{'s' if out['counts']['bad'] > 1 else ''} exceeded" if out["counts"]["bad"] else "")
    out["note"] = ("A planned profile from rest to rest. The real move adds the controller's tracking lag; torque needs cover acceleration "
                   "(and gravity for a vertical axis) only - add friction= and check against the drive's datasheet.")
    return out
