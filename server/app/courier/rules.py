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
STATE_LABEL = {"draft": "Draft (not booked)", "waiting": "Waiting for your approval", "booked": "Booked (pickup pending)", "manual": "You book it",
               "picked": "Picked up by the courier", "in_transit": "In transit", "out_for_delivery": "Out for delivery today",
               "delivered": "Delivered", "rto": "Returning (RTO)", "exception": "Not delivered (NDR)",
               "cancelled": "Cancelled", "failed": "Booking failed"}
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
             "note": "Contract customers get DTDC's API from their DTDC account manager; until then enter the AWB."},
    "ekart": {"label": "Ekart", "api": [], "keys": (), "site": "https://ekartlogistics.com", "track": "https://ekartlogistics.com",
              "note": "Ekart's API is through Flipkart / a contract; for now enter the AWB or book through Shiprocket."},
    "xpressbees": {"label": "Xpressbees", "api": [], "keys": (), "site": "https://www.xpressbees.com", "track": "https://www.xpressbees.com",
                   "note": "Business API is by contract; for now enter the AWB or book through Shiprocket."},
    "indiapost": {"label": "India Post (Speed Post)", "api": [], "keys": (), "site": "https://www.indiapost.gov.in",
                  "track": "https://www.indiapost.gov.in",
                  "note": "India Post has no open tracking API for ordinary merchants; book at the counter / app and enter the article number."},
    "other": {"label": "Another courier", "api": [], "keys": (), "site": "", "track": "", "note": "Enter the AWB; tracking is on their page."},
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
                      "label": "Customer was not at home", "ask": "When will you be at home? Tell us a day / time."},
    "phone": {"words": ("phone", "not contactable", "unreachable", "switched off", "no response", "not responding", "call not"),
              "label": "Customer's phone was not reachable", "ask": "Tell us a working phone number the delivery person can call."},
    "address": {"words": ("address", "incomplete", "wrong", "incorrect", "landmark", "out of delivery area", "oda", "not found"),
                "label": "Address incomplete / wrong", "ask": "Send the full address, landmark and PIN code."},
    "refused": {"words": ("refused", "rejected", "denied", "not accepted", "cancelled by customer", "did not order", "not interested"),
                "label": "Customer refused to accept", "ask": "Do you want to receive the order? If yes, tell us the day."},
    "cod": {"words": ("cod", "cash not ready", "amount not ready", "payment not ready"),
            "label": "COD money was not ready", "ask": "When will the money be ready? We will send it again that day."},
    "future": {"words": ("future delivery", "reschedule", "later date", "asked for delivery on", "requested delivery"),
               "label": "Customer asked for a later date", "ask": "Which day do you want the delivery?"},
}
MAX_ATTEMPTS_NOTE = "Couriers usually send a parcel back (RTO) after 3 attempts; respond quickly."


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
        notes.append("Enter the actual weight (kg): without it the rate is not final.")
    if not vol:
        notes.append("Enter the box size (L x B x H cm): the courier also charges by volumetric weight.")
    elif vol > dead * 1.5 and dead:
        notes.append(f"The box is big: volumetric {vol} kg vs actual {dead} kg. A smaller box = lower cost.")
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
    "flammable items": ("petrol", "diesel", "kerosene", "lpg", "cylinder", "fireworks", "patakhe", "patake", "gunpowder", "flammable",
                               "thinner", "matchbox", "lighter fluid"),
    "weapons": ("gun", "pistol", "ammunition", "cartridge", "explosive"),
    "narcotics / drugs": ("ganja", "narcotic", "charas", "drugs"),
}
RESTRICTED = {
    "loose lithium battery / power bank": ("power bank", "lithium battery", "li-ion battery", "loose battery"),
    "liquid / aerosol / perfume": ("perfume", "aerosol", "spray", "deo"),
    "medicine": ("medicine", "tablet", "syrup", "dawai", "injection"),
    "gold / silver / jewellery": ("gold", "silver", "jewellery", "jewelry", "sona", "chandi"),
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
        got.append("Fastest courier first")
    elif any(w in t for w in ("sabse sasta", "cheapest", "kam rate", "sasta")):
        r["prefer"] = "cheapest"
        got.append("Cheapest courier first")
    for sent in re.split(r"[.;\n]| aur ", t):
        names = [k for w, k in _NAMES.items() if w in sent]
        if not names:
            continue
        if any(w in sent for w in ("mat ", "nahi lena", "mat lena", "avoid", "never", "kabhi nahi", "band karo")):
            r["avoid"] = sorted(set(r["avoid"]) | set(names))
            got.append("Never: " + ", ".join(names))
        elif "cod" in sent:
            r["cod_carrier"] = names[0]
            got.append(f"COD parcel: {names[0]}")
        else:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilo)", sent)
            if m and any(w in sent for w in ("upar", "se zyada", "above", "over", "bhari", "heavy")):
                r["heavy_kg"], r["heavy_carrier"] = float(m.group(1)), names[0]
                got.append(f"{m.group(1)} kg and heavier: {names[0]}")
    m = re.search(r"(?:rate|kharcha)[^0-9]{0,20}(\d{2,5})\s*(?:se zyada nahi|max|tak|se upar nahi)", t) or \
        re.search(r"(?:max|zyada se zyada)\s*₹?\s*(\d{2,5})", t)
    if m:
        r["max_rate"] = float(m.group(1))
        got.append(f"Rate above ₹{m.group(1)}: ask first")
    m = re.search(r"(\d)\s*din\s*(?:se zyada nahi|ke andar|tak)", t)
    if m:
        r["max_days"] = int(m.group(1))
        got.append(f"Delivers within {m.group(1)} days")
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
    out = ["First: " + ("fastest" if r["prefer"] == "fastest" else "cheapest")]
    if r["cod_carrier"]:
        out.append(f"COD parcel: {r['cod_carrier']}")
    if r["heavy_kg"] and r["heavy_carrier"]:
        out.append(f"{r['heavy_kg']:g} kg and heavier: {r['heavy_carrier']}")
    if r["avoid"]:
        out.append("Never: " + ", ".join(r["avoid"]))
    if r["max_rate"]:
        out.append(f"₹{r['max_rate']:g}: a warning on the card when the rate is higher")
    if r["max_days"]:
        out.append(f"Those taking more than {r['max_days']} days go to the bottom")
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
        return {"best": None, "ranked": [], "why": "No courier is left under your rules (or no rate came)."}
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
        why.append("your rule: " + ("COD" if cod and r["cod_carrier"] == want else "heavy parcel") + f" = {want}")
    else:
        why.append("fastest" if r["prefer"] == "fastest" else "cheapest")
    if r["max_rate"] and isinstance(best.get("rate"), (int, float)) and best["rate"] > r["max_rate"]:
        why.append(f"note: rate ₹{best['rate']:g} is above your limit ₹{r['max_rate']:g}")
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
    {"what": "E-way bill (CGST Rule 138)", "text": "When the goods are worth more than ₹50,000 (to another state; within the state ₹1 lakh in some states), "
     "an e-way bill is needed before sending. The courier needs its number. Hoola does not make the e-way bill.",
     "source": "CGST Rules 2017, Rule 138 (thok.rules limits)"},
    {"what": "Customer data (DPDP Act 2023)", "text": "Address / phone are only for sending the parcel; delete them when the customer asks (`forget`). One customer "
     "never sees another customer's parcel.", "source": "DPDP Act 2023 + Rules 2025 (notified 13-14 Nov 2025; phased to May 2027)"},
    {"what": "Prohibited goods", "text": "Cash, fireworks / petrol / gas, weapons and narcotics cannot go by courier; for battery / perfume / medicine check the courier's "
     "rules.", "source": "Courier terms (Shiprocket / Delhivery prohibited lists)"},
    {"what": "NDR", "text": MAX_ATTEMPTS_NOTE, "source": "support.shiprocket.in 'How to process an NDR' (checked 23 Oct 2026)"},
]
NEVER = ("Booking / wallet charge without your tap", "Asking the customer for an OTP / PIN", "Making up a courier status",
         "Showing one customer another customer's parcel", "Taking / sending COD money itself", "Making the e-way bill itself")
