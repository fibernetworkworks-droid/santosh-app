"""Latency, worked out in code: from durations (a log, a CSV column or plain numbers) or from a Prometheus histogram's buckets.

- percentiles (p50 / p90 / p95 / p99 / p99.9), the share under her latency threshold, Apdex (satisfied <= T, tolerating <= 4T);
- buckets ('le' lines or the _bucket series of one histogram) -> the quantiles the way histogram_quantile() interpolates them, and
  the honest error bound: the true value is somewhere inside the bucket."""
from __future__ import annotations

import csv
import io
import re
from typing import Any

MAX = 3_000_000
MAX_N = 1_000_000
UNITS = {"ns": 1e-6, "us": 1e-3, "µs": 1e-3, "ms": 1.0, "s": 1000.0, "sec": 1000.0, "m": 60000.0}
PCTS = (0.5, 0.9, 0.95, 0.99, 0.999)


class LatencyError(ValueError):
    pass


def _pct(s: list[float], p: float) -> float:
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


_DUR = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(ns|us|µs|ms|sec|s)\b")


def read_durations(text: str, unit: str = "ms") -> tuple[list[float], str]:
    text = str(text or "")[:MAX].strip()
    if not text:
        return [], ""
    first = text.split("\n", 1)[0]
    if "," in first and re.search(r"[A-Za-z]", first):
        rows = list(csv.reader(io.StringIO(text)))
        head = [h.strip().lower() for h in rows[0]]
        col = next((i for i, h in enumerate(head) if re.search(r"latenc|duration|elapsed|response_?time|took|_ms$|\bms\b|seconds?$", h)), None)
        if col is None:
            raise LatencyError("No duration column found (latency, duration, elapsed or response_time).")
        mul = 1000.0 if re.search(r"seconds?$|_s$", head[col]) else UNITS.get(unit, 1.0)
        out = []
        for r in rows[1:MAX_N + 1]:
            try:
                out.append(float(r[col]) * mul)
            except (ValueError, IndexError):
                continue
        return out, head[col]
    hits = _DUR.findall(text)
    if len(hits) >= 5:
        return [float(v) * UNITS[u] for v, u in hits[:MAX_N]], "durations in the text"
    vals = []
    for x in re.split(r"[\s,;]+", text)[:MAX_N]:
        try:
            vals.append(float(x) * UNITS.get(unit, 1.0))
        except ValueError:
            continue
    return vals, "numbers"


def analyse(text: str, threshold_ms: Any = 300, unit: str = "ms", objective: Any = None) -> dict[str, Any]:
    vals, col = read_durations(text, unit)
    vals = [v for v in vals if v == v and 0 <= v < 1e9]
    if len(vals) < 10:
        raise LatencyError("At least 10 durations are needed.")
    try:
        T = float(threshold_ms)
    except (TypeError, ValueError):
        raise LatencyError("Threshold: milliseconds.")
    if T <= 0:
        raise LatencyError("Threshold: more than 0 ms.")
    s = sorted(vals)
    n = len(s)
    sat = sum(1 for v in s if v <= T)
    tol = sum(1 for v in s if T < v <= 4 * T)
    under = sat / n
    out: dict[str, Any] = {"ok": True, "source": col, "count": n, "mean_ms": round(sum(s) / n, 3), "min_ms": round(s[0], 3), "max_ms": round(s[-1], 3),
                           "percentiles": {f"p{p * 100:g}": round(_pct(s, p), 3) for p in PCTS}, "threshold_ms": T,
                           "under_threshold": round(under, 6), "apdex": round((sat + tol / 2) / n, 4), "issues": []}
    edges = [T / 4, T / 2, T, 2 * T, 4 * T, 8 * T]
    hist = [0] * (len(edges) + 1)
    for v in s:
        hist[next((i for i, e in enumerate(edges) if v <= e), len(edges))] += 1
    out["hist"] = {"edges": [round(e, 3) for e in edges], "counts": hist}
    if objective not in (None, ""):
        o = float(str(objective).rstrip("%"))
        o = o / 100 if o > 1 else o
        out["objective"] = o
        if under < o:
            out["issues"].append({"sev": "bad", "text": f"{under:.3%} of requests are within {T:g} ms; the objective is {o:.3%}."})
    p99, p50 = _pct(s, 0.99), _pct(s, 0.5)
    if p50 > 0 and p99 / p50 > 10:
        out["issues"].append({"sev": "warn", "text": f"A long tail: p99 is {p99 / p50:.0f}x the median. Look at retries, cold caches, GC pauses or one slow dependency."})
    out["verdict"] = (f"{n} requests: median {p50:.1f} ms, p99 {p99:.1f} ms; {under:.2%} within {T:g} ms, Apdex {out['apdex']:.2f}.")
    return out


_LE = re.compile(r'le="([^"]+)"[^}]*\}\s+([0-9.eE+-]+)')


def buckets(text: str, threshold_ms: Any = None, unit: str = "s") -> dict[str, Any]:
    """Cumulative buckets: Prometheus '_bucket{le="0.1"} 123' lines, or 'le,count' lines."""
    text = str(text or "")[:500_000]
    pairs: list[tuple[float, float]] = []
    for m in _LE.finditer(text):
        le = float("inf") if m.group(1) in ("+Inf", "Inf", "inf") else float(m.group(1))
        pairs.append((le, float(m.group(2))))
    if not pairs:
        for ln in text.splitlines():
            parts = [p.strip() for p in re.split(r"[,\t ]+", ln.strip()) if p.strip()]
            if len(parts) == 2:
                try:
                    le = float("inf") if parts[0].lower() in ("+inf", "inf") else float(parts[0])
                    pairs.append((le, float(parts[1])))
                except ValueError:
                    continue
    if len(pairs) < 2:
        raise LatencyError('Paste the buckets: lines like  http_request_duration_seconds_bucket{le="0.1"} 123')
    merged: dict[float, float] = {}
    for le, c in pairs:
        merged[le] = merged.get(le, 0) + c     # several series of one histogram add up
    bs = sorted(merged.items())
    issues = []
    for i in range(1, len(bs)):
        if bs[i][1] < bs[i - 1][1]:
            issues.append({"sev": "bad", "text": f"The count goes down at le={bs[i][0]:g}: buckets must be cumulative."})
            break
    if bs[-1][0] != float("inf"):
        issues.append({"sev": "warn", "text": "No +Inf bucket: the slowest requests are not counted."})
    total = bs[-1][1]
    if total <= 0:
        raise LatencyError("The buckets are empty.")
    mul = UNITS.get(unit, 1000.0)

    def q(p: float) -> tuple[float, float, float]:
        rank = p * total
        lo_le, lo_c = 0.0, 0.0
        for le, c in bs:
            if c >= rank:
                if le == float("inf"):
                    return lo_le, lo_le, float("inf")
                frac = (rank - lo_c) / (c - lo_c) if c > lo_c else 0
                return lo_le + (le - lo_le) * frac, lo_le, le
            lo_le, lo_c = le, c
        return lo_le, lo_le, float("inf")

    qs = {}
    for p in PCTS:
        v, lo, hi = q(p)
        qs[f"p{p * 100:g}"] = {"ms": round(v * mul, 3), "between_ms": [round(lo * mul, 3), None if hi == float("inf") else round(hi * mul, 3)]}
    out: dict[str, Any] = {"ok": True, "total": total, "buckets": [{"le_ms": None if le == float("inf") else round(le * mul, 3), "count": c} for le, c in bs],
                           "quantiles": qs, "issues": issues}
    if threshold_ms not in (None, ""):
        T = float(threshold_ms) / mul
        exact = next((c for le, c in bs if abs(le - T) < 1e-12), None)
        out["threshold_ms"] = float(threshold_ms)
        if exact is None:
            out["issues"].append({"sev": "warn", "text": f"No bucket ends at {float(threshold_ms):g} ms: add one, or the share under it is only an estimate."})
            under, lo_le, lo_c = None, 0.0, 0.0
            for le, c in bs:
                if le >= T:
                    under = (lo_c + (c - lo_c) * ((T - lo_le) / (le - lo_le) if le != float("inf") and le > lo_le else 0)) / total
                    break
                lo_le, lo_c = le, c
            out["under_threshold"] = round(under, 6) if under is not None else None
            out["estimated"] = True
        else:
            out["under_threshold"] = round(exact / total, 6)
            out["estimated"] = False
    p99 = qs["p99"]
    where = (f"somewhere between {p99['between_ms'][0]:g} and {p99['between_ms'][1]:g} ms" if p99["between_ms"][1] is not None
             else f"above {p99['between_ms'][0]:g} ms - in the last bucket, so add a higher one")
    out["verdict"] = (f"{total:g} requests: p50 about {qs['p50']['ms']:g} ms, p99 about {p99['ms']:g} ms ({where}; a histogram only "
                      "knows the bucket).")
    return out
