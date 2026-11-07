"""Hand-built BM25 Okapi — no rank_bm25, no new dependency (the port law).

BM25 is a published ranking function (Robertson/Sparck Jones), not anyone's code: for a query term q in
document d,  idf(q) * (f(q,d) * (k1+1)) / (f(q,d) + k1 * (1 - b + b * |d|/avgdl)).
k1=1.2 / b=0.75 are the standard defaults and the ones crawl4ai uses, so scores stay comparable.

Used by: prune.BM25Filter (keep only the blocks that answer her question) and enough.py (coverage).
"""
from __future__ import annotations

import math
import re

_WORD = re.compile(r"[a-z0-9]+")
# Deliberately small: an English stop list only. Hinglish/Hindi words carry meaning here and must NOT be
# stripped - "kahan", "kitna", "daam" are the whole query on a Hoola ask.
_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he", "in", "is", "it",
         "its", "of", "on", "or", "that", "the", "to", "was", "were", "will", "with", "this", "these"}


def words(text: str, keep_stop: bool = False) -> list[str]:
    ws = _WORD.findall((text or "").lower())
    return ws if keep_stop else [w for w in ws if w not in _STOP and len(w) > 1]


class BM25:
    """Scores documents against a query. Documents are token lists; build once, score many."""

    __slots__ = ("docs", "df", "idf", "avgdl", "k1", "b", "n")

    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75) -> None:
        self.docs = docs
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.avgdl = (sum(len(d) for d in docs) / self.n) if self.n else 0.0
        self.df: dict[str, int] = {}
        for d in docs:
            for w in set(d):
                self.df[w] = self.df.get(w, 0) + 1
        # idf with the +1 inside the log so a term in EVERY document scores ~0 instead of going negative
        # (the classic BM25 idf can go negative and then a common word would push a block DOWN).
        self.idf = {w: math.log(1.0 + (self.n - c + 0.5) / (c + 0.5)) for w, c in self.df.items()}

    def score(self, query: list[str], i: int) -> float:
        d = self.docs[i]
        if not d:
            return 0.0
        dl = len(d)
        freq: dict[str, int] = {}
        for w in d:
            freq[w] = freq.get(w, 0) + 1
        total = 0.0
        for q in query:
            f = freq.get(q, 0)
            if not f:
                continue
            idf = self.idf.get(q, 0.0)
            total += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
        return total

    def scores(self, query: list[str]) -> list[float]:
        return [self.score(query, i) for i in range(self.n)]

    def covered(self, query: list[str]) -> set[str]:
        """Which query terms appear in ANY document - the coverage input for enough.py."""
        seen: set[str] = set()
        for d in self.docs:
            seen |= set(d)
        return {q for q in query if q in seen}
