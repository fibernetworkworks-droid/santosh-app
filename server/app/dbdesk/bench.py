"""Benchmark output read into numbers - pgbench, sysbench, YCSB, HammerDB-style 'NOPM / TPM' lines, or plain latencies in ms - and
two runs compared: throughput and latency change, and whether the change is bigger than the run-to-run noise she says she sees.
Output is DATA."""
from __future__ import annotations

import re
from statistics import mean, median, pstdev
from typing import Any

MAX = 2_000_000


def _f(x: str) -> float | None:
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def _pct(v: list[float], p: float) -> float:
    s = sorted(v)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def read(text: str) -> dict[str, Any]:
    t = str(text or "")[:MAX]
    out: dict[str, Any] = {"tool": "", "tps": None, "qps": None, "lat_avg": None, "lat_p95": None, "lat_p99": None, "lat_max": None,
                           "errors": None, "clients": None, "duration_s": None, "meta": {}}
    if "pgbench" in t or re.search(r"^tps = ", t, re.M):
        out["tool"] = "pgbench"
        m = re.search(r"^tps = ([\d.]+)", t, re.M)
        out["tps"] = _f(m[1]) if m else None
        m = re.search(r"latency average = ([\d.]+) ms", t)
        out["lat_avg"] = _f(m[1]) if m else None
        m = re.search(r"latency stddev = ([\d.]+) ms", t)
        if m:
            out["meta"]["stddev_ms"] = _f(m[1])
        m = re.search(r"number of clients: (\d+)", t)
        out["clients"] = int(m[1]) if m else None
        m = re.search(r"duration: (\d+) s", t)
        out["duration_s"] = int(m[1]) if m else None
        m = re.search(r"number of failed transactions: (\d+)", t)
        out["errors"] = int(m[1]) if m else None
        m = re.search(r"scaling factor: (\d+)", t)
        if m:
            out["meta"]["scale"] = int(m[1])
    elif "SQL statistics" in t or "sysbench" in t.lower():
        out["tool"] = "sysbench"
        m = re.search(r"transactions:\s+\d+\s+\(([\d.]+) per sec", t)
        out["tps"] = _f(m[1]) if m else None
        m = re.search(r"queries:\s+\d+\s+\(([\d.]+) per sec", t)
        out["qps"] = _f(m[1]) if m else None
        for k, rx in (("lat_avg", r"avg:\s+([\d.]+)"), ("lat_p95", r"95th percentile:\s+([\d.]+)"), ("lat_max", r"max:\s+([\d.]+)")):
            m = re.search(rx, t)
            out[k] = _f(m[1]) if m else None
        m = re.search(r"ignored errors:\s+(\d+)", t)
        out["errors"] = int(m[1]) if m else None
        m = re.search(r"Number of threads: (\d+)", t)
        out["clients"] = int(m[1]) if m else None
    elif re.search(r"\[OVERALL\], Throughput", t):
        out["tool"] = "YCSB"
        m = re.search(r"\[OVERALL\], Throughput\(ops/sec\), ([\d.]+)", t)
        out["qps"] = _f(m[1]) if m else None
        ops = {}
        for op, k, v in re.findall(r"\[(READ|UPDATE|INSERT|SCAN|READ-MODIFY-WRITE)\], (AverageLatency|95thPercentileLatency|99thPercentileLatency)\(us\), ([\d.]+)", t):
            ops.setdefault(op, {})[k] = round(float(v) / 1000, 3)
        out["meta"]["ops"] = ops
        if "READ" in ops:
            out["lat_avg"], out["lat_p95"], out["lat_p99"] = ops["READ"].get("AverageLatency"), ops["READ"].get("95thPercentileLatency"), ops["READ"].get("99thPercentileLatency")
    elif re.search(r"\bNOPM\b|\bTPM\b", t):
        out["tool"] = "TPROC-C (HammerDB)"
        m = re.search(r"(\d[\d,]*)\s+NOPM", t)
        out["meta"]["nopm"] = _f(m[1]) if m else None
        m = re.search(r"(\d[\d,]*)\s+[A-Za-z]*\s*TPM", t)
        out["meta"]["tpm"] = _f(m[1]) if m else None
        out["tps"] = round(out["meta"]["tpm"] / 60, 2) if out["meta"].get("tpm") else None
    else:
        vals = [v for v in (_f(x) for x in re.split(r"[\s,;]+", t.strip())[:500_000]) if v is not None and v >= 0]
        if len(vals) >= 10:
            out["tool"] = "latencies"
            out.update(lat_avg=round(mean(vals), 3), lat_p95=round(_pct(vals, .95), 3), lat_p99=round(_pct(vals, .99), 3), lat_max=round(max(vals), 3))
            out["meta"].update(n=len(vals), median=round(median(vals), 3), stddev=round(pstdev(vals), 3))
    if not out["tool"]:
        return {"ok": False, "error": "Not a benchmark Hoola can read: paste pgbench, sysbench, YCSB or HammerDB output, or latencies in ms."}
    return {"ok": True, **out}


KEYS = (("tps", "Transactions / s", 1), ("qps", "Queries / s", 1), ("lat_avg", "Average latency (ms)", -1), ("lat_p95", "p95 latency (ms)", -1),
        ("lat_p99", "p99 latency (ms)", -1), ("lat_max", "Worst latency (ms)", -1))


def compare(a: dict[str, Any], b: dict[str, Any], noise_pct: float = 5.0) -> dict[str, Any]:
    rows = []
    for k, name, good in KEYS:
        x, y = a.get(k), b.get(k)
        if x is None or y is None or x == 0:
            continue
        ch = (y - x) / x * 100
        better = ch * good > 0
        rows.append({"key": k, "name": name, "a": x, "b": y, "change_pct": round(ch, 1),
                     "verdict": "within noise" if abs(ch) < noise_pct else ("better" if better else "worse")})
    worse = [r for r in rows if r["verdict"] == "worse"]
    better = [r for r in rows if r["verdict"] == "better"]
    note = []
    if a.get("clients") and b.get("clients") and a["clients"] != b["clients"]:
        note.append(f"The runs used different client counts ({a['clients']} and {b['clients']}): not a like-for-like comparison.")
    if a.get("tool") != b.get("tool"):
        note.append("The runs come from different tools.")
    return {"rows": rows, "noise_pct": noise_pct, "notes": note,
            "verdict": ("No change bigger than the noise." if not worse and not better else
                        (f"Slower: {', '.join(r['name'].lower() + ' ' + format(r['change_pct'], '+.1f') + '%' for r in worse)}." if worse else "") +
                        (" " if worse and better else "") +
                        (f"Faster: {', '.join(r['name'].lower() + ' ' + format(r['change_pct'], '+.1f') + '%' for r in better)}." if better else ""))}
