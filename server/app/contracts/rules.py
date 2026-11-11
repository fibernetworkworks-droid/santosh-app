"""Contracts Sahayak rules: contract kinds, clause finder (English + Hinglish words), value readers (durations, notice days,
payment days, dates, parties, law, seat, courts), the starter playbook (her standard positions replace it), the risk review in
plain English, redline suggestions (find / replace / insert / delete), stamp duty ONLY from her rates, renewal maths.

Everything here is pure (no DB, no network) so it is tested directly. Hoola is not a lawyer: every output carries DRAFT_LINE."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

DRAFT_LINE = "This is a draft / information, not legal advice: have a lawyer / CA / CS confirm it."

NEVER = [
    "Never changes the contract's original file: a redline is always a new Word copy",
    "A draft / redline to the other party, e-sign, e-stamp, notice: only from the card you tap (Hoola does not send by itself)",
    "Stamp duty only from your rate; no rate means blank, never a guess",
    "A section / case citation only from a source Hoola has read (with the link), otherwise [citation needed]",
    "Each signer enters the Aadhaar eSign OTP themselves; Hoola never takes an OTP / PIN",
    "Never moves money: you pay the stamp duty / fee on the portal yourself",
    "Never shows one client's / party's contract to another",
]

KINDS = {
    "nda": "NDA / confidentiality", "msa": "Master services agreement", "service": "Service agreement", "vendor": "Vendor / supply",
    "purchase": "Purchase order / terms", "consultancy": "Consultancy", "employment": "Employment / appointment",
    "lease": "Lease / rent", "leave_licence": "Leave & licence", "distribution": "Distribution / dealership",
    "franchise": "Franchise", "loan": "Loan / credit", "partnership": "Partnership / JV", "software": "Software / SaaS licence",
    "sale_immovable": "Sale of immovable property", "poa": "Power of attorney", "other": "Other",
}
# IT Act 2000 First Schedule: the Act (and so e-signatures) does not apply to these documents.
FIRST_SCHEDULE = {"sale_immovable": "contract for sale / conveyance of immovable property",
                  "poa": "power of attorney", "will": "will", "trust": "trust", "negotiable": "negotiable instrument (other than cheque)"}

ROLES = ("customer", "vendor", "employer", "employee", "licensor", "licensee", "landlord", "tenant", "discloser", "recipient",
         "lender", "borrower", "franchisor", "franchisee", "mutual")
WE_PAY = {"customer", "employer", "licensee", "tenant", "borrower", "franchisee"}
WE_GET_PAID = {"vendor", "employee", "licensor", "landlord", "lender", "franchisor"}

STATUSES = ("draft", "negotiation", "waiting_sign", "signed", "active", "expired", "terminated", "archived")

CLAUSES: dict[str, dict[str, Any]] = {
    "parties": {"label": "Parties", "words": [r"\bbetween\b", r"\bby and between\b", r"hereinafter (?:referred|called)"]},
    "term": {"label": "Term", "words": [r"\bterm of (?:this|the) agreement\b", r"\bshall (?:remain|be) in (?:full )?force\b",
                                                  r"\bvalid (?:for|till|until)\b", r"\bperiod of\b", r"\bcommence\w*\b", r"\bavadhi\b"]},
    "renewal": {"label": "Renewal", "words": [r"\brenew\w*\b", r"\bextend\w*\b", r"\bnaveeni\w*\b"]},
    "auto_renewal": {"label": "Auto-renewal", "words": [r"\bautomatically renew\w*\b", r"\bauto[- ]?renew\w*\b",
                                                         r"\bdeemed (?:to (?:have been|be) )?renewed\b", r"\bshall renew automatically\b"]},
    "notice": {"label": "Notice period", "words": [r"\bnotice period\b", r"\bprior (?:written )?notice\b", r"\b\w+ \(\d+\) days'? (?:prior )?(?:written )?notice\b",
                                                   r"\bdays'? (?:prior )?(?:written )?notice\b"]},
    "payment": {"label": "Payment terms", "words": [r"\binvoice\w*\b", r"\bpayment\w*\b", r"\bfees?\b", r"\bconsideration\b", r"\bbhugtan\b"]},
    "liability_cap": {"label": "Liability cap", "words": [r"\blimitation of liability\b", r"\bliability\b.{0,80}\bshall not exceed\b",
                                                          r"\baggregate liability\b", r"\bin no event shall\b.{0,60}\bliable\b",
                                                          r"\bunlimited liability\b"]},
    "indemnity": {"label": "Indemnity", "words": [r"\bindemnif\w*\b", r"\bhold harmless\b"]},
    "termination": {"label": "Termination", "words": [r"\bterminat\w*\b"]},
    "governing_law": {"label": "Governing law", "words": [r"\bgoverned by\b", r"\bgoverning law\b", r"\blaws of\b"]},
    "arbitration": {"label": "Arbitration / seat", "words": [r"\barbitrat\w*\b", r"\bseat\b", r"\bvenue\b"]},
    "jurisdiction": {"label": "Courts / jurisdiction", "words": [r"\bjurisdiction\b", r"\bcourts? (?:at|in|of)\b"]},
    "stamp": {"label": "Stamp duty", "words": [r"\bstamp duty\b", r"\be-?stamp\w*\b", r"\bstamp paper\b", r"\bIN-[A-Z]{2}\d{6,}"]},
    "confidentiality": {"label": "Confidentiality", "words": [r"\bconfidential\w*\b", r"\bnon-?disclosure\b"]},
    "ip": {"label": "IP / ownership", "words": [r"\bintellectual property\b", r"\bcopyright\b", r"\bIPR\b", r"\bdeliverables?\b.{0,60}\b(?:own|vest|belong)\w*\b"]},
    "non_compete": {"label": "Non-compete", "words": [r"\bnon-?compet\w*\b", r"\bshall not\b.{0,80}\b(?:compete|competing|competitor|similar business|rival)\b",
                                                      r"\brestraint of trade\b"]},
    "non_solicit": {"label": "Non-solicit", "words": [r"\bnon-?solicit\w*\b", r"\bshall not\b.{0,60}\bsolicit\b"]},
    "liquidated_damages": {"label": "Liquidated damages / penalty", "words": [r"\bliquidated damages\b", r"\bpenalty\b", r"\bjurmana\b"]},
    "force_majeure": {"label": "Force majeure", "words": [r"\bforce majeure\b", r"\bact of god\b"]},
    "data_protection": {"label": "Data protection (DPDP)", "words": [r"\bpersonal data\b", r"\bdata protection\b", r"\bDPDP\b",
                                                                      r"\bDigital Personal Data Protection\b"]},
    "assignment": {"label": "Assignment", "words": [r"\bassign\w*\b.{0,80}\b(?:consent|without)\b", r"\bassignment\b"]},
    "limitation": {"label": "Time to bring a claim", "words": [r"\b(?:claim|suit|action|proceeding)s?\b.{0,80}\bwithin\b.{0,20}\b(?:months?|days?|years?)\b"]},
}

LEVELS = ("high", "medium", "low", "ok")

# Starter playbook: her own standard positions replace these (per key: position / value / standard_text / level / off).
DEFAULT_PLAYBOOK: dict[str, dict[str, Any]] = {
    "liability_cap": {"position": "Liability capped on both sides (up to the fees of the last 12 months); no unlimited liability.",
                      "level": "high",
                      "standard_text": ("The aggregate liability of either Party arising out of or in connection with this Agreement shall not "
                                        "exceed the total fees paid or payable under this Agreement in the twelve (12) months preceding the "
                                        "event giving rise to the claim.")},
    "indemnity": {"position": "Indemnity on both sides (mutual), limited to one's own fault / third-party claims.", "level": "high",
                  "standard_text": ("Each Party shall indemnify the other Party against third-party claims to the extent caused by its "
                                    "own breach of this Agreement, negligence or wilful misconduct.")},
    "governing_law": {"position": "Laws of India.", "level": "high", "value": "India",
                      "standard_text": "This Agreement shall be governed by and construed in accordance with the laws of India."},
    "arbitration": {"position": "Disputes by arbitration, seat in your city.", "level": "medium", "value": "",
                    "standard_text": ("Any dispute arising out of or in connection with this Agreement shall be referred to arbitration by a "
                                      "sole arbitrator under the Arbitration and Conciliation Act, 1996. The seat of arbitration shall be "
                                      "{seat}. The language of arbitration shall be English.")},
    "payment": {"position": "We are paid within 45 days of the invoice (for an MSME, never more than 45 days).", "level": "medium",
                "value": 45},
    "notice": {"position": "Notice to end the contract is not more than 90 days.", "level": "medium", "value": 90},
    "termination": {"position": "We too can end it without cause (for convenience) by giving notice.", "level": "medium"},
    "auto_renewal": {"position": "Auto-renewal is fine, but with a reminder for the notice deadline.", "level": "low"},
    "non_compete": {"position": "No non-compete on us after the contract ends.", "level": "high"},
    "ip": {"position": "What we built before (background IP) stays ours.", "level": "medium"},
    "confidentiality": {"position": "Confidentiality on both sides.", "level": "low",
                        "standard_text": ("Each Party shall keep the other Party's confidential information confidential and use it only "
                                          "for the purposes of this Agreement.")},
    "liquidated_damages": {"position": "Any penalty / liquidated damages must be reasonable and capped.", "level": "medium"},
    "limitation": {"position": "The time to make a claim is not shorter than the law allows.", "level": "medium"},
    "data_protection": {"position": "If personal data is shared, there is a DPDP clause.", "level": "low",
                        "standard_text": ("Each Party shall process any personal data received under this Agreement only for the purposes "
                                          "of this Agreement and in compliance with the Digital Personal Data Protection Act, 2023 and the "
                                          "rules made under it.")},
    "force_majeure": {"position": "There is a force majeure clause.", "level": "low"},
    "assignment": {"position": "The other party does not assign the contract without our consent.", "level": "low"},
    "stamp": {"position": "Stamp duty is paid before signing / on the same day.", "level": "medium"},
    "term": {"position": "The start and end dates are clear.", "level": "low"},
    "dispute": {"position": "The way disputes are settled (arbitration / court) is written.", "level": "medium"},
}

_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "fifteen": 15, "eighteen": 18, "twenty": 20, "twenty-four": 24, "twenty four": 24,
        "thirty": 30, "thirty-six": 36, "thirty six": 36, "forty-five": 45, "forty five": 45, "sixty": 60, "ninety": 90,
        "one hundred twenty": 120, "one hundred and twenty": 120, "hundred and eighty": 180, "one hundred eighty": 180,
        "ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5, "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10, "baarah": 12}
_WORDNUM = r"(?:one hundred (?:and )?twenty|one hundred (?:and )?eighty|hundred and eighty|twenty[- ]four|thirty[- ]six|forty[- ]five|" \
           r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|eighteen|twenty|thirty|sixty|ninety|ek|do|teen|" \
           r"chaar|paanch|chhe|saat|aath|nau|das|baarah)"
_QTY = rf"(?:(\d{{1,4}})|({_WORDNUM})\s*(?:\((\d{{1,4}})\))?)"
_UNIT_D = r"(?:calendar |business |working )?(?:days?|din)"
_UNIT_M = r"(?:months?|mahine|mahina)"
_UNIT_Y = r"(?:years?|saal|varsh)"
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _qty(m: re.Match, base: int = 1) -> int | None:
    """Number from a _QTY match (groups base..base+2): '30', 'thirty (30)', 'thirty'. The figure in brackets wins."""
    d, w, b = m.group(base), m.group(base + 1), m.group(base + 2)
    if b:
        return int(b)
    if d:
        return int(d)
    if w:
        return _NUM.get(w.lower().replace("  ", " "))
    return None


def num(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()
    mult = 1.0
    for w, f in (("crore", 1e7), ("cr", 1e7), ("lakh", 1e5), ("lac", 1e5), ("k", 1e3)):
        if s.endswith(w):
            s, mult = s[: -len(w)].strip(), f
            break
    try:
        return float(s) * mult
    except ValueError:
        return None


def parse_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s[:10], f).date()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?(?:\s+day\s+of)?\s+([A-Za-z]{3,9})[,]?\s+(\d{4})", s)
    if m and m.group(2)[:3].lower() in _MONTHS:
        try:
            return date(int(m.group(3)), _MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s)
    if m and m.group(1)[:3].lower() in _MONTHS:
        try:
            return date(int(m.group(3)), _MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
        except ValueError:
            return None
    return None


_DATE_RX = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|"
                      r"\b\d{1,2}(?:st|nd|rd|th)?(?:\s+day\s+of)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*,?\s+\d{4}\b|"
                      r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b", re.I)


def dates_in(text: str) -> list[date]:
    out = []
    for m in _DATE_RX.finditer(text or ""):
        d = parse_date(m.group(0))
        if d and 1950 <= d.year <= 2100:
            out.append(d)
    return out


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + int(months), 12)
    y += d.year
    m += 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    return date(y, m, 28)


def duration_months(text: str) -> int | None:
    """'a period of two (2) years' -> 24, '12 months' -> 12, '36 mahine' -> 36. First one found after term words."""
    t = text or ""
    for rx, mult in ((rf"{_QTY}\s*{_UNIT_Y}", 12), (rf"{_QTY}\s*{_UNIT_M}", 1)):
        m = re.search(rx, t, re.I)
        if m:
            q = _qty(m)
            if q:
                return q * mult
    return None


def days_in(text: str) -> int | None:
    m = re.search(rf"{_QTY}\s*{_UNIT_D}", text or "", re.I)
    if m:
        return _qty(m)
    m = re.search(rf"{_QTY}\s*{_UNIT_M}'?\s*(?:prior )?(?:written )?notice", text or "", re.I)
    if m:
        q = _qty(m)
        return q * 30 if q else None
    return None


def days_phrase(text: str) -> str:
    """The exact words for the number of days ('ninety (90) days') - used as the redline 'find'."""
    m = re.search(rf"{_QTY}\s*{_UNIT_D}", text or "", re.I)
    return m.group(0) if m else ""


def words_for(n: int) -> str:
    inv = {v: k for k, v in _NUM.items() if re.fullmatch(r"[a-z -]+", k) and k not in ("ek", "do", "teen", "chaar", "paanch", "chhe",
                                                                                        "saat", "aath", "nau", "das", "baarah")}
    w = inv.get(int(n))
    return f"{w} ({int(n)}) days" if w else f"{int(n)} days"


# ---------------------------------------------------------------- splitting + finding
def paragraphs(text: str) -> list[str]:
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n(?=\s*(?:\d{1,2}(?:\.\d{1,2})*[.)]|\([a-z]\)|clause \d|article \d)\s)", t, flags=re.I)]
    out = []
    for p in parts:
        p = re.sub(r"[ \t]*\n[ \t]*", " ", p).strip()
        if p:
            out.append(p)
    return out


def find_clauses(text: str) -> dict[str, list[int]]:
    paras = paragraphs(text)
    found: dict[str, list[int]] = {}
    for key, d in CLAUSES.items():
        hits = []
        for i, p in enumerate(paras):
            if any(re.search(w, p, re.I) for w in d["words"]):
                hits.append(i)
        if hits:
            found[key] = hits[:8]
    return found


def _clip(s: str, n: int = 400) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _defined_terms(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"(?:hereinafter|herein after)\s+(?:referred to as|called)\s+(?:the\s+)?[\"“'‘]?([A-Z][\w &.-]{1,40}?)[\"”'’]",
                                                   text or "", re.I)][:6]


def parties(text: str) -> list[dict[str, str]]:
    t = re.sub(r"\s+", " ", (text or "")[:6000])
    out: list[dict[str, str]] = []
    m = re.search(r"\bbetween\s*:?\s*(.{3,160}?)(?:,|\(|\bhaving\b|\bhereinafter\b).{0,600}?\band\s*:?\s*(.{3,160}?)(?:,|\(|\bhaving\b|\bhereinafter\b)", t, re.I)
    terms = _defined_terms(t)
    if m:
        for i, g in enumerate((m.group(1), m.group(2))):
            name = re.sub(r"^(?:m/s\.?|messrs\.?)\s*", "", g.strip(" :.-"), flags=re.I)
            out.append({"name": name[:120], "label": terms[i] if i < len(terms) else ""})
    return out


def extract(text: str) -> dict[str, Any]:
    """Clauses + values from the contract's own words. Each clause: label, text (the paragraph), found True/False. Values are
    only what the words say; nothing is guessed."""
    paras = paragraphs(text)
    hits = find_clauses(text)
    t = text or ""
    clauses: dict[str, dict[str, Any]] = {}
    for key, d in CLAUSES.items():
        idx = hits.get(key) or []
        clauses[key] = {"key": key, "label": d["label"], "found": bool(idx), "text": _clip(" ".join(paras[i] for i in idx[:2]), 700),
                        "para": idx[0] if idx else None}
    vals: dict[str, Any] = {}
    vals["parties"] = parties(t)
    # term
    term_txt = clauses["term"]["text"]
    vals["term_months"] = duration_months(term_txt) if term_txt else None
    ds = dates_in(t[:4000])
    vals["dates_seen"] = [d.isoformat() for d in ds[:6]]
    m = re.search(r"(?:effective|commence\w*|start\w*)\s+(?:date\s+)?(?:from|on|with effect from|w\.?e\.?f\.?)?\s*:?\s*(.{0,40})", t, re.I)
    sd = parse_date(m.group(1)) if m else None
    if not sd:
        m = re.search(r"(?:dated|made on|executed on|entered into on)\s*:?\s*(.{0,40})", t, re.I)
        sd = parse_date(m.group(1)) if m else None
    vals["start"] = sd.isoformat() if sd else ""
    m = re.search(r"(?:expire\w*|valid (?:till|until|upto|up to)|end\w* on|terminate\w* on)\s*(?:on)?\s*:?\s*(.{0,40})", t, re.I)
    ed = parse_date(m.group(1)) if m else None
    vals["end"] = ed.isoformat() if ed else ""
    # renewal / notice
    ar = clauses["auto_renewal"]
    vals["auto_renew"] = ar["found"]
    if ar["found"]:
        mm = re.search(r"renew|extend", ar["text"], re.I)
        tail = ar["text"][mm.start():] if mm else ar["text"]
        vals["renew_months"] = duration_months(tail) or vals["term_months"]
        nd = days_in(tail)
        if nd:
            vals["renewal_notice_days"] = nd
    nt = clauses["notice"]["text"] or clauses["termination"]["text"]
    vals["notice_days"] = days_in(nt) if nt else None
    vals["notice_phrase"] = days_phrase(nt) if nt else ""
    vals["convenience"] = bool(re.search(r"\b(?:without (?:any )?(?:cause|reason)|for convenience|for any reason(?: whatsoever)?)\b",
                                          clauses["termination"]["text"] or "", re.I))
    # payment
    pm = re.search(rf"within\s+{_QTY}\s*{_UNIT_D}\s*(?:of|from|after)\s+(?:the\s+)?(?:date of\s+)?(?:receipt of\s+)?(?:a\s+|the\s+)?(?:valid\s+)?(?:invoice|bill)",
                   t, re.I)
    vals["payment_days"] = _qty(pm) if pm else None
    vals["payment_phrase"] = (re.search(rf"{_QTY}\s*{_UNIT_D}", pm.group(0), re.I).group(0) if pm else "")
    money = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakh|crore)?", t, re.I)
    vals["value"] = num(money.group(1) + (money.group(2) or "")) if money else None
    # law / seat / courts
    gl = re.search(r"governed by(?: and construed in accordance with)?(?: the)? laws? of (?:the )?(?:republic of )?([A-Z][A-Za-z ]{2,40}?)(?:[.,;]| and\b)", t, re.I)
    vals["governing_law"] = gl.group(1).strip() if gl else ""
    se = re.search(r"seat(?: and venue)?(?: of (?:the )?arbitration)?\s+(?:shall be|will be|is)\s+(?:at\s+|in\s+)?([A-Z][A-Za-z ]{2,30}?)(?:[.,;(]| and\b)", t)
    vals["seat"] = se.group(1).strip() if se else ""
    ve = re.search(r"venue(?: of (?:the )?arbitration)?\s+(?:shall be|will be|is)\s+(?:at\s+|in\s+)?([A-Z][A-Za-z ]{2,30}?)(?:[.,;(]| and\b)", t)
    vals["venue"] = ve.group(1).strip() if ve else ""
    co = re.search(r"courts?\s+(?:at|in|of)\s+([A-Z][A-Za-z ]{2,30}?)(?:\s+shall|[.,;(]| and\b)", t)
    vals["courts"] = co.group(1).strip() if co else ""
    vals["arbitration"] = clauses["arbitration"]["found"] and bool(re.search(r"arbitrat", t, re.I))
    # liability
    lc = clauses["liability_cap"]["text"]
    vals["unlimited_liability"] = bool(re.search(r"\bunlimited liability\b|\bwithout (?:any )?limit\w*\b", lc or "", re.I))
    vals["cap_found"] = bool(re.search(r"shall not exceed|aggregate liability|limited to", lc or "", re.I))
    # stamp
    sc = re.search(r"\bIN-[A-Z]{2}\d{6,}[A-Z]?\b", t)
    vals["stamp_cert"] = sc.group(0) if sc else ""
    vals["stamp_mentioned"] = clauses["stamp"]["found"]
    lm = re.search(rf"\b(?:claim|suit|action|proceeding)s?\b.{{0,80}}\bwithin\s+{_QTY}\s*({_UNIT_M}|{_UNIT_D}|{_UNIT_Y})", t, re.I)
    if lm:
        q = _qty(lm, 1)
        unit = lm.group(4).lower()
        vals["claim_window_months"] = (q * 12 if unit.startswith(("year", "saal", "varsh")) else
                                       q if unit.startswith(("month", "mahin")) else round(q / 30, 1)) if q else None
    vals["defined_terms"] = _defined_terms(t)
    return {"clauses": clauses, "values": vals, "paragraphs": len(paras)}


# ---------------------------------------------------------------- playbook + review
def playbook(mine: dict | None) -> dict[str, dict[str, Any]]:
    out = {k: dict(v) for k, v in DEFAULT_PLAYBOOK.items()}
    for k, v in (mine or {}).items():
        if k in out and isinstance(v, dict):
            out[k].update({x: y for x, y in v.items() if x in ("position", "level", "value", "standard_text", "off")})
            out[k]["mine"] = True
    return out


def _who_does(text: str, verb: str, labels: list[str]) -> str:
    """Which defined party 'shall <verb>' in this paragraph: 'mutual' | label | ''."""
    t = text or ""
    if re.search(rf"\b(?:each|either|both)\s+part(?:y|ies)\b[^.]{{0,40}}\b{verb}", t, re.I):
        return "mutual"
    for lb in labels:
        if lb and re.search(rf"\b(?:the\s+)?{re.escape(lb)}\b[^.]{{0,40}}\bshall\b[^.]{{0,30}}\b{verb}", t, re.I):
            return lb
    return ""


SOURCES = {
    "s27": "https://www.indialaw.in/blog/labour/section-27-of-indian-contract-act-varun-tyagi-ruling/",
    "stamp": "https://www.verdictum.in/app-lite/court-updates/supreme-court/unstamped-arbitration-agreement-not-void-1509237",
    "first_schedule": "https://www.mondaq.com/india/contracts-and-commercial-law/1099806/e-signing-of-contract-and-documents-in-india",
    "estamp": "https://www.shcilestamp.com/",
    "s74": "https://www.scconline.com/blog/?p=391523",
}


def _risk(key, level, title, why, fix=None, quote="", source="") -> dict[str, Any]:
    return {"key": key, "label": CLAUSES.get(key, {}).get("label", key.replace("_", " ").title()), "level": level, "title": title,
            "why": why, "fix": fix or {}, "quote": _clip(quote, 300), "source": SOURCES.get(source, ""), "draft": DRAFT_LINE}


def review(ex: dict, pb: dict, meta: dict) -> list[dict[str, Any]]:
    """Her playbook vs the contract. meta: kind, our_role, our_label, their_label, seat_city, msme. Plain Hinglish 'why'."""
    c, v = ex["clauses"], ex["values"]
    role = meta.get("our_role") or ""
    our, their = (meta.get("our_label") or "").strip(), (meta.get("their_label") or "").strip()
    labels = [x for x in (our, their) if x]
    kind = meta.get("kind") or "other"
    out: list[dict[str, Any]] = []

    def on(k):
        return not (pb.get(k) or {}).get("off")

    def lvl(k, d="medium"):
        return (pb.get(k) or {}).get("level") or d

    # governing law
    gl = (v.get("governing_law") or "").strip()
    want_law = str((pb.get("governing_law") or {}).get("value") or "India")
    if on("governing_law"):
        if gl and want_law.lower() not in gl.lower():
            out.append(_risk("governing_law", lvl("governing_law", "high"), f"Governed by {gl} law",
                             f"The contract is governed by {gl} law; a dispute means lawyers and costs there. Your position: {want_law}.",
                             {"op": "replace", "find": gl, "replace": want_law}, c["governing_law"]["text"]))
        elif not gl:
            out.append(_risk("governing_law", "low", "Governing law not written",
                             "It is not clear which country's law governs the contract.",
                             {"op": "insert", "after": "governing_law", "text": (pb.get("governing_law") or {}).get("standard_text", "")}))
    # dispute / seat
    city = (meta.get("seat_city") or (pb.get("arbitration") or {}).get("value") or "").strip()
    if on("arbitration"):
        if not v.get("arbitration") and not v.get("courts"):
            st = (pb.get("arbitration") or {}).get("standard_text", "")
            out.append(_risk("arbitration", lvl("dispute", "medium"), "No way to settle disputes",
                             "Neither arbitration nor a court is written: a dispute can take longer and cost more.",
                             {"op": "insert", "after": "governing_law", "text": st.replace("{seat}", city)} if city and st else {}))
        elif v.get("seat") and city and city.lower() not in v["seat"].lower():
            out.append(_risk("arbitration", lvl("arbitration"), f"Arbitration seat {v['seat']}",
                             f"Seat {v['seat']}, you prefer {city}. The seat decides which court supervises the arbitration.",
                             {"op": "replace", "find": v["seat"], "replace": city}, c["arbitration"]["text"]))
        elif v.get("arbitration") and not v.get("seat") and v.get("venue"):
            out.append(_risk("arbitration", "medium", "Only 'venue' is written, not 'seat'",
                             "Venue and seat are different things; it is better to write the seat clearly (have a lawyer confirm).",
                             {}, c["arbitration"]["text"]))
        if v.get("courts") and city and city.lower() not in v["courts"].lower() and not v.get("arbitration"):
            out.append(_risk("jurisdiction", "medium", f"Courts of {v['courts']}",
                             f"The courts of {v['courts']} will hear the case; your city is {city}.",
                             {"op": "replace", "find": v["courts"], "replace": city}, c["jurisdiction"]["text"]))
    # liability cap
    if on("liability_cap"):
        if v.get("unlimited_liability"):
            out.append(_risk("liability_cap", lvl("liability_cap", "high"), "Unlimited liability",
                             "No limit on damages if something goes wrong: the whole business can be at stake.",
                             {"op": "insert", "after": "liability_cap", "text": (pb["liability_cap"] or {}).get("standard_text", "")},
                             c["liability_cap"]["text"]))
        elif not v.get("cap_found"):
            out.append(_risk("liability_cap", lvl("liability_cap", "high"), "No liability cap",
                             "The contract has no upper limit on damages; your position: " + pb["liability_cap"].get("position", ""),
                             {"op": "insert", "after": "indemnity" if c["indemnity"]["found"] else "", "text": pb["liability_cap"].get("standard_text", "")}))
        elif their and re.search(rf"in no event shall (?:the )?{re.escape(their)}\b", c["liability_cap"]["text"] or "", re.I) and not re.search(
                r"\b(?:either|each|neither) party\b", c["liability_cap"]["text"] or "", re.I):
            out.append(_risk("liability_cap", "medium", "Cap only for the other party",
                             f"The liability cap protects only {their}, not you. It should be on both sides.",
                             {"op": "replace", "find": f"the {their}", "replace": "either Party"}, c["liability_cap"]["text"]))
    # indemnity
    if on("indemnity") and c["indemnity"]["found"]:
        who = _who_does(c["indemnity"]["text"], r"(?:indemnif|hold harmless)", labels)
        if our and who == our:
            out.append(_risk("indemnity", lvl("indemnity", "high"), "Indemnity only on you",
                             f"Only {our} (you) will pay for losses, not {their or 'the other party'}. Your position: {pb['indemnity'].get('position', '')}",
                             {"op": "replace_para", "key": "indemnity", "text": pb["indemnity"].get("standard_text", "")}, c["indemnity"]["text"]))
    # termination / notice
    nd = v.get("notice_days")
    max_nd = int(num((pb.get("notice") or {}).get("value")) or 90)
    if on("notice") and nd and nd > max_nd:
        out.append(_risk("notice", lvl("notice"), f"Notice {nd} days",
                         f"Leaving the contract needs {nd} days of notice; your limit is {max_nd} days.",
                         {"op": "replace", "find": v.get("notice_phrase") or "", "replace": words_for(max_nd)} if v.get("notice_phrase") else {},
                         c["notice"]["text"] or c["termination"]["text"]))
    if on("termination"):
        if not c["termination"]["found"]:
            out.append(_risk("termination", "medium", "No termination clause", "It is not written when / how the contract can end."))
        elif v.get("convenience") and their and not re.search(r"\b(?:either|each|both) part", c["termination"]["text"], re.I) and \
                re.search(rf"\b{re.escape(their)}\b[^.]{{0,30}}\bmay\b[^.]{{0,20}}\bterminat", c["termination"]["text"], re.I) and \
                not (our and re.search(rf"\b{re.escape(our)}\b[^.]{{0,30}}\bmay\b[^.]{{0,20}}\bterminat", c["termination"]["text"], re.I)):
            out.append(_risk("termination", lvl("termination"), "Only they can exit without cause",
                             f"{their} can end the contract at any time by giving notice, you cannot. Both should have the same right.",
                             {"op": "replace", "find": f"The {their} may terminate", "replace": "Either Party may terminate"},
                             c["termination"]["text"]))
        elif not v.get("convenience") and kind not in ("loan", "sale_immovable", "poa"):
            out.append(_risk("termination", lvl("termination"), "No right to end without cause",
                             "The contract can end only on a breach; you cannot exit by giving notice.", {}, c["termination"]["text"]))
    # auto renewal
    if on("auto_renewal") and v.get("auto_renew"):
        rn = v.get("renewal_notice_days") or nd
        out.append(_risk("auto_renewal", lvl("auto_renewal", "low"), "Renews automatically",
                         "If you do not want to renew, written notice is needed " + (f"{rn} days before" if rn else "in time") +
                         ". Hoola sets a reminder for the deadline.", {}, c["auto_renewal"]["text"]))
    # payment
    pd = v.get("payment_days")
    max_pd = int(num((pb.get("payment") or {}).get("value")) or 45)
    if on("payment") and pd and role in WE_GET_PAID and pd > max_pd:
        msme = " An MSME (Udyam) supplier must be paid by the buyer within 45 days (MSMED Act)." if meta.get("msme") else ""
        out.append(_risk("payment", lvl("payment"), f"Payment in {pd} days",
                         f"You are paid {pd} days after the invoice; your limit is {max_pd} days.{msme}",
                         {"op": "replace", "find": v.get("payment_phrase") or "", "replace": words_for(max_pd)} if v.get("payment_phrase") else {},
                         c["payment"]["text"]))
    # non-compete
    if on("non_compete") and c["non_compete"]["found"]:
        txt = c["non_compete"]["text"]
        after = re.search(r"\b(?:after|following|post)\b.{0,40}\b(?:termination|expiry|expiration|end|cessation)\b|\bthereafter\b", txt, re.I)
        on_us = (not our) or re.search(rf"\b{re.escape(our)}\b", txt, re.I) or re.search(r"\b(?:each|either) party\b", txt, re.I) or kind == "employment"
        if on_us:
            out.append(_risk("non_compete", lvl("non_compete", "high") if after else "medium",
                             "Non-compete" + (" even after the contract" if after else ""),
                             "Under Contract Act s.27 an agreement that stops work / trade (restraint of trade) is generally not enforceable, "
                             "especially after the contract ends (there are exceptions such as selling goodwill). It can still lead to a dispute: "
                             "better to have it removed." + (" (Delhi HC 2025 Varun Tyagi v Daffodil Software: post-employment non-compete void.)" if kind == "employment" else ""),
                             {"op": "delete", "find": _sentence(txt, r"compet|restraint")}, txt, "s27"))
    # IP
    if on("ip") and c["ip"]["found"] and role in ("vendor", "licensor", "employee") and their:
        t = c["ip"]["text"]
        if re.search(rf"\b(?:vest|belong|own|assign)\w*\b[^.]{{0,60}}\b{re.escape(their)}\b", t, re.I) and not re.search(
                r"pre-?existing|background|already owned|prior", t, re.I):
            out.append(_risk("ip", lvl("ip"), "All IP goes to the other party",
                             "All IP in the work becomes theirs and nothing protects what you built before (background IP).",
                             {"op": "insert", "after": "ip", "text": "Nothing in this Agreement transfers either Party's pre-existing intellectual property."}, t))
    # confidentiality
    if on("confidentiality"):
        t = c["confidentiality"]["text"]
        if not c["confidentiality"]["found"] and kind in ("nda", "msa", "service", "consultancy", "software", "vendor"):
            out.append(_risk("confidentiality", "medium" if kind == "nda" else "low", "No confidentiality clause", "No clause on keeping things confidential was found.",
                             {"op": "insert", "after": "", "text": pb["confidentiality"].get("standard_text", "")}))
        elif c["confidentiality"]["found"] and our and _who_does(t, r"(?:keep|maintain|hold)", labels) == our:
            out.append(_risk("confidentiality", lvl("confidentiality", "low"), "Confidentiality only on you",
                             "Only you must keep things confidential; the other party need not.", {}, t))
    # LD / penalty
    if on("liquidated_damages") and c["liquidated_damages"]["found"]:
        out.append(_risk("liquidated_damages", lvl("liquidated_damages"), "Penalty / liquidated damages",
                         "Contract Act s.74: a court gives only 'reasonable compensation', not necessarily the full written sum. Still, check the sum and "
                         "the cap: does it fall on you?", {}, c["liquidated_damages"]["text"], "s74"))
    # claim window
    cw = v.get("claim_window_months")
    if on("limitation") and cw is not None and cw < 36:
        out.append(_risk("limitation", lvl("limitation"), f"Claims only within {cw:g} months",
                         "The contract shortens the time to make a claim (the law generally gives 3 years). Contract Act s.28 makes such a term "
                         "largely unenforceable; have a lawyer confirm.", {}, c["limitation"]["text"]))
    # data
    if on("data_protection") and not c["data_protection"]["found"] and kind in ("msa", "service", "vendor", "software", "consultancy", "employment"):
        out.append(_risk("data_protection", lvl("data_protection", "low"), "No DPDP / personal data clause",
                         "If customer / staff personal data will be shared, a DPDP Act 2023 clause is needed.",
                         {"op": "insert", "after": "confidentiality" if c["confidentiality"]["found"] else "", "text": pb["data_protection"].get("standard_text", "")}))
    if on("force_majeure") and not c["force_majeure"]["found"] and kind in ("msa", "service", "vendor", "purchase", "distribution", "franchise", "software"):
        out.append(_risk("force_majeure", "low", "No force majeure", "It is not written what happens in events like a flood / lockdown."))
    # assignment
    if on("assignment") and c["assignment"]["found"] and re.search(r"\bwithout (?:the )?(?:prior )?(?:written )?consent\b", c["assignment"]["text"] or "", re.I) \
            and their and re.search(rf"\b{re.escape(their)}\b[^.]{{0,40}}\bmay\b[^.]{{0,30}}\bassign", c["assignment"]["text"], re.I):
        out.append(_risk("assignment", "low", "The other party can assign without asking",
                         "They can hand the contract to someone else and need not ask you.", {}, c["assignment"]["text"]))
    # term
    if on("term") and not v.get("end") and not v.get("term_months") and kind not in ("employment", "nda", "poa"):
        out.append(_risk("term", "low", "Term not clear", "No end date or term was found; enter the date in the register yourself."))
    # stamp
    if on("stamp") and not meta.get("stamp_paid"):
        out.append(_risk("stamp", lvl("stamp"), "No proof of stamp duty",
                         "If stamp duty is not paid, under Stamp Act s.35 the contract cannot be used as evidence in court until the duty + penalty is "
                         "paid (Supreme Court 7 judges, Dec 2023: the contract is not void, the defect can be cured). Get the e-stamp before signing / on the same "
                         "day; the rate is your state's.", source="stamp"))
    if kind in FIRST_SCHEDULE:
        out.append(_risk("signing", "high", "Cannot be e-signed",
                         f"IT Act First Schedule: {FIRST_SCHEDULE[kind]} cannot be signed electronically; physical signing (and, where needed, "
                         "registration) is required.", source="first_schedule"))
    order = {x: i for i, x in enumerate(LEVELS)}
    out.sort(key=lambda r: order.get(r["level"], 9))
    return out


def _sentence(text: str, word_rx: str) -> str:
    for s in re.split(r"(?<=[.;])\s+", text or ""):
        if re.search(word_rx, s, re.I) and re.search(r"\bshall\b|\bwill\b|\bagrees?\b|\bundertakes?\b", s, re.I):
            return s.strip()
    return ""


def score(risks: list[dict]) -> int:
    w = {"high": 25, "medium": 10, "low": 3}
    return max(0, 100 - sum(w.get(r["level"], 0) for r in risks))


# ---------------------------------------------------------------- stamp duty (HER rates only)
def stamp_calc(kind: str, state: str, value: float | None, rates: list[dict]) -> dict[str, Any]:
    """Her own rate rows: {kind, state, mode fixed|pct, rate, min, max, note}. No row = no number."""
    st = (state or "").strip().lower()
    row = next((r for r in rates or [] if r.get("kind") == kind and (not r.get("state") or str(r["state"]).lower() == st)), None)
    row = row or next((r for r in rates or [] if r.get("kind") in ("any", "*") and (not r.get("state") or str(r["state"]).lower() == st)), None)
    if not row:
        return {"amount": None, "say": f"{KINDS.get(kind, kind)} ({state or 'state?'}): you have not given the stamp rate. Add it under Rules or tell me the amount.",
                "row": None}
    rate = num(row.get("rate"))
    if rate is None:
        return {"amount": None, "say": "The rate is empty.", "row": row}
    if (row.get("mode") or "fixed") == "pct":
        if value is None:
            return {"amount": None, "say": "The contract value is needed (the rate is in %).", "row": row}
        amt = value * rate / 100
    else:
        amt = rate
    lo, hi = num(row.get("min")), num(row.get("max"))
    if lo is not None:
        amt = max(amt, lo)
    if hi is not None:
        amt = min(amt, hi)
    amt = float(round(amt))
    return {"amount": amt, "say": f"Stamp duty at your rate: Rs {amt:,.0f} ({row.get('note') or row.get('mode')}).", "row": row}


# ---------------------------------------------------------------- dates
def end_of(start: date | None, months: int | None, end: date | None) -> date | None:
    if end:
        return end
    if start and months:
        return add_months(start, months) - timedelta(days=1)
    return None


def notice_deadline(end: date | None, notice_days: int | None) -> date | None:
    return end - timedelta(days=int(notice_days)) if end and notice_days else None


def mask(text: str) -> str:
    """Contract text kept by Hoola: Aadhaar, card / account-like numbers, PAN, OTP / PIN / password values hidden."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [removed]", t, flags=re.I)
    t = re.sub(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)", "[Aadhaar removed]", t)
    t = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[number removed]", t)
    t = re.sub(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b", "[PAN removed]", t)
    return t
