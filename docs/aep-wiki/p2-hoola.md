---
type: "AEP evidence"
title: "P2 HOOLA TRACE"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/tracers.py
  - repo://server/app/aep/vault_sink.py
  - repo://server/tests/test_v0520_hoola_trace.py
---

The LangSmith layer self-hosted: callbacks manager, run trees, astream_events v2, the Span fire seam every later phase rides, and the flag-gated vault persistence (runs land as 'aep_run' observations).

Files: `server/app/aep/tracers.py` (644 lines), `server/app/aep/vault_sink.py` (142 lines)
Suite: `server/tests/test_v0520_hoola_trace.py` (39 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| CallbackManager child propagation | `app.aep.tracers.CallbackManager` | `test_manager_child_propagation` |
| a broken handler never breaks the run | `app.aep.tracers.CallbackManager` | `test_broken_handler_never_breaks_the_run` |
| callbacks_from_config shapes | `app.aep.tracers.callbacks_from_config` | `test_callbacks_from_config_shapes` |
| chain spans build a sequence tree | `app.aep.tracers.Span` | `test_chain_spans_sequence_tree` |
| chat_model spans on invoke + stream | `app.aep.tracers.Span` | `test_chat_model_spans_invoke_and_stream` |
| BaseLLM span | `app.aep.tracers.Span` | `test_base_llm_span` |
| tool span named by the tool | `app.aep.tracers.Span` | `test_tool_span_named_by_the_tool` |
| error tree captures + reraises | `app.aep.tracers.Span` | `test_error_tree_captures_and_reraises` |
| parallel tree nesting | `app.aep.tracers.Span` | `test_tree_nesting_parallel` |
| trace_id shared across the invocation | `app.aep.tracers.Run` | `test_trace_id_shared_across_the_invocation` |
| Run node shape + status | `app.aep.tracers.Run` | `test_run_node_shape_and_status` |
| dumps_safe handles messages + junk | `app.aep.tracers.dumps_safe` | `test_dumps_safe_handles_messages_and_junk` |
| astream_events v2 full sequence + parents | `app.aep.tracers.astream_events` | `test_astream_events_full_sequence_and_parent_wiring` |
| astream_events over a bare model | `app.aep.tracers.astream_events` | `test_astream_events_over_a_bare_model` |
| astream_events version guard | `app.aep.tracers.astream_events` | `test_astream_events_version_guard` |
| astream_events error surfaced + generator ends | `app.aep.tracers.astream_events` | `test_astream_events_error_surfaced_and_generator_ends` |
| InMemoryRunStore ring cap | `app.aep.tracers.InMemoryRunStore` | `test_inmemory_store_ring_cap` |
| global_tracer + traced_invoke | `app.aep.tracers.traced_invoke` | `test_global_tracer_and_traced_invoke` |
| aep_trace flag defaults OFF | `app.aep.vault_sink.trace_enabled` | `test_flag_defaults_off(monkeypatch)` |
| flag OFF is a silent noop | `app.aep.vault_sink.VaultRunSink` | `test_vault_sink_flag_off_is_a_silent_noop(monkeypatch)` |
| flag ON lands an aep_run row | `app.aep.vault_sink.VaultRunSink` | `test_vault_sink_flag_on_lands_an_aep_run_row(monkeypatch)` |
| redaction before storage | `app.aep.vault_sink.VaultRunSink` | `test_vault_sink_redaction_before_storage(monkeypatch)` |
| fail-closed on sink errors | `app.aep.vault_sink.VaultRunSink` | `test_vault_sink_fail_closed(monkeypatch)` |
| attach_vault_sink idempotent | `app.aep.vault_sink.attach_vault_sink` | `test_attach_vault_sink_idempotent` |
| runs explorer routes fail closed | `app.aep.vault_sink.vault_runs` | `test_routes_fail_closed_when_flag_off(monkeypatch, env)` |
| stats carries the AEP block | `app.aep.vault_sink.STATS` | `test_agent_stats_carries_the_aep_block(env)` |
| the trace_flip vps-ops job shape | `app.aep.vault_sink.trace_enabled` | `test_trace_flip_job_shape` |
| retriever run type pre-declared (the P6 seam) | `app.aep.tracers.RUN_TYPES` | `test_retriever_is_a_runnable_and_fires_the_p2_span(tmp_db)` |

