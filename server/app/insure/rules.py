"""Insurance rules Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.98). Pure functions.

IRDAI (2024 master circulars): free-look 30 days; grace period 15 days for monthly premiums, 30 days for others;
death claims settled in 15 days (45 if investigated), interest at bank rate + 2% when late; health cashless authorisation
within 1 hour, discharge within 3 hours, reimbursement within 15 days; need analysis mandatory for savings / annuity
products; a Customer Information Sheet with every policy. Revival of a lapsed policy: usually up to 5 years for
traditional plans and 3 years for ULIPs (the policy document decides). GST: individual life and health premiums exempt
from 22 Sep 2025 (group policies still taxed). Income-tax Act 2025 Sec 126 (old 80D): health premium Rs 25,000 for
self / family + Rs 25,000 for parents (Rs 50,000 each for senior citizens), check-ups up to Rs 5,000 inside; old regime
only. Needs-based cover numbers below are rules of thumb, not advice.
"""
from __future__ import annotations

from datetime import date, timedelta

MODES = {"monthly": 1, "quarterly": 3, "half_yearly": 6, "yearly": 12, "single": 0}
FREE_LOOK_DAYS = 30
TYPES = {"term": "Term life", "endowment": "Endowment / money-back", "ulip": "ULIP", "pension": "Pension / annuity",
         "health": "Health", "topup": "Health super top-up", "pa": "Personal accident", "critical": "Critical illness",
         "motor": "Motor", "home": "Home / shop", "travel": "Travel", "other": "Other"}
LIFE = {"term", "endowment", "ulip", "pension"}
SAVINGS = {"endowment", "ulip", "pension"}
CLAIM_DAYS = {"death": 15, "death_investigated": 45, "health_cashless": 0, "health_reimbursement": 15}


def mode_of(v: str) -> str:
    s = str(v or "").lower().replace("-", "_").replace(" ", "_")
    return {"annual": "yearly", "year": "yearly", "yly": "yearly", "hly": "half_yearly", "halfyearly": "half_yearly",
            "qly": "quarterly", "quarter": "quarterly", "mly": "monthly", "month": "monthly", "ecs": "monthly",
            "single_premium": "single"}.get(s, s if s in MODES else "yearly")


def grace_days(mode: str) -> int:
    return 15 if mode_of(mode) == "monthly" else 30


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    from calendar import monthrange
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def next_due_after(start: date, mode: str, on: date) -> date | None:
    k = MODES.get(mode_of(mode), 12)
    if k == 0:
        return None
    d = start
    while d <= on - timedelta(days=0):
        d = add_months(d, k)
    return d


def revival_years(ptype: str) -> int:
    return 3 if ptype == "ulip" else 5


def premium_state(due: date | None, mode: str, ptype: str, on: date) -> dict:
    """due / grace / lapsed / revival-over for a premium due date."""
    if not due:
        return {"state": "paid_up", "label": "Single premium / paid-up"}
    g = grace_days(mode)
    grace_end = due + timedelta(days=g)
    rev_end = add_months(due, 12 * revival_years(ptype))
    days = (due - on).days
    if days >= 0:
        return {"state": "due", "days": days, "due": due.isoformat(), "grace_end": grace_end.isoformat(), "label": f"due in {days} days"}
    if on <= grace_end:
        return {"state": "grace", "days_left": (grace_end - on).days, "due": due.isoformat(), "grace_end": grace_end.isoformat(),
                "label": f"Grace period: {(grace_end - on).days} days left"}
    if on <= rev_end:
        return {"state": "lapsed", "due": due.isoformat(), "revive_by": rev_end.isoformat(),
                "label": f"Lapsed: can be revived until {rev_end.isoformat()}"}
    return {"state": "lapsed_final", "due": due.isoformat(), "label": "Revival period has ended"}


def age_on(dob: date | None, on: date) -> int | None:
    if not dob:
        return None
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def life_cover_need(income: float, age: int | None, liabilities: float = 0.0, goals: float = 0.0, existing: float = 0.0,
                    savings: float = 0.0) -> dict:
    """Income replacement (rule of thumb): 15x yearly income below 40, 12x to 50, 10x after, + loans + goals - existing
    cover - savings."""
    a = age or 35
    mult = 15 if a < 40 else 12 if a < 50 else 10 if a < 60 else 5
    need = income * mult + liabilities + goals
    gap = max(0.0, need - existing - savings)
    return {"multiple": mult, "need": round(need), "existing": round(existing), "gap": round(gap)}


def health_cover_need(members: int, metro: bool, eldest_age: int | None, existing: float = 0.0) -> dict:
    """Family floater rule of thumb: Rs 10 lakh (metro) / 5 lakh base, +Rs 2.5 lakh per extra member, +50% if anyone 55+."""
    base = 1000000 if metro else 500000
    need = base + max(0, members - 2) * 250000
    if eldest_age and eldest_age >= 55:
        need *= 1.5
    return {"need": round(need), "existing": round(existing), "gap": round(max(0.0, need - existing)),
            "tip": "For a large cover, a base plan plus a super top-up costs less."}


def gst_on(ptype: str, group: bool = False) -> float:
    """GST % on the premium: individual life / health exempt from 22 Sep 2025; group and general insurance 18%."""
    if group:
        return 18.0
    if ptype in LIFE or ptype in ("health", "topup", "critical", "pa"):
        return 0.0
    return 18.0


def health_deduction(self_premium: float, parents_premium: float, self_senior: bool = False, parents_senior: bool = False) -> dict:
    """Sec 126 (old 80D), old regime only."""
    s_cap = 50000 if self_senior else 25000
    p_cap = 50000 if parents_senior else 25000
    a, b = min(self_premium, s_cap), min(parents_premium, p_cap)
    return {"self": round(a), "parents": round(b), "total": round(a + b), "note": "Only in the old tax regime; there is no such deduction in the new regime."}


PROPOSAL_DOCS = {
    "common": ["PAN", "Aadhaar / address proof (KYC, CKYC number if available)", "Photo", "Bank details (for NACH / auto-debit)",
               "Nominee's name, relationship, date of birth", "Health / habit declaration: the customer fills it in truthfully"],
    "term": ["Income proof (ITR / salary slip) for a large cover", "Medical test (the insurer will say, based on age and cover)"],
    "health": ["Full details of existing illnesses (hiding them can block a claim)", "Previous policy (if porting)"],
    "motor": ["RC", "Previous policy / NCB proof", "Driving licence"],
    "savings": ["Need analysis (required by IRDAI)", "Show the benefit illustration to the customer"],
}

CLAIM_DOCS = {
    "death": ["Claim form (nominee)", "Death certificate", "Policy document / number", "Nominee KYC + bank (cancelled cheque)",
              "Hospital / medical record (for illness) or FIR + post-mortem (for an accident)"],
    "health_cashless": ["Health card / policy number", "Hospital's pre-authorisation form", "Patient's ID", "Doctor's note"],
    "health_reimbursement": ["Claim form", "Discharge summary", "Original bill + payment receipt", "Test reports", "Medicine bills + prescription",
                             "Bank details (cancelled cheque)", "KYC"],
    "motor": ["Claim form", "RC + driving licence", "FIR (theft / third-party damage)", "Photo of the vehicle", "Repair estimate / bill"],
    "other": ["Claim form", "Policy number", "Documents / photos of the damage", "KYC + bank"],
}

NEVER = ("Hoola never takes or pays a premium: the customer pays the insurer directly (insurer's link / app / office).",
         "Hoola never signs the proposal form or fills in the health declaration in place of the customer.",
         "'Guaranteed return' only when the brochure says guaranteed.",
         "Tell every customer about the 30-day free-look period.")
