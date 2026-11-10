"""HOOLA AEP retrieve - the retrieval layer (v0.570.0 HOOLA RETRIEVE, P6 of the
AEP plan). The langchain retrieval FEATURE SURFACE hand-built as house code after
re-reading upstream at the pinned commit aa2528fb980a290d2b06c83a1be43e60bc2348f9
(core/langchain_core/vectorstores/base.py 1111 lines + in_memory.py 546 + utils.py
(the MMR), embeddings/embeddings.py 78 + fake.py, indexing/base.py 661 + api.py
954 + in_memory.py, retrievers.py 328, and the text-splitters package's base.py +
character.py) - ZERO upstream code or imports (the port law).

Vectors are IN SCOPE per the 100% directive (the old exclusion is superseded).
The layer, in reading order:

- Document          : page_content + metadata + id (the upstream documents.py shape)
- Embeddings        : the ABC (embed_documents/embed_query + a-twins via to_thread)
- DeterministicEmbeddings : the zero-network test embedder - sha256-seeded unit
                      vectors, byte-identical across processes (upstream fake.py's
                      deterministic idea, numpy-free)
- maximal_marginal_relevance : pure-python MMR (the numpy port, same formula:
                      lambda_mult * sim_to_query - (1-lambda_mult) * max_sim_selected)
- VectorStore       : the ABC - add_texts/add_documents/delete/get_by_ids, search
                      dispatch (similarity | similarity_score_threshold | mmr),
                      with_score, with_relevance_scores (the [0,1] contract +
                      score_threshold filter), by_vector, MMR search, from_texts/
                      from_documents, as_retriever, a-twins
- SqliteVectorStore : the sqlite-first ANN - stdlib sqlite3 (WAL), a path OR the
                      vault's sqlalchemy Engine (the P3 SqliteSaver seam: lazy
                      raw_connection, table ensured on first use), one table
                      aep_vectors(id, doc, vec, ts); exact cosine kNN scan with a
                      metadata-equality filter (the honest first cut - the table
                      shape and the index() dedup are the ANN substrate; a real
                      ANN index slots in behind the same ABC later)
- RecordManager + SqliteRecordManager : the indexing ledger - namespace,
                      create_schema/get_time/update(keys, group_ids,
                      time_at_least)/exists/list_keys(before/after/group_ids/
                      limit)/delete_keys; stdlib sqlite, one table
                      aep_index_records(uuid, updated_at, group_id)
- index()/aindex()  : the dedup flow - hash each doc (content and metadata
                      hashed SEPARATELY, then the concatenation hashed again;
                      key_encoder sha1|sha256|sha512|blake2b - the house default
                      is sha256, upstream still defaults sha1+warning), dedup in
                      order, then per batch: exists -> refresh vs write -> write
                      the vector store FIRST (pessimistic) -> update ALL records
                      (refresh timestamps) -> cleanup: incremental (stale keys of
                      the sources seen this batch, during the walk), full (keys
                      not seen this run, after it), scoped_full (full, scoped to
                      the sources this run touched); IndexingResult counts
                      num_added/num_updated/num_skipped/num_deleted
- TextSplitter      : the ABC - chunk_size/chunk_overlap (overlap must be <= size),
                      length_function, keep_separator bool|"start"|"end",
                      add_start_index, strip_whitespace; split_text abstract,
                      create_documents (the start_index offset math),
                      split_documents, _merge_splits (the overlap pop-loop,
                      ported exactly), transform_documents
- CharacterTextSplitter / RecursiveCharacterTextSplitter : the two house
                      splitters (the recursive walk picks the first separator
                      present, recurses with the rest, the "" terminal splits
                      per character; the lookaround guard never re-inserts a
                      zero-width separator)
- BaseRetriever     : the Runnable retriever - _get_relevant_documents abstract,
                      invoke/ainvoke emit the P2 "retriever" span (RUN_TYPES
                      pre-declared it in P2), batch/stream ride the Runnable ABC
- VectorStoreRetriever : search_type similarity|mmr (validated), search_kwargs
                      (k, fetch_k, filter, lambda_mult, score_threshold),
                      add_documents proxy, the store's retriever tags
- Docs7Retriever    : docs7 as a retriever source - the same gates (coder_docs7
                      flag, vault-as-cache) behind the same seam; the fetch is
                      injectable so tests stay zero-network, the real handler is
                      imported lazily inside the call (inertness); ok=False is
                      the honest empty list, the raw result stays on .last_result

INERTNESS LAW (re-proven): a fresh interpreter imports app.aep.retrieve with zero
threads, zero env reads, zero files created - sqlite opens only on first use, the
docs7 import is lazy, nothing executes unless called. Library module: no tools,
no routes, no flag - the registry keeps its count. Voice untouched by
construction; desktop untouched - server-only, old APKs keep working.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import math
import re
import sqlite3
import threading
import time
import uuid
import warnings
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable, Iterator, Literal, Sequence, TypedDict

from .runnable import RunnableConfig, RunnableSerializable, ensure_config
from pydantic import Field, PrivateAttr

# The P2 fire seam (the same shape as runnable._span_start) - None unless the
# config carries callbacks; the tracer import stays lazy.
def _span_start(cfg: dict, obj: Any, run_type: str, inputs: Any):
    if not cfg.get("callbacks"):
        return None
    from .tracers import Span
    return Span.start(cfg, obj, run_type, inputs)


# Magic namespace UUID for hashing - used to generate deterministic per-document
# UUIDs from hashing the content + metadata (upstream api.py:38 uses int=1984;
# the value is arbitrary but FIXED, so the same text hashes to the same id).
NAMESPACE_UUID = uuid.UUID(int=1984)

_HASH_ALGOS = ("sha1", "sha256", "sha512", "blake2b")


# ---------------------------------------------------------------------------
# the document (upstream documents.py)
# ---------------------------------------------------------------------------
class Document:
    """A piece of text with optional metadata (upstream documents.py:110).

    The unit that flows through the splitters, the vector stores, the index()
    dedup and the retrievers. `id` is optional - index() assigns hash ids when
    it is absent; add_documents generates uuid4s.
    """

    __slots__ = ("page_content", "metadata", "id")

    def __init__(self, page_content: str, metadata: dict[str, Any] | None = None,
                 id: str | None = None) -> None:  # noqa: A002 - the upstream name
        self.page_content = page_content
        self.metadata = metadata or {}
        self.id = id

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Document):
            return NotImplemented
        return (self.page_content == other.page_content
                and self.metadata == other.metadata and self.id == other.id)

    def __repr__(self) -> str:
        return (f"Document(page_content={self.page_content!r}, "
                f"metadata={self.metadata!r}, id={self.id!r})")

    def to_dict(self) -> dict[str, Any]:
        return {"page_content": self.page_content,
                "metadata": dict(self.metadata), "id": self.id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        return cls(page_content=data.get("page_content", ""),
                   metadata=data.get("metadata") or {},
                   id=data.get("id"))


# ---------------------------------------------------------------------------
# embeddings (upstream embeddings/embeddings.py + fake.py)
# ---------------------------------------------------------------------------
class Embeddings(ABC):
    """Interface for embedding models (upstream embeddings.py:8).

    embed_documents maps a list of texts to a list of vectors; embed_query maps
    ONE query text to ONE vector (usually identical work, but the two doors stay
    independent so a store can asymmetric-embed). The a-twins default to the
    sync methods via to_thread; native-async implementations may override.
    """

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self.embed_query, text)


class DeterministicEmbeddings(Embeddings):
    """The zero-network embedder: sha256-seeded unit vectors, stable across
    processes (upstream fake.py's DeterministicFakeEmbedding idea, numpy-free -
    the digest bytes of a re-hashed stream become the dims, L2-normalized so
    cosine similarity == plain dot product). Identical texts embed identically;
    different texts embed differently (the sha256 avalanche)."""

    def __init__(self, dim: int = 8, seed: str = "hoola") -> None:
        if dim <= 0:
            raise ValueError(f"dim must be a positive int, got {dim}")
        self.dim = int(dim)
        self.seed = seed

    def _unit(self, text: str) -> list[float]:
        raw: list[float] = []
        counter = 0
        while len(raw) < self.dim:
            digest = hashlib.sha256(
                f"{self.seed}:{text}:{counter}".encode("utf-8")).digest()
            for i in range(0, 32, 4):
                value = int.from_bytes(digest[i:i + 4], "big") / 0xFFFFFFFF
                raw.append(value * 2.0 - 1.0)
                if len(raw) == self.dim:
                    break
            counter += 1
        norm = math.sqrt(math.fsum(v * v for v in raw))
        if norm == 0.0:
            norm = 1.0
        return [v / norm for v in raw]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._unit(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._unit(text)


# ---------------------------------------------------------------------------
# cosine + MMR (pure python; upstream vectorstores/utils.py:112 numpy port)
# ---------------------------------------------------------------------------
def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(
            f"Vector dims differ: {len(a)} vs {len(b)} - one store, one embedder.")
    dot = math.fsum(x * y for x, y in zip(a, b))
    na = math.sqrt(math.fsum(x * x for x in a))
    nb = math.sqrt(math.fsum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def maximal_marginal_relevance(
    query_embedding: Sequence[float],
    embedding_list: Sequence[Sequence[float]],
    *,
    lambda_mult: float = 0.5,
    k: int = 4,
) -> list[int]:
    """MMR: greedy relevance/diversity balance (upstream utils.py:112).

    Picks the most query-similar embedding first, then each next one maximizes
    lambda_mult * sim_to_query - (1 - lambda_mult) * max_sim_to_selected.
    Returns the selected INDICES (the caller maps them to docs).
    """
    if min(k, len(embedding_list)) <= 0:
        return []
    sim_to_query = [_cosine(query_embedding, e) for e in embedding_list]
    most_similar = max(range(len(sim_to_query)), key=sim_to_query.__getitem__)
    idxs = [most_similar]
    selected: list[int] = [most_similar]
    while len(idxs) < min(k, len(embedding_list)):
        best_score = -math.inf
        idx_to_add = -1
        for i, query_score in enumerate(sim_to_query):
            if i in idxs:
                continue
            redundant = max(_cosine(embedding_list[i], embedding_list[j])
                            for j in selected)
            score = lambda_mult * query_score - (1 - lambda_mult) * redundant
            if score > best_score:
                best_score = score
                idx_to_add = i
        idxs.append(idx_to_add)
        selected.append(idx_to_add)
    return idxs


def _metadata_filter(doc: Document, filter: dict[str, Any] | None) -> bool:  # noqa: A002
    """The upstream in_memory filter contract: every key/value pair in `filter`
    must be present and equal in doc.metadata (no deep matching)."""
    if not filter:
        return True
    return all(doc.metadata.get(k) == v for k, v in filter.items())


# ---------------------------------------------------------------------------
# the vector store ABC (upstream vectorstores/base.py)
# ---------------------------------------------------------------------------
class VectorStore(ABC):
    """The vector store contract (upstream vectorstores/base.py:43).

    A subclass MUST implement similarity_search + from_texts; everything else
    has an honest default (add_texts/delete raise, with_score pairs 0.0, the
    a-twins ride to_thread). The relevance-score plumbing expects scores in
    [0, 1] after _select_relevance_score_fn maps the store's native metric.
    """

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: list[dict] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Default: refuse (upstream base.py:46). Subclasses embed + persist."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support add_texts - "
            "implement it or use add_documents with a store that does.")

    @property
    def embeddings(self) -> Embeddings | None:
        """The embedding model this store was built with (None is legal)."""
        return None

    def delete(self, ids: list[str] | None = None, **kwargs: Any) -> bool | None:
        """Delete by vector id (upstream base.py:108). Default: refuse."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support delete - index() "
            "cleanup modes need it.")

    def get_by_ids(self, ids: Sequence[str], /) -> list[Document]:
        """Fetch documents by id (upstream base.py:122). Default: none."""
        return []

    def add_documents(self, documents: list[Document], **kwargs: Any) -> list[str]:
        """Embed + persist Documents (upstream base.py:234). Ids ride the
        documents' .id when set, else uuid4; the generated ids are returned."""
        texts = [d.page_content for d in documents]
        metadatas = [d.metadata for d in documents]
        ids = kwargs.pop("ids", None)
        if ids is None:
            generated: list[str] = []
            for d in documents:
                if d.id is None:
                    d.id = str(uuid.uuid4())
                generated.append(d.id)
            ids = generated
        return self.add_texts(texts, metadatas=metadatas, ids=ids, **kwargs)

    async def aadd_documents(self, documents: list[Document],
                             **kwargs: Any) -> list[str]:
        return await asyncio.to_thread(self.add_documents, documents, **kwargs)

    def search(self, query: str, search_type: str, **kwargs: Any) -> list[Document]:
        """Dispatch by search_type (upstream base.py:293):
        similarity | similarity_score_threshold | mmr."""
        if search_type == "similarity":
            return self.similarity_search(query, **kwargs)
        if search_type == "similarity_score_threshold":
            docs_and_scores = self.similarity_search_with_relevance_scores(
                query, **kwargs)
            return [doc for doc, _ in docs_and_scores]
        if search_type == "mmr":
            return self.max_marginal_relevance_search(query, **kwargs)
        raise ValueError(
            f"search_type must be 'similarity', 'similarity_score_threshold' "
            f"or 'mmr', got {search_type!r}.")

    async def asearch(self, query: str, search_type: str,
                      **kwargs: Any) -> list[Document]:
        return await asyncio.to_thread(self.search, query, search_type, **kwargs)

    @abstractmethod
    def similarity_search(self, query: str, k: int = 4,
                          **kwargs: Any) -> list[Document]: ...

    # -- the relevance-score plumbing (upstream base.py:376-604) ------------
    @staticmethod
    def _euclidean_relevance_score_fn(distance: float) -> float:
        return 1.0 - distance / math.sqrt(2.0)

    @staticmethod
    def _cosine_relevance_score_fn(distance: float) -> float:
        return 1.0 - distance / 2.0

    @staticmethod
    def _max_inner_product_relevance_score_fn(distance: float) -> float:
        return (1.0 + distance) / 2.0

    def _select_relevance_score_fn(self) -> Callable[[float], float]:
        """The store's native metric -> [0, 1] relevance. Subclasses define it;
        the ABC refuses so an unconfigured store never invents scores."""
        raise NotImplementedError(
            f"{self.__class__.__name__} has not defined a relevance score "
            "function - similarity_search_with_relevance_scores is unavailable.")

    def similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        """Default: the ABC refuses (upstream base.py:417 raises; a store that
        only has similarity_search can port the (doc, 0.0) placeholder instead -
        the sqlite store implements this for real)."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support "
            "similarity_search_with_score.")

    async def asimilarity_search_with_score(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        return await asyncio.to_thread(
            self.similarity_search_with_score, query, k, **kwargs)

    def _similarity_search_with_relevance_scores(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        relevance_score_fn = self._select_relevance_score_fn()
        docs_and_scores = self.similarity_search_with_score(query, k, **kwargs)
        return [(doc, relevance_score_fn(score)) for doc, score in docs_and_scores]

    def similarity_search_with_relevance_scores(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        """Docs + relevance in [0, 1] (upstream base.py:506): the scores pass
        the relevance fn, out-of-range results warn, score_threshold filters
        (an empty after-filter result is an honest empty list, not an error)."""
        score_threshold = kwargs.pop("score_threshold", None)
        docs_and_similarities = self._similarity_search_with_relevance_scores(
            query, k=k, **kwargs)
        if any(sim < 0.0 or sim > 1.0 for _, sim in docs_and_similarities):
            warnings.warn(
                "Relevance scores must be between 0 and 1, got "
                f"{docs_and_similarities}", stacklevel=2)
        if score_threshold is not None:
            docs_and_similarities = [
                (doc, sim) for doc, sim in docs_and_similarities
                if sim >= score_threshold]
            if not docs_and_similarities:
                warnings.warn(
                    "No relevant docs were retrieved using the relevance "
                    f"score threshold {score_threshold}", stacklevel=2)
        return docs_and_similarities

    async def asimilarity_search_with_relevance_scores(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        return await asyncio.to_thread(
            self.similarity_search_with_relevance_scores, query, k, **kwargs)

    async def asimilarity_search(self, query: str, k: int = 4,
                                 **kwargs: Any) -> list[Document]:
        return await asyncio.to_thread(self.similarity_search, query, k, **kwargs)

    def similarity_search_by_vector(
        self, embedding: list[float], k: int = 4, **kwargs: Any
    ) -> list[Document]:
        """Search by a ready vector (skips embed_query). Default: refuse."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support "
            "similarity_search_by_vector.")

    async def asimilarity_search_by_vector(
        self, embedding: list[float], k: int = 4, **kwargs: Any
    ) -> list[Document]:
        return await asyncio.to_thread(
            self.similarity_search_by_vector, embedding, k, **kwargs)

    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20,
        lambda_mult: float = 0.5, **kwargs: Any,
    ) -> list[Document]:
        """MMR over fetch_k candidates, k returned. Default: embed the query
        and ride by_vector (upstream base.py:659)."""
        embedding_vector = self.embeddings.embed_query(query) \
            if self.embeddings is not None else None
        if embedding_vector is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} has no embeddings property and "
                "did not override max_marginal_relevance_search.")
        return self.max_marginal_relevance_search_by_vector(
            embedding_vector, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult,
            **kwargs)

    async def amax_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20,
        lambda_mult: float = 0.5, **kwargs: Any,
    ) -> list[Document]:
        return await asyncio.to_thread(
            self.max_marginal_relevance_search, query, k=k, fetch_k=fetch_k,
            lambda_mult=lambda_mult, **kwargs)

    def max_marginal_relevance_search_by_vector(
        self, embedding: list[float], k: int = 4, fetch_k: int = 20,
        lambda_mult: float = 0.5, **kwargs: Any,
    ) -> list[Document]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support "
            "max_marginal_relevance_search_by_vector.")

    async def amax_marginal_relevance_search_by_vector(
        self, embedding: list[float], k: int = 4, fetch_k: int = 20,
        lambda_mult: float = 0.5, **kwargs: Any,
    ) -> list[Document]:
        return await asyncio.to_thread(
            self.max_marginal_relevance_search_by_vector, embedding, k=k,
            fetch_k=fetch_k, lambda_mult=lambda_mult, **kwargs)

    @classmethod
    def from_documents(
        cls, documents: list[Document], embedding: Embeddings, **kwargs: Any,
    ) -> "VectorStore":
        """Build a store FROM documents (upstream base.py:787): construct with
        the embedding then add_documents. Needs the constructor to take
        embedding= (the sqlite store does)."""
        texts = [d.page_content for d in documents]
        metadatas = [d.metadata for d in documents]
        return cls.from_texts(texts, embedding, metadatas=metadatas, **kwargs)

    @classmethod
    async def afrom_documents(
        cls, documents: list[Document], embedding: Embeddings, **kwargs: Any,
    ) -> "VectorStore":
        return await asyncio.to_thread(
            cls.from_documents, documents, embedding, **kwargs)

    @classmethod
    @abstractmethod
    def from_texts(
        cls, texts: list[str], embedding: Embeddings,
        metadatas: list[dict] | None = None, **kwargs: Any,
    ) -> "VectorStore": ...

    @classmethod
    async def afrom_texts(
        cls, texts: list[str], embedding: Embeddings,
        metadatas: list[dict] | None = None, **kwargs: Any,
    ) -> "VectorStore":
        return await asyncio.to_thread(
            cls.from_texts, texts, embedding, metadatas=metadatas, **kwargs)

    def _get_retriever_tags(self) -> list[str]:
        """Tags the retriever carries into the run tree (upstream base.py:898)."""
        return [self.__class__.__name__]

    def as_retriever(self, **kwargs: Any) -> "VectorStoreRetriever":
        """This store as a Runnable retriever (upstream base.py:905):
        search_type ('similarity'|'mmr') + search_kwargs (k, fetch_k, filter,
        lambda_mult, score_threshold)."""
        search_type = kwargs.get("search_type", "similarity")
        search_kwargs = kwargs.get("search_kwargs") or {}
        tags = kwargs.get("tags")
        return VectorStoreRetriever(
            vectorstore=self, search_type=search_type,
            search_kwargs=dict(search_kwargs), tags=list(tags or []))


# ---------------------------------------------------------------------------
# the sqlite-first ANN (the house InMemoryVectorStore sibling; the P3
# SqliteSaver seam: a path OR the vault's sqlalchemy Engine, lazy raw_connection,
# table ensured on first use, thread-local connections on the path lane)
# ---------------------------------------------------------------------------
class SqliteVectorStore(VectorStore):
    """Vectors on stdlib sqlite3 (upstream vectorstores/in_memory.py's contract,
    persisted): one table aep_vectors(id TEXT PRIMARY KEY, doc TEXT, vec TEXT,
    ts REAL). doc is the Document JSON, vec the embedding JSON. Search is an
    exact cosine kNN scan (fetch all rows, score, sort, cut) with the upstream
    metadata-equality filter applied post-parse - the honest "ANN" first cut:
    the ANN substrate is the table + the index() dedup, an approximate index
    slots in behind the same ABC later. Exactly one of path= / engine=."""

    def __init__(self, embedding: Embeddings, *, path: str | None = None,
                 engine: Any = None) -> None:
        if embedding is None:
            raise ValueError("SqliteVectorStore needs an Embeddings model.")
        if (path is None) == (engine is None):
            raise ValueError(
                "SqliteVectorStore needs exactly one of path= / engine=")
        self.embedding = embedding
        self.path = path
        self.engine = engine
        self._local = threading.local()
        self._ensured = False   # per-instance: a class flag leaked across dbs
        if self.path:
            conn = self._conn()
            self._ensure(conn)

    @property
    def embeddings(self) -> Embeddings:
        return self.embedding

    # -- the connection seams (the SqliteSaver shape) ------------------------
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _ensure(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS aep_vectors ("
            "id TEXT PRIMARY KEY, doc TEXT NOT NULL, vec TEXT NOT NULL,"
            "ts REAL NOT NULL)")
        conn.commit()

    def _raw(self) -> tuple[Any, bool]:
        """(connection, borrowed) - the engine lane borrows a pooled
        raw_connection (ensured on first use), the path lane is thread-local."""
        if self.engine is not None:
            conn = self.engine.raw_connection()
            if not self._ensured:
                self._ensure(conn)
                self._ensured = True
            return conn, True
        return self._conn(), False

    # -- writes ---------------------------------------------------------------
    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: list[dict] | None = None,
        ids: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        texts = list(texts)
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError(
                f"metadatas ({len(metadatas)}) must match texts ({len(texts)}).")
        if ids is not None and len(ids) != len(texts):
            raise ValueError(
                f"ids ({len(ids)}) must match texts ({len(texts)}).")
        vectors = self.embedding.embed_documents(texts)
        if len(vectors) != len(texts):
            raise ValueError(
                f"embedder returned {len(vectors)} vectors for "
                f"{len(texts)} texts.")
        metadatas = metadatas or [{} for _ in texts]
        out_ids = list(ids) if ids is not None else [
            str(uuid.uuid4()) for _ in texts]
        now = time.time()
        conn, borrowed = self._raw()
        try:
            for doc_id, text, meta, vec in zip(out_ids, texts, metadatas, vectors):
                doc = Document(text, meta, doc_id)
                conn.execute(
                    "INSERT OR REPLACE INTO aep_vectors (id, doc, vec, ts)"
                    " VALUES (?, ?, ?, ?)",
                    (doc_id, json.dumps(doc.to_dict(), ensure_ascii=False),
                     json.dumps([float(v) for v in vec]), now))
            conn.commit()
        finally:
            if borrowed:
                conn.close()
        return out_ids

    def get_by_ids(self, ids: Sequence[str], /) -> list[Document]:
        conn, borrowed = self._raw()
        try:
            marks = ",".join("?" for _ in ids)
            rows = conn.execute(
                f"SELECT doc FROM aep_vectors WHERE id IN ({marks})",
                tuple(ids)).fetchall() if ids else []
        finally:
            if borrowed:
                conn.close()
        found: dict[str, Document] = {}
        for r in rows:
            d = json.loads(r[0])
            if d.get("id") is not None:
                found[d["id"]] = Document.from_dict(d)
        return [found[i] for i in ids if i in found]

    def delete(self, ids: list[str] | None = None, **kwargs: Any) -> bool | None:
        if ids is None:
            raise ValueError("SqliteVectorStore.delete needs ids.")
        conn, borrowed = self._raw()
        try:
            marks = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM aep_vectors WHERE id IN ({marks})",
                         tuple(ids))
            conn.commit()
        finally:
            if borrowed:
                conn.close()
        return True

    # -- reads ----------------------------------------------------------------
    def _rows(self, filter: dict[str, Any] | None) -> list[tuple[Document, list[float]]]:  # noqa: A002
        conn, borrowed = self._raw()
        try:
            rows = conn.execute("SELECT doc, vec FROM aep_vectors").fetchall()
        finally:
            if borrowed:
                conn.close()
        out: list[tuple[Document, list[float]]] = []
        for doc_json, vec_json in rows:
            doc = Document.from_dict(json.loads(doc_json))
            if not _metadata_filter(doc, filter):
                continue
            out.append((doc, json.loads(vec_json)))
        return out

    def _sim_scan(
        self, vector: list[float], k: int, filter: dict[str, Any] | None,  # noqa: A002
    ) -> list[tuple[Document, float]]:
        scored = [(doc, _cosine(vector, vec)) for doc, vec in self._rows(filter)]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:max(0, k)]

    def similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs: Any,
    ) -> list[tuple[Document, float]]:
        """(doc, cosine SIMILARITY) - higher is closer (the in_memory contract);
        use similarity_search_with_relevance_scores for the [0, 1] relevance."""
        return self._sim_scan(
            self.embedding.embed_query(query), k, kwargs.pop("filter", None))

    def similarity_search(self, query: str, k: int = 4,
                          **kwargs: Any) -> list[Document]:
        return [doc for doc, _ in self.similarity_search_with_score(
            query, k, **kwargs)]

    def similarity_search_by_vector(
        self, embedding: list[float], k: int = 4, **kwargs: Any,
    ) -> list[Document]:
        return [doc for doc, _ in self._sim_scan(
            embedding, k, kwargs.pop("filter", None))]

    def max_marginal_relevance_search_by_vector(
        self, embedding: list[float], k: int = 4, fetch_k: int = 20,
        lambda_mult: float = 0.5, **kwargs: Any,
    ) -> list[Document]:
        rows = self._rows(kwargs.pop("filter", None))
        scored = [(doc, _cosine(embedding, vec), vec) for doc, vec in rows]
        scored.sort(key=lambda t: t[1], reverse=True)
        candidates = scored[:max(0, fetch_k)]
        if not candidates:
            return []
        idxs = maximal_marginal_relevance(
            embedding, [vec for _, _, vec in candidates],
            lambda_mult=lambda_mult, k=k)
        return [candidates[i][0] for i in idxs]

    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20,
        lambda_mult: float = 0.5, **kwargs: Any,
    ) -> list[Document]:
        return self.max_marginal_relevance_search_by_vector(
            self.embedding.embed_query(query), k=k, fetch_k=fetch_k,
            lambda_mult=lambda_mult, **kwargs)

    def _select_relevance_score_fn(self) -> Callable[[float], float]:
        # with_score returns cosine SIMILARITY already in [-1, 1]; relevance
        # clamps into [0, 1] (orthogonal -> 0, identical -> 1, opposed -> 0).
        return lambda sim: max(0.0, min(1.0, sim))

    @classmethod
    def from_texts(
        cls, texts: list[str], embedding: Embeddings,
        metadatas: list[dict] | None = None, ids: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> "SqliteVectorStore":
        store = cls(embedding, path=kwargs.pop("path", None),
                    engine=kwargs.pop("engine", None))
        store.add_texts(texts, metadatas=metadatas, ids=ids, **kwargs)
        return store


# ---------------------------------------------------------------------------
# the indexing ledger (upstream indexing/base.py RecordManager + in-memory
# sqlite house twin)
# ---------------------------------------------------------------------------
class RecordManager(ABC):
    """The timestamped ledger index() dedups against (upstream base.py:22).

    Tracks which doc hashes were written into a vector store, when, and under
    which source group - so index() can skip unchanged docs, refresh touched
    ones, and delete the stale ones. Constraints carried over from upstream:
    timestamps must be monotonic (get_time comes from the SERVER, here
    time.time()), and the ledger is separate from the store (the index()
    ordering - store write first, ledger update second - is the mitigation).

    The a-twins default to the sync methods via to_thread.
    """

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace

    @abstractmethod
    def create_schema(self) -> None: ...

    @abstractmethod
    def get_time(self) -> float: ...

    @abstractmethod
    def update(
        self,
        keys: Sequence[str],
        *,
        group_ids: Sequence[str | None] | None = None,
        time_at_least: float | None = None,
    ) -> None: ...

    @abstractmethod
    def exists(self, keys: Sequence[str]) -> list[bool]: ...

    @abstractmethod
    def list_keys(
        self,
        *,
        before: float | None = None,
        after: float | None = None,
        group_ids: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> list[str]: ...

    @abstractmethod
    def delete_keys(self, keys: Sequence[str]) -> None: ...

    async def acreate_schema(self) -> None:
        return await asyncio.to_thread(self.create_schema)

    async def aget_time(self) -> float:
        return await asyncio.to_thread(self.get_time)

    async def aupdate(
        self, keys: Sequence[str], *,
        group_ids: Sequence[str | None] | None = None,
        time_at_least: float | None = None,
    ) -> None:
        return await asyncio.to_thread(
            self.update, keys, group_ids=group_ids, time_at_least=time_at_least)

    async def aexists(self, keys: Sequence[str]) -> list[bool]:
        return await asyncio.to_thread(self.exists, keys)

    async def alist_keys(
        self, *, before: float | None = None, after: float | None = None,
        group_ids: Sequence[str] | None = None, limit: int | None = None,
    ) -> list[str]:
        return await asyncio.to_thread(
            self.list_keys, before=before, after=after,
            group_ids=group_ids, limit=limit)

    async def adelete_keys(self, keys: Sequence[str]) -> None:
        return await asyncio.to_thread(self.delete_keys, keys)


class SqliteRecordManager(RecordManager):
    """The ledger on stdlib sqlite3 - one table aep_index_records(uuid TEXT
    PRIMARY KEY, updated_at REAL NOT NULL, group_id TEXT). Exactly one of
    path= / engine= (the vault's sqlalchemy Engine rides raw_connection, the
    P3 SqliteSaver seam); the schema ensures on construction (the path lane)
    or first use (the engine lane)."""

    def __init__(self, namespace: str, *, path: str | None = None,
                 engine: Any = None) -> None:
        super().__init__(namespace)
        if (path is None) == (engine is None):
            raise ValueError(
                "SqliteRecordManager needs exactly one of path= / engine=")
        self.path = path
        self.engine = engine
        self._local = threading.local()
        self._ensured = False
        self.create_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _raw(self) -> tuple[Any, bool]:
        if self.engine is not None:
            conn = self.engine.raw_connection()
            if not self._ensured:
                self._ensure(conn)
                self._ensured = True
            return conn, True
        return self._conn(), False

    def _ensure(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS aep_index_records ("
            "uuid TEXT PRIMARY KEY, updated_at REAL NOT NULL, group_id TEXT)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_aep_rec_updated"
            " ON aep_index_records (updated_at)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_aep_rec_group"
            " ON aep_index_records (group_id)")
        conn.commit()

    def create_schema(self) -> None:
        if self.path:
            self._ensure(self._conn())
        # the engine lane ensures lazily (a raw_connection is not held open)

    def get_time(self) -> float:
        return time.time()

    def update(
        self, keys: Sequence[str], *,
        group_ids: Sequence[str | None] | None = None,
        time_at_least: float | None = None,
    ) -> None:
        if group_ids is not None and len(group_ids) != len(keys):
            raise ValueError(
                f"group_ids ({len(group_ids)}) must match keys ({len(keys)}), "
                "or be None.")
        now = time.time()
        if time_at_least is not None and now < time_at_least:
            raise ValueError(
                "The ledger clock drifted behind time_at_least - "
                f"{now} < {time_at_least}; refusing the upsert (the monotonic "
                "timestamps law).")
        groups = list(group_ids) if group_ids is not None else [None] * len(keys)
        conn, borrowed = self._raw()
        try:
            for key, group in zip(keys, groups):
                conn.execute(
                    "INSERT OR REPLACE INTO aep_index_records"
                    " (uuid, updated_at, group_id) VALUES (?, ?, ?)",
                    (key, now, group))
            conn.commit()
        finally:
            if borrowed:
                conn.close()

    def exists(self, keys: Sequence[str]) -> list[bool]:
        found: set[str] = set()
        conn, borrowed = self._raw()
        try:
            # chunked IN clauses (sqlite's 999-variable ceiling)
            chunk = 900
            for i in range(0, len(keys), chunk):
                part = list(keys[i:i + chunk])
                marks = ",".join("?" for _ in part)
                rows = conn.execute(
                    f"SELECT uuid FROM aep_index_records WHERE uuid IN ({marks})",
                    tuple(part)).fetchall()
                found.update(r[0] for r in rows)
        finally:
            if borrowed:
                conn.close()
        return [k in found for k in keys]

    def list_keys(
        self, *, before: float | None = None, after: float | None = None,
        group_ids: Sequence[str] | None = None, limit: int | None = None,
    ) -> list[str]:
        where: list[str] = []
        params: list[Any] = []
        if before is not None:
            where.append("updated_at < ?")
            params.append(float(before))
        if after is not None:
            where.append("updated_at > ?")
            params.append(float(after))
        if group_ids is not None:
            marks = ",".join("?" for _ in group_ids)
            where.append(f"group_id IN ({marks})")
            params.extend(group_ids)
        sql = "SELECT uuid FROM aep_index_records"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        conn, borrowed = self._raw()
        try:
            rows = conn.execute(sql, tuple(params)).fetchall()
        finally:
            if borrowed:
                conn.close()
        return [r[0] for r in rows]

    def delete_keys(self, keys: Sequence[str]) -> None:
        if not keys:
            return
        conn, borrowed = self._raw()
        try:
            marks = ",".join("?" for _ in keys)
            conn.execute(
                f"DELETE FROM aep_index_records WHERE uuid IN ({marks})",
                tuple(keys))
            conn.commit()
        finally:
            if borrowed:
                conn.close()


# ---------------------------------------------------------------------------
# index() - the dedup flow (upstream indexing/api.py)
# ---------------------------------------------------------------------------
class IndexingException(Exception):
    """Raised when an indexing operation fails (upstream api.py:153)."""


class IndexingResult(TypedDict):
    """The index() breakdown (upstream api.py:283)."""
    num_added: int
    num_updated: int
    num_deleted: int
    num_skipped: int


def _calculate_hash(text: str, algorithm: str) -> str:
    if algorithm == "sha1":
        # the upstream legacy shape: uuid5 over the sha1 hex digest
        digest = hashlib.sha1(
            text.encode("utf-8"), usedforsecurity=False).hexdigest()
        return str(uuid.uuid5(NAMESPACE_UUID, digest))
    if algorithm == "blake2b":
        return hashlib.blake2b(text.encode("utf-8")).hexdigest()
    if algorithm == "sha256":
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    if algorithm == "sha512":
        return hashlib.sha512(text.encode("utf-8")).hexdigest()
    raise ValueError(
        f"Unsupported hashing algorithm: {algorithm} - "
        f"expected one of {_HASH_ALGOS} or a callable key_encoder.")


def _hash_document(
    document: Document, key_encoder: str | Callable[[Document], str],
) -> Document:
    """Hash content and metadata SEPARATELY, then the concatenation (upstream
    api.py:175) - so a metadata-only edit rehashes, and a same-content
    different-metadata pair stays distinct."""
    if callable(key_encoder):
        hash_ = key_encoder(document)
    else:
        content_hash = _calculate_hash(document.page_content, key_encoder)
        try:
            serialized_meta = json.dumps(document.metadata or {}, sort_keys=True)
        except Exception as e:
            raise ValueError(
                f"Failed to hash metadata: {e}. Use json-serializable "
                "metadata.") from e
        metadata_hash = _calculate_hash(serialized_meta, key_encoder)
        hash_ = _calculate_hash(content_hash + metadata_hash, key_encoder)
    return Document(document.page_content, document.metadata, hash_)


def _dedup_in_order(docs: Iterable[Document]) -> Iterator[Document]:
    """First occurrence wins, order preserved (upstream api.py:139)."""
    seen: set[str] = set()
    for doc in docs:
        if doc.id not in seen:
            seen.add(doc.id)  # type: ignore[arg-type]
            yield doc


def _batch(size: int, items: Iterable[Any]) -> Iterator[list[Any]]:
    if size <= 0:
        raise ValueError(f"Batch size must be a positive integer, got {size}.")
    it = iter(items)
    while True:
        chunk = []
        for _ in range(size):
            try:
                chunk.append(next(it))
            except StopIteration:
                break
        if not chunk:
            return
        yield chunk


def _source_id_assigner(
    source_id_key: str | Callable[[Document], str] | None,
) -> Callable[[Document], Any]:
    if source_id_key is None:
        return lambda _doc: None
    if isinstance(source_id_key, str):
        # .get: a missing metadata key becomes the friendly "not assigned a
        # source id" refusal inside index(), never a raw KeyError
        return lambda doc: doc.metadata.get(source_id_key)
    if callable(source_id_key):
        return source_id_key
    raise ValueError(
        "source_id_key should be None, a string or a callable - "
        f"got {source_id_key!r}.")


def _index_delete(destination: VectorStore, ids: list[str]) -> None:
    delete_ok = destination.delete(ids)
    if delete_ok is not None and delete_ok is False:
        raise IndexingException("The delete operation to VectorStore failed.")


def _index_require_store(destination: VectorStore) -> None:
    """index() needs a store that can add AND delete (upstream api.py:427)."""
    if not isinstance(destination, VectorStore):
        raise TypeError(
            "vector_store should be a VectorStore - "
            f"got {type(destination).__name__}.")
    if type(destination).delete == VectorStore.delete:
        raise ValueError(
            f"Vectorstore {destination.__class__.__name__} has not implemented "
            "the delete method - index() cleanup needs it.")


def index(
    docs_source: Iterable[Document],
    record_manager: RecordManager,
    vector_store: VectorStore,
    *,
    batch_size: int = 100,
    cleanup: Literal["incremental", "full", "scoped_full"] | None = None,
    source_id_key: str | Callable[[Document], str] | None = None,
    cleanup_batch_size: int = 1_000,
    force_update: bool = False,
    key_encoder: str | Callable[[Document], str] = "sha256",
    upsert_kwargs: dict[str, Any] | None = None,
) -> IndexingResult:
    """Index documents into the store, deduped by content+metadata hash
    (upstream api.py:296, the house default key_encoder is sha256 - upstream
    still defaults sha1 + a collision warning).

    Per batch: hash + in-order dedup -> exists? -> refresh (skip + timestamp)
    vs write -> the STORE write first, the LEDGER update second (pessimistic:
    a lost ledger row re-indexes, a lost store row never lies in the ledger) ->
    cleanup. cleanup modes:
      - None        : never delete (the ledger still tracks)
      - incremental : after each batch, delete this batch's SOURCES' keys that
                      predate this run (requires source_id_key)
      - full        : after ALL batches, delete every key this run did not see
                      (the loader must return the WHOLE dataset)
      - scoped_full : full, scoped to only the sources this run touched
    """
    if cleanup in ("incremental", "scoped_full") and source_id_key is None:
        raise ValueError(
            "source_id_key is required when cleanup mode is incremental "
            "or scoped_full.")
    _index_require_store(vector_store)
    source_id_assigner = _source_id_assigner(source_id_key)

    index_start_dt = record_manager.get_time()
    num_added = num_skipped = num_updated = num_deleted = 0
    scoped_full_sources: set[str] = set()

    for doc_batch in _batch(batch_size, docs_source):
        original_batch_size = len(doc_batch)
        hashed_docs = list(_dedup_in_order(
            _hash_document(doc, key_encoder) for doc in doc_batch))
        num_skipped += original_batch_size - len(hashed_docs)

        source_ids: list[str | None] = [
            source_id_assigner(doc) for doc in hashed_docs]

        if cleanup in ("incremental", "scoped_full"):
            for source_id, hashed_doc in zip(source_ids, hashed_docs):
                if source_id is None:
                    raise ValueError(
                        "Source IDs are required when cleanup mode is "
                        "incremental or scoped_full. Document starting with "
                        f"content: {hashed_doc.page_content[:100]!r} was not "
                        "assigned a source id.")
                if cleanup == "scoped_full":
                    scoped_full_sources.add(source_id)
            source_ids_clean: Sequence[str | None] = source_ids
        else:
            source_ids_clean = source_ids

        exists_batch = record_manager.exists([doc.id for doc in hashed_docs])

        uids: list[str] = []
        docs_to_index: list[Document] = []
        uids_to_refresh: list[str] = []
        seen_docs: set[str] = set()
        for hashed_doc, doc_exists in zip(hashed_docs, exists_batch):
            hashed_id = hashed_doc.id or ""
            if doc_exists:
                if force_update:
                    seen_docs.add(hashed_id)
                else:
                    uids_to_refresh.append(hashed_id)
                    continue
            uids.append(hashed_id)
            docs_to_index.append(hashed_doc)

        if uids_to_refresh:
            record_manager.update(uids_to_refresh, time_at_least=index_start_dt)
            num_skipped += len(uids_to_refresh)

        # the store write FIRST, the ledger update SECOND (pessimistic)
        if docs_to_index:
            vector_store.add_documents(
                docs_to_index, ids=uids, **(upsert_kwargs or {}))
            num_added += len(docs_to_index) - len(seen_docs)
            num_updated += len(seen_docs)

        record_manager.update(
            [doc.id for doc in hashed_docs],
            group_ids=source_ids_clean, time_at_least=index_start_dt)

        if cleanup == "incremental":
            while uids_to_delete := record_manager.list_keys(
                    group_ids=[sid for sid in source_ids_clean if sid is not None],
                    before=index_start_dt, limit=cleanup_batch_size):
                _index_delete(vector_store, uids_to_delete)
                record_manager.delete_keys(uids_to_delete)
                num_deleted += len(uids_to_delete)

    if cleanup == "full" or (
            cleanup == "scoped_full" and scoped_full_sources):
        delete_group_ids: Sequence[str] | None = None
        if cleanup == "scoped_full":
            delete_group_ids = list(scoped_full_sources)
        while uids_to_delete := record_manager.list_keys(
                group_ids=delete_group_ids, before=index_start_dt,
                limit=cleanup_batch_size):
            _index_delete(vector_store, uids_to_delete)
            record_manager.delete_keys(uids_to_delete)
            num_deleted += len(uids_to_delete)

    return {"num_added": num_added, "num_updated": num_updated,
            "num_skipped": num_skipped, "num_deleted": num_deleted}


async def aindex(
    docs_source: Iterable[Document],
    record_manager: RecordManager,
    vector_store: VectorStore,
    *,
    batch_size: int = 100,
    cleanup: Literal["incremental", "full", "scoped_full"] | None = None,
    source_id_key: str | Callable[[Document], str] | None = None,
    cleanup_batch_size: int = 1_000,
    force_update: bool = False,
    key_encoder: str | Callable[[Document], str] = "sha256",
    upsert_kwargs: dict[str, Any] | None = None,
) -> IndexingResult:
    """The async twin - the dedup flow itself rides to_thread (one honest
    lane; the sqlite scan is CPU-bound python, a fake async would hide it)."""
    return await asyncio.to_thread(
        index, docs_source, record_manager, vector_store,
        batch_size=batch_size, cleanup=cleanup,
        source_id_key=source_id_key, cleanup_batch_size=cleanup_batch_size,
        force_update=force_update, key_encoder=key_encoder,
        upsert_kwargs=upsert_kwargs)


# ---------------------------------------------------------------------------
# the text splitters (upstream libs/text-splitters base.py + character.py)
# ---------------------------------------------------------------------------
def _split_text_with_regex(
    text: str, separator: str, *, keep_separator: bool | Literal["start", "end"],
) -> list[str]:
    """Split keeping the delimiter in the result when asked (upstream
    character.py:64) - the parentheses in the pattern keep the delimiters;
    'start' attaches them to the following chunk, 'end'/True to the preceding."""
    if separator:
        if keep_separator:
            splits_ = re.split(f"({separator})", text)
            splits = (
                [splits_[i] + splits_[i + 1] for i in range(0, len(splits_) - 1, 2)]
                if keep_separator == "end"
                else [splits_[i] + splits_[i + 1] for i in range(1, len(splits_), 2)]
            )
            if len(splits_) % 2 == 0:
                splits += splits_[-1:]
            splits = (
                [*splits, splits_[-1]]
                if keep_separator == "end"
                else [splits_[0], *splits]
            )
        else:
            splits = re.split(separator, text)
    else:
        splits = list(text)
    return [s for s in splits if s]


class TextSplitter(ABC):
    """The splitter contract (upstream base.py:59): split_text into chunks of
    at most chunk_size length-function units, overlap chunk_overlap, merges
    with the separator. create_documents/split_documents turn texts or
    Documents into chunk Documents (add_start_index stamps each chunk's
    character offset in its source text into the metadata)."""

    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Callable[[str], int] = len,
        keep_separator: bool | Literal["start", "end"] = False,
        add_start_index: bool = False,
        strip_whitespace: bool = True,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}.")
        if chunk_overlap < 0:
            raise ValueError(
                f"chunk_overlap must be non-negative, got {chunk_overlap}.")
        if chunk_overlap > chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) may not exceed chunk_size "
                f"({chunk_size}).")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function
        self._keep_separator = keep_separator
        self._add_start_index = add_start_index
        self._strip_whitespace = strip_whitespace

    @abstractmethod
    def split_text(self, text: str) -> list[str]: ...

    def create_documents(
        self, texts: list[str], metadatas: list[dict] | None = None,
    ) -> list[Document]:
        """Split texts into Documents (upstream base.py:118); the metadata is
        deep-copied per chunk so no chunk edits leak into a sibling."""
        metadatas_ = metadatas or [{}] * len(texts)
        if len(metadatas_) != len(texts):
            raise ValueError(
                f"metadatas ({len(metadatas_)}) must match texts ({len(texts)}).")
        documents: list[Document] = []
        for i, text in enumerate(texts):
            index = 0
            previous_chunk_len = 0
            for chunk in self.split_text(text):
                metadata = copy.deepcopy(metadatas_[i])
                if self._add_start_index:
                    offset = index + previous_chunk_len - self._chunk_overlap
                    index = text.find(chunk, max(0, offset))
                    metadata["start_index"] = index
                    previous_chunk_len = len(chunk)
                documents.append(Document(chunk, metadata))
        return documents

    def split_documents(self, documents: Iterable[Document]) -> list[Document]:
        """Split Documents, metadata carried through (upstream base.py:146)."""
        texts, metadatas = [], []
        for doc in documents:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata)
        return self.create_documents(texts, metadatas=metadatas)

    def transform_documents(
        self, documents: Sequence[Document], **kwargs: Any,
    ) -> Sequence[Document]:
        """The BaseDocumentTransformer lane (upstream base.py:311)."""
        return self.split_documents(documents)

    def _join_docs(self, docs: list[str], separator: str) -> str | None:
        text = separator.join(docs)
        if self._strip_whitespace:
            text = text.strip()
        return text or None

    def _merge_splits(self, splits: Iterable[str], separator: str) -> list[str]:
        """The overlap merge (upstream base.py:167, ported exactly): accumulate
        splits while they fit; on overflow flush the chunk then POP from the
        front until the remainder fits inside the overlap budget (or the next
        split can finally fit) - the sliding-window law."""
        separator_len = self._length_function(separator)
        docs: list[str] = []
        current_doc: list[str] = []
        total = 0
        for d in splits:
            len_ = self._length_function(d)
            if (total + len_ + (separator_len if len(current_doc) > 0 else 0)
                    > self._chunk_size):
                if total > self._chunk_size:
                    warnings.warn(
                        f"Created a chunk of size {total}, which is longer "
                        f"than the specified {self._chunk_size}", stacklevel=2)
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    while total > self._chunk_overlap or (
                            total + len_
                            + (separator_len if len(current_doc) > 0 else 0)
                            > self._chunk_size and total > 0):
                        total -= self._length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0)
                        current_doc = current_doc[1:]
            current_doc.append(d)
            total += len_ + (separator_len if len(current_doc) > 1 else 0)
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        return docs


class CharacterTextSplitter(TextSplitter):
    """Split on one separator (default the blank line), then merge to size
    (upstream character.py:13)."""

    def __init__(
        self,
        separator: str = "\n\n",
        is_separator_regex: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._separator = separator
        self._is_separator_regex = is_separator_regex

    def split_text(self, text: str) -> list[str]:
        sep_pattern = (
            self._separator
            if self._is_separator_regex else re.escape(self._separator))
        splits = _split_text_with_regex(
            text, sep_pattern, keep_separator=self._keep_separator)
        # a zero-width lookaround separator is never re-inserted (the upstream
        # lookaround guard - re-joining would corrupt the chunks)
        lookaround_prefixes = ("(?=", "(?<!", "(?<=", "(?!")
        is_lookaround = self._is_separator_regex and any(
            self._separator.startswith(p) for p in lookaround_prefixes)
        merge_sep = ""
        if not (self._keep_separator or is_lookaround):
            merge_sep = self._separator
        return self._merge_splits(splits, merge_sep)


class RecursiveCharacterTextSplitter(TextSplitter):
    """Split recursively down the separator ladder [\n\n, \n, ' ', ''] (upstream
    character.py:91): the first separator PRESENT in the text splits it; any
    piece still over chunk_size recurses with the REMAINING separators; the ""
    terminal splits per character. keep_separator defaults True here."""

    def __init__(
        self,
        separators: list[str] | None = None,
        keep_separator: bool | Literal["start", "end"] = True,
        is_separator_regex: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or ["\n\n", "\n", " ", ""]
        self._is_separator_regex = is_separator_regex

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        final_chunks: list[str] = []
        separator = separators[-1]
        new_separators: list[str] = []
        for i, s_ in enumerate(separators):
            separator_ = s_ if self._is_separator_regex else re.escape(s_)
            if not s_:
                separator = s_
                break
            if re.search(separator_, text):
                separator = s_
                new_separators = separators[i + 1:]
                break
        separator_ = separator if self._is_separator_regex else re.escape(separator)
        splits = _split_text_with_regex(
            text, separator_, keep_separator=self._keep_separator)
        good_splits: list[str] = []
        separator_ = "" if self._keep_separator else separator
        for s in splits:
            if self._length_function(s) < self._chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged_text = self._merge_splits(good_splits, separator_)
                    final_chunks.extend(merged_text)
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    other_info = self._split_text(s, new_separators)
                    final_chunks.extend(other_info)
        if good_splits:
            merged_text = self._merge_splits(good_splits, separator_)
            final_chunks.extend(merged_text)
        return final_chunks

    def split_text(self, text: str) -> list[str]:
        return self._split_text(text, self._separators)


# ---------------------------------------------------------------------------
# the retrievers (upstream retrievers.py + vectorstores/base.py:964)
# ---------------------------------------------------------------------------
class BaseRetriever(RunnableSerializable):
    """The document retrieval Runnable (upstream retrievers.py:55): a str in,
    a list[Document] out, the P2 "retriever" span fired on every invoke
    (RUN_TYPES pre-declared the run type in P2). Subclasses implement
    _get_relevant_documents; the a-twin defaults to to_thread."""

    tags: list[str] = Field(default_factory=list)

    def invoke(  # noqa: A002,A003
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any,
    ) -> list[Document]:
        cfg = ensure_config(config)
        span = _span_start(cfg, self, "retriever", input)
        try:
            docs = self._get_relevant_documents(input, **kwargs)
        except Exception as e:  # noqa: BLE001
            if span is not None:
                span.error(e)
            raise
        if span is not None:
            # the run tree carries the documents JSON-shaped (the tracer's
            # _plain never sees a bare object)
            span.end([d.to_dict() for d in docs])
        return docs

    async def ainvoke(  # noqa: A002,A003
        self, input: str, config: RunnableConfig | None = None, **kwargs: Any,
    ) -> list[Document]:
        return await asyncio.to_thread(self.invoke, input, config, **kwargs)

    @abstractmethod
    def _get_relevant_documents(
        self, query: str, *, run_manager: Any = None,
    ) -> list[Document]: ...

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: Any = None,
    ) -> list[Document]:
        return await asyncio.to_thread(self._get_relevant_documents, query)


class VectorStoreRetriever(BaseRetriever):
    """A VectorStore as a retriever (upstream base.py:964): search_type
    'similarity' rides similarity_search, 'mmr' rides
    max_marginal_relevance_search; search_kwargs (k, fetch_k, filter,
    lambda_mult, score_threshold) ride every call. add_documents proxies the
    store (the ingestion door stays open on the retriever)."""

    vectorstore: Any
    search_type: str = "similarity"
    search_kwargs: dict[str, Any] = Field(default_factory=dict)

    def __init__(
        self,
        vectorstore: VectorStore,
        search_type: str = "similarity",
        search_kwargs: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        if search_type not in ("similarity", "mmr"):
            raise ValueError(
                f"search_type must be 'similarity' or 'mmr', got {search_type!r}.")
        merged_tags = list(tags or []) + vectorstore._get_retriever_tags()
        super().__init__(
            vectorstore=vectorstore, search_type=search_type,
            search_kwargs=dict(search_kwargs or {}), tags=merged_tags)

    def get_name(self, suffix: str | None = None) -> str:
        base = self.__class__.__name__
        return f"{base}.{self.search_type}" if suffix is None else f"{base}{suffix}"

    def _get_relevant_documents(
        self, query: str, *, run_manager: Any = None,
    ) -> list[Document]:
        if self.search_type == "similarity":
            return self.vectorstore.similarity_search(query, **self.search_kwargs)
        return self.vectorstore.max_marginal_relevance_search(
            query, **self.search_kwargs)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: Any = None,
    ) -> list[Document]:
        return await asyncio.to_thread(self._get_relevant_documents, query)

    def add_documents(self, documents: list[Document], **kwargs: Any) -> list[str]:
        return self.vectorstore.add_documents(documents, **kwargs)

    async def aadd_documents(
        self, documents: list[Document], **kwargs: Any,
    ) -> list[str]:
        return await self.vectorstore.aadd_documents(documents, **kwargs)


class Docs7Retriever(BaseRetriever):
    """docs7 as a retriever source - the house library-docs door behind the
    retriever seam. The fetch is injectable (tests stay zero-network); the
    default lazily imports the real coder.docs7 handler (inertness) and runs
    it with a shim ctx - the same coder_docs7 flag, redaction, courtesy
    window and vault-as-cache gates apply, unchanged. ok=False (flag off,
    window full, unreachable) is the honest EMPTY list - the raw result stays
    on .last_result for the caller to inspect."""

    library_id: str
    language: str | None = None
    tenant_id: str = "-"
    conversation_id: str = ""

    _fetch: Any = PrivateAttr(default=None)
    _last_result: dict[str, Any] | None = PrivateAttr(default=None)

    def __init__(
        self,
        library_id: str,
        *,
        language: str | None = None,
        tenant_id: str = "-",
        conversation_id: str = "",
        tags: list[str] | None = None,
        fetch: Callable[..., Any] | None = None,
    ) -> None:
        if not library_id or not str(library_id).startswith("/"):
            raise ValueError(
                "Docs7Retriever needs a Context7 library ID in the /org/project "
                "form - the docs7 gate refuses anything else.")
        super().__init__(
            library_id=library_id, language=language, tenant_id=tenant_id,
            conversation_id=conversation_id,
            tags=list(tags or []) + ["Docs7Retriever"])
        self._fetch = fetch

    @property
    def last_result(self) -> dict[str, Any] | None:
        return self._last_result

    def _default_fetch(self, query: str) -> dict[str, Any]:
        """The real docs7 handler, imported lazily inside the call (the
        inertness law). asyncio.run is safe here: invoke() arrives either
        without a loop or inside to_thread's worker (ainvoke)."""
        import asyncio as _asyncio
        from types import SimpleNamespace
        from ..coder.docs7 import docs7 as docs7_handler
        ctx = SimpleNamespace(
            tenant_id=self.tenant_id, conversation_id=self.conversation_id)
        return _asyncio.run(docs7_handler(
            ctx, op="query", query=query, library_id=self.library_id,
            language=self.language))

    def _get_relevant_documents(
        self, query: str, *, run_manager: Any = None,
    ) -> list[Document]:
        fetch = self._fetch if self._fetch is not None else self._default_fetch
        result = fetch(query)
        self._last_result = result
        if not isinstance(result, dict) or not result.get("ok"):
            return []
        text = str(result.get("text") or "")
        if not text:
            return []
        metadata = {
            "source": "docs7",
            "library_id": result.get("library_id") or self.library_id,
            "cached": bool(result.get("cached")),
        }
        return [Document(text, metadata)]


__all__ = [
    # documents + embeddings
    "Document", "Embeddings", "DeterministicEmbeddings",
    # the math
    "maximal_marginal_relevance",
    # the stores
    "VectorStore", "SqliteVectorStore",
    # the indexing ledger + the dedup flow
    "RecordManager", "SqliteRecordManager", "IndexingException",
    "IndexingResult", "index", "aindex",
    # the splitters
    "TextSplitter", "CharacterTextSplitter", "RecursiveCharacterTextSplitter",
    # the retrievers
    "BaseRetriever", "VectorStoreRetriever", "Docs7Retriever",
]

