"""Wholesale rules Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.107). Pure functions.

GST: tax invoice fields (Rule 46), HSN 4 digits up to Rs 5 crore AATO / 6 above; slabs 0 / 5 / 18 / 40 % since 22 Sep 2025;
intra-state CGST + SGST, inter-state IGST. E-invoice (IRN) for B2B when AATO > Rs 5 crore, reported within 30 days when
AATO >= Rs 10 crore. E-way bill: inter-state consignment > Rs 50,000; intra-state limit set by the state (Maharashtra,
Delhi, Tamil Nadu, Punjab, Bihar Rs 1 lakh); can't be made for an invoice older than 180 days; validity ~1 day per 200 km.
Income-tax Act 2025: TDS on purchase of goods Sec 393(1) (old 194Q) 0.1% above Rs 50 lakh a year from one seller when
the buyer's turnover > Rs 10 crore (5% without PAN); cash receipt Rs 2 lakh or more from one person in a day / one deal
is barred (Sec 221, old 269ST). MSME supplier: pay in 15 days (no agreement) / 45 days max, else the expense waits
(Sec 43B(h) carried into the 2025 Act). Cheque bounce (NI Act Sec 138): cheque valid 3 months, demand notice within 30
days of the bank's return memo, drawer gets 15 days, complaint within 30 days after that.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

GST_SLABS = (0.0, 5.0, 18.0, 40.0)
EWB_INTER = 50000.0
EWB_INTRA = {"27": 100000.0, "07": 100000.0, "33": 100000.0, "03": 100000.0, "10": 100000.0, "08": 100000.0, "19": 50000.0}
EINV_AATO = 5e7
EINV_30DAY_AATO = 1e8
CASH_LIMIT = 200000.0
TDS_PURCHASE = {"rate": 0.1, "threshold": 5e6, "buyer_turnover": 1e8, "no_pan": 5.0}
MSME_DAYS = (15, 45)
AGING = ((0, 30, "0-30"), (31, 60, "31-60"), (61, 90, "61-90"), (91, 10 ** 6, "90+"))

UNITS = {"bori": "BAG", "bag": "BAG", "bags": "BAG", "katta": "BAG", "kg": "KGS", "kilo": "KGS", "kgs": "KGS", "quintal": "QTL",
         "qtl": "QTL", "ton": "TON", "litre": "LTR", "liter": "LTR", "ltr": "LTR", "l": "LTR", "pc": "PCS", "pcs": "PCS", "piece": "PCS",
         "nag": "PCS", "box": "BOX", "peti": "BOX", "carton": "BOX", "dabba": "BOX", "packet": "PAC", "pack": "PAC", "dozen": "DOZ",
         "darjan": "DOZ", "tin": "NOS", "nos": "NOS", "bundle": "BDL", "gaddi": "BDL"}

NEVER = ("Paisa kabhi Hoola nahi leta / nahi bhejta; payment graahak aapko seedha deta hai.",
         "Bill, reminder ya order sirf aapki haan se bahar jaata hai.",
         "E-way bill / e-invoice (IRN) portal par aap ya aapka CA banata hai; Hoola sirf data taiyaar karta hai.",
         "Rs 2 lakh ya zyada nakad ek party se ek din / ek sauda mein nahi (Sec 221).",
         "Cheque bounce ka notice vakil se jaanch kar bhejiye; Hoola sirf tareekh yaad dilata hai.")


def money(v) -> float:
    if v is None or v == "":
        return 0.0
    s = str(v).replace(",", "").replace("₹", "").replace("Rs", "").replace("rs", "").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    if not m:
        return 0.0
    n = float(m.group(0))
    low = s.lower()
    if "lakh" in low or "lac" in low:
        n *= 1e5
    elif re.search(r"\bcr|crore", low):
        n *= 1e7
    elif re.search(r"\d\s*k\b", low):
        n *= 1e3
    return n


def r2(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def parse_order(text: str) -> list[dict]:
    """'Atta 10 bori, cheeni 5 bag @ 4200, 20 kg dal' -> [{item, qty, unit, rate}]. Lines / commas split items."""
    out = []
    for part in re.split(r"[,\n;]+|\s+aur\s+|\s+and\s+", str(text or "")):
        p = part.strip(" .-")
        if not p:
            continue
        rate = None
        m = re.search(r"@\s*(?:rs\.?|₹)?\s*([\d,.]+)", p, re.I)
        if m:
            rate = money(m.group(1))
            p = (p[:m.start()] + p[m.end():]).strip()
        m = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?", p)
        if not m:
            continue
        qty = float(m.group(1))
        unit_word = (m.group(2) or "").lower()
        unit = UNITS.get(unit_word, "")
        name = (p[:m.start()] + " " + p[m.end():]) if unit or not unit_word else (p[:m.start()] + " " + p[m.start(2):])
        if unit_word and not unit:
            name = p[:m.start()] + " " + p[m.end() - len(m.group(2)):]
        name = re.sub(r"\s+", " ", name).strip(" .-")
        if not name or qty <= 0:
            continue
        out.append({"item": name, "qty": qty, "unit": unit, "rate": rate})
    return out


def is_intra(seller_state: str, buyer_state: str) -> bool:
    return not buyer_state or seller_state == buyer_state


def tax_split(taxable: float, rate: float, intra: bool) -> dict:
    t = taxable * rate / 100
    if intra:
        h = r2(t / 2)
        return {"cgst": h, "sgst": h, "igst": 0.0, "tax": r2(2 * h)}
    return {"cgst": 0.0, "sgst": 0.0, "igst": r2(t), "tax": r2(t)}


def eway_needed(value: float, seller_state: str, buyer_state: str) -> tuple[bool, float]:
    intra = is_intra(seller_state, buyer_state)
    limit = EWB_INTRA.get(seller_state, EWB_INTER) if intra else EWB_INTER
    return value > limit, limit


def eway_days(km: float) -> int:
    return max(1, -(-int(km or 0) // 200)) if km else 1


def hsn_digits(aato: float) -> int:
    return 6 if aato > EINV_AATO else 4


def aging_bucket(days: int) -> str:
    for lo, hi, name in AGING:
        if lo <= days <= hi:
            return name
    return "0-30"


def credit_check(outstanding: float, overdue: float, limit: float, new_amount: float, oldest_overdue_days: int) -> dict:
    """ok | warn | stop with the reason (she decides; Hoola only says)."""
    after = outstanding + new_amount
    if limit and after > limit:
        return {"level": "stop", "text": f"Credit limit Rs {limit:,.0f} paar ho jayegi (baaki ke baad Rs {after:,.0f})."}
    if oldest_overdue_days > 60:
        return {"level": "stop", "text": f"Purana bill {oldest_overdue_days} din se baaki (Rs {overdue:,.0f})."}
    if overdue > 0:
        return {"level": "warn", "text": f"Rs {overdue:,.0f} due date paar; order ke saath vasooli ki baat kariye."}
    if limit and after > 0.8 * limit:
        return {"level": "warn", "text": f"Limit ka {after * 100 / limit:.0f}% bhar jayega."}
    return {"level": "ok", "text": "Credit theek."}


def cheque_steps(return_memo: date) -> dict:
    notice_by = return_memo + timedelta(days=30)
    return {"notice_by": notice_by.isoformat(),
            "pay_window": "notice milne ke 15 din",
            "complaint_window": "15 din khatam hone ke agle 30 din mein (apne bank branch ke magistrate ke paas)",
            "say": f"Cheque bounce: {notice_by.strftime('%d %b %Y')} tak likhit demand notice (registered post), vakil se jaanch kar."}


def tds_on_purchase(fy_purchases: float, this_bill: float, my_turnover: float, pan: bool = True) -> dict:
    """Sec 393(1): 0.1% on the part above Rs 50 lakh in the FY (only if her turnover last FY > Rs 10 crore)."""
    if my_turnover <= TDS_PURCHASE["buyer_turnover"]:
        return {"applies": False, "tds": 0.0}
    before, after = fy_purchases, fy_purchases + this_bill
    above = max(0.0, after - TDS_PURCHASE["threshold"]) - max(0.0, before - TDS_PURCHASE["threshold"])
    rate = TDS_PURCHASE["rate"] if pan else TDS_PURCHASE["no_pan"]
    return {"applies": above > 0, "tds": r2(above * rate / 100), "on": r2(above), "rate": rate}


def msme_due(bill_date: date, agreed_days: int | None) -> date:
    d = MSME_DAYS[1] if agreed_days else MSME_DAYS[0]
    return bill_date + timedelta(days=min(int(agreed_days or d), MSME_DAYS[1]))


def reorder_qty(sold_30: float, free: float, lead_days: int, cover_days: int = 15) -> float:
    """Daily sale x (lead time + cover days) - what is free now (never negative)."""
    daily = sold_30 / 30.0
    need = daily * (max(1, lead_days) + cover_days) - (free or 0.0)
    return max(0.0, round(need, 1))
