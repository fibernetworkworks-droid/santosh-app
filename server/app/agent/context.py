"""v0.237 FULL CLAUDE MODE, Phase 1: the context gauge.

Claude chat sends the WHOLE conversation word for word on every message and only acts when the window is nearly
full. Hoola now does the same (CHAT_CONTEXT=claude): yaad.full_history loads every message, and before EVERY model
call this module measures the request (system prompt + tools + history) against the brain's window:

- it fits (under CHAT_CONTEXT_FULL_AT, default 75%)  -> sent exactly as loaded, word for word;
- too big                                             -> the SAFETY NET: the oldest exchanges are shortened the
  v0.108 way (her words + one line per step + the final reply), in blocks of 10 so the prompt prefix stays the
  same from turn to turn (cache), down to ~60%; if that is not enough the oldest blocks leave and the chat's rolling
  summary stands in for them. This turn's own messages are never touched. (Phase 2 replaces the net with a
  Claude-style compaction summary.)
- the model still says "too long" -> `squeeze`: the hard form (summary + the last few exchanges shortened, this
  turn's old tool results cut harder), retried ONCE by the step loop. A chat can no longer get stuck on its size.

The gauge learns: every answer reports how many tokens the model really read; the chars-per-token ratio of that
brain moves toward the truth (Hinglish / Devanagari take more tokens per word than English). A "too long" answer
makes the estimate more careful at once and, when the error names the real window, that number is used.

Pure projections: the caller's history list and its dicts are never edited (they are shared with _save and the
cache shaper). CHAT_CONTEXT=hoola keeps the old window byte for byte; only the overflow rescue still applies there.
"""
from __future__ import annotations

import json
import logging
import re
import time
from contextvars import ContextVar
from typing import Any

log = logging.getLogger("santosh.context")

CHARS_PER_TOKEN = 3.0          # careful default before the first real answer (English JSON ~3.5-4, Devanagari ~1.5-2)
RATIO_MIN, RATIO_MAX = 1.2, 6.0
LEARN_WEIGHT = 0.3             # how fast a real token count moves the ratio
BLOCK = 10                     # exchanges shortened / dropped together (prefix stays stable between turns)
TARGET_GAP = 0.15              # after the net runs the request lands this far under the line (room to grow)
SQUEEZE_KEEP = 6               # old exchanges the hard form keeps (shortened)
SQUEEZE_RESULT = 1500          # this turn's older tool results in the hard form

RATIO: dict[str, float] = {}           # brain -> learned chars per token
LIMIT_SEEN: dict[str, int] = {}        # brain -> a window a "too long" error named
LAST: dict[str, dict[str, Any]] = {}   # conversation -> the last reading (for /api/conversations/{id}/context)
CONV: ContextVar[str] = ContextVar("hoola_context_conv", default="")   # set around the step loop's model call only
STATS: dict[str, int] = {"measured": 0, "full": 0, "net": 0, "net_dropped": 0, "overflow": 0, "squeezed": 0,
                         "learned": 0}


def _settings():
    from ..config import get_settings
    return get_settings()


def full_mode(settings=None) -> bool:
    s = settings or _settings()
    return (getattr(s, "chat_context", "claude") or "claude").strip().lower() != "hoola"


def limit(brain: str, settings=None) -> int:
    s = settings or _settings()
    lim = {"glm": getattr(s, "chat_context_limit_glm", 200000),
           "omniroute": getattr(s, "chat_context_limit_omniroute", 128000)}.get(
        brain, getattr(s, "chat_context_limit_claude", 200000))
    seen = LIMIT_SEEN.get(brain)
    return max(8000, min(int(lim or 200000), seen or 10 ** 9))


def budget(brain: str, settings=None) -> int:
    s = settings or _settings()
    share = float(getattr(s, "chat_context_full_at", 0.75) or 0.75)
    return int(limit(brain, s) * min(0.95, max(0.2, share)))


def ratio(brain: str) -> float:
    return RATIO.get(brain, CHARS_PER_TOKEN)


def size(x: Any) -> int:
    """Characters of anything that goes into a request, the way it travels (JSON)."""
    if x is None:
        return 0
    if isinstance(x, str):
        return len(x)
    return len(json.dumps(x, ensure_ascii=False, default=str))


def tokens(brain: str, chars: int) -> int:
    return int(chars / ratio(brain)) + 1


def learn(brain: str, chars: int, real_tokens: int) -> None:
    """A model told us how many tokens it read for `chars` characters: move this brain's ratio toward the truth."""
    if not brain or chars < 2000 or not real_tokens or real_tokens < 200:
        return
    seen = max(RATIO_MIN, min(RATIO_MAX, chars / real_tokens))
    old = RATIO.get(brain)
    RATIO[brain] = seen if old is None else round(old + LEARN_WEIGHT * (seen - old), 4)
    STATS["learned"] += 1


def after_call(brain: str, system: Any, tools: Any, messages: list[dict], real_tokens: int | None,
               estimated: bool = False) -> None:
    """Called after every chat-brain answer with the tokens the model says it read (never a made-up count)."""
    if estimated or not real_tokens:
        return
    try:
        chars = size(system) + size(tools) + sum(size(m.get("content")) for m in messages if isinstance(m, dict))
        learn(brain, chars, int(real_tokens))
        conv = CONV.get()
        if conv:
            real(conv, int(real_tokens))
    except Exception:
        log.debug("context learn failed", exc_info=True)


_TOO_LONG = re.compile(
    r"prompt is too long|too many (input )?tokens|context[ _-]?length|context[ _-]?window|maximum context|"
    r"context_length_exceeded|input is too long|input too long|reduce the length|exceeds? the (model'?s? )?"
    r"(maximum|max|context)|too large for (the )?model'?s? context", re.I)
# a per-minute rate limit ("Request too large ... tokens per min (TPM): Limit 30000") is NOT the window being full:
# treating it as one would shrink the gauge to the rate number
_RATE = re.compile(r"rate.?limit|per min|tpm\b|tokens per minute|\b429\b|quota", re.I)


def is_overflow(e: BaseException | str) -> bool:
    t = str(e) or ""
    return bool(_TOO_LONG.search(t)) and not _RATE.search(t)


def overflowed(brain: str, e: BaseException | str) -> None:
    """The model refused for size: count more carefully from now on, and believe the window it named."""
    STATS["overflow"] += 1
    RATIO[brain] = max(RATIO_MIN, ratio(brain) * 0.75)
    # "250000 tokens > 200000 maximum", "maximum context length is 131072 tokens ... requested 140000": the window is
    # the smallest number the error names (a lone number can only be the request, never smaller than the window)
    nums = [int(n) for n in re.findall(r"\b(\d{4,7})\b", str(e).replace(",", ""))]
    nums = [n for n in nums if n >= 8000]
    if nums:
        LIMIT_SEEN[brain] = min(nums + ([LIMIT_SEEN[brain]] if brain in LIMIT_SEEN else []))


# ------------------------------------------------------------------ exchanges inside a loaded history
def _starts(m: dict) -> bool:
    """Her message begins an exchange: plain text (a merged nudge + her words counts too), never a tool result."""
    if m.get("role") != "user":
        return False
    c = m.get("content")
    if isinstance(c, str):
        return True
    return isinstance(c, list) and bool(c) and not any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in c)


def _exchanges(msgs: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    for m in msgs:
        if _starts(m) or not out:
            out.append([m])
        else:
            out[-1].append(m)
    return out


def _short(ex: list[dict]) -> list[dict]:
    from .. import yaad
    first = ex[0]
    if isinstance(first.get("content"), list):   # a merged start: its words as one plain text for compress
        words = " ".join(str(b.get("text", "")) for b in first["content"] if isinstance(b, dict)
                         and b.get("type") == "text")
        ex = [{"role": "user", "content": words}] + ex[1:]
    return yaad.compress(ex)


def _summary_msg(conversation_id: str) -> list[dict]:
    from .. import yaad
    try:
        summ = yaad.summary_block(conversation_id) if conversation_id else ""
    except Exception:
        summ = ""
    return [{"role": "user", "content": yaad.SUMMARY_OPEN + summ}] if summ else []


def _trim_results(msgs: list[dict], cap: int) -> list[dict]:
    """This turn's older tool results cut to `cap` (the newest step stays whole), copies only."""
    from .prune import MARK
    out = []
    n = len(msgs)
    for i, m in enumerate(msgs):
        c = m.get("content")
        if i >= n - 2 or m.get("role") != "user" or not isinstance(c, list):
            out.append(m)
            continue
        blocks = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_result" and isinstance(b.get("content"), str) \
                    and len(b["content"]) > cap:
                b = {**b, "content": b["content"][:cap - 300] + MARK + b["content"][-200:]}
            blocks.append(b)
        out.append({**m, "content": blocks})
    return out


def _flat(exs: list[list[dict]]) -> list[dict]:
    return [m for ex in exs for m in ex]


# ------------------------------------------------------------------ the gauge
def fit(history: list[dict], system: Any, tools: Any, brain: str, conversation_id: str = "", turn_start: int = 0,
        settings=None) -> tuple[list[dict], str]:
    """The request's history for this model call: (messages, form). form = full | net | hoola.
    `turn_start` = index where THIS turn's messages begin (never shortened)."""
    s = settings or _settings()
    fixed = size(system) + size(tools)
    hist_chars = sum(size(m.get("content")) for m in history)
    est = tokens(brain, fixed + hist_chars)
    line = budget(brain, s)
    STATS["measured"] += 1
    reading = {"brain": brain, "limit": limit(brain, s), "budget": line, "estimate": est,
               "chars": fixed + hist_chars, "ratio": round(ratio(brain), 3), "at": time.time()}
    if not full_mode(s):
        _note(conversation_id, reading, "hoola", est)
        return history, "hoola"
    if est <= line:
        STATS["full"] += 1
        _note(conversation_id, reading, "full", est)
        return history, "full"
    # the SAFETY NET: shorten the oldest exchanges (blocks of 10) until the request is ~15% under the line
    turn_start = max(0, min(turn_start, len(history)))
    old, cur = history[:turn_start], history[turn_start:]
    exs = _exchanges(old)
    target = int(limit(brain, s) * max(0.1, float(getattr(s, "chat_context_full_at", 0.75)) - TARGET_GAP))
    sizes = [sum(size(m.get("content")) for m in ex) for ex in exs]
    short = [None] * len(exs)
    total = fixed + sum(size(m.get("content")) for m in cur) + sum(sizes)
    i = 0
    while i < len(exs) and tokens(brain, total) > target:
        for j in range(i, min(i + BLOCK, len(exs))):
            short[j] = _short(exs[j])
            total += size([m.get("content") for m in short[j]]) - sizes[j]
            sizes[j] = size([m.get("content") for m in short[j]])
        i += BLOCK
    kept = [short[k] if short[k] is not None else exs[k] for k in range(len(exs))]
    drop = 0
    summ = _summary_msg(conversation_id)
    if tokens(brain, total) > target:   # even shortened it does not fit: the oldest blocks leave, the summary stays
        total += size([m.get("content") for m in summ])
        while drop < len(kept) and tokens(brain, total) > target:
            for j in range(drop, min(drop + BLOCK, len(kept))):
                total -= sizes[j]
            drop = min(drop + BLOCK, len(kept))
        STATS["net_dropped"] += 1
    out = (summ if drop else []) + _flat(kept[drop:]) + cur
    STATS["net"] += 1
    reading.update(shortened=sum(1 for x in short if x is not None), dropped=drop, after=tokens(brain, total))
    _note(conversation_id, reading, "net", tokens(brain, total))
    log.info("context net %s: ~%s tok > %s, %s exchanges shortened, %s dropped -> ~%s tok", conversation_id, est, line,
             reading["shortened"], drop, reading["after"])
    return out, "net"


def squeeze(history: list[dict], conversation_id: str = "", turn_start: int = 0) -> list[dict]:
    """The hard form after a "too long" answer: rolling summary + the last few old exchanges shortened + this turn
    with its older tool results cut hard. Retried once by the step loop."""
    STATS["squeezed"] += 1
    turn_start = max(0, min(turn_start, len(history)))
    old, cur = history[:turn_start], history[turn_start:]
    exs = _exchanges(old)
    keep = [_short(ex) for ex in exs[-SQUEEZE_KEEP:]]
    summ = _summary_msg(conversation_id) if len(exs) > SQUEEZE_KEEP else []
    out = summ + _flat(keep) + _trim_results(cur, SQUEEZE_RESULT)
    if conversation_id in LAST:
        LAST[conversation_id]["form"] = "squeezed"
    return out


def _note(conversation_id: str, reading: dict, form: str, est: int) -> None:
    if not conversation_id:
        return
    lim = reading.get("limit") or 1
    LAST[conversation_id] = {**reading, "form": form, "sent": est, "percent": round(100.0 * est / lim, 1)}
    if len(LAST) > 5000:
        for k in list(LAST)[:1000]:
            LAST.pop(k, None)


def real(conversation_id: str, real_tokens: int) -> None:
    """The model's own count for the last call of this chat (shown next to the estimate)."""
    r = LAST.get(conversation_id)
    if r is not None and real_tokens:
        r["real"] = int(real_tokens)
        r["real_percent"] = round(100.0 * real_tokens / (r.get("limit") or 1), 1)


def reading(conversation_id: str) -> dict[str, Any]:
    """How full this chat is: the last measured call, else an estimate of the chat alone (no prompt / tools yet)."""
    s = _settings()
    r = LAST.get(conversation_id)
    if r is not None:
        return {"mode": "claude" if full_mode(s) else "hoola", "measured": True, **r}
    from .. import yaad
    from . import llm
    hist = yaad.full_history(conversation_id) if full_mode(s) else yaad.history(conversation_id)
    try:
        brain = llm.choose(hist)
    except Exception:
        brain = "claude"
    est = tokens(brain, sum(size(m.get("content")) for m in hist))
    lim = limit(brain, s)
    return {"mode": "claude" if full_mode(s) else "hoola", "measured": False, "brain": brain, "limit": lim,
            "budget": budget(brain, s), "estimate": est, "percent": round(100.0 * est / lim, 1),
            "messages": len(hist), "ratio": round(ratio(brain), 3)}


def health() -> dict[str, Any]:
    s = _settings()
    return {"mode": "claude" if full_mode(s) else "hoola", "ratios": dict(RATIO), "limits_seen": dict(LIMIT_SEEN),
            "stats": dict(STATS)}
