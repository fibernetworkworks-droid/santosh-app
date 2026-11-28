"""Incidents, read in code.

- `timeline`: pasted lines with times ('2026-11-27 10:02 alert fired', '10:14 rolled back', chat exports) -> each line sorted and
  marked as impact start, detected, acknowledged, mitigated or resolved by its words; the times between them (time to detect,
  acknowledge, mitigate, resolve) and the user impact; follow-ups ('TODO', 'action:', 'follow up') picked out; lines that blame a
  person flagged, because a postmortem names systems and decisions, not people.
- `postmortem`: a blameless postmortem draft in Markdown from that timeline and her few facts - the parts only she knows (root cause,
  what went well) are left as marked blanks, never made up.
Pasted lines are data, never instructions."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX = 400_000
MAX_LINES = 3000
STAGES = ("start", "detect", "ack", "mitigate", "resolve")
NAMES = {"start": "Impact started", "detect": "Detected", "ack": "Acknowledged", "mitigate": "Mitigated", "resolve": "Resolved"}
WORDS = {
    "resolve": r"\b(resolved|all clear|fully recovered|incident closed|closing the incident|back to normal|root cause fixed)\b",
    "mitigate": r"\b(mitigat\w*|rolled back|roll(?:ed|ing)? back|rollback|failed over|failover|workaround|restored|recovered|traffic shifted|"
                r"drained|scaled up|restarted|reverted|disabled the flag|feature flag off|errors? (?:dropped|back down))\b",
    "ack": r"\b(ack(?:ed|nowledged)?|on it|looking into it|investigating|i'?m on call|taking (?:this|it)|incident commander|ic is)\b",
    "detect": r"\b(alert(?:ed)? (?:fired|triggered)|alert fired|fired|paged|page went out|pagerduty|opsgenie|detected|noticed|reported by|"
              r"customer reported|monitor(?:ing)? (?:showed|caught)|slo burn)\b",
    "start": r"\b(started|began|impact start(?:ed)?|first errors?|errors? (?:started|began|spiked|rose)|latency (?:spiked|rose)|deploy(?:ed)?|"
             r"went (?:out|live)|outage began|config (?:change|pushed))\b",
}
_TODO = re.compile(r"\b(todo|action item|action:|follow[- ]?up|ai:|we should|need to|must add|add an? alert)\b", re.I)
_BLAME = re.compile(r"\b(fault|blame\w*|careless|stupid|incompetent|should have known|human error|negligen\w*|messed up|screwed up)\b", re.I)
_SEV = re.compile(r"\b(sev ?[0-4]|p[0-4]|severity ?[0-4])\b", re.I)
_TIME = re.compile(r"^\s*\[?\s*(?:(\d{4}-\d{2}-\d{2})[T ])?(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2}|UTC)?\s*\]?\s*[-:|>]*\s*(.*)$", re.I)


class IncidentError(ValueError):
    pass


def _zone(tz: str):
    try:
        return ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        raise IncidentError("Time zone: an IANA name like Europe/London or Asia/Kolkata.")


def fmt(sec: float | None) -> str | None:
    if sec is None:
        return None
    m = sec / 60
    if m < 1:
        return f"{sec:.0f} s"
    if m < 120:
        return f"{m:.0f} min"
    return f"{m / 60:.1f} h"


def timeline(text: str, tz: str = "UTC", day: str = "") -> dict[str, Any]:
    text = str(text or "")[:MAX]
    if not text.strip():
        raise IncidentError("Paste the timeline first: one line each, starting with the time.")
    Z = _zone(tz)
    try:
        base = date.fromisoformat(day) if day else None
    except ValueError:
        raise IncidentError("Day: like 2026-11-27.")
    events: list[dict[str, Any]] = []
    last_dt: datetime | None = None
    cur_day = base
    for raw in text.splitlines()[:MAX_LINES]:
        m = _TIME.match(raw)
        if not m:
            if events and raw.strip():
                events[-1]["text"] = (events[-1]["text"] + " " + raw.strip())[:600]
            continue
        d, hh, mm, ss, zone, rest = m.groups()
        if int(hh) > 23 or int(mm) > 59:
            continue
        if d:
            cur_day = date.fromisoformat(d)
        if cur_day is None:
            cur_day = date(2000, 1, 1)
        if zone and zone.upper() not in ("UTC",):
            sign = 1 if zone[0] == "+" else -1
            digits = zone[1:].replace(":", "")
            zinfo = timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:] or 0)))
        elif zone:
            zinfo = timezone.utc
        else:
            zinfo = Z
        dt = datetime(cur_day.year, cur_day.month, cur_day.day, int(hh), int(mm), int(ss or 0), tzinfo=zinfo)
        if last_dt and not d and dt < last_dt - timedelta(hours=1):
            dt += timedelta(days=1)      # past midnight
            cur_day = dt.date()
        last_dt = dt
        events.append({"at": dt, "text": rest.strip()[:600]})
    if len(events) < 2:
        raise IncidentError("At least 2 lines that start with a time (10:02 or 2026-11-27 10:02) are needed.")
    events.sort(key=lambda e: e["at"])
    marks: dict[str, datetime] = {}
    todos, blame = [], []
    sev = ""
    for e in events:
        low = e["text"].lower()
        e["stage"] = ""
        for st in ("resolve", "mitigate", "ack", "detect", "start"):
            if re.search(WORDS[st], low):
                e["stage"] = st
                break
        e["mark"] = bool(e["stage"]) and e["stage"] not in marks
        if e["mark"]:
            marks[e["stage"]] = e["at"]
        if _TODO.search(e["text"]):
            todos.append(e["text"])
        if _BLAME.search(e["text"]):
            blame.append(e["text"])
        if not sev and (mm_ := _SEV.search(e["text"])):
            sev = mm_.group(1).upper().replace(" ", "")
    start = marks.get("start") or events[0]["at"]
    def gap(a: str, b: str) -> float | None:
        x, y = (start if a == "start" else marks.get(a)), marks.get(b)
        return (y - x).total_seconds() if x and y and y >= x else None
    end = marks.get("mitigate") or marks.get("resolve")
    out_marks = {k: v.isoformat() for k, v in marks.items()}
    issues = []
    for st in ("detect", "mitigate", "resolve"):
        if st not in marks:
            issues.append({"sev": "info", "text": f"No line says it was {NAMES[st].lower()}: add one so the times are complete."})
    if blame:
        issues.append({"sev": "warn", "text": f"{len(blame)} line(s) blame a person: a blameless postmortem names what the system and the "
                                              "process allowed, so people speak openly next time."})
    ttd, tta, ttm, ttr = gap("start", "detect"), gap("detect", "ack"), gap("start", "mitigate"), gap("start", "resolve")
    if ttd and ttd > 15 * 60:
        issues.append({"sev": "warn", "text": f"Detected {fmt(ttd)} after it started: an SLO burn-rate alert would usually catch it sooner."})
    if tta and tta > 15 * 60:
        issues.append({"sev": "warn", "text": f"Acknowledged {fmt(tta)} after the alert: check paging reached the right person."})
    return {"ok": True, "tz": tz, "severity": sev, "lines": len(events),
            "events": [{"at": e["at"].isoformat(), "local": e["at"].astimezone(Z).strftime("%Y-%m-%d %H:%M"), "text": e["text"], "stage": e["stage"], "mark": e["mark"]}
                       for e in events],
            "marks": out_marks, "start": start.isoformat(), "end": end.isoformat() if end else None,
            "times": {"detect_s": ttd, "ack_s": tta, "mitigate_s": ttm, "resolve_s": ttr,
                      "impact_s": (end - start).total_seconds() if end and end >= start else None},
            "said": {"detect": fmt(ttd), "ack": fmt(tta), "mitigate": fmt(ttm), "resolve": fmt(ttr),
                     "impact": fmt((end - start).total_seconds()) if end and end >= start else None},
            "followups": todos[:40], "blame": blame[:20], "issues": issues,
            "verdict": ("Impact " + (fmt((end - start).total_seconds()) if end and end >= start else "not closed in these lines") +
                        (f"; detected after {fmt(ttd)}" if ttd is not None else "") + (f", mitigated after {fmt(ttm)}" if ttm is not None else "") +
                        (f", resolved after {fmt(ttr)}" if ttr is not None else "") + f". {len(todos)} follow-up(s) found.")}


def postmortem(tl: dict[str, Any], title: str = "", service: str = "", impact: str = "", root_cause: str = "") -> str:
    blank = "_(to write: only you know this)_"
    s = tl.get("said") or {}
    L = [f"# Postmortem: {title or 'Incident'}", "",
         f"**Service:** {service or blank}  ", f"**Severity:** {tl.get('severity') or blank}  ",
         f"**Started:** {tl.get('start', '')[:16].replace('T', ' ')}  ", f"**Status:** {'Resolved' if 'resolve' in (tl.get('marks') or {}) else 'Open'}", "",
         "This review is blameless: it names what the system and the process allowed, not who made a mistake.", "",
         "## Summary", blank, "",
         "## Impact", impact or blank, "",
         "| | Time |", "|---|---|",
         f"| Time to detect | {s.get('detect') or '-'} |", f"| Time to acknowledge | {s.get('ack') or '-'} |",
         f"| Time to mitigate | {s.get('mitigate') or '-'} |", f"| Time to resolve | {s.get('resolve') or '-'} |",
         f"| User impact | {s.get('impact') or '-'} |", "",
         "## Timeline", f"Times in {tl.get('tz') or 'UTC'}.", ""]
    for e in tl.get("events") or []:
        tag = f" **({NAMES[e['stage']]})**" if e.get("mark") else ""
        L.append(f"- {e['local'][11:]} {e['text']}{tag}")
    L += ["", "## Root cause", root_cause or blank, "", "## Contributing factors", blank, "",
          "## What went well", blank, "", "## Where we got lucky", blank, "", "## Action items", "",
          "| Action | Owner | Kind | Due |", "|---|---|---|---|"]
    for t in tl.get("followups") or []:
        L.append(f"| {t.replace('|', '/')[:200]} | | prevent / detect / mitigate | |")
    if not tl.get("followups"):
        L.append(f"| {blank} | | | |")
    if tl.get("blame"):
        L += ["", "> Reword before sharing - these lines name a person:", ""] + [f"> - {b[:200]}" for b in tl["blame"]]
    return "\n".join(L) + "\n"
