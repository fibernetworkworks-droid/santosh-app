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
    "MCA V3 par koi form Hoola khud file nahi karta: login, DSC, fee aur 'Submit' aap (ya aapke director) khud karte hain.",
    "Koi notice, minutes ya filing card aapke tap ke bina aage nahi badhta.",
    "Hoola vakil / CS nahi: har notice, minutes, calendar 'draft / jaankari' hai - CS / vakil / CA se pakka karwaiye.",
    "Tareekh, fee, section number khud se nahi banta: aapki tareekh se hisaab, warna khaali; andaaza ho to 'andaaza' likha hota hai.",
    "Director ka sirf DIN rakha jaata hai; Aadhaar / PAN sirf Pehchaan Locker ke {id:...} reference se.",
    "Ek client company ki baat doosre client ko kabhi nahi; DPDP par 'bhool jao' aapke tap se.",
    "Paise kabhi nahi chalte: MCA fee aap portal par khud bharti hain.",
]
DRAFT_LINE = "Draft / jaankari - CS / vakil / CA se pakka karwaiye."

KINDS = {"private": "Private Limited", "opc": "One Person Company", "public": "Public Limited (unlisted)",
         "listed": "Listed company", "section8": "Section 8 company", "llp": "LLP"}

SMALL_PAIDUP = 10_00_00_000          # Rs 10 crore (from 1 Dec 2025)
SMALL_TURNOVER = 100_00_00_000       # Rs 100 crore
KYC_AMENDED_ON = date(2026, 3, 31)

# fee kinds: day100 = Rs 100 a day no cap ; multiple = slab multiple of the normal fee ; llp100 = Rs 100 a day ; kyc ; none
FORMS: dict[str, dict[str, Any]] = {
    "AGM": {"label": "Annual General Meeting", "law": "Companies Act 2013 s.96", "fee": "none",
            "what": "AGM - FY khatam hone ke 6 mahine mein (pehla AGM 9 mahine mein); OPC ko AGM nahi"},
    "AOC-4": {"label": "Financial statements (AOC-4)", "law": "s.137", "fee": "day100", "what": "AGM ke 30 din mein"},
    "AOC-4 OPC": {"label": "Financial statements OPC (AOC-4)", "law": "s.137 proviso", "fee": "day100",
                  "what": "FY khatam hone ke 180 din mein"},
    "MGT-7": {"label": "Annual return (MGT-7)", "law": "s.92", "fee": "day100", "what": "AGM ke 60 din mein"},
    "MGT-7A": {"label": "Annual return - small company / OPC (MGT-7A)", "law": "s.92", "fee": "day100", "what": "AGM ke 60 din mein"},
    "ADT-1": {"label": "Auditor appointment (ADT-1)", "law": "s.139(1)", "fee": "multiple", "what": "appointment / AGM ke 15 din mein"},
    "DPT-3": {"label": "Return of deposits / outstanding loans (DPT-3)", "law": "Deposits Rules 2014 r.16", "fee": "multiple",
              "what": "har saal 30 June tak (31 March ke hisaab se)"},
    "MSME-1": {"label": "MSME dues > 45 din (MSME-1)", "law": "s.405 order 22 Jan 2019", "fee": "multiple",
               "what": "chhamahi: Oct-Mar ka 30 April tak, Apr-Sep ka 31 October tak"},
    "DIR-3 KYC": {"label": "Director KYC (DIR-3 KYC)", "law": "Appointment Rules r.12A (G.S.R. 943(E), 31 Dec 2025)", "fee": "kyc",
                  "what": "teen FY mein ek baar, 30 June tak"},
    "DIR-3 KYC WEB": {"label": "Director KYC update (mobile / email / pata badla)", "law": "r.12A (2025 amendment)", "fee": "kyc",
                      "what": "badlav ke 30 din mein"},
    "INC-20A": {"label": "Commencement of business (INC-20A)", "law": "s.10A", "fee": "multiple", "what": "incorporation ke 180 din mein"},
    "FIRST-AUDITOR": {"label": "Pehla auditor appoint (Board)", "law": "s.139(6)", "fee": "none", "what": "incorporation ke 30 din mein"},
    "FIRST-BOARD": {"label": "Pehli Board meeting", "law": "s.173(1)", "fee": "none", "what": "incorporation ke 30 din mein"},
    "BEN-2": {"label": "Significant beneficial owner (BEN-2)", "law": "s.90(4)", "fee": "multiple", "what": "BEN-1 milne ke 30 din mein"},
    "DIR-12": {"label": "Director / KMP appoint ya resign (DIR-12)", "law": "s.152 / s.168 / s.170(2)", "fee": "multiple",
               "what": "appointment / resignation ke 30 din mein"},
    "PAS-3": {"label": "Return of allotment (PAS-3)", "law": "s.39(4) + PAS Rules r.12", "fee": "multiple", "what": "allotment ke 30 din mein"},
    "INC-22": {"label": "Registered office badla (INC-22)", "law": "s.12(4)", "fee": "multiple", "what": "badlav ke 30 din mein"},
    "MGT-14": {"label": "Resolution filing (MGT-14)", "law": "s.117", "fee": "multiple", "what": "resolution ke 30 din mein"},
    "CHG-1": {"label": "Charge banaya / badla (CHG-1)", "law": "s.77", "fee": "multiple",
              "what": "charge ke 30 din mein (aage extra fee ke saath - CS se pakka)"},
    "CHG-4": {"label": "Charge satisfaction (CHG-4)", "law": "s.82", "fee": "multiple", "what": "loan chukne ke 30 din mein"},
    "ADT-3": {"label": "Auditor resignation (ADT-3, auditor file karta hai)", "law": "s.140(2)", "fee": "multiple",
              "what": "resignation ke 30 din mein"},
    "INC-23": {"label": "Registered office doosre state mein (Regional Director)", "law": "s.13(4)", "fee": "none",
               "what": "special resolution + RD ki manzoori; vakil / CS ka kaam"},
    "LLP-11": {"label": "LLP annual return (Form 11)", "law": "LLP Act s.35", "fee": "llp100", "what": "har saal 30 May tak"},
    "LLP-8": {"label": "LLP accounts + solvency (Form 8)", "law": "LLP Act s.34", "fee": "llp100", "what": "har saal 30 October tak"},
    "LLP-4": {"label": "LLP partner / designated partner badla (Form 4)", "law": "LLP Act s.25", "fee": "llp100",
              "what": "badlav ke 30 din mein"},
}

FORM_ALIASES = {"aoc4": "AOC-4", "aoc-4": "AOC-4", "mgt7": "MGT-7", "mgt7a": "MGT-7A", "adt1": "ADT-1", "dpt3": "DPT-3", "msme1": "MSME-1",
                "dir3": "DIR-3 KYC", "dir3kyc": "DIR-3 KYC", "inc20a": "INC-20A", "ben2": "BEN-2", "dir12": "DIR-12", "pas3": "PAS-3",
                "inc22": "INC-22", "mgt14": "MGT-14", "chg1": "CHG-1", "chg4": "CHG-4", "adt3": "ADT-3", "form11": "LLP-11",
                "form8": "LLP-8", "form4": "LLP-4", "llp11": "LLP-11", "llp8": "LLP-8", "llp4": "LLP-4"}

# events her words trigger -> [(form, days, note)]
EVENTS: dict[str, dict[str, Any]] = {
    "director_appoint": {"label": "Naya director / KMP", "forms": [("DIR-12", 30, "DIR-2 consent + DIR-8 + MBP-1 file mein rakhiye")]},
    "director_resign": {"label": "Director / KMP ne istifa diya", "forms": [("DIR-12", 30, "director chahe to DIR-11 khud bhar sakta hai")]},
    "allotment": {"label": "Shares allot hue", "forms": [("PAS-3", 30, "Board resolution + valuation / special resolution jahan zaroori ho")]},
    "transfer": {"label": "Share transfer", "forms": [], "note": "MCA form nahi; SH-4 par stamp duty (aapke state ka rate) + register badlo"},
    "ro_change_local": {"label": "Registered office - usi shehar mein", "forms": [("INC-22", 30, "Board resolution + naye pate ka saboot")]},
    "ro_change_city": {"label": "Registered office - usi state, doosra shehar", "forms": [
        ("MGT-14", 30, "special resolution"), ("INC-22", 30, "ROC badle to RD ki manzoori bhi (vakil / CS)")]},
    "ro_change_state": {"label": "Registered office - doosra state", "forms": [("INC-23", None, "special resolution + Regional Director")]},
    "charge_create": {"label": "Loan par charge bana", "forms": [("CHG-1", 30, "bank ke saath sign; aage CHG register mein")]},
    "charge_satisfy": {"label": "Charge chuka", "forms": [("CHG-4", 30, "bank ka NOC rakhiye")]},
    "ben_declaration": {"label": "BEN-1 declaration mili", "forms": [("BEN-2", 30, "register of SBO (BEN-3) bhi")]},
    "auditor_appoint": {"label": "Auditor appoint hua", "forms": [("ADT-1", 15, "auditor ka consent + eligibility certificate")]},
    "auditor_resign": {"label": "Auditor ne istifa diya", "forms": [("ADT-3", 30, "ADT-3 auditor bharta hai; casual vacancy 30 din mein bharo")]},
    "special_resolution": {"label": "Special resolution pass hua", "forms": [("MGT-14", 30, "explanatory statement + notice saath")]},
    "incorporation": {"label": "Company bani", "forms": [("INC-20A", 180, "subscribers ka paisa bank mein aane ka saboot"),
                                                          ("FIRST-AUDITOR", 30, "Board pehla auditor rakhe; ADT-1 bhi"),
                                                          ("FIRST-BOARD", 30, "pehli Board meeting")]},
    "partner_change": {"label": "LLP partner badla", "forms": [("LLP-4", 30, "LLP agreement badle to Form 3 bhi")]},
    "kyc_change": {"label": "Director ka mobile / email / pata badla", "forms": [("DIR-3 KYC WEB", 30, "")]},
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
    "agm": ["Audited financial statements, Board's report aur auditor's report ko apnaana (ordinary business)",
            "[Dividend ho to: dividend declare karna]",
            "[Public company: rotation se retire hone wale director ki re-appointment]",
            "[Auditor ka appointment / re-appointment, agar is AGM par term khatam]"],
    "board": ["Pichhli Board meeting ke minutes padhna aur pakka karna", "Leave of absence (jo nahi aaye)",
              "Directors ke disclosures (MBP-1 / DIR-8) note karna [saal ki pehli meeting]", "[Aaj ka kaam]"],
    "egm": ["[Special business - explanatory statement s.102 ke saath]"],
    "committee": ["[Committee ka kaam]"],
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
        raise ValueError("CIN 21 characters ka hota hai (jaise U74999MH2020PTC123456).")
    return c


def check_llpin(v: str) -> str:
    c = re.sub(r"\s", "", str(v or "")).upper()
    if c and not LLPIN_RE.match(c):
        raise ValueError("LLPIN jaise AAB-1234 hota hai.")
    return c


def check_din(v: str) -> str:
    c = re.sub(r"\D", "", str(v or ""))
    if v and not DIN_RE.match(c):
        raise ValueError("DIN / DPIN 8 ankon ka hota hai.")
    return c


def small_check(kind: str, paid_up: float | None, turnover: float | None, holding_or_sub: bool = False) -> dict[str, Any]:
    """Small company only for a private company (not Section 8 / holding / subsidiary) under both limits; unknown numbers = None."""
    if kind != "private" or holding_or_sub:
        why = {"opc": "OPC alag category hai", "llp": "LLP par lagoo nahi"}.get(kind, "sirf private company (holding / subsidiary / Section 8 nahi) small ho sakti hai")
        return {"small": False, "why": why}
    if paid_up is None or turnover is None:
        return {"small": None, "why": "Paid-up capital aur pichhle saal ka turnover dono chahiye (small = Rs 10 crore / Rs 100 crore tak, 1 Dec 2025 se)."}
    ok = paid_up <= SMALL_PAIDUP and turnover <= SMALL_TURNOVER
    return {"small": ok, "why": ("Dono seema ke andar: small company (MGT-7A, saal mein 2 Board meeting kaafi)." if ok
                                 else "Seema se upar: small company nahi.")}


def mgt8_needed(kind: str, paid_up: float | None, turnover: float | None) -> bool:
    return kind == "listed" or (paid_up or 0) >= 10_00_00_000 or (turnover or 0) >= 50_00_00_000


def kyc_due(kyc_on: date | None, din_on: date | None = None) -> dict[str, Any]:
    """DIR-3 KYC once in three FYs by 30 June (from 31 Mar 2026). Filed before the amendment -> 30 June 2028."""
    if kyc_on:
        if kyc_on <= KYC_AMENDED_ON:
            return {"due": date(2028, 6, 30), "est": False, "basis": "Pehle KYC ho chuka: agla 30 June 2028 tak"}
        e = fy_end_year(kyc_on)
        return {"due": date(e + 2, 6, 30), "est": True,
                "basis": f"KYC FY {fy_label(e)} mein hua: teesre FY ke baad 30 June (andaaza - CS se pakka)"}
    if din_on:
        e = fy_end_year(din_on)
        return {"due": date(e + 1, 6, 30), "est": True,
                "basis": "DIN mila, KYC ki tareekh nahi pata: agle 30 June tak maan liya (andaaza - CS se pakka)"}
    return {"due": None, "est": True, "basis": "KYC / DIN ki tareekh batao"}


def additional_fee(form: str, days_late: int, normal_fee: float | None = None) -> dict[str, Any]:
    """Additional fee STARTER (MCA fee calculator decides). Never invents the normal fee."""
    f = FORMS.get(norm_form(form), {})
    kind = f.get("fee", "none")
    d = max(0, int(days_late or 0))
    if d == 0:
        return {"days": 0, "amount": 0, "text": "Samay par: koi extra fee nahi."}
    if kind in ("day100", "llp100"):
        return {"days": d, "amount": 100 * d, "text": f"Andaaza: Rs 100 x {d} din = Rs {100 * d:,} extra (koi upar ki seema nahi). MCA fee calculator se pakka."}
    if kind == "multiple":
        mult = 1 if d <= 15 else 2 if d <= 30 else 4 if d <= 60 else 6 if d <= 90 else 10 if d <= 180 else 12
        amt = round(mult * normal_fee, 2) if normal_fee else None
        return {"days": d, "multiple": mult, "amount": amt,
                "text": (f"Andaaza: normal fee ka {mult} guna extra" + (f" = Rs {amt:,.0f}" if amt else " (normal fee capital par nirbhar; MCA fee calculator dekhiye)")
                         + "; baar baar der par aur zyada.")}
    if kind == "kyc":
        return {"days": d, "amount": 5000, "text": "Der hui to DIN 'deactivated'; KYC ke saath Rs 5,000 dekar wapas chalu."}
    return {"days": d, "amount": None, "text": "Is par seedhi fee nahi, par der ka asar / penalty ho sakta hai - CS se pakka."}


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
                     "note": "Solvency statement designated partners sign karte hain"})
        return rows
    est_agm = agm_on is None
    if kind == "opc":
        aoc_due = end + timedelta(days=180)
        rows.append({"form": "AOC-4 OPC", "period": f"FY {lab}", "due": aoc_due, "basis": "FY khatam + 180 din", "est": False, "note": "OPC ko AGM nahi"})
        seen = add_months(end, 6)
        rows.append({"form": "MGT-7A", "period": f"FY {lab}", "due": seen + timedelta(days=60), "est": True,
                     "basis": "OPC: AGM ki jagah 30 Sep + 60 din (andaaza - CS se pakka)", "note": ""})
    else:
        deadline = add_months(end, 9 if first_fy else 6)
        if last_agm and not first_fy:
            deadline = min(deadline, add_months(last_agm, 15))
        rows.append({"form": "AGM", "period": f"FY {lab}", "due": deadline, "est": False,
                     "basis": ("Pehla AGM: FY khatam + 9 mahine" if first_fy else "FY khatam + 6 mahine (aur pichhle AGM se 15 mahine tak)"),
                     "note": "Held ho gaya to AGM ki asli tareekh se aage ke din gine jaate hain", "done_on": agm_on})
        base = agm_on or deadline
        tag = "AGM ki tareekh" if not est_agm else "AGM ki aakhri tareekh (asli AGM tareekh aate hi badlegi)"
        rows.append({"form": "AOC-4", "period": f"FY {lab}", "due": base + timedelta(days=30), "est": est_agm, "basis": f"{tag} + 30 din", "note": ""})
        ret = "MGT-7A" if small else "MGT-7"
        note = "MGT-8: PCS ka certificate bhi (paid-up >= Rs 10 crore / turnover >= Rs 50 crore / listed)" if mgt8_needed(kind, paid_up, turnover) else ""
        rows.append({"form": ret, "period": f"FY {lab}", "due": base + timedelta(days=60), "est": est_agm, "basis": f"{tag} + 60 din", "note": note})
        if auditor_term_ends:
            rows.append({"form": "ADT-1", "period": f"AGM {lab}", "due": base + timedelta(days=15), "est": est_agm,
                         "basis": f"{tag} + 15 din", "note": "Auditor ka term isi AGM par khatam: naya / dobara appointment"})
    if deposits:
        rows.append({"form": "DPT-3", "period": f"31 Mar {fy_end}", "due": date(fy_end, 6, 30), "basis": "30 June", "est": False,
                     "note": "Deposit / company ke paas outstanding loans (exempt bhi) ki return - na ho to 'zaroori nahi' kijiye"})
    if msme_dues:
        rows.append({"form": "MSME-1", "period": f"H2 {lab} (Oct-Mar)", "due": date(fy_end, 4, 30), "basis": "30 April", "est": False,
                     "note": "MSME supplier ka 45 din se zyada baaki ho to"})
        rows.append({"form": "MSME-1", "period": f"H1 {fy_label(fy_end + 1)} (Apr-Sep)", "due": date(fy_end, 10, 31), "basis": "31 October",
                     "est": False, "note": "MSME supplier ka 45 din se zyada baaki ho to"})
    return rows


def event_filings(kind: str, on: date, entity_kind: str = "private") -> list[dict[str, Any]]:
    e = EVENTS.get(kind)
    if not e:
        raise ValueError("event = " + " | ".join(EVENTS))
    out = []
    for form, days, note in e["forms"]:
        if entity_kind == "llp" and form in ("DIR-12", "PAS-3", "MGT-14", "INC-22", "AOC-4", "MGT-7"):
            continue
        out.append({"form": form, "due": (on + timedelta(days=days)) if days else None, "basis": (f"{e['label']} ({on.isoformat()}) + {days} din"
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
        note = f"{got} clear din: theek ({need} chahiye)."
    elif shorter_consent:
        note = (f"Sirf {got} clear din ({need} chahiye): shorter notice - "
                + ("members ki likhit sahmati (AGM: number mein majority + 95% paid-up / voting power) file mein rakhiye."
                   if kind in ("agm", "egm") else "zaroori kaam ho; independent director ho to kam se kam ek maujood; notice mein 'shorter notice' likhiye."))
    else:
        note = f"Sirf {got} clear din: {need} chahiye. Meeting aage badhaiye ya shorter-notice sahmati lijiye."
    return {"need": need, "got": got, "ok": ok or shorter_consent, "short": not ok, "note": note,
            "latest_send": meeting - timedelta(days=need + 1 + (2 if mode in ("post", "courier", "speed_post") else 0))}


def quorum(kind: str, *, strength: int = 0, members: int = 0, entity_kind: str = "private", present: int = 0,
           interested: int = 0) -> dict[str, Any]:
    if kind in ("board", "committee"):
        need = max(2, math.ceil(strength / 3)) if strength else 2
        count = present - (0 if entity_kind in ("private", "opc") else interested)
        note = "1/3 ya 2, jo zyada (s.174)" + ("; private company mein interested director gine ja sakte hain (revised SS-1)"
                                               if interested and entity_kind in ("private", "opc") else
                                               "; interested director quorum mein nahi gine jaate" if interested else "")
    else:
        if entity_kind in ("private", "opc"):
            need, note = 2, "Private: 2 members (s.103)"
        elif members > 5000:
            need, note = 30, "Public, 5000 se zyada members: 30"
        elif members > 1000:
            need, note = 15, "Public, 1000-5000 members: 15"
        else:
            need, note = 5, "Public, 1000 tak members: 5"
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
            issues.append(f"{year} ke pehle chhamahi (Jan-Jun) mein Board meeting nahi.")
        if not h2:
            issues.append(f"{year} ke doosre chhamahi (Jul-Dec) mein Board meeting nahi (abhi tak).")
        if h1 and h2 and (h2[0] - h1[-1]).days < 90:
            issues.append("Dono chhamahi ki meetings mein 90 din ka gap chahiye.")
    else:
        if len(ds) < 4:
            issues.append(f"{year} mein {len(ds)} Board meeting (kam se kam 4 chahiye).")
        for a, b in zip(ds, ds[1:]):
            if (b - a).days > 120:
                issues.append(f"{a.isoformat()} aur {b.isoformat()} ke beech {(b - a).days} din (120 se zyada nahi).")
    return issues


def next_board_by(last: date | None, light: bool) -> date | None:
    if not last or light:
        return None
    return last + timedelta(days=120)


def minutes_deadlines(kind: str, held: date) -> dict[str, date]:
    if kind in ("board", "committee"):
        return {"draft_by": held + timedelta(days=15), "comments_by": held + timedelta(days=22), "sign_by": held + timedelta(days=30)}
    return {"sign_by": held + timedelta(days=30)}
