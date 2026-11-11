"""v0.570.0 HOOLA RETRIEVE - the retrieval layer, P6 of the AEP plan (the name
keeps the first-build number, the v0.566 middleware precedent).

The langchain retrieval FEATURE SURFACE hand-built as app/aep/retrieve.py after the
upstream re-read at the pinned commit aa2528fb (vectorstores/base.py 1111 lines +
in_memory.py + utils.py MMR, embeddings/ 78+129, indexing/ base 661 + api 954,
retrievers.py 328, text-splitters base.py + character.py) - ZERO upstream code.

What is tested FOR REAL (all offline, tmp sqlite files wiped per test): the
Document round trip; DeterministicEmbeddings (determinism, unit norm, the dim
gate); the VectorStore ABC's honest defaults + the search dispatch + the
relevance-score [0,1] contract with score_threshold; the sqlite-first ANN
(add/get/delete, the kNN scan, the metadata filter, MMR, the path/engine gate,
persistence across instances); RecordManager + SqliteRecordManager (the ledger
shape, group_ids alignment, the time_at_least monotonic gate, list_keys filters);
index()/aindex() (first index, the no-op re-index, changed content -> update +
stale delete, incremental/full/scoped_full cleanup, the source-id gates, the
delete-override gate, the batch gate, force_update, the key encoders); the text
splitters (the recursive ladder, the overlap pop-loop, create_documents +
add_start_index + the metadata deep-copy, the split gates, the lookaround guard);
the retrievers (VectorStoreRetriever similarity + mmr + search_type validation +
the add_documents proxy, the P2 "retriever" span in the run tree, the a-twins);
Docs7Retriever (the library-id gate, the injected fetch, the ok=False empty list,
last_result); the inertness probe (fresh import: zero threads, zero files) + the
package-export law + the APP_VERSION/pubspec pins.
"""
import asyncio
import os
import shutil
import tempfile
import threading

import pytest

from app.aep import retrieve as R
from app.aep import *  # noqa: F401,F403 - the package-export law probe
import app.aep as _pkg  # noqa: F401 - the export law names live on the package
from app.aep.tracers import CallbackManager, InMemoryRunStore, RunTreeTracer


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_db():
    d = tempfile.mkdtemp(prefix="hoola-p6-")
    yield os.path.join(d, "vectors.db"), d
    shutil.rmtree(d, ignore_errors=True)


EMB = R.DeterministicEmbeddings(dim=8, seed="p6")


# ---------------------------------------------------------------------------
# document + embeddings
# ---------------------------------------------------------------------------
def test_document_round_trip_and_equality():
    d = R.Document("hello", {"a": 1}, "id1")
    assert R.Document.from_dict(d.to_dict()) == d
    assert R.Document("hello", {"a": 1}, "id1") == d
    assert R.Document("hello") != d
    assert "id1" in repr(d)
    # metadata defaults to a dict, never None
    assert R.Document("x").metadata == {}


def test_deterministic_embeddings_is_deterministic_and_unit():
    a = EMB.embed_query("alpha beta")
    b = R.DeterministicEmbeddings(dim=8, seed="p6").embed_query("alpha beta")
    assert a == b                       # byte-identical across instances
    assert len(a) == 8
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9   # unit norm -> cosine == dot
    assert a != EMB.embed_query("gamma delta")       # different text, other vector
    # documents embed per-text
    docs = EMB.embed_documents(["x", "y"])
    assert len(docs) == 2 and docs[0] != docs[1]


def test_deterministic_embeddings_dim_gate():
    with pytest.raises(ValueError):
        R.DeterministicEmbeddings(dim=0)


# ---------------------------------------------------------------------------
# the VectorStore ABC defaults + dispatch
# ---------------------------------------------------------------------------
def test_vectorstore_abc_honest_defaults(tmp_db):
    path, _ = tmp_db

    class BareStore(R.VectorStore):
        def similarity_search(self, query, k=4, **kwargs):
            return []

        @classmethod
        def from_texts(cls, texts, embedding, metadatas=None, **kwargs):
            return cls()

    bare = BareStore()
    with pytest.raises(NotImplementedError):
        bare.add_texts(["x"])
    with pytest.raises(NotImplementedError):
        bare.delete(["x"])
    with pytest.raises(NotImplementedError):
        bare.similarity_search_with_score("q")
    with pytest.raises(NotImplementedError):
        bare._select_relevance_score_fn()
    assert bare.get_by_ids(["x"]) == []          # an honest empty default
    assert bare.embeddings is None               # the property default
    # the dispatch refuses an unknown search_type
    with pytest.raises(ValueError, match="search_type"):
        bare.search("q", "fuzzy")


def test_vectorstore_search_dispatch(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    store.add_texts(["alpha", "beta"], metadatas=[{"t": "a"}, {"t": "b"}])
    sim = store.search("alpha", "similarity", k=2)
    assert len(sim) == 2 and sim[0].page_content == "alpha"
    thr = store.search("alpha", "similarity_score_threshold", k=1,
                       score_threshold=0.0)
    assert [d.page_content for d in thr] == ["alpha"]
    mmr = store.search("alpha", "mmr", k=2, fetch_k=2)
    assert len(mmr) == 2


def test_relevance_scores_contract_with_threshold(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    store.add_texts(["alpha beta", "gamma delta"])
    pairs = store.similarity_search_with_relevance_scores(
        "alpha beta", k=2, score_threshold=0.0)
    assert all(0.0 <= s <= 1.0 for _, s in pairs)     # the [0,1] contract
    assert pairs[0][0].page_content == "alpha beta"   # best match first
    # a threshold above every score is the honest empty list
    empty = store.similarity_search_with_relevance_scores(
        "alpha beta", k=2, score_threshold=1.01)
    assert empty == []


# ---------------------------------------------------------------------------
# the sqlite-first ANN
# ---------------------------------------------------------------------------
def test_sqlite_store_add_get_delete_and_scan(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    ids = store.add_texts(
        ["alpha beta", "gamma delta", "alpha zeta"],
        metadatas=[{"a": 1}, {"a": 2}, {"a": 1}])
    assert len(ids) == 3 and len(set(ids)) == 3
    # the kNN scan: the identical text wins
    top = store.similarity_search("alpha beta", k=3)
    assert top[0].page_content == "alpha beta"
    # with_score is cosine SIMILARITY, descending; the identical text is ~1.0
    pairs = store.similarity_search_with_score("alpha beta", k=2)
    assert pairs[0][1] == pytest.approx(1.0, abs=1e-6)
    assert pairs[0][1] > pairs[1][1]
    # the metadata-equality filter (the upstream in_memory contract)
    assert [d.page_content for d in
            store.similarity_search("alpha beta", k=3, filter={"a": 2})] \
        == ["gamma delta"]
    # get_by_ids honours the INPUT order, missing ids drop out
    got = store.get_by_ids([ids[2], ids[0]])
    assert [g.id for g in got] == [ids[2], ids[0]]
    assert store.get_by_ids(["nope"]) == []
    # delete is idempotent-True
    assert store.delete([ids[0]]) is True
    assert store.delete([ids[0]]) is True
    assert len(store.get_by_ids(ids[:1])) == 0
    with pytest.raises(ValueError):
        store.delete(None)


def test_sqlite_store_persists_across_instances(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    ids = store.add_texts(["persist me"], ids=["fixed-id"])
    # a fresh instance over the same file sees the rows
    store2 = R.SqliteVectorStore(EMB, path=path)
    assert store2.get_by_ids(ids)[0].page_content == "persist me"
    assert store2.similarity_search("persist me", k=1)[0].id == "fixed-id"


def test_sqlite_store_path_engine_gate(tmp_db):
    path, _ = tmp_db
    with pytest.raises(ValueError, match="exactly one"):
        R.SqliteVectorStore(EMB)
    with pytest.raises(ValueError, match="exactly one"):
        R.SqliteVectorStore(EMB, path=path, engine=object())
    with pytest.raises(ValueError, match="Embeddings"):
        R.SqliteVectorStore(None, path=path)


def test_sqlite_store_length_gates_and_from_texts(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    with pytest.raises(ValueError, match="metadatas"):
        store.add_texts(["a", "b"], metadatas=[{}])
    with pytest.raises(ValueError, match="ids"):
        store.add_texts(["a", "b"], ids=["x"])
    built = R.SqliteVectorStore.from_texts(
        ["one", "two"], EMB, metadatas=[{"i": 1}, {"i": 2}], path=path)
    assert len(built.similarity_search("one", k=2)) == 2
    assert built.embeddings is EMB


def test_sqlite_store_engine_lane(tmp_db):
    """The vault's sqlalchemy Engine rides raw_connection (the P3 SqliteSaver
    seam) - exercised with a shim engine, no sqlalchemy needed."""
    import sqlite3

    class ShimEngine:
        """The raw_connection shape the vault engine exposes."""

        def __init__(self, db_path):
            self._path = db_path

        def raw_connection(self):
            return sqlite3.connect(self._path)

    _, d = tmp_db
    eng_path = os.path.join(d, "engine.db")
    store = R.SqliteVectorStore(EMB, engine=ShimEngine(eng_path))
    store.add_texts(["engine lane"])          # first use ensures the table
    assert store.similarity_search("engine lane", k=1)[0].page_content \
        == "engine lane"
    rm = R.SqliteRecordManager("ns", engine=ShimEngine(eng_path))
    res = R.index([R.Document("ledger row", {"source": "s"})], rm, store)
    assert res["num_added"] == 1
    assert rm.list_keys()                     # the ledger really wrote


# ---------------------------------------------------------------------------
# MMR
# ---------------------------------------------------------------------------
def test_maximal_marginal_relevance_formula():
    q = [1.0, 0.0]
    same = [[1.0, 0.0], [0.9999, 0.01]]       # near-duplicates
    diverse = [[0.0, 1.0]]
    idxs = R.maximal_marginal_relevance(q, same + diverse, k=3)
    assert idxs[0] == 0                        # most query-similar first
    assert set(idxs) == {0, 1, 2}              # all picked when k covers all
    # lambda_mult=0 -> pure diversity: the second pick maximizes distance
    # to the selected set
    idxs0 = R.maximal_marginal_relevance(q, same + diverse, k=2, lambda_mult=0.0)
    assert idxs0[0] == 0 and idxs0[1] == 2
    # degenerate inputs
    assert R.maximal_marginal_relevance(q, [], k=4) == []
    assert R.maximal_marginal_relevance(q, same, k=0) == []


def test_mmr_diversifies_on_the_store(tmp_db):
    """MMR on the store with a CONTROLLED embedder - the deterministic sha
    embedder scatters unrelated texts randomly, so diversity needs vectors
    that actually mean what the test says."""
    path, _ = tmp_db
    v_dup_a = [1.0, 0.0, 0.0, 0.0]
    v_dup_b = [0.99, 0.1, 0.0, 0.0]          # a near-duplicate of dup_a
    v_other = [0.0, 0.0, 1.0, 0.0]           # orthogonal
    table = {"dup one": v_dup_a, "dup one again": v_dup_b,
             "totally other thing": v_other, "query": v_dup_a}

    class TableEmbeddings(R.Embeddings):
        def embed_documents(self, texts):
            return [table[t] for t in texts]

        def embed_query(self, text):
            return table[text]

    store = R.SqliteVectorStore(TableEmbeddings(), path=path)
    store.add_texts(list(table)[:3])
    mmr = store.max_marginal_relevance_search(
        "query", k=2, fetch_k=3, lambda_mult=0.0)
    assert len(mmr) == 2
    assert mmr[0].page_content == "dup one"
    # pure diversity drags the unrelated doc into the second slot
    assert mmr[1].page_content == "totally other thing"


# ---------------------------------------------------------------------------
# the ledger
# ---------------------------------------------------------------------------
def test_record_manager_ledger_shape_and_gates(tmp_db):
    _, d = tmp_db
    rm = R.SqliteRecordManager("ns1", path=os.path.join(d, "ledger.db"))
    rm.create_schema()                          # idempotent
    t0 = rm.get_time()
    assert isinstance(t0, float)
    rm.update(["k1", "k2"], group_ids=["g1", None])
    assert rm.exists(["k1", "k2", "k3"]) == [True, True, False]
    assert sorted(rm.list_keys()) == ["k1", "k2"]
    assert rm.list_keys(group_ids=["g1"]) == ["k1"]
    assert rm.list_keys(before=t0 + 1) == ["k1", "k2"]
    assert rm.list_keys(after=t0 + 1) == []
    assert rm.list_keys(limit=1) == ["k1"]      # ordered by updated_at
    rm.delete_keys(["k1"])
    assert rm.exists(["k1"]) == [False]
    rm.delete_keys([])                          # a no-op, never an error
    with pytest.raises(ValueError, match="group_ids"):
        rm.update(["a"], group_ids=["x", "y"])
    # the monotonic-clock law: a drifted time_at_least refuses the write
    with pytest.raises(ValueError, match="drifted"):
        rm.update(["k9"], time_at_least=rm.get_time() + 10_000)


def test_record_manager_path_engine_gate(tmp_db):
    _, d = tmp_db
    with pytest.raises(ValueError, match="exactly one"):
        R.SqliteRecordManager("ns")
    with pytest.raises(ValueError, match="exactly one"):
        R.SqliteRecordManager("ns", path=os.path.join(d, "a.db"),
                              engine=object())


# ---------------------------------------------------------------------------
# index()
# ---------------------------------------------------------------------------
def test_index_first_pass_and_no_op_reindex(tmp_db):
    path, d = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    rm = R.SqliteRecordManager("ns", path=os.path.join(d, "ledger.db"))
    docs = [R.Document("hello world", {"source": "s1"}),
            R.Document("other doc", {"source": "s1"}),
            R.Document("hello world", {"source": "s1"})]  # in-batch duplicate
    r1 = R.index(docs, rm, store)
    assert r1 == {"num_added": 2, "num_updated": 0, "num_skipped": 1,
                  "num_deleted": 0}
    r2 = R.index(docs, rm, store)
    assert r2["num_added"] == 0 and r2["num_skipped"] == 3  # 1 dup + 2 refreshes
    assert len(store.similarity_search("hello world", k=10)) == 2  # never doubled


def test_index_changed_content_updates_and_deletes_stale(tmp_db):
    path, d = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    rm = R.SqliteRecordManager("ns", path=os.path.join(d, "ledger.db"))
    R.index([R.Document("v1", {"source": "s1"})], rm, store,
            cleanup="incremental", source_id_key="source")
    r = R.index([R.Document("v2 changed", {"source": "s1"})], rm, store,
                cleanup="incremental", source_id_key="source")
    assert r["num_added"] == 1 and r["num_deleted"] == 1
    pages = [x.page_content for x in store.similarity_search("v2", k=10)]
    assert "v1" not in pages and "v2 changed" in pages


def test_index_full_and_scoped_full_cleanup(tmp_db):
    path, d = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    rm = R.SqliteRecordManager("ns", path=os.path.join(d, "ledger.db"))
    # run one: two sources
    R.index([R.Document("a1", {"source": "s1"}), R.Document("b1", {"source": "s2"})],
            rm, store, cleanup="incremental", source_id_key="source")
    # run two: full cleanup, only s1 returned -> s2's rows are gone
    r_full = R.index([R.Document("a1", {"source": "s1"})], rm, store,
                     cleanup="full")
    assert r_full["num_deleted"] == 1 and r_full["num_skipped"] == 1
    pages = [x.page_content for x in store.similarity_search("a1 b1", k=10)]
    assert pages == ["a1"]
    # scoped_full: only the sources TOUCHED this run get swept
    R.index([R.Document("c1", {"source": "s3"})], rm, store,
            cleanup="incremental", source_id_key="source")
    r_scoped = R.index([R.Document("c2", {"source": "s3"})], rm, store,
                       cleanup="scoped_full", source_id_key="source")
    assert r_scoped["num_deleted"] == 1
    pages = [x.page_content for x in store.similarity_search("a1 c2", k=10)]
    assert sorted(pages) == ["a1", "c2"]


def test_index_gates(tmp_db):
    path, d = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    rm = R.SqliteRecordManager("ns", path=os.path.join(d, "ledger.db"))
    # incremental/scoped_full require a source id key
    with pytest.raises(ValueError, match="source_id_key"):
        R.index([R.Document("x")], rm, store, cleanup="incremental")
    with pytest.raises(ValueError, match="source_id_key"):
        R.index([R.Document("x")], rm, store, cleanup="scoped_full")
    # a doc without the source metadata is refused under incremental
    with pytest.raises(ValueError, match="not assigned a source id"):
        R.index([R.Document("x", {})], rm, store, cleanup="incremental",
                source_id_key="source")
    # batch_size must be positive
    with pytest.raises(ValueError, match="Batch size"):
        R.index([R.Document("x")], rm, store, batch_size=0)
    # a store that never implemented delete cannot be indexed
    class NoDelete(R.VectorStore):
        def similarity_search(self, query, k=4, **kwargs):
            return []

        @classmethod
        def from_texts(cls, texts, embedding, metadatas=None, **kwargs):
            return cls()

    with pytest.raises(ValueError, match="delete"):
        R.index([R.Document("x")], rm, NoDelete())
    with pytest.raises(TypeError):
        R.index([R.Document("x")], rm, "not a store")


def test_index_force_update_and_key_encoders(tmp_db):
    path, d = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    rm = R.SqliteRecordManager("ns", path=os.path.join(d, "ledger.db"))
    docs = [R.Document("same text", {"source": "s1"})]
    R.index(docs, rm, store)
    forced = R.index(docs, rm, store, force_update=True)
    assert forced["num_updated"] == 1 and forced["num_skipped"] == 0
    # the encoders all produce stable, distinct-per-content ids
    ids = set()
    for algo in ("sha1", "sha256", "sha512", "blake2b"):
        h1 = R._hash_document(R.Document("t", {"m": 1}), algo)
        h2 = R._hash_document(R.Document("t", {"m": 1}), algo)
        assert h1.id == h2.id
        ids.add(h1.id)
    assert len(ids) == 4
    # a metadata-only edit rehashes (content and metadata hashed separately)
    assert R._hash_document(R.Document("t", {"m": 1}), "sha256").id \
        != R._hash_document(R.Document("t", {"m": 2}), "sha256").id
    with pytest.raises(ValueError, match="Unsupported hashing"):
        R._hash_document(R.Document("t"), "md5")
    # an unserializable metadata dict is refused with the upstream wording
    with pytest.raises(ValueError, match="Failed to hash metadata"):
        R._hash_document(R.Document("t", {"bad": object()}), "sha256")


async def _aindex_probe(store, rm, docs):
    return await R.aindex(docs, rm, store)


def test_aindex_twin(tmp_db):
    path, d = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    rm = R.SqliteRecordManager("ns", path=os.path.join(d, "ledger.db"))
    result = asyncio.run(_aindex_probe(
        store, rm, [R.Document("async doc", {"source": "s"})]))
    assert result["num_added"] == 1
    assert store.similarity_search("async doc", k=1)[0].page_content \
        == "async doc"


# ---------------------------------------------------------------------------
# the text splitters
# ---------------------------------------------------------------------------
def test_recursive_splitter_ladder_and_gates():
    sp = R.RecursiveCharacterTextSplitter(chunk_size=30, chunk_overlap=5)
    text = ("para one " * 6 + "\n\n" + "line two " * 4 + "\n" + "tail")
    chunks = sp.split_text(text)
    assert len(chunks) >= 2
    assert all(len(c) <= 30 for c in chunks)      # every chunk respects the cap
    assert "".join(chunks).replace(" ", "").startswith("paraone")
    # a short text is one chunk, unchanged
    assert sp.split_text("tiny") == ["tiny"]
    # the split gates
    with pytest.raises(ValueError, match="chunk_overlap"):
        R.CharacterTextSplitter(chunk_size=10, chunk_overlap=11)
    with pytest.raises(ValueError, match="positive"):
        R.CharacterTextSplitter(chunk_size=0)
    with pytest.raises(ValueError, match="non-negative"):
        R.CharacterTextSplitter(chunk_size=10, chunk_overlap=-1)


def test_character_splitter_separator_laws():
    sp = R.CharacterTextSplitter(separator="\n\n", chunk_size=100,
                                 chunk_overlap=0)
    out = sp.split_text("aaa\n\nbbb\n\nccc")
    assert out == ["aaa\n\nbbb\n\nccc"]           # under the cap: joined back
    sp_small = R.CharacterTextSplitter(separator="\n\n", chunk_size=3,
                                       chunk_overlap=0)
    out = sp_small.split_text("aaa\n\nbbbb\n\nccc")
    # a single split longer than the cap is emitted AS-IS (never truncated -
    # the upstream law), the rest merge to the cap
    assert out == ["aaa", "bbbb", "ccc"]
    # keep_separator keeps the delimiter attached (strip_whitespace off, or the
    # stripped reality is indistinguishable from a dropped separator)
    sp_keep = R.CharacterTextSplitter(separator="\n\n", chunk_size=6,
                                      chunk_overlap=0, keep_separator=True,
                                      strip_whitespace=False)
    out = sp_keep.split_text("aaa\n\nbbbb")
    assert out == ["aaa", "\n\nbbbb"]
    # a regex lookaround separator is never re-inserted (the upstream guard)
    sp_look = R.CharacterTextSplitter(separator="(?=b)", chunk_size=3,
                                      chunk_overlap=0, is_separator_regex=True)
    out = sp_look.split_text("ababab")
    assert all("(?=b)" not in c for c in out)
    assert len(out) >= 2


def test_splitter_create_documents_metadata_laws():
    sp = R.RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=2,
                                          add_start_index=True)
    docs = sp.create_documents(["x" * 25], [{"k": "v"}])
    assert len(docs) == 3
    assert docs[0].metadata["k"] == "v"
    assert docs[0].metadata["start_index"] == 0
    assert docs[1].metadata["start_index"] > 0    # the offset math ran
    # the metadata deep-copy law: mutating one chunk never leaks into a sibling
    docs[0].metadata["k"] = "mutated"
    assert docs[1].metadata["k"] == "v"
    with pytest.raises(ValueError, match="metadatas"):
        sp.create_documents(["a", "b"], [{}])
    # split_documents carries metadata through
    src = [R.Document("y" * 30, {"src": "doc1"})]
    split = sp.split_documents(src)
    assert len(split) >= 3 and all(d.metadata["src"] == "doc1" for d in split)


# ---------------------------------------------------------------------------
# the retrievers
# ---------------------------------------------------------------------------
def test_vector_store_retriever_similarity_and_mmr(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    store.add_texts(["alpha beta", "gamma delta"])
    rt = store.as_retriever(search_type="similarity", search_kwargs={"k": 1})
    out = rt.invoke("alpha beta")
    assert len(out) == 1 and out[0].page_content == "alpha beta"
    mmr_rt = store.as_retriever(search_type="mmr",
                                search_kwargs={"k": 2, "fetch_k": 2})
    assert len(mmr_rt.invoke("alpha beta")) == 2
    with pytest.raises(ValueError, match="search_type"):
        store.as_retriever(search_type="tfidf")
    # the add_documents proxy keeps the ingestion door on the retriever
    new_id = rt.add_documents([R.Document("added via retriever")])[0]
    assert store.get_by_ids([new_id])[0].page_content == "added via retriever"


def test_retriever_is_a_runnable_and_fires_the_p2_span(tmp_db):
    path, _ = tmp_db
    store = R.SqliteVectorStore(EMB, path=path)
    store.add_texts(["alpha beta"])
    runstore = InMemoryRunStore()
    mgr = CallbackManager([RunTreeTracer(sinks=[runstore])])
    rt = store.as_retriever()
    out = rt.invoke("alpha beta", {"callbacks": mgr, "tags": ["p6"]})
    assert isinstance(out, list) and out
    kinds = [r.run_type for r in runstore.recent(limit=20)]
    assert "retriever" in kinds                   # RUN_TYPES pre-declared it in P2
    run = next(r for r in runstore.recent(limit=20) if r.run_type == "retriever")
    assert run.outputs and len(run.outputs) == 1  # the finished run persisted
    # the a-twin rides to_thread and returns the same shape
    out2 = asyncio.run(rt.ainvoke("alpha beta"))
    assert [d.page_content for d in out2] == [d.page_content for d in out]


def test_custom_retriever_subclass_contract():
    class StaticRetriever(R.BaseRetriever):
        def _get_relevant_documents(self, query, *, run_manager=None):
            return [R.Document(f"doc for {query}")]

    out = StaticRetriever().invoke("q")
    assert out[0].page_content == "doc for q"


def test_docs7_retriever_injected_fetch_and_gates():
    calls = []

    def fetch(query):
        calls.append(query)
        return {"ok": True, "text": "the library docs body",
                "library_id": "/org/proj", "cached": True}

    d7 = R.Docs7Retriever("/org/proj", fetch=fetch)
    out = d7.invoke("how do i x")
    assert calls == ["how do i x"]
    assert len(out) == 1
    assert out[0].page_content == "the library docs body"
    assert out[0].metadata == {"source": "docs7", "library_id": "/org/proj",
                               "cached": True}
    assert d7.last_result["ok"] is True
    # ok=False is the honest EMPTY list, the raw result stays inspectable
    d7_off = R.Docs7Retriever(
        "/org/proj", fetch=lambda q: {"ok": False, "error": "docs7 is switched off"})
    assert d7_off.invoke("q") == []
    assert d7_off.last_result["ok"] is False
    # an empty text is also empty (a valid not-found upstream)
    d7_empty = R.Docs7Retriever("/org/proj", fetch=lambda q: {"ok": True, "text": ""})
    assert d7_empty.invoke("q") == []
    # the library-id gate mirrors the docs7 handler's own rule
    with pytest.raises(ValueError, match="org/project"):
        R.Docs7Retriever("bad-id")
    # the async twin
    out2 = asyncio.run(d7.ainvoke("how do i x"))
    assert len(out2) == 1


# ---------------------------------------------------------------------------
# the laws
# ---------------------------------------------------------------------------
def test_inertness_law():
    """A fresh interpreter imports app.aep.retrieve with zero extra threads,
    zero env reads, zero files - the P1/P5 inertness law, re-proven for P6."""
    import subprocess
    import sys
    code = (
        "import sys, threading; sys.path.insert(0, 'server');"
        "before = threading.active_count();"
        "import app.aep.retrieve;"
        "import app.aep as pkg;"
        "assert threading.active_count() == before, 'thread leak';"
        "assert not [n for n in dir(app.aep.retrieve) if n.startswith('_open')], 'oops';"
        "print('INERT-OK', threading.active_count())"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "INERT-OK" in out.stdout


def test_package_export_law():
    import app.aep as pkg
    for name in R.__all__:
        assert hasattr(pkg, name), f"app.aep.{name} missing (the export law)"
        assert name in pkg.__all__, f"{name} missing from app.aep.__all__"


def test_version_pins():
    from pathlib import Path
    from app.main import APP_VERSION
    root = Path(__file__).resolve().parents[2]
    assert APP_VERSION == "0.800.0"
    assert "0.800.0+799" in (root / "pubspec.yaml").read_text()
