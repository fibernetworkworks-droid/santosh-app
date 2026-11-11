"""DPO Sahayak rules: DPDP Act 2023 + DPDP Rules 2025 as plain data (no I/O).

Everything here is "jaankari", not legal advice: the owner's lawyer / CA confirms. Sources with dates in SOURCES.
Only facts Hoola actually read are written here; anything not confirmed is said as such (never a guessed section / date / fee).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- law facts (read 23 Oct 2026)
RULES_NOTIFIED = date(2025, 11, 13)          # Gazette 13 Nov 2025: Rules 1, 2, 17-21 (Board) in force the same day
CONSENT_MANAGER_FROM = date(2026, 11, 13)    # Rule 4 (consent managers) after 12 months
MAIN_DUTIES_FROM = date(2027, 5, 13)         # Rules 3, 5-16, 22, 23 (notice, safeguards, breach, retention, children, rights)
RIGHTS_DAYS = 90                             # Rule 14(3): respond within a reasonable period not exceeding 90 days
BREACH_REPORT_HOURS = 72                     # Rule 7(2)(b): detailed report to the Board within 72 h of becoming aware
CERT_IN_HOURS = 6                            # CERT-In Directions 28 Apr 2022 (cyber incidents), via the IT Helpdesk incident
LOG_KEEP_DAYS = 365                          # Rule 8(3): personal data, traffic data and logs kept at least one year
ERASE_WARN_HOURS = 48                        # Rule 8(2): tell her / the person at least 48 h before erasure (Third Schedule)
THIRD_SCHEDULE = [                           # Rule 8(1) + Third Schedule: 3 years after last approach
    ("E-commerce entity, 2 crore+ registered users in India", "ecommerce", 20_000_000),
    ("Online gaming intermediary, 50 lakh+ registered users in India", "gaming", 5_000_000),
    ("Social media intermediary, 2 crore+ registered users in India", "social", 20_000_000),
]
PENALTIES = [                                # Schedule to the Act (maximum)
    ("Not taking security safeguards (s.8(5))", "up to ₹250 crore"),
    ("Not telling the Board / the people about a breach (s.8(6))", "up to ₹200 crore"),
    ("Breaking the rules on children's data (s.9)", "up to ₹200 crore"),
    ("Extra rules for a Significant Data Fiduciary (s.10)", "up to ₹150 crore"),
    ("A data principal breaking their own duties (s.15)", "up to ₹10,000"),
    ("Any other rule", "up to ₹50 crore"),
]

DISCLAIMER = "This is a draft / information, not legal advice. Have a lawyer / CA / CS confirm it."

# ---------------------------------------------------------------- legal basis (s.6 consent / s.7 certain legitimate uses)
BASES = {
    "consent": "Consent (s.6): clear, freely given, for a specific purpose; can be withdrawn at any time",
    "voluntary": "Legitimate use (s.7(a)): they gave it themselves for a specific purpose and did not object",
    "employment": "Legitimate use (s.7(i)): for employment / staff purposes",
    "law": "Legitimate use (s.7): required by a law / court order (write which law)",
    "emergency": "Legitimate use (s.7): medical emergency / disaster (only when it is real)",
}

# ---------------------------------------------------------------- request kinds (rights of the data principal)
KINDS = {
    "access": ("Access request (s.11)", "which data, for what purpose, shared with whom"),
    "correction": ("Correction / completion (s.12)", "fixing wrong or incomplete data"),
    "erasure": ("Erasure (s.12)", "removing data, unless a law requires keeping it"),
    "withdraw": ("Consent withdrawn (s.6(4))", "processing stops from now on; earlier processing stays valid"),
    "grievance": ("Grievance (s.13)", "a reply to their problem; if not satisfied with the reply they can go to the Board"),
    "nominee": ("Nominee (s.14)", "who will exercise their rights in case of death / incapacity"),
}
KIND_WORDS = [
    ("erasure", r"\b(delete|erase|mita|mitao|mitaa|hata do|hatao|remove my|forget me|bhool ja|data hatana|नष्ट|मिटा|हटा|काढून)"),
    ("correction", r"\b(correct|galat|sudhar|update my|badal do|theek kar|सुधार|बदल|दुरुस्त)"),
    ("withdraw", r"\b(withdraw|consent wapas|sahmati wapas|unsubscribe|stop messag|message mat|band karo|सहमति वापस|संमती)"),
    ("nominee", r"\b(nominee|nominate|namankit|नामांकित|वारस)"),
    ("access", r"\b(access|copy of my data|kya data|mera data|what data|summary|जानकारी|माहिती|kaunsi jaankari)"),
    ("grievance", r"\b(complain|shikayat|grievance|takleef|शिकायत|तक्रार)"),
]


def kind_of(text: str) -> str:
    t = (text or "").lower()
    for k, rx in KIND_WORDS:
        if re.search(rx, t):
            return k
    return "grievance"


# ---------------------------------------------------------------- Hoola modules -> records of processing (pre-fill)
# tables: (table, tenant column) used only to see if she uses the module and how many records. All "andaaza": she edits.
ROPA_CATALOG: list[dict] = [
    {"key": "telecall", "label": "Telecaller: leads and call log", "tables": ["tele_leads", "tele_calls"], "people": "customers / leads",
     "items": ["name", "mobile number", "need / interest", "call notes", "next call"], "purpose": "calling customers and following up",
     "basis": "consent", "retention": "closed lead: 1 year (your rule)", "days": 365, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "eraser": "telecall"},
    {"key": "whatsapp", "label": "Business WhatsApp inbox", "tables": ["employee_contacts", "employee_messages"], "people": "customers",
     "items": ["WhatsApp number", "name", "messages"], "purpose": "answering customers' questions, bookings, dues", "basis": "voluntary",
     "retention": "your rule", "days": None, "processors": ["Meta (WhatsApp Cloud API)", "Hoola (Newtika Pvt Ltd) server"]},
    {"key": "appointments", "label": "Appointments", "tables": ["employee_appointments"], "people": "customers", "items": ["name", "mobile number", "time"],
     "purpose": "booking appointments and sending reminders", "basis": "voluntary", "retention": "your rule", "days": 365,
     "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "dues", "label": "Dues / credit", "tables": ["employee_dues"], "people": "customers", "items": ["name", "mobile number", "amount", "date"],
     "purpose": "reminders for money due", "basis": "voluntary", "retention": "as accounting law requires (ask your CA)", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"], "law_hold": True},
    {"key": "payroll", "label": "Payroll: staff salary", "tables": ["pay_employees", "pay_runs"], "people": "staff",
     "items": ["name", "PAN (masked)", "bank account (masked)", "UAN / ESIC", "salary", "attendance"], "purpose": "salary, PF / ESIC / TDS",
     "basis": "employment", "retention": "as labour / PF / income-tax law requires (ask your CA)", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server", "your bank (salary file)"], "law_hold": True, "financial": True},
    {"key": "team", "label": "Team (Hoola Employee)", "tables": ["employee_team"], "people": "staff", "items": ["name", "mobile number", "Hoola ID"],
     "purpose": "assigning work", "basis": "employment", "retention": "after employment ends: your rule", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "darzi", "label": "Tailoring: customers and measurements", "tables": ["darzi_customers", "darzi_orders"], "people": "customers",
     "items": ["name", "mobile number", "body measurements", "order"], "purpose": "tailoring orders", "basis": "voluntary",
     "retention": "your rule", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "mshop", "label": "Mobile shop: repair + recharge", "tables": ["mshop_customers", "mshop_jobs", "mshop_recharges"],
     "people": "customers", "items": ["name", "mobile number", "IMEI", "photo of the phone", "recharge number"], "purpose": "repair, warranty, recharge",
     "basis": "voluntary", "retention": "until the warranty ends + your rule", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "insure", "label": "Insurance: clients and policies", "tables": ["ins_clients", "ins_policies"], "people": "customers / family",
     "items": ["name", "mobile number", "date of birth", "family", "income", "policy", "health details"], "purpose": "renewal, advice, claim",
     "basis": "consent", "retention": "as IRDAI / insurer rules require", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "law_hold": True, "health": True},
    {"key": "rentdesk", "label": "Property manager: tenants", "tables": ["rentdesk_people", "rentdesk_tenancies"], "people": "tenants",
     "items": ["name", "mobile number", "ID (in the locker)", "rent", "deposit", "inspection photos"], "purpose": "rent, agreement, deposit",
     "basis": "voluntary", "retention": "after the deposit is returned: your rule", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "society", "label": "Housing society: members", "tables": ["society_flats", "society_visits"], "people": "members / visitors",
     "items": ["name", "mobile number", "flat", "nominee", "bill / dues", "visitor's name"], "purpose": "running the society, bills, gate register",
     "basis": "voluntary", "retention": "visitors: your number of days; members: society law", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "seva", "label": "Customer support tickets", "tables": ["seva_tickets"], "people": "customers", "items": ["name", "mobile number", "complaint text"],
     "purpose": "support and complaints", "basis": "voluntary", "retention": "your rule", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "shikayat", "label": "Complaints", "tables": ["shikayat_cases"], "people": "customers", "items": ["name", "mobile number", "complaint", "proof photo"],
     "purpose": "resolving complaints", "basis": "voluntary", "retention": "your rule", "days": 1095, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "eraser": "shikayat"},
    {"key": "wapsi", "label": "Returns / refunds", "tables": ["wapsi_returns"], "people": "customers", "items": ["name", "mobile number", "address", "UPI ID", "photos"],
     "purpose": "returns and refunds", "basis": "voluntary", "retention": "amount for GST; personal data: your rule", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server", "courier (Shiprocket / Delhivery, if you use one)"], "eraser": "wapsi"},
    {"key": "courier", "label": "Courier parcels", "tables": ["courier_parcels"], "people": "customers", "items": ["name", "mobile number", "address"],
     "purpose": "sending parcels", "basis": "voluntary", "retention": "after delivery: your rule", "days": 365,
     "processors": ["courier company", "Hoola (Newtika Pvt Ltd) server"], "eraser": "courier"},
    {"key": "feedback", "label": "Feedback / reviews", "tables": ["feedback_items"], "people": "customers", "items": ["name", "review text", "rating"],
     "purpose": "improving the service", "basis": "voluntary", "retention": "your rule", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "community", "label": "Community groups", "tables": ["samudaay_members"], "people": "group members", "items": ["name", "username", "messages"],
     "purpose": "running the group", "basis": "voluntary", "retention": "messages for 90 days", "days": 90, "processors": ["Telegram", "Hoola (Newtika Pvt Ltd) server"]},
    {"key": "callcentre", "label": "Call centre line", "tables": ["callcentre_callers", "callcentre_calls"], "people": "callers",
     "items": ["number", "written summary of the call (masked)"], "purpose": "answering questions on the phone", "basis": "consent",
     "retention": "your rule", "days": 365, "processors": ["Plivo / Exotel (phone line)", "Google (Gemini voice)", "Hoola (Newtika Pvt Ltd) server"],
     "eraser": "callcentre"},
    {"key": "propagent", "label": "Property leads + owners", "tables": ["propagent_leads", "propagent_listings"], "people": "buyers / owners",
     "items": ["name", "mobile number", "budget", "property address"], "purpose": "showing property / deals", "basis": "consent",
     "retention": "after the deal closes: your rule", "days": 365, "processors": ["Hoola (Newtika Pvt Ltd) server"], "eraser": "propagent"},
    {"key": "drivers", "label": "Drivers", "tables": ["drivers_drivers"], "people": "staff (driver)", "items": ["name", "mobile number", "licence (in the locker)", "duty"],
     "purpose": "duty and trips", "basis": "employment", "retention": "after employment ends: your rule", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "thok", "label": "Wholesale parties", "tables": ["thok_parties"], "people": "customers (business)", "items": ["name", "mobile number", "GSTIN", "dues"],
     "purpose": "bills and credit", "basis": "voluntary", "retention": "GST: 72 months (confirm with your CA)", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"], "law_hold": True, "financial": True},
    {"key": "aftersales", "label": "After-sales customers", "tables": ["aftersales_customers"], "people": "customers", "items": ["name", "mobile number", "address", "machine"],
     "purpose": "service reminders, visits", "basis": "voluntary", "retention": "after the warranty / AMC ends: your rule", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "galla", "label": "Till (UPI alerts)", "tables": ["galla_entries"], "people": "customers", "items": ["sender's first name", "amount"],
     "purpose": "counting daily sales", "basis": "voluntary", "retention": "your rule", "days": 365, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "financial": True},
    {"key": "idvault", "label": "ID Locker (Aadhaar / PAN)", "tables": ["id_vault"], "people": "you / family / customers",
     "items": ["Aadhaar / PAN / ID number (encrypted)"], "purpose": "filling forms", "basis": "consent", "retention": "as long as you keep it",
     "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server (encrypted)"]},
    {"key": "voiceid", "label": "Voice ID (voice fingerprint)", "tables": ["voice_members"], "people": "family",
     "items": ["encrypted fingerprint of the voice (not audio)"], "purpose": "recognising who is speaking", "basis": "consent",
     "retention": "as long as you keep it", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "travel", "label": "Travel: travellers", "tables": ["travel_trips"], "people": "customers / family", "items": ["name", "age", "ID (in the locker)"],
     "purpose": "ticket / hotel booking", "basis": "voluntary", "retention": "after the trip: your rule", "days": 365,
     "processors": ["IRCTC / airline / hotel site", "Hoola (Newtika Pvt Ltd) server"]},
    {"key": "sitesup", "label": "Site labour register", "tables": ["sitesup_labour"], "people": "workers", "items": ["name", "attendance", "hours"],
     "purpose": "attendance and wage register", "basis": "employment", "retention": "as labour law requires", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"], "law_hold": True},
]
CATALOG = {c["key"]: c for c in ROPA_CATALOG}

# modules where Hoola can find a person by phone (table, phone column, id column, eraser key)
FINDERS = [
    ("telecall", "Telecaller lead", "tele_leads", "phone", "id", "telecall"),
    ("shikayat", "Complaint", "shikayat_cases", "phone", "id", "shikayat"),
    ("callcentre", "Call centre caller", "callcentre_callers", "key", "id", "callcentre"),
    ("wapsi", "Return", "wapsi_returns", "phone", "id", "wapsi"),
    ("courier", "Parcel", "courier_parcels", "phone", "id", "courier"),
    ("propagent", "Property lead", "propagent_leads", "phone", "id", "propagent"),
    ("darzi", "Tailoring customer", "darzi_customers", "phone", "id", ""),
    ("mshop", "Mobile shop customer", "mshop_customers", "phone", "id", ""),
    ("insure", "Insurance client", "ins_clients", "phone", "id", ""),
    ("aftersales", "After-sales customer", "aftersales_customers", "phone", "id", ""),
    ("thok", "Wholesale party", "thok_parties", "phone", "id", ""),
]

# ---------------------------------------------------------------- DPIA + processor (DPA) checklists
DPIA_QUESTIONS = [
    ("purpose", "Is the purpose written clearly, and do you collect only as much data as is needed (data minimisation)?", False),
    ("children", "Does it include data of children (under 18)?", True),
    ("health_fin", "Risky data such as health, money / bank, ID numbers, voice / face?", True),
    ("scale", "Data of a very large number of people (thousands), or growing every day?", True),
    ("new_tech", "A new method: AI decisions, profiling, location tracking, camera?", True),
    ("abroad", "Does the data go outside India (to a vendor's server)?", True),
    ("sharing", "Does the data go to a third party (vendor / partner)?", True),
    ("security", "Are encryption / masking, access control, backup and 1 year of logs in place (Rule 6)?", False),
    ("consent_ok", "Was the notice shown and is there a record of consent (or a clear s.7 basis)?", False),
    ("erase_ok", "Is there a schedule to erase the data once the purpose is complete?", False),
]

DPA_CLAUSES = [
    ("instructions", "The vendor uses the data only for the work you have written down (only on your instruction)"),
    ("security", "Security: encryption / masking, access control, logs, backup (as in Rule 6)"),
    ("breach", "Tells you at once on learning of a breach (you must report to the Board within 72 hours)"),
    ("subprocessor", "Does not pass the data on to anyone else without your written permission"),
    ("staff", "Confidentiality binding on its staff"),
    ("erase", "At the end of the work / contract, returns or erases the data and confirms in writing"),
    ("help_rights", "Helps with people's requests (access / correction / erasure)"),
    ("location", "Where the data is kept (country) is written down; if outside India, check the government's restricted list"),
    ("audit", "You can ask for a check / audit report"),
    ("logs", "Processing logs kept for at least 1 year (Rule 8(3))"),
    ("liability", "Liability / compensation for mistakes (in your lawyer's words)"),
]

CHILD_RISK_WORDS = re.compile(r"\b(ad|ads|advert|target|marketing|promotion|track|tracking|location|profil|behaviou?r|monitor)", re.I)


def dpia_score(answers: dict) -> tuple[int, str, list[str]]:
    """Risk: each risky 'yes' +2, each missing safeguard ('no' to a safeguard question) +2. 0-4 low, 5-8 medium, 9+ high."""
    score, notes = 0, []
    for key, q, risky in DPIA_QUESTIONS:
        v = answers.get(key)
        if v is None:
            notes.append(f"Not answered: {q}")
            continue
        if risky and bool(v):
            score += 2
            notes.append(f"Risk: {q}")
        if not risky and not bool(v):
            score += 2
            notes.append(f"Gap: {q}")
    level = "high" if score >= 9 else ("medium" if score >= 5 else "low")
    return score, level, notes


def child_flags(activity: dict) -> list[str]:
    out = []
    if not activity.get("children"):
        return out
    out.append("Children's data: verifiable consent of a parent BEFORE processing (s.9(1), Rule 10). Hoola keeps only the method of "
               "verification and a reference, not their ID number.")
    txt = " ".join([activity.get("purpose") or "", " ".join(activity.get("items") or [])])
    if CHILD_RISK_WORDS.search(txt):
        out.append("Tracking children, monitoring their behaviour or targeting ads at them is prohibited (s.9(3)): remove this activity.")
    return out


# ---------------------------------------------------------------- helpers
def phone10(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    return d[-10:] if len(d) >= 10 else ""


def mask_phone(p: str) -> str:
    p = phone10(p)
    return f"XXXXXX{p[-4:]}" if p else ""


def mask_email(e: str) -> str:
    e = (e or "").strip()
    if "@" not in e:
        return ""
    u, d = e.split("@", 1)
    return (u[:2] + "***@" + d)[:120]


def scrub(text, n: int = 4000) -> str:
    """Their words are data: OTP / PIN / passwords / card / long numbers / PAN never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|passcode|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [removed]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[removed]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[removed]", t)
    return t.strip()[:n]


BLANK = "[____]"


def has_blank(text: str) -> bool:
    return BLANK in (text or "") or "[blank]" in (text or "").lower()


def due_rights(received: date, own_days: int = 0) -> date:
    days = RIGHTS_DAYS if not own_days or own_days > RIGHTS_DAYS else own_days
    return received + timedelta(days=days)


def phase_notes(today: date) -> list[str]:
    out = []
    if today < MAIN_DUTIES_FROM:
        out.append(f"The rules on notice, consent, rights, breach, retention and children apply from {MAIN_DUTIES_FROM.strftime('%d-%m-%Y')} "
                   "(Rules 3, 5-16). It is good to prepare now; the Board's rules have applied since 13-11-2025.")
    if today < CONSENT_MANAGER_FROM:
        out.append(f"Consent managers (Rule 4) apply from {CONSENT_MANAGER_FROM.strftime('%d-%m-%Y')}.")
    return out


# ---------------------------------------------------------------- notice (Rule 3) in hi / mr / en
LANGS = {"en": "English", "hi": "हिन्दी", "mr": "मराठी"}

_NOTICE = {
    "en": {
        "title": "Privacy notice: {org}",
        "intro": "{org} collects and uses your personal data only for the purposes written below. Please read this notice; it stands "
                 "on its own.",
        "items": "What personal data we collect",
        "purpose": "Why we use it (purpose) and what we provide to you",
        "basis_c": "We use this with your consent.",
        "basis_l": "We use this because you gave it to us for this purpose (a legitimate use under the law).",
        "keep": "How long we keep it",
        "share": "Who processes it for us",
        "withdraw": "Withdraw consent: {link} (as easy as giving it). After withdrawal we stop; earlier processing stays valid.",
        "rights": "Your rights: ask what data we hold, correct or complete it, erase it, name a nominee, or raise a grievance: {link}. "
                  "We reply within {days} days.",
        "board": "If you are not satisfied with our reply, you may complain to the Data Protection Board of India.",
        "contact": "Contact for your questions: {contact}",
        "children": "For anyone under 18 we first take verifiable consent of a parent / lawful guardian.",
        "ver": "Version {ver}, {date}",
    },
    "hi": {
        "title": "गोपनीयता सूचना: {org}",
        "intro": "{org} आपका निजी डेटा सिर्फ़ नीचे लिखे कामों के लिए लेता और इस्तेमाल करता है। कृपया यह सूचना पढ़ें; यह अपने आप में पूरी है।",
        "items": "हम कौन-सा निजी डेटा लेते हैं",
        "purpose": "किस काम के लिए (उद्देश्य) और आपको क्या सेवा / सामान मिलता है",
        "basis_c": "यह हम आपकी सहमति से करते हैं।",
        "basis_l": "यह हम इसलिए करते हैं क्योंकि आपने यह जानकारी इसी काम के लिए खुद दी है (कानून में मान्य उपयोग)।",
        "keep": "कितने समय तक रखते हैं",
        "share": "हमारे लिए कौन प्रोसेस करता है",
        "withdraw": "सहमति वापस लेने के लिए: {link} (उतना ही आसान जितना सहमति देना)। वापस लेने के बाद हम रुक जाते हैं; पहले का काम मान्य रहता है।",
        "rights": "आपके अधिकार: आपका कौन-सा डेटा है यह जानना, सुधारना या पूरा करवाना, मिटवाना, नॉमिनी बनाना, या शिकायत करना: {link}। "
                  "हम {days} दिन के भीतर जवाब देते हैं।",
        "board": "हमारे जवाब से संतुष्ट न हों तो आप भारत के डेटा प्रोटेक्शन बोर्ड में शिकायत कर सकते हैं।",
        "contact": "सवालों के लिए संपर्क: {contact}",
        "children": "18 साल से कम उम्र वालों के लिए हम पहले माता-पिता / कानूनी अभिभावक की सत्यापित सहमति लेते हैं।",
        "ver": "संस्करण {ver}, {date}",
    },
    "mr": {
        "title": "गोपनीयता सूचना: {org}",
        "intro": "{org} तुमचा वैयक्तिक डेटा फक्त खाली लिहिलेल्या कामांसाठी घेते आणि वापरते. कृपया ही सूचना वाचा; ती स्वतंत्रपणे पूर्ण आहे.",
        "items": "आम्ही कोणता वैयक्तिक डेटा घेतो",
        "purpose": "कोणत्या कामासाठी (उद्देश) आणि तुम्हाला कोणती सेवा / वस्तू मिळते",
        "basis_c": "हे आम्ही तुमच्या संमतीने करतो.",
        "basis_l": "हे आम्ही करतो कारण तुम्ही ही माहिती याच कामासाठी स्वतः दिली आहे (कायद्याने मान्य वापर).",
        "keep": "किती काळ ठेवतो",
        "share": "आमच्यासाठी कोण प्रक्रिया करते",
        "withdraw": "संमती मागे घेण्यासाठी: {link} (संमती देण्याइतकेच सोपे). मागे घेतल्यानंतर आम्ही थांबतो; आधीचे काम वैध राहते.",
        "rights": "तुमचे अधिकार: तुमचा कोणता डेटा आहे ते जाणणे, दुरुस्त / पूर्ण करणे, पुसून टाकणे, नॉमिनी नेमणे, किंवा तक्रार करणे: {link}. "
                  "आम्ही {days} दिवसांत उत्तर देतो.",
        "board": "आमच्या उत्तराने समाधान न झाल्यास तुम्ही भारताच्या डेटा प्रोटेक्शन बोर्डकडे तक्रार करू शकता.",
        "contact": "प्रश्नांसाठी संपर्क: {contact}",
        "children": "18 वर्षांखालील व्यक्तींसाठी आम्ही आधी पालक / कायदेशीर पालकाची पडताळलेली संमती घेतो.",
        "ver": "आवृत्ती {ver}, {date}",
    },
}


def notice_text(lang: str, org: str, activities: list[dict], link: str, contact: str, days: int, ver: int, on: date) -> str:
    """Rule 3: standalone, plain language; (i) itemised data, (ii) purposes + goods / services, (c) link to withdraw (as easy as
    giving), to exercise rights, and to complain to the Board. Missing facts stay BLANK (never invented)."""
    L = _NOTICE.get(lang) or _NOTICE["en"]
    org = org or BLANK
    link = link or BLANK
    contact = contact or BLANK
    lines = [L["title"].format(org=org), "", L["intro"].format(org=org), ""]
    for a in activities:
        lines.append(f"■ {a.get('name') or a.get('label')}")
        lines.append(f"  {L['items']}: {', '.join(a.get('items') or []) or BLANK}")
        lines.append(f"  {L['purpose']}: {a.get('purpose') or BLANK}")
        lines.append("  " + (L["basis_c"] if a.get("basis") == "consent" else L["basis_l"]))
        lines.append(f"  {L['keep']}: {a.get('retention') or BLANK}")
        if a.get("processors"):
            lines.append(f"  {L['share']}: {', '.join(a['processors'])}")
        lines.append("")
    if any(a.get("children") for a in activities):
        lines += [L["children"], ""]
    lines.append(L["withdraw"].format(link=link))
    lines.append(L["rights"].format(link=link, days=days))
    lines.append(L["board"])
    lines.append(L["contact"].format(contact=contact))
    lines += ["", L["ver"].format(ver=ver, date=on.strftime("%d-%m-%Y"))]
    return "\n".join(lines)


# ---------------------------------------------------------------- breach texts (Rule 7)
def breach_people_text(b: dict, org: str, contact: str) -> str:
    """Rule 7(1): concise, plain, without delay: (a) what / extent / when, (b) likely consequences, (c) our measures,
    (d) what she can do, (e) business contact."""
    return "\n".join([
        f"Important notice from {org or BLANK}: a security incident involving your data (data breach).",
        f"What happened: {b.get('nature') or BLANK}. Extent: {b.get('extent') or BLANK}. When: {b.get('when') or BLANK}.",
        f"How it may affect you: {b.get('consequences') or BLANK}.",
        f"What we have done / are doing: {b.get('measures') or BLANK}.",
        f"What you can do: {b.get('safety') or BLANK}. We never ask for an OTP / PIN / password.",
        f"For questions: {contact or BLANK}.",
    ])


def breach_initial_text(b: dict, org: str) -> str:
    """Rule 7(2)(a): without delay to the Board: description incl. nature, extent, timing, location and likely impact."""
    return "\n".join([
        f"Personal data breach: initial intimation (Rule 7(2)(a)) - {org or BLANK}",
        f"Became aware: {b.get('aware_text') or BLANK}",
        f"Nature: {b.get('nature') or BLANK}",
        f"Extent (how many people / records, which data): {b.get('extent') or BLANK}",
        f"Timing: {b.get('when') or BLANK}",
        f"Location / system: {b.get('location') or BLANK}",
        f"Likely impact: {b.get('impact') or BLANK}",
    ])


def breach_report_text(b: dict, org: str) -> str:
    """Rule 7(2)(b): within 72 h: (i) updated details, (ii) broad facts / reasons, (iii) mitigation, (iv) findings on who caused it,
    (v) remedial steps against recurrence, (vi) report on intimations given to affected people."""
    return "\n".join([
        f"Personal data breach: 72-hour report (Rule 7(2)(b)) - {org or BLANK}",
        f"(i) Updated and complete details: {b.get('details') or b.get('nature') or BLANK}",
        f"(ii) The event, circumstances and reasons: {b.get('cause') or BLANK}",
        f"(iii) Measures to reduce the risk (taken / proposed): {b.get('measures') or BLANK}",
        f"(iv) Findings about who caused it: {b.get('findings') or BLANK}",
        f"(v) Remedial steps to prevent a recurrence: {b.get('remedial') or BLANK}",
        f"(vi) Report on the intimations given to affected people: {b.get('people_report') or BLANK}",
    ])


BREACH_FIELDS = ("nature", "extent", "when", "location", "impact", "consequences", "measures", "safety", "cause", "findings",
                 "remedial", "details", "systems", "people_report")

# ---------------------------------------------------------------- reply drafts to a request
def reply_text(kind: str, name: str, org: str, number: str, body: str, contact: str) -> str:
    head = f"Hello {name or ''},".replace(" ,", ",")
    k = KINDS.get(kind, ("Your request", ""))[0]
    return "\n".join([
        head,
        f"{org or BLANK} has received your request {number} ({k}).",
        body or BLANK,
        "If you are not satisfied with our reply, you may complain to the Data Protection Board of India.",
        f"Contact: {contact or BLANK}",
    ])


NEVER = [
    "Not legal advice: have a lawyer / CA / CS confirm every draft.",
    "Publishing a notice, replying to people, erasing data, breach notices to the Board / people: only with your tap in the app (card + hash).",
    "No Aadhaar / PAN number for identity checks: only the method and a reference (if an ID arrives, it goes into the ID Locker).",
    "Never makes up a section / date / penalty: only what was read in a source; the rest stays [____].",
    "Nobody's data goes to anyone else; numbers are masked in logs.",
    "Hoola does not file on any portal itself; you send to the Board / CERT-In through your own channel.",
]

SOURCES = [
    ("DPDP Rules 2025 notified 13 Nov 2025; phases: Board rules same day, Rule 4 after 12 months, Rules 3, 5-16, 22, 23 after 18 months "
     "(13 May 2027); Rule 7 72 h; Rule 8(3) 1-year logs; Rule 14(3) 90 days",
     "https://www.barandbench.com/view-point/meity-notifies-final-digital-personal-data-protection-rules-2025", "2025-11-17"),
    ("Rule 3 notice contents (text)", "https://www.dpdpa.com/dpdparules/rule3.html", "2026-10-23"),
    ("Rule 7 breach intimation to people and Board (text)", "https://www.dpdpa.com/dpdparules/rule7.html", "2026-10-23"),
    ("Rule 8 erasure, 48 h prior intimation, 1-year logs (text)", "https://www.dpdpa.com/dpdparules/rule8.html", "2026-10-23"),
    ("Rule 10 verifiable consent of parent (text)", "https://www.dpdpa.com/dpdparules/rule10.html", "2026-10-23"),
    ("Rule 14 rights: publish means, identifiers, 90 days, nominee (text)", "https://www.dpdpa.com/dpdparules/rule14.html", "2026-10-23"),
    ("Third Schedule: e-commerce 2 crore / gaming 50 lakh / social media 2 crore users, 3 years", "https://www.dpdpa.com/schedule/schedule3.html",
     "2026-10-23"),
    ("Schedule of penalties (Rs 250 / 200 / 200 / 150 crore, Rs 10,000, Rs 50 crore)", "https://dpdpa.com/theschedule.html", "2026-10-23"),
    ("Data Protection Board: no chairperson / members appointed as of Aug 2026", "https://www.livelaw.in/articles/india-data-protection-board-established-law-543751",
     "2026-08-01"),
    ("Rules overview (Rule 6 safeguards, Rule 7, Rule 10 methods)", "https://lawrbit.com/article/digital-personal-data-protection-rules-2025",
     "2025-11"),
    ("CERT-In Directions 28 Apr 2022: 6-hour reporting (used through the IT Helpdesk incident)",
     "", "2022-04-28 (source list in the IT Helpdesk module)"),
]


def fmt_dt(d: datetime | None) -> str:
    return d.strftime("%d-%m-%Y %H:%M") if d else ""
