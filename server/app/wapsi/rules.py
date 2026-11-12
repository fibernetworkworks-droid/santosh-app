"""Wapsi Sahayak rules: reason codes, categories, her policy from her own words, the policy check, the refund sum,
fraud signals and the legal notes. Pure functions (no database), so every number here is tested on its own.

Research (23 Oct 2026):
- Consumer Protection (E-Commerce) Rules 2020: a seller may not refuse to take back goods or refuse a refund when they
  are defective, deficient, spurious, not as described / agreed, or delivered late (Rule 6(3), inventory model Rule
  7(4); force majeure excepted for late delivery). Return / refund / exchange terms and return-shipping cost must be
  shown to the buyer (Rule 6(5)(g), 7(1)(a)). Accepted refunds must be paid "within a reasonable period of time, or as
  prescribed under applicable laws" (Rule 4(10)); complaints acknowledged in 48 hours and redressed within one month
  (Rule 4(5)). https://www.legitquest.com/act/consumer-protection-e-commerce-rules-2020/91C8
- RBI TAT circular DPSS.CO.PD No.629/02.01.014/2019-20 (20 Sep 2019): failed UPI payment to a merchant auto-reversed by
  T+5, Rs 100 / day after; failed P2P / IMPS by T+1. These are bank-side failed transactions, not merchant refunds.
  https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=11693
- CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023 (notified 30 Nov 2023; self-audit advisory June
  2025): forced action, interface interference, trick question, confirm shaming... -> store credit is offered as a
  choice, never forced; "refund" and "store credit" buttons look the same.
  https://www.jsalaw.com/newsletters-and-updates/ccpa-issues-guidelines-for-prevention-and-regulation-of-dark-patterns-2023/
- GST: a sales return = a credit note (Sec 34; Rule 53 contents), declared by 30 November after the FY ends or the
  annual return, whichever is earlier. https://busy.in/gst/guide-to-a-credit-note-under-gst/
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

# ---------------------------------------------------------------- reasons
REASONS: dict[str, dict[str, Any]] = {
    "damaged": {"label": "Arrived broken / damaged", "fault": True, "proof": True,
                "words": ("damage", "toota", "tuta", "tut gaya", "phata", "phati", "fata", "fati", "phat ", "crack", "broken", "dent", "leak", "kharab aaya", "tooti")},
    "defective": {"label": "Not working / faulty", "fault": True, "proof": True,
                  "words": ("defect", "kaam nahi", "chal nahi", "not working", "band ho", "on nahi", "kharab", "faulty", "dead", "awaaz nahi", "aawaz nahi", "sound nahi", "charge nahi", "nahi chalta", "nahi chalti", "hang ho")},
    "wrong_item": {"label": "Wrong item arrived", "fault": True, "proof": True,
                   "words": ("galat", "wrong", "dusra", "doosra", "alag item", "different item", "wrong colour", "wrong color", "wrong size bheja")},
    "missing_item": {"label": "Something missing", "fault": True, "proof": True,
                     "words": ("missing", "gayab", "kam aaya", "nahi aaya", "khaali", "empty", "part nahi", "adhoora")},
    "not_as_described": {"label": "Not as shown", "fault": True, "proof": True,
                         "words": ("not as described", "photo jaisa nahi", "jaisa dikhaya", "fake", "duplicate", "nakli", "original nahi", "different from")},
    "expired": {"label": "Expired / old stock", "fault": True, "proof": True,
                "words": ("expire", "expiry", "purana", "date nikal", "kharab ho gaya khana", "sada", "fungus")},
    "late_delivery": {"label": "Arrived late", "fault": True, "proof": False, "words": ("late", "der se", "der ho", "delay")},
    "size_fit": {"label": "Size / fit is wrong", "fault": False, "proof": False,
                 "words": ("size", "fit", "chhota", "bada", "tight", "loose", "dheela")},
    "quality": {"label": "Did not like the quality", "fault": False, "proof": False, "words": ("quality", "kapda patla", "cheap lag", "pasand nahi aaya quality")},
    "changed_mind": {"label": "Changed mind / no longer needed", "fault": False, "proof": False,
                     "words": ("man badal", "nahi chahiye", "zaroorat nahi", "changed my mind", "pasand nahi", "dont want", "don't want", "mood")},
    "ordered_by_mistake": {"label": "Ordered by mistake", "fault": False, "proof": False, "words": ("galti se", "by mistake", "do baar", "twice", "duplicate order")},
    "other": {"label": "Something else", "fault": False, "proof": False, "words": ()},
}
SELLER_FAULT = {k for k, v in REASONS.items() if v["fault"]}


def reason_of(text: str) -> str:
    t = (text or "").lower().strip()
    if t in REASONS:
        return t
    for k, v in REASONS.items():                       # order matters: damage / defect / wrong before "pasand nahi"
        if any(w in t for w in v["words"]):
            return k
    return "other"


# ---------------------------------------------------------------- categories
CATEGORIES: dict[str, tuple[str, ...]] = {
    "innerwear": ("innerwear", "undergarment", "lingerie", "bra", "panty", "brief", "boxer", "baniyan", "vest"),
    "clothes": ("kapde", "kapda", "kurti", "kurta", "saree", "sari", "shirt", "tshirt", "t-shirt", "dress", "top", "jeans", "pant",
                "lehenga", "dupatta", "apparel", "fashion", "clothes", "clothing", "suit", "jacket", "frock", "blouse"),
    "footwear": ("chappal", "joota", "juta", "shoe", "shoes", "sandal", "slipper", "footwear", "sneaker", "heels"),
    "electronics": ("mobile", "phone", "earphone", "earbuds", "headphone", "charger", "cable", "electronics", "laptop", "speaker",
                    "watch", "smartwatch", "power bank", "powerbank", "tv", "mixer", "gadget", "trimmer", "appliance"),
    "cosmetics": ("cosmetic", "makeup", "make-up", "beauty", "cream", "lipstick", "perfume", "shampoo", "skincare", "serum", "kajal", "nail"),
    "food": ("khana", "food", "grocery", "kirana", "mithai", "sweets", "snack", "namkeen", "masala", "achaar", "pickle", "cake", "dry fruit"),
    "medicine": ("medicine", "dawai", "dawa", "tablet", "syrup", "pharma", "capsule"),
    "jewellery": ("jewellery", "jewelry", "gehna", "earring", "jhumka", "necklace", "ring", "bangle", "chudi", "payal", "gold", "silver"),
    "custom": ("custom", "customised", "customized", "personalised", "personalized", "naam likha", "made to order", "stitched", "silai"),
    "home": ("bartan", "utensil", "home decor", "decor", "bedsheet", "curtain", "furniture", "kitchen", "lamp"),
    "books": ("book", "kitaab", "kitab", "novel", "notebook"),
    "toys": ("toy", "khilona", "game", "puzzle"),
}
CAT_LABEL = {"innerwear": "innerwear", "clothes": "clothes", "footwear": "footwear", "electronics": "electronics",
             "cosmetics": "cosmetics", "food": "food / grocery", "medicine": "medicine", "jewellery": "jewellery", "custom": "custom / personalised",
             "home": "home goods", "books": "books", "toys": "toys", "other": "other goods"}


def category_of(text: str) -> str:
    t = f" {(text or '').lower()} "
    if t.strip() in CATEGORIES or t.strip() == "other":
        return t.strip()
    for cat, words in CATEGORIES.items():
        for w in words:
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?:s|es)?(?![a-z])", t):
                return cat
    return "other"


def cats_in(text: str) -> list[str]:
    t = f" {(text or '').lower()} "
    out = []
    for cat, words in CATEGORIES.items():
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?:s|es)?(?![a-z])", t) for w in words):
            out.append(cat)
    return out


# ---------------------------------------------------------------- her policy, in her words -> structured
DEFAULT_POLICY: dict[str, Any] = {
    "window_days": {"default": 7},          # days from delivery
    "non_returnable": [],                   # categories
    "need_tags": False, "need_packaging": False, "need_unused": False,
    "video_for": [],                        # categories that need an unboxing video for damage / missing claims (proof, never a refusal)
    "restocking_pct": 0.0,                  # only on change-of-mind returns
    "reverse_fee": 0.0,                     # her return-pickup charge on change-of-mind returns (rupees)
    "exchange": True, "refund": True,
    "refund_mode": "original",              # original | store_credit (offered as a CHOICE only)
    "refund_days": 7,                       # her promise: refund within N days of QC
    "no_pickup_below": 0.0,                 # below this item value: refund without taking it back ("rakh lijiye")
    "ship_back_on_full": False,             # change of mind + the whole order back -> delivery charge refunded too
    "notes": [],
}

_NO = r"(nahi|nahin|nhi|na |no |not|non[- ]?returnable|mat|nahi hoga|nahi milega|nahi hota)"


def parse_policy(text: str, base: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    """Her return policy in Hinglish / English -> the structure above. Returns (policy, what_was_understood lines).
    Anything not understood stays as it was (never guessed)."""
    pol = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v) for k, v in (base or DEFAULT_POLICY).items()}
    for k, v in DEFAULT_POLICY.items():
        pol.setdefault(k, v)
    got: list[str] = []
    for raw in re.split(r"[\n.;!|]+|,(?![^()]*\))", text or ""):
        c = raw.strip().lower()
        if not c:
            continue
        cats = cats_in(c)
        neg = re.search(_NO, c + " ")
        m_days = re.search(r"(\d{1,3})\s*(din|days?|dino|dinon)", c)
        if re.search(r"restock|kaat|katenge|deduct|cut", c) and re.search(r"(\d{1,2}(\.\d)?)\s*%", c):
            pol["restocking_pct"] = min(50.0, float(re.search(r"(\d{1,2}(\.\d)?)\s*%", c).group(1)))
            got.append(f"{pol['restocking_pct']:g}% restocking fee on change of mind")
            continue
        if re.search(r"(pickup|return shipping|wapsi ka kharcha|reverse|courier charge|shipping charge)", c) and re.search(r"(₹|rs\.?|rupay|rupee)\s*(\d+)|(\d+)\s*(₹|rs|rupay|rupee)", c):
            mm = re.search(r"(?:₹|rs\.?|rupay|rupee)\s*(\d+)|(\d+)\s*(?:₹|rs|rupay|rupee)", c)
            pol["reverse_fee"] = float(mm.group(1) or mm.group(2))
            got.append(f"Pickup charge ₹{pol['reverse_fee']:g} on change of mind")
            continue
        if "unboxing" in c or ("video" in c and ("khol" in c or "open" in c)):
            vc = cats or ["electronics"]
            pol["video_for"] = sorted(set(pol["video_for"]) | set(vc))
            got.append("Unboxing video needed (for damage / missing-item claims): " + ", ".join(CAT_LABEL.get(x, x) for x in vc))
            continue
        if re.search(r"(store credit|wallet|coupon|credit note|voucher)", c):
            if re.search(r"(sirf|only|hi milega|hi denge)", c) and not neg:
                pol["refund_mode"] = "store_credit"
                got.append("Refund: store credit (only if the customer chooses; if the fault is yours the money goes back - law)")
            else:
                got.append("Store credit if the customer wants it")
            continue
        if re.search(r"(original|same mode|jaise pay|usi mode|source|bank mein|account mein wapas)", c) and re.search(r"refund|paisa|paise", c):
            pol["refund_mode"] = "original"
            got.append("Refund: to the same method used to pay")
            continue
        if "exchange" in c or "badal" in c and "man badal" not in c:
            pol["exchange"] = not bool(neg)
            got.append("Exchange allowed" if pol["exchange"] else "No exchange")
            if not m_days:
                continue
        if re.search(r"(tag|label)", c) and not neg:
            pol["need_tags"] = True
            got.append("Tags must be attached")
        if re.search(r"(packing|packaging|dabba|box|original pack)", c) and not cats and not m_days:
            pol["need_packaging"] = True
            got.append("In original packing")
        if re.search(r"(unused|use na|bina use|istemal|istemaal|pehna na|pehne bina|not used|use nahi)", c) and not m_days:
            pol["need_unused"] = True
            got.append("Unused")
        if re.search(r"(rakh lo|rakh lijiye|wapas mat bhejo|pickup nahi)", c):
            mm = re.search(r"(\d+)", c)
            if mm:
                pol["no_pickup_below"] = float(mm.group(1))
                got.append(f"Below ₹{mm.group(1)}: do not collect the item, refund directly")
            continue
        if m_days and re.search(r"refund", c) and re.search(r"(andar|within|tak|mein)", c) and not re.search(r"return|wapas", c):
            pol["refund_days"] = int(m_days.group(1))
            got.append(f"Refund within {pol['refund_days']} days")
            continue
        if neg and cats and re.search(r"(return|wapas|wapsi|returnable)", c) and not m_days:
            pol["non_returnable"] = sorted(set(pol["non_returnable"]) | set(cats))
            got.append("Not returnable: " + ", ".join(CAT_LABEL.get(x, x) for x in cats))
            continue
        if re.search(r"(no return|return nahi|wapsi nahi|non[- ]?returnable)", c) and not cats and not m_days:
            pol["refund"] = False
            got.append("No return on change of mind (you must still take it back by law if the fault is yours)")
            continue
        if m_days and re.search(r"(return|wapas|wapsi|replace|refund)", c):
            n = int(m_days.group(1))
            for cat in (cats or ["default"]):
                pol["window_days"][cat] = n
            got.append(f"Return within {n} days" + (" (" + ", ".join(CAT_LABEL.get(x, x) for x in cats) + ")" if cats else ""))
            continue
        if raw.strip() and not any(raw.strip().lower() in g.lower() for g in got):
            pol["notes"] = (pol["notes"] + [raw.strip()[:200]])[-20:]
    return pol, got


def clean_policy(p: dict[str, Any]) -> dict[str, Any]:
    """A policy from the app / model, kept to known keys with sane limits."""
    out = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_POLICY.items()}
    if not isinstance(p, dict):
        return out
    wd = p.get("window_days")
    if isinstance(wd, dict):
        out["window_days"] = {str(k): max(0, min(365, int(float(v)))) for k, v in wd.items()
                              if (str(k) in CATEGORIES or str(k) in ("default", "other")) and str(v).replace(".", "", 1).isdigit()}
        out["window_days"].setdefault("default", 7)
    for k in ("non_returnable", "video_for"):
        if isinstance(p.get(k), list):
            out[k] = sorted({category_of(str(x)) for x in p[k]} - {"other"} | ({"other"} if "other" in p[k] else set()))
    for k in ("need_tags", "need_packaging", "need_unused", "exchange", "refund", "ship_back_on_full"):
        if k in p:
            out[k] = bool(p[k])
    for k, lo, hi in (("restocking_pct", 0, 50), ("reverse_fee", 0, 2000), ("no_pickup_below", 0, 100000), ("refund_days", 1, 30)):
        if p.get(k) not in (None, ""):
            try:
                out[k] = max(lo, min(hi, float(p[k])))
            except (TypeError, ValueError):
                pass
    out["refund_days"] = int(out["refund_days"])
    if p.get("refund_mode") in ("original", "store_credit"):
        out["refund_mode"] = p["refund_mode"]
    if isinstance(p.get("notes"), list):
        out["notes"] = [str(x)[:200] for x in p["notes"]][:20]
    return out


def policy_lines(p: dict[str, Any]) -> list[str]:
    """Her policy read back in plain words (the app and the model show the same thing)."""
    wd = p.get("window_days", {})
    out = [f"Return within {wd.get('default', 7)} days of delivery"]
    for k, v in wd.items():
        if k != "default":
            out.append(f"{CAT_LABEL.get(k, k)}: {v} days")
    if p.get("non_returnable"):
        out.append("Not returnable (change of mind): " + ", ".join(CAT_LABEL.get(x, x) for x in p["non_returnable"]))
    conds = [t for k, t in (("need_tags", "tags attached"), ("need_packaging", "original packing"), ("need_unused", "unused")) if p.get(k)]
    if conds:
        out.append("Conditions: " + ", ".join(conds))
    if p.get("video_for"):
        out.append("Ask for an unboxing video: " + ", ".join(CAT_LABEL.get(x, x) for x in p["video_for"]))
    if p.get("restocking_pct"):
        out.append(f"{p['restocking_pct']:g}% restocking fee on change of mind")
    if p.get("reverse_fee"):
        out.append(f"Pickup charge ₹{p['reverse_fee']:g} on change of mind")
    out.append("Exchange: yes" if p.get("exchange") else "Exchange: no")
    out.append("Refund: " + ("the mode used to pay" if p.get("refund_mode") == "original" else "store credit (at the customer's choice)"))
    out.append(f"Refund within {p.get('refund_days', 7)} days of QC")
    if p.get("no_pickup_below"):
        out.append(f"Below ₹{p['no_pickup_below']:g}: no item return, refund directly")
    out.append("If the fault is yours (broken / faulty / wrong / missing / not as shown / late) you cannot refuse a return or refund (E-Commerce Rules 2020)")
    return out


# ---------------------------------------------------------------- the policy check (by code)
def check(policy: dict[str, Any], reason: str, items: list[dict[str, Any]], delivered_on: date | None, on: date,
          proof: dict[str, Any], want: str = "refund") -> dict[str, Any]:
    """approve | ask_more | reject_suggest + the reasons, item by item. A seller-fault return is never 'reject'."""
    reason = reason if reason in REASONS else reason_of(reason)
    fault = reason in SELLER_FAULT
    rs: list[str] = []
    asks: list[str] = []
    blocks: list[str] = []
    per: list[dict[str, Any]] = []
    days = (on - delivered_on).days if delivered_on else None
    if delivered_on is None:
        asks.append("The delivery date is needed (to count the window).")
    elif days is not None and days < 0:
        asks.append("The delivery date is in the future; give the correct date.")
    for it in items:
        cat = it.get("category") or category_of(str(it.get("name", "")))
        win = int(policy.get("window_days", {}).get(cat, policy.get("window_days", {}).get("default", 7)))
        inwin = days is None or days <= win
        row = {"name": it.get("name", ""), "category": cat, "window": win, "in_window": inwin, "ok": True, "notes": []}
        if cat in policy.get("non_returnable", []):
            if fault:
                row["notes"].append(f"{CAT_LABEL.get(cat, cat)} is normally not returnable, but the fault is yours: you must take it back by law")
            else:
                row["ok"] = False
                row["notes"].append(f"{CAT_LABEL.get(cat, cat)} cannot be returned under your policy")
        if not inwin:
            if fault:
                row["notes"].append(f"The {win}-day window has passed ({days} days), but the complaint is about a fault: check the warranty / law, do not refuse outright")
                asks.append(f"{it.get('name', 'Item')}: fault complaint after the window - your decision")
            else:
                row["ok"] = False
                row["notes"].append(f"The {win}-day window has passed ({days} days)")
        per.append(row)
    if not fault and not policy.get("refund", True) and want == "refund":
        blocks.append("Your policy has no refund on change of mind (an exchange is possible)" if policy.get("exchange") else "Your policy has no return on change of mind")
    if want == "exchange" and not policy.get("exchange", True) and not fault:
        blocks.append("Your policy has no exchange")
    photos = int(proof.get("photos", 0))
    videos = int(proof.get("videos", 0))
    if REASONS[reason]["proof"] and photos == 0 and videos == 0:
        asks.append("Ask the customer for photos: the whole item, a close-up of the damage, and the parcel label")
    cats = {r["category"] for r in per}
    if reason in ("damaged", "missing_item", "wrong_item") and set(policy.get("video_for", [])) & cats and videos == 0:
        rs.append("Your policy asks for an unboxing video; if there is none, still decide from photos / QC (do not refuse just because there is no video)")
    look = proof.get("look") or {}
    if look.get("not_product"):
        asks.append("The item is not visible in the photo: ask for a clear photo")
    if reason == "damaged" and photos and look and look.get("damage_seen") is False:
        asks.append("The damage is not clear in the photo: ask for a close-up photo")
    if look.get("mismatch"):
        asks.append("The item in the photo looks different from the order: please check")
    if not fault:
        conds = [t for k, t in (("need_tags", "tags attached"), ("need_packaging", "original packing"), ("need_unused", "unused"))
                 if policy.get(k)]
        if conds:
            rs.append("Check at pickup / QC: " + ", ".join(conds))
    bad = [r for r in per if not r["ok"]]
    if blocks or (bad and len(bad) == len(per)):
        verdict = "reject_suggest" if not fault else "ask_more"
    elif asks:
        verdict = "ask_more"
    else:
        verdict = "approve"
    if fault and verdict == "reject_suggest":
        verdict = "ask_more"
    if bad and len(bad) < len(per):
        rs.append("Some items fall under the policy, some do not: " + ", ".join(r["name"] for r in bad) + " cannot be returned")
    for r in per:
        rs.extend(f"{r['name']}: {n}" for n in r["notes"])
    rs.extend(blocks)
    return {"verdict": verdict, "fault": fault, "reason": reason, "reason_label": REASONS[reason]["label"], "days_since_delivery": days,
            "items": per, "asks": list(dict.fromkeys(asks)), "notes": list(dict.fromkeys(rs)), "pickup_needed": True}


# ---------------------------------------------------------------- QC checklist
QC_BASE = [("same_item", "Same item (name / SKU / colour / size)"), ("qty_ok", "Quantity complete"),
           ("not_empty", "Box is not empty / no stones or bricks"), ("parts_ok", "All parts / accessories")]
QC_EXTRA = {"clothes": [("tags_ok", "Tags are attached"), ("unused_ok", "Not worn / washed (stains, smell, creases)")],
            "footwear": [("unused_ok", "Soles clean, not worn"), ("box_ok", "Shoe box")],
            "electronics": [("serial_ok", "Serial / IMEI matches the order"), ("works_ok", "Tested by switching it on"), ("box_ok", "Box + charger / cable")],
            "cosmetics": [("seal_ok", "Seal not opened")], "jewellery": [("hallmark_ok", "Hallmark / weight same")],
            "innerwear": [("seal_ok", "Pack sealed")]}


def qc_list(cats: list[str], policy: dict[str, Any]) -> list[dict[str, str]]:
    out = list(QC_BASE)
    for c in cats:
        for x in QC_EXTRA.get(c, []):
            if x not in out:
                out.append(x)
    if policy.get("need_tags") and ("tags_ok", QC_EXTRA["clothes"][0][1]) not in out:
        out.append(("tags_ok", "Tags are attached"))
    if policy.get("need_packaging") and not any(k == "box_ok" for k, _ in out):
        out.append(("box_ok", "Original packing"))
    if policy.get("need_unused") and not any(k == "unused_ok" for k, _ in out):
        out.append(("unused_ok", "Unused"))
    return [{"key": k, "label": v} for k, v in out]


# ---------------------------------------------------------------- the refund sum (by code)
def _r(x: float) -> float:
    return round(x + 1e-9, 2)


def refund_calc(policy: dict[str, Any], reason: str, items: list[dict[str, Any]], order: dict[str, Any], *,
                same_state: bool | None = True, extra_deduction: float = 0.0, extra_reason: str = "", full_order: bool | None = None) -> dict[str, Any]:
    """items: [{name, qty (being returned), price (selling price per unit incl GST), gst_pct, order_qty}].
    order: {items_total (all items as sold, incl GST), coupon, shipping}. Returns lines, deductions, total and the GST split.
    Rules: coupon shared pro-rata on value; forward shipping back when it is her fault or the whole order comes back
    and she charged it; restocking / pickup fee only on change-of-mind returns, never when she was at fault."""
    fault = reason in SELLER_FAULT
    items_total = float(order.get("items_total") or 0) or sum(float(i.get("price", 0)) * float(i.get("order_qty") or i.get("qty") or 1) for i in items)
    coupon = max(0.0, float(order.get("coupon") or 0))
    shipping = max(0.0, float(order.get("shipping") or 0))
    lines, gst_rows = [], []
    value = 0.0
    for i in items:
        q = max(0.0, float(i.get("qty") or 1))
        p = max(0.0, float(i.get("price") or 0))
        gross = _r(q * p)
        share = _r(coupon * gross / items_total) if items_total and coupon else 0.0
        net = _r(gross - share)
        value += net
        lines.append({"name": i.get("name", ""), "qty": q, "price": p, "gross": gross, "coupon_share": share, "net": net})
        r = max(0.0, float(i.get("gst_pct") or 0))
        taxable = _r(net / (1 + r / 100)) if r else net
        gst_rows.append({"name": i.get("name", ""), "hsn": i.get("hsn", ""), "rate": r, "taxable": taxable, "gst": _r(net - taxable)})
    value = _r(value)
    returned_qty = sum(float(i.get("qty") or 1) for i in items)
    order_qty = sum(float(i.get("order_qty") or i.get("qty") or 1) for i in items) if full_order is None else None
    whole = full_order if full_order is not None else (value + sum(l["coupon_share"] for l in lines) >= items_total - 0.5 and returned_qty >= (order_qty or 0))
    notes0 = [] if fault or not shipping or policy.get("ship_back_on_full") else ["Delivery charge not refunded (change of mind; refunded if the fault is yours)"]
    add, ded = [], []
    if shipping and (fault or (whole and policy.get("ship_back_on_full"))):
        add.append({"what": "Delivery charge refunded" + (" (your fault)" if fault else " (whole order returned, your policy)"), "amount": _r(shipping)})
    if not fault:
        if policy.get("restocking_pct"):
            ded.append({"what": f"Restocking fee {policy['restocking_pct']:g}% (your policy, change of mind)",
                        "amount": _r(value * float(policy["restocking_pct"]) / 100)})
        if policy.get("reverse_fee"):
            ded.append({"what": "Pickup charge (your policy, change of mind)", "amount": _r(min(float(policy["reverse_fee"]), value))})
    if extra_deduction and extra_deduction > 0:
        ded.append({"what": "QC deduction: " + (extra_reason or "damage caused by the customer")[:120], "amount": _r(extra_deduction)})
    total = _r(value + sum(a["amount"] for a in add) - sum(d["amount"] for d in ded))
    if total < 0:
        total = 0.0
    taxable = _r(sum(g["taxable"] for g in gst_rows))
    gst = _r(sum(g["gst"] for g in gst_rows))
    split = ({"cgst": _r(gst / 2), "sgst": _r(gst - _r(gst / 2)), "igst": 0.0} if same_state else {"cgst": 0.0, "sgst": 0.0, "igst": gst})
    notes = list(notes0)
    if ded and not fault:
        notes.append("GST may apply separately on a restocking / pickup fee - ask your CA")
    if coupon:
        notes.append("The coupon share was deducted in proportion to each item's price (pro-rata)")
    return {"lines": lines, "items_value": value, "add": add, "deductions": ded, "total": total, "fault": fault,
            "gst": {"rows": gst_rows, "taxable": taxable, "tax": gst, **split, "same_state": bool(same_state)}, "notes": notes}


# ---------------------------------------------------------------- refund modes, and the dark-pattern guard
def refund_mode(policy: dict[str, Any], reason: str, customer_choice: str, paid_mode: str) -> tuple[str, list[str]]:
    """original | upi | bank | store_credit | exchange. Store credit only when the customer chose it (CCPA dark patterns:
    no forced action); a COD order can't go back 'original', so it goes to the customer's own UPI / bank."""
    notes: list[str] = []
    ch = (customer_choice or "").lower()
    if ch in ("exchange", "store_credit"):
        return ch, notes
    if policy.get("refund_mode") == "store_credit":
        notes.append("Your policy says store credit, but the customer asked for money back: store credit cannot be forced "
                     "(CCPA dark patterns) - and if the fault is yours the money must be refunded")
    if (paid_mode or "").lower() in ("cod", "cash", "nakad"):
        notes.append("COD order: the money goes to the customer's own UPI ID / bank (ask the customer for the UPI ID; never a PIN / OTP)")
        return ("upi" if ch != "bank" else "bank"), notes
    if ch in ("upi", "bank"):
        return ch, notes
    return "original", notes


# ---------------------------------------------------------------- fraud signals (signals, never verdicts)
def signals(history: list[dict[str, Any]], this: dict[str, Any], qc: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """history: this customer's other returns [{created (date), reason, value, photo_hashes}]; this: {reason, value,
    categories, delivered_on, photo_hashes, photo_dates (EXIF dates, before stripping)}."""
    out: list[dict[str, str]] = []
    recent = [h for h in history if h.get("days_ago", 999) <= 90]
    if len(recent) >= 3:
        out.append({"kind": "serial_returner", "text": f"This customer has {len(recent)} more returns in the last 90 days"})
    if this.get("reason") in ("size_fit", "changed_mind", "quality") and set(this.get("categories") or []) & {"clothes", "footwear", "jewellery"}:
        if any(h.get("reason") in ("size_fit", "changed_mind", "quality") for h in recent):
            out.append({"kind": "wardrobing", "text": "Returned a wearable item before saying 'changed my mind': check tags / stains / smell at QC"})
    if qc:
        cl = qc.get("checklist") or {}
        if cl.get("not_empty") is False:
            out.append({"kind": "empty_box", "text": "Box was empty / had something else at QC: claim from the courier with the video"})
        if cl.get("same_item") is False:
            out.append({"kind": "switched_item", "text": "The returned item is not the one ordered"})
        if cl.get("tags_ok") is False or cl.get("unused_ok") is False:
            out.append({"kind": "used_item", "text": "The item looks worn / used"})
    seen = {ph for h in history for ph in h.get("photo_hashes") or []}
    if seen & set(this.get("photo_hashes") or []):
        out.append({"kind": "photo_reused", "text": "This same photo was used in an earlier return"})
    dl = this.get("delivered_on")
    for d in this.get("photo_dates") or []:
        if dl and d and d < dl:
            out.append({"kind": "old_photo", "text": f"The photo is dated {d.isoformat()}, before delivery ({dl.isoformat()})"})
            break
    if float(this.get("value") or 0) >= 10000 and not history and this.get("reason") in ("missing_item", "wrong_item", "damaged"):
        out.append({"kind": "high_value", "text": "High amount + first-time customer: do QC with video"})
    return out


NEVER = ("Hoola never sends money: every refund is made by you after your tap (fingerprint)",
         "If the fault is yours, you cannot refuse a return / refund (E-Commerce Rules 2020, Rule 6(3) / 7(4))",
         "Store credit only if the customer chooses it (CCPA dark patterns 2023)",
         "The customer is never asked for a UPI PIN / OTP / card number",
         "Fraud signals are only signals: the decision is yours")

LAW = [
    {"what": "Faulty goods", "text": "Broken, faulty, fake, not as shown, or late: you cannot refuse to take it back or refuse a refund.",
     "source": "Consumer Protection (E-Commerce) Rules 2020, Rule 6(3), 7(4)"},
    {"what": "Policy shown clearly", "text": "Return / refund / exchange terms and the return shipping cost must be shown before purchase.",
     "source": "E-Commerce Rules 2020, Rule 6(5)(g), 7(1)(a)"},
    {"what": "Refund time", "text": "An approved refund within a 'reasonable period'; complaints acknowledged in 48 hours and resolved in 1 month.",
     "source": "E-Commerce Rules 2020, Rule 4(10), 4(5)"},
    {"what": "Store credit", "text": "Forcing store credit or hiding the refund button is a dark pattern.",
     "source": "CCPA Dark Patterns Guidelines 2023 (30 Nov 2023)"},
    {"what": "Failed UPI on the bank's side", "text": "Money was debited but did not reach the merchant: the bank reverses it itself within T+5 days, with ₹100 / day for delay.",
     "source": "RBI DPSS.CO.PD No.629/02.01.014/2019-20 (20 Sep 2019)"},
    {"what": "GST credit note", "text": "Credit note on a sales return (Sec 34, Rule 53); report in GSTR-1 by 30 November of the next FY or the annual return, whichever is earlier.",
     "source": "CGST Act Sec 34, Rule 53"},
]
