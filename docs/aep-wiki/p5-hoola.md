---
type: "AEP evidence"
title: "P5 HOOLA MIDDLEWARE (the 24)"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/middleware.py
  - repo://server/tests/test_v0550_hoola_middleware.py
---

The 24: the hook taxonomy (before/wrap/after + ModelRequest.override + the ephemeral jump_to channel) and the middleware tiers - summarization, PII + the live stream transformer, limits, retry/fallback, HITL on the park seam, todo, context editing, file search, provider tool search, the bounded shell - plus THE UNIFICATION: nudge/curator/delegate/skills-primer as middlewares on the one loop.

Files: `server/app/aep/middleware.py` (2122 lines)
Suite: `server/tests/test_v0550_hoola_middleware.py` (68 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| AgentMiddleware hook taxonomy | `app.aep.middleware.AgentMiddleware` | `test_agent_middleware_base_hooks_exist_and_are_inert` |
| ModelRequest.override immutable | `app.aep.middleware.ModelRequest` | `test_model_request_override_is_immutable_and_validates` |
| direct assignment refused | `app.aep.middleware.ModelRequest` | `test_model_request_direct_assignment_refused` |
| ModelResponse/ExtendedModelRequest shapes | `app.aep.middleware.ModelResponse` | `test_model_result_normalization_shapes` |
| hook_config + the decorators | `app.aep.middleware.hook_config` | `test_hook_config_and_decorators_build_middlewares` |
| async-only wrap hook refused at build | `app.aep.middleware.wrap_model_call` | `test_async_only_wrap_hook_refused_at_build` |
| a-* twins honest wording | `app.aep.middleware.AgentMiddleware` | `test_awrap_only_raises_the_upstream_wording` |
| after_model reverse registration order | `app.aep.middleware.AgentMiddleware` | `test_after_model_runs_in_reverse_registration_order` |
| duplicate middleware names refused | `app.aep.agent.create_agent` | `test_duplicate_middleware_names_and_junk_entries_refused` |
| middleware tools + schema merge (first wins) | `app.aep.agent.create_agent` | `test_middleware_tools_join_the_surface_and_schemas_merge` |
| hook nodes carry the middleware name | `app.aep.agent.create_agent` | `test_hook_node_names_carry_the_middleware_name` |
| jump_to reroute (declared/undeclared/ephemeral) | `app.aep.middleware.AgentMiddleware` | `test_jump_to_is_ephemeral_no_stale_reroute` |
| run counters restart, thread counters persist | `app.aep.middleware.ModelCallLimitMiddleware` | `test_run_counters_restart_thread_counters_persist` |
| SummarizationMiddleware (safe cutoff) | `app.aep.middleware.SummarizationMiddleware` | `test_summarization_triggers_and_rewrites_the_lane` |
| AI/Tool pairs never split | `app.aep.middleware.SummarizationMiddleware` | `test_summarization_never_splits_an_ai_tool_pair` |
| overflow middle-cut fallback | `app.aep.middleware.SummarizationMiddleware` | `test_summarization_middle_cut_fallback_when_the_summarizer_fails` |
| PIIMiddleware detectors + strategies | `app.aep.middleware.PIIMiddleware` | `test_pii_email_redact_and_hash_and_mask` |
| PII Luhn credit card | `app.aep.middleware.PIIMiddleware` | `test_pii_credit_card_luhn_rejects_invalid` |
| PII lanes (output/tool-results) | `app.aep.middleware.PIIMiddleware` | `test_pii_output_and_tool_result_lanes` |
| the live PII stream transformer | `app.aep.middleware.PIIMiddleware` | `test_pii_stream_transformer_redacts_in_flight` |
| ModelCallLimit (end/error exits) | `app.aep.middleware.ModelCallLimitMiddleware` | `test_run_limit_end_jump_stops_the_loop_with_the_message` |
| ToolCallLimit (continue/end, per-name scoping) | `app.aep.middleware.ToolCallLimitMiddleware` | `test_tool_limit_scoped_to_a_tool_name` |
| ModelRetryMiddleware | `app.aep.middleware.ModelRetryMiddleware` | `test_model_retry_recovers_and_delay_is_zero_when_configured` |
| interrupts never retried | `app.aep.middleware.ModelRetryMiddleware` | `test_model_retry_never_retries_an_interrupt` |
| ModelFallbackMiddleware chain | `app.aep.middleware.ModelFallbackMiddleware` | `test_model_fallback_chain_and_all_fail` |
| ToolError/ToolRetry middlewares | `app.aep.middleware.ToolRetryMiddleware` | `test_tool_retry_recovers_then_reports` |
| LLMToolEmulator | `app.aep.middleware.LLMToolEmulator` | `test_llm_tool_emulator_answers_without_executing` |
| HumanInTheLoop on the P3 park seam | `app.aep.middleware.HumanInTheLoopMiddleware` | `test_hitl_parks_with_the_request_shape_and_approve_runs` |
| HITL edit substitutes args | `app.aep.middleware.HumanInTheLoopMiddleware` | `test_hitl_edit_substitutes_args_and_marks_the_result` |
| HITL reject/respond + rule 6 | `app.aep.middleware.HumanInTheLoopMiddleware` | `test_hitl_reject_and_respond_answer_without_running` |
| TodoListMiddleware | `app.aep.middleware.TodoListMiddleware` | `test_todo_middleware_registers_the_tool_and_rides_the_prompt` |
| ContextEditingMiddleware + ClearToolUsesEdit | `app.aep.middleware.ContextEditingMiddleware` | `test_context_edit_clears_old_tool_results_and_marks_them` |
| FileSearch (glob+grep, stdlib) | `app.aep.middleware.FilesystemFileSearchMiddleware` | `test_file_search_glob_and_grep_over_a_tree(tmp_path)` |
| ProviderToolSearch validated+tagged | `app.aep.middleware.ProviderToolSearchMiddleware` | `test_provider_tool_search_tags_and_refuses` |
| bounded ShellToolMiddleware | `app.aep.middleware.ShellToolMiddleware` | `test_shell_tool_bounded_and_honest` |
| THE UNIFICATION: NudgeMiddleware | `app.aep.middleware.NudgeMiddleware` | `test_nudge_rides_the_system_message_every_call` |
| THE UNIFICATION: CuratorMiddleware | `app.aep.middleware.CuratorMiddleware` | `test_curator_folds_duplicate_tool_noise` |
| THE UNIFICATION: DelegateMiddleware | `app.aep.middleware.DelegateMiddleware` | `test_delegate_runs_bounded_workers_fail_open` |
| THE UNIFICATION: SkillsPrimerMiddleware | `app.aep.middleware.SkillsPrimerMiddleware` | `test_skills_primer_injects_matched_primers` |

