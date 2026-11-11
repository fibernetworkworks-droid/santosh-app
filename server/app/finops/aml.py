"""#87 AML triage + #88 sanctions/PEP name match. The rows and the watch list are HERS: no built-in list, no threshold of ours. Output is for an analyst; filing an STR belongs to the MLRO."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def triage(txns: list[dict], cash_threshold: Any = 1000000, structuring_band_pct: Any = 10, min_structured: int = 3, passthrough_pct: Any = 90,
           fanout: int = 10) -> dict[str, Any]:
    if not txns:
        raise ValueError("txns rows do: account, date, amount, type (cash_in/cash_out/credit/debit), counterparty.")
    thr, band = _f(cash_threshold), _f(structuring_band_pct)
    by = defaultdict(list)
    for t in txns[:20000]:
        by[str(t.get("account") or "?")].append(t)
    alerts = []
    for acc, ts in by.items():
        low = thr * (1 - band / 100.0)
        near = [t for t in ts if str(t.get("type", "")).startswith("cash") and low <= _f(t.get("amount")) < thr]
        if len(near) >= min_structured:
            alerts.append({"account": acc, "rule": "structuring_like", "evidence": [(t.get("date"), _f(t.get("amount"))) for t in near[:10]],
                           "why": f"{len(near)} cash entries between Rs {low:,.0f}-{thr:,.0f} (just under the limit)."})
        cin = sum(_f(t.get("amount")) for t in ts if str(t.get("type")) in ("credit", "cash_in"))
        cout = sum(_f(t.get("amount")) for t in ts if str(t.get("type")) in ("debit", "cash_out"))
        if cin and cout >= cin * _f(passthrough_pct) / 100.0 and cin >= thr * 0.5:
            alerts.append({"account": acc, "rule": "pass_through", "evidence": {"in": round(cin, 2), "out": round(cout, 2)},
                           "why": f"About as much went out (Rs {cout:,.0f}) as came in (Rs {cin:,.0f})."})
        cps = {str(t.get("counterparty")) for t in ts if t.get("counterparty")}
        if len(cps) >= fanout:
            alerts.append({"account": acc, "rule": "many_counterparties", "evidence": len(cps), "why": f"{len(cps)} different counterparties."})
        rnd = [t for t in ts if _f(t.get("amount")) >= 10000 and _f(t.get("amount")) % 10000 == 0]
        if len(ts) >= 5 and len(rnd) / len(ts) >= 0.8:
            alerts.append({"account": acc, "rule": "round_amounts", "evidence": len(rnd), "why": "Most amounts are round (multiples of 10,000)."})
    for a in alerts:
        a["kind"] = "heuristic"
        a["draft_narrative"] = (f"Account {a['account']}: rule '{a['rule']}' fired. {a['why']} Customer's profile / income / occupation: [analyst to fill in]. "
                                "The alert may have an innocent cause: [analyst's view]. Next step: [analyst to decide].")
    return {"alerts": alerts, "accounts": len(by), "clean_accounts": len(by) - len({a["account"] for a in alerts}),
            "kind_note": "These rules are signals, not proof; most alerts turn out to be false. The threshold is the one you gave, not ours.",
            "decider": "Closing a case or deciding on an STR is for the analyst / MLRO; nothing is filed here."}


_TITLES = {"mr", "mrs", "ms", "dr", "shri", "smt", "sri", "kumari", "md", "mohd", "mohammad", "muhammad", "mohammed"}


def _norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in _TITLES]


def _lev1(a: str, b: str) -> bool:
    """True when a and b are within ONE edit (insert / delete / substitute)."""
    if abs(len(a) - len(b)) > 1:
        return False
    i = j = d = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1; j += 1
            continue
        d += 1
        if d > 1:
            return False
        if len(a) == len(b):
            i += 1; j += 1
        elif len(a) > len(b):
            i += 1
        else:
            j += 1
    return d + (len(a) - i) + (len(b) - j) <= 1


def _tok_sim(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if len(a) == 1 or len(b) == 1:
        return 0.6 if a[0] == b[0] else 0.0
    if len(a) >= 4 and len(b) >= 4 and _lev1(a, b):
        return 0.85
    return 0.0


def screen(names: list[str], watch: list[dict], threshold: Any = 0.7) -> dict[str, Any]:
    if not names or not watch:
        raise ValueError("Give names and a watch list (your own: [{name, list, ref}]); we have no list of our own.")
    th = _f(threshold)
    res = []
    for n in names[:500]:
        nt = _norm(n)
        hits = []
        for w in watch[:20000]:
            wt = _norm(w.get("name"))
            if not nt or not wt:
                continue
            used, total, why = set(), 0.0, []
            for a in nt:
                best, bj = 0.0, None
                for j, b in enumerate(wt):
                    if j in used:
                        continue
                    s = _tok_sim(a, b)
                    if s > best:
                        best, bj = s, j
                if bj is not None and best:
                    used.add(bj)
                    total += best
                    why.append(f"{a}~{wt[bj]}={best:.2f}")
            score = total / max(len(nt), len(wt))
            if score >= th:
                hits.append({"watch_name": w.get("name"), "list": w.get("list"), "ref": w.get("ref"), "score": round(score, 2), "explained_by": why})
        res.append({"name": n, "possible_matches": sorted(hits, key=lambda h: -h["score"])[:5]})
    return {"results": res, "threshold": th, "not_checked": "Date of birth, country, ID, alias spellings in other scripts: these were not matched. The score is name similarity, not identity.",
            "decider": "Whether it is a true match is decided by the compliance officer; nothing is blocked or frozen here."}
