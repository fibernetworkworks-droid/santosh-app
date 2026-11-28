"""Country packs for the Labour & Wages desk: the overtime rule, the papers people and companies must hold, levies on
construction, withholding on contractor payments, statutory deductions, the payment rail, record keeping and the filing
calendar - each row with its source. A row nobody has checked against the primary text says `check: True`: it is shown as
"check this" and never applied until a person types the source and their name. A country with no rows gets the general rows.

Read for these rows (Nov 2026, see docs/research/construction/LABOUR_WAGES_WORKFLOW.md): the PIB factsheets on India's four
labour codes in force from 21 Nov 2025 (OSH Code: overtime at twice the ordinary rate, contract-labour licence from 50
workers, wages through the bank); secondary sources on the Income-tax Act 2025 s.393(1) (contractor withholding 1% / 2%,
INR 30,000 single / INR 1,00,000 a year); HMRC's Construction Industry Scheme guidance (20% / 30% / 0%, monthly return by
the 19th); US FLSA 29 U.S.C. 207 (1.5x over 40 hours a week) and 29 CFR 5.5(a)(3) (weekly certified payroll on federal
work); QLeave (Queensland portable long service leave levy 0.575% of the cost of work); UAE Ministerial Resolution 340 of
2026 (wages through the Wage Protection System, due on the 1st of the next month). Everything else here says check this."""
from __future__ import annotations

from typing import Any

SRC_OSH = "India - OSH Code 2020, in force 21 Nov 2025 (PIB factsheet, Nov 2025)"
SRC_ITA = "India - Income-tax Act 2025 s.393(1), Table Sl. 6(i), from 1 Apr 2026 (secondary sources; quote the new section on the return)"
SRC_CIS = "UK - HMRC Construction Industry Scheme guidance (CIS 340)"
SRC_FLSA = "US - Fair Labor Standards Act, 29 U.S.C. 207"
SRC_DB = "US - 29 CFR 5.5(a)(3), weekly certified payroll (WH-347) on federal construction contracts"
SRC_QL = "Australia (Queensland) - QLeave levy notice: 0.575% of the total cost of work"
SRC_WPS = "UAE - Ministerial Resolution 340 of 2026 (Wage Protection System; wages due on the 1st of the next month)"

# overtime: basis day (beyond the day's normal hours) | week (beyond the week's hours) | contract (her contract decides)
OT: list[dict[str, Any]] = [
    {"id": "in-ot", "where": "IN", "basis": "day", "after": 8, "week_after": 48, "x": 2.0, "source": SRC_OSH + "; at least twice the ordinary rate, with the worker's consent", "check": False},
    {"id": "us-ot", "where": "US", "basis": "week", "after": 40, "x": 1.5, "source": SRC_FLSA + "; 1.5x the regular rate after 40 hours in a workweek", "check": False},
    {"id": "gb-ot", "where": "GB", "basis": "contract", "after": 0, "x": 0, "source": "UK - no statutory overtime premium; the employment contract decides", "check": False},
    {"id": "ae-ot", "where": "AE", "basis": "day", "after": 8, "x": 1.25, "source": "UAE Labour Law: at least 25% extra (50% at night) - not read from the decree", "check": True},
    {"id": "sa-ot", "where": "SA", "basis": "day", "after": 8, "x": 1.5, "source": "Saudi Labour Law art. 107: 50% extra - not read from the law", "check": True},
    {"id": "sg-ot", "where": "SG", "basis": "day", "after": 8, "x": 1.5, "source": "Singapore Employment Act Part IV: 1.5x for workmen - not read here", "check": True},
    {"id": "au-ot", "where": "AU", "basis": "contract", "after": 0, "x": 0, "source": "Australia - the Building and Construction award / agreement decides - not read here", "check": True},
    {"id": "de-ot", "where": "DE", "basis": "contract", "after": 0, "x": 0, "source": "Germany - no statutory premium; the collective agreement (BRTV) decides - not read here", "check": True},
    {"id": "gen-ot", "where": "*", "basis": "contract", "after": 0, "x": 0, "source": "No rule for this country on file - write your contract's multiplier", "check": True},
]

# papers: whose = worker | company; required = flagged at muster when lapsed or missing (her settings can add more)
PAPERS: list[dict[str, Any]] = [
    {"id": "gen-induction", "where": "*", "whose": "worker", "kind": "induction", "name": "Site induction", "required": True, "source": "General practice", "check": False},
    {"id": "gen-medical", "where": "*", "whose": "worker", "kind": "medical", "name": "Medical fitness", "required": False, "source": "General practice", "check": False},
    {"id": "gen-insurance", "where": "*", "whose": "company", "kind": "insurance", "name": "Workers' accident / compensation insurance", "required": True, "source": "General practice", "check": False},
    {"id": "in-licence", "where": "IN", "whose": "company", "kind": "licence", "name": "Contract-labour licence (from 50 contract workers; work-specific, or one licence up to 5 years)", "required": True, "source": SRC_OSH, "check": False},
    {"id": "in-reg", "where": "IN", "whose": "company", "kind": "registration", "name": "Establishment registration under the OSH Code", "required": True, "source": SRC_OSH, "check": False},
    {"id": "in-bocw", "where": "IN", "whose": "worker", "kind": "registration", "name": "Building worker registration with the state board", "required": False, "source": "State building workers' welfare board - not read here", "check": True},
    {"id": "gb-cscs", "where": "GB", "whose": "worker", "kind": "skills", "name": "CSCS card (or the site's accepted scheme)", "required": True, "source": "Most UK main contractors require it - a site rule, not a law", "check": False},
    {"id": "gb-rtw", "where": "GB", "whose": "worker", "kind": "right_to_work", "name": "Right to work check", "required": True, "source": "UK Home Office right to work checks - not read here", "check": True},
    {"id": "gb-cisreg", "where": "GB", "whose": "company", "kind": "registration", "name": "CIS registration as a contractor", "required": True, "source": SRC_CIS, "check": False},
    {"id": "ae-permit", "where": "AE", "whose": "worker", "kind": "work_permit", "name": "Work permit (labour card) and Emirates ID", "required": True, "source": "UAE MOHRE - not read here", "check": True},
    {"id": "sa-iqama", "where": "SA", "whose": "worker", "kind": "work_permit", "name": "Iqama and work permit", "required": True, "source": "Saudi HRSD - not read here", "check": True},
    {"id": "sg-wp", "where": "SG", "whose": "worker", "kind": "work_permit", "name": "Work permit + Construction Safety Orientation Course", "required": True, "source": "Singapore MOM / BCA - not read here", "check": True},
    {"id": "au-white", "where": "AU", "whose": "worker", "kind": "skills", "name": "White Card (general construction induction)", "required": True, "source": "Safe Work Australia - general construction induction training", "check": False},
    {"id": "us-i9", "where": "US", "whose": "worker", "kind": "right_to_work", "name": "Form I-9 employment eligibility", "required": True, "source": "US - 8 U.S.C. 1324a (Form I-9)", "check": False},
    {"id": "de-a1", "where": "DE", "whose": "worker", "kind": "posting", "name": "A1 certificate for a posted worker", "required": False, "source": "EU Regulation 883/2004 - not read here", "check": True},
]

# levies: base cost_of_work | gross_wages | per_head | per_permit; rate None = the pack does not give one (she must)
LEVIES: list[dict[str, Any]] = [
    {"id": "in-cess", "where": "IN", "name": "Building workers' cess", "base": "cost_of_work", "rate_pct": None,
     "note": "Not more than 2% of the cost of construction under the Social Security Code; 1% was the old Cess Act rate. Your state's rate and rules: check this.",
     "due": {"type": "days_after", "days": 30}, "source": "India - Social Security Code 2020 (building workers' cess) - the state rate is not read here", "check": True},
    {"id": "au-qld", "where": "AU", "region": "QLD", "name": "QLeave portable long service leave levy", "base": "cost_of_work", "rate_pct": 0.575,
     "note": "0.35% of it is long service leave. Paid before the work starts.", "due": {"type": "days_after", "days": 0}, "source": SRC_QL, "check": False},
    {"id": "au-nsw", "where": "AU", "region": "NSW", "name": "NSW long service levy", "base": "cost_of_work", "rate_pct": None,
     "note": "On works of AUD 250,000 or more.", "due": {"type": "days_after", "days": 0}, "source": "NSW Long Service Corporation - rate not read here", "check": True},
    {"id": "de-soka", "where": "DE", "name": "SOKA-BAU contributions", "base": "gross_wages", "rate_pct": None,
     "note": "The general contractor answers for a subcontractor's contributions (AEntG s.14).", "due": {"type": "monthly", "day": 15},
     "source": "Germany - SOKA-BAU; sources disagree on the rate", "check": True},
    {"id": "sg-fwl", "where": "SG", "name": "Foreign worker levy", "base": "per_permit", "rate_pct": None, "per_unit": None,
     "note": "Per work permit per month, by skill tier.", "due": {"type": "monthly", "day": 17}, "source": "Singapore MOM - amounts not read here", "check": True},
]

# withholding on contractor payments, by the subcontractor's status at the date
WITHHOLD: list[dict[str, Any]] = [
    {"id": "in-393", "where": "IN", "name": "Tax withheld on contractor payments (s.393(1))", "rates": {"individual": 1.0, "firm": 2.0, "no_id": 20.0},
     "limits": {"single": 30000, "year": 100000, "year_start": "04-01"}, "due": {"type": "monthly", "day": 7, "march": "04-30"},
     "source": SRC_ITA, "check": False},
    {"id": "gb-cis", "where": "GB", "name": "Construction Industry Scheme deduction", "rates": {"registered": 20.0, "unregistered": 30.0, "gross": 0.0, "no_id": 30.0},
     "limits": {"year_start": "04-06", "ex_materials": True}, "due": {"type": "monthly", "day": 22},
     "source": SRC_CIS + "; verify each new subcontractor with HMRC first; an unverified one is deducted at 30%", "check": False},
    {"id": "us-backup", "where": "US", "name": "Backup withholding when a contractor gives no TIN", "rates": {"no_id": 24.0},
     "limits": {"year_start": "01-01"}, "due": {"type": "monthly", "day": 15}, "source": "US IRS backup withholding - not read here", "check": True},
]

# statutory deductions: shown as suggestions; only HER saved rows (with a source) are applied to a run
DEDUCTIONS: list[dict[str, Any]] = [
    {"id": "in-pf", "where": "IN", "name": "Provident fund (employee)", "pct": 12.0, "base": "basic", "cap": 15000, "employer_pct": 12.0,
     "source": "EPF scheme - wage ceiling and rate not read here", "check": True},
    {"id": "in-esi", "where": "IN", "name": "ESI (employee)", "pct": 0.75, "base": "gross", "cap": 0, "employer_pct": 3.25,
     "source": "ESI scheme - rates and the wage limit not read here", "check": True},
    {"id": "us-fica", "where": "US", "name": "Social Security + Medicare (employee)", "pct": 7.65, "base": "gross", "cap": 0, "employer_pct": 7.65,
     "source": "US FICA - the wage base not read here", "check": True},
    {"id": "gb-paye", "where": "GB", "name": "PAYE and National Insurance", "pct": None, "base": "gross", "cap": 0, "employer_pct": None,
     "source": "Run through your payroll software (HMRC RTI); not worked out here", "check": True},
]

RAIL: dict[str, dict[str, Any]] = {
    "IN": {"format": "in_bulk", "name": "Bank bulk upload (account + IFSC typed for this file)", "source": SRC_OSH + "; wages by bank or electronic mode", "check": False},
    "AE": {"format": "ae_wps", "name": "Wage Protection System file through your agent bank", "source": SRC_WPS, "check": False,
           "note": "The salary information file layout is your agent bank's: check this before you upload."},
    "SA": {"format": "csv", "name": "Mudad wage file", "source": "Saudi Mudad - not read here", "check": True},
}

RETENTION: list[dict[str, Any]] = [
    {"id": "gen-keep", "where": "*", "what": "Muster rolls, wage registers and payslips", "years": None, "source": "Your country's labour rules - not read here", "check": True},
]

# the filing calendar: monthly / quarterly / weekly items she files (Hoola prepares the data)
RETURNS: list[dict[str, Any]] = [
    {"id": "in-tds-q", "where": "IN", "what": "Quarterly return of tax withheld on contractors", "every": "quarter",
     "dues": {"1": "07-31", "2": "10-31", "3": "01-31", "4": "05-31"}, "quarters_from": "04", "needs": "withholding", "source": SRC_ITA + " - the form number under the new Act: check this", "check": True},
    {"id": "gb-cis-m", "where": "GB", "what": "CIS monthly return", "every": "month", "day": 19, "needs": "withholding", "source": SRC_CIS + "; the tax month ends on the 5th", "check": False},
    {"id": "us-wh347", "where": "US", "what": "Certified payroll (WH-347) for federal work", "every": "week", "needs": "federal", "source": SRC_DB, "check": False},
    {"id": "ae-wps", "where": "AE", "what": "Wages paid through WPS", "every": "month", "day": 1, "source": SRC_WPS, "check": False},
]

STATUSES = ("individual", "firm", "registered", "unregistered", "gross")
CURRENCY = {"IN": "INR", "GB": "GBP", "US": "USD", "AE": "AED", "SA": "SAR", "SG": "SGD", "AU": "AUD", "DE": "EUR", "IE": "EUR", "FR": "EUR",
            "CA": "CAD", "NZ": "NZD", "ZA": "ZAR", "KE": "KES", "NG": "NGN", "QA": "QAR", "OM": "OMR", "KW": "KWD", "BH": "BHD", "MY": "MYR"}


def _applies(row: dict[str, Any], country: str, region: str = "") -> bool:
    w = row.get("where", "*")
    if w not in ("*", country):
        return False
    r = row.get("region")
    return not r or not region or r.upper() == region.upper()


def ot(country: str, off: list[str] | None = None) -> dict[str, Any]:
    off = set(off or [])
    c = (country or "").upper()
    for r in OT:
        if r["where"] == c and r["id"] not in off:
            return r
    return next(r for r in OT if r["where"] == "*")


def papers(country: str, whose: str = "", off: list[str] | None = None) -> list[dict[str, Any]]:
    off = set(off or [])
    c = (country or "").upper()
    return [r for r in PAPERS if r["id"] not in off and _applies(r, c) and (not whose or r["whose"] == whose)]


def row(pid: str) -> dict[str, Any] | None:
    for group in (LEVIES, WITHHOLD, DEDUCTIONS, PAPERS, OT, RETURNS):
        for r in group:
            if r["id"] == pid:
                return r
    return None


def pack(country: str, region: str = "") -> dict[str, Any]:
    c = (country or "").upper()
    return {"country": c or "-", "currency": CURRENCY.get(c, ""), "ot": ot(c),
            "papers": [r for r in PAPERS if _applies(r, c)],
            "levies": [r for r in LEVIES if _applies(r, c, region) or (r["where"] == c)],
            "withholding": [r for r in WITHHOLD if _applies(r, c)],
            "deductions": [r for r in DEDUCTIONS if _applies(r, c)],
            "rail": RAIL.get(c, {"format": "csv", "name": "A CSV for your bank (names, your payee references, amounts)", "source": "General", "check": False}),
            "retention": [r for r in RETENTION if _applies(r, c)],
            "returns": [r for r in RETURNS if _applies(r, c)],
            "note": ("Rows marked 'check this' were not read from the primary text: they are shown, never applied, until a person writes "
                     "the source and their name. A country with no rows of its own gets the general rows only.")}
