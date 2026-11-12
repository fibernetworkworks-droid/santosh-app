"""Vakil Sahayak rules: CNR, case numbers, cause-list / case-status parsing (text she pastes from the official eCourts app /
court site), limitation arithmetic (Limitation Act 1963 ss.4 / 12 with HER inputs), document checklists, draft templates.

Nothing here is legal advice. Every period below is a STARTER from the bare text we read (sources in SOURCES); the result is
always "andaaza, vakil se pakka". A limitation the table doesn't know is asked from her, never guessed."""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any

CHECK = "This is an estimate / draft, not advice: have the advocate confirm it."
NEVER = [
    "Hoola is not a lawyer: no legal advice, only the diary, dates and drafts.",
    "Court filings, notices / letters / messages to the client / other side, fee requests: only by your tap (card).",
    "Never takes or sends money itself. You pay court fees / e-stamp / ePay yourself.",
    "eCourts / court sites only by official routes: you paste text or a file from the app / site, Hoola reads it. No scraping.",
    "Sections / citations only from a source that was read (with the link); otherwise '[citation needed]'.",
    "Never share one client's matters with another client. Aadhaar / PAN only by ID Locker {id:...}.",
]

SOURCES = [
    {"what": "Limitation Act 1963 Schedule (Arts 19, 21, 54, 55, 58, 65, 113-118, 123, 124, 131, 136, 137) as printed",
     "url": "https://advocatetanmoy.com/period-of-limitation-under-the-limitation-act-1963/", "read": "2026-10-23"},
    {"what": "eCourts Services Mobile App 4.0 manual (CNR search, case status, cause list, orders)",
     "url": "https://tshc.gov.in/documents/admin_2026_05_25T13_31_22.pdf", "read": "2026-10-23"},
    {"what": "eCourts SMS: 'ECOURTS <CNR>' to 9766899899; SMS / email alerts at each stage; e-filing",
     "url": "https://mphc.gov.in/php/hc/front/ECOURTS.html", "read": "2026-10-23"},
]

OFFICIAL = {
    "case_status": "https://services.ecourts.gov.in/",
    "efiling": "https://efiling.ecourts.gov.in/",
    "njdg": "https://njdg.ecourts.gov.in/",
    "sci": "https://www.sci.gov.in/",
    "app": "eCourts Services app (Android / iOS, e-Committee Supreme Court)",
    "sms": "SMS 'ECOURTS <CNR>' to 9766899899",
}

# ---------------------------------------------------------------- small parsers
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["sept"] = 9


def num(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("rs", "").replace("₹", "").strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(k|hazar|hazaar|thousand|lakh|lac|l|cr|crore)?$", s)
    if not m:
        return None
    x = float(m.group(1))
    mult = {"k": 1e3, "hazar": 1e3, "hazaar": 1e3, "thousand": 1e3, "lakh": 1e5, "lac": 1e5, "l": 1e5, "cr": 1e7, "crore": 1e7}
    return x * mult.get(m.group(2) or "", 1)


def parse_date(v, ref: date | None = None) -> date | None:
    """'2026-11-15', '15-11-2026', '15/11/26', '15th November 2026', '15 Nov 2026', 'November 15, 2026'."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s, flags=re.I)
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y", "%d.%m.%y"):
        try:
            return datetime.strptime(s[:10] if f == "%Y-%m-%d" else s.split()[0], f).date()
        except (ValueError, IndexError):
            pass
    m = re.search(r"(\d{1,2})[\s\-]+([A-Za-z]{3,9})[,\s\-]+(\d{4})", s)
    if m and m.group(2).lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})", s)
    if m and m.group(1).lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
        except ValueError:
            return None
    return None


def find_dates(text: str) -> list[date]:
    out = []
    for m in re.finditer(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b|\b\d{1,2}(?:st|nd|rd|th)?[\s\-]+[A-Za-z]{3,9}[,\s\-]+\d{4}\b", text or ""):
        d = parse_date(m.group(0))
        if d:
            out.append(d)
    return out


CNR_RE = re.compile(r"\b([A-Z]{2})([A-Z]{2})(\d{2})(\d{6})((?:19|20)\d{2})\b")


def cnr(v) -> dict[str, Any] | None:
    """CNR = 16 characters: state (2 letters) + district (2 letters) + establishment (2 digits) + case no (6) + year (4)."""
    s = re.sub(r"[\s\-]", "", str(v or "")).upper()
    m = CNR_RE.fullmatch(s)
    if not m:
        return None
    return {"cnr": s, "state": m.group(1), "district": m.group(2), "establishment": m.group(3), "serial": int(m.group(4)),
            "year": int(m.group(5))}


CASE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z.()\s]{0,24}?)\s*[\s/.\-]\s*(?:No\.?\s*)?(\d{1,7})\s*/\s*((?:19|20)\d{2})(?!\d)")


def case_key(case_type: str, no, year) -> str:
    t = re.sub(r"[^A-Z]", "", str(case_type or "").upper())
    try:
        n = int(str(no).strip())
        y = int(str(year).strip())
    except (TypeError, ValueError):
        return ""
    return f"{t}|{n}|{y}" if n and y else ""


def case_numbers(text: str) -> list[dict[str, Any]]:
    out = []
    for m in CASE_RE.finditer(text or ""):
        t = re.sub(r"\s+", " ", m.group(1)).strip(" .")
        if len(re.sub(r"[^A-Za-z]", "", t)) < 1:
            continue
        out.append({"type": t, "no": int(m.group(2)), "year": int(m.group(3)), "key": case_key(t, m.group(2), m.group(3)),
                    "loose": f"{int(m.group(2))}|{int(m.group(3))}", "span": m.span()})
    return out


def parse_case_ref(text: str) -> dict[str, Any]:
    """Her words 'RCS 123/2024', 'Cri.M.A. 456/2025' or a CNR."""
    c = cnr(text)
    if c:
        return {"cnr": c["cnr"]}
    cs = case_numbers(text)
    if cs:
        x = cs[0]
        return {"case_type": x["type"], "case_no": str(x["no"]), "case_year": str(x["year"])}
    return {}


# ---------------------------------------------------------------- case status (pasted from eCourts / court site)
STATUS_KEYS = {
    "cnr": r"CNR\s*(?:Number|No\.?)",
    "case_type": r"Case\s*Type",
    "filing": r"Filing\s*(?:Number|No\.?)",
    "filing_date": r"Filing\s*Date",
    "registration": r"Registration\s*(?:Number|No\.?)",
    "registration_date": r"Registration\s*Date",
    "first_date": r"First\s*Hearing\s*Date",
    "next_date": r"Next\s*(?:Hearing\s*)?Date",
    "stage": r"(?:Case\s*Stage|Stage\s*of\s*Case|Stage)",
    "court": r"Court\s*(?:Number\s*and\s*Judge|No\.?\s*(?:&|and)\s*Judge|Number)",
    "decision_date": r"Decision\s*Date",
    "status": r"Case\s*Status|Nature\s*of\s*Disposal",
    "petitioner": r"Petitioner(?:\s*and\s*Advocate)?",
    "respondent": r"Respondent(?:\s*and\s*Advocate)?",
    "acts": r"Under\s*Act(?:\(s\))?|Acts?",
}


def parse_status(text: str) -> dict[str, Any]:
    """Key: value lines of a case-status page / app screen she copied. Returns only what is written."""
    t = text or ""
    out: dict[str, Any] = {}
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    for key, pat in STATUS_KEYS.items():
        for i, ln in enumerate(lines):
            m = re.match(rf"^(?:{pat})\s*[:\-–]\s*(.*)$", ln, re.I)
            if m is None and re.fullmatch(rf"(?:{pat})\s*:?", ln, re.I) and i + 1 < len(lines):
                val = lines[i + 1]
            elif m is not None:
                val = m.group(1)
            else:
                continue
            val = val.strip()
            if val and key not in out:
                out[key] = val[:300]
                break
    for k in ("filing_date", "registration_date", "first_date", "next_date", "decision_date"):
        if k in out:
            d = parse_date(out[k])
            out[k] = d.isoformat() if d else ""
            if not out[k]:
                out.pop(k)
    if "cnr" in out:
        c = cnr(out["cnr"])
        if c:
            out["cnr"] = c["cnr"]
        else:
            out.pop("cnr")
    if "cnr" not in out:
        m = CNR_RE.search(t.upper())
        if m:
            out["cnr"] = m.group(0)
    for k in ("registration", "filing"):
        if k in out:
            m = re.search(r"(\d{1,7})\s*/\s*((?:19|20)\d{2})", out[k])
            if m:
                out[k + "_no"], out[k + "_year"] = str(int(m.group(1))), m.group(2)
    # history rows: "Judge  15-10-2026  20-11-2026  Evidence"
    hist = []
    for ln in lines:
        ds = find_dates(ln)
        if len(ds) >= 2 and not re.match(r"^(?:%s)" % "|".join(STATUS_KEYS.values()), ln, re.I):
            purpose = re.sub(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9},?\s+\d{4}\b", " ", ln)
            purpose = re.sub(r"\s{2,}", " ", purpose).strip(" -|\t")
            hist.append({"on": ds[0].isoformat(), "next": ds[1].isoformat(), "purpose": purpose[-80:]})
    if hist:
        out["history"] = hist[-30:]
    disposed = re.search(r"\b(disposed|decided|dismissed|allowed|withdrawn|compromised)\b", out.get("status", "") + " " + out.get("stage", ""), re.I)
    out["disposed"] = bool(disposed) or bool(out.get("decision_date"))
    return out


# ---------------------------------------------------------------- cause list (pasted)
def parse_cause_list(text: str, on: date | None = None) -> dict[str, Any]:
    """Cause list text -> {date, court, items [{item, case_type, no, year, key, parties, line}]}."""
    t = text or ""
    head = "\n".join(t.splitlines()[:8])
    d = on
    if d is None:
        m = re.search(r"(?:cause\s*list|board|date|dated|for)\D{0,20}(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9},?\s+\d{4})",
                      head, re.I)
        if m:
            d = parse_date(m.group(1))
        if d is None:
            ds = find_dates(head)
            d = ds[0] if ds else None
    court = ""
    m = re.search(r"(court\s*(?:room|hall|no\.?)?\s*[:\-]?\s*\d+[^\n]{0,60})", head, re.I)
    if m:
        court = m.group(1).strip()[:100]
    items, cur = [], None
    for ln in t.splitlines():
        s = ln.strip()
        if not s:
            continue
        cs = case_numbers(s)
        if cs:
            im = re.match(r"^\(?(\d{1,4})[).\s]", s)
            x = cs[0]
            parties = s[x["span"][1]:].strip(" -:|,\t")
            cur = {"item": int(im.group(1)) if im else None, "case_type": x["type"], "no": x["no"], "year": x["year"],
                   "key": x["key"], "loose": x["loose"], "parties": parties[:200], "line": s[:300]}
            items.append(cur)
        elif cur is not None and re.search(r"\b(vs?\.?|versus|v/s)\b", s, re.I) and not re.search(r"\b(vs?\.?|versus|v/s)\b", cur["parties"], re.I):
            cur["parties"] = (cur["parties"] + " " + s).strip()[:200]
    return {"date": d.isoformat() if d else "", "court": court, "items": items}


def words_of(name: str) -> set[str]:
    stop = {"the", "and", "ors", "anr", "others", "another", "smt", "shri", "mr", "mrs", "ms", "dr", "pvt", "ltd", "state", "of", "vs",
            "v", "versus", "through", "thr"}
    return {w for w in re.findall(r"[a-z]{3,}", (name or "").lower()) if w not in stop}


# ---------------------------------------------------------------- limitation (starter table + arithmetic)
# unit: d = days, m = months, y = years. src = what the bare text says (see SOURCES); kind = suit | appeal | application | complaint
LIMITS: dict[str, dict[str, Any]] = {
    "money_loan": {"label": "Recovery of money lent (suit)", "n": 3, "unit": "y", "from": "the day the loan was given",
                   "src": "Limitation Act Sch. Art. 19", "kind": "suit"},
    "money_demand": {"label": "Loan repayable on demand (suit)", "n": 3, "unit": "y", "from": "the day the loan was given",
                     "src": "Limitation Act Sch. Art. 21", "kind": "suit"},
    "specific_performance": {"label": "Specific performance of an agreement (suit)", "n": 3, "unit": "y",
                             "from": "the fixed date, or when the refusal became known", "src": "Limitation Act Sch. Art. 54", "kind": "suit"},
    "breach_contract": {"label": "Compensation for breach of contract (suit)", "n": 3, "unit": "y", "from": "when the contract was broken",
                        "src": "Limitation Act Sch. Art. 55", "kind": "suit"},
    "declaration": {"label": "Any other declaration (suit)", "n": 3, "unit": "y", "from": "when the right to sue arose",
                    "src": "Limitation Act Sch. Art. 58", "kind": "suit"},
    "possession_title": {"label": "Possession of land / house based on title (suit)", "n": 12, "unit": "y",
                         "from": "when the other person's possession became adverse to you", "src": "Limitation Act Sch. Art. 65", "kind": "suit"},
    "suit_residuary": {"label": "Any other suit with no separate period", "n": 3, "unit": "y", "from": "when the right to sue arose",
                       "src": "Limitation Act Sch. Art. 113", "kind": "suit"},
    "appeal_hc_civil": {"label": "Civil appeal to the High Court (decree / order)", "n": 90, "unit": "d", "from": "date of the decree / order",
                        "src": "Limitation Act Sch. Art. 116(a)", "kind": "appeal"},
    "appeal_other_civil": {"label": "Civil appeal to any other court (for example District Court)", "n": 30, "unit": "d",
                           "from": "date of the decree / order", "src": "Limitation Act Sch. Art. 116(b)", "kind": "appeal"},
    "appeal_hc_same": {"label": "Appeal within the same High Court from its decree / order (like an LPA)", "n": 30, "unit": "d",
                       "from": "date of the decree / order", "src": "Limitation Act Sch. Art. 117", "kind": "appeal"},
    "crim_appeal_hc": {"label": "Criminal appeal (sentence / order, not acquittal) to the High Court", "n": 60, "unit": "d",
                       "from": "date of the sentence / order", "src": "Limitation Act Sch. Art. 115(b)(i)", "kind": "appeal"},
    "crim_appeal_other": {"label": "Criminal appeal (sentence / order) to any other court (Sessions)", "n": 30, "unit": "d",
                          "from": "date of the sentence / order", "src": "Limitation Act Sch. Art. 115(b)(ii)", "kind": "appeal"},
    "acquittal_appeal": {"label": "Appeal against acquittal (State)", "n": 90, "unit": "d", "from": "date of the order",
                         "src": "Limitation Act Sch. Art. 114(a)", "kind": "appeal"},
    "leave_defend": {"label": "Leave to defend in a summary suit", "n": 10, "unit": "d", "from": "the day the summons was served",
                     "src": "Limitation Act Sch. Art. 118", "kind": "application"},
    "set_aside_exparte": {"label": "Setting aside an ex parte decree", "n": 30, "unit": "d",
                          "from": "date of the decree (if the summons was not properly served, when it became known)",
                          "src": "Limitation Act Sch. Art. 123", "kind": "application"},
    "review": {"label": "Review (other than the Supreme Court)", "n": 30, "unit": "d", "from": "date of the decree / order",
               "src": "Limitation Act Sch. Art. 124", "kind": "application"},
    "revision": {"label": "Revision (CPC / CrPC)", "n": 90, "unit": "d", "from": "date of the decree / order / sentence",
                 "src": "Limitation Act Sch. Art. 131", "kind": "application"},
    "execution": {"label": "Execution of a decree (other than a perpetual injunction)", "n": 12, "unit": "y",
                  "from": "when the decree became enforceable", "src": "Limitation Act Sch. Art. 136", "kind": "application"},
    "application_residuary": {"label": "Any other application with no separate period", "n": 3, "unit": "y", "from": "when the right to apply arose",
                              "src": "Limitation Act Sch. Art. 137", "kind": "application"},
}
# periods outside the Limitation Act that she asked about often: no number is built in (the bare text was not read here).
ASK_ONLY = {
    "cheque_138": "Cheque bounce (NI Act s.138 / 142): notice, payment and complaint dates from the advocate; the Wholesale Assistant's dates are only estimates.",
    "consumer": "Consumer complaint / appeal (Consumer Protection Act 2019): confirm the period with the advocate, then give 'n' and 'unit'.",
    "arbitration_34": "Challenge to an arbitration award (Arbitration Act s.34): get the period from the advocate, then tell me.",
    "slp": "Supreme Court SLP: get the period under the Supreme Court Rules 2013 from the advocate, then tell me.",
    "written_statement": "Written statement (CPC Order VIII / commercial courts): get the period from the advocate, then tell me.",
}
SEC5 = ("Section 5 (condonation of delay) may apply to appeals and applications, not suits; it is at the court's discretion, "
        "so treat the last date as the real one.")


def add_period(start: date, n: int, unit: str) -> date:
    """Period counted EXCLUDING the start day (s.12(1)). Months / years = same calendar day, clipped to the month end."""
    if unit == "d":
        return start + timedelta(days=n)
    months = n * (12 if unit == "y" else 1)
    y, m = divmod(start.month - 1 + months, 12)
    y, m = start.year + y, m + 1
    return date(y, m, min(start.day, calendar.monthrange(y, m)[1]))


def limitation(kind: str, start, n: int | None = None, unit: str = "", cc_applied=None, cc_ready=None,
               closed: set[str] | None = None, closed_weekdays: tuple[int, ...] = (6,), today: date | None = None) -> dict[str, Any]:
    """Last date by Limitation Act ss.12 / 4 from HER dates. kind = a LIMITS key, or 'custom' with her n + unit."""
    steps: list[str] = []
    base = LIMITS.get(kind)
    if base is None and kind in ASK_ONLY and not n:
        return {"ok": False, "ask": ASK_ONLY[kind], "say": ASK_ONLY[kind] + " " + CHECK}
    if base is None and not n:
        return {"ok": False, "ask": "Which period? It is not in the table: ask the advocate for the period (days / months / years) and tell me.",
                "say": "Period unknown; I will not guess. " + CHECK}
    st = parse_date(start)
    if st is None:
        return {"ok": False, "ask": "The start date (order / decree / cause of action) is needed.", "say": "Date is needed."}
    if n:
        unit = unit if unit in ("d", "m", "y") else "d"
        label, src, k = (base or {}).get("label") or "The period you gave", (base or {}).get("src") or "given by you", \
            (base or {}).get("kind") or "application"
        if base and (int(n) != base["n"] or unit != base["unit"]):
            steps.append(f"The table says {base['n']} {base['unit']}, you gave {n} {unit}: using yours.")
            src = "given by you"
    else:
        n, unit, label, src, k = base["n"], base["unit"], base["label"], base["src"], base["kind"]
    n = int(n)
    word = {"d": "days", "m": "months", "y": "years"}[unit]
    last = add_period(st, n, unit)
    steps.append(f"{st.isoformat()} + {n} {word} (first day not counted, s.12(1)) = {last.isoformat()}.")
    excl = 0
    a, r = parse_date(cc_applied), parse_date(cc_ready)
    if k in ("appeal", "application") and (a or r):
        if a and r and r >= a:
            if a <= last:
                excl = (r - a).days
                last = last + timedelta(days=excl)
                steps.append(f"Certified copy {a.isoformat()} requested, {r.isoformat()} received: {excl} days excluded (s.12(2)) = {last.isoformat()}.")
            else:
                steps.append("Certified copy requested after the limitation ended: that time is not excluded.")
        else:
            steps.append("Both certified copy dates (requested / received) are needed; nothing excluded yet.")
    closed = closed or set()
    moved = 0
    while last.isoformat() in closed or last.weekday() in closed_weekdays:
        last += timedelta(days=1)
        moved += 1
        if moved > 60:
            break
    if moved:
        steps.append(f"The court is closed that day: next open day {last.isoformat()} (s.4).")
    left = (last - today).days if today else None
    out = {"ok": True, "kind": kind, "label": label, "period": f"{n} {word}", "source": src, "start": st.isoformat(),
           "excluded_days": excl, "last_date": last.isoformat(), "days_left": left, "steps": steps,
           "notes": [SEC5] if k in ("appeal", "application") else ["Section 5 (condonation of delay) does not apply to a suit."],
           "check": CHECK}
    if left is not None:
        tail = "has passed" if left < 0 else ("today is the last day" if left == 0 else f"{left} days left")
        out["say"] = f"{label}: estimated last date {last.isoformat()} ({tail}). {CHECK}"
    else:
        out["say"] = f"{label}: estimated last date {last.isoformat()}. {CHECK}"
    return out


# ---------------------------------------------------------------- matter kinds -> document checklist
MATTER_KINDS = {
    "civil_suit": "Civil suit", "criminal": "Criminal case", "bail": "Bail", "cheque_138": "Cheque bounce (NI Act 138)",
    "consumer": "Consumer complaint", "family": "Family / matrimonial", "writ": "Writ petition", "appeal": "Appeal / revision",
    "arbitration": "Arbitration", "property": "Property / title", "recovery": "Recovery / money", "labour": "Labour / service",
    "motor_accident": "Motor accident claim", "other": "Other",
}
COMMON_DOCS = [("vakalatnama", "Vakalatnama (client's signature + advocate's acceptance)"), ("client_id", "Client's ID (locker reference)"),
               ("address", "Client ka address for service"), ("brief", "Client's written statement / brief")]
DOCS: dict[str, list[tuple[str, str]]] = {
    "civil_suit": [("plaint", "Plaint draft"), ("valuation", "Suit valuation + court fee calculation (you pay the court fee)"),
                   ("cause_docs", "Cause of action documents"), ("legal_notice", "Notice sent earlier + post / courier receipt"),
                   ("affidavit", "Verification affidavit"), ("list_docs", "List of documents")],
    "criminal": [("fir", "FIR / complaint copy"), ("chargesheet", "Chargesheet / police report"), ("orders", "Orders so far"),
                 ("witness", "List of witnesses"), ("evidence_docs", "Evidence documents (65B / BSA 63 certificate where electronic)")],
    "bail": [("fir", "FIR copy"), ("arrest_memo", "Arrest memo / remand order"), ("surety", "Surety documents"),
             ("previous_bail", "Previous bail application / order"), ("medical", "Medical documents (if any)")],
    "cheque_138": [("cheque", "Copy of the cheque (keep the original safe)"), ("return_memo", "Bank's return memo"),
                   ("notice", "Demand notice + post receipt + tracking"), ("reply", "Reply to the notice (if any)"),
                   ("liability", "Debt / liability documents"), ("affidavit", "Affidavit with the complaint")],
    "consumer": [("invoice", "Bill / invoice"), ("warranty", "Warranty card"), ("correspondence", "Correspondence / emails with the company"),
                 ("complaint_ack", "Company's complaint number"), ("proof", "Photo / video evidence")],
    "family": [("marriage", "Proof / certificate of marriage"), ("income", "Income documents"), ("children", "Children's documents"),
               ("residence", "Proof of residence"), ("previous", "Earlier cases / orders")],
    "writ": [("impugned", "The order being challenged (impugned order)"), ("representation", "Representation made to the government"),
             ("annexures", "Annexures, page numbered"), ("affidavit", "Affidavit")],
    "appeal": [("judgment", "Certified copy of the judgment / decree / order"), ("cc_dates", "Dates the certified copy was requested / received"),
               ("lower_record", "Lower court record"), ("grounds", "Draft grounds of appeal"), ("delay", "Delay application if late")],
    "arbitration": [("agreement", "Agreement with the arbitration clause"), ("notice", "Arbitration notice"), ("award", "Award copy (if any)"),
                    ("claim", "Claim statement")],
    "property": [("title", "Title deed / sale deed"), ("seven_twelve", "7/12 / property card"), ("mutation", "Mutation entry"),
                 ("tax", "Property tax receipts"), ("map", "Map / measurement")],
    "recovery": [("agreement", "Agreement / invoice"), ("ledger", "Account / ledger"), ("ack", "Proof the debt was acknowledged"),
                 ("notice", "Demand notice + receipt")],
    "labour": [("appointment", "Appointment letter"), ("salary", "Salary slips"), ("termination", "Termination / order"),
               ("service", "Service record")],
    "motor_accident": [("fir", "FIR"), ("medical", "Medical / post-mortem"), ("bills", "Treatment bills"), ("income", "Proof of income"),
                       ("vehicle", "Vehicle papers / insurance")],
    "other": [],
}


def checklist(kind: str) -> list[tuple[str, str]]:
    return COMMON_DOCS + DOCS.get(kind if kind in DOCS else "other", [])


VAKALATNAMA = [
    "Client's full name, father's / husband's name, age, address (in the court's format)",
    "Client's signature / thumb impression on every page where the court asks",
    "Advocate's 'accepted' + name, enrolment number, address, phone / email",
    "State Advocates Welfare Fund stamp / ticket (amount as per your state's rule; Hoola does not fill amounts)",
    "Court fee stamp where the court asks (your amount)",
    "For a company / firm, the board resolution / authority letter",
    "If through someone else, a copy of the Power of Attorney",
    "If changing advocates, the previous advocate's NOC / the court's permission",
    "Case number / CNR and court name at the top",
]

STAGES = ["filing", "registration", "notice", "appearance", "written_statement", "framing_issues", "charge", "evidence",
          "cross", "arguments", "judgment", "order", "execution", "disposed", "other"]

SIDES = ["petitioner", "respondent", "plaintiff", "defendant", "complainant", "accused", "appellant", "applicant", "opponent", "other"]
