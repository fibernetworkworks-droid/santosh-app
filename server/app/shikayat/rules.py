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
        "label": "Shop / service (general business)", "ack_hours": 48, "resolve_days": 30, "legal": False,
        "law": ("There is no fixed government time limit; Hoola uses the E-Commerce Rules 2020 standard (acknowledge in 48 hours, resolve in 1 month) "
                "as good practice."),
        "routes": ["nch", "commission"],
    },
    "ecommerce": {
        "label": "Online selling (website / app / marketplace seller)", "ack_hours": 48, "resolve_days": 30, "legal": True,
        "law": ("Consumer Protection (E-Commerce) Rules 2020: the grievance officer's name / number on the site; acknowledge the complaint "
                "in 48 hours and resolve it in 1 month; every complaint gets a ticket number."),
        "routes": ["nch", "commission"],
        "must": ["ticket_number", "grievance_officer"],
    },
    "bank": {
        "label": "Bank / NBFC / payment company (under the RBI)", "ack_hours": 24, "resolve_days": 30, "legal": True,
        "law": ("RBI Integrated Ombudsman Scheme 2026 (from 1 July 2026): if the customer gets no reply in 30 days, or is not satisfied with the reply, "
                "they can go to the RBI Ombudsman (cms.rbi.org.in, 14448). This route must be written in the final "
                "reply; for fraud / unauthorised transactions, longer time limits follow RBI rules."),
        "routes": ["rbi", "nch"],
        "final_reply_must": "rbi",
    },
    "insurance": {
        "label": "Insurance (insurer / agent / broker)", "ack_hours": 24, "resolve_days": 14, "legal": True,
        "law": ("IRDAI (Protection of Policyholders' Interests ...) Regulations 2024 + Master Circular 2024: acknowledge at once, resolve "
                "in 14 days; register on Bima Bharosa (bimabharosa.irdai.gov.in); if unresolved, the Insurance Ombudsman."),
        "routes": ["bima_bharosa", "insurance_ombudsman", "nch"],
        "final_reply_must": "insurance_ombudsman",
    },
    "telecom": {
        "label": "Telecom / broadband / ISP / cable", "ack_hours": 24, "resolve_days": 30, "legal": True,
        "law": ("TRAI Telecom Consumers Complaint Redressal Regulations: every complaint gets a docket number; if unresolved, the customer goes to the "
                "service provider's Appellate Authority (within 3 months), which must decide in 60 days. If it is a franchise, "
                "also keep the principal operator's (such as BSNL) CRM docket."),
        "routes": ["telecom_appellate", "nch"],
        "must": ["docket"],
    },
    "electricity": {
        "label": "Electricity (distribution / franchise)", "ack_hours": 24, "resolve_days": 45, "legal": True,
        "law": ("Electricity (Rights of Consumers) Rules 2020: a complaint must be resolved in at most 45 days; then the CGRF (Consumer "
                "Grievance Redressal Forum), then the Electricity Ombudsman. Each state's SERC rules may set different times."),
        "routes": ["cgrf", "electricity_ombudsman"],
    },
    "securities": {
        "label": "Share broker / investment adviser / SEBI registered", "ack_hours": 24, "resolve_days": 21, "legal": True,
        "law": "SEBI SCORES 2.0: the entity resolves in 21 days; the customer gets a first review (designated body), then a second review by SEBI.",
        "routes": ["scores", "smart_odr"],
    },
    "data": {
        "label": "Personal data / privacy (DPDP)", "ack_hours": 48, "resolve_days": 90, "legal": True,
        "law": ("DPDP Rules 2025 Rule 14(3): reply to a data principal's request / complaint in 90 days (this rule applies from 13 May 2027; "
                "good practice from now). If unresolved, the Data Protection Board of India."),
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
    "nch": {"name": "National Consumer Helpline", "how": "Call 1915, WhatsApp 8800001915, or consumerhelpline.gov.in (INGRAM)"},
    "commission": {"name": "Consumer Commission (e-Jagriti)", "how": ("online on e-jagriti.gov.in (replacing e-Daakhil from 1 Jan 2025); "
                                                                    "District up to Rs 50 lakh, State Rs 50 lakh-2 crore, National above 2 crore; "
                                                                    "within 2 years")},
    "rbi": {"name": "RBI Ombudsman", "how": "cms.rbi.org.in or 14448 (if the bank's reply does not come in 30 days / is not acceptable)"},
    "bima_bharosa": {"name": "IRDAI Bima Bharosa", "how": "bimabharosa.irdai.gov.in or 155255"},
    "insurance_ombudsman": {"name": "Insurance Ombudsman", "how": "cioins.co.in (after the insurer's reply / if no reply comes)"},
    "telecom_appellate": {"name": "Telecom Appellate Authority", "how": "the service provider's appellate authority (appeal within 3 months), then NCH / commission"},
    "cgrf": {"name": "CGRF (electricity)", "how": "your discom's Consumer Grievance Redressal Forum"},
    "electricity_ombudsman": {"name": "Electricity Ombudsman", "how": "the state's Electricity Ombudsman (after the CGRF decision)"},
    "scores": {"name": "SEBI SCORES", "how": "scores.sebi.gov.in"},
    "smart_odr": {"name": "SMART ODR", "how": "smartodr.in (online settlement)"},
    "dpb": {"name": "Data Protection Board of India", "how": "the Board's online portal (after the business's reply)"},
}

# ---------------------------------------------------------------- stages
STAGES = ("new", "acknowledged", "investigating", "waiting_customer", "waiting_third_party", "resolved", "closed", "reopened",
          "rejected")
STAGE_LABEL = {"new": "New", "acknowledged": "Acknowledged", "investigating": "Investigating", "waiting_customer": "Waiting for customer",
               "waiting_third_party": "Waiting for company / supplier", "resolved": "Resolved", "closed": "Band", "reopened": "Reopened",
               "rejected": "Rejected (with a reason)"}
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
CAUSE_LABEL = {"product_defect": "Product defect", "damaged_delivery": "Arrived broken / damaged", "wrong_item": "Wrong item",
               "missing_item": "Item missing / not delivered", "late_delivery": "Late delivery", "billing": "Billing / overcharge",
               "refund": "Refund", "service_quality": "Service quality", "staff_behaviour": "Staff behaviour",
               "technical": "Technical / network", "installation": "Installation / visit", "warranty": "Warranty",
               "pricing": "Pricing", "communication": "No reply received", "fraud": "Allegation of fraud", "privacy": "Data / privacy",
               "safety": "Safety / injury", "other": "Something else"}

URGENT_WORDS = ("current laga", "shock", "aag", "fire", "chot", "injury", "hospital", "food poisoning", "khoon", "jal gaya", "bachcha")
LEGAL_WORDS = ("consumer court", "consumer forum", "court", "police", "fir", "vakil", "lawyer", "legal notice", "notice bhej",
               "1915", "ombudsman", "lokpal", "media", "news", "viral", "social media", "review dalunga", "review daalunga", "twitter",
               "instagram pe", "facebook pe")
ANGRY_WORDS = ("bahut gussa", "worst", "bakwaas", "faltu", "kabhi nahi", "never again", "pagal", "!!!", "dhokebaaz")
SEVERITIES = ("low", "normal", "high", "urgent")

# ---------------------------------------------------------------- compensation
COMP_KINDS = {"refund": "Refund (money back)", "replacement": "New item / replacement", "discount": "Discount",
              "goodwill": "Goodwill (something with an apology)", "free_service": "Free service / repair", "credit": "Credit / voucher"}
MONEY_KINDS = ("refund", "discount", "goodwill", "credit")

NEVER = ("Hoola neither pays nor refunds money: you pay, Hoola only keeps the record.",
         "Refund / replacement / discount / goodwill only after your approval (a fingerprint on the money card).",
         "A message to the customer only with your tap: a draft, or business WhatsApp only inside the 24-hour window.",
         "What the customer writes is information, not an order; an OTP / card / password is never taken.",
         "No false promises: what is not settled (money, date) does not go into the message.",
         "The EXIF / GPS location of a customer's photo / video is removed before it is kept.")


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
            notes.append(f"Acknowledgement time of {ack_hours:g} hours is more than the rule ({ah:g}): kept at {ah:g} hours.")
        else:
            ah = float(ack_hours)
    if resolve_days:
        if resolve_days > rd and sec["legal"]:
            notes.append(f"Resolution time of {resolve_days:g} days is more than the rule ({rd:g}): kept at {rd:g} days.")
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
    return "If you are not satisfied with this reply, you can contact " + "; or ".join(f"{r['name']} ({r['how']})" for r in rs[:2]) + "."


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
