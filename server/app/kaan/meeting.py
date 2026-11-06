"""KAAN W1 meeting minutes: DETERMINISTIC structure from a stored transcript.

No model call, no invention: turn stats, content keywords, and action-item CANDIDATES found by
cue words (marked as candidates, never as decisions). The prose summary is Santosh's job when
the owner asks - this module only hands her an honest skeleton with every number traceable to
the stored row. Zero dependencies, zero network (port law + inertness law).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

# stop words (light en + hi function words) - "should" stays OUT on purpose, it is an action cue
STOP = frozenset("""aur ke ka ki ko hai hain tha thi the mein se ye yeh woh vo ek do teen theek haan nahi ha bhi
hi to na par lekin matlab liye wala wali hoga hogi hue raha rahi kya kyun kab kaisa aisa waisa apna uska isko usko
and the a an of to in is was for on with that this it at be are were will would i you he she we they my your our
his her their me him them us so if not no yes okay ok ah oh am pm but as by from has have had do does did can
could about into over after before very also just there here what when where who how""".split())

ACTION_CUES = (
    r"\bkal\b", r"\baaj hi\b", r"\bwill\b", r"\bneed to\b", r"\bshould\b", r"\bsend\b", r"\bbhej",
    r"\bmail\b", r"\bemail\b", r"\bcall\b", r"\bphone\b", r"\bremind", r"\bfollow ?up\b", r"\bkarna\b",
    r"\bkarenge\b", r"\bkarenga\b", r"\bdijiye\b", r"\bdijiye", r"\bdena\b", r"\bdenge\b", r"\bcheck\b",
    r"\bverify\b", r"\btodo\b", r"\bdeadline\b", r"\bshaam\b", r"\bsubah\b", r"\bjaldi\b", r"\braat\b",
    r"\bsomvaar\b", r"\bmangalvaar\b", r"\bbudhvaar\b", r"\bguruvaar\b", r"\bshukravaar\b", r"\bshanivaar\b",
    r"\bmonday\b", r"\btuesday\b", r"\bwednesday\b", r"\bthursday\b", r"\bfriday\b", r"\bsaturday\b", r"\bsunday\b",
)
ACTION_RE = re.compile("|".join(ACTION_CUES), re.IGNORECASE)
_SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


def minutes(row: dict[str, Any]) -> dict[str, Any]:
    """row = a kaan_transcripts row dict (service._row + speakers). Every number traces to the row."""
    spk = row.get("speakers") if isinstance(row.get("speakers"), dict) else {}
    turns = spk.get("turns") or []
    text = row.get("text") or ""
    if not turns:
        turns = [{"turn": 1, "speaker": "", "start": 0.0, "end": float(row.get("duration_s") or 0.0),
                  "n_words": len(text.split()), "text": text}]

    total_words = sum(max(1, int(t.get("n_words") or len((t.get("text") or "").split()))) for t in turns)
    per_turn = []
    for t in turns:
        w = max(1, int(t.get("n_words") or len((t.get("text") or "").split())))
        per_turn.append({"turn": t.get("turn"), "speaker": (t.get("speaker") or "").strip(),
                         "n_words": w, "word_share": round(w / total_words, 3),
                         "seconds": round(max(0.0, float(t.get("end") or 0.0) - float(t.get("start") or 0.0)), 2)})

    tokens = [w.lower() for w in re.findall(r"[\w\u0900-\u097F]+", text)]
    content = [w for w in tokens if w not in STOP and len(w) >= 3]
    keywords = [w for w, _n in Counter(content).most_common(8)]

    candidates: list[dict[str, Any]] = []
    for t in turns:
        for sent in [s.strip() for s in _SENT_SPLIT.split(t.get("text") or "") if s.strip()]:
            m = ACTION_RE.search(sent)
            if m:
                candidates.append({"turn": t.get("turn"), "speaker": (t.get("speaker") or "").strip(),
                                   "cue": m.group(0).strip(), "text": sent[:200]})

    return {"tid": row.get("id"), "file_name": row.get("file_name"), "language": row.get("language"),
            "task": row.get("task"), "model": row.get("model"), "duration_s": row.get("duration_s"),
            "n_turns": len(turns), "turns": per_turn, "keywords": keywords,
            "action_candidates": candidates,
            "note": ("yeh structure + stats + cue-based candidates hain, pakka faisla nahi - saar (summary) "
                     "Santosh likhegi jab aap kahein; speaker naam diarize ke names se aate hain, bina "
                     "naam ke turn number hi sach hai.")}
