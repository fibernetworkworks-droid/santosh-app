"""v0.223 DRAFT JAANCH: the last look at a reply - does it answer what she asked, and is every hard fact in it
backed by something real?

The rulebook (v0.221) tells the model to check its own draft once before sending. This is the part that does not
depend on the model remembering to: two checks, both built so they add NO visible delay.

1. A claim with nothing behind it (free, in code, inside the turn): the reply says the work is done - "bhej diya",
   "book ho gaya", "save kar diya" - while every tool that finished ok this turn was a read, so nothing was really
   sent, saved or booked. The model is told once to actually do it or say plainly that it is not done; if it claims
   again, the honest line is added after the words she already read. The same words about HER, in the future or as
   an offer are never a claim. pakka's own self-check owns the case where tools DID run, and goal mode (v0.186) owns
   its own truth, so this check stays out of both.

2. The draft check (one small cheap-brain call, AFTER the reply is already on her screen): it runs only when code
   sees something worth checking - a hard fact (an amount, a date, a time, an id) that appears nowhere in her
   message, the recent chat or this turn's tool results, or a question of hers that had two or more parts. The code
   only DECIDES whether to look; the model is the only thing that may speak, so an amount Hoola worked out from
   real numbers, or a public rule, never turns into a wrong warning. When it finds something real, one short note
   follows the reply - it never rewrites the words she has already read.

Capped per chat per hour so it can never chatter, owner turns only, and silent when she tapped Stop or the turn
already carries a "(Saaf baat:" / "(Dhyaan:" note.
"""
from __future__ import annotations

import json
import logging
import re
import time

log = logging.getLogger("santosh.draftcheck")

STATS = {"fake_done": 0, "fake_done_said": 0, "gated": 0, "checked": 0, "missed": 0, "unsupported": 0,
         "skipped_cap": 0, "quiet": 0}

NOTE_MARKS = ("(Saaf baat:", "(Dhyaan:", "(Ek baat reh gayi:")

# ---------------------------------------------------------------- 1. a claim with nothing behind it

# only phrases that claim a REAL action already happened; a bare "ho gaya" is too loose to judge
_DONE = re.compile(
    r"(bhej\s*(?:diya|di|diye|dii)|send\s*kar\s*diya|sent\b|mail\s*kar\s*diya|whatsapp\s*kar\s*diya"
    r"|book\s*(?:ho\s*gaya|kar\s*diya|kar\s*di)|save\s*kar\s*d|update\s*kar\s*d|add\s*kar\s*d|delete\s*kar\s*d"
    r"|order\s*kar\s*d|pay\s*kar\s*d|cancel\s*kar\s*d|set\s*kar\s*d"
    r"|reminder\s*(?:lag\s*gaya|laga\s*diya)|upload\s*kar\s*d|download\s*kar\s*l|kaam\s*ho\s*gaya"
    r"|likh\s*kar\s*bhej|draft\s*bhej)", re.I)
# the same words are fine about HER, in the future, or as a condition
_NOT_A_CLAIM = re.compile(r"(aap\s*ne|aapne|aap\s+khud|jayega|jaayega|jaega|jaye|hoga|hogi|karunga|karungi|karoonga|doon"
                          r"|dunga|dungi|denge|agar\b|jaise\s*hi|haan\s*kar|tap\s*kar|card\s*par|baad\s*mein"
                          r"|nahi\s*bhej|nahi\s*hua|mat\b|chahiye\s*to|kahiye\s*to|bolo\s*to|bataiye\s*to)", re.I)


def claims_done(text: str) -> str:
    """The claimed action when the reply says something was really done, else ''."""
    for m in _DONE.finditer(text or ""):
        a, b = max(0, m.start() - 45), min(len(text), m.end() + 30)
        if _NOT_A_CLAIM.search(text[a:b]):
            continue
        return m.group(1)[:60]
    return ""


# reads and bookkeeping: running one of these is not "doing" anything. Every Sahayak's own read tool follows the
# "<name>_dekho" convention, so the whole family is covered by the rule instead of a list.
READS = {"google_search", "web_sources", "open_website", "parallel_search", "kaam_status", "session_log",
         "file_read", "doc_preview", "gyaan_khojo", "yaad_khojo", "india_info", "ai_kharcha", "phone_health",
         "get_weather", "maps_search", "tool_search", "kaam_plan", "youtube_search", "api_find", "api_docs",
         "indiamart_khoj", "indiamart_detail"}


def _is_read(name: str) -> bool:
    from . import pakka
    n = str(name or "")
    return n in READS or n in pakka.SKIP or n.endswith("_dekho")


def nothing_ran(calls: list[dict] | None) -> bool:
    """True when this turn did not actually DO anything: every tool that finished ok was a read."""
    for c in calls or []:
        if c.get("ok") and not _is_read(c.get("tool")):
            return False
    return True


NUDGE = ("[System check, not the user] Your message says the work is already done, but nothing that could do it "
         "ran this turn - only reads, so nothing was actually sent, saved, booked or ordered. Either do it NOW "
         "with the right tool (every card, "
         "approval and OTP rule as usual), or say plainly in one line that it is NOT done yet and what the next "
         "step is. Never say done for something that did not happen.")
SAID = "(Saaf baat: yeh kaam abhi hua nahi hai - ab bhi karna baaki hai.)"


def fake_done(state: dict, text: str) -> str:
    """Inside the turn, free: returns a nudge the first time the reply claims work that never ran. The second time
    it sets state['correct'] (added after the words she already read) and returns ''."""
    if not claims_done(text) or not nothing_ran(state.get("calls")):
        return ""
    seen = state.get("fake_done", 0) + 1
    state["fake_done"] = seen
    if seen == 1:
        STATS["fake_done"] += 1
        return NUDGE
    if seen == 2 and not state.get("correct"):
        STATS["fake_done_said"] += 1
        state["correct"] = SAID
    return ""


# ---------------------------------------------------------------- 2. is it worth one small check?

_MONTH = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?"
          r"|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?")
_FACTS = [
    re.compile(r"(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d+)?)", re.I),                       # Rs 4,500
    re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:rs\b|rupees?|rupaye|rupaiye|₹)", re.I),      # 4500 rupaye
    re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|crore|karod)", re.I),               # 2.5 lakh
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b"),                          # 15/11 , 15-11-2026
    re.compile(r"\b(\d{1,2})\s*(?:" + _MONTH + r")\b", re.I),                         # 15 Nov
    re.compile(r"(?:" + _MONTH + r")\s*(\d{1,2})\b", re.I),                           # Nov 15
    re.compile(r"\b(\d{1,2})\s*(?:tareekh|tarikh|taarikh)", re.I),                    # 20 tareekh
    re.compile(r"\b(\d{1,2}(?::\d{2})?)\s*(?:am|pm|baje|bajey)\b", re.I),             # 4 baje , 4:30 pm
    re.compile(r"\b(\d{5,})\b"),                                                      # an order / invoice / pin
]


def _digits(s: str) -> str:
    return re.sub(r"[^\d]", "", s or "")


def hard_facts(text: str) -> list[str]:
    """Every concrete figure in the reply: amounts, dates, times, long numbers. Percentages and small counts are
    left out on purpose - they are almost always worked out or general."""
    out, seen = [], set()
    for rx in _FACTS:
        for m in rx.finditer(text or ""):
            raw = (m.group(1) or "").strip()
            d = _digits(raw)
            if not d or d in seen:
                continue
            seen.add(d)
            out.append(raw)
    return out[:12]


def sources_text(request: str, calls: list[dict] | None, chat_tail: str = "") -> str:
    """Everything real this turn had to go on: her words, the recent chat, and what the tools really returned."""
    parts = [str(request or ""), str(chat_tail or "")]
    for c in calls or []:
        parts.append(str(c.get("args") or ""))
        parts.append(str(c.get("result") or ""))
        parts.append(str(c.get("error") or ""))
    return "\n".join(parts)


def loose_facts(text: str, sources: str) -> list[str]:
    """Figures in the reply whose digits appear nowhere in the sources. A gate only - a figure worked out from real
    numbers lands here too, which is exactly why only the model may speak."""
    have = _digits(sources)
    out = []
    for f in hard_facts(text):
        d = _digits(f)
        if d and d not in have:
            out.append(f)
    return out[:6]


_MULTI = re.compile(r"(?m)^\s*(?:2[.)]|b[.)]|दो[.)])\s")


def many_parts(ask: str) -> bool:
    """Her question had two or more parts, so a short reply may have answered only the first."""
    a = str(ask or "")
    return a.count("?") >= 2 or bool(_MULTI.search(a))


def worth_checking(ask: str, reply: str, calls: list[dict] | None, chat_tail: str = "") -> dict | None:
    """Free, in code: the one decision about spending a small model call. None = say nothing, check nothing."""
    r = str(reply or "").strip()
    # no length floor: "Total Rs 7,250 hua hai." is short AND exactly the kind of line worth one look. The fact /
    # parts gate below is what keeps a plain "Theek." from ever costing a model call.
    if len(r) < 8 or any(m in r for m in NOTE_MARKS):
        return None
    src = sources_text(ask, calls, chat_tail)
    loose = loose_facts(r, src)
    parts = many_parts(ask)
    if not loose and not parts:
        return None
    STATS["gated"] += 1
    return {"loose": loose, "parts": parts, "src": src}


# ---------------------------------------------------------------- the small check, after the words are out

CHECK_SYSTEM = """You take one last look at an assistant's reply that has ALREADY been sent to the user. You get the
user's request, what the tools really returned this turn, and the reply.
Answer ONLY with JSON: {"ok": true|false, "missed": "<the part of the request the reply does not answer, in the
user's own language, short>", "unsupported": ["<a figure or name in the reply that nothing backs>"]}
- ok=true (and both fields empty) unless you are SURE something is wrong. Silence is the right answer most of the time.
- unsupported = only a figure, date or name that looks like THIS user's own data (an amount she is owed, her order
  or invoice number, a date agreed with her, a person's name) and that is NOT in the request or the tool results.
  A figure the assistant worked out from the given numbers (a sum, a total, a difference) is fine. A public rule, a
  standard tax rate, a statutory due date, a well-known fact or a plain example is NEVER unsupported.
- missed = only a clearly separate question of hers that the reply does not answer at all. A short answer that
  covers everything is fine. An offer to do more is fine.
- Never comment on tone, length, formatting or politeness. Never suggest skipping an approval."""


def _mask(s: str, n: int) -> str:
    from .pakka import mask
    return mask(str(s or ""), n)


async def ask_model(ask: str, reply: str, calls: list[dict] | None, settings) -> dict | None:
    import asyncio

    from . import pakka
    lines = []
    for c in (calls or [])[-12:]:
        lines.append(f"- {c.get('tool')}: {'ok' if c.get('ok') else 'ERROR'}"
                     + (f" -> {_mask(c.get('result', ''), 200)}" if c.get("ok") and c.get("result") else ""))
    msg = (f"User request:\n{_mask(ask, 900)}\n\nTool results this turn:\n"
           + ("\n".join(lines) or "- (none: the assistant only talked)")
           + f"\n\nThe reply that was sent:\n{_mask(reply, 1400)}")
    STATS["checked"] += 1
    try:
        raw = await asyncio.wait_for(pakka._ask(CHECK_SYSTEM, msg, settings), 25)
    except Exception as e:
        log.info("draft check skipped: %s", e)
        return None
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        v = json.loads(m.group(0))
    except Exception:
        return None
    uns = v.get("unsupported") or []
    if isinstance(uns, str):
        uns = [uns]
    return {"ok": v.get("ok", True) is not False,
            "missed": str(v.get("missed") or "")[:200],
            "unsupported": [str(x)[:60] for x in uns if str(x or "").strip()][:3]}


def _backs(item: str, loose_digits: str, sources_low: str) -> bool:
    """This flagged item is one the code also found unbacked: a figure whose digits were loose, or a name that is
    really nowhere in the sources."""
    d = _digits(item)
    if d:
        return d in loose_digits
    t = str(item or "").strip().lower()
    return bool(t) and t not in sources_low


def note_of(v: dict, loose: list[str], sources: str = "") -> str:
    """One short honest line, or '' when there is nothing to say. Only what the CODE also found unbacked may be
    named - a figure whose digits code saw as loose, or a name that really is nowhere in the sources - so the note
    can never invent a worry of its own."""
    seen, low = _digits(" ".join(loose)), str(sources or "").lower()
    uns = [u for u in (v.get("unsupported") or []) if _backs(u, seen, low)]
    if uns:
        STATS["unsupported"] += 1
        return ("(Dhyaan: " + " aur ".join(uns[:2])
                + " - yeh mujhe kisi pakke source se nahi mila; ek baar khud dekh lijiye.)")
    if v.get("missed"):
        STATS["missed"] += 1
        return "(Ek baat reh gayi: " + v["missed"] + " - bataun?)"
    return ""


# ---------------------------------------------------------------- the per-chat cap

_SPOKE: dict[str, list[float]] = {}


def may_speak(conversation_id: str, settings) -> bool:
    cap = int(getattr(settings, "draft_check_max_hour", 4) or 0)
    if cap <= 0:
        return False
    now = time.time()
    seen = [t for t in _SPOKE.get(conversation_id, []) if now - t < 3600]
    _SPOKE[conversation_id] = seen
    if len(seen) >= cap:
        STATS["skipped_cap"] += 1
        return False
    return True


def _spoke(conversation_id: str) -> None:
    _SPOKE.setdefault(conversation_id, []).append(time.time())


async def after_turn(conversation_id: str, tenant_id: str | None, ask: str, reply: str, state: dict, settings) -> str:
    """Runs in the background once the reply is already on her screen, so nothing waits for it. Returns the note it
    published (tests read it); '' when it stayed quiet, which is the normal case."""
    from .santosh import _stopped
    if not getattr(settings, "draft_check", True) or conversation_id in _stopped or state.get("halted"):
        return ""
    if str(reply or "").startswith(("Maaf kijiye", "Yeh kaam lamba", "Theek, rok")):
        return ""
    g = worth_checking(ask, reply, state.get("calls"), state.get("chat_tail", ""))
    if not g or not may_speak(conversation_id, settings):
        return ""
    try:
        from .. import usage
        if tenant_id and not usage.allowed(tenant_id, "draft_check"):
            return ""
    except Exception:
        pass
    v = await ask_model(ask, reply, state.get("calls"), settings)
    if not v or v.get("ok"):
        STATS["quiet"] += 1
        return ""
    line = note_of(v, g["loose"], g.get("src", ""))
    if not line:
        STATS["quiet"] += 1
        return ""
    _spoke(conversation_id)
    try:
        from ..events import notify
        notify(conversation_id, line)
    except Exception:
        log.exception("draft note failed")
        return ""
    try:   # the same quiet line into her live call, like every other note (v0.193)
        from .. import kaamwatch
        kaamwatch._voice(tenant_id or "", conversation_id, line.strip("()"))
    except Exception:
        log.debug("draft note voice failed", exc_info=True)
    return line
