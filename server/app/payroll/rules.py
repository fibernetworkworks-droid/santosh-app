"""Indian payroll law Hoola checks against (researched 22 Oct 2026; sources in CLAUDE.md v0.94). Pure functions only.

Code on Wages 2019 (in force 21 Nov 2025): "wages" = basic + DA + retaining allowance, and if the excluded parts (HRA,
conveyance, overtime, commission...) are more than half of the pay, the excess is added back -> wages = max(basic + DA,
half of total pay). PF / gratuity / bonus are worked on these wages. Wages by the 7th of the next month; dues of a person
who leaves within 2 working days; overtime at twice the ordinary rate; deductions at most 50% of wages.
EPF (S.O. 5109(E), 17 Sep 2026): wage ceiling Rs 25,000 (was 15,000; September 2026 split 16 / 14 days), employee 12%,
employer 12% = EPS 8.33% (only members eligible for EPS) + EPF 3.67%, EDLI 0.5%, admin 0.5% (min Rs 500). ECR by 15th.
ESIC: wages up to Rs 21,000 (covered for the whole contribution period Apr-Sep / Oct-Mar), employee 0.75% (nil if
average daily wage <= Rs 176), employer 3.25%, rounded up to the rupee, by the 15th.
Income-tax Act 2025 (from 1 Apr 2026): salary TDS under Sec 392 (was 192), deposit by the 7th (30 Apr for March),
quarterly statement Form 138 (was 24Q), certificate Form 130 (was Form 16) by 15 June. New regime default: slabs
4 / 8 / 12 / 16 / 20 / 24 lakh, standard deduction Rs 75,000, no tax up to Rs 12 lakh taxable (rebate, marginal relief),
4% cess. Old regime: 2.5 / 5 / 10 lakh, standard deduction Rs 50,000, rebate up to Rs 5 lakh.
"""
from __future__ import annotations

import calendar
import math
import re
from datetime import date, timedelta

# ---------------------------------------------------------------- periods ("2026-10")
def parse_period(p: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", str(p or "").strip())
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
    else:
        m = re.fullmatch(r"(\d{1,2})[/-](\d{4})", str(p or "").strip())
        if not m:
            raise ValueError(f"Mahina samajh nahi aaya: {p!r} (jaise 2026-10)")
        mo, y = int(m.group(1)), int(m.group(2))
    if not 1 <= mo <= 12:
        raise ValueError(f"Mahina galat: {p!r}")
    return y, mo


def norm_period(p: str) -> str:
    y, m = parse_period(p)
    return f"{y:04d}-{m:02d}"


def days_in(p: str) -> int:
    y, m = parse_period(p)
    return calendar.monthrange(y, m)[1]


def fy_of(p: str) -> str:
    y, m = parse_period(p)
    s = y if m >= 4 else y - 1
    return f"{s}-{str(s + 1)[2:]}"


def fy_months(p: str) -> list[str]:
    y, m = parse_period(p)
    s = y if m >= 4 else y - 1
    return [f"{s if mm >= 4 else s + 1:04d}-{mm:02d}" for mm in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]


def months_left_in_fy(p: str) -> int:
    """Including this month: April -> 12, March -> 1."""
    return 12 - fy_months(p).index(norm_period(p))


def nice(p: str) -> str:
    y, m = parse_period(p)
    return ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[m - 1] + f" {y}"


def next_month(p: str) -> tuple[int, int]:
    y, m = parse_period(p)
    return (y + 1, 1) if m == 12 else (y, m + 1)


def rnd(x: float) -> int:
    """Half-up to the rupee (EPFO convention)."""
    return int(math.floor(float(x) + 0.5 + 1e-9))


# ---------------------------------------------------------------- wages (Code on Wages)
def code_wages(basic_da: float, total_pay: float) -> float:
    """Wages per the Code: basic + DA, but never less than half of the total pay."""
    return round(max(float(basic_da), float(total_pay) / 2.0), 2)


def ot_amount(wages: float, hours: float, rate: float = 2.0) -> float:
    """Overtime at twice the ordinary hourly rate (wages / 26 days / 8 hours)."""
    if hours <= 0:
        return 0.0
    return round(float(wages) / 26 / 8 * rate * float(hours), 2)


# ---------------------------------------------------------------- EPF
PF_NEW_CEILING_FROM = date(2026, 9, 17)


def pf_ceiling(p: str) -> float:
    y, m = parse_period(p)
    return 25000.0 if (y, m) >= (2026, 10) else (15000.0 if (y, m) <= (2026, 8) else 0.0)   # 0 = September split


def pf_capped(p: str, wage: float) -> float:
    """PF wages after the ceiling. September 2026: days 1-16 at 15,000 and 17-30 at 25,000 (each on a 30-day basis)."""
    c = pf_ceiling(p)
    if c:
        return min(float(wage), c)
    return min(wage * 16 / 30, 15000 * 16 / 30) + min(wage * 14 / 30, 25000 * 14 / 30)


def pf(p: str, wage: float, eps_member: bool = True, on_full: bool = False) -> dict:
    """Contributions on this month's PF wages. on_full: both sides on full wages above the ceiling (voluntary, with
    the employer's consent); EPS always stays on the capped wages."""
    capped = pf_capped(p, wage)
    pfw = float(wage) if on_full else capped
    ee = rnd(pfw * 0.12)
    eps_w = capped if eps_member else 0.0
    eps = rnd(eps_w * 0.0833) if eps_member else 0
    er_total = rnd(pfw * 0.12)
    return {"pf_wages": rnd(pfw), "eps_wages": rnd(eps_w), "edli_wages": rnd(capped), "ee": ee, "eps": eps,
            "er_epf": max(0, er_total - eps), "edli": rnd(capped * 0.005), "admin": rnd(pfw * 0.005)}


# ---------------------------------------------------------------- ESIC
ESI_CEILING = 21000.0
ESI_FREE_DAILY = 176.0


def esi_period_start(p: str) -> str:
    y, m = parse_period(p)
    if 4 <= m <= 9:
        return f"{y:04d}-04"
    return f"{y if m >= 10 else y - 1:04d}-10"


def esi(gross: float, days_paid: float) -> dict:
    ee = 0 if days_paid and gross / max(days_paid, 1) <= ESI_FREE_DAILY else int(math.ceil(gross * 0.0075 - 1e-9))
    return {"esi_wages": rnd(gross), "ee": ee, "er": int(math.ceil(gross * 0.0325 - 1e-9))}


# ---------------------------------------------------------------- Professional tax (monthly gross; state rules)
PT_STATES = {"27": "Maharashtra", "29": "Karnataka", "19": "West Bengal", "24": "Gujarat", "36": "Telangana",
             "37": "Andhra Pradesh", "23": "Madhya Pradesh", "21": "Odisha", "33": "Tamil Nadu", "32": "Kerala"}
STATE_CODE = {"maharashtra": "27", "karnataka": "29", "west bengal": "19", "gujarat": "24", "telangana": "36",
              "andhra pradesh": "37", "madhya pradesh": "23", "odisha": "21", "tamil nadu": "33", "kerala": "32",
              "delhi": "07", "uttar pradesh": "09", "rajasthan": "08", "haryana": "06", "punjab": "03", "bihar": "10",
              "goa": "30", "assam": "18", "jharkhand": "20", "chhattisgarh": "22", "uttarakhand": "05", "himachal pradesh": "02"}


def state_code(v: str) -> str:
    s = str(v or "").strip().lower()
    if re.fullmatch(r"\d{1,2}", s):
        return s.zfill(2)
    return STATE_CODE.get(s, "")


def _band(x: float, bands: list[tuple[float, int]]) -> int:
    for upto, amt in bands:
        if x <= upto:
            return amt
    return bands[-1][1]


def pt(state: str, gross: float, month: int, gender: str = "", half_year_gross: float | None = None) -> int:
    """Professional tax this month. Tamil Nadu / Kerala collect half-yearly (in September and March)."""
    g = float(gross)
    s = state_code(state)
    if s == "27":                                               # Maharashtra (women up to 25,000 exempt from 1 Apr 2023)
        if str(gender).lower().startswith("f") and g <= 25000:
            return 0
        if g <= 7500:
            return 0
        if g <= 10000:
            return 175
        return 300 if month == 2 else 200
    if s == "29":
        return _band(g, [(25000, 0), (41999.99, 150), (float("inf"), 200)])
    if s == "19":
        return _band(g, [(10000, 0), (15000, 110), (25000, 130), (40000, 150), (float("inf"), 200)])
    if s == "24":
        return _band(g, [(5999.99, 0), (8999.99, 80), (11999.99, 150), (float("inf"), 200)])
    if s in ("36", "37"):
        return _band(g, [(15000, 0), (20000, 150), (float("inf"), 200)])
    if s == "23":
        return _band(g, [(18750, 0), (25000, 125), (33333, 167), (float("inf"), 208)])
    if s == "21":
        return _band(g, [(13304, 0), (25000, 125), (41666, 167), (float("inf"), 208)])
    if s in ("33", "32"):
        if month not in (9, 3):
            return 0
        h = half_year_gross if half_year_gross is not None else g * 6
        if s == "33":
            return _band(h, [(21000, 0), (30000, 135), (45000, 315), (60000, 690), (75000, 1025), (float("inf"), 1250)])
        return _band(h, [(11999, 0), (17999, 120), (29999, 180), (44999, 300), (59999, 450), (74999, 600), (99999, 750),
                         (124999, 1000), (float("inf"), 1250)])
    return 0


# ---------------------------------------------------------------- income tax on salary (Sec 392, Income-tax Act 2025)
NEW_SLABS = [(400000, 0.0), (800000, 0.05), (1200000, 0.10), (1600000, 0.15), (2000000, 0.20), (2400000, 0.25), (float("inf"), 0.30)]
OLD_SLABS = [(250000, 0.0), (500000, 0.05), (1000000, 0.20), (float("inf"), 0.30)]
STD_DED = {"new": 75000.0, "old": 50000.0}


def _slab_tax(ti: float, slabs) -> float:
    tax, prev = 0.0, 0.0
    for upto, r in slabs:
        if ti > prev:
            tax += (min(ti, upto) - prev) * r
        prev = upto
    return tax


def annual_tax(taxable: float, regime: str = "new") -> dict:
    ti = max(0.0, float(taxable))
    if regime == "old":
        base = _slab_tax(ti, OLD_SLABS)
        if ti <= 500000:
            base = 0.0
    else:
        base = _slab_tax(ti, NEW_SLABS)
        if ti <= 1200000:
            base = 0.0
        else:
            base = min(base, ti - 1200000)                       # marginal relief just above 12 lakh
    sur_rate = 0.0
    for lim, r in ((5e7 if regime == "old" else float("inf"), 0.37), (2e7, 0.25), (1e7, 0.15), (5e6, 0.10)):
        if ti > lim:
            sur_rate = r if not (regime == "new" and r > 0.25) else 0.25
            break
    sur = base * sur_rate
    total = (base + sur) * 1.04
    return {"taxable": round(ti), "tax": round(base), "surcharge": round(sur), "cess": round((base + sur) * 0.04), "total": round(total)}


def monthly_tds(projected_gross: float, regime: str, deductions: float, tds_so_far: float, months_left: int,
                other_income: float = 0.0, pt_year: float = 0.0) -> dict:
    """Spread the year's tax over the months left (Sec 392 asks for an even estimate of the year's income)."""
    taxable = projected_gross + other_income - STD_DED.get(regime, 75000.0) - (deductions if regime == "old" else 0.0) \
        - (pt_year if regime == "old" else 0.0)
    t = annual_tax(taxable, regime)
    left = max(0.0, t["total"] - tds_so_far)
    return {**t, "this_month": rnd(left / max(1, months_left))}


# ---------------------------------------------------------------- bonus / gratuity / F&F
BONUS_ELIGIBLE = 21000.0
BONUS_CALC = 7000.0
GRATUITY_MAX = 2000000.0


def bonus(monthly_wages: list[float], min_wage: float = 0.0, rate: float = 8.33) -> float:
    """Statutory bonus on wages up to Rs 21,000 a month, worked on Rs 7,000 or the minimum wage (higher), 8.33%-20%."""
    base = max(BONUS_CALC, float(min_wage or 0))
    return round(sum(min(w, base) for w in monthly_wages if w <= BONUS_ELIGIBLE) * max(8.33, min(rate, 20.0)) / 100, 0)


def service_years(doj: date, dol: date) -> int:
    days = (dol - doj).days
    yrs, rem = divmod(days, 365)
    return yrs + (1 if rem >= 183 else 0)          # more than 6 months counts as a year


def gratuity(last_wages: float, doj: date, dol: date, fixed_term: bool = False, death_or_disability: bool = False) -> dict:
    yrs_exact = (dol - doj).days / 365
    need = 1 if fixed_term else 5
    if yrs_exact < need and not death_or_disability:
        return {"eligible": False, "years": round(yrs_exact, 2), "amount": 0,
                "why": f"{need} saal ki naukri chahiye ({'fixed-term' if fixed_term else 'regular'})."}
    yrs = service_years(doj, dol)
    amt = min(GRATUITY_MAX, round(float(last_wages) * 15 / 26 * yrs))
    return {"eligible": True, "years": yrs, "amount": amt}


def leave_encashment(wages: float, days: float) -> float:
    return round(float(wages) / 26 * float(days), 0)


def working_days_after(d: date, n: int) -> date:
    x = d
    while n > 0:
        x += timedelta(days=1)
        if x.weekday() < 6:
            n -= 1
    return x


# ---------------------------------------------------------------- due dates
def dues(period: str, pf_on: bool = True, esi_on: bool = True) -> list[dict]:
    """What falls due because of this month's payroll."""
    ny, nm = next_month(period)
    y, m = parse_period(period)
    out = [{"kind": "salary", "label": "Salary dena (Code on Wages: 7 tareekh tak)", "due": date(ny, nm, 7)}]
    if pf_on:
        out.append({"kind": "pf", "label": "PF ECR + challan", "due": date(ny, nm, 15)})
    if esi_on:
        out.append({"kind": "esi", "label": "ESIC contribution", "due": date(ny, nm, 15)})
    out.append({"kind": "tds", "label": "TDS jama (Sec 392)", "due": date(ny, 4, 30) if m == 3 else date(ny, nm, 7)})
    if m in (6, 9, 12, 3):
        qd = {6: date(y, 7, 31), 9: date(y, 10, 31), 12: date(y + 1, 1, 31), 3: date(y, 5, 31)}[m]
        out.append({"kind": "form138", "label": "TDS statement Form 138 (salary, quarter)", "due": qd})
    if m == 9 and esi_on:
        out.append({"kind": "esi_return", "label": "ESIC half-yearly return (Apr-Sep)", "due": date(y, 11, 11)})
    if m == 3:
        if esi_on:
            out.append({"kind": "esi_return", "label": "ESIC half-yearly return (Oct-Mar)", "due": date(y, 5, 11)})
        out.append({"kind": "form130", "label": "Form 130 (salary TDS certificate) har employee ko", "due": date(y, 6, 15)})
        out.append({"kind": "bonus", "label": "Bonus (FY khatam hone ke 8 mahine mein)", "due": date(y, 11, 30)})
    return out
