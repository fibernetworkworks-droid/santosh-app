"""Film Desk PRODUCTION layer: shooting schedule, day-out-of-days, call sheet and a rate-card budget, all in CODE.

Why code: a schedule is arithmetic and a rule set (group by location, day before night, cast availability, hours per day), so the
model never does it. Every number that is a guess is returned as an ASSUMPTION the owner can overwrite; nothing here invents a
rate, a contact or an address (unknown = a blank to fill). Pure functions, no database, no network, no model.

Register: docs/research/film_industry/00_INDEX.md  (#24 breakdown, #25 schedule optimiser, #26 day-out-of-days, #27 call sheet,
#13 line-producer budget). A person (1st AD, line producer) approves; nothing here sends or pays.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

# The defaults are ASSUMPTIONS, shown in every result as assumed=True so she overwrites them with her own numbers.
DEFAULTS = {"day_hours": 10.0, "setup_hours": 1.0, "hours_per_screen_minute": 2.0, "call_time": "07:00"}
MAX_DAYS = 400
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _num(v: Any, default: float, lo: float = 0.1, hi: float = 24.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return min(max(x, lo), hi)


def _day_part(sc: dict) -> str:
    """day | night. Scenes with no time are treated as day (the owner is told which ones)."""
    return "night" if (sc.get("time") or "") == "night" else "day"


def scene_hours(sc: dict, setup_hours: float, hours_per_screen_minute: float) -> float:
    """Shoot time for one scene = set-up + screen minutes x hours per screen minute (both HERS to change)."""
    minutes = max(int(sc.get("seconds") or 0), 1) / 60.0
    return round(setup_hours + minutes * hours_per_screen_minute, 2)


def _parse_day(v: Any) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _calendar(start: date | None, days_off: set[str], blocked: set[date], n: int):
    """Yield up to n working calendar dates from `start`, skipping weekly days off and blocked dates."""
    if start is None:
        return
    d, out = start, 0
    for _ in range(MAX_DAYS * 3):
        if _WEEKDAYS[d.weekday()] not in days_off and d not in blocked:
            yield d
            out += 1
            if out >= n:
                return
        d += timedelta(days=1)


def build_schedule(scenes: list[dict], *, start_date: str = "", day_hours: Any = None, setup_hours: Any = None,
                   hours_per_screen_minute: Any = None, days_off: Any = None, blocked_dates: Any = None,
                   unavailable: Any = None, call_time: str = "") -> dict[str, Any]:
    """Group scenes into shooting days.

    Rules (in order): one DAY-or-NIGHT bucket per shooting day; scenes at the same place shoot together; places keep their order
    of first appearance in the script; a day closes when the next scene would pass `day_hours`; a scene longer than a day gets its
    own day and is flagged. Dates (if a start date is given) skip weekly days off and blocked dates, and a day whose cast includes
    someone unavailable on that date is moved to a later date that suits (never silently dropped; if none fits it is listed as
    unscheduled)."""
    if not scenes:
        raise ValueError("Pehle script save karo: koi scene nahi mila.")
    dh = _num(day_hours, DEFAULTS["day_hours"], 1.0, 24.0)
    sh = _num(setup_hours, DEFAULTS["setup_hours"], 0.0, 12.0)
    hm = _num(hours_per_screen_minute, DEFAULTS["hours_per_screen_minute"], 0.1, 60.0)
    off = {str(x).strip().lower()[:3] for x in (days_off or []) if str(x).strip()} & set(_WEEKDAYS)
    blocked = {d for d in (_parse_day(x) for x in (blocked_dates or [])) if d}
    una: dict[str, set[date]] = {}
    for who, dates in (unavailable or {}).items() if isinstance(unavailable, dict) else []:
        ds = {d for d in (_parse_day(x) for x in (dates or [])) if d}
        if ds:
            una[str(who).strip().title()] = ds
    first_seen: dict[str, int] = {}
    for i, sc in enumerate(scenes):
        first_seen.setdefault((sc.get("place") or "").strip().lower() or "?", i)

    def group_key(sc: dict) -> tuple:
        place = (sc.get("place") or "").strip().lower() or "?"
        return (0 if _day_part(sc) == "day" else 1, first_seen[place], place)

    ordered = sorted(scenes, key=lambda sc: (group_key(sc), int(sc.get("n") or 0)))
    days: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    flags: list[str] = []
    for sc in ordered:
        hrs = scene_hours(sc, sh, hm)
        part = _day_part(sc)
        fits = cur is not None and cur["part"] == part and cur["hours"] + hrs <= dh
        if not fits:
            cur = {"part": part, "scenes": [], "hours": 0.0, "places": []}
            days.append(cur)
        cur["scenes"].append({"n": sc.get("n"), "id": sc.get("id"), "heading": sc.get("heading"), "int_ext": sc.get("int_ext", ""),
                              "place": sc.get("place", ""), "time": sc.get("time", ""), "seconds": sc.get("seconds"),
                              "hours": hrs, "characters": list(sc.get("characters") or [])})
        cur["hours"] = round(cur["hours"] + hrs, 2)
        pl = sc.get("place") or "?"
        if pl not in cur["places"]:
            cur["places"].append(pl)
        if hrs > dh:
            flags.append(f"Scene {sc.get('n')} ({hrs} ghante) ek din se lamba hai: do din me todna ya samay badalna.")
    for sc in scenes:
        if not (sc.get("time") or ""):
            flags.append(f"Scene {sc.get('n')} me din/raat likha nahi: din maana gaya.")
    for i, d in enumerate(days, 1):
        d["day"] = i
        d["moves"] = max(len(d["places"]) - 1, 0)
        d["cast"] = sorted({c for s in d["scenes"] for c in s["characters"]})
        d["screen_seconds"] = sum(int(s.get("seconds") or 0) for s in d["scenes"])
    unscheduled: list[int] = []
    if _parse_day(start_date):
        cal = list(_calendar(_parse_day(start_date), off, blocked, MAX_DAYS))
        left = list(range(len(days)))
        used = 0
        for dt in cal:
            if not left:
                break
            pick = next((i for i in left if not any(dt in una.get(c, ()) for c in days[i]["cast"])), None)
            if pick is None:
                continue
            days[pick]["date"] = dt.isoformat()
            left.remove(pick)
            used += 1
        unscheduled = [days[i]["day"] for i in left]
        for i in left:
            days[i]["date"] = ""
        if unscheduled:
            flags.append("Din " + ", ".join(str(x) for x in unscheduled) + ": cast ki uplabdhta ki wajah se tareekh nahi baith saki.")
        days.sort(key=lambda d: (d.get("date") or "9999", d["day"]))
        for i, d in enumerate(days, 1):
            d["order"] = i
    else:
        for i, d in enumerate(days, 1):
            d["date"] = ""
            d["order"] = i
    return {
        "days": days, "shoot_days": len(days), "night_days": sum(1 for d in days if d["part"] == "night"),
        "company_moves": sum(d["moves"] for d in days), "screen_seconds": sum(d["screen_seconds"] for d in days),
        "flags": flags, "unscheduled": unscheduled,
        "assumptions": {"day_hours": dh, "setup_hours": sh, "hours_per_screen_minute": hm, "assumed": True,
                        "call_time": call_time or DEFAULTS["call_time"], "days_off": sorted(off),
                        "blocked_dates": sorted(d.isoformat() for d in blocked),
                        "note": "Yeh ghante andaaze hain (ek din ka samay, set-up, har screen-minute par kitna). Apne asli number do."}}


def day_out_of_days(schedule: dict[str, Any]) -> dict[str, Any]:
    """Cast x shooting day grid. SW start-work, W work, WF work-finish, SWF single day, H hold (between first and last, not working).
    Hold days are shown, NOT priced: whether they are paid is in the contract."""
    days = schedule["days"]
    people: dict[str, list[int]] = {}
    for idx, d in enumerate(days):
        for c in d["cast"]:
            people.setdefault(c, []).append(idx)
    grid, summary = [], []
    for who in sorted(people, key=lambda w: (-len(people[w]), w)):
        idxs = people[who]
        first, last = idxs[0], idxs[-1]
        row = []
        for i in range(len(days)):
            if i not in idxs:
                row.append("H" if first < i < last else "")
            elif first == last:
                row.append("SWF")
            elif i == first:
                row.append("SW")
            elif i == last:
                row.append("WF")
            else:
                row.append("W")
        grid.append({"who": who, "cells": row})
        summary.append({"who": who, "work_days": len(idxs), "hold_days": sum(1 for x in row if x == "H"),
                        "first_day": days[first]["order"], "last_day": days[last]["order"]})
    return {"days": [{"order": d["order"], "date": d["date"]} for d in days], "grid": grid, "summary": summary,
            "note": "H = hold: kaam nahi par bandha hua. Hold din ka bhugtan contract par hai; yahan daam nahi lagaya."}


def call_sheet(project: dict[str, Any], day: dict[str, Any], *, call_time: str = "", cast_calls: Any = None,
               location_address: Any = None, contacts: Any = None, notes: str = "") -> dict[str, Any]:
    """One day's call sheet. Everything the owner did not give stays a BLANK in square brackets: we never make up an
    address, hospital, phone or weather."""
    ct = _clock(call_time) or DEFAULTS["call_time"]
    calls = {str(k).strip().title(): _clock(v) for k, v in (cast_calls or {}).items()} if isinstance(cast_calls, dict) else {}
    addr = {str(k).strip().lower(): str(v)[:200] for k, v in (location_address or {}).items()} if isinstance(location_address, dict) else {}
    ph = {str(k).strip().lower(): str(v)[:60] for k, v in (contacts or {}).items()} if isinstance(contacts, dict) else {}
    places = [{"place": p, "address": addr.get(p.lower(), "[pata bharo]")} for p in day.get("places", [])]
    cast = [{"who": c, "call": calls.get(c) or ct, "call_is_default": c not in calls,
             "scenes": [s["n"] for s in day["scenes"] if c in s["characters"]]} for c in day.get("cast", [])]
    scenes = [{"n": s["n"], "heading": s["heading"], "int_ext": s["int_ext"], "place": s["place"], "time": s["time"],
               "hours": s["hours"], "cast": s["characters"]} for s in day["scenes"]]
    blanks = ["[nazdiki aspatal / doctor bharo]", "[1st AD ka number bharo]", "[producer ka number bharo]"]
    contact_rows = [{"role": k.title(), "phone": v} for k, v in ph.items()]
    lines = [f"CALL SHEET - {project.get('title', '')}" + (f" ({project.get('number')})" if project.get("number") else ""),
             f"Shoot din {day.get('order')}" + (f" - {day['date']}" if day.get("date") else " - [tareekh bharo]"),
             f"Unit call: {ct}", ""]
    for p in places:
        lines.append(f"Jagah: {p['place']} - {p['address']}")
    lines.append("")
    for s in scenes:
        lines.append(f"Scene {s['n']}: {s['heading']} ({s['hours']} ghante) - {', '.join(s['cast']) or 'koi cast nahi'}")
    lines.append("")
    for c in cast:
        lines.append(f"{c['who']}: call {c['call']}" + (" (unit call hi)" if c["call_is_default"] else ""))
    lines.append("")
    lines += [f"{r['role']}: {r['phone']}" for r in contact_rows] or blanks
    if notes:
        lines += ["", f"Note: {notes[:400]}"]
    lines += ["", "Mausam, sunrise/sunset aur surakshit raasta yahan nahi bharte: asli source se dekhiye."]
    return {"day": day.get("order"), "date": day.get("date", ""), "unit_call": ct, "places": places, "scenes": scenes, "cast": cast,
            "contacts": contact_rows, "blanks": blanks if not contact_rows else [], "notes": notes[:400],
            "text": "\n".join(lines)}


def _clock(v: Any) -> str:
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})\s*$", str(v or ""))
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2))
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else ""


# ---------------------------------------------------------------- budget from HER rate card
_HEADS = [  # (key, label, unit, how the quantity is derived from the schedule)
    ("crew", "Crew (roz)", "din", "shoot_days"),
    ("cast", "Cast (kaam ke din)", "cast-din", "cast_days"),
    ("location", "Location kiraya", "din", "location_days"),
    ("equipment", "Camera / light / grip", "din", "shoot_days"),
    ("night_allowance", "Raat ka bhatta", "raat", "night_days"),
    ("transport", "Gaadi / company move", "move", "company_moves"),
    ("food", "Khana / chai", "din", "shoot_days"),
    ("post_per_screen_minute", "Post (edit, sound, colour)", "screen-minute", "screen_minutes"),
]


def budget_from_rates(schedule: dict[str, Any], dood: dict[str, Any], rates: Any, contingency_pct: Any = None) -> dict[str, Any]:
    """Quantities come from the schedule; rupees come ONLY from her rate card. A head with no rate is listed with
    'rate nahi di' and is left out of the total (so the total is always 'at least', never a guess)."""
    rates = rates if isinstance(rates, dict) else {}
    qty = {"shoot_days": schedule["shoot_days"],
           "cast_days": sum(r["work_days"] for r in dood["summary"]),
           "location_days": sum(len(d["places"]) for d in schedule["days"]),
           "night_days": schedule["night_days"], "company_moves": schedule["company_moves"],
           "screen_minutes": round(schedule["screen_seconds"] / 60.0, 1)}
    lines, total, missing = [], 0.0, []
    for key, label, unit, qkey in _HEADS:
        q = qty[qkey]
        try:
            rate = float(rates[key]) if key in rates and rates[key] not in (None, "") else None
        except (TypeError, ValueError):
            rate = None
        if rate is not None and rate < 0:
            rate = None
        amt = round(q * rate, 2) if rate is not None else None
        if amt is None:
            missing.append(label)
        else:
            total += amt
        lines.append({"key": key, "head": label, "unit": unit, "qty": q, "rate_inr": rate, "amount_inr": amt})
    extra = []
    for k, v in rates.items():
        if k in {h[0] for h in _HEADS} or not str(k).startswith("extra:"):
            continue
        try:
            amt = float(v)
        except (TypeError, ValueError):
            continue
        if amt >= 0:
            extra.append({"key": k, "head": str(k)[6:60], "unit": "ek baar", "qty": 1, "rate_inr": amt, "amount_inr": round(amt, 2)})
            total += amt
    try:
        cp = float(contingency_pct) if contingency_pct not in (None, "") else None
    except (TypeError, ValueError):
        cp = None
    cont = round(total * cp / 100.0, 2) if cp is not None and 0 <= cp <= 100 else None
    return {"lines": lines + extra, "subtotal_inr": round(total, 2), "contingency_pct": cp if cont is not None else None,
            "contingency_inr": cont, "total_inr": round(total + (cont or 0), 2), "missing_rates": missing,
            "quantities": qty,
            "note": ("Total sirf un heads ka hai jinki rate aapne di; baaki heads ke saamne 'rate nahi di'. Contingency tabhi judti hai "
                     "jab aap percent dein. Yeh andaaza hai, quote nahi."),
            "say": (f"Kam se kam ₹{round(total + (cont or 0)):,} ({schedule['shoot_days']} shoot din)"
                    + (f"; {len(missing)} head ki rate baaki." if missing else "."))}
