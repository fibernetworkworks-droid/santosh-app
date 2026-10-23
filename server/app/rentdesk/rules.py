"""Rentdesk Sahayak rules: Indian rental law notes, tax notes (TDS / GST / HRA receipts), checklists, repair words, small parsers.

Everything here is plain-words guidance with dated sources, never legal or tax advice: the agreement is a draft for her lawyer,
tax treatment is for her CA. Numbers she must give (stamp duty, registration fee, rent, deposit) are never invented here."""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

NEVER = (
    "Kirayedar ko koi message khud nahi bhejna: har message draft, sirf aapke tap se jaata hai.",
    "Deposit se koi katauti, kiraya badhana / notice, ya repair ka kharcha: sirf aapki haan (app ka card) se.",
    "Paise kabhi khud nahi lena / dena: UPI link aapke UPI ID par, 'mila' aap batati hain; Galla ki UPI sirf ishaara.",
    "Stamp duty, registration fee, kiraya, deposit, area: sirf aapke number; Hoola gadhta nahi.",
    "Aadhaar / PAN sirf Pehchaan Locker mein (masked reference); OTP / PIN / password kabhi nahi.",
    "IGR / police / RERA / municipal portal scrape nahi: aap khud login karti hain (OTP / biometric aapka / kirayedar ka).",
    "Agreement sirf draft hai (vakil se pakka karwaiye), kanooni salah nahi.",
)

# (what, url, date checked / published)
SOURCES = (
    ("Maharashtra Rent Control Act 1999 s.55: L&L / tenancy agreement in writing + registered; landlord's duty; without it "
     "the tenant's version prevails; up to 3 months jail / Rs 5,000 fine", "https://www.advocatekhoj.com/library/bareacts/maharashtrarentcontrol/55.php",
     "checked 23 Oct 2026"),
    ("Maharashtra IGR online leave & licence e-registration (draft, stamp duty, fee, Aadhaar e-KYC, no sub-registrar visit)",
     "https://rentu.in/news/10001371/maharashtra-pushes-online-registration-of-leave-and-licence-agreements", "27 May 2026"),
    ("Leave and Licence 2.0: registered L&L tenant data shared with police (CCTNS); BNS s.223 cases for not giving tenant details",
     "https://www.punekarnews.in/?p=208283", "3 Jun 2025"),
    ("Model Tenancy Act 2021 adopted / aligned: only a few states / UTs (Assam, Arunachal, A&N, DNH&DD, Lakshadweep; UP, AP, TN, "
     "Uttarakhand on older versions); viral 'rent rules 2026' are not a national law", "https://addressadvisors.com/news/new-rent-rules-2026-social-media-claims-dont-match-reality",
     "Sep 2026"),
    ("Rajya Sabha reply 25 Jul 2022: UP, Assam, AP, TN revised tenancy acts on MTA lines",
     "https://housing.com/news/only-4-states-have-adopted-model-tenancy-act-rajya-sabha-told/", "25 Jul 2022"),
    ("TDS on rent, Income-tax Act 2025 s.393(1) Table 2(ii).D(b) (old 194-I(b)): 10% land / building above Rs 50,000 a month, "
     "from 1 Apr 2026", "https://blog.tdsman.com/2026/06/tds-on-rent-section-3931-section-194i-a-b/", "Jun 2026"),
    ("Form 141 (unified challan-cum-statement, replaces 26QB / 26QC): rent paid by an individual / HUF = s.393(1) Table 2(i), "
     "Schedule A", "https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/form-141-challan-cum-statement-deduction-tax-us-3931-UM",
     "checked 23 Oct 2026"),
    ("Old 194-IB (individual / HUF tenant not under audit): 2% when rent > Rs 50,000 a month, once in the last month of the year "
     "/ tenancy; 20% without PAN capped at the last month's rent", "https://www.incometaxindia.gov.in/w/tds-on-rent-by-certain-individual-or-huf",
     "checked 23 Oct 2026"),
    ("HRA from 1 Apr 2026: Form 124 (replaces 12BB) asks landlord name, address, PAN (rent > Rs 1 lakh a year) and relationship; "
     "agreement + monthly receipts; 50% metro list adds Bengaluru, Hyderabad, Pune, Ahmedabad",
     "https://uatcdn.angelone.in/news/taxation/new-hra-rules-from-april-1-2026-pan-and-rent-proof-now-mandatory", "1 Apr 2026"),
    ("GST: RCM on commercial (non-residential) rent from an unregistered landlord to a registered tenant from 10 Oct 2024; "
     "composition tenants excluded from 16 Jan 2025 (Notfn 07/2025-CT(R)); 18%", "https://cleartax.in/s/rcm-on-rent-of-commercial-property-under-gst",
     "checked 23 Oct 2026"),
    ("GST: hostel / PG accommodation up to Rs 20,000 per person per month, stay of 90 days or more, exempt (from 15 Jul 2024)",
     "https://www.bajajfinserv.in/gst-on-hostel", "18 Jun 2026"),
    ("DPDP Act 2023 + Rules 2025 (notified Nov 2025, most duties from 13 May 2027): purpose limit, erase when the purpose is over",
     "https://www.meity.gov.in/data-protection-framework", "checked 23 Oct 2026"),
)

# state notes. Only facts we have sources for; else "aapke rajya ka kanoon / vakil".
MTA_STATES = {"AS", "AR", "AN", "DN", "DD", "LD"}                  # MTA-aligned per Rajya Sabha / news (above)
OLD_MTA_STATES = {"UP", "AP", "TN", "UK"}                          # own acts on an older MTA draft
STATE_NAMES = {"MH": "Maharashtra", "KA": "Karnataka", "DL": "Delhi", "GJ": "Gujarat", "TN": "Tamil Nadu", "UP": "Uttar Pradesh",
               "AP": "Andhra Pradesh", "TG": "Telangana", "WB": "West Bengal", "RJ": "Rajasthan", "MP": "Madhya Pradesh", "AS": "Assam",
               "GA": "Goa", "KL": "Kerala", "PB": "Punjab", "HR": "Haryana", "UK": "Uttarakhand", "OD": "Odisha", "BR": "Bihar"}

UNIT_KINDS = {"flat": "Flat", "house": "Ghar", "room": "Room", "pg_bed": "PG / hostel bed", "shop": "Dukaan", "office": "Office",
              "godown": "Godown", "other": "Doosra"}
COMMERCIAL_KINDS = {"shop", "office", "godown"}
CHARGE_KINDS = {"rent": "Kiraya", "deposit": "Deposit", "maintenance": "Maintenance", "electricity": "Bijli", "water": "Paani",
                "late_fee": "Late fee", "repair": "Repair", "other": "Doosra"}
TRADES = {"plumber": "Plumber", "electrician": "Electrician", "carpenter": "Carpenter", "painter": "Painter", "appliance": "Appliance",
          "pest": "Pest control", "cleaning": "Safai", "gas": "Gas", "internet": "Internet", "civil": "Civil / mistri", "other": "Doosra"}

REPAIR_WORDS = {
    "plumber": ("nal", "tap", "leak", "pani tapak", "paani tapak", "pipe", "drain", "nali", "gutter", "flush", "toilet jam", "commode",
                "tanki", "tank", "geyser pipe", "basin", "choke", "block", "seepage", "seelan"),
    "electrician": ("bijli", "light", "switch", "socket", "mcb", "fuse", "wiring", "short", "current", "fan", "pankha", "tube", "bulb",
                    "meter", "inverter"),
    "appliance": ("geyser", "ac ", " ac", "fridge", "washing", "microwave", "ro ", "purifier", "chimney", "gas stove", "tv"),
    "carpenter": ("darwaza", "door", "lock", "taala", "tala", "khidki", "window", "almari", "wardrobe", "hinge", "drawer", "cupboard"),
    "painter": ("paint", "rang", "deewar", "diwar", "patch", "plaster"),
    "pest": ("cockroach", "keede", "dimak", "termite", "chuha", "rat", "pest", "machhar", "bed bug", "khatmal"),
    "gas": ("gas leak", "gas ki", "cylinder", "pipeline gas", "png"),
    "internet": ("wifi", "wi-fi", "internet", "broadband", "router"),
    "civil": ("crack", "daraar", "chhat", "roof", "tile", "floor", "waterproof"),
}
URGENT_WORDS = ("gas leak", "gas ki smell", "gas ki badboo", "aag", "fire", "short circuit", "spark", "chingari", "current lag", "shock",
                "pani bhar", "paani bhar", "flood", "chhat gir", "roof gir", "lift band", "taala toot", "chori", "break in")


def is_mta(state: str) -> bool:
    return (state or "").upper() in MTA_STATES


def state_label(state: str) -> str:
    return STATE_NAMES.get((state or "").upper(), state or "aapka rajya")


def default_kind(state: str) -> str:
    return "leave_licence" if (state or "").upper() == "MH" else ("mta" if is_mta(state) else "rent")


AGREEMENT_KINDS = {"leave_licence": "Leave & licence agreement", "rent": "Rent agreement", "mta": "Tenancy agreement (Model Tenancy Act)"}


# ---------------------------------------------------------------- parsers
def money(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    mult = 1.0
    m = re.search(r"(lakh|lac|l\b|k\b|hazar|hazaar|thousand)", s)
    if m:
        mult = 100000.0 if m.group(1) in ("lakh", "lac", "l") else 1000.0
    n = re.search(r"-?\d+(?:\.\d+)?", s)
    if not n:
        return 0.0
    return float(n.group()) * mult


def phone10(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else ""


def parse_date(v) -> date | None:
    from datetime import datetime
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s[:20], f).date()
        except ValueError:
            pass
    return None


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def end_of(start: date, months: int) -> date:
    return add_months(start, months) - timedelta(days=1)


def periods(start: date, end: date, upto: date) -> list[date]:
    """Licence-month starts from start, up to `upto` (inclusive) and never past the end."""
    out, i = [], 0
    while True:
        p = add_months(start, i)
        if p > upto or p > end:
            return out
        out.append(p)
        i += 1
        if i > 600:
            return out


def due_date(period_start: date, due_day: int, start: date) -> date:
    if not due_day:
        return period_start
    last = calendar.monthrange(period_start.year, period_start.month)[1]
    d = date(period_start.year, period_start.month, min(due_day, last))
    if d < period_start:          # e.g. licence month starts 20th, due day 5 -> 5th of the next month
        nxt = add_months(date(period_start.year, period_start.month, 1), 1)
        d = date(nxt.year, nxt.month, min(due_day, calendar.monthrange(nxt.year, nxt.month)[1]))
    return max(d, start)


def fy_of(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{str(y)[2:]}{str(y + 1)[2:]}"


def scrub(text: str, n: int = 2000) -> str:
    """Free text: OTP / PIN / password values, card-like runs, Aadhaar-like 12 digits and PAN are never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[hataya]", t)
    t = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[ID hataya]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN hataya]", t)
    return t.strip()[:n]


def repair_category(text: str) -> tuple[str, bool]:
    t = f" {str(text or '').lower()} "
    urgent = any(w in t for w in URGENT_WORDS)
    best, hits = "other", 0
    for k, words in REPAIR_WORDS.items():
        h = sum(1 for w in words if w in t)
        if h > hits:
            best, hits = k, h
    if "gas" in t and ("leak" in t or "smell" in t or "badboo" in t):
        best, urgent = "gas", True
    return best, urgent


# ---------------------------------------------------------------- checks
def deposit_check(state: str, use: str, rent: float, deposit: float) -> list[str]:
    out = []
    if rent <= 0 or deposit <= 0:
        return out
    months = deposit / rent
    if is_mta(state):
        cap = 2 if use == "residential" else 6
        if months > cap:
            out.append(f"Model Tenancy Act wale rajya ({state_label(state)}): deposit {cap} mahine tak ({months:.1f} mahine rakha hai). "
                       "Apne rajya ka kanoon / vakil se pakka kijiye.")
    elif months > 10:
        out.append(f"Deposit {months:.1f} mahine ke kiraye jitna: bahut zyada lagta hai, dobara dekhiye.")
    return out


def tds_note(tenant_kind: str, rent: float, use: str) -> str:
    if rent <= 50000:
        return "Kiraya Rs 50,000 mahina se kam: kirayedar par TDS nahi (dhara 393(1))."
    if tenant_kind in ("company", "firm"):
        return ("Kiraya Rs 50,000/mahina se zyada: company / firm kirayedar 10% TDS kaategi (Income-tax Act 2025 s.393(1) Table "
                "2(ii).D(b), purana 194-I). Form 16A / 26AS mein milaan kijiye; CA se pakka.")
    return ("Kiraya Rs 50,000/mahina se zyada: vyakti / HUF kirayedar 2% TDS saal ke aakhri mahine (ya ghar chhodte waqt) ek baar "
            "kaatega (s.393(1) Table 2(i), Form 141; purana 194-IB). Aapka PAN dena hoga, warna 20%. CA se pakka.")


def gst_note(unit_kind: str, use: str, tenant_registered: bool, tenant_composition: bool, landlord_gstin: str,
             rent_per_person: float = 0.0) -> str:
    if unit_kind == "pg_bed":
        if rent_per_person and rent_per_person <= 20000:
            return ("PG / hostel: Rs 20,000 per vyakti mahina tak aur 90+ din rehne par GST maaf (15 Jul 2024 se). Record rakhiye.")
        return "PG / hostel Rs 20,000 per vyakti mahina se zyada: GST lag sakta hai; rate CA se pakka."
    if use == "residential" and unit_kind not in COMMERCIAL_KINDS:
        if tenant_registered:
            return ("Ghar GST-registered kirayedar ko (business ke liye): 18% GST kirayedar RCM mein bharta hai (proprietor apne rehne "
                    "ke liye ho to nahi). CA se pakka.")
        return "Rehne ke liye ghar vyakti ko: GST nahi."
    if landlord_gstin:
        return "Commercial kiraya, aap GST-registered: bill par 18% GST (forward charge). Tax invoice CA / GST Sahayak se."
    if tenant_registered and not tenant_composition:
        return ("Commercial kiraya, aap unregistered, kirayedar registered: 18% GST kirayedar RCM mein bharega (10 Oct 2024 se). "
                "Saal ka commercial kiraya Rs 20 lakh paar = registration dekhiye (CA).")
    return "Commercial kiraya: saal ka kiraya Rs 20 lakh (kuch rajyon mein Rs 10 lakh) paar ho to GST registration dekhiye (CA)."


def receipt_notes(annual_rent: float, mode: str, amount: float, pan_ready: bool) -> list[str]:
    out = []
    if annual_rent > 100000 and not pan_ready:
        out.append("Saal ka kiraya Rs 1 lakh se zyada: HRA (Form 124) ke liye kirayedar ko aapka PAN chahiye; Niyam mein PAN locker "
                   "se jodiye.")
    if mode == "cash" and amount > 5000:
        out.append("Cash Rs 5,000 se zyada ki receipt par Re 1 revenue stamp lagaiye (sign uske upar).")
    return out


def checklist(state: str, kind: str, months: int, use: str) -> list[dict]:
    st = (state or "").upper()
    items = [
        {"id": "kyc", "what": "Kirayedar ka photo ID (Aadhaar / PAN Pehchaan Locker mein, masked) + photo", "who": "aap"},
        {"id": "agreement", "what": f"Likhit {AGREEMENT_KINDS.get(kind, 'agreement')} (Hoola ka draft vakil se padhwaiye)", "who": "aap"},
    ]
    if st == "MH":
        items += [
            {"id": "registration", "what": "IGR Maharashtra par online L&L registration (stamp duty + fee aap bharti hain; dono ka "
                                           "Aadhaar e-KYC / biometric) - kanoon s.55: registration landlord ki zimmedari",
             "who": "aap + kirayedar", "link": "https://igrmaharashtra.gov.in"},
            {"id": "police", "what": "Police ko kirayedar ki jaankari: registered e-L&L hone par kayi jagah apne aap (Leave and Licence "
                                     "2.0); warna police station / city police portal par form (BNS s.223)", "who": "aap"},
        ]
    else:
        items.append({"id": "registration", "what": ("11 mahine se lamba / 1 saal+ ka lease: Registration Act s.17 mein registration "
                                                     "zaroori; stamp duty rajya ke hisaab se (aapke number)") if months >= 12 else
                      "Stamp paper / e-stamp par agreement (stamp duty rajya ke hisaab se, aapke number)", "who": "aap"})
        if is_mta(st):
            items.append({"id": "rent_authority", "what": "Model Tenancy Act: agreement 2 mahine ke andar Rent Authority ko batana",
                          "who": "aap + kirayedar"})
        items.append({"id": "police", "what": "Local police ke niyam se kirayedar verification (police station / state police portal)",
                      "who": "aap"})
    items += [
        {"id": "society", "what": "Society ko batana / NOC (society ke bye-laws ke hisaab se)" if use == "residential" else
            "Building / mall ke niyam se intimation", "who": "aap"},
        {"id": "move_in", "what": "Move-in inspection: har kamre ki photo, meter reading, chaabiyan", "who": "aap + kirayedar"},
        {"id": "deposit_receipt", "what": "Deposit ki receipt", "who": "aap"},
    ]
    return items


def compare_inspections(move_in: list[dict], move_out: list[dict]) -> list[dict]:
    """Items worse at move-out. No rupee amount: that is hers to say."""
    rank = {"good": 0, "fair": 1, "damaged": 2, "missing": 3}
    before = {(i.get("room", ""), i.get("item", "")).__str__().lower(): i for i in move_in}
    out = []
    for i in move_out:
        k = (i.get("room", ""), i.get("item", "")).__str__().lower()
        b = before.get(k)
        now_r = rank.get(i.get("condition", ""), -1)
        was_r = rank.get(b.get("condition", ""), -1) if b else 0
        if now_r > max(was_r, 0) and now_r >= 1:
            out.append({"room": i.get("room", ""), "item": i.get("item", ""), "was": (b or {}).get("condition", "darj nahi"),
                        "now": i.get("condition", ""), "note": i.get("note", ""), "photos": i.get("photos", []),
                        "say": "Aam ghisaav (wear and tear) deposit se nahi katta; nuksaan ho to rakam aap likhiye."})
    return out


STANDARD_ITEMS = (
    ("Hall", "Deewar / paint"), ("Hall", "Farsh / tiles"), ("Hall", "Pankhe / light"), ("Hall", "Khidki / jaali"),
    ("Kitchen", "Platform / sink"), ("Kitchen", "Nal"), ("Bedroom", "Deewar / paint"), ("Bedroom", "Darwaza / lock"),
    ("Bathroom", "Nal / shower"), ("Bathroom", "Geyser"), ("Bathroom", "Commode / basin"), ("Main door", "Lock / chaabi"),
)


def notice_text(kind: str, d: dict) -> str:
    """Plain draft letter (English, standard Indian format). Unknowns stay [blank]."""
    def g(k):
        v = d.get(k)
        return str(v) if v not in (None, "") else f"[{k}]"
    head = (f"Date: {g('date')}\n\nTo,\n{g('tenant')}\n{g('unit')}\n\nFrom,\n{g('landlord')}\n{g('landlord_address')}\n\n")
    if kind == "rent_increase":
        body = (f"Subject: Revision of monthly {g('fee_word')} for {g('unit')}\n\nAs per clause {g('clause')} of our agreement dated "
                f"{g('agreement_date')}, the monthly {g('fee_word')} stands revised from Rs {g('old')} to Rs {g('new')} with effect "
                f"from {g('from')}.\n\nKindly pay the revised amount from that date.\n")
    elif kind == "renewal":
        body = (f"Subject: Renewal of agreement for {g('unit')}\n\nOur agreement for the above premises ends on {g('end')}. "
                f"If you wish to continue, we can renew it from {g('from')} at a monthly {g('fee_word')} of Rs {g('new')} on terms to "
                "be agreed and registered afresh. Please reply by [date].\n")
    else:
        body = (f"Subject: Notice to vacate {g('unit')}\n\nAs per our agreement dated {g('agreement_date')}, this is a notice of "
                f"{g('notice_months')} month(s). Kindly vacate and hand over peaceful possession of the premises on or before "
                f"{g('vacate_on')}. The security deposit will be settled after the move-out inspection, as per the agreement.\n"
                f"{('Reason: ' + d['reason'] + chr(10)) if d.get('reason') else ''}")
    return head + body + f"\nThank you,\n{g('landlord')}\n\n(Draft prepared by Hoola - please check with your lawyer before sending.)"
