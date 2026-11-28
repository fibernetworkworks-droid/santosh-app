"""A translation proved side by side: the old program's output and the new program's output compared record by record - matched by
key fields or by position, field by field through the copybook layout (fixed-width records), as CSV with a header, or line by line -
with every difference named for what it usually is: a rounding the old code truncated, a lost sign, trailing spaces, zeros against
spaces, low-values, upper / lower case, or the same records in another order (EBCDIC and ASCII sort letters and digits differently).
Pasted output is data."""
from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from typing import Any


class ProofError(ValueError):
    pass


OVER_POS = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4", "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
OVER_NEG = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4", "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def _sides(text: str) -> tuple[str, str, str, str]:
    t = str(text or "")
    heads = list(re.finditer(r"^\s*##\s*(.+?)\s*$", t, re.M))
    if len(heads) < 2:
        raise ProofError("Put the old output under '## old' and the new output under '## new'.")
    a, b = heads[0], heads[1]
    return a.group(1)[:40], t[a.end():b.start()].strip("\n"), b.group(1)[:40], t[b.end():(heads[2].start() if len(heads) > 2 else len(t))].strip("\n")


def _num(s: str, scale: int = 0, signed: bool = False) -> Decimal | None:
    v = s.strip()
    if not v:
        return None
    neg = False
    if signed and v[-1:] in OVER_POS:
        v = v[:-1] + OVER_POS[v[-1]]
    elif signed and v[-1:] in OVER_NEG:
        v, neg = v[:-1] + OVER_NEG[v[-1]], True
    v = v.replace(",", "")
    if v.endswith("-") or v.endswith("CR") or v.endswith("DB"):
        v, neg = re.sub(r"(?:-|CR|DB)$", "", v), True
    try:
        d = Decimal(v)
    except InvalidOperation:
        return None
    if scale and re.fullmatch(r"[+-]?\d+", v):
        d = d.scaleb(-scale)
    return -d if neg else d


def _ebc_key(s: str) -> list[int]:
    return list(s.encode("cp037", "replace"))


def _records(body: str, mode: str, layout: list[dict[str, Any]] | None) -> tuple[list[str], list[dict[str, str]]]:
    lines = [ln.rstrip("\r") for ln in body.split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    if mode == "csv":
        sn = csv.Sniffer()
        try:
            dia = sn.sniff(body[:4000], delimiters=",;|\t")
        except csv.Error:
            dia = csv.excel
        rows = list(csv.reader(io.StringIO("\n".join(lines)), dia))
        if not rows:
            return [], []
        head = [h.strip() or f"col{i + 1}" for i, h in enumerate(rows[0])]
        return head, [{h: (r[i] if i < len(r) else "") for i, h in enumerate(head)} for r in rows[1:]]
    if mode == "fixed" and layout:
        names = [f["name"] for f in layout]
        return names, [{f["name"]: ln[f["offset"]:f["offset"] + f["length"]] for f in layout} for ln in lines]
    return ["line"], [{"line": ln} for ln in lines]


def _classify(a: str, b: str, f: dict[str, Any] | None, tol: Decimal) -> tuple[str, str]:
    """(kind, label) - kind 'same' when equal within tolerance."""
    numeric = bool(f and f.get("kind") in ("zoned", "packed", "binary", "edited")) or (re.fullmatch(r"\s*[+-]?[\d,]*\.?\d+[-]?\s*", a or "x") and re.fullmatch(r"\s*[+-]?[\d,]*\.?\d+[-]?\s*", b or "x"))
    if numeric:
        sc = (f or {}).get("scale", 0) if f and f.get("kind") == "zoned" else 0
        x, y = _num(a, sc, bool(f and f.get("signed"))), _num(b, sc, bool(f and f.get("signed")))
        if x is not None and y is not None:
            d = abs(x - y)
            if d <= tol:
                return ("same" if d == 0 else "within", "equal" if d == 0 else f"within {tol}")
            if x == -y:
                return ("sign", "sign lost or flipped")
            exp = min(x.as_tuple().exponent if isinstance(x.as_tuple().exponent, int) else 0, y.as_tuple().exponent if isinstance(y.as_tuple().exponent, int) else 0)
            if exp < 0 and d == Decimal(1).scaleb(exp):
                return ("rounding", "off by one in the last decimal - rounding where COBOL truncates (or the other way round)")
            if exp < 0 and d < Decimal(1).scaleb(exp + 1) and len(str(abs(x)).replace(".", "")) != len(str(abs(y)).replace(".", "")):
                return ("precision", "different number of decimals kept")
            big = max(abs(x), abs(y))
            if big and (d / big) > Decimal("0.5") and str(abs(x)).lstrip("0").replace(".", "")[-3:] == str(abs(y)).lstrip("0").replace(".", "")[-3:]:
                return ("truncation", "high-order digits lost - the field is too small (COBOL cuts the left digits)")
            return ("value", f"{x} vs {y}")
    if a.rstrip() == b.rstrip():
        return ("spaces", "trailing spaces")
    if a.strip() == b.strip():
        return ("spaces", "leading / trailing spaces")
    if "\x00" in a + b:
        return ("lowvalues", "low-values (X'00') on one side")
    if a.strip("0 ") == b.strip("0 ") and (set(a) - set("0 ")) == (set(b) - set("0 ")):
        return ("zeros", "zeros against spaces")
    if a.lower() == b.lower():
        return ("case", "upper / lower case")
    return ("value", "different text")


def prove(text: str, layout: list[dict[str, Any]] | None = None, keys: str = "", ignore: str = "", tolerance: Any = 0, mode: str = "") -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 40_000_000:
        raise ProofError("That is longer than 40 MB.")
    try:
        tol = Decimal(str(tolerance or 0))
    except InvalidOperation:
        raise ProofError("Tolerance: a number, for example 0 or 0.01.")
    if tol < 0:
        raise ProofError("Tolerance cannot be below 0.")
    na, a, nb, b = _sides(t)
    leaf = [f for f in (layout or []) if not f.get("group") and f.get("length")] if layout else None
    if leaf:
        leaf = [f for f in leaf if not f.get("redefines")]
    if not mode:
        head5 = [ln for ln in a.split("\n") if ln.strip()][:5]
        is_csv = any(head5 and head5[0].count(d) >= 1 and len({ln.count(d) for ln in head5}) == 1 and (len(head5) > 1 or head5[0].count(d) >= 2)
                     for d in (",", ";", "|", "\t")) and not re.search(r"\s{3,}", head5[0] if head5 else "")
        mode = "fixed" if leaf else ("csv" if is_csv else "lines")
    if mode == "fixed" and not leaf:
        raise ProofError("Fixed-width records need a copybook layout - pick one, or compare as lines.")
    fa, ra = _records(a, mode, leaf)
    fb, rb = _records(b, mode, leaf)
    if not ra and not rb:
        raise ProofError("Both sides are empty.")
    fields = fa if fa else fb
    if mode == "csv" and fa != fb:
        missing = [h for h in fa if h not in fb]
        extra = [h for h in fb if h not in fa]
        if missing or extra:
            raise ProofError(f"The CSV headers differ (old only: {', '.join(missing[:6]) or '-'}; new only: {', '.join(extra[:6]) or '-'}).")
    ign = {x.strip().upper() for x in re.split(r"[,\s]+", ignore or "") if x.strip()}
    kk = [x.strip() for x in re.split(r"[,\s]+", keys or "") if x.strip()]
    up = {h.upper(): h for h in fields}
    kfields = []
    for k in kk:
        if k.upper() not in up:
            raise ProofError(f"Key field {k} is not one of: {', '.join(fields[:12])}.")
        kfields.append(up[k.upper()])
    cmp_fields = [h for h in fields if h.upper() not in ign and h not in kfields]
    fmeta = {f["name"]: f for f in (leaf or [])}
    issues: list[dict[str, Any]] = []
    pairs: list[tuple[int | None, int | None]] = []
    dup = 0
    if kfields:
        ka: dict[tuple, int] = {}
        for i, r in enumerate(ra):
            k = tuple(r[f].strip() for f in kfields)
            if k in ka:
                dup += 1
            ka.setdefault(k, i)
        kb: dict[tuple, int] = {}
        for i, r in enumerate(rb):
            k = tuple(r[f].strip() for f in kfields)
            if k in kb:
                dup += 1
            kb.setdefault(k, i)
        for k, i in ka.items():
            pairs.append((i, kb.get(k)))
        for k, j in kb.items():
            if k not in ka:
                pairs.append((None, j))
        if dup:
            issues.append({"sev": "warn", "text": f"{dup} record(s) share a key with another - only the first of each is compared; add fields to the key."})
    else:
        n = max(len(ra), len(rb))
        pairs = [(i if i < len(ra) else None, i if i < len(rb) else None) for i in range(n)]
    by_field: dict[str, dict[str, int]] = {}
    diffs = []
    equal = differ = within = 0
    only_a = only_b = 0
    for i, j in pairs:
        if i is None:
            only_b += 1
            if len(diffs) < 200:
                diffs.append({"old": None, "new": j + 1, "key": " ".join(rb[j][f].strip() for f in kfields), "field": "(record)", "a": "", "b": _show(rb[j]), "kind": "only_new", "label": "only in the new output"})
            continue
        if j is None:
            only_a += 1
            if len(diffs) < 200:
                diffs.append({"old": i + 1, "new": None, "key": " ".join(ra[i][f].strip() for f in kfields), "field": "(record)", "a": _show(ra[i]), "b": "", "kind": "only_old", "label": "only in the old output"})
            continue
        bad = False
        close = False
        for h in cmp_fields:
            x, y = ra[i].get(h, ""), rb[j].get(h, "")
            if x == y:
                continue
            kind, label = _classify(x, y, fmeta.get(h), tol)
            if kind == "same":
                continue
            if kind == "within":
                close = True
                continue
            bad = True
            st = by_field.setdefault(h, {})
            st[kind] = st.get(kind, 0) + 1
            if len(diffs) < 200:
                diffs.append({"old": i + 1, "new": j + 1, "key": " ".join(ra[i][f].strip() for f in kfields), "field": h, "a": x[:120], "b": y[:120], "kind": kind, "label": label})
        if bad:
            differ += 1
        else:
            equal += 1
            within += 1 if close else 0
    # the same records in another order?
    order_note = None
    if not kfields and differ and len(ra) == len(rb) and sorted(map(_line, ra)) == sorted(map(_line, rb)):
        la, lb = list(map(_line, ra)), list(map(_line, rb))
        ebc_a = la == sorted(la, key=_ebc_key)
        asc_b = lb == sorted(lb)
        order_note = ("The same records, in another order: the old output is in EBCDIC order and the new in ASCII order (EBCDIC puts lower case before "
                      "upper case before digits). Sort the new side with an EBCDIC collation, or compare by key.") if ebc_a and asc_b else \
                     "The same records, in another order - the content matches; match by key fields, or make the new sort keep the old order."
        issues.append({"sev": "warn", "text": order_note})
    total = len(pairs)
    kinds: dict[str, int] = {}
    for st in by_field.values():
        for k, v in st.items():
            kinds[k] = kinds.get(k, 0) + v
    for k, txt in (("rounding", "values off by one in the last decimal: COBOL truncates unless the statement says ROUNDED - match its rule (RoundingMode.DOWN / ROUND_DOWN where it truncates)."),
                   ("sign", "values whose sign was lost or flipped: check signed fields (S in the PICTURE) and how the sign is written (overpunch, trailing '-', separate)."),
                   ("truncation", "values that lost their high-order digits: a receiving field is too small - COBOL cuts the left digits; the new code must, or must report it."),
                   ("spaces", "differences only in spaces: COBOL pads text fields with spaces to their length - pad (or trim) the same way."),
                   ("zeros", "zeros against spaces: an unset numeric field or a different edit picture."),
                   ("lowvalues", "low-values (X'00') on one side: an uninitialised field - INITIALIZE / VALUE clauses must match."),
                   ("case", "upper / lower case: the old program upper-cases somewhere (INSPECT CONVERTING / FUNCTION UPPER-CASE)."),
                   ("precision", "a different number of decimals kept.")):
        if kinds.get(k):
            issues.append({"sev": "warn" if k in ("rounding", "sign", "truncation") else "info", "text": f"{kinds[k]} {txt.replace('values ', 'value ', 1) if kinds[k] == 1 and txt.startswith('values ') else txt}"})
    if kinds.get("value") and not order_note:
        issues.append({"sev": "bad", "text": f"{kinds['value']} field value(s) differ for no pattern these checks know - the translation does something else there."})
    if only_a or only_b:
        issues.append({"sev": "bad", "text": f"{only_a} record(s) only in the old output, {only_b} only in the new - records are lost or added."})
    if not differ and not only_a and not only_b and not order_note:
        issues.append({"sev": "info", "text": f"All {total:,} record(s) are the same in every compared field" + (f" ({within} within your tolerance of {tol})" if within else "") + "."})
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda x: order[x["sev"]])
    proved = not differ and not only_a and not only_b
    reordered = bool(order_note)
    return {"mode": mode, "old": {"name": na, "records": len(ra)}, "new": {"name": nb, "records": len(rb)}, "fields": fields[:400], "keys": kfields,
            "ignored": sorted(ign)[:40], "compared": len(cmp_fields), "pairs": total, "equal": equal, "within": within, "differ": differ, "only_old": only_a,
            "only_new": only_b, "by_field": [{"field": h, "n": sum(v.values()), "kinds": v} for h, v in sorted(by_field.items(), key=lambda kv: -sum(kv[1].values()))][:100],
            "diffs": diffs, "proved": proved, "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order},
            "reordered": reordered,
            "verdict": ("The same records, in another order - no value differs." if reordered else f"Proved the same: {total:,} record(s), every compared field" + (f" ({within} within {tol})" if within else "") + "." if proved else
                        f"{differ:,} of {total:,} record(s) differ" + (f", {only_a} only in the old and {only_b} only in the new" if only_a or only_b else "")
                        + (f"; most in {', '.join(x[0] for x in sorted(by_field.items(), key=lambda kv: -sum(kv[1].values()))[:3])}" if by_field else "") + "."),
            "note": ("Proved for these records only: it says the new output equals the old for the input that produced them, not for every input. "
                     "Feed both with the same inputs, including edge cases (zeros, negatives, the largest values, empty fields, end of month and year).")}


def _line(r: dict[str, str]) -> str:
    return "\x1f".join(r.values())


def _show(r: dict[str, str]) -> str:
    return " | ".join(v.strip() for v in list(r.values())[:8])[:160]
