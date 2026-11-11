"""Health insurance Wave 3 engines (#4 experience, #5 price trend, #6 run-off triangle, #7 pricing fairness, #22/#24 underwriting triage + explainer,
#55 provider outliers, #56 duplicates, #58 geo plausibility, #59 cashless misuse, #60 case builder, #62/#76 fairness + override audit, #88 scheme anomalies).
Pure functions. Rules, thresholds, loadings and peer sets are HERS. A hit is a question for a named person; nothing is declined, accused, repriced or reserved here."""
from __future__ import annotations

import datetime as dt
import math
import statistics as st
from collections import defaultdict
from typing import Any

PROTECTED = ("religion", "caste", "community", "gender", "sex", "race", "ethnic", "locality", "pincode_religion", "marital", "sexual", "disability_status", "surname", "name")


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _d(v: Any) -> dt.date:
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Could not read the date: '{v}' (use 2026-11-05).")


def _no_protected(names, what="rule"):
    bad = [n for n in names if any(p == str(n).lower() or str(n).lower().startswith(p + "_") for p in PROTECTED)]
    if bad:
        raise ValueError(f"{what} cannot be built on a protected attribute: {', '.join(map(str, bad))}. Use a medical / age-band rule.")


def experience(rows: list[dict], group_by: str = "age_band", loss_ratio_alert: Any = 100, min_exposure: Any = 0) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows do: premium, paid, claims, exposure (policy-years) aur group column.")
    _no_protected([group_by], "grouping")
    g: dict[str, dict] = defaultdict(lambda: {"premium": 0.0, "paid": 0.0, "claims": 0.0, "exposure": 0.0})
    for r in rows[:100000]:
        k = str(r.get(group_by, "all"))
        for f in ("premium", "paid", "claims", "exposure"):
            g[k][f] += _f(r.get(f))
    out, alerts = [], []
    for k, v in sorted(g.items()):
        lr = round(100 * v["paid"] / v["premium"], 2) if v["premium"] else None
        row = {"group": k, "premium": round(v["premium"], 2), "paid": round(v["paid"], 2), "loss_ratio_pct": lr,
               "frequency_per_year": round(v["claims"] / v["exposure"], 4) if v["exposure"] else None,
               "severity": round(v["paid"] / v["claims"], 2) if v["claims"] else None, "exposure": v["exposure"], "thin": v["exposure"] < _f(min_exposure)}
        out.append(row)
        if lr is not None and lr > _f(loss_ratio_alert) and not row["thin"]:
            alerts.append(k)
    return {"groups": out, "above_alert": alerts, "decider": "appointed actuary", "note": "Descriptive only: a high loss ratio is a question for the actuary, not a price change. Thin groups are marked.", "not_checked": ["credibility", "trend", "IBNR"]}


def price_trend(obs: list[dict]) -> dict[str, Any]:
    if not obs:
        raise ValueError("obs rows do: item, year, price.")
    by: dict[str, dict] = defaultdict(dict)
    for o in obs[:20000]:
        by[str(o.get("item"))][int(_f(o.get("year")))] = _f(o.get("price"))
    out = []
    for it, ys in by.items():
        if len(ys) < 2:
            out.append({"item": it, "note": "one year only"})
            continue
        a, b = min(ys), max(ys)
        n = b - a
        out.append({"item": it, "from": a, "to": b, "start": ys[a], "end": ys[b], "cagr_pct": round(100 * ((ys[b] / ys[a]) ** (1 / n) - 1), 2) if ys[a] > 0 and n > 0 else None})
    return {"items": out, "decider": "appointed actuary", "note": "Observed price change between the first and last year given; not a forecast."}


def triangle(tri: list[list], tail: Any = 1.0) -> dict[str, Any]:
    """Cumulative run-off triangle, one row per origin period, rows shorter as periods are newer."""
    if len(tri or []) < 3:
        raise ValueError("At least 3 origin rows are needed (cumulative paid, newer rows shorter).")
    n = max(len(r) for r in tri)
    fac = []
    for j in range(n - 1):
        num = sum(_f(r[j + 1]) for r in tri if len(r) > j + 1)
        den = sum(_f(r[j]) for r in tri if len(r) > j + 1)
        fac.append(round(num / den, 4) if den else 1.0)
    rows, ib = [], 0.0
    for i, r in enumerate(tri):
        last = _f(r[-1])
        ult = last
        for j in range(len(r) - 1, n - 1):
            ult *= fac[j]
        ult *= _f(tail)
        ib += ult - last
        rows.append({"origin": i, "latest": last, "ultimate": round(ult, 2), "unpaid": round(ult - last, 2)})
    return {"development_factors": fac, "rows": rows, "total_unpaid": round(ib, 2), "method": "volume-weighted chain-ladder, tail as given",
            "decider": "appointed actuary (reserve sign-off is reserved to them)", "note": "A working paper. One method only; compare others and apply judgement before any reserve.", "not_checked": ["tail factor", "inflation", "mix change"]}


def pricing_fairness(factors: list[dict], max_jump_pct: Any = 30, max_gap_pct: Any = 15) -> dict[str, Any]:
    """factors: [{factor, level, premium_relativity, cost_relativity}] relativities vs base 1.0"""
    if not factors:
        raise ValueError("factors rows do: factor, level, premium_relativity, cost_relativity.")
    _no_protected([f.get("factor") for f in factors], "rating factor")
    hits = []
    for f in factors[:2000]:
        p, c = _f(f.get("premium_relativity")), _f(f.get("cost_relativity"))
        if c > 0 and abs(p / c - 1) * 100 > _f(max_gap_pct):
            hits.append({"factor": f.get("factor"), "level": f.get("level"), "premium_rel": p, "cost_rel": c, "gap_pct": round((p / c - 1) * 100, 1), "issue": "premium moves differently from cost: explain or fix"})
    lv: dict[str, list] = defaultdict(list)
    for f in factors:
        lv[str(f.get("factor"))].append((str(f.get("level")), _f(f.get("premium_relativity"))))
    jumps = []
    for k, v in lv.items():
        for (a, x), (b, y) in zip(v, v[1:]):
            if x > 0 and abs(y / x - 1) * 100 > _f(max_jump_pct):
                jumps.append({"factor": k, "between": [a, b], "jump_pct": round((y / x - 1) * 100, 1)})
    return {"gaps": hits, "jumps": jumps, "decider": "chief risk officer / appointed actuary", "note": "Protected attributes are refused as factors. This tests premium vs cost relativities you give; it does not prove or clear a proxy.", "not_checked": ["proxy correlation between factors"]}


def uw_triage(proposals: list[dict], rules: list[dict]) -> dict[str, Any]:
    """rules: [{field, op (>,>=,<,<=,==,in), value, route (medical|refer), label, manual_ref, loading_pct}]; default auto_accept. A 'decline' route becomes refer."""
    if not proposals or not rules:
        raise ValueError("proposals aur rules (field, op, value, route) do.")
    _no_protected([r.get("field") for r in rules])
    out = []
    for p in proposals[:5000]:
        hits = []
        for r in rules:
            v = p.get(r.get("field"))
            if v in (None, ""):
                continue
            op, t = r.get("op", "=="), r.get("value")
            try:
                ok = {">": lambda: _f(v) > _f(t), ">=": lambda: _f(v) >= _f(t), "<": lambda: _f(v) < _f(t), "<=": lambda: _f(v) <= _f(t),
                      "==": lambda: str(v).lower() == str(t).lower(), "in": lambda: str(v).lower() in [str(x).lower() for x in (t or [])]}[op]()
            except KeyError:
                raise ValueError(f"invalid op: {op}")
            if ok:
                rt = str(r.get("route", "refer")).lower()
                hits.append({"label": r.get("label") or r.get("field"), "field": r["field"], "value": v, "route": "refer" if rt == "decline" else rt, "manual_ref": r.get("manual_ref", "[manual page]"),
                             "loading_pct": r.get("loading_pct"), "was_decline_rule": rt == "decline"})
        route = "refer" if any(h["route"] == "refer" for h in hits) else "medical" if hits else "auto_accept"
        out.append({"id": p.get("id"), "route": route, "rules_fired": hits, "loading_pct_if_accepted": round(sum(_f(h["loading_pct"]) for h in hits), 2) or None})
    return {"results": out, "decider": "underwriter (decline, loading and acceptance are theirs)", "note": "Rule routing from YOUR manual. 'Decline' rules route to a human referral; nothing is declined or loaded here.", "not_checked": ["medical reports", "disclosure"]}


def provider_outliers(claims: list[dict], ratio: Any = 1.5, min_peers: Any = 5) -> dict[str, Any]:
    if not claims:
        raise ValueError("claims rows do: provider, procedure, amount (optional los).")
    peers: dict[str, list] = defaultdict(list)
    prov: dict[tuple, list] = defaultdict(list)
    for c in claims[:100000]:
        peers[str(c.get("procedure"))].append(_f(c.get("amount")))
        prov[(str(c.get("provider")), str(c.get("procedure")))].append(_f(c.get("amount")))
    out = []
    for (p, proc), v in prov.items():
        allv = peers[proc]
        if len(allv) < _f(min_peers):
            continue
        med = st.median(allv)
        m = st.mean(v)
        if med > 0 and m / med > _f(ratio):
            out.append({"provider": p, "procedure": proc, "provider_mean": round(m, 2), "peer_median": round(med, 2), "ratio": round(m / med, 2), "claims": len(v)})
    out.sort(key=lambda r: -r["ratio"])
    return {"outliers": out[:200], "decider": "SIU investigator", "note": "A price above the peer median has many honest causes (case mix, tier, city). This is a question list, not an allegation.", "not_checked": ["case mix", "hospital tier", "city"]}


def duplicates(claims: list[dict]) -> dict[str, Any]:
    if not claims:
        raise ValueError("claims rows do: claim, member, hospital, admit, discharge, amount.")
    by = defaultdict(list)
    for c in claims[:50000]:
        by[str(c.get("member"))].append(c)
    overlap, same = [], []
    for m, cs in by.items():
        for i, a in enumerate(cs):
            for b in cs[i + 1:]:
                a1, a2, b1, b2 = _d(a["admit"]), _d(a["discharge"]), _d(b["admit"]), _d(b["discharge"])
                if a1 <= b2 and b1 <= a2:
                    rec = {"member": m, "claims": [a.get("claim"), b.get("claim")], "hospitals": [a.get("hospital"), b.get("hospital")]}
                    (same if a.get("hospital") == b.get("hospital") and a1 == b1 else overlap).append(rec)
    return {"overlapping_stays_different_hospitals": overlap, "same_stay_repeated": same, "decider": "SIU", "note": "Overlap can be a transfer or a data-entry error. Ask, do not assume."}


def _hav(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(x))


def geo_plausibility(stays: list[dict], max_home_km: Any = 300, max_kmph: Any = 90) -> dict[str, Any]:
    """stays: [{claim, member, home:[lat,lon], hospital:[lat,lon], admit}]"""
    if not stays:
        raise ValueError("stays rows do: claim, member, home [lat,lon], hospital [lat,lon], admit.")
    far, fast = [], []
    for s in stays[:50000]:
        d = _hav(s["home"], s["hospital"])
        if d > _f(max_home_km):
            far.append({"claim": s.get("claim"), "km_from_home": round(d)})
    by = defaultdict(list)
    for s in stays:
        by[str(s.get("member"))].append(s)
    for m, ss in by.items():
        ss.sort(key=lambda s: _d(s["admit"]))
        for a, b in zip(ss, ss[1:]):
            days = max((_d(b["admit"]) - _d(a["admit"])).days, 0)
            d = _hav(a["hospital"], b["hospital"])
            if d > 50 and days * 24 * _f(max_kmph) < d:
                fast.append({"member": m, "claims": [a.get("claim"), b.get("claim")], "km": round(d), "days_apart": days})
    return {"far_from_home": far, "impossible_travel": fast, "decider": "SIU", "note": "Distance only. People travel for treatment; coordinates are as given.", "not_checked": ["referral pathway", "emergency travel"]}


def cashless_misuse(cases: list[dict], upgrade_pct: Any = 25, short_stay_days: Any = 1) -> dict[str, Any]:
    if not cases:
        raise ValueError("cases rows do: claim, approved, final, los_days, planned_procedure, final_procedure.")
    out = []
    for c in cases[:50000]:
        ap, fi = _f(c.get("approved")), _f(c.get("final"))
        why = []
        if ap > 0 and (fi / ap - 1) * 100 > _f(upgrade_pct):
            why.append(f"final {round((fi / ap - 1) * 100)}% above approval")
        if c.get("planned_procedure") and c.get("final_procedure") and c["planned_procedure"] != c["final_procedure"]:
            why.append("procedure changed after approval")
        if _f(c.get("los_days")) <= _f(short_stay_days) and fi > 0:
            why.append("very short stay")
        if why:
            out.append({"claim": c.get("claim"), "reasons": why})
    return {"flagged": out, "decider": "SIU + medical officer", "note": "Complications and added procedures are common and legitimate; flagged cases need a medical read, not a conclusion."}


def case_builder(events: list[dict], evidence: list[dict] | None = None, questions: list[str] | None = None) -> dict[str, Any]:
    if not events:
        raise ValueError("events rows do: date, text, source.")
    ev = sorted(events[:1000], key=lambda e: _d(e.get("date")))
    return {"timeline": [{"date": e["date"], "text": e.get("text"), "source": e.get("source", "[source]")} for e in ev],
            "evidence_table": [{"item": x.get("item"), "supports": x.get("supports", "[what it shows]"), "source": x.get("source", "[source]"), "status": x.get("status", "unverified")} for x in (evidence or [])],
            "interview_questions": (questions or []) + ["Walk me through the admission in your own words.", "Who advised the procedure and when?"],
            "allegation": "[reserved to the SIU head: this tool writes none]", "decider": "SIU head", "note": "A neutral file: facts with sources. No conclusion, no accusation."}


def fraud_audit(decisions: list[dict], max_gap: Any = 1.25, min_group: Any = 30) -> dict[str, Any]:
    """decisions: [{flagged, confirmed (true/false/None), group, human_override}]"""
    if not decisions:
        raise ValueError("decisions rows do: flagged, confirmed, group, human_override.")
    _no_protected([k for d in decisions[:20] for k in d if k not in ("flagged", "confirmed", "group", "human_override")], "column")
    g: dict[str, dict] = defaultdict(lambda: {"n": 0, "flagged": 0, "false_pos": 0, "reviewed": 0, "override": 0})
    for d in decisions[:200000]:
        k = str(d.get("group", "all"))
        s = g[k]
        s["n"] += 1
        if d.get("flagged"):
            s["flagged"] += 1
            if d.get("confirmed") is not None:
                s["reviewed"] += 1
                if d.get("confirmed") is False:
                    s["false_pos"] += 1
            if d.get("human_override"):
                s["override"] += 1
    rows = [{"group": k, "n": v["n"], "flag_rate_pct": round(100 * v["flagged"] / v["n"], 2), "false_positive_pct_of_reviewed": round(100 * v["false_pos"] / v["reviewed"], 2) if v["reviewed"] else None,
             "override_pct_of_flagged": round(100 * v["override"] / v["flagged"], 2) if v["flagged"] else None, "thin": v["n"] < _f(min_group)} for k, v in sorted(g.items())]
    rates = [r["flag_rate_pct"] for r in rows if not r["thin"] and r["flag_rate_pct"] > 0]
    gap = round(max(rates) / min(rates), 2) if len(rates) > 1 else None
    return {"groups": rows, "flag_rate_ratio_max_over_min": gap, "disparity_alert": bool(gap and gap > _f(max_gap)), "decider": "chief risk officer / AI governance committee",
            "note": "Groups are whatever neutral grouping you pass (hospital tier, city size, channel). A gap is a question about the model, not proof of bias; thin groups are marked."}


def scheme_anomalies(claims: list[dict], z: Any = 3, min_n: Any = 10) -> dict[str, Any]:
    if not claims:
        raise ValueError("claims rows do: hospital, district, beneficiary_id, amount.")
    ids = defaultdict(list)
    per: dict[str, list] = defaultdict(list)
    for c in claims[:200000]:
        ids[str(c.get("beneficiary_id"))].append(c.get("hospital"))
        per[str(c.get("hospital"))].append(_f(c.get("amount")))
    dup = [{"beneficiary_id": k, "hospitals": sorted(set(map(str, v))), "claims": len(v)} for k, v in ids.items() if len(set(map(str, v))) > 1]
    means = {h: st.mean(v) for h, v in per.items() if len(v) >= _f(min_n)}
    out = []
    if len(means) >= 3:
        mu, sd = st.mean(means.values()), st.pstdev(means.values())
        if sd:
            out = [{"hospital": h, "mean_claim": round(m, 2), "z": round((m - mu) / sd, 2)} for h, m in means.items() if abs((m - mu) / sd) > _f(z)]
    return {"hospital_outliers": out, "beneficiary_in_multiple_hospitals": dup[:200], "decider": "state health agency (action is theirs)", "note": "Statistical outliers and shared IDs are leads to look into, not findings."}
