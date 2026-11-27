"""Frame timing: a PresentMon CSV (MsBetweenPresents / FrameTime, CPUBusy / GPUBusy when there), a CSV with a frame-time column,
or plain numbers in milliseconds -> average FPS, percentiles, 1% / 0.1% lows, stutters, time over her frame budget, and whether
the CPU or the GPU looks like the limit. Also GPU pass timings ('name, ms' lines) -> their share of the frame."""
from __future__ import annotations

import csv
import io
import re
from statistics import median
from typing import Any

MAX = 3_000_000
MAX_FRAMES = 500_000
COLS = ("msbetweenpresents", "frametime", "frame time", "ms", "frametime_ms", "frame_ms", "msbetweendisplaychange", "displayedtime")


def _num(x: str) -> float | None:
    try:
        v = float(str(x).strip())
    except (TypeError, ValueError):
        return None
    return v if v == v and 0 < v < 10_000 else None


def read_times(text: str) -> tuple[list[float], dict[str, list[float]], str]:
    text = str(text or "")[:MAX].strip()
    if not text:
        return [], {}, ""
    first = text.split("\n", 1)[0]
    if "," in first and re.search(r"[A-Za-z]", first):
        rows = list(csv.reader(io.StringIO(text)))
        head = [h.strip().lower() for h in rows[0]]
        col = next((head.index(c) for c in COLS if c in head), None)
        if col is None:
            col = next((i for i, h in enumerate(head) if "frame" in h and "time" in h), None)
        if col is None:
            return [], {}, "No frame-time column found (MsBetweenPresents, FrameTime or ms)."
        extra = {k: head.index(k) for k in ("cpubusy", "gpubusy", "msgpuactive", "msuntilrenderstart") if k in head}
        times, more = [], {k: [] for k in extra}
        for r in rows[1:MAX_FRAMES + 1]:
            if len(r) <= col:
                continue
            v = _num(r[col])
            if v is None:
                continue
            times.append(v)
            for k, i in extra.items():
                w = _num(r[i]) if len(r) > i else None
                if w is not None:
                    more[k].append(w)
        return times, {k: v for k, v in more.items() if v}, head[col]
    vals = [_num(x) for x in re.split(r"[\s,;]+", text)[:MAX_FRAMES]]
    return [v for v in vals if v is not None], {}, "numbers"


def _pct(sorted_v: list[float], p: float) -> float:
    if not sorted_v:
        return 0.0
    k = (len(sorted_v) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    return sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f)


def analyse(text: str, target_fps: float = 60.0) -> dict[str, Any]:
    times, more, col = read_times(text)
    if len(times) < 10:
        return {"ok": False, "error": col if col and "No frame" in col else "At least 10 frame times are needed."}
    s = sorted(times)
    n = len(times)
    total = sum(times)
    budget = 1000.0 / float(target_fps or 60)
    worst1 = s[-max(1, n // 100):]
    worst01 = s[-max(1, n // 1000):]
    stutters = []
    w = 30
    for i, t in enumerate(times):
        lo, hi = max(0, i - w), min(n, i + w)
        m = median(times[lo:hi])
        if t > 2 * m and t > budget:
            stutters.append({"i": i, "ms": round(t, 2), "typical": round(m, 2)})
    step = max(1, n // 600)
    series = [round(max(times[i:i + step]), 2) for i in range(0, n, step)]
    hist = [0] * 12
    for t in times:
        hist[min(11, int(t / budget * 4))] += 1
    out: dict[str, Any] = {"ok": True, "column": col, "frames": n, "seconds": round(total / 1000, 2), "avg_fps": round(1000 * n / total, 1),
                           "median_ms": round(_pct(s, 0.5), 2), "p95_ms": round(_pct(s, 0.95), 2), "p99_ms": round(_pct(s, 0.99), 2),
                           "max_ms": round(s[-1], 2), "low1_fps": round(1000 / (sum(worst1) / len(worst1)), 1),
                           "low01_fps": round(1000 / (sum(worst01) / len(worst01)), 1), "budget_ms": round(budget, 2), "target_fps": target_fps,
                           "over_budget": round(sum(1 for t in times if t > budget) / n, 4), "stutters": len(stutters),
                           "stutter_list": stutters[:30], "series": series, "hist": hist}
    if "cpubusy" in more and "gpubusy" in more and more["cpubusy"] and more["gpubusy"]:
        c, g = median(more["cpubusy"]), median(more["gpubusy"])
        out["cpu_ms"], out["gpu_ms"] = round(c, 2), round(g, 2)
        out["bound"] = "GPU" if g > c * 1.1 else "CPU" if c > g * 1.1 else "both about the same"
    verdict = [f"{out['avg_fps']} FPS on average, 1% low {out['low1_fps']} FPS."]
    if out["over_budget"] > 0.05:
        verdict.append(f"{out['over_budget'] * 100:.1f}% of frames miss the {budget:.1f} ms budget for {target_fps:g} FPS.")
    if out["stutters"]:
        verdict.append(f"{out['stutters']} stutter(s): frames over twice the frames around them.")
    if out.get("bound"):
        verdict.append(f"Looks {out['bound']}-bound (CPU {out['cpu_ms']} ms, GPU {out['gpu_ms']} ms median).")
    out["verdict"] = " ".join(verdict)
    return out


def passes(text: str, target_fps: float = 60.0) -> dict[str, Any]:
    rows = []
    for ln in str(text or "")[:200_000].splitlines():
        m = re.match(r"\s*(.+?)\s*[,;\t:|]\s*([\d.]+)\s*(ms)?\s*$", ln)
        if m and not re.match(r"(?i)^(pass|name)$", m.group(1).strip()):
            v = _num(m.group(2))
            if v is not None:
                rows.append({"name": m.group(1).strip()[:80], "ms": v})
    if not rows:
        return {"ok": False, "error": "Write one pass per line: name, milliseconds."}
    total = sum(r["ms"] for r in rows)
    budget = 1000.0 / float(target_fps or 60)
    rows.sort(key=lambda r: -r["ms"])
    for r in rows:
        r["share"] = round(r["ms"] / total, 4)
        r["of_budget"] = round(r["ms"] / budget, 4)
    return {"ok": True, "passes": rows[:80], "total_ms": round(total, 3), "budget_ms": round(budget, 2), "over": total > budget,
            "verdict": (f"The passes add up to {total:.2f} ms of a {budget:.2f} ms budget" + (" - over it." if total > budget else ".") +
                        f" The biggest is {rows[0]['name']} ({rows[0]['ms']:.2f} ms, {rows[0]['share'] * 100:.0f}%).")}
