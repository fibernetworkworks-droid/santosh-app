"""How much GPU a model needs, in code: the memory its weights take at a precision, the KV cache for a context length and batch
(from the layer count, KV heads and head size), whether it fits the GPUs with room for the runtime, the largest batch that fits,
the upper bound of decoding speed from memory bandwidth, and for training the memory of full fine-tuning with Adam, LoRA or QLoRA
and the compute of a training run (about 6 x parameters x tokens) in GPU-hours at her utilisation. GPU figures are datasheet values."""
from __future__ import annotations

import math
import re
from typing import Any


class SizingError(ValueError):
    pass


BYTES = {"fp32": 4.0, "tf32": 4.0, "fp16": 2.0, "bf16": 2.0, "fp8": 1.0, "int8": 1.0, "int4": 0.5, "nf4": 0.5, "gptq": 0.5, "awq": 0.5, "q4": 0.5, "q8": 1.0}
# name: (memory GB, memory bandwidth GB/s, dense bf16/fp16 tensor TFLOPS) - datasheet values; give gpu_mem= / bw= / tflops= to override
GPUS = {"h200": (141, 4800, 989), "h100": (80, 3350, 989), "h100-pcie": (80, 2000, 756), "a100-80": (80, 2039, 312), "a100-40": (40, 1555, 312),
        "a100": (80, 2039, 312), "l40s": (48, 864, 362), "l4": (24, 300, 121), "a10": (24, 600, 125), "a10g": (24, 600, 70), "t4": (16, 320, 65),
        "v100": (32, 900, 125), "a6000": (48, 768, 155), "rtx 6000 ada": (48, 960, 364), "rtx 4090": (24, 1008, 165), "4090": (24, 1008, 165),
        "rtx 3090": (24, 936, 71), "3090": (24, 936, 71), "mi300x": (192, 5300, 1307), "mi250x": (128, 3277, 383)}


def _n(v: str) -> float:
    m = re.fullmatch(r"\s*([\d.]+)\s*([kmbt])?\s*", v.lower())
    if not m:
        raise SizingError(f"'{v}' is not a number (e.g. 7B, 70e9, 8192).")
    return float(m.group(1)) * {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12, None: 1}[m.group(2)]


def gb(b: float) -> float:
    return b / 1e9


def analyse(text: str, util: float = 0.9, mfu: float = 0.4) -> dict[str, Any]:
    t = str(text or "").lower()
    if not t.strip():
        raise SizingError("Describe the model and the GPUs: 'model 8B bf16 layers=32 kv_heads=8 head_dim=128', 'serve context=8192 batch=16', 'gpu h100 x2'.")
    kv = {k: v for k, v in re.findall(r"([a-z_]+)\s*=\s*([\w.]+)", t)}
    m = re.search(r"\b([\d.]+)\s*([kmbt])\b(?!\s*tokens)", t)
    if "params" in kv:
        N = _n(kv["params"])
    elif m:
        N = _n(m.group(1) + m.group(2))
    else:
        raise SizingError("Give the parameter count: 'model 8B' or params=8e9.")
    if not 1e5 <= N <= 1e13:
        raise SizingError("Parameters: between 100 thousand and 10 trillion.")
    prec = next((p for p in sorted(BYTES, key=len, reverse=True) if re.search(rf"\b{p}\b", t)), "bf16")
    kvp = kv.get("kv_dtype", "fp16" if BYTES[prec] >= 2 else prec if prec in ("fp8", "int8") else "fp16")
    if kvp not in BYTES:
        raise SizingError("kv_dtype: fp16, bf16, fp8 or int8.")
    gpu_name = None
    gm = re.search(r"\bgpus?\s+([a-z0-9 .\-]+?)(?:\s*x\s*(\d+)|\s+count\s*=\s*(\d+)|$|\n|,)", t)
    count = 1
    mem = bw = tf = None
    if gm:
        nm = gm.group(1).strip().replace("nvidia ", "").replace("-sxm", "")
        nm = re.sub(r"\s*(\d+)\s*gb$", lambda x: "-" + x.group(1) if nm.startswith("a100") else "", nm).strip()
        gpu_name = next((k for k in sorted(GPUS, key=len, reverse=True) if k == nm or nm.startswith(k)), None)
        count = int(gm.group(2) or gm.group(3) or 1)
        if gpu_name:
            mem, bw, tf = GPUS[gpu_name]
    for k_, cast in (("gpu_mem", "mem"), ("bw", "bw"), ("tflops", "tf")):
        if k_ in kv:
            v = float(re.sub(r"[a-z]+$", "", kv[k_]))
            if cast == "mem":
                mem = v
            elif cast == "bw":
                bw = v
            else:
                tf = v
    if "count" in kv:
        count = int(kv["count"])
    if gm and not gpu_name and mem is None:
        raise SizingError(f"Unknown GPU '{gm.group(1).strip()}' - give its memory with gpu_mem=80 (GB), and bw= / tflops= for speed.")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, txt, fix="": issues.append({"sev": sev, "area": area, "text": txt, "fix": fix})   # noqa: E731
    W = N * BYTES[prec]
    out: dict[str, Any] = {"params": N, "precision": prec, "weights_gb": gb(W), "gpu": gpu_name or ("custom" if mem else None), "count": count, "mem_gb": mem,
                           "bw": bw, "tflops": tf, "util": util}
    L_ = int(_n(kv["layers"])) if "layers" in kv else None
    kvh = int(_n(kv.get("kv_heads", kv.get("heads", "0")))) or None
    hd = int(_n(kv["head_dim"])) if "head_dim" in kv else (int(_n(kv["hidden"]) / _n(kv["heads"])) if "hidden" in kv and "heads" in kv else None)
    ctx = int(_n(kv.get("context", kv.get("ctx", "0")))) or None
    batch = int(_n(kv.get("batch", "1")))
    per_tok = 2 * L_ * kvh * hd * BYTES[kvp] if L_ and kvh and hd else None
    out.update(layers=L_, kv_heads=kvh, head_dim=hd, context=ctx, batch=batch, kv_dtype=kvp)
    serve = None
    if per_tok:
        out["kv_per_token_mb"] = per_tok / 1e6
        if ctx:
            kvb = per_tok * ctx * batch
            over = 0.1 * W + 1e9 * count
            total = W + kvb + over
            serve = {"kv_gb": gb(kvb), "overhead_gb": gb(over), "total_gb": gb(total)}
            if mem:
                avail = mem * 1e9 * count * util
                serve["fits"] = total <= avail
                serve["max_batch"] = max(0, int((avail - W - over) // (per_tok * ctx)))
                serve["max_context"] = max(0, int((avail - W - over) // (per_tok * batch)))
                serve["gpus_needed"] = math.ceil(total / (mem * 1e9 * util))
                if not serve["fits"]:
                    add("bad", "Memory", f"Serving needs about {gb(total):.1f} GB but {count} x {mem:g} GB at {util * 100:.0f}% use gives {avail / 1e9:.1f} GB.",
                        f"Use {serve['gpus_needed']} GPUs (tensor parallel), a smaller batch (up to {serve['max_batch']}), a shorter context, an fp8 KV cache, or a 4-bit model.")
                elif serve["max_batch"] < 2 * batch:
                    add("warn", "Memory", f"It fits, but only up to batch {serve['max_batch']} at this context - little room for more users.", "")
        elif mem and W > mem * 1e9 * count * util:
            add("bad", "Memory", f"The weights alone ({gb(W):.1f} GB) do not fit {count} x {mem:g} GB.", "More GPUs, or a lower precision (int8 / 4-bit).")
    else:
        if mem and W > mem * 1e9 * count * util:
            add("bad", "Memory", f"The weights alone ({gb(W):.1f} GB at {prec}) do not fit {count} x {mem:g} GB.", "More GPUs, or a lower precision (int8 / 4-bit).")
        add("info", "KV cache", "Give layers=, kv_heads= and head_dim= (or hidden= and heads=) and a context= to size the KV cache - the config.json of the model has them.", "")
    out["serve"] = serve
    if bw:
        dec = bw * 1e9 * count / W
        out["decode_tok_s"] = dec
        add("info", "Speed", f"Decoding one sequence is limited by memory bandwidth to about {dec:.0f} tokens/s at most (every weight read once per token); "
            "batching raises the total, not this.", "")
    tr = re.search(r"\btrain\w*\b(.*)", t)
    train = None
    if tr:
        mode = "qlora" if "qlora" in tr.group(1) else "lora" if "lora" in tr.group(1) else "full"
        if mode == "full":
            mem_b = 16 * N if BYTES[prec] <= 2 else 16 * N
            what = "weights + gradients in 16-bit, fp32 master weights and two Adam moments: 16 bytes a parameter"
            trainable = N
        else:
            r_ = int(kv.get("rank", "16"))
            hid = _n(kv["hidden"]) if "hidden" in kv else (kvh * hd * 4 if kvh and hd else math.sqrt(N / 12 / max(L_ or 32, 1)))
            trainable = 4 * 2 * r_ * hid * (L_ or 32)
            wbytes = 0.5 if mode == "qlora" else BYTES[prec]
            mem_b = N * wbytes + 16 * trainable
            what = f"frozen weights at {'4-bit' if mode == 'qlora' else prec} + LoRA rank {r_} on the attention projections ({trainable / 1e6:.1f}M trainable) with Adam"
        train = {"mode": mode, "gb": gb(mem_b), "what": what, "trainable": trainable}
        tok = re.search(r"([\d.]+\s*[kmbt]?)\s*tokens", t)
        if tok:
            D = _n(tok.group(1))
            flops = (6 if mode == "full" else 4) * N * D     # frozen weights: no weight gradients, about 4 x N x D
            train.update(tokens=D, flops=flops)
            if tf:
                secs = flops / (tf * 1e12 * mfu * count)
                train.update(gpu_hours=flops / (tf * 1e12 * mfu) / 3600, days=secs / 86400)
        if mem:
            if mode == "full" and mem_b > mem * 1e9 * count * util:
                add("warn", "Training", f"Full fine-tuning needs about {gb(mem_b):.0f} GB before activations - more than {count} x {mem:g} GB.",
                    f"Shard it (ZeRO-3 / FSDP over at least {math.ceil(mem_b / (mem * 1e9 * util))} GPUs), or use LoRA / QLoRA.")
            elif mem_b > mem * 1e9 * count * util:
                add("warn", "Training", f"{mode.upper()} needs about {gb(mem_b):.1f} GB before activations - more than the GPUs hold.", "QLoRA, more GPUs, or a smaller model.")
        add("info", "Activations", "Training memory above leaves out activations, which grow with batch x sequence length.", "Gradient checkpointing trades about a third more compute for most of that memory.")
    out["train"] = train
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    out["verdict"] = (f"{N / 1e9:.3g}B parameters at {prec}: {gb(W):.1f} GB of weights"
                      + (f", {serve['total_gb']:.1f} GB to serve {batch} x {ctx:,} tokens" if serve else "")
                      + (f" - {'fits' if serve.get('fits') else 'does not fit'} {count} x {gpu_name or 'GPU'}" if serve and "fits" in serve else ""))
    out["note"] = ("Estimates from the model's shape and datasheet figures: real serving adds the framework's own buffers and fragmentation, "
                   "and real speed is lower than the bandwidth bound. Measure on the hardware before you buy or promise latency.")
    return out
