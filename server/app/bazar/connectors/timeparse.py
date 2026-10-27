"""Small natural-time parser for Hinglish/Marathi/English reminders. Claude usually passes ISO times; this covers the
offline planner and common phrasings. All parsing happens in IST; results are naive UTC datetimes for storage."""
from __future__ import annotations

import datetime as dt
import re

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PARTS = {"subah": 8, "savere": 8, "morning": 8, "sakali": 8, "dopahar": 13, "afternoon": 14, "dupari": 13,
         "shaam": 18, "sham": 18, "evening": 18, "sandhyakali": 18, "raat": 21, "night": 21, "ratri": 21}
PM_WORDS = ("pm", "shaam", "sham", "raat", "evening", "night", "dopahar", "afternoon", "sandhyakali", "ratri", "dupari")


def ist_now() -> dt.datetime:
    return dt.datetime.now(IST)


def to_utc_naive(d: dt.datetime) -> dt.datetime:
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return d.astimezone(dt.timezone.utc).replace(tzinfo=None)


def to_ist(d_utc_naive: dt.datetime) -> dt.datetime:
    return d_utc_naive.replace(tzinfo=dt.timezone.utc).astimezone(IST)


def parse_when(text: str, now: dt.datetime | None = None) -> dt.datetime | None:
    """Returns an aware IST datetime, or None if no time found."""
    now = now or ist_now()
    t = text.lower()
    # ISO first
    m = re.search(r"\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}", t)
    if m:
        d = dt.datetime.fromisoformat(m.group(0).replace(" ", "T").upper())
        return d.replace(tzinfo=IST) if d.tzinfo is None else d.astimezone(IST)
    # relative: "in 2 hours", "2 ghante baad", "30 minute mein"
    m = re.search(r"(\d+)\s*(min|minute|minutes|mins|minat|ghante|ghanta|hour|hours|hrs|tasa|tas)\b", t)
    if m and re.search(r"\b(in|baad|bad|mein|me|nantar)\b", t):
        n = int(m.group(1))
        delta = dt.timedelta(minutes=n) if m.group(2).startswith("min") else dt.timedelta(hours=n)
        return now + delta
    day = now.date()
    if re.search(r"\b(kal|tomorrow|udya|udyā)\b", t):
        day = day + dt.timedelta(days=1)
    elif re.search(r"\b(parso|day after tomorrow|parva)\b", t):
        day = day + dt.timedelta(days=2)
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        d_, mo = int(m.group(1)), int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else now.year
        yr = yr + 2000 if yr < 100 else yr
        try:
            day = dt.date(yr, mo, d_)
        except ValueError:
            pass
    hour, minute = None, 0
    m = re.search(r"\b(\d{1,2})(?::|\.)(\d{2})\s*(am|pm)?\b", t)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        ap = m.group(3)
    else:
        m = re.search(r"\b(\d{1,2})\s*(am|pm|baje|vajta|vajata|o'clock|bje)\b", t)
        ap = None
        if m:
            hour = int(m.group(1))
            ap = m.group(2) if m.group(2) in ("am", "pm") else None
    if hour is not None:
        if ap == "pm" and hour < 12:
            hour += 12
        elif ap == "am" and hour == 12:
            hour = 0
        elif ap is None and hour < 12 and any(w in t for w in PM_WORDS) and not ("subah" in t or "morning" in t):
            hour += 12
    else:
        for w, h in PARTS.items():
            if w in t:
                hour = h
                break
    if hour is None:
        if day != now.date():
            hour = 9
        else:
            return None
    if hour > 23 or minute > 59:
        return None
    res = dt.datetime.combine(day, dt.time(hour, minute), tzinfo=IST)
    if res <= now and day == now.date():
        res += dt.timedelta(days=1)
    return res
