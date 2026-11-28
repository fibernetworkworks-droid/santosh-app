"""A training table profiled before modelling: each column's type, missing values, distinct values, ranges, skew and outliers; constant
columns, ID-like columns, duplicated rows; the target's balance (or spread); features that leak the target (near-perfect correlation,
or a value that always gives the same target), near-duplicate features, and - when a split column says which rows are train and
test - how far each feature's distribution moves between them. All from the CSV text."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .table import NA, TableError, kind, num, psi, psi_cat, quantile, read


def _corr(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def profile(text: str, target: str = "", split: str = "") -> dict[str, Any]:
    head, rows = read(text)
    n = len(rows)
    lower = {h.lower(): h for h in head}
    tgt = lower.get(str(target or "").strip().lower(), "") if target else ""
    if target and not tgt:
        raise TableError(f"There is no column '{target}' - the columns are: {', '.join(head[:12])}.")
    spl = lower.get(str(split or "").strip().lower(), "") if split else ""
    if not spl:
        spl = next((h for h in head if h.lower() in ("split", "set", "subset", "fold_type")), "")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    cols: list[dict[str, Any]] = []
    numeric: dict[str, list[float | None]] = {}
    for j, h in enumerate(head):
        vals = [r[j] for r in rows]
        k = kind(vals)
        miss = sum(1 for v in vals if v.lower() in NA)
        present = [v for v in vals if v.lower() not in NA]
        uniq = len(set(present))
        c: dict[str, Any] = {"name": h, "kind": k, "missing": miss / n, "unique": uniq, "target": h == tgt, "split": h == spl}
        if k == "boolean" and all(v.lower() in NA or num(v) is not None for v in vals):
            numeric[h] = [num(v) for v in vals]
        if k == "number":
            xs = [num(v) for v in vals]
            numeric[h] = xs
            s = sorted(x for x in xs if x is not None)
            if s:
                mean = sum(s) / len(s)
                sd = math.sqrt(sum((x - mean) ** 2 for x in s) / max(1, len(s) - 1))
                q1, q3 = quantile(s, .25), quantile(s, .75)
                iqr = q3 - q1
                out_ = sum(1 for x in s if x < q1 - 1.5 * iqr or x > q3 + 1.5 * iqr) if iqr > 0 else 0
                skew = (sum((x - mean) ** 3 for x in s) / len(s)) / sd ** 3 if sd > 0 else 0.0
                c.update(min=s[0], max=s[-1], mean=mean, sd=sd, median=quantile(s, .5), q1=q1, q3=q3, outliers=out_ / len(s), skew=skew,
                         zeros=sum(1 for x in s if x == 0) / len(s), hist=_hist(s))
        else:
            top = Counter(present).most_common(8)
            c["top"] = [[v, cnt / n] for v, cnt in top]
        cols.append(c)
        if h in (tgt, spl):
            continue
        if miss / n > 0.5:
            add("warn", "Missing", f"{h} is {miss / n * 100:.0f}% empty.", "Drop it, or add an 'is missing' flag and fill it - check why it is missing first.", h)
        elif miss / n > 0.05:
            add("info", "Missing", f"{h} is {miss / n * 100:.1f}% empty.", "Impute (median / most frequent) inside the training pipeline, fitted on the training rows only.", h)
        if uniq <= 1 and miss < n:
            add("warn", "Constant", f"{h} has one value only - it cannot help a model.", "Drop it.", h)
        elif k in ("category", "text") and uniq > 0.95 * len(present) and len(present) > 50:
            c["id"] = True
            add("warn", "ID-like", f"{h} is different on almost every row ({uniq:,} values) - an identifier, not a feature.", "Drop it from the features (keep it to join or to group the split).", h)
        elif k == "number" and uniq >= 0.98 * len(present) and len(present) > 50 and c.get("min") is not None and all(float(x).is_integer() for x in numeric[h] if x is not None) and (c["max"] - c["min"] + 1) <= 1.05 * uniq:
            c["id"] = True
            add("warn", "ID-like", f"{h} counts 1, 2, 3 ... (almost) without repeats - a row number or ID.", "Drop it from the features; a model can learn the row order from it.", h)
        elif k == "category" and uniq > 100:
            add("info", "Cardinality", f"{h} has {uniq:,} categories - one-hot encoding makes {uniq:,} columns.", "Target or frequency encoding (fitted on training rows only), or group the rare values.", h)
        if k == "number" and c.get("skew") is not None and abs(c["skew"]) > 3 and c.get("min", 0) >= 0:
            add("info", "Skew", f"{h} is heavily skewed (skewness {c['skew']:.1f}).", "A log transform (log1p) helps linear models and neural nets; trees do not mind.", h)
    seen: dict[tuple, int] = {}
    dups = 0
    for r in rows:
        key = tuple(v for v, h in zip(r, head) if h != spl)
        if key in seen:
            dups += 1
        seen[key] = 1
    if dups:
        add("warn" if dups / n > 0.01 else "info", "Duplicates", f"{dups:,} row(s) ({dups / n * 100:.1f}%) repeat another row exactly.",
            "Remove them before splitting - otherwise the same example lands in train and test.")
    tinfo: dict[str, Any] | None = None
    if tgt:
        tc = next(c for c in cols if c["name"] == tgt)
        tv = [r[head.index(tgt)] for r in rows]
        if tc["kind"] in ("category", "boolean") or (tc["kind"] == "number" and tc["unique"] <= 20):
            cnt = Counter(v for v in tv if v.lower() not in NA)
            tinfo = {"type": "classes", "counts": [[k, v] for k, v in cnt.most_common(40)]}
            big, small = cnt.most_common()[0][1], cnt.most_common()[-1][1]
            if big >= 10 * small:
                add("warn", "Target", f"The target is lopsided: '{cnt.most_common()[0][0]}' {big:,} rows, '{cnt.most_common()[-1][0]}' {small:,}.",
                    "Use class weights or resampling in training, a stratified split, and judge by recall / F1 / PR-AUC, not accuracy.")
        else:
            tinfo = {"type": "number", **{k: tc.get(k) for k in ("min", "max", "mean", "median", "sd", "skew")}}
        if tc["missing"]:
            add("warn", "Target", f"The target is missing on {tc['missing'] * n:.0f} row(s).", "Drop those rows from training (do not impute a target).")
        tnum = numeric.get(tgt)
        tcat = [v for v in tv]
        for c in cols:
            h = c["name"]
            if h in (tgt, spl) or c.get("id"):
                continue
            if tnum is not None and h in numeric:
                pairs = [(a, b) for a, b in zip(numeric[h], tnum) if a is not None and b is not None]
                r_ = _corr([a for a, _ in pairs], [b for _, b in pairs])
                c["corr_target"] = r_
                if r_ is not None and abs(r_) > 0.98:
                    add("bad", "Leakage", f"{h} follows the target almost exactly (correlation {r_:.3f}) - it is probably computed from the target or recorded after it.",
                        "Drop it unless it is truly known at prediction time.", h)
            if c["kind"] in ("category", "boolean", "number") and 2 < c["unique"] < 0.5 * n:
                j = head.index(h)
                m: dict[str, set] = {}
                for r, t in zip(rows, tcat):
                    if r[j].lower() not in NA and t.lower() not in NA:
                        m.setdefault(r[j], set()).add(t)
                if m and all(len(s) == 1 for s in m.values()) and len({next(iter(s)) for s in m.values()}) > 1 and c["unique"] >= 5 and tinfo and tinfo["type"] == "classes":
                    add("bad", "Leakage", f"Every value of {h} always comes with the same target - the column gives the answer away.", "Check how it is made; drop it if it is filled in from the outcome.", h)
    nums = [h for h in numeric if h not in (tgt, spl) and not next(c for c in cols if c["name"] == h).get("id") and next(c for c in cols if c["name"] == h)["unique"] > 2][:60]
    pairs_hi = []
    for i, a in enumerate(nums):
        for b in nums[i + 1:]:
            pr = [(x, y) for x, y in zip(numeric[a], numeric[b]) if x is not None and y is not None]
            r_ = _corr([x for x, _ in pr], [y for _, y in pr])
            if r_ is not None and abs(r_) > 0.95:
                pairs_hi.append({"a": a, "b": b, "r": r_})
    if pairs_hi:
        add("info", "Redundant", f"{len(pairs_hi)} pair(s) of features carry almost the same information (e.g. {pairs_hi[0]['a']} and {pairs_hi[0]['b']}, r = {pairs_hi[0]['r']:.3f}).",
            "Keep one of each pair for linear models; it also makes importance plots easier to read.")
    split_info = None
    if spl:
        j = head.index(spl)
        parts = Counter(r[j].lower() for r in rows)
        trn = next((k for k in parts if k in ("train", "training", "tr", "0")), None)
        tst = next((k for k in parts if k in ("test", "valid", "val", "validation", "holdout", "1")), None)
        split_info = {"column": spl, "counts": dict(parts)}
        if trn and tst:
            drift = []
            for c in cols:
                h = c["name"]
                if h in (spl,) or c.get("id"):
                    continue
                k_ = head.index(h)
                A = [r[k_] for r in rows if r[j].lower() == trn]
                B = [r[k_] for r in rows if r[j].lower() == tst]
                if h in numeric:
                    a_ = [x for x in (num(v) for v in A) if x is not None]
                    b_ = [x for x in (num(v) for v in B) if x is not None]
                    if len(a_) >= 20 and len(b_) >= 20:
                        drift.append({"name": h, "psi": psi(a_, b_)[0]})
                elif c["kind"] in ("category", "boolean"):
                    a_ = [v for v in A if v.lower() not in NA]
                    b_ = [v for v in B if v.lower() not in NA]
                    if len(a_) >= 20 and len(b_) >= 20:
                        drift.append({"name": h, "psi": psi_cat(a_, b_)[0]})
            drift.sort(key=lambda x: -x["psi"])
            split_info["drift"] = drift[:40]
            moved = [d for d in drift if d["psi"] > 0.25]
            if moved:
                add("warn", "Split", f"{len(moved)} feature(s) differ a lot between {trn} and {tst} (PSI over 0.25), e.g. {moved[0]['name']} ({moved[0]['psi']:.2f}).",
                    "If the split is random this points to a bug; if it is by time, the test set shows the shift the model will meet.")
    out = {"rows": n, "columns": len(head), "cols": cols, "target": tinfo, "target_name": tgt, "split": split_info, "duplicates": dups,
           "redundant": pairs_hi[:20], "issues": issues}
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    b = out["counts"]["bad"]
    out["verdict"] = f"{n:,} rows x {len(head)} columns" + (f", target {tgt}" if tgt else "") + (f" - {b} column{'s leak' if b > 1 else ' leaks'} the target" if b else "")
    out["note"] = ("A profile of the rows you pasted. Leakage checks find columns that mirror the target in this sample; a column known "
                   "only after the outcome can still leak more quietly - ask of every feature: would I have it at prediction time?")
    return out


def _hist(s: list[float], bins: int = 20) -> list[list[float]]:
    lo, hi = s[0], s[-1]
    if hi - lo < 1e-12:
        return [[lo, len(s)]]
    w = (hi - lo) / bins
    h = [0] * bins
    for x in s:
        h[min(bins - 1, int((x - lo) / w))] += 1
    return [[lo + i * w, c] for i, c in enumerate(h)]
