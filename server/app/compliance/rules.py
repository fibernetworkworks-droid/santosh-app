"""Compliance Sahayak rules: the statutory catalogue (what applies to whom, when it falls due, starter penalties with sources).

Everything here is a STARTER read from dated public sources (Oct 2026). Hoola is not a CA / CS / lawyer: every line carries
"CA / CS / vakil se pakka karwaiye". A source is only shown when it was really read (with its link and date); otherwise the
entry says "[citation needed]" and is marked verify=True. Dates move by notification: her own date (`due_override`) always wins.
"""
from __future__ import annotations

import calendar as _cal
import re
from datetime import date, timedelta
from typing import Any, Callable

CHECK_LINE = "This is information / a draft, not legal advice: have a CA / CS / lawyer confirm it."
NEVER = [
    "Hoola never files, submits or pays on a portal itself: even after your approval card, the login, OTP, payment and submit are done by you.",
    "A task is 'done' only with evidence (challan / ack / certificate file) or on your own word.",
    "The monthly compliance certificate is signed off only by your tap in the app.",
    "It never makes up a section number, date or penalty: no source means '[citation needed]'.",
    "It never sends money and never pays a challan.",
]

ENTITIES = {"proprietor": "Proprietorship", "partnership": "Partnership firm", "llp": "LLP", "pvt_ltd": "Private limited company",
            "public_ltd": "Public limited company", "opc": "One person company", "trust": "Trust", "society": "Society", "huf": "HUF"}
COMPANY = ("pvt_ltd", "public_ltd", "opc")
AREAS = {"gst": "GST", "tds": "TDS / TCS", "labour": "Labour (PF / ESIC / codes)", "pt": "Professional tax", "lwf": "Labour welfare fund",
         "licence": "Licence / registration", "fssai": "FSSAI (food)", "fire": "Fire", "pollution": "Pollution", "msme": "MSME",
         "roc": "ROC / MCA", "posh": "POSH", "custom": "Your own"}
POLLUTION = ("none", "white", "green", "orange", "red")
FOOD_KINDS = ("none", "manufacturer", "importer", "packer", "relabeller", "trader", "restaurant", "milk", "storage", "transport")
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ---------------------------------------------------------------- sources (read on the dates shown)
SRC = {
    "tds": {"title": "StudyCafe: TDS / TCS due date calendar tax year 2026-27 (Income-tax Act 2025: s.398, s.427, forms 138 / 140 / 143)",
            "url": "https://studycafe.in/tds-and-tcs-due-date-compliance-calendar-for-tax-year-2026-27-419614.html", "read": "2026-10-23"},
    "gst": {"title": "Hoola GST Assistant (v0.93) rules: due dates, late fee, Sec 50 interest (ClearTax returns rules from July 2025)",
            "url": "https://cleartax.in/s/gst-return-filing-rule-changes-from-july-2025", "read": "2026-10-22"},
    "osh": {"title": "iPleaders: OSH Central Rules 2026 (G.S.R. 345(E), 8 May 2026) - Form I registration on Shram Suvidha, "
                     "annual return Form XVII by last day of February, contractor half-yearly Form XVIII, contract labour licence at 50+",
            "url": "https://blog.ipleaders.in/osh-central-rules-2026-registration-hours-contract-labour/", "read": "2026-10-23"},
    "codes": {"title": "K&S Partners: Labour codes Central Rules 2026 notified 8 May 2026 (online registration, registers, returns)",
              "url": "https://ksandk.com/newsletter/labour-codes-central-rules-2026/", "read": "2026-10-23"},
    "hrcal": {"title": "PocketHRMS HR compliance calendar India 2026 (PF 15th, ESIC 15th, POSH annual report 31 Jan) - undated page",
              "url": "https://www.pockethrms.com/tools/hr-compliance-calendar-india/", "read": "2026-10-23"},
    "mhpt": {"title": "CalcGuru: Maharashtra professional tax 2026-27 (notification 28 Feb 2026: PTRC 15th / annual 15 Mar, PTEC 15 Jun)",
             "url": "https://calcguru.in/?p=529", "read": "2026-10-23"},
    "mhlwf": {"title": "factoHR: Maharashtra Labour Welfare Fund (June / December, due 15 July / 15 January)",
              "url": "https://factohr.com/labour-welfare-fund/maharashtra/", "read": "2026-10-23"},
    "fssai": {"title": "ClearTax: FSSAI annual return D-1 (31 May), D-2 for milk (31 Oct / 30 Apr), Rs 100 a day late",
              "url": "https://cleartax.in/s/fssai-annual-returns", "read": "2026-10-23"},
    "msme1": {"title": "CalcGuru: MSME-1 half-yearly return (31 Oct / 30 Apr), Sec 405(4) penalty (Aug 2026)",
              "url": "https://calcguru.in/?p=5764", "read": "2026-10-23"},
    "consent": {"title": "Corporate Professionals: Air Act consent guidelines 29 Jan 2025 (renewal 4 months early = 5% rebate; late 25 / 50 / 100%)",
                "url": "https://www.corporateprofessionals.com/regulatoryupdate/control-of-air-pollution-grant-refusal-or-cancellation-of-consent-guidelines-2025/",
                "read": "2026-10-23"},
    "dir3": {"title": "EquityList: DIR-3 KYC once every three financial years from 31 Mar 2026, due 30 June of that year, Rs 5,000 late",
             "url": "https://www.equitylist.co/blog-post/dir-3-kyc", "read": "2026-10-23"},
}
NO_SRC = {"title": "[citation needed]", "url": "", "read": ""}


# ---------------------------------------------------------------- small date helpers
def last_day(y: int, m: int) -> int:
    return _cal.monthrange(y, m)[1]


def d(y: int, m: int, day: int) -> date:
    return date(y, m, min(day, last_day(y, m)))


def add_months(y: int, m: int, k: int) -> tuple[int, int]:
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1


def fy_start(on: date) -> int:
    return on.year if on.month >= 4 else on.year - 1


def fy_label(y: int) -> str:
    return f"FY{str(y)[2:]}{str(y + 1)[2:]}"


def nice(dt: date | None) -> str:
    return f"{dt.day} {MONTHS[dt.month]} {dt.year}" if dt else ""


def state_code(v: Any) -> str:
    from ..payroll.rules import state_code as sc
    return sc(str(v or ""))


# ---------------------------------------------------------------- facts
FACT_KEYS = ("entity", "state", "employees", "contract_workers", "contractor", "turnover", "gstin", "gst_scheme", "tan", "salary_tds", "tcs",
             "pt_yearly", "sectors", "food_kind", "food_licence", "pollution", "factory", "fire_noc", "msme_dues", "agm_date",
             "licences")


def clean_facts(f: dict | None) -> dict:
    f = dict(f or {})
    out: dict[str, Any] = {}
    e = str(f.get("entity") or "").strip().lower().replace(" ", "_").replace("-", "_")
    e = {"private_limited": "pvt_ltd", "pvt": "pvt_ltd", "company": "pvt_ltd", "ltd": "public_ltd", "proprietorship": "proprietor",
         "firm": "partnership", "partnership_firm": "partnership"}.get(e, e)
    if e and e not in ENTITIES:
        raise ValueError("entity = " + " | ".join(ENTITIES))
    out["entity"] = e
    sc = state_code(f.get("state"))
    if f.get("state") and not sc:
        raise ValueError("Could not read the state: write its name (Maharashtra) or GST code (27).")
    out["state"] = sc
    for k in ("employees", "contract_workers"):
        v = f.get(k)
        if v in (None, ""):
            out[k] = None
        else:
            try:
                n = int(float(v))
            except (TypeError, ValueError):
                raise ValueError(f"{k} must be a number")
            if n < 0:
                raise ValueError(f"{k} cannot be negative")
            out[k] = n
    for k in ("turnover", "pt_yearly"):
        v = f.get(k)
        out[k] = None if v in (None, "") else float(v)
    g = re.sub(r"\s", "", str(f.get("gstin") or "")).upper()
    if g:
        from ..gstp.rules import valid_gstin
        if not valid_gstin(g):
            raise ValueError("The GSTIN does not look right (check digit).")
        if not sc:
            out["state"] = g[:2]
    out["gstin"] = g
    sch = str(f.get("gst_scheme") or "monthly").lower()
    out["gst_scheme"] = sch if sch in ("monthly", "qrmp", "composition") else "monthly"
    for k in ("tan", "salary_tds", "tcs", "factory", "fire_noc", "msme_dues", "contractor"):
        out[k] = bool(f.get(k)) if f.get(k) is not None else None
    secs = f.get("sectors") or []
    if isinstance(secs, str):
        secs = [x for x in re.split(r"[,\s/]+", secs) if x]
    out["sectors"] = sorted({str(x).strip().lower()[:30] for x in secs if str(x).strip()})[:12]
    fk = str(f.get("food_kind") or "none").lower()
    out["food_kind"] = fk if fk in FOOD_KINDS else "none"
    fl = str(f.get("food_licence") or "").lower()
    out["food_licence"] = fl if fl in ("", "registration", "state", "central") else ""
    pol = str(f.get("pollution") or "none").lower()
    if pol not in POLLUTION:
        raise ValueError("pollution = " + " | ".join(POLLUTION))
    out["pollution"] = pol
    out["agm_date"] = _iso(f.get("agm_date"))
    lic = f.get("licences") or {}
    out["licences"] = {k: _iso(v) for k, v in dict(lic).items() if k in LICENCE_KEYS and _iso(v)}
    return out


def _iso(v) -> str:
    if not v:
        return ""
    s = str(v).strip()[:10]
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def _n(f: dict, k: str) -> int:
    return int(f.get(k) or 0)


def has_food(f: dict) -> bool:
    return f.get("food_kind", "none") != "none" or bool(f.get("food_licence")) or bool({"food", "restaurant", "hotel", "dairy"} & set(f.get("sectors") or []))


def is_factory(f: dict) -> bool:
    return bool(f.get("factory")) or bool({"factory", "manufacturing"} & set(f.get("sectors") or []))


# ---------------------------------------------------------------- the catalogue
# freq: monthly | quarterly | half | yearly | cyear (calendar year) | expiry | once | agm | gst | her
# due: monthly -> (day, march_override (m, d) or None); quarterly / half / yearly -> list of (period_tag, month, day, year offset from
# the FY start year); cyear -> (month, day) of the next year; expiry -> licence key + lead days; agm -> days after the AGM.
LICENCE_KEYS = {"fssai": "FSSAI licence / registration", "consent": "Pollution consent to operate (CTO)", "fire": "Fire NOC / certificate",
                "shop": "Shop & Establishment registration", "trade": "Trade licence (municipal)", "factory": "Factory licence (OSH Code)",
                "contract": "Contract labour licence (OSH Code)"}


def _a(cond: bool, why: str) -> tuple[bool, str]:
    return bool(cond), why


def _state(f: dict) -> str:
    return f.get("state") or ""


CATALOGUE: list[dict[str, Any]] = [
    # ---- GST (linked to the GST Sahayak when she uses it)
    {"key": "gst", "area": "gst", "label": "GST return", "freq": "gst", "link": "gstp",
     "applies": lambda f: _a(bool(f.get("gstin")), "has a GSTIN"), "src": "gst", "portal": "gst.gov.in",
     "evidence": "ARN / filed return PDF", "penalty": {"text": "Late fee (GSTR-3B Rs 50 / day, nil Rs 20, cap) + 18% interest (Sec 50) - calculated by the GST Assistant",
                                                      "gst": True}},
    {"key": "gstr9", "area": "gst", "label": "GSTR-9 annual return", "freq": "yearly", "due": [("A", 12, 31, 1)], "link": "gstp",
     "applies": lambda f: _a(bool(f.get("gstin")) and (f.get("turnover") or 0) > 2e7, "GSTIN + turnover above Rs 2 crore"),
     "src": "gst", "portal": "gst.gov.in", "evidence": "ARN", "penalty": {"text": "Late fee per day (see the GST Assistant)"}},
    # ---- TDS / TCS (non-salary; salary TDS lives in payroll)
    {"key": "tds_deposit", "area": "tds", "label": "TDS deposit (challan)", "freq": "monthly", "due": (7, (4, 30)),
     "applies": lambda f: _a(bool(f.get("tan")), "has a TAN / deducts TDS"), "src": "tds", "portal": "Income-tax e-pay tax",
     "evidence": "Challan (CIN / BSR) PDF", "penalty": {"text": "Late deposit: 1.5% / month interest (Sec 398(3))", "interest_pm": 1.5}},
    {"key": "tds_140", "area": "tds", "label": "TDS statement Form 140 (non-salary)", "freq": "quarterly",
     "due": [("Q1", 7, 31, 0), ("Q2", 10, 31, 0), ("Q3", 1, 31, 1), ("Q4", 5, 31, 1)],
     "applies": lambda f: _a(bool(f.get("tan")), "has a TAN"), "src": "tds", "portal": "TRACES / e-filing",
     "evidence": "Statement token / ack", "penalty": {"text": "Rs 200 / day (Sec 427), up to the TDS amount; penalty of Rs 10,000-1,00,000 (Sec 461/462)",
                                                        "per_day": 200}},
    {"key": "tds_138", "area": "tds", "label": "Salary TDS statement Form 138", "freq": "quarterly", "link": "payroll",
     "due": [("Q1", 7, 31, 0), ("Q2", 10, 31, 0), ("Q3", 1, 31, 1), ("Q4", 5, 31, 1)],
     "applies": lambda f: _a(bool(f.get("salary_tds")), "TDS is deducted on salary"), "src": "tds", "portal": "TRACES / e-filing",
     "evidence": "Statement token / ack", "penalty": {"text": "Rs 200 / day (Sec 427), up to the TDS amount", "per_day": 200}},
    {"key": "tcs_deposit", "area": "tds", "label": "TCS deposit (challan)", "freq": "monthly", "due": (7, (4, 7)),
     "applies": lambda f: _a(bool(f.get("tcs")), "collects TCS"), "src": "tds", "portal": "Income-tax e-pay tax",
     "evidence": "Challan PDF", "penalty": {"text": "Interest on a late deposit (Sec 398)"}},
    {"key": "tcs_143", "area": "tds", "label": "TCS statement Form 143", "freq": "quarterly",
     "due": [("Q1", 7, 31, 0), ("Q2", 10, 31, 0), ("Q3", 1, 31, 1), ("Q4", 5, 15, 1)],
     "applies": lambda f: _a(bool(f.get("tcs")), "collects TCS"), "src": "tds", "portal": "TRACES / e-filing",
     "evidence": "Statement ack", "penalty": {"text": "Rs 200 / day (Sec 427)", "per_day": 200}},
    # ---- PF / ESIC (linked to payroll when she uses it)
    {"key": "pf", "area": "labour", "label": "PF ECR + challan", "freq": "monthly", "due": (15, None), "link": "payroll",
     "applies": lambda f: _a(_n(f, "employees") >= 20, "20+ people work here"), "src": "hrcal", "portal": "EPFO unified portal",
     "evidence": "ECR ack + TRRN challan", "penalty": {"text": "Late = interest + damages (Social Security Code / EPFO); confirm the rate with EPFO"}},
    {"key": "esic", "area": "labour", "label": "ESIC contribution", "freq": "monthly", "due": (15, None), "link": "payroll",
     "applies": lambda f: _a(_n(f, "employees") >= 10, "10+ people (within the ESIC wage limit)"), "src": "hrcal", "portal": "ESIC portal",
     "evidence": "Challan", "penalty": {"text": "Late = interest + damages (ESIC); confirm the rate with ESIC"}},
    # ---- labour codes (in force 21 Nov 2025; central rules 8 May 2026)
    {"key": "osh_reg", "area": "labour", "label": "Establishment registration (OSH Code, Form I, Shram Suvidha)", "freq": "once",
     "applies": lambda f: _a(_n(f, "employees") >= 10, "10+ workers"), "src": "osh", "portal": "Shram Suvidha",
     "evidence": "Registration certificate", "penalty": {"text": "Working without registration = penalties under the OSH Code; check the state rules"}},
    {"key": "annual_return", "area": "labour", "label": "Annual return Form XVII (labour codes, Shram Suvidha)", "freq": "cyear", "due": (2, 31),
     "applies": lambda f: _a(_n(f, "employees") >= 10, "10+ workers"), "src": "osh", "portal": "Shram Suvidha",
     "evidence": "Return ack", "penalty": {"text": "State / central inspector notice; confirm the date from your state's rules"}},
    {"key": "contract_licence", "area": "labour", "label": "Contract labour licence (Form XXI)", "freq": "once",
     "applies": lambda f: _a(bool(f.get("contractor")) and _n(f, "contract_workers") >= 50, "you are a contractor with 50+ contract workers"),
     "src": "osh", "portal": "Shram Suvidha", "evidence": "Licence", "penalty": {"text": "Engaging contract labour without a licence is prohibited"}},
    {"key": "contractor_half", "area": "labour", "label": "Contractor half-yearly return Form XVIII", "freq": "half",
     "due": [("H1", 7, 30, 0), ("H2", 1, 30, 1)],
     "applies": lambda f: _a(bool(f.get("contractor")) and _n(f, "contract_workers") >= 50, "licensed contractor"), "src": "osh",
     "portal": "Shram Suvidha", "evidence": "Return ack", "penalty": {"text": "Inspector notice"}, "verify": True},
    {"key": "posh_ic", "area": "posh", "label": "Set up the POSH Internal Committee (10+ people)", "freq": "once",
     "applies": lambda f: _a(_n(f, "employees") >= 10, "10+ people"), "src": "", "portal": "-",
     "evidence": "IC order / notice board photo", "penalty": {"text": "[citation needed] - confirm with a lawyer"}},
    {"key": "posh_report", "area": "posh", "label": "POSH annual report to the District Officer", "freq": "cyear", "due": (1, 31),
     "applies": lambda f: _a(_n(f, "employees") >= 10, "10+ people"), "src": "hrcal", "portal": "District Officer / state portal",
     "evidence": "Report copy + receipt", "penalty": {"text": "[citation needed]"}, "verify": True},
    # ---- professional tax / LWF (Maharashtra built in; other states her own date)
    {"key": "ptrc_month", "area": "pt", "label": "PTRC monthly return (Maharashtra)", "freq": "monthly", "due": (15, None),
     "applies": lambda f: _a(_state(f) == "27" and _n(f, "employees") > 0 and (f.get("pt_yearly") or 0) >= 100000,
                             "Maharashtra, staff, yearly PT Rs 1 lakh+"), "src": "mhpt", "portal": "mahagst.gov.in",
     "evidence": "Return ack + challan", "penalty": {"text": "1.25% / month interest, penalty up to 10%, Rs 1,000 late fee / return", "per_return": 1000,
                                                      "interest_pm": 1.25}},
    {"key": "ptrc_year", "area": "pt", "label": "PTRC annual return (Maharashtra)", "freq": "yearly", "due": [("A", 3, 15, 1)],
     "applies": lambda f: _a(_state(f) == "27" and _n(f, "employees") > 0 and (f.get("pt_yearly") or 0) < 100000,
                             "Maharashtra, staff, yearly PT below Rs 1 lakh (or not known)"), "src": "mhpt", "portal": "mahagst.gov.in",
     "evidence": "Return ack + challan", "penalty": {"text": "Rs 1,000 late fee / return + interest", "per_return": 1000}},
    {"key": "ptec", "area": "pt", "label": "PTEC (the business's own PT, Maharashtra)", "freq": "yearly", "due": [("A", 6, 15, 0)],
     "applies": lambda f: _a(_state(f) == "27" and bool(f.get("entity")), "business in Maharashtra"), "src": "mhpt",
     "portal": "mahagst.gov.in", "evidence": "Challan", "penalty": {"text": "1.25% / month interest + penalty", "interest_pm": 1.25}},
    {"key": "pt_other", "area": "pt", "label": "Professional tax (your state's date)", "freq": "her",
     "applies": lambda f: _a(_state(f) not in ("", "27") and _n(f, "employees") > 0 and _state(f) in _pt_states(),
                             "PT applies in this state"), "src": "", "portal": "state portal", "evidence": "Challan",
     "penalty": {"text": "[citation needed] - the state's rule"}},
    {"key": "lwf_mh", "area": "lwf", "label": "Labour Welfare Fund (Maharashtra)", "freq": "half", "due": [("H1", 7, 15, 0), ("H2", 1, 15, 1)],
     "applies": lambda f: _a(_state(f) == "27" and _n(f, "employees") > 0, "Maharashtra, staff"), "src": "mhlwf",
     "portal": "MLWB portal", "evidence": "Challan + statement", "penalty": {"text": "The board's interest / notice; confirm the amount with the board"}},
    # ---- licences (expiry from HER paper; office renewals linked when there)
    {"key": "fssai", "area": "fssai", "label": "FSSAI licence renew", "freq": "expiry", "due": ("fssai", 120), "link": "office",
     "applies": lambda f: _a(has_food(f), "makes / sells / stores food"), "src": "", "portal": "foscos.fssai.gov.in",
     "evidence": "New licence PDF", "penalty": {"text": "Renewing in the last 30 days = Rs 100 / day (Hoola v0.115 note); expired = a new licence",
                                                  "per_day": 100}, "verify": True},
    {"key": "fssai_d1", "area": "fssai", "label": "FSSAI annual return D-1", "freq": "yearly", "due": [("A", 5, 31, 1)],
     "applies": lambda f: _a(f.get("food_kind") in ("manufacturer", "importer", "packer", "relabeller", "milk")
                             or f.get("food_licence") in ("state", "central"), "manufacturer / importer / packer or a state / central licence"),
     "src": "fssai", "portal": "foscos.fssai.gov.in", "evidence": "D-1 ack", "penalty": {"text": "Rs 100 / day", "per_day": 100}},
    {"key": "fssai_d2", "area": "fssai", "label": "FSSAI half-yearly return D-2 (milk)", "freq": "half",
     "due": [("H1", 10, 31, 0), ("H2", 4, 30, 1)],
     "applies": lambda f: _a(f.get("food_kind") == "milk", "milk / dairy product"), "src": "fssai", "portal": "foscos.fssai.gov.in",
     "evidence": "D-2 ack", "penalty": {"text": "Rs 100 / day", "per_day": 100}},
    {"key": "consent", "area": "pollution", "label": "Pollution consent (CTO) renew", "freq": "expiry", "due": ("consent", 120), "link": "office",
     "applies": lambda f: _a(f.get("pollution") in ("green", "orange", "red"), f"{f.get('pollution')} category"), "src": "consent",
     "portal": "State PCB portal", "evidence": "Renewed consent order",
     "penalty": {"text": "Apply 4 months early = 5% fee rebate; apply late = 25% / 50% / 100% extra fee (guidelines 29 Jan 2025)"}},
    {"key": "env_statement", "area": "pollution", "label": "Environmental statement (Form V)", "freq": "yearly", "due": [("A", 9, 30, 1)],
     "applies": lambda f: _a(f.get("pollution") in ("orange", "red"), "unit that needs consent"), "src": "", "portal": "State PCB portal",
     "evidence": "Ack", "penalty": {"text": "[citation needed]"}, "verify": True},
    {"key": "fire", "area": "fire", "label": "Fire NOC / fire certificate renew", "freq": "expiry", "due": ("fire", 60), "link": "office",
     "applies": lambda f: _a(bool(f.get("fire_noc")), "you said a fire NOC is needed"), "src": "", "portal": "fire dept / Mahafire",
     "evidence": "Certificate", "penalty": {"text": "[citation needed] (Maharashtra: Form B twice a year, Hoola Office note)"}, "verify": True},
    {"key": "shop", "area": "licence", "label": "Shop & Establishment registration / intimation", "freq": "expiry", "due": ("shop", 60),
     "link": "office", "applies": lambda f: _a(bool({"shop", "office", "restaurant", "hotel", "trading", "it"} & set(f.get("sectors") or []))
                                              or (bool(f.get("entity")) and not is_factory(f)), "shop / office"),
     "src": "", "portal": "state labour portal", "evidence": "Certificate / intimation receipt",
     "penalty": {"text": "[citation needed] (Maharashtra 2017 Act: fewer than 10 = one-time intimation; 10+ = registration)"}, "verify": True},
    {"key": "trade", "area": "licence", "label": "Trade licence renew (municipal)", "freq": "expiry", "due": ("trade", 30), "link": "office",
     "applies": lambda f: _a(bool((f.get("licences") or {}).get("trade")), "a trade licence date is given"), "src": "",
     "portal": "municipal council", "evidence": "Licence", "penalty": {"text": "[citation needed] - the city's rule"}, "verify": True},
    {"key": "factory", "area": "licence", "label": "Factory licence renew (OSH Code)", "freq": "expiry", "due": ("factory", 60), "link": "office",
     "applies": lambda f: _a(is_factory(f), "factory / manufacturing"), "src": "codes", "portal": "state labour portal",
     "evidence": "Licence", "penalty": {"text": "Running a factory without a licence is prohibited; check the state rules"}, "verify": True},
    # ---- MSME
    {"key": "msme1", "area": "msme", "label": "MSME-1 (dues to MSE suppliers older than 45 days)", "freq": "half",
     "due": [("H1", 10, 31, 0), ("H2", 4, 30, 1)], "link": "cosec",
     "applies": lambda f: _a(f.get("entity") in COMPANY and bool(f.get("msme_dues")), "company + dues to an MSE supplier older than 45 days"),
     "src": "msme1", "portal": "MCA V3", "evidence": "SRN / challan", "penalty": {"text": "Company up to Rs 25,000; officer Rs 25,000-3,00,000 (Sec 405(4))"}},
    # ---- ROC basics (the Company Secretary Sahayak 'cosec' owns these when she uses it)
    {"key": "agm", "area": "roc", "label": "AGM (financial statements adopt)", "freq": "yearly", "due": [("A", 9, 30, 1)], "link": "cosec",
     "applies": lambda f: _a(f.get("entity") in ("pvt_ltd", "public_ltd"), "company"), "src": "", "portal": "-",
     "evidence": "AGM minutes", "penalty": {"text": "[citation needed] - confirm with a CS"}, "verify": True},
    {"key": "aoc4", "area": "roc", "label": "AOC-4 (financial statements)", "freq": "agm", "due": 30, "link": "cosec",
     "applies": lambda f: _a(f.get("entity") in COMPANY, "company"), "src": "", "portal": "MCA V3", "evidence": "SRN",
     "penalty": {"text": "Additional fee per day - [citation needed], confirm with a CS"}, "verify": True},
    {"key": "mgt7", "area": "roc", "label": "MGT-7 / 7A (annual return)", "freq": "agm", "due": 60, "link": "cosec",
     "applies": lambda f: _a(f.get("entity") in COMPANY, "company"), "src": "", "portal": "MCA V3", "evidence": "SRN",
     "penalty": {"text": "Additional fee per day - [citation needed], confirm with a CS"}, "verify": True},
    {"key": "dpt3", "area": "roc", "label": "DPT-3 (deposits / loans return)", "freq": "yearly", "due": [("A", 6, 30, 1)], "link": "cosec",
     "applies": lambda f: _a(f.get("entity") in COMPANY, "company"), "src": "", "portal": "MCA V3", "evidence": "SRN",
     "penalty": {"text": "[citation needed]"}, "verify": True},
    {"key": "dir3", "area": "roc", "label": "DIR-3 KYC directors (every three years, 30 June)", "freq": "her", "link": "cosec",
     "applies": lambda f: _a(f.get("entity") in COMPANY + ("llp",), "directors / designated partners"), "src": "dir3",
     "portal": "MCA V3", "evidence": "SRN", "penalty": {"text": "Late = Rs 5,000; DIN deactivated", "per_return": 5000}},
    {"key": "llp11", "area": "roc", "label": "LLP Form 11 (annual return)", "freq": "yearly", "due": [("A", 5, 30, 1)], "link": "cosec",
     "applies": lambda f: _a(f.get("entity") == "llp", "LLP"), "src": "", "portal": "MCA V3", "evidence": "SRN",
     "penalty": {"text": "[citation needed]"}, "verify": True},
    {"key": "llp8", "area": "roc", "label": "LLP Form 8 (accounts + solvency)", "freq": "yearly", "due": [("A", 10, 30, 1)], "link": "cosec",
     "applies": lambda f: _a(f.get("entity") == "llp", "LLP"), "src": "", "portal": "MCA V3", "evidence": "SRN",
     "penalty": {"text": "[citation needed]"}, "verify": True},
]
BY_KEY = {c["key"]: c for c in CATALOGUE}


def _pt_states() -> set[str]:
    from ..payroll.rules import PT_STATES
    return set(PT_STATES)


def source(entry: dict) -> dict:
    return dict(SRC.get(entry.get("src") or "", NO_SRC))


def applicability(facts: dict) -> list[dict]:
    out = []
    for c in CATALOGUE:
        try:
            ok, why = c["applies"](facts)
        except Exception:
            ok, why = False, "facts incomplete"
        out.append({"key": c["key"], "area": c["area"], "area_label": AREAS[c["area"]], "label": c["label"], "applies": ok,
                    "why": why if ok else f"no: not the case that {why}", "freq": c["freq"], "link": c.get("link", ""),
                    "source": source(c), "verify": bool(c.get("verify")) or not c.get("src"), "portal": c.get("portal", ""),
                    "evidence": c.get("evidence", "")})
    return out


def questions(facts: dict) -> list[str]:
    q = []
    if not facts.get("entity"):
        q.append("What type of business is it: proprietor / partnership / LLP / pvt ltd / OPC / trust?")
    if not facts.get("state"):
        q.append("In which state? (Maharashtra or GST code 27)")
    if facts.get("employees") is None:
        q.append("How many people work there (staff + workers)?")
    if facts.get("tan") is None:
        q.append("Do you deduct TDS (have a TAN)? On rent / contractor / professional fees?")
    if facts.get("state") == "27" and (facts.get("employees") or 0) > 0 and facts.get("pt_yearly") is None:
        q.append("How much is the staff's PT for the year? (Rs 1 lakh+ = PTRC every month, less = once a year)")
    if facts.get("pollution") == "none" and is_factory(facts):
        q.append("What is the pollution board category: white / green / orange / red?")
    if has_food(facts) and not (facts.get("licences") or {}).get("fssai"):
        q.append("Until when is the FSSAI licence valid?")
    if facts.get("entity") in COMPANY and facts.get("msme_dues") is None:
        q.append("Is any payment to a micro / small supplier pending for more than 45 days? (MSME-1)")
    if facts.get("fire_noc") is None:
        q.append("Does your premises need a fire NOC / certificate? (depends on the building / business type)")
    return q


# ---------------------------------------------------------------- instances: (period, due date) inside a window
def instances(entry: dict, facts: dict, start: date, end: date) -> list[tuple[str, date | None, str]]:
    """[(period, due, label suffix)] for this obligation with due dates in [start, end]. Due None = she must give the date."""
    fr = entry["freq"]
    out: list[tuple[str, date | None, str]] = []
    if fr == "monthly":
        day, mar = entry["due"]
        y, m = add_months(start.year, start.month, -2)
        for _ in range(16):
            ny, nm = add_months(y, m, 1)
            due = d(ny, nm, day)
            if mar and m == 3:
                due = d(ny, mar[0], mar[1])
            if start <= due <= end:
                out.append((f"{y:04d}-{m:02d}", due, f"{MONTHS[m]} {y}"))
            y, m = ny, nm
    elif fr in ("quarterly", "half", "yearly"):
        for fy in range(fy_start(start) - 1, fy_start(end) + 2):
            for tag, mm, dd, yo in entry["due"]:
                due = d(fy + yo, mm, dd)
                if start <= due <= end:
                    per = fy_label(fy) + ("" if tag == "A" else f"-{tag}")
                    out.append((per, due, per.replace("FY", "FY ")))
    elif fr == "cyear":
        mm, dd = entry["due"]
        for y in range(start.year - 1, end.year + 1):
            due = d(y + 1, mm, dd)
            if start <= due <= end:
                out.append((f"CY{y}", due, f"year {y}"))
    elif fr == "expiry":
        lk, lead = entry["due"]
        exp = (facts.get("licences") or {}).get(lk)
        if exp:
            e = date.fromisoformat(exp)
            due = e - timedelta(days=lead)
            if due <= end and e >= start - timedelta(days=60):
                out.append((f"exp:{exp}", due, f"valid until {nice(e)}; apply {lead} days before"))
        else:
            out.append(("exp:?", None, "tell me the valid-till date"))
    elif fr == "agm":
        agm = facts.get("agm_date")
        if agm:
            a = date.fromisoformat(agm)
            due = a + timedelta(days=int(entry["due"]))
            if start <= due <= end:
                out.append((f"AGM{agm}", due, f"{entry['due']} days after the AGM on {nice(a)}"))
        else:
            out.append(("AGM?", None, "tell me the AGM date"))
    elif fr in ("once", "her"):
        out.append(("once" if fr == "once" else "her", None, "tell me the date / status"))
    elif fr == "gst":
        from ..gstp import rules as G
        sch, st = facts.get("gst_scheme") or "monthly", facts.get("state") or "27"
        y, m = add_months(start.year, start.month, -2)
        for _ in range(16):
            per = f"{y:04d}-{m:02d}"
            for ob in G.obligations(per, sch, st):
                if ob["kind"] == "iff":
                    continue
                if start <= ob["due"] <= end:
                    out.append((f"{per}:{ob['kind']}", ob["due"], f"{ob['label']} {MONTHS[m]} {y}"))
            y, m = add_months(y, m, 1)
    return out


def penalty(entry: dict, days_late: int, period: str = "", facts: dict | None = None) -> dict:
    """Starter penalty andaaza for being late (never a promise; source alongside)."""
    p = entry.get("penalty") or {}
    out = {"text": p.get("text", "[citation needed]"), "amount": None, "basis": ""}
    if days_late <= 0:
        return out
    if p.get("gst") and ":" in period:
        from ..gstp import rules as G
        kind = period.split(":", 1)[1]
        rk = "gstr1" if kind in ("gstr1",) else kind
        try:
            out["amount"] = float(G.late_fee(rk, days_late, False, float((facts or {}).get("turnover") or 0)))
            out["basis"] = f"late fee for {days_late} days (calculated by the GST Assistant; interest is extra)"
        except Exception:
            pass
    elif p.get("per_day"):
        out["amount"] = float(p["per_day"] * days_late)
        out["basis"] = f"Rs {p['per_day']} x {days_late} days" + (" (not more than the TDS / TCS amount)" if p["per_day"] == 200 else "")
    elif p.get("per_return"):
        out["amount"] = float(p["per_return"])
        out["basis"] = "late fee per return"
    elif p.get("interest_pm"):
        out["basis"] = f"{p['interest_pm']}% interest every month (on the amount)"
    return out


def steps(entry: dict) -> list[str]:
    """Portal steps she does herself (login / OTP / payment / submit are hers)."""
    portal = entry.get("portal") or "portal"
    return [f"You log in at {portal} (the password / OTP is yours to enter)",
            "Fill in the details from the information / file Hoola prepared, or have the Computer Operator open the form",
            "If there is a payment / challan, you pay it yourself",
            "You press Submit; send Hoola the ack / ARN / challan file (evidence)"]


def certificate_text(name: str, firm: str, month_label: str, counts: dict, exceptions: list[str]) -> str:
    lines = [f"I, {name or '[name]'}, on behalf of {firm or '[business]'}, confirm for {month_label} that the statutory compliance list "
             "given below has been completed to the best of my knowledge, except for the exceptions written below.",
             f"Total tasks: {counts.get('total', 0)} · Done (with evidence): {counts.get('done_evidence', 0)} · Done (on my word): "
             f"{counts.get('done_word', 0)} · Not applicable: {counts.get('na', 0)} · Pending / late: {counts.get('open', 0)} · "
             f"In another Assistant: {counts.get('linked', 0)}"]
    if exceptions:
        lines.append("Exceptions: " + "; ".join(exceptions[:30]))
    lines.append(CHECK_LINE)
    return "\n".join(lines)
