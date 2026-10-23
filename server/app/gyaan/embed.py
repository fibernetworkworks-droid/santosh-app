"""Gyaan embedders and reranker (pluggable; chosen by GYAAN_EMBED, default auto).

auto = Voyage API (voyage-4-lite, when VOYAGE_API_KEY is set) -> FastEmbed on the VPS CPU (GYAAN_EMBED_MODEL, default the
MiniLM model Hoola already ships) -> "hash" (char n-grams of a spelling-forgiving key incl. transliterated Devanagari:
no model, no network, still matches Hinglish to Devanagari). Vectors are stored as int8 (~97% of float quality at 1/4 size).
Switching the model marks every chunk for re-embedding by the worker (the model name is stored per vector)."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from typing import Any

log = logging.getLogger("santosh.gyaan")

try:
    import numpy as np
except ImportError:            # pragma: no cover - numpy is in requirements
    np = None


def _unit(m):
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (m / n).astype(np.float32)


class HashEmbedder:
    """Deterministic, offline. Good enough for spelling variants and cross-script names; no real 'meaning'."""
    name = "hash-v1"

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _feats(self, text: str) -> list[str]:
        from .norm import phon
        t = phon(text)
        ws = re.findall(r"[a-z0-9]+", t)
        f = [f"w:{w}" for w in ws]
        for w in ws:
            g = f"#{w}#"
            f += [g[i:i + 3] for i in range(len(g) - 2)]
        return f

    def embed(self, texts: list[str], kind: str = "doc"):
        m = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for f in self._feats(t):
                h = hashlib.blake2b(f.encode(), digest_size=8).digest()
                j = int.from_bytes(h[:4], "little") % self.dim
                m[i, j] += 1.0 if h[4] & 1 else -1.0
        return _unit(m)


class FastEmbedder:
    def __init__(self, model: str):
        self.model = model
        self.name = f"fastembed:{model}"
        self._m = None
        self._lock = threading.Lock()

    def _get(self):
        if self._m is None:
            with self._lock:
                if self._m is None:
                    from .. import semantic
                    if self.model == semantic.MODEL:
                        self._m = semantic._model() or False      # loaded once for the whole server
                    else:
                        from fastembed import TextEmbedding
                        self._m = TextEmbedding(self.model)
        return self._m or None

    def embed(self, texts: list[str], kind: str = "doc"):
        m = self._get()
        if m is None:
            return None
        if "e5" in self.model.lower():          # e5 models are trained with these prefixes
            texts = [("query: " if kind == "query" else "passage: ") + t for t in texts]
        vs = list(m.embed(texts, batch_size=16))
        return _unit(np.asarray(vs, dtype=np.float32))


class VoyageEmbedder:
    def __init__(self, model: str, key: str):
        self.model, self.key = model, key
        self.name = f"voyage:{model}"

    def embed(self, texts: list[str], kind: str = "doc"):
        import httpx
        out = []
        for i in range(0, len(texts), 96):
            r = httpx.post("https://api.voyageai.com/v1/embeddings", timeout=30,
                           headers={"Authorization": f"Bearer {self.key}"},
                           json={"input": texts[i:i + 96], "model": self.model,
                                 "input_type": "query" if kind == "query" else "document"})
            r.raise_for_status()
            data = sorted(r.json().get("data") or [], key=lambda d: d.get("index", 0))
            out += [d["embedding"] for d in data]
        return _unit(np.asarray(out, dtype=np.float32))


class GeminiEmbedder:
    def __init__(self, model: str):
        self.model = model
        self.name = f"gemini:{model}"

    def embed(self, texts: list[str], kind: str = "doc"):
        from google import genai
        from google.genai import types
        from ..config import get_settings
        c = genai.Client(api_key=get_settings().gemini_api_key)
        out = []
        for i in range(0, len(texts), 64):
            r = c.models.embed_content(model=self.model, contents=texts[i:i + 64], config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY" if kind == "query" else "RETRIEVAL_DOCUMENT"))
            out += [e.values for e in r.embeddings]
        return _unit(np.asarray(out, dtype=np.float32))


_CHOSEN: dict[str, Any] = {}
_CLOCK = threading.Lock()


def embedder():
    """The configured embedder (None only when numpy is missing)."""
    if np is None:
        return None
    from ..config import get_settings
    st = get_settings()
    want = (st.gyaan_embed or "auto").strip().lower()
    key = f"{want}|{st.gyaan_embed_model}|{bool(st.voyage_api_key)}|{os.environ.get('SEMANTIC_OFF', '')}"
    with _CLOCK:
        if key in _CHOSEN:
            return _CHOSEN[key]
        e: Any = None
        if want in ("voyage", "auto") and st.voyage_api_key:
            e = VoyageEmbedder(st.gyaan_voyage_model, st.voyage_api_key)
        elif want == "gemini" and st.gemini_api_key:
            e = GeminiEmbedder(st.gyaan_gemini_model)
        elif want.startswith("fastembed") or (want == "auto" and os.environ.get("SEMANTIC_OFF", "").lower() not in ("1", "true", "yes")):
            model = want.split(":", 1)[1] if ":" in want else st.gyaan_embed_model
            try:
                import fastembed  # noqa: F401
                e = FastEmbedder(model)
            except ImportError:
                log.info("fastembed not installed: Gyaan uses the offline hash embedder")
        if e is None:
            e = HashEmbedder()
        _CHOSEN[key] = e
        return e


def reset() -> None:
    with _CLOCK:
        _CHOSEN.clear()


def safe_embed(texts: list[str], kind: str = "doc"):
    """Embed with the configured model; on any failure fall back to the hash embedder for THIS call is NOT done (vectors of
    two models can't be mixed) - returns (None, name) and the caller keeps keyword search only."""
    e = embedder()
    if e is None or not texts:
        return None, ""
    try:
        return e.embed(texts, kind), e.name
    except Exception as ex:
        log.warning("gyaan embed (%s) failed: %s", e.name, ex)
        return None, e.name


# ---------------------------------------------------------------- int8 storage
def quantize(v) -> tuple[bytes, float]:
    scale = float(np.max(np.abs(v))) / 127.0 or 1e-9
    q = np.clip(np.round(v / scale), -127, 127).astype(np.int8)
    return q.tobytes(), scale


def dequantize_rows(blobs: list[bytes], scales: list[float], dim: int):
    m = np.frombuffer(b"".join(blobs), dtype=np.int8).reshape(len(blobs), dim).astype(np.float32)
    return m * np.asarray(scales, dtype=np.float32)[:, None]


# ---------------------------------------------------------------- reranker (API; text chat only, never in a call)
def rerank(query: str, docs: list[str]) -> list[float] | None:
    from ..config import get_settings
    st = get_settings()
    if not (st.gyaan_rerank and st.voyage_api_key and docs):
        return None
    try:
        import httpx
        r = httpx.post("https://api.voyageai.com/v1/rerank", timeout=12, headers={"Authorization": f"Bearer {st.voyage_api_key}"},
                       json={"query": query, "documents": [d[:4000] for d in docs], "model": st.gyaan_rerank_model})
        r.raise_for_status()
        scores = [0.0] * len(docs)
        for d in r.json().get("data") or []:
            scores[int(d["index"])] = float(d["relevance_score"])
        return scores
    except Exception as ex:
        log.warning("gyaan rerank failed (keeping fusion order): %s", ex)
        return None
