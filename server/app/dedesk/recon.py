"""Source and target reconciled row by row on a key: rows missing from the target, rows the target has extra, keys that appear
twice, values that changed (per column, numbers within her tolerance), and the column totals on each side - the checks a load
should pass before anyone trusts it. Both sides are CSVs with a header."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..mldesk.table import NA, TableError, num, read
from .common import finder, finish


class ReconError(TableError):
    pass


def _key_cols(head: list[str], want: str) -> list[str]:
    want = [w.strip() for w in str(want or "").split(",") if w.strip()]
    low = {h.lower(): h for h in head}
    if want:
        out = []
        for w in want:
            if w.lower() not in low:
                raise ReconError(f"The key column '{w}' is not in the source.")
            out.append(low[w.lower()])
        return out
    for guess in ("id", "key", "pk", "uuid"):
        if guess in low:
            return [low[guess]]
    ids = [h for h in head if h.lower().endswith("_id") or h.lower().endswith("id")]
    if ids:
        return [ids[0]]
    raise ReconError("Name the key column(s) - the column(s) that identify a row (e.g. order_id).")


def _same(a: str, b: str, tol: float) -> bool:
    if a == b:
        return True
    if a.lower() in NA and b.lower() in NA:
        return True
    x, y = num(a), num(b)
    if x is not None and y is not None:
        return abs(x - y) <= tol + 1e-12 * max(1.0, abs(x))
    return False


def reconcile(src_text: str, tgt_text: str, key: str = "", tol: float = 0.0, ignore: str = "") -> dict[str, Any]:
    if not str(tgt_text or "").strip():
        raise ReconError("Paste the target too (what landed), as a CSV with the same key column.")
    h1, r1 = read(src_text, "The source")
    h2, r2 = read(tgt_text, "The target")
    keys = _key_cols(h1, key)
    low2 = {h.lower(): h for h in h2}
    for k in keys:
        if k.lower() not in low2:
            raise ReconError(f"The key column '{k}' is not in the target.")
    ign = {x.strip().lower() for x in str(ignore or "").split(",") if x.strip()}
    common = [h for h in h1 if h.lower() in low2 and h not in keys and h.lower() not in ign]
    i1 = [h1.index(k) for k in keys]
    i2 = [h2.index(low2[k.lower()]) for k in keys]
    issues, add = finder()
    K1 = [tuple(r[i] for i in i1) for r in r1]
    K2 = [tuple(r[i] for i in i2) for r in r2]
    d1 = [k for k, c in Counter(K1).items() if c > 1]
    d2 = [k for k, c in Counter(K2).items() if c > 1]
    m1 = {k: r for k, r in zip(K1, r1)}
    m2 = {k: r for k, r in zip(K2, r2)}
    miss = [k for k in m1 if k not in m2]
    extra = [k for k in m2 if k not in m1]
    both = [k for k in m1 if k in m2]
    diff_cols: dict[str, int] = defaultdict(int)
    samples: list[dict[str, Any]] = []
    changed = 0
    for k in both:
        a, b = m1[k], m2[k]
        row_bad = False
        for h in common:
            va, vb = a[h1.index(h)], b[h2.index(low2[h.lower()])]
            if not _same(va, vb, tol):
                diff_cols[h] += 1
                row_bad = True
                if len(samples) < 40:
                    samples.append({"key": " / ".join(k), "column": h, "source": va, "target": vb})
        changed += row_bad
    nulls = []
    for h in common:
        a = sum(1 for r in r1 if r[h1.index(h)].lower() in NA)
        b = sum(1 for r in r2 if r[h2.index(low2[h.lower()])].lower() in NA)
        if b > a:
            nulls.append({"column": h, "source": a, "target": b})
    totals = []
    for h in common:
        xa = [num(r[h1.index(h)]) for r in r1]
        xb = [num(r[h2.index(low2[h.lower()])]) for r in r2]
        if sum(v is not None for v in xa) >= 0.9 * len(xa) and len(xa) and not any(h.lower().endswith(s) for s in ("id", "_id", "code", "zip", "phone")):
            sa, sb = sum(v for v in xa if v is not None), sum(v for v in xb if v is not None)
            totals.append({"column": h, "source": sa, "target": sb, "diff": sb - sa})
    res: dict[str, Any] = {"key": keys, "source_rows": len(r1), "target_rows": len(r2), "matched": len(both), "missing": len(miss), "extra": len(extra),
                           "changed": changed, "dup_source": len(d1), "dup_target": len(d2), "compared": common, "diff_cols": dict(sorted(diff_cols.items(), key=lambda x: -x[1])),
                           "missing_keys": [" / ".join(k) for k in miss[:50]], "extra_keys": [" / ".join(k) for k in extra[:50]], "samples": samples, "totals": totals, "nulls": nulls,
                           "only_source": [h for h in h1 if h.lower() not in low2], "only_target": [h for h in h2 if h.lower() not in {x.lower() for x in h1}]}
    kn = " + ".join(keys)
    if miss:
        add("bad", "Missing", f"{len(miss):,} source row(s) did not reach the target (e.g. {kn} {' / '.join(miss[0])}).", "Check the load's filters, a failed batch, or late-arriving rows past the cut-off.")
    if extra:
        add("warn", "Extra", f"The target has {len(extra):,} row(s) the source does not (e.g. {kn} {' / '.join(extra[0])}).", "Deletes not carried over, or rows from another run.")
    if d1:
        add("warn", "Duplicates", f"{len(d1):,} key(s) appear more than once in the source.", "The key is not unique - reconcile on more columns, or deduplicate.")
    if d2:
        add("bad", "Duplicates", f"{len(d2):,} key(s) appear more than once in the target - a load ran twice or a join fanned out.", "Make the load idempotent (MERGE on the key) and check joins.")
    if changed:
        top = next(iter(res["diff_cols"]))
        add("bad" if changed > 0.01 * max(1, len(both)) else "warn", "Changed", f"{changed:,} matched row(s) differ; most in {top} ({res['diff_cols'][top]:,}).",
            "Compare a few rows: casting, rounding, time zones and trimmed text are the usual causes.", top)
    for t in totals:
        if abs(t["diff"]) > max(1e-9, tol * len(both)) and not miss and not extra:
            add("warn", "Totals", f"The total of {t['column']} differs by {t['diff']:+.6g} with the same rows.", "", t["column"])
    for n in nulls:
        add("warn", "Empty", f"{n['column']} is empty in {n['target']:,} target rows against {n['source']:,} in the source.", "A mapping lost the value.", n["column"])
    if res["only_source"]:
        add("info", "Columns", f"Only in the source: {', '.join(res['only_source'][:6])}.", "")
    ok = not miss and not extra and not changed and not d2
    res["verdict"] = (f"Reconciled: all {len(both):,} rows match" if ok else
                      f"{len(miss):,} missing, {len(extra):,} extra, {changed:,} changed of {len(r1):,} source rows")
    res["note"] = f"Matched on {kn}; {len(common)} column(s) compared - numbers " + (f"within {tol:g}" if tol else "exactly") + ", text exactly (case and spaces count)."
    return finish(res, issues)
