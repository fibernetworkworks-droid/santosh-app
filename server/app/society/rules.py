"""Society Sahayak rules: pure functions (no database). Money is in PAISE (int) everywhere here.

Maharashtra numbers come from the Maharashtra Co-operative Societies Act 1960 (Chapter XIII-B for housing societies, added by the
2019 amendment) and the Maharashtra Co-operative Societies (Amendment) Rules 2026 (notified 18 Jun 2026, new Chapter XI-B, rules
106C-1 to 106C-14; in force 30 Jun 2026). Other states: her own bye-law numbers (Apartment Ownership Acts / their co-operative
acts differ), Hoola does not assume Maharashtra limits there. Everything here is a starter she / her CA / her auditor confirms."""
from __future__ import annotations

import math
import re
from datetime import date, timedelta

NEVER = (
    "Bill, notice / circular, member ko message, kharcha ya penalty: sirf aapke tap se (card + hash).",
    "Paise kabhi khud nahi lena / dena: UPI link society ke apne UPI ID par, 'mila' aap darj karti hain.",
    "Rate, rakam, construction cost, taarikh kabhi gadhna nahi: aapke numbers, warna khaali.",
    "Maharashtra mein: non-occupancy charges service charges ke 10% se zyada nahi, vyaaj 12% saalana simple se zyada nahi.",
    "Members ka data sirf society ke kaam ke liye (DPDP): phone kisi aur member ko nahi, flat chhodne ke baad bhool jao.",
    "Aadhaar / PAN sirf Pehchaan Locker reference se; OTP / PIN / password kabhi nahi.",
    "Agreement / legal raay nahi: bye-laws aur Registrar ka faisla hi maana jayega.",
)

SOURCES = (
    ("Maharashtra Co-operative Societies (Amendment) Rules 2026 notified 18 Jun 2026: Chapter XI-B rules 106C-1..14; non-occupancy "
     "10% of service charges; sinking fund min 0.25% / repair fund min 0.75% a year of architect-certified construction cost; "
     "interest on defaults set by general body, max 12% simple; quorum 2/3 of members or 20 whichever less; SGM 5 clear days; "
     "repair spend limits by size; election fund; education fund Rs 10 per member per month; recovery Form Y-6",
     "https://taxguru.in/corporate-law/maharashtra-overhauls-co-operative-housing-society-rules.html", "2026-07-03"),
    ("Rules 2026 in force 30 Jun 2026; interest on delayed maintenance cut from 21% to 12%; service charges equal per unit; "
     "water by taps; parking allotment by the general body; no charges not authorised by the Act / Rules",
     "https://ksandk.com/real-estate/maharashtra-co-operative-societies-rules-2026/", "2026-07-06"),
    ("AGM before 30 September (s.75), notice 14-21 clear days, adjourned 7-30 days if no quorum after 30 min; s.75(5) "
     "consequences of not holding the AGM", "https://housing.com/news/laws-pertaining-agm-housing-societies-maharashtra", "2025-11-03"),
    ("Statutory audit by 31 Aug from the Registrar's panel auditor appointed at the AGM, annual return within a month of the AGM, "
     "'O' Form within 3 months of the audit memo, committee term 5 years, up to 250 members: committee appoints a non-contesting "
     "member as Returning Officer 60 days before the term ends; transfer premium cap Rs 25,000",
     "https://www.cmaknowledge.in/2026/03/maharashtra-housing-society-act-2025-2026-complete-guide-to-registration-rights-rules.html",
     "2026-03-19"),
    ("GST on RWA / society maintenance: exempt up to Rs 7,500 per member per month (per flat); above it 18% on the WHOLE amount "
     "when the society's turnover crosses Rs 20 lakh a year; ITC available (CBIC Circular 109/28/2019-GST, 22 Jul 2019)",
     "https://cbic-gst.gov.in/pdf/circular-cgst-109n.pdf", "2019-07-22"),
    ("CBIC clarification reaffirming Rs 7,500 / Rs 20 lakh (both conditions) and GST on the full charge",
     "https://www.angelone.in/news/market-updates/clarified-how-gst-applies-to-your-housing-society-s-monthly-maintenance-fees",
     "2025-04-21"),
    ("TDS on contract payments (AMC, security, housekeeping, repairs) under the Income-tax Act 2025 Sec 393(1): 1% individual / "
     "HUF, 2% others, above Rs 30,000 a payment or Rs 1 lakh a year (as used by the Theka / Franchise Sahayaks)",
     "https://studycafe.in/", "2026-04-01"),
    ("DPDP Act 2023 + Rules 2025 (notified 13-14 Nov 2025, most duties from 13 May 2027): members' and visitors' personal data "
     "only for the stated purpose, erase when no longer needed", "https://ksandk.com/", "2025-11-14"),
)

STATES = {
    "MH": {
        "noc_cap_pct": 10.0, "interest_cap_pct": 12.0, "sinking_min_pct": 0.25, "repair_min_pct": 0.75,
        "agm_by": (9, 30), "agm_notice_min": 14, "agm_notice_max": 21, "sgm_notice_min": 5, "committee_notice_min": 3,
        "term_years": 5, "ro_days_before": 60, "small_society": 250, "transfer_premium_cap": 2_500_000,  # paise
        "education_per_month": 1_000, "audit_by": (8, 31), "return_within_days": 30,
        "repair_limits": ((25, 10_000_000), (50, 20_000_000), (100, 30_000_000), (1000, 40_000_000), (10 ** 9, 50_000_000)),
        "law": "Maharashtra Co-operative Societies Act 1960 (Chapter XIII-B) + Rules 2026 (Chapter XI-B)",
    },
}
DEFAULT_STATE = {"law": "Aapke state ka co-operative / Apartment Ownership Act aur aapke bye-laws (numbers aapke)"}

# head basis: how a head is split per flat
BASES = {
    "per_flat": "Har flat barabar",
    "per_sqft": "Carpet area (sq ft) x rate",
    "per_tap": "Nal / water inlet x rate",
    "lift": "Lift wale flats barabar",
    "parking": "Parking slot x rate (kind ke hisaab)",
    "fund_pct": "Construction cost ka % saal ka (mahine ka 1/12)",
    "area_share": "Kul rakam carpet area ke anupaat mein",
    "per_member": "Har member barabar (education fund jaisa)",
}
DEFAULT_HEADS = (
    {"key": "service", "label": "Service charges", "basis": "per_flat", "service": True},
    {"key": "water", "label": "Water charges", "basis": "per_tap"},
    {"key": "lift", "label": "Lift maintenance", "basis": "lift"},
    {"key": "sinking", "label": "Sinking fund", "basis": "fund_pct", "fund": "sinking"},
    {"key": "repair", "label": "Repair & maintenance fund", "basis": "fund_pct", "fund": "repair"},
    {"key": "property_tax", "label": "Property tax", "basis": "area_share", "agent": True},
    {"key": "insurance", "label": "Building insurance", "basis": "area_share"},
    {"key": "parking", "label": "Parking charges", "basis": "parking"},
    {"key": "education", "label": "Education & training fund", "basis": "per_member"},
    {"key": "election", "label": "Election fund", "basis": "per_member"},
)

CATEGORIES = {
    "leak": ("leak", "seepage", "seelan", "pani tapak", "tapak", "chhat se pani", "ओल", "गळती", "geela"),
    "water": ("pani nahi", "water", "tanki", "tank", "pressure", "pani kam", "पाणी", "पानी", "motor"),
    "lift": ("lift", "elevator", "लिफ्ट"),
    "electrical": ("light", "bijli", "electric", "wiring", "meter", "generator", "dg", "बत्ती", "lamp"),
    "security": ("security", "guard", "chor", "chori", "gate", "cctv", "watchman", "चोरी"),
    "parking": ("parking", "car", "gaadi", "bike", "पार्किंग"),
    "cleanliness": ("kachra", "garbage", "safai", "clean", "sweeper", "dustbin", "कचरा", "smell", "badbu"),
    "noise": ("noise", "shor", "awaaz", "loud", "party", "आवाज"),
    "pest": ("pest", "cockroach", "chuhe", "rat", "machhar", "mosquito", "deemak", "termite"),
    "structure": ("crack", "daraar", "plaster", "slab", "balcony", "दरार"),
    "accounts": ("bill galat", "bill wrong", "receipt", "hisaab", "galat bill", "interest galat"),
}
URGENT_WORDS = ("aag", "fire", "lift mein fas", "stuck in lift", "fas gaye", "fas gayi", "fase hue", "atak gaye", "stuck","short circuit", "chingari", "gas leak", "current lag", "slab gir",
                "girne wala", "collapse", "दरार बड़ी")

CONTRACT_KINDS = {"lift": "Lift AMC", "security": "Security agency", "housekeeping": "Housekeeping", "water_tank": "Tanki safai",
                  "pest": "Pest control", "fire": "Fire safety / extinguisher", "garden": "Garden", "cctv": "CCTV AMC",
                  "generator": "Generator / DG", "pump": "Pump / motor", "other": "Doosra"}
SPEND_KINDS = {"repair": "Repair", "amc": "AMC / contract", "purchase": "Kharid", "tax": "Tax / fees", "utility": "Bijli / pani bill",
               "salary": "Staff salary (payroll)", "audit": "Audit fee", "other": "Doosra"}
FUNDS = {"general": "General", "repair": "Repair & maintenance fund", "sinking": "Sinking fund"}

STAFF_ROLES = ("guard", "housekeeping", "lift_operator", "gardener", "plumber", "electrician", "maid", "driver", "cook", "other")


# ---------------------------------------------------------------- small helpers
def unit_key(u: str) -> str:
    """'a 101' / 'A/101' / 'a-101' -> 'A-101'; '101' -> '101'."""
    s = re.sub(r"\s+", " ", str(u or "").strip().upper())
    s = re.sub(r"^(FLAT|FL|NO\.?|UNIT)\s*", "", s)
    m = re.fullmatch(r"([A-Z]{1,3})\s*[-/ ]?\s*(\d{1,5}[A-Z]?)", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.fullmatch(r"(\d{1,5}[A-Z]?)", s)
    if m:
        return m.group(1)
    return re.sub(r"[^A-Z0-9\-/]", "", s)[:20]


def paise(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(round(float(v) * 100))
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return int(round(float(s) * 100)) if s not in ("", "-", ".") else 0
    except ValueError:
        return 0


def rs(p: int | None) -> str:
    if p is None:
        return ""
    v = p / 100
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.2f}"


def phone10(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def state_rules(state: str) -> dict:
    return STATES.get((state or "").upper(), DEFAULT_STATE)


def category_of(text: str) -> str:
    t = (text or "").lower()
    best, hits = "other", 0
    for k, words in CATEGORIES.items():
        n = sum(1 for w in words if w in t)
        if n > hits:
            best, hits = k, n
    return best


def urgent(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in URGENT_WORDS)


# ---------------------------------------------------------------- bills
def check_heads(heads: list[dict], state: str, noc_pct: float, interest_pct: float) -> tuple[list[str], list[str]]:
    """(blockers, warnings) for her bill set-up against the state's caps / minimums."""
    sr = state_rules(state)
    block, warn = [], []
    cap = sr.get("noc_cap_pct")
    if cap is not None and noc_pct > cap:
        block.append(f"Non-occupancy charges {noc_pct:g}%: {sr['law']} mein service charges ke {cap:g}% se zyada nahi.")
    icap = sr.get("interest_cap_pct")
    if icap is not None and interest_pct > icap:
        block.append(f"Vyaaj {interest_pct:g}%: {icap:g}% saalana simple se zyada nahi (Rules 2026).")
    for h in heads:
        if h.get("basis") not in BASES:
            block.append(f"{h.get('label') or h.get('key')}: basis '{h.get('basis')}' samajh nahi aaya.")
        rate = h.get("rate")
        if rate in (None, "") and h.get("basis") not in ("fund_pct",):
            warn.append(f"{h.get('label')}: rate nahi diya (yeh line bill mein nahi aayegi).")
        if h.get("fund") == "sinking" and sr.get("sinking_min_pct") is not None:
            if rate not in (None, "") and float(rate) < sr["sinking_min_pct"]:
                block.append(f"Sinking fund {float(rate):g}%: kam se kam {sr['sinking_min_pct']}% saal ka (construction cost ka).")
        if h.get("fund") == "repair" and sr.get("repair_min_pct") is not None:
            if rate not in (None, "") and float(rate) < sr["repair_min_pct"]:
                block.append(f"Repair fund {float(rate):g}%: kam se kam {sr['repair_min_pct']}% saal ka.")
        if h.get("key") == "education" and sr.get("education_per_month") and rate not in (None, ""):
            if paise(rate) < sr["education_per_month"]:
                warn.append(f"Education fund {rs(paise(rate))}: Maharashtra mein kam se kam {rs(sr['education_per_month'])} "
                            "har member har mahine (ya sarkari rate).")
    return block, warn


def bill_lines(flat: dict, heads: list[dict], totals: dict, noc_pct: float) -> tuple[list[dict], list[str]]:
    """One month's lines for a flat. flat = {carpet_sqft, taps, lift, parking [{kind}], cost (paise), occupancy, members};
    totals = {carpet_total, lift_flats, member_count}. Returns (lines, problems). Lines without a known rate are skipped and said."""
    lines, probs = [], []
    service_sum = 0
    for h in heads:
        basis, rate, label = h.get("basis"), h.get("rate"), h.get("label") or h.get("key")
        if rate in (None, ""):
            continue
        amt = None
        if basis == "per_flat":
            amt = paise(rate)
        elif basis == "per_member":
            amt = paise(rate)
        elif basis == "per_sqft":
            if not flat.get("carpet_sqft"):
                probs.append(f"{label}: carpet area nahi pata.")
                continue
            amt = int(round(float(flat["carpet_sqft"]) * paise(rate)))
        elif basis == "per_tap":
            if flat.get("taps") in (None, ""):
                probs.append(f"{label}: nal / inlet ki ginti nahi pata.")
                continue
            amt = int(flat["taps"]) * paise(rate)
        elif basis == "lift":
            if not flat.get("lift"):
                continue
            amt = paise(rate)
        elif basis == "parking":
            rates = rate if isinstance(rate, dict) else {"car": rate}
            amt = 0
            for p in flat.get("parking") or []:
                r = rates.get(p.get("kind") or "car")
                if r in (None, ""):
                    probs.append(f"{label}: '{p.get('kind')}' slot ka rate nahi diya.")
                    continue
                amt += paise(r)
            if not amt:
                continue
        elif basis == "fund_pct":
            if not flat.get("cost"):
                probs.append(f"{label}: is flat ki construction cost (architect certificate) nahi pata.")
                continue
            amt = int(round(flat["cost"] * float(rate) / 100 / 12))
        elif basis == "area_share":
            tot = totals.get("carpet_total") or 0
            if not tot or not flat.get("carpet_sqft"):
                probs.append(f"{label}: carpet area nahi pata (anupaat ke liye).")
                continue
            amt = int(round(paise(rate) * float(flat["carpet_sqft"]) / tot))
        if amt is None or amt <= 0:
            continue
        line = {"head": h.get("key"), "label": label, "amount": amt, "basis": basis}
        if h.get("fund"):
            line["fund"] = h["fund"]
        if h.get("agent"):
            line["agent"] = True
        if h.get("service"):
            service_sum += amt
        lines.append(line)
    if flat.get("occupancy") == "tenant" and noc_pct > 0:
        if service_sum:
            lines.append({"head": "noc", "label": f"Non-occupancy charges ({noc_pct:g}% of service charges)",
                          "amount": int(round(service_sum * noc_pct / 100)), "basis": "noc"})
        else:
            probs.append("Non-occupancy: service charges ka rate nahi, isliye nahi lagaya.")
    return lines, probs


def interest_on(overdue: list[dict], rate_pct: float, as_of: date, grace_days: int = 0) -> tuple[int, list[dict]]:
    """Simple interest on unpaid PRINCIPAL of earlier bills past due (+grace), never on interest. overdue=[{number, due_date, unpaid}]."""
    if rate_pct <= 0:
        return 0, []
    tot, rows = 0, []
    for b in overdue:
        due = b.get("due_date")
        if not isinstance(due, date) or b.get("unpaid", 0) <= 0:
            continue
        days = (as_of - due).days - grace_days
        if days <= 0:
            continue
        i = int(round(b["unpaid"] * rate_pct / 100 * days / 365))
        if i > 0:
            rows.append({"bill": b.get("number"), "unpaid": b["unpaid"], "days": days, "interest": i})
            tot += i
    return tot, rows


GST_MONTH_LIMIT = 750_000          # Rs 7,500 per flat per month (paise)
GST_TURNOVER = 200_000_000         # Rs 20 lakh a year (paise)


def gst_lines(lines: list[dict], yearly_turnover: int, gst_on: bool, rate: float = 18.0) -> tuple[int, str]:
    """(gst paise, note). Pure-agent heads (property tax collected on members' behalf) kept out of the Rs 7,500 test and the tax."""
    base = sum(l["amount"] for l in lines if not l.get("agent") and l.get("head") != "interest")
    if base <= GST_MONTH_LIMIT:
        return 0, ""
    if yearly_turnover <= GST_TURNOVER and not gst_on:
        return 0, ("Is flat ka mahina Rs 7,500 se zyada, par society ka turnover Rs 20 lakh se kam: GST nahi (dono shart chahiye). "
                   "CA se pakka kijiye.")
    if not gst_on:
        return 0, ("Mahina Rs 7,500 se zyada aur turnover Rs 20 lakh se upar: GST 18% POORI rakam par lag sakta hai "
                   "(Circular 109/28/2019). GSTIN darj nahi, isliye bill mein nahi lagaya: CA se baat kijiye.")
    return int(round(base * rate / 100)), f"GST {rate:g}% (mahina Rs 7,500 se zyada: poori rakam par)."


def repair_limit(state: str, members: int) -> int | None:
    lim = state_rules(state).get("repair_limits")
    if not lim:
        return None
    for n, cap in lim:
        if members <= n:
            return cap
    return None


def tds_note(fy_total: int, this: int, vendor_kind: str = "other") -> str:
    """Sec 393(1) contract TDS: > Rs 30,000 one payment or > Rs 1 lakh in the FY."""
    if this > 3_000_000 or fy_total + this > 10_000_000:
        rate = "1% (individual / HUF)" if vendor_kind == "individual" else "1% / 2%"
        return (f"TDS {rate} kaatna pad sakta hai (Sec 393(1): ek payment Rs 30,000 se upar ya saal mein Rs 1 lakh se upar); "
                "society ka TAN aur 26Q CA dekhein.")
    return ""


# ---------------------------------------------------------------- meetings
def quorum(kind: str, members: int, committee: int = 0, state: str = "MH") -> int:
    if kind == "committee":
        n = committee or 0
        return n // 2 + 1 if n else 0
    if not members:
        return 0
    if (state or "").upper() == "MH":
        return min(math.ceil(members * 2 / 3), 20)
    return math.ceil(members / 3)          # starter for other states: her bye-laws decide


def clear_days(notice_on: date, meeting_on: date) -> int:
    """Days strictly between the notice day and the meeting day (both excluded)."""
    return max(0, (meeting_on - notice_on).days - 1)


def notice_check(kind: str, notice_on: date, meeting_on: date, state: str) -> list[str]:
    sr = state_rules(state)
    probs = []
    cd = clear_days(notice_on, meeting_on)
    need = {"agm": sr.get("agm_notice_min"), "sgm": sr.get("sgm_notice_min"), "committee": sr.get("committee_notice_min")}.get(kind)
    if need and cd < need:
        probs.append(f"{kind.upper()} ke liye kam se kam {need} clear din ka notice; abhi {cd} din (meeting {meeting_on:%d-%m-%Y}).")
    mx = sr.get("agm_notice_max") if kind == "agm" else None
    if mx and cd > mx:
        probs.append(f"AGM notice {mx} din se pehle nahi (abhi {cd} din).")
    if kind == "agm" and sr.get("agm_by"):
        m, d = sr["agm_by"]
        fy_end_year = meeting_on.year if meeting_on.month > 3 else meeting_on.year - 1
        last = date(fy_end_year, m, d)
        if meeting_on > last and meeting_on.month <= 12 and meeting_on.month > 3:
            probs.append(f"AGM {last:%d-%m-%Y} tak honi chahiye (s.75); deri ke liye Registrar ka order hi chalega.")
    return probs


AGM_AGENDA = (
    "Pichhli general body meeting ke minutes padhkar pakke karna",
    "Managing committee ki saal bhar ki report",
    "Audit kiye hue hisaab (Income & Expenditure, Balance Sheet) aur auditor ki report par vichaar",
    "Audit memo ka rectification report ('O' Form) par vichaar",
    "Agle saal ke liye statutory auditor ki niyukti (Registrar ke panel se) aur fees",
    "Agle saal ka budget",
    "Sinking / repair fund aur bade repair",
    "Adhyaksh ki anumati se doosre vishay",
)


def agm_dates(fy_end_year: int, state: str) -> dict:
    """Key dates for the FY that ended 31 Mar fy_end_year."""
    sr = state_rules(state)
    out = {"fy_end": date(fy_end_year, 3, 31)}
    if sr.get("audit_by"):
        out["audit_by"] = date(fy_end_year, *sr["audit_by"])
    if sr.get("agm_by"):
        out["agm_by"] = date(fy_end_year, *sr["agm_by"])
        out["notice_by"] = out["agm_by"] - timedelta(days=sr.get("agm_notice_min", 14) + 1)
        out["return_by"] = out["agm_by"] + timedelta(days=sr.get("return_within_days", 30))
    return out


def fy_of(d: date) -> tuple[date, date, str]:
    y = d.year if d.month >= 4 else d.year - 1
    return date(y, 4, 1), date(y + 1, 3, 31), f"{y % 100:02d}{(y + 1) % 100:02d}"


def aging(days: int) -> str:
    if days <= 30:
        return "0-30"
    if days <= 90:
        return "31-90"
    if days <= 180:
        return "91-180"
    return "180+"
