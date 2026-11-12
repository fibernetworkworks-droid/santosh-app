"""Cosec Sahayak rules (company secretary's desk): MCA21 V3 forms, due dates computed from HER FY / AGM / event dates,
additional-fee starters, SS-1 / SS-2 notice + quorum checks, board-meeting frequency, event -> filing map.

Everything here is "jaankari / draft": the CS / vakil / CA decides. Dates come only from her dates; a due date that rests on a
deadline (AGM not yet held) is marked `est` (andaaza). Research (23 Oct 2026, sources in WIRING.md):
- Companies Act 2013: s.96 AGM within 6 months of FY end (first AGM within 9 months of the first FY's end, OPC exempt, max 15
  months between AGMs); s.101 general meeting notice 21 clear days (shorter with members' consent); s.103 quorum; s.137 AOC-4
  within 30 days of the AGM (OPC: within 180 days of FY end); s.92 MGT-7 / MGT-7A (small companies + OPC) within 60 days of the
  AGM; s.139(1) ADT-1 within 15 days; s.173 board meetings (4 a year, gap <= 120 days; OPC / small / dormant: one in each half of
  the calendar year, gap >= 90 days); s.174 quorum 1/3 or 2; s.10A INC-20A 180 days; s.12 INC-22 30 days; s.90(4) BEN-2 30
  days; DIR-12 30 days; s.39(4) + PAS Rule 12 PAS-3 30 days; s.117 MGT-14 30 days; s.77 CHG-1 30 days; s.82 CHG-4 30 days;
  s.140(2) ADT-3 30 days; s.164(2) disqualification after 3 years of non-filing; s.118 minutes within 30 days.
- Small company (s.2(85) as amended, from 1 Dec 2025): paid-up <= Rs 10 crore AND turnover <= Rs 100 crore, not public /
  holding / subsidiary / Section 8 (taxguru.in, 7 Sep 2026).
- DIR-3 KYC: Companies (Appointment and Qualification of Directors) Amendment Rules 2025, G.S.R. 943(E) 31 Dec 2025, from 31 Mar
  2026: once every three financial years by 30 June; those who filed before are next due 30 June 2028; mobile / email / address
  change within 30 days; a deactivated DIN costs Rs 5,000 to restore (taxguru.in; ICAI CLCGC 2 Jan 2026).
- DPT-3 by 30 June; MSME-1 half-yearly 30 April / 31 October (order 22 Jan 2019 under s.405) (taxmann.com, upd. 21 Nov 2024).
- Additional fee: AOC-4 / MGT-7 / MGT-7A Rs 100 a day, no cap (since 1 Jul 2018); other forms a multiple of the normal fee:
  <= 15 days 1x, 16-30 2x, 31-60 4x, 61-90 6x, 91-180 10x, > 180 12x (calcguru.in, Aug 2026). LLP Form 8 / 11: Rs 100 a day
  (tallysolutions.com, 7 Apr 2026: Form 11 by 30 May, Form 8 by 30 Oct).
- ICSI SS-1 / SS-2 (revised, in force 1 Apr 2024): board notice + agenda + notes at least 7 days before; draft minutes to
  directors within 15 days, comments within 7 days, minutes entered within 30 days (taxguru.in SS-1 notes; mondaq.com 12 Mar 2024).
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta
from typing import Any

NEVER = [
    "Hoola files no form on MCA V3 itself: the login, DSC, fee and 'Submit' are done by you (or your director).",
    "No notice, minutes or filing card moves ahead without your tap.",
    "Hoola is not a lawyer / CS: every notice, minutes and calendar is a 'draft / information' - get it confirmed by a CS / lawyer / CA.",
    "Dates, fees and section numbers are never made up: worked out from your dates, else left blank; an estimate is marked 'estimate'.",
    "Only a director's DIN is kept; Aadhaar / PAN only as an ID Locker {id:...} reference.",
    "One client company's details never go to another client; DPDP 'forget' only by your tap.",
    "Money never moves: you pay the MCA fee on the portal yourself.",
]
DRAFT_LINE = "Draft / information - get it confirmed by a CS / lawyer / CA."

KINDS = {"private": "Private Limited", "opc": "One Person Company", "public": "Public Limited (unlisted)",
         "listed": "Listed company", "section8": "Section 8 company", "llp": "LLP"}

SMALL_PAIDUP = 10_00_00_000          # Rs 10 crore (from 1 Dec 2025)
SMALL_TURNOVER = 100_00_00_000       # Rs 100 crore
KYC_AMENDED_ON = date(2026, 3, 31)

# fee kinds: day100 = Rs 100 a day no cap ; multiple = slab multiple of the normal fee ; llp100 = Rs 100 a day ; kyc ; none
FORMS: dict[str, dict[str, Any]] = {
    "AGM": {"label": "Annual General Meeting", "law": "Companies Act 2013 s.96", "fee": "none",
            "what": "AGM - within 6 months of FY end (first AGM within 9 months); no AGM for an OPC"},
    "AOC-4": {"label": "Financial statements (AOC-4)", "law": "s.137", "fee": "day100", "what": "within 30 days of the AGM"},
    "AOC-4 OPC": {"label": "Financial statements OPC (AOC-4)", "law": "s.137 proviso", "fee": "day100",
                  "what": "within 180 days of FY end"},
    "MGT-7": {"label": "Annual return (MGT-7)", "law": "s.92", "fee": "day100", "what": "within 60 days of the AGM"},
    "MGT-7A": {"label": "Annual return - small company / OPC (MGT-7A)", "law": "s.92", "fee": "day100", "what": "within 60 days of the AGM"},
    "ADT-1": {"label": "Auditor appointment (ADT-1)", "law": "s.139(1)", "fee": "multiple", "what": "within 15 days of appointment / AGM"},
    "DPT-3": {"label": "Return of deposits / outstanding loans (DPT-3)", "law": "Deposits Rules 2014 r.16", "fee": "multiple",
              "what": "every year by 30 June (as at 31 March)"},
    "MSME-1": {"label": "MSME dues > 45 days (MSME-1)", "law": "s.405 order 22 Jan 2019", "fee": "multiple",
               "what": "half-yearly: Oct-Mar by 30 April, Apr-Sep by 31 October"},
    "DIR-3 KYC": {"label": "Director KYC (DIR-3 KYC)", "law": "Appointment Rules r.12A (G.S.R. 943(E), 31 Dec 2025)", "fee": "kyc",
                  "what": "once in three FYs, by 30 June"},
    "DIR-3 KYC WEB": {"label": "Director KYC update (mobile / email / address changed)", "law": "r.12A (2025 amendment)", "fee": "kyc",
                      "what": "within 30 days of the change"},
    "INC-20A": {"label": "Commencement of business (INC-20A)", "law": "s.10A", "fee": "multiple", "what": "within 180 days of incorporation"},
    "FIRST-AUDITOR": {"label": "First auditor appointment (Board)", "law": "s.139(6)", "fee": "none", "what": "within 30 days of incorporation"},
    "FIRST-BOARD": {"label": "First Board meeting", "law": "s.173(1)", "fee": "none", "what": "within 30 days of incorporation"},
    "BEN-2": {"label": "Significant beneficial owner (BEN-2)", "law": "s.90(4)", "fee": "multiple", "what": "within 30 days of receiving BEN-1"},
    "DIR-12": {"label": "Director / KMP appointment or resignation (DIR-12)", "law": "s.152 / s.168 / s.170(2)", "fee": "multiple",
               "what": "within 30 days of appointment / resignation"},
    "PAS-3": {"label": "Return of allotment (PAS-3)", "law": "s.39(4) + PAS Rules r.12", "fee": "multiple", "what": "within 30 days of allotment"},
    "INC-22": {"label": "Registered office changed (INC-22)", "law": "s.12(4)", "fee": "multiple", "what": "within 30 days of the change"},
    "MGT-14": {"label": "Resolution filing (MGT-14)", "law": "s.117", "fee": "multiple", "what": "within 30 days of the resolution"},
    "CHG-1": {"label": "Charge created / modified (CHG-1)", "law": "s.77", "fee": "multiple",
              "what": "within 30 days of the charge (later with extra fees - confirm with your CS)"},
    "CHG-4": {"label": "Charge satisfaction (CHG-4)", "law": "s.82", "fee": "multiple", "what": "within 30 days of repaying the loan"},
    "ADT-3": {"label": "Auditor resignation (ADT-3, filed by the auditor)", "law": "s.140(2)", "fee": "multiple",
              "what": "within 30 days of resignation"},
    "INC-23": {"label": "Registered office to another state (Regional Director)", "law": "s.13(4)", "fee": "none",
               "what": "special resolution + RD approval; work for a lawyer / CS"},
    "LLP-11": {"label": "LLP annual return (Form 11)", "law": "LLP Act s.35", "fee": "llp100", "what": "every year by 30 May"},
    "LLP-8": {"label": "LLP accounts + solvency (Form 8)", "law": "LLP Act s.34", "fee": "llp100", "what": "every year by 30 October"},
    "LLP-4": {"label": "LLP partner / designated partner changed (Form 4)", "law": "LLP Act s.25", "fee": "llp100",
              "what": "within 30 days of the change"},
}

FORM_ALIASES = {"aoc4": "AOC-4", "aoc-4": "AOC-4", "mgt7": "MGT-7", "mgt7a": "MGT-7A", "adt1": "ADT-1", "dpt3": "DPT-3", "msme1": "MSME-1",
                "dir3": "DIR-3 KYC", "dir3kyc": "DIR-3 KYC", "inc20a": "INC-20A", "ben2": "BEN-2", "dir12": "DIR-12", "pas3": "PAS-3",
                "inc22": "INC-22", "mgt14": "MGT-14", "chg1": "CHG-1", "chg4": "CHG-4", "adt3": "ADT-3", "form11": "LLP-11",
                "form8": "LLP-8", "form4": "LLP-4", "llp11": "LLP-11", "llp8": "LLP-8", "llp4": "LLP-4"}

# events her words trigger -> [(form, days, note)]
EVENTS: dict[str, dict[str, Any]] = {
    "director_appoint": {"label": "New director / KMP", "forms": [("DIR-12", 30, "keep DIR-2 consent + DIR-8 + MBP-1 on file")]},
    "director_resign": {"label": "Director / KMP resigned", "forms": [("DIR-12", 30, "the director may file DIR-11 themselves")]},
    "allotment": {"label": "Shares allotted", "forms": [("PAS-3", 30, "Board resolution + valuation / special resolution where needed")]},
    "transfer": {"label": "Share transfer", "forms": [], "note": "no MCA form; stamp duty on SH-4 (your state's rate) + update the register"},
    "ro_change_local": {"label": "Registered office - same city", "forms": [("INC-22", 30, "Board resolution + proof of the new address")]},
    "ro_change_city": {"label": "Registered office - same state, another city", "forms": [
        ("MGT-14", 30, "special resolution"), ("INC-22", 30, "if the ROC changes, RD approval too (lawyer / CS)")]},
    "ro_change_state": {"label": "Registered office - another state", "forms": [("INC-23", None, "special resolution + Regional Director")]},
    "charge_create": {"label": "Charge created on a loan", "forms": [("CHG-1", 30, "signed with the bank; then into the CHG register")]},
    "charge_satisfy": {"label": "Charge satisfied", "forms": [("CHG-4", 30, "keep the bank's NOC")]},
    "ben_declaration": {"label": "BEN-1 declaration received", "forms": [("BEN-2", 30, "register of SBO (BEN-3) too")]},
    "auditor_appoint": {"label": "Auditor appointed", "forms": [("ADT-1", 15, "auditor's consent + eligibility certificate")]},
    "auditor_resign": {"label": "Auditor resigned", "forms": [("ADT-3", 30, "the auditor files ADT-3; fill the casual vacancy within 30 days")]},
    "special_resolution": {"label": "Special resolution passed", "forms": [("MGT-14", 30, "explanatory statement + notice with it")]},
    "incorporation": {"label": "Company incorporated", "forms": [("INC-20A", 180, "proof that the subscribers' money reached the bank"),
                                                          ("FIRST-AUDITOR", 30, "the Board appoints the first auditor; ADT-1 too"),
                                                          ("FIRST-BOARD", 30, "first Board meeting")]},
    "partner_change": {"label": "LLP partner changed", "forms": [("LLP-4", 30, "if the LLP agreement changes, Form 3 too")]},
    "kyc_change": {"label": "Director's mobile / email / address changed", "forms": [("DIR-3 KYC WEB", 30, "")]},
}

_EVENT_WORDS: list[tuple[str, tuple[str, ...]]] = [
    ("director_resign", ("resign", "istifa", "isteefa", "chhod", "hat gaye", "cessation")),
    ("director_appoint", ("naya director", "new director", "director appoint", "director banaya", "add director", "kmp appoint",
                          "cfo appoint", "company secretary appoint")),
    ("allotment", ("allot", "allotment", "naye share", "shares diye", "rights issue", "preferential")),
    ("transfer", ("share transfer", "shares transfer", "sh-4")),
    ("ro_change_state", ("doosre state", "dusre state", "other state", "another state")),
    ("ro_change_city", ("doosre shehar", "dusre shehar", "other city", "another city")),
    ("ro_change_local", ("registered office", "office shift", "office badla", "address change", "pata badla")),
    ("charge_satisfy", ("loan chuka", "charge satisf", "loan close", "noc mila")),
    ("charge_create", ("charge", "hypothecation", "mortgage", "bank loan", "loan liya")),
    ("ben_declaration", ("ben-1", "ben 1", "beneficial owner", "sbo")),
    ("auditor_resign", ("auditor resign", "auditor ne istifa", "auditor chhod")),
    ("auditor_appoint", ("auditor appoint", "naya auditor", "auditor rakha")),
    ("special_resolution", ("special resolution",)),
    ("incorporation", ("incorporat", "company bani", "nayi company")),
    ("partner_change", ("partner", "designated partner")),
    ("kyc_change", ("mobile badla", "email badla", "number badla")),
]

# starter AGM / board agenda (her items replace these)
AGENDA = {
    "agm": ["Adopting the audited financial statements, Board's report and auditor's report (ordinary business)",
            "[If any: declaring a dividend]",
            "[Public company: re-appointment of the director retiring by rotation]",
            "[Auditor appointment / re-appointment, if the term ends at this AGM]"],
    "board": ["Reading and confirming the minutes of the last Board meeting", "Leave of absence (those not present)",
              "Noting directors' disclosures (MBP-1 / DIR-8) [first meeting of the year]", "[Today's business]"],
    "egm": ["[Special business - with an explanatory statement under s.102]"],
    "committee": ["[Committee business]"],
}
MEETING_KINDS = {"board": "Board meeting", "agm": "AGM", "egm": "EGM", "committee": "Committee meeting"}


# ---------------------------------------------------------------- small helpers
def norm_form(code: str) -> str:
    c = str(code or "").strip()
    if c.upper() in FORMS:
        return c.upper()
    k = re.sub(r"[^a-z0-9]", "", c.lower())
    return FORM_ALIASES.get(k, c.upper())


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def fy_label(end_year: int) -> str:
    return f"{end_year - 1}-{str(end_year)[2:]}"


def fy_end_year(label_or_date) -> int | None:
    if isinstance(label_or_date, date):
        d = label_or_date
        return d.year if d.month <= 3 else d.year + 1
    s = str(label_or_date or "").strip()
    m = re.match(r"^(\d{4})\s*[-/]\s*(\d{2,4})$", s)
    if m:
        a = int(m.group(1))
        return a + 1
    m = re.match(r"^(?:fy\s*)?(\d{4})$", s, re.I)
    return int(m.group(1)) if m else None


CIN_RE = re.compile(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")
LLPIN_RE = re.compile(r"^[A-Z]{3}-\d{4}$")
DIN_RE = re.compile(r"^\d{8}$")


def check_cin(v: str) -> str:
    c = re.sub(r"\s", "", str(v or "")).upper()
    if c and not CIN_RE.match(c):
        raise ValueError("A CIN has 21 characters (like U74999MH2020PTC123456).")
    return c


def check_llpin(v: str) -> str:
    c = re.sub(r"\s", "", str(v or "")).upper()
    if c and not LLPIN_RE.match(c):
        raise ValueError("An LLPIN looks like AAB-1234.")
    return c


def check_din(v: str) -> str:
    c = re.sub(r"\D", "", str(v or ""))
    if v and not DIN_RE.match(c):
        raise ValueError("A DIN / DPIN has 8 digits.")
    return c


def small_check(kind: str, paid_up: float | None, turnover: float | None, holding_or_sub: bool = False) -> dict[str, Any]:
    """Small company only for a private company (not Section 8 / holding / subsidiary) under both limits; unknown numbers = None."""
    if kind != "private" or holding_or_sub:
        why = {"opc": "an OPC is a separate category", "llp": "does not apply to an LLP"}.get(kind, "only a private company (not a holding / subsidiary / Section 8) can be small")
        return {"small": False, "why": why}
    if paid_up is None or turnover is None:
        return {"small": None, "why": "Both paid-up capital and last year's turnover are needed (small = up to Rs 10 crore / Rs 100 crore, from 1 Dec 2025)."}
    ok = paid_up <= SMALL_PAIDUP and turnover <= SMALL_TURNOVER
    return {"small": ok, "why": ("Within both limits: small company (MGT-7A, 2 Board meetings a year are enough)." if ok
                                 else "Above the limit: not a small company.")}


def mgt8_needed(kind: str, paid_up: float | None, turnover: float | None) -> bool:
    return kind == "listed" or (paid_up or 0) >= 10_00_00_000 or (turnover or 0) >= 50_00_00_000


def kyc_due(kyc_on: date | None, din_on: date | None = None) -> dict[str, Any]:
    """DIR-3 KYC once in three FYs by 30 June (from 31 Mar 2026). Filed before the amendment -> 30 June 2028."""
    if kyc_on:
        if kyc_on <= KYC_AMENDED_ON:
            return {"due": date(2028, 6, 30), "est": False, "basis": "KYC already done: next one by 30 June 2028"}
        e = fy_end_year(kyc_on)
        return {"due": date(e + 2, 6, 30), "est": True,
                "basis": f"KYC FY {fy_label(e)} done: 30 June after the third FY (estimate - confirm with your CS)"}
    if din_on:
        e = fy_end_year(din_on)
        return {"due": date(e + 1, 6, 30), "est": True,
                "basis": "DIN received, KYC date not known: taken as next 30 June (estimate - confirm with your CS)"}
    return {"due": None, "est": True, "basis": "Give the KYC / DIN date"}


def additional_fee(form: str, days_late: int, normal_fee: float | None = None) -> dict[str, Any]:
    """Additional fee STARTER (MCA fee calculator decides). Never invents the normal fee."""
    f = FORMS.get(norm_form(form), {})
    kind = f.get("fee", "none")
    d = max(0, int(days_late or 0))
    if d == 0:
        return {"days": 0, "amount": 0, "text": "On time: no extra fee."}
    if kind in ("day100", "llp100"):
        return {"days": d, "amount": 100 * d, "text": f"Estimate: Rs 100 x {d} days = Rs {100 * d:,} extra (no upper limit). Confirm with the MCA fee calculator."}
    if kind == "multiple":
        mult = 1 if d <= 15 else 2 if d <= 30 else 4 if d <= 60 else 6 if d <= 90 else 10 if d <= 180 else 12
        amt = round(mult * normal_fee, 2) if normal_fee else None
        return {"days": d, "multiple": mult, "amount": amt,
                "text": (f"Estimate: {mult} times the normal fee extra" + (f" = Rs {amt:,.0f}" if amt else " (the normal fee depends on capital; see the MCA fee calculator)")
                         + "; more for repeated delays.")}
    if kind == "kyc":
        return {"days": d, "amount": 5000, "text": "If late, the DIN is 'deactivated'; it is active again after KYC with Rs 5,000."}
    return {"days": d, "amount": None, "text": "No direct fee on this, but a delay can have effects / penalties - confirm with your CS."}


# ---------------------------------------------------------------- annual calendar (computed from HER dates)
def annual(kind: str, small: bool, fy_end: int, *, agm_on: date | None = None, last_agm: date | None = None,
           first_fy: bool = False, auditor_term_ends: bool = False, deposits: bool = True, msme_dues: bool = False,
           paid_up: float | None = None, turnover: float | None = None) -> list[dict[str, Any]]:
    """Annual filings for the FY ending 31 March of `fy_end`. Each row: form, period, due (date), basis, est, note."""
    end = date(fy_end, 3, 31)
    lab = fy_label(fy_end)
    rows: list[dict[str, Any]] = []
    if kind == "llp":
        rows.append({"form": "LLP-11", "period": f"FY {lab}", "due": date(fy_end, 5, 30), "basis": "30 May", "est": False, "note": ""})
        rows.append({"form": "LLP-8", "period": f"FY {lab}", "due": date(fy_end, 10, 30), "basis": "30 October", "est": False,
                     "note": "The designated partners sign the solvency statement"})
        return rows
    est_agm = agm_on is None
    if kind == "opc":
        aoc_due = end + timedelta(days=180)
        rows.append({"form": "AOC-4 OPC", "period": f"FY {lab}", "due": aoc_due, "basis": "FY end + 180 days", "est": False, "note": "no AGM for an OPC"})
        seen = add_months(end, 6)
        rows.append({"form": "MGT-7A", "period": f"FY {lab}", "due": seen + timedelta(days=60), "est": True,
                     "basis": "OPC: 30 Sep + 60 days instead of the AGM (estimate - confirm with your CS)", "note": ""})
    else:
        deadline = add_months(end, 9 if first_fy else 6)
        if last_agm and not first_fy:
            deadline = min(deadline, add_months(last_agm, 15))
        rows.append({"form": "AGM", "period": f"FY {lab}", "due": deadline, "est": False,
                     "basis": ("First AGM: FY end + 9 months" if first_fy else "FY end + 6 months (and within 15 months of the last AGM)"),
                     "note": "Once held, the following days count from the actual AGM date", "done_on": agm_on})
        base = agm_on or deadline
        tag = "AGM date" if not est_agm else "AGM deadline (changes once the actual AGM date is in)"
        rows.append({"form": "AOC-4", "period": f"FY {lab}", "due": base + timedelta(days=30), "est": est_agm, "basis": f"{tag} + 30 days", "note": ""})
        ret = "MGT-7A" if small else "MGT-7"
        note = "MGT-8: a PCS certificate too (paid-up >= Rs 10 crore / turnover >= Rs 50 crore / listed)" if mgt8_needed(kind, paid_up, turnover) else ""
        rows.append({"form": ret, "period": f"FY {lab}", "due": base + timedelta(days=60), "est": est_agm, "basis": f"{tag} + 60 days", "note": note})
        if auditor_term_ends:
            rows.append({"form": "ADT-1", "period": f"AGM {lab}", "due": base + timedelta(days=15), "est": est_agm,
                         "basis": f"{tag} + 15 days", "note": "The auditor's term ends at this AGM: new appointment / re-appointment"})
    if deposits:
        rows.append({"form": "DPT-3", "period": f"31 Mar {fy_end}", "due": date(fy_end, 6, 30), "basis": "30 June", "est": False,
                     "note": "Return of deposits / outstanding loans held by the company (exempt ones too) - if none, mark it 'not needed'"})
    if msme_dues:
        rows.append({"form": "MSME-1", "period": f"H2 {lab} (Oct-Mar)", "due": date(fy_end, 4, 30), "basis": "30 April", "est": False,
                     "note": "if an MSME supplier is owed for more than 45 days"})
        rows.append({"form": "MSME-1", "period": f"H1 {fy_label(fy_end + 1)} (Apr-Sep)", "due": date(fy_end, 10, 31), "basis": "31 October",
                     "est": False, "note": "if an MSME supplier is owed for more than 45 days"})
    return rows


def event_filings(kind: str, on: date, entity_kind: str = "private") -> list[dict[str, Any]]:
    e = EVENTS.get(kind)
    if not e:
        raise ValueError("event = " + " | ".join(EVENTS))
    out = []
    for form, days, note in e["forms"]:
        if entity_kind == "llp" and form in ("DIR-12", "PAS-3", "MGT-14", "INC-22", "AOC-4", "MGT-7"):
            continue
        out.append({"form": form, "due": (on + timedelta(days=days)) if days else None, "basis": (f"{e['label']} ({on.isoformat()}) + {days} days"
                                                                                                    if days else e["label"]),
                    "est": False, "note": note})
    return out


def guess_event(words: str) -> str:
    w = str(words or "").lower()
    for kind, keys in _EVENT_WORDS:
        if any(k in w for k in keys):
            return kind
    return ""


# ---------------------------------------------------------------- meetings: notice, quorum, frequency
def clear_days(sent: date, meeting: date, mode: str = "email") -> int:
    """Days between sending and the meeting, both excluded; post / courier counts as delivered 48 hours later (Rule 35(6))."""
    d = (meeting - sent).days - 1
    if mode in ("post", "courier", "speed_post"):
        d -= 2
    return d


def notice_need(kind: str) -> int:
    return 21 if kind in ("agm", "egm") else 7


def notice_check(kind: str, meeting: date, sent: date, mode: str = "email", shorter_consent: bool = False) -> dict[str, Any]:
    need = notice_need(kind)
    got = clear_days(sent, meeting, mode)
    ok = got >= need
    if ok:
        note = f"{got} clear days: fine ({need} needed)."
    elif shorter_consent:
        note = (f"Only {got} clear days ({need} needed): shorter notice - "
                + ("keep the members' written consent on file (AGM: majority in number + 95% of paid-up / voting power)."
                   if kind in ("agm", "egm") else "only for urgent business; if there is an independent director, at least one present; write 'shorter notice' in the notice."))
    else:
        note = f"Only {got} clear days: {need} needed. Move the meeting later or get shorter-notice consent."
    return {"need": need, "got": got, "ok": ok or shorter_consent, "short": not ok, "note": note,
            "latest_send": meeting - timedelta(days=need + 1 + (2 if mode in ("post", "courier", "speed_post") else 0))}


def quorum(kind: str, *, strength: int = 0, members: int = 0, entity_kind: str = "private", present: int = 0,
           interested: int = 0) -> dict[str, Any]:
    if kind in ("board", "committee"):
        need = max(2, math.ceil(strength / 3)) if strength else 2
        count = present - (0 if entity_kind in ("private", "opc") else interested)
        note = "1/3 or 2, whichever is more (s.174)" + ("; in a private company interested directors can be counted (revised SS-1)"
                                               if interested and entity_kind in ("private", "opc") else
                                               "; interested directors are not counted in the quorum" if interested else "")
    else:
        if entity_kind in ("private", "opc"):
            need, note = 2, "Private: 2 members (s.103)"
        elif members > 5000:
            need, note = 30, "Public, more than 5000 members: 30"
        elif members > 1000:
            need, note = 15, "Public, 1000-5000 members: 15"
        else:
            need, note = 5, "Public, up to 1000 members: 5"
        count = present
    return {"need": need, "present": count, "ok": count >= need, "note": note}


def board_frequency(meeting_dates: list[date], year: int, light: bool, single_director_opc: bool = False) -> list[str]:
    """s.173: 4 a calendar year, gap <= 120 days; OPC / small / dormant / startup: 1 in each half, gap >= 90 days."""
    ds = sorted(d for d in meeting_dates if d.year == year)
    issues: list[str] = []
    if single_director_opc:
        return issues
    if light:
        h1 = [d for d in ds if d.month <= 6]
        h2 = [d for d in ds if d.month >= 7]
        if not h1:
            issues.append(f"No Board meeting in the first half (Jan-Jun) of {year}.")
        if not h2:
            issues.append(f"No Board meeting in the second half (Jul-Dec) of {year} (so far).")
        if h1 and h2 and (h2[0] - h1[-1]).days < 90:
            issues.append("The meetings of the two halves need a 90-day gap.")
    else:
        if len(ds) < 4:
            issues.append(f"{len(ds)} Board meeting(s) in {year} (at least 4 needed).")
        for a, b in zip(ds, ds[1:]):
            if (b - a).days > 120:
                issues.append(f"{(b - a).days} days between {a.isoformat()} and {b.isoformat()} (no more than 120).")
    return issues


def next_board_by(last: date | None, light: bool) -> date | None:
    if not last or light:
        return None
    return last + timedelta(days=120)


def minutes_deadlines(kind: str, held: date) -> dict[str, date]:
    if kind in ("board", "committee"):
        return {"draft_by": held + timedelta(days=15), "comments_by": held + timedelta(days=22), "sign_by": held + timedelta(days=30)}
    return {"sign_by": held + timedelta(days=30)}
