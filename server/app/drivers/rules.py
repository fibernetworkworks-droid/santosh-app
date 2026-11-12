"""Driver Sahayak rules: the law's limits on drivers' hours, licence classes, document windows, and the plain-text
readers for trip sheets ("start 45210 end 45480, diesel 40 L 3,800, toll 450"). Pure functions, no database.

Hours (India, checked 23 Oct 2026):
  * Motor Vehicles Act 1988 s.91: hours of work of a person operating a transport vehicle follow the Motor Transport
    Workers Act 1961 (now subsumed in the OSH Code 2020).
  * OSH Code 2020 (in force 21 Nov 2025; s.143 repeals the MTW Act) s.25: 8 hours a day; for motor transport workers the
    hours include running time, subsidiary work (loading, checks) and terminal attendance under 15 minutes. OSH Central
    Rules 2026 (G.S.R. 345(E), 8 May 2026) Rule 64: 48 hours a week. Spread-over / rest intervals are left to the
    appropriate (state) Government: the MTW Act values (spread-over 12 h, 30 min rest after 5 h, 9 h rest between duties,
    10 h a day only on notified long-distance routes) are used as starters, clearly labelled.
  * Overtime = beyond 8 h a day or 48 h a week, double wages (Code s.27, Rule 69), with the worker's consent.
  * Weekly rest: max 6 working days a week; a rest day worked must be given within the next 10 days (Code).
Licence:
  * Transport licence valid 5 years (MV Act s.14 as amended 2019); dangerous / hazardous goods 3 years; renewal can be
    applied up to 1 year before expiry (s.15). Driving after expiry = no valid licence (s.3 / s.181, Rs 5,000).
  * Medical certificate (Form 1A, CMV Rules) for transport licences.
  * Supreme Court, Bajaj Allianz v Rambha Devi (6 Nov 2024): an LMV licence covers transport vehicles of gross vehicle
    weight up to 7,500 kg; heavier ones need the medium / heavy goods or passenger class.
  * Dangerous / hazardous goods: driver needs the hazardous-goods training endorsement (CMV Rules r.9).
Police verification has no single legal expiry for goods drivers (aggregator / school-bus / state rules differ): the
recheck period is her setting (starter 24 months).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

# ---------------------------------------------------------------- law (starters she can make stricter, never looser)
LAW = {
    "day_h": 8.0,            # OSH Code s.25(1)(a)
    "week_h": 48.0,          # OSH Central Rules 2026 r.64(1)
    "spread_h": 12.0,        # MTW Act value (state rules decide): starter
    "rest_after_h": 5.0,     # MTW Act: 30 min rest after 5 h work: starter
    "rest_min": 30,
    "between_h": 9.0,        # MTW Act: 9 h rest between duties: starter
    "days_row": 6,           # OSH Code: max 6 working days a week
}
LAW_NOTE = {
    "day_h": "OSH Code 2020 s.25: 8 hours a day (driving + loading / checking + short waits at the terminal).",
    "week_h": "OSH Central Rules 2026 r.64: 48 hours a week.",
    "spread_h": "Spread-over 12 hours (old MTW Act rule; now check the state rule).",
    "rest_after_h": "At least 30 minutes rest after 5 hours of work (MTW Act; check the state rule).",
    "between_h": "At least 9 hours continuous rest between two duties (MTW Act; check the state rule).",
    "days_row": "No more than 6 working days a week; if a rest day is worked, give a day off within the next 10 days (OSH Code).",
    "ot": "Over 8 hours / day or 48 / week = overtime, double pay, only with the driver's consent (OSH Code s.27).",
}

SOURCES = [
    ("Motor Vehicles Act 1988 s.91 (hours of drivers -> MTW Act / OSH Code)", "indiacode.nic.in", "checked 2026-10-23"),
    ("Motor Transport Workers Act 1961 hours (8 h, 48 h, spread-over 12 h, 30 min after 5 h, 9 h rest)", "https://factohr.com/?p=48986", "2026-10-23"),
    ("OSH Central Rules 2026 Rule 64 (48 h/week, G.S.R. 345(E) 8 May 2026; Code in force 21 Nov 2025)",
     "https://www.taxclue.in/blog/rule-64-osh-central-rules-2026-working-hours/", "2026-10-23"),
    ("Licence renewal: transport licence 5 years, renew 1 year before (MV Act s.14 / s.15)",
     "https://advocategandhi.com/renewal-of-driving-license-a-complete-legal-guide-for-motorists-in-india/", "2026-10-23"),
    ("Supreme Court, Bajaj Allianz v Rambha Devi, 6 Nov 2024: LMV licence covers transport vehicles up to 7,500 kg",
     "https://www.scobserver.in/cases/validity-of-light-motor-vehicle-licence-to-drive-transport-vehicle-bajaj-allianz-general-insurance-v-rambha-devi/",
     "2026-10-23"),
    ("Motor Vehicle Aggregator Guidelines 2025 (1 Jul 2025): driver checks, 40 h induction training, Rs 5 lakh cover",
     "https://www.scconline.com/blog/?p=352371", "2026-10-23"),
]

NEVER = (
    "Hoola never pays money / advances to a driver: that is your or payroll's job.",
    "Hoola never messages a driver by itself: you send the draft, or it goes by your tap over business WhatsApp / Hoola Network.",
    "The full licence number never enters Hoola's memory: it is locked in the ID Locker; only the last 4 digits are shown.",
    "No duty for a driver after the licence expires: driving without a valid licence is an offence under MV Act s.3 / s.181.",
    "Never two duties for one driver at once, or one vehicle for two drivers at once.",
)

# ---------------------------------------------------------------- licence classes
CLASSES = {
    "mcwg": "Motorcycle with gear", "lmv": "LMV (car / jeep / small tempo)", "lmv_tr": "LMV transport",
    "mgv": "Medium goods (MGV)", "hgv": "Heavy goods (HGV)", "htv": "Heavy transport (HTV / HPMV)",
    "mpv": "Medium passenger", "hpv": "Heavy passenger (bus)", "trans": "Transport (TRANS)", "erik": "E-rickshaw",
    "hazardous": "Hazardous goods endorsement",
}
CLASS_WORDS = {
    "mcwg": ("mcwg", "bike", "motorcycle"), "lmv": ("lmv", "car", "light motor"), "lmv_tr": ("lmv-tr", "lmv tr", "lmvtr"),
    "mgv": ("mgv", "medium goods"), "hgv": ("hgv", "heavy goods", "truck"), "htv": ("htv", "hpmv", "heavy transport", "trailer"),
    "mpv": ("mpv",), "hpv": ("hpv", "bus", "heavy passenger"), "trans": ("trans", "transport", "badge"),
    "erik": ("e-rickshaw", "erik", "e rickshaw"), "hazardous": ("hazardous", "hazard", "khatarnak", "chemical", "gas tanker"),
}
HEAVY = {"mgv", "hgv", "htv", "trans", "mpv", "hpv"}

DOCS = {      # what expires on a driver: label
    "dl": "Driving licence", "medical": "Medical certificate (Form 1A)", "badge": "Badge / PSV",
    "police": "Police verification", "hazardous": "Hazardous goods training",
}
WINDOWS = (30, 15, 7, 1, 0)


def classes_of(text: Any) -> list[str]:
    if isinstance(text, (list, tuple)):
        text = " ".join(str(x) for x in text)
    t = f" {str(text or '').lower()} "
    out = []
    for k, words in CLASS_WORDS.items():
        if k in out:
            continue
        for w in words:
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t):
                out.append(k)
                break
    if "lmv_tr" in out and "lmv" in out and not re.search(r"(?<![a-z-])lmv(?![a-z-]|\s*tr)", t):
        out.remove("lmv")
    return out


def licence_ok_for(classes: list[str], gvw_kg: float | None, kind: str = "", hazardous: bool = False) -> list[str]:
    """Problems with this licence for this vehicle ([] = fine / not known)."""
    cl = set(classes or [])
    out = []
    if not cl:
        return ["Licence class not recorded (LMV / HGV ...); could not check."]
    if gvw_kg and gvw_kg > 7500 and not (cl & {"mgv", "hgv", "htv", "trans"}):
        out.append(f"Vehicle {gvw_kg:g} kg (heavier than 7,500 kg): an LMV licence is not enough, MGV / HGV / transport class is needed "
                   "(Supreme Court, Rambha Devi, Nov 2024).")
    if kind in ("bus", "passenger") and gvw_kg and gvw_kg > 7500 and not (cl & {"hpv", "mpv", "trans"}):
        out.append("A large bus needs a passenger / transport class.")
    if hazardous and "hazardous" not in cl:
        out.append("Hazardous goods: the driver needs hazardous goods training (endorsement) (CMV Rules r.9).")
    return out


DL_RE = re.compile(r"\b([A-Z]{2})[ -]?(\d{2})[ -]?((?:19|20)\d{2})[ -]?(\d{7})\b")
DL_LOOSE = re.compile(r"\b([A-Z]{2}[ -]?\d{2}[ -]?\d{9,11})\b")


def dl_clean(v: str) -> str:
    return re.sub(r"[\s-]", "", str(v or "")).upper()


def dl_valid(v: str) -> bool:
    v = dl_clean(v)
    return bool(re.fullmatch(r"[A-Z]{2}\d{2}(?:19|20)?\d{2}\d{7}", v)) or bool(re.fullmatch(r"[A-Z]{2}\d{11,14}", v))


def mask_ids(text: str) -> str:
    """Licence-looking numbers (and 10-digit phones) in OCR / message text -> masked, so the model never reads them."""
    t = DL_LOOSE.sub(lambda m: "XXXXXXXXXX" + dl_clean(m.group(1))[-4:], str(text or ""))
    return re.sub(r"(?<!\d)([6-9]\d{9})(?!\d)", lambda m: "XXXXXX" + m.group(1)[-4:], t)


# ---------------------------------------------------------------- time helpers
def hm(v: Any) -> str:
    """'6', '6 baje', '6:30 pm', '18:30', 'subah 6', 'shaam 7' -> 'HH:MM' ('' when unknown)."""
    s = str(v or "").strip().lower()
    if not s:
        return ""
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|baje|bje)?", s)
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    ap = m.group(3) or ""
    if ap == "pm" or re.search(r"\b(shaam|sham|raat|dopahar|dopeher|evening|night)\b", s):
        if h < 12 and not (re.search(r"\braat\b", s) and h <= 4):
            h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return ""
    return f"{h:02d}:{mi:02d}"


def at(day: date, t: str) -> datetime:
    h, m = (int(x) for x in t.split(":"))
    return datetime(day.year, day.month, day.day, h, m)


def span(day: date, start: str, end: str) -> tuple[datetime, datetime]:
    a, b = at(day, start), at(day, end)
    if b <= a:
        b += timedelta(days=1)            # ends after midnight
    return a, b


def hours(a: datetime, b: datetime) -> float:
    return round((b - a).total_seconds() / 3600, 2)


# ---------------------------------------------------------------- duty check (pure: the service passes the facts)
def limits(her: dict | None) -> dict:
    """Her rules, but never looser than the law's values (a looser one is ignored and said)."""
    out = dict(LAW)
    h = her or {}
    for k in ("day_h", "week_h", "spread_h", "between_h"):
        v = h.get(k)
        if isinstance(v, (int, float)) and v > 0:
            if k == "between_h":
                out[k] = max(out[k], float(v))
            else:
                out[k] = min(out[k], float(v))
    v = h.get("days_row")
    if isinstance(v, (int, float)) and v > 0:
        out["days_row"] = min(out["days_row"], int(v))
    return out


def check_duty(duty: dict, others: list[dict], driver: dict, leave_days: set[date], her: dict | None = None,
               vehicle_busy: list[dict] | None = None, vehicle: dict | None = None) -> dict:
    """duty {day: date, start 'HH:MM', end 'HH:MM', break_min, hazardous}; others = the driver's other duties
    [{day, start, end, break_min, id}]. -> {block: [...], law: [...], warn: [...], work_h, spread_h, ot_h}"""
    lim = limits(her)
    block: list[str] = []
    law: list[str] = []
    warn: list[str] = []
    d = duty["day"]
    a, b = span(d, duty["start"], duty["end"])
    spread = hours(a, b)
    brk = max(0, int(duty.get("break_min") or 0))
    work = round(max(0.0, spread - brk / 60), 2)
    if not driver.get("active", True):
        block.append(f"{driver.get('name')} no longer works here (left).")
    if d in leave_days:
        block.append(f"{driver.get('name')} is on leave that day.")
    exp = driver.get("dl_valid_to")
    if not exp:
        warn.append("Licence expiry date not recorded: check it.")
    elif exp < b.date():
        block.append(f"Licence {exp:%d-%m-%Y} has expired: no duty without a valid licence (MV Act s.3 / s.181).")
    med = driver.get("medical_valid_to")
    if med and med < d:
        law.append(f"Medical certificate {med:%d-%m-%Y} expired (Form 1A for a transport licence).")
    if vehicle is not None:
        for p in licence_ok_for(driver.get("classes") or [], vehicle.get("gvw_kg"), vehicle.get("kind", ""), bool(duty.get("hazardous"))):
            (block if "7,500" in p or "hazardous" in p.lower() else warn).append(p)
    elif duty.get("hazardous") and "hazardous" not in (driver.get("classes") or []):
        block.append("Hazardous goods: the driver needs hazardous goods training (endorsement) (CMV Rules r.9).")
    # overlaps
    spans = []
    for o in others:
        if o.get("id") and o.get("id") == duty.get("id"):
            continue
        oa, ob = span(o["day"], o["start"], o["end"])
        spans.append((oa, ob, o))
        if oa < b and a < ob:
            block.append(f"The driver has another duty at the same time ({o['day']:%d-%m} {o['start']}-{o['end']}).")
    for v in vehicle_busy or []:
        va, vb = span(v["day"], v["start"], v["end"])
        if va < b and a < vb:
            block.append(f"Vehicle {v.get('vehicle')} at the same time is with {v.get('driver_name') or 'another driver'}.")
    # the same day's other duties count together (split duty): one spread-over, one day's hours
    same = [x for x in spans if x[2]["day"] == d]
    day_a = min([a] + [x[0] for x in same])
    day_b = max([b] + [x[1] for x in same])
    day_spread = hours(day_a, day_b)
    day_work = round(work + sum(max(0.0, hours(x[0], x[1]) - int(x[2].get("break_min") or 0) / 60) for x in same), 2)
    if day_spread > lim["spread_h"]:
        law.append(f"Duty {day_spread:g} hours spread (more than the spread-over of {lim['spread_h']:g}). {LAW_NOTE['spread_h']}")
    if day_work > lim["day_h"]:
        law.append(f"Work that day {day_work:g} hours: {round(day_work - lim['day_h'], 2):g} hours overtime over {lim['day_h']:g}. {LAW_NOTE['ot']}")
    if work > lim["rest_after_h"] and brk < LAW["rest_min"]:
        warn.append(f"After {lim['rest_after_h']:g} hours give {LAW['rest_min']} minutes rest (write the break in the duty).")
    # rest between duties on different days
    prev = [x for x in spans if x[1] <= a and x[2]["day"] != d]
    nxt = [x for x in spans if x[0] >= b and x[2]["day"] != d]
    if prev:
        pe = max(x[1] for x in prev)
        gap = hours(pe, day_a)
        if gap < lim["between_h"]:
            law.append(f"Only {gap:g} hours rest after the last duty (at least {lim['between_h']:g}). {LAW_NOTE['between_h']}")
    if nxt:
        ns = min(x[0] for x in nxt)
        gap = hours(day_b, ns)
        if gap < lim["between_h"]:
            law.append(f"Only {gap:g} hours rest between this duty and the next (at least {lim['between_h']:g}).")
    # week (Mon-Sun) hours
    wk0 = d - timedelta(days=d.weekday())
    wk = [x for x in spans if wk0 <= x[2]["day"] < wk0 + timedelta(days=7)]
    week_h = round(work + sum(max(0.0, hours(x[0], x[1]) - int(x[2].get("break_min") or 0) / 60) for x in wk), 2)
    if week_h > lim["week_h"]:
        law.append(f"This week will reach {week_h:g} hours (more than {lim['week_h']:g}). {LAW_NOTE['week_h']}")
    # days in a row
    days = {x[2]["day"] for x in spans} | {d}
    run, k = 1, d - timedelta(days=1)
    while k in days:
        run, k = run + 1, k - timedelta(days=1)
    k = d + timedelta(days=1)
    while k in days:
        run, k = run + 1, k + timedelta(days=1)
    if run > lim["days_row"]:
        law.append(f"{run} days of duty in a row (no day off). {LAW_NOTE['days_row']}")
    ot = round(max(0.0, day_work - lim["day_h"]), 2)
    return {"block": block, "law": law, "warn": warn, "work_h": work, "spread_h": spread, "day_h": day_work, "ot_h": ot, "week_h": week_h,
            "ok": not block and not law}


# ---------------------------------------------------------------- trip sheet reader
_NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _n(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def parse_sheet(text: str) -> dict[str, Any]:
    """Pull what is really written: start / end km, times, fuel litres + amount, tolls, other expenses, from / to.
    Nothing is guessed: a field not found stays out."""
    t = " " + re.sub(r"[ \t]+", " ", str(text or "")).lower() + " "
    out: dict[str, Any] = {}
    m = re.search(rf"(?:km|kms|meter|reading|odometer)\s*[:\-]?\s*{_NUM}\s*(?:-|to|se|–)\s*{_NUM}", t)
    if m:
        out["start_km"], out["end_km"] = _n(m.group(1)), _n(m.group(2))
    else:
        m1 = re.search(rf"(?:start|opening|shuru|shuruaat|nikalte|open)\w*\s*(?:km|kms|reading|meter)?\s*[:\-]?\s*{_NUM}", t)
        m2 = re.search(rf"(?:end|closing|band|khatam|aakhir|close|wapas)\w*\s*(?:km|kms|reading|meter)?\s*[:\-]?\s*{_NUM}", t)
        if m1 and _n(m1.group(1)) and _n(m1.group(1)) > 50:
            out["start_km"] = _n(m1.group(1))
        if m2 and _n(m2.group(1)) and _n(m2.group(1)) > 50:
            out["end_km"] = _n(m2.group(1))
    times = []
    for m in re.finditer(r"(?:\b(subah|sawere|savere|dopahar|dopeher|shaam|sham|raat)\s*)?(?<![\d,.])(\d{1,2})(?:([:.])(\d{2}))?\s*(am|pm|baje|bje)?(?![\d,])", t):
        if not (m.group(3) or m.group(5)):
            continue
        if m.group(3) == "." and not m.group(5):
            continue
        v = hm(f"{m.group(1) or ''} {m.group(2)}:{m.group(4) or '00'} {m.group(5) or ''}")
        if v:
            times.append(v)
    if len(times) >= 2:
        out["start_time"], out["end_time"] = times[0], times[1]
    fm = re.search(rf"(?:diesel|petrol|fuel|cng|tel|deezal|dijal)\s*[:\-]?\s*{_NUM}\s*(?:l|ltr|litre|liter|lit|kg)\b", t) or \
        re.search(rf"{_NUM}\s*(?:l|ltr|litre|liter|lit)\b\s*(?:diesel|petrol|fuel|tel)", t)
    if fm:
        out["fuel_l"] = _n(fm.group(1))
    fa = re.search(rf"(?:diesel|petrol|fuel|cng|tel)[^.\n,]*?(?:rs\.?|₹|rupaye|rupees|rs)\s*{_NUM}", t) or \
        re.search(rf"(?:diesel|petrol|fuel|cng|tel)[^.\n]*?\b(?:l|ltr|litre|liter|lit|kg)\b\s*[:\-]?\s*(?:rs\.?|₹)?\s*{_NUM}", t)
    if fa:
        out["fuel_amount"] = _n(fa.group(1))
    tl = re.search(rf"(?:toll|tol|fastag)\s*[:\-]?\s*(?:rs\.?|₹)?\s*{_NUM}", t)
    if tl:
        out["tolls"] = _n(tl.group(1))
    ex = []
    for word, label in (("parking", "Parking"), ("khana|food|meal|bhatta", "Food / allowance"), ("puncture|tyre|tayar", "Puncture / tyre"),
                        ("loading|hamali|unloading", "Loading / hamali"), ("police|challan", "Challan"), ("repair|mistri", "Repair")):
        m = re.search(rf"(?:{word})\w*\s*[:\-]?\s*(?:rs\.?|₹)?\s*{_NUM}", t)
        if m and _n(m.group(1)):
            ex.append({"what": label, "amount": _n(m.group(1))})
    if ex:
        out["expenses"] = ex
    rt = re.search(r"\b([a-z][a-z ]{2,30}?)\s+(?:se|to)\s+([a-z][a-z ]{2,30}?)\s+(?:tak|gaya|gayi|gaye|trip|route|\.|,|$)", t)
    if rt and not re.search(r"\d", rt.group(0)) and rt.group(1).strip() not in ("subah", "shaam", "raat"):
        out["route"] = f"{rt.group(1).strip().title()} - {rt.group(2).strip().title()}"
    return out


def check_trip(trip: dict, prev_end_km: float | None, kmpl_ref: float | None, her: dict | None = None,
               tolerance: float = 0.2) -> list[dict]:
    """Flags on one trip sheet: [{kind, say, level}]. Numbers only from the sheet / her history; never invented."""
    f: list[dict] = []
    s, e = trip.get("start_km"), trip.get("end_km")
    if s is None or e is None:
        f.append({"kind": "km_missing", "level": "warn", "say": "Start / end km not written."})
    else:
        if e < s:
            f.append({"kind": "km_back", "level": "bad", "say": f"End km ({e:g}) is less than start ({s:g}): written wrongly."})
        elif e - s > 1200:
            f.append({"kind": "km_big", "level": "warn", "say": f"One trip of {e - s:g} km: is that right? Check the meter."})
        if prev_end_km is not None and abs(s - prev_end_km) > 1:
            gap = s - prev_end_km
            f.append({"kind": "km_gap", "level": "bad" if gap > 0 else "warn",
                      "say": (f"The last trip ended at {prev_end_km:g}, this one starts at {s:g}: the {gap:g} km in between are on no sheet."
                              if gap > 0 else f"This trip starts at {s:g}, the last one ended at {prev_end_km:g}: how did the meter go back?")})
    km = (e - s) if (s is not None and e is not None and e >= s) else None
    fl = trip.get("fuel_l")
    if km and fl and kmpl_ref:
        kmpl = km / fl if fl else 0
        if kmpl and abs(kmpl - kmpl_ref) / kmpl_ref > tolerance:
            lo = kmpl < kmpl_ref
            f.append({"kind": "fuel_odd", "level": "warn",
                      "say": (f"This trip: {kmpl:.1f} km / litre; this vehicle's usual is {kmpl_ref:.1f}. "
                              + ("More fuel used: was the tank filled? leak / theft / long idling? Match with the bill and FASTag / GPS."
                                 if lo else "Less fuel shown: was the tank filled last time? Match the bill."))})
    a, b = trip.get("start_time"), trip.get("end_time")
    if a and b and trip.get("day"):
        x, y = span(trip["day"], a, b)
        h = hours(x, y)
        lim = limits(her)
        if h > lim["day_h"]:
            f.append({"kind": "overtime", "level": "info", "say": f"Trip {h:g} hours: {h - lim['day_h']:g} hours overtime (goes to payroll)."})
        if h > lim["spread_h"]:
            f.append({"kind": "spread", "level": "warn", "say": f"Trip {h:g} ghante lambi: {LAW_NOTE['spread_h']}"})
    return f


def window_hit(days_left: int) -> int | None:
    """Which reminder window applies today (the tightest), None when none."""
    if days_left < 0:
        return -1
    for w in sorted(WINDOWS):
        if days_left <= w:
            return w
    return None
