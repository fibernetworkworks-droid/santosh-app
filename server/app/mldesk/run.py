"""A training run read from its log: a CSV of epochs (or steps) with the losses and metrics, or the lines Keras, PyTorch Lightning,
Hugging Face and plain print loops write. It finds the best epoch, overfitting (validation loss turning up while training loss keeps
falling, and by how much), underfitting, a loss that diverges or goes NaN, plateaus, a learning rate that is too high (the loss
jumping about), a noisy validation set, and when early stopping would have stopped - all from the numbers in the log."""
from __future__ import annotations

import ast
import math
import re
from typing import Any


class RunError(ValueError):
    pass


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|nan|inf"


def _f(v: str) -> float:
    v = v.strip().lower()
    if v in ("nan", "inf", "-inf"):
        return float(v)
    return float(v)


def parse(text: str) -> tuple[list[dict[str, float]], str]:
    lines = [l for l in str(text or "").splitlines() if l.strip()]
    if not lines:
        raise RunError("Paste the training log: a CSV of epochs with losses, or the lines your trainer prints.")
    head = [h.strip().lower() for h in re.split(r"[,\t;]", lines[0])]
    if len(head) >= 2 and any(re.search(r"loss|acc|f1|auc|epoch|step", h) for h in head) and not re.search(r"\d+/\d+|[{}:='\"]", lines[0]):
        rows = []
        for n, l in enumerate(lines[1:], 2):
            parts = [p.strip() for p in re.split(r"[,\t;]", l)]
            if len(parts) != len(head):
                continue
            row = {}
            for h, p in zip(head, parts):
                if p == "":
                    continue
                try:
                    row[h] = _f(p)
                except ValueError:
                    pass
            if row:
                rows.append(row)
        return rows, "CSV"
    rows: list[dict[str, float]] = []
    cur_ep = None
    for l in lines:
        s = l.strip()
        ep = re.fullmatch(r"epoch\s*(\d+)\s*/\s*\d+\s*:?", s, re.I)
        if ep:
            cur_ep = float(ep.group(1))
            continue
        d = None
        m = re.search(r"\{[^{}]*'[^']+'\s*:\s*[^{}]+\}", s)
        if m:
            try:
                d = {str(k).lower(): float(v) for k, v in ast.literal_eval(m.group(0)).items() if isinstance(v, (int, float))}
            except (ValueError, SyntaxError):
                d = None
        if d is None:
            pairs = re.findall(r"([A-Za-z_][\w/.@-]*)\s*[:=]\s*(" + _NUM + r")(?![\w.])", s.replace("'", "").replace('"', ""), re.I)
            if not pairs:
                continue
            d = {}
            for k, v in pairs:
                try:
                    d[k.lower()] = _f(v)
                except ValueError:
                    pass
            e = re.search(r"\bepoch\s*[:=]?\s*\[?\s*(\d+)(?:\s*/\s*\d+)?", s, re.I)
            if e and "epoch" not in d:
                d["epoch"] = float(e.group(1))
            elif cur_ep is not None and "epoch" not in d:
                d["epoch"] = cur_ep
        if d:
            rows.append(d)
    if not rows:
        raise RunError("No numbers found in the log - paste lines like 'epoch 3 loss=0.41 val_loss=0.52' or a CSV with a header.")
    # Hugging Face / Lightning print eval lines apart from train lines: merge by epoch
    merged: dict[float, dict[str, float]] = {}
    order: list[float] = []
    for i, r in enumerate(rows):
        k = r.get("epoch", r.get("step", float(i)))
        if k not in merged:
            merged[k] = {}
            order.append(k)
        merged[k].update(r)
    return [merged[k] for k in order], "log"


def _pick(cols: set[str], *pats: str) -> str | None:
    for p in pats:
        for c in sorted(cols, key=len):
            if re.fullmatch(p, c):
                return c
    return None


def analyse(text: str, patience: int = 5, higher: str = "") -> dict[str, Any]:
    rows, fmt = parse(text)
    if len(rows) < 3:
        raise RunError("At least 3 epochs (or evaluation points) are needed to read a run.")
    if len(rows) > 200_000:
        raise RunError("Up to 200,000 rows.")
    cols = set().union(*rows)
    x = _pick(cols, r"epoch", r"step", r"global_step", r"iter(ation)?")
    tr = _pick(cols, r"loss", r"train_loss", r"train/loss", r"training_loss", r"train_loss_epoch", r"loss_epoch")
    va = _pick(cols, r"val_loss", r"eval_loss", r"valid_loss", r"validation_loss", r"val/loss", r"eval/loss", r"test_loss", r"val_loss_epoch")
    lr = _pick(cols, r"lr", r"learning_rate", r"lr-\w+", r"train/learning_rate")
    gn = _pick(cols, r"grad_norm", r"gradient_norm", r"train/grad_norm")
    mets = sorted(c for c in cols if c not in {x, tr, va, lr, gn} and re.search(r"(val|eval|valid|test).*(acc|f1|auc|precision|recall|map|iou|bleu|rouge|r2|exact|wer|cer|mae|rmse)", c))
    if not tr and not va:
        raise RunError("No loss column found - name them loss / train_loss and val_loss / eval_loss.")
    xs = [r.get(x, float(i)) if x else float(i) for i, r in enumerate(rows)]
    series = {c: [r.get(c) for r in rows] for c in [tr, va, lr, gn, *mets] if c}
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    out: dict[str, Any] = {"format": fmt, "x": x or "row", "points": len(rows), "train": tr, "val": va, "lr": lr, "metrics": mets, "columns": sorted(cols)}

    def clean(c: str) -> list[tuple[float, float]]:
        return [(a, b) for a, b in zip(xs, series[c]) if b is not None and math.isfinite(b)]

    for c in (tr, va):
        if not c:
            continue
        bad = [a for a, b in zip(xs, series[c]) if b is not None and not math.isfinite(b)]
        if bad:
            add("bad", "Divergence", f"{c} became {'NaN' if any(math.isnan(b) for b in series[c] if b is not None) else 'infinite'} at {out['x']} {bad[0]:g}.",
                "Lower the learning rate, add gradient clipping (max norm 1.0), check for log(0) or a division by zero, and in fp16 use loss scaling or bf16.")
    best = None
    if va and clean(va):
        v = clean(va)
        bi = min(range(len(v)), key=lambda i: v[i][1])
        best = {"at": v[bi][0], "val": v[bi][1], "index": bi}
        last = v[-1][1]
        out["best"] = best
        rise = (last - best["val"]) / abs(best["val"]) * 100 if best["val"] else 0
        out["since_best"] = len(v) - 1 - bi
        if tr and clean(tr):
            t = dict(clean(tr))
            gap_best = (best["val"] - t.get(best["at"], best["val"]))
            gap_last = last - t.get(v[-1][0], last)
            out["gap"] = {"at_best": gap_best, "at_end": gap_last}
            tfall = t.get(v[-1][0]) is not None and t.get(best["at"]) is not None and t[v[-1][0]] < t[best["at"]]
            if out["since_best"] >= max(2, patience // 2) and rise > 5 and tfall:
                add("bad" if rise > 20 else "warn", "Overfitting",
                    f"Validation loss was lowest at {out['x']} {best['at']:g} ({best['val']:.4g}) and rose {rise:.0f}% by the end while training loss kept falling - the model memorises the training set.",
                    f"Keep the checkpoint from {out['x']} {best['at']:g}; add regularisation (weight decay, dropout, augmentation), more data, or a smaller model.")
        if out["since_best"] >= patience:
            stop = v[min(len(v) - 1, bi + patience)][0]
            out["early_stop"] = stop
            add("info", "Early stopping", f"With patience {patience}, early stopping would have stopped at {out['x']} {stop:g} and kept {out['x']} {best['at']:g}"
                f" - {out['since_best'] - patience} {out['x']}(s) of training saved.", "EarlyStopping(monitor='val_loss', patience=" + str(patience) + ", restore_best_weights=True).")
        if len(v) >= 6:
            d = [b[1] - a[1] for a, b in zip(v, v[1:])]
            ups = sum(1 for i in range(1, len(d)) if (d[i] > 0) != (d[i - 1] > 0))
            if ups / len(d) > 0.6 and out["since_best"] < max(2, patience // 2):
                add("info", "Noise", "Validation loss zig-zags from one evaluation to the next - the validation set may be small or the learning rate high.", "Evaluate on more examples, or smooth by watching a moving average before deciding.")
    if tr and clean(tr):
        t = clean(tr)
        first, last = t[0][1], t[-1][1]
        out["train_drop"] = (first - last) / abs(first) * 100 if first else 0
        if len(t) >= 6:
            tail = [b for _, b in t[-max(3, len(t) // 5):]]
            rel = (max(tail) - min(tail)) / max(abs(sum(tail) / len(tail)), 1e-12)
            if rel < 0.01 and out["train_drop"] < 30:
                add("warn", "Underfitting", f"Training loss fell only {out['train_drop']:.0f}% and has stopped moving - the model is not learning much.",
                    "Raise the learning rate, train longer, use a bigger model, or check the labels and the input pipeline (shuffling, normalisation).")
            elif rel < 0.002:
                add("info", "Plateau", "Training loss has flattened over the last part of the run.", "A learning-rate schedule (cosine, step decay) or stopping earlier.")
            jumps = sum(1 for a, b in zip(t, t[1:]) if b[1] > a[1] * 1.25)
            if jumps >= max(2, len(t) // 10):
                add("warn", "Learning rate", f"Training loss jumped up by over 25% {jumps} times - the learning rate is likely too high.", "Halve the learning rate, add warm-up, and clip gradients.")
        if first and last > first * 0.98 and len(t) >= 4:
            add("bad", "Not learning", "Training loss did not go down from start to end.", "Check the learning rate (often 10x too high or too low), the loss function and that the labels match the inputs.")
    if va and tr and clean(va) and clean(tr):
        tv = dict(clean(tr))
        under = [a for a, b in clean(va) if a in tv and b < tv[a] * 0.8]
        if len(under) > len(clean(va)) * 0.7:
            add("info", "Validation", "Validation loss stays well below training loss - common with dropout / augmentation on in training, or a leak between the splits if it is extreme.", "If no regularisation explains it, check the same examples are not in both sets.")
    if lr and clean(lr):
        l_ = [b for _, b in clean(lr)]
        out["lr_range"] = [min(l_), max(l_)]
    if gn and clean(gn):
        g = [b for _, b in clean(gn)]
        med = sorted(g)[len(g) // 2]
        spikes = sum(1 for b in g if b > 10 * med)
        if spikes:
            add("warn", "Gradients", f"The gradient norm spiked over 10x its median {spikes} time(s).", "Clip gradients (max norm 1.0) and check for bad batches.")
    for c in mets:
        v = clean(c)
        if not v:
            continue
        hb = not re.search(r"mae|rmse|wer|cer|loss", c)
        bi = max(range(len(v)), key=lambda i: v[i][1]) if hb else min(range(len(v)), key=lambda i: v[i][1])
        out.setdefault("metric_best", {})[c] = {"at": v[bi][0], "value": v[bi][1], "last": v[-1][1]}
        if best and abs(v[bi][0] - best["at"]) > max(1, patience) and hb:
            add("info", "Metric", f"{c} was best at {out['x']} {v[bi][0]:g}, not where validation loss was lowest ({best['at']:g}) - pick the checkpoint by the metric you care about.", "")
    step = max(1, len(rows) // 400)
    out["series"] = {c: [[xs[i], series[c][i]] for i in range(0, len(rows), step) if series[c][i] is not None and math.isfinite(series[c][i])] for c in series}
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    v_ = f"best validation loss {best['val']:.4g} at {out['x']} {best['at']:g}" if best else f"training loss {clean(tr)[-1][1]:.4g} at the end" if tr and clean(tr) else ""
    b = out["counts"]["bad"]
    out["verdict"] = f"{len(rows)} {out['x']}s: {v_}" + (f" - {b} problem{'s' if b > 1 else ''}" if b else "")
    out["note"] = ("Read from the logged numbers only. One run on one seed: differences of a few percent between runs can be noise - "
                   "repeat with another seed before trusting a small gain.")
    return out
