"""Capacity, worked out in code.

- `forecast`: a series of (date, peak use) and her limit -> a least-squares trend, when the peak crosses her headroom line and the
  limit, how many weeks that leaves; the fit's r2 is shown so a weak trend is not trusted.
- `queue`: requests per second, time per request, servers -> utilisation and the wait an M/M/c queue predicts (Erlang C), and how
  fast the wait grows near 100 %. A model with random arrivals and service times, not her system - said."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from math import factorial
from typing import Any

MAX_ROWS = 20_000


class CapacityError(ValueError):
    pass


def _day(v: str) -> date:
    v = str(v).strip()
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(v[:10])
    except ValueError:
        raise CapacityError(f"A date I cannot read: {v[:30]} (use 2026-11-27).")


def read(text: str) -> list[tuple[date, float]]:
    rows = []
    for i, ln in enumerate(str(text or "").splitlines()[:MAX_ROWS + 1]):
        parts = [p.strip() for p in re.split(r"[,\t;]|\s{2,}|\s(?=[\d.]+\s*$)", ln.strip()) if p.strip()]
        if len(parts) < 2:
            continue
        try:
            v = float(parts[-1].rstrip("%"))
        except ValueError:
            if i == 0:
                continue
            raise CapacityError(f"Line {i + 1}: the use must be a number.")
        try:
            d = _day(parts[0])
        except CapacityError:
            if i == 0:
                continue
            raise
        rows.append((d, v))
    rows.sort()
    if len(rows) < 3:
        raise CapacityError("At least 3 dated values are needed: date, peak use.")
    return rows


def forecast(text: str, limit: Any, headroom: Any = 80, unit: str = "") -> dict[str, Any]:
    rows = read(text)
    try:
        L = float(limit)
    except (TypeError, ValueError):
        raise CapacityError("Limit: the most the system can take, in the same unit.")
    if L <= 0:
        raise CapacityError("Limit: more than 0.")
    h = float(str(headroom).rstrip("%") or 80)
    h = h / 100 if h > 1 else h
    if not 0.1 <= h <= 1:
        raise CapacityError("Headroom line: 10 to 100 % of the limit.")
    d0 = rows[0][0]
    xs = [(d - d0).days for d, _ in rows]
    ys = [v for _, v in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise CapacityError("The dates must differ.")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    icpt = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (icpt + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    last = rows[-1][0]
    out: dict[str, Any] = {"ok": True, "points": n, "from": d0.isoformat(), "to": last.isoformat(), "slope_per_day": round(slope, 6),
                           "slope_per_week": round(slope * 7, 4), "r2": round(r2, 4), "limit": L, "headroom": h, "unit": unit,
                           "now": round(ys[-1], 4), "now_share": round(ys[-1] / L, 4), "issues": [],
                           "series": [{"d": d.isoformat(), "v": v, "fit": round(icpt + slope * (d - d0).days, 4)} for d, v in rows[-400:]]}

    def when(level: float) -> str | None:
        if slope <= 0:
            return None
        x = (level - icpt) / slope
        return (d0 + timedelta(days=max(x, xs[-1]))).isoformat()

    out["hits_headroom"] = when(L * h)
    out["hits_limit"] = when(L)
    if ys[-1] >= L * h:
        out["issues"].append({"sev": "bad", "text": f"Peak use is already at {ys[-1] / L:.0%} of the limit, past the {h:.0%} line."})
    if out["hits_headroom"]:
        weeks = (date.fromisoformat(out["hits_headroom"]) - last).days / 7
        out["weeks_left"] = round(weeks, 1)
        if weeks < 8 and ys[-1] < L * h:
            out["issues"].append({"sev": "warn", "text": f"At this trend peak use crosses the {h:.0%} line in {weeks:.1f} weeks."})
    if r2 < 0.5:
        out["issues"].append({"sev": "info", "text": f"The trend fits weakly (r2 {r2:.2f}): the dates are a rough guide only."})
    out["verdict"] = (f"Peak use {ys[-1]:.4g}{unit} of {L:g}{unit} ({ys[-1] / L:.0%}), growing {slope * 7:+.3g}{unit} a week. "
                      + (f"It reaches the {h:.0%} line on {out['hits_headroom']} and the limit on {out['hits_limit']}." if out["hits_limit"]
                         else "It is not growing, so no date for the limit."))
    return out


def _erlang_c(c: int, a: float) -> float:
    """Probability a request waits, c servers, offered load a = lambda / mu (Erlang C)."""
    s = sum(a ** k / factorial(k) for k in range(c))
    top = a ** c / factorial(c) * (c / (c - a))
    return top / (s + top)


def queue(rps: Any, service_ms: Any, servers: Any) -> dict[str, Any]:
    try:
        lam, s_ms, c = float(rps), float(service_ms), int(servers)
    except (TypeError, ValueError):
        raise CapacityError("Requests per second, time per request (ms) and servers: numbers.")
    if lam <= 0 or s_ms <= 0 or not 1 <= c <= 400:
        raise CapacityError("Requests per second and time per request above 0, servers 1 to 400.")
    mu = 1000 / s_ms
    a = lam / mu
    rho = a / c
    out: dict[str, Any] = {"ok": True, "rps": lam, "service_ms": s_ms, "servers": c, "utilisation": round(rho, 4), "issues": []}
    if rho >= 1:
        out["issues"].append({"sev": "bad", "text": f"Utilisation {rho:.0%}: more work arrives than the servers can do - the queue grows without end."})
        out["verdict"] = f"Overloaded: needs at least {int(a) + 1} servers just to keep up."
        out["min_servers"] = int(a) + 1
        return out
    pw = _erlang_c(c, a)
    wq = pw / (c * mu - lam) * 1000
    out.update(p_wait=round(pw, 4), wait_ms=round(wq, 3), response_ms=round(wq + s_ms, 3), min_servers=int(a) + 1)
    curve = []
    for u in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98):
        l2 = u * c * mu
        p2 = _erlang_c(c, l2 / mu)
        curve.append({"utilisation": u, "rps": round(l2, 2), "response_ms": round(p2 / (c * mu - l2) * 1000 + s_ms, 3)})
    out["curve"] = curve
    if rho > 0.8:
        out["issues"].append({"sev": "warn", "text": f"Utilisation {rho:.0%}: waits rise steeply above about 80 %, and a lost server pushes the rest higher."})
    if c > 1:
        a2 = lam / mu / (c - 1)
        out["one_down_utilisation"] = round(a2, 4)
        if a2 >= 1:
            out["issues"].append({"sev": "bad", "text": "With one server down the rest cannot keep up (no N+1)."})
    out["issues"].append({"sev": "info", "text": "An M/M/c queue model (random arrivals and service times), not your system."})
    out["verdict"] = (f"{c} servers at {rho:.0%}: {pw:.0%} of requests wait, about {wq:.1f} ms on average; response about {wq + s_ms:.1f} ms.")
    return out
