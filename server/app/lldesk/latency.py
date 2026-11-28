"""Latency runs read and worked out: raw samples (one number per line or separated by commas / spaces, with or without a unit),
HdrHistogram percentile output, wrk / wrk2 latency distributions, or lines like 'p99: 1.2 ms'. Percentiles, how far each can be
trusted from the number of samples, the tail against the middle, groups of samples (two modes), coordinated omission corrected when
the load was sent at a fixed rate, and two to six runs compared with a bootstrap interval. Everything is in microseconds."""
from __future__ import annotations

import math
import random
import re
from typing import Any


class LatencyError(ValueError):
    pass


UNIT = {"ns": 0.001, "us": 1.0, "µs": 1.0, "μs": 1.0, "usec": 1.0, "ms": 1000.0, "msec": 1000.0, "s": 1e6, "sec": 1e6}
QS = [50.0, 90.0, 99.0, 99.9, 99.99]
MAX_SAMPLES = 2_000_000
_NUM = r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?"


def _f(x: str) -> float:
    return float(x.replace(",", "")) if x.count(",") and "." in x else float(x.replace(",", "."))


def _u(unit: str, default: str) -> float:
    u = (unit or default or "us").strip().lower().replace("μ", "µ")
    if u not in UNIT:
        raise LatencyError(f"Unit '{unit}': use ns, us, ms or s.")
    return UNIT[u]


def fmt(us: float | None) -> str:
    if us is None:
        return "—"
    a = abs(us)
    if a >= 1e6:
        return f"{us / 1e6:.3g} s"
    if a >= 1000:
        return f"{us / 1000:.3g} ms"
    if a >= 1:
        return f"{us:.3g} µs"
    return f"{us * 1000:.3g} ns"


def _split(text: str) -> list[tuple[str, str]]:
    t = str(text or "")
    heads = list(re.finditer(r"^\s*(?:##+\s*(.+?)\s*|-{3,}\s*(.*?)\s*)$", t, re.M))
    if not heads:
        return [("run 1", t)]
    out = []
    if t[:heads[0].start()].strip():
        out.append(("run 1", t[:heads[0].start()]))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
        body = t[m.end():end]
        if body.strip():
            out.append(((m.group(1) or m.group(2) or "").strip()[:60] or f"run {len(out) + 1}", body))
    return out


def _parse(name: str, t: str, unit: str) -> dict[str, Any]:
    """Return {'name', 'samples': sorted list | None, 'points': {q: us} | None, 'tool': str}."""
    low = t.lower()
    tool = ("wrk2" if ("recorded latency" in low or "uncorrected latency" in low) else "wrk" if re.search(r"\blatency distribution\b", low) and "requests/sec" in low
            else "hdr" if "percentile" in low and "totalcount" in low.replace(" ", "") else "")
    pts: dict[float, float] = {}
    # HdrHistogram: "Value Percentile TotalCount 1/(1-Percentile)" rows; the value is in the unit she gives (wrk2 prints ms)
    if tool in ("hdr", "wrk2") and re.search(r"^\s*value\s+percentile", low, re.M):
        mult = _u(unit, "ms" if tool == "wrk2" else "us")
        sec = re.split(r"^\s*value\s+percentile.*$", t, flags=re.M | re.I)[1]
        for m in re.finditer(rf"^\s*({_NUM})\s+(0?\.\d+|1\.0+)\s+(\d+)(?:\s+\S+)?\s*$", sec, re.M):
            q = float(m.group(2)) * 100
            pts[round(q, 6)] = _f(m.group(1)) * mult
        if pts:
            mx = re.search(rf"#\[Max\s*=\s*({_NUM})", t)
            if mx:
                pts[100.0] = max(pts.get(100.0, 0), _f(mx.group(1)) * mult)
            tc = re.search(r"#\[.*Total count\s*=\s*(\d+)", t)
            return {"name": name, "samples": None, "points": dict(sorted(pts.items())), "tool": "wrk2" if tool == "wrk2" else "HdrHistogram",
                    "count": int(tc.group(1)) if tc else None}
    # wrk / wrk2 short form: " 50.000%    1.23ms" / "99%  4.5ms"; generic "p99: 1.2 ms", "p99.9=300us", "99th percentile: 3 ms"
    pat = re.compile(rf"(?:^|\s)(?:p\s*({_NUM})|({_NUM})\s*(?:%|th\s+percentile|th\b))\s*[:=]?\s*({_NUM})\s*(ns|us|µs|μs|usec|ms|msec|s|sec)?\b", re.I)
    for m in pat.finditer(t):
        q = float(m.group(1) or m.group(2))
        if not 0 < q <= 100:
            continue
        if q < 1 and m.group(1) and not m.group(2):   # "p0.99" style
            q *= 100
        v = _f(m.group(3)) * _u(m.group(4) or "", unit or ("ms" if tool.startswith("wrk") else "us"))
        pts[round(q, 6)] = v
    for lab, q in (("max", 100.0), ("maximum", 100.0), ("min", 0.0), ("median", 50.0)):
        m = re.search(rf"\b{lab}\b\s*[:=]?\s*({_NUM})\s*(ns|us|µs|μs|usec|ms|msec|s|sec)?\b", t, re.I)
        if m and pts:
            pts.setdefault(q, _f(m.group(1)) * _u(m.group(2) or "", unit or "us"))
    if len(pts) >= 2:
        return {"name": name, "samples": None, "points": dict(sorted(pts.items())), "tool": tool or "percentiles", "count": None}
    # raw samples
    mult = _u(unit, "us")
    vals: list[float] = []
    for m in re.finditer(rf"({_NUM})\s*(ns|us|µs|μs|usec|ms|msec|s|sec)?(?=$|[\s,;])", t, re.M):
        try:
            v = float(m.group(1).replace(",", "") if "." in m.group(1) else m.group(1).replace(",", "."))
        except ValueError:
            continue
        vals.append(v * (UNIT[m.group(2).lower().replace("μ", "µ")] if m.group(2) else mult))
        if len(vals) > MAX_SAMPLES:
            raise LatencyError(f"{name}: more than {MAX_SAMPLES:,} samples - use HdrHistogram output for bigger runs.")
    vals = [v for v in vals if v >= 0 and math.isfinite(v)]
    if len(vals) < 2:
        raise LatencyError(f"{name}: no latency numbers found - paste one sample per line, HdrHistogram / wrk2 output, or lines like 'p99: 1.2 ms'.")
    vals.sort()
    return {"name": name, "samples": vals, "points": None, "tool": "samples", "count": len(vals)}


def _q_samples(v: list[float], q: float) -> float:
    if q >= 100:
        return v[-1]
    if q <= 0:
        return v[0]
    k = max(0, math.ceil(q / 100 * len(v)) - 1)   # nearest rank, as HdrHistogram reports
    return v[min(k, len(v) - 1)]


def _q_points(p: dict[float, float], q: float) -> float | None:
    ks = sorted(p)
    if q in p:
        return p[q]
    if q > ks[-1] or q < ks[0]:
        return None
    for a, b in zip(ks, ks[1:]):
        if a <= q <= b:
            return p[a] + (p[b] - p[a]) * (q - a) / (b - a) if b > a else p[a]
    return None


def quantile(run: dict[str, Any], q: float) -> float | None:
    return _q_samples(run["samples"], q) if run["samples"] else _q_points(run["points"], q)


def _co(v: list[float], interval: float) -> list[float]:
    """HdrHistogram's recordValueWithExpectedInterval: a stall of length L at a fixed send rate also delayed the requests that
    should have been sent during it, by L - interval, L - 2 * interval, ..."""
    out = list(v)
    for x in v:
        y = x - interval
        while y >= interval:
            out.append(y)
            y -= interval
            if len(out) > MAX_SAMPLES * 2:
                raise LatencyError("Correcting for coordinated omission would make more than 4,000,000 samples - check the interval.")
    out.sort()
    return out


def _hist(v: list[float], n: int = 32) -> list[dict[str, Any]]:
    lo, hi = max(v[0], 1e-3), max(v[-1], 1e-3)
    if hi <= lo * 1.0001:
        return [{"lo": lo, "hi": hi, "n": len(v)}]
    a, b = math.log(lo), math.log(hi)
    out = [{"lo": math.exp(a + (b - a) * i / n), "hi": math.exp(a + (b - a) * (i + 1) / n), "n": 0} for i in range(n)]
    for x in v:
        i = min(n - 1, max(0, int((math.log(max(x, 1e-3)) - a) / (b - a) * n)))
        out[i]["n"] += 1
    return out


def _modes(h: list[dict[str, Any]], total: int) -> list[float]:
    sm = [(h[i - 1]["n"] if i else 0) + 2 * h[i]["n"] + (h[i + 1]["n"] if i + 1 < len(h) else 0) for i in range(len(h))]
    peaks = [i for i in range(len(sm)) if sm[i] > 0 and (i == 0 or sm[i] >= sm[i - 1]) and (i + 1 == len(sm) or sm[i] > sm[i + 1])]
    peaks = [i for i in peaks if sm[i] >= 0.12 * total]   # sm counts a bin about 4 times: a peak of ~3% of the samples
    keep: list[int] = []
    for i in peaks:
        if keep and min(sm[keep[-1]:i + 1]) > 0.5 * min(sm[keep[-1]], sm[i]):
            if sm[i] > sm[keep[-1]]:
                keep[-1] = i
            continue
        keep.append(i)
    return [math.sqrt(h[i]["lo"] * h[i]["hi"]) for i in keep]


def _stats(run: dict[str, Any], target_q: float, target_us: float | None) -> dict[str, Any]:
    v = run["samples"]
    n = run["count"] if run.get("count") else (len(v) if v else None)
    qs = {}
    for q in QS + [100.0]:
        x = quantile(run, q)
        qs[str(q).rstrip("0").rstrip(".")] = x
    rel = {}
    for q in QS:
        k = str(q).rstrip("0").rstrip(".")
        if n:
            tail = n * (1 - q / 100)
            rel[k] = "ok" if tail >= 10 else "few" if tail >= 1 else "none"
        else:
            rel[k] = "unknown"
    out: dict[str, Any] = {"name": run["name"], "tool": run["tool"], "count": n, "q": qs, "reliable": rel,
                           "min": v[0] if v else run["points"].get(0.0), "max": qs["100"]}
    if v:
        mean = sum(v) / len(v)
        var = sum((x - mean) ** 2 for x in v) / max(1, len(v) - 1)
        out.update(mean=mean, stdev=math.sqrt(var), hist=_hist(v))
        out["modes"] = _modes(out["hist"], len(v)) if len(v) >= 200 else []
    else:
        out["points"] = [[q, x] for q, x in run["points"].items()]
    if target_us:
        x = quantile(run, target_q)
        out["target"] = {"q": target_q, "us": target_us, "value": x, "ok": None if x is None else x <= target_us}
    return out


def _issues(s: dict[str, Any], raw: str) -> list[dict[str, Any]]:
    iss: list[dict[str, Any]] = []
    q = s["q"]
    nm = s["name"]
    if s["tool"] == "wrk":
        iss.append({"sev": "warn", "text": f"{nm}: wrk waits for each answer before sending the next, so a stall hides the requests that "
                    "should have waited behind it (coordinated omission) - its tail is too good.", "fix": "Measure with wrk2 -R <rate> (or k6 / Gatling at a fixed arrival rate) and read the corrected numbers."})
    for k, lab in (("99", "p99"), ("99.9", "p99.9"), ("99.99", "p99.99")):
        if s["reliable"].get(k) in ("few", "none") and q.get(k) is not None:
            iss.append({"sev": "info", "text": f"{nm}: {lab} and above rest on fewer than 10 samples beyond them ({s['count']:,} samples) - they are close to the maximum, not percentiles you can compare.",
                        "fix": f"Collect at least {round(10 / (1 - float(k) / 100)):,} samples to read {lab}."})
            break
    p50, p99, p999, mx = q.get("50"), q.get("99"), q.get("99.9"), q.get("100")
    if p50 and p99 and p99 / p50 > 10:
        iss.append({"sev": "warn", "text": f"{nm}: p99 is {p99 / p50:.0f} times the median ({fmt(p99)} against {fmt(p50)}) - a heavy tail: something stalls now and then (allocation / GC, a lock, a page fault, the scheduler, interrupts)."})
    if p999 and mx and s.get("count") and s["count"] >= 1000 and mx > 10 * p999:
        iss.append({"sev": "warn", "text": f"{nm}: the slowest sample ({fmt(mx)}) is over 10 times p99.9 - a single long stall; look for what ran at that moment (GC pause, swap, a migration, a timer)."})
    if len(s.get("modes") or []) >= 2:
        m = s["modes"]
        iss.append({"sev": "info", "text": f"{nm}: the samples fall into {len(m)} groups, around " + ", ".join(fmt(x) for x in m[:4]) +
                    " - two different paths (a cache hit and a miss, a fast and a slow branch, two machines) are mixed in one number."})
    if s.get("stdev") and s.get("mean") and s["stdev"] > 2 * s["mean"]:
        iss.append({"sev": "info", "text": f"{nm}: the spread (standard deviation {fmt(s['stdev'])}) is over twice the mean - report percentiles, not the mean."})
    t = s.get("target")
    if t and t["value"] is not None:
        iss.append({"sev": "info" if t["ok"] else "bad", "text": f"{nm}: p{t['q']:g} is {fmt(t['value'])} against your target of {fmt(t['us'])} - " + ("within it." if t["ok"] else f"{(t['value'] / t['us'] - 1) * 100:.0f}% over.")})
    return iss


def _boot(a: list[float], b: list[float], q: float, seed: int = 7, reps: int = 300) -> tuple[float, float]:
    rnd = random.Random(seed)
    cap = 20000
    a2 = a if len(a) <= cap else [a[int(i * len(a) / cap)] for i in range(cap)]
    b2 = b if len(b) <= cap else [b[int(i * len(b) / cap)] for i in range(cap)]
    ds = []
    for _ in range(reps):
        sa = sorted(rnd.choice(a2) for _ in range(len(a2)))
        sb = sorted(rnd.choice(b2) for _ in range(len(b2)))
        x, y = _q_samples(sa, q), _q_samples(sb, q)
        if x > 0:
            ds.append(y / x - 1)
    ds.sort()
    return ds[int(0.025 * len(ds))], ds[min(len(ds) - 1, int(0.975 * len(ds)))]


def analyse(text: str, unit: str = "us", interval_us: float | None = None, target_q: float = 99.0, target_us: float | None = None) -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 40_000_000:
        raise LatencyError("That is longer than 40 MB.")
    try:
        target_q = float(target_q or 99)
        target_us = float(target_us) if target_us not in (None, "", 0, "0") else None
        interval_us = float(interval_us) if interval_us not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        raise LatencyError("Target and interval must be numbers.")
    if not 0 < target_q < 100:
        raise LatencyError("The target percentile: between 0 and 100, for example 99.")
    parts = _split(t)
    if len(parts) > 6:
        raise LatencyError("Up to 6 runs at a time.")
    runs = [_parse(n, b, unit) for n, b in parts]
    if len({r["name"] for r in runs}) != len(runs):
        for i, r in enumerate(runs):
            r["name"] = f"{r['name']} ({i + 1})"
    stats = [_stats(r, target_q, target_us) for r in runs]
    issues: list[dict[str, Any]] = []
    for s in stats:
        issues += _issues(s, t)
    corrected = None
    if interval_us:
        if interval_us <= 0:
            raise LatencyError("The send interval must be above 0.")
        r0 = runs[0]
        if not r0["samples"]:
            issues.append({"sev": "info", "text": "Coordinated omission can only be corrected from raw samples; HdrHistogram can do it while recording (recordValueWithExpectedInterval), and wrk2 already prints the corrected numbers."})
        else:
            cv = _co(r0["samples"], interval_us)
            cs = _stats({"name": r0["name"] + " (corrected)", "samples": cv, "points": None, "tool": "samples", "count": len(cv)}, target_q, target_us)
            corrected = {"added": len(cv) - len(r0["samples"]), "q": cs["q"], "interval": interval_us}
            p99, c99 = stats[0]["q"].get("99"), cs["q"].get("99")
            if p99 and c99 and c99 > p99 * 1.1:
                issues.append({"sev": "warn", "text": f"Corrected for a fixed send rate of one request every {fmt(interval_us)}, p99 is {fmt(c99)}, not {fmt(p99)}: "
                               f"{corrected['added']:,} requests waited behind stalls and were never measured."})
    compare = []
    if len(runs) > 1:
        base = runs[0]
        for r in runs[1:]:
            row: dict[str, Any] = {"name": r["name"], "base": base["name"], "q": {}}
            for q in QS:
                k = str(q).rstrip("0").rstrip(".")
                a, b = quantile(base, q), quantile(r, q)
                row["q"][k] = {"a": a, "b": b, "change": (b / a - 1) if a and b is not None else None}
            if base["samples"] and r["samples"] and min(len(base["samples"]), len(r["samples"])) >= 200:
                lo, hi = _boot(base["samples"], r["samples"], 99.0)
                lo5, hi5 = _boot(base["samples"], r["samples"], 50.0, seed=11)
                row["ci99"], row["ci50"] = [lo, hi], [lo5, hi5]
                ch = row["q"]["99"]["change"]
                if lo > 0.02:
                    row["verdict"] = "slower"
                    issues.append({"sev": "bad" if lo > 0.1 else "warn", "text": f"{r['name']}: p99 is {ch * 100:.0f}% slower than {base['name']} (95% interval +{lo * 100:.0f}% to +{hi * 100:.0f}%)."})
                elif hi < -0.02:
                    row["verdict"] = "faster"
                    issues.append({"sev": "info", "text": f"{r['name']}: p99 is {abs(ch) * 100:.0f}% faster than {base['name']} (95% interval {lo * 100:.0f}% to {hi * 100:.0f}%)."})
                else:
                    row["verdict"] = "same"
                    issues.append({"sev": "info", "text": f"{r['name']}: p99 is within the noise of {base['name']} (95% interval {lo * 100:+.0f}% to {hi * 100:+.0f}%)."})
            else:
                ch = row["q"]["99"]["change"]
                row["verdict"] = "unknown"
                if ch is not None:
                    issues.append({"sev": "info", "text": f"{r['name']}: p99 {ch * 100:+.0f}% against {base['name']} - no raw samples (at least 200 each), so no confidence interval: run each side several times before you trust it."})
            compare.append(row)
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in order}
    s0 = stats[0]
    if compare:
        c = compare[-1]
        ch = c["q"]["99"]["change"]
        verdict = (f"{c['name']} against {c['base']}: p99 {fmt(c['q']['99']['a'])} -> {fmt(c['q']['99']['b'])}" + (f" ({ch * 100:+.0f}%)" if ch is not None else "")
                   + {"slower": " - slower, beyond the noise.", "faster": " - faster, beyond the noise.", "same": " - within the noise.", "unknown": "."}[c["verdict"]])
    else:
        verdict = (f"{s0['name']}: p50 {fmt(s0['q'].get('50'))}, p99 {fmt(s0['q'].get('99'))}, p99.9 {fmt(s0['q'].get('99.9'))}, max {fmt(s0['q'].get('100'))}"
                   + (f" from {s0['count']:,} samples." if s0.get("count") else "."))
    return {"runs": stats, "compare": compare, "corrected": corrected, "issues": issues, "counts": counts, "verdict": verdict,
            "target": {"q": target_q, "us": target_us}, "unit": "us",
            "note": ("Percentiles are nearest-rank, as HdrHistogram reports them; from percentile lines, values between two lines are interpolated. "
                     "The comparison interval is a bootstrap of the raw samples (300 resamples) - it says whether the difference is beyond the noise "
                     "of these runs, not that it will hold on another machine.")}
