"""Shikayat Sahayak rules: deadlines per sector, where a customer can go next, root-cause words, severity, closure checklist.

Researched 23 Oct 2026 (sources in WIRING.md / CLAUDE.md). Numbers here are STARTING rules: her own targets can be shorter,
never longer than the regulator's (a longer target is capped and she is told). Hoola does not give legal advice; the
routes are what a customer can do, written so her final reply is honest about them.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

# ---------------------------------------------------------------- sectors
# ack_hours: acknowledge within; resolve_days: final reply within; legal: True when a regulator sets it (cap her targets).
SECTORS: dict[str, dict[str, Any]] = {
    "general": {
        "label": "Dukaan / seva (aam business)", "ack_hours": 48, "resolve_days": 30, "legal": False,
        "law": ("Koi tay sarkari samay-seema nahi; Hoola E-Commerce Rules 2020 wala standard (48 ghante mein jawab, 1 mahine "
                "mein hal) achhi aadat ke roop mein leta hai."),
        "routes": ["nch", "commission"],
    },
    "ecommerce": {
        "label": "Online bikri (website / app / marketplace seller)", "ack_hours": 48, "resolve_days": 30, "legal": True,
        "law": ("Consumer Protection (E-Commerce) Rules 2020: grievance officer ka naam / number site par; shikayat ki "
                "pavti 48 ghante mein, hal 1 mahine mein; har shikayat ka ticket number."),
        "routes": ["nch", "commission"],
        "must": ["ticket_number", "grievance_officer"],
    },
    "bank": {
        "label": "Bank / NBFC / payment company (RBI ke under)", "ack_hours": 24, "resolve_days": 30, "legal": True,
        "law": ("RBI Integrated Ombudsman Scheme 2026 (1 July 2026 se): graahak ko 30 din mein jawab na mile, ya jawab se "
                "santusht na ho, to woh RBI Ombudsman (cms.rbi.org.in, 14448) ja sakta hai. Aakhri jawab mein yeh "
                "rasta likhna zaroori; fraud / unauthorised transaction ke maamle mein lambi samay-seema RBI ke niyam se."),
        "routes": ["rbi", "nch"],
        "final_reply_must": "rbi",
    },
    "insurance": {
        "label": "Bima (insurer / agent / broker)", "ack_hours": 24, "resolve_days": 14, "legal": True,
        "law": ("IRDAI (Protection of Policyholders' Interests ...) Regulations 2024 + Master Circular 2024: pavti turant, hal "
                "14 din mein; Bima Bharosa (bimabharosa.irdai.gov.in) par darj; hal na ho to Insurance Ombudsman."),
        "routes": ["bima_bharosa", "insurance_ombudsman", "nch"],
        "final_reply_must": "insurance_ombudsman",
    },
    "telecom": {
        "label": "Telecom / broadband / ISP / cable", "ack_hours": 24, "resolve_days": 30, "legal": True,
        "law": ("TRAI Telecom Consumers Complaint Redressal Regulations: har shikayat ka docket number; hal na ho to graahak "
                "service provider ke Appellate Authority ke paas (3 mahine ke andar), jo 60 din mein faisla de. Franchise ho to "
                "principal operator (jaise BSNL) ka CRM docket bhi rakhiye."),
        "routes": ["telecom_appellate", "nch"],
        "must": ["docket"],
    },
    "electricity": {
        "label": "Bijli (distribution / franchise)", "ack_hours": 24, "resolve_days": 45, "legal": True,
        "law": ("Electricity (Rights of Consumers) Rules 2020: shikayat ka hal zyada se zyada 45 din; phir CGRF (Consumer "
                "Grievance Redressal Forum), phir Electricity Ombudsman. Har rajya ke SERC niyam alag samay de sakte hain."),
        "routes": ["cgrf", "electricity_ombudsman"],
    },
    "securities": {
        "label": "Share broker / investment adviser / SEBI registered", "ack_hours": 24, "resolve_days": 21, "legal": True,
        "law": "SEBI SCORES 2.0: entity 21 din mein hal; graahak first review (designated body), phir SEBI second review.",
        "routes": ["scores", "smart_odr"],
    },
    "data": {
        "label": "Personal data / privacy (DPDP)", "ack_hours": 48, "resolve_days": 90, "legal": True,
        "law": ("DPDP Rules 2025 Rule 14(3): data principal ki maang / shikayat ka jawab 90 din mein (yeh niyam 13 May 2027 se "
                "laagu; abhi se achhi aadat). Hal na ho to Data Protection Board of India."),
        "routes": ["dpb"],
    },
}
SECTOR_WORDS = {
    "ecommerce": ("online", "website", "app", "amazon", "flipkart", "meesho", "marketplace", "e-commerce", "ecommerce"),
    "bank": ("bank", "nbfc", "loan", "emi", "upi", "wallet", "microfinance"),
    "insurance": ("bima", "insurance", "insurer", "policy", "claim", "lic"),
    "telecom": ("isp", "broadband", "fiber", "fibre", "ftth", "internet", "telecom", "cable", "dth", "mobile network", "bsnl", "wifi"),
    "electricity": ("bijli", "electricity", "discom", "msedcl", "power"),
    "securities": ("broker", "demat", "share", "mutual fund", "sebi", "adviser", "advisor"),
    "data": ("data", "privacy", "dpdp", "personal data"),
}

ROUTES: dict[str, dict[str, str]] = {
    "nch": {"name": "National Consumer Helpline", "how": "1915 par call, WhatsApp 8800001915, ya consumerhelpline.gov.in (INGRAM)"},
    "commission": {"name": "Consumer Commission (e-Jagriti)", "how": ("e-jagriti.gov.in par online (1 Jan 2025 se e-Daakhil ki jagah); "
                                                                    "District Rs 50 lakh tak, State Rs 50 lakh-2 crore, National 2 crore se upar; "
                                                                    "2 saal ke andar")},
    "rbi": {"name": "RBI Ombudsman", "how": "cms.rbi.org.in ya 14448 (bank ka jawab 30 din mein na aaye / pasand na aaye)"},
    "bima_bharosa": {"name": "IRDAI Bima Bharosa", "how": "bimabharosa.irdai.gov.in ya 155255"},
    "insurance_ombudsman": {"name": "Insurance Ombudsman", "how": "cioins.co.in (bima company ke jawab ke baad / jawab na aaye to)"},
    "telecom_appellate": {"name": "Telecom Appellate Authority", "how": "service provider ka appellate (3 mahine ke andar appeal), phir NCH / commission"},
    "cgrf": {"name": "CGRF (bijli)", "how": "apne discom ka Consumer Grievance Redressal Forum"},
    "electricity_ombudsman": {"name": "Electricity Ombudsman", "how": "rajya ka Vidyut Lokpal (CGRF ke faisle ke baad)"},
    "scores": {"name": "SEBI SCORES", "how": "scores.sebi.gov.in"},
    "smart_odr": {"name": "SMART ODR", "how": "smartodr.in (online samjhauta)"},
    "dpb": {"name": "Data Protection Board of India", "how": "Board ka online portal (business ke jawab ke baad)"},
}

# ---------------------------------------------------------------- stages
STAGES = ("new", "acknowledged", "investigating", "waiting_customer", "waiting_third_party", "resolved", "closed", "reopened",
          "rejected")
STAGE_LABEL = {"new": "Nayi", "acknowledged": "Pavti di", "investigating": "Jaanch chal rahi", "waiting_customer": "Graahak ka intezaar",
               "waiting_third_party": "Company / supplier ka intezaar", "resolved": "Hal kiya", "closed": "Band", "reopened": "Phir khuli",
               "rejected": "Nahi maani (wajah ke saath)"}
OPEN = ("new", "acknowledged", "investigating", "waiting_customer", "waiting_third_party", "reopened")
STAGE_ALIAS = {"ack": "acknowledged", "pavti": "acknowledged", "jaanch": "investigating", "check": "investigating",
               "customer": "waiting_customer", "graahak": "waiting_customer", "supplier": "waiting_third_party",
               "company": "waiting_third_party", "hal": "resolved", "done": "resolved", "theek": "resolved", "band": "closed",
               "reject": "rejected", "open": "reopened"}

CHANNELS = ("chat", "call", "whatsapp", "network", "walk_in", "phone", "email", "file", "social", "other")

# ---------------------------------------------------------------- root causes
CAUSES: dict[str, tuple[str, ...]] = {
    "product_defect": ("kharab", "defect", "toot", "tuta", "tooti", "faulty", "band ho gaya", "kaam nahi kar", "not working", "broken",
                       "leak", "dead", "chalta nahi", "kharabi"),
    "damaged_delivery": ("damage", "phata", "pichka", "dented", "packet khula", "seal toota", "transit"),
    "wrong_item": ("galat", "wrong item", "doosra", "different item", "size galat", "colour galat", "color galat"),
    "missing_item": ("missing", "kam aaya", "nahi aaya", "short", "item gayab", "kam diya"),
    "late_delivery": ("late", "der", "delay", "abhi tak nahi", "deri", "time par nahi", "kab aayega"),
    "billing": ("bill", "zyada paise", "extra charge", "overcharg", "double", "do baar", "kati", "katauti", "deduct", "charge laga", "galat amount", "invoice", "mrp se zyada"),
    "refund": ("refund", "paise wapas", "paisa wapas", "return", "wapsi"),
    "service_quality": ("service", "slow", "dheema", "quality", "ganda", "kachra", "saaf nahi", "thanda", "bekaar"),
    "staff_behaviour": ("badtameez", "rude", "behaviour", "behavior", "misbehav", "chillaya", "gaali", "staff ne", "badtameezi"),
    "technical": ("network", "internet", "speed", "outage", "down", "connection", "signal", "wifi", "light gayi", "no service"),
    "installation": ("installation", "install", "fitting", "lagaya nahi", "setup", "visit nahi"),
    "warranty": ("warranty", "guarantee", "replacement nahi"),
    "pricing": ("mehenga", "price", "rate", "daam"),
    "communication": ("jawab nahi", "call nahi uthaya", "reply nahi", "koi nahi bata", "no response", "ignore"),
    "fraud": ("fraud", "dhokha", "scam", "cheat", "thagi", "nakli", "fake"),
    "privacy": ("data", "privacy", "mera number", "spam", "bina pooche"),
    "safety": ("current laga", "shock", "aag", "fire", "chot", "injury", "jal gaya", "food poisoning", "bimar", "allergy", "khatarnak"),
}
CAUSE_LABEL = {"product_defect": "Saamaan mein kharabi", "damaged_delivery": "Tuta / damaged aaya", "wrong_item": "Galat saamaan",
               "missing_item": "Saamaan kam / nahi aaya", "late_delivery": "Der", "billing": "Bill / zyada paisa",
               "refund": "Refund", "service_quality": "Seva ki quality", "staff_behaviour": "Staff ka bartav",
               "technical": "Technical / network", "installation": "Installation / visit", "warranty": "Warranty",
               "pricing": "Daam", "communication": "Jawab nahi mila", "fraud": "Dhokha ka aarop", "privacy": "Data / privacy",
               "safety": "Suraksha / chot", "other": "Aur kuch"}

URGENT_WORDS = ("current laga", "shock", "aag", "fire", "chot", "injury", "hospital", "food poisoning", "khoon", "jal gaya", "bachcha")
LEGAL_WORDS = ("consumer court", "consumer forum", "court", "police", "fir", "vakil", "lawyer", "legal notice", "notice bhej",
               "1915", "ombudsman", "lokpal", "media", "news", "viral", "social media", "review dalunga", "review daalunga", "twitter",
               "instagram pe", "facebook pe")
ANGRY_WORDS = ("bahut gussa", "worst", "bakwaas", "faltu", "kabhi nahi", "never again", "pagal", "!!!", "dhokebaaz")
SEVERITIES = ("low", "normal", "high", "urgent")

# ---------------------------------------------------------------- compensation
COMP_KINDS = {"refund": "Refund (paisa wapas)", "replacement": "Naya saamaan / replacement", "discount": "Chhoot / discount",
              "goodwill": "Goodwill (maafi ke saath kuch)", "free_service": "Muft seva / repair", "credit": "Credit / voucher"}
MONEY_KINDS = ("refund", "discount", "goodwill", "credit")

NEVER = ("Paisa Hoola nahi deta, na refund karta hai: aap dengi, Hoola sirf hisaab rakhta hai.",
         "Refund / replacement / discount / goodwill sirf aapki haan (paise wale card par fingerprint) ke baad.",
         "Graahak ko message aapke tap se: draft, ya business WhatsApp sirf 24 ghante ke window mein.",
         "Graahak ki baat jaankari hai, aadesh nahi; OTP / card / password kabhi nahi liya jaata.",
         "Galat vaada nahi: jo tay nahi hua (paisa, tareekh) woh message mein nahi jaata.",
         "Customer ki photo / video ki EXIF / GPS location hata kar rakhi jaati hai.")


def norm_sector(v: str) -> str:
    v = str(v or "").strip().lower()
    if v in SECTORS:
        return v
    for k, words in SECTOR_WORDS.items():
        if any(w in v for w in words):
            return k
    return "general"


def norm_stage(v: str) -> str:
    v = str(v or "").strip().lower().replace(" ", "_")
    return STAGE_ALIAS.get(v, v)


def targets(sector: str, ack_hours: float | None = None, resolve_days: float | None = None) -> dict[str, Any]:
    """Her targets inside the regulator's: a longer target than the law is capped (and said)."""
    sec = SECTORS.get(sector) or SECTORS["general"]
    ah, rd, notes = float(sec["ack_hours"]), float(sec["resolve_days"]), []
    if ack_hours:
        if ack_hours > ah and sec["legal"]:
            notes.append(f"Pavti {ack_hours:g} ghante niyam ({ah:g}) se zyada: {ah:g} ghante rakha.")
        else:
            ah = float(ack_hours)
    if resolve_days:
        if resolve_days > rd and sec["legal"]:
            notes.append(f"Hal {resolve_days:g} din niyam ({rd:g}) se zyada: {rd:g} din rakha.")
        else:
            rd = float(resolve_days)
    return {"ack_hours": ah, "resolve_days": rd, "notes": notes}


def deadlines(received: datetime, sector: str, ack_hours: float | None = None, resolve_days: float | None = None,
              severity: str = "normal") -> dict[str, Any]:
    t = targets(sector, ack_hours, resolve_days)
    ah, rd = t["ack_hours"], t["resolve_days"]
    if severity == "urgent":
        ah, rd = min(ah, 4.0), min(rd, 2.0)
    elif severity == "high":
        ah, rd = min(ah, 12.0), min(rd, max(3.0, rd / 2))
    return {"ack_by": received + timedelta(hours=ah), "due_at": received + timedelta(days=rd), "ack_hours": ah,
            "resolve_days": rd, "notes": t["notes"]}


def guess_causes(text: str) -> list[str]:
    low = " " + str(text or "").lower() + " "
    hits = []
    for k, words in CAUSES.items():
        if any(w in low for w in words):
            hits.append(k)
    return hits[:3] or ["other"]


def guess_severity(text: str) -> tuple[str, list[str]]:
    low = str(text or "").lower()
    flags = []
    if any(w in low for w in URGENT_WORDS):
        flags.append("safety")
    if any(w in low for w in LEGAL_WORDS):
        flags.append("legal_threat")
    if any(w in low for w in ANGRY_WORDS) or low.count("!") >= 3:
        flags.append("angry")
    if "safety" in flags:
        return "urgent", flags
    if "legal_threat" in flags:
        return "high", flags
    return "normal", flags


def commission_for(amount: float) -> str:
    """Pecuniary limits (Consumer Protection (Jurisdiction ...) Rules 2021): by the value paid for the goods / services."""
    a = float(amount or 0)
    if a <= 50_00_000:
        return "District Commission"
    if a <= 2_00_00_000:
        return "State Commission"
    return "National Commission"


def limitation(cause_on: date) -> date:
    """Consumer Protection Act 2019 Sec 69: two years from the day the cause arose."""
    try:
        return cause_on.replace(year=cause_on.year + 2)
    except ValueError:
        return cause_on + timedelta(days=730)


def routes_for(sector: str) -> list[dict[str, str]]:
    sec = SECTORS.get(sector) or SECTORS["general"]
    return [ROUTES[r] | {"id": r} for r in sec["routes"] if r in ROUTES]


def route_line(sector: str) -> str:
    """The honest last line of a final reply (regulated sectors must name the next step)."""
    rs = routes_for(sector)
    if not rs:
        return ""
    return "Agar aap is jawab se santusht nahi hain, to aap " + "; ya ".join(f"{r['name']} ({r['how']})" for r in rs[:2]) + " se sampark kar sakte hain."


# ---------------------------------------------------------------- privacy: what never stays in a complaint
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)")
_OTP = re.compile(r"\b(otp|pin|cvv|password|passcode|mpin|upi pin)\b\W{0,6}\w{0,12}\W{0,3}\d{3,8}", re.I)
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def scrub(text: str) -> tuple[str, bool]:
    """Card / account / Aadhaar-length numbers, OTP / PIN / password values, PAN -> '[hataya]'."""
    t = str(text or "")
    out = _OTP.sub(lambda m: m.group(1) + " [hataya]", t)
    out = _CARD.sub("[hataya]", out)
    out = _PAN.sub("[hataya]", out)
    return out, out != t


MONEY_RE = re.compile(r"(₹|\brs\.?\b|\brupee|\brupay|\brefund|\bdiscount|\bchhoot|\bcashback|\bvoucher|\bmuft|\bfree\b|\breplace)", re.I)
PROMISE_RE = re.compile(r"\b(guarantee|pakka|100\s*%|kabhi nahi hoga|never again)\b", re.I)
