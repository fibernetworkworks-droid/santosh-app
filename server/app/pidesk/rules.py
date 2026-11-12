"""PI Desk rules: what this desk refuses (in code), identifier format checks, red-flag words, tamper SIGNALS, chat-export
timelines, chain-of-custody hashing and complaint drafts. Pure functions (no DB) so tests can call them directly.

The desk is for BUSINESSES: due diligence on a company / firm / vendor / customer business from public official registries, checks
on documents she holds, and evidence files for police / 1930 / court. It never locates, tracks, watches or profiles a private
individual, never gets phone / CDR / bank records, never pretexts. Everything it says is "signals, not verdicts"."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

DISCLAIMER = ("This is check information (signals, not verdicts), not legal advice. Every fact carries its source; "
              "confirm with a lawyer / CA / police before you decide.")

NEVER = [
    "Finding a private individual's address, home, office, phone or location, following or watching them",
    "Social-media profiling of a person, 'what they do online'",
    "Checks on a husband / wife / relationship / before a wedding (pre-matrimonial), affair / loyalty checks",
    "Getting phone CDRs / call records / SIM details, bank statements / account details (only by police / court order)",
    "GPS trackers, spyware, secret recording, getting into someone's phone / account",
    "Pretexting: getting information by lying (posing as a bank / police / courier)",
    "Employee / candidate background checks without their signed consent; even with consent, only checks tied to the role",
    "Sending a report to anyone else without your tap in the app",
]

# ---------------------------------------------------------------- refusal in code
_REFUSE: list[tuple[str, str, str]] = [
    ("locate", r"(kaha[n]?\s*(reh|rah)(ta|ti|te)|ghar\s*ka\s*pata|address\s*(dhoo?nd|nikal|pata|find|trace)|"
               r"(find|locate|trace)\s+(his|her|their|the)\s+(address|home|house|location|whereabouts)|whereabouts|"
               r"live\s*location|location\s*(nikal|batao|pata|track|trace|find)|kahan\s*hai\s*(woh|wo|vo)|"
               r"(kahan|kaha)\s*(kaam|naukri)\s*kar(ta|ti|te)|workplace\s+of|where\s+(does\s+)?(he|she)\s+(live|work|stay)s?|"
               r"(ghar|पता|ठिकाना)\s*(dhundh|dhoondh|ढूंढ|खोज)|कहाँ\s*रह)",
     "Finding a person's home / address / location / workplace is not this desk's job (privacy, Puttaswamy 2017; BNS s.78 stalking). "
     "If someone has cheated you, the police will find who they are and where: we make a police / 1930 complaint from your evidence."),
    ("track", r"\b(track|trace|tail|follow|stalk|surveil|spy|monitor)(ing|ed)?\s+(him|her|them|this\s+person|that\s+person|my\s+(wife|husband|partner|employee))|"
              r"peecha\s*kar|pichha\s*kar|nigrani|nigraani|jasoosi|jaasoosi|surveillance|gps\s*tracker|tracker\s*(laga|lagao|lagana)|"
              r"spy\s*app|spyware|phone\s*(hack|tap)|chupke\s*se\s*(record|dekh)|निगरानी|जासूसी|पीछा",
     "Following / watching a person, GPS trackers and spy apps are never done on this desk (BNS s.78 stalking, IT Act s.66E / s.72). "
     "A business can be checked from public government registries; for fraud, an evidence file + a police complaint."),
    ("records", r"\b(cdr|call\s*detail|call\s*record|call\s*history|sim\s*(details|owner|kiske\s*naam)|tower\s*location|"
                r"kisne\s*call\s*kiya|number\s*kiske\s*naam|bank\s*(statement|record|details|account\s*details)\s*(nikal|nikaal|chahiye|of|uska|uski)|"
                r"(uska|uski|unka)\s*bank\s*(statement|record|details|balance)\s*(nikal|chahiye|dekh)|whatsapp\s*(chat|message)s?\s*(nikal|padh)|email\s*hack|password\s*(nikal|crack))",
     "Phone CDRs, SIM and bank records, or someone else's chats / email, come only through a legal police / court order; Hoola does not "
     "even try to get them. You can write 'please obtain the records' in a police complaint."),
    ("social", r"(instagram|facebook|insta|twitter|x\.com|linkedin|snapchat|social\s*media)\s*(profile|account|se|pe|par)?\s*"
               r"(dekh|check|nikal|pata|stalk|profil|scan|search)|social[- ]media\s*profil|online\s*kya\s*kar(ta|ti)|"
               r"(uske|uski)\s*(posts|photos|dost|friends)|profile\s*(him|her|this\s+person)",
     "Social-media profiling of a person is not done on this desk. For a business we can look at public registries, court mentions and news (by "
     "business name)."),
    ("relation", r"\b(wife|husband|spouse|girlfriend|boyfriend|fianc[eé]e?|affair|extramarital|loyalty\s*(test|check)|cheating\s+on)\b|"
                 r"\b(pati|patni|biwi|ghar\s*wali|gharwali|mangetar|premi|premika)\b|pre[- ]?matrimonial|shaadi\s*se\s*pehle|"
                 r"rishte?\s*(ki|ke)\s*(jaanch|check)|(ladke|ladki)\s*(ka|ki)\s*(background|jaanch|check)|"
                 r"पति|पत्नी|रिश्ते\s*की\s*जांच|शादी\s*से\s*पहले",
     "Checks on a husband / wife / relationship / before a wedding are not done on this desk (privacy). In a family matter, talk to a lawyer; "
     "the legal route is a court / family court."),
    ("pretext", r"(ban\s*ke|banke|bankar|ban\s*kar)\s*(baat|call|phone|pooch)|pretend(ing)?\s+to\s+be|pose\s+as|posing\s+as|"
                r"jhoo?th\s*bol\s*(ke|kar)|fake\s*(call|caller|identity)\s*(karke|kar|se)|police\s*(ban|banke)|"
                r"impersonat",
     "Getting information by lying / posing as someone else (pretexting) is never done: it is fraud (BNS impersonation / "
     "cheating). Use a direct written request in your own name, or the legal route."),
    ("person_bg", r"(background\s*(check|verification|jaanch)|bgv|pura\s*record|criminal\s*record|police\s*record)\s*(of|ka|ki|nikal|chahiye)?\s*"
                  r"(neighbou?r|padosi|tenant\s*ke\s*ghar|kisi\s*insaan|this\s*person|us\s*aadmi|us\s*aurat|uska|uski)",
     "A background check on a person only with that person's signed consent, and only tied to a job / tenancy-like purpose (DPDP Act 2023). "
     "For an employee / candidate, open an 'employee_verify' case and attach their signed consent; police verification is done by the police."),
]
_REFUSE_RE = [(k, re.compile(p, re.I), m) for k, p, m in _REFUSE]


def guard(*texts: Any) -> dict | None:
    """None = fine. Else {category, say}: the desk refuses before anything is stored or searched."""
    t = " ".join(str(x or "") for x in texts)
    if not t.strip():
        return None
    for k, rx, msg in _REFUSE_RE:
        if rx.search(t):
            return {"category": k, "say": msg + " (This desk is only for business checks, checks on your documents and evidence files.)"}
    return None


# ---------------------------------------------------------------- business identifiers
CIN_TYPES = {"PLC": "public limited", "PTC": "private limited", "GOI": "Government of India company", "SGC": "state govt company",
             "FLC": "foreign (public)", "FTC": "foreign (private)", "NPL": "Section 8 / not for profit", "ULL": "unlimited (public)",
             "ULT": "unlimited (private)", "GAP": "guarantee (public)", "GAT": "guarantee (private)", "OPC": "one person company"}
_CIN = re.compile(r"^([LU])(\d{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$")
_LLPIN = re.compile(r"^[A-Z]{3}-\d{4}$")
_UDYAM = re.compile(r"^UDYAM-([A-Z]{2})-(\d{2})-(\d{7})$")
_PAN = re.compile(r"^[A-Z]{3}([ABCFGHJLPT])[A-Z]\d{4}[A-Z]$")
_FSSAI = re.compile(r"^\d{14}$")
_IEC = re.compile(r"^[A-Z0-9]{10}$")
PAN_KIND = {"C": "company", "F": "firm / LLP", "H": "HUF", "A": "AOP", "T": "trust", "B": "BOI", "L": "local authority",
            "J": "artificial juridical person", "G": "government", "P": "individual (personal)"}
ID_KINDS = ("gstin", "cin", "llpin", "udyam", "fssai", "pan", "iec")


def _norm(v: Any) -> str:
    return re.sub(r"\s+", "", str(v or "")).upper()


def guess_kind(v: str) -> str:
    x = _norm(v)
    if len(x) == 15 and re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]", x):
        return "gstin"
    if _CIN.match(x):
        return "cin"
    if _LLPIN.match(x):
        return "llpin"
    if x.startswith("UDYAM"):
        return "udyam"
    if _PAN.match(x):
        return "pan"
    if _FSSAI.match(x):
        return "fssai"
    return ""


def check_identifier(kind: str, value: str, today: date | None = None) -> dict:
    """Format / check-digit checks done by Hoola's own code: they say a number is WELL-FORMED, not that the business is real or
    active. Status always comes from the official page (read with its link)."""
    from ..india.money import STATE_CODES, gstin_info
    v = _norm(value)
    kind = (kind or guess_kind(v)).lower()
    today = today or date.today()
    out: dict[str, Any] = {"kind": kind, "value": v, "valid": False, "facts": [], "flags": [], "source": "Hoola format check (code)"}
    if kind == "gstin":
        info = gstin_info(v)
        out["valid"] = bool(info.get("valid"))
        if out["valid"]:
            out["facts"] += [f"GSTIN check digit correct, state code {v[:2]} = {info.get('state')}",
                             f"PAN part {v[2:12]}: entity type {info.get('kind')}"]
            out["state"] = info.get("state")
            if v[5] == "P":
                out["flags"].append("A proprietor's (individual's) PAN-based GSTIN: the PAN stays masked in the report.")
        else:
            out["flags"].append("GSTIN format / check digit wrong: this number cannot belong to a real registration (or it was mistyped).")
        out["official"] = {"label": "GST portal 'Search Taxpayer' (services.gst.gov.in)", "url": "https://services.gst.gov.in/services/searchtp"}
    elif kind == "cin":
        m = _CIN.match(v)
        if m:
            yr = int(m.group(4))
            out["valid"] = m.group(5) in CIN_TYPES and 1850 <= yr <= today.year
            out["facts"] += [f"Listed: {'yes (L)' if m.group(1) == 'L' else 'no (U)'}", f"Industry (NIC) code {m.group(2)}",
                             f"State code {m.group(3)}", f"Registration year {yr}", f"Type {m.group(5)} = {CIN_TYPES.get(m.group(5), '?')}"]
            if yr > today.year - 1:
                out["flags"].append(f"The company is very new ({yr}): little track record.")
            if not out["valid"]:
                out["flags"].append("The CIN type / year does not look right.")
        else:
            out["flags"].append("A CIN has 21 characters (like U12345MH2020PTC123456): wrong format.")
        out["official"] = {"label": "MCA 'Master Data' (mca.gov.in)", "url": "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"}
    elif kind == "llpin":
        out["valid"] = bool(_LLPIN.match(v))
        out["flags"] += [] if out["valid"] else ["An LLPIN looks like 'AAA-1234': wrong format."]
        out["official"] = {"label": "MCA 'Master Data' (mca.gov.in)", "url": "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"}
    elif kind == "udyam":
        m = _UDYAM.match(v)
        out["valid"] = bool(m)
        if m:
            out["facts"].append(f"Udyam state {m.group(1)}, district code {m.group(2)}")
        else:
            out["flags"].append("A Udyam number looks like 'UDYAM-XX-00-0000000': wrong format.")
        out["official"] = {"label": "Udyam 'Verify Udyam Registration Number' (udyamregistration.gov.in)",
                           "url": "https://udyamregistration.gov.in/Udyam_Verify.aspx"}
    elif kind == "fssai":
        out["valid"] = bool(_FSSAI.match(v))
        if out["valid"]:
            out["facts"].append("14-digit FSSAI number (format correct)")
        else:
            out["flags"].append("An FSSAI licence / registration number has 14 digits.")
        out["official"] = {"label": "FoSCoS 'FBO search' (foscos.fssai.gov.in)", "url": "https://foscos.fssai.gov.in/"}
    elif kind == "pan":
        m = _PAN.match(v)
        out["valid"] = bool(m)
        if m:
            out["facts"].append(f"PAN entity type: {PAN_KIND.get(m.group(1), '?')}")
            if m.group(1) == "P":
                out["flags"].append("This is an individual's PAN (personal data): it stays masked in the report; keep it in the ID Locker.")
                out["value"] = v[:2] + "XXX" + v[5:6] + "XXX" + v[-1]
                out["personal"] = True
        else:
            out["flags"].append("Wrong PAN format (AAAAA9999A).")
        out["official"] = {"label": "Income-tax 'Verify Your PAN' (incometax.gov.in, after login)",
                           "url": "https://www.incometax.gov.in/iec/foportal/"}
    elif kind == "iec":
        out["valid"] = bool(_IEC.match(v))
        out["official"] = {"label": "DGFT 'IEC view' (dgft.gov.in)", "url": "https://www.dgft.gov.in/"}
    else:
        out["kind"] = "unknown"
        out["flags"].append("Could not tell what this number is (GSTIN / CIN / LLPIN / Udyam / FSSAI / PAN / IEC).")
    out["note"] = "A correct format = the number is well-formed; whether the business is real / active is confirmed on the official page."
    if kind == "gstin" and v[:2] not in STATE_CODES:
        out["valid"] = False
    return out


# ---------------------------------------------------------------- pages and words
OFFICIAL_SUFFIX = (".gov.in", ".nic.in")
OFFICIAL_HOSTS = {"mca.gov.in", "www.mca.gov.in", "services.gst.gov.in", "www.gst.gov.in", "udyamregistration.gov.in",
                  "foscos.fssai.gov.in", "services.ecourts.gov.in", "ecourts.gov.in", "main.sci.gov.in", "www.sci.gov.in",
                  "dgft.gov.in", "www.dgft.gov.in", "njdg.ecourts.gov.in", "www.sebi.gov.in", "rbi.org.in", "www.rbi.org.in",
                  "nclt.gov.in", "ibbi.gov.in", "www.ibbi.gov.in", "epfindia.gov.in", "www.epfindia.gov.in"}


def is_official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in OFFICIAL_HOSTS or host.endswith(OFFICIAL_SUFFIX) or host in ("rbi.org.in", "sebi.gov.in")


STATUS_FLAGS = [
    (r"strike\s*off|struck\s*off|strike\s*-\s*off", "The company shows 'Strike Off' (MCA): do not deal with a closed company."),
    (r"under\s*(process\s*of\s*)?striking\s*off", "A strike-off process is under way."),
    (r"under\s*liquidation|liquidated|liquidator", "The page mentions liquidation / closure."),
    (r"\bcirp\b|insolvency|resolution\s*professional|\bnclt\b", "The page mentions insolvency (NCLT / IBC)."),
    (r"\bdormant\b", "The company shows 'Dormant' (not operating)."),
    (r"amalgamated|dissolved", "The company seems to have merged into another / been dissolved."),
    (r"\bcancel+ed\b|registration\s*cancel", "The registration shows 'Cancelled' (GST / licence)."),
    (r"\bsuspended\b", "The registration shows 'Suspended'."),
    (r"\binactive\b|\bexpired\b", "The status shows 'Inactive / Expired'."),
    (r"active\s*non[- ]?compliant|\bACTIVE\s*NON", "'Active Non-Compliant' on MCA (filings pending)."),
]
ADVERSE = [r"\bfraud\b", r"\bcheat(ing|ed)?\b", r"\barrest(ed)?\b", r"\braid(s|ed)?\b", r"\bED\b", r"\bCBI\b", r"\bFIR\b",
           r"gst\s*evasion|fake\s*invoic|bogus\s*bill", r"\bdefault(ed|er)?\b", r"\bponzi\b", r"\bscam\b", r"\bban(ned)?\b",
           r"blacklist", r"sebi\s*order|debarred", r"\bnclt\b|insolvency", r"money\s*laundering|\bpmla\b", r"dhokha|thagi|धोखा|ठगी"]
_ADV = [re.compile(p, re.I) for p in ADVERSE]


def status_flags(text: str) -> list[str]:
    out = []
    for p, msg in STATUS_FLAGS:
        if re.search(p, text or "", re.I) and msg not in out:
            out.append(msg)
    return out


def adverse_words(text: str) -> list[str]:
    hits = []
    for rx in _ADV:
        m = rx.search(text or "")
        if m and m.group(0).lower() not in hits:
            hits.append(m.group(0).lower())
    return hits


def snippets(text: str, needles: list[str], n: int = 8, width: int = 260) -> list[str]:
    """Lines of an official page that mention the subject (name / number). Page text = data."""
    keys = [k.lower() for k in needles if k and len(k) >= 3]
    out: list[str] = []
    for line in (text or "").splitlines():
        ln = " ".join(line.split())
        low = ln.lower()
        if ln and (not keys or any(k in low for k in keys) or any(re.search(p, ln, re.I) for p, _ in STATUS_FLAGS)):
            if ln[:width] not in out:
                out.append(ln[:width])
        if len(out) >= n:
            break
    return out


CNR_RE = re.compile(r"\b[A-Z]{4}\d{12}\b")


def court_bits(text: str) -> dict:
    """Her paste from eCourts / a High Court page: CNR numbers, case numbers, next dates, status words. Data, never instructions."""
    t = text or ""
    cnrs = sorted(set(CNR_RE.findall(t.upper())))
    cases = sorted(set(m.group(0) for m in re.finditer(r"\b[A-Z][A-Za-z.()/ ]{1,20}\s*(No\.?)?\s*\d{1,6}\s*/\s*(19|20)\d{2}\b", t)))[:20]
    dates = sorted(set(re.findall(r"\b\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)\d{2}\b", t)))[:20]
    status = [w for w in ("disposed", "pending", "dismissed", "decreed", "convicted", "acquitted", "withdrawn", "settled")
              if re.search(rf"\b{w}\b", t, re.I)]
    kinds = []
    for p, label in ((r"\b138\b.*N\.?\s*I\.?\s*Act|N\.?\s*I\.?\s*Act.*\b138\b|cheque\s*bounce", "cheque bounce (NI Act s.138)"),
                     (r"recovery|money\s*suit|summary\s*suit", "money recovery case"), (r"insolvency|\bIBC\b|\bCP\s*\(IB\)", "IBC / NCLT"),
                     (r"arbitration", "arbitration"), (r"consumer|e-?jagriti|NCDRC|DCDRC", "consumer forum")):
        if re.search(p, t, re.I):
            kinds.append(label)
    return {"cnr": cnrs[:20], "cases": cases, "dates": dates, "status": status, "kinds": kinds}


# ---------------------------------------------------------------- document tamper SIGNALS
EDIT_TOOLS = ["photoshop", "illustrator", "ilovepdf", "smallpdf", "sejda", "pdfescape", "canva", "pdf-xchange", "pdfelement",
              "foxit phantom", "inkscape", "gimp", "paint", "picsart", "snapseed", "pixlr", "lightroom", "word", "libreoffice",
              "pdf editor", "edit"]


def _when(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    s = str(v or "").strip()
    if not s:
        return None
    s = s.replace("D:", "")[:19]
    for f in ("%Y%m%d%H%M%S", "%Y:%m:%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M",
              "%Y-%m-%d %H:%M", "%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:len(datetime(2000, 1, 1).strftime(f))], f)
        except ValueError:
            continue
    return None


def pdf_signals(meta: dict, claimed: str = "") -> list[dict]:
    """meta: producer, creator, created, modified, eof_count, fonts, pages, signatures [{intact, whole_file, ...}], text_chars."""
    sig: list[dict] = []
    tool = f"{meta.get('producer') or ''} {meta.get('creator') or ''}".lower()
    hit = next((t for t in EDIT_TOOLS if t in tool and t not in ("word", "edit", "libreoffice")), "")
    if hit:
        sig.append({"level": "warn", "signal": f"PDF made / changed with an editing tool like '{hit}' ({(meta.get('producer') or meta.get('creator') or '')[:60]})",
                    "why": "Real government / bank / company PDFs usually come from their own systems; if an editing tool's name shows, look carefully."})
    elif any(t in tool for t in ("word", "libreoffice")):
        sig.append({"level": "info", "signal": "PDF made with Word / LibreOffice", "why": "Many small businesses make bills this way; on its own this proves nothing."})
    c, m = _when(meta.get("created")), _when(meta.get("modified"))
    if c and m and (m - c) > timedelta(minutes=2):
        sig.append({"level": "warn", "signal": f"Changed ({m:%d-%m-%Y %H:%M}) after it was made ({c:%d-%m-%Y %H:%M})",
                    "why": "The modify date is after the create date: the file was saved / edited again later."})
    eofs = int(meta.get("eof_count") or 0)
    sigs = meta.get("signatures") or []
    if eofs > 1 and not sigs:
        sig.append({"level": "warn", "signal": f"Changes were added to the PDF {eofs - 1} time(s) later (incremental save)",
                    "why": "Later updates in an unsigned PDF = someone may have added / changed something."})
    for s in sigs:
        if s.get("intact") is False or s.get("crypto_ok") is False:
            sig.append({"level": "strong", "signal": "PDF changed after the digital signature",
                        "why": "The signature is broken: the content changed after signing. Ask the issuer for the original copy."})
        elif s.get("intact") and not s.get("whole_file"):
            sig.append({"level": "warn", "signal": "The signature does not cover the whole file", "why": "Pages / form fields were added after signing."})
        elif s.get("intact"):
            sig.append({"level": "ok", "signal": f"Digital signature intact ({(s.get('signer') or '')[:60]})",
                        "why": "The file has not changed since signing. Trust in the signer (CCA root) is not checked here."})
    fonts = meta.get("fonts") or []
    pages = max(1, int(meta.get("pages") or 1))
    if len(fonts) >= 6 + 2 * pages:
        sig.append({"level": "info", "signal": f"{len(fonts)} different fonts", "why": "Many fonts are sometimes a sign of copy-paste / editing."})
    fams = {}
    for f in fonts:
        base = re.sub(r"^[A-Z]{6}\+", "", str(f))
        fams.setdefault(re.split(r"[-,]", base)[0].lower(), set()).add(str(f))
    dup = [k for k, v in fams.items() if len(v) > 2]
    if dup:
        sig.append({"level": "info", "signal": f"Several separate subsets of one font ({', '.join(dup[:3])})",
                    "why": "Separate embedded parts of one font are sometimes a sign of a line added later."})
    cd = _when(claimed)
    if cd and c:
        if c.date() > cd.date() + timedelta(days=30):
            sig.append({"level": "warn", "signal": f"File made on {c:%d-%m-%Y}; date on the document {cd:%d-%m-%Y}",
                        "why": "The file was made well after the document's date. It may also be a scan / reprint: ask the issuer."})
        elif c.date() < cd.date() - timedelta(days=1):
            sig.append({"level": "warn", "signal": f"File made on {c:%d-%m-%Y}, BEFORE the document date {cd:%d-%m-%Y}",
                        "why": "How was the document made before its own date? Look carefully."})
    if meta.get("pages") and not meta.get("text_chars"):
        sig.append({"level": "info", "signal": "No text in the PDF, only an image (scan)", "why": "Edits are hard to catch in a scan: ask for the original or a digital copy."})
    return sig


def image_signals(exif: dict, claimed: str = "") -> list[dict]:
    """exif: has_exif, software, original, modified, make, model."""
    sig: list[dict] = []
    if not exif.get("has_exif"):
        sig.append({"level": "info", "signal": "The photo has no EXIF (camera / date)",
                    "why": "WhatsApp / screenshots / social media remove EXIF: this proves nothing."})
        return sig
    sw = str(exif.get("software") or "").lower()
    hit = next((t for t in EDIT_TOOLS if t in sw and t not in ("word", "libreoffice")), "")
    if hit:
        sig.append({"level": "warn", "signal": f"Photo editing software name: {exif.get('software')}", "why": "The photo was edited / saved again."})
    o, m = _when(exif.get("original")), _when(exif.get("modified"))
    if o and m and (m - o) > timedelta(minutes=5):
        sig.append({"level": "info", "signal": f"Photo taken {o:%d-%m-%Y %H:%M}, changed {m:%d-%m-%Y %H:%M}", "why": "Saved / edited later."})
    cd = _when(claimed)
    if cd and o and abs((o.date() - cd.date()).days) > 1:
        sig.append({"level": "warn", "signal": f"Photo camera date {o:%d-%m-%Y}, stated date {cd:%d-%m-%Y}",
                    "why": "The camera clock can be wrong; but this difference is worth noting."})
    if o and not cd:
        sig.append({"level": "info", "signal": f"Photo taken: {o:%d-%m-%Y %H:%M} ({exif.get('make') or ''} {exif.get('model') or ''})".strip(),
                    "why": "By the camera's own clock."})
    return sig


def einvoice_signals(inv: dict, expect: dict) -> list[dict]:
    """The IRP QR's own data vs what the printed bill says (her numbers). A mismatch is a strong signal."""
    sig = []
    pairs = (("seller_gstin", "gstin", "GSTIN"), ("doc_no", "doc_no", "Bill number"), ("total", "total", "Total"),
             ("doc_date", "doc_date", "Date"))
    for qk, ek, label in pairs:
        e = expect.get(ek)
        q = inv.get(qk)
        if e in (None, "") or q in (None, ""):
            continue
        same = (abs(_num(q) - _num(e)) < 1.0) if qk == "total" and _num(q) is not None and _num(e) is not None else (
            _norm(q) == _norm(e))
        sig.append({"level": "ok" if same else "strong", "signal": f"{label}: '{q}' in the QR, '{e}' on the document",
                    "why": "The QR is from the IRP (the government e-invoice system); if the printed part is changed it does not match the QR." if not same else "It matches."})
    for k in ("seller_gstin_valid", "buyer_gstin_valid"):
        if inv.get(k) is False:
            sig.append({"level": "warn", "signal": f"Wrong check digit in the QR's {k.split('_')[0]} GSTIN", "why": "This should not happen in a real IRP QR."})
    sig.append({"level": "info", "signal": "The IRP digital signature was not verified here",
                "why": "To confirm, use 'Verify Signed QR' on the e-invoice portal (einvoice1.gst.gov.in)."})
    return sig


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def summary_level(signals: list[dict]) -> str:
    lv = [s.get("level") for s in signals]
    if "strong" in lv:
        return "strong"
    if lv.count("warn") >= 2:
        return "several"
    if "warn" in lv:
        return "some"
    return "none"


LEVEL_SAY = {"strong": "Strong signal: there are signs of changes in the document. Ask the issuer for the original copy.",
             "several": "Several signals: check carefully, confirm with the issuer.",
             "some": "One signal found: on its own it proves nothing; confirm with the issuer.",
             "none": "No particular signal found. This does not mean the document is genuine; only that this check showed nothing."}


# ---------------------------------------------------------------- chat exports -> timeline
_WA_ANDROID = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2})(?:\s?([apAP]\.?[mM]\.?))?\s+-\s+([^:]{1,60}):\s?(.*)$")
_WA_IOS = re.compile(r"^‎?\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2})(?::\d{2})?(?:\s?([apAP][mM]))?\]\s+([^:]{1,60}):\s?(.*)$")
MONEY_WORDS = re.compile(r"(?i)\bupi\b|paise|paisa|transfer|₹|\brs\.?\b|\binr\b|account|a/c|\botp\b|link|kyc|refund|payment|bhej|"
                         r"advance|deposit|invoice|order|deliver|utr|\bref\b")


def mask_text(t: str) -> str:
    t = re.sub(r"(?i)\b(otp|pin|cvv|password|upi pin|mpin)\b\s*(is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [removed]", t or "")
    t = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[number removed]", t)
    t = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[number removed]", t)
    return t


def _wa_dt(d: str, tm: str, ap: str | None) -> datetime | None:
    try:
        dd, mm, yy = (int(x) for x in d.split("/"))
        if yy < 100:
            yy += 2000
        hh, mi = (int(x) for x in tm.split(":"))
        a = (ap or "").lower().replace(".", "")
        if a == "pm" and hh < 12:
            hh += 12
        if a == "am" and hh == 12:
            hh = 0
        return datetime(yy, mm, dd, hh, mi)
    except (ValueError, TypeError):
        return None


def parse_chat(text: str, limit: int = 400) -> list[dict]:
    """WhatsApp 'Export chat' text (Android and iPhone lines). Each message -> {at, who, text (masked), important}."""
    out: list[dict] = []
    for raw in (text or "").splitlines():
        line = raw.strip("﻿‎ ")
        m = _WA_ANDROID.match(line) or _WA_IOS.match(line)
        if m:
            at = _wa_dt(m.group(1), m.group(2), m.group(3))
            if at is None:
                continue
            msg = mask_text(m.group(5))[:300]
            out.append({"at": at.isoformat(timespec="minutes"), "who": m.group(4).strip()[:60], "text": msg,
                        "important": bool(MONEY_WORDS.search(msg))})
        elif out and line:
            out[-1]["text"] = (out[-1]["text"] + " " + mask_text(line))[:300]
            out[-1]["important"] = out[-1]["important"] or bool(MONEY_WORDS.search(line))
        if len(out) >= limit:
            break
    return out


UTR_RE = re.compile(r"\b(?:UTR|RRN|Ref(?:erence)?\.?\s*(?:No\.?)?|UPI\s*Ref\.?\s*(?:No\.?)?|Txn\s*ID)\s*[:#-]?\s*([A-Z0-9]{10,22})\b", re.I)
AMT_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.I)


def money_bits(text: str) -> dict:
    """UTR / reference numbers and amounts from a receipt / bank SMS text she shares (for the complaint; never looked up)."""
    refs = sorted(set(m.group(1).upper() for m in UTR_RE.finditer(text or "")))[:10]
    amts = []
    for m in AMT_RE.finditer(text or ""):
        v = _num(m.group(1))
        if v and v not in amts:
            amts.append(v)
    return {"refs": refs, "amounts": amts[:10]}


# ---------------------------------------------------------------- chain of custody
def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chain_hash(prev: str, entry: dict) -> str:
    return hashlib.sha256((prev + "|" + json.dumps(entry, sort_keys=True, ensure_ascii=False, default=str)).encode()).hexdigest()


# ---------------------------------------------------------------- complaints
COMPLAINT_TO = {
    "cyber": {"label": "Cyber crime (NCRP / 1930)", "how": [
        "If money has gone, call 1930 AT ONCE (the sooner, the better the chance of stopping the money).",
        "On cybercrime.gov.in, 'Report Cyber Crime' -> financial fraud: upload the text below and the evidence (screenshots, UTR).",
        "Give Hoola the complaint / acknowledgement number; it will be added to the file."]},
    "police": {"label": "Police station (written complaint / FIR)", "how": [
        "Print the text below and hand it in at the police station; be sure to get a receipt (stamp + date).",
        "In a cognizable case, registering the FIR is the police's duty (BNSS 2023 s.173; old CrPC s.154); many states also have e-FIR.",
        "Hand in the evidence pen drive / prints with the index (SHA-256)."]},
    "bank": {"label": "Bank (unauthorised transaction)", "how": [
        "Report to the bank at once (within 3 working days) in writing / in the app: under the RBI circular of 6 Jul 2017, a prompt report "
        "makes the customer's liability zero / limited.",
        "Get a complaint number; if it is not resolved in 30 days, go to the RBI Integrated Ombudsman (cms.rbi.org.in)."]},
}
OFFENCE_LINE = "Sections that apply: [to be decided by the police / lawyer]"


def complaint_text(to: str, me: dict, case: dict, timeline: list[dict], evidence: list[dict], money: dict) -> str:
    who = me.get("firm") or me.get("name") or "[your name / firm]"
    lines = []
    if to == "bank":
        lines.append("To, The Branch Manager / Grievance Cell, [bank name]")
    elif to == "police":
        lines.append("To, The Station House Officer (SHO), [police station], [city]")
    else:
        lines.append("National Cyber Crime Reporting Portal (cybercrime.gov.in) / 1930")
    lines += ["", f"Subject: {case.get('title') or 'Complaint of fraud'}", "",
              f"I, {who} ({me.get('address') or '[address]'}, {me.get('phone') or '[phone]'}), make this complaint.", ""]
    if money.get("lost"):
        lines.append(f"Total loss: Rs {money['lost']:,.2f} (" + ", ".join(money.get("refs") or ["[UTR / reference]"]) + ")")
    if case.get("suspect"):
        lines.append("Identity used in the fraud by the other party (as I saw it): " + case["suspect"])
    lines += ["", "Sequence of events (timeline):"]
    for i, e in enumerate(timeline[:40], 1):
        lines.append(f"{i}. {e.get('at', '')[:16].replace('T', ' ')} - {e.get('what', '')}")
    lines += ["", "Evidence (SHA-256 hash of each file, so it can be shown the file has not changed):"]
    for i, e in enumerate(evidence[:40], 1):
        lines.append(f"{i}. {e.get('name')} - SHA-256 {e.get('sha256')}")
    lines += ["", OFFENCE_LINE, "", "I request that the case be registered and appropriate action taken.", "",
              f"{who}", "Date: [date]", "Signature: [signature]"]
    return "\n".join(lines)


def bsa63_draft(case: dict, evidence: list[dict], me: dict) -> str:
    """Part A style details of a s.63(4) BSA certificate (the electronic record + hash). Part B (expert) is not Hoola's."""
    lines = ["DRAFT - details for Part A of the Bharatiya Sakshya Adhiniyam 2023, s.63(4) certificate (have a lawyer confirm the format)",
             f"Case: {case.get('number')} {case.get('title') or ''}", f"Given by: {me.get('name') or '[name]'} ({me.get('firm') or ''})",
             "Device / source: [the phone / computer the record was taken from]", "Hash algorithm: SHA-256", ""]
    for i, e in enumerate(evidence, 1):
        lines.append(f"{i}. {e.get('name')} | {e.get('size')} bytes | SHA-256 {e.get('sha256')} | received by Hoola {e.get('received_at', '')[:16]}")
    lines += ["", "Part B (expert certificate) from a computer / cyber forensics expert: Hoola does not give this.",
              "Signature: [signature]   Date: [date]   Place: [place]"]
    return "\n".join(lines)


CONSENT_TEXT = ("I, {candidate}, of my own free will allow {firm} to check the documents I have given (identity, education, previous job, address), "
                "only for this job ({role}). These checks: {checks}. I have been told "
                "how long the data will be kept ({days} days) and that I can withdraw my consent. Signature: ________ Date: ________")
EMPLOY_CHECKS = {"identity": "identity documents (given by the candidate)", "education": "education certificates (confirmed with the institution)",
                 "employment": "previous job (confirmed with the employer the candidate named)", "address": "address (from a document the candidate gave)"}

SOURCES = [
    "verdictum.in 1 Aug 2026: HC v State of Rajasthan, 2026 INSC 778 - private investigation 'an area sans regulation', copy to Law "
    "Ministry + Law Commission; Private Detective Agencies (Regulation) Bill 2007 never enacted "
    "(https://www.verdictum.in/supreme-court/hc-v-state-of-rajasthan-anr-2026-insc-778-private-investigators-privacy-1618984)",
    "livelaw.in 28 May 2026: Supreme Court (22 May 2026) upheld BSA s.63(4) - certificate Part A with hash value, Part B expert "
    "(https://www.livelaw.in/amp/top-stories/supreme-court-rejects-challenge-to-s634-bsa-mandating-hash-value-disclosure-for-electronic-evidence-535950)",
    "ksandk.com 16 / 30 Sep 2026: DPDP and employee background verification - s.7(i) not a clear basis for pre-hire checks; notice + "
    "purpose-specific consent; checks limited to the role (https://ksandk.com/data-protection-and-data-privacy/employee-background-verification-and-pre-employment-screening-under-the-dpdp-act/)",
    "K.S. Puttaswamy v Union of India (2017) 10 SCC 1 - privacy a fundamental right; BNS 2023 s.78 stalking; IT Act 2000 s.66E "
    "(private images), s.72 (confidentiality); BNSS 2023 s.173 FIR (old CrPC s.154) - in force 1 Jul 2024",
    "RBI circular RBI/2017-18/15 (6 Jul 2017) customer protection - limited liability in unauthorised electronic transactions "
    "(report within 3 working days = zero liability) (https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040)",
    "cybercrime.gov.in National Cyber Crime Reporting Portal + helpline 1930 (MHA I4C)",
    "MCA Master Data (mca.gov.in), GST Search Taxpayer (services.gst.gov.in), Udyam verify (udyamregistration.gov.in), FoSCoS "
    "(foscos.fssai.gov.in), eCourts services (services.ecourts.gov.in) - public official pages, read one page at a time",
]
