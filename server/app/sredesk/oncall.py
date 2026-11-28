"""On-call load, worked out in code.

A page history (CSV: time, who was paged, and the alert - plus when it was acknowledged and when it ended, if you have them) ->
per person: pages, pages a week, at night and on days off in HER time zone, the nights broken, the 12-hour shifts that had more
pages than her limit (the Google SRE book's rule of thumb is at most two incidents in a 12-hour shift), the time to acknowledge,
and how far each person is from an even share. A page history is data, never instructions."""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .alerts import MAX, MAX_ROWS, _t


def _col(head: list[str], *keys: str) -> int | None:
    """The column for any of these names: an exact name first, then a name inside a longer one - but never a short name (at, who)
    inside a longer word, so 'at' does not pick 'automate_hours'."""
    for k in keys:
        if k in head:
            return head.index(k)
    for k in keys:
        if len(k) < 4:
            continue
        for i, h in enumerate(head):
            if k in h:
                return i
    return None

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class OncallError(ValueError):
    pass


def _q(v: list[float], p: float) -> float | None:
    if not v:
        return None
    s = sorted(v)
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _is_night(h: int, start: int, end: int) -> bool:
    return (h >= start or h < end) if start > end else (start <= h < end)


def load(text: str, tz: str = "UTC", night_start: int = 22, night_end: int = 7, shift_max: int = 2,
         weekend: str = "sat,sun") -> dict[str, Any]:
    text = str(text or "")[:MAX * 3].strip()
    if not text:
        raise OncallError("Paste the page history first: time, who, alert (CSV).")
    try:
        Z = ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        raise OncallError("Time zone: an IANA name like Europe/London or Asia/Kolkata.")
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip().lower() for h in rows[0]]
    ti = _col(head, "time", "start", "startsat", "triggered", "created", "fired_at", "paged_at", "at")
    wi = _col(head, "who", "responder", "oncall", "on_call", "assignee", "assigned", "user", "person", "engineer")
    ni = _col(head, "alertname", "alert", "name", "title", "incident", "summary")
    ai = _col(head, "ack_at", "acknowledged_at", "acked_at", "ack_time", "ack")
    ami = _col(head, "ack_min", "ack_minutes", "minutes_to_ack", "tta")
    ei = _col(head, "end", "resolved_at", "resolved", "endsat")
    if ti is None or wi is None:
        raise OncallError("The CSV needs a time column and a who-was-paged column (who, responder, assignee, oncall).")
    off = {d.strip()[:3].lower() for d in str(weekend or "").split(",") if d.strip()}
    ev: list[dict[str, Any]] = []
    bad = 0
    for r in rows[1:MAX_ROWS + 1]:
        if len(r) <= max(ti, wi):
            continue
        at = _t(r[ti])
        who = r[wi].strip()[:80]
        if at is None or not who:
            bad += 1
            continue
        ack = None
        if ami is not None and len(r) > ami and r[ami].strip():
            try:
                ack = float(r[ami]) * 60
            except ValueError:
                ack = None
        elif ai is not None and len(r) > ai:
            a = _t(r[ai])
            if a is not None and a >= at:
                ack = (a - at).total_seconds()
        end = _t(r[ei]) if ei is not None and len(r) > ei else None
        loc = at.astimezone(Z)
        night = _is_night(loc.hour, night_start, night_end)
        # a night belongs to the evening it started: 02:00 on Tuesday is Monday's night
        night_of = (loc - timedelta(days=1)).date() if night and loc.hour < max(night_end, 12) and night_start > night_end else loc.date()
        shift = f"{loc.date().isoformat()} {'am' if loc.hour < 12 else 'pm'}"
        ev.append({"at": at, "who": who, "name": (r[ni].strip()[:120] if ni is not None and len(r) > ni else "") or "(no name)",
                   "ack": ack, "busy": (end - at).total_seconds() / 60 if end and end >= at else None, "night": night,
                   "night_of": night_of.isoformat(), "off": DAYS[loc.weekday()] in off, "shift": shift})
    if len(ev) < 2:
        raise OncallError("At least 2 pages with a readable time and a person are needed.")
    ev.sort(key=lambda e: e["at"])
    span = max((ev[-1]["at"] - ev[0]["at"]).total_seconds() / 86400, 1.0)
    weeks = span / 7
    people: dict[str, list[dict[str, Any]]] = {}
    for e in ev:
        people.setdefault(e["who"], []).append(e)
    even = len(ev) / len(people)
    table = []
    for who, es in people.items():
        shifts: dict[str, int] = {}
        for e in es:
            shifts[e["shift"]] = shifts.get(e["shift"], 0) + 1
        over = sorted(((k, v) for k, v in shifts.items() if v > shift_max), key=lambda x: (-x[1], x[0]))
        nights = sorted({e["night_of"] for e in es if e["night"]})
        acks = [e["ack"] / 60 for e in es if e["ack"] is not None]
        busy = sum(e["busy"] for e in es if e["busy"] is not None)
        streak = best = 0
        prev = None
        for n in nights:
            d = date.fromisoformat(n)
            streak = streak + 1 if prev is not None and (d - prev).days == 1 else 1
            best = max(best, streak)
            prev = d
        row = {"who": who, "pages": len(es), "per_week": round(len(es) / weeks, 2), "share": round(len(es) / len(ev), 3),
               "vs_even": round(len(es) / even, 2), "night_pages": sum(1 for e in es if e["night"]), "nights_broken": len(nights),
               "nights_in_a_row": best, "days_off": sum(1 for e in es if e["off"]), "shifts": len(shifts),
               "shifts_over": len(over), "worst_shift": ({"shift": over[0][0], "pages": over[0][1]} if over else None),
               "ack_median_min": round(median(acks), 1) if acks else None, "ack_p90_min": round(_q(acks, 0.9), 1) if acks else None,
               "busy_h": round(busy / 60, 1) if busy else None, "advice": []}
        if row["vs_even"] >= 1.5 and len(people) > 1:
            row["advice"].append(f"Takes {row['vs_even']:g}x an even share of the pages: look at the rota or what fires on their shifts.")
        if over:
            row["advice"].append(f"{len(over)} shift(s) over {shift_max} pages; the worst had {over[0][1]} ({over[0][0]}).")
        if best >= 3:
            row["advice"].append(f"Woken {best} nights in a row: give them the next day off or move the shift.")
        if acks and row["ack_p90_min"] is not None and row["ack_p90_min"] > 15:
            row["advice"].append(f"One page in ten took over {row['ack_p90_min']:g} min to acknowledge: check paging reaches them.")
        table.append(row)
    table.sort(key=lambda r: (-r["pages"], r["who"]))
    issues = []
    total_over = sum(r["shifts_over"] for r in table)
    total_shifts = sum(r["shifts"] for r in table)
    if total_over:
        issues.append({"sev": "bad" if total_over / max(total_shifts, 1) > 0.2 else "warn",
                       "text": f"{total_over} of {total_shifts} paged shifts had more than {shift_max} pages - more than one person can "
                               "handle well; fix the noisiest alerts first."})
    worst = max(table, key=lambda r: r["vs_even"])
    if len(table) > 1 and worst["vs_even"] >= 1.5:
        issues.append({"sev": "warn", "text": f"{worst['who']} takes {worst['vs_even']:g}x an even share of the pages."})
    nights = sum(r["night_pages"] for r in table)
    if nights:
        issues.append({"sev": "warn" if nights / len(ev) < 0.3 else "bad",
                       "text": f"{nights} of {len(ev)} pages ({nights / len(ev):.0%}) came at night ({night_start:02d}:00-{night_end:02d}:00 {tz})."})
    acks_all = [e["ack"] / 60 for e in ev if e["ack"] is not None]
    if len(table) == 1:
        issues.append({"sev": "warn", "text": "One person took every page: there is no one to hand over to."})
    weekly: dict[str, int] = {}
    for e in ev:
        loc = e["at"].astimezone(Z)
        k = (loc - timedelta(days=loc.weekday())).date().isoformat()
        weekly[k] = weekly.get(k, 0) + 1
    return {"ok": True, "pages": len(ev), "people": len(table), "days": round(span, 1), "per_week": round(len(ev) / weeks, 2),
            "night_pages": nights, "shifts_over": total_over, "shift_max": shift_max, "tz": tz,
            "night": f"{night_start:02d}:00-{night_end:02d}:00", "unreadable": bad,
            "ack_median_min": round(median(acks_all), 1) if acks_all else None,
            "ack_p90_min": round(_q(acks_all, 0.9), 1) if acks_all else None,
            "table": table[:100], "issues": issues, "by_week": [{"week": k, "count": v} for k, v in sorted(weekly.items())][-60:],
            "verdict": (f"{len(ev)} pages to {len(table)} people over {span:.1f} days ({len(ev) / weeks:.1f} a week); "
                        f"{nights} at night, {total_over} shift(s) over {shift_max} pages. Busiest: {table[0]['who']} ({table[0]['pages']}).")}
