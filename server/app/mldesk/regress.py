"""Regression and forecast errors from one row per prediction (actual, predicted, and if she has them a group, a date, and the lower /
upper bounds of a prediction interval): MAE, RMSE, MAPE (said plainly when actual zeros make it meaningless), sMAPE, WAPE, R², bias,
the error spread, how the model compares with always predicting the mean and - for a time series - with the naive forecast (MASE),
errors by group, whether errors grow with the size of the prediction, a calibration table, and how often the interval holds the
actual."""
from __future__ import annotations

import math
import re
from typing import Any

from .table import NA, TableError, num, quantile, read

ACT = r"(actual|y|y_true|truth|target|label|observed|obs|sales|value)"
PRED = r"(predicted|prediction|pred|y_pred|yhat|y_hat|forecast|fcst|estimate|output)"


def _col(head: list[str], pat: str, given: str = "") -> str | None:
    if given:
        g = next((h for h in head if h.lower() == given.lower()), None)
        if not g:
            raise TableError(f"There is no column '{given}'.")
        return g
    return next((h for h in head if re.fullmatch(pat, h.lower())), None)


def evaluate(text: str, actual: str = "", predicted: str = "", group: str = "", season: int = 1) -> dict[str, Any]:
    head, rows = read(text)
    a_c = _col(head, ACT, actual)
    p_c = _col(head, PRED, predicted)
    if not a_c or not p_c:
        raise TableError("Name the columns actual and predicted (or say which ones they are). Columns here: " + ", ".join(head[:10]) + ".")
    g_c = _col(head, r"(group|segment|store|region|category|sku|series|item|country|class)", group)
    d_c = next((h for h in head if re.fullmatch(r"(date|ds|time|timestamp|period|week|month|day)", h.lower())), None)
    lo_c = next((h for h in head if re.fullmatch(r"(lower|lo|p10|q10|lower_bound|pi_lower|yhat_lower)", h.lower())), None)
    hi_c = next((h for h in head if re.fullmatch(r"(upper|hi|p90|q90|upper_bound|pi_upper|yhat_upper)", h.lower())), None)
    ix = {h: i for i, h in enumerate(head)}
    data = []
    skipped = 0
    for r in rows:
        y, p = num(r[ix[a_c]]), num(r[ix[p_c]])
        if y is None or p is None:
            skipped += 1
            continue
        data.append({"y": y, "p": p, "g": r[ix[g_c]] if g_c else "", "d": r[ix[d_c]] if d_c else "",
                     "lo": num(r[ix[lo_c]]) if lo_c else None, "hi": num(r[ix[hi_c]]) if hi_c else None})
    n = len(data)
    if n < 5:
        raise TableError("At least 5 rows with a number in both the actual and the predicted column.")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", fn="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": fn})   # noqa: E731
    e = [d["p"] - d["y"] for d in data]
    ae = sorted(abs(x) for x in e)
    ys = [d["y"] for d in data]
    my = sum(ys) / n
    mae = sum(ae) / n
    rmse = math.sqrt(sum(x * x for x in e) / n)
    sst = sum((y - my) ** 2 for y in ys)
    r2 = 1 - sum(x * x for x in e) / sst if sst > 0 else None
    nz = [(d["y"], d["p"]) for d in data if d["y"] != 0]
    mape = sum(abs((p - y) / y) for y, p in nz) / len(nz) * 100 if nz else None
    smape = sum(2 * abs(d["p"] - d["y"]) / (abs(d["y"]) + abs(d["p"])) for d in data if abs(d["y"]) + abs(d["p"]) > 0) / n * 100
    wape = sum(ae) / sum(abs(y) for y in ys) * 100 if sum(abs(y) for y in ys) else None
    bias = sum(e) / n
    base_rmse = math.sqrt(sst / n)
    out: dict[str, Any] = {"n": n, "skipped": skipped, "columns": {"actual": a_c, "predicted": p_c, "group": g_c, "date": d_c, "lower": lo_c, "upper": hi_c},
                           "mae": mae, "rmse": rmse, "r2": r2, "mape": mape, "smape": smape, "wape": wape, "bias": bias, "medae": quantile(ae, .5),
                           "p90ae": quantile(ae, .9), "maxae": ae[-1], "mean_rmse": base_rmse}
    zeros = n - len(nz)
    if zeros:
        add("warn" if zeros / n > 0.05 else "info", "MAPE", f"{zeros} actual value(s) are zero - MAPE leaves them out and blows up near zero.", "Read WAPE or MAE instead for data with zeros.")
    if r2 is not None and r2 < 0:
        add("bad", "Baseline", f"R² is {r2:.3f}: always predicting the average ({my:.4g}) would do better.", "Check the predictions line up with the right actuals, and the model's target scaling.")
    if abs(bias) > 0.1 * mae and abs(bias) > 1e-12:
        add("warn", "Bias", f"The model {'over' if bias > 0 else 'under'}-predicts by {abs(bias):.4g} on average - {abs(bias) / mae * 100:.0f}% of the average error.",
            "A systematic offset: check the target's transform (log back-transform needs a correction), recent level shifts, or add a bias correction.")
    if d_c or season > 1:
        seq: dict[str, list[float]] = {}
        for d in (sorted(data, key=lambda d: (d["g"], d["d"])) if d_c else data):
            seq.setdefault(d["g"], []).append(d["y"])
        naive = [abs(s[i] - s[i - season]) for s in seq.values() for i in range(season, len(s))]
        if naive and sum(naive) > 0:
            mase = mae / (sum(naive) / len(naive))
            out["mase"] = mase
            out["season"] = season
            if mase > 1:
                add("warn", "Naive forecast", f"MASE is {mase:.2f}: repeating the {'last value' if season == 1 else f'value {season} periods back'} would forecast better.",
                    "Make sure the model sees recent lags and seasonality; a forecast must beat the naive one to be worth running.")
    pr = sorted(data, key=lambda d: d["p"])
    k = 10 if n >= 50 else max(2, n // 5)
    cal = []
    for i in range(k):
        part = pr[i * n // k:(i + 1) * n // k]
        if part:
            cal.append({"pred": sum(d["p"] for d in part) / len(part), "actual": sum(d["y"] for d in part) / len(part), "n": len(part),
                        "mae": sum(abs(d["p"] - d["y"]) for d in part) / len(part)})
    out["calibration"] = cal
    if len(cal) >= 4 and cal[0]["mae"] > 0 and cal[-1]["mae"] > 3 * cal[0]["mae"] and pr[0]["p"] >= 0:
        add("info", "Spread", "Errors grow with the size of the prediction (the top tenth errs over 3 times the bottom tenth).",
            "Normal for sales-like data: judge it in percentage terms, or model log(target).")
    if g_c:
        by: dict[str, list[dict]] = {}
        for d in data:
            by.setdefault(d["g"], []).append(d)
        groups = []
        for g, ds in by.items():
            ee = [d["p"] - d["y"] for d in ds]
            groups.append({"group": g, "n": len(ds), "mae": sum(abs(x) for x in ee) / len(ds), "bias": sum(ee) / len(ds),
                           "wape": sum(abs(x) for x in ee) / max(1e-12, sum(abs(d["y"]) for d in ds)) * 100})
        groups.sort(key=lambda x: -x["mae"] * x["n"])
        out["groups"] = groups[:60]
        if len(groups) >= 3:
            worst = max(groups, key=lambda x: x["wape"] if x["n"] >= 5 else -1)
            if worst["n"] >= 5 and wape and worst["wape"] > 2 * wape:
                add("warn", "Groups", f"{g_c} '{worst['group']}' is predicted much worse than the rest (WAPE {worst['wape']:.1f}% against {wape:.1f}% overall).", "Look at that segment's data - a separate model or features for it may help.", worst["group"])
    if lo_c and hi_c:
        iv = [d for d in data if d["lo"] is not None and d["hi"] is not None]
        if iv:
            cov = sum(1 for d in iv if d["lo"] <= d["y"] <= d["hi"]) / len(iv)
            width = sum(d["hi"] - d["lo"] for d in iv) / len(iv)
            out["interval"] = {"coverage": cov, "width": width, "n": len(iv)}
            if abs(cov - 0.8) > 0.1 and re.search(r"10|90", lo_c + hi_c):
                add("warn", "Intervals", f"The 10-90% interval holds the actual {cov * 100:.0f}% of the time, not 80%.", "Recalibrate the quantiles (conformal prediction on a held-out set is a simple way).")
            else:
                add("info", "Intervals", f"The interval holds the actual {cov * 100:.1f}% of the time (average width {width:.4g}).", "")
    step = max(1, n // 600)
    out["points"] = [[round(d["y"], 6), round(d["p"], 6)] for d in data[::step]]
    out["err_hist"] = _hist(sorted(e))
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    out["verdict"] = (f"MAE {mae:.4g}, RMSE {rmse:.4g}" + (f", R² {r2:.3f}" if r2 is not None else "") + (f", WAPE {wape:.1f}%" if wape is not None else "")
                      + (f", MASE {out['mase']:.2f}" if out.get("mase") is not None else "") + f" over {n:,} predictions")
    out["note"] = ("Measured on the rows you pasted. Errors on data the model trained on say little - use rows it never saw, and for a "
                   "forecast, a period after its training data.")
    return out


def _hist(s: list[float], bins: int = 24) -> list[list[float]]:
    lo, hi = s[0], s[-1]
    if hi - lo < 1e-12:
        return [[lo, len(s)]]
    w = (hi - lo) / bins
    h = [0] * bins
    for x in s:
        h[min(bins - 1, int((x - lo) / w))] += 1
    return [[lo + i * w, c] for i, c in enumerate(h)]
