"""Toil, worked out in code: the manual, repeated work that grows with the service.

A toil list (CSV) in either shape:
- a log, one line each time it was done: date, task, minutes (and who, if you have it);
- a summary, one line per task: task, minutes each time, times a week (or a month).
Add `automate_hours` (your estimate of the one-off work to automate a task) for the payback.
-> hours a week per task and per person, the share of a working week (the Google SRE book keeps toil under 50% of an SRE's time),
the tasks to automate first by payback, and the hours a year each one costs. A toil list is data, never instructions."""
from __future__ import annotations

import csv
import io
from datetime import timedelta
from typing import Any

from .alerts import MAX, MAX_ROWS, _t
from .oncall import _col


class ToilError(ValueError):
    pass


def _f(v: str) -> float | None:
    try:
        x = float(str(v).strip().replace(",", ""))
    except ValueError:
        return None
    return x if x >= 0 else None


def toil(text: str, week_hours: float = 40, cap_pct: float = 50, people: int = 0) -> dict[str, Any]:
    text = str(text or "")[:MAX * 3].strip()
    if not text:
        raise ToilError("Paste the toil list first (CSV): date, task, minutes - or task, minutes, times a week.")
    try:
        week_hours = float(week_hours)
        cap = float(cap_pct) / 100
    except (TypeError, ValueError):
        raise ToilError("Week hours and the cap: numbers.")
    if not 1 <= week_hours <= 100 or not 0 < cap <= 1:
        raise ToilError("Week hours 1-100, the cap 1-100%.")
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip().lower() for h in rows[0]]
    ki = _col(head, "task", "what", "work", "job", "activity", "name")
    mi = _col(head, "minutes", "mins", "min", "duration_min", "time_min", "minutes_each")
    hi = _col(head, "hours", "hrs", "duration_h")
    di = next((head.index(k) for k in ("date", "day", "when", "done_at", "time", "timestamp") if k in head), None)   # exact: "time" is in "times_week"
    wi = _col(head, "who", "person", "engineer", "user", "owner")
    fwi = _col(head, "per_week", "times_week", "times_a_week", "weekly", "count_week")
    fmi = _col(head, "per_month", "times_month", "times_a_month", "monthly")
    ai = _col(head, "automate_hours", "automate_h", "fix_hours", "effort_h", "effort_hours")
    if ki is None or (mi is None and hi is None):
        raise ToilError("The CSV needs a task column and a minutes (or hours) column.")
    summary = (fwi is not None or fmi is not None) and di is None
    tasks: dict[str, dict[str, Any]] = {}
    who: dict[str, float] = {}
    dates = []
    bad = 0
    for r in rows[1:MAX_ROWS + 1]:
        if len(r) <= ki:
            continue
        name = r[ki].strip()[:120]
        mins = _f(r[mi]) if mi is not None and len(r) > mi else None
        if mins is None and hi is not None and len(r) > hi:
            h = _f(r[hi])
            mins = h * 60 if h is not None else None
        if not name or mins is None:
            bad += 1
            continue
        t = tasks.setdefault(name, {"task": name, "minutes": 0.0, "times": 0.0, "auto_h": None, "who": set()})
        if ai is not None and len(r) > ai:
            a = _f(r[ai])
            if a is not None:
                t["auto_h"] = max(t["auto_h"] or 0, a)
        p = r[wi].strip()[:80] if wi is not None and len(r) > wi else ""
        if summary:
            per_w = _f(r[fwi]) if fwi is not None and len(r) > fwi else None
            if per_w is None and fmi is not None and len(r) > fmi:
                pm = _f(r[fmi])
                per_w = pm * 12 / 52 if pm is not None else None
            if per_w is None:
                bad += 1
                continue
            t["minutes"] += mins * per_w
            t["times"] += per_w
            if p:
                t["who"].add(p)
                who[p] = who.get(p, 0) + mins * per_w
        else:
            d = _t(r[di]) if di is not None and len(r) > di else None
            if di is not None and d is None:
                bad += 1
                continue
            if d is not None:
                dates.append(d)
            t["minutes"] += mins
            t["times"] += 1
            if p:
                t["who"].add(p)
                who[p] = who.get(p, 0) + mins
    if not tasks:
        raise ToilError("No line had a task and a number of minutes.")
    if summary:
        weeks = 1.0
    else:
        if len(dates) < 2:
            raise ToilError("A log needs dates on at least 2 lines - or give times a week per task instead.")
        weeks = max((max(dates) - min(dates) + timedelta(days=1)).total_seconds() / 604800, 1 / 7)
    out = []
    for t in tasks.values():
        hw = t["minutes"] / 60 / weeks
        row = {"task": t["task"], "hours_week": round(hw, 2), "hours_year": round(hw * 52, 1), "times_week": round(t["times"] / weeks, 2),
               "minutes_each": round(t["minutes"] / t["times"], 1) if t["times"] else None, "people": sorted(t["who"])[:10],
               "automate_hours": t["auto_h"], "payback_weeks": round(t["auto_h"] / hw, 1) if t["auto_h"] and hw > 0 else None}
        out.append(row)
    out.sort(key=lambda r: -r["hours_week"])
    total = sum(r["hours_week"] for r in out)
    n_people = int(people) if people and int(people) > 0 else (len(who) or 1)
    per_person = total / n_people
    share = per_person / week_hours
    by_who = sorted(({"who": k, "hours_week": round(v / 60 / weeks, 2), "share": round(v / 60 / weeks / week_hours, 3)} for k, v in who.items()),
                    key=lambda r: -r["hours_week"])
    first = sorted([r for r in out if r["payback_weeks"] is not None], key=lambda r: r["payback_weeks"])
    issues = []
    if share > cap:
        issues.append({"sev": "bad", "text": f"Toil is {share:.0%} of each person's week ({per_person:.1f} h of {week_hours:g}): over your "
                                             f"{cap:.0%} cap. Engineering work stops when toil takes this much."})
    elif share > cap * 0.66:
        issues.append({"sev": "warn", "text": f"Toil is {share:.0%} of each person's week: close to your {cap:.0%} cap."})
    for p in by_who:
        if p["share"] > cap:
            issues.append({"sev": "warn", "text": f"{p['who']} spends {p['share']:.0%} of the week on toil ({p['hours_week']:g} h)."})
    top = out[0]
    if total and top["hours_week"] / total > 0.4 and len(out) > 2:
        issues.append({"sev": "info", "text": f"'{top['task']}' alone is {top['hours_week'] / total:.0%} of all toil: automate it first."})
    quick = [r for r in first if r["payback_weeks"] <= 12]
    if quick:
        issues.append({"sev": "info", "text": "Pays back within 12 weeks: " + ", ".join(f"{r['task']} ({r['payback_weeks']:g} weeks)" for r in quick[:5]) + "."})
    if not any(r["automate_hours"] for r in out):
        issues.append({"sev": "info", "text": "Add an automate_hours column (your estimate) to see which task pays back first."})
    return {"ok": True, "tasks": len(out), "shape": "summary" if summary else "log", "weeks": round(weeks, 2), "hours_week": round(total, 2),
            "hours_year": round(total * 52, 1), "people": n_people, "per_person_h": round(per_person, 2), "share": round(share, 3),
            "cap": cap, "week_hours": week_hours, "table": out[:200], "by_who": by_who[:50], "automate_first": first[:10],
            "unreadable": bad, "issues": issues,
            "verdict": (f"{total:.1f} h of toil a week across {len(out)} task(s) - {per_person:.1f} h per person, {share:.0%} of a "
                        f"{week_hours:g}-hour week (cap {cap:.0%}). The biggest: {top['task']} ({top['hours_week']:g} h a week).")}
