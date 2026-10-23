"""Propagent Sahayak rules (pure functions, no DB): money words, a buyer's / tenant's need from her words, RERA numbers,
listing checks, matching, stamp duty / registration estimate ONLY from her rates, TDS notes (Income-tax Act 2025 numbers),
commission + GST, document checklists, NRI notes, visit order."""
from __future__ import annotations

import re
from typing import Any, Callable

SOURCES = [
    ("RERA agent registration (MahaRERA: Rs 10,590 individual / Rs 1,00,590 firm, 5 years, Certificate of Competency mandatory "
     "since 1 Jan 2024; s.62 penalty Rs 10,000 a day up to 5% of the unit cost)", "https://calcguru.in/?p=4950", "2026"),
    ("MahaRERA: QR code (top right) + project registration number + website on every ad of a registered project; up to "
     "Rs 50,000 penalty, 10 days to fix (order 8 Apr 2025, mandate from 1 Aug 2023)",
     "https://therealtytoday.com/news/regulatory/maharera-makes-qr-code-registration-number-mandatory-in-ads-50000-penalty-for-violations/",
     "2025-04-12"),
    ("QR code display in MahaRERA-registered projects mandatory from 1 Aug 2023",
     "https://housing.com/news/qr-code-display-in-all-maharera-registered-projects-mandatory-from-aug-1-2023/", "2023"),
    ("TDS on purchase of immovable property: Income-tax Act 2025 s.393(1) Table Sl. 3(i) (old 194-IA), 1% when the total "
     "consideration is Rs 50 lakh or more, from 1 Apr 2026; NRI seller = the non-resident rule (old s.195)",
     "https://blog.tdsman.com/2026/05/tds-on-purchase-of-immovable-property-section-3931-194ia/", "2026-05"),
    ("TDS on brokerage / commission: s.393(1) Table Sl. 1(ii) (old 194H), 2%, above Rs 20,000 a year, from 1 Apr 2026",
     "https://blog.tdsman.com/2026/06/tds-on-brokerage-and-commission-section-3931-section-194h/", "2026-06"),
    ("TDS on rent paid by an individual / HUF (old 194-IB): s.393(1) Table Sl. 2(i), 2% when rent is above Rs 50,000 a month, "
     "once for the last month of the year / tenancy, PAN enough (no TAN)", "https://calcguru.in/?p=5521", "2026-08"),
    ("GST on real estate brokerage: SAC 997222 'building sales on a fee / commission basis', 18% (unchanged after GST 2.0, "
     "22 Sep 2025); leasing brokerage code to be confirmed by her CA", "https://busy.in/sac-code-997222/", "2026"),
    ("Property portals (99acres, MagicBricks, Housing, NoBroker) publish no public listing API: only scrapers exist, which "
     "Hoola never uses; she posts from her own portal account", "https://www.scrapingbee.com/scrapers/magicbricks-api/", "2026-10"),
]

NEVER = [
    "Listing public (page / portal / poster / WhatsApp) bina aapki haan ke card ke",
    "Graahak ya malik ko koi message bina aapke tap ke (Hoola sirf draft banata hai, aap bhejti hain)",
    "Token receipt / offer letter / commission bill jaise kaagaz jisme paise likhe hon, bina aapki haan ke",
    "Daam, kiraya, area, stamp duty, ready reckoner rate ya taarikh khud se gadhna",
    "Paise lena / dena / token collect karna",
    "Property portals / RERA / IGR site scrape karna",
    "Aadhaar / PAN ka poora number rakhna (sirf Pehchaan Locker ka reference)",
    "Kanooni salah dena: agreement sirf draft hai, vakil se check karwaiye",
]

PURPOSES = {"sale": "Bikri", "rent": "Kiraya", "lease": "Lease"}
KINDS = {"flat": "Flat", "house": "Ghar / bungalow", "row_house": "Row house", "plot": "Plot", "shop": "Dukaan",
         "office": "Office", "warehouse": "Godown", "land": "Zameen / khet", "pg": "PG / room"}
STATUSES = {"draft": "Draft", "active": "Chalu", "on_hold": "Ruka", "under_offer": "Baat chal rahi", "sold": "Bik gaya",
            "rented": "Kiraye par gaya", "withdrawn": "Hataya"}
LEAD_STAGES = {"new": "Naya", "contacted": "Baat hui", "visiting": "Visit", "negotiating": "Mol-bhav", "deal": "Deal",
               "lost": "Nahi hua", "closed": "Poora"}
SOURCES_LEAD = {"walk_in": "walk_in", "call": "enquiry", "enquiry": "enquiry", "portal": "enquiry", "website": "website",
                "referral": "referral", "whatsapp": "whatsapp", "hoarding": "enquiry", "ads": "ads_form", "cold": "cold"}
FURNISH = {"unfurnished": ["unfurnished", "khaali", "bina furniture"], "semi": ["semi", "semi furnished", "semi-furnished"],
           "full": ["fully furnished", "full furnished", "furnished"]}

_KIND_WORDS = [("row_house", r"row\s*house|rowhouse"), ("plot", r"\bplot|\bna plot|jagah"), ("shop", r"\bshop|dukaan|dukan|gala"),
               ("office", r"\boffice|daftar"), ("warehouse", r"godown|warehouse|gowdown"), ("land", r"\bland\b|khet|zameen|jameen|acre|guntha"),
               ("pg", r"\bpg\b|paying guest|\broom\b|kholi"), ("house", r"bungalow|banglow|\bhouse\b|independent|\bghar\b|makaan"),
               ("flat", r"\bflat|apartment|\bbhk\b|\d\s*bhk|\brk\b")]


# ---------------------------------------------------------------- money
def money(text: Any) -> float | None:
    """'45 lakh' / '45L' / '1.2 cr' / '25k' / '₹25,000' / 4500000 -> rupees. None when there is no amount."""
    if text is None or text == "":
        return None
    if isinstance(text, (int, float)):
        return float(text) if text > 0 else None
    s = str(text).lower().replace(",", "").replace("₹", " ").replace("rs.", " ").replace("rs", " ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(crore|cr\b|c\b|lakh|lac|lakhs|l\b|thousand|hazaar|hazar|k\b)?", s)
    if not m:
        return None
    n = float(m.group(1))
    u = (m.group(2) or "").strip()
    mult = {"crore": 1e7, "cr": 1e7, "c": 1e7, "lakh": 1e5, "lac": 1e5, "lakhs": 1e5, "l": 1e5,
            "thousand": 1e3, "hazaar": 1e3, "hazar": 1e3, "k": 1e3}.get(u, 1)
    v = n * mult
    return v if v > 0 else None


def short(v: float | None) -> str:
    if not v:
        return ""
    if v >= 1e7:
        return f"₹{v / 1e7:.2f}".rstrip("0").rstrip(".") + " cr"
    if v >= 1e5:
        return f"₹{v / 1e5:.2f}".rstrip("0").rstrip(".") + " lakh"
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.0f}"


def phone(p: Any) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def mask_phone(p: str) -> str:
    return (p[:2] + "XXXX" + p[-4:]) if len(p) == 10 else ""


def kind_of(text: str) -> str:
    low = (text or "").lower()
    for k, pat in _KIND_WORDS:
        if re.search(pat, low):
            return k
    return ""


def purpose_of(text: str) -> str:
    low = (text or "").lower()
    if re.search(r"\blease\b|leasing", low):
        return "lease"
    if re.search(r"kiray|kiraye|kiraya|\brent|rental|tenant|bhade|bhaade|bhada|bhaadekari", low):
        return "rent"
    if re.search(r"khareed|kharid|\bbuy|\bsale|bechna|bikri|resale|investment|vikat", low):
        return "sale"
    return ""


def furnishing_of(text: str) -> str:
    low = (text or "").lower()
    for k in ("unfurnished", "semi", "full"):
        if any(w in low for w in FURNISH[k]):
            return k
    return ""


def parse_need(text: str) -> dict[str, Any]:
    """A buyer's / tenant's words -> {purpose, kind, bhk [..], budget_min, budget_max, localities [..], furnishing, nri, loan}.
    Only what is in the words; nothing is guessed."""
    t = text or ""
    low = t.lower()
    out: dict[str, Any] = {"purpose": purpose_of(t), "kind": kind_of(t), "bhk": [], "budget_min": None, "budget_max": None,
                           "localities": [], "furnishing": furnishing_of(t), "nri": bool(re.search(r"\bnri\b|abroad|videsh|dubai|usa\b", low)),
                           "loan": bool(re.search(r"\bloan\b|home loan|karz", low))}
    for a, b in re.findall(r"(\d)\s*(?:or|ya|/|-|se)\s*(\d)\s*bhk", low):
        out["bhk"] += [int(a), int(b)]
    for a in re.findall(r"(\d)\s*bhk", low):
        if int(a) not in out["bhk"]:
            out["bhk"].append(int(a))
    if re.search(r"\b1\s*rk\b|\brk\b", low) and 0 not in out["bhk"]:
        out["bhk"].append(0)
    out["bhk"] = sorted(set(out["bhk"]))
    if out["bhk"] and not out["kind"]:
        out["kind"] = "flat"
    unit = r"(?:crore|cr\b|lakh|lac|l\b|k\b|hazaar|hazar|thousand)"
    rng = re.search(rf"(\d+(?:\.\d+)?)\s*({unit})?\s*(?:se|to|-|–)\s*(\d+(?:\.\d+)?)\s*({unit})", low)
    if rng:
        u2 = rng.group(4)
        out["budget_min"] = money(f"{rng.group(1)} {rng.group(2) or u2}")
        out["budget_max"] = money(f"{rng.group(3)} {u2}")
    else:
        m = re.search(rf"(?:budget|tak|under|upto|up to|max|andar|within)?\s*(\d+(?:\.\d+)?)\s*({unit})\s*(?:tak|ke andar|max|under)?", low)
        if m:
            out["budget_max"] = money(f"{m.group(1)} {m.group(2)}")
    locs = re.findall(r"(?:\bin|\bmein|\bme|\bnear|\bpaas|area)\s+([A-Za-z][A-Za-z .]{2,30}?)(?=,|\.|$|\s+(?:mein|me|area|ke|ka|ki|budget|tak|\d))", t)
    locs += re.findall(r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\s+(?:mein|me|area|ke paas|side|ilake)\b", t)
    stop = {"budget", "rent", "sale", "flat", "kiraye", "range", "lakh", "the", "a", "bhk"}
    for l in locs:
        w = l.strip(" .").strip()
        if w and w.lower() not in stop and w.lower() not in out["localities"]:
            out["localities"].append(w)
    return out


# ---------------------------------------------------------------- RERA
def rera_project_ok(no: str, state: str = "MH") -> bool:
    s = re.sub(r"\s", "", no or "").upper()
    if not s:
        return False
    if state == "MH":
        return bool(re.fullmatch(r"P5\d{10}", s))
    return len(s) >= 6


def rera_agent_ok(no: str, state: str = "MH") -> bool:
    s = re.sub(r"\s", "", no or "").upper()
    if not s:
        return False
    if state == "MH":
        return bool(re.fullmatch(r"A5\d{10}", s))
    return len(s) >= 6


# ---------------------------------------------------------------- listing text claims
RISKY = [
    (r"guarantee|guaranteed|assured (?:return|rent)|pakka return|100\s*%\s*(?:return|loan|safe)", "Guaranteed / assured return ka waada"),
    (r"\b(?:best|no\.?\s*1|number one|sabse sasta|cheapest|lowest price)\b", "'Best / No.1 / sabse sasta' ka saboot chahiye"),
    (r"rera approved|rera certified|government approved|sarkari manzoor", "'RERA approved' jaisa shabd galat hai: RERA registered hota hai, approve nahi"),
    (r"\bclear title\b|title clear|no dispute|koi jhagda nahi", "'Clear title' tabhi likhiye jab search report aapke paas ho"),
    (r"(?:last|sirf|only)\s*\d+\s*(?:unit|flat|din|day)|jaldi karein|offer khatam", "Jhoothi jaldbaazi (dark pattern) se bachiye"),
    (r"\d+\s*(?:min|minute|mins)\s*(?:from|se|tak)", "Doori ka daava: Google Maps se check karke hi likhiye"),
]


def risky_claims(text: str) -> list[str]:
    low = (text or "").lower()
    out = [why for pat, why in RISKY if re.search(pat, low)]
    try:
        from ..kalam.service import claims_of
        for c in claims_of(text or ""):
            if "health" in c["kinds"] or "guarantee" in c["kinds"]:
                msg = f"Daava jaanchiye: \"{c['text'][:80]}\""
                if msg not in out:
                    out.append(msg)
    except Exception:
        pass
    return out


def numbers_in(text: str) -> set[str]:
    out = set()
    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or ""):
        n = n.replace(",", "")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n)
    return out


def listing_checks(L: dict, st: dict) -> dict[str, list[str]]:
    """Blockers (can't go public) and warnings. L = listing view, st = her settings view."""
    block, warn = [], []
    state = (st.get("state") or "MH").upper()
    if not L.get("purpose"):
        block.append("Bikri ya kiraya: batayiye.")
    if L.get("purpose") == "sale" and not L.get("price"):
        block.append("Daam chahiye (malik ka bataya hua): Hoola daam nahi gadhta.")
    if L.get("purpose") in ("rent", "lease") and not L.get("rent"):
        block.append("Mahine ka kiraya chahiye (malik ka bataya hua).")
    if not (L.get("locality") or L.get("city")):
        block.append("Ilaka / shehar chahiye.")
    if not (L.get("mandate") or {}).get("consent"):
        block.append("Malik ki haan (likhit / WhatsApp) ki bina listing public nahi: 'Malik ne haan kahi' darj kijiye.")
    if L.get("kind") not in ("plot", "land") and not L.get("carpet_sqft"):
        (block if L.get("new_project") else warn).append("Carpet area (RERA ki paribhasha) likhiye; super built-up akela galat samjha jaata hai.")
    if L.get("new_project") and L.get("purpose") == "sale":
        if not rera_project_ok(L.get("rera_project_no", ""), state):
            block.append("Naye project ka RERA registration number (MahaRERA: P5xxxxxxxxxx) har ad mein zaroori.")
        if state == "MH" and not L.get("has_qr"):
            block.append("MahaRERA QR code (project ke MahaRERA page wala) photo mein jodiye: har ad ke upar daayein kone mein zaroori.")
        if not rera_agent_ok(st.get("rera_agent_no", ""), state):
            block.append("Aapka RERA agent registration number (MahaRERA: A5xxxxxxxxxx) settings mein nahi: RERA project bechne ke liye zaroori (s.9 / s.10).")
        elif st.get("rera_expired"):
            block.append("Aapka RERA agent registration khatam ho gaya hai: renew kijiye.")
    elif st.get("rera_agent_no") and st.get("rera_expired"):
        warn.append("Aapka RERA agent registration khatam ho gaya hai.")
    if not L.get("photos"):
        warn.append("Photo nahi: listing bina photo kam chalti hai.")
    if L.get("built_sqft") and L.get("carpet_sqft") and L["built_sqft"] < L["carpet_sqft"]:
        warn.append("Built-up area carpet se kam likha hai: dobara dekhiye.")
    for c in risky_claims(L.get("description", "")):
        warn.append(c)
    return {"block": block, "warn": warn}


# ---------------------------------------------------------------- matching
def _lo(xs) -> list[str]:
    return [str(x).strip().lower() for x in (xs or []) if str(x).strip()]


def match(lead: dict, L: dict, stretch_pct: float = 10.0) -> dict[str, Any] | None:
    """Score one listing for one lead. None = does not fit (purpose / kind / status). Reasons in Hinglish."""
    if L.get("status") not in ("active", "under_offer"):
        return None
    lp = lead.get("purpose") or ""
    if lp and lp != L.get("purpose") and not ({lp, L.get("purpose")} <= {"rent", "lease"}):
        return None
    if lead.get("kind") and L.get("kind") and lead["kind"] != L["kind"]:
        return None
    score, why, miss = 40.0, [], []
    bhk = lead.get("bhk") or []
    if bhk:
        if L.get("bhk") in bhk:
            score += 15
            why.append(f"{L['bhk']} BHK jaisa chahiye")
        elif L.get("bhk") is not None:
            score -= 15
            miss.append(f"{L['bhk']} BHK hai ({'/'.join(map(str, bhk))} chahiye tha)")
    price = L.get("price") if L.get("purpose") == "sale" else L.get("rent")
    mx, mn = lead.get("budget_max"), lead.get("budget_min")
    if price and mx:
        if price <= mx:
            score += 20
            why.append(f"budget mein ({short(price)})")
        elif price <= mx * (1 + stretch_pct / 100):
            score += 5
            miss.append(f"budget se thoda upar ({short(price)} vs {short(mx)})")
        else:
            return None
        if mn and price < mn * 0.7:
            score -= 5
            miss.append("budget se kaafi kam: shayad unki pasand ka nahi")
    elif not price:
        miss.append("daam / kiraya pata nahi")
    locs = _lo(lead.get("localities"))
    here = " ".join(_lo([L.get("locality"), L.get("city"), L.get("project")]))
    if locs:
        if any(l in here for l in locs):
            score += 20
            why.append(f"ilaka {L.get('locality') or L.get('city')}")
        else:
            score -= 10
            miss.append(f"ilaka alag ({L.get('locality') or L.get('city') or '?'})")
    if lead.get("furnishing") and L.get("furnishing"):
        if lead["furnishing"] == L["furnishing"]:
            score += 5
            why.append("furnishing jaisa chahiye")
        else:
            miss.append(f"furnishing {L['furnishing']}")
    if lead.get("min_carpet") and L.get("carpet_sqft"):
        if L["carpet_sqft"] >= lead["min_carpet"]:
            score += 5
        else:
            miss.append(f"carpet {L['carpet_sqft']:.0f} sq ft (kam)")
    if lead.get("nri") and L.get("kind") in ("land",):
        return None                                     # FEMA: NRIs can't buy agricultural land / plantation / farmhouse
    if lead.get("loan") and L.get("purpose") == "sale" and L.get("new_project") and not L.get("rera_project_no"):
        miss.append("loan ke liye RERA number chahiye")
    if L.get("status") == "under_offer":
        score -= 10
        miss.append("is par pehle se baat chal rahi hai")
    return {"listing": L["id"], "number": L.get("number"), "score": round(max(0, min(100, score))), "why": why, "miss": miss}


# ---------------------------------------------------------------- stamp duty / registration (HER rates only)
def stamp_estimate(value: float, rates: dict | None, market_value: float | None = None, women: bool = False) -> dict[str, Any]:
    """value = agreed price; market_value = ready reckoner / guidance value she gives. Rates: {stamp_pct, cess_pct,
    women_less_pct, reg_pct, reg_cap, reg_flat} — all hers. Nothing missing is filled in."""
    r = rates or {}
    base = max(value or 0, market_value or 0)
    out: dict[str, Any] = {"base": base or None, "base_note": "", "missing": [], "stamp": None, "cess": None, "registration": None,
                           "total": None}
    if market_value and market_value > (value or 0):
        out["base_note"] = "Ready reckoner / guidance value daam se zyada: duty usi par lagti hai."
    elif not market_value:
        out["missing"].append("ready reckoner / guidance value (IGR se)")
    sp = r.get("stamp_pct")
    if sp in (None, ""):
        out["missing"].append("stamp duty % (aapke area ka)")
        return out
    sp = float(sp) - (float(r.get("women_less_pct") or 0) if women else 0)
    out["stamp"] = round(base * sp / 100)
    out["cess"] = round(base * float(r.get("cess_pct") or 0) / 100)
    if r.get("reg_flat"):
        out["registration"] = float(r["reg_flat"])
    elif r.get("reg_pct") not in (None, ""):
        reg = base * float(r["reg_pct"]) / 100
        if r.get("reg_cap"):
            reg = min(reg, float(r["reg_cap"]))
        out["registration"] = round(reg)
    else:
        out["missing"].append("registration fee (% aur cap)")
    out["total"] = (out["stamp"] or 0) + (out["cess"] or 0) + (out["registration"] or 0)
    out["note"] = "Sirf andaaza, aapke rates se: IGR / sub-registrar par pakka hoga."
    return out


# ---------------------------------------------------------------- TDS notes (Income-tax Act 2025)
def tds_sale(value: float, market_value: float | None = None, seller_nri: bool = False) -> dict[str, Any]:
    if seller_nri:
        return {"applies": True, "section": "Non-resident ke liye TDS (purana s.195)", "rate": None, "amount": None,
                "say": "Bechne wala NRI hai: kharidaar ko TAN lena hoga aur TDS capital gains ke rate (+ surcharge, cess) par kaatna hoga; "
                       "rate ya kam TDS certificate CA batayega. 1% wala niyam yahan nahi lagta."}
    base = max(value or 0, market_value or 0)
    if base < 50_00_000:
        return {"applies": False, "section": "s.393(1) Table Sl. 3(i) (purana 194-IA)", "rate": 1.0, "amount": 0,
                "say": "Kul keemat ₹50 lakh se kam: kharidaar par 1% TDS nahi."}
    amt = round((value or 0) * 0.01)
    return {"applies": True, "section": "s.393(1) Table Sl. 3(i) (purana 194-IA)", "rate": 1.0, "amount": amt,
            "say": f"Kharidaar har payment se 1% TDS kaatega (kul ~{short(amt)}), bechne wale ka PAN chahiye, TAN nahi; "
                   "challan-cum-statement (Form 26QB jaisa) samay par. CA se pakka karwaiye."}


def tds_rent(monthly: float | None, tenant_individual: bool = True) -> dict[str, Any]:
    if not monthly:
        return {"applies": False, "say": ""}
    if tenant_individual and monthly > 50_000:
        return {"applies": True, "section": "s.393(1) Table Sl. 2(i) (purana 194-IB)", "rate": 2.0,
                "say": "Kiraya ₹50,000 / mahina se upar: kirayedaar (individual) saal / tenancy ke aakhri mahine mein 2% TDS kaatega, "
                       "malik ka PAN chahiye."}
    if not tenant_individual:
        return {"applies": True, "section": "s.393(1) rent (purana 194-I)", "rate": None,
                "say": "Kirayedaar company / business hai: rent par TDS ke niyam lagenge; rate aur seema CA se."}
    return {"applies": False, "say": "Kiraya ₹50,000 / mahina tak: kirayedaar par TDS nahi."}


# ---------------------------------------------------------------- commission
def commission(base: float | None, pct: float | None = None, months: float | None = None, rent: float | None = None,
               gst_on: bool = False, gst_pct: float = 18.0) -> dict[str, Any]:
    """Her agreed brokerage: % of the price, or months of rent. GST only when she is registered (gst_on)."""
    amt = None
    how = ""
    if months and rent:
        amt, how = rent * months, f"{months:g} mahine ka kiraya"
    elif pct and base:
        amt, how = base * pct / 100, f"{pct:g}% of {short(base)}"
    if amt is None:
        return {"amount": None, "gst": None, "total": None, "how": "", "missing": "commission % / mahine (aapka tay kiya)"}
    gst = round(amt * gst_pct / 100) if gst_on else 0
    return {"amount": round(amt), "gst": gst, "total": round(amt) + gst, "how": how,
            "sac": "997222" if not rent else "9972 (CA se code pakka)", "gst_note": "" if gst_on else "GST registration nahi: GST nahi lagaya."}


def tds_on_commission(amount: float | None, payer_business: bool) -> str:
    if not amount or not payer_business:
        return ""
    if amount > 20_000:
        return "Dene wala business hai aur saal mein ₹20,000 se upar: woh 2% TDS (s.393(1) Sl. 1(ii), purana 194H) kaat sakta hai."
    return ""


# ---------------------------------------------------------------- checklists
def doc_checklist(purpose: str, kind: str, new_project: bool = False, loan: bool = False, society: bool = False,
                  buyer_nri: bool = False, seller_nri: bool = False, state: str = "MH") -> list[dict[str, str]]:
    out: list[tuple[str, str]] = []
    if purpose == "sale":
        out += [("title", "Title deed / pichhli bikri ke kaagaz (30 saal ki chain) + search report vakil se"),
                ("record", "7/12 utara ya property card / municipal record (malik ka naam)" if state == "MH" else "Land record / khata (malik ka naam)"),
                ("tax", "Property tax ki latest raseed + bijli bill"),
                ("ids", "Dono taraf ke PAN / Aadhaar (Pehchaan Locker reference)"),
                ("encumbrance", "Encumbrance / loan nahi hai ka saboot (bank NOC agar loan tha)")]
        if kind not in ("plot", "land"):
            out += [("oc", "Occupancy / completion certificate (OC / CC)"), ("plan", "Manzoor naksha (approved plan)")]
        if kind in ("plot", "land"):
            out += [("na", "NA order / zone certificate (khet ke liye)"), ("measure", "Naap / boundary (TILR / map)")]
        if new_project:
            out += [("rera", "Project ka RERA registration + carpet area wala agreement for sale (RERA model)"),
                    ("allot", "Allotment letter; 10% se zyada advance agreement registration se pehle nahi (RERA s.13)")]
        if society:
            out += [("society", "Society NOC + share certificate + maintenance clear raseed")]
        if loan:
            out += [("loan", "Kharidaar ka loan sanction letter")]
        if buyer_nri:
            out += [("nri_buy", "NRI kharidaar: payment bank se (NRE / NRO / FCNR), khet / farmhouse / plantation nahi (FEMA NDI Rules 2019)")]
        if seller_nri:
            out += [("nri_sell", "NRI bechne wala: kharidaar ka TAN, TDS, Form 15CA / 15CB (CA)")]
        out += [("stamp", "Stamp duty + registration (sub-registrar / IGR online); kharidaar khud bharega")]
    else:
        out += [("agreement", "Leave & licence / rent agreement (Maharashtra mein registration zaroori)" if state == "MH"
                 else "Rent agreement (state ke niyam se, registration)"),
                ("police", "Kirayedaar ki police verification (thane / online)"),
                ("ids", "Dono taraf ke ID (Pehchaan Locker reference)"),
                ("deposit", "Deposit ki raseed + society NOC (agar maange)"),
                ("inventory", "Ghar ka saaman / meter reading ki list")]
    return [{"key": k, "item": v, "done": False} for k, v in out]


def nri_notes(buyer_nri: bool, seller_nri: bool) -> list[str]:
    n = []
    if buyer_nri:
        n.append("NRI kharidaar: ghar / dukaan / office le sakte hain; khet, plantation, farmhouse nahi (FEMA NDI Rules 2019). "
                 "Payment India ke bank channel / NRE / NRO / FCNR se.")
    if seller_nri:
        n.append("NRI bechne wala: kharidaar ko TAN + non-resident TDS; paisa bahar bhejne ke liye Form 15CA / 15CB (CA).")
    return n


# ---------------------------------------------------------------- visit order
def visit_order(points: list[dict], dist: Callable[[str, str], float | None]) -> tuple[list[dict], bool]:
    """Nearest-next order from the first stop. If any distance is unknown, keep her order (False)."""
    if len(points) <= 2:
        return points, True
    left = points[1:]
    route = [points[0]]
    known = True
    while left:
        cur = route[-1]
        best, bd = None, None
        for p in left:
            d = dist(cur["where"], p["where"])
            if d is None:
                known = False
                break
            if bd is None or d < bd:
                best, bd = p, d
        if not known:
            return points, False
        route.append(best)
        left.remove(best)
    return route, True
