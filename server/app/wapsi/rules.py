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
    "damaged": {"label": "Toota / damage aaya", "fault": True, "proof": True,
                "words": ("damage", "toota", "tuta", "tut gaya", "phata", "phati", "fata", "fati", "phat ", "crack", "broken", "dent", "leak", "kharab aaya", "tooti")},
    "defective": {"label": "Chal nahi raha / kharab", "fault": True, "proof": True,
                  "words": ("defect", "kaam nahi", "chal nahi", "not working", "band ho", "on nahi", "kharab", "faulty", "dead", "awaaz nahi", "aawaz nahi", "sound nahi", "charge nahi", "nahi chalta", "nahi chalti", "hang ho")},
    "wrong_item": {"label": "Galat saamaan aaya", "fault": True, "proof": True,
                   "words": ("galat", "wrong", "dusra", "doosra", "alag item", "different item", "wrong colour", "wrong color", "wrong size bheja")},
    "missing_item": {"label": "Kuch kam / gayab", "fault": True, "proof": True,
                     "words": ("missing", "gayab", "kam aaya", "nahi aaya", "khaali", "empty", "part nahi", "adhoora")},
    "not_as_described": {"label": "Jaisa dikhaya waisa nahi", "fault": True, "proof": True,
                         "words": ("not as described", "photo jaisa nahi", "jaisa dikhaya", "fake", "duplicate", "nakli", "original nahi", "different from")},
    "expired": {"label": "Expiry / purana maal", "fault": True, "proof": True,
                "words": ("expire", "expiry", "purana", "date nikal", "kharab ho gaya khana", "sada", "fungus")},
    "late_delivery": {"label": "Der se aaya", "fault": True, "proof": False, "words": ("late", "der se", "der ho", "delay")},
    "size_fit": {"label": "Size / fit theek nahi", "fault": False, "proof": False,
                 "words": ("size", "fit", "chhota", "bada", "tight", "loose", "dheela")},
    "quality": {"label": "Quality pasand nahi", "fault": False, "proof": False, "words": ("quality", "kapda patla", "cheap lag", "pasand nahi aaya quality")},
    "changed_mind": {"label": "Man badal gaya / zaroorat nahi", "fault": False, "proof": False,
                     "words": ("man badal", "nahi chahiye", "zaroorat nahi", "changed my mind", "pasand nahi", "dont want", "don't want", "mood")},
    "ordered_by_mistake": {"label": "Galti se order", "fault": False, "proof": False, "words": ("galti se", "by mistake", "do baar", "twice", "duplicate order")},
    "other": {"label": "Aur kuch", "fault": False, "proof": False, "words": ()},
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
CAT_LABEL = {"innerwear": "innerwear", "clothes": "kapde", "footwear": "joote-chappal", "electronics": "electronics",
             "cosmetics": "cosmetics", "food": "khana / grocery", "medicine": "dawai", "jewellery": "jewellery", "custom": "custom / naam wala",
             "home": "ghar ka saamaan", "books": "kitaabein", "toys": "khilone", "other": "baaki saamaan"}


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
            got.append(f"Man badalne par {pol['restocking_pct']:g}% restocking fee")
            continue
        if re.search(r"(pickup|return shipping|wapsi ka kharcha|reverse|courier charge|shipping charge)", c) and re.search(r"(₹|rs\.?|rupay|rupee)\s*(\d+)|(\d+)\s*(₹|rs|rupay|rupee)", c):
            mm = re.search(r"(?:₹|rs\.?|rupay|rupee)\s*(\d+)|(\d+)\s*(?:₹|rs|rupay|rupee)", c)
            pol["reverse_fee"] = float(mm.group(1) or mm.group(2))
            got.append(f"Man badalne par pickup charge ₹{pol['reverse_fee']:g}")
            continue
        if "unboxing" in c or ("video" in c and ("khol" in c or "open" in c)):
            vc = cats or ["electronics"]
            pol["video_for"] = sorted(set(pol["video_for"]) | set(vc))
            got.append("Unboxing video chahiye (damage / kam saamaan ke daawe par): " + ", ".join(CAT_LABEL.get(x, x) for x in vc))
            continue
        if re.search(r"(store credit|wallet|coupon|credit note|voucher)", c):
            if re.search(r"(sirf|only|hi milega|hi denge)", c) and not neg:
                pol["refund_mode"] = "store_credit"
                got.append("Refund: store credit (sirf graahak ki marzi se; galti aapki ho to paisa wapas - kanoon)")
            else:
                got.append("Store credit graahak chahe to")
            continue
        if re.search(r"(original|same mode|jaise pay|usi mode|source|bank mein|account mein wapas)", c) and re.search(r"refund|paisa|paise", c):
            pol["refund_mode"] = "original"
            got.append("Refund: jis tareeke se pay kiya usi mein")
            continue
        if "exchange" in c or "badal" in c and "man badal" not in c:
            pol["exchange"] = not bool(neg)
            got.append("Exchange milega" if pol["exchange"] else "Exchange nahi")
            if not m_days:
                continue
        if re.search(r"(tag|label)", c) and not neg:
            pol["need_tags"] = True
            got.append("Tag lage hone chahiye")
        if re.search(r"(packing|packaging|dabba|box|original pack)", c) and not cats and not m_days:
            pol["need_packaging"] = True
            got.append("Original packing mein")
        if re.search(r"(unused|use na|bina use|istemal|istemaal|pehna na|pehne bina|not used|use nahi)", c) and not m_days:
            pol["need_unused"] = True
            got.append("Bina use kiya hua")
        if re.search(r"(rakh lo|rakh lijiye|wapas mat bhejo|pickup nahi)", c):
            mm = re.search(r"(\d+)", c)
            if mm:
                pol["no_pickup_below"] = float(mm.group(1))
                got.append(f"₹{mm.group(1)} se kam ka saamaan wapas nahi mangwana, seedha refund")
            continue
        if m_days and re.search(r"refund", c) and re.search(r"(andar|within|tak|mein)", c) and not re.search(r"return|wapas", c):
            pol["refund_days"] = int(m_days.group(1))
            got.append(f"Refund {pol['refund_days']} din mein")
            continue
        if neg and cats and re.search(r"(return|wapas|wapsi|returnable)", c) and not m_days:
            pol["non_returnable"] = sorted(set(pol["non_returnable"]) | set(cats))
            got.append("Wapas nahi: " + ", ".join(CAT_LABEL.get(x, x) for x in cats))
            continue
        if re.search(r"(no return|return nahi|wapsi nahi|non[- ]?returnable)", c) and not cats and not m_days:
            pol["refund"] = False
            got.append("Man badalne par return nahi (galti aapki ho to kanoonan lena padega)")
            continue
        if m_days and re.search(r"(return|wapas|wapsi|replace|refund)", c):
            n = int(m_days.group(1))
            for cat in (cats or ["default"]):
                pol["window_days"][cat] = n
            got.append(f"{n} din mein return" + (" (" + ", ".join(CAT_LABEL.get(x, x) for x in cats) + ")" if cats else ""))
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
    out = [f"Delivery ke {wd.get('default', 7)} din tak return"]
    for k, v in wd.items():
        if k != "default":
            out.append(f"{CAT_LABEL.get(k, k)}: {v} din")
    if p.get("non_returnable"):
        out.append("Wapas nahi (man badalne par): " + ", ".join(CAT_LABEL.get(x, x) for x in p["non_returnable"]))
    conds = [t for k, t in (("need_tags", "tag lage hon"), ("need_packaging", "original packing"), ("need_unused", "bina use")) if p.get(k)]
    if conds:
        out.append("Shart: " + ", ".join(conds))
    if p.get("video_for"):
        out.append("Unboxing video maangein: " + ", ".join(CAT_LABEL.get(x, x) for x in p["video_for"]))
    if p.get("restocking_pct"):
        out.append(f"Man badalne par {p['restocking_pct']:g}% restocking fee")
    if p.get("reverse_fee"):
        out.append(f"Man badalne par pickup ₹{p['reverse_fee']:g}")
    out.append("Exchange: haan" if p.get("exchange") else "Exchange: nahi")
    out.append("Refund: " + ("jis mode se pay kiya" if p.get("refund_mode") == "original" else "store credit (graahak ki marzi se)"))
    out.append(f"Refund QC ke {p.get('refund_days', 7)} din mein")
    if p.get("no_pickup_below"):
        out.append(f"₹{p['no_pickup_below']:g} se kam: saamaan wapas nahi, seedha refund")
    out.append("Galti aapki ho (toota / kharab / galat / kam / jaisa dikhaya waisa nahi / der se) to return aur refund se mana nahi (E-Commerce Rules 2020)")
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
        asks.append("Delivery ki tareekh chahiye (window ginne ke liye).")
    elif days is not None and days < 0:
        asks.append("Delivery ki tareekh aage ki hai; sahi tareekh bataiye.")
    for it in items:
        cat = it.get("category") or category_of(str(it.get("name", "")))
        win = int(policy.get("window_days", {}).get(cat, policy.get("window_days", {}).get("default", 7)))
        inwin = days is None or days <= win
        row = {"name": it.get("name", ""), "category": cat, "window": win, "in_window": inwin, "ok": True, "notes": []}
        if cat in policy.get("non_returnable", []):
            if fault:
                row["notes"].append(f"{CAT_LABEL.get(cat, cat)} aam taur par wapas nahi, par galti aapki hai: kanoon ke hisaab se lena hoga")
            else:
                row["ok"] = False
                row["notes"].append(f"{CAT_LABEL.get(cat, cat)} aapki policy mein wapas nahi hota")
        if not inwin:
            if fault:
                row["notes"].append(f"{win} din ki window nikal gayi ({days} din), par shikayat galti ki hai: warranty / kanoon dekhiye, seedha mana mat kijiye")
                asks.append(f"{it.get('name', 'Saamaan')}: window ke baad galti ki shikayat - aapka faisla")
            else:
                row["ok"] = False
                row["notes"].append(f"{win} din ki window nikal gayi ({days} din)")
        per.append(row)
    if not fault and not policy.get("refund", True) and want == "refund":
        blocks.append("Aapki policy mein man badalne par refund nahi (exchange ho sakta hai)" if policy.get("exchange") else "Aapki policy mein man badalne par return nahi")
    if want == "exchange" and not policy.get("exchange", True) and not fault:
        blocks.append("Aapki policy mein exchange nahi")
    photos = int(proof.get("photos", 0))
    videos = int(proof.get("videos", 0))
    if REASONS[reason]["proof"] and photos == 0 and videos == 0:
        asks.append("Graahak se photo maangiye: poora saamaan, kharabi paas se, aur parcel ka label")
    cats = {r["category"] for r in per}
    if reason in ("damaged", "missing_item", "wrong_item") and set(policy.get("video_for", [])) & cats and videos == 0:
        rs.append("Aapki policy unboxing video maangti hai; na ho to bhi photo / QC se faisla kijiye (sirf video na hone par mana na karein)")
    look = proof.get("look") or {}
    if look.get("not_product"):
        asks.append("Photo mein yeh saamaan nahi dikh raha: saaf photo maangiye")
    if reason == "damaged" and photos and look and look.get("damage_seen") is False:
        asks.append("Photo mein damage saaf nahi dikh raha: paas se photo maangiye")
    if look.get("mismatch"):
        asks.append("Photo ka saamaan order se alag lag raha hai: dekh lijiye")
    if not fault:
        conds = [t for k, t in (("need_tags", "tag lage hon"), ("need_packaging", "original packing"), ("need_unused", "bina use"))
                 if policy.get(k)]
        if conds:
            rs.append("Pickup / QC par dekhna: " + ", ".join(conds))
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
        rs.append("Kuch saamaan policy mein aata hai, kuch nahi: " + ", ".join(r["name"] for r in bad) + " wapas nahi")
    for r in per:
        rs.extend(f"{r['name']}: {n}" for n in r["notes"])
    rs.extend(blocks)
    return {"verdict": verdict, "fault": fault, "reason": reason, "reason_label": REASONS[reason]["label"], "days_since_delivery": days,
            "items": per, "asks": list(dict.fromkeys(asks)), "notes": list(dict.fromkeys(rs)), "pickup_needed": True}


# ---------------------------------------------------------------- QC checklist
QC_BASE = [("same_item", "Wahi saamaan hai (naam / SKU / rang / size)"), ("qty_ok", "Ginti poori"),
           ("not_empty", "Dabba khaali nahi / pathar-eent nahi"), ("parts_ok", "Saare parts / accessories")]
QC_EXTRA = {"clothes": [("tags_ok", "Tag lage hain"), ("unused_ok", "Pehna / dhula nahi (daag, khushboo, silvatein)")],
            "footwear": [("unused_ok", "Talwe saaf, pehne nahi"), ("box_ok", "Joote ka dabba")],
            "electronics": [("serial_ok", "Serial / IMEI order wala"), ("works_ok", "Chalu karke dekha"), ("box_ok", "Dabba + charger / cable")],
            "cosmetics": [("seal_ok", "Seal nahi khula")], "jewellery": [("hallmark_ok", "Hallmark / wazan same")],
            "innerwear": [("seal_ok", "Packet seal band")]}


def qc_list(cats: list[str], policy: dict[str, Any]) -> list[dict[str, str]]:
    out = list(QC_BASE)
    for c in cats:
        for x in QC_EXTRA.get(c, []):
            if x not in out:
                out.append(x)
    if policy.get("need_tags") and ("tags_ok", QC_EXTRA["clothes"][0][1]) not in out:
        out.append(("tags_ok", "Tag lage hain"))
    if policy.get("need_packaging") and not any(k == "box_ok" for k, _ in out):
        out.append(("box_ok", "Original packing"))
    if policy.get("need_unused") and not any(k == "unused_ok" for k, _ in out):
        out.append(("unused_ok", "Bina use kiya hua"))
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
    notes0 = [] if fault or not shipping or policy.get("ship_back_on_full") else ["Delivery charge wapas nahi (man badalne par; galti aapki ho to wapas)"]
    add, ded = [], []
    if shipping and (fault or (whole and policy.get("ship_back_on_full"))):
        add.append({"what": "Delivery charge wapas" + (" (galti aapki)" if fault else " (poora order wapas, aapki policy)"), "amount": _r(shipping)})
    if not fault:
        if policy.get("restocking_pct"):
            ded.append({"what": f"Restocking fee {policy['restocking_pct']:g}% (aapki policy, man badalne par)",
                        "amount": _r(value * float(policy["restocking_pct"]) / 100)})
        if policy.get("reverse_fee"):
            ded.append({"what": "Pickup charge (aapki policy, man badalne par)", "amount": _r(min(float(policy["reverse_fee"]), value))})
    if extra_deduction and extra_deduction > 0:
        ded.append({"what": "QC kataayi: " + (extra_reason or "kharabi graahak ki taraf se")[:120], "amount": _r(extra_deduction)})
    total = _r(value + sum(a["amount"] for a in add) - sum(d["amount"] for d in ded))
    if total < 0:
        total = 0.0
    taxable = _r(sum(g["taxable"] for g in gst_rows))
    gst = _r(sum(g["gst"] for g in gst_rows))
    split = ({"cgst": _r(gst / 2), "sgst": _r(gst - _r(gst / 2)), "igst": 0.0} if same_state else {"cgst": 0.0, "sgst": 0.0, "igst": gst})
    notes = list(notes0)
    if ded and not fault:
        notes.append("Restocking / pickup fee par GST alag se lag sakta hai - apne CA se poochh lijiye")
    if coupon:
        notes.append("Coupon ka hissa har item ke daam ke hisaab se kata (pro-rata)")
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
        notes.append("Aapki policy store credit kehti hai, par graahak ne paisa maanga hai: store credit zabardasti nahi diya ja sakta "
                     "(CCPA dark patterns) - aur galti aapki ho to paisa wapas dena hi hai")
    if (paid_mode or "").lower() in ("cod", "cash", "nakad"):
        notes.append("COD order: paisa graahak ke apne UPI ID / bank mein jayega (graahak se UPI ID lijiye; PIN / OTP kabhi nahi)")
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
        out.append({"kind": "serial_returner", "text": f"Is graahak ke 90 din mein {len(recent)} aur return"})
    if this.get("reason") in ("size_fit", "changed_mind", "quality") and set(this.get("categories") or []) & {"clothes", "footwear", "jewellery"}:
        if any(h.get("reason") in ("size_fit", "changed_mind", "quality") for h in recent):
            out.append({"kind": "wardrobing", "text": "Pehle bhi pehnne wali cheez 'man badla' bol kar lautayi: QC mein tag / daag / khushboo dekhiye"})
    if qc:
        cl = qc.get("checklist") or {}
        if cl.get("not_empty") is False:
            out.append({"kind": "empty_box", "text": "QC mein dabba khaali / kuch aur nikla: video ke saath courier ko claim kijiye"})
        if cl.get("same_item") is False:
            out.append({"kind": "switched_item", "text": "Wapas aaya saamaan order wala nahi"})
        if cl.get("tags_ok") is False or cl.get("unused_ok") is False:
            out.append({"kind": "used_item", "text": "Saamaan pehna / use kiya hua lagta hai"})
    seen = {ph for h in history for ph in h.get("photo_hashes") or []}
    if seen & set(this.get("photo_hashes") or []):
        out.append({"kind": "photo_reused", "text": "Yahi photo pehle kisi aur return mein aa chuki hai"})
    dl = this.get("delivered_on")
    for d in this.get("photo_dates") or []:
        if dl and d and d < dl:
            out.append({"kind": "old_photo", "text": f"Photo {d.isoformat()} ki hai, delivery ({dl.isoformat()}) se pehle ki"})
            break
    if float(this.get("value") or 0) >= 10000 and not history and this.get("reason") in ("missing_item", "wrong_item", "damaged"):
        out.append({"kind": "high_value", "text": "Bada amount + pehli baar ka graahak: QC video ke saath kijiye"})
    return out


NEVER = ("Hoola paisa kabhi nahi bhejta: har refund aapke tap (fingerprint) ke baad aap khud karti hain",
         "Galti aapki ho to return / refund se mana nahi (E-Commerce Rules 2020, Rule 6(3) / 7(4))",
         "Store credit sirf graahak ki marzi se (CCPA dark patterns 2023)",
         "Graahak se UPI PIN / OTP / card number kabhi nahi maanga jaata",
         "Fraud ke signal sirf signal hain: faisla aapka")

LAW = [
    {"what": "Galti waala maal", "text": "Toota, kharab, nakli, jaisa dikhaya waisa nahi, ya der se aaya: wapas lene aur refund se mana nahi kar sakte.",
     "source": "Consumer Protection (E-Commerce) Rules 2020, Rule 6(3), 7(4)"},
    {"what": "Policy saaf dikhe", "text": "Return / refund / exchange ki sharten aur wapsi shipping ka kharcha khareedne se pehle dikhna chahiye.",
     "source": "E-Commerce Rules 2020, Rule 6(5)(g), 7(1)(a)"},
    {"what": "Refund ka samay", "text": "Mana hua refund 'reasonable period' mein; shikayat 48 ghante mein acknowledge, 1 mahine mein hal.",
     "source": "E-Commerce Rules 2020, Rule 4(10), 4(5)"},
    {"what": "Store credit", "text": "Zabardasti store credit ya refund button chhupana = dark pattern.",
     "source": "CCPA Dark Patterns Guidelines 2023 (30 Nov 2023)"},
    {"what": "Bank ki taraf ka failed UPI", "text": "Paisa kata par merchant tak nahi pahuncha: bank T+5 din mein khud lautata hai, der par ₹100 / din.",
     "source": "RBI DPSS.CO.PD No.629/02.01.014/2019-20 (20 Sep 2019)"},
    {"what": "GST credit note", "text": "Sales return par credit note (Sec 34, Rule 53); agle FY ki 30 November ya annual return, jo pehle ho, tak GSTR-1 mein.",
     "source": "CGST Act Sec 34, Rule 53"},
]
