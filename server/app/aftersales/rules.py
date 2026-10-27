"""After-sales service rules Hoola works to (researched 22-23 Oct 2026; sources in WIRING.md / CLAUDE.md). Pure functions.

Service intervals are common Indian dealer practice and are only STARTING values: her own schedule (per product type) and the
brand's manual win. A visit's checklist is what a good technician ticks for that product.

Warranty: the Department of Consumer Affairs asked white-goods makers (Nov 2023) to start the warranty from the date of
INSTALLATION, not purchase; starting it before the buyer can use the product is called an unfair trade practice / unfair
contract under the Consumer Protection Act 2019. So Hoola counts warranty from the install date and flags a warranty card that
starts earlier. A product not matching its express warranty is a product-liability ground against the manufacturer (CPA 2019
Sec 84(1)(d)); poor service by the dealer is 'deficiency in service' (Sec 2(11)). Legal Metrology rules govern package
declarations (MRP etc.), not the length of a warranty: the warranty is whatever the maker's card says.

WhatsApp (Meta, Oct 2026): a UTILITY template must be non-promotional and about the customer's own product / booking (service
due, visit confirmed, visit report). A renewal push ("AMC renew karein") or any offer is MARKETING (Meta re-categorises it).
Free-form text only inside 24 h of the customer's last message; templates any time. From 1 Oct 2026 utility messages inside the
window are charged again (1,000 free service messages / number / month).
"""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta

# label, words (Hinglish / brand words), months between services, usage step (km / hours) + unit, seasons (months of the
# year when the service is best), visit minutes, typical warranty months, AMC visits per year, checklist, readings to note
PRODUCTS: dict[str, dict] = {
    "ro": {"label": "RO water purifier", "words": ("ro", "purifier", "water purifier", "aquaguard", "kent", "pureit", "livpure", "filter", "paani"),
           "months": 4, "minutes": 45, "warranty": 12, "amc_visits": 3,
           "checklist": ["Sediment filter badla / saaf", "Carbon filter dekha", "Membrane flow theek", "TDS jaancha (input / output)",
                         "Leakage nahi", "Tank saaf kiya", "UV lamp chal raha"],
           "readings": ["tds_in", "tds_out"]},
    "ac": {"label": "AC", "words": ("ac", "air conditioner", "split", "window ac", "inverter ac", "voltas", "daikin", "lloyd", "blue star"),
           "months": 6, "seasons": (3, 9), "minutes": 60, "warranty": 12, "amc_visits": 2,
           "checklist": ["Filter saaf", "Indoor coil jet wash", "Outdoor coil saaf", "Drain pipe saaf", "Gas pressure check",
                         "Cooling (vent temp) check", "Earthing / wiring check", "Remote / display theek"],
           "readings": ["gas_psi", "vent_temp_c", "amps"]},
    "inverter": {"label": "Inverter / battery", "words": ("inverter", "battery", "ups", "luminous", "exide", "microtek", "amaron", "tubular"),
                 "months": 3, "minutes": 30, "warranty": 24, "amc_visits": 4,
                 "checklist": ["Distilled water top-up", "Terminal saaf + grease", "Specific gravity / voltage check", "Backup test",
                               "Charging check", "Wiring tight"],
                 "readings": ["battery_volts", "specific_gravity", "backup_minutes"]},
    "cctv": {"label": "CCTV", "words": ("cctv", "camera", "dvr", "nvr", "hikvision", "cp plus", "dahua"),
             "months": 3, "minutes": 45, "warranty": 12, "amc_visits": 4,
             "checklist": ["Har camera ki picture saaf", "Lens saaf", "DVR / NVR recording chal rahi", "Hard disk health", "Date / time sahi",
                           "Mobile app view check", "Power supply / adaptor check"],
             "readings": ["cameras_ok", "recording_days"]},
    "two_wheeler": {"label": "Two-wheeler", "words": ("bike", "scooter", "scooty", "activa", "splendor", "two wheeler", "motorcycle", "gaadi"),
                    "months": 3, "usage": 3000, "usage_unit": "km", "minutes": 90, "warranty": 24, "amc_visits": 4,
                    "checklist": ["Engine oil", "Air filter", "Brake check", "Chain lube / adjust", "Battery", "Tyre pressure", "Lights / horn"],
                    "readings": ["odometer_km"]},
    "car": {"label": "Car", "words": ("car", "gaadi", "suv", "maruti", "hyundai", "tata", "mahindra", "four wheeler"),
            "months": 12, "usage": 10000, "usage_unit": "km", "minutes": 180, "warranty": 36, "amc_visits": 1,
            "checklist": ["Engine oil + filter", "Air filter", "AC filter", "Brake pads", "Coolant", "Battery", "Tyres / alignment", "Wiper / lights"],
            "readings": ["odometer_km"]},
    "solar": {"label": "Solar system", "words": ("solar", "panel", "rooftop", "ongrid", "on-grid", "solar inverter"),
              "months": 3, "minutes": 60, "warranty": 60, "amc_visits": 4,
              "checklist": ["Panel saaf", "Inverter display / error", "Earthing / lightning arrester", "DC / AC wiring", "Generation (kWh) dekha",
                            "Structure tight"],
              "readings": ["kwh_total", "kwh_today"]},
    "genset": {"label": "Generator (DG set)", "words": ("genset", "generator", "dg", "dg set", "kirloskar", "cummins"),
               "months": 6, "usage": 250, "usage_unit": "hours", "minutes": 120, "warranty": 12, "amc_visits": 4,
               "checklist": ["Engine oil", "Oil / fuel / air filter", "Coolant", "Battery", "Fan belt", "Load test", "Leakage nahi"],
               "readings": ["run_hours", "battery_volts"]},
    "lift": {"label": "Lift / elevator", "words": ("lift", "elevator", "otis", "kone", "johnson lift"),
             "months": 1, "minutes": 90, "warranty": 12, "amc_visits": 12,
             "checklist": ["Brake check", "Door / interlock", "Ropes / pulleys", "Emergency alarm + light", "ARD / rescue device",
                           "Levelling", "Machine room saaf", "Lubrication"],
             "readings": ["trips", "levelling_mm"]},
    "appliance": {"label": "Appliance (fridge / washing machine)", "words": ("fridge", "refrigerator", "washing machine", "washer", "microwave",
                                                                             "oven", "dishwasher", "samsung", "lg", "whirlpool", "godrej"),
                  "months": 12, "minutes": 60, "warranty": 12, "amc_visits": 1,
                  "checklist": ["Cooling / drum chal raha", "Gasket / door seal", "Drain / filter saaf", "Wiring / earthing", "Noise / vibration"],
                  "readings": []},
    "water_heater": {"label": "Water heater / geyser", "words": ("geyser", "water heater", "heater", "racold", "bajaj geyser"),
                     "months": 12, "minutes": 45, "warranty": 24, "amc_visits": 1,
                     "checklist": ["Descaling", "Anode rod", "Thermostat", "Safety valve", "Earthing"], "readings": []},
    "chimney": {"label": "Kitchen chimney", "words": ("chimney", "hood", "elica", "faber"),
                "months": 4, "minutes": 45, "warranty": 12, "amc_visits": 3,
                "checklist": ["Filter saaf", "Oil collector", "Motor / suction", "Duct check"], "readings": []},
    "broadband": {"label": "Broadband / FTTH", "words": ("broadband", "ftth", "wifi", "router", "ont", "fiber", "fibre", "internet"),
                  "months": 6, "minutes": 30, "warranty": 12, "amc_visits": 2,
                  "checklist": ["Optical power (dBm) dekha", "Router / ONT firmware", "Wi-Fi speed test", "Patch cord / connector saaf",
                                "Power adaptor"],
                  "readings": ["rx_power_dbm", "speed_mbps"]},
    "other": {"label": "Machine", "words": (), "months": 6, "minutes": 60, "warranty": 12, "amc_visits": 2,
              "checklist": ["Chal raha hai", "Saaf-safai", "Wiring / safety"], "readings": []},
}

KINDS = ("service", "repair", "install", "amc", "warranty", "inspection")
AMC_PLANS = ("comprehensive", "non_comprehensive")   # comprehensive = parts + labour covered; non = labour / visits only

NEVER = ("Graahak ko message Hoola khud nahi bhejta: draft aap bhejti hain, ya business WhatsApp template aapke tap par.",
         "Graahak se paisa (visit / part charge) aapki haan ke bina nahi maanga jaata; Hoola paisa leta / bhejta nahi.",
         "Ek technician ke do visit ek samay par book nahi hote.",
         "Warranty install ki tareekh se ginte hain; brand claim ka faisla brand ka.",
         "Renewal / offer wala message 'marketing' hai: sirf jinhone haan kahi unhe template se.")

PROMO_WORDS = re.compile(r"(offer|discount|% ?off|chhoot|chhut|sale\b|free gift|renew (now|today|karein|karo)|abhi renew|save ₹|"
                         r"limited time|jaldi karein|upgrade|naya model|exchange offer|cashback|deal)", re.I)

# recommended Meta templates (language hi = Hinglish in Roman script is fine); her WABA must approve them first
TEMPLATES = {
    "service_due_reminder": {"category": "UTILITY", "language": "hi",
                             "body": "Namaste {{1}} ji, {{2}} se: aapke {{3}} ki service {{4}} tak due hai. Technician kab bhejein? Suvidha "
                                     "ka din aur samay reply karein.",
                             "example": ["Ramesh", "Shree Sales & Service", "RO water purifier", "28 Oct"],
                             "params": ["first_name", "business", "product", "due"]},
    "service_visit_confirmed": {"category": "UTILITY", "language": "hi",
                                "body": "Namaste {{1}} ji, aapke {{2}} ke liye technician {{3}} aayenge, samay: {{4}}. Visit number {{5}}. "
                                        "Samay badalna ho to reply karein.",
                                "example": ["Ramesh", "AC", "Sunil", "25 Oct, 11:00 baje", "V-0012"],
                                "params": ["first_name", "product", "tech", "when", "number"]},
    "service_visit_report": {"category": "UTILITY", "language": "hi",
                             "body": "Namaste {{1}} ji, aapke {{2}} ki service (visit {{3}}) poori hui. Kaam: {{4}}. Agli service: {{5}}. "
                                     "Report ke liye dhanyavaad, sawaal ho to reply karein.",
                             "example": ["Ramesh", "RO water purifier", "V-0012", "filter badla, TDS 60", "Feb 2027"],
                             "params": ["first_name", "product", "number", "work", "next_due"]},
    "amc_expiry_notice": {"category": "MARKETING", "language": "hi",
                          "body": "Namaste {{1}} ji, {{2}} se: aapke {{3}} ka AMC {{4}} ko khatam ho raha hai. Aage jaari rakhna ho to reply karein.",
                          "example": ["Ramesh", "Shree Sales & Service", "AC", "30 Nov"],
                          "params": ["first_name", "business", "product", "until"], "footer": "Band karne ke liye STOP likhein"},
}


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def ptype_of(text: str, given: str = "") -> str:
    g = str(given or "").strip().lower().replace("-", "_").replace(" ", "_")
    if g in PRODUCTS:
        return g
    low = f" {str(text or '').lower()} {str(given or '').lower()} "
    best, score = "other", 0
    for k, p in PRODUCTS.items():
        for w in p["words"]:
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low):
                sc = len(w) + (3 if w == k else 0)
                if sc > score:
                    best, score = k, sc
    return best


def interval_months(ptype: str, schedule: dict | None = None, amc_visits: int = 0) -> int:
    """Her schedule first, then an active AMC's visits per year, then the starting value."""
    sch = (schedule or {}).get(ptype) or {}
    if sch.get("months"):
        return max(1, int(sch["months"]))
    if amc_visits:
        return max(1, round(12 / max(1, int(amc_visits))))
    return int(PRODUCTS.get(ptype, PRODUCTS["other"])["months"])


def usage_step(ptype: str, schedule: dict | None = None) -> float:
    sch = (schedule or {}).get(ptype) or {}
    if sch.get("usage"):
        return float(sch["usage"])
    return float(PRODUCTS.get(ptype, PRODUCTS["other"]).get("usage") or 0)


def _season_snap(due: date, seasons: tuple) -> date:
    """AC: service just before summer / after the monsoon. Move a due date to the 1st of the closest season month within 2 months."""
    best, gap = due, 10 ** 6
    for y in (due.year - 1, due.year, due.year + 1):
        for m in seasons:
            c = date(y, m, 1)
            g = abs((c - due).days)
            if g <= 62 and g < gap:
                best, gap = c, g
    return best


def next_due(ptype: str, last: date | None, installed: date | None, schedule: dict | None = None, amc_visits: int = 0,
             reading: float | None = None, per_day: float | None = None, last_reading_on: date | None = None) -> dict:
    """When the next service falls due: time from the last service (or install), the sooner usage-based date when a reading
    and the daily use are known, AC snapped to its season."""
    base = last or installed
    if base is None:
        return {"due": None, "why": "Install / pichhli service ki tareekh nahi"}
    m = interval_months(ptype, schedule, amc_visits)
    due = add_months(base, m)
    why = f"har {m} mahine"
    seasons = PRODUCTS.get(ptype, {}).get("seasons")
    if seasons and not (schedule or {}).get(ptype, {}).get("months") and not amc_visits:
        snapped = _season_snap(due, seasons)
        if snapped != due:
            due, why = snapped, why + " (garmi se pehle / baarish ke baad)"
    step = usage_step(ptype, schedule)
    if step and reading is not None and per_day and per_day > 0:
        unit = PRODUCTS.get(ptype, {}).get("usage_unit", "")
        days = int(step / per_day)
        u = (last_reading_on or base) + timedelta(days=max(1, days))
        if u < due:
            due, why = u, f"har {step:g} {unit} (roz ~{per_day:.0f} {unit})"
    return {"due": due, "why": why}


def warranty_until(installed: date | None, months: int | None, purchase: date | None = None) -> dict:
    if not installed and not purchase:
        return {"until": None, "note": ""}
    start = installed or purchase
    note = ""
    if installed and purchase and purchase < installed:
        note = ("Warranty install ki tareekh se gini (DoCA, Nov 2023): card par kharid ki tareekh likhi ho to brand se "
                "install date se ginwaiye.")
    return {"until": add_months(start, int(months or 12)), "note": note}


def coverage(on: date, warranty_end: date | None, amc_until: date | None, amc_plan: str) -> dict:
    """Who pays for this visit: brand warranty (parts + labour), comprehensive AMC (parts + labour), non-comprehensive AMC
    (visit / labour only), or the customer (her Haan before asking)."""
    if warranty_end and on <= warranty_end:
        return {"by": "warranty", "parts": True, "labour": True, "say": f"Warranty mein ({warranty_end.isoformat()} tak)"}
    if amc_until and on <= amc_until:
        comp = amc_plan == "comprehensive"
        return {"by": "amc", "parts": comp, "labour": True,
                "say": f"AMC ({'comprehensive' if comp else 'sirf labour / visit'}) {amc_until.isoformat()} tak"}
    return {"by": "customer", "parts": False, "labour": False, "say": "Warranty / AMC nahi: charge graahak ka (aapki haan se)"}


def classify(text: str) -> str:
    """UTILITY only when nothing promotional; any offer / renewal push = MARKETING (Meta's rule)."""
    return "MARKETING" if PROMO_WORDS.search(text or "") else "UTILITY"


def same_area(a: dict, b: dict) -> bool:
    pa, pb = str(a.get("pincode") or ""), str(b.get("pincode") or "")
    if len(pa) == 6 and len(pb) == 6:
        return pa == pb or (pa[:5] == pb[:5] and _norm(a.get("area")) == _norm(b.get("area")) and bool(_norm(a.get("area"))))
    aa, ab = _norm(a.get("area")), _norm(b.get("area"))
    return bool(aa) and aa == ab


def _norm(v) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def covers_area(tech_areas: list, place: dict) -> bool:
    """A technician's areas: names ('Kothrud') or pincode prefixes ('4110', '411038'). Empty list = goes everywhere."""
    if not tech_areas:
        return True
    pin, area = str(place.get("pincode") or ""), _norm(place.get("area"))
    for a in tech_areas:
        a = str(a).strip()
        if a.isdigit() and pin.startswith(a):
            return True
        if _norm(a) and _norm(a) == area:
            return True
    return False
