"""A vision pipeline's speed worked out from its stages (decode, resize, the model, NMS, tracking...): per frame the latency is the sum
of the stages, but run as threads the frame rate is set by the slowest one - so both are shown, against the camera's rate and her
target. Measured latency samples (one number a line, or a benchmark log) give percentiles and the frames that come late. And the
camera's resolution against the model's input size: how small an object gets after the resize, and whether tiling would help."""
from __future__ import annotations

import math
import re
from typing import Any


class PipelineError(ValueError):
    pass


def _ms(v: str) -> float:
    m = re.fullmatch(r"\s*([\d.]+)\s*(ms|us|µs|s)?\s*", v, re.I)
    if not m:
        raise PipelineError(f"'{v}' is not a time - e.g. 12ms.")
    return float(m.group(1)) * {"ms": 1, "us": 1e-3, "µs": 1e-3, "s": 1000}[(m.group(2) or "ms").lower()]


def _pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * q
    f = math.floor(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)


def analyse(text: str, target_fps: Any = "", min_px: float = 20) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    samples: list[float] = []
    camera = None
    res = None
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        s = raw.split("#")[0].strip()
        if not s:
            continue
        low = s.lower()
        if re.fullmatch(r"[\d.]+\s*(ms|us|µs|s)?", low):
            samples.append(_ms(low))
            continue
        m = re.search(r"(?:latency|inference|time)[^\d]{0,20}([\d.]+)\s*(ms|us|µs|s)\b", low)
        if m and re.search(r"\b(iter|run|frame|batch|step)\b", low):
            samples.append(_ms(m.group(1) + m.group(2)))
            continue
        if low.startswith("camera"):
            r_ = re.search(r"(\d+)\s*[x×]\s*(\d+)", low)
            f_ = re.search(r"([\d.]+)\s*fps", low)
            if not f_:
                raise PipelineError(f"Line {n}: 'camera 1920x1080 30fps'.")
            camera = {"fps": float(f_.group(1)), "W": int(r_.group(1)) if r_ else None, "H": int(r_.group(2)) if r_ else None}
            continue
        if low.startswith(("model", "input", "resize")):
            i_ = re.search(r"(?:input|size|imgsz)\s*=?\s*(\d+)(?:\s*[x×]\s*(\d+))?", low)
            o_ = re.search(r"object\s*=?\s*([\d.]+)\s*px", low)
            if not i_:
                raise PipelineError(f"Line {n}: 'model input=640 object=24px' (the object's size in camera pixels).")
            res = {"in_w": int(i_.group(1)), "in_h": int(i_.group(2) or i_.group(1)), "obj": float(o_.group(1)) if o_ else None,
                   "letterbox": "stretch" not in low}
            continue
        m = re.fullmatch(r"([A-Za-z][\w .+/-]*?)\s*[:=]?\s+([\d.]+\s*(?:ms|us|µs|s)?)\s*(.*)", s)
        if m:
            extra = m.group(3).lower()
            stages.append({"name": m.group(1).strip(), "ms": _ms(m.group(2)), "gpu": "gpu" in extra or "cuda" in extra or "npu" in extra,
                           "every": int(e.group(1)) if (e := re.search(r"every\s+(\d+)", extra)) else 1, "line": n})
            continue
        raise PipelineError(f"Line {n}: '{s[:60]}' - a stage ('inference 18ms'), a camera ('camera 1920x1080 30fps'), a model ('model input=640 object=24px') or a latency sample (one number).")
    if not stages and not samples and not res:
        raise PipelineError("One stage per line with its time ('decode 4ms', 'inference 18ms gpu', 'nms 1.5ms'), latency samples (one number a line), "
                            "a camera line ('camera 1920x1080 30fps') and the model input ('model input=640 object=24px').")
    tfps = None
    if str(target_fps or "").strip():
        try:
            tfps = float(target_fps)
        except (TypeError, ValueError):
            raise PipelineError("Target frame rate: a number.")
        if tfps <= 0:
            raise PipelineError("Target frame rate: above 0.")
    need = tfps or (camera["fps"] if camera else None)
    out: dict[str, Any] = {"stages": [], "camera": camera, "target_fps": tfps}
    if stages:
        per_frame = [st["ms"] / st["every"] for st in stages]
        total = sum(st["ms"] for st in stages)
        avg = sum(per_frame)
        slow = max(range(len(stages)), key=lambda i: per_frame[i])
        seq_fps = 1000 / avg if avg else float("inf")
        par_fps = 1000 / per_frame[slow] if per_frame[slow] else float("inf")
        gpu = sum(p for p, st in zip(per_frame, stages) if st["gpu"])
        cpu = avg - gpu
        par_fps = min(par_fps, 1000 / max(gpu, 1e-9) if gpu else float("inf"))
        out.update(stages=[{**st, "per_frame": p, "share": p / avg if avg else 0} for st, p in zip(stages, per_frame)], latency=total, avg=avg,
                   seq_fps=seq_fps, par_fps=par_fps, slowest=stages[slow]["name"], gpu_ms=gpu, cpu_ms=cpu)
        if need:
            budget = 1000 / need
            out["budget"] = budget
            if seq_fps < need and par_fps >= need:
                add("warn", "Frame rate", f"One after another the stages give {seq_fps:.1f} fps, short of {need:g} - run as a pipeline (each stage its own thread, frames in flight) they reach {par_fps:.1f} fps.",
                    "Overlap the stages with queues; latency stays at the sum of the stages.")
            elif par_fps < need:
                add("bad", "Frame rate", f"Even pipelined, {stages[slow]['name']} ({per_frame[slow]:.1f} ms) holds the rate to {par_fps:.1f} fps - under the {need:g} needed (a frame every {budget:.1f} ms).",
                    f"Speed up {stages[slow]['name']} (a smaller model or input, FP16 / INT8 with TensorRT or OpenVINO, batching), run it every 2nd frame with tracking between, or drop the rate.")
            if camera and camera["fps"] > par_fps and not tfps:
                add("info", "Frame rate", f"The camera gives {camera['fps']:g} fps and the pipeline keeps {par_fps:.1f}: {(1 - par_fps / camera['fps']) * 100:.0f}% of frames are dropped.", "Drop frames on purpose (keep the newest) so latency does not build up in a queue.")
        if gpu and cpu > gpu * 2 and stages[slow]["gpu"] is False:
            add("info", "Balance", f"The CPU side ({cpu:.1f} ms) outweighs the GPU ({gpu:.1f} ms) - the GPU waits on it.", "Move resizing / colour conversion onto the GPU (NVIDIA DALI, VPI, CUDA kernels) or decode with the hardware decoder.")
    if samples:
        if len(samples) < 20:
            add("info", "Samples", f"Only {len(samples)} latency samples - the high percentiles are guesses below about 100.", "")
        warm = samples[: min(5, len(samples) // 10)] if len(samples) >= 50 else []
        xs = samples[len(warm):]
        p = {k: _pct(xs, q) for k, q in (("p50", .5), ("p90", .9), ("p95", .95), ("p99", .99))}
        mean = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / max(1, len(xs) - 1))
        out["samples"] = {"n": len(samples), "warmup": len(warm), **p, "max": max(xs), "min": min(xs), "mean": mean, "sd": sd,
                          "hist": _hist(xs), "series": [round(x, 3) for x in samples[:: max(1, len(samples) // 400)]]}
        if warm and sum(warm) / len(warm) > 2 * p["p50"]:
            add("info", "Warm-up", f"The first {len(warm)} runs were slow ({sum(warm) / len(warm):.1f} ms on average) and were left out - engines build and caches fill on the first frames.", "Run a few frames at start-up before going live.")
        if need:
            late = sum(1 for x in xs if x > 1000 / need)
            out["samples"]["late"] = late
            if late / len(xs) > 0.01:
                add("bad" if late / len(xs) > 0.05 else "warn", "Latency", f"{late} of {len(xs)} frames ({late / len(xs) * 100:.1f}%) took longer than the {1000 / need:.1f} ms a frame has at {need:g} fps.",
                    "Look at what the slow frames have in common (many objects -> NMS, a busy CPU, thermal throttling on embedded boards).")
        if p["p99"] > 2 * p["p50"]:
            add("warn", "Latency", f"The slowest 1% take {p['p99']:.1f} ms, over twice the median {p['p50']:.1f} ms - a long tail.",
                "On Jetson-class boards lock the clocks (jetson_clocks / nvpmodel) and watch the temperature; on PCs pin the process and check other loads.")
    if res:
        if camera and camera.get("W"):
            sc = min(res["in_w"] / camera["W"], res["in_h"] / camera["H"]) if res["letterbox"] else res["in_w"] / camera["W"]
            res["scale"] = sc
            if res["obj"]:
                res["obj_after"] = res["obj"] * sc
                if res["obj_after"] < min_px / 2:
                    tiles = math.ceil(min_px / 2 / res["obj_after"])
                    res["tiles"] = tiles * tiles
                    add("bad", "Resolution", f"A {res['obj']:g} px object becomes {res['obj_after']:.1f} px after shrinking {camera['W']}x{camera['H']} to {res['in_w']}x{res['in_h']} - too small for most detectors.",
                        f"Tile the frame into about {tiles} x {tiles} pieces (SAHI-style), raise the input size, or crop to the area of interest.")
                elif res["obj_after"] < min_px:
                    add("warn", "Resolution", f"A {res['obj']:g} px object becomes {res['obj_after']:.1f} px at the model's input - small objects like this are found much less often.", "A larger input size or a crop helps.")
        out["resolution"] = res
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    parts = []
    if stages:
        parts.append(f"{out['latency']:.1f} ms a frame, {out['par_fps']:.1f} fps pipelined ({out['seq_fps']:.1f} one after another)")
    if samples:
        parts.append(f"measured p50 {out['samples']['p50']:.1f} ms, p99 {out['samples']['p99']:.1f} ms")
    if res and res.get("obj_after") is not None:
        parts.append(f"objects {res['obj_after']:.1f} px at the model")
    out["verdict"] = "; ".join(parts)
    out["note"] = ("Stage times are what you give - measure them on the target device with the real input, after warm-up. Pipelining raises "
                   "the frame rate, never lowers the latency of one frame.")
    return out


def _hist(xs: list[float], bins: int = 24) -> list[list[float]]:
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-9:
        return [[lo, len(xs)]]
    w = (hi - lo) / bins
    h = [0] * bins
    for x in xs:
        h[min(bins - 1, int((x - lo) / w))] += 1
    return [[round(lo + i * w, 4), c] for i, c in enumerate(h)]
