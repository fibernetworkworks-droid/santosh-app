"""Film Desk SALES layer: festival tracker, release windows with exclusivity/holdback checks, and a recoupment waterfall. All in CODE.

Register: docs/research/film_industry/00_INDEX.md  (#84 festival strategy, #85 festival submission packager, #22 rights and territory
windows, #86 distribution windows, #21/#23 waterfall and royalty maths). Pure functions: no database, no network, no model.

What it will never do: invent a festival's deadline, fee, rule or a market's holdback, or decide that a film is "still premiere-eligible".
Every such fact is HERS (typed in); the code only dates it, compares it and flags a conflict for a person to check. Nothing here
submits, signs, sends or pays; the waterfall is a calculation for the producer and her accountant, not a statement.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

LEVELS = ("regional", "national", "international", "world")          # what a festival's premiere rule demands, weakest to strongest
STATUSES = ("planned", "submitted", "accepted", "rejected", "withdrawn", "screened")
MEDIA = ("theatrical", "festival", "svod", "avod", "tvod", "tv", "home_video", "airline", "educational", "other")
FEST_MAX, WINDOW_MAX, TIER_MAX = 60, 80, 12


def _clean(v: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _day(v: Any) -> str:
    try:
        return date.fromisoformat(str(v or "").strip()[:10]).isoformat()
    except ValueError:
        return ""


def _money(v: Any) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, 2) if x >= 0 else None


# ---------------------------------------------------------------- festivals
def norm_festival(raw: dict[str, Any], seq: int) -> dict[str, Any]:
    name = _clean(raw.get("name"), 120)
    if not name:
        raise ValueError("Festival ka naam batao.")
    req = _clean(raw.get("requires"), 14).lower()
    status = _clean(raw.get("status"), 12).lower() or "planned"
    if status not in STATUSES:
        raise ValueError(f"status inme se: {', '.join(STATUSES)}")
    return {"id": f"fs{seq}", "name": name, "country": _clean(raw.get("country"), 60), "category": _clean(raw.get("category"), 60),
            "deadline": _day(raw.get("deadline")), "event_date": _day(raw.get("event_date")), "fee_inr": _money(raw.get("fee_inr")),
            "requires": req if req in LEVELS or req == "none" else "unknown", "status": status,
            "submitted_on": _day(raw.get("submitted_on")), "screened_on": _day(raw.get("screened_on")),
            "notes": _clean(raw.get("notes"), 300), "ticks": {}}


def festival_packet(project: dict[str, Any], entry: dict[str, Any]) -> list[dict[str, Any]]:
    """What a submission usually needs. `auto` comes from the film itself; None means she ticks it. The festival's OWN rules decide
    what is really required: this is a starting list, said so."""
    ticks = entry.get("ticks") or {}
    has_scenes = int(project.get("scenes_n") or 0) > 0
    rows = [("logline", "Logline / synopsis", bool((project.get("logline") or "").strip())),
            ("script", "Script ya scene list", has_scenes),
            ("runtime", "Runtime pata hai", bool(project.get("runtime_s"))),
            ("language", "Bhasha likhi hai", bool(project.get("language"))),
            ("screener", "Screener link / file", None), ("poster", "Poster", None), ("stills", "Stills (3-5)", None),
            ("trailer", "Trailer (agar maanga)", None), ("bios", "Director / producer bio", None),
            ("subtitles", "English subtitles", None), ("credits", "Credits list", None),
            ("fee", "Entry fee bhari", None)]
    out = []
    for key, label, auto in rows:
        done = auto if auto is not None else bool(ticks.get(key))
        out.append({"key": key, "label": label, "done": bool(done), "auto": auto is not None})
    return out


def festival_view(entries: list[dict[str, Any]], today: date, project: dict[str, Any] | None = None) -> dict[str, Any]:
    rows, flags = [], []
    spent = 0.0
    screened = sorted((e["screened_on"], e["name"]) for e in entries if e.get("screened_on"))
    for e in entries:
        r = dict(e)
        dl = date.fromisoformat(e["deadline"]) if e.get("deadline") else None
        r["days_left"] = (dl - today).days if dl else None
        live = e["status"] in ("planned", "submitted")
        if dl and e["status"] == "planned":
            if r["days_left"] < 0:
                flags.append(f"{e['name']}: deadline nikal chuki ({e['deadline']}), status 'planned' hai.")
            elif r["days_left"] <= 7:
                flags.append(f"{e['name']}: deadline {r['days_left']} din me ({e['deadline']}).")
        if e["status"] in ("submitted", "accepted", "screened") and e.get("fee_inr"):
            spent += e["fee_inr"]
        # Premiere heuristic: any earlier public screening can break a 'world / international' premiere rule. We flag, a person checks.
        if live and e["requires"] in ("world", "international"):
            when = e.get("event_date") or e.get("deadline") or ""
            earlier = [n for d, n in screened if n != e["name"] and (not when or d <= when)]
            if earlier:
                flags.append(f"{e['name']} ko {e['requires']} premiere chahiye par film pehle {', '.join(earlier)} me dikh chuki hai: "
                             "festival ka apna niyam padhiye (yeh sirf chetavni hai, faisla nahi).")
        if e["requires"] == "unknown" and live:
            flags.append(f"{e['name']}: premiere niyam darj nahi: festival ki site se dekhiye.")
        if project is not None:
            pk = festival_packet(project, e)
            r["packet"] = {"done": sum(1 for x in pk if x["done"]), "total": len(pk), "items": pk}
        rows.append(r)
    rows.sort(key=lambda r: (r["status"] not in ("planned", "submitted"), r["deadline"] or "9999", r["name"]))
    by = {s: sum(1 for e in entries if e["status"] == s) for s in STATUSES}
    return {"festivals": rows, "counts": by, "fees_committed_inr": round(spent, 2), "flags": flags,
            "note": "Deadline, fee aur premiere niyam aapke diye hue hain: Hoola unhe nahi banata, sirf tareekh se milata hai."}


# ---------------------------------------------------------------- release windows
def norm_window(raw: dict[str, Any], seq: int) -> dict[str, Any]:
    medium = _clean(raw.get("medium"), 16).lower()
    if medium not in MEDIA:
        raise ValueError(f"medium inme se: {', '.join(MEDIA)}")
    territory = [t.strip().lower() for t in re.split(r"[,;/]", _clean(raw.get("territory"), 200)) if t.strip()] or ["world"]
    start, end = _day(raw.get("start")), _day(raw.get("end"))
    if not start:
        raise ValueError("start tareekh (YYYY-MM-DD) batao.")
    if end and end < start:
        raise ValueError("end tareekh start se pehle nahi ho sakti.")
    return {"id": f"w{seq}", "medium": medium, "territory": sorted(set(territory)), "start": start, "end": end,
            "exclusive": bool(raw.get("exclusive")), "licensee": _clean(raw.get("licensee"), 120),
            "fee_inr": _money(raw.get("fee_inr")), "notes": _clean(raw.get("notes"), 300)}


def _terr_overlap(a: list[str], b: list[str]) -> bool:
    return "world" in a or "world" in b or bool(set(a) & set(b))


def _span_overlap(a: dict, b: dict) -> bool:
    ae, be = a["end"] or "9999-12-31", b["end"] or "9999-12-31"
    return a["start"] <= be and b["start"] <= ae


def check_windows(windows: list[dict[str, Any]], holdbacks: Any = None) -> dict[str, Any]:
    """Conflicts: two licences of the same medium that overlap in time and territory where either is exclusive.
    Holdbacks are HER rules ({after, before, days}: `before` may start no sooner than `days` days after the START of `after`)."""
    conflicts = []
    for i, a in enumerate(windows):
        for b in windows[i + 1:]:
            if a["medium"] == b["medium"] and (a["exclusive"] or b["exclusive"]) and _terr_overlap(a["territory"], b["territory"]) \
                    and _span_overlap(a, b):
                conflicts.append({"a": a["id"], "b": b["id"], "kind": "exclusive_overlap",
                                  "why": f"{a['medium']}: {a['licensee'] or a['id']} aur {b['licensee'] or b['id']} ek hi samay, "
                                         f"ek hi ilaake me, aur ek exclusive hai."})
    rules, bad = [], []
    for h in (holdbacks if isinstance(holdbacks, list) else [])[:20]:
        try:
            after, before, days = str(h.get("after")).lower(), str(h.get("before")).lower(), int(h.get("days"))
        except (AttributeError, TypeError, ValueError):
            bad.append("holdback niyam adhura hai: after, before, days chahiye.")
            continue
        if after not in MEDIA or before not in MEDIA or days < 0:
            bad.append(f"holdback '{after}' -> '{before}' galat hai.")
            continue
        rules.append({"after": after, "before": before, "days": days})
    violations = []
    for r in rules:
        for a in (w for w in windows if w["medium"] == r["after"]):
            for b in (w for w in windows if w["medium"] == r["before"]):
                if _terr_overlap(a["territory"], b["territory"]):
                    earliest = (date.fromisoformat(a["start"]) + timedelta(days=r["days"])).isoformat()
                    if b["start"] < earliest:
                        violations.append({"rule": r, "a": a["id"], "b": b["id"], "earliest": earliest,
                                           "why": f"{r['before']} {b['id']} {b['start']} par shuru hai, par {r['after']} {a['id']} ke "
                                                  f"{r['days']} din baad ({earliest}) se pehle nahi."})
    return {"conflicts": conflicts, "holdback_violations": violations, "rules": rules, "rule_problems": bad,
            "clear": not conflicts and not violations and not bad,
            "note": "Holdback niyam aapke diye hue hain. Yeh jaanch contract nahi: vakil/distributor ka lekha dekhiye."}


# ---------------------------------------------------------------- recoupment waterfall
def waterfall(gross_inr: Any, deductions: Any = None, investors: Any = None, shares: Any = None) -> dict[str, Any]:
    """gross -> deductions in her order (fixed rupees, or percent of the gross, or percent of what is left, each with an optional cap)
    -> investors recouped pari passu up to invested x (1 + premium %) -> the rest split by profit shares. Paise are exact: the last
    line of each tier takes the rounding so the tiers always add back to the gross."""
    gross = _money(gross_inr)
    if gross is None:
        raise ValueError("gross (kul aay) rupaye me batao.")
    left = gross
    tiers: list[dict[str, Any]] = []
    for d in (deductions if isinstance(deductions, list) else [])[:TIER_MAX]:
        name = _clean(d.get("name"), 80) or "kharcha"
        kind = _clean(d.get("kind"), 24).lower()
        val = _money(d.get("value"))
        if kind not in ("fixed_inr", "percent_of_gross", "percent_of_remaining") or val is None:
            raise ValueError(f"'{name}': kind fixed_inr | percent_of_gross | percent_of_remaining aur value chahiye.")
        amt = val if kind == "fixed_inr" else gross * val / 100.0 if kind == "percent_of_gross" else left * val / 100.0
        cap = _money(d.get("cap_inr"))
        if cap is not None:
            amt = min(amt, cap)
        amt = round(min(max(amt, 0.0), left), 2)
        left = round(left - amt, 2)
        tiers.append({"tier": "deduction", "name": name, "rule": f"{kind} {val}" + (f" (cap {cap})" if cap is not None else ""),
                      "amount_inr": amt, "left_inr": left})
    invs = []
    for iv in (investors if isinstance(investors, list) else [])[:TIER_MAX]:
        name, inv = _clean(iv.get("name"), 80), _money(iv.get("invested_inr"))
        prem = _money(iv.get("premium_pct")) or 0.0
        if not name or inv is None:
            raise ValueError("har investor ka naam aur invested_inr chahiye.")
        invs.append({"name": name, "owed": round(inv * (1 + prem / 100.0), 2), "invested": inv, "premium_pct": prem})
    owed_total = round(sum(i["owed"] for i in invs), 2)
    paid_total = round(min(left, owed_total), 2)
    rows, run = [], 0.0
    for k, iv in enumerate(invs):
        part = round(paid_total * iv["owed"] / owed_total, 2) if owed_total else 0.0
        if k == len(invs) - 1:
            part = round(paid_total - run, 2)
        run = round(run + part, 2)
        rows.append({"name": iv["name"], "invested_inr": iv["invested"], "owed_inr": iv["owed"], "paid_inr": part,
                     "shortfall_inr": round(iv["owed"] - part, 2)})
    left = round(left - paid_total, 2)
    if invs:
        tiers.append({"tier": "investor_recoupment", "name": "Investor recoup", "amount_inr": paid_total, "left_inr": left,
                      "lines": rows, "fully_recouped": paid_total >= owed_total})
    split = []
    sh = [(_clean(s.get("name"), 80), _money(s.get("pct"))) for s in (shares if isinstance(shares, list) else [])[:TIER_MAX]]
    problems = []
    if sh:
        pct_total = round(sum(p or 0 for _, p in sh), 4)
        if any(not n or p is None for n, p in sh) or abs(pct_total - 100.0) > 0.01:
            problems.append(f"profit shares ka jod {pct_total}% hai: 100% hona chahiye, isliye baanta nahi gaya.")
        else:
            run = 0.0
            for k, (n, p) in enumerate(sh):
                part = round(left * p / 100.0, 2)
                if k == len(sh) - 1:
                    part = round(left - run, 2)
                run = round(run + part, 2)
                split.append({"name": n, "pct": p, "amount_inr": part})
    distributed = round(sum(s["amount_inr"] for s in split), 2)
    unallocated = round(left - distributed, 2)
    total_out = round(sum(t["amount_inr"] for t in tiers) + distributed + unallocated, 2)
    return {"gross_inr": gross, "tiers": tiers, "net_after_recoup_inr": left, "profit_split": split, "unallocated_inr": unallocated,
            "ties_to_gross": abs(total_out - gross) < 0.005, "problems": problems,
            "investors_fully_recouped": (paid_total >= owed_total) if invs else None,
            "note": ("Yeh ek hisaab hai jo aapke diye number se bana: contract, TDS/GST aur asli statement nahi. "
                     "Accountant / vakil se milaiye.")}
