"""A request path's latency budget: the stages a request goes through one after another (each with its median and p99), stages that
fan out to N backends and wait for all of them, and stages that send a hedged second request. Each stage is modelled as a log-normal
fitted to her p50 and p99, the path is sampled 20,000 times (the same seed every time), and the end-to-end percentiles, which stage
the tail comes from and what hedging or a smaller fan-out would save are worked out. A model on her numbers, said as such."""
from __future__ import annotations

import math
import random
import re
from typing import Any

from .latency import UNIT, fmt


class BudgetError(ValueError):
    pass


Z99 = 2.3263478740408408
N = 20000


def _val(s: str, unit: str, what: str) -> float:
    m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)\s*(ns|us|µs|μs|ms|s)?\s*", str(s or ""))
    if not m:
        raise BudgetError(f"{what}: '{s}' is not a time, write 1.2ms, 300us or a number.")
    return float(m.group(1)) * UNIT[(m.group(2) or unit).replace("μ", "µ")]


def parse(text: str, unit: str = "ms") -> tuple[list[dict[str, Any]], float | None, float]:
    stages: list[dict[str, Any]] = []
    target, tq = None, 99.0
    for ln, raw in enumerate(str(text or "").splitlines(), 1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        p = [x.strip() for x in re.split(r"\s*[,;\t]\s*", line)]
        k = p[0].lower()
        where = f"Line {ln}"
        try:
            if k == "target":
                if len(p) < 3:
                    raise BudgetError(f"{where}: target, p99, 5ms")
                tq = float(p[1].lower().lstrip("p"))
                target = _val(p[2], unit, where)
                continue
            if k in ("stage", "call", "step"):
                if len(p) < 4:
                    raise BudgetError(f"{where}: stage, name, p50, p99[, times]")
                st = {"type": "stage", "name": p[1][:60], "p50": _val(p[2], unit, where), "p99": _val(p[3], unit, where),
                      "times": int(p[4]) if len(p) > 4 and p[4] else 1}
            elif k == "fanout":
                if len(p) < 5:
                    raise BudgetError(f"{where}: fanout, name, N backends, p50, p99")
                st = {"type": "fanout", "name": p[1][:60], "n": int(p[2]), "p50": _val(p[3], unit, where), "p99": _val(p[4], unit, where), "times": 1}
            elif k == "hedge":
                if len(p) < 5:
                    raise BudgetError(f"{where}: hedge, name, p50, p99, send the second after")
                st = {"type": "hedge", "name": p[1][:60], "p50": _val(p[2], unit, where), "p99": _val(p[3], unit, where), "after": _val(p[4], unit, where), "times": 1}
            else:
                raise BudgetError(f"{where}: start with stage, fanout, hedge or target.")
        except (ValueError, IndexError) as e:
            raise BudgetError(str(e) if isinstance(e, BudgetError) else f"{where}: a number is wrong.")
        if st["p50"] <= 0 or st["p99"] < st["p50"]:
            raise BudgetError(f"{where}: p99 must be at least the p50, and both above 0.")
        if not 1 <= st.get("times", 1) <= 1000 or not 1 <= st.get("n", 1) <= 100000:
            raise BudgetError(f"{where}: times 1-1000, N 1-100,000.")
        stages.append(st)
    if not stages:
        raise BudgetError("List the stages first: stage, name, p50, p99 - one per line.")
    if len(stages) > 60:
        raise BudgetError("Up to 60 stages.")
    if len({s["name"] for s in stages}) != len(stages):
        raise BudgetError("Two stages have the same name.")
    if not 0 < tq < 100:
        raise BudgetError("The target percentile: between 0 and 100.")
    return stages, target, tq


def _ln(p50: float, p99: float) -> tuple[float, float]:
    return math.log(p50), max(1e-9, math.log(p99 / p50) / Z99)


def _draw(st: dict[str, Any], rnd: random.Random, flat: bool = False) -> float:
    mu, sg = _ln(st["p50"], st["p99"])
    one = (lambda: st["p50"]) if flat else (lambda: math.exp(rnd.gauss(mu, sg)))
    if st["type"] == "fanout":
        if flat:
            return st["p50"]
        n = st["n"]
        if n <= 64:
            return max(one() for _ in range(n))
        # the max of n log-normals: draw its quantile directly, u^(1/n)
        u = rnd.random() ** (1 / n)
        return math.exp(mu + sg * _ndtri(u))
    if st["type"] == "hedge":
        a = one()
        return a if a <= st["after"] else min(a, st["after"] + one())
    return sum(one() for _ in range(st["times"]))


def _ndtri(p: float) -> float:
    """The inverse of the normal CDF (Acklam's rational approximation, |error| < 1.2e-9)."""
    p = min(max(p, 1e-300), 1 - 1e-16)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _q(v: list[float], q: float) -> float:
    return v[min(len(v) - 1, max(0, math.ceil(q / 100 * len(v)) - 1))]


def _sim(stages: list[dict[str, Any]], flat_i: int = -1, swap: dict[int, dict[str, Any]] | None = None, seed: int = 42) -> tuple[list[float], list[list[float]]]:
    rnd = random.Random(seed)
    tot, per = [], [[] for _ in stages]
    for _ in range(N):
        s = 0.0
        for i, st in enumerate(stages):
            x = _draw((swap or {}).get(i, st), rnd, flat=(i == flat_i))
            per[i].append(x)
            s += x
        tot.append(s)
    tot.sort()
    return tot, per


def budget(text: str, unit: str = "ms", target_us: float | None = None, target_q: float = 99.0) -> dict[str, Any]:
    stages, t2, tq2 = parse(text, unit or "ms")
    if t2 is not None:
        target_us, target_q = t2, tq2
    try:
        target_us = float(target_us) if target_us not in (None, "", 0, "0") else None
        target_q = float(target_q or 99)
    except (TypeError, ValueError):
        raise BudgetError("The target must be a number.")
    tot, per = _sim(stages)
    qs = {k: _q(tot, float(k)) for k in ("50", "90", "99", "99.9")}
    tq = _q(tot, target_q)
    rows = []
    for i, st in enumerate(stages):
        v = sorted(per[i])
        flat, _ = _sim(stages, flat_i=i)
        gain = tq - _q(flat, target_q)
        r = {"name": st["name"], "type": st["type"], "p50": st["p50"], "p99": st["p99"], "sim50": _q(v, 50), "sim99": _q(v, 99),
             "times": st.get("times", 1), "n": st.get("n"), "after": st.get("after"), "gain": gain, "share50": 0.0}
        if st["type"] == "fanout":
            r["slow_chance"] = 1 - 0.99 ** st["n"]
        rows.append(r)
    s50 = sum(r["sim50"] for r in rows) or 1
    for r in rows:
        r["share50"] = r["sim50"] / s50
    issues: list[dict[str, Any]] = []
    best = max(rows, key=lambda r: r["gain"])
    if best["gain"] > 0.05 * tq:
        issues.append({"sev": "info", "text": f"The biggest win: if '{best['name']}' always took its median, the end-to-end p{target_q:g} would drop by {fmt(best['gain'])} "
                       f"({best['gain'] / tq * 100:.0f}%), from {fmt(tq)} to {fmt(tq - best['gain'])}."})
    what_if = []
    for i, st in enumerate(stages):
        if st["type"] == "fanout" and st["n"] >= 2:
            r = rows[i]
            sev = "warn" if st["n"] >= 10 else "info"
            issues.append({"sev": sev, "text": f"'{st['name']}' waits for all {st['n']} backends: {r['slow_chance'] * 100:.0f}% of requests wait on at least one backend's p99, so this stage's median ({fmt(r['sim50'])}) is near a single backend's p{min(99.99, 100 * 0.5 ** (1 / st['n'])):.3g}.",
                           "fix": "Fewer backends per request, answer with what came back by a deadline (partial results), or hedge the slowest replicas."})
            hal = max(1, st["n"] // 2)
            t3, _ = _sim(stages, swap={i: {**st, "n": hal}})
            what_if.append({"what": f"'{st['name']}' to {hal} backends", "q": _q(t3, target_q), "load": None})
        if st["type"] == "stage" and st["p99"] / st["p50"] >= 5:
            mu, sg = _ln(st["p50"], st["p99"])
            p95 = math.exp(mu + 1.6448536 * sg)
            t3, _ = _sim(stages, swap={i: {**st, "type": "hedge", "after": p95, "times": 1}} if st["times"] == 1 else None)
            if st["times"] == 1:
                what_if.append({"what": f"hedge '{st['name']}' after its p95 ({fmt(p95)})", "q": _q(t3, target_q), "load": 0.05})
                issues.append({"sev": "info", "text": f"'{st['name']}' has a heavy tail (p99 is {st['p99'] / st['p50']:.0f} times its median): a hedged second request after {fmt(p95)} costs about 5% more calls to it.",
                               "fix": "Only hedge calls that are safe to repeat (reads, or writes with an idempotency key)."})
        if st["type"] == "stage" and st["times"] >= 3:
            issues.append({"sev": "info", "text": f"'{st['name']}' runs {st['times']} times one after another - batch them or run them in parallel and the stage costs one round, not {st['times']}."})
    if target_us:
        ok = tq <= target_us
        issues.append({"sev": "info" if ok else "bad", "text": f"End-to-end p{target_q:g} is about {fmt(tq)} against your budget of {fmt(target_us)} - " + ("within it." if ok else f"{(tq / target_us - 1) * 100:.0f}% over.")})
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    for w in what_if:
        w["change"] = w["q"] / tq - 1 if tq else None
    hist = []
    lo, hi = max(tot[0], 1e-3), tot[min(len(tot) - 1, int(0.999 * len(tot)))]
    if hi > lo:
        a, b = math.log(lo), math.log(hi)
        cnt = [0] * 28
        for x in tot:
            if x <= hi:
                cnt[min(27, int((math.log(max(x, lo)) - a) / (b - a) * 28))] += 1
        hist = [{"lo": math.exp(a + (b - a) * j / 28), "hi": math.exp(a + (b - a) * (j + 1) / 28), "n": c} for j, c in enumerate(cnt)]
    return {"stages": rows, "q": qs, "target": {"q": target_q, "us": target_us, "value": tq, "ok": None if not target_us else tq <= target_us},
            "what_if": what_if, "hist": hist, "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order},
            "sum_p50": sum(st["p50"] * st.get("times", 1) for st in stages), "sum_p99": sum(st["p99"] * st.get("times", 1) for st in stages),
            "verdict": (f"End to end: p50 about {fmt(qs['50'])}, p99 about {fmt(qs['99'])}, p99.9 about {fmt(qs['99.9'])} over {len(stages)} stage(s)"
                        + (f" - {'within' if tq <= target_us else 'over'} your {fmt(target_us)} budget." if target_us else ".")),
            "note": ("Each stage is a log-normal fitted to your p50 and p99, sampled 20,000 times with the same seed; stages are taken as independent, "
                     "so shared causes (a GC pause that slows every stage at once) make the real tail worse than this. Adding the p99s gives "
                     f"{fmt(sum(st['p99'] * st.get('times', 1) for st in stages))} - an upper bound that almost never happens.")}
