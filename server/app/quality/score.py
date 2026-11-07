"""v0.224 The scorer: pure code, no model. One reply in, numbers out - so the same reply always scores the same and
two runs can be compared honestly.

It measures SHAPE and HONESTY, the two things the rulebook (v0.221) can be held to in code: answer first, a length
that fits the question, light formatting, her script, no filler, no closing "aur kuch?", no figure that came from
nowhere, no claim of work that never ran. Whether the content is RIGHT is not code's job - that is the optional
judge in run.py, and the owner's own eyes.
"""
from __future__ import annotations

import re

PENALTY = {"filler": 10, "closing": 6, "short": 8, "long": 12, "script": 15, "list": 8, "plain": 5,
           "answer_first": 12, "invent": 20, "claim": 25, "questions": 10}
INVENT_CAP = 40

_FILLER = re.compile(r"^\s*(great question|good question|excellent question|behtareen sawaal|bahut (accha|badhiya) sawaal"
                     r"|shandaar sawaal|bilkul|zaroor|of course|absolutely|sure|certainly|wah|great|awesome|perfect)"
                     r"\s*[!.,:]+", re.I)
_CLOSING = re.compile(r"(aur kuch(\s*(chahiye|batao|poochhna|poochna))?\s*\??|kuch aur\s*\??|anything else\s*\??"
                      r"|koi aur sawaal\s*\??|let me know if you need anything else\.?)\s*$", re.I)
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⬀-⯿️]")
_DEVA = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")
_LIST = re.compile(r"(?m)^\s{0,6}(?:[-*+]\s+|\d+[.)]\s+)")
_HEAD = re.compile(r"(?m)^\s{0,3}#{1,6}\s+")
_BOLD = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
_CODE = re.compile(r"`[^`\n]+`|```")
_TABLE = re.compile(r"(?m)^\s*\|.*\|\s*$")
_SEP = re.compile(r"(?m)^\s*\|?[\s:-]*-{2,}[\s:|-]*\|?\s*$")
_LINK = re.compile(r"https?://|\]\(")
_YESNO = re.compile(r"\b(haan|haa+n|ha|ji|nahi+|na|nope|yes|no|bilkul|sakta|sakti|sakte|paunga|paungi|kar sakta"
                    r"|kar sakti|nahin|हाँ|हां|नहीं|नाही|होय)\b", re.I)
_STOP = {"ka", "ki", "ke", "kya", "hai", "hain", "ho", "hota", "hoti", "mein", "me", "se", "ko", "aur", "par", "tak",
         "kar", "karo", "karna", "kaise", "kab", "kahan", "kitna", "kitni", "mera", "meri", "main", "tum", "aap",
         "yeh", "woh", "is", "us", "to", "the", "a", "an", "of", "and", "is", "it", "do", "i"}


def words(text: str) -> int:
    return len([w for w in re.split(r"\s+", str(text or "").strip()) if w])


def first_sentence(text: str) -> str:
    t = _HEAD.sub("", str(text or "")).strip()
    m = re.search(r"[.!?\n]", t)
    return (t[:m.start() + 1] if m else t).strip()


def fmt(text: str) -> dict:
    t = str(text or "")
    rows = _TABLE.findall(t)
    return {"bold": len(_BOLD.findall(t)), "headings": len(_HEAD.findall(t)),
            "tables": 1 if (len(rows) >= 2 and _SEP.search(t)) else 0,
            "list_lines": len(_LIST.findall(t)), "code": len(_CODE.findall(t)),
            "emoji": len(_EMOJI.findall(t)), "links": len(_LINK.findall(t)),
            "lines": len([ln for ln in t.splitlines() if ln.strip()])}


def filler_open(text: str) -> str:
    m = _FILLER.match(str(text or ""))
    return m.group(1) if m else ""


def closing_question(text: str) -> bool:
    return bool(_CLOSING.search(str(text or "").strip()))


def script_of(text: str) -> str:
    t = str(text or "")
    d, lat = len(_DEVA.findall(t)), len(_LATIN.findall(t))
    if not d and not lat:
        return "none"
    return "deva" if d >= max(6, 0.25 * (d + lat)) else "latin"


def _content(text: str) -> set[str]:
    return {w for w in re.findall(r"[\wऀ-ॿ]+", str(text or "").lower()) if w not in _STOP and len(w) > 2}


def answer_first(ask_text: str, reply: str, kind: str) -> bool:
    """The first sentence carries the answer: it is not a filler, it does not just hand her question back, and for a
    yes / no ask it really says yes or no."""
    fs = first_sentence(reply)
    if not fs or filler_open(reply):
        return False
    her = _content(ask_text)
    mine = _content(fs)
    if her and fs.rstrip().endswith("?") and len(her & mine) >= 0.6 * len(her):
        return False                       # her question handed back as a question
    if kind == "yesno" and not _YESNO.search(fs):
        return False
    return True


def band_fit(n: int, band) -> str:
    lo, hi = band
    return "short" if n < lo else "long" if n > hi else "ok"


def invented(reply: str, ask: dict, calls: list[dict] | None = None) -> list[str]:
    """Figures in the reply that came from nowhere: not from her turns, not from what the ask itself allows, not from
    a tool result. Reuses v0.223's own gate so both features agree on what a hard fact is."""
    from ..agent import draftcheck
    src = " ".join(list(_turns(ask)) + [str(x) for x in ask.get("facts", [])])
    src += " " + draftcheck.sources_text("", calls or [])
    return draftcheck.loose_facts(reply, src)


def _turns(ask: dict) -> list[str]:
    from .asks import turns_of
    return turns_of(ask)


def fake_claim(reply: str, calls: list[dict] | None) -> str:
    from ..agent import draftcheck
    c = draftcheck.claims_done(reply)
    return c if (c and draftcheck.nothing_ran(calls)) else ""


def score_one(ask: dict, reply: str, meta: dict | None = None) -> dict:
    """One ask's card: every number, every broken rule, and what it cost out of 100."""
    meta = dict(meta or {})
    want = set(ask.get("want", []))
    r = str(reply or "")
    n = words(r)
    f = fmt(r)
    flags, lost = [], 0

    def hit(flag: str, why: str = "") -> None:
        nonlocal lost
        flags.append(flag + (f" ({why})" if why else ""))
        lost += PENALTY[flag.split(":")[0]]

    if "no_filler" in want:
        fo = filler_open(r)
        if fo:
            hit("filler", fo)
        if closing_question(r):
            hit("closing")
    fitv = band_fit(n, ask.get("band", (0, 10 ** 6)))
    if fitv != "ok":
        hit(fitv, f"{n} shabd")
    if "script" in want:
        her = script_of(" ".join(_turns(ask)))
        if her != "none" and script_of(r) != her:
            hit("script", f"{her} -> {script_of(r)}")
    if "no_list" in want and f["list_lines"] >= 2:
        hit("list", f"{f['list_lines']} lines")
    if "plain" in want and (f["bold"] or f["headings"] or f["tables"]):
        hit("plain")
    if "answer_first" in want and not answer_first(" ".join(_turns(ask)), r, ask.get("kind", "")):
        hit("answer_first")
    inv = invented(r, ask, meta.get("calls")) if "no_invent" in want else []
    if inv:
        flags.append("invent (" + ", ".join(inv[:3]) + ")")
        lost += min(INVENT_CAP, PENALTY["invent"] * len(inv))
    claim = fake_claim(r, meta.get("calls")) if ("no_claim" in want or not meta.get("calls")) else ""
    if claim:
        hit("claim", claim)
    if "one_question" in want and r.count("?") >= 2:
        hit("questions", f"{r.count('?')} sawaal")

    return {"id": ask["id"], "kind": ask["kind"], "words": n, "fit": fitv, "script": script_of(r),
            "fmt": f, "flags": flags, "points": max(0, 100 - lost),
            "ttfw_ms": meta.get("ttfw_ms"), "total_ms": meta.get("total_ms"), "steps": meta.get("steps"),
            "model_calls": meta.get("model_calls"), "prompt_kb": meta.get("prompt_kb"),
            "tools": meta.get("tools"), "reply": r[:1200]}


def totals(cards: list[dict]) -> dict:
    """The run's own line: the average score, every flag counted, and the timings that matter."""
    def mid(vals, q=0.5):
        v = sorted(x for x in vals if isinstance(x, (int, float)))
        return None if not v else v[min(len(v) - 1, int(q * len(v)))]

    counts: dict[str, int] = {}
    for c in cards:
        for fl in c["flags"]:
            counts[fl.split(" (")[0]] = counts.get(fl.split(" (")[0], 0) + 1
    pts = [c["points"] for c in cards]
    return {"asks": len(cards), "points": round(sum(pts) / len(pts), 1) if pts else None,
            "clean": sum(1 for c in cards if not c["flags"]), "flags": counts,
            "words_median": mid([c["words"] for c in cards]),
            "ttfw_median_ms": mid([c["ttfw_ms"] for c in cards]),
            "ttfw_p90_ms": mid([c["ttfw_ms"] for c in cards], 0.9),
            "total_median_ms": mid([c["total_ms"] for c in cards]),
            "prompt_kb_median": mid([c["prompt_kb"] for c in cards]),
            "tools_median": mid([c["tools"] for c in cards])}
