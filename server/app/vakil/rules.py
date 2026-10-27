"""Vakil Sahayak rules: CNR, case numbers, cause-list / case-status parsing (text she pastes from the official eCourts app /
court site), limitation arithmetic (Limitation Act 1963 ss.4 / 12 with HER inputs), document checklists, draft templates.

Nothing here is legal advice. Every period below is a STARTER from the bare text we read (sources in SOURCES); the result is
always "andaaza, vakil se pakka". A limitation the table doesn't know is asked from her, never guessed."""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any

CHECK = "Yeh andaaza / draft hai, salah nahi: vakil sahab se pakka karwaiye."
NEVER = [
    "Hoola vakil nahi hai: koi kanooni salah nahi, sirf diary, tareekhein, drafts.",
    "Court mein filing, client / doosre paksh ko notice / letter / message, fee ki maang: sirf aapke tap se (card).",
    "Paise kabhi khud nahi leta / bhejta. Court fee / e-stamp / ePay aap khud bharti hain.",
    "eCourts / court site par sirf official raaste: aap app / site se text ya file chipkaati hain, Hoola padhta hai. Scraping nahi.",
    "Section / citation sirf jo source padha ho (link ke saath); warna '[citation chahiye]'.",
    "Ek client ki baat doosre client ko kabhi nahi. Aadhaar / PAN sirf Pehchaan Locker ke {id:...} se.",
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
    "money_loan": {"label": "Udhaar diye paise ki vasooli (suit)", "n": 3, "unit": "y", "from": "jis din udhaar diya",
                   "src": "Limitation Act Sch. Art. 19", "kind": "suit"},
    "money_demand": {"label": "Maangne par lautaane wala udhaar (suit)", "n": 3, "unit": "y", "from": "jis din udhaar diya",
                     "src": "Limitation Act Sch. Art. 21", "kind": "suit"},
    "specific_performance": {"label": "Agreement ka specific performance (suit)", "n": 3, "unit": "y",
                             "from": "tay tareekh, ya jab pata chala ki inkaar hai", "src": "Limitation Act Sch. Art. 54", "kind": "suit"},
    "breach_contract": {"label": "Contract tootne ka muavza (suit)", "n": 3, "unit": "y", "from": "jab contract toota",
                        "src": "Limitation Act Sch. Art. 55", "kind": "suit"},
    "declaration": {"label": "Koi aur declaration (suit)", "n": 3, "unit": "y", "from": "jab mukadma karne ka haq bana",
                    "src": "Limitation Act Sch. Art. 58", "kind": "suit"},
    "possession_title": {"label": "Title ke aadhar par zameen / ghar ka kabza (suit)", "n": 12, "unit": "y",
                         "from": "jab doosre ka kabza aapke khilaaf (adverse) hua", "src": "Limitation Act Sch. Art. 65", "kind": "suit"},
    "suit_residuary": {"label": "Koi aur suit jiska alag period nahi", "n": 3, "unit": "y", "from": "jab mukadma karne ka haq bana",
                       "src": "Limitation Act Sch. Art. 113", "kind": "suit"},
    "appeal_hc_civil": {"label": "Civil appeal High Court mein (decree / order)", "n": 90, "unit": "d", "from": "decree / order ki tareekh",
                        "src": "Limitation Act Sch. Art. 116(a)", "kind": "appeal"},
    "appeal_other_civil": {"label": "Civil appeal kisi aur court mein (jaise District Court)", "n": 30, "unit": "d",
                           "from": "decree / order ki tareekh", "src": "Limitation Act Sch. Art. 116(b)", "kind": "appeal"},
    "appeal_hc_same": {"label": "High Court ke decree / order se usi High Court mein appeal (LPA jaisa)", "n": 30, "unit": "d",
                       "from": "decree / order ki tareekh", "src": "Limitation Act Sch. Art. 117", "kind": "appeal"},
    "crim_appeal_hc": {"label": "Criminal appeal (sazaa / order, acquittal nahi) High Court mein", "n": 60, "unit": "d",
                       "from": "sazaa / order ki tareekh", "src": "Limitation Act Sch. Art. 115(b)(i)", "kind": "appeal"},
    "crim_appeal_other": {"label": "Criminal appeal (sazaa / order) kisi aur court mein (Sessions)", "n": 30, "unit": "d",
                          "from": "sazaa / order ki tareekh", "src": "Limitation Act Sch. Art. 115(b)(ii)", "kind": "appeal"},
    "acquittal_appeal": {"label": "Acquittal ke khilaaf appeal (State)", "n": 90, "unit": "d", "from": "order ki tareekh",
                         "src": "Limitation Act Sch. Art. 114(a)", "kind": "appeal"},
    "leave_defend": {"label": "Summary suit mein leave to defend", "n": 10, "unit": "d", "from": "summons serve hone ka din",
                     "src": "Limitation Act Sch. Art. 118", "kind": "application"},
    "set_aside_exparte": {"label": "Ex parte decree hatwana", "n": 30, "unit": "d",
                          "from": "decree ki tareekh (summons theek se serve na ho to jab pata chala)",
                          "src": "Limitation Act Sch. Art. 123", "kind": "application"},
    "review": {"label": "Review (Supreme Court ke alawa)", "n": 30, "unit": "d", "from": "decree / order ki tareekh",
               "src": "Limitation Act Sch. Art. 124", "kind": "application"},
    "revision": {"label": "Revision (CPC / CrPC)", "n": 90, "unit": "d", "from": "decree / order / sazaa ki tareekh",
                 "src": "Limitation Act Sch. Art. 131", "kind": "application"},
    "execution": {"label": "Decree ka execution (perpetual injunction ke alawa)", "n": 12, "unit": "y",
                  "from": "jab decree enforceable hui", "src": "Limitation Act Sch. Art. 136", "kind": "application"},
    "application_residuary": {"label": "Koi aur application jiska alag period nahi", "n": 3, "unit": "y", "from": "jab apply karne ka haq bana",
                              "src": "Limitation Act Sch. Art. 137", "kind": "application"},
}
# periods outside the Limitation Act that she asked about often: no number is built in (the bare text was not read here).
ASK_ONLY = {
    "cheque_138": "Cheque bounce (NI Act s.138 / 142): notice, payment aur complaint ki tareekhein vakil se; Thok Sahayak ke dates sirf andaaza.",
    "consumer": "Consumer complaint / appeal (Consumer Protection Act 2019): period vakil se pakka kijiye, phir 'n' aur 'unit' bataiye.",
    "arbitration_34": "Arbitration award ko chunauti (Arbitration Act s.34): period vakil se, phir bataiye.",
    "slp": "Supreme Court SLP: Supreme Court Rules 2013 ke hisaab se period vakil se, phir bataiye.",
    "written_statement": "Written statement (CPC Order VIII / commercial courts): period vakil se, phir bataiye.",
}
SEC5 = ("Section 5 (der maafi / condonation) appeal aur applications par lag sakta hai, suit par nahi; court ki marzi hai, "
        "isliye last date ko hi asli maaniye.")


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
        return {"ok": False, "ask": "Kaunsa period? Table mein nahi hai: vakil se period (din / mahine / saal) poochkar bataiye.",
                "say": "Period pata nahi, andaaza nahi lagaunga. " + CHECK}
    st = parse_date(start)
    if st is None:
        return {"ok": False, "ask": "Shuruaat ki tareekh (order / decree / cause of action) chahiye.", "say": "Tareekh chahiye."}
    if n:
        unit = unit if unit in ("d", "m", "y") else "d"
        label, src, k = (base or {}).get("label") or "Aapka bataya period", (base or {}).get("src") or "aapka bataya", \
            (base or {}).get("kind") or "application"
        if base and (int(n) != base["n"] or unit != base["unit"]):
            steps.append(f"Table mein {base['n']} {base['unit']} hai, aapne {n} {unit} bataya: aapka maana.")
            src = "aapka bataya"
    else:
        n, unit, label, src, k = base["n"], base["unit"], base["label"], base["src"], base["kind"]
    n = int(n)
    word = {"d": "din", "m": "mahine", "y": "saal"}[unit]
    last = add_period(st, n, unit)
    steps.append(f"{st.isoformat()} se {n} {word} (pehla din nahi gina, s.12(1)) = {last.isoformat()}.")
    excl = 0
    a, r = parse_date(cc_applied), parse_date(cc_ready)
    if k in ("appeal", "application") and (a or r):
        if a and r and r >= a:
            if a <= last:
                excl = (r - a).days
                last = last + timedelta(days=excl)
                steps.append(f"Certified copy {a.isoformat()} ko maangi, {r.isoformat()} ko mili: {excl} din chhod diye (s.12(2)) = {last.isoformat()}.")
            else:
                steps.append("Certified copy limitation khatam hone ke baad maangi: woh samay nahi chhuta.")
        else:
            steps.append("Certified copy ki dono tareekhein (maangi / mili) chahiye; abhi nahi chhoda.")
    closed = closed or set()
    moved = 0
    while last.isoformat() in closed or last.weekday() in closed_weekdays:
        last += timedelta(days=1)
        moved += 1
        if moved > 60:
            break
    if moved:
        steps.append(f"Us din court band: agla khula din {last.isoformat()} (s.4).")
    left = (last - today).days if today else None
    out = {"ok": True, "kind": kind, "label": label, "period": f"{n} {word}", "source": src, "start": st.isoformat(),
           "excluded_days": excl, "last_date": last.isoformat(), "days_left": left, "steps": steps,
           "notes": [SEC5] if k in ("appeal", "application") else ["Suit par Section 5 (der maafi) nahi lagta."],
           "check": CHECK}
    if left is not None:
        tail = "nikal chuki" if left < 0 else ("aaj aakhri din" if left == 0 else f"{left} din baaki")
        out["say"] = f"{label}: andaazan aakhri tareekh {last.isoformat()} ({tail}). {CHECK}"
    else:
        out["say"] = f"{label}: andaazan aakhri tareekh {last.isoformat()}. {CHECK}"
    return out


# ---------------------------------------------------------------- matter kinds -> document checklist
MATTER_KINDS = {
    "civil_suit": "Civil suit", "criminal": "Criminal case", "bail": "Bail", "cheque_138": "Cheque bounce (NI Act 138)",
    "consumer": "Consumer complaint", "family": "Family / matrimonial", "writ": "Writ petition", "appeal": "Appeal / revision",
    "arbitration": "Arbitration", "property": "Property / title", "recovery": "Recovery / money", "labour": "Labour / service",
    "motor_accident": "Motor accident claim", "other": "Other",
}
COMMON_DOCS = [("vakalatnama", "Vakalatnama (client ke sign + vakil ka accept)"), ("client_id", "Client ki pehchaan (locker reference)"),
               ("address", "Client ka address for service"), ("brief", "Client ki likhit baat / brief")]
DOCS: dict[str, list[tuple[str, str]]] = {
    "civil_suit": [("plaint", "Plaint draft"), ("valuation", "Suit valuation + court fee hisaab (court fee aap bharengi)"),
                   ("cause_docs", "Cause of action ke kaagaz"), ("legal_notice", "Pehle bheja notice + daak / courier receipt"),
                   ("affidavit", "Verification affidavit"), ("list_docs", "List of documents")],
    "criminal": [("fir", "FIR / complaint copy"), ("chargesheet", "Chargesheet / police report"), ("orders", "Ab tak ke orders"),
                 ("witness", "Gawahon ki list"), ("evidence_docs", "Saboot ke kaagaz (65B / BSA 63 certificate jahan electronic)")],
    "bail": [("fir", "FIR copy"), ("arrest_memo", "Arrest memo / remand order"), ("surety", "Surety ke kaagaz"),
             ("previous_bail", "Pichhli bail application / order"), ("medical", "Medical kaagaz (agar ho)")],
    "cheque_138": [("cheque", "Cheque ki copy (original surakshit)"), ("return_memo", "Bank ka return memo"),
                   ("notice", "Demand notice + daak receipt + tracking"), ("reply", "Notice ka jawab (agar aaya)"),
                   ("liability", "Karz / liability ke kaagaz"), ("affidavit", "Complaint ke saath affidavit")],
    "consumer": [("invoice", "Bill / invoice"), ("warranty", "Warranty card"), ("correspondence", "Company se baat / emails"),
                 ("complaint_ack", "Company ki shikayat ka number"), ("proof", "Photo / video saboot")],
    "family": [("marriage", "Shaadi ka saboot / certificate"), ("income", "Aamdani ke kaagaz"), ("children", "Bachchon ke kaagaz"),
               ("residence", "Rehne ka saboot"), ("previous", "Pichhle case / orders")],
    "writ": [("impugned", "Jis order ko chunauti (impugned order)"), ("representation", "Sarkar ko di gayi arzi"),
             ("annexures", "Annexures, page numbered"), ("affidavit", "Affidavit")],
    "appeal": [("judgment", "Judgment / decree / order ki certified copy"), ("cc_dates", "Certified copy maangne / milne ki tareekh"),
               ("lower_record", "Lower court ke kaagaz"), ("grounds", "Appeal ke grounds draft"), ("delay", "Der ho to delay application")],
    "arbitration": [("agreement", "Arbitration clause wala agreement"), ("notice", "Arbitration notice"), ("award", "Award copy (agar aaya)"),
                    ("claim", "Claim statement")],
    "property": [("title", "Title deed / sale deed"), ("seven_twelve", "7/12 / property card"), ("mutation", "Ferfar / mutation"),
                 ("tax", "Property tax receipts"), ("map", "Naksha / measurement")],
    "recovery": [("agreement", "Agreement / invoice"), ("ledger", "Khaata / ledger"), ("ack", "Udhaar maanne ka saboot"),
                 ("notice", "Demand notice + receipt")],
    "labour": [("appointment", "Appointment letter"), ("salary", "Salary slips"), ("termination", "Termination / order"),
               ("service", "Service record")],
    "motor_accident": [("fir", "FIR"), ("medical", "Medical / post-mortem"), ("bills", "Ilaaj ke bill"), ("income", "Aamdani ka saboot"),
                       ("vehicle", "Gaadi ke kaagaz / insurance")],
    "other": [],
}


def checklist(kind: str) -> list[tuple[str, str]]:
    return COMMON_DOCS + DOCS.get(kind if kind in DOCS else "other", [])


VAKALATNAMA = [
    "Client ka poora naam, pita / pati ka naam, umar, pata (court ke format mein)",
    "Client ke sign / angootha har page par jahan court maange",
    "Vakil ka 'accepted' + naam, enrolment number, pata, phone / email",
    "State ke Advocates Welfare Fund ka stamp / ticket (rakam aapke state ke rule se; Hoola rakam nahi bharta)",
    "Court fee stamp jahan court maange (rakam aapki)",
    "Company / firm ho to board resolution / authority letter",
    "Kisi aur ke zariye ho to Power of Attorney ki copy",
    "Vakil badal rahe hon to pichhle vakil ka NOC / court ki ijazat",
    "Case number / CNR aur court ka naam upar",
]

STAGES = ["filing", "registration", "notice", "appearance", "written_statement", "framing_issues", "charge", "evidence",
          "cross", "arguments", "judgment", "order", "execution", "disposed", "other"]

SIDES = ["petitioner", "respondent", "plaintiff", "defendant", "complainant", "accused", "appellant", "applicant", "opponent", "other"]
