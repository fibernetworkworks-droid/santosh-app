"""Audit rules and practice Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.96). Pure functions.

Standards on Auditing (ICAI): SA 320 materiality (judgement; common starting points 5% of profit before tax, 0.5-1% of
revenue or expenses, 1-2% of total assets, 1-5% of equity; performance materiality 50-75%; clearly trivial ~5%), SA 520
analytics, SA 240 journal-entry testing, SA 530 sampling, SA 505 confirmations, SA 570 going concern, SA 580
representations, SA 230 documentation. Income-tax Act 2025 (from 1 Apr 2026): tax audit Sec 63 (old 44AB) - FY
2025-26 still on Form 3CA / 3CB + 3CD, Form 26 from Tax Year 2026-27; cash payment over Rs 10,000 a day to one person
disallowed Sec 34(3) (old 40A(3)); cash receipt of Rs 2 lakh or more barred Sec 221 (old 269ST); cash loans / deposits
Rs 20,000+ Sec 219 / 220 (old 269SS / 269T); TDS Sec 393 thresholds. Companies: CARO 2020 (21 clauses) and the audit
trail (Rule 3(1) Accounts Rules, reported under Rule 11(g)).
"""
from __future__ import annotations

import math
import random
from collections import Counter
from datetime import date

# ---------------------------------------------------------------- materiality (SA 320 starting points; judgement decides)
BENCHMARKS = {"pbt": (5.0, "Profit before tax"), "revenue": (1.0, "Revenue"), "expenses": (1.0, "Total expenses"),
              "assets": (1.5, "Total assets"), "equity": (2.0, "Equity / net worth")}


def materiality(pbt: float, revenue: float, assets: float = 0.0, equity: float = 0.0, expenses: float = 0.0,
                benchmark: str = "", pct: float | None = None, risk: str = "normal") -> dict:
    """Overall materiality, performance materiality and the clearly-trivial line, with the reason for the benchmark."""
    vals = {"pbt": pbt, "revenue": revenue, "assets": assets, "equity": equity, "expenses": expenses}
    why = ""
    if not benchmark:
        if pbt > 0 and revenue and pbt >= 0.05 * revenue:
            benchmark, why = "pbt", "munafa sthir aur revenue ka 5%+ hai: profit before tax"
        elif revenue > 0:
            benchmark, why = "revenue", "munafa kam / ghata / asthir: revenue"
        elif assets > 0:
            benchmark, why = "assets", "revenue nahi: total assets"
        else:
            raise ValueError("Materiality ke liye PBT, revenue ya assets chahiye.")
    base = abs(float(vals.get(benchmark) or 0))
    p = float(pct) if pct else BENCHMARKS[benchmark][0]
    om = round(base * p / 100)
    pm_pct = {"high": 50, "normal": 65, "low": 75}.get(risk, 65)
    return {"benchmark": benchmark, "benchmark_label": BENCHMARKS[benchmark][1], "base": round(base), "pct": p, "overall": om,
            "performance_pct": pm_pct, "performance": round(om * pm_pct / 100), "trivial": round(om * 0.05),
            "why": why or "aapka chuna hua benchmark"}


# ---------------------------------------------------------------- analytical review (SA 520)
def variance(cur: float, prev: float, pm: float, pct_limit: float = 20.0) -> dict:
    diff = float(cur) - float(prev)
    pct = round(diff * 100 / abs(prev), 1) if prev else None
    flag = abs(diff) >= pm * 0.5 and (pct is None or abs(pct) >= pct_limit) and abs(diff) > 0
    return {"current": round(cur), "previous": round(prev), "diff": round(diff), "pct": pct, "flag": bool(flag)}


# ---------------------------------------------------------------- journal-entry tests (SA 240)
HOLIDAYS_FIXED = {(1, 26): "Republic Day", (8, 15): "Independence Day", (10, 2): "Gandhi Jayanti"}
CASH_PAY_LIMIT = 10000.0          # Sec 34(3), old 40A(3) (Rs 35,000 for goods transporters)
CASH_PAY_TRANSPORT = 35000.0
CASH_RECEIPT_LIMIT = 200000.0     # Sec 221, old 269ST
CASH_LOAN_LIMIT = 20000.0         # Sec 219 / 220, old 269SS / 269T


def is_round(x: float, unit: int = 10000, min_amt: float = 100000.0) -> bool:
    return abs(x) >= min_amt and abs(x) % unit == 0


def just_below(x: float, limit: float, band: float = 0.03) -> bool:
    return bool(limit) and limit * (1 - band) <= abs(x) < limit


def holiday(d: date, extra: dict | None = None) -> str:
    if d.weekday() == 6:
        return "Ravivar"
    if (d.month, d.day) in HOLIDAYS_FIXED:
        return HOLIDAYS_FIXED[(d.month, d.day)]
    if extra and d.isoformat() in extra:
        return extra[d.isoformat()]
    return ""


# ---------------------------------------------------------------- Benford's law (first digit)
BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def benford(amounts: list[float], min_amount: float = 10.0) -> dict:
    """First-digit test; MAD conformity bands (Nigrini): <=0.006 close, <=0.012 acceptable, <=0.015 marginal, above = not."""
    firsts = []
    for a in amounts:
        a = abs(float(a))
        if a >= min_amount:
            s = f"{a:.10e}"
            firsts.append(int(s[0]))
    n = len(firsts)
    if n < 300:
        return {"n": n, "ok": None, "note": "300 se kam entries: Benford test bharosemand nahi."}
    c = Counter(firsts)
    rows = []
    mad = 0.0
    for d in range(1, 10):
        actual = c.get(d, 0) / n
        exp = BENFORD[d]
        z = (abs(actual - exp) - 1 / (2 * n)) / math.sqrt(exp * (1 - exp) / n)
        rows.append({"digit": d, "actual_pct": round(actual * 100, 1), "expected_pct": round(exp * 100, 1), "z": round(max(0.0, z), 2)})
        mad += abs(actual - exp)
    mad /= 9
    band = "close" if mad <= 0.006 else "acceptable" if mad <= 0.012 else "marginal" if mad <= 0.015 else "nonconformity"
    spikes = [r["digit"] for r in rows if r["z"] > 1.96 and r["actual_pct"] > r["expected_pct"]]
    return {"n": n, "mad": round(mad, 4), "conformity": band, "ok": band in ("close", "acceptable"), "digits": rows, "spikes": spikes}


# ---------------------------------------------------------------- sampling (SA 530)
CONFIDENCE_FACTOR = {90: 2.31, 95: 3.0, 99: 4.61}     # Poisson factors, zero expected misstatement


def mus_interval(tolerable: float, confidence: int = 95) -> float:
    return tolerable / CONFIDENCE_FACTOR.get(confidence, 3.0)


def mus_select(items: list[tuple[str, float]], tolerable: float, confidence: int = 95, seed: int = 7) -> dict:
    """Monetary-unit sampling: every item at or above the interval is taken; the rest by a random start + interval."""
    interval = mus_interval(tolerable, confidence)
    if interval <= 0:
        raise ValueError("Tolerable misstatement chahiye.")
    rnd = random.Random(seed)
    start = rnd.uniform(0, interval)
    picked, key = [], []
    cum, nxt = 0.0, start
    for ref, amt in items:
        a = abs(float(amt))
        if a >= interval:
            key.append(ref)
            continue
        cum += a
        while nxt <= cum:
            if ref not in picked:
                picked.append(ref)
            nxt += interval
    pop = sum(abs(float(a)) for _r, a in items)
    return {"interval": round(interval), "start": round(start), "key_items": key, "sampled": picked, "population_value": round(pop),
            "size": len(key) + len(picked), "seed": seed, "confidence": confidence}


def random_select(refs: list[str], n: int, seed: int = 7) -> list[str]:
    rnd = random.Random(seed)
    refs = list(refs)
    return refs if n >= len(refs) else sorted(rnd.sample(refs, n), key=refs.index)


# ---------------------------------------------------------------- TDS (Income-tax Act 2025, Sec 393) - TY 2026-27
TDS = [
    # nature, words in ledger / narration, threshold (single, yearly), rate %, old section
    ("contractor", ("contract", "labour charges", "job work", "fabrication charges", "transport", "freight", "carriage", "catering", "advertis"),
     30000.0, 100000.0, 1.0, "194C"),
    ("professional", ("professional", "legal", "audit fee", "consultan", "architect", "doctor", "lawyer", "ca fees", "retainership"),
     0.0, 50000.0, 10.0, "194J(b)"),
    ("technical", ("technical", "software service", "maintenance contract", "amc", "call centre"), 0.0, 50000.0, 2.0, "194J(a)"),
    ("rent", ("rent",), 0.0, 600000.0, 10.0, "194-I"),
    ("commission", ("commission", "brokerage"), 0.0, 20000.0, 2.0, "194H"),
    ("interest", ("interest on loan", "interest paid", "interest on unsecured"), 0.0, 10000.0, 10.0, "194A"),
]


def tds_nature(text: str) -> tuple | None:
    t = f" {str(text or '').lower()} "
    for row in TDS:
        if any(w in t for w in row[1]):
            return row
    return None


# ---------------------------------------------------------------- applicability
def tax_audit(kind: str, turnover: float, cash_receipts_pct: float | None = None, cash_payments_pct: float | None = None,
              fy_start: int = 2025) -> dict:
    """Sec 63 (old 44AB). Business: Rs 1 crore, or Rs 10 crore when cash receipts and payments are each <= 5%.
    Profession: Rs 50 lakh gross receipts."""
    if kind == "profession":
        limit = 5e6
    else:
        low_cash = cash_receipts_pct is not None and cash_payments_pct is not None and cash_receipts_pct <= 5 and cash_payments_pct <= 5
        limit = 1e8 if low_cash else 1e7
    need = float(turnover) > limit
    form = "Form 26 (Sec 63)" if fy_start >= 2026 else ("Form 3CA + 3CD (accounts audited under another law) / 3CB + 3CD")
    due = date(fy_start + 1, 9, 30)
    note = ""
    if fy_start == 2025:
        due = date(2026, 10, 21)
        note = "CBDT Circular 07/2026 ne 30 Sep 2026 ko 21 Oct 2026 kiya."
    return {"required": need, "limit": limit, "form": form, "due": due.isoformat(), "note": note}


def caro(kind: str, paid_up_reserves: float, borrowings: float, revenue: float, is_holding_or_sub_of_public: bool = False,
         paid_up: float | None = None, on: date | None = None) -> dict:
    """CARO 2020 needed? Exempt: banks, insurers, Sec 8, OPC, small companies, and small private companies."""
    on = on or date.today()
    k = kind.lower()
    if k in ("bank", "insurance", "section8", "opc"):
        return {"applies": False, "why": f"{k} ko CARO lagu nahi."}
    if k not in ("private", "public"):
        return {"applies": False, "why": "CARO sirf companies par."}
    cap, turn = (10e7, 100e7) if on >= date(2025, 12, 1) else (4e7, 40e7)
    pu = paid_up if paid_up is not None else paid_up_reserves
    if k == "private" and not is_holding_or_sub_of_public and pu < cap and revenue < turn:
        return {"applies": False, "why": f"Small company (paid-up < Rs {cap / 1e7:g} cr, turnover < Rs {turn / 1e7:g} cr)."}
    if k == "private" and not is_holding_or_sub_of_public and paid_up_reserves < 1e7 and borrowings < 1e7 and revenue < 1e8:
        return {"applies": False, "why": "Chhoti private company (capital + reserves, udhaar < 1 cr, revenue < 10 cr)."}
    return {"applies": True, "why": "CARO 2020 ke 21 clause par report."}


AUDIT_TRAIL = ["Software mein audit trail (edit log) ka feature hai", "Saal bhar sab entries par chalu raha (migration se pehle bhi)",
               "Band / tamper nahi hua (backdated / delete entries ki jaanch)", "Log 8 saal sambhal kar rakha (export, India server backup)",
               "Cloud software ho to vendor ka SOC 2 / ISO report (SA 402)"]

GOING_CONCERN = [("net_worth_negative", "Net worth minus mein"), ("current_ratio_below_1", "Current ratio 1 se kam"),
                 ("losses", "Lagaataar ghata"), ("loan_overdue", "Loan ki kist / byaaj late"), ("debtors_stuck", "Debtors 180+ din")]
