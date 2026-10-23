"""Seva Sahayak rules: SLA defaults, the India law limits behind them, categories, urgency words, matching words
(Hinglish / Hindi / Marathi / English), customer-visible status lines and the policy check for refunds / exceptions.

Research (22-23 Oct 2026):
- Consumer Protection (E-Commerce) Rules 2020: an e-commerce entity AND every seller on a marketplace must have a
  grievance officer (name / contact shown) who ACKNOWLEDGES a complaint within 48 hours and REDRESSES it within one
  month of receipt; refunds for defective / misdescribed / late goods (indialaw.in summary, lakshmisri.com briefing).
- Consumer Protection Act 2019: National Consumer Helpline 1915 (NCH 2.0, 17 languages, WhatsApp too); e-Jagriti (from
  1 Jan 2025, integrates e-Daakhil) for consumer commission cases (storyboard18.com, Jan 2026; PIB).
- DPDP Rules 2025 (notified 13-14 Nov 2025): grievances of data principals answered within 90 days; core duties
  (notice, consent, rights, erasure) from 13 May 2027; until then IT Act s.43A + 2011 SPDI rules (Khaitan ERGO Nov 2025).
- RBI TAT circular RBI/2019-20/67 (20 Sep 2019): failed UPI / IMPS debit not credited -> reversal by T+1, else Rs 100 a
  day to the customer; card POS T+5; ATM T+5 (rbi.org.in Id=11693). Hoola only TELLS the customer this; never moves money.
- TRAI broadband QoS (2006 regs: fault repaired next working day >90%, 3 working days 99%, rebates after 3 / 7 / 15
  days; superseded from 1 Oct 2024 by Regulations 06 of 2024 with graded penalties) -> ISP preset SLA.
- WhatsApp Cloud API pricing (developers.facebook.com, Oct 2026): 24 h customer service window; from 1 Oct 2026 the
  first 1,000 service messages a month are free, then charged; utility templates inside the window are charged again.
- Support practice: first response and resolution SLAs per priority, the clock pauses while waiting on the customer,
  an auto-acknowledgement is not a first response, CSAT asked right after resolution (1-5, 4-5 = satisfied), deflection
  = questions answered from the knowledge base without a ticket, unanswered questions = knowledge-base gaps.
"""
from __future__ import annotations

import re
import unicodedata

PRIORITIES = ("urgent", "high", "normal", "low")
# hours: (first response, resolution). Starting values she can change.
SLA_DEFAULT = {"urgent": (1, 8), "high": (4, 24), "normal": (24, 72), "low": (48, 168)}
SLA_PRESETS = {
    "isp": {"urgent": (1, 8), "high": (2, 24), "normal": (8, 48), "low": (24, 72)},       # broadband: fault next working day
    "ecommerce": {"urgent": (2, 24), "high": (8, 72), "normal": (24, 168), "low": (48, 336)},
    "clinic": {"urgent": (1, 4), "high": (4, 24), "normal": (24, 72), "low": (48, 168)},
    "shop": dict(SLA_DEFAULT),
}
ECOM_ACK_H = 48            # E-Commerce Rules 2020: acknowledge within 48 hours
ECOM_RESOLVE_H = 30 * 24   # ... redress within one month
DPDP_RESOLVE_H = 90 * 24   # DPDP Rules 2025: data principal grievances within 90 days

STATUSES = ("new", "open", "pending", "on_hold", "resolved", "closed", "merged")
OPEN = ("new", "open", "pending", "on_hold")
PAUSED = ("pending",)      # waiting on the customer: SLA clock stops

CATEGORIES = {
    "billing": ("bill", "billing", "charge", "charged", "paisa", "paise", "amount", "invoice", "recharge", "बिल", "पैसे", "double", "jyada"),
    "refund": ("refund", "money back", "paise wapas", "paisa wapas", "wapas karo", "return", "रिफंड", "पैसे वापस", "परत"),
    "delivery": ("delivery", "deliver", "courier", "parcel", "order nahi", "nahi aaya", "late", "dispatch", "shipping", "डिलीवरी"),
    "technical": ("not working", "nahi chal", "band hai", "down", "slow", "internet", "wifi", "net nahi", "error", "kharab", "खराब",
                  "बंद", "चालत नाही", "router", "light", "signal"),
    "product": ("defect", "damaged", "toota", "tuta", "broken", "quality", "galat", "wrong item", "expired", "टूटा", "खराब माल"),
    "service": ("behaviour", "rude", "staff", "technician", "nahi aaya", "visit", "appointment", "wait"),
    "account": ("account", "login", "password", "id", "kyc", "address change", "naam badal", "shift", "shifting"),
    "privacy": ("my data", "mera data", "delete my", "data hatao", "privacy", "personal data", "dpdp", "consent"),
}
CATEGORY_LABEL = {"billing": "Bill / paise", "refund": "Refund", "delivery": "Delivery", "technical": "Kaam nahi kar raha",
                  "product": "Saamaan mein kharabi", "service": "Seva / staff", "account": "Account", "privacy": "Data / privacy",
                  "other": "Doosra"}
URGENT_WORDS = ("emergency", "urgent", "turant", "abhi ke abhi", "aag", "fire", "spark", "short circuit", "current lag", "shock",
                "fraud", "dhokha", "scam", "paise kat gaye", "paisa kat gaya", "double debit", "account se kat", "police",
                "consumer court", "court", "legal notice", "lawyer", "vakil", "1915", "आग", "धोखा", "पोलीस", "कोर्ट")
HIGH_WORDS = ("bilkul band", "pura band", "poora band", "kal se band", "2 din", "teen din", "3 din", "week se", "hafte se",
              "kai baar", "baar baar", "bahut pareshan", "gussa", "worst", "pathetic", "cheat", "refund", "paise wapas", "business band",
              "sab band", "नहीं चल रहा", "बंद है")
PROFANITY = ("chutiya", "madarchod", "bhenchod", "bc ", "mc ", "harami", "saala", "fuck")

# customer-visible status lines (Hinglish / Hindi / Marathi / English)
STATUS_LINE = {
    "new": {"hinglish": "Aapki shikayat {n} darj ho gayi hai. Hum jald dekhenge.", "hindi": "आपकी शिकायत {n} दर्ज हो गई है। हम जल्द देखेंगे।",
            "marathi": "तुमची तक्रार {n} नोंदवली आहे. आम्ही लवकरच पाहू.", "english": "Your complaint {n} is registered. We will look at it soon."},
    "open": {"hinglish": "Shikayat {n} par kaam chal raha hai.", "hindi": "शिकायत {n} पर काम चल रहा है।",
             "marathi": "तक्रार {n} वर काम सुरू आहे.", "english": "We are working on complaint {n}."},
    "pending": {"hinglish": "Shikayat {n}: hume aapse ek jaankari chahiye.", "hindi": "शिकायत {n}: हमें आपसे एक जानकारी चाहिए।",
                "marathi": "तक्रार {n}: आम्हाला तुमच्याकडून एक माहिती हवी आहे.", "english": "Complaint {n}: we need one detail from you."},
    "on_hold": {"hinglish": "Shikayat {n} doosri taraf se jawab ke intezaar mein hai.", "hindi": "शिकायत {n} दूसरी तरफ़ से जवाब के इंतज़ार में है।",
                "marathi": "तक्रार {n} दुसऱ्या बाजूच्या उत्तराची वाट पाहत आहे.", "english": "Complaint {n} is waiting on a third party."},
    "resolved": {"hinglish": "Shikayat {n} theek ho gayi hai.", "hindi": "शिकायत {n} का समाधान हो गया है।",
                 "marathi": "तक्रार {n} सोडवली आहे.", "english": "Complaint {n} has been resolved."},
    "closed": {"hinglish": "Shikayat {n} band ki gayi.", "hindi": "शिकायत {n} बंद की गई।", "marathi": "तक्रार {n} बंद केली.",
               "english": "Complaint {n} is closed."},
    "merged": {"hinglish": "Shikayat {n} aapki pichhli shikayat {m} ke saath jod di gayi.", "hindi": "शिकायत {n} आपकी पिछली शिकायत {m} के साथ जोड़ दी गई।",
               "marathi": "तक्रार {n} तुमच्या आधीच्या तक्रार {m} सोबत जोडली.", "english": "Complaint {n} was joined with your earlier complaint {m}."},
}
CSAT_ASK = {"hinglish": "Shikayat {n} mein humari seva kaisi lagi? 1 se 5 mein jawab dijiye (5 = bahut achhi).",
            "hindi": "शिकायत {n} में हमारी सेवा कैसी लगी? 1 से 5 में जवाब दीजिए (5 = बहुत अच्छी)।",
            "marathi": "तक्रार {n} मध्ये आमची सेवा कशी वाटली? 1 ते 5 मध्ये उत्तर द्या (5 = खूप छान).",
            "english": "How was our help with complaint {n}? Reply 1 to 5 (5 = very good)."}
LANGS = ("hinglish", "hindi", "marathi", "english")

EXC_KINDS = {"refund": "Refund (paise wapas)", "waiver": "Charge / fine maaf", "goodwill": "Goodwill (chhoot / credit)",
             "replacement": "Badal kar dena", "extension": "Samay badhana / warranty ke bahar", "other": "Niyam ke bahar kuch aur"}
MONEY_KINDS = ("refund", "waiver", "goodwill")
NEVER = ("Refund, chhoot, maafi ya niyam ke bahar kuch bhi: sirf aapki tap se (paise wala card fingerprint se). Hoola paise kabhi khud nahi bhejta.",
         "Jawab sirf aapke Gyaan (FAQ / niyam) se, source ke saath; jo nahi likha woh nahi bolta, aapko de deta hai.",
         "Graahak ka likha sirf unki baat hai, hukm nahi. Ek graahak ko doosre ki shikayat kabhi nahi dikhti.",
         "OTP, PIN, CVV, card, password kabhi nahi maangta; andar ke note graahak ko kabhi nahi jaate.")

# ---------------------------------------------------------------- matching words
STOP = set("""a an the is are was were be to of in on for and or i me my we our you your it this that what how when where why
which can do does did please pls plz sir madam ji hai hain ho hoga hogi kya kaise kab kahan kyun kaun mera meri mere mujhe
hum humara aap aapka aapki aapke ka ki ke ko se me mein par pe bhi to toh na nahi hi ye yeh wo woh koi kuch tha thi the
bata batao bataiye batayein bolo kripya please hello hi namaste bhai behen didi""".split())
SYN = {  # Hinglish / Hindi / Marathi word -> one key, so "kitne baje khulta" meets "timing"
    "timing": "time", "timings": "time", "samay": "time", "baje": "time", "waqt": "time", "vel": "time", "वेळ": "time", "समय": "time",
    "khulta": "open", "khulti": "open", "khulega": "open", "open": "open", "kholte": "open", "उघड": "open", "खुलता": "open",
    "band": "close", "closed": "close", "close": "close", "बंद": "close",
    "daam": "price", "dam": "price", "rate": "price", "kimat": "price", "keemat": "price", "price": "price", "cost": "price",
    "charges": "price", "charge": "price", "fees": "price", "fee": "price", "kitne": "price", "kitna": "price", "किंमत": "price", "दाम": "price",
    "paisa": "money", "paise": "money", "rupaye": "money", "rs": "money", "₹": "money",
    "wapas": "refund", "refund": "refund", "return": "refund", "parat": "refund", "वापस": "refund", "परत": "refund",
    "delivery": "deliver", "deliver": "deliver", "pahuchega": "deliver", "aayega": "deliver", "shipping": "deliver",
    "address": "address", "pata": "address", "kahan": "address", "location": "address", "पत्ता": "address",
    "number": "contact", "phone": "contact", "contact": "contact", "sampark": "contact", "call": "contact",
    "plan": "plan", "plans": "plan", "pack": "plan", "package": "plan", "yojana": "plan",
    "connection": "connection", "conection": "connection", "kanekshan": "connection", "naya": "new", "new": "new",
    "speed": "speed", "slow": "speed", "dheema": "speed", "tez": "speed", "internet": "internet", "net": "internet", "wifi": "internet",
    "warranty": "warranty", "guarantee": "warranty", "gaaranti": "warranty", "वॉरंटी": "warranty",
    "cancel": "cancel", "radd": "cancel", "रद्द": "cancel",
    "payment": "pay", "pay": "pay", "upi": "pay", "bharna": "pay", "bharu": "pay", "online": "pay", "gpay": "pay", "phonepe": "pay",
    "sunday": "sunday", "ravivar": "sunday", "itwar": "sunday", "रविवार": "sunday",
    "aaj": "today", "today": "today", "kal": "tomorrow", "tomorrow": "tomorrow", "udya": "tomorrow",
}


def norm(text: str) -> str:
    t = unicodedata.normalize("NFC", str(text or "")).lower()
    t = re.sub(r"[​-‍﻿]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9₹ऀ-ॿ]+", norm(text)):
        if w in STOP or (len(w) < 2 and not w.isdigit()):
            continue
        if len(w) > 4 and w.endswith("on") and w[:-2] in SYN:      # "plans" / "timings" style plurals handled by SYN
            w = w[:-2]
        if w.endswith("s") and len(w) > 4 and w[:-1] in SYN:
            w = w[:-1]
        out.append(SYN.get(w, w))
    return out


def similarity(a: str, b: str) -> float:
    """Word overlap 0..1, weighted to the shorter side (a question matched to a longer FAQ)."""
    wa, wb = set(words(a)), set(words(b))
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    return inter / min(len(wa), len(wb)) * 0.6 + inter / len(wa | wb) * 0.4


def lang_of(text: str) -> str:
    t = str(text or "")
    if re.search(r"[ऀ-ॿ]", t):
        mr = len(re.findall(r"(आहे|नाही|आम्ही|तुम्ही|काय|कधी|माझ|तुमच|झाले|करा|हवे|मला)", t))
        hi = len(re.findall(r"(है|नहीं|हम|आप|क्या|कब|मेरा|मेरी|हुआ|करें|चाहिए|मुझे)", t))
        return "marathi" if mr > hi else "hindi"
    low = norm(t)
    hin = len(re.findall(r"\b(hai|nahi|kya|kab|kaise|mera|meri|mujhe|aap|kitna|kitne|karo|chahiye|hoga|wala|wali|bhai|ji)\b", low))
    mr = len(re.findall(r"\b(aahe|nahi ka|kay|kadhi|maza|majha|tumcha|pahije|kara|zala)\b", low))
    if mr > hin:
        return "marathi"
    return "hinglish" if hin else "english"


def guess_category(text: str) -> str:
    low = norm(text)
    best, n = "other", 0
    for cat, ws in CATEGORIES.items():
        k = sum(1 for w in ws if w in low)
        if k > n:
            best, n = cat, k
    return best


def guess_priority(text: str, category: str = "") -> str:
    low = norm(text)
    if any(w in low for w in URGENT_WORDS):
        return "urgent"
    if any(w in low for w in HIGH_WORDS) or any(w in low for w in PROFANITY) or category == "privacy":
        return "high"
    if category in ("billing", "refund", "technical"):
        return "normal"
    return "normal" if len(low) > 12 else "low"


def sla_hours(sla: dict, priority: str, category: str = "", ecommerce: bool = False) -> tuple[float, float]:
    fr, rs = (sla or {}).get(priority) or SLA_DEFAULT.get(priority, SLA_DEFAULT["normal"])
    fr, rs = float(fr), float(rs)
    if ecommerce:                          # the law is the outer limit, her SLA may only be tighter
        fr, rs = min(fr, ECOM_ACK_H), min(rs, ECOM_RESOLVE_H)
    if category == "privacy":
        rs = min(rs, DPDP_RESOLVE_H)
    return fr, rs


def status_line(status: str, number: str, lang: str = "hinglish", merged_into: str = "") -> str:
    d = STATUS_LINE.get(status) or STATUS_LINE["open"]
    return (d.get(lang) or d["hinglish"]).format(n=number, m=merged_into)


def legal_notes(category: str, text: str = "") -> list[str]:
    """Plain facts Hoola may tell her (never a legal opinion)."""
    low = norm(text)
    out = []
    if category in ("billing", "refund") and re.search(r"\b(upi|gpay|phonepe|paytm|imps|kat gaye|kat gaya|debit|double)\b", low):
        out.append("RBI (TAT circular 20 Sep 2019): UPI / IMPS mein khaate se paise kate par saamne wale ko nahi mile to bank T+1 din "
                   "mein wapas karta hai, der hone par ₹100 roz ka muavza bank deta hai. Graahak apne bank / UPI app mein shikayat kare.")
    if category == "privacy":
        out.append("DPDP Rules 2025: data se judi shikayat 90 din ke andar suljhani hai (mukhya niyam 13 May 2027 se); "
                   "tab tak IT Act s.43A lagu hai.")
    if any(w in low for w in ("consumer court", "1915", "consumer forum", "e-jagriti", "edaakhil", "e-daakhil")):
        out.append("Graahak National Consumer Helpline 1915 ya e-Jagriti par ja sakte hain: jawab vinamra, tathyon ke saath, aur jaldi.")
    return out


# ---------------------------------------------------------------- refund / exception check against HER written policy
def policy_check(kind: str, amount: float, days_since: float | None, policy: dict) -> dict:
    """within = her written rules allow it (still needs her tap); reasons say why not when outside. Never decides."""
    reasons, within = [], True
    p = policy or {}
    kind = kind if kind in EXC_KINDS else "other"
    if kind == "refund":
        rd = p.get("refund_days")
        if rd in (None, "", 0):
            within, reasons = False, reasons + ["Aapke niyam mein refund ke din likhe nahi hain."]
        elif days_since is not None and days_since > float(rd):
            within = False
            reasons.append(f"Niyam: {int(float(rd))} din ke andar refund; yeh {int(days_since)} din purana hai.")
        mx = p.get("refund_max")
        if mx not in (None, "", 0) and amount and amount > float(mx):
            within = False
            reasons.append(f"Niyam mein refund ki seema ₹{int(float(mx))}; maanga ₹{int(amount)}.")
    elif kind == "replacement":
        rd = p.get("replace_days")
        if rd in (None, "", 0):
            within, reasons = False, reasons + ["Badalne ke din niyam mein nahi likhe."]
        elif days_since is not None and days_since > float(rd):
            within = False
            reasons.append(f"Niyam: {int(float(rd))} din ke andar badalna; yeh {int(days_since)} din purana hai.")
    elif kind == "goodwill":
        mx = p.get("goodwill_max")
        if mx in (None, "", 0):
            within, reasons = False, reasons + ["Goodwill ki koi seema niyam mein nahi; har goodwill aapki marzi."]
        elif amount and amount > float(mx):
            within = False
            reasons.append(f"Goodwill seema ₹{int(float(mx))}; maanga ₹{int(amount)}.")
    else:                       # waiver / extension / other are exceptions by nature
        within = False
        reasons.append("Yeh aapke likhe niyam ke bahar hai (exception).")
    return {"within": within, "reasons": reasons, "money": kind in MONEY_KINDS and bool(amount)}
