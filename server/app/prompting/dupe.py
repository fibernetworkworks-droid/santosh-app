"""Near-duplicate check for prompts and recipes (no model).

The text is normalised (blanks of every shape, punctuation and case removed), then compared two ways: the share of
words in common (Jaccard) and the share of three-letter pieces in common (trigrams), weighted 0.6 / 0.4. 1.0 = the
same words, 0.85 and up = a copy with small changes. Ported from prompts.chat (src/lib/similarity.ts, MIT licence,
see THIRD_PARTY_NOTICES.md)."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

SAME = 0.85          # treated as a copy
CLOSE = 0.6          # shown to the reviewer as "close to"


def normalise(text: str) -> str:
    t = str(text or "")
    t = re.sub(r"\$\{[^}]+\}", " ", t)
    t = re.sub(r"\{\{[^}]+\}\}|\{[^}]+\}", " ", t)
    t = re.sub(r"\[[^\]]+\]", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=8192)
def _sets(norm: str) -> tuple[frozenset[str], frozenset[str]]:
    words = frozenset(w for w in norm.split(" ") if w)
    padded = "  " + norm + "  "
    grams = frozenset(padded[i:i + 3] for i in range(len(padded) - 2))
    return words, grams


def _j(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(a: str, b: str) -> float:
    na, nb = normalise(a), normalise(b)
    if na == nb:
        return 1.0 if na else 0.0
    if not na or not nb:
        return 0.0
    wa, ga = _sets(na)
    wb, gb = _sets(nb)
    return round(_j(wa, wb) * 0.6 + _j(ga, gb) * 0.4, 3)


def closest(text: str, pool: Iterable[dict[str, Any]], least: float = CLOSE, top: int = 3) -> list[dict[str, Any]]:
    """The pool's entries ({id, title, text}) closest to `text`, best first, each with its score."""
    out = []
    for p in pool:
        s = similarity(text, p.get("text") or "")
        if s >= least:
            out.append({"id": p.get("id"), "title": p.get("title") or "", "score": s})
    return sorted(out, key=lambda x: -x["score"])[:top]
