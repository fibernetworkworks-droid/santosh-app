"""Production data compared with the data a model was trained on (or this week with last week), column by column: for numbers the
population stability index over the reference's deciles, the two-sample Kolmogorov-Smirnov test and how far the mean moved; for
categories the PSI over the values and any value never seen in training; missing values going up. Prediction or score columns are
compared the same way - a moving score is often the first sign. All from the two CSVs."""
from __future__ import annotations

from typing import Any

from .table import NA, TableError, kind, ks, num, psi, psi_cat, read


def compare(ref_text: str, cur_text: str, warn: float = 0.1, alarm: float = 0.25) -> dict[str, Any]:
    if not str(cur_text or "").strip():
        raise TableError("Paste the current data too (the same columns), to compare with the reference.")
    h1, r1 = read(ref_text, "The reference data")
    h2, r2 = read(cur_text, "The current data")
    common = [h for h in h1 if h in h2]
    if not common:
        raise TableError("The two tables share no column names.")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    only1, only2 = [h for h in h1 if h not in h2], [h for h in h2 if h not in h1]
    if only1:
        add("bad", "Columns", f"{len(only1)} column(s) are missing from the current data: {', '.join(only1[:6])}.", "The model will fail or fill them with defaults - fix the pipeline.")
    if only2:
        add("info", "Columns", f"The current data has new column(s): {', '.join(only2[:6])}.", "")
    out_cols = []
    for h in common:
        A = [r[h1.index(h)] for r in r1]
        B = [r[h2.index(h)] for r in r2]
        k = kind(A)
        ma = sum(1 for v in A if v.lower() in NA) / len(A)
        mb = sum(1 for v in B if v.lower() in NA) / len(B)
        row: dict[str, Any] = {"name": h, "kind": k, "missing_ref": ma, "missing_cur": mb}
        if k == "number":
            a = [x for x in (num(v) for v in A) if x is not None]
            b = [x for x in (num(v) for v in B) if x is not None]
            if len(a) < 10 or len(b) < 10:
                continue
            p, bins = psi(a, b)
            d, pv = ks(a, b)
            m1, m2 = sum(a) / len(a), sum(b) / len(b)
            sd = (sum((x - m1) ** 2 for x in a) / max(1, len(a) - 1)) ** 0.5
            row.update(psi=p, bins=bins, ks=d, p=pv, mean_ref=m1, mean_cur=m2, shift_sd=(m2 - m1) / sd if sd else 0.0)
            bad_type = sum(1 for v in B if v.lower() not in NA and num(v) is None)
            if bad_type:
                add("bad", "Types", f"{h}: {bad_type} current value(s) are not numbers any more.", "A format change upstream (units, separators, text in a number column).", h)
        elif k in ("category", "boolean"):
            a = [v for v in A if v.lower() not in NA]
            b = [v for v in B if v.lower() not in NA]
            if len(a) < 10 or len(b) < 10:
                continue
            p, bins = psi_cat(a, b)
            row.update(psi=p, bins=bins)
            new = [x for x in bins if x.get("new") and x["cur"] > 0.01]
            if new:
                add("warn", "New values", f"{h} has values never seen in training: {', '.join(repr(x['value']) for x in new[:4])} ({sum(x['cur'] for x in new) * 100:.1f}% of rows).",
                    "Check the encoder handles unknown values, and retrain once they are common.", h)
        else:
            continue
        p = row["psi"]
        row["state"] = "bad" if p > alarm else "warn" if p > warn else "ok"
        if p > alarm:
            add("bad", "Drift", f"{h} has shifted a lot (PSI {p:.2f})" + (f": the mean moved {row['shift_sd']:+.2f} standard deviations" if k == "number" else "") + ".",
                "Find the cause (a real change in the world, or a broken upstream feed) before trusting the model's outputs; retrain if real.", h)
        elif p > warn:
            add("warn", "Drift", f"{h} has moved (PSI {p:.2f}).", "Watch it; check the model's accuracy on recent labelled data.", h)
        if mb - ma > 0.05:
            add("warn", "Missing", f"{h} is missing on {mb * 100:.1f}% of current rows against {ma * 100:.1f}% in the reference.", "An upstream feed may be failing.", h)
        out_cols.append(row)
    out_cols.sort(key=lambda r: -r.get("psi", 0))
    moved = sum(1 for r in out_cols if r["state"] != "ok")
    out = {"ref_rows": len(r1), "cur_rows": len(r2), "columns": out_cols, "warn": warn, "alarm": alarm, "issues": issues}
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    out["verdict"] = f"{moved} of {len(out_cols)} columns moved ({len(r1):,} reference rows against {len(r2):,} current)"
    out["note"] = ("PSI under 0.1 is usually stable, 0.1-0.25 a moderate shift, over 0.25 a large one - rules of thumb, not tests. With large "
                   "samples the KS p-value flags even tiny shifts; read the size of the change (PSI, the mean shift) before the p-value.")
    return out
