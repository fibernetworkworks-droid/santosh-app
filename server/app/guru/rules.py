"""Pure rules of the Guru Sahayak (personal tutor): the hint ladder, checking an answer in code, mastery and spaced
revision, picking the next practice question's difficulty, and spotting graded / exam work."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from ..shiksha import rules as SR

LEVELS = ("hint", "nudge", "step", "answer")     # the ladder: a hint, a bigger nudge, worked steps, the full solution
LEVEL_SAY = {"hint": "Ek ishaara", "nudge": "Thoda aur", "step": "Ek-ek step", "answer": "Poora hal"}
DISCLAIMER = ("Hoola ek AI tutor hai: samjhaata hai, khud sochne deta hai. Jawab kabhi galat ho sakta hai - jo 'code se "
              "jaancha' nahi likha, use teacher se pakka karein.")
NEVER = ["Graded homework / test / exam ka jawab likh kar dena (sirf ishaare aur samjhaana)",
         "Bachche (18 se kam) ke saath kaam guardian ki consent ke bina",
         "Roz ke tay samay se zyada padhai (bachchon ke liye)",
         "Bachche ki jaankari ya report guardian ke alawa kisi ko; report bhi sirf aapke tap se",
         "Jawab 'pakka' kehna jab code ya answer key ne jaancha nahi"]
EXAM_WORDS = re.compile(r"\b(exam|test|paper|quiz|assignment|homework|graded|submit|jama karna|abhi chal raha|online test|"
                        r"viva|olympiad|marks milenge|teacher check karegi)\b", re.I)


def looks_graded(text: str) -> bool:
    """Her words suggest graded work happening now (a test / assignment to submit): the tutor teaches with hints only."""
    t = str(text or "")
    return bool(EXAM_WORDS.search(t)) and bool(re.search(r"\b(abhi|now|kal|tomorrow|aaj|today|submit|jama|due|chal raha)\b", t, re.I))


def clean_ladder(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The model's ladder, checked: a hint, a nudge, 1-12 worked steps and a final answer, each non-empty."""
    p: list[str] = []
    hint = SR._s(raw.get("hint"), 600)
    nudge = SR._s(raw.get("nudge"), 900)
    steps = [SR._s(x, 900) for x in (raw.get("steps") or []) if SR._s(x, 900)][:12]
    answer = SR._s(raw.get("answer"), 1500)
    if not hint:
        p.append("hint khaali")
    if not nudge:
        p.append("nudge khaali")
    if not steps:
        p.append("steps khaali")
    if not answer:
        p.append("answer khaali")
    out = {"problem": SR._s(raw.get("problem"), 1500), "topic": SR._s(raw.get("topic"), 200), "hint": hint, "nudge": nudge,
           "steps": steps, "answer": answer, "check": SR._s(raw.get("check_question"), 600),
           "verify_code": str(raw.get("verify_code") or "")[:4000], "expected": SR._s(raw.get("expected"), 120)}
    return out, p


def level_text(ladder: dict[str, Any], level: str) -> str:
    if level == "step":
        return "\n".join(f"{i}. {s}" for i, s in enumerate(ladder["steps"], 1))
    return ladder.get(level, "")


# ---------------------------------------------------------------- checking an answer in code
_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:/\d+)?")


def _num(s: str) -> float | None:
    m = _NUM.search(str(s or "").replace(",", ""))
    if not m:
        return None
    v = m.group(0)
    try:
        if "/" in v:
            a, b = v.split("/")
            return float(a) / float(b)
        return float(v)
    except (ValueError, ZeroDivisionError):
        return None


def same_number(a: str, b: str, rel: float = 0.01) -> bool | None:
    x, y = _num(a), _num(b)
    if x is None or y is None:
        return None
    return abs(x - y) <= max(1e-9, rel * max(abs(x), abs(y)))


def check_objective(qtype: str, given: str, answer: str, options: list[str]) -> float | None:
    """1.0 / 0.0 for an objective question checked in code; None when code cannot judge it (subjective)."""
    g = SR.norm_text(given)
    if not g:
        return 0.0
    if qtype in ("mcq", "assertion_reason"):
        letter = re.fullmatch(r"\(?([a-d])\)?", g)
        if letter and len(options) >= 4:
            g = SR.norm_text(options["abcd".index(letter.group(1))])
        return 1.0 if g == SR.norm_text(answer) else 0.0
    if qtype == "true_false":
        g = {"t": "true", "sahi": "true", "satya": "true", "f": "false", "galat": "false", "asatya": "false"}.get(g, g)
        return 1.0 if g == SR.norm_text(answer) else 0.0
    if qtype == "numeric":
        r = same_number(given, answer)
        return None if r is None else (1.0 if r else 0.0)
    if qtype == "fill_blank":
        if same_number(given, answer):
            return 1.0
        return 1.0 if g == SR.norm_text(answer) else 0.0
    return None


# ---------------------------------------------------------------- mastery + spaced revision
def expected(score: float, difficulty: str) -> float:
    """The chance a learner at this mastery answers a question of this difficulty right (a simple logistic curve)."""
    import math
    d = {"easy": 0.25, "medium": 0.5, "hard": 0.75}.get(difficulty, 0.5)
    return 1 / (1 + math.exp(-8 * (score - d)))


def update(score: float, result: float, difficulty: str, hints: int = 0, k: float = 0.15) -> float:
    """Move mastery towards what happened: more when the result surprised; a hint-assisted right answer counts less."""
    r = max(0.0, min(1.0, result)) * (1.0 - min(0.6, 0.2 * hints))
    return round(max(0.0, min(1.0, score + k * (r - expected(score, difficulty)))), 4)


def next_review(interval_days: int, result: float, today: date) -> tuple[int, date]:
    if result >= 0.8:
        iv = min(60, max(1, interval_days) * 2)
    elif result >= 0.5:
        iv = max(1, interval_days)
    else:
        iv = 1
    return iv, today + timedelta(days=iv)


def target_difficulty(score: float) -> str:
    return "easy" if score < 0.4 else ("medium" if score < 0.75 else "hard")


# ---------------------------------------------------------------- 2.1 mastery with a confidence cap (after DeepTutor,
# Apache-2.0: learning/mastery.py) - recent answers count more, and one or two lucky answers cannot "master" a topic
RECENCY = (0.5, 0.7, 0.85, 0.95, 1.0)
CONFIDENCE_CAP = {1: 0.5, 2: 0.8}


def compute_mastery(results: list[float]) -> float:
    """0..1 from a topic's checked answers in order (each 0..1, partial credit allowed)."""
    if not results:
        return 0.0
    recent = results[-len(RECENCY):]
    w = RECENCY[-len(recent):]
    score = sum(wi * max(0.0, min(1.0, float(r))) for r, wi in zip(recent, w)) / sum(w)
    return round(min(score, CONFIDENCE_CAP.get(len(results), 1.0)), 4)


def credit(score: float, hints: int) -> float:
    """A hint-assisted answer earns less (20% per hint, at most 60% off)."""
    return max(0.0, min(1.0, score)) * (1.0 - min(0.6, 0.2 * max(0, hints)))


# ---------------------------------------------------------------- 2.1 SM-2 revision (after DeepTutor's services/practice/
# scheduler.py, Apache-2.0) in whole days, with an exam window that squeezes gaps to fit before her exam date
def rating(score: float, hints: int) -> str:
    if score < 0.5:
        return "again"
    if score < 0.8:
        return "hard"
    return "easy" if score >= 0.95 and hints == 0 else "good"


def sm2(interval: int, ease: float, streak: int, lapses: int, rate: str, cramming: bool = False) -> tuple[int, float, int, int]:
    if rate == "again":
        return (0 if cramming else 1), max(1.3, ease - 0.2), 0, lapses + 1
    if rate == "hard":
        return max(1, round(interval * 1.2)), max(1.3, ease - 0.15), 0, lapses
    iv = 3 if streak == 0 or interval <= 1 else round(interval * ease)
    if rate == "easy":
        iv, ease = round(iv * 1.3), min(3.0, ease + 0.15)
    return min(365, max(1, iv)), ease, streak + 1, lapses


def fit_exam(interval: int, today: date, exam: date | None) -> int:
    """Before an exam, a revision never lands after it: at most a third of the days left (so it comes round again)."""
    if not exam or exam <= today:
        return interval
    left = (exam - today).days
    return max(0 if left <= 3 else 1, min(interval, max(1, left // 3)))


def cramming(strategy: str, today: date, exam: date | None) -> bool:
    return strategy == "cramming" or bool(exam and today < exam <= today + timedelta(days=45))
