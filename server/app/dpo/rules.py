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
    ("Security safeguards na lena (s.8(5))", "₹250 crore tak"),
    ("Board / logon ko breach na batana (s.8(6))", "₹200 crore tak"),
    ("Bachchon ke data ke niyam todna (s.9)", "₹200 crore tak"),
    ("Significant Data Fiduciary ke extra niyam (s.10)", "₹150 crore tak"),
    ("Data principal ke apne kartavya todna (s.15)", "₹10,000 tak"),
    ("Baaki koi bhi niyam", "₹50 crore tak"),
]

DISCLAIMER = "Yeh draft / jaankari hai, kanooni salah nahi. Vakil / CA / CS se pakka karwaiye."

# ---------------------------------------------------------------- legal basis (s.6 consent / s.7 certain legitimate uses)
BASES = {
    "consent": "Consent (s.6): saaf, apni marzi se, kisi khaas kaam ke liye; kabhi bhi wapas le sakte hain",
    "voluntary": "Legitimate use (s.7(a)): unhone khud kisi khaas kaam ke liye diya aur mana nahi kiya",
    "employment": "Legitimate use (s.7(i)): naukri / staff ke kaam ke liye",
    "law": "Legitimate use (s.7): kisi kanoon / court order ki zaroorat (kaunsa kanoon: likhiye)",
    "emergency": "Legitimate use (s.7): medical emergency / aapda (sirf jab sach mein ho)",
}

# ---------------------------------------------------------------- request kinds (rights of the data principal)
KINDS = {
    "access": ("Jaankari maangi (s.11)", "kaunsa data, kis kaam ke liye, kisko diya"),
    "correction": ("Sudhaar / poora karna (s.12)", "galat ya adhoora data theek karna"),
    "erasure": ("Mitaana (s.12)", "data hatana, jab tak kisi kanoon ke liye rakhna zaroori na ho"),
    "withdraw": ("Consent wapas (s.6(4))", "aage se processing band; pehle ka kaam valid rehta hai"),
    "grievance": ("Shikayat (s.13)", "unki dikkat ka jawab; jawab se khush nahi to Board ke paas jaa sakte hain"),
    "nominee": ("Nominee (s.14)", "maut / asamarthata mein unki jagah kaun adhikaar use karega"),
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
    {"key": "telecall", "label": "Telecaller: leads aur call log", "tables": ["tele_leads", "tele_calls"], "people": "graahak / leads",
     "items": ["naam", "mobile", "zaroorat / interest", "call ke notes", "agla call"], "purpose": "graahak ko call karna aur follow-up",
     "basis": "consent", "retention": "band lead: 1 saal (aapka niyam)", "days": 365, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "eraser": "telecall"},
    {"key": "whatsapp", "label": "Business WhatsApp inbox", "tables": ["employee_contacts", "employee_messages"], "people": "graahak",
     "items": ["WhatsApp number", "naam", "messages"], "purpose": "graahak ke sawaal ka jawab, booking, baaki", "basis": "voluntary",
     "retention": "aapka niyam", "days": None, "processors": ["Meta (WhatsApp Cloud API)", "Hoola (Newtika Pvt Ltd) server"]},
    {"key": "appointments", "label": "Appointments", "tables": ["employee_appointments"], "people": "graahak", "items": ["naam", "mobile", "samay"],
     "purpose": "appointment book karna aur yaad dilana", "basis": "voluntary", "retention": "aapka niyam", "days": 365,
     "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "dues", "label": "Baaki / udhaar", "tables": ["employee_dues"], "people": "graahak", "items": ["naam", "mobile", "rakam", "taarikh"],
     "purpose": "baaki paisa yaad dilana", "basis": "voluntary", "retention": "accounts ke kanoon ke hisaab se (CA se poochhiye)", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"], "law_hold": True},
    {"key": "payroll", "label": "Payroll: staff salary", "tables": ["pay_employees", "pay_runs"], "people": "staff",
     "items": ["naam", "PAN (chhupa)", "bank account (chhupa)", "UAN / ESIC", "salary", "hazri"], "purpose": "salary, PF / ESIC / TDS",
     "basis": "employment", "retention": "labour / PF / income-tax kanoon ke hisaab se (CA se poochhiye)", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server", "aapka bank (salary file)"], "law_hold": True, "financial": True},
    {"key": "team", "label": "Team (Hoola Employee)", "tables": ["employee_team"], "people": "staff", "items": ["naam", "mobile", "Hoola ID"],
     "purpose": "kaam baantna", "basis": "employment", "retention": "naukri ke baad: aapka niyam", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "darzi", "label": "Darzi: graahak aur naap", "tables": ["darzi_customers", "darzi_orders"], "people": "graahak",
     "items": ["naam", "mobile", "naap (body measurements)", "order"], "purpose": "silai ka order", "basis": "voluntary",
     "retention": "aapka niyam", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "mshop", "label": "Mobile dukaan: repair + recharge", "tables": ["mshop_customers", "mshop_jobs", "mshop_recharges"],
     "people": "graahak", "items": ["naam", "mobile", "IMEI", "phone ki photo", "recharge number"], "purpose": "repair, warranty, recharge",
     "basis": "voluntary", "retention": "warranty khatam hone tak + aapka niyam", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "insure", "label": "Bima: client aur policy", "tables": ["ins_clients", "ins_policies"], "people": "graahak / parivaar",
     "items": ["naam", "mobile", "janam taarikh", "parivaar", "aamdani", "policy", "health ki baatein"], "purpose": "renewal, salah, claim",
     "basis": "consent", "retention": "IRDAI / insurer ke niyam ke hisaab se", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "law_hold": True, "health": True},
    {"key": "rentdesk", "label": "Property manager: kirayedar", "tables": ["rentdesk_people", "rentdesk_tenancies"], "people": "kirayedar",
     "items": ["naam", "mobile", "ID (locker mein)", "kiraya", "deposit", "inspection photos"], "purpose": "kiraya, agreement, deposit",
     "basis": "voluntary", "retention": "deposit wapas hone ke baad: aapka niyam", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "society", "label": "Housing society: members", "tables": ["society_flats", "society_visits"], "people": "members / visitors",
     "items": ["naam", "mobile", "flat", "nominee", "bill / baaki", "visitor ka naam"], "purpose": "society chalana, bill, gate register",
     "basis": "voluntary", "retention": "visitors: aapke din; members: society kanoon", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "seva", "label": "Customer support tickets", "tables": ["seva_tickets"], "people": "graahak", "items": ["naam", "mobile", "shikayat ka text"],
     "purpose": "support aur shikayat", "basis": "voluntary", "retention": "aapka niyam", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "shikayat", "label": "Complaints (Shikayat)", "tables": ["shikayat_cases"], "people": "graahak", "items": ["naam", "mobile", "shikayat", "saboot photo"],
     "purpose": "shikayat suljhana", "basis": "voluntary", "retention": "aapka niyam", "days": 1095, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "eraser": "shikayat"},
    {"key": "wapsi", "label": "Returns / refunds", "tables": ["wapsi_returns"], "people": "graahak", "items": ["naam", "mobile", "pata", "UPI ID", "photos"],
     "purpose": "return aur refund", "basis": "voluntary", "retention": "GST ke liye amount; personal: aapka niyam", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server", "courier (Shiprocket / Delhivery, agar use karti hain)"], "eraser": "wapsi"},
    {"key": "courier", "label": "Courier parcels", "tables": ["courier_parcels"], "people": "graahak", "items": ["naam", "mobile", "pata"],
     "purpose": "parcel bhejna", "basis": "voluntary", "retention": "delivery ke baad: aapka niyam", "days": 365,
     "processors": ["courier company", "Hoola (Newtika Pvt Ltd) server"], "eraser": "courier"},
    {"key": "feedback", "label": "Feedback / reviews", "tables": ["feedback_items"], "people": "graahak", "items": ["naam", "review ka text", "rating"],
     "purpose": "seva behtar karna", "basis": "voluntary", "retention": "aapka niyam", "days": 730, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "community", "label": "Community groups", "tables": ["samudaay_members"], "people": "group members", "items": ["naam", "username", "messages"],
     "purpose": "group chalana", "basis": "voluntary", "retention": "90 din messages", "days": 90, "processors": ["Telegram", "Hoola (Newtika Pvt Ltd) server"]},
    {"key": "callcentre", "label": "Call centre line", "tables": ["callcentre_callers", "callcentre_calls"], "people": "callers",
     "items": ["number", "call ka likha hua saar (masked)"], "purpose": "phone par sawaal ka jawab", "basis": "consent",
     "retention": "aapka niyam", "days": 365, "processors": ["Plivo / Exotel (phone line)", "Google (Gemini voice)", "Hoola (Newtika Pvt Ltd) server"],
     "eraser": "callcentre"},
    {"key": "propagent", "label": "Property leads + owners", "tables": ["propagent_leads", "propagent_listings"], "people": "kharidaar / malik",
     "items": ["naam", "mobile", "budget", "property ka pata"], "purpose": "property dikhana / deal", "basis": "consent",
     "retention": "deal band hone ke baad: aapka niyam", "days": 365, "processors": ["Hoola (Newtika Pvt Ltd) server"], "eraser": "propagent"},
    {"key": "drivers", "label": "Drivers", "tables": ["drivers_drivers"], "people": "staff (driver)", "items": ["naam", "mobile", "licence (locker mein)", "duty"],
     "purpose": "duty aur trip", "basis": "employment", "retention": "naukri ke baad: aapka niyam", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "thok", "label": "Wholesale parties", "tables": ["thok_parties"], "people": "graahak (business)", "items": ["naam", "mobile", "GSTIN", "baaki"],
     "purpose": "bill aur udhaar", "basis": "voluntary", "retention": "GST: 72 mahine (CA se pakka)", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"], "law_hold": True, "financial": True},
    {"key": "aftersales", "label": "After-sales graahak", "tables": ["aftersales_customers"], "people": "graahak", "items": ["naam", "mobile", "pata", "machine"],
     "purpose": "service yaad dilana, visit", "basis": "voluntary", "retention": "warranty / AMC ke baad: aapka niyam", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "galla", "label": "Galla (UPI alerts)", "tables": ["galla_entries"], "people": "graahak", "items": ["bhejne wale ka pehla naam", "rakam"],
     "purpose": "rozana bikri ginna", "basis": "voluntary", "retention": "aapka niyam", "days": 365, "processors": ["Hoola (Newtika Pvt Ltd) server"],
     "financial": True},
    {"key": "idvault", "label": "Pehchaan Locker (Aadhaar / PAN)", "tables": ["id_vault"], "people": "aap / parivaar / graahak",
     "items": ["Aadhaar / PAN / ID number (encrypted)"], "purpose": "form bharna", "basis": "consent", "retention": "jab tak aap rakhein",
     "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server (encrypted)"]},
    {"key": "voiceid", "label": "Awaaz Pehchaan (voice fingerprint)", "tables": ["voice_members"], "people": "parivaar",
     "items": ["awaaz ka encrypted fingerprint (audio nahi)"], "purpose": "kaun bol raha hai pehchanna", "basis": "consent",
     "retention": "jab tak aap rakhein", "days": None, "processors": ["Hoola (Newtika Pvt Ltd) server"]},
    {"key": "travel", "label": "Travel: yatri", "tables": ["travel_trips"], "people": "graahak / parivaar", "items": ["naam", "umar", "ID (locker mein)"],
     "purpose": "ticket / hotel booking", "basis": "voluntary", "retention": "safar ke baad: aapka niyam", "days": 365,
     "processors": ["IRCTC / airline / hotel site", "Hoola (Newtika Pvt Ltd) server"]},
    {"key": "sitesup", "label": "Site labour register", "tables": ["sitesup_labour"], "people": "majdoor", "items": ["naam", "hazri", "ghante"],
     "purpose": "hazri aur wage register", "basis": "employment", "retention": "labour kanoon ke hisaab se", "days": None,
     "processors": ["Hoola (Newtika Pvt Ltd) server"], "law_hold": True},
]
CATALOG = {c["key"]: c for c in ROPA_CATALOG}

# modules where Hoola can find a person by phone (table, phone column, id column, eraser key)
FINDERS = [
    ("telecall", "Telecaller lead", "tele_leads", "phone", "id", "telecall"),
    ("shikayat", "Shikayat", "shikayat_cases", "phone", "id", "shikayat"),
    ("callcentre", "Call centre caller", "callcentre_callers", "key", "id", "callcentre"),
    ("wapsi", "Return", "wapsi_returns", "phone", "id", "wapsi"),
    ("courier", "Parcel", "courier_parcels", "phone", "id", "courier"),
    ("propagent", "Property lead", "propagent_leads", "phone", "id", "propagent"),
    ("darzi", "Darzi graahak", "darzi_customers", "phone", "id", ""),
    ("mshop", "Mobile dukaan graahak", "mshop_customers", "phone", "id", ""),
    ("insure", "Bima client", "ins_clients", "phone", "id", ""),
    ("aftersales", "After-sales graahak", "aftersales_customers", "phone", "id", ""),
    ("thok", "Wholesale party", "thok_parties", "phone", "id", ""),
]

# ---------------------------------------------------------------- DPIA + processor (DPA) checklists
DPIA_QUESTIONS = [
    ("purpose", "Kaam saaf likha hai aur sirf utna data lete hain jitna zaroori (data minimisation)?", False),
    ("children", "Isme bachchon (18 se kam) ka data hai?", True),
    ("health_fin", "Health, paisa / bank, ID number, awaaz / chehra jaisa jokhim wala data?", True),
    ("scale", "Bahut zyada logon ka data (hazaaron) ya roz badhta hua?", True),
    ("new_tech", "Naya tareeka: AI faisla, profiling, location tracking, camera?", True),
    ("abroad", "Data India ke bahar jaata hai (kisi vendor ke server par)?", True),
    ("sharing", "Kisi teesre (vendor / partner) ko data jaata hai?", True),
    ("security", "Encryption / masking, access control, backup aur 1 saal ke logs hain (Rule 6)?", False),
    ("consent_ok", "Notice dikhaya aur consent ka record hai (ya s.7 ka saaf aadhaar)?", False),
    ("erase_ok", "Kaam poora hone par mitaane ka schedule hai?", False),
]

DPA_CLAUSES = [
    ("instructions", "Vendor sirf aapke likhe kaam ke liye data use karega (aapke kehne par hi)"),
    ("security", "Suraksha: encryption / masking, access control, logs, backup (Rule 6 jaisa)"),
    ("breach", "Breach ka pata chalte hi turant aapko batayega (aapko 72 ghante mein Board ko report deni hai)"),
    ("subprocessor", "Aapki likhit ijazat ke bina aage kisi aur ko nahi dega"),
    ("staff", "Uske staff par confidentiality"),
    ("erase", "Kaam khatam / contract khatam par data wapas ya mita kar likhit confirm"),
    ("help_rights", "Logon ki maang (access / sudhaar / mitaana) mein madad karega"),
    ("location", "Data kahan rakha jaata hai (desh) likha ho; India ke bahar ho to sarkar ki rok wali list dekhiye"),
    ("audit", "Aap jaanch / audit report maang sakti hain"),
    ("logs", "Processing ke logs kam se kam 1 saal (Rule 8(3))"),
    ("liability", "Galti par zimmedari / muavza (aapke vakil ke shabdon mein)"),
]

CHILD_RISK_WORDS = re.compile(r"\b(ad|ads|advert|target|marketing|promotion|track|tracking|location|profil|behaviou?r|monitor)", re.I)


def dpia_score(answers: dict) -> tuple[int, str, list[str]]:
    """Risk: each risky 'yes' +2, each missing safeguard ('no' to a safeguard question) +2. 0-4 low, 5-8 medium, 9+ high."""
    score, notes = 0, []
    for key, q, risky in DPIA_QUESTIONS:
        v = answers.get(key)
        if v is None:
            notes.append(f"Jawab baaki: {q}")
            continue
        if risky and bool(v):
            score += 2
            notes.append(f"Jokhim: {q}")
        if not risky and not bool(v):
            score += 2
            notes.append(f"Kami: {q}")
    level = "high" if score >= 9 else ("medium" if score >= 5 else "low")
    return score, level, notes


def child_flags(activity: dict) -> list[str]:
    out = []
    if not activity.get("children"):
        return out
    out.append("Bachchon ka data: processing se PEHLE maa-baap ki verifiable consent (s.9(1), Rule 10). Hoola sirf kaise verify kiya "
               "uska tareeka aur reference rakhega, unka ID number nahi.")
    txt = " ".join([activity.get("purpose") or "", " ".join(activity.get("items") or [])])
    if CHILD_RISK_WORDS.search(txt):
        out.append("Bachchon ki tracking, behaviour monitoring ya un par targeted ads mana hain (s.9(3)): yeh kaam hata dijiye.")
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
    t = re.sub(r"\b(otp|pin|cvv|password|passcode|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[hataya]", t)
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
        out.append(f"Notice, consent, rights, breach, retention, bachchon ke niyam {MAIN_DUTIES_FROM.strftime('%d-%m-%Y')} se lagu "
                   "(Rules 3, 5-16). Abhi se taiyaari achhi hai; Board ke niyam 13-11-2025 se lagu hain.")
    if today < CONSENT_MANAGER_FROM:
        out.append(f"Consent manager (Rule 4) {CONSENT_MANAGER_FROM.strftime('%d-%m-%Y')} se.")
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
        f"{org or BLANK} se zaroori soochna: aapke data se judi ek suraksha ghatna (data breach).",
        f"Kya hua: {b.get('nature') or BLANK}. Kitna: {b.get('extent') or BLANK}. Kab: {b.get('when') or BLANK}.",
        f"Aap par asar ho sakta hai: {b.get('consequences') or BLANK}.",
        f"Humne kya kiya / kar rahe hain: {b.get('measures') or BLANK}.",
        f"Aap kya kar sakte hain: {b.get('safety') or BLANK}. Hum kabhi OTP / PIN / password nahi maangte.",
        f"Sawaal ke liye: {contact or BLANK}.",
    ])


def breach_initial_text(b: dict, org: str) -> str:
    """Rule 7(2)(a): without delay to the Board: description incl. nature, extent, timing, location and likely impact."""
    return "\n".join([
        f"Personal data breach: pehli soochna (Rule 7(2)(a)) - {org or BLANK}",
        f"Pata chala: {b.get('aware_text') or BLANK}",
        f"Prakriti (nature): {b.get('nature') or BLANK}",
        f"Vistaar (extent: kitne log / records, kaunsa data): {b.get('extent') or BLANK}",
        f"Samay (timing): {b.get('when') or BLANK}",
        f"Jagah (location / system): {b.get('location') or BLANK}",
        f"Sambhavit asar (likely impact): {b.get('impact') or BLANK}",
    ])


def breach_report_text(b: dict, org: str) -> str:
    """Rule 7(2)(b): within 72 h: (i) updated details, (ii) broad facts / reasons, (iii) mitigation, (iv) findings on who caused it,
    (v) remedial steps against recurrence, (vi) report on intimations given to affected people."""
    return "\n".join([
        f"Personal data breach: 72 ghante ki report (Rule 7(2)(b)) - {org or BLANK}",
        f"(i) Taaza aur poori jaankari: {b.get('details') or b.get('nature') or BLANK}",
        f"(ii) Ghatna, haalaat aur wajah: {b.get('cause') or BLANK}",
        f"(iii) Jokhim kam karne ke kadam (kiye / prastaavit): {b.get('measures') or BLANK}",
        f"(iv) Kisne kiya, uske baare mein jo mila: {b.get('findings') or BLANK}",
        f"(v) Dobara na ho, uske liye sudhaar: {b.get('remedial') or BLANK}",
        f"(vi) Prabhavit logon ko soochna ki report: {b.get('people_report') or BLANK}",
    ])


BREACH_FIELDS = ("nature", "extent", "when", "location", "impact", "consequences", "measures", "safety", "cause", "findings",
                 "remedial", "details", "systems", "people_report")

# ---------------------------------------------------------------- reply drafts to a request
def reply_text(kind: str, name: str, org: str, number: str, body: str, contact: str) -> str:
    head = f"Namaste {name or ''},".replace(" ,", ",")
    k = KINDS.get(kind, ("Aapki maang", ""))[0]
    return "\n".join([
        head,
        f"Aapki maang {number} ({k}) {org or BLANK} ko mili.",
        body or BLANK,
        "Hamare jawab se santusht na hon to aap Data Protection Board of India mein shikayat kar sakte hain.",
        f"Sampark: {contact or BLANK}",
    ])


NEVER = [
    "Kanooni salah nahi: har draft vakil / CA / CS se pakka karwaiye.",
    "Notice publish, logon ko jawab, data mitaana, Board / logon ko breach soochna: sirf aapke app tap se (card + hash).",
    "Pehchaan ke liye Aadhaar / PAN number nahi: sirf tareeka aur reference (ID aaye to Pehchaan Locker mein).",
    "Section / taarikh / jurmana khud se nahi banata: jo source padha wahi; baaki [____].",
    "Kisi ka data kisi aur ko nahi; logs mein number chhupe.",
    "Hoola kisi portal par khud file nahi karta; Board / CERT-In ko aap apne channel se bhejti hain.",
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
