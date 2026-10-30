"""v0.272 SOCH KE JAWAB, step 1 - spotting HARD reasoning work (owner: "NOW LETS WORK ON HARD, COMPLEX, REASONING WORK -
FIRST CHECK WHAT ACTUALLY HOOLA HANDLES", then "GO ONE BY ONE").

What the check found: a hard question was handled like a quick chat. The only switch into a deeper mode was
goal.looks_big, which counts LISTS, sequence words and action verbs - a multi-step JOB. A hard QUESTION is short and
has none of those: "Prove root 2 is irrational", "3 saal ka financial model banao, profitable kab hoga", "GST
composition vs regular, kya better hai" - 6 of 6 such asks came out "not big", so no thinking, 2,000 tokens.

This module answers a different question: does this ask need THINKING (analysis, a comparison and a decision, a
calculation, maths / logic, a plan or strategy, a root cause, a deep explanation)? Word rules only - never a model
call, so it adds no delay. Each kind of reasoning adds points; a plain action ("mail bhejo", "alarm lagao") or a
plain fact needs none. score >= 2 = hard. Measured on app/quality/hard_asks.py (the test pins it).
"""
from __future__ import annotations

import re

STATS = {"checked": 0, "hard": 0}

# (pattern, points, label) - each label counts once
_SIGNALS: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"\banaly[sz]\w*|\bvishleshan|विश्लेषण|\bevaluat\w*|\bassess\w*|\bcritique|\binterpret\w*|"
                r"\bjaanch\s*ke\s*batao|\bdeep\s*dive", re.I), 2, "analysis"),
    (re.compile(r"\broot\s*cause|\bdiagnos\w*|\btroubleshoot\w*|figure\s+out\s+why|\bkya\s+galat|\bgalti\s+kahan|"
                r"\bwhat(?:'s|\s+is|\s+went)\s+wrong|\bkahan\s+(?:gadbad|galti)", re.I), 2, "diagnosis"),
    (re.compile(r"\bkis\s+wajah|\bwajah\s+(?:kya|batao)|\bwhy\s+(?:did|does|is|are|do|has|have|my|the|would)|\bkyu[n]?\s|"
                r"\bkyon\s|\bkyun\b|क्यों|\bkaaran\b|\bhow\s+(?:do|can|should)\s+(?:we|i)\b", re.I), 1, "why"),
    (re.compile(r"\bcompar\w*|\bvs\.?\s|\bversus\b|\btulna|तुलना|\bpros\s+and\s+cons|\bfaayd\w*\s+(?:aur\s+)?nuksan|"
                r"\btrade.?offs?\b|\bbetter\b|\bbehtar\b|\bbest\s+(?:option|way|choice|plan)|\bkaun\s*sa\s+"
                r"(?:behtar|accha|sahi|best)|\bshould\s+(?:i|we)\b|\bkarna\s+chahiye|\blena\s+chahiye|\brecommend\w*|"
                r"\bkya\s+(?:karu|karun|karein|kare)\b|\bdecide\b|\bdecision\b|\bkya\s+mujhe\b.{0,80}\bchahiye|"
                r"\bchahiye\s+ya\b|\bbest\s+time\b|\bsahi\s+(?:rahega|hoga)\b.{0,20}\bya\b", re.I), 2, "decision"),
    (re.compile(r"\bstrateg\w*|\broadmap\b|\bgo.?to.?market\b|\bbusiness\s+plan\b|\bforecast\w*|\bprojection\w*|"
                r"\bgrowth\s+plan|\bexpansion\s+plan|\branneeti|रणनीति|\bplan\s+(?:for|banao|bana\s+do)\b.{0,40}"
                r"(?:month|year|saal|mahine|quarter|week)|\b\d+\s*(?:-|\s)?(?:month|year|saal|mahine)\w*\s+(?:ka|ki|ke)?\s*"
                r"(?:plan|strategy|model|forecast|roadmap)|\b(?:concrete|detailed|action|step.?wise)\s+plan\b", re.I), 2, "plan"),
    (re.compile(r"\bcalculat\w*|\bcompute\b|\bkitn[aie]\s+(?:banega|banegi|hoga|hogi|lagega|lagegi|bachega|bachegi|"
                r"milega|milegi|padega|padegi)|\broi\b|\birr\b|\bnpv\b|\bemi\b|\bbreak.?even|\bmargin\b|\bcompound|"
                r"\bcagr\b|\bvaluation|\bcash\s*flow|\bfinancial\s+model|\bunit\s+economics|\bp&l\b|\bprofit\w*\b.{0,30}"
                r"(?:kab|when|kitna|how\s+much)|\binterest\b.{0,20}(?:kitna|how\s+much|rate)|\bpayback", re.I), 2,
     "calculation"),
    (re.compile(r"\bprove\b|\bproof\b|\bderive\b|\bsolve\b|\bequation|\bprobabilit\w*|\bpuzzle|\briddle|\blogic\w*|"
                r"\bintegral|\bderivative|\btheorem|\balgebra|\bgeometry|\bkm\s*/\s*h\b|\bspeed\b.{0,40}\bdistance|"
                r"\d+\s*[x×*/^]\s*\d+|\bpaheli|\bsawaal\s+hal", re.I), 2, "maths"),
    (re.compile(r"\bstep\s*by\s*step|\bdetail\s+(?:mein|me|se)\s+(?:samjha|bata)\w*|\bexplain\s+(?:how|why|in\s+detail)|"
                r"\bsamjhao\s+(?:kaise|kyun|ki)|\bin\s+depth|\bin.?depth\b|\bthorough\w*|\bgehrai\s+se|\bvistaar\s+se|"
                r"\bfirst\s+principles|\bthink\s+(?:it\s+)?through|\bsoch\s+(?:ke|kar|samajh)|\breasoning\b|"
                r"\bwith\s+reasons?\b|\bkaaran\s+ke\s+saath|\btark\b", re.I), 2, "deep"),
    (re.compile(r"(?:\bgst\b|\btax\b|\bitr\b|\btds\b|\blegal\b|\bcontract\b|\bclause\b|\bcompliance\b|\bkanoon\b)"
                r".{0,60}(?:\bwhich\b|\bkaun\b|\bbetter\b|\bshould\b|\bkya\s+karna|\bimplication|\bliabilit|\beligib|"
                r"\brisk\b|\bnuksan|\bfaayda|\bya\s+nahi|\bapplicable|\blagega|\bpadega|\bkis\s+section|\bwhich\s+section|"
                r"\bkitna\b)", re.I), 2, "rules"),
    (re.compile(r"\bdebug\w*|\b(?:error|issue|problem|bug)\b.{0,25}(?:kyu|why)|\boptimi[sz]\w*|\bminimi[sz]\w*|"
                r"\bmaximi[sz]\w*|\bbottleneck", re.I), 2, "fix"),
]
# v0.272 general SHAPES of reasoning (not topics): a what-if, an impact, a difference, a design to justify, the
# reasons behind something, how to reduce / raise a number, a yes-or-no judgement on a plan, "how many years until"
_SHAPES: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"\bagar\b.{3,90}\b(?:to|toh)\b|\bif\s+(?:we|i|our|my|the|a)\b.{3,90}(?:\bthen\b|\bwhat\b|\bhow\b|\bis\b|,)|"
                r"\bwhat\s+(?:if|happens\s+if|would\s+happen)|\bsuppose\b|\bmaan\s+lo|अगर\b.{3,60}तो", re.I), 1, "what-if"),
    (re.compile(r"\bimpact\b|\beffects?\s+of\b|\bsecond.?order|\bconsequence|\b(?:kya|kitna)\s+asar\b|\basar\s+padega|"
                r"\bhow\s+(?:will|would|does)\b.{0,40}\baffect|\bअसर", re.I), 2, "impact"),
    (re.compile(r"\bdifference\s+between|\bfarak\s+kya|\bfarq\s+kya|\bantar\s+kya|\bअंतर|\bwhich\s+one\b|"
                r"\bkis\s*(?:e|se|ko)\s+(?:kitna|chun|lun|loon|du|dun)|\bkiss?e\s+kitna", re.I), 2, "difference"),
    (re.compile(r"\bjustify\b|\bdesign\s+(?:a|an|the|my|our)\b.{0,40}(?:structure|system|model|pricing|plan|process|"
                r"architecture|tier)|\bdecision\s+memo|\bframework\s+(?:for|to)\b|\bstructure\s+(?:for|of)\b", re.I), 2,
     "design"),
    (re.compile(r"\bpossible\s+(?:reasons?|causes?)|\breasons?\s+(?:nikalo|batao|kya|for|behind)|\bkaaran\s+(?:kya|batao)|"
                r"\bkyun\s+gir|\bgir\s+rah[aie]|\bghat\s+rah[aie]|\bbadh\s+rah[aie]\b.{0,30}(?:kyun|why|\?)|"
                r"\bkam\s+ho\s+rah[aie]|घट\s+रह", re.I), 2, "reasons"),
    (re.compile(r"\b(?:kaise|how\s+(?:can|do|should)\s+(?:i|we))\b.{0,40}\b(?:kam|badh|reduce|increase|improve|grow|cut|"
                r"save|bacha)\w*|\btaaki\b.{0,30}\b(?:kam|zyada|badh|bach)|\bso\s+that\b.{0,30}\b(?:cost|time|"
                r"profit)|\bkaise\s+(?:plan|manage|split|baant)\w*|कैसे\s+(?:प्लान|कम|बढ़)", re.I), 2, "how-to-improve"),
    (re.compile(r"\b(?:rahega|chalega|hoga|hogi|milega|bachega|sahi\s+hai)\s+ya\s+nahi|\bya\s+nahi\s*\?|"
                r"\bis\s+(?:it|this|the\s+business|our)\b.{0,30}\b(?:healthy|worth|viable|profitable|good\s+idea)|"
                r"\bworth\s+it\b|\bviable\b|\bprofitable\b", re.I), 2, "judgement"),
    (re.compile(r"\bkitne\s+(?:saal|mahine|din|years?|months?)\s+(?:mein|me|lagenge)|\bhow\s+(?:many|long)\s+(?:years?|"
                r"months?)\b|\bhow\s+long\s+(?:will|until)|\bkitna\s+(?:penalty|nuksan|faayda|tax|bachat)", re.I), 2,
     "how-long"),
    (re.compile(r"विस्तार|योजना|बजट|रणनीति|समझाइए|विश्लेषण|\bbudget\b.{0,30}\b(?:plan|kaise|how)|\bsamjhao\b|"
                r"\bexplain\b", re.I), 1, "explain"),
]
# a plain action or a plain fact: no thinking needed when nothing above fired strongly
_ACTION = re.compile(r"^\s*(?:hoola[,\s]+)?(?:send|bhej\w*|remind|yaad\s+dila\w*|alarm|timer|book|order|mangwa\w*|"
                     r"kholo|open|play|chala\w*|call|share|delete|hata\w*|save|daal\w*|add)\b", re.I)
_QTY = re.compile(r"\bkitn[aeiy]\b|\bkitni\b|\bhow\s+(?:much|many|long)\b|\bkab\s+(?:tak|hoga|milenge|milega)\b|"
                  r"\bwhen\s+will\b|\bam\s+i\s+(?:actually\s+)?(?:earning|losing|saving)|कितन", re.I)
_NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:\s*(?:%|lakh|crore|k\b|cr\b|rs|₹))?", re.I)


def assess(text: str) -> dict:
    """{'hard': bool, 'score': int, 'why': [labels]} for one ask of hers."""
    t = str(text or "").strip()
    STATS["checked"] += 1
    if not t or t.startswith(("[", "(")):
        return {"hard": False, "maybe": False, "score": 0, "why": []}
    t = t[:3000]
    why: list[str] = []
    score = 0
    for pat, pts, label in _SIGNALS + _SHAPES:
        if pat.search(t):
            why.append(label)
            score += pts
    words = len(t.split())
    if len(_NUM.findall(t)) >= 3 and any(w in why for w in ("calculation", "maths", "decision", "plan")):
        score += 1
        why.append("numbers")
    if t.count("?") >= 2 and why:
        score += 1
        why.append("many questions")
    if words >= 45 and why:
        score += 1
        why.append("long ask")
    nums = len(_NUM.findall(t))
    if nums >= 2 and _QTY.search(t) and "calculation" not in why:
        score += 2                                  # a word problem: numbers + "how much / how many / when"
        why.append("word problem")
    if _ACTION.match(t) and score < 3:
        score = 0
    hard = score >= 2
    # not sure: one weak signal, or a real question (8+ words) that is not an action - the fast judge decides
    maybe = (not hard) and not _ACTION.match(t) and (score == 1 or (words >= 8 and ("?" in t or nums >= 2)))
    if hard:
        STATS["hard"] += 1
    return {"hard": hard, "maybe": maybe, "score": score, "why": why}


def is_hard(text: str) -> bool:
    return assess(text)["hard"]


# ---------------------------------------------------------------- the fast judge for the "not sure" zone
JUDGE = ("Does answering this message well need careful multi-step reasoning - analysis, a calculation, a comparison "
         "and a decision, a plan or strategy, finding a root cause, a proof or puzzle, or a deep explanation? A plain "
         "fact, small talk, or a simple action (send, remind, open, play, order) is NOT. Reply with exactly one word: "
         "HARD or EASY.")
_CACHE: dict[str, bool] = {}


async def judge(text: str, settings) -> bool | None:
    """One tiny model call (Haiku, 1 output token, hard time limit) for the 'maybe' zone. None = could not decide
    (no key, timeout, error) - the caller then stays on the fast path, exactly as before."""
    import asyncio
    key = str(text or "")[:1500]
    if key in _CACHE:
        return _CACHE[key]
    if not getattr(settings, "hard_judge", True):
        return None
    try:
        from .santosh import get_client
        resp = await asyncio.wait_for(get_client().messages.create(
            model=getattr(settings, "hard_judge_model", "") or "claude-haiku-5-5", max_tokens=3, system=JUDGE,
            messages=[{"role": "user", "content": key}]), timeout=float(getattr(settings, "hard_judge_timeout_s", 2.5)))
        word = "".join(getattr(b, "text", "") for b in resp.content).strip().upper()
        STATS["judged"] = STATS.get("judged", 0) + 1
        out = word.startswith("HARD")
        _CACHE[key] = out
        if len(_CACHE) > 500:
            _CACHE.pop(next(iter(_CACHE)))
        return out
    except Exception:
        STATS["judge_failed"] = STATS.get("judge_failed", 0) + 1
        return None


async def decide(text: str, settings) -> dict:
    """The verdict for one ask: rules first (free), the judge only for 'maybe'. {'hard', 'by', 'why'}"""
    a = assess(text)
    if a["hard"]:
        return {"hard": True, "by": "rules", "why": a["why"]}
    if a.get("maybe"):
        j = await judge(text, settings)
        if j is not None:
            if j:
                STATS["hard"] += 1
            return {"hard": bool(j), "by": "judge", "why": a["why"]}
    return {"hard": False, "by": "rules", "why": a["why"]}
