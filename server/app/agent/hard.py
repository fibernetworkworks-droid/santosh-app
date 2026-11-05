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
    # v0.437 SOCH KE JAWAB step 6: DEEP RESEARCH is hard work on its own (5 of 5 research asks scored 0 before)
    (re.compile(r"\bdeep\s*research|\bresearch\s+(?:karo|kar\s*do|kijiye|kariye|karke|kar\s*ke|report|on|about|into|"
                r"paper)|\b(?:market|industry|sector|competitor\w*|feasibility|landscape)\s+(?:study|research|analysis|"
                r"report|overview|size|sizing|map)|\bdetailed\s+(?:report|study|analysis)|\b(?:with|ke\s+saath)\s+"
                r"sources?|\bsources?\s+ke\s+saath|\bliterature\s+review|\bwhite\s*paper|\bstate\s+of\s+the\b|"
                r"\btrends?\s+in\b|\b(?:pe|par|on)\s+(?:ek\s+)?(?:poori|detailed|in.?depth)?\s*report\b|शोध|रिसर्च|"
                # v0.472 R1: the R0 card found 11 of 20 real research asks NOT seen ("Research the cotton...", "Research
                # India's...", "Compare ... date every price"). The VERB at the start of a sentence, "do / need research",
                # and the phrases only a sourced report asks for. "meri research ki file kholo" stays a plain ask.
                r"(?:^|[.!?\n]\s*)(?:please\s+|zara\s+)?research\s+(?!notes?\b|team\b|folder\b|files?\b|gate\b|lab\b|wing\b|dept\b|department\b|"
                r"cent(?:re|er)\b|institute\b|tab\b|sheet\b)\S|"
                r"\b(?:do|run|need|want|make|start)\s+(?:some\s+|a\s+|proper\s+)?research\b|"
                r"\bresearch\s+(?:chahiye|karna|karni)\b|\bofficial\s+(?:sources?|guidance|documents?)\b|"
                r"\bsources?\s+(?:and|aur)\s+dates?\b|\bdate\s+every\s+(?:price|point|figure|number)\b|"
                r"\bown\s+pricing\s+page\b|\bcite\s+the\b",
                re.I), 3, "research"),
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
# v0.556 a MAKE / DO request anywhere in her words ("50 chairs ka quotation bana do", "Make an invoice for...") with no
# reasoning signal is plain work: it skips the 'maybe' judge, which held the reply up to 2.5 s for nothing
_MAKE = re.compile(r"\bbana\s*(?:do|dijiye|dena|de)\b|\bbanao\b|\bbanaiye\b|\blikh\s*(?:do|dijiye|dena)\b|\blikho\b|"
                   r"\bbhej\s*(?:do|dijiye)\b|\bset\s*(?:karo|kar\s*do)\b|\blaga\s*do\b|\bmake\s+(?:a|an|the|me)\b|"
                   r"\bcreate\s+(?:a|an|the)\b|\bgenerate\s+(?:a|an|the)\b|\bdraft\s+(?:a|an|the)\b|\bprepare\s+(?:a|an|the)\b", re.I)


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
    if nums >= 2 and _QTY.search(t) and "calculation" not in why and (words >= 12 or nums >= 3):
        # a word problem: numbers + "how much / how many / when". v0.556: not a bare sum - "12 aur 15 ka total
        # kitna?" (6 words, 2 numbers) was sent to Opus with thinking at effort high; a real word problem has a story
        score += 2
        why.append("word problem")
    if _ACTION.match(t) and score < 3:
        score = 0
    hard = score >= 2
    # not sure: one weak signal, or a real question (8+ words) that is not an action - the fast judge decides
    maybe = (not hard) and not _ACTION.match(t) and (score == 1 or (words >= 8 and ("?" in t or nums >= 2)))
    if maybe and score == 0 and _MAKE.search(t):
        maybe = False                               # v0.556 plain make / do work never waits for the judge
    if hard:
        STATS["hard"] += 1
    return {"hard": hard, "maybe": maybe, "score": score, "why": why}


def is_hard(text: str) -> bool:
    return assess(text)["hard"]


def research_wanted(text: str) -> bool:
    """v0.437 does this ask want DEEP RESEARCH (many sources, a report)?"""
    return "research" in assess(text)["why"]


# ---------------------------------------------------------------- the fast judge for the "not sure" zone
JUDGE = ("Does answering this message well need careful multi-step reasoning - analysis, a calculation, a comparison "
         "and a decision, a plan or strategy, finding a root cause, a proof or puzzle, or a deep explanation? A plain "
         "fact, small talk, or a simple action (send, remind, open, play, order) is NOT. Reply with exactly one word: "
         "HARD or EASY.")
_CACHE: dict[str, bool] = {}


def _text_of(b) -> str:
    """A content block's text - SDK objects and plain dicts alike."""
    return str(b.get("text") or "") if isinstance(b, dict) else str(getattr(b, "text", "") or "")


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
        word = "".join(_text_of(b) for b in resp.content).strip().upper()
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


# ---------------------------------------------------------------- v0.433 SOCH KE JAWAB step 4: the reasoning recipe
# Rides in the system prompt ONLY on a hard turn (ordinary chat stays lean). The core is how a careful analyst works;
# the kind lines come from the labels assess() found. The reply rulebook (her language, answer first, length follows
# the question, light formatting) still governs HOW it is written - this governs how it is THOUGHT.
RECIPE_CORE = """SOCH KA TAREEKA (this is a hard question - think it through like a careful analyst, then answer like Hoola):
1. The real question: what decision or number does she actually need? If the words allow two readings, take the most
   likely one and say it in ONE line; ask a question only when a wrong guess would cost her (money, a filing, a send).
2. Facts first: use what she gave, this chat, her files and memory. A fact you need and do not have = a stated
   assumption in one short line ("maan ke chal rahe hain: ..."), never a made-up fact. Current rates, rules or prices
   that change = say they should be checked, or look them up with a tool.
3. Work it out in parts. EVERY number you work out comes from pylab (run it, quote the printed result) - never mental
   maths. Keep units and the Indian way of writing money (Rs / lakh / crore).
4. Check before you write: do the totals add up, are units and orders of magnitude sane, does the answer survive the
   strongest objection? Re-run the one figure the answer stands on. If a check fails, fix it before writing.
5. Write it: the answer or decision FIRST (one or two lines, with the key number); then the reasoning, compact - steps,
   or a small table when comparing; then the assumptions that matter, what would change the answer, and the next step
   for her. Say plainly what is uncertain. Your private thinking is not the reply - show the clean result."""

RECIPE_KIND = {
    "research": "DEEP RESEARCH: (a) split the topic into 4-6 sub-questions that together answer her real question; "
                "(b) gather - call research_run with the question and the sub-questions (Hoola's own engine: it reads "
                "the real pages in parallel and returns a dossier you write from; use its notes, never memory), and fall back to "
                "deploy_agents with one agent per sub-question plus web_sources / google_search / open_website if it is "
                "unavailable; prefer primary sources (government, regulator, "
                "company filings and reports, MoSPI for Indian official numbers) over blogs; (c) every fact and number "
                "carries its source as [n] with the date; the key numbers from two sources when you can, and say when "
                "they disagree; (d) derived figures (growth, share, CAGR, totals) from pylab; (e) write: a 5-7 line "
                "summary with the key numbers first, then findings by sub-question, what is still uncertain, and "
                "'Sources: [n] title - link - date'; a document with research_document (PDF / Word / workbook) when she asked for a file or the report is "
                "long, the chat then carries the summary + the file. Never cite a link you did not get from a tool in "
                "this work.",
    "calculation": "Calculation: write the formula in words, compute it in pylab, show the 2-4 inputs and the result; "
                   "for money over time give the monthly AND total figure.",
    "word problem": "Word problem: list the givens, solve step by step (pylab for the arithmetic), then check the "
                    "answer against the question's own numbers.",
    "maths": "Maths / logic: show each step so she can follow it; for a proof state the claim, the method, and close "
             "it cleanly; verify any numeric result in pylab.",
    "decision": "Decision: name 2-3 real options, judge them on HER criteria (cost, risk, time, effort) - a small table "
                "when it helps - then recommend ONE and say when the other would be better.",
    "plan": "Plan / strategy: goal and constraints first, then phases with what happens, who, by when and rough cost; "
            "name the 2-3 biggest risks and the first step for this week.",
    "diagnosis": "Root cause: list the likely causes ranked by how well the evidence fits, what she can check to "
                 "confirm each, and the fix for the most likely one first.",
    "analysis": "Analysis: what the data says (numbers from pylab), what it means, and what she should do about it - "
                "separate facts from your reading of them.",
    "rules": "Tax / legal / compliance: name the rule or section you rely on, apply it to her facts, say what is "
             "uncertain, and that a CA / lawyer should confirm before she files or signs.",
    "impact": "Impact / what-if: compare before vs after with the numbers, and name second-order effects.",
    "deep": "Explanation: build from the basics up, one idea per paragraph, with one concrete example from her world.",
}


def recipe(why: list[str] | None) -> str:
    """The reasoning recipe for one hard turn: the core + the lines for the kinds of reasoning found (max 3)."""
    kinds = []
    for w in sorted(why or [], key=lambda x: x != "research"):     # research leads when present
        k = {"how-long": "calculation", "numbers": "calculation", "judgement": "decision", "difference": "decision",
             "how-to-improve": "plan", "reasons": "diagnosis", "why": "diagnosis", "design": "plan", "fix": "diagnosis",
             "what-if": "impact", "explain": "deep"}.get(w, w)
        if k in RECIPE_KIND and k not in kinds:
            kinds.append(k)
    lines = [RECIPE_KIND[k] for k in kinds[:3]]
    return RECIPE_CORE + ("\n" + "\n".join("- " + x for x in lines) if lines else "")


# ---------------------------------------------------------------- v0.436 SOCH KE JAWAB step 5: the self-check
# A hard answer is HELD (not streamed) and checked before she sees it - like a careful analyst who re-reads the
# working before sending. Two checks: a free one in code (a calculation answered without running pylab), then ONE
# independent reviewer call that sees her question, the draft and the real tool evidence (pylab code + output). Any
# problem goes back to the same brain ONCE as a fix note; the corrected answer replaces the draft (she never sees the
# wrong one). A failing / slow reviewer never blocks the answer.
CHECK_SYSTEM = """You are the REVIEWER of a draft answer an AI assistant wrote for a hard question. Do not rewrite it.
Find only REAL problems that would make the answer wrong or misleading for her:
- a number that does not follow from the inputs (re-derive the key figures yourself; compare with the tool evidence),
- a figure stated as computed but not present in the tool evidence,
- a logical gap, a wrong formula, a wrong unit, a total that does not add up,
- a wrong rule / law / rate stated as fact, or an assumption hidden instead of stated,
- the draft does not actually answer the question she asked (or skips a part of it),
- for research: a fact or number with no source, or a source that the tool evidence does not back.
Style, tone, length and formatting are NOT problems. If the answer is right, say so.
Reply with ONLY a JSON object: {"ok": true} or {"ok": false, "problems": ["short, specific problem with the correct value if you know it", ...]} (max 4 problems)."""

_CALC_KINDS = {"calculation", "word problem", "maths", "numbers", "how-long", "impact"}
_DIGITS = re.compile(r"\d[\d,]*(?:\.\d+)?")


_URL = re.compile(r"https?://[^\s)\]>\"']+")


def _norm_url(u: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", u.rstrip(".,;:")).rstrip("/").lower()


def research_check(draft: str, evidence_text: str) -> list[str]:
    """v0.437 free check for a research answer: sources must exist, and every link must come from this work's tools."""
    links = [_norm_url(u) for u in _URL.findall(draft or "")]
    if not links:
        return ["The research answer cites no sources. Every fact and number needs its source link from the tool "
                "results (as [n], with a Sources list)."]
    ev = (evidence_text or "").lower()
    made_up = [u for u in dict.fromkeys(links) if u.split("?")[0] not in ev]
    if made_up:
        return [f"These links are not in any tool result of this work (do not cite a page you did not get from a "
                f"tool): {', '.join(made_up[:5])}. Remove them or open the real source and cite that."]
    return []


def code_check(question: str, draft: str, why: list[str] | None, tools_run: list[str],
               evidence_text: str = "") -> list[str]:
    """Free check: a calculation ask whose draft carries worked-out numbers while pylab never ran; a research answer
    with no sources or with links no tool returned."""
    if "research" in (why or []):
        found = research_check(draft, evidence_text)
        if found:
            return found
    if "pylab" in (tools_run or []):
        return []
    if not (set(why or []) & _CALC_KINDS):
        return []
    asked = set(_DIGITS.findall(question or ""))
    new = [n for n in _DIGITS.findall(draft or "") if n not in asked and len(n.replace(",", "")) >= 3]
    if len(new) >= 2:
        return [f"These figures were worked out without running pylab: {', '.join(new[:6])}. Compute them in pylab "
                "and use its printed results."]
    return []


def evidence(history: list[dict], limit: int = 9000, per: int = 2000) -> tuple[str, list[str]]:
    """This turn's tool calls and their results (pylab code + output first-class), newest last, capped."""
    start = 0
    for i in range(len(history) - 1, -1, -1):
        m = history[i]
        c = m.get("content")
        if m.get("role") == "user" and (isinstance(c, str) or not any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in (c or []))):
            txt = c if isinstance(c, str) else " ".join(str(b.get("text") or "") for b in c if isinstance(b, dict))
            if not txt.lstrip().startswith("[System"):
                start = i
                break
    parts: list[str] = []
    names: list[str] = []
    for m in history[start:]:
        for b in (m.get("content") if isinstance(m.get("content"), list) else []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                names.append(str(b.get("name")))
                inp = b.get("input") or {}
                shown = inp.get("code") if b.get("name") == "pylab" else inp
                parts.append(f"TOOL {b.get('name')} input: {str(shown)[:1500]}")
            elif b.get("type") == "tool_result":
                cont = b.get("content")
                cont = cont if isinstance(cont, str) else " ".join(str(x.get("text") or "") for x in (cont or [])
                                                                  if isinstance(x, dict))
                parts.append(f"RESULT: {cont[:per]}")
    text = "\n".join(parts)
    return (text[-limit:] if len(text) > limit else text), names


async def review(question: str, draft: str, ev: str, settings) -> list[str]:
    """One independent reviewer call. [] = no problem found (or the reviewer failed - never blocks the answer)."""
    import asyncio
    import json as _json
    try:
        from .santosh import get_client
        model = getattr(settings, "hard_check_model", "") or settings.anthropic_model
        user = (f"HER QUESTION:\n{question[:3000]}\n\nTOOL EVIDENCE FROM THIS TURN (pylab code + outputs, data):\n"
                f"{ev or '(no tools ran)'}\n\nDRAFT ANSWER:\n{draft[:8000]}")
        resp = await asyncio.wait_for(get_client().messages.create(
            model=model, max_tokens=900, system=CHECK_SYSTEM, messages=[{"role": "user", "content": user}]),
            timeout=float(getattr(settings, "hard_check_timeout_s", 60)))
        raw = "".join(_text_of(b) for b in resp.content).strip()
        m = re.search(r"\{.*\}", raw, re.S)
        v = _json.loads(m.group(0)) if m else {}
        STATS["reviewed"] = STATS.get("reviewed", 0) + 1
        if v.get("ok") is False:
            probs = [str(p)[:400] for p in (v.get("problems") or []) if str(p).strip()][:4]
            if probs:
                STATS["review_found"] = STATS.get("review_found", 0) + 1
            return probs
        return []
    except Exception:
        STATS["review_failed"] = STATS.get("review_failed", 0) + 1
        return []


def fix_note(problems: list[str]) -> str:
    return ("[System: JAANCH - your draft answer was checked before she saw it, and these problems were found:\n" +
            "\n".join(f"- {p}" for p in problems) +
            "\nFix them (run pylab again for any number), then write the COMPLETE corrected answer from the start, "
            "in her language - she has not seen the draft. Keep what was right. Do not mention this check.]")
