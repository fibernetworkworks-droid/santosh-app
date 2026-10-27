"""Legalres rules (pure functions, no database): official sources, the old-law -> new-law table (IPC -> BNS, CrPC -> BNSS,
Evidence Act -> BSA), section / citation finders and the GROUNDING check that keeps every cited section or judgment tied to a
source Hoola actually read.

House rule: Hoola is not a lawyer. A citation is shown only when it is in the text of a source that was fetched in this research;
anything else becomes "[citation chahiye]". The mapping table is jaankari (each row says how sure it is), never a substitute for the
bare act on India Code."""
from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

DISCLAIMER = ("Yeh legal research ka draft / jaankari hai, legal advice nahi. Har citation us source se hai jo Hoola ne padha (link + "
              "asli hissa); vakil se pakka karwaiye.")
NAHI_MILA = "Padhe gaye sources mein iska pakka jawab nahi mila."
NEED_CITE = "[citation chahiye]"
IK_ATTRIBUTION = "Judgments / search: powered by IKanoon (api.indiankanoon.org)"

NEVER = [
    "Legal advice ya case ka nateeja: kabhi nahi (sirf research draft, vakil decide karein).",
    "Koi section / judgment / citation jo kisi padhe gaye source mein nahi: kabhi nahi -> '[citation chahiye]'.",
    "Court / sarkari site ki bulk scraping ya CAPTCHA todna: kabhi nahi; sirf official public pages, Indian Kanoon ki official API (aapki key).",
    "Memo bahar bhejna (client / vakil / kisi ko): sirf aapke app ke tap se.",
    "Ek client / matter ki baat doosre matter mein: kabhi nahi.",
    "API key chat mein: kabhi nahi (sirf app mein, sealed).",
]

# Official public hosts whose pages count as "official" (read with web.open_website). Everything under gov.in / nic.in is government.
OFFICIAL_EXACT = {"indiacode.nic.in", "sci.gov.in", "main.sci.gov.in", "digiscr.sci.gov.in", "egazette.gov.in", "ecourts.gov.in",
                  "services.ecourts.gov.in", "judgments.ecourts.gov.in", "njdg.ecourts.gov.in", "legislative.gov.in", "lawmin.gov.in",
                  "mha.gov.in", "rbi.org.in", "sebi.gov.in", "incometaxindia.gov.in", "cbic.gov.in", "mca.gov.in", "irdai.gov.in",
                  "trai.gov.in", "nclt.gov.in", "nclat.nic.in", "greentribunal.gov.in", "meity.gov.in", "dpdpboard.gov.in"}
OFFICIAL_SUFFIX = (".gov.in", ".nic.in")


def host(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def official(url: str) -> bool:
    h = host(url)
    if not h or not str(url).lower().startswith("https://") and not str(url).lower().startswith("http://"):
        return False
    return h in OFFICIAL_EXACT or h.endswith(OFFICIAL_SUFFIX) or h in ("gov.in", "nic.in")


# ---------------------------------------------------------------- acts (official India Code pages)
ACTS = {
    "IPC": {"name": "Indian Penal Code, 1860", "new": "BNS", "repealed": "1 Jul 2024 (BNS s.358)"},
    "CRPC": {"name": "Code of Criminal Procedure, 1973", "new": "BNSS", "repealed": "1 Jul 2024 (BNSS s.531)"},
    "IEA": {"name": "Indian Evidence Act, 1872", "new": "BSA", "repealed": "1 Jul 2024 (BSA s.170)"},
    "BNS": {"name": "Bharatiya Nyaya Sanhita, 2023 (Act 45 of 2023)", "url": "https://www.indiacode.nic.in/handle/123456789/20062"},
    "BNSS": {"name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (Act 46 of 2023)", "url": "https://www.indiacode.nic.in/handle/123456789/20099"},
    "BSA": {"name": "Bharatiya Sakshya Adhiniyam, 2023 (Act 47 of 2023)",
            "url": "https://www.indiacode.nic.in/simple-search?query=Bharatiya+Sakshya+Adhiniyam"},
}
NEW_LAW_FROM = "1 July 2024 (notifications of 23 Feb 2024; offences / proceedings before that date stay under the old law: BNSS s.531)"

# (old act, old section, new act, new section, subject, sure)
# sure=True: the section-level pairing matches a published conversion table (lawsikho.com IPC->BNS table, 2026) AND Hoola's own
# reading; sure=False ("andaaza"): commonly cited pairing, sub-section / pairing to be checked on India Code before use.
MAPPING: list[tuple[str, str, str, str, str, bool]] = [
    # IPC -> BNS
    ("IPC", "34", "BNS", "3(5)", "Common intention", True),
    ("IPC", "107", "BNS", "45", "Abetment of a thing", True),
    ("IPC", "109", "BNS", "49", "Punishment of abetment if act committed", False),
    ("IPC", "120B", "BNS", "61(2)", "Criminal conspiracy (punishment)", True),
    ("IPC", "124A", "BNS", "152", "Sedition removed; s.152 is a different offence (sovereignty, unity and integrity)", False),
    ("IPC", "141", "BNS", "189(1)", "Unlawful assembly", False),
    ("IPC", "143", "BNS", "189(2)", "Member of unlawful assembly", True),
    ("IPC", "147", "BNS", "191(2)", "Rioting", True),
    ("IPC", "148", "BNS", "191(3)", "Rioting armed with deadly weapon", False),
    ("IPC", "149", "BNS", "190", "Common object of unlawful assembly", True),
    ("IPC", "153A", "BNS", "196", "Promoting enmity between groups", True),
    ("IPC", "186", "BNS", "221", "Obstructing public servant", False),
    ("IPC", "201", "BNS", "238", "Causing disappearance of evidence", False),
    ("IPC", "279", "BNS", "281", "Rash driving on a public way", False),
    ("IPC", "294", "BNS", "296", "Obscene acts and songs", False),
    ("IPC", "295A", "BNS", "299", "Outraging religious feelings", True),
    ("IPC", "299", "BNS", "100", "Culpable homicide (definition)", True),
    ("IPC", "300", "BNS", "101", "Murder (definition)", True),
    ("IPC", "302", "BNS", "103(1)", "Punishment for murder (BNS s.302 is a DIFFERENT offence)", True),
    ("IPC", "304", "BNS", "105", "Culpable homicide not amounting to murder", True),
    ("IPC", "304A", "BNS", "106(1)", "Causing death by negligence", True),
    ("IPC", "304B", "BNS", "80", "Dowry death", True),
    ("IPC", "306", "BNS", "108", "Abetment of suicide", False),
    ("IPC", "307", "BNS", "109", "Attempt to murder", True),
    ("IPC", "323", "BNS", "115(2)", "Voluntarily causing hurt", True),
    ("IPC", "324", "BNS", "118(1)", "Hurt by dangerous weapons or means", False),
    ("IPC", "325", "BNS", "117(2)", "Voluntarily causing grievous hurt", False),
    ("IPC", "326", "BNS", "118(2)", "Grievous hurt by dangerous weapons (one table says 119: check)", False),
    ("IPC", "341", "BNS", "126(2)", "Wrongful restraint", False),
    ("IPC", "342", "BNS", "127(2)", "Wrongful confinement", False),
    ("IPC", "353", "BNS", "132", "Assault to deter public servant", False),
    ("IPC", "354", "BNS", "74", "Assault to outrage modesty of a woman", True),
    ("IPC", "354A", "BNS", "75", "Sexual harassment", True),
    ("IPC", "354B", "BNS", "76", "Assault with intent to disrobe", True),
    ("IPC", "354C", "BNS", "77", "Voyeurism", True),
    ("IPC", "354D", "BNS", "78", "Stalking", True),
    ("IPC", "363", "BNS", "137(2)", "Kidnapping (punishment)", True),
    ("IPC", "366", "BNS", "87", "Kidnapping to compel marriage (one table says 138: check)", False),
    ("IPC", "376", "BNS", "64", "Rape (punishment)", True),
    ("IPC", "376D", "BNS", "70", "Gang rape", True),
    ("IPC", "379", "BNS", "303(2)", "Theft (punishment)", True),
    ("IPC", "380", "BNS", "305", "Theft in dwelling house", True),
    ("IPC", "384", "BNS", "308(2)", "Extortion (punishment)", True),
    ("IPC", "392", "BNS", "309(4)", "Robbery (punishment)", True),
    ("IPC", "395", "BNS", "310(2)", "Dacoity (punishment)", False),
    ("IPC", "406", "BNS", "316(2)", "Criminal breach of trust", True),
    ("IPC", "409", "BNS", "316(5)", "CBT by public servant / banker / agent", False),
    ("IPC", "415", "BNS", "318(1)", "Cheating (definition)", False),
    ("IPC", "417", "BNS", "318(2)", "Punishment for cheating", False),
    ("IPC", "419", "BNS", "319(2)", "Cheating by personation", False),
    ("IPC", "420", "BNS", "318(4)", "Cheating and dishonestly inducing delivery of property", True),
    ("IPC", "425", "BNS", "324(1)", "Mischief (definition)", False),
    ("IPC", "447", "BNS", "329(3)", "Criminal trespass (punishment)", False),
    ("IPC", "448", "BNS", "329(4)", "House-trespass (punishment)", False),
    ("IPC", "463", "BNS", "336(1)", "Forgery (definition)", True),
    ("IPC", "465", "BNS", "336(2)", "Punishment for forgery", True),
    ("IPC", "467", "BNS", "338", "Forgery of valuable security / will", True),
    ("IPC", "468", "BNS", "336(3)", "Forgery for cheating (one table says 339: check)", False),
    ("IPC", "471", "BNS", "340(2)", "Using a forged document as genuine", False),
    ("IPC", "489A", "BNS", "178", "Counterfeiting currency notes", False),
    ("IPC", "498A", "BNS", "85", "Cruelty by husband or relatives", True),
    ("IPC", "499", "BNS", "356(1)", "Defamation (definition)", False),
    ("IPC", "500", "BNS", "356(2)", "Punishment for defamation", True),
    ("IPC", "504", "BNS", "352", "Intentional insult to provoke breach of peace", False),
    ("IPC", "505", "BNS", "353", "Statements conducing to public mischief (one table says 197: check)", False),
    ("IPC", "506", "BNS", "351(2)", "Criminal intimidation (punishment; second part 351(3))", True),
    ("IPC", "509", "BNS", "79", "Word / gesture to insult modesty of a woman", True),
    ("IPC", "511", "BNS", "62", "Attempt to commit offences", False),
    # CrPC -> BNSS
    ("CRPC", "41", "BNSS", "35", "Arrest without warrant", True),
    ("CRPC", "41A", "BNSS", "35(3)", "Notice of appearance before police", False),
    ("CRPC", "91", "BNSS", "94", "Summons to produce document", False),
    ("CRPC", "102", "BNSS", "106", "Police power to seize property", False),
    ("CRPC", "107", "BNSS", "126", "Security for keeping the peace", False),
    ("CRPC", "125", "BNSS", "144", "Maintenance of wives, children and parents", False),
    ("CRPC", "144", "BNSS", "163", "Urgent cases of nuisance / apprehended danger", False),
    ("CRPC", "154", "BNSS", "173", "Information in cognizable cases (FIR)", True),
    ("CRPC", "155", "BNSS", "174", "Non-cognizable cases", False),
    ("CRPC", "156", "BNSS", "175", "Police power to investigate (156(3) -> 175(3))", False),
    ("CRPC", "161", "BNSS", "180", "Examination of witnesses by police", True),
    ("CRPC", "164", "BNSS", "183", "Recording confessions and statements", True),
    ("CRPC", "167", "BNSS", "187", "Remand / procedure when investigation not completed in 24 h", True),
    ("CRPC", "173", "BNSS", "193", "Police report on completion of investigation", True),
    ("CRPC", "190", "BNSS", "210", "Cognizance of offences by Magistrates", False),
    ("CRPC", "197", "BNSS", "218", "Prosecution of judges and public servants", True),
    ("CRPC", "200", "BNSS", "223", "Examination of complainant", False),
    ("CRPC", "207", "BNSS", "230", "Supply of copies to accused", False),
    ("CRPC", "227", "BNSS", "250", "Discharge (Sessions)", False),
    ("CRPC", "239", "BNSS", "262", "Discharge (warrant case on police report)", False),
    ("CRPC", "300", "BNSS", "337", "Not to be tried twice for the same offence", False),
    ("CRPC", "313", "BNSS", "351", "Power to examine the accused", False),
    ("CRPC", "320", "BNSS", "359", "Compounding of offences", False),
    ("CRPC", "374", "BNSS", "415", "Appeals from convictions", False),
    ("CRPC", "378", "BNSS", "419", "Appeal in case of acquittal", False),
    ("CRPC", "397", "BNSS", "438", "Calling for records to exercise revision", False),
    ("CRPC", "436", "BNSS", "478", "Bail in bailable offences", False),
    ("CRPC", "436A", "BNSS", "479", "Maximum period of undertrial detention", False),
    ("CRPC", "437", "BNSS", "480", "Bail in non-bailable offences", False),
    ("CRPC", "438", "BNSS", "482", "Anticipatory bail", True),
    ("CRPC", "439", "BNSS", "483", "Special powers of High Court / Sessions regarding bail", True),
    ("CRPC", "468", "BNSS", "514", "Bar to taking cognizance after limitation", False),
    ("CRPC", "482", "BNSS", "528", "Inherent powers of High Court", True),
    # Evidence Act -> BSA
    ("IEA", "3", "BSA", "2", "Definitions (incl. evidence, document)", False),
    ("IEA", "24", "BSA", "22", "Confession caused by inducement / threat", False),
    ("IEA", "25", "BSA", "23(1)", "Confession to police officer", False),
    ("IEA", "26", "BSA", "23(2)", "Confession in police custody", False),
    ("IEA", "27", "BSA", "23(2) proviso", "Information leading to discovery", True),
    ("IEA", "30", "BSA", "24", "Confession of co-accused", False),
    ("IEA", "32", "BSA", "26", "Statements of persons who cannot be called (dying declaration)", False),
    ("IEA", "45", "BSA", "39", "Opinions of experts", True),
    ("IEA", "63", "BSA", "58", "Secondary evidence", False),
    ("IEA", "65", "BSA", "60", "Cases where secondary evidence may be given", False),
    ("IEA", "65B", "BSA", "63", "Admissibility of electronic records (certificate: 63(4))", True),
    ("IEA", "101", "BSA", "104", "Burden of proof", False),
    ("IEA", "106", "BSA", "109", "Burden of proving fact especially within knowledge", False),
    ("IEA", "113A", "BSA", "117", "Presumption as to abetment of suicide by a married woman", False),
    ("IEA", "113B", "BSA", "118", "Presumption as to dowry death", False),
    ("IEA", "114", "BSA", "119", "Court may presume existence of certain facts", False),
    ("IEA", "115", "BSA", "121", "Estoppel", False),
    ("IEA", "118", "BSA", "124", "Who may testify", False),
    ("IEA", "137", "BSA", "142", "Examination-in-chief, cross, re-examination", False),
    ("IEA", "145", "BSA", "148", "Cross-examination as to previous statements in writing", False),
    ("IEA", "154", "BSA", "157", "Question by party to his own witness (hostile)", False),
    ("IEA", "165", "BSA", "168", "Judge's power to put questions", False),
]
REMOVED = {("IPC", "309"): "Attempt to suicide: BNS mein nahi (removed).", ("IPC", "377"): "Unnatural offences: BNS mein nahi.",
           ("IPC", "497"): "Adultery: Supreme Court ne 2018 mein khatam kiya; BNS mein nahi.",
           ("IPC", "124A"): "Sedition: BNS mein nahi; s.152 alag offence hai."}
MAP_SOURCES = [
    {"title": "IPC to BNS Conversion Table 2026 (lawsikho.com)", "url": "https://lawsikho.com/blog/ipc-to-bns-conversion"},
    {"title": "IPC vis-a-vis BNS (UP Police)", "url": "https://uppolice.gov.in/site/writereaddata/siteContent/Three%20New%20Major%20Acts/202402161435066605IPC%20vis-a-vis%20BNS.pdf"},
]

_ACT_WORDS = {
    "IPC": ("ipc", "indian penal code", "i.p.c", "आईपीसी", "भादंवि", "भा.दं.सं"),
    "CRPC": ("crpc", "cr.p.c", "code of criminal procedure", "सीआरपीसी", "दंड प्रक्रिया"),
    "IEA": ("evidence act", "indian evidence act", "iea", "साक्ष्य अधिनियम", "पुरावा कायदा"),
    "BNS": ("bns", "bharatiya nyaya sanhita", "भारतीय न्याय संहिता", "बीएनएस"),
    "BNSS": ("bnss", "bharatiya nagarik suraksha sanhita", "भारतीय नागरिक सुरक्षा संहिता"),
    "BSA": ("bsa", "bharatiya sakshya adhiniyam", "भारतीय साक्ष्य अधिनियम"),
}


def _row(r) -> dict[str, Any]:
    old_act, old, new_act, new, subject, sure = r
    return {"old_act": old_act, "old": old, "new_act": new_act, "new": new, "subject": subject, "sure": sure,
            "label": "pakka (published table se mila)" if sure else "andaaza (India Code se pakka karein)",
            "new_url": ACTS[new_act].get("url", "")}


def _norm_sec(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).upper()


def _base(sec: str) -> str:
    m = re.match(r"(\d+[A-Z]*)", _norm_sec(sec))
    return m.group(1) if m else ""


def map_old(act: str, sec: str) -> dict[str, Any] | None:
    act = act.upper()
    b = _norm_sec(sec)
    if (act, b) in REMOVED and act == "IPC" and b != "124A":
        return {"old_act": act, "old": b, "new_act": ACTS[act]["new"], "new": "", "subject": REMOVED[(act, b)], "sure": True,
                "label": "hata diya gaya", "new_url": ""}
    for r in MAPPING:
        if r[0] == act and _norm_sec(r[1]) == b:
            return _row(r)
    return None


def map_new(act: str, sec: str) -> list[dict[str, Any]]:
    act = act.upper()
    b = _base(sec)
    return [_row(r) for r in MAPPING if r[2] == act and _base(r[3]) == b]


def table(act: str = "") -> list[dict[str, Any]]:
    a = act.upper()
    return [_row(r) for r in MAPPING if not a or r[0] == a or r[2] == a]


_SEC = r"(\d{1,3}[A-Z]{0,2}(?:\s*\(\s*\d{1,2}\s*\))?)"
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _act_of(word: str) -> str:
    w = word.lower().strip(" .,")
    for k, words in _ACT_WORDS.items():
        if any(w == x or w.replace(".", "") == x.replace(".", "") for x in words):
            return k
    return ""


def find_refs(text: str) -> list[dict[str, str]]:
    """Old / new criminal-law section references in her words: 'IPC 420', '420 IPC', 'section 438 CrPC', 'धारा 302 आईपीसी',
    'Evidence Act 65B', 'BNS 103(1)'."""
    t = unicodedata.normalize("NFC", str(text or "")).translate(_DEV_DIGITS)
    out: list[dict[str, str]] = []
    acts_alt = "|".join(sorted({re.escape(w) for ws in _ACT_WORDS.values() for w in ws}, key=len, reverse=True))
    pat1 = re.compile(rf"(?<![\w.])({acts_alt})\s*(?:ki|ka|ke|की|का|के)?\s*(?:section|sec\.?|s\.|dhara|धारा|कलम)?\s*{_SEC}(?![\w])", re.I)
    pat2 = re.compile(rf"(?:section|sec\.?|s\.|u/s|dhara|धारा|कलम)?\s*{_SEC}\s*(?:of\s+(?:the\s+)?)?({acts_alt})(?![\w])", re.I)
    for m in pat1.finditer(t):
        a = _act_of(m.group(1))
        if a:
            out.append({"act": a, "sec": _norm_sec(m.group(2))})
    for m in pat2.finditer(t):
        a = _act_of(m.group(2))
        if a:
            out.append({"act": a, "sec": _norm_sec(m.group(1))})
    seen, res = set(), []
    for r in out:
        k = (r["act"], r["sec"])
        if k not in seen:
            seen.add(k)
            res.append(r)
    return res


def mapping_for(text: str) -> list[dict[str, Any]]:
    rows = []
    for r in find_refs(text):
        if r["act"] in ("IPC", "CRPC", "IEA"):
            m = map_old(r["act"], r["sec"])
            rows.append(m or {"old_act": r["act"], "old": r["sec"], "new_act": ACTS[r["act"]]["new"], "new": "", "sure": False,
                              "subject": "", "label": "table mein nahi: India Code mein dekhiye", "new_url": ACTS[ACTS[r["act"]]["new"]].get("url", "")})
        else:
            for m in map_new(r["act"], r["sec"]):
                rows.append(m)
    return rows


# ---------------------------------------------------------------- citations + grounding
_CASE_PATTERNS = [
    r"\(\s*\d{4}\s*\)\s*\d{1,3}\s*SCC\s*\d{1,4}",
    r"\d{4}\s*SCC\s*OnLine\s*[A-Za-z]{2,6}\s*\d{1,6}",
    r"AIR\s*\d{4}\s*[A-Z][A-Za-z]{1,10}\s*\d{1,5}",
    r"\d{4}\s*INSC\s*\d{1,5}",
    r"\[\s*\d{4}\s*\]\s*\d{1,3}\s*S\.?\s*C\.?\s*R\.?\s*\d{1,5}",
    r"\d{4}\s*:\s*[A-Z]{2,8}\s*:\s*\d{1,6}",                    # neutral citation e.g. 2024:BHC-AS:12345 (rough)
    r"MANU/[A-Z]{2,4}/\d{3,5}/\d{4}",
    r"\(\s*\d{4}\s*\)\s*\d{1,3}\s*SCR\s*\d{1,4}",
]
_CASE_RE = re.compile("|".join(f"(?:{p})" for p in _CASE_PATTERNS), re.I)
_SEC_RE = re.compile(r"(?:\b(?:sections?|secs?\.?|s\.|u/s|articles?|art\.|rules?|order|dhara)|धारा|कलम|अनुच्छेद)\s*"
                     r"(\d{1,3}[A-Z]{0,2}(?:\s*\(\s*[0-9a-z]{1,3}\s*\))*)", re.I)
_ACT_SEC_RE = re.compile(r"\b(?:BNS|BNSS|BSA|IPC|CrPC|Cr\.P\.C\.?)\s*(\d{1,3}[A-Z]{0,2}(?:\s*\(\s*[0-9a-z]{1,3}\s*\))*)", re.I)


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", str(t or "")).translate(_DEV_DIGITS)
    t = t.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", t).strip().lower()


def cites_in(text: str) -> list[str]:
    return list(dict.fromkeys(re.sub(r"\s+", " ", m.group(0)).strip() for m in _CASE_RE.finditer(text or "")))


def secs_in(text: str) -> list[tuple[str, str]]:
    """[(as written, base number)] for section / article / rule references."""
    out = []
    for rx in (_SEC_RE, _ACT_SEC_RE):
        for m in rx.finditer(text or ""):
            out.append((m.group(0).strip(), _base(m.group(1))))
    return out


def sec_in_source(base: str, src_norm: str) -> bool:
    """The section number appears in the source as a section: after a section word, or as a statute heading '103.' / '(103)'."""
    if not base:
        return False
    b = re.escape(base.lower())
    if re.search(rf"(?:section|sections|sec\.?|s\.|u/s|article|art\.|rule|order|dhara|धारा|कलम|अनुच्छेद|bns|bnss|bsa|ipc|crpc|cr\.p\.c\.?)\s*{b}(?![0-9a-z])", src_norm):
        return True
    return bool(re.search(rf"(?:^|\s){b}\.\s", src_norm))


def cite_in_source(cite: str, src_norm: str) -> bool:
    c = re.sub(r"[\s\[\]\(\)\.]", "", norm(cite))
    s = re.sub(r"[\s\[\]\(\)\.]", "", src_norm)
    return bool(c) and c in s


def quote_ok(quote: str, src_norm: str) -> bool:
    q = norm(quote).strip(" .\"'…")
    q = re.sub(r"\s*(?:\.\.\.|…)\s*", " ", q).strip()
    return len(q) >= 20 and q in src_norm


def ground(text: str, srcs: list[str], allowed: set[str] | None = None) -> tuple[str, list[dict[str, str]]]:
    """Replace every case citation / section reference in `text` that is not in any of the given (normalised) source texts and
    not in `allowed` (mapping-table sections shown with their own label) by NEED_CITE. Returns (clean text, removed list)."""
    allowed = {a.lower() for a in (allowed or set())}
    removed: list[dict[str, str]] = []
    out = text or ""
    for c in cites_in(out):
        if not any(cite_in_source(c, s) for s in srcs):
            removed.append({"what": c, "why": "yeh judgment / citation kisi padhe gaye source mein nahi"})
            out = out.replace(c, NEED_CITE)
    for written, base in secs_in(out):
        if not base or base.lower() in allowed:
            continue
        if not any(sec_in_source(base, s) for s in srcs):
            removed.append({"what": written, "why": "yeh section padhe gaye source mein nahi mila"})
            out = out.replace(written, NEED_CITE, 1)
    return out, removed


# ---------------------------------------------------------------- excerpts
_STOP = set("the and for with that this from what which when where kya hai hain kaise kab kis kaun kya aur bhi mein main par ka ki ke ko se "
            "section sec act law case court under about does have been will shall".split())


def terms(question: str, extra: list[str] | None = None) -> list[str]:
    q = norm(question)
    words = [w for w in re.findall(r"[a-zऀ-ॿ]{4,}|\d{1,4}[a-z]?", q) if w not in _STOP]
    return list(dict.fromkeys(words + [e.lower() for e in (extra or []) if e]))[:30]


def excerpts(text: str, tlist: list[str], k: int = 2, width: int = 600) -> list[str]:
    """Best passages of a source for these terms, copied VERBATIM (so the quote check passes on them)."""
    t = re.sub(r"[ \t]+", " ", str(text or "")).strip()
    if not t:
        return []
    parts = [p.strip() for p in re.split(r"\n+|(?<=[.;:])\s+(?=[A-Z(\"'0-9ऀ-ॿ])", t) if p.strip()]
    wins: list[str] = []
    cur = ""
    for p in parts:
        if len(cur) + len(p) + 1 > width and cur:
            wins.append(cur)
            cur = p[:width]
        else:
            cur = (cur + " " + p).strip() if cur else p[:width]
    if cur:
        wins.append(cur)
    if not tlist:
        return wins[:k]
    scored = []
    for i, w in enumerate(wins):
        n = norm(w)
        sc = sum(n.count(x) for x in tlist) + 2 * sum(1 for x in set(tlist) if x in n)
        scored.append((sc, -i, w))
    scored.sort(reverse=True)
    return [w for sc, _, w in scored[:k] if sc > 0]


def token_like(text: str) -> bool:
    t = str(text or "")
    return bool(re.search(r"\b(?:token|api[_ ]?key)\s*[:=]?\s*[A-Za-z0-9]{24,}", t, re.I) or re.search(r"\b[a-f0-9]{32,}\b", t))
