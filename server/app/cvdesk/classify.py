"""Image classification scored from one line per image (id, true class, predicted class, and the model's score if she has it):
accuracy with its 95% interval, per-class precision / recall / F1 and support, macro and weighted F1, Cohen's kappa, the confusion
matrix and the pairs most confused; with scores, calibration (expected calibration error, a reliability table), and for two classes
the ROC AUC, the precision-recall curve and the threshold that reaches the precision or recall she needs."""
from __future__ import annotations

import math
import re
from typing import Any


class ClassifyError(ValueError):
    pass


def parse(text: str) -> list[dict[str, Any]]:
    rows = []
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        s = raw.split("#")[0].strip()
        if not s:
            continue
        p = [x for x in re.split(r"[,\t;]+|\s+", s) if x]
        if n == 1 and re.fullmatch(r"(id|image|img|file|filename|name)", p[0], re.I):
            continue
        if len(p) < 3:
            raise ClassifyError(f"Line {n}: image, true class, predicted class (and a score from 0 to 1 if you have it).")
        sc = None
        if len(p) >= 4:
            try:
                sc = float(p[3])
            except ValueError:
                raise ClassifyError(f"Line {n}: the score '{p[3]}' is not a number.")
            if not 0 <= sc <= 1:
                raise ClassifyError(f"Line {n}: the score must be from 0 to 1 (a probability, not a logit).")
        rows.append({"id": p[0], "true": p[1], "pred": p[2], "score": sc})
    if len(rows) < 5:
        raise ClassifyError("At least 5 lines: image, true class, predicted class (and a score from 0 to 1).")
    if len(rows) > 2_000_000:
        raise ClassifyError("Up to 2,000,000 lines.")
    return rows


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def evaluate(text: str, positive: str = "", need: str = "") -> dict[str, Any]:
    rows = parse(text)
    labels = sorted({r["true"] for r in rows} | {r["pred"] for r in rows}, key=lambda c: (-sum(1 for r in rows if r["true"] == c), c))
    if len(labels) > 400:
        raise ClassifyError("Up to 400 classes.")
    ix = {c: i for i, c in enumerate(labels)}
    K = len(labels)
    M = [[0] * K for _ in range(K)]
    for r in rows:
        M[ix[r["true"]]][ix[r["pred"]]] += 1
    n = len(rows)
    right = sum(M[i][i] for i in range(K))
    per = []
    for c, i in ix.items():
        tp = M[i][i]
        sup = sum(M[i])
        said = sum(M[j][i] for j in range(K))
        p = tp / said if said else None
        r_ = tp / sup if sup else None
        f1 = 2 * p * r_ / (p + r_) if p is not None and r_ is not None and p + r_ else (0.0 if sup else None)
        per.append({"cls": c, "support": sup, "said": said, "p": p, "r": r_, "f1": f1})
    real = [x for x in per if x["support"]]
    macro = sum(x["f1"] or 0 for x in real) / len(real)
    weighted = sum((x["f1"] or 0) * x["support"] for x in real) / n
    pe = sum(sum(M[i]) * sum(M[j][i] for j in range(K)) for i in range(K)) / (n * n)
    acc = right / n
    kappa = (acc - pe) / (1 - pe) if pe < 1 else 1.0
    pairs = sorted(({"truth": labels[i], "said": labels[j], "n": M[i][j]} for i in range(K) for j in range(K) if i != j and M[i][j]), key=lambda x: -x["n"])
    lo, hi = wilson(right, n)
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    out: dict[str, Any] = {"n": n, "labels": labels, "matrix": M if K <= 40 else None, "classes": per, "accuracy": acc, "acc_ci": [lo, hi],
                           "macro_f1": macro, "weighted_f1": weighted, "kappa": kappa, "pairs": pairs[:20]}
    big = max(x["support"] for x in real)
    small = min(x["support"] for x in real)
    if big >= 10 * max(1, small):
        top = max(real, key=lambda x: x["support"])
        add("warn", "Balance", f"The classes are lopsided: {top['cls']} has {big} images, the smallest class {small} - accuracy mostly measures {top['cls']}.",
            "Read the macro F1 and each class's recall, not the accuracy.")
        if acc - top["support"] / n < 0.02:
            add("bad", "Balance", f"Accuracy {acc * 100:.1f}% is barely above always saying {top['cls']} ({top['support'] / n * 100:.1f}%).", "The model has learnt little beyond the majority class.")
    for x in real:
        if x["r"] is not None and x["r"] < 0.5 and x["support"] >= 5:
            add("warn", "Classes", f"{x['cls']}: only {x['r'] * 100:.0f}% of its {x['support']} images are recognised.", "More examples of it, or look at which class takes them (the confusion matrix).", x["cls"])
    if pairs and pairs[0]["n"] >= max(3, 0.05 * n):
        pr = pairs[0]
        add("info", "Confusion", f"The most common mistake: {pr['truth']} called {pr['said']} ({pr['n']} times).", "Look at those images - often the labels themselves disagree.")
    sc = [r for r in rows if r["score"] is not None]
    if sc:
        bins = []
        ece = 0.0
        for b in range(10):
            lo_, hi_ = b / 10, (b + 1) / 10
            inb = [r for r in sc if (lo_ <= r["score"] < hi_) or (b == 9 and r["score"] == 1.0)]
            if inb:
                conf = sum(r["score"] for r in inb) / len(inb)
                accb = sum(1 for r in inb if r["true"] == r["pred"]) / len(inb)
                ece += len(inb) / len(sc) * abs(accb - conf)
                bins.append({"lo": lo_, "hi": hi_, "n": len(inb), "conf": conf, "acc": accb})
        out["calibration"] = {"ece": ece, "bins": bins, "scored": len(sc)}
        if ece > 0.1:
            over = sum(b["n"] * (b["conf"] - b["acc"]) for b in bins) > 0
            add("warn", "Calibration", f"The scores are {'over' if over else 'under'}confident: they are off from the real hit rate by {ece * 100:.1f} points on average (expected calibration error).",
                "Fit temperature scaling on a held-out set before using the score as a probability or a threshold.")
    if len(labels) == 2 and sc and len(sc) == n:
        pos = positive if positive in labels else labels[1] if labels[0].lower() in ("0", "neg", "negative", "no", "ok", "good", "normal", "false") else labels[0]
        neg = next(c for c in labels if c != pos)
        # a score is the confidence in the PREDICTED class; turn it into the score for the positive class
        ps = [(r["score"] if r["pred"] == pos else 1 - r["score"], r["true"] == pos) for r in rows]
        ps.sort(key=lambda x: -x[0])
        P = sum(1 for _, y in ps if y)
        N = len(ps) - P
        if P and N:
            tp = fp = 0
            roc, pr, best = [[0.0, 0.0]], [], []
            prev = None
            auc = 0.0
            last = (0.0, 0.0)
            for s_, y in ps:
                if prev is not None and s_ != prev:
                    roc.append([fp / N, tp / P])
                    auc += (fp / N - last[0]) * (tp / P + last[1]) / 2
                    last = (fp / N, tp / P)
                    pr.append([tp / P, tp / (tp + fp)])
                    best.append((prev, tp / (tp + fp), tp / P))
                tp += y
                fp += not y
                prev = s_
            roc.append([fp / N, tp / P])
            auc += (fp / N - last[0]) * (tp / P + last[1]) / 2
            pr.append([tp / P, tp / (tp + fp)])
            best.append((prev, tp / (tp + fp), tp / P))
            out["binary"] = {"positive": pos, "negative": neg, "auc": auc, "roc": roc[:: max(1, len(roc) // 300)] + [roc[-1]],
                             "pr": pr[:: max(1, len(pr) // 300)], "pos": P, "neg": N}
            m = re.fullmatch(r"\s*(precision|recall)\s*(?:>=|=|at least)?\s*([\d.]+)\s*%?\s*", str(need or ""), re.I)
            if m:
                kind, v = m.group(1).lower(), float(m.group(2))
                v = v / 100 if v > 1 else v
                ok = [b for b in best if (b[1] if kind == "precision" else b[2]) >= v]
                pick = (max(ok, key=lambda b: b[2]) if kind == "precision" else max(ok, key=lambda b: b[1])) if ok else None
                out["binary"]["need"] = {"kind": kind, "value": v, "thr": pick[0] if pick else None, "p": pick[1] if pick else None, "r": pick[2] if pick else None}
                if not pick:
                    add("bad", "Threshold", f"No threshold reaches {kind} {v * 100:g}% on these images.", "The model needs to get better before that target is possible.")
            if auc < 0.7:
                add("warn", "Separation", f"ROC AUC is {auc:.3f}: the scores barely separate {pos} from {neg}.", "")
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    out["verdict"] = (f"Accuracy {acc * 100:.1f}% (95% interval {lo * 100:.1f}-{hi * 100:.1f}), macro F1 {macro:.3f} over {len(real)} classes and {n:,} images"
                      + (f"; ROC AUC {out['binary']['auc']:.3f}" if out.get("binary") else ""))
    out["note"] = ("Scored from the lines you pasted. A score is read as the model's confidence in its predicted class (0 to 1); "
                   "the interval shows how much accuracy could move on a different sample of the same size.")
    return out
