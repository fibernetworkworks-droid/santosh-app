"""Courier Sahayak rules: pure functions (no DB, no network).

- weights: volumetric = L x B x H (cm) / 5000 (the divisor Indian courier aggregators use for surface / air express parcels;
  her carrier may use another, so the divisor is her setting), chargeable = the higher of dead and volumetric, rounded up to
  the next 0.5 kg slab (what the card shows; the carrier's own applied weight wins when it reports one).
- tracking: the carrier's own words are kept exactly (`raw`); `state_of` only maps them to our 8 states (booked, picked,
  in_transit, out_for_delivery, delivered, rto, exception, cancelled). Words we don't recognise map to None = keep the old
  state and show her the carrier's words (never a guess).
- NDR (failed delivery): reason from the carrier's words -> what to ask the customer + the draft message.
- her courier rules from her words ("sabse sasta", "COD par Delhivery", "5 kg se upar Xpressbees", "Ekart mat lena").
- e-way bill: value above the Rule 138 limit (thok.rules.eway_needed: Rs 50,000 inter-state; some states 1 lakh inside the
  state) needs an e-way bill number before booking; Hoola never generates it (she / her GSP does, Part A by the consignor).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

STATES = ("booked", "picked", "in_transit", "out_for_delivery", "delivered", "rto", "exception", "cancelled")
STATE_LABEL = {"draft": "Kaccha (book nahi)", "waiting": "Aapki haan baaki", "booked": "Book (pickup baaki)", "manual": "Aap book karein",
               "picked": "Courier ne utha liya", "in_transit": "Raste mein", "out_for_delivery": "Aaj delivery ke liye nikla",
               "delivered": "Pahunch gaya", "rto": "Wapas aa raha (RTO)", "exception": "Delivery nahi hui (NDR)",
               "cancelled": "Cancel", "failed": "Booking nahi hui"}
ACTIVE = ("booked", "manual", "picked", "in_transit", "out_for_delivery", "exception", "rto")

# Carriers. `api` = what Hoola can do with HER keys through the carrier's own documented API; everything else = manual
# (she books in the carrier's app / portal, types the AWB, opens the carrier's own tracking page).
CARRIERS: dict[str, dict[str, Any]] = {
    "shiprocket": {"label": "Shiprocket (aggregator)", "api": ["rates", "book", "label", "pickup", "track", "ndr", "cancel", "reverse"],
                   "keys": ("email", "password", "pickup_location"), "site": "https://www.shiprocket.in",
                   "track": "https://shiprocket.co/tracking/{awb}",
                   "note": "Shiprocket API user (Settings > API) + pickup location nickname. Rates of Delhivery / Xpressbees / Ekart / "
                           "DTDC / Blue Dart etc. come through her Shiprocket account."},
    "delhivery": {"label": "Delhivery", "api": ["rates", "book", "label", "pickup", "track", "ndr", "cancel", "reverse"],
                  "keys": ("token", "pickup_location"), "site": "https://www.delhivery.com", "track": "https://www.delhivery.com",
                  "note": "Delhivery One API token + registered warehouse name."},
    "bluedart": {"label": "Blue Dart", "api": ["track"], "keys": ("client_id", "client_secret", "login_id", "license_key"),
                 "site": "https://www.bluedart.com", "track": "https://www.bluedart.com",
                 "note": "Blue Dart APIs (DHL developer portal) are for contract customers: tracking with her keys; booking in her "
                         "Blue Dart account."},
    "dtdc": {"label": "DTDC", "api": [], "keys": (), "site": "https://www.dtdc.com", "track": "https://www.dtdc.com",
             "note": "Contract customers get DTDC's API from their DTDC account manager; until then AWB likhiye."},
    "ekart": {"label": "Ekart", "api": [], "keys": (), "site": "https://ekartlogistics.com", "track": "https://ekartlogistics.com",
              "note": "Ekart ka API Flipkart / contract ke through; abhi AWB likhiye ya Shiprocket se book kijiye."},
    "xpressbees": {"label": "Xpressbees", "api": [], "keys": (), "site": "https://www.xpressbees.com", "track": "https://www.xpressbees.com",
                   "note": "Business API contract par; abhi AWB likhiye ya Shiprocket se book kijiye."},
    "indiapost": {"label": "India Post (Speed Post)", "api": [], "keys": (), "site": "https://www.indiapost.gov.in",
                  "track": "https://www.indiapost.gov.in",
                  "note": "Aam vyapari ke liye India Post ka khula tracking API nahi; counter / app se book kijiye, article number likhiye."},
    "other": {"label": "Doosra courier", "api": [], "keys": (), "site": "", "track": "", "note": "AWB likhiye; tracking unke page par."},
}

# Carrier words -> our states. Order matters (first match wins); "undelivered" must not read as "delivered".
_STATE_WORDS: list[tuple[str, tuple[str, ...]]] = [
    ("cancelled", ("cancel",)),
    ("rto", ("rto", "return to origin", "returned to origin", "return to shipper", "returned to shipper", "returning to origin")),
    ("exception", ("undelivered", "not delivered", "delivery attempt", "attempt failed", "failed attempt", "ndr", "consignee not",
                   "customer not available", "not available", "refused", "rejected by", "address incomplete", "incorrect address",
                   "wrong address", "door locked", "premises closed", "cod not ready", "lost", "damaged", "misrouted", "held at",
                   "on hold", "exception", "shipment held", "undeliverable")),
    ("out_for_delivery", ("out for delivery", "out-for-delivery", "ofd", "dispatched for delivery")),
    ("delivered", ("delivered",)),
    ("picked", ("picked up", "pickup done", "pickup completed", "shipment picked", "picked")),
    ("in_transit", ("in transit", "in-transit", "intransit", "reached", "arrived", "departed", "dispatched", "connected", "bagged",
                    "received at", "shipped", "forwarded")),
    ("booked", ("pickup scheduled", "pickup generated", "pickup queued", "manifest", "awb assigned", "label generated",
                "out for pickup", "pickup pending", "order placed", "new", "pending", "not picked", "booked", "ready to ship")),
]


def state_of(raw: str) -> str | None:
    t = " " + re.sub(r"\s+", " ", (raw or "").lower()) + " "
    if not t.strip():
        return None
    for st, words in _STATE_WORDS:
        for w in words:
            if w == "ndr" or w == "ofd" or w == "new" or w == "rto":
                if re.search(rf"\b{w}\b", t):
                    return st
            elif w in t:
                return st
    return None


NDR_REASONS: dict[str, dict[str, Any]] = {
    "not_available": {"words": ("not available", "not reachable", "door locked", "premises closed", "no one", "nobody", "consignee unavailable"),
                      "label": "Graahak ghar par nahi tha", "ask": "Kab ghar par rahenge? Ek din / samay bataiye."},
    "phone": {"words": ("phone", "not contactable", "unreachable", "switched off", "no response", "not responding", "call not"),
              "label": "Graahak ka phone nahi laga", "ask": "Chaalu phone number bataiye jis par delivery boy call kare."},
    "address": {"words": ("address", "incomplete", "wrong", "incorrect", "landmark", "out of delivery area", "oda", "not found"),
                "label": "Pata adhoora / galat", "ask": "Poora pata, landmark aur PIN code bhejiye."},
    "refused": {"words": ("refused", "rejected", "denied", "not accepted", "cancelled by customer", "did not order", "not interested"),
                "label": "Graahak ne lene se mana kiya", "ask": "Kya aap order lena chahte hain? Haan ho to din bataiye."},
    "cod": {"words": ("cod", "cash not ready", "amount not ready", "payment not ready"),
            "label": "COD ka paisa tayyar nahi tha", "ask": "Kab paisa tayyar hoga? Us din dobara bhejte hain."},
    "future": {"words": ("future delivery", "reschedule", "later date", "asked for delivery on", "requested delivery"),
               "label": "Graahak ne baad mein maanga", "ask": "Kis din delivery chahiye?"},
}
MAX_ATTEMPTS_NOTE = "Courier aam taur par 3 koshish ke baad parcel RTO (wapas) kar dete hain; jaldi jawab dein."


def ndr_reason(raw: str) -> str:
    t = (raw or "").lower()
    for k in ("refused", "cod", "future", "phone", "address", "not_available"):
        if any(w in t for w in NDR_REASONS[k]["words"]):
            return k
    return "other"


# ---------------------------------------------------------------- numbers
def num(v) -> float:
    if v in (None, ""):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(\.\d+)?", str(v).replace(",", "").replace("₹", ""))
    return float(m.group(0)) if m else 0.0


def volumetric(length: float, breadth: float, height: float, divisor: float = 5000.0) -> float:
    if min(length, breadth, height) <= 0 or divisor <= 0:
        return 0.0
    return round(length * breadth * height / divisor, 3)


def slab(kg: float, step: float = 0.5) -> float:
    if kg <= 0:
        return 0.0
    return round(math.ceil(round(kg / step, 6)) * step, 2)


def weights(dead_kg: float, dims: dict | None, divisor: float = 5000.0) -> dict[str, Any]:
    d = dims or {}
    vol = volumetric(num(d.get("l") or d.get("length")), num(d.get("b") or d.get("breadth")), num(d.get("h") or d.get("height")), divisor)
    dead = round(max(num(dead_kg), 0.0), 3)
    high = max(dead, vol)
    out = {"dead_kg": dead, "volumetric_kg": vol, "chargeable_kg": slab(high), "divisor": divisor, "by": "volumetric" if vol > dead else "dead"}
    notes = []
    if not dead:
        notes.append("Asli wazan (kg) likhiye: bina wazan ke rate pakka nahi.")
    if not vol:
        notes.append("Dabbe ka naap (L x B x H cm) likhiye: courier volumetric wazan se bhi charge karta hai.")
    elif vol > dead * 1.5 and dead:
        notes.append(f"Dabba bada hai: volumetric {vol} kg vs asli {dead} kg. Chhota dabba = kam kharcha.")
    out["notes"] = notes
    return out


def pincode_ok(pin: str) -> bool:
    return bool(re.fullmatch(r"[1-9]\d{5}", str(pin or "").strip()))


def phone10(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    return d[-10:] if len(d) >= 10 else ""


def mask_phone(p: str) -> str:
    d = phone10(p)
    return f"{d[:2]}XXXXXX{d[-2:]}" if d else ""


def mask_address(a: str) -> str:
    """Only the last part (area / city) of an address is shown in summaries; the full address stays in her parcel page."""
    parts = [x.strip() for x in re.split(r"[,\n]+", str(a or "")) if x.strip()]
    return parts[-1][:40] if parts else ""


def awb_ok(awb: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9-]{6,30}", str(awb or "").strip()))


# ---------------------------------------------------------------- prohibited / restricted goods (never booked by Hoola)
PROHIBITED = {
    "cash / currency": ("cash", "currency", "notes bundle", "nakad"),
    "aag pakadne wali cheez": ("petrol", "diesel", "kerosene", "lpg", "cylinder", "fireworks", "patakhe", "patake", "gunpowder", "flammable",
                               "thinner", "matchbox", "lighter fluid"),
    "hathiyaar": ("gun", "pistol", "ammunition", "cartridge", "explosive"),
    "nasha / drugs": ("ganja", "narcotic", "charas", "drugs"),
}
RESTRICTED = {
    "loose lithium battery / power bank": ("power bank", "lithium battery", "li-ion battery", "loose battery"),
    "liquid / aerosol / perfume": ("perfume", "aerosol", "spray", "deo"),
    "dawai (medicine)": ("medicine", "tablet", "syrup", "dawai", "injection"),
    "sona-chandi / jewellery": ("gold", "silver", "jewellery", "jewelry", "sona", "chandi"),
}


def goods_check(text: str) -> dict[str, list[str]]:
    t = " " + (text or "").lower() + " "
    bad = [k for k, ws in PROHIBITED.items() if any(re.search(rf"\b{re.escape(w)}\b", t) for w in ws)]
    warn = [k for k, ws in RESTRICTED.items() if any(re.search(rf"\b{re.escape(w)}\b", t) for w in ws)]
    return {"prohibited": bad, "restricted": warn}


# ---------------------------------------------------------------- her courier rules
DEFAULT_RULES: dict[str, Any] = {"prefer": "cheapest", "cod_carrier": "", "heavy_kg": 0.0, "heavy_carrier": "", "avoid": [], "max_rate": 0.0,
                                 "max_days": 0}

_NAMES = {"delhivery": "delhivery", "dilivery": "delhivery", "xpressbees": "xpressbees", "xpress bees": "xpressbees", "ekart": "ekart",
          "dtdc": "dtdc", "blue dart": "bluedart", "bluedart": "bluedart", "india post": "indiapost", "speed post": "indiapost",
          "shadowfax": "shadowfax", "ecom express": "ecom", "amazon shipping": "amazon", "shiprocket": "shiprocket"}


def carrier_key(name: str) -> str:
    t = (name or "").lower()
    for w, k in _NAMES.items():
        if w in t:
            return k
    return re.sub(r"[^a-z0-9]", "", t)[:20]


def parse_rules(text: str) -> tuple[dict[str, Any], list[str]]:
    t = (text or "").lower()
    r = json.loads(json.dumps(DEFAULT_RULES))
    got = []
    if any(w in t for w in ("sabse tez", "fastest", "jaldi wala", "jaldi pahunche")):
        r["prefer"] = "fastest"
        got.append("Sabse jaldi pahunchane wala courier pehle")
    elif any(w in t for w in ("sabse sasta", "cheapest", "kam rate", "sasta")):
        r["prefer"] = "cheapest"
        got.append("Sabse sasta courier pehle")
    for sent in re.split(r"[.;\n]| aur ", t):
        names = [k for w, k in _NAMES.items() if w in sent]
        if not names:
            continue
        if any(w in sent for w in ("mat ", "nahi lena", "mat lena", "avoid", "never", "kabhi nahi", "band karo")):
            r["avoid"] = sorted(set(r["avoid"]) | set(names))
            got.append("Kabhi nahi: " + ", ".join(names))
        elif "cod" in sent:
            r["cod_carrier"] = names[0]
            got.append(f"COD parcel: {names[0]}")
        else:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilo)", sent)
            if m and any(w in sent for w in ("upar", "se zyada", "above", "over", "bhari", "heavy")):
                r["heavy_kg"], r["heavy_carrier"] = float(m.group(1)), names[0]
                got.append(f"{m.group(1)} kg se bhari: {names[0]}")
    m = re.search(r"(?:rate|kharcha)[^0-9]{0,20}(\d{2,5})\s*(?:se zyada nahi|max|tak|se upar nahi)", t) or \
        re.search(r"(?:max|zyada se zyada)\s*₹?\s*(\d{2,5})", t)
    if m:
        r["max_rate"] = float(m.group(1))
        got.append(f"Rate ₹{m.group(1)} se zyada ho to poochho")
    m = re.search(r"(\d)\s*din\s*(?:se zyada nahi|ke andar|tak)", t)
    if m:
        r["max_days"] = int(m.group(1))
        got.append(f"{m.group(1)} din ke andar pahunchne wala")
    return r, got


def clean_rules(r: dict | None) -> dict[str, Any]:
    out = json.loads(json.dumps(DEFAULT_RULES))
    r = r or {}
    if r.get("prefer") in ("cheapest", "fastest"):
        out["prefer"] = r["prefer"]
    for k in ("cod_carrier", "heavy_carrier"):
        out[k] = carrier_key(str(r.get(k) or "")) if r.get(k) else ""
    out["heavy_kg"] = max(0.0, min(num(r.get("heavy_kg")), 500.0))
    out["max_rate"] = max(0.0, min(num(r.get("max_rate")), 100000.0))
    out["max_days"] = int(max(0, min(num(r.get("max_days")), 30)))
    out["avoid"] = sorted({carrier_key(str(x)) for x in (r.get("avoid") or []) if str(x).strip()})[:20]
    return out


def rule_lines(r: dict) -> list[str]:
    r = clean_rules(r)
    out = ["Pehle: " + ("sabse jaldi" if r["prefer"] == "fastest" else "sabse sasta")]
    if r["cod_carrier"]:
        out.append(f"COD parcel: {r['cod_carrier']}")
    if r["heavy_kg"] and r["heavy_carrier"]:
        out.append(f"{r['heavy_kg']:g} kg se bhari: {r['heavy_carrier']}")
    if r["avoid"]:
        out.append("Kabhi nahi: " + ", ".join(r["avoid"]))
    if r["max_rate"]:
        out.append(f"₹{r['max_rate']:g} se mehenga ho to card par chetavni")
    if r["max_days"]:
        out.append(f"{r['max_days']} din se zyada lagne wale neeche")
    return out


def choose(options: list[dict], rules: dict, cod: bool, kg: float) -> dict[str, Any]:
    """Rank the carrier's own quotes by her rules. Never invents a rate: options without a rate go last, flagged."""
    r = clean_rules(rules)
    opts = []
    for o in options or []:
        k = carrier_key(str(o.get("courier") or ""))
        if k in r["avoid"]:
            continue
        if cod and o.get("cod") is False:
            continue
        opts.append({**o, "key": k})
    if not opts:
        return {"best": None, "ranked": [], "why": "Aapke niyam ke hisaab se koi courier nahi bacha (ya koi rate nahi aaya)."}
    want = ""
    if cod and r["cod_carrier"]:
        want = r["cod_carrier"]
    if r["heavy_kg"] and kg > r["heavy_kg"] and r["heavy_carrier"]:
        want = r["heavy_carrier"]

    def score(o):
        rate = o.get("rate")
        days = o.get("days")
        late = 1 if (r["max_days"] and days and days > r["max_days"]) else 0
        has_rate = 0 if isinstance(rate, (int, float)) and rate > 0 else 1
        pick = 0 if (want and o["key"] == want) else 1
        if r["prefer"] == "fastest":
            return (pick, late, has_rate, days or 99, rate or 1e9)
        return (pick, late, has_rate, rate or 1e9, days or 99)

    ranked = sorted(opts, key=score)
    best = ranked[0]
    why = []
    if want and best["key"] == want:
        why.append("aapka niyam: " + ("COD" if cod and r["cod_carrier"] == want else "bhari parcel") + f" = {want}")
    else:
        why.append("sabse jaldi" if r["prefer"] == "fastest" else "sabse sasta")
    if r["max_rate"] and isinstance(best.get("rate"), (int, float)) and best["rate"] > r["max_rate"]:
        why.append(f"dhyaan: rate ₹{best['rate']:g} aapki seema ₹{r['max_rate']:g} se zyada")
    return {"best": best, "ranked": ranked[:6], "why": "; ".join(why)}


# ---------------------------------------------------------------- remittance CSV columns
REMIT_COLS = {
    "awb": ("awb", "awb no", "awb number", "waybill", "tracking", "airway bill", "awb code"),
    "amount": ("cod amount", "remitted amount", "amount remitted", "remittance amount", "cod value", "collected amount", "amount", "net amount"),
    "utr": ("utr", "utr no", "crf id", "remittance id", "transaction id", "bank ref", "reference"),
    "date": ("remittance date", "remitted on", "date", "payment date", "credited on"),
    "order": ("order id", "order no", "order number", "channel order id", "reference no"),
}


def remit_header(cells: list[str]) -> dict[str, int]:
    low = [re.sub(r"\s+", " ", str(c or "").strip().lower().replace("_", " ")) for c in cells]
    out: dict[str, int] = {}
    for key, names in REMIT_COLS.items():
        for n in names:                      # longer / more specific names first in each tuple
            for i, c in enumerate(low):
                if i in out.values():
                    continue
                if c == n or (len(n) > 4 and n in c):
                    out[key] = i
                    break
            if key in out:
                break
    return out


# ---------------------------------------------------------------- hashes + texts
def card_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


LAW = [
    {"what": "E-way bill (CGST Rule 138)", "text": "Saamaan ki keemat ₹50,000 se zyada (doosre rajya ko; kuch rajyon mein rajya ke andar ₹1 lakh) "
     "ho to bhejne se pehle e-way bill. Courier ko number dena hota hai. Hoola e-way bill nahi banata.",
     "source": "CGST Rules 2017, Rule 138 (thok.rules limits)"},
    {"what": "Graahak ka data (DPDP Act 2023)", "text": "Pata / phone sirf parcel bhejne ke liye; graahak maange to mitao (`forget`). Dusre graahak ko "
     "kabhi kisi aur ka parcel nahi dikhta.", "source": "DPDP Act 2023 + Rules 2025 (notified 13-14 Nov 2025; phased to May 2027)"},
    {"what": "Mana saamaan", "text": "Nakad, patakhe / petrol / gas, hathiyaar, nasha courier se nahi jaata; battery / perfume / dawai par courier ke "
     "niyam dekhiye.", "source": "Courier terms (Shiprocket / Delhivery prohibited lists)"},
    {"what": "NDR", "text": MAX_ATTEMPTS_NOTE, "source": "support.shiprocket.in 'How to process an NDR' (checked 23 Oct 2026)"},
]
NEVER = ("Booking / wallet charge bina aapki tap ke", "Graahak ka OTP / PIN maangna", "Courier ka status khud se banana",
         "Ek graahak ko doosre ka parcel dikhana", "COD ka paisa khud lena / bhejna", "E-way bill khud banana")
