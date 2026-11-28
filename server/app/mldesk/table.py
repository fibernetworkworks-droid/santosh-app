"""Shared table reading for the ML desk: a CSV (comma, tab or semicolon) into columns, each column typed (number, date, true / false,
category or text), and the drift measures between two samples of one column - the population stability index over reference
quantile bins (or categories), and the two-sample Kolmogorov-Smirnov statistic with its asymptotic p-value."""
from __future__ import annotations

import csv
import io
import math
import re
from typing import Any


class TableError(ValueError):
    pass


MAX_ROWS = 300_000
NA = {"", "na", "n/a", "nan", "null", "none", "?", "-", "missing", "#n/a"}
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}([ t]\d{2}:\d{2}(:\d{2})?)?|\d{1,2}/\d{1,2}/\d{2,4}")


def read(text: str, what: str = "The table") -> tuple[list[str], list[list[str]]]:
    t = str(text or "").strip("﻿\n\r ")
    if not t:
        raise TableError(f"{what}: paste a CSV with a header row.")
    first = t.split("\n", 1)[0]
    delim = max((",", "\t", ";", "|"), key=first.count)
    if first.count(delim) == 0:
        raise TableError(f"{what}: a header row with column names separated by commas (or tabs).")
    r = csv.reader(io.StringIO(t), delimiter=delim)
    head = [h.strip() for h in next(r)]
    if len(set(head)) != len(head):
        dup = sorted({h for h in head if head.count(h) > 1})
        raise TableError(f"{what}: two columns share a name ({', '.join(dup[:3])}).")
    rows = []
    for row in r:
        if not any(c.strip() for c in row):
            continue
        if len(row) != len(head):
            row = (row + [""] * len(head))[:len(head)]
        rows.append([c.strip() for c in row])
        if len(rows) > MAX_ROWS:
            raise TableError(f"{what}: up to {MAX_ROWS:,} rows - sample it first.")
    if not rows:
        raise TableError(f"{what}: no data rows under the header.")
    return head, rows


def num(v: str) -> float | None:
    if v.lower() in NA:
        return None
    try:
        x = float(v.replace(",", "")) if re.fullmatch(r"[-+]?[\d,]*\.?\d+(e[-+]?\d+)?%?", v.rstrip("%"), re.I) else float(v)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def kind(vals: list[str]) -> str:
    seen = [v for v in vals if v.lower() not in NA]
    if not seen:
        return "empty"
    if sum(1 for v in seen if num(v) is not None) >= 0.95 * len(seen):
        u = {v.lower() for v in seen}
        return "boolean" if u <= {"0", "1"} and len(u) == 2 else "number"
    if {v.lower() for v in seen} <= {"true", "false", "yes", "no", "y", "n", "t", "f"}:
        return "boolean"
    if sum(1 for v in seen[:2000] if _DATE.fullmatch(v.lower())) >= 0.95 * min(len(seen), 2000):
        return "date"
    u = len(set(seen))
    avg = sum(len(v) for v in seen[:2000]) / min(len(seen), 2000)
    return "text" if avg > 40 and u > 0.5 * len(seen) else "category"


def quantile(s: list[float], q: float) -> float:
    if not s:
        return float("nan")
    k = (len(s) - 1) * q
    f = math.floor(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)


def psi(ref: list[float], cur: list[float], bins: int = 10) -> tuple[float, list[dict[str, Any]]]:
    rs = sorted(ref)
    edges = sorted({quantile(rs, i / bins) for i in range(1, bins)})
    def counts(xs: list[float]) -> list[int]:
        c = [0] * (len(edges) + 1)
        import bisect
        for x in xs:
            c[bisect.bisect_right(edges, x)] += 1
        return c
    a, b = counts(ref), counts(cur)
    total = 0.0
    out = []
    lo = float("-inf")
    for i, (ca, cb) in enumerate(zip(a, b)):
        pa, pb = max(ca / len(ref), 1e-4), max(cb / len(cur), 1e-4)
        part = (pb - pa) * math.log(pb / pa)
        total += part
        hi = edges[i] if i < len(edges) else float("inf")
        out.append({"lo": lo, "hi": hi, "ref": ca / len(ref), "cur": cb / len(cur), "psi": part})
        lo = hi
    return total, out


def psi_cat(ref: list[str], cur: list[str], top: int = 20) -> tuple[float, list[dict[str, Any]]]:
    from collections import Counter
    cr, cc = Counter(ref), Counter(cur)
    keep = [k for k, _ in cr.most_common(top)]
    cats = keep + [k for k, _ in cc.most_common(top) if k not in keep][:5]
    total = 0.0
    out = []
    for k in cats + ["(other)"]:
        if k == "(other)":
            na = sum(v for kk, v in cr.items() if kk not in cats)
            nb = sum(v for kk, v in cc.items() if kk not in cats)
        else:
            na, nb = cr.get(k, 0), cc.get(k, 0)
        if k == "(other)" and not na and not nb:
            continue
        pa, pb = max(na / len(ref), 1e-4), max(nb / len(cur), 1e-4)
        part = (pb - pa) * math.log(pb / pa)
        total += part
        out.append({"value": k, "ref": na / len(ref), "cur": nb / len(cur), "psi": part, "new": k != "(other)" and not na})
    return total, out


def ks(a: list[float], b: list[float]) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov: the largest gap between the two empirical distribution functions, and the asymptotic p-value."""
    sa, sb = sorted(a), sorted(b)
    n, m = len(sa), len(sb)
    i = j = 0
    d = 0.0
    while i < n and j < m:
        x = min(sa[i], sb[j])
        while i < n and sa[i] <= x:
            i += 1
        while j < m and sb[j] <= x:
            j += 1
        d = max(d, abs(i / n - j / m))
    en = math.sqrt(n * m / (n + m))
    lam = en * d
    if lam < 0.27:          # Q_KS(0.27) > 0.99999; the series is slow to settle below it
        return d, 1.0
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return d, max(0.0, min(1.0, p))
