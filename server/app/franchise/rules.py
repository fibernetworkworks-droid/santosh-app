"""Franchise rules Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.115). Pure functions.

GST: franchise fee, royalty and franchisor-run marketing fund are taxable at 18% (SAC 997336); an Indian franchisor charges
it (CGST + SGST or IGST), a foreign franchisor's fee is under reverse charge (the franchisee pays IGST 18% itself). ITC is
blocked for a restaurant on the 5% no-ITC rate. Income-tax Act 2025 Sec 393(1) (old 194J / 194I): TDS on royalty /
professional fees 10% (technical fees 2%) once the year's total crosses Rs 50,000; rent of land / building 10% above
Rs 50,000 a month (when she is a person who must deduct). FSSAI licence: 1-5 years; renewal opens 120 days before expiry;
filed in the last 30 days costs Rs 100 a day; after expiry up to 3x (90 days) / 5x (180 days) the yearly fee, then a
fresh licence. Cost ratios are rules of thumb for Indian QSR / cafe outlets; her own targets override them.
"""
from __future__ import annotations

from datetime import date, timedelta

GST_FEE = 18.0
TDS_ROYALTY = {"rate": 10.0, "year_threshold": 50000.0}
TDS_RENT = {"rate": 10.0, "month_threshold": 50000.0}
COST_KINDS = {"food": "Raw material / food cost", "staff": "Staff salary", "rent": "Rent + CAM", "utility": "Bijli / pani / gas",
              "aggregator": "Swiggy / Zomato commission", "marketing": "Local marketing", "maintenance": "Repair / maintenance",
              "royalty": "Royalty + fees", "other": "Other"}
TARGETS = {"food": 32.0, "staff": 18.0, "rent": 12.0, "utility": 6.0, "aggregator": 8.0}     # % of net sales
LICENCES = {"fssai": ("FSSAI licence", 120), "shop_act": ("Shop & Establishment", 60), "trade": ("Trade licence (municipal)", 60),
            "fire_noc": ("Fire NOC", 90), "gst": ("GST registration", 0), "music": ("Music licence (PPL / IPRS / Novex)", 30),
            "signage": ("Signage / hoarding permit", 60), "health": ("Health trade licence", 60), "lift": ("Lift licence", 60),
            "liquor": ("Liquor licence", 90), "pollution": ("Pollution consent (SPCB)", 120), "weights": ("Legal Metrology (weights)", 60),
            "other": ("Other licence", 60)}

NEVER = ("Royalty / fees Hoola kabhi nahi bharta; aap bank se bharti hain.",
         "Franchisor ko sales report / statement sirf aapki haan se.",
         "Licence ka form portal par aap / consultant bharte hain; Hoola tareekh aur kaagaz yaad dilata hai.",
         "Agreement ki shart ka matlab vakil / CA se pakka kariye; Hoola sirf tareekh aur hisaab rakhta hai.")


def royalty(base: float, pct: float, min_guarantee: float = 0.0) -> dict:
    calc = base * pct / 100
    top = max(0.0, (min_guarantee or 0.0) - calc)
    return {"calc": round(calc, 2), "min_topup": round(top, 2), "royalty": round(calc + top, 2)}


def fee_gst(fees: float, foreign: bool, intra: bool) -> dict:
    g = round(fees * GST_FEE / 100, 2)
    if foreign:
        return {"gst": g, "how": "rcm", "say": f"Videshi franchisor: IGST {g:,.0f} aap reverse charge mein bharengi (self-invoice, GSTR-3B 3.1(d))."}
    if intra:
        return {"gst": g, "how": "cgst_sgst", "say": f"CGST + SGST {g:,.0f} franchisor ke bill mein."}
    return {"gst": g, "how": "igst", "say": f"IGST {g:,.0f} franchisor ke bill mein."}


def tds_on_fee(fy_paid_before: float, this_fee: float, applies: bool) -> dict:
    """10% on royalty once the year's fees cross Rs 50,000 (deduct on the whole year once crossed: catch up)."""
    if not applies:
        return {"tds": 0.0, "applies": False}
    after = fy_paid_before + this_fee
    if after <= TDS_ROYALTY["year_threshold"]:
        return {"tds": 0.0, "applies": False}
    on = this_fee if fy_paid_before > TDS_ROYALTY["year_threshold"] else after
    return {"tds": round(on * TDS_ROYALTY["rate"] / 100, 2), "applies": True, "on": round(on, 2)}


def ratios(net_sales: float, costs: dict[str, float]) -> dict[str, float]:
    if net_sales <= 0:
        return {}
    return {k: round(v * 100 / net_sales, 1) for k, v in costs.items()}


def flags(r: dict[str, float], targets: dict[str, float]) -> list[str]:
    out = []
    for k, t in targets.items():
        if k in r and r[k] > t + 0.5:
            out.append(f"{COST_KINDS.get(k, k)} {r[k]}% (lakshya {t:g}%)")
    return out


def break_even(fixed_month: float, variable_pct: float) -> float | None:
    """Monthly net sales needed to cover fixed costs when variable costs (food, aggregator, royalty...) take variable_pct."""
    if variable_pct >= 100:
        return None
    return round(fixed_month / (1 - variable_pct / 100), 0)


def licence_status(kind: str, valid_to: date, on: date) -> dict:
    name, lead = LICENCES.get(kind, LICENCES["other"])
    days = (valid_to - on).days
    if days < 0:
        late = -days
        if kind == "fssai":
            txt = ("FSSAI khatam: 90 din tak 3 guna, 180 din tak 5 guna saal ki fees ke saath renew; uske baad naya licence."
                   if late <= 180 else "FSSAI 180 din se zyada khatam: naya licence lena hoga, tab tak khaana bechna mana.")
        else:
            txt = f"{name} {late} din pehle khatam: turant renew."
        return {"state": "expired", "days": days, "text": txt}
    if kind == "fssai" and days <= 30:
        return {"state": "late_window", "days": days, "text": f"FSSAI {days} din mein khatam: ab renew par Rs 100 roz late fee; aaj hi bhariye."}
    if lead and days <= lead:
        return {"state": "renew_now", "days": days, "text": f"{name} {days} din mein khatam: renew ki tayyari (window khuli)."}
    return {"state": "ok", "days": days, "text": f"{name} {valid_to.isoformat()} tak."}


def agreement_dates(start: date, term_years: int, notice_months: int, lock_in_years: int, add_months) -> dict:
    end = add_months(start, 12 * term_years) - timedelta(days=1) if term_years else None
    notice = add_months(end, -notice_months) if end and notice_months else None
    lock = add_months(start, 12 * lock_in_years) if lock_in_years else None
    return {"end": end.isoformat() if end else "", "notice_by": notice.isoformat() if notice else "", "lock_in_till": lock.isoformat() if lock else ""}
