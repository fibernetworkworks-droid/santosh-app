"""HOOLA CODER dedup - three tiers, only the first two act alone (v0.473.0).

claude-mem's ladder, ported:
  Tier 0  exact content hash      -> re-confirm (reinforce + occurrence_count), never a new row
  Tier 0b normalized title key    -> the same titled memory re-confirmed, same as above
  Tier 1  near-duplicate TF-IDF   -> REVIEW ONLY: cosine >= 0.80 AND no IDF veto fires. A candidate
          row is written for a human decision; nothing is ever auto-merged on Tier 1.

The IDF veto is Fellegi-Sunter logic in miniature: if a token that appears in <=10 of the
project's records is present in exactly one of the two titles, the pair is distinct no matter
how high the cosine - a rare distinctive word (a function name, a version) is evidence, not
noise. Near-dup scanning is opt-in via coder_dedup_fuzzy and gated on a minimum corpus
(coder_dedup_min_docs, default 10), because IDF on 3 documents is astrology.
"""
from __future__ import annotations

import math
import re

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)

COSINE_THRESHOLD = 0.80
MIN_SHARED_TOKENS = 2
IDF_VETO_DF = 10
MAX_SCAN = 2000


def tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def idf(df: int, n: int) -> float:
    return math.log(1.0 + n / (df + 0.5))


def tfidf_cosine(a: list[str], b: list[str], idf_fn) -> float:
    """Cosine over IDF-weighted term frequencies (the claude-mem nearDuplicate maths)."""
    if not a or not b:
        return 0.0
    ta: dict[str, float] = {}
    for t in a:
        ta[t] = ta.get(t, 0.0) + 1.0
    tb: dict[str, float] = {}
    for t in b:
        tb[t] = tb.get(t, 0.0) + 1.0
    wa = {t: (1.0 + math.log(c)) * idf_fn(t) for t, c in ta.items()}
    wb = {t: (1.0 + math.log(c)) * idf_fn(t) for t, c in tb.items()}
    dot = sum(v * wb.get(t, 0.0) for t, v in wa.items())
    na = math.sqrt(sum(v * v for v in wa.values()))
    nb = math.sqrt(sum(v * v for v in wb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def idf_veto(a: list[str], b: list[str], df_fn, doc_count: int) -> str | None:
    """Return the distinctive token that vetoes the merge, or None if no veto fires.
    theta = idf(IDF_VETO_DF + 1, doc_count): a token rarer than that carries identity."""
    if doc_count <= 0:
        return None
    theta = idf(IDF_VETO_DF + 1, doc_count)
    sa, sb = set(a), set(b)
    for tok in sa ^ sb:
        if df_fn(tok) <= IDF_VETO_DF and idf(df_fn(tok), doc_count) > theta:
            return tok
    return None


def classify_pair(title_a: str, title_b: str, df_fn, doc_count: int) -> tuple[float, bool, str | None]:
    """(score, is_near_duplicate, veto_token). A pair is a candidate when cosine >= threshold,
    they share >= MIN_SHARED_TOKENS, and the veto stays silent."""
    ta, tb = tokens(title_a), tokens(title_b)
    shared = len(set(ta) & set(tb))
    if shared < MIN_SHARED_TOKENS:
        return 0.0, False, None
    score = tfidf_cosine(ta, tb, lambda t: idf(df_fn(t), doc_count))
    if score < COSINE_THRESHOLD:
        return score, False, None
    veto = idf_veto(ta, tb, df_fn, doc_count)
    return score, veto is None, veto
