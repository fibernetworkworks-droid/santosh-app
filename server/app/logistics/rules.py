"""Rules the Logistics Sahayak works to (researched 23 Oct 2026; sources in WIRING.md / CLAUDE.md). Pure functions, no DB.

E-way bill (CGST Rule 138): needed when a consignment's value is above Rs 50,000 inter-state; intra-state limits are set by each
state (the same table Thok uses: `thok.rules.EWB_INTRA`). Part A = invoice / challan data (supplier, recipient, HSN, value, place
of delivery, document no / date, reason); Part B = vehicle number (road) or transport document (rail / air / ship). Part B is not
needed for movement up to 50 km inside the state from the consignor to the transporter's place (Rule 138(3) proviso). Validity
from Part B entry: 1 day up to 200 km, +1 day for every 200 km or part (over-dimensional cargo: 20 km per day); "one day" ends at
midnight of the day after the start. Extension can be asked from 8 hours before to 8 hours after expiry (portal); from 1 Jan 2025
an EWB can't be made for a document older than 180 days and can't be extended beyond 360 days from generation. Multi-factor login
on the EWB portal mandatory for everyone from 1 Apr 2025. Penalty for goods without a valid EWB: Rs 10,000 or the tax, whichever
higher, and the goods / vehicle can be detained (Sec 122 / 129 CGST).

Carriage by Road Act 2007 + Rules 2011: a common carrier needs a registration (s.3); the consignor signs a goods forwarding note
with the value and a dangerous-goods declaration (s.8); the carrier issues the goods receipt / consignment note in triplicate,
original to the consignor (s.9); liability for loss is limited to 10 x freight, not more than the declared value, unless a higher
risk rate was agreed (s.10-11, Rule 12(1)); a claim needs written notice within 180 days of booking (s.16).
GST: a transporter issuing a consignment note is a GTA; from 22 Sep 2025 GTA = 5% (no ITC, RCM or forward) or 18% with ITC.
Delivery challan (CGST Rule 55) for goods moving without an invoice (job work, approval, own use, line sales): serial no <= 16
characters, date, consignor / consignee with GSTIN, HSN, description, quantity, taxable value, tax where it is a supply, place of
supply, signature; three copies (consignee, transporter, consignor).
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from ..thok.rules import EWB_INTER, EWB_INTRA, money, r2  # noqa: F401  (one table for e-way limits across Hoola)

PART_B_FREE_KM = 50
KM_PER_DAY = 200
ODC_KM_PER_DAY = 20
EXTEND_WINDOW_H = 8
MAX_DOC_AGE_DAYS = 180
MAX_EXTEND_DAYS = 360
EWB_PENALTY = 10000
LIABILITY_X_FREIGHT = 10
CLAIM_NOTICE_DAYS = 180
GTA_RATES = (5.0, 18.0)

# NIC e-way bill masters (as used by the bulk-upload JSON / API)
SUB_SUPPLY = {"supply": 1, "import": 2, "export": 3, "job_work": 4, "own_use": 5, "job_work_return": 6, "sales_return": 7,
              "others": 8, "skd_ckd": 9, "line_sales": 10, "recipient_unknown": 11, "exhibition": 12}
DOC_TYPE = {"invoice": "INV", "bill_of_supply": "BIL", "bill_of_entry": "BOE", "challan": "CHL", "other": "OTH"}
TRANS_MODE = {"road": 1, "rail": 2, "air": 3, "ship": 4}
UQC = {"BAG", "BAL", "BDL", "BKL", "BOU", "BOX", "BTL", "BUN", "CAN", "CBM", "CCM", "CMS", "CTN", "DOZ", "DRM", "GGK", "GMS", "GRS",
       "GYD", "KGS", "KLR", "KME", "LTR", "MLT", "MTR", "MTS", "NOS", "PAC", "PCS", "PRS", "QTL", "ROL", "SET", "SQF", "SQM", "SQY",
       "TBS", "TGM", "THD", "TON", "TUB", "UGS", "UNT", "YDS", "OTH"}
UNIT_WORDS = {"bori": "BAG", "bag": "BAG", "bags": "BAG", "katta": "BAG", "kg": "KGS", "kgs": "KGS", "kilo": "KGS", "quintal": "QTL",
              "qtl": "QTL", "ton": "TON", "tonne": "TON", "mt": "MTS", "litre": "LTR", "liter": "LTR", "ltr": "LTR", "pc": "PCS", "pcs": "PCS",
              "piece": "PCS", "nag": "NOS", "nos": "NOS", "box": "BOX", "peti": "BOX", "carton": "CTN", "ctn": "CTN", "drum": "DRM",
              "roll": "ROL", "bundle": "BDL", "set": "SET", "dozen": "DOZ", "packet": "PAC", "pack": "PAC", "tin": "CAN", "bottle": "BTL"}

STATUSES = ("booked", "loaded", "dispatched", "in_transit", "reached_hub", "out_for_delivery", "delivered", "held", "breakdown",
            "delayed", "returned", "cancelled")
LABEL = {"booked": "Booking", "loaded": "Load ho gaya", "dispatched": "Nikal gaya", "in_transit": "Raste mein", "reached_hub": "Hub / godown pahuncha",
         "out_for_delivery": "Delivery ke liye nikla", "delivered": "Deliver ho gaya", "held": "Ruka hua (check / naka)", "breakdown": "Gaadi kharab",
         "delayed": "Der", "returned": "Wapas", "cancelled": "Cancel"}
OPEN = ("booked", "loaded", "dispatched", "in_transit", "reached_hub", "out_for_delivery", "held", "breakdown", "delayed")
MOVING = ("dispatched", "in_transit", "reached_hub", "out_for_delivery", "held", "breakdown", "delayed")
STATUS_WORDS = (("out_for_delivery", ("out for delivery", "delivery ke liye", "delivery pe nikla", "delivery par nikla")),
                ("delivered", ("deliver ho gaya", "delivered", "pahunch gaya graahak", "maal utar gaya", "unload ho gaya", "mil gaya")),
                ("breakdown", ("breakdown", "gaadi kharab", "puncture", "tyre phat", "engine band")),
                ("held", ("rok liya", "naka", "checkpost", "check post", "detain", "jaanch", "rto ne", "mobile squad")),
                ("reached_hub", ("hub", "godown pahuncha", "transhipment", "transit point")),
                ("returned", ("wapas aa raha", "return", "rto")),
                ("loaded", ("load ho gaya", "loaded", "loading ho gayi", "maal chadh gaya")),
                ("dispatched", ("nikal gaya", "nikal gayi", "dispatch", "rawana", "chal pada", "nikla")),
                ("in_transit", ("raste mein", "on the way", "in transit", "chal rahi", "highway")),
                ("cancelled", ("cancel",)))

NEVER = ("Graahak ko message sirf aapki haan / aapke bhejne se jaata hai (WhatsApp draft, ya business WhatsApp par aapka tap).",
         "E-way bill portal par banana / Part B badalna / extension = filing: sirf aapke tap se (GSP API ya aap khud portal par, OTP aapka).",
         "Tracking ki koi baat Hoola apne se nahi banata: sirf aapka / transporter / driver / courier ka bataya hua.",
         "Paisa Hoola na leta hai na bhejta hai (bhada, COD, claim).",
         "Driver ki location sirf woh jo aap / driver khud share kare.")

_VEH = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}$")
_VEH_BH = re.compile(r"^\d{2}BH\d{4}[A-Z]{1,2}$")
_VEH_TEMP = re.compile(r"^(T|TR|TMP)[A-Z0-9]{5,14}$")


def clean_vehicle(v: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def vehicle_ok(v: str) -> bool:
    v = clean_vehicle(v)
    return bool(v and (_VEH.match(v) or _VEH_BH.match(v) or _VEH_TEMP.match(v)))


def uqc(unit: str) -> str:
    u = str(unit or "").strip()
    up = u.upper()
    if up in UQC:
        return up
    return UNIT_WORDS.get(u.lower(), "OTH" if u else "NOS")


def ewb_needed(value: float, from_state: str, to_state: str) -> dict:
    """{needed, limit, intra, why}. from_state / to_state = GST state codes ('27')."""
    intra = not to_state or not from_state or from_state == to_state
    limit = EWB_INTRA.get(from_state, EWB_INTER) if intra else EWB_INTER
    need = float(value or 0) > limit
    where = "rajya ke andar" if intra else "doosre rajya"
    why = (f"Maal ki keemat Rs {value:,.0f} > Rs {limit:,.0f} ({where}): e-way bill zaroori." if need
           else f"Rs {value:,.0f} ({where}, limit Rs {limit:,.0f}): e-way bill zaroori nahi (job work / kuch khaas maal mein phir bhi lagta hai).")
    return {"needed": need, "limit": limit, "intra": intra, "why": why}


def validity_days(km: float, odc: bool = False) -> int:
    per = ODC_KM_PER_DAY if odc else KM_PER_DAY
    km = max(0.0, float(km or 0))
    return max(1, -(-int(round(km)) // per)) if km else 1


def valid_upto(start: datetime, km: float, odc: bool = False) -> datetime:
    """'One day' ends at midnight of the day after the start; each extra day adds 24 hours."""
    days = validity_days(km, odc)
    end_day = start.date() + timedelta(days=days)
    return datetime.combine(end_day, time(23, 59, 59), tzinfo=start.tzinfo)


def extend_window(upto: datetime) -> tuple[datetime, datetime]:
    return upto - timedelta(hours=EXTEND_WINDOW_H), upto + timedelta(hours=EXTEND_WINDOW_H)


def ewb_alert(upto: datetime | None, at: datetime, generated: datetime | None = None) -> dict | None:
    """Warn before the bill runs out while the goods are still moving."""
    if not upto:
        return None
    a, b = extend_window(upto)
    if generated and (at - generated).days >= MAX_EXTEND_DAYS:
        return {"level": "bad", "kind": "ewb_max", "text": "E-way bill 360 din se purana: ab extend nahi hoga, naya banana padega."}
    if at > b:
        return {"level": "bad", "kind": "ewb_expired", "text": "E-way bill khatam ho gaya aur extension ka samay bhi nikal gaya: maal ruk sakta hai (Rs 10,000 ya tax). Naya EWB banana padega."}
    if at > upto:
        return {"level": "bad", "kind": "ewb_expired",
                "text": f"E-way bill khatam: extension abhi ho sakta hai ({b.strftime('%d %b %H:%M')} tak)."}
    if at >= a:
        return {"level": "warn", "kind": "ewb_expiring",
                "text": f"E-way bill {upto.strftime('%d %b %H:%M')} ko khatam: maal raste mein hai to extension ab maang sakte hain."}
    if upto - at <= timedelta(hours=24):
        return {"level": "info", "kind": "ewb_soon", "text": f"E-way bill kal tak ({upto.strftime('%d %b %H:%M')}) valid."}
    return None


def part_b_needed(km: float, intra: bool, to_transporter_only: bool = False) -> bool:
    return not (intra and to_transporter_only and float(km or 0) <= PART_B_FREE_KM)


def doc_too_old(doc: date | None, on: date) -> bool:
    return bool(doc and (on - doc).days > MAX_DOC_AGE_DAYS)


def liability_cap(freight: float, declared: float, higher_risk: bool = False) -> dict:
    if higher_risk:
        return {"cap": float(declared or 0), "text": "Zyada risk rate tay hua: poori declared value tak zimmedari."}
    cap = min(LIABILITY_X_FREIGHT * float(freight or 0), float(declared or 0)) if declared else LIABILITY_X_FREIGHT * float(freight or 0)
    return {"cap": r2(cap), "text": f"Nuksaan par carrier ki zimmedari bhade ka 10 guna (Rs {cap:,.0f}) tak, declared value se zyada nahi (Rule 12(1))."}


def claim_by(booked: date) -> date:
    return booked + timedelta(days=CLAIM_NOTICE_DAYS)


def status_from_words(text: str) -> str:
    t = " " + str(text or "").lower() + " "
    for st, words in STATUS_WORDS:
        if any(w in t for w in words):
            return st
    return ""


_MAPS = (re.compile(r"[?&](?:q|query|ll|destination)=(-?\d{1,2}\.\d{3,}),\s*(-?\d{1,3}\.\d{3,})"),
         re.compile(r"@(-?\d{1,2}\.\d{3,}),(-?\d{1,3}\.\d{3,})"),
         re.compile(r"(?<![\d.])(-?\d{1,2}\.\d{4,})\s*,\s*(-?\d{1,3}\.\d{4,})(?![\d.])"))


def parse_location(text: str) -> dict | None:
    """A location the driver / she shared: Google Maps link with coordinates, or plain 'lat, lng'. Short links stay as links."""
    t = str(text or "")
    for rx in _MAPS:
        m = rx.search(t)
        if m:
            lat, lng = float(m.group(1)), float(m.group(2))
            if 6 <= lat <= 37.5 and 68 <= lng <= 97.5:
                return {"lat": round(lat, 5), "lng": round(lng, 5), "maps": f"https://www.google.com/maps?q={lat:.5f},{lng:.5f}"}
    m = re.search(r"https://(?:maps\.app\.goo\.gl|goo\.gl/maps)/[A-Za-z0-9_-]+", t)
    if m:
        return {"lat": None, "lng": None, "maps": m.group(0)}
    return None


def delay_of(eta: datetime | None, at: datetime, grace_h: float = 2.0) -> float:
    """Hours late beyond the grace (0 = not late)."""
    if not eta:
        return 0.0
    h = (at - eta).total_seconds() / 3600 - grace_h
    return round(h, 1) if h > 0 else 0.0


def first(name: str) -> str:
    n = str(name or "").strip().split()
    return n[0] if n else ""


def customer_text(kind: str, f: dict) -> str:
    """Hinglish drafts. Facts we don't have stay as [blanks]; nothing is guessed."""
    nm = first(f.get("name", "")) or "ji"
    biz = f.get("business") or "[aapki firm]"
    ref = f.get("ref") or ""
    goods = f.get("goods") or "aapka maal"
    veh = f.get("vehicle") or "[gaadi no.]"
    eta = f.get("eta") or "[pahunchne ka samay]"
    lr = f" (LR {f['lr']})" if f.get("lr") else ""
    ewb = f" E-way bill: {f['ewb']}." if f.get("ewb") else ""
    awb = f" Tracking: {f['courier']} {f['awb']}." if f.get("awb") else ""
    driver = f" Driver: {f['driver']}." if f.get("driver") else ""
    if kind == "dispatch":
        return (f"Namaste {nm}, {biz} se {goods} {ref} aaj nikal gaya hai{lr}. Gaadi: {veh}.{driver}{ewb}{awb} "
                f"Andaazan pahunchne ka samay: {eta}. Koi baat ho to isi number par bataiye.")
    if kind == "in_transit":
        where = f.get("where") or "[abhi kahan]"
        return f"Namaste {nm}, aapka maal {ref}{lr} raste mein hai, abhi {where} ke paas. Pahunchne ka andaaza: {eta}.{awb}"
    if kind == "delay":
        why = f.get("reason") or "[der ki wajah]"
        return (f"Namaste {nm}, maafi chahte hain: aapke maal {ref}{lr} mein der ho rahi hai ({why}). Naya andaaza: {eta}. "
                f"Hum lagatar nazar rakh rahe hain, aur update denge.")
    if kind == "out_for_delivery":
        return f"Namaste {nm}, aapka maal {ref}{lr} aaj delivery ke liye nikal gaya hai (gaadi {veh}). Kripya maal lene ke liye koi uplabdh rahe."
    if kind == "delivered":
        who = f" {f['receiver']} ji ne liya." if f.get("receiver") else ""
        return (f"Namaste {nm}, aapka maal {ref}{lr} deliver ho gaya hai.{who} Kripya packets gin kar dekh lijiye; koi kami / nuksaan ho "
                f"to aaj hi bataiye. Dhanyavaad, {biz}.")
    return f"Namaste {nm}, aapke maal {ref}{lr} ke baare mein: [baat]."
