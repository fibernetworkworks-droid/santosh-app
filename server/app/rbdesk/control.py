"""A control loop worked out from a recorded step response: rise time, overshoot, settling time and steady-state error; for an
open-loop step, a first-order-plus-dead-time model fitted from the 28% and 63% points (Smith's method) and PI / PID gains from it -
SIMC (Skogestad) tight and smooth, and Ziegler-Nichols' reaction curve for comparison - each simulated in closed loop on the fitted
model so the overshoot and settling it would give are shown before she tries it on the robot. Her current gains can be simulated
the same way. Gains come in both the ideal form (Kc, Ti, Td) and the parallel form (p, i, d) that ros2_control's PID uses."""
from __future__ import annotations

import math
import re
from typing import Any


class ControlError(ValueError):
    pass


def parse(text: str) -> dict[str, Any]:
    rows: list[list[float]] = []
    head: list[str] = []
    for ln in str(text or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p for p in re.split(r"[,;\t ]+", s) if p]
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            if not rows and not head:
                head = [p.lower() for p in parts]
                continue
            raise ControlError(f"'{s[:60]}' is not numbers.")
        if len(vals) < 2:
            raise ControlError("Each line: time, measured value (and optionally the setpoint or the command).")
        rows.append(vals[:3])
    if len(rows) < 10:
        raise ControlError("At least 10 samples: time, measured value - from before the step until it has settled.")
    if len({len(r) for r in rows}) != 1:
        raise ControlError("Every line needs the same number of columns.")
    t = [r[0] for r in rows]
    if any(b <= a for a, b in zip(t, t[1:])):
        raise ControlError("Time must go up on every line.")
    third = [r[2] for r in rows] if len(rows[0]) > 2 else None
    role = ""
    if third is not None:
        name = head[2] if len(head) > 2 else ""
        role = "input" if re.search(r"^(u|input|cmd|command|effort|duty|pwm|voltage|out)", name) else "setpoint"
    return {"t": t, "y": [r[1] for r in rows], "x": third, "role": role}


def _interp(t: list[float], y: list[float], level: float, start: int, rising: bool) -> float | None:
    for i in range(max(1, start), len(y)):
        a, b = y[i - 1], y[i]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            return t[i - 1] + (level - a) / (b - a) * (t[i] - t[i - 1]) if b != a else t[i]
    return None


def metrics(t: list[float], y: list[float], t0: float, y0: float, yf: float, target: float | None = None) -> dict[str, Any]:
    d = yf - y0
    if abs(d) < 1e-12:
        raise ControlError("The output did not move: no step to read.")
    up = d > 0
    i0 = next((i for i, v in enumerate(t) if v >= t0), 0)
    t10, t90 = _interp(t, y, y0 + 0.1 * d, i0, up), _interp(t, y, y0 + 0.9 * d, i0, up)
    peak = max(y[i0:]) if up else min(y[i0:])
    over = max(0.0, (peak - yf) / d * 100)
    band = 0.02 * abs(d)
    ts = None
    for i in range(len(y) - 1, i0 - 1, -1):
        if abs(y[i] - yf) > band:
            ts = t[i + 1] - t0 if i + 1 < len(t) else None
            break
    else:
        ts = 0.0
    cross, prev = 0, None
    for v in y[i0:]:
        s = v > yf
        if prev is not None and s != prev:
            cross += 1
        prev = s
    return {"rise": None if t10 is None or t90 is None else t90 - t10, "overshoot": over, "settle": ts, "peak": peak,
            "sse_pct": None if target is None or abs(target - y0) < 1e-12 else (target - yf) / (target - y0) * 100, "swings": cross // 2}


def fopdt(t: list[float], y: list[float], t0: float, y0: float, yf: float, du: float) -> dict[str, Any]:
    d = yf - y0
    up = d > 0
    i0 = next((i for i, v in enumerate(t) if v >= t0), 0)
    t28, t63 = _interp(t, y, y0 + 0.283 * d, i0, up), _interp(t, y, y0 + 0.632 * d, i0, up)
    if t28 is None or t63 is None:
        raise ControlError("The response never reaches 63% of its change - record longer.")
    tau = 1.5 * (t63 - t28)
    theta = max(0.0, (t63 - t0) - tau)
    if tau <= 0:
        raise ControlError("Could not fit a time constant - the response jumps in one sample; record faster.")
    K = d / du
    sim = [y0 + (d * (1 - math.exp(-(tt - t0 - theta) / tau)) if tt - t0 > theta else 0.0) for tt in t]
    rms = math.sqrt(sum((a - b) ** 2 for a, b in zip(sim, y)) / len(y)) / abs(d) * 100
    return {"K": K, "tau": tau, "theta": theta, "fit_pct": rms}


def simulate(K: float, tau: float, theta: float, kp: float, ki: float, kd: float, horizon: float | None = None, n_out: int = 240) -> dict[str, Any]:
    horizon = horizon or 8 * (tau + theta) + 1e-9
    dt = max(horizon / 20000, min(tau, theta if theta > 0 else tau) / 60)
    steps = int(horizon / dt) + 1
    delay = int(round(theta / dt))
    buf = [0.0] * (delay + 1)
    y = integ = 0.0
    tf = (kd / kp / 10) if kp and kd else 0.0
    dfilt = 0.0
    prev_y = 0.0
    out, iae = [], 0.0
    every = max(1, steps // n_out)
    for k in range(steps):
        e = 1.0 - y
        integ += e * dt
        dy = (y - prev_y) / dt
        dfilt = dfilt + (dt / (tf + dt)) * (dy - dfilt) if tf else dy
        u = kp * e + ki * integ - kd * dfilt
        prev_y = y
        buf.append(u)
        ud = buf.pop(0)
        y += dt * (K * ud - y) / tau
        if not math.isfinite(y) or abs(y) > 1e6:
            return {"stable": False, "trace": out, "dt": dt}
        iae += abs(e) * dt
        if k % every == 0:
            out.append([round(k * dt, 6), round(y, 5)])
    tt = [p[0] for p in out]
    yy = [p[1] for p in out]
    tail = yy[int(len(yy) * 0.85):]
    stable = (max(tail) - min(tail)) < 0.05 and abs(tail[-1] - 1) < 0.05
    m = metrics(tt, yy, 0.0, 0.0, 1.0, 1.0) if stable else {}
    return {"stable": stable, "trace": out, "overshoot": m.get("overshoot"), "settle": m.get("settle"), "rise": m.get("rise"), "iae": iae}


def tunings(K: float, tau: float, theta: float) -> list[dict[str, Any]]:
    out = []
    th = theta if theta > 0.05 * tau else 0.05 * tau
    for name, tc, note in (("SIMC tight", th, "Fast; the dead time sets how fast."), ("SIMC smooth", 3 * th, "Slower, gentle on the motors and robust to a wrong model.")):
        kc = tau / (K * (tc + theta))
        ti = min(tau, 4 * (tc + theta))
        out.append({"name": name, "form": "PI", "Kc": kc, "Ti": ti, "Td": 0.0, "note": note})
    if theta > 0:
        kc = 1.2 * tau / (K * theta)
        out.append({"name": "Ziegler-Nichols (reaction curve)", "form": "PID", "Kc": kc, "Ti": 2 * theta, "Td": 0.5 * theta,
                    "note": "The classic: aggressive, often 40-60% overshoot - shown for comparison."})
    for x in out:
        x.update(p=x["Kc"], i=x["Kc"] / x["Ti"] if x["Ti"] else 0.0, d=x["Kc"] * x["Td"])
    return out


def _f(v: Any, name: str) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ControlError(f"{name}: a number.")


def analyse(text: str, mode: str = "auto", u_step: Any = "", t_step: Any = "", kp: Any = "", ki: Any = "", kd: Any = "") -> dict[str, Any]:
    d = parse(text)
    t, y, x = d["t"], d["y"], d["x"]
    role = d["role"]
    if mode in ("open", "closed"):
        role = {"open": "input", "closed": "setpoint"}[mode] if x is not None else ("" if mode == "open" else "closed")
    elif mode not in ("auto", ""):
        raise ControlError("Kind: auto, open (the command stepped, loop open) or closed (the setpoint stepped, loop closed).")
    if mode == "closed" and x is None:
        raise ControlError("A closed-loop step needs the setpoint as a third column.")
    ts = _f(t_step, "Step time")
    if x is not None:
        first = x[0]
        i_s = next((i for i, v in enumerate(x) if abs(v - first) > 1e-9 * max(1.0, abs(first))), None)
        if i_s is None:
            raise ControlError("The third column never changes - no step in it.")
        t0 = ts if ts is not None else t[i_s]
        dx = x[-1] - first
    else:
        t0 = ts if ts is not None else t[0]
        dx = _f(u_step, "Step size") or 1.0
    pre = [v for tt, v in zip(t, y) if tt < t0] or [y[0]]
    y0 = sum(pre[-max(1, len(pre) // 3):]) / max(1, len(pre[-max(1, len(pre) // 3):]))
    n = len(y)
    yf = sum(y[-max(3, n // 20):]) / max(3, n // 20)
    closed = role == "setpoint"
    m = metrics(t, y, t0, y0, yf, x[-1] if closed else None)
    span = t[-1] - t0
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, txt, fix="": issues.append({"sev": sev, "area": area, "text": txt, "fix": fix})   # noqa: E731
    tail = y[-max(5, n // 10):]
    if (max(tail) - min(tail)) > 0.05 * abs(yf - y0):
        add("warn", "Data", "The end of the recording still moves by more than 5% of the step - it may not have settled, so every number below is rough.", "Record longer, until the value stops changing.")
    out: dict[str, Any] = {"closed": closed, "t0": t0, "y0": y0, "yf": yf, "step_in": dx, "samples": n, "span": span,
                           "dt": span / max(1, sum(1 for v in t if v >= t0)), "metrics": m}
    if closed:
        if m["overshoot"] > 20:
            add("warn", "Overshoot", f"{m['overshoot']:.0f}% overshoot - joints hit limits and payloads swing.", "Lower the proportional gain or the integral gain (raise Ti), or add some derivative.")
        if m["swings"] >= 5:
            add("bad", "Oscillation", f"It swings {m['swings']} times before settling: the loop is close to unstable.", "Cut the gains by a third, then raise them step by step.")
        elif m["swings"] >= 2:
            add("warn", "Oscillation", f"It swings {m['swings']} times before settling: the loop is lightly damped.", "Lower the proportional gain a little or add derivative action.")
        if m["sse_pct"] is not None and abs(m["sse_pct"]) > 2:
            add("warn", "Offset", f"It settles {m['sse_pct']:.1f}% short of the setpoint.", "Add integral action (an i gain), or check for a saturated command or friction it cannot beat.")
        if m["settle"] is None:
            add("warn", "Settling", "It never stays within 2% of its final value in this recording.", "")
    try:
        mdl = fopdt(t, y, t0, y0, yf, dx if dx else 1.0)
    except ControlError as e:
        mdl = None
        add("info", "Model", str(e))
    if mdl and not closed:
        out["model"] = mdl
        if mdl["fit_pct"] > 8:
            add("warn", "Model", f"The simple model fits only roughly ({mdl['fit_pct']:.1f}% average error) - the system has more than one lag or something nonlinear; treat the gains as a starting point.", "")
        if mdl["theta"] > 2 * mdl["tau"]:
            add("info", "Model", "The dead time is long against the time constant: PI control will be slow whatever the gains; a Smith predictor or feed-forward helps more.", "")
        tn = tunings(mdl["K"], mdl["tau"], mdl["theta"])
        for x_ in tn:
            s = simulate(mdl["K"], mdl["tau"], mdl["theta"], x_["p"], x_["i"], x_["d"])
            x_.update(stable=s["stable"], overshoot=s.get("overshoot"), settle=s.get("settle"), trace=s["trace"])
        out["tunings"] = tn
        if (mdl["K"] < 0):
            add("info", "Model", "The output moves the opposite way to the command (negative gain): flip the sign of the error or the gains.", "")
    elif mdl and closed:
        out["model_note"] = "A closed-loop step does not give the plant's own model; record an open-loop step (command stepped, controller off) to get tuning suggestions."
    gk = [_f(v, n_) for v, n_ in ((kp, "p gain"), (ki, "i gain"), (kd, "d gain"))]
    if any(v is not None for v in gk) and mdl and not closed:
        p_, i_, d_ = (v or 0.0 for v in gk)
        s = simulate(mdl["K"], mdl["tau"], mdl["theta"], p_, i_, d_)
        out["yours"] = {"p": p_, "i": i_, "d": d_, "stable": s["stable"], "overshoot": s.get("overshoot"), "settle": s.get("settle"), "trace": s["trace"]}
        if not s["stable"]:
            add("bad", "Your gains", "Your gains go unstable on the fitted model.", "Start from the SIMC smooth gains.")
        elif (s.get("overshoot") or 0) > 25:
            add("warn", "Your gains", f"Your gains give about {s['overshoot']:.0f}% overshoot on the fitted model.", "")
    step = max(1, n // 300)
    out["measured"] = [[round(t[i] - t0, 6), round((y[i] - y0) / (yf - y0), 5)] for i in range(0, n, step) if t[i] >= t0 - 0.05 * span]
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    fm = lambda v: "—" if v is None else f"{v:.3g} s"   # noqa: E731
    out["verdict"] = (("Closed loop: " if closed else "Open loop: ") + f"rise {fm(m['rise'])}, overshoot {m['overshoot']:.0f}%, settles in {fm(m['settle'])}"
                      + (f"; model gain {mdl['K']:.3g}, lag {mdl['tau']:.3g} s, dead time {mdl['theta']:.3g} s" if mdl and not closed else ""))
    out["note"] = ("Worked out from one recorded step. Gains come from a fitted first-order model and are checked on that model only - "
                   "try them on the real robot with small steps, limits on, and a hand on the stop.")
    return out
