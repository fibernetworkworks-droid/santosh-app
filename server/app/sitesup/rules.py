"""Site supervisor rules Hoola works to (researched 23 Oct 2026; sources in WIRING.md / CLAUDE.md). Pure functions, no DB.

Working hours (OSH Code 2020 s.25-27, in force 21 Nov 2025; OSH (Central) Rules 2026, G.S.R. 345(E) 8 May 2026): no worker more
than 48 hours a week; daily-wage workers get overtime beyond 8 hours a day, at TWICE the ordinary rate; 15-30 minutes of overtime
counts as half an hour, more than 30 minutes as a full hour. Spread-over / intervals are set by the appropriate (state) Government:
her settings, starter values only. Wages (amounts) are payroll's job (v0.94); here only the register NUMBERS.

Accidents (OSH Code s.10, OSH Central Rules 2026 r.7, Form XI): death = notify forthwith (Inspector-cum-Facilitator, DM / SDO,
police station, the family), bodily injury keeping the worker off work 48 hours or more = within 12 hours after those 48 hours,
dangerous occurrence (collapse of building / scaffolding / formwork / excavation, crane / hoist failure, fall from height, fire,
electrical flash...) with or without injury = within 12 hours. State rules may differ: her state's form / portal decides.

Concrete (IS 456:2000 cl. 13.5, 15, 16 + Table 11; IS 516 (Part 1 / Sec 1):2021): 150 mm cubes, 3 per sample, cured under water
27 +/- 2 C, tested at 7 days (indicative, ~65-70%) and 28 days (acceptance); PPC / PSC often 56 days by her QA plan. Samples per
day per grade by volume: 1-5 cum 1, 6-15 2, 16-30 3, 31-50 4, above 50 4 + 1 per extra 50 cum. Moist curing at least 7 days for
OPC, 10 days with mineral admixtures / blended cement or in hot dry weather. Acceptance limits differ between published summaries:
the defaults below follow IS 456:2000 Table 11 (with amendments) as commonly applied, and her project's QA plan / engineer decides.
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta

DAY_HOURS = 8.0
WEEK_HOURS = 48.0
OT_RATE = 2.0

NEVER = ("Material indent / purchase sirf aapki haan (card par tap) se; Hoola khud kuch nahi mangwata, na paise deta.",
         "Client ko DPR / message sirf aapki haan se jaata hai; Hoola apne aap kuch nahi bhejta.",
         "Kaam rokne ka order (stop-work) sirf aapke tap se; jaan ka khatra ho to turant logon ko door hatana pehle.",
         "Naap / progress / cube result jaisa bataya waisa hi likhta hai: badha-chadha kar nahi, gadh kar nahi.",
         "Mazdooron ki salary payroll ka kaam; yahan sirf hazri, ghante aur overtime ke numbers.",
         "Aadhaar / PAN sirf Pehchaan Locker ke {id:...} reference se; register mein number nahi.")

TRADES = {
    "mason": ("mason", "mistri", "raj mistri", "rajmistri", "gavandi", "मिस्त्री"),
    "helper": ("helper", "beldar", "majdoor", "mazdoor", "labour", "coolie", "hamal", "मजदूर"),
    "carpenter": ("carpenter", "sutar", "badhai", "shuttering", "formwork"),
    "bar_bender": ("bar bender", "barbender", "fitter", "steel fixer", "sariya", "saria"),
    "electrician": ("electrician", "wireman", "bijli"),
    "plumber": ("plumber", "nal"),
    "painter": ("painter", "rangari", "putty"),
    "welder": ("welder", "fabricator", "welding"),
    "tiler": ("tiler", "tile", "tiles", "flooring"),
    "operator": ("operator", "jcb", "mixer", "crane", "driver"),
    "supervisor": ("supervisor", "foreman", "munshi", "engineer"),
    "watchman": ("watchman", "guard", "chowkidar"),
}
TRADE_LABEL = {"mason": "Mason / mistri", "helper": "Helper / beldar", "carpenter": "Carpenter / shuttering", "bar_bender": "Bar bender",
               "electrician": "Electrician", "plumber": "Plumber", "painter": "Painter", "welder": "Welder", "tiler": "Tiler",
               "operator": "Operator", "supervisor": "Supervisor / foreman", "watchman": "Watchman", "other": "Other"}

# Delay reasons (words -> kind). by_client = hindrance on the client / department side (counts for an extension in theka).
DELAY_REASONS = {
    "rain": (("baarish", "barish", "rain", "paani bhar", "monsoon"), False),
    "material": (("material nahi", "cement nahi", "steel nahi", "sariya nahi", "ret nahi", "sand nahi", "maal nahi", "supply"), False),
    "labour": (("labour kam", "mazdoor kam", "mazdoor nahi", "labour nahi", "chhutti", "holiday"), False),
    "drawing": (("drawing", "design", "naksha", "revision", "approval"), True),
    "client": (("client", "department", "owner ne roka", "payment nahi", "site nahi mili", "encroach", "front nahi"), True),
    "power": (("light nahi", "bijli nahi", "power cut", "light gayi"), False),
    "equipment": (("mixer kharab", "machine kharab", "breakdown", "jcb nahi", "crane nahi"), False),
    "quality": (("cube fail", "rework", "tod", "dobara", "snag"), False),
    "safety": (("accident", "stop work", "safety", "hadsa"), False),
}

UNITS = {"bag": ("bag", "bags", "bori", "katta"), "cum": ("cum", "m3", "cu m", "cubic metre", "cubic meter", "ghan meter", "brass"),
         "kg": ("kg", "kilo"), "t": ("t", "ton", "tonne", "mt"), "nos": ("nos", "no", "pcs", "piece", "nag"), "sqm": ("sqm", "sq m", "m2"),
         "rmt": ("rmt", "rm", "running metre", "metre", "m"), "l": ("l", "litre", "liter"), "trip": ("trip", "trolley", "dumper", "truck")}

# Checklists: (id, question, critical). A critical "no" = an unsafe condition -> a stop-work suggestion card for HER tap.
CHECKLISTS: dict[str, dict] = {
    "ppe": {"label": "PPE (helmet, shoes, jacket)", "items": [
        ("helmet", "Sabke sar par helmet (chin strap ke saath)?", True),
        ("shoes", "Safety shoes / gum boots pehne hain?", False),
        ("jacket", "Reflective jacket (gaadi / machine ke paas)?", False),
        ("gloves", "Kaam ke hisaab se gloves / goggles / mask?", False),
        ("harness", "Unchai wale kaam par full body harness?", True)]},
    "height": {"label": "Unchai par kaam (2 m se upar)", "items": [
        ("edge", "Khule kinaron / slab edge par guard rail (top rail ~1 m + mid rail + toe board)?", True),
        ("openings", "Floor / shaft openings dhake ya ghere hue?", True),
        ("harness", "Harness double lanyard, mazboot anchor par bandha?", True),
        ("ladder", "Seedhi (ladder) bandhi hui, 1:4 dhalaan, upar 1 m nikli?", False),
        ("net", "Jahan rail nahi, wahan safety net?", False),
        ("permit", "Height work permit / supervisor ki nazar?", False)]},
    "scaffold": {"label": "Scaffolding", "items": [
        ("base", "Base plate + sole board, zameen pakki?", True),
        ("bracing", "Bracing / ties building se bandhe?", True),
        ("platform", "Platform poora phatta (boards) bichha, khisakta nahi?", True),
        ("rails", "Guard rail + toe board har working platform par?", True),
        ("access", "Chadhne ki seedhi / stair (frame par chadhna nahi)?", False),
        ("tag", "Inspection tag (pichhle 7 din mein / mausam ke baad jaancha)?", False),
        ("load", "Upar maal ka dher zyada nahi?", False)]},
    "excavation": {"label": "Khudai (excavation)", "items": [
        ("support", "1.5 m se gehri khudai mein shoring / dhalaan (slope)?", True),
        ("spoil", "Mitti ka dher aur gaadiyan kinare se door?", True),
        ("barrier", "Gadde ke chaaron taraf barrier / rassi / board?", True),
        ("access", "Utarne-chadhne ki seedhi?", False),
        ("water", "Paani nikaalne ka intezaam, kinare dhasak nahi rahe?", False),
        ("services", "Bijli / gas / paani ki line pehle dekh li?", True)]},
    "pour": {"label": "Concrete pour (formwork + steel)", "items": [
        ("props", "Props / staging seedhe, bracing, base mazboot?", True),
        ("form", "Shuttering joints band, oil laga, level / line theek?", False),
        ("steel", "Sariya drawing ke hisaab se (dia, spacing, laps) - engineer ne dekha?", False),
        ("cover", "Cover blocks lage?", False),
        ("cubes", "Cube moulds + slump cone site par?", False),
        ("vibrator", "Vibrator + standby?", False),
        ("curing", "Curing ka intezaam (paani / gunny)?", False)]},
    "electrical": {"label": "Site bijli", "items": [
        ("rccb", "Distribution board mein RCCB / ELCB?", True),
        ("wires", "Nange taar / zameen par pade joint nahi?", True),
        ("plugs", "Sahi plug-socket (taar seedhe ghusaye nahi)?", True),
        ("earthing", "Machines ki earthing?", False)]},
    "welfare": {"label": "Mazdooron ki suvidha", "items": [
        ("water", "Peene ka saaf paani?", False),
        ("toilet", "Toilet (mard / aurat alag)?", False),
        ("firstaid", "First aid box bhara hua + trained aadmi?", False),
        ("shelter", "Aaram / khane ki chhaanv (shelter)?", False),
        ("creche", "Bachche hon to creche / dekhbhaal (aapke rajya ke niyam)?", False)]},
}

TOOLBOX_TOPICS = ("Helmet aur chin strap", "Unchai par harness", "Scaffolding par chadhna-utarna", "Khudai ke kinare", "Bijli ke taar / RCCB",
                  "Machine ke paas reflective jacket", "Maal uthane ka sahi tareeka (kamar seedhi)", "Garmi mein paani aur chhaanv",
                  "Aag / fire extinguisher", "Cement / chemical se haath-aankh bachana", "Nashe mein kaam nahi", "Near-miss batana zaroori kyun")

INCIDENT_KINDS = {
    "near_miss": "Near-miss (bach gaye)",
    "first_aid": "First aid (chhoti chot)",
    "injury": "Chot (48 ghante ya zyada kaam se bahar)",
    "death": "Maut",
    "dangerous": "Dangerous occurrence (dhaancha / scaffold / formwork / khudai girna, crane, aag, bijli...)",
    "property": "Saamaan / machine ka nuksaan",
}
DANGEROUS_WORDS = ("scaffold", "formwork", "shuttering", "staging", "collapse", "gir gaya", "gir gayi", "dhah", "dhasak", "crane", "hoist",
                   "lift", "aag", "fire", "current", "shock", "electrocut", "khudai", "trench", "slab gir", "wall gir", "deewar gir")

STOP_TRIGGERS = ("helmet", "edge", "openings", "harness", "base", "bracing", "platform", "rails", "support", "spoil", "barrier", "services",
                 "props", "rccb", "wires", "plugs")


def low(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def trade_of(text: str) -> str:
    t = low(text)
    for k, words in TRADES.items():
        if t == k or any(re.search(rf"\b{re.escape(w)}\b", t) for w in words):
            return k
    return "other"


def unit_of(text: str) -> str:
    t = low(text).strip(". ")
    for k, words in UNITS.items():
        if t == k or t in words:
            return k
    return t[:12]


def delay_kind(text: str) -> tuple[str, bool]:
    t = low(text)
    if not t:
        return "", False
    for k, (words, by_client) in DELAY_REASONS.items():
        if any(w in t for w in words):
            return k, by_client
    return "other", False


def round_ot(hours: float) -> float:
    """OSH Central Rules 2026: overtime under 15 min = 0, 15-30 min = 0.5 h, more than 30 min = a full hour."""
    if hours <= 0:
        return 0.0
    whole = math.floor(hours + 1e-9)
    frac = hours - whole
    if frac < 0.25 - 1e-9:
        add = 0.0
    elif frac <= 0.5 + 1e-9:
        add = 0.5
    else:
        add = 1.0
    return whole + add


def split_hours(hours: float, day_limit: float = DAY_HOURS) -> dict:
    """One worker-day: normal hours and overtime (beyond the daily limit, rounded per the rule)."""
    h = max(0.0, float(hours or 0))
    normal = min(h, day_limit)
    return {"hours": round(h, 2), "normal": round(normal, 2), "ot": round_ot(h - day_limit)}


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def planned_pct(start: date, finish: date, on: date) -> float:
    if on < start:
        return 0.0
    if on >= finish:
        return 100.0
    total = max(1, (finish - start).days + 1)
    return round(((on - start).days + 1) * 100 / total, 1)


def activity_state(start: date | None, finish: date | None, on: date, done_pct: float, behind_limit: float = 10.0) -> dict:
    if not start or not finish:
        return {"planned_pct": None, "behind_pct": None, "state": "no_plan", "late_days": 0}
    pp = planned_pct(start, finish, on)
    behind = round(pp - done_pct, 1)
    late = (on - finish).days if done_pct < 100 and on > finish else 0
    if done_pct >= 100:
        st = "done"
    elif on < start:
        st = "not_started"
    elif late > 0:
        st = "late"
    elif behind > behind_limit:
        st = "behind"
    else:
        st = "on_track"
    return {"planned_pct": pp, "behind_pct": behind, "state": st, "late_days": max(0, late)}


# ---------------------------------------------------------------- concrete
def samples_for(volume_cum: float) -> int:
    """IS 456 cl. 15.2.2 frequency for one grade in one day."""
    v = max(0.0, float(volume_cum or 0))
    if v <= 5:
        return 1
    if v <= 15:
        return 2
    if v <= 30:
        return 3
    if v <= 50:
        return 4
    return 4 + math.ceil((v - 50) / 50)


def grade_fck(grade: str) -> float | None:
    m = re.search(r"m\s*-?\s*(\d{2,3})", low(grade))
    return float(m.group(1)) if m else None


def curing_days(cement: str, hot_dry: bool = False) -> int:
    c = low(cement)
    blended = any(w in c for w in ("ppc", "psc", "fly", "slag", "ggbs", "blended", "pozz"))
    return 10 if (blended or hot_dry) else 7


def cube_ages(cement: str, ages: list[int] | None = None) -> list[int]:
    if ages:
        return sorted({int(a) for a in ages if 1 <= int(a) <= 120})
    c = low(cement)
    return [7, 28] if not any(w in c for w in ("ppc", "psc", "slag", "ggbs")) else [7, 28, 56]


ASSUMED_SD = ((15, 3.5), (25, 4.0), (999, 5.0))


def assumed_sd(fck: float) -> float:
    for top, sd in ASSUMED_SD:
        if fck <= top:
            return sd
    return 5.0


def judge_cubes(grade: str, age: int, results: list[float], earlier_means: list[float] | None = None, limits: dict | None = None) -> dict:
    """One sample (usually 3 cubes) at one age. 7-day = indicative only. 28-day: individual vs fck - k and, when 4 consecutive
    sample means exist, their mean vs fck + max(0.825 sd, m). Limits are her QA plan's if given."""
    fck = grade_fck(grade)
    vals = [float(x) for x in results if x not in (None, "") and float(x) > 0]
    if not vals:
        return {"verdict": "no_result", "say": "Cube ka result (N/mm2) chahiye."}
    mean = round(sum(vals) / len(vals), 2)
    out = {"mean": mean, "results": vals, "fck": fck}
    if fck is None:
        return {**out, "verdict": "unknown", "say": f"Mean {mean} N/mm2; grade (M20 / M25...) bataiye to jaanch karun."}
    spread = (max(vals) - min(vals)) * 100 / mean if mean else 0
    note = f" 3 cube ka farq {spread:.0f}% (15% se zyada: testing / sampling dekhiye)." if len(vals) >= 3 and spread > 15 else ""
    if age < 28:
        exp = 0.65 * fck
        ok = mean >= exp
        return {**out, "verdict": "indicative_ok" if ok else "indicative_low", "expected": round(exp, 1),
                "say": (f"{age} din: mean {mean} N/mm2 (andaaza ~{exp:.1f}+). " + ("Theek chal raha." if ok else
                        "Kam lag raha: 28 din ka result aane tak dhyaan; engineer ko bataiye.") + note)}
    lim = dict(limits or {})
    k_ind = float(lim.get("individual_minus", 3.0 if fck <= 15 else 4.0))
    m_add = float(lim.get("mean_plus", 3.0 if fck <= 15 else 4.0))
    sd = float(lim.get("sd") or assumed_sd(fck))
    need_ind = fck - k_ind
    low_ones = [v for v in vals if v < need_ind]
    four = (list(earlier_means or [])[-3:] + [mean]) if earlier_means and len(earlier_means) >= 3 else None
    need_mean = round(fck + max(0.825 * sd, m_add), 2)
    group = round(sum(four) / 4, 2) if four else None
    fail = bool(low_ones) or (group is not None and group < need_mean)
    say = f"28 din {grade.upper()}: mean {mean} N/mm2."
    if low_ones:
        say += f" {len(low_ones)} cube {need_ind:g} se kam: FAIL ki nishani - engineer / QA plan (core test / load test) dekhe."
    if group is not None:
        say += f" Pichhle 4 sample ka mean {group} (chahiye {need_mean})" + (" - kam." if group < need_mean else " - theek.")
    if not fail:
        say += " Pass (Table 11 ke hisaab se; QA plan aakhri)."
    return {**out, "verdict": "fail" if fail else "pass", "need_individual": need_ind, "need_mean": need_mean, "group_mean": group,
            "say": say + note}


# ---------------------------------------------------------------- incidents
def incident_kind(kind: str, text: str) -> str:
    k = low(kind)
    if k in INCIDENT_KINDS:
        return k
    t = low(text)
    if any(w in t for w in ("maut", "death", "died", "mar gaya", "mar gayi", "expired", "dead")):
        return "death"
    if any(w in t for w in DANGEROUS_WORDS):
        return "dangerous"
    if any(w in t for w in ("hospital", "fracture", "haddi", "stitch", "tanke", "admit")):
        return "injury"
    if any(w in t for w in ("bal bal", "bach gaya", "bach gaye", "near miss", "near-miss", "gira par")):
        return "near_miss"
    return "first_aid" if t else "near_miss"


def report_due(kind: str, at, injury_off_since=None):
    """When the Form XI notice is due (None = no statutory notice). Returns (due datetime or None, plain words)."""
    if kind == "death":
        return at, "TURANT (forthwith): Inspector-cum-Facilitator, DM / SDO, police station aur parivaar ko; Form XI."
    if kind == "dangerous":
        return at + timedelta(hours=12), "12 ghante mein Form XI: Inspector-cum-Facilitator aur DM / SDO ko (chot na ho tab bhi)."
    if kind == "injury":
        base = injury_off_since or at
        return base + timedelta(hours=60), "Chot se 48 ghante kaam se bahar = uske 12 ghante ke andar Form XI (Inspector-cum-Facilitator)."
    return None, "Kanooni notice nahi; register mein likhna aur seekh lena zaroori."


def checklist_result(kind: str, answers: dict) -> dict:
    cl = CHECKLISTS.get(kind)
    if not cl:
        raise ValueError(f"Checklist '{kind}' nahi: " + ", ".join(CHECKLISTS))
    items = []
    for iid, q, critical in cl["items"]:
        raw = answers.get(iid)
        val = raw if isinstance(raw, bool) else (None if raw in (None, "", "na") else low(raw) in ("1", "true", "haan", "ha", "yes", "ok", "y"))
        items.append({"id": iid, "q": q, "critical": critical, "ok": val})
    failed = [i for i in items if i["ok"] is False]
    unsafe = [i for i in failed if i["critical"]]
    unanswered = [i for i in items if i["ok"] is None]
    score = round(sum(1 for i in items if i["ok"]) * 100 / len(items))
    return {"kind": kind, "label": cl["label"], "items": items, "failed": [i["id"] for i in failed], "unsafe": [i["id"] for i in unsafe],
            "unanswered": [i["id"] for i in unanswered], "score": score}
