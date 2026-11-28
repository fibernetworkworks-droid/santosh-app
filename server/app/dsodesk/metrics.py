"""How fast security findings get fixed, from an export of findings over time (CSV: id, severity, opened, closed - closed blank if
still open; optional team and source): what is open now by severity and age, what is past her fix-time rule, the median and 90th
percentile time to fix per severity, the share fixed within the rule, opened against closed week by week, and whether the backlog
is growing. Worked out from the dates given - nothing is looked up."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..mldesk.table import TableError, read
from .common import DsoInputError, col, day, finder, finish, median, quantile


class MetricsError(TableError):
    pass


SEVS = ("critical", "high", "medium", "low")


def _sev(v: str) -> str:
    s = str(v or "").strip().lower()
    return {"crit": "critical", "p1": "critical", "sev1": "critical", "p2": "high", "sev2": "high", "moderate": "medium", "p3": "medium", "sev3": "medium",
            "p4": "low", "sev4": "low", "info": "low", "informational": "low"}.get(s, s if s in SEVS else "medium")


def analyse(text: str, sla: dict[str, float] | None = None, today: Any = None) -> dict[str, Any]:
    head, rows = read(text, "The findings")
    ix = {"id": col(head, r"id", r"key", r"finding", r"cve", r"title"), "sev": col(head, r"severity", r"sev", r"priority", r"risk"),
          "op": col(head, r"opened(at|on|date)?", r"created(at|on|date)?", r"found(at|on|date)?", r"firstseen", r"detected(at|on)?", r"start"),
          "cl": col(head, r"closed(at|on|date)?", r"fixed(at|on|date)?", r"resolved(at|on|date)?", r"remediated(at|on)?", r"end"),
          "team": col(head, r"team", r"owner", r"squad", r"service", r"repo(sitory)?"), "src": col(head, r"source", r"tool", r"scanner")}
    if ix["sev"] is None or ix["op"] is None:
        raise MetricsError("The findings need a severity column and an opened date column (closed blank while open).")
    td = day(today) if today else date.today()
    sl = {"critical": 7, "high": 30, "medium": 90, "low": 180, **{k: v for k, v in (sla or {}).items() if v}}
    g = lambda r, k: r[ix[k]] if ix[k] is not None else ""   # noqa: E731
    issues, add = finder()
    items = []
    for r in rows:
        try:
            op = day(g(r, "op"))
            cl = day(g(r, "cl")) if g(r, "cl") else None
        except DsoInputError as e:
            raise MetricsError(f"{g(r, 'id')}: {e}")
        if op is None:
            continue
        if cl and cl < op:
            raise MetricsError(f"{g(r, 'id')}: closed before it was opened.")
        s = _sev(g(r, "sev"))
        age = ((cl or td) - op).days
        items.append({"id": g(r, "id"), "sev": s, "opened": op.isoformat(), "closed": cl.isoformat() if cl else "", "days": age, "open": cl is None,
                      "late": age > sl[s], "team": g(r, "team") or "", "source": g(r, "src") or ""})
    if not items:
        raise MetricsError("No findings with an opened date.")
    per = []
    for s in SEVS:
        mine = [x for x in items if x["sev"] == s]
        done = [x["days"] for x in mine if not x["open"]]
        op = [x for x in mine if x["open"]]
        per.append({"sev": s, "sla": sl[s], "total": len(mine), "open": len(op), "open_late": sum(1 for x in op if x["late"]), "closed": len(done),
                    "mttr": median(done) if done else None, "p90": quantile(done, 0.9) if done else None,
                    "in_sla": (sum(1 for d_ in done if d_ <= sl[s]) / len(done)) if done else None, "oldest": max((x["days"] for x in op), default=None)})
    first = min(date.fromisoformat(x["opened"]) for x in items)
    start = first - timedelta(days=first.weekday())
    weeks = []
    w = start
    while w <= td and len(weeks) < 104:
        e = w + timedelta(days=7)
        o = sum(1 for x in items if w <= date.fromisoformat(x["opened"]) < e)
        c = sum(1 for x in items if x["closed"] and w <= date.fromisoformat(x["closed"]) < e)
        backlog = sum(1 for x in items if date.fromisoformat(x["opened"]) < e and (not x["closed"] or date.fromisoformat(x["closed"]) >= e))
        weeks.append({"week": w.isoformat(), "opened": o, "closed": c, "backlog": backlog})
        w = e
    buckets = {"0-7": 0, "8-30": 0, "31-90": 0, "91-180": 0, "180+": 0}
    for x in items:
        if x["open"]:
            d_ = x["days"]
            buckets["0-7" if d_ <= 7 else "8-30" if d_ <= 30 else "31-90" if d_ <= 90 else "91-180" if d_ <= 180 else "180+"] += 1
    late = [x for x in items if x["open"] and x["late"]]
    for p in per:
        if p["open_late"]:
            add("bad" if p["sev"] in ("critical", "high") else "warn", "Past the fix time", f"{p['open_late']} open {p['sev']} finding(s) are older than your {p['sla']:g} days (oldest {p['oldest']} days).",
                "Fix them or record an accepted risk with an end date.", p["sev"])
        if p["in_sla"] is not None and p["in_sla"] < 0.8 and p["closed"] >= 5:
            add("warn", "Fix times missed", f"Only {p['in_sla'] * 100:.0f}% of {p['sev']} findings were fixed within {p['sla']:g} days (median {p['mttr']:g} days).", "Look at where they wait.", p["sev"])
    trend = None
    if len(weeks) >= 8:
        a, b = weeks[-8]["backlog"], weeks[-1]["backlog"]
        trend = b - a
        if b > a * 1.2 and b - a >= 3:
            add("warn", "Backlog growing", f"The open backlog grew from {a} to {b} over the last 8 weeks.", "More is found than fixed - add fixing time or narrow what is scanned.")
    teams: dict[str, dict[str, int]] = {}
    for x in items:
        if x["team"]:
            t_ = teams.setdefault(x["team"], {"open": 0, "late": 0, "total": 0})
            t_["total"] += 1
            t_["open"] += x["open"]
            t_["late"] += x["open"] and x["late"]
    late.sort(key=lambda x: ({"critical": 0, "high": 1, "medium": 2, "low": 3}[x["sev"]], -x["days"]))
    opn = sum(1 for x in items if x["open"])
    res = {"findings": len(items), "open": opn, "late": len(late), "per": per, "weeks": weeks, "buckets": buckets, "late_list": late[:200], "trend": trend, "today": td.isoformat(),
           "teams": sorted(({"team": k, **v} for k, v in teams.items()), key=lambda t_: (-t_["late"], -t_["open"]))[:30], "sla": sl,
           "verdict": f"{opn} open of {len(items)}, {len(late)} past the fix time"}
    res["note"] = "Ages count calendar days from the opened date to the closed date (or today). Median and 90th percentile are of findings already fixed."
    return finish(res, issues)
