"""Pure rules of the Shiksha suite: question types and their code checks, Bloom levels, child-data rules (DPDP Act 2023
s.9) and the curriculum frameworks library (official facts only, each with its source; see frameworks.json)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

QTYPES = {
    "mcq": "Multiple choice (one correct of 4)",
    "assertion_reason": "Assertion - Reason (the 4 standard CBSE options)",
    "true_false": "True / False",
    "fill_blank": "Fill in the blank",
    "very_short": "Very short answer (1-2 marks)",
    "short": "Short answer (2-3 marks)",
    "long": "Long answer (4-6 marks)",
    "case_based": "Case / source based (a passage + sub-questions)",
    "numeric": "Numerical answer",
    "match": "Match the following",
    "code": "Programming (with test cases)",
}
OBJECTIVE = {"mcq", "assertion_reason", "true_false", "fill_blank", "numeric", "match"}
BLOOM = ["remember", "understand", "apply", "analyse", "evaluate", "create"]
DIFFICULTY = ["easy", "medium", "hard"]
BOARDS = {"CBSE": "Central Board of Secondary Education", "ICSE": "CISCE (ICSE class 10 / ISC class 12)",
          "MSBSHSE": "Maharashtra State Board", "STATE": "Other state board", "IB": "International Baccalaureate",
          "CAMBRIDGE": "Cambridge International", "UK_NC": "UK National Curriculum", "US_CCSS": "US Common Core",
          "UNIVERSITY": "College / university", "OTHER": "Other / own syllabus"}
# The four standard options CBSE uses for every Assertion - Reason question (sample papers).
AR_OPTIONS = ["Both Assertion (A) and Reason (R) are true and Reason (R) is the correct explanation of Assertion (A).",
              "Both Assertion (A) and Reason (R) are true, but Reason (R) is not the correct explanation of Assertion (A).",
              "Assertion (A) is true, but Reason (R) is false.",
              "Assertion (A) is false, but Reason (R) is true."]
DISCLAIMER = ("AI se bana draft: chhapne / baantne se pehle teacher ek baar padh kar approve karein. Chapter aur pattern "
              "board ke official source se; source ke bina kuch 'pakka' nahi likha jaata.")
NEVER = ["Board ka copyrighted syllabus / textbook text copy nahi (sirf chapter ke naam, codes, official links)",
         "Bina source ke 'CBSE pattern' / 'marks' pakka nahi bataya jaata - 'andaaza' likha jaata hai",
         "Bachche (18 se kam) ki jaankari sirf guardian ki consent ke saath; marks sirf guardian ko",
         "Paper / quiz / plan bahar (parents, class, Google Form) sirf teacher / owner ke tap se",
         "Exam ke asli paper ka leak ya 'leak hua paper' kabhi nahi"]


class RuleError(ValueError):
    pass


def _s(v: Any, n: int = 4000) -> str:
    return re.sub(r"[ \t]+", " ", str(v if v is not None else "")).strip()[:n]


def norm_text(t: str) -> str:
    return re.sub(r"[^a-z0-9ऀ-ॿ]+", " ", str(t or "").lower()).strip()


def fingerprint(text: str, options: list[str] | None = None) -> str:
    base = norm_text(text) + "|" + "|".join(sorted(norm_text(o) for o in (options or [])))
    return hashlib.sha256(base.encode()).hexdigest()[:32]


def similar(a: str, b: str) -> float:
    """Word-overlap similarity 0..1 (near-duplicate questions in the bank)."""
    wa, wb = set(norm_text(a).split()), set(norm_text(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa | wb), 1)


def _marks(v: Any) -> float:
    try:
        m = float(v)
    except (TypeError, ValueError):
        return 0.0
    return round(m * 2) / 2                 # whole or half marks only


def check_question(q: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Normalise one question and list what is wrong. A question with problems is never saved as approved; a 'fatal'
    problem (prefix '!') means it is not saved at all."""
    p: list[str] = []
    qtype = _s(q.get("qtype") or q.get("type"), 20).lower().replace("-", "_").replace(" ", "_")
    qtype = {"mcq_single": "mcq", "multiple_choice": "mcq", "ar": "assertion_reason", "assertion": "assertion_reason",
             "tf": "true_false", "fill": "fill_blank", "vsa": "very_short", "sa": "short", "la": "long", "case": "case_based",
             "source_based": "case_based", "numerical": "numeric", "programming": "code"}.get(qtype, qtype)
    if qtype not in QTYPES:
        p.append(f"! type '{qtype}' samajh nahi aaya")
        qtype = "short"
    text = _s(q.get("text") or q.get("question"), 6000)
    if len(text) < 8:
        p.append("! sawaal ka text bahut chhota / khaali")
    opts = [_s(o, 600) for o in (q.get("options") or []) if _s(o, 600)]
    answer = _s(q.get("answer"), 3000)
    if qtype == "mcq":
        opts = [re.sub(r"^\(?[a-dA-D1-4][\).:]\s+", "", o) for o in opts]
        if len(opts) != 4:
            p.append(f"! MCQ ke 4 options chahiye ({len(opts)} mile)")
        if len({norm_text(o) for o in opts}) != len(opts):
            p.append("! MCQ ke do options ek jaise")
        letter = re.fullmatch(r"\(?([a-dA-D])\)?", answer)
        if letter and len(opts) == 4:
            answer = opts["abcd".index(letter.group(1).lower())]
        if opts and norm_text(answer) not in {norm_text(o) for o in opts}:
            p.append("! MCQ ka sahi jawab options mein nahi")
        if any(re.search(r"\b(all|none) of the (above|these)\b", o, re.I) for o in opts):
            p.append("option 'all / none of the above' (achha MCQ isse bachta hai)")
    elif qtype == "assertion_reason":
        if not re.search(r"assertion", text, re.I) or not re.search(r"reason", text, re.I):
            p.append("! Assertion aur Reason dono likhe hone chahiye")
        opts = list(AR_OPTIONS)
        letter = re.fullmatch(r"\(?([a-dA-D])\)?", answer)
        if letter:
            answer = AR_OPTIONS["abcd".index(letter.group(1).lower())]
        if answer not in AR_OPTIONS:
            p.append("! Assertion-Reason ka jawab 4 standard options mein se hona chahiye")
    elif qtype == "true_false":
        a = norm_text(answer)
        if a in ("true", "t", "sahi", "satya"):
            answer = "True"
        elif a in ("false", "f", "galat", "asatya"):
            answer = "False"
        else:
            p.append("! True / False ka jawab True ya False hona chahiye")
        opts = ["True", "False"]
    elif qtype == "numeric":
        if not re.search(r"-?\d", answer):
            p.append("! numerical sawaal ka jawab number mein chahiye")
    elif qtype == "fill_blank":
        if "_" not in text and "…" not in text and "..." not in text:
            p.append("blank (____) sawaal mein dikhna chahiye")
    if not answer and qtype not in ("long", "case_based", "code"):
        p.append("! jawab khaali")
    marks = _marks(q.get("marks"))
    if marks <= 0:
        p.append("! marks chahiye")
        marks = 1.0
    if qtype in ("mcq", "assertion_reason", "true_false", "fill_blank") and marks > 2:
        p.append("objective sawaal par 2 se zyada marks (pattern se milaiye)")
    steps = [_s(x, 1200) for x in (q.get("steps") or []) if _s(x, 1200)]
    scheme = []
    for x in q.get("scheme") or []:
        if isinstance(x, dict) and _s(x.get("point"), 400):
            scheme.append({"point": _s(x.get("point"), 400), "marks": _marks(x.get("marks"))})
        elif isinstance(x, str) and x.strip():
            scheme.append({"point": _s(x, 400), "marks": 0.0})
    if scheme and all(s["marks"] > 0 for s in scheme) and abs(sum(s["marks"] for s in scheme) - marks) > 0.01:
        p.append(f"marking scheme ke marks ({sum(s['marks'] for s in scheme)}) sawaal ke marks ({marks}) se nahi milte")
    if qtype in ("short", "long", "case_based") and not scheme and not answer:
        p.append("! subjective sawaal ke liye model answer ya marking points chahiye")
    bloom = _s(q.get("bloom"), 12).lower().replace("analyze", "analyse")
    if bloom not in BLOOM:
        bloom = "understand"
    diff = _s(q.get("difficulty"), 8).lower()
    if diff not in DIFFICULTY:
        diff = "medium"
    clean = {"qtype": qtype, "text": text, "options": opts if qtype in ("mcq", "assertion_reason", "true_false", "match") else [],
             "answer": answer, "steps": steps[:20], "scheme": scheme[:20], "marks": marks, "bloom": bloom, "difficulty": diff,
             "competency": bool(q.get("competency")), "chapter": _s(q.get("chapter"), 200), "topic": _s(q.get("topic"), 200),
             "standards": [_s(x, 60) for x in (q.get("standards") or []) if _s(x, 60)][:8]}
    return clean, p


def fatal(problems: list[str]) -> bool:
    return any(x.startswith("!") for x in problems)


# ---------------------------------------------------------------- children (DPDP Act 2023 s.9)
def is_child(birth_year: int, adult_flag: bool = False, grade: str = "", today: date | None = None) -> bool:
    """A learner is a child (under 18) unless she marked them adult, or the birth year shows 18+. With no birth year a
    school grade (K-12) counts as a child: the safe side."""
    if adult_flag:
        return False
    if birth_year:
        y = (today or date.today()).year
        return y - int(birth_year) < 18 or (y - int(birth_year) == 18 and (today or date.today()).month < 4)
    g = str(grade or "").strip().upper()
    return not g.startswith(("UG", "PG", "PHD", "COLLEGE", "ADULT"))


CONSENT_METHODS = {"signed_form": "Guardian ne signed consent form diya", "in_person": "Guardian ne office mein khud haan kahi",
                   "digilocker": "Guardian ki pehchaan DigiLocker / virtual token se jaanchi",
                   "school_record": "School admission record (guardian ki pehchaan pehle se jaanchi hui)",
                   "email_confirmed": "Guardian ki registered email se likhit haan"}


# ---------------------------------------------------------------- frameworks (official facts only)
FRAMEWORKS_FILE = Path(__file__).with_name("frameworks.json")


@lru_cache
def frameworks() -> dict[str, Any]:
    try:
        return json.loads(FRAMEWORKS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _grade_key(grade: str) -> str:
    g = re.sub(r"(?i)^(class|grade|std\.?|standard)\s*", "", str(grade or "")).strip()
    return {"x": "10", "xii": "12", "ix": "9", "xi": "11", "viii": "8", "vii": "7", "vi": "6"}.get(g.lower(), g)


def _subject_match(want: str, have: list[str]) -> str:
    w = norm_text(want)
    for h in have:
        if norm_text(h) == w:
            return h
    for h in have:
        hn = norm_text(h)
        if w and (w in hn or hn in w):
            return h
    alias = {"maths": "mathematics", "math": "mathematics", "sst": "social science", "english": "english language and literature",
             "bio": "biology", "phy": "physics", "chem": "chemistry"}
    if alias.get(w) and alias[w] != w:
        return _subject_match(alias[w], have)
    return ""


def chapters(subject: str, grade: str) -> dict[str, Any]:
    """Current NCERT textbook chapters for a subject + class (CBSE follows NCERT), with the source page, or {} when the
    library does not have that book (then the teacher gives the chapter list)."""
    books = ((frameworks().get("ncert") or {}).get("textbooks") or {})
    subj = _subject_match(subject, list(books))
    if not subj:
        return {}
    book = (books.get(subj) or {}).get(_grade_key(grade)) or {}
    if not book.get("chapters"):
        return {}
    return {"subject": subj, "grade": _grade_key(grade), "book": book.get("book", ""), "chapters": list(book["chapters"]),
            "source": book.get("source", ""), "verified": not book.get("unverified")}


def pattern(board: str, grade: str, subject: str) -> dict[str, Any]:
    """The board's paper pattern (sections, marks, duration) for a class + subject from the official sample paper, or {}."""
    if str(board or "").upper() != "CBSE":
        return {}
    pats = (((frameworks().get("cbse") or {}).get("paper_patterns") or {}).get(_grade_key(grade)) or {})
    subj = _subject_match(subject, list(pats))
    if not subj:
        return {}
    p = dict(pats[subj])
    p["subject"] = subj
    p["grade"] = _grade_key(grade)
    p["session"] = (frameworks().get("cbse") or {}).get("session", "")
    p["verified"] = not p.get("unverified")
    return p


def blueprint_total(sections: list[dict]) -> float:
    return round(sum(float(s.get("count") or 0) * float(s.get("marks_each") or 0) for s in sections), 2)


def check_blueprint(sections: list[dict], max_marks: float | None = None) -> list[str]:
    p = []
    if not sections:
        return ["! blueprint mein koi section nahi"]
    for s in sections:
        if int(s.get("count") or 0) <= 0 or float(s.get("marks_each") or 0) <= 0:
            p.append(f"! section {s.get('name', '?')}: count aur marks_each dono chahiye")
        if str(s.get("qtype") or "") not in QTYPES:
            p.append(f"! section {s.get('name', '?')}: qtype '{s.get('qtype')}' galat")
    tot = blueprint_total(sections)
    if max_marks and abs(tot - float(max_marks)) > 0.01:
        p.append(f"! sections ka jod {tot} hai, paper {max_marks} ka hona chahiye")
    return p
