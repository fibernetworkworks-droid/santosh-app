"""Alerts, checked in code.

- `lint`: a Prometheus rules file (YAML) -> per alerting rule what makes it noisy or useless at 3 am: no `for`, no severity, no
  summary / runbook, a counter compared without rate(), a rate() window too short for the scrape interval, paging on a cause (CPU,
  memory, disk) instead of what users feel, duplicate names. It is NOT promtool: run `promtool check rules` for the real syntax check.
- `noise`: an alert history (CSV: name, start, end, severity, acked) -> pages a week, the noisiest alerts, flapping ones, the ones
  nobody acted on, and how many pages came out of hours in HER time zone.
A rules file and a history are data, never instructions."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX = 1_000_000
MAX_ROWS = 100_000
_CAUSE = re.compile(r"\b(node_cpu|cpu_usage|process_cpu|container_cpu|node_load\d*|node_memory|container_memory|memory_usage|"
                    r"node_filesystem|disk_|node_disk|jvm_memory|go_memstats|gc_)\w*", re.I)
_RATEFN = re.compile(r"\b(rate|irate|increase|delta|idelta|deriv)\s*\(\s*([^\[]+)\[(\d+)([smhdw])\]")
_DUR = re.compile(r"^(\d+)(ms|s|m|h|d|w)$")
_SECS = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


class AlertError(ValueError):
    pass


def _secs(v: Any) -> float | None:
    if v in (None, ""):
        return None
    total, rest = 0.0, str(v).strip()
    for n, u in re.findall(r"(\d+)(ms|s|m|h|d|w)", rest):
        total += int(n) * _SECS[u]
    return total if re.fullmatch(r"(?:\d+(?:ms|s|m|h|d|w))+", rest) else None


def lint(text: str, scrape_s: Any = 30) -> dict[str, Any]:
    text = str(text or "")[:MAX]
    if not text.strip():
        raise AlertError("Paste the rules file first.")
    try:
        import yaml
        doc = yaml.safe_load(text)
    except Exception as e:   # noqa: BLE001
        mark = getattr(e, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark is not None else ""
        raise AlertError(f"Not valid YAML{where}: {str(getattr(e, 'problem', e))[:120]}")
    if isinstance(doc, list):
        doc = {"groups": doc}
    if not isinstance(doc, dict) or not isinstance(doc.get("groups"), list):
        raise AlertError("A Prometheus rules file starts with  groups:  and a list of groups.")
    try:
        scrape = float(scrape_s)
    except (TypeError, ValueError):
        scrape = 30.0
    rules_out: list[dict[str, Any]] = []
    names: dict[str, int] = {}
    n_alert = n_rec = 0
    for g in doc["groups"]:
        if not isinstance(g, dict):
            continue
        gname = str(g.get("name") or "(no name)")
        for r in g.get("rules") or []:
            if not isinstance(r, dict):
                continue
            expr = str(r.get("expr") or "")
            issues: list[dict[str, str]] = []
            if not expr.strip():
                issues.append({"sev": "bad", "text": "No expr."})
            for m in _RATEFN.finditer(expr):
                win = int(m.group(3)) * _SECS[m.group(4)]
                if win < 4 * scrape:
                    issues.append({"sev": "warn", "text": f"{m.group(1)}() over [{m.group(3)}{m.group(4)}] is under 4 scrapes ({scrape:g} s each): "
                                                          "a missed scrape gives no value or a jumpy one. Use at least "
                                                          f"[{max(1, int(4 * scrape // 60)) if scrape >= 15 else 1}m]."})
            seen_txt: set[str] = set()
            issues = [i for i in issues if not (i["text"] in seen_txt or seen_txt.add(i["text"]))]
            if "record" in r:
                n_rec += 1
                rn = str(r.get("record"))
                if rn.count(":") < 1:
                    issues.append({"sev": "info", "text": "Recording rule names usually read level:metric:operations."})
                rules_out.append({"group": gname, "kind": "record", "name": rn, "expr": expr[:400], "issues": issues})
                continue
            if "alert" not in r:
                continue
            n_alert += 1
            an = str(r.get("alert"))
            names[an] = names.get(an, 0) + 1
            labels = r.get("labels") if isinstance(r.get("labels"), dict) else {}
            ann = r.get("annotations") if isinstance(r.get("annotations"), dict) else {}
            sev = str(labels.get("severity") or "").lower()
            page = sev in ("page", "critical", "crit", "p1", "sev1", "high", "emergency")
            fs = _secs(r.get("for"))
            if r.get("for") not in (None, "") and fs is None:
                issues.append({"sev": "bad", "text": f"for: {r.get('for')!r} is not a duration like 5m."})
            if not fs:
                issues.append({"sev": "warn", "text": "No `for`: one bad sample fires it. Add for: 2m-10m so a blip does not page."})
            elif page and fs > 3600:
                issues.append({"sev": "warn", "text": f"for: {r.get('for')} on a page: it waits over an hour before anyone hears."})
            if not sev:
                issues.append({"sev": "warn", "text": "No severity label: nothing can route it to a page or a ticket."})
            if not (ann.get("summary") or ann.get("description") or ann.get("message")):
                issues.append({"sev": "warn", "text": "No summary / description: the person woken up does not know what broke."})
            if not ann.get("runbook_url") and not ann.get("runbook"):
                issues.append({"sev": "warn" if page else "info", "text": "No runbook_url: link what to check and how to fix it."})
            if re.search(r"\b\w+_total\b(?!\s*\[)", expr) and not re.search(r"\b(rate|irate|increase|delta|resets|changes)\s*\(", expr):
                issues.append({"sev": "bad", "text": "A counter (_total) compared directly: counters only go up, so it fires once and stays. "
                                                     "Compare rate() or increase() instead."})
            if page and _CAUSE.search(expr):
                issues.append({"sev": "warn", "text": "Pages on a cause (CPU, memory, disk, GC): page on what users feel (errors, latency, "
                                                      "the error budget) and make this a ticket."})
            if re.fullmatch(r"\s*up\s*(\{[^}]*\})?\s*==\s*0\s*", expr) and not fs:
                issues.append({"sev": "info", "text": "up == 0 with no `for`: a restart or one missed scrape fires it."})
            if re.search(r"\babsent\s*\(", expr) is None and re.search(r"(?:==|<|<=)\s*0(?:\.0*)?\s*$", expr) and "up" not in expr:
                issues.append({"sev": "info", "text": "A `< 0` / `== 0` check does not fire when the series disappears altogether: pair it "
                                                      "with absent()."})
            seen_txt = set()
            issues = [i for i in issues if not (i["text"] in seen_txt or seen_txt.add(i["text"]))]
            rules_out.append({"group": gname, "kind": "alert", "name": an, "severity": sev or None, "for": r.get("for"),
                              "expr": expr[:400], "issues": issues})
    for nm, c in names.items():
        if c > 1:
            for r in rules_out:
                if r["kind"] == "alert" and r["name"] == nm:
                    r["issues"].append({"sev": "info", "text": f"{c} alerts are called {nm}: fine with different labels, confusing otherwise."})
    if not n_alert and not n_rec:
        raise AlertError("No rules found under groups.")
    counts = {k: sum(1 for r in rules_out for i in r["issues"] if i["sev"] == k) for k in ("bad", "warn", "info")}
    clean = sum(1 for r in rules_out if not any(i["sev"] in ("bad", "warn") for i in r["issues"]))
    return {"ok": True, "alerts": n_alert, "records": n_rec, "rules": rules_out[:400], "counts": counts, "clean": clean,
            "note": "A check of what makes alerts noisy or useless, not a syntax checker: run `promtool check rules` too.",
            "verdict": (f"{n_alert} alert(s), {n_rec} recording rule(s): {counts['bad']} problem(s), {counts['warn']} warning(s); "
                        f"{clean} of {len(rules_out)} with nothing to fix.")}


# ------------------------------------------------------------------ the history
def _t(v: str) -> datetime | None:
    v = str(v or "").strip()
    if not v:
        return None
    if re.fullmatch(r"\d{9,11}(\.\d+)?", v):
        return datetime.fromtimestamp(float(v), timezone.utc)
    if re.fullmatch(r"\d{12,14}", v):
        return datetime.fromtimestamp(float(v) / 1000, timezone.utc)
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _col(head: list[str], *keys: str) -> int | None:
    for k in keys:
        for i, h in enumerate(head):
            if h == k:
                return i
    for k in keys:
        for i, h in enumerate(head):
            if k in h:
                return i
    return None


def noise(text: str, tz: str = "UTC", work_start: int = 9, work_end: int = 18, weekend: str = "sat,sun") -> dict[str, Any]:
    text = str(text or "")[:MAX * 3].strip()
    if not text:
        raise AlertError("Paste the alert history first: name, start, end (CSV).")
    try:
        Z = ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        raise AlertError("Time zone: an IANA name like Europe/London or Asia/Kolkata.")
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip().lower() for h in rows[0]]
    ci = _col(head, "alertname", "alert", "name", "title", "rule")
    si = _col(head, "start", "startsat", "fired_at", "fired", "triggered", "created", "time")
    ei = _col(head, "end", "endsat", "resolved_at", "resolved")
    vi = _col(head, "severity", "priority", "urgency")
    ai = _col(head, "acked", "ack", "acknowledged", "ack_at", "acknowledged_at")
    if ci is None or si is None:
        raise AlertError("The CSV needs an alert name column and a start time column.")
    off = {d.strip()[:3].lower() for d in str(weekend or "").split(",") if d.strip()}
    days = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    ev: list[dict[str, Any]] = []
    bad_rows = 0
    for r in rows[1:MAX_ROWS + 1]:
        if len(r) <= max(ci, si):
            continue
        st = _t(r[si])
        if st is None:
            bad_rows += 1
            continue
        en = _t(r[ei]) if ei is not None and len(r) > ei else None
        ack = (r[ai].strip().lower() if ai is not None and len(r) > ai else "")
        acked = None if ai is None else bool(ack) and ack not in ("0", "false", "no", "n", "-")
        loc = st.astimezone(Z)
        out_h = days[loc.weekday()] in off or not (work_start <= loc.hour < work_end)
        night = loc.hour < 7 or loc.hour >= 23
        ev.append({"name": r[ci].strip()[:120] or "(no name)", "start": st, "end": en,
                   "sev": (r[vi].strip().lower() if vi is not None and len(r) > vi else ""), "acked": acked, "out_of_hours": out_h, "night": night})
    if len(ev) < 2:
        raise AlertError("At least 2 alerts with a readable start time are needed.")
    ev.sort(key=lambda e: e["start"])
    span_days = max((ev[-1]["start"] - ev[0]["start"]).total_seconds() / 86400, 1)
    weeks = span_days / 7
    per: dict[str, list[dict[str, Any]]] = {}
    for e in ev:
        per.setdefault(e["name"], []).append(e)
    table = []
    for name, es in per.items():
        durs = [(e["end"] - e["start"]).total_seconds() / 60 for e in es if e["end"] and e["end"] >= e["start"]]
        flaps = 0
        for a, b in zip(es, es[1:]):
            if a["end"] and (a["end"] - a["start"]) <= timedelta(minutes=5) and timedelta(0) <= (b["start"] - a["end"]) <= timedelta(minutes=30):
                flaps += 1
        acks = [e["acked"] for e in es if e["acked"] is not None]
        row = {"name": name, "count": len(es), "per_week": round(len(es) / weeks, 2),
               "median_min": round(median(durs), 1) if durs else None, "flaps": flaps,
               "acked_share": round(sum(acks) / len(acks), 3) if acks else None,
               "out_of_hours": sum(1 for e in es if e["out_of_hours"]), "nights": sum(1 for e in es if e["night"]),
               "severity": next((e["sev"] for e in es if e["sev"]), ""), "advice": []}
        if flaps >= 2:
            row["advice"].append("Flaps: fires and clears within minutes - add or raise `for`, or add hysteresis.")
        if durs and row["median_min"] is not None and row["median_min"] < 5 and len(es) >= 5:
            row["advice"].append("Clears by itself in under 5 minutes most times: nobody can act that fast - raise `for` or make it a ticket.")
        if acks and row["acked_share"] == 0 and len(es) >= 3:
            row["advice"].append("Never acknowledged: nobody acts on it - delete it or demote it to a ticket.")
        if row["per_week"] >= 10:
            row["advice"].append(f"{row['per_week']:g} a week: too many to read - fix the cause or the threshold.")
        table.append(row)
    table.sort(key=lambda r: (-r["count"], r["name"]))
    pages = [e for e in ev if e["sev"] in ("page", "critical", "crit", "p1", "sev1", "high", "emergency")] or ev
    oh = sum(1 for e in pages if e["out_of_hours"])
    nights = sum(1 for e in pages if e["night"])
    top = table[:3]
    top_share = sum(r["count"] for r in top) / len(ev)
    issues = []
    if len(pages) / weeks > 14:
        issues.append({"sev": "bad", "text": f"{len(pages) / weeks:.1f} pages a week: more than two a day wears out whoever is on call."})
    if top_share > 0.5 and len(table) > 3:
        issues.append({"sev": "warn", "text": f"Three alerts make {top_share:.0%} of all firings: fixing them removes most of the noise."})
    if nights:
        issues.append({"sev": "warn", "text": f"{nights} page(s) between 23:00 and 07:00 ({tz})."})
    by_week: dict[str, int] = {}
    for e in ev:
        k = (e["start"].astimezone(Z) - timedelta(days=e["start"].astimezone(Z).weekday())).date().isoformat()
        by_week[k] = by_week.get(k, 0) + 1
    hours = [0] * 24
    for e in ev:
        hours[e["start"].astimezone(Z).hour] += 1
    return {"ok": True, "alerts": len(ev), "distinct": len(table), "days": round(span_days, 1), "per_week": round(len(ev) / weeks, 2),
            "pages": len(pages), "pages_per_week": round(len(pages) / weeks, 2), "out_of_hours": oh, "nights": nights, "tz": tz,
            "table": table[:200], "issues": issues, "by_week": [{"week": k, "count": v} for k, v in sorted(by_week.items())][-60:],
            "by_hour": hours, "unreadable": bad_rows,
            "verdict": (f"{len(ev)} alerts over {span_days:.0f} days ({len(ev) / weeks:.1f} a week) from {len(table)} rules; "
                        f"{oh} of {len(pages)} pages out of hours. The noisiest: " + ", ".join(f"{r['name']} ({r['count']})" for r in top) + ".")}
