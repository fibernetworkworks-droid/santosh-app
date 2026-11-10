---
type: "AEP evidence"
title: "P6 HOOLA RETRIEVE"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/retrieve.py
  - repo://server/tests/test_v0560_hoola_retrieve.py
---

The retrieval layer: Document, Embeddings + the deterministic sha embedder, the sqlite-first ANN, RecordManager + index() dedup, the text splitters, retrievers as Runnables firing the P2 span, docs7 as a source.

Files: `server/app/aep/retrieve.py` (1644 lines)
Suite: `server/tests/test_v0560_hoola_retrieve.py` (31 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| Document + dict round trip | `app.aep.retrieve.Document` | `test_document_round_trip_and_equality` |
| Embeddings ABC + the deterministic embedder | `app.aep.retrieve.DeterministicEmbeddings` | `test_deterministic_embeddings_is_deterministic_and_unit` |
| VectorStore ABC honest defaults | `app.aep.retrieve.VectorStore` | `test_vectorstore_abc_honest_defaults(tmp_db)` |
| search dispatch similarity|threshold|mmr | `app.aep.retrieve.VectorStore` | `test_vectorstore_search_dispatch(tmp_db)` |
| the [0,1] relevance contract | `app.aep.retrieve.VectorStore` | `test_relevance_scores_contract_with_threshold(tmp_db)` |
| SqliteVectorStore kNN scan + filter | `app.aep.retrieve.SqliteVectorStore` | `test_sqlite_store_add_get_delete_and_scan(tmp_db)` |
| sqlite persistence across instances | `app.aep.retrieve.SqliteVectorStore` | `test_sqlite_store_persists_across_instances(tmp_db)` |
| path=/engine= gate (the vault seam) | `app.aep.retrieve.SqliteVectorStore` | `test_sqlite_store_path_engine_gate(tmp_db)` |
| maximal_marginal_relevance formula | `app.aep.retrieve.maximal_marginal_relevance` | `test_maximal_marginal_relevance_formula` |
| MMR on the store | `app.aep.retrieve.SqliteVectorStore` | `test_mmr_diversifies_on_the_store(tmp_db)` |
| RecordManager ledger + gates | `app.aep.retrieve.SqliteRecordManager` | `test_record_manager_ledger_shape_and_gates(tmp_db)` |
| index() dedup first pass / no-op | `app.aep.retrieve.index` | `test_index_first_pass_and_no_op_reindex(tmp_db)` |
| changed content -> update + stale delete | `app.aep.retrieve.index` | `test_index_changed_content_updates_and_deletes_stale(tmp_db)` |
| full + scoped_full cleanup | `app.aep.retrieve.index` | `test_index_full_and_scoped_full_cleanup(tmp_db)` |
| key encoders + force_update | `app.aep.retrieve.index` | `test_index_force_update_and_key_encoders(tmp_db)` |
| aindex twin | `app.aep.retrieve.aindex` | `test_aindex_twin(tmp_db)` |
| RecursiveCharacterTextSplitter ladder | `app.aep.retrieve.RecursiveCharacterTextSplitter` | `test_recursive_splitter_ladder_and_gates` |
| CharacterTextSplitter separator laws | `app.aep.retrieve.CharacterTextSplitter` | `test_character_splitter_separator_laws` |
| create_documents metadata laws | `app.aep.retrieve.TextSplitter` | `test_splitter_create_documents_metadata_laws` |
| VectorStoreRetriever similarity+mmr | `app.aep.retrieve.VectorStoreRetriever` | `test_vector_store_retriever_similarity_and_mmr(tmp_db)` |
| retriever fires the P2 span | `app.aep.retrieve.BaseRetriever` | `test_retriever_is_a_runnable_and_fires_the_p2_span(tmp_db)` |
| Docs7Retriever (docs7 as a source) | `app.aep.retrieve.Docs7Retriever` | `test_docs7_retriever_injected_fetch_and_gates` |

