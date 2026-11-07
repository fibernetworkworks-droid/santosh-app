"""Item 6: chunking strategies for page content. Hand-built (the port law).

Hoola chunks in xlsxgen / kalam / tourguide, but nothing chunked PAGE text - so a long page either fits the
budget or gets truncated mid-sentence. These split it on meaning instead.

Six strategies, all pure string work, no model, no NLTK download:
  identity      - one chunk, the no-op (so a caller can switch strategy without branching)
  regex         - split on a pattern (default: a blank line = a paragraph)
  sentence      - sentence boundaries, with the abbreviation traps handled (Dr., Rs., No., i.e.)
  fixed_words   - N words a chunk
  sliding       - N words a chunk, step M (overlap = N-M), so a fact spanning a boundary is never cut once
  topic         - greedy segmentation: start a new chunk when a paragraph's vocabulary stops overlapping
                  the current one (a cheap TextTiling, no embeddings)

Every strategy returns list[str] and never loses text (except `sliding`, which repeats it on purpose).
"""
from __future__ import annotations

import re

from .bm25 import words

_PARA = re.compile(r"\n\s*\n+")
# Sentence end: ., !, ?, or a Hindi danda, followed by space + a capital/Devanagari start.
_SENT = re.compile(r"(?<=[.!?।])\s+(?=[A-Zऀ-ॿ\"'(])")
# Abbreviations that must NOT end a sentence (the classic false split).
_ABBR = re.compile(r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|No|Rs|vs|etc|viz|approx|Co|Ltd|Pvt|Inc|"
                   r"i\.e|e\.g|a\.m|p\.m|Fig|Vol|Ch|pp)\.$", re.I)


def identity(text: str) -> list[str]:
    t = (text or "").strip()
    return [t] if t else []


def regex_chunks(text: str, pattern: str = r"\n\s*\n+", min_chars: int = 1) -> list[str]:
    parts = [p.strip() for p in re.split(pattern, text or "")]
    return [p for p in parts if len(p) >= max(1, min_chars)]


def sentences(text: str) -> list[str]:
    """Sentence split that does not break on 'Rs. 380' or 'Dr. Patil'."""
    out: list[str] = []
    buf = ""
    for piece in _SENT.split((text or "").strip()):
        cand = (buf + " " + piece).strip() if buf else piece.strip()
        if _ABBR.search(cand):
            buf = cand          # ended on an abbreviation: the sentence continues
            continue
        buf = ""
        if cand:
            out.append(cand)
    if buf:
        out.append(buf)
    return out


def fixed_words(text: str, n: int = 200) -> list[str]:
    ws = (text or "").split()
    n = max(1, n)
    return [" ".join(ws[i:i + n]) for i in range(0, len(ws), n)] or []


def sliding(text: str, n: int = 200, step: int = 150) -> list[str]:
    """Overlapping windows, so a fact that straddles a boundary survives in one piece somewhere."""
    ws = (text or "").split()
    n = max(1, n)
    step = max(1, min(step, n))
    if len(ws) <= n:
        return [" ".join(ws)] if ws else []
    out = []
    i = 0
    while i < len(ws):
        out.append(" ".join(ws[i:i + n]))
        if i + n >= len(ws):
            break
        i += step
    return out


def topic(text: str, min_overlap: float = 0.18, max_chars: int = 3000) -> list[str]:
    """Greedy topic segmentation. Start a new chunk when the next paragraph stops sharing vocabulary with
    the one being built - a cheap TextTiling that needs no embeddings and no model."""
    paras = [p.strip() for p in _PARA.split(text or "") if p.strip()]
    if not paras:
        return []
    out: list[str] = []
    cur = [paras[0]]
    cur_terms = set(words(paras[0]))
    for p in paras[1:]:
        pt = set(words(p))
        denom = min(len(cur_terms), len(pt)) or 1
        overlap = len(cur_terms & pt) / float(denom)
        joined = len("\n\n".join(cur))
        if overlap < min_overlap or joined + len(p) > max_chars:
            out.append("\n\n".join(cur))
            cur, cur_terms = [p], set(pt)
        else:
            cur.append(p)
            cur_terms |= pt
    out.append("\n\n".join(cur))
    return out


STRATEGIES = {"identity": identity, "regex": regex_chunks, "sentence": sentences,
              "fixed_words": fixed_words, "sliding": sliding, "topic": topic}


def chunk(text: str, how: str = "topic", **kw) -> list[str]:
    fn = STRATEGIES.get(str(how or "topic").lower())
    if fn is None:
        raise ValueError(f"unknown chunking strategy {how!r}; have {sorted(STRATEGIES)}")
    return fn(text, **kw)
