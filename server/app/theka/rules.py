"""Contractor rules Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.117). Pure functions.

GST: works contracts (incl. government civil works) 18% from 22 Sep 2025; affordable housing (PMAY) 1% without ITC; pure labour
for an individual's own house exempt. GST TDS (CGST Sec 51): government / local authority / notified bodies deduct 2% of the
taxable value (excluding GST) when the contract value exceeds Rs 2.5 lakh; it reaches the contractor's cash ledger (GSTR-7A).
Income-tax Act 2025 Sec 393(1) (old 194C): TDS on contract payments 1% (individual / HUF) or 2% (others) above Rs 30,000 in one
payment or Rs 1 lakh in the year. BOCW welfare cess (Code on Social Security 2020, in force 21 Nov 2025): 1% of the cost of
construction (land excluded), deducted from bills by government / PSUs or paid in advance on self-assessment. Retention, security
deposit, mobilisation-advance recovery and performance security come from HER contract (NIT / agreement) and are set per project.
"""
from __future__ import annotations

from datetime import date, timedelta

GST_WORKS = 18.0
GST_TDS = {"rate": 2.0, "threshold": 250000.0}
IT_TDS = {"individual": 1.0, "other": 2.0, "single": 30000.0, "year": 100000.0}
LABOUR_CESS = 1.0
DOCS = ["Udyam / MSME certificate (EMD chhoot ho to)", "GST registration", "PAN", "Contractor registration (class) certificate",
        "Pichhle 3 / 5 saal ka turnover (CA certificate)", "Similar work completion certificates", "Solvency certificate (bank)",
        "ITR (pichhle 3 saal)", "EMD / bid security (DD / BG / online / declaration)", "DSC (class 3) - aapka", "Affidavit / undertaking (NIT ke format mein)",
        "Labour licence (agar NIT maange)", "EPF / ESIC registration", "Power of attorney (agar koi aur sign kare)"]

NEVER = ("Tender portal par bid Hoola submit nahi karta: DSC aur submit aapka.",
         "Bill department ko sirf aapki haan se; naap (measurement) jaisi likhi gayi waisi, badha-chadha kar nahi.",
         "Paisa Hoola nahi leta / bhejta; subcontractor ko payment aap karti hain.",
         "Rishwat / 'speed money' ka hisaab nahi rakhta, na usme madad.")


def it_tds(amount: float, fy_paid_before: float, individual: bool, pan: bool = True, fy_taxed_before: float = 0.0) -> dict:
    """Sec 393(1) on a contractor / subcontractor payment: above Rs 30,000 in one payment, or once the year's total crosses
    Rs 1 lakh - then on everything paid this year that was not taxed yet (catch-up)."""
    rate = (IT_TDS["individual"] if individual else IT_TDS["other"]) if pan else 20.0
    total = fy_paid_before + amount
    if total > IT_TDS["year"]:
        on = total - fy_taxed_before
    elif amount > IT_TDS["single"]:
        on = amount
    else:
        return {"tds": 0.0, "rate": rate, "applies": False}
    return {"tds": round(on * rate / 100, 2), "rate": rate, "applies": True, "on": round(on, 2)}


def deductions(taxable: float, gst: float, p: dict, mob_left: float) -> dict:
    """Deductions on one RA bill from the project's terms (p): retention %, sd %, it_tds %, gst_tds, cess %, mob recovery %."""
    d: dict[str, float] = {}
    if p.get("retention_pct"):
        d["retention"] = round(taxable * p["retention_pct"] / 100, 2)
    if p.get("sd_pct"):
        d["security_deposit"] = round(taxable * p["sd_pct"] / 100, 2)
    if p.get("it_tds_pct"):
        d["income_tax_tds"] = round(taxable * p["it_tds_pct"] / 100, 2)
    if p.get("gst_tds") and (p.get("value") or 0) > GST_TDS["threshold"]:
        d["gst_tds"] = round(taxable * GST_TDS["rate"] / 100, 2)
    if p.get("cess_pct"):
        d["labour_cess"] = round(taxable * p["cess_pct"] / 100, 2)
    if p.get("mob_pct") and mob_left > 0:
        d["mobilisation_recovery"] = round(min(mob_left, taxable * p["mob_pct"] / 100), 2)
    total = round(sum(d.values()), 2)
    return {"items": d, "total": total, "net": round(taxable + gst - total, 2)}


def deviation(cum_qty: float, boq_qty: float, limit_pct: float = 25.0) -> dict | None:
    if boq_qty <= 0:
        return {"level": "warn", "text": "BOQ mein nahi: extra item - department se approval / rate pehle."}
    over = (cum_qty - boq_qty) * 100 / boq_qty
    if over > limit_pct:
        return {"level": "stop", "text": f"BOQ se {over:.0f}% zyada (deviation limit {limit_pct:g}%): deviation / extra quantity approval chahiye."}
    if over > 0:
        return {"level": "warn", "text": f"BOQ se {over:.0f}% zyada: deviation statement banaiye."}
    return None


def delay(start: date, stipulated_end: date, on: date, progress_pct: float) -> dict:
    total = max(1, (stipulated_end - start).days)
    elapsed = max(0, (on - start).days)
    time_pct = min(100.0, elapsed * 100 / total)
    behind = time_pct - progress_pct
    late_days = (on - stipulated_end).days
    return {"time_pct": round(time_pct, 1), "progress_pct": round(progress_pct, 1), "behind_pct": round(behind, 1),
            "late_days": max(0, late_days),
            "say": (f"Samay {time_pct:.0f}% beeta, kaam {progress_pct:.0f}% hua" + (f" - {behind:.0f}% peeche." if behind > 10 else ".")
                    + (f" Tay tareekh se {late_days} din upar: EOT (extension) ki arzi hindrance register ke saath." if late_days > 0 else ""))}


def retention_release(completion: date | None, dlp_months: int, add_months) -> date | None:
    return add_months(completion, dlp_months) if completion else None


def tender_alert(last_date: date, on: date) -> str:
    d = (last_date - on).days
    if d < 0:
        return "Tareekh nikal gayi."
    if d == 0:
        return "Aaj aakhri din: DSC tayyar, server bheed se pehle submit kariye."
    if d <= 3:
        return f"{d} din baaki: kaagaz poore kariye, EMD tayyar."
    return f"{d} din baaki."
