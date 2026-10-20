"""v0.51 Meaning-based recall in Hinglish (FastEmbed, Apache-2.0, CPU): "beti ka school" finds "Riya ki class teacher
Mrs Rao" even with no shared words. Model paraphrase-multilingual-MiniLM-L12-v2 (50+ languages incl. Hindi), downloaded
once (~220 MB). Without it: plain word overlap."""
from __future__ import annotations

import logging
import re
import threading
from typing import Any

log = logging.getLogger("santosh.semantic")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_EMB = None
_LOCK = threading.Lock()
_CACHE: dict[str, list[float]] = {}


def _model():
    global _EMB
    if _EMB is None:
        with _LOCK:
            if _EMB is None:
                try:
                    from fastembed import TextEmbedding
                    _EMB = TextEmbedding(MODEL)
                except Exception as e:
                    log.info("fastembed unavailable: %s", e)
                    _EMB = False
    return _EMB or None


def _vecs(texts: list[str]) -> list[list[float]] | None:
    m = _model()
    if m is None:
        return None
    todo = [t for t in texts if t not in _CACHE]
    if todo:
        for t, v in zip(todo, m.embed(todo)):
            _CACHE[t] = [float(x) for x in v]
        while len(_CACHE) > 20000:
            _CACHE.pop(next(iter(_CACHE)))
    return [_CACHE[t] for t in texts]


def _cos(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    return num / (da * db) if da and db else 0.0


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9ऀ-ॿ]+", (t or "").lower()) if len(w) > 2}


def rank(query: str, items: list[tuple[Any, str]], top: int = 8, floor: float = 0.35) -> list[tuple[Any, str, float]]:
    """items = [(id, text)] -> best matches [(id, text, score)]."""
    if not items or not (query or "").strip():
        return []
    vs = _vecs([query] + [t for _, t in items])
    if vs is not None:
        q = vs[0]
        scored = [(i, t, _cos(q, v)) for (i, t), v in zip(items, vs[1:])]
        scored = [x for x in scored if x[2] >= floor]
    else:
        qw = _words(query)
        scored = [(i, t, len(qw & _words(t)) / (len(qw) or 1)) for i, t in items]
        scored = [x for x in scored if x[2] > 0]
    scored.sort(key=lambda x: -x[2])
    return scored[:top]


def available() -> bool:
    return _model() is not None
