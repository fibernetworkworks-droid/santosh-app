"""GST law and portal rules Hoola checks against (researched Oct 2026; every number here has a source in CLAUDE.md v0.93).

Pure functions only: periods, due dates, late fee, interest, tax split, rate / HSN / e-invoice checks, ITC set-off.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from ..india.money import STATE_CODES, gstin_ok

# ---------------------------------------------------------------- rates (GST 2.0 from 22-09-2025: 5 / 18 / 40 + special)
RATES = (0.0, 0.1, 0.25, 1.0, 1.5, 3.0, 5.0, 6.0, 7.5, 12.0, 18.0, 28.0, 40.0)
GST2_DATE = date(2025, 9, 22)
OLD_SLABS = (12.0, 28.0)              # most goods left these slabs on 22-09-2025 (28% stays for tobacco / pan masala)
B2CL_LIMIT = 100000.0                 # inter-state B2C invoice above Rs 1 lakh is reported invoice-wise (from Aug 2024)
EINV_LIMIT = 5e7                      # e-invoice (IRN) for B2B when AATO in any FY since 2017-18 > Rs 5 crore
EINV_30DAY = 1e8                      # AATO >= Rs 10 crore: report to IRP within 30 days (from 1 Apr 2025)
QRMP_LIMIT = 5e7                      # QRMP only up to Rs 5 crore AATO
HSN6_LIMIT = 5e7                      # 6-digit HSN above Rs 5 crore AATO, else 4
GSTR9_LIMIT = 2e7                     # annual return optional up to Rs 2 crore (Notfn 15/2025-CT, FY 2024-25 onwards)
GSTR9C_LIMIT = 5e7                    # GSTR-9C above Rs 5 crore
RULE37_DAYS = 180                     # unpaid supplier after 180 days -> reverse ITC (with interest), re-avail on payment
TIME_BAR_YEARS = 3                    # returns can't be filed 3 years after their due date (enforced from July 2025)

# QRMP GSTR-3B: 22nd for these states, 24th for the rest (CGST Notfn 1/2021 groups)
GROUP_22 = {"22", "23", "24", "27", "29", "30", "32", "33", "36", "37", "26", "25", "34", "35", "31"}

UQC = ("NOS", "PCS", "KGS", "GMS", "LTR", "MLT", "MTR", "SQM", "SQF", "BOX", "PAC", "SET", "PRS", "DOZ", "TON", "QTL",
       "BAG", "BTL", "CAN", "CTN", "UNT", "OTH", "NA")

# notice form -> (what it is, reply form, days to reply)
NOTICES = {
    "ASMT-10": ("Return scrutiny: discrepancies found (Sec 61)", "ASMT-11", 30),
    "DRC-01": ("Show cause notice: demand (Sec 73 / 74 / 74A)", "DRC-06", 30),
    "DRC-01A": ("Pre-SCN intimation: pay or explain (Rule 142(1A))", "DRC-01A Part B / DRC-03", 30),
    "DRC-01B": ("GSTR-1 liability more than GSTR-3B (Rule 88C)", "DRC-01B Part B", 7),
    "DRC-01C": ("ITC in GSTR-3B more than GSTR-2B (Rule 88D)", "DRC-01C Part B", 7),
    "GSTR-3A": ("Return not filed: default notice (Sec 46)", "File the pending return", 15),
    "REG-03": ("Registration application: clarification needed", "REG-04", 7),
    "REG-17": ("Show cause: registration cancellation", "REG-18", 7),
    "REG-31": ("Registration suspended: intimation (Rule 21A)", "Reply on portal / file pending returns", 30),
    "CMP-05": ("Composition eligibility doubted", "CMP-06", 15),
    "ADT-01": ("Departmental audit (Sec 65)", "Documents at audit", 15),
    "RFD-08": ("Refund: show cause for rejection", "RFD-09", 15),
    "OTHER": ("Other notice", "Reply as asked", 15),
}

BLOCKED_17_5 = ("motor vehicle", "car ", "vehicle insurance", "food", "beverage", "catering", "restaurant", "club",
                "membership", "health", "fitness", "beauty", "cosmetic", "life insurance", "health insurance", "travel benefit",
                "leave travel", "gift", "personal", "construction of building", "works contract")


# ---------------------------------------------------------------- periods ("2026-10" = October 2026)
def period_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def parse_period(p: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", str(p or "").strip())
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
    else:
        m = re.fullmatch(r"(\d{1,2})[/-](\d{4})", str(p or "").strip()) or re.fullmatch(r"(\d{2})(\d{4})", str(p or "").strip())
        if not m:
            raise ValueError(f"Period samajh nahi aaya: {p!r} (jaise 2026-10)")
        mo, y = int(m.group(1)), int(m.group(2))
    if not 1 <= mo <= 12:
        raise ValueError(f"Mahina galat: {p!r}")
    return y, mo


def norm_period(p: str) -> str:
    y, m = parse_period(p)
    return f"{y:04d}-{m:02d}"


def add_months(y: int, m: int, k: int) -> tuple[int, int]:
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1


def quarter_months(p: str) -> list[str]:
    """The 3 months of the quarter that ends with (or contains) period p (Indian FY quarters Apr-Jun, Jul-Sep...)."""
    y, m = parse_period(p)
    q_end = {1: 3, 2: 3, 3: 3, 4: 6, 5: 6, 6: 6, 7: 9, 8: 9, 9: 9, 10: 12, 11: 12, 12: 12}[m]
    return [f"{y:04d}-{mm:02d}" for mm in (q_end - 2, q_end - 1, q_end)]


def is_quarter_end(p: str) -> bool:
    return parse_period(p)[1] in (3, 6, 9, 12)


def fy_of(p: str) -> str:
    y, m = parse_period(p)
    start = y if m >= 4 else y - 1
    return f"{start}-{str(start + 1)[2:]}"


def fp(p: str) -> str:
    """Portal 'fp' / 'ret_period' format MMYYYY."""
    y, m = parse_period(p)
    return f"{m:02d}{y:04d}"


def nice_period(p: str) -> str:
    y, m = parse_period(p)
    return ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[m - 1] + f" {y}"


# ---------------------------------------------------------------- due dates
def _d(y: int, m: int, day: int) -> date:
    return date(y, m, day)


def due_date(kind: str, period: str, scheme: str = "monthly", state: str = "27") -> date:
    """kind: gstr1 | iff | gstr3b | pmt06 | cmp08 | gstr4 | gstr9 | itc_last. period = the month (quarter end for QRMP)."""
    y, m = parse_period(period)
    ny, nm = add_months(y, m, 1)
    if kind == "gstr1":
        return _d(ny, nm, 13 if scheme == "qrmp" else 11)
    if kind == "iff":
        return _d(ny, nm, 13)
    if kind == "gstr3b":
        if scheme == "qrmp":
            return _d(ny, nm, 22 if state in GROUP_22 else 24)
        return _d(ny, nm, 20)
    if kind == "pmt06":
        return _d(ny, nm, 25)
    if kind == "cmp08":
        return _d(ny, nm, 18)
    fy_start = y if m >= 4 else y - 1
    if kind == "gstr4":
        return _d(fy_start + 1, 4, 30)
    if kind == "gstr9":
        return _d(fy_start + 1, 12, 31)
    if kind == "itc_last":
        return _d(fy_start + 1, 11, 30)
    raise ValueError(kind)


def time_barred(kind: str, period: str, scheme: str, state: str, on: date) -> bool:
    d = due_date(kind, period, scheme, state)
    try:
        bar = d.replace(year=d.year + TIME_BAR_YEARS)
    except ValueError:
        bar = d + timedelta(days=365 * TIME_BAR_YEARS)
    return on > bar


def obligations(period: str, scheme: str, state: str) -> list[dict]:
    """What is due for this month: [{kind, label, due}]."""
    out = []
    if scheme == "composition":
        if is_quarter_end(period):
            out.append({"kind": "cmp08", "label": "CMP-08 (tax payment)", "due": due_date("cmp08", period, scheme, state)})
        return out
    if scheme == "qrmp":
        if is_quarter_end(period):
            out += [{"kind": "gstr1", "label": "GSTR-1 (quarter)", "due": due_date("gstr1", period, scheme, state)},
                    {"kind": "gstr3b", "label": "GSTR-3B (quarter)", "due": due_date("gstr3b", period, scheme, state)}]
        else:
            out += [{"kind": "iff", "label": "IFF (B2B invoices, optional)", "due": due_date("iff", period, scheme, state)},
                    {"kind": "pmt06", "label": "PMT-06 (monthly tax payment)", "due": due_date("pmt06", period, scheme, state)}]
        return out
    return [{"kind": "gstr1", "label": "GSTR-1", "due": due_date("gstr1", period, scheme, state)},
            {"kind": "gstr3b", "label": "GSTR-3B", "due": due_date("gstr3b", period, scheme, state)}]


# ---------------------------------------------------------------- late fee + interest
def late_fee(kind: str, days: int, nil: bool = False, aato: float = 0.0, turnover: float = 0.0) -> float:
    """Total late fee (CGST + SGST) for `days` late. GSTR-1 / 3B: Rs 50 a day (Rs 20 nil), capped by AATO.
    GSTR-9: Rs 50 / 100 / 200 a day by AATO, capped at 0.04% / 0.04% / 0.5% of turnover in the state."""
    if days <= 0:
        return 0.0
    if kind in ("gstr1", "gstr3b", "iff", "gstr4", "cmp08"):
        if kind in ("iff", "cmp08"):
            return 0.0
        if nil:
            return float(min(days * 20, 500))
        cap = 2000 if aato <= 1.5e7 else (5000 if aato <= 5e7 else 10000)
        return float(min(days * 50, cap))
    if kind == "gstr9":
        if aato <= 5e7:
            per, pct = 50, 0.0004
        elif aato <= 2e8:
            per, pct = 100, 0.0004
        else:
            per, pct = 200, 0.005
        cap = turnover * pct if turnover else days * per
        return float(round(min(days * per, cap), 2))
    return 0.0


def interest(cash_tax: float, days: int, rate: float = 18.0) -> float:
    """Sec 50: 18% a year on tax paid late in cash (24% on ITC wrongly availed and used)."""
    if days <= 0 or cash_tax <= 0:
        return 0.0
    return round(cash_tax * rate / 100 * days / 365, 0)


# ---------------------------------------------------------------- tax on a line
def intra(supplier_state: str, pos: str, sez: bool = False) -> bool:
    return not sez and str(supplier_state).zfill(2) == str(pos).zfill(2)


def split_tax(txval: float, rate: float, is_intra: bool, cess: float = 0.0) -> dict:
    t = round(txval * rate / 100, 2)
    if is_intra:
        h = round(t / 2, 2)
        return {"igst": 0.0, "cgst": h, "sgst": round(t - h, 2), "cess": cess}
    return {"igst": t, "cgst": 0.0, "sgst": 0.0, "cess": cess}


def pos_code(v) -> str:
    """'27', 27, 'Maharashtra', '27-Maharashtra' -> '27'."""
    s = str(v or "").strip()
    m = re.match(r"^(\d{1,2})", s)
    if m:
        return m.group(1).zfill(2)
    low = s.lower()
    for k, name in STATE_CODES.items():
        if name.lower() == low or name.lower().startswith(low) and len(low) >= 4:
            return k
    return ""


def hsn_digits_needed(aato: float) -> int:
    return 6 if aato > HSN6_LIMIT else 4


def is_service_hsn(h: str) -> bool:
    return str(h or "").startswith("99")


def check_line(doc_date: date, rate: float, hsn: str, aato: float, txval: float, igst: float, cgst: float, sgst: float,
               is_intra: bool) -> list[str]:
    """Problems on one invoice line (empty list = fine)."""
    p: list[str] = []
    if rate not in RATES:
        p.append(f"Rate {rate:g}% GST mein nahi hai.")
    elif rate in OLD_SLABS and doc_date >= GST2_DATE:
        p.append(f"{rate:g}% purana slab: 22-09-2025 se zyaadatar cheezein 5% / 18% / 40% mein gayi (tobacco jaise kuch hi 28% par).")
    h = re.sub(r"\D", "", str(hsn or ""))
    need = hsn_digits_needed(aato)
    if not h:
        p.append(f"HSN / SAC nahi hai ({need} digit chahiye).")
    elif len(h) < need:
        p.append(f"HSN {h}: kam se kam {need} digit chahiye.")
    exp = split_tax(txval, rate, is_intra)
    if is_intra and igst > 0.5:
        p.append("State ke andar ki sale par IGST laga hai: CGST + SGST hona chahiye.")
    if not is_intra and (cgst > 0.5 or sgst > 0.5):
        p.append("Doosre state ki sale par CGST / SGST laga hai: IGST hona chahiye.")
    got = igst + cgst + sgst
    if txval and abs(got - (exp["igst"] + exp["cgst"] + exp["sgst"])) > max(1.0, 0.005 * got):
        p.append(f"Tax {got:.2f} hai, {rate:g}% par {exp['igst'] + exp['cgst'] + exp['sgst']:.2f} hona chahiye.")
    return p


def blocked_hint(text: str) -> bool:
    t = f" {str(text or '').lower()} "
    return any(w in t for w in BLOCKED_17_5)


# ---------------------------------------------------------------- ITC set-off (Sec 49 / 49A / 49B, Rule 88A)
def set_off(liab: dict, credit: dict) -> dict:
    """Least cash, legal order: IGST credit first on IGST, rest on CGST / SGST gaps; CGST credit on CGST then IGST;
    SGST credit on SGST then IGST; CGST never pays SGST (nor the reverse); cess credit only cess."""
    L = {k: max(0.0, float(liab.get(k) or 0)) for k in ("igst", "cgst", "sgst", "cess")}
    C = {k: max(0.0, float(credit.get(k) or 0)) for k in ("igst", "cgst", "sgst", "cess")}
    used = {f"{a}->{b}": 0.0 for a in ("igst", "cgst", "sgst") for b in ("igst", "cgst", "sgst")}
    used["cess->cess"] = 0.0

    def use(a: str, b: str, amt: float) -> None:
        amt = round(max(0.0, min(amt, C[a], L[b])), 2)
        C[a] -= amt
        L[b] -= amt
        used[f"{a}->{b}"] += amt

    use("igst", "igst", L["igst"])
    gap_c, gap_s = max(0.0, L["cgst"] - C["cgst"]), max(0.0, L["sgst"] - C["sgst"])
    use("igst", "cgst", gap_c)
    use("igst", "sgst", gap_s)
    use("igst", "cgst", L["cgst"])
    use("igst", "sgst", L["sgst"])
    use("cgst", "cgst", L["cgst"])
    use("sgst", "sgst", L["sgst"])
    use("cgst", "igst", L["igst"])
    use("sgst", "igst", L["igst"])
    use("cess", "cess", L["cess"])
    return {"cash": {k: round(v, 2) for k, v in L.items()}, "used": {k: round(v, 2) for k, v in used.items() if v},
            "credit_left": {k: round(v, 2) for k, v in C.items()}, "cash_total": round(sum(L.values()), 2)}


def valid_gstin(g: str) -> bool:
    return gstin_ok(g)
