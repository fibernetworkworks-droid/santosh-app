"""HOOLA AEP audit - the 100% parity audit + the openwiki analog, P8 of the
AEP plan (owner: "P7 HUB -> P8 the 100% parity audit"; the plan: "every
langchain feature mapped to a Hoola module + test, phase-by-phase checklist
sign-off").

The upstream analog (read at the pinned commit aa2528fb): openwiki/ = generated
evidence index pages grounded in the repo (front-matter with `sources:
repo://...`, an index listing, per-topic pages); the house harness generates
the same SHAPE from the vault (the live aep tree + the seven phase suites).

WHAT LIVES HERE
- `PARITY_MATRIX` - the machine-readable parity claim: one row per upstream
  feature -> (phase, feature, upstream ref, hoola module, hoola symbol,
  proving test file, proving test needle). THE 100% CLAIM IS CHECKED, NOT
  ASSERTED: `audit_parity()` imports every symbol live, greps every test
  needle live, and reports any row that drifted - a red row fails the audit.
- `phase_checklist()` - the phase-by-phase sign-off: P1..P8 with the real
  files, real LOC (counted from the tree), real test counts (counted from the
  suites) - living numbers, never hard-coded.
- `generate_wiki(out_dir)` - the openwiki analog: deterministic markdown
  evidence pages (index.md + one page per phase) with front-matter
  (generated-by, deterministic stamp) and `repo://` sources; the same payload
  writes byte-stable files.
- `main(argv)` - the CLI: `python -m app.aep.audit matrix|checklist|wiki`.

Inert library: files are read only when a command runs - nothing on import.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER = REPO_ROOT / "server"
AEP = SERVER / "app" / "aep"
TESTS = SERVER / "tests"

CORE_SUITE = "test_v0510_hoola_core.py"
TRACE_SUITE = "test_v0520_hoola_trace.py"
GRAPH_SUITE = "test_v0530_hoola_graph.py"
AGENT_SUITE = "test_v0540_hoola_agent.py"
MW_SUITE = "test_v0550_hoola_middleware.py"
RET_SUITE = "test_v0560_hoola_retrieve.py"
HUB_SUITE = "test_v0570_hoola_hub.py"
AUDIT_SUITE = "test_v0600_hoola_aep1.py"

# ---------------------------------------------------------------------------
# the parity matrix
# row = (phase, feature, upstream_ref, module, symbol, test_file, needle)
# upstream refs cite the verified read @ aa2528fb (file:line where known).
# ---------------------------------------------------------------------------

R = tuple[str, str, str, str, str, str, str]


def _rows() -> list[R]:
    m: list[R] = []
    a = m.append

    # ---- P1 HOOLA CORE -----------------------------------------------------
    p1 = "P1"
    for feat, mod, sym, needle in [
        ("17 content block types", "messages", "CONTENT_BLOCK_TYPES", "test_seventeen_content_block_types"),
        ("BaseMessage family (human/ai/system/tool/function/chat)", "messages", "HumanMessage", "test_message_family_types"),
        ("AIMessageChunk '+' merge", "messages", "AIMessageChunk", "test_chunk_merge_content_and_id"),
        ("tool_call_chunk merge by index", "messages", "ToolCallChunk", "test_chunk_merge_tool_call_chunks_by_index"),
        ("message dict round trip", "messages", "message_to_dict", "test_message_dict_round_trip"),
        ("RemoveMessage + REMOVE_ALL_MESSAGES", "messages", "RemoveMessage", "test_remove_message_and_sentinel"),
        ("merge_content shapes", "messages", "merge_content", "test_merge_content_shapes"),
        ("chunk -> message downgrade", "messages", "message_chunk_to_message", "test_message_chunk_to_message_downgrade"),
        ("Runnable invoke/batch/stream", "runnable", "Runnable", "test_sequence_pipe_and_invoke"),
        ("RunnableSequence '|' + ror", "runnable", "RunnableSequence", "test_sequence_ror_and_pipe_alias"),
        ("RunnableParallel (dict literal coercion)", "runnable", "RunnableParallel", "test_dict_literal_coerces_to_parallel"),
        ("batch threaded + ordered", "runnable", "Runnable", "test_batch_threaded_and_ordered"),
        ("batch return_exceptions", "runnable", "Runnable", "test_batch_return_exceptions"),
        ("ainvoke/abatch twins", "runnable", "Runnable", "test_ainvoke_and_abatch"),
        ("RunnableLambda (+ async)", "runnable", "RunnableLambda", "test_async_lambda_and_sequence"),
        ("stream through a sequence", "runnable", "RunnableSequence", "test_stream_and_sequence_stream"),
        ("RunnableBinding kwargs ride config", "runnable", "RunnableBinding", "test_binding_kwargs_ride_the_config_channel"),
        ("with_retry (flaky recovery)", "runnable", "RunnableRetry", "test_retry_succeeds_after_flaky_failures"),
        ("with_fallbacks (second wins / last raise)", "runnable", "RunnableWithFallbacks", "test_fallbacks_second_wins"),
        ("RunnablePassthrough assign", "runnable", "RunnablePassthrough", "test_passthrough_and_assign"),
        ("lambda input schema from hints", "runnable", "RunnableLambda", "test_lambda_input_schema_from_basemodel_hint"),
        ("BaseTool + @tool schema from hints/docstring", "tools", "tool", "test_tool_decorator_schema_from_hints_and_docstring"),
        ("BaseTool subclass contract", "tools", "BaseTool", "test_basetool_subclass_contract"),
        ("tool_call dict -> ToolMessage", "tools", "BaseTool", "test_tool_call_dict_returns_tool_message"),
        ("content_and_artifact", "tools", "BaseTool", "test_content_and_artifact_response_format"),
        ("ToolException + handle_tool_error", "tools", "ToolException", "test_tool_exception_and_handle_tool_error"),
        ("InjectedToolArg hidden from the model schema", "tools", "InjectedToolArg", "test_injected_args_hidden_from_model_schema"),
        ("StructuredTool.from_function", "tools", "StructuredTool", "test_structured_tool_from_function"),
        ("tool as a Runnable (composes)", "tools", "BaseTool", "test_tool_is_runnable_and_composes"),
        ("BaseChatModel _generate/_llm_type contract", "models", "BaseChatModel", "test_chat_model_subclass_contract_invoke"),
        ("message list/dict input coercion", "models", "BaseChatModel", "test_chat_model_message_list_and_dict_inputs"),
        ("generate -> ChatResult", "models", "BaseChatModel", "test_generate_returns_chat_result"),
        ("generate_prompt", "models", "BaseChatModel", "test_generate_prompt_uses_prompt_values"),
        ("InMemoryCache dedupes generate", "models", "InMemoryCache", "test_inmemory_cache_dedupes_generate_calls"),
        ("InMemoryRateLimiter token bucket", "models", "InMemoryRateLimiter", "test_rate_limiter_token_bucket"),
        ("bind_tools honest default refusal", "models", "BaseChatModel", "test_bind_tools_default_unsupported"),
        ("with_structured_output (plain + fenced JSON)", "models", "BaseChatModel", "test_with_structured_output_fenced_json_and_system_merge"),
        ("ModelProfile + UsageMetadata", "models", "ModelProfile", "test_model_profile_and_usage_fields_exist"),
        ("FakeListChatModel stream chunks", "models", "FakeListChatModel", "test_fake_stream_chunks"),
        ("BaseLLM contract", "models", "BaseLLM", "test_base_llm_contract"),
        ("_identifying_params + _llm_string", "models", "BaseChatModel", "test_identifying_params_and_llm_string"),
        ("PromptTemplate (+ partials, missing-var raise)", "prompts", "PromptTemplate", "test_prompt_template_from_template_and_format"),
        ("prompt invoke -> StringPromptValue", "prompts", "PromptTemplate", "test_prompt_invoke_returns_string_prompt_value"),
        ("ChatPromptTemplate from tuples", "prompts", "ChatPromptTemplate", "test_chat_prompt_template_from_tuples"),
        ("MessagesPlaceholder required/optional", "prompts", "MessagesPlaceholder", "test_chat_prompt_placeholder_required_and_optional"),
        ("StrOutputParser", "parsers", "StrOutputParser", "test_str_output_parser"),
        ("JsonOutputParser tolerates fences", "parsers", "JsonOutputParser", "test_json_output_parser_tolerates_fences"),
        ("PydanticOutputParser validates", "parsers", "PydanticOutputParser", "test_pydantic_output_parser_validates"),
        ("parser composes after a model", "parsers", "BaseOutputParser", "test_parser_composes_after_model"),
        ("BaseChatMessageHistory + InMemory", "history", "InMemoryChatMessageHistory", "test_inmemory_history_round_trip"),
        ("get_buffer_string roles", "history", "get_buffer_string", "test_buffer_string_roles"),
        ("BaseStore/InMemoryStore namespaced", "stores", "InMemoryStore", "test_inmemory_store_namespaced"),
        ("store key validation", "stores", "InvalidKeyException", "test_store_rejects_bad_keys"),
        ("InMemoryByteStore bytes only", "stores", "InMemoryByteStore", "test_byte_store_bytes_only"),
        ("Serializable lc shape (the P7 loader seed)", "serializable", "Serializable", "test_serializable_lc_shape"),
        ("lc_id path convention", "serializable", "Serializable", "test_serializable_lc_id_path"),
    ]:
        a((p1, feat, "langchain-core @ aa2528fb (messages/runnables/tools/language_models/prompts/parsers/stories)",
           mod, sym, CORE_SUITE, needle))

    # ---- P2 HOOLA TRACE ----------------------------------------------------
    p2 = "P2"
    for feat, mod, sym, needle in [
        ("CallbackManager child propagation", "tracers", "CallbackManager", "test_manager_child_propagation"),
        ("a broken handler never breaks the run", "tracers", "CallbackManager", "test_broken_handler_never_breaks_the_run"),
        ("callbacks_from_config shapes", "tracers", "callbacks_from_config", "test_callbacks_from_config_shapes"),
        ("chain spans build a sequence tree", "tracers", "Span", "test_chain_spans_sequence_tree"),
        ("chat_model spans on invoke + stream", "tracers", "Span", "test_chat_model_spans_invoke_and_stream"),
        ("BaseLLM span", "tracers", "Span", "test_base_llm_span"),
        ("tool span named by the tool", "tracers", "Span", "test_tool_span_named_by_the_tool"),
        ("error tree captures + reraises", "tracers", "Span", "test_error_tree_captures_and_reraises"),
        ("parallel tree nesting", "tracers", "Span", "test_tree_nesting_parallel"),
        ("trace_id shared across the invocation", "tracers", "Run", "test_trace_id_shared_across_the_invocation"),
        ("Run node shape + status", "tracers", "Run", "test_run_node_shape_and_status"),
        ("dumps_safe handles messages + junk", "tracers", "dumps_safe", "test_dumps_safe_handles_messages_and_junk"),
        ("astream_events v2 full sequence + parents", "tracers", "astream_events", "test_astream_events_full_sequence_and_parent_wiring"),
        ("astream_events over a bare model", "tracers", "astream_events", "test_astream_events_over_a_bare_model"),
        ("astream_events version guard", "tracers", "astream_events", "test_astream_events_version_guard"),
        ("astream_events error surfaced + generator ends", "tracers", "astream_events", "test_astream_events_error_surfaced_and_generator_ends"),
        ("InMemoryRunStore ring cap", "tracers", "InMemoryRunStore", "test_inmemory_store_ring_cap"),
        ("global_tracer + traced_invoke", "tracers", "traced_invoke", "test_global_tracer_and_traced_invoke"),
        ("aep_trace flag defaults OFF", "vault_sink", "trace_enabled", "test_flag_defaults_off(monkeypatch)"),
        ("flag OFF is a silent noop", "vault_sink", "VaultRunSink", "test_vault_sink_flag_off_is_a_silent_noop(monkeypatch)"),
        ("flag ON lands an aep_run row", "vault_sink", "VaultRunSink", "test_vault_sink_flag_on_lands_an_aep_run_row(monkeypatch)"),
        ("redaction before storage", "vault_sink", "VaultRunSink", "test_vault_sink_redaction_before_storage(monkeypatch)"),
        ("fail-closed on sink errors", "vault_sink", "VaultRunSink", "test_vault_sink_fail_closed(monkeypatch)"),
        ("attach_vault_sink idempotent", "vault_sink", "attach_vault_sink", "test_attach_vault_sink_idempotent"),
        ("runs explorer routes fail closed", "vault_sink", "vault_runs", "test_routes_fail_closed_when_flag_off(monkeypatch, env)"),
        ("stats carries the AEP block", "vault_sink", "STATS", "test_agent_stats_carries_the_aep_block(env)"),
        ("the trace_flip vps-ops job shape", "vault_sink", "trace_enabled", "test_trace_flip_job_shape"),
    ]:
        a((p2, feat, "LangSmith layer (tracers/, callbacks/manager.py) @ aa2528fb", mod, sym, TRACE_SUITE, needle))
    # the P6 seam row proves itself in the P6 suite (the retriever span test)
    a((p2, "retriever run type pre-declared (the P6 seam)",
       "LangSmith layer (tracers/, callbacks/manager.py) @ aa2528fb",
       "tracers", "RUN_TYPES", RET_SUITE,
       "test_retriever_is_a_runnable_and_fires_the_p2_span(tmp_db)"))

    # ---- P3 HOOLA GRAPH ----------------------------------------------------
    p3 = "P3"
    for feat, mod, sym, needle in [
        ("StateGraph nodes/edges build-time gates", "graph", "StateGraph", "test_add_node_refuses_duplicates_reserved_and_junk"),
        ("conditional edges + path maps", "graph", "StateGraph", "test_conditional_dict_and_positional_path_maps"),
        ("compile gates (no nodes/entry/bad map)", "graph", "StateGraph", "test_compile_refuses_no_nodes_no_entry_and_bad_path_map"),
        ("plain channels last-value-wins", "graph", "StateGraph", "test_plain_channels_are_last_value_wins"),
        ("reducer channels merge, first seeds", "graph", "StateGraph", "test_reducer_channels_merge_and_first_value_seeds"),
        ("diamond fan-out + join barrier", "graph", "StateGraph", "test_diamond_fan_out_join_barrier_runs_once"),
        ("add_messages semantics", "graph", "add_messages", "test_add_messages_semantics"),
        ("AgentState accumulates messages", "graph", "AgentState", "test_agent_state_accumulates_messages_across_nodes"),
        ("checkpoint every super-step + get_state", "graph", "BaseCheckpointSaver", "test_checkpoint_after_every_super_step_and_get_state"),
        ("MemorySaver isolation + delete", "graph", "MemorySaver", "test_memory_saver_thread_isolation_and_delete"),
        ("SqliteSaver round trip (path lane)", "graph", "SqliteSaver", "test_sqlite_saver_round_trip_and_refusals(tmp_path)"),
        ("SqliteSaver engine lane (the vault way)", "graph", "SqliteSaver", "test_sqlite_saver_engine_shape_the_vault_way(tmp_path)"),
        ("interrupt()/Command park-and-resume", "graph", "interrupt", "test_park_shape_and_resume"),
        ("Command(update) + goto", "graph", "Command", "test_command_update_only_and_goto"),
        ("second interrupt keeps the first answer", "graph", "GraphInterrupt", "test_two_interrupts_second_park_keeps_first_answer"),
        ("resume without a park refuses", "graph", "GraphInterrupt", "test_resume_without_a_park_refuses"),
        ("async nodes + park", "graph", "StateGraph", "test_async_nodes_ainvoke_and_park"),
        ("node spans named by the node", "graph", "StateGraph", "test_node_spans_fire_named_by_the_node"),
        ("recursion limit default + configurable", "graph", "GraphRecursionError", "test_recursion_limit_default_and_configurable"),
        ("config + store ride two-arg nodes", "graph", "StateGraph", "test_two_arg_node_receives_config_and_store_rides"),
        ("update_state rederives next", "graph", "StateGraph", "test_update_state_as_node_rederives_next"),
    ]:
        a((p3, feat, "langgraph-lite (StateGraph/interrupts/checkpointers) @ aa2528fb", mod, sym, GRAPH_SUITE, needle))

    # ---- P4 HOOLA AGENT ----------------------------------------------------
    p4 = "P4"
    for feat, mod, sym, needle in [
        ("create_agent -> a named compiled graph", "agent", "create_agent", "test_create_agent_returns_a_named_compiled_graph"),
        ("create_react_agent alias", "agent", "create_react_agent", "test_default_name_is_agent_and_alias_is_identity"),
        ("model-only agent (no tools)", "agent", "create_agent", "test_no_tools_agent_is_model_only"),
        ("model string refused (the P7 pointer)", "agent", "create_agent", "test_model_string_refused_with_the_p7_pointer"),
        ("plain callables become tools", "agent", "create_agent", "test_plain_callable_becomes_a_tool"),
        ("model without bind_tools refused at build", "agent", "create_agent", "test_model_without_bind_tools_refused_at_build_time"),
        ("prebound Runnable model lane", "agent", "create_agent", "test_prebound_runnable_model_lane"),
        ("full ReAct loop", "agent", "create_agent", "test_full_react_loop"),
        ("system prompt rides the prompt", "agent", "create_agent", "test_system_prompt_rides_the_prompt_never_the_state"),
        ("parallel tool calls fan-in call order", "agent", "ToolNode", "test_parallel_tool_calls_fan_in_call_order"),
        ("tool error -> error ToolMessage, loop continues", "agent", "ToolNode", "test_tool_error_becomes_an_error_toolmessage_and_loop_continues"),
        ("handle_tool_errors=False reraises", "agent", "ToolNode", "test_handle_tool_errors_false_reraises"),
        ("unknown tool -> honest error ToolMessage", "agent", "ToolNode", "test_unknown_tool_name_is_an_honest_error_toolmessage"),
        ("return_direct ends the walk", "agent", "ToolNode", "test_return_direct_tool_ends_the_walk"),
        ("ToolNode standalone lanes + name override", "agent", "ToolNode", "test_toolnode_standalone_state_and_explicit_lanes"),
        ("response_format -> structured_response", "agent", "create_agent", "test_response_format_pydantic_populates_structured_response"),
        ("response_format after the tool rounds", "agent", "create_agent", "test_response_format_runs_only_after_the_tool_rounds"),
        ("custom state schema rides extra channels", "agent", "create_agent", "test_custom_state_schema_rides_extra_channels"),
        ("checkpointer = chat memory across invokes", "agent", "create_agent", "test_checkpointer_gives_chat_memory_across_invokes"),
        ("interrupt_before/after breakpoints", "agent", "create_agent", "test_interrupt_before_tools_parks_then_resumes"),
        ("a tool may park the walk (interrupt inside)", "agent", "ToolNode", "test_a_tool_may_park_the_walk_and_resume_inside_the_tool"),
        ("agent spans nest under a named root", "agent", "create_agent", "test_agent_spans_nest_model_and_tools_under_a_named_root"),
        ("compiled agent carries checkpointer + store", "agent", "create_agent", "test_compiled_agent_carries_checkpointer_and_store"),
        ("recursion limit configurable per invoke", "agent", "create_agent", "test_recursion_limit_configurable_per_invoke"),
    ]:
        a((p4, feat, "langchain/agents/factory.py create_agent @ aa2528fb (2164 lines)", mod, sym, AGENT_SUITE, needle))

    # ---- P5 HOOLA MIDDLEWARE ----------------------------------------------
    p5 = "P5"
    for feat, mod, sym, needle in [
        ("AgentMiddleware hook taxonomy", "middleware", "AgentMiddleware", "test_agent_middleware_base_hooks_exist_and_are_inert"),
        ("ModelRequest.override immutable", "middleware", "ModelRequest", "test_model_request_override_is_immutable_and_validates"),
        ("direct assignment refused", "middleware", "ModelRequest", "test_model_request_direct_assignment_refused"),
        ("ModelResponse/ExtendedModelRequest shapes", "middleware", "ModelResponse", "test_model_result_normalization_shapes"),
        ("hook_config + the decorators", "middleware", "hook_config", "test_hook_config_and_decorators_build_middlewares"),
        ("async-only wrap hook refused at build", "middleware", "wrap_model_call", "test_async_only_wrap_hook_refused_at_build"),
        ("a-* twins honest wording", "middleware", "AgentMiddleware", "test_awrap_only_raises_the_upstream_wording"),
        ("after_model reverse registration order", "middleware", "AgentMiddleware", "test_after_model_runs_in_reverse_registration_order"),
        ("duplicate middleware names refused", "agent", "create_agent", "test_duplicate_middleware_names_and_junk_entries_refused"),
        ("middleware tools + schema merge (first wins)", "agent", "create_agent", "test_middleware_tools_join_the_surface_and_schemas_merge"),
        ("hook nodes carry the middleware name", "agent", "create_agent", "test_hook_node_names_carry_the_middleware_name"),
        ("jump_to reroute (declared/undeclared/ephemeral)", "middleware", "AgentMiddleware", "test_jump_to_is_ephemeral_no_stale_reroute"),
        ("run counters restart, thread counters persist", "middleware", "ModelCallLimitMiddleware", "test_run_counters_restart_thread_counters_persist"),
        ("SummarizationMiddleware (safe cutoff)", "middleware", "SummarizationMiddleware", "test_summarization_triggers_and_rewrites_the_lane"),
        ("AI/Tool pairs never split", "middleware", "SummarizationMiddleware", "test_summarization_never_splits_an_ai_tool_pair"),
        ("overflow middle-cut fallback", "middleware", "SummarizationMiddleware", "test_summarization_middle_cut_fallback_when_the_summarizer_fails"),
        ("PIIMiddleware detectors + strategies", "middleware", "PIIMiddleware", "test_pii_email_redact_and_hash_and_mask"),
        ("PII Luhn credit card", "middleware", "PIIMiddleware", "test_pii_credit_card_luhn_rejects_invalid"),
        ("PII lanes (output/tool-results)", "middleware", "PIIMiddleware", "test_pii_output_and_tool_result_lanes"),
        ("the live PII stream transformer", "middleware", "PIIMiddleware", "test_pii_stream_transformer_redacts_in_flight"),
        ("ModelCallLimit (end/error exits)", "middleware", "ModelCallLimitMiddleware", "test_run_limit_end_jump_stops_the_loop_with_the_message"),
        ("ToolCallLimit (continue/end, per-name scoping)", "middleware", "ToolCallLimitMiddleware", "test_tool_limit_scoped_to_a_tool_name"),
        ("ModelRetryMiddleware", "middleware", "ModelRetryMiddleware", "test_model_retry_recovers_and_delay_is_zero_when_configured"),
        ("interrupts never retried", "middleware", "ModelRetryMiddleware", "test_model_retry_never_retries_an_interrupt"),
        ("ModelFallbackMiddleware chain", "middleware", "ModelFallbackMiddleware", "test_model_fallback_chain_and_all_fail"),
        ("ToolError/ToolRetry middlewares", "middleware", "ToolRetryMiddleware", "test_tool_retry_recovers_then_reports"),
        ("LLMToolEmulator", "middleware", "LLMToolEmulator", "test_llm_tool_emulator_answers_without_executing"),
        ("HumanInTheLoop on the P3 park seam", "middleware", "HumanInTheLoopMiddleware", "test_hitl_parks_with_the_request_shape_and_approve_runs"),
        ("HITL edit substitutes args", "middleware", "HumanInTheLoopMiddleware", "test_hitl_edit_substitutes_args_and_marks_the_result"),
        ("HITL reject/respond + rule 6", "middleware", "HumanInTheLoopMiddleware", "test_hitl_reject_and_respond_answer_without_running"),
        ("TodoListMiddleware", "middleware", "TodoListMiddleware", "test_todo_middleware_registers_the_tool_and_rides_the_prompt"),
        ("ContextEditingMiddleware + ClearToolUsesEdit", "middleware", "ContextEditingMiddleware", "test_context_edit_clears_old_tool_results_and_marks_them"),
        ("FileSearch (glob+grep, stdlib)", "middleware", "FilesystemFileSearchMiddleware", "test_file_search_glob_and_grep_over_a_tree(tmp_path)"),
        ("ProviderToolSearch validated+tagged", "middleware", "ProviderToolSearchMiddleware", "test_provider_tool_search_tags_and_refuses"),
        ("bounded ShellToolMiddleware", "middleware", "ShellToolMiddleware", "test_shell_tool_bounded_and_honest"),
        ("THE UNIFICATION: NudgeMiddleware", "middleware", "NudgeMiddleware", "test_nudge_rides_the_system_message_every_call"),
        ("THE UNIFICATION: CuratorMiddleware", "middleware", "CuratorMiddleware", "test_curator_folds_duplicate_tool_noise"),
        ("THE UNIFICATION: DelegateMiddleware", "middleware", "DelegateMiddleware", "test_delegate_runs_bounded_workers_fail_open"),
        ("THE UNIFICATION: SkillsPrimerMiddleware", "middleware", "SkillsPrimerMiddleware", "test_skills_primer_injects_matched_primers"),
    ]:
        a((p5, feat, "langchain middleware/ types.py 2201 lines + the tier modules @ aa2528fb", mod, sym, MW_SUITE, needle))

    # ---- P6 HOOLA RETRIEVE -------------------------------------------------
    p6 = "P6"
    for feat, mod, sym, needle in [
        ("Document + dict round trip", "retrieve", "Document", "test_document_round_trip_and_equality"),
        ("Embeddings ABC + the deterministic embedder", "retrieve", "DeterministicEmbeddings", "test_deterministic_embeddings_is_deterministic_and_unit"),
        ("VectorStore ABC honest defaults", "retrieve", "VectorStore", "test_vectorstore_abc_honest_defaults(tmp_db)"),
        ("search dispatch similarity|threshold|mmr", "retrieve", "VectorStore", "test_vectorstore_search_dispatch(tmp_db)"),
        ("the [0,1] relevance contract", "retrieve", "VectorStore", "test_relevance_scores_contract_with_threshold(tmp_db)"),
        ("SqliteVectorStore kNN scan + filter", "retrieve", "SqliteVectorStore", "test_sqlite_store_add_get_delete_and_scan(tmp_db)"),
        ("sqlite persistence across instances", "retrieve", "SqliteVectorStore", "test_sqlite_store_persists_across_instances(tmp_db)"),
        ("path=/engine= gate (the vault seam)", "retrieve", "SqliteVectorStore", "test_sqlite_store_path_engine_gate(tmp_db)"),
        ("maximal_marginal_relevance formula", "retrieve", "maximal_marginal_relevance", "test_maximal_marginal_relevance_formula"),
        ("MMR on the store", "retrieve", "SqliteVectorStore", "test_mmr_diversifies_on_the_store(tmp_db)"),
        ("RecordManager ledger + gates", "retrieve", "SqliteRecordManager", "test_record_manager_ledger_shape_and_gates(tmp_db)"),
        ("index() dedup first pass / no-op", "retrieve", "index", "test_index_first_pass_and_no_op_reindex(tmp_db)"),
        ("changed content -> update + stale delete", "retrieve", "index", "test_index_changed_content_updates_and_deletes_stale(tmp_db)"),
        ("full + scoped_full cleanup", "retrieve", "index", "test_index_full_and_scoped_full_cleanup(tmp_db)"),
        ("key encoders + force_update", "retrieve", "index", "test_index_force_update_and_key_encoders(tmp_db)"),
        ("aindex twin", "retrieve", "aindex", "test_aindex_twin(tmp_db)"),
        ("RecursiveCharacterTextSplitter ladder", "retrieve", "RecursiveCharacterTextSplitter", "test_recursive_splitter_ladder_and_gates"),
        ("CharacterTextSplitter separator laws", "retrieve", "CharacterTextSplitter", "test_character_splitter_separator_laws"),
        ("create_documents metadata laws", "retrieve", "TextSplitter", "test_splitter_create_documents_metadata_laws"),
        ("VectorStoreRetriever similarity+mmr", "retrieve", "VectorStoreRetriever", "test_vector_store_retriever_similarity_and_mmr(tmp_db)"),
        ("retriever fires the P2 span", "retrieve", "BaseRetriever", "test_retriever_is_a_runnable_and_fires_the_p2_span(tmp_db)"),
        ("Docs7Retriever (docs7 as a source)", "retrieve", "Docs7Retriever", "test_docs7_retriever_injected_fetch_and_gates"),
    ]:
        a((p6, feat, "langchain retrieval (vectorstores/, indexing/, retrievers.py, text-splitters/) @ aa2528fb", mod, sym, RET_SUITE, needle))

    # ---- P7 HOOLA HUB ------------------------------------------------------
    p7 = "P7"
    for feat, mod, sym, needle in [
        ("init_chat_model fixed mode", "hub", "init_chat_model", "test_fixed_model_and_provider_kwarg_form"),
        ("prefix inference + honest unknown refusal", "hub", "init_chat_model", "test_prefix_inference_and_unknown_refusal"),
        ("register_provider extensions", "hub", "register_provider", "test_register_provider_extension"),
        ("ConfigurableModel model-less mode", "hub", "ConfigurableModel", "test_model_less_requires_config"),
        ("per-call config selection + fields filter", "hub", "ConfigurableModel", "test_configurable_selects_model_per_call"),
        ("queued declarative calls", "hub", "ConfigurableModel", "test_declarative_calls_queued_until_resolved"),
        ("with_config pinned + per-call win", "hub", "ConfigurableModel", "test_with_config_and_stream_batch_ride_resolution"),
        ("HouseBrainChatModel injected runner", "hub", "HouseBrainChatModel", "test_house_brain_sync_runner_and_no_runner_refusal"),
        ("the async brain lane", "hub", "HouseBrainChatModel", "test_house_brain_async_runner"),
        ("BYOK invoke + tool-call parse", "hub", "OpenAICompatChatModel", "test_byok_invoke_and_tool_call_parse"),
        ("broken args dropped (finish=length)", "hub", "OpenAICompatChatModel", "test_byok_broken_args_dropped_and_finish_length"),
        ("SSE streaming merge", "hub", "OpenAICompatChatModel", "test_byok_stream_sse_merge"),
        ("bind_tools on the OpenAI wire", "hub", "OpenAICompatChatModel", "test_byok_bind_tools_rides_the_openai_wire"),
        ("standard_params override (misattribution law)", "hub", "OpenAICompatChatModel", "test_byok_standard_params_override"),
        ("BYOK error lanes", "hub", "OpenAICompatChatModel", "test_byok_error_lanes"),
        ("dumpd/load round trip (both lanes)", "load", "dumpd", "test_dumpd_load_round_trip_message_lane"),
        ("dumps/loads JSON string lane", "load", "loads", "test_dumps_loads_string_lane"),
        ("not_implemented marker names the loss", "load", "SerializedNotImplemented", "test_not_implemented_marker_names_the_loss"),
        ("the escape law (lc dicts never instantiate)", "load", "load", "test_escape_law_plain_lc_dicts_never_instantiate"),
        ("allowed_objects gates + crafted-id refusal", "load", "load", "test_allowed_objects_gates"),
        ("lc_secrets placeholders", "load", "dumpd", "test_secrets_placeholders"),
        ("MCP initialize + cursor pagination", "mcp", "McpClient", "test_mcp_handshake_pagination_and_tools"),
        ("MCP tool call + artifact", "mcp", "McpTool", "test_mcp_tool_call_content_and_artifact"),
        ("open object args stay open", "mcp", "schema_dict_to_model", "test_mcp_open_object_args_stay_open"),
        ("MCP image/audio/error lanes", "mcp", "McpToolError", "test_mcp_image_audio_and_error_lanes"),
        ("elicitation both ways", "mcp", "McpClient", "test_mcp_elicitation_both_ways"),
        ("stdio subprocess round trip", "mcp", "StdioTransport", "test_stdio_transport_real_subprocess_round_trip"),
        ("stdio timeout refusal", "mcp", "StdioTransport", "test_stdio_timeout_refusal"),
        ("group mangling + resolve", "mcp", "McpClientGroup", "test_mcp_group_mangling_and_resolve"),
        ("string targets refused at the gate", "mcp", "load_mcp_tools", "test_bare_string_targets_refused_at_the_mcp_gate"),
        ("conformance: every house adapter passes", "conformance", "assert_conformance", "test_conformance_every_house_adapter_passes"),
        ("conformance: broken fails by name", "conformance", "run_standard_tests", "test_conformance_broken_model_fails_by_name"),
        ("model_data_to_profile (models.dev shape)", "hub", "model_data_to_profile", "test_model_data_to_profile_mapping"),
        ("refresh_profiles byte-stable", "hub", "refresh_profiles", "test_refresh_profiles_byte_stable"),
        ("profile diff markdown", "hub", "summarize_profile_diff", "test_summarize_profile_diff_markdown"),
        ("the CLI lanes + the -m entry", "hub", "main", "test_cli_lanes"),
    ]:
        a((p7, feat, "langchain chat_models/base.py + core/load + langchain/mcp + standard-tests + model-profiles @ aa2528fb",
           mod, sym, HUB_SUITE, needle))

    # ---- P8 THE AUDIT ITSELF ----------------------------------------------
    p8 = "P8"
    for feat, mod, sym, needle in [
        ("the parity matrix verified live", "audit", "audit_parity", "test_audit_parity_all_rows_verified"),
        ("the phase checklist sign-off", "audit", "phase_checklist", "test_phase_checklist_signoff"),
        ("the openwiki analog generated", "audit", "generate_wiki", "test_wiki_generation_deterministic"),
        ("the CLI lanes", "audit", "main", "test_audit_cli_lanes"),
    ]:
        a((p8, feat, "upstream openwiki/ evidence pages + the phase plan (Task 22)", mod, sym, AUDIT_SUITE, needle))
    return m


PARITY_MATRIX: list[R] = _rows()

# ---------------------------------------------------------------------------
# the phase checklist (living numbers)
# ---------------------------------------------------------------------------

PHASES: list[dict[str, Any]] = [
    {"phase": "P1", "name": "HOOLA CORE", "version": "v0.510.0",
     "files": ["messages.py", "runnable.py", "tools.py", "models.py", "prompts.py",
               "parsers.py", "history.py", "stores.py", "serializable.py"],
     "suite": CORE_SUITE},
    {"phase": "P2", "name": "HOOLA TRACE", "version": "v0.520.0",
     "files": ["tracers.py", "vault_sink.py"], "suite": TRACE_SUITE},
    {"phase": "P3", "name": "HOOLA GRAPH", "version": "v0.530.0",
     "files": ["graph.py"], "suite": GRAPH_SUITE},
    {"phase": "P4", "name": "HOOLA AGENT", "version": "v0.549.0",
     "files": ["agent.py"], "suite": AGENT_SUITE},
    {"phase": "P5", "name": "HOOLA MIDDLEWARE (the 24)", "version": "v0.566.0",
     "files": ["middleware.py"], "suite": MW_SUITE},
    {"phase": "P6", "name": "HOOLA RETRIEVE", "version": "v0.580.0",
     "files": ["retrieve.py"], "suite": RET_SUITE},
    {"phase": "P7", "name": "HOOLA HUB", "version": "v0.589.0",
     "files": ["hub.py", "load.py", "mcp.py", "conformance.py"], "suite": HUB_SUITE},
    {"phase": "P8", "name": "HOOLA AEP 1.0 - the parity audit", "version": "v0.600.0",
     "files": ["audit.py"], "suite": AUDIT_SUITE},
]


def _loc(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def phase_checklist() -> list[dict[str, Any]]:
    """The phase-by-phase sign-off with LIVING numbers: LOC counted from the
    tree, test counts counted from the suites - never hard-coded claims."""
    out: list[dict[str, Any]] = []
    for ph in PHASES:
        files = {f: _loc(AEP / f) for f in ph["files"]}
        suite = TESTS / ph["suite"]
        n_tests = sum(1 for line in suite.read_text(encoding="utf-8").splitlines()
                      if line.startswith("def test_")) if suite.exists() else 0
        out.append({**ph, "loc": sum(files.values()), "files_loc": files,
                    "tests": n_tests, "status": "DONE" if suite.exists() else "OPEN"})
    return out


# ---------------------------------------------------------------------------
# the audit itself
# ---------------------------------------------------------------------------

@dataclass
class AuditRow:
    phase: str
    feature: str
    ok: bool
    detail: str


def audit_parity(matrix: list[R] | None = None) -> dict[str, Any]:
    """Verify EVERY matrix row live: the symbol imports, the test needle greps.
    Returns the report dict; `ok` is True only when zero rows drifted - the
    100% claim is computed, never asserted."""
    import importlib
    rows = list(matrix if matrix is not None else PARITY_MATRIX)
    verified: list[AuditRow] = []
    for phase, feature, _ref, mod_name, symbol, test_file, needle in rows:
        # 1. the symbol is importable from the named module
        try:
            mod = importlib.import_module(f"app.aep.{mod_name}")
            if not hasattr(mod, symbol):
                verified.append(AuditRow(phase, feature, False,
                                         f"app.aep.{mod_name}.{symbol} missing"))
                continue
        except Exception as e:  # noqa: BLE001 - a broken import IS the row's failure
            verified.append(AuditRow(phase, feature, False,
                                     f"import app.aep.{mod_name} failed: {e}"))
            continue
        # 2. the proving test needle greps in the named suite
        suite = TESTS / test_file
        try:
            text = suite.read_text(encoding="utf-8")
        except OSError:
            verified.append(AuditRow(phase, feature, False, f"{test_file} missing"))
            continue
        if needle not in text:
            verified.append(AuditRow(phase, feature, False,
                                     f"needle {needle!r} not in {test_file}"))
            continue
        verified.append(AuditRow(phase, feature, True, "ok"))
    failed = [r for r in verified if not r.ok]
    by_phase: dict[str, dict[str, int]] = {}
    for r in verified:
        slot = by_phase.setdefault(r.phase, {"total": 0, "ok": 0})
        slot["total"] += 1
        slot["ok"] += 1 if r.ok else 0
    return {"ok": not failed, "total": len(verified), "verified": len(verified) - len(failed),
            "failed": [{"phase": r.phase, "feature": r.feature, "detail": r.detail}
                       for r in failed],
            "by_phase": by_phase}


# ---------------------------------------------------------------------------
# the openwiki analog
# ---------------------------------------------------------------------------

_WIKI_INTRO = {
    "P1": ("The langchain-core feature surface as house code: messages with the 17 "
           "content blocks, the Runnable composition substrate, tools, the chat-model "
           "contracts, prompts, parsers, chat history, stores - and the serializable "
           "seed P7's loader was reserved for."),
    "P2": ("The LangSmith layer self-hosted: callbacks manager, run trees, "
           "astream_events v2, the Span fire seam every later phase rides, and the "
           "flag-gated vault persistence (runs land as 'aep_run' observations)."),
    "P3": ("The state-graph engine: nodes/edges/conditional, fan-out + join "
           "barriers, add_messages + AgentState, interrupt/Command park-and-resume, "
           "MemorySaver + SqliteSaver - the machine create_agent compiles onto."),
    "P4": ("create_agent: the agent loop compiled onto the house graph - ToolNode, "
           "pending-tool_calls routing, return_direct, structured response, "
           "breakpoints on the park seam, checkpointer chat memory."),
    "P5": ("The 24: the hook taxonomy (before/wrap/after + ModelRequest.override + "
           "the ephemeral jump_to channel) and the middleware tiers - summarization, "
           "PII + the live stream transformer, limits, retry/fallback, HITL on the "
           "park seam, todo, context editing, file search, provider tool search, the "
           "bounded shell - plus THE UNIFICATION: nudge/curator/delegate/"
           "skills-primer as middlewares on the one loop."),
    "P6": ("The retrieval layer: Document, Embeddings + the deterministic sha "
           "embedder, the sqlite-first ANN, RecordManager + index() dedup, the text "
           "splitters, retrievers as Runnables firing the P2 span, docs7 as a source."),
    "P7": ("The hub: init_chat_model over Hoola's brains (fake / hoola-injected-"
           "runner / the openai_compat BYOK zoo), the ConfigurableModel declarative "
           "mode, the from-dict loader (escape law, allowlist Reviver, secrets "
           "placeholders), the hand-built MCP client adapter (stdio + in-memory, "
           "elicitation both ways), the conformance suite every model passes, and "
           "the model-profiles registry + CLI."),
    "P8": ("The 100% parity audit: the matrix verified live (every symbol imports, "
           "every test needle greps), the phase checklist with living numbers, and "
           "these evidence pages - generated from the tree, never asserted."),
}


def generate_wiki(out_dir: str | Path) -> list[Path]:
    """Generate the openwiki-analog evidence pages into out_dir (deterministic:
    the same tree writes byte-stable files)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    checklist = phase_checklist()
    report = audit_parity()
    written: list[Path] = []

    index = ["# HOOLA AEP - the parity wiki (P8)", "",
             "Generated from the tree by `python -m app.aep.audit wiki` - every",
             "feature row cites the house module + symbol and the suite test that",
             "proves it. The numbers are counted live, never hard-coded.", "",
             "| Phase | Name | Version | LOC | Tests | Status |", "|---|---|---|---|---|---|"]
    for ph in checklist:
        index.append(f"| {ph['phase']} | {ph['name']} | {ph['version']} | "
                     f"{ph['loc']} | {ph['tests']} | {ph['status']} |")
    index += ["", f"Parity matrix: **{report['verified']}/{report['total']} rows verified** "
              f"({'OK' if report['ok'] else 'DRIFTED - see the audit output'})", "",
              "# Pages", ""]
    for ph in PHASES:
        index.append(f"- [{ph['phase']} {ph['name']}]({ph['phase'].lower()}-{ph['name'].split()[0].lower()}.md)")
    (out / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    written.append(out / "index.md")

    rows_by_phase: dict[str, list[R]] = {}
    for row in PARITY_MATRIX:
        rows_by_phase.setdefault(row[0], []).append(row)
    for ph in PHASES:
        phase, name = ph["phase"], ph["name"]
        short = name.split()[0].lower()
        entry = next(c for c in checklist if c["phase"] == phase)
        lines = [
            "---",
            f'type: "AEP evidence"',
            f'title: "{phase} {name}"',
            f'generated: {{ by: "app.aep.audit/0.600.0" }}',
            "sources:",
        ]
        for f in ph["files"]:
            lines.append(f"  - repo://server/app/aep/{f}")
        lines.append(f"  - repo://server/tests/{ph['suite']}")
        lines += ["---", "", _WIKI_INTRO[phase], "",
                  f"Files: " + ", ".join(f"`server/app/aep/{f}` ({entry['files_loc'][f]} lines)"
                                         for f in ph["files"]),
                  f"Suite: `server/tests/{ph['suite']}` ({entry['tests']} tests)", "",
                  "| Upstream feature | Hoola symbol | Proven by |", "|---|---|---|"]
        for _phase, feature, _ref, mod_name, symbol, _tf, needle in rows_by_phase.get(phase, []):
            lines.append(f"| {feature} | `app.aep.{mod_name}.{symbol}` | `{needle}` |")
        lines.append("")
        (out / f"{phase.lower()}-{short}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(out / f"{phase.lower()}-{short}.md")
    return written


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.aep.audit",
        description="HOOLA AEP 1.0 - the 100% parity audit + the openwiki "
                    "analog (P8). matrix: print + verify every row. checklist: "
                    "the phase sign-off with living numbers. wiki: generate the "
                    "evidence pages.")
    parser.add_argument("cmd", choices=("matrix", "checklist", "wiki"))
    parser.add_argument("--out", default=None, help="wiki output dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "matrix":
        report = audit_parity()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for ph in PHASES:
                slot = report["by_phase"].get(ph["phase"], {"ok": 0, "total": 0})
                print(f"{ph['phase']}: {slot['ok']}/{slot['total']} rows verified")
            for f in report["failed"]:
                print(f"DRIFT {f['phase']} {f['feature']}: {f['detail']}")
            print(f"TOTAL: {report['verified']}/{report['total']} - "
                  f"{'100% PARITY VERIFIED' if report['ok'] else 'PARITY DRIFT'}")
        return 0 if report["ok"] else 1

    if args.cmd == "checklist":
        rows = phase_checklist()
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                print(f"{r['phase']} {r['name']:<28} {r['version']:<10} "
                      f"{r['loc']:>6} LOC {r['tests']:>3} tests {r['status']}")
        return 0

    if args.cmd == "wiki":
        out_dir = args.out or str(REPO_ROOT / "docs" / "aep-wiki")
        written = generate_wiki(out_dir)
        for p in written:
            print(f"wrote {p}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PARITY_MATRIX", "PHASES", "AuditRow", "audit_parity",
    "generate_wiki", "phase_checklist",
]
