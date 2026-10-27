"""Fleet Sahayak rules: pure functions (no DB). Registration numbers, document kinds with validity / reminder windows (CMVR,
National Permit, fitness by age + ATS, PUC, insurance, AIS-140), fuel efficiency (tank-to-tank) + outliers, service due by km /
months, load fit (weight + volume + body size), trip estimates ONLY from her own rates. Starter numbers are labelled starters.

Sources (checked 23 Oct 2026) are in SOURCES; nothing here is legal advice, her RTO / maker's manual decides."""
from __future__ import annotations

import re
import statistics
from datetime import date, timedelta
from typing import Any

# ---------------------------------------------------------------- what Hoola never does
NEVER = (
    "Challan, permit fee, road tax, insurance, FASTag recharge, service ya tyre ka paisa khud kabhi nahi deta / kharidta: har kharcha aapke tap ka card hai, paise aap khud dete hain.",
    "Vahan / Sarathi / eChallan / Parivahan site scrape nahi karta: aapko official steps deta hai (ya aap Computer Operator se karwati hain, OTP / payment aapka).",
    "Kisi document ki expiry khud nahi gadhta: tareekh aapke kaagaz se, warna khaali.",
    "Distance / toll / diesel ka daam khud nahi gadhta: Google Maps (jab juda ho) ya aapka number, aapke rate.",
    "Overload trip plan nahi karta: vehicle ki capacity se zyada maal = trip nahi banti.",
    "Driver ki salary payroll ka kaam hai; driver ki duty / hours drivers sahayak ka.",
)

# ---------------------------------------------------------------- vehicles
VEHICLE_TYPES = {
    "truck": {"label": "Truck (HGV / MGV)", "commercial": True, "goods": True},
    "trailer": {"label": "Trailer / tractor-trailer", "commercial": True, "goods": True},
    "tanker": {"label": "Tanker", "commercial": True, "goods": True},
    "tempo": {"label": "Tempo / LCV (chhota maal vahan)", "commercial": True, "goods": True},
    "pickup": {"label": "Pickup", "commercial": True, "goods": True},
    "van": {"label": "Van (maal / staff)", "commercial": True, "goods": True},
    "bus": {"label": "Bus", "commercial": True, "goods": False, "passenger": True},
    "taxi": {"label": "Taxi / cab (yellow board)", "commercial": True, "goods": False, "passenger": True},
    "car": {"label": "Car (private, white board)", "commercial": False, "goods": False},
    "two_wheeler": {"label": "Two-wheeler", "commercial": False, "goods": False},
}
TYPE_WORDS = {
    "truck": ("truck", "trak", "lorry", "hgv", "mgv", "dumper", "container", "10 wheel", "12 wheel", "6 wheel", "ट्रक"),
    "trailer": ("trailer", "tralla", "taurus"),
    "tanker": ("tanker", "tankar"),
    "tempo": ("tempo", "lcv", "407", "eicher", "dost", "bada dost", "tata ace", "chhota hathi", "chota hathi", "टेम्पो"),
    "pickup": ("pickup", "pick up", "bolero pickup", "maxx"),
    "van": ("van", "eeco", "omni"),
    "bus": ("bus", "बस", "school bus"),
    "taxi": ("taxi", "cab", "ertiga", "innova", "dzire tour"),
    "car": ("car", "gaadi", "kar"),
    "two_wheeler": ("bike", "scooter", "activa", "two wheeler", "2 wheeler", "motorcycle"),
}
FUELS = ("diesel", "petrol", "cng", "lng", "electric", "lpg")

STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH",
    "ML", "MN", "MP", "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "TG", "UK", "UA", "UP", "WB",
}
STATE_NAMES = {
    "MH": "Maharashtra", "GA": "Goa", "KA": "Karnataka", "GJ": "Gujarat", "MP": "Madhya Pradesh", "TS": "Telangana", "TG": "Telangana",
    "AP": "Andhra Pradesh", "TN": "Tamil Nadu", "KL": "Kerala", "DL": "Delhi", "UP": "Uttar Pradesh", "RJ": "Rajasthan", "HR": "Haryana",
    "PB": "Punjab", "WB": "West Bengal", "BR": "Bihar", "OD": "Odisha", "OR": "Odisha", "CG": "Chhattisgarh", "JH": "Jharkhand",
}
_REG = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$")
_BH = re.compile(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$")


def reg_check(text: str) -> dict:
    """'MH 30 AB 1234' / 'mh-30-ab-1234' / '22 BH 1234 AA' -> {ok, reg (clean, spaced), state, problem}."""
    raw = re.sub(r"[\s\-./]", "", str(text or "")).upper()
    if not raw:
        return {"ok": False, "reg": "", "state": "", "problem": "Gaadi number chahiye."}
    m = _BH.match(raw)
    if m:
        return {"ok": True, "reg": f"{m.group(1)} BH {m.group(2)} {m.group(3)}", "key": raw, "state": "BH", "bh": True, "problem": ""}
    m = _REG.match(raw)
    if not m:
        return {"ok": False, "reg": raw, "key": raw, "state": "", "problem": f"'{text}' gaadi number jaisa nahi lagta (jaise MH 30 AB 1234)."}
    st, rto, series, num = m.groups()
    if st not in STATE_CODES:
        return {"ok": False, "reg": raw, "key": raw, "state": st, "problem": f"'{st}' kisi rajya ka code nahi hai."}
    if int(num) == 0 or int(rto) == 0:
        return {"ok": False, "reg": raw, "key": raw, "state": st, "problem": "Number mein 0000 / RTO 00 nahi hota."}
    reg = " ".join(x for x in (st, rto.zfill(2), series, num.zfill(4)) if x)
    return {"ok": True, "reg": reg, "key": raw, "state": st, "bh": False, "problem": ""}


def type_of(text: str) -> str:
    t = f" {str(text or '').lower()} "
    for k in ("tanker", "trailer", "pickup", "two_wheeler", "bus", "taxi", "tempo", "van", "truck", "car"):
        if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) for w in TYPE_WORDS[k]):
            return k
    return ""


# ---------------------------------------------------------------- documents
# validity_months = what the law sets when it is fixed (used only to SUGGEST the next expiry after a renewal; the date on her
# paper always wins). windows = reminder days before expiry (one reminder per window: the tightest that applies).
DOC_KINDS: dict[str, dict[str, Any]] = {
    "rc": {"label": "RC (registration)", "windows": [60, 30, 15, 7], "for": "all",
           "note": "Private gaadi ka RC 15 saal, phir 5 saal ka renewal. Transport gaadi ka RC fitness ke saath chalta hai.",
           "where": "vahan.parivahan.gov.in > Vahan citizen services / mParivahan app; DigiLocker mein RC aa sakta hai."},
    "insurance": {"label": "Insurance", "validity_months": 12, "windows": [30, 15, 7, 1, 0], "for": "all",
                  "note": "Third-party insurance ke bina gaadi chalana mana hai (MV Act s.146; s.196 jurmana).",
                  "where": "Apne insurer / agent se renew; policy ki date yahan likhiye."},
    "fitness": {"label": "Fitness certificate (FC)", "windows": [45, 30, 15, 7, 1, 0], "for": "commercial",
                "note": "Transport gaadi: 8 saal tak har 2 saal, uske baad har saal (CMVR Rule 62). Fitness ab Automated Testing "
                        "Station (ATS) par, jahan aapke RTO ne ATS notify kiya hai (taarikhein kai baar badhi hain; RTO se pakka karein).",
                "where": "vahan.parivahan.gov.in > Fitness renewal appointment; ATS / RTO slot."},
    "puc": {"label": "PUC (pollution)", "windows": [15, 7, 1, 0], "for": "all",
            "note": "Nayi gaadi: registration se 1 saal; BS-IV / BS-VI: aam taur par 1 saal; purani: kam (CMVR Rule 115). "
                    "BS-VI 3-saal PUC ka July 2026 wala niyam abhi DRAFT hai.",
            "where": "Kisi bhi online PUC centre; certificate Vahan PUCC database mein dikhta hai."},
    "national_permit": {"label": "National Permit + authorisation", "validity_months": 12, "windows": [45, 30, 15, 7, 1, 0], "for": "goods",
                        "note": "National permit 5 saal ka, authorisation har saal online fees se (vahan.parivahan.gov.in/npermit).",
                        "where": "vahan.parivahan.gov.in/npermit > authorisation renewal; fees aap khud bharti hain."},
    "state_permit": {"label": "State / goods permit", "windows": [45, 30, 15, 7, 1, 0], "for": "commercial",
                     "note": "Rajya ka goods / contract carriage permit; taarikh permit par likhi hoti hai.",
                     "where": "Apne RTO / Vahan permit services."},
    "road_tax": {"label": "Road tax", "windows": [15, 7, 1, 0], "for": "all",
                 "note": "Commercial gaadi ka tax kai rajyon mein quarterly / yearly; taarikh tax receipt se.",
                 "where": "vahan.parivahan.gov.in > Pay your tax (aap khud bharti hain)."},
    "ais140": {"label": "AIS-140 GPS (VLTD) + panic button", "windows": [30, 15, 7, 0], "for": "commercial",
               "note": "Public service gaadi (bus, taxi) mein AIS-140 GPS + panic button zaroori (CMVR Rule 125H); goods / national "
                       "permit gaadi ke liye rajya ka niyam dekhiye. Device / SIM ka saalana renewal yahan.",
               "where": "Apne AIS-140 device vendor + rajya ka backend registration."},
    "fastag": {"label": "FASTag", "windows": [], "for": "all",
               "note": "Bina valid FASTag: cash par dugna toll, UPI par 1.25 guna (NHAI, 15 Nov 2025 se); 1 Feb 2026 se naye tag "
                       "par KYV nahi. Balance aap bank app mein dekhti hain; yahan sirf aakhri balance note.",
               "where": "Apne FASTag bank ka app / NETC portal."},
    "speed_governor": {"label": "Speed governor certificate", "windows": [30, 15, 7, 0], "for": "commercial",
                       "note": "Transport gaadi mein speed limiting device (CMVR Rule 118), certificate ki taarikh se.",
                       "where": "Device vendor / RTO."},
    "other": {"label": "Doosra kaagaz", "windows": [30, 7, 0], "for": "all", "note": "", "where": ""},
}
DOC_WORDS = {
    "rc": ("rc", "registration", "registration certificate"),
    "insurance": ("insurance", "bima", "policy", "beema"),
    "fitness": ("fitness", "fc", "fitness certificate"),
    "puc": ("puc", "pollution", "puc certificate", "pucc"),
    "national_permit": ("national permit", "np", "all india permit", "authorisation", "authorization"),
    "state_permit": ("permit", "state permit", "goods permit"),
    "road_tax": ("road tax", "tax", "mv tax"),
    "ais140": ("ais 140", "ais-140", "ais140", "vltd", "gps", "panic button"),
    "fastag": ("fastag", "fast tag"),
    "speed_governor": ("speed governor", "speed limiter"),
}


def doc_kind(text: str) -> str:
    t = str(text or "").lower().strip().replace("_", " ")
    if t.replace(" ", "_") in DOC_KINDS:
        return t.replace(" ", "_")
    for k in ("national_permit", "ais140", "speed_governor", "road_tax", "fastag", "fitness", "insurance", "puc", "rc", "state_permit"):
        if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) for w in DOC_WORDS[k]):
            return k
    return "other"


def required_docs(vtype: str, national: bool = False) -> list[str]:
    """Which documents this kind of vehicle normally needs (she can add / skip; the law + her RTO decide)."""
    info = VEHICLE_TYPES.get(vtype, VEHICLE_TYPES["truck"])
    out = ["rc", "insurance", "puc", "road_tax", "fastag"]
    if info.get("commercial"):
        out += ["fitness", "speed_governor"]
        out.append("national_permit" if (national and info.get("goods")) else "state_permit")
        if info.get("passenger"):
            out.append("ais140")
    return out


def fitness_months(reg_date: date | None, on: date) -> int:
    """CMVR Rule 62 (as amended 2022): transport vehicle fitness 24 months while up to 8 years old, else 12."""
    if reg_date is None:
        return 12
    age = (on - reg_date).days / 365.25
    return 24 if age < 8 else 12


def suggest_expiry(kind: str, renewed_on: date, reg_date: date | None = None, bs: str = "") -> date | None:
    """A SUGGESTION only (shown as 'andaaza'); the expiry on her paper wins."""
    months = None
    if kind == "fitness":
        months = fitness_months(reg_date, renewed_on)
    elif kind == "puc":
        months = 12 if (bs in ("BS4", "BS6") or (reg_date and (renewed_on - reg_date).days < 366)) else 6
    else:
        months = DOC_KINDS.get(kind, {}).get("validity_months")
    if not months:
        return None
    y, m = divmod(renewed_on.month - 1 + months, 12)
    d = min(renewed_on.day, [31, 29 if (renewed_on.year + y) % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m])
    return date(renewed_on.year + y, m + 1, d) - timedelta(days=1)


def doc_state(expires: date | None, on: date, windows: list[int]) -> dict:
    """-> {state missing|expired|due|ok, days_left, window (tightest reminder window that applies, or None)}."""
    if expires is None:
        return {"state": "missing", "days_left": None, "window": None}
    left = (expires - on).days
    if left < 0:
        return {"state": "expired", "days_left": left, "window": -1}
    hit = [w for w in sorted(windows or []) if left <= w]
    return {"state": "due" if hit else "ok", "days_left": left, "window": hit[0] if hit else None}


def bs_of(text: str) -> str:
    t = re.sub(r"[\s\-]", "", str(text or "").upper())
    for k, words in (("BS6", ("BS6", "BSVI")), ("BS4", ("BS4", "BSIV")), ("BS3", ("BS3", "BSIII")), ("BS2", ("BS2", "BSII"))):
        if any(w in t for w in words):
            return k
    return ""


# ---------------------------------------------------------------- fuel
def kmpl_series(fills: list[dict]) -> list[dict]:
    """Tank-to-tank: fills sorted by odometer; km/l is computed at each FULL fill from the previous full fill, using all litres
    put in after that previous full fill. Fills: {id, odo, litres, full}. Returns [{id, km, litres, kmpl}]."""
    out = []
    pts = sorted([f for f in fills if f.get("odo")], key=lambda f: f["odo"])
    last_full, acc = None, 0.0
    for f in pts:
        if last_full is not None:
            acc += float(f.get("litres") or 0)
        if f.get("full", True):
            if last_full is not None and acc > 0:
                km = f["odo"] - last_full["odo"]
                if km > 0:
                    out.append({"id": f["id"], "km": km, "litres": round(acc, 2), "kmpl": round(km / acc, 2)})
            last_full, acc = f, 0.0
    return out


def fuel_flags(entry: dict, prev_odo: float | None, history_kmpl: list[float], kmpl: float | None, tank_l: float = 0,
               price_hist: list[float] | None = None, low_pct: float = 25.0) -> list[dict]:
    """Outliers for one fill: odometer backwards, more litres than the tank, km/l far below this vehicle's usual, price per
    litre far from her usual. Possible theft / leak / meter fault: a signal, never a verdict."""
    fl = []
    odo = entry.get("odo")
    if odo and prev_odo and odo < prev_odo:
        fl.append({"id": "odo_back", "say": f"Odometer pichhli baar ({prev_odo:g}) se kam ({odo:g}): meter ya galat entry?"})
    lit = float(entry.get("litres") or 0)
    if tank_l and lit > tank_l * 1.05:
        fl.append({"id": "over_tank", "say": f"{lit:g} litre, tank sirf {tank_l:g} litre ka: bill / entry jaanchiye."})
    if kmpl is not None and len(history_kmpl) >= 3:
        med = statistics.median(history_kmpl)
        if med > 0 and kmpl < med * (1 - low_pct / 100):
            fl.append({"id": "low_kmpl", "say": f"Average {kmpl:g} km/l, is gaadi ka aam {med:g} km/l: {round((1 - kmpl / med) * 100)}% kam. "
                                                "Diesel chori / leak / tyre pressure / load / meter jaanchiye (yeh sirf ishaara hai).",
                       "median": med})
        elif med > 0 and kmpl > med * 1.6:
            fl.append({"id": "high_kmpl", "say": f"Average {kmpl:g} km/l bahut zyada (aam {med:g}): pichhli fill adhoori likhi thi?"})
    rpl = (float(entry.get("amount") or 0) / lit) if lit else 0
    if rpl and price_hist and len(price_hist) >= 3:
        pm = statistics.median(price_hist)
        if pm and abs(rpl - pm) / pm > 0.10:
            fl.append({"id": "price", "say": f"₹{rpl:.2f}/litre, aapka aam ₹{pm:.2f}: bill jaanchiye."})
    return fl


# ---------------------------------------------------------------- service schedule (STARTER numbers: maker's manual decides)
SERVICE_STARTERS: dict[str, list[dict]] = {
    "truck": [{"item": "Engine oil + filter", "km": 20000, "months": 6}, {"item": "Air filter", "km": 40000, "months": 12},
              {"item": "Fuel filter", "km": 20000, "months": 6}, {"item": "Greasing", "km": 5000, "months": 1},
              {"item": "Brake check", "km": 10000, "months": 3}, {"item": "Wheel alignment", "km": 20000, "months": 6}],
    "tempo": [{"item": "Engine oil + filter", "km": 10000, "months": 6}, {"item": "Air filter", "km": 20000, "months": 12},
              {"item": "Brake check", "km": 10000, "months": 6}, {"item": "Greasing", "km": 5000, "months": 2}],
    "bus": [{"item": "Engine oil + filter", "km": 15000, "months": 6}, {"item": "Brake check", "km": 5000, "months": 1},
            {"item": "AC / blower check", "km": 0, "months": 3}],
    "car": [{"item": "General service", "km": 10000, "months": 12}, {"item": "Wheel alignment", "km": 10000, "months": 12}],
}
for _k in ("trailer", "tanker"):
    SERVICE_STARTERS[_k] = SERVICE_STARTERS["truck"]
for _k in ("pickup", "van"):
    SERVICE_STARTERS[_k] = SERVICE_STARTERS["tempo"]
SERVICE_STARTERS["taxi"] = SERVICE_STARTERS["car"]
SERVICE_STARTERS["two_wheeler"] = [{"item": "General service", "km": 3000, "months": 4}]


def service_due(item: dict, odo_now: float | None, on: date, warn_km: float = 1000, warn_days: int = 10) -> dict:
    """item {km, months, last_km, last_on (date)} -> {state ok|due|late|unknown, km_left, days_left, why}."""
    km_left = days_left = None
    if item.get("km") and item.get("last_km") is not None and odo_now:
        km_left = item["last_km"] + item["km"] - odo_now
    if item.get("months") and item.get("last_on"):
        lo: date = item["last_on"]
        y, m = divmod(lo.month - 1 + int(item["months"]), 12)
        due_on = date(lo.year + y, m + 1, min(lo.day, 28))
        days_left = (due_on - on).days
    if km_left is None and days_left is None:
        return {"state": "unknown", "km_left": None, "days_left": None, "why": "Pichhli service kab / kitne km par, pata nahi."}
    late = (km_left is not None and km_left < 0) or (days_left is not None and days_left < 0)
    due = (km_left is not None and km_left <= warn_km) or (days_left is not None and days_left <= warn_days)
    why = []
    if km_left is not None:
        why.append(f"{abs(km_left):,.0f} km {'upar' if km_left < 0 else 'baaki'}")
    if days_left is not None:
        why.append(f"{abs(days_left)} din {'upar' if days_left < 0 else 'baaki'}")
    return {"state": "late" if late else ("due" if due else "ok"), "km_left": km_left, "days_left": days_left, "why": ", ".join(why)}


# ---------------------------------------------------------------- loads
def load_totals(items: list[dict]) -> dict:
    w = sum(float(i.get("weight_kg") or 0) * max(1, int(i.get("count") or 1)) for i in items)
    v = sum(float(i.get("cbm") or 0) * max(1, int(i.get("count") or 1)) for i in items)
    return {"weight_kg": round(w, 1), "cbm": round(v, 3), "missing_weight": [i.get("name", "") for i in items if not i.get("weight_kg")]}


def load_fit(items: list[dict], vehicle: dict, fill_pct: float = 85.0) -> dict:
    """Simple bin check: total weight vs payload (tonnes), total volume vs body cbm x fill factor, each piece's longest side vs
    body length / width / height (when both known). -> {fits, weight_pct, volume_pct, problems, notes}."""
    tot = load_totals(items)
    cap_kg = float(vehicle.get("capacity_t") or 0) * 1000
    cap_cbm = float(vehicle.get("capacity_cbm") or 0)
    probs, notes = [], []
    wpct = vpct = None
    if tot["missing_weight"]:
        probs.append("Inka wazan nahi diya: " + ", ".join(x for x in tot["missing_weight"][:5] if x) + " (wazan ke bina plan nahi).")
    if not cap_kg:
        probs.append(f"{vehicle.get('reg', 'Gaadi')} ki capacity (tonne) nahi likhi.")
    else:
        wpct = round(tot["weight_kg"] / cap_kg * 100, 1)
        if tot["weight_kg"] > cap_kg:
            probs.append(f"Wazan {tot['weight_kg']:,.0f} kg, capacity {cap_kg:,.0f} kg: {tot['weight_kg'] - cap_kg:,.0f} kg zyada (overload = "
                         "MV Act s.194 jurmana, tyre / brake ka khatra).")
    if cap_cbm and tot["cbm"]:
        vpct = round(tot["cbm"] / cap_cbm * 100, 1)
        if tot["cbm"] > cap_cbm * fill_pct / 100:
            probs.append(f"Jagah {tot['cbm']:g} cbm, body {cap_cbm:g} cbm ({fill_pct:g}% bharaai tak): nahi samayega.")
    elif tot["cbm"] and not cap_cbm:
        notes.append("Body ka cbm nahi likha: sirf wazan se jaancha.")
    body = [float(vehicle.get(k) or 0) for k in ("body_l", "body_w", "body_h")]
    if all(body):
        bmax = sorted(body, reverse=True)
        for i in items:
            dims = sorted([float(x) for x in (i.get("dims") or []) if x], reverse=True)
            if len(dims) == 3 and any(d > b for d, b in zip(dims, bmax)):
                probs.append(f"'{i.get('name', 'saamaan')}' ({' x '.join(f'{d:g}' for d in dims)} m) body ({' x '.join(f'{b:g}' for b in bmax)} m) mein nahi aayega.")
    if wpct is not None and wpct < 40 and not probs:
        notes.append(f"Gaadi sirf {wpct:g}% bhari: chhoti gaadi ya saath mein aur maal?")
    return {"fits": not probs, "weight_kg": tot["weight_kg"], "cbm": tot["cbm"], "weight_pct": wpct, "volume_pct": vpct,
            "problems": probs, "notes": notes}


def split_load(items: list[dict], vehicles: list[dict], fill_pct: float = 85.0) -> dict:
    """First-fit decreasing by weight across the free vehicles (biggest pieces first, smallest vehicle that still takes them).
    -> {plan: [{vehicle, items, weight_kg, cbm}], left: [items that fit nowhere]}."""
    pieces = []
    for i in items:
        for _ in range(max(1, int(i.get("count") or 1))):
            pieces.append({**i, "count": 1})
    pieces.sort(key=lambda p: (float(p.get("weight_kg") or 0), float(p.get("cbm") or 0)), reverse=True)
    vs = sorted([v for v in vehicles if float(v.get("capacity_t") or 0) > 0], key=lambda v: float(v["capacity_t"]))
    bins = [{"vehicle": v, "items": [], "kg": 0.0, "cbm": 0.0} for v in vs]
    left = []
    for p in pieces:
        kg, cbm = float(p.get("weight_kg") or 0), float(p.get("cbm") or 0)
        placed = False
        for b in sorted(bins, key=lambda b: (0 if b["items"] else 1, float(b["vehicle"]["capacity_t"]))):
            capk = float(b["vehicle"]["capacity_t"]) * 1000
            capv = float(b["vehicle"].get("capacity_cbm") or 0) * fill_pct / 100
            if b["kg"] + kg <= capk and (not capv or not cbm or b["cbm"] + cbm <= capv):
                b["items"].append(p)
                b["kg"] += kg
                b["cbm"] += cbm
                placed = True
                break
        if not placed:
            left.append(p)
    plan = []
    for b in bins:
        if not b["items"]:
            continue
        grouped: dict[str, dict] = {}
        for p in b["items"]:
            g = grouped.setdefault(p.get("name", "saamaan"), {**p, "count": 0})
            g["count"] += 1
        plan.append({"vehicle": b["vehicle"].get("reg", ""), "vehicle_id": b["vehicle"].get("id", ""), "items": list(grouped.values()),
                     "weight_kg": round(b["kg"], 1), "cbm": round(b["cbm"], 3)})
    return {"plan": plan, "left": left}


def trip_estimate(km: float | None, kmpl: float | None, diesel_rate: float | None, toll: float | None = None,
                  toll_per_km: float | None = None, other: float | None = None) -> dict:
    """Only from HER numbers. Anything missing = None + what is missing (never a guessed rate)."""
    miss = []
    fuel_l = round(km / kmpl, 1) if (km and kmpl) else None
    if not km:
        miss.append("distance")
    if not kmpl:
        miss.append("gaadi ka km/l (diesel entries se banta hai)")
    fuel_rs = round(fuel_l * diesel_rate) if (fuel_l and diesel_rate) else None
    if fuel_l and not diesel_rate:
        miss.append("aapka diesel rate")
    toll_rs = toll if toll else (round(km * toll_per_km) if (km and toll_per_km) else None)
    if toll_rs is None:
        miss.append("toll (is route ka ya per km)")
    total = None
    if fuel_rs is not None and toll_rs is not None:
        total = round(fuel_rs + toll_rs + float(other or 0))
    return {"km": km, "fuel_l": fuel_l, "fuel_rs": fuel_rs, "toll_rs": toll_rs, "other_rs": other or None, "total_rs": total, "missing": miss}


def drive_hours_note(hours: float | None, drivers: int = 1) -> str:
    """Motor Transport Workers Act 1961 (8 h a day / 48 a week) - subsumed in the OSH Code 2020 (in force 21 Nov 2025)."""
    if not hours:
        return ""
    if drivers <= 1 and hours > 8:
        return (f"Lagbhag {hours:g} ghante ki drive: ek driver ke liye 8 ghante / din se zyada. Do driver ya beech mein aaram rakhiye "
                "(duty / hours: drivers sahayak).")
    return ""


def interstate(origin_state: str, dest_state: str) -> bool:
    return bool(origin_state and dest_state and origin_state.upper() != dest_state.upper())


SOURCES = [
    ("MoRTH G.S.R. 272(E) 5 Apr 2022 - fitness only via registered Automated Testing Stations (Rule 175), phased (heavy goods / "
     "passenger 1 Apr 2023, medium + LMV transport 1 Jun 2024), fitness 2 years up to 8 years then yearly",
     "https://morth.gov.in/sites/default/files/notifications_document/3GSR%20272(E)%205%20April%202022%20transport%20vehicle%20fitness%20ATS.pdf",
     "notification 5 Apr 2022"),
    ("ATS mandatory date extended to 1 Oct 2024", "https://vikaspedia.in/news/extension-of-date-for-mandatory-testing-to-1st-oct-2024", "2024"),
    ("Nagpur RTO: transport vehicles fitness every 2 years for first 8 years, then yearly; ATS opening",
     "https://www.thehitavada.com/Encyc/2026/4/8/automated-vehicle-testing-station-to-open-in-nagpur-on-may-15.html", "8 Apr 2026"),
    ("PUC validity today by BS norm and the July 2026 DRAFT for 3-year PUC on BS-VI private vehicles under 6 years",
     "https://www.angelone.in/news/economy/bs-vi-cars-under-6-years-may-need-puc-certificate-only-once-every-3-years-government-proposal-explained",
     "29 Jul 2026"),
    ("National Permit: base permit 5 years, yearly authorisation, documents, vahan.parivahan.gov.in/npermit (fees approximate; portal decides)",
     "https://www.paybima.com/blog/motor-insurance/all-india-permit-for-commercial-vehicles", "2026"),
    ("AIS-140 VLTD + hard-wired panic button for transport vehicles (GSR 979(E) 28 Sep 2018 / CMVR 125H), state enforcement",
     "https://blog.fleetx.ai/blog-ais140-guide/", "May 2026 (vendor guide)"),
    ("FASTag 2026: no cash at NH plazas from 1 Apr 2026, UPI without FASTag 1.25x, KYV dropped for new tags from 1 Feb 2026",
     "https://www.trucksbuses.com/news/fastag-2026-updates-new-toll-rules-penalties-and-changes", "30 Jan 2026"),
    ("eChallan check / pay: echallan.parivahan.gov.in (vehicle number + chassis / engine last digits + OTP; she pays herself)",
     "https://echallan.parivahan.gov.in/", "official portal"),
]

ECHALLAN_STEPS = [
    "echallan.parivahan.gov.in kholiye (ya mParivahan app) > 'Check Online Services' > 'Get Challan Details'.",
    "Vehicle number chuniye, gaadi number + chassis / engine number ke aakhri 5 ank daaliye, CAPTCHA bhariye.",
    "Challan dikhe to number, taarikh, rakam aur offence yahan bataiye (ya screenshot bhejiye): Hoola darj karega.",
    "Bharna ho to card yahan aayega; paise aap khud portal par bhariye (OTP / payment aapka), phir 'Maine bhar diya' dabaiye.",
    "Galat challan lage to portal par 'Grievance' / virtual court ka raasta; Hoola khud kuch nahi bharta.",
]
VAHAN_STEPS = [
    "vahan.parivahan.gov.in/vahanservice > rajya chuniye > 'Know your vehicle details' / RC status / tax / permit / fitness services.",
    "mParivahan app mein bhi RC, insurance, fitness, PUC ki taarikh dikhti hai (OTP aapke phone par).",
    "Taarikhein yahan bataiye ya kaagaz ki photo bhejiye: Hoola padh ke card mein likhega, aap pakka karein.",
]
